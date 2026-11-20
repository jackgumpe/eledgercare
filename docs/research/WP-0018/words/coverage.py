"""Account for every H/A truth location, keyed by packet and frozen scorer path."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from trace import Packet, TracePage, center, get_scorer, read_checked, require, write_json


WITNESS_HASH = "64b8e29bcacee8d0978e422bfc3f3c6471877a5c2b30eb69104891f7c073c5a8"
HISTORY = {
    "H": "827d653fa6d82ea8c71c5c8c53db1b3a30ed6fc1373cd13b1db48df3da26abff",
    "A": "7503cb3c2352a7d55cbcb0c191fe5e5a52099277a03fb45de8325fc8eea111db",
}
WRONG = ("unchanged_wrong", "gain")


def linear_fragment(page, ids, cell):
    """Locate literal OcrLine.Text for the whole line or an unambiguous contiguous raw word range."""
    if not ids:
        return None, None
    line_ids = {page.words[i]["raw_line"] for i in ids}
    if len(line_ids) != 1:
        return None, None
    info = page.lines[next(iter(line_ids))]
    word_order = info["spans_in_word_order"]
    if ids == word_order:
        return info["raw_text"], "whole_raw_line"
    if not cell:
        return None, None
    start = word_order.index(ids[0])
    if (word_order[start:start+len(ids)] == ids and
            info["raw_text"] == " ".join(page.words[i]["text"] for i in word_order)):
        return " ".join(page.words[i]["text"] for i in ids), "literal_contiguous_range_in_raw_line"
    return None, None


def group_checks(page, location):
    ids = location["reference_spans_join_order"]
    box = location["reference_bbox"]
    cell = "/table/" in location["at"]
    if cell:
        # This independent proximity test intentionally accepts more than in_cell(). A word crossing
        # the reference boundary is a competing observation even if the scorer excluded it.
        intersecting = [w["span"] for w in page.words if all(
            max(w["projected_bbox"][a], box[a]) < min(w["projected_bbox"][a+2], box[a+2])
            for a in (0, 1))]
        centered = [w["span"] for w in page.words if all(
            box[a] <= center(w["projected_bbox"], a) < box[a+2] for a in (0, 1))]
        geometric_support = set(intersecting) == set(centered) == set(ids)
    else:
        # Includes geometrically eligible spans even when a reference cell or nearer line took them.
        intersecting = [w["span"] for w in page.words
                        if page.scorer["on_line"](w["projected_bbox"], box)]
        centered = None
        geometric_support = set(intersecting) == set(ids)
    raw_order = sorted(ids)
    literal, literal_scope = linear_fragment(page, raw_order, cell)
    raw_words = [page.words[i]["text"] for i in raw_order]
    return dict(reference_intersecting_or_line_eligible_spans=intersecting,
                reference_center_spans=centered, unanimous_geometry=geometric_support,
                raw_order=raw_order, raw_order_word_texts=raw_words,
                raw_word_concatenation="".join(raw_words), literal_raw_fragment=literal,
                literal_raw_scope=literal_scope, scorer_order_matches_raw=raw_order == ids)


def nospace(s):
    return "".join(s.split())


def attribute(row, group):
    """Describe the first evidenced surface difference. Do not infer a hidden recognition mechanism."""
    expected, ids = row["expected"], row["reference_spans_join_order"]
    if row["original_correct"] and row["without_grid_correct"]:
        return "no_scored_divergence", [], []
    before, after = row["original_observed"], row["without_grid_observed"]
    changed = before != after
    effects = []
    if changed:
        effects.append("matched_grid_and_reference_box_selections_produce_different_values")
    if row["without_grid_correct"]:
        return "matched_grid_output_differs_from_correct_reference_group", effects, [
            "grid detection, cell membership and reference matching are not isolated by deleting tables"]
    if row["original_correct"]:
        return "oracle_selection_diverges_from_correct_original", effects, [
            "oracle memberships may omit or add words relative to the emitted cell"]
    alternatives = []
    if not ids:
        return "no_reference_eligible_group", effects, [
            "unread text, absent or displaced word boxes, and reference eligibility are unresolved"]
    if not group["unanimous_geometry"]:
        return "competing_or_rejected_nearby_words", effects, [
            "a nearby word overlaps the target but geometric ownership or eligibility differs"]
    literal = group["literal_raw_fragment"]
    if not group["scorer_order_matches_raw"]:
        effects.append("scorer_x_then_y_order_differs_from_raw_order")
        if literal == expected:
            return "selection_order_differs_from_correct_raw_line", effects, []
        return "ambiguous_word_order_and_raw_group", effects, [
            "raw ordering and geometry do not identify one cause"]
    cell = "/table/" in row["at"]
    texts = group["raw_order_word_texts"]
    if literal == expected:
        return "adapter_or_scorer_word_join_differs_from_correct_raw_line", effects + [
            "space_join_of_exported_words_differs_from_raw_line"], [
            "word boundaries and joining each participate in the observed string"]
    if literal is not None and nospace(literal) == nospace(expected):
        effects.append("downstream_word_join_preserves_raw_spacing" if after == literal
                       else "downstream_word_join_changes_raw_spacing")
        return "raw_line_whitespace_difference", effects, [
            "the archive exposes line text and word boundaries together; internal segmentation order is unknown"]
    if cell and len(texts) == 1 and len(expected.split()) == 1:
        return "anchored_raw_word_character_difference", effects, [
            "font, raster, glyph classification, internal segmentation and decoding are not separated"]
    if literal is not None:
        if nospace(literal) != nospace(expected):
            if after != literal:
                effects.append("downstream_join_changes_literal_raw_fragment")
            if (nospace(after or "") == nospace(expected) and
                    nospace(literal) != nospace(expected)):
                alternatives.append("word strings and WinRT line text have different nonspace characters")
            return "anchored_raw_line_character_difference", effects, alternatives + [
                "which glyphs were omitted, substituted, merged or added internally is unresolved"]
    return "raw_group_alignment_unresolved", effects, [
        "multiple raw lines or omitted word associations prevent a unique literal alignment"]


def category(first):
    if first.startswith("anchored_raw_") or first == "raw_line_whitespace_difference":
        return "raw_surface"
    if first in {"matched_grid_output_differs_from_correct_reference_group",
                 "selection_order_differs_from_correct_raw_line",
                 "adapter_or_scorer_word_join_differs_from_correct_raw_line",
                 "oracle_selection_diverges_from_correct_original"}:
        return "assembly_or_selection"
    return "no_scored_divergence" if first == "no_scored_divergence" else "uncertain"


def pack(page, path, history):
    row = page.location(path)
    h = history[row["at"]]
    require(h == page.scores[0][row["at"]], "original differs from archived score at " + row["at"])
    group = group_checks(page, row)
    first, effects, alternatives = attribute(row, group)
    label = category(first)
    if label == "raw_surface" and row["original_observed"] != row["without_grid_observed"]:
        label = "raw_surface_and_assembly_sensitivity"
    before, after = row["original_correct"], row["without_grid_correct"]
    outcome = {(True, True): "unchanged_right", (True, False): "loss",
               (False, False): "unchanged_wrong", (False, True): "gain"}[before, after]
    require(row["at"].startswith(f"page/{page.num}/"), row["at"])
    raw_name = f"windows/raw-{page.num:03d}.json"
    return dict(**row, raw_file=raw_name, raw_sha256=page.evidence["sha256"][raw_name],
                page_evidence_key=[page.packet.family, page.num], outcome=outcome, **group,
                first_supported_divergence=first, evidence_category=label, later_observations=effects,
                unresolved_alternatives=alternatives)


def jsonl(path, rows):
    with path.open("wb") as f:
        for row in rows:
            f.write((json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False)+"\n").encode())


def counts(rows, key):
    return dict(sorted(Counter(r[key] for r in rows).items()))


def analyze(inputs, out, checkpoint):
    require(sha256(checkpoint.read_bytes()).hexdigest() == WITNESS_HASH, "four-witness checkpoint mismatch")
    scorer = get_scorer(inputs)
    out.mkdir(parents=True, exist_ok=True)
    totals = {}
    for family, (length, cells, lines) in {"H": (4, 20, 16), "A": (60, 300, 288)}.items():
        packet = Packet(inputs, family)
        baseline = read_checked(packet.directory / "historical-score.json", HISTORY[family])
        require(len(packet.truth["pages"]) == len(baseline["pages"]) == length, family)
        locations, pages = [], []
        for num, hist in enumerate(baseline["pages"], 1):
            page = TracePage(packet, num, scorer)
            history = {r["at"]: r for r in hist["cells"] + hist["lines"]}
            records = [pack(page, path, history) for path in page.targets]
            require({r["at"] for r in records} == set(history), f"{family} page {num}")
            locations.extend(records)
            pages.append(page.evidence)
        require(len({r["at"] for r in locations}) == cells + lines, "location coverage")
        jsonl(out / f"locations-{family}.jsonl", locations)
        jsonl(out / f"pages-{family}.jsonl", pages)
        totals[family] = {}
        for kind, token, n in (("cells", "/table/", cells), ("prose", "/line/", lines)):
            subset = [r for r in locations if token in r["at"]]
            require(len(subset) == n, family + kind)
            wrong = [r for r in subset if r["outcome"] in WRONG]
            counts_by_outcome = counts(subset, "outcome")
            totals[family][kind] = dict(reference=n, originally_wrong=len(wrong),
                outcomes={k: counts_by_outcome.get(k, 0) for k in ("gain", "loss", "unchanged_wrong", "unchanged_right")},
                original_modes=counts(subset, "original_mode"),
                original_wrong_by_category=counts(wrong, "evidence_category"),
                original_wrong_first_divergence=counts(wrong, "first_supported_divergence"))
    write_json(out / "summary.json", totals)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--checkpoint", type=Path, default=Path(__file__).with_name("witnesses.json"))
    args = parser.parse_args()
    analyze(args.inputs, args.output, args.checkpoint)

