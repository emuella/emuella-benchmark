#!/usr/bin/env python3
"""Run one Rust test selection with a fresh, attributable JUnit report."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
MINIMUM = (0, 9, 146)


def run(profile, arguments, root=ROOT):
    configuration = (root / ".config/nextest.toml").read_text()
    profiles = tomllib.loads(configuration)["profile"]
    if profile not in profiles or profile in {"default", "ci"}:
        raise ValueError(f"unknown test configuration: {profile}")
    cargo = ["cargo"]
    if arguments and arguments[0].startswith("+"):
        cargo.append(arguments[0])
        arguments = arguments[1:]
    version = subprocess.run([*cargo, "nextest", "--version"], cwd=root,
                             capture_output=True, text=True, check=False)
    match = re.match(r"cargo-nextest (\d+)\.(\d+)\.(\d+)(?:\s|$)", version.stdout)
    if version.returncode or match is None or tuple(map(int, match.groups())) < MINIMUM:
        raise ValueError("cargo-nextest >= 0.9.146 is required; install the pinned pre-built release")

    # Report location is independent of Cargo's build cache. This also loads the
    # root-owned configuration explicitly for the separate workers workspace.
    reports = Path(os.environ.get("EMUELLA_NEXTEST_REPORT_DIR", root / "target/nextest")).resolve()
    reports.mkdir(parents=True, exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix=f"{profile}-", dir=reports))
    report = destination / profile / "junit.xml"
    receipt = {"profile": profile, "cwd": str(root),
               "configuration_sha256": hashlib.sha256(configuration.encode()).hexdigest(),
               "nextest": version.stdout.strip(), "report": str(report), "exit_code": None}
    print(f"Nextest configuration: {profile}; report: {report}", flush=True)
    # Nextest resolves store.dir against the selected workspace, independently
    # of --target-dir/CARGO_TARGET_DIR. An absolute store keeps both routes equal.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", dir=destination) as config:
        config.write(configuration + "\n[store]\ndir = " + json.dumps(str(destination)) + "\n")
        config.write(f"\n[profile.{profile}.junit]\nreport-name = {json.dumps(profile)}\n")
        config.flush()
        command = [*cargo, "nextest", "run", "--config-file", config.name,
                   "--profile", profile, *arguments]
        receipt["command"] = command
        (destination / "invocation.json").write_text(json.dumps(receipt, indent=2) + "\n")
        result = subprocess.run(command, cwd=root, check=False)
    receipt["exit_code"] = result.returncode
    (destination / "invocation.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if result.returncode == 0 and not report.is_file():
        raise ValueError(f"successful Nextest run did not produce {report}")
    return result.returncode


def main():
    try:
        if len(sys.argv) < 2:
            raise ValueError("usage: run-nextest.py CONFIGURATION [+TOOLCHAIN] [NEXTEST ARGUMENTS...]")
        return run(sys.argv[1], sys.argv[2:])
    except (OSError, ValueError) as error:
        print(f"Nextest runner failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
