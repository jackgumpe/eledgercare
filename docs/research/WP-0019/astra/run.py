"""Paired same-bitmap Windows OCR measurement. Takes a raster-only manifest and a fresh output path."""
import argparse
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from time import perf_counter_ns

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
HISTORICAL = REPO / "docs/research/WP-0015/astra"
sys.path[:0] = [str(HERE), str(HISTORICAL)]
from formats import publish
from policy import attach_read, prediction, regions
from visual import layout, rule_tables


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_manifest(manifest):
    require(set(manifest) - {"renderer"} == {"family", "pages", "source_sha256"}, "raster-only manifest expected")
    require(isinstance(manifest["family"], str) and manifest["pages"], "missing family/pages")
    for n, page in enumerate(manifest["pages"], 1):
        fields = {"page", "bmp", "width", "height", "points", "rgb_sha256", "bgra_sha256"}
        require(set(page) - {"bmp_sha256"} == fields and page["page"] == n, "raster-only ordered page metadata expected")
        require(Path(page["bmp"]).is_absolute(), "absolute admitted bitmap path expected")
        require(len(page["points"]) == 2 and all(v > 0 for v in page["points"]), "invalid PDF geometry")


def source_image(page):
    image = Image.open(page["bmp"])
    try:
        require(image.format == "BMP" and image.mode == "RGB", "lossless opaque RGB BMP expected")
        require(image.size == (page["width"], page["height"]), "admitted dimension mismatch")
        require(sha(image.tobytes()) == page["rgb_sha256"], "admitted RGB mismatch")
        require(bgra_digest(image) == page["bgra_sha256"], "admitted BGRA mismatch")
        return image
    except BaseException:
        image.close()
        raise


def bgra_digest(image):
    with image.convert("RGBA") as rgba:
        return sha(rgba.tobytes("raw", "BGRA"))


def validate_read(raw, size, digest):
    require((raw["width"], raw["height"]) == size, "recognizer input dimensions changed")
    require(raw["pixel_format"].lower() == "bgra8" and raw["bgra_sha256"] == digest,
            "recognizer input format or bytes differ")
    require(isinstance(raw["text"], str) and isinstance(raw["lines"], list), "invalid raw result")
    for line in raw["lines"]:
        require(isinstance(line["text"], str) and isinstance(line["words"], list), "invalid raw line")
        for w in line["words"]:
            box = w["bbox"]
            require(isinstance(w["text"], str) and len(box) == 4 and all(math.isfinite(v) for v in box)
                    and 0 <= box[0] < box[2] <= size[0] and 0 <= box[1] < box[3] <= size[1],
                    "invalid raw word geometry")


def full_identity(raw):
    # Everything intrinsic to the OCR result. Exclude observed timings, PID and request metadata.
    keys = ("text", "lines", "width", "height", "bgra_sha256", "pixel_format", "angle")
    return sha(canonical({k: raw.get(k) for k in keys}))


def page_result(worker, arm, meta, source, folder, expected_identity):
    n, points = meta["page"], meta["points"]
    with source_image(meta) as image:
        full = worker.full(meta["bmp"])
        validate_read(full, image.size, meta["bgra_sha256"])
        identity = full_identity(full)
        require(expected_identity is None or identity == expected_identity,
                f"paired full call differs on page {n}")
        grids = rule_tables(image, points)
        base = layout(full, grids, points)
        rows = []
        if arm == "B":
            rows = regions(full, grids, points, n, base)
            for r in rows:
                r.update(crop=None, projected_words=[], crop_value=None, decision="not_selected",
                         disagreement=None, flagged=False, emitted_value=r["full_value"])
                if not r["selected"]:
                    continue
                rect = r["rect_px"]
                with image.crop(rect) as clip:
                    expected = bgra_digest(clip)
                    size = clip.size
                crop = worker.crop(rect)
                validate_read(crop, size, expected)
                proofs = [crop[k] for k in ("source_rectangle_sha256", "source_rect_sha256") if k in crop]
                require(proofs and all(v == expected for v in proofs)
                        and crop["full_bgra_sha256"] == meta["bgra_sha256"], "invalid worker crop proof")
                r.update(expected_bgra_sha256=expected, observed_source_sha256=proofs[0])
                attach_read(r, full, crop)
            base = prediction(full, grids, points, rows)
    value = dict(page=n, source_sha256=source, state="complete", **base)
    evidence = dict(page=n, source_sha256=source, bitmap=meta, full=full, full_identity=identity,
                    grids=grids, regions=rows, arm=arm)
    record_sha = publish(folder / f"page-{n:03d}.json", evidence)
    return value, identity, sum(r["selected"] for r in rows), record_sha


def run_arm(worker, arm, manifest, out, expected):
    start = perf_counter_ns()
    folder = out / arm
    folder.mkdir()
    pages, hashes, crops, records = [], [], [], []
    for i, meta in enumerate(manifest["pages"]):
        page, identity, count, record = page_result(worker, arm, meta, manifest["source_sha256"],
                                                    folder, expected[i] if expected is not None else None)
        pages.append(page)
        hashes.append(identity)
        crops.append(count)
        records.append(record)
    prediction_sha = publish(folder / "prediction.json",
                             dict(source_sha256=manifest["source_sha256"], pages=pages))
    ns = perf_counter_ns() - start
    return dict(arm=arm, elapsed_ns=ns, pages_per_minute=60e9*len(pages)/ns, crops=sum(crops),
                crops_per_page=sum(crops)/len(pages), per_page_crops=crops, full_identities=hashes,
                prediction_sha256=prediction_sha, page_evidence_sha256=records,
                startup_inside_timed_arm_ns=0)


def measure(manifest, order, out, worker_type, metadata):
    validate_manifest(manifest)
    out.mkdir(parents=True, exist_ok=False)
    start = perf_counter_ns()
    receipt = dict(metadata, family=manifest["family"], source_sha256=manifest["source_sha256"],
                   order=order, pages=len(manifest["pages"]), arms={},
                   began_utc=datetime.now(UTC).isoformat())
    try:
        with worker_type() as worker:
            receipt["startup_ns"] = perf_counter_ns()-start
            info = worker.info
            receipt["engine"] = info
            require(info["language"].lower() == "en-us", "expected en-US WinRT")
            maximum = info.get("max_dimension", info.get("max_image_dimension"))
            require(isinstance(maximum, int) and all(max(p["width"], p["height"]) <= maximum
                    for p in manifest["pages"]), "recognizer maximum dimension")
            first = manifest["pages"][0]
            start = perf_counter_ns()
            warmup = worker.full(first["bmp"])
            validate_read(warmup, (first["width"], first["height"]), first["bgra_sha256"])
            receipt["warmup"] = dict(page=first["page"], elapsed_ns=perf_counter_ns()-start,
                                     full_identity=full_identity(warmup), excluded=True)
            expected = None
            for arm in order:
                result = run_arm(worker, arm, manifest, out, expected)
                receipt["arms"][arm] = result
                expected = result["full_identities"]
                require(expected[0] == receipt["warmup"]["full_identity"], "warmup/full read changed")
            a, b = receipt["arms"]["A"], receipt["arms"]["B"]
            receipt["added_ms_per_page"] = (b["elapsed_ns"]-a["elapsed_ns"])/1e6/len(manifest["pages"])
        receipt["finished_utc"] = datetime.now(UTC).isoformat()
        publish(out / "receipt.json", receipt)
    except BaseException as exc:
        receipt.update(error=repr(exc), failed_utc=datetime.now(UTC).isoformat())
        publish(out / "failure.json", receipt)
        raise
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--order", choices=["AB", "BA"], required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    engine_dir = args.engine_dir.resolve(strict=True)
    engine = engine_dir / "engine.py"
    spec = importlib.util.spec_from_file_location("wp0019_carbon_engine", engine)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(engine_dir))
    spec.loader.exec_module(module)
    sources = [HERE / "run.py", HERE / "policy.py", HISTORICAL / "visual.py", HISTORICAL / "formats.py",
               *sorted(p for p in engine_dir.iterdir() if p.suffix.lower() in {".py", ".ps1", ".cs"})]
    hashes = {str(p): sha(p.read_bytes()) for p in sources}
    require(hashes[str(HISTORICAL / "visual.py")] ==
            "93480f58e05760d02b1c4d8a78c488e2eb616fda1b8f2dc70751fb519ea26287" and
            hashes[str(HISTORICAL / "formats.py")] ==
            "b832a7ee452f807a01a4acaa4d63fed927241f73b75fc1a47c7ae830ce28c0a6",
            "historical layout/writer source mismatch")
    result = measure(manifest, args.order, args.out.resolve(), module.Worker,
                     dict(manifest=str(args.manifest.resolve()), manifest_sha256=sha(manifest_bytes),
                          sources_sha256=hashes, argv=sys.argv, python=sys.version, executable=sys.executable))
    print(json.dumps(dict(family=result["family"], order=args.order, added_ms_per_page=result["added_ms_per_page"],
                          result=str(args.out / "receipt.json"))))


if __name__ == "__main__":
    main()
