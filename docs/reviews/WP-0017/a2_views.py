"""WP-0017 A2 both-view scoring adapter (eld-rd-reviewer). Stdlib only, CPU only.

Written by the continuation session (common.OPERATOR) before any A2 output existed. Supersedes the scoring
half of a2_stoploss.py `decide` (kept unchanged as the prior session's version); the pure rules
a2_stoploss.stoploss / astra_a2 / check_orders are reused unchanged.

`prekey` (after the A2 blind inventory is committed and pushed; no key):
  re-verifies every inventoried hash, then validates every document of the six fresh single-arm processes FROM
  ITS RAW CAPTURES: timing request = plan request, prediction digest = timing record, page ordinals, page-NNN =
  prediction entry, raw page/source/RGB pins against the public dev raster record (404712df...), <PAGE> start and
  token count, the stored page equals the pinned frozen projection formats.native_page(raw_output, points),
  window token and raw reassembly, stop and page counts, window coverage, durable clock order and elapsed.
  It derives each run's order from its own segment sequence (AB = native, carbon_bf16, carbon_surgical;
  BA = reverse), requires identical excluded warm-ups across all arms/orders, one 18-page measured document per
  arm with six windows, the dev PDF 56033270... and flagged == false everywhere.
`score` (only after the pre-key record is also committed and pushed; the dev key is then passed by path):
  verifies the inventory and pre-key commits are on origin/review/wp-0017-escrow, the key digest equals its
  custody commitment (dfdf62cb...) without parsing it here, re-verifies the trees, builds the title view with the
  WP-0016 title_adapt.py (blob-verified, with its helper) in its own OS process, scores every (order, arm, view)
  with the frozen score.py (1ceb36fe...) in its own OS process, and VALIDATES PATHS AND METRICS:
    * paths: 18 pages in order, exactly one critical line and two critical table cells per page (54 critical,
      all distinct, as predeclared in the design fixture), the identical critical path sequence in all twelve
      scores, complete matched pairs;
    * metrics: every scorer count is recomputed from its own per-path records (critical values/errors/unflagged/
      flagged, cells, lines, CER = edits/chars, cell accuracy = correct/(cells+extra)); each comparison delta
      equals trial - base from the separate scores; the comparison's trial score equals the separate score; the
      frozen compare's new-or-changed critical set equals the reviewer's transition classes.
  Then applies the unchanged A2 stop-loss and the Astra cross-check. Only counts are published; per-path rows
  with reference values go to a PRIVATE details file.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a2_stoploss as A2  # noqa: E402
from common import (DEV_PDF_SHA256, DEV_RASTERS_SHA256, DEV_TRUTH_SHA256, HERE, PAGE_ID, WP17, Check,  # noqa: E402
                    all_flags_false, blob, blob_module, load, pushed, run_score, sha, sha_file, transitions, utc,
                    write_new)

WINDOW = 3
PAGES = 18
DEV_RASTERS = WP17 / "review/inputs/dev-id-ablation/rasters.json"
WP16 = HERE.parent / "WP-0016"
COUNT_KEYS = ("critical_values", "critical_errors", "unflagged_critical_errors", "flagged_critical", "correct_cells",
              "reference_cells", "correct_lines", "reference_lines", "edits", "reference_chars", "extra_cells")


def load_formats(pins):
    import importlib.util  # noqa: PLC0415
    if sha_file(Path(pins) / "formats.py") != sha(blob("formats.py")):
        raise SystemExit("pinned formats.py differs from its blob")
    spec = importlib.util.spec_from_file_location("wp17_pinned_formats", Path(pins) / "formats.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dev_rgb(check):
    data = DEV_RASTERS.read_bytes()
    check(sha(data) == DEV_RASTERS_SHA256, "public dev raster record = 404712df...")
    return [p["rgb_sha256"] for p in sorted(json.loads(data)["pages"], key=lambda p: p["page"])]


def verify_doc(folder, req, fmt, check):
    """Validate one document folder from its raw captures (no truth). Returns a summary or None."""
    tag = "/".join(Path(folder).parts[-3:])
    n = req["pages"]
    if not check((folder / "timing.json").is_file() and (folder / "prediction.json").is_file(), f"{tag}: timing/prediction"):
        return None
    t = load(folder / "timing.json")
    check(t.get("request") == req, f"{tag}: timing request = plan request")
    pb = (folder / "prediction.json").read_bytes()
    pred = json.loads(pb)
    check(sha(pb) == t.get("prediction_sha256"), f"{tag}: prediction digest = timing record")
    check(pred.get("source_sha256") == req["sha256"], f"{tag}: prediction source")
    check([p.get("page") for p in pred["pages"]] == list(range(1, n + 1)), f"{tag}: page ordinals")
    check(not list(folder.glob("*.pending")) and not (folder / "failure.json").exists(), f"{tag}: pending/failure file")
    raws = {}
    for i, p in enumerate(pred["pages"], 1):
        rawf, pagef = folder / f"raw-{i:03d}.json", folder / f"page-{i:03d}.json"
        if not check(rawf.is_file() and pagef.is_file(), f"{tag}: p{i} raw/page file"):
            continue
        raw = load(rawf)
        check(load(pagef) == p, f"{tag}: page-{i:03d} = prediction entry")
        check(raw.get("page") == i and raw.get("rgb_sha256") == req["rgb_sha256"][i - 1], f"{tag}: p{i} RGB pin")
        check(raw.get("source_sha256") == p.get("source_sha256") == req["sha256"], f"{tag}: p{i} source link")
        check(p.get("state") == "complete", f"{tag}: p{i} complete")
        check(raw["token_ids"][:1] == [PAGE_ID] and raw.get("token_count") == len(raw["token_ids"]), f"{tag}: p{i} <PAGE>/count")
        check(fmt.native_page(raw["raw_output"], raw["points"]) == {k: p.get(k) for k in ("text", "spans", "tables")},
              f"{tag}: p{i} stored page = frozen projection of its raw output")
        raws[i] = raw
    files = sorted(folder.glob("window-*.json"))
    check([f.name for f in files] == [f"window-{s:03d}.json" for s in range(1, n + 1, WINDOW)], f"{tag}: window files")
    covered, stops = [], []
    for f in files:
        d = load(f)
        span = list(range(d["first_page"], d["first_page"] + d["pages"]))
        covered += span
        ids = d["window_token_ids"]
        check(d.get("source_sha256") == req["sha256"], f"{tag}: {f.name} source")
        if all(i in raws for i in span):
            check([x for i in span for x in raws[i]["token_ids"]] == ids, f"{tag}: {f.name} token reassembly")
            check("".join(raws[i]["raw_output"] for i in span) == d["raw_output"], f"{tag}: {f.name} raw reassembly")
        ok = d.get("finish_reason") == "stop" and d.get("num_pages_out") == d.get("expected_pages") == d["pages"] == ids.count(PAGE_ID)
        check(ok, f"{tag}: {f.name} stop and page count")
        stops.append(ok)
    check(covered == list(range(1, n + 1)), f"{tag}: windows cover pages once in order")
    pc = t.get("page_committed_ns") or []
    check(t.get("status") == "completed" and t.get("complete_pages") == n, f"{tag}: completion record")
    check(len(pc) == n and t["accepted_ns"] < t["first_page_committed_ns"] == pc[0] and pc == sorted(pc)
          and pc[-1] <= t["document_committed_ns"], f"{tag}: durable clock order")
    check(abs(t["elapsed_s"] - (t["document_committed_ns"] - t["accepted_ns"]) / 1e9) < 1e-6, f"{tag}: elapsed")
    check(all_flags_false(pred), f"{tag}: original flagged == false everywhere")
    return dict(folder=str(folder), prediction=str(folder / "prediction.json"), prediction_sha256=sha(pb),
                complete_s=t["elapsed_s"], windows=len(files), all_stopped=all(stops) and len(stops) == -(-n // WINDOW))


def prekey(inv, pins, record, check):
    from escrow import verify_unchanged  # noqa: PLC0415
    check(not verify_unchanged(inv), "A2 run trees unchanged since the blind inventory")
    fmt = load_formats(pins)
    rgb = dev_rgb(check)
    names = A2.check_orders(record, check) if record else {}
    by_sha = {b["sha256"]: n for n, b in (record or {}).get("orders", {}).items()}
    runs, warms = {}, []
    for ir in inv["runs"]:
        run = Path(ir["path"])
        plan = load(run / "plan.json")
        segs = A2.split_segments(plan["requests"])
        seq = tuple(m for m, _ in segs)
        hit = [o for o, v in A2.ORDERS.items() if v == seq]
        if not check(len(hit) == 1, f"{run.name}: segment order {list(seq)} is AB or BA"):
            continue
        o = hit[0]
        check(o not in runs, f"{run.name}: one run per order")
        if record:
            check(names.get(by_sha.get(sha_file(run / "plan.json"))) == o, f"{run.name}: plan record agrees on order {o}")
        arms = {}
        for si, (mode, reqs) in enumerate(segs, 1):
            seg = run / f"segment-{si:02d}-{mode}"
            warm = [(r["label"], r["sha256"], tuple(r["rgb_sha256"]), r["pages"]) for r in reqs if r.get("warmup")]
            warms.append(tuple(warm))
            measured = [(i, r) for i, r in enumerate(reqs, 1) if not r.get("warmup")]
            check(len(measured) == 1, f"{run.name}/{mode}: one measured document")
            for i, req in enumerate(reqs, 1):
                folder = seg / f"{i:02d}-{req['label']}-{req['mode']}"
                info = verify_doc(folder, req, fmt, check)
                if req.get("warmup") or info is None:
                    continue
                check(req["pages"] == PAGES and req["sha256"] == DEV_PDF_SHA256 and req["rgb_sha256"] == rgb,
                      f"{run.name}/{mode}: measured request is the 18-page dev packet with pinned RGB")
                check(info["windows"] == PAGES // WINDOW and info["all_stopped"], f"{run.name}/{mode}: six stopped windows")
                arms[mode] = info
        check(sorted(arms) == sorted(A2.ARMS), f"{run.name}: three measured arms")
        runs[o] = dict(run=run.name, plan_sha256=sha_file(run / "plan.json"), arms=arms)
    check(sorted(runs) == ["ab", "ba"], "both orders present")
    check(len(set(warms)) == 1 and bool(warms), "identical excluded warm-ups across all arms and orders")
    return runs


def recount(s):
    crit = [c for p in s["pages"] for c in p["critical"]]
    cells = [c for p in s["pages"] for c in p["cells"]]
    lines = [x for p in s["pages"] for x in p["lines"]]
    edits = sum(p["edit_distance"] for p in s["pages"]) + sum(e["insertion_chars"] for e in s["extra_page_outputs"])
    chars = sum(p["reference_chars"] for p in s["pages"])
    extra = sum(p["extra_cells"] for p in s["pages"]) + sum(e["extra_cells"] for e in s["extra_page_outputs"])
    correct = sum(c["correct"] for c in cells)
    return dict(critical_values=len(crit), critical_errors=sum(not c["correct"] for c in crit),
                unflagged_critical_errors=sum(not c["correct"] and not c["flagged"] for c in crit),
                flagged_critical=sum(c["flagged"] for c in crit), correct_cells=correct, reference_cells=len(cells),
                correct_lines=sum(x["correct"] for x in lines), reference_lines=len(lines), edits=edits,
                reference_chars=chars, extra_cells=extra, cer=edits / chars if chars else None,
                cell_accuracy=correct / (len(cells) + extra) if cells else None)


def critical_paths(s):
    return [c["at"] for p in s["pages"] for c in p["critical"]]


def validate_score(key, s, check):
    """Path and metric validation of one frozen-scorer output against its own per-path records."""
    check(s["expected_pages"] == PAGES and s["output_pages"] == PAGES and s["observed_order"] == list(range(1, PAGES + 1)),
          f"{key}: 18 pages in order")
    check(s["packet_complete"] is True, f"{key}: packet complete")
    paths = critical_paths(s)
    check(len(paths) == 3 * PAGES and len(set(paths)) == len(paths), f"{key}: 54 distinct critical paths")
    for p in s["pages"]:
        kinds = [c["at"].split("/")[2] for c in p["critical"]]
        check(all(c["at"].startswith(f"page/{p['page']}/") for c in p["critical"]) and
              sorted(kinds) == ["line", "table", "table"], f"{key}: page {p['page']} has one critical line, two cells")
    r = recount(s)
    for k in COUNT_KEYS:
        check(r[k] == s["counts"][k], f"{key}: count {k} recomputes from per-path records")
    for k in ("cer", "cell_accuracy"):
        a, b = r[k], s["counts"][k]
        check((a is None and b is None) or (a is not None and b is not None and abs(a - b) < 1e-12), f"{key}: {k} recomputes")
    return paths


def title_view(pins, folder, out_pred, out_receipt, check):
    for name, f in (("wp16/title_adapt.py", WP16 / "title_adapt.py"), ("wp16/common.py", WP16 / "common.py")):
        check(f.read_bytes() == blob(name), f"{name} on disk = its blob at 1e75ebe")
    subprocess.run([sys.executable, "-I", "-B", str(WP16 / "title_adapt.py"), "--pins", str(pins), "--doc", str(folder),
                    "--out", str(out_pred), "--receipt", str(out_receipt)], check=True, cwd=str(pins),
                   stdin=subprocess.DEVNULL)
    return out_pred


def score(pre, inv, pins, truth, out, check, truth_sha256=DEV_TRUTH_SHA256):
    """truth_sha256 is overridden only by the CPU self-test with a synthetic key; main() always uses the pin."""
    from escrow import verify_unchanged  # noqa: PLC0415
    check(not verify_unchanged(inv), "A2 run trees unchanged since the blind inventory")
    check(sha_file(truth) == truth_sha256, f"key equals its custody commitment ({truth_sha256[:8]}...)")
    out.mkdir(parents=True, exist_ok=False)
    for d in ("title", "scores", "compare"):
        (out / d).mkdir()
    preds, scores, T = {}, {}, {}
    for o, r in pre["runs"].items():
        for m, x in r["arms"].items():
            check(sha_file(x["prediction"]) == x["prediction_sha256"], f"{o}/{m}: prediction unchanged since pre-key")
            T[(o, m)] = x["complete_s"]
            preds[(o, m, "frozen")] = Path(x["prediction"])
            preds[(o, m, "title")] = title_view(pins, Path(x["folder"]), out / "title" / f"{o}-{m}.prediction.json",
                                                out / "title" / f"{o}-{m}.receipt.json", check)
    for (o, m, v), p in preds.items():
        scores[(o, m, v)] = run_score(pins, truth, p, out / "scores" / f"{o}-{m}-{v}.json")
    seqs = {k: validate_score("/".join(k), s, check) for k, s in scores.items()}
    check(len({tuple(x) for x in seqs.values()}) == 1, "identical critical path sequence in every score")
    silent, comps, details, complete = {}, {}, {}, len(scores) == 12
    for o in ("ab", "ba"):
        for v in ("frozen", "title"):
            for trial in ("carbon_surgical", "carbon_bf16"):
                base_k, trial_k = (o, "native", v), (o, trial, v)
                if base_k not in preds or trial_k not in preds:
                    complete = False
                    continue
                res = run_score(pins, truth, preds[trial_k], out / "compare" / f"{o}-{v}-native__{trial}.json",
                                preds[base_k])
                cmp = res.pop("comparison")
                name = f"{o}:{v}:native->{trial}"
                check(res == scores[trial_k], f"{name}: trial score identical across scorer processes")
                for k in ("cer", "cell_accuracy"):
                    a, b = scores[base_k]["counts"][k], scores[trial_k]["counts"][k]
                    want = None if a is None else b - a
                    got = cmp["delta"][k]
                    check((want is None and got is None) or (want is not None and got is not None and abs(want - got) < 1e-12),
                          f"{name}: delta {k} = trial - base from separate scores")
                tr, rows = transitions(scores[base_k], scores[trial_k])
                novel = {c["at"] for c in cmp["new_or_changed_critical_errors"]}
                mine = {x["at"] for x in rows if x["kind"] in ("regress", "abstain", "persist_changed")}
                check(novel == mine, f"{name}: transition classes agree with the frozen compare")
                cells, _ = transitions(scores[base_k], scores[trial_k], "cells")
                comps[name] = dict(critical={k: x for k, x in tr.items() if k != "new_unflagged_paths"},
                                   changed_persistent=tr["counts"]["persist_changed"],
                                   complete_matched_pair=cmp["complete_matched_pair"], matched_paths=tr["matched_paths"],
                                   delta=cmp["delta"], inside_quality_budget=cmp["inside_quality_budget"],
                                   new_wrong_source_links=len(cmp["new_wrong_source_links"]), cells_four_way=cells["four_way"])
                details[name] = rows
                if trial == "carbon_surgical":
                    silent[(o, v)] = tr["new_unflagged"]
                    complete &= bool(cmp["complete_matched_pair"] and tr["matched_paths"])
    per_arm = {"/".join(k): {c: s["counts"][c] for c in ("cer", "cell_accuracy", "critical_values", "critical_errors",
                                                          "unflagged_critical_errors", "wrong_source")}
               for k, s in scores.items()}
    return T, silent, complete, comps, details, per_arm


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prekey")
    p.add_argument("--inventory", type=Path, required=True)
    p.add_argument("--inventory-commit", required=True)
    p.add_argument("--plans", type=Path, help="coordinator A2 plan record (cross-checked when given)")
    p.add_argument("--plans-sha256")
    p.add_argument("--pins", type=Path, required=True, help="materialized score.py, formats.py, rescore.py")
    p.add_argument("--out", type=Path, required=True, help="new pre-key record (commit and push before `score`)")
    s = sub.add_parser("score")
    s.add_argument("--prekey", type=Path, required=True)
    s.add_argument("--prekey-commit", required=True)
    s.add_argument("--inventory", type=Path, required=True)
    s.add_argument("--inventory-commit", required=True)
    s.add_argument("--pins", type=Path, required=True)
    s.add_argument("--truth", type=Path, required=True, help="released dev key, passed only to score.py")
    s.add_argument("--out", type=Path, required=True, help="new private directory")
    a = ap.parse_args()
    check = Check()
    check(pushed(a.inventory, a.inventory_commit), "blind inventory committed and pushed before this stage")
    inv = load(a.inventory)
    if a.cmd == "prekey":
        record = None
        if a.plans:
            check(sha_file(a.plans) == a.plans_sha256, "A2 plan record digest")
            record = load(a.plans)
        runs = prekey(inv, a.pins, record, check)
        rec = dict(kind="WP-0017 A2 reviewer pre-key validation (raw captures, no key)", reviewer="eld-rd-reviewer",
                   created_utc=utc(), inventory_sha256=sha_file(a.inventory), inventory_commit=a.inventory_commit,
                   runs=runs, checks_run=check.count, failures=check.failures)
        digest = write_new(a.out, rec)
        print(json.dumps(dict(prekey=str(a.out), sha256=digest, checks=check.count, failures=check.failures[:20]), indent=1))
        return 0 if not check.failures else 1
    check(pushed(a.prekey, a.prekey_commit), "pre-key record committed and pushed before the key handle is used")
    pre = load(a.prekey)
    check(pre["inventory_sha256"] == sha_file(a.inventory) and not pre["failures"], "clean pre-key record of this inventory")
    T, silent, complete, comps, details, per_arm = score(pre, inv, a.pins, a.truth, a.out, check)
    rule = A2.stoploss(T, silent, complete)
    try:
        astra = A2.astra_a2(blob_module("design/rules.py", "astra_rules"), T, silent, complete)
        check(astra["advance"] == rule["advance"], "reviewer and Astra A2 arithmetic agree")
    except (KeyError, ValueError, TypeError) as exc:
        astra = dict(error=repr(exc))
        check(not rule["advance"], "Astra A2 arithmetic could not run; advance must then be false")
    advance = rule["advance"] and not check.failures
    summary = dict(kind="WP-0017 A2 reviewer both-view scoring and stop-loss", reviewer="eld-rd-reviewer",
                   created_utc=utc(), prekey_sha256=sha_file(a.prekey), inventory_sha256=sha_file(a.inventory),
                   truth_sha256=DEV_TRUTH_SHA256, scorer_sha256=sha(blob("score.py")), per_arm=per_arm,
                   comparisons=comps, rule=rule, astra_rules_a2=astra, checks_run=check.count, failures=check.failures,
                   advance_to_A3=advance, outcome="ADVANCE_TO_A3" if advance else "HALT_AT_A2")
    digest = write_new(a.out / "summary.json", summary)
    write_new(a.out / "details.json", dict(note="PRIVATE: contains reference and observed values", rows=details))
    print(json.dumps(dict(summary=str(a.out / "summary.json"), sha256=digest, outcome=summary["outcome"],
                          failures=check.failures[:20]), indent=1))
    return 0 if advance else 1


if __name__ == "__main__":
    sys.exit(main())
