"""Serial untouched/observed supervisor. No torch import until an admitted child."""
import contextlib
import dis
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from timing import NS, mark, read_timing, timeline
from bindings import resolve
from capture import digest
from native_observer import PINNED_BYTES

DIR=Path(__file__).resolve().parent
REPO=DIR.parents[2]
BASE="d497bae7db42589bd2ede512f932b0488f6309cd"
Q0="9e73ef86600b5e16f74b056676a6d3a4f1474058"
ARCH="f5e68668a5999a12ba399eb0f5103ffa835e4b30"
HIST="docs/coordination/WP-0005/gpu-reviewer-release/author-run-snapshot/evidence/"
UUID="GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"
ROOT=Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005")
MODEL=ROOT/"models/Unlimited_OCR_2_04809669"
PYTHON=ROOT/"venv/Scripts/python.exe"
SPEED=Path("C:/Users/jackg/eLedgerCare-Speed")
OUT=SPEED/"WP-0043/author/stock-run-01"
GIT=Path("C:/Program Files/Git/cmd/git.exe")
SMI=Path("C:/Windows/System32/nvidia-smi.exe")
SCHEME="wp43-native/1"
ARM=("untouched","observed")
LABELS=("F01.warmup","F07.warmup","F01.warm1","F07.warm1")
MIB=1<<20
LIMITS={"allocator_bytes":10<<30,"device_free_initial":11<<30,"device_free_during":2<<30,
        "host_job_commit":15<<30,"pinned_host_pool":PINNED_BYTES,"output_bytes":2560*MIB,
        "disk_free_initial":4<<30,"disk_free_during":1<<30,"files":512,"log_bytes":32*MIB,
        "wall_s":7200,"load_s":900,"call_s":1200,"stall_s":360,"poll_s":1}
RELEASE="docs/coordination/WP-0043/device-release.json"
ACTIVE_RUNTIME={"torch/lib/cudart64_13.dll":"58c509047f9dd1879cf82c6d5375a95c02c7bd295ae6c8362c745c936e2afc31",
                "torch/cuda/streams.py":"44762c1ec5b741b6430812e37fcc7364c6a5556834caa6ba2f15b1154fad699d"}
WHEELS="docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/02-verify-wheelhouse.json"


def git(*args):
    return subprocess.check_output([str(GIT),"-c","safe.directory="+str(REPO).replace(chr(92),"/"),"-C",str(REPO),*args],stderr=subprocess.DEVNULL)


def blob(ref,path):
    return git("show",ref+":"+path)


def protocol():
    return json.loads(blob(Q0,"qualification/q0/harness/protocol.json"))


def hash_file(path,check=None):
    with path.open("rb") as f:
        if check is None:
            return hashlib.file_digest(f,"sha256").hexdigest()
        sha=hashlib.sha256()
        while True:
            check()
            chunk=f.read(8*MIB)
            if not chunk:
                return sha.hexdigest()
            sha.update(chunk)


def bytes_json(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf8")


def write_new(path,obj):
    data=bytes_json(obj)
    if len(data)>16*MIB or path.name=="outcome.json" and len(data)>MIB:
        raise RuntimeError("bounded JSON receipt size")
    with path.open("xb") as f:
        f.write(data)


def plan():
    sites=resolve(MODEL)
    argv=[str(PYTHON),"-B","-u",str(DIR/"stock.py"),"run"]
    children=[[str(PYTHON),"-B","-u",str(DIR/"native.py"),"_worker",a] for a in ARM]
    return {"schema":SCHEME,"argv":argv,"worker_argv":children,"cwd":str(REPO),"output":str(OUT),
            "uuid":UUID,"q0":Q0,"model_revision":"0480966938291445591f69f08a13b041c073a96a",
            "model":str(MODEL),"python":str(PYTHON),"limits":LIMITS,"arms":list(ARM),
            "prehistory":list(LABELS),"fixtures":protocol()["fixtures"],"input_options":protocol()["call"],
            "cuts":{c.co_qualname:o for c,o in sites.items()},
            "guard_returns":{c.co_qualname:[i.offset for i in dis.get_instructions(c)
            if i.opname in ("RETURN_VALUE","RETURN_CONST")] for c in sites
            if c.co_name in ("_uocr_no_repeat_ngram","_uocr_page_count_guard")}}


def admission():
    # Coordinator publication is read from the coordinator-owned branch, never accepted from a caller argument.
    release=json.loads(blob("refs/heads/coordination/bootstrap",RELEASE))
    expected=plan()
    if release["plan_sha256"]!=digest(bytes_json(expected)) or release["owner"]!="eld-coordinator":
        raise RuntimeError("coordinator plan binding absent")
    rev=release["candidate"]
    if git("rev-parse",rev+":docs/research/WP-0043")!=git("rev-parse","HEAD:docs/research/WP-0043"):
        raise RuntimeError("source differs from admitted tree")
    if git("status","--porcelain","--",str(DIR)):
        raise RuntimeError("dirty candidate")
    if not release.get("review_accepted") or not release.get("lease_id") or release["uuid"]!=UUID:
        raise RuntimeError("independent review and sole lease required")
    git("cat-file","-e",release["review_commit"]+"^{commit}")
    now=dt.datetime.now(dt.timezone.utc)
    if not dt.datetime.fromisoformat(release["start_utc"])<=now<dt.datetime.fromisoformat(release["end_utc"]):
        raise RuntimeError("stock lease outside current interval")
    if not release.get("observed_ownership") or not isinstance(release["allowed_resident_pids"],list):
        raise RuntimeError("observed ownership and exact resident process list required")
    if Path(sys.executable).resolve()!=PYTHON.resolve():
        raise RuntimeError("incorrect Python")
    if bool(set(release["allowed_resident_pids"])-{i for i in release["allowed_resident_pids"] if type(i)==int and i>0}):
        raise RuntimeError("invalid resident process inventory")
    return release


def validate_files(check):
    if hash_file(PYTHON)!="0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14":
        raise RuntimeError("venv executable")
    source=json.loads(blob(BASE,"docs/research/WP-0041/source.json"))
    if hash_file(Path(sys._base_executable))!=source["python_sha256"]:
        raise RuntimeError("base Python")
    wheels=json.loads(blob(BASE,WHEELS))["wheels"]
    for item in wheels:
        if hash_file(ROOT/"wheelhouse"/item["wheel"],check)!=item["sha256"]:
            raise RuntimeError("wheel: "+item["wheel"])
    for name,item in source["files"].items():
        if hash_file(MODEL/name,check)!=item["sha256"]:
            raise RuntimeError("model object: "+name)
    return {"n_model":len(source["files"]),"wheels":len(wheels),"source":source}


def smi(args):
    p=subprocess.run([str(SMI),"--id="+UUID,*args,"--format=csv,noheader,nounits"],
                     text=True,capture_output=True,timeout=12,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    return p.stdout.strip()


def device_check(release,owned=(),initial=False):
    fields=smi(["--query-gpu=uuid,driver_version,memory.free"]).split(",")
    if len(fields)!=3 or fields[0].strip()!=UUID or fields[1].strip()!=release["driver_version"]:
        raise RuntimeError("device identity/driver")
    floor=LIMITS["device_free_initial" if initial else "device_free_during"]
    if int(fields[2].strip())*MIB<floor:
        raise RuntimeError("device free reserve")
    pids={int(x.strip()) for x in smi(["--query-compute-apps=pid"]).splitlines() if x.strip()}
    if pids-set(owned)-set(release["allowed_resident_pids"]):
        raise RuntimeError("unbound device process")
    return {"pids":sorted(pids),"free":int(fields[2])*MIB}


def inventory():
    files=[p for p in OUT.rglob("*") if p.is_file()]
    return len(files),sum(p.stat().st_size for p in files)


def final_limits(start,release):
    n,size=inventory()
    logs=sum(p.stat().st_size for p in OUT.rglob("*.log"))
    device=device_check(release)
    if (n+1>LIMITS["files"] or size+MIB>LIMITS["output_bytes"] or logs>LIMITS["log_bytes"] or
        shutil.disk_usage(OUT).free-MIB<LIMITS["disk_free_during"] or time.monotonic()-start>LIMITS["wall_s"]
        or dt.datetime.now(dt.timezone.utc)>=dt.datetime.fromisoformat(release["end_utc"])):
        raise RuntimeError("final resource/lease check")
    return {"files":n,"bytes":size,"logs":logs,"elapsed_s":time.monotonic()-start,"device":device}


def partial_inventory():
    # Bound the exception path even if an external writer violated the output lease.
    result={}
    total=0
    for p in OUT.rglob("*"):
        if not p.is_file():
            continue
        if len(result)>=LIMITS["files"] or total+p.stat().st_size>LIMITS["output_bytes"]:
            break
        total+=p.stat().st_size
        result[p.relative_to(OUT).as_posix()]=hash_file(p)
    return result


def env_for(out):
    env={k:os.environ[k] for k in ("SystemRoot","windir","OS","ComSpec","NUMBER_OF_PROCESSORS",
                                    "PROCESSOR_ARCHITECTURE","PATHEXT") if k in os.environ}
    env.update(PATH=str(PYTHON.parent)+";C:\\Windows\\System32;C:\\Windows",
               TEMP=str(out/"tmp"),TMP=str(out/"tmp"),HOME=str(out/"home"),USERPROFILE=str(out/"home"),
               HF_HOME=str(out/"hf"),HF_MODULES_CACHE=str(out/"modules"),HF_HUB_OFFLINE="1",
               TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1",HF_HUB_DISABLE_XET="1",
               CUDA_DEVICE_ORDER="PCI_BUS_ID",CUDA_VISIBLE_DEVICES=UUID,CUDA_CACHE_PATH=str(out/"cuda"),
               TORCH_HOME=str(out/"torch"),TORCHINDUCTOR_CACHE_DIR=str(out/"inductor"),PIP_NO_INDEX="1",
               XDG_CACHE_HOME=str(out/"xdg"),PYTHONDONTWRITEBYTECODE="1",PYTHONNOUSERSITE="1",
               PYTHONHASHSEED="0",PYTHONUTF8="1",PYTHONIOENCODING="utf-8",PYTHONUNBUFFERED="1")
    for name in ("tmp","home"):
        (out/name).mkdir()
    return env


def supervise(arm,argv,release,start):
    from limits import job,job_member
    import psutil
    folder=OUT/arm
    folder.mkdir()
    device_check(release,initial=True)
    with (folder/"stdout.log").open("xb") as stdout,(folder/"stderr.log").open("xb") as stderr:
        origin=time.monotonic_ns()
        proc=subprocess.Popen(argv,cwd=REPO,env=env_for(folder),stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,
                              creationflags=subprocess.CREATE_NO_WINDOW|4)
        try:
            with job(proc,LIMITS["host_job_commit"]) as job_handle:
                proc.stdin.write(bytes_json({"parent":os.getpid(),"lease":release["lease_id"]})+b"\n")
                proc.stdin.close()
                def deadline():
                    data=read_timing(folder)
                    return timeline(data,arm,LABELS,LIMITS,origin,time.monotonic_ns())

                while proc.poll() is None:
                    deadline()
                    count,used=inventory()
                    logsize=(folder/"stdout.log").stat().st_size+(folder/"stderr.log").stat().st_size
                    try:
                        owned={proc.pid,*[p.pid for p in psutil.Process(proc.pid).children(recursive=True)]}
                        if not all(job_member(pid,job_handle) for pid in owned):
                            raise RuntimeError("worker escaped bound Windows Job")
                    except (OSError,psutil.NoSuchProcess):
                        if proc.poll() is not None:
                            break
                        raise
                    device_check(release,owned)
                    if (used+MIB>LIMITS["output_bytes"] or count+1>LIMITS["files"] or
                        logsize>LIMITS["log_bytes"] or shutil.disk_usage(OUT).free<LIMITS["disk_free_during"]):
                        raise RuntimeError("supervisor disk/log ceiling")
                    until=min((deadline()-time.monotonic_ns())/NS,
                              start+LIMITS["wall_s"]-time.monotonic(),
                              (dt.datetime.fromisoformat(release["end_utc"])-dt.datetime.now(dt.timezone.utc)).total_seconds())
                    if until<=0:
                        raise RuntimeError("supervisor wall/phase/lease deadline")
                    try:
                        proc.wait(timeout=min(LIMITS["poll_s"],until))
                    except subprocess.TimeoutExpired:
                        pass
                exited=time.monotonic_ns()
                if proc.returncode:
                    raise RuntimeError(f"{arm} exit {proc.returncode}")
                timeline(read_timing(folder),arm,LABELS,LIMITS,origin,exited,finished=True)
                final_limits(start,release)
                return {"origin_ns":origin,"exit_check_ns":exited}
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=20)


def run():
    from limits import device_lock
    release=admission()
    if OUT.exists() or shutil.disk_usage(OUT.parent).free<LIMITS["disk_free_initial"]:
        raise RuntimeError("fresh resource directory and initial disk headroom required")
    start=time.monotonic()
    with device_lock(SPEED/(UUID+".lock")):
        initial=device_check(release,initial=True)
        OUT.mkdir()
        try:
            def preflight_guard():
                if (time.monotonic()-start>LIMITS["load_s"] or dt.datetime.now(dt.timezone.utc)>=dt.datetime.fromisoformat(release["end_utc"])
                    or shutil.disk_usage(OUT).free<LIMITS["disk_free_during"]):
                    raise RuntimeError("parent preflight deadline/lease/disk")
            receipt=validate_files(preflight_guard)
            preflight_guard()
            write_new(OUT/"admission.json",{"release":release,"plan":plan(),"initial_device":initial,"n_model":receipt["n_model"],"wheels":receipt["wheels"]})
            timing={}
            for arm,argv in zip(ARM,plan()["worker_argv"],strict=True):
                timing[arm]=supervise(arm,argv,release,start)
            files=partial_inventory()
            stats=final_limits(start,release)
            if len(files)!=stats["files"]:
                raise RuntimeError("incomplete bounded outcome inventory")
            outcome={"status":"finished","timing":timing,"final_resources":stats,"files":files}
        except BaseException as exc:
            outcome={"status":"partial","reason":str(exc),"files":partial_inventory()}
            write_new(OUT/"outcome.json",outcome)
            raise
        write_new(OUT/"outcome.json",outcome)
        return outcome


def render(fixture):
    import pypdfium2
    raw=blob(Q0,fixture["path"])
    if digest(raw)!=fixture["sha256"]:
        raise ValueError("fixture PDF")
    images=[]
    with pypdfium2.PdfDocument(raw) as pdf:
        for page,want in zip(pdf,fixture["raster"],strict=True):
            try:
                bitmap=page.render(scale=300.0/72.0)
                try:
                    image=bitmap.to_pil().convert("RGB")
                finally:
                    bitmap.close()
            finally:
                page.close()
            if image.size!=(want["width"],want["height"]) or digest(image.tobytes())!=want["rgb_sha256"]:
                raise ValueError("rendered page")
            images.append(image)
    return images


def worker(arm):
    if arm not in ARM:
        raise RuntimeError("unknown arm")
    message=json.loads(sys.stdin.buffer.readline(512))
    release=admission()
    import psutil
    ancestors={p.pid for p in psutil.Process().parents()}
    if (message.get("parent") not in ancestors or message.get("lease")!=release["lease_id"]
        or not psutil.Process(message["parent"]).cmdline()[-2:]==[str(DIR/"stock.py"),"run"]):
        raise RuntimeError("supervised child handshake required")
    out=OUT/arm
    if os.environ.get("CUDA_VISIBLE_DEVICES")!=UUID or os.environ.get("HF_HUB_OFFLINE")!="1":
        raise RuntimeError("child environment")
    import importlib.metadata as md
    import importlib.util as util
    source=json.loads(blob(BASE,"docs/research/WP-0041/source.json"))
    for name,version in source["versions"]["verified_pinned_distributions"].items():
        if md.version(name)!=version:
            raise RuntimeError("distribution: "+name)
    if util.find_spec("triton") is not None:
        raise RuntimeError("Triton differs from Q0")
    for name,sha in {**source["versions"]["runtime_source_sha256"],**ACTIVE_RUNTIME}.items():
        if hash_file(ROOT/"venv/Lib/site-packages"/name)!=sha:
            raise RuntimeError("runtime source: "+name)
    import torch
    from transformers import AutoModel,AutoTokenizer
    if torch.cuda.device_count()!=1 or str(torch.cuda.get_device_properties(0).uuid).removeprefix("GPU-")!=UUID[4:]:
        raise RuntimeError("visible CUDA device")
    torch.cuda.set_per_process_memory_fraction(LIMITS["allocator_bytes"]/torch.cuda.get_device_properties(0).total_memory)
    options=protocol()
    images={f["family_id"]:render(f) for f in options["fixtures"]}
    mark(out,"load")
    tok=AutoTokenizer.from_pretrained(str(MODEL),local_files_only=True,trust_remote_code=True)
    model=AutoModel.from_pretrained(str(MODEL),local_files_only=True,trust_remote_code=True,
                                    use_safetensors=True,torch_dtype=torch.bfloat16).eval().cuda()
    torch.cuda.current_stream().synchronize()
    package=type(model).__module__.rsplit(".",1)[0]
    if any(m.training for m in model.modules()) or any(getattr(m,"ep_size",1)!=1 for m in model.modules()):
        raise RuntimeError("unqualified training or distributed writer")
    origins={}
    for obj in sys.modules.copy().values():
        name=getattr(obj,"__name__","")
        if isinstance(name,str) and name.startswith(package+"."):
            file=Path(obj.__file__).resolve()
            if not file.is_relative_to((out/"modules").resolve()) or hash_file(file)!=source["files"][file.name]["sha256"]:
                raise RuntimeError("dynamic origin: "+name)
            origins[name]={"path":str(file),"sha256":hash_file(file)}
    write_new(out/"runtime.json",{"pid":os.getpid(),"parent":message["parent"],"receivers":{"generator":id(model),"decoder":id(model.model),"layer11":id(model.model.layers[11])},"argv":sys.orig_argv,"arm":arm,"schema":SCHEME,"uuid":UUID,"active_runtime":ACTIVE_RUNTIME,"modules":origins,"eval":not model.training,"device":str(torch.cuda.get_device_properties(0)),
             "allocator_limit":LIMITS["allocator_bytes"],"cuda":torch.version.cuda,"torch":str(torch.__version__),
             "deterministic":torch.are_deterministic_algorithms_enabled(),"tf32":torch.backends.cuda.matmul.allow_tf32,
             "cudnn_tf32":torch.backends.cudnn.allow_tf32,"autocast":torch.is_autocast_enabled(),
             "training_modules":[n for n,m in model.named_modules() if m.training]})
    from native_observer import StockObserver
    obs=StockObserver(torch,model,MODEL,out) if arm=="observed" else None
    try:
        for i,label in enumerate(LABELS):
            family=label[:3]
            pages=images[family]
            kwargs={**options["call"]["fixed_kwargs"],"max_new_tokens":8000*len(pages),
                    "ngram_window":128 if len(pages)==1 else 1024}
            mark(out,label)
            with obs.monitor if obs and i==3 else contextlib.nullcontext():
                result=model.infer(tok,prompt=options["call"]["prompt"],image_file=list(pages),return_dict=True,**kwargs)
            torch.cuda.current_stream().synchronize()
            document={k:v for k,v in result.items() if k not in {"time","prefill_time"}}
            document["ids"]=document.pop("token_ids")
            document["terminal"]=document.pop("finish_reason")
            document.update(output_tokens=len(document["ids"]),markers=[j for j,x in enumerate(document["ids"]) if x==128827])
            write_new(out/(label+".json"),{"call":i,"family":family,"kwargs":kwargs,"document":document,
                    "peak_allocated":torch.cuda.max_memory_allocated(),"peak_reserved":torch.cuda.max_memory_reserved()})
            if torch.cuda.max_memory_reserved()>LIMITS["allocator_bytes"]:
                raise RuntimeError("device allocator high-water")
    finally:
        if obs:
            obs.close()
    mark(out,"finished")


if __name__=="__main__":
    if sys.argv[1:2]!=["_worker"] or len(sys.argv)!=3:
        raise SystemExit("use stock.py")
    worker(sys.argv[2])
