# Measurement stability qualification: completed controlled A/A

> **Execution-integrity follow-up:** retained CPU accounting shows effectively
> single-core execution for the nominal eight-worker calls. The original interval
> arithmetic and restoration record stand, but parallel execution and transfer to
> panel confirmation are not qualified. See the [follow-up audit](measurement-execution-integrity.md).
> No new A/A study or panel confirmation has been launched.

`measurement-stability-qualification/v1` completed one prospectively frozen
condition: **all twelve sessions valid, all 964 calls retained**, including four
separate preflights and 960 timed fresh-process calls. The observation window was
2,198.436626098 seconds (36 minutes 38 seconds), with 46,227,929 bytes recorded at
cohort completion, below the two-hour/2 GiB limits. Registered builds occupied
413,796,648 bytes at launch, below 30 GiB. No failed calls, replacements, added
rounds, warmups or simultaneous codec benchmarks occurred. Runner affinity and
empty-worker cleanup passed; the reservation helper separately verified full
restoration with no issues.

All four cells are **supported in this limited study**: each of their three
sessions includes zero and has its upper bound strictly below +1% in both label
orientations. The unchanged production comparator called every orientation
`equivalent` under its legacy verdict. This is neither candidate qualification
nor calibration of coverage, power or universal repeatability.

## Frozen identities and condition

The [reviewed operational checkpoint](https://github.com/emuella/emuella-workspace/blob/d5b773915a770449f3b2a063c4604920795c344e/docs/measurement-stability-qualification.md)
was frozen before preflight. Benchmark runner/worker source was
`d9b35866f01f7fc3be70303a6f4456f297800349`; exact production codec was
`975a5e734773578f61abf76d5fddfbd837f3bd7d`. Both labels invoked the same executable,
SHA-256 `66ce23174bc9f861409ef88bcfccba2c479afdbe172413f338bf99a34ba1d5ac`.
The fresh build is explicitly different from the cleaned historical executable;
rustc 1.97.1/LLVM 22.1.6, six linked-library hashes, tuned perf/ThinLTO/one codegen
unit, SIMD off and original MQ/packed-default/W/traversal were retained. The panel
candidate was neither built nor invoked.

CPUs 0–7 were workers; their SMT siblings 16–23 remained reserved and excluded from worker affinity
(the follow-up counters retain small residual system activity).
An authenticated systemd/cgroup-v2 isolated exclusive cpuset excluded ordinary
workloads. Controller, telemetry and builds used 8–15,24–31 on the other L3 domain.
All cores share package 0 and NUMA node 0; memory/package and kernel/IRQ interference
remain. Driver `amd-pstate-epp`, governor `powersave`, EPP `balance_performance`,
boost 1 and 624194–5756452 kHz limits remained unchanged, as did global SMT and IRQ
routing. These policy labels and frequency snapshots are not effective-frequency
evidence; effective-frequency and migration counters were unavailable.

The [protocol](measurement-stability.md) preserves exact prepared/source/stream
hashes, D2/RCT/direct/global settings, fresh-process boundaries, verification outside
the operation clock, fixed cadence, external accounting and predeclared validity
criteria. Authority and frozen binding SHA-256 are respectively
`a57a7cc922c717a4e2e4aeb81fee2c0efae04c1042048a25f589b03557e38771` and
`5e27912737fbecf98259ead8f4dec233e58ae638d4d77fb88d5392df494b0661`.
Full launch, per-call identity/environment/resource, session, original settings,
failed-setup archival and final restoration receipts remain in the authorised
RarePlanes store. The earlier failed setup admitted no codec call and its original
state was verified before the successful reservation.

[Machine-readable observations](measurement-stability-observations.json) retain
all 960 samples, ordered pairs, means, both actual comparator outputs, full
intervals, variability, covariance, order/dependence diagnostics and every
session's projections. The full retained report SHA-256 is
`ebcb6f701f4ce7fc8aa5e431d381b769d6e8a52889b36a629fafd57600c55c8b`;
individual session receipt hashes are included. Local paths and payloads are
excluded from this public summary. Historical shared-host results remain
[separate](precision-feasibility-results.md); no pooling or causal variance-reduction
claim is made.

## Session-local results

Cell 0 is Boca RGB8 bypass encode/8; cell 1 Mansfield RGB16 bypass encode/8;
cell 2 Mansfield RGB8 style-zero decode/8; cell 3 the same decode/1. Decode uses
the identical common OpenJPEG-origin stream. Each session has forty pairs,
twenty AB and twenty BA, following the frozen three-sweep order and starting arms.
Intervals and point changes below are percentages; width is percentage points.
Zero inclusion is inclusive and the A/A +1% comparison is strictly `<`, unchanged.

| Session | Cell | A / B arithmetic mean (ms) | B/A 99% interval (%) | A/B 99% interval (%) | B/A width (pp) | B/A displacement (%) |
|---|---:|---:|---|---|---:|---:|
| 00 | 0 | 2059.288 / 2059.006 | [-0.3296, +0.3033] | [-0.3024, +0.3307] | 0.6330 | -0.0137 |
| 01 | 1 | 135.305 / 135.107 | [-0.5418, +0.2506] | [-0.2499, +0.5448] | 0.7924 | -0.1465 |
| 02 | 2 | 1823.301 / 1823.512 | [-0.3724, +0.3970] | [-0.3954, +0.3738] | 0.7693 | +0.0115 |
| 03 | 3 | 1798.040 / 1798.017 | [-0.1620, +0.1597] | [-0.1594, +0.1622] | 0.3216 | -0.0013 |
| 04 | 2 | 1822.220 / 1823.563 | [-0.2303, +0.3785] | [-0.3771, +0.2308] | 0.6088 | +0.0737 |
| 05 | 3 | 1798.942 / 1798.431 | [-0.1758, +0.1192] | [-0.1191, +0.1761] | 0.2950 | -0.0284 |
| 06 | 0 | 2062.135 / 2059.889 | [-0.5027, +0.2863] | [-0.2855, +0.5052] | 0.7890 | -0.1089 |
| 07 | 1 | 135.280 / 135.236 | [-0.4162, +0.3535] | [-0.3522, +0.4179] | 0.7697 | -0.0321 |
| 08 | 3 | 1800.202 / 1799.989 | [-0.1682, +0.1447] | [-0.1445, +0.1684] | 0.3129 | -0.0118 |
| 09 | 2 | 1822.586 / 1821.443 | [-0.3948, +0.2706] | [-0.2699, +0.3964] | 0.6654 | -0.0628 |
| 10 | 1 | 135.183 / 135.143 | [-0.4273, +0.3693] | [-0.3680, +0.4291] | 0.7966 | -0.0298 |
| 11 | 0 | 2064.485 / 2065.933 | [-0.3367, +0.4785] | [-0.4763, +0.3378] | 0.8152 | +0.0701 |

Every interval includes zero. Width and displacement are reported separately:
the largest upper bound in either direction was +0.5448%, with no centring or
sample removal. All three sessions per cell meet the limited-study rule.

| Session | A / B CV (%) | Pair correlation | Acquisition lag-1 correlation | Second/first change (%) | AB / BA B/A change (%) |
|---|---:|---:|---:|---:|---:|
| 00 | 0.3657 / 0.2949 | -0.006 | +0.064 | -0.0013 | -0.0150 / -0.0124 |
| 01 | 0.4616 / 0.3665 | +0.167 | +0.073 | +0.0166 | -0.1300 / -0.1630 |
| 02 | 0.4211 / 0.3818 | +0.153 | +0.270 | -0.0747 | -0.0632 / +0.0863 |
| 03 | 0.1716 / 0.1641 | +0.261 | +0.328 | +0.0400 | +0.0387 / -0.0413 |
| 04 | 0.2883 / 0.3466 | +0.153 | +0.068 | -0.0846 | -0.0110 / +0.1584 |
| 05 | 0.1364 / 0.1716 | +0.112 | +0.237 | -0.0053 | -0.0337 / -0.0231 |
| 06 | 0.3951 / 0.4292 | +0.065 | -0.067 | -0.1265 | -0.2353 / +0.0176 |
| 07 | 0.4100 / 0.3935 | -0.145 | -0.127 | -0.0374 | -0.0694 / +0.0053 |
| 08 | 0.1784 / 0.1482 | +0.149 | +0.138 | +0.0330 | +0.0211 / -0.0448 |
| 09 | 0.4217 / 0.2732 | +0.059 | +0.097 | -0.1737 | -0.2363 / +0.1112 |
| 10 | 0.4217 / 0.4099 | +0.121 | +0.072 | -0.1052 | -0.1350 / +0.0755 |
| 11 | 0.4084 / 0.4418 | +0.422 | +0.234 | -0.0186 | +0.0515 / +0.0888 |

Position and run-order differences remain visible. For example, session 09 has
second-position mean −0.1737% relative to first; session 03's acquisition-time
trend correlation is approximately +0.465. Pair correlations range from −0.145
to +0.422. These descriptive values do not establish a cause, independence or a
paired-inference benefit. Separate launches do not establish independence either.
The full vectors, covariance, slopes and acquisition order allow examination
without discarding tails or substituting a different estimator.

## Planning projections, not additional observations

Each entry is the larger of the two orientation upper bounds (%), shown as
**zero-effect centre / observed displacement retained**. All twelve sessions are
retained. The complete lower/upper intervals and widths are in the JSON; these
summaries do not select a quiet session or a favourable direction.

| Session / cell | 20 pairs | 40 pairs | 80 pairs | 160 pairs |
|---|---:|---:|---:|---:|
| 00 / 0 | 0.4869 / 0.5004 | 0.3171 / 0.3307 | 0.2156 / 0.2293 | 0.1495 / 0.1632 |
| 01 / 1 | 0.6108 / 0.7580 | 0.3977 / 0.5448 | 0.2703 / 0.4173 | 0.1875 / 0.3344 |
| 02 / 2 | 0.5919 / 0.6035 | 0.3854 / 0.3970 | 0.2620 / 0.2736 | 0.1817 / 0.1933 |
| 03 / 3 | 0.2470 / 0.2483 | 0.1610 / 0.1622 | 0.1095 / 0.1108 | 0.0759 / 0.0772 |
| 04 / 2 | 0.4679 / 0.5417 | 0.3047 / 0.3785 | 0.2072 / 0.2809 | 0.1437 / 0.2174 |
| 05 / 3 | 0.2267 / 0.2551 | 0.1477 / 0.1761 | 0.1004 / 0.1289 | 0.0697 / 0.0981 |
| 06 / 0 | 0.6078 / 0.7175 | 0.3958 / 0.5052 | 0.2690 / 0.3784 | 0.1866 / 0.2958 |
| 07 / 1 | 0.5924 / 0.6246 | 0.3857 / 0.4179 | 0.2622 / 0.2944 | 0.1818 / 0.2140 |
| 08 / 3 | 0.2403 / 0.2522 | 0.1566 / 0.1684 | 0.1065 / 0.1183 | 0.0739 / 0.0857 |
| 09 / 2 | 0.5124 / 0.5749 | 0.3336 / 0.3964 | 0.2268 / 0.2896 | 0.1573 / 0.2201 |
| 10 / 1 | 0.6131 / 0.6430 | 0.3992 / 0.4291 | 0.2714 / 0.3013 | 0.1882 / 0.2180 |
| 11 / 0 | 0.6269 / 0.6973 | 0.4082 / 0.4785 | 0.2775 / 0.3478 | 0.1924 / 0.2627 |

The actual comparator's critical values are 3.287/3.030/2.915/2.860 for
20/40/80/160 samples per arm (df 19/39/79/159). These calculations hold each
session's SD fixed and assume independent, stationary future observations.
Those assumptions are not proved. Persistent displacement is not removed by
larger counts. No projection changes this completed cohort or supplies power,
coverage, a false-positive rate or a probability of clearing the full matrix.

Forty pairs is a defensible representative planning count under the measured
condition. One-worker encoding, other styles, Tok, PAN/MSI16 and SpaceNet remain
unmeasured here. The workspace owns explicit transfer rationales, the full
28-contrast/112-allocation register, unchanged candidate gates and any proposed
finite confirmation manifest. Such a proposal remains unlaunched and requires
its prospective review and resource admission. The pending panel stays
qualification-pending; no new speedup or candidate non-regression is claimed.
