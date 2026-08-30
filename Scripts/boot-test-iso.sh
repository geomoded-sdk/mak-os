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
#
#  Modo gráfico (GRAPHICAL=1): além do boot até basic.target, extrai o
#  rootfs do squashfs, injeta autologin no tty1 + uma sessão Pineapple real
#  (systemd --user + pineappleos-session.target + units), e exige a evidência
#  "[PINEAPPLE-UI] UP" por /dev/console (= serial). Diagnostica por unidade o
#  estado do desktop (binários ausentes, units não-habilitados, crash etc).
# =============================================================================
set -euo pipefail

ISO="${1:?uso: boot-test-iso.sh <imagem.iso>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK" >/dev/null 2>&1 || true' EXIT
BOOT_TIMEOUT="${BOOT_TIMEOUT:-600}"
GRAPHICAL="${GRAPHICAL:-0}"

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

# --- 2.5) modo gráfico: sessão real Pineapple dentro do squashfs ----------------
# Troca o rootfs por uma cópia patcheada: autologin do usuário live no tty1 +
# loader da sessão que sobe systemd --user + pineappleos-session.target e deixa
# a prova de que o compositor (labwc) e os applets ficaram de pé via /dev/console.
# O diagnóstico (preflight AUSENTE por binário/unit) vira a evidência de quais
# peças o build da ISO REAL precisa instalar para o desktop subir sozinho.
prepare_graphical() {
    SQ=""
    for f in "$WORK/tree"/live/*.squashfs; do
        [ -e "$f" ] && SQ="$f"
    done
    [ -n "$SQ" ] || { echo "FALHA[grafico]: live/*.squashfs ausente"; exit 1; }
    command -v unsquashfs >/dev/null 2>&1 || { echo "FALHA[grafico]: instale squashfs-tools"; exit 1; }

    R="$WORK/rootfs"
    sudo rm -rf "$R"
    echo "=> [grafico] extraindo rootfs ($(basename "$SQ"))"
    ( cd "$WORK" && sudo unsquashfs -d rootfs "$SQ" > /dev/null 2>&1 ) || {
        echo "FALHA[grafico]: unsquashfs"; exit 1; }

    echo "=> [grafico] preflight do stack gráfico no rootfs:"
    for p in \
        usr/bin/labwc \
        usr/bin/swaybg \
        usr/bin/pineapple-wallpaper \
        usr/bin/pineapple-notifyd.py \
        usr/bin/pineapple-control-center.py \
        usr/bin/pineapple-ai \
        usr/local/bin/pineapple-shell \
        usr/local/bin/pineapple-dock \
        usr/local/bin/pineapple-launcher \
        usr/local/bin/pineapple-launchpad \
        usr/local/bin/pineapple-mission \
        usr/local/bin/pineapple-gestures \
        usr/share/pineappleos/Desktop/data/labwc/rc.xml \
        usr/share/pineappleos/Desktop/data/prepare.sh \
        usr/share/sddm/themes/pineappleos \
        usr/share/wayland-sessions \
        etc/systemd/user/pineappleos-session.target \
        etc/systemd/user/pineapple-compositor.service \
        etc/systemd/user/pineapple-shell.service \
        etc/systemd/user/pineapple-dock.service \
        ; do
        if [ -e "$R/$p" ]; then
            echo "    OK  $p"
        else
            echo "    AUSENTE  $p"
        fi
    done
    echo "    --- /etc/systemd/user/ ---"
    ls "$R/etc/systemd/user/" 2>/dev/null | sed 's/^/      /' || true

    echo "=> [grafico] usuário live 'user' (senha 'pineapple')"
    grep -q '^user:' "$R/etc/passwd" 2>/dev/null || \
        sudo chroot "$R" /usr/sbin/useradd -m -s /bin/bash \
            -G video,input,seat,audio,sudo user >/dev/null 2>&1 || true
    echo "user:pineapple" | sudo chroot "$R" /usr/sbin/chpasswd >/dev/null 2>&1 || true
    sudo mkdir -p "$R/home/user" "$R/etc/systemd/system/multi-user.target.wants"
    # Serviço SYSTEMD (não depende de getty/VT que o console=ttyS0 suprime):
    sudo tee "$R/etc/systemd/system/pineapple-vm-session.service" >/dev/null <<'SVCS'
[Unit]
Description=Pineapple VM graphical session (teste)
After=systemd-user-sessions.service graphical.target
Wants=graphical.target

[Service]
Type=simple
User=user
Environment=HOME=/home/user
StandardOutput=console
StandardError=console
ExecStart=/usr/share/pineappleos/session/session-loader.sh

[Install]
WantedBy=multi-user.target
SVCS
    sudo ln -sf ../pineapple-vm-session.service \
        "$R/etc/systemd/system/multi-user.target.wants/pineapple-vm-session.service"

    echo "=> [grafico] loader da sessão (prova por /dev/console)"
    sudo mkdir -p "$R/usr/share/pineappleos/session"
    sudo tee "$R/usr/share/pineappleos/session/session-loader.sh" >/dev/null <<'SESS'
#!/bin/bash
# Executado pelo serviço pineapple-vm-session (User=user) quando o sistema
# atinge multi-user. A saída vai pro console via StandardOutput/Error=console.
export PINEAPPLE_LOADED=1
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export XDG_SESSION_TYPE=wayland
export XDG_SESSION_DESKTOP=PineappleOS
export XDG_CURRENT_DESKTOP=PineappleOS
export GDK_BACKEND=wayland
export QT_QPA_PLATFORM=wayland
export WLR_BACKENDS=headless
export WLR_LIBINPUT_NO_DEVICES=1
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
mkdir -p "$XDG_RUNTIME_DIR" 2>/dev/null || true
echo "[PINEAPPLE-UI] loader ok uid=$(id -u)"
exec dbus-run-session -- /usr/share/pineappleos/session/session-main.sh
SESS
    sudo tee "$R/usr/share/pineappleos/session/session-main.sh" >/dev/null <<'MAIN'
#!/bin/bash
set -u
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export XDG_SESSION_TYPE=wayland
export XDG_SESSION_DESKTOP=PineappleOS
export XDG_CURRENT_DESKTOP=PineappleOS
export GDK_BACKEND=wayland
export QT_QPA_PLATFORM=wayland
export WLR_BACKENDS=headless
export WLR_LIBINPUT_NO_DEVICES=1
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
echo "[PINEAPPLE-UI] dbus ok, bootstrap systemd --user"
systemd --user >"$XDG_RUNTIME_DIR/user-boot.log" 2>&1 &
for _ in $(seq 1 200); do
    [ -S "$XDG_RUNTIME_DIR/systemd/private" ] && break
    sleep 0.1
done
systemctl --user import-environment XDG_SESSION_TYPE XDG_SESSION_DESKTOP \
    XDG_CURRENT_DESKTOP WLR_BACKENDS WLR_LIBINPUT_NO_DEVICES GDK_BACKEND QT_QPA_PLATFORM PATH || true
echo "[PINEAPPLE-UI] systemd-user ok, iniciando compositor (labwc)"
systemctl --user start pineapple-compositor.service
W="-"
wl=""
for i in $(seq 1 120); do
    wl="$(ls "$XDG_RUNTIME_DIR"/wayland-* 2>/dev/null | head -n1 || true)"
    [ -n "$wl" ] && { W=ok; break; }
    sleep 0.25
done
echo "[PINEAPPLE-UI] socket wayland: $W ${wl##*/}"
if [ -n "$wl" ]; then
    export WAYLAND_DISPLAY="${wl##*/}"
    systemctl --user import-environment WAYLAND_DISPLAY || true
fi
systemctl --user enable --now pineapple-wallpaper.service \
    pineapple-shell.service pineapple-dock.service pineapple-launcher.service \
    pineapple-launchpad.service pineapple-mission.service pineapple-gestures.service \
    pineapple-notifyd.service pineapple-control-center.service pineapple-ai.service \
    >/dev/null 2>&1 || true
systemctl --user start pineappleos-session.target || true
sleep 8
echo "[PINEAPPLE-UI] unidades:"
systemctl --user list-units --no-legend --type=service \
    | awk '{print $1}' | grep '^pineapple-' \
    | while read -r u; do
        st="$(systemctl --user is-active "$u" 2>/dev/null || echo ?)"
        echo "[PINEAPPLE-UI]   $u $st"
    done
sleep 40
st="$(systemctl --user is-active pineapple-compositor.service 2>/dev/null || echo inactive)"
echo "[PINEAPPLE-UI] compositor apos 40s=$st"
if [ "$st" = "active" ]; then
    echo "[PINEAPPLE-UI] UP"
fi
sleep 90
systemctl --user stop pineappleos-session.target >/dev/null 2>&1 || true
sudo systemctl poweroff >/dev/null 2>&1 || true
exit 0
MAIN
    sudo chmod +x "$R/usr/share/pineappleos/session/session-loader.sh" \
                 "$R/usr/share/pineappleos/session/session-main.sh"

    echo "=> [grafico] regravando squashfs"
    comp="$(unsquashfs -s "$SQ" 2>/dev/null | sed -n 's/^Compression\s*//p' | tr 'A-Z' 'a-z' || true)"
    case "$comp" in xz|zstd|gzip|lzo|lz4) : ;; *) comp=xz ;; esac
    echo "   compressão atual: $comp"
    sudo mksquashfs "$R" "$WORK/newfs.squashfs" -comp "$comp" \
        -no-progress -processors "$(nproc)" > "$WORK/mksquash.log" 2>&1 || {
        echo "FALHA[grafico]: mksquashfs"; tail -20 "$WORK/mksquash.log"; exit 1; }
    sudo chown "$(id -u):$(id -g)" "$WORK/newfs.squashfs"
    mv "$WORK/newfs.squashfs" "$SQ"
    sudo rm -rf "$R"
    echo "=> [grafico] squashfs regravado com sessão de teste (dirá PASS se a UI subir)"
}

if [ "$GRAPHICAL" = "1" ]; then
    prepare_graphical
fi

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

# run_boot foi removida: os QEMUs sobem direto como filhos do pai em background
# e um único loop do pai monitora os dois logs ao vivo (evita trap/subshell bugs).

analyze() {
    # ESTRITO: PASS apenas se o early-boot systemd completar ("basic.target").
    # O systemd 257 imprime "Reached target basic.target - Basic System."
    # (versões antigas: "Reached target Basic System.") — casa os dois.
    local name="$1" log="$2" s="$3" state="$4"
    scrub < "$log" > "$s"
    if [ ! -s "$s" ]; then
        echo "FAIL[$name]: log de boot vazio"
        return 1
    fi
    echo "    --- primeiras 12 linhas do boot log ---"
    sed -n '1,12p' "$s" | sed 's/^/      /'
    case "$state" in
        pass)   [ "$GRAPHICAL" = "1" ] \
                    && echo "PASS[$name]: sessão gráfica Pineapple de pé (compositor + applets)" \
                    || echo "PASS[$name]: atingiu o alvo Basic System (early-boot completo)" ;;
        panic)  echo "FAIL[$name]: kernel panic detectado" ;;
        grub)   echo "FAIL[$name]: erro do GRUB no boot" ;;
        earlyexit) echo "FAIL[$name]: QEMU encerrou antes do alvo" ;;
        timeout) echo "FAIL[$name]: timeout sem atingir o alvo" ;;
    esac
    if [ "$state" = "pass" ]; then
        if [ "$GRAPHICAL" = "1" ]; then
            grep -a "PINEAPPLE-UI" "$s" | sed 's/^/      /' || true
        elif grep -q "debian login:" "$s"; then
            echo "PASS[$name]: getty vivo (multi-user.target / login: pronto)"
        fi
        return 0
    fi
    [ "$GRAPHICAL" = "1" ] && grep -a "PINEAPPLE-UI" "$s" | sed 's/^/      /' || true
    tail -40 "$s" | sed 's/^/      /'
    return 1
}

# 5.1 e 5.2 — BIOS (SeaBIOS) e UEFI (OVMF) em PARALELO
# Atenção: nada de subshell/background com trap herdado — os QEMUs sobem direto
# como filhos do shell e UM LOOOP do pai monitora os dois logs ao vivo.
echo "==> boots BIOS (SeaBIOS, El Torito) e UEFI (OVMF) em paralelo (até ${BOOT_TIMEOUT}s cada)"

ORIG_CONFIG_LOG="$WORK/test.iso"
$QRUN "${QEMU[@]}" -cdrom "$WORK/test.iso" -boot d \
    > "$WORK/bios.log" 2>&1 &
BIOS_Q=$!

CODE_FD=""
VARS_TMPL=""
if [ -d /usr/share/OVMF ]; then
    CODE_FD="$(ls /usr/share/OVMF/OVMF_CODE*.fd 2>/dev/null | head -n1 || true)"
    VARS_TMPL="$(ls /usr/share/OVMF/OVMF_VARS*.fd 2>/dev/null | head -n1 || true)"
fi

EFI_Q=""
EFI_MODE="ded"
if [ -n "$CODE_FD" ] && [ -n "$VARS_TMPL" ]; then
    cp "$VARS_TMPL" "$WORK/OVMF_VARS.fd"
    $QRUN "${QEMU[@]}" \
        -drive 'if=pflash,format=raw,readonly=on,file='"$CODE_FD" \
        -drive 'if=pflash,format=raw,file='"$WORK/OVMF_VARS.fd" \
        -cdrom "$WORK/test.iso" -boot order=d \
        > "$WORK/efi.log" 2>&1 &
    EFI_Q=$!
else
    echo "aviso: OVMF não instalado — pulando teste UEFI"
fi

# watcher: um loop no pai, até BOOT_TIMEOUT ou ambos qemus saírem
# Alvo: no modo normal é basic.target; no modo gráfico é a evidência da UI.
if [ "$GRAPHICAL" = "1" ]; then
    TARGET_RE="PINEAPPLE-UI: UP"
else
    TARGET_RE="Reached target (Basic System|basic\.target)"
fi
scrub < "$WORK/bios.log" > "$WORK/bios.live"
scrub < "$WORK/efi.log" > "$WORK/efi.live" 2>/dev/null || :
deadline=$((SECONDS + BOOT_TIMEOUT))
bios_done=""
efi_done=""
while [ "$SECONDS" -lt "$deadline" ]; do
    sleep 4
    if [ -z "$bios_done" ]; then
        scrub < "$WORK/bios.log" > "$WORK/bios.live"
        if grep -qE "$TARGET_RE" "$WORK/bios.live"; then bios_done="pass"; fi
        if grep -q "Kernel panic" "$WORK/bios.live"; then bios_done="panic"; fi
        if grep -qE "^error: " "$WORK/bios.live"; then bios_done="grub"; fi
        if ! kill -0 "$BIOS_Q" 2>/dev/null; then bios_done="${bios_done:-earlyexit}"; fi
    fi
    if [ -n "$EFI_Q" ] && [ -z "$efi_done" ]; then
        scrub < "$WORK/efi.log" > "$WORK/efi.live"
        if grep -qE "$TARGET_RE" "$WORK/efi.live"; then efi_done="pass"; fi
        if grep -q "Kernel panic" "$WORK/efi.live"; then efi_done="panic"; fi
        if grep -qE "^error: " "$WORK/efi.live"; then efi_done="grub"; fi
        if ! kill -0 "$EFI_Q" 2>/dev/null; then efi_done="${efi_done:-earlyexit}"; fi
    fi
    if [ -n "$bios_done" ] && { [ -z "$EFI_Q" ] || [ -n "$efi_done" ]; }; then
        break
    fi
done
bios_done="${bios_done:-timeout}"
efi_done="${efi_done:-timeout}"

kill "$BIOS_Q" 2>/dev/null || true
[ -n "$EFI_Q" ] && kill "$EFI_Q" 2>/dev/null || true
wait "$BIOS_Q" 2>/dev/null || true
[ -n "$EFI_Q" ] && wait "$EFI_Q" 2>/dev/null || true

BIOS_STATUS=0
EFI_STATUS=0
scrub < "$WORK/bios.log" > "$WORK/bios.s"
analyze "BIOS" "$WORK/bios.log" "$WORK/bios.s" "$bios_done" || BIOS_STATUS=$?
if [ -s "$WORK/efi.log" ]; then
    scrub < "$WORK/efi.log" > "$WORK/efi.s"
    analyze "UEFI" "$WORK/efi.log" "$WORK/efi.s" "$efi_done" || EFI_STATUS=$?
else
    analyze "UEFI" "$WORK/bios.log" "$WORK/bios.s" "$efi_done" || EFI_STATUS=$?
fi
echo "    (último BIOS): $(tail -2 "$WORK/bios.log" 2>/dev/null | scrub | tr '\n' ' ' | cut -c1-120)"
echo "    (último UEFI): $(tail -2 "$WORK/efi.log" 2>/dev/null | scrub | tr '\n' ' ' | cut -c1-120)"

if [ "$BIOS_STATUS" -ne 0 ] || [ "$EFI_STATUS" -ne 0 ]; then
    echo "==> BOOT TEST FALHOU"
    exit 1
fi
echo "==> BOOT TEST OK (BIOS+UEFI bootaram)"
exit 0