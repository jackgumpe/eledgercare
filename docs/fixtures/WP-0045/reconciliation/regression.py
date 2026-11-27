"""WP-0045 A2 r1 distinguishing regression (eld-fixture-claude, post-opening).

    python -I -B regression.py [--out <json>]

Runs the r1 A2 evaluator and the unchanged opened v1 evaluator on each case in
regression.json and checks the hand-written expectations frozen there:
r1 output fields, v1 conflicts, and whether the two readings differ.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("oracle_r1", HERE / "oracle_r1.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

FIELDS = ("status", "first", "conflicts", "allowed", "winner")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "results" / "regression-results.json"))
    a = ap.parse_args(argv)
    spec_ = json.loads((HERE / "regression.json").read_text(encoding="utf-8"))
    res, fails = [], 0
    for c in spec_["cases"]:
        r1 = R.a2_r1(c["input"])
        v1 = R.V1_A2(c["input"])
        ok_r1 = all(R.O.canon(r1[f]) == R.O.canon(c["expected_r1"][f]) for f in FIELDS)
        ok_echo = r1["raw"] == c["input"]["raw"] and r1["repeat"] == c["input"]["repeat"] and r1["page"] == c["input"]["page"]
        ok_v1 = v1["conflicts"] == c["expected_v1_conflicts"]
        ok_diff = (R.O.canon(r1) != R.O.canon(v1)) == c["v1_differs"]
        ok = ok_r1 and ok_echo and ok_v1 and ok_diff
        fails += not ok
        res.append({"name": c["name"], "pass": ok, "r1_conflicts": r1["conflicts"], "v1_conflicts": v1["conflicts"],
                    "checks": {"r1_fields": ok_r1, "echo": ok_echo, "v1_conflicts": ok_v1, "differs_as_predicted": ok_diff}})
    out = {"version": spec_["version"], "cases": len(res), "failed": fails, "results": res}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_bytes((json.dumps(out, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print("%d cases, %d failed" % (len(res), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
