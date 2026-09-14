//! One fresh-process sample with matching owned interleaved buffer boundaries.
// Link the worker library so Cargo carries its native adapter link directives.
use emuella_benchmark_workers as _;
use emuella_j2k as codec;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{ffi::c_void, io::Write, path::PathBuf, ptr, time::Instant};

type Result<T> = std::result::Result<T, String>;
unsafe extern "C" {
    fn benchmark_openjpeg_free(p: *mut c_void);
    fn benchmark_openjpeg_encode_profile(
        samples: *const i32,
        w: u32,
        h: u32,
        components: u32,
        bits: u32,
        levels: i32,
        lossless: i32,
        ratio: f64,
        threads: i32,
        style: i32,
        mct: i32,
        out: *mut *mut u8,
        len: *mut usize,
    ) -> i32;
    fn benchmark_openjpeg_decode(
        input: *const u8,
        len: usize,
        source_w: u32,
        source_h: u32,
        w: u32,
        h: u32,
        components: u32,
        bits: u32,
        reduction: i32,
        roi: i32,
        x0: u32,
        y0: u32,
        x1: u32,
        y1: u32,
        threads: i32,
        out: *mut *mut i32,
    ) -> i32;
}
fn hash(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
fn err(e: impl std::fmt::Debug) -> String {
    format!("{e:?}")
}

// Compile this control into a separate diagnostic executable only. The ordinary
// facade worker performs no environment lookup, control IO or sampling branch.
#[cfg(feature = "classic-encode-sampling")]
struct Sampling {
    control: std::fs::File,
    acknowledgement: std::io::BufReader<std::fs::File>,
}
#[cfg(feature = "classic-encode-sampling")]
impl Sampling {
    fn open() -> Result<Self> {
        let path = |key| std::env::var_os(key).ok_or_else(|| format!("missing {key}"));
        Ok(Self {
            control: std::fs::OpenOptions::new()
                .write(true)
                .open(path("EMUELLA_PERF_CONTROL")?)
                .map_err(err)?,
            acknowledgement: std::io::BufReader::new(
                std::fs::File::open(path("EMUELLA_PERF_ACK")?).map_err(err)?,
            ),
        })
    }
    fn command(&mut self, command: &[u8]) -> Result<()> {
        use std::io::BufRead;
        self.control.write_all(command).map_err(err)?;
        self.control.flush().map_err(err)?;
        let mut acknowledgement = String::new();
        self.acknowledgement
            .read_line(&mut acknowledgement)
            .map_err(err)?;
        // perf's FIFO acknowledgement may include a trailing NUL after its
        // newline; read_line leaves that byte for the following acknowledgement.
        if acknowledgement.trim_matches(|c: char| c.is_ascii_whitespace() || c == '\0') != "ack" {
            return Err("perf did not acknowledge sampling control".into());
        }
        Ok(())
    }
}
struct Request {
    codec: String,
    operation: String,
    case_id: String,
    round: u64,
    width: u32,
    height: u32,
    components: u16,
    bits: u8,
    style: u8,
    workers: u8,
    raw_path: PathBuf,
    raw_sha256: String,
    stream_path: PathBuf,
    stream_sha256: Option<String>,
    limits: codec::LosslessEncodeLimits,
}
impl Request {
    fn parse(v: Value) -> Result<Self> {
        let o = v.as_object().ok_or("request must be an object")?;
        let fields = [
            "codec",
            "operation",
            "case_id",
            "round",
            "width",
            "height",
            "components",
            "bits",
            "layout",
            "style",
            "workers",
            "raw_path",
            "raw_sha256",
            "stream_path",
            "stream_sha256",
            "max_working_bytes",
            "max_output_bytes",
        ];
        if o.keys().any(|k| !fields.contains(&k.as_str())) {
            return Err("unknown request field".into());
        }
        let string = |k: &str| -> Result<String> {
            o.get(k)
                .and_then(Value::as_str)
                .filter(|s| !s.is_empty())
                .map(str::to_owned)
                .ok_or_else(|| format!("missing or invalid {k}"))
        };
        let number = |k: &str| -> Result<u64> {
            o.get(k)
                .and_then(Value::as_u64)
                .ok_or_else(|| format!("missing or invalid {k}"))
        };
        if string("layout")? != "interleaved" {
            return Err("layout must be interleaved".into());
        }
        let r = Self {
            codec: string("codec")?,
            operation: string("operation")?,
            case_id: string("case_id")?,
            round: number("round")?,
            width: number("width")?.try_into().map_err(err)?,
            height: number("height")?.try_into().map_err(err)?,
            components: number("components")?.try_into().map_err(err)?,
            bits: number("bits")?.try_into().map_err(err)?,
            style: number("style")?.try_into().map_err(err)?,
            workers: number("workers")?.try_into().map_err(err)?,
            raw_path: string("raw_path")?.into(),
            raw_sha256: string("raw_sha256")?,
            stream_path: string("stream_path")?.into(),
            stream_sha256: if o.contains_key("stream_sha256") {
                Some(string("stream_sha256")?)
            } else {
                None
            },
            limits: codec::LosslessEncodeLimits {
                max_working_bytes: number("max_working_bytes")?,
                max_output_bytes: number("max_output_bytes")?,
            },
        };
        if !["emuella", "openjpeg"].contains(&r.codec.as_str())
            || !["prepare", "encode", "decode"].contains(&r.operation.as_str())
            || !(4..=32768).contains(&r.width)
            || !(4..=32768).contains(&r.height)
            || ![1, 3, 8].contains(&r.components)
            || ![8, 16].contains(&r.bits)
            || (r.components == 8 && r.bits != 16)
            || r.style > 1
            || ![1, 8].contains(&r.workers)
            || r.limits.max_working_bytes == 0
            || r.limits.max_output_bytes == 0
        {
            return Err("unsupported comparison settings or geometry".into());
        }
        if (r.operation == "prepare") != r.stream_sha256.is_none() {
            return Err("stream_sha256 required only for encode/decode".into());
        }
        for digest in std::iter::once(&r.raw_sha256).chain(r.stream_sha256.iter()) {
            if digest.len() != 64
                || !digest
                    .bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
            {
                return Err("SHA-256 must be lowercase hex".into());
            }
        }
        Ok(r)
    }
    fn sample_count(&self) -> usize {
        self.width as usize * self.height as usize * self.components as usize
    }
    fn byte_count(&self) -> usize {
        self.sample_count() * usize::from(self.bits / 8)
    }
    fn info(&self) -> Result<codec::ImageInfo> {
        codec::ImageInfo::new(
            self.width,
            self.height,
            self.components,
            if self.bits == 8 {
                codec::SampleFormat::U8
            } else {
                codec::SampleFormat::U16_LE
            },
            match self.components {
                1 => codec::ColorModel::Grayscale,
                3 => codec::ColorModel::Rgb,
                _ => codec::ColorModel::Unknown,
            },
            codec::ComponentLayout::Interleaved,
        )
        .map_err(err)
    }
    fn options(&self) -> codec::EncodeOptions {
        codec::EncodeOptions {
            format: codec::OutputFormat::J2kCodestream,
            decomposition_levels: 2,
            transform: codec::WaveletTransform::Reversible53,
            quality: codec::EncodeQuality::Lossless,
            ..Default::default()
        }
    }
}
fn encode(r: &Request, raw: &[u8]) -> Result<Vec<u8>> {
    if r.codec == "emuella" {
        let info = r.info()?;
        let view = codec::ImageView::Interleaved {
            info: &info,
            samples: raw,
            stride_bytes: r.byte_count() / r.height as usize,
        };
        return if r.style == 0 {
            codec::encode_with_limits(view, &r.options(), &r.limits)
        } else {
            codec::encode_lossless_bypass_with_limits(view, &r.options(), &r.limits)
        }
        .map_err(err);
    }
    // Conversion is deliberately inside the timed owned-buffer boundary.
    let samples: Vec<i32> = if r.bits == 8 {
        raw.iter().map(|&v| i32::from(v)).collect()
    } else {
        raw.chunks_exact(2)
            .map(|v| i32::from(u16::from_le_bytes([v[0], v[1]])))
            .collect()
    };
    let mut out = ptr::null_mut();
    let mut len = 0;
    // The adapter borrows samples and returns a malloc-owned allocation, freed once.
    unsafe {
        if benchmark_openjpeg_encode_profile(
            samples.as_ptr(),
            r.width,
            r.height,
            r.components.into(),
            r.bits.into(),
            2,
            1,
            1.0,
            r.workers.into(),
            r.style.into(),
            i32::from(r.components == 3),
            &mut out,
            &mut len,
        ) == 0
        {
            return Err("OpenJPEG encode failed".into());
        }
        if len as u64 > r.limits.max_output_bytes {
            benchmark_openjpeg_free(out.cast());
            return Err("output limit exceeded".into());
        }
        let bytes = std::slice::from_raw_parts(out, len).to_vec();
        benchmark_openjpeg_free(out.cast());
        Ok(bytes)
    }
}
fn decode(r: &Request, stream: &[u8]) -> Result<Vec<u8>> {
    if r.codec == "emuella" {
        let image = codec::decode(
            stream,
            &codec::DecodeOptions {
                mode: codec::DecodeMode::Components,
                target_layout: codec::ComponentLayout::Interleaved,
                ..Default::default()
            },
        )
        .map_err(err)?;
        let expected = r.info()?;
        if image.info.width != r.width
            || image.info.height != r.height
            || image.info.components != r.components
            || image.info.sample_format != expected.sample_format
        {
            return Err("decoded metadata mismatch".into());
        }
        return match image.data {
            codec::ImageData::Interleaved(bytes) => Ok(bytes),
            _ => Err("decoder did not return interleaved bytes".into()),
        };
    }
    let mut out = ptr::null_mut();
    // The adapter returns checked, full-resolution interleaved i32 samples.
    unsafe {
        if benchmark_openjpeg_decode(
            stream.as_ptr(),
            stream.len(),
            r.width,
            r.height,
            r.width,
            r.height,
            r.components.into(),
            r.bits.into(),
            0,
            0,
            0,
            0,
            r.width,
            r.height,
            r.workers.into(),
            &mut out,
        ) == 0
        {
            return Err("OpenJPEG decode failed".into());
        }
        let samples = std::slice::from_raw_parts(out, r.sample_count());
        let mut bytes = Vec::with_capacity(r.byte_count());
        for &v in samples {
            if v < 0 || v >= (1 << r.bits) {
                benchmark_openjpeg_free(out.cast());
                return Err("sample outside precision".into());
            }
            if r.bits == 8 {
                bytes.push(v as u8);
            } else {
                bytes.extend_from_slice(&(v as u16).to_le_bytes());
            }
        }
        benchmark_openjpeg_free(out.cast());
        Ok(bytes)
    }
}
// Inspect actual marker facts, including tile headers, independently of codec metadata APIs.
fn inspect(r: &Request, bytes: &[u8]) -> Result<Value> {
    let invalid = || "codestream does not match requested classic D2 profile".to_owned();
    if bytes.get(..2) != Some(&[0xff, 0x4f]) {
        return Err(invalid());
    }
    let mut p = 2;
    let mut siz = false;
    let mut cod = false;
    let mut qcd = false;
    let mut tiles = 0;
    let u16be = |s: &[u8]| u16::from_be_bytes([s[0], s[1]]);
    let u32be = |s: &[u8]| u32::from_be_bytes([s[0], s[1], s[2], s[3]]);
    while p < bytes.len() {
        let marker = bytes.get(p..p + 2).ok_or_else(invalid)?;
        if marker == [0xff, 0xd9] {
            if p + 2 != bytes.len() {
                return Err(invalid());
            }
            break;
        }
        if marker[0] != 0xff {
            return Err(invalid());
        }
        let len = usize::from(u16be(bytes.get(p + 2..p + 4).ok_or_else(invalid)?));
        if len < 2 {
            return Err(invalid());
        }
        let body = bytes.get(p + 4..p + 2 + len).ok_or_else(invalid)?;
        match marker[1] {
            0x51 => {
                if siz || tiles != 0 || body.len() != 36 + 3 * usize::from(r.components) {
                    return Err(invalid());
                }
                let expected = [r.width, r.height, 0, 0, r.width, r.height, 0, 0];
                if u16be(&body[..2]) != 0
                    || body[2..34]
                        .chunks_exact(4)
                        .zip(expected)
                        .any(|(s, e)| u32be(s) != e)
                    || u16be(&body[34..36]) != r.components
                    || body[36..].chunks_exact(3).any(|s| s != [r.bits - 1, 1, 1])
                {
                    return Err(invalid());
                }
                siz = true;
            }
            0x52 => {
                if cod
                    || tiles != 0
                    || body != [0, 0, 0, 1, u8::from(r.components == 3), 2, 4, 4, r.style, 1]
                {
                    return Err(invalid());
                }
                cod = true;
            }
            0x53 | 0x5e => return Err(invalid()), // No component coding or progression overrides.
            0x90 => {
                if !siz
                    || !cod
                    || tiles != 0
                    || body.len() != 8
                    || u16be(&body[..2]) != 0
                    || body[6..] != [0, 1]
                {
                    return Err(invalid());
                }
                let tile_len = u32be(&body[2..6]) as usize;
                let end = p
                    .checked_add(tile_len)
                    .filter(|&e| e <= bytes.len())
                    .ok_or_else(invalid)?;
                if tile_len < 14 {
                    return Err(invalid());
                }
                // Encoders in this profile emit no tile-header overrides, only SOD.
                if bytes.get(p + 12..p + 14) != Some(&[0xff, 0x93]) {
                    return Err(invalid());
                }
                tiles += 1;
                p = end;
                continue;
            }
            0x5c => {
                if qcd || tiles != 0 || body.len() != 8 || body[0] & 31 != 0 {
                    return Err(invalid());
                }
                qcd = true;
            }
            0x64 => {} // Optional comment has no coding effect.
            _ => return Err(invalid()),
        }
        p += 2 + len;
    }
    if !siz || !cod || !qcd || tiles != 1 || bytes.get(p..p + 2) != Some(&[0xff, 0xd9]) {
        return Err(invalid());
    }
    Ok(
        json!({"format":"raw_j2k", "coding":"classic", "decomposition_levels":2,
        "tiles":1,"layers":1,"progression":"LRCP","code_block_width":64,"code_block_height":64,
        "precincts":"default","transform":"reversible_5_3","mct":if r.components==3 {"reversible_colour_transform"} else {"none"},
        "style":r.style,"layout":"interleaved","bits":r.bits,"components":r.components}),
    )
}
fn asset(path: &std::path::Path, expected: &str, max: u64) -> Result<Vec<u8>> {
    if std::fs::metadata(path).map_err(err)?.len() > max {
        return Err("input exceeds admitted size".into());
    }
    let bytes = std::fs::read(path).map_err(err)?;
    if bytes.len() as u64 > max || hash(&bytes) != expected {
        return Err("input size or SHA-256 mismatch".into());
    }
    Ok(bytes)
}
fn run(r: Request) -> Result<Value> {
    // Configure the global pool once. The main thread calls public APIs directly.
    rayon::ThreadPoolBuilder::new()
        .num_threads(usize::from(r.workers))
        .build_global()
        .map_err(err)?;
    // Same conservative geometry admission for both codecs. This is not an OpenJPEG RSS cap.
    let info = r.info()?;
    if r.style == 0 {
        codec::lossless_encode_requirements(&info, &r.options(), &r.limits)
    } else {
        codec::lossless_bypass_encode_requirements(&info, &r.options(), &r.limits)
    }
    .map_err(err)?;
    let raw = asset(&r.raw_path, &r.raw_sha256, r.byte_count() as u64)?;
    if raw.len() != r.byte_count() {
        return Err("raw byte count mismatch".into());
    }
    let binary_sha256 = hash(&std::fs::read(std::env::current_exe().map_err(err)?).map_err(err)?);
    let input = if r.operation != "prepare" {
        Some(asset(
            &r.stream_path,
            r.stream_sha256.as_deref().unwrap(),
            r.limits.max_output_bytes,
        )?)
    } else {
        None
    };
    if let Some(bytes) = &input {
        inspect(&r, bytes)?;
    }
    #[cfg(feature = "classic-encode-sampling")]
    let mut sampling = {
        if r.operation != "encode" || r.codec != "emuella" || r.workers != 1 {
            return Err("sampling requires one-worker Emuella encode".into());
        }
        let mut sampling = Sampling::open()?;
        sampling.command(b"enable\n")?;
        sampling
    };
    let start = Instant::now();
    let output = if r.operation == "decode" {
        decode(&r, input.as_ref().unwrap())?
    } else {
        encode(&r, &raw)?
    };
    let ns = u64::try_from(start.elapsed().as_nanos()).map_err(err)?;
    #[cfg(feature = "classic-encode-sampling")]
    sampling.command(b"disable\n")?;
    let (stream, pixels) = if r.operation == "decode" {
        (input.unwrap(), output)
    } else {
        if output.len() as u64 > r.limits.max_output_bytes {
            return Err("output limit exceeded".into());
        }
        if r.operation == "encode" && hash(&output) != *r.stream_sha256.as_ref().unwrap() {
            return Err("encode differs from prepared stream SHA-256".into());
        }
        let pixels = decode(&r, &output)?;
        (output, pixels)
    };
    let profile = inspect(&r, &stream)?;
    if pixels != raw {
        return Err("reconstructed sample bytes differ from raw reference".into());
    }
    if r.operation == "prepare" {
        std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&r.stream_path)
            .map_err(err)?
            .write_all(&stream)
            .map_err(err)?;
    }
    Ok(
        json!({"codec":r.codec,"operation":r.operation,"case_id":r.case_id,"round":r.round,"style":r.style,"workers":r.workers,
        "boundary":"owned_interleaved_bytes_to_owned_codestream_or_interleaved_bytes", "profile":profile,
        "exact":true,"diagnostic_sampling":cfg!(feature = "classic-encode-sampling"),
        "samples_ns":if r.operation=="prepare" || cfg!(feature = "classic-encode-sampling") {vec![]} else {vec![ns]},"raw_sha256":r.raw_sha256,
        "stream_sha256":hash(&stream),"binary_sha256":binary_sha256,"stream_bytes":stream.len()}),
    )
}
fn main() {
    let result = (|| -> Result<Value> {
        let args: Vec<_> = std::env::args_os().skip(1).collect();
        if args.len() != 1 {
            return Err("usage: classic-compare-worker REQUEST.json".into());
        }
        run(Request::parse(
            serde_json::from_slice(&std::fs::read(&args[0]).map_err(err)?).map_err(err)?,
        )?)
    })();
    match result {
        Ok(value) => println!("{value}"),
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(1);
        }
    }
}
