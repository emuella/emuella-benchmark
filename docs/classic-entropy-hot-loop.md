# Classic entropy hot-loop measurement

## Baseline and diagnosis

This bounded study starts from clean merged codec
`bc747f86907aff09e09278e4444ad5932ef4669d`, after removal of the rejected
4W scheduler. The packed encoder and original W joined batches remain fixed.
There are no intervening codec changes. Historical executable timings do not
qualify the fresh control. The benchmark starting revision is
`ba3b8d596379d21cbc9f6c8a3be27107bd5a9abd`.

The [matched refresh](openjpeg-refresh.md) owns the facade operation boundary,
full-sample verification, source/build identity, process limits and affinity.
The [comparison method](comparisons.md) owns the unchanged conservative 99%
per-contrast ratio interval and 5% gate. Both arms use perf/optimisation 3,
ThinLTO, one codegen unit, parallel enabled/SIMD disabled, and leave
`EMUELLA_TIER1_ENCODER` unset. Eligible dispatch must be packed; fallback stays
available. CPU 0 is used at one worker and CPUs 0–7 at eight. Keep direct/global
decode, D2/style 0 and bypass, RGB RCT, PAN/MSI no MCT, interleaved inputs,
768 MiB working/64 MiB output limits, 120-second calls and 8 GiB process ceiling.

Initial diagnosis is twelve operation-scoped samples: full Mansfield PAN16,
eight-band MS16 and RGB8, both styles, encode and decode, one worker. Up to four
failed setup attempts may be repaired without replacing successful observations.
Use the existing FIFO-controlled sampler at the production facade boundary.
Setup, input loading/hashing and verification are outside enabled sampling;
small control/clock overhead at the boundaries remains diagnostic overhead.
Sampling builds emit no headline timings and ordinary builds contain no sampler.
Inspect sampled Emuella instructions and distinguish MQ decisions/state,
renormalisation, byte IO and raw bits from traversal/preparation/output.
Tier-1 invocation duration is not MQ attribution. External implementation
source and disassembly are excluded.

## Mechanism and directional freeze

Diagnosis is in progress. No candidate timing is authorised by this provisional
protocol. Before candidate timing, this section will fix one mechanism family,
at most three related variants, finite screen and replay budgets, target
direction/style, primary cases, non-regression coverage and stopping conditions.
Before arithmetic editing, retain the unchanged implementation including affected
byte IO and termination as an independent test-only reference. It must never
call the candidate helper. Encoder-backend agreement and a changed round trip
are not independent arithmetic proof.

## Fixed constraints on qualification

Discovery precedes internal confirmation/regression; only a surviving candidate
receives the relevant fresh OpenJPEG anchor. Freeze one candidate before
confirmation with zero warmups, twenty adjacent alternating AB/BA pairs per
required contrast and one operation per fresh process. Use the existing
estimator without outlier removal, replacement samples or confirmation-driven
tuning. Candidate/baseline minus one needs an upper bound below −5% for a
required primary; every required non-regression upper bound must be at most +5%.
A qualified direction/style is sufficient. Inconclusive improvement is not
equivalence, although an upper bound at most +5% establishes non-regression.
No family-wide confidence or universal ranking is claimed.

Choose a proportionate matrix from the fixed nine RarePlanes products and
SpaceNet development RGB16 chips before timing. Group acquisitions and label
prior exposure; these are previously measured products, not untouched holdouts.
Khartoum remains excluded from performance/lossy evaluation. Baseline
qualification, candidate-relative effects and absolute acceptance are separate:
a failing control does not prove candidate regression. Missing mandatory
observations are blockers. Complete failed internal predicates stop expensive
external or unrelated cohorts; retain every already-started observation.

Require baseline-identical complete bytes and segment metadata, exact native
samples and 1/2/4/8-worker resource/byte parity. Decode arms receive identical
streams with both Emuella/OpenJPEG origins represented. Changed decoders execute
anew. Independent-decoder receipts may be reused only for unchanged stream
hashes with explicit provenance; changed coverage requires fresh evidence.
Preserve correctness/failure checks beyond the performance cohort, including
styles/fallback, magnitudes, edges, prefixes, striding, scratch reuse, no-std/WASM,
truncation, synthetic end-input and resource admission. Use safe Rust and existing
accounted scratch with no new limits, hidden buffers or padding assumptions.

Retain absolute one/eight-worker times, per-case intervals, stream bytes and
separate allocation/RSS/CPU observations. Re-profile a surviving selected
implementation without using diagnostic times as headline evidence. Bind exact
sources/builds and preserve all failures. Rejected production experiments are
removed; no excluded stage is optimised to rescue an entropy rejection.

## Evidence handling

Raw observations, traces, streams, derivatives and full build receipts remain
in their respective approved persistent input stores with notices and lineage.
Registered build scratch is separate. Only factual measurements and identities
enter public evidence; protected traces never become public test fixtures.
RarePlanes Dataset, June 2020: J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and
AI.Reverie, CC BY-SA 4.0. SpaceNet Dataset, SpaceNet Partners and DigitalGlobe
imagery, CC BY-SA 4.0; Van Etten, Lindenbaum and Bacastow (2018).
