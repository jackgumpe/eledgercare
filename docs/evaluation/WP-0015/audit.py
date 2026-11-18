"""Inspect actual PDFs independently of the builder's raster buffer. CPU only."""
import argparse
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
from PIL import Image
import pypdfium2 as pdfium
import pypdfium2.raw as raw

from score import read, valid_box

SCALE = 300 / 72


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def crop_ink(image, box, inset):
    l, t, r, b = box
    rect = (math.ceil((l+inset)*SCALE), math.ceil((t+inset)*SCALE),
            math.floor((r-inset)*SCALE), math.floor((b-inset)*SCALE))
    region = image.crop(rect)
    try:
        return region.getextrema()[0] < 115
    finally:
        region.close()


def audit(folder):
    path = folder/"source.pdf"
    doc_sha = sha_bytes(path.read_bytes())
    gt = read(folder/"truth.json")
    assert doc_sha == gt["source_sha256"]
    rendered = []
    with pdfium.PdfDocument(path) as pdf:
        assert len(pdf) == len(gt["pages"]) >= 1
        for index, truth in enumerate(gt["pages"]):
            page = pdf[index]
            try:
                text_page = page.get_textpage()
                try:
                    assert text_page.count_chars() == 0
                finally:
                    text_page.close()
                objects = [obj.type for obj in page.get_objects()]
                assert objects == [raw.FPDF_PAGEOBJ_IMAGE]
                assert page.get_size() == (truth["width"], truth["height"])
                assert truth["page"] == index+1
                bitmap = page.render(scale=SCALE)
                try:
                    rgb = bitmap.to_pil().convert("RGB")
                finally:
                    bitmap.close()
                assert rgb.size == (math.ceil(truth["width"]*SCALE), math.ceil(truth["height"]*SCALE))
                pix_hash = sha_bytes(rgb.tobytes())
                gray = rgb.convert("L")
                rgb.close()
                has_ink = gray.getextrema()[0] < 115
                assert has_ink == bool(truth["text"].strip())
                for line in truth["lines"]:
                    box = line["bbox"]
                    assert valid_box(box, truth["width"], truth["height"])
                    assert crop_ink(gray, box, 0)
                    assert line["critical"] is None or line["critical"] in line["text"]
                total = empty = 0
                for table in truth["tables"]:
                    assert valid_box(table["bbox"], truth["width"], truth["height"])
                    for row in table["rows"]:
                        for cell in row:
                            box = cell["bbox"]
                            assert valid_box(box, truth["width"], truth["height"])
                            assert crop_ink(gray, box, 2) == bool(cell["text"])
                            total += 1
                            empty += cell["text"] == ""
                rendered.append(dict(page_number=index+1, width_px=gray.width, height_px=gray.height,
                                     rgb_sha256=pix_hash, embedded_images=len(objects), text_layer_chars=0,
                                     visible_ink=has_ink, printed_lines=len(truth["lines"]),
                                     table_cells=total, explicitly_empty_cells=empty))
                gray.close()
            finally:
                page.close()
    return dict(family=gt["family"], pdf_sha256=doc_sha, pdf_bytes=path.stat().st_size,
                truth_sha256=sha_bytes((folder/"truth.json").read_bytes()),
                renderer=dict(pypdfium2=version("pypdfium2"), pdfium=str(pdfium.PDFIUM_INFO),
                              pillow=Image.__version__, dpi=300, pixel_mode="RGB"),
                pages=rendered)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    payload = json.dumps(audit(args.folder), indent=2)+"\n"
    if args.out:
        args.out.write_bytes(payload.encode())
    else:
        print(payload, end="")
