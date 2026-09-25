# Parallel forward 5/3 dispatch treatment

The one authorised attempt is closed as **NOT QUALIFIED WITHIN BUDGET**.
Production retains the existing forward transform and defaults. The candidate
is preserved as a source-only archive in [codec PR #115](https://github.com/emuella/emuella-j2k/pull/115).
There is no further confirmation, rescue change or retest authorised by this
result. Historical finite-confirmation v1/v2 remain closed and unchanged.

The [factual evidence](evidence/classic-forward53-parallel-dispatch.json) records
all 28 endpoint statuses, exact source/build/comparator identities, retained
receipt locators and SHA-256 bindings, resource observations and restoration.
The one acquisition used runner `7c5e24c4e07221e2f401b8ee4374f28a969dd406`,
candidate `4f5bfb39f02e043c9a1f594a8159d3cf86d52c3f` and preparation SHA-256
`f84c3a97f0bbabf4f7e9530934d853f01ec9da082849fb275f5e76ccbf5e67e8`.

## Terminal observations

Each completed endpoint received exactly 40 AB/BA pairs. These are arithmetic
means of operation samples and unchanged 99% candidate/baseline relative-time
intervals; the primary also requires at least 10 ms absolute mean saving.

| Endpoint | Boca RGB8 encode workload | Baseline mean (ms) | Candidate mean (ms) | Relative interval | Required gate |
|---|---|---:|---:|---|---|
| 00, sole primary | Bypass, eight workers | 736.661 | 462.905 | −37.7405% to −36.5760% | Pass |
| 02 | Style zero, eight workers | 788.585 | 524.972 | −33.9847% to −32.8679% | Pass |
| 01 | Style zero, one worker | 2,434.578 | 2,457.712 | +0.76909% to +1.13169% | Unresolved |

The primary saved **273.75549005 ms** and passed both required predicates.
Endpoint 01 took **23.13435745 ms more** on the observed means. Its upper bound
of **+1.1316918582%** exceeded the mandatory +1% limit, while its lower bound
remained below +1%. The fixed-count interval therefore leaves the non-regression
gate unresolved; it does not demonstrate regression beyond the unacceptable
margin. Its legacy ±5% verdict was `equivalent`, which cannot satisfy or replace
the +1% engineering gate. Primary gains cannot waive that gate.

The runner stopped after **278 starts**: 240 ordinary calls, six preflights and
32 separate allocation calls. There were no failed worker calls, retries,
replacement observations or intermediate endpoint decisions. The remaining
**25 endpoints and 2,370 calls were unstarted**, including endpoint 11's 160-pair
session and all RGB16 timing endpoints. Acquisition consumed **745.527180032
seconds**, 67,604,495 evidence bytes and 3,218,419,656 registered build bytes.
The stopping reason was the unresolved endpoint predicate, not exhaustion of
the two-hour or storage caps.

All 32 initial allocation calls passed the query-equality and absolute resource
gates. Across Boca and Mansfield RGB8, styles zero/bypass and worker budgets
1/2/4/8, both arms' observed requested allocation peaks ranged from 197,314,500
to 366,357,664 bytes, with unchanged working queries and output capacities.
These facts cover only the initial matrix; 80 later allocation calls were
unstarted. Allocation request counts and whole-process CPU/wall/RSS are retained
as separate descriptive quantities in the factual extract. They do not identify
the cause of the observed timing difference. Selecting the original serial
helper is a source-routing property and supplies no serial speed guarantee.

Retained reconstruction reproduced all three decisions with no issues, missing
terminal receipts or orphaned receipts. Mandatory checks passed for reviewed
prerequisites and the **observed prefix only**. One successful reservation setup
hosted the one execution, under lease `df30047d-2a49-4eec-a25c-1f369ac8cd8c`.
Ordinary restoration and independent installed verification both passed with
no issues. The exact journal, authority, restoration and privileged verification
locators/digests remain in the factual evidence. No historical samples were
pooled; the incomplete matrix does not qualify the candidate for production.

## Frozen acquisition protocol

`classic-forward53-parallel-dispatch/v1` explicitly admits one new source
comparison through the existing finite runner. Historical finite-confirmation
v1/v2 contracts and results remain unchanged. This implementation supplies no
new workload authority, automatic retest or production promotion.

The source owner selects the original serial helper and scratch lifecycle unless
at least two effective panel slots are admitted. Its independent source review
and authored proofs establish routing and correctness; routing alone does not
establish a timing gain. The benchmark worker source and compilation semantics
are unchanged.

## Immutable source contract

Use `finite_confirmation_live.py derive-dispatch` with the externally pinned
historical v1 manifest, register and design, new authority locator, and an
externally pinned source-treatment JSON receipt. The derivation imports every
endpoint, role, threshold, request identity, dependency, call label and order.
It changes the schema and the two source revisions, then adds predecessor,
authority, reusable condition and retained source-review bindings.

The receipt schema is `classic-forward53-parallel-dispatch-source/v1`, with
exactly these fields in addition to `schema`:

| Field | Binding |
|---|---|
| `recorded_production_codec` | `975a5e734773578f61abf76d5fddfbd837f3bd7d` |
| `baseline_codec` | `a7576ad03486e097ac923b8e49cac39a1cbef5d2` |
| `donor_codec` | `d60859a8595554be52c8748a8e8c85b69614fea5` |
| `candidate_codec` | Independently reviewed new full commit identity |
| `baseline_tree`, `donor_tree`, `candidate_tree` | Corresponding full Git trees |
| `production_to_candidate_diff_sha256` | Live baseline to candidate full diff |
| `donor_to_candidate_diff_sha256` | Donor to candidate full diff, including documentation/archive changes |
| `recorded_to_baseline_diff_sha256` | Recorded production to live baseline full diff |
| `independent_review` | Absolute `path` and externally reviewed `sha256` of the review JSON |

Hash exact stdout bytes from this command for each pair:

```sh
git -C CANDIDATE diff --no-ext-diff --no-textconv --binary --full-index \
  --no-renames --no-color --diff-algorithm=myers --no-indent-heuristic \
  --unified=3 --src-prefix=a/ --dst-prefix=b/ BEFORE AFTER --
```

The review JSON uses schema
`classic-forward53-parallel-dispatch-source-review/v1`, `verdict: "PASS"`,
nonempty `reviewer` and `locator`, and `sources` containing all ten source/tree/diff
fields above. Independent judgement and authority remain external obligations;
JSON does not establish that the author was independent. Preparation checks the
clean source revisions/trees and recomputes all three diffs. The intervening
production-baseline drift must remain exactly the three known documentation and
archive paths. The manifest retains exact UTF-8 receipt and review bytes and
checks their hashes; reconstruction needs neither original source checkouts nor
review paths.

```sh
python3 scripts/finite_confirmation_live.py derive-dispatch \
  --v1 V1.json --sha256 V1_SHA --register REGISTER.json --design DESIGN.json \
  --authority NEW_REVIEWED_AUTHORITY --source-treatment SOURCE.json \
  --source-treatment-sha256 SOURCE_SHA --output DISPATCH.json
```

## Preparation, acquisition and reconstruction

Use the existing [finite preparation configuration](classic-forward53-finite-confirmation-v2.md#preparation-and-immutable-bindings),
adding `contract.source_treatment` and `contract.source_treatment_sha256`.
Set the derived manifest path/digest to the new contract. The preparation schema
is `classic-forward53-parallel-dispatch-preparation/v1`; the registered build
root and marker slug are `classic-forward53-parallel-dispatch`. Historical v2
preparations cannot admit this treatment, and new preparations cannot relabel
historical acquisition receipts.

Supply new independently reviewed `source_correctness`, `output_failure` and
`parallel_route` prerequisites. Each descriptor adds `source_treatment_sha256`
matching this receipt to its existing `path` and `sha256`. Preparation, live
reading and retained analysis enforce that binding. `independent_decode` may
reuse reviewed receipts only for identical stream hashes, with explicit
provenance and coverage reviewed before launch.

Build and review all four workers and both fixed comparators before preparation
and acquisition. The existing `prepare`, `execute` and report commands are
unchanged. The installed `balanced-reusable` launcher, exclusive `root`
partition with normal balancing, outside cleanup owner and independent terminal
restoration remain mandatory. No privileged helper source changes are involved.

All fixed limits remain: order 00,02,01,03,10,11,04–09,12–27; 40 pairs except
endpoint 11's 160; 1,240 pairs, 2,480 ordinary calls, 56 preflights, 112 allocation
calls and at most 2,648 starts. The primary requires a 99% upper bound strictly
below −5% and at least 10 ms arithmetic-mean saving. Every mandatory non-regression
bound is at most +1%; serial controls and all other gates remain mandatory.
The two-hour window begins at first preflight, with 2 GiB evidence and 30 GiB
registered builds. Per-call/endpoint limits, sequential fresh processes, fixed
comparators and no retries/replacements remain unchanged.

Reconstruct with `finite_confirmation_report.py` and the retained v1/register/
design plus the existing fixed 40/160 comparator arguments. The report preserves
the new schema, receipt digest and reviewed source identities and rejects mixed
historical/new completion records. It invokes no corpus worker or live lease.
Authored tests verify full schedule preservation, source/review/diff rejection,
new prerequisite bindings and complete retained reconstruction. A frozen v2
reconstruction hash from benchmark revision `0db3755` checks historical output
bytes after normalising authored temporary paths and their SHA-256 bindings.
