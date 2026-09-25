# Prospective caller-boundary experiment

`classic-forward53-caller-boundary/v1` tests one source-level ownership change.
Production remains unchanged. This is neither historical causal reconstruction
nor production qualification. Codec owns the source-only C archive and compiled
code interpretation; benchmark owns the opt-in controller and unchanged estimator;
workspace owns the frozen experiment and disposition.

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
