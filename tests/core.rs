use emuella_benchmark::{
    compare::{Verdict, compare, validate_run},
    contract::*,
    runner,
};
use std::{collections::BTreeMap, fs, path::Path};
fn experiment(root: &Path) -> Experiment {
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
        schema_version: 1,
        name: "fixture".into(),
        protocol: Protocol {
            rounds: 5,
            samples_per_batch: 2,
            warmup: 1,
            timeout_ms: 1000,
            ..Protocol::default()
        },
        environment_tags: BTreeMap::new(),
        cases: vec![Case {
            id: "fixture".into(),
            input: Asset {
                sha256: runner::sha256_file(&path).unwrap(),
                path,
                provenance: BTreeMap::new(),
            },
            reference: None,
            image: image.clone(),
            operation: Operation::Encode,
            settings: BTreeMap::new(),
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
        args: args.iter().map(|x| (*x).into()).collect(),
        implementation: "synthetic".into(),
        source_identity: "project-authored-test".into(),
        artefacts: vec![],
    }
}
fn fixture_run() -> (tempfile::TempDir, Run) {
    let root = tempfile::tempdir().unwrap();
    let e = experiment(root.path());
    let run = runner::run(&e, &worker(&[]), &root.path().join("run"), false).unwrap();
    (root, run)
}
fn set_samples(run: &mut Run, means: &[u64]) {
    for (batch, &mean) in run.batches.iter_mut().zip(means) {
        batch.response.as_mut().unwrap().samples_ns.fill(mean);
    }
}
#[test]
fn isolated_worker_retains_raw_samples_and_refuses_overwrite() {
    let (root, run) = fixture_run();
    validate_run(&run).unwrap();
    assert_eq!(run.batches.len(), 5);
    assert!(run.batches.iter().all(|x| x.status == BatchStatus::Ok));
    assert_eq!(
        run.batches[0]
            .response
            .as_ref()
            .unwrap()
            .correctness
            .as_ref()
            .unwrap()
            .sample_count,
        8
    );
    assert!(root.path().join("run/manifest.json").is_file());
    assert!(
        root.path()
            .join("run/batches/00000000/request.json")
            .is_file()
    );
    assert!(
        runner::run(
            &run.experiment,
            &worker(&[]),
            &root.path().join("run"),
            false
        )
        .is_err()
    );
}
#[test]
fn slowdown_noise_and_equivalence_have_distinct_verdicts() {
    let (_root, mut baseline) = fixture_run();
    set_samples(&mut baseline, &[1000; 5]);
    let mut candidate = baseline.clone();
    set_samples(&mut candidate, &[1400; 5]);
    assert_eq!(compare(&baseline, &candidate).verdict, Verdict::Regressed);
    set_samples(&mut candidate, &[600; 5]);
    assert_eq!(compare(&baseline, &candidate).verdict, Verdict::Improved);
    set_samples(&mut candidate, &[1000; 5]);
    assert_eq!(compare(&baseline, &candidate).verdict, Verdict::Equivalent);
    set_samples(&mut candidate, &[100, 3000, 100, 3000, 100]);
    assert_eq!(
        compare(&baseline, &candidate).verdict,
        Verdict::Inconclusive
    );
}
#[test]
fn missing_coverage_and_semantic_mismatches_never_improve() {
    let (_root, baseline) = fixture_run();
    let mut candidate = baseline.clone();
    candidate.batches.pop();
    assert_eq!(compare(&baseline, &candidate).verdict, Verdict::Invalid);
    let mut candidate = baseline.clone();
    candidate.experiment.cases[0].threads = 2;
    // Fix applied request too: a valid but semantically different workload.
    for batch in &mut candidate.batches {
        batch.response.as_mut().unwrap().applied_case.threads = 2;
    }
    assert_eq!(
        compare(&baseline, &candidate).verdict,
        Verdict::NotComparable
    );
    let mut candidate = baseline.clone();
    candidate.machine.cpu.push_str(" different");
    assert_eq!(
        compare(&baseline, &candidate).verdict,
        Verdict::NotComparable
    );
    let mut candidate = baseline.clone();
    candidate.harness_sha256 = "1".repeat(64);
    assert_eq!(
        compare(&baseline, &candidate).verdict,
        Verdict::NotComparable
    );
    let mut candidate = baseline.clone();
    candidate.diagnostic = true;
    for batch in &mut candidate.batches {
        batch.response.as_mut().unwrap().diagnostics.insert(
            "unsupported_reason".into(),
            "synthetic worker has no instrumentation".into(),
        );
    }
    assert_eq!(
        compare(&baseline, &candidate).verdict,
        Verdict::NotComparable
    );
    let mut candidate = baseline.clone();
    candidate.worker.definition.source_identity = "new revision".into();
    assert_ne!(
        compare(&baseline, &candidate).verdict,
        Verdict::NotComparable
    );
}
#[test]
fn worker_failures_are_retained_and_cannot_be_compared_away() {
    let root = tempfile::tempdir().unwrap();
    let mut e = experiment(root.path());
    for (flag, status) in [
        ("--corrupt", BatchStatus::Invalid),
        ("--unattainable", BatchStatus::UnattainableRate),
        ("--crash", BatchStatus::Crashed),
        ("--bad-schema", BatchStatus::Invalid),
        ("--unsupported", BatchStatus::Unsupported),
        ("--timeout", BatchStatus::Timeout),
    ] {
        e.protocol.timeout_ms = if flag == "--timeout" { 20 } else { 1000 };
        let run = runner::run(&e, &worker(&[flag]), &root.path().join(flag), false).unwrap();
        assert!(
            run.batches.iter().all(|x| x.status == status),
            "{flag}: {:?}",
            run.batches
        );
        assert!(matches!(
            compare(&run, &run).verdict,
            Verdict::Invalid | Verdict::NotComparable
        ));
    }
}
#[test]
fn interleaving_uses_actual_timed_delay_and_correct_order() {
    let root = tempfile::tempdir().unwrap();
    let e = experiment(root.path());
    let (baseline, candidate) = runner::run_pair(
        &e,
        &worker(&["--delay-ms", "2"]),
        &worker(&["--delay-ms", "15"]),
        &root.path().join("pair"),
    )
    .unwrap();
    assert_eq!(baseline.pair_id, candidate.pair_id);
    for round in 0..5 {
        let a = &baseline.batches[round];
        let b = &candidate.batches[round];
        assert_eq!(a.execution_index.abs_diff(b.execution_index), 1);
        assert_eq!(a.execution_index < b.execution_index, round % 2 == 0);
    }
    assert_eq!(compare(&baseline, &candidate).verdict, Verdict::Regressed);
}
#[test]
fn schemas_and_digest_are_strict() {
    let root = tempfile::tempdir().unwrap();
    let mut e = experiment(root.path());
    e.schema_version = 2;
    assert!(e.validate().is_err());
    e.schema_version = 1;
    let mut json = serde_json::to_value(&e).unwrap();
    json["surprise"] = true.into();
    assert!(serde_json::from_value::<Experiment>(json).is_err());
    fs::write(&e.cases[0].input.path, [9_u8; 4]).unwrap();
    assert!(runner::run(&e, &worker(&[]), &root.path().join("run"), false).is_err());
}
#[test]
fn malformed_correctness_is_invalid_even_in_stored_results() {
    let (_root, baseline) = fixture_run();
    let mut candidate = baseline.clone();
    candidate.batches[0]
        .response
        .as_mut()
        .unwrap()
        .correctness
        .as_mut()
        .unwrap()
        .sample_count = 1;
    assert_eq!(compare(&baseline, &candidate).verdict, Verdict::Invalid);
}

#[test]
fn static_report_escapes_untrusted_run_and_case_labels() {
    let (_root, mut baseline) = fixture_run();
    baseline.run_id = "<script>alert('run')</script>".into();
    baseline.experiment.cases[0].id = "<img src=x onerror=alert(1)>".into();
    for batch in &mut baseline.batches {
        batch.case_id = baseline.experiment.cases[0].id.clone();
        let response = batch.response.as_mut().unwrap();
        response.request_id = format!("{}-{}", baseline.run_id, batch.execution_index);
        response.applied_case.id = batch.case_id.clone();
    }
    let comparison = compare(&baseline, &baseline);
    let html = emuella_benchmark::report::html(&comparison);
    assert!(!html.contains("<script>"));
    assert!(!html.contains("<img src"));
    assert!(html.contains("&lt;script&gt;"));
    assert!(html.contains("&lt;img src"));
    assert!(html.contains("Timing") || html.contains("timing"));
    assert!(
        comparison.cases[0]
            .baseline_measurements
            .as_ref()
            .unwrap()
            .correctness
            .exact
    );
}

#[test]
fn cli_compares_stored_runs_as_machine_readable_json() {
    let (root, mut baseline) = fixture_run();
    set_samples(&mut baseline, &[1000; 5]);
    let mut candidate = baseline.clone();
    set_samples(&mut candidate, &[1500; 5]);
    let a = root.path().join("a.json");
    let b = root.path().join("b.json");
    runner::write_json_new(&a, &baseline).unwrap();
    runner::write_json_new(&b, &candidate).unwrap();
    let output = std::process::Command::new(env!("CARGO_BIN_EXE_emuella-benchmark"))
        .arg("compare")
        .arg(a)
        .arg(b)
        .arg("--json")
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    let comparison: emuella_benchmark::compare::Comparison =
        serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(comparison.verdict, Verdict::Regressed);
}

#[test]
fn response_validation_rejects_invalid_request_before_arithmetic() {
    let (_root, run) = fixture_run();
    let response = run.batches[0].response.as_ref().unwrap().clone();
    let mut request = WorkerRequest {
        schema_version: 1,
        request_id: response.request_id.clone(),
        case: response.applied_case.clone(),
        protocol: run.experiment.protocol.clone(),
        diagnostic: false,
    };
    request.case.output.image.precision = 32;
    let mut invalid_response = response.clone();
    invalid_response.applied_case = request.case.clone();
    assert!(runner::validate_response(&request, &invalid_response).is_err());
    request.case = response.applied_case.clone();
    request.schema_version = 2;
    assert!(runner::validate_response(&request, &response).is_err());
}

#[cfg(target_os = "linux")]
#[test]
fn timeout_stops_codec_descendants_without_an_external_kill_program() {
    let root = tempfile::tempdir().unwrap();
    let script = root.path().join("descendant.py");
    fs::write(&script, "import pathlib, subprocess, time\nchild = subprocess.Popen(['sleep', '60'])\nwith pathlib.Path(__file__).with_suffix('.pids').open('a') as output:\n output.write(str(child.pid) + '\\n')\ntime.sleep(60)\n").unwrap();
    let definition = WorkerDefinition {
        executable: "/usr/bin/python3".into(),
        args: vec![script.to_string_lossy().into_owned()],
        implementation: "synthetic-descendant".into(),
        source_identity: "project-authored-process-cleanup-probe".into(),
        artefacts: vec![script.clone()],
    };
    let mut exp = experiment(root.path());
    exp.protocol.timeout_ms = 500;
    let run = runner::run(&exp, &definition, &root.path().join("run"), false).unwrap();
    assert!(run.batches.iter().all(|b| b.status == BatchStatus::Timeout));
    let ids = fs::read_to_string(script.with_extension("pids")).unwrap();
    assert!(!ids.trim().is_empty());
    for pid in ids.lines() {
        let stat = fs::read_to_string(format!("/proc/{pid}/stat"));
        if let Ok(stat) = stat {
            // A killed descendant may briefly await its system reaper as a zombie.
            assert_eq!(stat.split_whitespace().nth(2), Some("Z"));
        }
    }
}

#[test]
fn diagnostic_success_requires_observations_or_explicit_unsupported_reason() {
    let (_root, run) = fixture_run();
    for operation in [Operation::Encode, Operation::Decode] {
        let mut response = run.batches[0].response.as_ref().unwrap().clone();
        response.applied_case.operation = operation;
        if response.applied_case.operation == Operation::Decode {
            response.applied_case.reference = Some(response.applied_case.input.clone());
        }
        let request = WorkerRequest {
            schema_version: 1,
            request_id: response.request_id.clone(),
            case: response.applied_case.clone(),
            protocol: run.experiment.protocol.clone(),
            diagnostic: true,
        };
        for diagnostics in [
            serde_json::json!({}),
            serde_json::json!({"encode_profile": {"coding": "classic"}}),
            serde_json::json!({"observations": {}, "unsupported_reason": "  "}),
            serde_json::json!({"observations": null, "unsupported_reason": 42}),
        ] {
            response.diagnostics = serde_json::from_value(diagnostics).unwrap();
            assert!(runner::validate_response(&request, &response).is_err());
        }
        for diagnostics in [
            serde_json::json!({"observations": {"execution_ns": 10}}),
            serde_json::json!({"unsupported_reason": "codec instrumentation is unavailable"}),
        ] {
            response.diagnostics = serde_json::from_value(diagnostics).unwrap();
            assert!(runner::validate_response(&request, &response).is_ok());
        }
    }
}
