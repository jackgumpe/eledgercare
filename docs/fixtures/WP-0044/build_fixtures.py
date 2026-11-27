"""WP-0044 fixture generator (eld-fixture-claude).

Writes blinded constructed records and mathematical-control inputs plus a
versioned manifest for all 33 scheduled rows. Standard library only; no
process launch, model, device, network or candidate code.

Records never contain a case ID, injection label or expectation. The row-to-file
mapping lives only in manifest.json, which is external to every record.

    python -I build_fixtures.py           # (re)generate inputs/ and manifest.json
    python -I build_fixtures.py --check   # verify inputs/ and manifest.json bytes
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
VERSION = "wp0044.fixtures.v1"
RECORD_SCHEMA = "wp0044.record.v1"
BASE_COMMIT = "eb2b09c176cf3793ea9e9f930b913b9769d516e8"
RESERVATION_PARENT = "13753c13893232a58bc38e5f0ebc5a476fc746bb"
ARCHIVE_PATH = "docs/coordination/WP-0043/native-evidence.json"
ARCHIVE_SHA256 = "66eb8bd4a1d51b813f7de7a846ce841238614017cb9c5970ebd82595a42218bb"
PAYLOAD = b"F07\n"  # 46 30 37 0A, the four-byte genuine payload

KEYS = [
    "L.image", "I.image",
    "E.launcher", "E.parent", "E.order", "E.instance", "E.job",
    "A.script", "A.args",
    "C.pyvenv", "C.include_system", "C.pth", "C.sitecustomize",
    "C.PYTHONHOME", "C.PYTHONPATH", "C.PYTHONSAFEPATH",
    "C.CUBLAS_WORKSPACE_CONFIG", "C.CUDA_VISIBLE_DEVICES",
    "C.prefix", "C.modules",
    "B.writer", "B.seal", "B.protection", "B.direct", "B.origin", "B.members",
    "content.bytes",
]

# Realistic observation order of a run; the record's "seq" values follow it.
OBSERVATION_ORDER = [
    "E.launcher", "L.image", "E.instance", "E.parent", "I.image", "E.order", "E.job",
    "A.script", "A.args",
    "C.pyvenv", "C.include_system", "C.pth", "C.sitecustomize",
    "C.PYTHONHOME", "C.PYTHONPATH", "C.PYTHONSAFEPATH",
    "C.CUBLAS_WORKSPACE_CONFIG", "C.CUDA_VISIBLE_DEVICES",
    "C.prefix", "C.modules",
    "B.writer", "B.members", "B.seal", "B.protection", "B.direct", "B.origin",
    "content.bytes",
]
assert sorted(OBSERVATION_ORDER) == sorted(KEYS)

METHOD = {
    "E.launcher": "supervisor_create_handle",
    "L.image": "live_image_digest",
    "E.instance": "process_instance_key",
    "E.parent": "parent_instance_query",
    "I.image": "live_image_digest",
    "E.order": "ordered_process_events",
    "E.job": "job_membership_query",
    "A.script": "script_digest",
    "A.args": "argv_capture",
    "C.pyvenv": "file_digest",
    "C.include_system": "config_probe",
    "C.pth": "site_inventory",
    "C.sitecustomize": "site_inventory",
    "C.PYTHONHOME": "environment_probe",
    "C.PYTHONPATH": "environment_probe",
    "C.PYTHONSAFEPATH": "environment_probe",
    "C.CUBLAS_WORKSPACE_CONFIG": "environment_probe",
    "C.CUDA_VISIBLE_DEVICES": "environment_probe",
    "C.prefix": "config_probe",
    "C.modules": "module_inventory",
    "B.writer": "writer_audit",
    "B.members": "member_inventory",
    "B.seal": "receipt_authentication",
    "B.protection": "protection_witness",
    "B.direct": "scorer_handle_identity",
    "B.origin": "receipt_mapping",
    "content.bytes": "content_read",
}

# Contract constants shared by every constructed record (synthetic digests).
def _d(label: str) -> str:
    return "sha256:" + hashlib.sha256(("wp0044-synthetic:" + label).encode()).hexdigest()

APPROVED_L = _d("launcher-image")
APPROVED_I = _d("interpreter-image")
SCRIPT = _d("inert-writer-script")
PYVENV = _d("pyvenv.cfg include-system-site-packages=false")
MODULES = [
    {"name": "_io", "builtin": True},
    {"name": "builtins", "builtin": True},
    {"name": "encodings", "path": "X:\\wp0044\\base\\Lib\\encodings\\__init__.py",
     "sha256": _d("encodings/__init__.py")[7:]},
    {"name": "site", "path": "X:\\wp0044\\base\\Lib\\site.py", "sha256": _d("site.py")[7:]},
]
ARGS = ["-I", "-B", "inert_writer.py", "emit"]


# ---------------------------------------------------------------- schedule
SCHEDULE = [
    ("W1.A", "live"), ("W1.B", "live"), ("W2.other", "live"), ("W4.denied", "live"),
    ("B1.original", "live"), ("B2.other", "live"), ("B3.copy", "live"),
    ("B4.invalid", "live"), ("B4.unavailable", "live"), ("B5.reopen", "live"),
    ("W2.helper", "constructed"), ("W3.missing", "constructed"),
    ("W3.late_missing", "constructed"), ("W3.reuse", "constructed"),
    ("W4.bad_I", "constructed"), ("W4.no_I", "constructed"), ("W4.bad_L", "constructed"),
    ("W5.args", "constructed"), ("W5.script", "constructed"), ("W5.config", "constructed"),
    ("W5.empty", "constructed"), ("W5.unobserved", "constructed"),
    ("W6.escape", "constructed"), ("W6.writer", "constructed"),
    ("B5.member_missing", "constructed"), ("B5.writer_missing", "constructed"),
    ("archive.gaps", "archive"), ("archive.support", "archive"), ("archive.verdict", "archive"),
    ("math.shift", "mathematical"), ("math.tie", "mathematical"),
    ("math.signed_zero", "mathematical"), ("math.linked", "mathematical"),
]

LIVE_CONSTRUCTION = {
    "W1.A": "Genuine arm A: approved venv launcher, its base interpreter child, sealed protected output, configured keys.",
    "W1.B": "Genuine arm B: second independent arm, same contract, distinct output object with equal bytes.",
    "W2.other": "Claim for arm A offered the other independently created approved launcher/interpreter pair.",
    "W4.denied": "Ordinary incompatible access request (replacement attempt) against an owned protected output; no filesystem mutation.",
    "B1.original": "Continuously protected original A with all process and sink bindings, submitted for A.",
    "B2.other": "Protected original B (trusted identity identifies it as B) submitted for A; equal bytes.",
    "B3.copy": "Detached equal-byte copy with A's authentic reference receipt, submitted for A.",
    "B4.invalid": "Detached equal-byte copy with a demonstrably invalid claimed seal, submitted for A.",
    "B4.unavailable": "Detached equal-byte copy whose claimed seal cannot be verified, submitted for A.",
    "B5.reopen": "Study's own deliberately closed protecting handle, then read-only reopening of the same pathname. Last row.",
}


def _rng(row: str) -> random.Random:
    return random.Random(int.from_bytes(hashlib.sha256(("wp0044-seed:" + row).encode()).digest()[:8], "big"))


def _instance(rng: random.Random) -> dict:
    # Creation-scoped process key: numeric PID plus creation FILETIME (100 ns ticks).
    return {"pid": rng.randrange(1000, 60000, 4), "created": 134088000000000000 + rng.randrange(10**12)}


def _baseline(row: str):
    rng = _rng(row)
    launcher = _instance(rng)
    interp = {"pid": rng.randrange(1000, 60000, 4), "created": launcher["created"] + rng.randrange(10**5, 10**7)}
    vol = "0x%08X" % rng.getrandbits(32)
    idx = "0x%016X" % rng.getrandbits(52)
    arm = "arm-%016x" % rng.getrandbits(64)
    receipt = "sha256:%064x" % rng.getrandbits(256)
    member = [{"name": "out.bin", "length": len(PAYLOAD), "sha256": hashlib.sha256(PAYLOAD).hexdigest()}]
    expected = {
        "L.image": APPROVED_L,
        "I.image": APPROVED_I,
        "E.launcher": launcher,
        "E.parent": launcher,
        "E.order": ["launcher.create", "interpreter.create", "launcher.exit"],
        "E.instance": interp,
        "E.job": {"breakaway_allowed": False, "launcher_contained": True, "interpreter_contained": True},
        "A.script": SCRIPT,
        "A.args": list(ARGS),
        "C.pyvenv": PYVENV,
        "C.include_system": False,
        "C.pth": [],
        "C.sitecustomize": None,
        "C.PYTHONHOME": None,
        "C.PYTHONPATH": None,
        "C.PYTHONSAFEPATH": None,
        "C.CUBLAS_WORKSPACE_CONFIG": None,
        "C.CUDA_VISIBLE_DEVICES": "",
        "C.prefix": "X:\\wp0044\\prüfung\\venv",
        "C.modules": copy.deepcopy(MODULES),
        "B.writer": [interp],
        "B.seal": {"receipt": receipt, "authenticated": True},
        "B.protection": {"continuous_from": "creation", "continuous_through": "acquisition"},
        "B.direct": {"volume_serial": vol, "file_index": idx},
        "B.origin": arm,
        "B.members": member,
        "content.bytes": PAYLOAD.hex(),
    }
    observed = copy.deepcopy(expected)
    offset = rng.randrange(1, 10**6)
    sources = {k: {"method": METHOD[k], "seq": offset + 10 * (i + 1)} for i, k in enumerate(OBSERVATION_ORDER)}
    return rng, expected, observed, sources


def _drop(observed: dict, sources: dict, key: str) -> None:
    del observed[key]
    del sources[key]


def _writer_sort(ws: list) -> list:
    return sorted(ws, key=lambda w: (w["pid"], w["created"]))


def construct(row: str) -> dict:
    """Apply the row's construction to a fresh baseline. Returns the blinded record."""
    rng, exp, obs, src = _baseline(row)
    if row == "W2.helper":
        helper = _instance(rng)
        obs["E.parent"] = helper  # helper sits in the direct edge, inside the same job
    elif row == "W3.missing":
        _drop(obs, src, "E.parent")
    elif row == "W3.late_missing":
        _drop(obs, src, "E.parent")
        obs["E.order"] = ["launcher.create", "launcher.exit", "interpreter.create"]
    elif row == "W3.reuse":
        reused = dict(exp["E.instance"])
        reused["created"] = reused["created"] + 7_300_000_000  # same numeric PID, later creation key
        obs["E.instance"] = reused
    elif row == "W4.bad_I":
        obs["I.image"] = _d("different-interpreter-image")
    elif row == "W4.no_I":
        _drop(obs, src, "I.image")
    elif row == "W4.bad_L":
        obs["L.image"] = _d("different-launcher-image")
    elif row == "W5.args":
        a = list(exp["A.args"])
        a[0], a[1] = a[1], a[0]  # same multiset, different order
        obs["A.args"] = a
    elif row == "W5.script":
        obs["A.script"] = _d("modified-inert-writer-script")
    elif row == "W5.config":
        # One physical edit of pyvenv.cfg: the effective value and the file digest both change.
        obs["C.include_system"] = True
        obs["C.pyvenv"] = _d("pyvenv.cfg include-system-site-packages=true")
    elif row == "W5.empty":
        obs["C.PYTHONPATH"] = ""
    elif row == "W5.unobserved":
        _drop(obs, src, "C.PYTHONSAFEPATH")
    elif row == "W6.escape":
        obs["E.job"] = {"breakaway_allowed": False, "launcher_contained": True, "interpreter_contained": False}
    elif row == "W6.writer":
        sibling = _instance(rng)
        obs["B.writer"] = _writer_sort([exp["E.instance"], sibling])
    elif row == "B5.member_missing":
        extra = {"name": "out.bin.tmp", "length": 4, "sha256": hashlib.sha256(b"F08\n").hexdigest()}
        obs["B.members"] = sorted(exp["B.members"] + [extra], key=lambda m: m["name"])
        _drop(obs, src, "B.direct")
    elif row == "B5.writer_missing":
        other = _instance(rng)
        obs["B.writer"] = _writer_sort([exp["E.instance"], other])
        _drop(obs, src, "B.direct")
    else:
        raise KeyError(row)
    # Blind key order inside each map (order is not meaningful).
    def shuffled(m: dict) -> dict:
        ks = list(m)
        rng.shuffle(ks)
        return {k: m[k] for k in ks}
    return {"schema": RECORD_SCHEMA, "expected": shuffled(exp), "observed": shuffled(obs), "sources": shuffled(src)}


# ---------------------------------------------------------- math controls
def math_input(row: str) -> dict:
    if row == "math.shift":
        return {"schema": "wp0044.margin.v1", "tie_rule": "first_index", "queries": [
            {"scores": [[6, "28.0"], [1449, "17.125"]], "delta": [[6, "10"], [1449, "10"]]},
            {"scores": [[6, "28.0"], [1449, "17.125"]], "delta": [[6, "-5"], [1449, "5"]]},
        ]}
    if row == "math.tie":
        return {"schema": "wp0044.margin.v1", "tie_rule": "first_index", "queries": [
            {"scores": [[6, "28.0"], [1449, "17.125"]], "delta": [[6, "0"], [1449, "10.875"]]},
            {"scores": [[223, "11.125"], [128822, "25.0"]], "delta": [[223, "13.875"], [128822, "0"]]},
        ]}
    if row == "math.signed_zero":
        return {"schema": "wp0044.fp32.v1", "tie_rule": "first_index", "queries": [
            {"words_le": ["00000000", "00000080"]},
            {"words_le": ["00000080", "00000000"]},
        ]}
    if row == "math.linked":
        # Z(q) = base + q * slope over support {0,1}; one scalar cache q.
        return {"schema": "wp0044.linked.v1", "tie_rule": "first_index", "support": [0, 1],
                "base": ["1", "0"], "slope": ["-1", "1"], "q0": "0",
                "stock_write": "0", "private_write": "2", "steps": 2}
    raise KeyError(row)


# ------------------------------------------------------------------ output
def dump(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def build() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    rows = []
    for row, iface in SCHEDULE:
        entry = {"id": row, "interface": iface, "repetitions": 1}
        if iface in ("constructed", "mathematical"):
            data = dump(construct(row) if iface == "constructed" else math_input(row))
            sub = "constructed" if iface == "constructed" else "math"
            rel = f"inputs/{sub}/{sha(data)[:16]}.json"
            files[rel] = data
            entry["input"] = {"path": rel, "sha256": sha(data), "bytes": len(data)}
        elif iface == "archive":
            entry["input"] = {"path": ARCHIVE_PATH, "sha256": ARCHIVE_SHA256, "commit": RESERVATION_PARENT}
        else:
            entry["input"] = None
            entry["live_construction"] = LIVE_CONSTRUCTION[row]
            entry["payload_hex"] = PAYLOAD.hex()
        rows.append(entry)
    gen = (HERE / "build_fixtures.py").read_bytes()
    manifest = {
        "version": VERSION,
        "owner": "eld-fixture-claude",
        "packet": "WP-0044",
        "base_commit": BASE_COMMIT,
        "reservation_parent": RESERVATION_PARENT,
        "record_schema": RECORD_SCHEMA,
        "canonical_keys": KEYS,
        "denominator_per_route": len(rows),
        "counts": {i: sum(1 for _, x in SCHEDULE if x == i) for i in ("live", "constructed", "archive", "mathematical")},
        "generator": {"path": "build_fixtures.py", "sha256": sha(gen), "bytes": len(gen)},
        "rows": rows,
        "files": {p: {"sha256": sha(b), "bytes": len(b)} for p, b in sorted(files.items())},
    }
    files["manifest.json"] = dump(manifest)
    return files


def main(argv: list[str]) -> int:
    files = build()
    assert len(SCHEDULE) == 33
    sched = json.loads((REPO / "docs/coordination/WP-0044/schedule.json").read_text(encoding="utf-8"))
    assert [(r["id"], r["interface"]) for r in sched["rows"]] == SCHEDULE, "schedule drift"
    assert sha((REPO / ARCHIVE_PATH).read_bytes()) == ARCHIVE_SHA256, "archive drift"
    if "--check" in argv:
        bad = [p for p, b in files.items() if not (HERE / p).is_file() or (HERE / p).read_bytes() != b]
        on_disk = {p.relative_to(HERE).as_posix() for p in (HERE / "inputs").rglob("*") if p.is_file()}
        extra = on_disk - set(files)
        print(json.dumps({"checked": len(files), "mismatched": bad, "unexpected": sorted(extra)}))
        return 1 if bad or extra else 0
    for p, b in files.items():
        (HERE / p).parent.mkdir(parents=True, exist_ok=True)
        (HERE / p).write_bytes(b)
    print(json.dumps({"written": len(files), "manifest_sha256": sha(files["manifest.json"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
