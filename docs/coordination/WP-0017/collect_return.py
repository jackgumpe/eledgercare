"""Collect completed lease clocks, board samples, exit receipts and worker identity checks."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
PACKET = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0017")


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker_status(meta):
    try:
        seconds = psutil.Process(meta["pid"]).create_time()
    except psutil.NoSuchProcess:
        return "exited"
    except psutil.AccessDenied:
        return "unverified"
    # FILETIME uses 100 ns ticks since 1601. psutil returns seconds since 1970.
    original = meta["creation_filetime"] / 10_000_000 - 11_644_473_600
    return "alive" if abs(seconds - original) < 0.002 else "pid reused"


def collect(name):
    release_path = HERE / (name + "-release.json")
    release = read(release_path)
    lease = PACKET / "coordination/leases" / name
    carrier = PACKET / "coordination/carrier" / name
    retired = read(lease / "returned.json")
    if retired["release_sha256"] != sha(release_path):
        raise ValueError("return does not match the published release")
    result = dict(lease=name, operator=read(carrier / "received.json")["operator_commit"],
                  candidate=release["review_worktree_head"], release_sha256=sha(release_path),
                  acquired_utc=read(lease / "acquired.json")["utc"], returned=retired,
                  carrier_exit=read(carrier / "return.json")["exit"], orders=[],
                  checked_utc=datetime.now(timezone.utc).isoformat())
    for order in release["orders"]:
        label = order["run"]
        returned = lease / (label + "-returned.json")
        if not returned.is_file():
            result["orders"].append(dict(order=label, status="no order return"))
            continue
        end = read(returned)
        sample_path = lease / (label + "-device.jsonl")
        samples = [json.loads(line) for line in sample_path.read_bytes().splitlines() if line]
        folder = Path(order["output"])
        children = []
        for command in read(Path(order["plan"]))["commands"]:
            for path in map(Path, command.get("required_outputs", ())):
                if path.name != "process.json" or not path.exists():
                    continue
                for child in read(path)["segments"]:
                    meta = child.get("child_meta") or {}
                    children.append(dict(mode=child["mode"], exit=child["returncode"], reason=child["reason"],
                                         process=meta, observed=worker_status(meta) if meta.get("creation_filetime") else "unverified"))
        result["orders"].append(dict(order=label, exit=end["exit"], guard=end["guard"], wall_s=end["wall_s"],
                                     samples=len(samples), peak_board_mib=max((x["used_mib"] for x in samples), default=None),
                                     board_after_mib=end["ownership_after_job_close"]["device"]["used_mib"],
                                     telemetry_sha256=sha(sample_path), return_sha256=sha(returned),
                                     outer_process=read(folder / "process.json") if (folder / "process.json").exists() else None,
                                     children=children))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("lease", choices=("a1-r1", "a1-p1", "a2-r1", "a3-r1"))
    args = p.parse_args()
    result = collect(args.lease)
    dest = HERE / (args.lease + "-return.json")
    with dest.open("x", encoding="utf8", newline="\n") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print(dest, [(o["order"], o.get("exit"), o.get("peak_board_mib")) for o in result["orders"]])
