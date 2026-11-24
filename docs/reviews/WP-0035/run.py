"""Run a released candidate exactly once in its own immutable scratch directory."""
import datetime
import gzip
import io
import json
import os
import platform
import re
import struct
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import bind
import metrics

RUNTIME=Path("C:/Users/jackg/eLedgerCare-Speed/WP-0030/runtime/venv/Scripts/python.exe")
EXE_SHA="0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14"


def environment(candidate):
    assert Path.cwd()==bind.ROOT and bind.ROOT.name=="w035-review"
    assert bind.git("branch","--show-current").decode().strip()=="review/wp-0035-trajectory"
    assert re.fullmatch(r"[0-9a-f]{40}",candidate) and bind.git("rev-parse","HEAD").decode().strip()==candidate
    assert bind.git("merge-base",candidate,bind.BASE).decode().strip()==bind.BASE and not bind.git("status","--porcelain")
    assert Path(sys.executable).resolve()==RUNTIME.resolve() and bind.sha(RUNTIME.read_bytes())==EXE_SHA
    assert platform.python_version()=="3.12.10" and sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize
    assert sys.byteorder=="little"
    work=bind.SCRATCH/candidate
    work.mkdir(exist_ok=False)
    for name in ("TEMP","TMP","HF_HOME","XDG_CACHE_HOME","TORCH_HOME","TORCHINDUCTOR_CACHE_DIR"):
        dest=work/name
        dest.mkdir()
        os.environ[name]=str(dest)
    os.environ.update(CUDA_VISIBLE_DEVICES="-1",OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1",
                      PIP_NO_INDEX="1",HF_HUB_OFFLINE="1",HF_DATASETS_OFFLINE="1",TRANSFORMERS_OFFLINE="1")
    return work


def init_torch(work,weights):
    global torch, matrix, online, observe
    sys.path.insert(0,str(work/"library"))
    import torch, matrix, online, observe, numpy
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.default_generator.manual_seed(3502)
    assert torch.__version__=="2.13.0+cpu" and torch.version.cuda is None and numpy.__version__=="2.2.6"
    assert torch.get_default_dtype()==torch.float32 and torch.get_num_threads()==torch.get_num_interop_threads()==1
    assert torch.are_deterministic_algorithms_enabled() and matrix.EPS==1e-8
    models={}
    for name,weights_bytes in weights.items():
        model=matrix.Memory(flat=name=="M1").eval()
        model.load_state_dict(torch.load(io.BytesIO(weights_bytes),weights_only=True,map_location="cpu"),strict=True)
        assert all(p.device.type=="cpu" and p.dtype==torch.float32 for p in model.parameters())
        models[name]=model
    return models


def emit(folder,name,value):
    encoded=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()+b"\n"
    (folder/(name+".json.gz")).write_bytes(gzip.compress(encoded,compresslevel=6,mtime=0))


def verify224(rows,steps):
    lookup={(r["model"],r["horizon"],r["truth"],r["phase"],r["step"]):r for r in rows}
    assert len(lookup)==len(rows)==448 and len(steps)==224
    receipt=[]
    for old in steps:
        m,h=old["run"].split("/")
        margin=[]
        for truth in ("Alder","Cedar"):
            entry=old[truth]
            got=lookup[m,int(h),truth,old["phase"],old["step"]]
            ref=entry["read"]
            assert ref["score_f32le"]==got["score_hex"] and struct.pack("<d",got["margin"]).hex()==ref["margin_f64le"]
            for k in ("query_sha256","read_sha256","matrix_sha256","owner_columns_sha256","registry"):
                assert ref[k]==got[k], (m,h,truth,old["step"],k)
            assert ref["zero_read"]==got["zero"] and ref["owner_eligible"]==got["eligible"]
            assert ref["controller"]==dict(depth=got["depth"],fault=got["fault"],held=got["held"],ambiguous_reason=got["scope"])
            assert got["events"]==entry["events_applied"]
            if entry["source"]:
                assert got["ptr"]==entry["source"]["ptr"] and got["text"]==entry["source"]["text"] and got["window"]==entry["source"]["key"]
            assert (ref["top"]=="tie") == got["tied"] and (got["tied"] or ref["top"]==got["leaders"][0])
            margin.append(got["margin"])
        d=margin[0]-margin[1]
        assert struct.pack("<d",d).hex()==old["delta_f64le"] and (margin[0]>0>margin[1])==old["paired_win"]
        receipt.append(dict(model=m,horizon=int(h),phase=old["phase"],step=old["step"],delta_f64le=old["delta_f64le"]))
    return receipt


def check_stock(original, attempts, typed):
    assert typed==original["selected_binder_decision"] and len(attempts)==original["attempt_count"]
    checks=0
    for obs in attempts:
        old=original["attempts_by_ptr"]["/".join(map(str,obs["ptr"]))]
        assert obs["typed"]==old["original_selected_typed"] and obs["reason"]==old["attempt_reason"]
        assert obs["zero"]==old["zero"] and obs["summary_target"]==old["summary_target"] and obs["literal"]==old["literal"]
        for f, item in old["fields"].items():
            values=item["scores_by_key"]
            if not values:
                assert f not in obs["fields"]
                continue
            current=obs["fields"][f]
            assert {online.key(k):v for k,v in current["scores"].items()}==values
            assert current["f32le"]==struct.pack("<"+"f"*len(values),*(values[online.key(k)] for k in current["scores"])).hex()
            assert current["read_sha256"]==item["actual_read"]["read_sha256"]
            assert obs["query_sha256"]==item["actual_read"]["query_sha256"]
            checks+=len(values)
    return checks


def assess(member,typed,scores):
    actual = [s for s in scores if s["phase"]=="native_pre"]
    row=actual[0] if len(actual)==1 else None
    status=None
    bucket=None
    if row:
        decision=row["eligible_decision"]
        status="A" if decision is None else "C" if decision==member["expected"]["owner"] else "W"
        if row["score_pass"] and row["gap_pass"]: bucket="pass"
        elif row["score_pass"]: bucket="gap_only"
        elif row["gap_pass"]: bucket="score_only"
        else: bucket="both"
    return dict(answerable=member["answerable"],expected=member["expected"],target=member["target"],typed=typed,
                typed_status=metrics.outcome(typed,member["expected"],member["answerable"]),owner_status=status,cutoff_failure=bucket)


def execute(work, folder):
    bindings,weights,steps,controls,labels,dev=bind.acquire(work)
    assert bindings==json.loads((HERE/"bindings.json").read_bytes())
    models=init_torch(work,weights)
    groups=bindings["cases"]
    windows={(name,k):online.load_window(work/name/k) for name,keys in (
        ("cal",bindings["calibration_windows"]),("captures",bindings["development_windows"])) for k in keys}
    prior=json.loads(bind.blob(bind.BASE,"docs/reviews/WP-0033/evidence/parity.json"))
    prior={r["cell"]:r for r in prior if (r["arm"],r["mode"],r["point"])==("M1","relative","0.50")}
    scores,terms,writes,geometries=[],[],{},{}
    stock,stock_dev=[],[]
    def neural(case,m,w,rs):
        ident={k:case[k] for k in ("task","pair","horizon")}
        all_steps=case["task"]=="A"
        cuts=bindings["thresholds"][m]
        for binder,member in case["members"].items():
            stream=observe.stream_for(case,member,windows)
            part,attempts,updates,an=observe.binder(models[m],w,rs,stream,all_steps,cuts)
            token=(case["pair"],binder,m,w)
            if token in writes:
                assert writes[token]==updates
            writes[token]=updates
            token=(case["pair"],binder,m)
            if token in geometries:
                assert geometries[token]==an
            geometries[token]=an
            for r in rs:
                tagged=[]
                for p in part:
                    if p["read"]!=r: continue
                    tagged.append(dict(p,**ident,binder=binder,model=m,write=w,truth=member["expected"]["owner"],
                                       step=p["step"] if all_steps else -1,actual_step=p["step"]))
                scores.extend(tagged)
                result=online.single([a["typed"] for a in attempts[r]])
                term=dict(**ident,binder=binder,model=m,write=w,read=r,attempts=attempts[r],
                          **assess(member,result,tagged))
                terms.append(term)
                if w=="W0" and r=="R0":
                    if case["task"]=="B":
                        old=labels[m]["by_binder"][binder]
                        n=check_stock(old,attempts[r],result)
                        stock.append(dict(model=m,binder=binder,fields_scores_exact=n,attempts=old["attempt_count"],typed=result))
                    else:
                        hist,=[x for x in dev["arms"][m] if x["pair"]==case["pair"]]
                        entry,=[x for x in hist["members"] if x["binder"]==binder]
                        old,=entry["parity"]["plain_target"]["attempts"]
                        curr,=attempts[r]
                        assert result==old["typed"] and {f:bind.sha(bytes.fromhex(v["f32le"])) for f,v in curr["fields"].items()}==old["logit_sha256"]
                        for field in ("summary_target","summary_zero","reason","zero"):
                            assert curr[field]==old[field]
                        stock_dev.append(dict(model=m,binder=binder,typed=result,field_hashes=old["logit_sha256"]))
    with torch.inference_mode():
        development=[c for c in groups if c["task"]=="A"]
        for case in development:
            for m in models:
                neural(case,m,"W0",["R0"])
        native=verify224(scores,steps)
        case,=[c for c in development if c["horizon"]==12]
        openings={}
        query=None
        for member in case["members"].values():
            stream=observe.stream_for(case,member,windows)
            w=stream[0][1]
            openings[member["expected"]["owner"][0]]=(w,w)
            t,=[e for idx,(_,win) in enumerate(stream,1) for sp in win.spans for e in online.identify(sp,idx) if e.kind=="TARGET"]
            q=models["M1"].project(stream[t.ptr[0]-1][1])[2][t.ptr[2]]
            assert query is None or observe.raw(q)==observe.raw(query)
            query=q
        cross=observe.crossed(models["M1"],openings,query,controls,prior)
        bind.save(folder/"parity.json",dict(native224=native,relative_half=cross,development_terminals=stock_dev))
        for case in groups:
            for m in models:
                for w in (("W0","W1","W2a","W2b") if m=="M1" else ("W0","W1")):
                    rs=["R1"] if case["task"]=="A" and w=="W0" else ["R0","R1"]
                    neural(case,m,w,rs)
            for binder,member in case["members"].items():
                typed,outputs=observe.symbolic(observe.stream_for(case,member,windows))
                terms.append(dict(task=case["task"],pair=case["pair"],horizon=case["horizon"],binder=binder,
                                  model="M2",write="symbolic",read="symbolic",attempts=outputs,**assess(member,typed,[])))
    paired=metrics.contrast(scores,groups)
    counts=Counter(s["task"] for s in scores)
    assert counts=={"A":2688,"B":192} and len(paired)==1440 and len(terms)==312 and len(stock)==40
    def flatten(d,keys,field):
        return [{**dict(zip(keys,k,strict=True)),field:v} for k,v in d.items()]
    for name,data in (("scores",scores),("contrasts",paired),("terminals",terms),("custody",bindings["custody"]),
                      ("anchor_geometry",flatten(geometries,("pair","binder","model"),"anchors")),
                      ("writes",flatten(writes,("pair","binder","model","write"),"observations")),
                      ("mechanism_differences",metrics.comparisons(paired)),("attenuation",metrics.attenuation(paired,writes)),
                      ("metrics",metrics.metrics(terms,paired)),("stock_calibration",stock)):
        emit(folder,name,data)
    return dict(scores=counts,contrasts=len(paired),terminals=len(terms),native=len(native),crossed=len(cross),stock=len(stock))


def main(candidate):
    work=environment(candidate)
    evidence=work/"evidence"
    evidence.mkdir()
    start=time.perf_counter()
    receipt=dict(candidate=candidate,base=bind.BASE,argv=sys.orig_argv,executable=str(RUNTIME),executable_sha256=EXE_SHA,
                 thread="01a20bdc-db62-7fe1-8b1b-d4dd9b47ae36",requested_configuration="gpt-6.2-astra/xhigh",
                 utc_start=datetime.datetime.now(datetime.UTC).isoformat(),cwd=str(Path.cwd()),python=platform.python_version(),
                 library_offline=True,cache_root=str(work),platform=platform.platform())
    try:
        receipt["counts"]=execute(work,evidence)
    except BaseException:
        receipt["failure"]=traceback.format_exc()
        raise
    finally:
        if "torch" in globals():
            receipt.update(torch_version=str(torch.__version__),cuda_build=torch.version.cuda,
                deterministic=torch.are_deterministic_algorithms_enabled(),threads=[torch.get_num_threads(),torch.get_num_interop_threads()])
        receipt.update(utc_end=datetime.datetime.now(datetime.UTC).isoformat(),wall_seconds=time.perf_counter()-start,
                       evidence_sha256={p.name:bind.sha(p.read_bytes()) for p in evidence.iterdir()},git_blobs=bind.BLOBS)
        bind.save(evidence/"execution.json",receipt)


if __name__=="__main__":
    main(*sys.argv[1:])
