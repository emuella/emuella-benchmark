//! Project-authored protocol fixture, not a codec or a production performance claim.
use emuella_benchmark::{Result, contract::*, metrics, read_json, runner::write_json_new};
use std::{
    collections::BTreeMap,
    path::Path,
    time::{Duration, Instant},
};
fn execute() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    let value = |key: &str| -> Result<&str> {
        let index = args
            .iter()
            .position(|x| x == key)
            .ok_or_else(|| format!("missing {key}"))?;
        args.get(index + 1)
            .map(String::as_str)
            .ok_or_else(|| format!("missing value for {key}").into())
    };
    let request: WorkerRequest = read_json(Path::new(value("--request")?))?;
    if args.iter().any(|x| x == "--crash") {
        std::process::exit(7);
    }
    if args.iter().any(|x| x == "--timeout") {
        std::thread::sleep(Duration::from_secs(60));
    }
    let unattainable = args.iter().any(|x| x == "--unattainable");
    let unsupported = args.iter().any(|x| x == "--unsupported");
    let mut response = WorkerResponse {
        schema_version: SCHEMA_VERSION,
        request_id: request.request_id.clone(),
        status: if unattainable {
            WorkerStatus::UnattainableRate
        } else if unsupported {
            WorkerStatus::Unsupported
        } else {
            WorkerStatus::Ok
        },
        message: (unsupported || unattainable)
            .then(|| "synthetic unavailable capability or rate".into()),
        applied_case: request.case.clone(),
        boundary: request.protocol.boundary.clone(),
        samples_ns: vec![],
        correctness: None,
        output_bytes: None,
        peak_rss_bytes: None,
        diagnostics: BTreeMap::new(),
    };
    if !unsupported && !unattainable {
        let delay = args
            .iter()
            .position(|x| x == "--delay-ms")
            .map(|index| args[index + 1].parse::<u64>())
            .transpose()?
            .unwrap_or(0);
        let input = metrics::read_raw(&request.case.input.path, &request.case.image)?;
        let reference = if let Some(reference) = &request.case.reference {
            metrics::read_raw(&reference.path, &request.case.output.image)?
        } else {
            input.clone()
        };
        let corrupt = args.iter().any(|x| x == "--corrupt");
        let mut measured = vec![];
        for index in
            0..u32::from(request.protocol.warmup) + u32::from(request.protocol.samples_per_batch)
        {
            let started = Instant::now();
            let mut output = std::hint::black_box(input.clone());
            if delay > 0 {
                std::thread::sleep(Duration::from_millis(delay));
            }
            std::hint::black_box(&output);
            let elapsed = started
                .elapsed()
                .as_nanos()
                .max(1)
                .min(u128::from(u64::MAX)) as u64;
            if corrupt {
                output[0] = if output[0] == 0 { 1 } else { 0 };
            }
            if index >= u32::from(request.protocol.warmup) {
                response.samples_ns.push(elapsed);
                measured.push(metrics::measure(
                    &reference,
                    &output,
                    &request.case.output.image,
                )?);
            }
        }
        response.correctness = Some(metrics::combine(&measured)?);
        response.output_bytes = Some(request.case.output.image.byte_count().unwrap() as u64);
        if request.diagnostic {
            response
                .diagnostics
                .insert("synthetic_worker".into(), true.into());
        }
    }
    if args.iter().any(|x| x == "--bad-schema") {
        response.schema_version += 1;
    }
    write_json_new(Path::new(value("--response")?), &response)
}
fn main() {
    if let Err(error) = execute() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
