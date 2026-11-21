"""Replay a frozen candidate on observable JSON and test decision invariants before scoring."""
import argparse
import copy
import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path

SOURCE = "docs/research/WP-0021/read_scope.py"
MODES = ["grid", "grid-words"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(path.read_bytes())


def word_stream(document):
    for page in document["pages"]:
        for line, entry in enumerate(page["lines"], 1):
            for word in entry["words"]:
                yield page["page"], line, word


def target_rows(document, output):
    second = next(page for page in document["pages"] if page["page"] == 2)
    by_line = {row["line"]: row for row in output["rows"] if row["page"] == 2}
    assert len(by_line) == sum(row["page"] == 2 for row in output["rows"])
    assert set(by_line) == {i for i, line in enumerate(second["lines"], 1) if line["words"]}
    words_by_ref = {word["ref"]: (page, line, word) for page, line, word in word_stream(document)}
    assert len(words_by_ref) == sum(1 for _ in word_stream(document))
    for line, row in by_line.items():
        words = second["lines"][line - 1]["words"]
        assert [(w["literal"], w["word_ref"]) for w in row["words"]] == [
            (w["text"], w["ref"]) for w in words]
        assert (row["literal"], row["word_ref"]) == (words[-1]["text"], words[-1]["ref"])
        for field in ("property", "unit"):
            label = words_by_ref[row[field + "_label_ref"]]
            values = [words_by_ref[ref] for ref in row[field + "_refs"]]
            assert label[0] == 1 and label[2]["text"].lower().rstrip(":") == field
            assert values and all(v[:2] == label[:2] for v in values)
            assert row[field] == " ".join(v[2]["text"] for v in values)
        assert row["flagged"] is (row["scope"] is None)
    return by_line


def signatures(rows):
    fields = ["scope", "column_role", "reason", "flagged", "heading_refs", "header_refs",
              "stack_before", "stack_after", "grid", "alignment", "property_refs", "unit_refs"]
    return {li: {f: row[f] for f in fields} for li, row in rows.items()}


def check_metamorphs(document, output, mode, bind):
    rows = target_rows(document, output)
    # Keep source coordinates, vary every data literal to destroy layout hints from content.
    changed = copy.deepcopy(document)
    for page, _, word in word_stream(changed):
        if page == 2:
            word["text"] = f"o1-IÃƒÅ¸/{word['ref']}"
    alternate = bind(changed, mode)
    alt_rows = target_rows(changed, alternate)
    assert signatures(rows) == signatures(alt_rows)
    # A document prefix gives the same decisions, before a later row can be inspected.
    for through_line in rows:
        prefix = copy.deepcopy(document)
        page = next(p for p in prefix["pages"] if p["page"] == 2)
        page["lines"] = page["lines"][:through_line]
        actual = target_rows(prefix, bind(prefix, mode))
        assert actual == {li: item for li, item in rows.items() if li <= through_line}
    # Remove page-two rule evidence in grid-only mode.
    cleared = copy.deepcopy(document)
    next(p for p in cleared["pages"] if p["page"] == 2)["grids"] = []
    gridless = target_rows(cleared, bind(cleared, "grid"))
    assert all(row["scope"] is None and row["flagged"] for row in gridless.values())
    # A horizontal negative control: move a same-sized single literal into the
    # page's right margin while retaining the printed table and the original y.
    shifted = copy.deepcopy(document)
    p2 = next(p for p in shifted["pages"] if p["page"] == 2)
    rightmost = max((g["xs"][-1] for g in p2["grids"]), default=0)
    for line in p2["lines"]:
        if line["words"]:
            word = line["words"][-1]
            box = word["bbox"]
            width = box[2] - box[0]
            box[2] = p2["width_pt"] - 2
            box[0] = box[2] - width
            assert box[0] > rightmost
            line["words"] = [word]
    outside_rows = target_rows(shifted, bind(shifted, mode))
    unflagged_outside = [li for li, row in outside_rows.items() if not row["flagged"]]
    return {"outside_grid_unflagged_lines": unflagged_outside, "literal_mutations": sum(len(row["words"]) for row in rows.values()),
            "causal_prefixes": len(rows), "gridless_abstentions": len(gridless)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate")
    parser.add_argument("observations", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    code = subprocess.check_output(["git", "show", f"{args.candidate}:{SOURCE}"])
    candidate_path = args.out / "read_scope.py"
    candidate_path.write_bytes(code)
    binder = runpy.run_path(str(candidate_path))["read"]

    restricted = False
    def boundary(event, _):
        if restricted and (event == "open" or event.startswith(("socket.", "subprocess.", "os.system",
                                                                "os.listdir", "os.scandir", "ctypes."))):
            raise PermissionError(f"Reader attempted external operation during binding: {event}")

    sys.addaudithook(boundary)
    def bind(observation, mode):
        nonlocal restricted
        restricted = True
        try:
            return json.loads(json.dumps(binder(observation, mode)))
        finally:
            restricted = False

    result = {"candidate": args.candidate, "source_sha256": sha(code), "observations": {}}
    inputs = sorted(args.observations.glob("*.json"))
    assert inputs, "Empty observable input directory"
    for index, original in enumerate(inputs, 1):
        copy_dir = args.out / f"case-{index}"
        copy_dir.mkdir()
        neutral = copy_dir / "input.json"
        neutral.write_bytes(original.read_bytes())
        observation = read_json(neutral)
        record = {"input_sha256": sha(neutral.read_bytes()), "modes": {}}
        for mode in MODES:
            out_path = copy_dir / f"{mode}.json"
            command = [sys.executable, "-I", "-B", str(candidate_path.resolve()), "--mode", mode,
                       str(neutral.resolve()), str(out_path.resolve())]
            subprocess.run(command, cwd=copy_dir, check=True, capture_output=True)
            output = read_json(out_path)
            before = copy.deepcopy(observation)
            assert output == bind(observation, mode)
            assert before == observation
            tests = check_metamorphs(observation, output, mode, bind)
            record["modes"][mode] = {"output": out_path.relative_to(args.out).as_posix(),
                                     "sha256": sha(out_path.read_bytes()), **tests}
        result["observations"][original.name] = record
    write_json(args.out / "predictions.json", result)
    print(f"Replayed {len(inputs)} documents in both modes with pointer, causality and input-boundary checks.")


if __name__ == "__main__":
    main()

