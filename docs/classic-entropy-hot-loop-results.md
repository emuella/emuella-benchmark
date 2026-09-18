# Finite classic entropy result

Neither decoder decision-path variant met the frozen high-bit-depth style-zero
development gate. Both production experiments were removed. The original MQ
arithmetic, packed encoder and W joined scheduler remain unchanged. The retained
changes are an independent test-only entropy oracle, operation-scoped decoder
sampling and the bounded treatment driver.

The [protocol](classic-entropy-hot-loop.md) was frozen at benchmark
`103b259953787205e2fc45ca6cb0ac419dd39ef7` before either candidate was edited or
timed. The [complete factual record](evidence/classic-entropy-hot-loop.json)
retains every operation time, per-case process RSS/CPU, input/build identities,
source checkpoints, aggregate sampling attribution and unstarted conditional gates.

## Diagnosis and finite family

Twelve CPU 0 samples covered complete Mansfield PAN16, eight-band MS16 and RGB8,
encode/decode, style zero/bypass. Source-address attribution assigned respectively
30.97%, 31.19% and 26.05% of style-zero decode cycles to MQ decision/state work;
renormalisation occupied 5.71%, 4.94% and 4.31%. Optimised unresolved boundaries
remain separate. Emuella-generated instructions showed eager successor loads,
early arithmetic writeback and duplicate exchange paths. Out-of-line decoder
calls occupied only 1.1–4.7%, so blanket inlining was not selected.

D1 held interval, code and context locally and delayed successor access while
preserving exchange branches. D2 factored exchange into a Boolean-selected
successor/writeback within the same family. Both preserved the fast MPS return,
probability data, renormalisation, byte IO, raw coding and termination. No other
mechanism, encoder change, scheduler policy or build/affinity sweep was tried.

## Descriptive observations

Every cell below uses three adjacent alternating fresh-process pairs, zero
warmups and one facade operation per process. These means have **no confidence
interval or promotion claim**. The baseline/D2 absolute times belong to the D2
pairs; D1 used its own adjacent baseline observations. Changes are
candidate/baseline minus one, with negative values favouring the candidate.

| Mansfield product | Style | D1 one-worker change | Baseline → D2 one-worker ms | D2 change | Baseline → D2 eight-worker ms | D2 change |
|---|---|---:|---:|---:|---:|---:|
| PAN16 | 0 | -2.35% | 1356.276 → 1306.450 | -3.67% | 205.567 → 199.691 | -2.86% |
| PAN16 | bypass | -4.03% | 681.078 → 675.202 | -0.86% | 122.342 → 117.507 | -3.95% |
| MS16 | 0 | -2.25% | 718.359 → 698.857 | -2.71% | 104.121 → 104.373 | +0.24% |
| MS16 | bypass | -2.93% | 330.229 → 322.198 | -2.43% | 55.494 → 53.761 | -3.12% |
| RGB8 | 0 | -5.45% | 1745.706 → 1672.134 | -4.21% | 277.802 → 263.614 | -5.11% |
| RGB8 | bypass | -6.06% | 1548.116 → 1493.749 | -3.51% | 248.578 → 236.016 | -5.05% |

Eligibility required at least one PAN16/MS16 style-zero mean ratio below 0.95
and every six-case mean ratio at most 1.05. Neither variant met the first
predicate; both met the second. RGB8 changes cannot satisfy the high-bit-depth
predicate. Their three-product style-zero geometric mean ratios were 0.966368
for D1 and 0.964637 for D2. Under the rejection rule, D2 therefore received the
fixed eight-worker description and six operation samples, without promotion.
No third variant, extra screen round, outlier removal or replacement was used.

The six D2 decoder samples still place most work inside Tier-1. MQ decisions,
caller context/traversal and preparation remain substantial; style-zero
renormalisation shares were approximately 3–5%. Source attribution and code
layout changed with the variant, and each point contains one sampled operation;
these shares cannot establish a timing effect or a recovered-cycle estimate.

## Correctness, resources and stopping

All 108 ordinary facade calls and all eighteen sampled calls completed with
exact native samples and the expected complete stream hashes. Timed decoder
arms received identical OpenJPEG-origin streams; initial sampled encoding also
checked unchanged Emuella stream bytes. Inputs were complete, previously measured
Mansfield products, with no crop or resampling.

The independent reference was retained before arithmetic editing. Thirty-one
Tier-1 tests cover every two-byte input, authored sequences reaching all 47
probability states, decision/context/register/byte-state checkpoints, consumed
prefixes, predictable termination results and raw stuffing. Authored block
replay checks independent writer bytes and segment lengths alongside existing
pass/missing-plane metadata and reconstruction checks. Coverage includes styles
zero/bypass, RESET, TERMALL, PTERM, SEGSYM and VSC combinations, all subbands,
1–32 magnitude planes, partial/wide shapes, prefixes and empty/truncated inputs.
Both experimental variants also passed explicit no-std and WASM checks.

Complete screen rejection stopped primary confirmation, internal regression,
the promotion allocation-only cohort, expanded both-origin/1/2/4/8-worker corpus
parity, SpaceNet performance and the external anchor before launch. No success
is claimed for these conditional stages. There is no measured candidate
allocation-only result. Recorded RSS/CPU are whole-process observations including
setup and verification, not codec allocation bounds. The restored production
resource and failure code is baseline-identical; final delivery requires its
canonical caller/failure checks.

The unexercised decoder allocation extension was removed from the final
benchmark source. The existing encoder allocation mode remains unchanged.
Operation sampling uses a separate build and emits no headline timing samples.
Legacy driver arm keys `reference` and `packed` identify baseline/candidate treatments in this study;
both leave the encoder selector unset and use packed-default dispatch.

## Bound identities and retained failures

- baseline-ordinary: codec `bc747f86907aff09e09278e4444ad5932ef4669d`, tree `138634fec5d3b7818b95c85d34881dc0807214a7`, binary SHA-256 `05fb07d5c8dba4cb84755bf56d5318899e9e9d68a98487dc04a7953b07609e8a`.
- d1-ordinary: codec `1e0e920c1096671b04863f81a254720df1d66866`, tree `da49733b249e75be730b38c30bf27303a15d74f1`, binary SHA-256 `265b437daaf97b6814042da1e8d9db1b39cfed765017e277daea78be98be4d5e`.
- d2-ordinary: codec `78534e6ebad9ad5bbec35529ff315d3900f69b8a`, tree `ada31becf548c53773ae66f893000526dac9426f`, binary SHA-256 `39a2e018d4c22aa6eabe05275d6a92fa904ef2a963915222d33f61d58212850c`.

All ordinary workers used the same compiled benchmark source at
`64b250144986d103b5a96f5afa914349d5b3cebf`.
Later removal of unexercised allocation support, driver interpretation/path
repairs and documentation do not relabel those binaries. Rust 1.97.1, optimisation
level 3, ThinLTO, one codegen unit, parallel enabled and SIMD disabled remain
fixed. The host is an AMD Ryzen 9 9950X3D using the powersave governor, CPU 0
or CPUs 0–7, direct/global decode and the original 768/64 MiB, 120-second/8 GiB
settings.

One initial sampling controller manifest-write failure occurred after a successful
encode and before the next call launched. That observation was retained and only
the eleven unstarted calls were resumed. Two oracle-development failures were
also retained: an incorrect test prefix offset and a distribution sequence that
missed eight probability states. Both were repaired before candidate screening.
There were no failed or missing planned codec observations. The original raw
reports remain unchanged; the factual record labels their legacy fields and
three-round interpretation explicitly.

Protected inputs, sample stacks, streams, raw observations, source/assembly
attribution and complete build receipts remain in the approved persistent store.
Only authorised factual summaries appear here. RarePlanes Dataset, June 2020:
J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and AI.Reverie; CC BY-SA 4.0. This fixed
previously measured acquisition is not an untouched holdout or a general codec
ranking.
