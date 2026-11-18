"""WP-0017 A3 product scorecard (non-gate telemetry) and offline simulated margin flags (eld-rd-reviewer).

Stdlib only. Runs only after the A3 gate has been decided by the derived G0 tools; it never changes a gate.

* Signed net critical repairs native -> carbon_surgical per family/order/view, and net repairs per extra
  second versus the stored Windows reference (A 15.6546455 s), copied from the derived stage-2 summary.
* Malformed headers per arm, copied from the derived stage-1 record.
* Locked behaviour: every scored prediction must carry flagged == false on every span/cell.
* Simulated margin flags (offline only): a critical path is "would-flag" when its logged minimum
  identifier-token top-two gap is strictly below 0.125 logits, the threshold predeclared in design
  PROTOCOL.md at 1fad21c (verified from the pinned blob). Margins from forced counterfactual branches are
  never transferred to free-emitted fields. Reported per arm: caught errors
  (wrong and would-flag), missed errors, false alarms (correct and would-flag), coverage and missingness.
  The threshold is never chosen, tuned or swept here.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import MARGIN_GAP_LOGITS, Check, all_flags_false, blob, load, sha_file, utc, write_new  # noqa: E402


def simulate(critical, margins, threshold):
    """critical: [{at, correct}] for one arm; margins: {at: min_margin or None}. Pure."""
    c = dict(paths=len(critical), with_margin=0, missing_margin=0, caught=0, missed=0, false_alarms=0, quiet_correct=0,
             missing_on_errors=0)
    for x in critical:
        m = margins.get(x["at"])
        if m is None:
            c["missing_margin"] += 1
            c["missing_on_errors"] += (not x["correct"])
            continue
        c["with_margin"] += 1
        flag = m < threshold
        if x["correct"]:
            c["false_alarms" if flag else "quiet_correct"] += 1
        else:
            c["caught" if flag else "missed"] += 1
    c["coverage"] = c["with_margin"] / c["paths"] if c["paths"] else None
    c["flag_volume"] = c["caught"] + c["false_alarms"]
    return c


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage1", type=Path, required=True)
    ap.add_argument("--stage2", type=Path, required=True, help="derived score_all summary.json")
    ap.add_argument("--scores", type=Path, required=True, help="derived score_all private scores/ directory")
    ap.add_argument("--margins", type=Path, help="normalized {arm_key: {path: min_margin|null}} built from A3 logs")


    ap.add_argument("--out", type=Path, required=True, help="new private directory")
    a = ap.parse_args()
    check = Check()
    s1, s2 = load(a.stage1), load(a.stage2)
    check(s2["stage1_sha256"] == sha_file(a.stage1), "stage 2 was produced from this stage 1")
    a.out.mkdir(parents=True, exist_ok=False)
    net = {k: dict(net_recovery=v["critical"]["net_recovery"], new_unflagged=v["critical"]["new_unflagged"],
                   four_way=v["critical"]["four_way"])
           for k, v in s2["comparisons"].items() if v["group"] == "gate"}
    win = {k: v.get("recovery") for k, v in s2["comparisons"].items() if v["group"] == "windows"}
    malformed = {}
    for o, r in s1["runs"].items():
        for mode, arm in r["arms"].items():
            g = arm["summary"].get("grammar_measured", {})
            malformed[f"{o}:{mode}"] = dict(malformed_headers=g.get("malformed_headers"),
                                            header_title_level=g.get("header_title_level"))
    flags_false = {}
    for o, r in s1["runs"].items():
        for mode, arm in r["arms"].items():
            for fam, m in arm["measured"].items():
                flags_false[f"{fam}:{mode}:{o}"] = all_flags_false(load(m["prediction"]))
    check(all(flags_false.values()), "flagged == false on every scored prediction (locked)")
    sim = None
    if a.margins:
        protocol = blob("design/PROTOCOL.md").decode("utf-8")
        check("<0.125" in protocol, "predeclared strict top-two gap < 0.125 logits present in design PROTOCOL.md")
        tau = MARGIN_GAP_LOGITS
        margins = load(a.margins) if a.margins else {}
        sim = dict(threshold_logits=tau, rule="flag when minimum effective top-two gap over aligned emitted ID tokens < 0.125",
                   source="design/PROTOCOL.md at 1fad21c (fe915bba...)", arms={},
                   coverage_note="only aligned positions actually measured; absent/malformed/uninstrumented spans counted as missing")
        for f in sorted(a.scores.glob("*-frozen.json")):
            key = f.name[:-len("-frozen.json")]
            crit = [dict(at=c["at"], correct=c["correct"]) for p in load(f)["pages"] for c in p["critical"]]
            sim["arms"][key] = simulate(crit, margins.get(key, {}), tau)
    else:
        sim = "not simulated: no margin log was supplied"
    rec = dict(kind="WP-0017 A3 product scorecard (non-gate)", reviewer="eld-rd-reviewer", created_utc=utc(),
               stage1_sha256=sha_file(a.stage1), stage2_sha256=sha_file(a.stage2), gate_unchanged=s2["verdict"],
               net_critical=net, windows_recovery=win, malformed=malformed, flags_false=flags_false,
               simulated_margin_flags=sim, checks_run=check.count, failures=check.failures)
    digest = write_new(a.out / "scorecard.json", rec)
    print(json.dumps(dict(scorecard=str(a.out / "scorecard.json"), sha256=digest, failures=check.failures), indent=1))
    return 0 if not check.failures else 1


if __name__ == "__main__":
    sys.exit(main())
