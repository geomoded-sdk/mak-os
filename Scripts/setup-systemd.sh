#!/bin/bash
# =============================================================================
#  setup-systemd.sh — instala os serviços de sessão (user) do Mak OS
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
systemctl --user enable --now makos-session.target || true

echo "==> Serviços habilitados:"
for u in mak-shell mak-dock mak-launcher mak-launchpad mak-mission mak-gestures mak-notifyd mak-control-center mak-ai; do
  systemctl --user enable "$u" 2>/dev/null || true
done

echo "==> Pronto. Verifique com:  systemctl --user status"