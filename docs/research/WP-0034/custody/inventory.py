"""Inventory public admission receipts without opening specimens or sensor archives."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

BASE = "ffec32d08f4137bea6d01505b1677b64cccbf5bc"
RESERVATION = "604a3a051d901ec8a1a8f7d6407ef57d99b19c10"
ROUTING = "318463589b32db69076da14c0f48b00aca071edd"
CONTRACT = "docs/coordination/WP-0034/contract.json"
REPO = "https://github.com/jackgumpe/eledgercare.git"
PRODUCT = Path("C:/Users/jackg/eLedgerCare-Speed")
PACKET = PRODUCT / "WP-0034"

# Every blob lookup uses a literal public path at one of the two fixed commits.
# Mixed coordinator decisions are projected immediately to individually named scalars.
RECEIPTS = {
    "WP-0024/decision": [
        "real_b1_calls", "exact_pairs", "total_pairs", "page_appearances",
    ],
    "WP-0025/decision": ["scope"],
    "WP-0026/blind-custody-release": [
        "blind_pairs", "blind_binders", "horizons", "gpu_calls_this_release",
    ],
    "WP-0026/decision": [
        "development.exact_h0_pairs", "development.train_uncached_calls",
        "development.train_c1_exact_duplicate_groups", "blind.bound_pairs",
        "blind.bound_binders", "blind.started", "blind.verified_feature_returns",
        "blind.completed_12_page_pairs", "blind.completed_30_page_pairs",
        "blind.remaining_unverified_duplicates", "blind.uncached_not_started",
        "blind.residual_feature_calls_started", "blind.scoring_key_release",
    ],
    "WP-0028/decision": [
        "scope", "study.document_pairs_planned", "admission.planned_distinct_window_inputs",
        "admission.cached_distinct_window_inputs", "admission.missing_distinct_window_inputs",
    ],
    "WP-0029/decision": [
        "scope", "acquisition.excluded_warmups", "acquisition.cedar_calls",
        "acquisition.total_native_calls",
    ],
    "WP-0030/decision": ["scope"],
    "WP-0032/decision": ["scope"],
    "WP-0033/decision": ["boundary"],
}
HISTORICAL_LIMITS = {
    "WP-0022–0023": "Prior WinRT ledger and batch-size studies lack a release for this cohort.",
    "WP-0024–0027 development": "Known warm-up, training, calibration or diagnostic inputs lack independent fresh-family custody for this trial.",
    "WP-0026 blind": "A different sealed cohort had its own release and partial acquisition. Its release does not authorize reuse or an opening here.",
    "WP-0028–0033": "Repeated known development openings, including Alder/Cedar across two lengths, were exposed during selection of the gain.",
}


def git(*args):
    return subprocess.check_output(["git", *args])


def digest(data):
    return hashlib.sha256(data).hexdigest()


def blob(revision, path):
    return git("cat-file", "blob", f"{revision}:{path}")


def tree(revision, path=""):
    # One level only. Callers specify only public structural directories.
    obj = f"{revision}:{path}" if path else revision
    entries = {}
    for row in git("ls-tree", "-z", obj).decode("utf-8").split("\0"):
        if row:
            meta, name = row.split("\t", 1)
            entries[name] = meta
    return entries


def projection():
    projected = {}
    for key, fields in RECEIPTS.items():
        path = "docs/coordination/" + key + ".json"
        data = blob(BASE, path)
        doc = json.loads(data)
        selected = {}
        for field in fields:
            value = doc
            for component in field.split("."):
                value = value[component]
            if field == "horizons":
                if not isinstance(value, list) or not all(type(x) is int for x in value):
                    raise ValueError("Unexpected horizon metadata")
            elif value is not None and type(value) not in {str, int, bool}:
                raise ValueError(f"Unexpected receipt schema at {key}/{field}")
            selected[field] = value
        projected[path] = {"sha256": digest(data), "aggregate_fields": selected}
    return projected


def live_observations():
    advertised = git("ls-remote", "--refs", REPO).decode().splitlines()
    return {
        "public_refs": {ref: sha for sha, ref in (line.split("\t") for line in advertised)},
        "product_top_level_names": sorted(os.listdir(PRODUCT)),
        "packet_top_level_names": sorted(os.listdir(PACKET)),
    }


def inventory(observations):
    policy = json.loads(blob(RESERVATION, CONTRACT))
    ancestors = set(git("rev-list", BASE).decode().splitlines())
    refs = observations["public_refs"]
    if not refs or "refs/heads/coordination/bootstrap" not in refs:
        raise ValueError("Missing public integration advertisement")
    flags = []
    classifications = {}
    for ref, tip in sorted(refs.items()):
        if not re.fullmatch("[0-9a-f]{40}", tip):
            raise ValueError("Invalid public object ID")
        if tip in ancestors:
            category = "at_or_before_public_base"
        elif ref == "refs/heads/coordination/bootstrap" and tip in {RESERVATION, ROUTING}:
            category = "reservation_or_routing_only"
        elif ref in {"refs/heads/research/wp-0034-custody", "refs/heads/review/wp-0034-admission"}:
            category = "assigned_inventory_role_excluded_from_independent_inputs"
        else:
            category = "requires_coordinator_source_identification"
            flags.append("public ref " + ref + " at " + tip)
        classifications[ref] = category

    namespace = {p: sorted(tree(BASE, p)) for p in ("docs/fixtures", "docs/research")}
    for name in namespace["docs/fixtures"]:
        if name not in {"WP-0022", "WP-0024", "WP-0026", "WP-0028"}:
            flags.append("unclassified fixture packet " + name)
    for name in namespace["docs/research"]:
        if not re.fullmatch("WP-00[0-9][0-9]", name) or int(name[-2:]) > 33:
            flags.append("unclassified public research namespace " + name)
    for name in observations["product_top_level_names"]:
        if name == "coordination" or re.fullmatch(r"GPU-[A-Fa-f0-9-]+\.lock", name):
            continue
        if not re.fullmatch("WP-00[0-9][0-9]", name) or int(name[-2:]) > 34:
            flags.append("unclassified product inventory name " + name)
    for name in observations["packet_top_level_names"]:
        if name not in {"author", "review", "custody", "coordination"}:
            flags.append("unclassified packet inventory name " + name)

    result = {
        "packet": policy["packet"], "accepted_base": BASE, "reservation": RESERVATION,
        "repository": REPO, "approved_routing": ROUTING, "namespace_at_base": namespace,
        "ref_classifications": classifications,
        "immutable_historical_projections": projection(),
        "historical_exclusions": HISTORICAL_LIMITS,
        "source_candidates_requiring_separate_identification": flags,
        "required_admission_records": policy["required_public_attestations"],
        "observation_scope": "Public receipt registry and origin ref advertisement, public fixture/research packet names, direct product and packet names only. Historical packet directories, private or sealed data, and unregistered external holdings were not searched for payloads.",
    }
    if flags:
        result["status"] = "additional_source_identification_required_before_disposition"
        return result

    # None of the registered receipt classes has a WP-0034 fresh-family release.
    # The reservation authorizes a conditional inventory; it supplies no specimens.
    result["status"] = "unavailable_within_observed_authorized_perimeter"
    result["missing_prerequisites"] = [
        "Authorized, previously unexposed family source with source/version and generation or acquisition commitments, new openings and owners, duplicate and independence checks.",
        "Opaque paired inventory with one horizon per family, balance and permutations, new matched opening edits and rendered suffixes, target/ambiguity definitions and safety schedule.",
        "Authenticated existing sensor output through the final window of both members, including ordered receipt, token/span map, pooled representation and box bindings.",
        "Independent truth commitment with protected family/binder/target join, unavailable to both operators until predictions freeze.",
    ]
    result["schedule"] = []
    for horizon in policy["horizons"]:
        for stratum, pairs in policy["required_pairs_per_horizon"].items():
            binders = pairs * policy["members_per_pair"]
            result["schedule"].append({
                "pages": horizon, "stratum": stratum, "planned_pairs": pairs,
                "planned_binders": binders, "receipt_confirmed_pairs": 0,
                "receipt_confirmed_binders": 0, "pairs_missing_evidence": pairs,
                "binders_missing_evidence": binders,
                "unavailable_terminal_slots_per_arm": binders,
            })
    binders = sum(row["planned_binders"] for row in result["schedule"])
    answerable = sum(r["planned_binders"] for r in result["schedule"] if r["stratum"].endswith("_answerable"))
    result["per_implementation"] = {
        "families_planned": policy["independent_families"], "binders_planned": binders,
        "answerable_pairs_planned": answerable // 2, "answerable_binders_planned": answerable,
        "safety_binders_planned": binders - answerable, "terminal_slots_planned": binders * len(policy["arms"]),
        "terminal_decisions_executed": 0, "unavailable_terminal_slots": binders * len(policy["arms"]),
        "arms": {arm: {
            "planned_terminal_slots": binders, "executed": 0, "unavailable": binders,
            "correct_postings": None, "wrong_postings": None, "abstentions": None,
            "rank_successes": None, "correct_posting_coverage": None, "safety_outcomes": None,
            "safety_gate": None, "paired_changes": None,
        } for arm in policy["arms"]},
    }
    if result["per_implementation"]["terminal_slots_planned"] != policy["planned_decisions_per_implementation"]:
        raise ValueError("Schedule disagrees with the reservation")
    result["next_gate"] = "Independent inventory verification and coordinator disposition. Substitution, new sensor acquisition and opening a different sealed cohort have no release."
    return result


def write_new(directory, name, obj):
    with (directory / name).open("x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--replay-observations", type=Path,
                        help="Re-read the pinned Git evidence using a published public metadata snapshot")
    args = parser.parse_args()
    directory = args.output_directory
    if directory.exists():
        raise FileExistsError("Select a new output directory")
    if args.replay_observations:
        obs = json.loads(args.replay_observations.read_bytes())
    else:
        obs = live_observations()
    result = inventory(obs)
    directory.mkdir(parents=True)
    write_new(directory, "public-observations.json", obs)
    write_new(directory, "inventory.json", result)
    print(result["status"])
    return int(bool(result["source_candidates_requiring_separate_identification"]))


if __name__ == "__main__":
    raise SystemExit(main())
