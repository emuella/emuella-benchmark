# Classic encode front-end observations

The finite experiment is in development; no candidate performance or promotion
claim is established. The [protocol](classic-encode-front-end.md) fixes the
primary, gates and conditional stages. [Factual observations](evidence/classic-encode-front-end.json)
retain all completed baseline observations with exact stream/input identities.

## Fresh production baseline and diagnosis

Ordinary baseline codec `b02b6ab1ddaecefd25e18d4cd610eba09e8a6627` has original MQ,
qualified packed dispatch, unset selector and original W batches. Diagnostic
codec `479ab6e128335bb60bed81afceab5aa3d5ecde73` adds feature-only clocks around
the ordinary bodies without an optimisation. Both use benchmark worker
`5b1426cd10d3845ea97fd7e24ecbe5838010f9a1`, perf/ThinLTO/one codegen unit,
parallel without optional SIMD, and the fixed direct/global CPU budgets.
All sixteen diagnostic and sixteen ordinary descriptive calls match immutable
stream hashes and reconstruct every native sample. Matching independent
OpenJPEG decode receipts were authenticated before the calls.

Full Mansfield times below are milliseconds. Each ordinary cell is one fresh
process, descriptive only, without an interval. Diagnostic columns are from
separate instrumented calls; their differences from ordinary timings combine
instrumentation and run variability, not a causal overhead estimate.

| Product / style | Ordinary one / eight workers | Conversion / RCT at eight | DWT at eight |
|---|---:|---:|---:|
| PAN16 / 0 | 1359.667 / 298.429 | 6.869 / 0 | 26.929 |
| PAN16 / bypass | 758.505 / 156.099 | 6.779 / 0 | 27.205 |
| RGB16 / 0 | 248.702 / 47.285 | 1.827 / 0.140 | 4.637 |
| RGB16 / bypass | 132.462 / 29.587 | 1.736 / 0.141 | 4.633 |
| MS16 / 0 | 712.910 / 128.552 | 4.985 / 0 | 12.252 |
| MS16 / bypass | 357.356 / 77.567 | 4.750 / 0 | 12.338 |
| RGB8 / 0 | 1785.789 / 400.342 | 21.164 / 5.334 | 104.883 |
| RGB8 / bypass | 1620.067 / 396.869 | 21.591 / 5.243 | 119.225 |

RGB8 DWT at eight workers spent 50.885/60.854 ms gathering columns,
6.280/6.458 ms in vertical lifting, 19.538/19.603 ms storing columns,
25.309/29.371 ms in horizontal lifting and 0.898/0.926 ms copying rows, for
style zero/bypass respectively. Scratch resizing was 0.009/0.020 ms; validation
and scratch destruction were below 0.001 ms each. Unattributed loop, clock and
observer overhead remains inside aggregate DWT. At one worker RGB8 DWT was
106.021/105.933 ms, including 52.013/51.908 ms column gathering. The scalable
conversion, RCT, components, levels and DWT axes are serial; parallel execution
begins in the unchanged Tier-1 batches. No redundant sample-range scan exists
for this signed-32 bounded DWT route.

These observations select paired-column gathering with existing scratch as one
locality mechanism. The measured gather interval is headroom, not a recoverable
saving prediction. Fusion and new parallel transform execution are not part of
this candidate. Fresh facade confirmation remains necessary.

## Correctness-cleared development selection

Candidate `21033ea890b4393e8c7f6791cf4a89d866d2dfd3` passed independent pre-timing
Route A source review and its exact-commit canonical gate, including platform,
malformed/failure, independent coefficient and complete-stream reference checks.
Ordinary and diagnostic worker contract tests passed. The mechanism reuses the
previously unused input scratch line; the original per-column lifting/scatter,
odd remainder and horizontal pass remain unchanged. Other encoder profiles keep
their original entry. No allocation, runtime option, scheduler or ISA was added.

All 32 initial resource calls passed: full Boca/Mansfield RGB8, both styles, both
arms and 1/2/4/8 workers. Streams match the immutable baseline and every native
sample reconstructs. Every pair has equal working queries, output capacities,
allocation peaks and observed allocation counts. The largest requested peak is
366,357,664 bytes, within its 602,189,308-byte query and the 768 MiB application
working limit. This is codec allocation, distinct from whole-process RSS/CPU.
Equality of these observed counts is not a scheduling guarantee.

The sole V1 screen completed all 24 calls, three alternating pairs per cell.
Mansfield RGB8 candidate/reference mean ratios were 0.997660/0.996657 at one
worker and 0.948432/0.941691 at eight, for style zero/bypass respectively.
Eight-worker estimates are therefore −5.157%/−5.831%; all screen non-regression
predicates pass. These are descriptive results without confidence intervals.
V1 is frozen for fresh confirmation, with no further variant or source tuning.

Protected observations and independent receipts remain in the approved
RarePlanes store; public evidence contains factual measurements and identities.
RarePlanes Dataset, June 2020: J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and
AI.Reverie, CC BY-SA 4.0. No pixel or coefficient payload is included.
