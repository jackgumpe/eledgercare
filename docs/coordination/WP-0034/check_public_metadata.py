"""Record the public branch and receipt inventory used for the coordinator's admission cross-check."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = "ffec32d08f4137bea6d01505b1677b64cccbf5bc"
RESERVATION = "604a3a051d901ec8a1a8f7d6407ef57d99b19c10"
ROOT_SCRATCH = Path("C:/Users/jackg/eLedgerCare-Speed")

def git(*args):
    return subprocess.check_output(["git","--no-optional-locks",*args])

def at(path):
    obj = git("cat-file","blob",f"{BASE}:{path}")
    return json.loads(obj), {"revision":BASE,"path":path,"sha256":hashlib.sha256(obj).hexdigest()}

def witness():
    history = set(git("rev-list",BASE).decode().splitlines())
    branches = dict(reversed(line.split()) for line in git("ls-remote","--heads","origin").decode().splitlines())
    local = dict(line.split() for line in git("for-each-ref","--format=%(refname) %(objectname)","refs/heads","refs/remotes").decode().splitlines())
    paths = {}
    for branch,sha in sorted(set(local.items()) | set(branches.items())):
        if sha in history:
            continue
        parent=git("merge-base",BASE,sha).decode().strip()
        changed=git("diff","--name-only",parent,sha).decode().splitlines()
        paths[branch+"@"+sha]={"public":branches.get(branch)==sha,"local":local.get(branch)==sha,"tip":sha,"changed_path_count":len(changed),"outside_packet_paths":
            [p for p in changed if "WP-0034/" not in p and p not in ("INDEX.md","CURRENT.md")]}
    names = git("ls-tree","-d","--name-only",f"{BASE}:docs/fixtures").decode().splitlines()
    receipts={}
    def read(path):
        result,receipt=at(path)
        receipts[path]=receipt
        return result
    order=read("docs/coordination/WP-0026/blind-custody-release.json")
    receipt=read("docs/fixtures/WP-0026/blind/receipt.json")
    counts=read("docs/reviews/WP-0026/blind-c1-partial-runtime.json")
    assert (order["blind_pairs"],order["blind_binders"])==(receipt["pairs"],receipt["binders"])
    scope=read("docs/coordination/WP-0029/decision.json")["scope"]
    assert "same opening-name edit" in scope and "development pairs" in scope
    dev={}
    for split in ("train","cal"):
        d=read(f"docs/fixtures/WP-0024/v2/{split}/receipt.json")
        dev[split]={"pairs":d["pairs"],"binders":d["binders"]}
    return {"basis":BASE,"reservation":RESERVATION,"utc":datetime.now(timezone.utc).isoformat(),
        "source_receipts":receipts,"public_head_count":len(branches),"local_ref_count":len(local),
        "public_head_list_sha256":hashlib.sha256(json.dumps(branches,sort_keys=True).encode()).hexdigest(),
        "tips_outside_accepted_history":paths,"tracked_fixture_directories":names,
        "product_scratch_top_level_names":sorted(p.name for p in ROOT_SCRATCH.iterdir() if p.is_dir()),
        "prior_inputs":{"exposed_development":scope,"WP0024_public_development_receipts":dev,
            "WP0026_separate_custody":{"action":order["action"],"horizons":order["horizons"],
                "pairs":receipt["pairs"],"binders":receipt["binders"],"capture_windows_issued":len(counts["issued_scored"]),
                "capture_windows_verified":len(counts["verified_scored"])}},
        "scope":"Committed product public metadata, names of public/manual local refs and top-level product inventory. Historical blind sources are represented by a custody order, aggregate receipt and acquisition counters only. External or undisclosed holdings are outside the search."}

if __name__=="__main__":
    result=witness()
    with Path(sys.argv[1]).open("x",encoding="utf-8",newline="\n") as out:
        json.dump(result,out,indent=2,allow_nan=False)
        out.write("\n")
