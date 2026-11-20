"""Compare the frozen baseline with a copy containing empty tables on each page.

Run only after the original four witness traces have been recorded. All observations
come from separate frozen scorer processes. Paths and hashes in cells.jsonl explain
their selections using the scorer's actual reported boxes and the original archive.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import runpy

from baseline import canon, check, digest, new_output, read, score_file, verify_archive, write


def without_tables(prediction):
    return {**prediction, "pages": [{**p, "tables": []} for p in prediction["pages"]]}


def retained_prediction(prediction):
    """Independent projection for verifying that the treatment changed only tables."""
    return {**prediction, "pages": [{k: v for k, v in p.items() if k != "tables"} for p in prediction["pages"]]}


def invariant(before, after, what):
    a, b = canon(before), canon(after)
    check(a == b, what)
    return digest(a)


def page_invariants(before, after):
    """Store equality digests for the complete ordered records, not just counts."""
    def prose(p):
        return [c for c in p["critical"] if "/line/" in c["at"]]

    keys = ("page", "state", "reference_chars", "edit_distance")
    before_edits = {k: before[k] for k in keys}
    return dict(**before_edits, line_records=len(before["lines"]), critical_lines=len(prose(before)),
                edits_sha256=invariant(before_edits, {k: after[k] for k in keys}, "page identity/state/edits"),
                lines_sha256=invariant(before["lines"], after["lines"], "per-line records"),
                critical_lines_sha256=invariant(prose(before), prose(after), "prose-critical records"),
                extra_cells_before=before["extra_cells"], extra_cells_after=after["extra_cells"])


def scored_observation(detail, page, ref_table, ri, ci, scorer):
    """Resolve archived grid entry or actual joined spans from the scorer record."""
    box = detail["reported_table_bbox"]
    tables = page["tables"]
    ious = [scorer["iou"](ref_table["bbox"], t["bbox"]) for t in tables]
    data = {k: detail[k] for k in ("observed", "correct", "flagged")}
    if box is not None:
        matches = [i for i, table in enumerate(tables) if table["bbox"] == box]
        check(len(matches) == 1, "ambiguous scored grid at " + detail["at"])
        i = matches[0]
        rows = tables[i]["rows"]
        if ri < len(rows) and ci < len(rows[ri]):
            entry = rows[ri][ci]
            value, flag = scorer["value"](entry)
            pointers = [f"/tables/{i}/rows/{ri}/{ci}"]
        else:
            value, flag = None, False
            pointers = []
        check(ious[i] >= .5, "selected table below match threshold")
        data.update(mode="matched_grid", matched_iou=ious[i], selected=pointers)
    else:
        boxes = detail["reported_span_boxes"]
        by_box = {tuple(b) for b in boxes}
        spans = [(i, span) for i, span in enumerate(page["spans"]) if tuple(span["bbox"]) in by_box]
        check([s["bbox"] for _, s in spans] == boxes, "ambiguous fallback span at " + detail["at"])
        value, flag = scorer["joined"]([s for _, s in spans])
        spans.sort(key=lambda item: (item[1]["bbox"][0], item[1]["bbox"][1]))
        data.update(mode="reference_box_fallback", matched_iou=None,
                    selected=[f"/spans/{i}" for i, _ in spans])
    check((value, flag) == (detail["observed"], detail["flagged"]), "selection verification " + detail["at"])
    data["best_candidate_iou"] = max(ious, default=None)
    return data


def summarize(rows):
    transitions = Counter(r["transition"] for r in rows)
    return dict(rows=len(rows), gain=transitions["gain"], loss=transitions["loss"],
                unchanged_wrong=transitions["unchanged_wrong"], unchanged_right=transitions["unchanged_right"],
                unavailable_score_rows=0,
                wrong_both_observation_changed=sum(r["transition"] == "unchanged_wrong" and
                                                   r["before"]["observed"] != r["after"]["observed"] for r in rows),
                null_observed_before=sum(r["before"]["observed"] is None for r in rows),
                null_observed_after=sum(r["after"]["observed"] is None for r in rows),
                flagged_before=sum(r["before"]["flagged"] for r in rows),
                flagged_after=sum(r["after"]["flagged"] for r in rows),
                flag_changes=sum(r["before"]["flagged"] != r["after"]["flagged"] for r in rows))


def collect_cells(packet, admission, reference, before_page, after_page, before, after, scorer):
    n = reference["page"]
    page_file = f"windows/page-{n:03d}.json"
    result = []
    index = 0
    for ti, table in enumerate(reference["tables"]):
        for ri, row in enumerate(table["rows"]):
            for ci, cell in enumerate(row):
                at = f"page/{n}/table/{ti+1}/row/{ri+1}/col/{ci+1}"
                b, a = before["cells"][index], after["cells"][index]
                check(b["at"] == a["at"] == at and a["expected"] == b["expected"] == scorer["norm"](cell["text"]),
                      "cell location/expected")
                check(b["reference_bbox"] == a["reference_bbox"] == cell["bbox"], "reference cell region")
                original = scored_observation(b, before_page, table, ri, ci, scorer)
                oracle = scored_observation(a, after_page, table, ri, ci, scorer)
                check(oracle["mode"] == "reference_box_fallback", "expected fallback after")
                if original["mode"] == oracle["mode"]:
                    check((original["observed"], original["flagged"], original["selected"]) ==
                          (oracle["observed"], oracle["flagged"], oracle["selected"]), "already fallback changed")
                transition = {(False, True): "gain", (True, False): "loss", (False, False): "unchanged_wrong",
                              (True, True): "unchanged_right"}[b["correct"], a["correct"]]
                result.append(dict(packet=packet, at=at, expected=b["expected"], critical=cell["critical"],
                                   before=original, after=oracle, transition=transition,
                                   archive_page=page_file, archive_page_sha256=admission["files"][page_file],
                                   reference_pointer=f"/pages/{n-1}/tables/{ti}/rows/{ri}/{ci}",
                                   truth_sha256=admission["files"]["truth.json"], reference_bbox=cell["bbox"],
                                   score_pointer=f"/pages/{n-1}/cells/{index}"))
                index += 1
    check(index == len(before["cells"]) == len(after["cells"]), "page reference-cell census")
    return result


def compare(inputs, packet, base_dir, out):
    receipt = read(base_dir / "baseline.json")
    admission = verify_archive(inputs, packet)
    check(canon(receipt["admission"]) == canon(admission), "baseline input archive changed")
    before = read(base_dir / "score.json")
    check(receipt["score_sha256"] == digest((base_dir / "score.json").read_bytes()), "baseline score digest")
    archive = inputs / packet
    historic = read(archive / "historical-score.json")
    historic.pop("comparison", None)
    invariant(before, historic, "baseline must equal historical Windows score")
    ref = read(archive / "truth.json")
    prediction = read(archive / "windows/prediction.json")
    trial_file = out / "tables-empty.json"
    write(trial_file, without_tables(prediction))
    trial = read(trial_file)
    retained = invariant(retained_prediction(prediction), retained_prediction(trial), "structural tables-only diff")
    changed_paths = []
    for i, (p, t) in enumerate(zip(prediction["pages"], trial["pages"], strict=True)):
        check(isinstance(p["tables"], list) and t["tables"] == [], "original and trial table arrays")
        if p["tables"]:
            changed_paths.append(f"/pages/{i}/tables")
    scorer = inputs / "control/score.py"
    after = score_file(scorer, archive / "truth.json", trial_file, out / "score.json")
    explain = runpy.run_path(str(scorer))
    packet_keys = ("family", "source_sha256", "packet_complete", "expected_pages", "output_pages",
                   "observed_order", "faults", "extra_page_outputs")
    common = invariant({k: before[k] for k in packet_keys}, {k: after[k] for k in packet_keys},
                       "packet identity/order/completeness/faults/extra pages")
    pages, rows = [], []
    for reference, p, t, b, a in zip(ref["pages"], prediction["pages"], trial["pages"],
                                     before["pages"], after["pages"], strict=True):
        pages.append(page_invariants(b, a))
        rows.extend(collect_cells(packet, admission, reference, p, t, b, a, explain))
    check(len({r["at"] for r in rows}) == len(rows), "unique reference locations")
    total = summarize(rows)
    modes = {mode: summarize([r for r in rows if r["before"]["mode"] == mode])
             for mode in ("matched_grid", "reference_box_fallback")}
    for arm, census in (("before", before["counts"]), ("after", after["counts"])):
        check(len(rows) == census["reference_cells"], "reference cell denominator")
        check(sum(r[arm]["correct"] for r in rows) == census["correct_cells"], "correct cell numerator")
        check(sum(p[f"extra_cells_{arm}"] for p in pages) == census["extra_cells"], "extra cell accounting")
    check(after["counts"]["correct_cells"] - before["counts"]["correct_cells"] == total["gain"] - total["loss"],
          "paired accounting")
    check(verify_archive(inputs, packet) == admission, "input archive changed during scoring")
    with (out / "cells.jsonl").open("xb") as stream:
        for row in rows:
            stream.write(canon(row) + b"\n")
    report = dict(packet=packet, archive_run=admission["run"], archive_folder=admission["folder"],
                  scorer_sha256=receipt["control_sha256"]["score.py"],
                  original_prediction_sha256=admission["files"]["windows/prediction.json"],
                  trial_prediction_sha256=digest(trial_file.read_bytes()), baseline_score_sha256=receipt["score_sha256"],
                  trial_score_sha256=digest((out / "score.json").read_bytes()),
                  retained_prediction_sha256=retained, changed_pointers=changed_paths, packet_invariant_sha256=common,
                  complete=after["packet_complete"], faults=after["faults"], counts_before=before["counts"],
                  counts_after=after["counts"], transitions=total, by_original_mode=modes,
                  cells_jsonl_sha256=digest((out / "cells.jsonl").read_bytes()), pages=pages)
    write(out / "pair.json", report)
    print(f"{packet} {total['rows']} rows: {total['gain']} gained, {total['loss']} lost")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs", type=Path)
    p.add_argument("packet", choices=("H", "A"))
    p.add_argument("baseline", type=Path, help="verified baseline directory for this packet")
    p.add_argument("output", type=Path, help="fresh scratch directory")
    a = p.parse_args()
    compare(a.inputs.resolve(), a.packet, a.baseline.resolve(), new_output(a.output, a.inputs))
