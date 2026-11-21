"""Rebuild the fixed W0 and compare each standalone raster to its full-PDF page."""
from contextlib import closing
import hashlib
import io
import json
import math
from pathlib import Path
import runpy
import sys

from PIL import Image, __version__ as pillow_version
import pypdfium2 as pdfium
from pypdfium2 import version


HERE = Path(__file__).resolve().parent
CORPUS = HERE.parent / "WP-0024" / "corpus.py"
LINES = ("Rain taps softly.", "A breeze stirs.", "Clouds drift past.")
FONTS = ("Helvetica", "Helvetica-Bold")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(out):
    # Only the public vector writer and single-page rasterizer are used.
    corpus = runpy.run_path(str(CORPUS))
    streams = [f"BT /F1 22 Tf 72 684 Td ({line}) Tj ET\n".encode("ascii") for line in LINES]
    pdf_bytes = corpus["pdf"](streams, FONTS)
    pdf_name = "w0.pdf"
    corpus["keep"](out / pdf_name, pdf_bytes)
    pages = []
    verification = []
    with pdfium.PdfDocument((out / pdf_name).read_bytes()) as full:
        assert len(full) == 3
        for i, stream in enumerate(streams, 1):
            record = corpus["page_receipt"](stream, FONTS, out, {})
            png = Path(record["image"])
            with Image.open(png) as image:
                assert image.mode == "RGB" and image.size == (2550, 3300)
                pixels = image.tobytes()
            with closing(full[i - 1]) as page:
                assert page.get_size() == (612.0, 792.0)
                with closing(page.get_textpage()) as textpage:
                    assert textpage.get_text_bounded() == LINES[i - 1]
                with closing(page.render(scale=math.nextafter(300 / 72, 0))) as bitmap:
                    with bitmap.to_pil().convert("RGB") as rendered:
                        assert rendered.size == (2550, 3300)
                        rgb = rendered.tobytes()
                        assert pixels == rgb
                        encoded = io.BytesIO()
                        rendered.save(encoded, format="PNG", dpi=(300, 300), compress_level=3)
            assert encoded.getvalue() == png.read_bytes()
            assert sha(rgb) == record["rgb_sha256"]
            assert sha(encoded.getvalue()) == record["sha256"]
            pages.append(dict(page=i, image=png.name, sha256=record["sha256"],
                              rgb_sha256=record["rgb_sha256"], width=2550, height=3300))
            verification.append(dict(page=i, visible_text=LINES[i - 1],
                                     full_pdf_rgb_sha256=sha(rgb),
                                     full_pdf_png_sha256=sha(encoded.getvalue())))
    assert len({page["rgb_sha256"] for page in pages}) == 3
    receipt = dict(
        fixture="WP-0026-W0", purpose="excluded stock warm-up",
        dpi=300, page_points=[612, 792], pixel_format="RGB8 row-major",
        pdf=dict(path=pdf_name, sha256=sha(pdf_bytes)), pages=pages,
        source_verification=dict(
            method="Render each single-page source, reopen the complete PDF, compare RGB and PNG bytes.",
            corpus_sha256=sha(CORPUS.read_bytes()), pdfium=str(version.PDFIUM_INFO),
            pypdfium2=str(version.PYPDFIUM_INFO), pillow=pillow_version, pages=verification))
    corpus["keep"](out / "receipt.json", (json.dumps(receipt, indent=2) + "\n").encode("ascii"))


if __name__ == "__main__":
    if not sys.flags.isolated or not sys.dont_write_bytecode or not __debug__ or len(sys.argv) != 2:
        raise SystemExit("Usage: python -I -B make_w0.py OUTPUT_DIRECTORY (assertions enabled)")
    build(Path(sys.argv[1]).resolve())
