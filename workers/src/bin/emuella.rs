use emuella_benchmark::contract::*;
use emuella_benchmark_workers::*;
use emuella_j2k as codec;
use emuella_j2k_codestream as diagnostic;

fn error(e: codec::J2kError) -> String {
    if let codec::J2kError::Unsupported { detail, .. } = &e
        && [
            "target-rate budget is smaller than the irreducible valid codestream",
            "target-rate budget is not attainable within the qualified non-padding tolerance",
            "irreversible HT target rate is unattainable within the bounded non-padding tolerance",
        ]
        .contains(&detail.as_str())
    {
        return format!("unattainable_rate: {detail}");
    }
    let text = format!("{e:?}");
    if text.starts_with("Unsupported") {
        format!("unsupported codec profile: {text}")
    } else {
        text
    }
}
fn partial(c: &Case) -> codec::PartialDecodeOptions {
    codec::PartialDecodeOptions {
        region: c.output.region.as_ref().map(|r| codec::Region {
            x: r.x,
            y: r.y,
            width: r.width,
            height: r.height,
        }),
        resolution: if c.output.reduction == 0 {
            codec::ResolutionLevel::Full
        } else {
            codec::ResolutionLevel::Reduced {
                discard_levels: c.output.reduction,
            }
        },
        ..Default::default()
    }
}
fn pixels(image: codec::Image, expected: &ImageSpec) -> Result<Vec<u8>> {
    let info = &image.info;
    if info.width != expected.width
        || info.height != expected.height
        || info.components != expected.components
        || info.sample_format.bits_per_sample != expected.precision
        || info.sample_format.signed != expected.signed
    {
        return Err("decoded output metadata differs from requested semantics".into());
    }
    match image.data {
        codec::ImageData::Interleaved(x) => Ok(x),
        codec::ImageData::Planes(planes) => {
            let bytes = usize::from(expected.precision / 8);
            let count = expected.width as usize * expected.height as usize;
            if planes.len() != usize::from(expected.components)
                || planes.iter().any(|p| p.len() != count * bytes)
            {
                return Err("non-uniform output component geometry".into());
            }
            let mut packed = Vec::with_capacity(expected.byte_count().unwrap());
            for pixel in 0..count {
                for plane in &planes {
                    packed.extend_from_slice(&plane[pixel * bytes..(pixel + 1) * bytes]);
                }
            }
            Ok(packed)
        }
    }
}
fn decode(bytes: &[u8], c: &Case) -> Result<Vec<u8>> {
    let image = if c.output.region.is_some() || c.output.reduction != 0 {
        codec::decode_partial(bytes, &partial(c))
    } else {
        codec::decode(
            bytes,
            &codec::DecodeOptions {
                mode: codec::DecodeMode::Components,
                target_layout: codec::ComponentLayout::Interleaved,
                ..Default::default()
            },
        )
    }
    .map_err(error)?;
    pixels(image, &c.output.image)
}
fn run(r: &WorkerRequest) -> Result<WorkerResponse> {
    validate(
        r,
        Boundary::CodecOperation,
        &["coding", "decomposition_levels", "target_bpp"],
    )?;
    let c = &r.case;
    let coding = string(c, "coding", "classic")?;
    if !["classic", "ht"].contains(&coding) {
        return Err("unsupported coding family".into());
    }
    if c.operation == Operation::Decode
        && (c.settings.contains_key("decomposition_levels")
            || c.settings.contains_key("target_bpp"))
    {
        return Err("unsupported decode encoder settings".into());
    }
    if c.output.lossless && c.settings.contains_key("target_bpp") {
        return Err("unsupported lossless target_bpp".into());
    }
    let levels = levels(c, if c.output.lossless { 0 } else { 2 })?;
    if !c.output.lossless && c.operation == Operation::Encode && levels != 2 {
        return Err("unsupported lossy decomposition count (requires 2)".into());
    }
    let rate = if !c.output.lossless && c.operation == Operation::Encode {
        if !c.settings.contains_key("target_bpp") {
            return Err("unsupported lossy encode without target_bpp".into());
        }
        let rate = number(c, "target_bpp", 1.0)?;
        if (rate as f32) as f64 != rate {
            return Err("unsupported target_bpp: must be exactly representable as f32".into());
        }
        rate as f32
    } else {
        1.0
    };
    let input = asset(&c.input)?;
    if c.operation == Operation::Decode {
        let metadata = codec::inspect(&input, &codec::InspectOptions::default()).map_err(error)?;
        let actual = metadata
            .image
            .ok_or("codec did not report input geometry")?;
        if actual.width != c.image.width
            || actual.height != c.image.height
            || actual.components != c.image.components
            || actual.sample_format.bits_per_sample != c.image.precision
            || actual.sample_format.signed != c.image.signed
        {
            return Err("input metadata differs from declared source image".into());
        }
        let expected = if coding == "classic" {
            codec::EntropyCoder::ClassicTier1
        } else {
            codec::EntropyCoder::HtBlockCoding
        };
        if metadata.codestream.and_then(|x| x.entropy_coder) != Some(expected) {
            return Err("input coding family differs from requested coding".into());
        }
    }
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(usize::from(c.threads))
        .build()
        .map_err(|e| e.to_string())?;
    let info = codec::ImageInfo::new(
        c.image.width,
        c.image.height,
        c.image.components,
        if c.image.precision == 8 {
            codec::SampleFormat::U8
        } else {
            codec::SampleFormat::U16_LE
        },
        if c.image.components == 1 {
            codec::ColorModel::Grayscale
        } else {
            codec::ColorModel::Rgb
        },
        codec::ComponentLayout::Interleaved,
    )
    .map_err(error)?;
    if c.operation == Operation::Encode {
        raw(&input, &c.image)?;
    }
    let encode = || {
        let view = codec::ImageView::Interleaved {
            info: &info,
            samples: &input,
            stride_bytes: c.image.width as usize
                * usize::from(c.image.components)
                * usize::from(c.image.precision / 8),
        };
        match (coding, c.output.lossless) {
            ("ht", true) => codec::encode_htj2k(
                view,
                &codec::Htj2kEncodeOptions {
                    decomposition_levels: levels,
                },
            ),
            ("ht", false) => codec::encode_htj2k_lossy(
                view,
                &codec::Htj2kLossyEncodeOptions {
                    bits_per_pixel: rate,
                },
            ),
            _ => codec::encode(
                view,
                &codec::EncodeOptions {
                    format: codec::OutputFormat::J2kCodestream,
                    decomposition_levels: levels,
                    transform: if c.output.lossless {
                        codec::WaveletTransform::Reversible53
                    } else {
                        codec::WaveletTransform::Irreversible97
                    },
                    quality: if c.output.lossless {
                        codec::EncodeQuality::Lossless
                    } else {
                        codec::EncodeQuality::TargetRate {
                            bits_per_pixel: rate,
                        }
                    },
                    ..Default::default()
                },
            ),
        }
        .map_err(error)
    };
    let mut result = pool.install(|| {
        if c.operation == Operation::Encode {
            run_samples(r, encode, |stream| {
                let len = stream.len() as u64;
                Ok((raw(&decode(&stream, c)?, &c.output.image)?, len))
            })
        } else {
            run_samples(
                r,
                || decode(&input, c),
                |bytes| Ok((raw(&bytes, &c.output.image)?, bytes.len() as u64)),
            )
        }
    })?;
    if r.diagnostic {
        let stream = if c.operation == Operation::Encode {
            pool.install(encode)?
        } else {
            input
        };
        match pool.install(|| codec::prepare_part1_decode(&stream, &partial(c))) {
            Ok(plan) => {
                result.diagnostics.insert(
                    "prepared_memory".into(),
                    serde_json::json!(format!("{:?}", plan.memory_accounting())),
                );
                result.diagnostics.insert(
                    "prepared_parallelism".into(),
                    serde_json::json!(format!("{:?}", plan.execution_parallelism())),
                );
                result.diagnostics.insert(
                    "preparation_timings".into(),
                    serde_json::json!(format!("{:?}", plan.preparation_timings())),
                );
                let info = plan.info().clone();
                let stride =
                    info.width as usize * usize::from(info.sample_format.bits_per_sample / 8);
                let mut buffers =
                    vec![vec![0_u8; stride * info.height as usize]; usize::from(info.components)];
                let mut planes = buffers
                    .iter_mut()
                    .map(|b| {
                        codec::PlaneMut::new(b, info.width, info.height, stride, info.sample_format)
                    })
                    .collect::<codec::Result<Vec<_>>>()
                    .map_err(error)?;
                let mut target = codec::ImageViewMut::Planar {
                    info: &info,
                    planes: &mut planes,
                };
                let mut workspace = codec::Part1DecodeWorkspace::new();
                let counters = pool.install(|| {
                    codec::execute_prepared_part1_decode_into_with_workspace(
                        &plan,
                        &mut target,
                        &mut workspace,
                        diagnostic::PreparedPart1ExecutionOptions {
                            instrumentation: diagnostic::DecodeInstrumentation::DetailedProfile,
                            collect_tier1_work_counters: true,
                            parallelism: diagnostic::DecodeExecutionParallelism::MaxWorkers(
                                usize::from(c.threads),
                            ),
                            ..Default::default()
                        },
                    )
                });
                match counters {
                    Ok(work) => {
                        let diagnostic_pixels = pixels(
                            codec::Image {
                                info: info.clone(),
                                component_info: plan.component_info().to_vec(),
                                data: codec::ImageData::Planes(buffers),
                            },
                            &c.output.image,
                        )?;
                        if diagnostic_pixels != pool.install(|| decode(&stream, c))? {
                            return Err(
                                "diagnostic prepared output differs from headline decode".into()
                            );
                        }
                        result
                            .diagnostics
                            .insert("execution_output_verified".into(), serde_json::json!(true));
                        result.diagnostics.insert("execution_work".into(),serde_json::json!({
                            "code_blocks_decoded":work.code_blocks_decoded,"tier1_coefficients":work.tier1_coefficients,
                            "tier1_codeword_bytes":work.tier1_codeword_bytes,"tier1_work_counters":format!("{:?}",work.tier1_work_counters),
                            "retained_workspace_bytes":workspace.retained_heap_bytes(),"execution_ns":work.execute_ns,
                            "tier1_phase_workers":format!("{:?}",work.tier1_phase_workers),
                            "executed_phase_worker_plan":format!("{:?}",work.executed_phase_worker_plan)}));
                    }
                    Err(e) => {
                        result.diagnostics.insert(
                            "execution_diagnostics_unsupported".into(),
                            serde_json::json!(format!("{e:?}")),
                        );
                    }
                }
            }
            Err(e) => {
                result.diagnostics.insert(
                    "prepared_diagnostics_unsupported".into(),
                    serde_json::json!(format!("{e:?}")),
                );
            }
        }
    }
    let mct = if coding == "classic" && c.image.components == 3 {
        if c.output.lossless {
            "reversible_colour_transform"
        } else {
            "irreversible_colour_transform"
        }
    } else {
        "none"
    };
    record_encode_profile(&mut result, coding, levels, mct);
    Ok(result)
}
fn main() {
    main_worker(run);
}
