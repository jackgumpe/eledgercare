"""Stage 2 finite real local OCR runtime acceptance runner for eld-f2-implementer (WP-0006).

Executes the coordinator-released 4-model-attempt matrix (717a768994bbbabf75b8ee96b3b1aadca1bc5df3)
against frozen product source 0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978 / clean executing HEAD
6faec9bf6eccc297a548523dbb52ae9262b25152 under sole GPU lease WP-0006-author-runtime-20261116T062318Z:
  1. Attempt #1: SYN-WO-01-v1-raster300.pdf (1p) -> completed persisted result + API & Edge verification
  2. Attempt #2: SYN-MP-01-v0-clean.pdf (3p) -> completed 3 ordered pages + API/DB/disk verification
  3. Attempt #3 & #4: fresh SYN-WO-01-v1-raster300.pdf -> single-process TerminateProcess on owned API
     supervisor during observed inference (forward_progress >= 1), kernel Job Object exit of launcher+worker,
     API restart -> reconciled 'interrupted' attempt (0 accepted result), 409 on empty replay, then explicit
     prior-attempt retry -> Attempt #4 completed, retaining both attempts and monotonic fencing tokens
  4. Stop model work, fast restart PostgreSQL 18.7 + start API with LocalOcr__Enabled=false -> reopen all
     3 saved completed documents and originals via HTTP API and headless Microsoft Edge without model execution,
     then stop services, re-verify 18 model objects + notice, and record explicit GPU lease return.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parent.parent.parent.parent
STAGE2_DIR = ROOT / ".scratch" / "stage2-runtime"
HELPERS_DIR = STAGE2_DIR / "helpers"
OBS_DIR = STAGE2_DIR / "observations"
OBS_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "workers" / "local_ocr"))
from local_ocr.env_guard import directory_size_bytes  # noqa: E402
from local_ocr.protocol import MODEL_MANIFEST_PATH, sha256_bytes  # noqa: E402
from local_ocr.verify_runtime import (  # noqa: E402
    load_json_checked,
    normalize_and_verify_model_dir,
    verify_model_sources_ast_safety,
)

EXPECTED_EXECUTING_HEAD = "6faec9bf6eccc297a548523dbb52ae9262b25152"
EXPECTED_SOURCE_COMMIT = "0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978"
RELEASE_COMMIT = "717a768994bbbabf75b8ee96b3b1aadca1bc5df3"
LEASE_ID = "WP-0006-author-runtime-20261116T062318Z"
GPU_UUID = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"
Q0_ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")
RUNTIME_ROOT = Path(r"C:\Users\jackg\eLedgerCare-F2\WP-0006\author")
DATABASE_NAME = "eledgercare_f2_runtime_author"
API_PORT = 5190
UI_PORT = 4210
PG_PORT = 55434
MAX_MODEL_ATTEMPTS = 4

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_TERMINATE = 0x0001
STILL_ACTIVE = 259


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Win32 exact (PID, CreationTime FILETIME) & single-process TerminateProcess helpers ---
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


def query_process_filetime_and_alive(pid: int) -> tuple[int | None, bool]:
    if not pid or pid <= 0:
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


def capture_host_and_gpu_snapshot(label: str) -> dict:
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
    # Filter non-WDDM CUDA compute apps (where used_memory != '[N/A]') vs desktop WDDM graphics processes
    app_lines = [ln.strip() for ln in compute_apps.splitlines() if ln.strip()]
    cuda_compute_apps = [ln for ln in app_lines if not ln.endswith("[N/A]")]
    wddm_desktop_count = len(app_lines) - len(cuda_compute_apps)

    py_dotnet_procs = subprocess.check_output(
        [
            "pwsh",
            "-NoProfile",
            "-Command",
            "Get-Process python*,dotnet*,postgres*,node* -ErrorAction SilentlyContinue | "
            "Select-Object Id,ProcessName | ConvertTo-Json -Compress",
        ],
        text=True,
    ).strip()

    disk_c = shutil.disk_usage(r"C:\\")
    snap = {
        "label": label,
        "observed_utc": utc_now(),
        "logical_cpus": os.cpu_count(),
        "ram_total_bytes": mem.ullTotalPhys,
        "ram_avail_bytes": mem.ullAvailPhys,
        "memory_load_pct": mem.dwMemoryLoad,
        "disk_c_free_bytes": disk_c.free,
        "runtime_root_used_bytes": directory_size_bytes(RUNTIME_ROOT),
        "ports_bound": {str(p): check_port_bound(p) for p in (API_PORT, UI_PORT, PG_PORT)},
        "nvidia_smi_gpu": gpu_line,
        "cuda_compute_apps": cuda_compute_apps,
        "wddm_desktop_app_count": wddm_desktop_count,
        "host_confounders_note": (
            "Windows 11 WDDM desktop session shares the RTX 5070 Ti (~1.35 GiB baseline VRAM across desktop apps) "
            "and independent CPU/PostgreSQL/Edge review (eld-next-reviewer) plus WP-0007 CPU correction work may "
            "contend for host CPU/RAM; timings are operational product observations, not isolated benchmarks."
        ),
        "active_python_dotnet_postgres_node_processes": json.loads(py_dotnet_procs) if py_dotnet_procs else [],
    }
    (OBS_DIR / f"{label}.json").write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    return snap


def verify_model_integrity_snapshot(label: str) -> dict:
    manifest, manifest_sha = load_json_checked(MODEL_MANIFEST_PATH, None, "model-files.json")
    model_dir = normalize_and_verify_model_dir(
        str(Q0_ROOT / "models" / "Unlimited_OCR_2_04809669"),
        str(Q0_ROOT / "notices" / "Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"),
        manifest,
    )
    verify_model_sources_ast_safety(model_dir)
    rec = {
        "label": label,
        "observed_utc": utc_now(),
        "q0_root": str(Q0_ROOT),
        "model_manifest_sha256": manifest_sha,
        "runtime_objects_verified": 18,
        "notice_readme_verified": True,
        "static_ast_safety_verified": True,
    }
    (OBS_DIR / f"{label}.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec


class OwnedPostgres:
    def __init__(self):
        self.settings = json.loads((ROOT / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
        self.psql = ROOT / ".local" / "tools" / "pgsql-18.7-1" / "bin" / "psql.exe"

    def start(self) -> dict:
        subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "deploy/dev/postgres/start-cluster.ps1")],
            cwd=ROOT,
            check=True,
        )
        pid_line = (ROOT / ".local/postgres-data/postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip()
        pid = int(pid_line)
        ft, alive = query_process_filetime_and_alive(pid)
        if not alive or not ft:
            raise RuntimeError(f"Started postmaster PID {pid} not alive")
        return {"postmaster_pid": pid, "postmaster_create_filetime": ft, "started_utc": utc_now()}

    def stop(self) -> dict:
        pid_file = ROOT / ".local/postgres-data/postmaster.pid"
        prior_pid = int(pid_file.read_text(encoding="utf-8").splitlines()[0].strip()) if pid_file.exists() else None
        subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "deploy/dev/postgres/stop-cluster.ps1")],
            cwd=ROOT,
            check=True,
        )
        return {"stopped_postmaster_pid": prior_pid, "stopped_utc": utc_now(), "port_55434_bound": check_port_bound(PG_PORT)}

    def prepare_database(self, db_name: str) -> str:
        proc = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "deploy/dev/database/prepare-database.ps1"), "-Database", db_name],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout

    def query_json(self, sql: str, *, db_name: str = DATABASE_NAME, role: str = "admin") -> object:
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
                db_name,
                "-c",
                wrapped,
            ],
            env=env,
            text=True,
        ).strip()
        return json.loads(out) if out else []

    def app_connection_string(self, db_name: str = DATABASE_NAME) -> str:
        s = self.settings
        return (
            f"Host={s['host']};Port={s['port']};Database={db_name};"
            f"Username={s['appUser']};Password={s['appPassword']}"
        )


class OwnedApiInstance:
    def __init__(self, label: str, app_conn_str: str, *, ocr_enabled: bool):
        self.label = label
        self.ocr_enabled = ocr_enabled
        self.app_conn_str = app_conn_str
        self.proc: subprocess.Popen | None = None
        self.pid: int = 0
        self.create_filetime: int = 0
        self.started_utc: str = ""
        self.stdout_log = OBS_DIR / f"api-{label}.stdout.log"
        self.stderr_log = OBS_DIR / f"api-{label}.stderr.log"
        self._out_fh = None
        self._err_fh = None

    def start(self) -> dict:
        if check_port_bound(API_PORT):
            raise RuntimeError(f"Port {API_PORT} is already bound before starting API '{self.label}'.")
        api_dir = ROOT / "src" / "ELedgerCare.Api" / "bin" / "Release" / "net10.0"
        api_dll = api_dir / "ELedgerCare.Api.dll"
        if not api_dll.is_file():
            raise FileNotFoundError(f"Missing built API assembly: {api_dll}")

        env = dict(os.environ)
        env["ASPNETCORE_ENVIRONMENT"] = "Production"
        env["DOTNET_NOLOGO"] = "1"
        env["Api__Port"] = str(API_PORT)
        env["ConnectionStrings__Runtime"] = self.app_conn_str
        if self.ocr_enabled:
            env["LocalOcr__Enabled"] = "true"
            env["LocalOcr__ReadOnlyQ0Root"] = str(Q0_ROOT)
            env["LocalOcr__WritableRuntimeRoot"] = str(RUNTIME_ROOT)
            env["LocalOcr__LeasedGpuUuid"] = GPU_UUID
            env["LocalOcr__WorkerRootPath"] = str(ROOT / "workers" / "local_ocr")
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
            if check_port_bound(API_PORT):
                break
            time.sleep(0.15)
        else:
            raise TimeoutError(f"API '{self.label}' did not bind 127.0.0.1:{API_PORT} within 60s.")

        return {
            "label": self.label,
            "pid": self.pid,
            "create_filetime": self.create_filetime,
            "ocr_enabled": self.ocr_enabled,
            "started_utc": self.started_utc,
        }

    def stop_single_process(self) -> dict:
        res = {"label": self.label, "pid": self.pid, "create_filetime": self.create_filetime}
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
        # Wait briefly for loopback port release
        t_end = time.monotonic() + 10.0
        while time.monotonic() < t_end and check_port_bound(API_PORT):
            time.sleep(0.1)
        res["stopped_utc"] = utc_now()
        res["port_5190_bound_after"] = check_port_bound(API_PORT)
        return res


def http_request(
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> tuple[int, dict[str, str], bytes]:
    url = f"http://127.0.0.1:{API_PORT}{path}"
    req = urllib.request.Request(url, data=body, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers.items()), resp.read()
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers.items()), err.read()


def submit_pdf(pdf_path: Path) -> dict:
    pdf_bytes = pdf_path.read_bytes()
    expected_sha = sha256_bytes(pdf_bytes)
    idem_key = str(uuid.uuid4())
    status, headers, raw = http_request(
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


def request_extraction_http(document_id: str, retry_attempt_id: str | None = None) -> tuple[int, dict]:
    if retry_attempt_id is None:
        status, _, raw = http_request("POST", f"/api/documents/{document_id}/extraction", body=b"")
    else:
        payload = json.dumps({"retryAttemptId": retry_attempt_id}).encode("utf-8")
        status, _, raw = http_request(
            "POST",
            f"/api/documents/{document_id}/extraction",
            body=payload,
            headers={"Content-Type": "application/json"},
        )
    return status, json.loads(raw.decode("utf-8")) if raw else {}


def wait_for_completed_attempt(
    pg: OwnedPostgres,
    document_id: str,
    *,
    timeout_s: float,
    tracked_identities: list[dict],
) -> dict:
    t0 = time.monotonic()
    timeline: list[dict] = []
    last_state_key = None
    gpu_samples: list[str] = []
    seen_attempt_id: str | None = None

    while time.monotonic() - t0 < timeout_s:
        status_code, _, raw = http_request("GET", f"/api/documents/{document_id}/extraction")
        if status_code != 200:
            raise RuntimeError(f"GET /extraction returned {status_code}")
        view = json.loads(raw.decode("utf-8"))
        cur = view.get("currentAttempt")
        att_id = cur["attemptId"] if cur else None
        if att_id:
            seen_attempt_id = att_id

        hb_data = None
        if seen_attempt_id:
            hb_path = RUNTIME_ROOT / "runs" / f"attempt-{seen_attempt_id}" / "output" / "heartbeat.json"
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
            winning_attempt_id = res_row["attempt_id"]
            run_dir = RUNTIME_ROOT / "runs" / f"attempt-{winning_attempt_id}"
            raw_disk = (run_dir / "output" / "raw_output.utf8.bin").read_bytes()
            raw_disk_sha = sha256_bytes(raw_disk)
            envelope_disk = json.loads((run_dir / "output" / "envelope.json").read_text(encoding="utf-8"))
            request_disk = json.loads((run_dir / "request.json").read_text(encoding="utf-8"))

            api_res = view["result"]
            api_raw_bytes = api_res["rawText"].encode("utf-8")
            api_raw_sha = sha256_bytes(api_raw_bytes)

            if not (raw_disk_sha == res_row["raw_output_sha256"] == api_res["rawSha256"] == api_raw_sha == envelope_disk["output"]["sha256"]):
                raise RuntimeError("Raw SHA-256 mismatch across disk, DB, envelope, and API!")

            orig_status, _, orig_bytes = http_request("GET", f"/api/documents/{document_id}/original")
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


def run_edge_ui_verification(label: str, docs_spec: list[dict]) -> dict:
    in_path = OBS_DIR / f"ui-spec-{label}.json"
    out_path = OBS_DIR / f"ui-verified-{label}.json"
    in_path.write_text(
        json.dumps({"uiPort": UI_PORT, "apiPort": API_PORT, "documents": docs_spec}, indent=2) + "\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            "node",
            str(HELPERS_DIR / "verify_ui_real_results.mjs"),
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


def verify_freeze_and_git_clean() -> dict:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    parent = subprocess.check_output(["git", "rev-parse", "HEAD~1"], cwd=ROOT, text=True).strip()
    porcelain = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    if head != EXPECTED_EXECUTING_HEAD or parent != EXPECTED_SOURCE_COMMIT or porcelain != "":
        raise RuntimeError(f"Invalid Git state: head={head}, parent={parent}, porcelain={porcelain!r}")

    freeze_path = STAGE2_DIR / "plan-and-helper-freeze.json"
    if not freeze_path.is_file():
        raise RuntimeError("plan-and-helper-freeze.json must be frozen before decisive execution.")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    for item in freeze["frozen_helpers"]:
        p = ROOT / item["relative_path"]
        raw = p.read_bytes()
        if len(raw) != item["byte_length"] or sha256_bytes(raw) != item["sha256"]:
            raise RuntimeError(f"Frozen helper {item['relative_path']} modified after freeze!")
    return {"head": head, "source_commit": parent, "clean": True, "freeze_verified": True}


def main() -> int:
    trial_started_utc = utc_now()
    tracked_identities: list[dict] = []
    active_api: OwnedApiInstance | None = None
    pg = OwnedPostgres()
    pg_started = False
    trial_record: dict = {
        "schema": "eledgercare.wp-0006.author-runtime-summary/1",
        "release_authority_commit": RELEASE_COMMIT,
        "lease_id": LEASE_ID,
        "gpu_uuid": GPU_UUID,
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "executing_head": EXPECTED_EXECUTING_HEAD,
        "writable_runtime_root": str(RUNTIME_ROOT),
        "readonly_q0_root": str(Q0_ROOT),
        "database": DATABASE_NAME,
        "worker_allowed_environment_names_only": [
            "CUDA_CACHE_PATH", "CUDA_DEVICE_ORDER", "CUDA_VISIBLE_DEVICES", "ComSpec",
            "HF_HOME", "HF_HUB_CACHE", "HF_HUB_DISABLE_PROGRESS_BARS", "HF_HUB_DISABLE_TELEMETRY",
            "HF_HUB_DISABLE_XET", "HF_HUB_OFFLINE", "HF_MODULES_CACHE", "HOME", "HUGGINGFACE_HUB_CACHE",
            "NUMBER_OF_PROCESSORS", "OS", "PATH", "PATHEXT", "PIP_CACHE_DIR", "PIP_CONFIG_FILE",
            "PIP_NO_INDEX", "PROCESSOR_ARCHITECTURE", "PROCESSOR_IDENTIFIER", "PROCESSOR_LEVEL",
            "PROCESSOR_REVISION", "SYSTEMROOT", "SystemRoot", "TEMP", "TMP", "TMPDIR",
            "TORCHINDUCTOR_CACHE_DIR", "TORCH_HOME", "TRANSFORMERS_CACHE", "TRANSFORMERS_OFFLINE",
            "TRITON_CACHE_DIR", "USERPROFILE", "UV_CACHE_DIR", "VIRTUAL_ENV", "XDG_CACHE_HOME", "windir",
        ],
        "started_utc": trial_started_utc,
        "scenarios": {},
    }

    try:
        print("[Stage2] 0. Verifying git state, helper freeze, ports, storage, and model preflight...", flush=True)
        trial_record["git_and_freeze_before"] = verify_freeze_and_git_clean()
        for p in (API_PORT, UI_PORT, PG_PORT):
            if check_port_bound(p):
                raise RuntimeError(f"Port {p} is unexpectedly bound before trial start.")

        if RUNTIME_ROOT.exists() and any(RUNTIME_ROOT.iterdir()):
            raise RuntimeError(f"Writable runtime root {RUNTIME_ROOT} already has contents; refusing reuse.")
        RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)

        trial_record["host_before"] = capture_host_and_gpu_snapshot("host-before")
        trial_record["model_before"] = verify_model_integrity_snapshot("model-before")

        print("[Stage2] Starting owned PostgreSQL 18.7 cluster on 127.0.0.1:55434...", flush=True)
        pg_info_1 = pg.start()
        pg_started = True
        prep_out = pg.prepare_database(DATABASE_NAME)
        (OBS_DIR / "prepare-database-runtime.log").write_text(prep_out, encoding="utf-8")
        trial_record["postgres_initial"] = pg_info_1

        # Start API #1 with LocalOcr__Enabled=true
        print("[Stage2] Starting owned ELedgerCare.Api #1 (LocalOcr:Enabled=true) on 127.0.0.1:5190...", flush=True)
        active_api = OwnedApiInstance("run1-ocr-enabled", pg.app_connection_string(), ocr_enabled=True)
        trial_record["api_1_start"] = active_api.start()

        # --- SCENARIO 1: Model Attempt #1 (SYN-WO-01-v1-raster300.pdf, 1 page) ---
        print("[Stage2] SCENARIO 1 / Attempt #1: Submitting SYN-WO-01-v1-raster300.pdf (1 page)...", flush=True)
        f01_path = ROOT / "tests" / "fixtures" / "SYN-WO-01-v1-raster300.pdf"
        sub1 = submit_pdf(f01_path)
        doc1_id = sub1["receipt"]["documentId"]
        post1_status, post1_body = request_extraction_http(doc1_id)
        if post1_status != 202:
            raise RuntimeError(f"Expected 202 Accepted on doc1 extraction, got {post1_status}: {post1_body}")
        comp1 = wait_for_completed_attempt(pg, doc1_id, timeout_s=2100.0, tracked_identities=tracked_identities)
        print(
            f"[Stage2] Attempt #1 COMPLETED! attempt={comp1['winning_attempt_id']} "
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
                    "expectedOriginalSha256": sub1["expected_sha256"],
                    "expectedOriginalBytes": sub1["expected_byte_length"],
                }
            ],
        )
        trial_record["scenarios"]["1_f01_single_page_complete"] = {
            "submission": sub1,
            "request_extraction_status": post1_status,
            "completion": comp1,
            "edge_ui_verification": ui1,
        }

        # --- SCENARIO 2: Model Attempt #2 (SYN-MP-01-v0-clean.pdf, 3 pages) ---
        print("[Stage2] SCENARIO 2 / Attempt #2: Submitting SYN-MP-01-v0-clean.pdf (3 pages)...", flush=True)
        f07_path = ROOT / "tests" / "fixtures" / "SYN-MP-01-v0-clean.pdf"
        sub2 = submit_pdf(f07_path)
        doc2_id = sub2["receipt"]["documentId"]
        post2_status, post2_body = request_extraction_http(doc2_id)
        if post2_status != 202:
            raise RuntimeError(f"Expected 202 Accepted on doc2 extraction, got {post2_status}: {post2_body}")
        comp2 = wait_for_completed_attempt(pg, doc2_id, timeout_s=3900.0, tracked_identities=tracked_identities)
        if comp2["api_page_numbers"] != [1, 2, 3]:
            raise RuntimeError(f"Expected ordered pages [1, 2, 3], got {comp2['api_page_numbers']}")
        print(
            f"[Stage2] Attempt #2 COMPLETED! attempt={comp2['winning_attempt_id']} "
            f"pages={comp2['api_page_numbers']} raw_sha={comp2['db_result']['raw_output_sha256']} "
            f"total_ms={comp2['db_result']['total_duration_ms']}",
            flush=True,
        )
        trial_record["scenarios"]["2_f07_three_page_complete"] = {
            "submission": sub2,
            "request_extraction_status": post2_status,
            "completion": comp2,
        }

        # --- SCENARIO 3: Model Attempt #3 (Deliberate Supervisor Single-Process Kill During Inference) + Attempt #4 (Explicit Retry) ---
        print("[Stage2] SCENARIO 3 / Attempt #3: Submitting fresh SYN-WO-01-v1-raster300.pdf for live interruption...", flush=True)
        sub3 = submit_pdf(f01_path)
        doc3_id = sub3["receipt"]["documentId"]
        post3_status, post3_body = request_extraction_http(doc3_id)
        if post3_status != 202:
            raise RuntimeError(f"Expected 202 Accepted on doc3 extraction, got {post3_status}: {post3_body}")

        # Poll rapidly (250ms) until Attempt #3 is in actual CUDA inference with forward_progress >= 1
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
                hb_file = RUNTIME_ROOT / "runs" / r["run_directory_name"] / "output" / "heartbeat.json"
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
            raise RuntimeError("Did not observe active inference (phase='inferring', forward_progress>=1) on Attempt #3.")

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
            f"[Stage2] Attempt #3 active inference confirmed! forward_progress={hb_at_kill['forward_progress']} "
            f"supervisor={active_api.pid} launcher={l_pid} worker={w_pid}. Executing single-process TerminateProcess on supervisor ONLY...",
            flush=True,
        )
        t_kill = time.perf_counter()
        kill_receipt = active_api.stop_single_process()
        active_api = None

        # Observe Job Object kernel cleanup of launcher and CUDA worker!
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
            f"[Stage2] Job Object killed launcher+worker in {job_cleanup_ms} ms (cuda_compute_apps={cuda_after_kill}). "
            f"Starting API #2 to reconcile abandoned Attempt #3...",
            flush=True,
        )
        active_api = OwnedApiInstance("run2-recovery-and-retry", pg.app_connection_string(), ocr_enabled=True)
        api2_start = active_api.start()

        # Poll until startup ReconcileAbandonedAttemptsAsync marks Attempt #3 'interrupted'
        t_rec = time.monotonic()
        reconciled_view = None
        while time.monotonic() - t_rec < 20.0:
            st, _, raw = http_request("GET", f"/api/documents/{doc3_id}/extraction")
            if st == 200:
                v = json.loads(raw.decode("utf-8"))
                if v["status"] == "interrupted":
                    reconciled_view = v
                    break
            time.sleep(0.25)
        if reconciled_view is None:
            raise RuntimeError("API #2 did not reconcile abandoned Attempt #3 to 'interrupted' within 20s.")

        # Confirm empty-body replay returns 409 retry_explicit_required without creating any model attempt!
        replay_409_status, replay_409_body = request_extraction_http(doc3_id, retry_attempt_id=None)
        if replay_409_status != 409 or replay_409_body.get("code") != "retry_explicit_required":
            raise RuntimeError(f"Expected 409 retry_explicit_required, got {replay_409_status}: {replay_409_body}")

        # Now issue explicit prior-attempt retry -> Model Attempt #4!
        attempt3_id = attempt3_row["attempt_id"]
        print(f"[Stage2] Issuing explicit retry for Attempt #3 ({attempt3_id}) -> Model Attempt #4...", flush=True)
        retry4_status, retry4_body = request_extraction_http(doc3_id, retry_attempt_id=attempt3_id)
        if retry4_status != 202:
            raise RuntimeError(f"Expected 202 Accepted on explicit retry, got {retry4_status}: {retry4_body}")

        comp4 = wait_for_completed_attempt(pg, doc3_id, timeout_s=2100.0, tracked_identities=tracked_identities)
        if len(comp4["db_attempts"]) != 2:
            raise RuntimeError(f"Expected 2 attempts retained on doc3, got {len(comp4['db_attempts'])}")
        if comp4["db_attempts"][0]["status"] != "interrupted" or comp4["db_attempts"][1]["status"] != "completed":
            raise RuntimeError(f"Unexpected doc3 attempt statuses: {comp4['db_attempts']}")
        if int(comp4["db_attempts"][1]["fencing_token"]) <= int(comp4["db_attempts"][0]["fencing_token"]):
            raise RuntimeError("Attempt #4 fencing token was not strictly greater than Attempt #3!")

        print(
            f"[Stage2] Attempt #4 COMPLETED! doc3 retains Attempt #1=interrupted (token={comp4['db_attempts'][0]['fencing_token']}) "
            f"and Attempt #2=completed (token={comp4['db_attempts'][1]['fencing_token']}).",
            flush=True,
        )
        trial_record["scenarios"]["3_live_supervisor_kill_and_explicit_retry"] = {
            "submission": sub3,
            "attempt3_observed_at_kill": {
                "db_row": attempt3_row,
                "heartbeat": hb_at_kill,
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

        # --- SCENARIO 4: Stop Model Work, Restart API + PostgreSQL (fast), Reopen All Saved Results with LocalOcr__Enabled=false ---
        print("[Stage2] SCENARIO 4: Stopping OCR-enabled API, fast-restarting PostgreSQL 18.7, and reopening with LocalOcr:Enabled=false...", flush=True)
        api2_stop = active_api.stop_single_process()
        active_api = None

        run_dirs = sorted(p.name for p in (RUNTIME_ROOT / "runs").iterdir() if p.is_dir())
        if len(run_dirs) != MAX_MODEL_ATTEMPTS:
            raise RuntimeError(f"Expected exactly {MAX_MODEL_ATTEMPTS} run directories, found {len(run_dirs)}: {run_dirs}")

        pg_stop_mid = pg.stop()
        pg_start_after = pg.start()

        active_api = OwnedApiInstance("run3-ocr-disabled-reopen", pg.app_connection_string(), ocr_enabled=False)
        api3_start = active_api.start()

        reopened_api_checks = []
        for label, sub, comp, want_attempts in [
            ("doc1_f01_1p", sub1, comp1, 1),
            ("doc2_f07_3p", sub2, comp2, 1),
            ("doc3_f01_interrupted_then_retried", sub3, comp4, 2),
        ]:
            d_id = sub["receipt"]["documentId"]
            st_doc, _, raw_doc = http_request("GET", f"/api/documents/{d_id}")
            st_ext, _, raw_ext = http_request("GET", f"/api/documents/{d_id}/extraction")
            st_rep, rep_body = request_extraction_http(d_id, retry_attempt_id=None)
            st_org, _, raw_org = http_request("GET", f"/api/documents/{d_id}/original")

            doc_body = json.loads(raw_doc.decode("utf-8"))
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

        # Verify ALL THREE saved real results in headless Microsoft Edge while LocalOcr__Enabled=false!
        ui_all_disabled = run_edge_ui_verification(
            "scenario4-all-reopened-ocr-disabled",
            [
                {
                    "label": "Reopened Doc 1: SYN-WO-01 (1p) after API+PG restart with OCR disabled",
                    "documentId": doc1_id,
                    "expectedPages": 1,
                    "expectedRawSha256": comp1["db_result"]["raw_output_sha256"],
                    "expectedAttemptCount": 1,
                    "expectedOriginalSha256": sub1["expected_sha256"],
                    "expectedOriginalBytes": sub1["expected_byte_length"],
                },
                {
                    "label": "Reopened Doc 2: SYN-MP-01 (3p) after API+PG restart with OCR disabled",
                    "documentId": doc2_id,
                    "expectedPages": 3,
                    "expectedRawSha256": comp2["db_result"]["raw_output_sha256"],
                    "expectedAttemptCount": 1,
                    "expectedOriginalSha256": sub2["expected_sha256"],
                    "expectedOriginalBytes": sub2["expected_byte_length"],
                },
                {
                    "label": "Reopened Doc 3: SYN-WO-01 (interrupted + retried) after API+PG restart with OCR disabled",
                    "documentId": doc3_id,
                    "expectedPages": 1,
                    "expectedRawSha256": comp4["db_result"]["raw_output_sha256"],
                    "expectedAttemptCount": 2,
                    "expectedOriginalSha256": sub3["expected_sha256"],
                    "expectedOriginalBytes": sub3["expected_byte_length"],
                },
            ],
        )

        # Verify run directory count did NOT change during disabled reopen (still 4!)
        run_dirs_after_reopen = sorted(p.name for p in (RUNTIME_ROOT / "runs").iterdir() if p.is_dir())
        if run_dirs_after_reopen != run_dirs:
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
            "run_directories_unchanged": run_dirs_after_reopen,
        }

        trial_record["outcome"] = "COMPLETED_ALL_4_SCENARIOS"
        return 0

    except Exception as exc:
        trial_record["outcome"] = "FAILED"
        trial_record["error"] = f"{type(exc).__name__}: {exc}"
        raise

    finally:
        # Emergency/normal cleanup: ensure owned API & PostgreSQL are stopped, verify every spawned launcher/worker
        # identity is dead, re-verify model integrity, and write explicit GPU lease return!
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

        # De-duplicate tracked launcher/worker OS identities and confirm 100% exited
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

        model_after = verify_model_integrity_snapshot("model-after")
        host_after = capture_host_and_gpu_snapshot("host-after")
        git_after = verify_freeze_and_git_clean()

        trial_record["completed_utc"] = utc_now()
        trial_record["git_and_freeze_after"] = git_after
        trial_record["model_after"] = model_after
        trial_record["host_after"] = host_after
        trial_record["observed_model_process_identities"] = unique_identities

        lease_return = {
            "schema": "eledgercare.gpu-lease-return/1",
            "lease_id": LEASE_ID,
            "owner": "eld-f2-implementer",
            "conversation_id": "2b6861af-031b-4e8b-9ce9-2a6d476f9da0",
            "gpu_uuid": GPU_UUID,
            "lease_state": "RETURNED_BY_OWNER_PENDING_COORDINATOR_ACK",
            "returned_utc": utc_now(),
            "model_attempts_executed": len(
                [p for p in (RUNTIME_ROOT / "runs").iterdir() if p.is_dir()]
            ) if (RUNTIME_ROOT / "runs").exists() else 0,
            "max_model_attempts_allowed": MAX_MODEL_ATTEMPTS,
            "all_owned_model_processes_observed_exited": all(
                not x["launcher_alive_at_return"] and not x["worker_alive_at_return"]
                for x in unique_identities
            ),
            "observed_model_process_identities": unique_identities,
            "cuda_compute_apps_at_return": host_after["cuda_compute_apps"],
            "ports_bound_at_return": host_after["ports_bound"],
            "model_18_objects_and_notice_unchanged": model_after["runtime_objects_verified"] == 18
            and model_after["notice_readme_verified"],
            "runtime_root": str(RUNTIME_ROOT),
            "runtime_root_used_bytes": host_after["runtime_root_used_bytes"],
        }
        (STAGE2_DIR / "lease-return.json").write_text(json.dumps(lease_return, indent=2) + "\n", encoding="utf-8")
        (STAGE2_DIR / "trial-summary.json").write_text(json.dumps(trial_record, indent=2) + "\n", encoding="utf-8")
        print(
            f"[Stage2] Finalized trial-summary.json ({trial_record.get('outcome')}) and explicit lease-return.json "
            f"(all_exited={lease_return['all_owned_model_processes_observed_exited']}).",
            flush=True,
        )


if __name__ == "__main__":
    raise SystemExit(main())
