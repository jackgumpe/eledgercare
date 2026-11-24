"""Reconcile pre-exposure reviewer evidence with exact published WP-0034 custody records."""
import hashlib
import json
import re
import subprocess
from pathlib import Path


REVIEW = "127f06219bb60fa7a90b96547019e29cefc735e6"
CUSTODY = "22f804598a505f7344a239428422b12494f88cef"
CUSTODY_SOURCE = "93f9cda5b99660d6936635ddced88b11b9d9a6da"
REPORT = "147e24835ee0eab8ca6561ff6fcb1c05dedf11ce"
DIRECTORY = "docs/research/WP-0034/custody/"
SCRATCH = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0034/review")
REPORT_PATH = "docs/agent-reports/eld-twin-custodian/WP-0034/004_2026-11-24_research_eld-twin-custodian.md"
LABELS = {
    "ordinary_answerable": "Ordinary answerable posting",
    "maintenance_summary_answerable": "Maintenance-summary answerable posting",
    "unresolved_scope_must_abstain": "Unresolved scope, must abstain",
    "target_structure_ambiguity_must_abstain": "Ambiguous target structure, must abstain",
}
FIELDS = {"planned_pairs": "planned_pairs", "planned_binders": "planned_binders",
          "supported_pairs": "receipt_confirmed_pairs", "supported_binders": "receipt_confirmed_binders",
          "missing_pairs": "pairs_missing_evidence", "missing_binders": "binders_missing_evidence",
          "unavailable_terminal_slots_per_arm": "unavailable_terminal_slots_per_arm"}


def check(test, message):
    if not test:
        raise ValueError(message)


def blob(rev, path):
    return subprocess.check_output(["git", "cat-file", "blob", rev + ":" + path])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def index(rows):
    mapped = {(r["pages"], r["stratum"]): r for r in rows}
    check(len(rows) == len(mapped) == 8 and set(mapped) == {(n, k) for n in (12, 30) for k in LABELS},
          "Duplicate, missing or unexpected schedule row")
    return mapped


def compare():
    replay = {}
    for name in ("public-observations.json", "inventory.json"):
        reproduced = (SCRATCH / "replay-001" / name).read_bytes()
        check(blob(CUSTODY, DIRECTORY + name) == reproduced, "Replayed bytes differ at " + name)
        replay[name] = {"sha256": sha(reproduced), "bytes": len(reproduced), "identical": True}
    raw_report = blob(REPORT, REPORT_PATH)
    report = raw_report.decode()
    raw_review = blob(REVIEW, "docs/reviews/WP-0034/independent-inventory.json")
    review = json.loads(raw_review)
    custody = json.loads(blob(CUSTODY, DIRECTORY + "inventory.json"))
    observations = json.loads(blob(CUSTODY, DIRECTORY + "public-observations.json"))
    check(review["decision"] == "admission_blocked_missing_receipts" and
          custody["status"] == "unavailable_within_observed_authorized_perimeter" and
          not custody["source_candidates_requiring_separate_identification"], "Disposition")
    check(review["required_unattested"] == custody["required_admission_records"] and
          len(custody["missing_prerequisites"]) == 4, "Admission elements")
    heads = {"refs/heads/" + k: rev for k, rev in review["public_remote_heads"].items()}
    check(heads == observations["public_refs"], "Remote observations differ")
    observations_count = len(heads)
    for key, names in custody["namespace_at_base"].items():
        check(review["directory_observations"]["public_tree_children"][key] == names, "Namespace " + key)
    product_names = [p for p in observations["product_top_level_names"] if not re.fullmatch(r"GPU-[a-fA-F0-9-]+\.lock", p)]
    check(sorted(product_names) == review["directory_observations"]["scratch_directory_names_only"], "Public scratch namespace")

    left, right = index(review["strata"]), index(custody["schedule"])
    rows = []
    for key in left:
        a, b = left[key], right[key]
        check(all(a[i] == b[j] for i, j in FIELDS.items()), "Schedule mismatch " + str(key))
        p, n = a["planned_pairs"], a["planned_binders"]
        check((p, n) == ((3, 6) if key[1].endswith("_answerable") else (1, 2)), "Wrong denominator")
        check(f"| {key[0]} | {LABELS[key[1]]} | {p} / {n} | 0 / 0 | {p} / {n} |" in report,
              "Canonical report row " + str(key))
        rows.append({**a, "published_custody_receipt_and_report_agree": True})
    r, c = review["per_implementation"], custody["per_implementation"]
    check((r["independent_families_required"], r["answerable_binders_planned"], r["safety_binders_planned"],
           r["answerable_rank_denominator_pairs"], r["scheduled_terminal_slots"], r["unavailable"])
          == (c["families_planned"], c["answerable_binders_planned"], c["safety_binders_planned"],
              c["answerable_pairs_planned"], c["terminal_slots_planned"], c["unavailable_terminal_slots"])
          == (16, 24, 8, 12, 96, 96), "Trial denominator totals")
    check(c["terminal_decisions_executed"] == 0 and r["scores"] is None and r["rank_result"] is None and
          len(r["arms"]) == 3 and set(r["arms"]) == set(c["arms"]), "Arm availability")
    for arm, cr in c["arms"].items():
        rr = r["arms"][arm]
        check(cr["planned_terminal_slots"] == rr["scheduled_terminal_slots"] == cr["unavailable"] == rr["unavailable"] == 32
              and cr["executed"] == 0, arm)
        check(all(rr[k] is None for k in ("C", "W", "A", "correct_posting_coverage", "safety")) and
              all(cr[k] is None for k in ("correct_postings", "wrong_postings", "abstentions", "rank_successes",
                                          "correct_posting_coverage", "safety_outcomes", "safety_gate", "paired_changes")), arm)

    custody_projections = custody["immutable_historical_projections"]
    intersecting = {}
    for rec in review["historical_evidence"]:
        path = rec["path"]
        if path not in custody_projections:
            continue
        proj = custody_projections[path]
        common = sorted(set(rec["public_fields"]).intersection(proj["aggregate_fields"]))
        check(rec["sha256"] == proj["sha256"] and common and
              all(rec["public_fields"][k] == proj["aggregate_fields"][k] for k in common), path)
        intersecting[path] = common
    check(len(intersecting) == 8, "Common high-level decision receipt count")
    return {"review_evidence": REVIEW, "review_evidence_sha256": sha(raw_review),
            "custody_source": CUSTODY_SOURCE, "custody_evidence": CUSTODY, "custody_report": REPORT,
            "custody_report_sha256": sha(raw_report), "replay": replay, "public_ref_bindings_equal": observations_count,
            "identical_projected_fields_on_common_receipts": intersecting, "matching_schedule_rows": rows,
            "equal_decisions": {"confirmed_pairs": 0, "confirmed_binders": 0, "unavailable_per_implementation": 96,
                                "valid_scored_outcomes": None, "answerable_pairs": 12, "safety_binders": 8,
                                "unavailable_per_arm": 32, "number_of_arms": 3},
            "source_review": "Public receipt projections and namespace checks. Both reviewers of availability used positive attestation as the admission condition. Scope is limited to authorized public holdings. The packet-level scratch listing and common-snapshot replay were additional custody checks.",
            "disposition": "accept_custody_inventory_and_block_trial"}


if __name__ == "__main__":
    evidence = compare()
    outfile = SCRATCH / "comparison.json"
    with outfile.open("x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(f"{evidence['disposition']}, {len(evidence['matching_schedule_rows'])} rows, sha256 {sha(outfile.read_bytes())}")
