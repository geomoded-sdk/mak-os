#!/usr/bin/env python3
# =============================================================================
#  pineapplefs / checksums.py — camada BFS: checksums
#
#  BFS v2 — camada "checksums". Registra a integridade (sha256 + tamanho) de
#  cada arquivo em .bfsprivate/checksums/index.json e permite verificar o
#  volume (APFS-like, mas honesto: checagem por arquivo, sob demanda).
# =============================================================================
import hashlib
import json

from .constants import sha256_of


def sha256_zeros(size):
    """sha256 de `size` bytes zerados sem materializar o buffer gigante."""
    digest = hashlib.sha256()
    chunk = b"\x00" * (64 * 1024)
    remaining = size
    while remaining:
        take = chunk[: min(len(chunk), remaining)]
        digest.update(take)
        remaining -= len(take)
    return digest.hexdigest()


class ChecksumLayer:
    def __init__(self, volume):
        self.v = volume

    # ------------------------------------------------------------ internos
    def _index_path(self):
        return self.v.private / "checksums" / "index.json"

    def _load(self):
        if not self._index_path().exists():
            return {}
        return json.loads(self._index_path().read_text(encoding="utf-8"))

    def _save(self, index):
        self._index_path().write_text(
            json.dumps(index, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")

    # --------------------------------------------------------------- API
    def register(self, rel, data):
        """Registra (ou atualiza) o checksum do conteúdo lógico de um arquivo."""
        index = self._load()
        index[rel.replace("\\", "/")] = {
            "sha256": sha256_of(data),
            "size": len(data),
        }
        self._save(index)

    def register_zeros(self, rel, size):
        """Registra o checksum de um arquivo totalmente zerado (expandido)."""
        index = self._load()
        index[rel.replace("\\", "/")] = {
            "sha256": sha256_zeros(size),
            "size": size,
        }
        self._save(index)

    def verify(self):
        """Verifica a integridade dos arquivos registrados (APFS-like)."""
        index = self._load()
        results = {}
        for rel, meta in index.items():
            path = self.v.resolve(rel)
            if path is None or not path.exists():
                results[rel] = "missing"
                continue
            digest = sha256_of(self.v.read(rel))
            results[rel] = "ok" if digest == meta["sha256"] else "corrupt"
        return results