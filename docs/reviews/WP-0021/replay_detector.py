"""Reproduce the original detector on independent raster controls and intake PNGs."""
import argparse
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path

import numpy
import PIL
from PIL import Image, ImageDraw

REV = "a0e738bc03e515999659dda09c5ee76d08fb37df"
SOURCE = "docs/research/WP-0015/astra"
BLOBS = {"visual.py": "bb6e041d3adef486ff8b784a9e738a3442211bb4",
         "formats.py": "596266b79ff98a8364f4ef8cdba34dd9a24535cc"}
PAGE = (612, 792)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_detector(folder):
    folder.mkdir()
    pins = {}
    for name, blob in BLOBS.items():
        data = subprocess.check_output(["git", "show", f"{REV}:{SOURCE}/{name}"])
        actual = subprocess.check_output(["git", "hash-object", "--stdin"], input=data).decode().strip()
        if actual != blob:
            raise ValueError(f"Wrong repository object for {name}: {actual}")
        (folder / name).write_bytes(data)
        pins[name] = {"blob": actual, "sha256": sha(data)}
    sys.path.insert(0, str(folder))
    visual = importlib.import_module("visual")
    assert Path(visual.__file__).resolve() == (folder / "visual.py").resolve()
    return visual.rule_tables, pins


def raster(directory, name, bands):
    """Write true 2x points RGB raster. The detector only receives the reopened image."""
    im = Image.new("RGB", tuple(2 * x for x in PAGE), "white")
    draw = ImageDraw.Draw(im)
    for xs, ys in bands:
        for y in ys:
            draw.line((2 * xs[0], 2 * y, 2 * xs[-1], 2 * y), fill="black")
        for x in xs:
            draw.line((2 * x, 2 * ys[0], 2 * x, 2 * ys[-1]), fill="black")
    dest = directory / (name + ".png")
    im.save(dest)
    return dest


def observation(path, points, detector):
    with Image.open(path) as im:
        return {"png_sha256": sha(path.read_bytes()), "size": list(im.size),
                "grids": detector(im, points)}


def control_checks(folder, detector):
    parent = [42, 130, 338, 430, 540]
    child = [78, 210, 362, 442, 540]
    same = [42, 205, 366, 430, 540]
    different = [42, 205, 366, 458, 540]
    top, bottom = [104, 124, 144], [158, 178, 198]
    cases = {
        "multirow_distinct_margins": ([(parent, top), (child, bottom)],
                                      [(parent, top), (child, bottom)]),
        "single_row_each": ([(parent, top[:2]), (child, bottom[:2])], []),
        "same_margins_one_shared_divider": ([(parent, top), (same, bottom)],
                                             [([42, 430, 540], top + bottom)]),
        "same_margins_no_shared_divider": ([(parent, top), (different, bottom)], []),
        "far_apart_same_margins": ([(parent, top), (different, [400, 420, 440])],
                                   [(parent, top), (different, [400, 420, 440])]),
        "blank_image": ([], []),
    }
    results = {}
    for name, (bands, expected) in cases.items():
        result = observation(raster(folder, name, bands), PAGE, detector)
        result["expected"] = [{"xs": xs, "ys": ys} for xs, ys in expected]
        if result["grids"] != result["expected"]:
            raise ValueError(f"Detector control {name}: {result}")
        results[name] = result
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scratch", type=Path)
    parser.add_argument("--input", type=Path, help="Directory of fixture page PNGs.")
    parser.add_argument("--points", nargs=2, type=float, default=PAGE)
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=False)
    detector, pins = load_detector(args.scratch / "source")
    results = {"detector_commit": REV, "sources": pins, "python": sys.version,
               "pillow": PIL.__version__, "numpy": numpy.__version__,
               "controls": control_checks(args.scratch, detector)}
    if args.input:
        paths = sorted(args.input.rglob("*.png"))
        assert paths, "No PNG files found"
        results["input_pages"] = {path.relative_to(args.input).as_posix():
                                  observation(path, args.points, detector) for path in paths}
    dest = args.scratch / "detector.json"
    dest.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"{len(results['controls'])} controls passed. {dest}")


if __name__ == "__main__":
    main()
