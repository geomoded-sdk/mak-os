# Desenvolvimento do Pineapple OS

Guia para rodar e testar os componentes do Pineapple OS em uma máquina Linux.

## Pré-requisitos

```bash
# Ubuntu/Debian
sudo apt install -y \
  build-essential pkg-config meson ninja-build \
  libgtk-4-dev libgtk-4-layer-shell-dev \
  libadwaita-1-dev libvte-3.90-dev libwebkitgtk-6.0-dev \
  libgstreamer1.0-dev \
  cargo rustc python3 python3-gi gir1.2-gtk-4.0 gir1.2-vte-3.91 \
  gir1.2-webkit-6.0 gir1.2-gstreamer-1.0 \
  labwc wayland-protocols wayland-utils \
  live-build debootstrap
```

## Sessão de desenvolvimento

Roda compositor + barra + dock + launcher + launchpad + mission + gestos em uma sessão Wayland própria:

```bash
./Scripts/start-session.sh
```

Para rodar em um servidor X existente (teste rápido de componentes):

```bash
GTK_THEME=Pineapple-HighSierra python3 Apps/Settings/pineapple-settings.py
GTK_THEME=Pineapple-HighSierra cargo run --manifest-path Dock/Cargo.toml
```

> Nota: barra e dock usam `gtk4-layer-shell` e precisam de um compositor Wayland
> compatível (labwc, sway, Hyprland, wayfire).

## Testar componentes isoladamente

| Componente | Comando |
|------------|---------|
| Pineapple Calculator | `python3 Apps/Calculator/pineapple-calculator.py` |
| Pineapple Terminal   | `python3 Apps/Terminal/pineapple-terminal.py` |
| Pineapple Notes      | `python3 Apps/Notes/pineapple-notes.py` |
| Pineapple Monitor    | `python3 Apps/Monitor/pineapple-monitor.py` |
| Pineapple Photos     | `python3 Apps/Photos/pineapple-photos.py` |
| Pineapple Music      | `python3 Apps/Music/pineapple-music.py` |
| Pineapple Browser    | `python3 Apps/Browser/pineapple-browser.py` |
| Pineapple Store      | `python3 Apps/Store/pineapple-store.py` |
| Central Controle | `python3 Apps/ControlCenter/pineapple-control-center.py` |
| Assistente IA  | `./AI/pineapple-ai.py "abrir o terminal"` |

## Testar o agente IA (sem Ollama)

As ações locais (abrir app, pesquisar arquivos, resumir) funcionam offline.
Apenas perguntas gerais exigem o Ollama (`ollama serve`).

## Tema e ícones

- Temas: copie `Themes/Pineapple-HighSierra` (padrão) e os demais para `~/.themes/`.
- Ícones: `Scripts/gen-icons.py` gera o set; instale em `~/.local/share/icons/pineapple-icons`.
- Aplique: `gsettings set org.gnome.desktop.interface gtk-theme Pineapple-HighSierra`.

## Build da ISO

```bash
./Scripts/build-darling-deb.sh   # opcional: Darling pré-instalado (.deb)
./Scripts/build-iso.sh           # Debian stable
DISTRO=ubuntu SUITE=noble ./Scripts/build-iso.sh
```
