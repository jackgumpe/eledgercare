"""Read-only Stage E (/004 GPU trial) post-run verification and safe evidence packager.

Verifies worker PID absence without capturing agent CLI prompt transcripts,
executes read-only post-trial `q0.py host-precheck --stage during` and `q0.py status`,
inventories `C:\\Users\\jackg\\eLedgerCare-Q0\\WP-0005` and the untouched external run
`20261115T202627Z-eb5bf7da`, and copies safe text/JSON run evidence byte-for-byte
into `qualification/q0/harness/evidence/004-gpu-trial/9e73ef86/`.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKTREE = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness")
MAIN_REPO = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare")
HARNESS_DIR = WORKTREE / "qualification" / "q0" / "harness"
Q0_PY = HARNESS_DIR / "q0.py"
SCRATCH_DIR = WORKTREE / ".scratch" / "004-gpu-trial"
EVIDENCE_ROOT = HARNESS_DIR / "evidence" / "004-gpu-trial"
OUT_DIR = EVIDENCE_ROOT / "9e73ef86"

RUNTIME_ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")
RUN_ID = "20261115T202627Z-eb5bf7da"
RUN_DIR = RUNTIME_ROOT / "runs" / "author" / RUN_ID
EXECUTE_RELEASE = MAIN_REPO / "docs" / "coordination" / "WP-0005" / "releases" / "author-execute.json"
HOST_PYTHON = Path(r"C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe")

OBSERVED_PIDS = {
    "launcher_argsplit_pid": 29480,
    "supervisor_child_pid": 31816,
    "heartbeat_worker_pid": 30992,
}
LEASE_ID = "WP-0005-author-004-20261115T202152Z"
GPU_UUID = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"

FILE_ATTRIBUTE_REPARSE_POINT = 0x0400


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1_bytes(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def file_digests(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "git_blob_sha1": git_blob_sha1_bytes(raw),
    }


def is_reparse_point(path: Path) -> bool:
    attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    if attrs == -1:
        return False
    return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)


def check_worker_absence() -> dict[str, object]:
    """Query Win32_Process safely without recording unrelated CLI prompt strings."""
    ps_script = r"""
$targetPids = @(29480, 31816, 30992)
$procs = Get-CimInstance Win32_Process
$byPid = @{}
foreach ($tp in $targetPids) {
    $hit = $procs | Where-Object { $_.ProcessId -eq $tp } | Select-Object -First 1
    if ($null -eq $hit) {
        $byPid[[string]$tp] = @{ alive = $false }
    } else {
        $byPid[[string]$tp] = @{
            alive = $true
            name = $hit.Name
            executable_path = $hit.ExecutablePath
        }
    }
}
$pythonOrRuntime = @(
    $procs | Where-Object {
        $name = [string]$_.Name
        $exe = [string]$_.ExecutablePath
        $cmd = [string]$_.CommandLine
        ($name -match '^pythonw?(\.exe)?$') -or
        ($exe -like 'C:\Users\jackg\eLedgerCare-Q0\*') -or
        (($name -match '^python') -and ($cmd -like '*20261115T202627Z-eb5bf7da*' -or $cmd -like '*q0.py*'))
    } | ForEach-Object {
        @{
            pid = [int]$_.ProcessId
            parent_pid = [int]$_.ParentProcessId
            name = [string]$_.Name
            executable_path = [string]$_.ExecutablePath
            is_self = ([int]$_.ProcessId -eq $PID)
        }
    }
)
@{
    observed_pids = $byPid
    python_or_runtime_processes = $pythonOrRuntime
} | ConvertTo-Json -Depth 5
"""
    proc = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        text=True,
        check=True,
    )
    parsed = json.loads(proc.stdout)
    my_pid = os.getpid()
    external_python = [
        p for p in parsed["python_or_runtime_processes"] if int(p["pid"]) != my_pid
    ]
    pid_states = parsed["observed_pids"]
    all_target_absent = all(not v["alive"] for v in pid_states.values())
    return {
        "observed_utc": utc_now(),
        "packager_pid_excluded": my_pid,
        "target_worker_pids": {
            label: {
                "pid": pid_num,
                **pid_states[str(pid_num)],
            }
            for label, pid_num in OBSERVED_PIDS.items()
        },
        "other_python_or_runtime_root_processes": external_python,
        "all_owned_workers_absent": bool(all_target_absent and len(external_python) == 0),
    }


def run_readonly_checks() -> dict[str, object]:
    sys.path.insert(0, str(HARNESS_DIR))
    from q0harness.environment import build_stage_env  # type: ignore
    from q0harness.protocol import load_protocol  # type: ignore

    precheck_proc = subprocess.run(
        [str(HOST_PYTHON), "-s", "-P", str(Q0_PY), "host-precheck", "--stage", "during"],
        cwd=str(WORKTREE),
        capture_output=True,
        check=False,
    )
    stage_env = build_stage_env(
        dict(os.environ),
        root=RUNTIME_ROOT,
        protocol=load_protocol()[0],
        network=False,
    )
    status_proc = subprocess.run(
        [str(HOST_PYTHON), "-s", "-P", str(Q0_PY), "status"],
        cwd=str(WORKTREE),
        env=stage_env,
        capture_output=True,
        check=False,
    )
    return {
        "host_precheck": {
            "returncode": precheck_proc.returncode,
            "stdout": json.loads(precheck_proc.stdout.decode("utf-8")),
            "stderr": precheck_proc.stderr.decode("utf-8", errors="replace"),
        },
        "stage_offline_status": {
            "returncode": status_proc.returncode,
            "stdout": json.loads(status_proc.stdout.decode("utf-8")),
            "stderr": status_proc.stderr.decode("utf-8", errors="replace"),
        },
    }


def parse_gpu_observer_line(line: str) -> dict[str, object] | None:
    parts = [p.strip() for p in line.strip().split(",")]
    if len(parts) != 10:
        return None
    return {
        "timestamp_local": parts[0],
        "uuid": parts[1],
        "name": parts[2],
        "driver_version": parts[3],
        "compute_cap": parts[4],
        "memory_total_mib": int(parts[5]),
        "memory_used_mib": int(parts[6]),
        "memory_free_mib": int(parts[7]),
        "utilization_gpu_pct": int(parts[8]),
        "pstate": parts[9],
    }


def inventory_run_dir() -> dict[str, object]:
    files = []
    reparse_points = []
    max_path_len = len(str(RUN_DIR))
    total_bytes = 0
    for root, dirs, filenames in os.walk(RUN_DIR):
        root_p = Path(root)
        if is_reparse_point(root_p):
            reparse_points.append(str(root_p))
        for d in sorted(dirs):
            dp = root_p / d
            max_path_len = max(max_path_len, len(str(dp)))
            if is_reparse_point(dp):
                reparse_points.append(str(dp))
        for fn in sorted(filenames):
            fp = root_p / fn
            max_path_len = max(max_path_len, len(str(fp)))
            if is_reparse_point(fp):
                reparse_points.append(str(fp))
            rel = fp.relative_to(RUN_DIR).as_posix()
            info = file_digests(fp)
            total_bytes += int(info["bytes"])
            files.append({"relpath": rel, **info})

    sup = json.loads((RUN_DIR / "supervisor.json").read_text(encoding="utf-8"))
    gpu_trajectory = []
    for obs in sup.get("observers", []):
        if obs.get("index") == 0:
            obs_path = Path(obs["path"])
            parsed = parse_gpu_observer_line(obs_path.read_text(encoding="utf-8"))
            compute_path = obs_path.with_name(obs_path.name.replace("-0.txt", "-1.txt"))
            compute_lines = [
                ln.strip()
                for ln in compute_path.read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
            worker_30992_listed = any(ln.startswith("30992,") for ln in compute_lines)
            gpu_trajectory.append(
                {
                    "tag": obs["tag"],
                    "t": obs["t"],
                    "returncode": obs["returncode"],
                    "gpu": parsed,
                    "compute_apps_count": len(compute_lines),
                    "worker_pid_30992_in_compute_apps": worker_30992_listed,
                }
            )
    used_vals = [x["gpu"]["memory_used_mib"] for x in gpu_trajectory if x["gpu"]]
    util_vals = [x["gpu"]["utilization_gpu_pct"] for x in gpu_trajectory if x["gpu"]]
    return {
        "observed_utc": utc_now(),
        "run_id": RUN_ID,
        "run_dir": str(RUN_DIR),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "max_path_len": max_path_len,
        "reparse_points": reparse_points,
        "observer_summary": {
            "sample_pairs": len(gpu_trajectory),
            "min_memory_used_mib": min(used_vals),
            "max_memory_used_mib": max(used_vals),
            "max_utilization_gpu_pct": max(util_vals),
            "samples": gpu_trajectory,
        },
        "files": files,
    }


def inventory_runtime_root() -> dict[str, object]:
    subdirs = {}
    overall_files = 0
    overall_dirs = 0
    overall_bytes = 0
    overall_max_len = len(str(RUNTIME_ROOT))
    reparse_points = []
    if is_reparse_point(RUNTIME_ROOT):
        reparse_points.append(str(RUNTIME_ROOT))

    for child in sorted(RUNTIME_ROOT.iterdir(), key=lambda p: p.name):
        c_files = 0
        c_dirs = 0
        c_bytes = 0
        c_max = len(str(child))
        if is_reparse_point(child):
            reparse_points.append(str(child))
        if child.is_dir():
            for root, dirs, filenames in os.walk(child):
                rp = Path(root)
                for d in dirs:
                    c_dirs += 1
                    dp = rp / d
                    c_max = max(c_max, len(str(dp)))
                    if is_reparse_point(dp):
                        reparse_points.append(str(dp))
                for fn in filenames:
                    c_files += 1
                    fp = rp / fn
                    c_max = max(c_max, len(str(fp)))
                    if is_reparse_point(fp):
                        reparse_points.append(str(fp))
                    c_bytes += fp.stat().st_size
        else:
            c_files = 1
            c_bytes = child.stat().st_size
        subdirs[child.name] = {
            "files": c_files,
            "dirs": c_dirs,
            "bytes": c_bytes,
            "max_path_len": c_max,
        }
        overall_files += c_files
        overall_dirs += c_dirs + (1 if child.is_dir() else 0)
        overall_bytes += c_bytes
        overall_max_len = max(overall_max_len, c_max)

    disk = shutil.disk_usage(RUNTIME_ROOT)
    return {
        "observed_utc": utc_now(),
        "runtime_root": str(RUNTIME_ROOT),
        "total_files": overall_files,
        "total_dirs": overall_dirs,
        "total_bytes": overall_bytes,
        "max_path_len": overall_max_len,
        "max_path_under_240": overall_max_len < 240,
        "reparse_points": reparse_points,
        "volume_c": {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "above_during_floor_20gib": disk.free >= 21474836480,
        },
        "subdirectories": subdirs,
    }


def copy_exact(src: Path, dst: Path) -> dict[str, object]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    raw = src.read_bytes()
    dst.write_bytes(raw)
    assert dst.read_bytes() == raw
    return {
        "relpath": dst.relative_to(EVIDENCE_ROOT).as_posix(),
        "source": str(src),
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "git_blob_sha1": git_blob_sha1_bytes(raw),
    }


def write_json(dst: Path, payload: object) -> dict[str, object]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    dst.write_bytes(raw)
    return {
        "relpath": dst.relative_to(EVIDENCE_ROOT).as_posix(),
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "git_blob_sha1": git_blob_sha1_bytes(raw),
    }


def safety_scan_evidence_tree() -> None:
    forbidden_exts = {".safetensors", ".whl", ".bin", ".pt", ".pth", ".ckpt", ".pyc", ".pyd", ".dll"}
    forbidden_substrings = [
        b"<USER_REQUEST>",
        b"<CONTEXT_SUMMARY>",
        b"agy.exe",
        b"Authorization:",
        b"Set-Cookie:",
    ]
    hf_token_rx = re.compile(rb"\bhf_[A-Za-z0-9]{20,}\b")
    for path in sorted(EVIDENCE_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "package_stage_e_evidence.py":
            continue
        if path.suffix.lower() in forbidden_exts:
            raise RuntimeError(f"Forbidden binary/weight extension in evidence: {path}")
        raw = path.read_bytes()
        if len(raw) > 250_000:
            raise RuntimeError(f"Unexpectedly large file in evidence ({len(raw)} B): {path}")
        for pat in forbidden_substrings:
            if pat in raw:
                raise RuntimeError(f"Forbidden substring {pat!r} found in {path}")
        if hf_token_rx.search(raw):
            raise RuntimeError(f"Possible HF token pattern found in {path}")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    copied_records = []

    # 1. Copy preserved scratch execution records (excluding 05-lease-return-observation.json!)
    scratch_pairs = [
        ("01-host-precheck-before-execute.json", "01-host-precheck-before-execute.json"),
        ("02-execute-meta.json", "02-launcher-argsplit-meta.json"),
        ("02-execute-stderr.txt", "02-launcher-argsplit-stderr.txt"),
        ("03-execute-meta.json", "03-execute-meta.json"),
        ("03-execute-output.txt", "03-execute-stdout.txt"),
        ("04-host-precheck-after-execute.json", "04-host-precheck-after-execute.json"),
    ]
    for src_name, dst_name in scratch_pairs:
        copied_records.append(copy_exact(SCRATCH_DIR / src_name, OUT_DIR / dst_name))

    # 2. Clean worker absence + post-trial host/stage checks + lease return receipt
    worker_check = check_worker_absence()
    if not worker_check["all_owned_workers_absent"]:
        raise RuntimeError(f"Owned worker still alive: {worker_check}")
    post_checks = run_readonly_checks()
    if post_checks["host_precheck"]["returncode"] != 0 or post_checks["stage_offline_status"]["returncode"] != 0:
        raise RuntimeError("Post-trial read-only check failed")

    lease_return = {
        "schema": "eldq0-lease-return/1",
        "lease_id": LEASE_ID,
        "gpu_uuid": GPU_UUID,
        "owner": "eld-q0-harness",
        "author_session": "bd92ddc3-af60-4096-b683-65386d81b718",
        "executing_head": "9e73ef86600b5e16f74b056676a6d3a4f1474058",
        "accepted_source_candidate": "41d6204648e4115ab197507d1a22f6d5c7f3e784",
        "execute_release_file": str(EXECUTE_RELEASE),
        "execute_release_digests": file_digests(EXECUTE_RELEASE),
        "run_id": RUN_ID,
        "lease_status": "RETURNED",
        "worker_absence": worker_check,
        "fresh_post_trial_checks": post_checks,
    }
    copied_records.append(write_json(OUT_DIR / "05-lease-return-verification.json", lease_return))

    # 3. Complete untouched external run directory inventory + Runtime root inventory
    run_inv = inventory_run_dir()
    copied_records.append(write_json(OUT_DIR / "06-run-dir-inventory.json", run_inv))

    root_inv = inventory_runtime_root()
    copied_records.append(write_json(OUT_DIR / "07-runtime-root-inventory.json", root_inv))

    # 4. Byte-identical copies of safe run-root & evidence/* files (no hf-modules/.pyc)
    run_copy_root = OUT_DIR / f"run-{RUN_ID}"
    run_top_files = [
        "supervisor.json",
        "heartbeat.json",
        "parent-context.json",
        "child.stdout.txt",
        "child.stderr.txt",
        "observer-pre-0.txt",
        "observer-pre-1.txt",
        "observer-during-1207-0.txt",
        "observer-during-1207-1.txt",
        "observer-post-0.txt",
        "observer-post-1.txt",
    ]
    for rel in run_top_files:
        copied_records.append(copy_exact(RUN_DIR / rel, run_copy_root / rel))

    for ev_file in sorted((RUN_DIR / "evidence").iterdir(), key=lambda p: p.name):
        if ev_file.is_file():
            copied_records.append(copy_exact(ev_file, run_copy_root / "evidence" / ev_file.name))

    manifest = {
        "schema": "eldq0-stage-e-evidence-manifest/1",
        "generated_utc": utc_now(),
        "executing_head": "9e73ef86600b5e16f74b056676a6d3a4f1474058",
        "accepted_source_candidate": "41d6204648e4115ab197507d1a22f6d5c7f3e784",
        "run_id": RUN_ID,
        "packager_script": file_digests(Path(__file__)),
        "packaged_files": copied_records,
    }
    write_json(OUT_DIR / "manifest.json", manifest)

    safety_scan_evidence_tree()
    print(
        json.dumps(
            {
                "status": "ok",
                "all_owned_workers_absent": worker_check["all_owned_workers_absent"],
                "packaged_files_count": len(copied_records) + 1,
                "external_run_files": run_inv["file_count"],
                "external_run_bytes": run_inv["total_bytes"],
                "runtime_root_files": root_inv["total_files"],
                "runtime_root_bytes": root_inv["total_bytes"],
                "runtime_root_max_path_len": root_inv["max_path_len"],
                "volume_c_free_bytes": root_inv["volume_c"]["free_bytes"],
                "observer_max_memory_used_mib": run_inv["observer_summary"]["max_memory_used_mib"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
