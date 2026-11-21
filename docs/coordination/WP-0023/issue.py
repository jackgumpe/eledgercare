"""Bind one clean integration checkout and two preselected development windows to a finite lease."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from device_lease import guard

MODEL_SOURCE = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/models/Unlimited_OCR_2_04809669/modeling_unlimitedocr.py")
QPY = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe")
P = "docs/coordination/WP-0023"
FIXTURE_HASH = "06abb2ab4cd7bf8d74286741d4ce5da08f6e60fd237050394e2b891ae909058f"
BASE = "9eedf0f8b684746ff163d614851120c2d7ee88a5"


def revision(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def issue(cwd, candidate, name):
    if not re.fullmatch(r"dev-r[1-9][0-9]*", name):
        raise ValueError("Expected a fresh development lease name")
    if revision(cwd, "rev-parse", "HEAD") != candidate or revision(cwd, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Clean candidate required")
    subprocess.run(["git", "-C", str(cwd), "merge-base", "--is-ancestor", BASE, candidate], check=True)
    roots = ["docs/research/WP-0023/engine", "docs/research/WP-0023/trial", P + "/fixtures"]
    rels = sorted({p.relative_to(cwd).as_posix() for root in roots for p in (cwd / root).rglob("*") if p.is_file()})
    coord = [P + "/" + file for file in ("device_lease.py", "run_plan.py", "issue.py", "release-receipt.json")]
    shared = ["docs/coordination/WP-0016/device_lease.py", "qualification/baseline/winjob.py",
              "docs/research/WP-0014/eld-latency-author/probe.py"]
    source = {r: guard.sha(cwd / r) for r in rels + coord + shared}
    pinned = {r: guard.sha(ROOT / r) for r in coord + shared}
    if any(d != source[r] for r, d in pinned.items()):
        raise ValueError("Guard does not match the candidate")
    if source[P + "/fixtures/manifest.json"] != FIXTURE_HASH:
        raise ValueError("Fixture manifest is not the reservation input")
    receipt = json.loads((HERE / "release-receipt.json").read_bytes())
    if guard.sha(MODEL_SOURCE) != receipt["modelSourceSha256"]:
        raise ValueError("Native modeling source pin changed")
    fixture_dir = cwd / P / "fixtures"
    manifest = json.loads((fixture_dir / "manifest.json").read_bytes())
    pdf = fixture_dir / manifest["source"]
    if guard.sha(pdf) != manifest["sha256"]:
        raise ValueError("Development PDF bytes changed")
    owner = guard.ownership()
    if owner["device"]["free_mib"] < 12000 or shutil.disk_usage(guard.PACKET.parent).free < 4 * 1024**3:
        raise RuntimeError("Insufficient free device memory or scratch disk")
    destination = guard.PACKET / "review/runs" / name
    if destination.exists():
        raise FileExistsError(destination)
    bound = [{"window": k, "pdf": str(pdf), "sha256": manifest["sha256"], "pages": 3,
              "page_numbers": [p["page"] for p in rows], "rgb_sha256": [p["rgb_sha256"] for p in rows]}
             for k, rows in manifest["windows"].items()]
    plan = {"packet": "WP-0023", "lease": name, "candidate": candidate, "worktree": str(cwd), "output": str(destination),
            "manifest_sha256": FIXTURE_HASH, "requests": bound, "operator": "eld-batch-reviewer",
            "gates": ["native / wrapper B=1 per window", "each slot against its singleton in both B=2 orders",
                      "on discrepancy trace first divergence and a float32 prefix; timing held",
                      "on complete parity only, excluded warm-ups then AB/BA resident comparison"],
            "page_limit": "6 distinct development pages. Scale decision only."}
    plan_path = HERE / (name + "-plan.json")
    guard.dump(plan_path, plan)
    psha = guard.sha(plan_path)
    lease = {"name": name, "packet": "WP-0023", "issued_utc": guard.utc(), "operator": "eld-batch-reviewer",
             "review_worktree_head": candidate, "worktree": str(cwd), "gpu_uuid": guard.GPU,
             "ceiling_mib": 16000, "free_floor_mib": 12000, "admission_observed": owner,
             "source_files": source, "coordination_files": pinned, "native_module_sha256": receipt["modelSourceSha256"],
             "orders": [{"run": name, "plan": str(plan_path), "plan_sha256": psha, "output": str(destination),
                         "seconds": 2400, "argv": [str(QPY), "-I", "-B", str(cwd / P / "run_plan.py"), str(plan_path), psha]}]}
    release_path = HERE / (name + "-release.json")
    guard.dump(release_path, lease)
    print(json.dumps({"release": str(release_path), "sha256": guard.sha(release_path), "candidate": candidate,
                      "observed_free_mib": owner["device"]["free_mib"], "plan_sha256": psha}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worktree", type=Path)
    parser.add_argument("candidate")
    parser.add_argument("name")
    args = parser.parse_args()
    issue(args.worktree.resolve(), args.candidate, args.name)
