"""eld-rd-reviewer post-run verifier and scoring driver for WP-0015 replay. Standard library only.

Stage 1 (after predictions are committed, before any key): `--runs` verifies each launched process
against the frozen source/plan, the RGB pins, durable page/window publication, native token/page state
and the clocks, and derives paired timing, order effects and control noise.
Stage 2 (after the custodian's separate scoring release): add `--truth` and `--rasters`. The frozen
custodian score.py runs in a separate process for every prediction (Windows against its same-process
native control; native repeats against each other). Supplemental reviewer diagnostics are reported
separately and never change frozen gate outcomes.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCORE = ROOT / "docs/evaluation/WP-0015/score.py"
COMMIT = ROOT / "docs/evaluation/WP-0015/commitments.json"
NUM = re.compile(r"[+-]?[\w]+(?:[.,-][\w]+)*")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def norm(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


class Check:
    def __init__(self):
        self.failures = []

    def __call__(self, ok, what):
        if not ok:
            self.failures.append(what)
        return ok


def verify_document(folder, pins, page_id, check):
    timing = load(folder / "timing.json")
    req = timing["request"]
    tag = folder.name
    pred_bytes = (folder / "prediction.json").read_bytes()
    check(sha(pred_bytes) == timing["prediction_sha256"], f"{tag}: prediction hash != timing record")
    pred = json.loads(pred_bytes)
    n = req["pages"]
    check(pred["source_sha256"] == req["sha256"], f"{tag}: prediction source")
    check([p["page"] for p in pred["pages"]] == list(range(1, n + 1)), f"{tag}: page ordinals")
    check(not list(folder.glob("*.pending")), f"{tag}: leftover pending writes")
    check(req["rgb_sha256"] == (pins if not req["warmup"] else req["rgb_sha256"]), f"{tag}: plan pins differ")
    pages = []
    for i, p in enumerate(pred["pages"], 1):
        raw = load(folder / f"raw-{i:03d}.json")
        check(load(folder / f"page-{i:03d}.json") == p, f"{tag}: page-{i:03d} != prediction entry")
        check(raw["source_sha256"] == req["sha256"] == p["source_sha256"], f"{tag}: raw/page source p{i}")
        check(raw["page"] == i and raw["rgb_sha256"] == req["rgb_sha256"][i - 1], f"{tag}: raw rgb/page p{i}")
        pages.append(dict(page=i, state=p["state"], raw=raw))
    windows = sorted(folder.glob("window-*.json"))
    covered, wins = [], []
    for w in windows:
        d = load(w)
        check(d["source_sha256"] == req["sha256"], f"{tag}: {w.name} source")
        span = list(range(d["first_page"], d["first_page"] + d["pages"]))
        covered += span
        info = dict(first_page=d["first_page"], pages=d["pages"], engine_s=(d["engine_end_ns"] - d["engine_begin_ns"]) / 1e9)
        if req["mode"] == "native":
            toks = d["window_token_ids"]
            per = [t for i in span for t in pages[i - 1]["raw"]["token_ids"]]
            starts = [pages[i - 1]["raw"]["token_ids"][:1] for i in span]
            check(per == toks, f"{tag}: {w.name} page tokens do not reassemble window tokens")
            check(all(s == [page_id] for s in starts), f"{tag}: {w.name} page does not start at <PAGE>")
            check(d["finish_reason"] == "stop" and d["num_pages_out"] == d["expected_pages"] == d["pages"],
                  f"{tag}: {w.name} native stop/page state")
            check(d["raw_output"] == "".join(pages[i - 1]["raw"]["raw_output"] for i in span),
                  f"{tag}: {w.name} raw text does not reassemble")
            m = d["clock_marks_ns"]
            gen = (m.get("generate_end", 0) - m.get("generate_start", 0)) / 1e9
            put = (m["last_token"] - m["first_token"]) / 1e9 if "first_token" in m else None
            info.update(tokens=len(toks), forward_count=d["forward_count"], kernel_path=d["kernel_path"],
                        triton_starts=d["triton_starts"], dense_starts=d["dense_starts"],
                        native_time_s=d["time_s"], prefill_s=d["prefill_time_s"], prompt_len=d["prompt_len"],
                        generate_s=gen, streamer_span_s=put,
                        tokens_per_s_streamer=(len(toks) - 1) / put if put else None,
                        vision_s=(m["vision_end"] - m["vision_start"]) / 1e9 if "vision_end" in m else None,
                        ttft_s=(m["first_token"] - m["generate_start"]) / 1e9 if "first_token" in m else None,
                        token_classes=[pages[i - 1]["raw"]["token_classes"] for i in span])
        else:
            info.update(words=d["windows_ocr_words"], recognize_ms=d["recognize_ms"],
                        reader_and_layout_s=d["reader_and_layout_ns"] / 1e9)
        wins.append(info)
    check(covered == list(range(1, n + 1)), f"{tag}: windows do not cover pages exactly once in order")
    check(timing["complete_pages"] == n and timing["status"] == "completed", f"{tag}: completion record")
    check(timing["accepted_ns"] < timing["first_page_committed_ns"] <= timing["document_committed_ns"],
          f"{tag}: clock order")
    return dict(folder=str(folder), label=req["label"], mode=req["mode"], warmup=req["warmup"], pages=n,
                elapsed_s=timing["elapsed_s"], first_page_s=timing["first_page_s"],
                pages_per_min=60 * n / timing["elapsed_s"], prediction=str(folder / "prediction.json"),
                prediction_sha256=timing["prediction_sha256"], windows=wins,
                token_ids=[t for i in range(1, n + 1) for t in (pages[i - 1]["raw"].get("token_ids") or [])])


def verify_run(run, source, pins, check):
    tag = run.name
    launch, process = load(run / "launch.json"), load(run / "process.json")
    plan = (run / "plan.json").read_bytes()
    check(launch["source"] == source, f"{tag}: launched source {launch['source']} != {source}")
    check(launch["plan_sha256"] == sha(plan), f"{tag}: plan digest")
    check(process["returncode"] == 0 and process["reason"] is None, f"{tag}: process outcome {process}")
    check((run / "child.json").exists() and (run / "session.json").exists(), f"{tag}: child/session records")
    loads = {p.stem[5:]: load(p) for p in run.glob("load-*.json")}
    page_id = loads.get("native", {}).get("page_id")
    requests = json.loads(plan)["requests"]
    docs = []
    for i, r in enumerate(requests, 1):
        folder = run / f"{i:02d}-{r['label']}-{r['mode']}"
        if not check((folder / "timing.json").exists(), f"{tag}: no timing for {folder.name}"):
            continue
        docs.append(dict(verify_document(folder, pins, page_id, check), position=i))
    order = "".join("a" if r["mode"] == "native" else "b" for r in requests if not r["warmup"])
    gpu = process.get("gpu_samples") or []
    return dict(run=tag, order=order, launch=launch, elapsed_s=process["elapsed_s"],
                load_s={k: v["elapsed_s"] for k, v in loads.items()},
                gpu_peak_used_mib=max((s["used_mib"] for s in gpu), default=None),
                gpu_min_free_mib=min((s["free_mib"] for s in gpu), default=None),
                gpu_max_temp_c=max((s["temperature_c"] for s in gpu), default=None), documents=docs)


def timing_summary(runs):
    by = {}
    for r in runs:
        for d in r["documents"]:
            if not d["warmup"]:
                by.setdefault(d["mode"], []).append(dict(run=r["run"], order=r["order"], s=d["elapsed_s"]))
    pairs = []
    for r in runs:
        m = {d["mode"]: d for d in r["documents"] if not d["warmup"]}
        if {"native", "windows"} <= set(m):
            pairs.append(dict(run=r["run"], order=r["order"], native_s=m["native"]["elapsed_s"],
                              windows_s=m["windows"]["elapsed_s"],
                              saving_s=m["native"]["elapsed_s"] - m["windows"]["elapsed_s"],
                              speedup=m["native"]["elapsed_s"] / m["windows"]["elapsed_s"]))
    spread = {k: (max(v["s"] for v in xs) - min(v["s"] for v in xs)) if len(xs) > 1 else None for k, xs in by.items()}
    noise = spread.get("native")
    orders = {p["order"] for p in pairs}
    return dict(per_mode=by, pairs=pairs, control_spread_s=noise, windows_spread_s=spread.get("windows"),
                both_orders_present=orders >= {"ab", "ba"},
                every_pair_saving_exceeds_control_spread=(noise is not None and bool(pairs) and
                                                          all(p["saving_s"] > noise for p in pairs)),
                note="Single observation per arm and order; no population percentile follows.")


def token_parity(runs):
    native = [(r["run"], d) for r in runs for d in r["documents"] if d["mode"] == "native" and not d["warmup"]]
    out = []
    for i in range(len(native)):
        for j in range(i + 1, len(native)):
            (ra, a), (rb, b) = native[i], native[j]
            ta, tb = a["token_ids"], b["token_ids"]
            first = next((k for k, (x, y) in enumerate(zip(ta, tb)) if x != y), None)
            out.append(dict(a=ra, b=rb, identical=ta == tb, len_a=len(ta), len_b=len(tb),
                            first_divergence=first if first is not None or len(ta) == len(tb) else min(len(ta), len(tb))))
    return out


def score_once(truth, pred, out, baseline=None):
    cmd = [sys.executable, "-B", str(SCORE), str(truth), str(pred), "--out", str(out)]
    if baseline:
        cmd[5:5] = ["--baseline", str(baseline)]
    if out.exists():
        raise SystemExit("score output exists: " + str(out))
    subprocess.run(cmd, check=True, cwd=SCORE.parent)
    return load(out)


def numeric_tokens(text):
    return Counter(t for t in NUM.findall(norm(text)) if any(c.isdigit() for c in t))


def diagnostics(truth, pred):
    """Reviewer-only checks for classes the frozen gates do not flag (see precheck S2-S4, N2)."""
    refs = {p["page"]: p for p in truth["pages"]}
    pages = {p["page"]: p for p in pred["pages"]}
    surplus, deficits, misplaced, alignment = {}, {}, [], []
    for n, ref in refs.items():
        got = pages.get(n, {}).get("text", "")
        want, have = numeric_tokens(ref["text"]), numeric_tokens(got)
        if have - want:
            surplus[n] = dict(have - want)
        if want - have:
            deficits[n] = dict(want - have)
        for tok in have - want:
            homes = [m for m, r in refs.items() if m != n and tok in numeric_tokens(r["text"])]
            if homes:
                misplaced.append(dict(page=n, token=tok, printed_on=homes))
        if norm(ref["text"]) and got:
            def d(a, b):
                a, b = norm(a), norm(b)
                last = list(range(len(b) + 1))
                for i, ca in enumerate(a, 1):
                    cur = [i]
                    for j, cb in enumerate(b, 1):
                        cur.append(min(last[j] + 1, cur[-1] + 1, last[j - 1] + (ca != cb)))
                    last = cur
                return last[-1] / max(1, len(b))
            scores = {m: d(got, r["text"]) for m, r in refs.items() if norm(r["text"])}
            best = min(scores, key=scores.get)
            if scores[best] < scores.get(n, float("inf")):
                alignment.append(dict(page=n, best_matching_truth_page=best, own=scores[n], best=scores[best]))
    flags = sum(bool(s.get("flagged")) for p in pred["pages"] for s in p.get("spans", [])) + sum(
        isinstance(c, dict) and bool(c.get("flagged")) for p in pred["pages"] for t in p.get("tables", [])
        for row in t["rows"] for c in row)
    return dict(numeric_surplus_by_page=surplus, numeric_deficit_by_page=deficits,
                numeric_tokens_printed_on_other_pages=misplaced, pages_better_matching_other_truth=alignment,
                flagged_entries=flags)


def critical_split(scored, pred):
    """Separate recognised-but-unlocalised critical values from absent/misread ones."""
    text = {p["page"]: norm(p["text"]) for p in pred["pages"]}
    out = []
    for p in scored["pages"]:
        for c in p["critical"]:
            if not c["correct"]:
                pat = r"(?<![\w.,+-])" + re.escape(c["expected"]) + r"(?![\w+-]|[.,]\d)"
                out.append(dict(at=c["at"], expected=c["expected"], observed=c["observed"], flagged=c["flagged"],
                                value_present_on_page_text=re.search(pat, text.get(p["page"], "")) is not None))
    return out


def table_ious(truth, pred):
    def iou(a, b):
        ov = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
        ar = lambda r: (r[2] - r[0]) * (r[3] - r[1])
        return ov / (ar(a) + ar(b) - ov) if ov else 0.0
    out = []
    for ref in truth["pages"]:
        got = next((p for p in pred["pages"] if p["page"] == ref["page"]), {})
        for ti, t in enumerate(ref["tables"]):
            best = max((iou(t["bbox"], g["bbox"]) for g in got.get("tables", []) if isinstance(g.get("bbox"), list)),
                       default=0.0)
            out.append(dict(page=ref["page"], table=ti + 1, best_iou=round(best, 3),
                            predicted_tables=len(got.get("tables", []))))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, nargs="+", required=True)
    ap.add_argument("--pins", type=Path, required=True, help="the same RGB pins file given to make_plans.py")
    ap.add_argument("--source", default="82206bc4b77654010ac02364adaaf589d1f36780")
    ap.add_argument("--family", required=True)
    ap.add_argument("--truth", type=Path, help="stage 2 only: released truth.json")
    ap.add_argument("--rasters", type=Path, help="stage 2 only: released rasters.json")
    ap.add_argument("--author-saving-s", type=float, help="author's matched saving on the same comparison")
    ap.add_argument("--out", type=Path, required=True, help="new directory")
    a = ap.parse_args()
    from make_plans import read_pins  # same parser as the plans
    commitments = load(COMMIT)["packets"]
    pages = (commitments[a.family]["pages"] if a.family in commitments else
             len(load(ROOT / "docs/evaluation/WP-0015/dev" / a.family / "rasters.json")["pages"]))
    pins = read_pins(a.pins, pages)
    check = Check()
    runs = [verify_run(r, a.source, pins, check) for r in a.runs]
    a.out.mkdir(parents=True, exist_ok=False)
    result = dict(stage=1, family=a.family, source=a.source, pins_sha256=sha(a.pins.read_bytes()),
                  runs=[{k: v for k, v in r.items()} for r in runs], timing=timing_summary(runs),
                  native_token_parity=token_parity(runs))
    for r in result["runs"]:
        for d in r["documents"]:
            d.pop("token_ids")
    if a.author_saving_s is not None:
        pairs = result["timing"]["pairs"]
        result["timing"]["same_sign_as_author"] = bool(pairs) and all(
            (p["saving_s"] > 0) == (a.author_saving_s > 0) for p in pairs)
    if a.truth:
        result["stage"] = 2
        truth_bytes = a.truth.read_bytes()
        truth = json.loads(truth_bytes)
        if a.family in commitments:
            files = commitments[a.family]["files"]
            check(sha(truth_bytes) == files["truth.json"], "truth commitment")
            check(sha(a.rasters.read_bytes()) == files["rasters.json"], "rasters commitment")
        released = [p["rgb_sha256"] for p in sorted(load(a.rasters)["pages"], key=lambda p: p["page_number"])]
        check(released == pins, "pins used for inference differ from the custodian's released rasters")
        scores, natives = {}, []
        for r in runs:
            docs = {d["mode"]: d for d in r["documents"] if not d["warmup"]}
            base = docs.get("native")
            if base:
                natives.append((f"{r['run']}-native", base))
            for mode, d in docs.items():
                key = f"{r['run']}-{mode}"
                s = score_once(a.truth, d["prediction"], a.out / f"score-{key}.json",
                               base["prediction"] if base and mode != "native" else None)
                pred = load(d["prediction"])
                scores[key] = dict(counts=s["counts"], packet_complete=s["packet_complete"],
                                   faults=Counter(f["issue"] for f in s["faults"]), comparison=s.get("comparison"),
                                   diagnostics=diagnostics(truth, pred), critical_errors=critical_split(s, pred),
                                   table_iou=table_ious(truth, pred))
        repeat = []
        for i, (key, d) in enumerate(natives[1:], 1):
            s = score_once(a.truth, d["prediction"], a.out / f"score-control-repeat-{i}.json", natives[0][1]["prediction"])
            repeat.append(dict(a=natives[0][0], b=key, comparison=s["comparison"]))
        result.update(scores=scores, control_quality_repeat=repeat)
    result["failures"] = check.failures
    with (a.out / "analysis.json").open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(failures=check.failures, timing=result["timing"]), indent=2))
    return 1 if check.failures else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
