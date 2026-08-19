"""Testes utilitários do Pineapple OS (formatação, persistência, gerenciador)."""
import os
import sys
import tempfile
import unittest

# Pineapple AppImage manager
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Compatibility", "AppImage"))


class TestAppImageSlug(unittest.TestCase):
    def test_slug_lowercases(self):
        # réplica da lógica do pineapple-appimage.sh
        def slug(name):
            return name.lower().replace(" ", "-")

        self.assertEqual(slug("Meu App"), "meu-app")


class TestHumanSize(unittest.TestCase):
    """Espelha a lógica de human_size do Finder (Rust) para validação."""

    @staticmethod
    def human_size(bytes_):
        units = ["B", "KiB", "MiB", "GiB", "TiB"]
        v = float(bytes_)
        i = 0
        while v >= 1024.0 and i < 4:
            v /= 1024.0
            i += 1
        if i == 0:
            return f"{int(bytes_)} B"
        return f"{v:.1f} {units[i]}"

    def test_bytes(self):
        self.assertEqual(self.human_size(512), "512 B")

    def test_kib(self):
        self.assertEqual(self.human_size(2048), "2.0 KiB")

    def test_mib(self):
        self.assertEqual(self.human_size(5 * 1024 * 1024), "5.0 MiB")


class TestNotesStorage(unittest.TestCase):
    def test_note_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            import json

            note = {"id": "abc", "title": "Lista", "body": "item 1", "updated": "2026-01-01"}
            path = os.path.join(tmp, "abc.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(note, f)
            with open(path, encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded["title"], "Lista")
            self.assertEqual(loaded["body"], "item 1")


if __name__ == "__main__":
    unittest.main()
