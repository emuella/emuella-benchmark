# Retained MQ D2 incremental confirmation

## Prospective identity and boundary

This new experiment selects `incremental-performance-policy/v1`, Route A. It
retests only the retained decoder MQ D2 decision-local-register/exchange factoring
against production codec `e0971bc82d18d787a47c53ff27ed51a81e70b94c`.
The selected candidate is codec `07c85ecac1fbe1c477c05a8f6c8d605d1039d9ad`
(tree `98206d5e870b1601815508796b83aac0ffbe24df`). Its production MQ source
is unchanged from the independent Route A review of
`3b010f001b7cc19db35e868cf1d525bdef47eef0`; the final delta adds a scratch
reuse-after-error test. The coordinator must bind the protocol revision,
worker/build hashes, immutable inputs and streams before releasing any timing.
No screening, alternative mechanism, estimator change or calibration is allowed.
The independent low-cost review must confirm no new buffer, persistent state,
backend, scheduler, option, unsafe/ISA dependency or material failure surface.

Reuse [matched refresh](openjpeg-refresh.md) facade clocks, perf optimisation 3,
ThinLTO/one codegen unit, parallel without SIMD, direct/global calls, selector
unset and original W scheduling. One-worker processes use CPU 0; eight workers
use CPUs 0–7. Lossless D2/style zero and bypass remain separate. RGB uses RCT;
PAN/MSI use no MCT. Zero warmups, one operation per fresh process, twenty adjacent
alternating AB/BA pairs per contrast. Use the unchanged
[ratio-of-arithmetic-means comparator](comparisons.md), conservative 99% per-case
interval and legacy ±5% timing verdict. No family-wide confidence is claimed.

## Frozen endpoints and finite stages

The single promotion primary is full Boca Raton PAN16, style zero, one worker,
common OpenJPEG-origin stream. Require candidate/baseline mean change <=−2%,
99% upper change bound <0 and mean saving >=20 ms per complete operation.
The absolute floor represents one second saved per fifty serial full-image
decodes. It is a prospective engineering value, not an estimated noise floor.
Boca MSI16 under identical settings is mandatory corroboration: its upper
change bound must be <=+1%; it cannot replace PAN16 as primary.

Every other critical contrast below also requires upper bound <=+1%.
Complete both initial contrasts before deciding. Only success of all initial
predicates permits the fixed regression/resource stage. Complete that stage
before disposition; it cannot rescue a failed primary. Missing/invalid evidence
blocks disposition. A point reduction below 2% or saving below 20 ms is
`not-selected`, with the interval retained. Adequate point/absolute saving but
upper bound >=0 is `insufficient precision`, not evidence of no effect. An MSI
upper bound >+1% means required non-regression is unproved; call it regression
only when the interval establishes regression. Missing baseline/candidate
absolute acceptance remains a blocker. A complete failed predicate stops subsequent conditional
work. There is no external timing anchor or independent performance screening.

| Stage and operation | Products | Styles | Workers | Stream origin | Contrasts |
|---|---|---|---|---|---:|
| Initial decode | Boca PAN16/MSI16 | 0 | 1 | OpenJPEG | 2 |
| Regression decode | Boca PAN16/MSI16 | bypass | 1 | OpenJPEG | 2 |
| Regression decode | Tok RGB8 | 0/bypass | 1/8 | OpenJPEG | 4 |
| Regression decode | Boca PAN16/MSI16 | 0 | 8 | OpenJPEG | 2 |
| Regression decode | Boca PAN16/MSI16 | 0 | 1 | Emuella | 2 |
| Regression encode | Mansfield PAN16 | 0/bypass | 1 | Emuella | 2 |
| Regression decode | SpaceNet Vegas img1454 RGB16 | 0/bypass | 1 | Emuella | 2 |

The 16 contrasts consume at most 640 ordinary calls: 80 initial and 560
conditional. `classic-encoder-kernel.py --study incremental` selects only these
stages (`primary`, `confirm`, `spacenet`); legacy arm names `reference`/`packed`
mean baseline/candidate, with packed-default encoder selection in both.
No stage may add rounds, pool products, remove outliers, substitute successful
calls, alter thresholds, select another primary or retune the candidate.

## Correctness and resources

Before timing, pass current independent MQ/raw oracle, platform/failure tests
and independent Route A source review. Separate allocation builds execute the
changed decoder anew with complete native-sample verification:

- Before initial timing: both arms, Boca PAN16/MSI16, both styles, 1/2/4/8
  workers, both immutable stream origins: 64 calls.
- Before initial timing: both arms, Mansfield PAN16 encode, both styles,
  1/2/4/8 workers, immutable Emuella stream: 16 calls. Require unchanged complete
  stream bytes; codec tests additionally cover pass/segment metadata.
- Only after initial success: both arms, Tok RGB8 and Mansfield PAN16 decode,
  both styles, 1/2/4/8 workers, both origins: 64 calls; Vegas img1454 decode,
  both styles, 1/2/4/8 workers, Emuella origin: 16 calls.

`scripts/mq-d2-resources.py` owns this fixed 160-call cohort. Allocation builds
emit no headline samples. Preserve facade peak additional requested allocation
and successful allocation/reallocation request count separately from process
RSS/CPU. Require count equality within each identical arm pair; unexplained drift
blocks acceptance. Peaks need not match because parallel overlap can differ.
Require peak <=768 MiB and <=the existing conservative geometry/encode working
query, explicitly a comparison bound rather than a decoder requirements API.
Source review must establish no unexplained additional buffer/runtime state.

Keep 120-second per-call timeout and 8 GiB address-space ceiling for every arm.
The 768 MiB working and 64 MiB encoded-output limits remain worker admission
settings. Native decoded byte count follows exact geometry; 64 MiB is not a
native-image-size or process-RSS cap. Candidate and baseline must satisfy their
absolute limits separately. A failing control cannot prove a candidate regression
or fulfil absolute acceptance. Immutable independent decoder receipts may be
reused only with exact stream hash/source provenance; changed native decoding
always executes anew. Authored malformed/resource/failure and worker parity
checks complement this bounded image cohort.

## Budget, exposure and evidence

Maximum total is 800 codec calls, zero acquisitions and zero new streams.
Allow at most two failed setup repairs before timing; retain failures and never
replace successful observations. The setup/build/check two-hour cap starts at protocol freeze; pre-freeze
authored tooling/check preparation is recorded separately.
all codec observation stages together have a two-hour wall cap. Cap newly
created protected evidence at 2 GiB and registered disposable build scratch at
20 GiB. Required landing/review/CI is outside these experimental cost caps.
`mq-d2-budget.py` enforces one shared persistent 800-call/two-hour ledger
before every observation process, including resource calls, reserving the full
120-second call timeout. The frozen budget JSON lists every new protected output
root and the registered campaign scratch root; it must be passed to every stage.
The sole operational owner also checks setup and storage caps between stages; interruption preserves started evidence and means incomplete,
never successful qualification on a smaller sample.

RarePlanes uses the existing nine-product prepared manifest
`6c37b54bf75af0c17c1b67c5ad7bd2d56b5d34d45de9737ddb50d0fc1fe10e7b`, with streams
from the matched refresh. SpaceNet uses prepared manifest
`209eb97c250f108c4ff0aff9a226db6dc6e4ecd68b10bc074e844b60b89e406e`, only the
existing development Vegas img1454 chip and existing classic-baseline streams.
The runtime identity manifest binds every selected raw/stream digest and source
lineage. Source acquisitions Mansfield, Boca, Tok and Vegas are previously
exposed; related products stay grouped. None is an untouched holdout. Khartoum
remains reserved and excluded. Do not invoke external codecs for timing.

Protected inputs, derivatives, raw observations and receipts remain inside each
existing approved input store with original notices and lineage. Retain build
receipts there before registered scratch cleanup. Public evidence contains only
permitted factual measurements and identities. Report baseline qualification,
candidate effects/uncertainty, legacy timing verdict and engineering disposition
separately, including every failed and unstarted conditional gate.

RarePlanes Dataset, June 2020: J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and
AI.Reverie, CC BY-SA 4.0. SpaceNet Dataset, SpaceNet Partners and DigitalGlobe
imagery, CC BY-SA 4.0; Van Etten, Lindenbaum and Bacastow (2018).
