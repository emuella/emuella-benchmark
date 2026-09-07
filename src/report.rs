use crate::compare::{Comparison, MeasurementSummary};

fn measurements(summary: &Option<MeasurementSummary>) -> String {
    match summary {
        None => "unavailable".into(),
        Some(m) => format!(
            "output {:.1} bytes (range {}–{}), bpp {}, exact {}, MSE {:.6}, PSNR {} dB, peak RSS {} bytes ({} observed batches)",
            m.mean_output_bytes,
            m.output_bytes_range[0],
            m.output_bytes_range[1],
            m.actual_bits_per_pixel
                .map_or_else(|| "not applicable".into(), |x| format!("{x:.4}")),
            m.correctness.exact,
            m.correctness.mse,
            m.correctness
                .psnr_db
                .map_or_else(|| "infinite (exact)".into(), |x| format!("{x:.4}")),
            m.peak_rss_bytes
                .map_or_else(|| "unavailable".into(), |x| x.to_string()),
            m.rss_observed_batches
        ),
    }
}
pub fn text(report: &Comparison) -> String {
    let mut out = format!(
        "Timing verdict {:?}: {}\n{}\n",
        report.verdict, report.reason, report.method
    );
    out.push_str(&format!(
        "Baseline: {} ({})\nCandidate: {} ({})\n",
        report.baseline_implementation,
        report.baseline_source_identity,
        report.candidate_implementation,
        report.candidate_source_identity
    ));
    for case in &report.cases {
        out.push_str(&format!(
            "{}: {:?} — {}\n  Baseline: {}\n  Candidate: {}\n",
            case.case_id,
            case.verdict,
            case.reason,
            measurements(&case.baseline_measurements),
            measurements(&case.candidate_measurements)
        ));
    }
    out
}
pub fn escape(value: &str) -> String {
    value
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&#39;")
}
/// Self-contained static HTML; no scripts, network requests or pixel payloads.
pub fn html(report: &Comparison) -> String {
    let mut out = format!(
        "<!doctype html><html lang=\"en-AU\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Codec benchmark comparison</title><link rel=\"icon\" href=\"data:,\"><style>body{{font:16px system-ui;max-width:1300px;margin:3rem auto;padding:0 1rem;color:#182b35;background:#f6f8f9}}table{{border-collapse:collapse;width:100%;background:white}}td,th{{padding:1rem;text-align:left;border-bottom:1px solid #ccd8df;vertical-align:top}}code{{overflow-wrap:anywhere}}h1{{font-size:2rem}}small{{display:block;margin-top:.5rem}}</style><h1>Codec benchmark timing verdict: {:?}</h1><p>{}</p><p>{}</p><p>Baseline <code>{}</code><br>Candidate <code>{}</code></p><table><thead><tr><th>Case</th><th>Timing verdict</th><th>Baseline</th><th>Candidate</th><th>Timing evidence</th></tr></thead><tbody>",
        report.verdict,
        escape(&report.reason),
        escape(&report.method),
        escape(&format!(
            "{} — {} — run {}",
            report.baseline_implementation, report.baseline_source_identity, report.baseline_run_id
        )),
        escape(&format!(
            "{} — {} — run {}",
            report.candidate_implementation,
            report.candidate_source_identity,
            report.candidate_run_id
        ))
    );
    for case in &report.cases {
        let cell = |n: Option<f64>, summary: &Option<MeasurementSummary>| {
            format!(
                "{} ns<small>{}</small>",
                n.map_or_else(|| "—".into(), |x| format!("{x:.1}")),
                escape(&measurements(summary))
            )
        };
        out.push_str(&format!(
            "<tr><td>{}</td><td>{:?}</td><td>{}</td><td>{}</td><td>{}</td></tr>",
            escape(&case.case_id),
            case.verdict,
            cell(case.baseline_mean_ns, &case.baseline_measurements),
            cell(case.candidate_mean_ns, &case.candidate_measurements),
            escape(&case.reason)
        ));
    }
    out.push_str("</tbody></table><p>Intervals describe this experiment, with per-case coverage and no family-wide guarantee. They do not establish universal performance or control all machine drift. Failed and unsupported coverage is retained. Timing improvements alone do not establish a better lossy size/distortion trade-off. RSS is a process peak, including setup and verification.</p></html>");
    out
}
#[cfg(test)]
mod tests {
    #[test]
    fn escape_markup() {
        assert_eq!(
            super::escape("<script>\"'&"),
            "&lt;script&gt;&quot;&#39;&amp;"
        );
    }
}
