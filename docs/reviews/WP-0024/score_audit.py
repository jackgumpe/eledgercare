"""Independent scorer perturbations from the public toy universe. Reads no evaluation truth."""
import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys


def source_test(revision):
    target = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024/review/cpu")/revision
    target.mkdir(parents=True,exist_ok=True)
    for name in ("score.py","check_score.py"):
        path = target/name
        raw = subprocess.check_output(["git","show",f"{revision}:docs/fixtures/WP-0024/{name}"])
        if not path.exists():
            with path.open("xb") as f:
                f.write(raw)
        assert path.read_bytes()==raw
    example=runpy.run_path(str(target/"check_score.py"))
    with redirect_stdout(io.StringIO()) as log:
        example["test"]()
    score=example["impl"]["score"]
    keys,routes,original,obs,res=example["toy"]()
    truths={k["binder"]:k for k in keys["binders"]}
    def post(store,arm,b):
        store[arm][b].update(type="Posting", **{k:truths[b][k] for k in ("owner","unit","column","subtotal_status")})
    def status(store,arm,b,good):
        val=truths[b]["subtotal_status"]
        if not good:
            val="UNBALANCED" if val=="BALANCED" else "BALANCED"
        store[arm][b]["subtotal_status"]=val
    def result(preds):
        return score(keys,routes,preds,obs,res)
    def alt(x):
        return x["slices"]["eligible"]["effects"]["T3_summary_at_tied_owner/M2"]
    base=result(original)
    assert base["decision"]["disposition"]=="ADVANCE ONLY TO FRESH-FAMILY REPLICATION"
    # Remove the two author's positive T2 transitions, isolating all subsequent effects.
    neutral=deepcopy(original)
    for pid in ("T2.0","T2.1"):
        for b in routes[pid]:
            post(neutral,"M2",b)
    assert result(neutral)["decision"]["disposition"]=="KEEP SIMPLER M2"
    changed=deepcopy(neutral)
    for pid in ("T3.0","T3.1","T3.2"):
        for b in routes[pid]:
            status(changed,"M2",b,False)
    positive=result(changed)
    assert set(alt(positive)["usable_summary_wins"])=={"T3.0","T3.1","T3.2"} and alt(positive)["net"]==3
    assert positive["decision"]["disposition"]=="ADVANCE ONLY TO FRESH-FAMILY REPLICATION"
    for pid in ("T3.3","T2.4"):
        b=routes[pid][0]
        binding={k:truths[b][k] for k in ("owner","unit","column")}
        changed["M3"][b].update(type="ABSTAIN",reason="independent_test",binding_diagnostic=dict(type="Posting",**binding))
        if pid=="T3.3":
            for b2 in routes[pid]:
                changed["M3"][b2]["binding_diagnostic"]={"type":"Posting",**{k:truths[b2][k] for k in binding}}
    penalties=result(changed)
    assert alt(penalties)["opposite_summary_losses"]==["T3.3"]
    assert set(alt(penalties)["full_T2_T3_pair_losses"])==set(alt(penalties)["union_losses"])=={"T3.3","T2.4"}
    assert alt(penalties)["net"]==1 and penalties["decision"]["disposition"]=="KEEP SIMPLER M2"
    for b in routes["T3.0"]:
        truth=truths[b]
        changed["M3"][b].update(type="ABSTAIN",reason="independent_test",subtotal_diagnostic={"type":"STATUS","subtotal_status":truth["subtotal_status"]},
                               binding_diagnostic={"type":"Posting",**{k:truth[k] for k in ("owner","unit","column")}})
    diagnostic=result(changed)
    assert "T3.0" not in alt(diagnostic)["usable_summary_wins"]
    t3=next(p for p in diagnostic["pairs"] if p["pair"]=="T3.0")["arms"]["M3"]
    assert t3["binding_diagnostic"] and t3["subtotal_diagnostic"] and not t3["correct"]
    tampered=deepcopy(original)
    tampered["M3-Swap"][routes["T2.3"][0]]["final_entry"]["matrix_sha256"]="0"*64
    assert "matrix_only_swap_proof" in result(tampered)["decision"]["entry_or_leakage_failures"]
    asym=deepcopy(original)
    asym["M0"][routes["T2.3"][0]]["candidate_receipt"]["inputs"]={"choices":["A"]}
    try:
        failed=result(asym)["decision"]["entry_or_leakage_failures"]
        assert "asymmetric_canonical_candidates" in failed
    except ValueError as err:
        assert "candidate" in str(err).lower()
    return {"source":revision,"upstream":log.getvalue().strip(),"eligible":base["decision"]["c0_answerable"],
            "three_usable_summary_gains":alt(positive),"overlapping_full_and_summary_losses":alt(penalties),
            "component_success_during_abstention":alt(diagnostic),"changed_matrix_receipt_rejected":True,
            "changed_candidate_payload_rejected":True}


if __name__=="__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    p=argparse.ArgumentParser()
    p.add_argument("revision")
    print(json.dumps(source_test(p.parse_args().revision),indent=2))

