#!/bin/bash
# =============================================================================
#  setup-voice.sh — dependências de voz (TTS + STT) para o Pineapple AI
# =============================================================================
set -euo pipefail

echo "==> Instalando TTS (espeak-ng) e gravação (arecord/sox)"
sudo apt install -y espeak-ng alsa-utils sox python3-pip

echo "==> Instalando Vosk (reconhecimento offline)"
pip3 install --user vosk

echo "==> Baixando modelo pt-BR (primeira execução automática)"
mkdir -p "$HOME/.local/share/vosk"
if [ ! -d "$HOME/.local/share/vosk/vosk-model-small-pt-0.3" ]; then
  wget -q https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip -O /tmp/vosk.zip
  unzip -q -o /tmp/vosk.zip -d "$HOME/.local/share/vosk"
fi

echo "==> Opcional: TTS de alta qualidade (piper)"
read -r -p "Instalar piper (melhor voz)? [s/N] " resp
if [[ "$resp" =~ ^[sS]$ ]]; then
  pip3 install --user piper-tts
fi

echo "==> Pronto! Teste:  pineapple-voice 5"
