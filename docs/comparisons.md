# Conservative timing comparisons

Compare completed runs only. Schema, protocol, case coverage/order, input and
reference digests/provenance, semantic settings, output geometry, thread budgets,
machine/environment and harness binary identity must match. Worker implementation,
source revision, executable and dependency hashes may differ: those are the
baseline/candidate treatment. Diagnostic runs are excluded. A changed requested
lossy rate point is a different workload, not an ordinary timing comparison.

Each fresh-process batch contributes its mean of measured in-memory repeats.
Within-process samples are retained but are not counted as independent trials.
`pair` keeps matching cases adjacent and alternates baseline/candidate order by
round (AB/BA). It records the shared pair identity and execution ordering. Pairing
reduces simple order drift; inference still uses conservative independent means.

For each side, compute a two-sided 99.5% Student t interval over independent batch
means, using upward-rounded critical values and conservative degrees-of-freedom
buckets. Bonferroni gives at least 99% joint marginal coverage under the model.
Positive bounds give the relative ratio interval `[candidate_low/baseline_high -
1, candidate_high/baseline_low - 1]`. Bounds reaching zero are inconclusive. This
is a per-case model-based interval, with no simultaneous family-wide guarantee,
no outlier removal and no claim that batch independence or normality is universal.
Calibration is required for each consequential deployment of the method.

With practical threshold `t`, a whole interval below `-t` is improved; above `t`
is regressed; wholly inside `[-t,t]` is equivalent; all other intervals are
inconclusive. Five percent is a configurable starting threshold, not a measured
universal noise floor. An unchanged build can remain inconclusive under load.

Failed, crashed, timed-out or invalid batches invalidate that case. Unsupported or unattainable-rate
coverage is not comparable. No successful subset can yield a whole-run speedup.
Overall precedence is invalid, not comparable, regressed, inconclusive, improved,
equivalent. Improvement therefore requires all cases to be equivalent or improved
and at least one improved. Cases are shown by actionable verdict and descending
absolute effect; raw run ordering is unchanged.

Reports call this a **timing verdict**. They also expose mean/range output bytes,
encoded bits per spatial pixel (encode only), aggregate exactness/MSE/PSNR and
observed peak process RSS with observation count. Lossy timing improvements do
not by themselves establish a better rate/distortion trade-off. Static HTML
escapes all dynamic strings and makes no network requests.
