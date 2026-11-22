"""Materialize only the three released k0014 pages and their independent PDF glyph records."""
import argparse
from contextlib import closing
from hashlib import sha256
from io import BytesIO
import json
import math
import os
from pathlib import Path
from zipfile import ZipFile

if os.environ.get("CUDA_VISIBLE_DEVICES") != "-1":
    raise SystemExit("Set CUDA_VISIBLE_DEVICES=-1 before starting this CPU-only program")
import pypdfium2 as pdfium
from PIL import Image

ARCHIVE = "76d203b4c70047b2f75c254da23ca3c51616ffb09d9f540c0f31ffee49d94b0f"
PLAN = "12a683f1d0562206f8fe4f9ea61c163790e374ef8a23204b2d7905cb0c2ae238"
BEGIN = "3db0aea9b93e311a97da1621459787a40f636a416698dd3668fe42286e9456e0"
NATIVE = "ce9d03a8d73ecf4366b96bc2dbbf9e129f5a2ca30265876a16b17c07cc20b169"
PDF = "38191ec7191afc58b68aa21461a1b9c785818218f63a2a6a8ce37edba1177e0e"
BINDER = "1dccb35a08a84cea541c71fc"
PHYSICAL_PAGES = (16, 17, 18)


def digest(data):
    return sha256(data).hexdigest()


def verified(data, expected):
    if digest(data) != expected:
        raise ValueError(f"SHA-256 mismatch against {expected}")
    return data


def source_lines(page):
    width, height = page.get_size()
    results, line, boxes = [], [], []
    with closing(page.get_textpage()) as textpage:
        def finish_line():
            if not line:
                return
            left = min(b[0] for b in boxes)
            bottom = min(b[1] for b in boxes)
            right = max(b[2] for b in boxes)
            top = max(b[3] for b in boxes)
            top_left = [left, height - top, right, height - bottom]
            results.append({
                "text": "".join(line),
                "bbox_pt_top_left": [round(x, 5) for x in top_left],
                "bbox999": [round(v * 999 / dim) for v, dim in zip(top_left, (width, height, width, height))],
            })
            line.clear()
            boxes.clear()

        for index in range(textpage.count_chars()):
            char = textpage.get_text_range(index, 1)
            if char in ("\r", "\n"):
                finish_line()
            else:
                line.append(char)
                boxes.append(textpage.get_charbox(index))
        finish_line()
        if [r["text"] for r in results] != textpage.get_text_bounded().splitlines():
            raise ValueError("Inconsistent PDF text views")
    return results


def materialize(repo, out):
    archive_path = repo / "docs/reviews/WP-0026/blind-c1-primary/primary-001.zip"
    release_dir = repo / "docs/coordination/WP-0026"
    plan_raw = verified((release_dir / "blind-c1-r1-plan.json").read_bytes(), PLAN)
    release = json.loads((release_dir / "blind-c1-r1-release.json").read_bytes())
    if PLAN not in json.dumps(release):
        raise ValueError("Release does not identify the frozen plan")
    archive = verified(archive_path.read_bytes(), ARCHIVE)
    out.mkdir(parents=True, exist_ok=True)
    result = {"schema": "wp0027-source-v1", "tag": "k0014", "binder": BINDER, "window": 6,
              "archive_sha256": ARCHIVE, "plan_sha256": PLAN, "begin_sha256": BEGIN,
              "native_sha256": NATIVE, "source_pdf_sha256": PDF, "source_page_count": 30, "pages": []}
    with ZipFile(BytesIO(archive)) as z:
        if z.read("binding/blind-c1-r1-plan.json") != plan_raw:
            raise ValueError("Archived and released plan bytes differ")
        plan = json.loads(plan_raw)
        call, = [c for c in plan["calls"] if c["tag"] == "k0014"]
        request, = [r for r in plan["requests"] if Path(r["pdf"]).stem == BINDER]
        prefix = "runs/blind-c1-r1/sensor/k0014"
        begin = json.loads(verified(z.read(prefix + "-begin.json"), BEGIN))
        if any(begin[k] != call[k] for k in ("pages", "binder", "window", "tag", "ordinal")):
            raise ValueError("Archived process input disagrees with released call")
        if not (call["binder"] == BINDER and call["window"] == 6 and len(call["pages"]) == 3
                and begin["plan_sha256"] == PLAN and request["pages"] == 30 and request["sha256"] == PDF):
            raise ValueError("Unexpected source binding")
        raw = verified(z.read(prefix + "/native.json"), NATIVE)
        source_pdf = verified(z.read("inputs/" + PDF + ".pdf"), PDF)
        with pdfium.PdfDocument(source_pdf) as doc:
            if len(doc) != 30:
                raise ValueError("Source page count differs")
            for number, entry in zip(PHYSICAL_PAGES, call["pages"]):
                if entry["rgb_sha256"] != request["rgb_sha256"][number - 1]:
                    raise ValueError("Source page position mismatch")
                png = verified(z.read("inputs/" + entry["sha256"] + ".png"), entry["sha256"])
                with closing(doc[number - 1]) as page, Image.open(BytesIO(png)) as image:
                    if page.get_size() != (612, 792) or image.mode != "RGB" or image.size != (2550, 3300):
                        raise ValueError("Unexpected source geometry or image mode")
                    orig = verified(image.tobytes(), entry["rgb_sha256"])
                    with closing(page.render(scale=math.nextafter(300 / 72, 0))) as bitmap:
                        with bitmap.to_pil().convert("RGB") as rendered:
                            if rendered.size != image.size or rendered.tobytes() != orig:
                                raise ValueError("Source PDF and archived input pixels differ")
                    name = f"page-{number:03}.png"
                    result["pages"].append({"page_number": number, "png_file": name, "png_sha256": entry["sha256"],
                                            "rgb_sha256": entry["rgb_sha256"], "width": image.width, "height": image.height,
                                            "pdf_point_size": list(page.get_size()), "source_lines": source_lines(page)})
                    (out / name).write_bytes(png)
        (out / "native.json").write_bytes(raw)
    source = (json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    (out / "source.json").write_bytes(source)
    print(json.dumps({"source_sha256": digest(source), "pages": PHYSICAL_PAGES, "native_sha256": NATIVE}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    materialize(args.repo, args.out)
