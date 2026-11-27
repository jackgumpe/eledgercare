"""Private WP-0045 current-user limited entry. Never runs a plan before checking its own token."""
import ctypes as c
import json, os, subprocess, sys, time
from pathlib import Path
from ctypes import wintypes as w

def token_state():
    a=c.WinDLL("advapi32",use_last_error=True)
    k=c.WinDLL("kernel32",use_last_error=True)
    t=w.HANDLE()
    if not a.OpenProcessToken(c.c_void_p(-1),8,c.byref(t)):
        raise c.WinError(c.get_last_error())
    try:
        def info(kind):
            n=w.DWORD()
            a.GetTokenInformation(t,kind,None,0,c.byref(n))
            b=c.create_string_buffer(n.value)
            if not a.GetTokenInformation(t,kind,b,n,c.byref(n)):
                raise c.WinError(c.get_last_error())
            return b
        label=info(25)
        sid=c.cast(label,c.POINTER(c.c_void_p))[0]
        a.GetSidSubAuthorityCount.argtypes=[c.c_void_p]
        a.GetSidSubAuthorityCount.restype=c.POINTER(c.c_ubyte)
        a.GetSidSubAuthority.argtypes=[c.c_void_p,w.DWORD]
        a.GetSidSubAuthority.restype=c.POINTER(w.DWORD)
        count=a.GetSidSubAuthorityCount(sid)[0]
        rid=a.GetSidSubAuthority(sid,count-1)[0]
        return {"integrity_rid":rid,"elevated":bool(w.DWORD.from_buffer(info(20)).value),
                "effective_admin":bool(c.windll.shell32.IsUserAnAdmin())}
    finally:
        k.CloseHandle(t)

def main(planfile):
    raw=planfile.read_bytes()
    plan=json.loads(raw)
    out=planfile.with_name(planfile.stem+".receipt.json")
    if out.exists():raise FileExistsError(out)
    token=token_state()
    report={"token":token,"launched":False,"exit":None}
    if not (8192 <= token["integrity_rid"] < 12288 and not token["elevated"] and not token["effective_admin"]):
        report["error"]="ordinary current-user token requirement failed"
    elif plan["argv"]:
        from hashlib import sha256
        report["plan_sha256"]=sha256(raw).hexdigest()
        env=dict(os.environ,OMP_NUM_THREADS="1",MKL_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",PYTHONDONTWRITEBYTECODE="1")
        cmd=plan["argv"]
        t=time.monotonic()
        with planfile.with_name(planfile.stem+".stdout").open("xb") as out_stream, planfile.with_name(planfile.stem+".stderr").open("xb") as err_stream:
            try:
                proc=subprocess.run(cmd,env=env,cwd=plan["cwd"],stdin=subprocess.DEVNULL,stdout=out_stream,stderr=err_stream,timeout=min(300,int(plan.get("timeout",300))))
                report.update(launched=True,exit=proc.returncode)
            except Exception as exc:report["error"]=str(exc)
        report["elapsed_seconds"]=time.monotonic()-t
    else:
        report["exit"]=0
    with out.open("x",encoding="utf8") as f:json.dump(report,f,indent=2)
    return report["exit"] if report["exit"] is not None else 3

if __name__=="__main__":
    raise SystemExit(main(Path(sys.argv[1])))
