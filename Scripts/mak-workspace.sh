#!/bin/bash
# =============================================================================
#  mak-workspace — publica a área de trabalho ativa para o indicador da barra
#
#  O compositor (ou um hook de troca de área) deve chamar:
#    mak-workspace set 2
#  A barra lê o arquivo e acende o ponto correspondente.
#
#  Uso:
#    mak-workspace set <n>     publica área ativa
#    mak-workspace get         lê área ativa
# =============================================================================
set -euo pipefail

UID_="$(id -u)"
STATE="/run/user/$UID_/makos-workspace"

case "${1:-get}" in
  set)
    n="${2:-1}"
    mkdir -p "$(dirname "$STATE")"
    echo "$n" > "$STATE"
    echo "área ativa: $n"
    ;;
  get)
    [ -f "$STATE" ] && cat "$STATE" || echo "1"
    ;;
  *)
    echo "uso: mak-workspace set <n> | get" >&2
    exit 1
    ;;
esac
