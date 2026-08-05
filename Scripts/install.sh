#!/bin/bash
# =============================================================================
#  install.sh — instala o Mak OS no sistema (a partir do stage do build)
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$ROOT/build/stage"

[ -d "$STAGE" ] || { echo "Execute ./Scripts/build.sh antes" >&2; exit 1; }

echo "==> Instalando binários e arquivos"
sudo cp -r "$STAGE/usr/local/bin/"* /usr/local/bin/
sudo cp -r "$STAGE/usr/bin/"* /usr/bin/
sudo cp -r "$STAGE/usr/share/makos" /usr/share/
sudo cp -r "$STAGE/usr/share/applications/"* /usr/share/applications/
sudo cp -r "$STAGE/usr/share/themes/Mak-Dark" "$STAGE/usr/share/themes/Mak-Light" "$STAGE/usr/share/themes/Mak-HighSierra" /usr/share/themes/
sudo cp -r "$STAGE/usr/share/icons/mak-icons" /usr/share/icons/

echo "==> Atualizando caches"
sudo gtk-update-icon-cache -f /usr/share/icons/mak-icons || true
sudo update-desktop-database /usr/share/applications || true

echo "==> Instalando schemas GSettings"
sudo cp -r "$STAGE/usr/share/glib-2.0/schemas" /usr/share/glib-2.0/ 2>/dev/null || \
  sudo cp -r "$ROOT/Installer/schemas" /usr/share/glib-2.0/schemas/
sudo glib-compile-schemas /usr/share/glib-2.0/schemas || true

echo "==> Configurando sessão do usuário"
mkdir -p "$HOME/.config"
cat > "$HOME/.config/makos.env" <<EOF
export XDG_CURRENT_DESKTOP=MakOS
export GTK_THEME=Mak-HighSierra
export XDG_DATA_DIRS=/usr/share:/usr/local/share
EOF
grep -q "makos.env" "$HOME/.bashrc" 2>/dev/null || \
  echo 'test -f "$HOME/.config/makos.env" && . "$HOME/.config/makos.env"' >> "$HOME/.bashrc"

echo "==> Instalação concluída!"
echo "    Inicie a sessão com:  ./Scripts/start-session.sh"
