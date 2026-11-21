"""Independently reconcile scope, full token receipts, raw grids and the paired counterexample."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def pixel_difference(path_a, path_b):
    with Image.open(path_a) as a, Image.open(path_b) as b:
        left, right = np.asarray(a.convert("L")), np.asarray(b.convert("L"))
        changed = left != right
        return {"different_grayscale_pixels": int(changed.sum()),
                "different_threshold_pixels": int(((left < 215) != (right < 215)).sum()),
                "values_left": np.unique(left[changed]).tolist(),
                "values_right": np.unique(right[changed]).tolist()}


def count_case(data, expected, out):
    by_id = {(r["page"], r["line"]): r for r in out["rows"]}
    actual_locations = [(target["page"], target["line"]) for target in expected["targets"]]
    assert sorted(by_id) == sorted(actual_locations) and len(by_id) == len(out["rows"])
    tokens = {w["ref"]: w["text"] for p in data["pages"] for l in p["lines"] for w in l["words"]}
    tally = Counter()
    details = []
    word_count = 0
    for target in expected["targets"]:
        p, line = target["page"], target["line"]
        scope = target["actual_scope"]
        group = "primary" if p == 2 else "initial"
        row = by_id[p, line]
        source = next(page for page in data["pages"] if page["page"] == p)["lines"][line - 1]["words"]
        assert [[w["literal"], w["word_ref"]] for w in row["words"]] == [
            [w["text"], w["ref"]] for w in source]
        assert (row["literal"], row["word_ref"]) == (target["literal"], target["word_ref"])
        assert tokens[row["word_ref"]] == row["literal"]
        assert all(row[f] == expected[f] for f in ("property", "unit", "property_refs", "unit_refs"))
        assert row["flagged"] is (row["scope"] is None)
        assert row["column_role"] == (None if row["flagged"] else "Amount")
        status = "abstained" if row["flagged"] else "exact" if row["scope"] == scope else "silent_wrong"
        tally.update([group + "_targets", group + "_" + status])
        if p == 2:
            word_count += len(source)
            ambiguity = "ambiguous" if target["ambiguous"] else "identifiable"
            tally.update([ambiguity + "_targets", ambiguity + "_" + status])
            if target["ambiguous"] and not row["flagged"]:
                tally["ambiguous_guesses"] += 1
            if target["missing_third"]:
                tally["rows_with_omitted_third"] += 1
                assert len(source) == 3
            if scope == "parent" and not target["ambiguous"]:
                tally["resumed_parent_targets"] += 1
                if status == "exact":
                    tally["resumed_parent_exact"] += 1
            details.append({"line": line, "true_scope": scope, "ambiguous": target["ambiguous"],
                            "scope": row["scope"], "flagged": row["flagged"], "reason": row["reason"],
                            "stack_before": row["stack_before"], "stack_after": row["stack_after"],
                            "word_ref": row["word_ref"], "literal": row["literal"]})
    return tally, {"p2_words_verified": word_count, "decisions": details}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("input_bundle", "truth", "blind_replay", "detector", "author_outputs", "coordinator_score", "out"):
        p.add_argument(arg, type=Path)
    a = p.parse_args()
    inputs, rasters = a.input_bundle / "inputs", a.input_bundle / "rasters"
    expected = load(a.truth)["cases"]
    replay = load(a.blind_replay / "predictions.json")["observations"]
    detected = load(a.detector)["input_pages"]
    reference = load(a.coordinator_score)
    assert set(expected) == {Path(n).stem for n in replay}
    result = {"cases": {}, "totals": {}, "sha256_verified_author_outputs": {}}
    totals = {"grid": Counter(), "words": Counter()}
    pair = []
    spent = set()
    for name, case in expected.items():
        filename = name + ".json"
        source_path = inputs / filename
        doc = load(source_path)
        assert digest(source_path) == replay[filename]["input_sha256"] == case["observationSha256"]
        item = {"page_grid_counts": [], "modes": {}}
        for page in doc["pages"]:
            loc = f"{name}-p{page['page']}.png"
            assert detected[loc]["grids"] == page["grids"]
            assert digest(rasters / loc) == detected[loc]["png_sha256"]
            spent.add(loc)
            item["page_grid_counts"].append(len(page["grids"]))
        if case["case"] == "ambiguous":
            pair.append(name)
        for mode, local_mode in (("grid", "grid"), ("words", "grid-words")):
            replay_record = replay[filename]["modes"][local_mode]
            resident = a.blind_replay / replay_record["output"]
            published = a.author_outputs / mode / filename
            assert resident.read_bytes() == published.read_bytes()
            result["sha256_verified_author_outputs"][f"{mode}/{filename}"] = digest(published)
            tally, classified = count_case(doc, case, load(resident))
            assert tally == Counter(reference[mode]["cases"][name]["counts"])
            totals[mode].update(tally)
            item["modes"][mode] = classified
        result["cases"][name] = item
    assert spent == set(detected)
    for mode, counts in totals.items():
        assert counts == Counter(reference[mode]["totals"])
        result["totals"][mode] = dict(sorted(counts.items()))
    assert len(pair) == 2
    left, right = pair
    assert (inputs / (left + ".json")).read_bytes() == (inputs / (right + ".json")).read_bytes()
    left_key = [t for t in expected[left]["targets"] if t["ambiguous"]]
    right_key = [t for t in expected[right]["targets"] if t["ambiguous"]]
    assert len(left_key) == len(right_key) == 1
    assert {left_key[0]["actual_scope"], right_key[0]["actual_scope"]} == {"parent", "child"}
    for mode in totals:
        assert (a.author_outputs / mode / (left + ".json")).read_bytes() == (
            a.author_outputs / mode / (right + ".json")).read_bytes()
    raster_diff = {str(page): pixel_difference(rasters / f"{left}-p{page}.png",
                                               rasters / f"{right}-p{page}.png") for page in (1, 2)}
    assert all(diff["different_threshold_pixels"] == 0 for diff in raster_diff.values())
    result["pair"] = {"ids": pair, "identical_observations": True, "identical_predictions": True,
                      "opposite_key": True, "raster_differences": raster_diff}
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["totals"], sort_keys=True))


if __name__ == "__main__":
    main()
