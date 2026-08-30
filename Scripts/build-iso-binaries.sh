#!/bin/bash
# =============================================================================
#  build-iso-binaries.sh — compila os binários da interface que entram na ISO.
#
#  As units systemd da sessão referem /usr/local/bin/pineapple-* (Rust) e
#  /usr/bin/pineapple-*.py (Python). build-iso.sh só copia FONTES para a
#  imagem; este script produz os binários REAIS em build/iso-stage/, que
#  build-iso.sh abastece em config/includes.chroot/usr/{local/bin,bin}.
#
#  É executado PELO USUÁRIO do runner (sem sudo) porque cargo/rustup vivem no
#  home do usuário; o gtk4-layer-shell (não empacotado no Debian estável)
#  é compilado e instalado no host antes do cargo build.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/build/iso-stage"
mkdir -p "$OUT/usr/local/bin" "$OUT/usr/bin"

if ! pkg-config --exists gtk4-layer-shell 2>/dev/null; then
    echo "==> Compilando gtk4-layer-shell (host, deps do gtk4-layer-shell Rust)"
    rm -rf "$ROOT/build/gtk4-layer-shell"
    git clone --depth 1 \
        https://github.com/wmww/gtk4-layer-shell.git \
        "$ROOT/build/gtk4-layer-shell"
    meson setup "$ROOT/build/gtk4-layer-shell/build" \
        "$ROOT/build/gtk4-layer-shell" -Dvapi=false
    ninja -C "$ROOT/build/gtk4-layer-shell/build"
    sudo ninja -C "$ROOT/build/gtk4-layer-shell/build" install
    sudo ldconfig
fi

echo "==> Compilando componentes Rust"
for spec in \
    Desktop:pineapple-shell \
    Dock:pineapple-dock \
    Launcher:pineapple-launcher \
    Launchpad:pineapple-launchpad \
    Mission:pineapple-mission \
    Canopy:pineapple-canopy \
    Gestures:pineapple-gestures ; do
    crate="${spec%%:*}"
    bin="${spec##*:}"
    echo "=> $crate -> $bin"
    (cd "$ROOT/$crate" && cargo build --release 2>/dev/null) \
        && cp "$ROOT/$crate/target/release/$bin" "$OUT/usr/local/bin/$bin" \
        || echo "   [aviso] $bin não compilado"
done

echo "==> Instalando aplicativos Python"
find "$ROOT/Apps" -maxdepth 2 -name '*.py' -type f -exec \
    install -m755 {} "$OUT/usr/bin/" \;

echo "==> Daemons de sessão (nomes fixos das units)"
install -m755 "$ROOT/Apps/Wallpaper/pineapple-wallpaper.py" \
    "$OUT/usr/bin/pineapple-wallpaper"
install -m755 "$ROOT/AI/pineapple-ai.py" "$OUT/usr/bin/pineapple-ai"

echo "==> Binários da interface em $OUT"
ls "$OUT/usr/local/bin/" | sed 's/^/    /'
ls "$OUT/usr/bin/" | sed 's/^/    /'