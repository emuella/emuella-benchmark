//! Comparisons use independent batch means, never treat within-process repeats as
//! independent trials. Conservative 99.5% marginal t intervals remain descriptive evidence,
//! not a guarantee against drift, autocorrelation or uncontrolled system load.
use crate::{Result, contract::*, runner::validate_response};
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Verdict {
    Improved,
    Regressed,
    Equivalent,
    Inconclusive,
    Invalid,
    NotComparable,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CaseComparison {
    pub case_id: String,
    pub verdict: Verdict,
    pub reason: String,
    pub baseline_mean_ns: Option<f64>,
    pub candidate_mean_ns: Option<f64>,
    /// Candidate / baseline minus one, with conservative uncertainty interval.
    pub relative_change: Option<f64>,
    pub relative_interval_99: Option<[f64; 2]>,
    pub baseline_measurements: Option<MeasurementSummary>,
    pub candidate_measurements: Option<MeasurementSummary>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MeasurementSummary {
    pub mean_output_bytes: f64,
    pub output_bytes_range: [u64; 2],
    /// Compressed bits per spatial pixel for encoding; not defined for raw decode output.
    pub actual_bits_per_pixel: Option<f64>,
    pub peak_rss_bytes: Option<u64>,
    pub rss_observed_batches: usize,
    pub correctness: Correctness,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Comparison {
    pub schema_version: u32,
    pub baseline_run_id: String,
    pub candidate_run_id: String,
    pub baseline_implementation: String,
    pub candidate_implementation: String,
    pub baseline_source_identity: String,
    pub candidate_source_identity: String,
    pub verdict: Verdict,
    pub reason: String,
    pub method: String,
    pub cases: Vec<CaseComparison>,
}

pub fn validate_run(run: &Run) -> Result<()> {
    if run.schema_version != SCHEMA_VERSION {
        return Err("unsupported run schema version".into());
    }
    run.experiment.validate()?;
    crate::contract::validate_digest(&run.harness_sha256)?;
    crate::contract::validate_digest(&run.worker.executable_sha256)?;
    if run.run_id.is_empty()
        || run.harness_version.is_empty()
        || run.worker.definition.implementation.is_empty()
        || run.worker.definition.source_identity.is_empty()
    {
        return Err("run has incomplete build or run identity".into());
    }
    if run.worker.artefact_sha256.len() != run.worker.definition.artefacts.len()
        || run
            .worker
            .definition
            .artefacts
            .iter()
            .any(|p| !run.worker.artefact_sha256.contains_key(p))
    {
        return Err("worker artefact identity coverage differs".into());
    }
    for digest in run.worker.artefact_sha256.values() {
        crate::contract::validate_digest(digest)?;
    }
    let expected = usize::from(run.experiment.protocol.rounds) * run.experiment.cases.len();
    if run.batches.len() != expected {
        return Err("missing or extra case/batch coverage".into());
    }
    let mut keys = BTreeSet::new();
    let mut indices = BTreeSet::new();
    for batch in &run.batches {
        let case = run
            .experiment
            .cases
            .iter()
            .find(|case| case.id == batch.case_id)
            .ok_or("batch references unknown case")?;
        if batch.round >= run.experiment.protocol.rounds
            || !keys.insert((&batch.case_id, batch.round))
            || !indices.insert(batch.execution_index)
        {
            return Err("duplicate or out-of-range batch".into());
        }
        if batch.status == BatchStatus::Ok {
            let response = batch
                .response
                .as_ref()
                .ok_or("successful batch lacks response")?;
            if response.status != WorkerStatus::Ok {
                return Err("batch and worker status disagree".into());
            }
            validate_response(
                &WorkerRequest {
                    schema_version: SCHEMA_VERSION,
                    request_id: format!("{}-{}", run.run_id, batch.execution_index),
                    case: case.clone(),
                    protocol: run.experiment.protocol.clone(),
                    diagnostic: run.diagnostic,
                },
                response,
            )?;
        }
    }
    Ok(())
}
fn equivalent_experiments(a: &Experiment, b: &Experiment) -> bool {
    let mut a = a.clone();
    let mut b = b.clone();
    // Runtime asset locations are not workload identity. All content digests,
    // catalogue references, case order and semantic fields remain significant.
    for experiment in [&mut a, &mut b] {
        experiment.name.clear();
        for case in &mut experiment.cases {
            case.input.path.clear();
            if let Some(reference) = &mut case.reference {
                reference.path.clear();
            }
        }
    }
    a == b
}
fn empty_case(case_id: &str, verdict: Verdict, reason: String) -> CaseComparison {
    CaseComparison {
        case_id: case_id.into(),
        verdict,
        reason,
        baseline_mean_ns: None,
        candidate_mean_ns: None,
        relative_change: None,
        relative_interval_99: None,
        baseline_measurements: None,
        candidate_measurements: None,
    }
}
pub fn compare(a: &Run, b: &Run) -> Comparison {
    let mut result = Comparison { schema_version: SCHEMA_VERSION, baseline_run_id: a.run_id.clone(),
        candidate_run_id: b.run_id.clone(),
        baseline_implementation: a.worker.definition.implementation.clone(),
        candidate_implementation: b.worker.definition.implementation.clone(),
        baseline_source_identity: a.worker.definition.source_identity.clone(),
        candidate_source_identity: b.worker.definition.source_identity.clone(), verdict: Verdict::Inconclusive, reason: String::new(),
        method: "99.5% marginal Student t intervals on independent batch means; Bonferroni conservative 99% ratio bounds per case; no outlier removal".into(), cases: vec![] };
    for run in [a, b] {
        if let Err(error) = validate_run(run) {
            result.verdict = Verdict::Invalid;
            result.reason = error.to_string();
            return result;
        }
    }
    if a.diagnostic || b.diagnostic {
        result.verdict = Verdict::NotComparable;
        result.reason = "diagnostic runs are excluded from timing inference".into();
        return result;
    }
    if !equivalent_experiments(&a.experiment, &b.experiment)
        || a.machine != b.machine
        || a.harness_sha256 != b.harness_sha256
        || a.harness_version != b.harness_version
    {
        result.verdict = Verdict::NotComparable;
        result.reason =
            "protocol, input coverage, output semantics, environment or harness identity differs"
                .into();
        return result;
    }
    if [a, b].iter().any(|run| {
        run.machine.logical_cpus == 0
            || [&run.machine.hostname, &run.machine.cpu, &run.machine.kernel]
                .iter()
                .any(|x| x.is_empty() || *x == "unavailable")
    }) {
        result.verdict = Verdict::NotComparable;
        result.reason = "insufficient observed machine identity for timing inference".into();
        return result;
    }
    let paired = a.pair_id.is_some() && a.pair_id == b.pair_id;
    if paired {
        for case in &a.experiment.cases {
            for round in 0..a.experiment.protocol.rounds {
                let x = a
                    .batches
                    .iter()
                    .find(|x| x.case_id == case.id && x.round == round)
                    .unwrap();
                let y = b
                    .batches
                    .iter()
                    .find(|x| x.case_id == case.id && x.round == round)
                    .unwrap();
                if (round % 2 == 0 && x.execution_index.checked_add(1) != Some(y.execution_index))
                    || (round % 2 == 1
                        && y.execution_index.checked_add(1) != Some(x.execution_index))
                {
                    result.verdict = Verdict::Invalid;
                    result.reason = "paired runs do not have the declared AB/BA adjacency".into();
                    return result;
                }
            }
        }
        // Pairing controls acquisition drift. We deliberately retain conservative
        // independent intervals, without claiming paired statistical efficiency.
        result.method.push_str("; paired AB/BA acquisition");
    }
    for case in &a.experiment.cases {
        let a_batches: Vec<_> = a.batches.iter().filter(|x| x.case_id == case.id).collect();
        let b_batches: Vec<_> = b.batches.iter().filter(|x| x.case_id == case.id).collect();
        if a_batches
            .iter()
            .chain(&b_batches)
            .any(|x| x.status != BatchStatus::Ok)
        {
            let unsupported_only = a_batches.iter().chain(&b_batches).all(|x| {
                matches!(
                    x.status,
                    BatchStatus::Ok | BatchStatus::Unsupported | BatchStatus::UnattainableRate
                )
            });
            result.cases.push(empty_case(&case.id, if unsupported_only { Verdict::NotComparable } else { Verdict::Invalid },
                "coverage includes unsupported, unattainable-rate, failed, timed-out, crashed or invalid batches; no measurements discarded".into()));
            continue;
        }
        let means = |batches: &[&Batch]| -> Vec<f64> {
            batches
                .iter()
                .map(|x| {
                    let samples = &x.response.as_ref().unwrap().samples_ns;
                    samples.iter().map(|&x| x as f64).sum::<f64>() / samples.len() as f64
                })
                .collect()
        };
        let xs = means(&a_batches);
        let ys = means(&b_batches);
        let (x, xlow, xhigh) = interval(&xs);
        let (y, ylow, yhigh) = interval(&ys);
        if xlow <= 0.0 || ylow <= 0.0 {
            result.cases.push(CaseComparison {
                baseline_mean_ns: Some(x),
                candidate_mean_ns: Some(y),
                relative_change: Some(y / x - 1.0),
                baseline_measurements: Some(summarise(&a_batches, case)),
                candidate_measurements: Some(summarise(&b_batches, case)),
                ..empty_case(
                    &case.id,
                    Verdict::Inconclusive,
                    "noise interval reaches zero; collect more stable independent batches".into(),
                )
            });
            continue;
        }
        let bounds = [ylow / xhigh - 1.0, yhigh / xlow - 1.0];
        let threshold = a.experiment.protocol.practical_relative_threshold;
        let verdict = if bounds[0] > threshold {
            Verdict::Regressed
        } else if bounds[1] < -threshold {
            Verdict::Improved
        } else if bounds[0] >= -threshold && bounds[1] <= threshold {
            Verdict::Equivalent
        } else {
            Verdict::Inconclusive
        };
        result.cases.push(CaseComparison {
            case_id: case.id.clone(),
            verdict,
            reason: format!(
                "relative interval [{:.4}, {:.4}], practical threshold ±{:.4}",
                bounds[0], bounds[1], threshold
            ),
            baseline_mean_ns: Some(x),
            candidate_mean_ns: Some(y),
            relative_change: Some(y / x - 1.0),
            relative_interval_99: Some(bounds),
            baseline_measurements: Some(summarise(&a_batches, case)),
            candidate_measurements: Some(summarise(&b_batches, case)),
        });
    }
    result.verdict = if result.cases.iter().any(|x| x.verdict == Verdict::Invalid) {
        Verdict::Invalid
    } else if result
        .cases
        .iter()
        .any(|x| x.verdict == Verdict::NotComparable)
    {
        Verdict::NotComparable
    } else if result.cases.iter().any(|x| x.verdict == Verdict::Regressed) {
        Verdict::Regressed
    } else if result
        .cases
        .iter()
        .any(|x| x.verdict == Verdict::Inconclusive)
    {
        Verdict::Inconclusive
    } else if result.cases.iter().any(|x| x.verdict == Verdict::Improved) {
        Verdict::Improved
    } else {
        Verdict::Equivalent
    };
    result.reason = "Whole coverage timing verdict: invalid/incomparable coverage blocks inference; any regression wins; uncertainty blocks improvement; remaining cases must be equivalent or improved.".into();
    result.cases.sort_by(|a, b| {
        let rank = |v: &Verdict| match v {
            Verdict::Invalid => 0,
            Verdict::NotComparable => 1,
            Verdict::Regressed => 2,
            Verdict::Inconclusive => 3,
            Verdict::Improved => 4,
            Verdict::Equivalent => 5,
        };
        rank(&a.verdict).cmp(&rank(&b.verdict)).then_with(|| {
            b.relative_change
                .unwrap_or(0.0)
                .abs()
                .total_cmp(&a.relative_change.unwrap_or(0.0).abs())
        })
    });
    result
}
/// Aggregate completed batch observations for one case. Callers must supply only
/// successful batches for the same declared case.
pub fn summarise(batches: &[&Batch], case: &Case) -> MeasurementSummary {
    let responses: Vec<_> = batches
        .iter()
        .map(|b| b.response.as_ref().unwrap())
        .collect();
    let sizes: Vec<_> = responses.iter().map(|r| r.output_bytes.unwrap()).collect();
    let mean_output_bytes = sizes.iter().map(|&n| n as f64).sum::<f64>() / sizes.len() as f64;
    let correctness = crate::metrics::combine(
        &responses
            .iter()
            .map(|r| r.correctness.clone().unwrap())
            .collect::<Vec<_>>(),
    )
    .unwrap();
    MeasurementSummary {
        mean_output_bytes,
        output_bytes_range: [*sizes.iter().min().unwrap(), *sizes.iter().max().unwrap()],
        actual_bits_per_pixel: (case.operation == Operation::Encode).then(|| {
            mean_output_bytes * 8.0 / (f64::from(case.image.width) * f64::from(case.image.height))
        }),
        peak_rss_bytes: responses.iter().filter_map(|r| r.peak_rss_bytes).max(),
        rss_observed_batches: responses
            .iter()
            .filter(|r| r.peak_rss_bytes.is_some())
            .count(),
        correctness,
    }
}
fn interval(values: &[f64]) -> (f64, f64, f64) {
    let n = values.len() as f64;
    let mean = values.iter().sum::<f64>() / n;
    let variance = values.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / (n - 1.0);
    // Conservative upper bucket bounds for two-sided 99.5% t critical values.
    // Bonferroni bounds the union of two marginal failures by 1% per case.
    // No simultaneous family-wide coverage across different cases is claimed.
    let t = match values.len() - 1 {
        0..=4 => 5.598,
        5 => 4.774,
        6 => 4.317,
        7 => 4.030,
        8 => 3.833,
        9 => 3.690,
        10..=14 => 3.582,
        15..=19 => 3.287,
        20..=29 => 3.154,
        30..=59 => 3.030,
        60..=119 => 2.915,
        _ => 2.860,
    };
    let margin = t * (variance / n).sqrt();
    (mean, mean - margin, mean + margin)
}

#[cfg(test)]
mod tests {
    #[test]
    fn minimum_batch_margin_covers_995_percent_t_interval() {
        // Five symmetric samples have sample variance one. The df=4 two-sided
        // 99.5% critical value is 5.5975683670755; use an upward-rounded bound.
        let d = 2.0_f64.sqrt();
        let (mean, lower, upper) = super::interval(&[10.0 - d, 10.0, 10.0, 10.0, 10.0 + d]);
        let required = 5.5975683670755 / 5.0_f64.sqrt();
        assert!(upper - mean >= required);
        assert!(mean - lower >= required);
        assert!(upper - mean < required + 0.001);
    }
}
