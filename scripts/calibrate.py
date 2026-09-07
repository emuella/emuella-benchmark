#!/usr/bin/env python3
"""Calibrate acquisition and verdicts with explicitly synthetic timed work."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--test-worker", required=True, type=Path)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.absolute()
    output.mkdir()
    experiment = json.loads(args.experiment.read_text())
    experiment["name"] = "synthetic-acquisition-calibration"
    experiment["cases"] = [experiment["cases"][0]]
    experiment["protocol"] = dict(rounds=7, samples_per_batch=5, warmup=2, timeout_ms=30000,
                                  boundary="codec_operation", context_policy="fresh_process_per_batch",
                                  cache_policy="warm_input", practical_relative_threshold=0.05)
    config = write(output / "experiment.json", experiment)
    worker = dict(executable=str(args.test_worker.resolve(strict=True)), implementation="synthetic-copy-and-sleep",
                  source_identity="project-authored-calibration-fixture-v1", artefacts=[], args=["--delay-ms", "5"])
    baseline = write(output / "baseline-worker.json", worker)
    delayed = copy.deepcopy(worker)
    delayed["args"] = ["--delay-ms", "25"]
    slow = write(output / "slow-worker.json", delayed)
    corrupt = copy.deepcopy(worker)
    corrupt["args"].append("--corrupt")
    bad = write(output / "corrupt-worker.json", corrupt)
    results = {}
    for name, candidate, allowed in (("unchanged", baseline, {"equivalent", "inconclusive"}),
                                     ("slowdown", slow, {"regressed"}),
                                     ("incorrect", bad, {"invalid"})):
        directory = output / name
        result = subprocess.run([str(args.benchmark), "pair", str(config), str(baseline), str(candidate), str(directory)], capture_output=True, text=True)
        if result.returncode not in (0, 2, 3, 4):
            raise RuntimeError(result.stderr)
        comparison = json.loads((directory / "comparison.json").read_text())
        results[name] = comparison
        if comparison["verdict"] not in allowed:
            write(output / "rejected-calibration.json", results)
            raise RuntimeError(f"calibration rejected: {name} => {comparison['verdict']}")
    summary = dict(schema_version=1, decision="retain", observations=results,
                   benchmark_sha256=hashlib.sha256(args.benchmark.read_bytes()).hexdigest(),
                   test_worker_sha256=hashlib.sha256(args.test_worker.read_bytes()).hexdigest(),
                   experiment_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
                   limitation="Synthetic sleep validates acquisition/verdict paths; real codec repeatability is a separate observation.")
    write(output / "calibration-summary.json", summary)
    print(json.dumps({name: result["verdict"] for name, result in results.items()}))


if __name__ == "__main__":
    main()
