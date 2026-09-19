# Bounded identical-binary precision feasibility

`precision-feasibility-v1` asks whether the unchanged comparator can establish
an intended +1% non-regression margin at practical sample cost on six real
workload cells. It supplies experiment-design evidence, not codec qualification,
a speedup, estimator adoption or calibrated confidence/power. Poor precision is
a completed finding; missing mandatory observations are an incomplete study.
The workspace selects `incremental-performance-policy/v1` as planning context;
no default, candidate gate, historical result or threshold changes here.

## Frozen workload and treatment

| Cell | Complete prepared product | Operation/style | Workers |
|---|---|---|---|
| 0, 1 | `106_10400100413CDF00-RGB8`, Boca Raton | encode, bypass | 1, 8 |
| 2, 3 | `94_104001000B823500-RGB16`, Mansfield | encode, bypass | 1, 8 |
| 4, 5 | `94_104001000B823500-RGB8`, Mansfield | decode, style zero | 1, 8 |

Prepared manifest SHA-256:
`6c37b54bf75af0c17c1b67c5ad7bd2d56b5d34d45de9737ddb50d0fc1fe10e7b`.
The unchanged `common/rareplanes-expanded` reviewed rights record authorises
local derivative benchmarking in the persistent RarePlanes store. Original
notice, attribution, source lineage and local change notice accompany evidence.
Only factual measurements/identities enter Git; no pixels, streams or external
binary/source material. No acquisition or SpaceNet/Khartoum exposure occurs.

| Product | Raw SHA-256 | Existing reference stream SHA-256 |
|---|---|---|
| Boca RGB8 | `aaf064a2d6b302d839e7f3c13b99e1344ba749fed53be6daf64f8a6c4c67bfe7` | `ebac8279fd3c42cc757d98c9d17cfc0c18019ae839910084e0fd2a758fb801fb` |
| Mansfield RGB16 | `11b98f162a80c8d45a50f2ca3f1bc4e8b6d763aa4cc4af6401f340244b074573` | `9e444c320a97937863a45d4fad62b691e9df6c769a51c484bfb2c0f4afcd74d0` |
| Mansfield RGB8 | `4b3b0f7baf1b13d65fff072ad1f52c7861388463a9b349918b3324d494660fd1` | `e4f42a0238389c5e39037c229dc6b6660edc91910cdf3d26801dbf06cbd1d289` |

Streams are reused from `openjpeg-refresh-main-01`: Emuella-origin for encode
byte equality and one immutable OpenJPEG-origin stream for decode. The retained
preparation receipts record exact reconstruction. Both arms use **one executable
path and hash**, codec `975a5e734773578f61abf76d5fddfbd837f3bd7d`, the same
linked libraries, options, source, raw input and stream. A/B never enters the
worker request or selects implementation. The machine-readable prelaunch binding
also identifies the clean benchmark source, compiler, Cargo artefacts and flags.

Existing `perf`/ThinLTO/one-codegen-unit build, SIMD off, parallel on, packed-default
selector unset, original MQ and W batches and original single-column forward
traversal remain. The only intervening codec change from `b02b6ab` is the restored
front-end record/feature-only diagnostics in PR113; diagnostics are disabled.
D2 lossless, RGB RCT, interleaved bytes, direct/global public facade, 768/64 MiB
working/output limits, 8 GiB address limit and 120-second process timeout remain.
Input loading/hash checking, stream inspection and complete exact reconstruction
are outside the operation clock. Process wall/CPU/RSS include those phases and
stay separately labelled. Encode verification also decodes outside timing; a
"call" here means one worker invocation, as in the inherited protocol.

## Fixed acquisition and caps

Three separately launched sessions/cell, twenty adjacent alternating pairs/session:
18 sessions, 360 pairs, 720 measured worker calls. Each fresh process measures
one operation, zero warmups. All processes are sequential; codec budgets are
one/eight workers. No in-process repetition supplies trials. Three sweeps visit
cells in orders `0 1 2 3 4 5`, `2 3 4 5 0 1`, `4 5 0 1 2 3`. Starting arm is A
when `(cell + zero-based sweep)` is even, B otherwise. Each session has ten AB
and ten BA pairs. This counterbalances order without proving independence.

Six fixed preflight calls, one/cell, precede the cohort and are excluded from
analysis even though the unchanged worker records its clock. No replacement
preflights are planned: 726 expected calls against the authorised ceiling 732.
The two-hour observation window starts before preflight. Reserve 150 seconds
before starting another call for its timeout and receipt checks. The 2 GiB
new-evidence cap reserves 1 MiB before each call. Builds and authored canonical
checks are separate and finish before observation. Immutable payloads are reused,
not copied. Started-call receipts are written before validation/invocation;
failed attempts consume budget and remain visible. Exclusive launch/session
receipts prohibit overwriting or restarting the cohort. Missing sessions/calls,
cap stops and failures cannot become a successful subset. No timing-driven stop,
extra rounds, outlier removal, substitution or retuning is permitted.

## One environment condition

Use historical CPU 0 for one worker, CPUs 0–7 for eight. On this host these are
eight distinct physical cores, SMT siblings 16–23, AMD Ryzen 9 9950X3D. Retain
`amd-pstate-epp`, `powersave`, `balance_performance` and enabled boost; change no
global setting. This is one condition, not a governor causal experiment or a
historical speed comparison. Launch only after local builds/codec benchmarks
finish and inspection finds an otherwise idle authorised window. Do not terminate
unrelated processes. Ordinary desktop/services and residual load are recorded.

External snapshots at session start/end and between pairs record CPU topology,
affinity, online/policy/frequency, `/proc` load/CPU/memory/pressure/scheduler counters,
available thermal/throttle counters, and boundary process listings. They add no
sampling inside the operation. Effective APERF/MPERF frequency and worker-specific
migration counters are unavailable; sampled frequency is not effective frequency.
Temperature has no invented causal threshold. Missing optional telemetry stays
unavailable and is not imputed.

Prospective invalidity: changed identity/profile/exactness, missing/failed calls,
changed affinity/topology/online or frequency policy, increased available throttle
counters, or an observed concurrent compiler/build/codec process at session
boundaries. Such sessions remain in the report as incomplete/uninterpretable.
Record visible load/drift and other protocol deviations without cleaning vectors;
a slow observation, elevated temperature or noisy interval alone is not invalid.
Boundary snapshots cannot rule out all transient contamination.

## Analysis and prospective recommendation

Use the [actual unchanged comparator](comparisons.md) via the existing
`real-scene-classic.py` owner-module wrapper. Keep ratio of arithmetic means,
conservative 99.5% marginal critical-value/df buckets, resulting 99% per-case
ratio interval and legacy 5% verdict. Report every session's means, relative
change, full interval/width/upper bound, zero inclusion and upper-bound-below-+1%
condition. Swapped A/B is a labelled sensitivity of the same data. +2%/+5% are
separate planning sensitivities, never replacement limits. No session pooling.

Each cell is **demonstrated in this limited study** only when all three valid
sessions contain zero and establish +1% in both directions; **not consistently
demonstrated** for complete valid observations failing that condition; and
**incomplete/uninterpretable** for absent observations/validity. These are advisory
repeatability descriptions, not estimator rejection/adoption. Three sessions
cannot estimate a 1% false-positive rate or validate 99% coverage/power.

Retain per-arm variability, covariance/correlation, AB/BA/position effects and
ordered/serial diagnostics. Covariance is diagnostic, not a paired estimator.
Null exclusion in one session is not proof of systematic bias; absence of a
visible serial pattern is not proof of independence. Report width and centring.

Project 20/40/80/160 pairs from each session's observed SD, assuming stable
variance and independent future pairs; use actual critical buckets 3.287, 3.030,
2.915, 2.860. Show both common-zero-effect and observed-displacement centres.
These are planning widths, not new observations, power or empirical coverage.
More samples do not cure persistent displacement. Retain all sessions' sensitivity,
call/wall/storage costs and the difficulty of clearing every critical case;
per-case intervals give no family-wide or probability-of-all-passing guarantee.
Recommend exactly one future action without running it. The 48,000-call Fieller
proposal and paired-column candidate are unchanged and outside this study.

## Opt-in reproduction

From clean committed source, first build the existing production worker and
estimator in registered disposable build storage; finish authored checks before
launch. Supply only approved existing prepared/stream roots:

```sh
python3 scripts/openjpeg-refresh.py build --codec-source CODEC --output BUILD
python3 scripts/openjpeg-refresh.py estimator --output ESTIMATOR
python3 scripts/precision-feasibility.py freeze --build BUILD/build.json \
  --codec-source CODEC --prepared STORE/prepared-final \
  --streams STORE/openjpeg-refresh-main-01 --output STORE/precision-feasibility-v1
python3 scripts/precision-feasibility.py study --output STORE/precision-feasibility-v1
python3 scripts/precision-feasibility.py analyse --output STORE/precision-feasibility-v1 \
  --estimator ESTIMATOR/target/release/classic-treatment-estimator \
  --report STORE/precision-feasibility-v1/report.json
```

`study` owns one exclusive launch and invokes each session in a separate controller
process. Its one watcher retains completion; never restart it or replace a failed
session. Build receipts/logs and estimator provenance are preserved in the
approved evidence root before registered scratch cleanup. Merged-tool integration
reconstructs results offline from those retained records; it does not rerun A/A.
