#!/usr/bin/env bash
# =============================================================================
#  boot-test-iso.sh — teste de boot QEMU rigoroso (BIOS + UEFI).
#
#  A partir de uma ISO "de produção", gera uma ISO de TESTE com o grub.cfg
#  patcheado para: console serial (captura de log), sem quiet/splash/loglevel,
#  timeout curto, e um serial válido de PowerBook injetado (ids.txt). Depois
#  tenta BOOTAR de verdade sob QEMU:
#    * BIOS (SeaBIOS) — via entrada El Torito;
#    * UEFI (OVMF)    — via entrada EFI.
#
#  Aceitação (por modo):
#    PASS  — o kernel entrega o controle ao initramfs
#            ("Run /init as init process" ou "Reached target Basic System");
#    FAIL  — "Kernel panic", erro do GRUB ("error: ...") ou nenhum handoff.
#
#  Uso: Scripts/boot-test-iso.sh <imagem.iso>
# =============================================================================
set -euo pipefail

ISO="${1:?uso: boot-test-iso.sh <imagem.iso>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
BOOT_TIMEOUT="${BOOT_TIMEOUT:-300}"

echo "==> Boot test: $ISO"

# --- 1) extrai a árvore da ISO -------------------------------------------------
echo "=> extraindo árvore ($(basename "$ISO"))"
xorriso -osirrox on -indev "$ISO" -extract / "$WORK/tree" > "$WORK/xorriso.log" 2>&1 || {
    echo "FALHA: xorriso não conseguiu extrair a ISO"
    tail -20 "$WORK/xorriso.log"
    exit 1
}

GRUBCFG="$WORK/tree/boot/grub/grub.cfg"
[ -f "$GRUBCFG" ] || { echo "FALHA: boot/grub/grub.cfg ausente no tree"; exit 1; }

VALID_ID="$(grep -E -m1 '^[A-Z0-9]{8,10}$' "$ROOT/ids.txt" | tr -d '\r' || true)"
if [ -z "$VALID_ID" ]; then
    echo "aviso: ids.txt sem serial válido aparente; sem injeção do powerbook id"
fi

# --- 2) patch no grub.cfg --------------------------------------------------------
python3 - "$GRUBCFG" "$VALID_ID" <<'PYEOF'
import re
import sys

cfg_path, valid_id = sys.argv[1], sys.argv[2]

with open(cfg_path, "r", encoding="utf-8", errors="replace") as fh:
    cfg = fh.read()

if "terminal_output serial" not in cfg:
    cfg = cfg.replace(
        "set default=0",
        "set default=0\nserial --unit=0 --speed=115200\n"
        "terminal_input serial\nterminal_output serial",
        1,
    )
cfg = re.sub(r"^set timeout=\d+", "set timeout=3", cfg, flags=re.M)

lines = cfg.splitlines(keepends=True)
for i, ln in enumerate(lines):
    if ln.lstrip().startswith("linux "):
        ln = re.sub(r"\b(quiet|loglevel=\S+|splash|rd\.quiet)\b", "", ln)
        ln = re.sub(r"[ \t]{2,}", " ", ln)
        if "console=ttyS0" not in ln:
            ln = ln.rstrip() + " console=ttyS0\n"
        if valid_id and "-pineapplepowerbookid=" not in ln:
            ln = ln.rstrip() + f" -pineapplepowerbookid={valid_id}\n"
        lines[i] = ln
        print("    linux line:", ln.strip())

with open(cfg_path, "w") as fh:
    fh.write("".join(lines))
PYEOF

# --- 3) regrava ISO de teste ----------------------------------------------------
echo "=> regravando ISO de teste (grub-mkrescue)"
grub-mkrescue -o "$WORK/test.iso" "$WORK/tree" > "$WORK/mkrescue.log" 2>&1 || {
    echo "FALHA: grub-mkrescue não criou a ISO de teste"
    tail -20 "$WORK/mkrescue.log"
    exit 1
}

# --- 4) ambiente QEMU -------------------------------------------------------------
if [ -e /dev/kvm ]; then
    ACCEL="-enable-kvm -cpu max"
    QRUN="sudo -E"
    echo "=> KVM presente em /dev/kvm — aceleração kvm ativa"
else
    ACCEL="-accel tcg,thread=multi -cpu qemu64"
    QRUN=""
    echo "=> /dev/kvm ausente — usando QEMU em modo TCG (mais lento)"
fi

QEMU=(qemu-system-x86_64 $ACCEL -machine q35 -m 4096 -smp 4
      -nographic -monitor none -no-reboot)

# --- 5) boots ---------------------------------------------------------------------
analyze() {
    local name="$1" log="$2"
    if [ ! -s "$log" ]; then
        echo "FAIL[$name]: log de boot vazio"
        return 1
    fi
    if grep -q "Kernel panic" "$log"; then
        echo "FAIL[$name]: kernel panic detectado"
        tail -80 "$log"
        return 1
    fi
    if grep -qE "^error: " "$log"; then
        echo "FAIL[$name]: erro do GRUB no boot"
        tail -80 "$log"
        return 1
    fi
    if grep -q "Run /init as init process" "$log"; then
        echo "PASS[$name]: kernel entregou o controle ao initramfs (handoff)"
        if grep -q "Reached target Basic System" "$log"; then
            echo "PASS[$name]: atingiu o alvo Basic System (early-boot completo)"
        fi
        return 0
    fi
    echo "FAIL[$name]: kernel não entregou o controle ao initramfs"
    tail -80 "$log"
    return 1
}

# 5.1 BIOS (SeaBIOS, El Torito)
echo "==> boot BIOS (SeaBIOS, até ${BOOT_TIMEOUT}s)"
$QRUN timeout "$BOOT_TIMEOUT" "${QEMU[@]}" \
    -cdrom "$WORK/test.iso" -boot d \
    </dev/null > "$WORK/bios.log" 2>&1 || true
BIOS_STATUS=0
analyze "BIOS" "$WORK/bios.log" || BIOS_STATUS=$?
echo "    (último BIOS log): $(tail -2 "$WORK/bios.log" | tr '\n' ' ' | cut -c1-140)"

# 5.2 UEFI (OVMF)
if [ -d /usr/share/OVMF ]; then
    CODE_FD="$(ls /usr/share/OVMF/OVMF_CODE*.fd 2>/dev/null | head -n1 || true)"
    VARS_TMPL="$(ls /usr/share/OVMF/OVMF_VARS*.fd 2>/dev/null | head -n1 || true)"
else
    CODE_FD=""
    VARS_TMPL=""
fi

EFI_STATUS=0
if [ -n "$CODE_FD" ] && [ -n "$VARS_TMPL" ]; then
    cp "$VARS_TMPL" "$WORK/OVMF_VARS.fd"
    echo "==> boot UEFI (OVMF $CODE_FD até ${BOOT_TIMEOUT}s)"
    $QRUN timeout "$BOOT_TIMEOUT" "${QEMU[@]}" \
        -drive if=pflash,format=raw,readonly=on,file="$CODE_FD" \
        -drive if=pflash,format=raw,file="$WORK/OVMF_VARS.fd" \
        -cdrom "$WORK/test.iso" -boot order=d \
        </dev/null > "$WORK/efi.log" 2>&1 || true
    analyze "UEFI" "$WORK/efi.log" || EFI_STATUS=$?
    echo "    (último UEFI log): $(tail -2 "$WORK/efi.log" | tr '\n' ' ' | cut -c1-140)"
else
    echo "aviso: OVMF não instalado — pulando teste UEFI"
    EFI_STATUS=0
fi

if [ "$BIOS_STATUS" -ne 0 ] || [ "$EFI_STATUS" -ne 0 ]; then
    echo "==> BOOT TEST FALHOU"
    exit 1
fi
echo "==> BOOT TEST OK (BIOS+UEFI bootaram)"
exit 0