use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{collections::BTreeMap, path::PathBuf};

pub const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Asset {
    pub path: PathBuf,
    pub sha256: String,
    /// Opaque runtime catalogue identity; no asset or rights acquisition occurs.
    #[serde(default)]
    pub provenance: BTreeMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ImageSpec {
    pub width: u32,
    pub height: u32,
    pub components: u16,
    pub precision: u8,
    pub signed: bool,
}

impl ImageSpec {
    pub fn sample_count(&self) -> Option<usize> {
        (self.width as usize)
            .checked_mul(self.height as usize)?
            .checked_mul(self.components as usize)
    }
    pub fn byte_count(&self) -> Option<usize> {
        self.sample_count()?
            .checked_mul(if self.precision <= 8 { 1 } else { 2 })
    }
    pub fn validate(&self) -> crate::Result<()> {
        if self.width == 0
            || self.height == 0
            || self.components == 0
            || !(1..=16).contains(&self.precision)
            || self.byte_count().is_none()
        {
            return Err("invalid image dimensions or precision (supported: 1–16 bits)".into());
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Operation {
    Encode,
    Decode,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Boundary {
    CodecOperation,
    ApplicationJourney,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Region {
    pub x: u32,
    pub y: u32,
    pub width: u32,
    pub height: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct OutputSemantics {
    /// Workers must explicitly reject unsupported meanings, never silently adapt.
    pub colour: String,
    pub layout: String,
    pub container: String,
    pub lossless: bool,
    pub reduction: u8,
    pub region: Option<Region>,
    /// Expected decoded output geometry, including ROI/reduction effects.
    pub image: ImageSpec,
    /// Required for lossy acceptance. PSNR uses the full declared sample range.
    pub minimum_psnr_db: Option<f64>,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Case {
    pub id: String,
    pub input: Asset,
    /// Required for decode; raw expected output with output.image geometry.
    pub reference: Option<Asset>,
    pub image: ImageSpec,
    pub operation: Operation,
    /// Codec-neutral semantic parameters for equivalence across adapters.
    #[serde(default)]
    pub settings: BTreeMap<String, Value>,
    pub threads: u16,
    pub output: OutputSemantics,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Protocol {
    pub rounds: u16,
    pub samples_per_batch: u16,
    pub warmup: u16,
    pub timeout_ms: u64,
    pub boundary: Boundary,
    /// v1 accepts only fresh_process_per_batch + warm_input.
    pub context_policy: String,
    pub cache_policy: String,
    pub practical_relative_threshold: f64,
}
impl Default for Protocol {
    fn default() -> Self {
        Self {
            rounds: 7,
            samples_per_batch: 5,
            warmup: 2,
            timeout_ms: 30_000,
            boundary: Boundary::CodecOperation,
            context_policy: "fresh_process_per_batch".into(),
            cache_policy: "warm_input".into(),
            practical_relative_threshold: 0.05,
        }
    }
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Experiment {
    pub schema_version: u32,
    pub name: String,
    #[serde(default)]
    pub protocol: Protocol,
    #[serde(default)]
    pub environment_tags: BTreeMap<String, String>,
    pub cases: Vec<Case>,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct WorkerDefinition {
    pub executable: PathBuf,
    #[serde(default)]
    pub args: Vec<String>,
    pub implementation: String,
    pub source_identity: String,
    /// Additional executable/script/library files whose bytes identify the build.
    #[serde(default)]
    pub artefacts: Vec<PathBuf>,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct WorkerRequest {
    pub schema_version: u32,
    pub request_id: String,
    pub case: Case,
    pub protocol: Protocol,
    pub diagnostic: bool,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum WorkerStatus {
    Ok,
    UnattainableRate,
    Unsupported,
    Failed,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Correctness {
    pub sample_count: u64,
    pub exact: bool,
    pub maximum_absolute_error: f64,
    pub mse: f64,
    pub peak: f64,
    /// None represents infinite PSNR for an exact match only.
    pub psnr_db: Option<f64>,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct WorkerResponse {
    pub schema_version: u32,
    pub request_id: String,
    pub status: WorkerStatus,
    pub message: Option<String>,
    /// Echo the settings actually applied. Any difference invalidates the batch.
    pub applied_case: Case,
    pub boundary: Boundary,
    /// Nanoseconds for each repeated operation; setup, input IO and verification excluded
    /// from codec_operation. Warmups are omitted. All outputs must be verified.
    pub samples_ns: Vec<u64>,
    pub correctness: Option<Correctness>,
    pub output_bytes: Option<u64>,
    /// Process peak RSS bytes, when actually observed; never a fabricated zero.
    pub peak_rss_bytes: Option<u64>,
    #[serde(default)]
    pub diagnostics: BTreeMap<String, Value>,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct WorkerIdentity {
    pub definition: WorkerDefinition,
    pub executable_sha256: String,
    pub artefact_sha256: BTreeMap<PathBuf, String>,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Machine {
    pub os: String,
    pub architecture: String,
    pub hostname: String,
    pub kernel: String,
    pub cpu: String,
    pub logical_cpus: usize,
    pub affinity: String,
    pub governors: BTreeMap<String, String>,
    /// Selected performance-relevant environment variables, hashed to avoid secrets.
    pub environment_sha256: String,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum BatchStatus {
    Ok,
    UnattainableRate,
    Unsupported,
    Failed,
    Timeout,
    Crashed,
    Invalid,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Batch {
    pub case_id: String,
    pub round: u16,
    pub execution_index: u64,
    pub status: BatchStatus,
    pub detail: Option<String>,
    pub response: Option<WorkerResponse>,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Run {
    pub schema_version: u32,
    pub run_id: String,
    pub created_unix_ms: u64,
    pub experiment: Experiment,
    pub worker: WorkerIdentity,
    pub harness_version: String,
    pub harness_sha256: String,
    pub machine: Machine,
    /// Same identity on paired, interleaved runs; None on independent runs.
    pub pair_id: Option<String>,
    pub diagnostic: bool,
    pub batches: Vec<Batch>,
}

pub fn validate_digest(digest: &str) -> crate::Result<()> {
    if digest.len() != 64
        || !digest
            .bytes()
            .all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase())
    {
        return Err("SHA-256 must be 64 lowercase hexadecimal characters".into());
    }
    Ok(())
}
impl Experiment {
    pub fn validate(&self) -> crate::Result<()> {
        if self.schema_version != SCHEMA_VERSION {
            return Err("unsupported experiment schema version".into());
        }
        if self.name.trim().is_empty() || self.cases.is_empty() || self.cases.len() > 10_000 {
            return Err("experiment needs a name and 1–10000 cases".into());
        }
        self.protocol.validate()?;
        let mut ids = std::collections::BTreeSet::new();
        for case in &self.cases {
            if case.id.trim().is_empty() || !ids.insert(&case.id) {
                return Err("case IDs must be nonempty and unique".into());
            }
            case.validate()?;
            (case
                .output
                .image
                .sample_count()
                .ok_or("sample count overflow")? as u64)
                .checked_mul(u64::from(self.protocol.samples_per_batch))
                .and_then(|n| n.checked_mul(u64::from(self.protocol.rounds)))
                .ok_or("aggregate metric sample count overflow")?;
        }
        Ok(())
    }
}
impl Protocol {
    pub fn validate(&self) -> crate::Result<()> {
        if !(5..=1000).contains(&self.rounds)
            || !(1..=1000).contains(&self.samples_per_batch)
            || self.warmup > 1000
            || !(1..=3_600_000).contains(&self.timeout_ms)
            || !self.practical_relative_threshold.is_finite()
            || !(0.0..1.0).contains(&self.practical_relative_threshold)
            || self.context_policy != "fresh_process_per_batch"
            || self.cache_policy != "warm_input"
        {
            return Err("invalid protocol bounds or unsupported context/cache policy".into());
        }
        Ok(())
    }
}
impl Case {
    pub fn validate(&self) -> crate::Result<()> {
        self.image.validate()?;
        self.output.image.validate()?;
        validate_digest(&self.input.sha256)?;
        if let Some(reference) = &self.reference {
            validate_digest(&reference.sha256)?;
        }
        if self.operation == Operation::Decode && self.reference.is_none() {
            return Err("decode requires a raw reference".into());
        }
        if self.threads == 0
            || self.output.colour.is_empty()
            || self.output.layout != "interleaved"
            || self.output.container.is_empty()
            || self.output.reduction > 31
        {
            return Err(
                "invalid threads or output semantics; v1 raw pixels are interleaved".into(),
            );
        }
        if let Some(region) = &self.output.region
            && (region.width == 0
                || region.height == 0
                || region
                    .x
                    .checked_add(region.width)
                    .is_none_or(|x| x > self.image.width)
                || region
                    .y
                    .checked_add(region.height)
                    .is_none_or(|y| y > self.image.height))
        {
            return Err("ROI lies outside the source image".into());
        }
        if self.output.minimum_psnr_db.is_some_and(|x| !x.is_finite())
            || (!self.output.lossless && self.output.minimum_psnr_db.is_none())
        {
            return Err("lossy output requires a finite minimum PSNR".into());
        }
        if self.operation == Operation::Encode
            && self.reference.is_none()
            && self.image != self.output.image
        {
            return Err(
                "encode output geometry differs from input without an explicit reference".into(),
            );
        }
        Ok(())
    }
}
