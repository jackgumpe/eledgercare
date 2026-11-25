"""Run one frozen, candidate-only planner in a single isolated interpreter."""
import argparse
import hashlib
import gzip
import io
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

PYTHON_SHA = "4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", "--no-optional-locks", *args])


def utc():
    return datetime.now(timezone.utc).isoformat()


def execute(args):
    if not sys.flags.isolated or not sys.dont_write_bytecode or sha(Path(sys.executable).read_bytes()) != PYTHON_SHA:
        raise RuntimeError("Interpreter differs from the single-thread stdlib qualification")
    if git("rev-parse", "HEAD").decode().strip() != args.candidate or git("status", "--porcelain"):
        raise ValueError("Candidate worktree is dirty or moved")
    path = Path(args.planner)
    source = path.read_bytes()
    if source.replace(b"\r\n", b"\n") != git("cat-file", "blob", f"{args.candidate}:{path.as_posix()}"):
        raise ValueError("Planner differs from frozen Git blob")
    inputs = args.observations.read_bytes()
    if sha(inputs) != args.input_sha:
        raise ValueError("Input digest differs")
    rows = [json.loads(line) for line in inputs.splitlines()]
    assert len(rows) == 1623
    fields = {"names","points","line","dist","areas","arm","y","read_status","status"}
    if any(set(row) != (fields | ({"q","radius"} if row["arm"]=="H" else set())) for row in rows):
        raise ValueError("Unexpected planner input fields")
    args.out.mkdir(exist_ok=False)
    for key in ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
        os.environ[key] = "1"
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    spec = importlib.util.spec_from_file_location("isolated_route", path)
    route = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(route)
    start_utc = utc()
    start_wall = time.perf_counter_ns()
    start_cpu = time.process_time_ns()
    elapsed = []
    errors = 0
    outputs = args.out / "outputs.jsonl.gz"
    with outputs.open("xb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0, compresslevel=6) as compressed, io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as out:
        for observation in rows:
            start = time.perf_counter_ns()
            try:
                answer = route.evaluate(observation)
            except Exception:
                elapsed.append(time.perf_counter_ns() - start)
                record = {"answer": None, "exception": traceback.format_exc()}
                errors += 1
            else:
                elapsed.append(time.perf_counter_ns() - start)
                record = {"answer": answer, "exception": None}
            record["plan_ns"] = elapsed[-1]
            out.write(json.dumps(record, separators=(",", ":"), allow_nan=False) + "\n")
    whole_cpu = time.process_time_ns() - start_cpu
    whole_wall = time.perf_counter_ns() - start_wall
    summary = {"candidate": args.candidate, "python": platform.python_version(), "executable_sha256": PYTHON_SHA,
               "planner_path": path.as_posix(), "planner_sha256_working_bytes": sha(source),
               "input_sha256": sha(inputs), "outputs_sha256": sha(outputs.read_bytes()),
               "start_utc": start_utc, "end_utc": utc(), "rows": len(rows), "exceptions": errors,
               "timed_region": "1623 sequential calls with compressed output writing; per-call timings bracket evaluate alone",
               "batch_wall_ns": whole_wall, "batch_process_cpu_ns": whole_cpu, "sum_plan_ns": sum(elapsed),
               "min_plan_ns": min(elapsed), "max_plan_ns": max(elapsed)}
    (args.out/"runtime.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(summary))
    return 1 if errors else 0


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--candidate", required=True)
    cli.add_argument("--planner", required=True)
    cli.add_argument("--observations", type=Path, required=True)
    cli.add_argument("--input-sha", required=True)
    cli.add_argument("--out", type=Path, required=True)
    sys.exit(execute(cli.parse_args()))
