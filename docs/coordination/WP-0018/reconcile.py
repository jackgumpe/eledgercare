"""Cross-check the two authors' Git records by location and summarize their observed boundaries."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[3]
PAIR = "docs/research/WP-0018/pair/evidence"
WORDS = "docs/research/WP-0018/words/coverage"


def git_file(rev, name):
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{rev}:{name}"])


def index(data):
    rows = [json.loads(line) for line in data.splitlines()]
    result = {r["at"]: r for r in rows}
    if len(rows) != len(result):
        raise ValueError("Duplicate scorer location")
    return result


def require(condition, message):
    if not condition:
        raise ValueError(message)


def reconcile(family, pair_revision, word_revision):
    pair_bytes = git_file(pair_revision, f"{PAIR}/{family}/cells.jsonl")
    word_bytes = git_file(word_revision, f"{WORDS}/locations-{family}.jsonl")
    summary = json.loads(git_file(pair_revision, f"{PAIR}/{family}/pair.json"))
    score_rows, locations = index(pair_bytes), index(word_bytes)
    require(set(score_rows) == {k for k in locations if "/table/" in k}, "Different cell populations")
    require(hashlib.sha256(pair_bytes).hexdigest() == summary["cells_jsonl_sha256"], "Invalid paired ledger checksum")
    attribution = {"cell": Counter(), "line": Counter()}
    by_half, by_row, losses = {}, {}, []
    changed_wrong = []
    for key, trace in locations.items():
        is_cell = "/table/" in key
        if not trace["original_correct"]:
            attribution["cell" if is_cell else "line"][trace["first_supported_divergence"]] += 1
        if not is_cell:
            require(trace["original_correct"] == trace["without_grid_correct"] and
                    trace["original_observed"] == trace["without_grid_observed"], f"Prose changed at {key}")
            continue
        row = score_rows[key]
        require(trace["packet"] == row["packet"] == family and trace["expected"] == row["expected"], key)
        require(row["before"]["mode"] == trace["original_mode"] and row["transition"] == trace["outcome"], key)
        for arm, prefix in (("before", "original"), ("after", "without_grid")):
            require(all(row[arm][k] == trace[f"{prefix}_{k}"] for k in ("observed", "correct", "flagged")), key)
        if trace["outcome"] == "loss":
            losses.append(key)
            require(row["expected"] == row["before"]["observed"] == "" and row["after"]["observed"] is None
                    and not row["critical"], f"Loss has a different explanation at {key}")
        if trace["outcome"] == "unchanged_wrong" and row["before"]["observed"] != row["after"]["observed"]:
            changed_wrong.append(key)
        _, page, _, _, _, table_row, _, _ = key.split("/")
        half = "first" if int(page) <= (2 if family == "H" else 30) else "second"
        for grouping, name in ((by_half, half), (by_row, table_row)):
            count = grouping.setdefault(name, {"reference": 0, "original_wrong": 0})
            count["reference"] += 1
            count["original_wrong"] += int(not row["before"]["correct"])
    return dict(pairedLedgerSha256=hashlib.sha256(pair_bytes).hexdigest(),
                traceLedgerSha256=hashlib.sha256(word_bytes).hexdigest(),
                joinedCells=len(score_rows), invariantLines=len(locations)-len(score_rows),
                before=summary["counts_before"], after=summary["counts_after"], transitions=summary["transitions"],
                originalWrongFirstDivergence=attribution, blankToAbsentLosses=losses,
                changedObservationStillWrong=changed_wrong, positionByDocumentHalf=by_half, positionByTableRow=by_row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pair_revision")
    parser.add_argument("word_revision")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = {"pairEvidenceRevision": args.pair_revision, "wordEvidenceRevision": args.word_revision,
              "denominators": "Each reference cell is keyed by packet and scorer location. Position counts include printed headers and explicit empty cells.",
              "families": {f: reconcile(f, args.pair_revision, args.word_revision) for f in ("H", "A")}}
    args.output.write_bytes((json.dumps(result, indent=2, ensure_ascii=True) + "\n").encode())


if __name__ == "__main__":
    main()
