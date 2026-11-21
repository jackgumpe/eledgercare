"""Start precisely one W0-conditioned model inside the issued Windows job."""
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from device_lease import guard

spec = spec_from_file_location("historical_supervisor", HERE.parent / "WP-0025/supervise.py")
previous = module_from_spec(spec)
spec.loader.exec_module(previous)
environment, QPY = previous.environment, previous.QPY
HOST = guard.PACKET
OUT = HOST / "review/runs"
P = "docs/coordination/WP-0026"
PROCESSES = {"p1", "p2", "train-c1-r1", "train-features-r1", "cal-features-r1",
             "blind-c1-r1", "blind-features-r1"}


def supervise(path, digest):
    if guard.sha(path) != digest:
        raise ValueError("Process plan has changed")
    plan = json.loads(path.read_bytes())
    label = plan["process_id"]
    out = Path(plan["output"]).resolve()
    if (label not in PROCESSES or plan["packet"] != "WP-0026" or out != (OUT / label).resolve()
            or Path.cwd() != ROOT or Path(sys.executable).resolve() != QPY.resolve()
            or not sys.flags.isolated or not sys.dont_write_bytecode):
        raise ValueError("Unexpected process binding")
    revision = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"], text=True).strip()
    if revision != plan["candidate"]:
        raise ValueError("Checkout differs from plan")
    out.mkdir(parents=True, exist_ok=False)
    folder = out / "sensor"
    env = environment(folder)
    if env != plan["environment"]:
        raise ValueError("Worker environment differs from plan")
    argv = [str(QPY), "-I", "-B", str(ROOT / "docs/research/WP-0026/worker.py"), str(path), digest]
    segment = {"argv": argv, "plan_sha256": digest, "supervisor_pid": os.getpid(),
               "supervisor_parent_pid": os.getppid(), "start_utc_ns": time.time_ns()}
    start = time.perf_counter()
    with (out / "stdout.txt").open("xb") as stdout, (out / "stderr.txt").open("xb") as stderr:
        child = subprocess.Popen(argv, cwd=folder, env=env, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
        segment["launcher_pid"] = child.pid
        guard.dump(out / "worker-issued.json", segment)
        try:
            code = child.wait(timeout=plan["deadline_seconds"])
        except subprocess.TimeoutExpired:
            code = 124
            segment["deadline_elapsed"] = True
    segment.update(returncode=code, end_utc_ns=time.time_ns(), elapsed_s=time.perf_counter()-start)
    guard.dump(out / "process.json", {"all_segments_completed": code == 0, "segments": [segment]})
    return code


if __name__ == "__main__":
    sys.exit(supervise(Path(sys.argv[1]).resolve(), sys.argv[2]))
