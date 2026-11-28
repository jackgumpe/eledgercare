"""Compare peer controls.py batch output with the reviewer's required and predicted results.
Usage: python -I compare_peer.py EXPECTED.json PEER_RESULTS.json
Reports two separate counts: agreement with 'required' (reviewer's position) and
agreement with 'predicted_peer' (inspection prediction). Neither is a blind count.
"""
import json
import sys


def get(d, path):
    for part in path.split("."):
        d = d.get(part) if isinstance(d, dict) else None
    return d


def check(spec, relation, actual):
    bad = []
    if relation == "full" or "conflict_keys" in spec:
        for f in [k for k in spec if not k.startswith("must_include")]:
            if get(actual, f) != spec[f]:
                bad.append(f)
    else:
        if actual.get("verdict") != spec["verdict"]:
            bad.append("verdict")
    for f, src in (("must_include_conflicts", "conflict_keys"), ("must_include_missing", "missing_keys")):
        miss = [k for k in spec.get(f, []) if k not in actual.get(src, [])]
        if miss:
            bad.append(f + ":" + ",".join(miss))
    return bad


def main(exp_path, res_path):
    exp = json.load(open(exp_path, encoding="utf-8"))["cases"]
    res = {r["case_id"]: r["result"] for r in json.load(open(res_path, encoding="utf-8"))["results"]}
    req_ok = pred_ok = 0
    for cid, e in exp.items():
        a = res.get(cid)
        if a is None:
            print(cid, "NOT RETURNED"); continue
        r = check(e["required"], e["relation"], a)
        p = check(e["predicted_peer"], "full", a)
        req_ok += not r
        pred_ok += not p
        print(cid, "required:", "agree" if not r else "DIFFER " + ";".join(r), "| predicted:", "agree" if not p else "DIFFER " + ";".join(p),
              "| peer verdict", a.get("verdict"), a.get("conflict_keys"), a.get("missing_keys"))
    print("required agreement %d/%d; prediction agreement %d/%d; returned %d" % (req_ok, len(exp), pred_ok, len(exp), len(res)))


if __name__ == "__main__":
    main(*sys.argv[1:3])
