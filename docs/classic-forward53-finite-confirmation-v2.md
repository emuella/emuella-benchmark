# Separately authorised finite forward 5/3 confirmation v2

`scripts/finite_confirmation_live.py` is the owner acquisition path for
`classic-forward53-finite-confirmation/v2`. The closed v1 attempt remains
**DECLINED BEFORE LAUNCH**, with zero corpus starts. V2 requires its own explicit
engineering-owner authority. Neither the reusable scheduling capability nor this
runner grants permission to reopen an attempt, acquire inputs or promote code.

The workspace owns the complete register, design, source treatment and authority.
The `derive` command verifies the externally pinned v1 manifest against its owner
register and design through `finite_confirmation_analysis.py`. It copies every
endpoint, threshold, ancillary dependency and scheduled call unchanged, adding only
the v2 schema, predecessor digest, authority locator and reusable condition.
V1 files are never rewritten. No historical A/A measurement enters inference or
becomes an additional prerequisite measurement campaign.

## Fixed execution

The schedule contains 27 contrasts of 40 pairs and endpoint 11 of 160 pairs:
1,240 pairs, 2,480 ordinary calls, 56 preflights and 112 separate allocation calls.
The exact order is 00,02,01,03,10,11,04–09,12–27. Every endpoint starts with its
registered preflights, then its prerequisite allocation group, then ordinary calls.
The original baseline/candidate labels, alternating adjacent AB/BA pair order and
call identifiers are retained. No warmups, retry, replacement, trimming, pooling,
extra input invocation or intermediate evaluation of the 160 pairs is available.

The unchanged worker performs one operation in each sequential fresh process.
Preflights use the endpoint's same ordinary operation; their clocks remain outside
inference. Allocation calls use separate instrumented builds with no samples.
Input loading, hashing and exact verification remain outside the operation clock.
Whole-process wall, CPU and peak RSS are separate facts, with raw worker/resource
logs retained even when a process fails. These measurements do not substitute for
allocation query or peak proofs. Raw inputs and streams remain in approved stores.

An exclusive started receipt consumes a planned slot before invocation, including
failed launches. Every completed or failed call retains its request and result;
interruption retains a failed receipt whenever the process permits cleanup. A hard
kill may leave a started receipt without a terminal receipt, which is incomplete
evidence. The attempt and transport each have exclusive start records. Failed or
incomplete attempts cannot be restarted in the same preparation. The owner must
not prepare another directory as a replacement attempt.

The two-hour window starts immediately before the first primary preflight and
includes allocation calls, environment checks, comparisons and controller work.
The global limits remain 2,648 starts, 2 GiB new evidence and 30 GiB registered
build scratch. Before each invocation the runner reserves 150 seconds and 1 MiB
of evidence space; the worker timeout remains 120 seconds and address-space cap
8 GiB. Worker files have a 128 KiB per-file ceiling to bound failed output within
that receipt headroom. The inherited ordinary endpoint caps remain 1,800 seconds
and 64 MiB. Separate allocation evidence stays within the 1 MiB per-call allowance.
Safety restoration remains required after an observation cap is exhausted.

Identity, exactness, resource or environment failure stops immediately. Allocation
queries must match between arms, allocation peak must fit the query and 768 MiB,
and output must fit its query and 64 MiB. Allocation request counts and process RSS
are separately recorded; they are not equality gates. A later endpoint is attempted
only after the earlier endpoint's full count satisfies its mandatory predicates.

Analysis calls the unchanged owner comparator through separately bound 40- and
160-pair wrappers, preserving the ratio of arithmetic means, conservative df
buckets and directional predicates. The primary requires its 99% upper bound
strictly below −5% and arithmetic-mean saving at least 10 ms. Every critical
endpoint requires its upper bound at most +1%. Faster candidate observations need
not satisfy reversed ±1% A/A equivalence. Legacy ±5% verdicts remain separate.
Unresolved required intervals produce **NOT QUALIFIED WITHIN BUDGET**; failed
requirements produce **NOT SELECTED**; operational failures produce
**OPERATIONALLY INCOMPLETE**. Passing all offline gates is still not permission to
promote production: complete independent engineering and restoration gates remain.

## Preparation and immutable bindings

Build four fresh receipts using the existing `openjpeg-refresh.py build` command:
baseline/candidate ordinary, and baseline/candidate with `--allocation-diagnostics`.
Use the frozen codec revisions `975a5e734773578f61abf76d5fddfbd837f3bd7d` and
`d60859a8595554be52c8748a8e8c85b69614fea5`. Build from clean committed source;
the benchmark worker source must match the live runner's worker source. The
runner admits only perf, effective ThinLTO/one-codegen-unit, parallel enabled,
SIMD disabled, unchanged MQ/window and unset backend selectors. Build receipts,
compiler logs, runtime libraries, source files and exact executables are bound.
Comparators require the existing `estimator_identity` provenance format for their
specific fixed count. Build and review everything before acquiring the lease.

The private absolute-path JSON configuration contains:

| Key | Required value |
|---|---|
| `authority` | Separately reviewed v2 authority locator |
| `contract` | `v1`, `v1_sha256`, `register`, `design`, `manifest`, `manifest_sha256` |
| `arms` | `baseline` and `candidate`, each with `ordinary` and `resource` build-receipt paths |
| `codec_sources` | Clean exact baseline and candidate source checkout paths |
| `benchmark_source` | Clean source checkout used for all four worker builds |
| `estimators` | `40` and `160`, each the corresponding comparator executable path |
| `stores` | `rareplanes` and `spacenet`, each with existing `prepared`, `streams` and new `output` paths |
| `allocation_identities` | Exactly 14 objects with `case_id`, `style`, `raw_sha256`, `stream_sha256` |
| `prerequisites` | `source_correctness`, `independent_decode`, `output_failure`, `parallel_route`, each with reviewed evidence `path` and `sha256` |
| `build_root` | Registered v2 campaign scratch root with its owner marker |
| `evidence_roots` | All new approved-store metadata roots, including both outputs and any retained binding/check evidence root |

The 14 allocation identities bind seven cases and both styles. Mansfield RGB8's
allocation calls require its retained Emuella encode stream even though its
registered ordinary endpoints are OpenJPEG-origin decode controls. The input
review must authenticate that stream and its independent reconstruction receipt.
The `parallel_route` evidence combines the frozen implementation/source review with retained balanced execution diagnostics and A/A route observations. Preflight receipts expose descriptive whole-process CPU/wall ratios without adding a new threshold or inferential sample.
An input digest proves identity; it does not itself prove rights or correctness.
The independent prelaunch review authenticates the prerequisite evidence and its
coverage. Endpoint and allocation identities are checked against the frozen request
and each worker response. Ordinary workers cannot silently change layout or limits.

Output roots must be fresh siblings of the selected prepared/stream directories
in their existing approved stores. Additional budget roots must be separate
metadata directories in those stores. No whole-store or overlapping budget root
is accepted. The registered build root must carry the workspace scratch marker for
`classic-forward53-finite-confirmation-v2`. Preparation retains the exact manifest,
build receipts, requests, source identities, comparators, installed package and
host frequency/boost policy. Independent review must pin the preparation digest
before transport. Per-call filesystem identities detect changes to bound inputs,
builds, dependencies and evidence; workers verify raw and stream hashes on every
operation, and full source/build/input checks bracket acquisition.

```sh
python3 scripts/finite_confirmation_live.py derive \
  --v1 V1.json --sha256 V1_SHA --register REGISTER.json --design DESIGN.json \
  --authority REVIEWED_V2_LOCATOR --output V2.json
python3 scripts/finite_confirmation_live.py prepare \
  --config CONFIG.json --output APPROVED_OUTPUT/preparation.json
```

These commands do not start corpus workers or create a reservation. Retain the
resulting SHA-256 outside the preparation, with the exact reviewed runner revision.

## Reusable admission and restoration

After review, the operational owner starts one fresh installed `balanced-reusable`
lease using the separately authorised v2 locator. The historical installed package
is used unchanged; this runner does not modify privileged source or policy. See
[the installed launcher contract](measurement-reservation.md#installed-reusable-balanced-launcher).

```sh
python3 scripts/finite_confirmation_live.py execute \
  --preparation APPROVED_OUTPUT/preparation.json --sha256 REVIEWED_PREPARATION_SHA \
  --authority-receipt FRESH_LEASE/public/authority.json
```

`execute` runs outside the reserved controller. It verifies the root-owned current
lease, installed package, authority and recovery helper, then uses the lease's
single ordinary-user command transport to enter `run`. Direct acquisition without
that outside restoration owner and the installed controller placement is rejected.
Admission explicitly requires `measurement-balanced-reusable-qualification/v1`,
`condition: balanced-reusable` and exclusive `root` partition with normal balancing.
Worker CPUs are 0–7, reserved unused siblings 16–23, controller CPUs 8–15,24–31.
Task and effective ancestor CPU quotas must be unlimited, and ordinary workload
exclusion, topology, frequency/boost policy and worker emptiness must hold.
Historical isolated, balanced-diagnostic or balanced-A/A receipts are rejected.

The ordinary controller restores its own affinity and verifies its worker group is
empty on success, failure and interruption. The outside owner always invokes the
installed `stop` and `verify` actions after transport, independently of observation
success or exhausted caps. Their retained output and root-owned restoration,
journal and launcher-verification receipts must identify the same lease and
installation. An unresolved or mismatched restoration prevents successful
completion. A hard termination of the outside process still relies on the installed
lease expiry/ExecStopPost safety mechanism; the owner must obtain independent
verification before terminal closeout. Never interpret absent terminal evidence as
successful restoration.

All observation rows, environment snapshots, endpoint decisions and missing call
identifiers stay in the approved output roots. The completion record labels the
statistical result separately from production authority and independent restoration.
This path adds no external codec speed anchor and consumes no proprietary or
private-reference material.
