#!/usr/bin/env python3
"""Prepare locked project-authored corpus inputs without acquiring any data."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tomllib

FILES = (
    "gray-u8-prime-gradient-17x19.pgm",
    "gray-u8-checkerboard-127x131.pgm",
    "gray-u8-noise-257x263.pgm",
    "gray-u16-ramp-257x193.pgm",
    "rgb-u8-edges-31x29.ppm",
    "rgb-u16-extrema-65x63.ppm",
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular_file(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("asset path must be relative and contained")
    path = root
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("symlink asset paths are not supported")
    if not path.is_file():
        raise ValueError("asset is not a regular file")
    return path


def read_pnm(data):
    """Read binary P5/P6, preserving a whitespace-valued first pixel."""
    cursor = 0

    def token():
        nonlocal cursor
        while cursor < len(data):
            if data[cursor] in b" \t\r\n":
                cursor += 1
            elif data[cursor] == 35:
                end = data.find(b"\n", cursor)
                if end < 0:
                    raise ValueError("unterminated PNM comment")
                cursor = end + 1
            else:
                break
        start = cursor
        while cursor < len(data) and data[cursor] not in b" \t\r\n#":
            cursor += 1
        if cursor == start:
            raise ValueError("missing PNM token")
        return data[start:cursor]

    magic = token()
    if magic not in (b"P5", b"P6"):
        raise ValueError("only binary greyscale/RGB PNM is supported")
    width, height, maximum = (int(token()) for _ in range(3))
    if not (0 < width <= 65536 and 0 < height <= 65536):
        raise ValueError("PNM dimensions exceed preparation bounds")
    if maximum not in (255, 65535):
        raise ValueError("only full-range U8/U16 PNM is supported")
    if cursor >= len(data) or data[cursor] not in b" \t\r\n":
        raise ValueError("missing PNM raster separator")
    if data[cursor:cursor + 2] == b"\r\n":
        cursor += 2
    else:
        cursor += 1
    components = 1 if magic == b"P5" else 3
    size = width * height * components * (1 if maximum == 255 else 2)
    if size > 256 * 1024 * 1024 or len(data) - cursor != size:
        raise ValueError("PNM raster length mismatch or preparation size limit")
    raw = data[cursor:]
    if maximum == 65535:
        converted = bytearray(size)
        converted[::2], converted[1::2] = raw[1::2], raw[::2]
        raw = bytes(converted)
    return raw, dict(width=width, height=height, components=components,
                     precision=8 if maximum == 255 else 16, signed=False)


def prepare(catalogue, output):
    catalogue = Path(catalogue).resolve(strict=True)
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("output must be a new directory")
    for parent in output.parents:
        if parent.is_symlink():
            raise ValueError("output ancestors must not be symlinks")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(catalogue), *args], text=True).strip()
    if Path(git("rev-parse", "--show-toplevel")).resolve() != catalogue:
        raise ValueError("catalogue must be a repository root")
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("catalogue must be clean")
    revision = git("rev-parse", "HEAD")
    manifest_path = regular_file(catalogue, "manifests/common/generated-core.toml")
    manifest_bytes = manifest_path.read_bytes()
    manifest = tomllib.loads(manifest_bytes.decode())
    if (manifest["id"] != "common/generated-core" or manifest["review_state"] != "locked"
            or manifest["license"]["expression"] != "Apache-2.0"
            or any(manifest["rights"].get(key) != "permitted"
                   for key in ("access", "modification", "publish_benchmarks"))):
        raise ValueError("bridge requires locked Apache-2.0 generated-core rights")
    rows = manifest["assets"]
    assets = {row["path"]: row for row in rows}
    if len(assets) != len(rows):
        raise ValueError("duplicate catalogue assets")
    prepared = []
    recipe = digest(Path(__file__).read_bytes())
    for name in FILES:
        item = assets[name]
        path = regular_file(catalogue, str(Path(manifest["materialization"]["directory"]) / name))
        source = path.read_bytes()
        if len(source) != item["bytes"] or digest(source) != item["sha256"]:
            raise ValueError("catalogue integrity mismatch: " + name)
        raw, image = read_pnm(source)
        provenance = dict(catalogue_commit=revision, pack_id=manifest["id"],
                          pack_version=str(manifest["version"]), asset=name,
                          source_sha256=item["sha256"], manifest_sha256=digest(manifest_bytes),
                          recipe="generated-pnm-to-interleaved-raw-v1",
                          recipe_sha256=recipe, licence="Apache-2.0")
        prepared.append((name, raw, image, provenance))
    # Verify all selected sources before creating any output.
    output.mkdir(parents=False)
    cases = []
    for name, raw, image, provenance in prepared:
        raw_path = output / (name + ".raw")
        raw_path.write_bytes(raw)
        cases.append(dict(id=Path(name).stem,
                          input=dict(path=str(raw_path), sha256=digest(raw), provenance=provenance),
                          reference=None, image=image, operation="encode",
                          settings=dict(coding="classic", decomposition_levels=2), threads=1,
                          output=dict(colour="native",
                                      layout="interleaved", container="j2k", lossless=True,
                                      reduction=0, region=None, image=image, minimum_psnr_db=None)))
    experiment = dict(schema_version=1, name="generated-core-lossless", cases=cases)
    (output / "experiment.json").write_text(json.dumps(experiment, indent=2) + "\n")
    return output / "experiment.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogue", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(prepare(args.catalogue, args.output))
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"preparation failed: {error}\n")
