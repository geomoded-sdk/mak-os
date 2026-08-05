#!/bin/bash
# =============================================================================
#  setup-ollama.sh — instala e configura o Ollama para o Mak OS
# =============================================================================
set -euo pipefail

MODEL="${MODEL:-llama3.1}"
SERVICE_USER="${SERVICE_USER:-$(whoami)}"

echo "==> Instalando Ollama"
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi

echo "==> Criando serviço systemd (mak-ollama.service)"
sudo tee /etc/systemd/system/mak-ollama.service > /dev/null <<EOF
[Unit]
Description=Mak OS Ollama (assistente local)
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Environment=OLLAMA_HOST=127.0.0.1:11434
ExecStart=/usr/local/bin/ollama serve
Restart=on-failure

[Install]
WantedBy=default.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now mak-ollama.service

echo "==> Baixando modelo ${MODEL} (primeira execução demora um pouco)"
ollama pull "${MODEL}"

echo "==> Pronto! Teste:  mak-ai 'resuma como anda o tempo por aí'"
