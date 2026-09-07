# Contributing

Use Australian English in human-facing text and preserve established APIs and
external terminology. Keep codec implementation in its owning repository and
corpus selection, integrity and rights in the catalogue owner.

Run `sh scripts/check.sh` before submitting a change. Add focused behavioural
coverage when changing comparability, correctness, worker failure handling or
schema admission. Keep `Cargo.lock` committed for reproducible CLI builds.
Increment the contract schema version for incompatible wire changes; reject
unknown versions explicitly. Workers must never silently fall back to different
settings, measurement boundaries or output semantics.

Use independent worker executables, project-authored inputs and isolated output
directories for probes. Keep source, binary, input and environment identities
with the resulting evidence. Do not commit generated image payloads, installed
external binaries, private machine paths or protected data. Runtime provenance
references record identity and do not confer rights or initiate acquisition.

Timing claims need completed coverage, matched semantics and uncertainty.
Within-process repeats are correlated; independent batches are the inferential
unit. Failed or unsupported batches remain visible and prevent a global speedup
claim. Diagnostic runs are separate from ordinary timing evidence.
