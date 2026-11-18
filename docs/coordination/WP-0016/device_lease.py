"""Execute already published G0 commands under one host file lock and kill-on-close Windows job."""
import argparse
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "qualification/baseline"))
import winjob

HOST = Path("C:/Users/jackg/eLedgerCare-Speed")
PACKET = HOST / "WP-0016"
GPU = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"
LOCK = HOST / (GPU + ".lock")


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    pending = path.with_suffix(".pending")
    with pending.open("x", encoding="utf8", newline="\n") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    if path.exists():
        raise FileExistsError(path)
    pending.rename(path)


@contextmanager
def exclusive(path):
    with path.open("a+b") as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def device():
    cmd = ["nvidia-smi", "--id=" + GPU, "--query-gpu=uuid,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu",
           "--format=csv,noheader,nounits"]
    row = next(csv.reader([subprocess.check_output(cmd, text=True, timeout=12).strip()], skipinitialspace=True))
    assert row[0] == GPU
    return dict(utc=utc(), total_mib=int(row[1]), used_mib=int(row[2]), free_mib=int(row[3]),
                temp_c=float(row[4]), utilization_percent=int(row[5]))


def ownership():
    cmd = ["nvidia-smi","--id="+GPU,"--query-compute-apps=pid,process_name","--format=csv,noheader,nounits"]
    rows = csv.reader(subprocess.check_output(cmd, text=True, timeout=12).splitlines(), skipinitialspace=True)
    apps = [{"pid":int(r[0]),"image":Path(r[1]).name} for r in rows if len(r) == 2 and r[0].isdigit()]
    suspect = [r for r in apps if any(k in r["image"].lower() for k in ("python","llama","inference","vllm","sglang"))]
    if suspect:
        raise RuntimeError(f"Another compute process owns the GPU: {suspect}")
    loaded = subprocess.check_output(["ollama", "ps"], text=True, timeout=12).splitlines()[1:]
    if any(line.strip() for line in loaded):
        raise RuntimeError("Ollama has a resident model")
    return {"device":device(),"processes":apps,"ollama_models":0}


def bind_inputs(lease, order):
    cwd = Path(lease["worktree"])
    source = subprocess.check_output(["git","-C",cwd,"rev-parse","HEAD"],text=True).strip()
    if source != lease["review_worktree_head"]:
        raise RuntimeError("Reviewer worktree changed after release")
    for rel, expected in lease["source_files"].items():
        if sha(cwd / rel) != expected:
            raise RuntimeError("Changed released file " + rel)
    for rel, expected in lease["coordination_files"].items():
        if sha(REPO / rel) != expected:
            raise RuntimeError("Changed coordination file " + rel)
    plan = Path(order["plan"])
    if sha(plan) != order["plan_sha256"]:
        raise RuntimeError("Plan changed")
    for item in json.loads(plan.read_bytes())["requests"]:
        if sha(Path(item["pdf"])) != item["sha256"] or len(item["rgb_sha256"]) != item["pages"]:
            raise RuntimeError("Released input changed")
    if Path(order["output"]).exists():
        raise FileExistsError(order["output"])


def run_order(path, lease, order, out):
    bind_inputs(lease, order)
    admission = ownership()
    if admission["device"]["free_mib"] < 12000:
        raise RuntimeError("The 12,000 MiB admission floor is unavailable")
    name = order["run"]
    job_name = "Local\\eLedgerCare-WP0016-" + uuid.uuid4().hex
    job = winjob.create(job_name)
    child = None
    reason = None
    begin = time.monotonic()
    try:
        with (out / (name + "-stdout.txt")).open("xb") as stdout, (out / (name + "-stderr.txt")).open("xb") as stderr:
            child = subprocess.Popen([sys.executable,"-I","-B",str(Path(__file__).resolve()),"child",str(path),
                                      name,job_name], stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL)
            dump(out / (name + "-issued.json"), {"issued":utc(), "admission":admission, "pid":child.pid,
                 "argv":order["argv"], "output":order["output"], "job":job_name})
            with (out / (name + "-device.jsonl")).open("x", encoding="utf8") as f:
                while child.poll() is None:
                    sample = device()
                    f.write(json.dumps(sample) + "\n")
                    f.flush()
                    if sample["used_mib"] > lease["ceiling_mib"]:
                        reason = f"Device used {sample['used_mib']} MiB, ceiling {lease['ceiling_mib']}"
                    elif time.monotonic() - begin > order["seconds"] + 15:
                        reason = "Bound supervised wall elapsed"
                    if reason:
                        break
                    try:
                        child.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
    finally:
        winjob.close(job)
        if child:
            child.wait(timeout=30)
    returned = ownership()
    record = {"utc":utc(),"exit":child.returncode,"guard":reason,"wall_s":time.monotonic()-begin,
              "ownership_after_job_close":returned,"output":order["output"]}
    dump(out / (name + "-returned.json"), record)
    if reason or child.returncode:
        raise RuntimeError(f"Order {name} stopped. {reason or child.returncode}")
    proc = json.loads((Path(order["output"]) / "process.json").read_bytes())
    if not proc["all_segments_completed"] or any(s["returncode"] for s in proc["segments"]):
        raise RuntimeError("Incomplete engine process return")


def run_release(path, expected):
    if sha(path) != expected:
        raise ValueError("Release digest mismatch")
    lease = json.loads(path.read_bytes())
    assert lease["gpu_uuid"] == GPU
    out = PACKET / "coordination/leases" / lease["name"]
    with exclusive(LOCK):
        out.mkdir(parents=True, exist_ok=False)
        dump(out / "acquired.json", {"pid":os.getpid(),"utc":utc(),"lock":str(LOCK),"release_sha256":expected})
        error = None
        try:
            for order in lease["orders"]:
                run_order(path, lease, order, out)
        except BaseException as exc:
            error = repr(exc)
            raise
        finally:
            dump(out / "returned.json", {"utc":utc(),"error":error,"release_sha256":expected,"retiring_pid":os.getpid()})


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "child":
        path, name, job = sys.argv[2:]
        winjob.join(job)
        cfg = json.loads(Path(path).read_bytes())
        order = next(o for o in cfg["orders"] if o["run"] == name)
        sys.exit(subprocess.run(order["argv"],cwd=cfg["worktree"]).returncode)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("release", type=Path)
    p.add_argument("sha256")
    args = p.parse_args()
    run_release(args.release, args.sha256)
