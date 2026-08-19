#!/bin/bash
# =============================================================================
#  prepare.sh — prepara o ambiente antes do compositor iniciar
# =============================================================================
set -euo pipefail

export XDG_SESSION_TYPE=wayland
export XDG_CURRENT_DESKTOP=PineappleOS

# Aplica o papel de parede (tema próprio) via compositor/kanshi se disponível
if [ -f /usr/share/backgrounds/pineappleos/wallpaper.svg ]; then
  true  # definido pelo WCAG/background do compositor
fi

# Garante que as variáveis de ambiente do usuário estejam disponíveis
if [ -f "$HOME/.config/pineappleos.env" ]; then
  # shellcheck disable=SC1091
  . "$HOME/.config/pineappleos.env"
fi

exit 0