"""Resolve the v2 blind within-pair call budget using the original split-aware planner's public routing."""
from pathlib import Path


def bounded_blind(sched, planner, public, prior, cached):
    receipt, pairs, binders = planner.source_groups(public)
    if len(pairs) != 32 or len(binders) != 64 or sched["manifest_sha256"] != receipt["manifest_sha256"]:
        raise ValueError("Blind corpus cardinality or source commitment")
    baseline = {t["binder"]:t["windows"] for p in sched["delivery"]["pairs"] for t in p["twins"]}
    prior_by_appearance = {}
    source_dir = Path(prior["output"]) / "sensor"
    rows = planner.read(source_dir / "outcome.json")["rows"]
    for c in prior["calls"]:
        k = planner.rgb_key(c["pages"])
        row = rows[c["tag"]]
        src = {**cached[k], "directory":str(source_dir/c["tag"]), "metadata_sha256":row["metadata_sha256"],
               "pooled_sha256":row["capture"]["pooled_sha256"]}
        prior_by_appearance[(c["binder"], c["window"])] = src
    if len(prior_by_appearance) != 28:
        raise ValueError("The two uncached complete blind pairs must precede reuse")
    calls, delivery = [], []
    for pair in pairs:
        seen = {}
        twins = []
        for member in pair["members"]:
            binder = member["binder"]
            views = []
            for window in binders[binder]:
                k = planner.rgb_key(window["pages"])
                ordinal = window["window"]
                if baseline[binder][ordinal-1]["rgb_key"] != k:
                    raise ValueError("Frozen planner and original raster disagree")
                key = (ordinal, k)
                source = prior_by_appearance.get((binder, ordinal), seen.get(key))
                if source is None:
                    tag = f"k{len(calls)+1:04d}"
                    calls.append({"tag":tag, "binder":binder, "window":ordinal, "pages":window["pages"],
                                  "hooked":True, "retain_hidden":False})
                    source = {"tag":tag, "rgb_key":k}
                if source["rgb_key"] != k:
                    raise ValueError("Unrelated evidence source for blind window")
                seen[key] = source
                views.append(source)
            twins.append({**member, "windows":views})
        delivery.append({"twins":twins})
    if len(calls) != 248 or sum(len(t["windows"]) for p in delivery for t in p["twins"]) != 448:
        raise ValueError("Blind budget must resolve all 448 appearances with 28 uncached and 248 further calls")
    return {**sched, "calls":calls, "delivery":{"pairs":delivery}, "cache_scope":"same pair, same window index and ordered RGBs"}
