"""Parent supervisor: launches exactly one execution child with an explicit environment,
enforces per-phase timeouts, the stall window, the log cap and the free-space floor from
the child's heartbeat and the volume, and terminates ONLY its own child process (by Popen
handle). It never inspects or stops any other process. Read-only observer commands (the
two frozen nvidia-smi queries) run with their own timeouts and bounded output and are
recorded, never acted upon. Raw child stdout/stderr are preserved byte-for-byte and scanned
for the model's own diagnostic markers (logscan; absence proves nothing).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

from . import logscan
from .outcome import FAILURE_CLASSES


def _read_heartbeat(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def run_observers(cmds: list[list[str]] | None, out_dir: Path, tag: str, cap: int = 65536, timeout_s: int = 30) -> list[dict]:
    rows = []
    for i, cmd in enumerate(cmds or []):
        t = time.time()
        try:
            cp = subprocess.run(cmd, capture_output=True, timeout=timeout_s)
            data, rc = cp.stdout[:cap] + (b"\n--- stderr ---\n" + cp.stderr[:4096] if cp.stderr else b""), cp.returncode
        except (OSError, subprocess.TimeoutExpired) as e:
            data, rc = repr(e).encode(), None
        path = Path(out_dir) / f"observer-{tag}-{i}.txt"
        with open(path, "xb") as f:
            f.write(data)
        rows.append({"tag": tag, "index": i, "returncode": rc, "bytes": len(data), "path": str(path), "t": t})
    return rows


def supervise(cmd: list[str], *, env: dict, cwd: Path, run_dir: Path, heartbeat_path: Path, session_timeout_s: int,
              stall_s: int, max_log_bytes: int, default_phase_timeout_s: int, poll_s: float = 1.0,
              observer_cmds: list[list[str]] | None = None, observer_every_s: int = 60,
              free_space_path: Path | None = None, min_free_bytes: int = 0, disk_usage=shutil.disk_usage,
              clock=time.monotonic) -> dict:
    run_dir = Path(run_dir)
    stdout_path, stderr_path = run_dir / "child.stdout.txt", run_dir / "child.stderr.txt"
    observers = run_observers(observer_cmds, run_dir, "pre")
    free = []

    def free_now():
        if free_space_path is None:
            return None
        v = disk_usage(str(free_space_path)).free
        free.append(v)
        return v

    free_before = free_now()
    with open(stdout_path, "xb") as out, open(stderr_path, "xb") as err:
        start = clock()
        proc = subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        verdict, detail = None, None
        phase, phase_seen_at, last_progress, progress_at = None, start, None, start
        next_obs = start + observer_every_s
        while True:
            rc = proc.poll()
            if rc is not None:
                break
            now = clock()
            hb = _read_heartbeat(heartbeat_path)
            if hb is not None:
                if hb.get("phase") != phase:
                    phase, phase_seen_at = hb.get("phase"), now
                    last_progress, progress_at = hb.get("progress"), now
                elif hb.get("progress") != last_progress:
                    last_progress, progress_at = hb.get("progress"), now
            phase_timeout = (hb or {}).get("phase_timeout_s") or default_phase_timeout_s
            log_bytes = stdout_path.stat().st_size + stderr_path.stat().st_size
            fv = free_now()
            if now - start > session_timeout_s:
                verdict, detail = "TIMEOUT", f"session exceeded {session_timeout_s}s in phase {phase}"
            elif now - phase_seen_at > phase_timeout:
                verdict, detail = "TIMEOUT", f"phase {phase} exceeded {phase_timeout}s"
            elif (hb or {}).get("stall_monitored") and now - progress_at > stall_s:
                verdict, detail = "SEVERE_STALL", f"no native forward progress for {stall_s}s in phase {phase}"
            elif log_bytes > max_log_bytes:
                verdict, detail = "LOG_CAP_EXCEEDED", f"child output {log_bytes} > {max_log_bytes} bytes"
            elif fv is not None and fv < min_free_bytes:
                verdict, detail = "STORAGE_FLOOR", f"free {fv} < floor {min_free_bytes} bytes in phase {phase}"
            if verdict:
                proc.kill()  # TerminateProcess on our own child handle only
                try:
                    proc.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    detail += "; child did not exit within 60s after kill"
                break
            if observer_cmds and now >= next_obs:
                observers += run_observers(observer_cmds, run_dir, f"during-{int(now - start)}")
                next_obs = now + observer_every_s
            time.sleep(poll_s)
        elapsed = clock() - start
    observers += run_observers(observer_cmds, run_dir, "post")
    free_after = free_now()
    result_path = run_dir / "evidence" / "outcome.json"
    child_outcome = None
    if result_path.is_file():
        try:
            child_outcome = json.loads(result_path.read_text(encoding="utf-8"))
        except ValueError:
            child_outcome = None
    if verdict is None and (proc.returncode != 0 or child_outcome is None):
        verdict, detail = "CHILD_EXIT_NONZERO", f"exit code {proc.returncode}; outcome present={child_outcome is not None}"
    rec = {"schema": "eldq0-supervisor/2", "child_pid": proc.pid, "child_returncode": proc.returncode,
           "elapsed_s": elapsed, "last_phase": phase, "last_progress": last_progress,
           "verdict": verdict or "CHILD_COMPLETED",
           "failure": None if verdict is None else {"failure_class": verdict, "description": FAILURE_CLASSES[verdict],
                                                     "detail": detail},
           "child_outcome_status": (child_outcome or {}).get("status"),
           "observers": observers, "stdout": str(stdout_path), "stderr": str(stderr_path),
           "log_markers": {"stdout": logscan.scan(stdout_path.read_bytes()),
                           "stderr": logscan.scan(stderr_path.read_bytes())},
           "free_space": {"provenance": "direct", "volume": None if free_space_path is None else str(free_space_path),
                          "floor_bytes": min_free_bytes, "before": free_before, "after": free_after,
                          "min_observed": min(free) if free else None, "samples": len(free)},
           "accuracy_score": None}
    with open(run_dir / "supervisor.json", "x", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, sort_keys=True)
    return rec
