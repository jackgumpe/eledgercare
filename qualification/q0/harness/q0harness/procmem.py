"""Process memory counters (Windows, stdlib ctypes) and a bounded-window peak sampler."""

from __future__ import annotations

import ctypes
import sys
import threading
import time

from .outcome import Q0Failure


class _PMC_EX(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t)]


def supported() -> bool:
    return sys.platform == "win32"


def snapshot() -> dict:
    """Direct measurement of this process: working set (RSS), private bytes, page faults."""
    if not supported():
        raise Q0Failure("TELEMETRY_UNSUPPORTED", "process memory counters implemented for Windows only")
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    fn = k32.K32GetProcessMemoryInfo
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(_PMC_EX), ctypes.c_ulong]
    fn.restype = ctypes.c_int
    c = _PMC_EX()
    c.cb = ctypes.sizeof(c)
    if not fn(k32.GetCurrentProcess(), ctypes.byref(c), c.cb):
        raise Q0Failure("TELEMETRY_UNSUPPORTED", f"K32GetProcessMemoryInfo failed: {ctypes.get_last_error()}")
    return {"working_set": c.WorkingSetSize, "peak_working_set_lifetime": c.PeakWorkingSetSize,
            "private_bytes": c.PrivateUsage, "page_faults": c.PageFaultCount}


class PeakSampler:
    """Samples the working set every interval_s during a window (lifetime peak cannot be reset).
    The reported window peak is a lower bound limited by the sampling interval."""

    def __init__(self, interval_s: float = 0.1):
        self.interval = interval_s
        self._stop = threading.Event()
        self._thread = None
        self.samples = 0
        self.peak_ws = 0
        self.peak_private = 0
        self.start_snapshot = None
        self.end_snapshot = None

    def _run(self):
        while not self._stop.is_set():
            s = snapshot()
            self.samples += 1
            self.peak_ws = max(self.peak_ws, s["working_set"])
            self.peak_private = max(self.peak_private, s["private_bytes"])
            self._stop.wait(self.interval)

    def __enter__(self):
        self.start_snapshot = snapshot()
        self._thread = threading.Thread(target=self._run, name="q0-rss-sampler", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join(timeout=5)
        self.end_snapshot = snapshot()
        self.peak_ws = max(self.peak_ws, self.end_snapshot["working_set"])
        self.peak_private = max(self.peak_private, self.end_snapshot["private_bytes"])
        return False

    def result(self) -> dict:
        return {"provenance": "direct_sampled", "interval_s": self.interval, "samples": self.samples,
                "window_peak_working_set_lower_bound": self.peak_ws,
                "window_peak_private_bytes_lower_bound": self.peak_private,
                "start": self.start_snapshot, "end": self.end_snapshot,
                "page_fault_delta": self.end_snapshot["page_faults"] - self.start_snapshot["page_faults"],
                "time": time.time()}
