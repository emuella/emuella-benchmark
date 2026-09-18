//! Authored arithmetic probes only: no worker, clock, corpus or deployment claim.
use emuella_benchmark::{
    compare::{CaseComparison, Verdict, compare},
    contract::Run,
};
use serde_json::json;

const N: usize = 20;
// Match the existing twenty-batch marginal multiplier to isolate the interval
// construction/covariance effect. This is not a newly calibrated confidence level.
const Q: f64 = 3.287;

type Pairs = Vec<(u64, u64)>;

fn fixture_run(pairs: &Pairs, candidate: bool) -> Run {
    let case = json!({
        "id": "authored-precision", "input": {"path": "unused.raw", "sha256": "0".repeat(64)},
        "reference": null, "image": {"width": 1, "height": 1, "components": 1,
        "precision": 8, "signed": false}, "operation": "encode", "settings": {}, "threads": 1,
        "output": {"colour": "grey", "layout": "interleaved", "container": "synthetic",
        "lossless": true, "reduction": 0, "region": null, "minimum_psnr_db": null,
        "image": {"width": 1, "height": 1, "components": 1, "precision": 8, "signed": false}}
    });
    let run_id = if candidate {
        "authored-b"
    } else {
        "authored-a"
    };
    let batches: Vec<_> = pairs
        .iter()
        .enumerate()
        .map(|(round, &(x, y))| {
            let index = 2 * round + usize::from(candidate == (round % 2 == 0));
            json!({"case_id": "authored-precision", "round": round, "execution_index": index,
            "status": "ok", "detail": null, "response": {"schema_version": 1,
            "request_id": format!("{run_id}-{index}"), "status": "ok", "message": null,
            "applied_case": case, "boundary": "codec_operation",
            "samples_ns": [if candidate {y} else {x}], "output_bytes": 1, "peak_rss_bytes": null,
            "correctness": {"sample_count": 1, "exact": true, "maximum_absolute_error": 0.0,
            "mse": 0.0, "peak": 255.0, "psnr_db": null}}})
        })
        .collect();
    serde_json::from_value(json!({
        "schema_version": 1, "run_id": run_id, "created_unix_ms": 0,
        "experiment": {"schema_version": 1, "name": "authored precision fixture",
            "protocol": {"rounds": pairs.len(), "samples_per_batch": 1, "warmup": 0,
            "timeout_ms": 1000, "boundary": "codec_operation",
            "context_policy": "fresh_process_per_batch", "cache_policy": "warm_input",
            "practical_relative_threshold": 0.05}, "environment_tags": {}, "cases": [case]},
        "worker": {"definition": {"executable": "unused", "args": [],
            "implementation": "authored", "source_identity": "test-fixture", "artefacts": []},
            "executable_sha256": "0".repeat(64), "artefact_sha256": {}},
        "harness_version": "authored", "harness_sha256": "0".repeat(64),
        "machine": {"os": "authored", "architecture": "authored", "hostname": "authored",
            "kernel": "authored", "cpu": "authored", "logical_cpus": 1,
            "affinity": "authored", "governors": {}, "environment_sha256": "0".repeat(64)},
        "pair_id": "authored-ab-ba", "diagnostic": false, "batches": batches
    }))
    .unwrap()
}

fn current(pairs: &Pairs) -> CaseComparison {
    let report = compare(&fixture_run(pairs, false), &fixture_run(pairs, true));
    assert!(report.method.contains("99.5% marginal Student t"));
    assert!(report.method.contains("paired AB/BA acquisition"));
    assert_eq!(report.cases.len(), 1, "{}", report.reason);
    report.cases.into_iter().next().unwrap()
}

fn mean(values: impl Iterator<Item = f64>, n: usize) -> f64 {
    values.sum::<f64>() / n as f64
}

// Experimental bounded branch of paired Fieller inversion, used only by tests.
// None preserves an unbounded/degenerate result; it must never become acceptance.
// A full future implementation must represent all confidence-set topologies.
fn paired_fieller(pairs: &Pairs) -> Option<[f64; 2]> {
    assert_eq!(pairs.len(), N);
    let x = mean(pairs.iter().map(|p| p.0 as f64), N);
    let y = mean(pairs.iter().map(|p| p.1 as f64), N);
    let covariance = |f: fn(f64, f64) -> f64| {
        pairs
            .iter()
            .map(|p| f(p.0 as f64 - x, p.1 as f64 - y))
            .sum::<f64>()
            / (N * (N - 1)) as f64
    };
    let vx = covariance(|dx, _| dx * dx);
    let vy = covariance(|_, dy| dy * dy);
    let cxy = covariance(|dx, dy| dx * dy);
    let a = x * x - Q * Q * vx;
    let b = -2.0 * (x * y - Q * Q * cxy);
    let c = y * y - Q * Q * vy;
    let discriminant = b * b - 4.0 * a * c;
    if a <= 0.0 || discriminant < 0.0 {
        return None;
    }
    Some([
        (-b - discriminant.sqrt()) / (2.0 * a) - 1.0,
        (-b + discriminant.sqrt()) / (2.0 * a) - 1.0,
    ])
}

fn symmetric(candidate_mean: u64, noise: u64) -> Pairs {
    (0..N)
        .map(|i| {
            let offset = if i % 2 == 0 {
                -(noise as i64)
            } else {
                noise as i64
            };
            (1_000_000, (candidate_mean as i64 + offset) as u64)
        })
        .collect()
}

fn width(bounds: [f64; 2]) -> f64 {
    bounds[1] - bounds[0]
}
fn contains(bounds: [f64; 2], value: f64) -> bool {
    bounds[0] <= value && value <= bounds[1]
}

#[test]
fn current_estimator_keeps_small_tiny_and_uncertain_effects_distinct() {
    for (name, centre, noise, verdict, expected) in [
        (
            "precise-three-percent",
            970_000,
            1_000,
            Verdict::Equivalent,
            [-0.030754089517232464, -0.02924591048276748],
        ),
        (
            "tiny-point-two-percent",
            998_000,
            100,
            Verdict::Equivalent,
            [-0.002075408951723201, -0.0019245910482768025],
        ),
        (
            "crosses-zero",
            980_000,
            100_000,
            Verdict::Inconclusive,
            [-0.09540895172325359, 0.05540895172325366],
        ),
        (
            "negative-crosses-minus-five",
            960_000,
            20_000,
            Verdict::Inconclusive,
            [-0.05508179034465077, -0.0249182096553493],
        ),
    ] {
        let result = current(&symmetric(centre, noise));
        assert_eq!(result.verdict, verdict, "{name}");
        assert!(
            (result.relative_change.unwrap() - (centre as f64 / 1_000_000.0 - 1.0)).abs() < 1e-12
        );
        let bounds = result.relative_interval_99.unwrap();
        for (actual, expected) in bounds.into_iter().zip(expected) {
            assert!((actual - expected).abs() < 1e-10, "{name}: {bounds:?}");
        }
        println!("{name}: current {bounds:?} {:?}", result.verdict);
    }
}

#[test]
fn shared_variation_can_cancel_for_null_and_small_effects() {
    for ratio in [1.0, 0.97, 0.998] {
        let pairs: Pairs = (0..N)
            .map(|i| {
                let x = 800_000 + i as u64 * 20_000;
                let residual = if i % 2 == 0 { -500.0 } else { 500.0 };
                (x, (x as f64 * ratio + residual).round() as u64)
            })
            .collect();
        let independent = current(&pairs).relative_interval_99.unwrap();
        let paired = paired_fieller(&pairs).unwrap();
        assert!(contains(paired, ratio - 1.0));
        assert!(width(paired) < width(independent) / 50.0);
        // Same marginals, broken pairing: covariance is substantive, not a label.
        let reversed: Pairs = pairs
            .iter()
            .zip(pairs.iter().rev())
            .map(|(a, b)| (a.0, b.1))
            .collect();
        assert!(width(paired_fieller(&reversed).unwrap()) > width(paired) * 50.0);
        assert_eq!(current(&reversed).relative_interval_99, Some(independent));
        println!("shared ratio {ratio}: current {independent:?}, experimental {paired:?}");
    }
}

#[test]
fn balanced_order_effect_and_treatment_specific_carryover() {
    // A common second-position cost balances with ten AB and ten BA pairs.
    let balanced: Pairs = (0..N)
        .map(|i| {
            if i % 2 == 0 {
                (1_000_000, 1_020_000)
            } else {
                (1_020_000, 1_000_000)
            }
        })
        .collect();
    assert!(contains(paired_fieller(&balanced).unwrap(), 0.0));
    assert!(contains(
        current(&balanced).relative_interval_99.unwrap(),
        0.0
    ));
    // Treatment-specific carryover does not balance: B alone is slower second.
    let carryover: Pairs = (0..N)
        .map(|i| (1_000_000, if i % 2 == 0 { 1_080_000 } else { 1_000_000 }))
        .collect();
    assert!(paired_fieller(&carryover).unwrap()[0] > 0.0);
    assert!(current(&carryover).relative_change.unwrap() > 0.0);
}

#[test]
fn unequal_variance_and_skew_do_not_establish_coverage() {
    let unequal = symmetric(970_000, 20_000);
    let independent = current(&unequal).relative_interval_99.unwrap();
    let paired = paired_fieller(&unequal).unwrap();
    // Fixed X makes Fieller exactly the Y interval divided by X for this Q.
    for (x, y) in independent.into_iter().zip(paired) {
        assert!((x - y).abs() < 1e-10);
    }
    let skew: Pairs = (0..N)
        .map(|i| (1_000_000, if i == N - 1 { 3_000_000 } else { 1_000_000 }))
        .collect();
    assert!(contains(paired_fieller(&skew).unwrap(), 0.0));
    assert!(contains(current(&skew).relative_interval_99.unwrap(), 0.0));
    assert!((current(&skew).relative_change.unwrap() - 0.1).abs() < 1e-12);
    // One authored tail value is retained, not trimmed or treated as a model.
}

#[test]
fn dependence_and_common_arm_bias_can_give_false_precision() {
    // Twenty records duplicate only two independent cluster shocks. The iid
    // formula cannot infer this provenance and excludes the stipulated null.
    let clustered: Pairs = (0..N)
        .map(|i| (1_000_000, if i < 10 { 1_020_000 } else { 1_040_000 }))
        .collect();
    let shuffled: Pairs = (0..N).map(|i| clustered[(i % 2) * 10 + i / 2]).collect();
    assert!(paired_fieller(&clustered).unwrap()[0] > 0.0);
    assert_eq!(paired_fieller(&clustered), paired_fieller(&shuffled));
    assert_eq!(
        current(&clustered).relative_interval_99,
        current(&shuffled).relative_interval_99
    );
    // Unobserved arm bias also cancels no more than its assumptions permit.
    let biased = symmetric(970_000, 1_000);
    assert!(paired_fieller(&biased).unwrap()[1] < 0.0);
}

#[test]
fn ratio_of_arithmetic_means_is_not_average_percentage_or_log_ratio() {
    let pairs: Pairs = (0..N)
        .map(|i| {
            if i % 2 == 0 {
                (1_000_000, 900_000)
            } else {
                (3_000_000, 3_000_000)
            }
        })
        .collect();
    let arithmetic = current(&pairs).relative_change.unwrap();
    let percentages = mean(pairs.iter().map(|&(x, y)| y as f64 / x as f64 - 1.0), N);
    let geometric = mean(pairs.iter().map(|&(x, y)| (y as f64 / x as f64).ln()), N).exp() - 1.0;
    assert!((arithmetic + 0.025).abs() < 1e-12);
    assert!((percentages + 0.05).abs() < 1e-12);
    assert!((geometric - (0.9_f64.sqrt() - 1.0)).abs() < 1e-12);
}

#[test]
fn weak_denominator_is_not_a_finite_precision_result() {
    let pairs: Pairs = (0..N)
        .map(|i| (if i == N - 1 { 20_000_000 } else { 1 }, 1_000_000))
        .collect();
    assert_eq!(paired_fieller(&pairs), None);
    let result = current(&pairs);
    assert_eq!(result.verdict, Verdict::Inconclusive);
    assert_eq!(result.relative_interval_99, None);
}
