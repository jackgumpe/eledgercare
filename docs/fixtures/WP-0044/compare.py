"""WP-0044 comparator (eld-fixture-claude). Joins frozen expectations with one route's
observations by row ID and reports per-field agreement and q. It never computes a verdict.

    python -I compare.py --expected <expected.json> --observed <observed.json> --manifest manifest.json --out <cmp.json>

Observed: {"rows": [ {"id": ..., <same fields as an expected row>} ]} in the wp0044.expected.v1
row shape (after any separately versioned schema-only crosswalk). A scheduled row that is
absent, duplicated or lacks a compared field fails and stays in the denominator.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

IGNORED = {"id", "interface", "input_sha256"}
UNORDERED_LISTS = {"conflicts", "missing"}  # canonical order: by key


def same(a, b) -> bool:
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def canon(field, value):
    if field in UNORDERED_LISTS and isinstance(value, list) and all(isinstance(x, dict) and "key" in x for x in value):
        return sorted(value, key=lambda x: x["key"])
    return value


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected", required=True)
    ap.add_argument("--observed", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    exp = json.loads(Path(a.expected).read_bytes().decode("utf-8"))
    obs = json.loads(Path(a.observed).read_bytes().decode("utf-8"))
    man = json.loads(Path(a.manifest).read_bytes().decode("utf-8"))
    sched = [(r["id"], r["interface"]) for r in man["rows"]]
    erows = {r["id"]: r for r in exp["rows"]}
    assert [(r["id"], r["interface"]) for r in exp["rows"]] == sched, "expected/manifest schedule mismatch"
    seen: dict[str, list] = {}
    for r in obs.get("rows", []):
        seen.setdefault(r.get("id"), []).append(r)
    rows, by_iface = [], {}
    for rid, iface in sched:
        e = erows[rid]
        got = seen.get(rid, [])
        fields = {}
        if len(got) != 1:
            status = "absent" if not got else "duplicated"
            ok = False
        else:
            o = got[0]
            for f in e:
                if f in IGNORED:
                    continue
                fields[f] = f in o and same(canon(f, e[f]), canon(f, o[f]))
            ok = all(fields.values())
            status = "match" if ok else "mismatch"
        rows.append({"id": rid, "interface": iface, "status": status, "fields": fields})
        t = by_iface.setdefault(iface, [0, 0])
        t[0] += ok
        t[1] += 1
    unscheduled = sorted(str(k) for k in seen if k not in erows)
    n = len(sched)
    matched = sum(1 for r in rows if r["status"] == "match")
    summary = {"q_numerator": matched, "q_denominator": n, "q_is_one": matched == n,
               "by_interface": {k: f"{v[0]}/{v[1]}" for k, v in by_iface.items()},
               "unscheduled_observed_ids": unscheduled, "rows": rows}
    Path(a.out).write_bytes((json.dumps(summary, indent=1) + "\n").encode("utf-8"))
    print(json.dumps({k: summary[k] for k in ("q_numerator", "q_denominator", "by_interface", "unscheduled_observed_ids")}))
    return 0 if matched == n and not unscheduled else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
