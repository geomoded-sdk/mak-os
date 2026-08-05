#!/bin/bash
# =============================================================================
#  setup-boot-themes.sh — instala o tema GRUB e Plymouth do Mak OS
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Instalando tema GRUB"
sudo mkdir -p /boot/grub/themes/makos
sudo cp "$ROOT"/Installer/grub/theme/* /boot/grub/themes/makos/
if ! grep -q "GRUB_THEME=/boot/grub/themes/makos/theme.txt" /etc/default/grub; then
  echo 'GRUB_THEME=/boot/grub/themes/makos/theme.txt' | sudo tee -a /etc/default/grub > /dev/null
fi
sudo update-grub

echo "==> Instalando tema Plymouth"
sudo mkdir -p /usr/share/plymouth/themes/makos
sudo cp "$ROOT"/Installer/plymouth/theme/* /usr/share/plymouth/themes/makos/
sudo update-alternatives --install \
  /usr/share/plymouth/themes/default.plymouth \
  default.plymouth /usr/share/plymouth/themes/makos/makos.plymouth 200
sudo update-alternatives --set default.plymouth \
  /usr/share/plymouth/themes/makos/makos.plymouth

echo "==> Instalando tema SDDM"
sudo mkdir -p /usr/share/sddm/themes/makos
sudo cp "$ROOT"/Installer/sddm/theme/* /usr/share/sddm/themes/makos/
if [ ! -d /etc/sddm.conf.d ]; then
  sudo mkdir -p /etc/sddm.conf.d
fi
if [ ! -f /etc/sddm.conf.d/makos.conf ]; then
  printf '[Theme]\nCurrent=makos\n' | sudo tee /etc/sddm.conf.d/makos.conf > /dev/null
fi

echo "==> Temas de boot aplicados. Reinicie para ver o novo visual."
