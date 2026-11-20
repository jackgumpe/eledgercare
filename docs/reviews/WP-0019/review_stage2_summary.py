"""WP-0019 reviewer Stage 2 machine summary (post-key-release analysis; Addendum 3). Reads only frozen outputs.

Joins the frozen field rows (review_score.py) with the released strata, and reports:
- per-stratum transitions, selection, full/crop agreement, flags and decisions;
- the larger-research criterion per PREREGISTRATION section 9;
- timing under both aggregation rules: the coordinator's primary rule (all treatment pages over the sum of all
  treatment durations, dd81aa35) and the reviewer's preregistered rule (treatment >= 30 pages/min in AB and in BA).
No OCR, no scorer change, no tuning.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_common import read_json, sha256_file, write_new


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--score", required=True)
    p.add_argument("--strata", action="append", required=True, help="FAMILY=strata.json")
    p.add_argument("--timing", required=True)
    p.add_argument("--decision", required=True)
    p.add_argument("--ppm", type=float, default=30.0)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    score = read_json(a.score)
    sdir = Path(a.score).parent
    strata = {k: v for k, v in (x.split("=", 1) for x in a.strata)}
    fams = {}
    for fam, path in strata.items():
        st = {x["at"]: x["stratum"] for x in read_json(path)["locations"]}
        per_run = {}
        for run in score["runs"]:
            rows = read_json(sdir / "joins" / run / f"{fam}-rows.json")
            missing = sorted(set(st) - {r["at"] for r in rows})
            table = Counter()
            for r in rows:
                key = "|".join([st.get(r["at"], "unstratified"), "critical" if r["critical"] else "noncritical", r["transition"],
                                "selected" if r["coverage"]["covered"] else "unselected", r["full_vs_crop"],
                                "flagged" if r["treat"]["flagged"] else "unflagged", str(r["coverage"]["author_decision"])])
                table[key] += 1
            crit = [r for r in rows if r["critical"]]
            per_run[run] = dict(
                strata_locations_missing_from_rows=missing,
                stratum_table=dict(sorted(table.items())),
                criticals=len(crit), transitions=dict(Counter(r["transition"] for r in crit)),
                selected_criticals=sum(r["coverage"]["covered"] for r in crit),
                unselected_criticals=sum(not r["coverage"]["covered"] for r in crit),
                by_stratum={s: dict(Counter(r["transition"] for r in rows if st.get(r["at"]) == s))
                            for s in sorted(set(st.values()))},
                negatives_changed=[r["at"] for r in rows if st.get(r["at"], "").endswith("negative") and r["changed"]],
                spaced_id_rows=[dict(at=r["at"], expected=r["expected"], base=r["base"]["observed"], treat=r["treat"]["observed"],
                                     transition=r["transition"], crop=r["diagnostic"] and r["diagnostic"]["observed"],
                                     decision=r["coverage"]["author_decision"]) for r in rows if st.get(r["at"]) == "legitimate_space"],
                wrong_critical_rows=[dict(at=r["at"], stratum=st.get(r["at"]), expected=r["expected"], base=r["base"]["observed"],
                                          treat=r["treat"]["observed"], flagged=r["treat"]["flagged"],
                                          crop=r["diagnostic"] and r["diagnostic"]["observed"], decision=r["coverage"]["author_decision"])
                                     for r in crit if not r["treat"]["ok"] or r["full_vs_crop"] == "disagree"],
                summary={k: score["runs"][run]["families"][fam]["summary"][k] for k in
                         ("WR", "RW", "WW", "RR", "WW_changed", "net", "newly_unflagged", "flag_transitions", "blanks", "legitimate_space",
                          "coverage", "disagreements", "diagnostic_crop", "decisions", "author_decisions", "disagreement_matrix_critical",
                          "frozen_compare")})
        fams[fam] = dict(strata=dict(path=path, sha256=sha256_file(path)), runs=per_run)
    t = read_json(a.timing)
    runs = t["runs"]
    tb_pages = sum(r["pages"] for r in runs.values())
    tb_secs = sum(r["B"]["seconds"] for r in runs.values())
    ta_secs = sum(r["A"]["seconds"] for r in runs.values())
    by_order = {o: 60 * sum(r["pages"] for r in runs.values() if r["order"] == o) / sum(r["B"]["seconds"] for r in runs.values() if r["order"] == o)
                for o in ("AB", "BA")}
    timing = dict(
        primary_rule_combined_treatment_pages_per_min=60 * tb_pages / tb_secs,
        combined_full_only_pages_per_min=60 * tb_pages / ta_secs,
        combined_added_ms_per_page=1000 * (tb_secs - ta_secs) / tb_pages,
        treatment_pages_per_min_by_order=by_order,
        reviewer_prereg_rule_min_order_pages_per_min=min(by_order.values()),
        per_run={k: dict(order=v["order"], family=v["family"], startup_ms=v["startup_ms"], warmup_ms=v["warmup_ms"],
                         A_pages_per_min=v["A"]["pages_per_min"], B_pages_per_min=v["B"]["pages_per_min"],
                         added_ms_per_page=v["added_ms_per_page"], crops_per_page=v["B"]["crops_per_page"]) for k, v in runs.items()},
        primary_rule_met=60 * tb_pages / tb_secs >= a.ppm, reviewer_prereg_rule_met=min(by_order.values()) >= a.ppm, threshold=a.ppm)
    gate = score["gate"]
    pooled_wr = {run: sum(fams[f]["runs"][run]["transitions"].get("WR", 0) for f in fams) for run in score["runs"]}
    crit = dict(
        fresh_critical_recovery=dict(required=">=1 pooled WR", observed=pooled_wr, met=all(v >= 1 for v in pooled_wr.values())),
        zero_newly_wrong=dict(observed={run: {f: fams[f]["runs"][run]["transitions"].get("RW", 0) for f in fams} for run in score["runs"]},
                              met=all(fams[f]["runs"][run]["transitions"].get("RW", 0) == 0 for f in fams for run in score["runs"])),
        preserved_blanks=dict(observed={run: {f: fams[f]["runs"][run]["summary"]["blanks"] for f in fams} for run in score["runs"]},
                              met=all(fams[f]["runs"][run]["summary"]["blanks"]["lost"] == 0 for f in fams for run in score["runs"])),
        speed=dict(primary=timing["primary_rule_met"], reviewer_prereg=timing["reviewer_prereg_rule_met"]),
        reproducible=gate["reproducible"], score_component=gate["score_component"])
    dec = read_json(a.decision)
    quality_fail = not crit["fresh_critical_recovery"]["met"]
    verdict = ("FAIL" if quality_fail else ("PASS" if dec["verdict"] == "STAGE2_RELEASE_SUPPORTED" else "INCONCLUSIVE"))
    doc = dict(kind="wp0019-review-STAGE2-RESULT", score=dict(path=a.score, sha256=sha256_file(a.score)),
               decision_frozen=dict(path=a.decision, sha256=sha256_file(a.decision), verdict=dec["verdict"],
                                    control_failures=dec["control_failures"]),
               families=fams, timing=timing, criterion=crit, larger_research_criterion=verdict,
               reasoning=("No fresh critical recovery in either family or order, so the criterion fails on its quality "
                          "component. The control shortfalls (K1 strict failure, no audited fresh run) concern label isolation "
                          "and could only invalidate a positive result; they cannot produce or hide a recovery."))
    sha = write_new(Path(a.out), doc)
    print(json.dumps(dict(out=a.out, sha256=sha, larger_research_criterion=verdict, criterion=crit,
                          timing={k: timing[k] for k in ("primary_rule_combined_treatment_pages_per_min", "treatment_pages_per_min_by_order",
                                                         "combined_added_ms_per_page")}), indent=1))


if __name__ == "__main__":
    main()
