# Emuella benchmark

A Rust library and CLI for reproducible codec experiments, isolated worker
execution and conservative baseline/candidate timing feedback. Versioned JSON
contracts retain input digests, source/build identities, machine configuration,
applied settings, correctness metrics and every raw timing batch. No hosted
service, asset acquisition or automatic publication is involved.

## Build and verify

Rust 1.88 or newer, Python 3 for corpus tooling tests:

```sh
cargo build --release
sh scripts/check.sh
```

The root package has no sibling codec dependency. Codec workers are separately
built adapters; see [worker documentation](docs/workers.md). Tests use a
project-authored synthetic protocol worker and require no external corpus.

## Run an experiment

```sh
emuella-benchmark run experiment.json worker.json new-run-directory
emuella-benchmark pair experiment.json baseline-worker.json candidate-worker.json new-pair-directory
emuella-benchmark compare new-pair-directory/baseline new-pair-directory/candidate --json
emuella-benchmark report new-pair-directory/baseline new-pair-directory/candidate comparison.html
emuella-benchmark points run-a run-b factual-points.json
emuella-benchmark series factual-series.html run-a run-b
emuella-benchmark diagnose experiment.json worker.json case-id new-diagnostic-directory
```

Output directories must not already exist. The manifest records intent; each
batch records its request, response and logs; `run.json` is written only after
completion and final identity checks. Interrupted runs remain incomplete evidence
and cannot be silently consumed as completed runs. No pixels appear in JSON or
HTML reports. Worker logs may contain adapter diagnostics: workers must not print
pixel payloads or secrets.

[Composed journeys](docs/composed-journeys.md) separately admit persistent application/cache/GPU traces.
[Protocol](docs/protocol.md) defines the JSON fields and measurement contract.
[Comparison methodology](docs/comparisons.md) explains uncertainty and verdicts.
[Multi-run series](docs/series.md) describes factual rate/distortion and progress extracts.
[Corpus integration](docs/corpus.md) describes runtime catalogue identities.
[RarePlanes calibration](docs/rareplanes-calibration.md) describes the bounded
full-location real-scene probe.

The CLI returns 0 for timing improvement/equivalence, 2 for regression, 3 for
inconclusive timing and 4 for invalid/not-comparable coverage. Execution errors
return 1. `run` returns 4 if any batch is unsuccessful; `report` returns 0 when the
HTML file is written, regardless of its displayed verdict.

Licensed under Apache-2.0. This repository does not grant rights to external
codecs, corpus assets or standards material.

## Real-codec qualification and calibration

```sh
python3 scripts/build-workers.py --output /path/to/new-worker-build
python3 scripts/qualify.py --benchmark /path/to/emuella-benchmark \
  --workers /path/to/new-worker-build --catalogue /path/to/emuella-testdata \
  --output /path/to/new-qualification
python3 scripts/calibrate.py --benchmark /path/to/emuella-benchmark \
  --test-worker /path/to/protocol-test-worker \
  --experiment /path/to/new-qualification/inputs/experiment.json \
  --output /path/to/new-calibration
```

Qualification requires a clean committed benchmark source (the explicitly labelled
`--allow-dirty-probe` mode is exploratory only). It exercises shared lossless codestreams, native encode/decode,
partial output, threads, lossy measured points, diagnostics and HTJ2K. `--quick`
selects two inputs for the separate real-worker CI job. Qualification retains
unsupported/unattainable lossy points and reports actual coverage; it does not
assert that every requested rate is attainable. Calibration uses explicitly
synthetic timed copy/sleep operations to validate acquisition and verdict paths;
its results are not codec performance measurements. See [calibration evidence](docs/calibration.md).
