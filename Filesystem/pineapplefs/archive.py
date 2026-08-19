#!/usr/bin/env python3
# =============================================================================
#  pineapplefs / archive.py — arquivos .zip no estilo macOS (ditto/Archive
#  Utility) com pasta "_PINEAPPLE" e sidecars "._*" (AppleDouble).
#
#  Quando o macOS empacota com "ditto -c -k --keepParent" ele cria, dentro do
#  .zip, uma pasta com um "._<nome>" para cada arquivo, guardando xattrs e
#  Finder Info. O Pineapple OS faz o mesmo com a pasta "_PINEAPPLE" (o nome
#  "macosx" é marca patenteada — aqui é Pineapple):
#
#    _PINEAPPLE/._<Topo>            (sidecar do item de topo)
#    _PINEAPPLE/._<Topo>/._<sub>    (sidecar de cada arquivo interno)
#
#  Sem dependências externas.
# =============================================================================
import os
import zipfile
from pathlib import Path

from .appledouble import build_sidecar, parse_sidecar

PINEAPPLE_FOLDER = "_PINEAPPLE"


def _default_sidecar():
    return build_sidecar(finder_flags=0)


def pack(root, out_zip, keep_parent=True):
    """Empacota `root` em um .zip estilo macOS (com _PINEAPPLE + ._ sidecars)."""
    from .bfs import BFSVolume, SYSTEM_NAMES, is_sidecar

    root = Path(root)
    top = root.name if keep_parent else ""
    prefix = top + "/" if top else ""
    bfs = BFSVolume(root)

    files = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SYSTEM_NAMES]
        for fn in names:
            if fn in SYSTEM_NAMES or is_sidecar(fn):
                continue
            files.append(Path(base) / fn)

    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files:
            rel = path.relative_to(root).as_posix()
            z.write(path, prefix + rel)
        # sidecar do item de topo
        if top:
            z.writestr(f"{PINEAPPLE_FOLDER}/._ {top}".replace("._ ", "._"),
                       _default_sidecar())
        for path in files:
            rel = path.relative_to(root).as_posix()
            data = bfs._read_sidecar(path)
            payload = build_sidecar(
                xattrs=data.get("xattrs"),
                finder_flags=data.get("finder_flags", 0),
                resource_fork=data.get("resource_fork"),
                unicode_name=data.get("unicode_name"),
            )
            entry = f"{PINEAPPLE_FOLDER}/._ {top}/._ {rel}".replace("._ ", "._")
            z.writestr(entry, payload)
    return len(files)


def unpack(zip_path, dest):
    """Extrai um .zip estilo macOS e aplica os sidecars '._' nos arquivos."""
    from .bfs import BFSVolume, is_sidecar

    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    bfs = BFSVolume(dest)
    sidecars = {}

    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename
            if name.endswith("/"):
                continue
            if name.startswith(PINEAPPLE_FOLDER + "/"):
                sidecars[name[len(PINEAPPLE_FOLDER) + 1:]] = z.read(info)
                continue
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as f:
                f.write(z.read(info))

    def apply_sidecar(side_name, payload):
        # "._Topo", "._Topo/._sub" -> caminho real (remove os prefixos "._")
        parts = side_name.split("/")
        real = []
        for p in parts:
            if not p:
                continue
            if p.startswith("._"):
                p = p[2:]
            real.append(p)
        if not real:
            return False
        target = dest
        for p in real:
            target = target / p
        if not target.exists():
            return False
        data = parse_sidecar(payload)
        sidecar = bfs.sidecar_path(target)
        sidecar.write_bytes(payload)
        return True

    applied = 0
    for side_name, payload in sidecars.items():
        if apply_sidecar(side_name, payload):
            applied += 1
    return applied


def has_pineapple_folder(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        return any(n.startswith(PINEAPPLE_FOLDER + "/") for n in z.namelist())