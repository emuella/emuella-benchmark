# Worker protocol v1

`src/contract.rs` is the executable serde contract. All structs reject unknown
fields and all top-level experiment, request, response and run versions must be
1. The crate exposes `contract`, `metrics`, `runner`, `compare` and `report`.

An experiment contains `schema_version`, `name`, `protocol`, `environment_tags`
and ordered `cases`. Omitted protocol selects seven rounds, five measured samples
per batch, two warmups, 30 seconds per batch and a 5% practical threshold. Explicit
protocols provide all fields. Rounds are bounded 5–1000 and samples 1–1000.

Each case declares `id`, `input` (`path`, lowercase `sha256`, optional provenance
map), optional `reference`, `image`, `operation`, `settings`, `threads` and
`output`. Input paths are resolved from the invoking working directory; use
absolute paths for portable invocation from different working directories.
References are mandatory for decode. The runner hashes every input/reference
before and after execution; encode input and all references must match raw shape
and precision. Runtime paths are not comparability keys; their digests and
provenance are.

Images declare width, height, component count, precision 1–16 and signedness.
Raw samples are interleaved, one byte at precision ≤8 or little-endian two bytes
above 8. Signed samples use sign-extended two's complement storage. Output declares
colour interpretation, layout (`interleaved`), container, losslessness, reduction,
optional source-coordinate region, expected output image and optional minimum
PSNR. Lossy requests require a finite minimum PSNR. Workers must reject unsupported
geometry, colour, layout, thread budgets, codec settings or output semantics.
`settings` is JSON for semantic codec parameters agreed by the adapter; there is
no silent automatic codec-specific default conversion.

## Executable boundary

A worker definition declares executable path, argument list, implementation name,
user-supplied source identity and optional artefact paths. The runner hashes the
executable and every artefact. File arguments such as Python scripts must also be
listed in artefacts. List dynamic codec libraries, script imports and other
build-relevant files explicitly; the runner does not discover transitive runtime
dependencies or verify the truth of user-supplied source identity.

The runner appends:

```text
--request /absolute/request.json --response /absolute/response.json
```

One process handles one case/batch, loading input once, running declared warmups
and measured repeats in memory, then writing one response. Requests contain
schema version, unique request ID, case, protocol and diagnostic flag. Workers
must exit after completing their batch and must not daemonise. Unix timeout
cleanup kills the worker process group; other platforms kill the direct child.
A worker is trusted installed code, not a sandboxed hostile executable. Logs are
redirected to files, so large output cannot deadlock pipe handling. Response JSON
is limited to 16 MiB before deserialisation. Timeouts include setup and shutdown.

A response contains schema version, matching request ID, status (`ok`,
`unsupported`, `unattainable_rate`, `failed`), nullable message, `applied_case`, boundary, samples in
nanoseconds, correctness, output byte count, nullable peak RSS and optional
JSON diagnostics. Applied case must exactly echo the semantics actually used.
Non-success needs a reason and empty samples/null correctness/output size.
Successful responses need exactly the requested measured count and positive
samples/output size.

`codec_operation` times only each in-memory codec call and its required output
allocation: input loading, warmup, reconstruction for encode validation, metrics,
worker startup and diagnostic collection are excluded. A worker supporting
`application_journey` must document the full per-sample application journey it
times (including invoked application startup and IO); it must not relabel codec
call timings. Worker-process startup itself is always outside sample timing.
Only fresh processes per batch and warm input are admitted in v1. Reused codec
contexts and cold-cache protocols require a new explicitly admitted contract.
Diagnostic requests must return diagnostic observations or explicitly report an
unsupported capability. Diagnostic runs never participate in timing inference.

Every measured output is checked outside timing. Correctness aggregates all
measured outputs: sample_count is output width × height × components × measured
repeats, exact is true only when all match, maximum absolute error is the worst,
MSE is sample-weighted, and peak is `2^precision - 1` (also for signed samples).
PSNR is `10 log10(peak²/MSE)`; null PSNR represents infinity only for exact output.
The runner checks metric self-consistency, geometry and the lossless or minimum
PSNR acceptance criterion. `metrics::measure`, `combine` and `read_raw` implement
these operations for native workers.

`output_bytes` is the encoded codestream/container size for encode and decoded
raw output size for decode. Workers must check that output size is deterministic across measured repeats
within a batch; variable per-sample size reporting is outside v1. RSS is an
observed process peak including setup/verification, not an allocation count or
codec-only peak. Missing observations are null.

## Stored evidence

Manifest and result writes use create-new semantics. Results are immutable by
library convention, not cryptographically signed or protected from manual edits.
Raw logs/requests/responses are retained with every batch, including unsuccessful
ones. A final `run.json` contains the complete experiment, worker hashes, harness
version and executable hash, machine identity, optional pairing identity,
diagnostic flag and batches. Batch identities include case, round and execution
index. No external material is acquired or copied into the results directory.

Machine identity records OS, architecture, host, kernel, CPU, available logical
CPUs, affinity, observed CPU governors and a hash of selected performance-related
environment variables. Environment tags capture additional operator-controlled
conditions. This is factual provenance, not isolation from competing workloads,
thermal drift, turbo variation or every possible environment dependency.
