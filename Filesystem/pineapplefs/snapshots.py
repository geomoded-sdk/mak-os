#!/usr/bin/env python3
# =============================================================================
#  pineapplefs / snapshots.py — camada BFS: snapshots
#
#  BFS v2 — camada "snapshots". Captura o estado imutável do volume em
#  .bfsprivate/snapshots/<nome>/: arquivos de clones são deduplicados via
#  hardlink com a camada de clones; os demais são copiados (imutabilidade
#  real, como o APFS tmutil/Time Machine — honesto: cópia, não copy-on-write
#  em bloco).
# =============================================================================
import json
import os
import shutil

from .constants import sanitize, sha256_of


class SnapshotLayer:
    def __init__(self, volume):
        self.v = volume

    def _dir(self, name):
        return self.v.private / "snapshots" / sanitize(name)

    # --------------------------------------------------------------- API
    def create(self, name):
        snap_dir = self._dir(name)
        tree = snap_dir / "tree"
        tree.mkdir(parents=True, exist_ok=True)
        manifest = []
        clones = self.v.clones
        for path in self.v.walk_files(include_sidecars=True):
            rel = path.relative_to(self.v.root).as_posix()
            dst = tree / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            digest = sha256_of(path.read_bytes())
            blob = clones.blob_path(digest)
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

    def list(self):
        base = self.v.private / "snapshots"
        if not base.exists():
            return []
        out = []
        for d in sorted(base.iterdir()):
            if d.is_dir() and (d / "manifest.json").exists():
                out.append(d.name)
        return out

    def restore(self, name):
        snap_dir = self._dir(name)
        manifest_path = snap_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"snapshot '{name}' não existe")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest:
            rel = entry["path"]
            src = snap_dir / "tree" / rel
            dst = self.v.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() or dst.is_symlink():
                dst.unlink()
            shutil.copy2(src, dst)
            os.utime(dst, (entry.get("mtime", 0), entry.get("mtime", 0)))
        return len(manifest)