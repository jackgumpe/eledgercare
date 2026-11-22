"""Rebuild replayable PDFs, rasters, page differences and development feature admission."""
from collections import defaultdict
import json
from pathlib import Path
import sys
from time import perf_counter, process_time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BASE, TRUTH, TRUTH_PIN, cpu, encode, git_blob, identity, keep, sha, triple

def route(pairs, archive, sources):
    captures = archive["physical_captures"]
    recorded = defaultdict(list)
    for c in captures:
        if c["feature"] is not None:
            recorded[c["rgb_key"]].append(c)
    missing = {}
    logical, matched = 0, 0
    keys = set()
    historical = json.loads(git_blob("docs/research/WP-0026/fit/cal-transport.json",
                                     "6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc"))
    transport = {t["binder"]:t for q in historical["pairs"] for t in q["twins"]}
    for p in pairs:
        base_transport = transport[p["base_binder"]]
        assert base_transport["target"] == p["base_target"]
        for m in p["members"]:
            for w in m["windows"]:
                n = w["window"]
                pages = w["pages"]
                k = w["rgb_key"] = triple(pages)
                keys.add(k)
                logical += 1
                candidates = recorded.get(k,[])
                assert all(tuple(tuple(x) for x in r["ordered_png_rgb"]) == identity(pages) for r in candidates)
                # WP-0026 routes are split-local. Record every search hit, including alternate bindings.
                eligible = [r for r in candidates if r["split"]=="cal"]
                assert all(r["split"]=="cal" for r in candidates), "cross-split collision requires separate disposition"
                w["matching_runs_tags"] = [[r["run"], r["tag"]] for r in candidates]
                w["feature"] = None
                if eligible:
                    r = eligible[0]
                    w["feature"] = r["feature"]
                    w["source_binder"] = r["historical_binder"]
                    w["source_window"] = r["historical_window"]
                    w["historical_logical_sources"] = sources["cal"]["uses"][k]
                    matched += 1
                else:
                    assert all(k not in s["uses"] for s in sources.values())
                    miss = missing.setdefault(k,dict(rgb_key=k,pages=pages,uses=[]))
                    miss["uses"].append(dict(template=p["template"],pair=p["pair"],binder=m["binder"],window=n))
                if m["owner"]=="Alder" or n>1:
                    old = Path(base_transport["windows"][n-1])
                    assert w["feature"] is not None and [old.parents[1].name, old.name] in w["matching_runs_tags"]
            m["complete"] = all(w["feature"] is not None for w in m["windows"])
        p["admitted"] = all(m["complete"] for m in p["members"])
    for key, miss in missing.items():
        desired = identity(miss["pages"])
        miss["historical_complete_matches"] = 0
        miss["per_position_counts"] = [sum(tuple(r["ordered_png_rgb"][j]) == desired[j] for r in captures if r["feature"]) for j in range(3)]
        miss["per_position_distinct_rows_matching"] = [
            [[r["run"],r["tag"]] for r in captures if r["feature"] and tuple(r["ordered_png_rgb"][j])==desired[j]]
            for j in range(3)]
        miss["reason"] = "NO_EXACT_WARMED_DEVELOPMENT_FEATURE_FOR_ORDERED_INPUT"
    return dict(schema_version=1, archive_revision=BASE, source_split="WP-0024/v2/cal", truth_sha256=TRUTH_PIN,
                scope="Development fixture and admission sidecar. Pass only admitted ordered feature bytes to the frozen readout.",
                rgb_key_encoding="SHA-256 of indent-2 ASCII JSON array of three ordered RGB digests and LF",
                target_identity="Per-member target corresponds to the same printed unheaded posting on page horizon-1.",
                planned_pairs=len(pairs),admitted_pairs=sum(p["admitted"] for p in pairs),
                logical_windows=logical,matched_logical_windows=matched,unique_windows=len(keys),matched_unique_windows=len(keys)-len(missing),
                pairs=pairs,missing=list(missing.values()))

def main(scratch):
    start, proc = perf_counter(), process_time()
    scratch = scratch.resolve()
    assert scratch.is_relative_to(Path("C:/Users/jackg/eLedgerCare-Speed/WP-0028").resolve())
    cpu(scratch)
    from archive import inventory
    from geometry import build
    output = scratch/"release"
    pairs, geometry = build(output)
    archive, sources = inventory()
    manifest = route(pairs, archive, sources)
    checks = dict(development_source_sha256=sha(git_blob("docs/fixtures/WP-0024/v2/cal/receipt.json")),
                  permitted_truth_path=str(TRUTH),permitted_truth_sha256=TRUTH_PIN,
                  libraries={"Pillow":"13.0.0","pypdfium2":"5.15.2","numpy":"2.2.6"},
                  canonical_png="Pillow RGB PNG, dpi=(300,300), compress_level=3",
                  geometry=geometry)
    from importlib.metadata import version
    assert checks["libraries"] == {k:version(k) for k in checks["libraries"]}
    for name, result in (("geometry",checks),("archive",archive),("manifest",manifest)):
        keep(output/(name+".json"),encode(result))
    print(json.dumps(dict(manifest_sha256=sha(encode(manifest)),archive_sha256=sha(encode(archive)),geometry_sha256=sha(encode(checks)),
                          pairs=manifest["planned_pairs"],admitted=manifest["admitted_pairs"],missing_unique=len(manifest["missing"]),
                          logical=manifest["logical_windows"],matched=manifest["matched_logical_windows"],
                          elapsed_s=perf_counter()-start,cpu_process_s=process_time()-proc)))
if __name__ == "__main__":
    main(Path(sys.argv[1]))
