#!/bin/bash
# =============================================================================
#  make-desktops.sh — gera os arquivos .desktop dos aplicativos do Mak OS
#  Uso: make-desktops.sh [stage_dir]
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="${1:-$ROOT/build/stage}"
DESKTOP="$STAGE/usr/share/applications"
mkdir -p "$DESKTOP"

desktop() {
  local id="$1" name="$2" exec="$3" icon="$4" comment="$5"
  cat > "$DESKTOP/$id.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=$name
Comment=$comment
Exec=$exec
Icon=$icon
Terminal=false
Categories=Utility;System;Office;Graphics;AudioVideo;Network;
StartupNotify=true
EOF
}

desktop mak-shell        "Mak Shell"        "/usr/local/bin/mak-shell"       "mak-logo"      "Barra superior do Mak OS"
desktop mak-dock         "Mak Dock"         "/usr/local/bin/mak-dock"        "mak-logo"      "Dock do Mak OS"
desktop mak-launcher     "Mak Launcher"     "/usr/local/bin/mak-launcher"    "mak-logo"      "Lançador de aplicativos"
desktop mak-finder       "Mak Finder"       "/usr/local/bin/mak-finder"      "mak-finder"    "Gerenciador de arquivos"
desktop mak-terminal     "Mak Terminal"     "/usr/bin/mak-terminal.py"       "mak-terminal"  "Terminal do Mak OS"
desktop mak-calculator   "Mak Calculator"   "/usr/bin/mak-calculator.py"     "mak-calc"      "Calculadora"
desktop mak-notes        "Mak Notes"        "/usr/bin/mak-notes.py"          "mak-notes"     "Notas"
desktop mak-settings     "Mak Settings"     "/usr/bin/mak-settings.py"       "mak-settings"  "Configurações do sistema"
desktop mak-monitor      "Mak Monitor"      "/usr/bin/mak-monitor.py"        "mak-monitor"   "Monitor de recursos"
desktop mak-photos       "Mak Photos"       "/usr/bin/mak-photos.py"         "mak-photos"    "Visualizador de fotos"
desktop mak-music        "Mak Music"        "/usr/bin/mak-music.py"          "mak-music"     "Player de música"
desktop mak-browser      "Mak Browser"      "/usr/bin/mak-browser.py"        "mak-browser"   "Navegador web"
desktop mak-store        "Mak Store"        "/usr/bin/mak-store.py"          "mak-store"     "Loja de aplicativos"
desktop mak-assistant    "Mak Assistant"    "/usr/bin/mak-assistant"         "mak-assistant" "Assistente local (IA)"
desktop mak-control-center "Central de Controle" "/usr/bin/mak-control-center.py" "mak-control-center-symbolic" "Controles rápidos"
desktop mak-notifyd      "Mak Notificações"  "/usr/bin/mak-notifyd.py"        "mak-logo"      "Central de notificações"

echo "==> $(ls "$DESKTOP" | wc -l) arquivos .desktop gerados em $DESKTOP"
