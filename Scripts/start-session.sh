#!/bin/bash
# =============================================================================
#  pineapple-session — inicia a sessão do Pineapple OS
# =============================================================================
set -euo pipefail

export XDG_CURRENT_DESKTOP=PineappleOS
export XDG_SESSION_TYPE=wayland
export GDK_BACKEND=wayland
export GTK_CSD=0
export GTK_THEME=Pineapple-HighSierra
export QT_QPA_PLATFORM=wayland
export MOZ_ENABLE_WAYLAND=1

log() { echo "[pineapple-session] $*"; }

# ------------------------------------------------------------- compositor
log "iniciando compositor (labwc)"
if command -v labwc >/dev/null 2>&1; then
  compositor="labwc -c /usr/share/pineappleos/Desktop/data/labwc/rc.xml"
else
  log "labwc não encontrado; usando wayfire"
  compositor="wayfire"
fi

# ------------------------------------------------------------- serviços
log "iniciando pineapple-wallpaper (papel de parede)"
/usr/bin/pineapple-wallpaper &

log "iniciando pineapple-notifyd"
/usr/lib/pineappleos/pineapple-notifyd &

log "iniciando pineapple-shell (barra superior)"
/usr/lib/pineappleos/pineapple-shell &

log "iniciando pineapple-dock"
/usr/lib/pineappleos/pineapple-dock &

log "iniciando pineapple-launcher (oculto)"
/usr/lib/pineappleos/pineapple-launcher --hidden &

log "iniciando pineapple-launchpad (oculto)"
/usr/lib/pineappleos/pineapple-launchpad --hidden &

log "iniciando pineapple-mission (oculto)"
/usr/lib/pineappleos/pineapple-mission --hidden &

log "iniciando pineapple-gestures (daemon de gestos)"
/usr/lib/pineappleos/pineapple-gestures &

log "iniciando pineapple-ai (assistente)"
/usr/lib/pineappleos/pineapple-ai &

# ------------------------------------------------------------- apps iniciais
sleep 2
/usr/lib/pineappleos/pineapple-finder &
/usr/lib/pineappleos/pineapple-settings &

# ------------------------------------------------------------- compositor (front)
exec $compositor
