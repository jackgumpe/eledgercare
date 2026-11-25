"""Verify the frozen public custody metadata without opening a page, prediction or answer key."""

import hashlib
import json
import subprocess
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
BASE = "2a9b44f86151f6976846094259771a14efcdbfcd"
REPO = DIRECTORY.parents[2]


def source(path):
    return subprocess.check_output(["git", "show", BASE + ":" + path], cwd=REPO)


def check(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def main():
    inventory = json.loads((DIRECTORY / "intake.json").read_bytes())
    check(inventory["source_revision"] == BASE, "Reservation changed")
    pins = inventory["public_source_pins"]
    for path, record in pins.items():
        raw = source(path)
        check(len(raw) == record["bytes"], f"Size mismatch for {path}")
        check(hashlib.sha256(raw).hexdigest() == record["sha256"], f"Digest mismatch for {path}")

    counts = inventory["historical_counts"]
    starter = json.loads(source("evaluation/manifests/corpus-manifest.json"))["counts"]
    public = json.loads(source("evaluation/manifests/public-candidates.json"))["candidates"]
    check(all(row["admission_status"] == "candidate_unadmitted" and not row["included_in_repo_bytes"]
              for row in public), "Public admission record changed")
    check(counts["WP-0004"] == {
        "synthetic_families": starter["families"], "synthetic_pdfs": starter["total_pdfs"],
        "synthetic_pages": starter["total_pages"], "external_pdf_candidates": len(public),
        "admitted_external_pdfs": starter["admitted_public_pdfs"],
    }, "Starter corpus differs")

    grant = json.loads(source("docs/coordination/WP-0022/release.json"))
    check(counts["WP-0022"] == {
        "synthetic_documents": grant["documents"], "page_appearances": grant["studyPageAppearances"],
        "unique_rasters_in_per_raster_winrt_grant": grant["uniquePageRasters"],
    }, "WinRT grant differs")

    paths = ["docs/coordination/WP-0036/reconciliation.json",
             "docs/reviews/WP-0036/evidence/summary.json",
             "docs/agent-reports/eld-rd-reviewer/WP-0036/002_2026-11-24_review_eld-rd-reviewer.md"]
    published = json.loads(source("docs/coordination/WP-0036/publication-receipt.json"))
    for path in paths:
        check(pins[path]["sha256"] == published["downloaded_files"][path]["sha256"],
              f"WP-0036 publication mismatch for {path}")
    rows = json.loads(source(paths[0]))["D_per_binder"]
    summary = json.loads(source(paths[1]))
    independent_report = source(paths[2]).decode()
    check("25 physical capture/span coordinates, 14 distinct block byte strings" in independent_report,
          "Location count missing")
    check("None of the 96 table-block uses supplied an Amount body plus a corresponding in-table "
          "total or an explicit balance series from b0 through bn." in independent_report,
          "Chain audit missing")
    check(len(rows) == len({r["binder"] for r in rows}) == summary["binders"], "Binder duplication")
    check(sum(r["physical_table_uses"] for r in rows) == summary["physical_table_uses"],
          "Table occurrence totals disagree")
    check(sum(r["eligible_archive_stress_cells"] for r in rows) == summary["d_cells"],
          "Stress-cell totals disagree")
    check(counts["WP-0036"] == {
        "exposed_binders": len(rows), "table_block_occurrences": summary["physical_table_uses"],
        "capture_span_locations": 25, "distinct_block_contents": summary["distinct_table_content"],
        "complete_running_balance_chains": 0, "eligible_archive_stress_cells": summary["d_cells"],
    }, "Archive summary differs")

    intake = inventory["physical_intake"]
    check(intake["frozen_order"] == intake["admitted_family_list"] == [], "Unexpected family")
    encoded_order = (json.dumps(intake["frozen_order"], separators=(",", ":")) + "\n").encode("utf-8")
    check(hashlib.sha256(encoded_order).hexdigest() == intake["empty_order_sha256"],
          "Empty order digest differs")
    check(all(value == 0 for value in intake.values() if type(value) is int),
          "A nonzero physical count needs supporting custody evidence")
    check(all(intake[k] is None for k in (
        "private_truth_manifest_sha256", "private_reference_box_manifest_sha256", "first_pass_manifest_sha256",
        "reader_operator_release", "selected_reader_config", "device_lease")), "Unbound artifact claimed")
    physical = inventory["physical_accounting"]
    check(all(value == 0 for value in physical.values() if type(value) is int), "Physical work claimed")
    check(all(physical[k] is None for k in ("correctness_rate", "wall_ms", "pixel_cost")),
          "Physical measurement claimed")
    cap = inventory["prospective_cap"]
    families = cap["families"]
    per_page = cap["max_mutable_cells_per_ambiguous_page"] + cap["single_table_views_per_ambiguous_page"]
    check(families == cap["first_passes_max"] == 24 and families * per_page == cap["distinct_additional_views_max"] == 216,
          "View budget differs")
    check(cap["total_views_max"] == families * (1 + per_page) == 240, "Total budget differs")
    print(f"{len(pins)} public source digests verified; WP-0036: 24 binders, 96 table occurrences, "
          "14 distinct contents, 0 complete chains. Empty family order and 24+216 ceiling verified.")


if __name__ == "__main__":
    main()
