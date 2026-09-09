# RarePlanes full-location calibration

## Scope and method

This bounded probe measures two preselected RarePlanes Real Full Location
bundles: Magadino (`30_104001002394E000`) and Apple Valley
(`47_104001001D2C7A00`). Testdata owns selection, rights, source locks and
preparation. Benchmark consumes its version 1 `prepared.json`, verifies all
eight regular-file paths, byte counts and SHA-256 digests before mutation, and
admits all eight PAN16, RGB8, RGB16 and MS16 assets. The two MS16 inputs use
exactly eight unsigned U16 native components, preserving supplied band order with
unit sampling and no MCT. The five-round, four-journey matrix contains 160 batches:
40 MSI batches plus the existing 120 grey/RGB batches. Earlier six-asset records
remain unchanged historical evidence.

Each admitted case uses classic lossless coding, two DWT decompositions and one
worker thread. Five fresh worker processes each provide one measured operation.
There is no timed warmup: the worker loads and verifies the input before its
in-memory operation timer, so the declared cache policy remains `warm_input`.
The 120-second limit applies to the complete worker batch, including setup,
verification and shutdown. Every failed, crashed, timed-out, invalid or
unsupported batch remains in `run.json` and the factual summary.

Encode runs exercise the independently built Emuella and OpenJPEG native
workers. Shared decode streams are generated outside timing by the installed
`opj_compress` from a testdata-owned, verified component-planar little-endian
RAWL derivative. The command explicitly selects one full-image tile, LRCP, one
lossless layer, two decompositions, no MCT and one thread. The original prepared
pixel-interleaved RAW remains the exact decode reference. The common stream,
planar derivative and all raw run records remain in the approved testdata
artefact store.

The sanitised summary records exact prepared/source, common-stream, worker,
harness and build identities; the applied profile; compressed size in bytes; raw-storage compression ratio; operation time in
nanoseconds; spatial pixels/second and component samples/second; bits/spatial
pixel and bits/component sample; exactness; and worker-process peak RSS in bytes.
One spatial pixel contains every band at one position; one component sample is
one scalar band value. The retained `sample_values_per_second` field aliases
component samples/second. RSS includes the whole worker process, setup and
verification; codec-owned allocation admission is a separate measurement. Build provenance includes compiler and dependency
versions, enabled features, source hashes and the resolved lock digest. Local
paths and the hostname are omitted. The orchestration revision and script digest
are checked again after the runs, so a source change during a long observation
prevents a completed evidence disposition.

## Reproduction

Use a clean committed benchmark checkout and new output name. The store is the
authorised persistent RarePlanes location; do not direct any input, planar
derivative, common codestream or run output to build scratch or Git.

```sh
python3 scripts/rareplanes-calibrate.py \
  --benchmark "$RAREPLANES_BUILD/harness-target/release/emuella-benchmark" \
  --workers "$RAREPLANES_BUILD/workers" \
  --build-provenance "$RAREPLANES_STORE/worker-build-provenance.json" \
  --prepared "$RAREPLANES_STORE/prepared/prepared.json" \
  --preparation-tool "$TESTDATA_CHECKOUT/recipes/rareplanes-calibration-v1.py" \
  --store "$RAREPLANES_STORE" \
  --output "$RAREPLANES_STORE/run-COMMITTED-BENCHMARK-REVISION" \
  --opj-compress /absolute/path/to/opj_compress \
  --opj-dump /absolute/path/to/opj_dump
```

The output must be a new direct child of the resolved store. A successful
complete observation exits zero. Exit status 4 means retained non-success
coverage; the summary is still written when the runner produced factual run
records. Setup or contract failures exit 1.

## Retained checkpoint observation

[The factual checkpoint record](evidence/rareplanes-calibration-checkpoint.json)
was acquired with orchestration revision
`9858bbb073a2077236f536ab8b9a38e9aadcf6c9` and summarised with the separately
identified candidate script. It is retained calibration evidence rather than
terminal exact-head qualification.

| Journey | Completed exact batches | Unsupported batches |
|---|---:|---:|
| Emuella classic lossless encode | 20 | 10 |
| OpenJPEG classic lossless encode | 30 | 0 |
| Emuella shared-stream decode | 30 | 0 |
| OpenJPEG shared-stream decode | 30 | 0 |

Every completed batch reconstructed the full input exactly. Emuella consistently
rejected the five Apple Valley PAN16 rounds at its existing 16-million-sample
image guard and the five Apple Valley RGB8 rounds at its corresponding
per-component guard. These are calibrated unsupported results, not missing
coverage. The record gives per-case mean/minimum/maximum operation time,
sample-value throughput, measured output bytes, raw-to-encoded compression ratio
and maximum observed worker-process RSS, together with raw run digests and exact
input, codestream, harness, worker and build identities.

## Interpretation limits

This is a practical resource and mechanism calibration on two deliberately
contrasting acquisitions, not a representative population. Timing is a native
codec-operation observation on one host. RSS is the worker process `VmHWM`,
including setup and verification, rather than a codec allocation count.

Emuella classic lossless RGB applies its reversible colour transform, while the
OpenJPEG worker profile disables MCT. The shared decode stream also disables
MCT. Output pixels are equivalent, but encoder profiles differ; size and timing
must remain factual per-worker observations rather than a universal speed or
compression ranking. The historical checkpoint did not cover lossy coding, HTJ2K, MSI
admission, image cropping, optimisation, corpus publication or release.
If a full-size case reaches an existing codec resource or admission guard, the
calibration retains that unsupported observation. A crop is not substituted.
Changing the relevant scalable encode profile belongs in a separate codec-owned
workstream.

## Independent verification of retained Emuella streams

The opt-in companion journey retains one deterministic public Emuella encode
per admitted asset and verifies each full image using both native decode workers.
It shares the timed worker's public encode path and classic lossless single-tile
D2 profile, including reversible colour transform for RGB. It leaves the
five-round 160-batch calibration protocol and its OpenJPEG common streams intact.
The separate decode verification uses five rounds, the existing protocol minimum,
for 80 additional batches; they are excluded from the headline matrix.
Earlier 60-batch verification records and MS16 exclusions remain historical
observations, without being relabelled as current coverage.

```sh
python3 scripts/rareplanes-verify-emuella.py \
  --benchmark "$RAREPLANES_BUILD/harness-target/release/emuella-benchmark" \
  --workers "$RAREPLANES_BUILD/workers" \
  --build-provenance "$RAREPLANES_STORE/worker-build-provenance.json" \
  --prepared "$RAREPLANES_STORE/prepared/prepared.json" \
  --store "$RAREPLANES_STORE" \
  --output "$RAREPLANES_STORE/emuella-verification-COMMITTED-BENCHMARK-REVISION" \
  --opj-dump /absolute/path/to/opj_dump
```

Use a clean committed checkout and workers built from the intended final codec
revision. The new output must be a direct child of the authorised persistent
store. Each export and each verification batch has a 120-second limit. Export
requests, responses, logs, codestreams, decode runs and the summary remain there;
no protected payload belongs in Git or build scratch. The worker's additive
`--export-lossless REQUEST RESPONSE NEW_CODESTREAM` entry point uses one encode,
no warmup and a new output file; ordinary worker invocations are unaffected.

The separate summary binds prepared and source identities, retained stream
hashes, applied encode profiles, build provenance, worker executable identities
and raw decode run hashes. It requires all eight full-reference decodes to be exact
for each decoder and checks input, executable, build and orchestration identities
again on completion. An export failure retains its request and available log
without claiming completed verification; a decode failure is retained in the
summary and exits 4. Setup/export failures exit 1. Time and process peak RSS in
this journey include its own verification context and are separate from both the
headline matrix and codec-owned additional working-allocation measurements.

The subsequent [scalable lossless work package](scalable-lossless.md) records
the 120-exact candidate matrix, merged-codec allocation scaling and retained
baseline comparison. It preserves this earlier calibration as historical evidence.

## Independent MSI header inspection

Both runners invoke the installed `opj_dump` outside timing for each MSI common
stream and each separately retained Emuella MSI stream. They retain tool binary
SHA-256, reported OpenJPEG library version, codestream SHA-256, raw dump and help
log hashes. Parsed factual records identify each component's zero-based index,
unsigned 16-bit precision, unit sampling, native width and height, reversible D2
coding, and the full-image single-tile, LRCP, one-layer, no-MCT defaults.
Dimensions follow from the observed zero image origin and unit sampling.

OpenJPEG's dump reports main-header defaults. The shared worker admission check
separately rejects coding/quantisation overrides, extension markers, multiple
tiles/tile-parts, and malformed/truncated envelopes for the new MSI workload.
The decoder and full-reference comparison establish every reconstructed sample;
header inspection alone does not establish entropy validity or exactness. All
streams and raw tool outputs stay within the approved store. The self-contained
parser tests use authored text, and native interoperability tests use authored
full-range, distinct-band samples.

The [native eight-band candidate report](native-msi.md) records the subsequent
160 exact matrix batches, 80 separate retained-stream decodes, independent MSI
header observations and separate authored allocation probes. It preserves the
historical records above and identifies the exact candidates measured.
