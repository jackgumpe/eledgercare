"""Independent matched PDF renders and predeclared whole-window archive search."""
from collections import Counter, defaultdict
from contextlib import closing
import io
import json
import math
from pathlib import Path
import sys
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BASE, DEV, ROOT, WORK, output, pinned, sha
import numpy as np
from PIL import ImageChops
import pypdfium2 as pdfium

BASES = {12: ("366ef9f7a5a787497b0f6634", "388abc9b198838d05730e328", "c68d80f8a27dd80a95e5aea0"),
         30: ("dd21685671af3251fb1cbcd6", "770f5bcd4ed40c3ff28a3905", "3d942ef5cf4ec8f1ce6b503f")}
ARCHIVES = ("h0-primary", "train-c1-primary", "train-features-primary", "cal-features-primary")
WORKER = "9c02c9fae465dc1d1322a81c23eb3af45bbb0aff"
SENSOR = "1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd"
MODEL = "0480966938291445591f69f08a13b041c073a96a"
W0 = "7c509b3514daf75854b2b719cc7a94d44175c5af9fdcbae8ef4df0c68ec812e7"

def page_data(page):
    assert page.get_size() == (612., 792.)
    with closing(page.render(scale=math.nextafter(300/72, 0))) as bitmap:
        image = bitmap.to_pil().convert("RGB")
    assert image.size == (2550, 3300)
    stream = io.BytesIO()
    image.save(stream, format="PNG", compress_level=3, dpi=(300, 300))
    return image, {"sha256": sha(stream.getvalue()), "rgb_sha256": sha(image.tobytes())}

def render():
    root = DEV / "public/cal"
    published = "docs/fixtures/WP-0024/v2/cal/"
    receipt = json.loads(pinned(BASE, published + "receipt.json"))
    plan = pinned(BASE, published + "manifest.json")
    assert sha(plan) == receipt["manifest_sha256"] and (root/"manifest.json").read_bytes() == plan
    truth = (DEV/"private/cal/truth.json").read_bytes()
    assert sha(truth) == receipt["truth_sha256"] == "a227da1293bcd6f8b0f636ce3349abd12d02a52361a46b47dbf34969cc773ff1"
    labels = {r["binder"]:r for r in json.loads(truth)["binders"]}
    old, new = b"(Ledger: Alder) Tj", b"(Ledger: Cedar) Tj"
    plan = {r["binder"]:r for r in json.loads(plan)["binders"]}
    result = {}
    for horizon,(binder,pair,target) in BASES.items():
        case = labels[binder]
        assert (case["owner"], case["pair"], case["target"], case["stratum"]) == ("Alder", pair, target, "T1")
        original = (root / "pdf" / (binder+".pdf")).read_bytes()
        assert sha(original) == receipt["source_pdfs"][binder] and original.count(old) == 1
        offset = original.index(old)+len(b"(Ledger: ")
        altered = original[:offset] + b"Cedar" + original[offset+5:]
        assert altered.replace(new,old,1) == original
        pages = [p for window in plan[binder]["windows"] for p in window["pages"]]
        members = {"Alder": [], "Cedar": []}
        with pdfium.PdfDocument(original) as a, pdfium.PdfDocument(altered) as c:
            assert len(a) == len(c) == horizon
            for i, source in enumerate(pages):
                with closing(a[i]) as pa, closing(c[i]) as pc:
                    img_a, ref = page_data(pa)
                    img_c, twin = page_data(pc)
                with img_a, img_c:
                    assert ref == {k:source[k] for k in ref}
                    assert sha(Path(source["image"]).read_bytes()) == ref["sha256"]
                    with ImageChops.difference(img_a, img_c) as diff:
                        bbox = diff.getbbox()
                        if i:
                            assert bbox is None and twin == ref
                        else:
                            ceiling = (575,1566,875,1705)
                            assert (bbox and ceiling[0]<=bbox[0]<bbox[2]<=ceiling[2]
                                    and ceiling[1]<=bbox[1]<bbox[3]<=ceiling[3])
                            changed = int(np.any(np.asarray(diff.crop(bbox)),axis=2).sum())
                            assert changed > 0
                            roi = {"declared_px":ceiling,"actual_bbox":bbox,"changed_rgb_pixels":changed}
                members["Alder"].append(ref)
                members["Cedar"].append(twin)
        result[str(horizon)] = {"base":binder,"pair":pair,"target":target,"literal_offset":offset,
                                "pdf":{"Alder":sha(original),"Cedar":sha(altered)},"roi":roi,"pages":members}
    return result

def archives():
    captures, inventories = defaultdict(list), {}
    for name in ARCHIVES:
        parent = "docs/reviews/WP-0026/"+name+"/"
        inv = json.loads(pinned(BASE,parent+"inventory.json"))
        raw = pinned(BASE,parent+"primary-001.zip")
        assert sha(raw) == inv["parts"]["primary-001.zip"]["sha256"]
        times,counts,loads = {},Counter(),{}
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            def member(path):
                content = z.read(path)
                assert sha(content) == inv["members"][path]["sha256"]
                return content
            release_name, = [n for n in z.namelist() if n.endswith("-release.json")]
            rel_raw = member(release_name)
            rel = json.loads(rel_raw)
            assert sha(rel_raw)==inv["release_sha256"]
            for order in rel["orders"]:
                run = order["run"]
                plan_raw = member("binding/"+Path(order["plan"]).name)
                assert sha(plan_raw) == order["plan_sha256"]
                plan = json.loads(plan_raw)
                assert plan["model_revision"] == MODEL and plan["candidate"] == WORKER
                assert plan["runner_sha256"] == sha(pinned(WORKER, "docs/research/WP-0026/worker.py"))
                prefix = f"runs/{run}/sensor/"
                w_raw = member(prefix+"warmup.json")
                warm = json.loads(w_raw)
                assert warm["fixture_sha256"] == W0 and warm["model_revision"] == MODEL and warm["success"]
                assert warm["ordinal"] == 1 and warm["mode"] == "S" and not warm["scored"] and warm["eos_observed"]
                w0_path = "docs/fixtures/WP-0026/w0/receipt.json"
                assert sha(pinned(WORKER,w0_path)) == W0
                loads[run] = {"w0_s":warm["elapsed_ns"]/1e9,"warm_sha256":sha(w_raw),"load":warm["model_load_id"],
                              "recording_tree":plan["sensor_tree"],"runner_sha256":plan["runner_sha256"]}
                for call in plan["calls"]:
                    namebase = prefix + call["tag"]
                    r_raw = member(namebase+"/receipt.json")
                    r = json.loads(r_raw)
                    assert r["verified"] and r["pages"]==call["pages"] and r["tag"]==call["tag"]
                    assert r["plan_sha256"]==sha(plan_raw) and r["warmup_sha256"]==sha(w_raw)
                    assert (r["model_revision"],r["candidate"],r["sensor_candidate"]) == (MODEL, WORKER, SENSOR)
                    assert r["model_load_id"] == warm["model_load_id"] and r["warmup_fixture_sha256"]==W0
                    assert r["mode"] == call["mode"] and r["ordinal"] == call["ordinal"]
                    counts[r["mode"]]+=1
                    if r["mode"]!="H":
                        continue
                    fhash={}
                    for f in ("metadata.json","pooled.f32","through-eos.u32le","capture.json","duration.json"):
                        b = member(namebase+"/"+f)
                        fhash[f]=sha(b)
                        assert fhash[f] == r["artifacts"][f], f
                    cap=json.loads(member(namebase+"/capture.json"))
                    assert cap["pooled_sha256"] == fhash["pooled.f32"]
                    assert fhash["through-eos.u32le"] == r["through_eos_sha256"]
                    rgb=tuple(p["rgb_sha256"] for p in r["pages"])
                    timings = json.loads(member(namebase+"/duration.json"))
                    captures[rgb].append({"run":run,"tag":r["tag"],"archive":parent+"primary-001.zip",
                        "prefix":namebase+"/","png":[p["sha256"] for p in r["pages"]],"hashes":fhash,
                        "seconds":timings["complete_window_wall_ns"]/1e9,"receipt_sha256":sha(r_raw)})
                    times[r["tag"]]=timings["complete_window_wall_ns"]/1e9
        inventories[name]={"archive_sha256":sha(raw),"counts":dict(counts),"loads":loads}
    return captures,inventories

def run():
    matched=render()
    captures,inventories=archives()
    coverage={}
    unique,missing=set(),set()
    for h,pair in matched.items():
        for owner,pages in pair["pages"].items():
            rows=[]
            for i in range(0,len(pages),3):
                window=pages[i:i+3]
                key=tuple(p["rgb_sha256"] for p in window)
                matches=captures.get(key,[])
                assert all(z["png"]==[p["sha256"] for p in window] for z in matches)
                unique.add(key)
                if not matches:
                    missing.add(key)
                rows.append({"pages":window,"matches":matches})
            coverage[h+"-"+owner]=rows
    return {"source":matched,"inventory":inventories,"coverage":coverage,"unique_inputs":len(unique),
            "missing":[list(k) for k in sorted(missing)],"eligible_source_keys":len(captures)}

if __name__=="__main__":
    output(sys.argv[1],run())
