#!/bin/sh
# =============================================================================
#  gen-allowed-hw.sh — gera allowed_hw.h a partir de Kernel/hwlist.txt
#
#  Uso (chamado por build-kernel.sh):
#    gen-allowed-hw.sh Kernel/hwlist.txt Kernel/pineapple/hwcheck/allowed_hw.h
#
#  A allowlist é POR BUILD: o .h gerado só vale para o kernel compilado
#  depois desta chamada.
# =============================================================================
set -eu

LIST="${1:?uso: gen-allowed-hw.sh HWLIST OUT_H}"
OUT="${2:?uso: gen-allowed-hw.sh HWLIST OUT_H}"

{
  echo "/* Gerado por gen-allowed-hw.sh — NÃO editar; fonte: Kernel/hwlist.txt */"
  echo "#ifndef PINEAPPLE_ALLOWED_HW_H"
  echo "#define PINEAPPLE_ALLOWED_HW_H"
  echo ""
  echo "struct pine_allowed_hw {"
  echo "    unsigned short vendor;"
  echo "    unsigned short device;"
  echo "    unsigned char  class_code; /* 0 = qualquer */"
  echo "};"
  echo ""
  echo "static const struct pine_allowed_hw pine_allowed_hw[] = {"

  count=0
  # shellcheck disable=SC2013
  for line in $(grep -v '^[[:space:]]*#' "$LIST" | grep -v '^[[:space:]]*$' || true); do
    v="${line%%:*}"
    rest="${line#*:}"
    d="${rest%%:*}"
    c="${rest#*:}"
    if [ "$c" = "$rest" ]; then
      c=0
    fi
    # valida hex
    if ! printf '%s' "$v" | grep -Eq '^[0-9a-fA-F]{1,4}$'; then
      echo "  /* IGNORADO (vendor inválido): $line */" >&2
      continue
    fi
    if ! printf '%s' "$d" | grep -Eq '^[0-9a-fA-F]{1,4}$'; then
      echo "  /* IGNORADO (device inválido): $line */" >&2
      continue
    fi
    echo "    { 0x$v, 0x$d, 0x$c },"
    count=$((count + 1))
  done

  echo "};"
  echo ""
  echo "static const unsigned int pine_allowed_hw_count ="
  echo "    sizeof(pine_allowed_hw) / sizeof(pine_allowed_hw[0]);"
  echo ""
  echo "#endif"
} > "$OUT"

echo "gen-allowed-hw: $(grep -c '0x' "$OUT" || true) entradas → $OUT"
