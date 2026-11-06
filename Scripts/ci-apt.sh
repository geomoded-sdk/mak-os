#!/usr/bin/env bash
# CI: instala pacotes via apt de forma robusta contra hangs do runner.
# O apt-get do GitHub Actions fica infinito se:
#   - unattended-upgrades/apt.systemd.daily segura o lock do dpkg;
#   - os mirrors Azure param de responder (sem timeout definido).
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
# A instalação da toolchain GTK/live-build pode ultrapassar 10 minutos em
# mirrors congestionados. O limite antigo de 600 s encerrava uma instalação
# saudável com exit 124 antes mesmo da compilação da ISO começar.
APT_TIMEOUT="${CI_APT_TIMEOUT:-1200}"

sudo pkill -9 -f "apt-get|apt.systemd.daily|unattended-upgrades" 2>/dev/null || true
sudo rm -f \
  /var/lib/dpkg/lock \
  /var/lib/dpkg/lock-frontend \
  /var/lib/apt/lists/lock \
  /var/cache/apt/archives/lock

# `timeout` sem --foreground pode terminar só o wrapper sudo e deixar apt/dpkg
# vivo no runner.  Isso fazia a etapa seguinte parecer travada indefinidamente.
run_limited() {
  local seconds="$1"
  shift
  timeout --foreground --signal=TERM --kill-after=45 "$seconds" "$@"
}

run_limited 60 sudo dpkg --configure -a || true

opts=(
  -o Acquire::Retries=5
  -o Acquire::http::Timeout=120
  -o Acquire::https::Timeout=120
  -o DPkg::Lock::Timeout=60
)

run_limited "$APT_TIMEOUT" sudo -E apt-get update "${opts[@]}"

run_limited "$APT_TIMEOUT" sudo -E apt-get install -y --no-install-recommends \
  -o Dpkg::Options::="--force-confold" \
  -o Dpkg::Options::="--force-confdef" \
  "${opts[@]}" \
  "$@"
