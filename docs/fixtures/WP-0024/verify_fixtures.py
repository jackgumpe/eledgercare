"""Independent source PDF rerasterization, opaque key checks and dev-only span witness."""
import argparse
from collections import Counter
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path

from PIL import Image
import pypdfium2 as pdfium


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def check(expr, message):
    if not expr:
        raise ValueError(message)


def ink(page, literal, y_range):
    text = page.get_textpage()
    try:
        search = text.search(literal,match_case=True)
        try:
            while (match := search.get_next()) is not None:
                first, count = match
                chars = [text.get_charbox(i) for i in range(first,first+count)]
                box = [min(c[0] for c in chars),792-max(c[3] for c in chars),
                       max(c[2] for c in chars),792-min(c[1] for c in chars)]
                if y_range[0] <= box[1] < y_range[1]:
                    return [round(v,2) for v in box]
        finally:
            search.close()
    finally:
        text.close()
    raise ValueError(f"missing expected source literal in vertical band: {literal}")


def verify(root,split,witness_path=None):
    public=root/"public"/split
    receipt=read(public/"receipt.json")
    keys=read(root/"private"/split/"truth.json")
    for filename,k in (("manifest","manifest"),("pairs","pairs"),("cross-pair","cross_pair")):
        check(sha((public/f"{filename}.json").read_bytes())==receipt[k+"_sha256"],filename)
    check(sha((root/"private"/split/"truth.json").read_bytes())==receipt["truth_sha256"],"truth commitment")
    plan=read(public/"manifest.json")
    routes=read(public/"pairs.json")["pairs"]
    docs={b["binder"]:b for b in plan["binders"]}
    lookup={b["binder"]:b for b in keys["binders"]}
    cases={p["pair"]:p for p in keys["pairs"]}
    check(set(docs)==set(lookup)=={b["binder"] for r in routes for b in r["members"]},"binder universe")
    check(set(cases)=={p["pair"] for p in routes},"pair universe")
    png_seen=set()
    renders={}
    witnesses=[]
    for binder,doc in docs.items():
        pdf=(public/"pdf"/(binder+".pdf")).read_bytes()
        check(sha(pdf)==receipt["source_pdfs"][binder],"PDF commitment")
        with pdfium.PdfDocument(pdf) as source:
            pages=[p for w in doc["windows"] for p in w["pages"]]
            check(len(source)==len(pages)==cases[lookup[binder]["pair"]]["horizon"],"source length")
            for i,entry in enumerate(pages):
                path=Path(entry["image"])
                if entry["sha256"] not in png_seen:
                    check(sha(path.read_bytes())==entry["sha256"],"encoded hash")
                    with Image.open(path) as im:
                        check(im.size==(2550,3300) and im.mode=="RGB","PNG dimensions or channels")
                        check(sha(im.tobytes())==entry["rgb_sha256"],"decoded hash")
                    png_seen.add(entry["sha256"])
                # Re-render all H0 appearances, and each logical PDF's first page + each new image otherwise.
                actual_render = split=="h0" or i==0 or entry["sha256"] not in renders
                with closing(source[i]) as page:
                    check(page.get_size()==(612.,792.),"source point size")
                    if actual_render:
                        bitmap=page.render(scale=math.nextafter(300/72,0))
                        try:
                            with bitmap.to_pil().convert("RGB") as im:
                                check(sha(im.tobytes())==entry["rgb_sha256"],"full source PDF raster match")
                        finally:
                            bitmap.close()
                        renders[entry["sha256"]]=True
                    if witness_path and i in (0,10):
                        check(split=="h0","only H0 witness may be public")
                        w1=lookup[binder]["window1"]
                        items=([("owner",[f"Ledger: {w1['owner']}"],(260,300)),
                                ("unit",[f"Unit: {w1['unit']}"],(295,340)),
                                ("schema",w1["schema"],(350,392)),
                                ("ordinary row",["Service","180","103"],(392,426))] if i==0 else
                               [("unheaded target",["Posting","240","850"],(155,200))])
                        for kind,cells,band in items:
                            witnesses.append(dict(binder=binder,page=i+1,window=i//3+1,
                                window_page=i%3+1,kind=kind,
                                cells=[dict(literal=t,source_ink_bbox_pt=ink(page,t,band)) for t in cells]))
    for route in routes:
        a,b=[docs[m["binder"]] for m in route["members"]]
        pairsig=lambda doc:[tuple(p["rgb_sha256"] for p in w["pages"]) for w in doc["windows"]]
        wa,wb=pairsig(a),pairsig(b)
        diffs={i+1 for i,(x,y) in enumerate(zip(wa,wb)) if x!=y}
        check(diffs==({1,2} if cases[route["pair"]]["stratum"]=="T2" else {1}),"window sharing")
    for match in {p["match"] for p in cases.values()}:
        counterparts=[p for p in cases.values() if p["match"]==match]
        if split!="h0":
            check(sorted(p["horizon"] for p in counterparts)==[12,30],"matched horizons")
            for short in [k for k in lookup.values() if k["pair"]==next(c["pair"] for c in counterparts if c["horizon"]==12)]:
                long=next(k for k in lookup.values() if cases[k["pair"]]["horizon"]==30 and cases[k["pair"]]["match"]==match
                          and k["window1"]["owner"]==short["window1"]["owner"])
                sw=docs[short["binder"]]["windows"]
                lw=docs[long["binder"]]["windows"]
                check([w["pages"] for w in sw]==[w["pages"] for w in lw[:2]+lw[-2:]],"matched horizon retained pages")
    if split=="blind":
        check(Counter((v["stratum"],v["horizon"]) for v in cases.values())=={(s,h):4 for s in ("T1","T2","T3","T4") for h in (12,30)},"blind crossing")
        check(Counter((v["horizon"],v["balanced"]) for v in cases.values() if v["stratum"]=="T3")=={(h,b):2 for h in (12,30) for b in (True,False)},"balanced crossing")
        for s in ("T1","T2","T3","T4"):
            for h in (12,30):
                check({p["variation"] for p in cases.values() if p["stratum"]==s and p["horizon"]==h}=={0,1,2,3},"2x2 variants")
    if witness_path:
        out={"split":"h0","description":"Visible vector-PDF source glyph ink. Coordinates in pt left/top to right/bottom. Multiply X by 999/612 and Y by 999/792 for native [0..999] space. Native BLOCK aggregate boxes can enclose multiple cells. Align actual emitted token spans separately; these source literals do not manufacture missing observations.","pdf_page_pt":[612,792],"raster_size":[2550,3300],"channels":"RGB8","decoded_bytes_per_page":25245000,"documents":receipt["source_pdfs"],"witnesses":witnesses}
        witness_path.write_bytes((json.dumps(out,indent=2)+"\n").encode())
    print(json.dumps(dict(split=split,pairs=len(cases),binders=len(docs),distinct_pngs=len(png_seen),full_pdf_rendered_distinct=len(renders))))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("split",choices=("h0","train","cal","blind"))
    p.add_argument("root",type=Path)
    p.add_argument("--h0-witness",type=Path)
    a=p.parse_args()
    verify(a.root,a.split,a.h0_witness)
