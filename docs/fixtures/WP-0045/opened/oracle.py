"""WP-0045 sealed independent expected-value oracle (eld-fixture-claude).

SEALED until eld-coordinator authorizes opening after both blind candidates
freeze and commit their results.  Standard library only, CPython 3.12.10.

    python -I oracle.py --fixtures <worktree>/docs/fixtures/WP-0045 --repo <worktree> --out <dir>

Reads the public manifest, verifies every input digest, computes each row
from the input bytes alone (dispatch is by input content, never by ID),
cross-checks the result against an independently hand-written intent table,
and writes <out>/expected/<ID>.json (one unwrapped projected row per file,
canonical JSON: sort_keys, separators (',',':'), ensure_ascii=False, LF)
plus <out>/expected-manifest.json mapping every ID to path+sha256+bytes.

COMMITMENT_NONCE hides this file and the expected manifest from guessing.
"""
COMMITMENT_NONCE = "43824adbd7bb13731b0685f3aeb5ae10919d7f16c5122dc2a2b1a8c8dab172d2"

import argparse
import hashlib
import json
import math
import struct
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

PIN = "7f9281bd247e312bbce89af9a3021832fca965da"
DISPOSITION_PATH = "docs/coordination/WP-0044/disposition.json"
DISPOSITION_SHA = "f0a126012df16c2df2695f072d300fdb3b3196780c8cef183e66a42ca74e3a14"

# ---------------------------------------------------------------- canonical JSON
def canon(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def encode_row(v):
    return (canon(v) + "\n").encode("utf-8")


# ---------------------------------------------------------------- Q1 projection
# Schedule atoms (wire.md / schedule.json).  Group = coordinate letter.
SCHEDULE = [
    ("L.image", "supervisor_image", 1), ("I.image", "child_image", 3),
    ("E.caller", "call_return_join", 3), ("E.child", "creation_instance", 3),
    ("E.order", "creation_order", 3), ("E.job", "job_membership", 3),
    ("A.command", "command_manifest", 4), ("C.runtime", "runtime_manifest", 5),
    ("B.writer", "writer_account", 6), ("B.seal", "authenticated_seal", 7),
    ("B.protection", "protected_lifetime", 8), ("B.direct", "direct_handle", 8),
    ("B.origin", "authenticated_origin", 8), ("B.members", "member_inventory", 8),
    ("content.bytes", "scorer_read", 8),
]
KEYS = [k for k, _, _ in SCHEDULE]
CANON_SOURCE = {k: s for k, s, _ in SCHEDULE}
RANK = {"M": 0, "U": 1, "P": 2}
GROUPS = "LIEACB"
WRONG_ORIGIN = {"E.caller", "E.child", "B.origin"}


def vmin(vals):
    return min(vals, key=RANK.__getitem__)


def group_of(key):
    """Coordinate group of an atom; content.bytes belongs to no coordinate (I1)."""
    g = key.split(".", 1)[0]
    return g if g in GROUPS else None


def reason_subtype(key, value):
    if value == "U":
        return "unresolved"
    if key in WRONG_ORIGIN:
        return "wrong_origin"
    if key == "B.writer":
        return "unauthorized_writer"
    return "integrity"


def project_q1(values, sources, ats):
    """values/sources/ats: dict over all 15 KEYS."""
    coords = {g: vmin([values[k] for k in KEYS if group_of(k) == g]) for g in GROUPS}
    custody = vmin([coords[g] for g in "LIEAB"])
    status = vmin([custody, coords["C"]])
    findings = sorted(k for k in KEYS if values[k] != "P")          # I1: includes content.bytes
    if not findings:
        first = None
    elif any(ats[k] is None for k in findings):
        first = {"at": None, "keys": findings}
    else:
        lo = min(ats[k] for k in findings)
        first = {"at": lo, "keys": sorted(k for k in findings if ats[k] == lo)}
    return {
        "status": status,
        "values": dict(values),
        "coordinates": coords,
        "custody": custody,
        "content": values["content.bytes"],
        "conflicts": sorted(k for k in KEYS if values[k] == "M"),
        "missing": sorted(k for k in KEYS if values[k] == "U"),
        "reason": {k: reason_subtype(k, values[k]) for k in findings},
        "first": first,
        "source": dict(sources),
    }


def q1_constructed(obj):
    assert set(obj) == {"expected", "observed", "evidence"}, "constructed record shape"
    exp, obs, ev = obj["expected"], obj["observed"], obj["evidence"]
    assert set(exp) == set(KEYS) and set(ev) == set(KEYS) and set(obs) <= set(KEYS)
    values = {}
    for k in KEYS:
        assert set(ev[k]) == {"source", "at"}
        assert isinstance(ev[k]["source"], str)
        assert ev[k]["at"] is None or (isinstance(ev[k]["at"], int) and not isinstance(ev[k]["at"], bool))
        if k not in obs:
            values[k] = "U"                                     # omission = unknown
        else:
            values[k] = "P" if canon(obs[k]) == canon(exp[k]) else "M"   # typed canonical equality
    return project_q1(values, {k: ev[k]["source"] for k in KEYS}, {k: ev[k]["at"] for k in KEYS})


def q1_live(obj):
    """Ideal-observer model of a genuine direct-launch arm (I4).

    The request names a selection (0 or 1) and the four-byte original.  An
    ideal compliant observer witnesses every atom at its schedule cut with its
    canonical source token, and every observation equals its frozen
    expectation, so every atom is P and there are no findings.
    """
    assert set(obj) == {"clause", "selection", "payload_hex"} and obj["clause"] == "Q1"
    assert obj["selection"] in (0, 1) and obj["payload_hex"] == "4630370a"
    return project_q1({k: "P" for k in KEYS}, CANON_SOURCE, {k: a for k, _, a in SCHEDULE})


def archive_old(obj, repo):
    """H.old: read-only typed record from the pinned WP-0044 disposition (I5)."""
    assert obj == {"clause": "archive", "packet": "WP-0044"}
    raw = subprocess.run(["git", "-C", str(repo), "show", "%s:%s" % (PIN, DISPOSITION_PATH)],
                         capture_output=True, check=True).stdout
    assert hashlib.sha256(raw).hexdigest() == DISPOSITION_SHA, "pinned disposition bytes"
    d = json.loads(raw)
    g = d["genuine_all_P"]
    author, reviewer, per_route = g["author"], g["reviewer"], g["scheduled_per_route"]
    # Genuine joint per route: no genuine arm reached P in either route and the
    # disposition records both arms unresolved ("Both genuine arms in each route
    # yielded joint/custody U"); the shared unmet obligation is the creating caller.
    assert "E.parent" in d["smallest_shared_unmet_obligation"]
    old_joint = "U" if author == 0 and reviewer == 0 else "P"
    direct_edge = "unobserved" if author == 0 and reviewer == 0 else "observed"
    return {"old_joint": old_joint, "author_genuine_P": author, "reviewer_genuine_P": reviewer,
            "genuine_per_route": per_route, "direct_edge": direct_edge}


# ---------------------------------------------------------------- A1
def a1(obj):
    assert set(obj) == {"clause", "mode", "k", "a", "select", "commit"}
    mode, k, a, sel, commit = obj["mode"], obj["k"], obj["a"], obj["select"], obj["commit"]
    assert isinstance(commit, bool) and isinstance(k, int) and isinstance(a, int)
    B = lambda x: x + 1                                          # scalar block
    if mode == "stock":
        assert k == 0
        permitted = {"stock"}
    elif mode == "duplicate":
        assert k == 0
        permitted = {"stock", "duplicate"}
    elif mode == "literal":
        assert k >= 1
        permitted = {"k%d" % k}
    else:
        raise ValueError(mode)
    if sel not in permitted:                                     # before any side effect
        return {"status": "M", "reason": "invalid_selection", "commits": 0, "history": []}
    h0 = B(a)
    calls = [["stock", a, h0]]
    hidden = {"stock": h0}
    if mode == "duplicate":                                      # same input again, disjoint scratch
        hd = B(a)
        calls.append(["duplicate", a, hd])
        hidden["duplicate"] = hd
        decoded = [["stock", h0], ["duplicate", hd]]             # I6: both readouts retained, call order
    elif mode == "literal":
        h = h0
        for j in range(1, k + 1):
            nh = B(h)
            calls.append(["k%d" % j, h, nh])
            h = nh
        hidden["k%d" % k] = h
        decoded = [["k%d" % k, h]]                               # final selected branch only
    else:
        decoded = [["stock", h0]]                                # stock decodes once
    token = hidden[sel]                                          # toy Dec: token = h
    transition = ["u:" + sel, token, "g:" + sel]
    return {"status": "P", "calls": calls, "decoded": decoded, "selected": sel,
            "transition": transition, "commits": 1 if commit else 0,
            "history": [transition] if commit else []}


# ---------------------------------------------------------------- A2
NINF = "ff800000"
PHASES = ["raw", "repeat", "page"]


def word_value(w):
    assert isinstance(w, str) and len(w) == 8 and w == w.lower() and all(c in "0123456789abcdef" for c in w)
    return struct.unpack(">f", bytes.fromhex(w))[0]


def word_finite(w):
    return (int(w, 16) >> 23) & 0xFF != 0xFF                     # exponent not all ones


def a2(obj):
    assert set(obj) == {"clause", "raw", "repeat", "page", "repeat_block", "page_block"}
    raw, rep, page = obj["raw"], obj["repeat"], obj["page"]
    n = len(raw)
    assert n > 0 and len(rep) == n and len(page) == n
    for w in raw + rep + page:
        word_value(w)
    rb, pb = obj["repeat_block"], obj["page_block"]
    assert all(isinstance(i, int) and 0 <= i < n for i in rb + pb)
    conflicts = []
    for i, w in enumerate(raw):                                  # every raw value finite
        if not word_finite(w):
            conflicts.append(["raw", i])
    excl = set(rb)                                               # cumulative exclusion after repeat
    for i in range(n):
        want = NINF if i in excl else raw[i]
        if rep[i] != want:
            conflicts.append(["repeat", i])
    excl |= set(pb)                                              # cumulative exclusion after page
    for i in range(n):
        want = NINF if i in excl else rep[i]                     # immediate supplied predecessor
        if page[i] != want:
            conflicts.append(["page", i])
    allowed = sorted(set(range(n)) - excl)                       # I8: from supplied masks
    if not allowed:
        conflicts.append(["support", -1])
    status = "M" if conflicts else "P"
    winner = None
    if status == "P":
        best = None
        for i in allowed:                                        # ascending: first wins ties (-0 == +0)
            v = word_value(page[i])
            if best is None or v > best:
                best, winner = v, i
    return {"status": status, "first": conflicts[0] if conflicts else None, "conflicts": conflicts,
            "allowed": allowed, "winner": winner, "raw": raw, "repeat": rep, "page": page}


# ---------------------------------------------------------------- C1
def rat(s):
    assert isinstance(s, str)
    f = Fraction(s)
    return f


def rstr(f):
    return str(Fraction(f))                                      # reduced; integers without /1


def c1_exact(F):
    if not F:
        return {"status": "CONFLICT", "action": None}
    m = len(F[0])
    assert all(len(r) == m and all(isinstance(x, int) and not isinstance(x, bool) for x in r) for r in F)
    if len(F) == 1:
        return {"status": "IDENTIFIED", "action": None}
    best = None
    for i in range(m):
        counts = {}
        for r in F:
            counts[r[i]] = counts.get(r[i], 0) + 1
        if len(counts) < 2:
            continue                                              # only varying fields
        score = sum(c * c for c in counts.values())
        if best is None or score < best[0]:
            best = (score, i)
    if best is None:
        return {"status": "CONFLICT", "action": None}            # duplicate candidates: not separable
    return {"status": "QUERY", "action": best[1]}


def gain(post, law):
    s0 = sum(p * p for p in post)
    e = Fraction(0)
    for o in range(len(law[0])):
        po = sum(post[y] * law[y][o] for y in range(len(post)))
        if po == 0:
            continue                                              # skip zero-probability outcomes
        e += po * sum((post[y] * law[y][o] / po) ** 2 for y in range(len(post)))
    return e - s0


def c1_noisy(obj):
    assert set(obj) == {"clause", "mode", "p", "threshold", "budget", "used", "actions", "observation"}
    post = [rat(s) for s in obj["p"]]
    assert all(p > 0 for p in post) and sum(post) == 1
    thr = rat(obj["threshold"])
    budget = obj["budget"]
    assert isinstance(budget, int) and budget >= 0
    used = set(obj["used"])
    actions = {}
    for a in obj["actions"]:
        law = [[rat(x) for x in row] for row in a["law"]]
        assert len(law) == len(post) and all(sum(row) == 1 for row in law)
        assert len({len(row) for row in law}) == 1
        assert a["id"] not in actions
        actions[a["id"]] = (a["source"], law)
    ob = obj["observation"]
    if ob is not None:
        src, law = actions[ob["action"]]
        o = ob["outcome"]
        if src not in used:                                       # a repeat is ignored (I9)
            w = [post[y] * law[y][o] for y in range(len(post))]
            z = sum(w)
            if z == 0:
                return {"status": "MODEL_CONFLICT", "posterior": None, "action": None, "gain": None}
            post = [x / z for x in w]
            if budget > 0:
                budget -= 1
            used.add(src)
    out_post = [rstr(p) for p in post]
    if max(post) >= thr:
        return {"status": "ACCEPT", "posterior": out_post, "action": None, "gain": None}
    if budget == 0:
        return {"status": "UNRESOLVED", "posterior": out_post, "action": None, "gain": None}
    best = None
    for aid in sorted(actions):                                  # ascending id: ties keep smallest
        src, law = actions[aid]
        if src in used:
            continue
        g = gain(post, law)
        if g > 0 and (best is None or g > best[0]):
            best = (g, aid)
    if best is None:
        return {"status": "UNRESOLVED", "posterior": out_post, "action": None, "gain": None}
    return {"status": "QUERY", "posterior": out_post, "action": best[1], "gain": rstr(best[0])}


def c1(obj):
    if obj["mode"] == "exact":
        assert set(obj) == {"clause", "mode", "F"}
        return c1_exact(obj["F"])
    assert obj["mode"] == "noisy"
    return c1_noisy(obj)


# ---------------------------------------------------------------- dispatch by content
def evaluate(obj, repo):
    if "clause" not in obj:
        return q1_constructed(obj)
    c = obj["clause"]
    if c == "Q1":
        return q1_live(obj)
    if c == "archive":
        return archive_old(obj, repo)
    return {"A1": a1, "A2": a2, "C1": c1}[c](obj)


# ---------------------------------------------------------------- independent intent (hand-written)
def _q(nonP, first, src_override=None):
    """Hand-derived intent for a provenance row: nonP = {key: 'M'|'U'}."""
    vals = {k: nonP.get(k, "P") for k in KEYS}
    co = {"L": "P", "I": "P", "E": "P", "A": "P", "C": "P", "B": "P"}
    for k, v in nonP.items():
        g = k[0]
        if v == "M" or co[g] == "P":
            co[g] = v if co[g] != "M" else "M"
    reason = {}
    for k, v in nonP.items():
        reason[k] = "unresolved" if v == "U" else {"E.caller": "wrong_origin", "B.origin": "wrong_origin",
                                                  "B.writer": "unauthorized_writer"}.get(k, "integrity")
    src = dict(CANON_SOURCE)
    src.update(src_override or {})
    return vals, co, reason, first, src


INTENT_Q = {
    "N.A": ({}, None, "P", "P"),
    "N.B": ({}, None, "P", "P"),
    "Q.other_caller": ({"E.caller": "M"}, {"at": 3, "keys": ["E.caller"]}, "M", "M"),
    "Q.no_caller": ({"E.caller": "U"}, {"at": 3, "keys": ["E.caller"]}, "U", "U"),
    "Q.other_writer": ({"B.writer": "M"}, {"at": 6, "keys": ["B.writer"]}, "M", "M"),
    "Q.no_writer": ({"B.writer": "U"}, {"at": 6, "keys": ["B.writer"]}, "U", "U"),
    "Q.mixed": ({"E.caller": "M", "B.writer": "U"}, {"at": 3, "keys": ["E.caller"]}, "M", "M"),
    "Q.other_original": ({"B.origin": "M"}, {"at": 8, "keys": ["B.origin"]}, "M", "M"),
    "Q.detached": ({"B.direct": "U", "B.origin": "U"}, {"at": 8, "keys": ["B.direct", "B.origin"]}, "U", "U"),
    "Q.bad_seal": ({"B.seal": "M", "B.direct": "U", "B.origin": "U"}, {"at": 7, "keys": ["B.seal"]}, "M", "M"),
    "Q.unordered": ({"E.caller": "U", "B.writer": "M"}, {"at": None, "keys": ["B.writer", "E.caller"]}, "M", "M"),
}
INTENT_SRC = {"Q.unordered": {"E.caller": "unobserved"}}


def intent_q(rid):
    nonP, first, status, custody = INTENT_Q[rid]
    vals, co, reason, first, src = _q(nonP, first, INTENT_SRC.get(rid))
    return {"status": status, "values": vals, "coordinates": co, "custody": custody, "content": "P",
            "conflicts": sorted(k for k, v in nonP.items() if v == "M"),
            "missing": sorted(k for k, v in nonP.items() if v == "U"),
            "reason": reason, "first": first, "source": src}


def _t(b, h):
    return ["u:" + b, h, "g:" + b]


INTENT_OTHER = {
    "H.old": {"old_joint": "U", "author_genuine_P": 0, "reviewer_genuine_P": 0,
              "genuine_per_route": 2, "direct_edge": "unobserved"},
    "A1.stock": {"status": "P", "calls": [["stock", 41, 42]], "decoded": [["stock", 42]], "selected": "stock",
                 "transition": _t("stock", 42), "commits": 1, "history": [_t("stock", 42)]},
    "A1.duplicate_first": {"status": "P", "calls": [["stock", -7, -6], ["duplicate", -7, -6]],
                           "decoded": [["stock", -6], ["duplicate", -6]], "selected": "stock",
                           "transition": _t("stock", -6), "commits": 1, "history": [_t("stock", -6)]},
    "A1.duplicate_second_private": {"status": "P", "calls": [["stock", 0, 1], ["duplicate", 0, 1]],
                                    "decoded": [["stock", 1], ["duplicate", 1]], "selected": "duplicate",
                                    "transition": _t("duplicate", 1), "commits": 0, "history": []},
    "A1.duplicate_second_commit": {"status": "P", "calls": [["stock", 12, 13], ["duplicate", 12, 13]],
                                   "decoded": [["stock", 13], ["duplicate", 13]], "selected": "duplicate",
                                   "transition": _t("duplicate", 13), "commits": 1,
                                   "history": [_t("duplicate", 13)]},
    "A1.literal": {"status": "P", "calls": [["stock", 5, 6], ["k1", 6, 7], ["k2", 7, 8], ["k3", 8, 9]],
                   "decoded": [["k3", 9]], "selected": "k3", "transition": _t("k3", 9), "commits": 1,
                   "history": [_t("k3", 9)]},
    "A1.invalid": {"status": "M", "reason": "invalid_selection", "commits": 0, "history": []},
    # A2: (status, first, conflicts, allowed, winner); raw/repeat/page echoed from input
    "A2.clean": ("P", None, [], [0, 2, 4, 5], 2),
    "A2.masked_nan": ("M", ["raw", 1], [["raw", 1], ["raw", 3]], [0, 2], None),
    "A2.raw_inf": ("M", ["raw", 1], [["raw", 1], ["raw", 3]], [1, 2], None),
    "A2.illegal_repeat": ("M", ["repeat", 1], [["repeat", 1], ["repeat", 2], ["page", 4]], [1, 3, 4], None),
    "A2.signed_zero": ("P", None, [], [1, 2, 3], 1),
    "A2.empty": ("M", ["support", -1], [["support", -1]], [], None),
    "C1.exact": {"status": "QUERY", "action": 1},
    "C1.uninformative": {"status": "UNRESOLVED", "posterior": ["1/4", "1/4", "1/2"], "action": None, "gain": None},
    "C1.informative": {"status": "QUERY", "posterior": ["9/13", "2/13", "2/13"], "action": 2, "gain": "54/169"},
    "C1.duplicate": {"status": "QUERY", "posterior": ["3/5", "2/5"], "action": 2, "gain": "9/175"},
    "C1.impossible": {"status": "MODEL_CONFLICT", "posterior": None, "action": None, "gain": None},
    "C1.budget": {"status": "UNRESOLVED", "posterior": ["1/4", "3/4"], "action": None, "gain": None},
    "C1.threshold": {"status": "ACCEPT", "posterior": ["4/5", "1/5"], "action": None, "gain": None},
    "C1.tie": {"status": "QUERY", "posterior": ["1/2", "1/2"], "action": 4, "gain": "1/8"},
}


def intent(rid, obj):
    if rid in INTENT_Q:
        return intent_q(rid)
    v = INTENT_OTHER[rid]
    if rid.startswith("A2."):
        st, first, conf, allowed, win = v
        return {"status": st, "first": first, "conflicts": conf, "allowed": allowed, "winner": win,
                "raw": obj["raw"], "repeat": obj["repeat"], "page": obj["page"]}
    return v


# ---------------------------------------------------------------- driver
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    fx, out = Path(a.fixtures), Path(a.out)
    mbytes = (fx / "manifest.json").read_bytes()
    man = json.loads(mbytes)
    assert man["version"] == "wp0045.fixtures.v1" and len(man["rows"]) == 32
    (out / "expected").mkdir(parents=True, exist_ok=True)
    rows, mism = {}, []
    for r in man["rows"]:
        data = (fx / r["input"]["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == r["input"]["sha256"], r["input"]["path"]
        obj = json.loads(data.decode("utf-8"))
        got = evaluate(obj, Path(a.repo))
        if canon(got) != canon(intent(r["id"], obj)):
            mism.append(r["id"])
        enc = encode_row(got)
        rel = "expected/%s.json" % r["id"]
        (out / rel).write_bytes(enc)
        rows[r["id"]] = {"path": rel, "sha256": hashlib.sha256(enc).hexdigest(), "bytes": len(enc)}
    em = {"version": "wp0045.expected.v1", "packet": "WP-0045", "owner": "eld-fixture-claude",
          "nonce": COMMITMENT_NONCE,
          "fixture_manifest_sha256": hashlib.sha256(mbytes).hexdigest(),
          "row_encoding": "one unwrapped projected row per file; canonical JSON sort_keys, separators (',',':'), ensure_ascii=false, UTF-8, one LF",
          "rows": rows}
    (out / "expected-manifest.json").write_bytes((json.dumps(em, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print("rows %d; intent mismatches %d %s" % (len(rows), len(mism), mism))
    return 1 if mism else 0


if __name__ == "__main__":
    sys.exit(main())
