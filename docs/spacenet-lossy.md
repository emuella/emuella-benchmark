# SpaceNet PS-RGB16 single lossy baseline

This opt-in numerical observation consumes the separate testdata
`common/spacenet-psrgb16` version 1 prepared manifest. It does not change the
codec, select a policy, search rates, or establish viewer or analytical suitability.
Khartoum remains reserved: neither its quality nor performance is measured.

`scripts/spacenet-lossy.py freeze` selects the first frozen development chip in
each of the other three AOIs. It reads only original TIFFs and freezes top-left,
centre and bottom-right 256-square views, scales 1 and 4, full-storage stretch
and exact nearest-rank 2/98 percentile stretches. Percentiles use each original
band's GDAL mask AND nodata validity. The SHA-256 sidecar prevents accidental
view changes during execution. No decoded values determine validity or stretch.

```sh
python3 scripts/spacenet-lossy.py freeze --store "$SPACENET_STORE" \
  --prepared "$SPACENET_STORE/prepared-candidate/prepared.json" \
  --output "$SPACENET_STORE/evidence/source-views.json"
python3 scripts/spacenet-lossy.py run --store "$SPACENET_STORE" \
  --prepared "$SPACENET_STORE/prepared-candidate/prepared.json" \
  --views "$SPACENET_STORE/evidence/source-views.json" \
  --build "$SPACENET_STORE/evidence/lossy-build.json" \
  --tool "$VIEWER_TOOLS" --gdal-library "$GDAL_LIBRARY" \
  --polyorama "$POLYORAMA_ROOT" \
  --asset RGB-PanSharpen_AOI_2_Vegas_img1454 \
  --output-name lossy-vegas-candidate
```

The same command applies once to each of the three declared development chips,
with a fresh output child. The build record binds the executable and GDAL hashes,
exact merged codec and Polyorama revisions, Cargo lock and build log. Build the
existing `emuella-viewer-tools` package from exact merged Git exports using
`cargo build --offline --release -p emuella-viewer-tools`; substitute only its two
codec dependency paths to the exact merged codec export. Retain the resulting
lock, dependency manifest and commands. This is a source dependency selection,
without an algorithm or profile change.

The existing indexed tool encodes the complete 1300-square chip at tile 512,
D6, irreversible 9/7, no MCT, three RGB bands, and **12 total spatial bpp**
(4 bits per component sample). This is one point, with at most three encodes.
The existing bounded `reference-export` operation reconstructs each frozen view.
The source/display error and stretch functions come from Polyorama's existing
real-scene quality tools; the storage check comes from its acceptance-quality
tool. Tool source hashes are retained. No RarePlanes wrappers or identities are
relabelled.

Per-band source-valid ANY cells gate both scales at U8-display RMSE <=3 and
p99 absolute error <=12. ALL, PARTIAL and historical all-pixel populations,
source-unit errors, actual bytes and failures remain explicit. Scale-four samples
use the same arithmetic box mean before the fixed stretch for both inputs.
Black source padding is valid when the supplier supplies neither a mask nor
nodata; this recipe does not invent a validity boundary.

The unchanged payload ceiling sums each actual tile's floored spatial-bpp target
plus 128 bytes, then adds the emitted main header and two-byte EOC. Descriptor
and manifest ceilings remain 1 MiB per tile and 1 MiB respectively. Validity
sidecars are separately prepared exact corpus derivatives; these quality-only
indexed outputs do not claim full representation eligibility. Payload failures
or quality failures do not invalidate authentic corpus inputs.

The execution guard is 1800 seconds and 4 GiB address space per preparation,
one Rayon worker, with process-group termination on timeout. These are finite
execution ceilings, not a newly qualified memory target. Whole preparation wall
time and peak RSS include source IO, hashing and setup and are separate from
classic codec-operation measurements. The inherited indexed tool's own finite
limits remain unchanged. There is no full-source runtime probe, resource tuning,
browser, recovery, independent indexed-decoder or human acceptance claim.
