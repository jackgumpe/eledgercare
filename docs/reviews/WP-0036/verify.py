"""Sole entry point for the held, single-thread independent CPU run."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from inputs import packed, read_inputs, sha
from machine import e4_case, historic_check, replay
from metric import edit, norm, token_checks, twin_sweep
from money import arithmetic, table_inventory

OUTROOT=Path("C:/Users/jackg/eLedgerCare-Speed/WP-0036/review")
EXE_SHA="4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a"


def save(out,group,obj):
    data=packed(obj)+b"\n"
    with (out/(group+".json.gz")).open("xb") as fp:
        with gzip.GzipFile(filename="", mode="wb",fileobj=fp,mtime=0,compresslevel=9) as stream:
            stream.write(data)
    return dict(sha256_uncompressed=sha(data),bytes=len(data))


def pair_score(pid,eta,members):
    rec={}
    for owner,r in members.items():
        f=r["owner"]
        distances={candidate:d for d,candidate in f["ranks"]}
        assert set(distances)=={"Alder","Cedar"}
        rec[owner]=dict(binder=r["binder"],error=distances[owner],signed=distances["Cedar"]-distances["Alder"],
                        text=f["text"],directory=f["candidates"],dmin=f["dmin"])
    a,b=rec["Alder"],rec["Cedar"]
    g=a["dmin"]
    assert g==b["dmin"]
    mu=(a["signed"]+b["signed"])/2
    delta=a["signed"]-b["signed"]
    checks=[g-2*a["error"]<=a["signed"]<=g, -g<=b["signed"]<=-g+2*b["error"],
            abs(mu)<=max(a["error"],b["error"]),delta>=2*g-2*(a["error"]+b["error"])]
    assert all(checks)
    return dict(pair=pid,eta=eta,g=g,members=rec,mu=mu,delta=delta,all_four_bounds=checks)


def run(dest,head):
    assert sys.flags.isolated and sys.dont_write_bytecode and sys.flags.optimize==0
    assert sha(Path(sys.executable).read_bytes())==EXE_SHA
    assert subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==head
    assert subprocess.check_output(["git","branch","--show-current"],text=True).strip()=="review/wp-0036-pgda"
    assert not subprocess.check_output(["git","status","--porcelain"])
    assert dest.parent.resolve()==OUTROOT.resolve()
    dest.mkdir(exist_ok=False)
    for thread_var in ["OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"]:
        os.environ[thread_var]="1"
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", CUDA_VISIBLE_DEVICES="")
    routes,caps,historical,labels,custody=read_inputs()
    custody["routes"]=routes
    tables=table_inventory(caps)
    terms,details,amounts={}, {}, []
    inputs_used=Counter()
    for route in routes:
        bid=route["binder"]
        terminal,steps,sources=replay(route,caps)
        terms[bid]=terminal
        details[bid]=(steps,sources)
        inputs_used.update(route["tags"])
        amounts.append(arithmetic(route,caps,tables))
    # No prediction path has seen expected labels. Now attach score-only references.
    pairs=defaultdict(dict)
    development={}
    sweeps=[]
    streams=[]
    for route in routes:
        bid=route["binder"]
        term=terms[bid]
        steps,src=details[bid]
        truth=labels[bid]
        term.update(truth=truth,pair=route["pair"],task=route["task"],horizon=route["horizon"])
        expected=dict(type="Posting",**truth) if truth["owner"] is not None else dict(type="ABSTAIN",reason="no_target")
        term["native_exact"]=term["native"]==expected
        assert term["native_exact"]
        if route["task"]=="A":
            development[route["horizon"],truth["owner"]]=(bid,term,steps,src)
        streams.append(dict(binder=bid,task=route["task"],horizon=route["horizon"],target=route["target"],
                            spans=steps,count=len(steps),full_no_target=term["ptr"] is None))
        for row in term["eta"]:
            row["exact"]=row["conditional"]==expected
            if truth["owner"] and term["ptr"]:
                f=row["fields"]["owner"]
                e=edit(norm(f["text"]),norm(truth["owner"]),row["eta"])
                u=row["fields"]["unit"]
                row["unit_error"]=edit(norm(u["text"]),norm(truth["unit"]),row["eta"])
                row["owner_error"]=e
                pairs[route["pair"],row["eta"]][truth["owner"]]=dict(binder=bid,owner=f)
                sweeps.extend(twin_sweep(bid,f,truth["owner"],row["eta"]))
    witnesses=historic_check(historical,development)
    twins=[pair_score(pid,eta,mem) for (pid,eta),mem in sorted(pairs.items())]
    assert len(twins)==20
    anomalies=[]
    for tag,c in caps.items():
        for s in c["spans"]:
            r=s["record"]
            if s["raw"]!=r["text"] or (r["kind"]=="block" and "<table" in s["raw"].lower() and
                                          not s["raw"].strip().endswith("</table>")):
                anomalies.append(dict(tag=tag,index=r["index"],range=r["byte_range"],kind=r["kind"],
                                      raw=s["raw"],parsed=r["text"],raw_sha=s["rawsha"],
                                      parsed_sha=sha(r["text"].encode()),cells=r["cells"]))
    evidence={
        "custody":custody,"raw-parse":anomalies,"physical-tables":tables,"streams":streams,"archival-witnesses":witnesses,
        "terminal":terms,"twins":twins,"sweep":sweeps,"arithmetic":amounts,"synthetic-A":token_checks(),
        "synthetic-E4":e4_case()
    }
    ledger={key:save(dest,key,value) for key,value in evidence.items()}
    sched=[s for a in amounts for s in a["schedules"]]
    summary=dict(candidate=head,python=sys.version,executable=sys.executable,sha=EXE_SHA,evidence=ledger,
                 binders=len(routes),unique_captures=len(inputs_used),window_uses=sum(inputs_used.values()),
                 physical_table_uses=sum(len(a["table_uses"]) for a in amounts),
                 distinct_table_content=len({t["raw_sha"] for tt in tables.values() for t in tt}),
                 child_subtotals=Counter(str(s["D"]) for s in sched),native_summary=Counter(
                     str(t["cross"]["diff"]) for t in terms.values() if t["cross"]),
                 all_native_exact=sum(t["native_exact"] for t in terms.values()),
                 conditional_typed_by_eta={str(eta):Counter((r["conditional"]["type"],r["exact"]).__repr__()
                    for t in terms.values() for r in t["eta"] if r["eta"]==eta) for eta in (0.0,.5)},
                 d_cells=sum(len(a["grid"]) for a in amounts), paired_archive=len(historical),
                 witness_points=len(witnesses),reference_only=sum(w["reference_only"] for w in witnesses),
                 sweep_rows=len(sweeps),attainable=sum(r["attainable"] for r in sweeps))
    (dest/"summary.json").write_bytes(json.dumps(summary,sort_keys=True,indent=2).encode()+b"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="evidence"},sort_keys=True))


if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--candidate",required=True)
    cli.add_argument("--out",type=Path,required=True)
    args=cli.parse_args()
    run(args.out,args.candidate)
