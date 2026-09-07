//! Separate admission for persistent, composed application journeys.
use crate::Result;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Identity {
    pub revisions: BTreeMap<String, String>,
    pub builds: BTreeMap<String, String>,
    pub inputs: BTreeMap<String, String>,
    pub workload_sha256: String,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Environment {
    pub hardware: String,
    pub operating_system: String,
    pub runtime: String,
    pub gpu: String,
    pub hardware_gpu: bool,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CacheState {
    pub source_storage: String,
    pub server: String,
    pub client_compressed: String,
    pub client_decoded: String,
    pub gpu: String,
    pub initialisation: String,
}

/// Measurement boundaries and units are part of comparability, not display labels.
#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Observation {
    pub value: Option<f64>,
    pub unavailable_reason: Option<String>,
    pub unit: String,
    pub boundary: String,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Event {
    pub at_ms: f64,
    pub kind: String,
    pub consumer: String,
    pub source: String,
    pub generation: u64,
    pub detail: String,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Trace {
    pub schema: String,
    pub started_unix_ms: u64,
    pub completed: bool,
    pub failures: Vec<String>,
    pub identity: Identity,
    pub environment: Environment,
    pub cache_state: CacheState,
    pub evidence_sha256: BTreeMap<String, String>,
    pub observations: BTreeMap<String, Observation>,
    pub events: Vec<Event>,
    pub thresholds_sha256: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Bound {
    pub unit: String,
    pub boundary: String,
    pub minimum: Option<f64>,
    pub maximum: Option<f64>,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Thresholds {
    pub schema: String,
    pub frozen_unix_ms: u64,
    pub workload_sha256: String,
    pub baseline_evidence_sha256: BTreeMap<String, String>,
    pub rationale: String,
    pub require_hardware_gpu: bool,
    pub bounds: BTreeMap<String, Bound>,
    pub required_events: BTreeSet<String>,
}

#[derive(Debug, Serialize)]
pub struct Assessment {
    pub admitted: bool,
    pub qualified: bool,
    pub reasons: Vec<String>,
}

fn ensure(condition: bool, message: &str) -> Result<()> {
    if !condition {
        return Err(message.into());
    }
    Ok(())
}

fn digest(value: &str, length: usize) -> bool {
    value.len() == length && value.bytes().all(|b| b.is_ascii_hexdigit())
}

fn identities(values: &BTreeMap<String, String>, length: usize) -> bool {
    !values.is_empty()
        && values
            .iter()
            .all(|(name, value)| !name.trim().is_empty() && digest(value, length))
}

fn nonnegative(value: f64) -> bool {
    value.is_finite() && value >= 0.0
}

pub fn assess(trace: &Trace, threshold_bytes: Option<&[u8]>) -> Result<Assessment> {
    ensure(
        trace.schema == "composed_journey_trace/1",
        "unknown trace schema",
    )?;
    ensure(
        identities(&trace.identity.revisions, 40)
            && identities(&trace.identity.builds, 64)
            && identities(&trace.identity.inputs, 64)
            && digest(&trace.identity.workload_sha256, 64)
            && identities(&trace.evidence_sha256, 64),
        "missing or malformed source/build/input/workload/evidence identity",
    )?;
    ensure(
        [
            &trace.environment.hardware,
            &trace.environment.operating_system,
            &trace.environment.runtime,
            &trace.environment.gpu,
            &trace.cache_state.source_storage,
            &trace.cache_state.server,
            &trace.cache_state.client_compressed,
            &trace.cache_state.client_decoded,
            &trace.cache_state.gpu,
            &trace.cache_state.initialisation,
        ]
        .iter()
        .all(|s| !s.trim().is_empty()),
        "environment and cache initialisation must be explicit",
    )?;
    ensure(!trace.observations.is_empty(), "empty observations")?;
    for (name, observation) in &trace.observations {
        ensure(
            !name.trim().is_empty()
                && !observation.unit.trim().is_empty()
                && !observation.boundary.trim().is_empty(),
            "measurement name, unit and boundary are required",
        )?;
        ensure(
            match (observation.value, &observation.unavailable_reason) {
                (Some(value), None) => nonnegative(value),
                (None, Some(reason)) => !reason.trim().is_empty(),
                _ => false,
            },
            "measurement must be finite/nonnegative or explicitly unavailable",
        )?;
    }
    let mut previous = 0.0;
    let mut kinds = BTreeSet::new();
    for event in &trace.events {
        ensure(
            nonnegative(event.at_ms)
                && event.at_ms >= previous
                && !event.kind.trim().is_empty()
                && !event.consumer.trim().is_empty()
                && !event.detail.trim().is_empty(),
            "events must be ordered and have a kind, consumer and evidence detail",
        )?;
        ensure(
            trace.identity.inputs.contains_key(&event.source),
            "event references an unknown source identity",
        )?;
        previous = event.at_ms;
        kinds.insert(event.kind.clone());
    }
    let mut reasons = trace.failures.clone();
    if !trace.completed {
        reasons.push("journey incomplete".into());
    }
    let Some(bytes) = threshold_bytes else {
        ensure(trace.thresholds_sha256.is_none(), "threshold file required")?;
        reasons.push("calibration only: no frozen qualification thresholds".into());
        return Ok(Assessment {
            admitted: true,
            qualified: false,
            reasons,
        });
    };
    let hash = format!("{:x}", Sha256::digest(bytes));
    ensure(
        trace.thresholds_sha256.as_deref() == Some(&hash),
        "threshold file identity mismatch",
    )?;
    let thresholds: Thresholds = serde_json::from_slice(bytes)?;
    ensure(
        thresholds.schema == "composed_journey_thresholds/1",
        "unknown threshold schema",
    )?;
    ensure(
        thresholds.frozen_unix_ms > 0
            && thresholds.frozen_unix_ms < trace.started_unix_ms
            && thresholds.workload_sha256 == trace.identity.workload_sha256
            && identities(&thresholds.baseline_evidence_sha256, 64)
            && !thresholds.rationale.trim().is_empty()
            && !thresholds.bounds.is_empty()
            && !thresholds.required_events.is_empty(),
        "thresholds need prior freeze, matching workload, baseline evidence and rationale",
    )?;
    if thresholds.require_hardware_gpu && !trace.environment.hardware_gpu {
        reasons.push("hardware GPU evidence required".into());
    }
    for required in thresholds.required_events.difference(&kinds) {
        reasons.push(format!("missing required event: {required}"));
    }
    for (name, bound) in &thresholds.bounds {
        ensure(
            !bound.unit.trim().is_empty()
                && !bound.boundary.trim().is_empty()
                && (bound.minimum.is_some() || bound.maximum.is_some())
                && bound.minimum.is_none_or(nonnegative)
                && bound.maximum.is_none_or(nonnegative)
                && match (bound.minimum, bound.maximum) {
                    (Some(min), Some(max)) => min <= max,
                    _ => true,
                },
            "invalid threshold bound",
        )?;
        match trace.observations.get(name) {
            Some(observation)
                if observation.unit == bound.unit && observation.boundary == bound.boundary =>
            {
                match observation.value {
                    Some(value)
                        if bound.minimum.is_none_or(|min| value >= min)
                            && bound.maximum.is_none_or(|max| value <= max) => {}
                    Some(_) => reasons.push(format!("threshold exceeded: {name}")),
                    None => reasons.push(format!("required measurement unavailable: {name}")),
                }
            }
            _ => reasons.push(format!("missing or incomparable measurement: {name}")),
        }
    }
    Ok(Assessment {
        admitted: true,
        qualified: reasons.is_empty(),
        reasons,
    })
}
