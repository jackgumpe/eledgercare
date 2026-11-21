"""Compare W0 with every committed public blind raster without inspecting printed values."""
from io import BytesIO
from pathlib import Path
import sys
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_common import blob,cpu,pinned,read,save,sha


def check(plan_file,pin):
    p = pinned(plan_file,pin)
    base = Path(p["raster_root"]).parent.resolve()
    assert p["phase"] == "c1" and p["split"] == "blind" and base.name == "blind" and base.parent.name == "public"
    prefix = "docs/fixtures/WP-0026/blind/"
    for name in ("manifest.json","receipt.json"):
        assert (base/name).read_bytes() == blob(p["candidate"],prefix+name)
    m = pinned(base/"manifest.json",p["manifest_sha256"])
    receipt = read(base/"receipt.json")
    w0 = p["warmup"]
    assert w0["request"]["sha256"] not in receipt["source_pdfs"].values()
    hits = set()
    counts = 0
    for b in m["binders"]:
        pdf = base/"pdf"/(b["binder"]+".pdf")
        assert pdf.parent == base/"pdf" and sha(pdf.read_bytes()) == receipt["source_pdfs"][b["binder"]]
        for window in b["windows"]:
            for page in window["pages"]:
                counts += 1
                pair = (page["sha256"],page["rgb_sha256"])
                image = Path(page["image"]).resolve()
                assert image == (base/"rasters"/(pair[0]+".png")).resolve()
                if pair in hits:
                    continue
                raw = image.read_bytes()
                assert sha(raw) == pair[0]
                with Image.open(BytesIO(raw)) as im:
                    rgb = im.convert("RGB")
                    assert rgb.size == (2550,3300) and sha(rgb.tobytes()) == pair[1]
                hits.add(pair)
    assert counts == 1344 and len(m["binders"]) == len(receipt["source_pdfs"]) == 64
    for page in w0["pages"]:
        assert page["sha256"] not in {k for k,_ in hits} and page["rgb_sha256"] not in {k for _,k in hits}
    return {"candidate":p["candidate"],"plan_sha256":pin,"warmup_receipt":w0["fixture_sha256"],
            "blind_public_manifest":p["manifest_sha256"],"pdf_files_hashed":len(m["binders"]),
            "raster_appearances":counts,"unique_png_rgb_pairs_hashed":len(hits),
            "w0_pdf_intersection":0,"w0_png_intersection":0,"w0_decoded_rgb_intersection":0}


if __name__ == "__main__":
    cpu()
    save(Path(sys.argv[3]),check(Path(sys.argv[1]),sys.argv[2]))
