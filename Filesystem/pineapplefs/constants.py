#!/usr/bin/env python3
# =============================================================================
#  pineapplefs / constants.py — constantes e helpers compartilhados do BFS v2
#
#  Este módulo não importa nenhum outro do pacote: é a base que todas as
#  camadas usam sem criar importação circular.
# =============================================================================
import datetime
import hashlib
import os
import uuid as _uuid
from pathlib import Path

MAGIC = "BFS"
FORMAT = "bfs-overlay"
FORMAT_VERSION = 2

# Pilha de camadas do BFS v2 (a ordem abaixo é a declarada no volume.info).
# O BFS NÃO finge ser APFS: é um overlay de usuário próprio sobre o filesystem
# do kernel (exFAT etc.), inspirado em recursos que existem em vários sistemas.
LAYERS = ("xattrs", "finder", "snapshots", "clones", "checksums", "sparse")

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
    """Dotfiles são ocultos por padrão na camada de apresentação Pineapple."""
    return name.startswith(".") and name not in SYSTEM_NAMES


def filesystem_type(path):
    """Devolve o tipo do filesystem Linux montado (exFAT etc.), se possível."""
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


def new_uuid():
    return str(_uuid.uuid4())


def now_utc_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()