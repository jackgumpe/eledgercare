"""Verify both independent and coordinator inventories, then close the bounded A1 experiment from raw captures."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REVIEW = REPO / "docs/reviews/WP-0017/evidence"
START = "1e75ebe25814227ef6450913bce301ba9e2ef0f2"
SOURCE = "c235bc61820def84142480e6e2a7a2e5485176d6"


def read(path):
    return json.loads(path.read_bytes())


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def main():
    primary = REVIEW / "A1-combined-decision.json"
    independent = read(primary)
    assert checksum(primary.read_bytes()) == "8e99460ed4c00ed50e50bebe94f387c29238446a833aeb1a6873f5af5584ebad"
    own = read(HERE / "a1-p1-carbon-combined.json")
    assert independent["outcome"] == "UNRESOLVED_NO_RESTORATION" and independent["run_sources"] == [SOURCE]
    assert independent["selected_removal"] is None and independent["selected_bits"] is None
    assert independent["frozen_design_rank"] is None and independent["frozen_reviewer_rank"] is None
    assert own["surgical_selection_status"] == "unresolved_halt_at_a1" and own["recommended_surgical_mode"] is None
    reference = read(REVIEW / "A1-combined-blind-inventory.json")
    mirror = read(HERE / "a1-p1-blind-inventory.json")
    ref = {r["run"]: r for r in reference["runs"]}
    copied = {r["run"]: r for r in mirror["runs"]}
    assert ref == copied and len(ref) == 6
    checked_files = 0
    checked_fields = 0
    modes = {}
    fingerprinted = {c["raw_mode"]: c for c in independent["configurations"].values()}
    for run in ref.values():
        folder = Path(run["path"])
        known = dict(run["files"], **run["runtime_cache_files"])
        assert set(known) == {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
        for name, expected in known.items():
            assert checksum((folder / name).read_bytes()) == expected, name
            checked_files += 1
        if folder.name.endswith("-order"):
            continue
        assert read(folder / "launch.json")["source"] == SOURCE
        for segment in folder.glob("segment-*"):
            mode = read(segment / "child.json")["mode"]
            emitted = []
            for page in (21, 37):
                raw = read(segment / "free" / f"raw-{page:03d}.json")
                # Both specified positions are the second source block, a prose inspection ID.
                block = raw["raw_output"].split("<BLOCK>")[2].rstrip("\n")
                match = re.fullmatch(r"text\[[^\]]+\]<FORK>Inspection ([A-Z0-9]+-[A-Z0-9]+)", block)
                assert match and raw["page"] == page and raw["source_sha256"] == "671e8e18d6cf84db671ea0487be8b197e535753dabac6c1561e169654d113c5b"
                emitted.append(match.group(1))
                checked_fields += 1
            assert emitted == fingerprinted[mode]["free_ids"] and mode not in modes
            modes[mode] = emitted
    assert len(modes) == 19 and checked_fields == 38
    pairs = {}
    for pair in independent["eligible_pairs"]:
        name = "remove_" + "_".join(pair)
        reviewer = fingerprinted[name]
        author = own["evaluated_pair_removals"][name]
        assert author["free_ids"] == modes[name] == ["108O1-388", "8OI10-774"]
        assert abs(reviewer["ordinary_seconds"]["sum"] - author["ordinary_two_window_sum_s"]) < 1e-8
        pairs[name] = dict(bits=reviewer["bits"], emitted=modes[name], seconds=reviewer["ordinary_seconds"])
    assert len(pairs) == len(own["evaluated_pair_removals"]) == 3
    receipts = [read(HERE / (name + "-return.json")) for name in ("a1-r1", "a1-p1")]
    orders = [o for receipt in receipts for o in receipt["orders"]]
    children = [p for o in orders for p in o["children"]]
    assert all(r["carrier_exit"] == 0 and r["returned"]["error"] is None for r in receipts)
    assert all(o["exit"] == 0 and o["guard"] is None for o in orders)
    assert len(children) == 19 and all(p["exit"] == 0 and p["observed"] in ("exited", "pid reused") for p in children)
    subprocess.run(["git", "-C", REPO, "diff", "--exit-code", START, "HEAD", "--",
                    "src", "workers", "web", "tests", "qualification", "deploy"], check=True)
    ties = read(HERE / "a1-p1-probe-ties.json")
    assert independent["probe_counts"] == {"passes": ties["probe_passes"], "tied": ties["tied_passes"],
                                           "differing": ties["differing_passes"]}
    result = dict(packet="WP-0017", status="CLOSED_AT_A1_UNRESOLVED_NO_RESTORATION", candidate=SOURCE,
                  weights="0480966938291445591f69f08a13b041c073a96a", integration_base=START,
                  decided_utc=datetime.now(timezone.utc).isoformat(), reviewer_decision_commit="e479b8c8a39bf5703ee084d89527dbe3b872bf8f",
                  reviewer_decision_sha256=checksum(primary.read_bytes()), reviewer_outcome=independent["outcome"],
                  ordinary_native_ids=independent["native_ids"], pairs=pairs, surgical_candidate=None,
                  checks=dict(configurations=19, distinct_mask_count=len({c["bits"] for c in fingerprinted.values()}),
                              inventoried_files_verified=checked_files, anchored_raw_field_reads=checked_fields,
                              reviewer_adapter=independent["adapter_checks"], reviewer_decision=independent["machine_checks"],
                              reviewer_execution=independent["execution"]["checks"], probes=independent["probe_counts"]),
                  gpu=dict(leases=["a1-r1", "a1-p1"], timed_orders=len(orders), trial_worker_processes_exited=len(children),
                           excluded_warmup_windows=57, ordinary_windows=38, peak_sampled_board_mib=max(o["peak_board_mib"] for o in orders),
                           total_supervised_order_s=sum(o["wall_s"] for o in orders), guard_interruptions=0),
                  scope=dict(A2="not released", A3="not released", scoring_keys_released=0, packet_B="sealed",
                             product="ordinary Baidu remains the reviewable reference"),
                  operators=dict(initial="Opus 5.5, native CLI xhigh, initial prefix audit from Antigravity High",
                                 pairs=independent["reviewer_identity"], carrier="coordinator Windows process"),
                  interventions=dict(user="Authorized fresh xhigh reviewer for the three pairs after Opus quota exhaustion.",
                                     human_active_seconds=None),)
    with (HERE / "decision.json").open("x", encoding="utf8", newline="\n") as out:
        json.dump(result, out, indent=2)
        out.write("\n")
    print(result["status"], checked_files, checked_fields, result["gpu"])


if __name__ == "__main__":
    main()
