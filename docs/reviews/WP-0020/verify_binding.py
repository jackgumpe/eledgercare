"""Rebind every selected observation independently and rebuild complete emitted predictions."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys


def get(path):
    return json.loads(path.read_bytes())


def idx(row):
    p = f"page/{row['page']}/"
    if row["kind"] == "line":
        return p + f"raw_line/{row['raw_line']}"
    return p + f"table/{row['table']}/row/{row['row']}/col/{row['col']}"


def area(box):
    return max(0,box[2]-box[0])*max(0,box[3]-box[1])


def intersect(b, c):
    return area([max(b[0],c[0]),max(b[1],c[1]),min(b[2],c[2]),min(b[3],c[3])])


def iou(b, c):
    common = intersect(b,c)
    return common/(area(b)+area(c)-common)


def good(box):
    return len(box) == 4 and all(x >= 0 for x in box) and area(box) > 0


def bounding(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def within(box, support):
    x,y=(box[0]+box[2])/2,(box[1]+box[3])/2
    return support[0] <= x < support[2] and support[1] <= y < support[3]


def layout(page, grouping):
    spans = page["spans"]
    outlines = [t["bbox"] for t in page["tables"]]
    lines, start = {}, 0
    for number, length in enumerate(grouping["line_word_counts"], 1):
        members = [i for i in range(start,start+length) if not any(within(spans[i]["bbox"],t) for t in outlines)]
        if members:
            lines[number] = (bounding([spans[i]["bbox"] for i in members]), " ".join(spans[i]["text"] for i in members))
        start += length
    return lines


def candidates(row, page, native, lines):
    if row["kind"] == "line":
        w = {n: b for n,(b,_) in lines.items()}
        n = {i:s["bbox"] for i,s in enumerate(native["spans"]) if good(s["bbox"]) and not any(
            good(t["bbox"]) and intersect(t["bbox"],s["bbox"])/area(s["bbox"]) >= .5 for t in native["tables"])}
        key = row["raw_line"]
    else:
        w = {i+1:t["bbox"] for i,t in enumerate(page["tables"])}
        n = {i:t["bbox"] for i,t in enumerate(native["tables"]) if good(t["bbox"])}
        key = row["table"]
    graph = [(i,j) for i, a in w.items() for j, b in n.items() if iou(a,b) >= .5]
    matching = [j for i,j in graph if i == key]
    if not matching:
        return "no_overlapping_region", None, matching, None
    if len(matching) > 1:
        return "multiple_native_regions", None, matching, None
    j = matching[0]
    if sum(b == j for a,b in graph) > 1:
        return "native_region_matches_multiple_windows_regions", None, matching, None
    if row["kind"] == "line":
        value = native["spans"][j]["text"]
        if not isinstance(value,str) or not value.strip() or len(value.splitlines()) != 1:
            return "no_literal_single_line", None, matching, j
        return "unique_whole_prose_line", value, matching, j
    wt = page["tables"][key-1]["rows"]
    nt = native["tables"][j]["rows"]
    if [len(r) for r in wt] != [len(r) for r in nt]:
        return "grid_shape_mismatch", None, matching, j
    value = nt[row["row"]-1][row["col"]-1]
    if not isinstance(value,str):
        return "no_literal_cell", None, matching, j
    return "same_shape_positional_cell",value,matching,j


def verify(family, independent, windows, native, author_manifest, author_decisions, pred):
    expected = get(independent)
    src = get(windows/family/"prediction.json")
    geometry = get(windows/family/"layout.json")["pages"]
    manifest = get(author_manifest)
    decisions = get(author_decisions)
    proposals = manifest["fields"]
    assert manifest["family"] == decisions["family"] == family
    assert manifest["source_sha256"] == expected["source_sha256"]
    assert manifest["input_sha256"] == expected["inputs"]
    assert manifest["selected_windows"] == list(map(int, expected["windows"]))
    assert decisions["manifest_sha256"] == hashlib.sha256(author_manifest.read_bytes()).hexdigest()
    ensure = {idx(row):row for row in expected["candidates"]}
    assert set(ensure) == {x["id"] for x in proposals} and len(ensure) == len(proposals)
    assert [p["id"] for p in proposals] == [d["id"] for d in decisions["fields"]]
    by_page = defaultdict(list)
    for p,d in zip(proposals, decisions["fields"]):
        by_page[p["page"]].append((p,d))
    out = deepcopy(src)
    counts = Counter()
    for original, page, g in zip(src["pages"], out["pages"], geometry, strict=True):
        n = page["page"]
        original_lines = layout(original,g)
        lines = dict(original_lines)
        edits, appended = {}, []
        if n not in by_page:
            continue
        native_path = native/family/f"page-{n:03d}.json"
        assert hashlib.sha256(native_path.read_bytes()).hexdigest() == decisions["native_page_sha256"][native_path.name]
        nn = get(native_path)
        assert nn["page"] == n and nn["source_sha256"] == src["source_sha256"]
        for candidate,dec in by_page[n]:
            row = ensure[candidate["id"]]
            assert row["page"] == n and row["window"] == candidate["window_start"] and row["bbox"] == candidate["bbox"]
            cell = row["kind"] == "cell"
            assert candidate["kind"] == ("cell" if cell else "prose")
            assert row["value"] == candidate["windows_value"] and candidate["label_text"] == row.get("label",row["value"])
            assert candidate["reason"] == ("label_in_detected_header" if cell else "label_in_non_table_line")
            if cell:
                assert [candidate["table_index"]+1,candidate["row_index"]+1,candidate["col_index"]+1] == [row[k] for k in ("table","row","col")]
                members = [i for i,s in enumerate(original["spans"]) if within(s["bbox"],row["bbox"])]
            else:
                assert candidate["line_index"]+1 == row["raw_line"]
                members = row["spans"]
            assert set(candidate["span_indices"]) == set(members)
            reason, value, matches, evidence = candidates(row,original,nn,original_lines)
            witness = dec["witness"]
            assert matches == witness["candidate_table_indices" if cell else "candidate_span_indices"]
            if evidence is not None:
                assert witness["table_index" if cell else "span_index"] == evidence
                assert witness["native_bbox"] == nn["tables" if cell else "spans"][evidence]["bbox"]
            old = row["value"]
            emitted = value if value is not None else old
            status = "substituted" if value is not None else "unresolved"
            assert (reason,value,emitted,status,emitted!=old) == (dec["reason"],dec["native_value"],dec["emitted_value"],dec["status"],dec["changed"])
            counts[reason] += 1
            if emitted == old:
                continue
            if cell:
                page["tables"][row["table"]-1]["rows"][row["row"]-1][row["col"]-1] = emitted
            else:
                lines[row["raw_line"]] = (row["bbox"], emitted)
            replacement = dict(bbox=bounding([original["spans"][i]["bbox"] for i in members]) if members else row["bbox"],
                               text=emitted,flagged=any(original["spans"][i]["flagged"] for i in members))
            for i in members:
                assert i not in edits
                edits[i]=[]
            if emitted and members:
                edits[min(members)] = [replacement]
            elif emitted:
                appended.append(replacement)
        page["spans"] = [s for i,old in enumerate(original["spans"]) for s in edits.get(i,[old])] + appended
        chunks = [(b[1],b[0],txt) for b,txt in lines.values()]
        chunks.extend((t["bbox"][1],t["bbox"][0]," ".join(v for row in t["rows"] for v in row)) for t in page["tables"])
        page["text"] = " ".join(" ".join(c[2] for c in sorted(chunks)).split())
    assert out == get(pred)
    print(json.dumps(dict(family=family, matched=len(ensure), bindings=dict(counts), full_prediction_matches=True)))


if __name__ == "__main__":
    verify(sys.argv[1], *map(Path,sys.argv[2:]))
