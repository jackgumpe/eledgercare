"""Authenticate predecessor records and construct the predeclared nonphysical control schedule."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE = "b527d946d4530475a90536124ec69ec98a987a09"
ARMS = "BERFT"


def pack(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(path):
    return subprocess.check_output(["git", "cat-file", "blob", BASE + ":" + path])


def authenticated(packet, name):
    folder = f"docs/coordination/{packet}/"
    path = folder + name
    receipt = json.loads(blob(folder + "publication-receipt.json"))
    raw = blob(path)
    binding = receipt["downloaded_files"][path]
    assert len(raw) == binding["bytes"] and digest(raw) == binding["sha256"]
    assert subprocess.check_output(["git","rev-parse",BASE+":"+path]).decode().strip() == binding["git_blob"]
    return raw


def schedule():
    records, named, strata, bindings = [], {}, Counter(), {}

    def issue(label, view, arm, truth=None, **changes):
        data = dict(deepcopy(view), arm=arm)
        data.update(changes)
        records.append((label, truth, data))

    for group in ("grid", "named"):
        path = "results/" + group + ".jsonl"
        upstream = authenticated("WP-0038", path)
        distances = authenticated("WP-0039", path)
        bindings[group] = dict(wp38_sha256=digest(upstream), wp39_sha256=digest(distances))
        indexed = {digest(line):json.loads(line) for line in upstream.splitlines()}
        for line in distances.splitlines():
            item = json.loads(line)
            old = indexed.pop(item["upstream_line_sha256"])
            assert old["id"] == item["id"] and old["variant"] == item["variant"]
            names = item["mutable"]
            o = old["observed"]
            observed = o["amounts"] + o["balances"][int(o["domain"]=="TRUSTED_OPEN"):] + [o["total"]]
            def vec(errors):
                return [x-errors.get(j,0) for j,x in zip(names,observed,strict=True)]
            a = old["answer"]
            points = ([observed] if a["clean"] else []) + [vec(dict(e)) for e in a["finite"]]
            family = None
            for f in a["families"]:
                assert family is None and f["domain"] == "Z" and f["parameter"] == "c"
                slopes = dict(zip(f["support"],f["slope"],strict=True))
                family = dict(h=vec(dict(zip(f["support"],f["offset"],strict=True))),
                              s=[-slopes.get(j,0) for j in names],excluded=f["excluded"])
            truth = [old["truth"][j] for j in names]
            view = dict(names=names, points=points, line=family, dist=item["distance_by_mask"],
                        status=a["status"], areas=[100]*len(names), read_status="OK", y=truth)
            if group == "grid" and item["k"]:
                strata[(item["n"],item["domain"],view["dist"][-1])] += 1
            if group == "named":
                named[item["id"],item["variant"]] = view
            for arm in ARMS:
                issue([group,item["id"],item["variant"],arm],view,arm,truth)
        assert not indexed

    def add(label, view, arm, truth=None, **changes):
        issue(["control",label,"constructed",arm],view,arm,truth,**changes)

    c1,c2,c9a,c9b = (named[k] for k in (("C1","ocr"),("C2","ocr"),("C9a","ocr"),("C9b","trusted")))
    for label, bal, constants in (("tie", [100,112],[11,11]),("tie_lost",[100,112],[11,12]),
                                 ("exact_active",[100,111],[11,12]),("two_shared",[100,111],[12,12])):
        for arm in "FT":
            add("c1_"+label,c1,arm,c1["y"],y=[constants[0],*bal,constants[1]])
    for label, opening, closing in (("hole0",106,117),("hole6",100,111),("allowed",105,116)):
        for arm in "RFT":
            add("c2_"+label,c2,arm,c2["y"],y=[11,opening,closing,11])
    # C9a two distance-two triples, with constructed area differences or equal pixel costs.
    for label, areas, y in (("amount",[1,2,2,5],[1,100,111,11]),
                            ("total",[5,2,2,1],[11,100,111,1]),
                            ("area_equal",[2,2,2,2],[1,100,111,11])):
        for arm in "ERFT":
            add("c9a_"+label,c9a,arm,c9a["y"],areas=areas,y=y)
    for label,y in (("hybrid",[11,100,121,11]),("exact",[11,100,111,11]),
                    ("active_empty",[33,333,444,55])):
        for arm in "FT":
            add("c9a_"+label,c9a,arm,c9a["y"],y=y)
    for arm in ARMS:
        add("c9b_corrupt",c9b,arm,c9b["y"],y=[11,101,11])
        # B abstains; E selects A1 (ties by equal area/mask) and resolves the rival literally.
        add("e_only",c9b,arm,c9b["y"],y=[1,111,11])
        add("outside",c9b,arm,[22,122,22],y=[11,111,11])
    for label,y in (("outside_shared_empty",[11,100,112,12]),("outside_tie",[11,100,112,11])):
        for arm in "FT":
            add(label,c1,arm,[13,100,113,13],y=y)
    c6=named["C6","ocr"]
    for arm in "FT":
        y=c6["y"].copy()
        y[3]+=1
        if arm=="T":
            y[0]+=1
        add("separate_views",c6,arm,c6["y"],y=y)
    for status in ("MISSING","UNPARSEABLE","UNBOUND","FAILED"):
        for arm in "ERFT":
            add("return_"+status,c9b,arm,c9b["y"],read_status=status,y=[None]*3)
    for label,status,points in (("admitted_empty","ADMITTED",[]),("unknown","UNKNOWN",[]),
                                ("duplicate","ADMITTED",[[0,0],[0,0]])):
        add(label,dict(c9b,names=["A","B"],line=None,points=points,areas=[1,1],dist=[None]*4,
                       y=[0,0],status=status),"R")
    guard=dict(c9b,names=["A","B"],line=None,points=[[1,0],[0,0]],areas=[1,1],dist=[0,1,0,1],y=[1,0])
    for arm in "RFT":
        add("malformed_distance_one",guard,arm)
    simple=dict(c9b,names=["x","z"],areas=[1,1],points=[],dist=[0,1,1,2],
                line=dict(h=[0,0],s=[2,2],excluded=[]),y=[3,4])
    for label,q,excluded in (("divisibility",3,[]),("excluded",3,[2]),("generic_infinite",1,[])):
        add(label,dict(simple,line=dict(simple["line"],excluded=excluded)),"H",q=q,radius=1)
    add("constant_slope",dict(simple,line=dict(h=[0,7],s=[2,0],excluded=[]),dist=[0,1,0,1],
                              y=[-4,8]),"H",q=3,radius=1)
    add("finite_line_duplicate",dict(simple,points=[[4,4],[4,4]],y=[4,4]),"H",q=3,radius=1)
    records.sort(key=lambda t:digest(b"WP-0040/shuffle/"+pack(t[0])))
    assert len({tuple(label) for label,_,_ in records})==len(records)
    return records, bindings, strata


def input_bytes(records):
    return b"".join(pack(v)+b"\n" for _,_,v in records)


if __name__ == "__main__":
    rec,bindings,strata=schedule()
    data=input_bytes(rec)
    with Path(sys.argv[1]).open("xb") as out:
        out.write(data)
    print(len(rec),digest(data),bindings,sorted(strata.items()))
