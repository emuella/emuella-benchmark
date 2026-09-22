# Balanced exclusive-CPU production A/A results

The finite `balanced-measurement-stability-v1` cohort completed with **twelve valid
sessions and all 964 calls retained**: four preflights and 960 timed fresh-process
calls. The observation window was 1,115.082465135 seconds (18 minutes 35 seconds),
with 46,407,399 bytes at completion, within two hours/2 GiB. No failures,
replacements, warmups, extra rounds or concurrent codec benchmarks occurred.
Runner placement restoration and the helper's separate post-removal verification
both passed. Frequency/boost, global SMT, IRQ routing and security were unchanged.

Three cells are **supported in this limited study**: Boca RGB8 bypass encode/8,
Mansfield RGB8 style-zero decode/8, and the same decode/1. **Mansfield RGB16 bypass
encode/8 is not consistently demonstrated**: all three sessions exceed the strict
+1% upper-bound check. This is an operationally valid finding of inadequate
precision for that requirement, not an invalid run or a candidate rejection.
All 24 orientation intervals contain zero and retain the legacy `equivalent`
verdict at 5%; that does not make the +1% precision requirement pass.

## Identities, condition and execution boundary

The [prospective operational freeze](https://github.com/emuella/emuella-workspace/blob/25a2ca74097911df18cbf948492f9ab4f5979a22/docs/balanced-measurement-stability.md)
and [benchmark protocol](measurement-stability.md) governed the new condition.
Runner `dd4f852ab90a66bab4798d2fa03f2fff1c5d8d2c` used original production worker
source `d9b35866f01f7fc3be70303a6f4456f297800349` and codec
`975a5e734773578f61abf76d5fddfbd837f3bd7d`. Both labels invoked the same executable,
SHA-256 `278066dffd584d4ffe0624ba3cf26401656d290c0bf2bdf56aa90e46d3bd9ade`.
The rebuilt binary differs from the cleaned historical binary; source, recorded
rustc 1.97.1/LLVM 22.1.6 and all six library hashes match the inherited build.
No panel or diagnostic instrumentation was compiled into this worker.

The authorised systemd/cgroup-v2 exclusive cpuset used partition **`root`**, keeping
normal internal scheduler load balancing. Workers used physical CPUs 0–7, or CPU0
for the one-worker control. SMT siblings 16–23 were reserved and excluded from
worker affinity. Ordinary workloads, controller and telemetry used 8–15,24–31,
on the other L3 domain. The worker and available ancestor CPU quotas were
unlimited. NUMA node 0 and package 0 remain shared; kernel/IRQ activity and shared
package/memory interference are residual limitations. Affinity alone is not the
reservation. Full original/affected settings and restoration receipts remain local.

`amd-pstate-epp` / `powersave` / `balance_performance`, boost 1 and limits
624194–5756452 kHz were frozen and unchanged. Effective-frequency, migration and
thermal-throttle counters were unavailable. Available task throttle counters did
not increase. Frequency snapshots cannot establish effective frequency or cause.
External pressure, CPU accounting and context switches are retained; none alters
the operation clock or creates an outcome-dependent invalidity rule.

Original MQ, packed-default encoding, W batches and forward traversal, tuned perf,
ThinLTO/one codegen unit, SIMD off, D2/RCT/direct/global and inherited resource
limits were retained. Loading, hashes, stream inspection and exactness remained
outside the operation clock. All 964 responses were exact. Labels stayed outside
requests; every call used one operation in a fresh process, with zero warmups.

Frozen preparation SHA-256:
`5faab2ad5a9534ed28ff9a4a80106052c239c4f992001d6301e0a6cd884e238e`.
Frozen live binding SHA-256:
`b03ec62b5f6fe9092b708d9ecb362899ad73b196cad864a9d0920158bd235f1f`.
The [allowlisted observations](balanced-measurement-stability-observations.json)
retain every sample, ordered pair, interval, variability/covariance/order measure,
projection, process resource record, input/stream/library hash and session receipt
hash, without pixels or local paths. Full retained report SHA-256:
`8e63bfe79070d086dbf5114aaeac4569e7a3f125fd81fc56ad2a5797f5295272`.

The completed [four-call diagnostic](parallel-execution-diagnostic-results.md)
is separate execution evidence. This production cohort's decoder means are about
299 ms at eight workers versus 1,813–1,815 ms at one worker. Whole-process CPU/wall
ratios average 3.357, 2.157, 5.051 and 0.964 for cells 0–3 respectively. These
support multi-core consumption and do not reproduce the historical gross
serialisation warning. They include setup and verification: they are not
operation-scoped per-thread utilisation, proof of simultaneous eight-core useful
work, or a causal comparison with the old condition. No new instrumentation ran.

## Session-local inference and descriptive checks

Cell 0: Boca RGB8 bypass encode/8. Cell 1: Mansfield RGB16 bypass encode/8.
Cell 2: Mansfield RGB8 style-zero common OpenJPEG-origin decode/8. Cell 3: same
stream decode/1. Each session contains forty adjacent alternating pairs, twenty
AB and twenty BA, following sweeps 0123, 2301, 3210 and frozen starting labels.
Separate launches do not establish independence.

The actual unchanged production comparator uses a ratio of arithmetic means,
its marginal critical-value/df construction and a 99% per-case interval. Zero
inclusion is inclusive; the A/A upper check remains strictly `< +1%` in both
directions. Reversal uses the same observations and is sensitivity analysis.

| Session | Cell | A / B mean (ms) | B/A 99% interval (%) | A/B 99% interval (%) | B/A width (pp) | B/A change (%) |
|---|---:|---:|---|---|---:|---:|
| 00 | 0 | 743.926 / 743.666 | [-0.4567, +0.3884] | [-0.3869, +0.4588] | 0.8451 | -0.0350 |
| 01 | 1 | 30.345 / 30.420 | [-1.3224, +1.8404] | [-1.8072, +1.3401] | 3.1628 | +0.2483 |
| 02 | 2 | 298.937 / 298.968 | [-0.6900, +0.7156] | [-0.7105, +0.6948] | 1.4056 | +0.0103 |
| 03 | 3 | 1813.782 / 1814.697 | [-0.1587, +0.2600] | [-0.2593, +0.1589] | 0.4186 | +0.0505 |
| 04 | 2 | 298.506 / 298.998 | [-0.6013, +0.9364] | [-0.9277, +0.6049] | 1.5377 | +0.1648 |
| 05 | 3 | 1814.356 / 1814.017 | [-0.1703, +0.1332] | [-0.1330, +0.1706] | 0.3035 | -0.0187 |
| 06 | 0 | 744.938 / 745.731 | [-0.5064, +0.7224] | [-0.7172, +0.5090] | 1.2288 | +0.1065 |
| 07 | 1 | 30.247 / 30.183 | [-1.6471, +1.2465] | [-1.2312, +1.6747] | 2.8936 | -0.2114 |
| 08 | 3 | 1812.648 / 1812.515 | [-0.1272, +0.1127] | [-0.1126, +0.1274] | 0.2399 | -0.0073 |
| 09 | 2 | 298.405 / 299.137 | [-0.3183, +0.8111] | [-0.8045, +0.3194] | 1.1294 | +0.2450 |
| 10 | 1 | 30.439 / 30.281 | [-2.1698, +1.1592] | [-1.1459, +2.2180] | 3.3290 | -0.5207 |
| 11 | 0 | 746.752 / 744.659 | [-0.9317, +0.3770] | [-0.3756, +0.9405] | 1.3087 | -0.2802 |

Width and displacement are distinct. RGB16 intervals are about 2.89–3.37
percentage points wide across orientations; the largest observed arm displacement
is about 0.523%. Zero inclusion therefore coexists with failure to exclude +1%.
No tails were removed, observations centred, quiet sessions selected or sessions
pooled. The larger bound across directions is +1.8404%, +1.6747% and +2.2180%
for RGB16 sessions 01, 07 and 10 respectively.

| Session | A / B CV (%) | Pair correlation | Acquisition lag-1 | Second/first change (%) | AB / BA B/A change (%) |
|---|---:|---:|---:|---:|---:|
| 00 | 0.4071 / 0.4752 | -0.391 | -0.338 | -0.0129 | -0.0479 / -0.0221 |
| 01 | 1.4167 / 1.8759 | +0.071 | +0.094 | -0.1148 | +0.1335 / +0.3627 |
| 02 | 0.7344 / 0.7324 | +0.070 | +0.130 | +0.0557 | +0.0660 / -0.0454 |
| 03 | 0.1688 / 0.2679 | +0.266 | +0.223 | -0.0102 | +0.0403 / +0.0607 |
| 04 | 0.7473 / 0.8549 | -0.113 | -0.053 | -0.0805 | +0.0841 / +0.2456 |
| 05 | 0.1760 / 0.1408 | +0.112 | +0.128 | +0.0013 | -0.0174 / -0.0200 |
| 06 | 0.5278 / 0.7533 | -0.153 | -0.197 | +0.1639 | +0.2708 / -0.0574 |
| 07 | 1.5986 / 1.4275 | -0.158 | -0.096 | +0.3406 | +0.1288 / -0.5490 |
| 08 | 0.1129 / 0.1375 | +0.286 | +0.235 | +0.0179 | +0.0106 / -0.0253 |
| 09 | 0.4985 / 0.6773 | -0.086 | -0.068 | -0.0170 | +0.2280 / +0.2621 |
| 10 | 1.9251 / 1.5672 | -0.238 | -0.008 | +0.2865 | -0.2361 / -0.8034 |
| 11 | 0.9177 / 0.4520 | -0.235 | -0.143 | -0.3646 | -0.6429 / +0.0848 |

Pair correlation ranges from −0.391 to +0.286. Session 11 has a −0.3646% second-
position difference and AB/BA changes of −0.6429%/+0.0848%; session 10 also shows
order differences. These remain descriptive, with all vectors/covariances/trends
available in JSON. Weak covariance promises no paired-inference benefit, and
absence of a visible pattern would not prove independence or stationarity.

## Planning projections, not further observations

Each entry gives the larger orientation upper bound (%), **zero-effect centre /
observed displacement retained**. Every session is retained. Full projected lower
bounds, widths and both orientations are in the observations file.

| Session / cell | 20 pairs | 40 pairs | 80 pairs | 160 pairs |
|---|---:|---:|---:|---:|
| 00 / 0 | 0.6508 / 0.6860 | 0.4237 / 0.4588 | 0.2880 / 0.3231 | 0.1997 / 0.2348 |
| 01 / 1 | 2.4543 / 2.6998 | 1.5920 / 1.8404 | 1.0799 / 1.3290 | 0.7478 / 0.9970 |
| 02 / 2 | 1.0839 / 1.0943 | 0.7052 / 0.7156 | 0.4792 / 0.4895 | 0.3322 / 0.3425 |
| 03 / 3 | 0.3216 / 0.3720 | 0.2095 / 0.2600 | 0.1424 / 0.1930 | 0.0988 / 0.1493 |
| 04 / 2 | 1.1851 / 1.3508 | 0.7708 / 0.9364 | 0.5236 / 0.6891 | 0.3630 / 0.5282 |
| 05 / 3 | 0.2332 / 0.2519 | 0.1519 / 0.1706 | 0.1033 / 0.1220 | 0.0717 / 0.0904 |
| 06 / 0 | 0.9469 / 1.0527 | 0.6160 / 0.7224 | 0.4186 / 0.5251 | 0.2902 / 0.3968 |
| 07 / 1 | 2.2508 / 2.4643 | 1.4611 / 1.6747 | 0.9915 / 1.2048 | 0.6867 / 0.8997 |
| 08 / 3 | 0.1842 / 0.1916 | 0.1200 / 0.1274 | 0.0816 / 0.0890 | 0.0566 / 0.0640 |
| 09 / 2 | 0.8687 / 1.1145 | 0.5653 / 0.8111 | 0.3841 / 0.6298 | 0.2663 / 0.5118 |
| 10 / 1 | 2.6044 / 3.1337 | 1.6892 / 2.2180 | 1.1457 / 1.6734 | 0.7933 / 1.3200 |
| 11 / 0 | 1.0140 / 1.2939 | 0.6594 / 0.9405 | 0.4479 / 0.7293 | 0.3105 / 0.5919 |

The actual comparator buckets are 3.287/3.030/2.915/2.860 for 20/40/80/160 samples
per arm (df 19/39/79/159). These plug-in calculations hold each session's SD fixed
and assume independent stationary future observations; neither assumption is
proved. More samples do not remove persistent displacement. The session-10
160-pair zero-effect upper is +0.7933%, but it is +1.3200% when the observed
displacement is retained. No assessed count supports a consistent both-direction
+1% planning result across all three RGB16 sessions.

The previously proposed forty-pair full-matrix confirmation cannot be justified
from these results. No new confirmation manifest is selected or launched here.
Workspace owns the full 28-endpoint register and the next bounded engineering
review of the product rationale for the inherited critical margins/scope against
finite measurement cost. That review is a recommendation, not a margin change,
endpoint deletion, estimator adoption or permission to rescue this candidate.
The existing primary 99%/5% gain, 10 ms saving, correctness/resource and critical
non-regression gates remain intact; the candidate stays qualification-pending.

The study does not certify 99% coverage, a 1% false-positive rate, power, future
stationary variance or a probability of passing all critical endpoints. The four
cells do not directly qualify one-worker encoding, other styles, Tok, PAN/MSI16
or SpaceNet. Historical [shared-host](precision-feasibility-results.md) and
[isolated-partition](measurement-stability-results.md) evidence remain separate;
no pooling or environmental variance-reduction claim is made. Reserved execution
is relevant to deployments able to reserve comparable resources, with limited
transfer to ordinary shared hosts.

## Reproduction and retention

The approved RarePlanes evidence store retains the frozen preparation/binding,
all call requests/responses/environment/accounting, twelve session receipts,
launch/completion, original settings, separate restoration verification and bounded
delivery receipts. Evidence identity is `balanced-measurement-stability-v1`.
The existing `measurement-stability.py analyse` command reconstructs the report
from those observations and the frozen comparator; the retained delivery projection
script reconstructs this public JSON. Merged integration compares reconstructed
hashes without repeating any real-input call. Disposal applies only to registered
builds and task Git resources, never to protected observations or imagery.
