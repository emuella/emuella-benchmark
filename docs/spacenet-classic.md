# SpaceNet supplier PS-RGB16 baseline

`scripts/spacenet-classic.py` admits the separate testdata-owned
`common/spacenet-psrgb16` prepared schema 1 contract: sixteen original supplier
RGB-PanSharpen chips in four acquisition groups, twelve development chips and
one whole four-chip geographic reserve. It checks raw U16LE interleaved RGB and
source-valid per-band U8 masks by shape, length and SHA-256. Source selection,
rights, TIFF interpretation and validity derivation remain catalogue-owned.
This pack does not substitute RarePlanes derived MSI RGB or admit RGB8 upcasts.

Use `freeze` with explicit `--prepared`, `--output`, `--binary`,
`--build-provenance`, `--codec-source`, `--codec-revision`, `--decoder`,
`--decoder-provenance`, `--source-views` and `--cpus`. The prepared input and new
experiment directories must share the authorised store. Source views and
stretches must already be frozen. The clean committed runner binds their record,
input manifest, exact codec revision/build, executable and runtime library
hashes, independent decoder provenance and CPU environment before execution.
The decoder is an independently installed OpenJPEG CLI; no external codec source
inspection or acquisition is performed. The existing `real-scene-classic.py build`
command produces the unchanged perf/parallel/no-SIMD facade worker once.

Run `prepare --output EXPERIMENT` then `measure --output EXPERIMENT`.
Preparation uses classic lossless D2 style 0 and bypass style 1, reversible colour
transform, one worker, direct/global facade execution and unchanged 768 MiB
working/64 MiB output limits. Every full stream is reconstructed natively and
independently with OpenJPEG; PPM big-endian U16 is converted to native U16LE only
for full-sample byte equality. Preparation retains no process clocks or RSS;
OpenJPEG uses `-quiet` to avoid incidental timing output. Reserved chips have
only source validation and untimed lossless exactness evidence.

The development schedule has five fresh processes per encode/decode and style,
zero warmups and one verified sample per batch: 240 timed batches. Each process
has a 120-second timeout and 4 GiB address-space limit; observed process RSS is
checked against 4 GiB. These are execution controls, not qualification of the
codec owner's memory admission. Failures, unsupported responses and invalid
observations remain in raw evidence and invalidate complete coverage. Outputs
are create-new; interrupted phases are incomplete evidence, never silently
resumed, discarded or accepted as successful subsets.

The factual summary reports absolute nanoseconds, component Msamples/s,
complete stream bytes, raw-storage bytes divided by stream bytes, and whole
process RSS. Codec-call timing includes facade layout/output work; input loading
and full reconstruction verification are outside it. Whole-process RSS includes
those operations and is separate from codec timing. No style ranking, speedup,
RarePlanes pooling, reserved performance, lossy rate search or viewer acceptance
claim is made. The separate lossy baseline retains its own frozen manifest and
source-valid display gates; a quality failure does not alter corpus membership.

Offline authored tests exercise separate-pack admission, per-band masks,
whole-group reserve protection, immutable output, raw mutation, incorrect worker
profiles, forbidden preparation clocks and incomplete/failed timing coverage.
