"""Score the blind predictions by physical source and audit the live state of the fixed reader.

This independent review program accepts the released key only after both predictions freeze.
It contains no OCR, grid extraction, document generator or production import.
"""
import argparse
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
import sys

READER_SHA = "613a5ff92e9dd6783b8950529fbda76f6c21e9d3"
READER_PATH = "docs/research/WP-0021/read_scope.py"


def load(path):
    return json.loads(path.read_bytes())


def save(path, data):
    path.write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode())


def size(box):
    return (box[2] - box[0]) * (box[3] - box[1])


def overlap(a, b):
    w = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    h = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return w * h


def center_inside(a, b):
    x, y = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
    return b[0] <= x < b[2] and b[1] <= y < b[3]


def located(box, region):
    return center_inside(box, region) and overlap(box, region) / size(box) >= .5


def row_contains(word, target):
    return any(center_inside(word["bbox"], b) for b in [target["row_box"], *target["note_boxes"]])


def side(word, target):
    box = word["bbox"]
    if any(located(box, b) for b in target["note_boxes"]):
        return "note"
    if located(box, target["amount_box"]):
        if any(overlap(box, b) > 0 for b in target["note_boxes"]):
            return "straddles-region"
        return "amount"
    return "other"


def import_reader(source):
    spec = importlib.util.spec_from_file_location("wp22_frozen_reader", source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def execute(reader, document):
    """At entry to each line, snapshot the prior event's exit and the new event's entry."""
    book = {}
    pending = None

    def trace(frame, event, _):
        nonlocal pending
        if frame.f_code is not reader.read.__code__:
            return None
        if event == "return" or (event == "line" and frame.f_lineno == 122):
            ctx = frame.f_locals
            frames = [asdict(item) for item in ctx["frames"]]
            if pending is not None:
                book[pending]["after"] = frames
            if event != "return":
                pending = (ctx["page_number"], ctx["line_no"])
                book[pending] = {"before": frames}
        return trace

    sys.settrace(trace)
    try:
        result = reader.read(document, "grid-words")
    finally:
        sys.settrace(None)
    assert {k for k, record in book.items() if "after" in record} == {
        (p["page"], i) for p in document["pages"] for i in range(1, len(p["lines"]) + 1)}
    return json.loads(json.dumps(result)), book


def index_document(doc, predictions):
    source, lines = {}, {}
    for page in doc["pages"]:
        for number, line in enumerate(page["lines"], 1):
            pair = page["page"], number
            lines[pair] = line["words"]
            for word in line["words"]:
                assert word["ref"] not in source and size(word["bbox"]) > 0
                source[word["ref"]] = (pair, word)
    outputs = {}
    for row in predictions["rows"]:
        pair = row["page"], row["line"]
        assert pair not in outputs
        outputs[pair] = row
        words = lines[pair]
        assert row["words"] == [{"literal": w["text"], "word_ref": w["ref"]} for w in words]
        assert (row["literal"], row["word_ref"]) == (words[-1]["text"], words[-1]["ref"])
        assert row["flagged"] is (row["scope"] is None)
        for key in ("property", "unit"):
            refs = row[key + "_refs"]
            label = row[key + "_label_ref"]
            assert row[key] == " ".join(source[r][1]["text"] for r in refs)
            if label:
                assert source[label][1]["text"] == key.title() + ":"
                assert all(source[r][0] == source[label][0] for r in refs)
    return source, lines, outputs


def binding(target, row, source):
    expected = {"scope": row["scope"] == target["scope"], "column_role": row["column_role"] == "Amount"}
    for name, key in [("heading", "heading_refs"), ("property_region", "property_refs"), ("unit_region", "unit_refs")]:
        region = target[name]
        expected[name] = bool(row[key]) and all(
            source[ref][0][0] == region["page"] and located(source[ref][1]["bbox"], region["bbox"])
            for ref in row[key])
    # The actual frozen reader stores the Amount header as the final pointer in each schema.
    expected["header_role_pointer"] = bool(row["header_refs"]) and source[row["header_refs"][-1]][1]["text"] == "Amount"
    return expected


def evaluate_target(target, lines, outputs, source, stack, siblings):
    page, rowbox = target["page"], target["row_box"]
    touched = [(pair, words) for pair, words in lines.items() if pair[0] == page and any(
        overlap(w["bbox"], b) > 0 for w in words for b in [rowbox, *target["note_boxes"]])]
    events, trace = [], []
    for pair, words in touched:
        row = outputs.get(pair)
        terminal = words[-1]
        in_row = row_contains(terminal, target)
        event = None
        if row and in_row:
            where = side(terminal, target)
            bound = binding(target, row, source)
            mixed = any(row_contains(w, other) for w in words for other in siblings
                        if other["page"] == page and other["id"] != target["id"])
            header = target["amount_header"]
            header_ref = row["header_refs"][-1] if row["header_refs"] else None
            header_matched = bool(header_ref and source[header_ref][0][0] == header["page"]
                                  and located(source[header_ref][1]["bbox"], header["bbox"]))
            event = {"line": pair[1], "source": where, "ref": row["word_ref"], "literal": row["literal"],
                     "flag": row["flagged"], "binding": bound, "cross_row": mixed,
                     "expected_amount_header_pointer": header_matched, "reason": row["reason"]}
            events.append(event)
        margins = []
        for frame in stack[pair]["before"]:
            margins.append({"scope": frame["scope"], "heading_refs": frame["heading_refs"],
                            "candidate_minus_amount_header_x0": terminal["bbox"][0] - frame["anchors"][-1]
                            if frame["anchors"] else None})
        trace.append({"line": pair[1], "words": words, "candidate": event, "frozen_output": row,
                      "header_deltas_pt": margins, **stack[pair]})
    amount_words = [w["ref"] for _, words in touched for w in words if side(w, target) == "amount"]
    amount_intersections = [w["ref"] for _, words in touched for w in words if overlap(w["bbox"], target["amount_box"]) > 0]
    flags = [e for e in events if e["flag"]]
    posts = [e for e in events if not e["flag"]]
    good = [e for e in posts if e["source"] == "amount" and all(e["binding"].values()) and not e["cross_row"]]
    amount_flags = [e for e in flags if e["source"] == "amount"]
    kind = target["kind"]
    if kind == "blank":
        status = "silent-wrong" if posts else "safe-withholding"
    elif kind == "ambiguous":
        status = "silent-wrong" if posts else ("ambiguous-abstention" if amount_flags else
                                                  "incidental-flag" if flags else "missing-output")
    elif len(posts) == len(good) == 1:
        status = "owned"
    elif posts:
        status = "silent-wrong"
    else:
        status = "unambiguous-abstention" if amount_flags else "incidental-flag" if flags else "missing-output"
    if kind != "blank" and not amount_intersections and not posts:
        status = "no-intersecting-source"
    return {"status": status, "pass": status in ("owned", "safe-withholding", "ambiguous-abstention"),
            "amount_words": amount_words, "amount_intersections": amount_intersections,
            "transcription": (good[0]["literal"] == target["literal"]) if status == "owned" else None,
            "events": events, "trace": trace, "missing_amount_header_pointer": any(not e["expected_amount_header_pointer"] for e in good),
            "false_posts": len(posts) - (min(len(good), 1) if kind == "value" else 0)}


def run(args):
    reader = import_reader(args.source)
    assert reader.WORD_TOLERANCE_PT == 3.0 and reader.GRID_TOLERANCE_PT == 2.0
    targets = load(args.truth)["targets"]
    case_ids = [t["id"] for t in targets]
    assert len(set(case_ids)) == len(case_ids)
    grouped = defaultdict(list)
    for target in targets:
        grouped[target["doc"]].append(target)
    args.out.mkdir(parents=True, exist_ok=True)
    rows, summaries, outside, matrices = {}, {}, {}, defaultdict(Counter)
    for arm in ("R", "W"):
        counts = Counter()
        outside[arm] = []
        for docid, cases in grouped.items():
            doc = load(args.evidence / "observations" / arm / (docid + ".json"))
            archived = load(args.evidence / "predictions" / arm / (docid + ".json"))
            replay, stack = execute(reader, doc)
            assert archived == replay, (arm, docid, "frozen output mismatch")
            source, lines, outputs = index_document(doc, replay)
            for pair, output in outputs.items():
                assert output["stack_before"] == [f["scope"] for f in stack[pair]["before"]]
                assert output["stack_after"] == [f["scope"] for f in stack[pair]["after"]]
            seen = set()
            for target in cases:
                result = evaluate_target(target, lines, outputs, source, stack, cases)
                counts[result["status"]] += 1
                counts["transcription-mismatch"] += result["transcription"] is False
                counts["false-posts"] += result["false_posts"]
                counts["owned-missing-intended-amount-header"] += result["missing_amount_header_pointer"]
                kind = target["kind"]
                counts["rows-" + kind] += 1
                flags = [e for e in result["events"] if e["flag"]]
                counts["flag-rows-" + kind] += bool(flags)
                counts["amount-flag-rows-" + kind] += any(e["source"] == "amount" for e in flags)
                counts["flag-events"] += len(flags)
                counts["no-cell-word-" + kind] += not result["amount_intersections"]
                counts["positive-blank-representation"] += 0  # No blank-output representation in fixed reader.
                for event in result["events"]:
                    p = (target["page"], event["line"])
                    assert p not in seen, ("claimed by two target rows", docid, p)
                    seen.add(p)
                    if not event["flag"] and event["source"] == "note":
                        counts["margin-post-opposite-" + target["kind"]] += 1
                rows.setdefault(target["id"], {"target": target})[arm] = result
            outside[arm].extend({"doc": docid, **row} for pair, row in outputs.items()
                                if pair not in seen and not row["flagged"])
            counts["outside-flags"] += sum(row["flagged"] for pair, row in outputs.items() if pair not in seen)
        summaries[arm] = dict(counts)
    for target_id, row in rows.items():
        pair = "".join("P" if row[a]["pass"] else "F" for a in ("R", "W"))
        group = "setup" if "setup" in row["target"]["tags"] else "non-setup"
        matrices["all"][pair] += 1
        matrices[group][pair] += 1
        save(args.out / (target_id + ".json"), row)
    result = {"reader_revision": READER_SHA, "reader_file_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
              "summary": summaries, "unmatched_unflagged_posts": outside,
              "matrix": {k: {cell: v[cell] for cell in ("PP", "PF", "FP", "FF")} for k, v in matrices.items()}}
    save(args.out / "review.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for field in ("source", "truth", "evidence", "out"):
        cli.add_argument("--" + field, type=Path, required=True)
    run(cli.parse_args())

