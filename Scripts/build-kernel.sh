#!/bin/bash
# =============================================================================
#  build-kernel.sh — compila o kernel do Pineapple OS
#
#  O que acontece:
#    1. Usa a árvore local Kernel/linux-<versao>.
#    2. Aplica o config próprio (Kernel/config-6.1-pineappleos).
#    3. Compila o kernel (bzImage) e os módulos.
#    4. Compila o LPNU do fonte (lpnu.ko + apfs.ko) contra este kernel e
#       instala o ld-mac — OBRIGATÓRIO (aborta se falhar).
#    5. Instala tudo e regenera o initramfs (que embute o PowerBook ID check).
#
#  Variáveis:
#    VERSION=6.1          versão do kernel (padrão: 6.1)
#    CONFIG_FILE=...      caminho alternativo do config
#    KERNEL_BUILD_OUT=... se definido, EMPACOTA o kernel (boot+initramfs+
#                         módulos+LPNU) nesse diretório em vez de instalar
#                         no sistema (usado pelo CI do GitHub).
#
#  Requisitos: make, gcc, libssl-dev, libelf-dev, flex, bison, pahole/dwarves
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${VERSION:-6.1}"
CONFIG_FILE="$ROOT/Kernel/config-6.1-pineappleos"
TARGET_DIR="$ROOT/Kernel/build"
KERNEL_SOURCE_DIR="${KERNEL_SOURCE_DIR:-$ROOT/Kernel/linux-$VERSION}"
KERNEL_ARCHIVE="${KERNEL_ARCHIVE:-$ROOT/Kernel/vendor/linux-$VERSION.tar.xz}"
KERNEL_BUILD_OUT="${KERNEL_BUILD_OUT:-}"
KERNSRC="$KERNEL_SOURCE_DIR"

command -v make >/dev/null 2>&1 || { echo "make não encontrado" >&2; exit 1; }

echo "==> Usando fonte local do kernel: $KERNEL_SOURCE_DIR"
mkdir -p "$TARGET_DIR"
if [ ! -d "$KERNEL_SOURCE_DIR" ]; then
  if [ ! -f "$KERNEL_ARCHIVE" ] && compgen -G "$KERNEL_ARCHIVE.part-*" >/dev/null; then
    KERNEL_ARCHIVE="$TARGET_DIR/linux-$VERSION.tar.xz"
    cat "$ROOT/Kernel/vendor/linux-$VERSION.tar.xz.part-"* > "$KERNEL_ARCHIVE"
  fi
  if [ -f "$KERNEL_ARCHIVE" ]; then
    echo "==> Extraindo arquivo local do kernel: $KERNEL_ARCHIVE"
    tar -xJf "$KERNEL_ARCHIVE" -C "$ROOT/Kernel"
  else
    echo "ERRO: fonte local ausente: $KERNEL_SOURCE_DIR" >&2
    echo "Coloque a arvore Linux $VERSION ou o arquivo $KERNEL_ARCHIVE." >&2
    exit 1
  fi
fi

cd "$KERNEL_SOURCE_DIR"

# Integra codigo Pineapple diretamente na arvore Linux vendorizada.
PINEAPPLE_SOURCE="$ROOT/Kernel/pineapple"
mkdir -p "$KERNSRC/drivers/pineapple"
cp "$PINEAPPLE_SOURCE/Kconfig" "$PINEAPPLE_SOURCE/Makefile" \
  "$PINEAPPLE_SOURCE/pineapple_core.c" "$KERNSRC/drivers/pineapple/"
grep -qxF 'source "drivers/pineapple/Kconfig"' "$KERNSRC/drivers/Kconfig" \
  || printf '\nsource "drivers/pineapple/Kconfig"\n' >> "$KERNSRC/drivers/Kconfig"
grep -qxF 'obj-$(CONFIG_PINEAPPLE_CORE) += pineapple/' "$KERNSRC/drivers/Makefile" \
  || printf '\nobj-$(CONFIG_PINEAPPLE_CORE) += pineapple/\n' >> "$KERNSRC/drivers/Makefile"

# Config próprio (identidade + otimizações + MAGIC_SYSRQ para o PowerBook ID)
echo "==> Aplicando config do Pineapple OS"
cp "$CONFIG_FILE" .config
make olddefconfig

echo "==> Compilando (use -j$(nproc))"
make -j"$(nproc)" bzImage modules

echo "==> Instalando módulos"
sudo make modules_install

# =============================================================================
#  LPNU — kernel compatibility layer (macOS) — integração OBRIGATÓRIA
#
#  Fonte: https://github.com/geomoded-sdk/lpnu/releases/tag/v2.0.0
#
#  Os módulos são COMPILADOS DO FONTE contra ESTE kernel: os .ko pré-compilados
#  do release são do kernel 6.17.0-1011-azure e NÃO carregam num kernel custom
#  (vermagic + modversions). Compilando do fonte, os dois batem.
#    * lpnu.ko  — kernel compatibility layer (execução de binários macOS)
#    * apfs.ko  — filesystem APFS (linux-apfs-rw v0.3.19, o mesmo do release)
#    * ld-mac   — Mach-O loader (binário pré-compilado do release, sha256)
#
#  Se qualquer etapa falhar (download, integridade, compilação ou vermagic),
#  o build é ABORTADO — o Pineapple OS não compila sem o LPNU.
# =============================================================================
LPNU_TAG="v2.0.0"
APFS_TAG="v0.3.19"
LPNU_REPO="https://github.com/geomoded-sdk/lpnu/archive/refs/tags/$LPNU_TAG.tar.gz"
APFS_REPO="https://github.com/linux-apfs/linux-apfs-rw/archive/refs/tags/$APFS_TAG.tar.gz"
LPNU_BASE="https://github.com/geomoded-sdk/lpnu/releases/download/$LPNU_TAG"
LPNU_SRC="$TARGET_DIR/lpnu-src"
APFS_SRC="$TARGET_DIR/apfs-src"
KRELEASE="$(make -s kernelrelease)"
MODEXTRA="/lib/modules/$KRELEASE/extra"

echo "==> [LPNU] Baixando fontes e componentes (obrigatório)"
mkdir -p "$LPNU_SRC" "$APFS_SRC"
[ -s "$TARGET_DIR/lpnu-$LPNU_TAG.tar.gz" ] \
  || wget -qO "$TARGET_DIR/lpnu-$LPNU_TAG.tar.gz" "$LPNU_REPO" \
  || { echo "ERRO: falha ao baixar o fonte do LPNU" >&2; exit 1; }
[ -s "$TARGET_DIR/linux-apfs-rw-$APFS_TAG.tar.gz" ] \
  || wget -qO "$TARGET_DIR/linux-apfs-rw-$APFS_TAG.tar.gz" "$APFS_REPO" \
  || { echo "ERRO: falha ao baixar o fonte do linux-apfs-rw" >&2; exit 1; }
[ -s "$TARGET_DIR/ld-mac" ] \
  || curl -fsSL -H 'Accept: application/octet-stream' \
    -o "$TARGET_DIR/ld-mac" \
    "https://api.github.com/repos/geomoded-sdk/lpnu/releases/assets/402871192" \
  || { echo "ERRO: falha ao baixar o ld-mac do LPNU" >&2; exit 1; }

echo "==> [LPNU] Verificando integridade do ld-mac (sha256)"
ld_got="$(sha256sum "$TARGET_DIR/ld-mac" | cut -d' ' -f1)"
if [ "$ld_got" != "e7ee78932e6f7abd21cd320af6b7e6895875306a4e491b50bd78ae6faaa9c4a5" ]; then
  echo "ERRO: sha256 de ld-mac não confere ($ld_got)" >&2
  exit 1
fi

echo "==> [LPNU] Extraindo fontes"
tar xzf "$TARGET_DIR/lpnu-$LPNU_TAG.tar.gz" -C "$LPNU_SRC" --strip-components=1
tar xzf "$TARGET_DIR/linux-apfs-rw-$APFS_TAG.tar.gz" -C "$APFS_SRC" --strip-components=1
printf '#define GIT_COMMIT "%s"\n' "$APFS_TAG" > "$APFS_SRC/version.h"

echo "==> [LPNU] Compilando lpnu.ko contra $KRELEASE"
make -C "$KERNSRC" M="$LPNU_SRC/linux-7.0/fs/lpnu" modules
LPNU_KO="$LPNU_SRC/linux-7.0/fs/lpnu/lpnu.ko"
[ -f "$LPNU_KO" ] || { echo "ERRO: lpnu.ko não foi gerado" >&2; exit 1; }

echo "==> [LPNU] Compilando apfs.ko contra $KRELEASE"
make -C "$KERNSRC" M="$APFS_SRC" \
  EXTRA_CFLAGS="-I$KERNSRC/include/generated/uapi/linux" modules
APFS_KO="$APFS_SRC/apfs.ko"
[ -f "$APFS_KO" ] || { echo "ERRO: apfs.ko não foi gerado" >&2; exit 1; }

echo "==> [LPNU] Verificando vermagic (obrigatório)"
for ko in "$LPNU_KO" "$APFS_KO"; do
  if ! strings "$ko" | grep -q "vermagic=$KRELEASE"; then
    echo "ERRO: vermagic de $ko não bate com $KRELEASE:" >&2
    strings "$ko" | grep -o 'vermagic=[^ ]*' || true
    exit 1
  fi
done
echo "    vermagic confirmado para $KRELEASE"

echo "==> [LPNU] Instalando módulos"
sudo mkdir -p "$MODEXTRA"
sudo install -m 0644 "$LPNU_KO" "$APFS_KO" "$MODEXTRA/"
sudo depmod -a "$KRELEASE"

echo "==> [LPNU] Instalando ld-mac (Mach-O loader)"
sudo install -m 0755 "$TARGET_DIR/ld-mac" /usr/local/bin/ld-mac

echo "==> [LPNU] Ativando lpnu + apfs no boot (carregamento automático)"
sudo tee /etc/modules-load.d/pineapple-lpnu.conf >/dev/null <<'EOF'
lpnu
apfs
EOF

# ---------------------------------------------------------------------------
#  Modo CI/empacotamento: não mexe no /boot/GRUB do runner; só empacota o
#  kernel, o initramfs (com PowerBook ID + BFS check) e os componentes LPNU.
# ---------------------------------------------------------------------------
if [ -n "$KERNEL_BUILD_OUT" ]; then
  echo "==> Empacotando kernel em $KERNEL_BUILD_OUT (modo CI)"
  mkdir -p "$KERNEL_BUILD_OUT"/boot "$KERNEL_BUILD_OUT"/lib/modules \
           "$KERNEL_BUILD_OUT"/usr/local/bin

  cp arch/x86/boot/bzImage "$KERNEL_BUILD_OUT/boot/vmlinuz-$KRELEASE"
  cp -a "/lib/modules/$KRELEASE" "$KERNEL_BUILD_OUT/lib/modules/"

  # Embute o PowerBook ID + BFS check no initramfs empacotado
  sudo mkdir -p /usr/share/pineappleos \
                /usr/share/initramfs-tools/hooks \
                /usr/share/initramfs-tools/scripts/init-bottom
  sudo cp "$ROOT/ids.txt" /usr/share/pineappleos/ids.txt
  sudo cp "$ROOT/Installer/initramfs/hooks/pineapple-powerbook-check" \
    /usr/share/initramfs-tools/hooks/
  sudo cp "$ROOT/Installer/initramfs/scripts/init-bottom/pineapple-powerbook-check" \
    /usr/share/initramfs-tools/scripts/init-bottom/
  sudo chmod +x /usr/share/initramfs-tools/hooks/pineapple-powerbook-check \
                /usr/share/initramfs-tools/scripts/init-bottom/pineapple-powerbook-check

  if command -v update-initramfs >/dev/null 2>&1; then
    echo "==> Gerando initramfs"
    sudo update-initramfs -c -k "$KRELEASE" || true
    [ -f "/boot/initrd.img-$KRELEASE" ] \
      && cp "/boot/initrd.img-$KRELEASE" "$KERNEL_BUILD_OUT/boot/"
  fi

  cp /usr/local/bin/ld-mac "$KERNEL_BUILD_OUT/usr/local/bin/"
  cp /etc/modules-load.d/pineapple-lpnu.conf "$KERNEL_BUILD_OUT/"
  cp "$LPNU_KO" "$APFS_KO" "$KERNEL_BUILD_OUT/"

  echo "==> Pacote do kernel pronto em: $KERNEL_BUILD_OUT"
  find "$KERNEL_BUILD_OUT" -type f | sort
  exit 0
fi

echo "==> Instalando kernel e initramfs"
sudo cp arch/x86/boot/bzImage /boot/vmlinuz-$VERSION-pineappleos
sudo update-initramfs -c -k "$KRELEASE"

# Garante que o PowerBook ID check esteja dentro do initramfs
if [ -x "$ROOT/Scripts/setup-powerbook-check.sh" ]; then
  echo "==> Reaplicando PowerBook ID check"
  "$ROOT/Scripts/setup-powerbook-check.sh"
fi

sudo update-grub

echo "==> Kernel instalado. Reinicie para usar o Pineapple OS."
echo "    Lembre-se do argumento: -pineapplepowerbookid=<ID> (senão: panic)"
echo "    LPNU compilado do fonte para este kernel: lpnu.ko, apfs.ko, ld-mac"