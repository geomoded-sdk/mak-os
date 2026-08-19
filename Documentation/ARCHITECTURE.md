# Arquitetura do Pineapple OS

## Visão geral

O Pineapple OS é construído sobre uma base Debian/Ubuntu. A camada de interface é um
shell Wayland composto por componentes GTK4 independentes que se comunicam por
D-Bus. Cada componente é um processo separado (modularidade e isolamento de
falhas), gerenciado pelo `pineapple-session` (session manager).

```
┌─────────────────────────────────────────────────────────┐
│                       Compositor                        │
│               (labwc / wlroots, GPU)                    │
├──────────────┬───────────────┬─────────────┬────────────┤
│  pineapple-bar    │  pineapple-dock │ pineapple-launcher │ pineapple-launchpad │ pineapple-mission │
│  (topo)      │  (inferior)   │ (apps)      │ (controle) │
├──────────────┴───────────────┴─────────────┴────────────┤
│  Aplicativos nativos (GTK4) │ Flatpak │ AppImage │ Wine │
├─────────────────────────────┴───────────────────────────┤
│  pineapple-services (D-Bus): notificações, áudio, energia, IA │
├─────────────────────────────────────────────────────────┤
│                    GNU/Linux (Debian)                   │
└─────────────────────────────────────────────────────────┘
```

## Plataforma integrada

O desktop usa uma base modular para parecer um sistema completo sem esconder
as responsabilidades de cada camada:

- **Wayland**: labwc/wlroots, XWayland, libinput e xkbcommon.
- **Sessao desktop**: PipeWire, WirePlumber, portals GTK e backend wlroots.
- **Privacidade e credenciais**: polkit, PAM, AppArmor, GnuPG, libsodium e
  libsecret.
- **Volumes**: UDisks2, FUSE3, libarchive, zstd, LZ4 e smartmontools. O BFS
  permanece a camada Pineapple acima dos filesystems montados.
- **Multimidia**: FFmpeg, libvpx, dav1d, JPEG Turbo, PNG, WebP e OpenEXR.

Smithay fica registrado como alternativa futura para um compositor totalmente
Rust; o compositor atual continua usando wlroots para reduzir risco e manter
compatibilidade com XWayland.

## Componentes

### 1. `Desktop` — Shell do sistema (Rust/GTK4)
- `pineapple-shell`: barra superior (menu Pineapple, relógio, status, centro de controle).
- `pineapple-session`: gerenciador de sessão (inicia/compositor, apps de inicialização).
- Integra-se ao compositor via `gtk4-layer-shell` (camadas `top`, `bottom`).

### 2. `Dock` — Biblioteca + componente (Rust/GTK4)
- Biblioteca `pineapple-dock-lib` reutilizável e processo `pineapple-dock`.
- Animações suaves (magnificação suave), indicador de apps em execução.
- Bandeja de janelas minimizadas estilo macOS via
  `wlr-foreign-toplevel-management-v1`: janelas minimizadas (`Super+M`) aparecem
  após o separador com animação de "colapso" para o Dock; clicar numa miniatura
  restaura a janela (`activate` + foco).
- Se comunica com o shell via D-Bus para abrir/ocultar apps.

### 3. `Launcher` — Lançador (Rust/GTK4)
- Busca por aplicativos, arquivos e comandos.
- Navegação por teclado (incremental), abre apps via D-Bus/`.desktop`.

### 4. `Launchpad` — Grade de aplicativos (Rust/GTK4)
- Overlay em tela cheia estilo macOS (grid de ícones + busca).
- Acesso por `F4`, ícone no dock; alterna mostrar/ocultar.

### 4b. `Gestures` — Daemon de gestos (Rust/libinput)
- Lê os dispositivos de entrada via libinput (independente do compositor).
- Reconhece gestos do touchpad: swipe up com 3 dedos abre o Mission Control.
- Gerenciado pelo `pineapple-session`/systemd junto com os demais componentes.

### 4c. `Mission` — Mission Control e Spaces (Rust/GTK4)
- Overlay em tela cheia com a faixa de áreas de trabalho (Spaces) e a grade de
  janelas abertas, como no macOS.
- Spaces via `ext-workspace-v1`; janelas via `wlr-foreign-toplevel-management-v1`
  (protocolos Wayland do labwc/wlroots).
- Acesso por `F3`, `Ctrl+Up` ou gesto de 3 dedos; clique num card foca a janela,
  clique num Space troca a área; `Esc` fecha.

### 5. `Finder` — Gerenciador de arquivos (Rust/GTK4)
- Visualizações ícones/listas, favoritos, montagens, pesquisa.
- Integração com `GVfs` para protocolos remotos.

### 6. `AI` — Assistente local (Python + Ollama)
- Daemon `pineapple-ai` que fala com o Ollama (API REST local).
- Ações: abrir apps, pesquisar arquivos, resumir documentos, executar scripts.
- Interface GTK4 `pineapple-assistant`.

### 7. `Settings`, `Store`, apps — ver `Apps/`
- Apps simples em Python/GTK4; os principais em Rust/GTK4.

### 8. Serviços
- `pineapple-notifyd`: central de notificações (D-Bus `org.freedesktop.Notifications`).
- `pineapple-audio`: controle de volume/dispositivos (PipeWire).
- `pineapple-power`: brilho e gerenciamento de energia.

## Compositor

Usamos **labwc** (compositor wlroots leve e estável) como base. Alternativa:
`wayfire`. O compositor é iniciado por `pineapple-session`:

```
/usr/lib/pineappleos/session/start-compositor.sh
```

## Comunicação entre componentes

- **D-Bus** (session bus): sessão, notificações, centro de controle.
- **GTK4 layershell**: posicionamento de barra/dock nas bordas da tela.
- **XDG Desktop Portal**: dialogs, screenshots, abertura de arquivos.

## Inicialização (boot)

1. GRUB (fundo claro + abacaxi) carrega o kernel com argumentos estilo macOS:
   `quiet loglevel=0 splash` e `-pineapplepowerbookid=<ID>`.
2. No initramfs, `pineapple-powerbook-check` valida o ID contra `ids.txt`.
   Ausente/inválido → **kernel panic** (SysRq) e o boot é interrompido.
3. Plymouth exibe o abacaxi + barra de progresso sobre o fundo claro.
4. `systemd` inicia `pineappleos-session.target` (multi-user).
5. `pineapple-session` detecta GPU, inicia compositor e componentes.
6. Apps de inicialização do usuário são abertos.

## Temas e identidade

- Temas GTK próprios em `Themes/` (`Pineapple-HighSierra` padrão,
  `Pineapple-Dark`, `Pineapple-Light`).
- Ícones próprios em `Icons/pineapple-icons` (SVG), gerados por
  `Scripts/gen-icons.py`.
- Fonte padrão: `Inter` ou `Sora` (open source).
- Wallpapers em `Themes/wallpapers/`: High Sierra (estático), Catalina
  (**dinâmico** — trocado por horário pelo daemon `pineapple-wallpaper`,
  ver `Apps/Wallpaper/`) e Sequoia.
- Identidade de plataforma: `os-release` (Installer/os-release) e kernel
  `6.1.0-pineappleos` (ver `Kernel/README.md`). A marca Linux é ocultada do
  usuário (boot limpo, sem logs de kernel).

## Sistema de arquivos (BFS)

Volumes exFAT ganham uma camada estilo APFS/HFS+ via `Filesystem/pineapplefs`
e o CLI `Scripts/pineapplefs.py`:

- Sidecars **AppleDouble `._*`** (xattrs, Finder Info, resource fork) — o mesmo
  formato do macOS, legível por qualquer leitor AppleDouble.
- **`.bfsprivate/`** guarda uuid, snapshots, clones e checksums do volume.
- Artefatos que o macOS criaria no volume: `.Spotlight-V100`, `.fseventsd`,
  `.Trashes`, `.DS_Store`, `.metadata_never_index`, `.localized`.
- Snapshots e clones **copy-on-write** (dedup por sha256 + hardlinks).
- Arquivos esparsos "expandidos" (container `PFSS01` com extents).
- `.zip` estilo macOS: `pack` gera a pasta `_PINEAPPLE` com `._*`, `unpack` aplica.

Detalhes em `Filesystem/README.md`.

## Padrões de código

- Rust: componentes críticos (shell, dock, launcher, launchpad, mission, finder, gestures).
- Python: apps utilitários e daemons de integração.
- C: módulos de baixo nível e integração com o kernel.

Consulte `Documentation/CONTRIBUTING.md` para as regras detalhadas.
