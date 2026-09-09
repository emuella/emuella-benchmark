# RarePlanes full-location calibration

## Scope and method

This bounded probe measures two preselected RarePlanes Real Full Location
bundles: Magadino (`30_104001002394E000`) and Apple Valley
(`47_104001001D2C7A00`). Testdata owns selection, rights, source locks and
preparation. Benchmark consumes its version 1 `prepared.json`, verifies all
eight regular-file paths, byte counts and SHA-256 digests before mutation, and
admits the six PAN16, RGB8 and RGB16 assets. The two eight-component MS16 assets
are recorded as unsupported because the native worker contract admits only one
or three uniformly sampled components.

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
harness and build identities; the applied profile; compressed size; raw-storage
compression ratio; operation time; sample-value throughput; exactness; and
worker-process peak RSS. Build provenance includes compiler and dependency
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
  --opj-compress /absolute/path/to/opj_compress
```

The output must be a new direct child of the resolved store. A successful
complete observation exits zero. Exit status 4 means retained non-success
coverage; the summary is still written when the runner produced factual run
records. Setup or contract failures exit 1.

## Interpretation limits

This is a practical resource and mechanism calibration on two deliberately
contrasting acquisitions, not a representative population. Timing is a native
codec-operation observation on one host. RSS is the worker process `VmHWM`,
including setup and verification, rather than a codec allocation count.

Emuella classic lossless RGB applies its reversible colour transform, while the
OpenJPEG worker profile disables MCT. The shared decode stream also disables
MCT. Output pixels are equivalent, but encoder profiles differ; size and timing
must remain factual per-worker observations rather than a universal speed or
compression ranking. This probe does not cover lossy coding, HTJ2K, MSI
admission, image cropping, optimisation, corpus publication or release.
If a full-size case reaches an existing codec resource or admission guard, the
calibration retains that unsupported observation. A crop is not substituted.
Changing the relevant scalable encode profile belongs in a separate codec-owned
workstream.
