"""Replay the fixed identifier-label rule using archived application observations."""
import argparse
from bisect import bisect_right
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re

# Exact LABELS and label from d62a96f8145345ce4c43544850d20fce13659879 policy.py.
LABELS = {"id", "identifier", "code", "docket", "serial", "tag", "ref", "reference",
          "asset", "batch", "lot", "inspection"}


def label(text):
    return bool(LABELS.intersection(re.findall(r"[a-z]+", text.lower())))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(obj):
    return json.dumps(obj, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode()


def publish(path, obj):
    data = encode(obj) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as target:
        target.write(data)
    return digest(data)


def valid_box(box):
    return (isinstance(box, list) and len(box) == 4
            and all(type(v) in (int, float) and math.isfinite(v) for v in box)
            and 0 <= box[0] < box[2] and 0 <= box[1] < box[3])


def union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def area(box):
    return (box[2] - box[0]) * (box[3] - box[1])


def overlap(a, b):
    return max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))


def eligible(a, b):
    shared = overlap(a, b)
    return 2 * shared >= area(a) + area(b) - shared  # IoU >= 1/2


def text_of(entry):
    return entry if isinstance(entry, str) else entry["text"]


def flat(text):
    return " ".join(text.split())


def page_text(page, lines):
    chunks = [(t["bbox"][1], t["bbox"][0], " ".join(text_of(v) for row in t["rows"] for v in row))
              for t in page["tables"]]
    chunks.extend((line["bbox"][1], line["bbox"][0], line["text"]) for line in lines.values())
    return flat(" ".join(text for y, x, text in sorted(chunks)))


def inspect_page(page, layout):
    """Recover original Windows groups; check every span, cell and page-text reconstruction."""
    spans, grids = page["spans"], layout["rule_tables"]
    require(page["page"] == layout["page"], "layout page identity")
    require(all(valid_box(s["bbox"]) for s in spans), "Windows span geometry")
    sequence = [[s["text"], s["bbox"]] for s in spans]
    require(digest(encode(sequence)) == layout["span_sha256"], "raw/predicted Windows span sequence")
    counts = layout["line_word_counts"]
    require(all(type(n) is int and n >= 0 for n in counts) and sum(counts) == len(spans), "line word counts")
    require(len(grids) == len(page["tables"]), "grid count")
    for g, t in zip(grids, page["tables"]):
        xs, ys = g["xs"], g["ys"]
        for axis in (xs, ys):
            require(len(axis) >= 2 and all(a < b for a, b in zip(axis, axis[1:])), "grid edges")
        require(t["bbox"] == [xs[0], ys[0], xs[-1], ys[-1]] and len(t["rows"]) == len(ys)-1
                and all(len(row) == len(xs)-1 for row in t["rows"]), "Windows grid geometry")
    cell_members, line_members = defaultdict(list), defaultdict(list)
    index = 0
    for li, count in enumerate(counts):
        for wi in range(index, index + count):
            b = spans[wi]["bbox"]
            x, y = (b[0]+b[2])/2, (b[1]+b[3])/2
            owners = []
            for ti, g in enumerate(grids):
                xs, ys = g["xs"], g["ys"]
                if xs[0] <= x < xs[-1] and ys[0] <= y < ys[-1]:
                    owners.append((ti, bisect_right(ys, y)-1, bisect_right(xs, x)-1))
            require(len(owners) <= 1, "overlapping Windows grids with shared word")
            if owners:
                cell_members[owners[0]].append((li, wi))
            else:
                line_members[li].append(wi)
        index += count

    cells = {}
    for ti, t in enumerate(page["tables"]):
        xs, ys = grids[ti]["xs"], grids[ti]["ys"]
        for ri, row in enumerate(t["rows"]):
            for ci, entry in enumerate(row):
                key = (ti, ri, ci)
                ordered = sorted(cell_members[key], key=lambda a: (a[0], spans[a[1]]["bbox"][0]))
                ids = [wi for _, wi in ordered]
                require(" ".join(spans[i]["text"] for i in ids) == text_of(entry), "Windows grid/word value")
                cells[key] = dict(bbox=[xs[ci], ys[ri], xs[ci+1], ys[ri+1]], span_indices=ids)
    lines = {li: dict(bbox=union([spans[i]["bbox"] for i in ids]), span_indices=ids,
                      text=" ".join(spans[i]["text"] for i in ids)) for li, ids in line_members.items()}
    require(page["text"] == page_text(page, lines), "Windows page-text reconstruction")
    return cells, lines


def read_windows(root, family):
    folder = root / family
    inputs = {n: (folder/n).read_bytes() for n in ("prediction.json", "windows.json", "layout.json")}
    p, w, layout = [json.loads(data) for data in inputs.values()]
    pages = [q["page"] for q in p["pages"]]
    require(pages == list(range(1, len(pages)+1)) and len(pages) > 0, "page sequence")
    require([q["page"] for q in layout["pages"]] == pages, "layout sequence")
    require(all(q["source_sha256"] == p["source_sha256"] and q["state"] == "complete"
                for q in p["pages"]), "Windows page source/state")
    windows = w["windows"]
    require([n for win in windows for n in win["pages"]] == pages, "window coverage")
    require(all(1 <= len(win["pages"]) <= 3 and win["pages"][0] == win["start"]
                for win in windows), "native window segmentation")
    starts = {n: win["start"] for win in windows for n in win["pages"]}
    fields, lines_by_page = [], {}
    for q, layout_page in zip(p["pages"], layout["pages"]):
        n = q["page"]
        cells, lines = inspect_page(q, layout_page)
        lines_by_page[n] = lines
        info = dict(page=n, window_start=starts[n])
        for (ti, ri, ci), cell in cells.items():
            rows = q["tables"][ti]["rows"]
            header = text_of(rows[0][ci])
            if ri > 0 and label(header):
                fields.append(dict(id=f"page/{n}/table/{ti+1}/row/{ri+1}/col/{ci+1}", **info, kind="cell",
                                   table_index=ti, row_index=ri, col_index=ci, **cell, label_text=header,
                                   reason="label_in_detected_header", windows_value=text_of(rows[ri][ci])))
        for li, line in lines.items():
            if label(line["text"]):
                fields.append(dict(id=f"page/{n}/raw_line/{li+1}", **info, kind="prose", line_index=li,
                                   bbox=line["bbox"], span_indices=line["span_indices"], label_text=line["text"],
                                   reason="label_in_non_table_line", windows_value=line["text"]))
    manifest = dict(family=family, source_sha256=p["source_sha256"],
                    input_sha256={n: digest(data) for n, data in inputs.items()}, windows=windows,
                    selected_windows=sorted({f["window_start"] for f in fields}), fields=fields)
    return p, lines_by_page, manifest


def lookup(region_index, windows, native):
    """Accept one forward and one reverse eligible region. Candidate indices identify the evidence."""
    choices = [ni for ni, b in native.items() if eligible(windows[region_index], b)]
    if not choices:
        return None, "no_overlapping_region", choices
    if len(choices) > 1:
        return None, "multiple_native_regions", choices
    chosen, = choices
    if sum(eligible(b, native[chosen]) for b in windows.values()) != 1:
        return None, "native_region_matches_multiple_windows_regions", choices
    return chosen, None, choices


def bind(field, page, lines, native):
    tables = native["tables"]
    if field["kind"] == "cell":
        ti, ri, ci = field["table_index"], field["row_index"], field["col_index"]
        windows_boxes = {i: t["bbox"] for i, t in enumerate(page["tables"])}
        native_boxes = {i: t["bbox"] for i, t in enumerate(tables) if valid_box(t["bbox"])}
        idx, reason, candidates = lookup(ti, windows_boxes, native_boxes)
        witness = dict(candidate_table_indices=candidates, row_index=ri, col_index=ci)
        if reason:
            return None, reason, witness
        table = tables[idx]
        witness.update(table_index=idx, native_bbox=table["bbox"])
        if list(map(len, page["tables"][ti]["rows"])) != list(map(len, table["rows"])):
            return None, "grid_shape_mismatch", witness
        value = table["rows"][ri][ci]
        if not isinstance(value, str):
            return None, "no_literal_cell", witness
        return value, "same_shape_positional_cell", witness

    native_lines = {i: s["bbox"] for i, s in enumerate(native["spans"]) if valid_box(s["bbox"])
                    and not any(valid_box(t["bbox"]) and 2 * overlap(s["bbox"], t["bbox"]) >= area(s["bbox"])
                                for t in tables)}
    idx, reason, candidates = lookup(field["line_index"], {li: ln["bbox"] for li, ln in lines.items()}, native_lines)
    witness = dict(candidate_span_indices=candidates)
    if reason:
        return None, reason, witness
    span = native["spans"][idx]
    witness.update(span_index=idx, native_bbox=span["bbox"])
    value = span["text"]
    if not isinstance(value, str) or not value.strip() or len(value.splitlines()) != 1:
        return None, "no_literal_single_line", witness
    return value, "unique_whole_prose_line", witness


def route(page, lines, fields, native):
    require(native["page"] == page["page"] and native["source_sha256"] == page["source_sha256"],
            "admitted native page source")
    require(native.get("state", "complete") == "complete", "admitted native page state")
    require(all(node.get("page", page["page"]) == page["page"]
                and node.get("source_sha256", page["source_sha256"]) == page["source_sha256"]
                for node in native["tables"] + native["spans"]), "native observation source")
    out = deepcopy(page)
    after_lines, edits, additions, records = deepcopy(lines), {}, [], []
    for f in fields:
        before = f["windows_value"]
        value, reason, witness = bind(f, page, lines, native)
        emitted = before if value is None else value
        records.append(dict(id=f["id"], page=f["page"], status="unresolved" if value is None else "substituted",
                            reason=reason, native_value=value, emitted_value=emitted, changed=before != emitted,
                            witness=witness))
        if before == emitted:
            continue
        ids = f["span_indices"]
        if f["kind"] == "cell":
            row = out["tables"][f["table_index"]]["rows"][f["row_index"]]
            old_entry = row[f["col_index"]]
            row[f["col_index"]] = emitted if isinstance(old_entry, str) else dict(old_entry, text=emitted)
        else:
            after_lines[f["line_index"]]["text"] = emitted
        # Reuse the Windows support in observed page coordinates. Empty-cell ink has no word box.
        box = union([page["spans"][i]["bbox"] for i in ids]) if ids else f["bbox"]
        replacement = [dict(bbox=box, text=emitted, flagged=any(page["spans"][i].get("flagged", False)
                                                                 for i in ids))] if emitted else []
        for i in ids:
            require(i not in edits, "overlapping selected field members")
            edits[i] = []
        if ids:
            edits[min(ids)] = replacement
        else:
            additions.extend(replacement)
    out["spans"] = [v for i, span in enumerate(page["spans"]) for v in edits.get(i, [span])] + additions
    out["text"] = page_text(out, after_lines)
    return out, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for verb in ("manifest", "route"):
        cmd = commands.add_parser(verb)
        cmd.add_argument("windows", type=Path)
        cmd.add_argument("family", choices=("H", "A", "DEV"))
        cmd.add_argument("manifest", type=Path)
        if verb == "route":
            cmd.add_argument("manifest_sha256")
            cmd.add_argument("native", type=Path)
            cmd.add_argument("out", type=Path)
    args = parser.parse_args()
    pred, lines, manifest = read_windows(args.windows, args.family)
    if args.command == "manifest":
        print(publish(args.manifest, manifest))
        return
    frozen = args.manifest.read_bytes()
    require(digest(frozen) == args.manifest_sha256 and frozen == encode(manifest) + b"\n", "manifest freeze")
    by_page = defaultdict(list)
    for f in manifest["fields"]:
        by_page[f["page"]].append(f)
    decisions, sources = [], {}
    for i, page in enumerate(pred["pages"]):
        n = page["page"]
        if n in by_page:
            file = f"page-{n:03d}.json"
            data = (args.native/args.family/file).read_bytes()
            sources[file] = digest(data)
            pred["pages"][i], records = route(page, lines[n], by_page[n], json.loads(data))
            decisions.extend(records)
    require([f["id"] for f in decisions] == [f["id"] for f in manifest["fields"]], "decision coverage/order")
    for name, obj in (("decisions.json", dict(family=args.family, manifest_sha256=digest(frozen),
                                               native_page_sha256=sources, fields=decisions)),
                      ("prediction.json", pred)):
        print(name, publish(args.out/name, obj))


if __name__ == "__main__":
    main()
