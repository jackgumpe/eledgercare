"""Issue one reviewer GPU command for the coordinator's passive carrier (eld-rd-reviewer). Stdlib only.

Method (root, docs/coordination/WP-0017/review_command.py at d17669e, SHA-256 c5596d0e...): for each release
the coordinator publishes <name>-release.json and its digest. After independent review I commit and push one
JSON command docs/reviews/WP-0017/commands/<name>.json on review/wp-0017-escrow. A passive carrier process
owned by the coordinator ("eld-coordinator Windows process") waits for that exact pushed object, checks that
it equals the signed release and executes only that pinned lease once. No reviewer process needs to break away
from the CLI job, and no reviewer tool call needs to remain open during GPU execution.

`review` performs the independent pre-issue checks and prints them; `issue` repeats them and writes the
command file (exclusive create) only if every check passes. Committing and pushing remain explicit manual
steps by the reviewer. This tool never starts the carrier, the executor or any GPU work.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BLOBS, HERE, REPO, WP17, Check, sha, sha_file, utc, write_new  # noqa: E402

COORD_DIR = Path("C:/Users/jackg/Asp.net Projects/eledgercare/docs/coordination/WP-0017")
GPU = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"
CEILING = {"A1": 14500, "A2": 14500, "A3": 10000}
CARRIER = "eld-coordinator Windows process (docs/coordination/WP-0017/review_command.py)"


def git(cwd, *args, ok=False):
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True)
    if ok:
        return r.returncode == 0
    r.check_returncode()
    return r.stdout


def review(name, digest, stage, coord_dir, check):
    rel = coord_dir / f"{name}-release.json"
    data = rel.read_bytes()
    check(sha(data) == digest, "release bytes equal the signed digest")
    lease = json.loads(data)
    check(lease.get("name") == name and lease.get("operator") == "eld-rd-reviewer" and lease.get("gate") == stage,
          "release name/operator/stage")
    check(lease.get("gpu_uuid") == GPU and lease.get("ceiling_mib") == CEILING[stage], "GPU UUID and stage ceiling")
    executor = coord_dir / "device_lease.py"
    ex_sha = sha_file(executor)
    pinned = BLOBS["coord/device_lease.py"][2]
    check(ex_sha == pinned, f"executor equals the reviewed device_lease.py ({pinned[:12]})")
    carrier = coord_dir / "review_command.py"
    check(sha_file(carrier) == BLOBS["coord/review_command.py"][2], "carrier equals the reviewed review_command.py")
    for f, h in lease.get("coordination_files", {}).items():
        check(sha_file(coord_dir.parents[2] / f) == h, f"coordination file {f} matches the release")
    wt = Path(lease["worktree"])
    head = lease["review_worktree_head"]
    check(git(wt, "rev-parse", "HEAD").decode().strip() == head, "replay worktree HEAD = candidate")
    check(git(wt, "status", "--porcelain") == b"", "replay worktree clean")
    check(git(REPO, "cat-file", "-e", f"{head}^{{commit}}", ok=True), "candidate commit is present in the repository")
    for f, h in lease.get("source_files", {}).items():
        check(sha_file(wt / f) == h, f"source file {f} matches the release")
    orders = []
    for o in lease["orders"]:
        plan = Path(o["plan"])
        check(sha_file(plan) == o["plan_sha256"], f"{o['run']}: plan digest")
        cfg = json.loads(plan.read_bytes())
        check(cfg.get("stage") == stage and cfg.get("source") == head, f"{o['run']}: plan stage/source")
        out = Path(o["output"]).resolve()
        check(out.is_relative_to((WP17 / "review/runs").resolve()) and not out.exists(), f"{o['run']}: new output root")
        for item in cfg.get("requests", []):
            check(sha_file(Path(item["pdf"])) == item["sha256"] and len(item["rgb_sha256"]) == item["pages"],
                  f"{o['run']}: request {item.get('label')} input pin")
            check("custody" not in item["pdf"].lower() and "truth" not in item["pdf"].lower(),
                  f"{o['run']}: request {item.get('label')} is a public input")
        orders.append(dict(run=o["run"], plan_sha256=o["plan_sha256"], seconds=o["seconds"], output=str(out)))
    return dict(release=str(rel), release_sha256=digest, executor_sha256=ex_sha, candidate=head, stage=stage,
                orders=orders, worktree=str(wt))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["review", "issue"])
    ap.add_argument("--name", required=True)
    ap.add_argument("--sha256", required=True)
    ap.add_argument("--stage", required=True, choices=["A1", "A2", "A3"])
    ap.add_argument("--coord-dir", type=Path, default=COORD_DIR)
    a = ap.parse_args()
    check = Check()
    r = review(a.name, a.sha256, a.stage, a.coord_dir, check)
    print(json.dumps(dict(review=r, checks=check.count, failures=check.failures), indent=1))
    if a.action == "issue":
        if check.failures:
            raise SystemExit("not issuing: independent review failed")
        cmd = dict(release_name=a.name, release_sha256=a.sha256, executor_sha256=r["executor_sha256"],
                   candidate=r["candidate"], operator="eld-rd-reviewer", action="execute once", stage=a.stage,
                   issued_utc=utc(), carrier=CARRIER, orders=r["orders"], reviewer_checks=check.count,
                   reviewer_session="Antigravity CLI, Claude Opus 5.5 High, conversation 5ab6a228-4214-49e5-aa83-c00fe9315782")
        path = HERE / "commands" / f"{a.name}.json"
        print(json.dumps(dict(command=str(path), sha256=write_new(path, cmd)), indent=1))
    return 0 if not check.failures else 1


if __name__ == "__main__":
    sys.exit(main())
