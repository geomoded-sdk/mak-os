# Desenvolvimento do Mak OS

Guia para rodar e testar os componentes do Mak OS em uma máquina Linux.

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
GTK_THEME=Mak-HighSierra python3 Apps/Settings/mak-settings.py
GTK_THEME=Mak-HighSierra cargo run --manifest-path Dock/Cargo.toml
```

> Nota: barra e dock usam `gtk4-layer-shell` e precisam de um compositor Wayland
> compatível (labwc, sway, Hyprland, wayfire).

## Testar componentes isoladamente

| Componente | Comando |
|------------|---------|
| Mak Calculator | `python3 Apps/Calculator/mak-calculator.py` |
| Mak Terminal   | `python3 Apps/Terminal/mak-terminal.py` |
| Mak Notes      | `python3 Apps/Notes/mak-notes.py` |
| Mak Monitor    | `python3 Apps/Monitor/mak-monitor.py` |
| Mak Photos     | `python3 Apps/Photos/mak-photos.py` |
| Mak Music      | `python3 Apps/Music/mak-music.py` |
| Mak Browser    | `python3 Apps/Browser/mak-browser.py` |
| Mak Store      | `python3 Apps/Store/mak-store.py` |
| Central Controle | `python3 Apps/ControlCenter/mak-control-center.py` |
| Assistente IA  | `./AI/mak-ai.py "abrir o terminal"` |

## Testar o agente IA (sem Ollama)

As ações locais (abrir app, pesquisar arquivos, resumir) funcionam offline.
Apenas perguntas gerais exigem o Ollama (`ollama serve`).

## Tema e ícones

- Temas: copie `Themes/Mak-HighSierra` (padrão) e os demais para `~/.themes/`.
- Ícones: `Scripts/gen-icons.py` gera o set; instale em `~/.local/share/icons/mak-icons`.
- Aplique: `gsettings set org.gnome.desktop.interface gtk-theme Mak-HighSierra`.

## Build da ISO

```bash
./Scripts/build-darling-deb.sh   # opcional: Darling pré-instalado (.deb)
./Scripts/build-iso.sh           # Debian stable
DISTRO=ubuntu SUITE=noble ./Scripts/build-iso.sh
```
