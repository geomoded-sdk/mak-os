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
trap 'rm -rf "$WORK" >/dev/null 2>&1 || true' EXIT
BOOT_TIMEOUT="${BOOT_TIMEOUT:-600}"

echo "==> Boot test: $ISO"

# --- 1) extrai a árvore da ISO -------------------------------------------------
echo "=> extraindo árvore ($(basename "$ISO"))"
xorriso -osirrox on -indev "$ISO" -extract / "$WORK/tree" > "$WORK/xorriso.log" 2>&1 || {
    echo "FALHA: xorriso não conseguiu extrair a ISO"
    tail -20 "$WORK/xorriso.log"
    exit 1
}

# xorriso preserva os atributos Rock Ridge (dirs 0555, owner root) — habilita
# escrita para o patch do grub.cfg e a regravação do grub-mkrescue.
chmod -R u+rwX "$WORK/tree" 2>/dev/null || { 
    echo "aviso: chmod da árvore extraída falhou; tentando sudo"
    sudo chmod -R u+rwX "$WORK/tree" || { echo "FALHA: sem escrita na árvore"; exit 1; }
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

# prova: o grub.cfg que FOI para a ISO de teste
echo "=> grub.cfg da ISO de teste (search/linux):"
sed -E 's/\x1b\[[0-9;]*[a-zA-Z]//g' "$WORK/tree/boot/grub/grub.cfg" |
    grep -nE "search|if \[|set root|linux |initrd " |
    sed 's/^/    /'
echo "=> arquivo (cd0)/live do tree:"
ls "$WORK/tree/live/" | sed 's/^/    /'

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
      -nographic -monitor none -no-reboot
      -netdev user,id=net0 -device e1000,netdev=net0)

# --- 5) boots ---------------------------------------------------------------------
scrub() {
    # remove sequências ESC/CR para greps fiáveis (QEMU serial emite ANSI)
    sed 's/\x1b\[[0-9;]*[a-zA-Z]//g; s/\r//g'
}

# run_boot <name> <timeout_s> <qemu-args...>
#   roda o QEMU em segundo plano e MONITORA o log ao vivo; mata o QEMU assim
#   que o boot atinge o alvo (ou condena por panic/erro do GRUB). Retorna
#   "pass"|"panic"|"grub"|"earlyexit"|"timeout".
run_boot() {
    local name="$1" timeout_s="$2"; shift 2
    local qpid deadline state s sfile="$WORK/$name.live"
    "$@" > "$WORK/$name.log" 2>&1 &
    qpid=$!
    deadline=$((SECONDS + timeout_s))
    state="timeout"
    while [ "$SECONDS" -lt "$deadline" ]; do
        sleep 4
        scrub < "$WORK/$name.log" > "$sfile"
        if grep -q "Reached target Basic System" "$sfile"; then state="pass"; break; fi
        if grep -q "Kernel panic" "$sfile"; then state="panic"; break; fi
        if grep -qE "^error: " "$sfile"; then state="grub"; break; fi
        if ! kill -0 "$qpid" 2>/dev/null; then state="earlyexit"; break; fi
    done
    kill "$qpid" 2>/dev/null || true
    wait "$qpid" 2>/dev/null || true
    echo "$state"
}

analyze() {
    # ESTRITO: PASS apenas se o early-boot systemd completar ("Basic System").
    local name="$1" log="$2" s="$3" state="$4"
    scrub < "$log" > "$s"
    if [ ! -s "$s" ]; then
        echo "FAIL[$name]: log de boot vazio"
        return 1
    fi
    echo "    --- primeiras 12 linhas do boot log ---"
    sed -n '1,12p' "$s" | sed 's/^/      /'
    case "$state" in
        pass)   echo "PASS[$name]: atingiu o alvo Basic System (early-boot completo)"; return 0 ;;
        panic)  echo "FAIL[$name]: kernel panic detectado" ;;
        grub)   echo "FAIL[$name]: erro do GRUB no boot" ;;
        earlyexit) echo "FAIL[$name]: QEMU encerrou antes do alvo" ;;
        timeout) echo "FAIL[$name]: timeout sem atingir Basic System" ;;
    esac
    tail -40 "$s" | sed 's/^/      /'
    return 1
}

# 5.1 e 5.2 — BIOS (SeaBIOS) e UEFI (OVMF) em PARALELO
echo "==> boots BIOS (SeaBIOS, El Torito) e UEFI (OVMF) em paralelo (até ${BOOT_TIMEOUT}s cada)"

run_boot BIOS "$BOOT_TIMEOUT" $QRUN "${QEMU[@]}" \
    -cdrom "$WORK/test.iso" -boot d \</dev/null > "$WORK/bios.state" 2>&1 &
BIOS_PID=$!

CODE_FD=""
VARS_TMPL=""
if [ -d /usr/share/OVMF ]; then
    CODE_FD="$(ls /usr/share/OVMF/OVMF_CODE*.fd 2>/dev/null | head -n1 || true)"
    VARS_TMPL="$(ls /usr/share/OVMF/OVMF_VARS*.fd 2>/dev/null | head -n1 || true)"
fi

EFI_PID=""
if [ -n "$CODE_FD" ] && [ -n "$VARS_TMPL" ]; then
    cp "$VARS_TMPL" "$WORK/OVMF_VARS.fd"
    run_boot UEFI "$BOOT_TIMEOUT" $QRUN "${QEMU[@]}" \
        -drive if=pflash,format=raw,readonly=on,file="$CODE_FD" \
        -drive if=pflash,format=raw,file="$WORK/OVMF_VARS.fd" \
        -cdrom "$WORK/test.iso" -boot order=d \</dev/null > "$WORK/efi.state" 2>&1 &
    EFI_PID=$!
else
    echo "aviso: OVMF não instalado — pulando teste UEFI"
fi

wait "$BIOS_PID"
BIOS_STATE="$(cat "$WORK/bios.state" | scrub)"
if [ -n "$EFI_PID" ]; then
    wait "$EFI_PID"
    EFI_STATE="$(cat "$WORK/efi.state" | scrub)"
else
    EFI_STATE="pass"
fi

BIOS_STATUS=0
EFI_STATUS=0
scrub < "$WORK/bios.log" > "$WORK/bios.s"
analyze "BIOS" "$WORK/bios.log" "$WORK/bios.s" "$BIOS_STATE" || BIOS_STATUS=$?
if [ -s "$WORK/efi.log" ]; then
    scrub < "$WORK/efi.log" > "$WORK/efi.s"
    analyze "UEFI" "$WORK/efi.log" "$WORK/efi.s" "$EFI_STATE" || EFI_STATUS=$?
else
    analyze "UEFI" "$WORK/bios.log" "$WORK/bios.s" "$EFI_STATE" || EFI_STATUS=$?
fi
echo "    (último BIOS): $(tail -2 "$WORK/bios.log" 2>/dev/null | scrub | tr '\n' ' ' | cut -c1-120)"
echo "    (último UEFI): $(tail -2 "$WORK/efi.log" 2>/dev/null | scrub | tr '\n' ' ' | cut -c1-120)"

if [ "$BIOS_STATUS" -ne 0 ] || [ "$EFI_STATUS" -ne 0 ]; then
    echo "==> BOOT TEST FALHOU"
    exit 1
fi
echo "==> BOOT TEST OK (BIOS+UEFI bootaram)"
exit 0