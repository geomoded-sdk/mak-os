#!/bin/bash
# =============================================================================
#  mak-update — atualização OTA do Mak OS (pacotes oficiais)
# =============================================================================
set -euo pipefail

echo "==> Mak OS Update"
echo "    versão atual: $(cat /etc/makos-version 2>/dev/null || echo dev)"

echo "==> Verificando atualizações"
if ! sudo apt update 2>/dev/null; then
  echo "Aviso: apt update falhou. Verifique o repositório (setup-repo.sh)." >&2
fi

UPGRADES=$(apt list --upgradable 2>/dev/null | grep -c 'mak-os' || true)
if [ "$UPGRADES" -eq 0 ]; then
  echo "==> Nenhuma atualização do Mak OS disponível. Tudo em dia!"
  exit 0
fi

echo "==> $UPGRADES pacote(s) com atualização disponível:"
apt list --upgradable 2>/dev/null | grep 'mak-os' || true

read -r -p "Instalar agora? [s/N] " resp
if [[ "$resp" =~ ^[sS]$ ]]; then
  sudo apt install -y --only-upgrade mak-os-desktop mak-os-apps mak-os-themes mak-os-boot
  echo "==> Atualização concluída!"
else
  echo "Atualização cancelada."
fi
