"""Read a two-level ledger from page-ordered, source-referenced line observations."""
import argparse
from dataclasses import dataclass
from itertools import combinations, pairwise
import json
from pathlib import Path


GRID_TOLERANCE_PT = 2.0
WORD_TOLERANCE_PT = 3.0
HEADINGS = {("Ledger",): "parent", ("Contractor", "detail"): "child"}
SHARED_HEADER = ("Date", "Description", "Ref", "Amount")
HEADERS = {
    "parent": {("Date", "Charge", "Unit", "Amount"), SHARED_HEADER},
    "child": {("Vendor", "WorkOrder", "Hrs", "Amount"), SHARED_HEADER},
}


@dataclass
class Frame:
    scope: str
    heading_refs: tuple = ()
    header_refs: tuple = ()
    anchors: tuple = ()
    rules: tuple = ()
    header_page: int = 0
    headed_grid: dict | None = None


@dataclass(frozen=True)
class Evidence:
    reason: str
    candidates: tuple = ()

    def record(self):
        return {"reason": self.reason, "candidates": list(self.candidates)}


def vertical_span(words):
    centers = [(w["bbox"][1] + w["bbox"][3]) / 2 for w in words]
    return min(centers), max(centers)


def observed_grid(words, grids):
    """Use only vertical word location to select a rule-delimited band."""
    low, high = vertical_span(words)
    covering = []
    for grid in grids:
        ys = grid["ys"]
        if any(top <= low and high < bottom for top, bottom in pairwise(ys)):
            covering.append(grid)
    if not covering:
        return "no-grid-band", None
    if len(covering) > 1:
        return "overlapping-grid-bands", None
    xs = covering[0]["xs"]
    if len(xs) != 5 or not all(a < b for a, b in pairwise(xs)):
        return "incomplete-grid", None
    return "complete-grid", covering[0]


def grid_evidence(frames, words, grids, page_number):
    reason, grid = observed_grid(words, grids)
    if grid is None:
        return Evidence(reason)
    current = frames[-1]
    if current.header_page == page_number and current.headed_grid is grid:
        return Evidence("same-headed-grid", (current.scope,))
    if not all(f.rules for f in frames):
        return Evidence("missing-header-grid")
    matches = tuple(f.scope for f in frames if all(
        abs(x - anchor) <= GRID_TOLERANCE_PT for x, anchor in zip(grid["xs"], f.rules)
    ))
    return Evidence("grid-match" if matches else "unmatched-grid", matches)


def aligns(words, anchors):
    # Empty cells have no token. Preserve source order and reserve the final slot
    # for the amount, the only required token in the supplied row contract.
    if len(words) > len(anchors):
        return False
    starts = [w["bbox"][0] for w in words]
    for slots in combinations(range(len(anchors) - 1), len(words) - 1):
        if all(abs(x - anchors[i]) <= WORD_TOLERANCE_PT
               for x, i in zip(starts, (*slots, len(anchors) - 1))):
            return True
    return False


def word_evidence(frames, words):
    if not all(f.anchors for f in frames):
        return Evidence("missing-header-anchors")
    matches = tuple(f.scope for f in frames if aligns(words, f.anchors))
    return Evidence("aligned-words" if matches else "unaligned-words", matches)


def decide(grid, alignment):
    if len(grid.candidates) == 1:
        scope = grid.candidates[0]
        if alignment is not None and scope not in alignment.candidates:
            return None, "grid-word-disagreement"
        return scope, grid.reason
    if alignment is not None and len(alignment.candidates) == 1:
        return alignment.candidates[0], "unique-word-alignment"
    evidence = alignment if alignment is not None else grid
    return None, "tied-scopes" if evidence.candidates else evidence.reason


def read(document, mode):
    if mode not in ("grid", "grid-words"):
        raise ValueError("unknown observation mode")
    frames = []
    banners = {}
    rows = []
    previous_page = 0
    for page in document["pages"]:
        page_number = page["page"]
        if page_number <= previous_page:
            raise ValueError("expected increasing page order")
        previous_page = page_number
        for line_no, line in enumerate(page["lines"], 1):
            words = line["words"]
            if not words:
                continue
            tokens = tuple(w["text"] for w in words)
            refs = tuple(w["ref"] for w in words)
            if not frames and tokens[0] in ("Property:", "Unit:"):
                banners[tokens[0][:-1].lower()] = (tokens[1:], refs[1:], refs[0])
                continue
            if scope := HEADINGS.get(tokens):
                frame = Frame(scope, heading_refs=refs)
                if scope == "parent":
                    frames = [frame]
                else:
                    parent = frames[0] if frames else Frame("parent")
                    frames = [parent, frame]
                continue

            if frames and not frames[-1].header_refs and tokens in HEADERS[frames[-1].scope]:
                frame = frames[-1]
                frame.header_refs = refs
                frame.anchors = tuple(w["bbox"][0] for w in words)
                _, header_grid = observed_grid(words, page["grids"])
                if header_grid is not None:
                    frame.rules = tuple(header_grid["xs"])
                    low, high = vertical_span(words)
                    if header_grid["ys"][0] <= low <= high < header_grid["ys"][1]:
                        frame.header_page = page_number
                        frame.headed_grid = header_grid
                continue

            before = [f.scope for f in frames]
            grid = Evidence("no-open-frame")
            alignment = None
            if frames:
                grid = grid_evidence(frames, words, page["grids"], page_number)
                if mode == "grid-words":
                    alignment = word_evidence(frames, words)
            scope, reason = decide(grid, alignment)
            if not all(banners.get(key, ((),))[0] for key in ("property", "unit")):
                scope, reason = None, "missing-banner"
            chosen = next((f for f in frames if f.scope == scope), None)
            if chosen is not None:
                frames = frames[:frames.index(chosen) + 1]

            row = {
                "page": page_number, "line": line_no,
                "literal": tokens[-1], "word_ref": refs[-1],
                "words": [{"literal": w["text"], "word_ref": w["ref"]} for w in words],
                "scope": scope, "column_role": "Amount" if chosen else None,
                "heading_refs": chosen.heading_refs if chosen else (),
                "header_refs": chosen.header_refs if chosen else (),
                "flagged": chosen is None, "reason": reason,
                "stack_before": before, "stack_after": [f.scope for f in frames],
                "grid": grid.record(),
                "alignment": alignment.record() if alignment is not None else None,
            }
            for key in ("property", "unit"):
                value, value_refs, label_ref = banners.get(key, ((), (), None))
                row[key] = " ".join(value)
                row[f"{key}_refs"] = value_refs
                row[f"{key}_label_ref"] = label_ref
            rows.append(row)
    return {"rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("grid", "grid-words"))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    document = json.loads(args.input.read_text(encoding="utf-8"))
    result = read(document, args.mode)
    with args.output.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(result, output, indent=2, ensure_ascii=False)
        output.write("\n")


if __name__ == "__main__":
    main()
