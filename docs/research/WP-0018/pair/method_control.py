"""Exercise the supplied invented layout in two separate pinned-scorer processes."""
import argparse
from pathlib import Path
import subprocess
import sys
import json

from baseline import PINS, canon, check, digest, new_output, read, write


def run(inputs, out):
    scorer = inputs / "control/score.py"
    source = inputs / "control/constructed-scorer-control.json"
    check(digest(source.read_bytes()) == PINS[source.name], "constructed control digest")
    fixture = read(source)
    check(digest(scorer.read_bytes()) == fixture["scorer_sha256"] == PINS["score.py"], "scorer digest")
    child = ("import json, runpy, sys; scorer=runpy.run_path(sys.argv[1]); "
             "print(json.dumps(scorer['layout'](*json.load(sys.stdin)), allow_nan=False))")
    results = {}
    for arm in ("before", "after"):
        page = dict(fixture["prediction_page"])
        if arm == "after":
            page["tables"] = []
        args = [fixture["reference_page"], page, fixture["source_sha256_placeholder"]]
        output = subprocess.check_output([sys.executable, "-I", "-B", "-c", child, str(scorer)],
                                         input=canon(args))
        layout = json.loads(output)
        small = dict(cells=[[c[k] for k in ("at", "expected", "observed", "correct")] for c in layout["cells"]],
                     lines=[[l[k] for k in ("at", "observed", "correct")] for l in layout["lines"]],
                     extra_cells=layout["extra_cells"], faults=layout["faults"])
        check(small == fixture[arm], arm)
        results[arm] = layout
    before, after = results["before"], results["after"]
    check(canon(before["lines"]) == canon(after["lines"]), "control line details")
    prose = lambda records: [c for c in records["critical"] if "/line/" in c["at"]]
    check(canon(prose(before)) == canon(prose(after)), "control critical line details")
    changes = [(b["correct"], a["correct"]) for b, a in zip(before["cells"], after["cells"], strict=True)]
    gains, losses = changes.count((False, True)), changes.count((True, False))
    check((gains, losses) == (1, 1), "control must expose offsetting changes")
    write(out / "constructed.json", dict(constructed=True, fixture_sha256=PINS[source.name],
                                        scorer_sha256=PINS["score.py"], gains=gains, losses=losses,
                                        net=gains-losses, arms=results))
    print("Constructed control passed: one gain, one loss, zero net, prose unchanged")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    run(a.inputs, new_output(a.output, a.inputs))
