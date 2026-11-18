"""Disposable per-job entry point. The accepted supervisor owns this process and heartbeat."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from local_ocr.env_guard import WorkerHeartbeat, audit_worker_environment
from local_ocr.worker import _validate_request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=Path)
    request = parser.parse_args().request
    req = json.loads(request.read_text())
    run, root, q0 = _validate_request(req, request)
    audit_worker_environment(dict(os.environ), run_dir=run, readonly_q0_root=q0, leased_gpu_uuid=req["leased_gpu_uuid"])
    control = root / "control"
    item = control / (req["attempt_id"] + ".job")
    start_ms = time.time_ns() / 1e6
    partial = item.with_suffix(".tmp")
    partial.write_text(json.dumps({"path": str(request), "worker_start_ms": start_ms, "bridge_pid": os.getpid()}))
    partial.rename(item)
    progress = 0
    beat = WorkerHeartbeat(run / "output/heartbeat.json", attempt_id=req["attempt_id"],
                           fencing_token=req["fencing_token"], interval_s=1, progress_fn=lambda: progress).start()
    beat.set_phase("waiting_for_resident", 600)
    last = None
    try:
        while time.time_ns() / 1e6 - start_ms < 600000:
            if item.with_suffix(".done").exists():
                return int(item.with_suffix(".done").read_text())
            if (control / "engine.dead").exists():
                return 3
            info = run / "output/resident-heartbeat.json"
            if info.exists():
                try:
                    hb = json.loads(info.read_bytes())
                    progress = hb["forward_progress"]
                    if hb["phase"] != last:
                        beat.set_phase(hb["phase"], hb["phase_timeout_s"], stall_monitored=hb["stall_monitored"])
                        last = hb["phase"]
                except (FileNotFoundError, PermissionError):
                    pass
            time.sleep(.03)
        return 4
    finally:
        beat.stop()


if __name__ == "__main__":
    sys.exit(main())
