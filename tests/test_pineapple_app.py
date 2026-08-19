import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pineapple_app", ROOT / "Compatibility/PineappleApp/pineapple_app.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TestPineappleApp(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_detects_formats_by_signature(self):
        cases = {
            "linux": (b"\x7fELF" + b"\0" * 28, "elf"),
            "windows": (b"MZ" + b"\0" * 30, "pe"),
            "macos": (b"\xcf\xfa\xed\xfe" + b"\0" * 28, "macho"),
        }
        for name, (header, expected) in cases.items():
            path = self.root / name
            path.write_bytes(header)
            self.assertEqual(MODULE.detect(path), expected)

    def test_registers_desktop_entry_with_runtime(self):
        path = self.root / "PineappleApp"
        path.write_bytes(b"\x7fELF" + b"\0" * 28)
        destination = self.root / "applications"
        entry = MODULE.register(path, destination)
        content = entry.read_text(encoding="utf-8")
        self.assertIn("Exec=", content)
        self.assertIn("X-Pineapple-Runtime=elf", content)
        self.assertTrue(entry.exists())

    def test_appimage_extension(self):
        path = self.root / "editor.AppImage"
        path.write_bytes(b"not-an-elf")
        self.assertEqual(MODULE.detect(path), "appimage")


if __name__ == "__main__":
    unittest.main()
