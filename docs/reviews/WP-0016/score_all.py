"""Stage 2 (after the separate scoring release): escrow scoring of WP-0016 G0. Stdlib only.

Verifies the released truth/rasters against the custody commitments and the coordinator's plan record,
re-verifies every run hash against the blind inventory and every prediction against stage 1, and binds the
stored WP-0015 Windows predictions and clocks to the committed WP-0015 hash-only inventories.

Two views are scored for every native-format arm: "frozen" (the stored predictions) and "title" (the public
title<LEVELn> rule from rescore.py at 0186467, applied by title_adapt.py in its own OS process). Every score
and every comparison is produced by the frozen score.py (SHA-256 1ceb36fe...f4bf7) in its own OS process;
this process never imports the scorer.

Pre-registered rules (README.md):
* critical transition per matched reference path (base -> trial): stable_correct, regress (wrong value),
  abstain (no value), repair, persist_same, persist_changed; four-way CC/CW/WC/WW.
* new unflagged critical at a path = trial wrong and unflagged where the base was correct or flagged.
  One at any matched path is a hard fail for the gate comparison, whatever the net count.
* G0 per family x order x view (native -> carbon_bf16 in the same process order): complete matched pair,
  frozen compare inside budget (CER delta <= 0.01, cell delta >= -0.02), zero new wrong-source links, zero
  new unflagged critical, matched paths. Plus carbon_bf16 sampled device and allocator peaks <= 10,000 MiB,
  a clean stage 1 and a real (pinned) binding. Missing evidence fails closed. Malformed structure is
  recorded, never gated in G0, and never treated as factual truth.
* Windows -> neural: signed net critical recovery (repair - regress - abstain) per extra neural second,
  extra seconds = neural complete_s - stored Windows complete_s (Windows uses zero GPU).
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (EPS, G0, PINS, WINDOWS_REFS, Check, check_pins, is_pinned, load, run_score,  # noqa: E402
                    run_title_adapter, sha, sha_file, utc, write_new)

ARMS = ("native-ab", "carbon-ab", "native-ba", "carbon-ba")
MODE = {"native": "native", "carbon": "carbon_bf16"}
NUM = re.compile(r"[+-]?[\w]+(?:[.,-][\w]+)*")


def norm(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


def transitions(base, trial, kind="critical"):
    seq_b = [(c["at"], c) for p in base["pages"] for c in p[kind]]
    seq_t = [c["at"] for p in trial["pages"] for c in p[kind]]
    t = {c["at"]: c for p in trial["pages"] for c in p[kind]}
    k, rows, new = Counter(), [], []
    for at, x in seq_b:
        y = t.get(at)
        if y is None:
            k["unmatched"] += 1
            continue
        fx, fy = bool(x.get("flagged")), bool(y.get("flagged"))
        if x["correct"] and y["correct"]:
            c = "stable_correct"
        elif x["correct"]:
            c = "abstain" if y["observed"] is None else "regress"
        elif y["correct"]:
            c = "repair"
        else:
            c = "persist_same" if (x["observed"], fx) == (y["observed"], fy) else "persist_changed"
        k[c] += 1
        nu = (not y["correct"]) and not fy and (x["correct"] or fx)
        if nu:
            new.append(at)
        if c != "stable_correct":
            rows.append(dict(at=at, kind=c, expected=x.get("expected"), base=x["observed"], trial=y["observed"],
                             base_flagged=fx, trial_flagged=fy, new_unflagged=nu))
    names = ("stable_correct", "regress", "abstain", "repair", "persist_same", "persist_changed")
    return dict(paths=len(seq_b), matched_paths=[a for a, _ in seq_b] == seq_t and not k["unmatched"],
                counts={n: k[n] for n in names},
                four_way=dict(CC=k["stable_correct"], CW=k["regress"] + k["abstain"], WC=k["repair"],
                              WW=k["persist_same"] + k["persist_changed"]),
                net_recovery=k["repair"] - k["regress"] - k["abstain"],
                new_unflagged=len(new), new_unflagged_paths=new), rows


def status(c):
    s = "C" if c["correct"] else ("N" if c["observed"] is None else "W")
    return s.lower() if c.get("flagged") else s


def patterns(scores, keys):
    by = [{c["at"]: c for p in scores[k]["pages"] for c in p["critical"]} for k in keys]
    paths = [c["at"] for p in scores[keys[0]]["pages"] for c in p["critical"]]
    return dict(arms=list(keys), counts=dict(Counter("".join(status(b[at]) for b in by) for at in paths)))


def tables_check(truth, pred):
    def valid(b, w, h):
        return (isinstance(b, list) and len(b) == 4 and all(type(v) in (int, float) for v in b)
                and 0 <= b[0] < b[2] <= w and 0 <= b[1] < b[3] <= h)

    def iou(a, b):
        ov = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
        ar = lambda r: (r[2] - r[0]) * (r[3] - r[1])
        return ov / (ar(a) + ar(b) - ov) if ov else 0.0
    pages = {p["page"]: p for p in pred["pages"]}
    out = Counter()
    for ref in truth["pages"]:
        got = [t for t in pages.get(ref["page"], {}).get("tables", []) if valid(t.get("bbox"), ref["width"], ref["height"])]
        pairs = sorted(((-iou(r["bbox"], g["bbox"]), ri, gi) for ri, r in enumerate(ref["tables"])
                        for gi, g in enumerate(got)))
        used_r, used_g = set(), set()
        for neg, ri, gi in pairs:
            if -neg >= 0.5 and ri not in used_r and gi not in used_g:
                used_r.add(ri)
                used_g.add(gi)
        out["reference_tables"] += len(ref["tables"])
        out["predicted_valid_tables"] += len(got)
        out["matched_tables"] += len(used_g)
        out["unmatched_predicted_tables"] += len(got) - len(used_g)
        out["missed_reference_tables"] += len(ref["tables"]) - len(used_r)
        if not ref["tables"]:
            out["tables_on_table_free_pages"] += len(got)
    return dict(out, note="diagnostic; an unmatched predicted table is an invented-table candidate, not proven")


def numeric_tokens(text):
    return Counter(t for t in NUM.findall(norm(text)) if any(c.isdigit() for c in t))


def lev(a, b):
    last = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(last[j] + 1, cur[-1] + 1, last[j - 1] + (ca != cb)))
        last = cur
    return last[-1]


def diagnostics(truth, pred):
    """Reviewer-only checks the frozen gates do not make (WP-0015 S2-S5). Never changes a frozen outcome."""
    refs = {p["page"]: p for p in truth["pages"]}
    pages = {p["page"]: p for p in pred["pages"]}
    nt = {n: numeric_tokens(r["text"]) for n, r in refs.items()}
    surplus = deficit = 0
    surplus_pages, misplaced, better = [], 0, []
    for n, ref in refs.items():
        got = pages.get(n, {}).get("text", "")
        have = numeric_tokens(got)
        s, d = have - nt[n], nt[n] - have
        surplus += sum(s.values())
        deficit += sum(d.values())
        if s:
            surplus_pages.append(n)
        misplaced += sum(1 for tok in s if any(tok in nt[m] for m in refs if m != n))
        if norm(ref["text"]) and got:
            g = norm(got)
            sim = sorted((-len(set(have) & set(nt[m])), m) for m in refs if m != n and norm(refs[m]["text"]))[:3]
            own = lev(g, norm(ref["text"])) / max(1, len(norm(ref["text"])))
            for _, m in sim:
                other = lev(g, norm(refs[m]["text"])) / max(1, len(norm(refs[m]["text"])))
                if other < own:
                    better.append(dict(page=n, better_matching_truth_page=m))
                    break
    flags = sum(bool(s.get("flagged")) for p in pred["pages"] for s in p.get("spans", [])) + sum(
        isinstance(c, dict) and bool(c.get("flagged")) for p in pred["pages"] for t in p.get("tables", [])
        for row in t["rows"] for c in row)
    return dict(surplus_numeric_tokens=surplus, surplus_pages=surplus_pages, missing_numeric_tokens=deficit,
                surplus_tokens_printed_on_other_pages=misplaced, pages_better_matching_other_truth=better,
                flagged_entries=flags, alignment_note="candidate pages limited to the top 3 by shared numeric tokens")


def counts(s):
    c = s["counts"]
    return dict(complete=s["packet_complete"], faults=dict(Counter(f["issue"] for f in s["faults"])),
                **{k: c[k] for k in ("edits", "reference_chars", "cer", "correct_cells", "reference_cells", "extra_cells",
                                     "cell_accuracy", "correct_lines", "reference_lines", "critical_values",
                                     "critical_errors", "unflagged_critical_errors", "flagged_critical", "wrong_source")},
                critical_abstentions=sum(x["observed"] is None and not x["correct"] for p in s["pages"] for x in p["critical"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage1", type=Path, required=True)
    ap.add_argument("--inventory", type=Path, required=True)
    ap.add_argument("--plans", type=Path, required=True)
    ap.add_argument("--pins", type=Path, required=True)
    ap.add_argument("--scoring", type=Path, required=True, help="released dir with H/ and A/ truth.json + rasters.json")
    ap.add_argument("--commitments", type=Path, help="default: <pins>/commitments.json")
    ap.add_argument("--windows-store", type=Path, required=True, help="<run>/<folder>/{prediction,timing}.json copies")
    ap.add_argument("--wp15-inventories", type=Path, help="dir with wp15-*-inventory.json (default: pins)")
    ap.add_argument("--out", type=Path, required=True, help="new private directory")
    a = ap.parse_args()
    check_pins(a.pins)
    check = Check()
    commitments = a.commitments or a.pins / "commitments.json"
    invdir = a.wp15_inventories or a.pins
    s1, inv, record = load(a.stage1), load(a.inventory), load(a.plans)
    real = dict(plans=is_pinned(a.plans, "g0-plans.json"), commitments=is_pinned(commitments, "commitments.json"),
                stage1=bool(s1.get("real_binding")),
                **{n: is_pinned(invdir / n, n) for n in ("wp15-H-inventory.json", "wp15-A-recovery-inventory.json",
                                                         "wp15-A-inventory.json")})
    check(s1["inventory_sha256"] == sha_file(a.inventory) and s1["plans_record_sha256"] == sha_file(a.plans),
          "stage 1 was not produced from this inventory/plan record")
    for ir in inv["runs"]:
        run = Path(ir["path"])
        now = {f.relative_to(run).as_posix(): sha_file(f) for f in sorted(run.rglob("*")) if f.is_file()}
        check(now == dict(ir["files"], **ir["runtime_cache_files"]), f"{run.name}: run tree changed since inventory")
    a.out.mkdir(parents=True, exist_ok=False)
    for d in ("title", "scores", "compare"):
        (a.out / d).mkdir()
    packets = load(commitments)["packets"]
    truths, truth_paths, windows = {}, {}, {}
    for fam in ("H", "A"):
        tp, rp = a.scoring / fam / "truth.json", a.scoring / fam / "rasters.json"
        files = packets[fam]["files"]
        check(sha_file(tp) == files["truth.json"] == record["inputs"][fam]["files"]["truth.json"], f"{fam}: truth commitment")
        check(sha_file(rp) == files["rasters.json"] == record["inputs"][fam]["files"]["rasters.json"], f"{fam}: rasters commitment")
        truth = load(tp)
        check(truth["source_sha256"] == files["source.pdf"] == record["inputs"][fam]["files"]["source.pdf"], f"{fam}: truth source")
        released = [p["rgb_sha256"] for p in sorted(load(rp)["pages"], key=lambda p: p["page_number"])]
        for o, r in s1["runs"].items():
            for mode, arm in r["arms"].items():
                m = arm["measured"].get(fam)
                if m:
                    rgb = [g["rgb_sha256"] for g in arm["grammar_pages"][fam]]
                    check(rgb == released, f"{fam} {o}/{mode}: inference pins differ from released rasters")
        truths[fam], truth_paths[fam] = truth, tp
        ref = WINDOWS_REFS[fam]
        wins = {}
        for role in ("primary", "sensitivity"):
            run, folder = ref[role]
            invname = ref["inventory"] if role == "primary" else ref.get("sensitivity_inventory", ref["inventory"])
            irun = next((x for x in load(invdir / invname)["runs"] if x["run"] == run), None)
            d = a.windows_store / run / folder
            ok = check(irun is not None and (d / "prediction.json").is_file() and (d / "timing.json").is_file(),
                       f"{fam}: stored Windows {run}/{folder} not supplied or not inventoried")
            if not ok:
                continue
            check(sha_file(d / "prediction.json") == irun["files"][f"{folder}/prediction.json"], f"{fam}: Windows {role} prediction hash")
            check(sha_file(d / "timing.json") == irun["files"][f"{folder}/timing.json"], f"{fam}: Windows {role} timing hash")
            t = load(d / "timing.json")
            check(t["request"]["mode"] == "windows" and t["prediction_sha256"] == sha_file(d / "prediction.json"),
                  f"{fam}: Windows {role} timing binding")
            check(load(d / "prediction.json")["source_sha256"] == truth["source_sha256"], f"{fam}: Windows {role} source")
            wins[role] = dict(run=run, folder=folder, prediction=str(d / "prediction.json"),
                              prediction_sha256=sha_file(d / "prediction.json"), complete_s=t["elapsed_s"])
        if "primary" in wins and real["plans"]:
            check(abs(wins["primary"]["complete_s"] - ref["declared_primary_s"]) < 5e-4,
                  f"{fam}: primary Windows clock {wins['primary']['complete_s']} != declared {ref['declared_primary_s']}")
        if len(wins) == 2:
            check(wins["primary"]["prediction_sha256"] == wins["sensitivity"]["prediction_sha256"],
                  f"{fam}: Windows predictions differ between WP-0015 orders")
        windows[fam] = wins
    # Predictions, views and separate-process scores.
    preds, scores, receipts, neural_s = {}, {}, {}, {}
    for fam in ("H", "A"):
        for o, r in s1["runs"].items():
            order = r["order"]
            for short, mode in MODE.items():
                m = r["arms"].get(mode, {}).get("measured", {}).get(fam)
                key = f"{short}-{order}"
                if not check(m is not None, f"{fam}: no measured {key}"):
                    continue
                check(sha_file(m["prediction"]) == m["prediction_sha256"], f"{fam} {key}: prediction changed since stage 1")
                preds[fam, key, "frozen"] = Path(m["prediction"])
                tp = a.out / "title" / f"{fam}-{key}.prediction.json"
                _, receipts[fam, key] = run_title_adapter(a.pins, Path(m["folder"]), tp, a.out / "title" / f"{fam}-{key}.receipt.json")
                preds[fam, key, "title"] = tp
                neural_s[fam, key] = m["complete_s"]
        if "primary" in windows[fam]:
            for view in ("frozen", "title"):
                preds[fam, "windows", view] = Path(windows[fam]["primary"]["prediction"])
    for (fam, key, view), p in preds.items():
        if key == "windows" and view == "title":
            continue
        scores[fam, key, view] = run_score(a.pins, truth_paths[fam], p, a.out / "scores" / f"{fam}-{key}-{view}.json")
    for fam in ("H", "A"):
        if (fam, "windows", "frozen") in scores:
            scores[fam, "windows", "title"] = scores[fam, "windows", "frozen"]
    plan = [("gate", "native-ab", "carbon-ab"), ("gate", "native-ba", "carbon-ba"),
            ("control", "native-ab", "native-ba"), ("control", "carbon-ab", "carbon-ba"),
            ("cross", "native-ab", "carbon-ba"), ("cross", "native-ba", "carbon-ab")] + [
            ("windows", "windows", k) for k in ARMS]
    comparisons, details = {}, {}
    for fam in ("H", "A"):
        for view in ("frozen", "title"):
            for group, base, trial in plan:
                if (fam, base, view) not in preds or (fam, trial, view) not in preds:
                    check(group == "windows" and not windows[fam], f"{fam} {view}: missing {base}->{trial}")
                    continue
                name = f"{fam}:{view}:{base}->{trial}"
                res = run_score(a.pins, truth_paths[fam], preds[fam, trial, view],
                                a.out / "compare" / f"{fam}-{view}-{base}__{trial}.json", preds[fam, base, view])
                cmp = res.pop("comparison")
                check(res == scores[fam, trial, view], f"{name}: trial score differs between scorer processes")
                tr, rows = transitions(scores[fam, base, view], scores[fam, trial, view])
                novel = {c["at"] for c in cmp["new_or_changed_critical_errors"]}
                mine = {r["at"] for r in rows if r["kind"] in ("regress", "abstain", "persist_changed")}
                check(novel == mine, f"{name}: transition classes disagree with frozen compare")
                cells, _ = transitions(scores[fam, base, view], scores[fam, trial, view], "cells")
                lines, _ = transitions(scores[fam, base, view], scores[fam, trial, view], "lines")
                d = cmp["delta"]
                entry = dict(group=group, family=fam, view=view, base=base, trial=trial, delta=d,
                             complete_matched_pair=cmp["complete_matched_pair"],
                             inside_quality_budget=cmp["inside_quality_budget"],
                             unattended_quality_gate=cmp["unattended_quality_gate"],
                             new_wrong_source_links=len(cmp["new_wrong_source_links"]),
                             frozen_new_or_changed_critical=len(novel), critical=tr,
                             cells_four_way=cells["four_way"], lines_four_way=lines["four_way"])
                if group == "gate":
                    rederived = ((d["cer"] is None or d["cer"] <= G0["cer_delta_max"] + EPS) and
                                 (d["cell_accuracy"] is None or d["cell_accuracy"] >= G0["cell_delta_min"] - EPS))
                    check(rederived == cmp["inside_quality_budget"], f"{name}: budget re-derivation disagrees")
                    entry["g0_pass"] = bool(cmp["complete_matched_pair"] and cmp["inside_quality_budget"] and
                                            not cmp["new_wrong_source_links"] and tr["matched_paths"] and
                                            tr["new_unflagged"] <= G0["new_unflagged_critical_max"])
                if group == "windows":
                    ws = windows[fam]
                    extra = {role: neural_s[fam, trial] - w["complete_s"] for role, w in ws.items()}
                    sb, st = scores[fam, base, view]["counts"], scores[fam, trial, view]["counts"]
                    entry["recovery"] = {role: dict(
                        extra_neural_s=x, windows_s=ws[role]["complete_s"], neural_s=neural_s[fam, trial],
                        net_critical_per_extra_s=tr["net_recovery"] / x if x else None,
                        cells_gained_per_extra_s=(st["correct_cells"] - sb["correct_cells"]) / x if x else None,
                        edits_saved_per_extra_s=(sb["edits"] - st["edits"]) / x if x else None,
                        added_gpu_cost_of_windows="zero") for role, x in extra.items()}
                comparisons[name] = entry
                details[name] = rows
    per_arm = {f"{fam}:{key}:{view}": dict(counts(s), tables=tables_check(truths[fam], load(preds[fam, key, view])),
                                           diagnostics=diagnostics(truths[fam], load(preds[fam, key, view])))
               for (fam, key, view), s in scores.items() if not (key == "windows" and view == "title")}
    correction = {}
    for fam in ("H", "A"):
        for key in ARMS:
            if (fam, key, "frozen") in scores:
                tr, _ = transitions(scores[fam, key, "frozen"], scores[fam, key, "title"])
                correction[f"{fam}:{key}"] = dict(critical=tr, recognized_headers=receipts[fam, key]["recognized_headers"])
    pattern = {f"{fam}:{view}": patterns(scores, [(fam, k, view) for k in ARMS + ("windows",)
                                                  if (fam, k, view) in scores])
               for fam in ("H", "A") for view in ("frozen", "title")}
    mem = s1.get("memory", {})
    mem_ok = {o: bool(mem.get(f"{o}:carbon_bf16", {}).get("device_within_g0")) and
              bool(mem.get(f"{o}:carbon_bf16", {}).get("allocator_within_g0")) for o in ("ab", "ba")}
    gates = {k: v["g0_pass"] for k, v in comparisons.items() if v["group"] == "gate"}
    complete = len(gates) == 8
    verdict = dict(gate_comparisons=gates, gate_comparisons_complete=complete, memory_within=mem_ok,
                   stage1_clean=not s1["failures"], stage2_clean=not check.failures, real_binding=all(real.values()),
                   binding_detail=real,
                   g0_pass=bool(complete and all(gates.values()) and all(mem_ok.values()) and not s1["failures"]
                                and not check.failures and all(real.values())),
                   malformed_structure="recorded in stage 1; not a G0 criterion")
    if not verdict["real_binding"]:
        verdict["label"] = "NOT A GATE RESULT: synthetic or unpinned binding"
    summary = dict(stage=2, reviewer="eld-rd-reviewer", created_utc=utc(), scorer_sha256=PINS["score.py"][2],
                   title_rule=dict(commit=PINS["rescore.py"][0], sha256=PINS["rescore.py"][2]),
                   stage1_sha256=sha_file(a.stage1), inventory_sha256=sha_file(a.inventory),
                   windows={f: {r: {k: v for k, v in w.items() if k != "prediction"} for r, w in ws.items()}
                            for f, ws in windows.items()},
                   failures=check.failures, checks_run=check.count, verdict=verdict, per_arm=per_arm,
                   comparisons=comparisons, title_correction=correction, critical_patterns=pattern)
    digest = write_new(a.out / "summary.json", summary)
    write_new(a.out / "details.json", dict(note="PRIVATE: contains reference and observed values", rows=details))
    write_new(a.out / "files.json", {p.relative_to(a.out).as_posix(): sha_file(p)
                                     for p in sorted(a.out.rglob("*")) if p.is_file() and p.name != "files.json"})
    print(json.dumps(dict(summary=str(a.out / "summary.json"), sha256=digest, verdict=verdict,
                          failures=check.failures[:20], failure_count=len(check.failures)), indent=1))
    return 0 if verdict["g0_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
