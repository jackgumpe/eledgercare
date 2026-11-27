"""Pure Q1 relation projection; case identity is outside the predicate."""
import json
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[2] / "coordination/WP-0045"
SCHEDULE = json.loads((CONTRACT / "schedule.json").read_bytes())
ATOMS = SCHEDULE["atoms"]
ORDER = "MUP"

def equal(a, b):
    return json.dumps(a, allow_nan=False, sort_keys=True) == json.dumps(b, allow_nan=False, sort_keys=True)

def worst(values):
    return min(values, key=ORDER.index)

def project(data):
    expected, observed, evidence = (data[k] for k in ("expected", "observed", "evidence"))
    if set(expected) != set(ATOMS) or set(evidence) != set(ATOMS) or not set(observed) <= set(ATOMS):
        raise ValueError("incomplete expected/source inventory or unknown atom")
    values, sources, reasons = {}, {}, {}
    for k, spec in ATOMS.items():
        witness = evidence[k]
        sources[k] = witness["source"]
        if k not in observed or sources[k] != spec["source"]:
            verdict = "U"
        else:
            verdict = "P" if equal(expected[k], observed[k]) else "M"
        values[k] = verdict
        if verdict == "U":
            reasons[k] = "unresolved"
        elif verdict == "M":
            if k in ("E.caller", "E.child", "B.origin"):
                reasons[k] = "wrong_origin"
            elif k == "B.writer":
                reasons[k] = "unauthorized_writer"
            else:
                reasons[k] = "integrity"
    findings = sorted(reasons)
    first = None
    if findings:
        times = [evidence[k]["at"] for k in findings]
        at = None if None in times else min(times)
        first = {"at": at, "keys": [k for k in findings if at is None or evidence[k]["at"] == at]}
    coordinates = {g: worst(v for k, v in values.items() if k.startswith(g + ".")) for g in "LIEACB"}
    custody = worst(coordinates[g] for g in "LIEAB")
    return {"status": worst([custody, coordinates["C"]]), "values": values, "coordinates": coordinates,
            "custody": custody, "content": values["content.bytes"], "source": sources,
            "first": first, "reason": reasons, "missing": [k for k in findings if values[k] == "U"],
            "conflicts": [k for k in findings if values[k] == "M"]}
