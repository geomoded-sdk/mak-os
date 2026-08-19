# BFS — Pineapple File System

> Sistema de arquivos de usuário baseado em **exFAT** com os recursos que a
> Apple oferece no **APFS/HFS+** — no mesmo espírito: `._*` (AppleDouble),
> `.bfsprivate`, snapshots, clones copy-on-write, arquivos esparsos
> ("expandidos"), xattrs, case-insensitive e os artefatos que o macOS cria
> no volume.

O kernel Linux já monta volumes exFAT; o BFS roda **por cima** dele e traz a
camada "esperta" estilo Apple para qualquer volume exFAT (pendrive, cartão,
partição de dados).

## O que ele faz (espelhando o macOS)

| Recurso                 | Como o macOS faz              | No BFS                                  |
|-------------------------|-------------------------------|-----------------------------------------|
| Atributos por arquivo   | `._<nome>` (AppleDouble)      | `._<nome>` idêntico, no exFAT           |
| Metadados do volume     | `.Spotlight-V100`, `.fseventsd`, `.Trashes`, `.DS_Store` | cria todos no `init` + `.bfsprivate` |
| Pasta de metadados      | —                             | `.bfsprivate/` (uuid, snapshots, clones, checksums) |
| Snapshots (APFS)        | `tmutil` / APFS snapshots     | `snapshot` / `restore` em `.bfsprivate/snapshots/` |
| Clones (APFS)           | `clonefile` copy-on-write     | `clone` (dedup por sha256 + hardlink, COW no `write`) |
| Arquivos expandidos     | APFS sparse files (extents)   | `expand` / `put-sparse` (container `PFSS01`, só blocos com dados) |
| Case-insensitive        | APFS/HFS+ (padrão)            | resolução de nomes case-insensitive     |
| Integridade             | APFS checksums                | `verify` (sha256 em `.bfsprivate/checksums/`) |
| Zip estilo macOS        | `ditto -c -k --keepParent` + `__MACOSX/` (nome da Apple) | `pack` cria `_PINEAPPLE/` com `._*` e `unpack` restaura |

## Como usar

Formatar um volume BFS (cria `.bfsprivate` + os artefatos do macOS):

```bash
python3 Scripts/pineapplefs.py init /media/PENDRIVE --name "Pineapple OS"
```

Escrever arquivos e atributos (o sidecar `._*` é criado automaticamente):

```bash
pineapplefs put  /media/PENDRIVE Fotos/foto.jpg ./foto.jpg
pineapplefs setxattr /media/PENDRIVE Fotos/foto.jpg \
    com.apple.metadata:kMDItemTitle "Minha foto"
pineapplefs invisible /media/PENDRIVE Fotos/foto.jpg on   # oculta no Finder
pineapplefs sync /media/PENDRIVE                          # gera todos os ._*
```

Recursos estilo APFS:

```bash
pineapplefs clone   /media/PENDRIVE foto.jpg foto-copia.jpg   # COW, dedup
pineapplefs write   /media/PENDRIVE foto-copia.jpg novo.jpg   # quebra o clone
pineapplefs snapshot /media/PENDRIVE antes-de-formatar
pineapplefs restore  /media/PENDRIVE antes-de-formatar
pineapplefs expand   /media/PENDRIVE disco.img 1073741824     # esparso expandido
pineapplefs verify   /media/PENDRIVE
```

Zip estilo macOS (com `_PINEAPPLE/` + sidecars `._*`, e restauração):

```bash
pineapplefs pack   /media/PENDRIVE -o pacote.zip
pineapplefs unpack /outra-pasta pacote.zip
```

Lista completa: `python3 Scripts/pineapplefs.py --help`.

## Estrutura

```
Filesystem/pineapplefs/
├── __init__.py        # pacote BFS
├── bfs.py             # BFSVolume: volume, xattrs, clones, snapshots, sparse, verify
├── appledouble.py     # formato AppleDouble "._*" (xattrs + Finder Info + resource fork)
├── sparse.py          # arquivos esparsos/expandidos (container PFSS01, extents)
└── archive.py         # pack/unpack de .zip estilo macOS (pasta _PINEAPPLE)
Scripts/pineapplefs.py # CLI
tests/test_appledouble.py, tests/test_bfs.py
```

## Formato AppleDouble (sidecars `._*`)

Mesmo formato real da Apple (`magic 0x00051607`, versão 2): grava xattrs
(entrada `0x8000`), Finder Info (entrada 8 — invisível, ícone, etc.), resource
fork (entrada 2) e nome Unicode (entrada 15). Qualquer leitor AppleDouble do
macOS/Linux lê os sidecars gerados pelo BFS.

## Limitações honestas

- O BFS é uma camada de usuário sobre o exFAT do kernel: clones usam hardlinks
  e a gravação faz copy-on-write no nível de arquivo (não de bloco, como o APFS).
- Snapshots copiam arquivos (imutáveis de verdade); clones são deduplicados por
  hardlink no armazenamento `.bfsprivate/clones/`.
- Testado na suíte (`tests/test_bfs.py` e `tests/test_appledouble.py`).