#!/usr/bin/env python3
# =============================================================================
#  pineapplefs / clones.py — camada BFS: clones copy-on-write
#
#  BFS v2 — camada "clones". Clones de arquivo com COW (copy-on-write) e
#  deduplicação real por conteúdo: o conteúdo vive em um blob único em
#  .bfsprivate/clones/ e cada path vira um hardlink desse blob. Gravar por
#  cima de um clone quebra o link antes da escrita (como o APFS clonefile,
#  mas honesto: no nível de arquivo, não de bloco).
# =============================================================================
import json
import os
import shutil


class CloneLayer:
    def __init__(self, volume):
        self.v = volume

    # ------------------------------------------------------------ internos
    def _registry_path(self):
        return self.v.private / "clones" / "registry.json"

    def _ensure_registry(self):
        if not self._registry_path().exists():
            self._registry_path().write_text("{}\n", encoding="utf-8")

    def registry(self):
        if not self._registry_path().exists():
            return {}
        return json.loads(self._registry_path().read_text(encoding="utf-8"))

    def save_registry(self, reg):
        self._registry_path().write_text(
            json.dumps(reg, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")

    def blob_path(self, digest):
        return self.v.private / "clones" / digest

    # --------------------------------------------------------------- clone
    def clone(self, rel_src, rel_dst):
        """Clona `rel_src` em `rel_dst` sem duplicar dados: ambos passam a
        referenciar o mesmo blob (hardlink), registrado em .bfsprivate/clones.
        Modificar um deles (write) quebra o link — copy-on-write, como no APFS."""
        src = self.v.resolve(rel_src)
        if src is None or not src.is_file():
            raise FileNotFoundError(rel_src)
        dst = self.v.resolve_or(rel_dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        from .constants import sha256_of
        digest = sha256_of(data)
        blob = self.blob_path(digest)
        if not blob.exists():
            blob.write_bytes(data)
        reg = self.registry()
        paths = reg.setdefault(digest, [])
        for rel in (rel_src, rel_dst):
            rel = rel.replace("\\", "/")
            if rel not in paths:
                paths.append(rel)
        self.save_registry(reg)
        # converte src e dst em hardlinks do blob (dedup real de dados)
        try:
            src.unlink()
            os.link(blob, src)
            if dst.exists():
                dst.unlink()
            os.link(blob, dst)
        except OSError:
            if not dst.exists():
                shutil.copyfile(blob, dst)
        return digest

    def cow_break(self, path, rel):
        """Quebra o link de clone antes de uma escrita (copy-on-write):
        copia o conteúdo atual para um inode independente, senão a gravação
        alteraria os outros clones (que compartilham o hardlink)."""
        reg = self.registry()
        rel = rel.replace("\\", "/")
        for digest, paths in list(reg.items()):
            if rel in paths:
                paths.remove(rel)
                if not paths:
                    reg.pop(digest, None)
                    self.blob_path(digest).unlink(missing_ok=True)
                self.save_registry(reg)
                tmp = path.with_name(path.name + ".cowtmp")
                shutil.copy2(path, tmp)
                path.unlink()
                os.replace(tmp, path)
                break

    def refcount(self, rel):
        """Quantas referências (paths) um clone tem — 0 se não for clone."""
        path = self.v.resolve(rel)
        if path is None or not path.exists():
            return 0
        from .constants import sha256_of
        digest = sha256_of(path.read_bytes())
        paths = self.registry().get(digest, [])
        return len(paths)

    def unlink(self, rel):
        """Remove um arquivo; se for clone, libera a referência (dedup)."""
        path = self.v.resolve(rel)
        if path is None or not path.exists():
            return False
        rel = rel.replace("\\", "/")
        reg = self.registry()
        for digest, paths in list(reg.items()):
            if rel in paths:
                paths.remove(rel)
                if not paths:
                    reg.pop(digest, None)
                    self.blob_path(digest).unlink(missing_ok=True)
                self.save_registry(reg)
                break
        path.unlink()
        sp = self.v.sidecar_path(path)
        if sp.exists():
            sp.unlink(missing_ok=True)
        return True