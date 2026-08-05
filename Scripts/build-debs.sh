#!/bin/bash
# =============================================================================
#  build-debs.sh — empacota o Mak OS em pacotes .deb (dpkg-deb)
#
#  Pacotes gerados em dist/:
#   - mak-os-desktop_<ver>.deb   (shell, dock, launcher, launchpad, finder)
#   - mak-os-apps_<ver>.deb      (apps Python + IA)
#   - mak-os-themes_<ver>.deb    (temas, ícones, wallpaper)
#   - mak-os-boot_<ver>.deb      (GRUB + Plymouth + Calamares)
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${VERSION:-0.1.0}"
DIST_DIR="$ROOT/dist"
WORK="$ROOT/build/debs"

rm -rf "$DIST_DIR" "$WORK"
mkdir -p "$DIST_DIR" "$WORK"

stage="build/stage"
[ -d "$stage" ] || { echo "execute ./Scripts/build.sh primeiro" >&2; exit 1; }

echo "==> Empacotando componentes"

makedeb() {
  local pkg="$1"; shift
  local name="$1" desc="$1"; shift
  local deps="$1"; shift
  local tree="$1"   # arquivo com lista de caminhos relativos (ou diretório)

  local pdir="$WORK/$pkg"
  mkdir -p "$pdir/DEBIAN"

  {
    echo "Package: $pkg"
    echo "Version: $VERSION"
    echo "Section: x11"
    echo "Priority: optional"
    echo "Architecture: amd64"
    echo "Maintainer: Mak OS Project <dev@makos.example>"
    echo "Description: $desc"
    [ -n "$deps" ] && echo "Depends: $deps"
    echo "Homepage: https://example.org/makos"
  } > "$pdir/DEBIAN/control"

  while read -r rel; do
    [ -n "$rel" ] || continue
    for src in "$stage"/$rel; do
      [ -e "$src" ] || continue
      local dest_rel="${src#"$stage"/}"
      mkdir -p "$pdir/$(dirname "$dest_rel")"
      cp -a "$src" "$pdir/$dest_rel"
    done
  done < "$ROOT/Scripts/deb-lists/$tree"

  dpkg-deb --build --root-owner-group "$pdir" "$DIST_DIR/$pkg_$VERSION"
}

echo "==> mak-os-desktop"
makedeb mak-os-desktop "Mak OS desktop components (shell, dock, launcher, launchpad, finder)" \
  "libgtk-4-1, libgtk-4-layer-shell0, libadwaita-1-0" desktop.list

echo "==> mak-os-apps"
makedeb mak-os-apps "Mak OS applications and AI assistant" \
  "python3-gi, gir1.2-gtk-4.0" apps.list

echo "==> mak-os-themes"
makedeb mak-os-themes "Mak OS themes, icons and wallpaper" \
  "librsvg2-common, hicolor-icon-theme" themes.list

echo "==> mak-os-boot"
makedeb mak-os-boot "Mak OS boot themes (GRUB, Plymouth) and Calamares" \
  "" boot.list

echo "==> Pacotes gerados:"
ls -lh "$DIST_DIR"
