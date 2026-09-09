"""Exercise build selection and provenance with real Cargo and authored tiny crates."""
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

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_workers", ROOT / "scripts/build-workers.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@unittest.skipUnless(shutil.which("cargo"), "Cargo is required")
class WorkerBuildTests(unittest.TestCase):
    def fixture(self, root):
        source = root / "source"
        (source / "workers/src").mkdir(parents=True)
        (source / "scripts").mkdir()
        shutil.copy2(ROOT / "scripts/build-workers.py", source / "scripts/build-workers.py")
        manifest = (ROOT / "workers/Cargo.toml").read_text()
        # Exercise the shipped feature forwarding and profile, with tiny authored
        # stand-ins for codec crates rather than compiling the complete codec.
        configuration = manifest[manifest.index("[features]"):manifest.index("[dependencies]")]
        worker_manifest = '[package]\nname="emuella-benchmark-workers"\nversion="0.1.0"\nedition="2024"\n[workspace]\n'
        worker_manifest += configuration + '[dependencies]\n'
        for name in ("emuella-j2k", "emuella-j2k-codestream", "rayon"):
            dependency = source / "src" / name
            dependency.mkdir(parents=True)
            (dependency / "Cargo.toml").write_text(
                f'[package]\nname="{name}"\nversion="0.1.0"\nedition="2024"\n'
                '[features]\nparallel=[]\nsimd=[]\n[lib]\npath="lib.rs"\n')
            (dependency / "lib.rs").write_text(
                'pub fn flags() -> (bool, bool) { (cfg!(feature="parallel"), cfg!(feature="simd")) }\n')
            features = ', features=["parallel"]' if name != "rayon" else ''
            worker_manifest += f'{name} = {{ path="../src/{name}", optional=true{features} }}\n'
        for name in ("emuella", "openjpeg", "openjph"):
            worker_manifest += f'[[bin]]\nname="{name}-worker"\npath="src/{name}.rs"\n'
            (source / "workers/src" / (name + ".rs")).write_text(
                'fn main() { println!("{:?} {:?}", emuella_j2k::flags(), emuella_j2k_codestream::flags()); }\n')
        (source / "workers/Cargo.toml").write_text(worker_manifest)
        (source / "workers/build.rs").write_text(
            'fn main() { println!("cargo:rerun-if-changed=build.rs"); '
            'println!("authored build-script output"); }\n')
        (source / "Cargo.toml").write_text('[package]\nname="authored-root"\nversion="0.1.0"\n')
        (source / "src/lib.rs").write_text('// Authored root placeholder.\n')
        (source / "Cargo.lock").write_text('# Authored root placeholder: not built by this fixture.\n')
        external = root / "authored-openjph"
        external.write_text("authored executable identity")
        return source, external

    def build(self, root, source, external, extra=(), overrides=None):
        destination = root / "build"
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(("CARGO_", "RUSTFLAGS", "RUSTC"))}
        environment.update(CARGO_HOME=str(root / "cargo-home"))
        environment.update(overrides or {})
        actual_output = module.output

        def output(*args, **kwargs):
            if args[0] in ("cc", "pkg-config"):
                return "authored native dependency identity"
            return actual_output(*args, **kwargs)

        with patch.object(module, "ROOT", source), patch.dict(os.environ, environment, clear=True), \
                patch.object(module.shutil, "which", return_value=str(external)), \
                patch.object(module, "libraries", return_value=[]), \
                patch.object(module, "output", side_effect=output), \
                patch("sys.argv", ["build-workers", "--output", str(destination), *extra]), \
                contextlib.redirect_stdout(io.StringIO()):
            try:
                module.main()
            except RuntimeError as error:
                raise AssertionError((destination / "cargo-build.stderr").read_text()) from error
        return destination, json.loads((destination / "build-provenance.json").read_text())

    def test_four_variants_build_real_selected_binaries_and_resolved_features(self):
        for profile in ("release", "perf"):
            for simd in (False, True):
                with self.subTest(profile=profile, simd=simd), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    source, external = self.fixture(root)
                    args = [] if profile == "release" and not simd else ["--profile", profile]
                    if simd:
                        args += ["--simd"]
                    dest, provenance = self.build(root, source, external, args)
                    expected = f"(true, {str(simd).lower()}) (true, {str(simd).lower()})"
                    self.assertEqual(subprocess.check_output([dest / "emuella-worker"], text=True).strip(), expected)
                    self.assertEqual(provenance["requested_build"],
                                     {"profile": profile, "simd": simd, "default_features": True})
                    artefacts = provenance["build_observations"]["compiler_artefacts"]
                    for crate in ("emuella_j2k", "emuella_j2k_codestream"):
                        observed = next(event for event in artefacts if event["target"]["name"] == crate)
                        self.assertIn("parallel", observed["features"])
                        self.assertEqual("simd" in observed["features"], simd)
                    executable = next(event for event in artefacts if event.get("executable"))
                    self.assertEqual(Path(executable["executable"]).parent.name, profile)
                    self.assertFalse(executable["fresh"])
                    verbose = (dest / "cargo-build.stderr").read_text()
                    self.assertIn("authored build-script output", (dest / "cargo-build.jsonl").read_text())
                    if profile == "perf":
                        self.assertIn("-C lto=thin", verbose)
                        self.assertIn("-C codegen-units=1", verbose)
                        self.assertIn("-C debuginfo=line-tables-only", verbose)
                    definition = json.loads((dest / "emuella-worker.json").read_text())
                    for name, digest in provenance["build_observations"]["evidence_sha256"].items():
                        self.assertEqual(module.sha(dest / name), digest)
                        self.assertIn(str(dest / name), definition["artefacts"])
                    self.assertFalse((source / "workers/Cargo.lock").exists())
                    self.assertTrue((dest / "build-source/workers/Cargo.lock").exists())

    def test_configuration_target_and_overrides_are_observed_without_relabelling_intent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, external = self.fixture(root)
            host = next(line.split(": ", 1)[1] for line in module.output("rustc", "-vV").splitlines()
                        if line.startswith("host: "))
            config = root / ".cargo/config.toml"
            config.parent.mkdir()
            config.write_text(f'[build]\ntarget="{host}"\n[profile.perf]\nopt-level=1\n')
            dest, provenance = self.build(root, source, external, ["--profile", "perf"],
                                          {"CARGO_PROFILE_PERF_CODEGEN_UNITS": "4", "RUSTFLAGS": "-C opt-level=2"})
            observations = provenance["build_observations"]
            self.assertIn({"path": str(config), "sha256": module.sha(config)}, observations["cargo_config_files"])
            executable = next(event for event in observations["compiler_artefacts"] if event.get("executable"))
            self.assertEqual(Path(executable["executable"]).parent.parent.name, host)
            self.assertEqual(executable["profile"]["opt_level"], "1")
            self.assertEqual(provenance["requested_build"]["profile"], "perf")
            self.assertEqual(provenance["build_environment"]["RUSTFLAGS"], "-C opt-level=2")
            self.assertEqual(subprocess.check_output([dest / "emuella-worker"], text=True).strip(),
                             "(true, false) (true, false)")
            verbose = (dest / "cargo-build.stderr").read_text()
            self.assertIn("-C opt-level=1", verbose)
            self.assertIn("-C opt-level=2", verbose)
            self.assertIn("-C codegen-units=4", verbose)

    def test_missing_executable_evidence_fails_instead_of_using_stale_release_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release").mkdir()
            (root / "release/emuella-worker").write_text("stale")

            def run(command, **kwargs):
                kwargs["stdout"].write(json.dumps({"reason": "build-finished", "success": True}) + "\n")
                return subprocess.CompletedProcess(command, 0)

            with patch.object(module.subprocess, "run", side_effect=run):
                with self.assertRaisesRegex(RuntimeError, "expected one Cargo executable artefact"):
                    module.build_workers(["cargo", "build"], root, {}, root)
            self.assertFalse((root / "emuella-worker").exists())

    def test_build_script_output_cannot_substitute_for_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def run(command, **kwargs):
                kwargs["stdout"].write('[authored 0.1.0] {"reason":"build-finished","success":true}\n')
                kwargs["stdout"].write('null\n[]\n"unstructured output"\n')
                return subprocess.CompletedProcess(command, 0)

            with patch.object(module.subprocess, "run", side_effect=run):
                with self.assertRaisesRegex(RuntimeError, "did not report a successful completed build"):
                    module.build_workers(["cargo", "build"], root, {}, root)


if __name__ == "__main__":
    unittest.main()
