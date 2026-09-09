"""Authored selection admission and mutation checks without external imagery."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from test_rareplanes_calibrate import RarePlanesCalibrationTests, module


class SelectionTests(unittest.TestCase):
    def fixture(self, root):
        prepared = RarePlanesCalibrationTests().prepared_fixture(root)
        document = json.loads(prepared.read_text())
        # A third selected bundle with a distinct test split exercises expansion.
        additional = copy.deepcopy(document["assets"][:4])
        for row in additional:
            row["bundle_id"] = "new_bundle"
            row["id"] = "new_bundle-" + row["product"]
        document["assets"].extend(additional)
        bundles = [{"id": bundle, "split": "train"} for bundle in module.BUNDLES]
        bundles.append({"id": "new_bundle", "split": "test"})
        sources = {}
        for row in document["assets"]:
            folder = {"PAN16": "PAN", "RGB8": "PS-RGB", "MS16": "MS", "RGB16": "MS"}[row["product"]]
            split = "test" if row["bundle_id"] == "new_bundle" else "train"
            row["source_path"] = f"real/{split}/{folder}/{row['bundle_id']}.tif"
            row["source_sha256"] = "a" * 64
            sources[row["source_path"]] = {"path": row["source_path"], "sha256": "a" * 64, "bytes": 12}
        selection = root / "selection.json"
        lock = {"schema_version": 1, "bundles": bundles, "assets": list(sources.values())}
        selection.write_text(json.dumps(lock))
        document["provenance"]["source_lock"] = {"sha256": module.digest_file(selection)}
        prepared.write_text(json.dumps(document))
        return prepared, selection, document, lock

    def test_expanded_matrix_and_legacy_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            prepared, selection, _, _ = self.fixture(Path(tmp))
            _, assets, digest = module.load_prepared(prepared, selection)
            self.assertEqual(len(assets), 12)
            experiment = module.build_encode_experiment(assets, digest)
            self.assertEqual(len(experiment["cases"]), 12)
            self.assertEqual(experiment["protocol"], module.PROTOCOL)
            with self.assertRaises(ValueError):
                module.load_prepared(prepared)

    def test_malformed_selection(self):
        mutations = [
            lambda x: x.update(schema_version=2),
            lambda x: x.update(bundles=[]),
            lambda x: x["bundles"].append(x["bundles"][0]),
            lambda x: x["bundles"][0].update(id="../unsafe"),
            lambda x: x["bundles"][0].update(split="unknown"),
            lambda x: x["assets"].pop(),
            lambda x: x["assets"].append(x["assets"][0]),
            lambda x: x["assets"][0].update(sha256="wrong"),
            lambda x: x["assets"][0].update(path="../source.tif"),
            lambda x: x["assets"].append({"path": "unexpected.tif", "bytes": 1, "sha256": "a" * 64}),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as tmp:
                _, selection, _, lock = self.fixture(Path(tmp))
                mutate(lock)
                selection.write_text(json.dumps(lock))
                with self.assertRaises(ValueError):
                    module.load_selection(selection)

    def test_prepared_membership_and_source_binding(self):
        mutations = [
            lambda x: x["assets"].pop(),
            lambda x: x["assets"].__setitem__(1, x["assets"][0]),
            lambda x: x["assets"][0].update(bundle_id="unexpected"),
            lambda x: x["assets"][0].update(source_sha256="b" * 64),
            lambda x: x["assets"][0].update(source_path=x["assets"][1]["source_path"]),
            lambda x: x["provenance"]["source_lock"].update(sha256="b" * 64),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as tmp:
                prepared, selection, document, _ = self.fixture(Path(tmp))
                mutate(document)
                prepared.write_text(json.dumps(document))
                with self.assertRaises(ValueError):
                    module.load_prepared(prepared, selection)

    def test_selection_tampering_including_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            prepared, selection, _, lock = self.fixture(Path(tmp))
            original = module.digest_file(selection)
            self.assertTrue(module.selection_unchanged(selection, original))
            lock["note"] = "changed after admission"
            selection.write_text(json.dumps(lock))
            self.assertFalse(module.selection_unchanged(selection, original))
            with self.assertRaises(ValueError):
                module.load_prepared(prepared, selection)
