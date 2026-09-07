use emuella_benchmark::{contract::*, runner, series};
use serde_json::json;
use std::{collections::BTreeMap, fs, path::Path, process::Command};

fn experiment(root: &Path, settings: BTreeMap<String, serde_json::Value>) -> Experiment {
    let path = root.join("input.raw");
    fs::write(&path, [0_u8, 1, 127, 255]).unwrap();
    let image = ImageSpec {
        width: 2,
        height: 2,
        components: 1,
        precision: 8,
        signed: false,
    };
    Experiment {
        schema_version: SCHEMA_VERSION,
        name: "series fixture".into(),
        protocol: Protocol {
            rounds: 5,
            samples_per_batch: 2,
            warmup: 1,
            timeout_ms: 1_000,
            ..Protocol::default()
        },
        environment_tags: BTreeMap::new(),
        cases: vec![Case {
            id: "fixture".into(),
            input: Asset {
                path: path.clone(),
                sha256: runner::sha256_file(&path).unwrap(),
                provenance: BTreeMap::new(),
            },
            reference: None,
            image: image.clone(),
            operation: Operation::Encode,
            settings,
            threads: 1,
            output: OutputSemantics {
                colour: "grey".into(),
                layout: "interleaved".into(),
                container: "synthetic".into(),
                lossless: true,
                reduction: 0,
                region: None,
                image,
                minimum_psnr_db: None,
            },
        }],
    }
}

fn worker(args: &[&str]) -> WorkerDefinition {
    WorkerDefinition {
        executable: env!("CARGO_BIN_EXE_protocol-test-worker").into(),
        args: args.iter().map(|arg| (*arg).into()).collect(),
        implementation: "synthetic worker".into(),
        source_identity: "series-test-revision".into(),
        artefacts: vec![],
    }
}

fn completed_run(
    root: &Path,
    directory: &str,
    settings: BTreeMap<String, serde_json::Value>,
    worker_args: &[&str],
) -> Run {
    runner::run(
        &experiment(root, settings),
        &worker(worker_args),
        &root.join(directory),
        false,
    )
    .unwrap()
}

#[test]
fn extracts_actual_bpp_from_mean_encoded_size() {
    let root = tempfile::tempdir().unwrap();
    let run = completed_run(root.path(), "run", BTreeMap::new(), &[]);
    let report = series::extract(&[run]).unwrap();
    let point = &report.rate_distortion[0].points[0];
    assert_eq!(point.mean_output_bytes, 4.0);
    assert_eq!(point.actual_bits_per_pixel, Some(8.0));
    assert_eq!(point.mse, 0.0);
    assert_eq!(point.psnr_db, None);
    assert_eq!(report.rate_distortion[0].coverage[0].statuses[0].batches, 5);
}

#[test]
fn rejects_invalid_runs_and_unknown_run_schema() {
    let root = tempfile::tempdir().unwrap();
    let mut run = completed_run(root.path(), "run", BTreeMap::new(), &[]);
    run.schema_version = SCHEMA_VERSION + 1;
    assert!(series::extract(&[run]).is_err());

    let mut malformed = completed_run(root.path(), "malformed", BTreeMap::new(), &[]);
    malformed.batches[0]
        .response
        .as_mut()
        .unwrap()
        .correctness
        .as_mut()
        .unwrap()
        .sample_count = 0;
    assert!(series::extract(&[malformed]).is_err());
}

#[test]
fn retains_unsupported_coverage_without_a_metric_point() {
    let root = tempfile::tempdir().unwrap();
    let run = completed_run(
        root.path(),
        "unsupported",
        BTreeMap::new(),
        &["--unsupported"],
    );
    let report = series::extract(&[run]).unwrap();
    let group = &report.rate_distortion[0];
    assert!(group.points.is_empty());
    assert_eq!(group.coverage[0].statuses.len(), 1);
    assert_eq!(
        group.coverage[0].statuses[0].status,
        BatchStatus::Unsupported
    );
    assert_eq!(group.coverage[0].statuses[0].batches, 5);
}

#[test]
fn groups_only_named_rate_knobs_and_retains_coding_family() {
    let root = tempfile::tempdir().unwrap();
    let settings = |target_bpp: f64, coding_family: &str| {
        BTreeMap::from([
            ("target_bpp".into(), json!(target_bpp)),
            ("coding_family".into(), json!(coding_family)),
        ])
    };
    let a = completed_run(root.path(), "a", settings(0.5, "reversible"), &[]);
    let b = completed_run(root.path(), "b", settings(1.0, "reversible"), &[]);
    let c = completed_run(root.path(), "c", settings(1.0, "irreversible"), &[]);
    let report = series::extract(&[a, b, c]).unwrap();
    assert_eq!(report.rate_distortion.len(), 2);
    assert!(
        report
            .rate_distortion
            .iter()
            .any(|group| group.points.len() == 2
                && group.identity.settings_excluding_rate_knobs["coding_family"] == "reversible")
    );
    assert_eq!(report.progress.len(), 3);
}

#[test]
fn static_html_escapes_worker_identity() {
    let root = tempfile::tempdir().unwrap();
    let mut run = completed_run(root.path(), "run", BTreeMap::new(), &[]);
    run.worker.definition.implementation = "<img src=x onerror=alert(1)>".into();
    run.worker.definition.source_identity = "<script>alert('source')</script>".into();
    let report = series::extract(&[run]).unwrap();
    let html = series::html(&report);
    assert!(html.contains("<svg"));
    assert!(!html.contains("<script>"));
    assert!(!html.contains("<img src"));
    assert!(html.contains("&lt;script&gt;"));
    assert!(html.contains("&lt;img src"));
}

#[test]
fn cli_writes_new_json_and_html_series_files() {
    let root = tempfile::tempdir().unwrap();
    let run = completed_run(root.path(), "run", BTreeMap::new(), &[]);
    let run_path = root.path().join("run");
    assert!(run_path.join("run.json").is_file());
    let points = root.path().join("points.json");
    let series_html = root.path().join("series.html");
    let binary = env!("CARGO_BIN_EXE_emuella-benchmark");
    assert!(
        Command::new(binary)
            .args([
                "points",
                run_path.to_str().unwrap(),
                points.to_str().unwrap()
            ])
            .status()
            .unwrap()
            .success()
    );
    assert!(
        Command::new(binary)
            .args([
                "series",
                series_html.to_str().unwrap(),
                run_path.to_str().unwrap(),
            ])
            .status()
            .unwrap()
            .success()
    );
    assert_eq!(
        serde_json::from_reader::<_, series::Series>(fs::File::open(points).unwrap())
            .unwrap()
            .rate_distortion[0]
            .points[0]
            .run
            .run_id,
        run.run_id
    );
    assert!(fs::read_to_string(series_html).unwrap().contains("<svg"));
}
