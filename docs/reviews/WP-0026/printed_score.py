"""After custody scoring, reconstruct target meanings from the public PDFs and reproduce the frozen scorer."""
import argparse
from collections import Counter,defaultdict
from contextlib import closing
import json
from pathlib import Path
import re
import sys

import pypdfium2 as pdfium

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_common import BASE, HOST, blob, cpu, pinned, read, save, sha
from preflights import SCORER

def source_truth(pdf,public_pin):
    assert sha(pdf.read_bytes()) == public_pin
    text = []
    with pdfium.PdfDocument(pdf) as doc:
        horizon = len(doc)
        assert horizon in (12,30)
        for i in range(horizon):
            with closing(doc[i]) as page,closing(page.get_textpage()) as visible:
                text.append(visible.get_text_bounded().replace("\r",""))
    def exactly(pattern,s):
        value, = re.findall(pattern,s,flags=re.M)
        return value
    first,final = text[0],text[-2]
    active = exactly(r"^Ledger:\s*(\S+)\s*$",first)
    unit = exactly(r"^Unit:\s*(\S+)\s*$",first)
    c2,c3 = exactly(r"^Item\s+(\w+)\s+(\w+)\s*$",first)
    assert {c2,c3} == {"Amount","Ref"}
    literal,val,other = exactly(r"^(Posting|MAINT-SUMMARY)\s+(\d+)\s+(\d+)\s*$",final)
    joined = "\n".join(text[1:])
    child_opened = any("Supporting schedule" in s for s in text[1:-2])
    child_closed = any("Schedule closed" in s for s in text[1:-2])
    assert child_opened
    ambiguous = not child_closed
    amendments = re.findall(r"^Unit amendment:\s*(\S+)\s*$",joined,flags=re.M)
    assert len(amendments) <= 1
    subtotal = None
    if literal == "MAINT-SUMMARY":
        assert child_closed and val == other and not amendments
        child = exactly(r"^Schedule subtotal:\s*(\d+)\s*$",joined)
        subtotal = "BALANCED" if int(val) == int(child) else "UNBALANCED"
    stratum = "T4" if ambiguous else "T3" if subtotal else "T2" if amendments else "T1"
    return horizon,{"ambiguous":ambiguous,"stratum":stratum,"owner":None if ambiguous else active,
                    "unit":None if ambiguous else (amendments or [unit])[0],"column":None if ambiguous else c2,
                    "subtotal_status":subtotal,"literal":val,"window1":{"owner":active,"unit":unit,"schema":["Item",c2,c3]}}

def development():
    results = {}
    for split in ("train","cal"):
        public = HOST.parent/"WP-0024/custody/v2/public"/split
        receipt = read(public/"receipt.json")
        assert receipt == json.loads(blob(BASE,f"docs/fixtures/WP-0024/v2/{split}/receipt.json"))
        # Historical development labels are supervised data. This path is restricted to the two development splits.
        truth = pinned(public.parents[1]/"private"/split/"truth.json",receipt["truth_sha256"])
        counts = Counter()
        for target in truth["binders"]:
            b = target["binder"]
            horizon,derived = source_truth(public/"pdf"/(b+".pdf"),receipt["source_pdfs"][b])
            assert all(target[k] == v for k,v in derived.items()), (split,b,derived,target)
            counts[f"{derived['stratum']}/{horizon}"] += 1
        results[split] = dict(counts)
    return {"purpose":"Validate the independent printed-source interpretation on released supervised development labels",
            "matched_development_targets":40,"strata_horizons":results,"blind_material_opened":False}

def blind(args):
    actual = pinned(args.scored,args.score_sha)
    freeze = pinned(args.freeze,args.freeze_sha)
    assert actual["freeze_sha256"] == args.freeze_sha and freeze["authority"] in ("eld-coordinator","eld-rd-reviewer")
    assert freeze["split"] == "blind" and freeze["action"] == "score-wp0024-frozen-predictions"
    public = args.public
    pred = pinned(args.predictions,freeze["predictions_sha256"])
    transport = pinned(args.transport,freeze["transport_sha256"])
    published_pairs = pinned(public/"pairs.json",freeze["pairs_sha256"])["pairs"]
    manifest = pinned(public/"manifest.json",freeze["sensor_plan_sha256"])
    assert len(published_pairs) == 32 and len(manifest["binders"]) == 64
    public_receipt = read(public/"receipt.json")
    assert public_receipt["manifest_sha256"] == freeze["sensor_plan_sha256"]
    resources = pinned(args.resources,freeze["resources_sha256"])
    assert resources == actual["resources"]
    module = {}
    source = blob(SCORER,"docs/fixtures/WP-0024/score.py")
    exec(compile(source,SCORER+":score.py","exec"),module)
    arms = module["ARMS"]
    assert tuple(freeze["arms"]) == arms
    routed = {b["binder"]:b for b in manifest["binders"]}
    reported = {p["pair"]:p for p in actual["pairs"]}
    routes, observations, suffixes = {},{},{}
    cases,targets = [],[]
    families = defaultdict(list)
    for pair in published_pairs:
        pid = pair["pair"]
        observed,signature = [],[]
        members = pair["members"]
        routes[pid] = [m["binder"] for m in members]
        for m in members:
            b = m["binder"]
            pdf = public/"pdf"/(b+".pdf")
            horizon,fields = source_truth(pdf,public_receipt["source_pdfs"][b])
            targets.append(dict(binder=b,target=m["target"],pair=pid,**fields))
            tokens = [r["rgb_sha256"] for w in routed[b]["windows"] for r in w["pages"]]
            assert len(tokens) == horizon
            signature.append(tuple(tokens[:6]+tokens[-6:]))
            observed.append((fields["stratum"],horizon))
            suffixes[b] = sha(json.dumps(tokens[-3:],separators=(",",":")).encode())
        assert len(set(observed)) == 1
        stratum,horizon = observed[0]
        assert reported[pid]["stratum"] == stratum and reported[pid]["horizon"] == horizon
        # Opaque family names only identify the independently recovered matched physical signatures.
        match = reported[pid]["match"]
        families[tuple(sorted(signature))].append((match,horizon))
        cases.append(dict(pair=pid,stratum=stratum,horizon=horizon,match=match))
    assert len(families) == 16
    assert all(len({n for n,h in rows}) == 1 and sorted(h for n,h in rows) == [12,30] for rows in families.values())
    assert len({rows[0][0] for rows in families.values()}) == 16
    for doublet in transport["pairs"]:
        for t in doublet["twins"]:
            b = t["binder"]
            observations[b] = pinned(Path(t["windows"][0])/"metadata.json",freeze["window1_sha256"][b])
    predictions = module["check_predictions"](pred["predictions"] if isinstance(pred,dict) else pred,
                                               {t["binder"]:t["target"] for t in targets})
    result = module["score"]({"pairs":cases,"binders":targets},routes,predictions,observations,resources,suffixes)
    result["freeze_sha256"] = args.freeze_sha
    normalized = json.loads(json.dumps(result,allow_nan=False))
    assert normalized == actual
    return {"physical_pdfs":len(targets),"matched_families":len(families),"pairs":len(cases),"replayed_rows":384,
            "raw_blind_key_read":False,"custody_score_sha256":args.score_sha,"freeze_sha256":args.freeze_sha,
            "scorer_revision":SCORER,"source_sha256":sha(source),"full_score_structurally_identical":True,
            "decision":result["decision"]}

if __name__ == "__main__":
    cpu()
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="mode",required=True)
    d = sub.add_parser("development")
    d.add_argument("output",type=Path)
    b = sub.add_parser("released-score")
    for key in ("scored","freeze","public","predictions","transport","resources","output"):
        b.add_argument("--"+key,type=Path,required=True)
    b.add_argument("--score-sha",required=True)
    b.add_argument("--freeze-sha",required=True)
    a = cli.parse_args()
    save(a.output,development() if a.mode == "development" else blind(a))
