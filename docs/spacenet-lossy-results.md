# SpaceNet PS-RGB16 single lossy result

At the sole frozen 12-total-spatial-bpp point, Vegas and Shanghai pass the
regional display gates; Paris fails 16 of its 36 band/scale/stretch cells.
All three pass the unchanged payload, descriptor and manifest byte ceilings.
The Paris source remains in the corpus. No gate, stretch, input or rate changed
in response, and no codec policy was selected.

| Frozen development chip | Payload bytes | Descriptor / manifest bytes | Worst display RMSE / p99 | Failed cells |
|---|---:|---:|---:|---:|
| Vegas img1454 | 2,535,275 | 8,677 / 1,618 | 1.070448 / 3 | 0/36 |
| Paris img235 | 2,535,369 | 8,953 / 1,617 | 11.407768 / 32 | 16/36 |
| Shanghai img1196 | 2,535,412 | 8,916 / 1,621 | 2.333088 / 6 | 0/36 |

Each complete 1300×1300×3 UInt16 chip contains 10,140,000 raw sample-storage
bytes. The target is 12 bits per spatial pixel, or 4 bits per component sample;
it is not 12 bits per component. All three payload ceilings are 2,536,272 bytes.
Masks are separate source-exact corpus derivatives, not part of these
quality-only indexed representations; no full representation eligibility follows.

| Chip | Worst source-unit RMSE / p99 / absolute error | Preparation wall seconds | Preparation peak RSS bytes |
|---|---:|---:|---:|
| Vegas img1454 | 4.229000 / 11 / 21 | 1.115099 | 58,064,896 |
| Paris img235 | 1.837968 / 5 / 11 | 1.115277 | 59,576,320 |
| Shanghai img1196 | 3.298818 / 9 / 15 | 1.215443 | 59,654,144 |

The narrow source-derived Paris stretch makes small native errors large in
U8 display units. This explains the distinction between the two reported error
spaces; it does not excuse the failed display gate or prove visual suitability.
The source-only noisy/striped appearance was recorded before codec results.
All delivered pixels, including unmasked black padding, retain supplier validity.

The [complete factual record](evidence/spacenet-lossy.json) retains every frozen
view's source errors and per-band ANY/ALL/PARTIAL/all-pixel display populations,
actual bytes, absolute preparation measurements, receipt hashes and identities.
The [recipe](spacenet-lossy.md) supplies opt-in commands and exact boundaries.

The measured benchmark revision is `ab00f93d84061cad394536b8fea48b309535791d`,
using unchanged codec `08fd8dfc80c3475209680032ce2c097409716246` and Polyorama
`dc7d3d6a89de0f070eade59bf7da7522de8b57f8` tool sources. Three complete-chip
encodes use indexed 512 tiles, D6, irreversible 9/7, no MCT, one worker and no
rate search. Nine predeclared 256-square source views use scales 1/4 and frozen
2/98-percentile and full-storage stretches. Gates remain per-band U8-display
RMSE <=3 and p99 <=12 on original-source ANY-valid populations.

Preparation wall/RSS include tool startup, source IO/hashing and encoding; they
are separate from classic facade-operation timings. All three finish below the
1800-second and 4 GiB execution guards, which are not a newly qualified memory
or latency target. Exact applied profiles, logical resource metrics, descriptors
and payload hashes remain in persistent receipts.

Khartoum received no lossy or performance evaluation. No full-source runtime,
independent indexed-decoder, browser, recovery, human, viewer-acceptance or
analytical-suitability claim is made. These three regional results do not show
population representativeness or supersede any RarePlanes result or failure.
