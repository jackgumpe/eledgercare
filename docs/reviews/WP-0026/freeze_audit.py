"""Verify six immutable view files, the merged opaque predictions and cross-twin matrix provenance before scoring."""
from collections import Counter
import json
import math
from pathlib import Path
import statistics
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_common import cpu,pinned,read,save,sha

ARMS = ("M0","M1","M2","M3-Zero","M3","M3-Swap")

def verify(root,view_pin,routing,fit_pin):
    six = pinned(root/"six-freeze.json",view_pin)
    freeze = pinned(root/"freeze.json",six["freeze_sha256"])
    assert freeze["fit_sha256"] == fit_pin and freeze["predictions_sha256"] == six["joint_sha256"]
    manifest = pinned(routing,freeze["manifest_sha256"])
    expected = {(t["binder"],t["target"]):len(t["windows"]) for p in manifest["pairs"] for t in p["twins"]}
    assert len(manifest["pairs"]) == 32 and len(expected) == 64 and sum(expected.values()) == 448
    targets = {b:t for b,t in expected}
    assert len(set(targets.values())) == 64
    companion = {}
    for p in manifest["pairs"]:
        a,b = [t["binder"] for t in p["twins"]]
        assert a != b
        companion[a],companion[b] = b,a
    joint = pinned(root/"predictions.json",freeze["predictions_sha256"])["predictions"]
    assert len(joint) == 384 and set(six["views"]) == set(ARMS)
    indexed = {}
    counts = {}
    for arm in ARMS:
        entry = six["views"][arm]
        assert entry["file"] == arm+"-predictions.json"
        single = pinned(root/entry["file"],entry["sha256"])["predictions"]
        assert single == [r for r in joint if r["arm"] == arm]
        assert len(single) == entry["predictions"] == 64 and {(r["binder"],r["target"]) for r in single} == set(expected)
        for record in single:
            assert record["type"] in ("ABSTAIN","Posting")
            if record["type"] == "ABSTAIN":
                assert record["reason"]
            else:
                assert all(isinstance(record[f],str) and record[f] for f in ("owner","unit","column"))
                assert record["subtotal_status"] in (None,"BALANCED","UNBALANCED")
            indexed[arm,record["binder"]] = record
        counts[arm] = {"sha256":entry["sha256"],"decision_types":dict(Counter(r["type"] for r in single))}
    proof,anchor = {},{}
    for receiver,donor in companion.items():
        s = indexed["M3-Swap",receiver]["final_entry"]
        before,other = [indexed["M3",t]["final_entry"] for t in (receiver,donor)]
        proof[receiver] = (s["receiver_binder"] == receiver and s["donor_binder"] == donor and
            s["matrix_sha256"] == other["matrix_sha256"] and s["original_matrix_sha256"] == before["matrix_sha256"] and
            s["nonmatrix_sha256"] == before["nonmatrix_sha256"] == s["receiver_nonmatrix_sha256"])
        candidates = [indexed[arm,b]["candidate_receipt"] for arm in ARMS for b in (receiver,donor)]
        anchor[receiver] = (len({c["sha256"] for c in candidates}) == 1 and
                            all(c["pair_equal"] and sha(json.dumps(c["inputs"],sort_keys=True,separators=(",",":")).encode()) == c["sha256"] for c in candidates))
    telemetry = pinned(root/"telemetry.json",freeze["telemetry_sha256"])
    times = telemetry["cached_cpu"]
    assert {(r["arm"],r["binder"],r["target"]) for r in times} == {(a,b,t) for a in ARMS for b,t in expected}
    assert len(times) == 384
    window_costs = [ns/1e6 for r in times if r["arm"] == "M3" for ns in r["window_ns"]]
    assert len(window_costs) == 448 and all(math.isfinite(n) and n >= 0 for n in window_costs)
    live = [n for r in times if r["arm"] == "M2" for n in r["live_host_bytes"]]
    assert len(live) == 448
    metrics = {"cached_probe_ms_per_window":statistics.mean(window_costs),"cached_window_count":448,
               "minimum_ms":min(window_costs),"median_ms":statistics.median(window_costs),"maximum_ms":max(window_costs),
               "m2_host_bytes":max(live),"probe_vram_mib":telemetry["probe_cuda_allocated_bytes"]/1024**2,
               "registry":{a:{"lookup_ns":sum(r["lookup_ns"] for r in times if r["arm"]==a),
                              "growth_rows":sum(len(r["registry_growth"]) for r in times if r["arm"]==a)} for a in ARMS}}
    window_one = {t["binder"]:sha((Path(t["windows"][0])/"metadata.json").read_bytes())
                  for p in manifest["pairs"] for t in p["twins"]}
    return {"fit_sha256":fit_pin,"views_sha256":view_pin,"joint_sha256":six["joint_sha256"],"telemetry_sha256":freeze["telemetry_sha256"],
            "transport_sha256":freeze["manifest_sha256"],"window1_sha256":window_one,"views":counts,
            "unique_directions":len(proof),"matrix_only_matches":sum(proof.values()),"symmetric_candidate_directions":sum(anchor.values()),
            "metrics":metrics,"private_key_read":False}

if __name__=="__main__":
    cpu()
    save(Path(sys.argv[5]),verify(Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3]),sys.argv[4]))
