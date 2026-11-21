"""Observe external board ownership, then invoke the coordinator's exact shared guard at most once."""
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
PREVIOUS=HERE.parent/"WP-0024"
sys.path[:0]=[str(HERE),str(PREVIOUS)]
from admission_watch import board
from binding import GPU,HOST,QPY,verify


def now():
    return datetime.now(timezone.utc).isoformat()


def record(path,data):
    with path.open("x",encoding="utf8",newline="\n") as f:
        f.write(json.dumps(data,indent=2)+"\n")
        f.flush()
        os.fsync(f.fileno())


def execute(release,digest,candidate,plans):
    folder=HOST/"review/operator"
    folder.mkdir(parents=True,exist_ok=True)
    assert Path(sys.executable)==QPY and sys.flags.isolated and sys.dont_write_bytecode
    assert not (folder/"issued.json").exists()
    guard=release.parent/"device_lease.py"
    binding=verify(release,digest,candidate,plans)
    old=PREVIOUS/"admission-watch-binding.json"
    assert sha256(old.read_bytes()).hexdigest()=="ad311561b81f7d3f86938861726385fa5f7ddd0ffff826d6a205552697b7ab6d"
    state=board(json.loads(old.read_bytes()))
    record(folder/("board-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+".json"),state)
    if state["holds"]:
        print(json.dumps(state,indent=2))
        return 75
    assert state["gpu"]==GPU and state["free_mib"]>=12000
    argv=[str(QPY),"-I","-B",str(guard),str(release),digest]
    record(folder/"issued.json",dict(utc=now(),pid=os.getpid(),argv=argv,board=state,binding=binding))
    with (folder/"guard.log").open("xb") as log:
        process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        record(folder/"guard-start.json",dict(pid=process.pid,utc=now()))
        exit_code=process.wait()
    record(folder/"return.json",dict(exit_code=exit_code,pid=process.pid,utc=now(),post_observation=board(json.loads(old.read_bytes()))))
    return exit_code


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("release",type=Path)
    p.add_argument("digest")
    p.add_argument("candidate")
    p.add_argument("plans",nargs=2)
    a=p.parse_args()
    sys.exit(execute(a.release.resolve(),a.digest,a.candidate,a.plans))
