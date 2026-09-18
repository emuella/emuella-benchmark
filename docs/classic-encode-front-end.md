# Classic encode front-end protocol

This prospective experiment selects `incremental-performance-policy/v1` and
experiment identity `classic-encode-front-end/v1`. Baseline codec is clean
post-D2-removal `b02b6ab1ddaecefd25e18d4cd610eba09e8a6627`: original MQ,
packed-default encoder with `EMUELLA_TIER1_ENCODER` unset and original W batches.
Historical 147–150 ms conversion/DWT observations are not this baseline.

## Diagnosis and selection

First measure full Mansfield RGB8 plus PAN16/MS16/RGB16 controls, styles zero
and bypass, one/eight workers: sixteen feature-only diagnostic calls and sixteen
ordinary descriptive calls. Attribute the ordinary production path: input
conversion/deinterleaving/level shift, RCT, useful DWT arithmetic, explicit
scratch/copy costs, and any remaining overhead or existing parallel execution.
Nested diagnostic clocks and allocation metering perturb execution; retain that
qualification and never use diagnostic samples as headline observations.

Select one measured mechanism. Freeze its identity, affected callers, complexity
and acceptance route before candidate timing. An independent source review must
justify Route A: no new backend, scheduler, public option, allocation/cache,
persistent state, unsafe/ISA dependency or meaningful failure surface. New
parallel machinery uses the existing larger-change gate, regardless of diff size.
No assumption that SIMD or parallelism is required. If no mechanism has adequate
headroom, record measured non-selection and a separate next proposal.

Fresh baseline diagnosis selected **paired-column DWT gather locality**: gather
two adjacent columns into the existing two input scratch lines, then execute
unchanged bounded lifting/scatter using the third coefficient line. The original
single-column path handles the odd remainder. This reuses the previously unused
line within the existing three-line allocation; no new allocation or parallel
execution. Scope is the classic scalable forward path through internal cross-crate
plumbing; other encoder and decoder entry points retain their routing. Independent
Route A classification and exact source binding remain prerequisites to timing.
Conversion/RCT, horizontal work and arithmetic are not additional treatments.

At most three related development variants, each three alternating pairs over
Mansfield RGB8 in both styles at one/eight workers (24 calls). First clear
authored correctness/resources. Screen eligibility requires >=2% bypass
eight-worker mean saving and no >1% mean regression in these development cells.
Select the lowest arithmetic mean of the two eight-worker candidate/baseline
ratios; differences within 1% favour the simpler variant. This descriptive screen
does not prove promotion. Freeze one coherent source before fresh confirmation;
no source retuning after confirmation starts.

## Primary and critical gates

Full Boca Raton RGB8 bypass at eight workers is the **sole promotion primary**.
Route A requires >=2% end-to-end point-estimate saving, 99% relative-time upper
bound <0, and >=10 ms mean absolute saving (one second per hundred encodes).
Larger-change/Route B acceptance requires upper bound strictly <−5%, retaining
the same absolute floor. Route B is not a mandate to bundle unrelated edits.
Every non-primary critical contrast has upper change bound <=+1%.

Complete the four initial contrasts before deciding. Only all initial predicates
passing permits conditional regression/resources. Adequate point and absolute
saving with an upper bound >=0 is insufficient precision, not zero effect.
An upper non-regression bound exceeding +1% leaves that gate unproved; call it
regression only when supported by the interval. Missing/invalid mandatory
evidence blocks disposition. A completed failed predicate stops later conditional
work. No favourable primary waives another critical regression.

| Stage | Operation and product | Styles | Workers | Contrasts |
|---|---|---|---|---:|
| Initial | Boca RGB8 encode | 0/bypass | 1/8 | 4 |
| Conditional | Mansfield PAN16/MS16/RGB16 encode | 0/bypass | 1/8 | 12 |
| Conditional | Tok RGB8 encode | 0/bypass | 1/8 | 4 |
| Conditional | Mansfield RGB8 decode, common OpenJPEG streams | 0/bypass | 1/8 | 4 |
| Conditional | SpaceNet Vegas img1454 RGB16 encode | 0/bypass | 1/8 | 4 |

Use twenty adjacent alternating AB/BA pairs per contrast: 1,120 ordinary
confirmation calls. Zero warmups, one operation per fresh process, no concurrent
codec processes. Reuse the [matched facade boundary](openjpeg-refresh.md) and
unchanged [ratio-of-arithmetic-means estimator](comparisons.md), conservative
99% per-case intervals and separate legacy ±5% timing labels. No family-wide
confidence, optional stopping, extra rounds, outlier removal, replacement
successes, primary switching, estimator change or historical-ratio multiplication.

Both arms use perf optimisation 3, ThinLTO, one codegen unit, parallel enabled,
optional SIMD disabled, direct/global context, CPU 0 for one worker and CPUs 0–7
for eight. Same D2 profiles, RGB RCT, PAN/MSI no MCT, packed interleaved U8/U16_LE
inputs and owned raw output. Input loading, hashing, profile inspection and
complete reconstruction verification stay outside the operation clock. Keep
120 seconds/call, 8 GiB address-space ceiling, 768 MiB working and 64 MiB output.
These are distinct limits; process RSS is not the codec allocation query.

## Correctness, resources and external anchor

Before timing, retain independent intermediate arrays and complete-stream tests
for the changed mechanism, covering sample models/layouts, full-range words,
colour extremes, odd/thin/partial shapes, strides/padding, boundaries, reuse,
prefix/capacity failure, tight admission and malformed inputs. The reference
must not share the changed helper. Existing worker admission, serial minimum,
pre-admitted peak lifetimes and owned/caller failure atomicity stay fixed.
No-std/WASM and relevant native checks remain required; native gains do not
prove browser gains. New parallelism additionally needs deterministic joined
failure/reuse tests and independent complexity review.

Allocation-only prerequisite coverage: baseline/candidate Boca and Mansfield
RGB8, both styles, 1/2/4/8 workers (32 calls). Conditional coverage: Mansfield
PAN16/MS16/RGB16, Tok RGB8 and Vegas img1454, both styles, 1/2/4/8 workers (80).
Require baseline-identical streams and exact native reconstruction. Independent
decoder receipts may be reused only for identical stream hashes with explicit
provenance. Codec allocation peaks must fit their existing working queries and
limits, output capacities their limits. Report allocation counts and investigate
changed paths; no deterministic count-equality requirement for scheduling.
Report process RSS/CPU separately, with baseline absolute qualification and
candidate absolute acceptance separate from relative effect.

After internal survival only, refresh matched OpenJPEG encode for Boca RGB8,
both styles at one/eight workers (160 calls), and sixteen candidate diagnostic
calls matching baseline. External results cannot rescue an internal failure.
No full 108-comparison refresh or new decoder campaign.

## Budgets, exposure and provenance

At most 1,600 observation calls, four hours observation wall time (including
between-stage time after its first call), three hours experimental setup/build
after protocol freeze, three setup repairs, 4 GiB new protected evidence and
30 GiB registered scratch. Canonical checks, independent review, CI and landing
are separate. The existing single-owner budget ledger consumes failed launches,
reserves the per-call timeout and enforces call/wall/storage caps. No resets,
replacement successes or smaller successful sample after cap exhaustion.
Coordinator owns every measurement and its resumable watcher.

RarePlanes prepared manifest SHA-256
`6c37b54bf75af0c17c1b67c5ad7bd2d56b5d34d45de9737ddb50d0fc1fe10e7b`;
SpaceNet prepared manifest
`209eb97c250f108c4ff0aff9a226db6dc6e4ecd68b10bc074e844b60b89e406e`.
Runtime bindings retain exact selected raw/stream hashes, notices, source locks,
build/profile/compiler/worker/estimator identities and source revisions. Reuse
existing matched-refresh RarePlanes and classic-baseline SpaceNet streams.
Mansfield, Boca, Tok and Vegas are previously measured acquisitions; related
products stay grouped. Khartoum remains reserved and excluded.

Protected observations, derivatives and complete receipts remain with their
approved persistent source stores. Disposable builds use registered scratch
`classic-encode-front-end`; retain receipts before cleanup. Only factual results
and identities enter Git. No new acquisition, terms, protected deletion,
redistribution, external implementation-source consultation or publication.

RarePlanes Dataset, June 2020: J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and
AI.Reverie, CC BY-SA 4.0. SpaceNet Dataset, SpaceNet Partners and DigitalGlobe
imagery, CC BY-SA 4.0; Van Etten, Lindenbaum and Bacastow (2018).
