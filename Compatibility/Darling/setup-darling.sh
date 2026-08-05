#!/bin/bash
# =============================================================================
#  setup-darling.sh — instala o Darling (camada de compatibilidade macOS)
#
#  Nota: Darling é experimental e exige compilação. Este script instala as
#  dependências e compila a partir do repositório oficial.
# =============================================================================
set -euo pipefail

echo "==> Instalando dependências de build"
sudo apt install -y \
  build-essential cmake ninja-build clang bison flex gettext libxml2-dev \
  libssl-dev zlib1g-dev libpam0g-dev libfuse-dev libicu-dev

BUILD_DIR="${BUILD_DIR:-$HOME/darling-build}"
if [ ! -d "$BUILD_DIR/darling" ]; then
  echo "==> Clonando Darling"
  mkdir -p "$BUILD_DIR"
  git clone --recursive https://github.com/darlinghq/darling.git "$BUILD_DIR/darling"
fi

echo "==> Compilando (isso pode demorar bastante)"
cd "$BUILD_DIR/darling"
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -GNinja
ninja

echo "==> Instalando"
sudo ninja install

echo "==> Pronto. Rode aplicativos macOS com:  darling open app.app"
echo "    (veja a lista de apps suportados em darlinghq.org)"
