"""Builds complete machine-readable inventory for WP-0012 / 006 bounded helper correction (eld-f4-implementer)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess

def resolve_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in (cur, *cur.parents):
        if (cand / "ELedgerCare.slnx").is_file() and (cand / "workers" / "local_ocr" / "run_worker.py").is_file():
            return cand
    raise RuntimeError(f"Could not locate eLedgerCare repository root above {start}")


SCRIPT_PATH = Path(__file__).resolve()
CORRECTION_DIR = SCRIPT_PATH.parent.parent
AUTHOR_WP0012_DIR = CORRECTION_DIR.parent
REPO_ROOT = resolve_repo_root(SCRIPT_PATH.parent)

ACCEPTED_PACKET_BASE_SHA = "73c8d3c4f0a00312e3444328331b6cbd6406e882"
ACCEPTED_F4_FINAL_SOURCE_SHA = "c1fed68020ae67e8b4763bc6ea5473adaa86de2b"
INITIAL_DISPATCH_AUTHORITY_SHA = "47fbc7612e4a08cf1960ad7ac01bd2843ae645e5"
CORRECTION_006_DISPATCH_AUTHORITY_SHA = "598b9e80c317a9fe3d8288732fc19d3a05219cbc"
PRIOR_AUTHOR_001_DELIVERABLE_SHA = "ad5202a029a7a86bea5fa3e3d97760d0a9cc673a"
PRIOR_AUTHOR_001_EVIDENCE_SHA = "32465da577237827c3ac9d8ed5ee608c8e5668cf"
PRIOR_AUTHOR_001_PUBLICATION_SHA = "165b2421b297bf49181c91af8d05a449ad69e9b5"
PRIOR_REVIEWER_002_PUBLICATION_SHA = "379d8c5d607fd248d7f272e412b4ed4a97bc64f6"
CORRECTION_006_BASE_SHA = PRIOR_REVIEWER_002_PUBLICATION_SHA

MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#?\s]+)(?:#[^)\s]*)?\)")


def git_out(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=str(REPO_ROOT), text=True, encoding="utf-8").strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def main() -> None:
    deliverable_sha = git_out(["rev-parse", "HEAD"])
    diff_lines = [
        ln
        for ln in git_out(["diff", "--name-status", CORRECTION_006_BASE_SHA, deliverable_sha]).splitlines()
        if ln.strip()
    ]
    deliverable_entries = []
    for ln in diff_lines:
        action, rel = ln.split("\t", 1)
        if not rel.startswith("docs/implementation/WP-0012/eld-f4-implementer/correction-006/"):
            raise RuntimeError(f"Unexpected path outside correction-006 namespace: {action} {rel}")
        if action != "A":
            raise RuntimeError(f"Expected only added paths in correction-006 deliverable diff, got: {action} {rel}")
        full = REPO_ROOT / rel
        raw = full.read_bytes()
        deliverable_entries.append(
            {
                "action": action,
                "path": rel,
                "bytes": len(raw),
                "sha256": sha256_bytes(raw),
                "sha256_lf": sha256_bytes(raw.replace(b"\r\n", b"\n")),
                "git_blob_oid": git_out(["rev-parse", f"{deliverable_sha}:{rel}"]),
            }
        )

    mutated_prior = [
        ln
        for ln in git_out(["diff", "--diff-filter=MD", "--name-only", CORRECTION_006_BASE_SHA, deliverable_sha]).splitlines()
        if ln.strip()
    ]
    if mutated_prior:
        raise RuntimeError(f"Protected base/001/002 paths modified or deleted: {mutated_prior}")

    preserved_006_base_count = len(
        [ln for ln in git_out(["ls-tree", "-r", "--name-only", CORRECTION_006_BASE_SHA]).splitlines() if ln.strip()]
    )
    preserved_authority_count = len(
        [ln for ln in git_out(["ls-tree", "-r", "--name-only", INITIAL_DISPATCH_AUTHORITY_SHA]).splitlines() if ln.strip()]
    )

    evidence_entries = []
    for f in sorted((CORRECTION_DIR / "evidence").rglob("*")):
        if f.is_file():
            raw = f.read_bytes()
            evidence_entries.append(
                {
                    "path": f.relative_to(REPO_ROOT).as_posix(),
                    "bytes": len(raw),
                    "sha256": sha256_bytes(raw),
                    "sha256_lf": sha256_bytes(raw.replace(b"\r\n", b"\n")),
                }
            )

    rr = CORRECTION_DIR / "resource-return.json"
    rr_raw = rr.read_bytes()
    post_freeze_entries = [
        {
            "path": rr.relative_to(REPO_ROOT).as_posix(),
            "bytes": len(rr_raw),
            "sha256": sha256_bytes(rr_raw),
            "sha256_lf": sha256_bytes(rr_raw.replace(b"\r\n", b"\n")),
        },
        *evidence_entries,
    ]

    # Verify links & zero secrets across all correction-006 artifacts
    settings = json.loads((REPO_ROOT / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
    secrets = [str(settings[k]) for k in ("adminPassword", "migratorPassword", "appPassword") if settings.get(k)]
    verified_links = 0
    for item in CORRECTION_DIR.rglob("*"):
        if not item.is_file():
            continue
        if item.suffix.lower() in (".md", ".json", ".log", ".txt", ".py", ".mjs"):
            txt = item.read_text(encoding="utf-8")
            for s in secrets:
                if s in txt:
                    raise RuntimeError(f"Secret leaked in {item}")
        if item.suffix.lower() == ".md":
            txt = item.read_text(encoding="utf-8")
            for m in MD_LINK_RE.finditer(txt):
                tgt = m.group(1)
                if tgt.startswith(("http://", "https://", "mailto:", "conversation://", "file://")):
                    continue
                if not (item.parent / tgt).resolve().exists():
                    raise RuntimeError(f"Broken relative link in {item}: {tgt}")
                verified_links += 1

    inv = {
        "schema": "eledgercare.wp0012-correction-006-inventory/1",
        "packet": "WP-0012",
        "sequence": "006",
        "author": "eld-f4-implementer",
        "branch": "rehearsal/wp-0012-product",
        "accepted_packet_base_sha": ACCEPTED_PACKET_BASE_SHA,
        "accepted_f4_final_source_sha": ACCEPTED_F4_FINAL_SOURCE_SHA,
        "initial_dispatch_authority_sha": INITIAL_DISPATCH_AUTHORITY_SHA,
        "correction_006_dispatch_authority_inspected_readonly_sha": CORRECTION_006_DISPATCH_AUTHORITY_SHA,
        "preserved_author_001": {
            "deliverable_sha": PRIOR_AUTHOR_001_DELIVERABLE_SHA,
            "evidence_sha": PRIOR_AUTHOR_001_EVIDENCE_SHA,
            "publication_sha": PRIOR_AUTHOR_001_PUBLICATION_SHA,
            "file_count": 24,
            "untouched": True,
        },
        "merged_reviewer_002": {
            "publication_sha": PRIOR_REVIEWER_002_PUBLICATION_SHA,
            "disposition": "changes-requested",
            "file_count": 44,
            "untouched": True,
        },
        "correction_006_base_sha": CORRECTION_006_BASE_SHA,
        "frozen_006_deliverable_sha": deliverable_sha,
        "base_to_deliverable_count": len(deliverable_entries),
        "base_to_deliverable_paths": deliverable_entries,
        "post_freeze_evidence_count_excluding_self_inventory": len(post_freeze_entries),
        "post_freeze_evidence_paths": post_freeze_entries,
        "preserved_006_base_files_verified_unchanged": preserved_006_base_count,
        "preserved_authority_base_files_verified_unchanged": preserved_authority_count,
        "correction_006_markdown_links_verified": verified_links,
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
            "executed_in_006": False,
            "held_for": [
                "Independent WP-0012 / 007 acceptance of corrected /006 preparation by eld-f4-reviewer",
                "Coordinator sole-GPU lease JSON binding exact /006 executing_head, accepting /007 SHA, and observation_files",
            ],
        },
    }

    out = CORRECTION_DIR / "inventory.json"
    out.write_text(json.dumps(inv, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(
        f"Wrote {out.relative_to(REPO_ROOT).as_posix()} "
        f"({len(deliverable_entries)} deliverable paths, {len(post_freeze_entries)} evidence paths, "
        f"{preserved_006_base_count} preserved base/001/002 paths, {verified_links} links OK)."
    )


if __name__ == "__main__":
    main()
