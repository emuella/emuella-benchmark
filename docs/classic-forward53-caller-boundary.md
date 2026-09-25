# Prospective caller-boundary experiment

`classic-forward53-caller-boundary/v1` tests one source-level ownership change.
Production remains unchanged. This is neither historical causal reconstruction
nor production qualification. Codec owns the source-only C archive and compiled
code interpretation; benchmark owns the opt-in controller and unchanged estimator;
workspace owns the frozen experiment and disposition.

The completed acquisition found **no worthwhile supported repair at this budget**.
C/B's observed change was +2.421219 ms (+0.098508%), with a 99% interval
[−0.120744%, +0.318239%]. Benefit and an adverse intervention effect both remain
unresolved. C/A passed the serial endpoint bound, but that favourable comparison
cannot establish that the boundary change helped. All 126 starts completed
successfully and independent restoration passed. The
[factual evidence](evidence/classic-forward53-caller-boundary.json) retains every
observation, order identity, source/build identity and comparison.

`scripts/caller_boundary_experiment.py` wraps the unchanged worker source
`0db375523ead4ff5113d7e73a77a39b04cff6644`. A is codec
`a7576ad03486e097ac923b8e49cac39a1cbef5d2`; B is archived codec
`4f5bfb39f02e043c9a1f594a8159d3cf86d52c3f`, tree
`259066112bda675e67a8d3eab3dbf9088d18fe91`. C is B plus the reviewed
owning-helper/serial-bypass intervention and authored tests. The source treatment
binds C's exact revision, tree and complete B-to-C diff, plus the prospective
choice of scoped `inline(never)`. It does not enable C in production.

Only full Boca RGB8, style zero, one worker is admitted: 5577 × 5036 × 3
interleaved U8, raw SHA-256
`aaf064a2d6b302d839e7f3c13b99e1344ba749fed53be6daf64f8a6c4c67bfe7` and
14,339,292-byte reference stream SHA-256
`5686eb89ffbf5152d5572441347ec388ae107d0e6790086a817a5529b702843c`.
The unchanged classic worker keeps lossless D2/RCT, 64 × 64 blocks, LRCP,
one layer/tile and the owned-input-to-owned-codestream operation boundary.
IO, hashes and exact native sample verification stay outside its operation timer.
Independent decoder evidence may be reused only for this identical stream.

## Frozen finite acquisition

The schedule has three ordinary preflights A/B/C, then three separate allocation
calls A/B/C, followed by 40 three-arm rounds. Round orders are
`ABC, CBA, ACB, BCA, BAC, CAB` repeated six times, followed by
`ABC, CBA, ACB, BCA`. All 126 slots are fixed. Every operation uses a fresh,
sequential process, zero warmups and no in-process repeats. Instrumented calls
and ordinary preflights never contribute inferential samples.

This explicitly extends acquisition to three arms. It is not the historical
two-arm adjacent AB/BA schedule. Each pair has 20 occurrences in either relative
order, but pairs are not always adjacent. A occurs in positions 0/1/2
14/12/14 times; B and C each occur 13/14/13 times. Every receipt retains round,
six-round block, position and full round order. The estimator remains unchanged.

All 120 ordinary calls must finish successfully before any performance
interpretation. A failed correctness, identity, resource or environment gate
stops immediately. Every started slot, including failed launch, consumes its
place; there are no retries, replacements, extra calls, trimming or pooling.
Missing terminal receipts and all unstarted slots remain explicit in the offline
report. Incomplete evidence yields no successful-subset inference.

The controller requires one freshly authorised installed `balanced-reusable`
lease, exclusive `root` partition with normal balancing. It uses physical CPU 0,
leaves the reserved SMT sibling unused and places the controller off core. It
reuses installed topology, policy, quota and exclusion admission without modifying
the helper. The outside execution owner always attempts installed `stop` and
`verify` after authenticated transport, including failure, and retains independent
restoration. An unauthenticated lease cannot be stopped as though it belonged to
this experiment.

Caps are 45 minutes from the first preflight, 2 GiB of new evidence and 30 GiB of
registered build scratch. Before a start, 150 seconds and 1 MiB of receipt
headroom must remain. The existing 120-second worker timeout, 8 GiB address-space
limit, 768 MiB working limit and 64 MiB output limit are unchanged. Process CPU,
RSS and allocation request counts remain separate observations. No timing pilot,
stage diagnostic or extra corpus screen is provided.

## Binding and commands

Complete source correctness, independent source and acquisition reviews, ordinary
compiled-code comparison and all builds before preparation and reservation.
The source treatment JSON uses `schema: classic-forward53-caller-boundary/v1/source`,
`A`, `B`, `C`, `A_tree`, `B_tree`, `C_tree`, `B_to_C_diff_sha256`,
`intervention: owning-helper-with-serial-bypass`, `inline_never` and
`production_enabled: false`. Diff hashing uses the deterministic full-index binary
Git diff switches in `source_treatment()`.

The local configuration contains:

- `authority`: the fresh workload authority locator.
- `worker_source`, `codec_sources` keyed by A/B/C, and `arms` keyed by A/B/C,
  each with `ordinary` and `resource` build receipt paths.
- `source_treatment`: `{path, sha256}`; `prerequisites`: pinned files for
  `source_correctness`, `source_review`, `acquisition_review`, `independent_decode`,
  `build_provenance` and `compiled_code`. Each new prerequisite also carries
  `source_treatment_sha256`; the identical-stream independent decoder receipt may
  retain its original identity.
- `request`: the exact endpoint request, round zero; `estimator`: the existing
  fixed40 owner-comparator executable.
- `build_root`: registered `classic-forward53-caller-boundary` scratch;
  `store_root`: approved existing corpus store; `output`: fresh acquisition folder;
  `evidence_roots`: distinct non-overlapping metadata folders including output and
  retained binaries/build evidence, all under that approved store. Existing
  prelaunch binding records are counted; protected input folders are excluded.

The selected matched recipe must be decided before corpus execution, with at
most one successful ordinary build per arm. Build receipts bind clean exact
inventories, dependencies, resolved locks, observed flags and features, plus
ordinary/allocation separation. Build-provenance evidence binds the full
inherited environment, actual compiler/linker paths, executable hashes and
versions, target and recipe rationale. Explicit matched tool and library lookup
environment is admitted; flag, profile, wrapper and instrumentation overrides are
not. Existing ThinLTO, one codegen unit, opt-level 3, line-table debug information,
parallel, no SIMD and no ordinary diagnostics remain required.

```sh
python3 scripts/caller_boundary_experiment.py prepare \
  --config /absolute/config.json --output /approved/output/preparation.json
python3 scripts/caller_boundary_experiment.py execute \
  --preparation /approved/output/preparation.json --sha256 FROZEN_SHA256 \
  --authority-receipt /var/lib/emuella-measurement/leases/LEASE/public/authority.json
python3 scripts/caller_boundary_experiment.py report \
  --preparation /approved/output/preparation.json --sha256 FROZEN_SHA256 \
  --estimator /retained/estimator/target/release/classic-treatment-estimator \
  --output /approved/output/report.json
```

`execute` owns the one transport and independent restoration; `run` is only its
installed controller entry point. `report` opens retained metadata and comparator
artifacts, launches no corpus worker and requires no live reservation. Retain
ordinary binaries, symbols, source/build/linker receipts and bounded code extracts
in the approved store before registered scratch cleanup. The unchanged comparator
can be reconstructed through the existing `real-scene-classic.py`
`estimator_build(repo, directory, 40)` helper; its owner/wrapper identity must match
the frozen preparation.

## Interpretation frozen before acquisition

C/B is the sole primary intervention contrast. B/A describes the present cost of
the archived implementation; C/A describes remaining distance from A. Each
contrast uses each arm's 40 ordinary observations exactly once in the existing
ratio-of-arithmetic-means comparator. Reports preserve vectors, absolute means,
savings, relative 99% intervals, order identities and legacy ±5% verdicts.
The three comparisons share samples: this is not 120 independent pairs and no
joint 99% coverage is asserted.

C/B's upper bound strictly below zero supports measured benefit; an interval
containing zero leaves benefit unresolved at this budget. C/A's upper bound at
most +1% separately passes the existing serial bound for this endpoint only.
A favourable C/A alone cannot demonstrate that the intervention helped. There
is no additional 2%/5% gain requirement. Absolute magnitude and independent
engineering value judgement determine whether even a resolved gain is worth
further investment.

When both tests pass, independent review may retain C as a measured repair
candidate for separately authorised qualification. When only benefit is resolved,
the intervention is useful evidence with the serial requirement still unproved.
Otherwise the result is no worthwhile supported repair at this budget, retaining
adverse effects and uncertainty separately. No automatic promotion or next
experiment follows. The entire source-level refactoring is the treatment when
helper bytes or placement also differ; static stack/copy/instruction observations
are never converted to estimated milliseconds. Missing historical binary identity
limits historical interpretation, not this prospective experiment.

## Completed result

The 40 ordinary observations per arm have arithmetic means A **2480.778231 ms**,
B **2457.900420 ms** and C **2460.321638 ms**. The following signed changes are
candidate minus reference; positive values mean slower encoding. Mean savings
have the opposite sign. The JSON retains full precision and all samples.

| Contrast | Mean change | Mean saving | Relative change | 99% relative interval | Legacy ±5% verdict |
|---|---:|---:|---:|---:|---|
| **C/B, sole primary** | +2.421219 ms | −2.421219 ms | +0.098508% | [−0.120744%, +0.318239%] | Equivalent |
| B/A | −22.877811 ms | +22.877811 ms | −0.922203% | [−1.136246%, −0.707702%] | Equivalent |
| C/A | −20.456592 ms | +20.456592 ms | −0.824604% | [−1.039415%, −0.609333%] | Equivalent |

The primary interval contains zero, so this budget supports neither a measured
benefit nor a resolved adverse intervention effect. C/A's upper bound is below
+1%, establishing the existing serial bound for this endpoint only. It does not
resolve the missing C/B benefit. The recorded disposition is **no worthwhile
supported repair at this budget**; C remains an exact source-only archive with
its tests and identities. No repair is promoted and no next experiment is
scheduled automatically.

B/A is faster in this prospective acquisition: it does **not** reproduce the
historical slowdown. Different ordinary executable identities and acquisition
conditions prevent rewriting the closed confirmation or assigning a historical
cause. The previous dispatch and static attribution outcomes remain unchanged.

### Source, compiled boundary and build provenance

C is revision `c6c07420e90cd7b871f7e6b0e3bc813ab384bf8c`, tree
`ff33aaeac39abbbf2d55f4cfa24f2afbfe58c0db`. Its complete B-to-C patch SHA-256 is
`3224ce3fa2412f2317aac3bdb24abcfefe7baca5979eb5e93fb3ac3c358fc9b1`.
The ordinary executable hashes are:

| Arm | Whole-file SHA-256 | `.text` SHA-256 |
|---|---|---|
| A | `459734d9abb32f6090ccaeb6ba660fe26cc95b386a93248554917ffa86b29664` | `93b89dfd851ab69a519671303142b2c01603fd734872f4124c553276018ac7aa` |
| B | `15c1a64ae941a64849a5c2b440bd1f28c760de4ff3af97d01f79e9b2fcff7019` | `2549e52ad8da0279db27149cdfd021410a6f8290a1286080bb9db16efb615e5c` |
| C | `f4167cafc6065ba11d0c2267476a362710bc8d8e2bb0475e44cfbb97e67e4a91` | `c3a251c849d3718cf0c75aa021ed05bbb8b82b4ff9e88b2a361121643b67fbd0` |

The [codec-owned compiled analysis](https://github.com/emuella/emuella-j2k/blob/main/docs/forward53-caller-boundary.md)
proves the requested boundary in these actual executables. C's serial admission
skips the owning helper. Panel preparation, all component execution and panel
destruction remain inside it; no large optional plan/workspace crosses into the
writer. The writer's explicit stack reservation falls from B's 1,144 bytes to
C's 840 bytes, compared with A's 792 bytes. B's two fixed 176-byte option copies
are absent from C's writer. These are structural facts, not time estimates.

Selected B/C original multi-level, bounded 2D and lifting helpers match under
the documented limited normalisation. Their raw bytes and placement differ;
the writer/component boundary also changes instruction and stack context, and
`.text` grows by 256 bytes. Conversion/RCT and assembly remain within that
changed context. Consequently this result measures the complete source-level
refactoring, with the narrower caller-state mechanism only partially isolated.
No claim of identical placement or runtime effects follows from normalisation.

Before any corpus timing, a matched fresh recipe was selected for all arms.
The retained ordinary A/B reconstruction receipts lacked the complete inherited
environment and actual linker identity needed to establish compatibility with
new C. This was a provenance decision with no timing-based binary selection.
Exactly one successful ordinary build and one separate allocation build per arm
were made. No measured executable was rebuilt in response to timings.

The unchanged worker source is `0db375523ead4ff5113d7e73a77a39b04cff6644`;
controller source is `8f00b8efb1ff29305b68b0b62643facd117afceb`.
All builds used rustc 1.97.1 (`8bab26f4f68e0e26f0bb7960be334d5b520ea452`),
LLVM 22.1.6 and the implicit `x86_64-unknown-linux-gnu` host target. Observed
build execution binds the GCC 16.1.1 driver and Rust LLD 22.1.6 linker chain.
The verbose compiler logs retain perf/opt-level 3, ThinLTO, one codegen unit,
existing line-table debug information, parallel, no SIMD and no ordinary
diagnostics. Resolved worker lock SHA-256 is
`5cb1a2d7d5d098c347cc0ccdca0e52ca0315bb3190830ebd45d4c51f616788e8`.
The matched existing OpenJPEG 2.5.4 library was linked; no new external-codec
operation or external implementation inspection was performed.

The approved binding store retains all six executables, symbols, build logs,
source inventories, resolved locks, full minimal build environment and observed
compiler/linker receipts. Public factual evidence records identity hashes and
omits private host paths and linked third-party payloads. Whole-file, executable
section and relevant symbol identity remain distinct. Historical binary equality
is unproved; every measured arm is prospective.

### Correctness, resources, accounting and restoration

All 126 invocations checked the encoded stream hash and reconstructed every
sample exactly. The authenticated existing independent-decoder receipt applies
only to that identical stream; it caused zero additional corpus calls.
Three ordinary preflights and three separate allocation calls were excluded from
inference. All 120 ordinary calls finished before interpretation. There were
zero failures, missing terminal receipts, retries, replacements or unstarted
slots. No sampled or stage-diagnostic corpus operation was performed.

Each separate allocation call reported the same 562,015,740-byte working query,
362,401,748-byte peak additional requested allocation, 707 successful allocation
or reallocation requests, 16,777,216-byte output capacity and 67,108,864-byte
output capacity limit. Every existing resource predicate passed. Allocation
request counts and requested-byte peaks are distinct from process RSS and CPU.

| Ordinary arm | Mean process wall | Mean process CPU | Observed peak-RSS range |
|---|---:|---:|---:|
| A | 5.039759 s | 4.976500 s | 541,818,880–542,912,512 bytes |
| B | 5.016808 s | 4.953250 s | 541,982,720–543,875,072 bytes |
| C | 5.028201 s | 4.960000 s | 541,900,800–542,941,184 bytes |

These descriptive process observations include setup and verification and are
not substitutes for the operation clock. Per-call wall, CPU, RSS and context
switch records remain in the factual extract. Optional unavailable throttle
counters were unavailable; no PMU or dynamic attribution observation is claimed.

The complete observation interval was **653.847357509 seconds**, within the
2,700-second cap. At acquisition completion, counted evidence was 131,217,671
bytes of the 2 GiB cap and registered scratch was 3,476,247,330 bytes of the
30 GiB cap. These are completion snapshots; terminal artifact retention and
scratch lifecycle are owned by final landing evidence.

Installed balanced-reusable lease `8bf30dc9-cab8-46cf-ba0b-149fc206532b` used
the required exclusive `root` partition with normal balancing, workers on CPU 0,
unused reserved SMT sibling 16 and the off-core controller. All before/after
identity and environment gates passed. The outside owner executed independent
stop and verification; ordinary controller restoration and installed host
restoration both passed. No helper modification or global tuning occurred.

Frozen preparation SHA-256 is
`75ee7c802962648bacd8e6909c71b53a4a9b7f9f756480eec4e8c096b94c2d76`;
the original retained offline report SHA-256 is
`25bd665805f4c15076b83c7b8030415a9f12b0920d2c396a99adf97b67cb92c8`.
The report command above reconstructs the completed evidence without launching
another corpus operation. The factual JSON carries its provenance and the raw
observation vectors so reviewers can trace each contrast to its 40 samples.

### Attribution and handling

RarePlanes Dataset, June 2020. J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and
AI.Reverie. [Source](https://registry.opendata.aws/rareplanes/),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
This record adds factual measurements of the existing full Boca RGB8 interleaved
derivative. Catalogue revision `96443cb19dddf756938d87c350067a02cff82648`
and the pinned reviewed rights/notice records authorise this existing local use.
Protected input and derivative payloads remain in their approved store. No new
imagery was acquired; no image, derivative, executable or linked library is
redistributed by this factual record.
