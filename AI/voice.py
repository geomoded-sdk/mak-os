# =============================================================================
#  mak voice — síntese e reconhecimento de voz locais para o Mak AI
#
#  TTS:  espeak-ng (padrão) ou piper (qualidade, opcional)
#  STT:  Vosk (offline, modelo ~50 MB) — grava com arecord/sox
# =============================================================================
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

TTS_ENGINE = os.environ.get("MAK_TTS", "espeak")
VOSK_MODEL_DIR = os.environ.get("VOSK_MODEL_DIR", str(Path.home() / ".local/share/vosk"))

LANG = os.environ.get("MAK_LANG", "pt-BR")


class TTS:
    """Síntese de voz local."""

    @staticmethod
    def available():
        return shutil.which("espeak-ng") is not None or shutil.which("piper") is not None

    def speak(self, text: str):
        if shutil.which("piper"):
            # piper — voz de alta qualidade (onix-pt_BR)
            voice = Path.home() / ".local/share/piper-voices" / "pt_BR"
            model = voice / "onix" / "pt_BR-onix-medium.onnx"
            if model.exists():
                subprocess.run(
                    ["piper", "--model", str(model), "--output_raw"]
                    + shlex.split(text),
                    check=False,
                )
                return
        # fallback: espeak-ng
        if shutil.which("espeak-ng"):
            subprocess.run(
                ["espeak-ng", "-v", "pt-br", "-s", "150", text], check=False
            )
            return
        raise RuntimeError("nenhum motor de TTS instalado (espeak-ng ou piper)")


class STT:
    """Reconhecimento de voz offline com Vosk."""

    MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"

    @staticmethod
    def available():
        return shutil.which("arecord") is not None and shutil.which("sox") is not None

    def _ensure_model(self):
        model_path = Path(VOSK_MODEL_DIR)
        if model_path.exists():
            return model_path
        print("Baixando modelo de voz (pt-BR)...")
        subprocess.run(["wget", "-q", self.MODEL_URL, "-O", "/tmp/vosk.zip"], check=True)
        subprocess.run(["unzip", "-q", "-o", "/tmp/vosk.zip", "-d", VOSK_MODEL_DIR], check=True)
        return Path(VOSK_MODEL_DIR) / "vosk-model-small-pt-0.3"

    def listen(self, seconds: int = 5) -> str:
        if not self.available():
            raise RuntimeError("instale arecord e sox para usar voz")
        try:
            from vosk import KaldiRecognizer, Model
            import json
            import wave
        except ImportError:
            raise RuntimeError("instale o Vosk: pip install vosk") from None

        model_path = self._ensure_model()
        model = Model(str(model_path))

        with tempfile.TemporaryDirectory() as tmp:
            wav = os.path.join(tmp, "capture.wav")
            subprocess.run(
                ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1",
                 "-d", str(seconds), wav],
                check=False,
            )
            if not os.path.exists(wav):
                return ""
            with wave.open(wav, "rb") as wf:
                rec = KaldiRecognizer(model, 16000)
                while True:
                    data = wf.readframes(4000)
                    if not data:
                        break
                    rec.AcceptWaveform(data)
                result = json.loads(rec.FinalResult())
                return result.get("text", "")


class VoiceAssistant:
    """Liga voz -> agente -> resposta falada."""

    def __init__(self, agent, tts=None, stt=None):
        self.agent = agent
        self.tts = tts or TTS()
        self.stt = stt or STT()

    def run_once(self, seconds: int = 5) -> str:
        text = self.stt.listen(seconds)
        if not text:
            return "não escutei nada"
        print(f"[voz->texto] {text}")
        reply = self.agent.handle(text)
        print(f"[resposta] {reply}")
        try:
            self.tts.speak(reply)
        except RuntimeError as e:
            print(f"[tts] {e}")
        return reply


def cli() -> int:
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from mak_ai import Agent, OllamaClient

    agent = Agent(OllamaClient())
    va = VoiceAssistant(agent)
    seconds = 5
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        seconds = int(sys.argv[1])
    try:
        va.run_once(seconds)
    except RuntimeError as e:
        print(f"erro: {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
