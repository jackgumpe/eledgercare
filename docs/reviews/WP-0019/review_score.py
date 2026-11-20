"""WP-0019 reviewer field-level scoring, joins and Stage-1 gate (eld-rd-reviewer, independent).

Consumes canonical run bundles (schema wp0019-review-run/1, see PREREGISTRATION.md section 4); author
formats are bound to that schema by a separate, committed adapter that may only rename/restructure
fields. Every H/A score comes from the unchanged frozen scorer in a separate `python -I` process.
In-process use of the frozen module is limited to predicates and to the per-crop diagnostic reading.
Ground truth is read only here, after predictions are frozen.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_common import (WITNESSES, ZERO_WORD_CELLS, Checks, FrozenScorer, centre, contains_point, load_pins,
                           overlap_area, pairs, project_pinned, read_json, sha256_file, write_new)

ARMS = ("baseline", "treatment")


# ---------------------------------------------------------------- positions
def value_class(expected):
    text = " ".join(expected.split())
    return "blank" if text == "" else ("spaced" if " " in text else "single")


def positions(score):
    """Every reference cell and line, with the critical record merged in. Keys are scorer `at` paths."""
    out = {}
    for p in score["pages"]:
        for c in p["cells"]:
            out[c["at"]] = dict(at=c["at"], page=p["page"], kind="cell", expected=c["expected"],
                                observed=c["observed"], correct=c["correct"], flagged=c["flagged"],
                                bbox=c["reference_bbox"], critical=False)
        for ln in p["lines"]:
            out[ln["at"]] = dict(at=ln["at"], page=p["page"], kind="line", expected=" ".join(ln["expected"].split()),
                                 observed=ln["observed"], correct=ln["correct"], flagged=None,
                                 bbox=ln["reference_bbox"], critical=False)
        for c in p["critical"]:
            r = out[c["at"]]
            r.update(critical=True, critical_expected=c["expected"], critical_correct=c["correct"],
                     critical_flagged=c["flagged"])
            if r["kind"] == "line":
                r["flagged"] = c["flagged"]
    for r in out.values():
        r["ok"] = r["critical_correct"] if r["critical"] else r["correct"]
        r["class"] = value_class(r["expected"])
    return out


def transition(b_ok, t_ok):
    return ("R" if b_ok else "W") + ("R" if t_ok else "W")


def tokens(text):
    return None if text is None else len(text.split())


def blankish(text):
    return "" if text is None else text


# ---------------------------------------------------------------- crops -> coverage and diagnostic reading
def crop_spans(crop, width, height, points):
    left, top = crop["rect"][0], crop["rect"][1]
    spans = []
    for line in crop.get("lines") or []:
        for w in line["words"]:
            b = w["bbox"]
            px = [b[0] + left, b[1] + top, b[2] + left, b[3] + top]
            spans.append(dict(text=w["text"], bbox=project_pinned(px, width, height, points), flagged=False,
                              crop_px=list(b)))
    return spans


def crop_rect_pt(crop, width, height, points):
    l, t, r, b = crop["rect"]
    return [l * points[0] / width, t * points[1] / height, r * points[0] / width, b * points[1] / height]


def diagnostic_readings(module, truth_page, sha, page_record):
    """Per crop: frozen-scorer fallback reading of that crop's words alone. Returns list per crop."""
    full = page_record["full"]
    width, height = full["width"], full["height"]
    points = (truth_page["width"], truth_page["height"])
    out = []
    for ix, crop in enumerate(page_record.get("crops") or []):
        spans = crop_spans(crop, width, height, points)
        pred_page = dict(page=truth_page["page"], state="complete", text="",
                         spans=[{k: s[k] for k in ("text", "bbox", "flagged")} for s in spans], tables=[])
        res = module.layout(truth_page, pred_page, sha)
        reads = {}
        for c in res["cells"]:
            if c["observed"] is not None:
                reads[c["at"]] = dict(observed=c["observed"], correct=c["correct"])
        for ln in res["lines"]:
            if ln["observed"] is not None:
                reads[ln["at"]] = dict(observed=ln["observed"], correct=ln["correct"])
        for c in res["critical"]:
            if c["at"] in reads:
                reads[c["at"]]["critical_correct"] = c["correct"]
        out.append(dict(index=ix, id=crop.get("id", ix), rect=crop["rect"], kind=crop.get("kind"),
                        region=crop.get("region"), decision=crop.get("decision"),
                        rect_pt=crop_rect_pt(crop, width, height, points), words=len(spans),
                        spans=spans, reads=reads, faults=res["faults"]))
    return out


def coverage_for(pos, diags):
    c = centre(pos["bbox"])
    area = (pos["bbox"][2] - pos["bbox"][0]) * (pos["bbox"][3] - pos["bbox"][1])
    covering = [d for d in diags if contains_point(d["rect_pt"], c)]
    touching = [d for d in diags if overlap_area(d["rect_pt"], pos["bbox"]) > 0]
    chosen = max(covering, key=lambda d: overlap_area(d["rect_pt"], pos["bbox"])) if covering else None
    reading = chosen["reads"].get(pos["at"]) if chosen else None
    diag = None
    if chosen is not None:
        if reading is None:
            diag = dict(observed=None, ok=False, words_read=0)
        else:
            ok = reading.get("critical_correct", reading["correct"]) if pos["critical"] else reading["correct"]
            diag = dict(observed=reading["observed"], ok=ok, words_read=None)
    return dict(covered=chosen is not None, covering=[d["id"] for d in covering],
                touching=[d["id"] for d in touching], chosen=None if chosen is None else chosen["id"],
                overlap_fraction=(overlap_area(chosen["rect_pt"], pos["bbox"]) / area) if chosen else 0.0,
                author_decision=None if chosen is None else chosen["decision"],
                author_region=None if chosen is None else chosen["region"],
                other_readings={d["id"]: d["reads"][pos["at"]]["observed"] for d in covering
                                if d is not chosen and pos["at"] in d["reads"]}), diag


def inferred_decision(base, treat, diag):
    same_full = (base["observed"], base["flagged"]) == (treat["observed"], treat["flagged"])
    if diag is None:
        return "unselected_changed" if not same_full else "unselected"
    agree = blankish(diag["observed"]) == blankish(base["observed"])
    if agree:
        return "agree_same" if same_full else ("agree_flagged" if treat["observed"] == base["observed"] else "agree_changed")
    if treat["observed"] == base["observed"]:
        return "kept_full_flagged" if treat["flagged"] != base["flagged"] else "kept_full"
    if blankish(treat["observed"]) == blankish(diag["observed"]):
        return "took_crop_flagged" if treat["flagged"] else "took_crop"
    return "other"


# ---------------------------------------------------------------- per run/family join
def join_family(family, truth, base_score, treat_score, archive_score, module, bundle_family):
    sha = truth["source_sha256"]
    pages_by_num = {p["page"]: p for p in truth["pages"]}
    base_pos, treat_pos = positions(base_score), positions(treat_score)
    arch_pos = positions(archive_score) if archive_score is not None else {}
    treat_pages = {p["page"]: p for p in (bundle_family or {}).get("pages", [])}
    diags_by_page = {}
    for num, rec in treat_pages.items():
        diags_by_page[num] = diagnostic_readings(module, pages_by_num[num], sha, rec) if rec.get("crops") else []
    rows = []
    for at in sorted(base_pos, key=lambda a: (base_pos[a]["page"], a)):
        b, t = base_pos[at], treat_pos.get(at)
        if t is None:
            raise ValueError(f"treatment lacks position {at}")
        cov, diag = coverage_for(b, diags_by_page.get(b["page"], []))
        a = arch_pos.get(at)
        row = dict(at=at, family=family, page=b["page"], kind=b["kind"], critical=b["critical"],
                   cls=b["class"], expected=b.get("critical_expected") if b["critical"] and b["kind"] == "line" else b["expected"],
                   reference_bbox=b["bbox"],
                   archive=None if a is None else dict(observed=a["observed"], ok=a["ok"], flagged=a["flagged"]),
                   base=dict(observed=b["observed"], ok=b["ok"], flagged=b["flagged"]),
                   treat=dict(observed=t["observed"], ok=t["ok"], flagged=t["flagged"]),
                   transition=transition(b["ok"], t["ok"]),
                   changed=(b["observed"], b["flagged"]) != (t["observed"], t["flagged"]),
                   token_delta=None if None in (tokens(b["observed"]), tokens(t["observed"])) else tokens(t["observed"]) - tokens(b["observed"]),
                   coverage=cov, diagnostic=diag)
        row["inferred_decision"] = inferred_decision(row["base"], row["treat"], diag)
        row["newly_unflagged"] = (row["critical"] and not t["ok"] and not t["flagged"] and
                                  not (not b["ok"] and not b["flagged"]))
        if diag is not None:
            row["full_vs_crop"] = "agree" if blankish(diag["observed"]) == blankish(b["observed"]) else "disagree"
        else:
            row["full_vs_crop"] = "unselected"
        rows.append(row)
    return rows, diags_by_page


def summarize(rows, comparison):
    crit = [r for r in rows if r["critical"]]
    tr = Counter(r["transition"] for r in crit)
    ww_changed = sum(1 for r in crit if r["transition"] == "WW" and r["changed"])
    cells = [r for r in rows if r["kind"] == "cell"]
    blanks = [r for r in cells if r["cls"] == "blank"]
    summary = dict(
        criticals=len(crit), critical_lines=sum(r["kind"] == "line" for r in crit),
        critical_cells=sum(r["kind"] == "cell" for r in crit),
        WR=tr["WR"], RW=tr["RW"], WW=tr["WW"], RR=tr["RR"], WW_changed=ww_changed, WW_same=tr["WW"] - ww_changed,
        net=tr["WR"] - tr["RW"],
        base_wrong=sum(not r["base"]["ok"] for r in crit), treat_wrong=sum(not r["treat"]["ok"] for r in crit),
        base_unflagged_wrong=sum(not r["base"]["ok"] and not r["base"]["flagged"] for r in crit),
        treat_unflagged_wrong=sum(not r["treat"]["ok"] and not r["treat"]["flagged"] for r in crit),
        newly_unflagged=sum(r["newly_unflagged"] for r in crit),
        flag_transitions=dict(Counter(f"{int(bool(r['base']['flagged']))}{int(bool(r['treat']['flagged']))}" for r in crit)),
        flagged_recoveries_excluded=sum(1 for r in crit if not r["treat"]["ok"] and r["treat"]["flagged"] and not r["base"]["ok"]),
        all_positions=dict(Counter(r["transition"] for r in rows)),
        cells=dict(Counter(r["transition"] for r in cells)),
        lines=dict(Counter(r["transition"] for r in rows if r["kind"] == "line")),
        by_class={cls: dict(Counter(r["transition"] for r in rows if r["cls"] == cls)) for cls in ("blank", "spaced", "single")},
        blanks=dict(reference=len(blanks), preserved=sum(r["base"]["ok"] and r["treat"]["ok"] for r in blanks),
                    lost=sum(r["base"]["ok"] and not r["treat"]["ok"] for r in blanks),
                    recovered=sum(not r["base"]["ok"] and r["treat"]["ok"] for r in blanks),
                    lost_to_null=sum(r["base"]["ok"] and r["treat"]["observed"] is None for r in blanks),
                    lost_to_text=sum(r["base"]["ok"] and bool(r["treat"]["observed"]) for r in blanks)),
        legitimate_space=dict(
            spaced_positions=sum(r["cls"] == "spaced" for r in rows),
            space_removed=sum(1 for r in rows if r["cls"] == "spaced" and (r["token_delta"] or 0) < 0),
            space_removed_RW=sum(1 for r in rows if r["cls"] == "spaced" and (r["token_delta"] or 0) < 0 and r["transition"] == "RW"),
            tokens_increased=sum(1 for r in rows if (r["token_delta"] or 0) > 0),
            critical_merge_recoveries=sum(1 for r in crit if (r["token_delta"] or 0) < 0 and r["transition"] == "WR")),
        coverage=dict(
            critical_covered=sum(r["coverage"]["covered"] for r in crit),
            critical_unselected=sum(not r["coverage"]["covered"] for r in crit),
            missed_wrong_unselected=sum(not r["coverage"]["covered"] and not r["base"]["ok"] for r in crit),
            covered_zero_words=sum(r["coverage"]["covered"] and r["diagnostic"]["observed"] is None for r in crit),
            unselected_changed=sum(1 for r in rows if not r["coverage"]["covered"] and r["changed"]),
            all_covered=sum(r["coverage"]["covered"] for r in rows)),
        disagreements=dict(critical=sum(r["full_vs_crop"] == "disagree" for r in crit),
                           all=sum(r["full_vs_crop"] == "disagree" for r in rows)),
        diagnostic_crop=dict(critical_right=sum(1 for r in crit if r["diagnostic"] and r["diagnostic"]["ok"]),
                             critical_wrong=sum(1 for r in crit if r["diagnostic"] and not r["diagnostic"]["ok"]),
                             wrong_full_right_crop=sum(1 for r in crit if r["diagnostic"] and r["diagnostic"]["ok"] and not r["base"]["ok"]),
                             right_full_wrong_crop=sum(1 for r in crit if r["diagnostic"] and not r["diagnostic"]["ok"] and r["base"]["ok"])),
        decisions=dict(Counter(r["inferred_decision"] for r in crit)),
        author_decisions=dict(Counter(str(r["coverage"]["author_decision"]) for r in crit if r["coverage"]["covered"])),
    )
    matrix = Counter()
    for r in crit:
        d = r["diagnostic"]
        key = "|".join([("covered" if r["coverage"]["covered"] else "unselected"), r["full_vs_crop"],
                        "full_" + ("R" if r["base"]["ok"] else "W"),
                        "crop_" + ("-" if d is None else ("R" if d["ok"] else "W")),
                        r["inferred_decision"], r["transition"]])
        matrix[key] += 1
    summary["disagreement_matrix_critical"] = dict(sorted(matrix.items()))
    if comparison is not None:
        novel = comparison["new_or_changed_critical_errors"]
        summary["frozen_compare"] = dict(delta=comparison["delta"], inside_quality_budget=comparison["inside_quality_budget"],
                                         new_or_changed_critical_errors=len(novel),
                                         complete_matched_pair=comparison["complete_matched_pair"],
                                         new_wrong_source_links=len(comparison["new_wrong_source_links"]))
        summary["frozen_compare_consistent"] = len(novel) == tr["RW"] + ww_changed
    return summary


def evidence_for(key, family, at, rows_by_key, diags_by_page, bundle_family, truth):
    row = rows_by_key.get((family, at))
    if row is None:
        return dict(id=key, family=family, at=at, present=False)
    page = row["page"]
    rec = {p["page"]: p for p in (bundle_family or {}).get("pages", [])}.get(page)
    tp = {p["page"]: p for p in truth["pages"]}[page]
    near = []
    if rec is not None:
        full = rec["full"]
        box = row["reference_bbox"]
        grow = [box[0] - 2, box[1] - 2, box[2] + 2, box[3] + 2]
        for li, ln in enumerate(full["lines"]):
            for wi, w in enumerate(ln["words"]):
                pb = project_pinned(w["bbox"], full["width"], full["height"], (tp["width"], tp["height"]))
                if overlap_area(pb, grow) > 0:
                    near.append(dict(line=li, word=wi, text=w["text"], bbox_px=w["bbox"], bbox_pt=pb, line_text=ln["text"]))
    crops = []
    for d in diags_by_page.get(page, []):
        if d["id"] in row["coverage"]["touching"]:
            crops.append(dict(id=d["id"], rect=d["rect"], rect_pt=d["rect_pt"], kind=d["kind"], region=d["region"],
                              decision=d["decision"], words=[dict(text=s["text"], crop_px=s["crop_px"], bbox_pt=s["bbox"]) for s in d["spans"]],
                              reading=d["reads"].get(at)))
    return dict(id=key, family=family, at=at, present=True, row=row, full_words_near=near, crops=crops,
                selected=row["coverage"]["covered"],
                non_selection=None if row["coverage"]["covered"] else "no crop rectangle contains the reference centre")


# ---------------------------------------------------------------- main scoring over runs
def bundle_family(bundle, arm, family):
    for a in bundle["arms"]:
        if a["arm"] == arm:
            for f in a["families"]:
                if f["family"] == family:
                    return f
    return None


def score_runs(args):
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    scorer = FrozenScorer(args.scorer, python=args.python)
    module = scorer.module()
    checks = Checks()
    pins_all = load_pins(args.pins)
    truth_paths = pairs(args.truth)
    families = list(truth_paths)
    truths = {f: read_json(p) for f, p in truth_paths.items()}
    archive_paths = pairs(args.archive_score)
    archives = {f: (read_json(archive_paths[f]) if f in archive_paths else None) for f in families}
    for fam, path in truth_paths.items():
        checks.add(f"S0.truth.{fam}", fam in pins_all and sha256_file(path) == pins_all[fam]["truth_sha256"],
                   "truth digest equals its commitment (WP-0015 for H/A; coordinator key digest for fresh families)", sha256_file(path))
    runs = {}
    for spec in args.run:
        name, path = spec.split("=", 1)
        bundle = read_json(path)
        checks.add(f"S0.schema.{name}", bundle.get("schema") == "wp0019-review-run/1", "canonical run schema", bundle.get("schema"))
        runs[name] = dict(path=str(Path(path).resolve()), sha256=sha256_file(path), bundle=bundle)
    results = dict(kind="wp0019-review-score", scorer_sha256=scorer.sha256, runs={}, checks=None)
    position_keys = {}
    for name, run in runs.items():
        bundle = run["bundle"]
        rr = dict(order=bundle.get("order"), families={})
        for fam in families:
            preds = {}
            for arm in ARMS:
                bf = bundle_family(bundle, arm, fam)
                if bf is None:
                    checks.add(f"S1.present.{name}.{fam}.{arm}", False, "prediction present", None)
                    continue
                pred = Path(bf["prediction"])
                if not Path(pred).is_absolute():
                    pred = Path(run["path"]).parent / pred
                sc_out = out / "scores" / name / f"{fam}-{arm}.json"
                sc_out.parent.mkdir(parents=True, exist_ok=True)
                res = scorer.run(truth_paths[fam], pred, sc_out, baseline=None)
                ok = res["returncode"] == 0
                checks.add(f"S1.score.{name}.{fam}.{arm}", ok, "frozen scorer exits 0 in a separate process",
                           dict(returncode=res["returncode"], stderr=res["stderr"][-400:], out_sha256=res["out_sha256"],
                                prediction_sha256=sha256_file(pred)))
                if ok:
                    preds[arm] = dict(path=pred, score=read_json(sc_out), score_sha256=res["out_sha256"],
                                      prediction_sha256=sha256_file(pred), family_bundle=bf)
            if set(preds) != set(ARMS):
                rr["families"][fam] = dict(evaluable=False)
                continue
            cmp_out = out / "scores" / name / f"{fam}-treatment-vs-baseline.json"
            res = scorer.run(truth_paths[fam], preds["treatment"]["path"], cmp_out, baseline=preds["baseline"]["path"])
            comparison = read_json(cmp_out)["comparison"] if res["returncode"] == 0 else None
            checks.add(f"S1.compare.{name}.{fam}", res["returncode"] == 0, "frozen compare() separate process", res["out_sha256"])
            for arm in ARMS:
                sc = preds[arm]["score"]
                c = sc["counts"]
                pins = pins_all[fam]
                checks.add(f"S2.denominator.{name}.{fam}.{arm}",
                           (c["critical_values"], c["reference_cells"], c["reference_lines"], sc["expected_pages"], sc["output_pages"]) ==
                           (pins["criticals"], pins["cells"], pins["lines"], pins["pages"], pins["pages"]),
                           "all criticals/cells/lines/pages in the denominator",
                           dict(critical_values=c["critical_values"], reference_cells=c["reference_cells"],
                                reference_lines=c["reference_lines"], output_pages=sc["output_pages"]))
                checks.add(f"S2.complete.{name}.{fam}.{arm}", sc["packet_complete"] and c["wrong_source"] == 0,
                           "packet complete, no wrong-source links", dict(faults=Counter(f["issue"] for f in sc["faults"])))
            rows, diags = join_family(fam, truths[fam], preds["baseline"]["score"], preds["treatment"]["score"],
                                      archives[fam], module, preds["treatment"]["family_bundle"])
            summ = summarize(rows, comparison)
            checks.add(f"S3.consistency.{name}.{fam}", summ.get("frozen_compare_consistent"),
                       "reviewer RW+WW_changed equals frozen compare() new_or_changed_critical_errors",
                       summ.get("frozen_compare", {}).get("new_or_changed_critical_errors"))
            unsel = [r["at"] for r in rows if not r["coverage"]["covered"] and r["changed"]]
            checks.add(f"S5.full_attach_unselected_unchanged.{name}.{fam}", not unsel,
                       "every position with no covering crop keeps its own full-pass (observed, flagged) in the treatment",
                       unsel[:100], gating=False)
            base_counts = preds["baseline"]["score"]["counts"]
            arch = pins_all[fam].get("archive")
            base_vs_archive = None if arch is None else dict(
                current={k: base_counts[k] for k in arch}, archive=arch,
                equal_counts=all(base_counts[k] == v for k, v in arch.items()),
                positions_differing=[r["at"] for r in rows if r["archive"] is not None and
                                     (r["archive"]["observed"], r["archive"]["ok"]) != (r["base"]["observed"], r["base"]["ok"])])
            rows_by_key = {(fam, r["at"]): r for r in rows}
            evidence = {}
            for key, (f2, at) in list(WITNESSES.items()) + list(ZERO_WORD_CELLS.items()):
                if f2 == fam:
                    evidence[key] = evidence_for(key, fam, at, rows_by_key, diags, preds["treatment"]["family_bundle"], truths[fam])
            fam_dir = out / "joins" / name
            fam_dir.mkdir(parents=True, exist_ok=True)
            rows_sha = write_new(fam_dir / f"{fam}-rows.json", rows)
            ev_sha = write_new(fam_dir / f"{fam}-individual-evidence.json", evidence)
            rr["families"][fam] = dict(evaluable=True, summary=summ, baseline_vs_archive=base_vs_archive,
                                       rows_sha256=rows_sha, evidence_sha256=ev_sha,
                                       prediction_sha256={arm: preds[arm]["prediction_sha256"] for arm in ARMS},
                                       score_sha256={arm: preds[arm]["score_sha256"] for arm in ARMS},
                                       individual={k: dict(transition=v["row"]["transition"], selected=v["selected"],
                                                           base=v["row"]["base"], treat=v["row"]["treat"],
                                                           diagnostic=v["row"]["diagnostic"])
                                                   for k, v in evidence.items() if v["present"]})
            position_keys[(name, fam)] = {r["at"]: (r["base"]["observed"], r["base"]["flagged"], r["treat"]["observed"], r["treat"]["flagged"]) for r in rows}
        results["runs"][name] = rr
    # reproducibility across runs (all positions, both arms)
    names = list(runs)
    repro = {}
    for fam in families:
        present = [n for n in names if (n, fam) in position_keys]
        ref = present[0] if present else None
        diffs = {}
        for n in present[1:]:
            a, b = position_keys[(ref, fam)], position_keys[(n, fam)]
            diffs[n] = sorted(k for k in a if a[k] != b.get(k))
        repro[fam] = dict(reference=ref, compared=present[1:], differing_positions=diffs,
                          identical=all(not v for v in diffs.values()) and len(present) == len(names))
        checks.add(f"S4.reproducible.{fam}", repro[fam]["identical"] if len(names) > 1 else None,
                   "per-position (observed, flagged) identical in both arms across every run", diffs)
    results["reproducibility"] = repro
    results["families"] = families
    results["stage"] = args.stage
    results["gate"] = gate(results, names, args.require_runs, families, args.stage)
    results["checks"] = checks.rows
    results["check_summary"] = checks.summary()
    results["failed_checks"] = checks.failed()
    sha = write_new(out / "stage1-score.json", results)
    print(json.dumps(dict(out=str(out / "stage1-score.json"), sha256=sha, gate=results["gate"],
                          check_summary=results["check_summary"], failed=results["failed_checks"]), indent=1))


def gate(results, names, required, families, stage):
    """Preregistered rule (PREREGISTRATION sections 6 and 9). Controls are combined in review_checks.py decision.
    Stage 1: pooled net critical WR-RW >= 1 and RW == 0 in every family, in every run.
    Stage 2 adds: zero lost correct blanks in every family (pooled WR >= 1 equals net >= 1 once RW == 0)."""
    per_run = {}
    for n in names:
        fams = results["runs"][n]["families"]
        if not all(fams.get(f, {}).get("evaluable") for f in families):
            per_run[n] = dict(evaluable=False)
            continue
        s = {f: fams[f]["summary"] for f in families}
        net = sum(s[f]["net"] for f in families)
        rw = {f: s[f]["RW"] for f in families}
        lost_blanks = {f: s[f]["blanks"]["lost"] for f in families}
        ok = net >= 1 and all(v == 0 for v in rw.values())
        if str(stage) == "2":
            ok = ok and all(v == 0 for v in lost_blanks.values())
        per_run[n] = dict(evaluable=True, net_pooled=net, WR_pooled=sum(s[f]["WR"] for f in families), RW=rw,
                          lost_blanks=lost_blanks, passes=ok)
    missing = [r for r in (required or []) if r not in per_run]
    all_eval = bool(per_run) and all(v["evaluable"] for v in per_run.values()) and not missing
    repro = all(results["reproducibility"][f]["identical"] for f in families) if len(names) > 1 else False
    quality = all_eval and all(v["passes"] for v in per_run.values())
    if not all_eval:
        verdict = "INCONCLUSIVE"
    elif not quality:
        verdict = "FAIL_QUALITY"
    elif not repro:
        verdict = "FAIL_NOT_REPRODUCIBLE"
    else:
        verdict = "PASS"
    return dict(per_run=per_run, missing_required_runs=missing, all_evaluable=all_eval, reproducible=repro,
                quality_rule_met_every_run=quality, score_component=verdict)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("--scorer", required=True)
    s.add_argument("--python", default=sys.executable)
    s.add_argument("--truth", action="append", required=True, help="FAMILY=truth.json (released only after predictions froze)")
    s.add_argument("--archive-score", action="append", default=[], help="FAMILY=historical WP-0015 score (H/A disclosure)")
    s.add_argument("--pins", help="coordinator-committed pins JSON for fresh families")
    s.add_argument("--stage", choices=["1", "2"], default="1")
    s.add_argument("--run", action="append", required=True, help="NAME=canonical run bundle path")
    s.add_argument("--require-runs", nargs="*", default=[])
    s.add_argument("--out", required=True)
    args = p.parse_args()
    if args.cmd == "score":
        score_runs(args)


if __name__ == "__main__":
    main()
