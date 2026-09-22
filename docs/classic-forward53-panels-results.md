# Classic forward 5/3 panel observations

The candidate is **qualification-pending**. The row-major engine passed source,
correctness, portability and resource checks and completed the entire frozen
168-call development schedule. The existing precision evidence cannot support
the mandatory confirmation design. No Boca confirmation, OpenJPEG encode anchor
or production promotion was attempted; this is not a performance rejection.
The enabled candidate remains in draft codec PR #114, with its one-slot source
comparison preserved separately. Production remains unchanged.

The [protocol](classic-forward53-panels.md) retains the prospective policy and
finite limits. [Factual evidence](evidence/classic-forward53-panels.json) includes
all 168 observations, ordinary samples, source/build/input/stream identities,
resource results, separate process RSS/CPU and diagnostic attribution. It contains
no sample, coefficient or codestream payloads. Protected receipts and notices
remain in the approved RarePlanes and SpaceNet stores.

## Source and verification

| Form | Codec revision | Role |
|---|---|---|
| reference | `975a5e734773578f61abf76d5fddfbd837f3bd7d` | Fresh current-production control |
| q1 | `c2e9212924d1b3533262c3c28cfa5b98b1339452` | Width-16 one-slot panels |
| qW | `d60859a8595554be52c8748a8e8c85b69614fea5` | Same engine, bounded parallel panels |

The two candidates differ only in the private backend constant. Independent
exact-head source review passed both. Codec canonical, native/no-std, explicit
`wasm32-unknown-unknown` and feature-enabled Clippy checks passed the final qW
head before observation. The forced-backend matrix includes q1, with exact q1
ordinary/resource/diagnostic builds. Codec CI also passed. The codec-owned
[memory and arithmetic proof](https://github.com/emuella/emuella-j2k/blob/d60859a8595554be52c8748a8e8c85b69614fea5/docs/forward53-panels.md)
records phase lifetimes, capacities, fallback and independent tests.

The frozen runner is benchmark `2f288e3c6827d15d16254497731525467c3f76cc`.
Reference ordinary/resource builds used `b332e3896979d01252be7d08e8cd34e5deb92ef1`;
all other builds used the frozen runner head. Compiled worker sources match
between these benchmark revisions. Canonical and independent runner review
passed before timing. One baseline diagnostic build detected a concurrent
source change during setup and was rebuilt after sources became stable. No
observation had started; this was one material setup repair, not a replaced call.

The host was an AMD Ryzen 9 9950X3D, Linux x86-64, rustc 1.97.1, recorded
powersave governor, CPU 0 / CPUs 0–7 (prefixes for two/four workers),
perf/ThinLTO/one codegen unit, parallel enabled and optional SIMD disabled.
Packed selection was unset, with original MQ and W. Calls ran serially, each in
a fresh process with one facade operation and no warmup. All builds and local
canonical checks finished before observation. The fixed schedule took 516.893
seconds from its first start to its final stage receipt, including between-stage
time, under the 90-minute/180-start budget. All 168 starts succeeded; none was
replaced, excluded or retried. Registered scratch was 9.42 GB at the final build
phase, below 30 GiB. Observation metadata was below 4 MB before evidence retention.

## Ordinary development observations

Times below are arithmetic means in milliseconds. Mansfield RGB8 has three
balanced cyclic-order observations per form/cell; every other row has one.
Style 1 is bypass. Ratios are descriptive only: **no confidence intervals or
non-regression verdicts are estimated from this development schedule**. The
absolute eight-worker RGB8 mean differences were 80.901 ms for style zero and
101.509 ms for bypass. They cannot substitute for the sole Boca promotion primary.
The one-worker RGB16 bypass observation was +6.585%; one observation cannot
establish a slowdown or clear a regression gate. No dispatch retuning followed.

| Input / style / workers | Reference ms | One-slot ms | Multi-slot ms | Multi-slot change % |
|---|---:|---:|---:|---:|
| Mansfield MS16 / 0 / 1 | 778.513 | 784.483 | 749.139 | -3.773 |
| Mansfield MS16 / 0 / 8 | 152.204 | 168.830 | 148.075 | -2.713 |
| Mansfield MS16 / 1 / 1 | 364.407 | 394.004 | 365.215 | +0.222 |
| Mansfield MS16 / 1 / 8 | 89.916 | 94.652 | 86.838 | -3.424 |
| Mansfield PAN16 / 0 / 1 | 1432.595 | 1468.091 | 1413.429 | -1.338 |
| Mansfield PAN16 / 0 / 8 | 304.946 | 298.202 | 284.670 | -6.649 |
| Mansfield PAN16 / 1 / 1 | 815.912 | 833.168 | 819.113 | +0.392 |
| Mansfield PAN16 / 1 / 8 | 199.723 | 185.984 | 175.786 | -11.985 |
| Mansfield RGB16 / 0 / 1 | 252.780 | 271.460 | 253.773 | +0.393 |
| Mansfield RGB16 / 0 / 8 | 51.901 | 55.901 | 50.195 | -3.287 |
| Mansfield RGB16 / 1 / 1 | 134.664 | 138.062 | 143.532 | +6.585 |
| Mansfield RGB16 / 1 / 8 | 33.038 | 34.502 | 30.442 | -7.857 |
| Mansfield RGB8 / 0 / 1 | 1979.123 | 1949.994 | 1925.316 | -2.719 |
| Mansfield RGB8 / 0 / 8 | 511.370 | 471.924 | 430.469 | -15.820 |
| Mansfield RGB8 / 1 / 1 | 1776.985 | 1737.061 | 1686.087 | -5.115 |
| Mansfield RGB8 / 1 / 8 | 502.524 | 448.787 | 401.015 | -20.200 |
| Vegas 1454 / 0 / 8 | 84.554 | 77.723 | 79.153 | -6.388 |
| Vegas 1454 / 1 / 8 | 59.788 | 54.116 | 52.833 | -11.632 |
| Paris 235 / 0 / 8 | 72.513 | 80.394 | 69.730 | -3.838 |
| Paris 235 / 1 / 8 | 64.229 | 62.873 | 61.919 | -3.597 |


## Memory, exactness and failure evidence

All 68 fresh allocation-only calls passed: reference/qW on full Mansfield
RGB8/PAN16/MS16/RGB16, both styles and 1/2/4/8 workers, plus q1 RGB8 at one/eight.
Every working query was unchanged. Measured requested peaks and output capacities
fit their queries and the application limits. The largest requested peak was
197,880,208 bytes in each form, for RGB8 bypass/eight, within its 374,257,252-byte
working query. Reference/qW peaks matched in every resource cell. Observed
allocation counts ranged 238–1889 for reference and 245–1889 for qW; counts are
not deterministic invariants. Process RSS/CPU are separate fields in the evidence.

The full RGB8 panel workspace requested 195,532 bytes at one slot and 1,564,256
bytes at eight. The reference retained 58,212 bytes of three-line scratch.
The larger panel workspace did not increase these whole-operation peaks because
it is released before entropy/output allocations. This measured result supports
the independent phase-aware proof; it does not treat arbitrary query terms as
spare memory. Authored allocation evidence separately covers 84 whole-operation
calls, seven odd/thin/wide shapes, 1/3/8 U8/U16 models, both styles and normal
one/eight plus serial-minimum budgets. Every call passed, with maxima
3,543,280/3,801,160 bytes for reference/candidate, below unchanged queries.
Those authored calls used pre-portability-repair candidate
`28975496ec66c3018eea283594aae4d7ae860a79`; review accepted reuse because the
repair preserves all executed worker-budget paths. They are not newly measured
at the final head. Deterministic codec tests cover joined panic/reservation
release, workspace reuse, optional fallback and output exhaustion.

All 164 encode calls matched the bound complete codestream hashes and reconstructed
every native sample. Independently authenticated OpenJPEG exact-decode receipts
were reused only for those identical stream hashes. Four targeted decode calls
used the unchanged decoder on common OpenJPEG RGB8 streams and reconstructed
exactly. Style-zero reference/qW times were 330.226/305.367 ms, bypass
301.508/294.340 ms; one call per cell supplies functional evidence, not a decoder
performance verdict. Decoder code, testdata and Polyorama were unchanged.

## Separate transform attribution

The following instrumented measurements never enter the ordinary means above.
Each panel stage includes dispatch and joins; aggregate DWT additionally includes
workspace preparation, zero initialisation, destruction and unassigned loop work.
Times nest inside DWT and must not be added to the facade clock. All candidate
levels used width 16; q1 and one-worker qW report `RowPanelScalar` at both levels,
eight-worker qW reports `RowPanelParallel` at both. Logical slots, peak overlapping
jobs and distinct participants are recorded separately even where values match.

| Form / style / workers | DWT ms | Gather/lift/join ms | Scatter/join ms | Horizontal/join ms | Workspace bytes | Slots / peak / participants |
|---|---:|---:|---:|---:|---:|---|
| reference / 0 / 1 | 114.745 | — | — | — | 58,212 (reference) | serial |
| q1 / 0 / 1 | 80.035 | 42.373 | 10.003 | 27.498 | 195,532 | 1 / 1 / 1 |
| qW / 0 / 1 | 70.404 | 31.311 | 10.925 | 28.002 | 195,532 | 1 / 1 / 1 |
| reference / 0 / 8 | 111.261 | — | — | — | 58,212 (reference) | serial |
| q1 / 0 / 8 | 82.394 | 44.508 | 9.705 | 28.026 | 195,532 | 1 / 1 / 1 |
| qW / 0 / 8 | 18.488 | 9.577 | 3.844 | 4.756 | 1,564,256 | 8 / 8 / 8 |
| reference / 1 / 1 | 105.752 | — | — | — | 58,212 (reference) | serial |
| q1 / 1 / 1 | 81.534 | 43.562 | 10.074 | 27.741 | 195,532 | 1 / 1 / 1 |
| qW / 1 / 1 | 71.582 | 32.974 | 10.583 | 27.862 | 195,532 | 1 / 1 / 1 |
| reference / 1 / 8 | 107.980 | — | — | — | 58,212 (reference) | serial |
| q1 / 1 / 8 | 80.056 | 43.454 | 8.863 | 27.514 | 195,532 | 1 / 1 / 1 |
| qW / 1 / 8 | 17.981 | 9.314 | 3.565 | 4.786 | 1,564,256 | 8 / 8 / 8 |

At eight workers, qW Tier-1 invocation occupied 310.034/281.959 ms and
conversion/level-shift/RCT 46.056/46.519 ms for style zero/bypass. These remain
larger stages than the 18.488/17.981 ms forward DWT. Diagnostic clocks and
allocation metering perturb execution; differences between independent diagnostic
calls are not a causal overhead estimate or a publishable speed claim.

## Disposition and next condition

The actual [precision-feasibility result](precision-feasibility-results.md)
failed to establish +1% both-way equivalence for Boca encode at one/eight workers
in any of its three sessions. Eight-worker reverse upper bounds were
+5.253/+6.690/+6.594%; conditional 160-pair zero-centred projections remained
+1.471–+1.781%. Tok and SpaceNet lack scope-specific A/A evidence, and no approved
estimator successor applies. This blocks a defensible full mandatory confirmation
protocol, independently of the promising descriptive Mansfield observations.

Preserve these exact sources and observations. Resume only when a separate
methodology outcome supports a finite, prospectively frozen confirmation design
with the unchanged estimator (or an independently approved successor), meaningful
critical margins and the full mandatory scope. The prospective sole primary is
Boca RGB8 bypass/eight, 99% upper bound below −5% and at least 10 ms absolute
saving. Style-zero, one-worker and critical non-regression/resource gates remain
mandatory. No gate was widened, no critical case was removed, and no new automatic
retesting obligation is created. Candidate source, benchmark evidence and the
active coordination plan remain draft handoffs; they are not enabled merges.

Protected complete report SHA-256:
`cd25a231a4c08e81675864b65abfa63d192c016d0b3ae4be8933790b66d4bfa7`.
Frozen protocol binding SHA-256:
`c410fe8c2eaafb3f83a3e7dece3a26168a696dc08b76b7292fcab0c2c48110e5`.
The approved-store retention manifest binds build/check logs and authored receipts
before disposable scratch cleanup; original path references remain historical.

RarePlanes Dataset, June 2020: J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and
AI.Reverie, CC BY-SA 4.0. SpaceNet Dataset, SpaceNet Partners and DigitalGlobe
imagery, CC BY-SA 4.0; Van Etten, Lindenbaum and Bacastow (2018).
