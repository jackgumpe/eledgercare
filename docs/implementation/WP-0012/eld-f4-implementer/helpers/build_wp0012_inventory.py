"""Builds complete machine-readable preparation inventory for WP-0012 / 001 (eld-f4-implementer)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[5]
DOSSIER_DIR = REPO_ROOT / "docs" / "implementation" / "WP-0012" / "eld-f4-implementer"

DISPATCH_AUTHORITY_SHA = "47fbc7612e4a08cf1960ad7ac01bd2843ae645e5"
ACCEPTED_PACKET_BASE_SHA = "73c8d3c4f0a00312e3444328331b6cbd6406e882"
ACCEPTED_F4_FINAL_SOURCE_SHA = "c1fed68020ae67e8b4763bc6ea5473adaa86de2b"


def git_out(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=str(REPO_ROOT), text=True, encoding="utf-8").strip()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    deliverable_sha = git_out(["rev-parse", "HEAD"])
    diff_lines = [
        ln
        for ln in git_out(["diff", "--name-status", DISPATCH_AUTHORITY_SHA, deliverable_sha]).splitlines()
        if ln.strip()
    ]
    deliverable_entries = []
    for ln in diff_lines:
        action, rel = ln.split("\t", 1)
        full = REPO_ROOT / rel
        deliverable_entries.append(
            {
                "action": action,
                "path": rel,
                "bytes": full.stat().st_size,
                "sha256": sha256_file(full),
                "git_blob_oid": git_out(["rev-parse", f"{deliverable_sha}:{rel}"]),
            }
        )

    evidence_entries = []
    for f in sorted((DOSSIER_DIR / "evidence").rglob("*")):
        if f.is_file():
            rel = f.relative_to(REPO_ROOT).as_posix()
            evidence_entries.append({"path": rel, "bytes": f.stat().st_size, "sha256": sha256_file(f)})

    rr = DOSSIER_DIR / "resource-return.json"
    post_freeze_entries = [
        {"path": rr.relative_to(REPO_ROOT).as_posix(), "bytes": rr.stat().st_size, "sha256": sha256_file(rr)},
        *evidence_entries,
    ]

    preserved_base_file_count = len(
        [
            ln
            for ln in git_out(["ls-tree", "-r", "--name-only", DISPATCH_AUTHORITY_SHA]).splitlines()
            if ln.strip()
        ]
    )
    prior_mutated = [
        ln
        for ln in git_out(["diff", "--name-only", DISPATCH_AUTHORITY_SHA, deliverable_sha]).splitlines()
        if ln.strip() and not ln.startswith("docs/implementation/WP-0012/eld-f4-implementer/")
    ]
    if prior_mutated:
        raise RuntimeError(f"Protected repository paths mutated: {prior_mutated}")

    inv = {
        "schema": "eledgercare.wp0012-preparation-inventory/1",
        "packet": "WP-0012",
        "sequence": "001",
        "author": "eld-f4-implementer",
        "branch": "rehearsal/wp-0012-product",
        "accepted_packet_base_sha": ACCEPTED_PACKET_BASE_SHA,
        "accepted_f4_final_source_sha": ACCEPTED_F4_FINAL_SOURCE_SHA,
        "dispatch_authority_sha": DISPATCH_AUTHORITY_SHA,
        "frozen_001_deliverable_sha": deliverable_sha,
        "base_to_deliverable_count": len(deliverable_entries),
        "base_to_deliverable_paths": deliverable_entries,
        "post_freeze_evidence_count_excluding_self_inventory": len(post_freeze_entries),
        "post_freeze_evidence_paths": post_freeze_entries,
        "preserved_base_files_verified_unchanged": preserved_base_file_count,
        "unchanged_product_and_worker_trees": {
            "src": git_out(["rev-parse", f"{deliverable_sha}:src"]),
            "web": git_out(["rev-parse", f"{deliverable_sha}:web"]),
            "tests": git_out(["rev-parse", f"{deliverable_sha}:tests"]),
            "deploy": git_out(["rev-parse", f"{deliverable_sha}:deploy"]),
            "workers/local_ocr": git_out(["rev-parse", f"{deliverable_sha}:workers/local_ocr"]),
            "ELedgerCare.slnx": git_out(["rev-parse", f"{deliverable_sha}:ELedgerCare.slnx"]),
        },
        "rehearsal_fixture_inputs": [
            {
                "path": "tests/fixtures/SYN-WO-01-v1-raster300.pdf",
                "bytes": (REPO_ROOT / "tests/fixtures/SYN-WO-01-v1-raster300.pdf").stat().st_size,
                "sha256": sha256_file(REPO_ROOT / "tests/fixtures/SYN-WO-01-v1-raster300.pdf"),
                "pages": 1,
            },
            {
                "path": "tests/fixtures/SYN-MP-01-v0-clean.pdf",
                "bytes": (REPO_ROOT / "tests/fixtures/SYN-MP-01-v0-clean.pdf").stat().st_size,
                "sha256": sha256_file(REPO_ROOT / "tests/fixtures/SYN-MP-01-v0-clean.pdf"),
                "pages": 3,
            },
        ],
        "readonly_external_q0_bindings": {
            "root": r"C:\Users\jackg\eLedgerCare-Q0\WP-0005",
            "model_manifest_sha256": sha256_file(REPO_ROOT / "workers/local_ocr/manifests/model-files.json"),
            "dependency_lock_sha256": sha256_file(REPO_ROOT / "workers/local_ocr/manifests/dependency-lock.json"),
        },
        "live_rehearsal_status": {
            "executed_in_001": False,
            "held_for": [
                "Independent WP-0012 / 002 preparation acceptance by eld-f4-reviewer",
                "Coordinator creation/release of C:\\Users\\jackg\\eLedgerCare-Demo\\WP-0012\\author and sole GPU lease",
            ],
        },
    }

    out = DOSSIER_DIR / "inventory.json"
    out.write_text(json.dumps(inv, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(
        f"Wrote {out.relative_to(REPO_ROOT).as_posix()} "
        f"({len(deliverable_entries)} deliverable paths, {len(post_freeze_entries)} evidence paths, {preserved_base_file_count} preserved base paths)."
    )


if __name__ == "__main__":
    main()
