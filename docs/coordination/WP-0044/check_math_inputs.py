"""Recompute the four frozen numerical fixture inputs without either route's scorer."""
import json
import struct
import subprocess
from fractions import Fraction
from hashlib import sha256

FIXTURE = "40eb491db2330a70fb2203f721ce921f79fa03a9"
PREFIX = FIXTURE + ":docs/fixtures/WP-0044/"


def blob(path):
    return subprocess.check_output(["git", "show", PREFIX + path])


def winners(scores):
    peak = max(scores.values())
    return sorted(i for i, score in scores.items() if score == peak)


def margin(query):
    baseline = {i: Fraction(v) for i, v in query["scores"]}
    change = {i: Fraction(v) for i, v in query["delta"]}
    assert baseline.keys() == change.keys()
    after = {i: v + change[i] for i, v in baseline.items()}
    top = winners(after)
    old = winners(baseline)[0]
    remaining = [v for i, v in after.items() if i != old]
    return {"original_winner": old, "winner": top[0], "tied_maxima": top,
            "gap_before": str(baseline[old] - max(v for i, v in baseline.items() if i != old)),
            "old_winner_margin_after": str(after[old] - max(remaining)),
            "score_changes": {i: str(v) for i, v in change.items()},
            "oscillation": str(max(change.values()) - min(change.values()))}


def zero(query):
    words = [bytes.fromhex(x) for x in query["words_le"]]
    scores = {i: struct.unpack("<f", word)[0] for i, word in enumerate(words)}
    top = winners(scores)
    return {"byte_equal": words[0] == words[1], "numeric_equal": scores[0] == scores[1],
            "words_le": [x.hex() for x in words], "tie_winner": top[0], "tied_maxima": top}


def linked(data):
    def run(reset, write):
        state = Fraction(data["q0"])
        outputs = []
        for _ in range(data["steps"]):
            scores = {i: Fraction(b) + state * Fraction(m)
                      for i, b, m in zip(data["support"], data["base"], data["slope"], strict=True)}
            outputs.append(winners(scores)[0])
            state = Fraction(data["q0"] if reset else write)
        return outputs
    return {"stock": run(False, data["stock_write"]), "reset": run(True, data["private_write"]),
            "linked": run(False, data["private_write"])}


def main():
    manifest = json.loads(blob("manifest.json"))
    results = {}
    for row in manifest["rows"]:
        if row["interface"] != "mathematical":
            continue
        meta = row["input"]
        raw = blob(meta["path"])
        if sha256(raw).hexdigest() != meta["sha256"]:
            raise ValueError(meta["path"])
        item = json.loads(raw)
        assert item["tie_rule"] == "first_index"
        if item["schema"] == "wp0044.margin.v1":
            measured = [margin(q) for q in item["queries"]]
        elif item["schema"] == "wp0044.fp32.v1":
            measured = [zero(q) for q in item["queries"]]
        elif item["schema"] == "wp0044.linked.v1":
            measured = linked(item)
        else:
            raise ValueError(item["schema"])
        results[row["id"]] = {"input_sha256": meta["sha256"], "observed": measured}
    print(json.dumps({"fixture_commit": FIXTURE, "rows": results}, indent=2))


if __name__ == "__main__":
    main()
