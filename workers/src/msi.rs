//! Narrow worker profile admission, not a general codestream validator.
//! Pixel correctness remains the decoder and full-reference metrics' responsibility.
use crate::Result;
use emuella_benchmark::contract::ImageSpec;

fn word(bytes: &[u8], at: usize) -> Option<u16> {
    Some(u16::from_be_bytes(bytes.get(at..at + 2)?.try_into().ok()?))
}
fn long(bytes: &[u8], at: usize) -> Option<u32> {
    Some(u32::from_be_bytes(bytes.get(at..at + 4)?.try_into().ok()?))
}

/// The added eight-band worker workload is one complete raw Part 1 tile-part.
/// Fail closed on overrides/extensions rather than infer effective coding policy.
pub fn validate_stream(bytes: &[u8], image: &ImageSpec) -> Result<()> {
    if image.components != 8 {
        return Ok(());
    }
    let rejected = || {
        "unsupported native eight-band codestream: requires unsigned16 unit-sampled full tile, classic reversible D2 LRCP one layer, no MCT or coding overrides".to_string()
    };
    if !admitted(bytes, image) {
        return Err(rejected());
    }
    Ok(())
}
fn admitted(bytes: &[u8], image: &ImageSpec) -> bool {
    if word(bytes, 0) != Some(0xff4f) {
        return false;
    }
    let (mut siz, mut cod, mut qcd) = (false, false, false);
    let mut at = 2;
    let mut tile_end: Option<usize> = None;
    loop {
        let Some(marker) = word(bytes, at) else {
            return false;
        };
        if marker == 0xff93 {
            return tile_end.is_some_and(|end| {
                end >= at + 2
                    && end.checked_add(2) == Some(bytes.len())
                    && word(bytes, end) == Some(0xffd9)
            });
        }
        let Some(len) = word(bytes, at + 2).map(usize::from).filter(|n| *n >= 2) else {
            return false;
        };
        let Some(end) = at.checked_add(2 + len).filter(|end| *end <= bytes.len()) else {
            return false;
        };
        if tile_end.is_some_and(|limit| end > limit) {
            return false;
        }
        let body = &bytes[at + 4..end];
        if tile_end.is_some() && marker != 0xff64 {
            return false;
        }
        match marker {
            0xff51 if !siz && !cod && !qcd && at == 2 => {
                if body.len() != 36 + 8 * 3
                    || word(body, 0) != Some(0)
                    || long(body, 2) != Some(image.width)
                    || long(body, 6) != Some(image.height)
                    || long(body, 10) != Some(0)
                    || long(body, 14) != Some(0)
                    || long(body, 18) != Some(image.width)
                    || long(body, 22) != Some(image.height)
                    || long(body, 26) != Some(0)
                    || long(body, 30) != Some(0)
                    || word(body, 34) != Some(8)
                    || body[36..]
                        .as_chunks::<3>()
                        .0
                        .iter()
                        .any(|c| *c != [15, 1, 1])
                {
                    return false;
                }
                siz = true;
            }
            0xff52 if siz && !cod => {
                // Scod, LRCP, one layer, MCT=0, D2, classic blocks, 5/3.
                if body.len() < 10
                    || body[0] > 1
                    || body[1] != 0
                    || word(body, 2) != Some(1)
                    || body[4] != 0
                    || body[5] != 2
                    || body[8] != 0
                    || body[9] != 1
                    || body.len() != if body[0] == 1 { 13 } else { 10 }
                {
                    return false;
                }
                cod = true;
            }
            0xff5c if siz && cod && !qcd => {
                if body.len() != 8 || body[0] & 0x1f != 0 {
                    return false;
                }
                qcd = true;
            }
            0xff64 => {} // Comments do not alter coding semantics.
            0xff90 if siz && cod && qcd => {
                if body.len() != 8 || word(body, 0) != Some(0) || body[6] != 0 || body[7] != 1 {
                    return false;
                }
                let Some(length) = long(body, 2).and_then(|n| usize::try_from(n).ok()) else {
                    return false;
                };
                tile_end = at
                    .checked_add(length)
                    .filter(|limit| *limit >= end + 2 && *limit <= bytes.len());
                if tile_end.is_none() {
                    return false;
                }
            }
            _ => return false,
        }
        at = end;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn segment(out: &mut Vec<u8>, marker: u16, body: &[u8]) {
        out.extend(marker.to_be_bytes());
        out.extend(((body.len() + 2) as u16).to_be_bytes());
        out.extend(body);
    }
    fn fixture() -> (Vec<u8>, ImageSpec) {
        let image = ImageSpec {
            width: 33,
            height: 29,
            components: 8,
            precision: 16,
            signed: false,
        };
        let mut stream = vec![0xff, 0x4f];
        let mut siz = vec![0, 0];
        for n in [33_u32, 29, 0, 0, 33, 29, 0, 0] {
            siz.extend(n.to_be_bytes());
        }
        siz.extend(8_u16.to_be_bytes());
        for _ in 0..8 {
            siz.extend([15, 1, 1]);
        }
        segment(&mut stream, 0xff51, &siz);
        segment(&mut stream, 0xff52, &[0, 0, 0, 1, 0, 2, 4, 4, 0, 1]);
        segment(&mut stream, 0xff5c, &[64, 0, 0, 0, 0, 0, 0, 0]);
        segment(&mut stream, 0xff90, &[0, 0, 0, 0, 0, 15, 0, 1]);
        stream.extend([0xff, 0x93, 0, 0xff, 0xd9]);
        (stream, image)
    }
    #[test]
    fn admits_only_complete_envelope_and_expected_profile() {
        let (stream, image) = fixture();
        assert!(validate_stream(&stream, &image).is_ok());
        for length in 0..stream.len() {
            assert!(
                validate_stream(&stream[..length], &image).is_err(),
                "length {length}"
            );
        }
        // SIZ precision/sampling/count, COD MCT/DWT/HT, QCD, SOT length/part.
        for at in [4, 5, 42, 43, 41, 74, 75, 78, 79, 84, 96, 100, 101, 102, 103] {
            let mut changed = stream.clone();
            changed[at] ^= 1;
            assert!(validate_stream(&changed, &image).is_err(), "offset {at}");
        }
        let mut changed = stream.clone();
        changed.extend([0]);
        assert!(validate_stream(&changed, &image).is_err());
        for marker in [0xff53_u16, 0xff5d, 0xff50, 0xff52] {
            let mut changed = stream.clone();
            // Insert a forbidden component/extension/coding override in tile header.
            changed.splice(
                104..104,
                [marker.to_be_bytes()[0], marker.to_be_bytes()[1], 0, 2],
            );
            changed[101] += 4;
            assert!(validate_stream(&changed, &image).is_err());
        }
    }
}
