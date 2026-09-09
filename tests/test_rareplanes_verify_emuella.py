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
    def test_eight_exports_bind_full_references_and_separate_protocol(self):
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
                    "schema_version": 1, "request_id": request["request_id"],
                    "applied_case": request["case"], "boundary": "codec_operation",
                    "samples_ns": [123], "status": "ok", "correctness": {"exact": True},
                    "output_bytes": Path(command[4]).stat().st_size,
                    "diagnostics": {"encode_profile": {
                        "tiles": 1, "decomposition_levels": 2, "coding": "classic",
                        "progression_order": "lrcp", "quality_layers": 1,
                        "multiple_component_transform": (
                            "reversible_colour_transform" if request["case"]["image"]["components"] == 3
                            else "none"),
                    }},
                }))
                return type("Result", (), {"returncode": 0, "stderr": ""})()

            with patch.object(module.subprocess, "run", side_effect=export):
                streams = module.export_streams(assets, digest, executable, root)
            self.assertNotIn(str(root), json.dumps([
                value["verification_journey_observations"] for value in streams.values()]))
            response_path = next((root / "inputs").glob("*-response.json"))
            response = json.loads(response_path.read_text())
            request = next(c for c in calls if c["request_id"] == response["request_id"])
            response["applied_case"]["threads"] = 2
            with self.assertRaisesRegex(RuntimeError, "differs from requested"):
                module.validate_export_response(request, response)
            experiment = module.decode_experiment(assets, digest, streams)
            self.assertEqual(len(calls), 8)
            self.assertEqual(len(experiment["cases"]), 8)
            self.assertEqual(module.calibration.PROTOCOL["rounds"], 5)
            for case in experiment["cases"]:
                self.assertEqual(case["input"]["provenance"]["generator"],
                                 "Emuella public lossless encoder")
                self.assertEqual(case["reference"]["sha256"],
                                 case["input"]["provenance"]["prepared_sha256"])
                self.assertEqual(case["image"], case["output"]["image"])
            self.assertEqual(len(module.calibration.unsupported_observations(assets)), 0)

    def test_empty_expanded_exports_write_summary_and_recheck_selection(self):
        from test_rareplanes_selection import SelectionTests
        for tamper in (False, True):
            with self.subTest(tamper=tamper), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                prepared, selection, _, lock = SelectionTests().fixture(root)
                selection_digest = module.calibration.digest_file(selection)
                executable = root / "worker"
                executable.write_bytes(b"authored")
                for name in ("emuella", "openjpeg"):
                    (root / (name + "-worker.json")).write_text(json.dumps({"executable": str(executable)}))
                output = root / "result"
                argv = ["verify", "--benchmark", str(executable), "--workers", str(root),
                        "--build-provenance", str(executable), "--prepared", str(prepared),
                        "--selection", str(selection), "--store", str(root),
                        "--output", str(output), "--opj-dump", str(executable)]

                def exports(assets, digest, worker, destination, failures):
                    self.assertEqual(len(assets), 12)
                    failures.extend({"name": a["id"], "stderr": "authored unsupported"} for a in assets)
                    if tamper:
                        lock["note"] = "mutated during export"
                        selection.write_text(json.dumps(lock))
                    return {}

                with patch.object(module.sys, "argv", argv), \
                        patch.object(module.calibration, "git", side_effect=lambda *args: "" if args[0] == "status" else "revision"), \
                        patch.object(module.calibration, "public_build_provenance", return_value={}), \
                        patch.object(module, "export_streams", side_effect=exports), \
                        patch.object(module.calibration, "invoke_run") as run, \
                        patch("builtins.print"):
                    self.assertEqual(module.main(), 4)
                    run.assert_not_called()
                summary = json.loads((output / "rareplanes-emuella-verification-summary.json").read_text())
                self.assertFalse(summary["complete"])
                self.assertEqual(summary["runs"], [])
                self.assertEqual(summary["selection_sha256"], selection_digest)
                self.assertEqual(any(f["name"] == "identity" for f in summary["failures"]), tamper)

    def test_failed_exports_continue_and_retain_identities(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = fixtures.RarePlanesCalibrationTests().prepared_fixture(root)
            _, assets, digest = module.calibration.load_prepared(prepared)
            executable = root / "worker"
            executable.write_bytes(b"authored")
            for child in ("inputs", "streams"):
                (root / child).mkdir()
            calls = []

            def export(command, **kwargs):
                request = json.loads(Path(command[2]).read_text())
                calls.append(request)
                if len(calls) == 2:
                    raise module.subprocess.TimeoutExpired(command, 120)
                Path(command[3]).write_text(json.dumps({
                    "schema_version": 1, "request_id": request["request_id"],
                    "applied_case": request["case"], "status": "unsupported"}))
                return type("Result", (), {"returncode": 4, "stderr": "authored guard"})()

            failures = []
            with patch.object(module.subprocess, "run", side_effect=export):
                streams = module.export_streams(assets, digest, executable, root, failures)
            self.assertEqual(streams, {})
            self.assertEqual(len(calls), len(assets))
            self.assertEqual(len(failures), len(assets))
            self.assertEqual(failures[0]["disposition"], "unsupported")
            self.assertEqual(failures[1]["disposition"], "export_failed")
            for failure in failures:
                self.assertIn("request", failure["records_sha256"])
                self.assertIn("log", failure["records_sha256"])

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
