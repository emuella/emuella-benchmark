# Classic encoder kernel measurement

The [completed qualification](classic-encoder-kernel-results.md) records the
selected backend, every-case results, resource evidence and limitations.

This bounded treatment compares the unchanged Emuella encoder with one selected
packed-state encoder. The [matched refresh protocol](openjpeg-refresh.md) supplies
the facade worker, process limits, CPU affinity, profile inspection and complete
sample checks. The [existing estimator](comparisons.md) supplies conservative 99%
per-case intervals and the 5% practical gate. OpenJPEG remains a separate matched
external anchor; its timing is not the reference treatment.

The freshly built merged codec baseline is
`08fd8dfc80c3475209680032ce2c097409716246`. Historical refresh results retain their
original build/measurement identities even though this starting revision agrees.
Worker builds use perf, optimisation level 3, ThinLTO, one codegen unit, parallel
enabled and optional SIMD disabled. The build receipt records the compile-time
`EMUELLA_TIER1_ENCODER` selection separately from the default build environment.
The reference and candidate must have identical compiled benchmark sources,
compiler, runtime libraries and build configuration; report-only and driver-only
changes do not relabel the measured worker source revision.

## Development and confirmation

Mansfield complete PAN16, RGB8 and eight-band MS16 are the development cases.
Styles 0 and 1 remain separate. Each of at most three related state/traversal
variants receives at most four alternating authored replay pairs and three
alternating full-image screen pairs per development contrast. A screen contains
36 fresh-process facade invocations and cannot establish promotion.

The selected backend receives twenty alternating reference/candidate pairs for
each of the inherited nine full products, both styles and one/eight workers.
Targeted decode regression covers the three development products, both styles
and one/eight workers, with identical OpenJPEG streams supplied to both builds.
Together these are 48 comparisons and 1,920 invocations. There are zero warmups
and one measured operation per process; codec processes run serially. Streams
are bound before measurement, and every encode must match its reference digest.
Verification decodes and process setup stay outside the facade clock.

Primary one-worker confirmation is Boca Raton PAN16/MS16/RGB8, for each style.
A promoted style must improve at least one primary high-bit-depth case; primary
cases must be equivalent or improved and no case may practically regress.
Other inconclusive cases remain uncertainty, never equivalence. These previously
measured acquisitions are confirmation cases, not untouched holdouts. No tuning
follows confirmation and no favourable subset replaces failed coverage.

SpaceNet is separate regression coverage: all twelve fixed Vegas, Paris and
Shanghai development RGB16 chips, both styles, one worker and twenty pairs
(960 invocations). The manifest is SHA-256
`209eb97c250f108c4ff0aff9a226db6dc6e4ecd68b10bc074e844b60b89e406e`.
Khartoum remains excluded from performance and lossy work. Related products
remain grouped by acquisition; no footprint-independent holdout is asserted.

Run `scripts/classic-encoder-kernel.py measure --help` for required build,
prepared-input and reference-stream arguments. `--phase screen`, `confirm` and
`spacenet` select these finite cohorts. `analyse` consumes the existing
`classic-treatment-estimator` executable. Each completed process retains its
request, response, resources and receipt before the driver continues; failed
observations invalidate the affected comparison. Absolute times and bytes are
separate from whole-process RSS/CPU. Codec allocation diagnostics are separate.

## Encode-only sampling

Build the separate diagnostic using `openjpeg-refresh.py build --sampling`.
It compiles `classic-encode-sampling` and requires `perf record -D -1` with
`--control=fifo:CONTROL,ACK`. Set `EMUELLA_PERF_CONTROL` and `EMUELLA_PERF_ACK`
to those FIFOs. The worker enables samples immediately before the existing
facade operation and disables them before hashing/profile inspection and full
reconstruction. Small control/clock overhead at the edges remains in the sampled
interval. The retained `classic-encode-sampling` feature also admits one-worker
Emuella decode at that same operation boundary. Both modes emit no timing
samples. Headline drivers reject its receipt. The ordinary binary compiles no
sampling control, environment lookup or control IO into its operation.

The fixed six-case baseline sampling completed with exact bytes and every sample
reconstructed. At 499 Hz user-cycle sampling, the standalone neighbourhood-query
symbol accounts for the following fraction of encode cycles:

| Development product | Style 0 | Bypass |
|---|---:|---:|
| PAN16 | 14.73% | 20.27% |
| RGB8 | 22.08% | 22.42% |
| MS16 | 17.53% | 21.67% |

Pass bodies contain substantial inlined MQ work. Their aggregate shares are not
state/traversal attribution, nor is the standalone query fraction a predicted
recoverable gain. Existing stage diagnostics place Tier-1 at approximately
93–98% of native encoder time, with their original boundaries preserved; serial
bypass includes preparation and appends. These observations justify a bounded
state experiment, not a full-image performance claim.

Initial whole-process samples passed exactness but had insufficient stack
unwinding for facade attribution. They remain separate from the bounded samples.
The first controlled invocation failed after disabling sampling because perf's
FIFO acknowledgement contained a NUL terminator. Its failed response is retained;
the repaired fixed six-case run supplied the completed observations above.
This consumed one unused diagnostic slot without expanding the 24-invocation
diagnosis cap. No codec or candidate tuning resulted from that harness repair.

Raw observations, streams and full build receipts remain under their authorised
RarePlanes/SpaceNet stores. No protected coefficients or pixel payload enter Git.
RarePlanes Dataset, June 2020: J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and
AI.Reverie, CC BY-SA 4.0. SpaceNet Dataset, SpaceNet Partners and DigitalGlobe
imagery, CC BY-SA 4.0; Van Etten, Lindenbaum and Bacastow (2018). Original notices
and source lineage remain with the respective local evidence.
