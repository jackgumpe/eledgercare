"""Observe ownership, pin both checkouts, then journal the one coordinator-issued guard command."""
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_common import HOST, HIST, QPY, pinned, save, sha
sys.path.insert(0,str(HIST))
from admission_watch import board

def now():
    return datetime.now(timezone.utc).isoformat()

def run(path,pin,revision):
    assert Path(sys.executable).resolve() == QPY.resolve() and sys.flags.isolated and sys.dont_write_bytecode
    rel = pinned(path,pin)
    assert rel["packet"] == "WP-0026" and rel["operator"] == "eld-rd-reviewer"
    root,dev = path.parents[3],Path(rel["worktree"])
    assert rel["review_worktree_head"] == revision
    assert subprocess.check_output(["git","-C",dev,"rev-parse","HEAD"],text=True).strip() == revision
    assert not subprocess.check_output(["git","-C",dev,"status","--porcelain","--untracked-files=all"])
    for folder,key in ((root,"coordination_files"),(dev,"source_files")):
        for f,s in rel[key].items():
            assert sha((folder/f).read_bytes()) == s, f
    plans = [pinned(Path(order["plan"]),order["plan_sha256"]) for order in rel["orders"]]
    if rel["name"] == "h0-r1":
        assert [p["process_id"] for p in plans] == ["p1","p2"]
        assert ["".join(c["mode"] for c in p["calls"]) for p in plans] == ["SSSSHHHH","HHHHSSSS"]
        assert all([c["ordinal"] for c in p["calls"]] == list(range(2,10)) for p in plans)
    assert all(p["candidate"] == revision for p in plans)
    binding = pinned(HIST/"admission-watch-binding.json","ad311561b81f7d3f86938861726385fa5f7ddd0ffff826d6a205552697b7ab6d")
    assert rel["gpu_uuid"] == binding["gpu"] and rel["free_floor_mib"] == binding["free_floor_mib"] == 12000
    journal = HOST/"review/operator"/rel["name"]
    journal.mkdir(parents=True,exist_ok=True)
    assert not (journal/"issued.json").exists()
    attempts = 0
    while attempts < 60:
        attempts += 1
        state = board(binding)
        save(journal/(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+".json"),state)
        if not state["holds"]:
            break
        time.sleep(50)
    else:
        return 75
    lease = HOST/"coordination/leases"/rel["name"]
    assert not lease.exists()
    argv = [str(QPY),"-I","-B",str(path.parent/"device_lease.py"),str(path),pin]
    save(journal/"issued.json",{"argv":argv,"utc":now(),"pid":os.getpid(),"candidate":revision,
                                "board":state,"release_sha256":pin})
    with (journal/"guard.log").open("xb") as log:
        p = subprocess.Popen(argv,cwd=root,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
        save(journal/"started.json",{"pid":p.pid,"utc":now()})
        ret = p.wait()
    save(journal/"return.json",{"pid":p.pid,"utc":now(),"exit_code":ret,"board":board(binding)})
    return ret

if __name__ == "__main__":
    sys.exit(run(Path(sys.argv[1]).resolve(),sys.argv[2],sys.argv[3]))
