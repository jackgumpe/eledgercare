"""Compare independent raw CPU returns and verify the preregistered decision/measurement controls."""
from collections import Counter
import gzip
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from fixtures import digest, input_bytes, pack, schedule
from protocol import audit_protocol


def fetch(rev, area):
    prefix=f"{rev}:docs/{area}/WP-0040/evidence/run-01/"
    raw=subprocess.check_output(["git","cat-file","blob",prefix+"outputs.jsonl.gz"])
    runtime=json.loads(subprocess.check_output(["git","cat-file","blob",prefix+"runtime.json"]))
    assert digest(raw)==runtime["outputs_sha256"]
    return [json.loads(x) for x in gzip.decompress(raw).splitlines()],runtime


def member(truth,v):
    if truth is None:
        return None
    if truth in v["points"]:
        return True
    line=v["line"]
    if not line:
        return False
    i=next(j for j,s in enumerate(line["s"]) if s)
    c,rem=divmod(truth[i]-line["h"][i],line["s"][i])
    return rem==0 and c not in line["excluded"] and all(h+c*s==x for x,h,s in zip(truth,line["h"],line["s"]))


def validate(label,truth,v,a):
    group,id,variant,arm=label
    status,q=a["status"],a["q"]
    assert set(a)==set("status q d ties points line count diag".split())
    if v["status"]!="ADMITTED" or (not v["points"] and v["line"] is None):
        expected={"ADMITTED":"ADMITTED_EMPTY","OUT_OF_DOMAIN_TRUSTED_OPENING":"OUT_OF_DOMAIN_TRUSTED_OPENING"}.get(v["status"],"UNSUPPORTED")
        assert status==expected and q is None and a["count"] is None
        return
    full=len(v["dist"])-1
    if v["dist"][full] is None and arm!="H":
        assert status=="FIRST_PASS_SINGLETON" and q==0 and a["count"]==1 and a["points"]==v["points"][:1]
        return
    if arm in "RFT" and v["dist"][full]<2:
        assert status=="INSUFFICIENT_SEPARATION" and q is None and a["count"] is None
        return
    if arm=="B":
        assert status=="FIRST_PASS_AMBIGUOUS" and q==0 and a["count"] is None
        return
    if arm in "ER":
        threshold=1 if arm=="E" else min(3,v["dist"][full])
        eligible=[i for i,d in enumerate(v["dist"]) if d>=threshold]
        size=min(i.bit_count() for i in eligible)
        ties=[i for i in eligible if i.bit_count()==size]
        assert a["ties"]==ties
        area=lambda m:sum(x for j,x in enumerate(v["areas"]) if m>>j&1)
        assert q==min(ties,key=lambda m:(area(m),m))
    else:
        assert q==(v["q"] if arm=="H" else full) and a["ties"]==[]
    assert a["d"]==v["dist"][q]
    if v["read_status"]!="OK":
        assert status==v["read_status"] and a["count"] is None
        return
    radius=v["radius"] if arm=="H" else int(arm!="E")
    for point in a["points"]:
        assert member(point,v) and sum(x!=y for j,(x,y) in enumerate(zip(point,v["y"])) if q>>j&1)<=radius
    assert a["points"]==[list(t) for t in sorted(set(map(tuple,a["points"])))]
    assert a["count"]==("infinite" if a["line"] else len(a["points"]))
    assert status==("RESOLVED" if a["count"]==1 else "INCONSISTENT" if a["count"]==0 else "AMBIGUOUS")
    if group!="control":
        assert status=="RESOLVED" and a["points"]==[truth]
    elif id.startswith("c1_"):
        mc,amin,ac,fc={"tie":(0,1,2,2),"tie_lost":(1,1,2,0),"exact_active":(1,0,1,1),
                       "two_shared":(2,0,1,0)}[id[3:]]
        d=a["diag"]
        assert (d["mc"],d["min_active"],d["active_count"],a["count"])==(mc,amin,ac,fc)
        assert not d["exact_full"]
    elif id.startswith("c2_"):
        assert a["points"]==[v["y"]]
    elif id in ("c9a_amount","c9a_total","c9a_area_equal"):
        if arm=="R":
            assert a["ties"]==[7,14] and q==(14 if id=="c9a_total" else 7) and a["count"]==2
        if arm in "FT":
            assert a["points"]==[truth]
    elif id in ("c9a_hybrid","c9a_exact","c9a_active_empty"):
        assert a["count"]=={"c9a_hybrid":2,"c9a_exact":1,"c9a_active_empty":0}[id]
        if id=="c9a_active_empty":
            assert a["diag"]["min_active"]>1
    elif id=="c9b_corrupt" and arm in "RFT":
        assert a["points"]==[[11,111,11]]
    elif id=="e_only":
        assert a["points"]==([[1,101,1]] if arm=="E" else [truth])
    elif id=="outside":
        assert member(truth,v) is False and a["points"]==[[11,111,11]]
    elif id in ("outside_shared_empty","outside_tie"):
        assert member(truth,v) is False and a["count"]==(0 if id.endswith("empty") else 2)
    elif id=="separate_views":
        mc=0 if arm=="F" else 1
        d=a["diag"]
        assert (d["mc"],d["min_active"],d["active_count"],a["count"],d["exact_full"])==(mc,1,1,1-mc,False)
    elif arm=="H" and id=="helper_singleton":
        point=v["points"][0]
        misses=sum(point[j]!=v["y"][j] for j in range(len(point)) if q>>j&1)
        assert a["points"]==([point] if misses<=radius else [])
    elif arm=="H":
        expected={"divisibility":[[4,4]],"excluded":[],"generic_infinite":[],
                  "constant_slope":[[-4,7]],"finite_line_duplicate":[[4,4]]}
        assert a["points"]==expected[id]
        assert a["line"]==(v["line"] if id=="generic_infinite" else None)
    if arm in "FT":
        d=a["diag"]
        assert d["full_count"]==a["count"]
        if d["mc"]==0:
            assert d["active_count"]==d["full_count"]
        elif d["mc"]==1:
            assert d["full_count"]==int(d["min_active"]==0)
        else:
            assert d["full_count"]==0
        assert d["exact_full"]==(d["mc"]==0 and d["min_active"]==0)


def main(author,review,out):
    schedule_rows,binding,strata=schedule()
    routes=[fetch(author,"research"),fetch(review,"reviews")]
    input_sha=digest(input_bytes(schedule_rows))
    assert all(t["input_sha256"]==input_sha for _,t in routes)
    out.mkdir(exist_ok=False)
    errors=[]
    results=[]
    empty_cause=Counter()
    for i,((label,truth,v),a,b) in enumerate(zip(schedule_rows,routes[0][0],routes[1][0],strict=True)):
        record=dict(label=label,origin="constructed CPU return",operator_row=i,view_sha256=digest(pack(v)),
                    read_status=v["read_status"],returned=v["y"],mutable=v["names"],areas_constructed=v["areas"],
                    synthetic_truth=truth,truth_in_candidates=member(truth,v),author_ns=a["plan_ns"],review_ns=b["plan_ns"])
        try:
            assert a["exception"] is None and b["exception"] is None,"runtime exception"
            assert pack(a["answer"])==pack(b["answer"]),"independent routes disagree"
            answer=a["answer"]
            validate(label,truth,v,answer)
            record["decision"]=answer
            record["correctness"]=None if truth is None else ("correct" if answer["points"]==[truth] and answer["count"]==1
                      else "wrong" if answer["count"]==1 else "withheld")
            if answer["diag"] and answer["count"]==0:
                d=answer["diag"]
                cause="shared_removed_last" if d["min_active"]<=1 else "active_already_empty"
                record["empty_cause"]=cause
                empty_cause[(label[3],str(record["truth_in_candidates"]),cause)]+=1
        except (AssertionError,KeyError,TypeError,ValueError) as exc:
            record.update(error=repr(exc),author=a,review=b)
            errors.append(label)
        results.append(record)
    assert sorted((n,dom,k) for (n,dom,d),k in strata.items() if d==4)==[(2,"OCR_OPEN",6),(2,"TRUSTED_OPEN",4),(3,"OCR_OPEN",16),(3,"TRUSTED_OPEN",8)]
    dist={d:sum(k for (_,_,x),k in strata.items() if x==d) for d in (2,3,4)}
    assert dist=={2:23,3:155,4:34}
    protocol=audit_protocol()
    stats={}
    for group in ("grid","named","control"):
        rr=sorted((r for r in results if r["label"][0]==group),key=lambda r:r["label"])
        (out/(group+".jsonl")).write_bytes(b"".join(pack(r)+b"\n" for r in rr))
        stats[group]=dict(calls=len(rr),outcomes=dict(Counter(r.get("decision",{}).get("status","ERROR") for r in rr)))
    doc=dict(source="Constructed CPU controls only",observed_calls_per_route=len(results),route_revisions=[author,review],
             input_sha256=input_sha,bindings=binding,exceptions=[t["exceptions"] for _,t in routes],
             timings=[t for _,t in routes],groups=stats,full_distances=dist,
             d4_by_2ocr_2trusted_3ocr_3trusted=[6,4,16,8],shared_diagnostics=[[*k,val] for k,val in sorted(empty_cause.items())],
             failed=errors,protocol_controls=protocol)
    (out/"summary.json").write_bytes((json.dumps(doc,sort_keys=True,indent=2)+"\n").encode())
    print(len(results),stats,"failures",errors[:20])
    return bool(errors)


if __name__=="__main__":
    sys.exit(main(sys.argv[1],sys.argv[2],Path(sys.argv[3])))
