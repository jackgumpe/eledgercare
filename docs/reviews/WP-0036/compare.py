"""Align independently frozen evidence. This entry point never instantiates a model or replays data."""
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

A="c63d6f034209bac5b9b1b66488587e527aaa36f7:docs/research/WP-0036/evidence/attempt-02/"
R="f8bda47a25d8c5170240a68ea5b72a11478b3d1b:docs/reviews/WP-0036/evidence/"


def data(prefix,name):
    raw=subprocess.check_output(["git","cat-file","blob",prefix+name+".json.gz"])
    return json.loads(gzip.decompress(raw))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def canonical(x):
    if isinstance(x,bool) or x is None or isinstance(x,str):
        return x
    if isinstance(x,(int,float)):
        # All common integers, including cents and IDs-by-index, are exactly representable here.
        assert not isinstance(x,int) or abs(x)<=2**53
        return {"f64le":struct.pack("<d",x).hex()}
    if isinstance(x,(tuple,list)):
        return list(map(canonical,x))
    return {k:canonical(v) for k,v in sorted(x.items())}


def encoded(x):
    return json.dumps(canonical(x),sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()


def full(w,side):
    if w is None:
        return None
    if side=="A":
        return [w["vector_sha256"],w["full_sha256"],w["valid"],w["text"] or "",w["confidence"],
                w["text_source"]["ptr"] if w["text_source"] else None]
    return [w["vector"],w["slot"],w["valid"],w["text"],w["confidence"],w["declaration"]]


def decode(f,side):
    if side=="A":
        return [f["decision"],f["dmin"],f["margin"],f["ranking"],f["G1"],f["G2"],f["G3"]]
    return [f["choice"],f["dmin"],f["margin"],[[s,d] for d,s in f["ranks"]],f["g1"],f["g2"],f["g3"]]


def compare():
    a=lambda name:data(A,name)
    r=lambda name:data(R,name)
    projected={"A":defaultdict(dict),"R":defaultdict(dict)}
    def add(side,group,key,value):
        collection=projected[side][group]
        k=json.dumps(key,separators=(",",":"),default=str)
        assert k not in collection,(group,key)
        collection[k]=value

    inputs=r("custody")
    route={t["binder"]:t for t in inputs["routes"]}
    author=a("inputs")
    for t in author["logical"]:
        add("A","routes",t["binder"],[t["task"],t["pair"],t["horizon"],t["tags"]])
    for bid,t in route.items():
        add("R","routes",bid,[t["task"],t["pair"],t["horizon"],t["tags"]])
    for c in author["captures"]:
        add("A","captures",c["tag"],[sorted(c["members"]),
            [c["members"][n] for n in ("receipt.json","metadata.json","pooled.f32","capture.json","native.json")],
            c["n_emitted_ids"],c["n_spans"]])
    for tag,c in inputs["surfaces"].items():
        add("R","captures",tag,[c["members"],c["triplet"]+[c["capture_sha"],c["native_sha"]],c["tokens"],c["pooled_shape"][0]])
    for x in a("raw-vs-native"):
        add("A","raw_parsed_differences",[x["tag"],x["span"]],[x["byte_range"],x["raw_sha256"],x["raw"],x["native"]])
    for x in r("raw-parse"):
        if x["raw"]!=x["parsed"]:
            add("R","raw_parsed_differences",[x["tag"],x["index"]],[x["range"],x["raw_sha"],x["raw"],x["parsed"]])

    terms=r("terminal")
    streams={t["binder"]:t for t in r("streams")}
    for x in a("E"):
        key=[x[k] for k in ("model","horizon","binder","phase","step")]
        add("A","E",key,[full(x["witness"],"A"),x["ptr"],x["depth"],x["events"],bool(x["excluded"]),x["arm"]])
    for x in r("archival-witnesses"):
        bid=x["binder"]
        n=x["write"]
        if x["phase"]=="initial":
            ptr,depth,ev=None,0,[]
        elif x["phase"]=="native_pre" or x["reference_only"]:
            ptr,depth,ev=terms[bid]["ptr"],terms[bid]["active_depth"],["TARGET"]
        else:
            obs=streams[bid]["spans"][n-1]
            ptr,depth,ev=obs["ptr"],obs["depth"],obs["kinds"]
        key=[x[k] for k in ("model","horizon","binder","phase","write")]
        add("R","E",key,[full(x["witness"],"R"),ptr,depth,ev,x["reference_only"],x["member"]])
    control_points=a("E-controls")
    for bid,seq in control_points.items():
        assert seq[0]["phase"]=="initial" and seq[0]["step"]==0
        for x in seq[1:]:
            add("A","safety_stream",[bid,x["step"]],[full(x["witness"],"A"),x["depth"],x["source"]["ptr"],x["events"]])
    for bid,t in streams.items():
        if t["full_no_target"]:
            for x in t["spans"]:
                add("R","safety_stream",[bid,x["write"]],[full(x["witness"],"R"),x["depth"],x["ptr"],x["kinds"]])
    for x in a("F"):
        bid=x["binder"]
        key=[bid,float(x["eta"])]
        add("A","F",key,[x["native"],x["typed"],x["expected"],x["scope"],x["correct"],x["target"],x["historical_target"]])
        for name,f in x["fields"].items():
            add("A","F_fields",key+[name],[f["raw"],f["directory"],f["error"],decode(f,"A"),f["source"]["ptr"],f["source"]["raw_slice_sha256"]])
    for bid,t in terms.items():
        for e in t["eta"]:
            key=[bid,e["eta"]]
            add("R","F",key,[t["native"],e["conditional"],t["truth"],t["scope"],e["exact"],t["ptr"],route[bid]["target"]])
            for j,name in enumerate(("owner","unit")):
                f=e["fields"][name]
                if f is not None:
                    src=t["attribute_sources"][j]
                    add("R","F_fields",key+[name],[f["text"],f["candidates"],e[name+"_error"],decode(f,"R"),src["ptr"],src["rawsha"]])
    for x in a("F3"):
        add("A","F3",[x["pair"],float(x["eta"])],[x[k] for k in
            ("g","e_alpha","e_beta","Delta_alpha","Delta_beta","mu","delta","alpha_bounds","beta_bounds","mu_bound","delta_lower","checks")])
    for x in r("twins"):
        g=x["g"]
        aa,bb=(x["members"][n] for n in ("Alder","Cedar"))
        ea,eb=aa["error"],bb["error"]
        add("R","F3",[x["pair"],x["eta"]],[g,ea,eb,aa["signed"],bb["signed"],x["mu"],x["delta"],[g-2*ea,g],[-g,-g+2*eb],max(ea,eb),2*g-2*(ea+eb),x["all_four_bounds"]])
    for side,rows in (("A",a("F-sweep")),("R",r("sweep"))):
        for x in rows:
            key=[x["binder"],float(x["eta"]),x["path"],x["k"]]
            truth=x["truth"]
            sites=x["eligible_positions"] if side=="A" else x["positions"]
            source=x["source"] if side=="A" else x["observed"]
            v=[x["attainable"],source,x["rival"].casefold(),truth,sites]
            if x["attainable"]:
                if side=="A":
                    v+= [x["changed"],x["literal"],x["actual_cost"],x["error"],x["progress"],x["nearest_correct"],
                         x["accepted_correct"],x["under_half"],x["decision"],x["margin"],x["ranking"],x["G1"],x["G2"],x["G3"],x["reasons"]]
                else:
                    d=decode(x["field"],"R")
                    v+=[sites[:x["actual_edits"]],x["modified"],x["cost"],x["error"],x["progress"],x["nearest_correct"],
                        x["accepted_correct"],x["error"]<x["field"]["dmin"]/2,d[0],d[2],d[3],*d[4:7],x["field"]["reason"]]
            add(side,"sweep",key,v)

    phys=r("physical-tables")
    malformed=[]
    for x in a("D"):
        bid=x["binder"]
        add("A","D_binder",bid,[x["grids"],x["eligible_child_interior_amount_rows"],x["final_scope"]])
        for t in x["tables"]:
            wi,p,i=t["ptr"]
            physical=next(s for s in phys[t["tag"]] if s["index"]==i)
            if not physical["complete"]:
                malformed.append(dict(binder=bid,tag=t["tag"],ptr=t["ptr"],sha=t["raw_sha256"],
                                      html_parser=t["rows"],sensor_row_records=physical["rows"]))
            key=[bid,wi,t["tag"],p,i]
            add("A","physical_tables",key,[t["raw_range"],t["raw_sha256"],t["observed_header"],t["balance_indices"],
                                          t["total_literal"],t["explicit_balance_chain"],t["D"],t["rho"]])
            if physical["complete"]:
                add("A","complete_table_rows",key,t["rows"])
        for s in x["child_subtotals"]:
            add("A","child_subtotal",bid,[s["ptr"],s["literal"],s["minor"],s["raw_slice_sha256"],s["body"],s["D"],
                                         [(u["unit"],u["header"],u["amount_index"]) for u in s["body_sources"]]])
        for m in x["maintenance"]:
            add("A","maintenance",bid,[m["ptr"],m["target_literal"],m["target_minor"],m["subtotal_ptr"],m["subtotal_minor"],m["residual"]])
    for x in r("arithmetic"):
        bid=x["binder"]
        add("R","D_binder",bid,[x["grid"],sum(s["interior_rows"] for s in x["schedules"] if s["D"]==0),terms[bid]["scope"]])
        for wi,tag,idx,hs in x["table_uses"]:
            t=next(s for s in phys[tag] if s["index"]==idx)
            key=[bid,wi,tag,t["page"],idx]
            assert not t["total_rows"] and not t["balance_columns"]
            add("R","physical_tables",key,[t["bytes"],hs,t["header"][0] if t["header"] else None,t["balance_columns"],None,None,None,None])
            if t["complete"]:
                add("R","complete_table_rows",key,[o["fields"] for o in t["rows"]])
        for s in x["schedules"]:
            if s["D"] is not None:
                t=s["subtotal"]
                wi,tag,p,i=t["ptr"]
                add("R","child_subtotal",bid,[[wi,p,i],t["literal"],t["value"],t["raw_sha"],[b["amount"] for b in s["body"]],s["D"],
                                             [(b["unit"],b["header"]["value"],b["col"]) for b in s["body"]]])
        t=terms[bid]
        if t["cross"]:
            c=t["cross"]
            add("R","maintenance",bid,[t["ptr"],c["observed"],c["left"],c["subtotal"]["ptr"],c["right"],c["diff"]])

    for x in a("A"):
        add("A","A",[x["case"],float(x["eta"])],[x[k] for k in ("vocab","logits","top","runner","rivals","ordinary_f64le","conf_f64le","score_f64le","theoretical_strict","observed_strict")])
    review_a=r("synthetic-A")
    for x in review_a["token_cases"]:
        v=[x[k] for k in ("tokens","logits","top","second","rivals","m","conf","sigma","strict_real","strict_fp")]
        add("R","A",[x["case"],x["eta"]],["+inf" if y=="+infinity" else y for y in v])
    for x in a("A-quantiles"):
        add("A","quantile",[x["mode"],x["alpha"]],[x[k] for k in ("values","n","k","threshold_f64le","strict_escape","ties_escape")])
    for x in review_a["conformal"]:
        cut=x["cut"] if x["cut"]!="+infinity" else "+inf"
        add("R","quantile",["max" if x["rule"]=="document_max" else "selected",x["alpha"]],
            [x["values"],x["n"],x["k"],cut,x["strict_escapes"],x["tie_escapes"]])

    report={}
    mismatches=[]
    assert set(projected["A"])==set(projected["R"])
    for group in sorted(projected["A"]):
        aa,rr=projected["A"][group],projected["R"][group]
        keys=sorted(set(aa)|set(rr))
        unequal=[k for k in keys if k not in aa or k not in rr or encoded(aa[k])!=encoded(rr[k])]
        for k in unequal:
            mismatches.append(dict(group=group,key=k,author=aa.get(k),independent=rr.get(k)))
        report[group]=dict(keys=len(keys),unequal=len(unequal),author_sha=sha(encoded(aa)),reviewer_sha=sha(encoded(rr)))
    return dict(author=A.split(":")[0],reviewer=R.split(":")[0],groups=report,differences=mismatches,
                incomplete_table_diagnostics=malformed)


if __name__=="__main__":
    findings=compare()
    with Path(sys.argv[1]).open("x",encoding="utf8",newline="\n") as out:
        json.dump(findings,out,sort_keys=True,indent=2)
        out.write("\n")
    print("groups",len(findings["groups"]),"mismatches",len(findings["differences"]))
