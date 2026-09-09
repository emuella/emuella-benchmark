# Scalable full-image lossless evidence

The full six-case, five-round RarePlanes candidate matrix completed **120 exact
batches**, replacing the previous ten Emuella Apple Valley encode rejections.
The primary profile remains raw single-tile Part 1 lossless D2, LRCP, one layer
and one worker thread. Neither MS16 input is submitted. No crop, resizing,
precision reduction, colour change or external encoder fallback is used.

This record separates the pre-landing candidate matrix from merged-codec
allocation qualification. Terminal system integration records the additional
rerun against merged benchmark and codec revisions; these candidate facts are
not relabelled as observations of a future source revision.

## Identities and method

- [Candidate matrix](evidence/scalable-lossless-candidate.json): benchmark
  `1c6215090d3c1ad191b9cd332f72e8f62e56c331`, codec
  `39dc6b2d4d47da99a76d655bbd1947d98ed8a607`. The codec landed in
  [PR 99](https://github.com/emuella/emuella-j2k/pull/99) as
  `68c850906fc0592b257b47d83edbd8c966e8de98`, with identical tree
  `4119597ba027e79cb7c6a97703c36431d486e418`.
- [Scaling observations](evidence/scalable-lossless-scaling.json): compiled from
  that merged codec revision, with exact source, build, executable and authored
  input/output identities. All 21 probes reconstruct exactly.
- [Comparison observations](evidence/scalable-lossless-comparison.json): retained
  final baseline summary `981c18b2424daa20d9499070e669b2e9361e9355b2a25c3814025d18f953d694`
  and a fresh 20-batch old-codec remeasurement. Harness binary identity matches.
- Testdata remains `b5ae1702dea1045e8af304458869bd6f0a763df4`; prepared manifest
  SHA-256 is `dca8c0f74d100d41a6241ff62fec5861811ebbe24620759cd7416c104693a7f9`.
  All eight source objects were rechecked against the unchanged source lock.

See [the calibration method](rareplanes-calibration.md) for reproduction, exact
input/profile/build retention and the separate retained-Emuella-stream decoder
journey. The primary decode matrix uses independent OpenJPEG-generated common
streams. Independent decoding of new Emuella streams is separate evidence;
the full Apple Valley streams passed Emuella and ten OpenJPEG candidate batches.
Raw imagery, derivatives and detailed runtime records remain in the authorised
persistent testdata store. Factual JSON contains no source pixel payloads.

## Candidate matrix observations

Times are means of five fresh-process batches, in seconds. RSS is the maximum
whole encode-worker process value in MiB, including setup and verification.
The decode column refers to the independent common stream, not the encoder's
own output. Full JSON also retains all OpenJPEG measurements and raw run hashes.

| Input | Emuella encode (s) | Common-stream decode (s) | Emuella encoded bytes | Encode-worker RSS (MiB) |
|---|---:|---:|---:|---:|
| Magadino-PAN16 | 2.470 | 1.828 | 15,897,166 | 197.2 |
| Magadino-RGB8 | 2.652 | 2.230 | 11,667,870 | 456.5 |
| Magadino-RGB16 | 0.467 | 0.336 | 2,689,386 | 55.4 |
| Apple Valley-PAN16 | 7.586 | 5.659 | 50,206,588 | 591.2 |
| Apple Valley-RGB8 | 10.828 | 9.382 | 51,668,288 | 1400.0 |
| Apple Valley-RGB16 | 1.444 | 1.127 | 9,492,982 | 127.2 |

All four previously supported Emuella cases retain their compressed lengths
and exact reconstruction. Their mean encode times are within 1.1% of the fresh
baseline; no previously supported matrix mean time changed by more than the
5% investigation threshold against the retained baseline. These descriptive
ratios are not statistical improvement verdicts. No speed improvement or
universal codec ranking is claimed. RGB MCT policies still differ by encoder.

## Memory accounting and scaling

The [codec contract](https://github.com/emuella/emuella-j2k/blob/68c850906fc0592b257b47d83edbd8c966e8de98/docs/scalable-lossless.md)
owns the checked bound, additive admission APIs and geometry restrictions.
Defaults allow 4 GiB conservative working bytes and 1 GiB output capacity.
Working admission occurs before coefficient allocation; actual compressed
output can still exceed its separate limit during encoding.

The authored diagnostic resets after caller sample storage is prepared, measures
encoding before decode verification, and reports total requested encoder peak,
retained output capacity and its checked working bound separately. Its total
peak includes output and conservative old/new reallocation overlap, so it is an
upper bound on additional working memory, not an additional-only peak. It does
not subtract final output capacity from a peak observed at a different time.
Allocator bookkeeping, stacks and mapped libraries are outside requested bytes.
Process RSS additionally includes input and verification. Instrumented probe
times may overlap diagnostic builds/probes and are not headline speed evidence.

The following values are total requested encoder peaks in MiB. Inputs use the
full storage range and a fixed authored xorshift generator. Capacity growth
causes steps, while coefficients and local packet work scale with sample count.

| Dimensions | Pixels | Grey U8 | Grey U16 | RGB U8 | RGB U16 |
|---|---:|---:|---:|---:|---:|
| 1025 × 1027 | 1,052,675 | 6.9 | 10.0 | 17.1 | 23.4 |
| 2049 × 2051 | 4,202,499 | 27.3 | 39.9 | 68.5 | 93.6 |
| 4095 × 4097 | 16,777,215 | 109.2 | 159.2 | 273.3 | 373.7 |
| 6650 × 7054 | 46,909,100 | 268.9 | 369.6 | 861.4 | 1264.7 |
| 8001 × 8003 | 64,032,003 | 424.1 | 623.4 | 1059.6 | 1458.9 |

The largest 8001 × 8003 RGB16 probe has 64,032,003 pixels, above Apple Valley's
46,909,100. Its total requested encoder peak is 1,529,759,404 bytes, within the
3,116,802,888-byte conservative working bound; retained output capacity is
507,379,712 bytes and encoded length 412,052,044 bytes. The planar repeat has
identical stream hash, length, capacity and encoder allocation peak. Caller
storage is excluded in both layouts; the planar diagnostic keeps an additional
caller-owned interleaved comparison copy, which is identified in its record.
Large probes are opt-in. Ordinary codec tests cover odd and processing-boundary
sizes, layouts, legacy long/thin shapes, checked arithmetic and budget rejection.

## Investigated RSS increase

Magadino RGB16's candidate encode-worker RSS rises by about 9 MiB (19%), while
the other three supported cases fall by roughly 7–24%. The
[phase diagnostic](evidence/scalable-lossless-rss.json) compares actual worker
snapshots with old and merged codecs in three paired fresh-process observations
and a separate allocator-trim control. All eight executions are exact.

Incremental encoder requested peak, including output, falls from 22,286,099 to
19,130,632 bytes. Retained codestream capacity rises from 2,689,386 to 5,050,880
bytes, while encoded length stays 2,689,386. The 2,361,494-byte capacity increase
exactly matches the requested-live difference during verification's U16-to-i32
conversion. Requested live bytes after verification are identical (28,788,187),
and the whole-journey requested peak differs by only 27,501 bytes. Higher RSS
appears during verification and remains after temporaries are freed, supporting
allocator reuse/retention as the explanation rather than retained live leakage.
The trim control does not establish a production remedy; no trimming is added.

Retain this bounded output-capacity and verification-RSS tradeoff. It is not a
claim that process RSS always decreases. Exact instrumentation and a verified
reproduction recipe persist beside the protected runtime records; their
retention manifest SHA-256 is
`ee5db7483b8687fbf67d8e777111148e5da8f78363267c0a20945eab08b4b848`.
The diagnosis is host/allocator-specific and its instrumented times are excluded
from headline comparisons.

The larger route remains sequential, including parallel builds. JP2, tiling,
D0/D1, HT, lossy and eight-component MSI expansion are outside this work package;
their prior admission rules remain in force.
