#!/bin/bash
# =============================================================================
#  setup-flatpak.sh — habilita Flatpak + Flathub no Pineapple OS
# =============================================================================
set -euo pipefail

echo "==> Verificando Flatpak"
if ! command -v flatpak >/dev/null 2>&1; then
  sudo apt install -y flatpak gnome-software-plugin-flatpak
fi

echo "==> Adicionando Flathub"
flatpak remote-add --if-not-exists flathub \
  https://dl.flathub.org/repo/flathub.flatpakrepo

echo "==> Configurando permissões para o Pineapple Store"
mkdir -p "$HOME/.config"
cat > "$HOME/.config/flatpak.ini" <<EOF
[Core]
Architectures=amd64
EOF

echo "==> Flatpak pronto. Instale apps com:  flatpak install flathub <app>"
