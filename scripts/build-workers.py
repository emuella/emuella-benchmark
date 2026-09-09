#!/usr/bin/env python3
"""Build isolated workers and bind their executable dependencies and build inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PIN = "1c1a7fbc583d69c6d57bfd1da4248aa6fae071cc"

def output(*args, cwd=ROOT):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def libraries(executable):
    text = output("ldd", str(executable))
    if "not found" in text:
        raise RuntimeError(f"unresolved dynamic dependency for {executable}: {text}")
    return sorted({Path(p).resolve() for p in re.findall(r"(/\S+)\s+\(", text) if Path(p).is_file()})

def cargo_config_files(directory, environment):
    """Identify Cargo's discovery inputs without copying possible credentials."""
    roots = [directory, *directory.parents]
    candidates = [root / ".cargo" / name for root in roots for name in ("config", "config.toml")]
    cargo_home = (directory / environment.get("CARGO_HOME", str(Path.home() / ".cargo"))).resolve()
    candidates += [cargo_home / name for name in ("config", "config.toml")]
    return [{"path": str(path), "sha256": sha(path)} for path in sorted(set(candidates)) if path.is_file()]

def build_environment(environment):
    names = {"RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RUSTC", "RUSTC_WRAPPER",
             "RUSTC_WORKSPACE_WRAPPER", "RUSTUP_TOOLCHAIN", "CC", "CFLAGS", "CXX",
             "CXXFLAGS", "AR", "LDFLAGS", "CARGO_HOME", "CARGO_BUILD_TARGET"}
    return {key: value for key, value in sorted(environment.items())
            if key in names or key.startswith(("CARGO_PROFILE_", "CARGO_BUILD_", "CARGO_TARGET_",
                                              "CC_", "CFLAGS_", "CXX_", "CXXFLAGS_", "AR_",
                                              "PKG_CONFIG", "OPENJPH_"))}

def build_workers(command, snapshot, environment, dest):
    """Retain Cargo observations and use its reported executable paths."""
    messages = dest / "cargo-build.jsonl"
    verbose = dest / "cargo-build.stderr"
    configs = cargo_config_files(snapshot, environment)
    with messages.open("w") as stdout, verbose.open("w") as stderr:
        result = subprocess.run(command, cwd=snapshot, env=environment, stdout=stdout, stderr=stderr)
    if result.returncode:
        raise RuntimeError(f"Cargo build failed ({result.returncode}); inspect {verbose}")
    if cargo_config_files(snapshot, environment) != configs:
        raise RuntimeError("Cargo configuration changed during build")
    events = [json.loads(line) for line in messages.read_text().splitlines() if line.strip()]
    if not any(event.get("reason") == "build-finished" and event.get("success") for event in events):
        raise RuntimeError("Cargo did not report a successful completed build")
    artefacts = [event for event in events if event.get("reason") == "compiler-artifact"]
    binaries = {}
    for name in ("emuella", "openjpeg", "openjph"):
        matches = [event for event in artefacts if event["target"]["name"] == name + "-worker"
                   and "bin" in event["target"]["kind"] and event.get("executable")]
        if len(matches) != 1:
            raise RuntimeError(f"expected one Cargo executable artefact for {name}-worker")
        binary = dest / (name + "-worker")
        shutil.copy2(matches[0]["executable"], binary)
        binaries[name] = binary
    observations = {
        "command": command, "cwd": str(snapshot), "cargo_config_files": configs,
        "compiler_artefacts": artefacts,
        "evidence_sha256": {path.name: sha(path) for path in (messages, verbose)},
        "compiler_command_evidence": "Cargo -vv records commands dispatched during this build; "
            "fresh=true artefacts were cached and have no new compiler command. "
            "Artefact profile fields are Cargo-reported and can be overridden by rustflags; "
            "inspect the ordered compiler arguments in cargo-build.stderr. "
            "Compiler wrappers may transform dispatched arguments; their internal invocations are not observed.",
    }
    return binaries, observations, {messages, verbose}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target-dir", type=Path)
    parser.add_argument("--emuella-source", type=Path)
    parser.add_argument("--emuella-revision", default=PIN)
    parser.add_argument("--profile", choices=("release", "perf"), default="release")
    parser.add_argument("--simd", action="store_true", help="enable optional Emuella SIMD; parallel remains enabled")
    args = parser.parse_args()
    dest = args.output.resolve()
    if dest == ROOT or ROOT in dest.parents:
        parser.error("build output must be outside the source checkout")
    dest.mkdir(parents=True, exist_ok=False)
    snapshot = dest / "build-source"
    snapshot.mkdir()
    inputs = sorted(p for base in [ROOT / "workers", ROOT / "src"] for p in base.rglob("*")
                    if p.is_file() and "target" not in p.parts and "__pycache__" not in p.parts)
    inputs += [ROOT / "scripts/build-workers.py", ROOT / "Cargo.toml", ROOT / "Cargo.lock"]
    for path in inputs:
        copied = snapshot / path.relative_to(ROOT)
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, copied)
    source_hashes = {str(p.relative_to(ROOT)): sha(snapshot / p.relative_to(ROOT)) for p in inputs}
    target = (args.target_dir or dest / "target").resolve()
    command = ["cargo", "build", "--profile", args.profile, "--manifest-path",
               str(snapshot / "workers/Cargo.toml"), "--target-dir", str(target),
               "--message-format=json", "-vv"]
    if args.simd:
        command += ["--features", "simd"]
    source = None
    if args.emuella_source:
        source = args.emuella_source.resolve()
        revision = output("git", "rev-parse", "HEAD", cwd=source)
        if revision != args.emuella_revision or output("git", "status", "--porcelain", cwd=source):
            parser.error("Emuella checkout must be clean and at the exact requested revision")
        command += ["--config", 'patch."https://github.com/emuella/emuella-j2k".emuella-j2k.path=' + json.dumps(str(source / "crates/emuella-j2k"))]
        command += ["--config", 'patch."https://github.com/emuella/emuella-j2k".emuella-j2k-codestream.path=' + json.dumps(str(source / "crates/emuella-j2k-codestream"))]
    elif args.emuella_revision != PIN:
        parser.error("custom revision requires --emuella-source")
    external = [Path(shutil.which(name) or parser.error(name + " is required")).resolve() for name in ["ojph_compress", "ojph_expand"]]
    build_env = dict(os.environ, OPENJPH_COMPRESS=str(external[0]), OPENJPH_EXPAND=str(external[1]))
    binaries, observations, evidence = build_workers(command, snapshot, build_env, dest)
    if source and (output("git", "rev-parse", "HEAD", cwd=source) != args.emuella_revision
                   or output("git", "status", "--porcelain", cwd=source)):
        parser.error("Emuella checkout changed during build")
    worker_artefact = next(event for event in observations["compiler_artefacts"]
                           if event["target"]["name"] == "emuella-worker" and event.get("executable"))
    observed_features = set()
    for event in observations["compiler_artefacts"]:
        if event["package_id"] == worker_artefact["package_id"]:
            observed_features.update(event["features"])
        elif "lib" in event["target"]["kind"]:
            prefix = event["target"]["name"].replace("_", "-") + "/"
            observed_features.update(prefix + feature for feature in event["features"])
    provenance = {
        "schema_version": 1, "emuella_revision": args.emuella_revision,
        "emuella_tree": output("git", "rev-parse", "HEAD^{tree}", cwd=source) if source else None,
        "rustc": output(build_env.get("RUSTC", "rustc"), "-vV", cwd=snapshot), "cargo": output("cargo", "-V"),
        "tool_identity_scope": "Tool identity queries use PATH and RUSTC/CC environment selections; "
            "Cargo configuration can select other tools, whose dispatched commands are in the verbose log.",
        "cc": output(os.environ.get("CC", "cc"), "--version"),
        "openjpeg_pkg_config": output("pkg-config", "--modversion", "libopenjp2"),
        "profile": args.profile, "features": sorted(observed_features),
        "requested_build": {"profile": args.profile, "simd": args.simd, "default_features": True},
        "build_observations": observations,
        "build_environment": build_environment(build_env),
        "source_sha256": source_hashes,
        "resolved_worker_lock_sha256": sha(snapshot / "workers/Cargo.lock"),
        "resolved_worker_lock": (snapshot / "workers/Cargo.lock").read_text(),
        "openjph_executables": {str(p): sha(p) for p in external},
    }
    sidecar = dest / "build-provenance.json"
    sidecar.write_text(json.dumps(provenance, indent=2) + "\n")
    for name, binary in binaries.items():
        artefacts = {sidecar, *evidence, *libraries(binary)}
        if name == "openjph":
            artefacts.update(external)
            for executable in external:
                artefacts.update(libraries(executable))
        definition = {"executable": str(binary), "args": [], "implementation": name,
            "source_identity": "emuella-j2k@" + args.emuella_revision if name == "emuella" else name + ":build-provenance:" + sha(sidecar),
            "artefacts": [str(p) for p in sorted(artefacts)]}
        (dest / (name + "-worker.json")).write_text(json.dumps(definition, indent=2) + "\n")
    print(dest)

if __name__ == "__main__":
    main()
