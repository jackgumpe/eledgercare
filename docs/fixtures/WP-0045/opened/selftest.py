"""WP-0045 sealed oracle self-test (eld-fixture-claude). SEALED with oracle.py.

    python -I selftest.py --fixtures <worktree>/docs/fixtures/WP-0045 --reference <edition02 dir>

Negative controls for the oracle predicates plus a cross-check of the
overlapping Edition 02 reference vectors (A02-A06, C01-C06, Q01-Q02).
Nonce: 43824adbd7bb13731b0685f3aeb5ae10919d7f16c5122dc2a2b1a8c8dab172d2
"""
import argparse
import copy
import importlib.util
import json
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("oracle", HERE / "oracle.py")
O = importlib.util.module_from_spec(spec)
spec.loader.exec_module(O)

results = []


def check(name, cond):
    results.append((name, bool(cond)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", required=True)
    ap.add_argument("--reference", required=True)
    a = ap.parse_args()
    fx = Path(a.fixtures)
    man = json.loads((fx / "manifest.json").read_text(encoding="utf-8"))
    inp = {r["id"]: json.loads((fx / r["input"]["path"]).read_text(encoding="utf-8")) for r in man["rows"]}

    # --- canonical typed equality
    check("bool!=int", O.canon(True) != O.canon(1))
    check("member order irrelevant", O.canon({"a": 1, "b": [2, None]}) == O.canon({"b": [2, None], "a": 1}))
    check("list order relevant", O.canon([1, 2]) != O.canon([2, 1]))
    check("null!=empty string", O.canon(None) != O.canon(""))

    # --- inputs carry no ID/label
    blob = json.dumps(inp, ensure_ascii=False)
    for rid in inp:
        if rid not in ("H.old",):
            check("no id in inputs " + rid, all(rid not in json.dumps(v, ensure_ascii=False) for v in inp.values()))
    check("no verdict field", all("status" not in v and "verdict" not in v for v in inp.values()))
    check("reordered nested members present", any(
        "expected" in v and json.dumps(v["expected"]["C.runtime"]) != json.dumps(v["observed"]["C.runtime"])
        and O.canon(v["expected"]["C.runtime"]) == O.canon(v["observed"]["C.runtime"]) for v in inp.values()))

    # --- Q1 predicate negative controls
    base = copy.deepcopy(inp["Q.other_caller"])
    fixed = copy.deepcopy(base)
    fixed["observed"]["E.caller"] = copy.deepcopy(fixed["expected"]["E.caller"])
    r = O.q1_constructed(fixed)
    check("repaired caller -> all P", r["status"] == "P" and r["first"] is None and r["reason"] == {})
    t = copy.deepcopy(fixed)
    t["observed"]["E.job"]["before_execution"] = 1          # bool vs int
    r = O.q1_constructed(t)
    check("bool/int mismatch -> M integrity", r["values"]["E.job"] == "M" and r["reason"]["E.job"] == "integrity")
    t = copy.deepcopy(fixed)
    t["observed"]["content.bytes"] = "4630370b"
    r = O.q1_constructed(t)
    check("content independent of status", r["status"] == "P" and r["content"] == "M" and r["conflicts"] == ["content.bytes"])
    t = copy.deepcopy(fixed)
    t["observed"]["C.runtime"] = None                       # witnessed null differs from object
    r = O.q1_constructed(t)
    check("C only in status not custody", r["custody"] == "P" and r["status"] == "M")
    t = copy.deepcopy(fixed)
    del t["observed"]["B.seal"]; del t["observed"]["E.child"]
    t["evidence"]["B.seal"]["at"] = 3
    r = O.q1_constructed(t)
    check("tie at lowest ordinal", r["first"] == {"at": 3, "keys": ["B.seal", "E.child"]})
    check("E.child wrong_origin when M", O.reason_subtype("E.child", "M") == "wrong_origin")
    t = copy.deepcopy(fixed)
    t["observed"]["X.extra"] = 1
    try:
        O.q1_constructed(t); check("extra observed key rejected", False)
    except AssertionError:
        check("extra observed key rejected", True)
    check("live ideal all P", O.q1_live({"clause": "Q1", "selection": 1, "payload_hex": "4630370a"})["status"] == "P")
    try:
        O.q1_live({"clause": "Q1", "selection": 2, "payload_hex": "4630370a"}); check("bad selection rejected", False)
    except AssertionError:
        check("bad selection rejected", True)
    # reference Q01/Q02 custody status
    v = {k: "P" for k in O.KEYS}; v["E.caller"] = "U"; v["B.writer"] = "U"
    r = O.project_q1(v, O.CANON_SOURCE, {k: a for k, _, a in O.SCHEDULE})
    check("ref Q01", r["status"] == "U" and r["missing"] == ["B.writer", "E.caller"] and r["conflicts"] == [])
    v["E.caller"] = "M"
    r = O.project_q1(v, O.CANON_SOURCE, {k: a for k, _, a in O.SCHEDULE})
    check("ref Q02", r["status"] == "M" and r["conflicts"] == ["E.caller"] and r["missing"] == ["B.writer"])

    # --- A1
    ref = {x["id"]: x for x in json.loads((Path(a.reference) / "vectors.json").read_text())}
    for vid, (mode, anchor, k, commit, sel) in {"A02": ("duplicate", 2, 0, True, "duplicate"),
                                               "A03": ("literal", 2, 1, True, "k1"),
                                               "A04": ("literal", 2, 3, False, "k3")}.items():
        r = O.a1({"clause": "A1", "mode": mode, "k": k, "a": anchor, "select": sel, "commit": commit})
        want = ref[vid]["want"]
        check("ref " + vid, [c[1] for c in r["calls"]] == want["inputs"] and r["transition"][1] == want["hidden"]
              and r["commits"] == want["appends"])
    for bad in [("stock", 0, "duplicate"), ("literal", 3, "k2"), ("literal", 3, "stock"), ("duplicate", 0, "k1")]:
        r = O.a1({"clause": "A1", "mode": bad[0], "k": bad[1], "a": 0, "select": bad[2], "commit": True})
        check("invalid select %s" % (bad,), r == {"status": "M", "reason": "invalid_selection", "commits": 0, "history": []})

    # --- A2
    for w, fin in [("7fc00000", False), ("ffc00000", False), ("7f800000", False), ("ff800000", False),
                   ("7f800001", False), ("00000001", True), ("80000000", True), ("7f7fffff", True), ("ff7fffff", True)]:
        check("finite " + w, O.word_finite(w) == fin)
    r = O.a2({"clause": "A2", "raw": ["80000000", "3f800000", "00000000"], "repeat": ["80000000", "ff800000", "00000000"],
              "page": ["80000000", "ff800000", "00000000"], "repeat_block": [1], "page_block": []})
    check("ref A05 signed-zero tie", r["winner"] == ref["A05"]["want"]["winner"] and r["status"] == "P")
    r = O.a2({"clause": "A2", "raw": ["3f800000"], "repeat": ["ff800000"], "page": ["ff800000"],
              "repeat_block": [0], "page_block": []})
    check("ref A06 empty", ref["A06"]["want"] == "INVALID" and r["status"] == "M" and r["conflicts"] == [["support", -1]])
    r = O.a2(inp["A2.illegal_repeat"])
    check("phase order not lexical", [c[0] for c in r["conflicts"]] == ["repeat", "repeat", "page"])
    t = copy.deepcopy(inp["A2.clean"]); t["page"][0] = "bf800000"
    r = O.a2(t)
    check("page unmasked change", r["conflicts"] == [["page", 0]] and r["winner"] is None)

    # --- C1
    def g_alt(post, law):          # independent formula: sum_o sum_y (p_y L_yo)^2 / P(o)  - sum p^2
        tot = Fraction(0)
        for o in range(len(law[0])):
            po = sum(post[y] * law[y][o] for y in range(len(post)))
            if po:
                tot += sum((post[y] * law[y][o]) ** 2 for y in range(len(post))) / po
        return tot - sum(p * p for p in post)
    for rid in ("C1.uninformative", "C1.informative", "C1.duplicate", "C1.budget", "C1.threshold", "C1.tie"):
        obj = inp[rid]
        post = [Fraction(x) for x in obj["p"]]
        for act in obj["actions"]:
            law = [[Fraction(x) for x in row] for row in act["law"]]
            check("gain alt %s/%d" % (rid, act["id"]), O.gain(post, law) == g_alt(post, law))
    check("ref C01", O.c1_exact([[20, 38, 58], [28, 30, 58]]) == {"status": "QUERY", "action": ref["C01"]["want"]})
    check("ref C02", O.c1_exact([]) == {"status": "CONFLICT", "action": None})
    check("ref C03", O.c1_exact([[20, 38]]) == {"status": "IDENTIFIED", "action": None})

    def post_only(p, lik):
        law = [[Fraction(l), 1 - Fraction(l)] for l in lik]
        obj = {"clause": "C1", "mode": "noisy", "p": p, "threshold": "1", "budget": 1, "used": [],
               "actions": [{"id": 1, "source": "s", "law": [[str(x) for x in row] for row in law]}],
               "observation": {"action": 1, "outcome": 0}}
        return O.c1_noisy(obj)
    check("ref C04", post_only(["9/10", "1/10"], ["1", "1"])["posterior"] == ref["C04"]["want"])
    check("ref C05", post_only(["9/10", "1/10"], ["9/10", "1/10"])["posterior"] == ref["C05"]["want"])
    check("ref C06", post_only(["1/2", "1/2"], ["0", "0"])["status"] == ref["C06"]["want"])
    t = copy.deepcopy(inp["C1.duplicate"]); t["used"] = []
    check("duplicate control: applying repeat would ACCEPT", O.c1_noisy(t)["status"] == "ACCEPT")
    t = copy.deepcopy(inp["C1.tie"]); t["actions"] = list(reversed(t["actions"]))
    check("tie independent of listing order", O.c1_noisy(t)["action"] == 4)
    t = copy.deepcopy(inp["C1.budget"]); t["budget"] = 2
    check("budget control: with budget left -> QUERY", O.c1_noisy(t)["status"] == "QUERY")
    check("rational canonical", O.rstr(Fraction(4, 2)) == "2" and O.rstr(Fraction(-2, 4)) == "-1/2")

    fails = [n for n, ok in results if not ok]
    print("%d checks, %d failed" % (len(results), len(fails)))
    for n in fails:
        print("FAIL", n)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
