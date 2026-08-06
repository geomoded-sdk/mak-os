# Arquitetura do Mak OS

## Visão geral

O Mak OS é construído sobre uma base Debian/Ubuntu. A camada de interface é um
shell Wayland composto por componentes GTK4 independentes que se comunicam por
D-Bus. Cada componente é um processo separado (modularidade e isolamento de
falhas), gerenciado pelo `mak-session` (session manager).

```
┌─────────────────────────────────────────────────────────┐
│                       Compositor                        │
│               (labwc / wlroots, GPU)                    │
├──────────────┬───────────────┬─────────────┬────────────┤
│  mak-bar    │  mak-dock │ mak-launcher │ mak-launchpad │ mak-mission │
│  (topo)      │  (inferior)   │ (apps)      │ (controle) │
├──────────────┴───────────────┴─────────────┴────────────┤
│  Aplicativos nativos (GTK4) │ Flatpak │ AppImage │ Wine │
├─────────────────────────────┴───────────────────────────┤
│  mak-services (D-Bus): notificações, áudio, energia, IA │
├─────────────────────────────────────────────────────────┤
│                    GNU/Linux (Debian)                   │
└─────────────────────────────────────────────────────────┘
```

## Componentes

### 1. `Desktop` — Shell do sistema (Rust/GTK4)
- `mak-shell`: barra superior (menu MaK, relógio, status, centro de controle).
- `mak-session`: gerenciador de sessão (inicia/compositor, apps de inicialização).
- Integra-se ao compositor via `gtk4-layer-shell` (camadas `top`, `bottom`).

### 2. `Dock` — Biblioteca + componente (Rust/GTK4)
- Biblioteca `mak-dock-lib` reutilizável e processo `mak-dock`.
- Animações suaves (magnificação suave), indicador de apps em execução.
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
- Gerenciado pelo `mak-session`/systemd junto com os demais componentes.

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
- Daemon `mak-ai` que fala com o Ollama (API REST local).
- Ações: abrir apps, pesquisar arquivos, resumir documentos, executar scripts.
- Interface GTK4 `mak-assistant`.

### 7. `Settings`, `Store`, apps — ver `Apps/`
- Apps simples em Python/GTK4; os principais em Rust/GTK4.

### 8. Serviços
- `mak-notifyd`: central de notificações (D-Bus `org.freedesktop.Notifications`).
- `mak-audio`: controle de volume/dispositivos (PipeWire).
- `mak-power`: brilho e gerenciamento de energia.

## Compositor

Usamos **labwc** (compositor wlroots leve e estável) como base. Alternativa:
`wayfire`. O compositor é iniciado por `mak-session`:

```
/usr/lib/makos/session/start-compositor.sh
```

## Comunicação entre componentes

- **D-Bus** (session bus): sessão, notificações, centro de controle.
- **GTK4 layershell**: posicionamento de barra/dock nas bordas da tela.
- **XDG Desktop Portal**: dialogs, screenshots, abertura de arquivos.

## Inicialização (boot)

1. GRUB → kernel + initramfs.
2. `systemd` inicia `makos-session.target` (multi-user).
3. `mak-session` detecta GPU, inicia compositor e componentes.
4. Apps de inicialização do usuário são abertos.

## Temas e identidade

- Temas GTK próprios em `Themes/` (`Mak-HighSierra` padrão, `Mak-Dark`, `Mak-Light`).
- Ícones próprios em `Icons/mak-icons` (SVG).
- Fonte padrão: `Inter` ou `Sora` (open source).

## Padrões de código

- Rust: componentes críticos (shell, dock, launcher, launchpad, mission, finder, gestures).
- Python: apps utilitários e daemons de integração.
- C: módulos de baixo nível e integração com o kernel.

Consulte `Documentation/CONTRIBUTING.md` para as regras detalhadas.
