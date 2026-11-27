"""WP-0045 full-row comparator (eld-fixture-claude).  Contains no expectations.

    python -I compare.py --manifest manifest.json \
        --expected <opened dir containing expected-manifest.json> \
        --observed <dir with one returned <ID>.json per scheduled row> \
        --digests <json mapping returned ID -> verified input sha256 (string or {"sha256":...})> \
        --out <comparison.json>

Exact outer join on scheduled ID.  A row matches only if the returned file
exists, parses as one JSON object, the returned input digest equals the
manifest digest, and the object equals the expected row under canonical typed
JSON equality (bool distinct from int, list order significant, object member
order not).  Missing, extra, duplicated or unparsable rows stay in the
denominator as failures.  No verdict is computed or translated.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

GROUPS = {"Q1": ("Q1.live", "Q1.constructed", "Q1.archive"), "A1": ("A1",), "A2": ("A2",), "C1": ("C1",)}


def canon(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def no_dupes(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError("duplicate member %r" % k)
        d[k] = v
    return d


def load(path):
    return json.loads(Path(path).read_bytes().decode("utf-8"), object_pairs_hook=no_dupes)


def main(argv=None):
    ap = argparse.ArgumentParser()
    for a in ("--manifest", "--expected", "--observed", "--digests", "--out"):
        ap.add_argument(a, required=True)
    a = ap.parse_args(argv)
    man = load(a.manifest)
    exp_dir = Path(a.expected)
    em = load(exp_dir / "expected-manifest.json")
    assert em["fixture_manifest_sha256"] == hashlib.sha256(Path(a.manifest).read_bytes()).hexdigest()
    digests = load(a.digests)
    obs_dir = Path(a.observed)
    sched = [r["id"] for r in man["rows"]]
    rows, extra = [], sorted(set(digests) - set(sched))
    extra += sorted(p.stem for p in obs_dir.glob("*.json") if p.stem not in sched)
    for r in man["rows"]:
        rid = r["id"]
        e = em["rows"][rid]
        ebytes = (exp_dir / e["path"]).read_bytes()
        assert hashlib.sha256(ebytes).hexdigest() == e["sha256"], rid
        want = json.loads(ebytes)
        res = {"id": rid, "family": r["family"], "match": False}
        d = digests.get(rid)
        d = d.get("sha256") if isinstance(d, dict) else d
        f = obs_dir / (rid + ".json")
        if d is None:
            res["failure"] = "no returned input digest"
        elif d != r["input"]["sha256"]:
            res["failure"] = "input digest differs"
        elif not f.is_file():
            res["failure"] = "missing returned row"
        else:
            try:
                got = load(f)
            except Exception as exc:  # noqa: BLE001 - recorded, stays in denominator
                res["failure"] = "unparsable: %s" % exc
                got = None
            if got is not None:
                res["match"] = canon(got) == canon(want)
                if not res["match"]:
                    if isinstance(got, dict) and isinstance(want, dict):
                        res["differing_fields"] = sorted(k for k in set(got) | set(want)
                                                         if k not in got or k not in want or canon(got[k]) != canon(want[k]))
                    else:
                        res["differing_fields"] = ["<top-level type>"]
        rows.append(res)
    q = {}
    for g, fams in GROUPS.items():
        sel = [x for x in rows if x["family"] in fams]
        q[g] = {"matched": sum(x["match"] for x in sel), "denominator": len(sel)}
    q["total"] = {"matched": sum(x["match"] for x in rows), "denominator": len(rows)}
    out = {"version": "wp0045.comparison.v1", "fixture_manifest_sha256": em["fixture_manifest_sha256"],
           "q": q, "extra_returned_ids": extra, "rows": rows}
    Path(a.out).write_bytes((json.dumps(out, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print(json.dumps(q))
    return 0 if q["total"]["matched"] == len(rows) and not extra else 1


if __name__ == "__main__":
    sys.exit(main())
