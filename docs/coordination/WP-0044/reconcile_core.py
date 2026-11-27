"""Compare returned provenance verdicts and atomic key sets independently of narrative labels."""
import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path

AUTHOR = "f3c59b478d4b6ce19dc7dd32ae68ad663a8ee29c:docs/research/WP-0044/blind-results.json"
REVIEWER = "dae70e25d8d03896d7757fd55044c030bf221880:docs/reviews/WP-0044/blind-results.json"


def frozen(spec):
    return json.loads(subprocess.check_output(["git", "show", spec]))


def projection(row, conflicts):
    return {"coordinates": row["coordinates"], "joint": row["joint"], "custody": row["custody"],
            "content": row["content"], "conflicts": sorted(conflicts), "missing": sorted(row["missing"])}


def differences(left, right):
    return [key for key in left if left[key] != right[key]]


def reconcile(oracle):
    a = frozen(AUTHOR)["rows"]
    b = frozen(REVIEWER)
    cases = []
    totals = Counter()
    for row in json.loads(oracle.read_bytes())["rows"]:
        if row["interface"] not in {"live", "constructed"}:
            continue
        key = row["id"]
        author = a[key]["verdict"]
        ar = projection(author, author["conflicts"])
        rev = projection(b[key], b[key]["conflict"])
        ref = dict(row, missing=[d["key"] for d in row["missing"]])
        ideal = projection(ref, [d["key"] for d in row["conflicts"]])
        comparisons = {name: differences(left, right)
                       for name, left, right in [("author_oracle", ar, ideal), ("reviewer_oracle", rev, ideal),
                                                 ("author_reviewer", ar, rev)]}
        totals[row["interface"]] += 1
        for name, delta in comparisons.items():
            totals[row["interface"] + "_" + name] += int(not delta)
        cases.append({"id": key, "interface": row["interface"], "author": ar, "reviewer": rev,
                      "oracle": ideal, "unequal_fields": comparisons})
    return {"scope": "Six coordinates, joint, custody, content, all conflicting and missing keys. This diagnostic does not count as complete-row q.", "counts": dict(totals), "rows": cases}


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("expected", type=Path)
    print(json.dumps(reconcile(cli.parse_args().expected), indent=2))
