"""Compare evaluator results with the frozen expectations, case by case and field by field.
Usage: python -I compare.py EXPECTED.json RESULTS.json
"""
import json
import sys


def main(exp_path, res_path):
    exp = json.load(open(exp_path, encoding="utf-8"))["cases"]
    res = json.load(open(res_path, encoding="utf-8"))["cases"]
    agree, rows = 0, []
    for cid in exp:
        got = res.get(cid)
        diff = sorted(k for k in set(exp[cid]) | set(got or {}) if (got or {}).get(k) != exp[cid].get(k))
        if not diff:
            agree += 1
        rows.append((cid, "agree" if not diff else "DIFFER " + ",".join(diff)))
    extra = sorted(set(res) - set(exp))
    for cid, status in rows:
        print(cid, status)
    print("full-record agreement %d/%d; unexpected result ids %d" % (agree, len(exp), len(extra)))
    return 0 if agree == len(exp) and not extra else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
