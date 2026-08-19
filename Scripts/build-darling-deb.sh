#!/bin/bash
# =============================================================================
#  build-darling-deb.sh — compila o Darling e gera o pacote .deb para a ISO
#
#  O resultado (Scripts/debs/darling_*.deb) é incluído automaticamente pelo
#  build-iso.sh, deixando o Darling PRÉ-INSTALADO na imagem.
#
#  Uso:
#    ./Scripts/build-darling-deb.sh              # Debian (detecta suíte)
#    DISTRO=debian ./Scripts/build-darling-deb.sh
#    DISTRO=ubuntu ./Scripts/build-darling-deb.sh
#
#  Nota: Darling é experimental e exige compilação (clang + ~30-60 min).
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/Scripts/debs"
WORK="${BUILD_DIR:-$ROOT/build/darling}"
DEST="$WORK/dest"
DISTRO="${DISTRO:-debian}"

mkdir -p "$OUT" "$DEST"

echo "==> Instalando dependências de build"
if [ "$DISTRO" = "ubuntu" ]; then
  sudo apt install -y \
    cmake automake clang bison flex xz-utils libfuse-dev libudev-dev pkg-config \
    libc6-dev-i386 gcc-multilib libcairo2-dev libgl1-mesa-dev curl libglu1-mesa-dev \
    libtiff-dev libfreetype6-dev git git-lfs libelf-dev libxml2-dev libegl1-mesa-dev \
    libfontconfig1-dev libbsd-dev libxrandr-dev libxcursor-dev libgif-dev libavutil-dev \
    libpulse-dev libavformat-dev libavcodec-dev libswresample-dev libdbus-1-dev \
    libxkbfile-dev libssl-dev libstdc++-12-dev ninja-build
else
  sudo apt install -y \
    cmake clang bison flex xz-utils libfuse-dev libudev-dev pkg-config \
    libc6-dev-i386 libcap2-bin git git-lfs libglu1-mesa-dev libcairo2-dev libgl1-mesa-dev \
    libtiff5-dev libfreetype6-dev libxml2-dev libegl1-mesa-dev libfontconfig1-dev \
    libbsd-dev libxrandr-dev libxcursor-dev libgif-dev libpulse-dev libavformat-dev \
    libavcodec-dev libswresample-dev libdbus-1-dev libxkbfile-dev libssl-dev llvm-dev \
    ninja-build gcc-multilib
fi

if [ ! -d "$WORK/darling" ]; then
  echo "==> Clonando Darling (git-lfs; proteção de clone desativada)"
  GIT_CLONE_PROTECTION_ACTIVE=false \
    git clone --recursive https://github.com/darlinghq/darling.git "$WORK/darling"
fi

echo "==> Atualizando submodules"
cd "$WORK/darling"
git pull --recurse-submodules 2>/dev/null || true
git submodule update --init --recursive

echo "==> Compilando (isso pode demorar bastante)"
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DTARGET_i386=OFF -GNinja
ninja

echo "==> Instalando em stage"
rm -rf "$DEST"
DESTDIR="$DEST" ninja install

echo "==> Gerando .deb"
VER="0.1.$(date +%Y%m%d)"
PKG="$WORK/pkg/darling"
rm -rf "$WORK/pkg"
mkdir -p "$PKG/DEBIAN"
cp -a "$DEST/." "$PKG/"

cat > "$PKG/DEBIAN/control" <<EOF
Package: darling
Version: $VER
Section: otherosfs
Priority: optional
Architecture: amd64
Maintainer: Pineapple OS Project <dev@pineappleos.example>
Depends: libc6 (>= 2.31)
Description: Darling — emulation layer for macOS applications
 Pre-built for the Pineapple OS installer (pré-instalado na ISO).
EOF

if command -v dpkg-shlibdeps >/dev/null 2>&1; then
  DEPS="$(dpkg-shlibdeps -O "$PKG"/usr/bin/* 2>/dev/null | sed 's/^shlibs:Depends=//' || true)"
  if [ -n "$DEPS" ]; then
    sed -i "s/^Depends: .*/Depends: $DEPS/" "$PKG/DEBIAN/control"
  fi
fi

dpkg-deb --build --root-owner-group "$PKG" "$OUT/darling_${VER}_amd64.deb"

echo "==> Pronto!"
echo "    Pacote: $OUT/darling_${VER}_amd64.deb"
echo "    A ISO (build-iso.sh) o inclui automaticamente em config/packages.chroot/."
