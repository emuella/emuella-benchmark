# SpaceNet classic baseline results

All 32 classic lossless streams reconstructed exactly through the unchanged
native facade and independent OpenJPEG 2.5.4 decoder. All 240 development timing
batches passed. Four Khartoum chips received source validation and untimed
lossless exactness only; no reserved timing, quality or lossy evidence was collected.

The [factual record](evidence/spacenet-classic.json) binds the experiment, raw
batch and preparation digests, exact build identities, source-view freeze and
per-AOI aggregates. The [recipe](spacenet-classic.md) defines reproduction.
Protected source pixels, generated streams and independent decoded pixels remain
in the authorised SpaceNet store; this public record contains factual metadata.

Each row below pools descriptive observations from four 1300×1300 RGB16 chips
and five fresh processes per chip. Means and ranges are milliseconds; the range
covers all 20 observed batches in that row and is not an uncertainty interval.
The styles are separate absolute profiles and carry no comparative ranking.

| AOI | Style | Operation | Mean ms | Observed range ms |
|---|---|---|---:|---:|
| Vegas | 0 | encode | 1110.705 | 635.305–1391.376 |
| Vegas | 0 | decode | 698.667 | 367.490–830.022 |
| Vegas | 1 | encode | 768.020 | 433.936–903.240 |
| Vegas | 1 | decode | 370.325 | 196.540–470.252 |
| Paris | 0 | encode | 838.846 | 197.447–1248.972 |
| Paris | 0 | decode | 538.611 | 116.680–721.061 |
| Paris | 1 | encode | 643.311 | 146.115–873.802 |
| Paris | 1 | decode | 376.039 | 102.187–562.783 |
| Shanghai | 0 | encode | 750.270 | 107.476–1118.370 |
| Shanghai | 0 | decode | 455.127 | 66.388–685.452 |
| Shanghai | 1 | encode | 539.689 | 86.905–795.076 |
| Shanghai | 1 | decode | 305.304 | 50.682–425.360 |

Classic D2 uses style 0 or bypass style 1 with reversible colour transform,
one worker, zero warmups and direct/global `facade_operation` execution. The
unchanged limits are 768 MiB working and 64 MiB output. CPU 0 on an AMD Ryzen 9
9950X3D used the powersave governor. The process timeout was 120 seconds; the
4 GiB address-space cap and RSS ceiling are execution controls, without a
codec-owner memory-admission qualification.

Encode/decode times include facade output/layout work. Input loading, hashing
and every-sample reconstruction verification are outside the clock. Whole-process
RSS includes those operations and is recorded separately. Component Msamples/s,
actual complete stream bytes and raw-storage/stream-byte ratios are retained in
the factual record. Development stream sizes ranged from 366,271 to 3,614,142
bytes, raw-storage ratios from 2.81 to 27.68 and observed process RSS from 37.72
to 55.05 MiB. No retries, exclusions, alternate rates or style selection were used.

The measured benchmark revision is
`c17058ea8d901e500b157381e3f9818014629dcd`; codec revision is
`08fd8dfc80c3475209680032ce2c097409716246`
(tree `fd6be6f310996223fa69551829b30f3865748f95`).
The bound build uses perf, parallel support and no SIMD; its executable SHA-256
is `e9d37f3b30186de508149dddb1445859b4efa57fa2d8ea8f60d6e2198a9a6546`.
The independent decoder executable and complete runtime-library inventory are
bound in the retained experiment manifest. Later documentation and test-only
commits do not change the measured worker or frozen runner bytes.
