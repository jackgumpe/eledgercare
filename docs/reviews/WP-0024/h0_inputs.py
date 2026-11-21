"""Independently resolve each H0 manifest raster to its page in the complete binder PDF."""
import hashlib
import json
import math
import sys
from contextlib import closing
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image


ROOT = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024/custody/public/h0")
PIN = "20cb3a35c03e752e4f83a455278dbf558bb9712163057901110069f2ec23bf4e"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check():
    manifest = (ROOT / "manifest.json").read_bytes()
    assert sha(manifest) == PIN
    receipt = json.loads((ROOT / "receipt.json").read_bytes())
    assert receipt["manifest_sha256"] == PIN
    hashes = {}
    text_witness = {}
    for entry in json.loads(manifest)["binders"]:
        binder = entry["binder"]
        pdf = (ROOT / "pdf" / (binder+".pdf")).read_bytes()
        assert sha(pdf) == receipt["source_pdfs"][binder]
        text_witness[binder] = {}
        pages = []
        with pdfium.PdfDocument(pdf) as document:
            assert len(document) == 12 and [w["window"] for w in entry["windows"]] == [1, 2, 3, 4]
            for window in entry["windows"]:
                assert len(window["pages"]) == 3
                for local_page, record in enumerate(window["pages"], 1):
                    i = (window["window"]-1)*3+local_page
                    path = Path(record["image"]).resolve()
                    assert path.parent == (ROOT/"rasters").resolve()
                    assert sha(path.read_bytes()) == record["sha256"]
                    with Image.open(path) as image:
                        assert image.size == (2550, 3300)
                        assert sha(image.convert("RGB").tobytes()) == record["rgb_sha256"]
                    with closing(document[i-1]) as page:
                        assert page.get_size() == (612.0, 792.0)
                        with closing(page.render(scale=math.nextafter(300/72, 0))) as bmp:
                            with bmp.to_pil().convert("RGB") as rendered:
                                assert sha(rendered.tobytes()) == record["rgb_sha256"]
                        with closing(page.get_textpage()) as layer:
                            # These are literal printed strings from the development PDF.
                            text_witness[binder][i] = layer.get_text_bounded().splitlines()
                    pages.append(record["rgb_sha256"])
        hashes[binder] = pages
    first, second = hashes.values()
    differing = [n for n, (a,b) in enumerate(zip(first, second, strict=True), 1) if a != b]
    return {"h0_manifest_sha256": PIN, "source_pdfs": receipt["source_pdfs"],
            "complete_pdf_rerenders_matched": sum(map(len,hashes.values())),
            "pair_differing_pages": differing, "visible_literals": text_witness}


if __name__ == "__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    print(json.dumps(check(), ensure_ascii=True, indent=2))

