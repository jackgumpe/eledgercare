"""Run the independent reviewer's published A1 tools from their exact command commit.

The coordinator records custody here. The reviewer's branch and acceptance remain
under the independent operator's control. No part of this script starts inference.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
AUDITOR = REPO.parent / "eledgercare-worktrees/ablation-frozen-auditor"
REVIEW_SHA = "62f4ce4407b3ef6093a412d0504408c500a42c92"
TOOLS = AUDITOR / "docs/reviews/WP-0017"
PYTHON = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe")
PACKET = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0017")
LEASE = PACKET / "coordination/leases/a1-r1"
CARRIER = PACKET / "coordination/carrier/a1-r1"
RUNS = PACKET / "review/runs"
INVENTORY = HERE / "a1-r1-blind-inventory.json"
NORMALIZED = HERE / "a1-r1-normalized.json"
DECISION = HERE / "a1-r1-machine-decision.json"
AUDIT = TOOLS / "evidence/A1-prefix-audit.json"
AUDIT_SHA = "16eca676114e847059503290b3c4a620eb1625769dd7f3a3e0a39ab252d263b3"
GROUPS = ("endpoints", "switches")


def git(root, *args):
    return subprocess.check_output(["git", "-C", root, *args])


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_tools():
    if git(AUDITOR, "rev-parse", "HEAD").decode().strip() != REVIEW_SHA:
        raise ValueError("unexpected reviewer checkout")
    if git(AUDITOR, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("reviewer checkout must be clean")
    if digest(AUDIT.read_bytes()) != AUDIT_SHA:
        raise ValueError("frozen reviewer prefix audit differs")
    receipt = json.loads((CARRIER / "received.json").read_bytes())
    if receipt["operator_commit"] != REVIEW_SHA:
        raise ValueError("operator command commit differs")
    return json.loads((CARRIER / "return.json").read_bytes())


def call(tool, *args):
    return subprocess.run([PYTHON, "-I", "-B", TOOLS / tool, *args], cwd=AUDITOR).returncode


def inventory():
    if INVENTORY.exists():
        raise FileExistsError(INVENTORY)
    records = [HERE / "a1-r1-release.json", PACKET / "coordination/a1-inputs.json",
               TOOLS / "commands/a1-r1.json"]
    records.extend(HERE / "a1-plans" / f"a1-r1-{group}.json" for group in GROUPS)
    receipts = [CARRIER / "received.json", CARRIER / "return.json"]
    receipts.extend(sorted(p for p in LEASE.iterdir() if p.is_file()))
    runs = [path for group in GROUPS for path in
            (RUNS / f"a1-r1-{group}", RUNS / f"a1-r1-{group}-order") if path.is_dir()]
    if not runs:
        raise ValueError("no raw run directories")
    return call("escrow.py", "--stage", "A1", "--runs", *runs, "--records", *records,
                "--operator", *receipts, "--out", INVENTORY)


def analyze():
    relative = INVENTORY.relative_to(REPO).as_posix()
    published = git(REPO, "show", "origin/coordination/bootstrap:" + relative)
    if digest(published) != digest(INVENTORY.read_bytes()):
        raise ValueError("publish the blind inventory byte for byte before analysis")
    if NORMALIZED.exists() or DECISION.exists():
        raise FileExistsError("retain previous analyses under their original names")
    status = call("a1_normalize.py", "--inventory", INVENTORY, "--endpoints", RUNS / "a1-r1-endpoints",
                  "--switches", RUNS / "a1-r1-switches", "--out", NORMALIZED)
    if not NORMALIZED.is_file():
        return status or 1
    result = call("a1_decide.py", "--audit", AUDIT, "--audit-sha256", AUDIT_SHA,
                  "--inventory", INVENTORY, "--results", NORMALIZED, "--out", DECISION)
    return status or result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inventory", "analyze"))
    args = parser.parse_args()
    checked_tools()
    raise SystemExit(inventory() if args.action == "inventory" else analyze())
