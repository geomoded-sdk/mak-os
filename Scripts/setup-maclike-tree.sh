#!/bin/bash
# =============================================================================
#  setup-maclike-tree.sh — cria a árvore de arquivos estilo macOS no sistema
#
#  O Pineapple OS apresenta ao usuário uma estrutura diferente do Linux:
#
#    /Macintosh HD     → / (volume raiz, nome amigável)
#    /Users            → /home
#    /Applications     → /usr/share/applications
#    /System           → /usr (somente leitura na interface)
#    /Library          → /usr/share (metadados e serviços)
#    /Volumes          → /media (volumes montados, PNFS)
#    /Trash            → ~/.local/share/Trash (lixeira XDG, por usuário)
#
#  Esta primeira versão usa SYMLINKS (não bind mounts) para não quebrar
#  pacotes Debian/POSIX: a camada física continua intacta. A interface
#  (Canopy) consome esta árvore. Bind mounts virão depois de testes.
#
#  Uso: sudo ./Scripts/setup-maclike-tree.sh
# =============================================================================
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Execute como root: sudo $0" >&2
  exit 1
fi

echo "==> Criando árvore mac-like em /"

link() {
  local target="$1" linkpath="$2"
  if [ -L "$linkpath" ]; then
    echo "    mantém: $linkpath → $(readlink "$linkpath")"
  elif [ -e "$linkpath" ]; then
    echo "    pula (existe e não é link): $linkpath"
  else
    ln -s "$target" "$linkpath"
    echo "    $linkpath → $target"
  fi
}

# Volume raiz com nome amigável (pasta real de apresentação).
mkdir -p "/Macintosh HD"
echo "Pineapple OS — volume raiz" > "/Macintosh HD/.placeholder" 2>/dev/null || true

# Árvore mac-like (symlinks de apresentação).
link /home                        /Users
link /usr/share/applications      /Applications
link /usr                         /System
link /usr/share                   /Library
link /media                       /Volumes

echo "==> Árvore mac-like criada (symlinks de apresentação)."
echo "    A interface (Canopy) deve navegar por estes caminhos."
echo "    Física POSIX (/usr, /home…) permanece intacta — compatível."
