# Classic forward 5/3 panel development

`classic-forward53-panels/v1` is bounded development under
`incremental-performance-policy/v1`, larger-change Route B. It measures one
width-16 row-panel policy, separating original scalar traversal (`reference`),
scalar row-panel traversal (`q1`) and parallel row-panel traversal (`qW`). The
reference is production codec `975a5e734773578f61abf76d5fddfbd837f3bd7d`.
The two panel forms share the structural implementation and differ only in a
private source constant; independent codec evidence owns that assertion. There
is no runtime selector in ordinary observations. A structural forced-reference
form used for authored correctness is outside this real-input schedule.

The [completed development record](classic-forward53-panels-results.md) retains
all observations and the original qualification-pending disposition. The later
finite attempt below closes that disposition without changing those observations.

Development provides descriptive observations, exactness and resource evidence.
It cannot qualify a production default or establish a speed claim. One policy
is within the exploration allowance of at most three; unused call headroom is
not permission for another policy, repeat or replacement observation.

## Fixed schedule and boundaries

| Stage | Full prepared inputs | Styles | Workers | Forms / rounds | Calls |
|---|---|---|---|---|---:|
| Resources | Mansfield RGB8/PAN16/MS16/RGB16 | 0/1 | 1/2/4/8 | reference, qW; one | 64 |
| Resources | Mansfield RGB8 | 0/1 | 1/8 | q1; one | 4 |
| Ordinary development | Mansfield RGB8 | 0/1 | 1/8 | three forms; three | 36 |
| Ordinary controls | Mansfield PAN16/MS16/RGB16 | 0/1 | 1/8 | three forms; one | 36 |
| Ordinary small inputs | SpaceNet Vegas img1454, Paris img235 | 0/1 | 8 | three forms; one | 12 |
| Diagnostics | Mansfield RGB8 | 0/1 | 1/8 | three forms; one | 12 |
| Unchanged decoder control | Mansfield RGB8, common OpenJPEG stream | 0/1 | 8 | reference, qW; one | 4 |
| **Total** | | | | | **168** |

Style 1 is bypass. RGB8 ordinary rounds traverse both styles and worker counts,
with form order reference/q1/qW, q1/qW/reference, qW/reference/q1 respectively.
Every form occupies each position once in each cell. High-bit-depth and small
input cells have one descriptive observation per form; no interval is inferred.
All cells use their complete existing prepared product, with no crop or resizing.
Boca, Tok and reserved Khartoum do not enter this development schedule.

Each worker is a fresh sequential process, one public facade operation, zero
warmups. The [matched boundary](openjpeg-refresh.md) includes input conversion,
workspace lifecycle, transform barriers, entropy and owned output. Input loading,
hashing, stream inspection and complete native reconstruction remain outside
the operation clock. Allocation and execution diagnostics are separate binaries
and calls; their clocks never enter ordinary samples. Process wall, CPU and peak
RSS remain separately labelled. qW has the requested existing worker budget;
that number alone does not prove participation. Codec diagnostic records own
per-level admission, actual concurrency, stage and barrier attribution.

All arms use perf/ThinLTO/one codegen unit, parallel enabled, SIMD disabled,
packed-default encoder and unchanged W, direct/global context, CPU 0 for one
worker and CPUs 0–7 for eight (prefixes for two/four). Frozen source and build
receipts bind compiler, features, configuration, worker source, native libraries,
source revision/tree and exact binary. Diagnostic feature differences are
intentional; ordinary and resource builds must retain their separate modes.

## Prerequisites, bounds and failure

Before freezing, complete codec correctness, independent source review and
native/no-std/WASM checks, including padded/thin/odd/partial extents, independent
intermediate arrays, unchanged streams, joined failures and workspace reuse.
The source-treatment receipt records the reviewed form/revision mapping; a
JSON declaration alone is not an independent source audit. The coordinator
owns these evidence checks and authenticates the existing OpenJPEG decode
receipts against every selected stream hash separately. The runner verifies
fresh raw/stream hashes and each worker verifies exact bytes and native samples.
It does not launch additional OpenJPEG operations or silently count unbudgeted
preflights. No proprietary codec or private-reference adapter/report is used.

All 68 allocation-only observations must succeed before any other stage.
Reference/qW allocation queries must remain identical at each cell, and q1
must match its reference cells. Each measured peak must fit the existing working
query and 768 MiB working limit; output capacity must fit its query and 64 MiB
limit. Counts remain factual, without a scheduling count-equality gate. Any
failure or incomplete prerequisite blocks ordinary timing. The independent
codec whole-operation allocation proof remains required; RSS is not that proof.

The shared ledger allows at most 180 starts, 90 minutes observation wall from
the first attempted call (including between-stage time), 2 GiB new observation
metadata across both approved output roots and 30 GiB registered build scratch.
Each call reserves its 120-second timeout; the process address-space cap is
8 GiB. Builds and authored checks finish before observation. At most three
material setup repairs are allowed by the workspace plan; they never reset the
ledger or replace a started observation. Protected input/stream payloads stay
in their existing authorised stores and are never copied to scratch.

A stage has an exclusive start receipt and cannot be restarted. Failed launches
consume a ledger slot and retain their request/error; failures stop the stage.
Every missing scheduled call stays explicit. A crash may leave a start without
a terminal receipt, which is incomplete evidence. One operational owner runs
stages serially and monitors the same process; no concurrent stage controllers.
No trimming, outlier removal, retries, replacement successes, extra samples or
successful-subset conclusion is permitted. Final identity and storage checks
must pass before a stage is complete. Logs and receipts stay in the original
approved source stores, with source notice and attribution.

## Freeze and run

Reuse `scripts/openjpeg-refresh.py build` to produce ordinary,
`--allocation-diagnostics` and `--execution-diagnostics` receipts for each form.
Candidate-only detailed forward-5/3 diagnostic features may supplement the last
mode, without entering ordinary builds. Retain exact build receipts/logs in the
approved store before disposable build cleanup; the freeze embeds each build
receipt but does not copy the executable or external library.

The operator supplies an absolute-path JSON configuration:

```json
{
  "policy": "classic-forward53-panels/v1",
  "panel_width": 16,
  "cpus": [0, 1, 2, 3, 4, 5, 6, 7],
  "budget": "/approved/rareplanes/panels-development/budget.json",
  "source_receipt": "/approved/rareplanes/panel-source-receipt.json",
  "arms": {
    "reference": {"ordinary": "/build/reference/ordinary/build.json", "resource": "/build/reference/resource/build.json", "diagnostic": "/build/reference/diagnostic/build.json"},
    "q1": {"ordinary": "/build/q1/ordinary/build.json", "resource": "/build/q1/resource/build.json", "diagnostic": "/build/q1/diagnostic/build.json"},
    "qW": {"ordinary": "/build/qW/ordinary/build.json", "resource": "/build/qW/resource/build.json", "diagnostic": "/build/qW/diagnostic/build.json"}
  },
  "stores": {
    "rareplanes": {"prepared": "/approved/rareplanes/prepared-final", "streams": "/approved/rareplanes/openjpeg-refresh-main-01", "output": "/approved/rareplanes/panels-development"},
    "spacenet": {"prepared": "/approved/spacenet/prepared", "streams": "/approved/spacenet/classic-baseline", "output": "/approved/spacenet/panels-development"}
  }
}
```

The source receipt contains `panel_width: 16` and `forms`, keyed by `reference`,
`q1`, `qW`. Each entry has a full `revision`, absolute clean checkout `source`
and `form` respectively `Reference`, `RowPanelScalar`, `RowPanelParallel`.
Keep these source checkouts committed and unchanged throughout observation.
The receipt also carries the coordinator's source-audit evidence as appropriate.

Create only the RarePlanes output directory and its `budget.json` before freeze.
The budget contains `policy`, `protected_output_roots` (both new output roots
and any additional, non-overlapping metadata binding roots in the same approved
stores) and `scratch_root` (registered campaign scratch). Entire source stores,
prepared inputs and stream roots cannot be budget metadata roots. No existing
observation root or ledger state may be reused. Freeze/run verify reviewed
RarePlanes/SpaceNet notices and existing prepared manifest locks through the
inherited asset selectors, constrain all raw/stream paths to the approved store,
and reject reserved SpaceNet selections.

```sh
python3 scripts/classic-forward53-panels.py freeze --config CONFIG.json --output STORE/panels-development/freeze.json
python3 scripts/classic-forward53-panels.py run --freeze STORE/panels-development/freeze.json --stage resources
# Inspect the complete resource gates before requesting ordinary observations.
python3 scripts/classic-forward53-panels.py run --freeze STORE/panels-development/freeze.json --stage ordinary
python3 scripts/classic-forward53-panels.py run --freeze STORE/panels-development/freeze.json --stage diagnostic
python3 scripts/classic-forward53-panels.py run --freeze STORE/panels-development/freeze.json --stage decoder
python3 scripts/classic-forward53-panels.py report --freeze STORE/panels-development/freeze.json --output STORE/panels-development/report.json
```

The report retains every available row and missing index, labels incomplete
stages, reports raw ordinary samples and arithmetic means separately from
instrumented observations, and always leaves qualification pending. Reporting
is offline and does not launch or replace calls. Output files are exclusive;
choose a new report filename when inspecting a later stage.

## Finite confirmation closed before launch

The historical [precision study](precision-feasibility-results.md) completed all
18 sessions. Boca RGB8 encode at one and eight workers established the +1%
both-direction predicate in 0/3 sessions each. Boca eight-worker reverse upper
bounds were +5.253%, +6.690% and +6.594%; conditional 160-pair, zero-centred
projections left worst-direction upper bounds at +1.471–+1.781%. The later
[balanced A/A study](balanced-measurement-stability-results.md) remains planning
evidence, including its unresolved representative RGB16 precision. Neither study
is candidate confirmation or a new estimator.

The engineering owner subsequently authorised one prospective
`classic-forward53-finite-confirmation/v1` attempt despite incomplete A/A
precision. That amendment removed the feasibility-based launch prohibition for
this attempt only. It retained the source, estimator and all mandatory gates.
Operational admission then failed: a fresh exclusive balanced reservation was
unavailable without administrator authentication. The previous A/A reservation
had been independently restored; its single-use receipt could not authorise a
new reservation. The terminal disposition is **DECLINED BEFORE LAUNCH**, with
**zero corpus worker starts**. Production remains unchanged. No statistical
rejection, measured speedup or automatic retest obligation follows.

The workspace owns the complete 28-endpoint register, unchanged owner rows,
source design, inherited resource/output requirements, exact manifest bytes and
their independently pinned hashes. Public benchmark tooling imports those rows
without reproducing that owner data here. The fixed plan uses 40 alternating
AB/BA pairs for 27 endpoints, including the sole Boca RGB8 bypass/eight primary;
only endpoint 11, Mansfield RGB16 bypass/eight, has 160 pairs. Endpoint order is
`0, 2, 1, 3, 10, 11, 4, 5, 6, 7, 8, 9, 12..27`. Each endpoint's two preflights
precede its allocation prerequisites and ordinary samples. Initial Boca RGB8
and Mansfield RGB8 allocations precede primary timing; RGB16, PAN16, MS16, Tok
and Vegas allocation groups precede endpoints 10, 4, 12, 16 and 24 respectively.
The unchanged allocation matrix has both styles, workers 1/2/4/8 and both arms.

The schedule contains 1,240 pairs / 2,480 ordinary calls, 56 preflights and 112
allocation checks: at most 2,648 starts including failures. The 7,200-second
clock begins at the first preflight and includes between-stage work. New evidence
is capped at 2 GiB and registered builds at 30 GiB. Each new start requires
150 seconds and 1 MiB remaining headroom, including its 120-second timeout.
There are no retries, replacement observations, extra samples, interim
performance decisions at 40/80 of 160 pairs, or second round.

`scripts/finite_confirmation_analysis.py` is an offline library with no
acquisition entry point. `make_manifest(register_path, source_design_path)`
imports the full rows and freezes source, comparator, schedule and limits;
`load_manifest(path, expected_sha256, register_path, source_design_path)` verifies
externally pinned bytes and reconstitutes the same binding. Source-design hashes
bind inherited owner requirements without treating a hash as proof of their
correctness or authority. `analyse_endpoint` accepts exactly 40 or 160 pairs,
uses the unchanged owner comparator and retains failed or missing observations.
`analyse_attempt` reconciles the complete planned call prefix, owner checks and
retained consumption counters. It preserves every unstarted endpoint and stops
inference after the first failed or unresolved endpoint. Budget checks are
arithmetic on supplied counters, not live resource enforcement.

Candidate acceptance is directional. The primary requires a 99% relative-time
upper bound strictly below −5% **and** arithmetic-mean saving at least 10 ms;
each critical endpoint requires upper bound at most +1%. A primary saving below
10 ms is **NOT SELECTED**, without implying slowdown. A primary interval wholly
at or above −5%, or a critical interval wholly above +1%, also yields
**NOT SELECTED** with its respective interval interpretation. A complete interval
that does not resolve its required bound yields **NOT QUALIFIED WITHIN BUDGET**,
even when its point estimate crosses the limit. Failed/missing observations,
owner gates, environmental validity or exhausted caps yield **OPERATIONALLY
INCOMPLETE**. Legacy +/-5% timing verdicts and both-way A/A diagnostics remain
separate from these candidate gates. Primary gain cannot override a later
unresolved critical endpoint.

A favourable synthetic reconstruction is labelled **PASSES OFFLINE GATES** and
never authorises promotion. The declined attempt did not implement or qualify
live bindings for reservation, rights/locks, source review, preflights, independent
decode receipts, allocation/output limits, start ledger, monitoring or restoration.
Existing balanced reservation admission and restoration tests remain applicable
to their own helper. No live confirmation runner or acquisition command is
provided. Future source reuse requires a separately authorised objective and
prospective evidence plan.

RarePlanes Dataset, June 2020: J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and
AI.Reverie, CC BY-SA 4.0. SpaceNet Dataset, SpaceNet Partners and DigitalGlobe
imagery, CC BY-SA 4.0; Van Etten, Lindenbaum and Bacastow (2018).
