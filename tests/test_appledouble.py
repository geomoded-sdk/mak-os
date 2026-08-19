"""Testes do formato AppleDouble (arquivos '._') do BFS/Pineapple OS."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Filesystem"))

from pineapplefs import appledouble as ad  # noqa: E402


class TestAppleDoubleFormat(unittest.TestCase):
    def test_magic_and_version(self):
        data = ad.encode({ad.ID_COMMENT: b"oi"})
        self.assertEqual(data[:4], (0x00051607).to_bytes(4, "big"))
        self.assertEqual(data[4:8], (0x00020000).to_bytes(4, "big"))

    def test_roundtrip_entries(self):
        entries = {
            ad.ID_COMMENT: b"comentario",
            ad.ID_DATA_FORK: b"dados",
            ad.ID_REAL_NAME: b"arquivo.txt",
        }
        decoded = ad.decode(ad.encode(entries))
        self.assertEqual(decoded, entries)

    def test_rejects_wrong_magic(self):
        with self.assertRaises(ValueError):
            ad.decode(b"\x00\x00\x00\x00" + bytes(22))

    def test_xattr_roundtrip(self):
        xattrs = {"org.pineappleos.autor": b"Pedro", "tags": b"foto,familia"}
        payload = ad.encode_xattrs(xattrs)
        self.assertEqual(ad.decode_xattrs(payload), xattrs)

    def test_unicode_name_roundtrip(self):
        payload = ad.encode_unicode_name("Fotos 2026")
        self.assertEqual(ad.decode_unicode_name(payload), "Fotos 2026")

    def test_build_sidecar_roundtrip(self):
        payload = ad.build_sidecar(
            xattrs={"com.apple.metadata:kMDItemTitle": b"Minha Foto"},
            finder_flags=ad.FINDER_INVISIBLE,
            resource_fork=b"\x00\x00\x00\x10RFORK",
            unicode_name="foto.jpg",
        )
        parsed = ad.parse_sidecar(payload)
        self.assertTrue(parsed["finder_flags"] & ad.FINDER_INVISIBLE)
        self.assertEqual(
            parsed["xattrs"]["com.apple.metadata:kMDItemTitle"],
            b"Minha Foto",
        )
        self.assertEqual(parsed["resource_fork"], b"\x00\x00\x00\x10RFORK")
        self.assertEqual(parsed["unicode_name"], "foto.jpg")

    def test_resource_fork_as_xattr(self):
        # no macOS, o resource fork vira a xattr com.apple.ResourceFork
        payload = ad.build_sidecar(
            xattrs={ad.XATTR_RESOURCE_FORK: b"RF"},
            finder_flags=0,
        )
        parsed = ad.parse_sidecar(payload)
        self.assertIn("resource_fork", parsed)
        self.assertEqual(parsed["resource_fork"], b"RF")
        self.assertNotIn(ad.XATTR_RESOURCE_FORK, parsed["xattrs"])

    def test_empty_sidecar(self):
        payload = ad.build_sidecar()
        parsed = ad.parse_sidecar(payload)
        self.assertEqual(parsed["xattrs"], {})
        self.assertEqual(parsed["finder_flags"], 0)


if __name__ == "__main__":
    unittest.main()