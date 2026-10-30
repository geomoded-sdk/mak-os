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

echo "==> Compilando runtime PNFS nativo para preboot"
make -C "$ROOT/Filesystem/pineapplefs-c"
sudo install -D -m 0755 "$ROOT/Filesystem/pineapplefs-c/pineapplefs-mkfs" \
  /usr/local/bin/pineapplefs-mkfs

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

# =============================================================================
#  Identidade Pineapple — modifica o fonte Linux de verdade (uname/proc/version)
#
#  O sistema que roda É o Linux, mas se identifica como "Pineapple" em:
#    * uname -s / uname -r          → Pineapple / <release>-pineappleos
#    * /proc/version                → "Pineapple version …"
#  (mesma filosofia do Android, que renomeia o banner do kernel.)
# =============================================================================
echo "==> Aplicando identidade Pineapple no fonte (uts.h / version.c)"
# UTS_SYSNAME: define o sysname do uname e a primeira palavra de /proc/version.
# Não use xargs aqui: algumas versões do kernel não têm essa macro no mesmo
# arquivo e o grep retorna 1, fazendo o pipeline abortar sob `set -e`.
patched_identity=0
while IFS= read -r -d '' f; do
  if grep -q 'UTS_SYSNAME "Linux"' "$f"; then
    sed -i 's/UTS_SYSNAME "Linux"/UTS_SYSNAME "Pineapple"/' "$f"
    echo "    patch: $f"
    patched_identity=1
  fi
done < <(find include init -type f \( -name '*.h' -o -name '*.c' \) -print0 2>/dev/null)

# fallback para árvores onde UTS_SYSNAME vive em outro lugar
if [ "$patched_identity" -eq 0 ]; then
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    sed -i 's/"Linux"/"Pineapple"/g' "$f"
    echo "    patch(fallback): $f"
    patched_identity=1
  done < <(grep -rl '"Linux"' include/linux/uts.h include/uapi/linux/utsname.h \
    init/version.c 2>/dev/null || true)
fi

if [ "$patched_identity" -eq 0 ]; then
  echo "    aviso: fonte não expõe UTS_SYSNAME; mantendo identidade padrão" >&2
fi

# Integra codigo Pineapple diretamente na arvore Linux vendorizada.
PINEAPPLE_SOURCE="$ROOT/Kernel/pineapple"
DEST="$KERNSRC/drivers/pineapple"
mkdir -p "$DEST/bsd" "$DEST/bootargs" "$DEST/hwcheck" "$DEST/pnfs"
cp "$PINEAPPLE_SOURCE/Kconfig" "$PINEAPPLE_SOURCE/Makefile" \
   "$PINEAPPLE_SOURCE/pineapple_core.c" "$DEST/"
cp "$PINEAPPLE_SOURCE/bsd/pineapple_bsd.c" "$DEST/bsd/"
cp "$PINEAPPLE_SOURCE/bootargs/pineapple_boot.c" "$DEST/bootargs/"
cp "$PINEAPPLE_SOURCE/hwcheck/pineapple_hwcheck.c" "$DEST/hwcheck/"
cp "$PINEAPPLE_SOURCE/pnfs/pnfs_fs.c" "$DEST/pnfs/"
grep -qxF 'source "drivers/pineapple/Kconfig"' "$KERNSRC/drivers/Kconfig" \
  || printf '\nsource "drivers/pineapple/Kconfig"\n' >> "$KERNSRC/drivers/Kconfig"
grep -qxF 'obj-y += pineapple/' "$KERNSRC/drivers/Makefile" \
  || printf '\nobj-y += pineapple/\n' >> "$KERNSRC/drivers/Makefile"

# =============================================================================
#  Headers gerados POR BUILD — allowlist de hardware + IDs do PowerBook
#
#  Cada build embute SUAS listas:
#    * Kernel/hwlist.txt  → allowed_hw.h  (hardware aceito por esta build;
#      placa fora da lista = kernel panic no boot)
#    * ids.txt            → pineapple_ids.h (PowerBook IDs desta build)
# =============================================================================
echo "==> Gerando allowlist de hardware (Kernel/hwlist.txt → allowed_hw.h)"
bash "$ROOT/Scripts/gen-allowed-hw.sh" \
  "$ROOT/Kernel/hwlist.txt" "$DEST/hwcheck/allowed_hw.h"

echo "==> Gerando lista de PowerBook IDs (ids.txt → pineapple_ids.h)"
{
  echo "/* Gerado por build-kernel.sh — NÃO editar; fonte: ids.txt */"
  echo "static const char *pineapple_valid_ids[] = {"
  while IFS= read -r id; do
    id="$(echo "$id" | tr -d '[:space:]')"
    [ -z "$id" ] && continue
    printf '    "%s",\n' "$id"
  done < "$ROOT/ids.txt"
  echo "};"
  echo "static const unsigned int pineapple_valid_ids_count ="
  echo "    sizeof(pineapple_valid_ids) / sizeof(pineapple_valid_ids[0]);"
} > "$DEST/bootargs/pineapple_ids.h"

# Config próprio (identidade + otimizações + MAGIC_SYSRQ para o PowerBook ID)
echo "==> Aplicando config do Pineapple OS"
cp "$CONFIG_FILE" .config

# Habilita os módulos Pineapple (identidade, BSD, boot-args, hwcheck, PNFS).
# A allowlist de hardware e os IDs desta build já foram gerados acima.
if [ -x scripts/config ]; then
  scripts/config --enable PINEAPPLE_CORE \
                 --enable PINEAPPLE_BSD \
                 --enable PINEAPPLE_BOOT \
                 --enable PINEAPPLE_BOOT_ENFORCE \
                 --enable PINEAPPLE_HWCHECK \
                 --enable PINEAPPLE_PNFS
else
  for opt in PINEAPPLE_CORE PINEAPPLE_BSD PINEAPPLE_BOOT \
             PINEAPPLE_BOOT_ENFORCE PINEAPPLE_HWCHECK PINEAPPLE_PNFS; do
    if grep -q "^# ${opt} is not set" .config; then
      sed -i "s/^# ${opt} is not set/${opt}=y/" .config
    elif ! grep -q "^${opt}=y" .config; then
      printf '%s=y\n' "$opt" >> .config
    fi
  done
fi
make HOSTCFLAGS="-std=gnu11" olddefconfig

echo "==> Compilando (use -j$(nproc))"
make HOSTCFLAGS="-std=gnu11" -j"$(nproc)" bzImage modules

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
#  kernel, o initramfs (com PowerBook ID + PNFS check) e os componentes LPNU.
# ---------------------------------------------------------------------------
if [ -n "$KERNEL_BUILD_OUT" ]; then
  echo "==> Empacotando kernel em $KERNEL_BUILD_OUT (modo CI)"
  mkdir -p "$KERNEL_BUILD_OUT"/boot "$KERNEL_BUILD_OUT"/lib/modules \
           "$KERNEL_BUILD_OUT"/usr/local/bin

  # Identidade: o artefato NÃO se chama vmlinuz — é pineapple.ekern.
  cp arch/x86/boot/bzImage "$KERNEL_BUILD_OUT/boot/pineapple.ekern-$KRELEASE"
  cp -a "/lib/modules/$KRELEASE" "$KERNEL_BUILD_OUT/lib/modules/"

  # Embute o PowerBook ID + PNFS check no initramfs empacotado
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
    sudo update-initramfs -c -k "$KRELEASE"
    [ -f "/boot/initrd.img-$KRELEASE" ] || {
      echo "ERRO: initramfs Pineapple não foi gerado" >&2
      exit 1
    }
    cp "/boot/initrd.img-$KRELEASE" "$KERNEL_BUILD_OUT/boot/"
  fi

  cp /usr/local/bin/ld-mac "$KERNEL_BUILD_OUT/usr/local/bin/"
  cp /etc/modules-load.d/pineapple-lpnu.conf "$KERNEL_BUILD_OUT/"
  cp "$LPNU_KO" "$APFS_KO" "$KERNEL_BUILD_OUT/"

  echo "==> Pacote do kernel pronto em: $KERNEL_BUILD_OUT"
  find "$KERNEL_BUILD_OUT" -type f | sort
  exit 0
fi

echo "==> Instalando kernel e initramfs"
# Identidade: instala como pineapple.ekern (nunca "vmlinuz").
sudo cp arch/x86/boot/bzImage "/boot/pineapple.ekern-$KRELEASE"
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
