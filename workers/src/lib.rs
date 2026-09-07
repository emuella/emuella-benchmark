use emuella_benchmark::{contract::*, metrics};
use sha2::{Digest, Sha256};
use std::{collections::BTreeMap, fs, time::Instant};
pub type Result<T> = std::result::Result<T, String>;

pub fn asset(asset: &Asset) -> Result<Vec<u8>> {
    let bytes = fs::read(&asset.path).map_err(|e| e.to_string())?;
    if format!("{:x}", Sha256::digest(&bytes)) != asset.sha256 {
        return Err("asset SHA-256 mismatch".into());
    }
    Ok(bytes)
}
pub fn raw(bytes: &[u8], image: &ImageSpec) -> Result<Vec<i32>> {
    if image.signed
        || ![8, 16].contains(&image.precision)
        || Some(bytes.len()) != image.byte_count()
    {
        return Err("expected packed unsigned U8/U16_LE samples with declared geometry".into());
    }
    Ok(if image.precision == 8 {
        bytes.iter().map(|x| i32::from(*x)).collect()
    } else {
        bytes
            .as_chunks::<2>()
            .0
            .iter()
            .map(|x| i32::from(u16::from_le_bytes([x[0], x[1]])))
            .collect()
    })
}
pub fn validate(request: &WorkerRequest, boundary: Boundary, keys: &[&str]) -> Result<()> {
    request.case.validate().map_err(|e| e.to_string())?;
    request.protocol.validate().map_err(|e| e.to_string())?;
    if request.schema_version != SCHEMA_VERSION {
        return Err("unsupported schema".into());
    }
    let c = &request.case;
    if request.protocol.boundary != boundary {
        return Err(format!("unsupported boundary: requires {boundary:?}"));
    }
    if c.image.signed
        || c.output.image.signed
        || ![8, 16].contains(&c.image.precision)
        || ![8, 16].contains(&c.output.image.precision)
        || ![1, 3].contains(&c.image.components)
        || c.output.colour != "native"
        || c.output.container != "j2k"
    {
        return Err("unsupported sample/colour/container semantics: unsigned U8/U16, grey/RGB, native, j2k required".into());
    }
    for key in c.settings.keys() {
        if !keys.contains(&key.as_str()) {
            return Err(format!("unsupported setting {key}"));
        }
    }
    if c.operation == Operation::Encode
        && (c.output.reduction != 0 || c.output.region.is_some() || c.output.image != c.image)
    {
        return Err("unsupported encode ROI/reduction or output geometry".into());
    }
    Ok(())
}
pub fn string<'a>(c: &'a Case, key: &str, default: &'a str) -> Result<&'a str> {
    c.settings.get(key).map_or(Ok(default), |x| {
        x.as_str().ok_or_else(|| format!("{key} must be a string"))
    })
}
pub fn number(c: &Case, key: &str, default: f64) -> Result<f64> {
    let x = c.settings.get(key).map_or(Ok(default), |x| {
        x.as_f64().ok_or_else(|| format!("{key} must be numeric"))
    })?;
    if !x.is_finite() || x <= 0.0 {
        return Err(format!("{key} must be finite and positive"));
    }
    Ok(x)
}
pub fn levels(c: &Case, default: u8) -> Result<u8> {
    if c.operation == Operation::Encode && !c.settings.contains_key("decomposition_levels") {
        return Err("unsupported encode without explicit decomposition_levels".into());
    }
    c.settings
        .get("decomposition_levels")
        .map_or(Ok(default), |x| {
            x.as_u64()
                .filter(|x| *x <= 32)
                .map(|x| x as u8)
                .ok_or_else(|| "decomposition_levels must be an integer in 0..32".into())
        })
}
pub fn rss() -> Option<u64> {
    fs::read_to_string("/proc/self/status")
        .ok()?
        .lines()
        .find_map(|line| {
            line.strip_prefix("VmHWM:")?
                .split_whitespace()
                .next()?
                .parse::<u64>()
                .ok()?
                .checked_mul(1024)
        })
}
pub fn response(r: &WorkerRequest) -> WorkerResponse {
    WorkerResponse {
        schema_version: SCHEMA_VERSION,
        request_id: r.request_id.clone(),
        status: WorkerStatus::Ok,
        message: None,
        applied_case: r.case.clone(),
        boundary: r.protocol.boundary.clone(),
        samples_ns: vec![],
        correctness: None,
        output_bytes: None,
        peak_rss_bytes: None,
        diagnostics: BTreeMap::new(),
    }
}
pub fn run_samples<T>(
    r: &WorkerRequest,
    mut operation: impl FnMut() -> Result<T>,
    mut verify: impl FnMut(T) -> Result<(Vec<i32>, u64)>,
) -> Result<WorkerResponse> {
    let reference_asset = r.case.reference.as_ref().unwrap_or(&r.case.input);
    let reference = raw(&asset(reference_asset)?, &r.case.output.image)?;
    let mut result = response(r);
    let mut checks = vec![];
    for index in 0..u32::from(r.protocol.warmup) + u32::from(r.protocol.samples_per_batch) {
        let start = Instant::now();
        let output = operation()?;
        let elapsed = u64::try_from(start.elapsed().as_nanos()).map_err(|e| e.to_string())?;
        let (samples, bytes) = verify(output)?;
        let correctness = metrics::measure(&reference, &samples, &r.case.output.image)
            .map_err(|e| e.to_string())?;
        if r.case.output.lossless && !correctness.exact {
            return Err("lossless output differs from reference".into());
        }
        if !r.case.output.lossless
            && correctness
                .psnr_db
                .is_some_and(|p| p < r.case.output.minimum_psnr_db.unwrap())
        {
            return Err("output falls below minimum PSNR".into());
        }
        if index >= u32::from(r.protocol.warmup) {
            result.samples_ns.push(elapsed);
            checks.push(correctness);
            if result.output_bytes.is_some_and(|b| b != bytes) {
                return Err("output size changed between samples".into());
            }
            result.output_bytes = Some(bytes);
        }
    }
    result.correctness = Some(metrics::combine(&checks).map_err(|e| e.to_string())?);
    result.peak_rss_bytes = rss();
    Ok(result)
}
pub fn main_worker(run: impl FnOnce(&WorkerRequest) -> Result<WorkerResponse>) {
    let result = (|| -> Result<()> {
        let args: Vec<_> = std::env::args_os().skip(1).collect();
        if args.len() != 4 || args[0] != "--request" || args[2] != "--response" {
            return Err("usage: worker --request PATH --response PATH".into());
        }
        let r: WorkerRequest =
            serde_json::from_slice(&fs::read(&args[1]).map_err(|e| e.to_string())?)
                .map_err(|e| e.to_string())?;
        let output = match run(&r) {
            Ok(x) => x,
            Err(e) => {
                let mut x = response(&r);
                x.status = if e.starts_with("unattainable_rate:") {
                    WorkerStatus::UnattainableRate
                } else if e.starts_with("unsupported") {
                    WorkerStatus::Unsupported
                } else {
                    WorkerStatus::Failed
                };
                x.message = Some(e);
                x
            }
        };
        fs::write(
            &args[3],
            serde_json::to_vec_pretty(&output).map_err(|e| e.to_string())?,
        )
        .map_err(|e| e.to_string())
    })();
    if let Err(e) = result {
        eprintln!("{e}");
        std::process::exit(1);
    }
}

/// Fixed encoder policies are factual output metadata even without instrumentation.
pub fn record_encode_profile(response: &mut WorkerResponse, coding: &str, levels: u8, mct: &str) {
    if response.applied_case.operation == Operation::Encode {
        response.diagnostics.insert(
            "encode_profile".into(),
            serde_json::json!({
                "coding": coding,
                "decomposition_levels": levels,
                "multiple_component_transform": mct,
                "progression_order": "lrcp",
                "quality_layers": 1,
                "tiles": 1
            }),
        );
    }
}

/// An unsupported instrumented request must not silently become an ordinary run.
pub fn record_unsupported_diagnostics(
    response: &mut WorkerResponse,
    request: &WorkerRequest,
    implementation: &str,
) {
    if request.diagnostic {
        response.diagnostics.insert(
            "unsupported_reason".into(),
            serde_json::json!(format!(
                "{implementation} worker does not expose codec diagnostic instrumentation"
            )),
        );
    }
}
