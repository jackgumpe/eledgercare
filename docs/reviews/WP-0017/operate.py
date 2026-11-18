"""Operator shell for coordinator-released WP-0017 GPU leases (eld-rd-reviewer). Stdlib only, Windows.

launch   Verifies the release-file digest and the lease-executor digest, then starts EXACTLY
         `python -I -B <lease.py> <release> <digest>` as a detached process that breaks away from the calling
         tool's job, so a CLI timeout cannot kill it. Writes an exclusive launch receipt. Builds no plan, edits
         nothing it launches, and never retries.
monitor  Starts `operate.py watch` itself as a second detached, reviewer-owned process. It survives the end of
         this CLI turn and appends to <opdir>/monitor.jsonl until the supervisor exits or its limit elapses.
watch    Low-frequency liveness checks of the one launched PID. Logs process state, lease-file NAMES and the
         latest device sample from the coordinator's *-device.jsonl. It never reads run outputs, stdout or
         model text. At its own limit it stops and leaves the supervisor untouched.
status   Prints the launch receipt, the last monitor lines and, after exit, the lease receipts.

The tool never terminates, signals or reprioritises any process.
"""
import argparse
import ctypes
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

DETACHED, NEW_GROUP, BREAKAWAY, NO_WINDOW = 0x00000008, 0x00000200, 0x01000000, 0x08000000
SYNCHRONIZE, QUERY_LIMITED = 0x00100000, 0x1000
WAIT_TIMEOUT = 0x102


def k32():
    lib = ctypes.WinDLL("kernel32", use_last_error=True)
    lib.OpenProcess.restype = ctypes.c_void_p
    lib.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
    lib.WaitForSingleObject.restype = ctypes.c_uint32
    lib.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
    lib.GetExitCodeProcess.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))
    return lib


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, obj):
    with Path(path).open("x", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(obj, indent=1) + "\n")


def detached(argv, cwd, out, err):
    with Path(out).open("xb") as o, Path(err).open("xb") as e:
        return subprocess.Popen(argv, cwd=str(cwd), stdin=subprocess.DEVNULL, stdout=o, stderr=e, close_fds=True,
                                creationflags=DETACHED | NEW_GROUP | BREAKAWAY)


def launch(a):
    if sha(a.release) != a.digest:
        raise SystemExit("release digest mismatch; not launching")
    if sha(a.lease_py) != a.lease_py_sha256:
        raise SystemExit("lease executor digest mismatch; not launching")
    a.opdir.mkdir(parents=True, exist_ok=False)
    argv = [a.python or sys.executable, "-I", "-B", str(a.lease_py), str(a.release), a.digest]
    p = detached(argv, a.opdir, a.opdir / "lease.stdout.txt", a.opdir / "lease.stderr.txt")
    rec = dict(operator="eld-rd-reviewer", launched_utc=utc(), pid=p.pid, argv=argv, cwd=str(a.opdir),
               release=str(a.release), release_sha256=a.digest, lease_py=str(a.lease_py),
               lease_py_sha256=a.lease_py_sha256, leases_dir=str(a.leases_dir), interpreter=sys.version,
               creationflags="DETACHED|NEW_PROCESS_GROUP|BREAKAWAY_FROM_JOB")
    write_new(a.opdir / "launch.json", rec)
    print(json.dumps(dict(pid=p.pid, launched_utc=rec["launched_utc"], argv=argv)))


def lease_state(leases):
    leases = Path(leases)
    names = sorted(p.name for p in leases.iterdir()) if leases.is_dir() else []
    last = None
    for dev in sorted(leases.glob("*-device.jsonl")) if leases.is_dir() else []:
        lines = dev.read_bytes().splitlines()
        if lines:
            s = json.loads(lines[-1])
            last = dict(file=dev.name, samples=len(lines), utc=s.get("utc"), used_mib=s.get("used_mib"),
                        temp_c=s.get("temp_c"))
    return names, last


def watch(a):
    rec = json.loads((a.opdir / "launch.json").read_bytes())
    pid, leases = rec["pid"], rec["leases_dir"]
    lib = k32()
    h = lib.OpenProcess(SYNCHRONIZE | QUERY_LIMITED, False, pid)
    begin = time.monotonic()
    state = "unknown" if h else "cannot_open_process"
    with (a.opdir / "monitor.jsonl").open("a", encoding="utf-8", newline="\n") as log:
        log.write(json.dumps(dict(utc=utc(), watch_start=True, pid=pid, interval_s=a.interval, limit_s=a.limit)) + "\n")
        while h:
            alive = lib.WaitForSingleObject(h, 0) == WAIT_TIMEOUT
            names, last = lease_state(leases)
            log.write(json.dumps(dict(utc=utc(), pid=pid, alive=alive, lease_files=names, last_device=last)) + "\n")
            log.flush()
            if not alive:
                state = "exited"
                break
            if time.monotonic() - begin > a.limit:
                state = "watch_limit_reached_supervisor_untouched"
                break
            lib.WaitForSingleObject(h, int(a.interval * 1000))
        code = ctypes.c_ulong()
        exit_code = code.value if (state == "exited" and lib.GetExitCodeProcess(h, ctypes.byref(code))) else None
        log.write(json.dumps(dict(utc=utc(), pid=pid, watch_end=state, exit_code=exit_code)) + "\n")
    print(json.dumps(dict(state=state, pid=pid, exit_code=exit_code)))


def monitor(a):
    if (a.opdir / "monitor.json").exists():
        raise SystemExit("a monitor was already started for this opdir")
    argv = [a.python or sys.executable, "-I", "-B", str(Path(__file__).resolve()), "watch", "--opdir", str(a.opdir),
            "--interval", str(a.interval), "--limit", str(a.limit)]
    p = detached(argv, a.opdir, a.opdir / "monitor.stdout.txt", a.opdir / "monitor.stderr.txt")
    write_new(a.opdir / "monitor.json", dict(operator="eld-rd-reviewer", started_utc=utc(), pid=p.pid, argv=argv))
    print(json.dumps(dict(monitor_pid=p.pid)))


def status(a):
    rec = json.loads((a.opdir / "launch.json").read_bytes())
    lines = (a.opdir / "monitor.jsonl").read_text(encoding="utf-8").splitlines() if (a.opdir / "monitor.jsonl").is_file() else []
    receipts = {}
    leases = Path(rec["leases_dir"])
    ended = any("watch_end" in ln for ln in lines[-2:])
    if ended and leases.is_dir():
        for f in sorted(leases.glob("*.json")):
            r = json.loads(f.read_bytes())
            r.pop("admission", None)
            r.pop("ownership_after_job_close", None)
            receipts[f.name] = r
    print(json.dumps(dict(launch=dict(pid=rec["pid"], launched_utc=rec["launched_utc"], release_sha256=rec["release_sha256"]),
                          monitor_tail=[json.loads(x) for x in lines[-a.tail:]], lease_files=lease_state(leases)[0],
                          receipts=receipts), indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["launch", "monitor", "watch", "status"])
    ap.add_argument("--opdir", type=Path, required=True)
    ap.add_argument("--release", type=Path)
    ap.add_argument("--digest")
    ap.add_argument("--lease-py", type=Path)
    ap.add_argument("--lease-py-sha256")
    ap.add_argument("--leases-dir", type=Path, help="coordinator lease receipt directory for this release")
    ap.add_argument("--python", help="interpreter for the detached child (default: this one)")
    ap.add_argument("--interval", type=float, default=120.0)
    ap.add_argument("--limit", type=float, default=7200.0)
    ap.add_argument("--tail", type=int, default=5)
    a = ap.parse_args()
    if a.command == "launch":
        missing = [n for n in ("release", "digest", "lease_py", "lease_py_sha256", "leases_dir") if getattr(a, n) is None]
        if missing:
            raise SystemExit(f"launch needs {missing}")
        launch(a)
    else:
        {"monitor": monitor, "watch": watch, "status": status}[a.command](a)


if __name__ == "__main__":
    main()
