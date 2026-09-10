# Satellite compression scout

`scripts/scout-satellite-compression.py` runs the independently installed
OpenJPEG CLI against previously authorised, prepared full-acquisition products.
It is a descriptive compression-profile experiment. Its process timings include
application I/O and process startup and belong to `application_journey`; they
cannot enter the native worker codec-operation leaderboard.

The frozen development acquisition is Mansfield `94_104001000B823500`, with
PAN16, RGB8, MS16 (eight components) and RGB16. Tok Junction
`105_104001002F92BB00` is a prospective holdout from this tuning work; it was
historically benchmarked and is not previously unseen imagery. No acquisition,
preparation, native codec admission change or publication is performed.

The initial question is whether the existing planar RAWL input and CLI RAWL
output reconstruct exactly for eight-component D3 and the separately named
bypass trial. The smallest probe uses development MS16, D3, one round, baseline
and bypass. Benchmark owns its factual output and acceptance; testdata retains
selection, preparation and rights ownership. Proceed to the broader scout only
when both probes have valid structure and complete byte equality. Record any
failed probe and its retain-or-reject disposition before selecting a candidate.

The ordinary sweep selects D2–D6 at these fixed settings:

| Setting | Value |
|---|---|
| Transform | Reversible, lossless (`-r 1`; no irreversible switch) |
| Tile | One full-image tile, one tile-part |
| Progression and layers | LRCP, one layer |
| MCT | Off |
| Code-block | 64 × 64 |
| Coding style | 0 |
| Precincts | Default 2^15 × 2^15 at every resolution |
| Threads | One |

Optional profiles are `rgb-mct` (RGB8 and RGB16 only), `block32x32`,
`block32x64`, and `bypass` (style 1). `baseline` supplies the 64 × 64 control.
Each changes only its named setting. Optional trials require one explicitly
chosen depth per invocation, avoiding a large Cartesian sweep. No spectral
transform is applied to MS16.

Use absolute paths for the approved store, original source lock, and installed
CLI tools. Every output must be a **new direct child** of that store. Existing
inputs and derivatives remain in place; the script never removes outputs.
For example, with shell variables already set to these local resources:

```sh
python3 scripts/scout-satellite-compression.py \
  --store "$scout_store" \
  --prepared "$scout_store/prepared-final/prepared.json" \
  --common-streams "$scout_store/final-matrix/inputs/common-codestreams.json" \
  --sources "$scout_source_lock" \
  --opj-compress "$scout_tools/opj_compress" \
  --opj-decompress "$scout_tools/opj_decompress" \
  --output "$scout_store/scout-msi-d3-probe" \
  --products MS16 --depths 3 --trials baseline bypass --rounds 1
```

After that probe passes, omit `--products`, `--depths` and `--trials` and choose
a new output name for the all-product baseline D2–D6 sweep. The default is three
rounds; `--rounds 5` is also available. One round is for a representative probe.
Rounds shuffle profile/product order using a recorded seed. This is a small,
correlated cohort with no confidence intervals or speedup verdicts; retain the
raw round observations when making a descriptive selection.

Run optional trials in another new output directory with, for example,
`--depths 3 --trials baseline rgb-mct block32x32 block32x64 bypass`. Select the
depth using the development sweep before running those trials. Separate profile
invocations remain separate evidence records.

Only after selecting from development, invoke the same command with
`--cohort holdout`, explicit `--depths` and `--trials`, a new output name, and
`--selection-evidence` pointing to a completed valid development `result.json`.
The result must use scout schema 2, identify Mansfield exactly, and contain
complete successful rounds with canonical profile settings, admitted asset
identities, observed structure, exact decoded byte identities and unchanged
runtime dependencies. Each chosen product/profile must match that evidence in
full; a matching profile name alone does not qualify. Earlier provisional
schema-1 results remain historical evidence and cannot select a new holdout.
The script does not pick settings, pool development results, or launch the
holdout automatically. If selected profiles come from separate development
results, use separate holdout invocations bound to their respective evidence.

Before timing, the script checks the prepared manifest, source-lock identity,
common-stream argument identity, recorded planar lineage and full prepared/raw
hashes. The existing RarePlanes selection loader validates the versioned source
lock and complete selected TIFF matrix. Each prepared asset must name the locked
TIFF for its acquisition and declared train/test split: PAN16 uses PAN, RGB8 uses
PS-RGB, and MS16/RGB16 use MS. A bounded-memory comparison checks every prepared interleaved sample
against its planar derivative. It reuses the authorised planar file without
writing a new input conversion. Source TIFF digests remain catalogue provenance;
this script verifies the existing prepared samples and their reviewed lineage,
and does not reopen the TIFFs or assert a new preparation authority.

Every encode and decode gets its own wall-clock observation, raw CLI log and
output path. SHA-256, size, profile validation, runtime dependency resolution and
exact reconstruction checks run outside those timers. Structural failures retain
the project-authored rejection reason in their local observation. The project-authored marker reader admits only the
requested reversible raw codestream profile, checking SIZ, COD and QCD plus one
tile-part without coding overrides and terminal EOC. It rejects unsupported
markers conservatively. It does not parse entropy packets or constitute JPEG
2000 conformance certification. The independently installed OpenJPEG decoder
writes component-planar little-endian RAWL for all component counts, including
eight-component D3–D6; byte count and SHA-256 must match the verified input.
The encoder and decoder are from the same external codec, so exactness here is
not an independent-codec interoperability claim.

`intent.json` preserves the selected scope and tool/input identities before
measurements. Each operation directory retains `observation.json`, the complete
codestream and decoded output when produced, and the raw tool logs. A final
`result.json` appears only after the schedule finishes and identities are
rechecked. It records every failure and is `valid` only when every submitted
observation succeeds with matching structure, complete decoded byte equality,
and unchanged bound files. A run can be complete and invalid. Interruptions or
unexpected orchestration errors leave incomplete evidence; use a fresh output
directory for a retry. Nothing silently consumes an incomplete result.

Executable hashes, compiled OpenJPEG library versions, dependency names,
loader-facing paths, resolved targets and dynamic-library hashes, source and
selection-loader script identities, input manifests, seed, CPU affinity and
platform are retained. Dependency resolution and hashes are checked before every
encode and decode and again at completion. Changed dependencies skip the affected
operation and invalidate the run, including a symlink retargeted while its old
file remains. These checks observe the installed environment around operations;
they do not lock it against a concurrent mutation during a process launch. The current Linux implementation uses `ldd` on explicitly supplied,
trusted installed executables and rejects unresolved dependencies. Do not inspect
or copy external implementation source. Raw logs and pixel-bearing outputs stay
in the approved store; inspect failures there and keep public reports to approved
factual summaries, without verbatim external diagnostics or private paths.

Run the self-contained behavioural tests with:

```sh
python3 -m unittest discover -s tests -p 'test_scout_satellite_compression.py'
```

These tests use authored synthetic bytes and mocked processes. Actual RAWL
reconstruction and tool/profile compatibility require the representative probe;
a passing synthetic suite alone does not establish them.
