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
    FileAttr, FileType, Filesystem, MountOption, ReplyAttr, ReplyData, ReplyDirectory,
    ReplyEntry, Request,
};
use std::ffi::OsStr;
use std::fs;
use std::os::unix::fs::MetadataExt;
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

const TTL: Duration = Duration::from_secs(1);

/// Raiz fixa de inodes: 1 = "/", 2 = ".bfsprivate".
const INO_ROOT: u64 = 1;
const INO_PRIVATE: u64 = 2;

struct BfsFs {
    /// Diretório de dados real (o "backing store" do volume).
    backing: PathBuf,
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
        perm: if kind == FileType::Directory { 0o755 } else { 0o644 },
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
        atime: meta.atime().unwrap_or(SystemTime::now()),
        mtime: meta.mtime().unwrap_or(SystemTime::now()),
        ctime: meta.ctime().unwrap_or(SystemTime::now()),
        crtime: meta.ctime().unwrap_or(SystemTime::now()),
        kind,
        perm: (meta.mode() & 0o777) as u16,
        nlink: meta.nlink() as u16,
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
            reply.entry(&TTL, &attr(INO_PRIVATE, 0, FileType::Directory, 0, 0), 0);
            return;
        }
        if parent == INO_PRIVATE {
            // Arquivos de metadados: expõe volume.info se existir.
            if name == "volume.info" {
                let p = self.backing.join(".bfsprivate/volume.info");
                if let Ok(meta) = fs::metadata(&p) {
                    reply.entry(&TTL, &file_attr_from_meta(INO_PRIVATE + 1, &meta), 0);
                    return;
                }
            }
            reply.error(libc::ENOENT);
            return;
        }
        // Passthrough do backing store.
        let path = self.backing.join(name);
        match fs::metadata(&path) {
            Ok(meta) => {
                // inode determinístico por hash do nome (suficiente p/ skeleton)
                let ino = 1000 + (name.to_string_lossy().bytes().map(|b| b as u64).sum::<u64>() % 1_000_000);
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
                // tenta volume.info
                let p = self.backing.join(".bfsprivate/volume.info");
                if ino == INO_PRIVATE + 1 {
                    if let Ok(meta) = fs::metadata(&p) {
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
                    let ino_e = 1000
                        + (name.bytes().map(|b| b as u64).sum::<u64>() % 1_000_000);
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
        }

        for (i, (e_ino, e_kind, e_name)) in entries.into_iter().enumerate().skip(offset as usize)
        {
            if reply.add(e_ino, (i + 1) as i64, e_kind, e_name) {
                break;
            }
        }
        reply.ok();
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
        if ino == INO_PRIVATE + 1 {
            let p = self.backing.join(".bfsprivate/volume.info");
            if let Ok(data) = fs::read(&p) {
                let start = offset as usize;
                if start >= data.len() {
                    reply.data(&[]);
                } else {
                    let end = (start + size as usize).min(data.len());
                    reply.data(&data[start..end]);
                }
                return;
            }
        }
        reply.error(libc::EIO);
    }
}

fn main() {
    let mut args = std::env::args().skip(1);
    let backing = PathBuf::from(args.next().unwrap_or_else(|| "/media/VOLUME".into()));
    let mountpoint = PathBuf::from(args.next().unwrap_or_else(|| "/mnt/bfs".into()));

    if !Path::new(&backing).is_dir() {
        eprintln!("bfs-fuse: backing store não é diretório: {}", backing.display());
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
    if let Err(e) = fuser::mount2(BfsFs { backing }, &mountpoint, &options) {
        eprintln!("bfs-fuse: falha ao montar: {e}");
        std::process::exit(1);
    }
}
