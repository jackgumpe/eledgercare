"""Read only the public revised development manifests/PDFs; infer stratum and status from print."""
from collections import Counter, defaultdict
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

import pypdfium2 as pdfium
from PIL import Image


PIN = "7ae03a8fc60719f162552a4ccf218227fcb0f92a"
CUSTODY = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024/custody/v2/public")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(split, basename):
    path = f"docs/fixtures/WP-0024/v2/{split}/{basename}.json"
    raw = subprocess.check_output(["git","show",f"{PIN}:{path}"])
    assert raw == (CUSTODY/split/(basename+".json")).read_bytes()
    return json.loads(raw)


def split_check(split):
    plan, routing, receipt = (pinned(split,s) for s in ("manifest","pairs","receipt"))
    per_doc = {}
    raster_seen = set()
    owners = set()
    for binder in plan["binders"]:
        ident = binder["binder"]
        pdf_data = (CUSTODY/split/"pdf"/(ident+".pdf")).read_bytes()
        assert sha(pdf_data) == receipt["source_pdfs"][ident]
        entries = [p for w in binder["windows"] for p in w["pages"]]
        signatures, paper = [], []
        with pdfium.PdfDocument(pdf_data) as doc:
            assert len(doc) == len(entries) and len(doc) in (12,30)
            for i, source in enumerate(entries):
                path = Path(source["image"]).resolve()
                assert path.parent == (CUSTODY/split/"rasters").resolve()
                if path not in raster_seen:
                    assert sha(path.read_bytes()) == source["sha256"]
                    with Image.open(path) as image:
                        assert sha(image.convert("RGB").tobytes()) == source["rgb_sha256"]
                    raster_seen.add(path)
                with closing(doc[i]) as page:
                    with closing(page.render(scale=math.nextafter(300/72,0))) as bmp:
                        with bmp.to_pil().convert("RGB") as image:
                            assert image.size == (2550,3300)
                            assert sha(image.tobytes()) == source["rgb_sha256"]
                    with closing(page.get_textpage()) as text:
                        literal = text.get_text_bounded()
                        paper.append(literal)
                        if i == 0:
                            cards = re.findall(r"Directory card: (\w+) / (\w+)", literal)
                            assert len(cards) == 2
                            ys = []
                            for owner,unit in cards:
                                with closing(text.search(f"Directory card: {owner} / {unit}",match_case=True)) as search:
                                    start,count = search.get_next()
                                    left,bottom,right,top = text.get_charbox(start)
                                    ys.append(792 - (top+bottom)/2)
                            assert ys[1] - ys[0] > 20
                signatures.append(source["rgb_sha256"])
        p1 = paper[0]
        printed = re.findall(r"^Owners: (\w+) / (\w+)$",p1.replace("\r",""),re.M)
        assert len(printed) == 1 and set(printed[0]) == set(x for x,_ in cards)
        owner = re.search(r"Ledger: (\w+)",p1).group(1)
        assert owner in printed[0]
        owners.update(printed[0])
        syntax = re.findall(r"Schema: (Item / (?:Amount / Ref|Ref / Amount))",p1)
        assert len(set(syntax)) == 2
        final = paper[-2]
        target = re.search(r"(MAINT-SUMMARY|Posting)\s+(\d+)\s+(\d+)",final)
        assert target
        kind = ("T3" if target[1] == "MAINT-SUMMARY" else "T2" if "Unit amendment:" in paper[3]
                else "T4" if "Supporting schedule" in paper[2] and "Schedule closed" not in "\n".join(paper)
                else "T1")
        subtotal = None
        if kind == "T3":
            amount = int(re.search(r"Schedule subtotal: (\d+)", "\n".join(paper)).group(1))
            subtotal = int(target[2]) == amount
            assert target[2] == target[3]
        per_doc[ident] = dict(pages=signatures, h=len(paper), stratum=kind, status=subtotal, owner=owner,
                              directory=tuple(printed[0]), top=cards[0][0], y_gap=ys[1]-ys[0],
                              choices=(tuple(sorted(printed[0])),tuple(sorted(syntax))))
    pairs = Counter()
    match = defaultdict(list)
    suffix = defaultdict(Counter)
    for pair in routing["pairs"]:
        a,b = (per_doc[m["binder"]] for m in pair["members"])
        assert a["h"] == b["h"] and a["stratum"] == b["stratum"] and a["owner"] != b["owner"]
        assert a["choices"] == b["choices"] and a["directory"] == b["directory"] and a["top"] == b["top"]
        diff = [i+1 for i,(x,y) in enumerate(zip(a["pages"],b["pages"])) if x!=y]
        assert diff == ([1,4] if a["stratum"]=="T2" else [1,3] if a["stratum"]=="T4" else [1])
        signature = tuple(sorted(tuple(t["pages"][:6]+t["pages"][-6:]) for t in (a,b)))
        match[signature].append(a["h"])
        pairs[a["stratum"],a["h"]] += 1
        if a["stratum"] == "T3":
            assert a["status"] == b["status"]
            suffix[a["h"],tuple(a["pages"][-3:]),a["choices"]][a["status"]] += 1
    assert len(match)==5 and all(sorted(h)==[12,30] for h in match.values())
    assert all(c==Counter({True:1,False:1}) for c in suffix.values()) and len(suffix) == 2
    return ({"pairs":len(routing["pairs"]),"binders":len(per_doc),"pages_rerendered":sum(t["h"] for t in per_doc.values()),
             "distinct_png_verified":len(raster_seen),"matches_recoverable_without_key":len(match),
             "counts":{f"{t}_{h}":n for (t,h),n in sorted(pairs.items())},
             "status_by_identical_suffix_and_choice_set":[{"horizon":h,"final_rgb":rgb,"status_counts":{"balanced":c[True],"unbalanced":c[False]}} for (h,rgb,_),c in sorted(suffix.items())],
             "physical_candidate_minimum_separation_pt":min(v["y_gap"] for v in per_doc.values())},
            set(receipt["source_pdfs"].values()), {sig for v in per_doc.values() for sig in v["pages"]}, owners)


if __name__ == "__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    train,cal = (split_check(split) for split in ("train","cal"))
    overlaps = {field:len(a & b) for field,a,b in zip(("source_pdf","page_rgb","owner_vocabulary"),train[1:],cal[1:])}
    assert not any(overlaps.values())
    print(json.dumps({"custody_revision": PIN, "train":train[0], "cal":cal[0], "train_cal_overlaps":overlaps},indent=2))

