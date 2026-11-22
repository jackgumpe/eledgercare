"""Reconcile the fixture and probe publications against the independently regenerated source keys and WP-0027 scores."""
from collections import Counter
from hashlib import sha256
import json
import os
import subprocess
import sys

SCOPE = "eb814e399d50fc9b28738751fbbf92ca3c732214"
HISTORY = "0573f69c481eea2e815899e00ddd5e68bb4e3c42"


def record(ref, path):
    raw = subprocess.check_output(["git", "cat-file", "blob", ref+":"+path])
    return json.loads(raw), sha256(raw).hexdigest()


def key(pages, png_field):
    return tuple((p[png_field],p["rgb_sha256"]) for p in pages)


def reconcile(fixture_ref, probe_ref):
    scope, ss = record(SCOPE,"docs/coordination/WP-0028/acquisition-scope.json")
    manifest, ms = record(fixture_ref,"docs/fixtures/WP-0028/manifest.json")
    geometry, gs = record(fixture_ref,"docs/fixtures/WP-0028/geometry.json")
    hist, hs = record(probe_ref,"docs/research/WP-0028/evidence/historical.json")
    controlled, cs = record(probe_ref,"docs/research/WP-0028/evidence/controlled.json")
    old, _ = record(HISTORY,"docs/research/WP-0027/owners/owner-progression.json")
    rankings, _ = record(HISTORY,"docs/research/WP-0027/owners/owner-rankings.json")

    cached = {key(entry["ordered_pages"],"png_sha256"):entry for entry in scope["cached"]}
    missing = {key(entry["ordered_pages"],"png_sha256"):entry for entry in scope["missing"]}
    independent_uses = {}
    for k, row in (cached | missing).items():
        independent_uses[k] = {(u["horizon"],u["owner"],u["window"]) for u in row["uses"]}
    fixture_uses = {}
    templates = {}
    for template in manifest["pairs"]:
        n = template["horizon"]
        for member in template["members"]:
            for w in member["windows"]:
                k=key(w["pages"],"sha256")
                fixture_uses.setdefault(k,set()).add((n, member["owner"], w["window"]))
                if k in cached:
                    f=w["feature"]
                    assert f["pooled_sha256"] == cached[k]["pooled_sha256"]
                    assert f["metadata_sha256"] == cached[k]["metadata_sha256"]
                    assert f["through_eos_sha256"] == cached[k]["through_eos_sha256"]
                else:
                    assert k in missing and w["feature"] is None
        assert not template["admitted"] and len(template["members"]) == 2
        assert {m["owner"]:m["complete"] for m in template["members"]} == {"Alder":True,"Cedar":False}
        templates[template["pair"]] = template
    assert fixture_uses == independent_uses and len(templates) == 2
    pixel_evidence = []
    for g in geometry["geometry"]:
        pages=g["page_evidence"]
        first=pages[0]
        assert first["changed_pixels"]>0 and first["outside"] == 0 and first["changed_pixels"]==first["inside"]
        assert all(p["changed_pixels"]==0 and p["twins_encoded_identical"] and p["twins_decoded_identical"] for p in pages[1:])
        pixel_evidence.append({"pages":len(pages),"changed_page":first["page"],"changed_rgb_pixels":first["changed_pixels"],
                               "change_bbox_xyxy_exclusive":first["bbox_xyxy_exclusive"],"outside_roi":first["outside"],
                               "other_byte_identical_pages":len(pages)-1})

    assert set(hist["arms"]) == set(controlled["arms"]) == {"M1","M3"}
    history, matrix = {}, []
    for arm in ("M1","M3"):
        rows=hist["arms"][arm]["pairs"]
        seen=set()
        checkpoint_count=Counter()
        positive=Counter()
        win=Counter()
        for pair in rows:
            pid=pair["pair"]
            assert pid not in seen
            seen.add(pid)
            members={m["owner"].lower():m for m in pair["members"]}
            assert set(members)=={"alder","cedar"} and len(pair["members"])==2
            initial=None
            for t in ("t1","t2","t3"):
                margins={}
                for owner, m in members.items():
                    cp=m["checkpoints"][t]
                    reference=old["arms"][arm][pid]["by_binder"][m["binder"]]["checkpoints"][cp["source_checkpoint"]]
                    scores=reference["owner_scores"]
                    assert reference["ptr"]==cp["pointer"] and scores=={name.lower():s for name,s in cp["scores"].items()}
                    assert reference["matrix_sha256"]==cp["matrix_sha256"] and reference["query_sha256"]==cp["query_sha256"]
                    assert reference["owner_read_sha256"]==cp["read_sha256"]
                    p0=m["parity"]
                    assert len(set(p0["final_state"].values()))==len(set(p0["trajectory"].values()))==1
                    assert p0["first_checkpoints"]==p0["repeat_checkpoints"]
                    prior=rankings["arms"][arm]["by_binder"][m["binder"]]
                    assert prior["pair"]==pid and prior["target"]==m["target"] and prior["expected"]["owner"].lower()==owner
                    assert cp["typed"]==(prior["selected_binder_decision"] if t=="t3" else None)
                    margins[owner]=scores["alder"]-scores["cedar"]
                a,c=margins["alder"],margins["cedar"]
                mu,delta=(a+c)/2,a-c
                if t=="t1":
                    initial=delta
                expected=pair["metrics"][t]
                assert expected["mu"]==mu and expected["delta"]==delta and expected["D"]==delta-initial
                assert expected["ratio"]==(delta/initial if abs(initial)>1e-6 else None)
                assert a == mu+delta/2 and c==mu-delta/2 and (a>0>c)==(delta>2*abs(mu))==expected["correct_paired_win"]
                checkpoint_count[t]+=1
                win[t]+=int(a>0>c)
                positive[t]+=int(delta>0)
        assert len(seen)==8
        history[arm]={"historical_pairs":len(seen),"paired_observations":dict(checkpoint_count),
                      "positive_historical_responses":dict(positive),"correct_historical_paired_wins":dict(win)}
        for row in controlled["arms"][arm]:
            p=templates[row["pair"]]
            counts=row["counts"]
            assert p["horizon"]==row["horizon"]
            assert counts=={"planned":1,"admitted":0,"completed":0} and row["reason"]=="missing_exact_whole_window_features"
            assert len(row["missing"])==1 and row["missing"][0]["window"]==1
            assert tuple(row["missing"][0]["ordered_rgb_sha256"])==tuple(r["rgb_sha256"] for r in scope["missing"][0]["ordered_pages"])
            missing_binders=[m["binder"] for m in p["members"] if m["owner"]=="Cedar"]
            assert missing_binders==[row["missing"][0]["binder"]]
            assert all(v is None for metrics in row["metrics"].values() for v in metrics.values())
            assert all(c["typed"] is None and c["pointer"] is None and c["exact_top_tie"] is None and
                       c["scores"]=={"Alder":None,"Cedar":None} for m in row["members"] for c in m["checkpoints"].values())
            matrix.append({"arm":arm,"horizon":row["horizon"],**counts,"trajectory_t1_t2_t3":[None,None,None]})
    assert {(r["arm"],r["horizon"]) for r in matrix}=={(a,n) for a in ("M1","M3") for n in (12,30)} and len(matrix)==4
    return {"basis":{"scope_sha256":ss,"fixture_manifest_sha256":ms,"geometry_sha256":gs,"historical_scores_sha256":hs,
                     "controlled_gate_sha256":cs},"pixel_evidence":pixel_evidence,"historical":history,"controlled":matrix,
            "distinct_exact_inputs":len(cached)+len(missing),"cached_distinct":len(cached),
            "logical_uses":sum(map(len,fixture_uses.values())),"missing_logical":sum(len(independent_uses[k]) for k in missing)}


if __name__=="__main__":
    if os.environ.get("CUDA_VISIBLE_DEVICES")!="-1" or not sys.flags.isolated or not sys.dont_write_bytecode or not __debug__:
        raise SystemExit("Use CPU-only isolated -I -B Python with assertions enabled")
    print(json.dumps(reconcile(*sys.argv[1:]),indent=2))
