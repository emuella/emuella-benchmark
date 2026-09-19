# Precision feasibility v1: results

The completed identical-binary study demonstrates the intended +1% margin only
for the one-worker Mansfield RGB8 decoder within this limited study. The other
five cells are **not consistently demonstrated**. All eighteen sessions are
complete and valid under the frozen criteria; none is incomplete/uninterpretable.
This is a precision finding, not codec optimisation, candidate qualification or
estimator certification.

[Frozen protocol](precision-feasibility.md) · [factual summary](evidence/precision-feasibility-v1/summary.json)

## Collection and identities

All 720 timed calls (360 pairs, eighteen separately launched sessions) and six
separate preflights succeeded: **726 total**, no replacements or omitted samples.
Observation wall was **16.466 minutes** against two hours;
collection evidence was **17.751 MiB** against 2 GiB.
Preflight worker clocks were retained as setup records and excluded from inference.
Exact reconstruction, raw/stream hashes, binary/libraries and clean source were
checked for every call. Process wall/CPU/RSS are separate from operation clocks.

Measured benchmark: `f5007373497adf65cfebcf9b4d42a27e08a92c55`; codec:
`975a5e734773578f61abf76d5fddfbd837f3bd7d`, tree `cea1ed5dd73b11bfaf3ee1260629fab6d3e4919e`.
One worker executable SHA-256 `ab1ab1d50991c41968721d60e522544f28a5cbe4b9bfab712c08fce2bd11e956` served both labels.
Prelaunch binding SHA-256 `684d70e014846c0aa1927795fab7321afd3ed63d270c2f76440cb1b31be37437`.
Actual comparator SHA-256 `12fafbd13bd6a17a1aba1ae86c2cf474ad0b86b87b3b5078e4bd40109be653d2`; estimator binary
`f008514c69e89012d6dc9008ec590e6b3aa695d83469bcbced0197bfe76fe66f`. Production comparator, workers and codec source
are unchanged by this package. No later documentation landing reruns the cohort.

The approved-store observation manifest binds 5495 retained files at capture:
`98a0e92d9bb7a38a90b454bbd5c6fbfe9db70dd63f4f72c76981f69030474a9b`. Later delivery receipts are separate.
RarePlanes attribution: J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and AI.Reverie,
RarePlanes Dataset (June 2020), CC BY-SA 4.0. Inputs, immutable streams, original
licence/lineage and raw local receipts remain in the authorised persistent store.
The following linked JSON records contain factual identities and measurements only.

## Every session, without pooling

A is the primary denominator. “Reverse upper” is the actual comparator applied
to A/B on the same observations, not another experiment. Width is percentage
points (pp); bounds/change are percent. Every interval contains zero in both
directions. +1% requires the upper bound strictly below +1% in both directions.

| Session / cell | A ms → B ms | B/A change | B/A 99% interval | Width pp | Reverse upper | +1% both | Legacy verdict |
|---|---:|---:|---|---:|---:|---|---|
| [00](evidence/precision-feasibility-v1/session-00.json) · Boca RGB8 encode / 1 | 1891.615 → 1888.885 | -0.144% | [-1.682%, +1.416%] | 3.099 | +1.711% | no | equivalent |
| [01](evidence/precision-feasibility-v1/session-01.json) · Boca RGB8 encode / 8 | 604.180 → 601.955 | -0.368% | [-4.990%, +4.473%] | 9.464 | +5.253% | no | equivalent |
| [02](evidence/precision-feasibility-v1/session-02.json) · Mansfield RGB16 encode / 1 | 133.385 → 133.392 | +0.005% | [-0.972%, +0.990%] | 1.962 | +0.981% | yes | equivalent |
| [03](evidence/precision-feasibility-v1/session-03.json) · Mansfield RGB16 encode / 8 | 29.688 → 30.010 | +1.087% | [-2.742%, +5.033%] | 7.775 | +2.819% | no | inconclusive |
| [04](evidence/precision-feasibility-v1/session-04.json) · Mansfield RGB8 decode / 1 | 1744.571 → 1743.645 | -0.053% | [-0.629%, +0.526%] | 1.155 | +0.633% | yes | equivalent |
| [05](evidence/precision-feasibility-v1/session-05.json) · Mansfield RGB8 decode / 8 | 272.117 → 270.224 | -0.696% | [-3.989%, +2.729%] | 6.718 | +4.155% | no | equivalent |
| [06](evidence/precision-feasibility-v1/session-06.json) · Mansfield RGB16 encode / 1 | 133.704 → 133.353 | -0.263% | [-1.438%, +0.931%] | 2.369 | +1.459% | no | equivalent |
| [07](evidence/precision-feasibility-v1/session-07.json) · Mansfield RGB16 encode / 8 | 29.846 → 30.932 | +3.637% | [-8.857%, +16.436%] | 25.293 | +9.718% | no | inconclusive |
| [08](evidence/precision-feasibility-v1/session-08.json) · Mansfield RGB8 decode / 1 | 1745.833 → 1743.383 | -0.140% | [-0.923%, +0.650%] | 1.572 | +0.931% | yes | equivalent |
| [09](evidence/precision-feasibility-v1/session-09.json) · Mansfield RGB8 decode / 8 | 271.816 → 272.608 | +0.291% | [-4.216%, +4.980%] | 9.196 | +4.401% | no | equivalent |
| [10](evidence/precision-feasibility-v1/session-10.json) · Boca RGB8 encode / 1 | 1883.991 → 1896.278 | +0.652% | [-1.198%, +2.522%] | 3.719 | +1.212% | no | equivalent |
| [11](evidence/precision-feasibility-v1/session-11.json) · Boca RGB8 encode / 8 | 603.124 → 594.773 | -1.385% | [-6.270%, +3.826%] | 10.097 | +6.690% | no | inconclusive |
| [12](evidence/precision-feasibility-v1/session-12.json) · Mansfield RGB8 decode / 1 | 1742.856 → 1743.743 | +0.051% | [-0.603%, +0.709%] | 1.312 | +0.607% | yes | equivalent |
| [13](evidence/precision-feasibility-v1/session-13.json) · Mansfield RGB8 decode / 8 | 272.153 → 271.299 | -0.314% | [-3.854%, +3.352%] | 7.206 | +4.009% | no | equivalent |
| [14](evidence/precision-feasibility-v1/session-14.json) · Boca RGB8 encode / 1 | 1890.893 → 1885.805 | -0.269% | [-1.755%, +1.239%] | 2.994 | +1.786% | no | equivalent |
| [15](evidence/precision-feasibility-v1/session-15.json) · Boca RGB8 encode / 8 | 593.108 → 589.031 | -0.687% | [-6.186%, +5.198%] | 11.384 | +6.594% | no | inconclusive |
| [16](evidence/precision-feasibility-v1/session-16.json) · Mansfield RGB16 encode / 1 | 133.467 → 133.579 | +0.084% | [-1.201%, +1.382%] | 2.583 | +1.216% | no | equivalent |
| [17](evidence/precision-feasibility-v1/session-17.json) · Mansfield RGB16 encode / 8 | 29.841 → 31.062 | +4.091% | [-10.258%, +18.750%] | 29.008 | +11.431% | no | inconclusive |

Each JSON retains all forty observations, both complete comparator outputs,
reverse interval/width, process resources, per-arm SD/CV, sample covariance,
AB/BA groups, ordered vectors, descriptive trends and lag-one correlations.
No individual pair percentages replace the ratio-of-arithmetic-means estimand.

## Repeatability by cell

Counts are sessions satisfying zero inclusion and the stated margin in both
directions. +2% and +5% are sensitivity information, not replacement gates.

| Cell | +1% | +2% sensitivity | +5% sensitivity | Planning disposition |
|---|---:|---:|---:|---|
| Boca RGB8 encode / 1 | 0/3 | 2/3 | 3/3 | not consistently demonstrated |
| Boca RGB8 encode / 8 | 0/3 | 0/3 | 0/3 | not consistently demonstrated |
| Mansfield RGB16 encode / 1 | 1/3 | 3/3 | 3/3 | not consistently demonstrated |
| Mansfield RGB16 encode / 8 | 0/3 | 0/3 | 0/3 | not consistently demonstrated |
| Mansfield RGB8 decode / 1 | 3/3 | 3/3 | 3/3 | demonstrated in this limited study |
| Mansfield RGB8 decode / 8 | 0/3 | 0/3 | 3/3 | not consistently demonstrated |

## Conditional sample-cost projections

These plug-in projections hold each session’s observed arm SDs fixed and assume
independent, stationary future process means under the comparator’s model. They
use its real df buckets: 3.287, 3.030, 2.915 and 2.860 for 20/40/80/160 pairs.
No observations are duplicated or bootstrapped, and no additional workers run.
The table shows the **zero-effect upper bound**, maximum of both directions,
as a range across all three sessions. It is a width/precision projection, not
power, empirical coverage or a probability of clearing the matrix.

| Cell | 20 pairs | 40 pairs | 80 pairs | 160 pairs |
|---|---:|---:|---:|---:|
| Boca RGB8 encode / 1 | 1.512–1.875% | 0.983–1.216% | 0.668–0.825% | 0.463–0.571% |
| Boca RGB8 encode / 8 | 4.864–5.930% | 3.144–3.819% | 2.128–2.579% | 1.471–1.781% |
| Mansfield RGB16 encode / 1 | 0.986–1.301% | 0.642–0.846% | 0.436–0.574% | 0.302–0.398% |
| Mansfield RGB16 encode / 8 | 3.942–16.309% | 2.548–10.099% | 1.725–6.671% | 1.193–4.542% |
| Mansfield RGB8 decode / 1 | 0.579–0.791% | 0.377–0.515% | 0.256–0.350% | 0.178–0.243% |
| Mansfield RGB8 decode / 8 | 3.451–4.706% | 2.234–3.039% | 1.513–2.056% | 1.047–1.421% |

The per-session JSON also retains the complete projected intervals and widths
around both a common zero-effect centre and each observed arm displacement.
Do not silently centre the observations: extra samples cannot cure persistent
bias or dependence. At 160 pairs, every eight-worker zero-centred session still
has an upper bound above +1%; a fixed design at that cost is not supported here.

At 160 pairs, the following separates projected width from centring. Widths are
B/A percentage points; upper bounds take the worse of both label directions.
Ranges retain all three sessions, including the tails.

| Cell | Zero-centred width pp | Observed-centre width pp | Observed-centre upper |
|---|---:|---:|---:|
| Boca RGB8 encode / 1 | 0.923–1.138 | 0.921–1.144 | 0.624–1.225% |
| Boca RGB8 encode / 8 | 2.920–3.525 | 2.910–3.498 | 1.846–3.009% |
| Mansfield RGB16 encode / 1 | 0.603–0.794 | 0.603–0.794 | 0.307–0.630% |
| Mansfield RGB16 encode / 8 | 2.368–8.717 | 2.391–8.923 | 2.288–8.567% |
| Mansfield RGB8 decode / 1 | 0.355–0.484 | 0.355–0.484 | 0.231–0.383% |
| Mansfield RGB8 decode / 8 | 2.082–2.820 | 2.066–2.828 | 1.436–1.753% |

| Pairs / cell | Six-cell calls | Six-cell wall minutes, min–max | Approx. metadata MiB | Illustrative 24-cell calls | 24-cell wall hours, min–max |
|---|---:|---:|---:|---:|---:|
| 20 | 240 | 5.4–5.5 | 5.9 | 960 | 0.36–0.36 |
| 40 | 480 | 10.8–10.9 | 11.8 | 1920 | 0.72–0.73 |
| 80 | 960 | 21.7–21.8 | 23.7 | 3840 | 1.44–1.46 |
| 160 | 1920 | 43.3–43.7 | 47.3 | 7680 | 2.89–2.91 |

These are one-session designs. Three separately launched sessions multiply
calls and wall by three. The 24-cell illustration assumes the same workload mix,
not arbitrary future cases. Costs include observed worker loading, verification
and controller overhead, but exclude new build/setup and preflight costs. Storage
conservatively scales collection metadata including fixed receipts; existing
input and stream payloads are reused. Per-case intervals supply no blanket
family-wide confidence or probability that every critical case will pass.

## Environment, order and limitations

The historical placement and frequency policy were unchanged: CPU 0 or distinct
physical CPUs 0–7, SMT siblings 16–23; powersave/amd-pstate-epp, balance_performance,
boost enabled. No compiler/codec contention or frozen identity/policy violation
was observed. The host was shared, not isolated. Sampled CPU pressure some/avg10
ranged 0.02–11.60%, memory pressure avg10 was zero, and minimum available memory
was 82,946,692 KiB. Sampled frequency ranged 624,194–5,670,145 kHz; idle/loaded
snapshots are not effective-frequency measurements. APERF/MPERF, per-worker
migration and thermal-throttling counters were unavailable. Sampled Tctl was
58.5–69.25°C; CCD readings spanned 33.75–70.875°C. Temperature samples
are contextual indicators, not proof of throttling or its absence. The retained
external snapshots cannot exclude transient interference or assign causality.

The short eight-worker RGB16 encode cell has two retained B-arm tails: 50.474 ms
at session 07 / pair 07 / first position and 54.030 ms at session 17 / pair 14 / first position,
among otherwise roughly 29–32 ms calls. B-arm CV reaches 14.96% and 17.50%;
their B/A mean changes are +3.64% and +4.09%, with widths 25.29 and 29.01 pp.
The AB/BA group changes in session 17 are −0.23% and +8.43%. These observations
identify tail/order uncertainty, not an established environmental cause or bias.
They remain included; a slow observation alone did not invalidate a session.

Within-pair correlation is mostly weak or negative; the short-cell tail sessions
have +0.722 and +0.317 correlation. Thus pairing does not guarantee a gain.
Per-arm lag-one correlations range approximately −0.30 to +0.38 across the
eighteen sessions, with no independence inference from their size. Boca eight-worker
means also decline across sweeps (A: 604.18 → 603.12 → 593.11 ms; B: 601.95 →
594.77 → 589.03 ms), so stationarity cannot simply be assumed. No three sessions
are pooled into sixty iid pairs. No interval excludes zero here; three sessions
cannot estimate a 1% false-positive rate or establish calibrated 99% coverage.

## One recommended next action

Commission a **separately reviewed, bounded pair-aware methodology investigation**.
The unchanged estimator did not demonstrate the required precision across this
matrix, and projecting eight times the samples still leaves every eight-worker
cell above +1% even after explicitly hypothetical zero centring. Any investigation
must treat tails, position effects and serial dependence prospectively and retain
the unchanged comparator as the reference. Mostly weak/negative covariance means
a precision gain is not presumed; a narrower interval alone is insufficient.

This recommendation is unexecuted. It neither launches/adopts the separate
48,000-call Fieller proposal nor reanalyses old candidates. The paired-column
patch is not retested or reclassified; its non-regression remains unestablished.
No margin, critical-case requirement, default estimator or historical gate changes.
