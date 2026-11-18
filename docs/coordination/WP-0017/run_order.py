"""Collect actual subprocess receipts for a released order. The parent owns the OS GPU lease."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(path, obj):
    tmp = path.with_suffix(".pending")
    with tmp.open("x", encoding="utf8", newline="\n") as stream:
        json.dump(obj, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    tmp.rename(path)


def run(plan, expected_hash):
    if digest(plan) != expected_hash:
        raise ValueError("order plan changed")
    order = json.loads(plan.read_bytes())
    if subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() != order["source"]:
        raise RuntimeError("unexpected engine worktree")
    for filename, value in order.get("bound_files", {}).items():
        if digest(Path(filename)) != value:
            raise ValueError(f"bound input changed: {filename}")
    out = Path(order["output"])
    out.mkdir(parents=True, exist_ok=False)
    segments = []
    try:
        for n, command in enumerate(order["commands"],1):
            start = datetime.now(timezone.utc).isoformat()
            begin = time.monotonic()
            with (out / f"{n:02d}-stdout.txt").open("xb") as stdout, (out / f"{n:02d}-stderr.txt").open("xb") as stderr:
                result = subprocess.run(command["argv"], cwd=order["worktree"], env={**os.environ, **command.get("env",{})},
                                        stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL)
            record = dict(label=command["label"], returncode=result.returncode, argv=command["argv"], started=start,
                          elapsed_seconds=time.monotonic()-begin)
            segments.append(record)
            save(out/f"{n:02d}-process.json",record)
            result.check_returncode()
            for item in command.get("required_outputs",[]):
                if not Path(item).is_file():
                    raise RuntimeError("missing released output " + item)
        complete = True
    except BaseException:
        complete = False
        raise
    finally:
        save(out/"process.json",dict(plan_sha256=expected_hash,all_segments_completed=complete,segments=segments))


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan",type=Path)
    p.add_argument("sha256")
    args=p.parse_args()
    run(args.plan,args.sha256)
