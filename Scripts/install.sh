#!/bin/bash
# =============================================================================
#  install.sh — instala o Pineapple OS no sistema (a partir do stage do build)
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$ROOT/build/stage"

[ -d "$STAGE" ] || { echo "Execute ./Scripts/build.sh antes" >&2; exit 1; }

echo "==> Instalando binários e arquivos"
sudo cp -r "$STAGE/usr/local/bin/"* /usr/local/bin/
sudo cp -r "$STAGE/usr/bin/"* /usr/bin/
sudo cp -r "$STAGE/usr/share/pineappleos" /usr/share/
sudo cp -r "$STAGE/usr/share/applications/"* /usr/share/applications/
sudo cp -r "$STAGE/usr/share/themes/Pineapple-Dark" "$STAGE/usr/share/themes/Pineapple-Light" "$STAGE/usr/share/themes/Pineapple-HighSierra" /usr/share/themes/
sudo cp -r "$STAGE/usr/share/icons/pineapple-icons" /usr/share/icons/

echo "==> Atualizando caches"
sudo gtk-update-icon-cache -f /usr/share/icons/pineapple-icons || true
sudo update-desktop-database /usr/share/applications || true

echo "==> Instalando schemas GSettings"
sudo cp -r "$STAGE/usr/share/glib-2.0/schemas" /usr/share/glib-2.0/ 2>/dev/null || \
  sudo cp -r "$ROOT/Installer/schemas" /usr/share/glib-2.0/schemas/
sudo glib-compile-schemas /usr/share/glib-2.0/schemas || true

echo "==> Instalando identidade do sistema (os-release)"
sudo cp "$STAGE/etc/os-release" /etc/os-release 2>/dev/null || true

echo "==> Configurando sessão do usuário"
mkdir -p "$HOME/.config"
cat > "$HOME/.config/pineappleos.env" <<EOF
export XDG_CURRENT_DESKTOP=PineappleOS
export GTK_THEME=Pineapple-HighSierra
export XDG_DATA_DIRS=/usr/share:/usr/local/share
EOF
grep -q "pineappleos.env" "$HOME/.bashrc" 2>/dev/null || \
  echo 'test -f "$HOME/.config/pineappleos.env" && . "$HOME/.config/pineappleos.env"' >> "$HOME/.bashrc"

echo "==> Instalação concluída!"
echo "    Inicie a sessão com:  ./Scripts/start-session.sh"
