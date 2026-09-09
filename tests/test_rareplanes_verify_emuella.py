"""Authored-data coverage for the independent stream verification journey."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_rareplanes_calibrate as fixtures

spec = importlib.util.spec_from_file_location(
    "verify_emuella", Path(__file__).resolve().parents[1] / "scripts/rareplanes-verify-emuella.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class IndependentVerificationTests(unittest.TestCase):
    def test_six_exports_bind_full_references_and_separate_protocol(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = fixtures.RarePlanesCalibrationTests().prepared_fixture(root)
            _, assets, digest = module.calibration.load_prepared(prepared)
            executable = root / "authored-worker"
            executable.write_bytes(b"authored test double")
            for child in ("inputs", "streams"):
                (root / child).mkdir()
            calls = []

            def export(command, **kwargs):
                self.assertEqual(kwargs["timeout"], 120)
                self.assertEqual(command[1], "--export-lossless")
                request = json.loads(Path(command[2]).read_text())
                calls.append(request)
                self.assertEqual(request["protocol"]["rounds"], 5)
                self.assertEqual(request["case"]["settings"],
                                 {"coding": "classic", "decomposition_levels": 2})
                Path(command[4]).write_bytes(b"authored codestream placeholder")
                Path(command[3]).write_text(json.dumps({
                    "status": "ok", "correctness": {"exact": True},
                    "output_bytes": Path(command[4]).stat().st_size,
                    "diagnostics": {"encode_profile": {"tiles": 1, "decomposition_levels": 2}},
                }))
                return type("Result", (), {"returncode": 0, "stderr": ""})()

            with patch.object(module.subprocess, "run", side_effect=export):
                streams = module.export_streams(assets, digest, executable, root)
            experiment = module.decode_experiment(assets, digest, streams)
            self.assertEqual(len(calls), 6)
            self.assertEqual(len(experiment["cases"]), 6)
            self.assertEqual(module.calibration.PROTOCOL["rounds"], 5)
            for case in experiment["cases"]:
                self.assertEqual(case["input"]["provenance"]["generator"],
                                 "Emuella public lossless encoder")
                self.assertEqual(case["reference"]["sha256"],
                                 case["input"]["provenance"]["prepared_sha256"])
                self.assertEqual(case["image"], case["output"]["image"])
            self.assertEqual(len(module.calibration.unsupported_observations(assets)), 2)

    def test_failed_export_is_not_admitted_as_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = fixtures.RarePlanesCalibrationTests().prepared_fixture(root)
            _, assets, digest = module.calibration.load_prepared(prepared)
            (root / "inputs").mkdir()
            result = type("Result", (), {"returncode": 1, "stderr": "authored failure"})()
            with patch.object(module.subprocess, "run", return_value=result):
                with self.assertRaisesRegex(RuntimeError, "export failed"):
                    module.export_streams(assets, digest, root / "worker", root)
            self.assertEqual(len(list((root / "inputs").glob("*-export.log"))), 1)


if __name__ == "__main__":
    unittest.main()
