"""Stage 1 (after the blind inventory is committed, before any scoring key): verify WP-0016 G0 runs.

Re-verifies every inventoried hash (immutability), then checks each run against the coordinator's plan
record, the bound source and lease, the input-only raster pins, durable publication, the frozen projection
(formats.native_page re-applied to every raw page), <PAGE> starts, window token/raw reassembly, stops and
page counts, window coverage and clocks. Records the named structural grammar per raw source page, cache
and burst counters, allocator and device memory separately, cold load / serving / segment walls, paired
timing in both orders with the A and H repeat spread, and token parity. Never reads truth. Stdlib only.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (G0, LABEL_FAMILY, MIB, PAGE_ID, PINS, WINDOW, Check, is_pinned, layout, load,  # noqa: E402
                    load_formats, order_of, sha, sha_file, split_segments, title_rule, utc, write_new)
from grammar import classify_page, totals  # noqa: E402

BOX = re.compile(r"\[\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\]")
COUNTERS = ("forward_count", "burst_extra_forwards", "static_cache_reallocations", "prefill_grouped_mm_layer_calls",
            "prefill_moe_fallback_layer_calls", "triton_starts", "dense_starts")


def immutable(inv_run, check):
    run = Path(inv_run["path"])
    now = {f.relative_to(run).as_posix(): sha_file(f) for f in sorted(run.rglob("*")) if f.is_file()}
    want = dict(inv_run["files"], **inv_run["runtime_cache_files"])
    check(now == want, f"{run.name}: run tree differs from blind inventory "
                       f"(changed/added/removed: {sorted(k for k in set(now) | set(want) if now.get(k) != want.get(k))[:8]})")


def inputs(record, root, check):
    pins = {}
    for fam in ("H", "A"):
        spec = record["inputs"][fam]
        d = Path(root) / fam
        check(sha_file(d / "source.pdf") == spec["files"]["source.pdf"], f"input {fam}: source.pdf hash")
        rb = (d / "rasters.input.json").read_bytes()
        check(sha(rb) == spec["raster_input_sha256"], f"input {fam}: rasters.input.json hash")
        r = json.loads(rb)
        rows = sorted(r["pages"], key=lambda x: x["page_number"])
        check([x["page_number"] for x in rows] == list(range(1, spec["pages"] + 1)), f"input {fam}: page numbers")
        check(r["pdf_sha256"] == spec["files"]["source.pdf"], f"input {fam}: raster record PDF binding")
        pins[fam] = dict(sha256=spec["files"]["source.pdf"], pages=spec["pages"], rgb=[x["rgb_sha256"] for x in rows])
    return pins


def verify_doc(folder, req, fmt, rule, check):
    tag = "/".join(Path(folder).parts[-3:])
    n = req["pages"]
    info = dict(folder=str(folder), label=req["label"], mode=req["mode"], warmup=req["warmup"], pages=n)
    if not check((folder / "timing.json").is_file() and (folder / "prediction.json").is_file(),
                 f"{tag}: missing timing/prediction"):
        return info, None
    t = load(folder / "timing.json")
    check(t.get("request") == req, f"{tag}: timing request differs from plan request")
    pb = (folder / "prediction.json").read_bytes()
    pred = json.loads(pb)
    check(sha(pb) == t.get("prediction_sha256"), f"{tag}: prediction hash != timing record")
    check(pred.get("source_sha256") == req["sha256"], f"{tag}: prediction source")
    check([p.get("page") for p in pred["pages"]] == list(range(1, n + 1)), f"{tag}: page ordinals")
    check(not list(folder.glob("*.pending")) and not (folder / "failure.json").exists(), f"{tag}: pending/failure file")
    raws, grams = {}, []
    for i, p in enumerate(pred["pages"], 1):
        rawf, pagef = folder / f"raw-{i:03d}.json", folder / f"page-{i:03d}.json"
        if not check(rawf.is_file() and pagef.is_file(), f"{tag}: p{i} raw/page file missing"):
            continue
        raw = load(rawf)
        check(load(pagef) == p, f"{tag}: page-{i:03d} != prediction entry")
        check(raw.get("page") == i and raw.get("rgb_sha256") == req["rgb_sha256"][i - 1], f"{tag}: p{i} rgb pin/page")
        check(raw.get("source_sha256") == p.get("source_sha256") == req["sha256"], f"{tag}: p{i} source link")
        check(p.get("state") == "complete", f"{tag}: p{i} state")
        check(raw["token_ids"][:1] == [PAGE_ID] and raw.get("token_count") == len(raw["token_ids"]),
              f"{tag}: p{i} <PAGE> start / token count")
        check(fmt.native_page(raw["raw_output"], raw["points"]) == {k: p.get(k) for k in ("text", "spans", "tables")},
              f"{tag}: p{i} stored page is not the frozen projection of its raw output")
        grams.append(dict(source_sha256=raw["source_sha256"], page=i, rgb_sha256=raw["rgb_sha256"],
                          **classify_page(raw["raw_output"], fmt.BLOCK, rule)))
        raws[i] = raw
    files = sorted(folder.glob("window-*.json"))
    check([f.name for f in files] == [f"window-{s:03d}.json" for s in range(1, n + 1, WINDOW)], f"{tag}: window files")
    wins, covered = [], []
    for f in files:
        d = load(f)
        span = list(range(d["first_page"], d["first_page"] + d["pages"]))
        covered += span
        ids = d["window_token_ids"]
        check(d.get("source_sha256") == req["sha256"], f"{tag}: {f.name} source")
        if all(i in raws for i in span):
            check([x for i in span for x in raws[i]["token_ids"]] == ids, f"{tag}: {f.name} token reassembly")
            check("".join(raws[i]["raw_output"] for i in span) == d["raw_output"], f"{tag}: {f.name} raw reassembly")
        check(d.get("finish_reason") == "stop", f"{tag}: {f.name} finish_reason {d.get('finish_reason')!r}")
        check(d.get("num_pages_out") == d.get("expected_pages") == d["pages"] == ids.count(PAGE_ID),
              f"{tag}: {f.name} page-count state")
        m, vram = d.get("clock_marks_ns") or {}, d.get("vram") or {}
        g = m.get("generate_start")
        wins.append(dict(first_page=d["first_page"], pages=d["pages"], tokens=len(ids),
                         engine_s=(d["engine_end_ns"] - d["engine_begin_ns"]) / 1e9,
                         ttft_s=(m["first_token"] - g) / 1e9 if g is not None and "first_token" in m else None,
                         decode_span_s=(m["last_token"] - m["first_token"]) / 1e9
                         if "last_token" in m and "first_token" in m else None,
                         finish_reason=d.get("finish_reason"), num_pages_out=d.get("num_pages_out"),
                         expected_pages=d.get("expected_pages"), kernel_path=d.get("kernel_path"),
                         native_time_s=d.get("time_s"), prefill_time_s=d.get("prefill_time_s"),
                         prompt_len=d.get("prompt_len"), visual_tokens=d.get("visual_tokens"),
                         cuda_max_allocated_bytes=vram.get("cuda_max_allocated_bytes"),
                         cuda_max_reserved_bytes=vram.get("cuda_max_reserved_bytes"),
                         raw_output_sha256=sha(d["raw_output"].encode("utf-8")),
                         token_ids_sha256=sha(json.dumps(ids).encode()), **{k: d.get(k) for k in COUNTERS}))
    check(covered == list(range(1, n + 1)), f"{tag}: windows do not cover pages exactly once in order")
    pc = t.get("page_committed_ns") or []
    check(t.get("status") == "completed" and t.get("complete_pages") == n, f"{tag}: completion record")
    check(len(pc) == n and t["accepted_ns"] < t["first_page_committed_ns"] == pc[0] and pc == sorted(pc)
          and pc[-1] <= t["document_committed_ns"], f"{tag}: clock order")
    check(abs(t["elapsed_s"] - (t["document_committed_ns"] - t["accepted_ns"]) / 1e9) < 1e-6, f"{tag}: elapsed")
    info.update(complete_s=t["elapsed_s"], first_page_s=t["first_page_s"],
                last_page_s=(pc[-1] - t["accepted_ns"]) / 1e9 if pc else None,
                pages_per_min=60 * n / t["elapsed_s"], accepted_ns=t["accepted_ns"],
                document_committed_ns=t["document_committed_ns"], prediction=str(folder / "prediction.json"),
                prediction_sha256=t.get("prediction_sha256"), windows=wins, grammar_pages=grams,
                grammar=totals(grams))
    return info, raws


def segment_checks(run, si, mode, seg, reqs, timings, process, check):
    tag = f"{run.name}/{seg.name}"
    check(seg.is_dir(), f"{tag}: missing segment directory")
    check((seg / "plan.json").is_file() and load(seg / "plan.json") == dict(mode=mode, requests=reqs),
          f"{tag}: segment plan differs")
    child = load(seg / "child.json") if (seg / "child.json").is_file() else {}
    check(child.get("mode") == mode, f"{tag}: child record mode")
    lp = seg / f"load-{mode}.json"
    load_info = load(lp) if check(lp.is_file(), f"{tag}: load record") else {}
    sp = load(seg / "segment-process.json") if (seg / "segment-process.json").is_file() else {}
    check(sp.get("returncode") == 0 and sp.get("reason") is None and sp.get("mode") == mode, f"{tag}: segment outcome")
    session = load(seg / "session.json") if (seg / "session.json").is_file() else None
    check(session == timings, f"{tag}: session.json differs from per-document timing records")
    starts = [seg / f"started-{i:02d}.json" for i in range(1, len(reqs) + 1)]
    check(all(s.is_file() for s in starts) and not list(seg.glob("failure-*.json")), f"{tag}: start/failure records")
    first_start = load(starts[0])["start_ns"] if starts[0].is_file() else None
    samples = [s for s in process.get("gpu_samples") or [] if s.get("segment") == si]
    before, after = sp.get("gpu_before_segment") or {}, sp.get("gpu_after_segment") or {}
    return dict(segment=si, mode=mode, child_pid=child.get("pid"), segment_wall_s=sp.get("elapsed_s"),
                cold_load_s=load_info.get("elapsed_s"), first_dispatch_ns=first_start,
                load_info={k: v for k, v in load_info.items() if k not in ("platform", "dependencies", "verified_modules",
                                                                             "renderer")},
                identity={k: load_info.get(k) for k in ("model_revision", "manifest_sha256", "dependency_lock_sha256",
                                                         "tokenizer_sha256", "eos_id", "page_id", "target_dtype")},
                device=dict(samples=len(samples), sample_cadence_s=5.0,
                            used_peak_mib=max((s["used_mib"] for s in samples), default=None),
                            free_min_mib=min((s["free_mib"] for s in samples), default=None),
                            temperature_max_c=max((s["temperature_c"] for s in samples), default=None),
                            before_used_mib=before.get("used_mib"), after_used_mib=after.get("used_mib")))


def parity(a, b):
    first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
    if first is None and len(a) != len(b):
        first = min(len(a), len(b))
    return dict(identical=a == b, len_a=len(a), len_b=len(b), first_mismatch=first)


def page_diffs(ra, rb):
    out = []
    for i in sorted(set(ra) & set(rb)):
        ta, tb = ra[i]["token_ids"], rb[i]["token_ids"]
        xa, xb = ra[i]["raw_output"], rb[i]["raw_output"]
        ba, bb = BOX.findall(xa), BOX.findall(xb)
        deltas = [abs(int(p) - int(q)) for x, y in zip(ba, bb) for p, q in zip(x, y)]
        out.append(dict(page=i, tokens=[len(ta), len(tb)],
                        differing_positions=sum(x != y for x, y in zip(ta, tb)) + abs(len(ta) - len(tb)),
                        raw_identical=xa == xb, text_outside_boxes_identical=BOX.sub("[]", xa) == BOX.sub("[]", xb),
                        boxes=[len(ba), len(bb)], boxes_differing=sum(x != y for x, y in zip(ba, bb)),
                        max_coordinate_delta=max(deltas or [0])))
    return out


def compare_tokens(ra, rb):
    a = [x for i in sorted(ra) for x in ra[i]["token_ids"]]
    b = [x for i in sorted(rb) for x in rb[i]["token_ids"]]
    pages = page_diffs(ra, rb)
    return dict(parity(a, b), pages_identical=sum(p["differing_positions"] == 0 for p in pages), pages=len(pages),
                pages_text_outside_boxes_identical=sum(p["text_outside_boxes_identical"] for p in pages),
                max_coordinate_delta=max((p["max_coordinate_delta"] for p in pages), default=0), per_page=pages)


def arm_summary(seg_info, docs):
    meas = [d for d in docs if not d["warmup"]]
    allw = [w for d in docs for w in d.get("windows", [])]
    mw = [w for d in meas for w in d.get("windows", [])]
    alloc = [w["cuda_max_allocated_bytes"] for w in allw if w["cuda_max_allocated_bytes"] is not None]
    resv = [w["cuda_max_reserved_bytes"] for w in allw if w["cuda_max_reserved_bytes"] is not None]
    span = None
    if seg_info["first_dispatch_ns"] is not None and docs and "document_committed_ns" in docs[-1]:
        span = (docs[-1]["document_committed_ns"] - seg_info["first_dispatch_ns"]) / 1e9
    wall = seg_info["segment_wall_s"]
    return dict(
        windows_total=len(allw), windows_warm=len(allw) - len(mw), windows_measured=len(mw),
        warmup_s=[d.get("complete_s") for d in docs if d["warmup"]],
        stops=dict(Counter(w["finish_reason"] for w in allw)),
        failed_or_fallback_windows=sum(w["finish_reason"] != "stop" or bool(w.get("prefill_moe_fallback_layer_calls"))
                                       for w in allw),
        counters={k: sum(w[k] or 0 for w in mw) for k in COUNTERS},
        counters_present={k: any(w[k] is not None for w in mw) for k in COUNTERS},
        kernel_paths=dict(Counter(str(w["kernel_path"]) for w in mw)),
        allocator=dict(max_allocated_mib=max(alloc) / MIB if alloc else None,
                       max_reserved_mib=max(resv) / MIB if resv else None, windows_reporting=len(resv),
                       weight_allocated_after_pack_mib=(seg_info["load_info"].get("weight_allocated_bytes_after_pack") or 0) / MIB
                       or None),
        device=seg_info["device"],
        walls=dict(cold_load_s=seg_info["cold_load_s"], segment_wall_s=wall, serving_span_s=span,
                   outside_serving_s=(wall - span) if wall is not None and span is not None else None,
                   note="outside_serving_s = supervisor-observed child wall minus in-child first-dispatch..last-commit "
                        "span; an upper bound on start-to-ready that also includes teardown"),
        grammar_measured=totals([g for d in meas for g in d.get("grammar_pages", [])]),
        grammar_warm=totals([g for d in docs if d["warmup"] for g in d.get("grammar_pages", [])]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inventory", type=Path, required=True)
    ap.add_argument("--plans", type=Path, required=True)
    ap.add_argument("--inputs", type=Path, required=True, help="directory with H/ and A/ input-only files")
    ap.add_argument("--pins", type=Path, required=True)
    ap.add_argument("--source", required=True, help="bound full 40-hex source the runs must report")
    ap.add_argument("--lease", help="bound lease identifier the runs must report")
    ap.add_argument("--out", type=Path, required=True, help="new directory")
    a = ap.parse_args()
    check = Check()
    fmt, rule = load_formats(a.pins), title_rule(a.pins)
    inv = load(a.inventory)
    record = load(a.plans)
    check(sha_file(a.plans) == inv["plans_record_sha256"], "plan record differs from the one inventoried")
    pins = inputs(record, a.inputs, check)
    runs, arms, raws = {}, {}, {}
    for ir in inv["runs"]:
        run = Path(ir["path"])
        immutable(ir, check)
        plan_bytes = (run / "plan.json").read_bytes()
        order = order_of(record, sha(plan_bytes))
        if not check(order is not None, f"{run.name}: plan matches no bound order"):
            continue
        bound = record["orders"][order]
        coord_plan = Path(bound["path"])
        if coord_plan.is_file():
            check(coord_plan.read_bytes() == plan_bytes, f"{run.name}: run plan bytes differ from coordinator plan file")
        launch, process = load(run / "launch.json"), load(run / "process.json")
        check(launch.get("source") == a.source, f"{run.name}: launched source {launch.get('source')} != bound {a.source}")
        check(launch.get("plan_sha256") == bound["sha256"], f"{run.name}: launch plan digest")
        check(a.lease is None or launch.get("lease") == a.lease, f"{run.name}: lease {launch.get('lease')!r}")
        check(launch.get("segment_modes") == bound["order"], f"{run.name}: segment order")
        check(process.get("all_segments_completed") is True and process.get("overall_reason") is None,
              f"{run.name}: process outcome")
        requests = json.loads(plan_bytes)["requests"]
        for r in requests:
            if r["warmup"]:
                check(r["pages"] == 1 and r["sha256"] == record["warm_sha256"] and r["rgb_sha256"] == [record["warm_rgb_sha256"]],
                      f"{run.name}: warm-up request binding {r['label']}")
            else:
                fam = LABEL_FAMILY.get(r["label"])
                check(fam is not None and r["sha256"] == pins[fam]["sha256"] and r["pages"] == pins[fam]["pages"]
                      and r["rgb_sha256"] == pins[fam]["rgb"], f"{run.name}: measured request binding {r['label']}")
        segs = split_segments(requests)
        check(len(process.get("segments") or []) == len(segs), f"{run.name}: segment receipts")
        docs_by_seg = {}
        for si, mode, seg, req, folder in layout(run, requests):
            info, rw = verify_doc(folder, req, fmt, rule, check)
            docs_by_seg.setdefault((si, mode, seg), []).append((req, info, rw))
        run_out = dict(order=order, source=launch.get("source"), head=launch.get("head"), lease=launch.get("lease"),
                       elapsed_s=process.get("elapsed_s"), arms={})
        for (si, mode, seg), items in docs_by_seg.items():
            reqs = [req for req, _, _ in items]
            timings = [load(i["folder"] + "/timing.json") if Path(i["folder"], "timing.json").is_file() else None
                       for _, i, _ in items]
            sinfo = segment_checks(run, si, mode, seg, reqs, timings, process, check)
            docs = [i for _, i, _ in items]
            summary = arm_summary(sinfo, docs)
            check(summary["windows_warm"] == 3 and summary["windows_measured"] ==
                  sum(-(-p["pages"] // WINDOW) for p in reqs if not p["warmup"]), f"{run.name}/{seg.name}: window counts")
            measured = {LABEL_FAMILY[i["label"]]: {k: v for k, v in i.items() if k != "grammar_pages"}
                        for i in docs if not i["warmup"] and i["label"] in LABEL_FAMILY}
            run_out["arms"][mode] = dict(segment=sinfo, summary=summary, measured=measured,
                                         grammar_pages={LABEL_FAMILY[i["label"]]: i.get("grammar_pages")
                                                        for i in docs if not i["warmup"] and i["label"] in LABEL_FAMILY})
            for _, i, rw in items:
                if not i["warmup"] and i["label"] in LABEL_FAMILY:
                    arms[order, mode, LABEL_FAMILY[i["label"]]] = i
                    raws[order, mode, LABEL_FAMILY[i["label"]]] = rw or {}
        runs[run.name] = run_out
    orders = sorted(r["order"] for r in runs.values())
    check(orders == ["ab", "ba"], f"orders present {orders}")
    identities = {json.dumps(arm["segment"]["identity"], sort_keys=True) for r in runs.values() for arm in r["arms"].values()}
    check(len(identities) == 1, "model/tokenizer/lock identity differs between arms")
    timing, tokens = {}, {}
    for fam in ("H", "A"):
        get = lambda o, m: arms.get((o, m, fam), {}).get("complete_s")
        pairs = {o: dict(native_s=get(o, "native"), carbon_s=get(o, "carbon_bf16")) for o in ("ab", "ba")}
        for p in pairs.values():
            if None not in p.values():
                p.update(saving_s=p["native_s"] - p["carbon_s"], speedup=p["native_s"] / p["carbon_s"])
        spread = {m: abs(get("ab", m) - get("ba", m)) if None not in (get("ab", m), get("ba", m)) else None
                  for m in ("native", "carbon_bf16")}
        sv = [p.get("saving_s") for p in pairs.values()]
        timing[fam] = dict(pairs=pairs, repeat_spread_s=spread,
                           first_page_s={f"{o}:{m}": arms.get((o, m, fam), {}).get("first_page_s")
                                         for o in ("ab", "ba") for m in ("native", "carbon_bf16")},
                           savings_exceed_native_spread=None if None in sv or spread["native"] is None
                           else all(s > spread["native"] for s in sv),
                           savings_exceed_both_spreads=None if None in sv or None in spread.values()
                           else all(s > max(spread.values()) for s in sv),
                           note="one observation per arm and order; no percentile follows")
        r = lambda o, m: raws.get((o, m, fam), {})
        tokens[fam] = {"ab:carbon_vs_native": compare_tokens(r("ab", "native"), r("ab", "carbon_bf16")),
                       "ba:carbon_vs_native": compare_tokens(r("ba", "native"), r("ba", "carbon_bf16")),
                       "native:ab_vs_ba": compare_tokens(r("ab", "native"), r("ba", "native")),
                       "carbon:ab_vs_ba": compare_tokens(r("ab", "carbon_bf16"), r("ba", "carbon_bf16"))}
    memory = {}
    for rn, r in runs.items():
        for mode, arm in r["arms"].items():
            s = arm["summary"]
            dev, alloc = s["device"]["used_peak_mib"], s["allocator"]["max_reserved_mib"]
            memory[f"{r['order']}:{mode}"] = dict(
                device_used_peak_mib=dev, device_before_used_mib=s["device"]["before_used_mib"],
                device_samples=s["device"]["samples"], allocator_max_reserved_mib=alloc,
                allocator_max_allocated_mib=s["allocator"]["max_allocated_mib"],
                device_within_g0=None if dev is None else dev <= G0["peak_mib_max"],
                allocator_within_g0=None if alloc is None else alloc <= G0["peak_mib_max"])
    out = dict(stage=1, reviewer="eld-rd-reviewer", created_utc=utc(), inventory_sha256=sha_file(a.inventory),
               plans_record_sha256=sha_file(a.plans), real_binding=is_pinned(a.plans, "g0-plans.json"),
               pinned_plans_record=PINS["g0-plans.json"][2], bound_source=a.source, bound_lease=a.lease,
               checks_run=check.count, failures=check.failures, runs=runs, timing=timing, token_parity=tokens,
               memory=memory, g0_memory_rule="carbon_bf16 arm: sampled device used and allocator reserved peaks are "
                                              "each compared with 10,000 MiB and reported separately; native reported")
    a.out.mkdir(parents=True, exist_ok=False)
    digest = write_new(a.out / "stage1.json", out)
    print(json.dumps(dict(stage1=str(a.out / "stage1.json"), sha256=digest, real_binding=out["real_binding"],
                          checks_run=check.count, failures=check.failures[:20], failure_count=len(check.failures),
                          memory=memory,
                          timing={f: {o: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in p.items()}
                                      for o, p in t["pairs"].items()} for f, t in timing.items()},
                          token_identical={f: {k: v["identical"] for k, v in t.items()} for f, t in tokens.items()}),
                     indent=1))
    return 1 if check.failures else 0


if __name__ == "__main__":
    sys.exit(main())
