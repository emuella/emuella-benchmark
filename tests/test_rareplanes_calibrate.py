"""Offline RarePlanes orchestration checks; no fixture imagery is committed."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/rareplanes-calibrate.py"
spec = importlib.util.spec_from_file_location("rareplanes_calibrate", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class RarePlanesCalibrationTests(unittest.TestCase):
    def prepared_fixture(self, root):
        prepared = root / "prepared"
        prepared.mkdir()
        assets = []
        for bundle in module.BUNDLES:
            bundle_root = prepared / bundle
            bundle_root.mkdir()
            for product, (components, precision, _) in module.PRODUCTS.items():
                image = {"width": 2, "height": 1, "components": components,
                         "precision": precision, "signed": False}
                data = bytes(range(components * (1 if precision <= 8 else 2) * 2))
                relative = f"{bundle}/{product}.raw"
                (prepared / relative).write_bytes(data)
                assets.append({
                    "id": f"{bundle}-{product}", "bundle_id": bundle, "product": product,
                    "path": relative, "sha256": digest(data), "bytes": len(data), "image": image,
                    "source_path": f"source/{bundle}.tif", "source_sha256": digest(product.encode()),
                    "band_indices": list(range(1, components + 1)),
                    "statistics": [{"checked": True} for _ in range(components)],
                })
        record = {"schema_version": 1, "provenance": {"recipe": "test"}, "assets": assets}
        path = prepared / "prepared.json"
        path.write_text(json.dumps(record))
        return path

    def test_prepared_metadata_becomes_six_explicit_experiments(self):
        with tempfile.TemporaryDirectory() as tmp:
            prepared = self.prepared_fixture(Path(tmp))
            _, assets, prepared_sha256 = module.load_prepared(prepared)
            encode = module.build_encode_experiment(assets, prepared_sha256)
            self.assertEqual(len(encode["cases"]), 6)
            self.assertEqual(encode["protocol"], module.PROTOCOL)
            for case in encode["cases"]:
                self.assertEqual(case["settings"], {"coding": "classic", "decomposition_levels": 2})
                self.assertEqual(case["threads"], 1)
                self.assertTrue(Path(case["input"]["path"]).is_absolute())
                self.assertNotIn("source_path", case["input"]["provenance"])

            streams = {
                asset["id"]: {
                    "path": Path(tmp) / (asset["id"] + ".j2k"), "sha256": digest(asset["id"].encode()),
                    "generator_sha256": digest(b"opj_compress"), "arguments_sha256": digest(b"arguments"),
                }
                for asset in assets if asset["supported"]
            }
            decode = module.build_decode_experiment(assets, prepared_sha256, streams)
            self.assertEqual(len(decode["cases"]), 6)
            for case in decode["cases"]:
                self.assertEqual(case["settings"], {"coding": "classic"})
                self.assertEqual(case["reference"]["sha256"], case["input"]["provenance"]["prepared_sha256"])
            unsupported = module.unsupported_observations(assets)
            self.assertEqual(len(unsupported), 2)
            self.assertTrue(all(item["disposition"] == "not_submitted" for item in unsupported))

    def test_tamper_is_rejected_before_experiment_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            prepared = self.prepared_fixture(Path(tmp))
            record = json.loads(prepared.read_text())
            target = prepared.parent / record["assets"][0]["path"]
            target.write_bytes(target.read_bytes()[:-1] + b"x")
            with self.assertRaisesRegex(ValueError, "integrity mismatch"):
                module.load_prepared(prepared)

    def test_output_is_a_normalised_new_direct_store_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp).resolve()
            self.assertEqual(module.new_store_child(store, store / "run-a"), store / "run-a")
            for requested in (store / "nested/run", store / "nested/../run", store / "../escaped"):
                with self.subTest(requested=requested), self.assertRaisesRegex(ValueError, "direct child|parent traversal"):
                    module.new_store_child(store, requested)

    def test_summary_keeps_failed_batches_without_store_paths(self):
        store = Path("/approved/rareplanes")
        case = {
            "id": f"{module.BUNDLES[0]}-PAN16-encode",
            "input": {"path": str(store / "prepared/PAN16.raw"), "sha256": digest(b"input")},
            "reference": None,
            "image": {"width": 2, "height": 1, "components": 1, "precision": 16, "signed": False},
            "operation": "encode", "settings": {"coding": "classic", "decomposition_levels": 2},
            "threads": 1,
        }
        response = {
            "samples_ns": [100], "output_bytes": 2, "peak_rss_bytes": 4096,
            "correctness": {"exact": True},
            "diagnostics": {"encode_profile": {"coding": "classic", "mct": "none"}},
        }
        run = {
            "run_id": "run-1", "_run_sha256": digest(b"run"),
            "experiment": {"cases": [case], "protocol": {"rounds": 2}},
            "batches": [
                {"case_id": case["id"], "round": 0, "status": "ok", "response": response},
                {"case_id": case["id"], "round": 1, "status": "failed",
                 "detail": f"could not read {store}/prepared/PAN16.raw", "response": None},
            ],
            "worker": {"definition": {"implementation": "worker", "source_identity": "source@revision"},
                       "executable_sha256": digest(b"worker"),
                       "artefact_sha256": {"/local/build/provenance.json": digest(b"build")}},
            "harness_version": "0.1.0", "harness_sha256": digest(b"harness"),
            "machine": {"hostname": "private", "os": "linux", "architecture": "x86_64"},
        }
        summary = module.summarise_run(run, {f"{module.BUNDLES[0]}-PAN16": 4}, (store,))
        serialised = json.dumps(summary)
        observation = summary["observations"][0]
        self.assertEqual(observation["statuses"], {"failed": 1, "ok": 1})
        self.assertEqual(observation["disposition"], "incomplete_or_failed")
        self.assertIn("<authorised-store>", observation["non_success"][0]["detail"])
        self.assertNotIn(str(store), serialised)
        self.assertNotIn("private", serialised)
        self.assertEqual(observation["compression_ratio_raw_over_encoded"], 2.0)
        self.assertEqual(observation["sample_values_per_second"], 20_000_000.0)
        self.assertEqual(observation["encode_profiles"], [{"coding": "classic", "mct": "none"}])


if __name__ == "__main__":
    unittest.main()
