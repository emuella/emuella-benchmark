"""Authored synthetic checks; no external tools or protected inputs are needed."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/scout-satellite-compression.py"
spec = importlib.util.spec_from_file_location("satellite_scout", SCRIPT)
scout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scout)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def marker(code, body):
    return bytes([255, code]) + struct.pack(">H", len(body) + 2) + body


def codestream(image, profile, tile_header=b"", style=None):
    siz = struct.pack(">H8IH", 0, image["width"], image["height"], 0, 0,
                      image["width"], image["height"], 0, 0, image["components"])
    siz += bytes([image["precision"] - 1, 1, 1]) * image["components"]
    cod = bytes([0, 0, 0, 1, profile["mct"], profile["depth"],
                 *[x.bit_length() - 3 for x in profile["block"]],
                 profile["style"] if style is None else style, 1])
    qcd = bytes([64]) + bytes(1 + 3 * profile["depth"])
    payload = b"authored synthetic entropy placeholder"
    sot = marker(0x90, struct.pack(">HIBB", 0, 14 + len(tile_header) + len(payload), 0, 1))
    return (b"\xff\x4f" + marker(0x51, siz) + marker(0x52, cod) + marker(0x5c, qcd)
            + sot + tile_header + b"\xff\x93" + payload + b"\xff\xd9")


class ScoutTests(unittest.TestCase):
    def fixture(self, root, split="train"):
        prepdir = root / "prepared"
        prepdir.mkdir()
        sources = root / "sources.json"
        sources.write_text(json.dumps({"schema_version": 1,
            "bundles": [{"id": bundle, "split": split} for bundle in (scout.DEVELOPMENT, scout.HOLDOUT)],
            "assets": [{"path": f"real/{split}/{folder}/{bundle}.tif", "sha256": digest(f"{bundle}-{folder}".encode()), "bytes": 1}
                       for bundle in (scout.DEVELOPMENT, scout.HOLDOUT) for folder in ("PAN", "PS-RGB", "MS")]}))
        provenance = {"source_lock": {"sha256": scout.sha(sources)}, "recipe": {"sha256": digest(b"recipe")}}
        assets = []
        for product, (components, precision) in scout.PRODUCTS.items():
            image = {"width": 4, "height": 2, "components": components, "precision": precision, "signed": False}
            bpp = precision // 8
            raw = bytes(range(8 * components * bpp))
            planar = b"".join(raw[(pixel * components + component) * bpp:(pixel * components + component + 1) * bpp]
                              for component in range(components) for pixel in range(8))
            (prepdir / f"{product}.raw").write_bytes(raw)
            (root / f"{product}.rawl").write_bytes(planar)
            folder = {"PAN16": "PAN", "RGB8": "PS-RGB", "MS16": "MS", "RGB16": "MS"}[product]
            assets.append({"id": f"{scout.DEVELOPMENT}-{product}", "product": product,
                           "bundle_id": scout.DEVELOPMENT, "path": f"{product}.raw", "sha256": digest(raw),
                           "bytes": len(raw), "source_path": f"real/{split}/{folder}/{scout.DEVELOPMENT}.tif",
                           "source_sha256": digest(f"{scout.DEVELOPMENT}-{folder}".encode()), "image": image})
        prepared = prepdir / "prepared.json"
        prepared.write_text(json.dumps({"schema_version": 1, "assets": assets, "provenance": provenance}))
        streams = {}
        for asset in assets:
            planar = root / f"{asset['product']}.rawl"
            args = ["-i", str(planar), "-F", scout.format_raw(asset["image"])]
            streams[asset["id"]] = {"arguments": args,
                "arguments_sha256": digest(json.dumps(args, separators=(",", ":")).encode()),
                "planar_sha256": scout.sha(planar), "preparation_record": {
                    "schema_version": 1, "asset_id": asset["id"], "bytes": asset["bytes"],
                    "path": planar.name, "sha256": scout.sha(planar), "source_sha256": asset["sha256"],
                    "layout": "packed component-planar little-endian unsigned",
                    "prepared_sha256": scout.sha(prepared), "provenance": provenance}}
        common = root / "common.json"
        common.write_text(json.dumps({"schema_version": 1, "streams": streams}))
        return prepared, common, sources

    def test_selection_binds_all_four_products_and_sample_conversion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = scout.load_inputs(root, *self.fixture(root), scout.DEVELOPMENT, list(scout.PRODUCTS))
            self.assertEqual([a["product"] for a in selected], list(scout.PRODUCTS))
            self.assertEqual(selected[2]["image"]["components"], 8)

    def test_mismatched_planar_bytes_rejected_even_with_updated_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared, common, sources = self.fixture(root)
            path = root / "MS16.rawl"
            path.write_bytes(bytes(reversed(path.read_bytes())))
            data = json.loads(common.read_text())
            entry = data["streams"][f"{scout.DEVELOPMENT}-MS16"]
            entry["planar_sha256"] = entry["preparation_record"]["sha256"] = scout.sha(path)
            common.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "differs from prepared samples"):
                scout.load_inputs(root, prepared, common, sources, scout.DEVELOPMENT, ["MS16"])

    def test_wrong_prepared_hash_and_duplicate_selection_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self.fixture(root)
            with self.assertRaises(ValueError):
                scout.load_inputs(root, *inputs, scout.DEVELOPMENT, ["MS16", "MS16"])
            data = json.loads(inputs[1].read_text())
            data["streams"][f"{scout.DEVELOPMENT}-MS16"]["preparation_record"]["prepared_sha256"] = "0" * 64
            inputs[1].write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "lineage"):
                scout.load_inputs(root, *inputs, scout.DEVELOPMENT, ["MS16"])

    def test_profiles_and_arguments_keep_baseline_fixed(self):
        asset = {"planar_path": "/synthetic/input.rawl", "image": {"width": 100, "height": 80, "components": 8, "precision": 16}}
        for profile in scout.profiles(list(range(2, 7)), ["baseline"]):
            args = scout.encode_args(Path("opj_compress"), asset, profile, Path("out.j2k"))
            options = dict(zip(args[1::2], args[2::2]))
            self.assertEqual(options["-n"], str(profile["depth"] + 1))
            self.assertEqual({k: options[k] for k in ["-t", "-p", "-r", "-mct", "-b", "-M", "-threads"]},
                             {"-t": "100,80", "-p": "LRCP", "-r": "1", "-mct": "0", "-b": "64,64", "-M": "0", "-threads": "1"})
        trials = scout.profiles([3], list(scout.TRIALS))
        self.assertEqual(len(trials), 5)
        self.assertEqual(trials[1]["mct"], 1)
        self.assertEqual(trials[2]["block"], [32, 32])
        self.assertEqual(trials[3]["block"], [32, 64])
        self.assertEqual(trials[4]["style"], 1)
        for depths in ([1], [7], [3, 3], []):
            with self.assertRaises(ValueError):
                scout.profiles(depths, ["baseline"])

    def test_output_safety_preserves_existing_paths_and_rejects_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            existing = root / "existing"
            existing.mkdir()
            sentinel = existing / "keep"
            sentinel.write_bytes(b"protected")
            for output in (existing, root.parent / "escape", root / "missing" / "nested", root):
                with self.assertRaises(ValueError):
                    scout.new_output(root, output)
            link = root / "link"
            link.symlink_to(existing, target_is_directory=True)
            with self.assertRaises(ValueError):
                scout.new_output(root, link)
            self.assertEqual(sentinel.read_bytes(), b"protected")
            self.assertEqual(scout.new_output(root, root / "fresh"), root / "fresh")

    def test_header_reader_checks_all_depths_and_named_trials(self):
        image = {"width": 128, "height": 128, "precision": 16, "components": 8}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.j2k"
            for profile in scout.profiles(list(range(2, 7)), list(scout.TRIALS)):
                path.write_bytes(codestream(image, profile))
                self.assertEqual(scout.inspect_codestream(path, image, profile)["depth"], profile["depth"])

    def test_header_reader_rejects_overrides_truncation_and_style_mismatch(self):
        image = {"width": 128, "height": 128, "precision": 16, "components": 8}
        profile = scout.profiles([3], ["baseline"])[0]
        valid = codestream(image, profile)
        bad = [valid[:-1], valid + b"extra", valid[:10], codestream(image, profile, style=1),
               codestream(image, profile, tile_header=marker(0x52, b"override")),
               valid[:2] + marker(0x53, b"override") + valid[2:]]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.j2k"
            for data in bad:
                path.write_bytes(data)
                with self.assertRaises(ValueError):
                    scout.inspect_codestream(path, image, profile)

    def test_full_byte_verification_rejects_trailing_truncated_and_corrupt_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "decoded.rawl"
            self.assertFalse(scout.byte_result(path, 4, digest(b"good"))["exact"])
            for data in (b"good!", b"goo", b"bad!"):
                path.write_bytes(data)
                result = scout.byte_result(path, 4, digest(b"good"))
                self.assertFalse(result["exact"])
                self.assertEqual(result["bytes"], len(data))
            path.write_bytes(b"good")
            self.assertTrue(scout.byte_result(path, 4, digest(b"good"))["exact"])

    def test_process_failure_and_timeout_are_retained_with_timing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for number, effect in enumerate((subprocess.CompletedProcess([], 9), subprocess.TimeoutExpired([], 1), OSError())):
                with patch.object(scout.subprocess, "run") as run, patch.object(scout.time, "perf_counter_ns", side_effect=[100, 250]):
                    if isinstance(effect, Exception):
                        run.side_effect = effect
                    else:
                        run.return_value = effect
                    result = scout.process(["synthetic"], root / str(number), 1)
                self.assertNotEqual(result["status"], "ok")
                self.assertEqual(result["wall_ns"], 150)
                self.assertEqual(result["measurement_boundary"], "application_journey")
                self.assertTrue((root / str(number)).exists())

    def test_failed_encode_keeps_partial_bytes_and_skips_decode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            asset = scout.load_inputs(root, *self.fixture(root), scout.DEVELOPMENT, ["MS16"])[0]
            def failed(command, log, timeout, identity):
                Path(command[command.index("-o") + 1]).write_bytes(b"partial")
                return {"status": "process_failed", "wall_ns": 99, "exit_code": 1}
            with patch.object(scout, "checked_process", side_effect=failed):
                result = scout.observe(asset, scout.profiles([3], ["baseline"])[0], 0,
                                       {"compress": Path("compress"), "decompress": Path("decompress")}, root, 1, {"compress": {}, "decompress": {}})
            self.assertEqual(result["codestream"]["bytes"], 7)
            self.assertEqual(result["decode"]["status"], "not_attempted")
            self.assertFalse(result["exact"])
            self.assertEqual(len(list(root.glob("*/observation.json"))), 1)

    def test_exact_decode_cannot_hide_wrong_coding_style(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            asset = scout.load_inputs(root, *self.fixture(root), scout.DEVELOPMENT, ["MS16"])[0]
            profile = scout.profiles([3], ["baseline"])[0]
            def fake(command, log, timeout, identity):
                destination = Path(command[command.index("-o") + 1])
                destination.write_bytes(codestream(asset["image"], profile, style=1) if destination.suffix == ".j2k"
                                        else Path(asset["planar_path"]).read_bytes())
                return {"status": "ok", "wall_ns": 99, "exit_code": 0}
            with patch.object(scout, "checked_process", side_effect=fake):
                result = scout.observe(asset, profile, 0, {"compress": Path("compress"), "decompress": Path("decompress")}, root, 1, {"compress": {}, "decompress": {}})
            self.assertTrue(result["exact"])
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["profile_status"], "invalid_structure")
            self.assertEqual(result["profile_failure_reason"], "COD differs from reversible fixed profile")

    def test_product_lineage_rejects_other_locked_acquisition_folder_and_split(self):
        for bundle, folder, split in ((scout.HOLDOUT, "MS", "train"),
                                       (scout.DEVELOPMENT, "PAN", "train"),
                                       (scout.DEVELOPMENT, "MS", "test")):
            with self.subTest(bundle=bundle, folder=folder, split=split), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                prepared, common, sources = self.fixture(root)
                document = json.loads(prepared.read_text())
                asset = next(a for a in document["assets"] if a["product"] == "MS16")
                asset["source_path"] = f"real/{split}/{folder}/{bundle}.tif"
                asset["source_sha256"] = digest(f"{bundle}-{folder}".encode())
                prepared.write_text(json.dumps(document))
                streams = json.loads(common.read_text())
                for entry in streams["streams"].values():
                    entry["preparation_record"]["prepared_sha256"] = scout.sha(prepared)
                common.write_text(json.dumps(streams))
                with self.assertRaisesRegex(ValueError, "selected acquisition, split or product"):
                    scout.load_inputs(root, prepared, common, sources, scout.DEVELOPMENT, ["MS16"])

    def test_source_lock_schema_selection_and_declared_test_split(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared, common, sources = self.fixture(root, split="test")
            assets = scout.load_inputs(root, prepared, common, sources, scout.DEVELOPMENT, ["PAN16"])
            self.assertIn("real/test/PAN/", assets[0]["source_path"])
            original = json.loads(sources.read_text())
            for mutation in ("schema", "selection", "matrix"):
                document = copy.deepcopy(original)
                if mutation == "schema":
                    document["schema_version"] = 99
                elif mutation == "selection":
                    document["bundles"] = []
                else:
                    document["assets"].pop()
                sources.write_text(json.dumps(document))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    scout.load_inputs(root, prepared, common, sources, scout.DEVELOPMENT, ["PAN16"])

    def test_runtime_dependency_symlink_switch_is_detected_with_original_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tool, first, second, loader = (root / name for name in ("tool", "lib.version1", "lib.version2", "libopenjp2.so.7"))
            tool.write_bytes(b"synthetic tool")
            first.write_bytes(b"original library")
            second.write_bytes(b"changed library")
            loader.symlink_to(first)
            ldd = subprocess.CompletedProcess([], 0, f"libopenjp2.so.7 => {loader} (0x1234)\n".encode(), b"")
            with patch.object(scout.subprocess, "run", return_value=ldd):
                libraries, _ = scout.runtime_dependencies(tool)
                identity = {"path": str(tool), "sha256": scout.sha(tool), "runtime_libraries": libraries}
                self.assertEqual(libraries[0]["name"], "libopenjp2.so.7")
                self.assertEqual(libraries[0]["loader_path"], str(loader))
                self.assertEqual(libraries[0]["resolved_path"], str(first))
                self.assertTrue(scout.tool_unchanged(tool, identity))
                loader.unlink()
                loader.symlink_to(second)
                self.assertTrue(first.exists())
                self.assertEqual(scout.sha(first), libraries[0]["sha256"])
                self.assertFalse(scout.tool_unchanged(tool, identity))
                with patch.object(scout, "process") as process:
                    result = scout.checked_process([str(tool)], root / "unused.log", 1, identity)
                    process.assert_not_called()
                self.assertEqual(result["status"], "identity_changed")
                self.assertIsNone(result["wall_ns"])

    def development_evidence(self):
        profile = scout.profiles([3], ["baseline"])[0]
        asset = {"id": f"{scout.DEVELOPMENT}-MS16", "bundle_id": scout.DEVELOPMENT, "product": "MS16",
                 "image": {"width": 128, "height": 128, "components": 8, "precision": 16, "signed": False},
                 "bytes": 128 * 128 * 8 * 2, "sha256": digest(b"prepared"), "planar_sha256": digest(b"planar")}
        operation = {"status": "ok", "exit_code": 0, "wall_ns": 10, "measurement_boundary": "application_journey"}
        return {"schema_version": 2, "kind": "openjpeg_satellite_compression_scout", "cohort": "development",
                "bundle": scout.DEVELOPMENT, "complete": True, "valid": True, "rounds": 1,
                "identity_changes": [], "runtime_identity_changes": [], "measurement_boundary": "application_journey",
                "profiles": [profile], "assets": [asset], "observations": [{
                    "asset_id": asset["id"], "profile": profile, "status": "ok", "exact": True,
                    "sequence": 0, "round": 0, "profile_status": "ok", "observed_profile": scout.expected_observation(profile),
                    "encode": operation, "decode": operation,
                    "decoded": {"status": "present", "exact": True, "bytes": asset["bytes"], "sha256": asset["planar_sha256"]},
                    "codestream": {"status": "present", "bytes": 100, "sha256": digest(b"stream")}}]}

    def test_holdout_accepts_complete_exact_development_profile_only(self):
        evidence = self.development_evidence()
        chosen = scout.profiles([3], ["baseline"])
        scout.validate_development_evidence(evidence, ["MS16"], chosen)
        for products, profiles in ((["PAN16"], chosen), (["MS16"], scout.profiles([4], ["baseline"]))):
            with self.assertRaises(ValueError):
                scout.validate_development_evidence(evidence, products, profiles)

    def test_holdout_rejects_forged_labels_malformed_contract_and_incomplete_rounds(self):
        mutations = [
            (("schema_version",), 99), (("schema_version",), 1), (("schema_version",), True), (("kind",), "other"),
            (("bundle",), scout.HOLDOUT), (("cohort",), "holdout"), (("complete",), 1), (("valid",), False),
            (("identity_changes",), ["input"]), (("runtime_identity_changes",), ["compress"]),
            (("observations", 0, "asset_id"), "MS16"),
            (("observations", 0, "asset_id"), f"{scout.HOLDOUT}-MS16"),
            (("assets", 0, "bundle_id"), scout.HOLDOUT), (("profiles", 0, "block"), [32, 32]),
            (("observations", 0, "profile", "style"), 1), (("observations", 0, "exact"), False),
            (("observations", 0, "profile_status"), "invalid_structure"),
            (("observations", 0, "observed_profile", "mct"), True),
            (("observations", 0, "decoded", "bytes"), 100), (("observations", 0, "decoded", "sha256"), digest(b"wrong")),
            (("observations", 0, "decode", "status"), "timeout"),
            (("observations", 0, "round"), 3), (("observations", 0, "sequence"), 1),
            (("rounds",), 3), (("observations",), []), (("observations", 0), {"status": "ok"}),
        ]
        for path, value in mutations:
            evidence = copy.deepcopy(self.development_evidence())
            target = evidence
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path, value=value), self.assertRaises(ValueError):
                scout.validate_development_evidence(evidence, ["MS16"], scout.profiles([3], ["baseline"]))
        for malformed in ([], None, {"cohort": "development", "complete": True, "valid": True}):
            with self.assertRaises(ValueError):
                scout.validate_development_evidence(malformed, ["MS16"], scout.profiles([3], ["baseline"]))

    def test_holdout_needs_explicit_selection_before_loading_any_pixels(self):
        args = [str(SCRIPT), "--cohort", "holdout"]
        for name in ("store", "prepared", "common-streams", "sources", "output", "opj-compress", "opj-decompress"):
            args += ["--" + name, "/not-used"]
        with patch.object(scout.sys, "argv", args), patch.object(scout.sys, "stderr"), patch.object(scout, "load_inputs") as load:
            with self.assertRaises(SystemExit):
                scout.main()
            load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
