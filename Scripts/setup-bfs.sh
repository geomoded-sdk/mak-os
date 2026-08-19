#!/bin/bash
# =============================================================================
#  setup-bfs.sh — cria o volume de dados BFS OBRIGATÓRIO do Pineapple OS
#
#  O Pineapple OS exige um volume BFS (exFAT + .bfsprivate) para iniciar
#  fora do modo live. Este script:
#
#    1. Formata o dispositivo como exFAT        (⚠️ APAGA TODOS OS DADOS)
#    2. Monta em /data (padrão)
#    3. Inicializa o BFS (pineapplefs init) — cria .bfsprivate, ._*,
#       .Spotlight-V100, .fseventsd, .Trashes, .DS_Store, etc.
#    4. Registra no /etc/fstab (por UUID)
#    5. Regenera o initramfs (o boot valida o BFS e entra em panic sem ele)
#
#  Uso:
#    sudo ./Scripts/setup-bfs.sh /dev/sdb2            # monta em /data
#    sudo ./Scripts/setup-bfs.sh /dev/sdb2 /home      # monta em /home
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
echo " ATENÇÃO: $DEV será APAGADO e formatado como exFAT (volume BFS)"
echo "=============================================================="
read -r -p "Tem certeza? Digite SIM para continuar: " resp
if [ "$resp" != "SIM" ]; then
  echo "Cancelado."
  exit 1
fi

echo "==> Formatando $DEV como exFAT"
command -v mkfs.exfat >/dev/null || { echo "Instale o pacote exfatprogs." >&2; exit 1; }
mkfs.exfat "$DEV"

echo "==> Montando em $MNT"
mkdir -p "$MNT"
mount "$DEV" "$MNT"

echo "==> Inicializando o volume BFS"
python3 "$ROOT/Scripts/pineapplefs.py" init "$MNT" --name "Pineapple OS"

echo "==> Registrando no /etc/fstab (por UUID)"
UUID="$(blkid -s UUID -o value "$DEV")"
if [ -z "$UUID" ]; then
  echo "Aviso: não consegui ler o UUID do volume." >&2
else
  if ! grep -q "UUID=$UUID" /etc/fstab; then
    echo "UUID=$UUID  $MNT  exfat  defaults,noatime,uid=1000,gid=1000  0  0" >> /etc/fstab
    echo "    adicionado ao /etc/fstab"
  fi
fi

echo "==> Regenerando initramfs (check de boot valida o BFS)"
if command -v update-initramfs >/dev/null; then
  update-initramfs -u
fi

echo "=============================================================="
echo " Volume BFS criado em $MNT (obrigatório no boot)."
echo ""
echo " Para informar o dispositivo na linha de boot, adicione em"
echo " /etc/default/grub (GRUB_CMDLINE_LINUX_DEFAULT):"
echo "   -pineapplefs=$DEV"
echo ""
echo " Sem esse volume o kernel entra em panic no boot (como o PowerBook ID)."
echo "=============================================================="