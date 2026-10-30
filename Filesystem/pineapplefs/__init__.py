#!/usr/bin/env python3
# =============================================================================
#  pineapplefs — PNFS (Pineapple Native File System)
#
#  Sistema de arquivos do Pineapple OS: overlay sobre o filesystem do kernel
#  (exFAT e outros) com uma camada de metadados explícita no módulo
#  .bfsprivate:
#
#    exFAT ↓ PNFS metadata layer (.bfsprivate)
#      ├── xattrs      → metadata.py
#      ├── finder      → finder.py
#      ├── snapshots   → snapshots.py
#      ├── clones      → clones.py
#      ├── checksums   → checksums.py
#      └── sparse      → sparse.py
#
#  O PNFS NÃO finge ser APFS: é um overlay próprio, inspirado em recursos que
#  existem em vários sistemas de arquivos (sidecars "._*", .bfsprivate,
#  snapshots, clones COW, arquivos esparsos, checksums, case-insensitive e os
#  artefatos que o macOS cria no volume).
# =============================================================================
__version__ = "2.0.0"
__all__ = [
    "PNFSVolume",
    "BFSVolume",
    "XattrLayer",
    "FinderLayer",
    "SnapshotLayer",
    "CloneLayer",
    "ChecksumLayer",
    "SparseLayer",
    "LAYERS",
    "appledouble",
    "sparse",
    "archive",
    "SpotlightIndex",
]

from .appledouble import build_sidecar, parse_sidecar  # noqa: F401
from .archive import pack, unpack, has_pineapple_folder  # noqa: F401
from .checksums import ChecksumLayer  # noqa: F401
from .clones import CloneLayer  # noqa: F401
from .constants import LAYERS, SYSTEM_NAMES, is_sidecar  # noqa: F401
from .core import PNFSVolume  # noqa: F401
from .finder import FinderLayer  # noqa: F401
from .metadata import XattrLayer  # noqa: F401
from .snapshots import SnapshotLayer  # noqa: F401
from .sparse import (  # noqa: F401
    SparseLayer,
    sparse_from_bytes,
    sparse_to_bytes,
    sparse_zero,
    logical_size,
)
from .spotlight import SpotlightIndex  # noqa: F401

# Compat: nome antigo (BFS) mantido como alias — o filesystem é PNFS.
BFSVolume = PNFSVolume