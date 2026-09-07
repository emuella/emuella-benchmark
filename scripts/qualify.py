#!/usr/bin/env python3
"""Exercise real workers on locked generated data; retain factual results in scratch."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare", ROOT / "scripts/prepare-generated.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--workers", type=Path, required=True)
    parser.add_argument("--catalogue", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-dirty-probe", action="store_true", help="label exploratory uncommitted source; not qualification evidence")
    parser.add_argument("--quick", action="store_true", help="one grey and one RGB case for CI")
    args = parser.parse_args()
    dirty = bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True).strip())
    if dirty and not args.allow_dirty_probe:
        parser.error("qualification requires a clean committed benchmark candidate; --allow-dirty-probe is exploratory only")
    output = args.output.absolute()
    output.mkdir()
    benchmark = args.benchmark.resolve(strict=True)
    workers = args.workers.resolve(strict=True)
    experiment = json.loads(prepare.prepare(args.catalogue, output / "inputs").read_text())
    experiment["protocol"] = dict(rounds=5 if args.quick else 7, samples_per_batch=2 if args.quick else 3,
                                  warmup=1, timeout_ms=60000, boundary="codec_operation",
                                  context_policy="fresh_process_per_batch", cache_policy="warm_input",
                                  practical_relative_threshold=0.05)
    if args.quick:
        experiment["cases"] = [experiment["cases"][1], experiment["cases"][4]]
    summary = dict(schema_version=1, provisional_dirty_source=dirty, harness_sha256=prepare.digest(benchmark.read_bytes()),
                   source_revision=subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
                   catalogue_commit=experiment["cases"][0]["input"]["provenance"]["catalogue_commit"], journeys={})

    def invoke(*parts):
        result = subprocess.run([str(benchmark), *map(str, parts)], capture_output=True, text=True)
        # Measurement verdict exit codes are data, while command errors are failures.
        if result.returncode not in (0, 2, 3, 4):
            raise RuntimeError(result.stderr or "benchmark command failed")
        return result.returncode

    def summarise(name, run_path, required=True):
        run = json.loads((run_path / "run.json").read_text())
        counts = {}
        for batch in run["batches"]:
            counts[batch["status"]] = counts.get(batch["status"], 0) + 1
        summary["journeys"][name] = dict(statuses=counts, run_sha256=prepare.digest((run_path / "run.json").read_bytes()),
                                           worker_sha256=run["worker"]["executable_sha256"])
        if not required and (not counts.get("ok") or not set(counts) <= {"ok", "unsupported", "unattainable_rate"}):
            raise RuntimeError(f"{name} has no successful points or unexpected failed/invalid coverage: {counts}")
        if required and set(counts) != {"ok"}:
            details = [b.get("detail") for b in run["batches"] if b["status"] != "ok"]
            raise RuntimeError(f"{name} failed: {details[:3]}")
        return run

    def paired(name, exp, baseline="openjpeg", candidate="emuella"):
        config = write(output / (name + ".json"), exp)
        directory = output / name
        invoke("pair", config, workers / (baseline + "-worker.json"), workers / (candidate + "-worker.json"), directory)
        summarise(name + "-baseline", directory / "baseline")
        summarise(name + "-candidate", directory / "candidate")
        comparison = json.loads((directory / "comparison.json").read_text())
        summary["journeys"][name] = dict(verdict=comparison["verdict"],
                                           cases={c["case_id"]: c["verdict"] for c in comparison["cases"]})
        invoke("report", directory / "baseline", directory / "candidate", output / (name + ".html"))
        return config, directory

    paired("lossless-encode", experiment)
    unchanged = copy.deepcopy(experiment)
    unchanged["cases"] = unchanged["cases"][:2]
    paired("unchanged-emuella", unchanged, "emuella", "emuella")

    compressor = Path(shutil.which("opj_compress") or "").resolve(strict=True)
    decompressor = Path(shutil.which("opj_decompress") or "").resolve(strict=True)
    bitstreams = output / "bitstreams"
    bitstreams.mkdir()
    decode = copy.deepcopy(experiment)
    for case in decode["cases"]:
        provenance = case["input"]["provenance"]
        source = args.catalogue / "generated/common/generated-core" / provenance["asset"]
        encoded = bitstreams / (case["id"] + ".j2k")
        process = subprocess.run([str(compressor), "-i", str(source), "-o", str(encoded), "-n", "3", "-mct", "0"], capture_output=True)
        if process.returncode:
            raise RuntimeError("independent codestream preparation failed")
        case["reference"] = case["input"]
        case["input"] = dict(path=str(encoded), sha256=prepare.digest(encoded.read_bytes()),
                             provenance=dict(generator="OpenJPEG CLI", generator_sha256=prepare.digest(compressor.read_bytes()),
                                             generator_arguments="-n 3 -mct 0", source_sha256=provenance["source_sha256"]))
        case["operation"] = "decode"
        case["settings"] = dict(coding="classic")
    decode_config, _ = paired("common-decode", decode)
    first_grey = next(c for c in decode["cases"] if c["image"]["components"] == 1 and c["image"]["width"] > 32)
    partial = copy.deepcopy(decode)
    partial["cases"] = []
    # Independent decoder materialises the exact requested reference grid in this
    # explicit project-authored scratch store; no crop/resample fallback is timed.
    for name, options, region, reduction in (
            ("roi", ["-d", "4,4,36,36"], dict(x=4, y=4, width=32, height=32), 0),
            ("reduced", ["-r", "1"], None, 1)):
        case = copy.deepcopy(first_grey)
        expected = bitstreams / (name + ".pgm")
        process = subprocess.run([str(decompressor), "-i", case["input"]["path"], "-o", str(expected), *options], capture_output=True)
        if process.returncode:
            raise RuntimeError("independent partial reference preparation failed")
        raw, image = prepare.read_pnm(expected.read_bytes())
        raw_path = bitstreams / (name + ".raw")
        raw_path.write_bytes(raw)
        case["id"] += "-" + name
        case["reference"] = dict(path=str(raw_path), sha256=prepare.digest(raw),
                                 provenance=dict(generator="OpenJPEG CLI", generator_sha256=prepare.digest(decompressor.read_bytes()),
                                                 generator_arguments=" ".join(options), input_sha256=case["input"]["sha256"]))
        case["output"].update(region=region, reduction=reduction, image=image)
        partial["cases"].append(case)
    partial_config = write(output / "partial.json", partial)
    for worker in ("openjpeg", "emuella"):
        invoke("run", partial_config, workers / (worker + "-worker.json"), output / (worker + "-partial"))
        summarise(worker + "-partial", output / (worker + "-partial"), required=True)
    invoke("diagnose", decode_config, workers / "emuella-worker.json", first_grey["id"], output / "diagnostic")
    summarise("diagnostic", output / "diagnostic")

    parallel = copy.deepcopy(experiment)
    parallel["cases"] = [copy.deepcopy(first_grey)]
    parallel["cases"][0]["threads"] = 2
    paired("two-threads-decode", parallel)

    lossy = copy.deepcopy(experiment)
    lossy["cases"] = []
    for original in experiment["cases"]:
        for bpp in (2.0, 4.0):
            case = copy.deepcopy(original)
            case["id"] += f"-bpp-{bpp:g}"
            case["settings"]["target_bpp"] = bpp
            case["output"].update(lossless=False, minimum_psnr_db=0.0)
            lossy["cases"].append(case)
    lossy_config = write(output / "lossy.json", lossy)
    for worker in ("emuella", "openjpeg"):
        invoke("run", lossy_config, workers / (worker + "-worker.json"), output / (worker + "-lossy"))
        summarise(worker + "-lossy", output / (worker + "-lossy"), required=False)

    ht = copy.deepcopy(experiment)
    for case in ht["cases"]:
        case["settings"].update(coding="ht", decomposition_levels=1)
    ht_config = write(output / "ht.json", ht)
    invoke("run", ht_config, workers / "emuella-worker.json", output / "emuella-ht")
    summarise("emuella-ht", output / "emuella-ht")
    ht["protocol"]["boundary"] = "application_journey"
    ht_config = write(output / "ht-application.json", ht)
    derivatives = output / "derivatives"
    derivatives.mkdir()
    os.environ["EMUELLA_BENCHMARK_DERIVATIVE_STORE"] = str(derivatives)
    invoke("run", ht_config, workers / "openjph-worker.json", output / "openjph-ht")
    summarise("openjph-ht", output / "openjph-ht")
    # HT lossy uses different explicit encoder controls: retain measured points,
    # never claim equal quality from equal numeric settings.
    for worker in ("emuella", "openjph"):
        ht_lossy = copy.deepcopy(experiment)
        ht_lossy["protocol"]["boundary"] = "codec_operation" if worker == "emuella" else "application_journey"
        for case in ht_lossy["cases"]:
            case["settings"] = dict(coding="ht", decomposition_levels=2)
            case["settings"].update({"target_bpp": 4.0} if worker == "emuella" else {"qstep": 0.01})
            case["output"].update(lossless=False, minimum_psnr_db=0.0)
        config = write(output / (worker + "-ht-lossy.json"), ht_lossy)
        invoke("run", config, workers / (worker + "-worker.json"), output / (worker + "-ht-lossy"))
        summarise(worker + "-ht-lossy", output / (worker + "-ht-lossy"), required=False)
    completed = sorted(path.parent for path in output.rglob("run.json"))
    invoke("points", *completed, output / "measured-points.json")
    invoke("series", output / "series.html", *completed)
    write(output / "qualification-summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
