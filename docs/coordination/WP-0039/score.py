"""Verify two immutable planner returns and publish exact ties and minimality certificates."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from admit import admitted, batch, encoded, sha

# Advisory edition 05, page 1. Columns: historical unique/multifinite/infinite, k=1, k=2.
PREDICTED = {
    "1/OCR_OPEN":[0,16,7,2,21], "1/TRUSTED_OPEN":[1,12,0,12,0],
    "2/OCR_OPEN":[4,48,0,30,18], "2/TRUSTED_OPEN":[9,27,0,24,3],
    "3/OCR_OPEN":[33,60,0,42,18], "3/TRUSTED_OPEN":[29,42,0,36,6],
}


def fetch(rev, area, run):
    prefix = rev + ":docs/"+area+"/WP-0039/evidence/"+run+"/"
    read = lambda filename: subprocess.check_output(["git","cat-file","blob",prefix+filename])
    raw = read("outputs.jsonl.gz")
    rt = json.loads(read("runtime.json"))
    if sha(raw) != rt["outputs_sha256"]:
        raise ValueError("Frozen output and operator receipt differ")
    return [json.loads(line) for line in gzip.decompress(raw).splitlines()],rt


def material(view):
    ans = view["answer"]
    obs = tuple(view["observed"])
    def subtract(errors):
        return tuple(x-errors.get(col,0) for col,x in zip(view["mutable"],obs,strict=True))
    points = [obs] if ans["clean"] else []
    for changes in ans["finite"]:
        points.append(subtract(dict(changes)))
    if not ans["families"]:
        return points,None
    line, = ans["families"]
    assert line["domain"]=="Z" and line["parameter"]=="c"
    bias = subtract(dict(zip(line["support"],line["offset"],strict=True)))
    slopes = dict(zip(line["support"],line["slope"],strict=True))
    return points,(bias,tuple(-slopes.get(col,0) for col in view["mutable"]),frozenset(line["excluded"]))


def geometry(points,line):
    def diff(p,q):
        return sum(1<<i for i,(a,b) in enumerate(zip(p,q,strict=True)) if a!=b)
    result = {diff(p,q) for i,p in enumerate(points) for q in points[i+1:]}
    if line is not None:
        base,slope,excluded = line
        moving = sum(1<<i for i,x in enumerate(slope) if x)
        result.add(moving)
        for p in points:
            generic = moving | diff(base,p)
            # Each varying cell has at most one exact equality root. Only an integral,
            # nonexcluded root can remove bits, all with the very same parameter.
            cancellations = {}
            for i,(x,b,m) in enumerate(zip(p,base,slope,strict=True)):
                if m:
                    c,rem = divmod(x-b,m)
                    if rem==0 and c not in excluded:
                        cancellations[c] = cancellations.get(c,0) | (1<<i)
            result.add(generic)
            result.update(generic & ~bits for bits in cancellations.values())
    result.discard(0)
    return sorted(result)


def vector(ref, points, line):
    if set(ref)=={"i"} and type(ref["i"]) is int and 0<=ref["i"]<len(points):
        return points[ref["i"]]
    if set(ref)=={"c"} and type(ref["c"]) is int and line is not None and ref["c"] not in line[2]:
        return tuple(b+m*ref["c"] for b,m in zip(line[0],line[1],strict=True))
    raise ValueError(f"invalid candidate reference {ref}")


def cells(names,mask):
    return [name for i,name in enumerate(names) if mask & (1<<i)]


def audit(view,outcomes):
    ans = view["answer"]
    status = {"OUT_OF_DOMAIN_TRUSTED_OPENING":"OUT_OF_DOMAIN_TRUSTED_OPENING"}.get(ans["status"])
    if ans["status"]=="ADMITTED":
        status = "OK" if (ans["clean"] or ans["finite"] or ans["families"]) else "ADMITTED_EMPTY"
    if status is None:
        status="UNSUPPORTED"
    names=view["mutable"]
    if status!="OK":
        exact={"status":status,"k":None,"minima":[],"checks":[]}
        assert all(encoded(r)==encoded(exact) for r in outcomes), "nonplanning status conflated"
        if status=="OUT_OF_DOMAIN_TRUSTED_OPENING":
            assert ans["anchor_status"]=="CONFLICT" and ans["solve_skipped"] and ans["rho"] is None and ans["D"] is None
        return {"status":status,"k":None,"minimum_sets":[],"minimum_masks":[],"checked_masks":0,
                "smaller_collisions":[],"witnesses_verified":0,"distance_by_mask":[]}
    points,line=material(view)
    supports=geometry(points,line)
    distances=[min(((q&e).bit_count() for e in supports),default=None) for q in range(1<<len(names))]
    minimum=min(q.bit_count() for q,d in enumerate(distances) if d!=0)
    ties=[q for q,d in enumerate(distances) if q.bit_count()==minimum and d!=0]
    smaller={}
    verified=0
    for route,result in zip(("support","projection"),outcomes,strict=True):
        assert set(result)=={"status","k","checks","minima"} and result["status"]==status
        assert type(result["k"]) is int and result["k"]==minimum and encoded(result["minima"])==encoded(ties), "minimum/tie difference"
        for q,(d,check) in enumerate(zip(distances,result["checks"],strict=True)):
            assert set(check)=={"d","pair"} and encoded(check["d"])==encoded(d), f"distance differs at mask {q}"
            if d!=0:
                assert check["pair"] is None
                continue
            left,right=check["pair"]
            x,y=vector(left,points,line),vector(right,points,line)
            assert x!=y and all(x[i]==y[i] for i in range(len(x)) if q&(1<<i)), f"invalid witness at {q}"
            verified+=1
            if q.bit_count()<minimum:
                rec=smaller.setdefault(q,{"mask":q,"cells":cells(names,q)})
                rec[route]={"pair":[left,right],"common_values":[x[i] for i in range(len(x)) if q&(1<<i)]}
    assert set(smaller)=={q for q in range(len(distances)) if q.bit_count()<minimum}
    return {"status":status,"k":minimum,"minimum_masks":ties,"minimum_sets":[cells(names,q) for q in ties],
            "checked_masks":len(distances),"distance_by_mask":distances,"difference_support_masks":supports,
            "smaller_collisions":list(smaller.values()),"witnesses_verified":verified,
            "candidate_category":"infinite" if line else "unique" if len(set(points))==1 else "multi_finite"}


def score(author,review,dest,author_run,review_run):
    route1,t1=fetch(author,"research",author_run)
    route2,t2=fetch(review,"reviews",review_run)
    inputs,custody=admitted()
    assert sha(batch(inputs))==t1["input_sha256"]==t2["input_sha256"]
    groups={"grid":[],"named":[],"interface":[]}
    issues=[]
    for i,((label,view),a,b) in enumerate(zip(inputs,route1,route2,strict=True)):
        row={**label,"operator_row":i,"mutable":view["mutable"],"input_record_sha256":sha(encoded(view)),
             "rho":view["answer"]["rho"],"D":view["answer"]["D"],"anchor_status":view["answer"]["anchor_status"],
             "support_ns":a["plan_ns"],"projection_ns":b["plan_ns"]}
        try:
            assert not a["exception"] and not b["exception"], "planner threw an exception"
            row.update(audit(view,[a["answer"],b["answer"]]))
        except (AssertionError,KeyError,TypeError,IndexError,ValueError) as exc:
            row.update(status="AUDIT_FAILURE",diagnostic=str(exc),support_return=a,projection_return=b)
            issues.append([label,str(exc)])
        groups[label["section"]].append(row)
    dest.mkdir(exist_ok=False)
    digests={}
    totals={}
    for group,rows in groups.items():
        rows.sort(key=lambda r:(r["id"],r["variant"]))
        raw=b"".join(encoded(r)+b"\n" for r in rows)
        (dest/(group+".jsonl")).write_bytes(raw)
        digests[group]=sha(raw)
        totals[group]={"calls":len(rows),"by_status":dict(Counter(r["status"] for r in rows)),
                       "by_k":dict(Counter(str(r["k"]) for r in rows if r["status"]=="OK")),
                       "masks_per_route":sum(r.get("checked_masks",0) for r in rows),
                       "minimum_sets_per_route":sum(len(r.get("minimum_sets",[])) for r in rows),
                       "smaller_set_witnesses_per_route":sum(len(r.get("smaller_collisions",[])) for r in rows),
                       "all_collision_witnesses_both_routes":sum(r.get("witnesses_verified",0) for r in rows)}
    strata={}
    for key,prediction in PREDICTED.items():
        rows=[r for r in groups["grid"] if str(r["n"])+"/"+r["domain"]==key]
        c=Counter(r.get("candidate_category") for r in rows)
        actual=[c["unique"],c["multi_finite"],c["infinite"],sum(r.get("k")==1 for r in rows),sum(r.get("k")==2 for r in rows)]
        strata[key]={"grid_cases":len(rows),"prediction":prediction,"observed":actual,
                     "difference":[a-p for a,p in zip(actual,prediction,strict=True)]}
    score={"status":"passed" if not issues else "failed","audit_failures":issues,"input_hashes":custody,
           "output_hashes":digests,"role_evidence":{"support":author,"projection":review},"runtime":{"support":t1,"projection":t2},
           "totals":totals,"named_assertions":len({r["id"] for r in groups["named"]}),
           "named_grid_overlaps":sum(r["generated_grid_id"] is not None for r in groups["named"]),
           "stratum_column_order":["unique","multi_finite","infinite","k1","k2"],"strata":strata}
    (dest/"summary.json").write_bytes((json.dumps(score,sort_keys=True,indent=2)+"\n").encode())
    print(score["status"],len(issues),"failures",totals)
    return int(bool(issues))


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("author")
    cli.add_argument("review")
    cli.add_argument("dest",type=Path)
    cli.add_argument("--author-run",default="run-01")
    cli.add_argument("--review-run",default="run-01")
    args=cli.parse_args()
    sys.exit(score(args.author,args.review,args.dest,args.author_run,args.review_run))
