#!/bin/bash
# =============================================================================
#  setup-powerbook-check.sh — instala a verificação do PowerBook ID
#
#  O que faz:
#    1. Copia a lista de IDs (ids.txt) para /usr/share/pineappleos/.
#    2. Instala o hook e o verificador de initramfs.
#    3. Regenera o initramfs do kernel instalado.
#
#  A partir daqui, o sistema só inicia se a linha de comando do kernel
#  contiver "-pineapplepowerbookid=<ID>" com um ID válido de ids.txt.
#  Caso contrário, o kernel entra em PANIC (estilo macOS) durante o boot.
#
#  Para definir o seu ID no GRUB (instalação), edite /etc/default/grub e
#  adicione à linha GRUB_CMDLINE_LINUX_DEFAULT:
#      -pineapplepowerbookid=SEU_ID
#  e rode: sudo update-grub
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Copiando lista de PowerBook IDs"
sudo mkdir -p /usr/share/pineappleos
sudo cp "$ROOT/ids.txt" /usr/share/pineappleos/ids.txt

echo "==> Instalando hook de initramfs"
sudo mkdir -p /usr/share/initramfs-tools/hooks
sudo cp "$ROOT/Installer/initramfs/hooks/pineapple-powerbook-check" \
  /usr/share/initramfs-tools/hooks/
sudo chmod +x /usr/share/initramfs-tools/hooks/pineapple-powerbook-check

echo "==> Instalando verificador de boot (init-bottom)"
sudo mkdir -p /usr/share/initramfs-tools/scripts/init-bottom
sudo cp "$ROOT/Installer/initramfs/scripts/init-bottom/pineapple-powerbook-check" \
  /usr/share/initramfs-tools/scripts/init-bottom/
sudo chmod +x /usr/share/initramfs-tools/scripts/init-bottom/pineapple-powerbook-check

echo "==> Regenerando initramfs"
if [ -x /usr/sbin/update-initramfs ]; then
  sudo update-initramfs -u
else
  echo "   [aviso] update-initramfs não encontrado. Execute-o manualmente."
fi

echo ""
echo "==> IMPORTANTE: defina o seu PowerBook ID no GRUB"
echo "    Edite /etc/default/grub e inclua em GRUB_CMDLINE_LINUX_DEFAULT:"
echo "      -pineapplepowerbookid=SEU_ID"
echo "    Depois rode: sudo update-grub"
echo "    Sem esse argumento o sistema entra em kernel panic no boot."