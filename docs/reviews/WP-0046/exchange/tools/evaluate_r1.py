"""Reviewer evaluator revision r1 (correction R-01): order integrity for the 'minimal' family.
Loads the frozen tools/evaluate.py unchanged and overrides only 'minimal'.
Usage: python -I evaluate_r1.py CASES_R1.json OUT.json
"""
import importlib.util
import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "tools" / "evaluate.py"
spec = importlib.util.spec_from_file_location("evaluate_r0", SRC)
r0 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r0)


def minimal_r1(inp):
    pairs = [tuple(p) for p in inp["precedes"]]
    if any(a == b for a, b in pairs):
        return {"minimal": None, "order_integrity": "reflexive"}
    nodes = set(inp["events"]) | {x for p in pairs for x in p}
    succ = {n: {b for a, b in pairs if a == n} for n in nodes}
    state = {}

    def cyclic(n):
        state[n] = 1
        for m in succ[n]:
            if state.get(m) == 1 or (state.get(m) is None and cyclic(m)):
                return True
        state[n] = 2
        return False

    if any(state.get(n) is None and cyclic(n) for n in sorted(nodes)):
        return {"minimal": None, "order_integrity": "cyclic"}
    return {**r0.minimal(inp), "order_integrity": None}


def main(src, dst):
    cases = json.load(open(src, encoding="utf-8"))["cases"]
    fam = {**r0.FAMILIES, "minimal": minimal_r1}
    out = {c["id"]: fam[c["family"]](c["input"]) for c in cases}
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"schema": "wp46-claude-results-r1/1", "cases": out}, f, indent=1, sort_keys=True)
        f.write("\n")
    print(len(out), "r1 cases evaluated")


if __name__ == "__main__":
    main(*sys.argv[1:3])
