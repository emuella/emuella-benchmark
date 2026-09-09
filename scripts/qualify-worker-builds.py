#!/usr/bin/env python3
"""Qualify four unchanged-codec builds using authorised complete acquisitions."""

import argparse
from collections import Counter
import importlib.util
import hashlib
import json
import math
from pathlib import Path
import subprocess
import shutil


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


calibration = module("build_calibration", "rareplanes-calibrate.py")
verification = module("build_verification", "rareplanes-verify-emuella.py")
ROOT = Path(__file__).resolve().parents[1]
VARIANTS = {"release": ("release", False), "release-simd": ("release", True),
            "perf": ("perf", False), "perf-simd": ("perf", True)}
PIN = "1c1a7fbc583d69c6d57bfd1da4248aa6fae071cc"
VALID_VERDICTS = {"improved", "regressed", "equivalent", "inconclusive"}


def select_bundles(assets, bundles):
    if not bundles or len(set(bundles)) != len(bundles):
        raise ValueError("select at least one unique complete bundle explicitly")
    selected = []
    for bundle in bundles:
        group = [asset for asset in assets if asset["bundle_id"] == bundle]
        if Counter(asset["product"] for asset in group) != Counter(calibration.PRODUCTS.keys()):
            raise ValueError(f"bundle {bundle} must contain all four products exactly once")
        selected.extend(sorted(group, key=lambda a: tuple(calibration.PRODUCTS).index(a["product"])))
    return selected


def store_file(store, path):
    path = Path(path).absolute()
    return calibration.checked_relative_file(store, path.relative_to(store))


def load_common(path, assets, store):
    document = json.loads(store_file(store, path).read_text())
    if document.get("schema_version") != 1 or document.get("generator") != "OpenJPEG opj_compress":
        raise ValueError("common streams require the existing version 1 OpenJPEG mapping")
    streams = {}
    for asset in assets:
        row = dict(document["streams"][asset["id"]])
        stream = store_file(store, row["path"])
        if (stream.stat().st_size != row["bytes"] or calibration.digest_file(stream) != row["sha256"]):
            raise ValueError(f"common stream integrity mismatch: {asset['id']}")
        image = asset["image"]
        arguments = row["arguments"]
        if not isinstance(arguments, list) or len(arguments) < 2:
            raise ValueError("common stream arguments differ from frozen D2/no-MCT profile")
        expected = ["-i", arguments[1], "-o", str(stream), "-F",
                    f"{image['width']},{image['height']},{image['components']},{image['precision']},u",
                    "-n", "3", "-t", f"{image['width']},{image['height']}",
                    "-p", "LRCP", "-r", "1", "-mct", "0", "-threads", "1"]
        arguments_digest = hashlib.sha256(json.dumps(arguments, separators=(",", ":")).encode()).hexdigest()
        if arguments != expected or arguments_digest != row["arguments_sha256"]:
            raise ValueError("common stream arguments differ from frozen D2/no-MCT profile")
        calibration.validate_digest(row["generator_sha256"], "common generator sha256")
        row["path"] = stream
        streams[asset["id"]] = row
    return streams


def validate_matrix(builds):
    if set(builds) != set(VARIANTS):
        raise ValueError("build matrix must contain release, release-simd, perf and perf-simd")
    baseline = builds["release"]
    for name, build in builds.items():
        profile, simd = VARIANTS[name]
        if (build.get("schema_version") != 1 or build.get("emuella_revision") != PIN
                or not build.get("emuella_tree")
                or build.get("requested_build") != {"profile": profile, "simd": simd, "default_features": True}
                or build.get("profile") != profile):
            raise ValueError(f"{name}: requested build matrix or frozen source identity differs")
        for field in ("emuella_tree", "source_sha256", "resolved_worker_lock_sha256", "rustc", "cargo", "cc", "build_environment"):
            if field not in build or build[field] != baseline[field]:
                raise ValueError(f"{name}: build inputs differ: {field}")
        events = build["build_observations"]["compiler_artefacts"]
        codec = [event for event in events if event["target"]["name"].replace("_", "-") == "emuella-j2k"]
        if len(codec) != 1 or ("simd" in codec[0]["features"]) != simd or "parallel" not in codec[0]["features"]:
            raise ValueError(f"{name}: observed codec features differ")
        if codec[0].get("fresh") is not False:
            raise ValueError(f"{name}: qualification requires a freshly compiled codec")
        environment = build["build_environment"]
        if any(value and (key in {"RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER",
                                 "CARGO_BUILD_RUSTFLAGS", "CARGO_BUILD_RUSTC_WRAPPER", "CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER"}
                          or key.startswith("CARGO_PROFILE_")
                          or (key.startswith("CARGO_TARGET_") and key.endswith("_RUSTFLAGS")))
               for key, value in environment.items()):
            raise ValueError("qualification excludes compiler flags, wrappers and profile overrides")
        if build["build_observations"].get("cargo_config_files"):
            raise ValueError("qualification requires no unreviewed Cargo configuration overrides")


def load_workers(directories):
    definitions, builds, paths = {}, {}, []
    for name, directory in directories.items():
        directory = directory.resolve(strict=True)
        sidecar = directory / "build-provenance.json"
        builds[name] = json.loads(sidecar.read_text())
        for kind in (("emuella", "openjpeg") if name == "release" else ("emuella",)):
            key = name if kind == "emuella" else "openjpeg"
            definition_path = directory / f"{kind}-worker.json"
            definition = json.loads(definition_path.read_text())
            executable = Path(definition["executable"])
            artefacts = [Path(p) for p in definition["artefacts"]]
            if (definition.get("args") or not executable.is_absolute() or sidecar not in artefacts
                    or any(not p.is_absolute() for p in artefacts)
                    or (kind == "emuella" and definition["source_identity"] != "emuella-j2k@" + PIN)):
                raise ValueError("workers require direct native executables and bound build sidecars")
            definitions[key] = (definition_path, definition)
            paths.extend([definition_path, executable, *artefacts])
        for relative, digest in builds[name]["source_sha256"].items():
            source = calibration.checked_relative_file(ROOT, relative)
            if calibration.digest_file(source) != digest:
                raise ValueError("worker build inputs differ from the committed benchmark candidate")
            paths.append(source)
        for filename, digest in builds[name]["build_observations"]["evidence_sha256"].items():
            path = calibration.checked_relative_file(directory, filename)
            if calibration.digest_file(path) != digest:
                raise ValueError("Cargo observation evidence changed")
            paths.append(path)
    validate_matrix(builds)
    return definitions, builds, paths


def exact_batches(run, case_id):
    batches = sorted((b for b in run["batches"] if b["case_id"] == case_id), key=lambda b: b["round"])
    rounds = run["experiment"]["protocol"]["rounds"]
    repeats = run["experiment"]["protocol"]["samples_per_batch"]
    if [b["round"] for b in batches] != list(range(rounds)):
        return None
    for batch in batches:
        response = batch.get("response") or {}
        samples = response.get("samples_ns", [])
        if (batch["status"] != "ok" or (response.get("correctness") or {}).get("exact") is not True
                or len(samples) != repeats or any(type(t) is not int or t <= 0 for t in samples)):
            return None
    return batches


def aggregate_pair(baseline, candidate, comparison, eligible):
    """Descriptive matched-round ratios on complete, independently qualified support."""
    cases = []
    totals = {side: {"component_samples": 0, "time_ns": 0} for side in ("baseline", "candidate")}
    compared = {case["case_id"]: case for case in comparison["cases"]}
    for case in baseline["experiment"]["cases"]:
        case_id = case["id"]
        left, right = exact_batches(baseline, case_id), exact_batches(candidate, case_id)
        admitted = (case_id in eligible and left is not None and right is not None
                    and compared.get(case_id, {}).get("verdict") in VALID_VERDICTS)
        row = {"case_id": case_id, "bundle_id": case["input"]["provenance"]["prepared_asset_id"].rsplit("-", 1)[0],
               "same_success": admitted, "harness": compared.get(case_id),
               "baseline_statuses": dict(Counter(b["status"] for b in baseline["batches"] if b["case_id"] == case_id)),
               "candidate_statuses": dict(Counter(b["status"] for b in candidate["batches"] if b["case_id"] == case_id))}
        if admitted:
            ratios = []
            for a, b in zip(left, right):
                ratios.append((sum(a["response"]["samples_ns"]) / len(a["response"]["samples_ns"])) /
                              (sum(b["response"]["samples_ns"]) / len(b["response"]["samples_ns"])))
            row["paired_round_speedups"] = ratios
            row["geometric_mean_speedup"] = math.exp(sum(math.log(r) for r in ratios) / len(ratios))
            image = case["image"]
            samples = image["width"] * image["height"] * image["components"]
            row["totals"] = {}
            for side, batches in (("baseline", left), ("candidate", right)):
                values = {"component_samples": samples * sum(len(b["response"]["samples_ns"]) for b in batches),
                          "time_ns": sum(sum(b["response"]["samples_ns"]) for b in batches)}
                row["totals"][side] = values
                for key, value in values.items():
                    totals[side][key] += value
        cases.append(row)
    ratios = [row["geometric_mean_speedup"] for row in cases if row["same_success"]]
    for values in totals.values():
        values["component_samples_per_second"] = (values["component_samples"] * 1e9 / values["time_ns"]
                                                    if values["time_ns"] else None)
    return {"harness_verdict": comparison["verdict"], "harness_reason": comparison["reason"],
            "cases": cases, "same_success_cases": len(ratios), "total_cases": len(cases),
            "equally_weighted_geometric_mean_speedup": math.exp(sum(map(math.log, ratios)) / len(ratios)) if ratios else None,
            "totals": totals}


def compare_streams(assets, exports):
    return [{"asset_id": asset["id"], "variants": {
        name: ("baseline_missing" if asset["id"] not in exports["release"] else
               "candidate_missing" if asset["id"] not in exports[name] else
               "identical" if exports[name][asset["id"]]["sha256"] == exports["release"][asset["id"]]["sha256"] else "hash_mismatch")
        for name in VARIANTS}} for asset in assets]


def invoke(benchmark, arguments, log, failures):
    with log.open("x") as stream:
        result = subprocess.run([str(benchmark), *map(str, arguments)], stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode not in (0, 2, 3, 4):
        failures.append({"stage": log.stem, "returncode": result.returncode, "log": str(log)})
    return result.returncode


def verify_decode(benchmark, assets, prepared_digest, streams, worker, output, failures, common=False):
    if not assets:
        return set()
    experiment = (calibration.build_decode_experiment if common else verification.decode_experiment)(assets, prepared_digest, streams)
    experiment["environment_tags"] = {"journey": "verification-only-no-timing-claims"}
    path = output.with_suffix(".json")
    calibration.write_new(path, experiment)
    invoke(benchmark, ["run", path, worker, output], output.with_suffix(".log"), failures)
    run_path = output / "run.json"
    if not run_path.is_file():
        failures.append({"stage": output.name, "disposition": "incomplete_verification"})
        return set()
    run = json.loads(run_path.read_text())
    return {a["id"] for a in assets if exact_batches(run, a["id"] + "-decode") is not None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("benchmark", "prepared", "selection", "common-streams", "store", "output", *VARIANTS):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--bundle", action="append", required=True)
    args = parser.parse_args()
    try:
        store = args.store.resolve(strict=True)
        prepared = store_file(store, args.prepared)
        common_path = store_file(store, args.common_streams)
        output = calibration.new_store_child(store, args.output)
        if calibration.git("status", "--porcelain", "--untracked-files=normal"):
            raise ValueError("qualification requires a clean committed benchmark candidate")
        revision = calibration.git("rev-parse", "HEAD")
        document, all_assets, prepared_digest = calibration.load_prepared(prepared, args.selection)
        assets = select_bundles(all_assets, args.bundle)
        streams = load_common(common_path, assets, store)
        definitions, builds, identity_paths = load_workers({name: getattr(args, name.replace("-", "_")) for name in VARIANTS})
        identity_paths += [Path(__file__), Path(calibration.__file__), Path(verification.__file__), args.benchmark,
                           args.selection, prepared, common_path]
        identity_paths += [a["raw_path"] for a in assets] + [row["path"] for row in streams.values()]
        identities = {str(path): calibration.digest_file(path) for path in identity_paths}
        output.mkdir()
        summary = {"schema_version": 1, "complete": False, "orchestration_revision": revision,
                   "selection_sha256": document["provenance"]["source_lock"]["sha256"],
                   "prepared_manifest_sha256": prepared_digest, "bundles": args.bundle,
                   "identities_at_start": identities, "builds": builds, "failures": [], "pairs": {},
                   "interpretation": "Descriptive matched-round speedups on complete same-success support only. "
                   "Each acquisition retains PAN16/RGB8/MS16/RGB16. Equally weighted geometric means and "
                   "total component samples / total time describe different weightings. Coverage is separate; "
                   "unsupported, newly successful or unverified cases cannot establish speed improvement. "
                   "Harness verdicts retain conservative uncertainty; aggregate speedups have no confidence interval. "
                   "Exports and separate verification are excluded from timing claims."}
        failures = summary["failures"]
        try:
            for child in ("inputs", "pairs", "exports", "verification", "evidence"):
                (output / child).mkdir()
            for name, build in builds.items():
                retained = output / "evidence" / name
                retained.mkdir()
                source = definitions[name][0].parent
                for filename in ("build-provenance.json", *build["build_observations"]["evidence_sha256"]):
                    shutil.copyfile(source / filename, retained / filename)
            exports, verified = {}, {}
            for name in VARIANTS:
                destination = output / "exports" / name
                destination.mkdir()
                (destination / "inputs").mkdir()
                (destination / "streams").mkdir()
                export_failures = []
                exports[name] = verification.export_streams(assets, prepared_digest,
                    Path(definitions[name][1]["executable"]), destination, export_failures)
                failures.extend({"variant": name, **row} for row in export_failures if row["disposition"] != "unsupported")
                calibration.write_new(destination / "exports.json", {"streams": {key: {**row, "path": str(row["path"])}
                    for key, row in exports[name].items()}, "outcomes": export_failures})
                retained = [a for a in assets if a["id"] in exports[name]]
                checks = []
                for decoder in (name, "openjpeg"):
                    checks.append(verify_decode(args.benchmark, retained, prepared_digest, exports[name],
                        definitions[decoder][0], output / "verification" / f"{name}-{decoder}", failures))
                verified[name] = checks[0] & checks[1]
                for asset in retained:
                    if asset["id"] not in verified[name]:
                        failures.append({"variant": name, "asset_id": asset["id"], "stage": "independent_decode"})
            common_verified = verify_decode(args.benchmark, assets, prepared_digest, streams,
                definitions["openjpeg"][0], output / "verification" / "common-openjpeg", failures, common=True)
            for asset in assets:
                if asset["id"] not in common_verified:
                    failures.append({"stage": "common_independent_decode", "asset_id": asset["id"]})
            summary["stream_identity"] = compare_streams(assets, exports)
            summary["verified_exports"] = {name: sorted(ids) for name, ids in verified.items()}
            summary["common_independently_verified"] = sorted(common_verified)
            for row in summary["stream_identity"]:
                if "hash_mismatch" in row["variants"].values():
                    failures.append({"stage": "stream_identity", **row})
            for operation, experiment in (("encode", calibration.build_encode_experiment(assets, prepared_digest)),
                    ("decode", calibration.build_decode_experiment(assets, prepared_digest, streams))):
                experiment_path = output / "inputs" / f"{operation}.json"
                calibration.write_new(experiment_path, experiment)
                for name in tuple(VARIANTS)[1:]:
                    pair = output / "pairs" / f"{name}-{operation}"
                    invoke(args.benchmark, ["pair", experiment_path, definitions["release"][0], definitions[name][0], pair],
                           pair.with_suffix(".log"), failures)
                    expected = [pair / side / "run.json" for side in ("baseline", "candidate")]
                    expected.append(pair / "comparison.json")
                    if not all(path.is_file() for path in expected):
                        failures.append({"stage": pair.name, "disposition": "incomplete_pair"})
                        continue
                    baseline, candidate, comparison = [json.loads(path.read_text()) for path in expected]
                    if any(batch["status"] not in ("ok", "unsupported")
                           for run in (baseline, candidate) for batch in run["batches"]):
                        failures.append({"stage": pair.name, "disposition": "non_success_other_than_unsupported"})
                    eligible = (verified["release"] & verified[name] &
                                {row["asset_id"] for row in summary["stream_identity"] if row["variants"][name] == "identical"}
                                if operation == "encode" else common_verified)
                    qualified = aggregate_pair(baseline, candidate, comparison, {asset_id + "-" + operation for asset_id in eligible})
                    qualified["acquisitions"] = {}
                    for bundle in args.bundle:
                        ids = {a["id"] + "-" + operation for a in assets if a["bundle_id"] == bundle and a["id"] in eligible}
                        group_baseline = {**baseline, "experiment": {**baseline["experiment"], "cases": [
                            case for case in baseline["experiment"]["cases"]
                            if case["input"]["provenance"]["prepared_asset_id"].rsplit("-", 1)[0] == bundle]}}
                        qualified["acquisitions"][bundle] = aggregate_pair(group_baseline, candidate, comparison, ids)
                    qualified["records_sha256"] = {str(path.relative_to(output)): calibration.digest_file(path) for path in expected}
                    summary["pairs"][pair.name] = qualified
            for records in exports.values():
                for row in records.values():
                    if calibration.digest_file(row["path"]) != row["sha256"]:
                        failures.append({"stage": "export_identity", "disposition": "changed"})
        except (ValueError, KeyError, OSError, RuntimeError, TypeError, subprocess.SubprocessError) as error:
            failures.append({"stage": "execution", "detail": str(error)})
        summary["orchestration_revision_at_completion"] = calibration.git("rev-parse", "HEAD")
        changed = [path for path, digest in identities.items()
                   if not Path(path).is_file() or calibration.digest_file(Path(path)) != digest]
        if (changed or revision != summary["orchestration_revision_at_completion"]
                or calibration.git("status", "--porcelain", "--untracked-files=normal")):
            failures.append({"stage": "identity", "changed_paths": changed})
        summary["complete"] = not failures and len(summary["pairs"]) == 6
        summary["timing_claims_admitted"] = summary["complete"] and any(
            pair["same_success_cases"] > 0 for pair in summary["pairs"].values())
        summary["builds_qualified_on_common_support"] = summary["complete"] and all(
            pair["same_success_cases"] > 0 for pair in summary["pairs"].values())
        summary["global_speed_claim"] = False
        calibration.write_new(output / "worker-build-qualification.json", summary)
        print(json.dumps({"complete": summary["complete"], "pairs": len(summary["pairs"]), "failures": len(failures)}))
        return 0 if summary["complete"] else 4
    except (ValueError, KeyError, OSError, RuntimeError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"build qualification failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
