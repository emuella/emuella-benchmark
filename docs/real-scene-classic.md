# Classic facade and application configuration

`scripts/real-scene-classic.py` orchestrates the bounded real-scene consumer
experiment. Codec-owned `lossless_bypass_batch` performs public facade calls,
including decode packing. Benchmark owns fresh-process execution, conservative
resource admission, treatment identities and statistics. No protected image
payload belongs in this source tree.

Build codec test-support examples `lossless_bypass_batch`,
`lossless_bypass_allocation` and `classic_ht_support` using `--profile perf
--features parallel`, without SIMD. Bind clean committed source revisions,
compiler identity and executable digests. Set an approved external Cargo target.
Preparation verifies the batch and allocation executable digests against their
bound build provenance and resolves its original commit/tree through Git objects.
A later checkout HEAD cannot relabel an earlier binary; final merged-owner
confirmations remain separately identified. The consumer explicitly supplies `LosslessEncodeLimits` of 768 MiB working
and 64 MiB output capacity for every treatment; library defaults are unchanged.
Requirements are queried in the actual direct/global or nested-pool context.

The primary configuration calls decode directly from an ordinary application
thread, after configuring the process-global Rayon pool. Calling decode from
inside `ThreadPool::install` retains the existing nested-call guard and can
perform less parallel work. Both routes reconstruct the same native samples;
thread-budget equality alone does not establish equal execution. Encoding
queries and calls use the same execution context and explicit limits.

The script admits only the frozen prepared-manifest digest and nine full
products: development Mansfield PAN16/RGB16/MS16/RGB8, validation Boca Raton
with the same products, and Tok RGB8 regression. Run `prepare` into a new child
of the approved image store for each role, passing `--prepared`, `--output`,
`--binary`, `--codec-source`, `--build-provenance`, `--role` and exactly eight `--cpus`. Generated streams
retain the complete licence notice, attribution, modification note and lineage.
Run `measure` against the same directory and binary. It executes 20 fixed AB/BA rounds for each of three adjacent paired contrasts:
style0/bypass at one worker, style0/bypass at eight, and style0/one versus
bypass/eight. Each process loads and checks input before
one measured facade call, with zero warmups and a 120-second process timeout.
All failed observations remain in their own directories and invalidate coverage.
No retries, trimmed samples or multiplied historical speedups are admitted.

`estimator --output NEW_SCRATCH_DIRECTORY` builds the historical narrow numeric
wrapper around the exact benchmark-owned `src/compare.rs`. It uses the unchanged
99.5% marginal t intervals, conservative 99% per-comparison ratio interval and
5% gate. The wrapper requires exactly 20 finite positive independent means per
side. `analyse --output ROLE_DIRECTORY --estimator BINARY` retains separately
named style/thread treatment comparisons. These are operating-point experiments;
they do not forge identical settings or relax ordinary `compare()` comparability.
Every claimed contrast keeps its two arms adjacent and alternates order;
all contrasts use independent-mean inference. Thread-only effects are descriptive.

`diagnose` separately records encoder stage/work/participant counters, instrumented
encoder allocation, nested decode and whole-process CPU/RSS. Serial bypass's
Tier-1 interval includes subband preparation and output appends. Parallel bypass
uses the existing separate preparation/assembly collector. These boundaries must
remain visible when reading profiles. Decoder diagnostics separately retain before/after Linux task CPU ticks for named
Rayon workers around the ordinary facade call, before validation. Nonzero deltas
are a lower bound on workers with CPU activity, not exact Tier-1 participation.
Missing decoder stage timings remain null; pool width is not participation. Diagnostic
clocks and allocation accounting never supply headline operation timing.

`schedule` compares eight identical full-image requests per cohort using one
eight-thread process, two four-thread processes or eight one-thread processes.
Only development PAN16/RGB8 select a schedule; use `--schedule 1x8`, `2x4` or
`8x1` for fixed Boca PAN16/RGB8 and Tok RGB8 validation. Other products have no
schedule qualification. `analyse-schedules` retains the same numeric estimator
for three-arm schedule observations, with the application boundary named.
Twenty alternating cohorts retain application wall time,
including process lifecycle, input reads and full verification, separately from
the inner warm-input facade latency. There is no claim of a persistent-service
latency or warm decoded-content cache.

The aggregate CPU affinity contains eight distinct CPUs. Before dispatch, query
actual encoder requirements at each pool width and add three source-sized buffers,
the output cap and a 64 MiB runtime margin. Reject the whole schedule when the
sum plus a 128 MiB controller reserve exceeds 8 GiB. Per-process address-space
ceilings divide the remaining budget by concurrency and bound decoder allocations too; the facade provides no
decoder requirements query. Whole-process peak RSS includes verification and
startup; the sum of the largest concurrent-count process peaks is a conservative
aggregate upper bound, not a sampled simultaneous peak or allocation measurement.
Timeout cleanup kills the complete process group. Process CPU time covers the
whole process and is separate from operation wall time.

The `classic_ht_support` example reads one full unsigned16 source and selects a
fixed top-left 256-square window in memory. It records actual D2 bypass success,
D2 HT rejection and D1 bypass requirement rejection. It emits facts and hashes,
never pixels. These unmatched profiles establish no codec ranking, full-scene
HT coverage or independent decoding result.
