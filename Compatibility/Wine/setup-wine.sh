#!/bin/bash
# =============================================================================
#  setup-wine.sh — instala Wine + Winetricks e configura o frontend mak-wine
# =============================================================================
set -euo pipefail

echo "==> Habilitando arquitetura 32 bits (necessária para o Wine)"
sudo dpkg --add-architecture i386
sudo apt update

echo "==> Instalando Wine e Winetricks"
sudo apt install -y wine wine64 winetricks

echo "==> Inicializando o prefixo (wineboot)"
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine-makos}"
mkdir -p "$WINEPREFIX"
wineboot -i || true

cat > "$HOME/.local/bin/mak-wine" <<'EOF'
#!/bin/bash
# Frontend do Wine no Mak OS
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine-makos}"
export WINEARCH=win64
exec wine "$@"
EOF
chmod +x "$HOME/.local/bin/mak-wine"

echo "==> Wine pronto. Use:  mak-wine programa.exe"
echo "    (Winetricks: winetricks --gui)"
