"""Publish one finite reviewer allocation for both independent control orders."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from device_lease import GPU, HERE, PACKET, REPO, dump, ownership, sha, utc

CONTROL = "61bec47689dcdf272a525185013f2dce6335fa24"
ENTRY = "docs/research/WP-0016/engine/g0.py"
PYTHON = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe")


def bind(args):
    cwd = args.worktree.resolve(strict=True)
    git = lambda *v: subprocess.check_output(["git","-C",cwd,*v],text=True).strip()
    assert git("rev-parse","HEAD") == args.source and len(args.source) == 40
    subprocess.run(["git","-C",cwd,"merge-base","--is-ancestor",CONTROL,args.source],check=True)
    assert not git("status","--porcelain")
    stable = ["docs/research/WP-0015","docs/research/WP-0014","workers/local_ocr","docs/evaluation/WP-0015"]
    assert not git("diff","--name-only",CONTROL,args.source,"--",*stable)
    assert subprocess.run(["git","-C",cwd,"ls-files","--error-unmatch",ENTRY],capture_output=True).returncode == 0
    runtime_files = [ENTRY, "docs/research/WP-0015/astra/trial.py", "docs/research/WP-0015/carbon/launch.py",
                     "docs/research/WP-0015/carbon/engine.py","docs/research/WP-0015/carbon/trial.py"]
    guards = ["docs/coordination/WP-0016/device_lease.py","qualification/baseline/winjob.py"]
    plans = json.loads((HERE / "g0-plans.json").read_bytes())["orders"]
    host = ownership()
    free_disk = shutil.disk_usage(PACKET).free
    assert host["device"]["free_mib"] >= 12000 and free_disk >= 20 * 2**30
    orders = []
    for order in ("ab","ba"):
        p = plans[order]
        assert sha(Path(p["path"])) == p["sha256"]
        name = "g0-" + order + args.suffix
        out = PACKET / "review/runs" / name
        if out.exists():
            raise FileExistsError(out)
        argv = [str(PYTHON.resolve(strict=True)),"-I","-B",ENTRY,"--source",args.source,
                "--plan",p["path"],"--sha256",p["sha256"],"--owner","review","--run",name,
                "--seconds",str(args.seconds),"--lease",name,"--min-vram-mib","12000"]
        orders.append({"run":name,"plan":p["path"],"plan_sha256":p["sha256"],"output":str(out),
                       "seconds":args.seconds,"argv":argv})
    release = {"name":"g0-anchor"+args.suffix,"gate":"G0","operator":"eld-rd-reviewer",
               "issued_utc":utc(),"worktree":str(cwd),"review_worktree_head":args.source,"inference_base":CONTROL,
               "gpu_uuid":GPU,"ceiling_mib":10000,"admission":host,"free_disk_bytes":free_disk,
               "source_files":{s:sha(cwd / s) for s in runtime_files},"coordination_files":{s:sha(REPO / s) for s in guards},
               "orders":orders,"initial_control":"Ready worker, three single-window warmups per arm; both PDFs redelivered and regenerated per order."}
    path = HERE / (release["name"] + "-release.json")
    dump(path,release)
    print(path,sha(path))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source")
    p.add_argument("worktree",type=Path)
    p.add_argument("--seconds",type=int,default=4200)
    p.add_argument("--suffix",default="")
    args = p.parse_args()
    assert 1 <= args.seconds <= 5400
    assert args.suffix in ("","-recovery")
    bind(args)
