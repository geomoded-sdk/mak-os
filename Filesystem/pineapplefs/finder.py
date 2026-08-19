#!/usr/bin/env python3
# =============================================================================
#  pineapplefs / finder.py — camada BFS: metadados do Finder
#
#  BFS v2 — camada "finder". Traduz o que o macOS grava no Finder Info e nas
#  xattrs "com.apple.metadata:*" para o overlay BFS:
#
#    * flags do Finder (invisível, ícone custom, estacionário)  → Finder Info
#    * tags coloridas (com.apple.metadata:kMDItemUserTags)      → xattr
#    * comentário (com.apple.metadata:kMDItemFinderComment)     → xattr
#    * ícone custom (org.pineappleos.customicon) + bit do Finder → xattr+flag
#
#  Empilha POR CIMA da camada de xattrs (metadata.py): a persistência dos
#  metadados acontece no mesmo sidecar AppleDouble '._*'.
# =============================================================================
import json

from .constants import is_hidden_name
from .metadata import XattrLayer  # noqa: F401  (dependência explícita)

# Bits do campo finder_flags no sidecar AppleDouble (modelo próprio do BFS,
# auto-consistente — espelha os conceitos do Finder, não o binário da Apple).
FINDER_INVISIBLE = 0x4000          # kIsInvisible
FINDER_CUSTOM_ICON = 0x0400        # kHasCustomIcon
FINDER_STATIONERY = 0x2000         # kIsStationery

XATTR_TAGS = "com.apple.metadata:kMDItemUserTags"
XATTR_COMMENT = "com.apple.metadata:kMDItemFinderComment"
XATTR_CUSTOM_ICON = "org.pineappleos.customicon"

COLOR_TAGS = ["Red", "Orange", "Yellow", "Green", "Blue", "Purple", "Gray"]


class FinderLayer:
    """Metadados estilo Finder do macOS, persistidos no sidecar '._*'."""

    def __init__(self, volume):
        self.v = volume

    # ------------------------------------------------------------ internos
    def _entry(self, rel):
        path = self.v.resolve_or(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path, self.v.xattrs.read_entry(path)

    def _save(self, path, data):
        self.v.xattrs.write_entry(path, data)

    # ------------------------------------------------------------- flags
    def flags(self, rel):
        path = self.v.resolve(rel)
        if path is None or not path.exists():
            return 0
        return self.v.xattrs.read_entry(path).get("finder_flags", 0)

    def set_flags(self, rel, value):
        path, data = self._entry(rel)
        data["finder_flags"] = value
        self._save(path, data)
        return value

    def invisible(self, rel):
        path = self.v.resolve(rel)
        if path is None or not path.exists():
            return False
        if is_hidden_name(path.name):
            return True
        return bool(self.flags(rel) & FINDER_INVISIBLE)

    def set_invisible(self, rel, value):
        path, data = self._entry(rel)
        flags = data.get("finder_flags", 0)
        if value:
            flags |= FINDER_INVISIBLE
        else:
            flags &= ~FINDER_INVISIBLE
        data["finder_flags"] = flags
        self._save(path, data)
        return flags

    def stationery(self, rel):
        return bool(self.flags(rel) & FINDER_STATIONERY)

    def set_stationery(self, rel, value):
        path, data = self._entry(rel)
        flags = data.get("finder_flags", 0)
        flags = flags | FINDER_STATIONERY if value else flags & ~FINDER_STATIONERY
        data["finder_flags"] = flags
        self._save(path, data)
        return flags

    # ------------------------------------------------------- ícone custom
    def custom_icon(self, rel):
        path = self.v.resolve(rel)
        if path is None or not path.exists():
            return False
        return bool(self.flags(rel) & FINDER_CUSTOM_ICON)

    def set_custom_icon(self, rel, png_bytes):
        """Define o ícone custom do arquivo (PNG) no xattr + bit do Finder."""
        path, data = self._entry(rel)
        xattrs = data.setdefault("xattrs", {})
        flags = data.get("finder_flags", 0)
        if png_bytes is None:
            xattrs.pop(XATTR_CUSTOM_ICON, None)
            flags &= ~FINDER_CUSTOM_ICON
        else:
            xattrs[XATTR_CUSTOM_ICON] = png_bytes
            flags |= FINDER_CUSTOM_ICON
        data["finder_flags"] = flags
        self._save(path, data)
        return flags

    def icon_bytes(self, rel):
        return self.v.xattrs.get(rel, XATTR_CUSTOM_ICON)

    # ------------------------------------------------------------- tags
    def tags(self, rel):
        raw = self.v.xattrs.get(rel, XATTR_TAGS)
        if raw is None:
            return []
        try:
            value = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return []
        return value if isinstance(value, list) else []

    def set_tags(self, rel, tags):
        value = list(tags)
        if value:
            self.v.xattrs.set(rel, XATTR_TAGS,
                              json.dumps(value, ensure_ascii=False).encode("utf-8"))
        else:
            self.v.xattrs.delete(rel, XATTR_TAGS)
        return value

    def add_tag(self, rel, tag):
        tags = self.tags(rel)
        if tag not in tags:
            tags.append(tag)
            self.set_tags(rel, tags)
        return tags

    def remove_tag(self, rel, tag):
        tags = [t for t in self.tags(rel) if t != tag]
        self.set_tags(rel, tags)
        return tags

    # ---------------------------------------------------------- comentário
    def comment(self, rel):
        raw = self.v.xattrs.get(rel, XATTR_COMMENT)
        if raw is None:
            return None
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("utf-8", errors="replace")

    def set_comment(self, rel, text):
        if text is None:
            self.v.xattrs.delete(rel, XATTR_COMMENT)
            return None
        self.v.xattrs.set(rel, XATTR_COMMENT, text.encode("utf-8"))
        return text

    # ------------------------------------------------------- sidecars
    def sync_sidecars(self):
        """Como o macOS em volumes exFAT: garante um '._*' ao lado de cada
        arquivo de dados do volume."""
        n = 0
        for path in self.v.walk_files(include_sidecars=False):
            self.v.xattrs._ensure_sidecar(path)
            n += 1
        return n

    # ------------------------- aliases compatíveis (API BFS v1)
    is_invisible = invisible

    def set_finder(self, rel, invisible=None, flags=None):
        path, data = self._entry(rel)
        current = data.get("finder_flags", 0)
        if flags is not None:
            current = flags
        if invisible is True:
            current |= FINDER_INVISIBLE
        elif invisible is False:
            current &= ~FINDER_INVISIBLE
        data["finder_flags"] = current
        self._save(path, data)
        return current