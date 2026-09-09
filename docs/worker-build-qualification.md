# Unchanged-codec worker build qualification

`scripts/qualify-worker-builds.py` compares four freshly compiled Emuella workers
against the historical release build with optional SIMD disabled. This is a
bounded satellite-profile build experiment; it does not select new encoding
settings or claim a codec algorithm improvement.

Prepare the four builds with `scripts/build-workers.py`: default release,
`--profile release --simd`, `--profile perf`, and `--profile perf --simd`. Use the
same clean local `--emuella-source` at revision
`1c1a7fbc583d69c6d57bfd1da4248aa6fae071cc` for every build, so the sidecars record
the source tree. Use fresh target directories to retain the compiler commands.
Commit the benchmark candidate before qualification. Its build input hashes must
match every worker build. The runner checks requested profiles, actual codec SIMD
and parallel features, identical source, resolved lock, toolchain and environment.
It rejects cached codec artefacts, Cargo configuration files, compiler wrappers,
Rust flags and profile environment overrides. This narrow admission rule belongs
to this frozen experiment; the general build helper records those overrides.

Select one or more complete acquisitions explicitly. The source lock and prepared
manifest remain testdata-owned. Admission uses the existing RarePlanes selection
and input validation, including SHA-256 and byte checks. Every selected acquisition
retains PAN16, RGB8, MS16 and RGB16 in that order, including unsupported outcomes.
No asset acquisition or preparation occurs. Use the existing
`inputs/common-codestreams.json` from a completed RarePlanes calibration for
common decode input. Its stream bytes, digests and recorded OpenJPEG arguments
must match the frozen full-image, one-tile, LRCP, one-layer, D2, lossless, no-MCT,
one-thread profile. The runner independently decodes those streams against the
prepared references. Preserve the original selection decision separately when
reserving holdout acquisitions.

```sh
python3 scripts/qualify-worker-builds.py \
  --benchmark /path/to/emuella-benchmark \
  --release /path/to/release-build \
  --release-simd /path/to/release-simd-build \
  --perf /path/to/perf-build \
  --perf-simd /path/to/perf-simd-build \
  --prepared /approved/store/prepared/prepared.json \
  --selection /path/to/catalogue/selection.source-lock.json \
  --common-streams /approved/store/prior-matrix/inputs/common-codestreams.json \
  --bundle acquisition_id \
  --store /approved/store \
  --output /approved/store/new-build-qualification
```

All prepared samples, common streams, retained codestreams and output must stay
inside the approved store. Output must be a new direct child; existing evidence
is never overwritten. The selection lock, worker binaries and compiler evidence
may remain in their existing source/build locations. The report contains local
paths and complete build provenance; it is store-local evidence, not a sanitised
publication artefact. Build sidecars and compiler logs are copied to `evidence/`
so later build-scratch cleanup preserves their contents.

The runner makes three baseline/candidate encode pairs and three decode pairs.
Each pair uses the existing harness's five AB/BA rounds, one timed sample per
fresh worker process, no warmup, codec-operation boundary and warm input policy.
The timeout is 120 seconds per worker batch. Encoding preserves the existing RGB
reversible colour transform policy and native no-MCT eight-band U16 policy.
Decoding uses the same no-MCT common streams for every variant. All raw requests,
responses, logs, batch outcomes, machine identities and conservative comparisons
remain in the harness pair directories.

Each variant separately exports one exact public-encoder codestream per admitted
asset. Every retained stream is decoded through that Emuella variant and the
independent baseline OpenJPEG worker against the complete prepared reference.
These verification runs preserve the harness minimum of five fresh processes
per case, with the ordinary identity/correctness validation. Their time and RSS observations are
excluded from headline timing. Export failures and unsupported results remain in
`exports/<variant>/exports.json`; all stream hashes are compared with baseline.

`worker-build-qualification.json` separates the following evidence:

- Coverage and existing per-case/global harness verdicts, including uncertainty.
- Per-round baseline/candidate time ratios for complete exact cases on both
  sides. Encode cases additionally require matching exported bytes and both
  decoders' verification; decode cases require independent common-stream
  verification. Newly successful cases contribute coverage only.
- An equally weighted geometric mean of per-case geometric mean speedups.
  Values above one favour the candidate. This descriptive aggregate has no
  confidence interval and does not override an inconclusive harness verdict.
- Total component samples divided by total measured time for each side, using
  the same eligible cases and all their timed samples. This weights acquisitions
  and products by their actual sample counts and elapsed time, unlike the
  equally weighted case aggregate. Per-acquisition results retain that distinction.

Source revision, script/helper hashes, selection, prepared samples, common
streams, worker definitions, binaries and bound sidecars are checked before and
after execution. Exported stream digests are checked again at completion.
`complete` means all six comparisons were retained without execution, identity,
byte-consistency or retained-stream verification failures; consistently
unsupported cases can still be present. It does not mean universal support or a
performance improvement. `builds_qualified_on_common_support` additionally needs
at least one qualified same-success case in every pair. No same-success cases
means `timing_claims_admitted` is false, even for completed observations. The
runner never makes a global speed claim across unsupported coverage. A failure
also makes `timing_claims_admitted` false and
leaves any descriptive calculations provisional. Exit status is zero for a
complete qualification, four for retained incomplete/failed evidence and one for
admission errors. Timing regressions or uncertainty are observations, not runner
execution failures. An interrupted process can leave incomplete evidence and
must be rerun into a new output directory.
