#!/bin/bash
# =============================================================================
#  pineapple-workspace — publica a área de trabalho ativa para o indicador da barra
#
#  O compositor (ou um hook de troca de área) deve chamar:
#    pineapple-workspace set 2
#  A barra lê o arquivo e acende o ponto correspondente.
#
#  Uso:
#    pineapple-workspace set <n>     publica área ativa
#    pineapple-workspace get         lê área ativa
# =============================================================================
set -euo pipefail

UID_="$(id -u)"
STATE="/run/user/$UID_/pineappleos-workspace"

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
    echo "uso: pineapple-workspace set <n> | get" >&2
    exit 1
    ;;
esac
