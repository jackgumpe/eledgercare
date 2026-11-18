"""Start one exact plan, contain its runtime and collect the timed process outcome."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WP14 = ROOT/"docs/research/WP-0014/eld-latency-author"
sys.path[:0] = [str(HERE),str(WP14)]
from formats import digest, publish
from probe import isolated_env
from cases import GPU, PYTHON

PACKET = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0015")
SCOPES = ("docs/research/WP-0015/astra","docs/research/WP-0014/eld-latency-author","workers/local_ocr")
SMI = Path(os.environ["SystemRoot"])/"System32/nvidia-smi.exe"


def git(*args):
    return subprocess.check_output(["git","-C",str(ROOT),*args],encoding="utf-8").strip()


def gpu_observation():
    cmd = [str(SMI),"--query-gpu=uuid,memory.free,memory.used,temperature.gpu,utilization.gpu,driver_version",
           "--format=csv,noheader,nounits","--id="+GPU]
    row = subprocess.check_output(cmd,encoding="utf-8",timeout=10).strip().split(", ")
    if row[0] != GPU:
        raise ValueError("wrong device")
    return dict(uuid=row[0],free_mib=int(row[1]),used_mib=int(row[2]),temperature_c=int(row[3]),
                utilization_percent=int(row[4]),driver=row[5])


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument("--source",required=True)
    p.add_argument("--plan",type=Path,required=True)
    p.add_argument("--sha256",required=True)
    p.add_argument("--owner",choices=["astra","review"],required=True)
    p.add_argument("--run",required=True)
    p.add_argument("--seconds",type=int,required=True)
    p.add_argument("--lease",required=True)
    p.add_argument("--min-vram-mib",type=int,default=12000)
    args=p.parse_args()
    if not re.fullmatch(r"[\w-]{1,64}",args.run) or not 1<=args.seconds<=10800:
        p.error("invalid run name or time budget")
    if not re.fullmatch(r"[a-f0-9]{40}",args.source):
        p.error("source must be a full commit")
    for scope in SCOPES:
        if git("rev-parse",args.source+":"+scope)!=git("rev-parse","HEAD:"+scope) or git("status","--porcelain","--",scope):
            raise ValueError("source differs from frozen revision: "+scope)
    data=args.plan.read_bytes()
    requests=json.loads(data)["requests"]
    if digest(data)!=args.sha256 or not requests:
        raise ValueError("plan digest or request list invalid")
    for r in requests:
        if (not re.fullmatch("[a-z0-9-]{1,28}",r["label"]) or r["mode"] not in ("native","windows")
                or not isinstance(r["warmup"],bool) or not 1<=r["pages"]<=60 or not re.fullmatch(r"[a-f0-9]{64}",r["sha256"])
                or not Path(r["pdf"]).is_absolute() or (r.get("rgb_sha256") and len(r["rgb_sha256"])!=r["pages"])):
            raise ValueError("invalid request")
    run=PACKET/args.owner/"runs"/args.run
    run.mkdir(parents=True,exist_ok=False)
    publish(run/"plan.json",data)
    live=any(r["mode"]=="native" for r in requests)
    start_state=gpu_observation() if live else None
    if shutil.disk_usage(run).free < 20*2**30 or (live and start_state["free_mib"] < args.min_vram_mib):
        raise ValueError("admission resource floor")
    env=isolated_env(run)
    cmd=[str(PYTHON),"-I","-B",str(HERE/"trial.py"),str(run)]
    begin=time.perf_counter()
    publish(run/"launch.json",dict(cmd=cmd,source=args.source,head=git("rev-parse","HEAD"),lease=args.lease,
                seconds=args.seconds,plan_sha256=args.sha256,initial_gpu=start_state,
                supervisor_pid=os.getpid(),start_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())))
    samples=[]
    with (run/"stdout.txt").open("xb") as out,(run/"stderr.txt").open("xb") as err:
        child=subprocess.Popen(cmd,cwd=run,env=env,stdout=out,stderr=err,stdin=subprocess.DEVNULL)
        reason=None
        try:
            while child.poll() is None:
                observed=time.perf_counter()-begin
                if observed>=args.seconds or shutil.disk_usage(run).free<20*2**30:
                    reason="time or disk floor";break
                if live and (not samples or observed-samples[-1]["s"]>=5):
                    samples.append(dict(s=observed,**gpu_observation()))
                time.sleep(.15)
        finally:
            if child.poll() is None:
                subprocess.run([str(Path(env["SystemRoot"])/"System32/taskkill.exe"),"/PID",str(child.pid),"/T","/F"],capture_output=True)
                child.wait(timeout=8)
            publish(run/"process.json",dict(pid=child.pid,returncode=child.returncode,elapsed_s=time.perf_counter()-begin,
                        reason=reason,gpu_samples=samples,end_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())))
    return int(reason is not None or child.returncode!=0)


if __name__=="__main__":
    sys.exit(main())
