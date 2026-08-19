#!/usr/bin/env python3
# =============================================================================
#  pineapplefs — Pineapple File System (BFS)
#
#  Sistema de arquivos de usuário baseado em exFAT com recursos estilo APFS/
#  HFS+ da Apple: sidecars AppleDouble "._", snapshots, clones copy-on-write,
#  arquivos esparsos ("expandidos"), xattrs, case-insensitive, checksums e os
#  artefatos que o macOS cria no volume (.bfsprivate, .Spotlight-V100,
#  .fseventsd, .Trashes, .DS_Store, _PINEAPPLE em .zip).
# =============================================================================
__version__ = "0.1.0"
__all__ = [
    "BFSVolume",
    "appledouble",
    "sparse",
    "archive",
]

from .appledouble import build_sidecar, parse_sidecar  # noqa: F401
from .archive import pack, unpack, has_pineapple_folder  # noqa: F401
from .bfs import BFSVolume, SYSTEM_NAMES, is_sidecar  # noqa: F401
from .sparse import (  # noqa: F401
    sparse_from_bytes,
    sparse_to_bytes,
    sparse_zero,
    logical_size,
)