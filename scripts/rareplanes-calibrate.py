#!/usr/bin/env python3
"""Run the bounded RarePlanes full-location lossless calibration."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
BUNDLES = ("30_104001002394E000", "47_104001001D2C7A00")
PRODUCTS = {
    "PAN16": (1, 16, True),
    "RGB8": (3, 8, True),
    "MS16": (8, 16, True),
    "RGB16": (3, 16, True),
}
PROTOCOL = {
    "rounds": 5,
    "samples_per_batch": 1,
    "warmup": 0,
    "timeout_ms": 120_000,
    "boundary": "codec_operation",
    "context_policy": "fresh_process_per_batch",
    "cache_policy": "warm_input",
    "practical_relative_threshold": 0.05,
}


def digest_file(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def checked_relative_file(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError("asset path must be relative and contained")
    path = root
    for part in relative.parts:
        path /= part
        if path.is_symlink():
            raise ValueError("symlink asset paths are not supported")
    if not path.is_file():
        raise ValueError("asset is not a regular file")
    return path


def new_store_child(store, requested):
    requested = requested.absolute()
    if ".." in requested.parts:
        raise ValueError("output must not contain parent traversal")
    if requested.is_symlink():
        raise ValueError("output must not be a symlink")
    output = requested.resolve(strict=False)
    if output.parent != store:
        raise ValueError("output must be a direct child of the approved store")
    if output.exists():
        raise ValueError("output must be a new directory")
    return output


def validate_digest(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")


def load_prepared(path):
    path = path.resolve(strict=True)
    if path.is_symlink() or not path.is_file():
        raise ValueError("prepared record must be a regular file")
    document = json.loads(path.read_text())
    if document.get("schema_version") != 1 or not isinstance(document.get("provenance"), dict):
        raise ValueError("prepared record needs schema_version 1 and provenance")
    rows = document.get("assets")
    if not isinstance(rows, list) or len(rows) != len(BUNDLES) * len(PRODUCTS):
        raise ValueError("prepared record must contain the complete two-bundle product matrix")
    assets = []
    seen = set()
    for row in rows:
        required = {
            "id", "bundle_id", "product", "path", "sha256", "bytes", "image",
            "source_path", "source_sha256", "band_indices", "statistics",
        }
        if not isinstance(row, dict) or not required <= row.keys():
            raise ValueError("prepared asset is missing required identity fields")
        key = (row["bundle_id"], row["product"])
        if key in seen or row["bundle_id"] not in BUNDLES or row["product"] not in PRODUCTS:
            raise ValueError("prepared asset has a duplicate or unexpected bundle/product")
        seen.add(key)
        if row["id"] != f"{row['bundle_id']}-{row['product']}":
            raise ValueError("prepared asset id does not match its bundle and product")
        components, precision, supported = PRODUCTS[row["product"]]
        image = row["image"]
        if not isinstance(image, dict) or set(image) != {"width", "height", "components", "precision", "signed"}:
            raise ValueError("prepared image declaration is malformed")
        if (not isinstance(image["width"], int) or image["width"] <= 0
                or not isinstance(image["height"], int) or image["height"] <= 0
                or image["components"] != components or image["precision"] != precision
                or image["signed"] is not False):
            raise ValueError("prepared image declaration does not match its product")
        expected_bytes = image["width"] * image["height"] * components * (1 if precision <= 8 else 2)
        if row["bytes"] != expected_bytes:
            raise ValueError("prepared asset byte count does not match its image")
        validate_digest(row["sha256"], "prepared asset sha256")
        validate_digest(row["source_sha256"], "prepared source_sha256")
        if (not isinstance(row["band_indices"], list)
                or len(row["band_indices"]) != components
                or not isinstance(row["statistics"], (dict, list))):
            raise ValueError("prepared band identity or statistics are malformed")
        raw = checked_relative_file(path.parent, row["path"])
        if raw.stat().st_size != row["bytes"] or digest_file(raw) != row["sha256"]:
            raise ValueError(f"prepared asset integrity mismatch: {row['id']}")
        item = dict(row)
        item["raw_path"] = raw
        item["supported"] = supported
        assets.append(item)
    if seen != {(bundle, product) for bundle in BUNDLES for product in PRODUCTS}:
        raise ValueError("prepared record is missing a selected bundle/product")
    assets.sort(key=lambda item: (BUNDLES.index(item["bundle_id"]), tuple(PRODUCTS).index(item["product"])))
    return document, assets, digest_file(path)


def asset_provenance(asset, prepared_sha256):
    return {
        "bundle_id": asset["bundle_id"],
        "product": asset["product"],
        "prepared_asset_id": asset["id"],
        "prepared_manifest_sha256": prepared_sha256,
        "prepared_sha256": asset["sha256"],
        "source_sha256": asset["source_sha256"],
    }


def output_semantics(image):
    return {
        "colour": "native",
        "layout": "interleaved",
        "container": "j2k",
        "lossless": True,
        "reduction": 0,
        "region": None,
        "image": image,
        "minimum_psnr_db": None,
    }


def build_encode_experiment(assets, prepared_sha256):
    cases = []
    for asset in assets:
        if not asset["supported"]:
            continue
        image = asset["image"]
        cases.append({
            "id": asset["id"] + "-encode",
            "input": {
                "path": str(asset["raw_path"]),
                "sha256": asset["sha256"],
                "provenance": asset_provenance(asset, prepared_sha256),
            },
            "reference": None,
            "image": image,
            "operation": "encode",
            "settings": {"coding": "classic", "decomposition_levels": 2},
            "threads": 1,
            "output": output_semantics(image),
        })
    return {
        "schema_version": 1,
        "name": "rareplanes-full-location-classic-lossless-encode",
        "protocol": dict(PROTOCOL),
        "environment_tags": {"calibration": "rareplanes-full-location-v1"},
        "cases": cases,
    }


def build_decode_experiment(assets, prepared_sha256, streams):
    cases = []
    for asset in assets:
        if not asset["supported"]:
            continue
        stream = streams[asset["id"]]
        image = asset["image"]
        cases.append({
            "id": asset["id"] + "-decode",
            "input": {
                "path": str(stream["path"]),
                "sha256": stream["sha256"],
                "provenance": {
                    "generator": "OpenJPEG opj_compress",
                    "generator_sha256": stream["generator_sha256"],
                    "generator_arguments_sha256": stream["arguments_sha256"],
                    "prepared_asset_id": asset["id"],
                    "prepared_sha256": asset["sha256"],
                },
            },
            "reference": {
                "path": str(asset["raw_path"]),
                "sha256": asset["sha256"],
                "provenance": asset_provenance(asset, prepared_sha256),
            },
            "image": image,
            "operation": "decode",
            "settings": {"coding": "classic"},
            "threads": 1,
            "output": output_semantics(image),
        })
    return {
        "schema_version": 1,
        "name": "rareplanes-full-location-shared-openjpeg-lossless-decode",
        "protocol": dict(PROTOCOL),
        "environment_tags": {"calibration": "rareplanes-full-location-v1"},
        "cases": cases,
    }


def parse_msi_dump(text, image):
    """Read factual OpenJPEG main-header fields; do not infer spectral semantics.

    The workers separately reject tile coding overrides before decode. opj_dump
    reports main-header defaults, so this observation alone does not prove their
    absence or validate entropy data.
    """
    def section(label):
        matches = list(re.finditer(re.escape(label) + r"\s*\{", text))
        if len(matches) != 1:
            raise ValueError(f"independent dump requires one {label}")
        start = matches[0].end()
        depth = 1
        for end in range(start, len(text)):
            depth += (text[end] == "{") - (text[end] == "}")
            if depth == 0:
                return text[start:end]
        raise ValueError("truncated independent dump")

    def integer(body, key):
        values = re.findall(r"(?<![\w])" + re.escape(key) + r"=(-?\d+)(?![\w])", body)
        if len(values) != 1:
            raise ValueError(f"independent dump requires one {key}")
        return int(values[0])

    pixels = section("Image info")
    coding = section("Codestream info from main header:")
    expected = {"x0": 0, "y0": 0, "x1": image["width"], "y1": image["height"], "numcomps": 8}
    if image["components"] != 8 or image["precision"] != 16 or image["signed"]:
        raise ValueError("independent MSI inspection requires eight unsigned16 components")
    if any(integer(pixels, key) != value for key, value in expected.items()):
        raise ValueError("independent image geometry/count differs")
    image_components = re.findall(r"component (\d+)\s*\{([^{}]*)\}", pixels)
    coding_components = re.findall(r"comp (\d+)\s*\{([^{}]*)\}", coding)
    if ([int(n) for n, _ in image_components] != list(range(8))
            or [int(n) for n, _ in coding_components] != list(range(8))):
        raise ValueError("independent dump requires eight ordered component records")
    tile = {"tx0": 0, "ty0": 0, "tdx": image["width"], "tdy": image["height"],
            "tw": 1, "th": 1, "prg": 0, "numlayers": 1, "mct": 0}
    if any(integer(coding, key) != value for key, value in tile.items()):
        raise ValueError("independent tile/MCT/profile differs")
    components = []
    for (index, geometry), (_, style) in zip(image_components, coding_components):
        fields = {key: integer(geometry, key) for key in ("dx", "dy", "prec", "sgnd")}
        transforms = {key: integer(style, key) for key in
                      ("numresolutions", "qmfbid", "qntsty", "cblksty", "roishift")}
        if fields != {"dx": 1, "dy": 1, "prec": 16, "sgnd": 0} or transforms != {
                "numresolutions": 3, "qmfbid": 1, "qntsty": 0, "cblksty": 0, "roishift": 0}:
            raise ValueError("independent component precision/sampling/coding differs")
        components.append({"index": int(index), "width": image["width"], "height": image["height"],
                           "precision": 16, "signed": False, "dx": 1, "dy": 1,
                           "decomposition_levels": 2, "reversible": True})
    return {"components": components, "tiles": 1, "mct": False, "layers": 1,
            "progression": "LRCP", "geometry_basis": "zero image origin and unit component sampling",
            "scope": "independent main-header observation; worker admission separately excludes overrides"}


def inspect_msi_stream(stream, image, inspector, output):
    """Run the independently installed CLI outside every operation timer."""
    inspector = inspector.resolve(strict=True)
    tool_digest = digest_file(inspector)
    stream_digest = digest_file(stream)
    help_result = subprocess.run([str(inspector), "-h"], capture_output=True, text=True, timeout=120)
    help_text = help_result.stdout + help_result.stderr
    version = re.search(r"compiled against openjp2 library v([^\s.]+(?:\.[^\s.]+)*)", help_text)
    if not version:
        raise RuntimeError("opj_dump did not identify its library version")
    help_path = output.with_suffix(".opj-dump-help.log")
    log_path = output.with_suffix(".opj-dump.log")
    with help_path.open("x") as log:
        log.write(help_text)
    result = subprocess.run([str(inspector), "-i", str(stream)], capture_output=True, text=True, timeout=120)
    with log_path.open("x") as log:
        log.write(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("independent opj_dump failed; retained inspection log")
    observed = parse_msi_dump(result.stdout, image)
    if tool_digest != digest_file(inspector) or stream_digest != digest_file(stream):
        raise RuntimeError("independent inspection tool or codestream changed")
    return {"tool": "OpenJPEG opj_dump", "tool_sha256": tool_digest,
            "openjp2_version": version.group(1).rstrip("."), "codestream_sha256": stream_digest,
            "raw_dump_sha256": digest_file(log_path), "tool_help_sha256": digest_file(help_path),
            "observed": observed}


def create_common_streams(assets, store, prepared_path, output, preparation_tool, compressor, inspector):
    compressor = compressor.resolve(strict=True)
    if not compressor.is_file():
        raise ValueError("opj_compress must be a regular file")
    generator_sha256 = digest_file(compressor)
    prepared_name = str(prepared_path.parent.relative_to(store))
    records = {}
    common = output / "common"
    common.mkdir()
    for asset in assets:
        if not asset["supported"]:
            continue
        # The corpus recipe deliberately permits only a direct child of its
        # approved store. RAWL makes OpenJPEG's little-endian interpretation
        # explicit; the prepared benchmark reference remains interleaved RAW.
        output_name = f"{output.name}-planar-{asset['id']}.rawl"
        planar = store / output_name
        prepare_command = [
            sys.executable, str(preparation_tool), "planar", "--store", str(store),
            "--prepared-name", prepared_name, "--asset-id", asset["id"],
            "--output-name", output_name,
        ]
        prepared = subprocess.run(prepare_command, capture_output=True, text=True)
        if prepared.returncode:
            raise RuntimeError(prepared.stderr or f"planar preparation failed for {asset['id']}")
        try:
            preparation_record = json.loads(prepared.stdout)
        except json.JSONDecodeError as error:
            raise RuntimeError("planar preparation did not return JSON identity") from error
        if not planar.is_file() or planar.is_symlink() or planar.stat().st_size != asset["bytes"]:
            raise RuntimeError(f"planar derivative is missing or has the wrong size: {asset['id']}")
        planar_sha256 = digest_file(planar)
        image = asset["image"]
        arguments = [
            "-i", str(planar), "-o", str(common / (asset["id"] + ".j2k")),
            "-F", f"{image['width']},{image['height']},{image['components']},{image['precision']},u",
            "-n", "3", "-t", f"{image['width']},{image['height']}", "-p", "LRCP",
            "-r", "1", "-mct", "0", "-threads", "1",
        ]
        stream = common / (asset["id"] + ".j2k")
        compressed = subprocess.run([str(compressor), *arguments], capture_output=True, text=True)
        if compressed.returncode:
            raise RuntimeError(compressed.stderr or f"common codestream preparation failed for {asset['id']}")
        if not stream.is_file() or stream.is_symlink() or stream.stat().st_size == 0:
            raise RuntimeError(f"common codestream is missing or empty: {asset['id']}")
        records[asset["id"]] = {
            "path": stream,
            "sha256": digest_file(stream),
            "bytes": stream.stat().st_size,
            "generator_sha256": generator_sha256,
            "arguments": arguments,
            "arguments_sha256": hashlib.sha256(json.dumps(arguments, separators=(",", ":")).encode()).hexdigest(),
            "planar_sha256": planar_sha256,
            "preparation_tool_sha256": digest_file(preparation_tool),
            "preparation_record": preparation_record,
        }
        if image["components"] == 8:
            records[asset["id"]]["independent_inspection"] = inspect_msi_stream(
                stream, image, inspector, common / asset["id"])
    runtime_record = {
        "schema_version": 1,
        "generator": "OpenJPEG opj_compress",
        "generator_sha256": generator_sha256,
        "preparation_tool_sha256": digest_file(preparation_tool),
        "streams": {
            key: {name: (str(value) if isinstance(value, Path) else value) for name, value in record.items()}
            for key, record in records.items()
        },
    }
    write_new(output / "inputs" / "common-codestreams.json", runtime_record)
    return records


def sanitise_detail(value, roots):
    if value is None:
        return None
    text = str(value)
    for root in sorted((str(root) for root in roots), key=len, reverse=True):
        text = text.replace(root, "<authorised-store>")
    return text


def public_machine(machine):
    fields = ("os", "architecture", "kernel", "cpu", "logical_cpus", "affinity", "governors", "environment_sha256")
    return {key: machine[key] for key in fields if key in machine}


def public_build_provenance(path):
    document = json.loads(path.read_text())
    lock = tomllib.loads(document["resolved_worker_lock"])
    dependencies = [
        {key: package[key] for key in ("name", "version", "source", "checksum") if key in package}
        for package in lock.get("package", [])
    ]
    fields = (
        "emuella_revision", "emuella_tree", "rustc", "cargo", "cc", "openjpeg_pkg_config",
        "profile", "features", "build_environment", "source_sha256", "resolved_worker_lock_sha256",
    )
    result = {key: document[key] for key in fields if key in document}
    result["dependencies"] = dependencies
    result["record_sha256"] = digest_file(path)
    return result


def summarise_run(run, raw_bytes_by_asset, roots):
    cases = {case["id"]: case for case in run["experiment"]["cases"]}
    grouped = {case_id: [] for case_id in cases}
    for batch in run["batches"]:
        grouped.setdefault(batch["case_id"], []).append(batch)
    observations = []
    for case_id, case in cases.items():
        batches = grouped.get(case_id, [])
        statuses = Counter(batch["status"] for batch in batches)
        ok = [batch for batch in batches if batch["status"] == "ok" and batch.get("response")]
        times = [sum(batch["response"]["samples_ns"]) / len(batch["response"]["samples_ns"]) for batch in ok]
        sizes = [batch["response"]["output_bytes"] for batch in ok]
        rss = [batch["response"]["peak_rss_bytes"] for batch in ok if batch["response"].get("peak_rss_bytes") is not None]
        asset_id = case_id.rsplit("-", 1)[0]
        raw_bytes = raw_bytes_by_asset[asset_id]
        encoded_bytes = (sum(sizes) / len(sizes)) if case["operation"] == "encode" and sizes else (
            Path(case["input"]["path"]).stat().st_size if case["operation"] == "decode" else None)
        image = case["image"]
        spatial_pixels = image["width"] * image["height"]
        sample_values = spatial_pixels * image["components"]
        mean_ns = sum(times) / len(times) if times else None
        exact = bool(ok) and all(batch["response"]["correctness"]["exact"] for batch in ok)
        complete = len(ok) == run["experiment"]["protocol"]["rounds"] and set(statuses) == {"ok"} and exact
        expected_rounds = run["experiment"]["protocol"]["rounds"]
        if complete:
            disposition = "completed_exact"
        elif len(batches) == expected_rounds and set(statuses) == {"unsupported"}:
            disposition = "observed_unsupported"
        elif len(batches) == expected_rounds and not ok:
            disposition = "observed_non_success"
        else:
            disposition = "incomplete_or_failed"
        observations.append({
            "case_id": case_id,
            "operation": case["operation"],
            "input_sha256": case["input"]["sha256"],
            "reference_sha256": case.get("reference", {}).get("sha256") if case.get("reference") else None,
            "image": image,
            "settings": case["settings"],
            "threads": case["threads"],
            "disposition": disposition,
            "statuses": dict(sorted(statuses.items())),
            "measured_time_ns": ({"mean": mean_ns, "minimum": min(times), "maximum": max(times)} if times else None),
            "spatial_pixels_per_second": spatial_pixels * 1_000_000_000 / mean_ns if mean_ns else None,
            "component_samples_per_second": sample_values * 1_000_000_000 / mean_ns if mean_ns else None,
            "bits_per_spatial_pixel": encoded_bytes * 8 / spatial_pixels if encoded_bytes else None,
            "bits_per_component_sample": encoded_bytes * 8 / sample_values if encoded_bytes else None,
            "sample_values_per_second": sample_values * 1_000_000_000 / mean_ns if mean_ns else None,
            "operations_per_second": 1_000_000_000 / mean_ns if mean_ns else None,
            "measured_output_bytes": ({"mean": sum(sizes) / len(sizes), "minimum": min(sizes), "maximum": max(sizes)} if sizes else None),
            "raw_storage_bytes": raw_bytes,
            "encoded_bytes": encoded_bytes,
            "compression_ratio_raw_over_encoded": raw_bytes / encoded_bytes if encoded_bytes else None,
            "exact": exact if ok else None,
            "peak_rss_bytes": max(rss) if rss else None,
            "rss_observed_batches": len(rss),
            "encode_profiles": [
                json.loads(value) for value in sorted({
                    json.dumps(batch["response"].get("diagnostics", {}).get("encode_profile"), sort_keys=True)
                    for batch in ok if batch["response"].get("diagnostics", {}).get("encode_profile")
                })
            ],
            "non_success": [
                {"round": batch["round"], "status": batch["status"],
                 "detail": sanitise_detail(batch.get("detail"), roots)}
                for batch in batches if batch["status"] != "ok"
            ],
        })
    worker = run["worker"]
    artefacts = [
        {"name": Path(path).name, "sha256": value}
        for path, value in sorted(worker.get("artefact_sha256", {}).items())
    ]
    machine_json = json.dumps(run["machine"], sort_keys=True, separators=(",", ":")).encode()
    return {
        "run_id": run["run_id"],
        "run_sha256": run.get("_run_sha256"),
        "worker": {
            "implementation": worker["definition"]["implementation"],
            "source_identity": worker["definition"]["source_identity"],
            "executable_sha256": worker["executable_sha256"],
            "artefacts": artefacts,
        },
        "harness_version": run["harness_version"],
        "harness_sha256": run["harness_sha256"],
        "machine_identity_sha256": hashlib.sha256(machine_json).hexdigest(),
        "machine": public_machine(run["machine"]),
        "protocol": run["experiment"]["protocol"],
        "measurement_units": {
            "time": "nanoseconds", "size": "bytes", "peak_rss": "bytes",
            "rss_scope": "whole worker process including setup and verification",
            "spatial_pixel": "one image position across all bands",
            "component_sample": "one scalar band value",
            "sample_values_per_second": "alias of component_samples_per_second",
        },
        "observations": observations,
    }


def unsupported_observations(assets):
    return [
        {
            "asset_id": asset["id"],
            "bundle_id": asset["bundle_id"],
            "product": asset["product"],
            "input_sha256": asset["sha256"],
            "source_sha256": asset["source_sha256"],
            "image": asset["image"],
            "disposition": "not_submitted",
            "workers": {"emuella": "unsupported_by_admission", "openjpeg": "unsupported_by_admission"},
            "reason": "The native worker contract admits one or three uniformly sampled components; MS16 has eight.",
        }
        for asset in assets if not asset["supported"]
    ]


def make_summary(run_paths, assets, prepared_sha256, source_identity, dirty, roots,
                 build_provenance=None, streams=None, invocation_failures=None):
    raw_bytes = {asset["id"]: asset["bytes"] for asset in assets}
    runs = []
    for run_path in run_paths:
        document = json.loads(run_path.read_text())
        document["_run_sha256"] = digest_file(run_path)
        runs.append(summarise_run(document, raw_bytes, roots))
    return {
        "schema_version": 1,
        "method": "Five fresh-process rounds, one measured operation per batch, no warmup; input is loaded before each timed native codec operation.",
        "interpretation": "Factual full-location observations only; encoder MCT policies differ, so no universal speed or compression ranking is made.",
        "orchestration": source_identity,
        "provisional_dirty_source": dirty,
        "prepared_manifest_sha256": prepared_sha256,
        "build_provenance": build_provenance,
        "shared_codestreams": [
            {
                "asset_id": asset_id,
                "sha256": record["sha256"],
                "bytes": record["bytes"],
                "generator": "OpenJPEG opj_compress",
                "generator_sha256": record["generator_sha256"],
                "planar_sha256": record["planar_sha256"],
                "preparation_tool_sha256": record["preparation_tool_sha256"],
                "preparation_record_sha256": hashlib.sha256(json.dumps(
                    record["preparation_record"], sort_keys=True, separators=(",", ":")
                ).encode()).hexdigest(),
                "independent_inspection": record.get("independent_inspection"),
                "profile": {
                    "coding": "classic", "decomposition_levels": 2, "tiles": 1,
                    "progression": "LRCP", "layers": 1, "mct": False, "threads": 1,
                },
            }
            for asset_id, record in sorted((streams or {}).items())
        ],
        "inputs": [
            {
                "asset_id": asset["id"], "bundle_id": asset["bundle_id"], "product": asset["product"],
                "prepared_sha256": asset["sha256"], "source_sha256": asset["source_sha256"],
                "bytes": asset["bytes"], "image": asset["image"], "band_indices": asset["band_indices"],
            }
            for asset in assets
        ],
        "unsupported": unsupported_observations(assets),
        "invocation_failures": invocation_failures or [],
        "runs": runs,
    }


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def invoke_run(benchmark, experiment, worker, output):
    process = subprocess.run([str(benchmark), "run", str(experiment), str(worker), str(output)],
                             capture_output=True, text=True)
    if process.returncode not in (0, 4):
        return {"name": output.name, "returncode": process.returncode,
                "stderr": process.stderr.strip() or "benchmark command failed"}
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--workers", type=Path, required=True)
    parser.add_argument("--build-provenance", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--preparation-tool", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True, help="approved RarePlanes artefact store")
    parser.add_argument("--output", type=Path, required=True, help="new run directory within --store")
    parser.add_argument("--opj-compress", type=Path, required=True)
    parser.add_argument("--opj-dump", type=Path, required=True)
    parser.add_argument("--allow-dirty-probe", action="store_true")
    args = parser.parse_args()
    try:
        store = args.store.resolve(strict=True)
        prepared = args.prepared.resolve(strict=True)
        output = new_store_child(store, args.output)
        preparation_tool = args.preparation_tool.resolve(strict=True)
        benchmark = args.benchmark.resolve(strict=True)
        workers = args.workers.resolve(strict=True)
        build_provenance_path = args.build_provenance.resolve(strict=True)
        if not store.is_dir() or store.is_symlink():
            raise ValueError("store must be an existing real directory")
        prepared.relative_to(store)
        document, assets, prepared_sha256 = load_prepared(prepared)
        del document
        dirty = bool(git("status", "--porcelain", "--untracked-files=normal"))
        if dirty and not args.allow_dirty_probe:
            raise ValueError("calibration requires a clean committed benchmark candidate; use --allow-dirty-probe only for exploration")
        source_revision = git("rev-parse", "HEAD")
        source_script_sha256 = digest_file(Path(__file__))
        build_provenance = public_build_provenance(build_provenance_path)
        independent_tools = {path.resolve(strict=True): digest_file(path.resolve(strict=True))
                             for path in (args.opj_compress, args.opj_dump, preparation_tool)}
        output.mkdir(parents=False)
        (output / "inputs").mkdir()
        streams = create_common_streams(assets, store, prepared, output, preparation_tool, args.opj_compress, args.opj_dump)
        encode = build_encode_experiment(assets, prepared_sha256)
        decode = build_decode_experiment(assets, prepared_sha256, streams)
        encode_path = output / "inputs" / "encode.json"
        decode_path = output / "inputs" / "decode.json"
        write_new(encode_path, encode)
        write_new(decode_path, decode)
        run_specs = (
            ("emuella-encode", encode_path, workers / "emuella-worker.json"),
            ("openjpeg-encode", encode_path, workers / "openjpeg-worker.json"),
            ("emuella-common-decode", decode_path, workers / "emuella-worker.json"),
            ("openjpeg-common-decode", decode_path, workers / "openjpeg-worker.json"),
        )
        run_root = output / "runs"
        run_root.mkdir()
        failures = []
        for name, experiment, worker in run_specs:
            if not worker.is_file():
                failures.append({"name": name, "returncode": None, "stderr": "worker definition is missing"})
                continue
            failure = invoke_run(benchmark, experiment, worker, run_root / name)
            if failure:
                failure["stderr"] = sanitise_detail(failure["stderr"], (store, output))
                failures.append(failure)
        end_revision = git("rev-parse", "HEAD")
        end_script_sha256 = digest_file(Path(__file__))
        build_record_changed = build_provenance["record_sha256"] != digest_file(build_provenance_path)
        source_changed = source_revision != end_revision or source_script_sha256 != end_script_sha256
        if (load_prepared(prepared)[2] != prepared_sha256
                or any(digest_file(path) != digest for path, digest in independent_tools.items())
                or any(digest_file(record["path"]) != record["sha256"] for record in streams.values())):
            failures.append({"name": "input-stream-tool-identity", "returncode": None,
                             "stderr": "prepared input, common stream or independent tool changed during the run"})
        if source_changed:
            failures.append({
                "name": "orchestration-source-identity", "returncode": None,
                "stderr": "benchmark revision or orchestration script changed during the run",
            })
        if build_record_changed:
            failures.append({
                "name": "build-provenance-identity", "returncode": None,
                "stderr": "build provenance record changed during the run",
            })
        source_identity = {
            "revision_at_start": source_revision,
            "revision_at_completion": end_revision,
            "script_sha256_at_start": source_script_sha256,
            "script_sha256_at_completion": end_script_sha256,
            "changed_during_run": source_changed,
        }
        run_paths = sorted(run_root.glob("*/run.json"))
        summary = make_summary(run_paths, assets, prepared_sha256, source_identity, dirty,
                               (store, output), build_provenance, streams, failures)
        write_new(output / "rareplanes-calibration-summary.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        expected = len(run_specs)
        complete = len(run_paths) == expected and not failures and all(
            observation["disposition"] == "completed_exact"
            for run in summary["runs"] for observation in run["observations"]
        )
        return 0 if complete else 4
    except (ValueError, KeyError, OSError, json.JSONDecodeError, subprocess.CalledProcessError, RuntimeError) as error:
        parser.exit(1, f"calibration failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
