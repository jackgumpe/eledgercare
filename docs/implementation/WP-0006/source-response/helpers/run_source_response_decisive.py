"""Post-freeze decisive CPU, child-process, and PostgreSQL 18.7 verification runner for WP-0006 source-response."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / ".scratch" / "source-response-decisive"
LOGS_DIR = OUT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

EXTERNAL_AUTHOR_ROOT = Path(r"C:\Users\jackg\eLedgerCare-F2\WP-0006\author")
Q0_ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def port_bound(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def query_pid_filetime(pid: int) -> int | None:
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    k32.GetProcessTimes.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL
    h = k32.OpenProcess(0x1000, False, pid)
    if not h:
        return None
    try:
        c, e, kt, ut = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
        if not k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut)):
            return None
        return (int(c.dwHighDateTime) << 32) | int(c.dwLowDateTime)
    finally:
        k32.CloseHandle(h)


def external_dir_fingerprint(p: Path) -> dict:
    if not p.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0}
    files = sorted(f for f in p.rglob("*") if f.is_file())
    return {
        "exists": True,
        "file_count": len(files),
        "total_bytes": sum(f.stat().st_size for f in files),
        "run_dirs": sorted(d.name for d in (p / "runs").iterdir() if d.is_dir()) if (p / "runs").exists() else [],
    }


def git_state() -> dict:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    porcelain = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    return {"head": head, "porcelain": porcelain, "clean": porcelain == ""}


def run_step(step_id: str, cmd: list[str], *, cwd: Path = ROOT) -> dict:
    env = dict(os.environ)
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"

    started_utc = utc_now()
    t0 = time.perf_counter()
    print(f"[{step_id}] START: {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True)
    elapsed_ms = round((time.perf_counter() - t0) * 1000)
    ended_utc = utc_now()

    header = f"$ {' '.join(cmd)}\n--- STDOUT ---\n".encode("utf-8")
    mid = b"\n--- STDERR ---\n"
    tail = b"\n"
    raw_bytes = header + proc.stdout + mid + proc.stderr + tail

    log_path = LOGS_DIR / f"{step_id}.log"
    log_path.write_bytes(raw_bytes)
    lf_bytes = raw_bytes.replace(b"\r\n", b"\n")

    print(f"[{step_id}] EXIT={proc.returncode} ({elapsed_ms} ms)", flush=True)
    if proc.returncode != 0:
        sys.stdout.buffer.write(proc.stdout[-2000:])
        sys.stderr.buffer.write(proc.stderr[-2000:])
        raise RuntimeError(f"Step {step_id} failed with exit code {proc.returncode}")

    wt_str = str(ROOT)
    sanitized_cmd = [c.replace(wt_str, "<worktree>") for c in cmd]
    return {
        "step_id": step_id,
        "command": sanitized_cmd,
        "cwd": str(cwd.relative_to(ROOT)) if cwd != ROOT else ".",
        "started_utc": started_utc,
        "ended_utc": ended_utc,
        "duration_ms": elapsed_ms,
        "exit_code": proc.returncode,
        "raw_bytes": len(raw_bytes),
        "raw_file_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "lf_bytes": len(lf_bytes),
        "lf_normalized_sha256": hashlib.sha256(lf_bytes).hexdigest(),
    }


def main() -> int:
    if len(sys.argv) != 2:
        raise RuntimeError("Usage: python run_source_response_decisive.py <expected_frozen_sha>")
    expected_sha = sys.argv[1].strip()

    pre_git = git_state()
    if pre_git["head"] != expected_sha or not pre_git["clean"]:
        raise RuntimeError(f"Repository must be clean at frozen SHA {expected_sha}: {pre_git}")

    ports_before = {str(p): port_bound(p) for p in (5190, 4210, 55434)}
    if any(ports_before.values()):
        raise RuntimeError(f"Owned port already bound before starting decisive checks: {ports_before}")

    ext_before = external_dir_fingerprint(EXTERNAL_AUTHOR_ROOT)
    nuget_pkgs = str(ROOT / ".local" / "nuget")
    steps: list[dict] = []
    pg_started = False
    pg_postmaster = None

    try:
        subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "deploy/dev/postgres/start-cluster.ps1")],
            cwd=ROOT,
            check=True,
        )
        pg_started = True
        pm_pid = int((ROOT / ".local/postgres-data/postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        pg_postmaster = {
            "pid": pm_pid,
            "create_filetime": query_pid_filetime(pm_pid),
            "port": 55434,
            "started_utc": utc_now(),
        }

        steps.append(run_step("01-dotnet-restore-locked", ["dotnet", "restore", "ELedgerCare.slnx", "--locked-mode", "--packages", nuget_pkgs]))
        steps.append(run_step("02-dotnet-build-release", ["dotnet", "build", "ELedgerCare.slnx", "-c", "Release", "--no-restore"]))
        steps.append(run_step("03-dotnet-publish-api", ["dotnet", "publish", "src/ELedgerCare.Api/ELedgerCare.Api.csproj", "-c", "Release", "--no-restore"]))
        steps.append(run_step("04-python-worker-cpu-tests", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "workers/local_ocr/tests", "-p", "test_*.py", "-v"]))
        steps.append(run_step("05-dotnet-test-solution", ["dotnet", "test", "--solution", "ELedgerCare.slnx", "-c", "Release", "--no-build"]))
    finally:
        if pg_started:
            subprocess.run(
                ["pwsh", "-NoProfile", "-File", str(ROOT / "deploy/dev/postgres/stop-cluster.ps1")],
                cwd=ROOT,
                check=True,
            )

    ports_after = {str(p): port_bound(p) for p in (5190, 4210, 55434)}
    if any(ports_after.values()):
        raise RuntimeError(f"Owned port remained bound after teardown: {ports_after}")

    ext_after = external_dir_fingerprint(EXTERNAL_AUTHOR_ROOT)
    if ext_after != ext_before:
        raise RuntimeError(f"External F2 runtime root mutated during CPU checks: before={ext_before}, after={ext_after}")

    post_git = git_state()
    if post_git["head"] != expected_sha or not post_git["clean"]:
        raise RuntimeError(f"Repository became dirty during decisive run: {post_git}")

    sys.path.insert(0, str(ROOT / "workers" / "local_ocr"))
    from local_ocr import protocol as wp  # noqa: E402

    summary = {
        "schema": "eledgercare.wp-0006.source-response-decisive-summary/1",
        "candidate_sha": expected_sha,
        "previous_source_sha": "0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978",
        "release_authority_sha": "2c54927463b46a96a9b0c0c5d1012636fb4f961e",
        "reviewer_findings_sha": "10193e2c904f99cfc23c97367f1e5d881b0630f2",
        "pre_git": pre_git,
        "post_git": post_git,
        "ports_before": ports_before,
        "ports_after": ports_after,
        "postgres_cluster": pg_postmaster,
        "external_author_runtime_root_unchanged": {
            "before": ext_before,
            "after": ext_after,
            "unchanged": ext_before == ext_after,
        },
        "gpu_or_model_imports_used": False,
        "pinned_digests": {
            "previous_worker_source_sha256": "01ad2fa1d6dcf8643ecb5801a934b37bae4630faca2f70959b4a85cc4480eb01",
            "new_worker_source_sha256": wp.compute_worker_source_sha256(),
            "model_manifest_sha256": wp.sha256_bytes((ROOT / "workers/local_ocr/manifests/model-files.json").read_bytes()),
            "dependency_lock_sha256": wp.sha256_bytes((ROOT / "workers/local_ocr/manifests/dependency-lock.json").read_bytes()),
            "worker_config_1p_sha256": wp.compute_config_digest(1),
            "worker_config_2p_sha256": wp.compute_config_digest(2),
            "worker_config_3p_sha256": wp.compute_config_digest(3),
        },
        "steps": steps,
    }
    (OUT_DIR / "summary.json").write_bytes((json.dumps(summary, indent=2) + "\n").encode("utf-8"))
    print("ALL 5 FOCUSED DECISIVE STEPS SUCCEEDED ON CLEAN FROZEN HEAD", expected_sha, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
