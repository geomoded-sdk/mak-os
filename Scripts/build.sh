#!/bin/bash
# =============================================================================
#  build.sh — compila os componentes do Mak OS
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${PREFIX:-/usr/local}"
STAGE="$ROOT/build/stage"
BIN="$STAGE/usr/local/bin"
APP_BIN="$STAGE/usr/bin"
APPS="$STAGE/usr/share/makos"
DESKTOP="$STAGE/usr/share/applications"

mkdir -p "$BIN" "$APP_BIN" "$APPS" "$DESKTOP"

echo "==> Compilando componentes Rust (shell, dock, launcher, finder)"

# shell
(cd "$ROOT/Desktop" && cargo build --release 2>/dev/null) && \
  cp "$ROOT/Desktop/target/release/mak-shell" "$BIN/" || \
  echo "   [aviso] mak-shell não compilado (verifique cargo/GTK4)"

# dock
(cd "$ROOT/Dock" && cargo build --release 2>/dev/null) && \
  cp "$ROOT/Dock/target/release/mak-dock" "$BIN/" || \
  echo "   [aviso] mak-dock não compilado"

# launcher
(cd "$ROOT/Launcher" && cargo build --release 2>/dev/null) && \
  cp "$ROOT/Launcher/target/release/mak-launcher" "$BIN/" || \
  echo "   [aviso] mak-launcher não compilado"

# finder
(cd "$ROOT/Finder" && cargo build --release 2>/dev/null) && \
  cp "$ROOT/Finder/target/release/mak-finder" "$BIN/" || \
  echo "   [aviso] mak-finder não compilado"

echo "==> Instalando aplicativos Python"
install -m755 "$ROOT"/Apps/*/*.py "$APP_BIN/"

echo "==> Instalando assistente IA"
install -m755 "$ROOT/AI/mak-ai.py" "$APP_BIN/mak-ai"
install -m755 "$ROOT/AI/mak-assistant.py" "$APP_BIN/mak-assistant"
install -m755 "$ROOT/AI/mak-voice.py" "$APP_BIN/mak-voice"
install -m644 "$ROOT/AI/mak_ai.py" "$ROOT/AI/voice.py" "$APPS/AI/"

echo "==> Instalando temas e ícones"
mkdir -p "$STAGE/usr/share/themes" "$STAGE/usr/share/icons"
cp -r "$ROOT/Themes/Mak-Dark" "$ROOT/Themes/Mak-Light" "$ROOT/Themes/Mak-HighSierra" "$STAGE/usr/share/themes/"
cp -r "$ROOT/Icons/mak-icons" "$STAGE/usr/share/icons/"

echo "==> Instalando wallpaper"
mkdir -p "$STAGE/usr/share/backgrounds/makos"
cp "$ROOT/Themes/wallpapers/wallpaper.svg" "$ROOT/Themes/wallpapers/highsierra.svg" "$STAGE/usr/share/backgrounds/makos/"

echo "==> Instalando schemas GSettings"
mkdir -p "$STAGE/usr/share/glib-2.0/schemas"
cp "$ROOT/Installer/schemas/org.makos.gschema.xml" "$STAGE/usr/share/glib-2.0/schemas/"

echo "==> Instalando temas de boot (GRUB/Plymouth/SDDM) e Calamares"
mkdir -p "$STAGE/boot/grub/themes/makos" "$STAGE/usr/share/plymouth/themes/makos"
mkdir -p "$STAGE/usr/share/sddm/themes/makos" "$STAGE/usr/share/calamares"
cp -r "$ROOT/Installer/grub/theme/." "$STAGE/boot/grub/themes/makos/"
cp -r "$ROOT/Installer/plymouth/theme/." "$STAGE/usr/share/plymouth/themes/makos/"
cp -r "$ROOT/Installer/sddm/theme/." "$STAGE/usr/share/sddm/themes/makos/"
cp -r "$ROOT/Installer/calamares" "$STAGE/usr/share/calamares/"

echo "==> Registrando versão"
mkdir -p "$STAGE/etc"
echo "0.1.0" > "$STAGE/etc/makos-version"

echo "==> Instalando configurações do compositor"
mkdir -p "$STAGE/usr/share/makos/Desktop/data"
cp -r "$ROOT/Desktop/data" "$STAGE/usr/share/makos/Desktop/"

echo "==> Instalando utilitários de sessão"
install -m755 "$ROOT/Scripts/mak-workspace.sh" "$BIN/mak-workspace"
install -m755 "$ROOT/Scripts/mak-update.sh" "$BIN/mak-update"

echo "==> Gerando .desktop files"
./Scripts/make-desktops.sh "$STAGE"

echo "==> Build concluído em $STAGE"
echo "    Para instalar no sistema:  sudo ./Scripts/install.sh"
