"""Cross-check the coordinator's budget and proposed exact matrix against primary receipts."""
import io
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BASE, WORK, blob, js, output, pinned, sha

CANDIDATE="9377977d43042a78dd14d018878f714bb8b763e6"
PUBLISHED="eb814e399d50fc9b28738751fbbf92ca3c732214"

def compare():
    snippet=WORK/"proposal-constructor.py"
    snippet.write_bytes(blob(CANDIDATE,"docs/coordination/WP-0028/acquisition_scope.py"))
    outfile=WORK/sys.argv[2]
    subprocess.run([sys.executable,"-I","-B",str(snippet),str(outfile)],check=True)
    planned=outfile.read_bytes()
    assert planned==blob(PUBLISHED,"docs/coordination/WP-0028/acquisition-scope.json")
    p=json.loads(planned)
    independent=js(WORK/sys.argv[3])
    coverage=independent["coverage"]
    def rows(c):
        return zip((v["position"] for v in c), (v["png_sha256"] for v in c),(v["rgb_sha256"] for v in c))
    candidates=p["cached"]+p["missing"]
    seen=set()
    for group in candidates:
        for use in group["uses"]:
            key=(use["horizon"],use["owner"],use["window"])
            assert key not in seen
            seen.add(key)
            ours=coverage[f"{key[0]}-{key[1]}"][key[2]-1]
            assert list(rows(group["ordered_pages"]))==[(i+1,x["sha256"],x["rgb_sha256"]) for i,x in enumerate(ours["pages"])]
            if ours["matches"]:
                ref,=[m for m in ours["matches"] if m["run"]=="cal-features-r1" and m["tag"]==group["tag"]]
                for field,member in (("pooled_sha256","pooled.f32"),("metadata_sha256","metadata.json"),("through_eos_sha256","through-eos.u32le")):
                    assert group[field]==ref["hashes"][member]
            else:
                assert group in p["missing"]
    assert len(seen)==p["logical_windows"]==28 and len(candidates)==p["unique_ordered_windows"]==11
    assert (len(p["cached"]),len(p["missing"]),sum(len(c["uses"]) for c in p["cached"]))==(10,1,26)
    assert p["missing_unique"]==1 and p["missing_logical"]==2
    proposal=p["proposed_future_acquisition"]
    assert proposal["released"] is False and proposal["loads"]==proposal["excluded_W0_calls"]==proposal["scored_B1_calls"]==1
    assert proposal["maximum_total_native_calls"]==2 and proposal["automatic_retries"]==0
    assert proposal["hard_supervised_wall_seconds"]==180
    costs=p["historical_timing_comparator"]
    prefix="runs/cal-features-r1/sensor/"
    zraw=pinned(BASE,"docs/reviews/WP-0026/cal-features-primary/primary-001.zip")
    with ZipFile(io.BytesIO(zraw)) as z:
        load=json.loads(z.read(prefix+"cold.json"))
        warm=json.loads(z.read(prefix+"warmup.json"))
        duration=json.loads(z.read(prefix+"k0007/duration.json"))
    assert load["model_load_id"]==warm["model_load_id"] and load["model"]["model_revision"]==proposal["native_model_revision"]
    assert load["model"]["manifest_sha256"]==proposal["model_manifest_sha256"] and load["model"]["target_dtype"]==proposal["dtype"]
    ns=[load["elapsed_ns"],warm["elapsed_ns"],duration["complete_window_wall_ns"]]
    assert [n/1e9 for n in ns]==[costs[k] for k in ("load_seconds","warmup_seconds","complete_window_seconds")]
    assert abs(sum(ns)/1e9-costs["combined_comparator_seconds"])<1e-12
    assert warm["fixture_sha256"]==proposal["warmup_fixture_sha256"] and warm["success"] and warm["eos_observed"]
    assert costs["duration_sha256"]==coverage["12-Alder"][0]["matches"][0]["hashes"]["duration.json"]
    return {"constructor":CANDIDATE,"proposal":PUBLISHED,"sha256":sha(planned),"duration_ns":ns,"comparator_seconds":sum(ns)/1e9,
            "hard_wall_s":180,"loads":1,"max_native_calls":2,"retry_count":0,"cached_unique":10,"cached_logical":26,
            "missing_unique":1,"missing_logical":2,"operator_release":False}

if __name__=="__main__":
    output(sys.argv[1],compare())
