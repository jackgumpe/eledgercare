"""Environment isolation audit, Win32 process creation FILETIME, disk checks, and heartbeat."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
import os
import re
import shutil
import stat
import threading
import time
from pathlib import Path

from .protocol import MAX_RUNTIME_ROOT_BYTES, MIN_FREE_DISK_BYTES, WorkerError

_REPARSE_ATTR = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
MAX_STORAGE_SCAN_DEPTH = 32
MAX_STORAGE_SCAN_ENTRIES = 100_000

FORBIDDEN_EXACT = {
    "TIME_DIAG", "TIME_DIAG_INTERVAL", "WARMUP_MAIN_LOCAL_WINDOW", "PAGE_SCOPE_PREFILL",
    "CODE_STAMP_LOG", "INDEXER_SCORE_TRITON", "FUSED_CHUNK_CE", "CE_CHUNK_SIZE",
    "KL_QUERY_STRIDE", "KL_CHUNK_RECOMPUTE", "PYTORCH_CUDA_ALLOC_CONF",
    "CUBLAS_WORKSPACE_CONFIG", "CUDA_LAUNCH_BLOCKING", "HF_ENDPOINT",
    "PYTHONPATH", "PYTHONSTARTUP", "PYTHONHOME", "PYTHONUSERBASE",
    "PYTHONINSPECT", "PYTHONBREAKPOINT", "ELEDGERCARE_MIGRATION_CONNECTION",
}

FORBIDDEN_PATTERNS = (
    re.compile(r"^DASH_"),
    re.compile(r"^KL_"),
    re.compile(r"^SGLANG_"),
    re.compile(r"^TORCHDYNAMO_"),
    re.compile(r"^TORCH_COMPILE"),
    re.compile(r"^CONNECTIONSTRINGS", re.I),
    re.compile(r"PGPASSWORD", re.I),
    re.compile(r"TOKEN", re.I),
    re.compile(r"SECRET", re.I),
    re.compile(r"PASSWORD", re.I),
    re.compile(r"API_?KEY", re.I),
    re.compile(r"CREDENTIAL", re.I),
    re.compile(r"^AWS_"),
    re.compile(r"^AZURE_"),
    re.compile(r"^ANTHROPIC"),
    re.compile(r"^OPENAI"),
    re.compile(r"^GH_|^GITHUB_"),
)

REQUIRED_RUN_LOCAL_VARS = (
    "TEMP", "TMP", "TMPDIR", "USERPROFILE", "HOME",
    "HF_HOME", "HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE", "TRANSFORMERS_CACHE",
    "HF_MODULES_CACHE", "TORCH_HOME", "TRITON_CACHE_DIR",
    "TORCHINDUCTOR_CACHE_DIR", "CUDA_CACHE_PATH", "XDG_CACHE_HOME",
    "PIP_CACHE_DIR", "UV_CACHE_DIR",
)


def _norm(p: str | os.PathLike) -> str:
    return os.path.normcase(os.path.abspath(str(p))).rstrip("\\/")


def is_inside(child: str | os.PathLike, parent: str | os.PathLike) -> bool:
    c, pa = _norm(child), _norm(parent)
    return c == pa or c.startswith(pa + os.sep)


def current_process_create_filetime() -> int:
    """Return the exact 64-bit Win32 CreationTime FILETIME (100ns ticks since 1601-01-01 UTC)."""
    if os.name != "nt":
        return int(time.time() * 10_000_000)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_current = kernel32.GetCurrentProcess
    get_current.restype = wintypes.HANDLE
    get_times = kernel32.GetProcessTimes
    get_times.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    get_times.restype = wintypes.BOOL
    creation = wintypes.FILETIME()
    exit_t = wintypes.FILETIME()
    kernel_t = wintypes.FILETIME()
    user_t = wintypes.FILETIME()
    if not get_times(get_current(), ctypes.byref(creation), ctypes.byref(exit_t),
                     ctypes.byref(kernel_t), ctypes.byref(user_t)):
        raise OSError(ctypes.get_last_error(), "GetProcessTimes failed")
    return (int(creation.dwHighDateTime) << 32) | int(creation.dwLowDateTime)


def audit_worker_environment(
    environ: dict[str, str],
    *,
    run_dir: Path,
    readonly_q0_root: Path,
    leased_gpu_uuid: str,
) -> None:
    violations = [
        k for k in environ
        if k in FORBIDDEN_EXACT or any(rx.search(k) for rx in FORBIDDEN_PATTERNS)
    ]
    if violations:
        raise WorkerError(
            "environment_isolation_failed",
            f"Forbidden variables present in worker environment: {', '.join(sorted(violations))}",
        )
    if environ.get("HF_HUB_OFFLINE") != "1" or environ.get("TRANSFORMERS_OFFLINE") != "1":
        raise WorkerError("environment_isolation_failed", "Offline Hugging Face flags are missing.")
    if environ.get("HF_HUB_DISABLE_XET") != "1" or environ.get("PIP_NO_INDEX") != "1":
        raise WorkerError("environment_isolation_failed", "Offline XET/pip flags are missing.")
    if environ.get("CUDA_DEVICE_ORDER") != "PCI_BUS_ID":
        raise WorkerError("environment_isolation_failed", "CUDA_DEVICE_ORDER must be PCI_BUS_ID.")
    if environ.get("CUDA_VISIBLE_DEVICES") != leased_gpu_uuid:
        raise WorkerError("environment_isolation_failed", "CUDA_VISIBLE_DEVICES does not match leased GPU UUID.")

    cache_root = run_dir / "cache"
    for var in REQUIRED_RUN_LOCAL_VARS:
        val = environ.get(var)
        if not val or not is_inside(val, cache_root):
            raise WorkerError(
                "environment_isolation_failed",
                f"Environment variable {var} is missing or outside owned attempt cache directory.",
            )
        if is_inside(val, readonly_q0_root):
            raise WorkerError(
                "environment_isolation_failed",
                f"Writable cache variable {var} points inside read-only Q0 root.",
            )


def _is_link_or_reparse_stat(st: os.stat_result) -> bool:
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & _REPARSE_ATTR)


def directory_size_bytes(root: Path) -> int:
    """Bounded, reparse-aware directory byte accounting tolerant of transient deletions only."""
    if not root.exists():
        return 0
    root_st = os.lstat(root)
    if _is_link_or_reparse_stat(root_st):
        raise WorkerError("storage_limit_exceeded", "Writable runtime root must not be a symlink or reparse point.")

    total = 0
    inspected = 0
    stack: list[tuple[Path, int]] = [(root, 0)]

    while stack:
        cur_dir, depth = stack.pop()
        if depth > MAX_STORAGE_SCAN_DEPTH:
            raise WorkerError("storage_limit_exceeded", "Runtime directory nesting exceeded bounded scan depth.")

        entries = None
        prev_ctime = None
        for attempt in range(5):
            try:
                with os.scandir(cur_dir) as it:
                    entries = list(it)
                break
            except FileNotFoundError:
                entries = None
                break
            except OSError as exc:
                try:
                    cur_st = os.lstat(cur_dir)
                except FileNotFoundError:
                    entries = None
                    break
                except OSError:
                    if attempt == 4:
                        raise WorkerError(
                            "storage_limit_exceeded",
                            f"Unable to inspect runtime directory safely ({type(exc).__name__}).",
                        ) from exc
                    time.sleep(0.002 * (attempt + 1))
                    continue

                if prev_ctime is not None and cur_st.st_ctime_ns == prev_ctime and attempt >= 2:
                    raise WorkerError(
                        "storage_limit_exceeded",
                        f"Persistent permission or I/O error inspecting runtime directory ({type(exc).__name__}).",
                    ) from exc
                prev_ctime = cur_st.st_ctime_ns
                time.sleep(0.002 * (attempt + 1))

        if entries is None:
            continue

        for entry in entries:
            inspected += 1
            if inspected > MAX_STORAGE_SCAN_ENTRIES:
                raise WorkerError("storage_limit_exceeded", "Runtime directory entry count exceeded bounded scan limit.")
            try:
                st = entry.stat(follow_symlinks=False)
            except FileNotFoundError:
                continue
            except OSError as exc:
                time.sleep(0.002)
                if not os.path.lexists(entry.path):
                    continue
                raise WorkerError(
                    "storage_limit_exceeded",
                    f"Unable to stat runtime entry safely ({type(exc).__name__}).",
                ) from exc

            if _is_link_or_reparse_stat(st):
                raise WorkerError(
                    "storage_limit_exceeded",
                    "Symlink or reparse point detected inside writable runtime directory.",
                )
            if stat.S_ISDIR(st.st_mode):
                stack.append((Path(entry.path), depth + 1))
            elif stat.S_ISREG(st.st_mode):
                total += int(st.st_size)

    return total


def verify_storage_guards(
    writable_runtime_root: Path,
    *,
    min_free_bytes: int = MIN_FREE_DISK_BYTES,
    max_root_bytes: int = MAX_RUNTIME_ROOT_BYTES,
    disk_usage_fn=shutil.disk_usage,
) -> dict:
    usage = disk_usage_fn(str(writable_runtime_root))
    if usage.free < min_free_bytes:
        raise WorkerError(
            "storage_limit_exceeded",
            f"Free disk space {usage.free} bytes is below floor {min_free_bytes} bytes.",
        )
    used = directory_size_bytes(writable_runtime_root)
    if used > max_root_bytes:
        raise WorkerError(
            "storage_limit_exceeded",
            f"Runtime root usage {used} bytes exceeds ceiling {max_root_bytes} bytes.",
        )
    return {"free_disk_bytes": usage.free, "runtime_root_used_bytes": used}


class WorkerHeartbeat:
    """Atomically writes worker identity, phase, and forward-progress counter for .NET supervision."""

    def __init__(
        self,
        path: Path,
        *,
        attempt_id: str,
        fencing_token: int,
        interval_s: float,
        progress_fn,
    ):
        self.path = Path(path)
        self.attempt_id = attempt_id
        self.fencing_token = fencing_token
        self.interval_s = interval_s
        self.progress_fn = progress_fn
        self.worker_pid = os.getpid()
        self.parent_pid = os.getppid()
        self.worker_create_filetime = current_process_create_filetime()
        self.phase = "starting"
        self.phase_timeout_s: int | None = 1800
        self.stall_monitored = False
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="f2-worker-heartbeat", daemon=True)

    def set_phase(self, phase: str, timeout_s: int | None, *, stall_monitored: bool = False) -> None:
        with self._lock:
            self.phase = phase
            self.phase_timeout_s = timeout_s
            self.stall_monitored = stall_monitored
            self._write_locked()

    def beat(self) -> None:
        with self._lock:
            self._write_locked()

    def _write_locked(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        payload = {
            "attempt_id": self.attempt_id,
            "fencing_token": self.fencing_token,
            "worker_pid": self.worker_pid,
            "worker_create_filetime": self.worker_create_filetime,
            "parent_pid": self.parent_pid,
            "phase": self.phase,
            "phase_timeout_s": self.phase_timeout_s,
            "stall_monitored": self.stall_monitored,
            "forward_progress": int(self.progress_fn()),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        text = json.dumps(payload, sort_keys=True)
        for retry in range(5):
            try:
                tmp.write_text(text, encoding="utf-8")
                os.replace(tmp, self.path)
                return
            except PermissionError:
                if retry == 4:
                    raise
                time.sleep(0.01 * (retry + 1))

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_s):
            try:
                self.beat()
            except OSError:
                pass

    def start(self) -> "WorkerHeartbeat":
        self.beat()
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
