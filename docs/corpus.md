# Runtime corpus inputs

The core accepts explicit raw sample paths (U8 or little-endian U16, interleaved),
SHA-256 digests and opaque provenance fields. It verifies input digests before
execution. It does not acquire data or grant rights to use a supplied asset.

`emuella-testdata` owns selection, generation, integrity and rights metadata. The
initial bridge deliberately supports only its locked, project-authored
Apache-2.0 `common/generated-core` P5/P6 greyscale and RGB subset:

```sh
python3 scripts/prepare-generated.py --catalogue /path/to/emuella-testdata \
  --output /path/to/new-scratch-inputs
```

Use Python 3.11 or newer and a clean catalogue checkout. The script verifies each
selected source against the catalogue manifest before creating the output. It
records catalogue revision, pack/version, source and manifest digests, and the
conversion script digest alongside each resulting raw input identity. U16 Netpbm
big-endian samples become little-endian raw samples. Existing output directories
are refused. The generated `experiment.json` is a lossless encode starting point;
copy and edit it for declared rates, thread budgets or adapter capabilities.

This bridge does not interpret external suite rights or copy protected packs.
Additional catalogue/suite integrations should consume their owning contracts
and reviewed permissions explicitly. Keep restricted inputs and derivatives in
their approved store. Factual measurement reports do not contain image payloads.
The tiny generated subset is useful for correctness and calibration; it is not a
representative photographic, HDR or large-image performance qualification.
