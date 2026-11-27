"""Record observed CLI results and independently reconcile frozen comparison omissions."""
from hashlib import sha256
import json
from pathlib import Path
import sys


def main(plan,supplement,equivalence,destination):
    read=lambda p: json.loads(p.read_bytes())
    readl=lambda p: [json.loads(x) for x in p.read_bytes().splitlines()]
    sem=readl(plan/"semantic.jsonl")
    run={r["case_id"]:r for r in readl(plan/"run.jsonl")}
    extras={r["case"]:r for r in read(supplement)}
    equals={r["alternative"]:r for r in read(equivalence)}
    rows=[]
    for row in sem:
        name=row["case_id"]
        rec=run[name]
        path=plan/"cases"/name/"result.json"
        got=read(path) if path.is_file() else {}
        holds=[]
        for d in row.get("differences",[]):
            typ,atom=d["what"],d.get("atom",{})
            if typ=="oracle_atom_without_candidate_counterpart":
                checks={"in_support":"selection_outside_support","composed_mask":"post_page_composed_word_mismatch"}
                key=checks.get(atom["check"])
                match=[item for item in got.get("conflicts",[]) if item["key"]==key
                       and item["row"]==atom["row"] and
                       ((item["phase"]=="D_selection" and item.get("observed")==atom["slot_id"]) or
                        (item["phase"]=="C2_post_page" and item.get("id")==atom["slot_id"]))]
                holds.append({"original":d,"comparison":"frozen key map predates the separate candidate predicate",
                              "observed_evidence":match,"confirmed":bool(match)})
            elif typ=="byte_detail":
                match=[item for item in got.get("conflicts",[]) if item["key"]=="firstmax_tie_violation"
                       and item["row"]==atom["row"] and item.get("observed")==atom["slot_id"]]
                holds.append({"original":d,"comparison":"selected token is in observed, not id",
                              "observed_evidence":match,"confirmed":bool(match)})
            elif typ=="verdict":
                match=[item for item in got.get("conflicts",[]) if item["phase"]=="C0_raw"
                       and item["key"]=="phase_cut_binding_mismatch"]
                holds.append({"original":d,"comparison":"genuine CPU receipt observes the differently placed read",
                              "observed_evidence":match,"confirmed":bool(match)})
        out={"case":name,"run":rec["status"],"expected":row.get("expected_verdict"),
             "candidate":got.get("verdict"),"original_semantic_agreement":row.get("semantic_agree"),
             "original_first_relation":row.get("first_relation"),
             "first_phase":got.get("first_divergent_phase"),"conflicts":got.get("conflicts",[]),
             "missing":got.get("missing",[]),"transport_deviations":row.get("transport_deviations",[]),
             "reconciliations":holds}
        if got:
            out["normal_cli"]={name:{k:v for k,v in rec[name].items() if k in
                               {"exit","stdout_sha256","stderr_sha256","stdout_bytes","stderr_bytes"}}
                               for name in ("capture","score")}
        if name in extras:
            out["supplement"]=extras[name]
        if name in equals:
            out["artifact_equivalence"]=equals[name]
        rows.append(out)
    assert len(rows)==50
    destination.write_bytes(b"".join((json.dumps(x,sort_keys=True,separators=(",",":"))+"\n").encode() for x in rows))
    print(json.dumps({"cases":len(rows),"sha256":sha256(destination.read_bytes()).hexdigest(),
        "confirmed_reconciliations":sum(c["confirmed"] for x in rows for c in x["reconciliations"]),
        "unconfirmed":[x["case"] for x in rows if any(not c["confirmed"] for c in x["reconciliations"])]}))


if __name__=="__main__":
    main(*map(Path,sys.argv[1:]))
