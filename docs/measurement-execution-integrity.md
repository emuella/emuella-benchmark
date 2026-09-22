# Execution-integrity follow-up to the controlled A/A study

The nominal eight-worker condition did not demonstrate productive execution
across eight physical cores. Retained counters instead provide strong evidence
of effectively single-core execution at their recording granularity. **Suspend
its use to justify parallel panel confirmation.** The original samples, comparator
arithmetic, protocol-valid session verdicts and verified restoration remain intact.
This is a follow-up interpretation, not a retroactive change of condition or data.

## Evidence and scope

The [offline audit](../scripts/measurement_execution_audit.py) authenticates the
retained observation manifest, binding, report, twelve sessions, all 960 timed
call receipts/environments/start records and four preflight start records. It
reads metadata only and launches no worker. The [derived report](measurement-execution-integrity.json)
retains all 960 call rows, all twelve session summaries and counter availability.
Its source identity includes the script, manifest, binding, report and binary hashes.
The trusted original manifest SHA-256 is
`2125ea4c62a1f7a0a77f9bf3f1338f192d486956c7963fc171db4151209537b3`.

Across worker CPUs 0–7, **719 of 720** nominal eight-worker calls have every
recorded user+nice+system tick on one CPU; the remaining call has **188/189
(99.47%)** there. The dominant CPU varies across calls. Including the reserved
SMT siblings 16–23 gives **709/720** calls with every tick on one logical CPU;
the minimum dominant share is **96.43%**. Small sibling system activity is retained,
not silently described as zero. These are logical-CPU counters; topology maps
worker CPUs 0–7 to distinct physical cores with siblings 16–23.

The mean whole-process CPU/wall ratios across the 240 calls in each cell are
approximately **0.986** (Boca encode/8), **0.788** (Mansfield RGB16 encode/8),
**0.963** (Mansfield decode/8), and **0.976** (decode/1). A ratio near one is
consistent with one CPU's execution, although it is not an operation-only metric.
The same-study decode means are approximately 1,821–1,824 ms at eight workers
and 1,798–1,800 ms at one. Historical serial timings are diagnostic context only;
no matched causal comparison or pooled inference is made.

At every retained boundary, the task and service ancestor `cpu.max` values are
`max 100000`; the root value was unavailable. Available task `nr_throttled`
counters do not increase. These observations supply no positive evidence for
quota throttling, but unavailable values are not interpreted as unlimited or zero.
The checked original condition allowed workers on 0–7 (or 0 for the control),
reserved siblings, and kept the controller on the other L3 domain. It used
`cpuset.cpus.partition=isolated`. No host settings were changed by this audit.

## What the counters establish, and what they do not

Per-CPU deltas sum user, nice and system ticks. Guest time is already included in
user/nice and is not counted twice. Idle, iowait, IRQ, softirq and steal are not
part of that metric. Tick quantisation and residual kernel activity limit its
resolution. The environment snapshots span external identity/hash checks as well
as the worker. Process CPU/wall includes loading and exact verification, including
post-encode decoding. Neither boundary isolates the codec's parallel stage.

The combined evidence is strong enough to withdraw the parallel-execution
qualification. It does not reveal individual Rayon thread affinity, thread CPU
trajectories, transient scheduler behaviour or the exact cause. Original frequency
policy labels and ordinary snapshots do not establish effective frequency or a
thermal explanation. No observations are removed for their timing or temperature.

## Execution route and mechanism hypothesis

The measured benchmark revision `d9b35866f01f7fc3be70303a6f4456f297800349`
constructs the global Rayon pool with the requested `num_threads` in
`workers/src/bin/classic_compare.rs` and provides no per-thread CPU binding.
Its response's `workers` field echoes the request; it is not a utilisation counter.
The production codec remains `975a5e734773578f61abf76d5fddfbd837f3bd7d`;
no panel source was built into this treatment.

Read-only source inspection finds that codec encode admission bounds workers by
Rayon pool size, memory slots and blocks (`scalable_lossless.rs`), and its admitted
parallel block path uses `par_iter_mut` (`scalable_lossless/parallel.rs`). Decode
also has feature-gated Rayon paths. Those source routes and requested counts do
not prove dynamic admission or productive concurrency in these retained calls.
Existing encode execution diagnostics expose admitted/participating workers and
logical block overlap, but were not recorded here. Overlap of entered regions
cannot distinguish simultaneous execution from time-sharing on one CPU.

Linux documents that an exclusive partition `root` forms a scheduling domain,
whereas `isolated` disables scheduler load balancing and requires deliberate task
distribution when several CPUs are used. The unbound pool inside an isolated
partition is therefore a concrete mechanism hypothesis consistent with the
receipts, not a causally established explanation.
[Kernel cgroup-v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html).

## Reproduction and next decision

Run from this repository with the authorised retained metadata root; no payload,
codec build or live reservation is needed. Output must be a new file:

```sh
python3 scripts/measurement_execution_audit.py \
  --root "$RETAINED_METADATA_ROOT" \
  --manifest-sha256 2125ea4c62a1f7a0a77f9bf3f1338f192d486956c7963fc171db4151209537b3 \
  --output "$NEW_AUDIT_REPORT"
```

Missing/tampered metadata, changed coverage, invalid required counters and negative
deltas fail closed; optional missing quota/throttle evidence remains unavailable.
Synthetic tests cover parsing, counter boundaries, identities, coverage and output
protection. This command performs no timing experiment or estimator calculation.

The single next recommendation is a bounded environment/worker execution
investigation: prefer an exclusive partition `root` retaining normal internal
load balancing, with the same authorised CPU/sibling exclusion. Review admission,
cleanup and the frozen condition before using it; the current helper/runner admit
`isolated` only and cannot be silently toggled. Collect operation-scoped task CPU
and placement evidence in a few diagnostic calls before considering fresh A/A.
Explicit per-thread placement is an alternative requiring a separately reviewed
worker identity; it is not implemented here.

The workspace owns the bounded diagnostic contract and confirmation hold. A
corrected scheduling condition needs new bounded A/A evidence before renewed
confirmation planning. Keep all 28 mandatory contrasts and their original gates;
no estimator, margin, codec implementation or panel draft changes follow from
this finding. The candidate remains qualification-pending.
