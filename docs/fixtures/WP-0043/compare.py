#!/usr/bin/env python3
"""WP-0043 comparison: join frozen oracle expectations with machine observations.

Author: eld-fixture-claude (Claude Code, claude-opus-5-5).  Standard library only.

Inputs
  --expected  expected/expected.jsonl            (oracle.py expect; frozen before candidate exposure)
  --observed  observations.jsonl                 (one wp0043.observation.v1 object per run)
  --cases     generated/cases.jsonl              (run_id <-> case_id; the scorer never sees it)
  --check-map optional wp0043.checkmap.v1 JSON   (generic candidate->oracle check-name translation)
Outputs
  --out       comparison.jsonl  one line per case, joined on run_id / case_id
  --summary   summary.json

Agreement on a case requires: equal verdict; candidate first discrepancy inside the
oracle's first interval (scoring.md: simultaneous order is an interval); equal sets of
(step, phase) carrying conflicts; equal sets of (step, phase) carrying missing evidence.
Slot, byte offset and translated check names are reported and, where both sides supply
them, compared; they do not change the agreement bit unless --strict-detail is given.
Exit status: 0 all cases agree, 1 at least one disagreement or missing observation,
2 malformed input.  This program reads observations only; it never computes verdicts.
"""

import argparse
import json
import sys

RANK = {"CFG": 0, "ROW": 1, "B_entry": 2, "C0_raw": 3, "C1_post_rep": 4, "C2_post_page": 5,
        "Y_select": 6, "D_exit": 7, "PUB": 8, "TERM": 9}


def read_jsonl(path):
    out = []
    with open(path, "rb") as fh:
        for n, line in enumerate(fh.read().decode("utf-8").splitlines(), 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError as exc:
                    raise SystemExit("malformed JSON at %s:%d: %s" % (path, n, exc))
    return out


def pos(step, phase):
    if phase not in RANK:
        return None
    return (-2 if step is None else step, RANK[phase])


def phase_set(items):
    return sorted({(x.get("step"), x.get("phase")) for x in items or []}, key=lambda t: pos(*t) or (99, 99))


def check_set(items, cmap):
    out = set()
    for x in items or []:
        chk = x.get("check")
        out.add((x.get("step"), x.get("phase"), cmap.get(chk, chk) if cmap is not None else chk))
    return out


def first_relation(ef, of):
    if ef is None:
        return "n/a" if of is None else "unexpected_first"
    if of is None:
        return "missing_first"
    lo = pos(ef.get("step_from", ef.get("step")), ef.get("phase_from", ef.get("phase")))
    hi = pos(ef.get("step"), ef.get("phase"))
    p = pos(of.get("step"), of.get("phase"))
    if p is None:
        return "unknown_phase"
    exact = (of.get("step"), of.get("phase")) == (ef.get("step"), ef.get("phase")) and \
        of.get("phase_from", of.get("phase")) == ef.get("phase_from", ef.get("phase"))
    if exact:
        return "exact"
    if lo <= p <= hi:
        return "within_interval"
    return "differ"


def detail_relation(ef, of):
    res = {}
    if ef is None or of is None:
        return res
    es, os_ = ef.get("slot_id"), of.get("slot_id")
    res["slot"] = "not_reported" if es is None or os_ is None else ("equal" if es == os_ else "differ")
    eo, oo = ef.get("dense_token_offset"), of.get("dense_token_offset")
    cand = ef.get("dense_token_offset_candidates")
    if oo is None:
        res["dense_token_offset"] = "not_reported"
    elif eo is not None:
        res["dense_token_offset"] = "equal" if eo == oo else "differ"
    elif cand:
        res["dense_token_offset"] = "consistent_with_guaranteed_lanes" if oo in cand else "outside_guaranteed_lanes"
    else:
        res["dense_token_offset"] = "oracle_none"
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="WP-0043 expected/observed comparison")
    ap.add_argument("--expected", required=True)
    ap.add_argument("--observed", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--check-map", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--strict-detail", action="store_true")
    a = ap.parse_args(argv)

    cases = {c["run_id"]: c for c in read_jsonl(a.cases)}
    expected = read_jsonl(a.expected)
    observed = {}
    dup = []
    for o in read_jsonl(a.observed):
        if o.get("schema") != "wp0043.observation.v1" or "run_id" not in o or o.get("verdict") not in ("M", "U", "P"):
            raise SystemExit("observation does not follow wp0043.observation.v1: %r" % (o.get("run_id"),))
        if o["run_id"] in observed:
            dup.append(o["run_id"])
        observed[o["run_id"]] = o
    cmap = None
    if a.check_map:
        with open(a.check_map, "rb") as fh:
            m = json.loads(fh.read())
        if m.get("schema") != "wp0043.checkmap.v1":
            raise SystemExit("check map schema")
        cmap = m["map"]

    lines = []
    summary = {"schema": "wp0043.comparison-summary.v1", "cases": 0, "agree": 0, "disagree": [], "no_observation": [],
               "unexpected_observations": sorted(set(observed) - {e["run_id"] for e in expected}),
               "duplicate_observations": dup, "verdict_pairs": {}}
    for e in expected:
        rid = e["run_id"]
        if rid not in cases or cases[rid]["case_id"] != e["case_id"]:
            raise SystemExit("expected record %s does not match cases.jsonl" % e["case_id"])
        summary["cases"] += 1
        ex = e["expected"]
        o = observed.get(rid)
        rec = {"schema": "wp0043.comparison.v1", "case_id": e["case_id"], "run_id": rid,
               "fixture": e["fixture"], "subcase": e["subcase"], "classification": e["classification"],
               "expected_verdict": ex["verdict"], "expected_first": ex["first"],
               "expected_missing": [{k: m.get(k) for k in ("row", "step", "phase", "object", "check")} for m in ex["missing"]],
               "ground_first_record_divergence": e["ground"]["first_record_divergence"],
               "ground_first_execution_divergence_step": (e["ground"]["first_execution_divergence"] or {}).get("step")}
        if o is None:
            rec.update({"status": "no_observation", "agree": False})
            summary["no_observation"].append(e["case_id"])
            lines.append(rec)
            continue
        fr = first_relation(ex["first"], o.get("first"))
        ec, oc = phase_set(ex["conflicts"]), phase_set(o.get("conflicts"))
        em, om = phase_set(ex["missing"]), phase_set(o.get("missing"))
        det = detail_relation(ex["first"], o.get("first"))
        rec.update({
            "observed_verdict": o["verdict"], "observed_first": o.get("first"),
            "verdict_match": ex["verdict"] == o["verdict"], "first_relation": fr, "first_detail": det,
            "conflict_phases": {"equal": ec == oc,
                                "only_expected": [list(x) for x in ec if x not in oc],
                                "only_observed": [list(x) for x in oc if x not in ec]},
            "missing_phases": {"equal": em == om,
                               "only_expected": [list(x) for x in em if x not in om],
                               "only_observed": [list(x) for x in om if x not in em]},
            "observed_missing": [{k: m.get(k) for k in ("row", "step", "phase", "object", "check")} for m in o.get("missing") or []],
            "observed_source": o.get("scorer"),
        })
        if cmap is not None:
            ek, ok = check_set(ex["conflicts"], None), check_set(o.get("conflicts"), cmap)
            rec["conflict_checks"] = {"equal": ek == ok, "only_expected": sorted(map(list, ek - ok), key=str),
                                      "only_observed": sorted(map(list, ok - ek), key=str)}
        agree = rec["verdict_match"] and fr in ("exact", "within_interval", "n/a") \
            and rec["conflict_phases"]["equal"] and rec["missing_phases"]["equal"]
        if a.strict_detail:
            agree = agree and all(v in ("equal", "not_reported", "consistent_with_guaranteed_lanes", "oracle_none")
                                  for v in det.values())
            if cmap is not None:
                agree = agree and rec["conflict_checks"]["equal"]
        rec["status"] = "agree" if agree else "disagree"
        rec["agree"] = agree
        pair = "%s->%s" % (ex["verdict"], o["verdict"])
        summary["verdict_pairs"][pair] = summary["verdict_pairs"].get(pair, 0) + 1
        if agree:
            summary["agree"] += 1
        else:
            summary["disagree"].append({"case_id": e["case_id"], "verdict": pair, "first": fr,
                                        "conflict_phases_equal": rec["conflict_phases"]["equal"],
                                        "missing_phases_equal": rec["missing_phases"]["equal"]})
        lines.append(rec)
    with open(a.out, "wb") as fh:
        fh.write(b"".join((json.dumps(x, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii") for x in lines))
    with open(a.summary, "wb") as fh:
        fh.write(json.dumps(summary, sort_keys=True, indent=1).encode("ascii") + b"\n")
    print("cases=%d agree=%d disagree=%d no_observation=%d unexpected=%d" % (
        summary["cases"], summary["agree"], len(summary["disagree"]), len(summary["no_observation"]),
        len(summary["unexpected_observations"])))
    ok = summary["agree"] == summary["cases"] and not summary["unexpected_observations"] and not dup
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
