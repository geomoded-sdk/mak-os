"""Testes do BFS (Pineapple File System) — volume exFAT + recursos APFS/HFS+."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Filesystem"))

from pineapplefs import BFSVolume, SpotlightIndex, archive, sparse  # noqa: E402


class TestBFSInit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "vol")
        self.vol = BFSVolume(self.root).init()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_bfsprivate_created(self):
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".bfsprivate")))
        self.assertTrue(
            os.path.exists(os.path.join(self.root, ".bfsprivate", "volume.info"))
        )

    def test_macos_artifacts(self):
        for name in [".Spotlight-V100", ".fseventsd", ".Trashes",
                     ".DS_Store", ".metadata_never_index", ".localized"]:
            self.assertTrue(os.path.exists(os.path.join(self.root, name)), name)

    def test_volume_info(self):
        info = self.vol.info()
        self.assertEqual(info["magic"], "BFS")
        self.assertEqual(info["format"], "bfs-overlay")
        self.assertTrue(info["case_insensitive"])

    def test_artifacts_have_utility(self):
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".Trashes", "pineapple")))
        self.assertTrue(os.path.exists(os.path.join(self.root, ".fseventsd", "pineapple.events")))
        self.assertEqual(
            open(os.path.join(self.root, ".localized"), encoding="utf-8").read().strip(),
            "Pineapple OS",
        )


class TestBFSFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "vol")
        self.vol = BFSVolume(self.root).init()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_put_read(self):
        self.vol.put("Docs/notas.txt", b"conteudo")
        self.assertEqual(self.vol.read("Docs/notas.txt"), b"conteudo")

    def test_case_insensitive_resolution(self):
        self.vol.put("Fotos/TESTE.TXT", b"x")
        self.assertIsNotNone(self.vol.resolve("fotos/teste.txt"))
        self.assertIsNotNone(self.vol.resolve("FOTOS/Teste.Txt"))

    def test_xattr_via_sidecar(self):
        self.vol.put("f.txt", b"dados")
        self.vol.set_xattr("f.txt", "org.pineappleos.autor", b"Pedro")
        self.assertEqual(self.vol.get_xattr("f.txt", "org.pineappleos.autor"),
                         b"Pedro")
        self.assertIn("org.pineappleos.autor", self.vol.list_xattrs("f.txt"))
        self.assertTrue(os.path.exists(os.path.join(self.root, "._f.txt")))
        self.assertTrue(self.vol.del_xattr("f.txt", "org.pineappleos.autor"))
        self.assertIsNone(self.vol.get_xattr("f.txt", "org.pineappleos.autor"))

    def test_finder_invisible(self):
        self.vol.put("secreto.txt", b"segredo")
        self.assertFalse(self.vol.is_invisible("secreto.txt"))
        self.vol.set_finder("secreto.txt", invisible=True)
        self.assertTrue(self.vol.is_invisible("secreto.txt"))
        self.vol.set_finder("secreto.txt", invisible=False)
        self.assertFalse(self.vol.is_invisible("secreto.txt"))

    def test_dotfiles_are_invisible(self):
        self.vol.put(".config", b"segredo")
        self.assertTrue(self.vol.is_invisible(".config"))

    def test_spotlight_index_and_search(self):
        self.vol.put("Docs/projeto.txt", b"Pineapple Spotlight veloz")
        index = SpotlightIndex(self.root)
        total, changed = index.rebuild()
        self.assertEqual((total, changed), (1, 1))
        self.assertEqual(index.search("Spotlight"), ["Docs/projeto.txt"])

    def test_sync_sidecars(self):
        self.vol.put("a.txt", b"a")
        self.vol.put("b.txt", b"b")
        n = self.vol.sync_sidecars()
        self.assertGreaterEqual(n, 2)
        self.assertTrue(os.path.exists(os.path.join(self.root, "._a.txt")))


class TestBFSSparse(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "vol")
        self.vol = BFSVolume(self.root).init()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_sparse_roundtrip(self):
        data = b"A" * 100 + b"\x00" * 9000 + b"B" * 50
        container = sparse.sparse_from_bytes(data)
        # o container é bem menor que os dados (buracos de zeros)
        self.assertLess(len(container), len(data))
        self.assertEqual(sparse.sparse_to_bytes(container), data)

    def test_sparse_zero(self):
        container = sparse.sparse_zero(8192)
        self.assertEqual(sparse.sparse_to_bytes(container), b"\x00" * 8192)
        self.assertEqual(sparse.logical_size(container), 8192)

    def test_expand_arquivo(self):
        self.vol.expand("imagem.img", 1_000_000)
        self.assertEqual(self.vol.size("imagem.img"), 1_000_000)
        self.assertEqual(self.vol.read("imagem.img"), b"\x00" * 1_000_000)

    def test_put_sparse_read(self):
        data = b"HEAD" + b"\x00" * 5000 + b"TAIL"
        self.vol.put_sparse("dados.bin", data)
        self.assertEqual(self.vol.read("dados.bin"), data)
        self.assertEqual(self.vol.size("dados.bin"), len(data))


class TestBFSClone(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "vol")
        self.vol = BFSVolume(self.root).init()
        self.vol.put("origem.bin", b"conteudo-compartilhado")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_clone_e_refcount(self):
        self.vol.clone("origem.bin", "clone.bin")
        self.assertEqual(self.vol.read("clone.bin"), b"conteudo-compartilhado")
        self.assertEqual(self.vol.refcount("clone.bin"), 2)

    def test_unlink_libera_referencia(self):
        self.vol.clone("origem.bin", "clone.bin")
        self.vol.unlink("clone.bin")
        self.assertEqual(self.vol.refcount("origem.bin"), 1)

    def test_write_quebra_clone_cow(self):
        self.vol.clone("origem.bin", "clone.bin")
        self.vol.write("clone.bin", b"modificado")
        self.assertEqual(self.vol.read("origem.bin"), b"conteudo-compartilhado")
        self.assertEqual(self.vol.read("clone.bin"), b"modificado")
        self.assertEqual(self.vol.refcount("origem.bin"), 1)


class TestBFSSnapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "vol")
        self.vol = BFSVolume(self.root).init()
        self.vol.put("arq.txt", b"versao-1")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_snapshot_restore(self):
        self.vol.snapshot("inicio")
        self.assertIn("inicio", self.vol.snapshots())
        self.vol.write("arq.txt", b"versao-2")
        self.assertEqual(self.vol.read("arq.txt"), b"versao-2")
        self.vol.restore("inicio")
        self.assertEqual(self.vol.read("arq.txt"), b"versao-1")

    def test_restore_snapshot_inexistente(self):
        with self.assertRaises(FileNotFoundError):
            self.vol.restore("nao-existe")


class TestBFSChecksum(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "vol")
        self.vol = BFSVolume(self.root).init()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_verify_ok_e_corrupt(self):
        self.vol.put("ok.txt", b"dados")
        results = self.vol.verify()
        self.assertEqual(results["ok.txt"], "ok")
        with open(os.path.join(self.root, "ok.txt"), "ab") as f:
            f.write(b"corrompido")
        results = self.vol.verify()
        self.assertEqual(results["ok.txt"], "corrupt")


class TestBFSArchive(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.vol_dir = os.path.join(self.tmp, "vol")
        self.dest = os.path.join(self.tmp, "extraido")
        self.zip_path = os.path.join(self.tmp, "pacote.zip")
        self.vol = BFSVolume(self.vol_dir).init()
        self.vol.put("Fotos/foto.jpg", b"JPEGBINARIO")
        self.vol.set_xattr("Fotos/foto.jpg", "com.apple.metadata:kMDItemComment",
                           b"da praia")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_pack_tem_pasta_pineapple(self):
        n = archive.pack(self.vol_dir, self.zip_path)
        self.assertGreaterEqual(n, 1)
        self.assertTrue(archive.has_pineapple_folder(self.zip_path))

    def test_unpack_aplica_sidecar(self):
        archive.pack(self.vol_dir, self.zip_path)
        archive.unpack(self.zip_path, self.dest)
        dst_vol = BFSVolume(self.dest)
        # o .zip preserva a pasta de topo (como o ditto --keepParent)
        self.assertEqual(dst_vol.read("vol/Fotos/foto.jpg"), b"JPEGBINARIO")
        self.assertEqual(
            dst_vol.get_xattr("vol/Fotos/foto.jpg",
                              "com.apple.metadata:kMDItemComment"),
            b"da praia",
        )


class TestBFSV2Layers(unittest.TestCase):
    """BFS v2 — pilha de camadas explícita (exFAT ↓ xattrs, finder, snapshots,
    clones, checksums, sparse) declarada no volume.info."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "vol")
        self.vol = BFSVolume(self.root).init()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_volume_info_declara_layers(self):
        info = self.vol.info()
        self.assertEqual(info["version"], 2)
        self.assertEqual(
            tuple(info["layers"]),
            ("xattrs", "finder", "snapshots", "clones", "checksums", "sparse"),
        )

    def test_camadas_expostas_no_volume(self):
        self.assertIsNotNone(self.vol.xattrs)
        self.assertIsNotNone(self.vol.finder)
        self.assertIsNotNone(self.vol.snapshots_layer)
        self.assertIsNotNone(self.vol.clones)
        self.assertIsNotNone(self.vol.checksums)
        self.assertIsNotNone(self.vol.sparse)

    def test_xattr_layer_direto(self):
        self.vol.put("a.txt", b"x")
        self.vol.xattrs.set("a.txt", "org.pineappleos.chave", b"valor")
        self.assertEqual(self.vol.xattrs.get("a.txt", "org.pineappleos.chave"), b"valor")

    def test_finder_metadata_tags_comment_icon(self):
        self.vol.put("foto.jpg", b"jpeg")
        self.vol.finder.set_tags("foto.jpg", ["Red", "Trabalho"])
        self.assertIn("Red", self.vol.finder.tags("foto.jpg"))
        self.vol.finder.add_tag("foto.jpg", "Verde")
        self.assertEqual(self.vol.finder.tags("foto.jpg"), ["Red", "Trabalho", "Verde"])
        self.vol.finder.set_comment("foto.jpg", "da praia")
        self.assertEqual(self.vol.finder.comment("foto.jpg"), "da praia")
        self.assertFalse(self.vol.finder.custom_icon("foto.jpg"))
        self.vol.finder.set_custom_icon("foto.jpg", b"\x89PNG...")
        self.assertTrue(self.vol.finder.custom_icon("foto.jpg"))
        self.assertEqual(self.vol.finder.icon_bytes("foto.jpg"), b"\x89PNG...")

    def test_verify_de_arquivo_expandido(self):
        # regressão do BFS v1: expand registrava checksum de b"" e o verify
        # acusava "corrupt" — agora registra o checksum lógico (zeros).
        self.vol.expand("disco.img", 1_000_000)
        self.assertEqual(self.vol.verify()["disco.img"], "ok")

    def test_clone_layer_independente(self):
        self.vol.put("origem.bin", b"dados")
        self.vol.clones.clone("origem.bin", "clone.bin")
        self.assertEqual(self.vol.clones.refcount("clone.bin"), 2)

    def test_snapshot_layer_independente(self):
        self.vol.put("arq.txt", b"v1")
        self.vol.snapshots_layer.create("estado-a")
        self.assertIn("estado-a", self.vol.snapshots_layer.list())


if __name__ == "__main__":
    unittest.main()