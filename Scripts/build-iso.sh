#!/bin/bash
# =============================================================================
#  build-iso.sh — gera a ISO do Mak OS a partir do live-build (Debian/Ubuntu)
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

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LB_DIR="$ROOT/Installer/live-build"
WORKDIR="$ROOT/Installer/live-build/$OUTPUT"

echo "==> Mak OS ISO build"
echo "    distro=$DISTRO suite=$SUITE arch=$ARCH"

command -v lb >/dev/null 2>&1 || {
  echo "live-build não encontrado. Instale com: sudo apt install live-build" >&2
  exit 1
}

# ------------------------------------------------------------ preparar workdir
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

echo "==> Inicializando live-build (lb config)"
lb config \
  --distribution "$SUITE" \
  --architecture "$ARCH" \
  --architectures "$ARCH" \
  --system live \
  --binary-images iso-hybrid \
  --bootappend-live "boot=live components quiet splash locale=pt_BR.UTF-8" \
  --debian-installer live \
  --debian-installer-distribution "$SUITE" \
  --apt-recommends false \
  --archive-areas "main contrib non-free-firmware" \
  --mode "$DISTRO" \
  --mirror-bootstrap "$MIRROR" \
  --mirror-binary "$MIRROR"

# ------------------------------------------------------------ incluir pacotes
# Lista de pacotes base do Mak OS
cat > config/package-lists/makos.list.chroot <<'EOF'
# --- sistema base ---
linux-image-amd64
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
cat > config/includes.chroot/usr/share/makos/scripts/setup-flatpak.sh <<'EOF'
#!/bin/bash
flatpak remote-add --if-not-exists flathub \
  https://dl.flathub.org/repo/flathub.flatpakrepo
EOF
chmod +x config/includes.chroot/usr/share/makos/scripts/setup-flatpak.sh

# ------------------------------------------------------------ incluir Mak OS
echo "==> Copiando componentes do Mak OS para a imagem"
cp -r "$ROOT"/Desktop "$ROOT"/Dock "$ROOT"/Launcher "$ROOT"/Launchpad "$ROOT"/Mission \
      "$ROOT"/Finder "$ROOT"/Gestures "$ROOT"/AI "$ROOT"/Settings "$ROOT"/Store "$ROOT"/Apps \
      "$ROOT"/Themes "$ROOT"/Icons config/includes.chroot/usr/share/makos/

# ------------------------------------------------------------ Darling pré-instalado
# Se houver .debs pré-compilados (gerados por build-darling-deb.sh), o
# live-build os instala na imagem → Darling já vem instalado na ISO.
if ls "$ROOT"/Scripts/debs/*.deb >/dev/null 2>&1; then
  echo "==> Incluindo Darling pré-compilado na imagem"
  mkdir -p config/packages.chroot
  cp "$ROOT"/Scripts/debs/*.deb config/packages.chroot/
fi

# ------------------------------------------------------------ build
echo "==> Gerando a ISO (isso pode levar vários minutos)"
lb build 2>&1 | tee "$ROOT/Installer/live-build/build.log"

ISO=$(ls live-image-*.hybrid.iso 2>/dev/null || ls *.iso 2>/dev/null | head -n1)
if [ -n "$ISO" ]; then
  cp "$ISO" "$ROOT/makos-$SUITE-$ARCH.iso"
  echo "==> ISO criada: $ROOT/makos-$SUITE-$ARCH.iso"
else
  echo "==> ERRO: nenhuma ISO gerada. Veja build.log." >&2
  exit 1
fi
