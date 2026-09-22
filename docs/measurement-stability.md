# Controlled identical-binary measurement stability

> **Execution-integrity follow-up:** retained CPU accounting shows effectively
> single-core execution for the nominal eight-worker calls. The original interval
> arithmetic and restoration record stand, but parallel execution and transfer to
> panel confirmation are not qualified. See the [follow-up audit](measurement-execution-integrity.md).
> The subsequent [balanced-condition A/A study](balanced-measurement-stability-results.md)
> is a separate completed record. Panel confirmation remains unlaunched.

`measurement-stability-qualification/v1` is an opt-in prospective condition check
using the unchanged production comparator and the inherited
[precision protocol](precision-feasibility.md). Its fresh-process boundary takes
precedence over historical calibration warmups. It does not test or promote the
pending forward-5/3 candidate. [Current delivery state](measurement-stability-results.md).
The workspace owns the operational authority, full confirmation endpoint register
and next decision; benchmark owns this runner, environment admission and analysis.

## Admission before observation

The first authorised cohort has [completed](measurement-stability-results.md).
Admission for any future invocation still requires its own valid reservation;
affinity, low observed load and a runner lock do not reserve CPUs. `inspect` writes an unlaunched report with
all twelve sessions and four cell verdicts incomplete; it reads only allowlisted
current cgroup/affinity information and launches no worker:

```sh
python3 scripts/measurement-stability.py inspect --output NEW-LOCAL-RECEIPT.json
```

Historical admission uses an **existing delegated cgroup-v2 isolated cpuset
partition**. The separately selected balanced A/A mode below requires an exclusive
partition `root` with ordinary internal load balancing. Both are empty
before/between worker calls, with no
child cgroups, exclusive effective CPUs covering the eight selected physical
cores and all their SMT siblings. It never creates or alters that partition.
The optional [temporary reservation helper](measurement-reservation.md) can
provision this arrangement after explicit administrative authorisation and local
authentication; the measurement runner itself remains read-only for host settings.
A reviewed resource-owner authority receipt must identify the active window,
issuer and authority, reservation and controller CPUs, and residual shared-cache,
package, memory and interrupt interference. Authority is independently checked by
the workspace owner; a JSON assertion is not an authority grant. A different
reservation mechanism needs separately reviewed admission support before timing.

Receipt fields are allowlisted, with no extra keys:

```json
{
  "schema": "measurement-stability-qualification/v1",
  "authority": "exact reviewed delegation record locator",
  "issuer": "resource owner",
  "approved": true,
  "valid_from_epoch": 0,
  "valid_until_epoch": 0,
  "cgroup": "/sys/fs/cgroup/EXISTING-DELEGATED-PARTITION",
  "worker_cpus": [0, 1, 2, 3, 4, 5, 6, 7],
  "reserved_cpus": [0, 1, 2, 3, 4, 5, 6, 7, 16, 17, 18, 19, 20, 21, 22, 23],
  "controller_cpus": [8, 9, 10, 11, 12, 13, 14, 15, 24, 25, 26, 27, 28, 29, 30, 31],
  "residual_interference": "resource-owner account of residual package/cache/memory/IRQ activity"
}
```

The example deliberately has no valid window or real authority. CPU numbers are
historical preferences, checked against actual topology before admission. The
controller's selected CPUs must be within its existing delegated affinity. Worker
children alone enter the reserved partition; taskset then selects CPU 0 or 0–7
from the frozen worker list. Their SMT siblings stay reserved and unused. Agents,
builds, telemetry and unrelated heavy processes stay outside this reservation.
The resource owner must retain control of admission throughout the window;
boundary checks cannot detect every transient unauthorised membership change.

The manifest freezes driver/governor/EPP/boost/min/max, online/core/sibling/cache
and NUMA topology, cpuset memory nodes, direct and ancestor CPU/memory limits,
compiler, linked libraries, build source and executable hashes, the exact estimator
executable/wrapper/provenance hashes, exact workload
identities, cadence, method and decision permalink. Host policy is read-only.
No cache dropping, selective warmup, cooldown, SMT/IRQ/scheduler change or host
administration occurs. Sampled frequency is not effective-frequency evidence.
Effective frequency and task migrations are explicitly unavailable; GNU time CPU,
RSS and context-switch counters, task cgroup CPU accounting/pressure and host
pressure/available throttle counters remain outside the operation timer.

Only the task controller's affinity changes. Original/intended values are written
before placement. Normal exit, failures and SIGINT/SIGTERM restore its original
affinity and verify an empty worker cgroup. If another actor changed affinity,
restoration records a blocker and does not overwrite that actor's change.
Child timeout/interruption kills and waits for that task's process group only.
SIGKILL or host failure cannot run a handler: missing restoration evidence is an
operational blocker. Reservation release remains with its external owner.

## Frozen cohort and stopping

One clean production executable at codec
`975a5e734773578f61abf76d5fddfbd837f3bd7d` serves both labels with the same path,
hash, libraries, options and input/stream hashes. Labels never enter requests.
The exact codec revision retains original MQ, packed-default, original W batches
and original forward traversal. The inherited build remains perf, ThinLTO, one
codegen unit, SIMD off, parallel on; lossless D2/RCT direct/global worker settings
and 768/64 MiB working/output, 8 GiB address-space and 120-second limits remain.
Runtime selector and dynamic-library override environment variables must be unset.

| Cell | Inherited complete product | Operation | Workers | Stream |
|---|---|---|---:|---|
| 0 | Boca `106_10400100413CDF00-RGB8` | bypass encode | 8 | existing Emuella reference |
| 1 | Mansfield `94_104001000B823500-RGB16` | bypass encode | 8 | existing Emuella reference |
| 2 | Mansfield `94_104001000B823500-RGB8` | style-zero decode | 8 | common OpenJPEG origin |
| 3 | same Mansfield RGB8 | style-zero decode | 1 | same immutable stream |

The runner enforces the exact prepared-manifest, raw and stream SHA-256 identities
in [the inherited protocol](precision-feasibility.md). Loading, hashing, source and
stream inspection and exact verification remain outside the operation clock.
Process wall/CPU/RSS/context switches remain separately labelled.

Three separately launched sessions per cell each contain forty adjacent
alternating AB/BA pairs: twelve sessions, 480 pairs, 960 timed worker calls. Four
separate preflight calls, one per cell, are setup only: **964 total attempts**,
including failures, with no replacement. There is one operation per fresh process,
zero warmups and no concurrent codec benchmarks or within-process repeats.

Three sweep orders are `0 1 2 3`, `2 3 0 1`, `3 2 1 0`. Session starting arm is
A when `(cell + zero-based sweep)` is even, otherwise B. Every session therefore
contains twenty AB and twenty BA pairs; every cell visits three distinct ordinal
positions. Cadence is sequential launches with mandatory external checks before
and after every call, with no inserted sleep or result-dependent delay. Separate
controller launches and counterbalancing do not establish independence.

The fixed observation window is two hours including preflight; before a call,
reserve 150 seconds for timeout/receipts and 1 MiB evidence headroom. New evidence
is capped at 2 GiB, registered disposable builds at 30 GiB. The workspace owns
scratch registration; `--build-root` must be that registered campaign root.
Builds, authored checks and review finish before observation. Every attempted call
gets an exclusive started receipt before validation. Failures and partial sessions
remain visible. An exclusive launch receipt prevents retries, replacement sessions
or another condition. All retained started attempts count against the cap.

Identity/profile/exactness, reservation, topology, policy, affinity, available
throttle counter increase, missing/failed calls and cap violations stop the cohort.
These criteria are frozen independently of timings. Slow calls, wide intervals,
displacement and elevated temperature do not invalidate observations. No tails
are removed and no second environment attempt is authorised after timing starts.

## Analysis and unlaunched confirmation planning

`analyse` uses the actual unchanged comparator on each complete valid forty-pair
session in both label directions. Reversal reuses the same data, not another
experiment or a way to select a favourable orientation. The inherited ratio of
arithmetic means, conservative marginal critical/df construction, 99% per-case
interval and legacy 5% timing verdict remain intact. All samples, ordered pairs,
means, bounds/width/centring, arm variability, covariance, AB/BA position and
serial/order diagnostics remain session-local. Sessions are never pooled as iid.

The inherited limited-study support requires all three valid sessions in a cell
to contain zero and have an upper bound **strictly below +1% in both directions**.
Otherwise a complete valid cell is not consistently demonstrated; missing/invalid
mandatory observations are incomplete/uninterpretable. +2%/+5% remain labelled
planning sensitivities. Invalid operational completion/restoration is separately
reported, without suppressing otherwise complete session observations. Mandatory
whole-study failures, including any missing or invalid mandatory session, make
authoritative cell dispositions incomplete; the separately
labelled session-only disposition retains the diagnostic interpretation.

Every session supplies planning-only 20/40/80/160-pair projections with actual
critical values 3.287/3.030/2.915/2.860. Observed SDs are held fixed under explicit
independence/stationarity assumptions. Common zero-effect centres and observed
displacement are separate: more samples cannot remove persistent displacement.
Projections never add observations, promise power/coverage or justify extra rounds.
Three sessions cannot calibrate 99% coverage, a 1% false-positive rate, power or
future stability. Per-case intervals give no probability-of-all-endpoints-passing
guarantee; cumulative call/wall/storage costs belong in the workspace design.

These four cells supply no direct A/A evidence for one-worker encoding, Tok,
MSI16 or SpaceNet. Any representative-cell transfer is planning only, with explicit
rationale and independent review. The candidate remains qualification-pending.
Its declared-direction non-regression is different from this A/A both-direction
sensitivity. No candidate confirmation is launched by this tooling.

## Runnable continuation after authority exists

First check the reviewed allocation, then resolve clean historical worker source
and exact compiler; build only if the exact retained executable is unavailable.
Use the existing `openjpeg-refresh.py build` command in registered scratch.
`measurement-stability.py estimator --output ESTIMATOR` reuses the existing
comparator wrapper builder with forty-pair admission; the comparator source and
classification are unchanged and historical wrappers still default to twenty. These actions are not authorised by a successful JSON parse alone.

```sh
python3 scripts/measurement-stability.py check-reservation --authority RECEIPT.json
python3 scripts/measurement-stability.py freeze \
  --build BUILD/build.json --codec-source CLEAN-REFERENCE-CODEC \
  --estimator ESTIMATOR/target/release/classic-treatment-estimator \
  --worker-benchmark-source CLEAN-WORKER-BENCHMARK --build-root REGISTERED-SCRATCH \
  --prepared APPROVED-STORE/prepared-final --streams APPROVED-STORE/openjpeg-refresh-main-01 \
  --authority RECEIPT.json --decisions EXACT-REVIEWED-WORKSPACE-PERMALINK \
  --output APPROVED-STORE/measurement-stability-qualification-v1
python3 scripts/measurement-stability.py study \
  --output APPROVED-STORE/measurement-stability-qualification-v1
python3 scripts/measurement-stability.py analyse \
  --output APPROVED-STORE/measurement-stability-qualification-v1 \
  --estimator ESTIMATOR/target/release/classic-treatment-estimator \
  --report APPROVED-STORE/measurement-stability-qualification-v1/report.json
```

Freeze from clean committed runner source; analysis requires the same frozen estimator identity; `--worker-benchmark-source` names the
clean source bound by the production build, which may differ from runner source.
One operational owner/watcher runs the study. Retain build/authority/restoration,
all observation and analysis receipts within the approved persistent store before
registered scratch cleanup. Offline merged integration reconstructs the report;
it never repeats real observations merely because tooling/documentation landed.


## Balanced A/A after execution-integrity support

The [four-call diagnostic](parallel-execution-diagnostic-results.md) supports the
limited parallel-execution criteria under the exclusive balanced condition. A new
production A/A cohort can select that condition explicitly; diagnostic timings
are never substituted for production observations and historical A/A stays separate.

Use helper `--condition balanced-aa`, runtime
`/run/emuella-balanced-aa-measurement-reservation`, receipt schema
`measurement-balanced-aa-qualification/v1`, `condition=balanced-aa`,
`partition_mode=root`. Its three-hour lease includes setup; the observation window
remains two hours. The old isolated and 30-minute balanced diagnostic runtimes,
leases and completed receipts are unchanged. No runtime is silently recycled.

The runner additionally requires exact worker/reserved/controller masks
0–7 / 0–7,16–23 / 8–15,24–31, unlimited task and available ancestor CPU quotas,
and exclusion of ordinary top-level cgroups. The helper enforces and checks
ordinary descendant exclusion too. Missing root quota interface remains unavailable.
All original policy/topology/affinity/available-throttle invalidity rules still
apply; this adds no timing-based data exclusion. No pool binding, worker changes,
codec instrumentation, governor change or new estimator accompanies admission.

`prepare-balanced` verifies the original four prepared/raw/stream identities and
one production build, freezes the unchanged comparator, schedule, counts/caps,
launch cadence, clean runner/helper and policy identities, and writes a preparation
receipt in registered scratch. It needs no live reservation and invokes no codec.
The output cohort directory must not exist. Both labels use the same executable;
the standard production verifier rejects diagnostic feature builds.

```sh
python3 scripts/measurement-stability.py prepare-balanced \
  --build BUILD/build.json --codec-source CLEAN_REFERENCE \
  --worker-benchmark-source CLEAN_ORIGINAL_WORKER_SOURCE \
  --estimator ESTIMATOR/target/release/classic-treatment-estimator \
  --prepared APPROVED_STORE/prepared-final \
  --streams APPROVED_STORE/openjpeg-refresh-main-01 \
  --build-root REGISTERED_SCRATCH --preparation REGISTERED_SCRATCH/preparation.json \
  --output APPROVED_STORE/balanced-measurement-stability-v1 \
  --decisions EXACT_REVIEWED_WORKSPACE_PERMALINK
```

After reviewed helper setup, admit one unprivileged controller command:

```sh
python3 scripts/measurement_reservation.py --condition balanced-aa run -- \
  /usr/bin/python3 ABSOLUTE_MEASUREMENT_STABILITY_RUNNER launch-balanced \
  --preparation FROZEN_PREPARATION --preparation-sha256 REVIEWED_SHA256 \
  --authority LIVE_BALANCED_AA_RECEIPT
```

`launch-balanced` checks the preparation hash and every build/source/input identity,
requires its exact decision URL in the live authority, and freezes the live
environment before the original study starts. It retains the preparation beside
the binding. The existing study launches the same four preflights and twelve
sessions, counting failures without replacement. Before/after every call, admission
and frozen identity/policy checks remain active. A changed preparation, helper or
policy fails closed; partial observations remain retained. Analyse with the same
unchanged command and frozen comparator described above. Always retain the separate
post-run helper verification; the runner's affinity receipt alone is insufficient.

A successful preparation, tooling merge or diagnostic result is not a precision
verdict. Fresh study results must assess all sessions in both orientations and
retain full-matrix planning gaps before reconsidering the suspended confirmation.

The completed balanced cohort is recorded in
[balanced production A/A results](balanced-measurement-stability-results.md).
It preserves the historical isolated observations separately and does not
authorise or launch panel confirmation.
