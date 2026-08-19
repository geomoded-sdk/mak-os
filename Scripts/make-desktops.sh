#!/bin/bash
# =============================================================================
#  make-desktops.sh — gera os arquivos .desktop dos aplicativos do Pineapple OS
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

desktop pineapple-shell        "Pineapple Shell"        "/usr/local/bin/pineapple-shell"       "pineapple-logo"      "Barra superior do Pineapple OS"
desktop pineapple-dock         "Pineapple Dock"         "/usr/local/bin/pineapple-dock"        "pineapple-logo"      "Dock do Pineapple OS"
desktop pineapple-launcher     "Pineapple Launcher"     "/usr/local/bin/pineapple-launcher"    "pineapple-logo"      "Lançador de aplicativos"
desktop pineapple-launchpad    "Pineapple Launchpad"    "/usr/local/bin/pineapple-launchpad"   "pineapple-launchpad" "Grade de aplicativos"
desktop pineapple-mission      "Pineapple Mission"      "/usr/local/bin/pineapple-mission"     "pineapple-mission"   "Mission Control (janelas e áreas de trabalho)"
desktop pineapple-canopy       "Pineapple Canopy"       "/usr/local/bin/pineapple-canopy"      "pineapple-canopy"    "Gerenciador de arquivos"
desktop pineapple-terminal     "Pineapple Terminal"     "/usr/bin/pineapple-terminal.py"       "pineapple-terminal"  "Terminal do Pineapple OS"
desktop pineapple-calculator   "Pineapple Calculator"   "/usr/bin/pineapple-calculator.py"     "pineapple-calc"      "Calculadora"
desktop pineapple-notes        "Pineapple Notes"        "/usr/bin/pineapple-notes.py"          "pineapple-notes"     "Notas"
desktop pineapple-settings     "Pineapple Settings"     "/usr/bin/pineapple-settings.py"       "pineapple-settings"  "Configurações do sistema"
desktop pineapple-monitor      "Pineapple Monitor"      "/usr/bin/pineapple-monitor.py"        "pineapple-monitor"   "Monitor de recursos"
desktop pineapple-photos       "Pineapple Photos"       "/usr/bin/pineapple-photos.py"         "pineapple-photos"    "Visualizador de fotos"
desktop pineapple-music        "Pineapple Music"        "/usr/bin/pineapple-music.py"          "pineapple-music"     "Player de música"
desktop pineapple-browser      "Pineapple Browser"      "/usr/bin/pineapple-browser.py"        "pineapple-browser"   "Navegador web"
desktop pineapple-store        "Pineapple Store"        "/usr/bin/pineapple-store.py"          "pineapple-store"     "Loja de aplicativos"
desktop pineapple-assistant    "Pineapple Assistant"    "/usr/bin/pineapple-assistant"         "pineapple-assistant" "Assistente local (IA)"
desktop pineapple-control-center "Central de Controle" "/usr/bin/pineapple-control-center.py" "pineapple-control-center-symbolic" "Controles rápidos"
desktop pineapple-notifyd      "Pineapple Notificações"  "/usr/bin/pineapple-notifyd.py"        "pineapple-logo"      "Central de notificações"

echo "==> $(ls "$DESKTOP" | wc -l) arquivos .desktop gerados em $DESKTOP"
