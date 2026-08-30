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
MIRROR="${MIRROR:-http://deb.debian.org/debian}"
MIRROR="${MIRROR%/}"
# PowerBook ID obrigatório (ver ids.txt). Se vazio, o live boot entra em
# kernel panic até que o argumento -pineapplepowerbookid=<ID> seja fornecido
# na linha de comando do kernel (ex.: editando o GRUB na tela de boot).
POWERBOOK_ID="${POWERBOOK_ID:-}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LB_DIR="$ROOT/Installer/live-build"
WORKDIR="$ROOT/Installer/live-build/$OUTPUT"

# ------------------------------------------------- boot.plist + args de boot
# boot.plist é o equivalente do boot-args/NVRAM do macOS: um plist que define
# os argumentos de kernel, o PowerBook ID e o volume BFS usados na linha
# linux do GRUB. A variável de ambiente POWERBOOK_ID tem prioridade sobre a
# chave PowerBookID do plist.
BOOT_PLIST="$LB_DIR/boot.plist"

# Lê uma chave do boot.plist (via python3/plistlib). Emite "" se indisponível.
plist_get() {
  local key="$1"
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$BOOT_PLIST" "$key" <<'PY' 2>/dev/null || true
import plistlib, sys
try:
    with open(sys.argv[1], 'rb') as f:
        d = plistlib.load(f)
    v = d.get(sys.argv[2])
    if v is True:
        print('true')
    elif v is False:
        print('false')
    else:
        print(v if v is not None else '')
except Exception:
    sys.exit(1)
PY
  fi
}

DEFAULT_BOOT_ARGS="quiet loglevel=0 splash rd.quiet locale=pt_BR.UTF-8"
PLIST_ARGS="$(plist_get Arguments)"
PLIST_FS="$(plist_get FileSystem)"
PLIST_VERBOSE="$(plist_get Verbose)"
PLIST_SAFE="$(plist_get SafeMode)"
[ -z "$PLIST_ARGS" ] && PLIST_ARGS="$DEFAULT_BOOT_ARGS"

# POWERBOOK_ID (ambiente) tem prioridade sobre o PowerBookID do plist.
BOOT_ID="$(plist_get PowerBookID)"
[ -n "$POWERBOOK_ID" ] && BOOT_ID="$POWERBOOK_ID"

# Argumentos de boot estilo macOS:
#   boot=live components      → live-boot obrigatório
#   -v / -x                   → boot verboso / modo de segurança (estilo macOS)
#   -pineapplepowerbookid=ID  → ID do PowerBook (obrigatório; sem ele: panic)
#   -pineapplefs=DEV          → volume BFS (fora do modo live)
BOOTARGS="boot=live components ${PLIST_ARGS}"
[ "$PLIST_VERBOSE" = "true" ] && BOOTARGS="$BOOTARGS -v"
[ "$PLIST_SAFE" = "true" ] && BOOTARGS="$BOOTARGS -x"
if [ -n "$BOOT_ID" ]; then
  BOOTARGS="$BOOTARGS -pineapplepowerbookid=$BOOT_ID"
fi
if [ -n "$PLIST_FS" ]; then
  BOOTARGS="$BOOTARGS -pineapplefs=$PLIST_FS"
fi

echo "==> Pineapple OS ISO build"
echo "    distro=$DISTRO suite=$SUITE arch=$ARCH"
if [ -z "$BOOT_ID" ]; then
  echo "    [ATENÇÃO] PowerBook ID vazio (env POWERBOOK_ID/boot.plist) — o live boot"
  echo "              exigirá -pineapplepowerbookid=<ID> na tela do GRUB (senão: panic)."
else
  echo "    powerbook_id=$BOOT_ID"
  if [ -f "$ROOT/ids.txt" ] && ! grep -qx "$BOOT_ID" "$ROOT/ids.txt"; then
    echo "    [ATENÇÃO] PowerBook ID '$BOOT_ID' NÃO está em ids.txt — boot dará panic."
  fi
fi
echo "    boot args: $BOOTARGS"

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
  --binary-images iso \
  --initsystem systemd \
  --bootappend-live "$BOOTARGS" \
  --debian-installer false \
  --debian-installer-distribution "$SUITE" \
  --apt-recommends false \
  --security false \
  --linux-flavours "amd64" \
  --bootloader grub2 \
  --firmware-chroot false \
  --firmware-binary false \
  --archive-areas "main contrib non-free-firmware" \
  --mode "$DISTRO" \
  --mirror-bootstrap "$MIRROR" \
  --mirror-binary "$MIRROR"

# live-build versions shipped by Debian may generate the obsolete
# security.debian.org stable/updates source. Rewrite it to the current
# debian-security suite before the chroot stage starts.
if [ "$DISTRO" = "debian" ]; then
  mkdir -p config/archives
  cat > config/archives/pineapple-security.list.chroot <<EOF
deb http://deb.debian.org/debian-security ${SUITE}-security main contrib non-free-firmware
EOF
  while IFS= read -r -d '' file; do
    sed -i \
      -e "s#http://security.debian.org#http://deb.debian.org/debian-security#g" \
      -e "s#${SUITE}/updates#${SUITE}-security#g" \
      "$file"
  done < <(grep -RIlZ "security.debian.org\|${SUITE}/updates" config || true)
fi

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
systemd-sysv

# --- X / Wayland ---
xserver-xorg-core
xwayland
labwc
wayland-protocols
wayland-utils
libwlroots-0.18
libxkbcommon0
libinput10
xdg-desktop-portal-wlr

# --- GTK4 e bibliotecas da interface ---
python3
python3-gi
python3-cairo
libgtk-4-1
libadwaita-1-0
gir1.2-gtk-4.0
gir1.2-gstreamer-1.0
gir1.2-gst-plugins-base-1.0
gir1.2-webkit-6.0
gir1.2-vte-3.91
libvte-2.91-gtk4-0
libwebkitgtk-6.0-4
gstreamer1.0-plugins-good
gstreamer1.0-plugins-bad
gstreamer1.0-plugins-ugly
gstreamer1.0-libav
librsvg2-common
hicolor-icon-theme
fonts-inter
fonts-sora
swaybg

# --- serviços ---
pipewire
pipewire-pulse
wireplumber
pipewire-audio
bluez
network-manager
upower
accountsservice
dbus
polkitd
sddm
greetd
gnupg
libgcrypt20
libsodium23
libsecret-1-0
libpam-systemd

# --- apps e utilitários ---
gvfs
gvfs-backends
xdg-desktop-portal
xdg-desktop-portal-gtk
flatpak
apparmor
calamares
util-linux
libarchive-tools
zstd
lz4
fuse3
udisks2
smartmontools
file-roller
gnome-disk-utility
rsync
git

# --- compatibilidade ---
wine
winetricks

# --- multimídia ---
ffmpeg
libvpx-dev
libdav1d-dev
libjpeg62-turbo
libpng16-16t64
libwebp7
libopenexr-3-1-30
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
      "$ROOT"/Canopy "$ROOT"/Gestures "$ROOT"/AI "$ROOT"/Settings "$ROOT"/Store "$ROOT"/Apps \
      "$ROOT"/Themes "$ROOT"/Icons config/includes.chroot/usr/share/pineappleos/

# Binários compilados da interface (produzidos por Scripts/build-iso-binaries.sh).
# Sem eles a sessão (units systemd) não sobe: as units chamam /usr/local/bin/*.
if [ -d "$ROOT/build/iso-stage/usr/local/bin" ]; then
    echo "==> Instalando binários compilados (Rust + Python) na imagem"
    mkdir -p config/includes.chroot/usr/local/bin config/includes.chroot/usr/bin
    cp -r "$ROOT/build/iso-stage/usr/local/bin/." config/includes.chroot/usr/local/bin/
    cp -r "$ROOT/build/iso-stage/usr/bin/." config/includes.chroot/usr/bin/
else
    echo "AVISO: build/iso-stage ausente — a ISO sairá SEM os binários da interface"
fi

# Entrada de sessão Wayland para o SDDM: senão o greeter não lista "Pineapple OS".
echo "==> Entrada de sessão Wayland do SDDM"
mkdir -p config/includes.chroot/usr/share/wayland-sessions \
         config/includes.chroot/usr/share/pineappleos/session
cat > config/includes.chroot/usr/share/pineappleos/session/pineapple-wayland-session.sh <<'EOF'
#!/bin/bash
# Sessão Wayland do Pineapple OS: sobe o target de sessão do usuário e
# permanece vivo (o SDDM encerra a sessão quando o Exec termina).
export XDG_SESSION_TYPE=wayland
export XDG_SESSION_DESKTOP=PineappleOS
export XDG_CURRENT_DESKTOP=PineappleOS
export GDK_BACKEND=wayland
export QT_QPA_PLATFORM=wayland
systemctl --user start graphical-session.target
systemctl --user start pineappleos-session.target
exec sleep infinity
EOF
chmod +x config/includes.chroot/usr/share/pineappleos/session/pineapple-wayland-session.sh
cat > config/includes.chroot/usr/share/wayland-sessions/pineappleos.desktop <<'EOF'
[Desktop Entry]
Name=Pineapple OS
Comment=Sessão Wayland do Pineapple OS
Exec=/usr/share/pineappleos/session/pineapple-wayland-session.sh
Type=Application
DesktopNames=PineappleOS;
EOF

# Configuracao e branding do instalador grafico Pineapple.
echo "==> Incluindo configuracao do Calamares"
mkdir -p config/includes.chroot/etc/calamares
cp "$ROOT/Installer/calamares/settings.conf" config/includes.chroot/etc/calamares/
cp -r "$ROOT/Installer/calamares/branding" config/includes.chroot/etc/calamares/
cp -r "$ROOT/Installer/calamares/modules" config/includes.chroot/etc/calamares/

# Unidades da sessão de usuário, incluindo o assistente de primeiro boot.
echo "==> Incluindo unidades systemd da sessão"
mkdir -p config/includes.chroot/etc/systemd/user
cp "$ROOT"/Installer/systemd/*.service "$ROOT"/Installer/systemd/*.target \
  config/includes.chroot/etc/systemd/user/
mkdir -p config/includes.chroot/etc/systemd/user/pineappleos-session.target.wants
WANTS=config/includes.chroot/etc/systemd/user/pineappleos-session.target.wants
# LIVE: a sessão desktop precisa subir SOZINHA no boot — habilita todos os
# units da sessão (antes só o pineapple-setup tinha symlink; o desktop inteiro
# dependeria de um "systemctl --user enable" pós-instalação).
for u in pineapple-setup.service pineapple-compositor.service \
         pineapple-wallpaper.service pineapple-shell.service \
         pineapple-dock.service pineapple-launcher.service \
         pineapple-launchpad.service pineapple-mission.service \
         pineapple-gestures.service pineapple-notifyd.service \
         pineapple-control-center.service pineapple-ai.service; do
    ln -sf "../$u" "$WANTS/$u"
done

# ------------------------------------------------------------ identidade do sistema
# /etc/os-release — o Pineapple OS deixa de aparecer como "Debian/GNU Linux"
# e passa a se identificar como Pineapple OS.
echo "==> Definindo identidade (os-release)"
mkdir -p config/includes.chroot/etc
cp "$ROOT/Installer/os-release" config/includes.chroot/etc/os-release

# O boot.plist também vai para o sistema, para servir de referência da
# configuração de boot usada na build (e de modelo para o sistema instalado).
mkdir -p config/includes.chroot/etc/pineappleos
cp "$BOOT_PLIST" config/includes.chroot/etc/pineappleos/boot.plist

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
curl -fsSL \
  -H 'Accept: application/octet-stream' \
  -o "$LPNU_DIR/ld-mac" \
  "https://api.github.com/repos/geomoded-sdk/lpnu/releases/assets/402871192"
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

# ------------------------------------------------------------ grub.cfg da ISO
# O template grub2 do live-build 3.0~a57 é frágil (background via ($root) e o
# core gerado pelo binary.sh usa grub-mkimage sem '-p', obrigatório desde o
# grub 2.12 — o que quebra o El Torito). Aqui regravamos um grub.cfg robusto
# que localiza o kernel por busca na mídia (CD/USB, BIOS/UEFI).
echo "==> Configurando grub.cfg da ISO (busca por /live/vmlinuz)"
cat > config/hooks/0020-pineapple-grub.cfg.hook.binary <<EOF
#!/bin/sh
set -eu
KERN="\$(basename binary/live/vmlinuz-*amd64)"
INITRD="\$(basename binary/live/initrd.img-*amd64)"
cat > binary/boot/grub/grub.cfg <<GRUB
set default=0
set timeout=5
insmod all_video
insmod part_msdos
insmod part_gpt
insmod fat
insmod exfat
insmod iso9660
insmod udf
insmod ext2
insmod search
# "menuentry" é obrigatório: sem ele o GRUB não auto-boota e cai no prompt
menuentry "pineappleos" {
    # busca pelo nome exato (Rock Ridge/FAT guarda vmlinuz-*amd64, não "vmlinuz")
    search --no-floppy --set=root --file /live/\$KERN
    # se a busca falhar (ex.: DVD onde o search não indexa a (cd0)), usa (cd0)
    if [ ! -e /live/\$KERN ]; then set root=(cd0); fi
    linux /live/\$KERN ${BOOTARGS}
    initrd /live/\$INITRD
}
GRUB
EOF
chmod +x config/hooks/0020-pineapple-grub.cfg.hook.binary

# ------------------------------------------------------------ build
echo "==> Gerando a ISO (isso pode levar vários minutos)"
lb build 2>&1 | tee "$ROOT/Installer/live-build/build.log"

# ------------------------------------------------------------ ISO híbrida (Rufus/USB)
# O genisoimage embutido no live-build 3.0~a57 com bootloader grub2 gera um
# 'binary.iso' sem híbrido MBR (e com El Torito danificado pelo grub-mkimage
# sem '-p'). Para o Rufus aceitar, extraímos a árvore dessa ISO bruta e a
# reconstruímos com grub-mkrescue: El Torito grub2 (BIOS) + imagem EFI (UEFI)
# + MBR híbrido — bootável em USB e DVD.
echo "==> Reconstruindo ISO híbrida (BIOS+UEFI) com grub-mkrescue"
if [ ! -f binary.iso ]; then
  echo "==> ERRO: binary.iso não encontrado. Veja build.log." >&2
  exit 1
fi
command -v xorriso >/dev/null 2>&1 || {
  echo "xorriso não encontrado. Instale com: sudo apt install xorriso grub-pc-bin grub-efi-amd64-bin mtools" >&2
  exit 1
}
command -v grub-mkrescue >/dev/null 2>&1 || {
  echo "grub-mkrescue não encontrado. Instale com: sudo apt install grub-pc-bin grub-efi-amd64-bin" >&2
  exit 1
}
rm -rf binary-root
xorriso -osirrox on -indev binary.iso -extract / binary-root
rm -f binary.iso
ISO="$ROOT/pineappleos-$SUITE-$ARCH.iso"
grub-mkrescue -o "$ISO" binary-root
if [ -f "$ISO" ]; then
  echo "==> ISO híbrida criada: $ISO"
else
  echo "==> ERRO: grub-mkrescue falhou. Veja build.log." >&2
  exit 1
fi
