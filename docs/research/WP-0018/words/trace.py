"""Trace the archived WinRT JSON and independently reconstruct the Windows adapter. CPU only."""
import argparse
from bisect import bisect_right
from collections import defaultdict
from hashlib import sha1, sha256
import json
from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[4]
INPUT_PINS = ROOT / "docs/coordination/WP-0018/kit/archive-pins.json"
SCORER_HASH = "1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7"
INVENTORIES = {
    "H": ("H-blind-inventory.json", "8e72acfc3f307da7e0f074edd937e61ce22f64ce"),
    "A": ("A-recovery-blind-inventory.json", "156e53d20f448d2410e218b961ae6a1630e9a978"),
}
WITNESSES = [
    ("H", 2, "table/1/row/2/col/1"),
    ("A", 60, "table/1/row/2/col/2"),
    ("H", 1, "line/2"),
    ("H", 2, "line/2"),
]


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def read_checked(path, want):
    data = path.read_bytes()
    require(sha256(data).hexdigest() == want, f"SHA-256 mismatch: {path}")
    return json.loads(data)


def write_json(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode())


def get_scorer(inputs):
    path = inputs / "control/score.py"
    require(sha256(path.read_bytes()).hexdigest() == SCORER_HASH, "scorer source mismatch")
    return runpy.run_path(str(path))


class Packet:
    def __init__(self, inputs, family):
        self.family = family
        self.directory = inputs / family
        self.pins = json.loads(INPUT_PINS.read_bytes())["families"][family]
        name, blob = INVENTORIES[family]
        # Normalize the Git working-tree EOL filter to the committed blob representation.
        data = (ROOT / "docs/reviews/WP-0015/evidence" / name).read_bytes().replace(b"\r\n", b"\n")
        require(sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == blob, name)
        runs = [r for r in json.loads(data)["runs"] if r["run"] == self.pins["run"]]
        require(len(runs) == 1, "ambiguous inventory run")
        self.file_pins = runs[0]["files"]
        self.truth_hash = self.pins["source_commitments_sha256"]["truth.json"]
        self.truth = read_checked(self.directory / "truth.json", self.truth_hash)
        self.pred_hash, self.pred = self.archived("prediction.json")
        require(self.pred["source_sha256"] == self.truth["source_sha256"] ==
                self.pins["source_commitments_sha256"]["source.pdf"], "wrong document")

    def archived(self, name):
        expected = self.file_pins[self.pins["folder"] + "/" + name]
        return expected, read_checked(self.directory / "windows" / name, expected)


def center(box, axis):
    return (box[axis] + box[axis + 2]) / 2


def spans_and_lines(raw, page):
    reader = raw["reader_result"]
    size = [reader["width"], reader["height"]]
    points = raw["points"]
    words, lines = [], []
    for li, line in enumerate(reader["lines"]):
        ids = []
        for wi, word in enumerate(line["words"]):
            ix = len(words)
            ids.append(ix)
            box = [round(v * points[i % 2] / size[i % 2], 3) for i, v in enumerate(word["bbox"])]
            require(page["spans"][ix] == {"text": word["text"], "bbox": box, "flagged": False},
                    f"projected word differs from span {ix}")
            words.append(dict(span=ix, raw_line=li, raw_word=wi, text=word["text"],
                              pixel_bbox=word["bbox"], projected_bbox=box))
        lines.append(dict(raw_line=li, raw_text=line["text"], spans_in_word_order=ids))
    require(len(words) == len(page["spans"]) == raw["word_count"], "raw/span count differs")
    return words, lines


def rebuild_grids(grids, words, lines, page):
    used = set()
    chunks, evidence = [], []
    for grid in grids:
        xs, ys = grid["xs"], grid["ys"]
        groups = [[[] for _ in xs[1:]] for _ in ys[1:]]
        for w in words:
            x, y = (center(w["projected_bbox"], a) for a in (0, 1))
            if xs[0] <= x < xs[-1] and ys[0] <= y < ys[-1]:
                groups[bisect_right(ys, y)-1][bisect_right(xs, x)-1].append(w["span"])
                used.add(w["span"])
        for row in groups:
            for group in row:
                group.sort(key=lambda i: (words[i]["raw_line"], words[i]["projected_bbox"][0]))
        rows = [[" ".join(words[i]["text"] for i in group) for group in row] for row in groups]
        bbox = [xs[0], ys[0], xs[-1], ys[-1]]
        archive_table = dict(bbox=bbox, rows=rows)
        require(page["tables"][len(evidence)] == archive_table, "grid rows differ from archive")
        evidence.append(dict(xs=xs, ys=ys, emitted=archive_table, spans_in_grid_join_order=groups))
        chunks.append((ys[0], xs[0], " ".join(v for row in rows for v in row)))
    require(len(grids) == len(page["tables"]), "grid count mismatch")
    for line in lines:
        remainder = [words[i] for i in line["spans_in_word_order"] if i not in used]
        if remainder:
            x, y = (min(w["projected_bbox"][a] for w in remainder) for a in (0, 1))
            chunks.append((y, x, " ".join(w["text"] for w in remainder)))
    require(" ".join(" ".join(c[2] for c in sorted(chunks)).split()) == page["text"],
            "reconstructed page text differs")
    return evidence


def targets(ref):
    for ti, table in enumerate(ref["tables"]):
        for ri, row in enumerate(table["rows"]):
            for ci, cell in enumerate(row):
                yield f"table/{ti+1}/row/{ri+1}/col/{ci+1}", cell, (ti, ri, ci)
    for li, line in enumerate(ref["lines"]):
        yield f"line/{li+1}", line, (li,)


def map_reference(ref, page, words, scorer):
    entries = list(targets(ref))
    cells = [(p, c) for p, c, ix in entries if len(ix) == 3]
    lines = [(p, c) for p, c, ix in entries if len(ix) == 1]
    owners = defaultdict(list)
    for w in words:
        box = w["projected_bbox"]
        if not scorer["valid_box"](box, ref["width"], ref["height"]):
            w["reference_owner"] = None
            continue
        owner = next((p for p, c in cells if scorer["in_cell"](box, c["bbox"])), None)
        if owner is None:
            eligible = [(p, c) for p, c in lines if scorer["on_line"](box, c["bbox"])]
            if eligible:
                owner = min(eligible, key=lambda pair: abs(center(pair[1]["bbox"], 1)-center(box, 1)))[0]
        w["reference_owner"] = owner
        if owner:
            owners[owner].append(w["span"])
    return owners


def match_tables(ref, page, scorer):
    candidates = sorted((-scorer["iou"](t["bbox"], p["bbox"]), ti, pi)
                        for ti, t in enumerate(ref["tables"]) for pi, p in enumerate(page["tables"])
                        if scorer["valid_box"](p["bbox"], ref["width"], ref["height"]))
    used, matched = set(), {}
    for neg, ti, pi in candidates:
        if -neg >= 0.5 and ti not in matched and pi not in used:
            used.add(pi)
            matched[ti] = (pi, -neg)
    return matched


class TracePage:
    def __init__(self, packet, num, scorer):
        self.packet = packet
        self.scorer = scorer
        self.num = num
        self.ref = ref = packet.truth["pages"][num-1]
        self.sha = packet.truth["source_sha256"]
        self.page = page = packet.pred["pages"][num-1]
        bindings = {"truth.json": packet.truth_hash, "windows/prediction.json": packet.pred_hash}
        def load(kind):
            name = f"{kind}-{num:03d}.json"
            digest, obj = packet.archived(name)
            require(obj["source_sha256"] == self.sha, name)
            bindings["windows/" + name] = digest
            return obj
        raw, stored_page, window = load("raw"), load("page"), load("window")
        require(page == stored_page and page["page"] == raw["page"] == ref["page"] == num and
                window["first_page"] == num and window["pages"] == 1, "page binding mismatch")
        require(raw["points"] == [ref["width"], ref["height"]], "projection point scale mismatch")
        self.words, lines = spans_and_lines(raw, page)
        self.grids = rebuild_grids(window["rule_tables"], self.words, lines, page)
        self.owners = map_reference(ref, page, self.words, scorer)
        self.matched = match_tables(ref, page, scorer)
        original = scorer["layout"](ref, page, self.sha)
        bare = scorer["layout"](ref, {**page, "tables": []}, self.sha)
        require(original["lines"] == bare["lines"], "prose changed")
        self.scores = [{entry["at"]: entry for entry in s["cells"] + s["lines"]} for s in (original, bare)]
        self.critical = {entry["at"]: entry for entry in original["critical"]}
        self.targets = {p: (c, ix) for p, c, ix in targets(ref)}
        reader = raw["reader_result"]
        self.evidence = dict(packet=packet.family, page=num, sha256=bindings,
                             recognition_pixels=[reader["width"], reader["height"]], pdf_points=raw["points"],
                             raw_reader_text=reader["text"], raw_lines=lines, reconstructed_spans=self.words,
                             original_grids=self.grids, emitted_page_text=page["text"])
        self.lines = lines

    def location(self, path):
        target, indices = self.targets[path]
        cell = len(indices) == 3
        at = f"page/{self.num}/{path}"
        original, bare = [s[at] for s in self.scores]
        input_order = self.owners[path]
        ordered = sorted(input_order, key=lambda i: self.words[i]["projected_bbox"][:2])
        spans = self.page["spans"]
        fallback_value, fallback_flag = self.scorer["joined"]([spans[i] for i in ordered])
        require(original["expected"] == target["text"] and fallback_value == bare["observed"] and
                bare["reported_span_boxes"] == [spans[i]["bbox"] for i in input_order], at)
        grid, iou, gid, grid_value = None, None, [], None
        if cell:
            ti, ri, ci = indices
            grid, iou = self.matched.get(ti, (None, None))
            if grid is not None:
                archive = self.grids[grid]
                require(original["reported_table_bbox"] == archive["emitted"]["bbox"], at)
                groups = archive["spans_in_grid_join_order"]
                if ri < len(groups) and ci < len(groups[ri]):
                    gid = groups[ri][ci]
                    grid_value = self.scorer["norm"](archive["emitted"]["rows"][ri][ci])
                require(grid_value == original["observed"] and not original["flagged"], at)
            else:
                require(original == bare, at)
            require(bare["flagged"] == fallback_flag, at)
            refptr = f"/pages/{self.num-1}/tables/{ti}/rows/{ri}/{ci}"
        else:
            refptr = f"/pages/{self.num-1}/lines/{indices[0]}"
        decision = "matched_grid" if grid is not None else ("already_fallback" if cell else "reference_line")
        return dict(packet=self.packet.family, at=at, truth_pointer=refptr, reference_bbox=target["bbox"],
                    expected=target["text"], critical_reference=target.get("critical"),
                    original_mode=decision, matched_predicted_table=grid, matched_iou=iou,
                    original_grid_spans=gid, reference_eligible_spans_input_order=input_order,
                    reference_spans_join_order=ordered,
                    selected_raw_lines=sorted({self.words[i]["raw_line"] for i in ordered + gid}),
                    original_observed=original["observed"], original_correct=original["correct"],
                    original_flagged=original.get("flagged", fallback_flag), without_grid_observed=bare["observed"],
                    without_grid_correct=bare["correct"], without_grid_flagged=fallback_flag,
                    original_critical_verdict=self.critical.get(at) if not cell else None)


def witnesses(inputs, out):
    scorer = get_scorer(inputs)
    packets, pages, records = {}, {}, []
    for family, num, path in WITNESSES:
        if family not in packets:
            packets[family] = Packet(inputs, family)
        key = f"{family}-{num:03d}"
        if key not in pages:
            pages[key] = TracePage(packets[family], num, scorer)
        records.append(pages[key].location(path))
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "witnesses.json", dict(
        conventions="Page numbers and at use one-based ordinals. All table, raw_line, raw_word, span and array indices use zero-based ordinals. Each reconstructed span is verified to equal the archived span in text, projected bbox and flagged=false. Grid orders reconstruct the archived cells.",
        locations=records, pages={k: v.evidence for k, v in pages.items()}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    witnesses(args.inputs, args.output)
