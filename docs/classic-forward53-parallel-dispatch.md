# Parallel forward 5/3 dispatch treatment

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
