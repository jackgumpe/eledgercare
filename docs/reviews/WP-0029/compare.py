"""Compare author evidence with both an independent observer and the independently invoked author entry point."""
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit import SCRATCH, blob, initialize, save, sha

def compare(revision, path):
    theirs=blob(revision,path)
    direct=(SCRATCH/"released-r1/result.json").read_bytes()
    assert theirs==direct
    rows=json.loads(theirs)
    mine=json.loads((SCRATCH/"independent-scores.json").read_bytes())
    counts={"member_checkpoints":0,"parity_confirmed_binders":0,"native_field_logits":0,"paired_checkpoints":0}
    assert mine["gate_revision"]==rows["gate"]["revision"]
    result={"score_revision":revision,"score_path":path,"score_sha256":sha(theirs),"exact_frozen_entrypoint_repeat":True,
            "counts":counts,"independent_scores_sha256":sha((SCRATCH/"independent-scores.json").read_bytes()),
            "controls_sha256":sha((SCRATCH/"controls-r1/result.json").read_bytes())}
    if not mine["counts"]["completed"]:
        assert rows["arm_pair_counts"]=={"planned":4,"admitted":0,"completed":0}
        for pairs in rows["arms"].values():
            for pair in pairs:
                assert pair["reason"] and all(v is None for m in pair["metrics"].values() for v in m.values())
                for member in pair["members"]:
                    assert member["parity"] is None
                    for cp in member["checkpoints"].values():
                        assert cp["scores"]=={"Alder":None,"Cedar":None} and cp["typed"] is None
        return result
    assert rows["arm_pair_counts"]=={"planned":4,"admitted":4,"completed":4} and rows["integrity_failure"] is None
    assert set(rows["capture_inventory"])==set(mine["archive_uses"]) and len(rows["capture_inventory"])==11
    for arm,pairs in rows["arms"].items():
        assert {r["horizon"] for r in pairs}=={12,30}
        for pair in pairs:
            assert pair["reason"] is None and pair["within_pair_query_bytes_equal"]
            own=mine["arms"][arm][str(pair["horizon"])]
            assert pair["source_target"]==own["source_target"]
            for step,metrics in pair["metrics"].items():
                o=own["trajectory"][step]
                for k,j in (("margin_Alder_input","margin_alder"),("margin_Cedar_input","margin_cedar"),("delta","delta"),
                            ("mu","mu"),("D","D"),("ratio","R"),("correct_paired_win","win"),("delta_gt_twice_abs_mu","win")):
                    assert metrics[k]==o[j], (arm,pair["horizon"],step,k)
                assert metrics["positive_response"]==(o["delta"]>0)
                counts["paired_checkpoints"]+=1
            for m in pair["members"]:
                o=own["binders"][m["owner"]]
                assert m["binder"]==o["binder"] and m["target"]==o["target"] and o["fresh_duplicate_plain_agreement"]
                q=m["parity"]["plain_target"]
                assert q["matrix_sha256"]==o["final_matrix"] and q["typed"]==o["typed"]
                assert len(set(m["parity"]["final_state"].values()))==len(set(m["parity"]["trajectory"].values()))==1
                assert m["parity"]["first_checkpoints"]==m["parity"]["repeat_checkpoints"]
                for f,bits in o["field_bytes"].items():
                    assert q["attempts"][0]["logit_sha256"][f]==sha(bytes.fromhex(bits))
                    counts["native_field_logits"]+=len(bits)//8
                counts["parity_confirmed_binders"]+=1
                p=m["eligibility_observations"]["depth_zero_opening_parents"]
                assert len(p)==1 and [p[0][k] for k in ("pointer","literal","value")]==o["parent"][:3]
                for step,c in m["checkpoints"].items():
                    independent=o["checkpoints"][step]
                    for k,j in (("pointer","ptr"),("matrix_sha256","matrix"),("query_sha256","query"),("read_sha256","read")):
                        assert c[k]==independent[j],(arm,m["binder"],step,k)
                    assert c["controller"]["depth"]==independent["depth"] and c["candidate_order"]==["Alder","Cedar"]
                    assert c["unit_column_controls"]==independent["unit_column"]
                    bits=b"".join(struct.pack("<f",independent["scores"][k]) for k in ("alder","cedar"))
                    assert all(c["scores"][key]==independent["scores"][key.lower()] for key in ("Alder","Cedar"))
                    assert sha(bits)==c["score_bytes_f32le_sha256"] and c["exact_top_tie"]==(bits[:4]==bits[4:])
                    assert c["typed"]==(o["typed"] if step=="t3" else None)
                    assert c["target_available"] and c["reason"] is None
                    counts["member_checkpoints"]+=1
        for owner,steps in rows["cross_horizon"][arm].items():
            for t,v in steps.items():
                o=mine["cross_horizon"][arm][t][owner]
                assert v["query_bytes_equal"]==o["query"] and v["score_bytes_equal"]==o["scores"]
                assert v["shared"]==(o["query"] and o["scores"])
    assert (counts["member_checkpoints"],counts["paired_checkpoints"],counts["parity_confirmed_binders"])==(24,12,8)
    return result

if __name__=="__main__":
    initialize()
    save(sys.argv[3],compare(sys.argv[1],sys.argv[2]))
