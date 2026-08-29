#!/bin/bash
# =============================================================================
#  prepare.sh — prepara o ambiente antes do compositor iniciar
# =============================================================================
set -euo pipefail

export XDG_SESSION_TYPE=wayland
export XDG_CURRENT_DESKTOP=PineappleOS

# Aplica o papel de parede (tema próprio) via compositor/kanshi se disponível
# O compositor (wlroots/swaybg) só renderiza raster (PNG/JPG); SVG não.
for _w in wallpaper.png wallpaper.jpg wallpaper.jpeg; do
  if [ -f "/usr/share/backgrounds/pineappleos/$_w" ]; then
    true  # definido pelo WCAG/background do compositor
    break
  fi
done

# Garante que as variáveis de ambiente do usuário estejam disponíveis
if [ -f "$HOME/.config/pineappleos.env" ]; then
  # shellcheck disable=SC1091
  . "$HOME/.config/pineappleos.env"
fi

exit 0