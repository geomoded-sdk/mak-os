#!/usr/bin/env python3
# =============================================================================
#  pineapplefs / bfs.py — BFS: Pineapple File System (camada sobre exFAT)
#
#  O BFS é um sistema de arquivos de usuário que roda sobre volumes exFAT e
#  traz os recursos que a Apple oferece no APFS/HFS+, no mesmo espírito:
#
#    - "._*" AppleDouble sidecars   (xattrs + Finder Info + resource fork)
#    - .bfsprivate                  (metadados do volume, snapshots, clones)
#    - Snapshots                    (APFS: captura o estado do volume)
#    - Clones / copy-on-write       (APFS: clone de arquivo sem duplicar)
#    - Arquivos esparsos/expandidos (APFS: extents + buracos de zeros)
#    - Case-insensitive             (APFS/HFS+ são case-insensitive por padrão)
#    - Checksums                    (verificação de integridade)
#    - Artefatos do macOS: .Spotlight-V100, .fseventsd, .Trashes, .DS_Store,
#      .metadata_never_index, .localized
#
#  Sem dependências externas (stdlib pura).
# =============================================================================
import datetime
import hashlib
import json
import os
import shutil
import struct
import uuid as _uuid
from pathlib import Path

from .appledouble import (
    build_sidecar,
    parse_sidecar,
    FINDER_INVISIBLE,
)
from .sparse import sparse_from_bytes, sparse_to_bytes, sparse_zero

FORMAT = "bfs-overlay"
FORMAT_VERSION = 1
MAGIC = "BFS"

# Diretórios/arquivos do sistema que o BFS ignora em varreduras
SYSTEM_NAMES = {
    ".bfsprivate",
    ".Spotlight-V100",
    ".fseventsd",
    ".Trashes",
    ".Trash-",
    ".DS_Store",
    ".metadata_never_index",
    ".localized",
}


def is_sidecar(name):
    return name.startswith("._") and len(name) > 2


def is_hidden_name(name):
    """Dotfiles are hidden by default in the Pineapple presentation layer."""
    return name.startswith(".") and name not in SYSTEM_NAMES


def filesystem_type(path):
    """Return the mounted Linux filesystem type when available."""
    try:
        mounts = Path("/proc/mounts").read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return "unknown"

    target = os.path.realpath(path)
    best = ("", "unknown")
    for line in mounts:
        fields = line.split()
        if len(fields) < 3:
            continue
        mountpoint = os.path.realpath(fields[1].replace("\\040", " "))
        if target == mountpoint or target.startswith(mountpoint.rstrip("/") + "/"):
            if len(mountpoint) > len(best[0]):
                best = (mountpoint, fields[2])
    return best[1]


def sha256_of(data):
    return hashlib.sha256(data).hexdigest()


def sanitize(name):
    out = "".join(c for c in name if c.isalnum() or c in "-_.").strip(".")
    return out or "snap"


class BFSVolume:
    def __init__(self, root, case_insensitive=True):
        self.root = Path(root)
        self.private = self.root / ".bfsprivate"
        self.case_insensitive = case_insensitive

    # ------------------------------------------------------------------
    #  Inicialização do volume (exFAT + artefatos do macOS)
    # ------------------------------------------------------------------
    def init(self, name="Pineapple OS"):
        """Add BFS metadata without formatting or deleting the underlying volume."""
        self.root.mkdir(parents=True, exist_ok=True)
        self.private.mkdir(exist_ok=True)
        for sub in ("snapshots", "clones", "checksums", "trash", "sparse"):
            (self.private / sub).mkdir(exist_ok=True)

        info_path = self.private / "volume.info"
        if not info_path.exists():
            info = {
                "magic": MAGIC,
                "name": name,
                "format": FORMAT,
                "filesystem": filesystem_type(self.root),
                "version": FORMAT_VERSION,
                "case_insensitive": self.case_insensitive,
                "uuid": str(_uuid.uuid4()),
                "created": datetime.datetime.now(datetime.timezone.utc)
                .isoformat(),
            }
            info_path.write_text(
                json.dumps(info, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        if not (self.private / "clones" / "registry.json").exists():
            (self.private / "clones" / "registry.json").write_text(
                "{}\n", encoding="utf-8")

        # artefatos que o macOS cria no volume (exFAT / APFS)
        (self.root / ".Spotlight-V100").mkdir(exist_ok=True)
        (self.root / ".fseventsd").mkdir(exist_ok=True)
        (self.root / ".Trashes").mkdir(exist_ok=True)
        (self.root / ".Trashes" / "pineapple").mkdir(exist_ok=True)
        (self.root / ".DS_Store").touch(exist_ok=True)
        (self.root / ".metadata_never_index").touch(exist_ok=True)
        localized = self.root / ".localized"
        if not localized.exists():
            localized.write_text(name + "\n", encoding="utf-8")
        event_log = self.root / ".fseventsd" / "pineapple.events"
        event_log.touch(exist_ok=True)
        return self

    def record_event(self, action, rel):
        """Record a small append-only change journal for fast rescan decisions."""
        event_log = self.root / ".fseventsd" / "pineapple.events"
        event_log.parent.mkdir(exist_ok=True)
        with event_log.open("a", encoding="utf-8") as stream:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            stream.write(json.dumps({"time": timestamp, "action": action, "path": rel}) + "\n")

    def trash(self, rel):
        path = self.resolve(rel)
        if path is None or not path.exists():
            return False
        target = self.root / ".Trashes" / "pineapple" / path.name
        counter = 1
        while target.exists():
            target = target.with_name(f"{path.name}.{counter}")
            counter += 1
        shutil.move(str(path), str(target))
        self.record_event("trash", rel)
        return True

    def info(self):
        info_path = self.private / "volume.info"
        if not info_path.exists():
            return {"magic": MAGIC, "format": FORMAT}
        info = json.loads(info_path.read_text(encoding="utf-8"))
        info.setdefault("filesystem", filesystem_type(self.root))
        return info

    # ------------------------------------------------------------------
    #  Resolução de caminhos (case-insensitive como APFS/HFS+)
    # ------------------------------------------------------------------
    def resolve(self, rel):
        """Devolve o Path real (respeitando case-insensitive) ou None."""
        parts = [p for p in rel.replace("\\", "/").split("/") if p not in ("", ".")]
        cur = self.root
        for p in parts:
            if p == "..":
                continue
            if self.case_insensitive:
                hit = None
                try:
                    names = os.listdir(cur)
                except OSError:
                    return None
                low = p.lower()
                for n in names:
                    if n.lower() == low:
                        hit = cur / n
                        break
                if hit is None:
                    return None
                cur = hit
            else:
                cur = cur / p
                if not os.path.lexists(cur):
                    return None
        return cur

    def resolve_or(self, rel):
        """Igual a resolve(), mas devolve o caminho literal se não existir."""
        found = self.resolve(rel)
        return found if found is not None else (self.root / rel)

    def is_system(self, path):
        try:
            return path.name in SYSTEM_NAMES
        except OSError:
            return True

    def walk_files(self, include_sidecars=True):
        """Itera os arquivos de dados do volume (ignora sistema/.bfsprivate)."""
        for base, dirs, files in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in SYSTEM_NAMES]
            base_p = Path(base)
            for fn in files:
                if fn in SYSTEM_NAMES:
                    continue
                if is_sidecar(fn) and not include_sidecars:
                    continue
                yield base_p / fn

    # ------------------------------------------------------------------
    #  Sidecars "._" (AppleDouble) + xattrs + Finder Info
    # ------------------------------------------------------------------
    def sidecar_path(self, path):
        return path.parent / ("._" + path.name)

    def _read_sidecar(self, path):
        sp = self.sidecar_path(path)
        if not sp.exists():
            return {}
        return parse_sidecar(sp.read_bytes())

    def _write_sidecar(self, path, data):
        sp = self.sidecar_path(path)
        payload = build_sidecar(
            xattrs=data.get("xattrs"),
            finder_flags=data.get("finder_flags", 0),
            resource_fork=data.get("resource_fork"),
            unicode_name=data.get("unicode_name"),
        )
        sp.write_bytes(payload)

    def sync_sidecars(self):
        """Como o macOS em volumes exFAT: garante um '._*' ao lado de cada
        arquivo de dados do volume."""
        n = 0
        for path in self.walk_files(include_sidecars=False):
            if not self.sidecar_path(path).exists():
                self._write_sidecar(path, {"finder_flags": 0})
                n += 1
        return n

    def set_xattr(self, rel, name, value):
        path = self.resolve_or(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._read_sidecar(path)
        data.setdefault("xattrs", {})
        if name == "com.apple.ResourceFork":
            data["resource_fork"] = value
            data["xattrs"].pop(name, None)
        else:
            data["xattrs"][name] = value
        self._write_sidecar(path, data)
        return data

    def get_xattr(self, rel, name):
        path = self.resolve(rel)
        if path is None or not path.exists():
            return None
        data = self._read_sidecar(path)
        if name == "com.apple.ResourceFork":
            return data.get("resource_fork")
        return data.get("xattrs", {}).get(name)

    def list_xattrs(self, rel):
        path = self.resolve(rel)
        if path is None or not path.exists():
            return []
        data = self._read_sidecar(path)
        names = list(data.get("xattrs", {}))
        if "resource_fork" in data:
            names.append("com.apple.ResourceFork")
        return names

    def del_xattr(self, rel, name):
        path = self.resolve(rel)
        if path is None or not path.exists():
            return False
        data = self._read_sidecar(path)
        changed = False
        if name == "com.apple.ResourceFork" and "resource_fork" in data:
            del data["resource_fork"]
            changed = True
        elif data.get("xattrs", {}).pop(name, None) is not None:
            changed = True
        if changed:
            self._write_sidecar(path, data)
        return changed

    def set_finder(self, rel, invisible=None, flags=None):
        path = self.resolve_or(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._read_sidecar(path)
        current = data.get("finder_flags", 0)
        if flags is not None:
            current = flags
        if invisible is True:
            current |= FINDER_INVISIBLE
        elif invisible is False:
            current &= ~FINDER_INVISIBLE
        data["finder_flags"] = current
        self._write_sidecar(path, data)
        return current

    def is_invisible(self, rel):
        path = self.resolve(rel)
        if path is None or not path.exists():
            return False
        if is_hidden_name(path.name):
            return True
        return bool(self._read_sidecar(path).get("finder_flags", 0)
                    & FINDER_INVISIBLE)

    # ------------------------------------------------------------------
    #  Dados do arquivo + checksums
    # ------------------------------------------------------------------
    def put(self, rel, data, xattrs=None, finder_flags=0):
        """Escreve `data` como arquivo do volume (com sidecar opcional)."""
        path = self.resolve_or(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self._register_checksum(rel, data)
        if xattrs or finder_flags:
            self._write_sidecar(path, {
                "xattrs": xattrs or {},
                "finder_flags": finder_flags,
            })
        return path

    def read(self, rel):
        """Lê os bytes reais de um arquivo (desfazendo esparso)."""
        path = self.resolve(rel)
        if path is None or not path.exists():
            return None
        return sparse_to_bytes(path.read_bytes())

    def write(self, rel, data):
        """Escrita com copy-on-write: se o arquivo for um clone, desfaz o
        link antes de gravar (como o APFS)."""
        path = self.resolve_or(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._cow_break(path, rel)
        path.write_bytes(data)
        self._register_checksum(rel, data)
        return path

    def size(self, rel):
        """Tamanho lógico do arquivo (desfaz esparso, como o APFS)."""
        path = self.resolve(rel)
        if path is None or not path.exists():
            return None
        data = path.read_bytes()
        if data[:6] == b"PFSS01":
            return struct.unpack(">Q", data[14:22])[0]
        return path.stat().st_size

    def expand(self, rel, size, block=4096):
        """Cria um arquivo esparso 'expandido' com `size` bytes lógicos
        (só extents são gravados; o resto é zeros)."""
        path = self.resolve_or(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(sparse_zero(size, block))
        self._register_checksum(rel, b"")
        return path

    def put_sparse(self, rel, data, block=4096):
        """Grava `data` como arquivo esparso (só blocos com dados)."""
        path = self.resolve_or(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        container = sparse_from_bytes(data, block)
        path.write_bytes(container)
        self._register_checksum(rel, data)
        return path

    def _register_checksum(self, rel, data):
        cj_path = self.private / "checksums" / "index.json"
        cj = {}
        if cj_path.exists():
            cj = json.loads(cj_path.read_text(encoding="utf-8"))
        cj[rel.replace("\\", "/")] = {
            "sha256": sha256_of(data),
            "size": len(data),
        }
        cj_path.write_text(
            json.dumps(cj, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")

    def verify(self):
        """Verifica integridade dos arquivos registrados (APFS-like)."""
        cj_path = self.private / "checksums" / "index.json"
        if not cj_path.exists():
            return {}
        cj = json.loads(cj_path.read_text(encoding="utf-8"))
        results = {}
        for rel, meta in cj.items():
            path = self.resolve(rel)
            if path is None or not path.exists():
                results[rel] = "missing"
                continue
            digest = sha256_of(self.read(rel))
            results[rel] = "ok" if digest == meta["sha256"] else "corrupt"
        return results

    # ------------------------------------------------------------------
    #  Clones (APFS) — copy-on-write com deduplicação
    # ------------------------------------------------------------------
    def _load_registry(self):
        p = self.private / "clones" / "registry.json"
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding="utf-8"))

    def _save_registry(self, reg):
        (self.private / "clones" / "registry.json").write_text(
            json.dumps(reg, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")

    def _clone_blob(self, digest):
        return self.private / "clones" / digest

    def clone(self, rel_src, rel_dst):
        """Clona `rel_src` em `rel_dst` sem duplicar dados: ambos passam a
        referenciar o mesmo blob (hardlink), registrado em .bfsprivate/clones.
        Modificar um deles (write) quebra o link — copy-on-write, como no APFS."""
        src = self.resolve(rel_src)
        if src is None or not src.is_file():
            raise FileNotFoundError(rel_src)
        dst = self.resolve_or(rel_dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        digest = sha256_of(data)
        blob = self._clone_blob(digest)
        if not blob.exists():
            blob.write_bytes(data)
        reg = self._load_registry()
        paths = reg.setdefault(digest, [])
        for rel in (rel_src, rel_dst):
            rel = rel.replace("\\", "/")
            if rel not in paths:
                paths.append(rel)
        self._save_registry(reg)
        # converte src e dst em hardlinks do blob (dedup real de dados)
        try:
            src.unlink()
            os.link(blob, src)
            if dst.exists():
                dst.unlink()
            os.link(blob, dst)
        except OSError:
            if not dst.exists():
                shutil.copyfile(blob, dst)
        return digest

    def _cow_break(self, path, rel):
        """Quebra o link de clone antes de uma escrita (copy-on-write):
        copia o conteúdo atual para um inode independente, senão a gravação
        alteraria os outros clones (que compartilham o hardlink)."""
        reg = self._load_registry()
        rel = rel.replace("\\", "/")
        for digest, paths in list(reg.items()):
            if rel in paths:
                paths.remove(rel)
                if not paths:
                    reg.pop(digest, None)
                    self._clone_blob(digest).unlink(missing_ok=True)
                self._save_registry(reg)
                tmp = path.with_name(path.name + ".cowtmp")
                shutil.copy2(path, tmp)
                path.unlink()
                os.replace(tmp, path)
                break

    def refcount(self, rel):
        """Quantas referências (paths) um clone tem — 0 se não for clone."""
        path = self.resolve(rel)
        if path is None or not path.exists():
            return 0
        digest = sha256_of(path.read_bytes())
        paths = self._load_registry().get(digest, [])
        return len(paths)

    def unlink(self, rel):
        """Remove um arquivo; se for clone, libera a referência (dedup)."""
        path = self.resolve(rel)
        if path is None or not path.exists():
            return False
        rel = rel.replace("\\", "/")
        reg = self._load_registry()
        for digest, paths in list(reg.items()):
            if rel in paths:
                paths.remove(rel)
                if not paths:
                    reg.pop(digest, None)
                    self._clone_blob(digest).unlink(missing_ok=True)
                self._save_registry(reg)
                break
        path.unlink()
        sp = self.sidecar_path(path)
        if sp.exists():
            sp.unlink(missing_ok=True)
        return True

    # ------------------------------------------------------------------
    #  Snapshots (APFS)
    # ------------------------------------------------------------------
    def snapshot(self, name):
        """Snapshot do volume: captura o estado atual em
        .bfsprivate/snapshots/<name>/ (arquivos de clones são deduplicados
        via hardlink; os demais são copiados, garantindo imutabilidade)."""
        snap_dir = self.private / "snapshots" / sanitize(name)
        tree = snap_dir / "tree"
        tree.mkdir(parents=True, exist_ok=True)
        manifest = []
        reg = self._load_registry()
        for path in self.walk_files(include_sidecars=True):
            rel = path.relative_to(self.root).as_posix()
            dst = tree / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            digest = sha256_of(path.read_bytes())
            blob = self._clone_blob(digest)
            try:
                if blob.exists() and os.path.samefile(path, blob):
                    os.link(blob, dst)
                else:
                    shutil.copy2(path, dst)
            except OSError:
                shutil.copy2(path, dst)
            manifest.append({
                "path": rel,
                "sha256": digest,
                "size": path.stat().st_size,
                "mtime": path.stat().st_mtime,
            })
        (snap_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        return name

    def snapshots(self):
        base = self.private / "snapshots"
        if not base.exists():
            return []
        out = []
        for d in sorted(base.iterdir()):
            if d.is_dir() and (d / "manifest.json").exists():
                out.append(d.name)
        return out

    def restore(self, name):
        snap_dir = self.private / "snapshots" / sanitize(name)
        manifest_path = snap_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"snapshot '{name}' não existe")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest:
            rel = entry["path"]
            src = snap_dir / "tree" / rel
            dst = self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() or dst.is_symlink():
                dst.unlink()
            shutil.copy2(src, dst)
            os.utime(dst, (entry.get("mtime", 0), entry.get("mtime", 0)))
        return len(manifest)