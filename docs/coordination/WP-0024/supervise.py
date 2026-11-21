"""Run one bound CPU-supervised B=1 sensor phase underneath the coordinator's Windows job."""
from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"docs/research/WP-0014/eld-latency-author"))
from probe import isolated_env


def main(plan_path, digest):
    raw=plan_path.read_bytes()
    if sha256(raw).hexdigest()!=digest:
        raise ValueError("Plan changed")
    plan=json.loads(raw)
    out=Path(plan["output"]).resolve()
    if out.parent!=Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024/review/runs") or Path.cwd()!=ROOT:
        raise ValueError("Unbound execution or output path")
    out.mkdir(parents=True,exist_ok=False)
    folder=out/"sensor"
    env=isolated_env(folder)
    env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONIOENCODING="utf8")
    for key,subpath in (("LOCALAPPDATA","app/local"),("APPDATA","app/roaming"),("PYTHONPYCACHEPREFIX","pycache"),
                        ("TRITON_HOME","triton-home"),("TORCH_EXTENSIONS_DIR","extensions"),("MPLCONFIGDIR","mpl"),
                        ("NUMBA_CACHE_DIR","numba")):
        p=folder/"cache"/subpath
        p.mkdir(parents=True,exist_ok=True)
        env[key]=str(p)
    cmd=[sys.executable,"-I","-B",str(ROOT/"docs/research/WP-0024/sensor/run_sensor.py"),str(plan_path),digest]
    start=time.time_ns()
    with (out/"stdout.txt").open("xb") as stdout,(out/"stderr.txt").open("xb") as stderr:
        proc=subprocess.run(cmd,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
    info={"all_segments_completed":proc.returncode==0,"segments":[{"returncode":proc.returncode,"argv":cmd,
          "start_utc_ns":start,"end_utc_ns":time.time_ns(),"plan_sha256":digest,"candidate":plan["candidate"]}]}
    with (out/"process.json").open("x",encoding="utf8",newline="\n") as f:
        json.dump(info,f,indent=2)
        f.write("\n")
    return proc.returncode


if __name__=="__main__":
    sys.exit(main(Path(sys.argv[1]),sys.argv[2]))
