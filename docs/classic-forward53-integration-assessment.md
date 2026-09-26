# Forward 5/3 integration assessment tooling

`classic-forward53-integration-assessment/v1` is an opt-in acquisition and
retained-report path. The [workspace contract](https://github.com/emuella/emuella-workspace/blob/4a533057c6ab4e27ae520eb5180ad76ac5fe0203/docs/classic-forward53-integration-assessment.md)
and [frozen endpoint register](https://github.com/emuella/emuella-workspace/blob/4a533057c6ab4e27ae520eb5180ad76ac5fe0203/docs/evidence/classic-forward53-integration-assessment/endpoint-register.json)
own the policy. Historical finite and parallel-dispatch schemas and results stay
closed. This code does not admit another historical attempt or promote a codec.

## Frozen design

The derivation verifies the unchanged dispatch predecessor manifest and imports
its full 28-endpoint graph. The assessment register binds every inherited
endpoint identity and old timing/absolute predicate, then records each new
predicate. The primary remains strict 99% upper `< −5%` and arithmetic-mean
saving `≥ 10 ms`; every secondary uses its explicit registered upper bound,
ordinarily `≤ +5%`. A tighter independently evidenced requirement belongs in
the register before preparation. The unchanged fixed 40/160 comparator supplies
each ratio-of-arithmetic-means interval. Legacy ±5% labels remain descriptive.

Main order is `00,02,01,03,10,11,04–09,12–27`: 2,480 ordinary calls, 56
preflights and 112 allocations. A second build instance repeats 00, 01 and 10
in that order with 40 pairs, two preflights and two allocations per endpoint.
The total is exactly 2,900 starts. The main endpoint 00 stops collection when
either primary predicate fails. After it passes, valid secondary and repeat
timing failures are retained while the remaining matrix runs. Any hard failed
call, invalid fixed-count session or cap stops. Every repeat is judged on its
own samples and original predicate; observations are never pooled or replaced.
The two-hour, 2 GiB evidence and 30 GiB registered-build caps, 150-second and
1 MiB start headroom, inherited per-endpoint caps and no-retry rule apply.

## Source and build preparation

The source-treatment JSON has schema
`classic-forward53-integration-assessment-source/v1` and exactly
`baseline_codec`, `candidate_codec`, `baseline_tree`, `candidate_tree`,
`baseline_to_candidate_diff_sha256`, and `independent_review` in addition to
`schema`. The review descriptor is an absolute `path` and SHA-256. Its JSON uses
`classic-forward53-integration-assessment-source-review/v1`, `verdict: "PASS"`,
nonempty `reviewer` and `locator`, and `sources` containing all five source
fields. Preparation checks clean source commits/trees and recomputes the full
binary Git diff with the deterministic switches used for parallel dispatch.
The baseline is the current production base selected for this campaign; no
historical baseline commit is hard-coded into the assessment path.

Complete source correctness, independent source review, two independently
prepared build instances and build compatibility review before any input or
lease use. Use the same clean benchmark and codec revisions and one matched
toolchain/recipe for all builds. Each command below creates a fresh output and
its own Cargo target directory under the registered scratch root. `CODEC_BASE`
and `CODEC_B` denote clean checkouts at the reviewed campaign revisions;
`BUILD_ROOT` denotes the root created by
`./scripts/workspace scratch create classic-forward53-integration-assessment`.
Run from the clean benchmark candidate checkout:

```sh
python3 scripts/openjpeg-refresh.py build --codec-source "$CODEC_BASE" --output "$BUILD_ROOT/main/baseline/ordinary"
python3 scripts/openjpeg-refresh.py build --codec-source "$CODEC_B" --output "$BUILD_ROOT/main/candidate/ordinary"
python3 scripts/openjpeg-refresh.py build --codec-source "$CODEC_BASE" --output "$BUILD_ROOT/main/baseline/resource" --allocation-diagnostics
python3 scripts/openjpeg-refresh.py build --codec-source "$CODEC_B" --output "$BUILD_ROOT/main/candidate/resource" --allocation-diagnostics
python3 scripts/openjpeg-refresh.py build --codec-source "$CODEC_BASE" --output "$BUILD_ROOT/repeat/baseline/ordinary"
python3 scripts/openjpeg-refresh.py build --codec-source "$CODEC_B" --output "$BUILD_ROOT/repeat/candidate/ordinary"
python3 scripts/openjpeg-refresh.py build --codec-source "$CODEC_BASE" --output "$BUILD_ROOT/repeat/baseline/resource" --allocation-diagnostics
python3 scripts/openjpeg-refresh.py build --codec-source "$CODEC_B" --output "$BUILD_ROOT/repeat/candidate/resource" --allocation-diagnostics
```

Each output retains `build.json`, `cargo.jsonl`, `cargo.stderr`, the source
snapshot, lockfile and executable; retain symbol files and these build records
with both executable instances in the approved binding store before scratch
cleanup. `build.json` binds exact benchmark/codec source inventory, executable
and library SHA-256, command, rustc version, Cargo artefacts, lockfile, selected
features and captured build environment. The verbose stderr records effective
compiler and linker invocations. Retain the actual compiler/linker paths and
versions, complete inherited build environment and any path-remapping decision
in a separately reviewed private `build_provenance` receipt. Pin its path and
SHA-256 as a prerequisite. Review those bytes and
the matched perf/optimisation-3/ThinLTO/one-codegen-unit/line-table flags,
parallel enabled, SIMD and ordinary diagnostics disabled, unset backend
overrides, and separate allocation feature. The preparer checks the effective
worker flags, library/toolchain/configuration equality, source identities,
fresh target roots and frozen receipt hashes.

The pinned `build_reproducibility` prerequisite is JSON with schema
`classic-forward53-integration-builds/v1`. `instances` has `main` and `repeat`,
each with `baseline` and `candidate`, each with `ordinary` and `resource`; every
leaf has exactly `binary_sha256`, `text_sha256` and `build_sha256`. Hash the
complete executable and its `.text` bytes extracted with
`objcopy --only-section=.text -O binary EXECUTABLE /dev/stdout`; `build_sha256`
is the corresponding `build.json` digest. The independent `review` object has
`verdict: "PASS"`, nonempty `reviewer`, `locator` and `explanation`, and
`section_differences`: the exact ordered list of `baseline/ordinary`,
`baseline/resource`, `candidate/ordinary`, `candidate/resource` whose `.text`
hash differs between build instances. A difference requires an explicit
compatibility explanation; unresolved material divergence blocks preparation.
Whole-executable equality is an observation, not a hidden gate. These build
receipts and source-review receipts are separate from timing evidence.

## Configuration and offline commands

Use the historical finite configuration's approved `stores`, exact 14
`allocation_identities`, `estimators`, `codec_sources`, `benchmark_source`,
`evidence_roots`, `build_root` and `authority`. Replace `arms` with
`build_instances.main` and `build_instances.repeat`; each instance has
`baseline`/`candidate`, each with `ordinary`/`resource` paths to its `build.json`.
The `contract` object contains the historical `v1`, `v1_sha256`, `register` and
`design`, plus the unchanged dispatch `predecessor`, `predecessor_sha256`,
`source_treatment`, `source_treatment_sha256`, `assessment_register`,
`assessment_register_sha256`, `manifest` and `manifest_sha256`. All paths are
absolute. `prerequisites` contains `source_correctness`, `independent_decode`,
`output_failure`, `parallel_route`, `source_review`, `build_provenance` and
`build_reproducibility`, each pinned by `path`/`sha256`; all but identical-stream
`independent_decode` also carry `source_treatment_sha256`. `source_review`
must be the source treatment's exact reviewed file and digest.

```sh
python3 scripts/finite_confirmation_live.py derive-assessment \
  --v1 V1.json --sha256 V1_SHA --register HISTORICAL_REGISTER.json \
  --design HISTORICAL_DESIGN.json --predecessor DISPATCH.json \
  --predecessor-sha256 DISPATCH_SHA --assessment-register ASSESSMENT_REGISTER.json \
  --assessment-register-sha256 ASSESSMENT_REGISTER_SHA \
  --source-treatment SOURCE.json --source-treatment-sha256 SOURCE_SHA \
  --authority REVIEWED_AUTHORITY --output ASSESSMENT.json
python3 scripts/finite_confirmation_live.py prepare \
  --config CONFIG.json --output APPROVED_OUTPUT/preparation.json
```

The resulting preparation uses
`classic-forward53-integration-assessment-preparation/v1`. It binds all eight
builds, source and policy bytes, both comparators, inputs, prerequisites,
installed launcher and host policy before timing. The operational owner uses
the existing single-use `execute` command and installed restoration procedure.
Retained reconstruction uses no corpus worker or live lease:

```sh
python3 scripts/finite_confirmation_report.py --preparation APPROVED_OUTPUT/preparation.json \
  --sha256 PREPARATION_SHA --v1 V1.json --register HISTORICAL_REGISTER.json \
  --design HISTORICAL_DESIGN.json --predecessor DISPATCH.json \
  --estimator-40 ESTIMATOR40 --estimator-160 ESTIMATOR160 \
  --output APPROVED_OUTPUT/report.json
```

Offline success means complete bound evidence and all 31 numerical predicates;
independent engineering acceptance and source-owner-first delivery remain
separate decisions. No assessment corpus acquisition has been run by this change.
