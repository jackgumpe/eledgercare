"""Post-freeze H/A scoring and evidence join. This module is never imported by the runner."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SCORER = HERE.parents[3] / "docs/evaluation/WP-0015/score.py"
SCORER_SHA = "1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7"
WITNESSES = {("H", "page/2/table/1/row/2/col/1"), ("A", "page/60/table/1/row/2/col/2"),
             ("H", "page/1/line/2"), ("H", "page/2/line/2")}
sys.path.insert(0, str(SCORER.parent))
import score


def read(p):
    return json.loads(p.read_bytes())


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, obj):
    with p.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        f.write("\n")


def check(ok, message):
    if not ok:
        raise ValueError(message)


def project(box, meta):
    size = meta["width"], meta["height"]
    return [round(v * meta["points"][i%2]/size[i%2], 3) for i, v in enumerate(box)]


def positive_intersection(a, b):
    return all(max(a[i], b[i]) < min(a[i+2], b[i+2]) for i in (0, 1))


def mechanisms(expected, observed):
    # Lexicographic minimum edit distance followed by minimum number of whitespace edits.
    # At equal cost prefer unchanged/replaced pairs, then deletion, then insertion.
    if observed is None or not observed and expected:
        return "no_returned_word"
    expected, observed = score.norm(expected), score.norm(observed)
    if expected == observed:
        return "exact"
    if "".join(expected.split()) == "".join(observed.split()):
        return "whitespace_only"
    prior = [(i, sum(v.isspace() for v in observed[:i])) for i in range(len(observed)+1)]
    for i, a in enumerate(expected, 1):
        row = [(i, prior[0][1] + a.isspace())]
        for j, b in enumerate(observed, 1):
            diag, delete, insert = prior[j-1], prior[j], row[j-1]
            row.append(min((diag[0]+(a != b), diag[1]+(a != b and (a.isspace() or b.isspace()))),
                           (delete[0]+1, delete[1]+a.isspace()),
                           (insert[0]+1, insert[1]+b.isspace())))
        prior = row
    return "mixed_character_and_whitespace" if prior[-1][1] else "character_difference"


def table_map(ref, predicted):
    candidates = sorted((-score.iou(t["bbox"], p["bbox"]), ti, pi)
                        for ti, t in enumerate(ref["tables"]) for pi, p in enumerate(predicted["tables"]))
    matches, used = {}, set()
    for cost, ti, pi in candidates:
        if -cost >= .5 and ti not in matches and pi not in used:
            matches[ti] = pi
            used.add(pi)
    return matches


def reference_fields(ref):
    p = ref["page"]
    result = {}
    for li, line in enumerate(ref["lines"]):
        result[f"page/{p}/line/{li+1}"] = dict(line, kind="prose")
    for ti, table in enumerate(ref["tables"]):
        for ri, row in enumerate(table["rows"]):
            for ci, c in enumerate(row):
                result[f"page/{p}/table/{ti+1}/row/{ri+1}/col/{ci+1}"] = dict(c, kind="cell",
                                                                             index=(ti, ri, ci))
    return result


def owners(box, fields):
    cell = next((at for at, f in fields.items() if f["kind"] == "cell" and score.in_cell(box, f["bbox"])), None)
    if cell:
        return cell
    viable = [(abs((f["bbox"][1]+f["bbox"][3])-(box[1]+box[3])), i, at)
              for i, (at, f) in enumerate(fields.items())
              if f["kind"] == "prose" and score.on_line(box, f["bbox"])]
    return min(viable)[2] if viable else None


def indexed(score_page):
    main = {r["at"]: r for r in score_page["cells"] + score_page["lines"]}
    critical = {r["at"]: r for r in score_page["critical"]}
    return main, critical


def trace_page(ref, base, trial, evidence, controls, treatments, family):
    p = ref["page"]
    meta = evidence["bitmap"]
    fields = reference_fields(ref)
    grids = table_map(ref, base)
    span_flags = [{owners(s["bbox"], fields) for s in pred["spans"] if s.get("flagged", False)}
                  for pred in (base, trial)]
    raw = evidence["full"]
    words = {(li, wi): w for li, line in enumerate(raw["lines"]) for wi, w in enumerate(line["words"])}
    projected = {r: project(w["bbox"], meta) for r, w in words.items()}
    full_owner = {key: owners(box, fields) for key, box in projected.items()}
    scored, crit = indexed(controls)
    treated, trialcrit = indexed(treatments)
    region_by_grid, regions_for = {}, defaultdict(list)
    for ix, r in enumerate(evidence["regions"]):
        if r["kind"] == "cell":
            region_by_grid[tuple(r["grid_index"])] = ix
        for at in {full_owner[tuple(key)] for key in r["full_word_refs"]} - {None}:
            regions_for[at].append(ix)
    evidence_file = f"B/page-{p:03d}.json"
    records = []
    for at, field in fields.items():
        iscrit = at in crit
        cell = field["kind"] == "cell"
        if cell and field["index"][0] in grids:
            ti, ri, ci = field["index"]
            grid = (grids[ti], ri, ci)
            indices = [region_by_grid[grid]] if grid in region_by_grid else []
            method = "matched_grid"
        else:
            indices = regions_for[at]
            method = "reference_cell_spans" if cell else "reference_line_spans"
        full_score = crit[at] if iscrit else scored[at]
        crop_score = trialcrit[at] if iscrit else treated[at]
        before, after = bool(full_score["correct"]), bool(crop_score["correct"])
        transition = ("right" if before else "wrong") + "_to_" + ("right" if after else "wrong")
        zero = cell and bool(field["text"]) and not any(positive_intersection(b, field["bbox"])
                                                       for b in projected.values())
        is_witness = (family, at) in WITNESSES
        detail = []
        for ix in indices:
            r = evidence["regions"][ix]
            probe = dict(index=ix, id=r["id"], decision=r["decision"], eligible=r["eligible"],
                         selected=r["selected"], reason=r["reason"], flagged=r["flagged"],
                         disagreement=r["disagreement"], full_value=r["full_value"],
                         emitted_value=r["emitted_value"], crop_value=r["crop_value"], diagnostic_correct=None)
            if r["selected"]:
                if method == "matched_grid":
                    probe["diagnostic_correct"] = score.norm(r["crop_value"]) == score.norm(field["text"])
                else:
                    spans = [dict(text=w["text"], bbox=project(w["bbox"], meta), flagged=False)
                             for w in r["projected_words"]]
                    isolated = score.layout(ref, dict(spans=spans), evidence["source_sha256"])
                    m, c = indexed(isolated)
                    probe["diagnostic_correct"] = bool((c if iscrit else m)[at]["correct"])
            if zero or is_witness:
                probe.update(rect_px=r["rect_px"], full_word_refs=r["full_word_refs"],
                             full_words=[words[tuple(key)] for key in r["full_word_refs"]],
                             full_raw_lines=[dict(line=li, **raw["lines"][li])
                                             for li in sorted({ref[0] for ref in r["full_word_refs"]})],
                             crop=r["crop"], projected_words=r["projected_words"])
            detail.append(probe)
        check(scored[at]["observed"] == full_score["observed"]
              and treated[at]["observed"] == crop_score["observed"], "observed field mismatch")
        selected = any(r["selected"] for r in detail)
        records.append(dict(at=at, kind=field["kind"], method=method, critical=iscrit,
                            expected=field["text"], critical_expected=full_score["expected"] if iscrit else None,
                            bbox_points=field["bbox"], before=full_score["observed"], after=crop_score["observed"],
                            before_correct=before, after_correct=after, transition=transition,
                            before_flagged=full_score.get("flagged", at in span_flags[0]),
                            after_flagged=crop_score.get("flagged", at in span_flags[1]),
                            before_mechanism=mechanisms(field["text"], full_score["observed"]),
                            after_mechanism=mechanisms(field["text"], crop_score["observed"]),
                            selected=selected, omitted=not selected, selector_region_missing=not detail,
                            any_disagreement=any(r["disagreement"] for r in detail),
                            any_crop_diagnostic_exact=any(r["diagnostic_correct"] for r in detail),
                            witness=is_witness, nonempty_cell_no_full_word_intersection=zero,
                            page_evidence=evidence_file, regions=detail))
    return records


def tally(rows, key):
    return dict(sorted(Counter(r[key] for r in rows).items()))


def summarize(rows, receipt, application):
    critical = [r for r in rows if r["critical"]]
    selected = [r for r in critical if r["selected"]]
    blanks = [r for r in rows if r["kind"] == "cell" and r["expected"] == ""]
    return dict(critical=len(critical), correct_full=sum(r["before_correct"] for r in critical),
                correct_crop=sum(r["after_correct"] for r in critical), transitions=tally(critical, "transition"),
                selected=len(selected), omitted=len(critical)-len(selected),
                selected_transitions=tally(selected, "transition"),
                omitted_transitions=tally([r for r in critical if not r["selected"]], "transition"),
                no_candidate=sum(r["selector_region_missing"] for r in critical),
                newly_wrong=sum(r["transition"] == "right_to_wrong" for r in critical),
                newly_wrong_unflagged=sum(r["transition"] == "right_to_wrong" and not r["after_flagged"]
                                          for r in critical),
                newly_unflagged=sum(not r["after_correct"] and not r["after_flagged"]
                                    and (r["before_correct"] or r["before_flagged"]) for r in critical),
                final_unflagged_errors=sum(not r["after_correct"] and not r["after_flagged"] for r in critical),
                critical_disagreement_matrix=dict(sorted(Counter(
                    f"{r['transition']}|{'disagree' if r['any_disagreement'] else 'agree'}" if r["selected"]
                    else f"{r['transition']}|unselected" for r in critical).items())),
                diagnostic_exact_but_final_wrong=[r["at"] for r in critical
                                                  if r["any_crop_diagnostic_exact"] and not r["after_correct"]],
                before_error_mechanisms=tally([r for r in critical if not r["before_correct"]], "before_mechanism"),
                after_error_mechanisms=tally([r for r in critical if not r["after_correct"]], "after_mechanism"),
                blank_cells=len(blanks), originally_correct_blanks=sum(r["before"] == "" for r in blanks),
                preserved_blanks=sum(r["before"] == r["after"] == "" for r in blanks),
                blank_missing_after=sum(r["after"] is None for r in blanks),
                attempted_blank_cells=sum(r["selected"] for r in blanks),
                zero_word_positions=[r["at"] for r in rows if r["nonempty_cell_no_full_word_intersection"]],
                application_regions=application, elapsed_ns={arm: receipt["arms"][arm]["elapsed_ns"] for arm in "AB"},
                pages_per_minute={arm: receipt["arms"][arm]["pages_per_minute"] for arm in "AB"},
                added_ms_per_page=receipt["added_ms_per_page"], crops_per_page=receipt["arms"]["B"]["crops_per_page"],
                startup_ns=receipt["startup_ns"], warmup_elapsed_ns=receipt["warmup"]["elapsed_ns"])


def account(truth_path, paired, out):
    check(digest(SCORER) == SCORER_SHA, "scorer pin")
    receipt = read(paired / "receipt.json")
    truth = read(truth_path)
    check(truth["source_sha256"] == receipt["source_sha256"] and truth["family"] == receipt["family"],
          "unmatched source")
    out.mkdir(parents=True, exist_ok=False)
    predictions, scores = {}, {}
    for arm in "AB":
        path = paired / arm / "prediction.json"
        check(digest(path) == receipt["arms"][arm]["prediction_sha256"], "prediction receipt")
        dest = out / f"score-{arm}.json"
        subprocess.run([sys.executable, "-I", "-B", str(SCORER), str(truth_path), str(path),
                        "--out", str(dest)], check=True)
        predictions[arm], scores[arm] = read(path), read(dest)
        check(scores[arm]["packet_complete"] and not scores[arm]["faults"], "incomplete scored packet")
    rows, decisions, matrix = [], Counter(), Counter()
    crop_ms = []
    for i, ref in enumerate(truth["pages"]):
        path = paired / "B" / f"page-{i+1:03d}.json"
        check(digest(path) == receipt["arms"]["B"]["page_evidence_sha256"][i], "page evidence receipt")
        evidence = read(path)
        check(evidence["full_identity"] == receipt["arms"]["A"]["full_identities"][i]
              == receipt["arms"]["B"]["full_identities"][i], "full identity")
        rows.extend(trace_page(ref, predictions["A"]["pages"][i], predictions["B"]["pages"][i], evidence, scores["A"]["pages"][i],
                               scores["B"]["pages"][i], truth["family"]))
        for region in evidence["regions"]:
            if region["selected"]:
                decisions[region["decision"]] += 1
                matrix["different" if region["disagreement"] else "same"] += 1
                if "recognize_ms" in region["crop"]:
                    crop_ms.append(region["crop"]["recognize_ms"])
    check(len(crit := [r for r in rows if r["critical"]]) == scores["A"]["counts"]["critical_values"]
          and sum(not r["after_correct"] for r in crit) == scores["B"]["counts"]["critical_errors"]
          and len({r["at"] for r in rows}) == len(rows), "field coverage")
    app = dict(decisions=dict(decisions), disagreements=dict(matrix), attempted=sum(decisions.values()),
               crop_recognition_ms_returned=len(crop_ms), crop_recognition_ms_sum=sum(crop_ms))
    summary = summarize(rows, receipt, app)
    summary.update(family=truth["family"], order=receipt["order"], scorer_sha256=SCORER_SHA,
                   truth_sha256=digest(truth_path), receipt_sha256=digest(paired/"receipt.json"),
                   score_counts={a: scores[a]["counts"] for a in "AB"})
    write(out / "all-fields.json", rows)
    write(out / "nine-witness-subset.json", [r for r in rows if r["witness"] or r["nonempty_cell_no_full_word_intersection"]])
    write(out / "summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("family", "order", "transitions", "newly_unflagged", "selected")}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("truth", "paired", "out"):
        p.add_argument("--"+name, required=True, type=Path)
    a = p.parse_args()
    account(a.truth.resolve(), a.paired.resolve(), a.out.resolve())
