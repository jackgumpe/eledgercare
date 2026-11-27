"""Typed equality over the WP-0044 interchange; there is no case identifier."""
import json

PHASES = ("launch", "image", "edge", "command", "configuration", "writer",
          "seal", "acquisition", "score")
KEYS = {
    "L.image": "image", "I.image": "image", "E.launcher": "edge",
    "E.parent": "edge", "E.order": "edge", "E.instance": "edge", "E.job": "edge",
    "A.script": "command", "A.args": "command", "C.pyvenv": "configuration",
    "C.include_system": "configuration", "C.pth": "configuration",
    "C.sitecustomize": "configuration", "C.PYTHONHOME": "configuration",
    "C.PYTHONPATH": "configuration", "C.PYTHONSAFEPATH": "configuration",
    "C.CUBLAS_WORKSPACE_CONFIG": "configuration", "C.CUDA_VISIBLE_DEVICES": "configuration",
    "C.prefix": "configuration", "C.modules": "configuration", "B.writer": "writer",
    "B.seal": "seal", "B.protection": "acquisition", "B.direct": "acquisition",
    "B.origin": "acquisition", "B.members": "acquisition", "content.bytes": "score",
}
RANK = {"M": 0, "U": 1, "P": 2}


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def minimum(values):
    return min(values, key=RANK.__getitem__)


def reason(key, status):
    if status == "U":
        return "unresolved"
    if status == "P":
        return "agreement"
    if key == "B.origin":
        return "wrong_origin"
    if key in ("B.members", "B.seal"):
        return "integrity"
    if key == "B.writer":
        return "unauthorized_writer"
    if key == "content.bytes":
        return "content_mismatch"
    return "mismatch"


def frontier(findings):
    # Native monotonic stamps share one observer; constructed sources can supply
    # different clocks. Retain every undominated diagnostic for incomparable cuts.
    def before(left, right):
        if "time_ns" in left and "time_ns" in right:
            return left["clock"] == right["clock"] and left["time_ns"] < right["time_ns"]
        if "time_ns" not in left and "time_ns" not in right:
            return PHASES.index(left["phase"]) < PHASES.index(right["phase"])
        return False

    return [item["key"] for item in findings if not any(before(other, item) for other in findings)]


def score(record):
    expected, observed, sources = (record[name] for name in ("expected", "observed", "sources"))
    if set(expected) != set(KEYS) or set(observed) - set(KEYS):
        raise ValueError("incorrect canonical key domain")
    atoms = []
    for key, default_phase in KEYS.items():
        source = sources.get(key, "measurement absent at prescribed cut")
        descriptor = source if isinstance(source, dict) else {"source": source}
        phase = descriptor.get("phase", default_phase)
        if phase not in PHASES:
            raise ValueError("unrecognized evidence phase")
        status = "U" if key not in observed else (
            "P" if encode(expected[key]) == encode(observed[key]) else "M")
        atom = {"key": key, "status": status, "reason": reason(key, status),
                "phase": phase, "source": descriptor.get("source", descriptor)}
        if "time_ns" in descriptor:
            atom.update(time_ns=descriptor["time_ns"], clock=descriptor.get("clock", "observer"))
        atoms.append(atom)
    coordinates = {k: minimum(x["status"] for x in atoms if x["key"].startswith(k + "."))
                   for k in "LIEACB"}
    custody = minimum(coordinates[k] for k in "LIEAB")
    findings = [a for a in atoms if a["status"] != "P"]
    mismatches = [a for a in findings if a["status"] == "M"]
    missing = [a for a in findings if a["status"] == "U"]
    return {"coordinates": coordinates, "custody": custody, "joint": minimum([custody, coordinates["C"]]),
            "content": atoms[-1]["status"], "conflicts": sorted(a["key"] for a in mismatches),
            "missing": sorted(a["key"] for a in missing), "earliest": frontier(findings),
            "earliest_conflict": frontier(mismatches), "earliest_missing": frontier(missing),
            "atoms": atoms}
