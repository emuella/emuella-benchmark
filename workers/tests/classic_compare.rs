#![cfg(all(
    feature = "emuella",
    feature = "openjpeg",
    feature = "classic-compare",
    not(feature = "classic-encode-sampling"),
    not(feature = "classic-execution-diagnostics"),
    not(feature = "classic-allocation-diagnostics"),
    not(feature = "classic-parallel-diagnostics")
))]
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::process::Command;
fn invoke(root: &std::path::Path, request: &Value) -> std::process::Output {
    let path = root.join("request.json");
    std::fs::write(&path, serde_json::to_vec(request).unwrap()).unwrap();
    Command::new(env!("CARGO_BIN_EXE_classic-compare-worker"))
        .arg(path)
        .output()
        .unwrap()
}
fn success(root: &std::path::Path, request: &Value) -> Value {
    let out = invoke(root, request);
    assert!(
        out.status.success(),
        "{request}: {}",
        String::from_utf8_lossy(&out.stderr)
    );
    let v: Value = serde_json::from_slice(&out.stdout).unwrap();
    assert_eq!(v["exact"], true);
    assert_eq!(
        v["samples_ns"].as_array().unwrap().len(),
        usize::from(request["operation"] != "prepare")
    );
    v
}
#[test]
fn authored_profiles_cross_decode_and_deterministic_encode() {
    let root = tempfile::tempdir().unwrap();
    for (components, bits) in [(1, 8), (1, 16), (3, 8), (3, 16), (8, 16)] {
        let raw: Vec<u8> = (0..19 * 17 * components)
            .flat_map(|n| {
                let v = ((n * 7919 + n / 7 * 13) % (1_u32 << bits)) as u16;
                if bits == 8 {
                    vec![v as u8]
                } else {
                    v.to_le_bytes().to_vec()
                }
            })
            .collect();
        std::fs::write(root.path().join("raw"), &raw).unwrap();
        for style in [0, 1] {
            for workers in [1, 8] {
                for source in ["emuella", "openjpeg"] {
                    let stream_path = root.path().join(format!(
                        "{components}-{bits}-{style}-{workers}-{source}.j2k"
                    ));
                    let mut r = json!({"codec":source,"operation":"prepare","case_id":"authored","round":0,"width":19,"height":17,
                "components":components,"bits":bits,"style":style,"workers":workers,"layout":"interleaved",
                "raw_path":root.path().join("raw"),"raw_sha256":format!("{:x}",Sha256::digest(&raw)),"stream_path":stream_path,
                "max_working_bytes":4294967296_u64,"max_output_bytes":1048576});
                    let prepared = success(root.path(), &r);
                    assert!(
                        !invoke(root.path(), &r).status.success(),
                        "prepare must not overwrite"
                    );
                    r["stream_sha256"] = prepared["stream_sha256"].clone();
                    r["operation"] = json!("encode");
                    success(root.path(), &r);
                    r["operation"] = json!("decode");
                    for decoder in ["emuella", "openjpeg"] {
                        r["codec"] = json!(decoder);
                        success(root.path(), &r);
                    }
                    r["style"] = json!(1 - style);
                    assert!(
                        !invoke(root.path(), &r).status.success(),
                        "actual COD style must match"
                    );
                    r["style"] = json!(style);
                    r["stream_sha256"] = json!("0".repeat(64));
                    assert!(
                        !invoke(root.path(), &r).status.success(),
                        "stream digest must match"
                    );
                }
            }
        }
    }
}
#[test]
fn authored_existing_reference_preflight_uses_encode_without_changing_stream() {
    let root = tempfile::tempdir().unwrap();
    let raw = vec![17_u8; 19 * 17];
    let prepared = root.path().join("prepared");
    let streams = root.path().join("stream-root");
    std::fs::create_dir(&prepared).unwrap();
    std::fs::create_dir(&streams).unwrap();
    let raw_path = prepared.join("authored.raw");
    std::fs::write(&raw_path, &raw).unwrap();
    let stream_path = streams.join("streams/authored-emuella-s0.j2k");
    std::fs::create_dir(stream_path.parent().unwrap()).unwrap();
    let raw_sha256 = format!("{:x}", Sha256::digest(&raw));
    let prepare = json!({"codec":"emuella","operation":"prepare","case_id":"authored","round":0,
        "width":19,"height":17,"components":1,"bits":8,"style":0,"workers":1,
        "layout":"interleaved","raw_path":raw_path,"raw_sha256":raw_sha256,
        "stream_path":stream_path,"max_working_bytes":4294967296_u64,"max_output_bytes":1048576});
    let prepared_response = success(root.path(), &prepare);
    assert!(!invoke(root.path(), &prepare).status.success());
    let original_stream = std::fs::read(&stream_path).unwrap();
    let stream_sha256 = prepared_response["stream_sha256"].as_str().unwrap();
    let identity = json!({"case_id":"authored","origin":"emuella","style":0,
        "raw_sha256":raw_sha256,"stream_path":stream_path,"stream_sha256":stream_sha256});
    let script = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join("scripts/classic-diagnosis-request.py");
    let mut ordinary_samples = Vec::new();
    for kind in ["preflight", "ordinary"] {
        let config = json!({"kind":kind,"asset":{"id":"authored","path":"authored.raw",
            "sha256":raw_sha256,"image":{"width":19,"height":17,"components":1,"precision":8}},
            "prepared":prepared,"streams":streams,"origin":"emuella","codec":"emuella",
            "style":0,"workers":1,"round":0,"stream_identity":identity});
        let config_path = root.path().join("metadata.json");
        std::fs::write(&config_path, serde_json::to_vec(&config).unwrap()).unwrap();
        let dry_run = Command::new("python3")
            .arg(&script)
            .arg("--config")
            .arg(&config_path)
            .output()
            .unwrap();
        assert!(
            dry_run.status.success(),
            "{}",
            String::from_utf8_lossy(&dry_run.stderr)
        );
        let call: Value = serde_json::from_slice(&dry_run.stdout).unwrap();
        assert_eq!(call["request"]["operation"], "encode");
        assert_eq!(call["request"]["stream_sha256"], stream_sha256);
        let response = success(root.path(), &call["request"]);
        assert_eq!(response["samples_ns"].as_array().unwrap().len(), 1);
        if call["timing_eligible"] == true {
            ordinary_samples.extend(response["samples_ns"].as_array().unwrap().iter().cloned());
        }
        assert_eq!(std::fs::read(&stream_path).unwrap(), original_stream);
    }
    assert_eq!(ordinary_samples.len(), 1);
    assert_eq!(
        format!("{:x}", Sha256::digest(&original_stream)),
        stream_sha256
    );
    let mut incorrect = prepare.clone();
    incorrect["operation"] = json!("encode");
    incorrect["stream_sha256"] = json!("0".repeat(64));
    assert!(!invoke(root.path(), &incorrect).status.success());
    assert_eq!(std::fs::read(&stream_path).unwrap(), original_stream);
}
#[test]
fn rejects_unknown_fields_hashes_and_unsupported_settings() {
    let root = tempfile::tempdir().unwrap();
    let raw = vec![0; 16];
    std::fs::write(root.path().join("raw"), &raw).unwrap();
    let base = json!({"codec":"emuella","operation":"prepare","case_id":"reject","round":0,"width":4,"height":4,
        "components":1,"bits":8,"style":0,"workers":1,"layout":"interleaved","raw_path":root.path().join("raw"),
        "raw_sha256":format!("{:x}",Sha256::digest(&raw)),"stream_path":root.path().join("stream"),
        "max_working_bytes":4294967296_u64,"max_output_bytes":1048576});
    for (key, value) in [
        ("unknown", json!(0)),
        ("style", json!(2)),
        ("workers", json!(3)),
        ("layout", json!("planar")),
        ("raw_sha256", json!("0".repeat(64))),
        ("components", json!(8)),
        ("width", json!(3)),
        ("max_working_bytes", json!(1)),
        ("max_output_bytes", json!(1)),
    ] {
        let mut r = base.clone();
        r[key] = value;
        assert!(
            !invoke(root.path(), &r).status.success(),
            "must reject {key}"
        );
        assert!(!root.path().join("stream").exists());
    }
}
