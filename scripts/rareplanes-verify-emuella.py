#!/usr/bin/env python3
"""Retain and independently verify eight Emuella RarePlanes lossless streams.

This opt-in journey is separate from the 160-batch timing matrix.
All inputs, streams and results must remain inside the approved store.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

spec = importlib.util.spec_from_file_location(
    "rareplanes_calibrate", Path(__file__).with_name("rareplanes-calibrate.py"))
calibration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibration)


def decode_experiment(assets, prepared_digest, streams):
    experiment = calibration.build_decode_experiment(assets, prepared_digest, streams)
    experiment["name"] = "rareplanes-independent-emuella-stream-verification"
    experiment["environment_tags"] = {"journey": "independent-verification-not-headline-timing"}
    for case in experiment["cases"]:
        case["input"]["provenance"]["generator"] = "Emuella public lossless encoder"
    return experiment


def validate_export_response(request, response):
    case = request["case"]
    profile = {
        "coding": "classic", "decomposition_levels": 2, "tiles": 1,
        "progression_order": "lrcp", "quality_layers": 1,
        "multiple_component_transform": (
            "reversible_colour_transform" if case["image"]["components"] == 3 else "none"),
    }
    if (response.get("schema_version") != request["schema_version"]
            or response.get("request_id") != request["request_id"]
            or response.get("applied_case") != case
            or response.get("boundary") != "codec_operation"
            or response.get("diagnostics", {}).get("encode_profile") != profile
            or response.get("status") != "ok"
            or response.get("correctness", {}).get("exact") is not True
            or len(response.get("samples_ns", [])) != 1):
        raise RuntimeError("export response differs from requested identity, profile or exact semantics")


def export_streams(assets, prepared_digest, executable, output):
    streams = {}
    sources = {asset["id"]: asset["source_sha256"] for asset in assets}
    encode = calibration.build_encode_experiment(assets, prepared_digest)
    for case in encode["cases"]:
        asset_id = case["id"].removesuffix("-encode")
        request = {"schema_version": 1, "request_id": asset_id,
                   "case": case, "protocol": encode["protocol"], "diagnostic": False}
        request_path = output / "inputs" / (asset_id + "-request.json")
        response_path = output / "inputs" / (asset_id + "-response.json")
        stream = output / "streams" / (asset_id + ".j2k")
        calibration.write_new(request_path, request)
        result = subprocess.run(
            [str(executable), "--export-lossless", str(request_path), str(response_path), str(stream)],
            capture_output=True, text=True, timeout=120)
        (output / "inputs" / (asset_id + "-export.log")).write_text(result.stderr)
        if result.returncode:
            raise RuntimeError(f"Emuella export failed for {asset_id}; retained export log")
        response = json.loads(response_path.read_text())
        validate_export_response(request, response)
        if (response.get("status") != "ok" or not response.get("correctness", {}).get("exact")
                or stream.is_symlink() or not stream.is_file() or stream.stat().st_size == 0
                or response.get("output_bytes") != stream.stat().st_size):
            raise RuntimeError(f"Emuella export was not exact for {asset_id}")
        streams[asset_id] = {
            "path": stream, "sha256": calibration.digest_file(stream), "bytes": stream.stat().st_size,
            "generator_sha256": calibration.digest_file(executable),
            "arguments_sha256": calibration.digest_file(request_path),
            "input_sha256": case["input"]["sha256"], "source_sha256": sources[asset_id],
            "image": case["image"],
            "profile": response["diagnostics"]["encode_profile"],
            "export_response_sha256": calibration.digest_file(response_path),
            "verification_journey_observations": {
                key: response[key] for key in ("samples_ns", "peak_rss_bytes", "correctness", "output_bytes")
                if key in response
            },
        }
    return streams


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("benchmark", "workers", "build-provenance", "prepared", "store", "output", "opj-dump"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        store = args.store.resolve(strict=True)
        prepared = args.prepared.resolve(strict=True)
        prepared.relative_to(store)
        output = calibration.new_store_child(store, args.output)
        _, assets, prepared_digest = calibration.load_prepared(prepared)
        if calibration.git("status", "--porcelain", "--untracked-files=normal"):
            raise ValueError("verification requires a clean committed benchmark checkout")
        revision = calibration.git("rev-parse", "HEAD")
        identity_paths = [Path(__file__), Path(calibration.__file__), args.benchmark,
                          args.build_provenance, args.opj_dump]
        definitions = {}
        for name in ("emuella", "openjpeg"):
            path = args.workers / (name + "-worker.json")
            definitions[name] = json.loads(path.read_text())
            if definitions[name].get("args"):
                raise ValueError("verification requires direct native worker definitions")
            executable = Path(definitions[name]["executable"])
            if not executable.is_absolute():
                raise ValueError("worker executable must be absolute")
            identity_paths.extend([path, executable])
            identity_paths.extend(Path(p) for p in definitions[name].get("artefacts", []))
        identities = {path: calibration.digest_file(path) for path in identity_paths}
        build = calibration.public_build_provenance(args.build_provenance)
        output.mkdir()
        for child in ("inputs", "streams", "runs"):
            (output / child).mkdir()
        streams = export_streams(assets, prepared_digest,
                                 Path(definitions["emuella"]["executable"]), output)
        for asset in assets:
            if asset["image"]["components"] == 8:
                record = streams[asset["id"]]
                record["independent_inspection"] = calibration.inspect_msi_stream(
                    record["path"], asset["image"], args.opj_dump, output / "streams" / asset["id"])
        runtime_streams = {key: {**value, "path": str(value["path"])} for key, value in streams.items()}
        calibration.write_new(output / "inputs" / "emuella-streams.json", runtime_streams)
        experiment_path = output / "inputs" / "decode.json"
        calibration.write_new(experiment_path, decode_experiment(assets, prepared_digest, streams))
        failures = []
        runs = []
        for name in ("emuella", "openjpeg"):
            run_dir = output / "runs" / (name + "-emuella-stream-decode")
            failure = calibration.invoke_run(args.benchmark, experiment_path,
                                             args.workers / (name + "-worker.json"), run_dir)
            if failure:
                failures.append(failure)
            if (run_dir / "run.json").is_file():
                run = json.loads((run_dir / "run.json").read_text())
                run["_run_sha256"] = calibration.digest_file(run_dir / "run.json")
                runs.append(calibration.summarise_run(
                    run, {a["id"]: a["bytes"] for a in assets}, (store,)))
        if (revision != calibration.git("rev-parse", "HEAD")
                or calibration.git("status", "--porcelain", "--untracked-files=normal")
                or any(calibration.digest_file(path) != digest for path, digest in identities.items())
                or calibration.load_prepared(prepared)[2] != prepared_digest
                or any(calibration.digest_file(v["path"]) != v["sha256"] for v in streams.values())):
            failures.append({"name": "identity", "stderr": "source, build or input changed during verification"})
        complete = (not failures and len(runs) == 2 and all(
            len(run["observations"]) == 8 and all(
                row["disposition"] == "completed_exact" for row in run["observations"])
            for run in runs))
        summary = {
            "schema_version": 1, "complete": complete,
            "method": "One separately exported public Emuella lossless D2 stream per admitted asset; full-reference Emuella and independent OpenJPEG verification.",
            "interpretation": "All time and process RSS here are verification-journey observations, excluded from headline matrix and codec working-allocation measurements.",
            "orchestration_revision": revision,
            "orchestration_sha256": identities[Path(__file__)],
            "calibration_script_sha256": identities[Path(calibration.__file__)],
            "prepared_manifest_sha256": prepared_digest, "build_provenance": build,
            "streams": [{"asset_id": key, **{k: v for k, v in value.items() if k != "path"}}
                        for key, value in streams.items()],
            "unsupported": calibration.unsupported_observations(assets),
            "failures": [{**f, "stderr": calibration.sanitise_detail(f["stderr"], (store,))}
                         for f in failures], "runs": runs,
        }
        calibration.write_new(output / "rareplanes-emuella-verification-summary.json", summary)
        print(json.dumps({"complete": complete, "streams": len(streams), "decode_runs": len(runs)}))
        return 0 if complete else 4
    except (ValueError, KeyError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"verification failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
