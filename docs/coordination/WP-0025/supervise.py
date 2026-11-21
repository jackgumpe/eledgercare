"""Launch one fresh, plan-bound WP-0025 resident model in the existing lease job."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HOST = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0025")
QPY = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe")
sys.path[:0] = [str(ROOT / "docs/research/WP-0014/eld-latency-author"), str(HERE)]
from probe import isolated_env
from device_lease import guard


def environment(sensor):
    env = isolated_env(sensor)
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf8")
    extra = {"LOCALAPPDATA": "app/local", "APPDATA": "app/roaming", "PYTHONPYCACHEPREFIX": "pycache",
             "TRITON_HOME": "triton-home", "TORCH_EXTENSIONS_DIR": "extensions", "MPLCONFIGDIR": "mpl",
             "NUMBA_CACHE_DIR": "numba"}
    for key, tail in extra.items():
        folder = sensor / "cache" / tail
        folder.mkdir(parents=True, exist_ok=True)
        env[key] = str(folder)
    return env


def main(plan_path, expected):
    raw = plan_path.read_bytes()
    if sha256(raw).hexdigest() != expected:
        raise ValueError("The process plan changed")
    plan = json.loads(raw)
    label = plan["process_id"].lower()
    out = Path(plan["output"]).resolve()
    if (label not in ("p1", "p2") or out != (HOST / "review/runs" / label).resolve() or
        Path.cwd() != ROOT or Path(sys.executable).resolve() != QPY.resolve() or
        not sys.flags.isolated or not sys.flags.dont_write_bytecode):
        raise ValueError("Unexpected supervisor execution or destination")
    if subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"], text=True).strip() != plan["candidate"]:
        raise ValueError("Worker checkout differs from the bound revision")
    out.mkdir(parents=True, exist_ok=False)
    run = out / "sensor"
    env = environment(run)
    if env != plan["environment"]:
        raise ValueError("Fresh worker environment differs from the signed plan")
    argv = [str(QPY), "-I", "-B", str(ROOT / "docs/research/WP-0025/runner/process.py"), str(plan_path), expected]
    segment = {"argv": argv, "plan_sha256": expected, "supervisor_pid": os.getpid(),
               "supervisor_parent_pid": os.getppid(), "start_utc_ns": time.time_ns()}
    start = time.perf_counter_ns()
    with (out / "stdout.txt").open("xb") as so, (out / "stderr.txt").open("xb") as se:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=so, stderr=se)
        segment["launcher_pid"] = child.pid
        guard.dump(out / "worker-issued.json", segment)
        try:
            code = child.wait(timeout=plan["deadline_seconds"])
        except subprocess.TimeoutExpired:
            code = 124  # The outer kill-on-close Windows job owns this process and its descendants.
            segment["deadline_elapsed"] = True
    segment.update(returncode=code, end_utc_ns=time.time_ns(), elapsed_s=(time.perf_counter_ns() - start) / 1e9)
    guard.dump(out / "process.json", {"all_segments_completed": code == 0, "segments": [segment]})
    return code


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve(), sys.argv[2]))
