#!/bin/bash
# =============================================================================
#  setup-wine.sh — instala Wine + Winetricks e configura o frontend pineapple-wine
# =============================================================================
set -euo pipefail

echo "==> Habilitando arquitetura 32 bits (necessária para o Wine)"
sudo dpkg --add-architecture i386
sudo apt update

echo "==> Instalando Wine e Winetricks"
sudo apt install -y wine wine64 winetricks

echo "==> Inicializando o prefixo (wineboot)"
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine-pineappleos}"
mkdir -p "$WINEPREFIX"
wineboot -i || true

cat > "$HOME/.local/bin/pineapple-wine" <<'EOF'
#!/bin/bash
# Frontend do Wine no Pineapple OS
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine-pineappleos}"
export WINEARCH=win64
exec wine "$@"
EOF
chmod +x "$HOME/.local/bin/pineapple-wine"

echo "==> Wine pronto. Use:  pineapple-wine programa.exe"
echo "    (Winetricks: winetricks --gui)"
