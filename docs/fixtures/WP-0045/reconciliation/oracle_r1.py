"""WP-0045 post-opening A2 oracle correction r1 (eld-fixture-claude).

Version wp0045.expected.r1.  Written AFTER opening and after the coordinator
reported that both frozen candidates and the sealed oracle differ on
[page,2] in A2.illegal_repeat.  It is NOT a blind oracle.

The opened oracle (docs/fixtures/WP-0045/opened/oracle.py, sha256 74feda7a...)
is left byte-for-byte unchanged.  This module loads it read-only after
verifying its digest, and replaces exactly one function: the A2 phase
comparison.  Every other clause, row and intent entry is reused.

Correction.  Opened I6 compared the page phase with the CUMULATIVE mask
(repeat_block | page_block).  The pre-input wire (wire.md at 1439d0c9,
A2 paragraph) says each later phase changes "those words only" (its own
blocked IDs) and that conflicts are found by "comparing each phase to its
immediate supplied predecessor and its stipulated own mask".  r1 therefore
checks, for phase f in (repeat, page) with predecessor p and own block b_f:
    conflict [f, i]  iff  f[i] != (ff800000 if i in b_f else p[i])   (bitwise)
The cumulative exclusion is used only for `allowed` (support), unchanged.

    python -I -B oracle_r1.py --repo <worktree> [--out <dir>]
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
FX = HERE.parent
OPENED = FX / "opened"
VERSION = "wp0045.expected.r1"
OPENED_ORACLE_SHA = "74feda7a2175b34efc907106443e76ad530263f0b1166970fbd9aa33a1f0fb8d"
OPENED_EXPECTED_MANIFEST_SHA = "4e7587eb3fd473449068c4c69416b08e1cf947b340532514f11d2e6df6b312e3"
FIXTURE_MANIFEST_SHA = "2c15a26dd1a4d6c5da68c8c5f57e54f0994f75b5926f09ae24b4b6d9e44c0cc0"


def load_opened():
    path = OPENED / "oracle.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == OPENED_ORACLE_SHA, "opened oracle changed"
    spec = importlib.util.spec_from_file_location("wp0045_oracle_v1", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


O = load_opened()
V1_A2 = O.a2  # the opened (v1) A2 evaluator, kept for comparison only
NINF = O.NINF


def a2_r1(obj):
    """A2 with own-phase-mask comparison against the immediate supplied predecessor."""
    assert set(obj) == {"clause", "raw", "repeat", "page", "repeat_block", "page_block"}
    raw, rep, page = obj["raw"], obj["repeat"], obj["page"]
    n = len(raw)
    assert n > 0 and len(rep) == n and len(page) == n
    for w in raw + rep + page:
        O.word_value(w)
    rb, pb = obj["repeat_block"], obj["page_block"]
    assert all(isinstance(i, int) and 0 <= i < n for i in rb + pb)
    conflicts = [["raw", i] for i, w in enumerate(raw) if not O.word_finite(w)]
    for phase, cur, pred, own in (("repeat", rep, raw, set(rb)), ("page", page, rep, set(pb))):
        for i in range(n):
            want = NINF if i in own else pred[i]
            if cur[i] != want:
                conflicts.append([phase, i])
    allowed = sorted(set(range(n)) - set(rb) - set(pb))      # cumulative exclusion: support only
    if not allowed:
        conflicts.append(["support", -1])
    status = "M" if conflicts else "P"
    winner = None
    if status == "P":
        best = None
        for i in allowed:
            v = O.word_value(page[i])
            if best is None or v > best:
                best, winner = v, i
    return {"status": status, "first": conflicts[0] if conflicts else None, "conflicts": conflicts,
            "allowed": allowed, "winner": winner, "raw": raw, "repeat": rep, "page": page}


# Hand-written r1 intent for the one row whose v1 intent changes; all others reuse v1 intent.
INTENT_R1_A2 = {
    "A2.illegal_repeat": ("M", ["repeat", 1], [["repeat", 1], ["repeat", 2], ["page", 2], ["page", 4]], [1, 3, 4], None),
}


def evaluate_r1(obj, repo):
    if isinstance(obj, dict) and obj.get("clause") == "A2":
        return a2_r1(obj)
    return O.evaluate(obj, repo)


def intent_r1(rid, obj):
    if rid in INTENT_R1_A2:
        st, first, conf, allowed, win = INTENT_R1_A2[rid]
        return {"status": st, "first": first, "conflicts": conf, "allowed": allowed, "winner": win,
                "raw": obj["raw"], "repeat": obj["repeat"], "page": obj["page"]}
    return O.intent(rid, obj)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args(argv)
    out = Path(a.out)
    mbytes = (FX / "manifest.json").read_bytes()
    assert hashlib.sha256(mbytes).hexdigest() == FIXTURE_MANIFEST_SHA, "fixture manifest changed"
    ebytes = (OPENED / "expected-manifest.json").read_bytes()
    assert hashlib.sha256(ebytes).hexdigest() == OPENED_EXPECTED_MANIFEST_SHA, "opened expected manifest changed"
    man, em1 = json.loads(mbytes), json.loads(ebytes)
    (out / "expected-r1").mkdir(parents=True, exist_ok=True)
    rows, diffs, mism, v1_repro = {}, [], [], 0
    for r in man["rows"]:
        rid = r["id"]
        data = (FX / r["input"]["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == r["input"]["sha256"], rid
        obj = json.loads(data.decode("utf-8"))
        v1_bytes = (OPENED / em1["rows"][rid]["path"]).read_bytes()
        assert hashlib.sha256(v1_bytes).hexdigest() == em1["rows"][rid]["sha256"], rid
        if O.encode_row(O.evaluate(obj, Path(a.repo))) == v1_bytes:
            v1_repro += 1
        got = evaluate_r1(obj, Path(a.repo))
        if O.canon(got) != O.canon(intent_r1(rid, obj)):
            mism.append(rid)
        enc = O.encode_row(got)
        rel = "expected-r1/%s.json" % rid
        (out / rel).write_bytes(enc)
        rows[rid] = {"path": rel, "sha256": hashlib.sha256(enc).hexdigest(), "bytes": len(enc)}
        if enc != v1_bytes:
            v1 = json.loads(v1_bytes)
            fields = sorted(k for k in set(v1) | set(got) if O.canon(v1.get(k)) != O.canon(got.get(k)))
            diffs.append({"id": rid, "fields": fields,
                          "v1": {k: v1.get(k) for k in fields}, "r1": {k: got.get(k) for k in fields}})
    em = {"version": VERSION, "packet": "WP-0045", "owner": "eld-fixture-claude",
          "post_opening": True,
          "supersedes_for_reconciliation_only": {"version": "wp0045.expected.v1", "sha256": OPENED_EXPECTED_MANIFEST_SHA},
          "fixture_manifest_sha256": FIXTURE_MANIFEST_SHA,
          "row_encoding": "identical to v1: canonical JSON sort_keys, separators (',',':'), ensure_ascii=false, UTF-8, one LF",
          "rows": rows}
    (out / "expected-r1-manifest.json").write_bytes((json.dumps(em, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    rec = {"version": VERSION, "rows": len(rows), "v1_reproduced": v1_repro, "intent_mismatches": mism,
           "differences": diffs}
    (out / "recompute.json").write_bytes((json.dumps(rec, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print("rows %d; v1 reproduced %d/%d; r1 intent mismatches %d %s; rows differing from v1 %d %s"
          % (len(rows), v1_repro, len(rows), len(mism), mism, len(diffs), [d["id"] for d in diffs]))
    return 1 if mism or v1_repro != len(rows) else 0


if __name__ == "__main__":
    sys.exit(main())
