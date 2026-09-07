//! The public encoder chooses classic RGB MCT; there is no facade toggle.
use emuella_j2k::{
    ColorModel, ComponentLayout, EncodeOptions, ImageInfo, ImageView, OutputFormat, SampleFormat,
    encode,
};

#[test]
fn classic_rgb_public_options_signal_reversible_colour_transform() {
    for precision in [8, 16] {
        for decomposition_levels in [0, 1, 2] {
            let format = if precision == 8 {
                SampleFormat::U8
            } else {
                SampleFormat::U16_LE
            };
            let info = ImageInfo::new(
                33,
                29,
                3,
                format,
                ColorModel::Rgb,
                ComponentLayout::Interleaved,
            )
            .unwrap();
            let samples: Vec<u8> = (0..33 * 29 * 3)
                .flat_map(|index| {
                    let value = (index * 977 + index * index * 3) as u16;
                    if precision == 8 {
                        vec![value as u8]
                    } else {
                        value.to_le_bytes().to_vec()
                    }
                })
                .collect();
            // These are the lossless classic options selected by the adapter.
            let stream = encode(
                ImageView::Interleaved {
                    info: &info,
                    samples: &samples,
                    stride_bytes: 33 * 3 * (precision / 8),
                },
                &EncodeOptions {
                    format: OutputFormat::J2kCodestream,
                    decomposition_levels,
                    ..Default::default()
                },
            )
            .unwrap();
            let parsed = emuella_j2k_codestream::parse(&stream).unwrap();
            let coding = parsed.uniform_effective_coding_style().unwrap();
            assert!(coding.multiple_component_transform);
            assert_eq!(coding.decomposition_levels, decomposition_levels);
        }
    }
}
