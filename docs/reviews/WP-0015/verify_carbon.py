"""Independent verification and scoring of the reviewer Carbon H pair (segmented layout). CPU only.

For h-carbon-ab / h-carbon-ba: process outcome, durable publication, RGB pins, page/window coverage,
<PAGE> starts, token and raw reassembly, stop/page state, clocks. Token parity of carbon_bf16 against the
same-run native, the other order and the original H native (first mismatch if any). Frozen score.py in a
separate process per prediction, the public title<LEVELn> sensitivity rule (commit 0186467), critical
transitions, reviewer supplemental checks, and the three-way H decision with the earlier Windows runs.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EVAL = ROOT / "docs/evaluation/WP-0015"
ASTRA = ROOT / "docs/research/WP-0015/astra"
sys.path[:0] = [str(EVAL), str(ASTRA), str(ASTRA / "sensitivity-title-level"), str(HERE)]
from score import compare, score  # noqa: E402
from scored_summary import corrected_native, counts, diag, transitions  # noqa: E402

PKT = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0015/review")
SOURCE = "7e70391cd790a95c68906902dbd9d5bc479aa9c0"
PAGE_ID = 128827


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def verify_doc(folder, pins, sha_pdf, fail):
    t = load(folder / "timing.json")
    req = t["request"]
    tag = f"{folder.parent.parent.name}/{folder.parent.name}/{folder.name}"
    pb = (folder / "prediction.json").read_bytes()
    pred = json.loads(pb)
    n = req["pages"]
    ok = lambda c, m: c or fail.append(f"{tag}: {m}")
    ok(hashlib.sha256(pb).hexdigest() == t["prediction_sha256"], "prediction hash != timing")
    ok(pred["source_sha256"] == req["sha256"] and [p["page"] for p in pred["pages"]] == list(range(1, n + 1)), "ordinals/source")
    ok(not list(folder.glob("*.pending")), "pending writes")
    if not req["warmup"]:
        ok(req["sha256"] == sha_pdf and req["rgb_sha256"] == pins, "request not bound to released H")
    raws = {}
    for i, p in enumerate(pred["pages"], 1):
        raw = load(folder / f"raw-{i:03d}.json")
        ok(load(folder / f"page-{i:03d}.json") == p, f"page-{i:03d} != prediction")
        ok(raw["page"] == i and raw["rgb_sha256"] == req["rgb_sha256"][i - 1], f"p{i} rgb pin")
        ok(raw["source_sha256"] == p["source_sha256"] == req["sha256"], f"p{i} source")
        ok(raw["token_ids"][:1] == [PAGE_ID] and p["state"] == "complete", f"p{i} <PAGE> start/state")
        raws[i] = raw
    covered, wins = [], []
    for w in sorted(folder.glob("window-*.json")):
        d = load(w)
        span = list(range(d["first_page"], d["first_page"] + d["pages"]))
        covered += span
        ok([x for i in span for x in raws[i]["token_ids"]] == d["window_token_ids"], f"{w.name} token reassembly")
        ok("".join(raws[i]["raw_output"] for i in span) == d["raw_output"], f"{w.name} raw reassembly")
        ok(d["finish_reason"] == "stop" and d["num_pages_out"] == d["expected_pages"] == d["pages"], f"{w.name} stop/page")
        m = d.get("clock_marks_ns", {})
        wins.append(dict(first_page=d["first_page"], pages=d["pages"], tokens=len(d["window_token_ids"]),
                         engine_s=round((d["engine_end_ns"] - d["engine_begin_ns"]) / 1e9, 3),
                         ttft_s=round((m["first_token"] - m["generate_start"]) / 1e9, 3) if "first_token" in m and "generate_start" in m else None,
                         forward_count=d.get("forward_count"), burst_extra_forwards=d.get("burst_extra_forwards"),
                         static_cache_reallocations=d.get("static_cache_reallocations"),
                         prefill_grouped_mm_layer_calls=d.get("prefill_grouped_mm_layer_calls"),
                         prefill_moe_fallback_layer_calls=d.get("prefill_moe_fallback_layer_calls")))
    ok(covered == list(range(1, n + 1)), "window coverage")
    ok(t["complete_pages"] == n and t["status"] == "completed", "completion")
    ok(t["accepted_ns"] < t["first_page_committed_ns"] <= t["page_committed_ns"][-1] <= t["document_committed_ns"], "clock order")
    tokens = [x for i in range(1, n + 1) for x in raws[i]["token_ids"]]
    return dict(folder=str(folder), mode=req["mode"], warmup=req["warmup"], pages=n,
                complete_s=round(t["elapsed_s"], 3), first_page_s=round(t["first_page_s"], 3),
                last_page_s=round((t["page_committed_ns"][-1] - t["accepted_ns"]) / 1e9, 3),
                pages_per_min=round(60 * n / t["elapsed_s"], 2), prediction_sha256=t["prediction_sha256"],
                windows=wins), tokens, pred


def parity(a, b):
    first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
    if first is None and len(a) != len(b):
        first = min(len(a), len(b))
    return dict(identical=a == b, len_a=len(a), len_b=len(b), first_mismatch=first)


def tokens_of(folder):
    pred = load(folder / "prediction.json")
    return [x for p in pred["pages"] for x in load(folder / f"raw-{p['page']:03d}.json")["token_ids"]]


def score_file(truth, pred, out, base=None):
    cmd = [sys.executable, "-B", str(EVAL / "score.py"), str(truth), str(pred), "--out", str(out)]
    if base:
        cmd[5:5] = ["--baseline", str(base)]
    subprocess.run(cmd, check=True, cwd=EVAL)
    return load(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--private", type=Path, required=True, help="new private directory for score files")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    commit = load(EVAL / "commitments.json")["packets"]["H"]
    truth_path, rasters_path = PKT / "scoring-H/truth.json", PKT / "scoring-H/rasters.json"
    truth = load(truth_path)
    pins = [p["rgb_sha256"] for p in load(PKT / "input-H/rasters.input.json")["pages"]]
    verified = dict(truth=sha(truth_path) == commit["files"]["truth.json"], rasters=sha(rasters_path) == commit["files"]["rasters.json"],
                    pins_equal_released=pins == [p["rgb_sha256"] for p in load(rasters_path)["pages"]],
                    input_pdf=sha(PKT / "input-H/source.pdf") == commit["files"]["source.pdf"])
    a.private.mkdir(parents=True, exist_ok=False)
    fail, runs, toks, preds = [], {}, {}, {}
    for name in ("h-carbon-ab", "h-carbon-ba"):
        run = PKT / "runs" / name
        launch, proc = load(run / "launch.json"), load(run / "process.json")
        if launch["source"] != SOURCE or launch["plan_sha256"] != sha(run / "plan.json") or not proc["all_segments_completed"]:
            fail.append(f"{name}: launch/plan/process")
        r = dict(order=[s["mode"] for s in proc["segments"]], lease=launch["lease"], process_s=round(proc["elapsed_s"], 3),
                 gpu_peak_used_mib=max(s["used_mib"] for s in proc["gpu_samples"]),
                 gpu_min_free_mib=min(s["free_mib"] for s in proc["gpu_samples"]),
                 gpu_max_temp_c=max(s["temperature_c"] for s in proc["gpu_samples"]), arms={})
        for seg in sorted(run.glob("segment-*")):
            mode = seg.name.split("-", 2)[2]
            ld = load(seg / f"load-{mode}.json")
            docs = {}
            for f in sorted(p for p in seg.iterdir() if p.is_dir() and p.name != "cache"):
                info, tk, pred = verify_doc(f, pins, commit["files"]["source.pdf"], fail)
                docs["warm" if info["warmup"] else "h"] = info
                if not info["warmup"]:
                    toks[name, mode], preds[name, mode] = tk, (f, pred)
            r["arms"][mode] = dict(load_s=round(ld["elapsed_s"], 3), warmup_s=docs["warm"]["complete_s"],
                                   warmup_prediction_sha256=docs["warm"]["prediction_sha256"], **docs["h"],
                                   flags={k: ld[k] for k in ("use_packed_moe", "use_gather_decode", "use_gpu_burst", "burst_stride") if k in ld})
        runs[name] = r
    orig = tokens_of(PKT / "runs/h-r1-ab/03-h-native")
    par = {f"{run}:{m}_vs_original_H_native": parity(toks[run, m], orig) for (run, m) in toks}
    par.update({f"{run}:carbon_bf16_vs_same_run_native": parity(toks[run, "carbon_bf16"], toks[run, "native"]) for run in runs})
    par["carbon_bf16_ab_vs_ba"] = parity(toks["h-carbon-ab", "carbon_bf16"], toks["h-carbon-ba", "carbon_bf16"])
    par["native_ab_vs_ba"] = parity(toks["h-carbon-ab", "native"], toks["h-carbon-ba", "native"])
    scores = {}
    for (run, mode), (folder, pred) in preds.items():
        base = preds[run, "native"][0] / "prediction.json" if mode != "native" else None
        off = score_file(truth_path, folder / "prediction.json", a.private / f"score-{run}-{mode}.json", base)
        assert off["counts"] == score(truth, pred)["counts"]
        entry = dict(official=counts(off), checks=diag(truth, pred))
        fixed, headers = corrected_native(folder, pred)
        cs = score(truth, fixed)
        entry.update(title_level_corrected=counts(cs), title_level_headers=headers, corrected_checks=diag(truth, fixed))
        scores[f"{run}:{mode}"] = entry
        preds[run, mode] = (folder, pred, score(truth, pred), cs)
    comps = {}
    for run in runs:
        _, _, noff, ncor = preds[run, "native"]
        _, _, coff, ccor = preds[run, "carbon_bf16"]
        for lab, b, t in (("official", noff, coff), ("title_corrected_both", ncor, ccor)):
            c = compare(b, t)
            comps[f"{run}:carbon_bf16_vs_native:{lab}"] = dict(delta={k: None if v is None else round(v, 4) for k, v in c["delta"].items()},
                                                                inside_quality_budget=c["inside_quality_budget"],
                                                                unattended_quality_gate=c["unattended_quality_gate"],
                                                                critical_transitions=transitions(b, t)[0])
    # Earlier Windows H (same released input) against these native controls.
    win_pred = load(PKT / "runs/h-r1-ab/04-h-windows/prediction.json")
    wsc = score(truth, win_pred)
    for run in runs:
        _, _, noff, ncor = preds[run, "native"]
        for lab, b in (("official", noff), ("title_corrected", ncor)):
            c = compare(b, wsc)
            comps[f"{run}:windows_h_r1_vs_native:{lab}"] = dict(delta={k: None if v is None else round(v, 4) for k, v in c["delta"].items()},
                                                                 inside_quality_budget=c["inside_quality_budget"],
                                                                 unattended_quality_gate=c["unattended_quality_gate"])
    nat = [runs[r]["arms"]["native"]["complete_s"] for r in runs]
    car = [runs[r]["arms"]["carbon_bf16"]["complete_s"] for r in runs]
    prior_nat = [load(PKT / f"runs/{r}/{f}/timing.json")["elapsed_s"] for r, f in (("h-r1-ab", "03-h-native"), ("h-r2-ba", "04-h-native"))]
    win = [load(PKT / f"runs/{r}/{f}/timing.json")["elapsed_s"] for r, f in (("h-r1-ab", "04-h-windows"), ("h-r2-ba", "03-h-windows"))]
    spread = round(max(nat) - min(nat), 3)
    savings = {r: round(runs[r]["arms"]["native"]["complete_s"] - runs[r]["arms"]["carbon_bf16"]["complete_s"], 3) for r in runs}
    timing = dict(native_pair_s=nat, carbon_pair_s=car, native_pair_spread_s=spread,
                  native_all_four_spread_s=round(max(nat + prior_nat) - min(nat + prior_nat), 3),
                  carbon_spread_s=round(max(car) - min(car), 3), carbon_saving_s=savings,
                  carbon_speedup={r: round(runs[r]["arms"]["native"]["complete_s"] / runs[r]["arms"]["carbon_bf16"]["complete_s"], 3) for r in runs},
                  both_orders_saving_exceed_native_spread=all(s > spread for s in savings.values()),
                  windows_h_s=[round(x, 3) for x in win])
    exact = all(par[f"{r}:carbon_bf16_vs_same_run_native"]["identical"] for r in runs)
    budget = all(comps[f"{r}:carbon_bf16_vs_native:official"]["inside_quality_budget"] and
                 comps[f"{r}:carbon_bf16_vs_native:title_corrected_both"]["inside_quality_budget"] for r in runs)
    wbudget = any(comps[k]["inside_quality_budget"] for k in comps if "windows" in k)
    decision = dict(fastest_complete="windows", windows_inside_budget=wbudget,
                    carbon_exact_token_parity=exact, carbon_inside_budget=budget,
                    fastest_complete_inside_budget="carbon_bf16" if (exact or budget) and timing["both_orders_saving_exceed_native_spread"] else "native",
                    unattended_any=False, scope="H four-page held-out only; no A/B or 60-page Carbon measurement")
    out = dict(reviewer="eld-rd-reviewer", source=SOURCE, verified=verified, failures=fail, runs=runs, parity=par,
               scores=scores, comparisons=comps, timing=timing, decision=decision,
               private_score_sha256={p.name: sha(p) for p in sorted(a.private.iterdir())})
    with a.out.open("x", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(dict(failures=fail, verified=verified, timing=timing, decision=decision,
                          parity={k: v["identical"] for k, v in par.items()}), indent=1))


if __name__ == "__main__":
    main()
