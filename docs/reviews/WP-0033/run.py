"""Run once on the exact released clean candidate; persist all scheduled statuses."""
import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys
import traceback
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = "297f028350b1521096061cf27c7ce89702b73e54"
SCRATCH = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0033/review")
CONTRACT = "docs/coordination/WP-0033/contract.json"
INPUTS = {}


def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(revision,path,digest=None):
    name=revision+":"+path
    raw=git("cat-file","blob",name)
    INPUTS[name]=sha(raw)
    if digest:
        assert INPUTS[name]==digest,name
    return raw


def save(path,data):
    path.write_bytes((json.dumps(data,indent=2,allow_nan=False)+"\n").encode())


def frozen(candidate):
    assert Path.cwd().resolve()==ROOT and ROOT.name=="w033-review"
    assert git("branch","--show-current").decode().strip()=="review/wp-0033-write8"
    assert git("rev-parse","HEAD").decode().strip()==candidate and len(candidate)==40
    assert git("merge-base",BASE,candidate).decode().strip()==BASE and not git("status","--porcelain")
    assert sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize and sys.byteorder=="little"
    for file in ("run.py","trial.py","audit.py"):
        path=HERE/file
        assert path.read_bytes().replace(b"\r\n",b"\n")==blob(candidate,path.relative_to(ROOT).as_posix()).replace(b"\r\n",b"\n")
    c=json.loads(blob(BASE,CONTRACT))
    assert git("merge-base",c["base"],BASE).decode().strip()==c["base"]
    assert Path(sys.executable).resolve()==Path(c["runtime"]).resolve()
    assert sha(Path(sys.executable).read_bytes())==c["runtime_sha256"] and platform.python_version()=="3.12.10"
    work=SCRATCH/candidate
    work.mkdir(parents=True,exist_ok=False)
    for name in ("TMP","TEMP","TORCH_HOME","HF_HOME","TORCHINDUCTOR_CACHE_DIR","XDG_CACHE_HOME"):
        (work/name).mkdir()
        os.environ[name]=str(work/name)
    os.environ.update(CUDA_VISIBLE_DEVICES="-1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",
                      HF_HUB_OFFLINE="1",PIP_NO_INDEX="1",HF_DATASETS_OFFLINE="1",TRANSFORMERS_OFFLINE="1")
    return c,work


def acquire(contract,work):
    pins=contract["input_pins"]
    for source,digest in contract["source_digests"].items():
        blob(*source.split(":",1),digest)
    loader=types.ModuleType("authenticated_loader")
    name="docs/research/WP-0031/inputs.py"
    loader.__file__=str(ROOT/name)
    exec(compile(blob(pins["loader"],name),loader.__file__,"exec"),loader.__dict__)
    archive=loader.archive_helpers(work/"library")
    captures,weights,thresholds,anchor_ids,bindings,_=loader.inputs(archive,work)
    assert (archive.OLD[0],archive.NEW[0],archive.FIX,archive.FIT,archive.PROBE)==(
        pins["Alder_sensor"],pins["Cedar_sensor"],pins["fixtures"],pins["weights"],pins["matrix"])
    for name in ("matrix","online"):
        path=f"docs/research/WP-0024/probe/{name}.py"
        assert sha((work/"library"/(name+".py")).read_bytes())==contract["source_digests"][pins["matrix"]+":"+path]
    INPUTS.update(archive.RECEIPTS)
    snap=pins["snapshots"]
    prefix="docs/research/WP-0031/evidence/"
    manifest=json.loads(blob(snap,prefix+"runtime.json"))["evidence_sha256"]
    read=lambda key: blob(snap,prefix+key,manifest[key])
    history=json.loads(blob(pins["WP32_reconciliation"],"docs/coordination/WP-0032/reconciliation.json"))["root_scalar_tables"]
    prior=json.loads(blob(pins["WP32_review"],"docs/reviews/WP-0032/evidence/tables.json"))["cells"]
    assert history["input_revision"]==snap
    return captures,weights,thresholds,anchor_ids,bindings,read,history,prior


def schedule(c):
    jobs=[]
    for mode in ("relative","absolute"):
        jobs.extend(("M1",mode,point,cell) for point in c[mode] for cell in c["hybrid"]["cells"])
    jobs.extend(("M3","hybrid",c["hybrid"]["point"],cell) for cell in c["hybrid"]["cells"])
    assert len(set(jobs))==52 and [sum(j[0]==a for j in jobs) for a in ("M1","M3")]==[48,4]
    return jobs


def count_checks(data):
    if isinstance(data,dict):
        if "pass_count" in data:
            return data["pass_count"],data["fail_count"]
        if "passed" in data:
            return (1,0) if data["passed"] else (0,1)
        data=data.values()
    elif not isinstance(data,list):
        return 0,0
    totals=[count_checks(item) for item in data]
    return sum(x for x,_ in totals),sum(y for _,y in totals)


def main(candidate):
    c,work=frozen(candidate)
    evidence=work/"evidence"
    evidence.mkdir()
    jobs=schedule(c)
    rows={}; analysis={}; manifests={}; controls={}; failures={}
    try:
        captures,weights,cuts,anchor_ids,bindings,read,history,prior=acquire(c,work)
        sys.path[:0]=[str(work/"library"),str(HERE)]
        import torch,numpy,matrix,online,trial
        assert torch.__version__=="2.13.0+cpu" and torch.version.cuda is None and numpy.__version__=="2.2.6"
        assert torch.get_default_dtype()==torch.float32 and matrix.EPS==c["epsilon"]==trial.audit.EPS
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        torch.default_generator.manual_seed(3302)
        assert torch.are_deterministic_algorithms_enabled() and torch.get_num_threads()==torch.get_num_interop_threads()==1
        windows={name:online.load_window(work/name) for name in trial.NAMES}
        with torch.inference_mode():
            for arm in ("M1","M3"):
                try:
                    doc=json.loads(read(arm+".json"))
                    runner=trial.Measurement(arm,doc,read,weights[arm],windows,captures,bindings,cuts[arm],anchor_ids[arm],prior[arm])
                    manifests[arm]=runner.source
                    controls[arm]={}
                    if arm=="M1":
                        analysis[arm]=runner.m1(jobs,c,history,prior[arm],rows,controls[arm])
                    else:
                        analysis[arm]=runner.m3(jobs,history,rows,controls[arm])
                except Exception:
                    failures[arm]=traceback.format_exc()
        save(evidence/"inputs.json",dict(captures=captures,arms=manifests,blobs_sha256=INPUTS))
    except Exception:
        failures["preflight"]=traceback.format_exc()
    parity=[]
    for job in jobs:
        arm,mode,point,cell=job
        fields=dict(arm=arm,mode=mode,point=point,cell=cell)
        row=rows.get(job)
        if row is None:
            reason=failures.get(arm) or failures.get("preflight") or "scheduled row missing"
            fields.update(dict.fromkeys(("score_f32le","read_sha256","matrix_sha256","numerator","margin","read_norm")))
            fields["reason"]=reason
            rows[job]={"status":"blocked","reason":reason}
        else:
            fields.update(row["parity"])
        parity.append(fields)
    save(evidence/"parity.json",parity)
    for arm in ("M1","M3"):
        output=dict(rows=[dict(mode=j[1],point=j[2],cell=j[3],**rows[j]) for j in jobs if j[0]==arm],
                    controls=controls.get(arm),analysis=analysis.get(arm),failure=failures.get(arm))
        output["passing_failing_check_records"]=count_checks(output)
        save(evidence/(arm+".json"),output)
    save(evidence/"run.json",dict(candidate=candidate,base=BASE,argv=sys.orig_argv,scratch=str(work),cwd=str(ROOT),
          utc=datetime.datetime.now(datetime.UTC).isoformat(),python=platform.python_version(),exe_sha256=c["runtime_sha256"],
          session="01a20b5b-d3cf-71d3-9cba-4a6b8dee98db",dispatcher_configuration="gpt-6.2-astra/xhigh",
          platform=platform.platform(),torch=str(torch.__version__) if "torch" in locals() else None,
          numpy=numpy.__version__ if "numpy" in locals() else None,
          threads=[torch.get_num_threads(),torch.get_num_interop_threads()] if "torch" in locals() else None,
          deterministic=torch.are_deterministic_algorithms_enabled() if "torch" in locals() else None,
          failures=failures,evidence_sha256={p.name:sha(p.read_bytes()) for p in evidence.iterdir()}))
    if failures:
        raise RuntimeError(failures)
    print("52 independent rows and six archived controls verified.")


if __name__=="__main__":
    main(*sys.argv[1:])
