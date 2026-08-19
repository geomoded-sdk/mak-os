#!/bin/bash
# =============================================================================
#  pineapple-appimage — gerenciador de AppImages do Pineapple OS
#
#  Registra AppImages no sistema (executável + entrada no Launcher).
#
#  Uso:
#    pineapple-appimage <arquivo.AppImage>       registrar um app
#    pineapple-appimage --list                   listar apps registrados
#    pineapple-appimage --remove <nome>          remover um app
# =============================================================================
set -euo pipefail

APPIMAGE_DIR="${APPIMAGE_DIR:-$HOME/Applications}"
APP_DIR="$HOME/.local/share/applications"
BIN_DIR="$HOME/.local/bin"
mkdir -p "$APPIMAGE_DIR" "$APP_DIR" "$BIN_DIR"

slug() { echo "$1" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-'; }

case "${1:-}" in
  --list)
    echo "==> AppImages registrados:"
    for app in "$APP_DIR"/*.appimage.desktop; do
      [ -e "$app" ] || continue
      grep -h '^Name=' "$app" | cut -d= -f2
    done
    exit 0
    ;;
  --remove)
    name="$(slug "$2")"
    rm -f "$APP_DIR/$name.appimage.desktop" "$BIN_DIR/$name"
    echo "removido: $name"
    exit 0
    ;;
  *)
    [ -n "${1:-}" ] || { echo "uso: pineapple-appimage <arquivo.AppImage>" >&2; exit 1; }
    src="$(realpath "$1")"
    [ -f "$src" ] || { echo "arquivo não encontrado: $src" >&2; exit 1; }
    base="$(basename "$src" .AppImage)"
    id="$(slug "$base")"
    chmod +x "$src"
    ln -sf "$src" "$BIN_DIR/$id"
    cat > "$APP_DIR/$id.appimage.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$base
Comment=AppImage gerenciado pelo Pineapple OS
Exec=$BIN_DIR/$id --appimage-extract-and-run
Icon=application-x-executable
Terminal=false
Categories=Application;
EOF
    echo "registrado: $base ($id)"
    echo "Pode ser necessário atualizar o cache:  update-desktop-database $APP_DIR"
    ;;
esac
