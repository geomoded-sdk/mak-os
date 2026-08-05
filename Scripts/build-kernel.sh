#!/bin/bash
# ============================================================
#  build-kernel.sh — compila o kernel Mak OS a partir do config
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${VERSION:-6.1}"
CONFIG_FILE="$ROOT/Kernel/config-6.1-makos"
TARGET_DIR="$ROOT/Kernel/build"

command -v make >/dev/null 2>&1 || { echo "make não encontrado" >&2; exit 1; }

echo "==> Baixando kernel $VERSION"
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

if [ ! -d "linux-$VERSION" ]; then
  wget -qO- "https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-$VERSION.tar.xz" \
    | tar xJ
fi

cd "linux-$VERSION"
cp "$CONFIG_FILE" .config
make olddefconfig

echo "==> Compilando (use -j$(nproc))"
make -j"$(nproc)" bzImage modules

echo "==> Instalando módulos"
sudo make modules_install

echo "==> Instalando kernel e initramfs"
sudo cp arch/x86/boot/bzImage /boot/vmlinuz-$VERSION-makos
sudo update-initramfs -c -k $VERSION-makos
sudo update-grub

echo "==> Kernel instalado. Reinicie para usar o Mak OS."
