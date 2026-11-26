"""Independent exact, synthetic and text checks. No model construction or device calls."""
import argparse
import hashlib
import itertools
import json
import subprocess
from collections import Counter
from copy import deepcopy
from fractions import Fraction as Q
from math import comb
from pathlib import Path

BASE = Path(__file__).resolve().parents[3]
PDF_HASH = "3f4451dd3a1bd2dc37d50c5ddb720dfd37005f62c1da68a6b2958aa86db14264"
RULE = BASE / "docs/coordination/WP-0041/handoff-rule.md"


def digest(content):
    return hashlib.sha256(content).hexdigest()


def rule_check(pdf, agreement):
    from pypdf import PdfReader

    assert digest(pdf.read_bytes()) == PDF_HASH
    pages = PdfReader(pdf).pages
    assert len(pages) == 9
    lines = pages[5].extract_text().splitlines()
    begin = next(i for i, line in enumerate(lines) if line.startswith("Every handoff that proposes"))
    end = lines.index("Revision and routing")
    paragraphs = []
    for line in lines[begin:end]:
        if not line.strip():
            continue
        if line.startswith(("Every handoff", "1. ", "2. ", "3. ", "4. ", "Apply the depth")):
            paragraphs.append(line)
        else:
            paragraphs[-1] += " " + line
    assert len(paragraphs) == 6
    reconstructed = "\n\n".join(paragraphs) + "\n"
    assert RULE.read_text(encoding="utf-8") == reconstructed
    result = {"rule_paragraphs": len(paragraphs), "text_sha256_utf8_lf": digest(reconstructed.encode())}
    if agreement:
        blob = subprocess.check_output(["git", "show", f"{agreement}:AGENTS.md"], cwd=BASE).decode()
        assert blob.split("\n\n").count(paragraphs[0]) == 1
        assert blob.count(reconstructed.rstrip("\n")) == 1
        result["agents_revision"] = agreement
    return result


def state_checks():
    def step(value, state):
        state["kv"].append(value)
        state["keys"].append(2 * value)
        state["rotation"][1] += 1
        return value + 1, state

    before = {"kv": [0] * 31, "keys": [0] * 31, "rotation": [0, 31]}
    snapshot = deepcopy(before)
    h1, once = step(4, deepcopy(before))
    assert (h1, once) == step(4, deepcopy(before))
    h2, twice = step(h1, deepcopy(before))
    assert (h1, h2) == (5, 6) and once != twice
    assert before == snapshot
    assert list(map(len, (once["kv"], twice["kv"]))) == [32, 32]
    broken = deepcopy(before)
    step(4, broken)
    step(h1, broken)
    assert len(broken["kv"]) == len(broken["keys"]) == broken["rotation"][1] == 33
    broken["kv"].pop()
    assert len(broken["kv"]) == 32 and broken["rotation"][1] == 33
    # Both readouts emit ID 0 at the first position; a future read can distinguish state.
    assert h1 > 0 and h2 > 0 and (once["kv"][-1] >= 5) != (twice["kv"][-1] >= 5)
    # Prefix counts include the final input opening token, which predicts amount piece 1.
    targets = ("1", "7", ".00", "</td>")
    assert list(zip((">", *targets[:-1]), targets))[-1] == (".00", "</td>")
    return {"private_lengths": [32, 32], "alias_length": 33, "calls_extra": len(targets),
            "prefix_fixture": "three amount pieces, one closing piece"}


def winner(scores):
    return max(range(len(scores)), key=scores.__getitem__)


def margin_checks():
    rows = list(itertools.product(range(-1, 2), repeat=3))
    paired = inequalities = 0
    for z1, z2 in itertools.product(rows, repeat=2):
        a = winner(z1)
        if z1.count(z1[a]) != 1:
            continue
        paired += 1
        delta = [q - p for p, q in zip(z1, z2)]
        rivals = [j for j in range(len(z1)) if j != a]
        margins = [z1[a] - z1[j] for j in rivals]
        for j, margin in zip(rivals, margins):
            change = delta[j] - delta[a]
            assert z2[a] - z2[j] == margin - change
            assert (change > margin) == (z2[j] > z2[a])
            assert (change == margin) == (z2[j] == z2[a])
            inequalities += 1
        if min(margins) > 2 * max(map(abs, delta)):
            assert z2.count(z2[a]) == 1 and winner(z2) == a
    z1 = (Q("1.40"), Q("1.00"))
    z2 = (Q("1.25"), Q("1.30"))
    assert (z2[1]-z1[1]) - (z2[0]-z1[0]) == Q(".45")
    assert z2[1] - z2[0] == Q(".05")
    assert [winner(z1), winner(z2)] == [0, 1]
    assert winner((0, 2)) == 1 and winner((1, 1)) == 0  # m = 2 epsilon
    assert winner((2, 0, 1)) == 0 and winner((0, 1, 2)) == 2  # overtaking rival 1 loses
    assert winner((3, 2)) == 0 and winner((-float("inf"), 2)) == 1  # changed mask
    # Cauchy-Schwarz, squared to retain exact integer arithmetic.
    vectors = list(itertools.product(range(-2, 3), repeat=2))
    for w, u in itertools.product(vectors, repeat=2):
        dot = sum(i*j for i, j in zip(w, u))
        assert dot**2 <= sum(i*i for i in w) * sum(j*j for j in u)
    return {"matched_pairs": paired, "pairwise_checks": inequalities, "raw_bound_examples": len(vectors)**2,
            "initial_lead": "2/5", "relative_gain": "9/20", "final_overtake": "1/20"}


def distance(left, right):
    assert len(left) == len(right)
    return sum(a != b for a, b in zip(left, right))


def recovery(trials):
    counts = Counter(trials)
    r = counts["W", "C"] + counts["A", "C"]
    g = counts["C", "W"] + counts["C", "A"]
    delta = Q(r-g, len(trials)) if trials else None
    assert r-g == sum(int(y == "C") - int(x == "C") for x, y in trials)
    return r, g, delta


def trial_checks():
    nine = list(itertools.product("CWA", repeat=2))
    assert recovery(nine) == (2, 2, 0) and recovery([]) == (0, 0, None)
    sample = [("W", "C")] * 2 + [("A", "C"), ("C", "A")] + [("W", "W")] * 6
    assert recovery(sample) == (3, 1, Q(1, 5))
    # Conditional sign test of the illustrative example for prespecified independent exchangeable signs.
    d = 4
    exact_p = Q(sum(comb(d, k) for k in range(3, d + 1)), 2**d)
    assert exact_p == Q(5, 16)
    assert [distance([11], [v]) for v in (11, 1, 17)] == [0, 1, 1]
    candidates = list(itertools.product(range(2), repeat=4))
    triples = 0
    for u, v, observation in itertools.product(candidates, repeat=3):
        if distance(u, v) >= 3:
            assert max(distance(u, observation), distance(v, observation)) > 1
            triples += 1
    assert distance("00", "01") == distance("11", "01") == 1
    assert distance("000", "110") == 2 and distance("111", "110") == 1
    return {"nine_transitions": {a+b: int(b=="C") - int(a=="C") for a,b in nine},
            "N10_R3_G1_delta": "1/5", "illustrative_sign_p": str(exact_p),
            "empty_denominator": None, "C9b_distances": [0,1,1], "disjoint_ball_triples": triples}


def compute_checks():
    def diff(a, p, b, c):
        return a + p*(b-c)
    comparisons = 0
    for a, b, c in itertools.product(range(4), repeat=3):
        for ticks in range(11):
            p = Q(ticks, 10)
            assert (diff(a, p, b, c) < 0) == (c > b and p > Q(a, c-b))
            comparisons += 1
    differences = [diff(2, p, 3, 11) for p in (Q(1,10), Q(1,4), Q(1,2))]
    assert differences == [Q(6,5), 0, -2]
    assert diff(9, 1, 3, 11) == 1
    return {"a2_b3_c11_at_p_.10_.25_.50": [str(x) for x in differences], "comparison_count": comparisons}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--agreement")
    args = parser.parse_args()
    print(json.dumps({"text": rule_check(args.pdf, args.agreement), "cache": state_checks(),
                      "margin": margin_checks(), "trial": trial_checks(), "cost": compute_checks()},
                     indent=2, sort_keys=True))
