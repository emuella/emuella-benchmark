"""Build qualification admission and arithmetic using authored metadata only."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("qualify_worker_builds",
    Path(__file__).resolve().parents[1] / "scripts/qualify-worker-builds.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def assets(bundle="acquisition"):
    return [{"id": f"{bundle}-{product}", "bundle_id": bundle, "product": product}
            for product in module.calibration.PRODUCTS]


def matrix():
    result = {}
    for name, (profile, simd) in module.VARIANTS.items():
        result[name] = {"schema_version": 1, "emuella_revision": module.PIN, "emuella_tree": "a" * 40,
            "profile": profile, "requested_build": {"profile": profile, "simd": simd, "default_features": True},
            "source_sha256": {"worker.rs": "a" * 64}, "resolved_worker_lock_sha256": "b" * 64,
            "rustc": "test", "cargo": "test", "cc": "test", "build_environment": {},
            "build_observations": {"cargo_config_files": [], "compiler_artefacts": [
                {"target": {"name": "emuella_j2k"}, "features": ["parallel"] + (["simd"] if simd else []), "fresh": False}]}}
    return result


def run(times, failed=()):
    cases, batches = [], []
    for case_id, values in times.items():
        cases.append({"id": case_id, "image": {"width": 10 if "PAN" in case_id else 100, "height": 1, "components": 1},
                      "input": {"provenance": {"prepared_asset_id": case_id.removesuffix("-encode")}}})
        for round_number, ns in enumerate(values):
            batches.append({"case_id": case_id, "round": round_number,
                "status": "unsupported" if case_id in failed else "ok",
                "response": {"correctness": {"exact": True}, "samples_ns": [ns]}})
    return {"experiment": {"cases": cases, "protocol": {"rounds": 5, "samples_per_batch": 1}}, "batches": batches}


def comparison(ids):
    return {"verdict": "invalid", "reason": "unsupported coverage retained", "cases": [
        {"case_id": case_id, "verdict": "inconclusive", "relative_interval_99": [-0.9, 1.0]} for case_id in ids]}


class WorkerBuildQualificationTests(unittest.TestCase):
    def test_complete_bundle_selection_preserves_all_products_in_selected_order(self):
        selected = module.select_bundles(assets("one") + assets("two"), ["two", "one"])
        self.assertEqual([a["id"] for a in selected], [a["id"] for a in assets("two") + assets("one")])
        for group, choices in ((assets()[:-1], ["acquisition"]), (assets(), ["unknown"]),
                               (assets(), ["acquisition", "acquisition"]), (assets(), [])):
            with self.subTest(choices=choices), self.assertRaises(ValueError):
                module.select_bundles(group, choices)

    def test_matrix_requires_actual_features_and_identical_sources(self):
        module.validate_matrix(matrix())
        for mutate in (lambda b: b.pop("perf"),
                       lambda b: b["perf"].update(emuella_revision="c" * 40),
                       lambda b: b["perf"]["source_sha256"].update({"worker.rs": "d" * 64}),
                       lambda b: b["perf-simd"]["build_observations"]["compiler_artefacts"][0].update(features=["parallel"]),
                       lambda b: b["perf"]["build_observations"]["compiler_artefacts"][0].update(fresh=True),
                       lambda b: b["perf"].update(requested_build={"profile": "release", "simd": False, "default_features": True})):
            builds = matrix()
            mutate(builds)
            with self.assertRaises(ValueError):
                module.validate_matrix(builds)

    def test_overrides_remain_outside_frozen_qualification(self):
        builds = matrix()
        for build in builds.values():
            build["build_environment"] = {"RUSTFLAGS": "-C target-cpu=native"}
        with self.assertRaisesRegex(ValueError, "excludes"):
            module.validate_matrix(builds)
        builds = matrix()
        builds["release"]["build_observations"]["cargo_config_files"] = [{"path": "config", "sha256": "a" * 64}]
        with self.assertRaisesRegex(ValueError, "configuration"):
            module.validate_matrix(builds)

    def test_common_stream_hash_and_no_mct_arguments_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            stream = store / "common.j2k"
            stream.write_bytes(b"authored codestream identity fixture")
            asset = {**assets()[0], "image": {"width": 2, "height": 3, "components": 1, "precision": 16}}
            arguments = ["-i", str(store / "planar.rawl"), "-o", str(stream), "-F", "2,3,1,16,u",
                         "-n", "3", "-t", "2,3", "-p", "LRCP", "-r", "1", "-mct", "0", "-threads", "1"]
            row = {"path": str(stream), "bytes": stream.stat().st_size, "sha256": module.calibration.digest_file(stream),
                   "arguments": arguments, "generator_sha256": "a" * 64,
                   "arguments_sha256": hashlib.sha256(json.dumps(arguments, separators=(",", ":")).encode()).hexdigest()}
            document = {"schema_version": 1, "generator": "OpenJPEG opj_compress", "streams": {asset["id"]: row}}
            path = store / "common.json"
            path.write_text(json.dumps(document))
            self.assertEqual(module.load_common(path, [asset], store)[asset["id"]]["path"], stream)
            arguments[arguments.index("-mct") + 1] = "1"
            row["arguments_sha256"] = hashlib.sha256(json.dumps(arguments, separators=(",", ":")).encode()).hexdigest()
            path.write_text(json.dumps(document))
            with self.assertRaisesRegex(ValueError, "frozen"):
                module.load_common(path, [asset], store)
            stream.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "integrity"):
                module.load_common(path, [asset], store)

    def test_common_paths_cannot_escape_store_or_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            source = store / "source"
            source.write_bytes(b"authored")
            linked = store / "link"
            linked.symlink_to(source)
            for path in (linked, store.parent / "outside"):
                with self.assertRaises(ValueError):
                    module.store_file(store, path)

    def test_hash_mismatch_and_missing_baseline_are_explicit(self):
        rows = assets()
        exports = {name: {row["id"]: {"sha256": "a" * 64} for row in rows} for name in module.VARIANTS}
        exports["perf"][rows[0]["id"]]["sha256"] = "b" * 64
        del exports["release"][rows[1]["id"]]
        del exports["perf-simd"][rows[2]["id"]]
        observed = module.compare_streams(rows, exports)
        self.assertEqual(observed[0]["variants"]["perf"], "hash_mismatch")
        self.assertEqual(observed[1]["variants"]["perf"], "baseline_missing")
        self.assertEqual(observed[2]["variants"]["perf-simd"], "candidate_missing")

    def test_geometric_speedup_and_total_samples_over_time_use_distinct_weights(self):
        left = run({"a-PAN16-encode": [100] * 5, "a-MS16-encode": [1000] * 5})
        right = run({"a-PAN16-encode": [50] * 5, "a-MS16-encode": [1000] * 5})
        ids = {c["id"] for c in left["experiment"]["cases"]}
        result = module.aggregate_pair(left, right, comparison(ids), ids)
        self.assertAlmostEqual(result["equally_weighted_geometric_mean_speedup"], 2 ** 0.5)
        self.assertEqual(result["totals"]["baseline"]["component_samples"], 550)
        self.assertEqual(result["totals"]["baseline"]["time_ns"], 5500)
        self.assertEqual(result["totals"]["candidate"]["time_ns"], 5250)
        self.assertEqual(result["harness_verdict"], "invalid")
        self.assertEqual(result["cases"][0]["paired_round_speedups"], [2] * 5)

    def test_newly_supported_incomplete_and_unverified_cases_never_count_as_speed(self):
        timings = {"a-PAN16-encode": [100] * 5, "a-MS16-encode": [100] * 5}
        left, right = run(timings, failed={"a-MS16-encode"}), run(timings)
        ids = set(timings)
        result = module.aggregate_pair(left, right, comparison(ids), ids)
        self.assertEqual(result["same_success_cases"], 1)
        self.assertEqual(result["cases"][1]["baseline_statuses"], {"unsupported": 5})
        self.assertNotIn("geometric_mean_speedup", result["cases"][1])
        right["batches"].pop(0)
        self.assertEqual(module.aggregate_pair(left, right, comparison(ids), ids)["same_success_cases"], 0)
        self.assertEqual(module.aggregate_pair(run(timings), run(timings), comparison(ids), set())["same_success_cases"], 0)

    def test_verification_uses_admitted_five_round_protocol_and_native_harness_argv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset = {**assets()[0], "supported": True, "raw_path": root / "reference.raw",
                     "sha256": "a" * 64, "source_sha256": "b" * 64,
                     "image": {"width": 2, "height": 1, "components": 1, "precision": 16, "signed": False}}
            streams = {asset["id"]: {"path": root / "stream.j2k", "sha256": "c" * 64,
                       "generator_sha256": "d" * 64, "arguments_sha256": "e" * 64}}
            destination = root / "verification"
            failures = []
            with mock.patch.object(module.subprocess, "run", return_value=mock.Mock(returncode=4)) as command:
                successful = module.verify_decode(root / "benchmark", [asset], "f" * 64, streams,
                                                  root / "worker.json", destination, failures)
            experiment_path = destination.with_suffix(".json")
            experiment = json.loads(experiment_path.read_text())
            self.assertEqual(experiment["protocol"], module.calibration.PROTOCOL)
            self.assertGreaterEqual(experiment["protocol"]["rounds"], 5)
            self.assertEqual(experiment["protocol"]["samples_per_batch"], 1)
            self.assertEqual(experiment["cases"][0]["threads"], 1)
            self.assertEqual(command.call_args.args[0], [str(root / "benchmark"), "run", str(experiment_path),
                                                       str(root / "worker.json"), str(destination)])
            self.assertEqual(successful, set())
            self.assertEqual(failures[0]["disposition"], "incomplete_verification")
            with self.assertRaises(FileExistsError):
                module.verify_decode(root / "benchmark", [asset], "f" * 64, streams,
                                     root / "worker.json", destination, failures)

    def test_rounds_must_be_complete_exact_and_nonzero(self):
        original = run({"a-PAN16-encode": [100] * 5})
        for mutation in (lambda r: r["batches"][1].update(round=0),
                         lambda r: r["batches"][0]["response"]["correctness"].update(exact=False),
                         lambda r: r["batches"][0]["response"].update(samples_ns=[0])):
            altered = copy.deepcopy(original)
            mutation(altered)
            self.assertIsNone(module.exact_batches(altered, "a-PAN16-encode"))


if __name__ == "__main__":
    unittest.main()
