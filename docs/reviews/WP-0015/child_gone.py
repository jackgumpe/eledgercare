"""Read-only check that a finished run's trial child (and its supervisor) no longer exist. Stdlib only.

Opens each recorded PID with query-only rights. A PID counts as the same process only when its Win32
creation FILETIME equals the recorded one (child.json) -- a reused PID is reported as 'pid_reused'.
Never signals or terminates anything.
"""
import ctypes
import json
import sys
from ctypes import wintypes
from pathlib import Path

K = ctypes.WinDLL("kernel32", use_last_error=True)
K.OpenProcess.restype = wintypes.HANDLE
K.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
K.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
K.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
K.CloseHandle.argtypes = (wintypes.HANDLE,)
QUERY_LIMITED, STILL_ACTIVE = 0x1000, 259


def state(pid, created=None):
    h = K.OpenProcess(QUERY_LIMITED, False, pid)
    if not h:
        return "absent"
    try:
        c, e, k, u = (wintypes.FILETIME() for _ in range(4))
        K.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u))
        ft = (c.dwHighDateTime << 32) | c.dwLowDateTime
        code = wintypes.DWORD()
        K.GetExitCodeProcess(h, ctypes.byref(code))
        if created is not None and ft != created:
            return "pid_reused"
        return "running" if code.value == STILL_ACTIVE else f"exited_handle_open({code.value})"
    finally:
        K.CloseHandle(h)


def main(run):
    run = Path(run)
    child = json.loads((run / "child.json").read_text())
    launch = json.loads((run / "launch.json").read_text())
    process = json.loads((run / "process.json").read_text())
    # process.json pid is the Popen'd venv launcher; child.json pid is the interpreter that ran trial.py.
    out = dict(run=run.name, trial_pid=child["pid"], trial=state(child["pid"], child["creation_filetime"]),
               popen_pid=process["pid"], popen=state(process["pid"]),
               supervisor_pid=launch["supervisor_pid"], supervisor=state(launch["supervisor_pid"]),
               returncode=process["returncode"], reason=process["reason"])
    out["gone"] = "running" not in (out["trial"], out["popen"], out["supervisor"])
    print(json.dumps(out))
    return 0 if out["gone"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
