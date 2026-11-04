#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/Bootloader/oemx-uefi"
OUT="${1:-$ROOT/Bootloader/build}"
mkdir -p "$OUT"

command -v x86_64-linux-gnu-gcc >/dev/null 2>&1 || {
  echo "x86_64-linux-gnu-gcc não encontrado (instale gnu-efi e gcc)" >&2
  exit 1
}

EFI_INC="/usr/include/efi"
EFI_LIB="/usr/lib/x86_64-linux-gnu"
EFI_CRT="$(find /usr -type f -name crt0-efi-x86_64.o -print -quit 2>/dev/null || true)"
EFI_LDS="$(find /usr -type f -name elf_x86_64_efi.lds -print -quit 2>/dev/null || true)"
EFI_GNUEFI="$(find /usr -type f -name libgnuefi.a -print -quit 2>/dev/null || true)"
EFI_LIBEFI="$(find /usr -type f -name libefi.a -print -quit 2>/dev/null || true)"
[ -f "$EFI_CRT" ] && [ -f "$EFI_LDS" ] && \
  [ -f "$EFI_GNUEFI" ] && [ -f "$EFI_LIBEFI" ] || {
  echo "gnu-efi não está instalado" >&2
  exit 1
}

x86_64-linux-gnu-gcc -I"$EFI_INC" -I"$EFI_INC/x86_64" \
  -ffreestanding -fpic -fshort-wchar -fno-stack-protector \
  -fno-strict-aliasing -mno-red-zone -maccumulate-outgoing-args \
  -c "$SRC/main.c" -o "$OUT/main.o"
x86_64-linux-gnu-ld -nostdlib -znocombreloc -T "$EFI_LDS" \
  -shared -Bsymbolic "$EFI_CRT" "$OUT/main.o" \
  "$EFI_GNUEFI" "$EFI_LIBEFI" -o "$OUT/oemx-boot.so"
x86_64-linux-gnu-objcopy -j .text -j .sdata -j .data -j .dynamic -j .dynsym \
  -j .rel -j .rela -j .reloc --target=efi-app-x86_64 \
  "$OUT/oemx-boot.so" "$OUT/BOOTX64.EFI"
echo "OEM-X UEFI loader: $OUT/BOOTX64.EFI"
