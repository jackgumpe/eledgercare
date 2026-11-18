"""Freeze the pair captures and cross-check all 19 configurations with the engine author's published analyzer."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mirror_a1 import HERE, PACKET, PYTHON, REPO, RUNS, call, checked_tools, digest, git

PRIOR = HERE / "a1-r1-blind-inventory.json"
INVENTORY = HERE / "a1-p1-blind-inventory.json"
COMBINED = HERE / "a1-p1-carbon-combined.json"
PAIR_SHA = "02eef09347e60af3b99d34fbe9eb7bddaa3151d6abd93a8dd0b01131ed56d8a8"
SOURCE = "c235bc61820def84142480e6e2a7a2e5485176d6"
REPLAY = REPO.parent / "eledgercare-worktrees/ablation-replay"


def freeze():
    lease = PACKET / "coordination/leases/a1-p1"
    carrier = PACKET / "coordination/carrier/a1-p1"
    release = HERE / "a1-p1-release.json"
    if digest(release.read_bytes()) != PAIR_SHA or json.loads((lease / "returned.json").read_bytes())["release_sha256"] != PAIR_SHA:
        raise ValueError("the actual pair lease did not return the expected release")
    prior = json.loads(PRIOR.read_bytes())
    folders = [Path(r["path"]) for r in prior["runs"]]
    folders += [r for r in (RUNS / "a1-p1-pairs", RUNS / "a1-p1-pairs-order") if r.exists()]
    receipts = sorted(p for p in lease.iterdir() if p.is_file()) + [carrier / "received.json", carrier / "return.json"]
    records = [release, PRIOR, HERE / "a1-r1-machine-decision.json", HERE / "a1-plans/a1-p1-pairs.json",
               PACKET / "coordination/a1-inputs.json"]
    code = call("escrow.py", "--stage", "A1", "--runs", *folders, "--records", *records, "--operator",
                *receipts, "--out", INVENTORY)
    if code:
        return code
    current = {r["run"]: r for r in json.loads(INVENTORY.read_bytes())["runs"]}
    if any(current.get(r["run"]) != r for r in prior["runs"]):
        raise ValueError("initial configurations differ from their original inventory")
    return 0


def analyze():
    published = git(REPO, "show", "origin/coordination/bootstrap:" + INVENTORY.relative_to(REPO).as_posix())
    if published != INVENTORY.read_bytes():
        raise ValueError("publish the new opaque inventory before reading pair findings")
    if git(REPLAY, "rev-parse", "HEAD").decode().strip() != SOURCE or git(REPLAY, "status", "--porcelain"):
        raise ValueError("author analyzer checkout differs from GPU source")
    if COMBINED.exists():
        raise FileExistsError(COMBINED)
    argv = [PYTHON, "-I", "-B", REPLAY / "docs/research/WP-0017/engine/a1_analyze.py",
            "--run-dirs", RUNS / "a1-r1-endpoints", RUNS / "a1-r1-switches", RUNS / "a1-p1-pairs",
            "--endpoint-check", RUNS / "a1-r1-endpoints-order/endpoint-check.json",
            "--a1-manifest", PACKET / "coordination/a1-inputs.json",
            "--a1-manifest-sha256", "e7f47d141972d0e32c53d16e090fcddc237c453ecfc2eaf5d494c6d3426bc8ef",
            "--out", COMBINED]
    return subprocess.run(argv, cwd=REPLAY).returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "analyze"))
    a = parser.parse_args()
    checked_tools()
    raise SystemExit(freeze() if a.action == "freeze" else analyze())
