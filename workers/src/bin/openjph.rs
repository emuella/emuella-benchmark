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
        for x in data.as_chunks_mut::<2>().0 {
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
fn scratch_directory(base: &Path) -> Result<tempfile::TempDir> {
    // TempDir owns cleanup only after its exclusive, randomly named creation succeeds.
    tempfile::Builder::new()
        .prefix("openjph-worker-")
        .tempdir_in(base)
        .map_err(|e| e.to_string())
}
fn command_fresh(executable: &Path, args: &[String], output: &Path) -> Result<()> {
    match fs::remove_file(output) {
        Ok(()) => {}
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(e) => return Err(format!("cannot remove previous codec output: {e}")),
    }
    command(executable, args)?;
    let metadata = fs::symlink_metadata(output)
        .map_err(|e| format!("codec did not create fresh output: {e}"))?;
    if !metadata.file_type().is_file() {
        return Err("codec output is not a regular file".into());
    }
    Ok(())
}
fn run_with_tools(
    r: &WorkerRequest,
    base: &Path,
    compress: &Path,
    expand: &Path,
) -> Result<WorkerResponse> {
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
    let scratch = scratch_directory(base)?;
    let input = asset(&c.input)?;
    let source = scratch.path().join(if c.image.components == 1 {
        "source.pgm"
    } else {
        "source.ppm"
    });
    let stream = scratch.path().join("stream.j2c");
    let decoded = scratch.path().join(if c.image.components == 1 {
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
                command_fresh(compress, &args, &stream)?;
                fs::read(&stream).map_err(|e| e.to_string())
            },
            |bytes| {
                command_fresh(expand, &expand_args(&stream), &decoded)?;
                Ok((read_pnm(&decoded, &c.output.image)?, bytes.len() as u64))
            },
        )?
    } else {
        // Stage warm codestream once; each measured journey includes process launch and output IO.
        fs::write(&stream, input).map_err(|e| e.to_string())?;
        run_samples(
            r,
            || {
                command_fresh(expand, &expand_args(&stream), &decoded)?;
                read_pnm(&decoded, &c.output.image)
            },
            |pixels| Ok((pixels, c.output.image.byte_count().unwrap() as u64)),
        )?
    };
    // /proc/self would observe the wrapper, not the codec child. Do not mislabel it.
    response.peak_rss_bytes = None;
    record_encode_profile(&mut response, "ht", levels, "none");
    record_unsupported_diagnostics(&mut response, r, "OpenJPH");
    Ok(response)
}
fn run(r: &WorkerRequest) -> Result<WorkerResponse> {
    let base = std::env::var_os("EMUELLA_BENCHMARK_DERIVATIVE_STORE").ok_or(
        "unsupported application journey without explicit EMUELLA_BENCHMARK_DERIVATIVE_STORE",
    )?;
    let base = PathBuf::from(base)
        .canonicalize()
        .map_err(|e| e.to_string())?;
    if !base.is_dir() {
        return Err("derivative store must be an existing directory".into());
    }
    let compress = Path::new(option_env!("OPENJPH_COMPRESS").unwrap_or("ojph_compress"));
    let expand = Path::new(option_env!("OPENJPH_EXPAND").unwrap_or("ojph_expand"));
    run_with_tools(r, &base, compress, expand)
}
fn main() {
    main_worker(run);
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;
    use sha2::{Digest, Sha256};
    use std::{collections::BTreeMap, os::unix::fs::PermissionsExt};

    fn authored_request(base: &Path, operation: Operation) -> WorkerRequest {
        let image = ImageSpec {
            width: 2,
            height: 2,
            components: 1,
            precision: 8,
            signed: false,
        };
        let samples = vec![0_u8, 17, 128, 255];
        let reference_path = base.join("reference.raw");
        fs::write(&reference_path, &samples).unwrap();
        let reference = Asset {
            path: reference_path,
            sha256: format!("{:x}", Sha256::digest(&samples)),
            provenance: BTreeMap::new(),
        };
        let input = if operation == Operation::Encode {
            reference.clone()
        } else {
            // Authored stand-in consumed by the fault-injection command, not a codec fixture.
            let bytes = pnm(&samples, &image).unwrap();
            let path = base.join("authored-command-input");
            fs::write(&path, &bytes).unwrap();
            Asset {
                path,
                sha256: format!("{:x}", Sha256::digest(&bytes)),
                provenance: BTreeMap::new(),
            }
        };
        let mut settings = BTreeMap::from([("coding".into(), serde_json::json!("ht"))]);
        if operation == Operation::Encode {
            settings.insert("decomposition_levels".into(), serde_json::json!(0));
        }
        WorkerRequest {
            schema_version: SCHEMA_VERSION,
            request_id: "fault-probe".into(),
            case: Case {
                id: "authored".into(),
                input,
                reference: Some(reference),
                image: image.clone(),
                operation,
                settings,
                threads: 1,
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
            },
            protocol: Protocol {
                boundary: Boundary::ApplicationJourney,
                warmup: 1,
                samples_per_batch: 2,
                ..Default::default()
            },
            diagnostic: false,
        }
    }
    fn command_script(base: &Path, name: &str, stop_after_warmup: bool) -> PathBuf {
        let path = base.join(name);
        let script = format!(
            r#"#!/bin/sh
set -eu
input=''
output=''
while [ "$#" -gt 0 ]; do
    case "$1" in
        -i) input="$2"; shift 2 ;;
        -o) output="$2"; shift 2 ;;
        *) shift ;;
    esac
done
if [ -f "$0.called" ] && [ '{}' = true ]; then exit 0; fi
: > "$0.called"
cp "$input" "$output"
"#,
            stop_after_warmup
        );
        fs::write(&path, script).unwrap();
        fs::set_permissions(&path, fs::Permissions::from_mode(0o700)).unwrap();
        path
    }
    #[test]
    fn existing_scratch_collision_preserves_its_sentinel() {
        let base = tempfile::tempdir().unwrap();
        let old_name = base
            .path()
            .join(format!("openjph-worker-{}", std::process::id()));
        fs::create_dir(&old_name).unwrap();
        fs::write(old_name.join("sentinel"), b"unrelated contents").unwrap();
        let owned = scratch_directory(base.path()).unwrap();
        assert_ne!(owned.path(), old_name);
        let owned_path = owned.path().to_path_buf();
        drop(owned);
        assert!(!owned_path.exists());
        assert_eq!(
            fs::read(old_name.join("sentinel")).unwrap(),
            b"unrelated contents"
        );
        // A failed exclusive creation must likewise leave the existing directory intact.
        assert!(
            tempfile::Builder::new()
                .prefix(old_name.file_name().unwrap())
                .rand_bytes(0)
                .tempdir_in(base.path())
                .is_err()
        );
        assert_eq!(
            fs::read(old_name.join("sentinel")).unwrap(),
            b"unrelated contents"
        );
    }
    #[test]
    fn successful_compressor_without_new_output_fails_after_warmup() {
        let base = tempfile::tempdir().unwrap();
        let request = authored_request(base.path(), Operation::Encode);
        let compress = command_script(base.path(), "compress", true);
        let expand = command_script(base.path(), "expand", false);
        let error = run_with_tools(&request, base.path(), &compress, &expand).unwrap_err();
        assert!(error.contains("did not create fresh output"), "{error}");
    }
    #[test]
    fn successful_verification_decoder_without_new_output_fails_after_warmup() {
        let base = tempfile::tempdir().unwrap();
        let request = authored_request(base.path(), Operation::Encode);
        let compress = command_script(base.path(), "compress", false);
        let expand = command_script(base.path(), "expand", true);
        let error = run_with_tools(&request, base.path(), &compress, &expand).unwrap_err();
        assert!(error.contains("did not create fresh output"), "{error}");
    }
    #[test]
    fn successful_measured_decoder_without_new_output_fails_after_warmup() {
        let base = tempfile::tempdir().unwrap();
        let request = authored_request(base.path(), Operation::Decode);
        let compress = command_script(base.path(), "compress", false);
        let expand = command_script(base.path(), "expand", true);
        let error = run_with_tools(&request, base.path(), &compress, &expand).unwrap_err();
        assert!(error.contains("did not create fresh output"), "{error}");
    }
    #[test]
    fn diagnostic_capability_is_explicit_for_encode_and_decode() {
        for operation in [Operation::Encode, Operation::Decode] {
            let base = tempfile::tempdir().unwrap();
            let mut request = authored_request(base.path(), operation);
            request.diagnostic = true;
            let compress = command_script(base.path(), "compress", false);
            let expand = command_script(base.path(), "expand", false);
            let result = run_with_tools(&request, base.path(), &compress, &expand).unwrap();
            emuella_benchmark::runner::validate_response(&request, &result).unwrap();
            assert_eq!(result.status, WorkerStatus::Ok);
            assert!(
                result.diagnostics["unsupported_reason"]
                    .as_str()
                    .unwrap()
                    .contains("OpenJPH")
            );
            assert_eq!(result.samples_ns.len(), 2);
        }
    }
}
