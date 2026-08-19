#!/usr/bin/env python3
# =============================================================================
#  pineapplefs / metadata.py — camada BFS: xattrs
#
#  BFS v2 — camada de metadados "xattrs". Grava os atributos estendidos de um
#  arquivo no formato AppleDouble (sidecar "._<nome>"), o mesmo que o macOS
#  usa em volumes que não suportam atributos nativos (exFAT, FAT, SMB).
#
#  Depende de: appledouble (formato) e do volume (core) para o sidecar.
# =============================================================================
from .appledouble import XATTR_RESOURCE_FORK, build_sidecar, parse_sidecar


class XattrLayer:
    """Atributos estendidos de arquivos do volume (sidecar AppleDouble '._*').

    Toda operação lê/escreve o sidecar do arquivo; a camada de apresentação
    (Finder) usa este mesmo mecanismo para gravar as tags/metadados do Finder.
    """

    def __init__(self, volume):
        self.v = volume

    # ------------------------------------------------------------------ plumb
    def _sidecar(self, path):
        return self.v.sidecar_path(path)

    def _read(self, path):
        sp = self._sidecar(path)
        if not sp.exists():
            return {}
        return parse_sidecar(sp.read_bytes())

    def _write(self, path, data):
        payload = build_sidecar(
            xattrs=data.get("xattrs"),
            finder_flags=data.get("finder_flags", 0),
            resource_fork=data.get("resource_fork"),
            unicode_name=data.get("unicode_name"),
        )
        self._sidecar(path).write_bytes(payload)

    def _ensure_sidecar(self, path, data=None):
        """Garante que o sidecar '._*' existe ao lado de `path`."""
        if not self._sidecar(path).exists():
            self._write(path, data or {"finder_flags": 0})

    # ------------------------------------------------------------------- API
    def get(self, rel, name):
        path = self.v.resolve(rel)
        if path is None or not path.exists():
            return None
        data = self._read(path)
        if name == XATTR_RESOURCE_FORK:
            return data.get("resource_fork")
        return data.get("xattrs", {}).get(name)

    def set(self, rel, name, value):
        path = self.v.resolve_or(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._read(path)
        data.setdefault("xattrs", {})
        if name == XATTR_RESOURCE_FORK:
            data["resource_fork"] = value
            data["xattrs"].pop(name, None)
        else:
            data["xattrs"][name] = value
        self._write(path, data)
        return data

    def list(self, rel):
        path = self.v.resolve(rel)
        if path is None or not path.exists():
            return []
        data = self._read(path)
        names = list(data.get("xattrs", {}))
        if "resource_fork" in data:
            names.append(XATTR_RESOURCE_FORK)
        return names

    def delete(self, rel, name):
        path = self.v.resolve(rel)
        if path is None or not path.exists():
            return False
        data = self._read(path)
        changed = False
        if name == XATTR_RESOURCE_FORK and "resource_fork" in data:
            del data["resource_fork"]
            changed = True
        elif data.get("xattrs", {}).pop(name, None) is not None:
            changed = True
        if changed:
            self._write(path, data)
        return changed

    # ------------------------------------------------- acesso cru ao sidecar
    # A camada Finder (e outras) empilham POR CIMA da camada de xattrs: leem e
    # gravam o mesmo sidecar '._*' para persistir Finder Info, tags etc.
    def read_entry(self, path):
        """Devolve {xattrs, finder_flags, resource_fork, unicode_name}."""
        return self._read(path)

    def write_entry(self, path, data):
        self._write(path, data)

    # Aliases compatíveis com a API antiga do BFS v1 (BFSVolume.set_xattr...)
    get_xattr = get
    set_xattr = set
    list_xattrs = list
    del_xattr = delete