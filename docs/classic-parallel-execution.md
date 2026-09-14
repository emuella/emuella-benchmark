# Classic parallel execution measurement

This finite scheduling study starts from merged packed codec
`94ba19589b0710192c295478c1f9ad284ea2abd5` and the existing W-job joined
scheduler. Both arms leave `EMUELLA_TIER1_ENCODER` unset and verify the packed
route. The kernel, selector, MQ/raw coding, decoder, transforms, packet syntax,
profile, layouts, limits, admission and current Rayon pool remain fixed.
One-worker calls retain the serial route. No new pool or pipeline is permitted.

The [matched refresh](openjpeg-refresh.md) owns fresh-process facade timing,
profile and full-sample verification, source/build receipts, affinity and process
limits. The [existing comparison method](comparisons.md) owns the unchanged
99% per-contrast intervals and 5% practical gate. This study uses perf/ThinLTO,
one codegen unit, parallel enabled, optional SIMD disabled, CPU 0 for one worker
and CPUs 0–7 for eight, D2/style zero and bypass, RGB RCT and PAN/MSI without MCT,
768 MiB working/64 MiB output, 120 seconds per call and 8 GiB process ceiling.

## Bounded diagnosis

Build the separate worker with `openjpeg-refresh.py build
--execution-diagnostics`. It activates the codec's feature-only observer around
the actual facade call. The ordinary build contains none of this instrumentation.
The observer uses the existing writer and serial route; worker slots capture
start/end timestamps and the caller aggregates at most two endpoints per slot
after joining. Durations include block geometry and the existing Tier-1 call,
including its internal preparation. Per-block histograms are fixed 64-bin
logarithmic distributions with exact count/sum/min/max; no per-image block log,
coefficient or codeword payload is retained. Zero-duration intervals do not
contribute overlap. Peak simultaneous intervals and their time integral describe
actual block activity; distinct threads do not establish concurrency.

Report block durations, first-completion-to-last-completion batch tails,
dispatch-to-first-start, last-finish-to-join, complete invocation/join, ordered
append, conversion/level shift/RCT, DWT and other existing stages. Serial bypass's
existing Tier-1 stage includes preparation and appends; separately bracketed block
calls and appends provide that missing attribution. Report active-block time
both against any-active time and the complete Tier-1 invocation wall interval.
Retained scratch/result/collector capacities and finite endpoint metadata are
separate from the diagnostic allocator's additional requested live peak, which
includes the output and conservatively counts old/new reallocation overlap.
Neither is process RSS. Process setup and reconstruction verification stay outside
the operation; process RSS/CPU include those phases and remain separate.

At most 36 diagnostic facade calls: Mansfield complete PAN16/MS16/RGB8 in both
styles, all six first at eight then at one worker; repeat these twelve for the
selected policy, retaining twelve calls for attribution or failed diagnostic
setup. These diagnostic clocks, aggregate bookkeeping and atomic allocation
metering perturb execution. Report their overhead against separate ordinary
screen calls; diagnostic samples never enter headline inference. Preserve every
failed or interrupted observation, including setup failures.

## Finite screening and selection

Compare baseline W batches with only two related finite windows: 2W and 4W,
each joined once before stream-order append. Each variant receives at most three
adjacent alternating pairs over all six development cases at one/eight workers:
72 fresh-process facade invocations per variant. Deterministic authored codec
probes establish bytes, metadata, joined faults and bounded resource behaviour.

Choose W using existing admission before funding extra buffering. Charge every
live scratch instance, result and collector capacity, queue bookkeeping and
old/new growth overlap before allocation. Shrink a window or fall back to W
batches when extra storage does not fit. Never lower admitted W to fund buffering
or raise an application limit. Slow early jobs cannot create unbounded completed
results; every started job joins on all exits. Stream-order first-error selection,
output-capacity failure and atomic owned publication remain unchanged.

A screen-eligible variant must pass exactness/resources, improve a high-bit-depth
case's mean by at least 5% in each style, and have no development mean regression
above 5%. Select the lowest geometric mean eight-worker candidate/baseline ratio;
a tie within 1% favours the smaller window. Freeze geometry/resource policy and
exact source before confirmation. No confirmation-driven retuning. If neither
variant qualifies, retain baseline, remove failed production experiments and
report the entire finite rejection plus a separate remaining-stage proposal.
Missing mandatory evidence is a blocker, not rejection evidence.

## Fixed confirmation

Use twenty adjacent alternating AB/BA pairs per contrast, zero warmups and one
operation per fresh process, no concurrent codec processes or outlier removal.
Confirm all nine previously measured RarePlanes products, both styles and
one/eight workers: 36 encode contrasts. Primary eight-worker cases are Boca Raton
PAN16/MS16/RGB8 in each style. Promotion needs an improved high-bit-depth primary
in each style; every required encode contrast needs a 99% upper change bound at
or below +5%. Every required one-worker contrast must be equivalent or improved.
Keep inconclusive labels; no family-wide confidence or every-case improvement
claim. Immediate OpenJPEG parity is unnecessary.

Separate SpaceNet regression takes the first lexical selected development chip
per AOI: Vegas img1454, Paris img235 and Shanghai img1196, both styles and one/eight
workers, twenty pairs (12 contrasts). Keep acquisitions grouped and all cases
labelled previously measured; Khartoum is excluded from performance/lossy work.
No corpus expansion or new acquisition occurs.

Labelled scaling/resources covers all nine RarePlanes products in both styles at
2/4 workers, with separate 1/8 resource coverage. Compare complete bytes and
segment metadata at 1/2/4/8; retain native/OpenJPEG exactness and reuse immutable
stream receipts only when hashes prove applicability. Target decoder regression
to Mansfield PAN16/MS16/RGB8, both styles, one/eight workers on common streams.
After selection refresh only matched OpenJPEG encode for all nine products,
styles and one/eight workers using twenty pairs. Decoder optimisation and the
historical full 108-contrast external decode study are outside this study.

Report absolute one/eight times and intervals, bytes, separate resource and
concurrency observations, selected re-profile, matched external anchor and the
remaining bottleneck. Freeze source identities and retain all failures. Raw
observations and protected derivatives stay with their approved RarePlanes or
SpaceNet source store and notices; only authorised factual summaries enter Git.
