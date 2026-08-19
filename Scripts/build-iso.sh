#!/bin/bash
# =============================================================================
#  build-iso.sh — gera a ISO do Pineapple OS a partir do live-build (Debian/Ubuntu)
# =============================================================================
# Uso:
#   ./build-iso.sh              # build padrão (debian stable amd64)
#   DISTRO=ubuntu SUITE=noble ./build-iso.sh
set -euo pipefail

# ------------------------------------------------------------------ configuração
DISTRO="${DISTRO:-debian}"
SUITE="${SUITE:-stable}"
ARCH="${ARCH:-amd64}"
OUTPUT="${OUTPUT:-build}"
MIRROR="${MIRROR:-http://deb.debian.org/debian/}"
# PowerBook ID obrigatório (ver ids.txt). Se vazio, o live boot entra em
# kernel panic até que o argumento -pineapplepowerbookid=<ID> seja fornecido
# na linha de comando do kernel (ex.: editando o GRUB na tela de boot).
POWERBOOK_ID="${POWERBOOK_ID:-}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LB_DIR="$ROOT/Installer/live-build"
WORKDIR="$ROOT/Installer/live-build/$OUTPUT"

echo "==> Pineapple OS ISO build"
echo "    distro=$DISTRO suite=$SUITE arch=$ARCH"
if [ -z "$POWERBOOK_ID" ]; then
  echo "    [ATENÇÃO] POWERBOOK_ID vazio — o live boot exigirá o argumento"
  echo "              -pineapplepowerbookid=<ID> no kernel (senão: panic)."
else
  echo "    powerbook_id=$POWERBOOK_ID"
fi

command -v lb >/dev/null 2>&1 || {
  echo "live-build não encontrado. Instale com: sudo apt install live-build" >&2
  exit 1
}

# ------------------------------------------------------------ preparar workdir
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

echo "==> Inicializando live-build (lb config)"

# Argumentos de boot estilo macOS:
#   quiet loglevel=0 rd.quiet  → esconde os logs de kernel (boot limpo)
#   splash                     → mostra o Plymouth (abacaxi sobre fundo claro)
#   -pineapplepowerbookid=ID   → ID do PowerBook (obrigatório; sem ele: panic)
BOOTARGS="boot=live components quiet loglevel=0 splash rd.quiet locale=pt_BR.UTF-8"
if [ -n "$POWERBOOK_ID" ]; then
  BOOTARGS="$BOOTARGS -pineapplepowerbookid=$POWERBOOK_ID"
fi

lb config \
  --distribution "$SUITE" \
  --architecture "$ARCH" \
  --architectures "$ARCH" \
  --system live \
  --binary-images iso-hybrid \
  --bootappend-live "$BOOTARGS" \
  --debian-installer live \
  --debian-installer-distribution "$SUITE" \
  --apt-recommends false \
  --archive-areas "main contrib non-free-firmware" \
  --mode "$DISTRO" \
  --mirror-bootstrap "$MIRROR" \
  --mirror-binary "$MIRROR"

# ------------------------------------------------------------ incluir pacotes
# Lista de pacotes base do Pineapple OS
cat > config/package-lists/pineappleos.list.chroot <<'EOF'
# --- sistema base ---
linux-image-amd64
linux-headers-amd64
build-essential
libelf-dev
libssl-dev
firmware-linux
firmware-linux-nonfree

# --- X / Wayland ---
xserver-xorg-core
xwayland
labwc
wayland-protocols
wayland-utils
libwlroots

# --- GTK4 e bibliotecas da interface ---
libgtk-4-1
libgtk-4-layer-shell0
libadwaita-1-0
gir1.2-gtk-4.0
vte-3.90
libvte-3.90-0
webkitgtk-6.0
libwebkitgtk-6.0-0
librsvg2-common
hicolor-icon-theme
fonts-inter
fonts-sora
swaybg

# --- serviços ---
pipewire
pipewire-pulse
wireplumber
bluez
network-manager
upower
accountsservice
dbus
polkitd
sddm

# --- apps e utilitários ---
gvfs
gvfs-backends
xdg-desktop-portal
xdg-desktop-portal-gtk
flatpak
apparmor
calamares
util-linux
file-roller
gnome-disk-utility
rsync
git

# --- compatibilidade ---
wine
winetricks
EOF

# Flatpak remoto por padrão
mkdir -p config/includes.chroot/usr/share/pineappleos/scripts
cat > config/includes.chroot/usr/share/pineappleos/scripts/setup-flatpak.sh <<'EOF'
#!/bin/bash
flatpak remote-add --if-not-exists flathub \
  https://dl.flathub.org/repo/flathub.flatpakrepo
EOF
chmod +x config/includes.chroot/usr/share/pineappleos/scripts/setup-flatpak.sh

# ------------------------------------------------------------ incluir Pineapple OS
echo "==> Copiando componentes do Pineapple OS para a imagem"
cp -r "$ROOT"/Desktop "$ROOT"/Dock "$ROOT"/Launcher "$ROOT"/Launchpad "$ROOT"/Mission \
      "$ROOT"/Finder "$ROOT"/Gestures "$ROOT"/AI "$ROOT"/Settings "$ROOT"/Store "$ROOT"/Apps \
      "$ROOT"/Themes "$ROOT"/Icons config/includes.chroot/usr/share/pineappleos/

# ------------------------------------------------------------ identidade do sistema
# /etc/os-release — o Pineapple OS deixa de aparecer como "Debian/GNU Linux"
# e passa a se identificar como Pineapple OS.
echo "==> Definindo identidade (os-release)"
mkdir -p config/includes.chroot/etc
cp "$ROOT/Installer/os-release" config/includes.chroot/etc/os-release

# ------------------------------------------------------------ PowerBook ID + panic
# A lista de IDs e o verificador de initramfs são embutidos na imagem.
# Durante o boot, se o argumento -pineapplepowerbookid=<ID> faltar (ou o ID
# for inválido), o kernel entra em PANIC estilo macOS e não inicia.
echo "==> Incluindo PowerBook ID check no initramfs"
mkdir -p config/includes.chroot/usr/share/pineappleos
cp "$ROOT/ids.txt" config/includes.chroot/usr/share/pineappleos/ids.txt
mkdir -p config/includes.chroot/usr/share/initramfs-tools/hooks
mkdir -p config/includes.chroot/usr/share/initramfs-tools/scripts/init-bottom
cp "$ROOT/Installer/initramfs/hooks/pineapple-powerbook-check" \
  config/includes.chroot/usr/share/initramfs-tools/hooks/
cp "$ROOT/Installer/initramfs/scripts/init-bottom/pineapple-powerbook-check" \
  config/includes.chroot/usr/share/initramfs-tools/scripts/init-bottom/
chmod +x config/includes.chroot/usr/share/initramfs-tools/hooks/pineapple-powerbook-check
chmod +x config/includes.chroot/usr/share/initramfs-tools/scripts/init-bottom/pineapple-powerbook-check

# ------------------------------------------------------------ temas de boot
# GRUB/Plymouth/SDDM estilo Apple + verificador de PowerBook
echo "==> Incluindo temas de boot"
mkdir -p config/includes.chroot/boot/grub/themes/pineappleos
mkdir -p config/includes.chroot/usr/share/plymouth/themes/pineappleos
mkdir -p config/includes.chroot/usr/share/sddm/themes/pineappleos
cp -r "$ROOT/Installer/grub/theme/." config/includes.chroot/boot/grub/themes/pineappleos/
cp -r "$ROOT/Installer/plymouth/theme/." config/includes.chroot/usr/share/plymouth/themes/pineappleos/
cp -r "$ROOT/Installer/sddm/theme/." config/includes.chroot/usr/share/sddm/themes/pineappleos/

# ------------------------------------------------------------ Darling pré-instalado
# Se houver .debs pré-compilados (gerados por build-darling-deb.sh), o
# live-build os instala na imagem → Darling já vem instalado na ISO.
if ls "$ROOT"/Scripts/debs/*.deb >/dev/null 2>&1; then
  echo "==> Incluindo Darling pré-compilado na imagem"
  mkdir -p config/packages.chroot
  cp "$ROOT"/Scripts/debs/*.deb config/packages.chroot/
fi

# ------------------------------------------------------------ LPNU (obrigatório)
# LPNU v2.0.0 — kernel compatibility layer (macOS): permite rodar binários
# Mach-O e montar APFS. Os módulos são COMPILADOS DO FONTE contra o kernel da
# própria ISO (os .ko pré-compilados do release são do 6.17-azure e não
# carregariam — vermagic/modversions). Aqui baixamos as fontes offline; o hook
# chroot (hooks/pineapple-lpnu.hook.chroot) compila e instala na imagem.
# Falhou em qualquer etapa → build da ISO é abortado.
echo "==> Incluindo LPNU (fontes + ld-mac) — obrigatório"
LPNU_DIR="config/includes.chroot/root/lpnu-build"
mkdir -p "$LPNU_DIR"
wget -qO "$LPNU_DIR/lpnu-src.tar.gz" \
  "https://github.com/geomoded-sdk/lpnu/archive/refs/tags/v2.0.0.tar.gz"
wget -qO "$LPNU_DIR/apfs-src.tar.gz" \
  "https://github.com/linux-apfs/linux-apfs-rw/archive/refs/tags/v0.3.19.tar.gz"
wget -qO "$LPNU_DIR/ld-mac" \
  "https://github.com/geomoded-sdk/lpnu/releases/download/v2.0.0/ld-mac"
if [ "$(sha256sum "$LPNU_DIR/ld-mac" | cut -d' ' -f1)" != \
     "e7ee78932e6f7abd21cd320af6b7e6895875306a4e491b50bd78ae6faaa9c4a5" ]; then
  echo "==> ERRO: sha256 de ld-mac não confere" >&2
  exit 1
fi
chmod +x "$LPNU_DIR/ld-mac"
mkdir -p config/hooks/normal
cp "$ROOT/Installer/live-build/hooks/pineapple-lpnu.hook.chroot" \
  config/hooks/normal/0001-pineapple-lpnu.hook.chroot
chmod +x config/hooks/normal/0001-pineapple-lpnu.hook.chroot

# ------------------------------------------------------------ build
echo "==> Gerando a ISO (isso pode levar vários minutos)"
lb build 2>&1 | tee "$ROOT/Installer/live-build/build.log"

ISO=$(ls live-image-*.hybrid.iso 2>/dev/null || ls *.iso 2>/dev/null | head -n1)
if [ -n "$ISO" ]; then
  cp "$ISO" "$ROOT/pineappleos-$SUITE-$ARCH.iso"
  echo "==> ISO criada: $ROOT/pineappleos-$SUITE-$ARCH.iso"
else
  echo "==> ERRO: nenhuma ISO gerada. Veja build.log." >&2
  exit 1
fi
