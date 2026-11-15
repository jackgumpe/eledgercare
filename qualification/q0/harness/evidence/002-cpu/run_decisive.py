"""Decisive CPU-check runner for WP-0005 /002 (evidence tooling; not part of the frozen candidate).

Runs the exact commands below from the worktree root with the current interpreter, and
writes each command's combined output, exit code and UTC timing beside this file, plus
summary.json. It refuses to run if tracked files differ from HEAD.
"""

import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]  # attempt 1 used parents[3] (= qualification/), so every command failed to start
OUT = HERE / (sys.argv[1] if len(sys.argv) > 1 else "attempt-2")
assert (ROOT / ".git").exists() and (ROOT / Q0_REL).is_file() if (Q0_REL := "qualification/q0/harness/q0.py") else False
PY = sys.executable
Q0 = "qualification/q0/harness/q0.py"
COMMANDS = [
    ("01-unittest", [PY, "-I", "-B", "-m", "unittest", "discover", "-s", "qualification/q0/harness/tests",
                     "-t", "qualification/q0/harness/tests", "-v"]),
    ("02-verify-snapshots", [PY, "-I", "-B", Q0, "verify-snapshots"]),
    ("03-derive-rasters-check", [PY, "-I", "-B", Q0, "derive-rasters", "--check"]),
    ("04-model-manifest-check", [PY, "-I", "-B", Q0, "build-model-manifest", "--check"]),
    ("05-check-protocol", [PY, "-I", "-B", Q0, "check-protocol"]),
    ("06-status", [PY, "-I", "-B", Q0, "status"]),
    ("07-execute-refused", [PY, "-I", "-B", Q0, "execute", "--owner", "author"]),
]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    if subprocess.run(["git", "diff", "--quiet", "HEAD"], cwd=ROOT).returncode != 0:
        raise SystemExit("tracked files differ from HEAD; refusing decisive run")
    OUT.mkdir()
    storage_root = Path(r"C:\Users\jackg\eLedgerCare-Q0")
    summary = {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
               "untracked_before": git("status", "--porcelain=v1", "-uall").splitlines(),
               "python": sys.version, "python_executable": PY, "platform": platform.platform(),
               "external_storage_parent_exists_before": storage_root.exists(), "started_utc": utc(), "commands": []}
    for name, cmd in COMMANDS:
        t0, started = time.monotonic(), utc()
        cp = subprocess.run(cmd, cwd=ROOT, capture_output=True)
        out = cp.stdout + (b"\n--- stderr ---\n" + cp.stderr if cp.stderr else b"")
        path = OUT / f"{name}.txt"
        with open(path, "xb") as f:
            f.write(out)
        summary["commands"].append({"name": name, "argv": [Path(a).name if a == PY else a for a in cmd],
                                    "exit_code": cp.returncode, "started_utc": started,
                                    "seconds": round(time.monotonic() - t0, 3), "output": path.name,
                                    "output_sha256": hashlib.sha256(out).hexdigest(), "output_bytes": len(out)})
    summary["finished_utc"] = utc()
    summary["external_storage_parent_exists_after"] = storage_root.exists()
    summary["head_after"] = git("rev-parse", "HEAD")
    summary["tracked_diff_after"] = git("diff", "--name-only", "HEAD").splitlines()
    summary["scratch_test_dirs_left"] = sorted(p.name for p in (ROOT / ".scratch" / "q0-harness-tests").glob("*")) \
        if (ROOT / ".scratch" / "q0-harness-tests").exists() else []
    with open(OUT / "summary.json", "x", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps({c["name"]: c["exit_code"] for c in summary["commands"]}))


if __name__ == "__main__":
    main()
