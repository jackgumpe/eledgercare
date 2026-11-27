"""WP-0045 blind fixture generator (eld-fixture-claude).

Writes inputs/<sha16>.json for all 32 scheduled rows and manifest.json.
Standard library only; CPython 3.12.10.  No case ID, label, verdict or
expected answer is written into any input file; the row-to-file mapping
exists only in manifest.json.

Usage:
    python -I build_fixtures.py           # (re)generate
    python -I build_fixtures.py --check   # re-derive every byte, report mismatches

Input encoding (fixed): UTF-8, json.dumps(obj, ensure_ascii=False,
separators=(",", ":")) with the member order constructed below (NOT
sorted), followed by one LF.  Integers only; rationals are strings; FP32
words are 8 lowercase hex digits.  Wire equality is canonical typed JSON,
so member order inside objects is never significant, and some constructed
records deliberately present nested `observed` members in a different
order from `expected`.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKET = "WP-0045"
SEED = "wp0045-fixture-claude-public-construction-v1"

ATOMS = [  # schedule.json order; source token, logical checkpoint
    ("L.image", "supervisor_image", 1),
    ("I.image", "child_image", 3),
    ("E.caller", "call_return_join", 3),
    ("E.child", "creation_instance", 3),
    ("E.order", "creation_order", 3),
    ("E.job", "job_membership", 3),
    ("A.command", "command_manifest", 4),
    ("C.runtime", "runtime_manifest", 5),
    ("B.writer", "writer_account", 6),
    ("B.seal", "authenticated_seal", 7),
    ("B.protection", "protected_lifetime", 8),
    ("B.direct", "direct_handle", 8),
    ("B.origin", "authenticated_origin", 8),
    ("B.members", "member_inventory", 8),
    ("content.bytes", "scorer_read", 8),
]


def h(*parts, n=64):
    return hashlib.sha256("|".join((SEED,) + tuple(map(str, parts))).encode()).hexdigest()[:n]


def num(*parts, lo=1000, span=60000):
    return lo + int(h(*parts, n=12), 16) % span


def ident(r, role):
    """Creation-scoped process identity: pid plus creation FILETIME."""
    return {"pid": num(r, role, "pid", lo=1200, span=50000),
            "created": 134400000000000000 + int(h(r, role, "ft", n=14), 16) % 10**13}


def file_id(r, role):
    return {"volume": h(r, role, "vol", n=8), "index": num(r, role, "idx", lo=10**6, span=10**9)}


def base_values(r):
    """Ideal frozen expectation for one constructed record r (opaque seed)."""
    sup = ident(r, "supervisor")
    child = ident(r, "child")
    worker = ident(r, "worker")
    original = "orig-" + h(r, "original", n=20)
    payload = "4630370a"
    return {
        "L.image": {"image": {"path": "X:\\wp0045\\sup\\python.exe",
                              "sha256": h(r, "sup-image"),
                              "file": file_id(r, "sup-image")},
                    "script": {"path": "X:\\wp0045\\sup\\supervisor.py",
                               "sha256": h(r, "sup-script")}},
        "I.image": {"path": "X:\\wp0045\\base\\Python312\\python.exe",
                    "sha256": h(r, "child-image"),
                    "file": file_id(r, "child-image")},
        "E.caller": sup,
        "E.child": child,
        "E.order": ["call", "create", "job_assign", "resume", "execute"],
        "E.job": {"job": "job-" + h(r, "job", n=16), "child": child, "before_execution": True},
        "A.command": {"argv": ["X:\\wp0045\\base\\Python312\\python.exe", "-I", "-B", "worker.py", "--write", "1"],
                      "original_argv": ["supervisor.py", "--arm", h(r, "arm", n=8)],
                      "cwd": "X:\\wp0045\\run\\caf\u00e9",
                      "flags": ["CREATE_SUSPENDED", "CREATE_UNICODE_ENVIRONMENT"]},
        "C.runtime": {"executable": "X:\\wp0045\\base\\Python312\\python.exe",
                      "prefix": "X:\\wp0045\\base\\Python312",
                      "base_prefix": "X:\\wp0045\\base\\Python312",
                      "sys_path": ["X:\\wp0045\\base\\Python312\\python312.zip",
                                   "X:\\wp0045\\base\\Python312\\DLLs",
                                   "X:\\wp0045\\base\\Python312\\Lib"],
                      "pyvenv_cfg": None,
                      "pth": [],
                      "sitecustomize": None,
                      "env": {"PYTHONHOME": None, "PYTHONPATH": None, "PYTHONSAFEPATH": ""},
                      "threads": 1},
        "B.writer": [{"process": worker, "access": "write", "count": 1}],
        "B.seal": {"alg": "hmac-sha256", "key_id": "k-" + h(r, "key", n=8),
                   "over": h(r, "sealed-tuple"), "tag": h(r, "tag")},
        "B.protection": {"share": "read", "from": "create", "to": "scorer_read", "gaps": 0},
        "B.direct": {"handle_source": "worker_transfer", "access": "read", "object": file_id(r, "sink")},
        "B.origin": {"original": original, "created_by": worker},
        "B.members": [{"name": "payload.bin", "bytes": 4, "sha256": hashlib.sha256(bytes.fromhex(payload)).hexdigest()}],
        "content.bytes": payload,
    }


def reorder(v):
    """Same JSON value, object members in reverse insertion order (recursively)."""
    if isinstance(v, dict):
        return {k: reorder(v[k]) for k in reversed(list(v))}
    if isinstance(v, list):
        return [reorder(x) for x in v]
    return v


def constructed(r, variation):
    """Build {expected, observed, evidence} for one constructed record."""
    exp = base_values(r)
    obs = {k: reorder(v) if k in ("C.runtime", "A.command", "L.image") else v for k, v in exp.items()}
    ev = {k: {"source": s, "at": at} for k, s, at in ATOMS}
    other = "o" + r
    for kind, key in variation:
        if kind == "differs":
            if key == "E.caller":  # different creating instance, same numeric PID (reuse trap)
                obs[key] = {"pid": exp[key]["pid"], "created": exp[key]["created"] + 7_000_000}
            elif key == "B.writer":  # additional unallowlisted writable alias
                obs[key] = exp[key] + [{"process": ident(other, "alias"), "access": "write", "count": 1}]
            elif key == "B.origin":  # a different authenticated original with equal bytes
                obs[key] = {"original": "orig-" + h(other, "original", n=20), "created_by": ident(other, "worker")}
            elif key == "B.seal":
                obs[key] = dict(exp[key], tag=h(other, "tag"))
            else:
                raise ValueError(key)
        elif kind == "omitted":  # absence identifiable at its prescribed (witnessed) cut
            del obs[key]
        elif kind == "unobserved":  # cut never witnessed
            del obs[key]
            ev[key] = {"source": "unobserved", "at": None}
        else:
            raise ValueError(kind)
    return {"expected": exp, "observed": obs, "evidence": ev}


# --- schedule rows (schedule.json order) --------------------------------------------
Q_CONSTRUCTED = [
    ("Q.other_caller", [("differs", "E.caller")]),
    ("Q.no_caller", [("omitted", "E.caller")]),
    ("Q.other_writer", [("differs", "B.writer")]),
    ("Q.no_writer", [("omitted", "B.writer")]),
    ("Q.mixed", [("differs", "E.caller"), ("omitted", "B.writer")]),
    ("Q.other_original", [("differs", "B.origin")]),
    ("Q.detached", [("omitted", "B.direct"), ("omitted", "B.origin")]),
    ("Q.bad_seal", [("differs", "B.seal"), ("omitted", "B.direct"), ("omitted", "B.origin")]),
    ("Q.unordered", [("unobserved", "E.caller"), ("differs", "B.writer")]),
]


def a1(mode, k, a, select, commit):
    return {"clause": "A1", "mode": mode, "k": k, "a": a, "select": select, "commit": commit}


def a2(raw, repeat, page, repeat_block, page_block):
    return {"clause": "A2", "raw": raw, "repeat": repeat, "page": page,
            "repeat_block": repeat_block, "page_block": page_block}


def noisy(p, threshold, budget, used, actions, observation):
    return {"clause": "C1", "mode": "noisy", "p": p, "threshold": threshold, "budget": budget,
            "used": used, "actions": [{"id": i, "source": s, "law": law} for i, s, law in actions],
            "observation": None if observation is None else {"action": observation[0], "outcome": observation[1]}}


NINF = "ff800000"
ROWS = []  # (id, family, clause, input-object)
ROWS.append(("N.A", "Q1.live", "Q1", {"clause": "Q1", "selection": 0, "payload_hex": "4630370a"}))
ROWS.append(("N.B", "Q1.live", "Q1", {"clause": "Q1", "selection": 1, "payload_hex": "4630370a"}))
for i, (rid, var) in enumerate(Q_CONSTRUCTED):
    ROWS.append((rid, "Q1.constructed", "Q1", constructed("r%02d" % (i + 3), var)))
ROWS.append(("H.old", "Q1.archive", "archive", {"clause": "archive", "packet": "WP-0044"}))

ROWS += [
    ("A1.stock", "A1", "A1", a1("stock", 0, 41, "stock", True)),
    ("A1.duplicate_first", "A1", "A1", a1("duplicate", 0, -7, "stock", True)),
    ("A1.duplicate_second_private", "A1", "A1", a1("duplicate", 0, 0, "duplicate", False)),
    ("A1.duplicate_second_commit", "A1", "A1", a1("duplicate", 0, 12, "duplicate", True)),
    ("A1.literal", "A1", "A1", a1("literal", 3, 5, "k3", True)),
    ("A1.invalid", "A1", "A1", a1("literal", 2, 3, "k1", True)),
]

ROWS += [
    ("A2.clean", "A2", "A2", a2(
        ["3f800000", "40800000", "3fc00000", "40400000", "bf800000", "00000001"],
        ["3f800000", NINF, "3fc00000", "40400000", "bf800000", "00000001"],
        ["3f800000", NINF, "3fc00000", NINF, "bf800000", "00000001"],
        [1], [3])),
    ("A2.masked_nan", "A2", "A2", a2(
        ["40000000", "7fc00000", "3f800000", "ffc00000"],
        ["40000000", NINF, "3f800000", "ffc00000"],
        ["40000000", NINF, "3f800000", NINF],
        [1], [3])),
    ("A2.raw_inf", "A2", "A2", a2(
        ["3f800000", "7f800000", "40000000", NINF],
        ["3f800000", "7f800000", "40000000", NINF],
        [NINF, "7f800000", "40000000", NINF],
        [3], [0])),
    ("A2.illegal_repeat", "A2", "A2", a2(
        ["3f800000", "40000000", "40400000", "3f000000", "c0000000"],
        ["3f800000", "40000001", "ff7fffff", "3f000000", "c0000000"],
        [NINF, "40000001", NINF, "3f000000", "40000000"],
        [2], [0])),
    ("A2.signed_zero", "A2", "A2", a2(
        ["40000000", "80000000", "bf800000", "00000000", "c0000000"],
        [NINF, "80000000", "bf800000", "00000000", "c0000000"],
        [NINF, "80000000", "bf800000", "00000000", NINF],
        [0], [4])),
    ("A2.empty", "A2", "A2", a2(
        ["3f800000", "40000000", "3f000000"],
        [NINF, "40000000", NINF],
        [NINF, NINF, NINF],
        [0, 2], [1])),
]

ROWS += [
    ("C1.exact", "C1", "C1", {"clause": "C1", "mode": "exact",
                              "F": [[5, 1, 1, 0], [5, 2, 1, 0], [5, 1, 1, 1], [5, 2, 2, 1]]}),
    ("C1.uninformative", "C1", "C1", noisy(
        ["1/4", "1/4", "1/2"], "3/4", 2, ["s-used"],
        [(1, "s-used", [["1", "0"], ["0", "1"], ["1/2", "1/2"]]),
         (2, "s-flat", [["1/3", "2/3"], ["1/3", "2/3"], ["1/3", "2/3"]]),
         (3, "s-single", [["1"], ["1"], ["1"]])],
        None)),
    ("C1.informative", "C1", "C1", noisy(
        ["1/2", "1/3", "1/6"], "9/10", 3, ["s-prior"],
        [(1, "s-north", [["3/4", "1/4"], ["1/4", "3/4"], ["1/2", "1/2"]]),
         (2, "s-east", [["1", "0", "0"], ["0", "1", "0"], ["0", "1", "0"]]),
         (4, "s-west", [["1/2", "1/2", "0"], ["1/2", "1/2", "0"], ["0", "0", "1"]]),
         (5, "s-south", [["1/2", "1/2", "0"], ["1/2", "1/2", "0"], ["1/2", "1/2", "0"]])],
        (1, 0))),
    ("C1.duplicate", "C1", "C1", noisy(
        ["3/5", "2/5"], "9/10", 2, ["s-old"],
        [(1, "s-old", [["9/10", "1/10"], ["1/10", "9/10"]]),
         (2, "s-new", [["2/3", "1/3"], ["1/3", "2/3"]])],
        (1, 0))),
    ("C1.impossible", "C1", "C1", noisy(
        ["1/3", "2/3"], "9/10", 2, [],
        [(1, "s-a", [["3/4", "1/4"], ["1/4", "3/4"]]),
         (2, "s-b", [["1", "0"], ["1", "0"]])],
        (2, 1))),
    ("C1.budget", "C1", "C1", noisy(
        ["2/5", "3/5"], "19/20", 1, [],
        [(1, "s-x", [["2/3", "1/3"], ["1/3", "2/3"]]),
         (2, "s-y", [["9/10", "1/10"], ["1/10", "9/10"]])],
        (1, 1))),
    ("C1.threshold", "C1", "C1", noisy(
        ["1/2", "1/2"], "4/5", 2, [],
        [(1, "s-a", [["4/5", "1/5"], ["1/5", "4/5"]]),
         (2, "s-c", [["2/3", "1/3"], ["1/3", "2/3"]])],
        (1, 0))),
    ("C1.tie", "C1", "C1", noisy(
        ["1/2", "1/2"], "9/10", 1, [],
        [(9, "s-p", [["3/4", "1/4"], ["1/4", "3/4"]]),
         (4, "s-q", [["1/4", "3/4"], ["3/4", "1/4"]]),
         (6, "s-r", [["2/3", "1/3"], ["1/3", "2/3"]])],
        None)),
]


def encode(obj):
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def schedule_ids():
    sched = json.loads((HERE.parents[2] / "docs" / "coordination" / PACKET / "schedule.json").read_text(encoding="utf-8"))
    rows = sched["rows"]
    return [i for grp in ("live", "constructed", "archive", "A1", "A2", "C1") for i in rows[grp]]


def build():
    ids = [r[0] for r in ROWS]
    assert ids == schedule_ids(), "row inventory/order differs from schedule.json"
    assert len(ids) == 32 and len(set(ids)) == 32
    files, rows = {}, []
    for rid, family, clause, obj in ROWS:
        data = encode(obj)
        digest = hashlib.sha256(data).hexdigest()
        path = "inputs/%s.json" % digest[:16]
        assert path not in files, "duplicate input bytes"
        files[path] = data
        rows.append({"id": rid, "family": family, "clause": clause, "repetitions": 1,
                     "input": {"path": path, "sha256": digest, "bytes": len(data)}})
    gen = (HERE / "build_fixtures.py").read_bytes()
    manifest = {
        "version": "wp0045.fixtures.v1",
        "packet": PACKET,
        "owner": "eld-fixture-claude",
        "reservation_commit": "1439d0c944a38d0993283b0485f59daa15b73be4",
        "reservation_parent": "7f9281bd247e312bbce89af9a3021832fca965da",
        "denominators": {"Q1": 12, "A1": 6, "A2": 6, "C1": 8, "total": 32},
        "input_encoding": "UTF-8 JSON, ensure_ascii=false, separators (',',':'), constructed member order, one trailing LF; no case ID, label or answer in data",
        "q1_atoms": [{"key": k, "source": s, "at": at} for k, s, at in ATOMS],
        "generator": {"path": "build_fixtures.py", "sha256": hashlib.sha256(gen).hexdigest(), "bytes": len(gen)},
        "rows": rows,
        "files": {p: {"sha256": hashlib.sha256(d).hexdigest(), "bytes": len(d)} for p, d in sorted(files.items())},
    }
    files["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    return files


def main(argv):
    files = build()
    if "--check" in argv:
        bad = [p for p, d in files.items() if not (HERE / p).is_file() or (HERE / p).read_bytes() != d]
        extra = sorted(str(p.relative_to(HERE)).replace("\\", "/") for p in (HERE / "inputs").glob("*")
                       if str(p.relative_to(HERE)).replace("\\", "/") not in files)
        print("%d files checked, %d mismatched, %d unexpected" % (len(files), len(bad), len(extra)))
        for p in bad + extra:
            print("  ", p)
        return 1 if bad or extra else 0
    (HERE / "inputs").mkdir(exist_ok=True)
    for p, d in files.items():
        (HERE / p).write_bytes(d)
    print("wrote %d files" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
