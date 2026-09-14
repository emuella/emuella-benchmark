# Classic parallel execution: initial diagnosis

This is the bounded baseline diagnostic milestone under the
[frozen protocol](classic-parallel-execution.md), before any scheduling variant.
It is not a throughput or promotion result. Twelve separate feature-enabled
facade calls completed: Mansfield complete PAN16/MS16/RGB8, style zero and bypass,
eight workers followed by one worker. Every complete stream matched its immutable
reference digest and every reconstructed native sample matched the input.

Eight-worker peaks reached eight overlapping blocks in all six cases. Mean
active blocks below divide the integrated block intervals by the complete
Tier-1 invocation/join wall interval. Tails sum the time from the first finished
block to the last finished block in each batch; these overlapping intervals are
not additive stage time or directly recoverable savings.

| Product | Style | Diagnostic facade ms | Tier-1 invocation ms | Mean active blocks | Accumulated tails ms | Dispatch + join edges ms |
|---|---|---:|---:|---:|---:|---:|
| PAN16 | 0 | 240.225 | 187.971 | 7.193 | 21.192 | 3.091 |
| PAN16 | bypass | 166.891 | 112.682 | 6.419 | 30.104 | 3.140 |
| MS16 | 0 | 132.076 | 111.807 | 6.380 | 45.238 | 1.693 |
| MS16 | bypass | 77.676 | 57.214 | 6.019 | 24.244 | 1.569 |
| RGB8 | 0 | 477.554 | 300.945 | 5.690 | 94.028 | 10.245 |
| RGB8 | bypass | 412.598 | 238.614 | 6.351 | 67.867 | 7.624 |

Mean active blocks restricted to time with any active block were respectively
7.314/6.605 for PAN16, 6.479/6.190 for MS16 and 5.892/6.563 for RGB8. Peak
parallelism therefore exists; uneven joined batches and their serial edges are
a plausible finite-window target. RGB8's conversion plus DWT occupies another
approximately 147–150 ms, outside that target. No scheduling gain is inferred
from these diagnostic observations alone.

The one-worker diagnostic facade times were 1383.944/761.677 ms for PAN16,
723.923/357.781 ms for MS16 and 1821.180/1643.722 ms for RGB8 (zero/bypass).
Every one-worker call used the existing serial branch and observed peak one.
The retained evidence includes fixed duration histograms, exact min/max/count/sum,
ordered appends, disjoint existing stages and their stated serial-bypass boundary.

Parallel aggregate bookkeeping took 0.092–0.482 ms per call. This is only its
measured interval: clock reads, profiled accounting and atomic allocation
metering also perturb the diagnostic. Total overhead remains unquantified until
separate ordinary screen baseline observations are available. These values supply
no headline samples or estimator inputs.

Eight-worker retained Tier-1 scratch totalled 264,416 bytes; retained result
capacity was at most 65,536 bytes and collectors at most 2,048 bytes. The largest
additional requested allocation peak was 197,880,720 bytes, including output and
conservative old/new growth overlap. Process RSS reached 291,647,488 bytes and
includes input, verification and process setup. These are separate observations,
not interchangeable resource bounds. Packed-storage presence may be inherited
from an earlier block; unchanged source selection and the authored real-entry
routing test establish packed dispatch with the selector unset.

The ordinary baseline build uses merged codec
`94ba19589b0710192c295478c1f9ad284ea2abd5`, executable SHA-256
`e4ef5e53b957055d62bdb07a9254abcef708e8ded0e166794300df0b6f1c8cc5`.
The attributed diagnostic source is codec
`032150dbb436d171bddacd0b8d0d700b2d7966ef`, executable SHA-256
`db21c696bab5fb89a20c1d98bef4088b76339fad70e64603c2de00b5ab65f45d`.
Both compiled benchmark source at
`f62c6eb5c2e524e5faa583e3fb8eb6916b4db075`. The baseline measurement record has
SHA-256 `9e14be124451ad3dd309ce60ba3df0ea58576fe96dd78832b94f4b24f866917b`.
Full requests, responses, machine/process metrics, histograms, immutable stream
bindings, build receipts and logs remain with the authorised RarePlanes store.

An initial build failed because declaring a new optional dependency feature
prevented Cargo resolving the historical baseline. The driver now enables the
codec feature explicitly only for diagnostic builds; both matched builds passed.
An authored worker fixture initially used incompatible default encode options;
its corrected explicit D2/raw/lossless fixture passed. A codec compilation exposed
private observer helper visibility and was repaired. These setup failures are
retained separately and consumed no protected diagnostic calls.

## Finite screen and frozen selection

Both predeclared variants completed all 72 fresh-process calls with exact
streams: three alternating baseline/candidate pairs for every development
product/style at one and eight workers. Both passed authored correctness and
resource probes and the fixed screening eligibility rules. The geometric mean
of six eight-worker candidate/baseline ratios was 0.903174 for 2W and 0.882386
for 4W. The latter is 2.30% lower, beyond the 1% tie band, selecting **4W**.

| Product | Style | 2W one-worker ratio | 2W eight-worker ratio | 4W one-worker ratio | 4W eight-worker ratio |
|---|---|---:|---:|---:|---:|
| PAN16 | 0 | 1.0066 | 0.9093 | 1.0040 | 0.8620 |
| PAN16 | bypass | 0.9988 | 0.9467 | 0.9940 | 0.8642 |
| MS16 | 0 | 0.9996 | 0.8076 | 0.9977 | 0.8990 |
| MS16 | bypass | 1.0007 | 0.9112 | 0.9719 | 0.8573 |
| RGB8 | 0 | 0.9926 | 0.9040 | 1.0038 | 0.9186 |
| RGB8 | bypass | 0.9946 | 0.9478 | 1.0025 | 0.8951 |

The 2W screen had lower ratios for eight-worker MS16/style zero and RGB8/style
zero. Selection follows the frozen aggregate rule, not every-case superiority.
These are separate three-pair screens, without confidence or a direct paired
2W-versus-4W claim. No development mean regression exceeded 5%; both styles
improved a high-bit-depth eight-worker mean by at least 5%.

The measured variant source is codec
`56c6c863716a476ea18c05da5e86f0ff6174f662`, with explicit geometry selectors 2
and 4; both use benchmark `c2c955c99d8fdddadff57e1f5b2cc865e8f4063e` and leave
the packed encoder selector unset. Screen report SHA-256 identities are
`e81495a70dc068904e472128c5f78fe4769b8717107610ccc7b3f61e7ec9f45d` (2W) and
`50314aba28ec75e3c045fa927ad39df32de499a9027a6f1fb2ed0be163a0cb9d` (4W).

Before confirmation, codec `8aca0cde9031c9e81f5cec33b3f09a8d2a330128` freezes
4W as a constant and removes the experimental geometry selector. The same
geometry-only policy funds each extra result slot with 4 MiB after choosing the
unchanged W; insufficient residual memory shrinks N or retains W batches.
The one-worker branch remains serial. Canonical/CI coverage now includes the
new deterministic scheduler and diagnostic tests. No confirmation-driven policy
retuning is permitted. Full confirmation and remaining qualification are pending.

RarePlanes Dataset, June 2020: J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and
AI.Reverie, CC BY-SA 4.0. Original notices and source lineage remain with the
local evidence. These are previously measured products on one host.
