#!/usr/bin/env bash
# CI: instala pacotes via apt de forma robusta contra hangs do runner.
# O apt-get do GitHub Actions fica infinito se:
#   - unattended-upgrades/apt.systemd.daily segura o lock do dpkg;
#   - os mirrors Azure param de responder (sem timeout definido).
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

sudo pkill -9 -f "apt-get|apt.systemd.daily|unattended-upgrades" 2>/dev/null || true
sudo rm -f \
  /var/lib/dpkg/lock \
  /var/lib/dpkg/lock-frontend \
  /var/lib/apt/lists/lock \
  /var/cache/apt/archives/lock

timeout 60 sudo dpkg --configure -a || true

opts=(
  -o Acquire::Retries=5
  -o Acquire::http::Timeout=120
  -o Acquire::https::Timeout=120
)

timeout 600 sudo -E apt-get update "${opts[@]}"

timeout 600 sudo -E apt-get install -y --no-install-recommends \
  -o Dpkg::Options::="--force-confold" \
  -o Dpkg::Options::="--force-confdef" \
  "${opts[@]}" \
  "$@"