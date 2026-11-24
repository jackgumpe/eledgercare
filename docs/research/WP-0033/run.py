"""Execute the frozen WP-0033 author matrix once in candidate-owned, empty scratch."""
import gzip
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import traceback
import types
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESERVATION = "297f028350b1521096061cf27c7ce89702b73e54"
BRANCH = "research/wp-0033-write8"
CONTRACT = "docs/coordination/WP-0033/contract.json"
ARCHIVE = "docs/research/WP-0031/evidence/"
SOURCES = ("run.py", "metrics.py", "bindings.py", "attribution.py", "erasure.py")
INPUTS = {}


def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(rev,path,expected=None):
    spec = rev+":"+path
    data = git("cat-file","blob",spec)
    actual = sha(data)
    assert expected is None or actual == expected, spec
    INPUTS[spec] = actual
    return data


def save(path,obj):
    data = (json.dumps(obj,indent=2,allow_nan=False,ensure_ascii=False)+"\n").encode()
    path.write_bytes(gzip.compress(data,mtime=0) if path.suffix==".gz" else data)


def row_keys(contract):
    cells=("AA","AC","CA","CC")
    tuples=[("M1",m,p,c) for m in ("relative","absolute") for p in contract[m] for c in cells]
    tuples += [("M3","hybrid",contract["hybrid"]["point"],c) for c in contract["hybrid"]["cells"]]
    assert len(tuples)==len(set(tuples))==52
    return tuples


def prereqs(contract,work):
    for spec,expected in contract["source_digests"].items():
        blob(*spec.split(":",1),expected)
    pins=contract["input_pins"]
    loader=pins["loader"]
    lib=work/"library"
    lib.mkdir()
    path="docs/research/WP-0031/inputs.py"
    mod=types.ModuleType("wp0031_inputs")
    mod.__file__=str(ROOT/path)
    exec(compile(blob(loader,path),mod.__file__,"exec"),mod.__dict__)
    archive=mod.archive_helpers(lib)
    assert (archive.FIT,archive.FIX,archive.PROBE,archive.OLD[0],archive.NEW[0]) == tuple(
        pins[x] for x in ("weights","fixtures","matrix","Alder_sensor","Cedar_sensor"))
    captures,weights,cuts,anchor_hashes,bindings,steps=mod.inputs(archive,work)
    previous=json.loads(blob(pins["snapshots"],ARCHIVE+"inputs.json"))
    assert json.loads(json.dumps(captures))==previous["captures"]
    assert archive.RECEIPTS == previous["blobs_sha256"]
    INPUTS.update(archive.RECEIPTS)
    (lib/"experiment.py").write_bytes(blob(loader,"docs/research/WP-0031/experiment.py"))
    sys.path[:0]=[str(lib),str(HERE)]
    return captures,weights,cuts,anchor_hashes,bindings,steps


def run(candidate):
    assert re.fullmatch("[0-9a-f]{40}",candidate)
    assert git("rev-parse","HEAD").decode().strip()==candidate
    assert git("branch","--show-current").decode().strip()==BRANCH
    assert git("merge-base",candidate,RESERVATION).decode().strip()==RESERVATION
    assert not git("status","--porcelain")
    contract=json.loads(blob(RESERVATION,CONTRACT))
    assert ROOT.resolve()==Path("C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w033-author").resolve()
    assert git("merge-base",RESERVATION,contract["base"]).decode().strip()==contract["base"]
    for name in SOURCES:
        path=HERE/name
        assert path.read_bytes().replace(b"\r\n",b"\n")==blob(candidate,path.relative_to(ROOT).as_posix()).replace(b"\r\n",b"\n")
    assert sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize
    executable=Path(sys.executable).resolve()
    assert executable==Path(contract["runtime"]).resolve() and sha(executable.read_bytes())==contract["runtime_sha256"]
    assert sys.version_info[:3]==(3,12,10) and sys.byteorder=="little"
    work=Path("C:/Users/jackg/eLedgerCare-Speed/WP-0033/author")/candidate
    work.mkdir(parents=True,exist_ok=False)
    evidence=work/"evidence"
    evidence.mkdir()
    for key in ("TMP","TEMP","TORCH_HOME","XDG_CACHE_HOME","TORCHINDUCTOR_CACHE_DIR","HF_HOME"):
        (work/key).mkdir()
        os.environ[key]=str(work/key)
    os.environ.update(CUDA_VISIBLE_DEVICES="-1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",
                      HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",PIP_NO_INDEX="1")
    parity_rows,failures=[],{}
    schedule=row_keys(contract)
    runtime=dict(start_utc=datetime.now(timezone.utc).isoformat(),candidate=candidate,authority=contract["base"],
                 reservation=RESERVATION,branch=BRANCH,worktree=str(ROOT),scratch=str(work),argv=sys.orig_argv,
                 executable=str(executable),executable_sha256=sha(executable.read_bytes()),platform=platform.platform(),
                 python=sys.version,isolated=sys.flags.isolated,disable_bytecode=sys.flags.dont_write_bytecode,
                 gain_cast="binary64 requested to FP32 once per update; absolute uses a separate matrix formula",
                 parity_scalar_convention="binary64 h dot promoted native read, its binary64 norm, margin of two promoted native scores")
    try:
        cap,weights,cuts,ah,bound,steps=prereqs(contract,work)
        import numpy
        import torch
        import attribution
        import bindings
        import erasure
        import matrix
        import metrics
        assert str(torch.__version__)=="2.13.0+cpu" and torch.version.cuda is None and numpy.__version__=="2.2.6"
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        torch.default_generator.manual_seed(2401)
        assert torch.get_num_threads()==torch.get_num_interop_threads()==1 and torch.get_default_dtype()==torch.float32
        assert matrix.EPS==metrics.EPS==contract["epsilon"]
        runtime.update(torch=str(torch.__version__),numpy=numpy.__version__,torch_cuda_build=torch.version.cuda,
                       threads=[torch.get_num_threads(),torch.get_num_interop_threads()],deterministic=torch.are_deterministic_algorithms_enabled())
        pins=contract["input_pins"]
        table=json.loads(blob(pins["WP32_reconciliation"],"docs/coordination/WP-0032/reconciliation.json"))["root_scalar_tables"]
        receipts=json.loads(blob(pins["snapshots"],ARCHIVE+"runtime.json"))["evidence_sha256"]
        def snapshot(name):
            return blob(pins["snapshots"],ARCHIVE+name,receipts[name])
        with torch.inference_mode():
            for arm in ("M1","M3"):
                result,checks={},metrics.Checks()
                try:
                    archived=json.loads(snapshot(arm+".json"))
                    prior=json.loads(blob(pins["WP32_author"],"docs/research/WP-0032/evidence/"+arm+".json"))
                    model,sources,windows,anchors,manifest,controls=bindings.verify_arm(
                        arm,work,weights,cuts,cap,steps,bound,archived,prior,snapshot)
                    assert metrics.digest(metrics.raw(anchors))==ah[arm]
                    save(evidence/(arm+"-bindings.json"),manifest)
                    save(evidence/(arm+"-controls.json"),controls)
                    if arm=="M1":
                        erasure.analyze(contract,model,sources,anchors,cuts[arm],controls,prior,table,checks,result,parity_rows)
                    else:
                        attribution.analyze(contract,model,sources,windows,anchors,cuts[arm],controls,table,checks,result,parity_rows)
                    assert all(x["passed"] for x in checks.rows), "one or more numerical checks failed"
                except Exception:
                    failures[arm]=traceback.format_exc()
                result.update(status="blocked" if arm in failures else "measured",reason=failures.get(arm),
                              checks={"groups":len(checks.rows),"scalars":sum(x.get("compared",1) for x in checks.rows),
                                      "failures":sum(x.get("failures",int(not x["passed"])) for x in checks.rows)})
                save(evidence/(arm+".json"),result)
                save(evidence/(arm+"-checks.json.gz"),checks.rows)
    except Exception:
        failures["prerequisite"]=traceback.format_exc()
    keyed={(r["arm"],r["mode"],r["point"],r["cell"]):r for r in parity_rows}
    assert len(keyed)==len(parity_rows) and set(keyed).issubset(schedule)
    for arm,mode,pt,cell in schedule:
        key=(arm,mode,pt,cell)
        if key not in keyed:
            reason=failures.get(arm,failures.get("prerequisite"))
            assert reason, key
            keyed[key]=dict(arm=arm,mode=mode,point=pt,cell=cell,score_f32le=None,read_sha256=None,matrix_sha256=None,
                            numerator=None,margin=None,read_norm=None,reason=reason)
    save(evidence/"parity.json",[keyed[k] for k in schedule])
    save(evidence/"input-manifest.json",INPUTS)
    runtime.update(failures=failures,observed_rows=len(parity_rows),planned_rows=len(schedule),
                   finished_utc=datetime.now(timezone.utc).isoformat(),digest_before_runtime={p.name:sha(p.read_bytes()) for p in evidence.iterdir()})
    save(evidence/"runtime.json",runtime)
    print(json.dumps({"candidate":candidate,"rows":len(parity_rows),"failures":failures},indent=2))
    return int(bool(failures))


if __name__=="__main__":
    sys.exit(run(*sys.argv[1:]))
