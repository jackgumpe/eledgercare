"""Finite, constructed checks for the amendment. Stdlib only. No reader or OCR."""
import argparse
import copy
from fractions import Fraction as Q
from itertools import product
import json
from math import comb
from pathlib import Path
import struct
import subprocess

BASE = "a0bf6122d082675d483ffd9aeb7f4dbedbfb174c"


def private_calls():
    def advance(h, st):
        # Deliberately mutate a private toy cache so inadvertent reuse is observable.
        st["values"].append(h)
        st["tok"] += 1
        return h + 1, st

    origin = {"values": [0] * 31, "tok": 30}
    pinned = copy.deepcopy(origin)
    h1, s1 = advance(0, copy.deepcopy(origin))
    dup_h, dup_s = advance(0, copy.deepcopy(origin))
    h2, s2 = advance(h1, copy.deepcopy(origin))
    assert (h1, s1) == (dup_h, dup_s) and origin == pinned
    assert len(s1["values"]) == len(s2["values"]) == 32 and s1 != s2
    assert len({id(st["values"]) for st in (origin, s1, dup_s, s2)}) == 4
    shared = copy.deepcopy(origin)
    bad_h, _ = advance(0, shared)
    advance(bad_h, shared)
    bad_len = len(shared["values"])
    shared["values"].pop()
    assert bad_len == 33 and shared["tok"] == 32 != s1["tok"]
    # Both h=1,2 emit A now; at the next step the stored value decides the score.
    now = [int(h > 2) for h in (h1, h2)]
    later = [st["values"][-1] for st in (s1, s2)]
    assert now == [0, 0] and later == [0, 1]
    assert 0.0 == -0.0 and struct.pack("<f", 0.0) != struct.pack("<f", -0.0)
    inputs = ["opening-last", "1", "7", ".00"]
    pred = ["1", "7", ".00", "close"]
    assert inputs[1:] == pred[:-1] and len(pred) == 4
    return {"private_lengths": [len(s["values"]) for s in (s1, dup_s, s2)], "origin_length": 31,
            "in_place_length": bad_len, "correct_tok": s1["tok"], "after_trim_wrong_tok": shared["tok"],
            "same_current_ids": now, "later_different_ids": later, "signed_zero_hex_f32":
            [struct.pack("<f", x).hex() for x in (0.0, -0.0)], "illustrative_input_to_prediction": list(zip(inputs, pred))}


def scores():
    old, new = [Q("1.40"), Q("1.00")], [Q("1.25"), Q("1.30")]
    delta = [y - x for x, y in zip(old, new)]
    lead = old[0] - old[1]
    rel = delta[1] - delta[0]
    assert (lead, rel, rel - lead) == (Q(2, 5), Q(9, 20), Q(1, 20))
    comparisons = 0
    protected = 0
    for z in product(range(-2, 3), repeat=3):
        if z.count(max(z)) != 1:
            continue
        a = z.index(max(z))
        for d in product(range(-2, 3), repeat=3):
            out = [x + dx for x, dx in zip(z, d)]
            rivals = [i for i in range(3) if i != a]
            for j in rivals:
                gap = z[a] - z[j]
                swing = d[j] - d[a]
                assert (swing > gap) == (out[j] > out[a])
                assert (swing == gap) == (out[j] == out[a])
                comparisons += 1
            if min(z[a] - z[j] for j in rivals) > 2 * max(map(abs, d)):
                assert out.index(max(out)) == a and out.count(max(out)) == 1
                protected += 1
    tie = [1, 1]
    assert tie.index(max(tie)) == 0
    # On equality at m=2 epsilon, lower token ID from each arrangement wins.
    assert [2 - 1, 0 + 1] == tie == [0 + 1, 2 - 1]
    # Strict pairwise overtake alone does not make this rival the final winner.
    assert [0, 1, 2].index(max([0, 1, 2])) == 2
    # Squared Cauchy-Schwarz in exact arithmetic. Equality example (3,4),(6,8).
    vecs = list(product(range(-2, 3), repeat=2)) + [(3, 4), (6, 8)]
    for w, u in product(vecs, repeat=2):
        dot = sum(x*y for x, y in zip(w, u))
        assert dot**2 <= sum(x*x for x in w) * sum(y*y for y in u)
    assert 3*6 + 4*8 == 5*10
    return {"worked_lead_delta_relative_new_rival_lead": list(map(str, [lead, *delta, rel, rel - lead])),
            "strict_overtake_and_equality_pair_checks": comparisons, "protected_winner_checks": protected,
            "geometric_checks": len(vecs)**2, "geometric_equality": 50,
            "epsilon_boundary": {"before": [[2, 0], [0, 2]], "after": tie, "selected": 0}}


def paired():
    labels = ["C", "W", "A"]
    # A complete table with R=3,G=1 and N=10; illustrative and not collected data.
    table = [[3, 1, 0], [2, 1, 1], [1, 1, 0]]
    delta_by_pair = {}
    numerator = 0
    for i, j in product(range(3), repeat=2):
        effect = int(j == 0) - int(i == 0)
        delta_by_pair[labels[i] + labels[j]] = effect
        numerator += effect * table[i][j]
    n = sum(map(sum, table))
    r = table[1][0] + table[2][0]
    g = table[0][1] + table[0][2]
    assert (n, r, g, numerator) == (10, 3, 1, r - g) and Q(numerator, n) == Q(1, 5)
    def effect(rows):
        if not rows:
            return None
        return Q(sum(int(y == "C") - int(x == "C") for x, y in rows), len(rows))
    assert effect([]) is None and effect([("C", "A"), ("W", "W")]) == -Q(1, 2)
    d = r + g
    tail = Q(sum(comb(d, k) for k in range(r, d + 1)), 2**d)
    assert tail == Q(5, 16)
    return {"order": labels, "synthetic_counts": table, "all_nine_contributions": delta_by_pair, "N": n,
            "R": r, "G": g, "D": d, "delta": str(Q(r-g, n)), "one_sided_null_tail": str(tail),
            "empty_N_delta": effect([]), "D0_directional_evidence": False}


def ledger():
    path = "docs/coordination/WP-0038/results/named.jsonl"
    rows = subprocess.check_output(["git", "show", f"{BASE}:{path}"]).splitlines()
    case, = [r for row in rows if (r := json.loads(row))["id"] == "C9b" and r["variant"] == "trusted"]
    obs = case["observed"]
    columns = {"A1": obs["amounts"][0], "B1": obs["balances"][-1], "T": obs["total"]}
    ledgers = [dict(columns) for _ in case["answer"]["finite"]]
    for candidate, changes in zip(ledgers, case["answer"]["finite"]):
        for key, error in changes:
            candidate[key] -= error
    aliases = [c["A1"] for c in ledgers]
    dist = [int(a != 11) for a in aliases]
    assert aliases == [11, 1, 17] and dist == [0, 1, 1]
    def hamming(x, y):
        return sum(a != b for a, b in zip(x, y, strict=True))
    triples = list(product((0, 1), repeat=3))
    for x, y, read in product(triples, repeat=3):
        assert hamming(x, y) <= hamming(x, read) + hamming(read, y)
        if hamming(x, y) >= 3:
            assert max(hamming(x, read), hamming(y, read)) > 1
    assert hamming((0, 0), (0, 1)) == hamming((1, 1), (0, 1)) == 1
    return {"C9b_candidates": ledgers, "one_field_read": 11, "distance": dist,
            "binary_three_coordinate_triples_checked": len(triples)**3,
            "distance_two_counterexample": {"centers": ["00", "11"], "read": "01"}}


def costs():
    def diff(a, b, c, p):
        return a + p*b - p*c
    a, b, c = 2, 3, 11
    worked = {str(p): str(diff(a, b, c, p)) for p in (Q(1,10), Q(1,4), Q(1,2))}
    assert worked == {"1/10": "6/5", "1/4": "0", "1/2": "-2"}
    checks = 0
    for a, b, c, k in product(range(5), range(5), range(5), range(11)):
        p = Q(k, 10)
        saving = diff(a, b, c, p) < 0
        assert saving == (c > b and p > Q(a, c-b))
        checks += 1
    return {"loop_minus_crop_ms_per_page": worked, "p_break_even": "1/4", "checks": checks}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = {"scope": "Constructed exact arithmetic and C9b archived candidate reconstruction only.",
              "toy_state": private_calls(), "scores": scores(), "paired": paired(),
              "ledger": ledger(), "costs": costs()}
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"All constructed examples passed; wrote {args.out.name}.")
