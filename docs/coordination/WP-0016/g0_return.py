"""Reconcile the exclusive resource, device samples, complete outputs and occupied time."""
from datetime import datetime
import json
from pathlib import Path

from device_lease import HERE, LOCK, PACKET, exclusive, ownership, dump
from inventory import inspect, read, sha


def collect(release_path):
    lease = read(release_path)
    folder = PACKET / "coordination/leases" / lease["name"]
    start, end = [read(folder/name) for name in ("acquired.json","returned.json")]
    assert start["release_sha256"] == end["release_sha256"] == sha(release_path) and not end["error"]
    with exclusive(LOCK):
        free = ownership()["device"]
    inventory = inspect(lease)
    orders = []
    for order, data in zip(lease["orders"], inventory["orders"]):
        name = order["run"]
        ret = read(folder/(name+"-returned.json"))
        assert ret["exit"] == 0 and ret["guard"] is None
        trace = folder/(name+"-device.jsonl")
        samples = [json.loads(line) for line in trace.read_bytes().splitlines()]
        maximum = max(x["used_mib"] for x in samples)
        assert maximum <= lease["ceiling_mib"]
        docs = []
        for d in data["docs"]:
            w = d["windows"]
            docs.append({"arm":d["mode"],"document":d["label"],"warmup":d["excluded"],"pages":d["pages"],
                         "windows":len(w),"ready_seconds":d["elapsed_s"], "prediction_sha256":d["prediction_sha256"],
                         "output_tokens":sum(v["tokens"] for v in w),
                         "max_reserved_mib":max(v["reserved_bytes"] for v in w)/2**20,
                         "max_allocated_mib":max(v["allocated_bytes"] for v in w)/2**20,
                         "carbon_static_reallocations":sum(v["cache_reallocations"] for v in w) if d["mode"]=="carbon_bf16" else None,
                         "carbon_prefill_fallback_layer_calls":sum(v["prefill_fallback_layer_calls"] for v in w) if d["mode"]=="carbon_bf16" else None})
        orders.append({"order":name,"exit":ret["exit"],"wall_seconds":ret["wall_s"],"device_samples":len(samples),
                       "device_used_peak_mib":maximum,"sample_stream_sha256":sha(trace),
                       "process_sha256":data["process_sha256"],"return":ret["utc"],"documents":docs})
    return {"state":"returned","source":lease["review_worktree_head"],"release_sha256":sha(release_path),
            "acquired_utc":start["utc"],"returned_utc":end["utc"],"lock_reacquired_after_return":True,
            "device_free_mib_after_return":free["free_mib"],
            "occupied_wall_seconds":(datetime.fromisoformat(end["utc"])-datetime.fromisoformat(start["utc"])).total_seconds(),
            "orders":orders,"requested_warmup_windows":12,"scored_windows":88,"completed_measured_source_pages":256,
            "monitoring":"Device maxima are sampled. Each window separately retains CUDA allocator high-water marks."}


if __name__ == "__main__":
    record = collect(HERE/"g0-anchor-release.json")
    dump(HERE/"g0-return.json",record)
    print(record["occupied_wall_seconds"],[(o["order"],o["device_used_peak_mib"]) for o in record["orders"]])
