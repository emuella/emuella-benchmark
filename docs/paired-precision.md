# Prospective precision investigation

The production comparator, commands, report schema and default 99% per-case
interval / 5% practical threshold remain unchanged. This note recommends one
**experimental, test-only** candidate for a separate prospective calibration:
paired-covariance Fieller inversion for the ratio of arithmetic mean operation
times. No new confidence, codec performance or deployment-coverage claim follows.
Engineering disposition is separate from the timing verdict; changing a decision
rule does not improve measurement precision.

## Acquisition, estimand and possible gain

The [current method](comparisons.md) retains fresh-process batch means, shared
pair identity, round and execution index. It checks adjacent alternating AB/BA
acquisition, but constructs independent marginal mean bounds. Adjacency can
reduce exposure to slow environmental drift; alternation balances a common
second-position cost in a balanced design. Neither establishes independence of
successive pairs, absence of carryover, or statistical efficiency from pairing.

For baseline batch means X and candidate batch means Y, the target change is
`E(Y) / E(X) - 1`, estimated by `mean(Y) / mean(X) - 1`. Each process contributes
one mean; its in-process repeats are not independent trials. Averaging individual
`Y/X - 1` percentages or exponentiating a mean log ratio changes the estimand.
The authored fixture with pairs `(1, 0.9)` and `(3, 3)` illustrates this:
ratio-of-means change is −2.5%, mean percentage is −5%, and geometric change is
about −5.13%. These are different quantities even with perfectly matched pairs.

Positive within-pair covariance can cancel common variation when estimating a
ratio. The candidate retains that covariance rather than taking opposite corners
of marginal intervals. Its apparent gain also includes changing the interval
construction; it cannot all be attributed to covariance. Negative covariance,
order interactions, skew, insufficient pairs and serial dependence can remove
the gain or invalidate the interpretation. Smaller intervals alone do not prove
better calibrated inference.

## One candidate, with explicit assumptions

Let `vx`, `vy`, `cxy` be the estimated variance/covariance of the two means:
sample variance/covariance divided by the number of independent pairs `n`.
Fieller inversion retains ratios `r` satisfying

```text
(mean(Y) - r * mean(X))² <= q² * (vy - 2*r*cxy + r²*vx)
```

This is a quadratic inequality in `r`; subtract one only after finding its
ratio bounds. A denominator compatible with zero can yield unbounded or
otherwise non-ordinary sets. Never clip such a set into a finite success interval.
The classical paired construction assumes independent, identically distributed
bivariate-normal pairs and uses the appropriate Student t quantile with `n-1`
degrees of freedom. Timing applications outside that model need validation;
a nominal quantile is not evidence of actual coverage. See von Luxburg and
Franz, [*A Geometric Approach to Confidence Sets for Ratios*](https://arxiv.org/html/0711.0198v1),
§§1.1–3, for the construction, assumptions and unbounded cases.

An eventual implementation would require complete pair identity/order validation,
all confidence-set shapes, numerical stability, and a predeclared response to
failed assumptions. AB and BA observations with systematic order effects are
not identically distributed merely because their counts balance. No production
selector, alternative CLI, new report fields or confidence label is introduced
here. This is the only candidate method recommended for investigation.

## Reproducible authored probes

Run `cargo test --test precision -- --nocapture`, or the existing canonical
`sh scripts/check.sh`. [The tests](../tests/precision.rs) construct in-memory
valid run records and invoke the actual comparator. They run no workers or
clocks and contain no protected data. All fixtures have twenty pairs with one
authored sample per batch, zero warmups and the unchanged 5% threshold.

The experimental helper implements only the bounded Fieller branch; `None`
means no finite result is available, never acceptance. It uses fixed `q=3.287`,
the current twenty-batch marginal multiplier, to compare interval construction
with the same multiplier. This is deliberately not a new nominal-99% estimator
or a complete library implementation. Tests check analytic special cases and
behaviour, not empirical confidence coverage.

| Actual current-comparator fixture | Mean change | Current relative interval | Timing verdict |
|---|---:|---:|---|
| Precise small effect | −3% | [−3.075409%, −2.924591%] | equivalent |
| Precise tiny effect | −0.2% | [−0.207541%, −0.192459%] | equivalent |
| Interval crosses zero | −2% | [−9.540895%, +5.540895%] | inconclusive |
| Below zero, crossing −5% | −4% | [−5.508179%, −2.491821%] | inconclusive |

Here `equivalent` retains the existing practical-band meaning: it does not assert
an exactly zero effect. The last interval supports a negative direction but does
not meet the historical whole-interval-below-−5% improvement rule. These tests
supply evidence for interpretation, not a new engineering acceptance decision.

| Further deterministic probe | Bounded observation and limitation |
|---|---|
| Shared linear drift with null, −3% and −0.2% ratios | Paired bounds include each authored ratio and are over 50 times narrower than current bounds. Reversing the pairing preserves current bounds and widens paired bounds. A constructed common trend is not evidence of iid pairs or calibrated coverage. |
| Balanced AB/BA position cost | Both constructions include zero for a common second-position cost. Treatment-specific carryover gives a positive apparent effect despite identical intrinsic operation costs. |
| Unequal arm variance | With constant baseline and variable candidate, Fieller reduces to the candidate mean interval divided by baseline; both bounds agree for the same multiplier. |
| Skewed candidate tail | One high value remains included and moves the mean by +10%; both intervals include zero. This one sequence cannot establish robustness to heavy tails. |
| Serial clusters and common arm bias | Repeating two cluster shocks as twenty records gives narrow bounds excluding the stipulated null. Reordering those records leaves both intervals unchanged. Neither formula detects the missing independent information or unobserved arm bias. |
| Weak denominator | Experimental helper returns no finite result; current comparator remains inconclusive with no ratio interval. |

## Available A/A evidence and missing proof

The [initial calibration](calibration.md#retained-initial-observation) and its
[factual record](evidence/initial-qualification.json) identify benchmark
`b72e560680d5ddb9834629e20d04fd2bef38a3b7`, seven rounds, three samples per batch,
one warmup, and the observed host/build/input identities. The synthetic unchanged
copy-and-sleep comparison was equivalent. Real unchanged Emuella used the same
worker digest on both sides; both selected generated cases were inconclusive.
This is a bounded historical observation, not an A/A failure-rate estimate.
The checked-in aggregate does not contain paired batch observations sufficient
to evaluate covariance or serial dependence. No pair-aware reanalysis or new
measurement was performed for this note.

The [4W scheduling result](classic-parallel-execution-results.md) remains a
rejection under its frozen confirmation gates. The [MQ D1/D2 result](classic-entropy-hot-loop-results.md)
remains a finite development-screen rejection; its small descriptive samples
have no confirmation claim. Their protocols, factual JSON and outcomes are
unchanged. They are not retrospective calibration inputs for this proposal.

## Required finite prospective calibration before adoption

Benchmark owns a separately reviewed calibration protocol and its evidence.
The proposed first budget is **two synthetic operation-duration cells**, nominally
5 ms and 50 ms, on one identified host/affinity/load configuration: **600
independent A/A sessions per cell, twenty adjacent alternating pairs per session,
one operation per fresh process, zero warmups**. That is 1,200 sessions and at
most 48,000 operation calls, with a 24-hour wall-clock cap for the whole study.
This bounds the initial question to the authored worker and these settings;
codec or other-host adoption would need separately scoped representative proof.
A session must be an independently scheduled acquisition, not twenty records
split out of one long correlated run. Declare scheduling and independence/order
diagnostics before launch; inability to justify independent sessions is a blocker.

Before collecting observations, freeze the candidate implementation with the
same `q=3.287` used by these probes and the current comparator reference, exact
worker binary/duration settings, host controls, session schedule and diagnostic
criteria. Bind identical worker hashes on both A/A arms and retain every
observation, failure, order, time and build/environment identity in its authorised
evidence store. No result-driven extra sessions, outlier removal or replacement
observations. Failed calls consume the budget; any missing/invalid session or
wall-clock cap reached before complete coverage ends in incomplete proof/deferment.

For each cell, propose a deliberately strict gate of **zero intervals excluding
the true zero change in 600 sessions**, including any false practical improvement
or regression decisions. Zero out of 600 gives the one-sided 99% exact binomial
upper bound `1 - 0.01^(1/600)`, approximately **0.765%**, for the session-level
null-exclusion probability, conditional on independent identically distributed
sessions. This is per cell, with no simultaneous family guarantee. It is a gate
to test, not a promised outcome or evidence from this change. Require complete
finite intervals and a median interval width at least 20% smaller than the
current comparator on those same sessions in each cell; retain all individual
widths and order/serial diagnostics. Zero observed false decisions alone does
not establish independence, non-null coverage or power.

Stop after the frozen counts or the cap, without tuning the estimator to rescue
failed gates. Exit with either evidence supporting this explicitly bounded scope
or finite rejection/deferment. Synthetic known-effect probes can check arithmetic
sensitivity, but any broader coverage claim needs additional predeclared evidence.
Any model, critical-value or ordering repair requires a new reviewed frozen
protocol and fresh independent observations before adoption. Until that work
establishes its gates, retain the existing estimator and label this method
experimental. This proposed budget does not launch calibration, candidate timing,
recurring retesting, or renewed qualification of any rejected codec experiment.
