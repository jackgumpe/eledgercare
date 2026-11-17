"""One-shot authorized reviewer004 launcher; records original exits, never retries."""
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(r"C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-f4-reviewer")
HERE=Path(__file__).resolve().parent
HEAD="ae71a7362718f36e351e3fd442d9751d875146fe"
AUTH="ddeeaba37868ee635c8f9e5641e3c0fc04404156"
LEASE="WP-0012-reviewer-004-r2-20261117T173846Z"
OUT=Path(r"C:/Users/jackg/eLedgerCare-Demo/WP-0012/reviewer/rehearsal-evidence/WP-0012-reviewer-004-native-02")
HELPER=ROOT/"docs/reviews/WP-0012/eld-f4-reviewer/live-004/preflight-correction/helpers/run_wp0012_reviewer_rehearsal_v6.py"
def utc():return datetime.now(timezone.utc).isoformat()
def identity(pid):
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
    kernel.GetProcessTimes.restype=wintypes.BOOL
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return {"pid":pid,"identity_unavailable":True}
    try:
        creation,exit_time,kernel_time,user_time=[wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle,ctypes.byref(creation),ctypes.byref(exit_time),ctypes.byref(kernel_time),ctypes.byref(user_time)):
            return {"pid":pid,"identity_unavailable":True}
        return {"pid":pid,"create_filetime":(creation.dwHighDateTime<<32)|creation.dwLowDateTime}
    finally:kernel.CloseHandle(handle)
def main():
    assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT).decode().strip()==HEAD
    assert not subprocess.check_output(["git","status","--porcelain","--untracked-files=all"],cwd=ROOT).strip()
    assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=="7fafe34da2f46ce9508a54748c275d272147655285c209c2fcf68ed34240f5df"
    assert hashlib.sha256((HELPER.parent/"ownership_v6.py").read_bytes()).hexdigest()=="ff01e70c09c1e7b69cbed3c660f9f6cb777d381a920a51af7e1204d24eee6d9f"
    assert not OUT.exists(), "Fresh external output root required"
    receipt=HERE/"launcher-receipt.json"
    assert not receipt.exists(),"Single invocation only; existing receipt must be preserved"
    data={"schema":"eledgercare.wp0012.reviewer004-launch/1","lease_id":LEASE,"release_commit":AUTH,
          "executing_head":HEAD,"launcher_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "wrapper_identity":identity(os.getpid()),"started_utc":utc(),"invocations":[]}
    def save():receipt.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8",newline="\n")
    def event(value):
        with (HERE/"events.jsonl").open("a",encoding="utf-8",newline="\n") as stream:stream.write(json.dumps(value)+"\n")
        print(json.dumps(value),flush=True)
    save();event({"event":"wrapper_started","utc":utc(),"identity":data["wrapper_identity"]})
    for mode in ("validate-release-cpu","live-leased-rehearsal"):
        command=[sys.executable,"-B",str(HELPER),"--mode",mode,"--release-commit",AUTH,
                 "--release-path","docs/coordination/WP-0012/releases/reviewer-004-r2.json",
                 "--summary-output",str(OUT/("cpu-release-validation.json" if mode=="validate-release-cpu" else "summary.json"))]
        if mode=="live-leased-rehearsal":
            for flag,path in (("--q0-check-output","q0-check.json"),("--resource-return-output","resource-return.json"),("--logs-dir","logs"),("--screenshots-dir","screenshots")):
                command += [flag,str(OUT/path)]
        started=utc()
        with (HERE/(mode+".stdout.log")).open("xb") as stdout, (HERE/(mode+".stderr.log")).open("xb") as stderr:
            proc=subprocess.Popen(command,cwd=ROOT,stdout=stdout,stderr=stderr)
            entry={"mode":mode,"command":command,"started_utc":started,"identity":identity(proc.pid)}
            data["invocations"].append(entry);save();event({"event":"invocation_started",**entry})
            code=proc.wait()
        entry.update(ended_utc=utc(),exit_code=code);save();event({"event":"invocation_ended","mode":mode,"utc":utc(),"exit_code":code})
        if code!=0:
            data.update(ended_utc=utc(),wrapper_exit_code=code);save();return code
    data.update(ended_utc=utc(),wrapper_exit_code=0);save();return 0
if __name__=="__main__":raise SystemExit(main())
