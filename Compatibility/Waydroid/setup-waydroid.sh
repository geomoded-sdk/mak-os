#!/bin/bash
# =============================================================================
#  setup-waydroid.sh — instala o Waydroid (Android) no Pineapple OS
# =============================================================================
set -euo pipefail

echo "==> Instalando dependências"
sudo apt install -y curl ca-certificates python3 lxc waydroid

echo "==> Registrando a imagem do Android (Waydroid)"
sudo waydroid init

echo "==> Habilite os módulos do kernel (binder, overlayfs) se necessário"
if ! ls /dev/binderfs >/dev/null 2>&1 && ! ls /dev/binder* >/dev/null 2>&1; then
  echo "Aviso: binder não encontrado. Carregue os módulos:"
  echo "  sudo modprobe binder_linux"
  echo "  sudo modprobe ashmem_linux"
fi

echo "==> Iniciando o Waydroid"
sudo systemctl enable --now waydroid-container || true
waydroid session start &

cat > "$HOME/.local/bin/pineapple-waydroid" <<'EOF'
#!/bin/bash
# Atalho do Waydroid no Pineapple OS
case "${1:-start}" in
  start)  waydroid session start & ;;
  stop)   waydroid session stop ;;
  apps)   waydroid app list ;;
  shell)  waydroid shell ;;
  install) shift; waydroid app install "$@" ;;
  *)      echo "uso: pineapple-waydroid [start|stop|apps|shell|install <apk>]";;
esac
EOF
chmod +x "$HOME/.local/bin/pineapple-waydroid"

echo "==> Waydroid pronto. Use:  pineapple-waydroid install app.apk"
