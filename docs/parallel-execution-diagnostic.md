# Four-call parallel execution diagnostic

`parallel-execution-diagnostic/v1` investigates the [retained execution warning](measurement-execution-integrity.md)
under one exclusive CPU reservation with ordinary internal load balancing. It is
opt-in, separate from headline timing, and does not run A/A or panel confirmation.
The existing [reservation helper](measurement-reservation.md) has an explicit
`--condition balanced` mode: new runtime state, partition `root`, same CPUs 0–7 and
reserved siblings 16–23, controller 8–15,24–31. Historical isolated defaults remain.

The workspace freezes resource authority and decision identity before launch.
Only four original cells are admitted, in order: Boca RGB8 bypass encode/8,
Mansfield RGB16 bypass encode/8, common OpenJPEG Mansfield RGB8 style-zero decode/8,
and that decode/1. Their exact requests come from original binding SHA-256
`5e27912737fbecf98259ead8f4dec233e58ae638d4d77fb88d5392df494b0661`.
The reference codec remains `975a5e734773578f61abf76d5fddfbd837f3bd7d`.
No candidate code, stream preparation, codec warmup or extra real preflight is used.

## Diagnostic boundary and evidence

Build with `openjpeg-refresh.py build --parallel-diagnostics`, using a clean
reference checkout and registered disposable storage. This preserves the tuned
perf profile and records source/compiler/library/binary identities. The opt-in
`classic-parallel-diagnostics` feature adds a joined Rayon metadata broadcast to
identify actual pool threads, operation socket handshakes, and Linux per-thread
CPU-clock reads. It leaves pool placement and production worker output unchanged.
The existing encode observer supplies effective/participating workers. Its clocks
and bookkeeping perturb this separate diagnostic call. Decode calls the ordinary
facade route; the diagnostic does not substitute its serial profiling API.

The begin acknowledgement precedes CPU snapshots and the operation. Final CPU
snapshots and the end handshake precede exact sample/stream verification. For
caller and pool threads, the worker reads `CPUCLOCK_SCHED` inside their own thread
group. Its CPU-snapshot span contains the whole operation. Subtract one full
outside-operation span per thread from aggregate CPU delta to obtain a conservative
operation CPU lower bound. This includes codec and scheduler/bookkeeping CPU, not
exclusive algorithm attribution. No new statistical estimator is involved.

An external controller on non-reserved CPUs samples only the admitted worker's
threads: allowed masks, last execution CPU, advisory schedstat and context switches.
It waits 2 ms between snapshots and retains actual timestamps. `/proc` schedstat
can lag running-task accounting; it does not supply the strict CPU bound. See
[Linux proc implementation](https://github.com/torvalds/linux/blob/master/fs/proc/base.c)
and [CPU clock implementation](https://github.com/torvalds/linux/blob/master/kernel/time/posix-cpu-timers.c).
Missing mandatory CPU clocks, changed thread coverage or affinity fail closed.
No kernel tracing, scheduler-class changes, frequency controls or extra telemetry
service is added. Optional counters remain unavailable when absent.

Eight-worker support requires actual pool 8, all eight pool threads with at least
100,000 ns bounded operation CPU, observed productive pool placement covering 0–7,
and aggregate operation CPU lower bound strictly above 1.5 CPUs. Encode also needs
effective/participating workers both 8. The single-worker control requires CPU 0,
positive bounded operation CPU and CPU/span no more than 1.1. These predeclared
execution criteria are not candidate performance thresholds. Placement sampling
does not prove eight-way simultaneity. Source-route inspection and observed CPU
execution are separate evidence. All four valid supported cells are needed before
considering a fresh bounded A/A study; this diagnostic never lifts confirmation.

## Finite runner

The existing process launcher retains timeout, address-space, exactness and
resource accounting. This entry point adds four-start/900-second/64 MiB limits,
120-second per-call timeout, 150-second admission reserve, 12 MiB/20,000-snapshot
per-call trace caps and 1 MiB per worker-output file. Builds are capped at 30 GiB.
Fixed sequential fresh processes, zero warmups, no replacements or added rounds.
Identity/reservation/policy/exactness failures, missing mandatory evidence and caps
stop later calls. Well-run unsupported concurrency remains visible; all four
fixed cells may finish without any outcome-driven extension. Temperature and slow
calls never justify deleting evidence. Throttling prevents support.

```sh
python3 scripts/parallel-execution-diagnostic.py freeze \
  --build BUILD/build.json --codec-source CLEAN_REFERENCE \
  --worker-benchmark-source CLEAN_BUILD_SOURCE --original-binding ORIGINAL_BINDING \
  --build-root REGISTERED_SCRATCH --binding REGISTERED_SCRATCH/binding.json \
  --decisions EXACT_REVIEWED_WORKSPACE_PERMALINK

python3 scripts/measurement_reservation.py --condition balanced run -- \
  /usr/bin/python3 ABSOLUTE_RUNNER run --binding FROZEN_BINDING \
  --binding-sha256 FROZEN_SHA256 --authority LIVE_AUTHORITY --output NEW_APPROVED_STORE_CHILD
```

Actual source, runtime paths and authentication instructions belong to the private
workspace handoff. Finish builds, tests and independent review before privileged
setup and observation. The helper releases the reservation after its one controller
command; always run its `verify` separately. Runner affinity restoration is not
proof of host restoration. Retain all started evidence even on failure.

Reconstruct with `parallel-execution-diagnostic.py analyse --output RETAINED_ROOT
--report RETAINED_ROOT/new-report.json`; this launches no codec or host operation.
The report distinguishes incomplete and unsupported calls and still requires the
separate helper restoration receipt. No runtime observation has been made merely
because the tooling is merged.
