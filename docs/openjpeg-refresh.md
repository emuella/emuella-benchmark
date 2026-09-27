# Matched Emuella–OpenJPEG refresh

The later [finite scheduling study](classic-parallel-execution-results.md)
rejected its selected 4W policy at fixed confirmation and retained the original
W-batch scheduler. Its complete internal, resource and encode-only external
evidence is separate from the historical results and scopes below.

`scripts/openjpeg-refresh.py` compares current public Emuella APIs and the
installed OpenJPEG library through a dedicated `classic-compare-worker`.
Historical worker defaults and their measurements are unchanged. The optional
`classic-compare` feature requires a current codec source override; it is not
part of default worker builds against the historical codec pin.

The frozen cohort is nine complete products: Mansfield and Boca Raton
PAN16/RGB16/eight-band MS16/RGB8, and Tok RGB8. The existing prepared manifest
is SHA-256 `6c37b54bf75af0c17c1b67c5ad7bd2d56b5d34d45de9737ddb50d0fc1fe10e7b`.
These are the latest classic configuration study's inputs, selected before new
timing. This refresh does not repeat the expanded 48-image admission matrix.

Both encoders request raw lossless Part 1, reversible D2, one full-image tile,
one layer, LRCP, 64×64 code blocks and default precincts. Style 0 and selective
arithmetic bypass are separate profiles. RGB uses reversible colour transform
in both codecs; PAN and eight-band MSI use none. The worker checks the actual
SIZ/COD profile outside timing and compares every reconstructed sample.

Each style runs with one and eight codec workers. For each product/style/thread
combination, encode starts from identical interleaved U8/U16_LE bytes. Decode
has two separately named contrasts: one common OpenJPEG stream and one common
Emuella stream. Both decoders receive the same bytes within each contrast.
Compressed outputs need not be byte-identical across codecs; each encoder's
repeated output must match its own prepared stream.

## Existing-stream diagnosis calls

For a future diagnosis against an existing reference, construct each preflight
with `openjpeg-refresh.py`'s `make_existing_stream_call`. It requires recorded
`case_id`, `origin`, `style`, `raw_sha256`, `stream_path` and `stream_sha256`
metadata matching the prepared asset and derived stream path. The resulting
worker request uses `operation: "encode"` and the explicit expected stream hash.
The worker reads and verifies the existing stream, checks the new encode against
its hash, and leaves that stream unchanged. `prepare` retains its separate
create-new operation. Missing or inconsistent identity is rejected before launch.

`scripts/classic-diagnosis-request.py --config METADATA.json` is the metadata-only
dry-run entry point. It emits a `kind`, `request` and `timing_eligible` record and
does not read raw or stream payloads or start a worker. A future controller can
use this same function within its existing lease, deadline and restoration flow.
Store preflight results under `kind: "preflight"` and use
`ordinary_samples_from_existing_stream_call` when forming ordinary timing
vectors from results already validated by `run_process`; the helper does not
repeat its binary, boundary or exactness checks. Worker preflights return a
sample but that helper excludes it. The metadata file is a single call with
`kind`, `asset`, `prepared`, `streams`,
`origin`, `codec`, `style`, `workers`, `round` and `stream_identity` fields.

The inner clock includes raw-to-library conversion, API setup/operation and
owned output conversion. Emuella uses its public facade and direct process-global
Rayon context; OpenJPEG uses its installed public API with explicit threads.
Input loading/hashing, profile inspection and complete sample verification are
outside timing. Process wall/CPU time and peak RSS include all of those phases
and are reported separately. Worker count is an execution budget, not proof
that all requested workers participated.

Each of the 108 contrasts has twenty adjacent alternating AB/BA codec pairs,
zero warmups and one measured operation per fresh process: 4,320 invocations,
plus 36 untimed stream preparations. One-worker pairs are restricted to the
first supplied CPU; eight-worker pairs use all eight supplied CPUs. No codec
processes run concurrently. The host CPU topology and governor are retained.
The process timeout is 120 seconds and address-space ceiling is 8 GiB. Explicit
Emuella working/output limits are 768/64 MiB; common admission is conservative,
and these codec allocation limits must not be described as OpenJPEG RSS caps.

The unchanged benchmark-owned estimator supplies conservative 99% per-comparison
ratio intervals and a 5% practical gate from independent batch means. OpenJPEG
is baseline, Emuella candidate. No family-wide confidence claim, outlier trimming,
retry selection, historical speedup multiplication or universal codec ranking
is made. Every planned failed or unsupported observation remains visible and
invalidates its affected timing comparison. Setup and one-round probe results
are separately identified and cannot become headline observations.

From a clean committed benchmark checkout:

```sh
python3 scripts/openjpeg-refresh.py build --codec-source /path/to/current-codec \
  --output /registered/scratch/refresh-build
python3 scripts/openjpeg-refresh.py measure \
  --build /registered/scratch/refresh-build/build.json \
  --prepared /approved/rareplanes-store/prepared \
  --output /approved/rareplanes-store/refresh-probe --cpus 0,1,2,3,4,5,6,7 --probe
python3 scripts/openjpeg-refresh.py measure \
  --build /registered/scratch/refresh-build/build.json \
  --prepared /approved/rareplanes-store/prepared \
  --output /approved/rareplanes-store/refresh-main --cpus 0,1,2,3,4,5,6,7
python3 scripts/openjpeg-refresh.py estimator --output /registered/scratch/estimator
python3 scripts/openjpeg-refresh.py analyse --output /approved/rareplanes-store/refresh-main \
  --estimator /registered/scratch/estimator/target/release/classic-treatment-estimator
python3 scripts/render-openjpeg-refresh.py /approved/rareplanes-store/refresh-main/report.json
```

Build receipts bind clean committed source bytes/modes, codec revision/tree,
Cargo artefacts, compiler/configuration/log identities, binary and runtime
libraries. Runs recheck source, build and prepared-input identities at completion.
Retain build receipts and logs in the approved store before scratch cleanup.
The report contains factual timings, intervals, sizes and process memory;
protected pixels, codestreams and raw run material stay in the approved store
with the complete original notice, attribution and source lineage.
