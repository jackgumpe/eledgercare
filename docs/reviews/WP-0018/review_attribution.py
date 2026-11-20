"""WP-0018 /003 reviewer attribution of every H/A reference cell and prose line (eld-rd-reviewer).

Second phase, CPU-only. Written and committed after the released paired run and BEFORE any WP-0018
author source or evidence was opened. Reads the reviewer copies plus the reviewer's own paired
outputs (hash-checked against paired.json) and assigns each incorrect location the earliest stage
the archived evidence supports. No OCR, WinRT, rasterization or GPU.

Stages, in pipeline order, for an incorrect cell (expected != observed); the first that applies:
  no_intersecting_word   no raw WinRT word box has positive-area overlap with the reference cell
  off_centre_word        a word overlaps the cell but none has its centre inside it
  winrt_text             the centred raw words, joined in adapter order, already differ from expected
                         (adapter_differs records whether the emitted grid cell also differs from them)
  adapter_grid           the centred raw words equal expected but the emitted grid cell differs
  scorer_selection       the emitted value equals expected yet the scored value differs
For an incorrect line (raw words = all word boxes with positive-area overlap with the reference line):
  no_intersecting_word   no word overlaps the line and none is assigned to it
  winrt_text             the overlapping raw words, joined in scorer order, already differ from expected
                         (assignment_differs records unassigned overlapping or assigned non-overlapping words)
  scorer_assignment      the overlapping raw words equal expected but the scorer's assigned set differs
Text differences: whitespace_only (word split/merge only), character_only (same space boundaries
after alignment), character_and_split (both), missing_value (scored None), empty_value (scored ''
for expected text), text_in_printed_empty (text scored for an expected '').
"""
import sys

sys.dont_write_bytecode = True

import argparse
import json
from collections import Counter
from pathlib import Path

import review_checks as rc

norm = None  # bound to the frozen scorer's norm() in main()


def overlap(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def centred(box, region):
    x, y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return region[0] <= x < region[2] and region[1] <= y < region[3]


def alignment_pairs(a, b):
    """Full minimal alignment as (i, j) pairs; None marks an insertion or deletion."""
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    pairs, i, j = [], n, m
    while i or j:
        if i and j and d[i][j] == d[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i and d[i][j] == d[i - 1][j] + 1:
            pairs.append((i - 1, None))
            i -= 1
        else:
            pairs.append((None, j - 1))
            j -= 1
    return list(reversed(pairs))


def boundaries(text):
    """Space-free indices preceded by a token boundary."""
    out, pos = set(), 0
    for t, tok in enumerate(text.split()):
        if t:
            out.add(pos)
        pos += len(tok)
    return out


def text_effect(expected, observed):
    if observed is None:
        return "missing_value"
    e, o = norm(expected), norm(observed)
    if e == o:
        return "none"
    if not o:
        return "empty_value"
    if not e:
        return "text_in_printed_empty"
    a, b = e.replace(" ", ""), o.replace(" ", "")
    if a == b:
        return "whitespace_only"
    consumed, mapped = 0, {}
    for i, j in alignment_pairs(a, b):
        if j is not None:
            mapped[j] = consumed
        if i is not None:
            consumed += 1
    observed_boundaries = {mapped[j] for j in boundaries(o)}
    return "character_only" if observed_boundaries == boundaries(e) else "character_and_split"


def char_ops(expected, observed):
    """Non-space character operations on the space-free strings (one minimal alignment)."""
    if observed is None:
        return []
    a = rc.align(norm(expected).replace(" ", ""), norm(observed).replace(" ", ""))
    return [(op["op"], op["expected"], op["observed"]) for op in a["ops"]]


def split_count(expected, observed):
    if observed is None:
        return None
    return len(norm(observed).split()) - len(norm(expected).split())


def page_inputs(paths, num):
    raw = rc.load(rc.page_file(paths, "raw", num))
    page = rc.load(rc.page_file(paths, "page", num))
    window = rc.load(rc.page_file(paths, "window", num))
    words = rc.raw_words(raw)
    rebuilt, membership = rc.adapter_layout(words, window["rule_tables"])
    if [dict(text=w["text"], bbox=w["bbox"], flagged=False) for w in words] != page["spans"]:
        raise SystemExit(f"page {num}: spans are not the projected raw words")
    return raw, page, window, words, membership


def near_matches(words, expected, limit=2):
    target = expected.replace(" ", "")
    out = []
    for k, w in enumerate(words):
        d = rc.align(target, w["text"].replace(" ", ""))["distance"]
        if d <= limit:
            out.append(dict(span=k, text=w["text"], distance=d, bbox=w["bbox"]))
    return out


def attribute_family(fam, data, paired_dir, scorer):
    paths = rc.family_paths(data, fam)
    truth = rc.load(paths["truth"])
    report = rc.load(Path(paired_dir) / "paired.json")
    pf = report[f"paired_{fam}"]
    before_path, after_path = Path(paired_dir) / f"paired-{fam}-before.json", Path(paired_dir) / f"paired-{fam}-after.json"
    hashes = [rc.sha256(before_path.read_bytes()), rc.sha256(after_path.read_bytes())]
    if hashes != [r["output_sha256"] for r in pf["runs"]]:
        raise SystemExit(f"{fam}: paired outputs do not match paired.json receipts")
    if before_path.read_bytes() != rc.historical_without_comparison(paths["historical"])["bytes"]:
        raise SystemExit(f"{fam}: before arm differs from the historical score")
    sb, sa = rc.load(before_path), rc.load(after_path)
    accounting = {r["at"]: r for r in pf["cells"]}
    cells, lines = [], []
    for pi, ref in enumerate(truth["pages"]):
        num = ref["page"]
        raw, page, window, words, membership = page_inputs(paths, num)
        bpage, apage = sb["pages"][pi], sa["pages"][pi]
        crit = {c["at"]: c for c in bpage["critical"]}
        in_cell_any = set()
        idx = 0
        for ti, table in enumerate(ref["tables"]):
            for ri, row in enumerate(table["rows"]):
                for ci, cell in enumerate(row):
                    b, a = bpage["cells"][idx], apage["cells"][idx]
                    idx += 1
                    region = cell["bbox"]
                    at = b["at"]
                    inter = [k for k, w in enumerate(words) if overlap(w["bbox"], region) > 0]
                    cent = [k for k, w in enumerate(words) if centred(w["bbox"], region)]
                    incell = [k for k, s in enumerate(page["spans"]) if scorer.in_cell(s["bbox"], region)]
                    in_cell_any |= set(incell)
                    order = sorted(cent, key=lambda k: (words[k]["line"], words[k]["bbox"][0]))
                    raw_join = " ".join(words[k]["text"] for k in order)
                    emitted, grid_cells = None, []
                    if b["reported_table_bbox"] is not None:
                        k = [k for k, t in enumerate(page["tables"]) if t["bbox"] == b["reported_table_bbox"]][0]
                        grid = page["tables"][k]["rows"]
                        emitted = grid[ri][ci] if ri < len(grid) and ci < len(grid[ri]) else None
                        grid_cells = [m for kk in cent for m in membership.get(kk, [])]
                    wanted = norm(cell["text"])
                    adapter_differs = emitted is not None and norm(raw_join) != norm(emitted)
                    stage = None
                    if not b["correct"]:
                        if wanted and not inter:
                            stage = "no_intersecting_word"
                        elif wanted and not cent:
                            stage = "off_centre_word"
                        elif norm(raw_join) != wanted:
                            stage = "winrt_text"
                        elif emitted is None or norm(emitted) != wanted:
                            stage = "adapter_grid"
                        else:
                            stage = "scorer_selection"
                    cells.append(dict(
                        at=at, expected=wanted, critical=bool(cell["critical"]), printed_empty=wanted == "",
                        before=dict(observed=b["observed"], correct=b["correct"], flagged=b["flagged"],
                                    mode="grid" if b["reported_table_bbox"] is not None else "span_fallback"),
                        after=dict(observed=a["observed"], correct=a["correct"], flagged=a["flagged"],
                                   mode="grid" if a["reported_table_bbox"] is not None else "span_fallback"),
                        klass=accounting[at]["klass"], intersecting_words=[words[k]["text"] for k in inter],
                        centred_words=[words[k]["text"] for k in order], scorer_in_cell_spans=incell,
                        raw_join=raw_join if cent else None, emitted=emitted, grid_membership=grid_cells,
                        adapter_differs=adapter_differs, earliest_stage=stage,
                        text_effect=text_effect(wanted, b["observed"]) if not b["correct"] else "none",
                        split_delta=split_count(wanted, b["observed"]) if not b["correct"] else 0,
                        char_ops=char_ops(wanted, b["observed"]) if not b["correct"] else [],
                        page_near_matches=near_matches(words, wanted) if stage == "no_intersecting_word" else None))
        # Lines: replicate the scorer's span-to-line assignment from stored spans.
        assigned = {}
        for k, s in enumerate(page["spans"]):
            if k in in_cell_any:
                continue
            elig = [j for j, ln in enumerate(ref["lines"]) if scorer.on_line(s["bbox"], ln["bbox"])]
            if elig:
                centre = lambda bx: (bx[1] + bx[3]) / 2
                j = min(elig, key=lambda j: abs(centre(ref["lines"][j]["bbox"]) - centre(s["bbox"])))
                assigned.setdefault(j, []).append(k)
        for li, line in enumerate(ref["lines"]):
            bl, al = bpage["lines"][li], apage["lines"][li]
            at = bl["at"]
            mine = assigned.get(li, [])
            joined = scorer.joined([page["spans"][k] for k in mine])[0]
            inter = [k for k, w in enumerate(words) if overlap(w["bbox"], line["bbox"]) > 0]
            unassigned = []
            for k in inter:
                if k in mine:
                    continue
                why = "captured_by_reference_cell" if k in in_cell_any else (
                    "assigned_to_other_line" if any(k in v for v in assigned.values()) else "not_on_line")
                unassigned.append(dict(span=k, text=words[k]["text"], reason=why))
            stray = [k for k in mine if k not in inter]
            overlap_join = scorer.joined([page["spans"][k] for k in inter])[0]
            assignment_differs = bool(unassigned or stray)
            stage = None
            if not bl["correct"]:
                if not inter and not mine:
                    stage = "no_intersecting_word"
                elif overlap_join is None or overlap_join != norm(line["text"]):
                    stage = "winrt_text"
                else:
                    stage = "scorer_assignment"
            ck = crit.get(at)
            winrt_lines = sorted({words[k]["line"] for k in mine})
            lines.append(dict(
                at=at, expected=line["text"], observed=bl["observed"], correct=bl["correct"],
                after_identical=bl == al, critical_token=line["critical"],
                critical_correct=ck["correct"] if ck else None, critical_flagged=ck["flagged"] if ck else None,
                assigned_spans=mine, reproduced_join_equals_scored=joined == bl["observed"],
                winrt_line_texts=[raw["reader_result"]["lines"][x]["text"] for x in winrt_lines],
                unassigned_overlapping=unassigned, assigned_not_overlapping=stray,
                overlapping_join=overlap_join, assignment_differs=assignment_differs, earliest_stage=stage,
                text_effect=text_effect(line["text"], bl["observed"]) if not bl["correct"] else "none",
                split_delta=split_count(line["text"], bl["observed"]) if not bl["correct"] else 0,
                char_ops=char_ops(line["text"], bl["observed"]) if not bl["correct"] else []))
    return dict(paired_hashes=hashes, cells=cells, lines=lines, tallies=tallies(cells, lines),
                edits_equal=[p["edit_distance"] for p in sb["pages"]] == [p["edit_distance"] for p in sa["pages"]],
                lines_equal=all(l["after_identical"] for l in lines),
                line_join_reproduced=all(l["reproduced_join_equals_scored"] for l in lines))


def tallies(cells, lines):
    wrong = [c for c in cells if not c["before"]["correct"]]
    bad = [l for l in lines if not l["correct"]]
    ops = Counter()
    for r in wrong + bad:
        for op in r["char_ops"]:
            ops[f"{op[0]}:{op[1]}->{op[2]}"] += 1
    crit_bad = [l for l in lines if l["critical_correct"] is False]
    return dict(
        cells=len(cells), cells_wrong_before=len(wrong), cells_wrong_after=sum(not c["after"]["correct"] for c in cells),
        cell_classes=dict(Counter(c["klass"] for c in cells)),
        printed_empty=dict(total=sum(c["printed_empty"] for c in cells),
                           before_empty_string=sum(c["printed_empty"] and c["before"]["observed"] == "" for c in cells),
                           after_none=sum(c["printed_empty"] and c["after"]["observed"] is None for c in cells),
                           losses=sum(c["printed_empty"] and c["klass"] == "loss" for c in cells)),
        expected_text_but_grid_empty=sum((not c["printed_empty"]) and c["before"]["observed"] == "" for c in cells),
        loss_not_printed_empty=sum(c["klass"] == "loss" and not c["printed_empty"] for c in cells),
        gains=sum(c["klass"] == "gain" for c in cells),
        changed_text_value=sum((c["before"]["observed"] or "") != (c["after"]["observed"] or "") for c in cells),
        cell_stage=dict(Counter(c["earliest_stage"] for c in wrong)),
        cell_stage_critical=dict(Counter(c["earliest_stage"] for c in wrong if c["critical"])),
        cells_adapter_differs=sum(c["adapter_differs"] for c in cells),
        cell_text_effect=dict(Counter(c["text_effect"] for c in wrong)),
        cell_text_effect_critical=dict(Counter(c["text_effect"] for c in wrong if c["critical"])),
        lines=len(lines), lines_wrong=len(bad),
        line_stage=dict(Counter(l["earliest_stage"] for l in bad)),
        lines_assignment_differs=sum(l["assignment_differs"] for l in lines),
        line_text_effect=dict(Counter(l["text_effect"] for l in bad)),
        critical_lines=sum(bool(l["critical_token"]) for l in lines),
        critical_line_errors=len(crit_bad),
        critical_line_errors_on_correct_lines=sum(l["correct"] for l in crit_bad),
        critical_line_error_effect=dict(Counter(l["text_effect"] for l in crit_bad)),
        flagged_any=sum(c["before"]["flagged"] or c["after"]["flagged"] for c in cells) +
                    sum(bool(l["critical_flagged"]) for l in lines),
        char_ops=dict(ops.most_common()))


def main():
    global norm
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(rc.DEFAULT_DATA))
    ap.add_argument("--paired-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = rc.fresh_dir(args.out)
    env = rc.environment()
    env["attribution_sha256"] = rc.sha256(Path(__file__).read_bytes())
    scorer = rc.load_scorer(Path(args.data) / "inputs" / "control" / "score.py")
    norm = scorer.norm
    result = dict(kind="WP-0018/003 reviewer attribution", environment=env, paired_dir=str(args.paired_dir),
                  paired_json_sha256=rc.sha256((Path(args.paired_dir) / "paired.json").read_bytes()))
    for fam in rc.FAMILIES:
        result[fam] = attribute_family(fam, args.data, args.paired_dir, scorer)
    result["ended_utc"] = rc.utc()
    digest = rc.dump(out / "attribution.json", result)
    print(json.dumps(dict(out=str(out / "attribution.json"), sha256=digest,
                          tallies={f: result[f]["tallies"] for f in rc.FAMILIES}), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
