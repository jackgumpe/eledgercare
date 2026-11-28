"""Amended r1 stdlib offline control evaluator for WP-0046 Stage 0 post-opening exchange.

Standard library only. Operates strictly on inert constructed JSON records.
Performs zero model/torch/stock imports, zero subprocess launches, zero host probes,
zero device access, and zero network I/O.

Supports TWO suites without modifying either frozen input file:
  1. Owner's frozen Turn-1 constructed suite (`--cases docs/research/WP-0046/control_cases.json`).
  2. Peer's frozen label-free challenge suite (`--claude-cases <path> [--claude-expected <path>]`),
     evaluating all 10 families (`record`, `compare`, `minimal`, `inventory`, `phase`,
     `join`, `gate12`, `ident`, `layout`, `linked`) independently from first principles
     under BOTH `--mode paper-r1-strict` (matching Paper I rev. 1 literal domain on P3/L3)
     and `--mode amended-r1` (enforcing M-05 unconditional X_oob on P3 and M-06 empty-view
     offset bound 0 <= b*o <= capacity on L3, plus M-04 cycle M_integrity in minimal).

Usage:
    python -I -B docs/research/WP-0046/controls_r1.py --cases docs/research/WP-0046/control_cases.json
    python -I -B docs/research/WP-0046/controls_r1.py --claude-cases <cases.json> --claude-expected <expected.json>
"""
from __future__ import annotations

import argparse
from collections import Counter
import itertools as it
import json
from pathlib import Path
from struct import pack, unpack
import sys
from typing import Any

NINF = 0xFF800000
UNOBSERVED = "?"
STAGE0_SOURCE_PIN = "e43af2e263f55478d1d551a5a095536b042589c2"


def strict_equal(a: Any, b: Any) -> bool:
    """Strict typed JSON equality: bool != int (False != 0, True != 1)."""
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(strict_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(strict_equal(a[k], b[k]) for k in a)
    return a == b


def canon_typed(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"))


def is_tagged(val: Any) -> bool:
    return isinstance(val, dict) and val.get("state") in ("present", "absent", "unobserved")


def check_strict_partial_order(nodes: set[str], edges: list[list[str]]) -> tuple[bool, str | None]:
    """Verify edges define an irreflexive, acyclic strict relation."""
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    for pair in edges:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2 or not all(isinstance(x, str) for x in pair):
            return False, "malformed_order_edge"
        u, v = pair
        if u == v:
            return False, f"reflexive_order_edge:{u}"
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set())
    indeg = {n: 0 for n in adj}
    for u, nbrs in adj.items():
        for v in nbrs:
            indeg[v] += 1
    queue = [n for n, d in indeg.items() if d == 0]
    visited = 0
    while queue:
        cur = queue.pop()
        visited += 1
        for nxt in adj[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if visited != len(adj):
        return False, "cyclic_order_relation"
    return True, None


def strict_minimal(events: set[str], edges: list[list[str]]) -> list[str]:
    """Minimal elements under transitive closure of strict order edges."""
    if not events:
        return []
    adj: dict[str, set[str]] = {}
    for u, v in edges:
        adj.setdefault(u, set()).add(v)
    ancestors: dict[str, set[str]] = {}
    for start in adj:
        seen: set[str] = set()
        stack = list(adj.get(start, ()))
        while stack:
            cur = stack.pop()
            if cur not in seen:
                seen.add(cur)
                stack.extend(adj.get(cur, ()))
        for target in seen:
            ancestors.setdefault(target, set()).add(start)
    return sorted(e for e in events if not (ancestors.get(e, set()) & events))


def ranked_minimal(keys: set[str], rank: dict[str, int | None]) -> list[str]:
    """Minimal elements under a < b iff both ranks are ints and rank[a] < rank[b]."""
    out = []
    for k in keys:
        rk = rank.get(k)
        if rk is None or not any(
            rank.get(a) is not None and type(rank[a]) is int and rank[a] < rk for a in keys
        ):
            out.append(k)
    return sorted(out)


# =============================================================================
# PART 1: Peer Challenge Families (10 families, independent first-principles impl)
# =============================================================================

def eval_claude_record(inp: dict[str, Any]) -> dict[str, Any]:
    """T8 Eq. (11) amended: plan-wide X_static(all), scoped Pi_s bindings, visible deferred_unbound."""
    stage = inp["stage"]
    scope = inp["binding_scope"]  # "whole_plan" or "due_only"
    X: set[str] = set()
    U: set[str] = set()
    deferred: set[str] = set()
    deferred_unbound: set[str] = set()
    atoms_out: dict[str, list[str]] = {}
    ranks: dict[str, int | None] = {}

    for atom in inp["atoms"]:
        k = atom["key"]
        due = atom["due"]
        pres = atom["prescriptions"]
        obs = atom["observed"]
        ranks[k] = atom.get("rank")
        tags: set[str] = set()

        # 1. Static binding & plan-wide intersection BEFORE deferral
        is_unbound = (pres == UNOBSERVED) or (not pres) or any(p == UNOBSERVED for p in pres)
        known_sets = (
            []
            if pres == UNOBSERVED
            else [{canon_typed(v) for v in p} for p in pres if p != UNOBSERVED]
        )
        inter = set.intersection(*known_sets) if known_sets else None
        if inter is not None and len(inter) == 0:
            X.add(k)
            tags.add("static_conflict")

        if is_unbound:
            if due > stage:
                deferred_unbound.add(k)
            if scope == "whole_plan" or due <= stage:
                U.add(k)
                tags.add("unbound")
            else:
                tags.add("unbound_deferred")

        # 2. Due-stage runtime observation vs deferral
        if due > stage:
            deferred.add(k)
            tags.add("deferred")
        elif obs == UNOBSERVED:
            U.add(k)
            tags.add("missing")
        elif isinstance(obs, dict) and "failed" in obs:
            X.add(k)
            tags.add("failed")
        elif inter is not None and canon_typed(obs) not in inter:
            X.add(k)
            tags.add("conflict")

        if not tags:
            tags.add("pass")
        atoms_out[k] = sorted(tags)

    verdict = "M" if X else "U" if U else "P"
    return {
        "verdict": verdict,
        "X": sorted(X),
        "U": sorted(U),
        "deferred": sorted(deferred),
        "deferred_unbound": sorted(deferred_unbound),
        "minX": ranked_minimal(X, ranks),
        "minXU": ranked_minimal(X | U, ranks),
        "atoms": atoms_out,
    }


def eval_claude_compare(inp: dict[str, Any]) -> dict[str, Any]:
    """T4 Eq. (6) first-matching-case precedence + typed ABSENT vs empty vs ?."""
    J, x, y = inp["J"], inp["x"], inp["y"]
    if J is False:
        return {"result": "incomparable"}
    if J == UNOBSERVED or x == UNOBSERVED or y == UNOBSERVED:
        return {"result": "unobserved"}
    return {"result": "same" if canon_typed(x) == canon_typed(y) else "different"}


def eval_claude_minimal(inp: dict[str, Any], *, check_order_integrity: bool = False) -> dict[str, Any]:
    """T4 minimal frontier over transitive closure of strict order edges (D6)."""
    events = set(inp["events"])
    edges = [list(p) for p in inp["precedes"]]
    if check_order_integrity:
        ok, err = check_strict_partial_order(events, edges)
        if not ok:
            return {"minimal": ["order.integrity"], "order_integrity_error": err}
    return {"minimal": strict_minimal(events, edges)}


def eval_claude_inventory(inp: dict[str, Any]) -> dict[str, Any]:
    """T3a amended M3: three-valued conjunct-wise evaluation, unique physical bindings, ordered projection."""
    E, I, R = inp["E"], inp["I"], inp["R"]
    X: set[str] = set()
    U: set[str] = set()

    if E == UNOBSERVED:
        U.add("schema")
    else:
        for k, c in Counter(E).items():
            if c > 1:
                X.add(f"schema.duplicate:{k}")

    if I == UNOBSERVED:
        U.add("inventory")
    elif E != UNOBSERVED:
        ce, ci = Counter(E), Counter(I)
        for k in ce:
            if ce[k] > ci[k]:
                X.add(f"omit:{k}")
        for k in ci:
            if ci[k] > ce[k]:
                X.add(f"extra:{k}")

    if R == UNOBSERVED:
        U.add("read")
    elif I != UNOBSERVED:
        ci, cr = Counter(I), Counter(R)
        for k in ci:
            if ci[k] > cr[k]:
                X.add(f"read.missing:{k}")
        for k in cr:
            if cr[k] > ci[k]:
                X.add(f"read.extra:{k}")
        if inp.get("ordered") and ci == cr and list(I) != list(R):
            X.add("order")

    if I != UNOBSERVED:
        members = [k for k in dict.fromkeys(I) if E == UNOBSERVED or k in E]
        for k in members:
            c = inp["custody"].get(k, UNOBSERVED)
            if c is False:
                X.add(f"custody:{k}")
            elif c is not True:
                U.add(f"custody:{k}")
        owners: dict[Any, list[str]] = {}
        for k in members:
            obj = inp["objects"].get(k, UNOBSERVED)
            if obj == UNOBSERVED:
                U.add(f"object:{k}")
            else:
                owners.setdefault(obj, []).append(k)
        for ks in owners.values():
            if len(ks) > 1:
                X.add("object.shared:" + "+".join(sorted(ks)))

    verdict = "M" if X else "U" if U else "P"
    return {"verdict": verdict, "X": sorted(X), "U": sorted(U)}


def _f32_from_u32(word: int) -> float:
    return unpack(">f", pack(">I", word))[0]


def _is_finite_u32(word: int) -> bool:
    return (word & 0x7F800000) != 0x7F800000


def eval_claude_phase(inp: dict[str, Any], *, include_unconditional_oob: bool = False) -> dict[str, Any]:
    """T5 Eq. (8) phase-local transitions + P7 Reading B + optional M-05 unconditional X_oob."""
    z = [[int(w, 16) for w in inp[name]] for name in ("z0", "z1", "z2")]
    n = len(z[0])
    if len(z[1]) != n or len(z[2]) != n:
        raise ValueError("vector length mismatch")
    masks = [None, set(inp["D1"]), set(inp["D2"])]
    X: list[str] = []
    U: list[str] = []

    for j in range(n):
        if not _is_finite_u32(z[0][j]):
            X.append(f"0/{j}")
    for p in (1, 2):
        for j in range(n):
            want = NINF if j in masks[p] else z[p - 1][j]
            if z[p][j] != want:
                X.append(f"{p}/{j}")

    allowed = [j for j in range(n) if j not in (masks[1] | masks[2])]
    if not allowed:
        X.append("supp")

    clean = len(X) == 0
    winner_candidate: int | None = None
    if clean:
        best_val = max(_f32_from_u32(z[2][j]) for j in allowed)
        winner_candidate = min(j for j in allowed if _f32_from_u32(z[2][j]) == best_val)

    y = inp["emitted"]
    if y == UNOBSERVED:
        # Reading B (convergent across both providers): missing emission always enters U.
        U.append("emission")
    else:
        if include_unconditional_oob and (type(y) is not int or y not in allowed):
            X.append("oob")
        if clean and y != winner_candidate:
            X.append("choice")

    verdict = "M" if X else "U" if U else "P"
    return {
        "verdict": verdict,
        "X": sorted(X),
        "U": sorted(U),
        "winner": winner_candidate if verdict == "P" else None,
    }


def eval_claude_join(inp: dict[str, Any]) -> dict[str, Any]:
    """T8a J5(r, R_cand) keyed on full 3-tuple (label, arm, pos) + Eq. (12) gate."""
    r = inp["run"]
    req = [tuple(k) for k in inp["required"]]
    keys = [(t["label"], t["arm"], t["pos"]) for t in inp["rows"]]
    cq, ck = Counter(req), Counter(keys)
    fmt = lambda k: f"{k[0]}/{k[1]}/{k[2]}"

    X: list[str] = []
    for k in cq:
        if cq[k] > ck[k]:
            X.append(f"keys:missing:{fmt(k)}")
    for k in ck:
        if ck[k] > cq[k]:
            X.append(f"keys:extra:{fmt(k)}")
    for t, k in zip(inp["rows"], keys):
        if t["run"] != r:
            X.append(f"run:{fmt(k)}")
        if t["bound"] is not True:
            X.append(f"bound:{fmt(k)}")
        if t["restorable"] is not True:
            X.append(f"restorable:{fmt(k)}")

    j5 = len(X) == 0
    cpr = bool(inp["P3"] and inp["D3"] and inp["stock"].get(r) == "P" and j5)
    return {"J5": j5, "considerPrivateReplay": cpr, "X": sorted(X)}


def eval_claude_gate12(inp: dict[str, Any]) -> dict[str, Any]:
    """T8a Eq. (12) amended M2: Stage-1 preflight to Stage-2 plan projection join."""
    pre, s2 = inp["preflight"], inp["stage2"]
    literal = bool(inp["P2"] and inp["D2"] and pre["verdict"] == "P")
    X = sorted(k for k in ("route", "env_schema", "source_pin") if pre.get(k) != s2.get(k))
    return {"literal_eq12": literal, "joined": literal and (len(X) == 0), "X": X}


def eval_claude_ident(inp: dict[str, Any]) -> dict[str, Any]:
    """T7 Theorem 5 weighted hitting set under coordinate erasures or correlated source erasures (K1-K3)."""
    sig, truth, cost, loss = inp["signatures"], inp["truth"], inp["costs"], inp["loss"]
    m = len(cost)
    pairs = [(a, b) for a, b in it.combinations(range(len(sig)), 2) if truth[a] != truth[b]]

    def erasure_patterns(S: tuple[int, ...]) -> list[set[int]]:
        if loss["type"] == "coordinate":
            return [
                set(e)
                for n in range(min(loss["f"], len(S)) + 1)
                for e in it.combinations(S, n)
            ]
        srcs = loss["sources"]
        return [
            set().union(*[srcs[i] for i in fail]) & set(S)
            for n in range(loss["f"] + 1)
            for fail in it.combinations(range(len(srcs)), n)
        ]

    feasible: list[tuple[int, list[int]]] = []
    for k in range(m + 1):
        for S in it.combinations(range(m), k):
            pats = erasure_patterns(S)
            if all(
                any(sig[a][j] != sig[b][j] for j in S if j not in er)
                for er in pats
                for a, b in pairs
            ):
                feasible.append((sum(cost[j] for j in S), list(S)))

    if not feasible:
        return {"infeasible": True, "min_cost": None, "argmin": []}
    best = min(c for c, _ in feasible)
    return {
        "infeasible": False,
        "min_cost": best,
        "argmin": sorted(S for c, S in feasible if c == best),
    }


def eval_claude_layout(inp: dict[str, Any], *, extend_empty_view: bool = False) -> dict[str, Any]:
    """T6 strided storage bound (L1-L3) with optional M-06 empty-view offset extension."""
    n, s, o, b, cap = inp["n"], inp["s"], inp["o"], inp["b"], inp["capacity"]
    if any(type(x) is not int for x in (*n, *s, o, b, cap)):
        return {"result": "outside_domain"}
    if len(n) != len(s) or any(x < 0 for x in n) or any(x < 0 for x in s) or o < 0 or b <= 0:
        return {"result": "outside_domain"}
    if any(x == 0 for x in n):
        if extend_empty_view:
            return {"result": 0 <= b * o <= cap}
        return {"result": "outside_domain"}
    return {"result": b * (1 + o + sum((ni - 1) * si for ni, si in zip(n, s))) <= cap}


def eval_claude_linked(inp: dict[str, Any]) -> dict[str, Any]:
    """T6 two-step hidden-cache counterexample (N1-N2)."""
    def argmax2(c: int) -> int:
        return min(range(2), key=lambda j: (-(1 - c, c)[j], j))

    native = argmax2(inp["cN"])
    private = argmax2(inp["cP"])
    compared = private if inp["bridge"] == "linked" else argmax2(inp["cN"])
    return {
        "native_y1": native,
        "private_y1": private,
        "compared_y1": compared,
        "verdict": "P" if compared == native else "M",
    }


def eval_claude_case(case: dict[str, Any], *, mode: str) -> dict[str, Any]:
    fam = case["family"]
    inp = case["input"]
    amended = mode == "amended-r1"
    if fam == "record":
        return eval_claude_record(inp)
    if fam == "compare":
        return eval_claude_compare(inp)
    if fam == "minimal":
        return eval_claude_minimal(inp, check_order_integrity=amended)
    if fam == "inventory":
        return eval_claude_inventory(inp)
    if fam == "phase":
        return eval_claude_phase(inp, include_unconditional_oob=amended)
    if fam == "join":
        return eval_claude_join(inp)
    if fam == "gate12":
        return eval_claude_gate12(inp)
    if fam == "ident":
        return eval_claude_ident(inp)
    if fam == "layout":
        return eval_claude_layout(inp, extend_empty_view=amended)
    if fam == "linked":
        return eval_claude_linked(inp)
    raise ValueError(f"Unknown peer challenge family: {fam}")


# =============================================================================
# PART 2: Owner Frozen Turn-1 Controls Suite Compatibility (delegates cleanly)
# =============================================================================

def run_owner_cases(cases_path: Path) -> dict[str, Any]:
    # Import sibling frozen Turn-1 controls cleanly by absolute path without mutating sys.path permanently
    import importlib.util

    ctrl_path = Path(__file__).resolve().parent / "controls.py"
    spec = importlib.util.spec_from_file_location("_wp46_turn1_controls", ctrl_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    bundle = json.loads(cases_path.read_text(encoding="utf-8"))
    results = []
    mismatches = []
    for case in bundle["cases"]:
        actual = mod.evaluate_case(case)
        expected = case.get("expected_return")
        matched = strict_equal(actual, expected) if expected is not None else None
        if matched is False:
            mismatches.append(case["case_id"])
        results.append(
            {
                "case_id": case["case_id"],
                "kind": case["kind"],
                "verdict": actual["verdict"],
                "matched_expected": matched,
                "result": actual,
            }
        )
    return {
        "schema": "wp0046-control-r1-self-results/1",
        "source_revision": STAGE0_SOURCE_PIN,
        "cases_total": len(results),
        "verdict_counts": dict(sorted(Counter(r["verdict"] for r in results).items())),
        "expected_matches": sum(1 for r in results if r["matched_expected"] is True),
        "expected_mismatches": len(mismatches),
        "mismatch_ids": mismatches,
        "results": results,
    }


def run_claude_suite(cases_path: Path, expected_path: Path | None) -> dict[str, Any]:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    expected_map = (
        json.loads(expected_path.read_text(encoding="utf-8"))["cases"]
        if expected_path is not None
        else None
    )

    out_modes: dict[str, Any] = {}
    for mode in ("paper-r1-strict", "amended-r1"):
        per_case: dict[str, Any] = {}
        agreements = 0
        diffs: list[dict[str, Any]] = []
        for c in cases:
            cid = c["id"]
            got = eval_claude_case(c, mode=mode)
            per_case[cid] = got
            if expected_map is not None:
                exp = expected_map[cid]
                if strict_equal(got, exp):
                    agreements += 1
                else:
                    diff_keys = sorted(k for k in (set(got) | set(exp)) if not strict_equal(got.get(k), exp.get(k)))
                    diffs.append({"id": cid, "diff_keys": diff_keys, "expected": exp, "got": got})
        out_modes[mode] = {
            "cases_evaluated": len(cases),
            "full_record_agreements_vs_peer_expected": agreements if expected_map is not None else None,
            "differences_vs_peer_expected": diffs if expected_map is not None else None,
            "cases": per_case,
        }

    return {
        "schema": "wp0046-control-r1-peer-eval/1",
        "source_revision": STAGE0_SOURCE_PIN,
        "peer_schema": "wp46-claude-challenges/1",
        "cases_total": len(cases),
        "modes": out_modes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute WP-0046 r1 offline controls on owner or peer constructed cases.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cases", type=Path, help="Path to owner constructed control_cases.json.")
    group.add_argument("--claude-cases", type=Path, help="Path to peer label-free challenges/cases.json.")
    parser.add_argument("--claude-expected", type=Path, default=None, help="Optional peer expectations/expected.json for comparison.")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output path.")
    args = parser.parse_args()

    if args.cases is not None:
        payload = run_owner_cases(args.cases)
        exit_code = 0 if payload["expected_mismatches"] == 0 else 1
    else:
        payload = run_claude_suite(args.claude_cases, args.claude_expected)
        strict = payload["modes"]["paper-r1-strict"]
        exit_code = 0
        if strict["full_record_agreements_vs_peer_expected"] is not None:
            if strict["full_record_agreements_vs_peer_expected"] != payload["cases_total"]:
                exit_code = 1

    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if args.out is not None:
        args.out.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(rendered)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
