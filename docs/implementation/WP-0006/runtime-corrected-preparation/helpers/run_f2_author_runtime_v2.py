"""Versioned Stage 2 finite real local OCR runtime acceptance driver v2 (eld-f2-implementer, WP-0006).

Prepared under coordinator authority 35e2f44d788a99ad1b2d10d1af95536cf1d1981a for corrected
product source 8a73b7a5dab51e3ccf803aceedded4929529dd35, preserving the original Stage 2 helper
(docs/implementation/WP-0006/runtime-author/helpers/run_f2_author_runtime.py) and all initial
pre-model failed-trial artifacts unchanged.

Key v2 design & safety properties:
  - Consumes an explicitly supplied future coordinator release commit and Git-relative release JSON path
    (--release-commit <sha> --release-path <git-path>); never hardcodes a future executing HEAD or lease,
    and explicitly rejects historical/returned/preparation commits and leases.
  - Validates clean executing HEAD, Git ancestry from frozen product source 8a73b7a5dab51e3ccf803aceedded4929529dd35
    (without assuming HEAD~1 == source_commit), exact product & protected Git tree OIDs, accepted /002 design
    review and independent source-reconciliation review bindings, updated worker_source_sha256
    (c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54), unchanged manifest/lock/config/fixture
    digests, active non-expired GPU lease, owned ports (5190/4210/55434), scoped roots, and pre-lease observation blobs.
  - Versions fresh scratch (.scratch/stage2-runtime-v2) and PostgreSQL database (eledgercare_f2_runtime_author_v2)
    paths so initial failed-trial artifacts cannot be overwritten, and snapshots/protects any retained prior run
    directory (attempt-01a1e316-879e-737e-b222-cf9ebea58b09) while accounting for the <= 4 new model attempts separately.
  - Supports pure CPU/Git --dry-run-validate mode (zero ML/CUDA imports, zero nvidia-smi queries, zero external
    root accesses, zero database/service starts).
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
from typing import Callable
import urllib.error
import urllib.request
import uuid


def resolve_repo_root(start: Path) -> Path:
    cur = start.resolve()
    if cur.is_file():
        cur = cur.parent
    for cand in (cur, *cur.parents):
        if (cand / "ELedgerCare.slnx").is_file() and (cand / "workers" / "local_ocr" / "run_worker.py").is_file():
            return cand
    raise RuntimeError(f"Could not locate eLedgerCare repository root above {start}")


SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
ROOT = resolve_repo_root(SCRIPT_DIR)
UI_HELPER_PATH = SCRIPT_DIR / "verify_ui_real_results_v2.mjs"

if str(ROOT / "workers" / "local_ocr") not in sys.path:
    sys.path.insert(0, str(ROOT / "workers" / "local_ocr"))

from local_ocr.env_guard import directory_size_bytes, is_inside  # noqa: E402
from local_ocr.protocol import (  # noqa: E402
    DEPENDENCY_LOCK_PATH,
    MODEL_MANIFEST_PATH,
    MODEL_REPO_ID,
    MODEL_REVISION,
    compute_config_digest,
    compute_worker_source_sha256,
    sha256_bytes,
)
from local_ocr.verify_runtime import (  # noqa: E402
    is_reparse_or_link,
    load_json_checked,
    normalize_and_verify_model_dir,
    verify_model_sources_ast_safety,
)

HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

EXPECTED_OWNER = "eld-f2-implementer"
EXPECTED_CONVERSATION_ID = "2b6861af-031b-4e8b-9ce9-2a6d476f9da0"
EXPECTED_MODEL = "gemini-4-carbon-high"
EXPECTED_EFFORT = "high"
EXPECTED_GPU_UUID = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"

EXPECTED_SOURCE_COMMIT = "8a73b7a5dab51e3ccf803aceedded4929529dd35"
EXPECTED_SOURCE_RESPONSE_CHECKPOINT = "386d5c30809c3c04d6640d9433eb4263306ac126"
EXPECTED_ACCEPTED_DESIGN_REVIEW = "e2452e1ab3d8937868c07ffb30ce430715b5be78"

REJECTED_AUTHORITY_COMMITS = frozenset({
    "d106db76de6dc8d9b52770d405ca95300b6dacd6",  # Stage 1 CPU implementation release
    "717a768994bbbabf75b8ee96b3b1aadca1bc5df3",  # Initial runtime release (lease returned/acknowledged)
    "2c54927463b46a96a9b0c0c5d1012636fb4f961e",  # Consolidated CPU source-response release
    "2ce3366d6aada92068088090bb026d4579b20e61",  # B0 heldout + reviewer reconciliation release
    "35e2f44d788a99ad1b2d10d1af95536cf1d1981a",  # CPU-only v2 driver preparation release
})

REJECTED_LEASE_IDS = frozenset({
    "WP-0006-author-runtime-20261116T062318Z",
})

REJECTED_EXECUTING_HEADS = frozenset({
    "0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978",
    "6faec9bf6eccc297a548523dbb52ae9262b25152",
    "7280463accdf0ff9fb3a218299193eeff2ec9c9e",
    "850d20063f09f0564a1008da20f09ff185fd0dfb",
    "8a73b7a5dab51e3ccf803aceedded4929529dd35",
    "386d5c30809c3c04d6640d9433eb4263306ac126",
})

REJECTED_SOURCE_REVIEWS = frozenset({
    "10193e2c904f99cfc23c97367f1e5d881b0630f2",  # Pre-reconciliation Stage 1 findings checkpoint
    "e2452e1ab3d8937868c07ffb30ce430715b5be78",  # Design-only /002 review
})

EXPECTED_PRODUCT_TREES: dict[str, str] = {
    "src": "73d0146b3624ab4928a4d2cda7806d7d6166906e",
    "workers/local_ocr": "1ed609368ca4c6bff8b92231362be2d802ae8baf",
    "workers/ocr": "493935fad8163ec9242b396232a55564446a52e6",
    "web": "f0877a006922818bf731d5f87603a368ed782487",
    "tests": "5ad9bd15f41ab24bd5851ca02bfa0d8054dc1453",
    "deploy": "dade6a38e165b5cc2ba81ba895bd9d3c572d26f2",
}

EXPECTED_PROTECTED_TREES: dict[str, str] = {
    "qualification": "b5918e65cb20b45cad83506b80d8a8bc611807ec",
    "research": "5036d17e55f96af3bdeea82a20a32eb54a26ddca",
    "evaluation": "60fcc7fa1741b6c44489bb9cf8484e03a4cbf019",
    "docs/implementation/WP-0006/stage1-checkpoint": "4acac7f102826f445687693190a34098d640bb6c",
    "docs/implementation/WP-0006/runtime-author": "72bb71576a88506d486c78d6ce0d3e0b4f66ebf0",
    "docs/implementation/WP-0006/source-response": "352d356920a7cc0b2b6c3c40d63ad246db441822",
}

FORBIDDEN_DIFF_PREFIXES = (
    "src/",
    "workers/",
    "web/",
    "tests/",
    "deploy/",
    "qualification/",
    "research/",
    "evaluation/",
    "docs/implementation/WP-0006/stage1-checkpoint/",
    "docs/implementation/WP-0006/runtime-author/",
    "docs/agent-reports/eld-f2-implementer/",
)

EXPECTED_PINNED_DIGESTS: dict[str, str] = {
    "model_manifest_sha256": "0df07bc60abf6937c917040bced32afabd7e4d11bafc0bd99902abca610a81be",
    "dependency_lock_sha256": "582071bf20eaca1836c3d1cef21d31cbdaa1e1407184033a918a40612c128111",
    "worker_source_sha256": "c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54",
    "worker_config_1p_sha256": "579aad63a9893a58466baf005ea63f87e92540d4c1f71f6b3c399e8b1e6b35ff",
    "worker_config_2p_sha256": "e4df504ddb51dcc8fb137e97f5af97c735252374738b1a1754a88b16a05de5df",
    "worker_config_3p_sha256": "ac90459ca4011b5859cfdd0b224d5ea247489b7c01775118736df7c1c9819e86",
    "f1_swo_001_sha256": "875a2d8c83c1c1002b38840f8136b60bd5ebcfe8d2df47187bf36454c59497cb",
    "syn_wo_01_sha256": "47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd",
    "syn_mp_01_sha256": "15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3",
}

EXPECTED_PORTS = {"api": 5190, "ui": 4210, "postgres": 55434}
EXPECTED_Q0_ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")
ALLOWED_F2_RUNTIME_PARENT = Path(r"C:\Users\jackg\eLedgerCare-F2\WP-0006")
DEFAULT_RETAINED_PRIOR_RUN_DIRS = frozenset({"attempt-01a1e316-879e-737e-b222-cf9ebea58b09"})
INITIAL_TRIAL_DATABASE_NAME = "eledgercare_f2_runtime_author"
DEFAULT_V2_DATABASE_NAME = "eledgercare_f2_runtime_author_v2"
EXPECTED_STORAGE_CAP_BYTES = 4 * 1024 * 1024 * 1024
EXPECTED_FREE_FLOOR_BYTES = 20 * 1024 * 1024 * 1024
EXPECTED_MAX_MODEL_ATTEMPTS = 4
MIN_LEASE_REMAINING_SECONDS = 300

HOLDOUT_SUBSTRINGS = ("WO-03", "PM-02", "CAL-02", "MP-02", "F03", "F05", "F06", "F08", "heldout", "holdout")

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_TERMINATE = 0x0001
STILL_ACTIVE = 259


class ReleaseValidationError(RuntimeError):
    """Raised when a coordinator runtime release or local repository state fails fail-closed validation."""


def utc_now_dt() -> datetime:
    return datetime.now(timezone.utc)


def utc_now() -> str:
    return utc_now_dt().isoformat()


def write_json_lf(path: Path, obj: object) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return raw


def parse_utc_iso(ts: str, field_name: str) -> datetime:
    if not isinstance(ts, str) or not ts.strip():
        raise ReleaseValidationError(f"Missing or non-string UTC timestamp in '{field_name}'.")
    normalized = ts.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ReleaseValidationError(f"Invalid ISO-8601 timestamp in '{field_name}': {ts!r}") from exc
    if dt.tzinfo is None:
        raise ReleaseValidationError(f"Timestamp '{field_name}' must be timezone-aware UTC: {ts!r}")
    return dt.astimezone(timezone.utc)


def git_stdout(root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True, encoding="utf-8").strip()


def git_bytes(root: Path, args: list[str]) -> bytes:
    return subprocess.check_output(["git", *args], cwd=root)


def git_object_exists(root: Path, spec: str) -> bool:
    proc = subprocess.run(
        ["git", "cat-file", "-e", spec],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def git_is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def compute_local_worktree_digests(root: Path = ROOT) -> dict[str, str]:
    worker_root = root / "workers" / "local_ocr"
    fixtures_dir = root / "tests" / "fixtures"
    return {
        "model_manifest_sha256": sha256_bytes((worker_root / "manifests" / "model-files.json").read_bytes()),
        "dependency_lock_sha256": sha256_bytes((worker_root / "manifests" / "dependency-lock.json").read_bytes()),
        "worker_source_sha256": compute_worker_source_sha256(worker_root),
        "worker_config_1p_sha256": compute_config_digest(1),
        "worker_config_2p_sha256": compute_config_digest(2),
        "worker_config_3p_sha256": compute_config_digest(3),
        "f1_swo_001_sha256": sha256_bytes((fixtures_dir / "F1-SWO-001.pdf").read_bytes()),
        "syn_wo_01_sha256": sha256_bytes((fixtures_dir / "SYN-WO-01-v1-raster300.pdf").read_bytes()),
        "syn_mp_01_sha256": sha256_bytes((fixtures_dir / "SYN-MP-01-v0-clean.pdf").read_bytes()),
    }


def _extract_source_review_sha(release_doc: dict) -> tuple[str, str]:
    candidate_keys = [
        "accepted_source_review",
        "accepted_source_reconciliation",
        "source_reconciliation_review",
        "source_review_acceptance",
        "accepted_implementation_review",
        "independent_source_review",
        "source_reconciliation",
        "source_review",
    ]
    for k in dir_or_keys(release_doc, candidate_keys):
        val = release_doc.get(k)
        sha = _coerce_sha_value(val)
        if sha is not None:
            return k, sha

    nested = release_doc.get("accepted_reviews")
    if isinstance(nested, dict):
        for nk in ("source", "source_reconciliation", "implementation", "reconciliation"):
            sha = _coerce_sha_value(nested.get(nk))
            if sha is not None:
                return f"accepted_reviews.{nk}", sha

    raise ReleaseValidationError(
        "Missing independent accepted source-review/reconciliation commit binding in coordinator release JSON."
    )


def dir_or_keys(doc: dict, preferred: list[str]) -> list[str]:
    found = [k for k in preferred if k in doc]
    for k in doc:
        if (
            k not in found
            and k not in ("source_commit", "source_response_checkpoint")
            and re.search(r"(reconcil|(source|impl|stage1).*(review|accept|disposition))", k, re.I)
        ):
            found.append(k)
    return found


def _coerce_sha_value(val: object) -> str | None:
    if isinstance(val, str) and val.strip():
        return val.strip().lower()
    if isinstance(val, dict):
        for subk in ("commit", "sha", "publication", "report", "review_commit", "checkpoint", "acceptance_commit"):
            subv = val.get(subk)
            if isinstance(subv, str) and subv.strip():
                return subv.strip().lower()
    return None


def verify_committed_helpers_unchanged(root: Path, head_sha: str) -> list[dict]:
    records: list[dict] = []
    for helper_abs in (SCRIPT_PATH, UI_HELPER_PATH):
        if not helper_abs.is_file():
            raise ReleaseValidationError(f"Required runtime helper missing on disk: {helper_abs}")
        rel_posix = helper_abs.relative_to(root).as_posix()
        disk_bytes = helper_abs.read_bytes()
        disk_sha = sha256_bytes(disk_bytes)
        if not git_object_exists(root, f"{head_sha}:{rel_posix}"):
            raise ReleaseValidationError(f"Helper {rel_posix} is not committed in executing HEAD {head_sha}.")
        git_blob = git_bytes(root, ["cat-file", "-p", f"{head_sha}:{rel_posix}"])
        git_sha = sha256_bytes(git_blob)
        if disk_bytes != git_blob:
            raise ReleaseValidationError(
                f"Helper {rel_posix} on disk ({disk_sha}) differs from committed HEAD blob ({git_sha})."
            )
        records.append({
            "relative_path": rel_posix,
            "byte_length": len(disk_bytes),
            "sha256": disk_sha,
        })
    return records


def validate_release_contract(
    release_doc: dict,
    *,
    root: Path,
    release_commit: str,
    release_path: str,
    now_utc: datetime,
    blob_loader: Callable[[str], bytes],
    commit_exists_fn: Callable[[str], bool],
    database_name: str = DEFAULT_V2_DATABASE_NAME,
) -> dict:
    """Pure CPU/Git fail-closed validation of the coordinator runtime release and local repository state."""
    rc = release_commit.strip().lower()
    if not HEX40_RE.match(rc):
        raise ReleaseValidationError(f"release_commit must be a 40-char lowercase hex SHA, got {release_commit!r}")
    if rc in REJECTED_AUTHORITY_COMMITS:
        raise ReleaseValidationError(
            f"Authority commit {rc} is historical/returned/preparation-only and cannot authorize runtime execution."
        )

    rel_norm = release_path.strip().replace("\\", "/")
    if (
        not rel_norm.startswith("docs/coordination/WP-0006/")
        or not rel_norm.endswith(".json")
        or ".." in rel_norm.split("/")
    ):
        raise ReleaseValidationError(
            f"release_path must be a JSON path under docs/coordination/WP-0006/, got {release_path!r}"
        )

    schema = release_doc.get("schema")
    if schema not in ("eledgercare.f2-runtime-release/1", "eledgercare.f2-runtime-release/2"):
        raise ReleaseValidationError(f"Unsupported release schema: {schema!r}")

    if release_doc.get("owner") != EXPECTED_OWNER:
        raise ReleaseValidationError(f"Release owner {release_doc.get('owner')!r} != {EXPECTED_OWNER!r}")
    if release_doc.get("conversation_id") != EXPECTED_CONVERSATION_ID:
        raise ReleaseValidationError(
            f"Release conversation_id {release_doc.get('conversation_id')!r} != {EXPECTED_CONVERSATION_ID!r}"
        )
    if release_doc.get("model") != EXPECTED_MODEL or release_doc.get("effort") != EXPECTED_EFFORT:
        raise ReleaseValidationError(
            f"Release model/effort ({release_doc.get('model')!r}/{release_doc.get('effort')!r}) "
            f"!= ({EXPECTED_MODEL!r}/{EXPECTED_EFFORT!r})"
        )

    source_commit = str(release_doc.get("source_commit") or "").strip().lower()
    if source_commit != EXPECTED_SOURCE_COMMIT:
        raise ReleaseValidationError(
            f"Release source_commit {source_commit!r} != frozen corrected product source {EXPECTED_SOURCE_COMMIT!r}"
        )

    executing_head = str(release_doc.get("executing_head") or "").strip().lower()
    if not HEX40_RE.match(executing_head) or executing_head in REJECTED_EXECUTING_HEADS:
        raise ReleaseValidationError(
            f"Release executing_head {executing_head!r} is invalid or superseded."
        )

    actual_head = git_stdout(root, ["rev-parse", "HEAD"]).lower()
    porcelain = git_stdout(root, ["status", "--porcelain"])
    if porcelain != "":
        raise ReleaseValidationError(f"Owned worktree is not clean: {porcelain!r}")
    if actual_head != executing_head:
        raise ReleaseValidationError(
            f"Local worktree HEAD {actual_head} does not match release executing_head {executing_head}."
        )

    # Ancestry check: source_commit and source-response checkpoint must be ancestors of executing_head
    # (never assuming immediate HEAD~1 == source_commit).
    if not git_is_ancestor(root, EXPECTED_SOURCE_COMMIT, actual_head):
        raise ReleaseValidationError(
            f"Corrected source commit {EXPECTED_SOURCE_COMMIT} is not an ancestor of executing HEAD {actual_head}."
        )
    if not git_is_ancestor(root, EXPECTED_SOURCE_RESPONSE_CHECKPOINT, actual_head):
        raise ReleaseValidationError(
            f"Source-response checkpoint {EXPECTED_SOURCE_RESPONSE_CHECKPOINT} is not an ancestor of {actual_head}."
        )

    changed_since_source = [
        ln.strip()
        for ln in git_stdout(root, ["diff", "--name-only", EXPECTED_SOURCE_COMMIT, actual_head]).splitlines()
        if ln.strip()
    ]
    forbidden_touched = [
        p
        for p in changed_since_source
        if any(p.startswith(pref) for pref in FORBIDDEN_DIFF_PREFIXES)
        or not (p.startswith("docs/") or p in ("CURRENT.md", "INDEX.md"))
    ]
    if forbidden_touched:
        raise ReleaseValidationError(
            f"Protected product/research/evidence paths changed between {EXPECTED_SOURCE_COMMIT} and {actual_head}: "
            f"{forbidden_touched}"
        )

    # Verify exact Git tree OIDs at BOTH source_commit and executing_head
    rel_trees = release_doc.get("product_tree_objects")
    if not isinstance(rel_trees, dict):
        raise ReleaseValidationError("Release missing product_tree_objects mapping.")
    required_release_tree_keys = {"src", "workers/local_ocr", "web", "tests", "deploy"}
    missing_tree_keys = sorted(required_release_tree_keys - set(rel_trees.keys()))
    if missing_tree_keys:
        raise ReleaseValidationError(f"Release product_tree_objects missing keys: {missing_tree_keys}")

    verified_product_trees: dict[str, str] = {}
    for tree_path, want_oid in EXPECTED_PRODUCT_TREES.items():
        src_oid = git_stdout(root, ["rev-parse", f"{EXPECTED_SOURCE_COMMIT}:{tree_path}"]).lower()
        head_oid = git_stdout(root, ["rev-parse", f"{actual_head}:{tree_path}"]).lower()
        if src_oid != want_oid or head_oid != want_oid:
            raise ReleaseValidationError(
                f"Product tree {tree_path} drifted: source={src_oid}, head={head_oid}, expected={want_oid}"
            )
        if tree_path in rel_trees and str(rel_trees[tree_path]).lower() != want_oid:
            raise ReleaseValidationError(
                f"Release product_tree_objects[{tree_path!r}]={rel_trees[tree_path]!r} != expected {want_oid}"
            )
        verified_product_trees[tree_path] = head_oid

    for extra_k, extra_v in rel_trees.items():
        if extra_k not in EXPECTED_PRODUCT_TREES:
            raise ReleaseValidationError(f"Unexpected key in product_tree_objects: {extra_k!r}")

    verified_protected_trees: dict[str, str] = {}
    for prot_path, want_oid in EXPECTED_PROTECTED_TREES.items():
        head_oid = git_stdout(root, ["rev-parse", f"{actual_head}:{prot_path}"]).lower()
        if head_oid != want_oid:
            raise ReleaseValidationError(
                f"Protected tree {prot_path} at HEAD ({head_oid}) != expected {want_oid}"
            )
        verified_protected_trees[prot_path] = head_oid

    if git_object_exists(root, f"{actual_head}:docs/agent-reports/eld-f2-implementer"):
        raise ReleaseValidationError(
            "Canonical docs/agent-reports/eld-f2-implementer already exists before genuine runtime completion!"
        )

    # Accepted design & independent source-review bindings
    design_rev = str(release_doc.get("accepted_design_review") or "").strip().lower()
    if design_rev != EXPECTED_ACCEPTED_DESIGN_REVIEW:
        raise ReleaseValidationError(
            f"accepted_design_review {design_rev!r} != {EXPECTED_ACCEPTED_DESIGN_REVIEW!r}"
        )
    src_rev_key, src_rev_sha = _extract_source_review_sha(release_doc)
    if not HEX40_RE.match(src_rev_sha) or src_rev_sha in REJECTED_SOURCE_REVIEWS:
        raise ReleaseValidationError(
            f"Invalid or unaccepted independent source-review SHA in {src_rev_key}: {src_rev_sha!r}"
        )
    if not commit_exists_fn(src_rev_sha):
        raise ReleaseValidationError(
            f"Accepted source-review commit {src_rev_sha} ({src_rev_key}) is not present in local Git objects; fetch origin first."
        )

    # Pinned digests: check BOTH release JSON and actual local worktree computations
    rel_digests = release_doc.get("pinned_digests")
    if not isinstance(rel_digests, dict):
        raise ReleaseValidationError("Release missing pinned_digests mapping.")
    local_digests = compute_local_worktree_digests(root)
    for dk, want_hex in EXPECTED_PINNED_DIGESTS.items():
        got_rel = str(rel_digests.get(dk) or "").strip().lower()
        got_loc = local_digests[dk].lower()
        if got_rel != want_hex:
            raise ReleaseValidationError(f"Release pinned_digests[{dk!r}]={got_rel!r} != expected {want_hex!r}")
        if got_loc != want_hex:
            raise ReleaseValidationError(f"Local worktree digest {dk}={got_loc!r} != expected {want_hex!r}")

    # Lease, GPU UUID, expiry
    lease_id = str(release_doc.get("lease_id") or "").strip()
    if (
        not lease_id.startswith("WP-0006-")
        or lease_id in REJECTED_LEASE_IDS
        or "WP-0007" in lease_id
        or "reviewer" in lease_id.lower()
    ):
        raise ReleaseValidationError(f"Invalid, returned, or non-author lease_id: {lease_id!r}")

    gpu_uuid = str(release_doc.get("gpu_uuid") or "").strip()
    if gpu_uuid != EXPECTED_GPU_UUID:
        raise ReleaseValidationError(f"gpu_uuid {gpu_uuid!r} != qualified {EXPECTED_GPU_UUID!r}")

    released_dt = parse_utc_iso(release_doc.get("released_utc", ""), "released_utc")
    expires_dt = parse_utc_iso(release_doc.get("expires_utc", ""), "expires_utc")
    if expires_dt <= released_dt:
        raise ReleaseValidationError("expires_utc must be strictly after released_utc.")
    if now_utc < released_dt - timedelta(seconds=30):
        raise ReleaseValidationError(f"Lease {lease_id} is not yet active (released_utc={released_dt.isoformat()}).")
    remaining_s = (expires_dt - now_utc).total_seconds()
    if remaining_s < MIN_LEASE_REMAINING_SECONDS:
        raise ReleaseValidationError(
            f"Lease {lease_id} is expired or within {MIN_LEASE_REMAINING_SECONDS}s of expiry "
            f"(expires_utc={expires_dt.isoformat()}, now={now_utc.isoformat()})."
        )

    # Scoped roots, ports, database, caps, and flags
    ports = release_doc.get("ports")
    if ports != EXPECTED_PORTS:
        raise ReleaseValidationError(f"Release ports {ports!r} != owned author ports {EXPECTED_PORTS!r}")

    q0_root = Path(os.path.abspath(str(release_doc.get("readonly_q0_root") or "")))
    if os.path.normcase(str(q0_root)) != os.path.normcase(str(EXPECTED_Q0_ROOT)):
        raise ReleaseValidationError(f"readonly_q0_root {q0_root} != expected {EXPECTED_Q0_ROOT}")

    runtime_root_raw = str(release_doc.get("runtime_root") or "").strip()
    if not runtime_root_raw:
        raise ReleaseValidationError("Release missing runtime_root.")
    runtime_root = Path(os.path.abspath(runtime_root_raw))
    if not is_inside(runtime_root, ALLOWED_F2_RUNTIME_PARENT):
        raise ReleaseValidationError(
            f"runtime_root {runtime_root} must be inside {ALLOWED_F2_RUNTIME_PARENT}"
        )
    if (
        os.path.normcase(str(runtime_root)) == os.path.normcase(str(ALLOWED_F2_RUNTIME_PARENT))
        or is_inside(runtime_root, q0_root)
        or is_inside(q0_root, runtime_root)
        or is_inside(runtime_root, root)
        or "reviewer" in runtime_root.name.lower()
        or "wp-0007" in str(runtime_root).lower()
    ):
        raise ReleaseValidationError(f"Unsafe or non-author runtime_root: {runtime_root}")

    if not database_name or database_name == INITIAL_TRIAL_DATABASE_NAME or not re.match(r"^[a-z0-9_]+$", database_name):
        raise ReleaseValidationError(
            f"Database name {database_name!r} is invalid or collides with retained initial trial DB {INITIAL_TRIAL_DATABASE_NAME!r}."
        )

    if release_doc.get("storage_cap_bytes") != EXPECTED_STORAGE_CAP_BYTES:
        raise ReleaseValidationError(f"Unexpected storage_cap_bytes: {release_doc.get('storage_cap_bytes')!r}")
    if release_doc.get("free_floor_bytes") != EXPECTED_FREE_FLOOR_BYTES:
        raise ReleaseValidationError(f"Unexpected free_floor_bytes: {release_doc.get('free_floor_bytes')!r}")
    if release_doc.get("allow_test_content") is not False:
        raise ReleaseValidationError("allow_test_content must be strictly false.")
    if release_doc.get("torchvision_local_sha256_TOFU_accepted") is not True:
        raise ReleaseValidationError("torchvision_local_sha256_TOFU_accepted must be true.")

    # Finite 4-attempt matrix validation (zero warmups, zero extra retries, zero holdouts)
    if release_doc.get("max_model_attempts") != EXPECTED_MAX_MODEL_ATTEMPTS:
        raise ReleaseValidationError(
            f"max_model_attempts {release_doc.get('max_model_attempts')!r} != {EXPECTED_MAX_MODEL_ATTEMPTS}"
        )
    plan = release_doc.get("plan")
    if not isinstance(plan, list) or len(plan) != 4:
        raise ReleaseValidationError("Release plan must contain exactly the 4 bounded scenarios.")
    plan_json_str = json.dumps(plan)
    if any(tok.lower() in plan_json_str.lower() for tok in (*HOLDOUT_SUBSTRINGS, "warmup")):
        raise ReleaseValidationError("Release plan references forbidden holdout or warmup work.")
    step_attempts = [s.get("model_attempts") for s in plan if isinstance(s, dict)]
    if step_attempts != [1, 1, 2, 0] or sum(step_attempts) != EXPECTED_MAX_MODEL_ATTEMPTS:
        raise ReleaseValidationError(f"Release plan attempt counts {step_attempts!r} != [1, 1, 2, 0].")
    step_fixtures = [plan[0].get("fixture_id"), plan[1].get("fixture_id"), plan[2].get("fixture_id"), plan[3].get("fixture_id")]
    if step_fixtures[:3] != ["SYN-WO-01-v1-raster300", "SYN-MP-01-v0-clean", "SYN-WO-01-v1-raster300"] or step_fixtures[3] not in (None, ""):
        raise ReleaseValidationError(f"Release plan fixture sequence {step_fixtures!r} diverges from accepted F2 matrix.")

    # Pre-lease coordinator observation files verification
    obs_files = release_doc.get("observation_files")
    if not isinstance(obs_files, dict) or not {"host-before.json", "processes-before.json", "model-before.json"}.issubset(obs_files.keys()):
        raise ReleaseValidationError("Release missing required observation_files (host-before, processes-before, model-before).")

    verified_observations: dict[str, dict] = {}
    for obs_name, obs_meta in obs_files.items():
        if not isinstance(obs_meta, dict):
            raise ReleaseValidationError(f"Invalid observation metadata for {obs_name!r}")
        obs_path = str(obs_meta.get("path") or "").strip().replace("\\", "/")
        want_sha = str(obs_meta.get("sha256") or "").strip().lower()
        if not obs_path.startswith("docs/coordination/WP-0006/") or not HEX64_RE.match(want_sha):
            raise ReleaseValidationError(f"Invalid path or sha256 in observation_files[{obs_name!r}]")
        blob_bytes = blob_loader(obs_path)
        raw_sha = sha256_bytes(blob_bytes)
        lf_sha = sha256_bytes(blob_bytes.replace(b"\r\n", b"\n"))
        if want_sha not in (raw_sha, lf_sha):
            raise ReleaseValidationError(
                f"Observation {obs_name} ({obs_path}) digest mismatch: expected {want_sha}, got raw={raw_sha}, lf={lf_sha}"
            )
        verified_observations[obs_name] = {
            "path": obs_path,
            "expected_sha256": want_sha,
            "raw_blob_sha256": raw_sha,
            "lf_normalized_sha256": lf_sha,
            "matched_representation": "raw_blob" if want_sha == raw_sha else "lf_normalized",
        }

    committed_helpers = verify_committed_helpers_unchanged(root, actual_head)

    retained_allowed = set(release_doc.get("retained_prior_run_directories") or DEFAULT_RETAINED_PRIOR_RUN_DIRS)

    return {
        "validated_utc": now_utc.isoformat(),
        "release_commit": rc,
        "release_path": rel_norm,
        "schema": schema,
        "lease_id": lease_id,
        "gpu_uuid": gpu_uuid,
        "released_utc": released_dt.isoformat(),
        "expires_utc": expires_dt.isoformat(),
        "lease_remaining_seconds_at_validation": round(remaining_s, 3),
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "source_response_checkpoint": EXPECTED_SOURCE_RESPONSE_CHECKPOINT,
        "executing_head": actual_head,
        "changed_paths_since_source_commit": changed_since_source,
        "accepted_design_review": design_rev,
        "accepted_source_review_field": src_rev_key,
        "accepted_source_review": src_rev_sha,
        "product_tree_objects": verified_product_trees,
        "protected_tree_objects": verified_protected_trees,
        "pinned_digests": local_digests,
        "readonly_q0_root": str(q0_root),
        "runtime_root": str(runtime_root),
        "database_name": database_name,
        "ports": dict(EXPECTED_PORTS),
        "max_model_attempts": EXPECTED_MAX_MODEL_ATTEMPTS,
        "allowed_retained_prior_run_directories": sorted(retained_allowed),
        "verified_observations": verified_observations,
        "committed_helpers": committed_helpers,
    }


def load_release_from_git(
    root: Path,
    release_commit: str,
    release_path: str,
    *,
    now_utc: datetime | None = None,
    database_name: str | None = None,
) -> tuple[dict, dict, dict]:
    rc = release_commit.strip().lower()
    if not HEX40_RE.match(rc):
        raise ReleaseValidationError(f"release_commit must be a 40-char lowercase hex SHA, got {release_commit!r}")
    if rc in REJECTED_AUTHORITY_COMMITS:
        raise ReleaseValidationError(
            f"Authority commit {rc} is historical/returned/preparation-only and cannot authorize runtime execution."
        )
    if not git_object_exists(root, f"{rc}^{{commit}}"):
        raise ReleaseValidationError(f"Coordinator commit {rc} not found in local Git repository; run git fetch origin.")

    rel_norm = release_path.strip().replace("\\", "/")
    if not git_object_exists(root, f"{rc}:{rel_norm}"):
        raise ReleaseValidationError(f"Release path {rel_norm!r} does not exist in commit {rc}.")

    raw_release = git_bytes(root, ["cat-file", "-p", f"{rc}:{rel_norm}"])
    release_doc = json.loads(raw_release.decode("utf-8"))
    db_name = database_name or str(release_doc.get("database_name") or DEFAULT_V2_DATABASE_NAME)

    def _blob_loader(p: str) -> bytes:
        if not git_object_exists(root, f"{rc}:{p}"):
            raise ReleaseValidationError(f"Observation blob {p!r} missing in commit {rc}.")
        return git_bytes(root, ["cat-file", "-p", f"{rc}:{p}"])

    def _commit_exists(sha: str) -> bool:
        return git_object_exists(root, f"{sha}^{{commit}}")

    validated = validate_release_contract(
        release_doc,
        root=root,
        release_commit=rc,
        release_path=rel_norm,
        now_utc=now_utc or utc_now_dt(),
        blob_loader=_blob_loader,
        commit_exists_fn=_commit_exists,
        database_name=db_name,
    )
    release_blob_meta = {
        "raw_sha256": sha256_bytes(raw_release),
        "lf_normalized_sha256": sha256_bytes(raw_release.replace(b"\r\n", b"\n")),
        "byte_length": len(raw_release),
    }
    return release_doc, validated, release_blob_meta


def inspect_and_snapshot_runtime_root(
    runtime_root: Path,
    allowed_retained_run_dirs: set[str],
    *,
    create_if_missing: bool,
) -> tuple[list[str], dict[str, dict[str, dict]]]:
    """Inspects runtime_root, snapshots any explicitly allowed retained prior run dirs, and fails closed on unknown state."""
    if runtime_root.exists():
        if is_reparse_or_link(runtime_root):
            raise RuntimeError(f"Writable runtime root {runtime_root} is a symlink or reparse point.")
    else:
        if create_if_missing:
            runtime_root.mkdir(parents=True, exist_ok=True)
        return [], {}

    for entry in runtime_root.iterdir():
        if entry.name != "runs" or not entry.is_dir() or is_reparse_or_link(entry):
            raise RuntimeError(
                f"Unexpected top-level entry in writable runtime root {runtime_root}: {entry.name!r}"
            )

    runs_dir = runtime_root / "runs"
    if not runs_dir.exists():
        return [], {}

    retained_names: list[str] = []
    snapshots: dict[str, dict[str, dict]] = {}
    for child in sorted(runs_dir.iterdir(), key=lambda p: p.name):
        if not child.is_dir() or is_reparse_or_link(child):
            raise RuntimeError(f"Unexpected non-directory or reparse entry under {runs_dir}: {child.name!r}")
        if child.name not in allowed_retained_run_dirs:
            raise RuntimeError(
                f"Unexpected pre-existing run directory {child.name!r} in {runs_dir}; refusing mutable state reuse."
            )
        retained_names.append(child.name)
        file_map: dict[str, dict] = {}
        for dirpath, dirnames, filenames in os.walk(child, followlinks=False):
            for dn in dirnames:
                if is_reparse_or_link(Path(dirpath, dn)):
                    raise RuntimeError(f"Reparse directory inside retained run dir {child.name}: {dn}")
            for fn in sorted(filenames):
                fp = Path(dirpath, fn)
                if is_reparse_or_link(fp):
                    raise RuntimeError(f"Reparse file inside retained run dir {child.name}: {fn}")
                raw = fp.read_bytes()
                rel = fp.relative_to(child).as_posix()
                file_map[rel] = {"byte_length": len(raw), "sha256": sha256_bytes(raw)}
        snapshots[child.name] = file_map

    return retained_names, snapshots


def verify_retained_snapshot_unchanged(runtime_root: Path, snapshots: dict[str, dict[str, dict]]) -> bool:
    for run_name, expected_files in snapshots.items():
        run_dir = runtime_root / "runs" / run_name
        if not run_dir.is_dir():
            raise RuntimeError(f"Retained prior run directory {run_dir} disappeared!")
        actual_files: dict[str, dict] = {}
        for dirpath, _, filenames in os.walk(run_dir, followlinks=False):
            for fn in sorted(filenames):
                fp = Path(dirpath, fn)
                raw = fp.read_bytes()
                rel = fp.relative_to(run_dir).as_posix()
                actual_files[rel] = {"byte_length": len(raw), "sha256": sha256_bytes(raw)}
        if actual_files != expected_files:
            raise RuntimeError(f"Retained prior run directory {run_name} was modified during execution!")
    return True


def list_new_run_directories(runtime_root: Path, retained_run_dirs: set[str]) -> list[str]:
    runs_dir = runtime_root / "runs"
    if not runs_dir.exists():
        return []
    return sorted(
        p.name for p in runs_dir.iterdir() if p.is_dir() and p.name not in retained_run_dirs
    )


def assert_lease_still_valid(expires_utc_iso: str, context_label: str) -> None:
    exp = parse_utc_iso(expires_utc_iso, "expires_utc")
    now = utc_now_dt()
    if now >= exp:
        raise RuntimeError(
            f"GPU lease expired at {exp.isoformat()} before {context_label} (now={now.isoformat()}); halting."
        )


# --- Win32 exact (PID, CreationTime FILETIME) & single-process TerminateProcess helpers ---
if os.name == "nt":
    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    _k32.GetProcessTimes.restype = wintypes.BOOL
    _k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    _k32.GetExitCodeProcess.restype = wintypes.BOOL
    _k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.TerminateProcess.restype = wintypes.BOOL
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.CloseHandle.restype = wintypes.BOOL
else:
    _k32 = None


def query_process_filetime_and_alive(pid: int) -> tuple[int | None, bool]:
    if _k32 is None or not pid or pid <= 0:
        return None, False
    h = _k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None, False
    try:
        c, e, kt, ut = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
        if not _k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut)):
            return None, False
        ft = (int(c.dwHighDateTime) << 32) | int(c.dwLowDateTime)
        code = wintypes.DWORD()
        alive = bool(_k32.GetExitCodeProcess(h, ctypes.byref(code)) and code.value == STILL_ACTIVE)
        return ft, alive
    finally:
        _k32.CloseHandle(h)


def is_exact_process_alive(pid: int | None, expected_ft: int | None) -> bool:
    if not pid or not expected_ft or pid <= 0 or expected_ft <= 0:
        return False
    ft, alive = query_process_filetime_and_alive(pid)
    return alive and ft == expected_ft


def terminate_single_process_verified(pid: int, expected_ft: int, exit_code: int = 1) -> dict:
    """Terminates ONLY the single verified OS process via Win32 TerminateProcess (no recursive tree kill)."""
    if _k32 is None:
        raise RuntimeError("Win32 process termination requires Windows.")
    h = _k32.OpenProcess(PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        ft, alive = query_process_filetime_and_alive(pid)
        return {"pid": pid, "already_exited": not alive, "observed_ft": ft}
    try:
        c, e, kt, ut = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
        if not _k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut)):
            raise RuntimeError(f"GetProcessTimes failed before terminating PID {pid}")
        actual_ft = (int(c.dwHighDateTime) << 32) | int(c.dwLowDateTime)
        if actual_ft != expected_ft:
            raise RuntimeError(
                f"Refusing to terminate PID {pid}: creation FILETIME {actual_ft} != expected {expected_ft}"
            )
        code = wintypes.DWORD()
        if _k32.GetExitCodeProcess(h, ctypes.byref(code)) and code.value != STILL_ACTIVE:
            return {"pid": pid, "expected_ft": expected_ft, "already_exited": True}
        terminated_utc = utc_now()
        if not _k32.TerminateProcess(h, exit_code):
            err = ctypes.get_last_error()
            raise RuntimeError(f"Win32 TerminateProcess({pid}) failed with error {err}")
        return {
            "pid": pid,
            "create_filetime": expected_ft,
            "method": "Win32 TerminateProcess (single process only, non-recursive)",
            "terminated_utc": terminated_utc,
        }
    finally:
        _k32.CloseHandle(h)


def check_port_bound(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def capture_host_and_gpu_snapshot(
    label: str,
    *,
    obs_dir: Path,
    runtime_root: Path,
    ports: dict[str, int],
) -> dict:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    mem = MEMORYSTATUSEX(dwLength=ctypes.sizeof(MEMORYSTATUSEX))
    _k32.GlobalMemoryStatusEx(ctypes.byref(mem))

    gpu_line = subprocess.check_output(
        [
            "nvidia-smi",
            "--query-gpu=index,uuid,name,driver_version,pstate,memory.total,memory.used,memory.free,utilization.gpu",
            "--format=csv,noheader",
        ],
        text=True,
    ).strip()
    compute_apps = subprocess.check_output(
        ["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,process_name,used_memory", "--format=csv,noheader"],
        text=True,
    ).strip()
    app_lines = [ln.strip() for ln in compute_apps.splitlines() if ln.strip()]
    cuda_compute_apps = [ln for ln in app_lines if not ln.endswith("[N/A]")]
    wddm_desktop_count = len(app_lines) - len(cuda_compute_apps)

    py_dotnet_procs = subprocess.check_output(
        [
            "pwsh",
            "-NoProfile",
            "-Command",
            "@(Get-Process python*,dotnet*,postgres*,node* -ErrorAction SilentlyContinue | "
            "Select-Object Id,ProcessName) | ConvertTo-Json -Compress",
        ],
        text=True,
    ).strip()
    parsed_procs = json.loads(py_dotnet_procs) if py_dotnet_procs else []
    if isinstance(parsed_procs, dict):
        parsed_procs = [parsed_procs]

    disk_c = shutil.disk_usage(r"C:\\")
    snap = {
        "label": label,
        "observed_utc": utc_now(),
        "logical_cpus": os.cpu_count(),
        "ram_total_bytes": mem.ullTotalPhys,
        "ram_avail_bytes": mem.ullAvailPhys,
        "memory_load_pct": mem.dwMemoryLoad,
        "disk_c_free_bytes": disk_c.free,
        "runtime_root_used_bytes": directory_size_bytes(runtime_root),
        "ports_bound": {str(p): check_port_bound(p) for p in (ports["api"], ports["ui"], ports["postgres"])},
        "nvidia_smi_gpu": gpu_line,
        "cuda_compute_apps": cuda_compute_apps,
        "wddm_desktop_app_count": wddm_desktop_count,
        "host_confounders_note": (
            "Windows 11 WDDM desktop session shares RTX 5070 Ti display VRAM across desktop processes, "
            "and concurrent non-GPU CPU/RAM host activity may exist; timings are operational product "
            "observations rather than isolated benchmark claims."
        ),
        "active_python_dotnet_postgres_node_processes": parsed_procs,
    }
    write_json_lf(obs_dir / f"{label}.json", snap)
    return snap


def verify_model_integrity_snapshot(label: str, *, q0_root: Path, obs_dir: Path) -> dict:
    manifest, manifest_sha = load_json_checked(
        MODEL_MANIFEST_PATH,
        EXPECTED_PINNED_DIGESTS["model_manifest_sha256"],
        "model-files.json",
    )
    model_dir = normalize_and_verify_model_dir(
        str(q0_root / "models" / "Unlimited_OCR_2_04809669"),
        str(q0_root / "notices" / "Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"),
        manifest,
    )
    verify_model_sources_ast_safety(model_dir)
    rec = {
        "label": label,
        "observed_utc": utc_now(),
        "q0_root": str(q0_root),
        "model_manifest_sha256": manifest_sha,
        "runtime_objects_verified": 18,
        "notice_readme_verified": True,
        "static_ast_safety_verified": True,
    }
    write_json_lf(obs_dir / f"{label}.json", rec)
    return rec


class OwnedPostgres:
    def __init__(self, root: Path, pg_port: int, default_db: str):
        self.root = root
        self.pg_port = pg_port
        self.default_db = default_db
        self.settings = json.loads((root / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
        if int(self.settings["port"]) != pg_port:
            raise RuntimeError(
                f".local/secrets/pg-local.json port {self.settings['port']} != released port {pg_port}"
            )
        self.psql = root / ".local" / "tools" / "pgsql-18.7-1" / "bin" / "psql.exe"

    def start(self) -> dict:
        subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(self.root / "deploy/dev/postgres/start-cluster.ps1")],
            cwd=self.root,
            check=True,
        )
        pid_line = (self.root / ".local/postgres-data/postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip()
        pid = int(pid_line)
        ft, alive = query_process_filetime_and_alive(pid)
        if not alive or not ft:
            raise RuntimeError(f"Started postmaster PID {pid} not alive")
        return {"postmaster_pid": pid, "postmaster_create_filetime": ft, "started_utc": utc_now()}

    def stop(self) -> dict:
        pid_file = self.root / ".local/postgres-data/postmaster.pid"
        prior_pid = int(pid_file.read_text(encoding="utf-8").splitlines()[0].strip()) if pid_file.exists() else None
        subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(self.root / "deploy/dev/postgres/stop-cluster.ps1")],
            cwd=self.root,
            check=True,
        )
        return {
            "stopped_postmaster_pid": prior_pid,
            "stopped_utc": utc_now(),
            "port_55434_bound": check_port_bound(self.pg_port),
        }

    def prepare_database(self, db_name: str) -> str:
        proc = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(self.root / "deploy/dev/database/prepare-database.ps1"), "-Database", db_name],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout

    def query_json(self, sql: str, *, db_name: str | None = None, role: str = "admin") -> list[dict]:
        target_db = db_name or self.default_db
        user = self.settings["adminUser"] if role == "admin" else self.settings["appUser"]
        pw = self.settings["adminPassword"] if role == "admin" else self.settings["appPassword"]
        env = dict(os.environ, PGPASSWORD=pw)
        wrapped = f"SELECT COALESCE(json_agg(t), '[]'::json)::text FROM ({sql}) t;"
        out = subprocess.check_output(
            [
                str(self.psql),
                "-X",
                "-q",
                "-A",
                "-t",
                "-v",
                "ON_ERROR_STOP=1",
                "-h",
                str(self.settings["host"]),
                "-p",
                str(self.settings["port"]),
                "-U",
                str(user),
                "-d",
                target_db,
                "-c",
                wrapped,
            ],
            env=env,
            text=True,
        ).strip()
        return json.loads(out) if out else []

    def app_connection_string(self, db_name: str | None = None) -> str:
        target_db = db_name or self.default_db
        s = self.settings
        return (
            f"Host={s['host']};Port={s['port']};Database={target_db};"
            f"Username={s['appUser']};Password={s['appPassword']}"
        )


class OwnedApiInstance:
    def __init__(
        self,
        label: str,
        app_conn_str: str,
        *,
        root: Path,
        api_port: int,
        q0_root: Path,
        runtime_root: Path,
        gpu_uuid: str,
        obs_dir: Path,
        ocr_enabled: bool,
    ):
        self.label = label
        self.ocr_enabled = ocr_enabled
        self.app_conn_str = app_conn_str
        self.root = root
        self.api_port = api_port
        self.q0_root = q0_root
        self.runtime_root = runtime_root
        self.gpu_uuid = gpu_uuid
        self.proc: subprocess.Popen | None = None
        self.pid: int = 0
        self.create_filetime: int = 0
        self.started_utc: str = ""
        self.stdout_log = obs_dir / f"api-{label}.stdout.log"
        self.stderr_log = obs_dir / f"api-{label}.stderr.log"
        self._out_fh = None
        self._err_fh = None

    def start(self) -> dict:
        if check_port_bound(self.api_port):
            raise RuntimeError(f"Port {self.api_port} is already bound before starting API '{self.label}'.")
        api_dir = self.root / "src" / "ELedgerCare.Api" / "bin" / "Release" / "net10.0"
        api_dll = api_dir / "ELedgerCare.Api.dll"
        if not api_dll.is_file():
            raise FileNotFoundError(f"Missing built API assembly: {api_dll}")

        env = dict(os.environ)
        env["ASPNETCORE_ENVIRONMENT"] = "Production"
        env["DOTNET_NOLOGO"] = "1"
        env["Api__Port"] = str(self.api_port)
        env["ConnectionStrings__Runtime"] = self.app_conn_str
        env["LocalOcr__WorkerRootPath"] = str(self.root / "workers" / "local_ocr")
        if self.ocr_enabled:
            env["LocalOcr__Enabled"] = "true"
            env["LocalOcr__ReadOnlyQ0Root"] = str(self.q0_root)
            env["LocalOcr__WritableRuntimeRoot"] = str(self.runtime_root)
            env["LocalOcr__LeasedGpuUuid"] = self.gpu_uuid
        else:
            env["LocalOcr__Enabled"] = "false"
            for k in ("LocalOcr__ReadOnlyQ0Root", "LocalOcr__WritableRuntimeRoot", "LocalOcr__LeasedGpuUuid"):
                env.pop(k, None)

        self._out_fh = open(self.stdout_log, "wb")
        self._err_fh = open(self.stderr_log, "wb")
        self.proc = subprocess.Popen(
            ["dotnet", str(api_dll)],
            cwd=api_dir,
            env=env,
            stdout=self._out_fh,
            stderr=self._err_fh,
        )
        self.pid = self.proc.pid
        ft, alive = query_process_filetime_and_alive(self.pid)
        if not alive or not ft:
            raise RuntimeError(f"API '{self.label}' exited immediately on start.")
        self.create_filetime = ft
        self.started_utc = utc_now()

        deadline = time.monotonic() + 60.0
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"API '{self.label}' exited with code {self.proc.returncode} before listening.")
            if check_port_bound(self.api_port):
                break
            time.sleep(0.15)
        else:
            raise TimeoutError(f"API '{self.label}' did not bind 127.0.0.1:{self.api_port} within 60s.")

        return {
            "label": self.label,
            "pid": self.pid,
            "create_filetime": self.create_filetime,
            "ocr_enabled": self.ocr_enabled,
            "started_utc": self.started_utc,
        }

    def stop_single_process(self) -> dict:
        res: dict = {"label": self.label, "pid": self.pid, "create_filetime": self.create_filetime}
        if self.pid > 0 and self.create_filetime > 0:
            res["termination"] = terminate_single_process_verified(self.pid, self.create_filetime, exit_code=1)
        if self.proc is not None:
            try:
                self.proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                pass
        for fh in (self._out_fh, self._err_fh):
            if fh is not None:
                try:
                    fh.close()
                except OSError:
                    pass
        t_end = time.monotonic() + 10.0
        while time.monotonic() < t_end and check_port_bound(self.api_port):
            time.sleep(0.1)
        res["stopped_utc"] = utc_now()
        res["port_5190_bound_after"] = check_port_bound(self.api_port)
        return res


def http_request(
    api_port: int,
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> tuple[int, dict[str, str], bytes]:
    url = f"http://127.0.0.1:{api_port}{path}"
    req = urllib.request.Request(url, data=body, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers.items()), resp.read()
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers.items()), err.read()


def submit_pdf(api_port: int, pdf_path: Path) -> dict:
    pdf_bytes = pdf_path.read_bytes()
    expected_sha = sha256_bytes(pdf_bytes)
    idem_key = str(uuid.uuid4())
    status, headers, raw = http_request(
        api_port,
        "POST",
        "/api/documents",
        body=pdf_bytes,
        headers={"Content-Type": "application/pdf", "Idempotency-Key": idem_key},
    )
    if status != 201:
        raise RuntimeError(f"POST /api/documents failed ({status}): {raw.decode('utf-8', 'replace')}")
    receipt = json.loads(raw.decode("utf-8"))
    if receipt["sha256"] != expected_sha or receipt["byteLength"] != len(pdf_bytes):
        raise RuntimeError(f"Receipt digest mismatch: {receipt}")
    return {
        "fixture_name": pdf_path.name,
        "idempotency_key": idem_key,
        "http_status": status,
        "location": headers.get("Location"),
        "receipt": receipt,
        "expected_sha256": expected_sha,
        "expected_byte_length": len(pdf_bytes),
    }


def request_extraction_http(api_port: int, document_id: str, retry_attempt_id: str | None = None) -> tuple[int, dict]:
    if retry_attempt_id is None:
        status, _, raw = http_request(api_port, "POST", f"/api/documents/{document_id}/extraction", body=b"")
    else:
        payload = json.dumps({"retryAttemptId": retry_attempt_id}).encode("utf-8")
        status, _, raw = http_request(
            api_port,
            "POST",
            f"/api/documents/{document_id}/extraction",
            body=payload,
            headers={"Content-Type": "application/json"},
        )
    return status, json.loads(raw.decode("utf-8")) if raw else {}


def wait_for_completed_attempt(
    pg: OwnedPostgres,
    *,
    api_port: int,
    runtime_root: Path,
    document_id: str,
    timeout_s: float,
    tracked_identities: list[dict],
) -> dict:
    t0 = time.monotonic()
    timeline: list[dict] = []
    last_state_key = None
    gpu_samples: list[str] = []
    seen_attempt_id: str | None = None

    while time.monotonic() - t0 < timeout_s:
        status_code, _, raw = http_request(api_port, "GET", f"/api/documents/{document_id}/extraction")
        if status_code != 200:
            raise RuntimeError(f"GET /extraction returned {status_code}")
        view = json.loads(raw.decode("utf-8"))
        cur = view.get("currentAttempt")
        att_id = cur["attemptId"] if cur else None
        if att_id:
            seen_attempt_id = att_id

        hb_data = None
        if seen_attempt_id:
            hb_path = runtime_root / "runs" / f"attempt-{seen_attempt_id}" / "output" / "heartbeat.json"
            if hb_path.is_file():
                try:
                    hb_data = json.loads(hb_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    pass

        state_key = (
            view["status"],
            cur["status"] if cur else None,
            cur["phase"] if cur else None,
            hb_data.get("phase") if hb_data else None,
            (hb_data.get("forward_progress", 0) > 0) if hb_data else False,
        )
        if state_key != last_state_key:
            last_state_key = state_key
            timeline.append({
                "observed_utc": utc_now(),
                "elapsed_s": round(time.monotonic() - t0, 3),
                "job_status": view["status"],
                "attempt_id": att_id,
                "attempt_phase_db": cur["phase"] if cur else None,
                "heartbeat_phase": hb_data.get("phase") if hb_data else None,
                "forward_progress": hb_data.get("forward_progress") if hb_data else None,
            })
            if hb_data and hb_data.get("phase") in ("loading_model", "inferring") and len(gpu_samples) < 6:
                gpu_out = subprocess.check_output(
                    ["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,process_name,used_memory", "--format=csv,noheader"],
                    text=True,
                ).strip()
                cuda_lines = [ln.strip() for ln in gpu_out.splitlines() if ln.strip() and not ln.strip().endswith("[N/A]")]
                gpu_samples.append(f"{utc_now()} | phase={hb_data.get('phase')} | {'; '.join(cuda_lines) if cuda_lines else 'none'}")

        if view["status"] in ("completed", "failed", "interrupted"):
            db_attempts = pg.query_json(
                f"SELECT attempt_id, attempt_number, fencing_token, retried_from_attempt_id, status, phase, "
                f"run_directory_name, supervisor_pid, supervisor_create_filetime, launcher_pid, launcher_create_filetime, "
                f"worker_pid, worker_create_filetime, started_at, ended_at, exit_code, failure_code, failure_detail "
                f"FROM eledgercare.execution_attempts WHERE document_id = '{document_id}' ORDER BY attempt_number ASC"
            )
            for row in db_attempts:
                tracked_identities.append({
                    "attempt_id": row["attempt_id"],
                    "launcher_pid": row["launcher_pid"],
                    "launcher_create_filetime": row["launcher_create_filetime"],
                    "worker_pid": row["worker_pid"],
                    "worker_create_filetime": row["worker_create_filetime"],
                })

            if view["status"] != "completed":
                raise RuntimeError(
                    f"Model attempt for document {document_id} ended with unexpected status '{view['status']}': "
                    f"{json.dumps({'view': view, 'db_attempts': db_attempts}, indent=2)}"
                )

            db_results = pg.query_json(
                f"SELECT result_id, attempt_id, fencing_token, schema_version, encode(input_sha256, 'hex') AS input_sha256, "
                f"input_byte_length, page_count, raw_output_byte_length, encode(raw_output_sha256, 'hex') AS raw_output_sha256, "
                f"model_repo_id, model_revision, encode(model_manifest_sha256, 'hex') AS model_manifest_sha256, "
                f"encode(dependency_lock_sha256, 'hex') AS dependency_lock_sha256, "
                f"encode(worker_source_digest, 'hex') AS worker_source_sha256, "
                f"encode(worker_config_digest, 'hex') AS worker_config_sha256, "
                f"renderer_identity, finish_reason, output_page_count, load_duration_ms, render_duration_ms, "
                f"infer_duration_ms, total_duration_ms, diagnostic_metadata_json "
                f"FROM eledgercare.extraction_results WHERE document_id = '{document_id}'"
            )
            if len(db_results) != 1:
                raise RuntimeError(f"Expected 1 extraction_results row for {document_id}, found {len(db_results)}")

            res_row = db_results[0]
            want_cfg_sha = EXPECTED_PINNED_DIGESTS[f"worker_config_{int(res_row['page_count'])}p_sha256"]
            if (
                res_row["model_repo_id"] != MODEL_REPO_ID
                or res_row["model_revision"] != MODEL_REVISION
                or res_row["model_manifest_sha256"] != EXPECTED_PINNED_DIGESTS["model_manifest_sha256"]
                or res_row["dependency_lock_sha256"] != EXPECTED_PINNED_DIGESTS["dependency_lock_sha256"]
                or res_row["worker_source_sha256"] != EXPECTED_PINNED_DIGESTS["worker_source_sha256"]
                or res_row["worker_config_sha256"] != want_cfg_sha
            ):
                raise RuntimeError(f"Persisted result provenance digests diverged from frozen pins: {res_row}")

            winning_attempt_id = res_row["attempt_id"]
            run_dir = runtime_root / "runs" / f"attempt-{winning_attempt_id}"
            raw_disk = (run_dir / "output" / "raw_output.utf8.bin").read_bytes()
            raw_disk_sha = sha256_bytes(raw_disk)
            envelope_disk = json.loads((run_dir / "output" / "envelope.json").read_text(encoding="utf-8"))
            request_disk = json.loads((run_dir / "request.json").read_text(encoding="utf-8"))

            api_res = view["result"]
            api_raw_bytes = api_res["rawText"].encode("utf-8")
            api_raw_sha = sha256_bytes(api_raw_bytes)

            if not (raw_disk_sha == res_row["raw_output_sha256"] == api_res["rawSha256"] == api_raw_sha == envelope_disk["output"]["sha256"]):
                raise RuntimeError("Raw SHA-256 mismatch across disk, DB, envelope, and API!")

            orig_status, _, orig_bytes = http_request(api_port, "GET", f"/api/documents/{document_id}/original")
            if orig_status != 200 or sha256_bytes(orig_bytes) != res_row["input_sha256"]:
                raise RuntimeError("Original PDF download failed byte/SHA-256 verification after completion!")

            return {
                "document_id": document_id,
                "winning_attempt_id": winning_attempt_id,
                "run_dir": str(run_dir),
                "timeline": timeline,
                "gpu_compute_samples": gpu_samples,
                "db_attempts": db_attempts,
                "db_result": res_row,
                "envelope": envelope_disk,
                "request_manifest_keys": sorted(request_disk.keys()),
                "api_page_numbers": [p["pageNumber"] for p in api_res["pages"]],
                "api_page_block_counts": [len(p["blocks"]) for p in api_res["pages"]],
                "original_download_verified_sha256": sha256_bytes(orig_bytes),
            }

        time.sleep(1.0)

    raise TimeoutError(f"Timed out after {timeout_s}s waiting for document {document_id} extraction.")


def run_edge_ui_verification(
    label: str,
    docs_spec: list[dict],
    *,
    obs_dir: Path,
    ui_port: int,
    api_port: int,
) -> dict:
    in_path = obs_dir / f"ui-spec-{label}.json"
    out_path = obs_dir / f"ui-verified-{label}.json"
    write_json_lf(in_path, {"uiPort": ui_port, "apiPort": api_port, "documents": docs_spec})
    subprocess.run(
        [
            "node",
            str(UI_HELPER_PATH),
            "--repoRoot",
            str(ROOT),
            "--input",
            str(in_path),
            "--output",
            str(out_path),
        ],
        cwd=ROOT,
        check=True,
    )
    return json.loads(out_path.read_text(encoding="utf-8"))


def execute_live_trial(
    release_doc: dict,
    validated: dict,
    release_blob_meta: dict,
    *,
    scratch_dir: Path,
) -> int:
    obs_dir = scratch_dir / "observations"
    obs_dir.mkdir(parents=True, exist_ok=True)

    freeze_manifest = {
        "schema": "eledgercare.wp-0006.helper-freeze/2",
        "frozen_utc": utc_now(),
        "release_commit": validated["release_commit"],
        "release_path": validated["release_path"],
        "release_blob": release_blob_meta,
        "executing_head": validated["executing_head"],
        "source_commit": validated["source_commit"],
        "committed_helpers": validated["committed_helpers"],
    }
    write_json_lf(scratch_dir / "plan-and-helper-freeze-v2.json", freeze_manifest)

    ports = validated["ports"]
    api_port = ports["api"]
    ui_port = ports["ui"]
    pg_port = ports["postgres"]
    q0_root = Path(validated["readonly_q0_root"])
    runtime_root = Path(validated["runtime_root"])
    gpu_uuid = validated["gpu_uuid"]
    lease_id = validated["lease_id"]
    expires_utc = validated["expires_utc"]
    db_name = validated["database_name"]
    allowed_retained = set(validated["allowed_retained_prior_run_directories"])

    tracked_identities: list[dict] = []
    active_api: OwnedApiInstance | None = None
    pg = OwnedPostgres(ROOT, pg_port, db_name)
    pg_started = False
    retained_names: list[str] = []
    retained_snapshots: dict[str, dict[str, dict]] = {}

    trial_record: dict = {
        "schema": "eledgercare.wp-0006.author-runtime-summary/2",
        "release_authority_commit": validated["release_commit"],
        "release_path": validated["release_path"],
        "release_blob": release_blob_meta,
        "lease_id": lease_id,
        "gpu_uuid": gpu_uuid,
        "source_commit": validated["source_commit"],
        "source_response_checkpoint": validated["source_response_checkpoint"],
        "executing_head": validated["executing_head"],
        "accepted_design_review": validated["accepted_design_review"],
        "accepted_source_review_field": validated["accepted_source_review_field"],
        "accepted_source_review": validated["accepted_source_review"],
        "writable_runtime_root": str(runtime_root),
        "readonly_q0_root": str(q0_root),
        "database": db_name,
        "pinned_digests": validated["pinned_digests"],
        "started_utc": utc_now(),
        "scenarios": {},
    }

    try:
        print("[Stage2-v2] 0. Verifying ports, runtime root snapshot, GPU/host preflight, and model integrity...", flush=True)
        for p in (api_port, ui_port, pg_port):
            if check_port_bound(p):
                raise RuntimeError(f"Port {p} is unexpectedly bound before trial start.")

        retained_names, retained_snapshots = inspect_and_snapshot_runtime_root(
            runtime_root, allowed_retained, create_if_missing=True
        )
        trial_record["retained_prior_failed_run_directories"] = retained_names

        host_before = capture_host_and_gpu_snapshot(
            "host-before", obs_dir=obs_dir, runtime_root=runtime_root, ports=ports
        )
        trial_record["host_before"] = host_before
        if gpu_uuid not in host_before["nvidia_smi_gpu"]:
            raise RuntimeError(f"Leased GPU {gpu_uuid} not observed in nvidia-smi: {host_before['nvidia_smi_gpu']}")
        if host_before["cuda_compute_apps"]:
            raise RuntimeError(
                f"Active CUDA compute processes exist on GPU before trial start: {host_before['cuda_compute_apps']}"
            )
        if host_before["disk_c_free_bytes"] < EXPECTED_FREE_FLOOR_BYTES:
            raise RuntimeError(f"Disk free bytes {host_before['disk_c_free_bytes']} below 20 GiB floor.")
        if host_before["runtime_root_used_bytes"] > EXPECTED_STORAGE_CAP_BYTES:
            raise RuntimeError(f"Runtime root used bytes {host_before['runtime_root_used_bytes']} exceeds 4 GiB cap.")

        trial_record["model_before"] = verify_model_integrity_snapshot(
            "model-before", q0_root=q0_root, obs_dir=obs_dir
        )

        print(f"[Stage2-v2] Starting owned PostgreSQL 18.7 cluster on 127.0.0.1:{pg_port}...", flush=True)
        pg_info_1 = pg.start()
        pg_started = True
        prep_out = pg.prepare_database(db_name)
        (obs_dir / "prepare-database-runtime-v2.log").write_bytes(prep_out.encode("utf-8"))
        existing_counts = pg.query_json(
            "SELECT (SELECT count(*) FROM eledgercare.documents) AS docs, "
            "(SELECT count(*) FROM eledgercare.execution_attempts) AS attempts"
        )[0]
        if int(existing_counts["docs"]) != 0 or int(existing_counts["attempts"]) != 0:
            raise RuntimeError(f"Database {db_name} is not clean at trial start: {existing_counts}")
        trial_record["postgres_initial"] = pg_info_1

        print(f"[Stage2-v2] Starting owned ELedgerCare.Api #1 (LocalOcr:Enabled=true) on 127.0.0.1:{api_port}...", flush=True)
        active_api = OwnedApiInstance(
            "v2-run1-ocr-enabled",
            pg.app_connection_string(),
            root=ROOT,
            api_port=api_port,
            q0_root=q0_root,
            runtime_root=runtime_root,
            gpu_uuid=gpu_uuid,
            obs_dir=obs_dir,
            ocr_enabled=True,
        )
        trial_record["api_1_start"] = active_api.start()

        # --- SCENARIO 1: Model Attempt #1 (SYN-WO-01-v1-raster300.pdf, 1 page) ---
        assert_lease_still_valid(expires_utc, "Model Attempt #1")
        print("[Stage2-v2] SCENARIO 1 / New Attempt #1: Submitting SYN-WO-01-v1-raster300.pdf (1 page)...", flush=True)
        f01_path = ROOT / "tests" / "fixtures" / "SYN-WO-01-v1-raster300.pdf"
        sub1 = submit_pdf(api_port, f01_path)
        doc1_id = sub1["receipt"]["documentId"]
        post1_status, post1_body = request_extraction_http(api_port, doc1_id)
        if post1_status != 202:
            raise RuntimeError(f"Expected 202 Accepted on doc1 extraction, got {post1_status}: {post1_body}")
        comp1 = wait_for_completed_attempt(
            pg,
            api_port=api_port,
            runtime_root=runtime_root,
            document_id=doc1_id,
            timeout_s=2100.0,
            tracked_identities=tracked_identities,
        )
        print(
            f"[Stage2-v2] New Attempt #1 COMPLETED! attempt={comp1['winning_attempt_id']} "
            f"raw_sha={comp1['db_result']['raw_output_sha256']} total_ms={comp1['db_result']['total_duration_ms']}",
            flush=True,
        )
        ui1 = run_edge_ui_verification(
            "scenario1-f01",
            [
                {
                    "label": "Scenario 1: SYN-WO-01-v1-raster300 (1 page)",
                    "documentId": doc1_id,
                    "expectedPages": 1,
                    "expectedRawSha256": comp1["db_result"]["raw_output_sha256"],
                    "expectedAttemptCount": 1,
                    "expectedAttemptStatuses": ["Completed"],
                    "expectedOriginalSha256": sub1["expected_sha256"],
                    "expectedOriginalBytes": sub1["expected_byte_length"],
                }
            ],
            obs_dir=obs_dir,
            ui_port=ui_port,
            api_port=api_port,
        )
        trial_record["scenarios"]["1_f01_single_page_complete"] = {
            "submission": sub1,
            "request_extraction_status": post1_status,
            "completion": comp1,
            "edge_ui_verification": ui1,
        }

        # --- SCENARIO 2: Model Attempt #2 (SYN-MP-01-v0-clean.pdf, 3 pages) ---
        assert_lease_still_valid(expires_utc, "Model Attempt #2")
        print("[Stage2-v2] SCENARIO 2 / New Attempt #2: Submitting SYN-MP-01-v0-clean.pdf (3 pages)...", flush=True)
        f07_path = ROOT / "tests" / "fixtures" / "SYN-MP-01-v0-clean.pdf"
        sub2 = submit_pdf(api_port, f07_path)
        doc2_id = sub2["receipt"]["documentId"]
        post2_status, post2_body = request_extraction_http(api_port, doc2_id)
        if post2_status != 202:
            raise RuntimeError(f"Expected 202 Accepted on doc2 extraction, got {post2_status}: {post2_body}")
        comp2 = wait_for_completed_attempt(
            pg,
            api_port=api_port,
            runtime_root=runtime_root,
            document_id=doc2_id,
            timeout_s=3900.0,
            tracked_identities=tracked_identities,
        )
        if comp2["api_page_numbers"] != [1, 2, 3]:
            raise RuntimeError(f"Expected ordered pages [1, 2, 3], got {comp2['api_page_numbers']}")
        print(
            f"[Stage2-v2] New Attempt #2 COMPLETED! attempt={comp2['winning_attempt_id']} "
            f"pages={comp2['api_page_numbers']} raw_sha={comp2['db_result']['raw_output_sha256']} "
            f"total_ms={comp2['db_result']['total_duration_ms']}",
            flush=True,
        )
        trial_record["scenarios"]["2_f07_three_page_complete"] = {
            "submission": sub2,
            "request_extraction_status": post2_status,
            "completion": comp2,
        }

        # --- SCENARIO 3: New Attempt #3 (Live Supervisor Single-Process Kill During Inference) + New Attempt #4 (Explicit Retry) ---
        assert_lease_still_valid(expires_utc, "Model Attempt #3")
        print("[Stage2-v2] SCENARIO 3 / New Attempt #3: Submitting fresh SYN-WO-01-v1-raster300.pdf for live interruption...", flush=True)
        sub3 = submit_pdf(api_port, f01_path)
        doc3_id = sub3["receipt"]["documentId"]
        post3_status, post3_body = request_extraction_http(api_port, doc3_id)
        if post3_status != 202:
            raise RuntimeError(f"Expected 202 Accepted on doc3 extraction, got {post3_status}: {post3_body}")

        t_wait_inf = time.monotonic()
        attempt3_row = None
        hb_at_kill = None
        while time.monotonic() - t_wait_inf < 1800.0:
            rows = pg.query_json(
                f"SELECT attempt_id, attempt_number, fencing_token, status, phase, run_directory_name, "
                f"supervisor_pid, supervisor_create_filetime, launcher_pid, launcher_create_filetime, "
                f"worker_pid, worker_create_filetime "
                f"FROM eledgercare.execution_attempts WHERE document_id = '{doc3_id}' ORDER BY attempt_number DESC LIMIT 1"
            )
            if rows:
                r = rows[0]
                if r["status"] in ("failed", "interrupted", "completed"):
                    raise RuntimeError(f"Attempt #3 exited before live inference interruption could run: {r}")
                hb_file = runtime_root / "runs" / r["run_directory_name"] / "output" / "heartbeat.json"
                if hb_file.is_file():
                    try:
                        hb = json.loads(hb_file.read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        hb = None
                    if (
                        hb
                        and hb.get("phase") == "inferring"
                        and int(hb.get("forward_progress") or 0) >= 1
                        and r.get("launcher_pid")
                        and r.get("launcher_create_filetime")
                    ):
                        w_pid = int(hb["worker_pid"])
                        w_ft = int(hb["worker_create_filetime"])
                        l_pid = int(r["launcher_pid"])
                        l_ft = int(r["launcher_create_filetime"])
                        if (
                            is_exact_process_alive(active_api.pid, active_api.create_filetime)
                            and is_exact_process_alive(l_pid, l_ft)
                            and is_exact_process_alive(w_pid, w_ft)
                        ):
                            attempt3_row = r
                            hb_at_kill = hb
                            break
            time.sleep(0.25)

        if attempt3_row is None or hb_at_kill is None:
            raise RuntimeError("Did not observe active inference (phase='inferring', forward_progress>=1) on New Attempt #3.")

        gpu_during_inf = subprocess.check_output(
            ["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,process_name,used_memory", "--format=csv,noheader"],
            text=True,
        ).strip()
        cuda_during_inf = [ln.strip() for ln in gpu_during_inf.splitlines() if ln.strip() and not ln.strip().endswith("[N/A]")]

        l_pid = int(attempt3_row["launcher_pid"])
        l_ft = int(attempt3_row["launcher_create_filetime"])
        w_pid = int(hb_at_kill["worker_pid"])
        w_ft = int(hb_at_kill["worker_create_filetime"])
        tracked_identities.append({
            "attempt_id": attempt3_row["attempt_id"],
            "launcher_pid": l_pid,
            "launcher_create_filetime": l_ft,
            "worker_pid": w_pid,
            "worker_create_filetime": w_ft,
        })

        print(
            f"[Stage2-v2] New Attempt #3 active inference confirmed! forward_progress={hb_at_kill['forward_progress']} "
            f"supervisor={active_api.pid} launcher={l_pid} worker={w_pid}. Terminating supervisor ONLY...",
            flush=True,
        )
        t_kill = time.perf_counter()
        kill_receipt = active_api.stop_single_process()
        active_api = None

        while time.perf_counter() - t_kill < 30.0:
            if not is_exact_process_alive(l_pid, l_ft) and not is_exact_process_alive(w_pid, w_ft):
                break
            time.sleep(0.05)
        job_cleanup_ms = round((time.perf_counter() - t_kill) * 1000, 1)
        launcher_alive_after = is_exact_process_alive(l_pid, l_ft)
        worker_alive_after = is_exact_process_alive(w_pid, w_ft)
        if launcher_alive_after or worker_alive_after:
            raise RuntimeError(
                f"Job Object containment failure! launcher_alive={launcher_alive_after}, worker_alive={worker_alive_after}"
            )

        gpu_after_kill = subprocess.check_output(
            ["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,process_name,used_memory", "--format=csv,noheader"],
            text=True,
        ).strip()
        cuda_after_kill = [ln.strip() for ln in gpu_after_kill.splitlines() if ln.strip() and not ln.strip().endswith("[N/A]")]

        db_before_reconcile = pg.query_json(
            f"SELECT j.status AS job_status, a.attempt_id, a.status AS attempt_status, "
            f"(SELECT count(*) FROM eledgercare.extraction_results r WHERE r.document_id = '{doc3_id}') AS result_count "
            f"FROM eledgercare.processing_jobs j JOIN eledgercare.execution_attempts a ON a.job_id = j.job_id "
            f"WHERE j.document_id = '{doc3_id}'"
        )

        print(
            f"[Stage2-v2] Job Object killed launcher+worker in {job_cleanup_ms} ms (cuda_after_kill={cuda_after_kill}). "
            f"Starting API #2 to reconcile abandoned Attempt #3...",
            flush=True,
        )
        active_api = OwnedApiInstance(
            "v2-run2-recovery-and-retry",
            pg.app_connection_string(),
            root=ROOT,
            api_port=api_port,
            q0_root=q0_root,
            runtime_root=runtime_root,
            gpu_uuid=gpu_uuid,
            obs_dir=obs_dir,
            ocr_enabled=True,
        )
        api2_start = active_api.start()

        t_rec = time.monotonic()
        reconciled_view = None
        while time.monotonic() - t_rec < 20.0:
            st, _, raw = http_request(api_port, "GET", f"/api/documents/{doc3_id}/extraction")
            if st == 200:
                v = json.loads(raw.decode("utf-8"))
                if v["status"] == "interrupted":
                    reconciled_view = v
                    break
            time.sleep(0.25)
        if reconciled_view is None:
            raise RuntimeError("API #2 did not reconcile abandoned Attempt #3 to 'interrupted' within 20s.")

        replay_409_status, replay_409_body = request_extraction_http(api_port, doc3_id, retry_attempt_id=None)
        if replay_409_status != 409 or replay_409_body.get("code") != "retry_explicit_required":
            raise RuntimeError(f"Expected 409 retry_explicit_required, got {replay_409_status}: {replay_409_body}")

        assert_lease_still_valid(expires_utc, "Model Attempt #4 (Explicit Retry)")
        attempt3_id = attempt3_row["attempt_id"]
        print(f"[Stage2-v2] Issuing explicit retry for Attempt #3 ({attempt3_id}) -> New Attempt #4...", flush=True)
        retry4_status, retry4_body = request_extraction_http(api_port, doc3_id, retry_attempt_id=attempt3_id)
        if retry4_status != 202:
            raise RuntimeError(f"Expected 202 Accepted on explicit retry, got {retry4_status}: {retry4_body}")

        comp4 = wait_for_completed_attempt(
            pg,
            api_port=api_port,
            runtime_root=runtime_root,
            document_id=doc3_id,
            timeout_s=2100.0,
            tracked_identities=tracked_identities,
        )
        if len(comp4["db_attempts"]) != 2:
            raise RuntimeError(f"Expected 2 attempts retained on doc3, got {len(comp4['db_attempts'])}")
        if comp4["db_attempts"][0]["status"] != "interrupted" or comp4["db_attempts"][1]["status"] != "completed":
            raise RuntimeError(f"Unexpected doc3 attempt statuses: {comp4['db_attempts']}")
        if int(comp4["db_attempts"][1]["fencing_token"]) <= int(comp4["db_attempts"][0]["fencing_token"]):
            raise RuntimeError("Attempt #4 fencing token was not strictly greater than Attempt #3!")

        print(
            f"[Stage2-v2] New Attempt #4 COMPLETED! doc3 retains Attempt #1=interrupted "
            f"(token={comp4['db_attempts'][0]['fencing_token']}) and Attempt #2=completed "
            f"(token={comp4['db_attempts'][1]['fencing_token']}).",
            flush=True,
        )
        trial_record["scenarios"]["3_live_supervisor_kill_and_explicit_retry"] = {
            "submission": sub3,
            "attempt3_observed_at_kill": {
                "db_row": attempt3_row,
                "heartbeat": hb_at_kill,
                "cuda_compute_apps_at_kill": cuda_during_inf,
            },
            "supervisor_single_process_kill": kill_receipt,
            "job_object_containment_verification": {
                "job_object_cleanup_ms": job_cleanup_ms,
                "launcher_alive_after": launcher_alive_after,
                "worker_alive_after": worker_alive_after,
                "cuda_compute_apps_after_kill": cuda_after_kill,
                "db_state_before_api_restart": db_before_reconcile,
            },
            "api_2_start": api2_start,
            "reconciled_interrupted_view": reconciled_view,
            "caller_empty_replay_guard": {
                "http_status": replay_409_status,
                "problem": replay_409_body,
            },
            "explicit_retry_status": retry4_status,
            "retry_completion": comp4,
        }

        # --- SCENARIO 4: Stop Model Work, Restart API + PostgreSQL (fast), Reopen Saved Results with LocalOcr__Enabled=false ---
        print("[Stage2-v2] SCENARIO 4: Stopping OCR-enabled API, fast-restarting PostgreSQL 18.7, and reopening with LocalOcr:Enabled=false...", flush=True)
        api2_stop = active_api.stop_single_process()
        active_api = None

        new_run_dirs = list_new_run_directories(runtime_root, set(retained_names))
        if len(new_run_dirs) != EXPECTED_MAX_MODEL_ATTEMPTS:
            raise RuntimeError(
                f"Expected exactly {EXPECTED_MAX_MODEL_ATTEMPTS} new run directories under this release, "
                f"found {len(new_run_dirs)}: {new_run_dirs} (retained_prior={retained_names})"
            )

        pg_stop_mid = pg.stop()
        pg_start_after = pg.start()

        active_api = OwnedApiInstance(
            "v2-run3-ocr-disabled-reopen",
            pg.app_connection_string(),
            root=ROOT,
            api_port=api_port,
            q0_root=q0_root,
            runtime_root=runtime_root,
            gpu_uuid=gpu_uuid,
            obs_dir=obs_dir,
            ocr_enabled=False,
        )
        api3_start = active_api.start()

        reopened_api_checks = []
        for label, sub, comp, want_attempts in [
            ("doc1_f01_1p", sub1, comp1, 1),
            ("doc2_f07_3p", sub2, comp2, 1),
            ("doc3_f01_interrupted_then_retried", sub3, comp4, 2),
        ]:
            d_id = sub["receipt"]["documentId"]
            st_doc, _, raw_doc = http_request(api_port, "GET", f"/api/documents/{d_id}")
            st_ext, _, raw_ext = http_request(api_port, "GET", f"/api/documents/{d_id}/extraction")
            st_rep, _ = request_extraction_http(api_port, d_id, retry_attempt_id=None)
            st_org, _, raw_org = http_request(api_port, "GET", f"/api/documents/{d_id}/original")

            ext_body = json.loads(raw_ext.decode("utf-8"))
            if st_doc != 200 or st_ext != 200 or st_rep != 200 or st_org != 200:
                raise RuntimeError(f"Unexpected status reopening {d_id}: {st_doc}/{st_ext}/{st_rep}/{st_org}")
            if ext_body["workerEnabled"] is not False or ext_body["status"] != "completed":
                raise RuntimeError(f"Expected workerEnabled=false & status=completed on {d_id}")
            if ext_body["result"]["rawSha256"] != comp["db_result"]["raw_output_sha256"]:
                raise RuntimeError(f"Reopened rawSha256 mismatch on {d_id}")
            if len(ext_body["attempts"]) != want_attempts:
                raise RuntimeError(f"Expected {want_attempts} attempts on {d_id}, got {len(ext_body['attempts'])}")
            if sha256_bytes(raw_org) != sub["expected_sha256"]:
                raise RuntimeError(f"Original SHA-256 mismatch after DB+API restart on {d_id}")

            reopened_api_checks.append({
                "label": label,
                "document_id": d_id,
                "get_document_status": st_doc,
                "get_extraction_status": st_ext,
                "post_completed_replay_status": st_rep,
                "worker_enabled": ext_body["workerEnabled"],
                "persisted_status": ext_body["status"],
                "attempt_count": len(ext_body["attempts"]),
                "raw_sha256": ext_body["result"]["rawSha256"],
                "original_sha256": sha256_bytes(raw_org),
                "page_numbers": [p["pageNumber"] for p in ext_body["result"]["pages"]],
                "model_checkpoint": f"{ext_body['result']['provenance']['modelRepoId']}@{ext_body['result']['provenance']['modelRevision']}",
            })

        ui_all_disabled = run_edge_ui_verification(
            "scenario4-all-reopened-ocr-disabled",
            [
                {
                    "label": "Reopened Doc 1: SYN-WO-01 (1p) after API+PG restart with OCR disabled",
                    "documentId": doc1_id,
                    "expectedPages": 1,
                    "expectedRawSha256": comp1["db_result"]["raw_output_sha256"],
                    "expectedAttemptCount": 1,
                    "expectedAttemptStatuses": ["Completed"],
                    "expectedOriginalSha256": sub1["expected_sha256"],
                    "expectedOriginalBytes": sub1["expected_byte_length"],
                },
                {
                    "label": "Reopened Doc 2: SYN-MP-01 (3p) after API+PG restart with OCR disabled",
                    "documentId": doc2_id,
                    "expectedPages": 3,
                    "expectedRawSha256": comp2["db_result"]["raw_output_sha256"],
                    "expectedAttemptCount": 1,
                    "expectedAttemptStatuses": ["Completed"],
                    "expectedOriginalSha256": sub2["expected_sha256"],
                    "expectedOriginalBytes": sub2["expected_byte_length"],
                },
                {
                    "label": "Reopened Doc 3: SYN-WO-01 (interrupted + retried) after API+PG restart with OCR disabled",
                    "documentId": doc3_id,
                    "expectedPages": 1,
                    "expectedRawSha256": comp4["db_result"]["raw_output_sha256"],
                    "expectedAttemptCount": 2,
                    "expectedAttemptStatuses": ["Interrupted", "Completed"],
                    "expectedOriginalSha256": sub3["expected_sha256"],
                    "expectedOriginalBytes": sub3["expected_byte_length"],
                },
            ],
            obs_dir=obs_dir,
            ui_port=ui_port,
            api_port=api_port,
        )

        new_run_dirs_after_reopen = list_new_run_directories(runtime_root, set(retained_names))
        if new_run_dirs_after_reopen != new_run_dirs:
            raise RuntimeError("Unexpected new run directory created while LocalOcr:Enabled=false!")

        api3_stop = active_api.stop_single_process()
        active_api = None

        trial_record["scenarios"]["4_api_and_postgres_restart_disabled_reopen"] = {
            "api_2_stop": api2_stop,
            "postgres_fast_restart": {
                "stop": pg_stop_mid,
                "start": pg_start_after,
                "note": "Clean pg_ctl fast restart of owned cluster; not a power-loss test.",
            },
            "api_3_disabled_start": api3_start,
            "api_3_disabled_stop": api3_stop,
            "reopened_api_checks": reopened_api_checks,
            "edge_ui_verification_all_three": ui_all_disabled,
            "new_run_directories_unchanged": new_run_dirs_after_reopen,
            "retained_prior_failed_run_directories_unchanged": retained_names,
        }

        trial_record["outcome"] = "COMPLETED_ALL_4_SCENARIOS"
        return 0

    except Exception as exc:
        trial_record["outcome"] = "FAILED"
        trial_record["error"] = f"{type(exc).__name__}: {exc}"
        raise

    finally:
        if active_api is not None:
            try:
                trial_record["cleanup_api_stop"] = active_api.stop_single_process()
            except Exception as cleanup_err:
                trial_record["cleanup_api_stop_error"] = str(cleanup_err)

        if pg_started:
            try:
                trial_record["postgres_final_stop"] = pg.stop()
            except Exception as pg_err:
                trial_record["postgres_final_stop_error"] = str(pg_err)

        unique_identities = []
        seen_keys = set()
        for item in tracked_identities:
            key = (item.get("attempt_id"), item.get("launcher_pid"), item.get("worker_pid"))
            if key not in seen_keys:
                seen_keys.add(key)
                l_alive = is_exact_process_alive(item.get("launcher_pid"), item.get("launcher_create_filetime"))
                w_alive = is_exact_process_alive(item.get("worker_pid"), item.get("worker_create_filetime"))
                unique_identities.append({
                    **item,
                    "launcher_alive_at_return": l_alive,
                    "worker_alive_at_return": w_alive,
                })

        retained_intact = None
        if retained_snapshots:
            try:
                retained_intact = verify_retained_snapshot_unchanged(runtime_root, retained_snapshots)
            except Exception as ret_err:
                retained_intact = False
                trial_record["retained_snapshot_error"] = str(ret_err)

        model_after: dict = {}
        try:
            model_after = verify_model_integrity_snapshot("model-after", q0_root=q0_root, obs_dir=obs_dir)
        except Exception as mod_err:
            trial_record["model_after_error"] = str(mod_err)

        host_after: dict = {}
        try:
            host_after = capture_host_and_gpu_snapshot(
                "host-after", obs_dir=obs_dir, runtime_root=runtime_root, ports=ports
            )
        except Exception as host_err:
            trial_record["host_after_error"] = str(host_err)

        helpers_after = verify_committed_helpers_unchanged(ROOT, validated["executing_head"])
        porcelain_after = git_stdout(ROOT, ["status", "--porcelain"])

        new_runs_final = list_new_run_directories(runtime_root, set(retained_names))

        trial_record["completed_utc"] = utc_now()
        trial_record["git_clean_after"] = porcelain_after == ""
        trial_record["committed_helpers_verified_after"] = helpers_after
        trial_record["retained_prior_runs_verified_unchanged"] = retained_intact
        trial_record["model_after"] = model_after
        trial_record["host_after"] = host_after
        trial_record["observed_model_process_identities"] = unique_identities
        trial_record["new_release_run_directories"] = new_runs_final

        lease_return = {
            "schema": "eledgercare.gpu-lease-return/2",
            "lease_id": lease_id,
            "release_authority_commit": validated["release_commit"],
            "owner": EXPECTED_OWNER,
            "conversation_id": EXPECTED_CONVERSATION_ID,
            "gpu_uuid": gpu_uuid,
            "lease_state": "RETURNED_BY_OWNER_PENDING_COORDINATOR_ACK",
            "returned_utc": utc_now(),
            "model_attempts_executed_under_this_lease": len(new_runs_final),
            "new_release_run_directories": new_runs_final,
            "retained_prior_failed_run_directories": retained_names,
            "retained_prior_runs_verified_unchanged": retained_intact,
            "max_model_attempts_allowed": EXPECTED_MAX_MODEL_ATTEMPTS,
            "all_owned_model_processes_observed_exited": all(
                not x["launcher_alive_at_return"] and not x["worker_alive_at_return"]
                for x in unique_identities
            ),
            "observed_model_process_identities": unique_identities,
            "cuda_compute_apps_at_return": host_after.get("cuda_compute_apps", []),
            "ports_bound_at_return": host_after.get("ports_bound", {}),
            "model_18_objects_and_notice_unchanged": model_after.get("runtime_objects_verified") == 18
            and bool(model_after.get("notice_readme_verified")),
            "runtime_root": str(runtime_root),
            "runtime_root_used_bytes": host_after.get("runtime_root_used_bytes"),
        }
        write_json_lf(scratch_dir / "lease-return-v2.json", lease_return)
        write_json_lf(scratch_dir / "trial-summary-v2.json", trial_record)
        print(
            f"[Stage2-v2] Finalized trial-summary-v2.json ({trial_record.get('outcome')}) and explicit "
            f"lease-return-v2.json (new_attempts={len(new_runs_final)}, "
            f"all_exited={lease_return['all_owned_model_processes_observed_exited']}).",
            flush=True,
        )


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Versioned WP-0006 F2 author runtime driver v2.")
    p.add_argument("--release-commit", required=True, help="Exact 40-char coordinator runtime authority commit SHA.")
    p.add_argument("--release-path", required=True, help="Repo-relative JSON path inside --release-commit.")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run-validate",
        action="store_true",
        help="Validate release JSON, Git ancestry/trees, digests, and bounds on CPU only without starting services or GPU.",
    )
    mode.add_argument(
        "--execute-live",
        action="store_true",
        help="Execute the bounded 4-model-attempt real runtime matrix under the validated active sole GPU lease.",
    )
    p.add_argument("--validation-output", help="Optional path to write dry-run validation receipt JSON.")
    p.add_argument(
        "--scratch-dir",
        default=str(ROOT / ".scratch" / "stage2-runtime-v2"),
        help="Owned scratch output directory for v2 live execution (never .scratch/stage2-runtime).",
    )
    p.add_argument(
        "--database-name",
        default=None,
        help="Optional owned PostgreSQL database name override (defaults to eledgercare_f2_runtime_author_v2).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    scratch_dir = Path(os.path.abspath(args.scratch_dir))
    forbidden_scratch = {
        os.path.normcase(str((ROOT / ".scratch" / "stage2-runtime").resolve())),
        os.path.normcase(str((ROOT / "docs" / "implementation" / "WP-0006" / "runtime-author").resolve())),
    }
    if os.path.normcase(str(scratch_dir)) in forbidden_scratch:
        raise ReleaseValidationError(f"Refusing to overwrite historical runtime directory: {scratch_dir}")

    release_doc, validated, release_blob_meta = load_release_from_git(
        ROOT,
        args.release_commit,
        args.release_path,
        database_name=args.database_name,
    )

    if args.dry_run_validate:
        receipt = {
            "mode": "dry_run_validate_cpu_only",
            "release_blob": release_blob_meta,
            "validation": validated,
        }
        if args.validation_output:
            write_json_lf(Path(args.validation_output), receipt)
        print(json.dumps(receipt, indent=2))
        return 0

    return execute_live_trial(release_doc, validated, release_blob_meta, scratch_dir=scratch_dir)


if __name__ == "__main__":
    raise SystemExit(main())
