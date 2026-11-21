"""Run the released WP-0022 capture once. Replay of archived data needs no OCR process."""
import argparse
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from time import perf_counter_ns, process_time_ns
from datetime import datetime, timezone

import numpy
import PIL
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRATCH = ROOT.parent / "wp0022-data" / "author"
EVIDENCE = HERE / "evidence"
PUBLIC = "docs/fixtures/WP-0022/public"
READER = "613a5ff92e9dd6783b8950529fbda76f6c21e9d3"
DETECTOR = "a0e738bc03e515999659dda09c5ee76d08fb37df"
POINTS = (612, 792)
PIXELS = (2550, 3300)
SHELL = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"


def git(*arguments):
    return subprocess.check_output(["git", *arguments], cwd=ROOT)


def blob(commit, path):
    return git("show", f"{commit}:{path}")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def exclusive(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def store(path, data):
    """Allow resumption only where the existing contents match exactly."""
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Immutable output differs: {path}")
    else:
        exclusive(path, data)


def read(path):
    return json.loads(path.read_bytes())


def now():
    return datetime.now(timezone.utc).isoformat()


def start():
    return now(), perf_counter_ns(), process_time_ns()


def elapsed(mark):
    wall, cpu = perf_counter_ns(), process_time_ns()
    return {"started_utc": mark[0], "finished_utc": now(),
            "wall_ms": (wall - mark[1]) / 1e6, "process_cpu_ms": (cpu - mark[2]) / 1e6}


def source(commit, path):
    data = blob(commit, path)
    if (ROOT / path).read_bytes() != data:
        raise ValueError(f"Working source differs from frozen Git bytes: {path}")
    return {"commit": commit, "path": path, "sha256": sha(data)}


def check_pins(args):
    for name in ("candidate", "custody", "scorer", "release"):
        revision = getattr(args, name)
        if not re.fullmatch("[0-9a-f]{40}", revision) or git("rev-parse", f"{revision}^{{commit}}").decode().strip() != revision:
            raise ValueError(f"Invalid full revision: {name}")
    pins = [source(READER, "docs/research/WP-0021/read_scope.py")]
    for name in ("visual.py", "formats.py"):
        pins.append(source(DETECTOR, "docs/research/WP-0015/astra/" + name))
    for name in ("paired.py", "capture.ps1"):
        pins.append(source(args.candidate, "docs/research/WP-0022/" + name))
    return pins


def validate_public(args):
    manifest = blob(args.custody, f"{PUBLIC}/manifest.json")
    if sha(manifest) != args.manifest_sha256:
        raise ValueError("Manifest digest differs from release")
    items = json.loads(manifest)["documents"]
    ids = set()
    digests = set()
    decoded_hashes = {}
    rendered = {}
    images = {}
    timing = {}
    for item in items:
        doc = item["id"]
        if not re.fullmatch("[a-zA-Z0-9_-]+", doc) or doc in ids:
            raise ValueError("Invalid public document ID")
        ids.add(doc)
        rendered[doc] = json.loads(blob(args.custody, f"{PUBLIC}/rendered/{doc}.json"))
        pages = item["pages"]
        if not pages or [p["page"] for p in pages] != list(range(1, len(pages) + 1)):
            raise ValueError("Invalid page order")
        rp = rendered[doc]["pages"]
        if [p["page"] for p in rp] != [p["page"] for p in pages]:
            raise ValueError("Renderer pages differ")
        for entry, page in zip(pages, rp, strict=True):
            if (page["width_pt"], page["height_pt"]) != POINTS:
                raise ValueError("Renderer size differs")
            digest = entry["sha256"]
            if not re.fullmatch(r"rasters/[a-zA-Z0-9._/-]+\.png", entry["raster"]) or ".." in entry["raster"].split("/"):
                raise ValueError("Unsafe public raster path")
            data = blob(args.custody, f"{PUBLIC}/{entry['raster']}")
            if sha(data) != digest:
                raise ValueError("Raster digest differs from manifest")
            if digest in digests:
                continue
            mark = start()
            with Image.open(io.BytesIO(data)) as im:
                if im.format != "PNG" or im.size != PIXELS or im.mode != "RGB":
                    raise ValueError("Expected a full-resolution RGB PNG")
                dpi = list(im.info.get("dpi", ()))
                if len(dpi) != 2 or any(abs(n - 300) > .1 for n in dpi):
                    raise ValueError(f"PNG density differs from 300 DPI: {dpi}")
                rgb = sha(im.tobytes())
                bgra = sha(im.convert("RGBA").tobytes("raw", "BGRA"))
            # Identical decoded images with a different container would be a release mismatch.
            if rgb in decoded_hashes:
                raise ValueError(f"Two different PNGs encode the same page pixels: {digest}")
            decoded_hashes[rgb] = digest
            digests.add(digest)
            path = SCRATCH / "inputs" / f"{digest}.png"
            store(path, data)
            images[digest] = {"rgb_sha256": rgb, "canonical_bgra_sha256": bgra,
                              "mode": "RGB", "size": list(PIXELS), "dpi": dpi,
                              "rgb_packed_row_bytes": PIXELS[0] * 3, "png_bytes": len(data)}
            timing[digest] = elapsed(mark)
    if len(digests) != args.rasters:
        raise ValueError("Unique input count differs from release")
    return items, rendered, images, timing


def capture(digest, meta, prep_time, detector):
    path = SCRATCH / "inputs" / f"{digest}.png"
    folder = EVIDENCE / "captures" / digest
    folder.mkdir(exist_ok=True, parents=True)
    if not (folder / "input.json").exists():
        exclusive(folder / "input.json", encoded({"sha256": digest, **meta, "prepare": prep_time}))
    grid = folder / "grid.json"
    if not grid.exists():
        exclusive(folder / "grid-started.json", encoded({"utc": now(), "sha256": digest}))
        with Image.open(path) as im:
            im.load()
            mark = start()
            grids = detector(im, POINTS)
            duration = elapsed(mark)
        exclusive(grid, encoded({"png_sha256": digest, "grids": grids, "detect": duration}))
    grid_data = read(grid)
    if grid_data["png_sha256"] != digest:
        raise ValueError("Wrong cached grid")
    raw_path = folder / "raw.json"
    if not raw_path.exists():
        if (folder / "ocr-started.json").exists():
            raise RuntimeError(f"Recognition was journaled without complete raw output; never retry {digest}")
        mark = start()
        subprocess.run([str(SHELL), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                        "-File", str(HERE / "capture.ps1"), "-Raster", str(path), "-RasterSha256", digest,
                        "-BgraSha256", meta["canonical_bgra_sha256"], "-ReceiptDirectory", str(folder)], check=True)
        exclusive(folder / "child-lifetime.json", encoded(elapsed(mark)))
    raw = read(raw_path)
    finish = read(folder / "ocr-finished.json")
    if (sha(raw_path.read_bytes()) != finish["raw_sha256"] or raw["png_sha256"] != digest
            or raw["language"] != "en-US" or raw["image"]["canonical_bgra_sha256"] != meta["canonical_bgra_sha256"]):
        raise ValueError("Captured bytes/image identity differs from native receipt")
    return grid_data, raw


def projected(page, raw):
    width, height = raw["image"]["width"], raw["image"]["height"]
    lines = []
    for li, line in enumerate(raw["lines"], 1):
        words = []
        for wi, word in enumerate(line["words"], 1):
            x, y, w, h = word["rect_px"]
            bbox = [x * POINTS[0] / width, y * POINTS[1] / height,
                    (x + w) * POINTS[0] / width, (y + h) * POINTS[1] / height]
            words.append({"text": word["text"], "bbox": bbox, "ref": f"p{page}:L{li}:W{wi}"})
        lines.append({"text": line["text"], "words": words})
    return {"page": page, "width_pt": POINTS[0], "height_pt": POINTS[1], "lines": lines}


def observe(document, arm, rendered, captures):
    pages, cost = [], []
    for entry, renderer_page in zip(document["pages"], rendered["pages"], strict=True):
        digest = entry["sha256"]
        grid, raw = captures[digest]
        mark = start()
        p = entry["page"]
        if arm == "R":
            # Whitelist visible reader inputs; preserve words, refs, order and optional native line text.
            page = {key: renderer_page[key] for key in ("page", "width_pt", "height_pt")}
            page["lines"] = []
            for line in renderer_page["lines"]:
                words = [{k: word[k] for k in ("text", "bbox", "ref")} for word in line["words"]]
                page["lines"].append({"words": words, **({"text": line["text"]} if "text" in line else {})})
        else:
            page = projected(p, raw)
        page["grids"] = grid["grids"]
        pages.append(page)
        cost.append({"page": p, "sha256": digest, "observation": elapsed(mark)})
    return {"pages": pages}, cost


def timed_read(reader, obs, cost):
    # The original read() sees one continuous ordered document. The yielding clock spans
    # just the time spent inside read() on each page, including cross-page state changes.
    def timed_pages():
        for page, receipt in zip(obs["pages"], cost, strict=True):
            mark = start()
            yield page
            receipt["reader"] = elapsed(mark)
    return reader({"pages": timed_pages()}, "grid-words")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidate", "custody", "scorer", "release", "manifest-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--rasters", type=int, required=True)
    args = parser.parse_args()
    pins = check_pins(args)
    documents, rendered, images, prep_times = validate_public(args)
    plan = {"packet": "WP-0022", **vars(args), "sources": pins, "inputs": images,
            "python": sys.version, "python_executable": sys.executable, "numpy": numpy.__version__, "pillow": PIL.__version__}
    store(EVIDENCE / "plan.json", encoded(plan))
    sys.path.insert(0, str(ROOT / "docs/research/WP-0015/astra"))
    detector = importlib.import_module("visual").rule_tables
    sys.path.insert(0, str(ROOT / "docs/research/WP-0021"))
    reader = importlib.import_module("read_scope").read
    captures = {digest: capture(digest, meta, prep_times[digest], detector) for digest, meta in images.items()}
    for doc in documents:
        doc_id = doc["id"]
        for arm in ("R", "W"):
            obs, cost = observe(doc, arm, rendered[doc_id], captures)
            store(EVIDENCE / "observations" / arm / (doc_id + ".json"), encoded(obs))
            outputs = timed_read(reader, obs, cost)
            store(EVIDENCE / "predictions" / arm / (doc_id + ".json"), encoded(outputs))
            timing = EVIDENCE / "timing" / arm / (doc_id + ".json")
            if not timing.exists():
                exclusive(timing, encoded(cost))
    index = {p.relative_to(EVIDENCE).as_posix(): sha(p.read_bytes())
             for p in sorted(EVIDENCE.rglob("*.json")) if p.name != "blind-hashes.json"}
    store(EVIDENCE / "blind-hashes.json", encoded(index))
    print(f"Frozen {len(index)} files for {len(documents)} documents and {len(captures)} unique rasters.")


if __name__ == "__main__":
    main()
