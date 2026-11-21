"""Audit frozen predictions against source words and a separate reader replay."""
import argparse
from hashlib import sha256
import json
from pathlib import Path


def inspect(document, rows):
    lines = {(p["page"], i): line["words"] for p in document["pages"]
             for i, line in enumerate(p["lines"], 1)}
    source = {w["ref"]: w["text"] for words in lines.values() for w in words}
    positions = [(r["page"], r["line"]) for r in rows]
    assert positions == sorted(set(positions))
    # Under the input contract every nonempty line on the second page is a body line.
    assert [pos for pos in positions if pos[0] == 2] == [
        pos for pos, words in lines.items() if pos[0] == 2 and words
    ]
    for position, row in zip(positions, rows, strict=True):
        words = lines[position]
        assert row["words"] == [{"literal": w["text"], "word_ref": w["ref"]} for w in words]
        assert (row["literal"], row["word_ref"]) == (words[-1]["text"], words[-1]["ref"])
        for field in ("property", "unit"):
            banner = next(b for b in lines.values() if b and b[0]["ref"] == row[f"{field}_label_ref"])
            assert banner[0]["text"] == field.capitalize() + ":"
            assert row[f"{field}_refs"] == [w["ref"] for w in banner[1:]]
            assert row[field] == " ".join(w["text"] for w in banner[1:])
        if row["flagged"]:
            assert row["scope"] is None and row["column_role"] is None
            assert row["header_refs"] == [] and row["heading_refs"] == []
            assert row["stack_before"] == row["stack_after"]
        else:
            assert source[row["header_refs"][-1]] == row["column_role"] == "Amount"
            title = " ".join(source[ref] for ref in row["heading_refs"])
            assert title == {"parent": "Ledger", "child": "Contractor detail"}[row["scope"]]
    page2 = [r for r in rows if r["page"] == 2]
    return {
        "all_pages_amount_literals_and_refs_checked": len(rows),
        "all_pages_body_words_and_refs_checked": sum(len(r["words"]) for r in rows),
        "page2_observed_amounts": len(page2),
        "page2_observed_body_words": sum(len(r["words"]) for r in page2),
        "page2_bound": sum(not r["flagged"] for r in page2),
        "page2_flagged": sum(r["flagged"] for r in page2),
        "page2_emitted_scopes": [r["scope"] for r in page2],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("replay", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("ids", nargs="+")
    args = parser.parse_args()
    results = []
    for item in args.ids:
        observed = (args.inputs / f"{item}.json").read_bytes()
        document = json.loads(observed)
        for mode in ("grid", "grid-words"):
            name = Path(mode) / f"{item}.json"
            original = (args.predictions / name).read_bytes()
            assert original == (args.replay / name).read_bytes()
            results.append({
                "id": item, "mode": mode, "source_sha256": sha256(observed).hexdigest(),
                "prediction_sha256": sha256(original).hexdigest(), "replay_equal": True,
                **inspect(document, json.loads(original)["rows"]),
            })
    with args.output.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(results, output, indent=2)
        output.write("\n")


if __name__ == "__main__":
    main()
