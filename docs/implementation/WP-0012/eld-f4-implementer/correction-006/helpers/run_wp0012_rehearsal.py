"""Complete-workflow demonstration rehearsal orchestrator & fail-closed guard validator (WP-0012 / 006).

Owner: eld-f4-implementer, native continuation /root/product_author_continuation.
Partial original author: Carbon/high b7c54417-db09-49bd-8d2b-7cc808f113be, preserved at d9de3bf.
Native backend/actual effort unexposed; requested effort xhigh.

Bounded WP-0012 / 006 corrections over immutable /001 helper (ad5202a0):
  - F12-B1: Internal partial-startup cleanup in `start_api_and_ui` terminating every already-spawned
    owned child (verified by Win32 PID + CreateFileTime) and closing every opened log handle.
  - F12-B2: Refusing pre-existing decisive output destinations (`guard_decisive_output_destinations`),
    pre-launch `count_ocr_worker_processes() == 0` guard, and unified failure-path / completion-path
    `persisted_attempts` query, launcher/worker exit check, `count_ocr_worker_processes() == 0` check,
    `assert_ports_unbound((5590, 4610, 55438))`, post-run Q0 model check, log secret scrubbing, and
    honest `owner-lease-return.json` emission (`status: "completed" | "failed_stopped"`).
  - F12-B3 & /007 gate: Exact release-key compatibility (including `"accepted_preparation_review"`,
    `"accepted_review_007"`, `"independent_preparation_review_007_sha"`, and `/001`'s
    `"independent_preparation_review_002_sha"`), explicit rejection of `changes-requested` WP-0012 / 002
    (`379d8c5d607fd248d7f272e412b4ed4a97bc64f6`) and all pre-`/006` ancestors, and executable synthetic
    sample validation (`--validate-synthetic-sample`) strictly isolated from live validation/execution.
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
import urllib.parse
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
CORRECTION_DIR = HELPERS_DIR.parent
AUTHOR_WP0012_DIR = CORRECTION_DIR.parent
REPO_ROOT = resolve_repo_root(HELPERS_DIR)
EDGE_DRIVER_PATH = HELPERS_DIR / "drive_rehearsal_edge.mjs"

if str(REPO_ROOT / "workers" / "local_ocr") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "workers" / "local_ocr"))

from local_ocr.protocol import (  # noqa: E402
    DEPENDENCY_LOCK_PATH,
    MODEL_MANIFEST_PATH,
    compute_config_digest,
    compute_worker_source_sha256,
)
from local_ocr.verify_runtime import (  # noqa: E402
    normalize_and_verify_model_dir,
    verify_model_sources_ast_safety,
)

HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
REPORT_STATUS_RE = re.compile(r"^-\s*Status:\s*([A-Za-z0-9_-]+)\s*$", re.MULTILINE)

EXPECTED_PACKET = "WP-0012"
EXPECTED_OWNER = "eld-f4-implementer"
EXPECTED_CONVERSATION_ID = "/root/product_author_continuation"
EXPECTED_MODEL = "native-codex-backend-unexposed"
EXPECTED_EFFORT = "xhigh-requested"
EXPECTED_BRANCH = "rehearsal/wp-0012-product"
EXPECTED_GPU_UUID = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"

ACCEPTED_PACKET_BASE_SHA = "73c8d3c4f0a00312e3444328331b6cbd6406e882"
ACCEPTED_F4_FINAL_SOURCE_SHA = "c1fed68020ae67e8b4763bc6ea5473adaa86de2b"
PREPARATION_DISPATCH_AUTHORITY_SHA = "47fbc7612e4a08cf1960ad7ac01bd2843ae645e5"
CORRECTION_006_DISPATCH_AUTHORITY_SHA = "598b9e80c317a9fe3d8288732fc19d3a05219cbc"
PRIOR_AUTHOR_001_DELIVERABLE_SHA = "ad5202a029a7a86bea5fa3e3d97760d0a9cc673a"
PRIOR_AUTHOR_001_EVIDENCE_SHA = "32465da577237827c3ac9d8ed5ee608c8e5668cf"
PRIOR_AUTHOR_001_PUBLICATION_SHA = "165b2421b297bf49181c91af8d05a449ad69e9b5"
PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA = "379d8c5d607fd248d7f272e412b4ed4a97bc64f6"
CORRECTION_006_BASE_SHA = PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA

SYNTHETIC_PLACEHOLDER_EXECUTING_HEAD = "6666666666666666666666666666666666666666"
SYNTHETIC_PLACEHOLDER_ACCEPTING_007 = "7777777777777777777777777777777777777777"
SYNTHETIC_PLACEHOLDER_RELEASE_COMMIT = "8888888888888888888888888888888888888888"

SYNTHETIC_SAMPLE_BLOBS: dict[str, bytes] = {
    "docs/coordination/WP-0012-0013/synthetic-author-003/ownership-before.json": (
        b'{"schema": "eld-wp12-wp13-ownership-observation/1", "synthetic_test_only": true, '
        b'"gpu_exit": 0, "apps_exit": 0, "apps": [], "candidate_and_gpu_processes": [], '
        b'"ollama_ps_exit": 0, "ollama_ps": []}\n'
    ),
    "docs/coordination/WP-0012-0013/synthetic-author-003/host-before.json": (
        b'{"status": "pass", "synthetic_test_only": true, "free_space": {"free_bytes": 42949672960}}\n'
    ),
    "docs/coordination/WP-0012-0013/synthetic-author-003/model-before.json": (
        b'{"ok": true, "synthetic_test_only": true, "model_objects": 18, "notice_verified": true}\n'
    ),
}

ALLOWED_SOURCE_COMMITS = frozenset({
    ACCEPTED_F4_FINAL_SOURCE_SHA,
    ACCEPTED_PACKET_BASE_SHA,
})

# Historical, CPU-preparation, or non-accepting review commits that can NEVER satisfy an accepting /007 gate
NON_ACCEPTING_REVIEW_COMMITS = frozenset({
    PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA,
    "8eec97ce301059f81ffacb04fc0144b3c33a248e",
    "0cabb137e71454d13342148a5652a5034df018ba",
    "d437fbf69e4ae2246f4e170f90bf5a5df2ef1a02",
    "d4bbfec29c201a1c1d3dda7881afc6029cbf88cb",
    "cb4189aced6f38b269d8a90fa362b92058852bd0",
    "7f3f8626489e898a50d275e93ee904660e97fd59",
    "c09cf1aa8282e440e364c6020152dd257355643b",
    "234878326696800a16cb901913dbf732268578ea",
    PRIOR_AUTHOR_001_PUBLICATION_SHA,
    PRIOR_AUTHOR_001_EVIDENCE_SHA,
    PRIOR_AUTHOR_001_DELIVERABLE_SHA,
    "7a1bdea970d84df297a07593a50184b32f766255",
    "51cf3ecc23a1bb847f8ea7618fb9960b5d18f325",
})

REJECTED_RELEASE_COMMITS = frozenset({
    *NON_ACCEPTING_REVIEW_COMMITS,
    PREPARATION_DISPATCH_AUTHORITY_SHA,
    CORRECTION_006_DISPATCH_AUTHORITY_SHA,
    "7af4cd0e2e8ffbcb9176fc78508b6cd601c16fc0",
    "dec2d6476b770b9b5ee1774100d3df391c8c53d5",
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
    "ELedgerCare.slnx",
    "qualification/",
    "research/",
    "evaluation/",
    "AGENTS.md",
    "START_HERE.md",
    "CURRENT.md",
    "INDEX.md",
    "docs/implementation/WP-0006/",
    "docs/implementation/WP-0008/",
    "docs/implementation/WP-0010/",
    "docs/reviews/WP-0006/",
    "docs/reviews/WP-0008/",
    "docs/reviews/WP-0010/",
    "docs/reviews/WP-0011/",
    "docs/reviews/WP-0013/",
    "docs/agent-reports/eld-f4-implementer/WP-0010/",
)

ALLOWED_COORDINATION_PREFIXES = (
    "docs/coordination/WP-0012/",
    "docs/coordination/WP-0012-0013/",
)

PROCESS_OWNERSHIP_OBS_NAMES = frozenset({
    "processes-before.json",
    "ownership-before.json",
    "ownership.json",
    "processes.json",
})
MODEL_OBS_NAMES = frozenset({
    "model-before.json",
    "model.json",
})

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


def load_local_secrets(settings: dict | None = None) -> list[str]:
    out: list[str] = []
    try:
        cfg = settings or json.loads((REPO_ROOT / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
    except Exception:
        return out
    for key in ("adminPassword", "migratorPassword", "appPassword"):
        val = str(cfg.get(key) or "")
        if val:
            out.append(val)
            quoted = urllib.parse.quote(val, safe="")
            if quoted and quoted != val:
                out.append(quoted)
    # Longest tokens first so substrings never partially mask longer secrets
    return sorted(set(out), key=len, reverse=True)


def scrub_text(text: str, secrets: list[str] | None) -> str:
    if not text:
        return text
    cleaned = text
    for sec in secrets or []:
        if sec:
            if len(sec) < 4:
                cleaned = re.sub(r"(?<![\w])" + re.escape(sec) + r"(?![\w])", "[REDACTED]", cleaned)
            else:
                cleaned = cleaned.replace(sec, "[REDACTED]")
    cleaned = re.sub(r"(?i)(Password\s*=\s*)([^\s;\"']+)", r"\1[REDACTED]", cleaned)
    return cleaned


def scrub_file_secrets(path: Path, secrets: list[str] | None) -> bool:
    if not path.is_file() or is_reparse_point(path):
        return False
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise RuntimeError(f"Unable to read log for scrubbing: {path}") from exc
    cleaned = scrub_text(raw, secrets)
    if cleaned != raw:
        path.write_text(cleaned, encoding="utf-8", newline="\n")
        return True
    return False


def scrub_directory_secrets(directory: Path, secrets: list[str] | None) -> int:
    if not directory.is_dir() or is_reparse_point(directory):
        return 0
    touched = 0
    for fp in sorted(directory.rglob("*")):
        if fp.is_file() and fp.suffix.lower() in (".log", ".txt", ".json", ".md"):
            if scrub_file_secrets(fp, secrets):
                touched += 1
    return touched


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
        expected_bytes = int(entry["size"])
        fpath = model_dir / rel_name
        if not fpath.is_file() or is_reparse_point(fpath):
            raise RehearsalGuardError(f"Model file missing or reparse point: {fpath}")
        stat_size = fpath.stat().st_size
        if stat_size != expected_bytes:
            raise RehearsalGuardError(f"Model file size mismatch on {rel_name}: {stat_size} != {expected_bytes}")
        checked_count += 1
        total_model_bytes += stat_size

    if verify_model_sha256:
        normalize_and_verify_model_dir(str(model_dir), str(notice_dir), manifest)
        verify_model_sources_ast_safety(model_dir)

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


def _extract_accepting_preparation_review_sha(release_doc: dict) -> tuple[str, str]:
    """Extracts the accepting independent review commit SHA (WP-0012 / 007) across all documented keys (F12-B3)."""
    candidate_keys = (
        "accepted_preparation_review",
        "accepted_preparation_review_sha",
        "accepted_review_007",
        "independent_preparation_review_007_sha",
        "independent_review_007",
        "accepted_007",
        "independent_preparation_review_sha",
        "accepted_review",
        "independent_preparation_review_002_sha",
        "accepted_review_002",
        "independent_review_002",
        "accepted_002",
        "preparation_review",
    )
    for key in candidate_keys:
        val = release_doc.get(key)
        if isinstance(val, str) and val.strip():
            return key, val.strip().lower()
        if isinstance(val, dict):
            disp = val.get("disposition") or val.get("status")
            if disp is not None and str(disp).strip().lower() != "accepted":
                raise RehearsalGuardError(
                    f"Review binding '{key}' has non-accepting disposition {disp!r}; "
                    f"live execution requires independent 'accepted' WP-0012 / 007 review."
                )
            for sub in ("commit", "sha", "publication", "report"):
                sval = val.get(sub)
                if isinstance(sval, str) and sval.strip():
                    return f"{key}.{sub}", sval.strip().lower()
    raise RehearsalGuardError(
        "Missing independent accepting WP-0012 / 007 review commit binding "
        "(e.g. accepted_preparation_review / accepted_review_007 / independent_preparation_review_002_sha) in release JSON."
    )


# Backward-compatible symbol alias
_extract_independent_review_002_sha = _extract_accepting_preparation_review_sha


def _commit_inspects_as_accepting_007(root: Path, commit_sha: str) -> tuple[bool, str | None]:
    """If commit_sha exists in local Git, checks any WP-0012 / 007 reviewer report inside it for Status: accepted."""
    if not git_object_exists(root, f"{commit_sha}^{{commit}}"):
        return False, None
    try:
        files = [
            ln.strip()
            for ln in git_stdout(
                root,
                ["ls-tree", "-r", "--name-only", commit_sha, "docs/agent-reports/eld-f4-reviewer/WP-0012"],
            ).splitlines()
            if ln.strip()
        ]
    except Exception:
        return False, None
    report_007_paths = [
        p for p in files if Path(p).name.startswith("007_") and p.endswith("_review_eld-f4-reviewer.md")
    ]
    if not report_007_paths:
        return False, None
    for rp in report_007_paths:
        txt = git_bytes(root, ["cat-file", "-p", f"{commit_sha}:{rp}"]).decode("utf-8", errors="replace")
        m = REPORT_STATUS_RE.search(txt)
        status_val = m.group(1).strip().lower() if m else "missing"
        if status_val != "accepted":
            return False, f"Reviewer report {rp} in {commit_sha} has Status: {status_val!r} (expected 'accepted')."
    return True, None


def guard_decisive_output_destinations(
    ev_out_dir: Path,
    explicit_output_path: Path | None = None,
    *,
    repo_root: Path = REPO_ROOT,
) -> None:
    """Refuses overwriting existing decisive rehearsal outputs or writing into immutable/protected directories (F12-B2)."""
    for anc in (ev_out_dir.absolute(), *ev_out_dir.absolute().parents):
        if anc.exists() and is_reparse_point(anc):
            raise RehearsalGuardError(f"Reparse point/symlink forbidden on output path: {anc}")
    ev_resolved = ev_out_dir.resolve()
    for anc in (ev_resolved, *ev_resolved.parents):
        if anc.exists() and is_reparse_point(anc):
            raise RehearsalGuardError(f"Reparse point/symlink forbidden on output path: {anc}")
    if ev_resolved.exists():
        raise RehearsalGuardError(
            f"Decisive rehearsal output directory already exists and will not be overwritten: {ev_resolved}"
        )

    if explicit_output_path is not None:
        for anc in (explicit_output_path.absolute(), *explicit_output_path.absolute().parents):
            if anc.exists() and is_reparse_point(anc):
                raise RehearsalGuardError(f"Reparse point/symlink forbidden on --output path: {anc}")
        out_res = explicit_output_path.resolve()
        for anc in (out_res, *out_res.parents):
            if anc.exists() and is_reparse_point(anc):
                raise RehearsalGuardError(f"Reparse point/symlink forbidden on --output path: {anc}")
        if out_res.exists():
            raise RehearsalGuardError(f"Refusing to overwrite existing --output target: {out_res}")

        protected_roots = [
            EXPECTED_Q0_ROOT.resolve(),
            (repo_root / "src").resolve(),
            (repo_root / "web").resolve(),
            (repo_root / "tests").resolve(),
            (repo_root / "deploy").resolve(),
            (repo_root / "workers").resolve(),
            (repo_root / "qualification").resolve(),
            (repo_root / "research").resolve(),
            (repo_root / "evaluation").resolve(),
            (repo_root / "docs" / "reviews").resolve(),
            (repo_root / "docs" / "agent-reports").resolve(),
            (repo_root / "docs" / "implementation" / "WP-0006").resolve(),
            (repo_root / "docs" / "implementation" / "WP-0008").resolve(),
            (repo_root / "docs" / "implementation" / "WP-0010").resolve(),
            (AUTHOR_WP0012_DIR / "evidence").resolve(),
            (AUTHOR_WP0012_DIR / "helpers").resolve(),
            (AUTHOR_WP0012_DIR / "retained-failures").resolve(),
            CORRECTION_DIR.resolve(),
        ]
        protected_files = {
            (AUTHOR_WP0012_DIR / "RUNBOOK.md").resolve(),
            (AUTHOR_WP0012_DIR / "inventory.json").resolve(),
            (AUTHOR_WP0012_DIR / "resource-return.json").resolve(),
            (AUTHOR_WP0012_DIR / ".gitattributes").resolve(),
        }
        if out_res in protected_files or any(
            out_res == pr or out_res.is_relative_to(pr) for pr in protected_roots
        ):
            raise RehearsalGuardError(
                f"Refusing to write live --output into protected/immutable repository path: {out_res}"
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
    allow_synthetic_test_only: bool = False,
) -> dict:
    """Pure CPU/Git fail-closed validator for a coordinator WP-0012 sole-GPU runtime release."""
    is_synth = bool(release_doc.get("synthetic_test_only", False))
    if is_synth and not allow_synthetic_test_only:
        raise RehearsalGuardError(
            "Release JSON is marked synthetic_test_only=true and cannot authorize live validation or execution."
        )

    rc = release_commit.strip().lower()
    if not HEX40_RE.match(rc):
        raise RehearsalGuardError(f"release_commit must be a 40-char lowercase hex SHA, got {release_commit!r}")
    if rc in REJECTED_RELEASE_COMMITS or (not is_synth and rc == SYNTHETIC_PLACEHOLDER_RELEASE_COMMIT):
        raise RehearsalGuardError(
            f"Authority commit {rc} is historical, synthetic, or CPU-preparation-only and cannot authorize live inference."
        )

    rel_norm = release_path.strip().replace("\\", "/")
    if (
        not rel_norm.startswith(ALLOWED_COORDINATION_PREFIXES)
        or not rel_norm.endswith(".json")
        or ".." in rel_norm.split("/")
    ):
        raise RehearsalGuardError(
            f"release_path must be a JSON path under docs/coordination/WP-0012*/, got {release_path!r}"
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
    if (
        not HEX40_RE.match(executing_head)
        or executing_head in REJECTED_RELEASE_COMMITS
        or (not is_synth and executing_head == SYNTHETIC_PLACEHOLDER_EXECUTING_HEAD)
    ):
        raise RehearsalGuardError(f"Invalid, synthetic, or pre-/006 executing_head: {executing_head!r}")

    actual_head = git_stdout(root, ["rev-parse", "HEAD"]).lower()
    actual_branch = git_stdout(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    if require_clean_worktree and actual_branch != EXPECTED_BRANCH:
        raise RehearsalGuardError(f"Owned branch must be {EXPECTED_BRANCH!r}, got {actual_branch!r}")
    porcelain = git_stdout(root, ["status", "--porcelain", "--untracked-files=all"])
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
    if not git_is_ancestor(root, CORRECTION_006_BASE_SHA, actual_head):
        raise RehearsalGuardError(
            f"Correction /006 base {CORRECTION_006_BASE_SHA} is not an ancestor of {actual_head}."
        )

    changed_since_authority = [
        ln.strip()
        for ln in git_stdout(root, ["diff", "--name-only", PREPARATION_DISPATCH_AUTHORITY_SHA, actual_head]).splitlines()
        if ln.strip()
    ]
    forbidden_touched = [p for p in changed_since_authority if p.startswith(FORBIDDEN_DIFF_PREFIXES)]
    if forbidden_touched:
        raise RehearsalGuardError(f"Forbidden paths modified since dispatch authority: {forbidden_touched}")

    mutated_prior_artifacts = [
        ln.strip()
        for ln in git_stdout(
            root,
            ["diff", "--diff-filter=MD", "--name-only", CORRECTION_006_BASE_SHA, actual_head],
        ).splitlines()
        if ln.strip()
    ]
    if mutated_prior_artifacts:
        raise RehearsalGuardError(
            f"Immutable /001, /002, or base files modified/deleted since {CORRECTION_006_BASE_SHA}: {mutated_prior_artifacts}"
        )

    if "prior_changes_requested_review_002" in release_doc:
        prior_002 = str(release_doc.get("prior_changes_requested_review_002") or "").strip().lower()
        if prior_002 != PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA:
            raise RehearsalGuardError(
                f"prior_changes_requested_review_002 {prior_002!r} != {PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA!r}"
            )

    rev_key, rev_sha = _extract_accepting_preparation_review_sha(release_doc)
    if not HEX40_RE.match(rev_sha) or (not is_synth and rev_sha == SYNTHETIC_PLACEHOLDER_ACCEPTING_007):
        raise RehearsalGuardError(f"Invalid or synthetic accepting review SHA in {rev_key}: {rev_sha!r}")
    if rev_sha in NON_ACCEPTING_REVIEW_COMMITS or rev_sha in REJECTED_RELEASE_COMMITS:
        raise RehearsalGuardError(
            f"Review commit {rev_sha} ({rev_key}) is earlier changes-requested WP-0012 / 002 or historical/preparation commit; "
            f"live execution requires independent accepting WP-0012 / 007 review."
        )
    if git_object_exists(root, f"{rev_sha}^{{commit}}") and git_is_ancestor(root, rev_sha, CORRECTION_006_BASE_SHA):
        raise RehearsalGuardError(
            f"Review commit {rev_sha} ({rev_key}) predates WP-0012 / 006 ({CORRECTION_006_BASE_SHA}); "
            f"live execution requires independent accepting WP-0012 / 007 review."
        )
    if not commit_exists_fn(rev_sha):
        raise RehearsalGuardError(f"Accepting review commit in {rev_key} not found in Git: {rev_sha!r}")

    has_accepting_007, bad_007_reason = _commit_inspects_as_accepting_007(root, rev_sha)
    if bad_007_reason:
        raise RehearsalGuardError(bad_007_reason)
    if not has_accepting_007 and (rev_sha == actual_head or not (is_synth and allow_synthetic_test_only)):
        raise RehearsalGuardError(
            f"Accepting review commit {rev_sha} has no accepted independent WP-0012 / 007 report."
        )

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
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", lease_id)
        or lease_id.startswith(REJECTED_LEASE_PREFIXES)
        or "WP-0012" not in lease_id
        or (not is_synth and "SYNTHETIC" in lease_id.upper())
    ):
        raise RehearsalGuardError(f"Invalid, synthetic, or non-WP-0012 lease_id: {lease_id!r}")

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

    # Verify coordinator pre-lease observation blobs (supports both WP-0012/ and WP-0012-0013/ layouts)
    obs = release_doc.get("observation_files")
    if not isinstance(obs, dict) or not obs:
        raise RehearsalGuardError("Missing or empty observation_files dict in release JSON.")
    verified_obs: dict[str, dict] = {}
    has_ownership_obs = False
    has_model_obs = False
    for obs_key, entry in obs.items():
        if not isinstance(entry, dict):
            raise RehearsalGuardError(f"Invalid observation_files[{obs_key!r}] entry.")
        obs_path = str(entry.get("path") or "").replace("\\", "/")
        obs_sha = str(entry.get("sha256") or "").lower()
        if (
            not obs_path.startswith(ALLOWED_COORDINATION_PREFIXES)
            or ".." in obs_path.split("/")
            or not HEX64_RE.match(obs_sha)
        ):
            raise RehearsalGuardError(f"Invalid observation_files[{obs_key!r}]: {entry!r}")
        raw_blob = blob_loader(obs_path)
        raw_sha = sha256_bytes(raw_blob)
        lf_sha = sha256_bytes(raw_blob.replace(b"\r\n", b"\n"))
        if obs_sha not in (raw_sha, lf_sha):
            raise RehearsalGuardError(
                f"Observation blob {obs_path} SHA-256 mismatch: expected {obs_sha}, got raw={raw_sha} / lf={lf_sha}"
            )
        verified_obs[obs_key] = {"path": obs_path, "declared_sha256": obs_sha, "raw_sha256": raw_sha}
        base_names = {obs_key.lower(), Path(obs_path).name.lower()}
        if base_names & PROCESS_OWNERSHIP_OBS_NAMES:
            has_ownership_obs = True
        if base_names & MODEL_OBS_NAMES:
            has_model_obs = True

    if not has_ownership_obs or not has_model_obs:
        raise RehearsalGuardError(
            "observation_files must include both a process/ownership snapshot "
            "(ownership-before.json / processes-before.json) and a model snapshot (model-before.json / model.json)."
        )

    return {
        "release_commit": rc,
        "release_path": rel_norm,
        "schema": schema,
        "synthetic_test_only": is_synth,
        "lease_id": lease_id,
        "gpu_uuid": EXPECTED_GPU_UUID,
        "executing_head": actual_head,
        "source_commit": source_commit,
        "accepting_preparation_review": {rev_key: rev_sha},
        "prior_changes_requested_review_002": PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA,
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


def stop_proc(
    proc: subprocess.Popen[str] | None,
    fh=None,
    *,
    expected_identity: dict | None = None,
) -> None:
    """Terminates an owned child process (verifying Win32 PID + CreateFileTime before taskkill) and closes its log handle."""
    try:
        if proc is not None and proc.poll() is None:
            can_taskkill_tree = False
            pid = int(proc.pid)
            if expected_identity and expected_identity.get("create_filetime") is not None:
                can_taskkill_tree = is_exact_process_alive(pid, int(expected_identity["create_filetime"]))
            else:
                ident_now = get_win32_process_identity(pid)
                can_taskkill_tree = bool(ident_now and ident_now.get("alive"))

            if can_taskkill_tree:
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        cwd=str(REPO_ROOT), capture_output=True, check=False, timeout=15,
                    )
                except Exception:
                    # Popen's retained process handle still identifies our original child.
                    pass
            if proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    pass
            if proc.poll() is None:
                try:
                    proc.kill()
                    proc.wait(timeout=10)
                except Exception:
                    pass
            else:
                try:
                    proc.wait(timeout=10)
                except Exception:
                    pass
            if proc.poll() is None:
                raise RuntimeError(f"Owned child {pid} did not exit after cleanup")
    finally:
        if fh is not None and not getattr(fh, "closed", False):
            try:
                fh.flush()
            finally:
                fh.close()


def start_api_and_ui(
    *,
    app_conn_str: str,
    ocr_enabled: bool,
    leased_gpu_uuid: str,
    log_dir: Path,
    tag: str,
    secrets: list[str] | None = None,
) -> tuple[subprocess.Popen[str], dict, subprocess.Popen[str], dict]:
    """Starts owned API (5590) and UI (4610) atomically; cleans up every spawned child and handle on partial failure (F12-B1)."""
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

    api_fh = None
    api_proc: subprocess.Popen[str] | None = None
    api_ident: dict | None = None
    ui_fh = None
    ui_proc: subprocess.Popen[str] | None = None
    ui_ident: dict | None = None

    try:
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
                raise RuntimeError(f"Owned API exited early ({api_proc.returncode}); see {api_log}")
            ports = observe_ports((5590,))
            if any(c["owningPid"] == api_proc.pid for c in ports["5590"]):
                break
            time.sleep(0.2)
        else:
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
            if api_proc.poll() is not None:
                raise RuntimeError(f"Owned API exited unexpectedly during UI startup ({api_proc.returncode}); see {api_log}")
            if ui_proc.poll() is not None:
                raise RuntimeError(f"Owned UI exited early ({ui_proc.returncode}); see {ui_log}")
            try:
                with opener.open("http://127.0.0.1:4610/", timeout=2.0) as r:
                    if r.status == 200:
                        break
            except Exception:
                pass
            time.sleep(0.3)
        else:
            raise RuntimeError("Owned UI did not respond 200 on 4610 within 90s")

        return (
            api_proc,
            {"pid": api_proc.pid, "identity": api_ident, "ocr_enabled": ocr_enabled, "fh": api_fh, "log": str(api_log)},
            ui_proc,
            {"pid": ui_proc.pid, "identity": ui_ident, "fh": ui_fh, "log": str(ui_log)},
        )
    except BaseException as exc:
        cleanup_errors = []
        for role, proc, fh, ident in (("ui", ui_proc, ui_fh, ui_ident), ("api", api_proc, api_fh, api_ident)):
            try:
                stop_proc(proc, fh, expected_identity=ident)
            except Exception as stop_exc:
                cleanup_errors.append(f"partial_start_{role}_stop_failed: {stop_exc}")
        for log in (api_log, ui_log):
            try:
                scrub_file_secrets(log, secrets)
            except Exception as scrub_exc:
                cleanup_errors.append(f"partial_start_scrub_failed: {scrub_exc}")
        exc.startup_cleanup_errors = cleanup_errors
        for error in cleanup_errors:
            exc.add_note(scrub_text(error, secrets))
        raise


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
        secrets = load_local_secrets(settings)
        app_conn = (
            f"Host={settings['host']};Port={settings['port']};Database={OWNED_REHEARSAL_DB};"
            f"Username={settings['appUser']};Password={settings['appPassword']}"
        )
        priv_audit = run_negative_privilege_probes(settings, OWNED_REHEARSAL_DB)

        scratch_dir = REPO_ROOT / ".scratch" / "wp0012-cpu-dryrun-006"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        api_proc = None
        api_meta: dict | None = None
        ui_proc = None
        ui_meta: dict | None = None
        try:
            api_proc, api_meta, ui_proc, ui_meta = start_api_and_ui(
                app_conn_str=app_conn,
                ocr_enabled=False,
                leased_gpu_uuid="",
                log_dir=scratch_dir,
                tag="cpu-preflight-006",
                secrets=secrets,
            )

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
            stop_proc(
                ui_proc,
                ui_meta["fh"] if ui_meta else None,
                expected_identity=ui_meta.get("identity") if ui_meta else None,
            )
            stop_proc(
                api_proc,
                api_meta["fh"] if api_meta else None,
                expected_identity=api_meta.get("identity") if api_meta else None,
            )
            scrub_directory_secrets(scratch_dir, secrets)

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
        "helper_revision_namespace": "correction-006",
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


def _collect_lingering_attempt_processes(persisted_attempts: list[dict], grace_s: float = 5.0) -> list[dict]:
    deadline = time.monotonic() + grace_s
    while True:
        lingering: list[dict] = []
        for att in persisted_attempts:
            if att.get("launcher_pid") and att.get("launcher_create_filetime"):
                if is_exact_process_alive(int(att["launcher_pid"]), int(att["launcher_create_filetime"])):
                    lingering.append(
                        {
                            "role": "launcher",
                            "attempt_id": att.get("attempt_id"),
                            "pid": int(att["launcher_pid"]),
                            "create_filetime": int(att["launcher_create_filetime"]),
                        }
                    )
            if att.get("worker_pid") and att.get("worker_create_filetime"):
                if is_exact_process_alive(int(att["worker_pid"]), int(att["worker_create_filetime"])):
                    lingering.append(
                        {
                            "role": "worker",
                            "attempt_id": att.get("attempt_id"),
                            "pid": int(att["worker_pid"]),
                            "create_filetime": int(att["worker_create_filetime"]),
                        }
                    )
        if not lingering or time.monotonic() >= deadline:
            return lingering
        time.sleep(0.25)


def execute_live_rehearsal(
    *,
    release_commit: str,
    release_path: str,
    explicit_output_path: Path | None = None,
) -> dict:
    """Strictly gated live 2-attempt rehearsal execution for WP-0012 / 003 (after accepting /007 review)."""
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
        allow_synthetic_test_only=False,
    )

    pre_roots = inspect_readonly_q0_and_demo_roots_cpu(verify_model_sha256=True)
    if not pre_roots["writable_demo_root_exists"]:
        raise RehearsalGuardError(
            f"Writable runtime root {EXPECTED_DEMO_RUNTIME_ROOT} does not exist yet; coordinator must create/release it first."
        )

    ev_out_dir = EXPECTED_DEMO_RUNTIME_ROOT / "rehearsal-evidence" / validated["lease_id"]
    guard_decisive_output_destinations(ev_out_dir, explicit_output_path, repo_root=REPO_ROOT)

    assert_ports_unbound((5590, 4610, 55438))
    pre_workers = count_ocr_worker_processes()
    if pre_workers != 0:
        raise RehearsalGuardError(
            f"Refusing live rehearsal start: {pre_workers} local_ocr worker process(es) already active."
        )

    runs_dir = EXPECTED_DEMO_RUNTIME_ROOT / "runs"
    prior_run_dirs = set(p.name for p in runs_dir.iterdir() if p.is_dir()) if runs_dir.is_dir() else set()
    shot_dir = ev_out_dir / "screenshots"
    logs_dir = ev_out_dir / "logs"
    ev_out_dir.mkdir(parents=True, exist_ok=False)
    logs_dir.mkdir(parents=True, exist_ok=False)

    settings = json.loads((REPO_ROOT / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
    secrets = load_local_secrets(settings)
    app_conn = (
        f"Host={settings['host']};Port={settings['port']};Database={OWNED_REHEARSAL_DB};"
        f"Username={settings['appUser']};Password={settings['appPassword']}"
    )

    pg_started = False
    api_proc: subprocess.Popen[str] | None = None
    api_meta: dict | None = None
    ui_proc: subprocess.Popen[str] | None = None
    ui_meta: dict | None = None
    sampler: ProcessMemorySampler | None = None
    mem_stats: dict | None = None
    recorded_service_identities: list[dict] = []
    persisted_attempts: list[dict] = []
    persisted_attempts_queried = False
    failure_stage: str | None = "init"
    failure_exc: BaseException | None = None
    cleanup_errors: list[str] = []
    lease_return: dict = {}

    try:
        failure_stage = "postgres-phase-a-start"
        pg_started = True
        subprocess.run(
            ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"],
            cwd=str(REPO_ROOT),
            check=True,
        )
        pg_started = True
        pg_pid_1 = int((REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0])
        recorded_service_identities.append({"role": "postgres-phase-a", **(get_win32_process_identity(pg_pid_1) or {"pid": pg_pid_1})})

        failure_stage = "prepare-rehearsal-database"
        subprocess.run(
            ["pwsh", "-NoProfile", "-File", "deploy/dev/database/prepare-database.ps1", "-Database", OWNED_REHEARSAL_DB],
            cwd=str(REPO_ROOT),
            check=True,
        )
        pre_attempts = int(run_psql_query(settings, OWNED_REHEARSAL_DB, "SELECT count(*) FROM eledgercare.execution_attempts;"))
        if pre_attempts != 0:
            raise RehearsalGuardError(f"Expected 0 existing attempts in {OWNED_REHEARSAL_DB}, found {pre_attempts}")

        failure_stage = "phase-a-service-startup"
        api_proc, api_meta, ui_proc, ui_meta = start_api_and_ui(
            app_conn_str=app_conn,
            ocr_enabled=True,
            leased_gpu_uuid=EXPECTED_GPU_UUID,
            log_dir=logs_dir,
            tag="phase-a-leased",
            secrets=secrets,
        )
        recorded_service_identities.append({"role": "api-phase-a", **(api_meta["identity"] or {"pid": api_proc.pid})})
        recorded_service_identities.append({"role": "ui-phase-a", **(ui_meta["identity"] or {"pid": ui_proc.pid})})

        sampler = ProcessMemorySampler(api_proc.pid)
        sampler.start()

        failure_stage = "phase-a-live-browser"
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
        (logs_dir / "phase-a-edge.log").write_text(
            scrub_text(cp_a.stdout + "\n" + cp_a.stderr, secrets),
            encoding="utf-8",
            newline="\n",
        )
        mem_stats = sampler.stop()
        sampler = None
        if cp_a.returncode != 0:
            raise RuntimeError(f"Live Phase A stopped/failed (exit={cp_a.returncode}); see {logs_dir / 'phase-a-edge.log'}")

        failure_stage = "phase-a-attempt-audit"
        persisted_attempts = json.loads(run_psql_query(settings, OWNED_REHEARSAL_DB, PERSISTED_ATTEMPTS_SQL))
        persisted_attempts_queried = True
        if len(persisted_attempts) != 2:
            raise RehearsalGuardError(f"Expected exactly 2 persisted execution_attempts, found {len(persisted_attempts)}")

        failure_stage = "phase-a-shutdown"
        stop_proc(ui_proc, ui_meta["fh"] if ui_meta else None, expected_identity=ui_meta.get("identity") if ui_meta else None)
        ui_proc, ui_meta = None, None
        stop_proc(api_proc, api_meta["fh"] if api_meta else None, expected_identity=api_meta.get("identity") if api_meta else None)
        api_proc, api_meta = None, None

        lingering_a = _collect_lingering_attempt_processes(persisted_attempts, grace_s=5.0)
        if lingering_a:
            raise RehearsalGuardError(f"Attempt launcher/worker processes still alive after Phase A stop: {lingering_a}")
        if count_ocr_worker_processes() != 0:
            raise RehearsalGuardError("Active local_ocr python worker detected after Phase A shutdown!")

        subprocess.run(
            ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"],
            cwd=str(REPO_ROOT),
            check=True,
        )
        pg_started = False
        assert_ports_unbound((5590, 4610, 55438))

        failure_stage = "phase-b-postgres-restart"
        pg_started = True
        subprocess.run(
            ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"],
            cwd=str(REPO_ROOT),
            check=True,
        )
        pg_started = True
        pg_pid_2 = int((REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0])
        recorded_service_identities.append({"role": "postgres-phase-b", **(get_win32_process_identity(pg_pid_2) or {"pid": pg_pid_2})})

        failure_stage = "phase-b-service-startup-ocr-disabled"
        api_proc, api_meta, ui_proc, ui_meta = start_api_and_ui(
            app_conn_str=app_conn,
            ocr_enabled=False,
            leased_gpu_uuid="",
            log_dir=logs_dir,
            tag="phase-b-ocr-disabled",
            secrets=secrets,
        )
        recorded_service_identities.append({"role": "api-phase-b-ocr-disabled", **(api_meta["identity"] or {"pid": api_proc.pid})})
        recorded_service_identities.append({"role": "ui-phase-b", **(ui_meta["identity"] or {"pid": ui_proc.pid})})

        failure_stage = "phase-b-disabled-ocr-reopen"
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
        (logs_dir / "phase-b-edge.log").write_text(
            scrub_text(cp_b.stdout + "\n" + cp_b.stderr, secrets),
            encoding="utf-8",
            newline="\n",
        )
        if cp_b.returncode != 0:
            raise RuntimeError(f"Live Phase B reopen failed (exit={cp_b.returncode}); see {logs_dir / 'phase-b-edge.log'}")

        failure_stage = "phase-b-post-checks"
        post_attempts = int(run_psql_query(settings, OWNED_REHEARSAL_DB, "SELECT count(*) FROM eledgercare.execution_attempts;"))
        if post_attempts != 2:
            raise RehearsalGuardError(f"Attempt count changed across disabled-OCR restart ({post_attempts} != 2)!")

        persisted_attempts = json.loads(run_psql_query(settings, OWNED_REHEARSAL_DB, PERSISTED_ATTEMPTS_SQL))
        persisted_attempts_queried = True

        phase_a_data = json.loads(phase_a_json.read_text(encoding="utf-8"))
        phase_b_data = json.loads(phase_b_json.read_text(encoding="utf-8"))
        if phase_b_data.get("verifiedWorkerEnabledFalseFromApi") is not True:
            raise RehearsalGuardError("Phase B receipt missing verifiedWorkerEnabledFalseFromApi === true!")
        if (
            phase_a_data["preRestartArchiveVerification"]["savedQueryCanonicalSha256"]
            != phase_b_data["postRestartArchiveVerification"]["savedQueryCanonicalSha256"]
        ):
            raise RehearsalGuardError("Saved archive query canonical digest differed after API+PG restart!")

        failure_stage = None
    except BaseException as exc:
        failure_exc = exc
        cleanup_errors.extend(getattr(exc, "startup_cleanup_errors", []))
    finally:
        if sampler is not None:
            try:
                mem_stats = sampler.stop()
            except Exception as s_exc:
                cleanup_errors.append(f"memory_sampler_stop_failed: {s_exc}")

        # Stop producers before the final attempt query so startup/phase failures cannot race the audit.
        for role, proc, meta in (("ui", ui_proc, ui_meta), ("api", api_proc, api_meta)):
            try:
                stop_proc(proc, meta["fh"] if meta else None, expected_identity=meta.get("identity") if meta else None)
            except Exception as stop_exc:
                cleanup_errors.append(f"{role}_stop_failed: {stop_exc}")

        if pg_started:
            try:
                raw_att = run_psql_query(settings, OWNED_REHEARSAL_DB, PERSISTED_ATTEMPTS_SQL)
                parsed_att = json.loads(raw_att)
                if not isinstance(parsed_att, list):
                    raise RuntimeError("Persisted attempts query did not return a list")
                persisted_attempts = parsed_att
                persisted_attempts_queried = True
            except Exception as q_exc:
                persisted_attempts_queried = False
                cleanup_errors.append(f"persisted_attempts_query_failed: {q_exc}")

        lingering_final = []
        try:
            lingering_final = _collect_lingering_attempt_processes(persisted_attempts, grace_s=5.0)
            if lingering_final:
                cleanup_errors.append(f"lingering_attempt_processes: {lingering_final}")
        except Exception as audit_exc:
            cleanup_errors.append(f"attempt_process_audit_failed: {audit_exc}")

        ocr_workers_after = -1
        try:
            ocr_workers_after = count_ocr_worker_processes()
            if ocr_workers_after != 0:
                cleanup_errors.append(f"ocr_worker_processes_running={ocr_workers_after}")
        except Exception as w_exc:
            cleanup_errors.append(f"count_ocr_worker_processes_failed: {w_exc}")

        if pg_started:
            try:
                cp_stop_pg = subprocess.run(
                    ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"],
                    cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8", check=False, timeout=45,
                )
                if cp_stop_pg.returncode != 0:
                    cleanup_errors.append(f"postgres_stop_failed ({cp_stop_pg.returncode}): {cp_stop_pg.stderr.strip()}")
            except Exception as pg_exc:
                cleanup_errors.append(f"postgres_stop_failed: {pg_exc}")

        lingering_services = []
        for identity in recorded_service_identities:
            try:
                if identity.get("create_filetime") is None:
                    cleanup_errors.append(f"service_identity_missing: {identity['role']}")
                elif is_exact_process_alive(int(identity["pid"]), int(identity["create_filetime"])):
                    lingering_services.append(identity)
            except Exception as identity_exc:
                cleanup_errors.append(f"service_identity_check_failed: {identity_exc}")
        if lingering_services:
            cleanup_errors.append(f"lingering_service_processes: {lingering_services}")

        ports_unbound_verified = False
        final_ports: dict[str, list[dict]] = {}
        try:
            final_ports = assert_ports_unbound((5590, 4610, 55438))
            ports_unbound_verified = True
        except Exception as p_exc:
            cleanup_errors.append(f"ports_not_unbound: {p_exc}")
            try:
                final_ports = observe_ports((5590, 4610, 55438))
            except Exception:
                final_ports = {}

        q0_model_verified = False
        try:
            inspect_readonly_q0_and_demo_roots_cpu(verify_model_sha256=True)
            q0_model_verified = True
        except Exception as m_exc:
            cleanup_errors.append(f"post_run_q0_model_check_failed: {m_exc}")

        new_run_dirs = []
        try:
            new_run_dirs = sorted(
                (set(p.name for p in runs_dir.iterdir() if p.is_dir()) if runs_dir.is_dir() else set()) - prior_run_dirs
            )
        except Exception as dir_exc:
            cleanup_errors.append(f"run_directory_audit_failed: {dir_exc}")
        scrubbed_count = 0
        logs_scrubbed = False
        try:
            scrubbed_count = scrub_directory_secrets(ev_out_dir, secrets)
            logs_scrubbed = True
        except Exception as scrub_exc:
            cleanup_errors.append(f"log_scrub_failed: {scrub_exc}")

        clean_return_ok = (
            ocr_workers_after == 0
            and len(lingering_final) == 0
            and ports_unbound_verified
            and q0_model_verified
            and len(cleanup_errors) == 0
        )
        final_status = "completed" if (failure_exc is None and clean_return_ok) else "failed_stopped"

        receipt_utc = utc_now()
        lease_return = {
            "schema": "eledgercare.wp0012-owner-lease-return/1",
            "status": final_status,
            "clean_return_verified": clean_return_ok,
            "failure_stage": failure_stage if failure_exc is not None else ("cleanup" if cleanup_errors else None),
            "failure_error": scrub_text(str(failure_exc), secrets) if failure_exc is not None else None,
            "cleanup_errors": [scrub_text(err, secrets) for err in cleanup_errors],
            "receipt_utc": receipt_utc,
            "lease_returned": clean_return_ok,
            "returned_utc": receipt_utc if clean_return_ok else None,
            "owner": EXPECTED_OWNER,
            "lease_id": validated["lease_id"],
            "gpu_uuid": EXPECTED_GPU_UUID,
            "model_attempts_executed": len(persisted_attempts) if persisted_attempts_queried else None,
            "persisted_attempts_query_verified": persisted_attempts_queried,
            "persisted_attempts": persisted_attempts,
            "lingering_attempt_processes": lingering_final,
            "lingering_service_processes": lingering_services,
            "new_run_directories": new_run_dirs,
            "prior_run_directories_preserved": sorted(prior_run_dirs),
            "recorded_service_identities": recorded_service_identities,
            "memory_telemetry": mem_stats,
            "ocr_worker_processes_running": ocr_workers_after,
            "ports_after_shutdown": final_ports,
            "ports_unbound_verified": ports_unbound_verified,
            "q0_model_18_objects_sha256_verified_after_run": q0_model_verified,
            "logs_scrubbed": logs_scrubbed,
            "scrubbed_artifact_count": scrubbed_count,
        }
        write_json_lf(ev_out_dir / "owner-lease-return.json", lease_return)
        scrub_file_secrets(ev_out_dir / "owner-lease-return.json", secrets)
        if explicit_output_path is not None:
            write_json_lf(explicit_output_path, lease_return)
            scrub_file_secrets(explicit_output_path, secrets)

    if failure_exc is not None:
        raise failure_exc
    if not lease_return.get("clean_return_verified", False):
        raise RehearsalGuardError(f"Post-run resource return verification failed: {cleanup_errors}")
    return lease_return


def validate_synthetic_sample_file(sample_path: Path, *, output_path: Path | None = None) -> dict:
    """Validates an explicitly synthetic sample release envelope on CPU and proves live mode rejects it."""
    raw_doc = json.loads(sample_path.read_text(encoding="utf-8"))
    if raw_doc.get("synthetic_test_only") is not True:
        raise RehearsalGuardError("Sample file must declare synthetic_test_only: true.")

    actual_head = git_stdout(REPO_ROOT, ["rev-parse", "HEAD"]).lower()
    doc_for_cpu = dict(raw_doc)
    if doc_for_cpu.get("executing_head") == SYNTHETIC_PLACEHOLDER_EXECUTING_HEAD:
        doc_for_cpu["executing_head"] = actual_head

    sample_now = datetime(2026, 11, 17, 16, 30, 0, tzinfo=timezone.utc)
    validated_synth = validate_release_contract(
        doc_for_cpu,
        root=REPO_ROOT,
        release_commit=SYNTHETIC_PLACEHOLDER_RELEASE_COMMIT,
        release_path="docs/coordination/WP-0012/releases/synthetic-sample.json",
        now_utc=sample_now,
        blob_loader=lambda p: SYNTHETIC_SAMPLE_BLOBS[p],
        commit_exists_fn=lambda sha: sha == SYNTHETIC_PLACEHOLDER_ACCEPTING_007
        or git_object_exists(REPO_ROOT, f"{sha}^{{commit}}"),
        require_clean_worktree=False,
        allow_synthetic_test_only=True,
    )

    live_rejected = False
    try:
        validate_release_contract(
            doc_for_cpu,
            root=REPO_ROOT,
            release_commit=SYNTHETIC_PLACEHOLDER_RELEASE_COMMIT,
            release_path="docs/coordination/WP-0012/releases/synthetic-sample.json",
            now_utc=sample_now,
            blob_loader=lambda p: SYNTHETIC_SAMPLE_BLOBS[p],
            commit_exists_fn=lambda _: True,
            require_clean_worktree=False,
            allow_synthetic_test_only=False,
        )
    except RehearsalGuardError:
        live_rejected = True

    if not live_rejected:
        raise RehearsalGuardError("Synthetic sample envelope was NOT rejected when allow_synthetic_test_only=False!")

    out = {
        "synthetic_sample_validated_on_cpu": True,
        "live_mode_rejected_synthetic_sample": True,
        "validated_contract": validated_synth,
    }
    if output_path is not None:
        write_json_lf(output_path, out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="WP-0012 / 006 complete-workflow rehearsal driver & guard validator.")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--cpu-dry-run", action="store_true", help="Run CPU-only dry-run guard validation (never invokes model).")
    mode_group.add_argument("--validate-synthetic-sample", type=str, metavar="JSON_PATH", help="Validate synthetic CPU sample envelope and prove live rejection.")
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

    if args.validate_synthetic_sample:
        res = validate_synthetic_sample_file(Path(args.validate_synthetic_sample).resolve(), output_path=out_path)
        print(f"Synthetic sample contract validation PASSED (live_rejected={res['live_mode_rejected_synthetic_sample']}).")
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
            allow_synthetic_test_only=False,
        )
        if out_path is not None:
            write_json_lf(out_path, res)
        print(f"Release contract validation PASSED for lease {res['lease_id']}.")
        return

    if args.execute_live:
        res = execute_live_rehearsal(
            release_commit=args.release_commit,
            release_path=args.release_path,
            explicit_output_path=out_path,
        )
        print(f"Live 2-attempt rehearsal COMPLETED and lease {res['lease_id']} returned cleanly.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
