// =============================================================================
//  bfs-fuse — PNFS (Pineapple Native File System) como filesystem FUSE
//
//  Evolução do overlay de usuário (Filesystem/pineapplefs/) rumo a um
//  filesystem de verdade. Este FUSE expõe um volume BFS como raiz de mount:
//
//    /                 → diretório de dados do volume (passthrough)
//    /.bfsprivate/     → metadados do volume (volume.info, snapshots, clones…)
//
//  A camada Python (pineapplefs) continua sendo a ferramenta de *escrita*
//  dos metadados; este FUSE é a camada de *apresentação/montagem* — o
//  primeiro passo para um módulo de kernel PNFS no futuro.
//
//  Uso:
//    bfs-fuse /media/PENDRIVE /mnt/bfs
//    fusermount -u /mnt/bfs
// =============================================================================

use fuser::{
    FileAttr, FileType, Filesystem, MountOption, ReplyAttr, ReplyData, ReplyDirectory, ReplyEntry,
    ReplyCreate, ReplyEmpty, ReplyOpen, ReplyWrite, Request,
};
use std::collections::HashMap;
use std::ffi::OsStr;
use std::fs;
use std::os::unix::fs::{FileExt, MetadataExt, OpenOptionsExt, PermissionsExt};
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

const TTL: Duration = Duration::from_secs(1);

/// Raiz fixa de inodes: 1 = "/", 2 = ".bfsprivate".
const INO_ROOT: u64 = 1;
const INO_PRIVATE: u64 = 2;

struct BfsFs {
    /// Diretório de dados real (o "backing store" do volume).
    backing: PathBuf,
    paths: HashMap<u64, PathBuf>,
}

fn inode_for(path: &Path) -> u64 {
    use std::hash::{Hash, Hasher};
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    path.hash(&mut hasher);
    1000 + (hasher.finish() % 1_000_000)
}

fn attr(ino: u64, size: u64, kind: FileType, uid: u32, gid: u32) -> FileAttr {
    FileAttr {
        ino,
        size,
        blocks: size.div_ceil(512),
        atime: SystemTime::now(),
        mtime: SystemTime::now(),
        ctime: SystemTime::now(),
        crtime: SystemTime::now(),
        kind,
        perm: if kind == FileType::Directory {
            0o755
        } else {
            0o644
        },
        nlink: if kind == FileType::Directory { 2 } else { 1 },
        uid,
        gid,
        rdev: 0,
        blksize: 4096,
        flags: 0,
    }
}

fn file_attr_from_meta(ino: u64, meta: &fs::Metadata) -> FileAttr {
    let kind = if meta.is_dir() {
        FileType::Directory
    } else {
        FileType::RegularFile
    };
    FileAttr {
        ino,
        size: meta.len(),
        blocks: meta.size().div_ceil(512),
        atime: TimeExt::atime(meta).unwrap_or(SystemTime::now()),
        mtime: TimeExt::mtime(meta).unwrap_or(SystemTime::now()),
        ctime: TimeExt::ctime(meta).unwrap_or(SystemTime::now()),
        crtime: TimeExt::ctime(meta).unwrap_or(SystemTime::now()),
        kind,
        perm: (meta.mode() & 0o777) as u16,
        nlink: meta.nlink() as u32,
        uid: meta.uid(),
        gid: meta.gid(),
        rdev: 0,
        blksize: 4096,
        flags: 0,
    }
}

// Conveniência: ctime/mtime como SystemTime (podem falhar em FS exóticos).
trait TimeExt {
    fn atime(&self) -> Option<SystemTime>;
    fn mtime(&self) -> Option<SystemTime>;
    fn ctime(&self) -> Option<SystemTime>;
}

impl TimeExt for fs::Metadata {
    fn atime(&self) -> Option<SystemTime> {
        self.accessed().ok()
    }
    fn mtime(&self) -> Option<SystemTime> {
        self.modified().ok()
    }
    fn ctime(&self) -> Option<SystemTime> {
        // best-effort: usa modified como aproximação se atime falhar
        self.modified().ok()
    }
}

impl Filesystem for BfsFs {
    fn lookup(&mut self, _req: &Request, parent: u64, name: &OsStr, reply: ReplyEntry) {
        if parent == INO_ROOT && name == ".bfsprivate" {
            self.paths.insert(INO_PRIVATE, self.backing.join(".bfsprivate"));
            reply.entry(&TTL, &attr(INO_PRIVATE, 0, FileType::Directory, 0, 0), 0);
            return;
        }
        if parent == INO_PRIVATE {
            // Arquivos de metadados: expõe volume.info se existir.
            if name == "volume.info" {
                let p = self.backing.join(".bfsprivate/volume.info");
                if let Ok(meta) = fs::metadata(&p) {
                    self.paths.insert(INO_PRIVATE + 1, p);
                    reply.entry(&TTL, &file_attr_from_meta(INO_PRIVATE + 1, &meta), 0);
                    return;
                }
            }
            reply.error(libc::ENOENT);
            return;
        }
        // Passthrough do backing store, resolvendo também subdiretórios.
        let base = self.paths.get(&parent).cloned().unwrap_or_else(|| self.backing.clone());
        let path = base.join(name);
        match fs::metadata(&path) {
            Ok(meta) => {
                let ino = inode_for(&path);
                self.paths.insert(ino, path.clone());
                reply.entry(&TTL, &file_attr_from_meta(ino, &meta), 0);
            }
            Err(_) => reply.error(libc::ENOENT),
        }
    }

    fn getattr(&mut self, _req: &Request, ino: u64, reply: ReplyAttr) {
        match ino {
            INO_ROOT => reply.attr(&TTL, &attr(INO_ROOT, 0, FileType::Directory, 0, 0)),
            INO_PRIVATE => reply.attr(&TTL, &attr(INO_PRIVATE, 0, FileType::Directory, 0, 0)),
            _ => {
                if let Some(path) = self.paths.get(&ino) {
                    if let Ok(meta) = fs::metadata(path) {
                        reply.attr(&TTL, &file_attr_from_meta(ino, &meta));
                        return;
                    }
                }
                reply.error(libc::ENOENT);
            }
        }
    }

    fn readdir(
        &mut self,
        _req: &Request,
        ino: u64,
        _fh: u64,
        offset: i64,
        mut reply: ReplyDirectory,
    ) {
        let mut entries: Vec<(u64, FileType, String)> = vec![
            (INO_ROOT, FileType::Directory, ".".into()),
            (INO_ROOT, FileType::Directory, "..".into()),
        ];
        if ino == INO_ROOT {
            entries.push((INO_PRIVATE, FileType::Directory, ".bfsprivate".into()));
            if let Ok(rd) = fs::read_dir(&self.backing) {
                for e in rd.flatten() {
                    let name = e.file_name().to_string_lossy().into_owned();
                    if name.starts_with('.') && name != ".bfsprivate" {
                        continue; // oculta metadados no listing (como o macOS)
                    }
                    let ino_e = inode_for(&e.path());
                    self.paths.insert(ino_e, e.path());
                    let kind = if e.path().is_dir() {
                        FileType::Directory
                    } else {
                        FileType::RegularFile
                    };
                    entries.push((ino_e, kind, name));
                }
            }
        } else if ino == INO_PRIVATE {
            let p = self.backing.join(".bfsprivate/volume.info");
            if p.exists() {
                entries.push((INO_PRIVATE + 1, FileType::RegularFile, "volume.info".into()));
            }
        } else if let Some(dir) = self.paths.get(&ino).cloned() {
            if let Ok(rd) = fs::read_dir(dir) {
                for entry in rd.flatten() {
                    let name = entry.file_name().to_string_lossy().into_owned();
                    if name.starts_with('.') {
                        continue;
                    }
                    let child = entry.path();
                    let child_ino = inode_for(&child);
                    self.paths.insert(child_ino, child.clone());
                    let kind = if child.is_dir() {
                        FileType::Directory
                    } else {
                        FileType::RegularFile
                    };
                    entries.push((child_ino, kind, name));
                }
            }
        }

        for (i, (e_ino, e_kind, e_name)) in entries.into_iter().enumerate().skip(offset as usize) {
            if reply.add(e_ino, (i + 1) as i64, e_kind, e_name) {
                break;
            }
        }
        reply.ok();
    }

    fn open(&mut self, _req: &Request, ino: u64, flags: i32, reply: ReplyOpen) {
        let Some(path) = self.paths.get(&ino) else {
            reply.error(libc::ENOENT);
            return;
        };
        let mut options = fs::OpenOptions::new();
        if flags & libc::O_RDWR != 0 {
            options.read(true).write(true);
        } else if flags & libc::O_WRONLY != 0 {
            options.write(true);
        } else {
            options.read(true);
        }
        match options.open(path) {
            Ok(_) => reply.opened(ino, 0),
            Err(err) => reply.error(err.raw_os_error().unwrap_or(libc::EIO)),
        }
    }

    fn create(
        &mut self,
        _req: &Request,
        parent: u64,
        name: &OsStr,
        mode: u32,
        _umask: u32,
        flags: i32,
        reply: ReplyCreate,
    ) {
        let base = self.paths.get(&parent).cloned().unwrap_or_else(|| self.backing.clone());
        let path = base.join(name);
        match fs::OpenOptions::new()
            .create(true)
            .write(true)
            .read(flags & libc::O_RDWR != 0)
            .mode(mode)
            .open(&path)
        {
            Ok(_) => {
                let ino = inode_for(&path);
                self.paths.insert(ino, path.clone());
                match fs::metadata(&path) {
                    Ok(meta) => reply.created(&TTL, &file_attr_from_meta(ino, &meta), 0, ino, 0),
                    Err(_) => reply.error(libc::EIO),
                }
            }
            Err(err) => reply.error(err.raw_os_error().unwrap_or(libc::EIO)),
        }
    }

    fn mkdir(
        &mut self,
        _req: &Request,
        parent: u64,
        name: &OsStr,
        mode: u32,
        _umask: u32,
        reply: fuser::ReplyEntry,
    ) {
        let base = self.paths.get(&parent).cloned().unwrap_or_else(|| self.backing.clone());
        let path = base.join(name);
        match fs::create_dir(&path) {
            Ok(()) => {
                let ino = inode_for(&path);
                self.paths.insert(ino, path.clone());
                let _ = fs::set_permissions(&path, PermissionsExt::from_mode(mode));
                match fs::metadata(&path) {
                    Ok(meta) => reply.entry(&TTL, &file_attr_from_meta(ino, &meta), 0),
                    Err(_) => reply.error(libc::EIO),
                }
            }
            Err(err) => reply.error(err.raw_os_error().unwrap_or(libc::EIO)),
        }
    }

    fn unlink(&mut self, _req: &Request, parent: u64, name: &OsStr, reply: ReplyEmpty) {
        let base = self.paths.get(&parent).cloned().unwrap_or_else(|| self.backing.clone());
        match fs::remove_file(base.join(name)) {
            Ok(()) => reply.ok(),
            Err(err) => reply.error(err.raw_os_error().unwrap_or(libc::EIO)),
        }
    }

    fn rmdir(&mut self, _req: &Request, parent: u64, name: &OsStr, reply: ReplyEmpty) {
        let base = self.paths.get(&parent).cloned().unwrap_or_else(|| self.backing.clone());
        match fs::remove_dir(base.join(name)) {
            Ok(()) => reply.ok(),
            Err(err) => reply.error(err.raw_os_error().unwrap_or(libc::EIO)),
        }
    }

    fn rename(
        &mut self,
        _req: &Request,
        parent: u64,
        name: &OsStr,
        newparent: u64,
        newname: &OsStr,
        _flags: u32,
        reply: ReplyEmpty,
    ) {
        let old_base = self.paths.get(&parent).cloned().unwrap_or_else(|| self.backing.clone());
        let new_base = self
            .paths
            .get(&newparent)
            .cloned()
            .unwrap_or_else(|| self.backing.clone());
        match fs::rename(old_base.join(name), new_base.join(newname)) {
            Ok(()) => reply.ok(),
            Err(err) => reply.error(err.raw_os_error().unwrap_or(libc::EIO)),
        }
    }

    fn symlink(
        &mut self,
        _req: &Request,
        parent: u64,
        name: &OsStr,
        link: &Path,
        reply: ReplyEntry,
    ) {
        let base = self.paths.get(&parent).cloned().unwrap_or_else(|| self.backing.clone());
        let path = base.join(name);
        match std::os::unix::fs::symlink(link, &path) {
            Ok(()) => {
                let ino = inode_for(&path);
                self.paths.insert(ino, path.clone());
                match fs::symlink_metadata(&path) {
                    Ok(meta) => reply.entry(&TTL, &file_attr_from_meta(ino, &meta), 0),
                    Err(_) => reply.error(libc::EIO),
                }
            }
            Err(err) => reply.error(err.raw_os_error().unwrap_or(libc::EIO)),
        }
    }

    fn readlink(&mut self, _req: &Request, ino: u64, reply: ReplyData) {
        match self.paths.get(&ino).and_then(|path| fs::read_link(path).ok()) {
            Some(target) => reply.data(target.as_os_str().as_encoded_bytes()),
            None => reply.error(libc::ENOENT),
        }
    }

    fn read(
        &mut self,
        _req: &Request,
        ino: u64,
        _fh: u64,
        offset: i64,
        size: u32,
        _flags: i32,
        _lock: Option<u64>,
        reply: ReplyData,
    ) {
        if let Some(path) = self.paths.get(&ino) {
            match fs::File::open(path) {
                Ok(file) => {
                    let mut data = vec![0u8; size as usize];
                    match file.read_at(&mut data, offset.max(0) as u64) {
                        Ok(n) => reply.data(&data[..n]),
                        Err(err) => reply.error(err.raw_os_error().unwrap_or(libc::EIO)),
                    }
                    return;
                }
                Err(err) => {
                    reply.error(err.raw_os_error().unwrap_or(libc::EIO));
                    return;
                }
            }
        }
        reply.error(libc::EIO);
    }

    fn write(
        &mut self,
        _req: &Request,
        ino: u64,
        _fh: u64,
        offset: i64,
        data: &[u8],
        _write_flags: u32,
        _flags: i32,
        _lock: Option<u64>,
        reply: ReplyWrite,
    ) {
        let Some(path) = self.paths.get(&ino) else {
            reply.error(libc::ENOENT);
            return;
        };
        match fs::OpenOptions::new().write(true).open(path) {
            Ok(file) => match file.write_at(data, offset.max(0) as u64) {
                Ok(n) => reply.written(n as u32),
                Err(err) => reply.error(err.raw_os_error().unwrap_or(libc::EIO)),
            },
            Err(err) => reply.error(err.raw_os_error().unwrap_or(libc::EIO)),
        }
    }
}

fn main() {
    let mut args = std::env::args().skip(1);
    let backing = PathBuf::from(args.next().unwrap_or_else(|| "/media/VOLUME".into()));
    let mountpoint = PathBuf::from(args.next().unwrap_or_else(|| "/mnt/bfs".into()));

    if !Path::new(&backing).is_dir() {
        eprintln!(
            "bfs-fuse: backing store não é diretório: {}",
            backing.display()
        );
        std::process::exit(1);
    }

    let options = vec![
        MountOption::FSName("pnfs".into()),
        MountOption::DefaultPermissions,
        MountOption::AllowOther,
    ];

    eprintln!(
        "bfs-fuse: montando {} em {} (PNFS)",
        backing.display(),
        mountpoint.display()
    );
    let _ = fs::create_dir_all(&mountpoint);
    let mut paths = HashMap::new();
    paths.insert(INO_ROOT, backing.clone());
    if let Err(e) = fuser::mount2(BfsFs { backing, paths }, &mountpoint, &options) {
        eprintln!("bfs-fuse: falha ao montar: {e}");
        std::process::exit(1);
    }
}
