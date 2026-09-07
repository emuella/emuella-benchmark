use emuella_benchmark::journey::{Trace, assess};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

fn fixture() -> (Value, Vec<u8>) {
    let thresholds = serde_json::to_vec(&json!({
        "schema":"composed_journey_thresholds/1", "frozen_unix_ms":1,
        "workload_sha256":"a".repeat(64), "baseline_evidence_sha256":{"baseline":"b".repeat(64)},
        "rationale":"Authored validator fixture; no product performance claim",
        "require_hardware_gpu":true,
        "bounds":{"compressed_peak":{"unit":"bytes","boundary":"all client representations",
            "minimum":null,"maximum":1024.0}},
        "required_events":["cancel_acknowledged"]
    }))
    .unwrap();
    let trace = json!({
        "schema":"composed_journey_trace/1", "started_unix_ms":2, "completed":true,
        "failures":[], "identity":{
            "revisions":{"application":"1".repeat(40)},"builds":{"native":"2".repeat(64)},
            "inputs":{"source":"3".repeat(64)},"workload_sha256":"a".repeat(64)},
        "environment":{"hardware":"authored","operating_system":"authored","runtime":"authored",
            "gpu":"authored validator fixture","hardware_gpu":true},
        "cache_state":{"source_storage":"uncontrolled","server":"new","client_compressed":"empty",
            "client_decoded":"empty","gpu":"empty","initialisation":"authored test only"},
        "evidence_sha256":{"events":"4".repeat(64)},
        "observations":{"compressed_peak":{"value":1024.0,"unavailable_reason":null,
            "unit":"bytes","boundary":"all client representations"}},
        "events":[{"at_ms":1.0,"kind":"cancel_acknowledged","consumer":"pane",
            "source":"source","generation":1,"detail":"authored cancellation acknowledgement"}],
        "thresholds_sha256":format!("{:x}",Sha256::digest(&thresholds))
    });
    (trace, thresholds)
}

#[test]
fn qualifies_matched_complete_trace_and_retains_failures() {
    let (mut value, bytes) = fixture();
    let trace: Trace = serde_json::from_value(value.clone()).unwrap();
    assert!(assess(&trace, Some(&bytes)).unwrap().qualified);
    value["failures"] = json!(["worker disconnected"]);
    let trace = serde_json::from_value(value).unwrap();
    let result = assess(&trace, Some(&bytes)).unwrap();
    assert!(!result.qualified);
    assert_eq!(result.reasons, ["worker disconnected"]);
}

#[test]
fn missing_or_incomparable_evidence_never_passes() {
    let (original, bytes) = fixture();
    for (pointer, replacement) in [
        ("/completed", json!(false)),
        ("/environment/hardware_gpu", json!(false)),
        ("/events", json!([])),
        ("/observations/compressed_peak/value", json!(1025)),
        ("/observations/compressed_peak/unit", json!("KiB")),
        (
            "/observations/compressed_peak/boundary",
            json!("one request"),
        ),
    ] {
        let mut value = original.clone();
        *value.pointer_mut(pointer).unwrap() = replacement;
        let trace = serde_json::from_value(value).unwrap();
        assert!(
            !assess(&trace, Some(&bytes)).unwrap().qualified,
            "{pointer}"
        );
    }
    let mut value = original;
    value["observations"]["compressed_peak"]["value"] = Value::Null;
    value["observations"]["compressed_peak"]["unavailable_reason"] = json!("not instrumented");
    let trace = serde_json::from_value(value).unwrap();
    assert!(!assess(&trace, Some(&bytes)).unwrap().qualified);
}

#[test]
fn rejects_changed_thresholds_posthoc_freeze_and_bad_event_order() {
    let (original, bytes) = fixture();
    let trace: Trace = serde_json::from_value(original.clone()).unwrap();
    let mut changed = bytes.clone();
    changed.push(b' ');
    assert!(assess(&trace, Some(&changed)).is_err());
    for (pointer, replacement) in [
        ("/started_unix_ms", json!(1)),
        ("/schema", json!("composed_journey_trace/2")),
        ("/identity/revisions/application", json!("short")),
        ("/events/0/at_ms", json!(-1)),
        ("/events/0/source", json!("unknown")),
    ] {
        let mut value = original.clone();
        *value.pointer_mut(pointer).unwrap() = replacement;
        let trace = serde_json::from_value(value).unwrap();
        assert!(assess(&trace, Some(&bytes)).is_err(), "{pointer}");
    }
    let mut value = original;
    value["events"].as_array_mut().unwrap().push(json!({
        "at_ms":0.5,"kind":"later","consumer":"pane","source":"source",
        "generation":1,"detail":"out of order"}));
    assert!(assess(&serde_json::from_value(value).unwrap(), Some(&bytes)).is_err());
}

#[test]
fn admits_calibration_without_qualification_claim() {
    let (mut value, _) = fixture();
    value["thresholds_sha256"] = Value::Null;
    let result = assess(&serde_json::from_value(value).unwrap(), None).unwrap();
    assert!(result.admitted);
    assert!(!result.qualified);
}
