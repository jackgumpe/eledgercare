"""Cross-check a frozen decision by directly intersecting coordinate equalities."""

from itertools import combinations


def line_intersection(line, required, y):
    """Return impossible, one exact allowed point, or the entire affine family."""
    if line is None:
        return None
    parameter = None
    for j in required:
        h, s = line["h"][j], line["s"][j]
        if s == 0:
            if h != y[j]:
                return None
        else:
            c, rem = divmod(y[j] - h, s)
            if rem or c in line["excluded"] or (parameter is not None and c != parameter):
                return None
            parameter = c
    if parameter is None:
        return "all"
    return tuple(h + parameter * s for h, s in zip(line["h"], line["s"], strict=True))


def subset_decode(record, queried, budget):
    line, y = record["line"], record["y"]
    points = {tuple(p) for p in record["points"]}
    surviving = set()
    all_parameters = False
    # Every ledger that agrees on some subset of |Q|-e coordinates has
    # at most e errors. Union the exact intersections, including finite points.
    for required in combinations(queried, max(0, len(queried) - budget)):
        surviving.update(p for p in points if all(p[j] == y[j] for j in required))
        match = line_intersection(line, required, y)
        if match == "all":
            all_parameters = True
        elif match is not None:
            surviving.add(match)
    if all_parameters:
        surviving = {p for p in surviving if line_intersection(line, range(len(y)), p) is None}
    return {
        "count": "infinite" if all_parameters else len(surviving),
        "line": line if all_parameters else None,
        "points": [list(p) for p in sorted(surviving)],
    }


def equal(expected, actual, reason):
    if expected != actual:
        raise AssertionError((reason, expected, actual))


def audit_return(record, actual):
    arm = record["arm"]
    r = dict(status="UNSUPPORTED", q=None, d=None, ties=[], count=None, line=None, points=[], diag=None)
    if record["status"] != "ADMITTED":
        if record["status"] == "OUT_OF_DOMAIN_TRUSTED_OPENING":
            r["status"] = record["status"]
        return equal(r, actual, "upstream")
    points = {tuple(p) for p in record["points"]}
    if record["line"] is None and (not points or (len(points) == 1 and arm != "H")):
        if points:
            r.update(status="FIRST_PASS_SINGLETON", q=0, count=1, points=[list(points.pop())])
        else:
            r["status"] = "ADMITTED_EMPTY"
        return equal(r, actual, "first pass")
    size = len(record["names"])
    indices = tuple(range(size))
    full = (1 << size) - 1
    distances = record["dist"]
    if arm == "B":
        r.update(status="FIRST_PASS_AMBIGUOUS", q=0, d=distances[0])
        return equal(r, actual, "control B")
    if arm in ("R", "F", "T") and distances[-1] < 2:
        r["status"] = "INSUFFICIENT_SEPARATION"
        return equal(r, actual, "separation")
    if arm in ("E", "R"):
        threshold = 1 if arm == "E" else min(3, distances[-1])
        for k in range(1, size + 1):
            options = []
            for indices_in_set in combinations(indices, k):
                mask = sum(1 << j for j in indices_in_set)
                if distances[mask] >= threshold:
                    area = sum(record["areas"][j] for j in indices_in_set)
                    options.append((area, mask))
            if options:
                r["q"] = min(options)[1]
                r["ties"] = sorted(mask for _, mask in options)
                break
    else:
        r["q"] = record["q"] if arm == "H" else full
    mask = r["q"]
    r["d"] = distances[mask]
    if record["read_status"] != "OK":
        r["status"] = record["read_status"]
        return equal(r, actual, "view failure")

    radius = record["radius"] if arm == "H" else int(arm != "E")
    cells = [j for j in indices if mask >> j & 1]
    r.update(subset_decode(record, cells, radius))
    r["status"] = {0: "INCONSISTENT", 1: "RESOLVED"}.get(r["count"], "AMBIGUOUS")

    if arm in ("F", "T"):
        # Build two distinct allowed representatives, sufficient to identify
        # every nonconstant affine coordinate independently of its slope.
        line = record["line"]
        if line is not None:
            offset = max([0, *line["excluded"]]) + 1
            for c in (offset, offset + 1):
                points.add(tuple(h + c * s for h, s in zip(line["h"], line["s"], strict=True)))
        values = [{p[j] for p in points} for j in indices]
        active = [j for j in indices if len(values[j]) > 1]
        constant = set(indices) - set(active)
        minimum = next(m for m in range(len(active) + 1) if subset_decode(record, active, m)["count"] != 0)
        mc = sum(record["y"][j] not in values[j] for j in constant)
        r["diag"] = dict(constant_mask=sum(1 << j for j in constant), mc=mc,
                         min_active=minimum, active_count=subset_decode(record, active, 1)["count"],
                         full_count=r["count"], exact_full=mc + minimum == 0)
    return equal(r, actual, "complete")

def audit(inputs):
    import gzip
    import hashlib
    import json
    import subprocess
    from collections import Counter
    from fractions import Fraction
    from pathlib import Path

    def blob(rev, path):
        return subprocess.check_output(["git", "cat-file", "blob", f"{rev}:{path}"])

    def rows(data):
        return [json.loads(row) for row in data.splitlines()]

    base = "b527d946d4530475a90536124ec69ec98a987a09"
    scores = "fa2d1ccd375b746f140bf3c781fb0aa8db891e3b"
    raw = {}
    for area, rev in [("research", "aecab0939edf1945221a0614f0d558131a7556f6"),
                      ("reviews", "e1dbf675b74c22ae616f8b3ae397413fffdf89f9")]:
        prefix = f"docs/{area}/WP-0040/evidence/run-01/"
        compressed = blob(rev, prefix + "outputs.jsonl.gz")
        runtime = json.loads(blob(rev, prefix + "runtime.json"))
        assert hashlib.sha256(compressed).hexdigest() == runtime["outputs_sha256"]
        raw[area] = rows(gzip.decompress(compressed))

    views = rows(Path(inputs).read_bytes())
    assert len(views) == len(raw["research"]) == len(raw["reviews"]) == 1623
    keyed = {}
    strata = Counter()
    for group in ("grid", "named", "control"):
        scored = rows(blob(scores, f"docs/coordination/WP-0040/results/{group}.jsonl"))
        if group != "control":
            old = {}
            for wp in ("0038", "0039"):
                folder = "docs/coordination/WP-" + wp + "/"
                path = folder + f"results/{group}.jsonl"
                original = blob(base, path)
                receipt = json.loads(blob(base, folder + "publication-receipt.json"))["downloaded_files"][path]
                assert hashlib.sha256(original).hexdigest() == receipt["sha256"]
                old[wp] = {(v["id"], v["variant"]): v for v in rows(original)}
        for outcome in scored:
            ix = outcome["operator_row"]
            arm = outcome["label"][3]
            rec = views[ix]
            assert rec["arm"] == arm
            truth = outcome["synthetic_truth"]
            assert outcome["returned"] == rec["y"]
            assert outcome["mutable"] == rec["names"]
            if group != "control":
                key = tuple(outcome["label"][1:3])
                candidate, prior = old["0038"][key], old["0039"][key]
                observed = candidate["observed"]
                values = {"T": observed["total"]}
                values.update({"A" + str(i): x for i, x in enumerate(observed["amounts"], 1)})
                values.update({"B" + str(i): x for i, x in enumerate(observed["balances"])})
                names = rec["names"]
                assert names == prior["mutable"] and rec["dist"] == prior["distance_by_mask"]
                assert rec["status"] == candidate["answer"]["status"]
                assert rec["y"] == truth == [candidate["truth"][n] for n in names]
                a = candidate["answer"]
                offsets = a["finite"] + ([[]] if a["clean"] else [])
                expected = {tuple(values[n] - dict(err).get(n, 0) for n in names) for err in offsets}
                assert expected == set(map(tuple, rec["points"]))
                if a["families"]:
                    f, = a["families"]
                    off = dict(zip(f["support"], f["offset"], strict=True))
                    step = dict(zip(f["support"], f["slope"], strict=True))
                    line = dict(h=[values[n]-off.get(n,0) for n in names],
                                s=[-step.get(n,0) for n in names], excluded=f["excluded"])
                    assert rec["line"] == line
                else:
                    assert rec["line"] is None
                if group == "grid" and arm == "B":
                    strata[(prior["n"], prior["domain"], rec["dist"][-1])] += 1
            answer = outcome["decision"]
            for area in raw:
                assert raw[area][ix]["exception"] is None
                equal(answer, raw[area][ix]["answer"], area)
            audit_return(rec, answer)
            if truth is not None:
                member = (truth in rec["points"] or
                          line_intersection(rec["line"], range(len(truth)), truth) is not None)
                assert member == outcome["truth_in_candidates"]
                expected = ("withheld" if answer["count"] != 1 else
                            "correct" if answer["points"] == [truth] else "wrong")
                assert expected == outcome["correctness"]
            keyed[tuple(outcome["label"])] = outcome
    assert len(keyed) == 1623
    partition = Counter()
    for (_, _, d), n in strata.items():
        partition[d] += n
    assert partition == {None: 76, 2: 23, 3: 155, 4: 34}
    assert {(n, domain): k for (n, domain, d), k in strata.items() if d == 4} == {
        (2,"OCR_OPEN"):6,(2,"TRUSTED_OPEN"):4,(3,"OCR_OPEN"):16,(3,"TRUSTED_OPEN"):8}
    named = [v for k, v in keyed.items() if k[:3] == ("named","C6","ocr")]
    assert len(named) == 5
    c6 = {r["label"][3]: r["decision"] for r in named}
    assert c6["R"]["q"].bit_count() == c6["R"]["d"] == 3
    assert c6["F"]["diag"]["constant_mask"].bit_count() == 4
    assert c6["R"]["q"] & c6["F"]["diag"]["constant_mask"] == 0
    p = Fraction(1, 10)
    print("C6 exact illustration", [str((1-p)**m + m*p*(1-p)**(m-1)) for m in (3,4,8)])
    print("Both raw routes and signed upstream data verified; all", len(keyed), "complete decisions checked.")


if __name__ == "__main__":
    import sys
    audit(sys.argv[1])

def audit_protocol_regressions():
    """Check mixed paired populations, incomplete costs and multiple tied boxes."""
    from fractions import Fraction
    import subprocess

    path = "docs/coordination/WP-0040/protocol.py"
    source = subprocess.check_output(["git", "cat-file", "blob",
                                     "c7a8d2d0343ee5aa286709a9af56eafc3080fcd0:" + path])
    namespace = {}
    exec(compile(source, path, "exec"), namespace)
    decision, boxes = namespace["decision"], namespace["box_audit"]
    def check(expect, changes=(), cost_changes=(), **kw):
        base = dict(B="A", E="A", R="C", F="C", T="C", ambiguous=True)
        singleton = dict(B="W", E="W", R="W", F="W", T="W", ambiguous=False)
        data = [dict(base) for _ in range(23)] + [singleton]
        cost = [dict(E=(1,3,8), R=(2,8,2), F=(4,18,4), T=(1,25,3)) for _ in data]
        for i, k, v in changes:
            data[i][k] = v
        for i, k, v in cost_changes:
            cost[i][k] = v
        result = decision(data, [True]*23+[False], cost, **kw)
        equal(expect, result["verdict"], "priority")
        for arm in "BERFT":
            assert sum(result["counts"][arm].values()) == 24
            assert sum(result["transitions"][arm].values()) == 24
            assert result["transitions"][arm]["WW"] == 1
        return result

    base = check("CONSIDER_R", [(0,"E","W")])
    assert base["new_wrong_E"] == 1 and base["cost_totals"]["R"] == [46,184,46]
    assert base["cost_totals"]["F"] == [92,414,92] and base["h2"]
    check("FEASIBILITY", cost_changes=[(2,"R",None)])
    check("HOLD_COMPARISON", [(0,"F","W")], [(2,"R",None)])
    check("HOLD_COMPARISON", controls_ok=False)
    check("HOLD_COMPARISON", leak=True)
    t = check("PREFER_T", cost_changes=[(0,"R",(2,8,25))])
    assert t["equal_performance"] and t["h1"] == {"T":True,"R":True}
    check("NO_WINNER", [(0,"R","A")])
    # A loss on an inherited correct case invalidates H1 despite many recoveries.
    lost = check("NO_WINNER", [(0,"B","C"),(0,"ambiguous",False),(0,"R","A"),(0,"T","A")])
    assert not any(lost["h1"].values())
    b = [(0,0,2,2),(0,0,1,2),(1,1,3,3),(4,0,6,2)]
    ref = [(0,0,2,2)]*4
    assert boxes(3,[3,5,9],b,ref)==dict(selected="3/4",other_mean=str(
        (Fraction(1+Fraction(1,7),2)+Fraction(1,2))/2),alternatives=2,missing=0,degenerate=0)
    invalid = boxes(3,[3,12],b,[None,ref[1],(4,4,4,6),ref[3]])
    assert invalid==dict(selected=None,other_mean=None,alternatives=1,missing=1,degenerate=1)
    print("Additional mixed-stratum decision, attribution, planned-cost and box-overlap cases passed.")


if __name__ == "__main__":
    audit_protocol_regressions()
