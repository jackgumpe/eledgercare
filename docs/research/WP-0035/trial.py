"""Execute the bounded CPU trial on an explicitly released source SHA and fresh run directory."""
import datetime
import gzip
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
from admit35 import BASE, HASHES, HERE, ROOT, check_local, git, sha, sources

PACKET = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0035/author")
PYTHON = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0030/runtime/venv/Scripts/python.exe")
EXE_HASH = "0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14"
FLAGS = ("HF_HUB_OFFLINE","TRANSFORMERS_OFFLINE","HF_DATASETS_OFFLINE","PIP_NO_INDEX",
         "OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS")
CACHES = ("TEMP","TMP","TMPDIR","HF_HOME","TORCH_HOME","XDG_CACHE_HOME","TORCHINDUCTOR_CACHE_DIR","PIP_CACHE_DIR")

def write_json(folder, name, value, zipped=False):
    data = json.dumps(value,separators=(",",":"),ensure_ascii=True,sort_keys=True,allow_nan=False).encode()+b"\n"
    path = folder/(name+".json"+(".gz" if zipped else ""))
    with path.open("xb") as f:
        f.write(gzip.compress(data,compresslevel=7,mtime=0) if zipped else data)

def main(candidate,work):
    started = time.perf_counter()
    assert sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize and sys.byteorder=="little"
    assert Path(sys.executable).resolve()==PYTHON and sha(PYTHON.read_bytes())==EXE_HASH
    assert work.parent == PACKET and all(Path(os.environ[k]).resolve()==work/k for k in CACHES)
    assert all(os.environ[k]=="1" for k in FLAGS) and os.environ["CUDA_VISIBLE_DEVICES"]=="-1"
    assert git("rev-parse","HEAD").decode().strip() == candidate
    assert git("branch","--show-current").decode().strip()=="research/wp-0035-trajectory"
    assert not git("status","--porcelain=v1")
    for f in HERE.iterdir():
        if f.is_file():
            check_local(candidate, f.relative_to(ROOT).as_posix())
    import torch
    import numpy as np
    assert str(torch.__version__)=="2.13.0+cpu" and np.__version__=="2.2.6" and torch.version.cuda is None
    torch.set_num_interop_threads(1)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.default_generator.manual_seed(2401)
    assert torch.get_num_interop_threads()==torch.get_num_threads()==1 and torch.get_default_dtype()==torch.float32
    assert torch.get_default_device().type=="cpu"
    task_a, task_b, custody, bindings, historical, archived, controls = sources(work)
    import matrix
    import online
    from trajectory35 import Replay, cross_controls
    from measure35 import add_replay, parity_a, parity_b, symbolic, tables
    evidence = work/"evidence"
    evidence.mkdir()
    write_json(evidence,"custody",custody)
    write_json(evidence,"bindings",dict(**bindings,git_sources_sha256=HASHES),True)
    native_windows = {}
    def windows(p):
        result = {}
        for m in p["members"]:
            for t in m["tags"]:
                if t not in native_windows:
                    native_windows[t] = online.load_window(work/"windows"/t)
            result[m["binder"]] = [native_windows[t] for t in m["tags"]]
        return result
    models, native_a, crossed = {}, [], []
    with torch.inference_mode():
        # Admission: both original full native trajectories and the four write-8 swap controls.
        for name in ("M1","M3"):
            model = matrix.Memory(flat=name=="M1").eval()
            model.load_state_dict(torch.load(work/(name+".pt"),weights_only=True,map_location="cpu"),strict=True)
            assert all(p.device.type=="cpu" and p.dtype==torch.float32 for p in model.parameters())
            models[name] = model
            for p in task_a:
                routed = windows(p)
                snapshots = {m["binder"]: Replay(model,"W0",routed[m["binder"]],m["tags"],"A",False,
                                                 capture_cross=(name=="M1" and p["horizon"]==12)) for m in p["members"]}
                native_a.extend(parity_a(p,name,snapshots,archived))
                if name=="M1" and p["horizon"]==12:
                    opened = {m["expected"]["owner"]:snapshots[m["binder"]] for m in p["members"]}
                    cross_input = model,opened
        assert len(native_a)==224
        crossed = cross_controls(*cross_input,controls)
        assert len(crossed)==4
        write_json(evidence,"admission",dict(native_pairs=native_a,write8=crossed),True)
        print("Native admission passed on 224 paired points and four write-8 crosses.",flush=True)
        data = {n:[] for n in ("scores","contrasts","terminals","anchors","writes")}
        cal_parity = []
        for p in task_a+task_b:
            routed = windows(p)
            for name,model in models.items():
                writes = ("W0","W1","W2a","W2b") if name=="M1" else ("W0","W1")
                for w in writes:
                    observations = {m["binder"]:Replay(model,w,routed[m["binder"]],m["tags"],p["task"],True) for m in p["members"]}
                    if name=="M1" and p["task"]=="A" and w=="W1":
                        for m in p["members"]:
                            owner = m["expected"]["owner"]
                            row, = [s for s in observations[m["binder"]].rows if s["actual_step"]==8 and s["read"]=="R0"]
                            assert row["score_hex"] == controls["M1/relative/0.50/"+owner[0]*2]["score_f32le"]
                    if p["task"]=="B" and w=="W0":
                        cal_parity.extend(parity_b(p,name,observations,historical))
                    add_replay(p,name,w,observations,data)
            symbolic(p,routed,data)
            print("Completed",p["task"],p["horizon"],p["pair"],flush=True)
    assert len(cal_parity)==40
    assert len(data["terminals"])==24*13
    assert len(data["contrasts"])==224*6+8*12
    assert len(data["scores"])==2*len(data["contrasts"])
    write_json(evidence,"calibration-parity",cal_parity)
    effects,metrics = tables(data)
    for n,values in data.items():
        write_json(evidence,n,values,True)
    write_json(evidence,"effects",effects,True)
    write_json(evidence,"metrics",metrics)
    write_json(evidence,"runtime",dict(source=candidate,accepted_base=BASE,argv=sys.orig_argv,python=sys.version,
               executable_sha256=EXE_HASH,torch=str(torch.__version__),numpy=np.__version__,cuda_build=torch.version.cuda,
               threads=torch.get_num_threads(),interop_threads=torch.get_num_interop_threads(),deterministic=torch.are_deterministic_algorithms_enabled(),
               guards={k:os.environ[k] for k in (*CACHES,*FLAGS,"CUDA_VISIBLE_DEVICES")},cpu_seconds=time.process_time(),
               wall_seconds=time.perf_counter()-started,completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               evidence_sha256={f.name:sha(f.read_bytes()) for f in sorted(evidence.iterdir())}))

if __name__=="__main__":
    main(sys.argv[1],Path(sys.argv[2]).resolve())
