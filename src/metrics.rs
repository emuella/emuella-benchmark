//! Sample-domain metrics. No colour conversion, perceptual weighting or hidden resampling.
use crate::{
    Result,
    contract::{Correctness, ImageSpec},
};
use std::path::Path;

pub fn read_raw(path: &Path, image: &ImageSpec) -> Result<Vec<i32>> {
    image.validate()?;
    let bytes = std::fs::read(path)?;
    if Some(bytes.len()) != image.byte_count() {
        return Err("raw image byte count differs from declared geometry".into());
    }
    let samples = if image.precision <= 8 {
        bytes
            .into_iter()
            .map(|x| {
                if image.signed {
                    i32::from(x as i8)
                } else {
                    i32::from(x)
                }
            })
            .collect::<Vec<_>>()
    } else {
        bytes
            .as_chunks::<2>()
            .0
            .iter()
            .map(|x| {
                if image.signed {
                    i32::from(i16::from_le_bytes([x[0], x[1]]))
                } else {
                    i32::from(u16::from_le_bytes([x[0], x[1]]))
                }
            })
            .collect()
    };
    validate_samples(&samples, image)?;
    Ok(samples)
}

fn validate_samples(samples: &[i32], image: &ImageSpec) -> Result<()> {
    image.validate()?;
    if Some(samples.len()) != image.sample_count() {
        return Err("sample count differs from declared geometry".into());
    }
    let (minimum, maximum) = if image.signed {
        (
            -(1_i32 << (image.precision - 1)),
            (1_i32 << (image.precision - 1)) - 1,
        )
    } else {
        (0, (1_i32 << image.precision) - 1)
    };
    if samples.iter().any(|&x| x < minimum || x > maximum) {
        return Err("sample outside declared precision".into());
    }
    Ok(())
}

pub fn measure(reference: &[i32], actual: &[i32], image: &ImageSpec) -> Result<Correctness> {
    validate_samples(reference, image)?;
    validate_samples(actual, image)?;
    let mut squared_error = 0.0;
    let mut maximum_absolute_error: f64 = 0.0;
    for (&a, &b) in reference.iter().zip(actual) {
        let delta = f64::from(a) - f64::from(b);
        squared_error += delta * delta;
        maximum_absolute_error = maximum_absolute_error.max(delta.abs());
    }
    let mse = squared_error / reference.len() as f64;
    let peak = f64::from((1_u32 << image.precision) - 1);
    Ok(Correctness {
        sample_count: reference.len() as u64,
        exact: maximum_absolute_error == 0.0,
        maximum_absolute_error,
        mse,
        peak,
        psnr_db: psnr(mse, peak),
    })
}

pub fn combine(values: &[Correctness]) -> Result<Correctness> {
    let first = values.first().ok_or("cannot combine empty metrics")?;
    let mut sample_count = 0_u64;
    let mut squared_error = 0.0;
    let mut maximum_absolute_error: f64 = 0.0;
    for value in values {
        validate(value)?;
        if value.peak != first.peak {
            return Err("metric peaks differ".into());
        }
        sample_count = sample_count
            .checked_add(value.sample_count)
            .ok_or("metric count overflow")?;
        squared_error += value.mse * value.sample_count as f64;
        maximum_absolute_error = maximum_absolute_error.max(value.maximum_absolute_error);
    }
    let mse = squared_error / sample_count as f64;
    Ok(Correctness {
        sample_count,
        exact: maximum_absolute_error == 0.0,
        maximum_absolute_error,
        mse,
        peak: first.peak,
        psnr_db: psnr(mse, first.peak),
    })
}

pub fn validate(value: &Correctness) -> Result<()> {
    if value.sample_count == 0
        || !value.mse.is_finite()
        || value.mse < 0.0
        || !value.peak.is_finite()
        || value.peak <= 0.0
        || !value.maximum_absolute_error.is_finite()
        || value.maximum_absolute_error < 0.0
        || value.maximum_absolute_error > value.peak
        || value.mse > value.peak * value.peak
        || value.exact != (value.maximum_absolute_error == 0.0)
        || value.exact != (value.mse == 0.0)
        || value.mse > value.maximum_absolute_error.powi(2) * (1.0 + 1e-12)
        || value.mse * (value.sample_count as f64)
            < value.maximum_absolute_error.powi(2) * (1.0 - 1e-12)
    {
        return Err("inconsistent correctness metrics".into());
    }
    match (value.psnr_db, psnr(value.mse, value.peak)) {
        (None, None) => Ok(()),
        (Some(a), Some(b)) if a.is_finite() && (a - b).abs() < 1e-7 => Ok(()),
        _ => Err("PSNR is inconsistent with MSE and peak".into()),
    }
}
fn psnr(mse: f64, peak: f64) -> Option<f64> {
    (mse != 0.0).then(|| 10.0 * (peak * peak / mse).log10())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn spec() -> ImageSpec {
        ImageSpec {
            width: 2,
            height: 1,
            components: 1,
            precision: 8,
            signed: false,
        }
    }
    #[test]
    fn exact_and_known_mse() {
        let exact = measure(&[0, 255], &[0, 255], &spec()).unwrap();
        assert!(exact.exact);
        assert_eq!(exact.psnr_db, None);
        let noisy = measure(&[0, 255], &[2, 253], &spec()).unwrap();
        assert_eq!(noisy.mse, 4.0);
        assert_eq!(noisy.maximum_absolute_error, 2.0);
        assert!((noisy.psnr_db.unwrap() - 42.1102036954).abs() < 1e-8);
        let combined = combine(&[exact, noisy]).unwrap();
        assert_eq!(combined.sample_count, 4);
        assert_eq!(combined.mse, 2.0);
        assert!(!combined.exact);
    }
    #[test]
    fn reject_wrong_shape_and_out_of_range() {
        assert!(measure(&[0], &[0], &spec()).is_err());
        assert!(measure(&[0, 256], &[0, 0], &spec()).is_err());
    }
}
