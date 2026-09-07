use emuella_benchmark::contract::*;
use emuella_benchmark_workers::*;
use std::{
    fs,
    path::{Path, PathBuf},
    process::Command,
};
fn pnm(raw: &[u8], i: &ImageSpec) -> Result<Vec<u8>> {
    emuella_benchmark_workers::raw(raw, i)?;
    let mut bytes = format!(
        "P{}\n{} {}\n{}\n",
        if i.components == 1 { 5 } else { 6 },
        i.width,
        i.height,
        (1_u32 << i.precision) - 1
    )
    .into_bytes();
    if i.precision == 16 {
        for x in raw.as_chunks::<2>().0.iter() {
            bytes.extend_from_slice(&[x[1], x[0]]);
        }
    } else {
        bytes.extend_from_slice(raw);
    }
    Ok(bytes)
}
fn read_pnm(path: &Path, i: &ImageSpec) -> Result<Vec<i32>> {
    let bytes = fs::read(path).map_err(|e| e.to_string())?;
    let mut offset = 0;
    let mut tokens = vec![];
    while tokens.len() < 4 {
        while offset < bytes.len() && bytes[offset].is_ascii_whitespace() {
            offset += 1;
        }
        if bytes.get(offset) == Some(&b'#') {
            while offset < bytes.len() && bytes[offset] != b'\n' {
                offset += 1;
            }
            continue;
        }
        let start = offset;
        while offset < bytes.len() && !bytes[offset].is_ascii_whitespace() {
            offset += 1;
        }
        if start == offset {
            return Err("truncated PNM header".into());
        }
        tokens.push(
            std::str::from_utf8(&bytes[start..offset])
                .map_err(|e| e.to_string())?
                .to_owned(),
        );
    }
    let expected = [
        format!("P{}", if i.components == 1 { 5 } else { 6 }),
        i.width.to_string(),
        i.height.to_string(),
        ((1_u32 << i.precision) - 1).to_string(),
    ];
    if tokens != expected {
        return Err("PNM output metadata differs from requested semantics".into());
    }
    if bytes.get(offset) == Some(&b'\r') && bytes.get(offset + 1) == Some(&b'\n') {
        offset += 2;
    } else {
        offset += 1;
    }
    let mut data = bytes.get(offset..).ok_or("truncated PNM")?.to_vec();
    if i.precision == 16 {
        for x in data.chunks_exact_mut(2) {
            x.swap(0, 1);
        }
    }
    raw(&data, i)
}
fn command(executable: &Path, args: &[String]) -> Result<()> {
    let output = Command::new(executable)
        .args(args)
        .output()
        .map_err(|e| e.to_string())?;
    if !output.status.success() {
        return Err(format!("OpenJPH command failed ({})", output.status));
    }
    Ok(())
}
struct Scratch(PathBuf);
impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}
fn run(r: &WorkerRequest) -> Result<WorkerResponse> {
    validate(
        r,
        Boundary::ApplicationJourney,
        &["coding", "decomposition_levels", "qstep"],
    )?;
    let c = &r.case;
    if string(c, "coding", "ht")? != "ht" {
        return Err("unsupported coding family: OpenJPH requires ht".into());
    }
    if c.threads != 1 {
        return Err("unsupported threads: this OpenJPH CLI exposes no thread control".into());
    }
    if c.output.region.is_some() {
        return Err("unsupported OpenJPH CLI ROI".into());
    }
    if c.operation == Operation::Decode && c.settings.keys().any(|k| k != "coding") {
        return Err("unsupported decode encoder settings".into());
    }
    if c.output.lossless && c.settings.contains_key("qstep") {
        return Err("unsupported lossless qstep".into());
    }
    let levels = levels(c, 2)?;
    let qstep = if !c.output.lossless && c.operation == Operation::Encode {
        if !c.settings.contains_key("qstep") {
            return Err("unsupported lossy encode without explicit qstep".into());
        }
        let value = number(c, "qstep", 0.01)?;
        if !(0.00001..=0.5).contains(&value) {
            return Err("unsupported qstep outside CLI bounds".into());
        }
        value
    } else {
        0.01
    };
    let base = std::env::var_os("EMUELLA_BENCHMARK_DERIVATIVE_STORE").ok_or(
        "unsupported application journey without explicit EMUELLA_BENCHMARK_DERIVATIVE_STORE",
    )?;
    let base = PathBuf::from(base)
        .canonicalize()
        .map_err(|e| e.to_string())?;
    if !base.is_dir() {
        return Err("derivative store must be an existing directory".into());
    }
    let scratch = Scratch(base.join(format!("openjph-worker-{}", std::process::id())));
    fs::create_dir(&scratch.0).map_err(|e| e.to_string())?;
    let compress = PathBuf::from(option_env!("OPENJPH_COMPRESS").unwrap_or("ojph_compress"));
    let expand = PathBuf::from(option_env!("OPENJPH_EXPAND").unwrap_or("ojph_expand"));
    let input = asset(&c.input)?;
    let source = scratch.0.join(if c.image.components == 1 {
        "source.pgm"
    } else {
        "source.ppm"
    });
    let stream = scratch.0.join("stream.j2c");
    let decoded = scratch.0.join(if c.image.components == 1 {
        "decoded.pgm"
    } else {
        "decoded.ppm"
    });
    let expand_args = |input: &Path| {
        vec![
            "-i".into(),
            input.to_string_lossy().into_owned(),
            "-o".into(),
            decoded.to_string_lossy().into_owned(),
            "-skip_res".into(),
            format!("{},{}", c.output.reduction, c.output.reduction),
        ]
    };
    let mut response = if c.operation == Operation::Encode {
        let mut args = vec![
            "-i".into(),
            source.to_string_lossy().into_owned(),
            "-o".into(),
            stream.to_string_lossy().into_owned(),
            "-num_decomps".into(),
            levels.to_string(),
            "-reversible".into(),
            c.output.lossless.to_string(),
            "-colour_trans".into(),
            "false".into(),
            "-prog_order".into(),
            "LRCP".into(),
        ];
        if !c.output.lossless {
            args.extend(["-qstep".into(), qstep.to_string()]);
        }
        run_samples(
            r,
            || {
                fs::write(&source, pnm(&input, &c.image)?).map_err(|e| e.to_string())?;
                command(&compress, &args)?;
                fs::read(&stream).map_err(|e| e.to_string())
            },
            |bytes| {
                command(&expand, &expand_args(&stream))?;
                Ok((read_pnm(&decoded, &c.output.image)?, bytes.len() as u64))
            },
        )?
    } else {
        // Stage warm codestream once; each measured journey includes process launch and output IO.
        fs::write(&stream, input).map_err(|e| e.to_string())?;
        run_samples(
            r,
            || {
                command(&expand, &expand_args(&stream))?;
                read_pnm(&decoded, &c.output.image)
            },
            |pixels| Ok((pixels, c.output.image.byte_count().unwrap() as u64)),
        )?
    };
    // /proc/self would observe the wrapper, not the codec child. Do not mislabel it.
    response.peak_rss_bytes = None;
    record_encode_profile(&mut response, "ht", levels, "none");
    Ok(response)
}
fn main() {
    main_worker(run);
}
