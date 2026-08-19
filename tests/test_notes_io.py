"""Testes de exportação/importação de notas em Markdown (Pineapple Notes)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Apps", "Notes"))
from pineapple_notes_io import note_from_markdown, note_to_markdown  # noqa: E402


class TestNoteToMarkdown(unittest.TestCase):
    def test_roundtrip(self):
        md = note_to_markdown("Minha nota", "Linha um\nLinha dois")
        self.assertEqual(md, "# Minha nota\n\nLinha um\nLinha dois\n")

    def test_empty_body(self):
        md = note_to_markdown("Só título", "")
        self.assertEqual(md, "# Só título\n")

    def test_empty_title(self):
        md = note_to_markdown("", "conteúdo")
        self.assertEqual(md, "# (sem título)\n\nconteúdo\n")


class TestNoteFromMarkdown(unittest.TestCase):
    def test_heading_title(self):
        title, body = note_from_markdown("# Título\n\ncorpo aqui")
        self.assertEqual(title, "Título")
        self.assertEqual(body, "corpo aqui")

    def test_plain_first_line_title(self):
        title, body = note_from_markdown("Título\ncorpo")
        self.assertEqual(title, "Título")
        self.assertEqual(body, "corpo")

    def test_empty(self):
        title, body = note_from_markdown("")
        self.assertEqual((title, body), ("", ""))


class TestNotesRoundtrip(unittest.TestCase):
    def test_full_roundtrip(self):
        md = note_to_markdown("Lista", "- item 1\n- item 2")
        title, body = note_from_markdown(md)
        self.assertEqual(title, "Lista")
        self.assertEqual(body, "- item 1\n- item 2")


if __name__ == "__main__":
    unittest.main()
