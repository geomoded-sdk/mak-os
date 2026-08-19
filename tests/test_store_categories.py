"""Testes das categorias da Pineapple Store."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Apps", "Store"))
from pineapple_store_categories import CATEGORIES, category_for, category_label  # noqa: E402


class TestCategoryFor(unittest.TestCase):
    def test_native_apps(self):
        self.assertEqual(category_for("org.pineappleos.calculator"), "nativos")
        self.assertEqual(category_for("org.pineappleos.terminal"), "nativos")

    def test_graphics(self):
        self.assertEqual(category_for("org.gimp.GIMP"), "graficos")
        self.assertEqual(category_for("org.inkscape.Inkscape"), "graficos")

    def test_office(self):
        self.assertEqual(category_for("org.libreoffice.LibreOffice"), "escritorio")

    def test_media(self):
        self.assertEqual(category_for("org.videolan.VLC"), "midia")
        self.assertEqual(category_for("com.spotify.Client"), "midia")

    def test_internet(self):
        self.assertEqual(category_for("org.mozilla.firefox"), "internet")
        self.assertEqual(category_for("com.discordapp.Discord"), "internet")

    def test_dev(self):
        self.assertEqual(category_for("com.visualstudio.code"), "desenvolvimento")

    def test_games(self):
        self.assertEqual(category_for("org.libretro.RetroArch"), "jogos")

    def test_unknown_defaults_to_other(self):
        self.assertEqual(category_for("com.example.Unknown"), "outros")

    def test_case_insensitive_and_empty(self):
        self.assertEqual(category_for("Org.Mozilla.Firefox"), "internet")
        self.assertEqual(category_for(""), "outros")
        self.assertEqual(category_for(None), "outros")


class TestCategories(unittest.TestCase):
    def test_categories_are_unique(self):
        keys = [k for k, _ in CATEGORIES]
        self.assertEqual(len(keys), len(set(keys)))

    def test_label_lookup(self):
        self.assertEqual(category_label("midia"), "Mídia")
        self.assertEqual(category_label("nao-existe"), "Outros")


if __name__ == "__main__":
    unittest.main()
