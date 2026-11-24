"""WP-0034 public custody receipt verification. Standard library and read-only Git."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


BASE = "ffec32d08f4137bea6d01505b1677b64cccbf5bc"
RESERVATION = "604a3a051d901ec8a1a8f7d6407ef57d99b19c10"
ORIGIN = "https://github.com/jackgumpe/eledgercare.git"
SPEED = Path("C:/Users/jackg/eLedgerCare-Speed")
OUT = SPEED / "WP-0034/review/independent-inventory.json"
SCRATCH_DIRECTORIES = {"coordination"} | {f"WP-{n:04}" for n in (15,16,17,*range(23,35))}
PACKET_ROLES = {"research/wp-0034-custody", "review/wp-0034-admission"}
RELATED_TIPS = {
    "research/wp-0022-custody": "b011231afb8634b29b13c339ca3d7e3e5dd0ed58",
    "research/wp-0024-twin-custody": "b66be9a6827f209fa6b6584b6e01a6af95802af5",
    "research/wp-0026-acquisition": "d4a73206b41c13d92f88bead7fe7950b57cafd11",
    "research/wp-0026-custody": "cef965394b6a4227d954a8b3ea1367e08a2e3e2c",
    "research/wp-0028-owner-fixtures": "98702b5583d27b654b52507673985e9d307e7a54",
    "research/wp-0029-cedar-acquisition": "eb932d8aa5daf8d0f5f378c8f1276172678042e3",
}
# Expectations apply to public aggregate acquisition/provenance fields only.
EXCLUSIONS = {
    22: ("Two-page WinRT documents", {"cohort.documents": 8, "cohort.page_appearances": 16}),
    24: ("Development H0 and unmaterialized separate design", {"real_b1_calls": 16, "total_pairs": 8,
         "subsequent_trial_observations.C1": None, "subsequent_trial_observations.heldout_views": None}),
    25: ("Repeat of a historical three-page window", {"scope": "historical b01w01 ordered three-page input only"}),
    26: ("Used development captures and separately authorized held-out cohort with partial capture",
         {"development.exact_h0_pairs": 8, "development.train_c1_exact_duplicate_groups": 12,
          "blind.bound_pairs": 32, "blind.bound_binders": 64, "blind.uncached_planned": 28,
          "blind.started": 14, "blind.verified_feature_returns": 13,
          "blind.completed_12_page_pairs": 1, "blind.completed_30_page_pairs": 0}),
    28: ("Synthetic development fixture and cache inventory", {"study.document_pairs_planned": 2,
         "admission.planned_distinct_window_inputs": 11, "admission.cached_distinct_window_inputs": 10,
         "scope": "CPU-only on synthetic development data and frozen M1/M3 probes, with no native Baidu calls and no GPU lease."}),
    29: ("One exposed opening edit reused at two horizons",
         {"scope": "Two preregistered synthetic development pairs, 12 and 30 pages, using the same opening-name edit. The longer binder adds six intervening three-page windows.",
          "acquisition.excluded_warmups": 1, "acquisition.cedar_calls": 1, "acquisition.total_native_calls": 2}),
    30: ("Exposed development trace",
         {"scope": "CPU per-span trace from an independent zero state through the actual posting and its separate subsequent write. Two probes and two lengths share one opening edit on synthetic development binders."}),
    31: ("CPU replay", {"measured.development_openings": 1, "measured.held_out_inputs": 0, "measured.ocr_calls": 0}),
    32: ("Existing opening, write 8 only",
         {"scope": "Four populated M1 cells and two empty M3 cells on the single archived synthetic development opening at write 8. Original thresholds 1.0/0.1, deterministic one-thread CPU."}),
    33: ("Existing opening, no acquisition",
         {"boundary": "One prior-exposed synthetic opening shared by two lengths, frozen CPU through window 1/page 1/span 7. No later write, fresh pair, held-out, GPU, OCR, fitting, product change or posting-target evaluation."}),
}
PUBLIC_CUSTODY = {
    24: ("research/wp-0024-twin-custody", "The blind corpus was never materialized, extracted or scored."),
    26: ("research/wp-0026-custody", "Custody materialized the single authorized 32-pair held-out family after fit and calibration freeze."),
}
# WP-0027's ruling concerns only calibration on an existing cohort.
ROUTING_PROVENANCE = "eight answerable calibration pairs"
SCHEDULE = {"ordinary_answerable": 3, "maintenance_summary_answerable": 3,
            "unresolved_scope_must_abstain": 1, "target_structure_ambiguity_must_abstain": 1}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(*args):
    return subprocess.check_output(["git", *args])


def lines(*args):
    return git(*args).decode("utf-8").splitlines()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def public_blob(revision, path):
    spec = f"{revision}:{path}"
    raw = git("cat-file", "blob", spec)
    descriptor = {"revision": revision, "path": path, "git_blob": lines("rev-parse", spec)[0],
                  "sha256": digest(raw)}
    return raw, descriptor


def inventory_refs():
    heads = {}
    for line in lines("ls-remote", "--heads", "origin"):
        sha, ref = line.split()
        heads[ref.removeprefix("refs/heads/")] = sha
    require(all(heads.get(r) == rev for r, rev in RELATED_TIPS.items()), "Historical custody tip moved; reassess source")
    for ref, rev in heads.items():
        if ref in PACKET_ROLES:
            # No reads of either role's new WP-0034 work; both are contemporaneous admission-only assignments.
            continue
        if ref == "coordination/bootstrap":
            git("merge-base", "--is-ancestor", RESERVATION, rev)
            changes = lines("diff", "--name-only", RESERVATION, rev)
            require(all(p in ("INDEX.md", "CURRENT.md") or p.startswith("docs/coordination/WP-0034/") for p in changes),
                    "Integration added material beyond packet routing; manual inspection required")
        else:
            git("merge-base", "--is-ancestor", rev, BASE)
    require(heads.get("coordination/bootstrap"), "Missing public integration head")
    return heads


def directory_inventory():
    # Top-level packet directories only. Do not list entries of any dataset or archive.
    trees = {p: lines("ls-tree", "-d", "--name-only", BASE + ":" + p)
             for p in ["docs/fixtures", "docs/research", "docs/evidence", "docs/evaluation"]}
    require(trees["docs/fixtures"] == ["WP-0022","WP-0024","WP-0026","WP-0028"], "Unexpected fixture packet")
    scratch = sorted(p.name for p in SPEED.iterdir() if p.is_dir())
    require(set(scratch) == SCRATCH_DIRECTORIES, "Changed product scratch roots; reassess public support")
    return {"revision": BASE, "public_tree_children": trees, "scratch_directory_names_only": scratch}


def historical_records():
    records = []
    for number, (reason, fields) in EXCLUSIONS.items():
        raw, row = public_blob(BASE, f"docs/coordination/WP-{number:04}/decision.json")
        data = json.loads(raw)
        observed = {}
        for field, expected in fields.items():
            value = data
            for key in field.split("."):
                value = value[key]
            require(type(value) is type(expected) and value == expected, f"Check exclusion WP-{number:04} {field}")
            observed[field] = value
        row.update(excluded_because=reason, public_fields=observed)
        records.append(row)
    for n, (branch, witness) in PUBLIC_CUSTODY.items():
        path = f"docs/agent-reports/eld-twin-custodian/WP-{n:04}/001_2026-11-21_research_eld-twin-custodian.md"
        raw, row = public_blob(RELATED_TIPS[branch], path)
        require(witness.encode("utf-8") in raw and lines("rev-parse", BASE + ":" + path)[0] == row["git_blob"],
                f"Public custody statement discrepancy WP-{n:04}")
        records.append({**row, "public_provenance_statement": witness, "same_blob_at_base": True})
    raw, row = public_blob(BASE, "CURRENT.md")
    require(ROUTING_PROVENANCE.encode() in raw, "Missing WP-0027 calibration provenance")
    records.append({**row, "WP-0027_scope_witness": ROUTING_PROVENANCE})
    return records


def main():
    require(sys.flags.isolated and sys.dont_write_bytecode, "Use -I -B")
    require(lines("branch","--show-current") == ["review/wp-0034-admission"], "Wrong branch")
    require(lines("remote","get-url","origin") == [ORIGIN] and not lines("status","--porcelain"), "Origin or worktree changed")
    head = lines("rev-parse","HEAD")[0]
    git("merge-base","--is-ancestor",RESERVATION,head)
    contract, binding = public_blob(RESERVATION, "docs/coordination/WP-0034/contract.json")
    terms = json.loads(contract)
    require(terms["public_base"] == BASE and terms["horizons"] == [12,30] and terms["members_per_pair"] == 2
            and terms["required_pairs_per_horizon"] == SCHEDULE and len(terms["arms"]) == 3, "Schedule mismatch")
    refs = inventory_refs()
    directories = directory_inventory()
    records = historical_records()
    # All public candidate sources selected in the frozen review have now passed their exclusion checks.
    # No approved receipt supports an opaque pair in any stratum. Unknown or changed sources abort above.
    strata = []
    for horizon in terms["horizons"]:
        for stratum, pairs in SCHEDULE.items():
            strata.append({"pages": horizon, "stratum": stratum, "planned_pairs": pairs, "supported_pairs": 0,
                           "missing_pairs": pairs, "planned_binders": 2*pairs, "supported_binders": 0,
                           "missing_binders": 2*pairs, "unavailable_terminal_slots_per_arm": 2*pairs})
    binders = sum(row["missing_binders"] for row in strata)
    total_slots = binders * len(terms["arms"])
    require(binders == 32 and total_slots == terms["planned_decisions_per_implementation"], "Slot mismatch")
    result = {
        "packet": "WP-0034", "owner": "eld-rd-reviewer", "independent_candidate": head,
        "observed_utc": datetime.now(timezone.utc).isoformat(), "public_base": BASE, "contract": binding,
        "runtime": {"python": sys.version, "executable_sha256": digest(Path(sys.executable).read_bytes()), "git": lines("--version")[0]},
        "public_remote_heads": refs, "directory_observations": directories, "historical_evidence": records,
        "scope": "Receipt-supported availability in the named public product inventory and contemporaneous public refs. No inference about inaccessible or off-repository holdings.",
        "required_unattested": terms["required_public_attestations"], "strata": strata,
        "per_implementation": {"independent_families_required": 16, "confirmed_families": 0, "answerable_binders_planned": 24,
                               "safety_binders_planned": 8, "arms": {a: {"scheduled_terminal_slots": binders, "unavailable": binders,
                               "C": None, "W": None, "A": None, "correct_posting_coverage": None, "safety": None}
                               for a in terms["arms"]}, "scheduled_terminal_slots": total_slots, "unavailable": total_slots,
                               "answerable_rank_denominator_pairs": 12, "rank_result": None, "scores": None},
        "decision": "admission_blocked_missing_receipts", "technical_reason": "No qualifying, authorized fresh pair with complete source, pairing, per-window frozen captures and sealed truth attestation."
    }
    with OUT.open("xb") as f:
        f.write((json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(f"{head} {len(refs)} public heads; {len(strata)} strata; {total_slots} unavailable; sha256 {digest(OUT.read_bytes())}")


if __name__ == "__main__":
    main()
