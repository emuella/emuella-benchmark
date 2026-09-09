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

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target-dir", type=Path)
    parser.add_argument("--emuella-source", type=Path)
    parser.add_argument("--emuella-revision", default=PIN)
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
    command = ["cargo", "build", "--release", "--manifest-path", str(snapshot / "workers/Cargo.toml"), "--target-dir", str(target)]
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
    subprocess.run(command, check=True, cwd=snapshot, env=build_env)
    if source and (output("git", "rev-parse", "HEAD", cwd=source) != args.emuella_revision
                   or output("git", "status", "--porcelain", cwd=source)):
        parser.error("Emuella checkout changed during build")
    binaries = {}
    for name in ["emuella", "openjpeg", "openjph"]:
        binary = dest / (name + "-worker")
        shutil.copy2(target / "release" / binary.name, binary)
        binaries[name] = binary
    provenance = {
        "schema_version": 1, "emuella_revision": args.emuella_revision,
        "emuella_tree": output("git", "rev-parse", "HEAD^{tree}", cwd=source) if source else None,
        "rustc": output("rustc", "-vV"), "cargo": output("cargo", "-V"),
        "cc": output(os.environ.get("CC", "cc"), "--version"),
        "openjpeg_pkg_config": output("pkg-config", "--modversion", "libopenjp2"),
        "profile": "release", "features": ["emuella", "openjpeg", "emuella-j2k/parallel"],
        "build_environment": {key: os.environ.get(key, "") for key in ["RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CC", "CFLAGS", "LDFLAGS", "CARGO_BUILD_TARGET"]},
        "source_sha256": source_hashes,
        "resolved_worker_lock_sha256": sha(snapshot / "workers/Cargo.lock"),
        "resolved_worker_lock": (snapshot / "workers/Cargo.lock").read_text(),
        "openjph_executables": {str(p): sha(p) for p in external},
    }
    sidecar = dest / "build-provenance.json"
    sidecar.write_text(json.dumps(provenance, indent=2) + "\n")
    for name, binary in binaries.items():
        artefacts = {sidecar, *libraries(binary)}
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
