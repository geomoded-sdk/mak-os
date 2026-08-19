#!/usr/bin/env python3
# =============================================================================
#  pineapplefs / core.py — BFS v2: núcleo do volume e pilha de camadas
#
#  O BFS (Pineapple File System) é um sistema de arquivos de usuário sobre o
#  filesystem do kernel (exFAT e outros). O volume real é o exFAT; o BFS roda
#  POR CIMA dele como uma camada de metadados explícita:
#
#    exFAT (ou outro filesystem do kernel)
#      └── BFS metadata layer  (overlay de usuário)
#            ├── xattrs      → metadata.py   (atributos extendidos AppleDouble)
#            ├── finder      → finder.py     (Finder Info, tags, ícone, comentário)
#            ├── snapshots   → snapshots.py  (estados imutáveis do volume)
#            ├── clones      → clones.py     (clones copy-on-write + dedup)
#            ├── checksums   → checksums.py  (integridade sha256)
#            └── sparse      → sparse.py     (representação esparsa/expandida)
#
#  O BFS NÃO finge ser APFS: é um overlay próprio, inspirado em recursos que
#  existem em vários sistemas de arquivos. Cada camada é um módulo separado e
#  a ordem da pilha é declarada no volume.info do volume.
# =============================================================================
import os
import shutil

from .checksums import ChecksumLayer
from .clones import CloneLayer
from .constants import (
    FORMAT,
    FORMAT_VERSION,
    LAYERS,
    MAGIC,
    SYSTEM_NAMES,
    filesystem_type,
    is_sidecar,
    new_uuid,
    now_utc_iso,
)
from .finder import FinderLayer
from .metadata import XattrLayer
from .snapshots import SnapshotLayer
from .sparse import SparseLayer

__all__ = [
    "BFSVolume",
    "FORMAT",
    "FORMAT_VERSION",
    "LAYERS",
    "MAGIC",
    "SYSTEM_NAMES",
    "is_sidecar",
]


class BFSVolume:
    """Volume BFS: núcleo (mount, init, caminhos, dados) + camadas de metadados.

    As camadas ficam expostas como atributos públicos para quem quiser acessar
    um recurso específico diretamente:

        vol.xattrs          # camada de atributos estendidos
        vol.finder          # camada de metadados do Finder
        vol.snapshots_layer # camada de snapshots
        vol.clones          # camada de clones copy-on-write
        vol.checksums       # camada de integridade
        vol.sparse          # camada de representação esparsa

    A API do BFS v1 continua funcionando (put, clone, snapshot, verify, …)
    delegando para as camadas.
    """

    def __init__(self, root, case_insensitive=True):
        from pathlib import Path

        self.root = Path(root)
        self.private = self.root / ".bfsprivate"
        self.case_insensitive = case_insensitive

        # pilha de camadas (ordem declarada em LAYERS)
        self.xattrs = XattrLayer(self)
        self.finder = FinderLayer(self)
        self.snapshots_layer = SnapshotLayer(self)
        self.clones = CloneLayer(self)
        self.checksums = ChecksumLayer(self)
        self.sparse = SparseLayer(self)

    # ------------------------------------------------------------------
    #  Inicialização do volume (exFAT + camada de metadados BFS)
    # ------------------------------------------------------------------
    def init(self, name="Pineapple OS"):
        """Adiciona a camada BFS sem formatar nem apagar o volume real."""
        self.root.mkdir(parents=True, exist_ok=True)
        self.private.mkdir(exist_ok=True)
        for sub in ("snapshots", "clones", "checksums", "trash", "sparse"):
            (self.private / sub).mkdir(exist_ok=True)

        info_path = self.private / "volume.info"
        if not info_path.exists():
            info = {
                "magic": MAGIC,
                "name": name,
                "format": FORMAT,
                "filesystem": filesystem_type(self.root),
                "version": FORMAT_VERSION,
                "layers": list(LAYERS),
                "case_insensitive": self.case_insensitive,
                "uuid": new_uuid(),
                "created": now_utc_iso(),
            }
            info_path.write_text(
                json_dumps(info) + "\n", encoding="utf-8")

        self.clones._ensure_registry()

        # artefatos que o macOS cria no volume (exFAT / APFS)
        (self.root / ".Spotlight-V100").mkdir(exist_ok=True)
        (self.root / ".fseventsd").mkdir(exist_ok=True)
        (self.root / ".Trashes").mkdir(exist_ok=True)
        (self.root / ".Trashes" / "pineapple").mkdir(exist_ok=True)
        (self.root / ".DS_Store").touch(exist_ok=True)
        (self.root / ".metadata_never_index").touch(exist_ok=True)
        localized = self.root / ".localized"
        if not localized.exists():
            localized.write_text(name + "\n", encoding="utf-8")
        (self.root / ".fseventsd" / "pineapple.events").touch(exist_ok=True)
        return self

    def info(self):
        info_path = self.private / "volume.info"
        if not info_path.exists():
            return {"magic": MAGIC, "format": FORMAT, "layers": list(LAYERS)}
        info = json_loads(info_path.read_text(encoding="utf-8"))
        info.setdefault("filesystem", filesystem_type(self.root))
        info.setdefault("layers", list(LAYERS))
        return info

    def record_event(self, action, rel):
        """Registra uma alteração no journal append-only (.fseventsd)."""
        event_log = self.root / ".fseventsd" / "pineapple.events"
        event_log.parent.mkdir(exist_ok=True)
        import datetime
        with event_log.open("a", encoding="utf-8") as stream:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            stream.write(json_dumps({"time": timestamp, "action": action, "path": rel}) + "\n")

    def trash(self, rel):
        path = self.resolve(rel)
        if path is None or not path.exists():
            return False
        target = self.root / ".Trashes" / "pineapple" / path.name
        counter = 1
        while target.exists():
            target = target.with_name(f"{path.name}.{counter}")
            counter += 1
        shutil.move(str(path), str(target))
        self.record_event("trash", rel)
        return True

    # ------------------------------------------------------------------
    #  Resolução de caminhos (case-insensitive como APFS/HFS+)
    # ------------------------------------------------------------------
    def resolve(self, rel):
        """Devolve o Path real (respeitando case-insensitive) ou None."""
        parts = [p for p in rel.replace("\\", "/").split("/") if p not in ("", ".")]
        cur = self.root
        for p in parts:
            if p == "..":
                continue
            if self.case_insensitive:
                hit = None
                try:
                    names = os.listdir(cur)
                except OSError:
                    return None
                low = p.lower()
                for n in names:
                    if n.lower() == low:
                        hit = cur / n
                        break
                if hit is None:
                    return None
                cur = hit
            else:
                cur = cur / p
                if not os.path.lexists(cur):
                    return None
        return cur

    def resolve_or(self, rel):
        """Igual a resolve(), mas devolve o caminho literal se não existir."""
        found = self.resolve(rel)
        return found if found is not None else (self.root / rel)

    def is_system(self, path):
        try:
            return path.name in SYSTEM_NAMES
        except OSError:
            return True

    def walk_files(self, include_sidecars=True):
        """Itera os arquivos de dados do volume (ignora sistema/.bfsprivate)."""
        for base, dirs, files in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in SYSTEM_NAMES]
            base_p = type(self.root)(base)
            for fn in files:
                if fn in SYSTEM_NAMES:
                    continue
                if is_sidecar(fn) and not include_sidecars:
                    continue
                yield base_p / fn

    # ------------------------------------------------------------------
    #  Plumb do sidecar "._*" (usado pelas camadas de metadados)
    # ------------------------------------------------------------------
    def sidecar_path(self, path):
        return path.parent / ("._" + path.name)

    # ------------------------------------------------------------------
    #  Dados do arquivo (núcleo) — delega para as camadas sparse/checksums
    # ------------------------------------------------------------------
    def put(self, rel, data, xattrs=None, finder_flags=0):
        """Escreve `data` como arquivo do volume (com sidecar opcional)."""
        path = self.resolve_or(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.checksums.register(rel, data)
        if xattrs or finder_flags:
            self.xattrs.write_entry(path, {
                "xattrs": xattrs or {},
                "finder_flags": finder_flags,
            })
        return path

    def read(self, rel):
        """Lê os bytes reais de um arquivo (desfazendo esparso)."""
        path = self.resolve(rel)
        if path is None or not path.exists():
            return None
        return self.sparse.decode(path.read_bytes())

    def write(self, rel, data):
        """Escrita com copy-on-write: se o arquivo for um clone, desfaz o
        link antes de gravar (como o APFS)."""
        path = self.resolve_or(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.clones.cow_break(path, rel)
        path.write_bytes(data)
        self.checksums.register(rel, data)
        return path

    def size(self, rel):
        """Tamanho lógico do arquivo (desfaz esparso, como o APFS)."""
        path = self.resolve(rel)
        if path is None or not path.exists():
            return None
        data = path.read_bytes()
        if data[:6] == b"PFSS01":
            return self.sparse.size(data)
        return path.stat().st_size

    def expand(self, rel, size, block=4096):
        """Cria um arquivo esparso 'expandido' (camada sparse) + checksum."""
        self.sparse.expand(rel, size, block)
        self.checksums.register_zeros(rel, size)
        return self.resolve_or(rel)

    def put_sparse(self, rel, data, block=4096):
        """Grava `data` como arquivo esparso (só blocos com dados)."""
        path = self.sparse.put(rel, data, block)
        self.checksums.register(rel, data)
        return path

    # ------------------------------------------------------------------
    #  Delegações para as camadas (API do BFS v1 preservada)
    # ------------------------------------------------------------------
    # xattrs (camada metadata)
    def set_xattr(self, rel, name, value):
        return self.xattrs.set(rel, name, value)

    def get_xattr(self, rel, name):
        return self.xattrs.get(rel, name)

    def list_xattrs(self, rel):
        return self.xattrs.list(rel)

    def del_xattr(self, rel, name):
        return self.xattrs.delete(rel, name)

    # finder (camada finder)
    def set_finder(self, rel, invisible=None, flags=None):
        return self.finder.set_finder(rel, invisible=invisible, flags=flags)

    def is_invisible(self, rel):
        return self.finder.is_invisible(rel)

    def sync_sidecars(self):
        return self.finder.sync_sidecars()

    # clones (camada clones)
    def clone(self, rel_src, rel_dst):
        return self.clones.clone(rel_src, rel_dst)

    def refcount(self, rel):
        return self.clones.refcount(rel)

    def unlink(self, rel):
        return self.clones.unlink(rel)

    # snapshots (camada snapshots)
    def snapshot(self, name):
        return self.snapshots_layer.create(name)

    def snapshots(self):
        return self.snapshots_layer.list()

    def restore(self, name):
        return self.snapshots_layer.restore(name)

    # checksums (camada checksums)
    def verify(self):
        return self.checksums.verify()


def json_dumps(obj):
    import json
    return json.dumps(obj, indent=2, ensure_ascii=False)


def json_loads(text):
    import json
    return json.loads(text)