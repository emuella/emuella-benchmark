use emuella_benchmark::contract::*;
use emuella_benchmark_workers::*;
use std::{
    ffi::{c_int, c_void},
    ptr,
};
unsafe extern "C" {
    fn benchmark_openjpeg_free(p: *mut c_void);
    fn benchmark_openjpeg_encode(
        samples: *const i32,
        w: u32,
        h: u32,
        components: u32,
        bits: u32,
        levels: c_int,
        lossless: c_int,
        ratio: f64,
        threads: c_int,
        out: *mut *mut u8,
        len: *mut usize,
    ) -> c_int;
    fn benchmark_openjpeg_decode(
        input: *const u8,
        len: usize,
        source_w: u32,
        source_h: u32,
        w: u32,
        h: u32,
        components: u32,
        bits: u32,
        reduction: c_int,
        roi: c_int,
        x0: u32,
        y0: u32,
        x1: u32,
        y1: u32,
        threads: c_int,
        out: *mut *mut i32,
    ) -> c_int;
}
fn decode(input: &[u8], c: &Case) -> Result<Vec<u8>> {
    let i = &c.output.image;
    let region = c.output.region.as_ref();
    let mut out = ptr::null_mut();
    // The C adapter owns this allocation until copied and released. Dimensions are validated.
    unsafe {
        if benchmark_openjpeg_decode(
            input.as_ptr(),
            input.len(),
            c.image.width,
            c.image.height,
            i.width,
            i.height,
            u32::from(i.components),
            u32::from(i.precision),
            i32::from(c.output.reduction),
            i32::from(region.is_some()),
            region.map_or(0, |r| r.x),
            region.map_or(0, |r| r.y),
            region.map_or(0, |r| r.x + r.width),
            region.map_or(0, |r| r.y + r.height),
            i32::from(c.threads),
            &mut out,
        ) == 0
        {
            return Err("OpenJPEG decode failed or output geometry/precision differs".into());
        }
        let samples = std::slice::from_raw_parts(out, i.sample_count().unwrap());
        if samples
            .iter()
            .any(|x| *x < 0 || *x >= (1_i32 << i.precision))
        {
            benchmark_openjpeg_free(out.cast());
            return Err("decoded sample outside declared precision".into());
        }
        let mut result = Vec::with_capacity(i.byte_count().unwrap());
        for &sample in samples {
            if i.precision == 8 {
                result.push(sample as u8);
            } else {
                result.extend_from_slice(&(sample as u16).to_le_bytes());
            }
        }
        benchmark_openjpeg_free(out.cast());
        Ok(result)
    }
}
fn run(r: &WorkerRequest) -> Result<WorkerResponse> {
    validate(
        r,
        Boundary::CodecOperation,
        &[
            "coding",
            "decomposition_levels",
            "target_bpp",
            "compression_ratio",
        ],
    )?;
    let c = &r.case;
    if c.image.width > i32::MAX as u32 || c.image.height > i32::MAX as u32 {
        return Err("unsupported OpenJPEG signed coordinate range".into());
    }
    if string(c, "coding", "classic")? != "classic" {
        return Err("unsupported coding family: OpenJPEG supports classic".into());
    }
    if c.settings.contains_key("target_bpp") && c.settings.contains_key("compression_ratio") {
        return Err("unsupported simultaneous target_bpp and compression_ratio".into());
    }
    if c.operation == Operation::Decode && c.settings.keys().any(|k| k != "coding") {
        return Err("unsupported decode encoder settings".into());
    }
    if c.output.lossless
        && (c.settings.contains_key("target_bpp") || c.settings.contains_key("compression_ratio"))
    {
        return Err("unsupported lossless rate setting".into());
    }
    let levels = levels(c, 2)?;
    let ratio = if c.operation == Operation::Encode && !c.output.lossless {
        if c.settings.contains_key("target_bpp") {
            f64::from(c.image.precision) * f64::from(c.image.components)
                / number(c, "target_bpp", 1.0)?
        } else if c.settings.contains_key("compression_ratio") {
            number(c, "compression_ratio", 1.0)?
        } else {
            return Err("unsupported lossy encode without rate setting".into());
        }
    } else {
        1.0
    };
    if ratio < 1.0 || ratio > f64::from(f32::MAX) {
        return Err("unsupported compression ratio outside 1..f32::MAX".into());
    }
    let input = asset(&c.input)?;
    let samples = if c.operation == Operation::Encode {
        raw(&input, &c.image)?
    } else {
        vec![]
    };
    let encode = || -> Result<Vec<u8>> {
        let i = &c.image;
        let mut out = ptr::null_mut();
        let mut len = 0;
        // Input remains borrowed throughout C execution; successful output is owned and freed once.
        unsafe {
            if benchmark_openjpeg_encode(
                samples.as_ptr(),
                i.width,
                i.height,
                u32::from(i.components),
                u32::from(i.precision),
                i32::from(levels),
                i32::from(c.output.lossless),
                ratio,
                i32::from(c.threads),
                &mut out,
                &mut len,
            ) == 0
            {
                return Err("OpenJPEG encode failed".into());
            }
            let result = std::slice::from_raw_parts(out, len).to_vec();
            benchmark_openjpeg_free(out.cast());
            Ok(result)
        }
    };
    let mut result = if c.operation == Operation::Encode {
        run_samples(r, encode, |stream| {
            Ok((
                raw(&decode(&stream, c)?, &c.output.image)?,
                stream.len() as u64,
            ))
        })
    } else {
        run_samples(
            r,
            || decode(&input, c),
            |samples| {
                Ok((
                    raw(&samples, &c.output.image)?,
                    c.output.image.byte_count().unwrap() as u64,
                ))
            },
        )
    }?;
    record_encode_profile(&mut result, "classic", levels, "none");
    record_unsupported_diagnostics(&mut result, r, "OpenJPEG");
    Ok(result)
}
fn main() {
    main_worker(run);
}
