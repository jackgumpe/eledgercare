"""Independent reviewer evaluator for WP-0046 constructed challenges.

Standard library only. Implements the reviewer's reading of Paper I revision 1
(T3a, T4, T5, T6, T7, T8, T8a). It imports nothing from the supplied bundle.
Usage: python -I evaluate.py CASES.json OUT.json
"""
import itertools as it
import json
import struct
import sys
from collections import Counter

NINF = 0xFF800000
UNOBSERVED = "?"


def canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"))


def ranked_minimal(keys, rank):
    """Minimal elements under a < b iff both ranks are integers and rank[a] < rank[b]."""
    out = []
    for k in keys:
        rk = rank.get(k)
        if rk is None or not any(rank.get(a) is not None and rank[a] < rk for a in keys):
            out.append(k)
    return sorted(out)


def record(inp):
    stage, scope = inp["stage"], inp["binding_scope"]
    X, U, deferred, dunbound, atoms, rank = set(), set(), set(), set(), {}, {}
    for a in inp["atoms"]:
        k, due, pres, obs = a["key"], a["due"], a["prescriptions"], a["observed"]
        rank[k] = a.get("rank")
        st = set()
        unbound = pres == UNOBSERVED or not pres or any(p == UNOBSERVED for p in pres)
        known = [] if pres == UNOBSERVED else [set(canon(v) for v in p) for p in pres if p != UNOBSERVED]
        inter = set.intersection(*known) if known else None
        if inter is not None and not inter:
            X.add(k); st.add("static_conflict")
        if unbound:
            if due > stage:
                dunbound.add(k)
            if scope == "whole_plan" or due <= stage:
                U.add(k); st.add("unbound")
            else:
                st.add("unbound_deferred")
        if due > stage:
            deferred.add(k); st.add("deferred")
        elif obs == UNOBSERVED:
            U.add(k); st.add("missing")
        elif isinstance(obs, dict) and "failed" in obs:
            X.add(k); st.add("failed")
        elif inter is not None and canon(obs) not in inter:
            X.add(k); st.add("conflict")
        if not st:
            st.add("pass")
        atoms[k] = sorted(st)
    verdict = "M" if X else "U" if U else "P"
    return {"verdict": verdict, "X": sorted(X), "U": sorted(U), "deferred": sorted(deferred),
            "deferred_unbound": sorted(dunbound), "minX": ranked_minimal(sorted(X), rank),
            "minXU": ranked_minimal(sorted(X | U), rank), "atoms": atoms}


def compare(inp):
    J, x, y = inp["J"], inp["x"], inp["y"]
    if J is False:
        return {"result": "incomparable"}
    if J == UNOBSERVED or x == UNOBSERVED or y == UNOBSERVED:
        return {"result": "unobserved"}
    return {"result": "same" if canon(x) == canon(y) else "different"}


def minimal(inp):
    events, pairs = set(inp["events"]), {tuple(p) for p in inp["precedes"]}
    nodes = events | {x for p in pairs for x in p}
    closure = set(pairs)
    for m in nodes:  # Warshall transitive closure
        for a in nodes:
            for b in nodes:
                if (a, m) in closure and (m, b) in closure:
                    closure.add((a, b))
    return {"minimal": sorted(e for e in events if not any((a, e) in closure for a in events if a != e))}


def inventory(inp):
    E, I, R = inp["E"], inp["I"], inp["R"]
    X, U = set(), set()
    if E == UNOBSERVED:
        U.add("schema")
    else:
        for k, c in Counter(E).items():
            if c > 1:
                X.add("schema.duplicate:" + k)
    if I == UNOBSERVED:
        U.add("inventory")
    elif E != UNOBSERVED:
        ce, ci = Counter(E), Counter(I)
        X.update("omit:" + k for k in ce if ce[k] > ci[k])
        X.update("extra:" + k for k in ci if ci[k] > ce[k])
    if R == UNOBSERVED:
        U.add("read")
    elif I != UNOBSERVED:
        ci, cr = Counter(I), Counter(R)
        X.update("read.missing:" + k for k in ci if ci[k] > cr[k])
        X.update("read.extra:" + k for k in cr if cr[k] > ci[k])
        if inp.get("ordered") and Counter(I) == Counter(R) and list(I) != list(R):
            X.add("order")
    if I != UNOBSERVED:
        members = [k for k in dict.fromkeys(I) if E == UNOBSERVED or k in E]
        for k in members:
            c = inp["custody"].get(k, UNOBSERVED)
            if c is False:
                X.add("custody:" + k)
            elif c is not True:
                U.add("custody:" + k)
        owners = {}
        for k in members:
            o = inp["objects"].get(k, UNOBSERVED)
            if o == UNOBSERVED:
                U.add("object:" + k)
            else:
                owners.setdefault(o, []).append(k)
        X.update("object.shared:" + "+".join(sorted(ks)) for ks in owners.values() if len(ks) > 1)
    return {"verdict": "M" if X else "U" if U else "P", "X": sorted(X), "U": sorted(U)}


def fval(word):
    return struct.unpack(">f", word.to_bytes(4, "big"))[0]


def finite(word):
    return (word & 0x7F800000) != 0x7F800000


def phase(inp):
    z = [[int(w, 16) for w in inp[n]] for n in ("z0", "z1", "z2")]
    n = len(z[0])
    if not (len(z[1]) == len(z[2]) == n):
        raise ValueError("schema")
    masks = [None, set(inp["D1"]), set(inp["D2"])]
    X, U = [], []
    X += ["0/%d" % j for j in range(n) if not finite(z[0][j])]
    for p in (1, 2):
        for j in range(n):
            want = NINF if j in masks[p] else z[p - 1][j]
            if z[p][j] != want:
                X.append("%d/%d" % (p, j))
    A = [j for j in range(n) if j not in masks[1] | masks[2]]
    if not A:
        X.append("supp")
    clean = not X
    winner = None
    if clean:
        best = max(fval(z[2][j]) for j in A)
        w = min(j for j in A if fval(z[2][j]) == best)
    y = inp["emitted"]
    if y == UNOBSERVED:
        U.append("emission")
    elif clean and y != w:
        X.append("choice")
    verdict = "M" if X else "U" if U else "P"
    if verdict == "P":
        winner = w
    return {"verdict": verdict, "X": sorted(X), "U": sorted(U), "winner": winner}


def join(inp):
    r, req = inp["run"], [tuple(k) for k in inp["required"]]
    keys = [(t["label"], t["arm"], t["pos"]) for t in inp["rows"]]
    cq, ck = Counter(req), Counter(keys)
    fmt = lambda k: "%s/%s/%s" % k
    X = ["keys:missing:" + fmt(k) for k in cq if cq[k] > ck[k]]
    X += ["keys:extra:" + fmt(k) for k in ck if ck[k] > cq[k]]
    for t, k in zip(inp["rows"], keys):
        if t["run"] != r:
            X.append("run:" + fmt(k))
        if t["bound"] is not True:
            X.append("bound:" + fmt(k))
        if t["restorable"] is not True:
            X.append("restorable:" + fmt(k))
    j5 = not X
    cpr = bool(inp["P3"] and inp["D3"] and inp["stock"].get(r) == "P" and j5)
    return {"J5": j5, "considerPrivateReplay": cpr, "X": sorted(X)}


def gate12(inp):
    pre, s2 = inp["preflight"], inp["stage2"]
    literal = bool(inp["P2"] and inp["D2"] and pre["verdict"] == "P")
    X = sorted(k for k in ("route", "env_schema", "source_pin") if pre.get(k) != s2.get(k))
    return {"literal_eq12": literal, "joined": literal and not X, "X": X}


def ident(inp):
    sig, truth, cost, loss = inp["signatures"], inp["truth"], inp["costs"], inp["loss"]
    m = len(cost)
    pairs = [(a, b) for a, b in it.combinations(range(len(sig)), 2) if truth[a] != truth[b]]
    if loss["type"] == "coordinate":
        patterns = lambda S: [set(e) for n in range(min(loss["f"], len(S)) + 1) for e in it.combinations(S, n)]
    else:
        srcs = loss["sources"]
        patterns = lambda S: [set().union(*[srcs[i] for i in fail]) & set(S)
                              for n in range(loss["f"] + 1) for fail in it.combinations(range(len(srcs)), n)]
    feasible = []
    for n in range(m + 1):
        for S in it.combinations(range(m), n):
            ok = all(any(sig[a][j] != sig[b][j] for j in S if j not in er)
                     for er in patterns(S) for a, b in pairs)
            if ok:
                feasible.append((sum(cost[j] for j in S), list(S)))
    if not feasible:
        return {"infeasible": True, "min_cost": None, "argmin": []}
    best = min(c for c, _ in feasible)
    return {"infeasible": False, "min_cost": best, "argmin": sorted(S for c, S in feasible if c == best)}


def layout(inp):
    n, s, o, b, cap = inp["n"], inp["s"], inp["o"], inp["b"], inp["capacity"]
    if len(n) != len(s) or any(x <= 0 for x in n) or any(x < 0 for x in s) or o < 0 or b <= 0:
        return {"result": "outside_domain"}
    return {"result": b * (1 + o + sum((ni - 1) * si for ni, si in zip(n, s))) <= cap}


def linked(inp):
    arg = lambda c: min(range(2), key=lambda j: (-(1 - c, c)[j], j))
    native, private = arg(inp["cN"]), arg(inp["cP"])
    compared = private if inp["bridge"] == "linked" else arg(inp["cN"])
    return {"native_y1": native, "private_y1": private, "compared_y1": compared,
            "verdict": "P" if compared == native else "M"}


FAMILIES = {"record": record, "compare": compare, "minimal": minimal, "inventory": inventory,
            "phase": phase, "join": join, "gate12": gate12, "ident": ident, "layout": layout, "linked": linked}


def main(src, dst):
    cases = json.load(open(src, encoding="utf-8"))["cases"]
    out = {c["id"]: FAMILIES[c["family"]](c["input"]) for c in cases}
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"schema": "wp46-claude-results/1", "cases": out}, f, indent=1, sort_keys=True)
        f.write("\n")
    print(len(out), "cases evaluated")


if __name__ == "__main__":
    main(*sys.argv[1:3])
