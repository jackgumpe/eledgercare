"""Pinned, offline WP-0036 author entry point. Run once under coordinator's CPU lease."""
import gzip
import hashlib
import json
import os
import platform
import subprocess
import sys
from collections import Counter,defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from archive import ROOT,admit,labels,sha
from arithmetic import archive_audit
from directory import decode,distance,perturb,twin
from slots import stream,e4
from margins import exercise


def write(work,name,obj):
    with (work/(name+".json.gz")).open("xb") as f:
        with gzip.GzipFile(filename="",fileobj=f,mode="wb",mtime=0) as g:
            g.write((json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)+"\n").encode())


def evaluate(routes,physical,online):
    calls,arithmetic={},[]
    for route in routes:
        key={k:route[k] for k in ("task","pair","binder","horizon")}
        calls[route["binder"]]=stream(route,physical,online)
        arithmetic.append(dict(**key,**archive_audit(route,physical,online)))
    return calls,arithmetic


def align(references,calls,routes,truth):
    rows=[]
    by_ref={(r["horizon"],truth[r["binder"]]["expected"]["owner"]):r for r in routes if r["task"]=="A"}
    for ref,line_sha in references:
        model,len_s=ref["run"].split("/")
        for arm in ("Alder","Cedar"):
            r=by_ref[(int(len_s),arm)]
            timeline=calls[r["binder"]]["timeline"]
            phase,step=ref["phase"],ref["step"]
            row,=[s for s in timeline if (s["phase"],s["step"])==(phase,step)]
            hist=ref[arm]
            assert (hist["phase"],hist["step"])==(phase,step)
            assert row["source"]==hist["source"],(model,len_s,phase,step,arm,row["source"],hist["source"])
            assert row["events"]==[e["kind"] for e in hist["events_applied"]]
            assert row["depth"]==hist["read"]["controller"]["depth"]
            first=timeline[8]
            assert first["events"]==["OPEN_LEDGER"] and first["step"]==8 and first["depth"]==0
            witness=row["witness"]
            rows.append(dict(model=model,horizon=int(len_s),binder=r["binder"],pair=r["pair"],arm=arm,
                             phase=phase,step=step,ptr=row["source"]["ptr"] if row["source"] else None,
                             events=row["events"],depth=row["depth"],reference_line_sha256=line_sha,
                             raw_slice_sha256=row["source"]["raw_slice_sha256"] if row["source"] else None,
                             witness=witness,first_root_full_sha256=first["witness"]["full_sha256"],
                             subject_to_isolation=step>=8 and witness is not None,
                             equal_since_declaration=witness==first["witness"] if step>=8 and witness is not None else None,
                             excluded=row.get("excluded")))
    assert len(rows)==448
    return rows


def score(routes,calls,truth):
    terminals,sweep=[],[]
    pairs=defaultdict(dict)
    for route in routes:
        bid=route["binder"]
        c=calls[bid]
        historical=truth[bid]
        expected=historical["expected"]
        assert c["native"]==historical["typed"] and c["native_targets"]==[a["ptr"] for a in historical["attempts"]]
        key={k:route[k] for k in ("task","pair","binder","horizon")}
        for variant in c["terminals"]:
            answer=variant["typed"]
            correct=(answer==dict(type="Posting",**expected)) if historical["answerable"] else answer=={"type":"ABSTAIN","reason":"no_target"}
            scored={}
            for field,item in variant["fields"].items():
                scored[field]=dict(**item,error=distance(item["raw"],expected[field],variant["eta"]) if item["raw"] is not None else None,
                                    correct=item["decision"]==expected[field])
            terminals.append(dict(**key,**{k:v for k,v in variant.items() if k!="fields"},fields=scored,correct=correct,
                                  historical_target=historical["target"],expected=expected,native=c["native"],native_parity=True,answerable=historical["answerable"]))
            if historical["answerable"]:
                item=variant["fields"]["owner"]
                eta=variant["eta"]
                pairs[(route["task"],route["pair"],route["horizon"],eta)][expected["owner"]]=item
                sweep.extend(dict(**key,eta=eta,**row) for row in perturb(item,expected["owner"],eta))
    contrasts=[dict(task=t,pair=p,horizon=h,eta=e,**twin(m["Alder"],m["Cedar"],e)) for (t,p,h,e),m in pairs.items()]
    return terminals,sweep,contrasts


def report_metrics(routes,physical,arithmetic,terminals,sweep,twins,refs,calls,astore):
    measured=[r for r in refs if r["subject_to_isolation"]]
    tables=[t for r in arithmetic for t in r["tables"]]
    child=[c for r in arithmetic for c in r["child_subtotals"]]
    maintenance=[c for r in arithmetic for c in r["maintenance"]]
    population={}
    for t in ("A","B"):
        for h in (12,30):
            for eta in (0,.5):
                ts=[r for r in terminals if (r["task"],r["horizon"],r["eta"])==(t,h,eta)]
                population[f"{t}/{h}/{eta}"]=dict(binders=len(ts),answerable=sum(r["answerable"] for r in ts),
                    conditional_correct_post=sum(r["correct"] and r["typed"]["type"]=="Posting" for r in ts),
                    native_post=sum(r["native"]["type"]=="Posting" for r in ts),
                    correct_no_target=sum(r["correct"] and r["reasons"]==["no_target"] for r in ts),
                    end_to_end_measured_answerable=0)
    return dict(population=population,physical_captures=len(physical),logical_windows=sum(len(r["tags"]) for r in routes),
                E=dict(paired_archived=len(refs)//2,member_references=len(refs),excluded=sum(bool(r["excluded"]) for r in refs),
                       post_decl_through_target=len(measured),changed=sum(not r["equal_since_declaration"] for r in measured),
                       controls_full_steps={r["binder"]:len(calls[r["binder"]]["timeline"])-1 for r in routes if not calls[r["binder"]]["native_targets"]}),
                F=dict(terminal_rows=len(terminals),tested_twin_bounds=len(twins),bound_violations=sum(not all(r["checks"]) for r in twins),
                       requested_perturbations=len(sweep),attainable=sum(r["attainable"] for r in sweep),
                       below_half=sum(r.get("under_half",False) for r in sweep),
                       below_half_nearest_errors=sum(r.get("under_half",False) and not r["nearest_correct"] for r in sweep)),
                D=dict(binders=len(arithmetic),physical_table_instances=len(tables),physical_distinct_raw_bytes=len({t["raw_sha256"] for t in tables}),
                       physical_D=sum(t["D"] is not None for t in tables),observed_complete_balances=sum(t["explicit_balance_chain"] is not None for t in tables),
                       child_schedule_instances=len(child),child_D=Counter(str(r["D"]) for r in child),
                       child_row_counts=Counter(len(r["body"]) for r in child),archived_injections=sum(len(r["grids"]) for r in arithmetic),
                       maintenance_instances=len(maintenance),maintenance_residual_minor=Counter(str(r["residual"]) for r in maintenance)),
                A=dict(capture_directories=len(physical),logical_binders=len(routes),archived_scores=0,eligible_archived_error_documents=0,
                       synthetic_score_rows=len(astore),rounded_strict_failures=[r["eta"] for r in astore if r["case"]=="rounded" and not r["observed_strict"]]))


def main():
    candidate,location=sys.argv[1:]
    work=Path(location).resolve()
    assert work.parent==Path("C:/Users/jackg/eLedgerCare-Speed/WP-0036/author") and work.name.startswith("attempt-")
    assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==candidate
    assert not subprocess.check_output(["git","status","--porcelain","--untracked-files=normal"],cwd=ROOT)
    assert sha(Path(sys.executable).read_bytes())=="0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14"
    assert sys.flags.isolated and sys.dont_write_bytecode
    assert os.environ["CUDA_VISIBLE_DEVICES"]=="-1"
    for n in ("OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","HF_HUB_OFFLINE","PIP_NO_INDEX"):
        assert os.environ[n]=="1"
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    assert torch.version.cuda is None and torch.get_num_threads()==torch.get_num_interop_threads()==1
    sys.path.insert(0,str(ROOT/"docs/research/WP-0024/probe"))
    import online
    physical,routes,audit,refs,custody=admit(online)
    accepted_files={"receipt.json","metadata.json","native.json","capture.json","duration.json","through-eos.u32le","pooled.f32",
                    "token_hidden.bf16","observed-positions.json"}
    for cap in audit:
        assert set(cap["members"])<=accepted_files,"review new archive member; presence/absence must be established"
        for keys in cap["json_keys"].values():
            assert not any("logit" in k.casefold() or "logprob" in k.casefold() for k in keys),"review newly available archived distribution"
    calls,arithmetic=evaluate(routes,physical,online)
    truth=labels(custody)
    erows=align(refs,calls,routes,truth)
    terminals,sweep,twins=score(routes,calls,truth)
    arows,ranks=exercise()
    metrics=report_metrics(routes,physical,arithmetic,terminals,sweep,twins,erows,calls,arows)
    safety={bid:c["timeline"] for bid,c in calls.items() if not c["native_targets"]}
    synthetic_gates=[dict(case=name,**decode(v,choices,.5,scope)) for name,v,choices,scope in (
        ("scope","Alder",["Alder","Cedar"],"unresolved_scope"),("missing",None,["Alder","Cedar"],""),
        ("tied","ab",["aa","bb"],""),("collision","ab",["ab","a.b"],""),
        ("inclusive_margin","6",["6","8"],""),("strict_half","ax",["aa","xx"],""))]
    a_binding=dict(captures=audit,logical=[{k:v for k,v in r.items() if k!="keys"} for r in routes],
                   raw_emitted_vocab_logits=0,raw_vocab_map=0,critical_error_labels=0,
                   limitation="Through-EOS IDs, hidden inputs to lm_head, pooled span features and entity logits do not identify emitted vocabulary rival logits.",
                   archives={k:v for k,v in custody["references_sha256"].items() if k.endswith(("steps.jsonl",".zip","cal-transport.json","online.py"))})
    differences=[]
    for tag,cap in physical.items():
        for item in cap["spans"]:
            s=item["canonical"]
            if s.text!=item["observed"]:
                differences.append(dict(tag=tag,span=s.index,kind=s.kind,block_kind=s.block_kind,raw=item["observed"],native=s.text,
                                        raw_sha256=item["sha256"],byte_range=item["byte_range"]))
    evidence={"inputs":a_binding,"raw-vs-native":differences,"E":erows,"E-controls":safety,"E4":e4(online),
              "F":terminals,"F3":twins,"F-sweep":sweep,"F-synthetic-guards":synthetic_gates,
              "D":arithmetic,"A":arows,"A-quantiles":ranks,"metrics":metrics}
    for name,obj in evidence.items():
        write(work,name,obj)
    print(json.dumps(metrics,sort_keys=True))
    receipt=dict(source=candidate,utc=datetime.now(timezone.utc).isoformat(),executable=sys.executable,argv=sys.argv,
                 cpu_only=True,torch=torch.__version__,numpy=online.np.__version__,python=platform.python_version(),
                 threads=[torch.get_num_threads(),torch.get_num_interop_threads()],artifacts={p.name:sha(p.read_bytes()) for p in sorted(work.glob("*.json.gz"))})
    (work/"runtime.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf8")
if __name__=="__main__":
    main()
