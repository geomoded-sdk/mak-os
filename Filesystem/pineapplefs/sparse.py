#!/usr/bin/env python3
# =============================================================================
#  pineapplefs / sparse.py — arquivos esparsos e "expandidos" (extents)
#
#  O BFS suporta arquivos esparsos no estilo APFS: apenas os blocos com dados
#  são gravados ("expandido"), e os buracos são preenchidos com zeros na
#  leitura. Formato de container proprietário, sem dependências externas:
#
#    magic  "PFSS01"        (6 bytes)
#    version  u32           (1)
#    block    u32           (tamanho do bloco, padrão 4096)
#    size     u64           (tamanho lógico do arquivo)
#    nextents u32
#    extents  (start u32, count u32) * nextents
#    payloads: blocos de dados concatenados (bloco final trunca em `size`)
# =============================================================================
import struct

SPARSE_MAGIC = b"PFSS01"
SPARSE_VERSION = 1


def sparse_from_bytes(data, block=4096):
    """Codifica `data` como container esparso (só grava blocos não-nulos)."""
    data = bytes(data)
    size = len(data)
    n = (size + block - 1) // block
    extents = []
    i = 0
    while i < n:
        chunk = data[i * block:(i + 1) * block]
        if chunk == b"\x00" * len(chunk):
            i += 1
            continue
        start = i
        payload = bytearray()
        while i < n:
            c = data[i * block:(i + 1) * block]
            if c == b"\x00" * len(c):
                break
            payload += c + b"\x00" * (block - len(c))
            i += 1
        extents.append((start, i - start, bytes(payload)))
    header = (
        SPARSE_MAGIC
        + struct.pack(">IIQI", SPARSE_VERSION, block, size, len(extents))
    )
    for start, count, _ in extents:
        header += struct.pack(">II", start, count)
    body = b"".join(p for _, _, p in extents)
    return header + body


def sparse_zero(size, block=4096):
    """Container esparso de `size` bytes totalmente zerado (sem extents)."""
    return SPARSE_MAGIC + struct.pack(">IIQI", SPARSE_VERSION, block, size, 0)


def sparse_to_bytes(data):
    """Devolve os bytes reais. Se `data` não for um container esparso,
    retorna os bytes originais (arquivos normais)."""
    if not data.startswith(SPARSE_MAGIC):
        return data
    off = len(SPARSE_MAGIC)
    version, block, size, n = struct.unpack(">IIQI", data[off:off + 20])
    off += 20
    extents = []
    for _ in range(n):
        start, count = struct.unpack(">II", data[off:off + 8])
        off += 8
        extents.append((start, count))
    out = bytearray(size)
    for start, count in extents:
        for b in range(count):
            pos = (start + b) * block
            take = min(block, size - pos)
            if take <= 0:
                break
            out[pos:pos + take] = data[off:off + take]
            off += block
    return bytes(out)


def logical_size(data):
    """Tamanho lógico: para esparso, o campo `size`; senão, o tamanho real."""
    if data.startswith(SPARSE_MAGIC):
        return struct.unpack(">Q", data[len(SPARSE_MAGIC) + 4 + 4:][:8])[0]
    return len(data)


class SparseLayer:
    """Camada BFS "sparse": representação esparsa/expandida de arquivos.

    Só os blocos com dados são gravados no container PFSS01; os buracos viram
    zeros na leitura (o "arquivo expandido" do Canopy). A camada de checksums
    registra a integridade do conteúdo LÓGICO (incluindo os zeros).
    """

    def __init__(self, volume):
        self.v = volume

    def expand(self, rel, size, block=4096):
        """Cria um arquivo esparso 'expandido' com `size` bytes lógicos."""
        path = self.v.resolve_or(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(sparse_zero(size, block))
        return path

    def put(self, rel, data, block=4096):
        """Grava `data` como arquivo esparso (só blocos com dados)."""
        path = self.v.resolve_or(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(sparse_from_bytes(data, block))
        return path

    def decode(self, raw):
        """Devolve os bytes reais de um arquivo (desfazendo esparso)."""
        return sparse_to_bytes(raw)

    def size(self, raw):
        """Tamanho lógico de um arquivo (esparso ou normal)."""
        return logical_size(raw)