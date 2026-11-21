"""Recover the two selected C1 pairs from signed public RGBs; render every bound page from its binder PDF."""
from collections import Counter,defaultdict
from contextlib import closing
import io
import math
from pathlib import Path
import sys

from PIL import Image
import pypdfium2 as pdfium

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_common import blob,cpu,pinned,read,save,sha
from routes import key

def verify(path,pin):
    p = pinned(path,pin)
    split = p["split"]
    assert p["packet"] == "WP-0026" and p["phase"] == "c1" and split in ("train","blind")
    public = Path(p["raster_root"]).parent
    prefix = "docs/fixtures/WP-0026/blind/" if split == "blind" else "docs/fixtures/WP-0024/v2/train/"
    for f,field in (("manifest","manifest_sha256"),("pairs","pairs_sha256"),("cross-pair","cross_pair_sha256"),
                    ("receipt",None)):
        file = public/(f+".json")
        raw = file.read_bytes()
        assert raw == blob(p["candidate"],prefix+file.name)
        if field:
            assert sha(raw) == p[field]
    manifest,pairs,receipt = [read(public/(f+".json")) for f in ("manifest","pairs","receipt")]
    binders = {b["binder"]:b["windows"] for b in manifest["binders"]}
    group_members = defaultdict(list)
    selected = {}
    for pair in sorted(pairs["pairs"],key=lambda q:q["pair"]):
        left,right = pair["members"]
        twins = [binders[t["binder"]] for t in (left,right)]
        ka,kb = [[key(w["pages"]) for w in windows] for windows in twins]
        assert len(ka) == len(kb) and ka[0] != kb[0] and ka[-1] == kb[-1]
        if ka[1:] == kb[1:]:
            selected.setdefault(len(ka),pair)
        for t,ws in zip((left,right),twins,strict=True):
            for w in ws:
                group_members[key(w["pages"])].append({"pair":pair["pair"],"binder":t["binder"],"window":w["window"]})
    multi = {k:sorted(v,key=lambda x:(x["binder"],x["window"])) for k,v in group_members.items() if len({a["pair"] for a in v})>1}
    assert multi == read(public/"cross-pair.json")["groups"]
    assert set(selected) == {4,10}
    actual_rows = []
    witness_keys = []
    pdf_sha = {}
    rgb_set = set()
    for horizon in (4,10):
        pair = selected[horizon]
        by_side = []
        for member in pair["members"]:
            b = member["binder"]
            pdf = public/"pdf"/(b+".pdf")
            expected_pdf = receipt["source_pdfs"][b]
            assert sha(pdf.read_bytes()) == expected_pdf
            assert next(r for r in p["requests"] if Path(r["pdf"]) == pdf)["sha256"] == expected_pdf
            pdf_sha[b] = expected_pdf
            tags = []
            with pdfium.PdfDocument(pdf) as doc:
                assert len(doc) == 3*horizon
                for i,w in enumerate(binders[b],1):
                    actual = p["calls"][len(actual_rows)]
                    assert actual["binder"] == b and actual["window"] == w["window"] == i
                    assert actual["pages"] == w["pages"] and actual["ordinal"] == len(actual_rows)+2
                    tag = f"k{len(actual_rows)+1:04d}"
                    assert tag == actual["tag"] and actual["hooked"] is True and actual["retain_hidden"] is True
                    for local,record in enumerate(w["pages"]):
                        page_number = 3*(i-1)+local
                        png = Path(record["image"]).read_bytes()
                        assert sha(png) == record["sha256"]
                        with Image.open(io.BytesIO(png)) as image, closing(doc[page_number]) as page:
                            assert image.size == (2550,3300) and page.get_size() == (612,792)
                            with closing(page.render(scale=math.nextafter(300/72,0.0))) as bitmap:
                                with bitmap.to_pil().convert("RGB") as rendered:
                                    assert rendered.tobytes() == image.convert("RGB").tobytes()
                                    assert sha(rendered.tobytes()) == record["rgb_sha256"]
                        rgb_set.add(record["rgb_sha256"])
                    actual_rows.append({"tag":tag,"binder":b,"window":i,"rgb_key":key(w["pages"])})
                    tags.append(tag)
            by_side.append(tags)
        for a,b in zip(by_side[0][1:],by_side[1][1:],strict=True):
            witness_keys.append({"mode":"duplicate","left":a,"right":b})
    assert witness_keys == p["check_groups"] and len(actual_rows) == len(p["calls"]) == 28
    return {"split":split,"candidate":p["candidate"],"plan_sha256":pin,"selected_pairs":{k:v["pair"] for k,v in selected.items()},
            "pdf_sha256":pdf_sha,"rerendered_page_appearances":3*len(actual_rows),"distinct_page_rgb":len(rgb_set),
            "cross_pair_groups_reconstructed":len(multi),"calls":actual_rows,"check_groups":witness_keys}

if __name__ == "__main__":
    cpu()
    save(Path(sys.argv[3]),verify(Path(sys.argv[1]),sys.argv[2]))
