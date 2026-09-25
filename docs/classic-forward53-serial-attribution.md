# Classic forward 5/3 serial attribution: build and observation identity

`classic-forward53-serial-attribution/v1` investigates the closed dispatch
comparison. This record supplies build provenance and separates evidence layers;
it does not reopen qualification or alter the archived candidate's disposition.
The [factual identity extract](evidence/classic-forward53-serial-attribution.json)
binds the original preparation, two historical receipts and one ordinary
reconstruction per arm. Codec owns the compiled-code interpretation.

## Historical comparison recovered

The preparation SHA-256 is
`f84c3a97f0bbabf4f7e9530934d853f01ec9da082849fb275f5e76ccbf5e67e8`.
Its acquisition runner is `7c5e24c4e07221e2f401b8ee4374f28a969dd406`, but
both ordinary workers were built from benchmark
`0db375523ead4ff5113d7e73a77a39b04cff6644`. These are different roles.
The [closed report](classic-forward53-parallel-dispatch.md) remains authoritative
for every earlier started and unstarted endpoint.

| Arm | Codec revision | Historical executable SHA-256 |
|---|---|---|
| Baseline | `a7576ad03486e097ac923b8e49cac39a1cbef5d2` | `a58280ce1c3f4c69c05b5258108b82d5a6e7724db74a77173ac6ac9b39deb187` |
| Candidate | `4f5bfb39f02e043c9a1f594a8159d3cf86d52c3f` | `682f2e85811157619c14b7635c24b8d3bcc289666269bb59f408902c535616f9` |

Endpoint 01 is full Boca RGB8, 5577 × 5036 × 3 interleaved U8, style zero,
one worker. Its raw hash is
`aaf064a2d6b302d839e7f3c13b99e1344ba749fed53be6daf64f8a6c4c67bfe7`;
its 14,339,292-byte stream hash is
`5686eb89ffbf5152d5572441347ec388ae107d0e6790086a817a5529b702843c`.
Retained requests `ordinary-0160` through `ordinary-0239` cover 40 pairs.
All 80 request/result/terminal receipt sets exist, succeeded, and bind these
hashes and the ordinary owned-interleaved facade boundary, with 40 results per
recorded executable. Existing input and stream files still match their hashes.

The facade uses classic raw J2K, reversible 5/3, reversible colour transform,
two levels, 64 × 64 blocks, LRCP, one layer, one tile and style zero. Results
retain native exact reconstruction. Setup, IO and verification are outside the
operation clock; conversion, allocation, transform, entropy and assembly are
inside it. Processes are fresh, one operation each, with zero warmups.

Historical means are 2434.577962 and 2457.712319 ms, approximately +23.134 ms.
The 99% relative interval [+0.769086%, +1.131692%] supports a small slowdown
under that model, while leaving the +1% margin unresolved. Neither a larger-than-
margin regression nor non-regression is established. No new observation is
appended to those 40 pairs.

## Reconstruction and limits

The original executable paths are absent. A bounded inspection of the original
build root and retained treatment/binding directories found no executable or
linker-map copy. This is a statement about the inspected locations. Historical
section and symbol hashes were not recorded, so none can be compared with the
reconstruction. Source equality is insufficient to fill that gap.

Exactly one ordinary reconstruction per arm used the original build helper at
worker revision `0db3755…`, separate recovered codec checkouts, and the retained
configuration. The archive independently reproduced candidate tree
`259066112bda675e67a8d3eab3dbf9088d18fe91`. No source archive was overwritten.
The effective Rust options in both original verbose logs are `opt-level=3`,
`lto=thin` for the worker, `linker-plugin-lto` for libraries, `codegen-units=1`,
and `debuginfo=line-tables-only`. The latter was already part of the measured
ordinary profile; no debug, frame-pointer or emission flags were added.
Worker features are `classic-compare/default/emuella/openjpeg`; codec parallel
is enabled, SIMD and all diagnostic modes are disabled. The target is the
implicit host `x86_64-unknown-linux-gnu`. The toolchain is rustc 1.97.1
(`8bab26f4f68e0e26f0bb7960be334d5b520ea452`), LLVM 22.1.6.

The resolved worker lock hash is
`5cb1a2d7d5d098c347cc0ccdca0e52ca0315bb3190830ebd45d4c51f616788e8`.
Complete source inventories, locks, toolchain identity and recorded dynamic
library hashes match their respective original receipts. The existing worker
links OpenJPEG 2.5.4; no external-codec operation or implementation inspection
was performed. No shared library was copied.

The command receipt records intent; Cargo `-vv` logs and artifact feature/profile
records establish the observed compiler invocations. Both record no explicit
build environment overrides and no discovered Cargo configuration files.
This does not establish a complete inherited environment. The actual historical
linker executable/version was not retained, although the compiler invocation
and native library rpath were. Reconstruction source/output paths differ.

| Arm | Reconstructed whole-file SHA-256 | Exact historical executable? |
|---|---|---|
| Baseline | `1066f9d95250b32bdf0be4dcc31efcb5ba9951fb2d8b567bf25916507222b335` | No: whole-file mismatch |
| Candidate | `6a29754a59c8be33b4a0777f60cbf1a49479924a1bd331e132e15546ceda73ea` | No: whole-file mismatch |

A mismatch can include debug paths, metadata or layout and is not proof that
hot instructions differ from history. Without the original bytes it cannot be
assigned exclusively to those causes either. The new executable-section and
Emuella symbol comparison therefore describes reconstructed artifacts only.
There was no repeated build, preferred-layout selection or new timing pilot.

## Evidence separation and reproduction

The ordinary historical layer is the closed 40-pair endpoint. New ordinary
context, operation-scoped samples and instrumented stage timings are separate
layers and were explicitly left unperformed: zero preflights, zero of the
12 ordinary context calls, zero of the six sampled calls and zero of the four
stage-diagnostic calls. Total new corpus starts: **0 of the 24-call ceiling**,
including zero failures. No schedule was launched and unused slots cannot fund
a later round. No reservation was started and
no measurement environment has been changed; restoration is not applicable.
No PMU event, multiplexing, lost-sample or dynamic attribution claim follows
from the static record.

Retained original build receipts and `cargo.jsonl`/`cargo.stderr` remain in the
existing local evidence store named by the closed report. The new binding
package retains both reconstructed executables, resolved worker locks, verbose
build logs, receipts and an integrity manifest. It contains no corpus payloads
or copied shared libraries. Whole-file hashes in the factual extract can be
verified with `sha256sum`; compare each receipt's `codec` and `benchmark`
inventories, `lock_sha256`, `rustc`, `libraries`, diagnostic flags and observed
artifact features. Inspect the final `classic_compare_worker` invocation in
`cargo.stderr` for effective flags, separately from the command array.
The codec-owned analysis commands reconstruct the bounded static comparison
from the retained executables; they launch no corpus worker.

The diagnostic condition was not taken. Static comparison identifies changed
compiled work but cannot quantify its historical effect; a new profile of the
reconstructions would not recover the missing historical executable identity
or causally isolate the changes. There is no current ordinary reproduction or
non-reproduction claim, no sampling or instrumented build, and no diagnostic
acquisition tooling to merge. Mode/count/sampling/failure/restoration fixture
tests for a new acquisition runner are therefore not applicable. Existing
worker and reservation contracts remain unchanged. The result is a bounded
unresolved attribution, with no supported repair selected.
