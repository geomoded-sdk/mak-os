#!/bin/bash
# =============================================================================
#  setup-pnfs.sh — cria o volume de dados PNFS OBRIGATÓRIO do Pineapple OS
#
#  O Pineapple OS exige um volume PNFS nativo para iniciar
#  fora do modo live. Este script:
#
#    1. Formata o dispositivo com o superbloco PNFS (⚠️ APAGA TODOS OS DADOS)
#    2. Monta como PNFS em /data (padrão)
#    3. Verifica o superbloco exposto pelo driver PNFS em volume.info.
#    4. Registra no /etc/fstab (por UUID)
#    5. Regenera o initramfs (o boot valida o PNFS e entra em panic sem ele)
#
#  Uso:
#    sudo ./Scripts/setup-pnfs.sh /dev/sdb2            # monta em /data
#    sudo ./Scripts/setup-pnfs.sh /dev/sdb2 /home      # monta em /home
#
#  Depois adicione na linha de boot (GRUB_CMDLINE_LINUX_DEFAULT):
#    -pineapplefs=/dev/sdb2
#  ou deixe que o boot detecte pelo /etc/fstab.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "Execute como root: sudo $0 /dev/sdX" >&2
  exit 1
fi

DEV="${1:-}"
MNT="${2:-/data}"

if [ -z "$DEV" ]; then
  echo "Uso: sudo $0 <dispositivo> [ponto-de-montagem]" >&2
  echo "Ex.: sudo $0 /dev/sdb2 /data" >&2
  exit 1
fi

if [ ! -b "$DEV" ]; then
  echo "ERRO: $DEV não é um dispositivo de bloco." >&2
  exit 1
fi

echo "=============================================================="
echo " ATENÇÃO: $DEV será APAGADO e formatado como PNFS nativo"
echo "=============================================================="
read -r -p "Tem certeza? Digite SIM para continuar: " resp
if [ "$resp" != "SIM" ]; then
  echo "Cancelado."
  exit 1
fi

echo "==> Formatando $DEV como PNFS nativo"
command -v pineapplefs-mkfs >/dev/null || { echo "pineapplefs-mkfs não encontrado; compile/instale o Pineapple OS primeiro." >&2; exit 1; }
pineapplefs-mkfs "$DEV"

echo "==> Montando em $MNT"
mkdir -p "$MNT"
mount -t pnfs "$DEV" "$MNT"

echo "==> Verificando o volume PNFS nativo"
test -r "$MNT/volume.info" || { echo "ERRO: o driver PNFS não expôs volume.info" >&2; umount "$MNT"; exit 1; }

echo "==> Registrando no /etc/fstab (por UUID)"
UUID="$(blkid -s UUID -o value "$DEV")"
if [ -z "$UUID" ]; then
  echo "Aviso: não consegui ler o UUID do volume." >&2
else
  if ! grep -q "UUID=$UUID" /etc/fstab; then
    echo "UUID=$UUID  $MNT  pnfs  defaults,noatime  0  0" >> /etc/fstab
    echo "    adicionado ao /etc/fstab"
  fi
fi

echo "==> Regenerando initramfs (check de boot valida o PNFS)"
if command -v update-initramfs >/dev/null; then
  update-initramfs -u
fi

echo "=============================================================="
echo " Volume PNFS nativo criado em $MNT (obrigatório no boot)."
echo ""
echo " Para informar o dispositivo na linha de boot, adicione em"
echo " /etc/default/grub (GRUB_CMDLINE_LINUX_DEFAULT):"
echo "   -pineapplefs=$DEV"
echo ""
echo " Sem esse volume o kernel entra em panic no boot (como o PowerBook ID)."
echo "=============================================================="
