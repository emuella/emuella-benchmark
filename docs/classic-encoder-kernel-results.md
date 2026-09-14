# Classic packed encoder qualification

The frozen packed encoder passed the predeclared promotion gates on 14 September
2026. Against a freshly built unchanged Emuella reference, all eighteen
one-worker RarePlanes encode comparisons improved under the conservative 99%
interval / 5% practical gate. Mean time reductions were 30–40% for style 0 and
31–49% for bypass. Every predeclared Boca Raton primary case improved, including
PAN16 and eight-band MS16 in both styles. At eight workers, seventeen of eighteen
encode comparisons improved; Boca Raton RGB8 bypass remained inconclusive.

All twenty-four separate SpaceNet development comparisons improved. No practical
regression against the unchanged reference was observed. Targeted decoder checks
were equivalent in all six one-worker comparisons and inconclusive in all six
eight-worker comparisons. Those uncertain results are not equivalence or a
cohort-wide non-regression proof. The selected backend was not retuned after
confirmation. Immediate OpenJPEG parity was not a promotion condition.

The [frozen protocol](classic-encoder-kernel.md) defines the role assignments,
finite development budgets, primary cases, limits and gates. The
[factual reference/SpaceNet record](evidence/classic-encoder-kernel.json) retains
all individual times, per-case intervals, compressed sizes, input/build hashes
and separate allocation observations. The
[matched external record](evidence/classic-encoder-kernel-openjpeg.json) retains
all 108 OpenJPEG comparisons. Historical refresh timings keep their original
identities; none was relabelled as this fresh reference.

## Mechanism and selection

The project-authored backend uses packed directional significance state and
ordered four-row/sixteen-column bitboards. Live significance masks preserve
scan order with a consumed-position mask; refinement skips ineligible positions,
cleanup retains aggregation and sign decisions, and visitation reset touches
at most 64 word groups. MQ/raw coding, decoder execution, transforms, packet
assembly, scheduling, APIs, limits and build profiles are unchanged. The codec
retains independent reference preparation/traversal and explicit fallback for
styles other than 0/1 or block axes exceeding 64.

Encode-only baseline sampling attributed 14.73–22.42% of cycles to standalone
neighbourhood queries. Inlined MQ remains substantial and is not labelled state
cost. Two bounded development variants were screened. Variant 2's six-case
geometric candidate/reference ratio was 0.62373 versus variant 1's 0.68837;
RGB8 was 1.4–1.9% slower than variant 1, within the predeclared 5% guard.
Both three-round screens are descriptive, not confidence or promotion results.
All four authored replay pairs per variant matched 732,408 bytes including pass,
missing-plane and segment metadata. The retained backend was frozen before
confirmation; no third variant or build sweep was used.

## Full-image reference treatment

Mean milliseconds per facade operation, reference → packed. Intervals are
packed/reference minus one, at 99% per comparison; negative favours packed.
All rows use twenty independent fresh-process pairs. `I` means improved,
`E` equivalent, and `?` inconclusive under the predeclared 5% practical gate.
The complete factual record retains every individual time and process metric.

| Product | Style | One worker ms | 99% change / verdict | Eight workers ms | 99% change / verdict | Bytes |
|---|---|---:|---|---:|---|---:|
| Mansfield PAN16 | 0 | 2126.398 → 1369.716 | [-36.3%, -34.9%] I | 359.376 → 243.083 | [-38.0%, -26.2%] I | 13,860,814 |
| Mansfield PAN16 | bypass | 1302.303 → 757.307 | [-43.2%, -40.5%] I | 236.091 → 161.549 | [-38.1%, -24.3%] I | 13,801,207 |
| Mansfield RGB16 | 0 | 403.940 → 252.639 | [-38.1%, -36.8%] I | 74.056 → 49.646 | [-42.0%, -22.7%] I | 2,480,209 |
| Mansfield RGB16 | bypass | 241.790 → 133.647 | [-45.5%, -43.9%] I | 46.156 → 30.207 | [-37.0%, -32.0%] I | 2,467,937 |
| Mansfield MS16 | 0 | 1133.189 → 713.347 | [-37.8%, -36.3%] I | 204.959 → 133.413 | [-41.6%, -27.4%] I | 7,414,382 |
| Mansfield MS16 | bypass | 658.979 → 359.367 | [-46.3%, -44.6%] I | 124.827 → 78.360 | [-39.5%, -34.8%] I | 7,399,817 |
| Mansfield RGB8 | 0 | 2676.228 → 1818.107 | [-33.3%, -30.8%] I | 584.196 → 437.908 | [-29.9%, -19.8%] I | 12,399,691 |
| Mansfield RGB8 | bypass | 2451.613 → 1645.612 | [-34.0%, -31.7%] I | 543.714 → 417.627 | [-28.7%, -17.3%] I | 12,445,920 |
| Boca Raton PAN16 | 0 | 2664.432 → 1708.521 | [-37.4%, -34.4%] I | 501.193 → 371.404 | [-35.6%, -14.9%] I | 16,469,500 |
| Boca Raton PAN16 | bypass | 1597.105 → 904.701 | [-45.7%, -40.9%] I | 347.807 → 260.026 | [-36.4%, -12.6%] I | 17,734,505 |
| Boca Raton RGB16 | 0 | 521.080 → 313.345 | [-40.7%, -39.1%] I | 104.832 → 68.332 | [-40.5%, -28.2%] I | 3,054,801 |
| Boca Raton RGB16 | bypass | 317.376 → 162.093 | [-49.9%, -47.9%] I | 68.617 → 43.284 | [-40.9%, -32.6%] I | 3,122,192 |
| Boca Raton MS16 | 0 | 1476.839 → 900.696 | [-40.0%, -38.0%] I | 297.786 → 199.945 | [-39.9%, -25.0%] I | 9,103,938 |
| Boca Raton MS16 | bypass | 888.890 → 461.137 | [-49.4%, -46.8%] I | 195.214 → 127.463 | [-40.6%, -28.4%] I | 9,721,574 |
| Boca Raton RGB8 | 0 | 3637.654 → 2390.253 | [-37.3%, -31.1%] I | 945.558 → 753.481 | [-31.8%, -7.4%] I | 14,339,292 |
| Boca Raton RGB8 | bypass | 3109.601 → 2001.574 | [-39.1%, -32.0%] I | 847.616 → 694.144 | [-30.8%, -3.4%] ? | 14,937,382 |
| Tok RGB8 | 0 | 3254.197 → 2266.012 | [-31.6%, -29.1%] I | 726.602 → 567.937 | [-29.1%, -14.1%] I | 15,267,665 |
| Tok RGB8 | bypass | 3019.877 → 2081.070 | [-32.2%, -29.9%] I | 687.244 → 537.182 | [-27.9%, -15.3%] I | 15,321,890 |

## Targeted decoder regression

Identical OpenJPEG-origin streams were supplied to both Emuella builds.

| Product | Style | One worker ms | 99% change / verdict | Eight workers ms | 99% change / verdict |
|---|---|---:|---|---:|---|
| Mansfield PAN16 | 0 | 1370.021 → 1378.127 | [-0.5%, +1.7%] E | 211.439 → 216.101 | [-3.4%, +8.0%] ? |
| Mansfield PAN16 | bypass | 697.503 → 696.765 | [-2.0%, +1.8%] E | 128.321 → 126.943 | [-8.3%, +6.8%] ? |
| Mansfield MS16 | 0 | 729.037 → 731.134 | [-1.3%, +1.9%] E | 106.051 → 108.146 | [-2.1%, +6.2%] ? |
| Mansfield MS16 | bypass | 337.395 → 333.750 | [-2.7%, +0.5%] E | 57.085 → 56.163 | [-6.0%, +3.0%] ? |
| Mansfield RGB8 | 0 | 1773.201 → 1761.202 | [-2.6%, +1.3%] E | 283.071 → 280.878 | [-7.7%, +6.6%] ? |
| Mansfield RGB8 | bypass | 1589.676 → 1572.889 | [-3.5%, +1.5%] E | 262.045 → 259.822 | [-9.8%, +9.1%] ? |

## Separate SpaceNet development regression

All twelve fixed RGB16 chips use one worker. Khartoum is excluded. The complete
stream hashes match the retained historical native/OpenJPEG full-sample evidence.

| Development chip | Style | Reference → packed ms | 99% change | Bytes |
|---|---|---:|---|---:|
| Vegas 1454 | 0 | 613.836 → 357.375 | [-42.4%, -41.2%] | 3,020,684 |
| Vegas 1454 | bypass | 412.294 → 209.811 | [-49.6%, -48.6%] | 3,094,243 |
| Vegas 230 | 0 | 664.095 → 405.576 | [-39.4%, -38.4%] | 3,576,221 |
| Vegas 230 | bypass | 429.823 → 235.817 | [-45.5%, -44.8%] | 3,614,142 |
| Vegas 699 | 0 | 639.235 → 395.884 | [-38.5%, -37.6%] | 3,470,891 |
| Vegas 699 | bypass | 423.173 → 239.232 | [-44.2%, -42.8%] | 3,492,702 |
| Vegas 794 | 0 | 652.857 → 395.365 | [-40.1%, -38.8%] | 3,389,718 |
| Vegas 794 | bypass | 423.298 → 227.550 | [-47.0%, -45.5%] | 3,446,014 |
| Paris 235 | 0 | 482.024 → 322.670 | [-33.6%, -32.5%] | 2,596,834 |
| Paris 235 | bypass | 417.263 → 275.135 | [-34.5%, -33.6%] | 2,637,991 |
| Paris 340 | 0 | 535.429 → 337.527 | [-37.3%, -36.6%] | 2,733,593 |
| Paris 340 | bypass | 405.457 → 241.514 | [-40.9%, -40.0%] | 2,785,304 |
| Paris 432 | 0 | 589.259 → 352.786 | [-40.6%, -39.7%] | 2,853,974 |
| Paris 432 | bypass | 405.564 → 217.854 | [-46.7%, -45.8%] | 2,931,088 |
| Paris 84 | 0 | 184.638 → 111.262 | [-40.5%, -38.9%] | 791,135 |
| Paris 84 | bypass | 142.522 → 79.938 | [-44.6%, -43.2%] | 922,405 |
| Shanghai 1196 | 0 | 527.855 → 330.846 | [-37.7%, -36.9%] | 2,724,532 |
| Shanghai 1196 | bypass | 378.145 → 220.611 | [-42.4%, -40.9%] | 2,776,005 |
| Shanghai 1700 | 0 | 462.722 → 298.281 | [-36.0%, -35.0%] | 2,314,884 |
| Shanghai 1700 | bypass | 348.211 → 213.326 | [-39.4%, -38.1%] | 2,427,627 |
| Shanghai 1890 | 0 | 103.912 → 62.734 | [-40.4%, -38.9%] | 366,271 |
| Shanghai 1890 | bypass | 84.604 → 48.511 | [-43.3%, -42.1%] | 520,464 |
| Shanghai 308 | 0 | 455.850 → 296.399 | [-35.3%, -34.7%] | 2,353,158 |
| Shanghai 308 | bypass | 350.717 → 218.682 | [-38.1%, -37.1%] | 2,443,815 |

## Exactness and resources

The reference treatment completed all 1,920 calls; SpaceNet completed all 960.
Every encode matched its bound reference stream and reconstructed every native
sample. The 24 SpaceNet development stream hashes also match the retained
historical independently decoded OpenJPEG streams; the factual record binds
that reuse chain. Khartoum was excluded from performance evaluation.

Separate codec allocation diagnostics completed 144 calls: both implementations,
all nine RarePlanes products, both styles, and 1/2/4/8 workers. Complete bytes,
queried working bounds and output capacities matched the reference at every
point. The maximum observed additional requested encode allocation was
366,357,664 bytes for packed versus 366,371,264 for reference. The maximum queried
working bound was 602,189,308 bytes and maximum output capacity 25,649,152 bytes,
within the unchanged 768 MiB / 64 MiB limits. Per-case observations, including
one/eight-worker allocations, are separate from whole-process RSS/CPU in the
factual record. Requested allocations are not physical heap usage or RSS.

Codec evidence covers exact authored context/decision/boundary traces, block
bytes, pass and missing-plane counts, segment lengths, signs, all subbands,
partial stripes/edges, 1–32 magnitude planes, strided input, prefixes, scratch
reuse, fallback, bypass stuffing/termination, malformed input, tight admission
and output capacities, and joined in-flight failure/reuse. No protected pixel
or coefficient payload is included here. Traces are unit-test-only; sampled
builds are separate and rejected for headline measurements.

## Matched OpenJPEG anchor

All 4,320 original timed calls and 36 preparations completed with exact
reconstruction. Ratios below are descriptive equally weighted geometric means
of nine per-image Emuella/OpenJPEG time ratios; they have no aggregate confidence
claim. Below one favours Emuella. Per-case intervals and absolute one/eight-worker
OpenJPEG and Emuella times are in the matched factual record.

| Profile | Workers | Encode E/O | Emuella faster | Equivalent | Inconclusive | OpenJPEG faster |
|---|---:|---:|---:|---:|---:|---:|
| Style 0 | 1 | 1.047 | 0 | 1 | 5 | 3 |
| Style 0 | 8 | 1.441 | 0 | 0 | 1 | 8 |
| Bypass | 1 | 0.934 | 5 | 0 | 2 | 2 |
| Bypass | 8 | 1.349 | 0 | 0 | 5 | 4 |

Across both stream origins, matched decode had seventeen OpenJPEG-faster,
fifty-four inconclusive and one equivalent comparison. These are external-codec
comparisons, not evidence that the unchanged Emuella decoder regressed. The
reference treatment above is the relevant decoder regression check.

## Bound source and retained interruptions

- Fresh reference codec: `08fd8dfc80c3475209680032ce2c097409716246`.
- Frozen measured packed codec: `f1115ef9b1b8066c77bfc91f737eb8bb4f97b878`, tree
  `acc07b9f940a27dc6381862b2eac9c3f20db0fef`; compile-time selector `packed`.
- Reference worker source: benchmark `a392fe8cba7b26c3358d1b90a5014c687a60f07b`;
  selected worker/confirmation source: `41492b783ac136fc11f630c4459eb26bb7a512ff`.
  Compiled benchmark sources were identical; intervening changes were the
  report/driver/test surface. The factual record preserves each actual identity.
- Rust 1.97.1; OpenJPEG 2.5.4; AMD Ryzen 9 9950X3D, powersave governor.
  Perf/optimisation 3/ThinLTO/one codegen unit, parallel on, optional SIMD off.
  CPU 0 at one worker and CPUs 0–7 at eight; 120-second process timeout and
  8 GiB address-space ceiling. Matching D2, one full tile/layer, LRCP,
  64-square blocks, RGB RCT and PAN/MSI without MCT.

The external controller exited 143 during round eighteen; the initiating actor
was not observed. It had persisted 3,772 timed results and left one additional
completed child response/resource report. Independent evidence review established
that the complete exactness JSON, empty stderr and normal GNU Time report without
`-q` proved successful child completion. That observation was recovered; its
controller wall duration remains unavailable. Its operation time, CPU time and
RSS are retained. Only the 547 unstarted calls were continued, preserving the
original sequence, builds, inputs and every sample. The pause between adjacent
codec calls remains a limitation; no sample was repeated, replaced or removed.
The matched factual record binds the interruption and continuation evidence.

Earlier whole-process profiling and one FIFO acknowledgement failure remain
separate from successful encode-only sampling. An attempted three-round screen
analysis hit the unchanged twenty-round estimator assertion; corrected screen
analysis is descriptive only. A benchmark canonical attempt using a relocated
cache failed on stale test-worker paths; a fresh registered build passed without
source changes. These setup/analysis failures are retained and are not codec
rejection evidence. No acceptance gate was weakened.

Raw observations, full build/check receipts and protected derivatives remain in
the authorised RarePlanes/SpaceNet stores. Later default-dispatch and documentation
commits do not relabel the frozen measured binary; delivery evidence binds the
small promotion delta and focused committed/merged integration checks.

RarePlanes Dataset, June 2020: J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and
AI.Reverie, CC BY-SA 4.0. SpaceNet Dataset, SpaceNet Partners and DigitalGlobe
imagery; Van Etten, Lindenbaum and Bacastow (2018), CC BY-SA 4.0. Original notices
and source lineage remain with the respective local evidence. These are fixed,
previously measured acquisitions on one host, not untouched holdouts or a
universal codec ranking.
