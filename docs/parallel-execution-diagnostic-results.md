# Balanced exclusive-CPU execution diagnostic results

All four authorised calls completed on 22 September 2026 and satisfied the
[prospectively frozen execution criteria](parallel-execution-diagnostic.md).
Each eight-worker call supplied operation-scoped CPU evidence above one CPU,
all eight productive pool threads, and observed pool placement across CPUs 0–7.
The one-worker control stayed on CPU 0. This supports the intended parallel
execution arrangement for a subsequent bounded precision study; **it does not
qualify A/A precision or lift the panel-confirmation hold**.

## Complete observations

These are individual instrumented diagnostic calls, not production performance
estimates. No headline samples, interval comparisons or speedup claims are made.
The CPU lower bound subtracts one whole outside-operation snapshot span for every
tracked thread, including the caller. CPU includes codec and scheduler/bookkeeping
work; observed placement is sampled and does not prove eight-way simultaneity.

| Fixed call | Workers | Diagnostic facade wall (ms) | Conservative operation CPU / wall | Productive pool threads | Observed productive CPUs | Verdict |
|---|---:|---:|---:|---:|---|---|
| Boca RGB8 bypass encode | 8 | 756.106 | 3.043830 | 8 | 0–7 | supported |
| Mansfield RGB16 bypass encode | 8 | 31.869 | 4.694260 | 8 | 0–7 | supported |
| Mansfield RGB8 style-zero decode | 8 | 300.753 | 6.183716 | 8 | 0–7 | supported |
| Same Mansfield decode control | 1 | 1,796.823 | 0.998220 | 0; caller performs serial work | 0 | supported |

The actual Rayon pool sizes match requests. Both encodes additionally report
codec-admitted and participating workers equal to eight. Decode uses the unchanged
ordinary full-image route: its source predicates select parallel code-block work
at eight workers, followed by serial inverse 5/3 reconstruction. Dynamic CPU
accounting corroborates execution; the response's requested worker count alone
would not establish it. All four workers exited successfully and exact verification
passed. The retained `samples_ns` arrays are empty.

All four starts were used, without warmups, preflights, replacements or concurrent
codec processes. The observation window lasted **6.155722990 seconds** out of 900;
completion recorded **1,266,101 bytes** before completion/report/restoration files
were appended. The observation manifest covers **52 files / 1,489,412 bytes**,
including those receipts, below 64 MiB. Per-call placement traces contain
298, 14, 115 and 749 snapshots, respectively. All started observations are retained.

## Condition, restrictions and restoration

The authorised systemd/cgroup-v2 reservation used an exclusive partition `root`,
with ordinary internal scheduler load balancing. CPUs 0–7 and their SMT siblings
16–23 were reserved; workers used 0–7, or 0 for the control. Ordinary cgroups,
controller and sampler were restricted to 8–15,24–31. The helper admitted one
controller command and checked allocation/exclusion rather than relying on affinity
alone. Caller and pool-thread masks were checked throughout each operation.

Task/service CPU quotas were unlimited at retained boundaries; the hierarchy-root
`cpu.max` interface was unavailable. Task `nr_throttled` deltas were zero in all
four calls. Optional core/package thermal-throttle counters and effective-frequency
observations were unavailable, so this is not evidence of their absence. Frequency
policy remained `amd-pstate-epp`, `powersave`, EPP `balance_performance`, boost on;
global SMT remained on. No frequency/boost policy, IRQ routing or security change
was made. Policy labels and ordinary snapshots do not establish effective frequency.

The package and NUMA memory domain remain shared; kernel/IRQ, package and memory
interference remain possible. This reserved condition is not a general claim about
shared-host deployment behaviour. The historical isolated-partition observations
remain separately identified: this is no matched causal contrast establishing why
those calls were effectively serial, or how much a policy change altered variance.

Runner restoration reports original affinity restored and worker cgroup empty.
The external helper reports cleanup executed and no issues, and requests final
verification after unit removal. That separate post-run helper `verify` succeeded:
affected original settings
match and the owned unit cgroup is gone. Historical reservation receipts are intact.

## Identities and reproduction

- Runner/helper: `16a6e99c3353908b276d0cdd44712ee421f06eeb`, delivered in [PR #25](https://github.com/emuella/emuella-benchmark/pull/25).
- Diagnostic worker source: `257c591a10922d08aa4d93a8bb6c400e27cb6a25`; compiled files match the runner tree.
- Reference codec: `975a5e734773578f61abf76d5fddfbd837f3bd7d`.
- Binary SHA-256: `ac1892a21f070827f94c713c6e2e33dcc41ab7c70f161527160f51b3163d0b6a`.
- Frozen binding SHA-256: `36a76be5a1a4d16a7bd97011543f1fddfd1b8a3e8a2d0c5a1f879ff0fa2fee23`.
- Observation manifest SHA-256: `40775a496b922e47f9e766d7d76fa152f8b7818a346088ca8644b3469f78c173`.
- [Reconstructed report](parallel-execution-diagnostic-results.json) SHA-256: `0fd7edd02db0f310880be3b2993c4b5604c8729d357afe454ce5da83ac6f242a`.

The binding retains the exact original four input/stream/rights identities,
prepared-input contract, tuned perf/ThinLTO/one-codegen-unit toolchain, SIMD-off,
original MQ/packed-default/W/traversal selectors and operation/resource limits.
Raw task-only traces, boundary environments, worker results, all start receipts,
launch/completion and independent restoration receipts remain in the authorised
RarePlanes store under `parallel-execution-diagnostic-v1`. No protected imagery,
private paths or external binaries are included in the public report.

Reconstruct offline from that retained root, without invoking a codec or requiring
a live reservation. Use a new report filename and compare parsed JSON values with
this report; thread-key object ordering may differ between processes:

```sh
python3 scripts/parallel-execution-diagnostic.py analyse \
  --output "$RETAINED_ROOT" --report "$RETAINED_ROOT/reconstructed.json"
```

The original diagnostic build and source receipt remain attributable through Git
and the retained build manifest; temporary build paths are historical after cleanup.
The standalone report requires the separate helper restoration evidence described
above; its generic reminder is not an unresolved restoration failure.

## Next decision and limits

The one next recommendation is a prospectively reviewed, bounded identical-production-
binary A/A study under this balanced reservation, with its own frozen production
build/condition identity and unchanged comparator, margins and full-matrix planning
obligations. This diagnostic instrumentation cannot supply that precision evidence.
No additional diagnostic call, A/A cohort or panel confirmation was launched.

The frozen panel candidate `d60859a8595554be52c8748a8e8c85b69614fea5` stays
qualification-pending. All 28 mandatory contrasts and their original gates remain;
this four-cell diagnostic covers no unmeasured endpoint and does not authorise
wider margins, case deletion, estimator changes or a partial confirmation matrix.
