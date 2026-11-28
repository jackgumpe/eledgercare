"""Archive and finite recomputation for WP-0046 (reviewer tool, independent of check.py).

Part A recomputes, from the pinned source extracts, every quantity printed by the
supplied checker, using separately written code. Part B derives the archived
page masks from guard state with the Edition 02.1 A2 page rule. Part C runs
exhaustive finite checks of Theorem 3, Theorem 5 and the erasure bound.
Usage: python -I archive_checks.py BUNDLE_DIR
"""
import itertools as it
import json
import struct
import sys
from pathlib import Path

NINF = 0xFF800000


def subsets(xs):
    return [c for n in range(len(xs) + 1) for c in it.combinations(xs, n)]


def decodable(sig, truth, chosen):
    seen = {}
    for s, t in zip(sig, truth):
        seen.setdefault(tuple(s[j] for j in chosen), set()).add(t)
    return all(len(v) == 1 for v in seen.values())


def hits(sig, truth, chosen):
    return all(any(sig[a][j] != sig[b][j] for j in chosen)
               for a, b in it.combinations(range(len(sig)), 2) if truth[a] != truth[b])


def main(bundle):
    B = Path(bundle)
    load = lambda n: json.loads((B / "sources" / n).read_text(encoding="utf-8"))
    out = {}
    # Part A: the checker's six lines, recomputed.
    d45, w45, h43, p43, g42 = (load(n) for n in ("disposition45.json", "windows45.json", "native43.json", "plan43.json", "design42.json"))
    reg = json.loads((B / "register.json").read_text(encoding="utf-8"))["groups"]
    cov = [w45["venv_field_coverage_author"]["0"]] + list(w45["venv_field_coverage_reviewer"]["0"].values())
    rows = h43["retained_rows"]
    out["A_sources"] = {"genuine": sum(d45["direct_launch"]["live_genuine_passed_by_route"]),
                        "denominators": [sum(c.values()) for c in cov],
                        "denominators_equal_across_arms": w45["venv_field_coverage_author"]["0"] == w45["venv_field_coverage_author"]["1"]
                        and w45["venv_field_coverage_reviewer"]["0"] == w45["venv_field_coverage_reviewer"]["1"],
                        "copies": sum(len(r["copies"]) for r in rows),
                        "score_bytes": sum(c["copy_bytes"] for r in rows for c in r["copies"]),
                        "design_bridges_and_calls": [g42["future_obligations"]["linked_bridges"], g42["future_obligations"]["private_block_calls"]]}
    out["A_register"] = {"entries": len(reg), "model": sum(r["key"].startswith("static.model.") for r in reg),
                         "dist": sum(r["key"].startswith("static.dist.") for r in reg),
                         "phase_slots": sum(r["key"].startswith("native.14") for r in reg)}
    sig = [(0, 0, 0), (1, 1, 0), (0, 1, 1), (1, 0, 1)]
    truth, cost = [1, 0, 0, 0], [2, 3, 2]
    n_ident, agree = 0, 0
    feas = []
    for ch in subsets(range(3)):
        n_ident += 1; agree += decodable(sig, truth, ch) == hits(sig, truth, ch)
        if hits(sig, truth, ch):
            feas.append((sum(cost[j] for j in ch), ch))
    cube = list(it.product((0, 1), repeat=2))
    for lab in it.product((0, 1), repeat=4):
        for ch in subsets(range(2)):
            n_ident += 1; agree += decodable(cube, lab, ch) == hits(cube, lab, ch)
    best = min(c for c, _ in feas)
    out["A_T7"] = {"identification_checks": n_ident, "theorem5_agreements": agree, "min_cost": best,
                   "minimizers": [list(s) for c, s in feas if c == best], "feasible": sorted([c, list(s)] for c, s in feas)}
    words = [0, 0x80000000, 0x3F800000, 0xFF7FFFFF]
    n_comp = 0
    for raw in it.product(words, repeat=2):
        for a, b in it.product(subsets([0, 1]), repeat=2):
            z1 = [NINF if i in a else x for i, x in enumerate(raw)]
            z2 = [NINF if i in b else x for i, x in enumerate(z1)]
            assert z2 == [NINF if i in set(a) | set(b) else x for i, x in enumerate(raw)]
            n_comp += 1
    out["A_T5_compositions"] = n_comp
    out["A_verdict_combinations"] = len(list(it.product("PUM", repeat=4)))

    # Part B: archived page masks derived from guard state (A2 page rule).
    s41 = load("source41.json")
    eos = s41["configuration"]["generation_config"]["eos_token_id"]  # post-freeze path correction
    page_id = s41["configuration"]["sparse_config"]["page_token_id"]
    vocab = s41["configuration"]["vocabulary_logits"]
    f07 = next(f for f in p43["fixtures"] if f["family_id"] == "F07")
    e, cap = f07["page_count"], p43["input_options"]["fixed_kwargs"]["max_page_tokens"]

    def page_mask(m, l):
        if e <= 0:
            return "permit all"
        if m > e:
            return "only EOS"
        if 0 < cap <= l:
            return "only PAGE" if m < e else "only EOS"
        if m < e:
            return "ban EOS"
        return "permit all"

    rb = []
    for r in rows:
        g = r["final_page_guard"]
        rule = page_mask(g["marker_cum"], g["page_len"])
        raw = bytes.fromhex(r["raw_eos_fp32le"]); post = bytes.fromhex(r["post_page_eos_fp32le"])
        first = next(i for i in range(4) if raw[i] != post[i])
        rb.append({"position": r["position"], "derived_page_rule": rule,
                   "derived_D2_equals_observed_effect": rule == "ban EOS" and r["c2_differs_from_c1_at_token_ids"] == [eos],
                   "post_page_eos_is_N": struct.unpack("<I", post)[0] == NINF,
                   "raw_eos_decodes": struct.unpack("<f", raw)[0] == r["raw_eos_value"],
                   "first_dense_difference_byte": 4 * eos + first == r["first_dense_difference_c0_to_c2"],
                   "guard_advanced_one": g["scanned"] == r["entry_page_guard"]["scanned"] + 1,
                   "emission_is_final_top": r["final_top_two"]["id"] == r["actual_emission"],
                   "margin": r["final_top_two"]["value"] - r["final_top_two"]["runner_up_value"] == r["final_top_two"]["difference"],
                   "copy_bytes_equal_vocab_words": all(c["copy_bytes"] == 4 * vocab for c in r["copies"]),
                   "layer11_entry_exit": [r["entry_cache_lengths"][11], r["exit_cache_lengths"][11]]})
    out["B_archive_rows"] = {"eos_id": eos, "page_id": page_id, "expected_pages": e, "page_cap": cap, "rows": rb,
                             "D1_derivation": "not derivable from the bundle: the no-repeat history is absent; c0_identical_c1 is effect-only evidence"}

    # Part C: exhaustive finite checks.
    W = [0, 0x80000000, 0x3F800000, 0x7FC00000]
    Wp = W + [NINF]
    passed = converse = n = 0
    for z0 in it.product(W, repeat=2):
        for z1 in it.product(Wp, repeat=2):
            for z2 in it.product(Wp, repeat=2):
                for D1, D2 in it.product(subsets([0, 1]), repeat=2):
                    n += 1
                    ok1 = all(z1[j] == (NINF if j in D1 else z0[j]) for j in range(2))
                    ok2 = all(z2[j] == (NINF if j in D2 else z1[j]) for j in range(2))
                    closed = all(z2[j] == (NINF if j in set(D1) | set(D2) else z0[j]) for j in range(2))
                    if ok1 and ok2:
                        passed += 1
                        assert closed
                    elif closed:
                        converse += 1
    out["C_theorem3"] = {"cases": n, "both_transitions_pass": passed, "closed_form_with_a_failed_transition": converse}
    n5 = a5 = 0
    for lab in it.product((0, 1), repeat=8):
        cube3 = list(it.product((0, 1), repeat=3))
        for ch in subsets(range(3)):
            n5 += 1; a5 += decodable(cube3, lab, ch) == hits(cube3, lab, ch)
    out["C_theorem5_3bit"] = {"checks": n5, "agree": a5}
    ne = ae = 0
    universe = list(it.product((0, 1), repeat=3))
    for table in it.combinations(universe, 4):
        for lab in it.product((0, 1), repeat=4):
            if len(set(lab)) < 2:
                continue
            for ch in subsets(range(3)):
                for f in (0, 1, 2):
                    pairs = [(a, b) for a, b in it.combinations(range(4), 2) if lab[a] != lab[b]]
                    robust = all(any(table[a][j] != table[b][j] for j in ch if j not in er)
                                 for k in range(min(f, len(ch)) + 1) for er in it.combinations(ch, k) for a, b in pairs)
                    dist = min(sum(table[a][j] != table[b][j] for j in ch) for a, b in pairs)
                    ne += 1; ae += robust == (dist >= f + 1)
    out["C_erasure_bound"] = {"checks": ne, "agree": ae}
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1])
