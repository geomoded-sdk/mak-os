"""Testes do módulo de voz do Mak AI (sem exigir mic/áudio)."""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "AI"))
from mak_ai import Agent  # noqa: E402
import voice  # noqa: E402


class FakeClient:
    def available(self):
        return False


class TestVoiceAssistant(unittest.TestCase):
    def test_run_once_no_speech(self):
        agent = Agent(FakeClient())
        va = voice.VoiceAssistant(agent)

        class FakeSTT:
            def listen(self, seconds):
                return ""

        class FakeTTS:
            def speak(self, text):
                raise AssertionError("não deve falar sem texto")

        va.stt = FakeSTT()
        va.tts = FakeTTS()
        self.assertEqual(va.run_once(5), "não escutei nada")

    def test_run_once_with_speech_and_tts(self):
        agent = Agent(FakeClient())

        class FakeSTT:
            def listen(self, seconds):
                return "abrir a calculadora"

        class FakeTTS:
            def __init__(self):
                self.spoken = []

            def speak(self, text):
                self.spoken.append(text)

        va = voice.VoiceAssistant(agent)
        va.stt = FakeSTT()
        tts = FakeTTS()
        va.tts = tts

        reply = va.run_once(5)
        self.assertTrue(reply)
        self.assertTrue(tts.spoken)

    def test_tts_detects_missing_engine(self):
        with patch("shutil.which", return_value=None):
            self.assertFalse(voice.TTS.available())


if __name__ == "__main__":
    unittest.main()
