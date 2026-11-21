"""External one-shot H0 operator watch. The released device guard alone opens the GPU job."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import time


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sync(path, value, mode):
    with path.open(mode, encoding="utf8", newline="\n") as f:
        f.write(json.dumps(value,ensure_ascii=True,sort_keys=True)+"\n")
        f.flush()
        os.fsync(f.fileno())


def update(folder, status, **fields):
    entry=dict(utc=utc(),pid=os.getpid(),status=status,**fields)
    tmp=folder/"status.pending"
    sync(tmp,entry,"w")
    os.replace(tmp,folder/"status.json")
    sync(folder/"watch.jsonl",entry,"a")


def query(command):
    result=subprocess.run(command,capture_output=True,text=True,errors="replace",timeout=15,check=True,
                          creationflags=subprocess.CREATE_NO_WINDOW)
    return result.stdout


def board(binding):
    gpu=binding["gpu"]
    lines=query(["nvidia-smi","--id="+gpu,"--query-gpu=uuid,memory.free,memory.used,utilization.gpu",
                 "--format=csv,noheader,nounits"])
    device,free,used,busy=next(csv.reader(io.StringIO(lines),skipinitialspace=True))
    if device!=gpu:
        raise ValueError("GPU identity changed")
    processes=query(["nvidia-smi","--id="+gpu,"--query-compute-apps=pid,process_name","--format=csv,noheader,nounits"])
    rows=[{"pid":int(pid),"name":Path(path).name.casefold()} for pid,path in csv.reader(io.StringIO(processes),skipinitialspace=True)]
    non_desktop=[p for p in rows if p["name"] not in binding["observed_desktop_images"]]
    os_game=query(["tasklist.exe","/FI","IMAGENAME eq DD2.exe","/FO","CSV","/NH"])
    dd2_os=[int(r[1]) for r in csv.reader(io.StringIO(os_game)) if len(r)>1 and r[0].casefold()=="dd2.exe"]
    resident=[l for l in query(["ollama","ps"]).splitlines()[1:] if l.strip()]
    problems=[]
    if int(free)<binding["free_floor_mib"]:
        problems.append("free_below_floor")
    if dd2_os:
        problems.append("DD2_active")
    if non_desktop:
        problems.append("gpu_has_non_desktop_owner")
    if resident:
        problems.append("ollama_has_resident_model")
    return dict(gpu=device,free_mib=int(free),used_mib=int(used),utilization=int(busy),gpu_apps=rows,
                dd2_os_pids=dd2_os,dd2_gpu_pids=[p["pid"] for p in rows if p["name"]=="dd2.exe"],
                non_desktop=non_desktop,resident_ollama_count=len(resident),holds=problems)


def verify(binding):
    argv=binding["guard_argv"]
    if Path(argv[0]).resolve()!=Path(sys.executable).resolve() or argv[1:3]!=["-I","-B"] or len(argv)!=6:
        raise ValueError("Guard command or Q0 interpreter changed")
    guard,release=Path(argv[3]),Path(argv[4])
    if sha(release)!=argv[5] or sha(guard)!=binding["device_guard_sha256"]:
        raise ValueError("Release or device guard changed")
    lease=json.loads(release.read_bytes())
    order,=lease["orders"]
    if (lease["operator"]!="eld-rd-reviewer" or lease["name"]!="h0-r1" or lease["gpu_uuid"]!=binding["gpu"]
            or lease["free_floor_mib"]!=binding["free_floor_mib"] or sha(Path(order["plan"]))!=order["plan_sha256"]):
        raise ValueError("Lease terms changed")
    if lease["review_worktree_head"]!=binding["candidate"]:
        raise ValueError("Candidate changed")
    for folder,key in ((Path(lease["worktree"]),"source_files"),(guard.parents[3],"coordination_files")):
        if any(sha(folder/k)!=v for k,v in lease[key].items()):
            raise ValueError("Pinned worktree or guard dependency changed")


def watch(path,pin):
    if not sys.flags.isolated or not sys.dont_write_bytecode or sha(path)!=pin:
        raise ValueError("Watch binding or Q0 interpreter flags changed")
    binding=json.loads(path.read_bytes())
    folder=path.parent.resolve()
    if sha(Path(__file__))!=binding["watcher_sha256"] or folder!=Path(binding["watch_folder"]).resolve():
        raise ValueError("Watch source or location changed")
    with (folder/"watch.lock").open("a+b") as lock:
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            return  # An existing operator owns the watch; do not write its journals.
        try:
            if (folder/"attempt.json").exists() or Path(binding["guard_receipts"]).exists():
                update(folder,"already_consumed",binding_sha256=pin)
                return
            verify(binding)
            while True:
                try:
                    sample=board(binding)
                except (OSError,ValueError,subprocess.SubprocessError) as exc:
                    update(folder,"admission_observation_unavailable",error=repr(exc),binding_sha256=pin)
                    time.sleep(binding["poll_seconds"])
                    continue
                if not sample["holds"]:
                    break
                update(folder,"waiting",board=sample,binding_sha256=pin)
                time.sleep(binding["poll_seconds"])
            verify(binding)
            if Path(binding["guard_receipts"]).exists():
                update(folder,"already_consumed",binding_sha256=pin)
                return
            # Durable at-most-once boundary. Any runtime failure now requires a new operator disposition.
            sync(folder/"attempt.json",dict(utc=utc(),board=sample,argv=binding["guard_argv"],binding_sha256=pin),"x")
            with (folder/"guard-launch.log").open("xb") as log:
                child=subprocess.Popen(binding["guard_argv"],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                update(folder,"guard_started",guard_pid=child.pid,board=sample,binding_sha256=pin)
                code=child.wait()
            update(folder,"guard_returned",guard_exit=code,binding_sha256=pin)
        except Exception as exc:
            update(folder,"watch_error",error=repr(exc),binding_sha256=pin)
            raise
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)


if __name__=="__main__":
    args=argparse.ArgumentParser()
    args.add_argument("binding",type=Path)
    args.add_argument("digest")
    a=args.parse_args()
    watch(a.binding,a.digest)

