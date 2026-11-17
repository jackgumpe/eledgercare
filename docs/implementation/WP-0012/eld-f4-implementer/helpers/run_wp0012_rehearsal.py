"""Complete-workflow demonstration rehearsal orchestrator & fail-closed guard validator (WP-0012).

Owner: eld-f4-implementer (conversation b7c54417-db09-49bd-8d2b-7cc808f113be, gemini-4-carbon-high/high).

Modes:
  1. --cpu-dry-run [--with-disabled-ocr-smoke] [--output <json>]
     Pure CPU/Git/local-stack preparation check. NEVER sets LocalOcr__Enabled=true, NEVER imports
     ML/CUDA libraries, NEVER invokes nvidia-smi or model processes, and NEVER creates or writes to
     C:\\Users\\jackg\\eLedgerCare-Demo\\WP-0012\\author.
  2. --validate-release --release-commit <40-hex> --release-path <git-rel-json>
     Pure CPU/Git validation of a coordinator-published WP-0012 sole-GPU runtime release JSON.
  3. --execute-live --release-commit <40-hex> --release-path <git-rel-json>
     Gated live 2-attempt rehearsal execution for WP-0012 / 003. Refuses to start unless a valid,
     non-expired coordinator WP-0012 sole-GPU lease JSON binds clean local HEAD, exact unchanged
     product/worker trees, all 9 artifact digests, and an accepted independent /002 review commit.
     Stops immediately on first failure with zero retries, terminates owned processes/Job Objects,
     restarts PostgreSQL + API with LocalOcr__Enabled=false for disabled-OCR reopen verification,
     and writes owner-lease-return.json.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Callable
import urllib.request


def resolve_repo_root(start: Path) -> Path:
    cur = start.resolve()
    if cur.is_file():
        cur = cur.parent
    for cand in (cur, *cur.parents):
        if (cand / "ELedgerCare.slnx").is_file() and (cand / "workers" / "local_ocr" / "run_worker.py").is_file():
            return cand
    raise RuntimeError(f"Could not locate eLedgerCare repository root above {start}")


SCRIPT_PATH = Path(__file__).resolve()
HELPERS_DIR = SCRIPT_PATH.parent
DOSSIER_DIR = HELPERS_DIR.parent
REPO_ROOT = resolve_repo_root(HELPERS_DIR)
EDGE_DRIVER_PATH = HELPERS_DIR / "drive_rehearsal_edge.mjs"

if str(REPO_ROOT / "workers" / "local_ocr") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "workers" / "local_ocr"))

from local_ocr.protocol import (  # noqa: E402
    DEPENDENCY_LOCK_PATH,
    MODEL_MANIFEST_PATH,
    MODEL_REPO_ID,
    MODEL_REVISION,
    compute_config_digest,
    compute_worker_source_sha256,
)

HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

EXPECTED_PACKET = "WP-0012"
EXPECTED_OWNER = "eld-f4-implementer"
EXPECTED_CONVERSATION_ID = "b7c54417-db09-49bd-8d2b-7cc808f113be"
EXPECTED_MODEL = "gemini-4-carbon-high"
EXPECTED_EFFORT = "high"
EXPECTED_BRANCH = "rehearsal/wp-0012-product"
EXPECTED_GPU_UUID = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"

ACCEPTED_PACKET_BASE_SHA = "73c8d3c4f0a00312e3444328331b6cbd6406e882"
ACCEPTED_F4_FINAL_SOURCE_SHA = "c1fed68020ae67e8b4763bc6ea5473adaa86de2b"
PREPARATION_DISPATCH_AUTHORITY_SHA = "47fbc7612e4a08cf1960ad7ac01bd2843ae645e5"

ALLOWED_SOURCE_COMMITS = frozenset({
    ACCEPTED_F4_FINAL_SOURCE_SHA,
    ACCEPTED_PACKET_BASE_SHA,
})

REJECTED_RELEASE_COMMITS = frozenset({
    PREPARATION_DISPATCH_AUTHORITY_SHA,
    ACCEPTED_PACKET_BASE_SHA,
    ACCEPTED_F4_FINAL_SOURCE_SHA,
    "717a768994bbbabf75b8ee96b3b1aadca1bc5df3",
    "35e2f44d788a99ad1b2d10d1af95536cf1d1981a",
    "56b36b52e682a7396b02c34cf40c85a4f31f9329",
    "6ad846322afeb3781c50cc70d3144bc1d456f24b",
})

REJECTED_LEASE_PREFIXES = (
    "WP-0005-",
    "WP-0006-",
    "WP-0007-",
    "WP-0008-",
    "WP-0009-",
    "WP-0010-",
    "WP-0011-",
    "WP-0013-",
)

ALLOWED_RELEASE_SCHEMAS = frozenset({
    "eledgercare.wp0012-rehearsal-release/1",
    "eledgercare.wp0012-runtime-release/1",
    "eledgercare.demo-runtime-release/1",
})

EXPECTED_PRODUCT_TREES: dict[str, str] = {
    "src": "9760402fa88dcb343c28b14ad4de1bcb2fbafb2e",
    "web": "50fbbee1f58aace4e6ec36bd64203146d23aa96f",
    "tests": "25c21310699086acb818549b2a4c0b99469208f1",
    "deploy": "86e0c73d4b4c07bbdf92ebcd65a0903fc9c039f1",
    "workers/local_ocr": "dc9b69e480f93db1e73ebdd65719efaa9aeab298",
}
EXPECTED_SLNX_BLOB = "c00c2bc5ef46019fb4452fdf0bba7ca2271fc976"

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

REQUIRED_PINNED_DIGEST_KEYS = (
    "model_manifest_sha256",
    "dependency_lock_sha256",
    "worker_source_sha256",
    "worker_config_1p_sha256",
    "worker_config_3p_sha256",
    "syn_wo_01_sha256",
    "syn_mp_01_sha256",
)

EXPECTED_PORTS = {"api": 5590, "ui": 4610, "postgres": 55438}
EXPECTED_Q0_ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")
EXPECTED_DEMO_RUNTIME_ROOT = Path(r"C:\Users\jackg\eLedgerCare-Demo\WP-0012\author")
OWNED_REHEARSAL_DB = "eledgercare_demo_wp0012_author"
FORBIDDEN_DATABASES = frozenset({
    "eledgercare_f4_author_seed_f3",
    "eledgercare_f4_author_migrated",
    "eledgercare_product_dev",
    "eledgercare_demo_wp0012_reviewer",
})

# Exact kickoff & accepted product ceilings (WP-0012 kickoff L11 & ExtractionCeilings.cs)
GUARD_CEILINGS = {
    "max_model_attempts": 2,
    "automatic_retries": 0,
    "warmups": 0,
    "storage_cap_bytes": 4_294_967_296,       # 4 GiB owner output cap
    "free_floor_bytes": 21_474_836_480,       # 20 GiB free floor
    "max_lease_seconds": 21_600,              # 6 h lease ceiling
    "min_lease_remaining_seconds": 300,       # >= 5 min remaining before attempt launch
    "load_timeout_s": 1800,                   # 1800s model load timeout
    "one_page_timeout_s": 1800,               # 1800s 1-page call timeout
    "two_page_timeout_s": 2700,               # 2700s 2-page call timeout
    "three_page_timeout_s": 3600,             # 3600s 3-page call timeout
    "stall_timeout_s": 300,                   # 300s stall timeout
    "heartbeat_interval_s": 5,                # 5s heartbeat interval
    "max_raw_output_bytes": 16_777_216,       # 16 MiB raw output cap
    "max_log_bytes": 67_108_864,              # 64 MiB child log cap
    "max_extraction_pages": 3,                # 1..3 page extraction profile
    "max_intake_document_bytes": 10_485_760,  # 10 MiB intake ceiling
    "max_intake_pages": 50,                   # 50-page intake ceiling
}

FORBIDDEN_DIFF_PREFIXES = (
    "src/",
    "web/",
    "tests/",
    "deploy/",
    "workers/",
    "qualification/",
    "research/",
    "evaluation/",
    "docs/implementation/WP-0006/",
    "docs/implementation/WP-0008/",
    "docs/implementation/WP-0010/",
    "docs/reviews/",
    "docs/agent-reports/eld-f4-implementer/WP-0010/",
)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259


class RehearsalGuardError(RuntimeError):
    """Raised when any fail-closed rehearsal guard, digest, or coordinator lease check fails."""


def utc_now_dt() -> datetime:
    return datetime.now(timezone.utc)


def utc_now() -> str:
    return utc_now_dt().isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json_lf(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def parse_utc_iso(ts: str, field_name: str) -> datetime:
    if not isinstance(ts, str) or not ts.strip():
        raise RehearsalGuardError(f"Missing or non-string UTC timestamp in '{field_name}'.")
    norm = ts.strip()
    if norm.endswith("Z"):
        norm = norm[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(norm)
    except ValueError as exc:
        raise RehearsalGuardError(f"Invalid ISO-8601 timestamp in '{field_name}': {ts!r}") from exc
    if dt.tzinfo is None:
        raise RehearsalGuardError(f"Timestamp '{field_name}' must be timezone-aware UTC: {ts!r}")
    return dt.astimezone(timezone.utc)


def git_stdout(root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=str(root), text=True, encoding="utf-8").strip()


def git_bytes(root: Path, args: list[str]) -> bytes:
    return subprocess.check_output(["git", *args], cwd=str(root))


def git_object_exists(root: Path, spec: str) -> bool:
    proc = subprocess.run(
        ["git", "cat-file", "-e", spec],
        cwd=str(root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode == 0


def git_is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=str(root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode == 0


def is_reparse_point(path: Path) -> bool:
    FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
    attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    if attrs == 0xFFFFFFFF:
        return False
    return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)


def get_win32_process_identity(pid: int) -> dict | None:
    """Returns (pid, create_filetime, alive) using Win32 OpenProcess + GetProcessTimes + GetExitCodeProcess."""
    if pid <= 0:
        return None
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        creation = wintypes.FILETIME()
        exit_ft = wintypes.FILETIME()
        kernel_ft = wintypes.FILETIME()
        user_ft = wintypes.FILETIME()
        ok = ctypes.windll.kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_ft),
            ctypes.byref(kernel_ft),
            ctypes.byref(user_ft),
        )
        if not ok:
            return None
        create_ft = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
        exit_code = wintypes.DWORD()
        alive = False
        if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            alive = exit_code.value == STILL_ACTIVE
        return {"pid": pid, "create_filetime": create_ft, "alive": alive}
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def is_exact_process_alive(pid: int, expected_create_filetime: int) -> bool:
    ident = get_win32_process_identity(pid)
    if ident is None:
        return False
    return bool(ident["alive"] and ident["create_filetime"] == expected_create_filetime)


def compute_local_digests(root: Path = REPO_ROOT) -> dict[str, str]:
    worker_root = root / "workers" / "local_ocr"
    fixtures_dir = root / "tests" / "fixtures"
    return {
        "model_manifest_sha256": sha256_file(worker_root / "manifests" / "model-files.json"),
        "dependency_lock_sha256": sha256_file(worker_root / "manifests" / "dependency-lock.json"),
        "worker_source_sha256": compute_worker_source_sha256(worker_root),
        "worker_config_1p_sha256": compute_config_digest(1),
        "worker_config_2p_sha256": compute_config_digest(2),
        "worker_config_3p_sha256": compute_config_digest(3),
        "f1_swo_001_sha256": sha256_file(fixtures_dir / "F1-SWO-001.pdf"),
        "syn_wo_01_sha256": sha256_file(fixtures_dir / "SYN-WO-01-v1-raster300.pdf"),
        "syn_mp_01_sha256": sha256_file(fixtures_dir / "SYN-MP-01-v0-clean.pdf"),
    }


def inspect_readonly_q0_and_demo_roots_cpu(verify_model_sha256: bool = False) -> dict:
    """Read-only filesystem metadata check on Q0 root and Demo writable root (zero writes, zero ML imports)."""
    if not EXPECTED_Q0_ROOT.is_dir() or is_reparse_point(EXPECTED_Q0_ROOT):
        raise RehearsalGuardError(f"Read-only Q0 root missing or reparse point: {EXPECTED_Q0_ROOT}")

    venv_python = EXPECTED_Q0_ROOT / "venv" / "Scripts" / "python.exe"
    model_dir = EXPECTED_Q0_ROOT / "models" / "Unlimited_OCR_2_04809669"
    notice_dir = EXPECTED_Q0_ROOT / "notices" / "Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"

    if not venv_python.is_file():
        raise RehearsalGuardError(f"Q0 venv python.exe missing: {venv_python}")
    if not model_dir.is_dir() or is_reparse_point(model_dir):
        raise RehearsalGuardError(f"Q0 model directory missing or reparse point: {model_dir}")
    if not notice_dir.is_dir() or is_reparse_point(notice_dir):
        raise RehearsalGuardError(f"Q0 notice directory missing or reparse point: {notice_dir}")

    manifest = json.loads(MODEL_MANIFEST_PATH.read_text(encoding="utf-8"))
    files_spec = manifest.get("files", [])
    checked_count = 0
    total_model_bytes = 0
    for entry in files_spec:
        rel_name = entry["path"]
        expected_bytes = int(entry["size_bytes"])
        expected_sha = str(entry["sha256"]).lower()
        fpath = model_dir / rel_name
        if not fpath.is_file() or is_reparse_point(fpath):
            raise RehearsalGuardError(f"Model file missing or reparse point: {fpath}")
        stat_size = fpath.stat().st_size
        if stat_size != expected_bytes:
            raise RehearsalGuardError(f"Model file size mismatch on {rel_name}: {stat_size} != {expected_bytes}")
        if verify_model_sha256:
            actual_sha = sha256_file(fpath)
            if actual_sha != expected_sha:
                raise RehearsalGuardError(f"Model file SHA-256 mismatch on {rel_name}: {actual_sha} != {expected_sha}")
        checked_count += 1
        total_model_bytes += stat_size

    demo_exists = EXPECTED_DEMO_RUNTIME_ROOT.exists()
    existing_demo_entries: list[str] = []
    demo_used_bytes = 0
    if demo_exists:
        if is_reparse_point(EXPECTED_DEMO_RUNTIME_ROOT):
            raise RehearsalGuardError(f"Demo writable root is a reparse point: {EXPECTED_DEMO_RUNTIME_ROOT}")
        for item in sorted(EXPECTED_DEMO_RUNTIME_ROOT.rglob("*")):
            if is_reparse_point(item):
                raise RehearsalGuardError(f"Reparse point inside demo writable root: {item}")
            if item.is_file():
                demo_used_bytes += item.stat().st_size
        existing_demo_entries = [p.name for p in sorted(EXPECTED_DEMO_RUNTIME_ROOT.iterdir())]
        if demo_used_bytes > GUARD_CEILINGS["storage_cap_bytes"]:
            raise RehearsalGuardError(f"Demo writable root exceeds 4 GiB cap: {demo_used_bytes}")

    free_bytes = shutil.disk_usage(REPO_ROOT.anchor).free
    if free_bytes < GUARD_CEILINGS["free_floor_bytes"]:
        raise RehearsalGuardError(f"Available disk space {free_bytes} below 20 GiB safety floor.")

    return {
        "readonly_q0_root": str(EXPECTED_Q0_ROOT),
        "venv_python_exists": True,
        "model_files_verified_count": checked_count,
        "model_files_sha256_hashed": verify_model_sha256,
        "model_total_bytes": total_model_bytes,
        "notice_dir_exists": True,
        "writable_demo_root": str(EXPECTED_DEMO_RUNTIME_ROOT),
        "writable_demo_root_exists": demo_exists,
        "writable_demo_existing_entries": existing_demo_entries,
        "writable_demo_used_bytes": demo_used_bytes,
        "drive_free_bytes": free_bytes,
    }


def _extract_independent_review_002_sha(release_doc: dict) -> tuple[str, str]:
    candidate_keys = (
        "accepted_preparation_review",
        "accepted_review_002",
        "independent_review_002",
        "accepted_002",
        "accepted_review",
        "preparation_review",
    )
    for key in candidate_keys:
        val = release_doc.get(key)
        if isinstance(val, str) and val.strip():
            return key, val.strip().lower()
        if isinstance(val, dict):
            for sub in ("commit", "sha", "publication", "report"):
                sval = val.get(sub)
                if isinstance(sval, str) and sval.strip():
                    return f"{key}.{sub}", sval.strip().lower()
    raise RehearsalGuardError(
        "Missing independent WP-0012 / 002 review commit binding (accepted_preparation_review) in release JSON."
    )


def validate_release_contract(
    release_doc: dict,
    *,
    root: Path,
    release_commit: str,
    release_path: str,
    now_utc: datetime,
    blob_loader: Callable[[str], bytes],
    commit_exists_fn: Callable[[str], bool],
    database_name: str = OWNED_REHEARSAL_DB,
    require_clean_worktree: bool = True,
) -> dict:
    """Pure CPU/Git fail-closed validator for a coordinator WP-0012 sole-GPU runtime release."""
    rc = release_commit.strip().lower()
    if not HEX40_RE.match(rc):
        raise RehearsalGuardError(f"release_commit must be a 40-char lowercase hex SHA, got {release_commit!r}")
    if rc in REJECTED_RELEASE_COMMITS:
        raise RehearsalGuardError(
            f"Authority commit {rc} is historical or CPU-preparation-only and cannot authorize live inference."
        )

    rel_norm = release_path.strip().replace("\\", "/")
    if (
        not rel_norm.startswith("docs/coordination/WP-0012/")
        or not rel_norm.endswith(".json")
        or ".." in rel_norm.split("/")
    ):
        raise RehearsalGuardError(
            f"release_path must be a JSON path under docs/coordination/WP-0012/, got {release_path!r}"
        )

    schema = release_doc.get("schema")
    if schema not in ALLOWED_RELEASE_SCHEMAS:
        raise RehearsalGuardError(f"Unsupported WP-0012 release schema: {schema!r}")

    if "packet" in release_doc and release_doc.get("packet") != EXPECTED_PACKET:
        raise RehearsalGuardError(f"Release packet {release_doc.get('packet')!r} != {EXPECTED_PACKET!r}")
    if release_doc.get("owner") != EXPECTED_OWNER:
        raise RehearsalGuardError(f"Release owner {release_doc.get('owner')!r} != {EXPECTED_OWNER!r}")
    if release_doc.get("conversation_id") != EXPECTED_CONVERSATION_ID:
        raise RehearsalGuardError(
            f"Release conversation_id {release_doc.get('conversation_id')!r} != {EXPECTED_CONVERSATION_ID!r}"
        )
    if release_doc.get("model") != EXPECTED_MODEL or release_doc.get("effort") != EXPECTED_EFFORT:
        raise RehearsalGuardError(
            f"Release model/effort ({release_doc.get('model')!r}/{release_doc.get('effort')!r}) "
            f"!= ({EXPECTED_MODEL!r}/{EXPECTED_EFFORT!r})"
        )

    db_target = str(release_doc.get("database") or release_doc.get("database_name") or database_name).strip()
    if db_target in FORBIDDEN_DATABASES or db_target != OWNED_REHEARSAL_DB:
        raise RehearsalGuardError(
            f"Database {db_target!r} is forbidden; WP-0012 author must use {OWNED_REHEARSAL_DB!r} only."
        )

    source_commit = str(release_doc.get("source_commit") or "").strip().lower()
    if source_commit not in ALLOWED_SOURCE_COMMITS:
        raise RehearsalGuardError(
            f"Release source_commit {source_commit!r} must match accepted F4 product source {ACCEPTED_F4_FINAL_SOURCE_SHA!r} "
            f"or packet base {ACCEPTED_PACKET_BASE_SHA!r}."
        )

    executing_head = str(release_doc.get("executing_head") or "").strip().lower()
    if not HEX40_RE.match(executing_head) or executing_head in REJECTED_RELEASE_COMMITS:
        raise RehearsalGuardError(f"Invalid or preparation-base executing_head: {executing_head!r}")

    actual_head = git_stdout(root, ["rev-parse", "HEAD"]).lower()
    porcelain = git_stdout(root, ["status", "--porcelain"])
    if require_clean_worktree and porcelain != "":
        raise RehearsalGuardError(f"Owned worktree must be clean before live execution:\n{porcelain}")
    if actual_head != executing_head:
        raise RehearsalGuardError(
            f"Local worktree HEAD {actual_head} does not match release executing_head {executing_head}."
        )
    if not git_is_ancestor(root, PREPARATION_DISPATCH_AUTHORITY_SHA, actual_head):
        raise RehearsalGuardError(
            f"Preparation dispatch authority {PREPARATION_DISPATCH_AUTHORITY_SHA} is not an ancestor of {actual_head}."
        )

    changed_since_authority = [
        ln.strip()
        for ln in git_stdout(root, ["diff", "--name-only", PREPARATION_DISPATCH_AUTHORITY_SHA, actual_head]).splitlines()
        if ln.strip()
    ]
    forbidden_touched = [
        p for p in changed_since_authority if p.startswith(FORBIDDEN_DIFF_PREFIXES)
    ]
    if forbidden_touched:
        raise RehearsalGuardError(f"Forbidden paths modified since dispatch authority: {forbidden_touched}")

    rev_key, rev_sha = _extract_independent_review_002_sha(release_doc)
    if not HEX40_RE.match(rev_sha) or rev_sha in REJECTED_RELEASE_COMMITS or not commit_exists_fn(rev_sha):
        raise RehearsalGuardError(f"Invalid or unknown independent /002 review commit in {rev_key}: {rev_sha!r}")

    # Verify unchanged product & worker Git tree OIDs both locally and in release JSON
    rel_trees = release_doc.get("product_tree_objects")
    if not isinstance(rel_trees, dict):
        raise RehearsalGuardError("Missing product_tree_objects dict in release JSON.")
    for tree_path, expected_oid in EXPECTED_PRODUCT_TREES.items():
        local_oid = git_stdout(root, ["rev-parse", f"HEAD:{tree_path}"]).lower()
        if local_oid != expected_oid:
            raise RehearsalGuardError(f"Local tree {tree_path} ({local_oid}) != expected {expected_oid}")
        if str(rel_trees.get(tree_path) or "").lower() != expected_oid:
            raise RehearsalGuardError(
                f"Release product_tree_objects[{tree_path!r}] != expected {expected_oid}"
            )
    if git_stdout(root, ["rev-parse", "HEAD:ELedgerCare.slnx"]).lower() != EXPECTED_SLNX_BLOB:
        raise RehearsalGuardError("ELedgerCare.slnx blob drifted from accepted F4 product.")

    # Verify all local & release artifact SHA-256 digests
    local_digests = compute_local_digests(root)
    for k, exp in EXPECTED_PINNED_DIGESTS.items():
        if local_digests[k] != exp:
            raise RehearsalGuardError(f"Local artifact digest {k} ({local_digests[k]}) != expected {exp}")

    rel_digests = release_doc.get("pinned_digests")
    if not isinstance(rel_digests, dict):
        raise RehearsalGuardError("Missing pinned_digests dict in release JSON.")
    for k in REQUIRED_PINNED_DIGEST_KEYS:
        if str(rel_digests.get(k) or "").lower() != EXPECTED_PINNED_DIGESTS[k]:
            raise RehearsalGuardError(
                f"Release pinned_digests[{k!r}] ({rel_digests.get(k)!r}) != {EXPECTED_PINNED_DIGESTS[k]!r}"
            )

    # Verify committed helper byte identity against executing HEAD
    if require_clean_worktree:
        for helper_path in (SCRIPT_PATH, EDGE_DRIVER_PATH):
            rel_p = helper_path.relative_to(root).as_posix()
            if not git_object_exists(root, f"{actual_head}:{rel_p}"):
                raise RehearsalGuardError(f"Helper {rel_p} is not committed in executing HEAD {actual_head}.")
            committed_bytes = git_bytes(root, ["cat-file", "-p", f"{actual_head}:{rel_p}"])
            if helper_path.read_bytes() != committed_bytes:
                raise RehearsalGuardError(f"Helper {rel_p} on disk differs from committed HEAD blob.")

    # Lease & ceiling validation
    lease_id = str(release_doc.get("lease_id") or "").strip()
    if (
        not lease_id
        or lease_id.startswith(REJECTED_LEASE_PREFIXES)
        or "WP-0012" not in lease_id
    ):
        raise RehearsalGuardError(f"Invalid or non-WP-0012 lease_id: {lease_id!r}")

    if release_doc.get("gpu_uuid") != EXPECTED_GPU_UUID:
        raise RehearsalGuardError(f"gpu_uuid {release_doc.get('gpu_uuid')!r} != {EXPECTED_GPU_UUID!r}")

    released_dt = parse_utc_iso(release_doc.get("released_utc", ""), "released_utc")
    expires_dt = parse_utc_iso(release_doc.get("expires_utc", ""), "expires_utc")
    lease_window_s = (expires_dt - released_dt).total_seconds()
    if lease_window_s <= 0 or lease_window_s > GUARD_CEILINGS["max_lease_seconds"]:
        raise RehearsalGuardError(
            f"Lease window ({lease_window_s}s) must be > 0 and <= {GUARD_CEILINGS['max_lease_seconds']}s (6h)."
        )
    if now_utc < released_dt:
        raise RehearsalGuardError(f"Lease released_utc {released_dt.isoformat()} is in the future.")
    remaining_s = (expires_dt - now_utc).total_seconds()
    if remaining_s < GUARD_CEILINGS["min_lease_remaining_seconds"]:
        raise RehearsalGuardError(
            f"Lease expired or has < {GUARD_CEILINGS['min_lease_remaining_seconds']}s remaining ({remaining_s:.1f}s)."
        )

    max_attempts = release_doc.get("max_model_attempts")
    if max_attempts != GUARD_CEILINGS["max_model_attempts"]:
        raise RehearsalGuardError(
            f"WP-0012 author max_model_attempts must be exactly 2, got {max_attempts!r}"
        )

    if release_doc.get("allow_test_content", False) is not False:
        raise RehearsalGuardError("allow_test_content must be false.")
    if release_doc.get("torchvision_local_sha256_TOFU_accepted") is not True:
        raise RehearsalGuardError("torchvision_local_sha256_TOFU_accepted must be true.")

    q0_cfg = Path(str(release_doc.get("readonly_q0_root") or ""))
    rt_raw = release_doc.get("runtime_root") or release_doc.get("writable_runtime_root") or ""
    rt_cfg = Path(str(rt_raw))
    if q0_cfg != EXPECTED_Q0_ROOT:
        raise RehearsalGuardError(f"readonly_q0_root {q0_cfg} != {EXPECTED_Q0_ROOT}")
    if rt_cfg != EXPECTED_DEMO_RUNTIME_ROOT:
        raise RehearsalGuardError(f"runtime_root {rt_cfg} != {EXPECTED_DEMO_RUNTIME_ROOT}")

    ports = release_doc.get("ports")
    if ports != EXPECTED_PORTS:
        raise RehearsalGuardError(f"ports {ports!r} != {EXPECTED_PORTS!r}")

    if release_doc.get("storage_cap_bytes") != GUARD_CEILINGS["storage_cap_bytes"]:
        raise RehearsalGuardError(f"storage_cap_bytes != {GUARD_CEILINGS['storage_cap_bytes']}")
    if release_doc.get("free_floor_bytes") != GUARD_CEILINGS["free_floor_bytes"]:
        raise RehearsalGuardError(f"free_floor_bytes != {GUARD_CEILINGS['free_floor_bytes']}")

    if isinstance(release_doc.get("guards"), dict):
        g = release_doc["guards"]
        for gk, gv in (
            ("load_timeout_s", 1800),
            ("one_page_timeout_s", 1800),
            ("three_page_timeout_s", 3600),
            ("stall_timeout_s", 300),
            ("max_raw_output_bytes", 16_777_216),
            ("max_log_bytes", 67_108_864),
        ):
            if gk in g and g[gk] != gv:
                raise RehearsalGuardError(f"Release guard {gk}={g[gk]!r} != {gv}")

    # Verify coordinator pre-lease observation blobs (raw or LF-normalized SHA-256)
    obs = release_doc.get("observation_files")
    if not isinstance(obs, dict):
        raise RehearsalGuardError("Missing observation_files dict in release JSON.")
    verified_obs: dict[str, dict] = {}
    for req_obs in ("host-before.json", "processes-before.json", "model-before.json"):
        entry = obs.get(req_obs)
        if not isinstance(entry, dict):
            raise RehearsalGuardError(f"Missing observation_files[{req_obs!r}] entry.")
        obs_path = str(entry.get("path") or "").replace("\\", "/")
        obs_sha = str(entry.get("sha256") or "").lower()
        if not obs_path.startswith("docs/coordination/WP-0012/") or not HEX64_RE.match(obs_sha):
            raise RehearsalGuardError(f"Invalid observation_files[{req_obs!r}]: {entry!r}")
        raw_blob = blob_loader(obs_path)
        raw_sha = sha256_bytes(raw_blob)
        lf_sha = sha256_bytes(raw_blob.replace(b"\r\n", b"\n"))
        if obs_sha not in (raw_sha, lf_sha):
            raise RehearsalGuardError(
                f"Observation blob {obs_path} SHA mismatch: expected {obs_sha}, got raw={raw_sha} / lf={lf_sha}"
            )
        verified_obs[req_obs] = {"path": obs_path, "declared_sha256": obs_sha, "raw_sha256": raw_sha}

    return {
        "release_commit": rc,
        "release_path": rel_norm,
        "schema": schema,
        "lease_id": lease_id,
        "gpu_uuid": EXPECTED_GPU_UUID,
        "executing_head": actual_head,
        "source_commit": source_commit,
        "independent_review_002": {rev_key: rev_sha},
        "database": db_target,
        "ports": EXPECTED_PORTS,
        "lease_remaining_seconds": round(remaining_s, 2),
        "verified_observation_files": verified_obs,
        "guard_ceilings": GUARD_CEILINGS,
    }


def observe_ports(ports: tuple[int, ...] = (5590, 4610, 55438)) -> dict[str, list[dict]]:
    ps = (
        "$out = @{}; "
        f"foreach ($p in @({','.join(str(p) for p in ports)})) {{ "
        "$conns = @(Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue | "
        "ForEach-Object { @{ localAddress = $_.LocalAddress; localPort = [int]$_.LocalPort; owningPid = [int]$_.OwningProcess } }); "
        "$out[\"$p\"] = $conns "
        "}; "
        "$out | ConvertTo-Json -Compress -Depth 4"
    )
    out = subprocess.check_output(["pwsh", "-NoProfile", "-Command", ps], cwd=str(REPO_ROOT), text=True, encoding="utf-8")
    return json.loads(out)


def assert_ports_unbound(ports: tuple[int, ...] = (5590, 4610, 55438), timeout_s: float = 15.0) -> dict[str, list[dict]]:
    deadline = time.monotonic() + timeout_s
    latest = observe_ports(ports)
    while time.monotonic() < deadline:
        if all(len(latest[str(p)]) == 0 for p in ports):
            return latest
        time.sleep(0.25)
        latest = observe_ports(ports)
    raise RehearsalGuardError(f"Owned ports not unbound: {latest}")


def count_ocr_worker_processes() -> int:
    self_pid = os.getpid()
    ps = (
        "@(Get-CimInstance Win32_Process | Where-Object { "
        f"$_.ProcessId -ne {self_pid} -and $_.ProcessId -ne $PID -and "
        "$_.Name -like 'python*' -and $_.CommandLine -like '*local_ocr*run_worker*' "
        "}).Count"
    )
    out = subprocess.check_output(["pwsh", "-NoProfile", "-Command", ps], cwd=str(REPO_ROOT), text=True, encoding="utf-8")
    return int(out.strip())


PERSISTED_ATTEMPTS_SQL = """
SELECT COALESCE(json_agg(json_build_object(
  'attempt_id', attempt_id::text,
  'document_id', document_id::text,
  'attempt_number', attempt_number,
  'fencing_token', fencing_token,
  'status', status,
  'phase', phase,
  'run_directory_name', run_directory_name,
  'supervisor_pid', supervisor_pid,
  'supervisor_create_filetime', supervisor_create_filetime,
  'launcher_pid', launcher_pid,
  'launcher_create_filetime', launcher_create_filetime,
  'worker_pid', worker_pid,
  'worker_create_filetime', worker_create_filetime,
  'exit_code', exit_code
) ORDER BY fencing_token), '[]'::json)::text
FROM eledgercare.execution_attempts;
"""


def run_psql_query(settings: dict, db: str, sql: str, as_app_user: bool = False) -> str:
    psql = REPO_ROOT / ".local" / "tools" / "pgsql-18.7-1" / "bin" / "psql.exe"
    user = settings["appUser"] if as_app_user else settings["adminUser"]
    pwd = settings["appPassword"] if as_app_user else settings["adminPassword"]
    cp = subprocess.run(
        [
            str(psql),
            "-X",
            "-q",
            "-A",
            "-t",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            str(settings["host"]),
            "-p",
            str(settings["port"]),
            "-U",
            str(user),
            "-d",
            db,
            "-f",
            "-",
        ],
        cwd=str(REPO_ROOT),
        env={**os.environ, "PGPASSWORD": str(pwd)},
        input=sql,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"psql failed on {db}: {cp.stderr}")
    return cp.stdout.strip()


def run_negative_privilege_probes(settings: dict, db: str) -> dict:
    psql = REPO_ROOT / ".local" / "tools" / "pgsql-18.7-1" / "bin" / "psql.exe"
    probes = [
        "DELETE FROM eledgercare.documents;",
        "UPDATE eledgercare.documents SET submitted_at = now();",
        "DELETE FROM eledgercare.original_artifacts;",
        "DELETE FROM eledgercare.extraction_results;",
        "UPDATE eledgercare.extraction_results SET finish_reason = 'tamper';",
        "DELETE FROM eledgercare.execution_attempts;",
        "DELETE FROM eledgercare.work_order_review_revisions;",
        "UPDATE eledgercare.work_order_review_revisions SET status = 'reviewed';",
        "DELETE FROM eledgercare.work_order_review_fields;",
        "UPDATE eledgercare.archive_result_projections SET unit_count = 99;",
        "DELETE FROM eledgercare.archive_result_projections;",
        "UPDATE eledgercare.archive_projection_units SET search_text = 'tamper';",
        "DELETE FROM eledgercare.archive_projection_units;",
    ]
    denied = 0
    for stmt in probes:
        cp = subprocess.run(
            [
                str(psql),
                "-X",
                "-q",
                "-v",
                "ON_ERROR_STOP=1",
                "-h",
                str(settings["host"]),
                "-p",
                str(settings["port"]),
                "-U",
                str(settings["appUser"]),
                "-d",
                db,
                "-c",
                stmt,
            ],
            cwd=str(REPO_ROOT),
            env={**os.environ, "PGPASSWORD": str(settings["appPassword"])},
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if cp.returncode == 0 or ("permission denied" not in cp.stderr.lower() and "42501" not in cp.stderr):
            raise RehearsalGuardError(f"Privilege probe was not denied with 42501: {stmt} -> {cp.stderr}")
        denied += 1
    return {"probe_count": len(probes), "denied_42501_count": denied, "all_denied": denied == len(probes)}


def start_api_and_ui(
    *,
    app_conn_str: str,
    ocr_enabled: bool,
    leased_gpu_uuid: str,
    log_dir: Path,
    tag: str,
) -> tuple[subprocess.Popen[str], dict, subprocess.Popen[str], dict]:
    assert_ports_unbound((5590, 4610))
    api_dir = REPO_ROOT / "src" / "ELedgerCare.Api" / "bin" / "Release" / "net10.0"
    api_dll = api_dir / "ELedgerCare.Api.dll"
    if not api_dll.is_file():
        raise RehearsalGuardError(f"Release API assembly not found: {api_dll}")

    log_dir.mkdir(parents=True, exist_ok=True)
    api_log = log_dir / f"api-5590-{tag}.log"
    ui_log = log_dir / f"ui-4610-{tag}.log"

    api_env = {
        **os.environ,
        "ASPNETCORE_ENVIRONMENT": "Production",
        "ConnectionStrings__Runtime": app_conn_str,
        "Api__Port": "5590",
        "LocalOcr__Enabled": "true" if ocr_enabled else "false",
        "LocalOcr__MaxExtractionPages": "3",
        "LocalOcr__ReadOnlyQ0Root": str(EXPECTED_Q0_ROOT) if ocr_enabled else "",
        "LocalOcr__WritableRuntimeRoot": str(EXPECTED_DEMO_RUNTIME_ROOT) if ocr_enabled else "",
        "LocalOcr__LeasedGpuUuid": leased_gpu_uuid if ocr_enabled else "",
        "LocalOcr__WorkerRootPath": str(REPO_ROOT / "workers" / "local_ocr") if ocr_enabled else "",
        "DOTNET_NOLOGO": "1",
    }

    api_fh = api_log.open("w", encoding="utf-8", newline="\n")
    api_proc = subprocess.Popen(
        ["dotnet", str(api_dll)],
        cwd=str(api_dir),
        env=api_env,
        stdout=api_fh,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    api_ident = get_win32_process_identity(api_proc.pid)

    deadline = time.monotonic() + 45.0
    while time.monotonic() < deadline:
        if api_proc.poll() is not None:
            api_fh.close()
            raise RuntimeError(f"Owned API exited early ({api_proc.returncode}); see {api_log}")
        ports = observe_ports((5590,))
        if any(c["owningPid"] == api_proc.pid for c in ports["5590"]):
            break
        time.sleep(0.2)
    else:
        api_fh.close()
        raise RuntimeError("Owned API did not bind 5590 within 45s")

    ui_fh = ui_log.open("w", encoding="utf-8", newline="\n")
    ng_bin = REPO_ROOT / "web" / "node_modules" / "@angular" / "cli" / "bin" / "ng.js"
    ui_proc = subprocess.Popen(
        ["node", str(ng_bin), "serve", "--host", "127.0.0.1", "--port", "4610", "--proxy-config", "proxy.conf.mjs"],
        cwd=str(REPO_ROOT / "web"),
        env={**os.environ, "ELEDGERCARE_API_PORT": "5590", "NG_CLI_ANALYTICS": "false"},
        stdout=ui_fh,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    ui_ident = get_win32_process_identity(ui_proc.pid)

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    ui_deadline = time.monotonic() + 90.0
    while time.monotonic() < ui_deadline:
        if ui_proc.poll() is not None:
            ui_fh.close()
            raise RuntimeError(f"Owned UI exited early ({ui_proc.returncode}); see {ui_log}")
        try:
            with opener.open("http://127.0.0.1:4610/", timeout=2.0) as r:
                if r.status == 200:
                    break
        except Exception:
            pass
        time.sleep(0.3)
    else:
        ui_fh.close()
        raise RuntimeError("Owned UI did not respond 200 on 4610 within 90s")

    return (
        api_proc,
        {"pid": api_proc.pid, "identity": api_ident, "ocr_enabled": ocr_enabled, "fh": api_fh, "log": str(api_log)},
        ui_proc,
        {"pid": ui_proc.pid, "identity": ui_ident, "fh": ui_fh, "log": str(ui_log)},
    )


def stop_proc(proc: subprocess.Popen[str] | None, fh=None) -> None:
    try:
        if proc is not None and proc.poll() is None:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], cwd=str(REPO_ROOT), capture_output=True)
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
    finally:
        if fh is not None:
            try:
                fh.close()
            except Exception:
                pass


class ProcessMemorySampler:
    """Background WorkingSet64 peak memory sampler for owned API and any active local_ocr worker processes."""

    def __init__(self, api_pid: int) -> None:
        self.api_pid = api_pid
        self._stop = threading.Event()
        self.api_peak_bytes = 0
        self.worker_peak_bytes = 0
        self.observed_worker_pids: set[int] = set()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> dict:
        self._stop.set()
        self._thread.join(timeout=5.0)
        return {
            "api_pid": self.api_pid,
            "api_peak_working_set_bytes": self.api_peak_bytes,
            "api_peak_working_set_mib": round(self.api_peak_bytes / (1024 * 1024), 2),
            "worker_peak_working_set_bytes": self.worker_peak_bytes,
            "worker_peak_working_set_mib": round(self.worker_peak_bytes / (1024 * 1024), 2),
            "observed_worker_pids": sorted(self.observed_worker_pids),
        }

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                ps = (
                    f"$apiWs = (Get-Process -Id {self.api_pid} -ErrorAction SilentlyContinue).WorkingSet64; "
                    "$workers = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*local_ocr*run_worker*' }); "
                    "$wPids = @($workers | ForEach-Object { [int]$_.ProcessId }); "
                    "$wMax = 0; foreach ($wp in $wPids) { $ws = (Get-Process -Id $wp -ErrorAction SilentlyContinue).WorkingSet64; if ($ws -gt $wMax) { $wMax = $ws } }; "
                    "@{ apiWs = [int64]($apiWs ?? 0); workerMaxWs = [int64]$wMax; workerPids = $wPids } | ConvertTo-Json -Compress"
                )
                cp = subprocess.run(["pwsh", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=4.0)
                if cp.returncode == 0 and cp.stdout.strip():
                    d = json.loads(cp.stdout.strip())
                    self.api_peak_bytes = max(self.api_peak_bytes, int(d.get("apiWs") or 0))
                    self.worker_peak_bytes = max(self.worker_peak_bytes, int(d.get("workerMaxWs") or 0))
                    for wp in d.get("workerPids") or []:
                        self.observed_worker_pids.add(int(wp))
            except Exception:
                pass
            self._stop.wait(2.0)


def run_cpu_dry_run(*, with_disabled_ocr_smoke: bool, output_path: Path | None) -> dict:
    """Executes CPU-only guard, digest, appsettings, Q0 metadata, and optional disabled-OCR Edge smoke."""
    appsettings = json.loads((REPO_ROOT / "src" / "ELedgerCare.Api" / "appsettings.json").read_text(encoding="utf-8"))
    if appsettings.get("LocalOcr", {}).get("Enabled") is not False:
        raise RehearsalGuardError("Default appsettings.json LocalOcr:Enabled must remain false!")
    if appsettings.get("Api", {}).get("Port") != 5590:
        raise RehearsalGuardError("Default appsettings.json Api:Port must be 5590!")

    digests = compute_local_digests(REPO_ROOT)
    for k, exp in EXPECTED_PINNED_DIGESTS.items():
        if digests[k] != exp:
            raise RehearsalGuardError(f"Digest mismatch for {k}: {digests[k]} != {exp}")

    trees = {rel: git_stdout(REPO_ROOT, ["rev-parse", f"HEAD:{rel}"]) for rel in EXPECTED_PRODUCT_TREES}
    for rel, exp_oid in EXPECTED_PRODUCT_TREES.items():
        if trees[rel] != exp_oid:
            raise RehearsalGuardError(f"Tree {rel} drifted: {trees[rel]} != {exp_oid}")

    roots_meta = inspect_readonly_q0_and_demo_roots_cpu(verify_model_sha256=False)

    disabled_smoke_receipt = None
    priv_audit = None
    db_counts = None
    if with_disabled_ocr_smoke:
        settings = json.loads((REPO_ROOT / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
        app_conn = (
            f"Host={settings['host']};Port={settings['port']};Database={OWNED_REHEARSAL_DB};"
            f"Username={settings['appUser']};Password={settings['appPassword']}"
        )
        priv_audit = run_negative_privilege_probes(settings, OWNED_REHEARSAL_DB)

        scratch_dir = REPO_ROOT / ".scratch" / "wp0012-cpu-dryrun"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        api_proc = None
        api_fh = None
        ui_proc = None
        ui_fh = None
        try:
            api_proc, api_meta, ui_proc, ui_meta = start_api_and_ui(
                app_conn_str=app_conn,
                ocr_enabled=False,
                leased_gpu_uuid="",
                log_dir=scratch_dir,
                tag="cpu-preflight",
            )
            api_fh = api_meta["fh"]
            ui_fh = ui_meta["fh"]

            edge_out = scratch_dir / "edge-preflight.json"
            shot_dir = (output_path.parent / "screenshots") if output_path else scratch_dir
            cp = subprocess.run(
                [
                    "node",
                    str(EDGE_DRIVER_PATH),
                    "--mode",
                    "cpu-preflight",
                    "--apiPort",
                    "5590",
                    "--uiPort",
                    "4610",
                    "--output",
                    str(edge_out),
                    "--screenshotDir",
                    str(shot_dir),
                ],
                cwd=str(REPO_ROOT),
                env={**os.environ, "PLAYWRIGHT_BROWSERS_PATH": str(REPO_ROOT / ".local" / "ms-playwright")},
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if cp.returncode != 0:
                raise RuntimeError(f"Edge cpu-preflight failed ({cp.returncode}): {cp.stderr}\n{cp.stdout}")
            disabled_smoke_receipt = json.loads(edge_out.read_text(encoding="utf-8"))
            if count_ocr_worker_processes() != 0:
                raise RehearsalGuardError("Unexpected OCR worker process during CPU dry-run!")
        finally:
            stop_proc(ui_proc, ui_fh)
            stop_proc(api_proc, api_fh)

        raw_counts = run_psql_query(
            settings,
            OWNED_REHEARSAL_DB,
            """
            SELECT json_build_object(
              'documents', (SELECT count(*) FROM eledgercare.documents),
              'execution_attempts', (SELECT count(*) FROM eledgercare.execution_attempts),
              'extraction_results', (SELECT count(*) FROM eledgercare.extraction_results),
              'review_revisions', (SELECT count(*) FROM eledgercare.work_order_review_revisions)
            )::text;
            """,
        )
        db_counts = json.loads(raw_counts)
        if any(v != 0 for v in db_counts.values()):
            raise RehearsalGuardError(f"Expected 0 rows in {OWNED_REHEARSAL_DB} after CPU dry-run, got: {db_counts}")
        attempts_smoke = json.loads(run_psql_query(settings, OWNED_REHEARSAL_DB, PERSISTED_ATTEMPTS_SQL))
        if attempts_smoke != []:
            raise RehearsalGuardError(f"Expected empty persisted attempts array in CPU dry-run, got: {attempts_smoke}")

    result = {
        "schema": "eledgercare.wp0012-cpu-dryrun-receipt/1",
        "verified_utc": utc_now(),
        "mode": "cpu-dry-run",
        "live_model_imported_or_invoked": False,
        "gpu_queries_or_inference_run": False,
        "branch": git_stdout(REPO_ROOT, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "head_sha": git_stdout(REPO_ROOT, ["rev-parse", "HEAD"]),
        "product_trees_verified": trees,
        "pinned_digests_verified": digests,
        "guard_ceilings_bound": GUARD_CEILINGS,
        "default_appsettings_ocr_disabled": True,
        "roots_inspection": roots_meta,
        "owned_rehearsal_database": OWNED_REHEARSAL_DB,
        "runtime_privilege_audit": priv_audit,
        "owned_rehearsal_database_row_counts": db_counts,
        "disabled_ocr_edge_preflight": disabled_smoke_receipt,
    }
    if output_path is not None:
        write_json_lf(output_path, result)
    return result


def execute_live_rehearsal(*, release_commit: str, release_path: str) -> dict:
    """Strictly gated live 2-attempt rehearsal execution for WP-0012 / 003."""
    rc = release_commit.strip().lower()
    rel_norm = release_path.strip().replace("\\", "/")
    if not git_object_exists(REPO_ROOT, f"{rc}:{rel_norm}"):
        raise RehearsalGuardError(f"Release JSON object {rc}:{rel_norm} does not exist in Git.")

    rel_doc = json.loads(git_bytes(REPO_ROOT, ["cat-file", "-p", f"{rc}:{rel_norm}"]).decode("utf-8"))
    validated = validate_release_contract(
        rel_doc,
        root=REPO_ROOT,
        release_commit=rc,
        release_path=rel_norm,
        now_utc=utc_now_dt(),
        blob_loader=lambda p: git_bytes(REPO_ROOT, ["cat-file", "-p", f"{rc}:{p}"]),
        commit_exists_fn=lambda sha: git_object_exists(REPO_ROOT, f"{sha}^{{commit}}"),
        database_name=OWNED_REHEARSAL_DB,
        require_clean_worktree=True,
    )

    # Full SHA-256 check on all 18 read-only Q0 model files before starting live trial
    pre_roots = inspect_readonly_q0_and_demo_roots_cpu(verify_model_sha256=True)
    if not pre_roots["writable_demo_root_exists"]:
        raise RehearsalGuardError(
            f"Writable runtime root {EXPECTED_DEMO_RUNTIME_ROOT} does not exist yet; coordinator must create/release it first."
        )

    runs_dir = EXPECTED_DEMO_RUNTIME_ROOT / "runs"
    prior_run_dirs = set(p.name for p in runs_dir.iterdir() if p.is_dir()) if runs_dir.is_dir() else set()
    ev_out_dir = EXPECTED_DEMO_RUNTIME_ROOT / "rehearsal-evidence" / validated["lease_id"]
    shot_dir = ev_out_dir / "screenshots"
    logs_dir = ev_out_dir / "logs"
    ev_out_dir.mkdir(parents=True, exist_ok=True)

    assert_ports_unbound((5590, 4610, 55438))
    settings = json.loads((REPO_ROOT / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
    app_conn = (
        f"Host={settings['host']};Port={settings['port']};Database={OWNED_REHEARSAL_DB};"
        f"Username={settings['appUser']};Password={settings['appPassword']}"
    )

    pg_started = False
    api_proc = None
    api_fh = None
    ui_proc = None
    ui_fh = None
    sampler: ProcessMemorySampler | None = None
    recorded_service_identities: list[dict] = []

    try:
        subprocess.run(
            ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"],
            cwd=str(REPO_ROOT),
            check=True,
        )
        pg_started = True
        pg_pid_1 = int((REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0])
        recorded_service_identities.append({"role": "postgres-phase-a", **(get_win32_process_identity(pg_pid_1) or {"pid": pg_pid_1})})

        # Ensure owned rehearsal DB is migrated and has 0 prior attempts before starting the 2-attempt ceiling
        subprocess.run(
            ["pwsh", "-NoProfile", "-File", "deploy/dev/database/prepare-database.ps1", "-Database", OWNED_REHEARSAL_DB],
            cwd=str(REPO_ROOT),
            check=True,
        )
        pre_attempts = int(run_psql_query(settings, OWNED_REHEARSAL_DB, "SELECT count(*) FROM eledgercare.execution_attempts;"))
        if pre_attempts != 0:
            raise RehearsalGuardError(f"Expected 0 existing attempts in {OWNED_REHEARSAL_DB}, found {pre_attempts}")

        # Phase A: Leased live execution (process-local LocalOcr__Enabled=true)
        api_proc, api_meta_a, ui_proc, ui_meta_a = start_api_and_ui(
            app_conn_str=app_conn,
            ocr_enabled=True,
            leased_gpu_uuid=EXPECTED_GPU_UUID,
            log_dir=logs_dir,
            tag="phase-a-leased",
        )
        api_fh = api_meta_a["fh"]
        ui_fh = ui_meta_a["fh"]
        recorded_service_identities.append({"role": "api-phase-a", **(api_meta_a["identity"] or {"pid": api_proc.pid})})
        recorded_service_identities.append({"role": "ui-phase-a", **(ui_meta_a["identity"] or {"pid": ui_proc.pid})})

        sampler = ProcessMemorySampler(api_proc.pid)
        sampler.start()

        phase_a_json = ev_out_dir / "phase-a-live-browser.json"
        state_file = ev_out_dir / "rehearsal-state.json"
        cp_a = subprocess.run(
            [
                "node",
                str(EDGE_DRIVER_PATH),
                "--mode",
                "live-phase-a",
                "--apiPort",
                "5590",
                "--uiPort",
                "4610",
                "--output",
                str(phase_a_json),
                "--stateFile",
                str(state_file),
                "--screenshotDir",
                str(shot_dir),
            ],
            cwd=str(REPO_ROOT),
            env={**os.environ, "PLAYWRIGHT_BROWSERS_PATH": str(REPO_ROOT / ".local" / "ms-playwright")},
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        (logs_dir / "phase-a-edge.log").write_text(cp_a.stdout + "\n" + cp_a.stderr, encoding="utf-8", newline="\n")
        mem_stats = sampler.stop()
        sampler = None
        if cp_a.returncode != 0:
            raise RuntimeError(f"Live Phase A stopped/failed (exit={cp_a.returncode}); see {logs_dir / 'phase-a-edge.log'}")

        # Query persisted attempt/launcher/worker PIDs & CreateFileTime before stopping Phase A
        persisted_attempts = json.loads(run_psql_query(settings, OWNED_REHEARSAL_DB, PERSISTED_ATTEMPTS_SQL))
        if len(persisted_attempts) != 2:
            raise RehearsalGuardError(f"Expected exactly 2 persisted execution_attempts, found {len(persisted_attempts)}")

        # Stop Phase A services and verify all model/worker processes & PostgreSQL cluster stop cleanly
        stop_proc(ui_proc, ui_fh)
        ui_proc, ui_fh = None, None
        stop_proc(api_proc, api_fh)
        api_proc, api_fh = None, None

        for att in persisted_attempts:
            if att.get("launcher_pid") and att.get("launcher_create_filetime"):
                if is_exact_process_alive(int(att["launcher_pid"]), int(att["launcher_create_filetime"])):
                    raise RehearsalGuardError(f"Launcher PID {att['launcher_pid']} still alive after Phase A stop!")
            if att.get("worker_pid") and att.get("worker_create_filetime"):
                if is_exact_process_alive(int(att["worker_pid"]), int(att["worker_create_filetime"])):
                    raise RehearsalGuardError(f"Worker PID {att['worker_pid']} still alive after Phase A stop!")

        if count_ocr_worker_processes() != 0:
            raise RehearsalGuardError("Active local_ocr python worker detected after Phase A shutdown!")

        subprocess.run(
            ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"],
            cwd=str(REPO_ROOT),
            check=True,
        )
        pg_started = False
        assert_ports_unbound((5590, 4610, 55438))

        # Phase B: Restart PostgreSQL + API with LocalOcr__Enabled=false & re-verify saved workflow in Edge
        subprocess.run(
            ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"],
            cwd=str(REPO_ROOT),
            check=True,
        )
        pg_started = True
        pg_pid_2 = int((REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0])
        recorded_service_identities.append({"role": "postgres-phase-b", **(get_win32_process_identity(pg_pid_2) or {"pid": pg_pid_2})})

        api_proc, api_meta_b, ui_proc, ui_meta_b = start_api_and_ui(
            app_conn_str=app_conn,
            ocr_enabled=False,
            leased_gpu_uuid="",
            log_dir=logs_dir,
            tag="phase-b-ocr-disabled",
        )
        api_fh = api_meta_b["fh"]
        ui_fh = ui_meta_b["fh"]
        recorded_service_identities.append({"role": "api-phase-b-ocr-disabled", **(api_meta_b["identity"] or {"pid": api_proc.pid})})
        recorded_service_identities.append({"role": "ui-phase-b", **(ui_meta_b["identity"] or {"pid": ui_proc.pid})})

        phase_b_json = ev_out_dir / "phase-b-disabled-ocr-reopen.json"
        cp_b = subprocess.run(
            [
                "node",
                str(EDGE_DRIVER_PATH),
                "--mode",
                "live-phase-b-reopen",
                "--apiPort",
                "5590",
                "--uiPort",
                "4610",
                "--stateFile",
                str(state_file),
                "--output",
                str(phase_b_json),
                "--screenshotDir",
                str(shot_dir),
            ],
            cwd=str(REPO_ROOT),
            env={**os.environ, "PLAYWRIGHT_BROWSERS_PATH": str(REPO_ROOT / ".local" / "ms-playwright")},
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        (logs_dir / "phase-b-edge.log").write_text(cp_b.stdout + "\n" + cp_b.stderr, encoding="utf-8", newline="\n")
        if cp_b.returncode != 0:
            raise RuntimeError(f"Live Phase B reopen failed (exit={cp_b.returncode}); see {logs_dir / 'phase-b-edge.log'}")

        post_attempts = int(run_psql_query(settings, OWNED_REHEARSAL_DB, "SELECT count(*) FROM eledgercare.execution_attempts;"))
        if post_attempts != 2:
            raise RehearsalGuardError(f"Attempt count changed across disabled-OCR restart ({post_attempts} != 2)!")

        phase_a_data = json.loads(phase_a_json.read_text(encoding="utf-8"))
        phase_b_data = json.loads(phase_b_json.read_text(encoding="utf-8"))
        if (
            phase_a_data["preRestartArchiveVerification"]["savedQueryCanonicalSha256"]
            != phase_b_data["postRestartArchiveVerification"]["savedQueryCanonicalSha256"]
        ):
            raise RehearsalGuardError("Saved archive query canonical digest differed after API+PG restart!")

        stop_proc(ui_proc, ui_fh)
        ui_proc, ui_fh = None, None
        stop_proc(api_proc, api_fh)
        api_proc, api_fh = None, None
        subprocess.run(
            ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"],
            cwd=str(REPO_ROOT),
            check=True,
        )
        pg_started = False
        final_ports = assert_ports_unbound((5590, 4610, 55438))

        post_roots = inspect_readonly_q0_and_demo_roots_cpu(verify_model_sha256=True)
        new_run_dirs = sorted((set(p.name for p in runs_dir.iterdir() if p.is_dir()) if runs_dir.is_dir() else set()) - prior_run_dirs)

        lease_return = {
            "schema": "eledgercare.wp0012-owner-lease-return/1",
            "returned_utc": utc_now(),
            "owner": EXPECTED_OWNER,
            "lease_id": validated["lease_id"],
            "gpu_uuid": EXPECTED_GPU_UUID,
            "model_attempts_executed": len(persisted_attempts),
            "persisted_attempts": persisted_attempts,
            "new_run_directories": new_run_dirs,
            "prior_run_directories_preserved": sorted(prior_run_dirs),
            "recorded_service_identities": recorded_service_identities,
            "memory_telemetry": mem_stats,
            "ocr_worker_processes_running": count_ocr_worker_processes(),
            "ports_after_shutdown": final_ports,
            "q0_model_18_objects_sha256_verified_after_run": True,
        }
        write_json_lf(ev_out_dir / "owner-lease-return.json", lease_return)
        return lease_return
    finally:
        if sampler is not None:
            sampler.stop()
        stop_proc(ui_proc, ui_fh)
        stop_proc(api_proc, api_fh)
        if pg_started:
            subprocess.run(
                ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"],
                cwd=str(REPO_ROOT),
                capture_output=True,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="WP-0012 complete-workflow rehearsal driver & guard validator.")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--cpu-dry-run", action="store_true", help="Run CPU-only dry-run guard validation (never invokes model).")
    mode_group.add_argument("--validate-release", action="store_true", help="Pure CPU/Git validation of coordinator release JSON.")
    mode_group.add_argument("--execute-live", action="store_true", help="Execute gated 2-attempt live rehearsal under coordinator lease.")

    parser.add_argument("--with-disabled-ocr-smoke", action="store_true", help="Include disabled-OCR API/UI/Edge preflight on owned empty DB.")
    parser.add_argument("--release-commit", type=str, default="", help="40-hex coordinator release commit SHA.")
    parser.add_argument("--release-path", type=str, default="", help="Git-relative path to coordinator WP-0012 release JSON.")
    parser.add_argument("--output", type=str, default="", help="Optional JSON output path.")
    args = parser.parse_args()

    out_path = Path(args.output).resolve() if args.output else None

    if args.cpu_dry_run:
        res = run_cpu_dry_run(with_disabled_ocr_smoke=args.with_disabled_ocr_smoke, output_path=out_path)
        print(f"CPU dry-run validation PASSED (live_model={res['live_model_imported_or_invoked']}, db={OWNED_REHEARSAL_DB}).")
        return

    if not args.release_commit or not args.release_path:
        print("ERROR: --release-commit and --release-path are required for --validate-release and --execute-live.", file=sys.stderr)
        sys.exit(2)

    if args.validate_release:
        rc = args.release_commit.strip().lower()
        rel_norm = args.release_path.strip().replace("\\", "/")
        if rc in REJECTED_RELEASE_COMMITS:
            raise RehearsalGuardError(
                f"Authority commit {rc} is historical or CPU-preparation-only and cannot authorize live inference."
            )
        if not git_object_exists(REPO_ROOT, f"{rc}:{rel_norm}"):
            raise RehearsalGuardError(f"Git object {rc}:{rel_norm} not found.")
        rel_doc = json.loads(git_bytes(REPO_ROOT, ["cat-file", "-p", f"{rc}:{rel_norm}"]).decode("utf-8"))
        res = validate_release_contract(
            rel_doc,
            root=REPO_ROOT,
            release_commit=rc,
            release_path=rel_norm,
            now_utc=utc_now_dt(),
            blob_loader=lambda p: git_bytes(REPO_ROOT, ["cat-file", "-p", f"{rc}:{p}"]),
            commit_exists_fn=lambda sha: git_object_exists(REPO_ROOT, f"{sha}^{{commit}}"),
        )
        if out_path is not None:
            write_json_lf(out_path, res)
        print(f"Release contract validation PASSED for lease {res['lease_id']}.")
        return

    if args.execute_live:
        res = execute_live_rehearsal(release_commit=args.release_commit, release_path=args.release_path)
        if out_path is not None:
            write_json_lf(out_path, res)
        print(f"Live 2-attempt rehearsal COMPLETED and lease {res['lease_id']} returned cleanly.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
