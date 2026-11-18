"""Verify independent development rasters and stage scoring-key-free A2 input bytes."""
import hashlib
import json
from pathlib import Path
import shutil
import pypdfium2 as pdfium
from PIL import Image

RUNTIME=Path("C:/Users/jackg/eLedgerCare-Speed/WP-0017")
SOURCE=RUNTIME/"design/public/dev/id_ablation"
DEST=RUNTIME/"review/inputs/dev-id-ablation"
PDF_SHA="56033270ff82568e393be6fdff21085eaefff82927097e054ef527d839fd9b3c"
RASTER_SHA="404712df4d98c881c008be62a7fc8e342d53e1068f0d79741356b50b18fa9598"


def digest(b):
    return hashlib.sha256(b).hexdigest()


def verify():
    pdf=SOURCE/"source.pdf"
    raster=SOURCE/"rasters.json"
    assert digest(pdf.read_bytes())==PDF_SHA and digest(raster.read_bytes())==RASTER_SHA
    refs=json.loads(raster.read_bytes())["pages"]
    d=pdfium.PdfDocument(pdf)
    try:
        assert len(d)==len(refs)==18
        for i,ref in enumerate(refs):
            page=d[i]
            bmp=page.render(scale=300/72)
            try:
                image=bmp.to_pil().convert("RGB")
                assert i+1==ref["page"] and digest(image.tobytes())==ref["rgb_sha256"]
                with Image.open(SOURCE/ref["png"]) as png:
                    assert digest(png.convert("RGB").tobytes())==ref["rgb_sha256"]
            finally:
                bmp.close()
                page.close()
    finally:
        d.close()
    assert len({r["rgb_sha256"] for r in refs})==18
    DEST.mkdir(parents=True,exist_ok=True)
    for name in ("source.pdf","rasters.json"):
        target=DEST/name
        if target.exists():
            assert target.read_bytes()==(SOURCE/name).read_bytes()
        else:
            shutil.copyfile(SOURCE/name,target)
    assert {p.name for p in DEST.iterdir()}=={"source.pdf","rasters.json"}
    print(json.dumps(dict(pdf_sha256=PDF_SHA,rasters_sha256=RASTER_SHA,pages=18,windows=6,renderer_rgb_verified=18,
                          png_rgb_verified=18,scoring_keys_released=0)))

if __name__=="__main__":
    verify()
