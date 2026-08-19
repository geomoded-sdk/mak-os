# BFS v2 — Pineapple File System

> Sistema de arquivos de usuário baseado no filesystem do kernel (**exFAT** por
> padrão) com uma **camada de metadados própria**. O BFS **não finge ser APFS**:
> é um overlay inspirado em recursos que existem em vários sistemas de
> arquivos (exFAT, APFS/HFS+, ext4, btrfs, xfs…).

O kernel Linux já monta volumes exFAT; o BFS roda **por cima** dele e traz a
camada "esperta" estilo Apple para qualquer volume montado (ext4, btrfs, xfs,
exFAT, NTFS, FAT, APFS via módulo e outros). A inicialização é não destrutiva.

## Arquitetura — a pilha de camadas

O projeto assume explicitamente a seguinte divisão:

```
exFAT (filesystem do kernel — a base)
 └── BFS metadata layer (overlay de usuário, em .bfsprivate/)
      ├── xattrs      → metadata.py   · atributos estendidos (AppleDouble "._*")
      ├── finder      → finder.py     · Finder Info, tags, ícone, comentário
      ├── snapshots   → snapshots.py  · estados imutáveis do volume
      ├── clones      → clones.py     · clones copy-on-write + deduplicação
      ├── checksums   → checksums.py  · integridade sha256
      └── sparse      → sparse.py     · representação esparsa/expandida
```

Cada camada é um módulo separado e a ordem da pilha é **declarada no
`volume.info`** de cada volume (`"layers": [...]`, formato `"bfs-overlay"`,
versão 2). O runtime nativo em `pineapplefs-c/` grava exatamente essa
declaração no preboot e no boot, e aplica `user.DOSATTRIB` quando o filesystem
suporta xattrs; os nomes começam por ponto para permanecerem ocultos também
nos sistemas que não suportam esse atributo.

```bash
python3 Scripts/pineapplefs.py layers /media/PENDRIVE   # mostra a pilha
python3 Scripts/pineapplefs.py status  /media/PENDRIVE  # volume.info completo
```

## O que ele faz (espelhando o macOS)

| Recurso                 | Como o macOS faz              | No BFS v2                                |
|-------------------------|-------------------------------|------------------------------------------|
| Atributos por arquivo   | `._<nome>` (AppleDouble)      | camada **xattrs** — `._<nome>` idêntico, no exFAT |
| Metadados do volume     | `.Spotlight-V100`, `.fseventsd`, `.Trashes`, `.DS_Store` | cria todos no `init` + `.bfsprivate` |
| Metadados do Finder     | Finder Info, tags, comentário | camada **finder** — flags, tags coloridas, ícone custom, comentário |
| Pasta de metadados      | —                             | `.bfsprivate/` (uuid, camadas, snapshots, clones, checksums) |
| Snapshots (APFS)        | `tmutil` / APFS snapshots     | camada **snapshots** — `snapshot`/`restore` em `.bfsprivate/snapshots/` |
| Clones (APFS)           | `clonefile` copy-on-write     | camada **clones** — `clone` (dedup por sha256 + hardlink, COW no `write`) |
| Arquivos expandidos     | APFS sparse files (extents)   | camada **sparse** — `expand`/`put-sparse` (container `PFSS01`, só blocos com dados) |
| Case-insensitive        | APFS/HFS+ (padrão)            | resolução de nomes case-insensitive     |
| Integridade             | APFS checksums                | camada **checksums** — `verify` (sha256 em `.bfsprivate/checksums/`) |
| Zip estilo macOS        | `ditto -c -k --keepParent` + `__MACOSX/` (nome da Apple) | `pack` cria `_PINEAPPLE/` com `._*` e `unpack` restaura |

## Como usar

Inicializar um volume BFS sem formatar nem apagar dados:

```bash
python3 Scripts/pineapplefs.py init /media/PENDRIVE --name "Pineapple OS"
```

O Spotlight do Pineapple usa `spotlight-index` e `spotlight-search`. O indice
SQLite FTS5 fica em `.Spotlight-V100/index.sqlite3`; `.fseventsd/pineapple.events`
registra alteracoes, `.Trashes/pineapple` recebe arquivos removidos e
`.localized` guarda o nome amigavel do volume.

Escrever arquivos e atributos (o sidecar `._*` é criado automaticamente):

```bash
pineapplefs put  /media/PENDRIVE Fotos/foto.jpg ./foto.jpg
pineapplefs setxattr /media/PENDRIVE Fotos/foto.jpg \
    com.apple.metadata:kMDItemTitle "Minha foto"
pineapplefs invisible /media/PENDRIVE Fotos/foto.jpg on   # oculta no Finder
pineapplefs tag /media/PENDRIVE Fotos/foto.jpg Red        # tag colorida
pineapplefs comment /media/PENDRIVE Fotos/foto.jpg "da praia"
pineapplefs icon /media/PENDRIVE Fotos/foto.jpg ./icone.png
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
├── __init__.py        # pacote BFS v2 (re-exporta BFSVolume + camadas)
├── constants.py       # constantes e helpers compartilhados (MAGIC, LAYERS, …)
├── core.py            # BFSVolume: núcleo + pilha de camadas (facade)
├── metadata.py        # camada xattrs  — atributos estendidos (AppleDouble)
├── finder.py          # camada finder  — Finder Info, tags, ícone, comentário
├── snapshots.py       # camada snapshots — estados imutáveis do volume
├── clones.py          # camada clones  — COW + dedup por hardlink
├── checksums.py       # camada checksums — integridade sha256
├── sparse.py          # camada sparse  — arquivos esparsos/expandidos (PFSS01)
├── appledouble.py     # formato AppleDouble "._*" (xattrs + Finder Info + resource fork)
├── archive.py         # pack/unpack de .zip estilo macOS (pasta _PINEAPPLE)
└── spotlight.py       # índice Spotlight (SQLite FTS5)
Scripts/pineapplefs.py # CLI
tests/test_bfs.py, tests/test_appledouble.py
```

## Formato AppleDouble (sidecars `._*`)

Mesmo formato real da Apple (`magic 0x00051607`, versão 2): grava xattrs
(entrada `0x8000`), Finder Info (entrada 8 — invisível, ícone, etc.), resource
fork (entrada 2) e nome Unicode (entrada 15). Qualquer leitor AppleDouble do
macOS/Linux lê os sidecars gerados pelo BFS.

## Limitações honestas

- O BFS é uma camada de usuário sobre o exFAT do kernel — **não é um
  filesystem de kernel** e não compete com o APFS em bloco.
- Clones usam hardlinks e a gravação faz copy-on-write no nível de arquivo
  (não de bloco, como o APFS).
- Snapshots copiam arquivos (imutáveis de verdade); clones são deduplicados
  por hardlink no armazenamento `.bfsprivate/clones/`.
- Verificação de integridade é sob demanda (`verify`), não contínua como o
  checksum de metadados do APFS.
- Testado na suíte (`tests/test_bfs.py` e `tests/test_appledouble.py`).