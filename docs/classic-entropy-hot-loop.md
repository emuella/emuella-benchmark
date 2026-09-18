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

The twelve completed baseline samples identify decoder decision/state work as
30.97% of PAN16, 31.19% of MS16 and 26.05% of RGB8 style-zero sampled cycles.
Renormalisation shares are 5.71%, 4.94% and 4.31%; unresolved MQ boundaries stay
separate. Emuella-generated instructions show eager successor-field loads before
the fast return and early register writeback. Out-of-line calls occupy only
1.1–4.7%, so a blanket-inline intervention is not justified. These are sampled
shares with attribution uncertainty, not predicted recovered time.

Freeze **decoder MQ decision-local registers and transition access** as the only
family, targeting one-worker style-zero decode. At most two variants:
D1 holds interval/code/context locally and delays successor access while
preserving exchange branches; D2 factors duplicate exchange into Boolean-selected
successor/writeback within that same local decision family. Preserve the fast
MPS return, probability data, renormalisation, byte IO, raw coding and termination.
No encoder arithmetic change, state/traversal rewrite or new generic coder.

The independent test-only full MQ/raw reference was committed before arithmetic
editing at codec `32ccc21ece484651de8b38a2186ebd618b3bc85a`; its body is unchanged
from the merged baseline. Candidate tests must compare decisions, all contexts,
registers and byte-boundary state at equivalent checkpoints, consumed prefix
accounting, termination, bytes and pass/segment metadata. Use bounded authored
traces, deterministic reachable-state sequences, feasible exhaustive small
domains and block replays; malformed inputs test rejection. The oracle cannot
call candidate helpers. Preserve restart/reset, carry/stuffing, ordinary and
predictable termination, raw/MQ transitions and synthetic end-input semantics.

Each variant receives at most four alternating authored replay pairs and three
alternating full-image pairs over Mansfield PAN16/MS16/RGB8, both styles at one
worker on common OpenJPEG streams: 36 facade calls per variant. Screen eligibility
requires at least one high-bit-depth style-zero mean ratio below 0.95, every
six-case decode ratio at most 1.05, and exactness/focused correctness passing.
Select the eligible variant with lowest geometric mean style-zero decode ratio
across the three products; a difference within 1% favours simpler D1. No eligible
variant means finite rejection, not an invitation to another family. Candidate
changes and performance observations stop at two variants. Fix one candidate
source before confirmation, and build a fresh uninstrumented baseline from
`bc747f86907aff09e09278e4444ad5932ef4669d` using identical compiled worker sources.

Before confirmation, collect three descriptive alternating pairs for selected
versus baseline decode of the same six development cases at eight workers
(36 calls). This checks consequences without scheduler changes; it supplies no
confidence or promotion claim and does not change the frozen choice. If discovery
rejects both variants, collect this bounded eight-worker description for the
lower style-zero geometric-mean variant without promoting it.

## Sequential confirmation matrix and stopping rules

The following matrix is frozen before any candidate timing. All confirmation
contrasts use twenty pairs and all required upper non-regression bounds are +5%.

1. **Primary stage:** Boca Raton PAN16 and MS16, style 0, one-worker decode,
   common OpenJPEG-origin streams: two contrasts, 80 calls. Complete both.
   At least one primary must have a 99% upper change bound below −5%, and both
   must have upper bounds at most +5%. If either predicate fails with complete
   valid observations, reject and stop before stage 2. Missing/invalid mandatory
   observations are blockers, not rejection. No extra primary samples or tuning.
2. **Internal regression stage, only if stage 1 passes:** complete the remaining
   contrasts in the 44-contrast matrix below (1,680 additional calls). Every
   upper change bound must be at most +5%; keep inconclusive classifications.
   Complete the fixed stage before disposition; it cannot rescue a failed stage 1.
3. **External anchor, only after all internal and correctness/resource gates
   pass:** fresh matched OpenJPEG-versus-selected decode on the two Boca primaries,
   style 0, one/eight workers, each common Emuella/OpenJPEG origin: eight contrasts,
   twenty pairs (320 calls). Anchor rankings do not alter internal acceptance.

| Required internal coverage | Contrasts |
|---|---:|
| All nine RarePlanes products, decode, both styles, one worker, OpenJPEG origin (includes stage 1) | 18 |
| Boca PAN16/MS16 and Tok RGB8, decode, both styles, eight workers, OpenJPEG origin | 6 |
| Boca PAN16/MS16, decode, style 0, one/eight workers, Emuella origin | 4 |
| Mansfield PAN16/MS16/RGB8, encode, both styles, one worker | 6 |
| Mansfield PAN16, encode, both styles, eight workers | 2 |
| SpaceNet Vegas img1454, Paris img235 and Shanghai img1196, decode, both styles, one worker, Emuella origin | 6 |
| SpaceNet Vegas img1454, decode, both styles, eight workers, Emuella origin | 2 |

This proportionate matrix covers full product classes/acquisitions at one worker,
eight-worker high-bit/RGB consequences, opposite-direction effects and the
separate supplier RGB16 class. Origin coverage beyond these timed contrasts is
an exactness requirement. No claim is made for unmeasured performance cells.

Before stage 1, establish authored 1/2/4/8-worker parity and failure gates and
separate allocation-only baseline/selected decode on the three development
products, both styles, one/eight workers (24 points). If internally surviving,
complete fresh exactness for all nine RarePlanes products, both styles and
1/2/4/8 workers: encoded bytes/metadata and changed-decoder native samples from
both origins. Complete corresponding three-chip SpaceNet Emuella-origin coverage.
Compare resource bounds/peaks with baseline and existing admissible limits;
allocation measurements for each affected operation stay outside headline runs.
Unchanged baseline resource evidence may be reused when all identities apply.
A primary rejection needs no expensive unrelated cohort; the removed production
experiment cannot support a default improvement claim. Retain oracle tests and
canonical correctness for the delivered source. Re-profile the selected decoder
on all six development cases (six operation samples) after its fixed choice,
regardless of stage-1 disposition, without headline inference or further tuning.

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
