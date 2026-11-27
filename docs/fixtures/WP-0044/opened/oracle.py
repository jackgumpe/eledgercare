"""WP-0044 independent oracle (eld-fixture-claude). SEALED until coordinator-authorized opening.

Shares no code with docs/fixtures/WP-0044/build_fixtures.py. It reads the blinded
input bytes named by the manifest, evaluates them with its own predicate, and
cross-checks every computed diagnosis against a separately hand-written intent
table taken from the coordinator handoff (pp. 2-4) and mathematical handoff
(pp. 2-8). Live rows are evaluated on explicit ideal-observer scenario models
written here. Archive rows are recomputed from the pinned WP-0043 bytes with
exact rationals. Mathematical rows are computed exactly. Any disagreement
between computation and intent aborts without writing output.

    python -I oracle.py --fixtures <docs/fixtures/WP-0044> --repo <worktree> --out <expected.json>

Standard library only. No process launch, model, device or network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from fractions import Fraction
from pathlib import Path

COMMITMENT_NONCE = "e46648dc590b6ba7692efa0e06692323950a0b663e1971ad64a915cf72a8edd1"
SCHEMA = "wp0044.expected.v1"
ARCHIVE_SHA256 = "66eb8bd4a1d51b813f7de7a846ce841238614017cb9c5970ebd82595a42218bb"

M, U, P = 0, 1, 2
NAME = {M: "M", U: "U", P: "P"}

PHASES = ["launch", "image", "edge", "command", "configuration", "writer", "seal", "acquisition", "score"]
RANK = {p: i for i, p in enumerate(PHASES)}

# Phase of the observation each canonical key stands for (earliest point at which a
# contradiction or a missing witness on that key becomes supportable).
KEY_PHASE = {
    "E.launcher": "launch",
    "L.image": "image", "I.image": "image",
    "E.parent": "edge", "E.order": "edge", "E.instance": "edge", "E.job": "edge",
    "A.script": "command", "A.args": "command",
    "B.writer": "writer",
    "B.seal": "seal", "B.members": "seal",
    "B.protection": "acquisition", "B.direct": "acquisition", "B.origin": "acquisition",
    "content.bytes": "score",
}
C_KEYS = ["C.pyvenv", "C.include_system", "C.pth", "C.sitecustomize", "C.PYTHONHOME",
          "C.PYTHONPATH", "C.PYTHONSAFEPATH", "C.CUBLAS_WORKSPACE_CONFIG",
          "C.CUDA_VISIBLE_DEVICES", "C.prefix", "C.modules"]
for _k in C_KEYS:
    KEY_PHASE[_k] = "configuration"
ALL_KEYS = sorted(KEY_PHASE)
assert len(ALL_KEYS) == 27

CONFLICT_SUBTYPE = {
    "L.image": "image_mismatch", "I.image": "image_mismatch",
    "E.launcher": "anchor_mismatch", "E.parent": "parent_mismatch",
    "E.order": "order_violation", "E.instance": "instance_mismatch",
    "E.job": "containment_escape",
    "A.script": "command_mismatch", "A.args": "command_mismatch",
    "B.writer": "writer_conflict", "B.seal": "seal_invalid", "B.members": "members_inconsistent",
    "B.protection": "protection_violated", "B.direct": "other_original", "B.origin": "other_run",
    "content.bytes": "content_mismatch",
}
for _k in C_KEYS:
    CONFLICT_SUBTYPE[_k] = "config_mismatch"

# Unresolved-provenance subtypes carried when a B witness is missing.
B_MISSING_SUBTYPE = {
    "B.direct": "direct_acquisition_unobserved",
    "B.origin": "origin_unbound",
    "B.protection": "protection_gap",
    "B.seal": "seal_unverified",
    "B.writer": "writer_unobserved",
    "B.members": "members_unobserved",
}


def coord(key: str) -> str:
    return "content" if key == "content.bytes" else key.split(".", 1)[0]


def same(a, b) -> bool:
    """Type-strict JSON equality: bool is not int, list order matters, object key order does not."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def assess(record: dict) -> dict:
    assert record.get("schema") == "wp0044.record.v1"
    exp, obs, src = record["expected"], record["observed"], record.get("sources", {})
    assert set(exp) == set(ALL_KEYS), sorted(set(exp) ^ set(ALL_KEYS))
    assert set(obs) <= set(ALL_KEYS)
    verdict, conflicts, missing = {}, [], []
    for k in ALL_KEYS:
        if k not in obs:
            verdict[k] = U
            missing.append(k)
        elif same(obs[k], exp[k]):
            verdict[k] = P
        else:
            verdict[k] = M
            conflicts.append(k)
    coords = {c: min(v for k, v in verdict.items() if coord(k) == c) for c in "LIEACB"}
    custody = min(coords[c] for c in "LIEAB")
    joint = min(custody, coords["C"])
    content = verdict["content.bytes"]

    def item(k, kind):
        d = {"key": k, "coordinate": coord(k), "phase": KEY_PHASE[k]}
        if kind == "conflict":
            d["subtype"] = CONFLICT_SUBTYPE[k]
            d["source"] = src[k]["method"] if k in src else None
        else:
            d["subtype"] = "unobserved"
            d["source"] = None
        return d

    b_conf = [k for k in conflicts if coord(k) == "B"]
    b_miss = [k for k in missing if coord(k) == "B"]
    if coords["B"] == P:
        cls = "verified"
    elif coords["B"] == U:
        cls = "unresolved"
    elif "B.origin" in b_conf or "B.direct" in b_conf:
        cls = "wrong_origin"
    else:
        cls = "integrity"
    origin = {"class": cls, "unresolved": sorted(B_MISSING_SUBTYPE[k] for k in b_miss)}

    earliest = None
    if conflicts:
        ranked = sorted(conflicts, key=lambda k: (RANK[KEY_PHASE[k]], src.get(k, {}).get("seq", math.inf)))
        k0 = ranked[0]
        top = [k for k in conflicts if RANK[KEY_PHASE[k]] == RANK[KEY_PHASE[k0]]
               and src.get(k, {}).get("seq", math.inf) == src.get(k0, {}).get("seq", math.inf)]
        earliest = {"kind": "conflict", "phase": KEY_PHASE[k0], "keys": sorted(top)}
    elif missing:
        r0 = min(RANK[KEY_PHASE[k]] for k in missing)
        earliest = {"kind": "missing", "phase": PHASES[r0],
                    "keys": sorted(k for k in missing if RANK[KEY_PHASE[k]] == r0)}
    return {
        "coordinates": {c: NAME[coords[c]] for c in "LIEACB"},
        "custody": NAME[custody], "joint": NAME[joint], "content": NAME[content],
        "origin": origin,
        "conflicts": [item(k, "conflict") for k in conflicts],
        "missing": [item(k, "missing") for k in missing],
        "earliest": earliest,
    }


# ------------------------------------------------------------------ intent
# Hand-written from the handoffs: conflicting keys | missing keys | L I E A C B | custody joint | origin class.
INTENT = {
    "W1.A":              ("", "", "PPPPPP", "PP", "verified"),
    "W1.B":              ("", "", "PPPPPP", "PP", "verified"),
    "W2.other":          ("E.launcher", "", "PPMPPP", "MM", "verified"),
    "W4.denied":         ("", "", "PPPPPP", "PP", "verified"),
    "B1.original":       ("", "", "PPPPPP", "PP", "verified"),
    "B2.other":          ("B.direct B.origin", "", "PPPPPM", "MM", "wrong_origin"),
    "B3.copy":           ("", "B.direct B.origin", "PPPPPU", "UU", "unresolved"),
    "B4.invalid":        ("B.seal", "B.direct B.origin", "PPPPPM", "MM", "integrity"),
    "B4.unavailable":    ("", "B.direct B.origin B.seal", "PPPPPU", "UU", "unresolved"),
    "B5.reopen":         ("", "B.protection", "PPPPPU", "UU", "unresolved"),
    "W2.helper":         ("E.parent", "", "PPMPPP", "MM", "verified"),
    "W3.missing":        ("", "E.parent", "PPUPPP", "UU", "verified"),
    "W3.late_missing":   ("E.order", "E.parent", "PPMPPP", "MM", "verified"),
    "W3.reuse":          ("E.instance", "", "PPMPPP", "MM", "verified"),
    "W4.bad_I":          ("I.image", "", "PMPPPP", "MM", "verified"),
    "W4.no_I":           ("", "I.image", "PUPPPP", "UU", "verified"),
    "W4.bad_L":          ("L.image", "", "MPPPPP", "MM", "verified"),
    "W5.args":           ("A.args", "", "PPPMPP", "MM", "verified"),
    "W5.script":         ("A.script", "", "PPPMPP", "MM", "verified"),
    "W5.config":         ("C.include_system C.pyvenv", "", "PPPPMP", "PM", "verified"),
    "W5.empty":          ("C.PYTHONPATH", "", "PPPPMP", "PM", "verified"),
    "W5.unobserved":     ("", "C.PYTHONSAFEPATH", "PPPPUP", "PU", "verified"),
    "W6.escape":         ("E.job", "", "PPMPPP", "MM", "verified"),
    "W6.writer":         ("B.writer", "", "PPPPPM", "MM", "integrity"),
    "B5.member_missing": ("B.members", "B.direct", "PPPPPM", "MM", "integrity"),
    "B5.writer_missing": ("B.writer", "B.direct", "PPPPPM", "MM", "integrity"),
}
# Hand-written earliest diagnostic (phase, keys).
INTENT_EARLIEST = {
    "W2.other": ("launch", "E.launcher"), "B2.other": ("acquisition", "B.direct"),
    "B3.copy": ("acquisition", "B.direct B.origin"), "B4.invalid": ("seal", "B.seal"),
    "B4.unavailable": ("seal", "B.seal"), "B5.reopen": ("acquisition", "B.protection"),
    "W2.helper": ("edge", "E.parent"), "W3.missing": ("edge", "E.parent"),
    "W3.late_missing": ("edge", "E.order"), "W3.reuse": ("edge", "E.instance"),
    "W4.bad_I": ("image", "I.image"), "W4.no_I": ("image", "I.image"), "W4.bad_L": ("image", "L.image"),
    "W5.args": ("command", "A.args"), "W5.script": ("command", "A.script"),
    "W5.config": ("configuration", "C.pyvenv"), "W5.empty": ("configuration", "C.PYTHONPATH"),
    "W5.unobserved": ("configuration", "C.PYTHONSAFEPATH"), "W6.escape": ("edge", "E.job"),
    "W6.writer": ("writer", "B.writer"), "B5.member_missing": ("seal", "B.members"),
    "B5.writer_missing": ("writer", "B.writer"),
}
EXTRAS = {
    "W1.A": {"executable_roles": "distinct_approved_launcher_and_interpreter"},
    "W1.B": {"executable_roles": "distinct_approved_launcher_and_interpreter"},
    "W2.other": {"instance_pairs_retained": 2},
    "W4.denied": {"competing_access": {"denied": True, "filesystem_mutation": False}},
}
B_UNRESOLVED_INTENT = {
    "B3.copy": ["direct_acquisition_unobserved", "origin_unbound"],
    "B4.invalid": ["direct_acquisition_unobserved", "origin_unbound"],
    "B4.unavailable": ["direct_acquisition_unobserved", "origin_unbound", "seal_unverified"],
    "B5.reopen": ["protection_gap"],
    "B5.member_missing": ["direct_acquisition_unobserved"],
    "B5.writer_missing": ["direct_acquisition_unobserved"],
}


def check_intent(row: str, got: dict) -> None:
    c, m, v, cj, cls = INTENT[row]
    assert sorted(x["key"] for x in got["conflicts"]) == sorted(c.split()), (row, got["conflicts"])
    assert sorted(x["key"] for x in got["missing"]) == sorted(m.split()), (row, got["missing"])
    assert "".join(got["coordinates"][k] for k in "LIEACB") == v, (row, got["coordinates"])
    assert got["custody"] + got["joint"] == cj, row
    assert got["origin"]["class"] == cls, (row, got["origin"])
    assert got["origin"]["unresolved"] == B_UNRESOLVED_INTENT.get(row, []), (row, got["origin"])
    assert got["content"] == "P", row
    e = INTENT_EARLIEST.get(row)
    if e is None:
        assert got["earliest"] is None, row
    else:
        assert (got["earliest"]["phase"], " ".join(got["earliest"]["keys"])) == e, (row, got["earliest"])
    # Proposition 3: any conflict forces joint M; otherwise any missing forces U; else P.
    expect_joint = "M" if c else ("U" if m else "P")
    assert got["joint"] == expect_joint, row


# --------------------------------------------------------------- live models
# Key-level interpretation choices for live rows (disclosed at opening; any route that
# differs goes to coordinator reconciliation, not silent correction):
#  I1 W2.other: only the anchor varies (check.py 'anchored_elsewhere'). E.parent is judged
#     against the observed launcher (E_r conjunct parent(i)=l) and E.instance against the
#     offered pair's own interpreter; the job witness is held fixed. Conflict {E.launcher}.
#     If a route's per-arm jobs also make E.job conflict, that is an interpretation delta.
#  I2 B2.other: B_r = W and S and G and [X=R_r]. W (B.writer), S (B.seal, B.protection)
#     hold for B's object under its own receipt; G and identity fail: {B.direct, B.origin}.
#     B.writer is writer exclusivity, not a run-identity comparison.
#  I3 B3/B4 detached: the scored bytes are not a sealed original, so the object identity
#     (B.direct) and the run binding (B.origin) are unobserved; A's original remains
#     exclusively written/protected and its member inventory matches the bytes read.
#     B4.invalid adds a B.seal conflict; B4.unavailable adds a missing B.seal.
#  I4 B5.reopen: the reopened handle witnesses the same object identity and binding;
#     only continuity is lost, so the gap alone: missing {B.protection}.
#  I5 W4.denied: a denied incompatible access leaves all genuine witnesses intact (all P);
#     the denial is reported in extras, its OS error code is recorded but not compared.
#  I6 Phases are those of the observation each key stands for (KEY_PHASE); within one
#     phase the earliest conflict is the one with the smallest observation seq.
SEQ_ORDER = ["E.launcher", "L.image", "E.instance", "E.parent", "I.image", "E.order", "E.job",
             "A.script", "A.args"] + C_KEYS + ["B.writer", "B.members", "B.seal", "B.protection",
             "B.direct", "B.origin", "content.bytes"]
assert sorted(SEQ_ORDER) == ALL_KEYS
LIVE_METHOD = {
    "E.launcher": "supervisor_create_handle", "L.image": "live_image_digest",
    "E.instance": "process_instance_key", "E.parent": "parent_instance_query",
    "I.image": "live_image_digest", "E.order": "ordered_process_events",
    "E.job": "job_membership_query", "A.script": "script_digest", "A.args": "argv_capture",
    "B.writer": "writer_audit", "B.members": "member_inventory", "B.seal": "receipt_authentication",
    "B.protection": "protection_witness", "B.direct": "scorer_handle_identity",
    "B.origin": "receipt_mapping", "content.bytes": "content_read",
}


def ideal_arm(tag: str) -> dict:
    """Ideal-observer record for one genuine arm. Values are opaque placeholders; only relations matter."""
    L, I = {"proc": f"launcher-{tag}"}, {"proc": f"interpreter-{tag}"}
    e = {
        "L.image": "approved-launcher-digest", "I.image": "approved-interpreter-digest",
        "E.launcher": L, "E.parent": L, "E.instance": I,
        "E.order": ["launcher.create", "interpreter.create", "launcher.exit"],
        "E.job": {"breakaway_allowed": False, "launcher_contained": True, "interpreter_contained": True},
        "A.script": "approved-script-digest", "A.args": ["-I", "-B", "script", "emit"],
        "C.pyvenv": "approved-pyvenv-digest", "C.include_system": False, "C.pth": [],
        "C.sitecustomize": None, "C.PYTHONHOME": None, "C.PYTHONPATH": None, "C.PYTHONSAFEPATH": None,
        "C.CUBLAS_WORKSPACE_CONFIG": None, "C.CUDA_VISIBLE_DEVICES": None,
        "C.prefix": "venv-prefix", "C.modules": [{"name": "builtins", "builtin": True}],
        "B.writer": [I], "B.seal": {"receipt": f"receipt-{tag}", "authenticated": True},
        "B.protection": {"continuous_from": "creation", "continuous_through": "acquisition"},
        "B.direct": {"object": f"sink-{tag}"}, "B.origin": f"arm-{tag}",
        "B.members": [{"name": "out.bin", "length": 4, "sha256": hashlib.sha256(b"F07\n").hexdigest()}],
        "content.bytes": "4630370a",
    }
    return e


def live_record(row: str) -> dict:
    exp = ideal_arm("A")
    obs = json.loads(json.dumps(exp))
    src = {k: {"method": LIVE_METHOD.get(k, "config_probe"), "seq": 10 * (i + 1)} for i, k in enumerate(SEQ_ORDER)}
    B = ideal_arm("B")
    if row in ("W1.A", "B1.original", "W4.denied"):
        pass
    elif row == "W1.B":
        exp = B
        obs = json.loads(json.dumps(B))
    elif row == "W2.other":
        # Other approved pair: its launcher is not s(r); its own direct edge, job, images and args hold.
        obs["E.launcher"] = B["E.launcher"]
        exp["E.parent"] = B["E.launcher"]
        obs["E.parent"] = B["E.launcher"]
        exp["E.instance"] = B["E.instance"]
        obs["E.instance"] = B["E.instance"]
        src["E.launcher"]["method"] = "process_instance_key"
    elif row == "B2.other":
        # B's protected original, independently identified as B, submitted for A. Writer
        # exclusivity, seal and protection hold for that object under its own receipt.
        obs["B.direct"] = B["B.direct"]
        obs["B.origin"] = B["B.origin"]
    elif row in ("B3.copy", "B4.invalid", "B4.unavailable"):
        del obs["B.direct"], obs["B.origin"]
        if row == "B4.invalid":
            obs["B.seal"] = {"receipt": "receipt-A", "authenticated": False}
        if row == "B4.unavailable":
            del obs["B.seal"]
    elif row == "B5.reopen":
        del obs["B.protection"]
    else:
        raise KeyError(row)
    for k in list(src):
        if k not in obs:
            del src[k]
    return {"schema": "wp0044.record.v1", "expected": exp, "observed": obs, "sources": src}


# ------------------------------------------------------------------ numbers
def dec(x: Fraction) -> str:
    """Exact decimal string for a dyadic/decimal rational, else p/q."""
    x = Fraction(x)
    d = x.denominator
    k2 = k5 = 0
    while d % 2 == 0:
        d //= 2; k2 += 1
    while d % 5 == 0:
        d //= 5; k5 += 1
    if d != 1:
        return f"{x.numerator}/{x.denominator}"
    n = max(k2, k5)
    if n == 0:
        return str(x.numerator)
    scaled = abs(x) * 10 ** n
    assert scaled.denominator == 1
    s = str(scaled.numerator).rjust(n + 1, "0")
    s = s[:-n] + "." + s[-n:]
    s = s.rstrip("0").rstrip(".")
    return ("-" if x < 0 else "") + s


def first_index_winner(pairs):
    """pairs: list of (token_id, value). First index = smallest token ID among maxima."""
    best = max(v for _, v in pairs)
    return min(t for t, v in pairs if v == best)


def margin_query(q: dict) -> dict:
    base = {int(t): Fraction(v) for t, v in q["scores"]}
    delta = {int(t): Fraction(v) for t, v in q["delta"]}
    assert base.keys() == delta.keys()
    after = {t: base[t] + delta[t] for t in base}
    y = first_index_winner(list(base.items()))
    assert sum(1 for v in base.values() if v == base[y]) == 1
    gaps = {j: base[y] - base[j] for j in base if j != y}
    gap = min(gaps.values())
    omega = max(delta.values()) - min(delta.values())
    linf = max(abs(v) for v in delta.values())
    y2 = first_index_winner(list(after.items()))
    unique = sum(1 for v in after.values() if v == after[y2]) == 1
    exact_unique = all(delta[j] - delta[y] < gaps[j] for j in gaps)
    first_index_keep = all((delta[j] - delta[y] < gaps[j]) if j < y else (delta[j] - delta[y] <= gaps[j]) for j in gaps)
    assert exact_unique == (unique and y2 == y)
    assert first_index_keep == (y2 == y)
    if omega < gap:
        assert y2 == y and unique
    if 2 * linf < gap:
        assert omega < gap
    out = {
        "winner_before": y, "winner_after": y2, "winner_changed": y2 != y, "unique_after": unique,
        "gap": dec(gap), "omega": dec(omega), "linf": dec(linf),
        "oscillation_certificate": omega < gap, "linf_certificate": 2 * linf < gap,
        "exact_unique_criterion": exact_unique, "first_index_criterion": first_index_keep,
        "after": [[t, dec(after[t])] for t in sorted(after)],
    }
    if len(base) == 2:
        (j,) = gaps
        out["winner_minus_runner_change"] = dec(delta[y] - delta[j])
    return out


def fp32(word_le: str) -> float:
    return struct.unpack("<f", bytes.fromhex(word_le))[0]


def signed_zero_query(q: dict) -> dict:
    words = q["words_le"]
    vals = [fp32(w) for w in words]
    best = max(vals)
    idx = min(i for i, v in enumerate(vals) if v == best)
    return {
        "values": [repr(v) for v in vals],
        "sign_bits": [int(math.copysign(1.0, v) < 0) for v in vals],
        "numerically_equal": all(v == vals[0] for v in vals),
        "bytes_equal": len(set(words)) == 1,
        "first_index_argmax": idx, "winner_word_le": words[idx],
        "unique_max": sum(1 for v in vals if v == best) == 1,
    }


def linked_query(q: dict) -> dict:
    base = [Fraction(x) for x in q["base"]]
    slope = [Fraction(x) for x in q["slope"]]
    support = q["support"]
    Z = lambda s: [base[i] + s * slope[i] for i in range(len(base))]
    def win(z):
        best = max(z[i] for i in support)
        return min(i for i in support if z[i] == best)
    qs = qp = Fraction(q["q0"])
    stock, reset, linked, linked_scores = [], [], [], []
    for _ in range(q["steps"]):
        stock.append(win(Z(qs)))
        reset.append(win(Z(qs)))  # private reader restarted from a fresh copy of the stock state
        linked.append(win(Z(qp)))  # private reader consuming its own carried state
        linked_scores.append([dec(v) for v in Z(qp)])
        qs, qp = Fraction(q["stock_write"]), Fraction(q["private_write"])
    div = next((t for t in range(len(stock)) if linked[t] != stock[t]), None)
    return {"stock_tokens": stock, "reset_tokens": reset, "linked_tokens": linked,
            "linked_scores": linked_scores, "reset_pass": reset == stock, "linked_pass": linked == stock,
            "first_linked_divergence_step": div}


def archive_results(raw: bytes) -> dict:
    assert hashlib.sha256(raw).hexdigest() == ARCHIVE_SHA256
    doc = json.loads(raw.decode("utf-8"), parse_float=Fraction)
    rows = doc["retained_rows"]
    assert len(rows) == 5
    winners, runners, gaps, recorded, positions, raw_eq_final = [], [], [], [], [], []
    support_ok, emission_ok, finite_ok, c01_ok, excl, vocab = [], [], [], [], [], set()
    triples = 0
    for k, r in enumerate(rows):
        f = r["final_top_two"]
        g = Fraction(f["value"]) - Fraction(f["runner_up_value"])
        assert g > 0
        winners.append(f["id"]); runners.append(f["runner_up"]); gaps.append(g)
        recorded.append(g == Fraction(f["difference"]))
        positions.append(r["position"])
        raw_eq_final.append(r["raw_top_two"] == r["final_top_two"])
        excl.append(r["c2_differs_from_c1_at_token_ids"])
        support_ok.append(r["c2_differs_from_c1_at_token_ids"] == [1] and r["post_page_eos_fp32le"] == "000080ff")
        emission_ok.append(r["actual_emission"] == f["id"])
        finite_ok.append(r["c0_all_finite"] is True)
        c01_ok.append(r["c0_identical_c1"] is True)
        for c in r["copies"]:
            vocab.add(c["copy_bytes"] // 4)
            assert c["copy_bytes"] % 4 == 0
        ph = {c["phase"]: c for c in r["copies"]}
        if set(ph) == {"C0_raw", "C1_post_rep", "C2_post_page"} and all(c["completion"] for c in r["copies"]):
            triples += 1
        assert ph["C0_raw"]["vector_sha256"] == ph["C1_post_rep"]["vector_sha256"]
        assert ph["C1_post_rep"]["vector_sha256"] != ph["C2_post_page"]["vector_sha256"]
    (V,) = vocab
    eos = fp32("000080ff")
    assert math.isinf(eos) and eos < 0
    v = doc["offline_scorer"]["verdict"]
    hist_rows = v["rows"]
    assert [h["y"] for h in hist_rows] == winners
    assert all(h["support_size"] == V - 1 for h in hist_rows)
    # BF16 spacing at the row-0 winner value: 8 significant bits.
    w0 = Fraction(rows[0]["final_top_two"]["value"])
    e = math.floor(math.log2(w0))
    spacing = Fraction(2) ** (e - 7)
    gmin = min(gaps)
    gaps_res = {
        "positions": positions, "winners": winners, "runner_ups": runners,
        "gaps": [dec(g) for g in gaps], "recomputed_equals_recorded": all(recorded),
        "raw_equals_final_top_two": all(raw_eq_final),
        "min_gap": dec(gmin), "min_gap_row": gaps.index(gmin), "half_min_gap": dec(gmin / 2),
        "row0_bf16_spacing": dec(spacing), "row0_gap_in_spacing_units": dec(gaps[0] / spacing),
    }
    support_res = {
        "rows": len(rows), "vocabulary": V, "support_size": V - 1,
        "excluded_ids_per_row": excl, "excluded_word_le": "000080ff", "excluded_value": "-inf",
        "only_eos_excluded_all_rows": all(support_ok), "c0_all_finite_all_rows": all(finite_ok),
        "c0_identical_c1_all_rows": all(c01_ok), "emission_equals_final_winner_all_rows": all(emission_ok),
        "historical_support_sizes": [h["support_size"] for h in hist_rows],
    }
    cf = v["conflicts"]
    diff_idx = [[i for i, (a, b) in enumerate(zip(c["expected"], c["observed"])) if a != b] for c in cf]
    pub = doc["public_content"]["F07.warm1"]
    verdict_res = {
        "verdict": v["verdict"], "first_divergent_phase": v["first_divergent_phase"],
        "conflict_keys": v["conflict_keys"], "missing_keys": v["missing_keys"],
        "argv_conflicts": len(cf), "argv_conflict_fields": sorted({c["field"] for c in cf}),
        "argv_differs_only_at_index": diff_idx,
        "argv_tails_equal": all(c["expected"][1:] == c["observed"][1:] for c in cf),
        "argv_workers": [c["expected"][-1] for c in cf],
        "expected_argv0_is_venv_scripts": all(c["expected"][0].lower().endswith("\\venv\\scripts\\python.exe") for c in cf),
        "observed_argv0_is_base_python312": all(c["observed"][0].lower().endswith("\\python312\\python.exe") for c in cf),
        "missing_rows": [m["row"] for m in v["missing"]], "missing_phase": sorted({m["phase"] for m in v["missing"]}),
        "row_verdicts": [h["verdict"] for h in hist_rows],
        "scheduled_rows": v["scheduled_rows"], "complete_rows": v["complete_rows"],
        "qualified_rows": f'{v["complete_rows"]}/{v["scheduled_rows"]}',
        "qualified_pairs": f'{v["public_pairs_matched"]}/{v["scheduled_pairs"]}',
        "public_verdict": v["public_verdict"],
        "F07_target_pairs_matched": f'{int(pub["matches_archived_ids"] and pub["matches_archived_utf8"] and pub["same_all_public_fields"])}/1',
        "complete_copy_triples": f"{triples}/{len(rows)}",
    }
    return {"archive.gaps": gaps_res, "archive.support": support_res, "archive.verdict": verdict_res}


ARCHIVE_INTENT = {
    "archive.gaps": {"gaps": ["10.875", "15.1875", "13.5625", "15.375", "13.875"], "min_gap": "10.875",
                     "half_min_gap": "5.4375", "winners": [6, 1449, 16, 1328, 128822],
                     "row0_gap_in_spacing_units": "87", "positions": [1445, 1446, 1447, 1448, 1449]},
    "archive.support": {"support_size": 129279, "only_eos_excluded_all_rows": True},
    "archive.verdict": {"verdict": "M", "argv_conflicts": 2, "qualified_rows": "0/5", "qualified_pairs": "0/1",
                        "missing_rows": [0, 1, 2, 3, 4], "row_verdicts": ["U"] * 5},
}
MATH_INTENT = {
    "math.shift": [{"winner_changed": False, "omega": "0", "linf": "10", "oscillation_certificate": True,
                    "linf_certificate": False, "winner_minus_runner_change": "0"},
                   {"winner_changed": False, "omega": "10", "linf": "5", "oscillation_certificate": True,
                    "linf_certificate": True, "winner_minus_runner_change": "-10"}],
    "math.tie": [{"winner_after": 6, "winner_changed": False, "unique_after": False, "oscillation_certificate": False},
                 {"winner_after": 223, "winner_changed": True, "unique_after": False, "oscillation_certificate": False}],
    "math.signed_zero": [{"numerically_equal": True, "bytes_equal": False, "first_index_argmax": 0, "winner_word_le": "00000000"},
                         {"numerically_equal": True, "bytes_equal": False, "first_index_argmax": 0, "winner_word_le": "00000080"}],
    "math.linked": {"reset_pass": True, "linked_pass": False, "first_linked_divergence_step": 1,
                    "linked_tokens": [0, 1], "linked_scores": [["1", "0"], ["-1", "2"]]},
}


def subset_ok(want, got) -> bool:
    if isinstance(want, dict):
        return all(k in got and subset_ok(v, got[k]) for k, v in want.items())
    if isinstance(want, list) and want and isinstance(want[0], dict):
        return len(want) == len(got) and all(subset_ok(a, b) for a, b in zip(want, got))
    return same(want, got)


# --------------------------------------------------------------------- main
def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    fx, repo = Path(a.fixtures), Path(a.repo)
    man_bytes = (fx / "manifest.json").read_bytes()
    man = json.loads(man_bytes.decode("utf-8"))
    assert man["version"] == "wp0044.fixtures.v1" and man["denominator_per_route"] == 33
    sched = json.loads((repo / "docs/coordination/WP-0044/schedule.json").read_bytes().decode("utf-8"))
    assert [(r["id"], r["interface"], r["repetitions"]) for r in sched["rows"]] == \
           [(r["id"], r["interface"], r["repetitions"]) for r in man["rows"]]
    archive = None
    out_rows = []
    for r in man["rows"]:
        row, iface = r["id"], r["interface"]
        rec = {"id": row, "interface": iface}
        if iface in ("constructed", "mathematical"):
            data = (fx / r["input"]["path"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == r["input"]["sha256"], row
            rec["input_sha256"] = r["input"]["sha256"]
            doc = json.loads(data.decode("utf-8"))
        if iface in ("live", "constructed"):
            got = assess(live_record(row) if iface == "live" else doc)
            check_intent(row, got)
            rec.update(got)
            rec["extras"] = EXTRAS.get(row, {})
        elif iface == "archive":
            if archive is None:
                raw = (repo / r["input"]["path"]).read_bytes()
                archive = archive_results(raw)
            rec["input_sha256"] = r["input"]["sha256"]
            rec["result"] = archive[row]
            assert subset_ok(ARCHIVE_INTENT[row], rec["result"]), row
        else:
            if doc["schema"] == "wp0044.margin.v1":
                res = [margin_query(q) for q in doc["queries"]]
            elif doc["schema"] == "wp0044.fp32.v1":
                res = [signed_zero_query(q) for q in doc["queries"]]
            else:
                res = linked_query(doc)
            assert subset_ok(MATH_INTENT[row], res), (row, res)
            rec["result"] = res
        out_rows.append(rec)
    assert len(out_rows) == 33
    counts = {}
    for x in out_rows:
        counts[x["interface"]] = counts.get(x["interface"], 0) + 1
    assert counts == {"live": 10, "constructed": 16, "archive": 3, "mathematical": 4}, counts
    doc = {
        "schema": SCHEMA, "owner": "eld-fixture-claude", "packet": "WP-0044",
        "commitment_nonce": COMMITMENT_NONCE,
        "fixture_manifest_sha256": hashlib.sha256(man_bytes).hexdigest(),
        "phase_order": PHASES, "rows": out_rows,
    }
    Path(a.out).write_bytes((json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=False) + "\n").encode("utf-8"))
    print(json.dumps({"rows": len(out_rows), "counts": counts,
                      "expected_sha256": hashlib.sha256(Path(a.out).read_bytes()).hexdigest()}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
