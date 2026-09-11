# Bounded real-scene classic configuration results

The combined public-facade operating point, style0/one worker to bypass/eight
workers, improved encode and decode on all nine full products. Across the three
separately acquired contrasts there were 50 improved and four inconclusive
comparisons; all 2,160 fresh-process invocations reconstructed exactly.

The eight-request application workload selected eight concurrent single-worker
processes (`8x1`) using development PAN16/RGB8. The original three-way
development schedule run failed its controller-reserve requirement, so its
resource qualification is partial. Its timing observations and frozen selection
are retained with that failure. Boca/Tok fixed-schedule observations passed
their resource checks. A separately declared selected-only development
confirmation passed the repaired resource enforcement; it did not rerun
alternatives or reselect the configuration.

The [machine-readable factual record](evidence/real-scene-classic.json) contains
every contrast, absolute schedule result, diagnostic summary and retained
evidence digest. Protected inputs and streams remain in their authorised store.
The [public recipe](real-scene-classic.md) describes reproduction and boundaries.

## Facade operating point

Each contrast used 20 alternating AB/BA rounds, zero warmups and one measured
public facade call per fresh process, with a 120-second process timeout.
Native layout conversion and owned decode output are inside the facade boundary;
input loading/hashing and full reconstruction verification are outside it.
The unchanged historical estimator uses a conservative 99% per-comparison
interval and a 5% practical gate. No outliers, retries or historical speedup
multiplication were used. There is no family-wide confidence claim.

Means below are milliseconds for style0/one worker → bypass/eight workers.
Every encode and decode entry met the improvement gate.

| Role/product | Encode ms | Decode ms |
|---|---:|---:|
| development PAN16 | 2,126.16 → 230.54 | 1,332.64 → 126.01 |
| development RGB16 | 404.04 → 45.99 | 248.58 → 18.82 |
| development MS16 | 1,138.84 → 126.29 | 714.50 → 57.04 |
| development RGB8 | 2,644.27 → 536.86 | 1,739.47 → 258.25 |
| validation PAN16 | 2,651.45 → 325.59 | 1,629.88 → 177.19 |
| validation RGB16 | 522.80 → 69.40 | 316.97 → 25.56 |
| validation MS16 | 1,478.02 → 189.06 | 923.50 → 83.93 |
| validation RGB8 | 3,519.99 → 762.34 | 2,181.23 → 337.64 |
| regression RGB8 | 3,223.89 → 651.43 | 2,161.90 → 322.30 |

The four inconclusive results are the separate bypass-at-eight encode/decode
comparisons for development RGB8 and Tok RGB8. Their means favour bypass,
but the conservative intervals do not establish the required practical
improvement. These outcomes remain inconclusive.

## Application configuration and resource result

Use classic lossless D2 bypass, explicit 768 MiB working and 64 MiB output
limits, direct/global decode, eight available logical CPUs and an 8 GiB
aggregate application budget. For the measured eight-request PAN16/RGB8
workload, bound concurrency to eight processes with one codec worker each.
Query requirements in the same context as encoding; retain source, output and
verification residency in admission. This configuration does not change library
defaults or the existing nested Rayon decode guard.

The original 240 development cohorts compared `1x8`, `2x4` and `8x1`.
Both alternatives met the predeclared timing eligibility rule; their descriptive
geometric mean ratios were 0.87943 and 0.68177 respectively, selecting `8x1`.
All four `8x1` timing comparisons improved. These application walls include
process startup, input IO/hash checks and full verification. They describe
fresh requests, not a persistent service or a warm decoded-content cache.

Original selected-schedule cohort means are seconds for eight full requests:

| Role/product | Encode s | Decode s | Resource qualification |
|---|---:|---:|---|
| development PAN16 | 2.2747 | 0.8705 | Partial: controller reserve failed |
| development RGB8 | 4.6448 | 1.8989 | Partial: controller reserve failed |
| validation PAN16 | 2.8699 | 1.0812 | Passed observed gates |
| validation RGB8 | 5.9707 | 2.4193 | Passed observed gates |
| regression RGB8 | 5.7006 | 2.3768 | Passed observed gates |

The original development controller process-lifetime high-water was 689.58 MiB,
above its 128 MiB reserve in all 240 rows. The cause is unestablished; no
pre-exec explanation is assumed. The conservative child-peak plus controller
total remained below 2,772.30 MiB. Replacing the reserve with the larger
recorded controller value in admission still fits within 8 GiB, but this is
observed-total evidence and does not turn the reserve failure into a pass.
All raw rows remain unchanged. The original alternative-arm resource
qualification remains partial. Prospective execution checks the controller
reserve before dispatch and after every cohort, and checks the conservative
total RSS after each cohort. Rejections prevent dispatch; post-cohort failures
retain all observations and invalidate ordinary successful coverage.

The selected-only development confirmation completed all 80 ordinary cohorts
and 640 child invocations successfully. Its controller high-water was at most
32.52 MiB, and its conservative total RSS bound was at most 2,114.56 MiB.
PAN16 encode/decode cohort means were 2.2994/0.8701 seconds; RGB8 means were
4.6393/1.9161 seconds. This is a separately identified confirmation, not a
replacement for the original schedule observations.

Boca completed 80 fixed `8x1` cohorts and Tok completed 40, with all 960 child
invocations successful. Their maximum conservative child-peak plus controller
bound was 4,183.64 MiB. All resource values are process observations, not
allocator bytes. Child address-space limits and conservative admission bound
the application; this experiment does not claim a kernel cgroup memory limit.
RGB16/MS16 and other products have no application-schedule qualification.

## Refreshed selected-configuration profile

Ten separate diagnostic cohorts ran eight concurrent single-worker processes
on the five scheduled products: one encoder and one ordinary decoder cohort
per product. All 80 invocations and resource gates passed. Every encoder
reported one actual participant; ordinary decoder task CPU deltas showed one
active application task per process, with zero active Rayon workers. That is
actual one-thread execution, not a pool-width inference.

Summed instrumented encoder intervals put Tier-1 at 81.28–93.59% of the
selected configuration. Serial bypass includes subband preparation and output
appends in that interval. These instrumented clocks are excluded from headline
statistics. The additional one/eight-worker diagnostics covered all nine
products; ordinary direct bypass/eight decode showed activity on eight named
Rayon workers for each product. Task CPU ticks are activity lower bounds,
not exact Tier-1 participants or decoder stage fractions.

The allocation-only probe uses a nested pool. Its additional requested encode
and decode bytes are retained separately from RSS; direct/global decode
allocation remains unobserved. The initial development allocation descriptors
were corrected by a bound explanatory receipt, preserving the original raw
records. No decoder stage fractions are supplied by a different checked path.

## Source, correctness and support boundary

All headline and application timings use codec
`022a0bbd8e4782d59ecaf781fe819c4638e5991e` (tree
`d54c974b8824045b2c86fc0321fd8b9d8ad3664f`). Build evidence binds Rust 1.97.1,
parallel without SIMD, optimisation level 3, ThinLTO, one codegen unit and
line-table debug information. The host was an AMD Ryzen 9 9950X3D, restricted
to logical CPUs 0–7 with the powersave governor. Later codec parsing/doc fixes
were not relabelled as the measured binary.

Development headline/initial diagnostics used benchmark `5804b0a`; development
schedules and reserved measurements used `010ef7e`; the concurrent selected
reprofile used `3e43d5e`. The record retains full revisions and digests.
The prospective resource repair and selected confirmation use `39d7497`.

Every full stream and raw reference was checked against retained independent
decoder receipts with the original tool/result identities preserved. One new
OpenJPEG 2.5.4 full-PAN bypass decode also reconstructed exactly. Separate
public-recipe preparation on merged codec
`6586e3d50f95429b242cb2e3535742b002784f2d` proved eight development streams
and direct/nested reconstruction; those setup clocks are not performance data.

The bounded top-left 256×256 PAN16/RGB16 support probes succeeded with D2
bypass and exact reconstruction. D2 HT returned `Unsupported WaveletTransform`;
D1 bypass requirements returned `Unsupported ComponentLayout`. There is no
common supported depth for this comparison, so no unmatched-profile HT/classic
ratio or codec ranking is claimed.
