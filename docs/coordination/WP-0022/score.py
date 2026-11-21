"""Score the frozen reader's ownership decisions using source geometry, never text for matching."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode())


def area(box):
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def overlap(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def centered(box, region):
    x = (box[0] + box[2]) / 2
    y = (box[1] + box[3]) / 2
    return region[0] <= x < region[2] and region[1] <= y < region[3]


def sourced(box, region):
    return centered(box, region) and overlap(box, region) >= .5 * area(box)


def belongs(word, target):
    box = word["bbox"]
    return centered(box, target["row_box"]) or any(centered(box, b) for b in target["note_boxes"])


def index_observation(observation):
    sources, lines = {}, {}
    for page in observation["pages"]:
        for number, line in enumerate(page["lines"], 1):
            location = (page["page"], number)
            assert location not in lines
            lines[location] = line["words"]
            for word in line["words"]:
                ref = word["ref"]
                assert ref not in sources and area(word["bbox"]) > 0, (location, ref)
                sources[ref] = (location[0], word)
    return sources, lines


def refs_in(refs, region, sources):
    if not refs:
        return False
    return all(sources[ref][0] == region["page"] and sourced(sources[ref][1]["bbox"], region["bbox"])
               for ref in refs)


def collect_outputs(targets, sources, lines, predictions):
    by_target = defaultdict(list)
    outside = []
    observed = set()
    for row in predictions["rows"]:
        location = (row["page"], row["line"])
        assert location not in observed
        observed.add(location)
        words = lines[location]
        assert [(w["text"], w["ref"]) for w in words] == [(v["literal"], v["word_ref"]) for v in row["words"]]
        assert words and (words[-1]["text"], words[-1]["ref"]) == (row["literal"], row["word_ref"])
        assert row["flagged"] is (row["scope"] is None)
        if row["flagged"]:
            assert row["column_role"] is None
        page_targets = [t for t in targets if t["page"] == location[0]]
        hits = [t for t in page_targets if belongs(words[-1], t)]
        assert len(hits) <= 1, ("overlapping truth rows", location, hits)
        if not hits:
            outside.append(dict(page=location[0], line=location[1], ref=row["word_ref"], literal=row["literal"],
                                scope=row["scope"], flagged=row["flagged"], reason=row["reason"]))
            continue
        target = hits[0]
        box = words[-1]["bbox"]
        note = any(sourced(box, b) for b in target["note_boxes"])
        amount = sourced(box, target["amount_box"])
        # A word spanning a note and a cell cannot prove which printed source supplied a value.
        straddles_note = amount and any(overlap(box, b) > 0 for b in target["note_boxes"])
        origin = "note" if note else "amount" if amount and not straddles_note else "other"
        mixed = any(any(t["id"] != target["id"] and belongs(w, t) for t in page_targets) for w in words)
        anchors = {field: refs_in(row[refs], target[region], sources) for field, refs, region in (
            ("property", "property_refs", "property_region"), ("unit", "unit_refs", "unit_region"),
            ("sectionHeading", "heading_refs", "heading"))}
        bound = row["flagged"] is False
        correct = (bound and target["kind"] == "value" and origin == "amount" and not mixed
                   and row["column_role"] == "Amount" and row["scope"] == target["scope"] and all(anchors.values()))
        by_target[target["id"]].append(dict(line=location[1], ref=row["word_ref"], literal=row["literal"],
            bounds=box, origin=origin, crossesKeyedRows=mixed, role=row["column_role"], scope=row["scope"],
            flagged=row["flagged"], context=anchors, correctPost=correct, reason=row["reason"]))
    return by_target, outside


def evaluate(target, events, sources):
    kind = target["kind"]
    assert kind in {"value", "blank", "ambiguous"}
    region = target["amount_box"]
    cell = [w for pg, w in sources.values() if pg == target["page"] and overlap(w["bbox"], region) > 0]
    centered_cell = [w for w in cell if sourced(w["bbox"], region)]
    posts = [e for e in events if not e["flagged"]]
    flagged = [e for e in events if e["flagged"]]
    cell_flags = [e for e in flagged if e["origin"] == "amount"]
    correct = [e for e in posts if e["correctPost"]]
    false_count = len(posts) - min(1, len(correct))
    if false_count:
        outcome = "silent_wrong"
    elif kind == "blank":
        outcome = "blank_safely_withheld"
    elif kind == "ambiguous" and cell_flags:
        outcome = "ambiguous_flagged"
    elif correct:
        outcome = "value_owned"
    elif not cell:
        outcome = "no_intersecting_word"
    elif cell_flags:
        outcome = "value_flagged" if kind == "value" else "ambiguous_flagged"
    elif flagged:
        outcome = "other_word_flagged"
    else:
        outcome = "no_field_emitted"
    passed = outcome in {"blank_safely_withheld", "value_owned", "ambiguous_flagged"}
    return dict(outcome=outcome, passed=passed, events=events, correctPosts=len(correct), silentWrongPosts=false_count,
                anyExplicitFlag=bool(flagged), anyAmountFlag=bool(cell_flags), intersectionRefs=[w["ref"] for w in cell],
                centeredRefs=[w["ref"] for w in centered_cell], noteCaptures=sum(e["origin"] == "note" for e in posts),
                transcriptionMismatch=int(outcome == "value_owned" and correct[0]["literal"] != target["literal"]),
                # This frozen reader cannot emit a typed, explicit empty cell. A null scope is a review flag.
                positivelyRepresentedBlank=False)


def summarize(items, outside):
    counts = Counter(dict(targets=0, valueTargets=0, blankTargets=0, ambiguousTargets=0, passed=0, exactValueOwnership=0,
        silentWrongTargets=0, silentWrongPosts=0, explicitFlagRowsUnambiguousValue=0, explicitFlagRowsAmbiguous=0,
        explicitFlagRowsBlank=0, explicitAmountFlagsUnambiguous=0, explicitAmountFlagsAmbiguous=0,
        explicitFlagEvents=0, ambiguousSafelyFlagged=0, preservedBlanksExplicit=0, safeUnpostedBlanks=0,
        blankRowsWithIntersectingWords=0, populatedZeroIntersectingWords=0, multipleCenterWordsPopulated=0,
        noteCapturesOppositePopulated=0, noteCapturesOppositeBlank=0, noteCapturesOppositeAmbiguous=0,
        transcriptionOnlyMismatches=0, correctOwnedAndTranscribed=0, unflaggedOutsideRows=0, flaggedOutsideRows=0))
    outcomes = Counter()
    for t, detail in items:
        outcome = detail["outcome"]
        kind = t["kind"]
        counts["targets"] += 1
        counts[kind + "Targets"] += 1
        counts["passed"] += detail["passed"]
        counts["exactValueOwnership"] += outcome == "value_owned"
        counts["silentWrongTargets"] += outcome == "silent_wrong"
        counts["silentWrongPosts"] += detail["silentWrongPosts"]
        flag_metric = {"value":"explicitFlagRowsUnambiguousValue","blank":"explicitFlagRowsBlank","ambiguous":"explicitFlagRowsAmbiguous"}
        counts[flag_metric[kind]] += detail["anyExplicitFlag"]
        counts["explicitFlagEvents"] += sum(e["flagged"] for e in detail["events"])
        counts["explicitAmountFlagsUnambiguous"] += kind == "value" and detail["anyAmountFlag"]
        counts["explicitAmountFlagsAmbiguous"] += kind == "ambiguous" and detail["anyAmountFlag"]
        counts["ambiguousSafelyFlagged"] += outcome == "ambiguous_flagged"
        counts["safeUnpostedBlanks"] += outcome == "blank_safely_withheld"
        counts["blankRowsWithIntersectingWords"] += kind == "blank" and bool(detail["intersectionRefs"])
        counts["populatedZeroIntersectingWords"] += kind != "blank" and not detail["intersectionRefs"]
        counts["multipleCenterWordsPopulated"] += kind != "blank" and len(detail["centeredRefs"]) > 1
        note_metric = {"value":"noteCapturesOppositePopulated","blank":"noteCapturesOppositeBlank","ambiguous":"noteCapturesOppositeAmbiguous"}
        counts[note_metric[kind]] += detail["noteCaptures"]
        counts["transcriptionOnlyMismatches"] += detail["transcriptionMismatch"]
        counts["correctOwnedAndTranscribed"] += outcome == "value_owned" and not detail["transcriptionMismatch"]
        outcomes[outcome] += 1
    counts["unflaggedOutsideRows"] = sum(not row["flagged"] for row in outside)
    counts["flaggedOutsideRows"] = sum(row["flagged"] for row in outside)
    return {"counts": dict(counts), "outcomes": dict(sorted(outcomes.items()))}


def score(key, evidence):
    targets = key["targets"]
    assert targets and len({t["id"] for t in targets}) == len(targets)
    by_doc = defaultdict(list)
    for t in targets:
        assert all(area(b)>0 for b in [t["row_box"], t["amount_box"], *t["note_boxes"]])
        assert t["scope"] in {"parent", "child"} and (t["kind"] == "blank") == (t["literal"] == "")
        by_doc[t["doc"]].append(t)
    seen = {p.stem for p in (evidence / "observations/R").glob("*.json")}
    assert seen == set(by_doc), (seen, set(by_doc))
    arms, row_results = {}, {t["id"]: {} for t in targets}
    for arm in ("R","W"):
        extras = []
        for doc, group in by_doc.items():
            sources, lines = index_observation(read(evidence / "observations" / arm / (doc + ".json")))
            pred = read(evidence / "predictions" / arm / (doc + ".json"))
            located, remainder = collect_outputs(group, sources, lines, pred)
            extras.extend(dict(doc=doc, **row) for row in remainder)
            for t in group:
                row_results[t["id"]][arm] = evaluate(t, located[t["id"]], sources)
        items = [(t, row_results[t["id"]][arm]) for t in targets]
        arms[arm] = dict(overall=summarize(items, extras),
            setup=summarize([x for x in items if "setup" in x[0]["tags"]], []),
            postBreak=summarize([x for x in items if x[0]["page"]>1], []), outside=extras)
    matrix = {name: [] for name in ("pass/pass","pass/fail","fail/pass","fail/fail")}
    for t in targets:
        pair = row_results[t["id"]]
        result = "/".join("pass" if pair[a]["passed"] else "fail" for a in ("R","W"))
        pair["pair"] = result
        matrix[result].append(t["id"])
    return dict(matrix=matrix, arms=arms, rows=row_results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("truth", type=Path)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write(args.output, score(read(args.truth), args.evidence))
