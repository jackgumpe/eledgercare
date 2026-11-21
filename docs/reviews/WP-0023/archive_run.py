"""Package the operator receipts and primary bytes, omitting only mutable runtime caches."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def peak(rows):
    return dict(samples=len(rows), peak_used_mib=max((r["used_mib"] for r in rows), default=None),
                minimum_free_mib=min((r["free_mib"] for r in rows), default=None))


def utc_ns(iso):
    delta = datetime.fromisoformat(iso) - datetime(1970,1,1,tzinfo=timezone.utc)
    return (delta.days*86400+delta.seconds)*1_000_000_000 + delta.microseconds*1000


def archive(root, name, packet, out):
    run = root / "review/runs" / name
    lease = root / "coordination/leases" / name
    files = {}
    for prefix, paths in [("run",run.glob("*")), ("run/trial",(run/"trial").glob("*")),
                          ("guard",lease.glob("*")), ("binding",[packet/(name+"-plan.json"),packet/(name+"-release.json")])]:
        for p in paths:
            if p.is_file():
                files[prefix+"/"+p.name] = p.read_bytes()
    with zipfile.ZipFile(out,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for label, raw in sorted(files.items()):
            entry = zipfile.ZipInfo(label,date_time=(1980,1,1,0,0,0))
            z.writestr(entry,raw,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(out) as z:
        assert not z.testzip() and all(z.read(label)==blob for label, blob in files.items())
    board = [json.loads(line) for line in files[f"guard/{name}-device.jsonl"].splitlines()]
    phases = {}
    for label, contents in files.items():
        if label.startswith("run/trial/") and label.endswith(".json"):
            record = json.loads(contents)
            timing = record.get("metrics", record)
            if "start_utc_ns" in timing and "end_utc_ns" in timing:
                samples = [r for r in board if timing["start_utc_ns"] <= utc_ns(r["utc"]) <= timing["end_utc_ns"]]
                phases[label] = peak(samples)
    release = json.loads(files[f"binding/{name}-release.json"])
    plan = json.loads(files[f"binding/{name}-plan.json"])
    guard_return = json.loads(files["guard/returned.json"])
    assert sha(files[f"binding/{name}-release.json"]) == guard_return["release_sha256"]
    assert sha(files[f"binding/{name}-plan.json"]) == release["orders"][0]["plan_sha256"]
    assert release["review_worktree_head"] == plan["candidate"]
    return dict(archive=out.name, archive_sha256=sha(out.read_bytes()), candidate=plan["candidate"], lease=name,
                files={key:dict(sha256=sha(raw),bytes=len(raw)) for key,raw in sorted(files.items())},
                board=peak(board), stages=phases, guard_return=guard_return)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("packet",type=Path)
    parser.add_argument("out",type=Path)
    a=parser.parse_args()
    root = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0023")
    print(json.dumps(archive(root,a.name,a.packet,a.out),indent=2))
