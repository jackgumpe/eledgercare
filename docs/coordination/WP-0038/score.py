"""Score two frozen D5.3 solver returns. No solver is imported or executed here."""
import argparse
import hashlib
import json
import math
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import cases, encoded, labels, observation_order


def named_finite(n, *choices):
    order = labels(n)
    signed = [[[k, v] for k, v in sorted(h.items(), key=lambda term: order.index(term[0]))] for h in choices]
    return sorted(signed, key=lambda h: (len(h), [order.index(k) for k, _ in h]))


def family(r):
    return {"support": ["B0", "B1"], "parameter": "c", "domain": "Z",
            "offset": [-r, 0], "slope": [1, 1], "excluded": sorted({0, r})}


def one_row(r, d, trusted):
    # Page three: use its five disjoint regimes and its explicitly signed formulas.
    p = {"A1": d, "B0": -r-d}
    q = {"A1": d, "B1": r+d}
    h = {"A1": -r, "T": -r-d}
    u = {"B0": -r, "T": -d}
    v = {"B1": r, "T": -d}
    if r == 0 and d == 0:
        regime, finite = "zero", []
    elif d == 0:
        regime, finite = "row_only", [{"B0": -r}, {"B1": r}, h]
    elif r == 0:
        regime, finite = "total_only", [{"T": -d}, p, q]
    elif r == -d:
        regime, finite = "opposite", [{"A1": d}, u, v]
    else:
        regime, finite = "generic", [p, q, h, u, v]
    valid = [e for e in finite if not trusted or "B0" not in e]
    return regime, (r == d == 0, named_finite(1, *valid), [family(r)] if d == 0 and not trusted else [])


# These expectations are transcribed from the named two- and three-row examples on page five.
MULTI = {
    "C3": ([6,-6], 0, [{"B1":6}, {"A1":-6,"A2":6}, {"B0":-6,"B2":-6}]),
    "C4": ([6,0], 0, [{"B0":-6}, {"A1":-6,"T":-6}, {"B1":6,"B2":6}]),
    "C5": ([6,0,0], 0, [{"B0":-6}, {"A1":-6,"T":-6}]),
    "C6": ([-6,6,-6], 0, [{"B0":6,"B2":6}, {"B1":-6,"B3":-6}]),
    "C7": ([-6,0,-6], 6, [{"A1":6,"B3":-6}, {"A3":6,"B0":6}]),
    "C8": ([-6,0,10], 6, [{"A1":6,"B3":10}]),
}


def residual(b, a, t):
    return [b[i+1]-b[i]-v for i,v in enumerate(a)], sum(a)-t


def adjudicate(row, actual):
    x, inj = row["observed"], row["injection"]
    n = len(x["amounts"])
    names = labels(n)
    measured = dict(zip(names, x["amounts"] + x["balances"] + [x["total"]], strict=True))
    trusted = x["domain"] == "TRUSTED_OPEN"
    notes = []
    def check(condition, issue):
        if not condition:
            notes.append(issue)
    keys = {"status","anchor_status","solve_skipped","rho","D","clean","finite","families"}
    if not isinstance(actual, dict) or set(actual) != keys:
        return ["incompatible answer fields"], None
    if trusted and x["balances"][0] != x["anchor"]:
        expected = dict(status="OUT_OF_DOMAIN_TRUSTED_OPENING", anchor_status="CONFLICT", solve_skipped=True,
                        rho=None, D=None, clean=False, finite=[], families=[])
        check(encoded(actual)==encoded(expected), "conflicting anchor produced residuals or candidates")
        return notes, "rejected"
    r, d = residual(x["balances"], x["amounts"], x["total"])
    for k, v in {"status":"ADMITTED","anchor_status":"VERIFIED" if trusted else "OCR_READ",
                 "solve_skipped":False,"rho":r,"D":d,"clean":not (any(r) or d)}.items():
        check(encoded(actual[k]) == encoded(v), "invalid "+k)
    signed, families = actual["finite"], actual["families"]
    def balanced(h):
        a = [measured[k]-h.get(k,0) for k in names[:n]]
        b = [measured[k]-h.get(k,0) for k in names[n:-1]]
        t = measured["T"]-h.get("T",0)
        return residual(b,a,t)==([0]*n,0) and (not trusted or b[0]==x["anchor"])
    check(all(measured[k]-inj.get(k,0)==row["truth"][k] for k in names), "scorer fixture truth")
    unique = set()
    contains = actual["clean"] and inj == {}
    indices = []
    for sol in signed:
        if not (isinstance(sol,list) and 1<=len(sol)<=2 and all(
            isinstance(t,list) and len(t)==2 and t[0] in names and type(t[1]) is int and t[1]!=0 for t in sol)):
            notes.append("invalid signed support")
            continue
        h = dict(sol)
        key = tuple(names.index(k) for k, _ in sol)
        check(len(h)==len(sol) and key==tuple(sorted(key)) and key not in unique,"duplicate or unordered finite support")
        check("B0" not in h or not trusted, "mutable trusted anchor")
        check(balanced(h), "finite hypothesis fails actual true-ledger reconstruction")
        unique.add(key)
        indices.append((len(key),key))
        contains = contains or h==inj
    check(indices == sorted(indices), "noncanonical support ordering")
    expected_families = [family(r[0])] if n==1 and not trusted and d==0 else []
    check(encoded(families)==encoded(expected_families),"affine family or exact parameter exclusions")
    # Symbolically, the true endpoint difference is unchanged by a common coefficient c;
    # the intercept -r removes the row residual. Exactly c=0 and c=r are excluded.
    if families==expected_families and families and set(inj)=={"B0","B1"}:
        c = inj["B1"]
        contains = contains or (c not in families[0]["excluded"] and inj["B0"]==c-r[0])
    check(contains, "injected hypothesis absent from complete answer")
    regime = None
    if n==1:
        regime, expected = one_row(r[0], d, trusted)
        check(encoded([actual["clean"],signed,families])==encoded(list(expected)), "signed one-row oracle")
    if row["id"] in MULTI:
        pr,pd,hyps = MULTI[row["id"]]
        expected = named_finite(n, *(h for h in hyps if not trusted or "B0" not in h))
        check((pr,pd)==(r,d) and encoded(signed)==encoded(expected) and not actual["clean"] and not families, "named support table")
    if row["id"] in ("C9a","C9b"):
        check((r,d)==([-16],6),"C9 residual")
    if row["id"]=="C1":
        check((r,d)==([0],0) and actual["clean"], "C1 invisible shift or trusted zero")
    return notes, regime


def evidence(rev, area, attempt):
    folder = f"{rev}:docs/{area}/WP-0038/evidence/{attempt}"
    def read(name):
        return subprocess.check_output(["git","cat-file","blob",folder+"/"+name])
    payload = read("outputs.jsonl")
    runtime = json.loads(read("runtime.json"))
    if hashlib.sha256(payload).hexdigest() != runtime["outputs_sha256"]:
        raise ValueError("Frozen output digest differs")
    return [json.loads(line) for line in payload.splitlines()], runtime


def timing(values):
    sort = sorted(values)
    return {"observations":len(sort),"sum_ns":sum(sort),"min_ns":min(sort),
            "median_ns":statistics.median(sort),"p95_ns":sort[math.ceil(.95*len(sort))-1],"max_ns":max(sort)}


def score(author, review, destination, author_run, review_run):
    a,at = evidence(author,"research",author_run)
    b,bt = evidence(review,"reviews",review_run)
    rows = cases()
    order = observation_order(rows)
    obs = b"".join(encoded(rows[i]["observed"])+b"\n" for i in order)
    assert hashlib.sha256(obs).hexdigest()==at["input_sha256"]==bt["input_sha256"]
    grid_inputs = {encoded(row["observed"]):row["id"] for row in rows if row["section"]=="grid"}
    assert len(grid_inputs)==288
    out = {"grid":[],"named":[]}
    checks = Counter()
    regimes = Counter()
    bad = []
    for slot,(i,x,y) in enumerate(zip(order,a,b,strict=True)):
        row = rows[i]
        checks[row["section"]+"_evaluations"] += 1
        notes = {}
        for name,run in [("support",x),("reconstruction",y)]:
            if run["exception"] is not None:
                notes[name] = ["runtime exception: "+run["exception"]]
                checks["solver_exceptions"] += 1
                continue
            try:
                issues,regime = adjudicate(row,run["answer"])
            except (KeyError,ValueError,TypeError,IndexError) as exc:
                issues,regime = ["incompatible output contract: "+str(exc)],None
            if issues:
                notes[name] = issues
            if name=="support" and regime:
                regimes[(row["section"],row["observed"]["domain"],regime)]+=1
        same = encoded(x["answer"]) == encoded(y["answer"])
        if not same:
            notes["comparison"] = ["signed outputs differ"]
        overlap = grid_inputs.get(encoded(row["observed"]))
        if row["id"]=="C9a" and not overlap or row["id"] in ("C9b","C9c") and overlap:
            notes["fixture"] = ["C9 grid membership"]
        if notes:
            bad.append({"id":row["id"],"variant":row["variant"],"failures":notes})
        result = {**row,"operator_row":slot,"generated_grid_id":overlap,"signed_outputs_equal":same,
                  "answer":x["answer"],"failures":notes,"support_ns":x["solve_ns"],"reconstruction_ns":y["solve_ns"]}
        if not same:
            result["reconstruction_answer"]=y["answer"]
        out[row["section"]].append((i,result))
    destination.mkdir(exist_ok=False,parents=True)
    digests={}
    times={}
    for group,entries in out.items():
        items=[v for _,v in sorted(entries)]
        p=destination/(group+".jsonl")
        payload=b"".join(encoded(v)+b"\n" for v in items)
        p.write_bytes(payload)
        digests[group]=hashlib.sha256(payload).hexdigest()
        times[group]={route:timing([v[route+"_ns"] for v in items]) for route in ["support","reconstruction"]}
    grid=[v for _,v in out["grid"]]
    named=[v for _,v in out["named"]]
    sizes=Counter(len(v["injection"]) for v in grid)
    assert sizes=={0:6,1:33,2:249} and len({v["id"] for v in named})==11 and len(named)==20
    for domain in ("TRUSTED_OPEN","OCR_OPEN"):
        assert {key[2] for key in regimes if key[:2]==("grid",domain)}=={"zero","row_only","total_only","opposite","generic"}
    if bad:
        status="failed"
    else:
        status="passed"
    census=Counter()
    for v in grid:
        h=v["answer"]
        if not isinstance(h,dict) or "families" not in h:continue
        category = "infinite" if h["families"] else "finite_ambiguous" if len(h["finite"])+int(h["clean"])>1 else "unique"
        census[category]+=1
    report={"status":status,"frozen_evidence":{"author":author,"review":review},"checks":dict(checks),
            "signed_output_disagreements":sum(not v["signed_outputs_equal"] for v in grid+named),
            "exceptions":checks["solver_exceptions"],"failures":bad,"grid_by_injection_size":dict(sizes),
            "grid_by_answer_cardinality":dict(census),"named_assertions":len({v["id"] for v in named}),
            "named_overlapping_grid_inputs":sum(v["generated_grid_id"] is not None for v in named),
            "one_row_by_section_domain_regime":{"/".join(k):v for k,v in sorted(regimes.items())},
            "scored_file_sha256":digests,"timing":times,"support_runtime":at,"reconstruction_runtime":bt}
    (destination/"summary.json").write_bytes((json.dumps(report,sort_keys=True,indent=2)+"\n").encode())
    print(status, "grid",len(grid),"named",len(named),"failures",len(bad))
    return int(bool(bad))


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("author")
    cli.add_argument("review")
    cli.add_argument("destination",type=Path)
    cli.add_argument("--author-run",default="run-01")
    cli.add_argument("--review-run",default="run-01")
    args=cli.parse_args()
    sys.exit(score(args.author,args.review,args.destination,args.author_run,args.review_run))
