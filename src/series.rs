//! Factual multi-run rate/distortion and progress extracts. These reports retain
//! coverage but make no interpolated, matched-quality or population-ranking claim.
use crate::{
    Result,
    compare::{MeasurementSummary, summarise, validate_run},
    contract::*,
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;

const RATE_KNOBS: [&str; 3] = ["target_bpp", "compression_ratio", "qstep"];

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Series {
    pub schema_version: u32,
    pub method: String,
    pub rate_distortion: Vec<RateDistortionGroup>,
    pub progress: Vec<ProgressGroup>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct RunIdentity {
    pub run_id: String,
    pub created_unix_ms: u64,
    pub pair_id: Option<String>,
    /// Complete executable, argument and content-hash identity used by the run.
    pub worker: WorkerIdentity,
    pub implementation: String,
    pub source_identity: String,
    pub executable_sha256: String,
    pub artefact_sha256: BTreeMap<std::path::PathBuf, String>,
    pub harness_version: String,
    pub harness_sha256: String,
    pub diagnostic: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct WorkloadIdentity {
    pub case_id: String,
    pub input_sha256: String,
    pub input_provenance: BTreeMap<String, String>,
    pub reference_sha256: Option<String>,
    pub reference_provenance: Option<BTreeMap<String, String>>,
    pub image: ImageSpec,
    pub operation: Operation,
    pub settings: BTreeMap<String, Value>,
    pub threads: u16,
    pub output: OutputSemantics,
    pub protocol: Protocol,
    pub environment_tags: BTreeMap<String, String>,
    pub machine: Machine,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct RateDistortionIdentity {
    pub input_sha256: String,
    pub input_provenance: BTreeMap<String, String>,
    pub reference_sha256: Option<String>,
    pub reference_provenance: Option<BTreeMap<String, String>>,
    pub image: ImageSpec,
    pub operation: Operation,
    /// All declared semantic settings except the three explicit rate controls.
    /// This deliberately retains a codec's coding family and every other setting.
    pub settings_excluding_rate_knobs: BTreeMap<String, Value>,
    pub threads: u16,
    pub output: OutputSemantics,
    pub protocol: Protocol,
    pub environment_tags: BTreeMap<String, String>,
    pub machine: Machine,
    pub harness_version: String,
    pub harness_sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct ProgressIdentity {
    pub workload: WorkloadIdentity,
    pub implementation: String,
    pub harness_version: String,
    pub harness_sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct MeasurementPoint {
    pub run: RunIdentity,
    pub workload: WorkloadIdentity,
    /// Mean of independent batch means in nanoseconds.
    pub mean_batch_ns: f64,
    pub mean_output_bytes: f64,
    /// Compressed bits per spatial input pixel. It is undefined for decode runs.
    pub actual_bits_per_pixel: Option<f64>,
    pub mse: f64,
    /// None means infinite PSNR for an exact output.
    pub psnr_db: Option<f64>,
    pub peak_rss_bytes: Option<u64>,
    pub rss_observed_batches: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct CoverageStatus {
    pub status: BatchStatus,
    pub batches: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct CoveragePoint {
    pub run: RunIdentity,
    pub workload: WorkloadIdentity,
    pub statuses: Vec<CoverageStatus>,
    /// Diagnostic evidence is retained but excluded from plotted timing points.
    pub excluded_from_points: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct RateDistortionGroup {
    pub identity: RateDistortionIdentity,
    pub points: Vec<MeasurementPoint>,
    pub coverage: Vec<CoveragePoint>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct ProgressGroup {
    pub identity: ProgressIdentity,
    pub points: Vec<MeasurementPoint>,
    pub coverage: Vec<CoveragePoint>,
}

fn run_identity(run: &Run) -> RunIdentity {
    RunIdentity {
        run_id: run.run_id.clone(),
        created_unix_ms: run.created_unix_ms,
        pair_id: run.pair_id.clone(),
        worker: run.worker.clone(),
        implementation: run.worker.definition.implementation.clone(),
        source_identity: run.worker.definition.source_identity.clone(),
        executable_sha256: run.worker.executable_sha256.clone(),
        artefact_sha256: run.worker.artefact_sha256.clone(),
        harness_version: run.harness_version.clone(),
        harness_sha256: run.harness_sha256.clone(),
        diagnostic: run.diagnostic,
    }
}

fn workload_identity(run: &Run, case: &Case) -> WorkloadIdentity {
    WorkloadIdentity {
        case_id: case.id.clone(),
        input_sha256: case.input.sha256.clone(),
        input_provenance: case.input.provenance.clone(),
        reference_sha256: case.reference.as_ref().map(|asset| asset.sha256.clone()),
        reference_provenance: case
            .reference
            .as_ref()
            .map(|asset| asset.provenance.clone()),
        image: case.image.clone(),
        operation: case.operation.clone(),
        settings: case.settings.clone(),
        threads: case.threads,
        output: case.output.clone(),
        protocol: run.experiment.protocol.clone(),
        environment_tags: run.experiment.environment_tags.clone(),
        machine: run.machine.clone(),
    }
}

fn rate_distortion_identity(run: &Run, case: &Case) -> RateDistortionIdentity {
    let mut settings_excluding_rate_knobs = case.settings.clone();
    for key in RATE_KNOBS {
        settings_excluding_rate_knobs.remove(key);
    }
    RateDistortionIdentity {
        input_sha256: case.input.sha256.clone(),
        input_provenance: case.input.provenance.clone(),
        reference_sha256: case.reference.as_ref().map(|asset| asset.sha256.clone()),
        reference_provenance: case
            .reference
            .as_ref()
            .map(|asset| asset.provenance.clone()),
        image: case.image.clone(),
        operation: case.operation.clone(),
        settings_excluding_rate_knobs,
        threads: case.threads,
        output: case.output.clone(),
        protocol: run.experiment.protocol.clone(),
        environment_tags: run.experiment.environment_tags.clone(),
        machine: run.machine.clone(),
        harness_version: run.harness_version.clone(),
        harness_sha256: run.harness_sha256.clone(),
    }
}

fn progress_identity(run: &Run, case: &Case) -> ProgressIdentity {
    ProgressIdentity {
        workload: workload_identity(run, case),
        implementation: run.worker.definition.implementation.clone(),
        harness_version: run.harness_version.clone(),
        harness_sha256: run.harness_sha256.clone(),
    }
}

fn serialised_key<T: Serialize>(value: &T) -> Result<String> {
    Ok(serde_json::to_string(value)?)
}

fn coverage(
    run: &Run,
    case: &Case,
    run_identity: &RunIdentity,
    workload: &WorkloadIdentity,
) -> CoveragePoint {
    let mut counts: BTreeMap<String, (BatchStatus, usize)> = BTreeMap::new();
    for batch in run.batches.iter().filter(|batch| batch.case_id == case.id) {
        let key = serde_json::to_string(&batch.status).expect("batch status serialises");
        let entry = counts.entry(key).or_insert((batch.status.clone(), 0));
        entry.1 += 1;
    }
    CoveragePoint {
        run: run_identity.clone(),
        workload: workload.clone(),
        statuses: counts
            .into_values()
            .map(|(status, batches)| CoverageStatus { status, batches })
            .collect(),
        excluded_from_points: run
            .diagnostic
            .then(|| "diagnostic runs are excluded from timing points".into()),
    }
}

fn all_successful(run: &Run, case: &Case) -> bool {
    run.batches
        .iter()
        .filter(|batch| batch.case_id == case.id)
        .all(|batch| batch.status == BatchStatus::Ok)
}

fn point(
    run: &Run,
    case: &Case,
    run_identity: &RunIdentity,
    workload: &WorkloadIdentity,
) -> MeasurementPoint {
    let batches: Vec<_> = run
        .batches
        .iter()
        .filter(|batch| batch.case_id == case.id)
        .collect();
    let summary: MeasurementSummary = summarise(&batches, case);
    let mean_batch_ns = batches
        .iter()
        .map(|batch| {
            let samples = &batch
                .response
                .as_ref()
                .expect("successful batch response")
                .samples_ns;
            samples.iter().map(|sample| *sample as f64).sum::<f64>() / samples.len() as f64
        })
        .sum::<f64>()
        / batches.len() as f64;
    MeasurementPoint {
        run: run_identity.clone(),
        workload: workload.clone(),
        mean_batch_ns,
        mean_output_bytes: summary.mean_output_bytes,
        actual_bits_per_pixel: summary.actual_bits_per_pixel,
        mse: summary.correctness.mse,
        psnr_db: summary.correctness.psnr_db,
        peak_rss_bytes: summary.peak_rss_bytes,
        rss_observed_batches: summary.rss_observed_batches,
    }
}

/// Extract validated completed runs into descriptive multi-run series. Invalid
/// stored runs are rejected; unsuccessful batches remain represented as coverage.
pub fn extract(runs: &[Run]) -> Result<Series> {
    let mut rd: BTreeMap<String, RateDistortionGroup> = BTreeMap::new();
    let mut progress: BTreeMap<String, ProgressGroup> = BTreeMap::new();
    for run in runs {
        validate_run(run)?;
        let run_identity = run_identity(run);
        for case in &run.experiment.cases {
            let workload = workload_identity(run, case);
            let rd_identity = rate_distortion_identity(run, case);
            let progress_identity = progress_identity(run, case);
            let coverage = coverage(run, case, &run_identity, &workload);
            let rd_group =
                rd.entry(serialised_key(&rd_identity)?)
                    .or_insert_with(|| RateDistortionGroup {
                        identity: rd_identity,
                        points: vec![],
                        coverage: vec![],
                    });
            rd_group.coverage.push(coverage.clone());
            let progress_group = progress
                .entry(serialised_key(&progress_identity)?)
                .or_insert_with(|| ProgressGroup {
                    identity: progress_identity,
                    points: vec![],
                    coverage: vec![],
                });
            progress_group.coverage.push(coverage);
            if !run.diagnostic && all_successful(run, case) {
                let point = point(run, case, &run_identity, &workload);
                rd_group.points.push(point.clone());
                progress_group.points.push(point);
            }
        }
    }
    let sort_points = |points: &mut Vec<MeasurementPoint>| {
        points.sort_by(|a, b| {
            a.run
                .created_unix_ms
                .cmp(&b.run.created_unix_ms)
                .then_with(|| a.run.run_id.cmp(&b.run.run_id))
        });
    };
    for group in rd.values_mut() {
        sort_points(&mut group.points);
    }
    for group in progress.values_mut() {
        sort_points(&mut group.points);
    }
    Ok(Series {
        schema_version: SCHEMA_VERSION,
        method: "Factual completed-run points: actual bpp is mean encoded output bytes times 8 divided by declared input width times height; timing is the mean of independent batch means. Coverage is retained. No interpolation, matched-quality comparison or population-ranking claim is made.".into(),
        rate_distortion: rd.into_values().collect(),
        progress: progress.into_values().collect(),
    })
}

fn svg_scatter(title: &str, x_label: &str, y_label: &str, points: &[(f64, f64, String)]) -> String {
    if points.is_empty() {
        return "<p>No completed points with these coordinates; inspect retained coverage below.</p>".into();
    }
    let (min_x, max_x) = points
        .iter()
        .fold((f64::INFINITY, f64::NEG_INFINITY), |range, point| {
            (range.0.min(point.0), range.1.max(point.0))
        });
    let (min_y, max_y) = points
        .iter()
        .fold((f64::INFINITY, f64::NEG_INFINITY), |range, point| {
            (range.0.min(point.1), range.1.max(point.1))
        });
    let scale = |value: f64, low: f64, high: f64, start: f64, span: f64| {
        if high == low {
            start + span / 2.0
        } else {
            start + (value - low) / (high - low) * span
        }
    };
    let mut out = format!(
        r##"<figure><figcaption>{}</figcaption><svg viewBox="0 0 760 360" role="img" aria-label="{}"><rect width="760" height="360" fill="white"/><path d="M70 20V300H740" fill="none" stroke="#47616d"/><text x="400" y="345" text-anchor="middle">{}</text><text x="18" y="160" transform="rotate(-90 18 160)" text-anchor="middle">{}</text><text x="70" y="320">{:.4}</text><text x="680" y="320">{:.4}</text><text x="22" y="292">{:.2}</text><text x="22" y="30">{:.2}</text>"##,
        crate::report::escape(title),
        crate::report::escape(title),
        crate::report::escape(x_label),
        crate::report::escape(y_label),
        min_x,
        max_x,
        min_y,
        max_y
    );
    for (x, y, label) in points {
        let cx = scale(*x, min_x, max_x, 70.0, 670.0);
        let cy = scale(*y, min_y, max_y, 300.0, -280.0);
        out.push_str(&format!(r##"<circle cx="{cx:.2}" cy="{cy:.2}" r="5" fill="#007f86"><title>{}</title></circle>"##, crate::report::escape(label)));
    }
    out.push_str("</svg></figure>");
    out
}

fn point_table(points: &[MeasurementPoint]) -> String {
    let mut out = "<table><thead><tr><th>Run</th><th>Implementation</th><th>Source revision</th><th>Actual bpp</th><th>Mean batch time</th><th>PSNR</th><th>MSE</th><th>Peak RSS</th></tr></thead><tbody>".to_owned();
    for point in points {
        out.push_str(&format!(
            "<tr><td><code>{}</code></td><td>{}</td><td><code>{}</code></td><td>{}</td><td>{:.2} ns</td><td>{}</td><td>{:.8}</td><td>{}</td></tr>",
            crate::report::escape(&point.run.run_id),
            crate::report::escape(&point.run.implementation),
            crate::report::escape(&point.run.source_identity),
            point.actual_bits_per_pixel.map_or_else(|| "not applicable".into(), |value| format!("{value:.6}")),
            point.mean_batch_ns,
            point.psnr_db.map_or_else(|| "infinite (exact)".into(), |value| format!("{value:.6} dB")),
            point.mse,
            point.peak_rss_bytes.map_or_else(|| "unobserved".into(), |value| format!("{value} bytes ({})", point.rss_observed_batches)),
        ));
    }
    out.push_str("</tbody></table>");
    out
}

fn coverage_table(coverage: &[CoveragePoint]) -> String {
    let mut out = "<table><thead><tr><th>Run</th><th>Case</th><th>Coverage</th><th>Point status</th></tr></thead><tbody>".to_owned();
    for item in coverage {
        let statuses = item
            .statuses
            .iter()
            .map(|status| format!("{:?}: {}", status.status, status.batches))
            .collect::<Vec<_>>()
            .join(", ");
        out.push_str(&format!(
            "<tr><td><code>{}</code></td><td>{}</td><td>{}</td><td>{}</td></tr>",
            crate::report::escape(&item.run.run_id),
            crate::report::escape(&item.workload.case_id),
            crate::report::escape(&statuses),
            crate::report::escape(
                item.excluded_from_points
                    .as_deref()
                    .unwrap_or("plotted only when all batches are successful")
            ),
        ));
    }
    out.push_str("</tbody></table>");
    out
}

/// Render a standalone, network-free factual series report with SVG scatterplots.
pub fn html(series: &Series) -> String {
    let mut out = format!(
        r##"<!doctype html><html lang="en-AU"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Codec benchmark series</title><link rel="icon" href="data:,"><style>body{{font:16px system-ui;max-width:1300px;margin:3rem auto;padding:0 1rem;color:#182b35;background:#f6f8f9}}table{{border-collapse:collapse;width:100%;background:white;margin:1rem 0}}td,th{{padding:.65rem;text-align:left;border-bottom:1px solid #ccd8df;vertical-align:top}}code{{overflow-wrap:anywhere}}svg{{max-width:100%;height:auto;background:white}}section{{margin:3rem 0}}h1{{font-size:2rem}}</style><h1>Codec benchmark factual series</h1><p>{}</p><p>Scatterplots show observed completed points only. They do not interpolate curves, match quality, rank populations or make claims across unlike machines or settings.</p>"##,
        crate::report::escape(&series.method)
    );
    for (index, group) in series.rate_distortion.iter().enumerate() {
        let points = group
            .points
            .iter()
            .filter_map(|point| {
                point.actual_bits_per_pixel.map(|bpp| {
                    (
                        bpp,
                        point.mean_batch_ns,
                        format!(
                            "run {}; source {}; PSNR {}; MSE {:.8}",
                            point.run.run_id,
                            point.run.source_identity,
                            point.psnr_db.map_or_else(
                                || "infinite".into(),
                                |value| format!("{value:.6} dB")
                            ),
                            point.mse
                        ),
                    )
                })
            })
            .collect::<Vec<_>>();
        out.push_str(&format!("<section><h2>Rate/distortion group {}</h2><p>Grouping retains input, output semantics, thread count, protocol, environment, machine, harness and every setting except the explicit rate controls <code>target_bpp</code>, <code>compression_ratio</code> and <code>qstep</code>.</p>{}<h3>Points</h3>{}<h3>Retained coverage</h3>{}</section>", index + 1, svg_scatter("Actual bpp versus mean batch time", "actual bpp", "mean batch time (ns)", &points), point_table(&group.points), coverage_table(&group.coverage)));
    }
    for (index, group) in series.progress.iter().enumerate() {
        let points = group
            .points
            .iter()
            .enumerate()
            .map(|(point_index, point)| {
                (
                    point_index as f64 + 1.0,
                    point.mean_batch_ns,
                    format!(
                        "source {}; run {}",
                        point.run.source_identity, point.run.run_id
                    ),
                )
            })
            .collect::<Vec<_>>();
        out.push_str(&format!("<section><h2>Progress group {}</h2><p>Source revision is listed against observed time for this exact grouped workload. It does not make unlike machines, configurations or implementations comparable.</p>{}<h3>Points</h3>{}<h3>Retained coverage</h3>{}</section>", index + 1, svg_scatter("Source revision/run order versus mean batch time", "source revision/run order", "mean batch time (ns)", &points), point_table(&group.points), coverage_table(&group.coverage)));
    }
    out.push_str("</html>");
    out
}
