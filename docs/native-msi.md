# Native eight-band U16 candidate evidence

Both complete RarePlanes MS16 inputs round-trip exactly through the public
Emuella encoder and both native workers. The candidate matrix completes **160
exact batches**: 40 newly admitted MSI encode/common-stream-decode batches plus
120 retained PAN16/RGB8/RGB16 batches. A separate retained-Emuella-stream journey
completes **80 exact decode batches**, including 20 MSI batches. No case is
unsupported, cropped, resized or precision-reduced.

These are measurements of committed candidates, not observations of future
merged revisions. Final qualification against merged owners belongs to the
workspace integration receipt. Earlier calibration and scalable-lossless
records remain unchanged historical evidence.

## Identities and scope

- [Candidate matrix](evidence/native-msi-candidate.json): benchmark
  `0c10522bd9e42d54c736942b0023dbc8f0e1b6dd`, codec
  `183c52a5ec2e69074f8d603b97e6bbe8ed7ef2b4`.
- [Build receipt](evidence/native-msi-candidate-build.json): exact harness and
  worker binary hashes. The full matrix retains compiler, dependency, source,
  build and machine identities. Testdata is
  `b5ae1702dea1045e8af304458869bd6f0a763df4`; prepared manifest SHA-256 is
  `dca8c0f74d100d41a6241ff62fec5861811ebbe24620759cd7416c104693a7f9`.
- [Separate stream verification](evidence/native-msi-candidate-verification.json)
  binds all eight retained Emuella streams, full references and both decoders.
- [Allocation observations](evidence/native-msi-candidate-allocation.json) use
  three project-authored inputs, the same codec revision and a separately
  identified instrumented executable. They contain no RarePlanes pixels.

Magadino (`30_104001002394E000-MS16`) is 1332 × 720 × 8: 959,040 spatial pixels
and 7,672,320 component samples. Apple Valley (`47_104001001D2C7A00-MS16`) is
1663 × 1763 × 8: 2,931,869 spatial pixels and 23,454,952 component samples.
Prepared band positions 1–8 remain ordered native components 0–7, preserving
every unsigned 16-bit value. Band names, wavelengths and display interpretation
remain application metadata.

The [codec-owned profile](https://github.com/emuella/emuella-j2k/blob/183c52a5ec2e69074f8d603b97e6bbe8ed7ef2b4/docs/native-eight-components.md)
uses `ColorModel::Unknown`, U16_LE and either planar or interleaved storage;
workers use packed interleaved storage. Output is one raw Part 1 full-image tile,
one layer, LRCP, reversible 5/3 with two decompositions, unit sampling, zero
origins and no MCT. The benchmark admits one tile-part. Native decode requests
all eight components at full resolution. Axes are 4–32768 with at most 32 Mi
spatial pixels (256 Mi component samples); codec defaults separately allow
4 GiB working admission and 1 GiB output capacity. Geometry admission does not
guarantee an arbitrary output budget or available memory. Eight-band U8, signed
or mixed precision, lossy, HT, spectral transforms, containers, selective output
and heterogeneous grids are outside this qualification. Broader existing codec
decode behaviour is unchanged.

## Timing, size and process memory

Each observation is the mean of five fresh worker processes, each with one
measured operation, one worker thread and no timed warmup. Input loading and
verification precede/follow the native operation timer. Decode includes native
layout conversion; encode verification is outside encode timing. RSS is the
maximum whole-worker `VmHWM`, including setup and verification. Measurements
come from one Linux x86-64 host with an AMD Ryzen 9 9950X3D; they are descriptive
observations, without a population-wide speed or compression verdict.

One spatial pixel comprises all eight bands at one position; one component
sample is one scalar band value. M in the throughput columns means 1,000,000;
MiB means 1,048,576 bytes. JSON retains nanoseconds, bytes and unrounded values.
Decode below uses the independently generated OpenJPEG common stream. The 80
separate Emuella-stream verification batches are excluded from these timings.

| Input | Worker | Operation | Mean time (s) | M spatial pixels/s | M component samples/s | Peak worker RSS (MiB) |
|---|---|---|---:|---:|---:|---:|
| Magadino | Emuella | Encode | 1.329 | 0.721 | 5.772 | 120.1 |
| Magadino | Emuella | Decode | 0.941 | 1.019 | 8.156 | 100.9 |
| Magadino | OpenJPEG | Encode | 0.776 | 1.236 | 9.891 | 178.3 |
| Magadino | OpenJPEG | Decode | 0.701 | 1.368 | 10.947 | 107.4 |
| Apple Valley | Emuella | Encode | 4.058 | 0.722 | 5.780 | 356.0 |
| Apple Valley | Emuella | Decode | 3.116 | 0.941 | 7.528 | 254.4 |
| Apple Valley | OpenJPEG | Encode | 2.566 | 1.143 | 9.140 | 501.3 |
| Apple Valley | OpenJPEG | Decode | 2.319 | 1.265 | 10.116 | 326.1 |

Rates count the complete encoded stream, including headers. Raw storage is
16 bytes per spatial pixel. Both MSI encoders disable MCT; the retained RGB
profiles still differ by encoder, so their observations do not imply identical
encoding policies.

| Input | Encoder | Encoded bytes | Bits/spatial pixel | Bits/component sample | Raw/encoded ratio |
|---|---|---:|---:|---:|---:|
| Magadino | Emuella | 7,845,403 | 65.443802 | 8.180475 | 1.955877 |
| Magadino | OpenJPEG | 7,845,469 | 65.444353 | 8.180544 | 1.955860 |
| Apple Valley | Emuella | 27,306,192 | 74.508628 | 9.313578 | 1.717922 |
| Apple Valley | OpenJPEG | 27,306,253 | 74.508794 | 9.313599 | 1.717918 |

The common-stream byte lengths equal the corresponding OpenJPEG encode sizes
in this observation. Exact hashes are retained separately; equality of length
alone is not used as a correctness test.

## Independent verification and retained compatibility

Installed OpenJPEG `opj_dump` 2.5.4 inspects both MSI common streams and both
retained Emuella MSI streams outside timing. All four inspections identify eight
ordered unsigned 16-bit components, native dimensions, unit sampling, reversible
D2, one full-image tile, LRCP, one layer and no MCT. The factual summaries retain
binary/version identity, stream hashes and raw dump/help hashes. Dumps expose
main-header defaults: worker admission separately rejects coding overrides and
unsupported envelopes. Full-reference decoding by both workers establishes
sample exactness, including band order. Raw images, derivatives, streams, logs
and detailed runs stay in the authorised testdata store.

The [retained comparison](evidence/native-msi-candidate-comparison.json) matches
all 24 prior grey/RGB observations to this candidate using the same harness,
prepared inputs, settings and protocol. All encoded sizes remain unchanged.
Mean-time changes range from −3.898% to +3.237%; whole-worker peak-RSS changes
range from −0.962% to +1.283%. Every absolute change is below the 5%
investigation threshold. These are descriptive retained-run comparisons, not
paired statistical equivalence or improvement verdicts. The comparison retains
both summary hashes, raw run hashes, original values and exact changes; its
baseline is the final scalable-lossless matrix, not the earlier provisional
checkpoint with unsupported Apple Valley encodes.

## Separate authored allocation observations

The codec diagnostic excludes caller sample storage and later decode
verification. It reports requested encoder peak including output and old/new
reallocation overlap, retained output capacity, and checked working allowance
separately. The peak is an upper bound on additional working allocations;
subtracting final output capacity from a peak at another time would be invalid.
Allocator bookkeeping, stacks and mapped libraries are outside requested bytes.
Instrumented durations are not headline timing evidence.

| Authored geometry | Layout | Requested encoder peak (bytes) | Retained output capacity (bytes) | Working allowance (bytes) | Encoded bytes |
|---|---|---:|---:|---:|---:|
| 1332 × 720 × 8 | Interleaved | 55,707,600 | 16,640,000 | 2,191,230,576 | 16,360,498 |
| 1663 × 1763 × 8 | Interleaved | 194,067,504 | 66,789,376 | 2,269,832,772 | 50,004,830 |
| 1663 × 1763 × 8 | Planar | 194,067,504 | 66,789,376 | 2,269,832,772 | 50,004,830 |

All three authored decodes are exact. Apple Valley-sized planar and interleaved
probes have identical input/output hashes, encoded lengths, retained capacities
and requested encoder peaks. Their full-range xorshift samples are distinct
from the RarePlanes inputs, so their sizes and allocation peaks cannot be
substituted for real-image measurements. The allocation model and caller-buffer
failure guarantees remain codec-owned.

Reproduce the real journeys using the [calibration instructions](rareplanes-calibration.md)
and a clean committed benchmark checkout with workers built from the explicitly
selected codec revision. Both runners require the installed `opj_dump` and new
output names inside the approved persistent store. Candidate receipts remain
bound to the revisions above when final merged-owner qualification is recorded.
