"""Compare independently reconstructed bytes and typed records to both exact candidates."""
from collections import Counter
from pathlib import Path
import json
import struct
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import WORK, blob, js, output, sha
from physical import archives

FIXTURE="ee8e96afcbd7a3c1f3eaa8125c05e68003c4a893"
EVIDENCE="fcaf30465f0ce120c8077369155e4b624044baad"
PUBLISHED="docs/research/WP-0028/evidence/"

def compare():
    begin=time.process_time()
    physical=js(WORK/"physical-1.json")
    history=js(WORK/"historical-3.json")
    root=WORK/"fixture-author-2/release"
    hashes={}
    for p in root.rglob("*"):
        if p.is_file():
            name=p.relative_to(root).as_posix()
            assert p.read_bytes()==blob(FIXTURE,"docs/fixtures/WP-0028/"+name)
            hashes[name]=sha(p.read_bytes())
    assert len(hashes)==38
    manifest=js(root/"manifest.json")
    assert manifest["source_split"]=="WP-0024/v2/cal" and manifest["planned_pairs"]==2 and manifest["admitted_pairs"]==0
    for pair in manifest["pairs"]:
        h=pair["horizon"]
        independent=physical["source"][str(h)]
        assert (pair["base_binder"],pair["base_pair"],pair["base_target"])==(independent["base"],independent["pair"],independent["target"])
        assert (pair["target_page"],pair["target_window"],pair["target_page_in_window"])==(h-1,h//3,2)
        for m in pair["members"]:
            owner=m["owner"]
            assert m["source_pdf_sha256"]==independent["pdf"][owner] and m["complete"]==(owner=="Alder")
            for author,review in zip(m["windows"],physical["coverage"][f"{h}-{owner}"],strict=True):
                assert [{k:p[k] for k in ("sha256","rgb_sha256")} for p in author["pages"]]==review["pages"]
                if review["matches"]:
                    match,=[a for a in review["matches"] if a["tag"]==author["feature"]["tag"]]
                    for fn,field in (("metadata.json","metadata_sha256"),("pooled.f32","pooled_sha256"),("through-eos.u32le","through_eos_sha256")):
                        assert author["feature"][field]==match["hashes"][fn]
                else:
                    assert author["feature"] is None and owner=="Cedar" and author["window"]==1
    miss,=manifest["missing"]
    captures,_=archives()
    pos=[sum(len(values) for rgbs,values in captures.items() if rgbs[i]==p["rgb_sha256"]) for i,p in enumerate(miss["pages"])]
    assert pos==miss["per_position_counts"]==[0,8,6] and len(miss["uses"])==2
    outputs={}
    for k,d in (("historical","historical-author-2"),("controlled","controlled-author-1")):
        data=(WORK/d/(k+".json")).read_bytes()
        assert data==blob(EVIDENCE,PUBLISHED+k+".json")
        outputs[k]=json.loads(data)
        hashes[k]=sha(data)
    counts=Counter()
    for arm,data in outputs["historical"]["arms"].items():
        assert len(data["pairs"])==8 and data["zero_state_control"]["zero"]
        for p in data["pairs"]:
            independent=history["arms"][arm][p["pair"]]
            for t,row in p["metrics"].items():
                ours=independent["trajectory"][t]
                for a,r in (("margin_Alder_input","margin_alder"),("margin_Cedar_input","margin_cedar"),
                            ("D","D"),("ratio","R"),("mu","mu"),("delta","delta"),("correct_paired_win","win")):
                    assert row[a]==ours[r]
                assert row["delta_gt_twice_abs_mu"]==ours["win"] and row["positive_response"]==(ours["delta"]>0)
                counts["paired_checkpoint_metrics"]+=1
            for m in p["members"]:
                own=independent["binders"][m["owner"]]
                assert own["target"]==m["target"] and own["binder"]==m["binder"]
                for t,b in m["checkpoints"].items():
                    observed=own["checkpoints"][t]
                    assert b["unit_column_controls"]==observed["unit_column"]
                    for a,r in (("matrix_sha256","matrix"),("read_sha256","read"),("query_sha256","query"),("pointer","ptr")):
                        assert b[a]==observed[r]
                    assert b["controller"]["depth"]==observed["depth"]
                    scores=[observed["scores"][name] for name in ("alder","cedar")]
                    assert b["scores"]==dict(zip(("Alder","Cedar"),scores,strict=True))
                    assert b["score_bytes_f32le_sha256"]==sha(struct.pack("<ff",*scores))
                    assert b["exact_top_tie"]==(scores[0]==scores[1])
                    assert b["typed"]==(own["typed"] if t=="t3" else None)
                    counts["member_checkpoints"]+=1
                receipt=m["parity"]["plain_target"]
                assert receipt["typed"]==own["typed"] and receipt["matrix_sha256"]==own["final_matrix"]
                attempt,=receipt["attempts"]
                for f,raw in own["field_bits"].items():
                    native=b"".join(bytes.fromhex(raw[k.casefold()]) for k in attempt["choices"][f])
                    assert sha(native)==attempt["logit_sha256"][f]
                    counts["native_field_logits"]+=len(raw)
                counts["native_attempts"]+=1
    for arm,rows in outputs["controlled"]["arms"].items():
        assert len(rows)==2 and {r["horizon"] for r in rows}=={12,30}
        for r in rows:
            reason="missing_exact_whole_window_features"
            assert r["reason"]==reason and r["counts"]=={"planned":1,"admitted":0,"completed":0}
            assert not r["fixture_admitted"] and all(v is None for point in r["metrics"].values() for v in point.values())
            assert r["missing"][0]["rgb_key"]==miss["rgb_key"] and r["missing"][0]["ordered_rgb_sha256"]==physical["missing"][0]
            for m in r["members"]:
                assert m["parity"] is None
                for t,row in m["checkpoints"].items():
                    assert row["scores"]=={"Alder":None,"Cedar":None} and row["reason"]==reason
                    assert row["unit_column_controls"]=={"unit":None,"column":None}
                    assert all(v is None for k,v in row.items() if k not in ("reason","role","scores","unit_column_controls"))
                    counts["null_member_checkpoints"]+=1
                    counts["null_owner_logits"]+=len(row["scores"])
    assert counts["paired_checkpoint_metrics"]==48 and counts["member_checkpoints"]==96 and counts["null_owner_logits"]==48
    return {"counts":dict(counts),"fixture_and_probe_bytes":hashes,"candidate_fixture":FIXTURE,"candidate_probe_evidence":EVIDENCE,
            "per_position_partial_hits":pos,"comparative_cpu_seconds":time.process_time()-begin}

if __name__=="__main__":
    output(sys.argv[1],compare())
