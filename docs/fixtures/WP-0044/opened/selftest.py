"""Negative controls for oracle.py (private). Each must be rejected or classified as stated.
Commitment nonce: e46648dc590b6ba7692efa0e06692323950a0b663e1971ad64a915cf72a8edd1"""
import json, sys, copy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import oracle as o

fx = Path(sys.argv[1])
man = json.loads((fx / "manifest.json").read_text(encoding="utf-8"))
recs = {r["id"]: json.loads((fx / r["input"]["path"]).read_text(encoding="utf-8"))
        for r in man["rows"] if r["interface"] == "constructed"}
results = []

def expect_fail(name, fn):
    try:
        fn()
    except AssertionError:
        results.append((name, "rejected"))
        return
    raise SystemExit(f"NOT rejected: {name}")

# 1. Type strictness and key-order independence.
assert not o.same(False, 0) and not o.same(0, False) and not o.same(1, True)
assert not o.same(None, "") and not o.same([], None) and not o.same(["a", "b"], ["b", "a"])
assert o.same({"a": 1, "b": [1, {"c": None}]}, {"b": [1, {"c": None}], "a": 1})
results.append(("type_strict_equality", "ok"))

# 2. Each constructed record checked against a wrong row's intent must be rejected.
ids = list(recs)
for i, row in enumerate(ids):
    other = ids[(i + 1) % len(ids)]
    got = o.assess(recs[row])
    expect_fail(f"intent_swap:{row}->{other}", lambda: o.check_intent(other, got))

# 3. Undoing the construction (observed := expected) must give all-P and fail its intent.
for row in ids:
    r = copy.deepcopy(recs[row]); r["observed"] = copy.deepcopy(r["expected"])
    r["sources"] = {k: {"method": "x", "seq": 1} for k in r["expected"]}
    g = o.assess(r)
    assert g["joint"] == "P" and not g["conflicts"] and not g["missing"]
    expect_fail(f"undone:{row}", lambda: o.check_intent(row, g))

# 4. Source-map presence must not count as observation.
r = copy.deepcopy(recs["W4.no_I"]); r["sources"]["I.image"] = {"method": "preflight_file_digest", "seq": 0}
g = o.assess(r); assert [m["key"] for m in g["missing"]] == ["I.image"] and g["coordinates"]["I"] == "U"
results.append(("sources_entry_not_observation", "ok"))

# 5. bool/int confusion in a config value is a conflict, not a pass.
r = copy.deepcopy(recs["W5.unobserved"]); r["observed"]["C.include_system"] = 0
g = o.assess(r); assert "C.include_system" in [c["key"] for c in g["conflicts"]] and g["custody"] == "P"
results.append(("bool_vs_int_conflict", "ok"))

# 6. Live model sanity: a byte-only verifier would give content P on all B rows.
for row in ("B1.original", "B2.other", "B3.copy", "B4.invalid", "B4.unavailable", "B5.reopen"):
    assert o.assess(o.live_record(row))["content"] == "P"
results.append(("content_independent_of_origin", "ok"))

# 7. Math: a tie at the gap must not satisfy the strict certificate.
q = o.margin_query({"scores": [[1, "1"], [2, "0"]], "delta": [[1, "0"], [2, "1"]]})
assert q["oscillation_certificate"] is False and q["winner_after"] == 1 and q["unique_after"] is False
results.append(("tie_boundary_strict", "ok"))

print(json.dumps({"checks": len(results), "rejected": sum(1 for _, s in results if s == "rejected"),
                  "ok": sum(1 for _, s in results if s == "ok")}))
