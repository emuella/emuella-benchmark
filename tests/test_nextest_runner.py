"""Qualify report lifecycle and test selection with real authored Rust tests."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_nextest", ROOT / "scripts/run-nextest.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class NextestRunnerTests(unittest.TestCase):
    def fixture(self, root):
        source = root / "source"
        (source / ".config").mkdir(parents=True)
        shutil.copy2(ROOT / ".config/nextest.toml", source / ".config/nextest.toml")
        shutil.copy2(ROOT / "rust-toolchain.toml", source / "rust-toolchain.toml")
        for workspace in (source, source / "workers"):
            (workspace / "src").mkdir(parents=True)
            name = "authored-workers" if workspace.name == "workers" else "authored-root"
            (workspace / "Cargo.toml").write_text(
                f'[package]\nname="{name}"\nversion="0.1.0"\nedition="2024"\n[workspace]\n')
            (workspace / "src/lib.rs").write_text(
                '#[test] fn alpha() {}\n#[test] fn beta() {}\n'
                '#[test] fn failure() { assert!(std::env::var_os("AUTHORED_FAIL").is_none()); }\n'
                '#[test] #[ignore] fn ignored() {}\n')
        return source

    def invoke(self, profile, arguments, source, environment):
        with patch.dict(os.environ, environment), contextlib.redirect_stdout(io.StringIO()):
            return module.run(profile, arguments, root=source)

    def reports(self, directory):
        return sorted(directory.glob("*/*/junit.xml"))

    def test_preflight_rejects_old_runner_before_creating_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.fixture(root)
            reports = root / "reports"
            result = subprocess.CompletedProcess([], 0, "cargo-nextest 0.9.145\n", "")
            with patch.dict(os.environ, {"EMUELLA_NEXTEST_REPORT_DIR": str(reports)}), \
                    patch.object(module.subprocess, "run", return_value=result):
                with self.assertRaisesRegex(ValueError, ">= 0.9.146"):
                    module.run("root", ["--all-targets"], root=source)
            self.assertFalse(reports.exists())

    def test_native_nested_selection_and_target_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.fixture(root)
            reports = root / "reports"
            environment = {"EMUELLA_NEXTEST_REPORT_DIR": str(reports),
                           "CARGO_TARGET_DIR": str(root / "environment-target")}
            self.assertEqual(self.invoke("root", ["--all-targets", "alpha"], source, environment), 0)
            first = self.reports(reports)[0]
            before = first.read_bytes()
            self.assertEqual(self.invoke("workers-ci", ["--manifest-path", "workers/Cargo.toml",
                             "--all-targets", "--target-dir", str(root / "argument-target")],
                             source, environment), 0)
            self.assertEqual(first.read_bytes(), before)
            self.assertEqual(len(self.reports(reports)), 2)
            selected = ET.parse(first).findall(".//testcase")
            self.assertEqual([test.attrib["name"] for test in selected
                              if test.find("skipped") is None], ["alpha"])
            nested = next(p for p in self.reports(reports) if p != first)
            self.assertEqual(len(ET.parse(nested).findall(".//testcase")), 4)
            self.assertTrue((root / "environment-target/debug").is_dir())
            self.assertTrue((root / "argument-target/debug").is_dir())
            self.assertFalse((source / "target").exists())
            self.assertFalse(list(reports.glob("*/*.toml")))

    def test_native_failure_keeps_all_results_and_previous_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.fixture(root)
            reports = root / "reports"
            environment = {"EMUELLA_NEXTEST_REPORT_DIR": str(reports),
                           "CARGO_TARGET_DIR": str(root / "target")}
            self.assertEqual(self.invoke("root-ci", ["--all-targets"], source, environment), 0)
            previous = self.reports(reports)[0]
            before = previous.read_bytes()
            environment["AUTHORED_FAIL"] = "1"
            self.assertNotEqual(self.invoke("root-ci", ["--all-targets"], source, environment), 0)
            current = next(p for p in self.reports(reports) if p != previous)
            cases = ET.parse(current).findall(".//testcase")
            self.assertEqual(len(cases), 4)
            self.assertEqual(sum(test.find("failure") is not None for test in cases), 1)
            self.assertEqual(sum(test.find("skipped") is not None for test in cases), 1)
            self.assertEqual(previous.read_bytes(), before)
            receipt = json.loads((current.parents[1] / "invocation.json").read_text())
            self.assertNotEqual(receipt["exit_code"], 0)
            self.assertFalse(list(reports.glob("*/*.toml")))

    def test_native_build_failure_cannot_reuse_success_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.fixture(root)
            reports = root / "reports"
            environment = {"EMUELLA_NEXTEST_REPORT_DIR": str(reports),
                           "CARGO_TARGET_DIR": str(root / "target")}
            self.assertEqual(self.invoke("root", ["--all-targets"], source, environment), 0)
            previous = self.reports(reports)[0]
            before = previous.read_bytes()
            (source / "src/lib.rs").write_text("authored compilation failure\n")
            self.assertNotEqual(self.invoke("root", ["--all-targets"], source, environment), 0)
            self.assertEqual(self.reports(reports), [previous])
            self.assertEqual(previous.read_bytes(), before)
            receipts = [json.loads(p.read_text()) for p in reports.glob("*/invocation.json")]
            self.assertEqual(sum(r["exit_code"] != 0 for r in receipts), 1)
            self.assertFalse(list(reports.glob("*/*.toml")))

    def test_native_valid_minimum_version_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.fixture(Path(directory))
            config = source / ".config/nextest.toml"
            configuration = config.read_text().replace('"0.9.146"', '"999.0.0"')
            config.write_text(configuration)
            result = subprocess.run(["cargo", "nextest", "list", "--config-file", str(config)],
                                    cwd=source, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 92)
            self.assertIn("requires nextest version 999.0.0", result.stderr)
            self.assertNotIn("error parsing", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
