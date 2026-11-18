"""Audit the public development scans at the same 300 DPI used by the native worker."""
import hashlib
import json
import sys
from pathlib import Path

import pypdfium2 as pdfium


def audit(family):
    data = (family / "source.pdf").read_bytes()
    truth = json.loads((family / "truth.json").read_bytes())
    source_id = hashlib.sha256(data).hexdigest()
    if source_id != truth["source_sha256"]:
        raise ValueError(f"{family.name}: PDF identity")
    doc = pdfium.PdfDocument(data)
    result = []
    try:
        if len(doc) != len(truth["pages"]):
            raise ValueError(f"{family.name}: page count")
        for ordinal, (page, expected) in enumerate(zip(doc, truth["pages"]), start=1):
            tp = page.get_textpage()
            chars = tp.count_chars()
            tp.close()
            bitmap = page.render(scale=300 / 72)
            image = bitmap.to_pil().convert("RGB")
            bitmap.close()
            extrema = image.convert("L").getextrema()
            blank = extrema[0] == extrema[1] and extrema[0] >= 245
            dims = list(page.get_size())
            page.close()
            if chars or blank != (not expected["text"].strip()) or ordinal != expected["page"]:
                raise ValueError(f"{family.name}, page {ordinal}: raster/text/order mismatch")
            result.append({"page": ordinal, "pdf_points": dims, "pixels": list(image.size),
                           "text_layer_characters": chars, "gray_extrema": list(extrema), "blank_raster": blank,
                           "rgb_sha256": hashlib.sha256(image.tobytes()).hexdigest()})
            image.close()
    finally:
        doc.close()
    return {"family": family.name, "pdf_sha256": source_id, "pages": result}


if __name__ == "__main__":
    dev = Path(sys.argv[1])
    print(json.dumps([audit(dev / family) for family in ("short", "dense", "boundary")], indent=2))
