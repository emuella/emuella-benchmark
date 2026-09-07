use crate::{Result, contract::*};
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::Path,
    process::{Command, Stdio},
    thread,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

pub fn sha256_file(path: &Path) -> Result<String> {
    let mut file = File::open(path)?;
    let mut hash = Sha256::new();
    let mut buffer = [0; 64 * 1024];
    loop {
        let count = file.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        hash.update(&buffer[..count]);
    }
    Ok(format!("{:x}", hash.finalize()))
}
pub fn write_json_new(path: &Path, value: &impl serde::Serialize) -> Result<()> {
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut file, value)?;
    file.write_all(b"\n")?;
    file.sync_all()?;
    Ok(())
}
fn next_id() -> String {
    static SEQUENCE: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    format!(
        "{}-{}-{}",
        stamp(),
        std::process::id(),
        SEQUENCE.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
    )
}
fn stamp() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}
fn identity(worker: &WorkerDefinition) -> Result<WorkerIdentity> {
    if worker.implementation.trim().is_empty() || worker.source_identity.trim().is_empty() {
        return Err("worker needs implementation and source identity".into());
    }
    let mut definition = worker.clone();
    definition.executable = definition.executable.canonicalize()?;
    definition.artefacts = definition
        .artefacts
        .iter()
        .map(|x| x.canonicalize())
        .collect::<std::io::Result<_>>()?;
    for argument in &definition.args {
        let path = Path::new(argument);
        if path.is_file() && !definition.artefacts.contains(&path.canonicalize()?) {
            return Err(format!(
                "file argument {} must be listed in worker artefacts",
                path.display()
            )
            .into());
        }
    }
    let mut artefact_sha256 = BTreeMap::new();
    for path in &definition.artefacts {
        artefact_sha256.insert(path.clone(), sha256_file(path)?);
    }
    Ok(WorkerIdentity {
        executable_sha256: sha256_file(&definition.executable)?,
        definition,
        artefact_sha256,
    })
}
fn verify_assets(experiment: &Experiment) -> Result<()> {
    for case in &experiment.cases {
        for asset in std::iter::once(&case.input).chain(case.reference.iter()) {
            if sha256_file(&asset.path)? != asset.sha256 {
                return Err(format!("input digest mismatch: {}", asset.path.display()).into());
            }
        }
        if case.operation == Operation::Encode {
            crate::metrics::read_raw(&case.input.path, &case.image)?;
        }
        if let Some(reference) = &case.reference {
            crate::metrics::read_raw(&reference.path, &case.output.image)?;
        }
    }
    Ok(())
}
fn read_trim(path: &str) -> String {
    fs::read_to_string(path)
        .unwrap_or_else(|_| "unavailable".into())
        .trim()
        .to_owned()
}
pub fn machine() -> Machine {
    let cpu_info = read_trim("/proc/cpuinfo");
    let cpu = cpu_info
        .lines()
        .find_map(|line| {
            line.strip_prefix("model name")
                .and_then(|x| x.split_once(':'))
                .map(|(_, x)| x.trim().to_owned())
        })
        .unwrap_or(cpu_info);
    let status = read_trim("/proc/self/status");
    let affinity = status
        .lines()
        .find(|x| x.starts_with("Cpus_allowed_list:"))
        .unwrap_or("unavailable")
        .to_owned();
    let mut governors = BTreeMap::new();
    if let Ok(entries) = fs::read_dir("/sys/devices/system/cpu") {
        for entry in entries.flatten() {
            let file = entry.path().join("cpufreq/scaling_governor");
            if let Ok(value) = fs::read_to_string(file) {
                governors.insert(
                    entry.file_name().to_string_lossy().into_owned(),
                    value.trim().to_owned(),
                );
            }
        }
    }
    let environment: BTreeMap<_, _> = std::env::vars()
        .filter(|(key, _)| {
            key.starts_with("OMP_")
                || key.starts_with("RAYON_")
                || key.starts_with("OPENBLAS_")
                || key.starts_with("MKL_")
                || key.starts_with("LD_")
                || key.starts_with("DYLD_")
                || [
                    "PATH",
                    "PYTHONPATH",
                    "PYTHONHASHSEED",
                    "MALLOC_CONF",
                    "GLIBC_TUNABLES",
                ]
                .contains(&key.as_str())
        })
        .collect();
    Machine {
        os: std::env::consts::OS.into(),
        architecture: std::env::consts::ARCH.into(),
        hostname: read_trim("/etc/hostname"),
        kernel: read_trim("/proc/sys/kernel/osrelease"),
        cpu,
        logical_cpus: thread::available_parallelism().map_or(0, |x| x.get()),
        affinity,
        governors,
        environment_sha256: format!(
            "{:x}",
            Sha256::digest(serde_json::to_vec(&environment).unwrap_or_default())
        ),
    }
}
fn initialise(
    experiment: &Experiment,
    worker: &WorkerDefinition,
    output: &Path,
    pair_id: Option<String>,
    diagnostic: bool,
) -> Result<Run> {
    experiment.validate()?;
    verify_assets(experiment)?;
    let worker = identity(worker)?;
    let run = Run {
        schema_version: SCHEMA_VERSION,
        run_id: next_id(),
        created_unix_ms: stamp(),
        experiment: experiment.clone(),
        worker,
        harness_version: env!("CARGO_PKG_VERSION").into(),
        harness_sha256: sha256_file(&std::env::current_exe()?)?,
        machine: machine(),
        pair_id,
        diagnostic,
        batches: vec![],
    };
    // Refuse an existing directory: results are append-once factual evidence.
    fs::create_dir(output)?;
    write_json_new(&output.join("manifest.json"), &run)?;
    fs::create_dir(output.join("batches"))?;
    Ok(run)
}
fn finish(run: &Run, output: &Path) -> Result<()> {
    // Detect changes during execution before accepting a completed run.
    verify_assets(&run.experiment)?;
    if identity(&run.worker.definition)? != run.worker {
        return Err("worker artefacts changed during execution".into());
    }
    if machine() != run.machine {
        return Err("machine configuration changed during execution".into());
    }
    write_json_new(&output.join("run.json"), run)
}

pub fn run(
    experiment: &Experiment,
    worker: &WorkerDefinition,
    output: &Path,
    diagnostic: bool,
) -> Result<Run> {
    let mut result = initialise(experiment, worker, output, None, diagnostic)?;
    let mut index = 0;
    for round in 0..experiment.protocol.rounds {
        for case in &experiment.cases {
            let batch = execute_batch(&result, case, round, index, output)?;
            result.batches.push(batch);
            index += 1;
        }
    }
    finish(&result, output)?;
    Ok(result)
}

/// Alternates AB/BA each round, keeping matched cases adjacent and raw batches intact.
pub fn run_pair(
    experiment: &Experiment,
    baseline: &WorkerDefinition,
    candidate: &WorkerDefinition,
    output: &Path,
) -> Result<(Run, Run)> {
    experiment.validate()?;
    fs::create_dir(output)?;
    let pair_id = Some(format!("pair-{}", next_id()));
    let base_path = output.join("baseline");
    let candidate_path = output.join("candidate");
    let mut a = initialise(experiment, baseline, &base_path, pair_id.clone(), false)?;
    let mut b = initialise(experiment, candidate, &candidate_path, pair_id, false)?;
    let mut index = 0;
    for round in 0..experiment.protocol.rounds {
        for case in &experiment.cases {
            if round % 2 == 0 {
                a.batches
                    .push(execute_batch(&a, case, round, index, &base_path)?);
                b.batches
                    .push(execute_batch(&b, case, round, index + 1, &candidate_path)?);
            } else {
                b.batches
                    .push(execute_batch(&b, case, round, index, &candidate_path)?);
                a.batches
                    .push(execute_batch(&a, case, round, index + 1, &base_path)?);
            }
            index += 2;
        }
    }
    finish(&a, &base_path)?;
    finish(&b, &candidate_path)?;
    Ok((a, b))
}

fn execute_batch(run: &Run, case: &Case, round: u16, index: u64, output: &Path) -> Result<Batch> {
    let request = WorkerRequest {
        schema_version: SCHEMA_VERSION,
        request_id: format!("{}-{index}", run.run_id),
        case: case.clone(),
        protocol: run.experiment.protocol.clone(),
        diagnostic: run.diagnostic,
    };
    let batch_path = output.join("batches").join(format!("{index:08}"));
    fs::create_dir(&batch_path)?;
    let request_path = batch_path.join("request.json");
    let response_path = batch_path.join("response.json");
    write_json_new(&request_path, &request)?;
    let stdout = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(batch_path.join("stdout.log"))?;
    let stderr = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(batch_path.join("stderr.log"))?;
    let mut command = Command::new(&run.worker.definition.executable);
    command
        .args(&run.worker.definition.args)
        .arg("--request")
        .arg(request_path.canonicalize()?)
        .arg("--response")
        .arg(batch_path.canonicalize()?.join("response.json"))
        .stdin(Stdio::null())
        .stdout(stdout)
        .stderr(stderr);
    // Worker processes must not daemonise. A dedicated process group also contains
    // ordinary adapter child commands so timeout cleanup does not leak codec jobs.
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        command.process_group(0);
    }
    let started = Instant::now();
    let mut batch = Batch {
        case_id: case.id.clone(),
        round,
        execution_index: index,
        status: BatchStatus::Failed,
        detail: None,
        response: None,
    };
    match command.spawn() {
        Err(error) => {
            batch.detail = Some(format!("worker spawn failed: {error}"));
        }
        Ok(mut child) => {
            let exit = loop {
                if let Some(status) = child.try_wait()? {
                    break Some(status);
                }
                if started.elapsed() >= Duration::from_millis(request.protocol.timeout_ms) {
                    #[cfg(unix)]
                    {
                        // SAFETY: kill takes integer process identifiers only. The
                        // child owns the process group created above; a negative
                        // identifier signals that group, including codec children.
                        unsafe {
                            libc::kill(-(child.id() as i32), libc::SIGKILL);
                        }
                    }
                    let _ = child.kill();
                    let _ = child.wait();
                    break None;
                }
                thread::sleep(Duration::from_millis(2));
            };
            match exit {
                None => {
                    batch.status = BatchStatus::Timeout;
                    batch.detail = Some("worker exceeded batch timeout".into());
                }
                Some(status) if !status.success() => {
                    batch.status = BatchStatus::Crashed;
                    batch.detail = Some(format!("worker exited {status}"));
                }
                Some(_) => {
                    // Bound untrusted protocol output before deserialising it.
                    let response = (|| -> Result<WorkerResponse> {
                        if fs::metadata(&response_path)?.len() > 16 * 1024 * 1024 {
                            return Err("response exceeds 16 MiB".into());
                        }
                        crate::read_json(&response_path)
                    })();
                    match response {
                        Err(error) => {
                            batch.status = BatchStatus::Invalid;
                            batch.detail = Some(format!("invalid response: {error}"));
                        }
                        Ok(response) => {
                            match validate_response(&request, &response) {
                                Err(error) => {
                                    batch.status = BatchStatus::Invalid;
                                    batch.detail = Some(error.to_string());
                                }
                                Ok(()) => {
                                    batch.status = match response.status {
                                        WorkerStatus::Ok => BatchStatus::Ok,
                                        WorkerStatus::UnattainableRate => {
                                            BatchStatus::UnattainableRate
                                        }
                                        WorkerStatus::Unsupported => BatchStatus::Unsupported,
                                        WorkerStatus::Failed => BatchStatus::Failed,
                                    };
                                    batch.detail = response.message.clone();
                                }
                            }
                            batch.response = Some(response);
                        }
                    }
                }
            }
        }
    }
    write_json_new(&batch_path.join("batch.json"), &batch)?;
    Ok(batch)
}

pub fn validate_response(request: &WorkerRequest, response: &WorkerResponse) -> Result<()> {
    request.case.validate()?;
    request.protocol.validate()?;
    if request.schema_version != SCHEMA_VERSION {
        return Err("unsupported request schema version".into());
    }
    if response.schema_version != SCHEMA_VERSION
        || response.request_id != request.request_id
        || response.applied_case != request.case
        || response.boundary != request.protocol.boundary
    {
        return Err(
            "response schema, identity, applied settings or measurement boundary mismatch".into(),
        );
    }
    if response.status != WorkerStatus::Ok {
        if response
            .message
            .as_ref()
            .is_none_or(|x| x.trim().is_empty())
            || !response.samples_ns.is_empty()
            || response.correctness.is_some()
            || response.output_bytes.is_some()
        {
            return Err(
                "non-success response needs a reason and must not carry successful measurements"
                    .into(),
            );
        }
        return Ok(());
    }
    if response.samples_ns.len() != usize::from(request.protocol.samples_per_batch)
        || response.samples_ns.contains(&0)
        || response.output_bytes.is_none_or(|n| n == 0)
    {
        return Err("missing, zero or unexpected measurement samples/output size".into());
    }
    if response.peak_rss_bytes == Some(0) {
        return Err("observed peak RSS must be positive or absent".into());
    }
    let metrics = response
        .correctness
        .as_ref()
        .ok_or("successful response lacks correctness metrics")?;
    crate::metrics::validate(metrics)?;
    let expected_count = request
        .case
        .output
        .image
        .sample_count()
        .ok_or("output sample count overflow")? as u64;
    let expected_count = expected_count
        .checked_mul(u64::from(request.protocol.samples_per_batch))
        .ok_or("aggregate sample count overflow")?;
    let expected_peak = f64::from((1_u32 << request.case.output.image.precision) - 1);
    if metrics.sample_count != expected_count || metrics.peak != expected_peak {
        return Err(
            "correctness count/peak differs from expected output geometry/precision".into(),
        );
    }
    if request.case.output.lossless && !metrics.exact {
        return Err("lossless output is not an exact match".into());
    }
    if let (Some(minimum), Some(actual)) = (request.case.output.minimum_psnr_db, metrics.psnr_db)
        && actual < minimum
    {
        return Err("lossy output misses minimum PSNR".into());
    }
    Ok(())
}
