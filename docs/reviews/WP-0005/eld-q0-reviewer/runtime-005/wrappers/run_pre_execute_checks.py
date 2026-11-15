"""WP-0005 /005 pre-execution verification runner using accepted q0.py commands.

Runs from ignored .scratch/005-runtime/ so reviewer HEAD c8daa97c5be6bc67931b215652a7a0f6ced621ef
remains completely clean throughout pre-execution checks and the single GPU trial.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REVIEWER_WT = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-reviewer-carbon")
HARNESS_DIR = REVIEWER_WT / "qualification" / "q0" / "harness"
Q0_PY = HARNESS_DIR / "q0.py"
MAIN_REPO = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare")
REVIEWER_INSTALL = MAIN_REPO / "docs" / "coordination" / "WP-0005" / "releases" / "reviewer-install.json"
REVIEWER_EXECUTE = MAIN_REPO / "docs" / "coordination" / "WP-0005" / "releases" / "reviewer-execute.json"

TASK_ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")
VENV_PY = TASK_ROOT / "venv" / "Scripts" / "python.exe"
WHEELHOUSE = TASK_ROOT / "wheelhouse"
MODEL_DIR = TASK_ROOT / "models" / "Unlimited_OCR_2_04809669"
NOTICE_DIR = TASK_ROOT / "notices" / "Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"
HOST_PY = Path(sys.executable)

OUT_DIR = Path(__file__).resolve().parent / "pre-execute"

sys.path.insert(0, str(HARNESS_DIR))
from q0harness.environment import build_stage_env  # noqa: E402
from q0harness.protocol import load_protocol  # noqa: E402
from q0harness.release import code_identity, validate_release  # noqa: E402
from q0harness import locks  # noqa: E402
from q0harness.hashing import sha256_bytes  # noqa: E402

_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def sha256_b(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_step(name: str, argv: list[str], *, env: dict, cwd: Path, out_file: str) -> dict:
    t0 = datetime.now(timezone.utc)
    cp = subprocess.run(
        argv,
        cwd=str(cwd),
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=300,
    )
    t1 = datetime.now(timezone.utc)
    fp = OUT_DIR / out_file
    fp.write_bytes(cp.stdout)
    if cp.stderr:
        (OUT_DIR / (out_file + ".stderr")).write_bytes(cp.stderr)
    if cp.returncode != 0:
        raise RuntimeError(
            f"Step {name} failed with exit_code={cp.returncode}:\n"
            f"STDOUT:\n{cp.stdout.decode('utf-8', errors='replace')}\n"
            f"STDERR:\n{cp.stderr.decode('utf-8', errors='replace')}"
        )
    return {
        "step": name,
        "argv": argv,
        "cwd": str(cwd),
        "started_utc": t0.isoformat(),
        "finished_utc": t1.isoformat(),
        "seconds": round((t1 - t0).total_seconds(), 3),
        "exit_code": cp.returncode,
        "output_file": out_file,
        "output_bytes": len(cp.stdout),
        "output_sha256": sha256_b(cp.stdout),
        "stderr_bytes": len(cp.stderr),
    }


def inspect_venv_paths(venv_root: Path) -> dict:
    file_count = 0
    total_bytes = 0
    max_len = 0
    max_path = ""
    over_240 = []
    reparse_points = []
    for dirpath, dirnames, filenames in os.walk(venv_root, followlinks=False):
        for dn in dirnames:
            dp = Path(dirpath) / dn
            st = os.lstat(dp)
            if stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & _REPARSE):
                reparse_points.append(str(dp))
        for fn in filenames:
            fp = Path(dirpath) / fn
            s = str(fp)
            st = os.lstat(fp)
            if stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & _REPARSE):
                reparse_points.append(s)
            file_count += 1
            total_bytes += st.st_size
            if len(s) > max_len:
                max_len = len(s)
                max_path = s
            if len(s) >= 240:
                over_240.append(s)
    return {
        "venv_root": str(venv_root),
        "file_count": file_count,
        "total_bytes": total_bytes,
        "max_path_len": max_len,
        "max_path_example": max_path,
        "paths_ge_240": over_240,
        "reparse_points": reparse_points,
    }


def query_python_q0_processes_and_gpu() -> dict:
    ps_cmd = (
        "$myPid = $PID; "
        "$procs = Get-CimInstance Win32_Process -Filter \"Name = 'python.exe' OR Name = 'pythonw.exe'\" | "
        "Select-Object ProcessId, ParentProcessId, Name, ExecutablePath, CommandLine; "
        "ConvertTo-Json -InputObject @($procs) -Compress"
    )
    cp_p = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    all_py = json.loads(cp_p.stdout or "[]")
    if isinstance(all_py, dict):
        all_py = [all_py]
    self_pid = os.getpid()
    q0_children = [
        p for p in all_py
        if p.get("ProcessId") != self_pid
        and (
            "q0.py" in (p.get("CommandLine") or "")
            or "eLedgerCare-Q0\\WP-0005" in (p.get("CommandLine") or "")
            or "eLedgerCare-Q0\\WP-0005" in (p.get("ExecutablePath") or "")
        )
    ]
    prior_author_pids_present = [
        p["ProcessId"] for p in all_py if p.get("ProcessId") in (30992, 31816)
    ]
    gpu_q = subprocess.run(
        ["nvidia-smi", "--id=GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d",
         "--query-gpu=timestamp,uuid,name,driver_version,compute_cap,memory.total,memory.used,memory.free,utilization.gpu,pstate",
         "--format=csv,noheader,nounits"],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, check=True,
    ).stdout.strip()
    gpu_apps = subprocess.run(
        ["nvidia-smi", "--id=GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d",
         "--query-compute-apps=pid,process_name,used_gpu_memory",
         "--format=csv,noheader,nounits"],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, check=True,
    ).stdout.strip()
    return {
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "observer_python_pid": self_pid,
        "prior_author_pids_checked": [30992, 31816],
        "prior_author_pids_present": prior_author_pids_present,
        "active_q0_worker_processes": q0_children,
        "nvidia_smi_gpu": gpu_q,
        "nvidia_smi_compute_apps": gpu_apps.splitlines() if gpu_apps else [],
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outside_cwd = Path(__file__).resolve().parent / "cwd"
    outside_cwd.mkdir(parents=True, exist_ok=True)

    # 0. Pure-validate both reviewer-install.json and reviewer-execute.json against clean HEAD c8daa97c...
    protocol, p_sha = load_protocol()
    lock_raw = (HARNESS_DIR / "locks" / "dependency-lock.json").read_bytes()
    lock_sha = sha256_bytes(lock_raw)
    lock = json.loads(lock_raw)
    pkgs = locks.validate_lock(lock, locks.git_blob_reader(REVIEWER_WT))
    code = code_identity(REVIEWER_WT)
    assert code["head"] == "c8daa97c5be6bc67931b215652a7a0f6ced621ef", f"Unexpected HEAD: {code}"
    assert code["harness_clean"] is True, f"Harness dirty: {code}"

    rel_inst = json.loads(REVIEWER_INSTALL.read_text(encoding="utf-8"))
    rel_exec = json.loads(REVIEWER_EXECUTE.read_text(encoding="utf-8"))
    locks.require_installable(pkgs, rel_inst)
    locks.require_installable(pkgs, rel_exec)
    v_inst = validate_release(rel_inst, stage="install", owner=None, protocol=protocol,
                              protocol_sha256=p_sha, lock_sha256=lock_sha, root=TASK_ROOT, code=code)
    v_exec = validate_release(rel_exec, stage="execute", owner="reviewer", protocol=protocol,
                              protocol_sha256=p_sha, lock_sha256=lock_sha, root=TASK_ROOT, code=code)
    assert v_exec["lease_id"] == "WP-0005-reviewer-005-20261115T205527Z"

    stage_offline_env = build_stage_env(os.environ, root=TASK_ROOT, protocol=protocol, network=False)
    host_env = dict(os.environ)

    steps = []
    # 1. host-precheck --stage during (normal operator environment)
    steps.append(run_step(
        "01-host-precheck-during",
        [str(HOST_PY), "-I", "-B", str(Q0_PY), "host-precheck", "--stage", "during"],
        env=host_env, cwd=outside_cwd, out_file="01-host-precheck-during.json",
    ))

    # 2. verify-wheelhouse under stage_offline
    steps.append(run_step(
        "02-verify-wheelhouse",
        [str(VENV_PY), "-s", "-B", "-P", "-X", "utf8", str(Q0_PY),
         "verify-wheelhouse", str(WHEELHOUSE), "--release", str(REVIEWER_INSTALL)],
        env=stage_offline_env, cwd=outside_cwd, out_file="02-verify-wheelhouse.json",
    ))

    # 3. pip check + pip list + venv path/reparse check
    cp_pip_chk = subprocess.run(
        [str(VENV_PY), "-s", "-m", "pip", "check"],
        cwd=str(outside_cwd), env=stage_offline_env,
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60, check=True,
    )
    cp_pip_lst = subprocess.run(
        [str(VENV_PY), "-s", "-m", "pip", "list", "--format=json"],
        cwd=str(outside_cwd), env=stage_offline_env,
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60, check=True,
    )
    pip_list = json.loads(cp_pip_lst.stdout)
    venv_inv = inspect_venv_paths(TASK_ROOT / "venv")
    assert venv_inv["paths_ge_240"] == [], f"Paths >= 240: {venv_inv['paths_ge_240']}"
    assert venv_inv["reparse_points"] == [], f"Reparse points: {venv_inv['reparse_points']}"
    assert len(pip_list) == 33, f"Expected 33 dists (32 locked + pip), got {len(pip_list)}"
    pip_blob = (json.dumps({
        "pip_check_exit_code": cp_pip_chk.returncode,
        "pip_check_stdout": cp_pip_chk.stdout.strip(),
        "installed_count": len(pip_list),
        "installed_distributions": pip_list,
        "venv_path_and_reparse_audit": venv_inv,
    }, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (OUT_DIR / "03-pip-check-and-venv-inventory.json").write_bytes(pip_blob)
    steps.append({
        "step": "03-pip-check-and-venv-inventory",
        "exit_code": 0,
        "output_file": "03-pip-check-and-venv-inventory.json",
        "output_bytes": len(pip_blob),
        "output_sha256": sha256_b(pip_blob),
    })

    # 4. verify-model (18 runtime objects + notice + static source safety)
    steps.append(run_step(
        "04-verify-model-before",
        [str(VENV_PY), "-s", "-B", "-P", "-X", "utf8", str(Q0_PY),
         "verify-model", str(MODEL_DIR), "--notices", str(NOTICE_DIR)],
        env=stage_offline_env, cwd=outside_cwd, out_file="04-verify-model-before.json",
    ))

    # 5. preflight-cpu (installed set, forbidden backends absent via find_spec, real pypdfium2 4-page render, model+notice)
    steps.append(run_step(
        "05-preflight-cpu",
        [str(VENV_PY), "-s", "-B", "-P", "-X", "utf8", str(Q0_PY),
         "preflight-cpu", "--release", str(REVIEWER_INSTALL),
         "--model-dir", str(MODEL_DIR), "--notices", str(NOTICE_DIR)],
        env=stage_offline_env, cwd=outside_cwd, out_file="05-preflight-cpu.json",
    ))

    # 6. Pre-GPU process + VRAM baseline immediately before launching q0.py execute --owner reviewer
    pre_gpu = query_python_q0_processes_and_gpu()
    assert pre_gpu["prior_author_pids_present"] == [], f"Author PIDs still alive: {pre_gpu}"
    assert pre_gpu["active_q0_worker_processes"] == [], f"Active Q0 workers found: {pre_gpu}"
    pre_gpu_blob = (json.dumps(pre_gpu, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (OUT_DIR / "06-pre-gpu-process-and-vram.json").write_bytes(pre_gpu_blob)
    steps.append({
        "step": "06-pre-gpu-process-and-vram",
        "exit_code": 0,
        "output_file": "06-pre-gpu-process-and-vram.json",
        "output_bytes": len(pre_gpu_blob),
        "output_sha256": sha256_b(pre_gpu_blob),
    })

    code_after = code_identity(REVIEWER_WT)
    assert code_after == code, f"Code identity drifted: {code_after} != {code}"

    summary = {
        "schema": "eld-q0-reviewer-005-pre-execute/1",
        "code_identity": code_after,
        "validated_install_release": v_inst,
        "validated_execute_release": v_exec,
        "venv_summary": {
            "installed_count": len(pip_list),
            "file_count": venv_inv["file_count"],
            "total_bytes": venv_inv["total_bytes"],
            "max_path_len": venv_inv["max_path_len"],
            "reparse_points": len(venv_inv["reparse_points"]),
        },
        "pre_gpu_baseline": pre_gpu,
        "steps": steps,
    }
    (OUT_DIR / "pre-execute-summary.json").write_bytes(
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
