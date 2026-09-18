# Classic encode front-end observations

The paired-column gather candidate is **not selected**. The sole Boca RGB8
bypass eight-worker primary passed Route A, but 22 of 24 conditional contrasts
did not establish the frozen non-regression bound. None establishes a slowdown:
every conditional interval includes zero. The [protocol](classic-encode-front-end.md)
retains the prospective decision rules. [Factual observations](evidence/classic-encode-front-end.json)
record all means, intervals, ordinary samples, bytes, stream/input identities,
whole-process RSS/CPU and allocation-only results.

The finite experiment completed 1,288 calls: 32 baseline observations, 24 screen
calls, 112 resource calls and 1,120 fresh confirmation calls. The 160-call
external anchor and sixteen selected-candidate diagnostic calls were conditional
on internal survival and remain unrun. There were no further timing rounds,
replacement observations, source retuning or alternative primary.

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
this candidate. The fresh facade confirmation below supplied the decision evidence.

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
V1 remained frozen throughout fresh confirmation, with no further variant or source tuning.

## Fresh confirmation and disposition

Twenty adjacent alternating AB/BA pairs per contrast used one operation per fresh
process, zero warmups and the frozen candidate. The ordinary worker was built
from benchmark `5b1426cd10d3845ea97fd7e24ecbe5838010f9a1`; the confirmation
driver and protocol were frozen at `78c816fa54df207a9aec479c9dbc7ce133c01337`.
Allocation workers used benchmark `0dd1cbd250581e4cbb438da4256e13e818bd358b`.
Receipts bind the baseline and candidate binaries to their exact codec sources.
The host was an AMD Ryzen 9 9950X3D, Linux x86-64, rustc 1.97.1, with the
recorded powersave governor, CPU 0 / CPUs 0–7, perf/ThinLTO, one codegen unit,
parallel enabled and optional SIMD disabled. Findings apply to these inputs,
profiles and host; they establish neither browser gains nor a family-wide effect.

The primary mean fell from **735.4691707 to 701.54848855 ms**: **−4.61211476%**,
99% interval **[−7.93165296%, −1.16716214%]**, saving **33.92068215 ms** per
encode (3.392 seconds per hundred). This passes Route A's 2% point saving,
negative upper interval bound and 10 ms absolute floor. Its separate legacy
±5% label is `inconclusive`; that label does not determine incremental acceptance.
All three other initial Boca contrasts passed the +1% upper-bound requirement,
permitting the conditional stage.

Times below are arithmetic means in milliseconds; changes and conservative
99% intervals are candidate/reference minus one, in percent. “Unproved” means
the required upper bound is above +1%; it is not evidence of a slowdown.
All 28 contrasts have twenty observations per arm. Decode uses common OpenJPEG
streams; all other rows encode with Emuella. There is no multiplicity-adjusted
or family-wide confidence claim.

| Product / operation | Style | Workers | Baseline ms | Candidate ms | Change % | 99% interval % | Frozen gate |
|---|---|---:|---:|---:|---:|---|---|
| Boca RGB8 encode | 0 | 1 | 2400.130 | 2372.458 | -1.153 | [-1.804, -0.498] | Pass |
| Boca RGB8 encode | 0 | 8 | 790.759 | 752.960 | -4.780 | [-8.060, -1.363] | Pass |
| Boca RGB8 encode | bypass | 1 | 2021.935 | 1990.437 | -1.558 | [-2.559, -0.547] | Pass |
| Boca RGB8 encode | bypass | 8 | 735.469 | 701.548 | -4.612 | [-7.932, -1.167] | Primary pass |
| Mansfield PAN16 encode | 0 | 1 | 1354.161 | 1354.331 | +0.013 | [-0.776, +0.807] | Pass |
| Mansfield PAN16 encode | 0 | 8 | 242.546 | 238.861 | -1.519 | [-12.752, +11.201] | Unproved |
| Mansfield PAN16 encode | bypass | 1 | 751.821 | 750.690 | -0.150 | [-1.792, +1.519] | Unproved |
| Mansfield PAN16 encode | bypass | 8 | 160.302 | 156.962 | -2.084 | [-12.632, +9.691] | Unproved |
| Mansfield RGB16 encode | 0 | 1 | 249.904 | 250.545 | +0.257 | [-0.744, +1.268] | Unproved |
| Mansfield RGB16 encode | 0 | 8 | 48.233 | 46.578 | -3.431 | [-12.438, +7.376] | Unproved |
| Mansfield RGB16 encode | bypass | 1 | 133.193 | 133.400 | +0.156 | [-0.808, +1.128] | Unproved |
| Mansfield RGB16 encode | bypass | 8 | 31.114 | 30.084 | -3.312 | [-16.684, +13.919] | Unproved |
| Mansfield MS16 encode | 0 | 1 | 706.566 | 706.563 | -0.000 | [-0.832, +0.840] | Pass |
| Mansfield MS16 encode | 0 | 8 | 131.171 | 132.748 | +1.203 | [-10.371, +14.015] | Unproved |
| Mansfield MS16 encode | bypass | 1 | 359.331 | 358.939 | -0.109 | [-1.270, +1.068] | Unproved |
| Mansfield MS16 encode | bypass | 8 | 78.307 | 78.144 | -0.209 | [-3.822, +3.538] | Unproved |
| Tok RGB8 encode | 0 | 1 | 2229.857 | 2240.817 | +0.492 | [-1.145, +2.146] | Unproved |
| Tok RGB8 encode | 0 | 8 | 543.273 | 544.260 | +0.182 | [-5.973, +6.753] | Unproved |
| Tok RGB8 encode | bypass | 1 | 2056.480 | 2056.704 | +0.011 | [-1.304, +1.345] | Unproved |
| Tok RGB8 encode | bypass | 8 | 518.238 | 521.068 | +0.546 | [-6.236, +7.800] | Unproved |
| Mansfield RGB8 decode | 0 | 1 | 1748.859 | 1748.077 | -0.045 | [-1.448, +1.378] | Unproved |
| Mansfield RGB8 decode | 0 | 8 | 272.898 | 271.749 | -0.421 | [-5.793, +5.246] | Unproved |
| Mansfield RGB8 decode | bypass | 1 | 1558.260 | 1552.557 | -0.366 | [-1.915, +1.206] | Unproved |
| Mansfield RGB8 decode | bypass | 8 | 249.916 | 249.734 | -0.073 | [-6.903, +7.315] | Unproved |
| Vegas RGB16 encode | 0 | 1 | 356.219 | 356.912 | +0.195 | [-0.881, +1.280] | Unproved |
| Vegas RGB16 encode | 0 | 8 | 70.776 | 69.410 | -1.930 | [-8.488, +5.226] | Unproved |
| Vegas RGB16 encode | bypass | 1 | 210.826 | 210.299 | -0.250 | [-1.593, +1.110] | Unproved |
| Vegas RGB16 encode | bypass | 8 | 47.903 | 48.300 | +0.829 | [-12.864, +15.064] | Unproved |

Only Mansfield PAN16 and MS16 style-zero one-worker conditional encodes passed
the +1% bound. The other 22 upper bounds exceeded it, including every conditional
eight-worker contrast and all four unchanged-path decoder controls. Those
controls also show that the available precision does not isolate every apparent
mean change as a candidate effect. All conditional intervals include zero.
The favourable primary cannot waive these critical gates; the frozen outcome is
non-selection, with no extra observations to narrow the intervals.

## Complete correctness and resource evidence

All 1,120 confirmation calls completed successfully, produced baseline-identical
streams (or decoded the same common streams), and reconstructed every native
sample exactly. All 112 allocation-only calls passed: 32 initial and 80 conditional,
covering the seven encode products in both styles, both arms and 1/2/4/8 workers.
The baseline's absolute resource qualification and the candidate's absolute
acceptance each passed independently. Both arms fit the 768 MiB working and
64 MiB output limits; these remain separate from the 8 GiB process address-space
ceiling and process RSS. Ordinary confirmation samples exclude allocation clocks.

Across every paired resource cell, allocation peaks, working queries, output
capacities and observed request counts were equal. Request counts ranged from
238 to 1,889 in each arm; this equality is an observation, not a scheduling
invariant. The maximum requested peak was 366,357,664 bytes against its
602,189,308-byte working query. Maximum resource-process RSS was 555,737,088
bytes for baseline and 554,975,232 for candidate. Resource-process CPU ranged
from 0.26–4.95 s and 0.26–5.03 s respectively. These instrumented process
measurements describe resources and are not facade timing samples.

The evidence JSON gives each resource cell's stream bytes, allocation peak,
request count, query, capacity, RSS and CPU, and each confirmation arm's exact
mean CPU and maximum RSS. It retains the separate legacy timing verdicts beside
the frozen gate decisions, plus complete per-arm timing samples. The extracts
were reconciled against all 1,120 confirmation and 112 resource receipts,
including report/manifest/measurement hashes, sample counts, means, bytes,
RSS/CPU, exactness, resource eligibility and binary identities.

## Retained outcome and remaining uncertainty

Codec `ab55794e91377e9c322105dddc8bbb4218c28eb4` restores production crates to
feature-only diagnostic source `479ab6e128335bb60bed81afceab5aa3d5ecde73`.
It archives the complete baseline-to-candidate patch, SHA-256
`08fdf2912df2ed5003c6a9365a3d35db2f4d32e5e179a7954a98f27d38407e08`,
recovering measured tree `19c26fe7f04f88ac8125fdd736916827e41c18a5`.
The paired-column production change is not retained. Original MQ, packed-default
encoding, unset selector and original W batches remain the production baseline.

Baseline diagnosis identifies column-gather locality as measured headroom, but
the conditional selected-candidate re-profile was not reached.
Remaining candidate bottlenecks and attribution of the primary saving among
DWT stages are therefore unproved. There is no fresh OpenJPEG advantage claim.
A later proposal would need its own prospective decision and precision design;
this experiment is complete with non-selection.

Protected observations and independent receipts remain in the approved RarePlanes
and SpaceNet stores. Public evidence contains factual measurements and identities;
no pixel, coefficient or codestream payload is included. RarePlanes Dataset,
June 2020: J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and AI.Reverie, CC BY-SA 4.0.
SpaceNet Dataset, SpaceNet Partners and DigitalGlobe imagery, CC BY-SA 4.0;
Van Etten, Lindenbaum and Bacastow (2018).
