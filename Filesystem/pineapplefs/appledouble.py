#!/usr/bin/env python3
# =============================================================================
#  pineapplefs / appledouble.py — formato AppleDouble (arquivos "._")
#
#  O macOS grava um arquivo "._<nome>" ao lado de cada arquivo quando o volume
#  não suporta os atributos do HFS/APFS (ex.: exFAT, FAT, SMB). Esse arquivo
#  guarda: atributos estendidos (xattrs), Finder Info (invisível, ícone, etc.)
#  e o resource fork.
#
#  O Pineapple OS replica esse comportamento no BFS (Pineapple File System,
#  camada de usuário sobre exFAT): cada arquivo pode ter um sidecar "._*"
#  compatível com o formato real da Apple (magic 0x00051607).
#
#  Referência: AppleDouble / AppleSingle (Inside Macintosh: Files).
#  Sem dependências externas.
# =============================================================================
import struct

MAGIC = 0x00051607        # AppleDouble magic
VERSION = 0x00020000      # versão 2.0

# IDs de entrada padrão (AppleDouble)
ID_DATA_FORK = 1
ID_RESOURCE_FORK = 2
ID_REAL_NAME = 3
ID_COMMENT = 4
ID_FINDER_INFO = 8
ID_UNICODE_NAME = 15
# extensão: atributos estendidos (a Apple usa 0x00008000)
ID_XATTR = 0x00008000

# Finder Flags relevantes (campo de 16 bits do Finder Info)
FINDER_INVISIBLE = 0x4000     # kIsInvisible
FINDER_INITED = 0x0100        # kHasBeenInited (extended flags)

# resource fork aparece como xattr "com.apple.ResourceFork" (como no macOS)
XATTR_RESOURCE_FORK = "com.apple.ResourceFork"


def encode(entries):
    """Codifica um dict {entry_id: payload} em um arquivo AppleDouble."""
    items = sorted(entries.items(), key=lambda kv: kv[0])
    n = len(items)
    header = struct.pack(">II", MAGIC, VERSION) + bytes(16) + struct.pack(">H", n)
    offset = 26 + 12 * n
    descriptors = b""
    payloads = b""
    for eid, data in items:
        descriptors += struct.pack(">III", eid, offset, len(data))
        payloads += data
        offset += len(data)
    return header + descriptors + payloads


def decode(data):
    """Decodifica um AppleDouble em um dict {entry_id: payload}."""
    if len(data) < 26:
        raise ValueError("AppleDouble muito curto")
    magic, version = struct.unpack(">II", data[:8])
    if magic != MAGIC:
        raise ValueError("não é um arquivo AppleDouble")
    n = struct.unpack(">H", data[24:26])[0]
    entries = {}
    for i in range(n):
        eid, off, ln = struct.unpack(">III", data[26 + 12 * i:38 + 12 * i])
        entries[eid] = data[off:off + ln]
    return entries


# ---------------------------------------------------------------------------
#  Payloads das entradas
# ---------------------------------------------------------------------------
def encode_xattrs(xattrs):
    """xattrs -> payload da entrada ID_XATTR (contador + pares nome/valor)."""
    out = struct.pack(">I", len(xattrs))
    for name, value in xattrs.items():
        nb = name.encode("utf-8")
        out += struct.pack(">I", len(nb)) + nb
        out += struct.pack(">I", len(value)) + value
    return out


def decode_xattrs(payload):
    """Payload da entrada ID_XATTR -> dict {nome: valor_bytes}."""
    if len(payload) < 4:
        return {}
    count = struct.unpack(">I", payload[:4])[0]
    off = 4
    xattrs = {}
    for _ in range(count):
        if off + 4 > len(payload):
            break
        nl = struct.unpack(">I", payload[off:off + 4])[0]
        off += 4
        name = payload[off:off + nl].decode("utf-8", errors="replace")
        off += nl
        vl = struct.unpack(">I", payload[off:off + 4])[0]
        off += 4
        xattrs[name] = payload[off:off + vl]
        off += vl
    return xattrs


def finder_info_bytes(flags=0, ext_flags=FINDER_INITED):
    """32 bytes do Finder Info (flags + campo estendido)."""
    return (
        struct.pack(">H", flags)          # FinderFlags
        + struct.pack(">I", 0)            # localização do ícone
        + bytes(2)                        # reservado
        + struct.pack(">H", ext_flags)    # extended FinderFlags
        + bytes(6)                        # reservado
        + struct.pack(">I", 0)            # putaway folder id
        + struct.pack(">H", 0)            # server id
        + bytes(10)                       # reservado
    )


def encode_unicode_name(name):
    """Entrada ID_UNICODE_NAME: contador de unidades UTF-16BE + texto."""
    raw = name.encode("utf-16-be")
    return struct.pack(">I", len(raw) // 2) + raw


def decode_unicode_name(payload):
    n = struct.unpack(">I", payload[:4])[0]
    return payload[4:4 + 2 * n].decode("utf-16-be", errors="replace")


# ---------------------------------------------------------------------------
#  Montagem/leitura de sidecar "._"
# ---------------------------------------------------------------------------
def build_sidecar(xattrs=None, finder_flags=0, resource_fork=None,
                  unicode_name=None):
    """Monta um arquivo AppleDouble completo (o conteúdo do sidecar '._*')."""
    entries = {}
    if resource_fork is not None:
        entries[ID_RESOURCE_FORK] = resource_fork
    entries[ID_FINDER_INFO] = finder_info_bytes(finder_flags)
    if unicode_name is not None:
        entries[ID_UNICODE_NAME] = encode_unicode_name(unicode_name)
    xattrs = dict(xattrs or {})
    if XATTR_RESOURCE_FORK in xattrs:
        entries[ID_RESOURCE_FORK] = xattrs.pop(XATTR_RESOURCE_FORK)
    if xattrs:
        entries[ID_XATTR] = encode_xattrs(xattrs)
    return encode(entries)


def parse_sidecar(data):
    """Lê um sidecar '._*' e devolve {finder_flags, xattrs, resource_fork,
    unicode_name}."""
    entries = decode(data)
    result = {}
    fi = entries.get(ID_FINDER_INFO)
    if fi:
        result["finder_flags"] = struct.unpack(">H", fi[:2])[0]
    result["xattrs"] = decode_xattrs(entries.get(ID_XATTR, b""))
    if ID_RESOURCE_FORK in entries:
        result["resource_fork"] = entries[ID_RESOURCE_FORK]
    if ID_UNICODE_NAME in entries:
        result["unicode_name"] = decode_unicode_name(entries[ID_UNICODE_NAME])
    return result


def finder_flags(data):
    return parse_sidecar(data).get("finder_flags", 0)