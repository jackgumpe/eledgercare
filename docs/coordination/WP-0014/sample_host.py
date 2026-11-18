"""Sample the shared GPU and owned diagnostic Python processes. Does not start CUDA."""

import argparse
import csv
import datetime
import json
import subprocess
import time
from pathlib import Path

import psutil


FIELDS = ("pstate", "temperature.gpu", "power.draw", "clocks.current.graphics",
          "clocks.current.memory", "utilization.gpu", "utilization.memory", "memory.used",
          "memory.free", "pcie.link.gen.current", "pcie.link.width.current")


def collect(roots):
    devices = subprocess.run(["nvidia-smi", "--id=GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d",
                              "--query-gpu=" + ",".join(FIELDS), "--format=csv,noheader,nounits"],
                             text=True, capture_output=True, timeout=5)
    gpu = dict(zip(FIELDS, next(csv.reader([devices.stdout.strip()], skipinitialspace=True)))) if devices.returncode == 0 else None
    processes = []
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"].lower() not in ("python.exe", "pythonw.exe"):
            continue
        try:
            cwd = Path(proc.cwd())
            owner = next((r for r in roots if cwd.is_relative_to(r)), None)
            if owner is None:
                continue
            mem = proc.memory_info()
            io = proc.io_counters()
            processes.append({"pid": proc.pid, "relative_directory": str(cwd.relative_to(owner)),
                              "private_bytes": mem.private, "working_set_bytes": mem.rss,
                              "read_bytes": io.read_bytes, "write_bytes": io.write_bytes})
        except (psutil.Error, OSError):
            continue
    return {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "host_available_bytes": psutil.virtual_memory().available, "gpu": gpu,
            "nvidia_smi_exit": devices.returncode, "python_in_owned_directories": processes}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--stop", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path, action="append")
    args = parser.parse_args()
    deadline = time.monotonic() + 7200
    with args.output.open("x", encoding="utf-8", buffering=1) as stream:
        while time.monotonic() < deadline and not args.stop.exists():
            print(json.dumps(collect(args.root), separators=(",", ":")), file=stream, flush=True)
            time.sleep(3)
