#!/bin/bash
# =============================================================================
#  build-debs.sh — empacota o Pineapple OS em pacotes .deb (dpkg-deb)
#
#  Pacotes gerados em dist/:
#   - pineapple-os-desktop_<ver>.deb   (shell, dock, launcher, launchpad, canopy)
#   - pineapple-os-apps_<ver>.deb      (apps Python + IA)
#   - pineapple-os-themes_<ver>.deb    (temas, ícones, wallpaper)
#   - pineapple-os-boot_<ver>.deb      (GRUB + Plymouth + Calamares)
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
    echo "Maintainer: Pineapple OS Project <dev@pineappleos.example>"
    echo "Description: $desc"
    [ -n "$deps" ] && echo "Depends: $deps"
    echo "Homepage: https://example.org/pineappleos"
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

echo "==> pineapple-os-desktop"
makedeb pineapple-os-desktop "Pineapple OS desktop components (shell, dock, launcher, launchpad, canopy)" \
  "libgtk-4-1, libgtk-4-layer-shell0, libadwaita-1-0" desktop.list

echo "==> pineapple-os-apps"
makedeb pineapple-os-apps "Pineapple OS applications and AI assistant" \
  "python3-gi, gir1.2-gtk-4.0" apps.list

echo "==> pineapple-os-themes"
makedeb pineapple-os-themes "Pineapple OS themes, icons and wallpaper" \
  "librsvg2-common, hicolor-icon-theme" themes.list

echo "==> pineapple-os-boot"
makedeb pineapple-os-boot "Pineapple OS boot themes (GRUB, Plymouth) and Calamares" \
  "" boot.list

echo "==> Pacotes gerados:"
ls -lh "$DIST_DIR"
