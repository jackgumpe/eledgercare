"""Freeze both whole development binders and all 16 true singleton calls before device admission."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
from device_lease import guard

HOST=guard.PACKET
NATIVE="f6df813cef23cc28b1daca40fd8cb20740d05a238e7b9dfa2334531fdcf39f1f"
QPY=Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe")
P="docs/coordination/WP-0024"
PUBSHA="20cb3a35c03e752e4f83a455278dbf558bb9712163057901110069f2ec23bf4e"


def git(repo,*args):
    return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()


def main(repo,source,lease):
    if not lease.startswith("h0-r") or not lease[4:].isdigit():
        raise ValueError("Use a fresh H0 lease name")
    if git(repo,"rev-parse","HEAD")!=source or git(repo,"status","--porcelain","--untracked-files=all"):
        raise ValueError("Replay checkout must be clean at exact candidate")
    public=HOST/"custody/public/h0"
    if guard.sha(public/"manifest.json")!=PUBSHA or guard.sha(repo/"docs/fixtures/WP-0024/h0/manifest.json")!=PUBSHA:
        raise ValueError("H0 development input is not reserved")
    corpus=json.loads((public/"manifest.json").read_bytes())
    receipts=json.loads((public/"receipt.json").read_bytes())
    if len(corpus["binders"])!=2 or {len(b["windows"]) for b in corpus["binders"]}!={4}:
        raise ValueError("Expected the entire twelve-page H0 pair")
    calls,checks,requests=[],[],[]
    for bi,binder in enumerate(corpus["binders"]):
        pages=[p for w in binder["windows"] for p in w["pages"]]
        pdf=public/"pdf"/(binder["binder"]+".pdf")
        pdf_sha=receipts["source_pdfs"][binder["binder"]]
        if guard.sha(pdf)!=pdf_sha:
            raise ValueError("H0 PDF changed")
        requests.append({"pdf":str(pdf),"sha256":pdf_sha,"pages":len(pages),"rgb_sha256":[p["rgb_sha256"] for p in pages]})
        for window in binder["windows"]:
            if len(window["pages"])!=3 or any(guard.sha(Path(p["image"]))!=p["sha256"] for p in window["pages"]):
                raise ValueError("H0 page count or encoded bytes changed")
            stem=f"b{bi+1:02d}w{window['window']:02d}"
            for mode in ("S","H"):
                calls.append({"tag":stem+mode,"binder":binder["binder"],"window":window["window"],
                              "hooked":mode=="H","retain_hidden":mode=="H","pages":window["pages"]})
            checks.append({"left":stem+"S","right":stem+"H","mode":"hook-parity"})
    rels=git(repo,"ls-files","docs/research/WP-0024/sensor",P+"/device_lease.py",P+"/supervise.py",P+"/plan_h0.py",
             "docs/fixtures/WP-0024/h0").splitlines()
    common=["docs/coordination/WP-0016/device_lease.py","qualification/baseline/winjob.py",
            "docs/research/WP-0015/astra/native.py","docs/research/WP-0015/astra/formats.py",
            "docs/research/WP-0015/astra/sensitivity-title-level/rescore.py","docs/research/WP-0023/trial/stock.py",
            "docs/research/WP-0014/eld-latency-author/probe.py",P+"/device_lease.py",P+"/supervise.py",P+"/plan_h0.py"]
    output=HOST/"review/runs"/lease
    if output.exists():
        raise FileExistsError(output)
    plan={"packet":"WP-0024","phase":"H0","lease":lease,"candidate":source,"output":str(output),
          "raster_root":str(public/"rasters"),"manifest_sha256":PUBSHA,"module_sha256":NATIVE,
          "model_revision":"0480966938291445591f69f08a13b041c073a96a","requests":requests,"calls":calls,"check_groups":checks}
    plan_path=HERE/(lease+"-plan.json")
    guard.dump(plan_path,plan)
    digest=guard.sha(plan_path)
    release={"packet":"WP-0024","name":lease,"operator":"eld-rd-reviewer","review_worktree_head":source,"worktree":str(repo),
             "gpu_uuid":guard.GPU,"ceiling_mib":12500,"free_floor_mib":12000,"prepared_utc":guard.utc(),
             "source_files":{r:guard.sha(repo/r) for r in sorted(set(rels+common))},
             "coordination_files":{r:guard.sha(ROOT/r) for r in common},
             "admission":"The operator may launch only after observing exclusive capacity and disjoint user workloads; the guard repeats admission under the shared lock. Preparation does not acquire the device.",
             "orders":[{"run":lease,"plan":str(plan_path),"plan_sha256":digest,"output":str(output),"seconds":5400,
                        "argv":[str(QPY),"-I","-B",str(repo/P/"supervise.py"),str(plan_path),digest]}]}
    for rel,stamp in release["coordination_files"].items():
        if release["source_files"][rel]!=stamp:
            raise ValueError(f"Replay path drift: {rel}")
    path=HERE/(lease+"-release.json")
    guard.dump(path,release)
    print(json.dumps({"release":str(path),"sha256":guard.sha(path),"calls":len(calls),"groups":len(checks),"candidate":source}))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo",type=Path)
    p.add_argument("source")
    p.add_argument("lease")
    args=p.parse_args()
    main(args.repo.resolve(),args.source,args.lease)
