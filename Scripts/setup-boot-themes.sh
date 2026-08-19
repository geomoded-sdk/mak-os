#!/bin/bash
# =============================================================================
#  setup-boot-themes.sh — aplica o visual de boot do Pineapple OS
#
#  Instala:
#    1. Tema GRUB (invisível: boot direto, sem passar pelo menu)
#    2. Tema Plymouth (boot estilo Apple: abacaxi de contorno + barra)
#    3. Tema SDDM (login estilo macOS)
#    4. Verificação do PowerBook ID (kernel panic se faltar o argumento)
#    5. Logs de boot silenciosos (quiet loglevel=0) — igual ao macOS
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Instalando tema GRUB"
sudo mkdir -p /boot/grub/themes/pineappleos
sudo cp "$ROOT"/Installer/grub/theme/* /boot/grub/themes/pineappleos/
if ! grep -q "GRUB_THEME=/boot/grub/themes/pineappleos/theme.txt" /etc/default/grub; then
  echo 'GRUB_THEME=/boot/grub/themes/pineappleos/theme.txt' | sudo tee -a /etc/default/grub > /dev/null
fi

echo "==> Ocultando o menu do GRUB (boot direto, estilo macOS)"
# Sem menu visível: o boot passa pelo GRUB sem "perceber" que ele existe.
if grep -q '^GRUB_TIMEOUT=' /etc/default/grub; then
  sudo sed -i 's/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=0/' /etc/default/grub
else
  echo 'GRUB_TIMEOUT=0' | sudo tee -a /etc/default/grub > /dev/null
fi
if ! grep -q "GRUB_HIDDEN_TIMEOUT=0" /etc/default/grub; then
  cat >> /etc/default/grub <<'EOF'
GRUB_HIDDEN_TIMEOUT=0
GRUB_HIDDEN_TIMEOUT_QUIET=true
GRUB_FORCE_HIDDEN_MENU="true"
GRUB_DISABLE_OS_PROBER=true
EOF
fi

echo "==> Configurando logs silenciosos (estilo macOS)"
# quiet + loglevel=0 escondem os logs do kernel; o único visual é o splash.
if ! grep -q "quiet loglevel=0" /etc/default/grub; then
  sudo sed -i 's/^GRUB_CMDLINE_LINUX_DEFAULT="\(.*\)"/GRUB_CMDLINE_LINUX_DEFAULT="\1 quiet loglevel=0"/' \
    /etc/default/grub
fi

echo "==> Definindo PowerBook ID (obrigatório no boot)"
# ATENÇÃO: sem o argumento -pineapplepowerbookid=<ID> o sistema entra em
# kernel panic. Descomente a linha abaixo e troque SEU_ID por um ID válido
# da lista em ids.txt.
if ! grep -q "pineapplepowerbookid" /etc/default/grub; then
  cat >> /etc/default/grub <<'EOF'

# Pineapple OS — PowerBook ID obrigatório. Sem ele o kernel entra em panic.
# Use um ID da lista em /usr/share/pineappleos/ids.txt:
# GRUB_CMDLINE_LINUX_DEFAULT="$(echo $GRUB_CMDLINE_LINUX_DEFAULT) -pineapplepowerbookid=SEU_ID"
#
# Pineapple OS — volume BFS obrigatório (fora do modo live). Sem um volume
# BFS válido (exFAT + .bfsprivate) o kernel entra em panic. Crie com
# Scripts/setup-bfs.sh e indique o dispositivo:
# GRUB_CMDLINE_LINUX_DEFAULT="$(echo $GRUB_CMDLINE_LINUX_DEFAULT) -pineapplefs=/dev/sdX2"
EOF
fi
sudo update-grub

echo "==> Instalando tema Plymouth"
sudo mkdir -p /usr/share/plymouth/themes/pineappleos
sudo cp "$ROOT"/Installer/plymouth/theme/* /usr/share/plymouth/themes/pineappleos/
sudo update-alternatives --install \
  /usr/share/plymouth/themes/default.plymouth \
  default.plymouth /usr/share/plymouth/themes/pineappleos/pineappleos.plymouth 200
sudo update-alternatives --set default.plymouth \
  /usr/share/plymouth/themes/pineappleos/pineappleos.plymouth

echo "==> Instalando tema SDDM"
sudo mkdir -p /usr/share/sddm/themes/pineappleos
sudo cp "$ROOT"/Installer/sddm/theme/* /usr/share/sddm/themes/pineappleos/
if [ ! -d /etc/sddm.conf.d ]; then
  sudo mkdir -p /etc/sddm.conf.d
fi
if [ ! -f /etc/sddm.conf.d/pineappleos.conf ]; then
  printf '[Theme]\nCurrent=pineappleos\n' | sudo tee /etc/sddm.conf.d/pineappleos.conf > /dev/null
fi

echo "==> Instalando verificação do PowerBook ID (panic no boot)"
"$ROOT/Scripts/setup-powerbook-check.sh"

echo "==> Temas de boot aplicados. Reinicie para ver o novo visual."
