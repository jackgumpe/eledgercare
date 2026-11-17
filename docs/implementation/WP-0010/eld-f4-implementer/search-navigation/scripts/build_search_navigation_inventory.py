"""Builds complete change, evidence, and preservation inventory for WP-0010 / 006."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess

REPO_ROOT = pathlib.Path(__file__).resolve().parents[6]
SN_DOSSIER_DIR = REPO_ROOT / "docs" / "implementation" / "WP-0010" / "eld-f4-implementer" / "search-navigation"

CONTINUATION_MERGE_BASE_SHA = "4b8e9b8231b9543b9a09cc8514a6876a70940d7b"
DISPATCH_AUTHORITY_SHA = "cd5237303beaa374c3a60e9de58e45808b55435f"
PRIOR_003_PUBLICATION_SHA = "7c578be6e8abff4d285ea1b519bbcfaeba1bb8c7"
PRIOR_003_SOURCE_SHA = "c383021be1774451ba3034d89255b38b4267353b"
PRIOR_003_EVIDENCE_SHA = "ceec957733d6c00c6b4277e7db3f391ab6ccb6b4"
PACKET_BASE_SHA = "956c056be2ec970340074871ecdd7e1a9855d944"
ACCEPTED_DESIGN_SHA = "01a6dab0695c93246b4cf04d1a2098d3b77248d8"


def git_out(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=str(REPO_ROOT), text=True, encoding="utf-8").strip()


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    deliverable_sha = git_out(["rev-parse", "HEAD"])
    diff_lines = [
        ln
        for ln in git_out(["diff", "--name-status", CONTINUATION_MERGE_BASE_SHA, deliverable_sha]).splitlines()
        if ln.strip()
    ]
    base_to_deliverable = []
    for ln in diff_lines:
        action, rel = ln.split("\t", 1)
        full = REPO_ROOT / rel
        blob_oid = git_out(["rev-parse", f"{deliverable_sha}:{rel}"])
        base_to_deliverable.append(
            {
                "action": action,
                "path": rel,
                "bytes": full.stat().st_size,
                "sha256": sha256_file(full),
                "git_blob_oid": blob_oid,
            }
        )

    evidence_files = []
    for f in sorted((SN_DOSSIER_DIR / "evidence").rglob("*")):
        if f.is_file():
            rel = f.relative_to(REPO_ROOT).as_posix()
            evidence_files.append(
                {
                    "path": rel,
                    "bytes": f.stat().st_size,
                    "sha256": sha256_file(f),
                }
            )

    rr = SN_DOSSIER_DIR / "resource-return.json"
    post_freeze_additions = [
        {
            "path": rr.relative_to(REPO_ROOT).as_posix(),
            "bytes": rr.stat().st_size,
            "sha256": sha256_file(rr),
        },
        *evidence_files,
    ]

    # Verify every prior /003 + preparation file in docs/implementation/WP-0010/eld-f4-implementer (outside search-navigation/) is untouched
    prior_dossier_diff = git_out(
        [
            "diff",
            "--name-only",
            CONTINUATION_MERGE_BASE_SHA,
            deliverable_sha,
            "--",
            "docs/implementation/WP-0010/eld-f4-implementer",
            ":(exclude)docs/implementation/WP-0010/eld-f4-implementer/search-navigation",
        ]
    )
    if prior_dossier_diff:
        raise RuntimeError(f"Prior /003 dossier mutated: {prior_dossier_diff}")

    prior_dossier_files_count = len(
        [
            ln
            for ln in git_out(
                [
                    "ls-tree",
                    "-r",
                    "--name-only",
                    deliverable_sha,
                    "--",
                    "docs/implementation/WP-0010/eld-f4-implementer",
                ]
            ).splitlines()
            if ln.strip() and not ln.startswith("docs/implementation/WP-0010/eld-f4-implementer/search-navigation/")
        ]
    )

    inventory = {
        "packet": "WP-0010",
        "sequence": "006",
        "author": "eld-f4-implementer",
        "branch": "feature/wp-0010-f4-archive",
        "packet_base_sha": PACKET_BASE_SHA,
        "accepted_design_sha": ACCEPTED_DESIGN_SHA,
        "prior_003_source_sha": PRIOR_003_SOURCE_SHA,
        "prior_003_evidence_sha": PRIOR_003_EVIDENCE_SHA,
        "prior_003_publication_sha": PRIOR_003_PUBLICATION_SHA,
        "dispatch_authority_sha": DISPATCH_AUTHORITY_SHA,
        "continuation_merge_base_sha": CONTINUATION_MERGE_BASE_SHA,
        "frozen_006_deliverable_sha": deliverable_sha,
        "base_to_deliverable_count": len(base_to_deliverable),
        "base_to_deliverable_paths": base_to_deliverable,
        "post_freeze_evidence_count_excluding_self_inventory": len(post_freeze_additions),
        "post_freeze_evidence_paths": post_freeze_additions,
        "preserved_trees_identical_to_c383021b": {
            "src": git_out(["rev-parse", f"{deliverable_sha}:src"]),
            "tests": git_out(["rev-parse", f"{deliverable_sha}:tests"]),
            "deploy": git_out(["rev-parse", f"{deliverable_sha}:deploy"]),
            "workers/local_ocr": git_out(["rev-parse", f"{deliverable_sha}:workers/local_ocr"]),
            "ELedgerCare.slnx": git_out(["rev-parse", f"{deliverable_sha}:ELedgerCare.slnx"]),
            "web/package.json": git_out(["rev-parse", f"{deliverable_sha}:web/package.json"]),
            "web/package-lock.json": git_out(["rev-parse", f"{deliverable_sha}:web/package-lock.json"]),
        },
        "updated_web_tree": git_out(["rev-parse", f"{deliverable_sha}:web"]),
        "prior_003_dossier_and_preparation_files_preserved_unchanged": prior_dossier_files_count,
        "prior_003_canonical_report_preserved_unchanged": {
            "path": "docs/agent-reports/eld-f4-implementer/WP-0010/003_2026-11-17_implementation_eld-f4-implementer.md",
            "git_blob_oid": git_out(
                [
                    "rev-parse",
                    f"{deliverable_sha}:docs/agent-reports/eld-f4-implementer/WP-0010/003_2026-11-17_implementation_eld-f4-implementer.md",
                ]
            ),
        },
        "attributed_inputs": [
            {
                "path": "tests/fixtures/SYN-WO-01-v1-raster300.pdf",
                "sha256": sha256_file(REPO_ROOT / "tests/fixtures/SYN-WO-01-v1-raster300.pdf"),
                "provenance": "Synthetic work-order fixture",
            },
            {
                "path": "tests/fixtures/SYN-MP-01-v0-clean.pdf",
                "sha256": sha256_file(REPO_ROOT / "tests/fixtures/SYN-MP-01-v0-clean.pdf"),
                "provenance": "Synthetic 3-page maintenance packet fixture",
            },
            {
                "path": "tests/fixtures/F1-SWO-001.pdf",
                "sha256": sha256_file(REPO_ROOT / "tests/fixtures/F1-SWO-001.pdf"),
                "provenance": "Synthetic F1 intake fixture",
            },
            {
                "path": "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4/output/raw_output.utf8.bin",
                "sha256": sha256_file(
                    REPO_ROOT
                    / "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4/output/raw_output.utf8.bin"
                ),
                "provenance": "Genuine accepted WP-0006 F2 raw extraction seed (no GPU rerun)",
            },
            {
                "path": "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d/output/raw_output.utf8.bin",
                "sha256": sha256_file(
                    REPO_ROOT
                    / "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d/output/raw_output.utf8.bin"
                ),
                "provenance": "Genuine accepted WP-0006 F2 3-page raw extraction seed (no GPU rerun)",
            },
        ],
    }

    out_path = SN_DOSSIER_DIR / "change-inventory.json"
    out_path.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {out_path.relative_to(REPO_ROOT).as_posix()} ({len(base_to_deliverable)} deliverable entries, {len(post_freeze_additions)} evidence entries).")


if __name__ == "__main__":
    main()
