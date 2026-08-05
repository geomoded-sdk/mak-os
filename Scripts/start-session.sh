#!/bin/bash
# =============================================================================
#  mak-session — inicia a sessão do Mak OS
# =============================================================================
set -euo pipefail

export XDG_CURRENT_DESKTOP=MakOS
export XDG_SESSION_TYPE=wayland
export GDK_BACKEND=wayland
export GTK_CSD=0
export GTK_THEME=Mak-Dark
export QT_QPA_PLATFORM=wayland
export MOZ_ENABLE_WAYLAND=1

log() { echo "[mak-session] $*"; }

# ------------------------------------------------------------- compositor
log "iniciando compositor (labwc)"
if command -v labwc >/dev/null 2>&1; then
  compositor="labwc -c /usr/share/makos/Desktop/data/labwc/rc.xml"
else
  log "labwc não encontrado; usando wayfire"
  compositor="wayfire"
fi

# ------------------------------------------------------------- serviços
log "iniciando mak-notifyd"
/usr/lib/makos/mak-notifyd &

log "iniciando mak-shell (barra superior)"
/usr/lib/makos/mak-shell &

log "iniciando mak-dock"
/usr/lib/makos/mak-dock &

log "iniciando mak-launcher (oculto)"
/usr/lib/makos/mak-launcher --hidden &

log "iniciando mak-ai (assistente)"
/usr/lib/makos/mak-ai &

# ------------------------------------------------------------- apps iniciais
sleep 2
/usr/lib/makos/mak-finder &
/usr/lib/makos/mak-settings &

# ------------------------------------------------------------- compositor (front)
exec $compositor
