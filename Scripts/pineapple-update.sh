#!/bin/bash
# =============================================================================
#  pineapple-update — atualização OTA do Pineapple OS (pacotes oficiais)
# =============================================================================
set -euo pipefail

echo "==> Pineapple OS Update"
echo "    versão atual: $(cat /etc/pineappleos-version 2>/dev/null || echo dev)"

echo "==> Verificando atualizações"
if ! sudo apt update 2>/dev/null; then
  echo "Aviso: apt update falhou. Verifique o repositório (setup-repo.sh)." >&2
fi

UPGRADES=$(apt list --upgradable 2>/dev/null | grep -c 'pineapple-os' || true)
if [ "$UPGRADES" -eq 0 ]; then
  echo "==> Nenhuma atualização do Pineapple OS disponível. Tudo em dia!"
  exit 0
fi

echo "==> $UPGRADES pacote(s) com atualização disponível:"
apt list --upgradable 2>/dev/null | grep 'pineapple-os' || true

read -r -p "Instalar agora? [s/N] " resp
if [[ "$resp" =~ ^[sS]$ ]]; then
  sudo apt install -y --only-upgrade pineapple-os-desktop pineapple-os-apps pineapple-os-themes pineapple-os-boot
  echo "==> Atualização concluída!"
else
  echo "Atualização cancelada."
fi
