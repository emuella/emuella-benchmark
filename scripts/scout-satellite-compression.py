#!/usr/bin/env python3
"""Scout explicit OpenJPEG satellite profiles using CLI application journeys."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT = "94_104001000B823500"
HOLDOUT = "105_104001002F92BB00"
PRODUCTS = {"PAN16": (1, 16), "RGB8": (3, 8), "MS16": (8, 16), "RGB16": (3, 16)}
TRIALS = ("baseline", "rgb-mct", "block32x32", "block32x64", "bypass")


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def inside(store, path):
    path = Path(path).absolute()
    if path.is_symlink() or store not in path.resolve().parents:
        raise ValueError("input must be a regular file inside the authorised store")
    if not path.is_file():
        raise ValueError("required input is missing")
    return path.resolve()


def new_output(store, output):
    output = Path(output).absolute()
    if output.parent != store or output.is_symlink() or output.exists():
        raise ValueError("output must be a new direct child of the authorised store")
    if store == ROOT or ROOT in store.parents:
        raise ValueError("protected output cannot be inside the source checkout")
    output.mkdir()
    return output


def profiles(depths, trials):
    if not depths or len(set(depths)) != len(depths) or any(d not in range(2, 7) for d in depths):
        raise ValueError("choose unique decomposition depths from 2 to 6")
    if not trials or len(set(trials)) != len(trials) or any(t not in TRIALS for t in trials):
        raise ValueError("choose unique named trials")
    # Each call is an explicit selection, never a product of arbitrary settings.
    return [{"name": f"D{depth}-{trial}", "depth": depth, "trial": trial,
             "mct": int(trial == "rgb-mct"),
             "block": [32, 32] if trial == "block32x32" else [32, 64] if trial == "block32x64" else [64, 64],
             "style": int(trial == "bypass")}
            for depth in depths for trial in trials]


def format_raw(image):
    return f"{image['width']},{image['height']},{image['components']},{image['precision']},u"


def encode_args(tool, asset, profile, output):
    image = asset["image"]
    return [str(tool), "-i", asset["planar_path"], "-o", str(output), "-F", format_raw(image),
            "-n", str(profile["depth"] + 1), "-t", f"{image['width']},{image['height']}",
            "-p", "LRCP", "-r", "1", "-mct", str(profile["mct"]),
            "-b", ",".join(map(str, profile["block"])), "-M", str(profile["style"]), "-threads", "1"]


def verify_planar(raw, planar, image):
    """Compare complete prepared samples to planar samples with bounded memory."""
    components, width = image["components"], image["precision"] // 8
    pixels = image["width"] * image["height"]
    with raw.open("rb") as source, planar.open("rb") as derivative:
        for offset in range(0, pixels, 65536):
            count = min(65536, pixels - offset)
            packed = source.read(count * components * width)
            for component in range(components):
                derivative.seek((component * pixels + offset) * width)
                plane = derivative.read(count * width)
                for byte in range(width):
                    if packed[component * width + byte::components * width] != plane[byte::width]:
                        raise ValueError("planar derivative differs from prepared samples")


def load_inputs(store, prepared_path, common_path, sources_path, bundle, products):
    if bundle not in (DEVELOPMENT, HOLDOUT):
        raise ValueError("only the frozen development and holdout acquisitions are admitted")
    if not products or len(set(products)) != len(products) or any(p not in PRODUCTS for p in products):
        raise ValueError("choose unique supported products")
    prepared_path, common_path = inside(store, prepared_path), inside(store, common_path)
    prepared = json.loads(prepared_path.read_text())
    common = json.loads(common_path.read_text())
    sources = json.loads(sources_path.read_text())
    if any(record["schema_version"] != 1 for record in (prepared, common)):
        raise ValueError("unsupported input manifest version")
    prepared_sha, sources_sha = sha(prepared_path), sha(sources_path)
    if prepared["provenance"]["source_lock"]["sha256"] != sources_sha:
        raise ValueError("prepared source lock identity differs")
    locked = {entry["path"]: entry["sha256"] for entry in sources["assets"]}
    selected = []
    for product in products:
        matches = [a for a in prepared["assets"] if a["bundle_id"] == bundle and a["product"] == product]
        if len(matches) != 1:
            raise ValueError("selected product must appear exactly once")
        asset = dict(matches[0])
        image = asset["image"]
        if ((image["components"], image["precision"]) != PRODUCTS[product] or image["signed"]
                or min(image["width"], image["height"]) <= 0 or asset["id"] != f"{bundle}-{product}"):
            raise ValueError("prepared product geometry differs")
        expected_bytes = image["width"] * image["height"] * image["components"] * (image["precision"] // 8)
        raw = inside(store, prepared_path.parent / asset["path"])
        entry = common["streams"][asset["id"]]
        record = entry["preparation_record"]
        planar = inside(store, store / record["path"])
        arguments = entry["arguments"]
        if (len(arguments) % 2 or len(set(arguments[::2])) != len(arguments[::2])
                or hashlib.sha256(json.dumps(arguments, separators=(",", ":")).encode()).hexdigest()
                != entry["arguments_sha256"]):
            raise ValueError("common-stream argument identity differs")
        options = dict(zip(arguments[::2], arguments[1::2]))
        if (Path(options["-i"]).resolve() != planar or options["-F"] != format_raw(image)
                or record["asset_id"] != asset["id"] or record["schema_version"] != 1
                or record["layout"] != "packed component-planar little-endian unsigned"
                or record["prepared_sha256"] != prepared_sha
                or record["provenance"] != prepared["provenance"]
                or record["source_sha256"] != asset["sha256"]
                or locked.get(asset["source_path"]) != asset["source_sha256"]
                or record["sha256"] != entry["planar_sha256"]):
            raise ValueError("planar preparation lineage differs")
        if (asset["bytes"] != expected_bytes or raw.stat().st_size != expected_bytes
                or record["bytes"] != expected_bytes or planar.stat().st_size != expected_bytes
                or sha(raw) != asset["sha256"] or sha(planar) != entry["planar_sha256"]):
            raise ValueError("prepared or planar byte identity differs")
        verify_planar(raw, planar, image)
        asset.update(raw_path=str(raw), planar_path=str(planar), planar_sha256=entry["planar_sha256"],
                     preparation_record=record)
        selected.append(asset)
    return selected


def inspect_codestream(path, image, profile):
    """Check this deliberately narrow single-tile/part profile; no entropy parsing.

    Project-authored marker reader. Reject unknown markers and coding overrides
    rather than assuming a main-header observation applies to every tile-part.
    """
    observed = {}
    with path.open("rb") as stream:
        def read(count):
            result = stream.read(count)
            if len(result) != count:
                raise ValueError("truncated codestream structure")
            return result

        if read(2) != b"\xff\x4f":
            raise ValueError("expected raw codestream SOC")
        seen = set()
        while True:
            start = stream.tell()
            marker = read(2)
            length = int.from_bytes(read(2), "big")
            if length < 2 or length > 4096:
                raise ValueError("invalid or unsupported marker length")
            body = read(length - 2)
            if marker == b"\xff\x90":
                if len(body) != 8 or not {b"\xff\x51", b"\xff\x52", b"\xff\x5c"} <= seen:
                    raise ValueError("missing required main header or invalid SOT")
                tile, size, part, parts = struct.unpack(">HIBB", body)
                if tile != 0 or part != 0 or parts != 1 or size < 14 or read(2) != b"\xff\x93":
                    raise ValueError("expected one tile-part without header overrides")
                stream.seek(start + size)
                if read(2) != b"\xff\xd9" or stream.read(1):
                    raise ValueError("tile-part length or terminal EOC differs")
                break
            if marker in seen and marker != b"\xff\x64":
                raise ValueError("duplicate profile marker")
            seen.add(marker)
            if marker == b"\xff\x51":
                if len(body) != 36 + 3 * image["components"]:
                    raise ValueError("SIZ component count differs")
                fields = struct.unpack(">H8IH", body[:36])
                expected = (0, image["width"], image["height"], 0, 0,
                            image["width"], image["height"], 0, 0, image["components"])
                if fields != expected or body[36:] != bytes([image["precision"] - 1, 1, 1]) * image["components"]:
                    raise ValueError("SIZ geometry or component precision differs")
            elif marker == b"\xff\x52":
                block = [value.bit_length() - 3 for value in profile["block"]]
                expected = bytes([0, 0, 0, 1, profile["mct"], profile["depth"], *block, profile["style"], 1])
                if body != expected:
                    raise ValueError("COD differs from reversible fixed profile")
                observed = {"depth": profile["depth"], "block": profile["block"], "style": profile["style"],
                            "mct": bool(profile["mct"]), "reversible": True, "layers": 1,
                            "progression": "LRCP", "tiles": 1, "tile_parts": 1,
                            "precinct_exponents": [15, 15]}
            elif marker == b"\xff\x5c":
                if len(body) != 2 + 3 * profile["depth"] or body[0] & 31:
                    raise ValueError("QCD differs from reversible quantisation")
            elif marker != b"\xff\x64":
                raise ValueError("unsupported marker or component override")
    return observed


def process(command, log, timeout):
    with log.open("xb") as output:
        start = time.perf_counter_ns()
        try:
            result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
            status = "ok" if result.returncode == 0 else "process_failed"
            code = result.returncode
        except subprocess.TimeoutExpired:
            status, code = "timeout", None
        except OSError:
            status, code = "launch_failed", None
        elapsed = time.perf_counter_ns() - start
    return {"status": status, "exit_code": code, "wall_ns": elapsed, "arguments": command,
            "log": str(log), "log_sha256": sha(log), "measurement_boundary": "application_journey"}


def byte_result(path, expected_bytes=None, expected_sha=None):
    if not path.is_file() or path.is_symlink():
        return {"status": "missing", "bytes": None, "sha256": None, "exact": False}
    size, digest = path.stat().st_size, sha(path)
    return {"status": "present", "bytes": size, "sha256": digest,
            "exact": size == expected_bytes and digest == expected_sha if expected_sha else None}


def tool_identity(tool, output):
    tool = tool.resolve(strict=True)
    help_result = subprocess.run([str(tool), "-h"], capture_output=True, timeout=30)
    help_data = help_result.stdout + help_result.stderr
    with (output / f"{tool.name}-help.log").open("xb") as log:
        log.write(help_data)
    version = re.search(rb"compiled against openjp2 library v(\d+\.\d+\.\d+)", help_data)
    if not version:
        raise ValueError("tool does not identify its OpenJPEG library version")
    dependencies = subprocess.run(["ldd", str(tool)], capture_output=True, timeout=30)
    with (output / f"{tool.name}-ldd.log").open("xb") as log:
        log.write(dependencies.stdout + dependencies.stderr)
    if dependencies.returncode or b"not found" in dependencies.stdout:
        raise ValueError("could not resolve runtime library identities")
    libs = sorted({Path(p).resolve() for p in re.findall(r"(/\S+)\s+\(", dependencies.stdout.decode())})
    if not libs:
        raise ValueError("expected dynamically linked OpenJPEG tool")
    return {"path": str(tool), "sha256": sha(tool), "openjp2_version": version[1].decode(),
            "help_sha256": hashlib.sha256(help_data).hexdigest(),
            "runtime_libraries": {str(p): sha(p) for p in libs}}


def observe(asset, profile, number, tools, output, timeout, round_number=0):
    directory = output / f"{number:04d}-{asset['id']}-{profile['name']}"
    directory.mkdir()
    encoded, decoded = directory / "encoded.j2k", directory / "decoded.rawl"
    observation = {"asset_id": asset["id"], "profile": profile, "sequence": number,
                   "status": "failed", "exact": False, "round": round_number}
    observation["encode"] = process(encode_args(tools["compress"], asset, profile, encoded),
                                    directory / "encode.log", timeout)
    observation["codestream"] = byte_result(encoded)
    if observation["encode"]["status"] == "ok" and encoded.is_file():
        try:
            observation["observed_profile"] = inspect_codestream(encoded, asset["image"], profile)
            observation["profile_status"] = "ok"
        except (ValueError, OSError):
            observation["profile_status"] = "invalid_structure"
        observation["decode"] = process([str(tools["decompress"]), "-i", str(encoded), "-o", str(decoded),
                                          "-threads", "1"], directory / "decode.log", timeout)
        observation["decoded"] = byte_result(decoded, asset["bytes"], asset["planar_sha256"])
        observation["exact"] = observation["decoded"]["exact"] and observation["decode"]["status"] == "ok"
        if observation["exact"] and observation["profile_status"] == "ok":
            observation["status"] = "ok"
    else:
        observation["decode"] = {"status": "not_attempted", "reason": "encode_failed"}
        observation["decoded"] = byte_result(decoded, asset["bytes"], asset["planar_sha256"])
    write_json(directory / "observation.json", observation)
    return observation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("store", "prepared", "common-streams", "sources", "output", "opj-compress", "opj-decompress"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--cohort", choices=("development", "holdout"), default="development")
    parser.add_argument("--depths", type=int, nargs="+")
    parser.add_argument("--trials", choices=TRIALS, nargs="+")
    parser.add_argument("--products", choices=PRODUCTS, nargs="+", default=list(PRODUCTS))
    parser.add_argument("--selection-evidence", type=Path, help="development result required for explicit holdout choices")
    parser.add_argument("--rounds", type=int, choices=(1, 3, 5), default=3)
    parser.add_argument("--seed", type=int, default=20260910)
    parser.add_argument("--timeout", type=float, default=3600)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("timeout must be positive")
    if args.cohort == "holdout" and (not args.depths or not args.trials or not args.selection_evidence):
        parser.error("holdout requires explicit depths, trials and development selection evidence")
    chosen = profiles(args.depths or list(range(2, 7)), args.trials or ["baseline"])
    # Keep optional trials bounded to one explicitly selected depth per call.
    if any(p["trial"] != "baseline" for p in chosen) and len(args.depths or []) != 1:
        parser.error("named configuration trials require one explicit depth")
    store = args.store.resolve(strict=True)
    bundle = DEVELOPMENT if args.cohort == "development" else HOLDOUT
    assets = load_inputs(store, args.prepared, args.common_streams, args.sources, bundle, args.products)
    scheduled = [(asset, profile) for asset in assets for profile in chosen
                 if profile["trial"] != "rgb-mct" or asset["product"] in ("RGB8", "RGB16")]
    if not scheduled:
        parser.error("selected profiles have no applicable products")
    selection = None
    if args.selection_evidence:
        evidence_path = inside(store, args.selection_evidence)
        evidence = json.loads(evidence_path.read_text())
        if evidence.get("cohort") != "development" or not evidence.get("complete") or not evidence.get("valid"):
            parser.error("selection evidence must be a complete valid development scout")
        measured = {(o["asset_id"].removeprefix(DEVELOPMENT + "-"), o["profile"]["name"])
                    for o in evidence["observations"] if o["status"] == "ok"}
        required = {(a["product"], p["name"]) for a in assets for p in chosen
                    if p["trial"] != "rgb-mct" or a["product"] in ("RGB8", "RGB16")}
        if not required <= measured:
            parser.error("selected holdout profiles lack successful development observations")
        selection = {"path": str(evidence_path), "sha256": sha(evidence_path)}
    source = {"revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip(),
              "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))}
    output = new_output(store, args.output)
    tools = {"compress": args.opj_compress.resolve(strict=True), "decompress": args.opj_decompress.resolve(strict=True)}
    identities = {name: tool_identity(tool, output) for name, tool in tools.items()}
    bindings = {str(p): sha(p) for p in (args.prepared, args.common_streams, args.sources, Path(__file__).resolve())}
    for asset in assets:
        bindings[asset["raw_path"]] = asset["sha256"]
        bindings[asset["planar_path"]] = asset["planar_sha256"]
    for identity in identities.values():
        bindings[identity["path"]] = identity["sha256"]
        bindings.update(identity["runtime_libraries"])
    result = {"schema_version": 1, "kind": "openjpeg_satellite_compression_scout", "cohort": args.cohort,
              "bundle": bundle, "profiles": chosen, "assets": assets, "rounds": args.rounds,
              "measurement_boundary": "application_journey",
              "timing_scope": "CLI process launch, codec, input/output and log writes; excludes hash and structure checks",
              "claim": "descriptive profile scout only; no native codec leaderboard or speed confidence claim",
              "tools": identities, "bindings": bindings, "selection_evidence": selection, "source": source,
              "excluded_cases": [{"asset_id": a["id"], "profile": p["name"], "reason": "RGB-only MCT trial"}
                                 for a in assets for p in chosen if (a, p) not in scheduled],
              "environment": {"platform": platform.platform(), "python": platform.python_version(),
                              "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
                              "processor": platform.processor()},
              "seed": args.seed, "complete": False, "valid": False, "observations": []}
    write_json(output / "intent.json", result)
    generator = random.Random(args.seed)
    sequence = 0
    for round_number in range(args.rounds):
        cases = list(scheduled)
        generator.shuffle(cases)
        for asset, profile in cases:
            observation = observe(asset, profile, sequence, tools, output, args.timeout, round_number)
            result["observations"].append(observation)
            sequence += 1
    result["identity_changes"] = [path for path, expected in bindings.items()
                                  if not Path(path).is_file() or sha(path) != expected]
    result["complete"] = True
    result["valid"] = not result["identity_changes"] and all(o["status"] == "ok" for o in result["observations"])
    write_json(output / "result.json", result)
    print(json.dumps({"result": str(output / "result.json"), "valid": result["valid"], "observations": sequence}))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, subprocess.SubprocessError):
        print("scout failed; retain output as incomplete evidence and inspect locally", file=sys.stderr)
        sys.exit(1)
