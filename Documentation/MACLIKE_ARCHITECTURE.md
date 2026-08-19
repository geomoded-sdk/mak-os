# Arquitetura mac-like do Pineapple OS

## Objetivo

O Pineapple OS deve apresentar uma experiencia integrada, previsivel e polida
como um desktop macOS, mantendo a capacidade de executar programas Linux,
pacotes Debian, Flatpak, AppImage, Wine e Darling.

A estrategia e separar a aparencia apresentada ao usuario da arvore POSIX que
os programas esperam. O sistema nao movera `/usr`, `/etc`, `/var` ou `/lib` para
caminhos novos: esses caminhos continuam estaveis para preservar compatibilidade.
O Finder, o launcher e os dialogos do sistema apresentarao uma camada de
navegacao Pineapple sobre essa base.

## Camadas

```text
+-------------------------------------------------------------+
| Pineapple Experience                                        |
| Finder, Dock, Launchpad, Mission Control, Settings          |
+-------------------------------------------------------------+
| Pineapple Workspace                                         |
| /Users, /Applications, /System, /Library, /Volumes         |
| favoritos, tags, aliases, busca e papeis de parede          |
+-------------------------------------------------------------+
| Linux desktop contracts                                     |
| XDG, D-Bus, Wayland, portals, systemd, POSIX                |
+-------------------------------------------------------------+
| Pineapple Kernel 6.1                                       |
| Linux 6.1 + configuracao Pineapple + modulos assinados      |
+-------------------------------------------------------------+
| Hardware                                                    |
+-------------------------------------------------------------+
```

## Estrutura de pastas apresentada ao usuario

A interface devera oferecer estes locais, mesmo quando a implementacao fisica
estiver em caminhos Linux equivalentes:

| Local Pineapple | Implementacao inicial | Regra |
|---|---|---|
| `Macintosh HD` | `/` | volume principal exibido com nome amigavel |
| `Users` | `/home` | contas de usuario e pastas pessoais |
| `Applications` | `.desktop` de `/usr/share/applications` e `~/.local/share/applications` | apps instalados, sem duplicar arquivos |
| `System` | `/usr`, `/bin`, `/sbin`, `/lib` | somente leitura na interface normal |
| `Library` | `/usr/share`, `/var/lib`, `/etc` | metadados e servicos, com protecao |
| `Volumes` | `/media`, `/mnt`, `/run/media` | volumes montados, incluindo BFS |
| `Trash` | `~/.local/share/Trash` | lixeira XDG, apresentada como Lixeira |

A primeira versao deve ser uma camada virtual no Finder. Symlinks e bind mounts
so devem ser adicionados depois de testes de instalacao e recuperacao, porque
mudar a topologia fisica pode quebrar pacotes Debian e ferramentas POSIX.

## Kernel e compatibilidade

- O ponto de partida permanece o Linux 6.1, com `CONFIG_LOCALVERSION` igual a
  `-pineappleos` e `CONFIG_MODULES=y`.
- O nome de produto pode ser **Pineapple Kernel**, mas a documentacao deve
  continuar declarando que ele e um kernel Linux modificado.
- Recursos de baixo nivel entram como modulos ou patches pequenos e isolados:
  suporte a hardware, energia, observabilidade, BFS e integracao com initramfs.
- Programas Linux continuam usando ELF, POSIX, procfs, sysfs, XDG e as ABI do
  Linux. A experiencia mac-like nao deve exigir uma ABI proprietaria.
- LPNU e APFS continuam compilados contra exatamente o release do kernel que
  sera empacotado, evitando `vermagic` incompativel.

## Inspiracoes e licencas

O projeto pode estudar conceitos publicos de sistemas Apple, incluindo a
organizacao de volumes, launch services, Finder, metadata e o modelo de
servicos. Isso nao significa copiar implementacao.

- Linux kernel: GPL-2.0-only, conforme a arvore do kernel usada pelo projeto.
- XNU: referencia arquitetural e de interfaces publicas; o XNU e distribuido
  pela Apple sob APSL 2.0. Nenhum codigo XNU deve ser copiado para este
  repositorio sem uma revisao juridica e de compatibilidade de licenca.
- APFS/HFS+, Finder e outros componentes Apple: comportamento observado e
  formatos publicamente documentados podem inspirar compatibilidade, mas
  implementacoes devem ser originais ou usar projetos com licenca compativel.
- Dependencias de terceiros permanecem sob as licencas indicadas por cada
  projeto e devem ser registradas antes de serem incorporadas.

## Fases de implementacao

1. **Workspace virtual**: modelo Rust para locais Pineapple, volumes, favoritos,
   lixeira, aplicativos e pastas protegidas; Finder passa a consumir esse
   modelo em vez de montar a arvore diretamente na tela inicial.
2. **Servico de metadata**: D-Bus para tags, thumbnails, busca e atualizacoes de
   volumes; usar inotify/fanotify ou APIs equivalentes sem exigir patches no
   kernel inicialmente.
3. **Volumes**: integrar BFS, ext4, exFAT e APFS via uma API comum de montagem,
   exibindo cada volume em `Volumes`.
4. **Experiencia de sistema**: aplicativos padrao, preferencias, instalador,
   atualizador e recuperacao com a mesma nomenclatura e hierarquia visual.
5. **Kernel**: somente depois de medir uma necessidade real, avaliar patches
   Linux 6.1 e modulos novos. Cada mudanca deve ter teste de boot e rollback.

## Criterios de aceite

- Um programa Linux continua abrindo arquivos em caminhos POSIX normais.
- O Finder oferece `Macintosh HD`, `Users`, `Applications`, `System`,
  `Library`, `Volumes` e `Trash` de forma consistente.
- Volumes removiveis aparecem e desaparecem sem reiniciar o shell.
- A interface nao permite editar arquivos protegidos por acidente.
- O sistema continua inicializando com a configuracao atual quando a camada
  Pineapple falha.
- Toda referencia externa e registrada com origem e licenca.
