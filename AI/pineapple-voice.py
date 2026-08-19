#!/usr/bin/env python3
# =============================================================================
#  pineapple-voice — CLI de voz do assistente Pineapple OS
#  Grava, transcreve (Vosk), responde (agente) e fala (TTS local).
#  Uso: pineapple-voice [segundos]
# =============================================================================
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from voice import cli  # noqa: E402

if __name__ == "__main__":
    sys.exit(cli())
