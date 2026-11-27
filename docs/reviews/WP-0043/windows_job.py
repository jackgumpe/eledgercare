"""Observe membership of a harmless venv launcher and its interpreter in one job."""
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import subprocess
import sys


def process_list(handle):
    class Ids(C.Structure):
        _fields_=[("assigned",W.DWORD),("listed",W.DWORD),("ids",C.c_size_t * 32)]
    ids=Ids()
    kernel=C.WinDLL("kernel32",use_last_error=True)
    query=kernel.QueryInformationJobObject
    query.argtypes=[W.HANDLE,C.c_int,W.LPVOID,W.DWORD,W.LPVOID]
    query.restype=W.BOOL
    if not query(handle,3,C.byref(ids),C.sizeof(ids),None):
        raise C.WinError(C.get_last_error())
    return list(ids.ids[:ids.listed])


def main(src, interpreter, suspended):
    sys.path.insert(0,str(src))
    import limits
    handles=[]
    factory=limits.winapi

    class Inspectable:
        def __init__(self):
            self.native=factory()
        def __getattr__(self,name):
            return getattr(self.native,name)
        def CreateJobObjectW(self,*args):
            h=self.native.CreateJobObjectW(*args)
            handles.append(h)
            return h

    limits.winapi = Inspectable
    code="import os,sys,time; print(os.getpid(),flush=True); time.sleep(2.5)"
    # Schedule a live descendant before job assignment in the original Popen-then-job
    # design. The timer always exits the harmless process even if job assignment fails.
    flags=subprocess.CREATE_NO_WINDOW | (4 if suspended else 0)
    proc=subprocess.Popen([str(interpreter),"-B","-u","-c",code],stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,creationflags=flags)
    try:
        child_pid=None if suspended else int(proc.stdout.readline().strip())
        with limits.job(proc,256<<20):
            if suspended:
                child_pid=int(proc.stdout.readline().strip())
            membership=process_list(handles[-1])
            report={"launcher_pid":proc.pid,"executing_interpreter_pid":child_pid,"observed_job_members":membership,
                    "launcher_in_test_job":proc.pid in membership,"interpreter_in_test_job":child_pid in membership,
                    "schedule":"suspended launcher assigned before resume" if suspended else
                               "interpreter reached stdout before launcher was assigned"}
            out,err=proc.communicate(timeout=10)
            assert proc.returncode==0 and not out and not err
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=10)
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main(Path(sys.argv[1]),Path(sys.argv[2]),"--suspended" in sys.argv[3:])
