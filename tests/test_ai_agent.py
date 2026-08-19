"""Testes do agente IA do Pineapple OS (sem exigir GTK ou Ollama)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "AI"))
from pineapple_ai import Agent  # noqa: E402


class FakeClient:
    """Client Ollama simulado: nunca disponível."""

    def available(self):
        return False

    def chat(self, messages, stream=False):
        raise AssertionError("chat não deve ser chamado offline")


class TestDetectAction(unittest.TestCase):
    def setUp(self):
        self.agent = Agent(FakeClient())

    def test_open_app(self):
        action = self.agent.detect_action("abrir a calculadora")
        self.assertEqual(action["type"], "open_app")
        self.assertIn("calculadora", action["target"])

    def test_open_app_english(self):
        action = self.agent.detect_action("open terminal")
        self.assertEqual(action["type"], "open_app")

    def test_search_files(self):
        action = self.agent.detect_action("pesquisar relatorio")
        self.assertEqual(action["type"], "search_files")
        self.assertEqual(action["target"], "relatorio")

    def test_search_files_english(self):
        action = self.agent.detect_action("find planilha")
        self.assertEqual(action["type"], "search_files")

    def test_summarize(self):
        action = self.agent.detect_action("resumir ~/documento.txt")
        self.assertEqual(action["type"], "summarize")

    def test_run_command(self):
        action = self.agent.detect_action("executar pineapple-canopy")
        self.assertEqual(action["type"], "run")

    def test_general_question(self):
        self.assertIsNone(self.agent.detect_action("qual a capital do brasil?"))


class TestTools(unittest.TestCase):
    def setUp(self):
        self.agent = Agent(FakeClient())

    def test_open_app_known(self):
        # reconhecido: ou "abri <app>" ou informa que não está instalado;
        # jamais "não encontrei".
        result = self.agent.open_app("calculadora")
        self.assertNotIn("não encontrei", result)

    def test_open_app_unknown(self):
        result = self.agent.open_app("app-inexistente-xyz")
        self.assertIn("não encontrei", result)

    def test_search_files_finds_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "relatorio-pineapple.txt"
            target.write_text("conteúdo", encoding="utf-8")
            results = self.agent.search_files("relatorio", base=tmp)
            self.assertTrue(any("relatorio" in r for r in results))

    def test_search_files_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = self.agent.search_files("nao-existe", base=tmp)
            self.assertEqual(results, [])

    def test_run_command_whitelist(self):
        # autorizado pela whitelist: ou executa, ou informa que não está instalado
        result = self.agent.run_command("pineapple-canopy")
        self.assertTrue("abri" in result or "não está instalado" in result)

    def test_run_command_blocked(self):
        result = self.agent.run_command("rm -rf /")
        self.assertIn("não autorizado", result)

    def test_summarize_missing_file(self):
        result = self.agent.summarize_file("/caminho/que/nao/existe.txt")
        self.assertIn("não encontrado", result)

    def test_handle_offline_general(self):
        result = self.agent.handle("qual a capital do brasil?")
        self.assertIn("Ollama não está rodando", result)


if __name__ == "__main__":
    unittest.main()
