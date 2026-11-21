"""Build a finite B=1 extraction schedule from signed public RGB manifests without opening a key."""
from argparse import ArgumentParser
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from device_lease import guard

P="docs/coordination/WP-0024"
PHASES=("c1","features")


def read(path):
    return json.loads(path.read_bytes())


def rgb_key(pages):
    ids=[p["rgb_sha256"] for p in pages]
    if len(ids)!=3:
        raise ValueError("Expected one ordered three-page window")
    return sha256((json.dumps(ids,ensure_ascii=True,indent=2)+"\n").encode("ascii")).hexdigest()


def source_groups(public):
    receipt=read(public/"receipt.json")
    for path,name in (("manifest.json","manifest_sha256"),("pairs.json","pairs_sha256"),("cross-pair.json","cross_pair_sha256")):
        if guard.sha(public/path)!=receipt[name]:
            raise ValueError("Unbound public data "+path)
    manifest=read(public/"manifest.json")
    pairs=read(public/"pairs.json")["pairs"]
    members={t["binder"]:p["pair"] for p in pairs for t in p["members"]}
    if len(members)!=2*len(pairs) or len({p["pair"] for p in pairs})!=len(pairs):
        raise ValueError("Unexpected public pair cardinality")
    binders={b["binder"]:b["windows"] for b in manifest["binders"]}
    if set(members)!=set(binders):
        raise ValueError("Unmatched binder identity")
    groups=defaultdict(list)
    for b,windows in binders.items():
        if len(windows) not in (4,10) or [w["window"] for w in windows]!=list(range(1,len(windows)+1)):
            raise ValueError("Windows are missing or unordered")
        for w in windows:
            groups[rgb_key(w["pages"])].append({"pair":members[b],"binder":b,"window":w["window"]})
    multiple={k:sorted(v,key=lambda row:(row["binder"],row["window"])) for k,v in groups.items() if len({r["pair"] for r in v})>1}
    if multiple!=read(public/"cross-pair.json")["groups"]:
        raise ValueError("Cross-pair reuse manifest disagrees with ordered RGB digests and members")
    return receipt,pairs,binders


def c1_selection(pairs,binders):
    """Preselect a common-interruption pair at each horizon by opaque ID and RGBs alone."""
    chosen={}
    for pair in sorted(pairs,key=lambda v:v["pair"]):
        a,b=(binders[t["binder"]] for t in pair["members"])
        if len(a)!=len(b):
            raise ValueError("Twin horizons disagree")
        ka,kb=([rgb_key(w["pages"]) for w in windows] for windows in (a,b))
        if ka[0]==kb[0] or ka[-1]!=kb[-1]:
            raise ValueError("Unexpected first or final twin RGB identity")
        if len(a) not in chosen and ka[1:]==kb[1:]:
            chosen[len(a)]=pair
    if set(chosen)!={4,10}:
        raise ValueError("C1 needs one common-interruption pair per horizon")
    return [chosen[4],chosen[10]]


def schedule(public,phase,previous=None):
    receipt,pairs,binders=source_groups(public)
    chosen=c1_selection(pairs,binders) if phase=="c1" else pairs
    cached={} if previous is None else dict(previous)
    calls,checks,references=[],[],{}
    for pair in chosen:
        twins=[]
        for twin in pair["members"]:
            ordered=[]
            for window in binders[twin["binder"]]:
                k=rgb_key(window["pages"])
                tag=f"k{len(calls)+1:04d}"
                if phase=="c1" or k not in cached:
                    calls.append({"tag":tag,"binder":twin["binder"],"window":window["window"],
                                  "pages":window["pages"],"hooked":True,"retain_hidden":phase=="c1"})
                    source={"tag":tag,"rgb_key":k}
                    if phase=="features":
                        cached[k]=source
                else:
                    source=cached[k]
                ordered.append(source)
            references[twin["binder"]]=ordered
            twins.append(ordered)
        if phase=="c1":
            for left,right in zip(twins[0][1:],twins[1][1:],strict=True):
                assert left["rgb_key"]==right["rgb_key"] and left["tag"]!=right["tag"]
                checks.append({"mode":"duplicate","left":left["tag"],"right":right["tag"]})
    if phase=="c1" and (len(calls),len(checks))!=(28,12):
        raise ValueError("C1 must exercise all 28 true singleton calls and 12 independent same-window comparisons")
    delivery={"pairs":[{"twins":[{**t,"windows":references[t["binder"]]} for t in p["members"]]} for p in chosen]}
    return {"phase":phase,"manifest_sha256":receipt["manifest_sha256"],"cross_pair_sha256":receipt["cross_pair_sha256"],
            "pairs_sha256":receipt["pairs_sha256"],"calls":calls,"check_groups":checks,"delivery":delivery}


def read_prior(plan_path):
    """Use previous feature bytes only after physically rechecking their full provenance and operator result."""
    plan=read(plan_path)
    out=Path(plan["output"])
    outcome=read(out/"sensor/outcome.json")
    binding=read(out/"sensor/binding.json")
    if (plan["phase"]!="c1" or len(outcome["checks"])!=12 or outcome["real_inference_calls"]!=28 or
        not outcome["all_equal"] or not all(c["passed"] for c in outcome["checks"]) or
        binding["plan_sha256"]!=guard.sha(plan_path)):
        raise ValueError("Incomplete uncached C1")
    if not read(out/"process.json")["all_segments_completed"]:
        raise ValueError("Unreturned operator process")
    cached={}
    for call in plan["calls"]:
        tag=call["tag"]
        ref=out/"sensor"/tag
        row=outcome["rows"][tag]
        cap=row["capture"]
        if guard.sha(ref/"metadata.json")!=row["metadata_sha256"] or guard.sha(ref/"pooled.f32")!=cap["pooled_sha256"]:
            raise ValueError("Changed retained feature")
        key=rgb_key(call["pages"])
        cached[key]={"directory":str(ref),"rgb_key":key,"metadata_sha256":row["metadata_sha256"],
                     "pooled_sha256":cap["pooled_sha256"],"source_lease":plan["lease"]}
    return plan,cached


def transport(plan):
    outcome=read(Path(plan["output"])/"sensor/outcome.json")
    if not outcome["all_equal"] or len(outcome["rows"])!=len(plan["calls"]):
        raise ValueError("Live extraction incomplete")
    direct=Path(plan["output"])/"sensor"
    resolved=[]
    for pair in plan["delivery"]["pairs"]:
        twins=[]
        for twin in pair["twins"]:
            paths=[]
            for provider in twin["windows"]:
                if "directory" in provider:
                    path=Path(provider["directory"])
                    expected=(provider["metadata_sha256"],provider["pooled_sha256"])
                else:
                    path=direct/provider["tag"]
                    row=outcome["rows"][provider["tag"]]
                    expected=(row["metadata_sha256"],row["capture"]["pooled_sha256"])
                if (guard.sha(path/"metadata.json"),guard.sha(path/"pooled.f32"))!=expected:
                    raise ValueError("Feature source digest changed")
                paths.append(str(path))
            twins.append({"binder":twin["binder"],"target":twin["target"],"windows":paths})
        resolved.append({"twins":twins})
    return {"pairs":resolved}


if __name__=="__main__":
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("public",type=Path)
    args=parser.parse_args()
    for phase in PHASES:
        plan=schedule(args.public,phase)
        print(json.dumps({"phase":phase,"pairs":len(plan["delivery"]["pairs"]),"real_calls":len(plan["calls"]),
                         "comparisons":len(plan["check_groups"]),"bound_cross_pair_sha256":plan["cross_pair_sha256"]}))
