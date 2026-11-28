"""Write label-free post-opening cases in the peer controls.py schema (kinds startup, inventory,
score_phase, replay_gate, assess, crosswalk_diagnostics). Constructed records only.
Usage: python -I make_peer_cases.py OUT.json
"""
import json
import sys

ONE, TWO, FIVE, NAN, NINF, BIG, NZ, PZ = 0x3F800000, 0x40000000, 0x40A00000, 0x7FC00000, 0xFF800000, 0xFF7FFFFF, 0x80000000, 0
P = lambda v: {"state": "present", "value": v}
ABS = {"state": "absent"}
UNO = {"state": "unobserved"}
OK = {f: True for f in ("writer_ok", "bound_write", "seal_ok", "handle_covers_interval", "share_excludes_write_delete",
                        "scorer_share_read_only", "object_id_match", "digest_match")}


def member(phys, **over):
    return {**OK, **over, "physical_object_id": phys}


def startup(cid, src, exp_child, obs_child, exp_flags, obs_flags):
    return {"case_id": cid, "kind": "startup", "projection_of": src, "stage": 1, "input": {
        "expected": {"e_launch": {}, "e_child": exp_child, "flags": exp_flags, "resolution": {}},
        "observed": {"e_launch": {}, "e_child": obs_child, "flags": obs_flags, "resolution": {}}}}


def inventory(cid, src, E, I, R, members, **extra):
    return {"case_id": cid, "kind": "inventory", "projection_of": src, "stage": 1, "input": {
        "qr_authenticated": True, "inventory_custody": True, "expected_keys": E, "sealed_keys": I,
        "read_keys": R, "members": members, **extra}}


def score(cid, src, raw, rep, page, m1, m2, emitted):
    return {"case_id": cid, "kind": "score_phase", "projection_of": src, "stage": 2, "input": {
        "vocab_size": len(raw), "raw": raw, "rep": rep, "page": page, "mask1": m1, "mask2": m2, "emitted": emitted}}


def gate(cid, src, rows, stock=None, p3=True):
    base = [{"run": "r1", "arm": "observed", "call": "F07.warm1", "position": p, "original_bound": True, "restorable": True}
            for p in range(1445, 1449)]
    return {"case_id": cid, "kind": "replay_gate", "projection_of": src, "stage": 2, "input": {
        "run_id": "r1", "stock_verdicts": stock or {"r1": "P", "r2": "P"}, "P3_complete_and_consistent": p3,
        "Rev3_independently_reviewed": True, "candidate_rows": base + rows}}


def last(**over):
    return [{"run": "r1", "arm": "observed", "call": "F07.warm1", "position": 1449, "original_bound": True, "restorable": True, **over}]


def assess(cid, src, stage, atoms, scope=None):
    inp = {"stage": stage, "atoms": atoms}
    if scope is not None:
        inp["required_binding_stages"] = scope
    return {"case_id": cid, "kind": "assess", "projection_of": src, "stage": stage, "input": inp}


def atom(key, due, presc, observed=UNO):
    return {"key": key, "due_stage": due, "observed": observed,
            "prescriptions": [UNO if p is None else {"state": "present", "values": [P(v) for v in p]} for p in presc]}


def cross(cid, src, comps, edges=()):
    return {"case_id": cid, "kind": "crosswalk_diagnostics", "projection_of": src, "stage": 0,
            "input": {"comparisons": comps, "order_edges": [list(e) for e in edges]}}


def comp(key, J, left, right):
    return {"key": key, "J_k": J, "left": left, "right": right, "mandatory": True}


cases = [
    startup("XS1", "S1", {"PYTHONHASHSEED": P("0")}, {"PYTHONHASHSEED": P("0")},
            {"ignore_environment": 0, "hash_randomization": 0}, {"ignore_environment": P(1), "hash_randomization": P(1)}),
    startup("XS3", "S3", {"PYTHONHASHSEED": P("0")}, {"PYTHONHASHSEED": P("0")},
            {"ignore_environment": 0, "hash_randomization": 0}, {"ignore_environment": UNO, "hash_randomization": UNO}),
    startup("XS6", "S6", {"PYTHONPATH": ABS, "PYTHONCASEOK": ABS}, {"PYTHONPATH": P(""), "PYTHONCASEOK": UNO}, {}, {}),
    startup("XC1", "new", {"PYTHONHASHSEED": P("0")}, {"PYTHONHASHSEED": P("0"), "PYTHONCASEOK": P("1")}, {}, {}),
    inventory("XI1", "I1", ["a", "b"], ["a"], ["a"], {"a": member([1, 1])}),
    inventory("XI3", "I3", None, ["a", "b"], ["a"], {"a": member([1, 1]), "b": member([1, 2])}),
    inventory("XI5", "I5", ["a", "b"], ["a", "b"], ["a", "b"], {"a": member([1, 1]), "b": member([1, 1])}),
    inventory("XC2", "new", None, ["a"], ["a"], {"a": member([1, 1], writer_ok=False)}),
    inventory("XC4", "I6a", ["a", "b"], ["a", "b"], ["b", "a"], {"a": member([1, 1]), "b": member([1, 2])}, ordered=True),
    score("XP1", "P1", [ONE] * 3, [ONE, ONE, BIG], [NINF, ONE, NINF], [2], [0], P(1)),
    score("XP2", "P2", [FIVE, NAN, TWO], [FIVE, NAN, TWO], [FIVE, NINF, TWO], [], [1], P(0)),
    score("XP3", "P3", [ONE, ONE], [NINF, ONE], [NINF, NINF], [0], [1], P(0)),
    score("XP4", "P4", [TWO, ONE], [TWO, ONE], [TWO, ONE], [], [], P(1)),
    score("XP5", "P5a", [NZ, PZ], [NZ, PZ], [NZ, PZ], [], [], P(0)),
    score("XP7", "P7", [ONE, NAN], [ONE, NAN], [ONE, NAN], [], [], UNO),
    gate("XJ1", "J1", last(run="r2")),
    gate("XJ3", "J3", last(call="F07.warmup")),
    gate("XJ4", "J4", last(arm="untouched")),
    gate("XJ5", "J5", last()),
    gate("XJ6", "J6", last(), p3=False),
    assess("XA1", "A1", 0, [atom("backend.tf32", 2, [[True], [False]])], scope=[0]),
    assess("XA2a", "A2a", 1, [atom("cpu.hash.hash_randomization", 1, [[0]], P(0)), atom("private.parity", 3, [None])], scope=[0, 1, 2, 3]),
    assess("XA2b", "A2b", 1, [atom("cpu.hash.hash_randomization", 1, [[0]], P(0)), atom("private.parity", 3, [None])], scope=[0, 1]),
    assess("XC3", "new", 2, [atom("cpu.import.dll_origins", 1, [None], P("pinned-set"))]),
    cross("XD1", "D1", [comp("d1", 0, UNO, UNO)]),
    cross("XD4", "D4", [comp("d4", 1, ABS, P(""))]),
    cross("XD6", "D6", [comp("a", 1, P(1), P(2)), comp("c", 1, P(3), P(4))], edges=[("a", "b"), ("b", "c")]),
]
with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as f:
    json.dump({"schema": "wp46-claude-peer-schema-cases/1", "author": "eld-rd-reviewer",
               "status": "post-opening constructed cases in the peer controls.py batch schema; label-free (no expected_return); answers in ../expectations/peer-schema-expected.json",
               "cases": cases}, f, indent=1)
    f.write("\n")
print(len(cases), "cases written")
