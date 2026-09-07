//! Authored inputs only; codec binaries are tested as isolated protocol processes.
use emuella_benchmark::contract::*;
use sha2::{Digest, Sha256};
use std::{collections::BTreeMap, fs, process::Command};

fn case(dir: &std::path::Path, components: u16, precision: u8) -> Case {
    let image = ImageSpec {
        width: 33,
        height: 29,
        components,
        precision,
        signed: false,
    };
    let samples: Vec<u8> = (0..image.sample_count().unwrap())
        .flat_map(|p| {
            let value = ((p * 977 + p * p * 3) & ((1_usize << precision) - 1)) as u16;
            if precision == 8 {
                vec![value as u8]
            } else {
                value.to_le_bytes().to_vec()
            }
        })
        .collect();
    let path = dir.join("source.raw");
    fs::write(&path, &samples).unwrap();
    Case {
        id: "authored".into(),
        input: Asset {
            path,
            sha256: format!("{:x}", Sha256::digest(&samples)),
            provenance: BTreeMap::new(),
        },
        reference: None,
        image: image.clone(),
        operation: Operation::Encode,
        settings: BTreeMap::from([
            ("coding".into(), serde_json::json!("classic")),
            ("decomposition_levels".into(), serde_json::json!(2)),
        ]),
        threads: 2,
        output: OutputSemantics {
            colour: "native".into(),
            layout: "interleaved".into(),
            container: "j2k".into(),
            lossless: true,
            reduction: 0,
            region: None,
            image,
            minimum_psnr_db: None,
        },
    }
}
fn invoke(binary: &str, dir: &std::path::Path, case: Case, diagnostic: bool) -> WorkerResponse {
    let request = WorkerRequest {
        schema_version: SCHEMA_VERSION,
        request_id: "test".into(),
        case,
        protocol: Protocol {
            warmup: 1,
            samples_per_batch: 2,
            ..Default::default()
        },
        diagnostic,
    };
    let input = dir.join("request.json");
    let output = dir.join("response.json");
    fs::write(&input, serde_json::to_vec(&request).unwrap()).unwrap();
    assert!(
        Command::new(binary)
            .arg("--request")
            .arg(input)
            .arg("--response")
            .arg(&output)
            .status()
            .unwrap()
            .success()
    );
    serde_json::from_slice(&fs::read(output).unwrap()).unwrap()
}
#[test]
fn lossless_native_matrix_verifies_every_measured_output() {
    for binary in [
        env!("CARGO_BIN_EXE_emuella-worker"),
        env!("CARGO_BIN_EXE_openjpeg-worker"),
    ] {
        for components in [1, 3] {
            for precision in [8, 16] {
                let temp = tempfile::tempdir().unwrap();
                let c = case(temp.path(), components, precision);
                let response = invoke(binary, temp.path(), c.clone(), false);
                assert_eq!(response.status, WorkerStatus::Ok, "{:?}", response.message);
                assert_eq!(response.samples_ns.len(), 2);
                let mct = if binary == env!("CARGO_BIN_EXE_emuella-worker") && components == 3 {
                    "reversible_colour_transform"
                } else {
                    "none"
                };
                assert_eq!(
                    response.diagnostics["encode_profile"]["multiple_component_transform"],
                    mct
                );
                assert_eq!(
                    response.diagnostics["encode_profile"]["decomposition_levels"],
                    2
                );
                let metrics = response.correctness.unwrap();
                assert!(metrics.exact);
                assert_eq!(
                    metrics.sample_count,
                    c.image.sample_count().unwrap() as u64 * 2
                );
                assert!(response.peak_rss_bytes.is_some_and(|x| x > 0));
            }
        }
    }
}
#[test]
fn native_workers_reject_unknown_settings_and_digest_changes() {
    for binary in [
        env!("CARGO_BIN_EXE_emuella-worker"),
        env!("CARGO_BIN_EXE_openjpeg-worker"),
    ] {
        let temp = tempfile::tempdir().unwrap();
        let mut c = case(temp.path(), 1, 8);
        c.settings
            .insert("imaginary_setting".into(), serde_json::json!(true));
        assert_eq!(
            invoke(binary, temp.path(), c, false).status,
            WorkerStatus::Unsupported
        );
        let mut c = case(temp.path(), 1, 8);
        c.settings.remove("decomposition_levels");
        assert_eq!(
            invoke(binary, temp.path(), c, false).status,
            WorkerStatus::Unsupported
        );
        let mut c = case(temp.path(), 1, 8);
        c.input.sha256 = "0".repeat(64);
        assert_eq!(
            invoke(binary, temp.path(), c, false).status,
            WorkerStatus::Failed
        );
    }
}
#[test]
fn diagnostics_execute_and_verify_actual_work_separately() {
    let temp = tempfile::tempdir().unwrap();
    let c = case(temp.path(), 1, 8);
    let response = invoke(env!("CARGO_BIN_EXE_emuella-worker"), temp.path(), c, true);
    assert_eq!(response.status, WorkerStatus::Ok, "{:?}", response.message);
    assert_eq!(
        response.diagnostics.get("execution_output_verified"),
        Some(&serde_json::json!(true)),
        "{:?}",
        response.diagnostics
    );
    assert!(
        response.diagnostics["execution_work"]["code_blocks_decoded"]
            .as_u64()
            .unwrap()
            > 0
    );
    assert_eq!(response.samples_ns.len(), 2);
}
#[test]
fn unattainable_rate_is_distinct_from_unsupported_profile() {
    let temp = tempfile::tempdir().unwrap();
    let mut c = case(temp.path(), 1, 8);
    c.output.lossless = false;
    c.output.minimum_psnr_db = Some(0.0);
    c.settings
        .insert("target_bpp".into(), serde_json::json!(0.125));
    let response = invoke(env!("CARGO_BIN_EXE_emuella-worker"), temp.path(), c, false);
    assert_eq!(
        response.status,
        WorkerStatus::UnattainableRate,
        "{:?}",
        response.message
    );
    assert!(response.samples_ns.is_empty());
    assert!(response.correctness.is_none());
}

#[test]
fn a_later_corrupt_output_invalidates_the_whole_batch() {
    let temp = tempfile::tempdir().unwrap();
    let c = case(temp.path(), 1, 8);
    let samples =
        emuella_benchmark_workers::raw(&fs::read(&c.input.path).unwrap(), &c.image).unwrap();
    let request = WorkerRequest {
        schema_version: SCHEMA_VERSION,
        request_id: "late-corruption".into(),
        case: c,
        protocol: Protocol {
            warmup: 1,
            samples_per_batch: 3,
            ..Default::default()
        },
        diagnostic: false,
    };
    let mut calls = 0;
    let result = emuella_benchmark_workers::run_samples(
        &request,
        || {
            calls += 1;
            let mut output = samples.clone();
            if calls == 3 {
                output[0] ^= 1;
            }
            Ok(output)
        },
        |output| Ok((output, samples.len() as u64)),
    );
    assert!(result.unwrap_err().contains("lossless output differs"));
    assert_eq!(calls, 3);
}
