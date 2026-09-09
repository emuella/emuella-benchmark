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
            let value = if p < usize::from(components) {
                // Distinct first-pixel bands, both U16 endpoints and asymmetric bytes.
                [0, 65535, 0x1234, 0xabcd, 0x00ff, 0xff00, 32768, 32767][p % 8]
                    & ((1_u32 << precision) - 1) as u16
            } else {
                ((p * 977 + p * p * 3) & ((1_usize << precision) - 1)) as u16
            };
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
    let response = serde_json::from_slice(&fs::read(output).unwrap()).unwrap();
    emuella_benchmark::runner::validate_response(&request, &response).unwrap();
    response
}
#[test]
fn lossless_native_matrix_verifies_every_measured_output() {
    for binary in [
        env!("CARGO_BIN_EXE_emuella-worker"),
        env!("CARGO_BIN_EXE_openjpeg-worker"),
    ] {
        for components in [1, 3, 8] {
            for precision in [8, 16] {
                if components == 8 && precision == 8 {
                    continue;
                }
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
        response.diagnostics["observations"].get("execution_output_verified"),
        Some(&serde_json::json!(true)),
        "{:?}",
        response.diagnostics
    );
    assert!(
        response.diagnostics["observations"]["execution_work"]["code_blocks_decoded"]
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

#[test]
fn openjpeg_reports_unsupported_diagnostics_for_encode_and_decode() {
    let temp = tempfile::tempdir().unwrap();
    let mut c = case(temp.path(), 1, 8);
    let response = invoke(
        env!("CARGO_BIN_EXE_openjpeg-worker"),
        temp.path(),
        c.clone(),
        true,
    );
    assert_eq!(response.status, WorkerStatus::Ok);
    assert!(
        response.diagnostics["unsupported_reason"]
            .as_str()
            .unwrap()
            .contains("OpenJPEG")
    );
    let bytes = fs::read(&c.input.path).unwrap();
    let info = emuella_j2k::ImageInfo::new(
        c.image.width,
        c.image.height,
        1,
        emuella_j2k::SampleFormat::U8,
        emuella_j2k::ColorModel::Grayscale,
        emuella_j2k::ComponentLayout::Interleaved,
    )
    .unwrap();
    let stream = emuella_j2k::encode(
        emuella_j2k::ImageView::Interleaved {
            info: &info,
            samples: &bytes,
            stride_bytes: c.image.width as usize,
        },
        &emuella_j2k::EncodeOptions {
            format: emuella_j2k::OutputFormat::J2kCodestream,
            decomposition_levels: 2,
            ..Default::default()
        },
    )
    .unwrap();
    c.reference = Some(c.input.clone());
    c.input.path = temp.path().join("authored.j2k");
    c.input.sha256 = format!("{:x}", Sha256::digest(&stream));
    fs::write(&c.input.path, stream).unwrap();
    c.operation = Operation::Decode;
    c.settings.remove("decomposition_levels");
    let response = invoke(env!("CARGO_BIN_EXE_openjpeg-worker"), temp.path(), c, true);
    assert_eq!(response.status, WorkerStatus::Ok);
    assert!(
        response.diagnostics["unsupported_reason"]
            .as_str()
            .unwrap()
            .contains("OpenJPEG")
    );
    assert_eq!(response.samples_ns.len(), 2);
}

#[test]
fn exported_public_streams_verify_independently_and_never_overwrite() {
    for components in [1, 3, 8] {
        for precision in [8, 16] {
            if components == 8 && precision == 8 {
                continue;
            }
            let temp = tempfile::tempdir().unwrap();
            let dir = temp.path();
            let mut original = case(dir, components, precision);
            original.threads = 1;
            let request = WorkerRequest {
                schema_version: SCHEMA_VERSION,
                request_id: "export".into(),
                case: original.clone(),
                protocol: Protocol {
                    warmup: 0,
                    samples_per_batch: 1,
                    ..Default::default()
                },
                diagnostic: false,
            };
            let request_path = dir.join("export-request.json");
            let response_path = dir.join("export-response.json");
            let stream_path = dir.join("export.j2k");
            fs::write(&request_path, serde_json::to_vec(&request).unwrap()).unwrap();
            let export = || {
                Command::new(env!("CARGO_BIN_EXE_emuella-worker"))
                    .arg("--export-lossless")
                    .arg(&request_path)
                    .arg(&response_path)
                    .arg(&stream_path)
                    .output()
                    .unwrap()
            };
            assert!(export().status.success());
            let bytes = fs::read(&stream_path).unwrap();
            assert!(!export().status.success());
            assert_eq!(fs::read(&stream_path).unwrap(), bytes);
            let mut decode = original.clone();
            decode.operation = Operation::Decode;
            decode.reference = Some(original.input);
            decode.input = Asset {
                path: stream_path,
                sha256: format!("{:x}", Sha256::digest(&bytes)),
                provenance: BTreeMap::new(),
            };
            decode.settings.remove("decomposition_levels");
            for binary in [
                env!("CARGO_BIN_EXE_emuella-worker"),
                env!("CARGO_BIN_EXE_openjpeg-worker"),
            ] {
                let response = invoke(binary, dir, decode.clone(), false);
                assert_eq!(response.status, WorkerStatus::Ok, "{:?}", response.message);
                assert!(response.correctness.unwrap().exact);
            }
            let mut invalid = request;
            invalid.protocol.samples_per_batch = 2;
            fs::write(&request_path, serde_json::to_vec(&invalid).unwrap()).unwrap();
            let rejected = Command::new(env!("CARGO_BIN_EXE_emuella-worker"))
                .arg("--export-lossless")
                .arg(&request_path)
                .arg(dir.join("invalid.json"))
                .arg(dir.join("invalid.j2k"))
                .output()
                .unwrap();
            assert!(!rejected.status.success());
            assert!(!dir.join("invalid.j2k").exists());
        }
    }
}

#[test]
fn eight_band_workers_reject_out_of_scope_requests() {
    for binary in [
        env!("CARGO_BIN_EXE_emuella-worker"),
        env!("CARGO_BIN_EXE_openjpeg-worker"),
    ] {
        let temp = tempfile::tempdir().unwrap();
        for (components, precision) in [(8, 8), (2, 16), (7, 16), (9, 16)] {
            let c = case(temp.path(), components, precision);
            assert_eq!(
                invoke(binary, temp.path(), c, false).status,
                WorkerStatus::Unsupported
            );
        }
        for setting in [
            serde_json::json!(0),
            serde_json::json!(1),
            serde_json::json!(3),
        ] {
            let mut c = case(temp.path(), 8, 16);
            c.settings.insert("decomposition_levels".into(), setting);
            assert_eq!(
                invoke(binary, temp.path(), c, false).status,
                WorkerStatus::Unsupported
            );
        }
        let mut c = case(temp.path(), 8, 16);
        c.settings.insert("coding".into(), serde_json::json!("ht"));
        assert_eq!(
            invoke(binary, temp.path(), c, false).status,
            WorkerStatus::Unsupported
        );
        let mut c = case(temp.path(), 8, 16);
        c.output.lossless = false;
        c.output.minimum_psnr_db = Some(0.0);
        c.settings.insert("target_bpp".into(), serde_json::json!(1));
        assert_eq!(
            invoke(binary, temp.path(), c, false).status,
            WorkerStatus::Unsupported
        );
    }
}

#[test]
fn independent_openjpeg_msi_stream_decodes_exactly_and_rejects_profile_changes() {
    unsafe extern "C" {
        fn benchmark_openjpeg_encode(
            samples: *const i32,
            w: u32,
            h: u32,
            components: u32,
            bits: u32,
            levels: i32,
            lossless: i32,
            ratio: f64,
            threads: i32,
            out: *mut *mut u8,
            len: *mut usize,
        ) -> i32;
        fn benchmark_openjpeg_free(p: *mut std::ffi::c_void);
    }
    let temp = tempfile::tempdir().unwrap();
    let dir = temp.path();
    let mut c = case(dir, 8, 16);
    let values =
        emuella_benchmark_workers::raw(&fs::read(&c.input.path).unwrap(), &c.image).unwrap();
    let mut out = std::ptr::null_mut();
    let mut len = 0;
    // Authored input stays borrowed; the public-API adapter allocation is freed once.
    let stream = unsafe {
        assert_eq!(
            benchmark_openjpeg_encode(
                values.as_ptr(),
                33,
                29,
                8,
                16,
                2,
                1,
                1.0,
                1,
                &mut out,
                &mut len
            ),
            1
        );
        let stream = std::slice::from_raw_parts(out, len).to_vec();
        benchmark_openjpeg_free(out.cast());
        stream
    };
    emuella_benchmark_workers::msi::validate_stream(&stream, &c.image).unwrap();
    c.reference = Some(c.input.clone());
    c.input.path = dir.join("independent.j2k");
    c.input.sha256 = format!("{:x}", Sha256::digest(&stream));
    fs::write(&c.input.path, &stream).unwrap();
    c.operation = Operation::Decode;
    c.settings.remove("decomposition_levels");
    for binary in [
        env!("CARGO_BIN_EXE_emuella-worker"),
        env!("CARGO_BIN_EXE_openjpeg-worker"),
    ] {
        let response = invoke(binary, dir, c.clone(), false);
        assert_eq!(response.status, WorkerStatus::Ok, "{:?}", response.message);
        assert!(response.correctness.unwrap().exact);
        // Header profile mutations must be rejected before entering either timer.
        for offset in [74, 75, 78, 79] {
            let mut changed = stream.clone();
            changed[offset] ^= 1;
            fs::write(&c.input.path, &changed).unwrap();
            let mut malformed = c.clone();
            malformed.input.sha256 = format!("{:x}", Sha256::digest(&changed));
            let response = invoke(binary, dir, malformed, false);
            assert_eq!(response.status, WorkerStatus::Unsupported);
            assert!(response.samples_ns.is_empty());
        }
        fs::write(&c.input.path, &stream).unwrap();
    }
}
