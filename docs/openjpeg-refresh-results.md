# Refreshed Emuella–OpenJPEG results

For the subsequent packed encoder qualification, see the
[separate results](classic-encoder-kernel-results.md). The measurements below
retain their original source and build identities.

The matched comparison completed on 13 September 2026. OpenJPEG was faster in
all 36 encoding comparisons under the conservative 99% interval / 5% practical
gate. Decode was closer: 28 slower Emuella comparisons, 42 inconclusive and two
equivalent. No comparison established an Emuella speed advantage under that gate.
All 4,320 timed invocations and 36 preparations reconstructed exactly.

## Descriptive timing summary

Ratios below are Emuella time / OpenJPEG time, using the equally weighted
geometric mean of nine per-image ratios. Below 1 favours Emuella. These aggregate
numbers are descriptive; they do not carry a cohort-wide confidence claim.

| Profile | Workers / CPU budget | Encode E/O | Decode OpenJPEG stream E/O | Decode Emuella stream E/O |
|---|---:|---:|---:|---:|
| Style 0 | 1 | 1.653 | 1.200 | 1.191 |
| Style 0 | 8 | 2.049 | 1.154 | 1.162 |
| Bypass | 1 | 1.632 | 1.109 | 1.115 |
| Bypass | 8 | 2.007 | 1.107 | 1.109 |

Both codecs benefit from their faster operating configurations; the earlier
Emuella-only optimisation ratios do not establish a cross-codec advantage.
Matching bypass and worker budgets preserves a material encoding gap.

## Concrete example: Mansfield, bypass, eight workers

Means are milliseconds per full-image operation. Decode below uses the same
OpenJPEG stream for both decoders; the factual record also contains both
decoders on the Emuella stream.

| Product | OpenJPEG encode ms | Emuella encode ms | OpenJPEG decode ms | Emuella decode ms |
|---|---:|---:|---:|---:|
| PAN16 | 133.706 | 239.524 | 104.896 | 122.447 |
| RGB16 | 25.380 | 47.164 | 19.641 | 18.345 |
| MS16 | 68.417 | 126.066 | 52.299 | 56.284 |
| RGB8 | 241.690 | 529.065 | 204.190 | 246.860 |

Some mean decode values favour Emuella, such as this RGB16 example, but they
remain inconclusive under the fixed gate. Means alone are not verdicts.

## Size, memory and coverage

Across all 18 image/style encodings, complete codestream sizes differ by less
than 0.002% between codecs. This compares raw J2K bytes with matching RGB RCT,
not source TIFF sizes or the historical unmatched-MCT encoders.

The largest measured worker peak for each codec occurred on Boca Raton RGB8
bypass/eight-worker encoding: **531.48 MiB Emuella**, **976.50 MiB OpenJPEG**.
These process high-water marks include setup and verification, and are separate
from codec allocation requirements or production application memory. Every
individual comparison retains its peak RSS and whole-process CPU time.

The fixed cohort contains nine full products: Mansfield and Boca Raton
PAN16/RGB16/eight-band MS16/RGB8, plus Tok RGB8. It is not a refresh of the
48-product admission matrix, a representative population or a universal ranking.
No failed observations, retries, warmups or outlier exclusions enter the result.

## Source and reproducibility

- Measured codec: `08fd8dfc80c3475209680032ce2c097409716246`.
- Measured benchmark runner: `9e7385fe048cd60d28cf09d1293830c6ec8affc1`.
- Analysis producer: `a2f25ab309fc565e0061abaf84ff94f0545194d4`.
- OpenJPEG: installed **2.5.4**; Rust **rustc 1.97.1 (8bab26f4f 2026-07-14)**.
- Host: AMD Ryzen 9 9950X3D, powersave governor. One-worker pairs use CPU 0; eight-worker pairs use CPUs 0–7.
- Worker build: perf profile, optimisation level 3, ThinLTO, one codegen unit, parallel enabled, optional SIMD disabled.
- Twenty alternating fresh-process codec pairs per contrast, one measured operation, zero warmups, 120-second process timeout.
- Raw lossless Part 1 D2, one full-image tile and layer, LRCP, 64-square blocks, default precincts; matching style and RGB RCT.

The [protocol and commands](openjpeg-refresh.md) define the timed interleaved-byte
to owned-output boundary, resource limits, exactness and uncertainty. The
[factual record](evidence/openjpeg-refresh.json) retains all 108 comparisons,
4,320 individual operation times, intervals, input/build identities, compressed
sizes and process metrics. `scripts/render-openjpeg-refresh.py` renders that
record as a portable filterable HTML report.

Later report-only additions do not relabel the original measured binary.
The original exact-candidate probe and final candidate/merged-owner probes
remain separately identified in PR #10 delivery evidence. Raw requests,
responses, logs, streams and build receipts remain in the authorised store.

RarePlanes Dataset, June 2020: J. Shermeyer, T. Hossler, A. Van Etten, D. Hogan,
R. Lewis and D. Kim; In-Q-Tel – CosmiQ Works and AI.Reverie; CC BY-SA 4.0.
Only factual measurements and identities are included here; the original notice,
source lineage and new lossless streams remain in the approved store.
