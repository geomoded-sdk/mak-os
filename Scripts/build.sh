#!/bin/bash
# =============================================================================
#  build.sh — compila os componentes do Pineapple OS
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${PREFIX:-/usr/local}"
STAGE="$ROOT/build/stage"
BIN="$STAGE/usr/local/bin"
APP_BIN="$STAGE/usr/bin"
APPS="$STAGE/usr/share/pineappleos"
DESKTOP="$STAGE/usr/share/applications"

mkdir -p "$BIN" "$APP_BIN" "$APPS" "$DESKTOP"

echo "==> Compilando componentes Rust (shell, dock, launcher, launchpad, canopy, gestures, mission)"

# shell
(cd "$ROOT/Desktop" && cargo build --release 2>/dev/null) && \
  cp "$ROOT/Desktop/target/release/pineapple-shell" "$BIN/" || \
  echo "   [aviso] pineapple-shell não compilado (verifique cargo/GTK4)"

# dock
(cd "$ROOT/Dock" && cargo build --release 2>/dev/null) && \
  cp "$ROOT/Dock/target/release/pineapple-dock" "$BIN/" || \
  echo "   [aviso] pineapple-dock não compilado"

# launcher
(cd "$ROOT/Launcher" && cargo build --release 2>/dev/null) && \
  cp "$ROOT/Launcher/target/release/pineapple-launcher" "$BIN/" || \
  echo "   [aviso] pineapple-launcher não compilado"

# launchpad
(cd "$ROOT/Launchpad" && cargo build --release 2>/dev/null) && \
  cp "$ROOT/Launchpad/target/release/pineapple-launchpad" "$BIN/" || \
  echo "   [aviso] pineapple-launchpad não compilado"

# canopy (gerenciador de arquivos)
(cd "$ROOT/Canopy" && cargo build --release 2>/dev/null) && \
  cp "$ROOT/Canopy/target/release/pineapple-canopy" "$BIN/" || \
  echo "   [aviso] pineapple-canopy não compilado"

# gestures (daemon de gestos no touchpad)
(cd "$ROOT/Gestures" && cargo build --release 2>/dev/null) && \
  cp "$ROOT/Gestures/target/release/pineapple-gestures" "$BIN/" || \
  echo "   [aviso] pineapple-gestures não compilado"

# mission control (janelas + areas de trabalho em tela cheia)
(cd "$ROOT/Mission" && cargo build --release 2>/dev/null) && \
  cp "$ROOT/Mission/target/release/pineapple-mission" "$BIN/" || \
  echo "   [aviso] pineapple-mission não compilado"

echo "==> Instalando aplicativos Python"
install -m755 "$ROOT"/Apps/*/*.py "$APP_BIN/"

echo "==> Instalando assistente IA"
install -m755 "$ROOT/AI/pineapple-ai.py" "$APP_BIN/pineapple-ai"
install -m755 "$ROOT/AI/pineapple-assistant.py" "$APP_BIN/pineapple-assistant"
install -m755 "$ROOT/AI/pineapple-voice.py" "$APP_BIN/pineapple-voice"
install -m644 "$ROOT/AI/pineapple_ai.py" "$ROOT/AI/voice.py" "$APPS/AI/"

echo "==> Instalando daemon de wallpaper (dinâmico estilo Catalina)"
install -m755 "$ROOT/Apps/Wallpaper/pineapple-wallpaper.py" "$APP_BIN/pineapple-wallpaper"

echo "==> Instalando BFS (Pineapple File System) — exFAT + recursos APFS/HFS+"
mkdir -p "$APPS/Filesystem"
cp -r "$ROOT/Filesystem/pineapplefs" "$APPS/Filesystem/"
install -m755 "$ROOT/Scripts/pineapplefs.py" "$APP_BIN/pineapplefs"

echo "==> Instalando temas e ícones"
mkdir -p "$STAGE/usr/share/themes" "$STAGE/usr/share/icons"
cp -r "$ROOT/Themes/Pineapple-Dark" "$ROOT/Themes/Pineapple-Light" "$ROOT/Themes/Pineapple-HighSierra" "$STAGE/usr/share/themes/"
cp -r "$ROOT/Icons/pineapple-icons" "$STAGE/usr/share/icons/"

echo "==> Instalando wallpapers (High Sierra, Catalina dinâmico, Sequoia)"
mkdir -p "$STAGE/usr/share/backgrounds/pineappleos"
cp -r "$ROOT/Themes/wallpapers/." "$STAGE/usr/share/backgrounds/pineappleos/"

echo "==> Instalando identidade do sistema (os-release)"
mkdir -p "$STAGE/etc"
cp "$ROOT/Installer/os-release" "$STAGE/etc/os-release"

echo "==> Instalando PowerBook ID check (initramfs)"
mkdir -p "$APPS"
cp "$ROOT/ids.txt" "$APPS/ids.txt"
mkdir -p "$STAGE/usr/share/initramfs-tools/hooks"
mkdir -p "$STAGE/usr/share/initramfs-tools/scripts/init-bottom"
cp "$ROOT/Installer/initramfs/hooks/pineapple-powerbook-check" \
  "$STAGE/usr/share/initramfs-tools/hooks/"
cp "$ROOT/Installer/initramfs/scripts/init-bottom/pineapple-powerbook-check" \
  "$STAGE/usr/share/initramfs-tools/scripts/init-bottom/"
chmod +x "$STAGE/usr/share/initramfs-tools/hooks/pineapple-powerbook-check"
chmod +x "$STAGE/usr/share/initramfs-tools/scripts/init-bottom/pineapple-powerbook-check"

echo "==> Instalando schemas GSettings"
mkdir -p "$STAGE/usr/share/glib-2.0/schemas"
cp "$ROOT/Installer/schemas/org.pineappleos.gschema.xml" "$STAGE/usr/share/glib-2.0/schemas/"

echo "==> Instalando temas de boot (GRUB/Plymouth/SDDM) e Calamares"
mkdir -p "$STAGE/boot/grub/themes/pineappleos" "$STAGE/usr/share/plymouth/themes/pineappleos"
mkdir -p "$STAGE/usr/share/sddm/themes/pineappleos" "$STAGE/usr/share/calamares"
cp -r "$ROOT/Installer/grub/theme/." "$STAGE/boot/grub/themes/pineappleos/"
cp -r "$ROOT/Installer/plymouth/theme/." "$STAGE/usr/share/plymouth/themes/pineappleos/"
cp -r "$ROOT/Installer/sddm/theme/." "$STAGE/usr/share/sddm/themes/pineappleos/"
cp -r "$ROOT/Installer/calamares" "$STAGE/usr/share/calamares/"

echo "==> Registrando versão"
mkdir -p "$STAGE/etc"
echo "0.1.0" > "$STAGE/etc/pineappleos-version"

echo "==> Instalando configurações do compositor"
mkdir -p "$STAGE/usr/share/pineappleos/Desktop/data"
cp -r "$ROOT/Desktop/data" "$STAGE/usr/share/pineappleos/Desktop/"

echo "==> Instalando utilitários de sessão"
install -m755 "$ROOT/Scripts/pineapple-workspace.sh" "$BIN/pineapple-workspace"
install -m755 "$ROOT/Scripts/pineapple-update.sh" "$BIN/pineapple-update"

echo "==> Gerando .desktop files"
./Scripts/make-desktops.sh "$STAGE"

echo "==> Build concluído em $STAGE"
echo "    Para instalar no sistema:  sudo ./Scripts/install.sh"
