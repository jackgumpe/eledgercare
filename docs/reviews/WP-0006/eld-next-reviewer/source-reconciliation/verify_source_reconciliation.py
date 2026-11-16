"""Independent WP-0006 F2 single-pass source, CPU, child-lifetime, and PostgreSQL 18.7 reconciliation verifier.

Owner: eld-next-reviewer (review/wp-0006-0007-next-tracks)
Scope: CPU / real OS child processes / PostgreSQL 18.7 (127.0.0.1:55435) ONLY.
Reconciles F2-S1-01, F2-S1-02, and F2-S1-03 against author candidate 8a73b7a5dab51e3ccf803aceedded4929529dd35
(published at 386d5c30809c3c04d6640d9433eb4263306ac126 under coordinator release 2ce3366d6aada92068088090bb026d4579b20e61).
Reuses unchanged Angular/Edge UI evidence (web tree f0877a006922818bf731d5f87603a368ed782487).
Zero GPU queries/use, zero model library imports, zero external F2 reviewer root creation, zero holdout access,
zero interference with concurrent WP-0007 B0 heldout inference, and zero secret disclosure.
Frozen before decisive execution.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

REVIEW_DIR = Path(__file__).resolve().parent
REPO_ROOT = REVIEW_DIR.parents[4]

ACCEPTED_DESIGN_REVIEW_SHA = "e2452e1ab3d8937868c07ffb30ce430715b5be78"
PRIOR_REVIEWER_FINDINGS_SHA = "10193e2c904f99cfc23c97367f1e5d881b0630f2"
COORDINATOR_AUTHORITY_SHA = "2ce3366d6aada92068088090bb026d4579b20e61"
AUTHOR_SOURCE_RESPONSE_PUB_SHA = "386d5c30809c3c04d6640d9433eb4263306ac126"
AUTHOR_CANDIDATE_SHA = "8a73b7a5dab51e3ccf803aceedded4929529dd35"
AUTHOR_INTERMEDIATE_SHA = "850d20063f09f0564a1008da20f09ff185fd0dfb"
PREVIOUS_AUTHOR_SOURCE_SHA = "0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978"
AUTHORIZED_MERGE_BASE_SHA = "3d12dcdc7735b48053f2a56a95c4247c49168786"
Q0_WHEEL_GRAPH_BLOB = "ec8c650ed5fbeb0a754e4daee53aad53753a57a3"

EXPECTED_NEW_WORKER_SOURCE_SHA256 = "c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54"
EXPECTED_MODEL_MANIFEST_SHA256 = "0df07bc60abf6937c917040bced32afabd7e4d11bafc0bd99902abca610a81be"
EXPECTED_DEPENDENCY_LOCK_SHA256 = "582071bf20eaca1836c3d1cef21d31cbdaa1e1407184033a918a40612c128111"
EXPECTED_CONFIG_SHA256_BY_PAGES = {
    1: "579aad63a9893a58466baf005ea63f87e92540d4c1f71f6b3c399e8b1e6b35ff",
    2: "e4df504ddb51dcc8fb137e97f5af97c735252374738b1a1754a88b16a05de5df",
    3: "ac90459ca4011b5859cfdd0b224d5ea247489b7c01775118736df7c1c9819e86",
}

EXPECTED_12_CHANGED_PATHS = [
    "src/ELedgerCare.Application/Extraction/ExtractionAttemptCoordinator.cs",
    "src/ELedgerCare.Application/Extraction/WorkerEnvelopeValidator.cs",
    "src/ELedgerCare.Domain/Processing/DiagnosticTextSanitizer.cs",
    "src/ELedgerCare.Domain/Processing/ExecutionAttempt.cs",
    "src/ELedgerCare.Infrastructure/Extraction/LocalPythonOcrWorkerRunner.cs",
    "src/ELedgerCare.Infrastructure/Persistence/ExtractionStore.cs",
    "tests/ELedgerCare.Acceptance.Tests/LocalExtractionAcceptanceTests.cs",
    "tests/ELedgerCare.Domain.Tests/ExtractionDomainAndParserTests.cs",
    "tests/ELedgerCare.Infrastructure.Tests/WorkerEnvelopeAndJobObjectTests.cs",
    "workers/local_ocr/local_ocr/env_guard.py",
    "workers/local_ocr/run_worker.py",
    "workers/local_ocr/tests/test_worker_cpu.py",
]

REVIEWER_API_PORT = 5290
REVIEWER_UI_PORT = 4310
REVIEWER_PG_PORT = 55435
AUTHOR_PORTS = (5190, 4210, 55434)

EXTERNAL_F2_REVIEWER_ROOT = Path(r"C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer")
EXTERNAL_F2_PARENT_ROOT = Path(r"C:\Users\jackg\eLedgerCare-F2\WP-0006")
AUTHOR_RESPONSE_SCRATCH_LOGS_DIR = Path(
    r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f2-implementer\.scratch\source-response-decisive\logs"
)
HOST_PYTHON_EXE = Path(r"C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe")

FORBIDDEN_HOLDOUT_TOKENS = (
    "F03", "F05", "F06", "F08",
    "SYN-WO-03", "SYN-INV-02", "SYN-INV-03", "SYN-MP-02",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dual_digests(data: bytes) -> dict:
    lf = data.replace(b"\r\n", b"\n")
    return {
        "raw_bytes": len(data),
        "raw_file_sha256": sha256_bytes(data),
        "lf_bytes": len(lf),
        "lf_normalized_sha256": sha256_bytes(lf),
        "contains_crlf": b"\r\n" in data,
    }


def is_loopback_port_bound(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def host_memory_and_cpu_snapshot() -> dict:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", wintypes.DWORD),
            ("dwMemoryLoad", wintypes.DWORD),
            ("ullTotalPhys", ctypes.c_uint64),
            ("ullAvailPhys", ctypes.c_uint64),
            ("ullTotalPageFile", ctypes.c_uint64),
            ("ullAvailPageFile", ctypes.c_uint64),
            ("ullTotalVirtual", ctypes.c_uint64),
            ("ullAvailVirtual", ctypes.c_uint64),
            ("ullAvailExtendedVirtual", ctypes.c_uint64),
        ]

    mem = MEMORYSTATUSEX()
    mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
    disk = shutil.disk_usage(str(REPO_ROOT))
    return {
        "observed_utc": utc_now(),
        "logical_cpu_count": os.cpu_count(),
        "memory_load_percent": int(mem.dwMemoryLoad),
        "total_phys_bytes": int(mem.ullTotalPhys),
        "avail_phys_bytes": int(mem.ullAvailPhys),
        "c_drive_free_bytes": int(disk.free),
        "reviewer_ports_bound": {
            str(p): is_loopback_port_bound(p)
            for p in (REVIEWER_API_PORT, REVIEWER_UI_PORT, REVIEWER_PG_PORT)
        },
        "author_ports_bound_readonly_observation": {
            str(p): is_loopback_port_bound(p)
            for p in AUTHOR_PORTS
        },
        "shared_host_confounder_note": (
            "Loopback CPU/child-process/PostgreSQL reconciliation shares physical host CPU/RAM/SSD I/O "
            "with concurrent WP-0007 B0 fixed heldout GPU inference under sole lease "
            "WP-0007-author-heldout-20261116T145544Z; zero GPU queries, zero ML imports, and zero "
            "other-owner processes, ports, or paths were touched."
        ),
    }


def current_or_pid_filetime(pid: int) -> int | None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    open_proc = kernel32.OpenProcess
    open_proc.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_proc.restype = wintypes.HANDLE
    get_times = kernel32.GetProcessTimes
    get_times.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    get_times.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    h = open_proc(0x1000, False, pid)
    if not h:
        return None
    try:
        c, e, kt, ut = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
        if not get_times(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut)):
            return None
        return (int(c.dwHighDateTime) << 32) | int(c.dwLowDateTime)
    finally:
        close_handle(h)


def run_git(args: list[str]) -> str:
    cp = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(REPO_ROOT), *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return cp.stdout


def build_base_env() -> dict[str, str]:
    env = dict(os.environ)
    env["DOTNET_CLI_HOME"] = str(REPO_ROOT / ".local" / "dotnet-home")
    env["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1"
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"
    env["NUGET_PACKAGES"] = str(REPO_ROOT / ".local" / "nuget" / "packages")
    return env


def redact_secrets(text: str, secrets: list[str]) -> str:
    out = text
    for s in secrets:
        if s:
            out = out.replace(s, "<REDACTED_SECRET>")
    return out


def run_logged_step(
    step_id: str,
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    logs_dir: Path,
    secrets_to_redact: list[str],
    check: bool = True,
) -> dict:
    started_utc = utc_now()
    t0 = time.perf_counter()
    cp = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
    )
    dur_ms = int(round((time.perf_counter() - t0) * 1000))
    ended_utc = utc_now()
    combined = cp.stdout + (b"\n" if cp.stdout and cp.stderr else b"") + cp.stderr
    text = combined.decode("utf-8", errors="replace")
    safe_text = redact_secrets(text, secrets_to_redact)
    raw_bytes = safe_text.encode("utf-8")

    log_path = logs_dir / f"{step_id}.log"
    log_path.write_bytes(raw_bytes)
    dig = dual_digests(raw_bytes)

    if check and cp.returncode != 0:
        raise RuntimeError(f"Step {step_id} failed with exit {cp.returncode}:\n{safe_text[-4000:]}")

    return {
        "step_id": step_id,
        "command": [str(x).replace(str(REPO_ROOT), "<worktree>") for x in cmd],
        "cwd": "." if cwd == REPO_ROOT else cwd.relative_to(REPO_ROOT).as_posix(),
        "started_utc": started_utc,
        "ended_utc": ended_utc,
        "duration_ms": dur_ms,
        "exit_code": cp.returncode,
        **dig,
    }


def verify_lineage_scope_and_author_publication() -> dict:
    head_sha = run_git(["rev-parse", "HEAD"]).strip()
    porcelain = run_git(["status", "--porcelain"]).strip()
    if porcelain:
        raise RuntimeError(f"Dirty working tree before decisive reconciliation run:\n{porcelain}")

    required_ancestors = (
        ACCEPTED_DESIGN_REVIEW_SHA,
        PRIOR_REVIEWER_FINDINGS_SHA,
        COORDINATOR_AUTHORITY_SHA,
        AUTHOR_SOURCE_RESPONSE_PUB_SHA,
        AUTHOR_CANDIDATE_SHA,
        AUTHOR_INTERMEDIATE_SHA,
        PREVIOUS_AUTHOR_SOURCE_SHA,
        AUTHORIZED_MERGE_BASE_SHA,
    )
    for anc in required_ancestors:
        rc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "merge-base", "--is-ancestor", anc, "HEAD"],
            stdin=subprocess.DEVNULL,
        ).returncode
        if rc != 0:
            raise RuntimeError(f"Required ancestor {anc} missing from HEAD {head_sha}!")

    # Verify exact 12 changed source/test paths from both 3d12dcdc and 0ad2fcd1 to 8a73b7a5
    diff_from_merge_base = sorted(
        ln.strip()
        for ln in run_git(["diff", "--name-only", f"{AUTHORIZED_MERGE_BASE_SHA}..{AUTHOR_CANDIDATE_SHA}"]).splitlines()
        if ln.strip()
    )
    diff_from_prev_source = sorted(
        ln.strip()
        for ln in run_git([
            "diff", "--name-only",
            f"{PREVIOUS_AUTHOR_SOURCE_SHA}..{AUTHOR_CANDIDATE_SHA}",
            "--", "src", "web", "workers", "tests", "deploy", "ELedgerCare.slnx",
        ]).splitlines()
        if ln.strip()
    )
    if diff_from_merge_base != EXPECTED_12_CHANGED_PATHS or diff_from_prev_source != EXPECTED_12_CHANGED_PATHS:
        raise RuntimeError(
            f"Unexpected source diff paths: merge_base={diff_from_merge_base}, prev_source={diff_from_prev_source}"
        )

    blob_checks = []
    for rel in EXPECTED_12_CHANGED_PATHS:
        cand_oid = run_git(["rev-parse", f"{AUTHOR_CANDIDATE_SHA}:{rel}"]).strip()
        head_oid = run_git(["rev-parse", f"HEAD:{rel}"]).strip()
        if cand_oid != head_oid:
            raise RuntimeError(f"Blob mismatch at HEAD for {rel}: {head_oid} != {cand_oid}")
        blob_checks.append({"path": rel, "blob_oid": head_oid})

    # Verify all 69 Stage 1 files outside the 12 updated paths remain byte-identical to 0ad2fcd1
    stage1_audit = json.loads(
        (REPO_ROOT / "docs" / "coordination" / "WP-0006" / "stage1-publication-audit.json").read_text(encoding="utf-8")
    )
    unchanged_stage1_count = 0
    for rel in stage1_audit["source_changed_files"]:
        if rel in EXPECTED_12_CHANGED_PATHS:
            continue
        prev_oid = run_git(["rev-parse", f"{PREVIOUS_AUTHOR_SOURCE_SHA}:{rel}"]).strip()
        head_oid = run_git(["rev-parse", f"HEAD:{rel}"]).strip()
        if prev_oid != head_oid:
            raise RuntimeError(f"Unrelated Stage 1 file {rel} mutated: {head_oid} != {prev_oid}")
        unchanged_stage1_count += 1

    # Verify protected trees & unchanged browser/UI trees
    audit = json.loads(
        (REPO_ROOT / "docs" / "coordination" / "WP-0006" / "source-response-publication-audit.json").read_text(
            encoding="utf-8"
        )
    )
    protected_results = []
    for item in audit["protected_objects"]:
        p = item["path"]
        expected_oid = item["object"]
        cand_oid = run_git(["rev-parse", f"{AUTHOR_SOURCE_RESPONSE_PUB_SHA}:{p}"]).strip()
        if cand_oid != expected_oid:
            raise RuntimeError(f"Protected object {p} mismatch in {AUTHOR_SOURCE_RESPONSE_PUB_SHA}: {cand_oid} != {expected_oid}")
        head_oid = run_git(["rev-parse", f"HEAD:{p}"]).strip()
        # Per kickoff L9, qualification/baseline advances via coordinator authority 2ce3366d while qualification/q0 is unchanged;
        # web, deploy, research, and evaluation must match identically at HEAD.
        if p in ("web", "deploy", "research", "evaluation") and head_oid != expected_oid:
            raise RuntimeError(f"Protected tree {p} mutated at HEAD: {head_oid} != {expected_oid}")
        if p == "qualification":
            coord_qual_oid = run_git(["rev-parse", f"{COORDINATOR_AUTHORITY_SHA}:qualification"]).strip()
            q0_prev_oid = run_git(["rev-parse", f"{PREVIOUS_AUTHOR_SOURCE_SHA}:qualification/q0"]).strip()
            q0_head_oid = run_git(["rev-parse", "HEAD:qualification/q0"]).strip()
            if head_oid != coord_qual_oid or q0_head_oid != q0_prev_oid:
                raise RuntimeError(
                    f"Unexpected qualification/q0 mutation: head={head_oid}, coord={coord_qual_oid}, q0_head={q0_head_oid}, q0_prev={q0_prev_oid}"
                )
        protected_results.append({
            "path": p,
            "expected_in_author_pub": expected_oid,
            "author_pub_oid": cand_oid,
            "reviewer_head_oid": head_oid,
        })

    # Verify reviewer's own prior immutable reports and review folders remain untouched since 10193e2c
    immutable_reviewer_paths = (
        "docs/agent-reports/eld-next-reviewer",
        "docs/reviews/WP-0006/eld-next-reviewer/design",
        "docs/reviews/WP-0006/eld-next-reviewer/preparation",
        "docs/reviews/WP-0006/eld-next-reviewer/implementation",
    )
    for imp in immutable_reviewer_paths:
        old_oid = run_git(["rev-parse", f"{PRIOR_REVIEWER_FINDINGS_SHA}:{imp}"]).strip()
        cur_oid = run_git(["rev-parse", f"HEAD:{imp}"]).strip()
        if old_oid != cur_oid:
            raise RuntimeError(f"Immutable reviewer directory {imp} changed since {PRIOR_REVIEWER_FINDINGS_SHA}!")

    # Verify all 10 published author source-response inventory entries + raw scratch log parity if accessible
    evidence_verified = []
    for ev in audit["evidence"]:
        fp = REPO_ROOT / ev["path"]
        raw = fp.read_bytes()
        dig = dual_digests(raw)
        if dig["raw_bytes"] != ev["bytes"] or dig["raw_file_sha256"] != ev["sha256"]:
            raise RuntimeError(f"Author evidence file mismatch on {ev['path']}: {dig} vs {ev}")
        scratch_match = None
        if ev["path"].startswith("docs/implementation/WP-0006/source-response/logs/"):
            scratch_fp = AUTHOR_RESPONSE_SCRATCH_LOGS_DIR / Path(ev["path"]).name
            if scratch_fp.is_file():
                scratch_match = sha256_bytes(scratch_fp.read_bytes()) == dig["raw_file_sha256"]
                if not scratch_match:
                    raise RuntimeError(f"Author published log {ev['path']} differs from raw scratch original!")
        evidence_verified.append({
            "path": ev["path"],
            "raw_bytes": dig["raw_bytes"],
            "raw_file_sha256": dig["raw_file_sha256"],
            "lf_normalized_sha256": dig["lf_normalized_sha256"],
            "matches_author_scratch_raw_bytes": scratch_match,
        })

    web_stage1_oid = run_git(["rev-parse", f"{PREVIOUS_AUTHOR_SOURCE_SHA}:web"]).strip()
    web_head_oid = run_git(["rev-parse", "HEAD:web"]).strip()
    deploy_stage1_oid = run_git(["rev-parse", f"{PREVIOUS_AUTHOR_SOURCE_SHA}:deploy"]).strip()
    deploy_head_oid = run_git(["rev-parse", "HEAD:deploy"]).strip()
    if web_stage1_oid != web_head_oid or deploy_stage1_oid != deploy_head_oid:
        raise RuntimeError("web or deploy tree changed since Stage 1 browser run; cannot reuse UI evidence!")

    return {
        "reviewer_frozen_helper_head": head_sha,
        "prior_reviewer_findings_sha": PRIOR_REVIEWER_FINDINGS_SHA,
        "coordinator_authority_sha": COORDINATOR_AUTHORITY_SHA,
        "author_source_response_publication_sha": AUTHOR_SOURCE_RESPONSE_PUB_SHA,
        "author_candidate_sha": AUTHOR_CANDIDATE_SHA,
        "author_retained_intermediate_sha": AUTHOR_INTERMEDIATE_SHA,
        "previous_author_source_sha": PREVIOUS_AUTHOR_SOURCE_SHA,
        "authorized_merge_base_sha": AUTHORIZED_MERGE_BASE_SHA,
        "changed_source_and_test_count": len(blob_checks),
        "changed_blobs_verified_at_head": blob_checks,
        "unchanged_other_stage1_files_verified": unchanged_stage1_count,
        "protected_objects": protected_results,
        "immutable_prior_reviewer_trees_intact": True,
        "author_evidence_inventory_verified_count": len(evidence_verified),
        "author_evidence_entries": evidence_verified,
        "reused_ui_browser_evidence": {
            "web_tree_oid": web_head_oid,
            "deploy_tree_oid": deploy_head_oid,
            "unchanged_from_stage1_0ad2fcd1": True,
            "prior_verified_reviewer_checkpoint": PRIOR_REVIEWER_FINDINGS_SHA,
            "prior_playwright_edge_passed": "10/10 on loopback API 5290 / UI 4310 / PG 55435",
        },
    }


def verify_static_digests_and_production_boundaries() -> dict:
    worker_root = REPO_ROOT / "workers" / "local_ocr"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))

    from local_ocr.protocol import compute_config_digest, compute_worker_source_sha256

    py_worker_sha = compute_worker_source_sha256(worker_root)
    if py_worker_sha != EXPECTED_NEW_WORKER_SOURCE_SHA256:
        raise RuntimeError(
            f"Python worker_source_sha256 {py_worker_sha} != expected {EXPECTED_NEW_WORKER_SOURCE_SHA256}"
        )

    manifest_bytes = (worker_root / "manifests" / "model-files.json").read_bytes()
    lock_bytes = (worker_root / "manifests" / "dependency-lock.json").read_bytes()
    manifest_sha = sha256_bytes(manifest_bytes)
    lock_sha = sha256_bytes(lock_bytes)
    if manifest_sha != EXPECTED_MODEL_MANIFEST_SHA256:
        raise RuntimeError(f"model-files.json SHA-256 changed: {manifest_sha}")
    if lock_sha != EXPECTED_DEPENDENCY_LOCK_SHA256:
        raise RuntimeError(f"dependency-lock.json SHA-256 changed: {lock_sha}")

    for pages, want_cfg in EXPECTED_CONFIG_SHA256_BY_PAGES.items():
        got_cfg = compute_config_digest(pages)
        if got_cfg != want_cfg:
            raise RuntimeError(f"worker_config_sha256({pages}) {got_cfg} != {want_cfg}")

    # Verify Q0 model-files.json & wheel-graph parity + DEV fixture parity without touching holdout files
    prod_model = json.loads(manifest_bytes.decode("utf-8"))
    q0_model = json.loads(
        (REPO_ROOT / "qualification" / "q0" / "harness" / "manifests" / "model-files.json").read_text(encoding="utf-8")
    )
    if prod_model["files"] != q0_model["files"] or prod_model["notices"] != q0_model["notices"]:
        raise RuntimeError("workers/local_ocr/manifests/model-files.json diverges from Q0 model-files.json!")

    f01_prod = (REPO_ROOT / "tests" / "fixtures" / "SYN-WO-01-v1-raster300.pdf").read_bytes()
    f01_dev = (REPO_ROOT / "evaluation" / "synthetic" / "pdfs" / "F01" / "SYN-WO-01-v1-raster300.pdf").read_bytes()
    f07_prod = (REPO_ROOT / "tests" / "fixtures" / "SYN-MP-01-v0-clean.pdf").read_bytes()
    f07_dev = (REPO_ROOT / "evaluation" / "synthetic" / "pdfs" / "F07" / "SYN-MP-01-v0-clean.pdf").read_bytes()
    if f01_prod != f01_dev or f07_prod != f07_dev:
        raise RuntimeError("Admitted DEV test fixtures diverge from corpus!")

    # Production cross-boundary reference scan
    scan_roots = [
        REPO_ROOT / "src",
        REPO_ROOT / "web" / "src",
        REPO_ROOT / "web" / "e2e",
        REPO_ROOT / "deploy" / "dev",
        REPO_ROOT / "workers" / "local_ocr" / "local_ocr",
    ]
    files_to_scan: list[Path] = [
        REPO_ROOT / "workers" / "local_ocr" / "run_worker.py",
        REPO_ROOT / "ELedgerCare.slnx",
    ]
    for sr in scan_roots:
        for p in sr.rglob("*"):
            if p.is_file() and not any(part in ("bin", "obj", "__pycache__", "node_modules", "dist") for part in p.parts):
                files_to_scan.append(p)

    forbidden_refs = ("qualification/", "qualification\\", "research/", "research\\", "evaluation/", "evaluation\\", "git.exe")
    violations = []
    for fp in files_to_scan:
        txt = fp.read_text(encoding="utf-8", errors="replace")
        body = "\n".join(ln for ln in txt.splitlines() if not ln.lstrip().startswith("#")) if fp.suffix.lower() == ".ps1" else txt
        for tok in forbidden_refs:
            if tok.lower() in body.lower():
                violations.append(f"{fp.relative_to(REPO_ROOT).as_posix()}: {tok}")
    if violations:
        raise RuntimeError(f"Production cross-boundary reference violation: {violations}")

    loaded_heavy = [m for m in ("torch", "transformers", "pypdfium2") if m in sys.modules]
    if loaded_heavy:
        raise RuntimeError(f"Forbidden heavy ML modules imported: {loaded_heavy}")

    return {
        "python_worker_source_sha256": py_worker_sha,
        "model_manifest_sha256": manifest_sha,
        "dependency_lock_sha256": lock_sha,
        "worker_config_sha256_by_pages": {str(k): v for k, v in EXPECTED_CONFIG_SHA256_BY_PAGES.items()},
        "admitted_dev_fixtures_identical": True,
        "scanned_production_files": len(files_to_scan),
        "cross_boundary_reference_violations": 0,
        "holdout_files_accessed": 0,
        "heavy_modules_imported": loaded_heavy,
    }


def run_python_storage_and_isolation_probes() -> dict:
    """Independent Python-side boundary probes for F2-S1-01 (-I isolation) and F2-S1-02 (directory_size_bytes)."""
    worker_root = REPO_ROOT / "workers" / "local_ocr"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))

    from local_ocr.env_guard import WorkerHeartbeat, directory_size_bytes, verify_storage_guards
    from local_ocr.protocol import MAX_RUNTIME_ROOT_BYTES, WorkerError

    # 1. Concurrent 4-thread NTFS delete/recreate churn + rapid WorkerHeartbeat atomic replace
    churn_iterations = 0
    with tempfile.TemporaryDirectory(prefix="elc-rev-py-churn-") as td:
        rt = Path(td)
        for s in range(16):
            sd = rt / "runs" / "attempt-1" / "cache" / f"seed-{s:02d}"
            sd.mkdir(parents=True, exist_ok=True)
            (sd / "blob.bin").write_bytes(b"abcd")

        stop_evt = threading.Event()

        def churn_worker(idx: int) -> None:
            seq = 0
            while not stop_evt.is_set():
                sub = rt / "runs" / "attempt-1" / "cache" / "tmp" / f"w{idx}-t-{seq % 16}"
                seq += 1
                try:
                    sub.mkdir(parents=True, exist_ok=True)
                    for f in range(4):
                        (sub / f"p-{f}.tmp").write_bytes(b"12345678")
                    shutil.rmtree(sub, ignore_errors=True)
                except OSError:
                    pass

        threads = [threading.Thread(target=churn_worker, args=(i,), daemon=True) for i in range(4)]
        for t in threads:
            t.start()

        hb = WorkerHeartbeat(
            rt / "runs" / "attempt-1" / "output" / "heartbeat.json",
            attempt_id="019a0000-0000-7000-8000-000000000101",
            fencing_token=1,
            interval_s=0.005,
            progress_fn=lambda: churn_iterations,
        ).start()
        try:
            deadline = time.perf_counter() + 2.0
            while time.perf_counter() < deadline or churn_iterations < 400:
                churn_iterations += 1
                hb.beat()
                sz = directory_size_bytes(rt)
                if sz < 64:
                    raise RuntimeError(f"Unexpectedly small byte count {sz} during seed+churn scan!")
                if churn_iterations >= 1500:
                    break
        finally:
            hb.stop()
            stop_evt.set()
            for t in threads:
                t.join(timeout=2.0)

    # 2. Fail-closed checks in Python directory_size_bytes / verify_storage_guards:
    #    (a) nested NTFS junction, (b) root NTFS junction, (c) ACL-denied directory (RD) & (RD,REA,RA),
    #    (d) excessive nesting depth > 32, (e) sparse file > 4 GiB ceiling.
    with tempfile.TemporaryDirectory(prefix="elc-rev-py-neg-") as td:
        base = Path(td)
        outside = base / "outside_target"
        outside.mkdir()
        (outside / "secret.bin").write_bytes(b"outside")

        # (a) Nested NTFS junction inside writable root
        rt_junc = base / "rt_nested_junction"
        (rt_junc / "runs").mkdir(parents=True)
        nested_link = rt_junc / "runs" / "escape_junc"
        subprocess.run(
            ["cmd.exe", "/c", "mklink", "/J", str(nested_link), str(outside)],
            stdin=subprocess.DEVNULL, capture_output=True, check=True,
        )
        try:
            nested_junction_rejected = False
            try:
                directory_size_bytes(rt_junc)
            except WorkerError as we:
                nested_junction_rejected = we.code == "storage_limit_exceeded"
        finally:
            os.rmdir(nested_link)

        # (b) Root NTFS junction itself
        root_link = base / "rt_root_junction"
        subprocess.run(
            ["cmd.exe", "/c", "mklink", "/J", str(root_link), str(outside)],
            stdin=subprocess.DEVNULL, capture_output=True, check=True,
        )
        try:
            root_junction_rejected = False
            try:
                directory_size_bytes(root_link)
            except WorkerError as we:
                root_junction_rejected = we.code == "storage_limit_exceeded"
        finally:
            os.rmdir(root_link)

        # (c) Persistent NTFS ACL-denied subdirectory: both (RD) and (RD,REA,RA)
        acl_rd_rejected = False
        acl_rd_ra_rejected = False
        rt_acl = base / "rt_acl"
        locked_dir = rt_acl / "runs" / "locked_sub"
        locked_dir.mkdir(parents=True)
        (locked_dir / "hidden.bin").write_bytes(b"1234")
        try:
            subprocess.run(
                ["icacls", str(locked_dir), "/deny", "*S-1-1-0:(RD)"],
                stdin=subprocess.DEVNULL, capture_output=True, check=True,
            )
            try:
                directory_size_bytes(rt_acl)
            except WorkerError as we:
                acl_rd_rejected = we.code == "storage_limit_exceeded"
        finally:
            subprocess.run(["icacls", str(locked_dir), "/reset"], stdin=subprocess.DEVNULL, capture_output=True)

        try:
            subprocess.run(
                ["icacls", str(locked_dir), "/deny", "*S-1-1-0:(RD,REA,RA)"],
                stdin=subprocess.DEVNULL, capture_output=True, check=True,
            )
            try:
                directory_size_bytes(rt_acl)
            except WorkerError as we:
                acl_rd_ra_rejected = we.code == "storage_limit_exceeded"
        finally:
            subprocess.run(["icacls", str(locked_dir), "/reset"], stdin=subprocess.DEVNULL, capture_output=True)

        # (d) Excessive directory depth (> 32)
        rt_deep = base / "rt_deep"
        cur = rt_deep
        for d in range(35):
            cur = cur / f"d{d}"
        cur.mkdir(parents=True)
        deep_rejected = False
        try:
            directory_size_bytes(rt_deep)
        except WorkerError as we:
            deep_rejected = we.code == "storage_limit_exceeded"

        # (e) Sparse file exceeding 4 GiB ceiling (zero physical disk allocation)
        rt_sparse = base / "rt_sparse"
        rt_sparse.mkdir()
        sparse_file = rt_sparse / "oversized.sparse"
        sparse_file.write_bytes(b"")
        subprocess.run(
            ["fsutil", "sparse", "setflag", str(sparse_file), "1"],
            stdin=subprocess.DEVNULL, capture_output=True, check=True,
        )
        with sparse_file.open("r+b") as sf:
            sf.truncate(MAX_RUNTIME_ROOT_BYTES + 4096)
        sparse_ceiling_rejected = False
        try:
            verify_storage_guards(rt_sparse, min_free_bytes=1024)
        except WorkerError as we:
            sparse_ceiling_rejected = we.code == "storage_limit_exceeded"

    checks = {
        "transient_churn_iterations_without_error": churn_iterations,
        "nested_ntfs_junction_rejected": nested_junction_rejected,
        "root_ntfs_junction_rejected": root_junction_rejected,
        "persistent_acl_rd_denied_rejected": acl_rd_rejected,
        "persistent_acl_rd_rea_ra_denied_rejected": acl_rd_ra_rejected,
        "depth_over_32_rejected": deep_rejected,
        "sparse_over_4gib_ceiling_rejected": sparse_ceiling_rejected,
        "heavy_modules_imported": [m for m in ("torch", "transformers", "pypdfium2") if m in sys.modules],
    }
    if not all([
        nested_junction_rejected,
        root_junction_rejected,
        acl_rd_rejected,
        acl_rd_ra_rejected,
        deep_rejected,
        sparse_ceiling_rejected,
        len(checks["heavy_modules_imported"]) == 0,
    ]):
        raise RuntimeError(f"Python storage fail-closed probe failed: {checks}")
    return checks


CSHARP_PROBE_CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <TreatWarningsAsErrors>false</TreatWarningsAsErrors>
    <AnalysisLevel>none</AnalysisLevel>
    <RestorePackagesWithLockFile>false</RestorePackagesWithLockFile>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="{repo_root}\\src\\ELedgerCare.Infrastructure\\ELedgerCare.Infrastructure.csproj" />
  </ItemGroup>
</Project>
"""

FAKE_GRANDCHILD_WORKER_PY = r'''import ctypes
from ctypes import wintypes
import json
import pathlib
import subprocess
import sys
import time


def proc_ft(pid):
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    k32.GetProcessTimes.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    h = k32.OpenProcess(0x1000, False, pid)
    c, e, kt, ut = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
    k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut))
    k32.CloseHandle(h)
    return (int(c.dwHighDateTime) << 32) | int(c.dwLowDateTime)


gc = subprocess.Popen(
    [sys.executable, "-I", "-c", "import time, sys; sys.stdout.write('gc-open\\n'); sys.stdout.flush(); time.sleep(60)"]
)
hb = {
    "phase": "inferring",
    "worker_pid": gc.pid,
    "worker_create_filetime": proc_ft(gc.pid),
    "phase_timeout_s": 600,
    "stall_monitored": False,
    "forward_progress": 1,
}
out_dir = pathlib.Path.cwd() / "output"
(out_dir / "heartbeat.json").write_text(json.dumps(hb), encoding="utf-8")
sys.stdout.write("launcher-open\n")
sys.stdout.flush()
time.sleep(60)
'''

CSHARP_PROBE_PROGRAM = r'''using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ELedgerCare.Application.Extraction;
using ELedgerCare.Domain.Documents;
using ELedgerCare.Domain.Processing;
using ELedgerCare.Infrastructure.Extraction;
using ELedgerCare.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Npgsql;

var repoRoot = args[0];
var outputJsonPath = args[1];
var expectedWorkerHex = args[2];
var fakeWorkerTemplatePath = args[3];
var hostPy = @"C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe";

var pgSettingsPath = Path.Combine(repoRoot, ".local", "secrets", "pg-local.json");
using var settingsDoc = JsonDocument.Parse(await File.ReadAllTextAsync(pgSettingsPath));
var sRoot = settingsDoc.RootElement;
var pgHost = sRoot.GetProperty("host").GetString()!;
var pgPort = sRoot.GetProperty("port").GetInt32();
var adminUser = sRoot.GetProperty("adminUser").GetString()!;
var adminPass = sRoot.GetProperty("adminPassword").GetString()!;
var migUser = sRoot.GetProperty("migratorUser").GetString()!;
var migPass = sRoot.GetProperty("migratorPassword").GetString()!;
var appUser = sRoot.GetProperty("appUser").GetString()!;
var appPass = sRoot.GetProperty("appPassword").GetString()!;

string AdminConn(string db = "postgres") => $"Host={pgHost};Port={pgPort};Database={db};Username={adminUser};Password={adminPass}";
string MigConn(string db) => $"Host={pgHost};Port={pgPort};Database={db};Username={migUser};Password={migPass}";
string AppConn(string db) => $"Host={pgHost};Port={pgPort};Database={db};Username={appUser};Password={appPass}";

var workerRoot = Path.Combine(repoRoot, "workers", "local_ocr");
var manifestSha = SHA256.HashData(await File.ReadAllBytesAsync(Path.Combine(workerRoot, "manifests", "model-files.json")));
var lockSha = SHA256.HashData(await File.ReadAllBytesAsync(Path.Combine(workerRoot, "manifests", "dependency-lock.json")));
var workerSha = ExtractionSettings.ComputeWorkerSourceSha256(workerRoot);
var actualWorkerHex = Convert.ToHexStringLower(workerSha);
if (actualWorkerHex != expectedWorkerHex)
    throw new InvalidOperationException($"C# ComputeWorkerSourceSha256 {actualWorkerHex} != expected {expectedWorkerHex}");

var results = new Dictionary<string, object?>
{
    ["csharp_worker_source_sha256"] = actualWorkerHex,
};

static async Task RunToolAsync(string fileName, params string[] arguments)
{
    var psi = new ProcessStartInfo(fileName)
    {
        UseShellExecute = false,
        CreateNoWindow = true,
        RedirectStandardOutput = true,
        RedirectStandardError = true,
    };
    foreach (var a in arguments) psi.ArgumentList.Add(a);
    using var p = Process.Start(psi)!;
    var outText = await p.StandardOutput.ReadToEndAsync();
    var errText = await p.StandardError.ReadToEndAsync();
    await p.WaitForExitAsync();
    if (p.ExitCode != 0)
        throw new InvalidOperationException($"{fileName} exited {p.ExitCode}: {outText} {errText}");
}

// =================================================================================================
// R1: Reconcile F2-S1-01 — Real LocalPythonOcrWorkerRunner -> WindowsJobProcess -> venv python -I
//     from external runDir WITH poison local_ocr.py injected directly into runDir before resume
//     AND poison PYTHONPATH in parent process environment!
// =================================================================================================
{
    var r1Root = Path.Combine(Path.GetTempPath(), $"elc-rev-r1-{Guid.NewGuid():N}");
    var fakeQ0 = Path.Combine(r1Root, "q0");
    var fakeRt = Path.Combine(r1Root, "rt");
    var poisonPyPath = Path.Combine(r1Root, "poison_pythonpath");
    Directory.CreateDirectory(fakeQ0);
    Directory.CreateDirectory(fakeRt);
    Directory.CreateDirectory(poisonPyPath);
    await File.WriteAllTextAsync(Path.Combine(poisonPyPath, "local_ocr.py"), "raise SystemExit(97)\n");

    var prevPyPath = Environment.GetEnvironmentVariable("PYTHONPATH");
    Environment.SetEnvironmentVariable("PYTHONPATH", poisonPyPath);
    try
    {
        await RunToolAsync(hostPy, "-m", "venv", "--without-pip", Path.Combine(fakeQ0, "venv"));
        Directory.CreateDirectory(Path.Combine(fakeQ0, "models", "Unlimited_OCR_2_04809669"));
        Directory.CreateDirectory(Path.Combine(fakeQ0, "notices", "Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"));

        var enabledSettings = new ExtractionSettings(
            true, 3, fakeQ0, fakeRt, "GPU-00000000-0000-0000-0000-000000000000",
            workerRoot, manifestSha, lockSha, workerSha);
        var runner = new LocalPythonOcrWorkerRunner(enabledSettings);
        var pdfBytes = Encoding.ASCII.GetBytes("%PDF-1.4\n%%EOF\n");
        var work = new ClaimedAttemptWork(
            Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(),
            1, 1, "attempt-r1", pdfBytes, SHA256.HashData(pdfBytes), pdfBytes.Length, 1);

        string poisonRunLocalOcr = Path.Combine(fakeRt, "runs", "attempt-r1", "local_ocr.py");
        var outcome = await runner.ExecuteAttemptAsync(
            work,
            async (_, _, _) =>
            {
                //Launcher is CREATE_SUSPENDED inside runDir; plant a poison local_ocr.py in cwd before resume!
                await File.WriteAllTextAsync(poisonRunLocalOcr, "import pathlib; pathlib.Path('hijacked.flag').write_text('bad'); raise SystemExit(98)\n");
                return true;
            },
            (_, _, _, _) => Task.FromResult(true),
            CancellationToken.None);

        var runOutDir = Path.Combine(fakeRt, "runs", "attempt-r1", "output");
        var stderrLog = File.Exists(Path.Combine(runOutDir, "child.stderr.log"))
            ? await File.ReadAllTextAsync(Path.Combine(runOutDir, "child.stderr.log"))
            : "";
        var hbExists = File.Exists(Path.Combine(runOutDir, "heartbeat.json"));
        var hijacked = File.Exists(Path.Combine(fakeRt, "runs", "attempt-r1", "hijacked.flag"));
        var val = WorkerEnvelopeValidator.Validate(work, enabledSettings, outcome, DateTimeOffset.UtcNow);
        var rej = val as EnvelopeValidationOutcome.Rejected
            ?? throw new InvalidOperationException("Expected Rejected outcome due to empty --without-pip venv.");

        if (outcome.ExitCode != 2 || outcome.EnvelopeJsonBytes is null || !hbExists || hijacked ||
            stderrLog.Contains("ModuleNotFoundError", StringComparison.Ordinal) ||
            rej.FailureCode != "dependency_lock_mismatch")
        {
            throw new InvalidOperationException(
                $"R1 F2-S1-01 reconciliation failed: exit={outcome.ExitCode}, envNull={outcome.EnvelopeJsonBytes is null}, hb={hbExists}, hijacked={hijacked}, code={rej.FailureCode}, stderr={stderrLog}");
        }

        using var envDoc = JsonDocument.Parse(outcome.EnvelopeJsonBytes);
        results["R1_F2_S1_01_isolated_entrypoint_and_cwd_poison_resistance"] = new
        {
            reconciled = true,
            child_exit_code = outcome.ExitCode,
            heartbeat_json_written = hbExists,
            envelope_schema = envDoc.RootElement.GetProperty("schema").GetString(),
            envelope_status = envDoc.RootElement.GetProperty("status").GetString(),
            validator_failure_code = rej.FailureCode,
            module_not_found_error_absent = !stderrLog.Contains("ModuleNotFoundError", StringComparison.Ordinal),
            cwd_poison_local_ocr_ignored = !hijacked,
            parent_pythonpath_poison_ignored = outcome.ExitCode != 97,
        };
    }
    finally
    {
        Environment.SetEnvironmentVariable("PYTHONPATH", prevPyPath);
        try { Directory.Delete(r1Root, true); } catch { }
    }
}

// =================================================================================================
// R2a: Reconcile F2-S1-02 (Part A) — C# CheckStorageBounds under 4-thread NTFS delete/recreate churn
//      PLUS fail-closed verification on junctions, persistent ACL denials, depth > 32, and > 4 GiB sparse file
// =================================================================================================
{
    var churnRoot = Path.Combine(Path.GetTempPath(), $"elc-rev-r2a-churn-{Guid.NewGuid():N}");
    Directory.CreateDirectory(churnRoot);
    int churnIterations = 0;
    try
    {
        for (var s = 0; s < 24; s++)
        {
            var seedDir = Path.Combine(churnRoot, "runs", "attempt-1", "cache", $"seed-{s:D2}");
            Directory.CreateDirectory(seedDir);
            File.WriteAllBytes(Path.Combine(seedDir, "blob.bin"), [1, 2, 3, 4]);
        }

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(2.5));
        var churnTasks = Enumerable.Range(0, 4).Select(workerIdx => Task.Run(() =>
        {
            var seq = 0;
            while (!cts.IsCancellationRequested)
            {
                var sub = Path.Combine(churnRoot, "runs", "attempt-1", "cache", "tmp", $"w{workerIdx}-transient-{seq++ % 16}");
                try
                {
                    Directory.CreateDirectory(sub);
                    for (var f = 0; f < 6; f++)
                        File.WriteAllBytes(Path.Combine(sub, $"part-{f}.tmp"), [1, 2, 3, 4]);
                    Directory.Delete(sub, true);
                }
                catch { }
            }
        })).ToArray();

        while ((!cts.IsCancellationRequested || churnIterations < 800) && churnIterations < 2500)
        {
            churnIterations++;
            if (!LocalPythonOcrWorkerRunner.CheckStorageBounds(churnRoot, out var failDetail))
                throw new InvalidOperationException($"CheckStorageBounds unexpectedly failed at iter {churnIterations}: {failDetail}");
        }
        cts.Cancel();
        try { await Task.WhenAll(churnTasks); } catch { }
    }
    finally
    {
        try { Directory.Delete(churnRoot, true); } catch { }
    }

    var negBase = Path.Combine(Path.GetTempPath(), $"elc-rev-r2a-neg-{Guid.NewGuid():N}");
    Directory.CreateDirectory(negBase);
    bool nestedJunctionRejected, rootJunctionRejected, aclRdRejected, aclRdRaRejected, deepRejected, over4GiBRejected;
    try
    {
        var outside = Path.Combine(negBase, "outside");
        Directory.CreateDirectory(outside);
        await File.WriteAllBytesAsync(Path.Combine(outside, "data.bin"), [9, 9, 9]);

        // 1. Nested NTFS junction
        var rtJunc = Path.Combine(negBase, "rt_junc");
        Directory.CreateDirectory(Path.Combine(rtJunc, "runs"));
        var nestedLink = Path.Combine(rtJunc, "runs", "junc");
        await RunToolAsync("cmd.exe", "/c", "mklink", "/J", nestedLink, outside);
        try
        {
            nestedJunctionRejected = !LocalPythonOcrWorkerRunner.CheckStorageBounds(rtJunc, out var d1) &&
                                     d1.Contains("Reparse point", StringComparison.OrdinalIgnoreCase);
        }
        finally
        {
            Directory.Delete(nestedLink, false);
        }

        // 2. Root NTFS junction
        var rootLink = Path.Combine(negBase, "rt_root_junc");
        await RunToolAsync("cmd.exe", "/c", "mklink", "/J", rootLink, outside);
        try
        {
            rootJunctionRejected = !LocalPythonOcrWorkerRunner.CheckStorageBounds(rootLink, out var d2) &&
                                   d2.Contains("reparse point", StringComparison.OrdinalIgnoreCase);
        }
        finally
        {
            Directory.Delete(rootLink, false);
        }

        // 3. Persistent ACL-denied directory inside runs/attempt-1/cache/locked_acl (tests cache-path persistent lock too!)
        var rtAcl = Path.Combine(negBase, "rt_acl");
        var lockedDir = Path.Combine(rtAcl, "runs", "attempt-1", "cache", "locked_acl");
        Directory.CreateDirectory(lockedDir);
        await File.WriteAllBytesAsync(Path.Combine(lockedDir, "secret.bin"), [1, 2, 3]);
        try
        {
            await RunToolAsync("icacls", lockedDir, "/deny", "*S-1-1-0:(RD)");
            aclRdRejected = !LocalPythonOcrWorkerRunner.CheckStorageBounds(rtAcl, out _);
        }
        finally
        {
            try { await RunToolAsync("icacls", lockedDir, "/reset"); } catch { }
        }

        try
        {
            await RunToolAsync("icacls", lockedDir, "/deny", "*S-1-1-0:(RD,REA,RA)");
            aclRdRaRejected = !LocalPythonOcrWorkerRunner.CheckStorageBounds(rtAcl, out _);
        }
        finally
        {
            try { await RunToolAsync("icacls", lockedDir, "/reset"); } catch { }
        }

        // 4. Depth > 32
        var rtDeep = Path.Combine(negBase, "rt_deep");
        var cur = rtDeep;
        for (var i = 0; i < 35; i++) cur = Path.Combine(cur, $"d{i}");
        Directory.CreateDirectory(cur);
        deepRejected = !LocalPythonOcrWorkerRunner.CheckStorageBounds(rtDeep, out var dDeep) &&
                       dDeep.Contains("depth", StringComparison.OrdinalIgnoreCase);

        // 5. Sparse file > 4 GiB ceiling (zero physical disk allocation)
        var rtSparse = Path.Combine(negBase, "rt_sparse");
        Directory.CreateDirectory(rtSparse);
        var sparsePath = Path.Combine(rtSparse, "big.sparse");
        await File.WriteAllBytesAsync(sparsePath, []);
        await RunToolAsync("fsutil", "sparse", "setflag", sparsePath, "1");
        using (var fs = new FileStream(sparsePath, FileMode.Open, FileAccess.Write))
        {
            fs.SetLength(ExtractionCeilings.MaxRuntimeRootBytes + 4096L);
        }
        over4GiBRejected = !LocalPythonOcrWorkerRunner.CheckStorageBounds(rtSparse, out var dBig) &&
                           dBig.Contains("4 GiB", StringComparison.OrdinalIgnoreCase);
    }
    finally
    {
        try { Directory.Delete(negBase, true); } catch { }
    }

    if (!(nestedJunctionRejected && rootJunctionRejected && aclRdRejected && aclRdRaRejected && deepRejected && over4GiBRejected))
    {
        throw new InvalidOperationException(
            $"R2a CheckStorageBounds fail-closed assertion failed: nestedJunc={nestedJunctionRejected}, rootJunc={rootJunctionRejected}, aclRd={aclRdRejected}, aclRdRa={aclRdRaRejected}, deep={deepRejected}, over4GiB={over4GiBRejected}");
    }

    results["R2a_F2_S1_02_csharp_storage_bounds"] = new
    {
        reconciled = true,
        transient_churn_iterations_passed = churnIterations,
        transient_churn_exceptions = 0,
        nested_ntfs_junction_rejected = nestedJunctionRejected,
        root_ntfs_junction_rejected = rootJunctionRejected,
        persistent_cache_acl_rd_denied_rejected = aclRdRejected,
        persistent_cache_acl_rd_rea_ra_denied_rejected = aclRdRaRejected,
        depth_over_32_rejected = deepRejected,
        sparse_over_4gib_rejected = over4GiBRejected,
    };
}

// =================================================================================================
// R2b: Reconcile F2-S1-02 (Part B) — ExecuteAttemptAsync finally terminates BOTH launcher AND
//      grandchild holding stdout/stderr pipes open across ALL non-normal exits without masking exceptions
// =================================================================================================
{
    var r2bRoot = Path.Combine(Path.GetTempPath(), $"elc-rev-r2b-{Guid.NewGuid():N}");
    var fakeQ0 = Path.Combine(r2bRoot, "q0");
    var fakeRt = Path.Combine(r2bRoot, "rt");
    var fakeWorkerRoot = Path.Combine(r2bRoot, "fake_worker");
    Directory.CreateDirectory(fakeQ0);
    Directory.CreateDirectory(fakeRt);
    Directory.CreateDirectory(Path.Combine(fakeWorkerRoot, "local_ocr"));
    var probe = new WindowsProcessIdentityProbe();

    try
    {
        await RunToolAsync(hostPy, "-m", "venv", "--without-pip", Path.Combine(fakeQ0, "venv"));
        Directory.CreateDirectory(Path.Combine(fakeQ0, "models", "Unlimited_OCR_2_04809669"));
        Directory.CreateDirectory(Path.Combine(fakeQ0, "notices", "Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"));
        await File.WriteAllTextAsync(Path.Combine(fakeWorkerRoot, "local_ocr", "__init__.py"), "");

        // Copy fake run_worker.py that spawns an additional grandchild python process inheriting stdout/stderr pipes for 60s
        // and writes grandchild (pid, create_filetime) into output/heartbeat.json!
        File.Copy(fakeWorkerTemplatePath, Path.Combine(fakeWorkerRoot, "run_worker.py"), overwrite: true);

        var fakeWorkerSha = ExtractionSettings.ComputeWorkerSourceSha256(fakeWorkerRoot);
        var settings = new ExtractionSettings(
            true, 3, fakeQ0, fakeRt, "GPU-00000000-0000-0000-0000-000000000000",
            fakeWorkerRoot, manifestSha, lockSha, fakeWorkerSha);
        var runner = new LocalPythonOcrWorkerRunner(settings);
        var pdfBytes = Encoding.ASCII.GetBytes("%PDF-1.4\n%%EOF\n");

        // Case 1: Exception inside onLauncherAssignedBeforeResumeAsync while launcher is CREATE_SUSPENDED
        int c1LauncherPid = 0;
        long c1LauncherFt = 0;
        string? c1ExMsg = null;
        var sw1 = Stopwatch.StartNew();
        try
        {
            var w1 = new ClaimedAttemptWork(Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(), 1, 1, "attempt-c1", pdfBytes, SHA256.HashData(pdfBytes), pdfBytes.Length, 1);
            await runner.ExecuteAttemptAsync(
                w1,
                (pid, ft, _) =>
                {
                    c1LauncherPid = pid;
                    c1LauncherFt = ft;
                    throw new InvalidOperationException("simulated-pre-resume-db-error");
                },
                (_, _, _, _) => Task.FromResult(true),
                CancellationToken.None).WaitAsync(TimeSpan.FromSeconds(5));
        }
        catch (InvalidOperationException ex)
        {
            c1ExMsg = ex.Message;
        }
        sw1.Stop();
        var c1Dead = c1LauncherPid > 0 && !probe.IsProcessAlive(c1LauncherPid, c1LauncherFt);

        // Case 2: Exception inside onHeartbeatAsync AFTER both launcher AND grandchild hold stdout/stderr pipes open!
        int c2LauncherPid = 0, c2GrandchildPid = 0;
        long c2LauncherFt = 0, c2GrandchildFt = 0;
        string? c2ExMsg = null;
        var sw2 = Stopwatch.StartNew();
        try
        {
            var w2 = new ClaimedAttemptWork(Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(), 1, 1, "attempt-c2", pdfBytes, SHA256.HashData(pdfBytes), pdfBytes.Length, 1);
            await runner.ExecuteAttemptAsync(
                w2,
                (pid, ft, _) => { c2LauncherPid = pid; c2LauncherFt = ft; return Task.FromResult(true); },
                (phase, wPid, wFt, _) =>
                {
                    if (phase == "inferring" && wPid is > 0 && wFt is > 0)
                    {
                        c2GrandchildPid = wPid.Value;
                        c2GrandchildFt = wFt.Value;
                        throw new InvalidOperationException("simulated-mid-run-heartbeat-db-error");
                    }
                    return Task.FromResult(true);
                },
                CancellationToken.None).WaitAsync(TimeSpan.FromSeconds(8));
        }
        catch (InvalidOperationException ex)
        {
            c2ExMsg = ex.Message;
        }
        sw2.Stop();
        var c2BothDead = c2LauncherPid > 0 && c2GrandchildPid > 0 &&
                         !probe.IsProcessAlive(c2LauncherPid, c2LauncherFt) &&
                         !probe.IsProcessAlive(c2GrandchildPid, c2GrandchildFt);

        // Case 3: CancellationToken cancelled while both launcher AND grandchild hold stdout/stderr pipes open!
        int c3LauncherPid = 0, c3GrandchildPid = 0;
        long c3LauncherFt = 0, c3GrandchildFt = 0;
        bool c3CanceledPropagated = false;
        using var cts3 = new CancellationTokenSource();
        var sw3 = Stopwatch.StartNew();
        try
        {
            var w3 = new ClaimedAttemptWork(Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(), 1, 1, "attempt-c3", pdfBytes, SHA256.HashData(pdfBytes), pdfBytes.Length, 1);
            await runner.ExecuteAttemptAsync(
                w3,
                (pid, ft, _) => { c3LauncherPid = pid; c3LauncherFt = ft; return Task.FromResult(true); },
                (phase, wPid, wFt, _) =>
                {
                    if (phase == "inferring" && wPid is > 0 && wFt is > 0)
                    {
                        c3GrandchildPid = wPid.Value;
                        c3GrandchildFt = wFt.Value;
                        cts3.Cancel();
                    }
                    return Task.FromResult(true);
                },
                cts3.Token).WaitAsync(TimeSpan.FromSeconds(8));
        }
        catch (OperationCanceledException)
        {
            c3CanceledPropagated = true;
        }
        sw3.Stop();
        var c3BothDead = c3LauncherPid > 0 && c3GrandchildPid > 0 &&
                         !probe.IsProcessAlive(c3LauncherPid, c3LauncherFt) &&
                         !probe.IsProcessAlive(c3GrandchildPid, c3GrandchildFt);

        if (c1ExMsg != "simulated-pre-resume-db-error" || !c1Dead ||
            c2ExMsg != "simulated-mid-run-heartbeat-db-error" || !c2BothDead ||
            !c3CanceledPropagated || !c3BothDead)
        {
            throw new InvalidOperationException(
                $"R2b child containment failed: c1=({c1ExMsg},{c1Dead}), c2=({c2ExMsg},{c2BothDead}), c3=({c3CanceledPropagated},{c3BothDead})");
        }

        results["R2b_F2_S1_02_finally_job_termination_and_pipe_unblock"] = new
        {
            reconciled = true,
            pre_resume_throw_unmasked_and_launcher_dead = c1Dead,
            pre_resume_cleanup_ms = sw1.ElapsedMilliseconds,
            heartbeat_throw_unmasked_and_launcher_plus_grandchild_dead = c2BothDead,
            heartbeat_throw_cleanup_ms = sw2.ElapsedMilliseconds,
            cancellation_propagated_and_launcher_plus_grandchild_dead = c3BothDead,
            cancellation_cleanup_ms = sw3.ElapsedMilliseconds,
        };
    }
    finally
    {
        try { Directory.Delete(r2bRoot, true); } catch { }
    }
}

// =================================================================================================
// R2c & R3: Real PostgreSQL 18.7 (127.0.0.1:55435, runtime role eledgercare_app) probes:
//   - R2c: Same-instance & cross-instance abandoned 'running' reconciliation with REAL OS child
//          processes + heartbeat.json liveness check, zero live-owner theft, zero auto-retry!
//   - R3:  NUL bytes, unpaired surrogates, astral surrogate boundary splits (100 / 500 / 65,536),
//          truncated UTF-8 tails, diagnostics JSON \u0000 sanitization, AND 100% byte-for-byte
//          preservation of accepted ExtractionResult.RawOutputBytes (bytea) + OriginalArtifact.Bytes!
// =================================================================================================
var probeDb = $"eledgercare_rev_reconcile_{Guid.NewGuid().ToString("N")[..8]}";
await using (var admin = new NpgsqlConnection(AdminConn()))
{
    await admin.OpenAsync();
    await using (var cmd = new NpgsqlCommand($"CREATE DATABASE {probeDb} OWNER {migUser} ENCODING 'UTF8' TEMPLATE template0", admin))
        await cmd.ExecuteNonQueryAsync();
    await using (var cmd = new NpgsqlCommand($"GRANT CONNECT ON DATABASE {probeDb} TO {appUser}", admin))
        await cmd.ExecuteNonQueryAsync();
}

var r2cRtRoot = Path.Combine(Path.GetTempPath(), $"elc-rev-r2c-{Guid.NewGuid():N}");
Directory.CreateDirectory(r2cRtRoot);
try
{
    var migOpts = new DbContextOptionsBuilder<ELedgerCareDbContext>()
        .UseNpgsql(MigConn(probeDb), n => n.MigrationsHistoryTable("__ef_migrations_history", ELedgerCareDbContext.Schema))
        .Options;
    await using (var migDb = new ELedgerCareDbContext(migOpts))
        await migDb.Database.MigrateAsync();
    await using (var migConn = new NpgsqlConnection(MigConn(probeDb)))
    {
        await migConn.OpenAsync();
        var grantSql = await File.ReadAllTextAsync(Path.Combine(repoRoot, "deploy", "dev", "database", "grant-runtime.sql"));
        await using var gCmd = new NpgsqlCommand(grantSql, migConn);
        await gCmd.ExecuteNonQueryAsync();
    }

    var appOpts = new DbContextOptionsBuilder<ELedgerCareDbContext>().UseNpgsql(AppConn(probeDb)).Options;
    var intakeStore = new IntakeStore(new PooledContextFactory(appOpts));
    var extractionStore = new ExtractionStore(new PooledContextFactory(appOpts));
    var realProbe = new WindowsProcessIdentityProbe();
    var t0 = new DateTimeOffset(2026, 11, 16, 15, 0, 0, TimeSpan.Zero);

    var pdf1 = await File.ReadAllBytesAsync(Path.Combine(repoRoot, "tests", "fixtures", "F1-SWO-001.pdf"));
    var pdf3 = await File.ReadAllBytesAsync(Path.Combine(repoRoot, "tests", "fixtures", "SYN-MP-01-v0-clean.pdf"));

    // --- R2c: Real-process + real-PG reconciliation probe ---
    var docActive = Document.Submit(Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(), pdf1, 1, t0);
    var docOtherSup = Document.Submit(Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(), pdf1, 1, t0);
    var docOrphan = Document.Submit(Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(), pdf1, 1, t0);
    await intakeStore.InsertAsync(docActive, CancellationToken.None);
    await intakeStore.InsertAsync(docOtherSup, CancellationToken.None);
    await intakeStore.InsertAsync(docOrphan, CancellationToken.None);

    var r2cSettings = new ExtractionSettings(
        true, 3, r2cRtRoot, r2cRtRoot, "GPU-00000000-0000-0000-0000-000000000000",
        workerRoot, manifestSha, lockSha, workerSha);
    var realRunnerForHeartbeat = new LocalPythonOcrWorkerRunner(r2cSettings);

    // 1) In-flight execution on coordinatorA must NOT be stolen by coordinatorA.ReconcileAbandonedAttemptsAsync
    var gateRunner = new GatedRunner(realRunnerForHeartbeat);
    var coordinatorA = new ExtractionAttemptCoordinator(extractionStore, gateRunner, realProbe, r2cSettings, TimeProvider.System);
    var coordinatorB = new ExtractionAttemptCoordinator(extractionStore, realRunnerForHeartbeat, realProbe, r2cSettings, TimeProvider.System);

    await extractionStore.QueueOrReconcileAsync(docActive.DocumentId, null, 3, true, t0.AddSeconds(1), CancellationToken.None);
    var inFlightTask = coordinatorA.ExecuteNextQueuedAttemptAsync(CancellationToken.None);
    await gateRunner.Entered.Task.WaitAsync(TimeSpan.FromSeconds(10));
    var reconciledWhileActive = await coordinatorA.ReconcileAbandonedAttemptsAsync(CancellationToken.None);
    gateRunner.Release.TrySetResult();
    await inFlightTask;

    // 2) Live other-supervisor attempt (coordinatorB in current live OS process) must NOT be stolen by coordinatorA
    await extractionStore.QueueOrReconcileAsync(docOtherSup.DocumentId, null, 3, true, t0.AddSeconds(2), CancellationToken.None);
    var otherClaim = (await extractionStore.ClaimNextQueuedJobAsync(
        coordinatorB.SupervisorInstanceId,
        coordinatorB.SupervisorIdentity.Pid,
        coordinatorB.SupervisorIdentity.CreateFileTime,
        t0.AddSeconds(3),
        CancellationToken.None))!;
    var reconciledLiveOtherSupervisor = await coordinatorA.ReconcileAbandonedAttemptsAsync(CancellationToken.None);
    // Cleanly mark coordinatorB's claim failed so it doesn't interfere with step 3
    await extractionStore.MarkAttemptFailedAsync(
        otherClaim.AttemptId, otherClaim.JobId, otherClaim.FencingToken,
        "worker_failed", "Done testing live other supervisor protection.", 1, null, null, t0.AddSeconds(4), CancellationToken.None);

    // 3) Orphaned 'running' row under coordinatorA.SupervisorInstanceId with a REAL OS child recorded ONLY in heartbeat.json!
    await extractionStore.QueueOrReconcileAsync(docOrphan.DocumentId, null, 3, true, t0.AddSeconds(5), CancellationToken.None);
    var orphanClaim = (await extractionStore.ClaimNextQueuedJobAsync(
        coordinatorA.SupervisorInstanceId,
        coordinatorA.SupervisorIdentity.Pid,
        coordinatorA.SupervisorIdentity.CreateFileTime,
        t0.AddSeconds(6),
        CancellationToken.None))!;

    var hbOutDir = Path.Combine(r2cRtRoot, "runs", orphanClaim.RunDirectoryName, "output");
    Directory.CreateDirectory(hbOutDir);

    int reconciledWhileHeartbeatChildAlive;
    using (var liveWorker = Process.Start(new ProcessStartInfo(hostPy)
    {
        ArgumentList = { "-I", "-c", "import time; time.sleep(30)" },
        UseShellExecute = false,
        CreateNoWindow = true,
    })!)
    {
        try
        {
            var liveFt = liveWorker.StartTime.ToFileTimeUtc();
            var hbJson = JsonSerializer.Serialize(new
            {
                phase = "inferring",
                worker_pid = liveWorker.Id,
                worker_create_filetime = liveFt,
                phase_timeout_s = 1800,
                stall_monitored = true,
                forward_progress = 2,
            });
            await File.WriteAllTextAsync(Path.Combine(hbOutDir, "heartbeat.json"), hbJson, Encoding.UTF8);

            // Real child is alive and recorded only in heartbeat.json -> coordinatorA must NOT reconcile yet!
            reconciledWhileHeartbeatChildAlive = await coordinatorA.ReconcileAbandonedAttemptsAsync(CancellationToken.None);
        }
        finally
        {
            try { liveWorker.Kill(entireProcessTree: true); } catch { }
            await liveWorker.WaitForExitAsync();
        }
    }

    // Now the real child has exited, while coordinatorA (same live API process) is still running -> must reconcile 1 row to 'interrupted'!
    var reconciledAfterChildExited = await coordinatorA.ReconcileAbandonedAttemptsAsync(CancellationToken.None);
    var autoClaimedAfterInterrupt = await coordinatorA.ExecuteNextQueuedAttemptAsync(CancellationToken.None);
    var orphanSnap = (await extractionStore.GetDocumentExtractionAsync(docOrphan.DocumentId, CancellationToken.None))!;
    // Explicit retry with orphanClaim.AttemptId must then succeed cleanly!
    var explicitRetryOutcome = await extractionStore.QueueOrReconcileAsync(
        docOrphan.DocumentId, orphanClaim.AttemptId, 3, true, t0.AddSeconds(10), CancellationToken.None);

    if (reconciledWhileActive != 0 ||
        reconciledLiveOtherSupervisor != 0 ||
        reconciledWhileHeartbeatChildAlive != 0 ||
        reconciledAfterChildExited != 1 ||
        autoClaimedAfterInterrupt ||
        orphanSnap.Status != ProcessingStatus.Interrupted ||
        orphanSnap.Attempts.Count != 1 ||
        orphanSnap.Attempts[0].FailureCode != "supervisor_interrupted" ||
        explicitRetryOutcome is not QueueExtractionOutcome.QueuedOrActive)
    {
        throw new InvalidOperationException(
            $"R2c reconciliation assertion failed: active={reconciledWhileActive}, otherSup={reconciledLiveOtherSupervisor}, hbAlive={reconciledWhileHeartbeatChildAlive}, afterExit={reconciledAfterChildExited}, autoRetry={autoClaimedAfterInterrupt}, status={orphanSnap.Status}");
    }

    results["R2c_F2_S1_02_same_and_cross_instance_reconciliation_real_pg"] = new
    {
        reconciled = true,
        reconciled_while_same_coordinator_in_flight = reconciledWhileActive,
        reconciled_while_other_live_supervisor_owns = reconciledLiveOtherSupervisor,
        reconciled_while_real_heartbeat_worker_alive = reconciledWhileHeartbeatChildAlive,
        reconciled_by_same_live_coordinator_once_children_exited = reconciledAfterChildExited,
        reconciled_status = orphanSnap.Status.ToWire(),
        automatic_retry_triggered = autoClaimedAfterInterrupt,
        explicit_retry_allowed_after_interrupted = explicitRetryOutcome is QueueExtractionOutcome.QueuedOrActive,
    };

    // --- R3: Reconcile F2-S1-03 — PostgreSQL text/jsonb sanitization + exact bytea preservation ---
    var docDiag1 = Document.Submit(Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(), pdf1, 1, t0.AddSeconds(20));
    var docDiag2 = Document.Submit(Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(), pdf1, 1, t0.AddSeconds(21));
    var docAccepted1 = Document.Submit(Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(), pdf1, 1, t0.AddSeconds(22));
    var docAccepted3 = Document.Submit(Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(), pdf3, 3, t0.AddSeconds(23));
    await intakeStore.InsertAsync(docDiag1, CancellationToken.None);
    await intakeStore.InsertAsync(docDiag2, CancellationToken.None);
    await intakeStore.InsertAsync(docAccepted1, CancellationToken.None);
    await intakeStore.InsertAsync(docAccepted3, CancellationToken.None);

    // R3a: Exact Stage 1 Probe P4 NUL byte in raw preview + truncated 4-byte UTF-8 tail [0xF0, 0x9F, 0x98] + \0 in phase heartbeat
    await extractionStore.QueueOrReconcileAsync(docDiag1.DocumentId, null, 3, true, t0.AddSeconds(24), CancellationToken.None);
    var claimD1 = (await extractionStore.ClaimNextQueuedJobAsync(Guid.NewGuid(), 9101, 133700000000009101L, t0.AddSeconds(25), CancellationToken.None))!;
    var hbOk = await extractionStore.RecordHeartbeatAsync(
        claimD1.AttemptId, claimD1.FencingToken,
        new string('p', 63) + "\U0001F600" + "\0",
        9102, 133700000000009102L, t0.AddSeconds(26), CancellationToken.None);
    byte[] rawNulAndTruncTail = [(byte)'<', (byte)'P', (byte)'A', (byte)'G', (byte)'E', (byte)'>', 0x00, (byte)'X', 0xF0, 0x9F, 0x98];
    var nulRej = (EnvelopeValidationOutcome.Rejected)WorkerEnvelopeValidator.Validate(
        claimD1, r2cSettings,
        new WorkerRunOutcome(null, rawNulAndTruncTail, 1, "bad\0code_" + new string('c', 90) + "\U0001F600", "detail\0" + new string('d', 492) + "\U0001F600"),
        t0.AddSeconds(27));
    var d1FailedOk = await extractionStore.MarkAttemptFailedAsync(
        claimD1.AttemptId, claimD1.JobId, claimD1.FencingToken,
        nulRej.FailureCode, nulRej.SafeDetail, 1,
        nulRej.DiagnosticRawOutputUtf8, "{\"k\\u0000ey\":\"val\\u0000ue\",\"arr\":[\"x\\u0000y\"]}",
        t0.AddSeconds(27), CancellationToken.None);

    // R3b: Exact Stage 1 Probe P4 unpaired surrogates + astral surrogate straddling 65,535/65,536
    await extractionStore.QueueOrReconcileAsync(docDiag2.DocumentId, null, 3, true, t0.AddSeconds(28), CancellationToken.None);
    var claimD2 = (await extractionStore.ClaimNextQueuedJobAsync(Guid.NewGuid(), 9201, 133700000000009201L, t0.AddSeconds(29), CancellationToken.None))!;
    var boundary65536 = new string('A', 65_535) + "\U0001F600";
    var unpairedDetail = "Unpaired high=" + '\uD800' + " low=" + '\uDC00' + " nul=\0";
    var d2FailedOk = await extractionStore.MarkAttemptFailedAsync(
        claimD2.AttemptId, claimD2.JobId, claimD2.FencingToken,
        new string('k', 99) + "\U0001F600",
        unpairedDetail,
        2,
        boundary65536,
        "not-valid-json-should-become-null",
        t0.AddSeconds(30),
        CancellationToken.None);

    // Inspect persisted diagnostic lengths and NUL absence directly in PostgreSQL 18.7
    int d1CodeLen, d1DetailLen, d2CodeLen, d2DiagLen;
    string d1JsonType;
    bool d2JsonIsNull;
    await using (var vConn = new NpgsqlConnection(AppConn(probeDb)))
    {
        await vConn.OpenAsync();
        await using (var cmd1 = new NpgsqlCommand(
            "SELECT char_length(failure_code), char_length(failure_detail), jsonb_typeof(diagnostic_metadata_json) FROM eledgercare.execution_attempts WHERE attempt_id = @id",
            vConn))
        {
            cmd1.Parameters.AddWithValue("id", claimD1.AttemptId);
            await using var r = await cmd1.ExecuteReaderAsync();
            await r.ReadAsync();
            d1CodeLen = r.GetInt32(0);
            d1DetailLen = r.GetInt32(1);
            d1JsonType = r.GetString(2);
        }
        await using (var cmd2 = new NpgsqlCommand(
            "SELECT char_length(failure_code), char_length(diagnostic_raw_output_utf8), diagnostic_metadata_json IS NULL FROM eledgercare.execution_attempts WHERE attempt_id = @id",
            vConn))
        {
            cmd2.Parameters.AddWithValue("id", claimD2.AttemptId);
            await using var r = await cmd2.ExecuteReaderAsync();
            await r.ReadAsync();
            d2CodeLen = r.GetInt32(0);
            d2DiagLen = r.GetInt32(1);
            d2JsonIsNull = r.GetBoolean(2);
        }
    }

    // R3c: Accepted results (1-page rich multi-byte UTF-8 + 3-page real Q0 F07.warm1.raw.txt) preserve 100% exact bytea!
    await extractionStore.QueueOrReconcileAsync(docAccepted1.DocumentId, null, 3, true, t0.AddSeconds(31), CancellationToken.None);
    var claimAcc1 = (await extractionStore.ClaimNextQueuedJobAsync(Guid.NewGuid(), 9301, 133700000000009301L, t0.AddSeconds(32), CancellationToken.None))!;
    var richUtf8Bytes = new UTF8Encoding(false).GetBytes("<PAGE>\nInvoice €1,234.56 — Temp 25°C — Astral 🧾🔧 — CJK 保養記録\r\nLine 2\n");
    var richSha = SHA256.HashData(richUtf8Bytes);
    var acc1Envelope = JsonSerializer.SerializeToUtf8Bytes(new
    {
        schema = ExtractionCeilings.EnvelopeSchema,
        status = "completed",
        document_id = claimAcc1.DocumentId.ToString("D"),
        job_id = claimAcc1.JobId.ToString("D"),
        attempt_id = claimAcc1.AttemptId.ToString("D"),
        fencing_token = claimAcc1.FencingToken,
        input = new { sha256 = Convert.ToHexStringLower(claimAcc1.InputSha256), byte_length = claimAcc1.InputByteLength, page_count = 1 },
        provenance = new
        {
            model_repo_id = ExtractionCeilings.ModelRepoId,
            model_revision = ExtractionCeilings.ModelRevision,
            model_manifest_sha256 = Convert.ToHexStringLower(manifestSha),
            dependency_lock_sha256 = Convert.ToHexStringLower(lockSha),
            worker_source_sha256 = actualWorkerHex,
            worker_config_sha256 = Convert.ToHexStringLower(ExtractionSettings.ComputeWorkerConfigSha256(1)),
            renderer_identity = "pypdfium2==5.15.2;pdfium=159.0.8149.0;dpi=300;rgb",
            provenance_exceptions = new[] { ExtractionCeilings.RequiredProvenanceException },
            generation_settings = new { temperature = 0.0, max_new_tokens = 8000 },
        },
        output = new { finish_reason = "stop", output_page_count = 1, byte_length = richUtf8Bytes.Length, sha256 = Convert.ToHexStringLower(richSha) },
        timings = new { started_at_utc = "2026-11-16T15:00:31Z", completed_at_utc = "2026-11-16T15:00:35Z", load_duration_ms = 10L, render_duration_ms = 5L, infer_duration_ms = 100L, total_duration_ms = 115L },
        diagnostics = new { kernel_path = "triton_import_failed_dense_fallback", note = "accepted\0diag" },
    });
    var acc1Val = (EnvelopeValidationOutcome.Accepted)WorkerEnvelopeValidator.Validate(
        claimAcc1, r2cSettings, new WorkerRunOutcome(acc1Envelope, richUtf8Bytes, 0, null, null), t0.AddSeconds(35));
    var acc1PubOk = await extractionStore.PublishCompletedResultAsync(acc1Val.Result, 0, t0.AddSeconds(35), CancellationToken.None);

    // Also persist real 3-page Q0 F07.warm1.raw.txt bytes and verify byte-for-byte identity
    var q0F07Bytes = await File.ReadAllBytesAsync(Path.Combine(
        repoRoot, "qualification", "q0", "harness", "evidence",
        "004-gpu-trial", "9e73ef86", "run-20261115T202627Z-eb5bf7da", "evidence", "F07.warm1.raw.txt"));
    var q0F07Sha = SHA256.HashData(q0F07Bytes);
    await extractionStore.QueueOrReconcileAsync(docAccepted3.DocumentId, null, 3, true, t0.AddSeconds(36), CancellationToken.None);
    var claimAcc3 = (await extractionStore.ClaimNextQueuedJobAsync(Guid.NewGuid(), 9302, 133700000000009302L, t0.AddSeconds(37), CancellationToken.None))!;
    var acc3Envelope = JsonSerializer.SerializeToUtf8Bytes(new
    {
        schema = ExtractionCeilings.EnvelopeSchema,
        status = "completed",
        document_id = claimAcc3.DocumentId.ToString("D"),
        job_id = claimAcc3.JobId.ToString("D"),
        attempt_id = claimAcc3.AttemptId.ToString("D"),
        fencing_token = claimAcc3.FencingToken,
        input = new { sha256 = Convert.ToHexStringLower(claimAcc3.InputSha256), byte_length = claimAcc3.InputByteLength, page_count = 3 },
        provenance = new
        {
            model_repo_id = ExtractionCeilings.ModelRepoId,
            model_revision = ExtractionCeilings.ModelRevision,
            model_manifest_sha256 = Convert.ToHexStringLower(manifestSha),
            dependency_lock_sha256 = Convert.ToHexStringLower(lockSha),
            worker_source_sha256 = actualWorkerHex,
            worker_config_sha256 = Convert.ToHexStringLower(ExtractionSettings.ComputeWorkerConfigSha256(3)),
            renderer_identity = "pypdfium2==5.15.2;pdfium=159.0.8149.0;dpi=300;rgb",
            provenance_exceptions = new[] { ExtractionCeilings.RequiredProvenanceException },
            generation_settings = new { temperature = 0.0, max_new_tokens = 24000 },
        },
        output = new { finish_reason = "stop", output_page_count = 3, byte_length = q0F07Bytes.Length, sha256 = Convert.ToHexStringLower(q0F07Sha) },
        timings = new { started_at_utc = "2026-11-16T15:00:36Z", completed_at_utc = "2026-11-16T15:05:09Z", load_duration_ms = 1000L, render_duration_ms = 120L, infer_duration_ms = 273174L, total_duration_ms = 274294L },
        diagnostics = new { kernel_path = "triton_import_failed_dense_fallback" },
    });
    var acc3Val = (EnvelopeValidationOutcome.Accepted)WorkerEnvelopeValidator.Validate(
        claimAcc3, r2cSettings, new WorkerRunOutcome(acc3Envelope, q0F07Bytes, 0, null, null), t0.AddSeconds(40));
    var acc3PubOk = await extractionStore.PublishCompletedResultAsync(acc3Val.Result, 0, t0.AddSeconds(40), CancellationToken.None);

    var snapAcc1 = (await extractionStore.GetDocumentExtractionAsync(docAccepted1.DocumentId, CancellationToken.None))!;
    var snapAcc3 = (await extractionStore.GetDocumentExtractionAsync(docAccepted3.DocumentId, CancellationToken.None))!;
    byte[] dbOrigPdf3Bytes;
    await using (var bConn = new NpgsqlConnection(AppConn(probeDb)))
    {
        await bConn.OpenAsync();
        await using var bCmd = new NpgsqlCommand("SELECT bytes FROM eledgercare.original_artifacts WHERE document_id = @id", bConn);
        bCmd.Parameters.AddWithValue("id", docAccepted3.DocumentId);
        dbOrigPdf3Bytes = (byte[])(await bCmd.ExecuteScalarAsync())!;
    }

    var richByteExact = CryptographicOperations.FixedTimeEquals(snapAcc1.AcceptedResult!.RawOutputBytes, richUtf8Bytes) &&
                        CryptographicOperations.FixedTimeEquals(snapAcc1.AcceptedResult.RawOutputSha256, richSha);
    var q0F07ByteExact = CryptographicOperations.FixedTimeEquals(snapAcc3.AcceptedResult!.RawOutputBytes, q0F07Bytes) &&
                         CryptographicOperations.FixedTimeEquals(snapAcc3.AcceptedResult.RawOutputSha256, q0F07Sha);
    var origPdf3ByteExact = CryptographicOperations.FixedTimeEquals(dbOrigPdf3Bytes, pdf3);

    if (!hbOk || !d1FailedOk || !d2FailedOk || d1CodeLen != 99 || d1DetailLen != 499 || d1JsonType != "object" ||
        d2CodeLen != 99 || d2DiagLen != 65_535 || !d2JsonIsNull ||
        !acc1PubOk || !acc3PubOk || !richByteExact || !q0F07ByteExact || !origPdf3ByteExact)
    {
        throw new InvalidOperationException(
            $"R3 PostgreSQL diagnostic/bytea assertion failed: hb={hbOk}, d1={d1FailedOk}({d1CodeLen},{d1DetailLen},{d1JsonType}), d2={d2FailedOk}({d2CodeLen},{d2DiagLen},{d2JsonIsNull}), acc1={acc1PubOk}/{richByteExact}, acc3={acc3PubOk}/{q0F07ByteExact}, orig={origPdf3ByteExact}");
    }

    results["R3_F2_S1_03_postgres_diagnostic_sanitization_and_exact_bytea"] = new
    {
        reconciled = true,
        heartbeat_phase_nul_and_surrogate_persisted = hbOk,
        nul_and_truncated_utf8_tail_failed_persisted = d1FailedOk,
        failure_code_surrogate_boundary_char_len = d1CodeLen,
        failure_detail_surrogate_boundary_char_len = d1DetailLen,
        diagnostic_jsonb_nul_sanitized_type = d1JsonType,
        unpaired_surrogates_and_65536_boundary_persisted = d2FailedOk,
        diagnostic_raw_65536_boundary_char_len = d2DiagLen,
        malformed_diagnostic_json_coerced_to_null = d2JsonIsNull,
        accepted_multibyte_utf8_with_nul_in_diagnostics_published = acc1PubOk,
        accepted_multibyte_raw_bytea_100pct_exact = richByteExact,
        accepted_q0_f07_3page_raw_bytea_100pct_exact = q0F07ByteExact,
        original_artifact_pdf_bytea_100pct_exact = origPdf3ByteExact,
    };
}
finally
{
    try { Directory.Delete(r2cRtRoot, true); } catch { }
    await using var admin2 = new NpgsqlConnection(AdminConn());
    await admin2.OpenAsync();
    await using var dropCmd = new NpgsqlCommand($"DROP DATABASE IF EXISTS {probeDb} WITH (FORCE)", admin2);
    await dropCmd.ExecuteNonQueryAsync();
}

var jsonOut = JsonSerializer.Serialize(results, new JsonSerializerOptions { WriteIndented = true });
await File.WriteAllTextAsync(outputJsonPath, jsonOut, new UTF8Encoding(false));
Console.WriteLine("Wrote reconciliation probe results JSON.");

sealed class PooledContextFactory(DbContextOptions<ELedgerCareDbContext> options) : IDbContextFactory<ELedgerCareDbContext>
{
    public ELedgerCareDbContext CreateDbContext() => new(options);
}

sealed class GatedRunner(ILocalOcrWorkerRunner inner) : ILocalOcrWorkerRunner
{
    public TaskCompletionSource Entered { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
    public TaskCompletionSource Release { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

    public OsProcessIdentity? TryReadRecordedWorkerIdentity(string runDirectoryName) =>
        inner.TryReadRecordedWorkerIdentity(runDirectoryName);

    public async Task<WorkerRunOutcome> ExecuteAttemptAsync(
        ClaimedAttemptWork work,
        Func<int, long, CancellationToken, Task<bool>> onLauncherAssignedBeforeResumeAsync,
        Func<string, int?, long?, CancellationToken, Task<bool>> onHeartbeatAsync,
        CancellationToken cancellationToken)
    {
        await onLauncherAssignedBeforeResumeAsync(Environment.ProcessId, Process.GetCurrentProcess().StartTime.ToFileTimeUtc(), cancellationToken);
        Entered.TrySetResult();
        await Release.Task.WaitAsync(cancellationToken);
        return new WorkerRunOutcome(null, null, 1, "worker_timeout", "Simulated gated attempt finished.");
    }
}
'''


def parse_dotnet_test_counts(log_bytes: bytes) -> dict:
    txt = log_bytes.decode("utf-8", errors="replace")
    # Match per-assembly summary lines in Microsoft.Testing.Platform / dotnet test output
    passed_matches = [int(m) for m in re.findall(r"succeeded:\s*(\d+)", txt, flags=re.IGNORECASE)]
    if not passed_matches:
        passed_matches = [int(m) for m in re.findall(r"Passed!\s*-\s*Failed:\s*0,\s*Passed:\s*(\d+)", txt)]
    failed_matches = [int(m) for m in re.findall(r"failed:\s*(\d+)", txt, flags=re.IGNORECASE)]
    return {
        "raw_matches_succeeded": passed_matches,
        "any_nonzero_failed": any(x != 0 for x in failed_matches),
    }


def run_csharp_reconciliation_probes(env: dict[str, str], logs_dir: Path, secrets_to_redact: list[str]) -> dict:
    probe_dir = REPO_ROOT / ".scratch" / "reconciliation-probes"
    if probe_dir.exists():
        shutil.rmtree(probe_dir)
    probe_dir.mkdir(parents=True, exist_ok=True)
    try:
        (probe_dir / "ReviewerReconciliationProbes.csproj").write_text(
            CSHARP_PROBE_CSPROJ.format(repo_root=str(REPO_ROOT)), encoding="utf-8"
        )
        (probe_dir / "Program.cs").write_text(CSHARP_PROBE_PROGRAM, encoding="utf-8")
        fake_worker_tpl = probe_dir / "fake_run_worker.py"
        fake_worker_tpl.write_text(FAKE_GRANDCHILD_WORKER_PY, encoding="utf-8")
        out_json_path = probe_dir / "reconciliation-probe-results.json"

        build_step = run_logged_step(
            "06-build-reviewer-reconciliation-probes",
            [
                "dotnet", "build", str(probe_dir / "ReviewerReconciliationProbes.csproj"),
                "-c", "Release",
                "--source", str(REPO_ROOT / ".local" / "nuget" / "packages"),
            ],
            cwd=probe_dir,
            env=env,
            logs_dir=logs_dir,
            secrets_to_redact=secrets_to_redact,
        )
        exe_path = probe_dir / "bin" / "Release" / "net10.0" / "ReviewerReconciliationProbes.exe"
        run_step = run_logged_step(
            "07-execute-reviewer-reconciliation-probes",
            [str(exe_path), str(REPO_ROOT), str(out_json_path), EXPECTED_NEW_WORKER_SOURCE_SHA256, str(fake_worker_tpl)],
            cwd=probe_dir,
            env=env,
            logs_dir=logs_dir,
            secrets_to_redact=secrets_to_redact,
        )
        probe_json = json.loads(out_json_path.read_text(encoding="utf-8"))
        return {
            "build_step": build_step,
            "run_step": run_step,
            "results": probe_json,
        }
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)


def main() -> int:
    started_utc = utc_now()
    if EXTERNAL_F2_REVIEWER_ROOT.exists():
        raise RuntimeError(f"External F2 reviewer root must not exist during source reconciliation: {EXTERNAL_F2_REVIEWER_ROOT}")

    pg_settings = json.loads((REPO_ROOT / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
    if int(pg_settings["port"]) != REVIEWER_PG_PORT:
        raise RuntimeError(f"Unexpected reviewer PG port {pg_settings['port']} != {REVIEWER_PG_PORT}")
    secrets_to_redact = [
        str(pg_settings.get("adminPassword") or ""),
        str(pg_settings.get("migratorPassword") or ""),
        str(pg_settings.get("appPassword") or ""),
    ]

    for port in (REVIEWER_API_PORT, REVIEWER_UI_PORT, REVIEWER_PG_PORT):
        if is_loopback_port_bound(port):
            raise RuntimeError(f"Reviewer port {port} is already bound before reconciliation start!")

    pre_host = host_memory_and_cpu_snapshot()
    lineage = verify_lineage_scope_and_author_publication()
    static_audit = verify_static_digests_and_production_boundaries()
    py_probes = run_python_storage_and_isolation_probes()

    logs_dir = REPO_ROOT / ".scratch" / "source-reconciliation-logs"
    if logs_dir.exists():
        shutil.rmtree(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    env = build_base_env()
    steps: list[dict] = []
    pg_started = False
    postmaster_identity: dict | None = None
    probe_bundle: dict | None = None

    try:
        steps.append(run_logged_step(
            "00-start-owned-postgres",
            ["pwsh", "-NoProfile", "-File", str(REPO_ROOT / "deploy" / "dev" / "postgres" / "start-cluster.ps1")],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        pg_started = True
        pm_pid = int((REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        postmaster_identity = {
            "pid": pm_pid,
            "create_filetime": current_or_pid_filetime(pm_pid),
            "port": REVIEWER_PG_PORT,
            "roles_configured": [
                str(pg_settings["adminUser"]),
                str(pg_settings["migratorUser"]),
                str(pg_settings["appUser"]),
            ],
        }

        steps.append(run_logged_step(
            "01-dotnet-restore-locked",
            [
                "dotnet", "restore", "ELedgerCare.slnx", "--locked-mode",
                "--packages", str(REPO_ROOT / ".local" / "nuget" / "packages"),
            ],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        steps.append(run_logged_step(
            "02-dotnet-build-release",
            ["dotnet", "build", "ELedgerCare.slnx", "-c", "Release", "--no-restore"],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        steps.append(run_logged_step(
            "03-dotnet-publish-api",
            ["dotnet", "publish", "src/ELedgerCare.Api/ELedgerCare.Api.csproj", "-c", "Release", "--no-restore"],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        steps.append(run_logged_step(
            "04-python-worker-cpu-tests",
            [str(HOST_PYTHON_EXE), "-B", "-m", "unittest", "discover", "-s", "workers/local_ocr/tests", "-p", "test_*.py", "-v"],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        steps.append(run_logged_step(
            "05-dotnet-test-solution",
            ["dotnet", "test", "--solution", "ELedgerCare.slnx", "-c", "Release", "--no-build"],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))

        probe_bundle = run_csharp_reconciliation_probes(env, logs_dir, secrets_to_redact)
        steps.append(probe_bundle["build_step"])
        steps.append(probe_bundle["run_step"])
    finally:
        if pg_started:
            steps.append(run_logged_step(
                "08-stop-owned-postgres",
                ["pwsh", "-NoProfile", "-File", str(REPO_ROOT / "deploy" / "dev" / "postgres" / "stop-cluster.ps1")],
                cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
                check=False,
            ))

    for port in (REVIEWER_API_PORT, REVIEWER_UI_PORT, REVIEWER_PG_PORT):
        if is_loopback_port_bound(port):
            raise RuntimeError(f"Reviewer port {port} remained bound after teardown!")

    if EXTERNAL_F2_REVIEWER_ROOT.exists():
        raise RuntimeError(f"External F2 reviewer root was unexpectedly created: {EXTERNAL_F2_REVIEWER_ROOT}")

    loaded_heavy_end = [m for m in ("torch", "transformers", "pypdfium2") if m in sys.modules]
    if loaded_heavy_end:
        raise RuntimeError(f"Forbidden heavy ML modules imported during reconciliation: {loaded_heavy_end}")

    py_log = (logs_dir / "04-python-worker-cpu-tests.log").read_text(encoding="utf-8", errors="replace")
    py_ran_m = re.search(r"Ran\s+(\d+)\s+tests", py_log)
    py_test_count = int(py_ran_m.group(1)) if py_ran_m else 0
    if py_test_count != 9 or "OK" not in py_log:
        raise RuntimeError(f"Expected 9 passing Python worker CPU tests, saw count={py_test_count}")

    dotnet_log = (logs_dir / "05-dotnet-test-solution.log").read_bytes()
    dotnet_parsed = parse_dotnet_test_counts(dotnet_log)
    if dotnet_parsed["any_nonzero_failed"] or sum(dotnet_parsed["raw_matches_succeeded"]) != 74:
        raise RuntimeError(f"Expected 74 passing .NET tests with 0 failures, got: {dotnet_parsed}")

    post_host = host_memory_and_cpu_snapshot()
    post_porcelain = run_git(["status", "--porcelain"]).strip()

    summary = {
        "schema": "eledgercare.wp-0006.reviewer-source-reconciliation/1",
        "reviewer": "eld-next-reviewer",
        "conversation_id": "101b19cf-3133-4ead-91cb-9ca6068e3e72",
        "model": "gemini-4-carbon-high",
        "effort": "high",
        "started_utc": started_utc,
        "completed_utc": utc_now(),
        "source_reconciliation_disposition": "accepted_stage1_source_pending_runtime",
        "canonical_004_status": "held_pending_stage2_gpu_and_recovery_release",
        "findings_reconciled": {
            "F2-S1-01": {
                "prior_status": "open_blocking",
                "reconciled_status": "resolved",
                "verified_in_candidate": AUTHOR_CANDIDATE_SHA,
            },
            "F2-S1-02": {
                "prior_status": "open_blocking",
                "reconciled_status": "resolved",
                "verified_in_candidate": AUTHOR_CANDIDATE_SHA,
            },
            "F2-S1-03": {
                "prior_status": "open_blocking",
                "reconciled_status": "resolved",
                "verified_in_candidate": AUTHOR_CANDIDATE_SHA,
            },
        },
        "new_findings_count": 0,
        "lineage_and_scope": lineage,
        "static_digests_and_boundaries": static_audit,
        "host_snapshots": {
            "before": pre_host,
            "after": post_host,
        },
        "external_roots": {
            "f2_reviewer_root_path": str(EXTERNAL_F2_REVIEWER_ROOT),
            "f2_reviewer_root_exists_before": False,
            "f2_reviewer_root_exists_after": EXTERNAL_F2_REVIEWER_ROOT.exists(),
            "f2_parent_root_exists_readonly": EXTERNAL_F2_PARENT_ROOT.exists(),
        },
        "owned_postgres_cluster": {
            "port": REVIEWER_PG_PORT,
            "postmaster_identity": postmaster_identity,
            "stopped_cleanly_at_end": not is_loopback_port_bound(REVIEWER_PG_PORT),
        },
        "regression_test_totals": {
            "python_worker_cpu_passed": py_test_count,
            "dotnet_succeeded_matches": dotnet_parsed["raw_matches_succeeded"],
            "dotnet_total_passed": sum(dotnet_parsed["raw_matches_succeeded"]),
            "combined_passed": py_test_count + sum(dotnet_parsed["raw_matches_succeeded"]),
            "combined_failed": 0,
            "reused_stage1_playwright_edge_passed": 10,
        },
        "independent_python_boundary_probes": py_probes,
        "independent_csharp_and_postgres_boundary_probes": probe_bundle["results"] if probe_bundle else None,
        "steps": steps,
        "post_git_porcelain_before_evidence_write": post_porcelain,
    }

    out_path = REVIEW_DIR / "reconciliation-verification-summary.json"
    out_text = json.dumps(summary, indent=2) + "\n"
    for s in secrets_to_redact:
        if s and s in out_text:
            raise RuntimeError("Secret leak detected in summary output; aborting!")
    for tok in FORBIDDEN_HOLDOUT_TOKENS:
        if tok in out_text:
            raise RuntimeError(f"Unexpected holdout token {tok} in summary output; aborting!")

    out_path.write_text(out_text, encoding="utf-8", newline="\n")
    print(f"Wrote {out_path} successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
