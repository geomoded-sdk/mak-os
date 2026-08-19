#!/usr/bin/env python3
# =============================================================================
#  pineapplefs — CLI do BFS (Pineapple File System)
#
#  Uso:  python3 Scripts/pineapplefs.py <comando> [args...]
#
#  Comandos:
#    init <dir>              formata um volume BFS (cria .bfsprivate + artefatos)
#    status <dir>            mostra info do volume
#    put <dir> <rel> <arquivo>   grava um arquivo no volume
#    read <dir> <rel>        imprime os bytes reais (desfaz esparso)
#    write <dir> <rel> <arquivo> grava com copy-on-write (quebra clone)
#    size <dir> <rel>        tamanho lógico (expansível/esparso)
#    expand <dir> <rel> <size>   cria arquivo esparso expandido
#    put-sparse <dir> <rel> <arquivo>  grava esparso (só blocos com dados)
#    setxattr <dir> <rel> <nome> <valor>
#    getxattr <dir> <rel> <nome>
#    listxattr <dir> <rel>
#    delxattr <dir> <rel> <nome>
#    invisible <dir> <rel> [on|off]   Finder Info (mostrar/ocultar no Finder)
#    sync <dir>              gera os sidecars "._*" de todos os arquivos
#    clone <dir> <src> <dst>     clone copy-on-write (APFS)
#    refcount <dir> <rel>    nº de referências de um clone
#    unlink <dir> <rel>      remove liberando a referência de clone
#    snapshot <dir> <nome>   cria snapshot (APFS)
#    snapshots <dir>         lista snapshots
#    restore <dir> <nome>    restaura snapshot
#    verify <dir>            verifica checksums (integridade)
#    pack <dir> -o out.zip   zip estilo macOS (com _PINEAPPLE + ._ sidecars)
#    unpack <dir> in.zip     extrai e aplica os sidecars
# =============================================================================
import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _candidate in (
    os.path.join(_HERE, "..", "Filesystem"),          # no repositório
    "/usr/share/pineappleos/Filesystem",              # instalado no sistema
):
    if os.path.isdir(_candidate):
        sys.path.insert(0, _candidate)
        break

from pineapplefs import (  # noqa: E402
    BFSVolume,
    SpotlightIndex,
    archive,
    sparse,
)


def _vol(args):
    return BFSVolume(args.dir).init()


def _read_file_or_dash(path):
    if path == "-":
        return sys.stdin.buffer.read()
    with open(path, "rb") as f:
        return f.read()


def cmd_init(args):
    BFSVolume(args.dir).init(args.name)
    print(f"volume BFS pronto em {args.dir} (overlay multi-filesystem)")
    print("criados: .bfsprivate, .Spotlight-V100, .fseventsd, .Trashes, .DS_Store, .metadata_never_index, .localized")


def cmd_spotlight_index(args):
    total, changed = SpotlightIndex(args.dir).rebuild()
    print(f"Spotlight indexado: {total} arquivos ({changed} atualizados)")


def cmd_spotlight_search(args):
    for path in SpotlightIndex(args.dir).search(args.query, args.limit):
        print(path)


def cmd_status(args):
    vol = BFSVolume(args.dir)
    print(json_dumps(vol.info()))


def cmd_put(args):
    _vol(args).put(args.rel, _read_file_or_dash(args.file))
    print("ok:", args.rel)


def cmd_read(args):
    data = _vol(args).read(args.rel)
    if data is None:
        sys.exit(f"arquivo não encontrado: {args.rel}")
    sys.stdout.buffer.write(data)


def cmd_write(args):
    _vol(args).write(args.rel, _read_file_or_dash(args.file))
    print("ok:", args.rel)


def cmd_size(args):
    n = _vol(args).size(args.rel)
    if n is None:
        sys.exit(f"arquivo não encontrado: {args.rel}")
    print(n)


def cmd_expand(args):
    _vol(args).expand(args.rel, int(args.size))
    print("expandido:", args.rel, "->", args.size, "bytes lógicos")


def cmd_put_sparse(args):
    _vol(args).put_sparse(args.rel, _read_file_or_dash(args.file))
    print("esparso:", args.rel)


def cmd_setxattr(args):
    _vol(args).set_xattr(args.rel, args.name, args.value.encode("utf-8"))
    print("xattr:", args.name, "=", args.value)


def cmd_getxattr(args):
    v = _vol(args).get_xattr(args.rel, args.name)
    if v is None:
        sys.exit(f"xattr não encontrado: {args.name}")
    sys.stdout.buffer.write(v)


def cmd_listxattr(args):
    for name in _vol(args).list_xattrs(args.rel):
        print(name)


def cmd_delxattr(args):
    if _vol(args).del_xattr(args.rel, args.name):
        print("removido:", args.name)
    else:
        sys.exit(f"xattr não encontrado: {args.name}")


def cmd_invisible(args):
    vol = _vol(args)
    if args.on_off is None:
        print("invisível" if vol.is_invisible(args.rel) else "visível")
    else:
        flags = vol.set_finder(args.rel, invisible=args.on_off == "on")
        print("finder_flags:", hex(flags))


def cmd_sync(args):
    n = _vol(args).sync_sidecars()
    print(f"{n} sidecars '._*' criados")


def cmd_clone(args):
    digest = _vol(args).clone(args.src, args.dst)
    print("clone:", args.dst, "->", digest[:12], "...")


def cmd_refcount(args):
    print(_vol(args).refcount(args.rel))


def cmd_unlink(args):
    if _vol(args).unlink(args.rel):
        print("removido:", args.rel)
    else:
        sys.exit(f"arquivo não encontrado: {args.rel}")


def cmd_snapshot(args):
    _vol(args).snapshot(args.name)
    print("snapshot:", args.name)


def cmd_snapshots(args):
    for s in _vol(args).snapshots():
        print(s)


def cmd_restore(args):
    n = _vol(args).restore(args.name)
    print(f"restaurados {n} arquivos do snapshot '{args.name}'")


def cmd_verify(args):
    results = _vol(args).verify()
    for rel, st in sorted(results.items()):
        print(f"{st:8} {rel}")
    bad = sum(1 for st in results.values() if st != "ok")
    print(f"{len(results)} verificados, {bad} com problema")
    if bad:
        sys.exit(1)


def cmd_pack(args):
    n = archive.pack(args.dir, args.out)
    print(f"empacotados {n} arquivos em {args.out} (com _PINEAPPLE + ._ sidecars)")


def cmd_unpack(args):
    n = archive.unpack(args.zip_path, args.dir)
    print(f"extraídos e {n} sidecars aplicados em {args.dir}")


def json_dumps(obj):
    import json
    return json.dumps(obj, indent=2, ensure_ascii=False)


def main():
    p = argparse.ArgumentParser(prog="pineapplefs", description="BFS — Pineapple File System (exFAT + recursos estilo APFS/HFS+)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(p_, name, help_, fn):
        sp = p_.add_parser(name, help=help_)
        sp.set_defaults(fn=fn)
        return sp

    add(sub, "init", "formata um volume BFS", cmd_init).add_argument("dir")
    sub.choices["init"].add_argument("--name", default="Pineapple OS")
    sp = add(sub, "spotlight-index", "indexa rapidamente um volume", cmd_spotlight_index)
    sp.add_argument("dir")
    sp = add(sub, "spotlight-search", "pesquisa no índice Spotlight", cmd_spotlight_search)
    sp.add_argument("dir")
    sp.add_argument("query")
    sp.add_argument("--limit", type=int, default=100)

    for c, h, fn in [
        ("status", "info do volume", cmd_status),
        ("put", "grava arquivo", cmd_put),
        ("read", "lê arquivo (desfaz esparso)", cmd_read),
        ("write", "grava com copy-on-write", cmd_write),
        ("size", "tamanho lógico", cmd_size),
        ("expand", "arquivo esparso expandido", cmd_expand),
        ("put-sparse", "grava esparso", cmd_put_sparse),
        ("sync", "gera sidecars ._*", cmd_sync),
        ("refcount", "refs de um clone", cmd_refcount),
        ("unlink", "remove liberando clone", cmd_unlink),
        ("snapshots", "lista snapshots", cmd_snapshots),
        ("verify", "verifica checksums", cmd_verify),
    ]:
        sp = add(sub, c, h, fn)
        sp.add_argument("dir")

    sp = sub.choices["put"]
    sp.add_argument("rel"); sp.add_argument("file")
    sp = sub.choices["read"]
    sp.add_argument("rel")
    sp = sub.choices["write"]
    sp.add_argument("rel"); sp.add_argument("file")
    sp = sub.choices["size"]
    sp.add_argument("rel")
    sp = sub.choices["expand"]
    sp.add_argument("rel"); sp.add_argument("size")
    sp = sub.choices["put-sparse"]
    sp.add_argument("rel"); sp.add_argument("file")
    sp = sub.choices["refcount"]
    sp.add_argument("rel")
    sp = sub.choices["unlink"]
    sp.add_argument("rel")

    sp = add(sub, "setxattr", "define xattr", cmd_setxattr)
    sp.add_argument("dir"); sp.add_argument("rel"); sp.add_argument("name"); sp.add_argument("value")
    sp = add(sub, "getxattr", "lê xattr", cmd_getxattr)
    sp.add_argument("dir"); sp.add_argument("rel"); sp.add_argument("name")
    sp = add(sub, "listxattr", "lista xattrs", cmd_listxattr)
    sp.add_argument("dir"); sp.add_argument("rel")
    sp = add(sub, "delxattr", "remove xattr", cmd_delxattr)
    sp.add_argument("dir"); sp.add_argument("rel"); sp.add_argument("name")
    sp = add(sub, "invisible", "Finder: mostra/oculta", cmd_invisible)
    sp.add_argument("dir"); sp.add_argument("rel"); sp.add_argument("on_off", nargs="?")

    sp = add(sub, "clone", "clone copy-on-write", cmd_clone)
    sp.add_argument("dir"); sp.add_argument("src"); sp.add_argument("dst")
    sp = add(sub, "snapshot", "cria snapshot", cmd_snapshot)
    sp.add_argument("dir"); sp.add_argument("name")
    sp = add(sub, "restore", "restaura snapshot", cmd_restore)
    sp.add_argument("dir"); sp.add_argument("name")

    sp = add(sub, "pack", "zip estilo macOS", cmd_pack)
    sp.add_argument("dir"); sp.add_argument("-o", "--out", required=True)
    sp = add(sub, "unpack", "extrai zip estilo macOS", cmd_unpack)
    sp.add_argument("dir"); sp.add_argument("zip_path")

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()