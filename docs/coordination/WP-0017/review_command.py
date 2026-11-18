"""Carry a specific independent reviewer's committed command into the coordinator's Windows job.

Cloud CLI tool-command jobs do not reliably permit Windows breakaway. The operator pushes
one named command to the reserved review branch. This carrier validates that Git object,
the local release and all pinned digests, records its own identity, and executes it once.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PACKET=Path("C:/Users/jackg/eLedgerCare-Speed/WP-0017")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("release",type=Path)
    p.add_argument("sha256")
    p.add_argument("--wait",type=int,default=2400)
    a=p.parse_args()
    release=a.release.resolve(strict=True)
    if release.parent!=HERE or sha(release)!=a.sha256:
        raise ValueError("not the published release bytes")
    lease=json.loads(release.read_bytes())
    name=lease["name"]
    if release.name!=name+"-release.json" or lease["operator"]!="eld-rd-reviewer":
        raise ValueError("unexpected release/role")
    executor=HERE/"device_lease.py"
    expectation=dict(release_name=name,release_sha256=a.sha256,executor_sha256=sha(executor),
                     candidate=lease["review_worktree_head"],operator="eld-rd-reviewer",
                     action="execute once",stage=lease["gate"])
    rel=f"docs/reviews/WP-0017/commands/{name}.json"
    deadline=time.monotonic()+a.wait
    while time.monotonic()<deadline:
        branch="review/wp-0017-escrow"
        current=subprocess.check_output(["git","rev-parse",branch],cwd=ROOT,text=True).strip()
        data=subprocess.run(["git","show",f"{current}:{rel}"],cwd=ROOT,capture_output=True)
        if data.returncode==0:
            intent=json.loads(data.stdout)
            if any(intent.get(k)!=v for k,v in expectation.items()):
                raise ValueError("reviewer command differs from the signed release")
            remote=subprocess.check_output(["git","ls-remote","--heads","origin",branch],cwd=ROOT,text=True).split()[0]
            if subprocess.run(["git","merge-base","--is-ancestor",current,remote],cwd=ROOT,capture_output=True).returncode==0:
                break
        time.sleep(4)
    else:
        raise TimeoutError("independent reviewer did not submit this command")
    path=PACKET/"coordination"/"carrier"/name
    path.mkdir(parents=True, exist_ok=False)
    argv=[sys.executable,"-I","-B",str(executor),str(release),a.sha256]
    record=dict(operator_commit=current,operator_path=rel,operator_command_sha256=hashlib.sha256(data.stdout).hexdigest(),
                carrier="eld-coordinator Windows process",start=datetime.now(timezone.utc).isoformat(),argv=argv)
    (path/"received.json").write_text(json.dumps(record,indent=2),encoding="utf8")
    with (path/"stdout.txt").open("xb") as out,(path/"stderr.txt").open("xb") as err:
        result=subprocess.run(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
    (path/"return.json").write_text(json.dumps(dict(exit=result.returncode,utc=datetime.now(timezone.utc).isoformat())),encoding="utf8")
    return result.returncode

if __name__=="__main__":
    sys.exit(main())
