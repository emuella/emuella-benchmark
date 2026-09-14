#![cfg(feature = "classic-execution-diagnostics")]
use emuella_j2k as codec;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

#[test]
fn diagnostic_process_preserves_bytes_and_cannot_emit_headline_samples() {
    let root = tempfile::tempdir().unwrap();
    let raw: Vec<u8> = (0..129 * 131)
        .flat_map(|n| ((n * 7919 + n / 7) as u16).to_le_bytes())
        .collect();
    let raw_path = root.path().join("raw");
    std::fs::write(&raw_path, &raw).unwrap();
    let info = codec::ImageInfo::new(
        129,
        131,
        1,
        codec::SampleFormat::U16_LE,
        codec::ColorModel::Grayscale,
        codec::ComponentLayout::Interleaved,
    )
    .unwrap();
    let options = codec::EncodeOptions {
        format: codec::OutputFormat::J2kCodestream,
        decomposition_levels: 2,
        transform: codec::WaveletTransform::Reversible53,
        quality: codec::EncodeQuality::Lossless,
        ..Default::default()
    };
    let limits = codec::LosslessEncodeLimits {
        max_working_bytes: 768 * 1024 * 1024,
        max_output_bytes: 64 * 1024 * 1024,
    };
    for style in [0, 1] {
        let view = codec::ImageView::Interleaved {
            info: &info,
            samples: &raw,
            stride_bytes: 258,
        };
        let stream = if style == 0 {
            codec::encode_with_limits(view, &options, &limits)
        } else {
            codec::encode_lossless_bypass_with_limits(view, &options, &limits)
        }
        .unwrap();
        let stream_path = root.path().join(format!("style{style}.j2k"));
        std::fs::write(&stream_path, &stream).unwrap();
        for workers in [1, 8] {
            let request = json!({"codec":"emuella","operation":"encode","case_id":"authored","round":0,
                "width":129,"height":131,"components":1,"bits":16,"style":style,"workers":workers,"layout":"interleaved",
                "raw_path":raw_path,"raw_sha256":format!("{:x}", Sha256::digest(&raw)),"stream_path":stream_path,
                "stream_sha256":format!("{:x}",Sha256::digest(&stream)),"max_working_bytes":limits.max_working_bytes,
                "max_output_bytes":limits.max_output_bytes});
            let request_path = root.path().join("request.json");
            std::fs::write(&request_path, serde_json::to_vec(&request).unwrap()).unwrap();
            let child = std::process::Command::new(env!("CARGO_BIN_EXE_classic-compare-worker"))
                .arg(request_path)
                .output()
                .unwrap();
            assert!(
                child.status.success(),
                "{}",
                String::from_utf8_lossy(&child.stderr)
            );
            let response: Value = serde_json::from_slice(&child.stdout).unwrap();
            assert_eq!(response["exact"], true);
            assert_eq!(response["samples_ns"], json!([]));
            assert_eq!(response["stream_sha256"], request["stream_sha256"]);
            let d = &response["execution_diagnostic"];
            assert_eq!(d["effective_workers"], workers);
            assert!(d["peak_active_blocks"].as_u64().unwrap() <= workers);
            assert!(d["blocks"]["count"].as_u64().unwrap() > 0);
            assert!(
                d["active_block_ns"].as_u64().unwrap()
                    >= d["any_block_active_ns"].as_u64().unwrap()
            );
            assert!(
                response["diagnostic_facade_ns"].as_u64().unwrap()
                    >= d["stages_ns"]["total"].as_u64().unwrap()
            );
            assert!(
                d["allocation_peak_additional_requested_bytes"]
                    .as_u64()
                    .unwrap()
                    < limits.max_working_bytes
            );
        }
    }
}
