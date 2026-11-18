"""CPU-only process tests for the coupled cross-process lock and owned process-tree cleanup."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import uuid

from device_lease import exclusive, winjob

HERE = Path(__file__).resolve().parent


def probe():
    with TemporaryDirectory() as scratch:
        path = Path(scratch) / "test.lock"
        src = ("import sys;sys.path.insert(0,sys.argv[1]);from device_lease import exclusive;"
               "from pathlib import Path\nwith exclusive(Path(sys.argv[2])): pass")
        argv = [sys.executable,"-I","-B","-c",src,str(HERE),str(path)]
        with exclusive(path):
            rejected = subprocess.run(argv,capture_output=True)
        admitted = subprocess.run(argv,capture_output=True)
        assert rejected.returncode != 0 and b"PermissionError" in rejected.stderr and admitted.returncode == 0
        name = "Local\\eLedgerCare-guard-test-" + uuid.uuid4().hex
        job = winjob.create(name)
        child = None
        try:
            test = ("import subprocess,sys,time;sys.path.insert(0,sys.argv[1]);from device_lease import winjob;"
                    "winjob.join(sys.argv[2]);gc=subprocess.Popen([sys.executable,'-I','-c','import time;time.sleep(30)']);"
                    "print(gc.pid,flush=True);time.sleep(30)")
            child = subprocess.Popen([sys.executable,"-I","-B","-c",test,str(HERE),name],
                                     stdout=subprocess.PIPE,text=True)
            pid = int(child.stdout.readline().strip())
        finally:
            winjob.close(job)
        # A kill-on-close job may supply exit code zero. Both children sleep for
        # 30 s, so observed termination within 10 s distinguishes job closure.
        child.wait(timeout=10)
        task = subprocess.check_output(["tasklist","/FI",f"PID eq {pid}","/FO","CSV","/NH"],text=True)
        assert f'","{pid}","' not in task
    return {"second_writer_rejected":True,"reacquired_after_release":True,"owned_child_and_grandchild_removed":True,
            "gpu_calls":0}


if __name__ == "__main__":
    print(json.dumps(probe(), indent=2))
