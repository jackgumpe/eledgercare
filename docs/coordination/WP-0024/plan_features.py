"""Bind an approved training, calibration or blind feature extraction phase to exact inputs and code."""
from argparse import ArgumentParser
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
from corpus_plan import P, read, read_prior, schedule
from plan_h0 import QPY, NATIVE, HOST, git
from device_lease import guard


def publish(repo,candidate,split,phase,label,gate,gate_digest,prior=None):
    if not label.startswith(split+"-"+phase+"-r") or not label.rsplit("-r",1)[-1].isdigit():
        raise ValueError("Unexpected lease label")
    if git(repo,"rev-parse","HEAD")!=candidate or git(repo,"status","--porcelain","--untracked-files=all"):
        raise ValueError("Candidate must be clean and frozen")
    if guard.sha(gate)!=gate_digest or not gate.resolve().is_relative_to(HERE):
        raise ValueError("Unbound coordinator gate receipt")
    boundary=read(gate)
    if not boundary["h0_accepted_by_reviewer"] or not boundary["h0_independent_evidence"]:
        raise ValueError("H0 requires reviewed real token and span evidence")
    if split=="blind" and not (boundary.get("fit_sha256") and boundary.get("cal_thresholds_frozen")):
        raise ValueError("Blind corpus requires frozen weights and dev-calibrated thresholds")
    if phase=="features" and not boundary.get("c1_accepted_by_reviewer"):
        raise ValueError("Feature reuse awaits independent uncached C1 validation")
    public=HOST/"custody/v2/public"/split
    inputs=repo/"docs/fixtures/WP-0024/v2"/split
    for file in ("receipt.json","manifest.json","cross-pair.json","pairs.json"):
        if guard.sha(inputs/file)!=guard.sha(public/file):
            raise ValueError("Corpus differs from immutable input "+file)
    c1,cached=None,None
    if prior is not None:
        c1,cached=read_prior(prior)
        if (c1["split"]!=split or c1["sensor_tree"]!=git(repo,"rev-parse",candidate+":docs/research/WP-0024/sensor") or
            c1["manifest_sha256"]!=guard.sha(public/"manifest.json") or c1["model_revision"]!=boundary["model_revision"]):
            raise ValueError("C1 feature source not bound to this split and sensor")
    if phase=="features" and split in ("train","blind") and prior is None:
        raise ValueError("The split's own uncached witnesses are required")
    plan=schedule(public,phase,cached)
    receipt=read(public/"receipt.json")
    docs={b["binder"]:b for b in read(public/"manifest.json")["binders"]}
    requests=[]
    for b in sorted({row["binder"] for row in plan["calls"]}):
        pdf=public/"pdf"/(b+".pdf")
        pages=[p for w in docs[b]["windows"] for p in w["pages"]]
        if guard.sha(pdf)!=receipt["source_pdfs"][b]:
            raise ValueError("Source document digest mismatch")
        requests.append({"pdf":str(pdf),"sha256":receipt["source_pdfs"][b],"pages":len(pages),"rgb_sha256":[p["rgb_sha256"] for p in pages]})
    for call in plan["calls"]:
        for page in call["pages"]:
            if guard.sha(Path(page["image"]))!=page["sha256"]:
                raise ValueError("Committed encoded raster changed")
    output=HOST/"review/runs"/label
    if output.exists():
        raise FileExistsError(output)
    plan.update(packet="WP-0024",lease=label,split=split,candidate=candidate,output=str(output),raster_root=str(public/"rasters"),
                requests=requests, model_revision=boundary["model_revision"],module_sha256=NATIVE,
                sensor_tree=git(repo,"rev-parse",candidate+":docs/research/WP-0024/sensor"),
                prior_c1_sha256=guard.sha(prior) if prior else None,gate_sha256=gate_digest)
    path=HERE/(label+"-plan.json")
    guard.dump(path,plan)
    common=["docs/coordination/WP-0016/device_lease.py","qualification/baseline/winjob.py",
            "docs/research/WP-0015/astra/native.py","docs/research/WP-0015/astra/formats.py",
            "docs/research/WP-0015/astra/sensitivity-title-level/rescore.py","docs/research/WP-0023/trial/stock.py",
            "docs/research/WP-0014/eld-latency-author/probe.py",P+"/device_lease.py",P+"/supervise.py",P+"/plan_features.py",P+"/corpus_plan.py"]
    rels=git(repo,"ls-files","docs/research/WP-0024/sensor","docs/fixtures/WP-0024/v2/"+split).splitlines()
    source={r:guard.sha(repo/r) for r in sorted(set(rels+common))}
    coordination={r:guard.sha(ROOT/r) for r in common}
    if any(source[r]!=s for r,s in coordination.items()):
        raise ValueError("Coordinator and candidate pins disagree")
    digest=guard.sha(path)
    release={"packet":"WP-0024","name":label,"operator":"eld-rd-reviewer","review_worktree_head":candidate,"worktree":str(repo),
             "gpu_uuid":guard.GPU,"ceiling_mib":12500,"free_floor_mib":12000,"prepared_utc":guard.utc(),
             "source_files":source,"coordination_files":coordination,"gate_sha256":gate_digest,
             "orders":[{"run":label,"plan":str(path),"plan_sha256":digest,"output":str(output),
                        "seconds":600+150*len(plan["calls"]),
                        "argv":[str(QPY),"-I","-B",str(repo/P/"supervise.py"),str(path),digest]}]}
    out=HERE/(label+"-release.json")
    guard.dump(out,release)
    print(label,guard.sha(out),len(plan["calls"]),"true singleton calls")


if __name__=="__main__":
    ap=ArgumentParser(description=__doc__)
    ap.add_argument("repo",type=Path)
    ap.add_argument("candidate")
    ap.add_argument("split",choices=("train","cal","blind"))
    ap.add_argument("phase",choices=("c1","features"))
    ap.add_argument("label")
    ap.add_argument("gate",type=Path)
    ap.add_argument("gate_sha256")
    ap.add_argument("--prior-c1",type=Path)
    a=ap.parse_args()
    publish(a.repo.resolve(),a.candidate,a.split,a.phase,a.label,a.gate.resolve(),a.gate_sha256,a.prior_c1)
