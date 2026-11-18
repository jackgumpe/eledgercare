"""Compact scored H and A evidence for the independent WP-0015 replay. CPU only; never runs OCR.

Verifies input/truth/raster/pin/scorer/prediction hashes, recomputes the frozen scorer in-process and
checks it equals the separate-process score files, applies the author's previously committed public
title<LEVELn> rule (sensitivity-title-level/rescore.py, 0186467) to native raw pages, classifies critical
transitions, runs reviewer-only numeric/page-alignment checks, and builds a source-linked late-page lookup.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EVAL = ROOT / "docs/evaluation/WP-0015"
ASTRA = ROOT / "docs/research/WP-0015/astra"
sys.path[:0] = [str(EVAL), str(ASTRA), str(ASTRA / "sensitivity-title-level"), str(HERE)]
from score import compare, score  # noqa: E402
from formats import native_page  # noqa: E402
from rescore import SCORER, TITLE, critical_transitions  # noqa: E402
from analyze import diagnostics  # noqa: E402

PKT = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0015/review")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def ns(t, key):
    return round((t[key] - t["accepted_ns"]) / 1e9, 3)


def docs(run):
    reqs = load(run / "plan.json")["requests"]
    return {(r["mode"], r["warmup"]): run / f"{i:02d}-{r['label']}-{r['mode']}" for i, r in enumerate(reqs, 1)}


def clocks(run, folder, warm):
    t = load(folder / "timing.json")
    w = load(warm / "timing.json")
    mode = t["request"]["mode"]
    return dict(load_s=round(load(run / f"load-{mode}.json")["elapsed_s"], 3), warmup_s=round(w["elapsed_s"], 3),
                first_page_s=ns(t, "first_page_committed_ns"),
                last_page_s=round((t["page_committed_ns"][-1] - t["accepted_ns"]) / 1e9, 3),
                complete_s=round(t["elapsed_s"], 3), pages=t["complete_pages"],
                pages_per_min=round(60 * t["complete_pages"] / t["elapsed_s"], 2))


def corrected_native(folder, pred):
    pages, headers = [], 0
    for p in pred["pages"]:
        raw = load(folder / f"raw-{p['page']:03d}.json")
        assert native_page(raw["raw_output"], raw["points"]) == {k: p[k] for k in ("text", "spans", "tables")}
        headers += len(TITLE.findall(raw["raw_output"]))
        pages.append(dict(p, **native_page(TITLE.sub(r"\1", raw["raw_output"]), raw["points"])))
    return dict(pred, pages=pages), headers


def counts(s):
    c = s["counts"]
    f = Counter(x["issue"] for x in s["faults"])
    return dict(complete=s["packet_complete"], edits=c["edits"], reference_chars=c["reference_chars"], cer=round(c["cer"], 4),
                correct_cells=c["correct_cells"], reference_cells=c["reference_cells"], extra_cells=c["extra_cells"],
                cell_accuracy=None if c["cell_accuracy"] is None else round(c["cell_accuracy"], 4),
                correct_lines=c["correct_lines"], reference_lines=c["reference_lines"],
                critical_values=c["critical_values"], critical_errors=c["critical_errors"],
                unflagged_critical_errors=c["unflagged_critical_errors"], flagged_critical=c["flagged_critical"],
                wrong_source=c["wrong_source"], missing=f["missing_page"], duplicate=f["duplicate_page"],
                out_of_range=f["out_of_range"], sequence_fault=f["page_sequence"], incomplete=f["incomplete_page"],
                unexpected_blank=f["unexpected_blank"], ink_on_blank=f["ink_on_blank"], invalid_geometry=f["invalid_geometry"])


def transitions(base, trial):
    t = critical_transitions(base, trial)
    k = Counter(x["kind"] for x in t)
    return dict(new_on_baseline_correct=k["new_error"], changed_existing=k["changed_error"],
                same_existing=k["same_error"], repaired=k["repaired"]), t


def diag(truth, pred):
    d = diagnostics(truth, pred)
    return dict(surplus_numeric_tokens=sum(sum(v.values()) for v in d["numeric_surplus_by_page"].values()),
                surplus_pages=len(d["numeric_surplus_by_page"]),
                missing_numeric_tokens=sum(sum(v.values()) for v in d["numeric_deficit_by_page"].values()),
                tokens_printed_on_other_pages=len(d["numeric_tokens_printed_on_other_pages"]),
                pages_better_matching_other_truth=[x["page"] for x in d["pages_better_matching_other_truth"]],
                flagged_entries=d["flagged_entries"])


def arm(truth, run, folder, warm, official_file, base=None):
    pred = load(folder / "prediction.json")
    off = score(truth, pred)
    filed = load(official_file)
    assert off["counts"] == filed["counts"] and off["faults"] == filed["faults"], "in-process != separate process"
    out = dict(run=run.name, folder=folder.name, prediction_sha256=sha(folder / "prediction.json"),
               clocks=clocks(run, folder, warm), official=counts(off), checks=diag(truth, pred))
    return out, off, pred


def lookup(truth, rasters, arms):
    pins = {p["page_number"]: p["rgb_sha256"] for p in rasters["pages"]}
    last = truth["pages"][-1]
    table_pages = [p["page"] for p in truth["pages"] if p["tables"]]
    late_table = last["page"] if last["tables"] else (table_pages[-1] if table_pages else None)
    out = dict(source_pdf_sha256=truth["source_sha256"], final_page=last["page"],
               final_page_has_table=bool(last["tables"]), late_table_page=late_table, pages={})
    for n in sorted({last["page"], late_table} - {None}):
        ref = truth["pages"][n - 1]
        rec = dict(rgb_pin=pins[n], truth_lines=len(ref["lines"]), truth_tables=len(ref["tables"]), arms={})
        for name, (folder, scored, pred) in arms.items():
            raw = load(folder / f"raw-{n:03d}.json")
            page = next(p for p in pred["pages"] if p["page"] == n)
            sp = next(p for p in scored["pages"] if p["page"] == n)
            crit_line = next((c for c in sp["critical"] if "/line/" in c["at"]), None)
            line = next((l for l in sp["lines"] if crit_line and l["at"] == crit_line["at"]), None)
            crit_cell = next((c for c in sp["critical"] if "/table/" in c["at"]), None)
            a = dict(raw_page=raw["page"], raw_source_sha256=raw["source_sha256"], raw_rgb_sha256=raw["rgb_sha256"],
                     rgb_matches_pin=raw["rgb_sha256"] == pins[n], source_matches=raw["source_sha256"] == truth["source_sha256"],
                     predicted_spans=len(page["spans"]), predicted_tables=len(page["tables"]),
                     predicted_table_bboxes=[t["bbox"] for t in page["tables"]])
            if crit_line:
                a["critical_line"] = dict(at=crit_line["at"], expected=crit_line["expected"], observed=crit_line["observed"],
                                          correct=crit_line["correct"], reference_bbox=line["reference_bbox"],
                                          reported_span_boxes=line["reported_span_boxes"])
            if crit_cell:
                r, c = (int(x) for x in crit_cell["at"].split("/")[-3::2])
                words = [dict(text=s["text"], bbox=s["bbox"]) for s in page["spans"]
                         if crit_cell["reference_bbox"][0] <= (s["bbox"][0] + s["bbox"][2]) / 2 < crit_cell["reference_bbox"][2]
                         and crit_cell["reference_bbox"][1] <= (s["bbox"][1] + s["bbox"][3]) / 2 < crit_cell["reference_bbox"][3]]
                a["critical_cell"] = dict(at=crit_cell["at"], row=r, col=c, expected=crit_cell["expected"],
                                          observed=crit_cell["observed"], correct=crit_cell["correct"],
                                          reference_bbox=crit_cell["reference_bbox"],
                                          reported_table_bbox=crit_cell["reported_table_bbox"],
                                          spans_centred_in_cell=words)
            rec["arms"][name] = a
        out["pages"][str(n)] = rec
    return out


def family(name, runs, complete_run, inventories):
    rel = PKT / f"scoring-{name}"
    commit = load(EVAL / "commitments.json")["packets"][name]
    truth, rasters = load(rel / "truth.json"), load(rel / "rasters.json")
    pins = load(PKT / f"input-{name}" / "rasters.input.json")
    inv = {}
    for i in inventories:
        for r in load(i)["runs"]:
            inv[r["run"]] = r["files"]
    hashes = dict(input_pdf=sha(PKT / f"input-{name}/source.pdf"), truth=sha(rel / "truth.json"), rasters=sha(rel / "rasters.json"))
    ver = dict(input_pdf_commitment=hashes["input_pdf"] == commit["files"]["source.pdf"] == truth["source_sha256"],
               truth_commitment=hashes["truth"] == commit["files"]["truth.json"],
               rasters_commitment=hashes["rasters"] == commit["files"]["rasters.json"],
               inference_pins_equal_released=[p["rgb_sha256"] for p in pins["pages"]] == [p["rgb_sha256"] for p in rasters["pages"]],
               scorer_sha256_matches_public_rule=sha(EVAL / "score.py") == SCORER)
    result = dict(family=name, pages=len(truth["pages"]), hashes=hashes, verified=ver, runs={})
    stage2 = PKT / f"analysis-{name}-stage2"
    lookup_arms = {}
    for run in runs:
        d = docs(run)
        r = {}
        nat = d.get(("native", False))
        win = d.get(("windows", False))
        base = None
        if nat and (nat / "timing.json").exists():
            a, off, pred = arm(truth, run, nat, d[("native", True)], stage2 / f"score-{run.name}-native.json")
            fixed, headers = corrected_native(nat, pred)
            cs = score(truth, fixed)
            a.update(corrected=counts(cs), title_level_headers_recognised=headers,
                     corrected_checks=diag(truth, fixed),
                     correction_transitions=transitions(off, cs)[0])
            r["native"], base = a, (off, cs)
            if run == complete_run:
                lookup_arms["native"] = (nat, off, pred)
        elif nat:
            f = load(nat / "failure.json")
            r["native"] = dict(status="failed", durable_pages=len(list(nat.glob("page-*.json"))),
                               failure_elapsed_since_dispatch_s=round(f["elapsed_since_dispatch_s"], 3),
                               failure_type=f["error"].split("(")[0], counted_in_attempt_denominator=True,
                               complete_document_rate=None)
        if win:
            sfile = stage2 / (f"score-{run.name}-windows.json" if base else f"score-{run.name}-windows-vs-recovery-native.json")
            a, off, pred = arm(truth, run, win, d[("windows", True)], sfile)
            if base is None:
                bdocs = docs(complete_run)
                bfolder = bdocs[("native", False)]
                bpred = load(bfolder / "prediction.json")
                base = (score(truth, bpred), score(truth, corrected_native(bfolder, bpred)[0]))
                a["baseline"] = f"{complete_run.name} native"
            for label, b in (("vs_official_native", base[0]), ("vs_corrected_native", base[1])):
                cmp = compare(b, off)
                k, t = transitions(b, off)
                a[label] = dict(delta={x: None if v is None else round(v, 4) for x, v in cmp["delta"].items()},
                                inside_quality_budget=cmp["inside_quality_budget"],
                                unattended_quality_gate=cmp["unattended_quality_gate"],
                                new_wrong_source_links=len(cmp["new_wrong_source_links"]), critical_transitions=k,
                                examples=[dict(kind=x["kind"], at=x["at"], expected=x["expected"], control=x["control"], trial=x["trial"])
                                          for x in t if x["kind"] in ("new_error", "changed_error")][:4])
            r["windows"] = a
            if run == complete_run:
                lookup_arms["windows"] = (win, off, pred)
        for m, v in r.items():
            if "prediction_sha256" in v:
                v["prediction_matches_blind_inventory"] = v["prediction_sha256"] == inv[run.name][f"{v['folder']}/prediction.json"]
        result["runs"][run.name] = r
    nat_base = [v["native"] for v in result["runs"].values() if "complete_s" in v.get("native", {}).get("clocks", {})]
    result["native_baselines_complete"] = len(nat_base)
    result["native_attempts"] = sum("native" in v for v in result["runs"].values())
    if len(nat_base) > 1:
        ts = [x["clocks"]["complete_s"] for x in nat_base]
        result["native_complete_spread_s"] = round(max(ts) - min(ts), 3)
    result["source_linked_lookup"] = lookup(truth, rasters, lookup_arms)
    return result


def prefix(failed, complete, truth_path):
    truth = load(truth_path)
    pages = sorted(int(p.stem[-3:]) for p in failed.glob("page-*.json"))
    same = all(load(failed / f"raw-{i:03d}.json")["token_ids"] == load(complete / f"raw-{i:03d}.json")["token_ids"] and
               load(failed / f"raw-{i:03d}.json")["raw_output"] == load(complete / f"raw-{i:03d}.json")["raw_output"]
               for i in pages)
    tokens = sum(len(load(failed / f"raw-{i:03d}.json")["token_ids"]) for i in pages)
    wins = sorted(w.name for w in failed.glob("window-*.json"))
    stops = all(load(failed / w)[k] == load(complete / w)[k] for w in wins
                for k in ("finish_reason", "num_pages_out", "expected_pages", "window_token_ids"))
    pred = load(complete / "prediction.json")
    sub = dict(pred, pages=[p for p in pred["pages"] if p["page"] in pages])
    s = score(dict(truth, pages=[p for p in truth["pages"] if p["page"] in pages]), sub)
    return dict(diagnostic_only=True, pages=f"{pages[0]}-{pages[-1]}", windows=len(wins), tokens=tokens,
                tokens_and_raw_identical=same, window_stops_identical=stops,
                prefix_pages_official=dict(edits=s["counts"]["edits"], reference_chars=s["counts"]["reference_chars"],
                                           correct_cells=s["counts"]["correct_cells"], reference_cells=s["counts"]["reference_cells"],
                                           critical_errors=s["counts"]["critical_errors"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    ev = HERE / "evidence"
    h = family("H", [PKT / "runs/h-r1-ab", PKT / "runs/h-r2-ba"], PKT / "runs/h-r1-ab", [ev / "H-blind-inventory.json"])
    A = family("A", [PKT / "runs/a-scale-ba", PKT / "runs/a-recovery-ab"], PKT / "runs/a-recovery-ab",
               [ev / "A-blind-inventory.json", ev / "A-recovery-blind-inventory.json"])
    A["failed_native_prefix"] = prefix(PKT / "runs/a-scale-ba/04-a-native", PKT / "runs/a-recovery-ab/03-a-native",
                                       PKT / "scoring-A/truth.json")
    out = dict(reviewer="eld-rd-reviewer", scorer_sha256=sha(EVAL / "score.py"),
               public_rule="docs/research/WP-0015/astra/sensitivity-title-level/rescore.py TITLE (commit 0186467)",
               H=h, A=A)
    with a.out.open("x", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("written", a.out)


if __name__ == "__main__":
    main()
