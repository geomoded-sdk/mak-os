#!/bin/bash
# =============================================================================
#  setup-systemd.sh — instala os serviços de sessão (user) do Pineapple OS
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/Installer/systemd"
DEST="$HOME/.config/systemd/user"

mkdir -p "$DEST"
echo "==> Copiando unit files para $DEST"
cp "$SRC"/*.service "$SRC"/*.target "$DEST/"

echo "==> Recarregando systemd (user)"
systemctl --user daemon-reload

echo "==> Habilitando a sessão"
systemctl --user enable --now pineappleos-session.target || true

echo "==> Serviços habilitados:"
for u in pineapple-wallpaper pineapple-shell pineapple-dock pineapple-launcher pineapple-launchpad pineapple-mission pineapple-gestures pineapple-notifyd pineapple-control-center pineapple-ai; do
  systemctl --user enable "$u" 2>/dev/null || true
done

echo "==> Pronto. Verifique com:  systemctl --user status"