"""Bounded CPU-only saved-result completion runner v3 (eld-f2-implementer, WP-0006).

Authorized by coordinator commit 6dec634c81a4b2cbc1b492541697958cc0f76232
(docs/kickoffs/WP-0006-eld-f2-saved-result-completion.md) after returned/acknowledged GPU lease
WP-0006-author-corrected-20261116T154140Z and published v2 runtime evidence
48e8896d53fa001bba55276ac244f4adee377587.

Strict CPU-only / read-only invariants:
  - ZERO CUDA/GPU/nvidia-smi queries, ZERO ML/PDF Python package imports, ZERO worker subprocesses.
  - ZERO touches of external runtime roots (C:\\Users\\jackg\\eLedgerCare-F2 or eLedgerCare-Q0).
  - ZERO POST requests, retries, database writes, or resets; strictly read-only GET HTTP endpoints
    and read-only SELECT snapshots on existing eledgercare_f2_runtime_author_v2 database.
  - Starts ELedgerCare.Api with LocalOcr__Enabled=false throughout, verifies all 3 saved documents
    and 4 attempt records before and after a clean PostgreSQL 18.7 fast restart + API restart,
    verifies actual headless Microsoft Edge rendering + cell-by-cell attempt-row status labels
    ('Extraction interrupted' / 'Completed (unreviewed)') + original PDF downloads, proves 0 new
    attempts via before/after table digests, and stops all owned services cleanly.
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
import socket
import subprocess
import sys
import time
import urllib.error
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
SCRIPT_DIR = SCRIPT_PATH.parent
ROOT = resolve_repo_root(SCRIPT_DIR)
UI_HELPER_PATH = SCRIPT_DIR / "verify_saved_results_ui_v3.mjs"

if str(ROOT / "workers" / "local_ocr") not in sys.path:
    sys.path.insert(0, str(ROOT / "workers" / "local_ocr"))

from local_ocr.protocol import (  # noqa: E402
    MODEL_REPO_ID,
    MODEL_REVISION,
    compute_config_digest,
    compute_worker_source_sha256,
    sha256_bytes,
)

EXPECTED_AUTHORITY_COMMIT = "6dec634c81a4b2cbc1b492541697958cc0f76232"
EXPECTED_KICKOFF_PATH = "docs/kickoffs/WP-0006-eld-f2-saved-result-completion.md"
EXPECTED_SOURCE_COMMIT = "8a73b7a5dab51e3ccf803aceedded4929529dd35"
EXPECTED_V2_EVIDENCE_BASE = "48e8896d53fa001bba55276ac244f4adee377587"
DATABASE_NAME = "eledgercare_f2_runtime_author_v2"
PORTS = {"api": 5190, "ui": 4210, "postgres": 55434}

UI_STATUS_LABELS: dict[str, str] = {
    "awaiting_extraction": "Awaiting extraction",
    "queued": "Queued for extraction",
    "running": "Extraction running",
    "completed": "Completed (unreviewed)",
    "failed": "Extraction failed",
    "interrupted": "Extraction interrupted",
}

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
    "docs/implementation/WP-0006/runtime-corrected-preparation": "3ec263bd7dc408e662887b2273429566d6fbb08d",
    "docs/implementation/WP-0006/runtime-author-v2": "83234b5c96aa2ec6c8a18ee6dbe3370a68e70b92",
}

EXPECTED_PINNED_DIGESTS: dict[str, str] = {
    "model_manifest_sha256": "0df07bc60abf6937c917040bced32afabd7e4d11bafc0bd99902abca610a81be",
    "dependency_lock_sha256": "582071bf20eaca1836c3d1cef21d31cbdaa1e1407184033a918a40612c128111",
    "worker_source_sha256": "c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54",
    "worker_config_1p_sha256": "579aad63a9893a58466baf005ea63f87e92540d4c1f71f6b3c399e8b1e6b35ff",
    "worker_config_3p_sha256": "ac90459ca4011b5859cfdd0b224d5ea247489b7c01775118736df7c1c9819e86",
}

PINNED_SAVED_DOCUMENTS: list[dict] = [
    {
        "label": "Doc 1: SYN-WO-01-v1-raster300 (1 page)",
        "documentId": "01a1e509-f496-737c-901f-2b6a8fb84094",
        "expectedJobId": "01a1e509-f496-78a6-b971-1345754d00ec",
        "expectedResultId": "01a1e50c-910f-7de0-9ce7-21a709200e52",
        "expectedWinningAttemptId": "01a1e509-f5d4-7a01-80f1-4f23fe282930",
        "expectedPages": 1,
        "expectedOriginalBytes": 372258,
        "expectedOriginalSha256": "47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd",
        "expectedRawBytes": 3236,
        "expectedRawSha256": "7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95",
        "expectedWorkerConfigSha256": EXPECTED_PINNED_DIGESTS["worker_config_1p_sha256"],
        "committedRawFileRel": (
            "docs/implementation/WP-0006/runtime-author-v2/runs/"
            "attempt-01a1e509-f5d4-7a01-80f1-4f23fe282930/output/raw_output.utf8.bin"
        ),
        "expectedAttempts": [
            {
                "attemptNumber": 1,
                "attemptId": "01a1e509-f5d4-7a01-80f1-4f23fe282930",
                "fencingToken": 1,
                "apiStatus": "completed",
                "expectedUiLabel": UI_STATUS_LABELS["completed"],
                "phase": "completed",
                "retriedFromAttemptId": None,
                "failureCode": None,
            }
        ],
    },
    {
        "label": "Doc 2: SYN-MP-01-v0-clean (3 pages)",
        "documentId": "01a1e50c-bd99-775e-8748-dc55022f4b04",
        "expectedJobId": "01a1e50c-bd99-7b98-985f-41ecaf9b2609",
        "expectedResultId": "01a1e511-aab6-71ae-bb23-1f7a9cdb4f8b",
        "expectedWinningAttemptId": "01a1e50c-bdb9-7477-a96a-abb58323c615",
        "expectedPages": 3,
        "expectedOriginalBytes": 8422,
        "expectedOriginalSha256": "15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3",
        "expectedRawBytes": 7511,
        "expectedRawSha256": "c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639",
        "expectedWorkerConfigSha256": EXPECTED_PINNED_DIGESTS["worker_config_3p_sha256"],
        "committedRawFileRel": (
            "docs/implementation/WP-0006/runtime-author-v2/runs/"
            "attempt-01a1e50c-bdb9-7477-a96a-abb58323c615/output/raw_output.utf8.bin"
        ),
        "expectedAttempts": [
            {
                "attemptNumber": 1,
                "attemptId": "01a1e50c-bdb9-7477-a96a-abb58323c615",
                "fencingToken": 2,
                "apiStatus": "completed",
                "expectedUiLabel": UI_STATUS_LABELS["completed"],
                "phase": "completed",
                "retriedFromAttemptId": None,
                "failureCode": None,
            }
        ],
    },
    {
        "label": "Doc 3: SYN-WO-01-v1-raster300 (interrupted + explicit retry completed)",
        "documentId": "01a1e511-ae58-72ad-a79e-0b359340f539",
        "expectedJobId": "01a1e511-ae58-787c-96a3-5f082e019140",
        "expectedResultId": "01a1e514-f736-732b-a901-b75406b5d076",
        "expectedWinningAttemptId": "01a1e512-6a6d-7554-a1b6-352f03223bda",
        "expectedPages": 1,
        "expectedOriginalBytes": 372258,
        "expectedOriginalSha256": "47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd",
        "expectedRawBytes": 3236,
        "expectedRawSha256": "7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95",
        "expectedWorkerConfigSha256": EXPECTED_PINNED_DIGESTS["worker_config_1p_sha256"],
        "committedRawFileRel": (
            "docs/implementation/WP-0006/runtime-author-v2/runs/"
            "attempt-01a1e512-6a6d-7554-a1b6-352f03223bda/output/raw_output.utf8.bin"
        ),
        "expectedAttempts": [
            {
                "attemptNumber": 1,
                "attemptId": "01a1e511-ae6a-74cf-b0c9-d6e5933a22ea",
                "fencingToken": 3,
                "apiStatus": "interrupted",
                "expectedUiLabel": UI_STATUS_LABELS["interrupted"],
                "phase": "interrupted",
                "retriedFromAttemptId": None,
                "failureCode": "supervisor_interrupted",
            },
            {
                "attemptNumber": 2,
                "attemptId": "01a1e512-6a6d-7554-a1b6-352f03223bda",
                "fencingToken": 4,
                "apiStatus": "completed",
                "expectedUiLabel": UI_STATUS_LABELS["completed"],
                "phase": "completed",
                "retriedFromAttemptId": "01a1e511-ae6a-74cf-b0c9-d6e5933a22ea",
                "failureCode": None,
            },
        ],
    },
]

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_TERMINATE = 0x0001
STILL_ACTIVE = 259


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json_lf(path: Path, obj: object) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return raw


def git_stdout(root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True, encoding="utf-8").strip()


def git_bytes(root: Path, args: list[str]) -> bytes:
    return subprocess.check_output(["git", *args], cwd=root)


def git_object_exists(root: Path, spec: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", spec],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def git_is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def validate_completion_contract(root: Path = ROOT, authority_commit: str = EXPECTED_AUTHORITY_COMMIT) -> dict:
    ac = authority_commit.strip().lower()
    if ac != EXPECTED_AUTHORITY_COMMIT:
        raise RuntimeError(f"Unexpected authority commit {ac!r} != {EXPECTED_AUTHORITY_COMMIT!r}")
    if not git_object_exists(root, f"{ac}^{{commit}}") or not git_object_exists(root, f"{ac}:{EXPECTED_KICKOFF_PATH}"):
        raise RuntimeError(f"Authority commit {ac} or kickoff {EXPECTED_KICKOFF_PATH} missing in local Git store.")

    porcelain = git_stdout(root, ["status", "--porcelain"])
    if porcelain != "":
        raise RuntimeError(f"Worktree must be clean before execution, got: {porcelain!r}")

    head_sha = git_stdout(root, ["rev-parse", "HEAD"]).lower()
    for req_anc in (EXPECTED_SOURCE_COMMIT, EXPECTED_V2_EVIDENCE_BASE):
        if not git_is_ancestor(root, req_anc, head_sha):
            raise RuntimeError(f"Required ancestor {req_anc} is not an ancestor of executing HEAD {head_sha}")

    diff_since_v2 = [
        ln.strip()
        for ln in git_stdout(root, ["diff", "--name-only", EXPECTED_V2_EVIDENCE_BASE, head_sha]).splitlines()
        if ln.strip()
    ]
    bad_diff = [p for p in diff_since_v2 if not p.startswith("docs/implementation/WP-0006/saved-result-completion/")]
    if bad_diff:
        raise RuntimeError(f"Unexpected paths modified since {EXPECTED_V2_EVIDENCE_BASE}: {bad_diff}")

    for t_path, want_oid in {**EXPECTED_PRODUCT_TREES, **EXPECTED_PROTECTED_TREES}.items():
        got_oid = git_stdout(root, ["rev-parse", f"{head_sha}:{t_path}"]).lower()
        if got_oid != want_oid:
            raise RuntimeError(f"Protected/product tree {t_path} drifted: {got_oid} != {want_oid}")

    if git_object_exists(root, f"{head_sha}:docs/agent-reports/eld-f2-implementer"):
        raise RuntimeError("Canonical /003 report already exists before completion run!")

    helper_records = []
    for h_abs in (SCRIPT_PATH, UI_HELPER_PATH):
        rel = h_abs.relative_to(root).as_posix()
        disk = h_abs.read_bytes()
        if not git_object_exists(root, f"{head_sha}:{rel}"):
            raise RuntimeError(f"Helper {rel} is not committed in clean HEAD {head_sha}")
        blob = git_bytes(root, ["cat-file", "-p", f"{head_sha}:{rel}"])
        if disk != blob:
            raise RuntimeError(f"Helper {rel} on disk differs from committed HEAD blob")
        helper_records.append({"relative_path": rel, "byte_length": len(disk), "sha256": sha256_bytes(disk)})

    worker_root = root / "workers" / "local_ocr"
    local_digests = {
        "model_manifest_sha256": sha256_bytes((worker_root / "manifests" / "model-files.json").read_bytes()),
        "dependency_lock_sha256": sha256_bytes((worker_root / "manifests" / "dependency-lock.json").read_bytes()),
        "worker_source_sha256": compute_worker_source_sha256(worker_root),
        "worker_config_1p_sha256": compute_config_digest(1),
        "worker_config_3p_sha256": compute_config_digest(3),
    }
    if local_digests != EXPECTED_PINNED_DIGESTS:
        raise RuntimeError(f"Local digests {local_digests} != {EXPECTED_PINNED_DIGESTS}")

    # Verify frozen Angular receipt.ts statusLabels matches UI_STATUS_LABELS
    receipt_ts = (root / "web" / "src" / "app" / "intake" / "receipt.ts").read_text(encoding="utf-8")
    for api_st, ui_lbl in UI_STATUS_LABELS.items():
        expected_entry = f"{api_st}: '{ui_lbl}'"
        if expected_entry not in receipt_ts:
            raise RuntimeError(f"web/src/app/intake/receipt.ts missing expected frozen statusLabel entry: {expected_entry}")

    return {
        "validated_utc": utc_now(),
        "authority_commit": ac,
        "kickoff_path": EXPECTED_KICKOFF_PATH,
        "executing_head": head_sha,
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "v2_evidence_base": EXPECTED_V2_EVIDENCE_BASE,
        "database_name": DATABASE_NAME,
        "ports": dict(PORTS),
        "pinned_digests": local_digests,
        "committed_helpers": helper_records,
    }


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


def terminate_single_process_verified(pid: int, expected_ft: int, exit_code: int = 1) -> dict:
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
            raise RuntimeError(f"Refusing to terminate PID {pid}: FILETIME {actual_ft} != {expected_ft}")
        code = wintypes.DWORD()
        if _k32.GetExitCodeProcess(h, ctypes.byref(code)) and code.value != STILL_ACTIVE:
            return {"pid": pid, "expected_ft": expected_ft, "already_exited": True}
        terminated_utc = utc_now()
        if not _k32.TerminateProcess(h, exit_code):
            raise RuntimeError(f"Win32 TerminateProcess({pid}) failed with error {ctypes.get_last_error()}")
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


class ReadOnlyPostgresSession:
    def __init__(self, root: Path, pg_port: int, db_name: str):
        self.root = root
        self.pg_port = pg_port
        self.db_name = db_name
        self.settings = json.loads((root / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
        if int(self.settings["port"]) != pg_port:
            raise RuntimeError(f"pg-local.json port {self.settings['port']} != {pg_port}")
        self.psql = root / ".local" / "tools" / "pgsql-18.7-1" / "bin" / "psql.exe"

    def start(self) -> dict:
        subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(self.root / "deploy/dev/postgres/start-cluster.ps1")],
            cwd=self.root,
            check=True,
        )
        pid = int((self.root / ".local/postgres-data/postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
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

    def select_json_readonly(self, select_sql: str) -> list[dict]:
        if not select_sql.lstrip().upper().startswith("SELECT "):
            raise ValueError("Only read-only SELECT queries are permitted.")
        env = dict(
            os.environ,
            PGPASSWORD=self.settings["appPassword"],
            PGOPTIONS="-c default_transaction_read_only=on",
        )
        wrapped = f"SELECT COALESCE(json_agg(t), '[]'::json)::text FROM ({select_sql}) t;"
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
                str(self.settings["appUser"]),
                "-d",
                self.db_name,
                "-c",
                wrapped,
            ],
            env=env,
            text=True,
        ).strip()
        return json.loads(out) if out else []

    def app_connection_string(self) -> str:
        s = self.settings
        return (
            f"Host={s['host']};Port={s['port']};Database={self.db_name};"
            f"Username={s['appUser']};Password={s['appPassword']}"
        )


def capture_readonly_db_snapshot(pg: ReadOnlyPostgresSession, label: str) -> dict:
    docs = pg.select_json_readonly(
        "SELECT d.document_id, d.idempotency_key, d.submitted_at, "
        "o.page_count, o.byte_length, encode(o.sha256, 'hex') AS sha256_hex, "
        "octet_length(o.bytes) AS artifact_byte_length, "
        "encode(sha256(o.bytes), 'hex') AS artifact_computed_sha256 "
        "FROM eledgercare.documents d "
        "JOIN eledgercare.original_artifacts o ON o.document_id = d.document_id "
        "ORDER BY d.submitted_at ASC, d.document_id ASC"
    )
    jobs = pg.select_json_readonly(
        "SELECT job_id, document_id, status, requested_at, queued_at, updated_at, "
        "attempt_count, latest_fencing_token, retried_from_attempt_id "
        "FROM eledgercare.processing_jobs ORDER BY document_id ASC"
    )
    attempts = pg.select_json_readonly(
        "SELECT attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id, "
        "status, phase, run_directory_name, supervisor_pid, supervisor_create_filetime, "
        "launcher_pid, launcher_create_filetime, worker_pid, worker_create_filetime, "
        "started_at, ended_at, exit_code, failure_code, failure_detail "
        "FROM eledgercare.execution_attempts ORDER BY fencing_token ASC"
    )
    results = pg.select_json_readonly(
        "SELECT result_id, document_id, job_id, attempt_id, fencing_token, schema_version, "
        "encode(input_sha256, 'hex') AS input_sha256, input_byte_length, page_count, "
        "raw_output_byte_length, encode(raw_output_sha256, 'hex') AS raw_output_sha256, "
        "encode(sha256(raw_output_bytes), 'hex') AS raw_bytes_computed_sha256, "
        "model_repo_id, model_revision, encode(model_manifest_sha256, 'hex') AS model_manifest_sha256, "
        "encode(dependency_lock_sha256, 'hex') AS dependency_lock_sha256, "
        "encode(worker_source_digest, 'hex') AS worker_source_sha256, "
        "encode(worker_config_digest, 'hex') AS worker_config_sha256, "
        "renderer_identity, finish_reason, output_page_count "
        "FROM eledgercare.extraction_results ORDER BY fencing_token ASC"
    )
    canonical_payload = json.dumps(
        {"documents": docs, "jobs": jobs, "attempts": attempts, "results": results},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = sha256_bytes(canonical_payload)

    if len(docs) != 3 or len(jobs) != 3 or len(attempts) != 4 or len(results) != 3:
        raise RuntimeError(
            f"Unexpected row counts in {label}: docs={len(docs)}, jobs={len(jobs)}, "
            f"attempts={len(attempts)}, results={len(results)}"
        )
    max_token = max(int(a["fencing_token"]) for a in attempts)
    if max_token != 4:
        raise RuntimeError(f"Expected max fencing_token == 4 in {label}, got {max_token}")

    return {
        "label": label,
        "observed_utc": utc_now(),
        "counts": {
            "documents": len(docs),
            "processing_jobs": len(jobs),
            "execution_attempts": len(attempts),
            "extraction_results": len(results),
            "max_fencing_token": max_token,
        },
        "canonical_state_sha256": digest,
        "documents": docs,
        "jobs": jobs,
        "attempts": attempts,
        "results": results,
    }


class DisabledOcrApiInstance:
    """Starts ELedgerCare.Api strictly with LocalOcr__Enabled=false and zero external/GPU roots."""

    def __init__(self, label: str, app_conn_str: str, *, root: Path, api_port: int, obs_dir: Path):
        self.label = label
        self.app_conn_str = app_conn_str
        self.root = root
        self.api_port = api_port
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
            "ocr_enabled": False,
            "started_utc": self.started_utc,
        }

    def check_zero_child_processes(self) -> list[dict]:
        if self.pid <= 0:
            return []
        out = subprocess.check_output(
            [
                "pwsh",
                "-NoProfile",
                "-Command",
                f"@(Get-CimInstance Win32_Process -Filter 'ParentProcessId = {self.pid}' | "
                f"Select-Object ProcessId,Name,CreationDate) | ConvertTo-Json -Compress",
            ],
            text=True,
        ).strip()
        children = json.loads(out) if out else []
        if isinstance(children, dict):
            children = [children]
        if children:
            raise RuntimeError(f"Disabled-OCR API PID {self.pid} unexpectedly spawned children: {children}")
        return children

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


def http_get_only(api_port: int, path: str, *, timeout: float = 30.0) -> tuple[int, bytes]:
    url = f"http://127.0.0.1:{api_port}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def verify_all_three_via_http_get(api_port: int, phase_label: str) -> list[dict]:
    records: list[dict] = []
    for spec in PINNED_SAVED_DOCUMENTS:
        doc_id = spec["documentId"]
        st_doc, raw_doc = http_get_only(api_port, f"/api/documents/{doc_id}")
        st_ext, raw_ext = http_get_only(api_port, f"/api/documents/{doc_id}/extraction")
        st_org, raw_org = http_get_only(api_port, f"/api/documents/{doc_id}/original")
        if (st_doc, st_ext, st_org) != (200, 200, 200):
            raise RuntimeError(f"[{phase_label}] Unexpected HTTP GET status on {doc_id}: {(st_doc, st_ext, st_org)}")

        doc_json = json.loads(raw_doc.decode("utf-8"))
        ext_json = json.loads(raw_ext.decode("utf-8"))

        if doc_json["documentId"] != doc_id or doc_json["jobId"] != spec["expectedJobId"]:
            raise RuntimeError(f"[{phase_label}] Document/Job ID mismatch on {doc_id}: {doc_json}")
        if doc_json["acceptedResultId"] != spec["expectedResultId"] or doc_json["currentAttemptId"] != spec["expectedWinningAttemptId"]:
            raise RuntimeError(f"[{phase_label}] AcceptedResultId/CurrentAttemptId mismatch on {doc_id}: {doc_json}")
        if len(raw_org) != spec["expectedOriginalBytes"] or sha256_bytes(raw_org) != spec["expectedOriginalSha256"]:
            raise RuntimeError(f"[{phase_label}] Original PDF download byte/SHA mismatch on {doc_id}")

        if ext_json["workerEnabled"] is not False or ext_json["canRequestExtraction"] is not False or ext_json["canRetryExtraction"] is not False:
            raise RuntimeError(f"[{phase_label}] Expected workerEnabled/canRequest/canRetry all false on {doc_id}: {ext_json}")
        if ext_json["status"] != "completed":
            raise RuntimeError(f"[{phase_label}] Expected status 'completed' on {doc_id}, got {ext_json['status']!r}")

        res = ext_json["result"]
        raw_utf8 = res["rawText"].encode("utf-8")
        committed_raw = (ROOT / spec["committedRawFileRel"]).read_bytes()
        if (
            res["resultId"] != spec["expectedResultId"]
            or res["attemptId"] != spec["expectedWinningAttemptId"]
            or res["reviewStatus"] != "unreviewed"
            or res["pageCount"] != spec["expectedPages"]
            or res["rawByteLength"] != spec["expectedRawBytes"]
            or len(raw_utf8) != spec["expectedRawBytes"]
            or sha256_bytes(raw_utf8) != spec["expectedRawSha256"]
            or res["rawSha256"] != spec["expectedRawSha256"]
            or raw_utf8 != committed_raw
        ):
            raise RuntimeError(f"[{phase_label}] Saved extraction result byte/SHA/identity mismatch on {doc_id}")

        prov = res["provenance"]
        if (
            prov["modelRepoId"] != MODEL_REPO_ID
            or prov["modelRevision"] != MODEL_REVISION
            or prov["modelManifestSha256"] != EXPECTED_PINNED_DIGESTS["model_manifest_sha256"]
            or prov["dependencyLockSha256"] != EXPECTED_PINNED_DIGESTS["dependency_lock_sha256"]
            or prov["workerSourceSha256"] != EXPECTED_PINNED_DIGESTS["worker_source_sha256"]
            or prov["workerConfigSha256"] != spec["expectedWorkerConfigSha256"]
            or prov["finishReason"] != "stop"
            or prov["provenanceException"] != "torchvision-local-sha256-TOFU"
        ):
            raise RuntimeError(f"[{phase_label}] Provenance mismatch on {doc_id}: {prov}")

        page_nums = [p["pageNumber"] for p in res["pages"]]
        if page_nums != list(range(1, spec["expectedPages"] + 1)):
            raise RuntimeError(f"[{phase_label}] Page ordering mismatch on {doc_id}: {page_nums}")

        api_atts = ext_json["attempts"]
        if len(api_atts) != len(spec["expectedAttempts"]):
            raise RuntimeError(f"[{phase_label}] Attempt count mismatch on {doc_id}: {api_atts}")
        for idx, want_a in enumerate(spec["expectedAttempts"]):
            got_a = api_atts[idx]
            if (
                got_a["attemptNumber"] != want_a["attemptNumber"]
                or got_a["attemptId"] != want_a["attemptId"]
                or got_a["status"] != want_a["apiStatus"]
                or got_a["phase"] != want_a["phase"]
                or got_a["failureCode"] != want_a["failureCode"]
            ):
                raise RuntimeError(f"[{phase_label}] Attempt #{idx + 1} mismatch on {doc_id}: {got_a} vs {want_a}")

        records.append({
            "phase": phase_label,
            "document_id": doc_id,
            "job_id": doc_json["jobId"],
            "result_id": res["resultId"],
            "winning_attempt_id": res["attemptId"],
            "worker_enabled": ext_json["workerEnabled"],
            "page_numbers": page_nums,
            "raw_byte_length": len(raw_utf8),
            "raw_sha256": res["rawSha256"],
            "matches_committed_v2_raw_bytes": True,
            "original_byte_length": len(raw_org),
            "original_sha256": sha256_bytes(raw_org),
            "attempt_count": len(api_atts),
            "attempt_statuses": [a["status"] for a in api_atts],
            "get_extraction_response_sha256": sha256_bytes(raw_ext),
        })
    return records


def execute_completion(scratch_dir: Path) -> int:
    validated = validate_completion_contract(ROOT, EXPECTED_AUTHORITY_COMMIT)
    obs_dir = scratch_dir / "observations"
    obs_dir.mkdir(parents=True, exist_ok=True)
    write_json_lf(scratch_dir / "contract-validation-v3.json", validated)

    for p in PORTS.values():
        if check_port_bound(p):
            raise RuntimeError(f"Owned port {p} is unexpectedly bound before completion start.")

    pg = ReadOnlyPostgresSession(ROOT, PORTS["postgres"], DATABASE_NAME)
    pg_started = False
    active_api: DisabledOcrApiInstance | None = None

    summary: dict = {
        "schema": "eledgercare.wp-0006.saved-result-completion-summary/3",
        "authority_commit": EXPECTED_AUTHORITY_COMMIT,
        "kickoff_path": EXPECTED_KICKOFF_PATH,
        "executing_head": validated["executing_head"],
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "prior_v2_evidence_commit": EXPECTED_V2_EVIDENCE_BASE,
        "database": DATABASE_NAME,
        "ocr_enabled_throughout": False,
        "gpu_or_cuda_queried_or_imported": False,
        "external_runtime_roots_touched": False,
        "post_or_mutation_requests_sent": 0,
        "started_utc": utc_now(),
        "ports_bound_before": {str(p): check_port_bound(p) for p in PORTS.values()},
    }

    try:
        print("[SavedResultCompletion-v3] 1. Starting owned PostgreSQL 18.7 cluster & capturing BEFORE snapshot...", flush=True)
        pg_start_1 = pg.start()
        pg_started = True
        summary["postgres_start_1"] = pg_start_1

        snap_before = capture_readonly_db_snapshot(pg, "db-before")
        write_json_lf(obs_dir / "db-snapshot-before.json", snap_before)
        summary["db_before_counts"] = snap_before["counts"]
        summary["db_before_canonical_sha256"] = snap_before["canonical_state_sha256"]

        print("[SavedResultCompletion-v3] 2. Starting API #1 (LocalOcr:Enabled=false) & verifying pre-restart GETs...", flush=True)
        active_api = DisabledOcrApiInstance(
            "v3-run1-ocr-disabled-pre-restart",
            pg.app_connection_string(),
            root=ROOT,
            api_port=PORTS["api"],
            obs_dir=obs_dir,
        )
        summary["api_1_start"] = active_api.start()
        http_pre = verify_all_three_via_http_get(PORTS["api"], "pre_restart")
        active_api.check_zero_child_processes()
        summary["http_get_checks_pre_restart"] = http_pre
        summary["api_1_stop"] = active_api.stop_single_process()
        active_api = None

        print("[SavedResultCompletion-v3] 3. Performing clean PostgreSQL 18.7 fast restart...", flush=True)
        pg_stop_mid = pg.stop()
        pg_start_2 = pg.start()
        summary["postgres_fast_restart"] = {
            "stop": pg_stop_mid,
            "start": pg_start_2,
            "note": "Clean pg_ctl fast restart of owned cluster; not a power-loss test.",
        }

        print("[SavedResultCompletion-v3] 4. Starting API #2 (LocalOcr:Enabled=false) & verifying post-restart GETs + headless Edge UI...", flush=True)
        active_api = DisabledOcrApiInstance(
            "v3-run2-ocr-disabled-post-restart",
            pg.app_connection_string(),
            root=ROOT,
            api_port=PORTS["api"],
            obs_dir=obs_dir,
        )
        summary["api_2_start"] = active_api.start()
        http_post = verify_all_three_via_http_get(PORTS["api"], "post_restart")
        summary["http_get_checks_post_restart"] = http_post

        # Verify byte-identical GET /extraction responses across API + PostgreSQL fast restart
        for pre_item, post_item in zip(http_pre, http_post, strict=True):
            if pre_item["get_extraction_response_sha256"] != post_item["get_extraction_response_sha256"]:
                raise RuntimeError(
                    f"GET /extraction payload drifted across restart for {pre_item['document_id']}"
                )

        ui_in_path = obs_dir / "ui-spec-v3-all-saved-ocr-disabled.json"
        ui_out_path = obs_dir / "ui-verified-v3-all-saved-ocr-disabled.json"
        write_json_lf(
            ui_in_path,
            {
                "uiPort": PORTS["ui"],
                "apiPort": PORTS["api"],
                "documents": PINNED_SAVED_DOCUMENTS,
            },
        )
        subprocess.run(
            [
                "node",
                str(UI_HELPER_PATH),
                "--repoRoot",
                str(ROOT),
                "--input",
                str(ui_in_path),
                "--output",
                str(ui_out_path),
            ],
            cwd=ROOT,
            check=True,
        )
        ui_verified = json.loads(ui_out_path.read_text(encoding="utf-8"))
        summary["edge_ui_verification_post_restart"] = ui_verified

        active_api.check_zero_child_processes()
        summary["api_2_stop"] = active_api.stop_single_process()
        active_api = None

        print("[SavedResultCompletion-v3] 5. Capturing AFTER database snapshot & verifying zero new attempts/mutations...", flush=True)
        snap_after = capture_readonly_db_snapshot(pg, "db-after")
        write_json_lf(obs_dir / "db-snapshot-after.json", snap_after)
        summary["db_after_counts"] = snap_after["counts"]
        summary["db_after_canonical_sha256"] = snap_after["canonical_state_sha256"]

        if snap_before["canonical_state_sha256"] != snap_after["canonical_state_sha256"]:
            raise RuntimeError(
                f"Database state mutated during read-only completion check! "
                f"before={snap_before['canonical_state_sha256']} != after={snap_after['canonical_state_sha256']}"
            )
        summary["zero_new_attempts_and_zero_db_mutations_verified"] = True

        summary["postgres_final_stop"] = pg.stop()
        pg_started = False
        summary["outcome"] = "COMPLETED_SAVED_RESULT_REOPEN_VERIFICATION"
        return 0

    except Exception as exc:
        summary["outcome"] = "FAILED"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        raise

    finally:
        if active_api is not None:
            try:
                summary["cleanup_api_stop"] = active_api.stop_single_process()
            except Exception as api_err:
                summary["cleanup_api_stop_error"] = str(api_err)
        if pg_started:
            try:
                summary["cleanup_postgres_stop"] = pg.stop()
            except Exception as pg_err:
                summary["cleanup_postgres_stop_error"] = str(pg_err)

        summary["ports_bound_after"] = {str(p): check_port_bound(p) for p in PORTS.values()}
        summary["git_clean_after"] = git_stdout(ROOT, ["status", "--porcelain"]) == ""
        summary["completed_utc"] = utc_now()
        write_json_lf(scratch_dir / "completion-summary-v3.json", summary)
        print(
            f"[SavedResultCompletion-v3] Finalized completion-summary-v3.json ({summary.get('outcome')}); "
            f"ports_after={summary['ports_bound_after']}.",
            flush=True,
        )


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Bounded CPU-only WP-0006 F2 saved-result completion runner v3.")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run-validate", action="store_true", help="Validate Git/tree/statusLabel contract only.")
    mode.add_argument("--execute", action="store_true", help="Execute read-only PG/API fast-restart + Edge reopen.")
    p.add_argument(
        "--scratch-dir",
        default=str(ROOT / ".scratch" / "stage2-saved-result-completion" / "run"),
        help="Fresh owned scratch output directory (never overwrites stage2-runtime or stage2-runtime-v2).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    scratch_dir = Path(os.path.abspath(args.scratch_dir))
    for protected_name in ("stage2-runtime", "stage2-runtime-v2"):
        prot = (ROOT / ".scratch" / protected_name).resolve()
        if os.path.normcase(str(scratch_dir)).startswith(os.path.normcase(str(prot))):
            raise RuntimeError(f"Refusing to write inside preserved scratch directory: {prot}")

    if args.dry_run_validate:
        res = validate_completion_contract(ROOT, EXPECTED_AUTHORITY_COMMIT)
        print(json.dumps(res, indent=2))
        return 0

    return execute_completion(scratch_dir)


if __name__ == "__main__":
    raise SystemExit(main())
