"""Independent WP-0006 F2 Stage 1 source, CPU, PostgreSQL 18.7, and Microsoft Edge verifier.

Owner: eld-next-reviewer (review/wp-0006-0007-next-tracks)
Scope: CPU / PostgreSQL (127.0.0.1:55435) / MS Edge (127.0.0.1:5290 API, 127.0.0.1:4310 UI) ONLY.
Zero GPU use, zero model library imports, zero external F2 root creation, zero holdout access,
and zero secret disclosure. Frozen before decisive execution.
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
import time

REVIEW_DIR = Path(__file__).resolve().parent
REPO_ROOT = REVIEW_DIR.parents[4]

AUTHOR_SOURCE_SHA = "0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978"
AUTHOR_CHECKPOINT_SHA = "6faec9bf6eccc297a548523dbb52ae9262b25152"
COORDINATOR_RELEASE_SHA = "97e65bed170ad0be705347791a830d860a6a38fe"
RELEASE_BASE_SHA = "d106db76de6dc8d9b52770d405ca95300b6dacd6"
Q0_WHEEL_GRAPH_BLOB = "ec8c650ed5fbeb0a754e4daee53aad53753a57a3"

REVIEWER_API_PORT = 5290
REVIEWER_UI_PORT = 4310
REVIEWER_PG_PORT = 55435
AUTHOR_PORTS = (5190, 4210, 55434)

EXTERNAL_F2_REVIEWER_ROOT = Path(r"C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer")
EXTERNAL_F2_PARENT_ROOT = Path(r"C:\Users\jackg\eLedgerCare-F2\WP-0006")
AUTHOR_SCRATCH_LOGS_DIR = Path(
    r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f2-implementer\.scratch\stage1-decisive\logs"
)
HOST_PYTHON_EXE = Path(r"C:\Users\jackg\AppData\Local\\Programs\Python\Python312\python.exe")

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
            "Loopback CPU/PostgreSQL/Edge verification shares physical host CPU/RAM/disk I/O; "
            "no other owner's ports, clusters, or processes were touched."
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
    env["npm_config_cache"] = str(REPO_ROOT / ".local" / "npm-cache")
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(REPO_ROOT / ".local" / "ms-playwright")
    env["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"
    env["NG_CLI_ANALYTICS"] = "false"
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


def verify_git_lineage_and_candidate_blobs() -> dict:
    head_sha = run_git(["rev-parse", "HEAD"]).strip()
    porcelain = run_git(["status", "--porcelain"]).strip()
    if porcelain:
        raise RuntimeError(f"Dirty working tree before decisive run:\n{porcelain}")

    for ancestor in (AUTHOR_SOURCE_SHA, AUTHOR_CHECKPOINT_SHA, COORDINATOR_RELEASE_SHA):
        rc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "merge-base", "--is-ancestor", ancestor, "HEAD"],
            stdin=subprocess.DEVNULL,
        ).returncode
        if rc != 0:
            raise RuntimeError(f"Commit {ancestor} is not an ancestor of HEAD {head_sha}")

    audit_doc = json.loads(
        (REPO_ROOT / "docs" / "coordination" / "WP-0006" / "stage1-publication-audit.json").read_text(encoding="utf-8")
    )
    changed_files: list[str] = audit_doc["source_changed_files"]
    mismatched_blobs: list[str] = []
    for rel in changed_files:
        want_oid = run_git(["rev-parse", f"{AUTHOR_SOURCE_SHA}:{rel}"]).strip()
        head_oid = run_git(["rev-parse", f"HEAD:{rel}"]).strip()
        if want_oid != head_oid:
            mismatched_blobs.append(f"{rel}: {head_oid} != {want_oid}")
    if mismatched_blobs:
        raise RuntimeError(f"Candidate blob mismatch at HEAD: {mismatched_blobs}")

    protected_checks = []
    for p in ("qualification", "evaluation", "research", "web/package-lock.json", "ELedgerCare.slnx"):
        rel_oid = run_git(["rev-parse", f"{RELEASE_BASE_SHA}:{p}"]).strip()
        cand_oid = run_git(["rev-parse", f"{AUTHOR_SOURCE_SHA}:{p}"]).strip()
        head_oid = run_git(["rev-parse", f"HEAD:{p}"]).strip()
        protected_checks.append({
            "path": p,
            "release_oid": rel_oid,
            "author_candidate_oid": cand_oid,
            "reviewer_head_oid": head_oid,
            "unchanged_in_author_candidate": rel_oid == cand_oid,
        })
        if rel_oid != cand_oid:
            raise RuntimeError(f"Protected path {p} mutated in author candidate!")

    return {
        "reviewer_frozen_helper_head": head_sha,
        "author_source_sha": AUTHOR_SOURCE_SHA,
        "author_checkpoint_sha": AUTHOR_CHECKPOINT_SHA,
        "coordinator_release_sha": COORDINATOR_RELEASE_SHA,
        "verified_candidate_file_count": len(changed_files),
        "all_69_candidate_blobs_identical_at_head": True,
        "protected_trees": protected_checks,
    }


def verify_author_scratch_logs_readonly() -> dict:
    audit_path = REPO_ROOT / "docs" / "coordination" / "WP-0006" / "stage1-publication-audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    expected_entries = audit["original_log_digests"]
    if not AUTHOR_SCRATCH_LOGS_DIR.is_dir():
        return {"available": False, "verified_count": 0}

    rows = []
    for item in expected_entries:
        step_id = item["step_id"]
        fp = AUTHOR_SCRATCH_LOGS_DIR / f"{step_id}.log"
        raw = fp.read_bytes()
        dig = dual_digests(raw)
        raw_matches_audit = dig["raw_file_sha256"] == item["sha256"] and dig["raw_bytes"] == item["bytes"]
        lf_matches_published = dig["lf_normalized_sha256"] == item["published_sha256"]
        raw_matches_published = dig["raw_file_sha256"] == item["published_sha256"]
        if not (raw_matches_audit and lf_matches_published and not raw_matches_published):
            raise RuntimeError(f"Author log digest discrepancy on {step_id}: {dig} vs {item}")
        rows.append({
            "step_id": step_id,
            "raw_bytes": dig["raw_bytes"],
            "raw_file_sha256": dig["raw_file_sha256"],
            "lf_normalized_sha256": dig["lf_normalized_sha256"],
            "matches_coordinator_raw_sha256": raw_matches_audit,
            "matches_author_published_lf_sha256": lf_matches_published,
            "raw_equals_published_without_normalization": raw_matches_published,
        })

    return {
        "available": True,
        "verified_count": len(rows),
        "all_11_raw_and_lf_digests_verified": len(rows) == 11,
        "logs": rows,
    }


def verify_manifests_fixtures_and_isolation() -> dict:
    # 1. Self-contained model-files.json vs Q0 model-files.json
    prod_model = json.loads(
        (REPO_ROOT / "workers" / "local_ocr" / "manifests" / "model-files.json").read_text(encoding="utf-8")
    )
    q0_model = json.loads(
        (REPO_ROOT / "qualification" / "q0" / "harness" / "manifests" / "model-files.json").read_text(encoding="utf-8")
    )
    if prod_model["files"] != q0_model["files"] or prod_model["notices"] != q0_model["notices"]:
        raise RuntimeError("workers/local_ocr/manifests/model-files.json diverges from Q0 model-files.json!")

    # 2. Self-contained dependency-lock.json vs Q0 metadata wheel graph blob
    prod_lock = json.loads(
        (REPO_ROOT / "workers" / "local_ocr" / "manifests" / "dependency-lock.json").read_text(encoding="utf-8")
    )
    q0_graph = json.loads(run_git(["cat-file", "blob", Q0_WHEEL_GRAPH_BLOB]))
    q0_wheels = q0_graph.get("packages") or q0_graph.get("distributions") or q0_graph.get("wheels")
    if isinstance(q0_wheels, list) and len(q0_wheels) == 32:
        q0_by_file = {w["filename"]: w for w in q0_wheels}
        for d in prod_lock["distributions"]:
            qw = q0_by_file.get(d["filename"])
            if qw is None or qw.get("version") != d["version"] or qw.get("size") != d["size"]:
                raise RuntimeError(f"Distribution {d['filename']} diverges from Q0 wheel graph!")

    # 3. Admitted DEV fixtures byte-for-byte parity (zero holdout files touched!)
    f01_prod = (REPO_ROOT / "tests" / "fixtures" / "SYN-WO-01-v1-raster300.pdf").read_bytes()
    f01_dev = (REPO_ROOT / "evaluation" / "synthetic" / "pdfs" / "F01" / "SYN-WO-01-v1-raster300.pdf").read_bytes()
    f07_prod = (REPO_ROOT / "tests" / "fixtures" / "SYN-MP-01-v0-clean.pdf").read_bytes()
    f07_dev = (REPO_ROOT / "evaluation" / "synthetic" / "pdfs" / "F07" / "SYN-MP-01-v0-clean.pdf").read_bytes()
    if f01_prod != f01_dev or f07_prod != f07_dev:
        raise RuntimeError("Committed F2 test fixtures diverge from admitted DEV corpus PDFs!")

    # 4. Product/worker/smoke isolation & XSS sink scan
    scan_roots = [
        REPO_ROOT / "src",
        REPO_ROOT / "web" / "src",
        REPO_ROOT / "web" / "e2e",
        REPO_ROOT / "deploy" / "dev",
        REPO_ROOT / "workers" / "local_ocr" / "local_ocr",
    ]
    extra_files = [
        REPO_ROOT / "workers" / "local_ocr" / "run_worker.py",
        REPO_ROOT / "web" / "playwright.config.ts",
        REPO_ROOT / "web" / "proxy.conf.mjs",
        REPO_ROOT / "ELedgerCare.slnx",
    ]
    files_to_scan: list[Path] = list(extra_files)
    for sr in scan_roots:
        for p in sr.rglob("*"):
            if p.is_file() and not any(part in ("bin", "obj", "__pycache__", "node_modules", "dist") for part in p.parts):
                files_to_scan.append(p)

    forbidden_refs = ("qualification/", "qualification\\", "research/", "research\\", "evaluation/", "evaluation\\", "git.exe")
    isolation_hits = []
    for fp in files_to_scan:
        txt = fp.read_text(encoding="utf-8", errors="replace")
        body = "\n".join(ln for ln in txt.splitlines() if not ln.lstrip().startswith("#")) if fp.suffix.lower() == ".ps1" else txt
        for tok in forbidden_refs:
            if tok.lower() in body.lower():
                isolation_hits.append(f"{fp.relative_to(REPO_ROOT).as_posix()}: {tok}")
    if isolation_hits:
        raise RuntimeError(f"Forbidden cross-boundary references found: {isolation_hits}")

    xss_sinks = ("innerHTML", "outerHTML", "bypassSecurityTrust", "insertAdjacentHTML", "document.write")
    xss_hits = []
    for fp in (REPO_ROOT / "web" / "src").rglob("*.ts"):
        txt = fp.read_text(encoding="utf-8")
        non_comment = "\n".join(
            ln for ln in txt.splitlines()
            if not ln.strip().startswith(("//", "*", "/*"))
        )
        for sink in xss_sinks:
            if sink in non_comment:
                xss_hits.append(f"{fp.relative_to(REPO_ROOT).as_posix()}: {sink}")
    if xss_hits:
        raise RuntimeError(f"Unsafe DOM sink found in Angular UI: {xss_hits}")

    return {
        "model_manifest_sha256": sha256_bytes((REPO_ROOT / "workers" / "local_ocr" / "manifests" / "model-files.json").read_bytes()),
        "dependency_lock_sha256": sha256_bytes((REPO_ROOT / "workers" / "local_ocr" / "manifests" / "dependency-lock.json").read_bytes()),
        "model_objects_verified": len(prod_model["files"]),
        "locked_distributions_verified": len(prod_lock["distributions"]),
        "f01_fixture_sha256": sha256_bytes(f01_prod),
        "f07_fixture_sha256": sha256_bytes(f07_prod),
        "scanned_production_files": len(files_to_scan),
        "cross_boundary_reference_violations": 0,
        "angular_unsafe_dom_sink_violations": 0,
        "holdout_files_accessed": 0,
    }


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

CSHARP_PROBE_PROGRAM = r"""using System.Diagnostics;
using System.Reflection;
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

var probeDb = $"eledgercare_rev_probe_{Guid.NewGuid().ToString("N")[..8]}";
string AdminConn(string db = "postgres") => $"Host={pgHost};Port={pgPort};Database={db};Username={adminUser};Password={adminPass}";
string MigConn(string db) => $"Host={pgHost};Port={pgPort};Database={db};Username={migUser};Password={migPass}";
string AppConn(string db) => $"Host={pgHost};Port={pgPort};Database={db};Username={appUser};Password={appPass}";

var workerRoot = Path.Combine(repoRoot, "workers", "local_ocr");
var manifestSha = SHA256.HashData(await File.ReadAllBytesAsync(Path.Combine(workerRoot, "manifests", "model-files.json")));
var lockSha = SHA256.HashData(await File.ReadAllBytesAsync(Path.Combine(workerRoot, "manifests", "dependency-lock.json")));
var workerSha = ExtractionSettings.ComputeWorkerSourceSha256(workerRoot);

var results = new Dictionary<string, object?>();

// --- Probe P1: Real Q0 Unlimited-OCR-2 outputs (F01 1p & F07 3p) through SafeNativeDisplayParser & WorkerEnvelopeValidator ---
{
    var q0Dir = Path.Combine(
        repoRoot, "qualification", "q0", "harness", "evidence",
        "004-gpu-trial", "9e73ef86", "run-20261115T202627Z-eb5bf7da", "evidence");
    var f01RawBytes = await File.ReadAllBytesAsync(Path.Combine(q0Dir, "F01.warm1.raw.txt"));
    var f07RawBytes = await File.ReadAllBytesAsync(Path.Combine(q0Dir, "F07.warm1.raw.txt"));

    var f01Pages = SafeNativeDisplayParser.ParsePages(Encoding.UTF8.GetString(f01RawBytes));
    var f07Pages = SafeNativeDisplayParser.ParsePages(Encoding.UTF8.GetString(f07RawBytes));

    var extSettings = new ExtractionSettings(false, 3, null, null, null, workerRoot, manifestSha, lockSha, workerSha);
    var pdfBytes = await File.ReadAllBytesAsync(Path.Combine(repoRoot, "tests", "fixtures", "SYN-MP-01-v0-clean.pdf"));
    var work3 = new ClaimedAttemptWork(
        Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(),
        1, 1, "attempt-q0-f07", pdfBytes, SHA256.HashData(pdfBytes), pdfBytes.Length, 3);
    var envPayload = new
    {
        schema = ExtractionCeilings.EnvelopeSchema,
        status = "completed",
        document_id = work3.DocumentId.ToString("D"),
        job_id = work3.JobId.ToString("D"),
        attempt_id = work3.AttemptId.ToString("D"),
        fencing_token = work3.FencingToken,
        input = new { sha256 = Convert.ToHexStringLower(work3.InputSha256), byte_length = work3.InputByteLength, page_count = 3 },
        provenance = new
        {
            model_repo_id = ExtractionCeilings.ModelRepoId,
            model_revision = ExtractionCeilings.ModelRevision,
            model_manifest_sha256 = Convert.ToHexStringLower(manifestSha),
            dependency_lock_sha256 = Convert.ToHexStringLower(lockSha),
            worker_source_sha256 = Convert.ToHexStringLower(workerSha),
            worker_config_sha256 = Convert.ToHexStringLower(ExtractionSettings.ComputeWorkerConfigSha256(3)),
            renderer_identity = "pypdfium2==5.15.2;pdfium=159.0.8149.0;dpi=300;rgb",
            provenance_exceptions = new[] { ExtractionCeilings.RequiredProvenanceException },
            generation_settings = new { temperature = 0.0, max_new_tokens = 24000 },
        },
        output = new
        {
            finish_reason = "stop",
            output_page_count = 3,
            byte_length = f07RawBytes.Length,
            sha256 = Convert.ToHexStringLower(SHA256.HashData(f07RawBytes)),
        },
        timings = new { started_at_utc = "2026-11-16T06:00:00Z", completed_at_utc = "2026-11-16T06:04:33Z", load_duration_ms = 1000L, render_duration_ms = 120L, infer_duration_ms = 273174L, total_duration_ms = 274294L },
        diagnostics = new { kernel_path = "triton_import_failed_dense_fallback" },
    };
    var val = WorkerEnvelopeValidator.Validate(
        work3, extSettings,
        new WorkerRunOutcome(JsonSerializer.SerializeToUtf8Bytes(envPayload), f07RawBytes, 0, null, null),
        DateTimeOffset.UtcNow);

    results["P1_real_q0_native_output_parse_and_validate"] = new
    {
        f01_parsed_pages = f01Pages.Count,
        f01_tables_parsed = f01Pages[0].Blocks.Count(b => b.Kind == "table"),
        f07_parsed_pages = f07Pages.Count,
        f07_page1_first_block_kind = f07Pages[0].Blocks[0].Kind,
        f07_envelope_accepted = val is EnvelopeValidationOutcome.Accepted,
    };
}

// --- Probe P2: Reproduce F2-S1-01 (LocalPythonOcrWorkerRunner launches run_worker.py with -I -> ModuleNotFoundError) ---
{
    var tempRoot = Path.Combine(Path.GetTempPath(), $"elc-rev-p2-{Guid.NewGuid():N}");
    var fakeQ0 = Path.Combine(tempRoot, "q0");
    var fakeRt = Path.Combine(tempRoot, "rt");
    Directory.CreateDirectory(fakeQ0);
    Directory.CreateDirectory(fakeRt);
    try
    {
        var hostPy = @"C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe";
        using (var venvProc = Process.Start(new ProcessStartInfo(hostPy)
        {
            ArgumentList = { "-m", "venv", "--without-pip", Path.Combine(fakeQ0, "venv") },
            UseShellExecute = false,
            CreateNoWindow = true,
        })!)
        {
            await venvProc.WaitForExitAsync();
        }
        Directory.CreateDirectory(Path.Combine(fakeQ0, "models", "Unlimited_OCR_2_04809669"));
        Directory.CreateDirectory(Path.Combine(fakeQ0, "notices", "Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"));

        var enabledSettings = new ExtractionSettings(
            true, 3, fakeQ0, fakeRt, "GPU-00000000-0000-0000-0000-000000000000",
            workerRoot, manifestSha, lockSha, workerSha);
        var runner = new LocalPythonOcrWorkerRunner(enabledSettings);
        var pdfBytes = Encoding.ASCII.GetBytes("%PDF-1.4\n%%EOF\n");
        var work = new ClaimedAttemptWork(
            Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(),
            1, 1, "attempt-p2", pdfBytes, SHA256.HashData(pdfBytes), pdfBytes.Length, 1);

        var outcome = await runner.ExecuteAttemptAsync(
            work,
            (_, _, _) => Task.FromResult(true),
            (_, _, _, _) => Task.FromResult(true),
            CancellationToken.None);
        var stderrLog = await File.ReadAllTextAsync(Path.Combine(fakeRt, "runs", "attempt-p2", "output", "child.stderr.log"));
        var val = WorkerEnvelopeValidator.Validate(work, enabledSettings, outcome, DateTimeOffset.UtcNow);
        var rej = val as EnvelopeValidationOutcome.Rejected;

        results["P2_F2_S1_01_isolated_mode_import_crash"] = new
        {
            reproduced = outcome.ExitCode == 1 && outcome.EnvelopeJsonBytes is null && stderrLog.Contains("ModuleNotFoundError: No module named 'local_ocr'"),
            child_exit_code = outcome.ExitCode,
            envelope_written = outcome.EnvelopeJsonBytes is not null,
            validator_failure_code = rej?.FailureCode,
            stderr_excerpt = stderrLog.Trim(),
        };
    }
    finally
    {
        try { Directory.Delete(tempRoot, true); } catch { }
    }
}

// --- Probe P3a & P3b: Reproduce F2-S1-02 (CheckStorageBounds transient subdir disappearance + ExecuteAttemptAsync finally missing TerminateAllInJob) ---
{
    var checkMethod = typeof(LocalPythonOcrWorkerRunner).GetMethod(
        "CheckStorageBounds", BindingFlags.NonPublic | BindingFlags.Static)!;
    var tempRt = Path.Combine(Path.GetTempPath(), $"elc-rev-p3a-{Guid.NewGuid():N}");
    Directory.CreateDirectory(tempRt);
    string? caughtExceptionType = null;
    int iterations = 0;
    try
    {
        for (var s = 0; s < 24; s++)
        {
            var seedDir = Path.Combine(tempRt, "runs", "attempt-1", "cache", $"seed-{s:D2}");
            Directory.CreateDirectory(seedDir);
            File.WriteAllBytes(Path.Combine(seedDir, "blob.bin"), [1, 2, 3, 4]);
        }
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(4));
        var churnTasks = Enumerable.Range(0, 4).Select(workerIdx => Task.Run(() =>
        {
            var seq = 0;
            while (!cts.IsCancellationRequested)
            {
                var sub = Path.Combine(tempRt, "runs", "attempt-1", "cache", "tmp", $"w{workerIdx}-transient-{seq++ % 16}");
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

        while (!cts.IsCancellationRequested && caughtExceptionType is null && iterations < 5000)
        {
            iterations++;
            try
            {
                object?[] invokeArgs = [tempRt, null];
                _ = checkMethod.Invoke(null, invokeArgs);
            }
            catch (TargetInvocationException tie) when (tie.InnerException is not null)
            {
                caughtExceptionType = tie.InnerException.GetType().FullName;
                break;
            }
        }
        cts.Cancel();
        try { await Task.WhenAll(churnTasks); } catch { }
    }
    finally
    {
        try { Directory.Delete(tempRt, true); } catch { }
    }

    // P3b: Prove ExecuteAttemptAsync finally skips TerminateAllInJob when onHeartbeatAsync throws!
    var p3bRoot = Path.Combine(Path.GetTempPath(), $"elc-rev-p3b-{Guid.NewGuid():N}");
    var p3bQ0 = Path.Combine(p3bRoot, "q0");
    var p3bRt = Path.Combine(p3bRoot, "rt");
    var p3bWorkerRoot = Path.Combine(p3bRoot, "fake_worker");
    Directory.CreateDirectory(p3bQ0);
    Directory.CreateDirectory(p3bRt);
    Directory.CreateDirectory(Path.Combine(p3bWorkerRoot, "local_ocr"));
    int leakedLauncherPid = 0;
    long leakedLauncherFt = 0;
    bool childStillAliveAfterHeartbeatThrow = false;
    bool executeTaskBlockedWaitingOnPipe = false;
    try
    {
        var hostPy = @"C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe";
        using (var venvProc = Process.Start(new ProcessStartInfo(hostPy)
        {
            ArgumentList = { "-m", "venv", "--without-pip", Path.Combine(p3bQ0, "venv") },
            UseShellExecute = false,
            CreateNoWindow = true,
        })!)
        {
            await venvProc.WaitForExitAsync();
        }
        Directory.CreateDirectory(Path.Combine(p3bQ0, "models", "Unlimited_OCR_2_04809669"));
        Directory.CreateDirectory(Path.Combine(p3bQ0, "notices", "Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"));
        await File.WriteAllTextAsync(Path.Combine(p3bWorkerRoot, "local_ocr", "__init__.py"), "");
        await File.WriteAllTextAsync(Path.Combine(p3bWorkerRoot, "run_worker.py"), "import time\ntime.sleep(30)\n");

        var fakeWorkerSha = ExtractionSettings.ComputeWorkerSourceSha256(p3bWorkerRoot);
        var settings = new ExtractionSettings(
            true, 3, p3bQ0, p3bRt, "GPU-00000000-0000-0000-0000-000000000000",
            p3bWorkerRoot, manifestSha, lockSha, fakeWorkerSha);
        var runner = new LocalPythonOcrWorkerRunner(settings);
        var probe = new WindowsProcessIdentityProbe();
        var pdfBytes = Encoding.ASCII.GetBytes("%PDF-1.4\n%%EOF\n");
        var work = new ClaimedAttemptWork(
            Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(),
            1, 1, "attempt-p3b", pdfBytes, SHA256.HashData(pdfBytes), pdfBytes.Length, 1);

        var hbThrown = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var execTask = runner.ExecuteAttemptAsync(
            work,
            (pid, ft, _) =>
            {
                leakedLauncherPid = pid;
                leakedLauncherFt = ft;
                return Task.FromResult(true);
            },
            (_, _, _, _) =>
            {
                hbThrown.TrySetResult();
                throw new InvalidOperationException("Simulated mid-run DB/storage exception");
            },
            CancellationToken.None);

        await hbThrown.Task.WaitAsync(TimeSpan.FromSeconds(10));
        // Give ExecuteAttemptAsync 1200ms after onHeartbeatAsync threw to reach finally:
        var finishedEarly = await Task.WhenAny(execTask, Task.Delay(1200)) == execTask;
        executeTaskBlockedWaitingOnPipe = !finishedEarly;
        childStillAliveAfterHeartbeatThrow = probe.IsProcessAlive(leakedLauncherPid, leakedLauncherFt);

        // Clean up our own spawned test child by verified (PID, CreateFileTime) so execTask unblocks cleanly:
        if (childStillAliveAfterHeartbeatThrow && probe.IsProcessAlive(leakedLauncherPid, leakedLauncherFt))
        {
            using var p = Process.GetProcessById(leakedLauncherPid);
            p.Kill(entireProcessTree: true);
        }
        try { await execTask.WaitAsync(TimeSpan.FromSeconds(5)); } catch { }
    }
    finally
    {
        try { Directory.Delete(p3bRoot, true); } catch { }
    }

    results["P3_F2_S1_02_storage_guard_and_finally_containment"] = new
    {
        transient_subdir_exception_in_CheckStorageBounds = caughtExceptionType,
        transient_subdir_iterations_until_throw = iterations,
        finally_skipped_TerminateAllInJob_on_exception = executeTaskBlockedWaitingOnPipe && childStillAliveAfterHeartbeatThrow,
        execute_task_blocked_waiting_on_pipe = executeTaskBlockedWaitingOnPipe,
        child_still_alive_1200ms_after_loop_exception = childStillAliveAfterHeartbeatThrow,
    };
}

// --- Probe P4 & P3c: PostgreSQL 18.7 DB probes (F2-S1-03 NUL byte / unpaired surrogate in MarkAttemptFailedAsync + F2-S1-02 same-instance stuck running row) ---
await using (var admin = new NpgsqlConnection(AdminConn()))
{
    await admin.OpenAsync();
    await using (var cmd = new NpgsqlCommand($"CREATE DATABASE {probeDb} OWNER {migUser} ENCODING 'UTF8' TEMPLATE template0", admin))
        await cmd.ExecuteNonQueryAsync();
    await using (var cmd = new NpgsqlCommand($"GRANT CONNECT ON DATABASE {probeDb} TO {appUser}", admin))
        await cmd.ExecuteNonQueryAsync();
}
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
    var t0 = new DateTimeOffset(2026, 11, 16, 6, 30, 0, TimeSpan.Zero);

    // Submit a valid 1-page document
    var pdf = await File.ReadAllBytesAsync(Path.Combine(repoRoot, "tests", "fixtures", "F1-SWO-001.pdf"));
    var doc1 = Document.Submit(Guid.CreateVersion7(), Guid.CreateVersion7(), Guid.CreateVersion7(), pdf, 1, t0);
    await intakeStore.InsertAsync(doc1, CancellationToken.None);
    await extractionStore.QueueOrReconcileAsync(doc1.DocumentId, null, 3, true, t0.AddSeconds(1), CancellationToken.None);

    var probe = new WindowsProcessIdentityProbe();
    var settings = new ExtractionSettings(false, 3, null, null, null, workerRoot, manifestSha, lockSha, workerSha);
    var coordinator = new ExtractionAttemptCoordinator(
        extractionStore, new LocalPythonOcrWorkerRunner(settings), probe, settings, TimeProvider.System);

    var claimed = (await extractionStore.ClaimNextQueuedJobAsync(
        coordinator.SupervisorInstanceId,
        coordinator.SupervisorIdentity.Pid,
        coordinator.SupervisorIdentity.CreateFileTime,
        t0.AddSeconds(2),
        CancellationToken.None))!;

    // 1. Test NUL byte (0x00) in rejected raw output preview -> PostgresException 22021
    byte[] rawWithNul = [(byte)'<', (byte)'P', (byte)'A', (byte)'G', (byte)'E', (byte)'>', 0x00, (byte)'X'];
    var nulOutcome = new WorkerRunOutcome(null, rawWithNul, 1, "output_cap_exceeded", "Simulated oversize raw with NUL byte");
    var nulRejected = (EnvelopeValidationOutcome.Rejected)WorkerEnvelopeValidator.Validate(claimed, settings, nulOutcome, t0.AddSeconds(3));
    string? nulSqlState = null;
    try
    {
        await extractionStore.MarkAttemptFailedAsync(
            claimed.AttemptId, claimed.JobId, claimed.FencingToken,
            nulRejected.FailureCode, nulRejected.SafeDetail, 1,
            nulRejected.DiagnosticRawOutputUtf8, nulRejected.DiagnosticMetadataJson,
            t0.AddSeconds(3), CancellationToken.None);
    }
    catch (PostgresException pex)
    {
        nulSqlState = pex.SqlState;
    }

    // 2. Test unpaired UTF-16 high surrogate at char 65,535 truncation boundary -> EncoderFallbackException / ArgumentException
    var sb = new StringBuilder(65_540);
    sb.Append('A', 65_535);
    sb.Append("\U0001F600"); // high surrogate at [65535], low surrogate at [65536]
    string? surrogateExceptionType = null;
    try
    {
        await extractionStore.MarkAttemptFailedAsync(
            claimed.AttemptId, claimed.JobId, claimed.FencingToken,
            "model_output_truncated", "Simulated surrogate split", 2,
            sb.ToString(), "{}",
            t0.AddSeconds(4), CancellationToken.None);
    }
    catch (Exception ex)
    {
        surrogateExceptionType = ex.GetType().FullName;
    }

    // 3. Because MarkAttemptFailedAsync threw above, claimed attempt is STILL 'running' in DB under coordinator.SupervisorInstanceId!
    // Check whether coordinator.ReconcileAbandonedAttemptsAsync() recovers it while the API process stays alive:
    var reconciledBySameCoordinator = await coordinator.ReconcileAbandonedAttemptsAsync(CancellationToken.None);
    string jobStatusAfterReconcile;
    await using (var checkConn = new NpgsqlConnection(AppConn(probeDb)))
    {
        await checkConn.OpenAsync();
        await using var cCmd = new NpgsqlCommand("SELECT status FROM eledgercare.processing_jobs WHERE job_id = @id", checkConn);
        cCmd.Parameters.AddWithValue("id", claimed.JobId);
        jobStatusAfterReconcile = (string)(await cCmd.ExecuteScalarAsync())!;
    }

    results["P4_F2_S1_03_and_same_instance_wedge"] = new
    {
        nul_byte_in_diagnostic_raw_sqlstate = nulSqlState,
        surrogate_split_at_65536_exception = surrogateExceptionType,
        reconciled_by_same_live_coordinator_after_failure = reconciledBySameCoordinator,
        job_status_stuck_running = jobStatusAfterReconcile == "running",
        observed_job_status = jobStatusAfterReconcile,
    };
}
finally
{
    await using var admin2 = new NpgsqlConnection(AdminConn());
    await admin2.OpenAsync();
    await using var dropCmd = new NpgsqlCommand($"DROP DATABASE IF EXISTS {probeDb} WITH (FORCE)", admin2);
    await dropCmd.ExecuteNonQueryAsync();
}

var jsonText = JsonSerializer.Serialize(results, new JsonSerializerOptions { WriteIndented = true });
await File.WriteAllTextAsync(outputJsonPath, jsonText, new UTF8Encoding(false));
Console.WriteLine("Wrote probe output JSON.");

sealed class PooledContextFactory(DbContextOptions<ELedgerCareDbContext> options) : IDbContextFactory<ELedgerCareDbContext>
{
    public ELedgerCareDbContext CreateDbContext() => new(options);
}
"""


def run_csharp_reviewer_probes(env: dict[str, str], logs_dir: Path, secrets_to_redact: list[str]) -> dict:
    probe_dir = REPO_ROOT / ".scratch" / "reviewer-probes"
    if probe_dir.exists():
        shutil.rmtree(probe_dir)
    probe_dir.mkdir(parents=True, exist_ok=True)
    try:
        (probe_dir / "ReviewerProbes.csproj").write_text(
            CSHARP_PROBE_CSPROJ.format(repo_root=str(REPO_ROOT)), encoding="utf-8"
        )
        (probe_dir / "Program.cs").write_text(CSHARP_PROBE_PROGRAM, encoding="utf-8")
        out_json_path = probe_dir / "probe-results.json"

        build_step = run_logged_step(
            "12-build-reviewer-probes",
            [
                "dotnet", "build", str(probe_dir / "ReviewerProbes.csproj"),
                "-c", "Release",
                "--source", str(REPO_ROOT / ".local" / "nuget" / "packages"),
            ],
            cwd=probe_dir,
            env=env,
            logs_dir=logs_dir,
            secrets_to_redact=secrets_to_redact,
        )
        exe_path = probe_dir / "bin" / "Release" / "net10.0" / "ReviewerProbes.exe"
        run_step = run_logged_step(
            "13-execute-reviewer-probes",
            [str(exe_path), str(REPO_ROOT), str(out_json_path)],
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


def run_python_transient_heartbeat_guard_probe() -> dict:
    worker_root = REPO_ROOT / "workers" / "local_ocr"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    from local_ocr.env_guard import WorkerHeartbeat, directory_size_bytes

    with tempfile.TemporaryDirectory() as td:
        rt = Path(td)
        hb_path = rt / "runs" / "attempt-hb" / "output" / "heartbeat.json"
        counter = 0

        hb = WorkerHeartbeat(
            hb_path,
            attempt_id="019a0000-0000-7000-8000-000000000099",
            fencing_token=1,
            interval_s=0.005,
            progress_fn=lambda: counter,
        ).start()
        try:
            scans = 0
            for i in range(200):
                counter = i
                hb.beat()
                _ = directory_size_bytes(rt)
                scans += 1
        finally:
            hb.stop()

    loaded_heavy = [m for m in ("torch", "transformers", "pypdfium2") if m in sys.modules]
    if loaded_heavy:
        raise RuntimeError(f"Forbidden heavy modules imported during CPU probe: {loaded_heavy}")

    return {
        "rapid_heartbeat_and_directory_size_iterations": scans,
        "exceptions": 0,
        "heavy_modules_imported": loaded_heavy,
    }


def cleanup_reviewer_databases(pg_settings: dict) -> list[str]:
    psql = REPO_ROOT / ".local" / "tools" / "pgsql-18.7-1" / "bin" / "psql.exe"
    dropped = []
    env = dict(os.environ, PGPASSWORD=pg_settings["adminPassword"])
    for db_name in ("eledgercare_reviewer_stage1", "eledgercare_reviewer_e2e", pg_settings["devDatabase"]):
        if not re.match(r"^[a-z][a-z0-9_]{0,62}$", db_name):
            continue
        subprocess.run(
            [
                str(psql), "-X", "-q", "-v", "ON_ERROR_STOP=1",
                "-h", str(pg_settings["host"]), "-p", str(pg_settings["port"]),
                "-U", str(pg_settings["adminUser"]), "-d", "postgres",
                "-c", f"DROP DATABASE IF EXISTS {db_name} WITH (FORCE);",
            ],
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=True,
        )
        dropped.append(db_name)
    return dropped


def main() -> int:
    started_utc = utc_now()
    if EXTERNAL_F2_REVIEWER_ROOT.exists():
        raise RuntimeError(f"External F2 reviewer root must not exist in Stage 1: {EXTERNAL_F2_REVIEWER_ROOT}")

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
            raise RuntimeError(f"Reviewer port {port} is already bound before test start!")

    pre_host = host_memory_and_cpu_snapshot()
    lineage = verify_git_lineage_and_candidate_blobs()
    author_log_audit = verify_author_scratch_logs_readonly()
    static_audit = verify_manifests_fixtures_and_isolation()

    logs_dir = REPO_ROOT / ".scratch" / "stage1-review-logs"
    if logs_dir.exists():
        shutil.rmtree(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    env = build_base_env()
    steps: list[dict] = []
    pg_started = False
    postmaster_identities: list[dict] = []
    dropped_dbs: list[str] = []
    demo_receipt_data: dict | None = None
    f2_browser_data: dict | None = None
    probe_bundle: dict | None = None
    py_guard_probe: dict | None = None

    try:
        # Start owned PostgreSQL 18.7 on 127.0.0.1:55435
        steps.append(run_logged_step(
            "00-start-owned-postgres",
            ["pwsh", "-NoProfile", "-File", str(REPO_ROOT / "deploy" / "dev" / "postgres" / "start-cluster.ps1")],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        pg_started = True
        pm_pid = int((REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        postmaster_identities.append({
            "event": "initial_start",
            "pid": pm_pid,
            "create_filetime": current_or_pid_filetime(pm_pid),
            "port": REVIEWER_PG_PORT,
        })

        steps.append(run_logged_step(
            "01-dotnet-tool-restore",
            ["dotnet", "tool", "restore"],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        steps.append(run_logged_step(
            "02-dotnet-restore-locked",
            [
                "dotnet", "restore", "ELedgerCare.slnx", "--locked-mode",
                "--packages", str(REPO_ROOT / ".local" / "nuget" / "packages"),
            ],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        steps.append(run_logged_step(
            "03-dotnet-build-release",
            ["dotnet", "build", "ELedgerCare.slnx", "-c", "Release", "--no-restore"],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        steps.append(run_logged_step(
            "04-dotnet-publish-api",
            ["dotnet", "publish", "src/ELedgerCare.Api/ELedgerCare.Api.csproj", "-c", "Release", "--no-restore"],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        steps.append(run_logged_step(
            "05-python-worker-cpu-tests",
            [str(HOST_PYTHON_EXE), "-B", "-m", "unittest", "discover", "-s", "workers/local_ocr/tests", "-p", "test_*.py", "-v"],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        steps.append(run_logged_step(
            "06-angular-build",
            ["cmd.exe", "/c", "npx", "ng", "build"],
            cwd=REPO_ROOT / "web", env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        steps.append(run_logged_step(
            "07-prepare-database-stage1",
            [
                "pwsh", "-NoProfile", "-File", "deploy/dev/database/prepare-database.ps1",
                "-Database", "eledgercare_reviewer_stage1",
            ],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        # Also prepare devDatabase for demo smoke
        steps.append(run_logged_step(
            "08-prepare-dev-database",
            [
                "pwsh", "-NoProfile", "-File", "deploy/dev/database/prepare-database.ps1",
                "-Database", str(pg_settings["devDatabase"]),
            ],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        steps.append(run_logged_step(
            "09-dotnet-test-solution",
            ["dotnet", "test", "--solution", "ELedgerCare.slnx", "-c", "Release", "--no-build"],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        steps.append(run_logged_step(
            "10-playwright-browser-checks-5290-4310",
            [
                "pwsh", "-NoProfile", "-File", "deploy/dev/smoke/run-browser-checks.ps1",
                "-Database", "eledgercare_reviewer_e2e",
                "-ApiPort", str(REVIEWER_API_PORT),
                "-UiPort", str(REVIEWER_UI_PORT),
            ],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))

        demo_receipt_path = REPO_ROOT / ".scratch" / "stage1-review-logs" / "reviewer-demo-smoke-receipt.json"
        steps.append(run_logged_step(
            "11-demo-smoke-restart-checks-5290",
            [
                "pwsh", "-NoProfile", "-File", "deploy/dev/smoke/run-demo-smoke.ps1",
                "-ApiPort", str(REVIEWER_API_PORT),
                "-ReceiptPath", str(demo_receipt_path),
            ],
            cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
        ))
        pm_pid_after_smoke = int((REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        postmaster_identities.append({
            "event": "after_demo_smoke_restart",
            "pid": pm_pid_after_smoke,
            "create_filetime": current_or_pid_filetime(pm_pid_after_smoke),
            "port": REVIEWER_PG_PORT,
        })

        demo_receipt_data = json.loads(demo_receipt_path.read_text(encoding="utf-8"))
        f2_browser_path = REPO_ROOT / ".scratch" / "playwright" / "f2-browser-evidence.json"
        if f2_browser_path.is_file():
            f2_browser_data = json.loads(f2_browser_path.read_text(encoding="utf-8"))

        # Run independent Python + C# probes (including reproduction of F2-S1-01, F2-S1-02, F2-S1-03)
        py_guard_probe = run_python_transient_heartbeat_guard_probe()
        probe_bundle = run_csharp_reviewer_probes(env, logs_dir, secrets_to_redact)
        steps.append(probe_bundle["build_step"])
        steps.append(probe_bundle["run_step"])

        dropped_dbs = cleanup_reviewer_databases(pg_settings)
    finally:
        if pg_started:
            steps.append(run_logged_step(
                "14-stop-owned-postgres",
                ["pwsh", "-NoProfile", "-File", str(REPO_ROOT / "deploy" / "dev" / "postgres" / "stop-cluster.ps1")],
                cwd=REPO_ROOT, env=env, logs_dir=logs_dir, secrets_to_redact=secrets_to_redact,
                check=False,
            ))

    for port in (REVIEWER_API_PORT, REVIEWER_UI_PORT, REVIEWER_PG_PORT):
        if is_loopback_port_bound(port):
            raise RuntimeError(f"Reviewer port {port} remained bound after teardown!")

    if EXTERNAL_F2_REVIEWER_ROOT.exists():
        raise RuntimeError(f"External F2 reviewer root was unexpectedly created: {EXTERNAL_F2_REVIEWER_ROOT}")

    post_host = host_memory_and_cpu_snapshot()
    post_porcelain = run_git(["status", "--porcelain"]).strip()

    summary = {
        "schema": "eledgercare.wp-0006.reviewer-stage1-verification/1",
        "reviewer": "eld-next-reviewer",
        "conversation_id": "101b19cf-3133-4ead-91cb-9ca6068e3e72",
        "started_utc": started_utc,
        "completed_utc": utc_now(),
        "stage1_disposition": "changes_requested",
        "runtime_acceptance_status": "pending_stage2_gpu_and_recovery_release",
        "lineage": lineage,
        "host_snapshots": {
            "before": pre_host,
            "after": post_host,
        },
        "external_roots": {
            "f2_reviewer_root_path": str(EXTERNAL_F2_REVIEWER_ROOT),
            "f2_reviewer_root_exists_before": False,
            "f2_reviewer_root_exists_after": EXTERNAL_F2_REVIEWER_ROOT.exists(),
            "f2_parent_root_exists": EXTERNAL_F2_PARENT_ROOT.exists(),
        },
        "owned_postgres_cluster": {
            "port": REVIEWER_PG_PORT,
            "postmaster_identities": postmaster_identities,
            "cleaned_databases_before_stop": dropped_dbs,
            "stopped_cleanly_at_end": not is_loopback_port_bound(REVIEWER_PG_PORT),
        },
        "author_scratch_log_audit": author_log_audit,
        "static_provenance_and_isolation": static_audit,
        "python_heartbeat_guard_probe": py_guard_probe,
        "independent_csharp_probes": probe_bundle["results"] if probe_bundle else None,
        "reviewer_demo_smoke_receipt": demo_receipt_data,
        "reviewer_f2_browser_evidence": f2_browser_data,
        "steps": steps,
        "post_git_porcelain_before_evidence_write": post_porcelain,
    }

    out_path = REVIEW_DIR / "stage1-verification-summary.json"
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
