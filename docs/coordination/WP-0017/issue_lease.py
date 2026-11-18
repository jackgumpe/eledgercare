"""Bind a prepared sequence of exact CPU/GPU commands to a clean frozen worktree and the exclusive board guard."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from device_lease import guard

HERE = Path(__file__).resolve().parent
ENGINE_BASE = "c7b2ee3663317e42a0e9bdd7ff9e17f16747d2cf"
SCORER = "1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7"
PYTHON = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe")
GUARD_FILES = [
    "qualification/baseline/winjob.py",
    "docs/coordination/WP-0016/device_lease.py",
    "docs/coordination/WP-0017/device_lease.py",
    "docs/coordination/WP-0017/run_order.py",
    "docs/coordination/WP-0017/issue_lease.py",
]


def issue(name, stage, seconds, paths):
    if not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in name):
        raise ValueError("invalid lease name")
    if stage not in ("A1", "A2", "A3") or not 1 <= seconds <= 14400:
        raise ValueError("invalid stage or wall allocation")
    orders=[]
    heads=set()
    worktrees=set()
    for path in paths:
        p=path.resolve(strict=True)
        cfg=json.loads(p.read_bytes())
        cwd=Path(cfg["worktree"]).resolve(strict=True)
        head=cfg["source"]
        def git(*a):
            return subprocess.check_output(["git","-C",cwd,*a],text=True).strip()
        if git("rev-parse","HEAD") != head or git("status","--porcelain"):
            raise ValueError("engine source or clean replay worktree differs")
        git("merge-base","--is-ancestor",ENGINE_BASE,head)
        if git("diff","--name-only",ENGINE_BASE,head,"--","docs/research/WP-0015","docs/evaluation/WP-0015","workers","src","web"):
            raise ValueError("historical inference inputs or product changed")
        if guard.sha(cwd/"docs/evaluation/WP-0015/score.py") != SCORER:
            raise ValueError("scorer changed")
        assert cfg["stage"]==stage and cfg["commands"] and cfg["requests"]
        for item in cfg["requests"]:
            assert len(item["rgb_sha256"])==item["pages"] and guard.sha(Path(item["pdf"]))==item["sha256"]
        for f,h in cfg.get("bound_files",{}).items():
            assert guard.sha(Path(f))==h
        out=Path(cfg["output"]).resolve()
        assert out.is_relative_to(guard.PACKET/"review/runs") and not out.exists()
        orders.append(dict(run=out.name,plan=str(p),plan_sha256=guard.sha(p),output=str(out),seconds=seconds,
                           argv=[str(PYTHON),"-I","-B",str(HERE/"run_order.py"),str(p),guard.sha(p)]))
        heads.add(head)
        worktrees.add(cwd)
    assert len(heads)==len(worktrees)==1 and len({o["run"] for o in orders})==len(orders)
    cwd=worktrees.pop()
    tracked=git("ls-files","docs/research/WP-0017/engine").splitlines()
    assert tracked
    # The published historical worktree was immutable; pin all new candidate code explicitly as well.
    files={f:guard.sha(cwd/f) for f in tracked if f.endswith(".py")}
    host=guard.ownership()
    if host["device"]["free_mib"]<12000 or shutil.disk_usage(guard.PACKET).free<10*1024**3:
        raise RuntimeError("resource admission unavailable")
    record=dict(name=name,gate=stage,operator="eld-rd-reviewer",issued_utc=guard.utc(),worktree=str(cwd),
                review_worktree_head=heads.pop(),inference_base=ENGINE_BASE,gpu_uuid=guard.GPU,ceiling_mib=10000 if stage=="A3" else 14500,
                admission=host,source_files=files,coordination_files={f:guard.sha(guard.REPO/f) for f in GUARD_FILES},orders=orders)
    path=HERE/(name+"-release.json")
    guard.dump(path,record)
    print(path,guard.sha(path))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("name")
    p.add_argument("stage")
    p.add_argument("seconds",type=int,help="per order")
    p.add_argument("plans",nargs="+",type=Path)
    a=p.parse_args()
    issue(a.name,a.stage,a.seconds,a.plans)
