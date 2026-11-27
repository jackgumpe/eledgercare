"""Compare complete WP-0045 projected returns with independently committed expectations."""
import argparse
import json
from pathlib import Path


def read(path):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError(f"Duplicate JSON key {key!r}")
            obj[key] = value
        return obj
    return json.loads(path.read_bytes(), object_pairs_hook=unique,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def unequal(expected, actual, path="$"):
    if type(expected) is not type(actual):
        return [path]
    if isinstance(expected, dict):
        differences = []
        for key in sorted(expected.keys() | actual.keys()):
            name = f"{path}.{key}"
            if key not in expected or key not in actual:
                differences.append(name)
            else:
                differences.extend(unequal(expected[key], actual[key], name))
        return differences
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [path]
        return [d for i,(x,y) in enumerate(zip(expected,actual,strict=True))
                for d in unequal(x,y,f"{path}[{i}]")]
    return [] if expected == actual else [path]


def compare(expected, actual, input_hashes, seen_hashes, schedule, groups):
    assigned = [key for group in groups for key in schedule["rows"][group]]
    if len(assigned) != len(set(assigned)):
        raise ValueError("Duplicate scheduled row")
    records = {}
    for key in assigned:
        issues = []
        if key not in input_hashes or key not in expected:
            raise ValueError(f"Missing frozen input or oracle for {key}")
        if seen_hashes.get(key) != input_hashes[key]:
            issues.append("input_sha256")
        if key not in actual:
            issues.append("missing_row")
        else:
            issues.extend(unequal(expected[key], actual[key]))
        records[key] = {"matches": not issues, "differences": issues}
    by_group = {group: [sum(records[key]["matches"] for key in schedule["rows"][group]),
                        len(schedule["rows"][group])] for group in groups}
    extras = sorted((actual.keys() | seen_hashes.keys()) - set(assigned))
    return {"compared_groups": groups, "matches_and_scheduled": by_group, "unscheduled_keys": extras,
            "complete": not extras and all(row["matches"] for row in records.values()), "rows": records}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    for arg in ["oracle", "actual", "input_hashes", "seen_hashes", "schedule", "output"]:
        ap.add_argument(arg, type=Path)
    ap.add_argument("groups", nargs="+")
    args = ap.parse_args()
    result = compare(read(args.oracle), read(args.actual), read(args.input_hashes),
                     read(args.seen_hashes), read(args.schedule), args.groups)
    with args.output.open("x", encoding="utf8", newline="\n") as out:
        json.dump(result, out, indent=2)
        out.write("\n")
    print(json.dumps(result["matches_and_scheduled"]))
    raise SystemExit(0 if result["complete"] else 1)
