"""Portable conversion and containment checks; no corpus or network required."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("prepare", Path(__file__).resolve().parents[1] / "scripts/prepare-generated.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PreparationTests(unittest.TestCase):
    def test_preserves_first_whitespace_pixel(self):
        raw, image = module.read_pnm(b"P5\n# generated\n2 1\n255\n\x0a\x20")
        self.assertEqual(raw, b"\x0a\x20")
        self.assertEqual(image["width"], 2)

    def test_u16_endian_and_components(self):
        raw, image = module.read_pnm(b"P6\n1 1\n65535\n\x12\x34\x00\xff\xff\x00")
        self.assertEqual(raw, b"\x34\x12\xff\x00\x00\xff")
        self.assertEqual(image["components"], 3)

    def test_rejects_malformed_rasters(self):
        for data in (b"P5\n0 1\n255\n", b"P5\n1 1\n255\n", b"P5\n1 1\n255\nxx", b"P5\n1 1\n31\nx", b"P5\n# unterminated"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                module.read_pnm(data)

    def test_symlink_and_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "file").write_bytes(b"x")
            (root / "link").symlink_to(root / "file")
            for path in ("link", "../file", str(root / "file")):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    module.regular_file(root, path)

    def test_catalogue_tamper_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "catalogue"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            manifests = root / "manifests/common"
            manifests.mkdir(parents=True)
            assets = root / "generated/common/generated-core"
            assets.mkdir(parents=True)
            contents = b"P5\n1 1\n255\nx"
            text = '\n'.join((
                'id = "common/generated-core"', 'version = "1"',
                'review_state = "locked"', '[license]', 'expression = "Apache-2.0"',
                '[rights]', 'access = "permitted"', 'modification = "permitted"',
                'publish_benchmarks = "permitted"', '[materialization]',
                'directory = "generated/common/generated-core"',
            )) + '\n'
            for name in module.FILES:
                (assets / name).write_bytes(contents)
                text += f'[[assets]]\npath = "{name}"\nbytes = {len(contents)}\nsha256 = "{module.digest(contents)}"\n'
            (manifests / "generated-core.toml").write_text(text)
            def commit():
                subprocess.run(["git", "-C", str(root), "add", "."], check=True)
                subprocess.run(["git", "-C", str(root), "-c", "user.name=Test",
                                "-c", "user.email=test@example.invalid", "commit", "-qm", "Fixture"], check=True)
            commit()
            output = Path(tmp) / "valid"
            self.assertTrue(module.prepare(root, output).is_file())
            (assets / module.FILES[0]).write_bytes(contents[:-1] + b"y")
            commit()
            bad_output = Path(tmp) / "tampered"
            with self.assertRaisesRegex(ValueError, "integrity mismatch"):
                module.prepare(root, bad_output)
            self.assertFalse(bad_output.exists())


if __name__ == "__main__":
    unittest.main()
