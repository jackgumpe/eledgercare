"""Resolve every logical feature appearance to the physical signed window, split, W0 and sensor."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_common import HOST, MODEL, blob, cpu, pinned, read, save, sha
from w0_inputs import RECEIPT

def key(pages):
    ordered = [p["rgb_sha256"] for p in pages]
    assert len(ordered) == 3
    return sha((json.dumps(ordered,ensure_ascii=True,indent=2)+"\n").encode("ascii"))

def verify(plan_path,pin):
    from span_audit import reconstruct
    import numpy as np
    p = pinned(plan_path,pin)
    split = p["split"]
    assert p["packet"] == "WP-0026" and p["phase"] == "features"
    public = Path(p["raster_root"]).parent
    signed = "docs/fixtures/WP-0026/blind/" if split == "blind" else f"docs/fixtures/WP-0024/v2/{split}/"
    for f in ("receipt","manifest","pairs","cross-pair"):
        name = f+".json"
        assert (public/name).read_bytes() == blob(p["candidate"],signed+name)
    assert p["manifest_sha256"] == sha((public/"manifest.json").read_bytes())
    binder = {b["binder"]:b["windows"] for b in read(public/"manifest.json")["binders"]}
    cross = read(public/"cross-pair.json")["groups"]
    pair_map = {m["binder"]:q["pair"] for q in read(public/"pairs.json")["pairs"] for m in q["members"]}
    horizons, used = [],{}
    reference_count = uncached_count = 0
    rows = {c["tag"]:c for c in p["calls"]}
    root = Path(p["output"])/"sensor"
    checked = set()
    source_splits, logical_keys = set(),set()
    for pair in p["delivery"]["pairs"]:
        twins = pair["twins"]
        assert len(twins) == 2 and pair_map[twins[0]["binder"]] == pair_map[twins[1]["binder"]]
        for twin in twins:
            b = twin["binder"]
            windows = binder[b]
            assert len(windows) in (4,10) and len(twin["windows"]) == len(windows)
            horizons.append(len(windows))
            for i,(ref,source_row) in enumerate(zip(twin["windows"],windows,strict=True),1):
                k = key(source_row["pages"])
                assert ref["rgb_key"] == k
                logical_keys.add(k)
                s = Path(ref["directory"]) if "directory" in ref else root/ref["tag"]
                assert s.parent.parent.parent == HOST/"review/runs"
                src = read(s/"receipt.json")
                assert src["split"] == split and src["model_revision"] == MODEL and src["verified"] is True
                assert src["warmup_fixture_sha256"] == RECEIPT and src["sensor_candidate"] == p["historical_sensor_revision"]
                assert sha((s.parent/"warmup.json").read_bytes()) == src["warmup_sha256"] and key(src["pages"]) == k
                if source_row["pages"] != src["pages"]:
                    assert [a["sha256"] for a in source_row["pages"]] == [a["sha256"] for a in src["pages"]]
                if pair_map[src["binder"]] != pair_map[b]:
                    refs = {(a["pair"],a["binder"],a["window"]) for a in cross[k]}
                    assert (pair_map[b],b,i) in refs and (pair_map[src["binder"]],src["binder"],src["window"]) in refs
                    assert split != "blind"
                if split == "blind":
                    assert src["window"] == i and pair_map[src["binder"]] == pair_map[b]
                source_splits.add(src["split"])
                used[s] = used.get(s,0)+1
                if s not in checked:
                    native,metadata = read(s/"native.json"),read(s/"metadata.json")
                    for field,v in reconstruct(native["text"],native["token_ids"]).items():
                        assert metadata[field] == v
                    assert sha((s/"metadata.json").read_bytes()) == src["artifacts"]["metadata.json"]
                    pools = (s/"pooled.f32").read_bytes()
                    assert sha(pools) == src["artifacts"]["pooled.f32"] and len(pools) == len(metadata["spans"])*1280*4
                    assert np.isfinite(np.frombuffer(pools,dtype="<f4")).all()
                    checked.add(s)
                if "directory" in ref:
                    assert src["artifacts"]["pooled.f32"] == ref["pooled_sha256"]
                    assert src["artifacts"]["metadata.json"] == ref["metadata_sha256"]
                    assert src["phase"] == "c1" and src["lease"] == ref["source_lease"] == split+"-c1-r1"
                    uncached_count += 1
                else:
                    assert src["phase"] == "features" and src["tag"] in rows
                reference_count += 1
    expected = {"train":(140,11,27),"cal":(140,29,29),"blind":(448,248,None)}[split]
    assert reference_count == expected[0] and len(rows) == expected[1]
    if expected[2] is not None:
        assert len(logical_keys) == expected[2]
    assert source_splits == {split} and len(set(horizons)) == 2
    return {"plan_sha256":pin,"candidate":p["candidate"],"split":split,"logical_appearances":reference_count,
            "unique_ordered_triples":len(logical_keys),"distinct_physical_sources":len(checked),
            "new_physical_calls":len(rows),"references_to_uncached_C1":uncached_count,
            "distinct_checked_pool_bytes":sum((s/"pooled.f32").stat().st_size for s in checked),
            "logical_pool_bytes":sum((s/"pooled.f32").stat().st_size*n for s,n in used.items()),
            "warmup_receipt":RECEIPT,"sensor_tree":p["sensor_tree"],"signed_cross_pair_groups":len(cross)}

if __name__ == "__main__":
    cpu()
    save(Path(sys.argv[3]),verify(Path(sys.argv[1]),sys.argv[2]))
