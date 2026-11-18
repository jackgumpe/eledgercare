"""Operator shell for the coordinator-released WP-0016 G0 lease (eld-rd-reviewer). Stdlib only.

launch: verifies the release digest, then starts EXACTLY the released command
        `python -I -B device_lease.py <release> <sha256>` as a detached process (breakaway from the tool's job,
        so a tool timeout cannot kill the supervisor). Writes a launch receipt. Generates no plan and
        retries nothing.
watch:  low-frequency liveness checks of that one PID. Logs only process state, lease-file NAMES and the
        latest device sample from the coordinator's device.jsonl. Never reads run outputs, stdout or raw text.
        It stops at its own time limit without touching the supervisor. On exit it prints the lease receipts.
"""
import argparse
import ctypes
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

RELEASE = Path("C:/Users/jackg/Asp.net Projects/eledgercare/docs/coordination/WP-0016/g0-anchor-release.json")
LEASE_PY = Path("C:/Users/jackg/Asp.net Projects/eledgercare/docs/coordination/WP-0016/device_lease.py")
DIGEST = "5595c8b78cd4e3f73c4db93e0081a56179033d2fe2314a520896cc68c7d88f90"
LEASES = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0016/coordination/leases/g0-anchor")
DETACHED, NEW_GROUP, BREAKAWAY = 0x00000008, 0x00000200, 0x01000000
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.OpenProcess.restype = ctypes.c_void_p
k32.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
k32.WaitForSingleObject.restype = ctypes.c_uint32
k32.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
k32.GetExitCodeProcess.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_new(path, obj):
    with Path(path).open("x", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(obj, indent=1) + "\n")


def launch(opdir):
    if hashlib.sha256(RELEASE.read_bytes()).hexdigest() != DIGEST:
        raise SystemExit("release digest mismatch; not launching")
    opdir.mkdir(parents=True, exist_ok=False)
    argv = [sys.executable, "-I", "-B", str(LEASE_PY), str(RELEASE), DIGEST]
    with (opdir / "device_lease.stdout.txt").open("xb") as out, (opdir / "device_lease.stderr.txt").open("xb") as err:
        p = subprocess.Popen(argv, cwd=str(opdir), stdin=subprocess.DEVNULL, stdout=out, stderr=err, close_fds=True,
                             creationflags=DETACHED | NEW_GROUP | BREAKAWAY)
    write_new(opdir / "launch.json", dict(operator="eld-rd-reviewer", launched_utc=utc(), pid=p.pid, argv=argv,
                                          cwd=str(opdir), release=str(RELEASE), release_sha256=DIGEST,
                                          interpreter=sys.version, creationflags="DETACHED|NEW_PROCESS_GROUP|BREAKAWAY"))
    print(json.dumps(dict(pid=p.pid, launched_utc=utc(), argv=argv)))


def lease_state():
    names = sorted(p.name for p in LEASES.iterdir()) if LEASES.is_dir() else []
    last = None
    for dev in sorted(LEASES.glob("*-device.jsonl")) if LEASES.is_dir() else []:
        lines = dev.read_bytes().splitlines()
        if lines:
            s = json.loads(lines[-1])
            last = dict(file=dev.name, samples=len(lines), utc=s.get("utc"), used_mib=s.get("used_mib"),
                        temp_c=s.get("temp_c"))
    return names, last


def watch(opdir, interval, limit):
    pid = json.loads((opdir / "launch.json").read_bytes())["pid"]
    h = k32.OpenProcess(0x00100000 | 0x1000, False, pid)  # SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION
    begin = time.monotonic()
    log = (opdir / "monitor.jsonl").open("a", encoding="utf-8", newline="\n")
    state = "unknown" if h else "cannot_open_process"
    while h:
        alive = k32.WaitForSingleObject(h, 0) == 0x102  # WAIT_TIMEOUT
        names, last = lease_state()
        log.write(json.dumps(dict(utc=utc(), pid=pid, alive=alive, lease_files=names, last_device=last)) + "\n")
        log.flush()
        if not alive:
            state = "exited"
            break
        if time.monotonic() - begin > limit:
            state = "watch_limit_reached_supervisor_untouched"
            break
        k32.WaitForSingleObject(h, int(interval * 1000))
    code = ctypes.c_ulong()
    exit_code = code.value if (state == "exited" and h and k32.GetExitCodeProcess(h, ctypes.byref(code))) else None
    log.write(json.dumps(dict(utc=utc(), pid=pid, watch_end=state, exit_code=exit_code)) + "\n")
    log.close()
    receipts = {}
    if state == "exited" and LEASES.is_dir():
        for f in sorted(LEASES.glob("*.json")):
            receipts[f.name] = json.loads(f.read_bytes())
            receipts[f.name].pop("admission", None)
            receipts[f.name].pop("ownership_after_job_close", None)
    print(json.dumps(dict(state=state, pid=pid, exit_code=exit_code, lease_files=lease_state()[0], receipts=receipts),
                     indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["launch", "watch"])
    ap.add_argument("--opdir", type=Path, required=True)
    ap.add_argument("--interval", type=float, default=120.0)
    ap.add_argument("--limit", type=float, default=7000.0)
    a = ap.parse_args()
    launch(a.opdir) if a.command == "launch" else watch(a.opdir, a.interval, a.limit)


if __name__ == "__main__":
    main()
