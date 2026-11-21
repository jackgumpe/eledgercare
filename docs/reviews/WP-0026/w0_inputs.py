"""Rerender the custodian's complete W0 PDF and compare all public development hash sets."""
from contextlib import closing
import io
import json
import math
from pathlib import Path
import sys

import pypdfium2 as pdfium
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import BASE, blob, cpu, save, sha

FIXTURE = "9ed0b70e53eb47ae2f6d47b35196f846408a0c2c"
RECEIPT = "7c509b3514daf75854b2b719cc7a94d44175c5af9fdcbae8ef4df0c68ec812e7"
PREFIX = "docs/fixtures/WP-0026/w0/"

def audit():
    raw = blob(FIXTURE,PREFIX+"receipt.json")
    assert sha(raw) == RECEIPT
    receipt = json.loads(raw)
    pdf = blob(FIXTURE,PREFIX+"w0.pdf")
    assert sha(pdf) == receipt["pdf"]["sha256"]
    labels = ["Rain taps softly.","A breeze stirs.","Clouds drift past."]
    pages = []
    with pdfium.PdfDocument(pdf) as document:
        assert len(document) == 3 == len(receipt["pages"])
        for i, expected in enumerate(receipt["pages"]):
            png = blob(FIXTURE,PREFIX+expected["image"])
            assert i+1 == expected["page"] and sha(png) == expected["sha256"]
            with closing(document[i]) as page, Image.open(io.BytesIO(png)) as original:
                assert page.get_size() == (612,792)
                assert original.mode == "RGB" and original.size == (2550,3300)
                with closing(page.get_textpage()) as textpage:
                    literal = textpage.get_text_bounded()
                    assert literal == labels[i]
                with closing(page.render(scale=math.nextafter(300/72,0.0))) as bitmap:
                    with bitmap.to_pil().convert("RGB") as rendered:
                        assert rendered.size == original.size and rendered.tobytes() == original.tobytes()
                        assert sha(rendered.tobytes()) == expected["rgb_sha256"]
                        encoded = io.BytesIO()
                        rendered.save(encoded,format="PNG",dpi=(300,300),compress_level=3)
                        assert encoded.getvalue() == png
            pages.append({"page":i+1,"physical_literal":literal,"png_sha256":sha(png),"rgb_sha256":expected["rgb_sha256"]})
    splits = {}
    for split in ("h0","train","cal","v2/train","v2/cal"):
        prefix = "docs/fixtures/WP-0024/"+split+"/"
        manifest, history = [json.loads(blob(BASE,prefix+n+".json")) for n in ("manifest","receipt")]
        pdf_hashes = set(history["source_pdfs"].values())
        assert sha(pdf) not in pdf_hashes
        refs = [p for b in manifest["binders"] for w in b["windows"] for p in w["pages"]]
        for key, field in (("png_sha256","sha256"),("rgb_sha256","rgb_sha256")):
            assert {p[key] for p in pages}.isdisjoint(p[field] for p in refs)
        splits[split] = {"pdf_hashes":len(pdf_hashes),"page_appearances":len(refs),
                         "distinct_rgb":len({p["rgb_sha256"] for p in refs}),"overlap":0}
    return {"fixture_revision":FIXTURE,"receipt_sha256":RECEIPT,"pdf_sha256":sha(pdf),"pages":pages,
            "signed_public_development_splits_checked":splits,"blind_key_opened":False}

if __name__ == "__main__":
    cpu()
    save(Path(sys.argv[1]),audit())
