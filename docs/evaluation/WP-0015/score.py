"""CPU common evaluator over a single packet. Predictions never receive truth at inference."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
import unicodedata


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def norm(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


def distance(a, b):
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    last = list(range(len(b)+1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(last[j]+1, cur[-1]+1, last[j-1]+(ca != cb)))
        last = cur
    return last[-1]


def valid_box(b, width, height):
    return (isinstance(b, list) and len(b) == 4 and
            all(type(v) in (float, int) and math.isfinite(v) for v in b) and
            0 <= b[0] < b[2] <= width and 0 <= b[1] < b[3] <= height)


def iou(a, b):
    overlap = max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))
    area = lambda r: (r[2]-r[0]) * (r[3]-r[1])
    return overlap / (area(a)+area(b)-overlap)


def in_cell(box, region):
    x, y = (box[0]+box[2])/2, (box[1]+box[3])/2
    return (region[0] <= x < region[2] and region[1] <= y < region[3] and
            box[0] >= region[0]-2 and box[2] <= region[2]+2 and
            box[1] >= region[1]-2 and box[3] <= region[3]+2)


def on_line(box, region):
    y = (box[1]+box[3])/2
    overlap = min(box[2], region[2])-max(box[0], region[0])
    return (region[1]-3 <= y <= region[3]+3 and
            box[3]-box[1] <= 2.5*max(4, region[3]-region[1]) and
            overlap >= 0.5*min(box[2]-box[0], region[2]-region[0]))


def value(entry):
    if isinstance(entry, str):
        return norm(entry), False
    if not isinstance(entry, dict) or not isinstance(entry.get("text"), str):
        raise ValueError("span/cell requires a text string")
    flag = entry.get("flagged", False)
    if type(flag) is not bool:
        raise ValueError("flagged requires a JSON boolean")
    return norm(entry["text"]), flag


def joined(spans):
    if not spans:
        return None, False
    spans = sorted(spans, key=lambda s: (s["bbox"][0], s["bbox"][1]))
    values = [value(s) for s in spans]
    return norm(" ".join(v for v, _ in values)), any(flag for _, flag in values)


def layout(ref, page, sha):
    num, width, height = ref["page"], ref["width"], ref["height"]
    faults, valid_spans, valid_tables = [], [], []
    extra_cells = 0

    def source_ok(obj, location):
        if obj.get("source_sha256", sha) != sha or obj.get("page", num) != num:
            faults.append(dict(issue="wrong_source", at=location))
            return False
        return True

    for kind, target in (("spans", valid_spans), ("tables", valid_tables)):
        nodes = page.get(kind, [])
        if not isinstance(nodes, list):
            raise ValueError(f"{kind} must be an array")
        for ix, obj in enumerate(nodes):
            local = f"{kind}/{ix}"
            if not isinstance(obj, dict):
                raise ValueError(f"invalid {local}")
            if kind == "tables":
                rows = obj.get("rows")
                if not isinstance(rows, list) or not all(isinstance(row, list) for row in rows):
                    raise ValueError("table rows must be arrays")
                for ri, row in enumerate(rows):
                    for ci, entry in enumerate(row):
                        value(entry)
                        if isinstance(entry, dict):
                            source_ok(entry, f"{local}/{ri}/{ci}")
            else:
                value(obj)
            source_matches = source_ok(obj, local)
            box_matches = valid_box(obj.get("bbox"), width, height)
            if not box_matches:
                faults.append(dict(issue="invalid_geometry", at=local))
            if source_matches and box_matches:
                target.append(obj)
            elif kind == "tables":
                extra_cells += sum(map(len, obj["rows"]))

    cell_spans, line_spans = defaultdict(list), defaultdict(list)
    for s in valid_spans:
        assigned = False
        for ti, table in enumerate(ref["tables"]):
            for ri, row in enumerate(table["rows"]):
                for ci, cell in enumerate(row):
                    if in_cell(s["bbox"], cell["bbox"]):
                        cell_spans[ti, ri, ci].append(s)
                        assigned = True
                        break
                if assigned:
                    break
            if assigned:
                break
        if not assigned:
            eligible = [(i, ln) for i, ln in enumerate(ref["lines"]) if on_line(s["bbox"], ln["bbox"])]
            if eligible:
                center = lambda box: (box[1]+box[3])/2
                i, _ = min(eligible, key=lambda it: abs(center(it[1]["bbox"])-center(s["bbox"])))
                line_spans[i].append(s)

    pairs = sorted(((-iou(t["bbox"], p["bbox"]), ti, pi) for ti, t in enumerate(ref["tables"])
                    for pi, p in enumerate(valid_tables)), key=lambda item: item)
    matched, used = {}, set()
    for neg_iou, ti, pi in pairs:
        if -neg_iou >= 0.5 and ti not in matched and pi not in used:
            matched[ti] = valid_tables[pi]
            used.add(pi)
    extra_cells += sum(sum(map(len, p["rows"])) for pi, p in enumerate(valid_tables) if pi not in used)

    cells, critical, lines = [], [], []
    for li, line in enumerate(ref["lines"]):
        actual, flagged = joined(line_spans[li])
        path = f"page/{num}/line/{li+1}"
        lines.append(dict(at=path, expected=line["text"], observed=actual, correct=actual == norm(line["text"]),
                          reference_bbox=line["bbox"], reported_span_boxes=[s["bbox"] for s in line_spans[li]]))
        wanted = line["critical"]
        if wanted:
            # A critical token must stand on its own on the correct source line.
            pattern = r"(?<![\w.,+-])" + re.escape(wanted) + r"(?![\w+-]|[.,]\d)"
            numbered = lambda s: [t for t in re.findall(r"[+-]?[\w]+(?:[.,-][\w]+)*", s) if any(c.isdigit() for c in t)]
            ok = (actual is not None and re.search(pattern, actual) is not None and
                  numbered(line["text"]) == numbered(actual))
            critical.append(dict(at=path, expected=wanted, observed=actual, correct=ok, flagged=flagged))

    for ti, table in enumerate(ref["tables"]):
        table_prediction = matched.get(ti)
        grid = table_prediction["rows"] if table_prediction is not None else None
        if grid is not None:
            for ri, row in enumerate(grid):
                wanted_length = len(table["rows"][ri]) if ri < len(table["rows"]) else 0
                extra_cells += max(0, len(row)-wanted_length)
        for ri, row in enumerate(table["rows"]):
            for ci, cell in enumerate(row):
                if grid is None:
                    actual, flagged = joined(cell_spans[ti, ri, ci])
                elif ri < len(grid) and ci < len(grid[ri]):
                    item = grid[ri][ci]
                    if isinstance(item, dict) and (item.get("source_sha256", sha) != sha or item.get("page", num) != num):
                        actual, flagged = None, False
                    else:
                        actual, flagged = value(item)
                else:
                    actual, flagged = None, False
                wanted = norm(cell["text"])
                path = f"page/{num}/table/{ti+1}/row/{ri+1}/col/{ci+1}"
                detail = dict(at=path, expected=wanted, observed=actual, correct=actual == wanted, flagged=flagged,
                              reference_bbox=cell["bbox"],
                              reported_table_bbox=table_prediction["bbox"] if table_prediction is not None else None,
                              reported_span_boxes=[s["bbox"] for s in cell_spans[ti, ri, ci]] if grid is None else [])
                cells.append(detail)
                if cell["critical"]:
                    critical.append(detail)
    return dict(cells=cells, lines=lines, critical=critical, extra_cells=extra_cells, faults=faults)


def score(truth, prediction):
    refs = truth["pages"]
    sha = truth["source_sha256"]
    pages = prediction["pages"]
    if not isinstance(pages, list):
        raise ValueError("pages must be an array")
    faults, records, extras = [], [], []
    if prediction.get("source_sha256") != sha:
        faults.append(dict(issue="wrong_source", at="document"))
    expected = list(range(1, len(refs)+1))
    assert [r["page"] for r in refs] == expected
    order, by_page = [], {}
    for ix, page in enumerate(pages):
        num = page.get("page")
        if type(num) is not int or not isinstance(page.get("text"), str):
            raise ValueError("page requires integral page ordinal and text string")
        order.append(num)
        if page.get("source_sha256") != sha or prediction.get("source_sha256") != sha:
            why = "wrong_source"
        elif num not in expected:
            why = "out_of_range"
        elif num in by_page:
            why = "duplicate_page"
        else:
            by_page[num] = page
            continue
        faults.append(dict(issue=why, at=f"pages/{ix}", page=num))
        extras.append(dict(page=num, reason=why, insertion_chars=len(norm(page["text"])),
                           extra_cells=sum(len(row) for table in page.get("tables", []) for row in table["rows"])))
    if order != expected:
        faults.append(dict(issue="page_sequence", observed=order, expected=expected))
    for ref in refs:
        num = ref["page"]
        page = by_page.get(num)
        if page is None:
            faults.append(dict(issue="missing_page", page=num))
            page = dict(state="missing", text="")
        elif page.get("state") != "complete":
            faults.append(dict(issue="incomplete_page", state=page.get("state"), page=num))
        target, actual = norm(ref["text"]), norm(page["text"])
        if target and not actual:
            faults.append(dict(issue="unexpected_blank", page=num))
        if not target and actual:
            faults.append(dict(issue="ink_on_blank", page=num))
        details = layout(ref, page, sha)
        faults.extend(dict(f, page=num) for f in details.pop("faults"))
        records.append(dict(page=num, state=page.get("state"), reference_chars=len(target),
                            edit_distance=distance(target, actual), **details))
    critical = [c for p in records for c in p["critical"]]
    cells = [c for p in records for c in p["cells"]]
    lines = [ln for p in records for ln in p["lines"]]
    edits = sum(p["edit_distance"] for p in records)+sum(e["insertion_chars"] for e in extras)
    chars = sum(p["reference_chars"] for p in records)
    extra_cells = sum(p["extra_cells"] for p in records)+sum(e["extra_cells"] for e in extras)
    correct = sum(c["correct"] for c in cells)
    counts = Counter(f["issue"] for f in faults)
    blocking = set(counts)-{"ink_on_blank", "invalid_geometry"}
    return dict(family=truth["family"], source_sha256=sha, packet_complete=not blocking,
                expected_pages=len(refs), output_pages=len(pages), observed_order=order, faults=faults,
                counts=dict(edits=edits, reference_chars=chars, cer=edits/chars if chars else None,
                            correct_cells=correct, reference_cells=len(cells), extra_cells=extra_cells,
                            cell_accuracy=correct/(len(cells)+extra_cells) if cells else None,
                            correct_lines=sum(l["correct"] for l in lines), reference_lines=len(lines),
                            critical_values=len(critical), critical_errors=sum(not c["correct"] for c in critical),
                            unflagged_critical_errors=sum(not c["correct"] and not c["flagged"] for c in critical),
                            flagged_critical=sum(c["flagged"] for c in critical), wrong_source=counts["wrong_source"]),
                extra_page_outputs=extras, pages=records)


def compare(base, trial):
    if (base["source_sha256"], base["family"]) != (trial["source_sha256"], trial["family"]):
        raise ValueError("unmatched input")
    delta = {}
    for key in ("cer", "cell_accuracy"):
        a, b = base["counts"][key], trial["counts"][key]
        if (a is None) != (b is None):
            raise ValueError("unmatched applicable metric")
        delta[key] = b-a if a is not None else None
    previous = {c["at"]: c for p in base["pages"] for c in p["critical"]}
    errors = [c for p in trial["pages"] for c in p["critical"] if not c["correct"]]
    novel = [c for c in errors if previous[c["at"]]["correct"] or
             (previous[c["at"]]["observed"], previous[c["at"]]["flagged"]) != (c["observed"], c["flagged"])]
    cer_ok = delta["cer"] is None or delta["cer"] <= 0.01+1e-12
    table_ok = delta["cell_accuracy"] is None or delta["cell_accuracy"] >= -0.02-1e-12
    def foreign(result):
        return [f for f in result["faults"] if f["issue"] == "wrong_source"]
    prior = foreign(base)
    return dict(family=trial["family"], source_sha256=trial["source_sha256"], delta=delta,
                new_wrong_source_links=[f for f in foreign(trial) if f not in prior],
                complete_matched_pair=base["packet_complete"] and trial["packet_complete"],
                inside_quality_budget=cer_ok and table_ok, new_or_changed_critical_errors=novel,
                unattended_quality_gate=(trial["packet_complete"] and trial["counts"]["wrong_source"] == 0 and
                                         trial["counts"]["unflagged_critical_errors"] == 0))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("truth")
    p.add_argument("prediction")
    p.add_argument("--baseline", help="matched control prediction for deltas")
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    truth = read(args.truth)
    result = score(truth, read(args.prediction))
    if args.baseline:
        baseline = score(truth, read(args.baseline))
        result["comparison"] = compare(baseline, result)
    output = json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False)+"\n"
    if args.out:
        args.out.write_bytes(output.encode())
    else:
        print(output, end="")
