# Isolated codec workers

The optional `workers/` Cargo workspace links genuine codecs behind the same
request/response contract as any third-party worker. The root measurement library
has no codec dependency. Native workers require Rust compatible with the pinned
Emuella revision, a C compiler, `pkg-config`, and installed OpenJPEG development
headers/library version 2.5 or newer. The supplied build helper targets Linux
(the dependency inventory uses `ldd`). OpenJPH's installed `ojph_compress` and
`ojph_expand` applications must also be discoverable on `PATH`.

```sh
python3 scripts/build-workers.py --output /approved/scratch/build-baseline
```

Choose a new absolute output directory outside the checkout for each build. The
helper snapshots project-owned adapter/core source, builds release executables by default,
and writes `emuella-worker.json`, `openjpeg-worker.json`, `openjph-worker.json`
and `build-provenance.json`. Pass a worker JSON directly to the harness. Native
OpenJPEG binaries receive an RPATH from the installed pkg-config library path;
unresolved dynamic dependencies fail the build inventory. OpenJPH executable
paths are resolved and bound into the binary at build time; runtime PATH changes
cannot substitute those programs in a helper-built worker.

A different clean Emuella checkout can provide a baseline or candidate:

```sh
python3 scripts/build-workers.py --output /approved/scratch/build-candidate \
  --emuella-source /checkout/emuella-j2k \
  --emuella-revision FULL_COMMIT_SHA \
  --target-dir /approved/scratch/candidate-target
```

The checkout must match the exact requested revision and be clean before and
after building. Cargo overrides and dependency resolution occur in the build
snapshot, leaving the benchmark checkout's lockfile unchanged. The provenance
sidecar records compiler identities, requested profile, observed features,
performance-relevant build flags, every adapter/core source digest and the exact
resolved worker dependency lock. Definitions bind this sidecar and the actual
runtime shared libraries; OpenJPH also binds both installed CLI executables and
their shared dependencies. Local source paths and executable paths exist only in
runtime manifests, binaries and provenance. Do not commit build snapshots or
runtime result inputs. Use separate target directories for concurrent builds.

Select the worker-owned tuned profile with `--profile perf`, and optionally add
`--simd` to either profile. The four build variants are `--profile release`,
`--profile release --simd`, `--profile perf`, and `--profile perf --simd`.
Omitting both options preserves release compilation without optional SIMD.
The `perf` profile inherits release and requests optimisation level 3, ThinLTO,
one codegen unit and line-table debug information. SIMD forwards to both the
public codec facade and the diagnostic codestream dependency. Parallel support
remains enabled in all four variants; runtime thread budgets remain independent.
Neither option changes codec source or coding settings.

`requested_build` records the selected profile, SIMD switch and use of default
features. The legacy `profile` field is also the requested profile name;
`features` now lists observed Cargo artefact features. `build_observations`
retains the exact Cargo command, configuration-file identities and compiler
artefacts, including each package's resolved features, Cargo-reported profile,
executable path and cache freshness. The helper copies these reported executable
paths, including target-specific paths selected by Cargo configuration.
`build_environment` records relevant compiler, profile, target and native build
overrides. The source snapshot and resolved lock remain part of provenance.

Cargo's JSON artefact profiles do not describe every effective compiler option:
rustflags can override profile values. The bound `cargo-build.jsonl` and verbose
`cargo-build.stderr` retain the observations and ordered commands dispatched by
Cargo, including LTO and codegen arguments when a crate is compiled. Use fresh
target directories for build qualification. Cached (`fresh: true`) artefacts
have no new compiler command, and compiler wrappers can transform dispatched
arguments internally; those internals are not observed. Do not infer a fully
verified effective profile from the requested name or Cargo profile fields
alone. Configuration files are identified by path and digest without copying
potential credentials. These logs and environment values are local build
evidence and may contain machine paths; do not publish them verbatim.

The default Emuella source is revision
`1c1a7fbc583d69c6d57bfd1da4248aa6fae071cc`. Its public facade owns headline operations;
the same pinned codestream crate exposes opt-in diagnostic instrumentation.
`parallel` is enabled and each batch uses a local Rayon pool with the requested
thread budget. This bounds available workers, without claiming that every codec
route can use all of them. OpenJPEG receives its public thread-budget setting.

## Workloads and capability boundaries

All workers admit unsigned 8-bit or little-endian 16-bit interleaved raw input,
one or three uniformly sampled components, `colour: "native"`, and
`container: "j2k"`. The container declares raw codestreams; decoded output is
always packed interleaved native samples. Decode references must already have the
requested ROI/reduced geometry and semantics. Neither metrics nor workers invent
reduced-resolution reference samples by resizing full output.

The two native workers additionally admit exactly eight unsigned U16_LE bands
for classic lossless D2 full-image operations. Bands are positional native
components: Emuella uses `ColorModel::Unknown`, OpenJPEG uses
`OPJ_CLRSPC_UNSPECIFIED`, and neither applies MCT or infers colour/spectral meaning.
Axes are 4 through 32768 with at most 32 Mi spatial pixels (256 Mi component
samples). The profile is raw Part 1, one full-image tile/tile-part, LRCP, one layer,
unit sampling and reversible 5/3. MSI U8, lossy, HT, ROI/reduction, other component
counts and coding overrides are explicit unsupported workloads. This additive
worker profile does not redefine the codec's broader existing decode admission.
OpenJPH remains limited to the original grey/RGB contract.

| Worker | Boundary | Encode settings | Partial decode |
|---|---|---|---|
| Emuella | `codec_operation` | `coding: classic` or `ht`; lossless `decomposition_levels`; lossy `target_bpp` with exactly two decompositions | Actual public `decode_partial`; the codec's bounded supported profiles apply |
| OpenJPEG | `codec_operation` | `coding: classic`; `decomposition_levels`; lossy `target_bpp` or `compression_ratio` | Actual OpenJPEG reduction and decode-area APIs |
| OpenJPH | `application_journey` | `coding: ht`; `decomposition_levels`; lossy `qstep` | CLI `-skip_res d,d`; ROI is unsupported |

`decomposition_levels` is required explicitly for every encode request, so an
omitted setting cannot select different defaults across adapters.
Lossy Emuella requires a finite positive `target_bpp` exactly representable by its
public `f32` API. OpenJPEG maps target bpp to
`precision * components / target_bpp`, then uses the public encoder's floating
compression-ratio parameter with irreversible coding and one quality layer.
These codecs have different rate controllers: the OpenJPEG value requests a rate
allocation target and is not an Emuella-style strict codestream budget guarantee.
Actual encoded size and distortion must be compared at every point. Explicit
`compression_ratio` and `target_bpp` are mutually exclusive. OpenJPH's `qstep`
is a separate quantisation parameter, never relabelled as a bpp target. Lossless
rate settings and missing lossy rate settings are rejected.

Encode uses one tile, LRCP and one layer through the selected profiles. Emuella
classic RGB automatically applies the reversible colour transform for lossless
coding and the irreversible colour transform for target-rate coding; its public
`EncodeOptions` has no MCT toggle. Emuella greyscale and the bounded HT encoder
profiles use no MCT. OpenJPEG explicitly disables MCT and OpenJPH sets
`-colour_trans false`. Consequently these adapters compare equivalent native
output semantics with different encoder colour-transform policies, not identical
encoding profiles. Interpret compressed size and timing with that difference in
view. Every successful encode response records its effective coding family,
decomposition count and MCT policy in `diagnostics.encode_profile`, including
uninstrumented runs; these are fixed profile facts, not diagnostic measurements. Decode cases accept only the
`coding` setting: decomposition count and rate are encoder requests and must be
removed when constructing a decode case. Unknown parameters, unsupported thread
budgets, incompatible boundaries and unsupported codec profiles return explicit
non-success responses. Malformed inputs, digest changes, incorrect samples and
internal execution failures return `failed`. The pinned Emuella facade flattens
its rate-unattainable errors into three documented error-detail strings; those
exact strings map to `unattainable_rate`, and no other error is reclassified.

OpenJPH supports exactly one requested thread because this CLI exposes no thread
budget control. Its worker requires an existing explicitly authorised derivative
store through `EMUELLA_BENCHMARK_DERIVATIVE_STORE`. Set this only when the input's
existing rights permit these PNM/codestream derivatives in that store. The worker
exclusively creates a randomly named private batch directory there and removes
only that owned directory afterwards. An existing path is never adopted for
cleanup; a name collision cannot delete its contents.
Project-authored inputs need no external corpus; protected inputs require the
applicable existing authority. No payload or external program output enters the
JSON response or public evidence.

## Measurement and diagnostics

Every native timed call includes codec creation/allocation and complete requested
output production. Decode layout conversion and OpenJPEG sample packing are
inside the timer; file reads, input digest checks, reference loading, metric
calculation and encode verification decodes are outside it. Inputs are loaded
once per fresh process batch. No prepared context or reusable scratch survives
between headline samples. Warmups execute the same operation and are verified;
all measured outputs contribute to aggregate correctness. A single invalid
output invalidates the batch rather than disappearing from its samples.

OpenJPH timing includes process launch, the codec application's IO and output
reading. Every compression or expansion removes its previous output before
launch and requires a newly created regular output file, including verification
expansion. This prevents an exit-zero command that omits output from reusing a
warmup result. Output cleanup and freshness checks are included in the relevant
application operation timer. Encode also includes raw-to-PNM packing/writing;
verification expansion and its cleanup are outside the encoder timer. Decode
stages the warm codestream before sampling and reads/validates each generated
PNM during the timed journey. This boundary is
not comparable with native codec-operation samples.

Native workers report observed Linux `/proc/self/status` `VmHWM` in bytes. This
is the peak RSS of the entire batch process, including setup and verification;
it is not a codec-only peak allocation measurement. OpenJPH leaves RSS absent
because the wrapper's peak would not measure its codec child.

Diagnostic Emuella requests perform a separate prepared Part 1 decode after the
headline samples, using detailed profiling with actual Tier-1 work counters and
the same thread budget. `diagnostics.observations` contains plan memory, planned
parallelism, preparation measurements, executed code blocks, coefficients/codeword bytes,
Tier-1 work counters and executed phase workers. Diagnostic output is verified
against the headline native decode. Unsupported diagnostic routes include
`diagnostics.unsupported_reason` while retaining the independently valid headline
measurements. If preparation succeeds but diagnostic execution is unsupported,
that reason remains alongside the preparation observations. OpenJPEG and OpenJPH
have no diagnostic instrumentation; both encode and decode diagnostic requests
return an explicit `diagnostics.unsupported_reason` with their separately
verified headline results. Fixed encoder profile facts never count as diagnostic
observations. Diagnostic data never replaces or subdivides the headline sample
vector.

## Verification

```sh
cargo fmt --manifest-path workers/Cargo.toml -- --check
cargo clippy --manifest-path workers/Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path workers/Cargo.toml --release
```

The authored native matrix checks grey/RGB U8/U16 and eight-band U16, two threads,
full-range values and distinct band order, exact round trips,
all-output metric counts, actual RSS, unknown settings, changed input digests,
diagnostic execution/output equivalence and distinct unattainable-rate outcomes.
Native MSI tests also prove Emuella-to-OpenJPEG and OpenJPEG-to-Emuella full-reference
interoperability, reject unsupported requests, and exercise truncated envelopes,
marker lengths, tile-part lengths and coding overrides before timing.
A generated COD-profile regression also checks that classic RGB U8/U16 streams
signal MCT at zero, one and two decomposition levels.
The repository's qualification journey additionally exercises common codestream
decode, independently generated partial references, lossy points and OpenJPH
application journeys. Unsupported profiles remain visible in those results.

OpenJPH fault-injection tests preserve an existing scratch sentinel and simulate
successful commands that stop producing output after warmup, separately for
compression, measured expansion and verification expansion. Diagnostic encode
and decode responses from both external adapters pass the common response
validator with their explicit unsupported capability disposition.
