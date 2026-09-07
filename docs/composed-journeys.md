# Composed journey evidence

`emuella-benchmark journey TRACE.json [THRESHOLDS.json]` admits the separate
`composed_journey_trace/1` contract. It does not change the fresh-worker,
warm-input contract in `protocol.md`. Exit 0 means the complete trace meets its
frozen thresholds; 4 means admitted calibration, incomplete coverage or failed
qualification; 1 means invalid input. Failed observations remain in the report.

The typed field definitions are in `src/journey.rs`; `tests/journey.rs` contains
a wholly authored validator fixture. A trace binds full Git revisions, SHA-256
build/input/workload/evidence identities, environment and independently described
source-storage/server/compressed/decoded/GPU cache initialisation. Unknown source
cache state must say `uncontrolled`, never `cold`. A fresh process does not prove
physical storage was cold. Record the actual GPU adapter and runtime; a software
renderer cannot satisfy a threshold requiring hardware evidence.

Each observation has a value, unit and measurement boundary. An unavailable value
must instead carry a reason. Keep these quantities separate in application traces:

| Observation family | Boundary |
|---|---|
| Source hash bytes, operations and duration | Original identity scan |
| Original read bytes and operations | Instrumented original storage handle |
| Returned pixel bytes and tile callbacks | GDAL-to-encoder interface |
| Process read bytes, characters and calls | Whole process, including libraries |
| Descriptor and payload bytes/operations | Prepared representation service |
| Received and sent bytes, including retries | Actual client HTTP transport |
| Compressed reuse, occupancy and evictions | Shared client across all consumers |
| Decoded blocks, coefficients, pixels and synthesis work | Codec reconstruction |
| Decoded, compressed and metadata peaks | Shared application budgets |
| Process/worker memory and concurrency | Named native/browser/service process |
| GPU residency and uploads | Application-owned GPU resources |
| First useful, detail, revisit and visible-thumbnail latency | Named demand to named completion |

Events carry monotonic elapsed milliseconds, kind, consumer, source identity,
generation and evidence detail. Every event needs a non-blank consumer and a
declared input identity. Trace-level environment/cache fields describe global
state; unattributed global events cannot substitute for consumer coverage.
Keep demand, cancellation acknowledgement, stale
completion rejection, transfer interruption, retry, reconnect, cache eviction and
presentation distinct. A label such as `abort-image-switch` is not evidence that
a transfer was aborted: record the actual acknowledgement and counters. Application
instrumentation and its tests own causal correctness; this validator checks
admission, temporal order, known source identities and declared required coverage.
It cannot authenticate a claimed event or infer missing instrumentation.

Freeze `composed_journey_thresholds/1` before qualification. Bind the exact file
bytes through `thresholds_sha256`, retain baseline evidence hashes and rationale,
and match its workload identity. Every bound declares its unit, boundary and at
least one inclusive limit. Required event kinds must occur. Missing observations,
unavailable required values, incompatible boundaries, failed runs and software
GPU substitutions cannot pass. The freeze timestamp is checked against the run
start; durable reviewed provenance must independently establish the time and
authenticity of the freeze. The validator is not a trusted timestamping service.

Calibration traces have no threshold hash and never report qualification success.
Select numerical limits from representative baseline observations and product
requirements, then retain the same threshold file for final runs. Do not generate
thresholds from the run being assessed. Raw evidence and its actual files must be
retained by the integration owner; digest syntax checks do not verify absent files.
Repeated-run statistical comparisons remain separate from single-run admission.
