"""Fixed application-visible selectors and merge. All OCR coordinates are raw pixel edges."""
from bisect import bisect_right
from collections import defaultdict
from math import ceil, floor
import re
from statistics import median

from visual import bbox_union, layout

CELL_INSET = 4
PROSE_PAD_X, PROSE_PAD_Y = 12, 8
MAX_REGIONS = 32
LABELS = {"id", "identifier", "code", "docket", "serial", "tag", "ref", "reference",
          "asset", "batch", "lot", "inspection"}
# Generic separated identifier. A candidate must be a single raw OCR word.
CODE = re.compile(r"[A-Za-z0-9]{2,}(?:-[A-Za-z0-9]{2,})+")
ALNUM = re.compile(r"[A-Za-z0-9]+")


def has_digit(text):
    return any(c.isdigit() for c in text)


def code(text):
    return bool(CODE.fullmatch(text) and has_digit(text))


def label(text):
    return bool(LABELS.intersection(re.findall(r"[a-z]+", text.lower())))


def column_signal(text):
    return has_digit(text) and ("-" in text or any(c.isalpha() for c in text))


def to_points(box, size, points):
    return [round(v * points[i % 2] / size[i % 2], 3) for i, v in enumerate(box)]


def area(box):
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def intersection(a, b):
    return [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]


def regions(raw, grids, points, page, base):
    size = (raw["width"], raw["height"])
    cell_words, prose = defaultdict(list), defaultdict(list)
    for li, line in enumerate(raw["lines"]):
        for wi, word in enumerate(line["words"]):
            ref = (li, wi)
            x0, y0, x1, y1 = to_points(word["bbox"], size, points)
            x, y = (x0 + x1) / 2, (y0 + y1) / 2
            owned = False
            for ti, grid in enumerate(grids):
                xs, ys = grid["xs"], grid["ys"]
                if xs[0] <= x < xs[-1] and ys[0] <= y < ys[-1]:
                    cell_words[ti, bisect_right(ys, y)-1, bisect_right(xs, x)-1].append(ref)
                    owned = True
            if not owned:
                prose[li].append(ref)

    def word(ref):
        return raw["lines"][ref[0]]["words"][ref[1]]

    candidates = []
    for ti, grid in enumerate(grids):
        xs, ys = grid["xs"], grid["ys"]
        rows = base["tables"][ti]["rows"]
        id_columns = [label(rows[0][ci]) or any(column_signal(r[ci]) for r in rows[1:])
                      for ci in range(len(xs)-1)]
        for ri, row in enumerate(rows):
            for ci, value in enumerate(row):
                box = [xs[ci], ys[ri], xs[ci+1], ys[ri+1]]
                x0, y0, x1, y1 = [v*size[i % 2]/points[i % 2] for i, v in enumerate(box)]
                rect = [max(0, ceil(x0)+CELL_INSET), max(0, ceil(y0)+CELL_INSET),
                        min(size[0], floor(x1)-CELL_INSET), min(size[1], floor(y1)-CELL_INSET)]
                refs = sorted(cell_words[ti, ri, ci],
                              key=lambda r: (r[0], to_points(word(r)["bbox"], size, points)[0]))
                if value != " ".join(word(r)["text"] for r in refs):
                    raise ValueError("grid/word membership differs from visual.layout")
                reason = ("numeric_cell" if has_digit(value) else
                          "identifier_column_body" if ri > 0 and id_columns[ci] else "no_id_signal")
                candidates.append(dict(id=f"page/{page}/table/{ti+1}/row/{ri+1}/col/{ci+1}",
                                       kind="cell", grid_index=[ti, ri, ci], bbox_points=box,
                                       rect_px=rect, full_word_refs=refs, full_value=value, reason=reason))
    for li, refs in prose.items():
        box = bbox_union([word(r)["bbox"] for r in refs])
        value = " ".join(word(r)["text"] for r in refs)
        rect = [max(0, floor(box[0])-PROSE_PAD_X), max(0, floor(box[1])-PROSE_PAD_Y),
                min(size[0], ceil(box[2])+PROSE_PAD_X), min(size[1], ceil(box[3])+PROSE_PAD_Y)]
        reason = ("numeric_line" if has_digit(value) else
                  "identifier_label" if label(value) else "no_id_signal")
        candidates.append(dict(id=f"page/{page}/raw_line/{li+1}", kind="prose", line_index=li,
                               bbox_points=to_points(box, size, points), rect_px=rect,
                               full_word_refs=refs, full_value=value, reason=reason))

    selected, used = [], set()
    for region in candidates:
        rect, refs = region["rect_px"], region["full_word_refs"]
        region["eligible"] = region["reason"] != "no_id_signal"
        region["selected"] = False
        if not region["eligible"]:
            continue
        if not area(rect):
            region["reason"] = "empty_clip"
        elif used.intersection(refs) or any(2*area(intersection(rect, prev)) >= min(area(rect), area(prev))
                                            for prev in selected):
            region["reason"] = "overlapping_region"
        elif len(selected) == MAX_REGIONS:
            region["reason"] = "page_cap"
        else:
            region["selected"] = True
            used.update(refs)
            selected.append(rect)
    return candidates


def compare_words(full_words, crop_words, kind, line_count):
    """Return one decision. Raw code points are never edited or concatenated for emission."""
    old = [w["text"] for w in full_words]
    new = [w["text"] for w in crop_words]
    if old == new:
        return "keep_agree"
    if not new:
        return "keep_empty_read"
    if line_count != 1:
        return "keep_multiline"
    if not old:
        if kind == "cell" and len(new) == 1 and code(new[0]):
            return "use_detected_empty_cell_read"
        return "keep_no_supported_replacement"
    # Isolate the one changed stretch, preserving every surrounding word exactly.
    left, right = 0, 0
    while left < min(len(old), len(new)) and old[left] == new[left]:
        left += 1
    while right < min(len(old), len(new))-left and old[-1-right] == new[-1-right]:
        right += 1
    a = full_words[left:len(old)-right]
    b = new[left:len(new)-right]
    if len(b) != 1 or not code(b[0]) or not a or any(code(w["text"]) for w in a):
        return "keep_no_supported_replacement"
    if len(a) == 1:
        prior = a[0]["text"]
        if ALNUM.fullmatch(prior) and prior == b[0].replace("-", ""):
            return "use_crop_delimiter"
    else:
        # A narrow split with exactly identical non-space characters is the only multiword edit.
        heights = [w["bbox"][3]-w["bbox"][1] for w in a]
        close = all(0 <= v["bbox"][0]-u["bbox"][2] <= .35*median(heights) for u, v in zip(a, a[1:]))
        if close and "".join(w["text"] for w in a) == b[0]:
            return "use_crop_single_word"
    return "keep_no_supported_replacement"


def attach_read(region, raw, crop):
    x, y, _, _ = region["rect_px"]
    projected = []
    for li, line in enumerate(crop["lines"]):
        for wi, w in enumerate(line["words"]):
            box = [v + (x, y)[i % 2] for i, v in enumerate(w["bbox"])]
            projected.append(dict(text=w["text"], bbox=box, crop_word_ref=[li, wi]))
    full = [raw["lines"][li]["words"][wi] for li, wi in region["full_word_refs"]]
    decision = compare_words(full, projected, region["kind"], len(crop["lines"]))
    if decision.startswith("use_") and full:
        old_box = bbox_union([w["bbox"] for w in full])
        new_box = bbox_union([w["bbox"] for w in projected])
        if area(intersection(old_box, new_box)) < .5*max(area(old_box), area(new_box)):
            decision = "keep_location_mismatch"
    value = " ".join(w["text"] for w in projected)
    different = value != region["full_value"]
    use = decision.startswith("use_")
    region.update(crop=crop, projected_words=projected, crop_value=value, decision=decision,
                  disagreement=different, flagged=different and not use,
                  emitted_value=value if use else region["full_value"])


def prediction(raw, grids, points, candidates):
    # Keep the baseline raw record immutable. Relayout actual projected crop words for accepted reads.
    edits, flags, appended = {}, set(), []
    for r in candidates:
        refs = r["full_word_refs"]
        if r.get("flagged"):
            flags.update(refs)
        if r.get("decision", "").startswith("use_"):
            words = [dict(text=w["text"], bbox=w["bbox"]) for w in r["projected_words"]]
            for ref in refs:
                edits[ref] = []
            if refs:
                edits[refs[0]] = words
            else:
                appended.append({"words": words})
    lines, span_flags = [], []
    for li, ln in enumerate(raw["lines"]):
        words = []
        for wi, w in enumerate(ln["words"]):
            replacement = edits.get((li, wi), [w])
            words.extend(replacement)
            span_flags.extend([(li, wi) in flags] * len(replacement))
        lines.append({"words": words})
    for ln in appended:
        span_flags.extend([False] * len(ln["words"]))
    output = layout(dict(raw, lines=lines + appended), grids, points)
    for span, flagged in zip(output["spans"], span_flags, strict=True):
        span["flagged"] = flagged
    for r in candidates:
        if r["kind"] != "cell":
            continue
        ti, ri, ci = r["grid_index"]
        row = output["tables"][ti]["rows"][ri]
        if row[ci] != r["emitted_value"]:
            raise ValueError("merged grid disagrees with decision at " + r["id"])
        if r.get("flagged"):
            row[ci] = {"text": row[ci], "flagged": True}
    return output
