"""Run harmless CPU children through the stock supervisor with a substituted device probe."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sys
import time


WORKER="""
import pathlib,sys,time
here=pathlib.Path(sys.argv[1])
mode=sys.argv[2]
sys.stdin.readline()
(here/'phase').write_text('F07.warm1')
if mode=='stderr_stall':
    for i in range(80):
        print(i,file=sys.stderr,flush=True)
        time.sleep(.025)
elif mode=='end_files':
    for i in range(12):
        (here/('f'+str(i))).write_bytes(b'x')
elif mode=='expires':
    time.sleep(2)
else:
    deadline=time.monotonic()+4
    while not (here/'seen').exists() and time.monotonic()<deadline:
        time.sleep(.01)
    time.sleep(.45)
"""


def main(src, work):
    sys.path.insert(0,str(src))
    import native
    results=[]
    for mode,arm in (("stderr_stall","observed"),("end_files","untouched"),
                     ("expires","observed"),("exit_between_polls","untouched")):
        root=work/mode
        root.mkdir(parents=True)
        folder=root/arm
        native.OUT=root
        native.LIMITS.update(poll_s=.1,stall_s=.35,call_s=10,files=512,load_s=20)
        if mode=="end_files":
            native.LIMITS.update(files=8,poll_s=.6)
        if mode=="exit_between_polls":
            native.LIMITS.update(poll_s=1,call_s=.25,stall_s=10)
        def device_probe(*args,**kwargs):
            if mode=="exit_between_polls" and (folder/"phase").is_file():
                (folder/"seen").touch()
            return {}
        native.device_check=device_probe
        lease={"lease_id":"review-cpu-test","end_utc":(datetime.now(timezone.utc)+
               timedelta(seconds=.6 if mode=="expires" else 30)).isoformat()}
        args=[str(native.PYTHON),"-B","-u","-c",WORKER,str(folder),mode]
        start=time.monotonic()
        try:
            native.supervise(arm,args,lease,start)
            outcome="finished"
        except Exception as exc:
            outcome=f"{type(exc).__name__}: {exc}"
        result={"scenario":mode,"arm":arm,"outcome":outcome,"elapsed_s":round(time.monotonic()-start,3),
                "partial_inventory_count":len(native.partial_inventory()),
                "stderr_bytes":(folder/"stderr.log").stat().st_size}
        results.append(result)
    print(json.dumps(results,indent=2))


if __name__=="__main__":
    main(Path(sys.argv[1]),Path(sys.argv[2]))
