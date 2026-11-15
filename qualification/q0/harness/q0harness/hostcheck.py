"""Read-only host preconditions (Q0R-05, Q0R-07) and GPU observer validation.

Everything here only reads: file presence/digests in System32, two registry values, memory
counters, volume free space, and read-only nvidia-smi queries (no CUDA context, no
allocation). Nothing is repaired or configured; a failing precondition stops the stage.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .environment import resolve_host_git
from .hashing import file_digests
from .outcome import Q0Failure

MSVC_DLLS = ("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll")
FS_KEY = r"SYSTEM\CurrentControlSet\Control\FileSystem"
MM_KEY = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
LEGACY_MAX_PATH = 260
PATH_MARGIN = 20  # stop below MAX_PATH with margin for tool-created suffixes


def _utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def file_version(path: Path) -> str | None:
    if sys.platform != "win32":
        return None
    ver = ctypes.WinDLL("version")
    size = ver.GetFileVersionInfoSizeW(str(path), None)
    if not size:
        return None
    buf = ctypes.create_string_buffer(size)
    if not ver.GetFileVersionInfoW(str(path), 0, size, buf):
        return None
    ptr, n = ctypes.c_void_p(), ctypes.c_uint()
    if not ver.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(n)) or n.value < 52:
        return None
    words = (ctypes.c_uint32 * 13).from_address(ptr.value)
    ms, ls = words[2], words[3]
    return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"


def msvc_runtime(system32: Path) -> list[dict]:
    rows = []
    for name in MSVC_DLLS:
        p = Path(system32) / name
        row = {"dll": name, "present": p.is_file()}
        if row["present"]:
            d = file_digests(p, git_blob=False)
            row.update(size=d["size"], sha256=d["sha256"], file_version=file_version(p))
        rows.append(row)
    return rows


def read_registry(key: str, value: str):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key, 0, winreg.KEY_READ) as k:
            v, t = winreg.QueryValueEx(k, value)
            return {"value": v, "type": t}
    except FileNotFoundError:
        return None


class _MEMSTATUS(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def memory_status() -> dict:
    m = _MEMSTATUS()
    m.dwLength = ctypes.sizeof(m)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
        raise Q0Failure("TELEMETRY_UNSUPPORTED", "GlobalMemoryStatusEx failed")
    return {"total_phys": m.ullTotalPhys, "avail_phys": m.ullAvailPhys,
            "commit_limit": m.ullTotalPageFile, "commit_available": m.ullAvailPageFile,
            "note": "commit_limit = physical RAM + current pagefile size; pagefile growth outside the task root is NOT bounded by the task budget"}


def free_space(path: Path) -> dict:
    anchor = Path(path).anchor or str(path)
    du = shutil.disk_usage(anchor)
    return {"volume": anchor, "free_bytes": du.free, "total_bytes": du.total, "observed_utc": _utc()}


def known_max_path(protocol: dict, manifest: dict) -> dict:
    """Longest path the harness itself will create/read under the root (venv paths are
    checked separately after installation with max_path_under)."""
    root = protocol["storage"]["root"]
    leaf = protocol["storage"]["subdirs"]["models"]
    longest_file = max((f["path"] for f in manifest["files"]), key=len)
    run_id = "20261115T000000Z-0123abcd"
    cands = {
        "model_file": os.path.join(root, leaf, longest_file),
        "module_cache_file": os.path.join(root, "runs", "reviewer", run_id, "hf-modules", "transformers_modules",
                                          os.path.basename(leaf), "sparse_gather_e2e_triton.py"),
        "evidence_file": os.path.join(root, "runs", "reviewer", run_id, "evidence", "F07.warm2.observation.json"),
    }
    return {"paths": {k: len(v) for k, v in cands.items()}, "max_len": max(len(v) for v in cands.values())}


def max_path_under(directory: Path) -> dict:
    longest, n = "", 0
    for dirpath, _, files in os.walk(directory):
        for f in files:
            p = os.path.join(dirpath, f)
            n += 1
            if len(p) > len(longest):
                longest = p
    return {"files": n, "max_len": len(longest), "longest": longest}


def run_observer(cmd: list[str], timeout_s: int = 30, cap: int = 65536) -> dict:
    t = _utc()
    try:
        cp = subprocess.run(cmd, capture_output=True, timeout=timeout_s)
        out, err, rc = cp.stdout[:cap], cp.stderr[:4096], cp.returncode
    except (OSError, subprocess.TimeoutExpired) as e:
        out, err, rc = b"", repr(e).encode(), None
    return {"argv": cmd, "returncode": rc, "observed_utc": t, "stdout": out.decode("utf-8", "replace"),
            "stderr": err.decode("utf-8", "replace")}


def validate_gpu_observation(rows: list[dict], protocol: dict) -> list[str]:
    """Check that the frozen observer commands work on this host and identify the leased GPU."""
    problems = []
    gpu_q, apps_q = rows
    if gpu_q["returncode"] != 0:
        problems.append("gpu query failed")
    else:
        lines = [l for l in gpu_q["stdout"].splitlines() if l.strip()]
        fields = [x.strip() for x in lines[0].split(",")] if len(lines) == 1 else []
        names = protocol["gpu"]["observer"]["gpu_fields"]
        if len(fields) != len(names):
            problems.append(f"gpu query returned {len(lines)} lines / {len(fields)} fields")
        else:
            rec = dict(zip(names, fields))
            if rec.get("uuid") != protocol["gpu"]["uuid"]:
                problems.append("gpu uuid differs")
            if protocol["gpu"]["name_contains"] not in rec.get("name", ""):
                problems.append("gpu name differs")
            if rec.get("compute_cap") != "12.0":
                problems.append("compute capability differs")
    if apps_q["returncode"] != 0:
        problems.append("compute-apps query failed")
    return problems


def host_precheck(protocol: dict, manifest: dict, *, stage: str, system32: Path | None = None,
                  registry=read_registry, observe=run_observer, git_resolver=resolve_host_git) -> dict:
    """stage: 'initial' (before any download; initial free-space floor) or 'during'."""
    system32 = Path(system32 or (Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"))
    floors = protocol["storage"]["free_space"]
    try:
        git_exe = git_resolver()
        git_rec = {"present": True, "executable": git_exe}
    except Q0Failure as exc:
        git_rec = {"present": False, "executable": None, "detail": exc.detail}
    rec = {"schema": "eldq0-host-precheck/1", "stage": stage, "started_utc": _utc(),
           "python": sys.version, "executable": sys.executable,
           "git_runtime": git_rec,
           "msvc_runtime": msvc_runtime(system32),
           "long_paths_enabled": registry(FS_KEY, "LongPathsEnabled"),
           "paging_files": registry(MM_KEY, "PagingFiles"),
           "memory": memory_status(),
           "free_space": free_space(Path(protocol["storage"]["root"])),
           "storage_root_exists": Path(protocol["storage"]["root"]).exists(),
           "known_paths": known_max_path(protocol, manifest),
           "gpu_observer": [observe(cmd) for cmd in protocol["gpu"]["observer"]["commands"]]}
    fails = []
    if not git_rec["present"]:
        fails.append(Q0Failure("HOST_PRECHECK_FAILED", "Git executable unavailable on host", git_rec).as_record())
    missing = [r["dll"] for r in rec["msvc_runtime"] if not r["present"]]
    if missing:
        fails.append(Q0Failure("HOST_PRECHECK_FAILED", "MSVC runtime DLLs absent from System32", missing).as_record())
    lpe = (rec["long_paths_enabled"] or {}).get("value")
    if lpe != 1 and rec["known_paths"]["max_len"] >= LEGACY_MAX_PATH - PATH_MARGIN:
        fails.append(Q0Failure("HOST_PRECHECK_FAILED", "long paths disabled and intended paths near MAX_PATH",
                               rec["known_paths"]).as_record())
    floor = floors["initial_min_bytes"] if stage == "initial" else floors["during_min_bytes"]
    if rec["free_space"]["free_bytes"] < floor:
        fails.append(Q0Failure("STORAGE_FLOOR", f"free {rec['free_space']['free_bytes']} < {stage} floor {floor}").as_record())
    gp = validate_gpu_observation(rec["gpu_observer"], protocol)
    if gp:
        fails.append(Q0Failure("HOST_PRECHECK_FAILED", "GPU observer commands invalid on this host", gp).as_record())
    rec["limits"] = ["DLL presence/version does not prove successful torch DLL resolution (later import gate).",
                     "Pagefile growth and OS/driver allocations outside the root are not bounded by the task budget.",
                     "nvidia-smi per-process used_memory is [N/A] under WDDM; per-process VRAM is unsupported telemetry.",
                     "No CUDA context is created; this is not GPU ownership or runtime qualification."]
    rec["failures"] = fails
    rec["status"] = "pass" if not fails else "fail"
    rec["finished_utc"] = _utc()
    return rec
