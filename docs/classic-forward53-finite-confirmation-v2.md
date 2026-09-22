# Separately authorised finite forward 5/3 confirmation v2

The v2 attempt is closed as **NOT QUALIFIED WITHIN BUDGET**. Production retains
the existing forward transform and defaults. The primary passed, but the fifth
completed endpoint did not resolve its mandatory +1% non-regression bound. The
runner stopped at that gate; the remaining 23 endpoints were not started.

The [factual evidence](evidence/classic-forward53-finite-confirmation-v2.json)
records all 28 statuses, bindings, counts and restoration facts. The protocol below
remains the record of this completed attempt; it supplies no authority for another
attempt, rescue patch or retest.

## Terminal observations

The one acquisition used independently reviewed runner
`71049b39236cf4052b95cda02445f32387b7f621` and preparation SHA-256
`4c723506f77a9c539bd14c88a60831afbcb12e279fa6f9919dc30d019aa10732`.
All five completed endpoints received exactly 40 pairs. Times below are arithmetic
means of operation samples; intervals are the unchanged 99% candidate/baseline
relative-time intervals.

| Endpoint | Fixed encode workload | Baseline mean (ms) | Candidate mean (ms) | Relative interval | Required gate |
|---|---|---:|---:|---|---|
| 00, sole primary | Boca RGB8, bypass, eight workers | 733.863 | 463.279 | −37.3820% to −36.3553% | Pass |
| 02 | Boca RGB8, style zero, eight workers | 789.419 | 521.635 | −34.5655% to −33.2717% | Pass |
| 01 | Boca RGB8, style zero, one worker | 2,430.240 | 2,289.434 | −5.9325% to −5.6551% | Pass |
| 03 | Boca RGB8, bypass, one worker | 2,045.878 | 1,897.306 | −7.4385% to −7.0852% | Pass |
| 10 | Mansfield RGB16, bypass, one worker | 134.332 | 135.302 | +0.38703% to +1.05799% | Unresolved |

The primary saved **270.583753075 ms** on the observed arithmetic means and passed
both its strict −5% upper-bound and 10 ms saving predicates. Endpoint 10's upper
bound was **+1.0579857318%**, above the required +1%; its lower bound remained below
+1%. This is an unresolved critical gate, not demonstrated regression beyond the
unacceptable margin. Its separate legacy ±5% verdict was `equivalent`, which does
not satisfy the tighter +1% requirement. The primary gain cannot waive this gate.

Acquisition stopped after **458 starts**: 400 ordinary calls, ten preflights and
48 allocation calls, with no failed worker calls or replacement observations.
Endpoint 11's fixed 160-pair session never started, so there was no intermediate
evaluation. All 2,190 later scheduled calls remained unstarted. The recorded
observation window was **1,140.33395129 seconds**; evidence and registered builds
occupied 33,121,720 and 2,061,543,743 bytes at acquisition completion. The stop was
the unresolved fixed-count endpoint predicate, not exhaustion of the global
wall-time or storage caps.

Retained reconstruction reproduced the five decisions with no issues, missing
terminal receipts or orphaned receipts. Mandatory checks passed for the reviewed
prerequisites and **observed prefix only**. They do not prove timing or resource
gates for the unstarted endpoints, and the incomplete matrix cannot qualify the
candidate for production. Historical development and A/A observations remain
separate and were not pooled.

The first installed reservation setup failed before its authority receipt,
transport or any corpus start because an unrelated transient app cgroup disappeared
during fail-closed traversal. Its independent privileged verification confirmed
restoration with no issues. The user then explicitly authorised one further setup.
That setup succeeded with the same preparation and acquisition identity and hosted
the **one measured execution**. Ordinary runner restoration and independent
privileged restoration both passed with no issues. The failed setup is retained
separately; it was not a retried or replaced measurement.

## Acquisition contract

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

Initial output roots must be fresh siblings of the selected prepared/stream directories
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

A prelaunch review repair may create an explicitly named preparation checkpoint
in the **same acquisition roots**. Supply the predecessor and its externally
pinned digest; the old bytes, notices and predecessor chain remain untouched:

```sh
python3 scripts/finite_confirmation_live.py prepare --config CONFIG.json \
  --output APPROVED_OUTPUT/preparation-reviewed.json \
  --previous-preparation APPROVED_OUTPUT/preparation.json \
  --previous-sha256 REVIEWED_PREDECESSOR_SHA
```

The checkpoint verifies the same manifest, authority, treatment and acquisition
configuration, allowing updated prerequisite evidence. Both output roots may
contain only their notices, the verified preparation chain and the shared
`prelaunch.lock`. Any transport, acquisition, worker-start or other unexpected
metadata blocks this operation. The checkpoint and outside execution share the
lock, so a preparation update cannot race acquisition. The new checkpoint records
its predecessor digest and requires a new independent review before launch.
This facility cannot replace an attempted execution or create another attempt.

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
lease, installed package, authority and recovery helper. It authenticates the
installed `installation` and `lease_id` extension fields against the frozen
installation and current owned lease before projecting the exact common admission
schema. Environmental admission, including schema, quota and expiry failures,
runs inside the owned-lease cleanup guard. An unauthenticated or different lease
is never stopped. Once ownership is proved, every admission failure or interruption
reaches installed cleanup. Successful admission then uses the lease's
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
installation. The retained independent record embeds exact authority and journal
text, plus restoration and privileged verification objects, so later reconstruction
can check their bindings without a live reservation. An unresolved or mismatched restoration prevents successful
completion. A hard termination of the outside process still relies on the installed
lease expiry/ExecStopPost safety mechanism; the owner must obtain independent
verification before terminal closeout. Never interpret absent terminal evidence as
successful restoration.

All observation rows, environment snapshots, endpoint decisions and missing call
identifiers stay in the approved output roots. The completion record labels the
statistical result separately from production authority and independent restoration.
This path adds no external codec speed anchor and consumes no proprietary or
private-reference material.


## Retained-data reconstruction

After acquisition and independent terminal verification, reconstruct the complete
v2 matrix without rerunning a corpus operation:

```sh
python3 scripts/finite_confirmation_report.py \
  --preparation APPROVED_OUTPUT/preparation-reviewed.json --sha256 REVIEWED_PREPARATION_SHA \
  --v1 RETAINED_V1.json --register REGISTER.json --design DESIGN.json \
  --estimator-40 FIXED40_EXECUTABLE --estimator-160 FIXED160_EXECUTABLE \
  --output APPROVED_OUTPUT/reconstruction.json
```

The supplied owner files verify the immutable v2 derivation independently of
historical checkout paths. Rebuilt comparators must retain the frozen owner module,
entrypoint and manifest identities. Reconstruction reads retained metadata and
prerequisite evidence only; source worktrees, workers, protected raw/stream payloads
and live reservation state are not required. Exact comparator results are checked
against every retained completed endpoint decision.

The shared analyser explicitly admits v2 and preserves that schema, predecessor,
authority and condition in the output. It produces all 28 endpoint statuses and
keeps the frozen call identities and original receipts. A start without a terminal
receipt is labelled `missing_terminal_receipt`; orphaned receipts and inconsistent
prefixes remain explicit failures. No receipt is relabelled as another attempt.
The reporter rechecks retained request, exactness, environment and allocation
predicates and validates both ordinary runner restoration and the independent
journal/authority/verification bindings. Missing or inconsistent evidence yields
**OPERATIONALLY INCOMPLETE**, never a successful subset. A complete reconstruction
still does not authorise production promotion.
