"""Bounded disposable WP-0014 scheduling trial. Execute from its assigned worktree on Windows."""
import argparse
import contextlib
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from threading import Thread

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT / ".local/wp0014"
Q0 = Path.home() / "eLedgerCare-Q0/WP-0005"
GPU = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"
AUTHOR = "4ade03ee00e9701241770523d5df60df27da4b0c"
HASH = {"A":"25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858",
        "B":"ef5d8f09658355dae46d54724a8cbeb89bc625362e41e8c4e154461d81a604c8",
        "W":"74d2847bed7ea768c80a25383de12c5ea9d3d4c08afb7ddc75a783e77a73dd28"}
PSQL = ROOT / ".local/tools/pgsql-18.7-1/bin/psql.exe"
CFG = json.loads((ROOT / ".local/secrets/pg-local.json").read_text())
assert ROOT.name == "eld-latency-scheduling" and CFG["host"] == "127.0.0.1" and CFG["port"] == 55464
NOW = lambda: time.time_ns()/1e6


def execute(command, **kwargs):
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, **kwargs).stdout


def sql(db, statement):
    env = {**os.environ, "PGPASSWORD":CFG["adminPassword"]}
    return execute([PSQL,"-XqAt", "-v","ON_ERROR_STOP=1","-h",CFG["host"],"-p",str(CFG["port"]),
                    "-U",CFG["adminUser"],"-d",db,"-f","-"],input=statement.encode(),env=env).decode().strip()


def prepare_worker(target):
    shutil.copytree(ROOT/"workers/local_ocr",target,ignore=shutil.ignore_patterns("__pycache__","tests"))
    shutil.copyfile(HERE/"bridge.py", target/"run_worker.py")
    for script in ("resident.py","pins.py"):
        shutil.copyfile(HERE/script, target/"local_ocr"/script)
    worker = target/"local_ocr/worker.py"
    content = worker.read_text()
    for old,new in [('output_dir / "heartbeat.json"', 'output_dir / "resident-heartbeat.json"'),
                    ('run_dir=run_dir,\n            readonly_q0_root=readonly_q0,',
                     'run_dir=writable_root / "runs/warmup",\n            readonly_q0_root=readonly_q0,'),
                    ('model_dir = normalize_and_verify_model_dir(', 'model_dir = rt.verified_dir('),
                    ('        write_exclusive_bytes(raw_output_path, raw_utf8)', '        rt.pins.check()\n        write_exclusive_bytes(raw_output_path, raw_utf8)')]:
        assert content.count(old)==1
        content=content.replace(old,new)
    worker.write_text(content,encoding="utf8")


def env_for_engine(root):
    win = os.environ["SystemRoot"]
    env = {k:os.environ[k] for k in ("SystemRoot","windir","NUMBER_OF_PROCESSORS","PROCESSOR_ARCHITECTURE","OS","PATHEXT","ComSpec") if k in os.environ}
    env.update({"PATH":os.pathsep.join([str(Q0/"venv/Scripts"),str(Path(win)/"System32"),win]),
                "VIRTUAL_ENV":str(Q0/"venv"),"CUDA_VISIBLE_DEVICES":GPU,"CUDA_DEVICE_ORDER":"PCI_BUS_ID",
                "HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_HUB_DISABLE_XET":"1","HF_HUB_DISABLE_TELEMETRY":"1",
                "HF_HUB_DISABLE_PROGRESS_BARS":"1","PIP_NO_INDEX":"1","PIP_CONFIG_FILE":"NUL"})
    for keys,sub in [("TEMP TMP TMPDIR","tmp"),("USERPROFILE HOME","home"),("HF_HOME","hf"),
                     ("HF_HUB_CACHE HUGGINGFACE_HUB_CACHE","hf/hub"),("TRANSFORMERS_CACHE","hf/transformers"),
                     ("HF_MODULES_CACHE","modules"),("TORCH_HOME","torch"),("TRITON_CACHE_DIR","triton"),
                     ("TORCHINDUCTOR_CACHE_DIR","inductor"),("CUDA_CACHE_PATH","cuda"),("XDG_CACHE_HOME","xdg"),
                     ("PIP_CACHE_DIR","pip"),("UV_CACHE_DIR","uv")]:
        folder=root/"runs/warmup/cache"/sub
        folder.mkdir(parents=True,exist_ok=True)
        for key in keys.split():
            env[key]=str(folder)
    return env


def begin(cmd, folder, role, env):
    log=(folder/(role+".log")).open("wb")
    try:
        p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    finally:
        log.close()
    return p


def end(p):
    if p and p.poll() is None:
        subprocess.run(["taskkill","/T","/F","/PID",str(p.pid)],capture_output=True)
        p.wait(timeout=15)


def occupancy():
    return execute(["nvidia-smi","--query-gpu=uuid,memory.used,memory.free,utilization.gpu","--format=csv,noheader,nounits"]).decode().strip()


def compute_processes():
    # WDDM reports desktop graphics clients here. Root separately confirms sole ownership.
    desktop = set("applicationframehost chrome copilotapp copilotapphost crossdeviceresume devenv explorer msedge msedgewebview2 notepad protondrive searchhost shellexperiencehost shellhost startmenuexperiencehost steam steamwebhelper systemsettings textinputhost windowsterminal".split())
    rows = execute(["nvidia-smi","--query-compute-apps=pid,process_name","--format=csv,noheader"]).decode().splitlines()
    return [(int(pid),Path(exe).name) for row in rows for pid,exe in [row.split(", ",1)] if Path(exe).stem.lower() not in desktop]


def run_phase(session,worker,files,mode,cpu,deadline,replay=False):
    db="eledgercare_wp0014_sched" + ("_cpu" if cpu or replay else "")
    root=session/mode
    ctl=root/"control"
    ctl.mkdir(parents=True)
    (root/"runs/warmup/input").mkdir(parents=True)
    shutil.copyfile(HERE/"W.pdf",root/"runs/warmup/input/document.pdf")
    inputs=["A","B"] if mode in ("immediate","ready") else ["A"]
    cfg={"mode":mode,"cpu_crash":cpu,"q0":str(Q0),"gpu":GPU,"inputs":inputs,
         "files":{k:str(v) for k,v in files.items()},"hashes":HASH}
    (root/"config.json").write_text(json.dumps(cfg))
    def log(event,**fields):
        with (root/"manager.jsonl").open("a") as f:
            print(json.dumps({"event":event,"t_ms":NOW(),**fields}), file=f)
    env={**os.environ,"ConnectionStrings__Runtime":f"Host=127.0.0.1;Port=55464;Database={db};Username={CFG['appUser']};Password={CFG['appPassword']}",
         "Api__Port":"5814","LocalOcr__Enabled":"true","LocalOcr__WorkerRootPath":str(ROOT/"workers/local_ocr" if mode=="stock" and not replay else worker),
         "LocalOcr__ReadOnlyQ0Root":str(Q0),"LocalOcr__WritableRuntimeRoot":str(root),"LocalOcr__LeasedGpuUuid":GPU}
    api=browser=engine=None
    observed=set()
    try:
        api=begin(["dotnet",ROOT/"src/ELedgerCare.Api/bin/Release/net10.0/ELedgerCare.Api.dll"],root,"api",env)
        for _ in range(200):
            try:
                with socket.create_connection(("127.0.0.1",5814),timeout=.1):break
            except OSError:time.sleep(.05)
        assert api.poll() is None
        browser=begin(["node",HERE/"browser.mjs",root], root,"browser",os.environ)
        idle_probed=False
        while browser.poll() is None:
            if time.monotonic()>deadline:
                raise TimeoutError("global budget reached")
            signals=set(p.name for p in ctl.glob("prepare.*"))
            for signal in sorted(signals-observed):
                log("prepare_signal",signal=signal,engine_already_started=engine is not None or bool(observed))
                observed.add(signal)
            jobs=list(ctl.glob("*.job"))
            if (signals or jobs) and engine is None:
                log("launch_requested",reason="intake_visible" if signals else "claimed_job")
                engine=begin([Q0/"venv/Scripts/python.exe","-I","-B","-X","utf8","-u",worker/"local_ocr/resident.py",root],
                             root,"engine",env_for_engine(root))
                log("spawned",launcher_pid=engine.pid)
            if engine and engine.poll() is not None and not (ctl/"engine.dead").exists():
                (ctl/"engine.dead").write_text(str(engine.returncode))
                log("crash",code=engine.returncode)
            # Exercise the shutdown guard during a pending/running job, once.
            if jobs and not idle_probed and engine and engine.poll() is None:
                idle_probed=True
                retire_if_idle(ctl,inputs,log)
            time.sleep(.018)
        if browser.returncode:
            raise RuntimeError(f"{mode} browser failed: {browser.returncode}")
        if cpu:
            assert engine.wait(5)==37 and not (ctl/"ready").exists()
        elif mode != "stock":
            assert retire_if_idle(ctl,inputs,log)
            assert engine.wait(20)==0
        log("phase_complete",engine_exit=engine.returncode if engine else None)
    finally:
        end(browser)
        end(engine)
        end(api)


def retire_if_idle(ctl, inputs, log):
    if len(list(ctl.glob("*.done"))) != len(inputs):
        log("idle_stop_refused", submitted=len(list(ctl.glob("*.job"))), completed=len(list(ctl.glob("*.done"))))
        return False
    (ctl/"retire").touch()
    log("idle_stop_allowed")
    return True


def check_ports(ports):
    for port in ports:
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
            sock.bind(("127.0.0.1",port))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=["cpu-crash","live"],required=True)
    parser.add_argument("--id",required=True)
    parser.add_argument("--frozen-head")
    parser.add_argument("--lease")
    args=parser.parse_args()
    cpu=args.mode=="cpu-crash"
    assert args.id.isalnum() and len(args.id)<40
    head=execute(["git","rev-parse","HEAD"]).decode().strip()
    if not cpu:
        assert args.frozen_head == head and args.lease and not execute(["git","status","--porcelain"])
        assert not compute_processes(), "Unexpected GPU client before release"
        pre=occupancy().split(", ")
        assert pre[0]==GPU and int(pre[2])>=10000 and shutil.disk_usage(ROOT).free>=20*1024**3
    check_ports([5814,4814])
    session=WORK/args.id
    session.mkdir(parents=True)
    db="eledgercare_wp0014_sched"+("_cpu" if cpu else "")
    assert Path(sql(db,"SHOW data_directory")).resolve() == (ROOT/".local/postgres-data").resolve()
    assert sql(db,"SHOW track_commit_timestamp")=="on"
    sql(db,(HERE/"trace.sql").read_text())
    if not cpu: assert sql(db,"SELECT count(*) FROM eledgercare.processing_jobs")=="0"
    files={}
    for key in ("A","B"):
        pdf=session/(key+".pdf")
        pdf.write_bytes(execute(["git","show",AUTHOR+":docs/research/WP-0014/eld-latency-author/"+key+".pdf"]))
        assert hashlib.sha256(pdf.read_bytes()).hexdigest()==HASH[key]
        files[key]=pdf
    assert hashlib.sha256((HERE/"W.pdf").read_bytes()).hexdigest()==HASH["W"]
    worker=session/"worker"
    prepare_worker(worker)
    ui=begin(["node",HERE/"ui.mjs"],session,"ui",os.environ)
    stop=False
    def sample():
        while not stop:
            try:
                with (session/"gpu.jsonl").open("a") as f:
                    print(json.dumps({"t_ms":NOW(),"device":occupancy(),"compute":compute_processes()}),file=f)
            except Exception as exc:
                print(type(exc).__name__,file=sys.stderr)
            time.sleep(.65)
    observer=Thread(target=sample,daemon=True)
    if not cpu: observer.start()
    try:
        deadline=time.monotonic()+840
        for mode in (["demand"] if cpu else ["stock","demandfirst","demand","immediate","ready"]):
            run_phase(session,worker,files,mode,cpu,deadline)
    finally:
        end(ui)
        stop=True
        if not cpu: observer.join(5)
        extract="""SELECT coalesce(json_agg(row_to_json(e) ORDER BY e.commit_ms),'[]') FROM
            (SELECT document_id,status,queued,active,extract(epoch FROM recorded)*1000 AS trigger_ms,
             extract(epoch FROM pg_xact_commit_timestamp(xmin))*1000 AS commit_ms FROM wp0014.events) e;"""
        (session/"database.json").write_text(sql(db,extract))
        attempts_sql="""SELECT json_agg(row_to_json(a) ORDER BY started_at) FROM
         (SELECT document_id, job_id, attempt_id, started_at, ended_at, status, launcher_pid, launcher_create_filetime,
          worker_pid,worker_create_filetime, failure_code FROM eledgercare.execution_attempts) a"""
        (session/"attempts.json").write_text(sql(db,attempts_sql) or "[]")
        (session/"run.json").write_text(json.dumps({"head":head,"author":AUTHOR,"lease":args.lease,"cpu":cpu,
            "db":db,"api_port":5814,"ui_port":4814,"db_port":55464,"hashes":HASH,
            "ended_ms":NOW(),"device_after":None if cpu else occupancy()}))
        check_ports([4814,5814])


if __name__=="__main__":
    main()
