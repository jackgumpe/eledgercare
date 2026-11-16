import sys,json,time,os
from pathlib import Path
sys.path.insert(0,'C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\eld-baseline-reviewer\\qualification\\baseline')
import winjob
a=sys.argv
run=Path(a[a.index("--run-dir")+1]);winjob.join(a[a.index("--job")+1])
(run/"heartbeat.json").write_text(json.dumps({"phase":"call:SYN-WO-01-v0-clean.warmup","phase_timeout_s":0.1,"stall_monitored":True,"progress":0,"pid":os.getpid()}))
time.sleep(30)
