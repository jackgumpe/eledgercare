"""Exercise the real supervisor on a harmless Python worker with simulated device telemetry."""
import datetime as dt
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

import native

CHILD="""
from pathlib import Path
import sys,time
sys.path.insert(0,sys.argv[1])
from timing import mark
sys.stdin.readline()
folder=Path(sys.argv[2])
mark(folder,"load")
for i,phase in enumerate(("F01.warmup","F07.warmup","F01.warm1","F07.warm1")):
    mark(folder,phase)
    if i==0:
        time.sleep(float(sys.argv[3]))
mark(folder,"finished")
"""


def exercise(dest):
    dest.mkdir(exist_ok=False)
    limits={**native.LIMITS,"poll_s":1,"load_s":5,"call_s":0.25,"stall_s":0.25,
            "host_job_commit":512<<20,"disk_free_during":32<<20}
    release={"lease_id":"cpu-control","end_utc":(dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=2)).isoformat()}
    results=[]
    for name,delay in (("inside",0.02),("completed_between_polls",0.45),("still_running",2.5)):
        out=dest/name
        out.mkdir()
        argv=[str(native.PYTHON),"-B","-u","-c",CHILD,str(native.DIR),str(out/"untouched"),str(delay)]
        start=time.monotonic()
        with patch.object(native,"OUT",out),patch.object(native,"LIMITS",limits),patch.object(native,"device_check",return_value={"test":True}):
            try:
                bounds=native.supervise("untouched",argv,release,start)
                result={"status":"finished","bounds":bounds}
            except (ValueError,RuntimeError) as exc:
                result={"status":"rejected","reason":str(exc)}
        phase=out/"untouched/phase"
        result.update(name=name,delay_s=delay,elapsed_s=time.monotonic()-start,
                      receipts=[json.loads(x) for x in phase.read_bytes().splitlines()] if phase.exists() else [])
        results.append(result)
    print(json.dumps(results))
    if (results[0]["status"]!="finished" or any(
        x["status"]!="rejected" or "deadline" not in x.get("reason","") for x in results[1:])):
        raise SystemExit(1)


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("one fresh CPU scratch directory is required")
    exercise(Path(sys.argv[1]).resolve())
