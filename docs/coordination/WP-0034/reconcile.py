"""Reconcile the two published admission inventories at their original Git revisions."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

PACKET = "docs/coordination/WP-0034/"
BASE = "ffec32d08f4137bea6d01505b1677b64cccbf5bc"
RESERVATION = "604a3a051d901ec8a1a8f7d6407ef57d99b19c10"
ROOT_EVIDENCE = "3ed0fffc8de15450c31eae4fd9fc787634b6cd14"


def git(*args):
    return subprocess.check_output(["git", "--no-optional-locks", *args])


def require(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def record(revision, path):
    raw = git("cat-file", "blob", f"{revision}:{path}")
    binding = {"revision": revision, "path": path, "sha256": hashlib.sha256(raw).hexdigest(),
               "git_blob": git("rev-parse", f"{revision}:{path}").decode().strip()}
    return raw, binding


def keyed_rows(rows):
    mapped = {(row["pages"], row["stratum"]): row for row in rows}
    require(len(mapped) == len(rows), "Duplicate horizon and stratum")
    return mapped


def compare(custody, review, terms):
    require(custody["status"] == "unavailable_within_observed_authorized_perimeter"
            and custody["source_candidates_requiring_separate_identification"] == []
            and review["decision"] == "admission_blocked_missing_receipts", "Independent gate decisions require reconciliation")
    require(custody["required_admission_records"] == review["required_unattested"] == terms["required_public_attestations"],
            "Admission prerequisite disagreement")
    crows = keyed_rows(custody["schedule"])
    rrows = keyed_rows(review["strata"])
    schedule = terms["required_pairs_per_horizon"]
    keys = [(h, s) for h in terms["horizons"] for s in schedule]
    require(set(crows) == set(rrows) == set(keys), "Missing or unexpected stratum")
    rows = []
    for horizon, stratum in keys:
        c, r = crows[horizon, stratum], rrows[horizon, stratum]
        pairs = schedule[stratum]
        binders = pairs * terms["members_per_pair"]
        for unit, planned in (("pairs", pairs), ("binders", binders)):
            require(c["planned_" + unit] == r["planned_" + unit] == planned, "Planned count differs")
            require(c["receipt_confirmed_" + unit] == r["supported_" + unit] == 0, "Supported inventory differs")
            require(c[unit + "_missing_evidence"] == r["missing_" + unit] == planned, "Missing count differs")
        require(c["unavailable_terminal_slots_per_arm"] == r["unavailable_terminal_slots_per_arm"] == binders,
                "Unavailable schedule differs")
        rows.append({"pages": horizon, "stratum": stratum, "required_pairs": pairs, "confirmed_pairs": 0, "missing_pairs": pairs,
                     "required_binders": binders, "confirmed_binders": 0, "missing_binders": binders})
    totals = {key: sum(row[key] for row in rows) for key in rows[0] if key not in ("pages", "stratum")}
    require(totals["required_pairs"] == terms["independent_families"] == 16 and totals["required_binders"] == 32,
            "Family or binder denominator differs")
    c, r = custody["per_implementation"], review["per_implementation"]
    require(c["terminal_decisions_executed"] == 0 and c["unavailable_terminal_slots"] == r["unavailable"]
            == terms["planned_decisions_per_implementation"] == 96, "Terminal denominator differs")
    require(c["answerable_binders_planned"] == r["answerable_binders_planned"] == 24
            and c["safety_binders_planned"] == r["safety_binders_planned"] == 8
            and c["answerable_pairs_planned"] == r["answerable_rank_denominator_pairs"] == 12, "Metric denominator differs")
    require(set(terms["arms"]) == set(c["arms"]) == set(r["arms"]), "Arm set differs")
    for arm in terms["arms"]:
        left, right = c["arms"][arm], r["arms"][arm]
        require(left["executed"] == 0 and left["unavailable"] == right["unavailable"] ==
                left["planned_terminal_slots"] == right["scheduled_terminal_slots"] == 32, "Arm accounting differs")
        require(all(left[k] is None for k in ("correct_postings", "wrong_postings", "abstentions", "rank_successes",
                    "correct_posting_coverage", "safety_outcomes", "safety_gate", "paired_changes")), "Custody contains outcomes")
        require(all(right[k] is None for k in ("C", "W", "A", "correct_posting_coverage", "safety"))
                and r["scores"] is None and r["rank_result"] is None, "Review contains outcomes")
    return rows, totals


REVIEW_INVENTORY = "docs/reviews/WP-0034/independent-inventory.json"
CUSTODY_REPORT = "docs/agent-reports/eld-twin-custodian/WP-0034/004_2026-11-24_research_eld-twin-custodian.md"
REVIEW_REPORT = "docs/agent-reports/eld-rd-reviewer/WP-0034/002_2026-11-24_review_eld-rd-reviewer.md"


def load_json(revision, path):
    raw, binding = record(revision, path)
    return json.loads(raw), binding


def reconcile(args):
    terms, contract = load_json(RESERVATION, PACKET + "contract.json")
    root, root_binding = load_json(ROOT_EVIDENCE, PACKET + "public-metadata.json")
    custody, cust_binding = load_json(args.custody_evidence, "docs/research/WP-0034/custody/inventory.json")
    review, review_binding = load_json(args.review_evidence, REVIEW_INVENTORY)
    require(custody["accepted_base"] == review["public_base"] == root["basis"] == terms["public_base"] == BASE,
            "Inventory base differs")
    require(review["contract"]["sha256"] == contract["sha256"] and custody["reservation"] == RESERVATION, "Contract differs")
    rows, totals = compare(custody, review, terms)
    require(all(not tip["outside_packet_paths"] for tip in root["tips_outside_accepted_history"].values()), "Unclassified ref")
    public26 = "docs/coordination/WP-0026/decision.json"
    hist = custody["immutable_historical_projections"][public26]
    counterpart = next(item for item in review["historical_evidence"] if item["path"] == public26)
    require(hist["sha256"] == counterpart["sha256"], "Historical decision digest differs")
    archive = root["prior_inputs"]["WP0026_separate_custody"]
    fields = {"blind.bound_pairs": archive["pairs"], "blind.bound_binders": archive["binders"],
              "blind.started": archive["capture_windows_issued"], "blind.verified_feature_returns": archive["capture_windows_verified"],
              "blind.completed_12_page_pairs": 1, "blind.completed_30_page_pairs": 0}
    for field, value in fields.items():
        require(hist["aggregate_fields"][field] == counterpart["public_fields"][field] == value, field)
    sources = {}
    for role, original, report, path in (
        ("custody", args.custody_evidence, args.custody_report, CUSTODY_REPORT),
        ("review", args.review_evidence, args.review_report, REVIEW_REPORT),
    ):
        git("merge-base", "--is-ancestor", original, report)
        git("merge-base", "--is-ancestor", report, "HEAD")
        _, sources[role] = record(report, path)
        require(git("rev-parse", f"HEAD:{path}") == git("rev-parse", f"{report}:{path}"), "Public report changed")
    return {
        "packet": terms["packet"], "disposition": "closed_at_admission_inputs_unavailable",
        "evaluation_author_slot": "001 unused; no operator dispatch",
        "authority": terms["authority"], "handoff": terms["handoff"], "source_pins": terms["pins"],
        "contract": contract, "independent_custody": cust_binding, "independent_review_inventory": review_binding,
        "canonical_reports": sources, "coordinator_metadata": root_binding, "strata": rows, "totals": totals,
        "accounting_per_implementation": {
            "implementation_roles": ["conditional author", "independent reproduction"],
            "arms": {a: {"planned": 32, "executed": 0, "unavailable": 32} for a in terms["arms"]},
            "per_horizon": {str(h): {"families": 8, "binders": 16, "planned": 48, "executed": 0, "unavailable": 48} for h in terms["horizons"]},
            "planned": 96, "executed": 0, "unavailable": 96,
            "technical_reason": "No receipt-supported independent fresh pair with complete authenticated windows and sealed truth commitment",
            "planned_answerable_binders_per_arm": 24, "planned_safety_binders_per_arm": 8, "planned_answerable_rank_pairs_per_arm": 12,
            "observed": dict.fromkeys(["correct_postings", "wrong_postings", "abstentions", "scores", "rank", "coverage",
                                      "safety_gate", "paired_changes", "declaration_and_posting_witnesses"]),
        },
        "missing_prerequisites": terms["required_public_attestations"],
        "historical_exclusions": {
            "WP-0024": root["prior_inputs"]["WP0024_public_development_receipts"],
            "WP-0026": {**archive, "complete_pairs_12_pages": 1, "complete_pairs_30_pages": 0, "admitted_for_WP0034": 0,
                        "authority": "Separate sealed benchmark and bounded partial acquisition"},
            "WP-0028_to_0033": root["prior_inputs"]["exposed_development"],
        },
        "interpretation": "Fresh posting benefit, rank, safety and coverage remain unmeasured for all three arms. The write-8 development result remains the extent of the evidence for relative rho=0.50.",
        "scope_limit": "Public product receipts, refs and authorized directory-name inventory establish the supported count. Undisclosed or off-repository holdings remain unknown.",
        "required_to_revisit": "An authorized opaque cohort manifest, independent sealed truth digest and complete pre-existing per-window sensor receipts meeting the frozen design. Acquisition, a different sealed benchmark or a revised cohort requires a separate decision.",
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for key in ("custody_evidence", "review_evidence", "custody_report", "review_report"):
        cli.add_argument(key)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    decision = reconcile(args)
    with args.output.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(decision, out, indent=2, allow_nan=False)
        out.write("\n")
    print(decision["disposition"], decision["totals"])
