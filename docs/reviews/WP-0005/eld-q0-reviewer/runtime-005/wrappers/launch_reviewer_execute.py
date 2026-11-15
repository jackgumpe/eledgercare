"""Launch the single authorized WP-0005 /005 reviewer GPU reproduction trial."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REVIEWER_WT = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-reviewer-carbon")
Q0_PY = REVIEWER_WT / "qualification" / "q0" / "harness" / "q0.py"
REVIEWER_EXECUTE = Path(
    r"C:\Users\jackg\Asp.net Projects\eledgercare\docs\coordination\WP-0005\releases\reviewer-execute.json"
)
OUT_DIR = Path(__file__).resolve().parent / "pre-execute"
OUTSIDE_CWD = Path(__file__).resolve().parent / "cwd"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTSIDE_CWD.mkdir(parents=True, exist_ok=True)

    # Verify reviewer worktree is still clean at c8daa97c5be6bc67931b215652a7a0f6ced621ef
    st = subprocess.run(
        [r"C:\Program Files\Git\cmd\git.exe", "-C", str(REVIEWER_WT), "status", "--porcelain=v1"],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True,
    ).stdout
    head = subprocess.run(
        [r"C:\Program Files\Git\cmd\git.exe", "-C", str(REVIEWER_WT), "rev-parse", "HEAD"],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert st == "", f"Worktree not clean: {st!r}"
    assert head == "c8daa97c5be6bc67931b215652a7a0f6ced621ef", f"Unexpected HEAD: {head}"

    stdout_path = OUT_DIR / "07-execute-reviewer-stdout.json"
    stderr_path = OUT_DIR / "07-execute-reviewer-stderr.txt"
    argv = [
        sys.executable,
        "-I",
        "-B",
        str(Q0_PY),
        "execute",
        "--owner",
        "reviewer",
        "--release",
        str(REVIEWER_EXECUTE),
    ]
    t0 = datetime.now(timezone.utc)
    with stdout_path.open("wb") as f_out, stderr_path.open("wb") as f_err:
        cp = subprocess.run(
            argv,
            cwd=str(OUTSIDE_CWD),
            env=dict(os.environ),
            stdin=subprocess.DEVNULL,
            stdout=f_out,
            stderr=f_err,
        )
    t1 = datetime.now(timezone.utc)
    out_bytes = stdout_path.read_bytes()
    err_bytes = stderr_path.read_bytes()
    receipt = {
        "argv": argv,
        "cwd": str(OUTSIDE_CWD),
        "started_utc": t0.isoformat(),
        "finished_utc": t1.isoformat(),
        "wall_seconds": round((t1 - t0).total_seconds(), 3),
        "exit_code": cp.returncode,
        "stdout_bytes": len(out_bytes),
        "stdout_sha256": hashlib.sha256(out_bytes).hexdigest(),
        "stderr_bytes": len(err_bytes),
        "stderr_sha256": hashlib.sha256(err_bytes).hexdigest(),
    }
    (OUT_DIR / "07-execute-reviewer-receipt.json").write_bytes(
        (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return cp.returncode


if __name__ == "__main__":
    raise SystemExit(main())
