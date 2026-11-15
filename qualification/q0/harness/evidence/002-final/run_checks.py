"""Decisive CPU checks for the frozen WP-0005 /002 candidate (evidence tooling; not candidate code).

Usage: python -I -B <this file> <output-subdir-name>
Runs the commands below from the worktree root with the current interpreter and writes each
command's raw stdout/stderr bytes (binary; this directory is `-text` in Git so committed bytes
equal the recorded digests), exit codes and UTC timing to <this dir>/<output-subdir-name>/,
plus summary.json. Refuses if tracked files differ from HEAD.
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
ROOT = HERE.parents[4]
Q0 = "qualification/q0/harness/q0.py"
assert (ROOT / ".git").exists() and (ROOT / Q0).is_file(), ROOT
PY = sys.executable
COMMANDS = [
    ("01-unittest", [PY, "-I", "-B", "-m", "unittest", "discover", "-s", "qualification/q0/harness/tests",
                     "-t", "qualification/q0/harness/tests", "-v"]),
    ("02-verify-snapshots", [PY, "-I", "-B", Q0, "verify-snapshots"]),
    ("03-derive-rasters-check", [PY, "-I", "-B", Q0, "derive-rasters", "--check"]),
    ("04-model-manifest-check", [PY, "-I", "-B", Q0, "build-model-manifest", "--check"]),
    ("05-check-protocol", [PY, "-I", "-B", Q0, "check-protocol"]),
    ("06-lock-check", [PY, "-I", "-B", Q0, "lock-check"]),
    ("07-status", [PY, "-I", "-B", Q0, "status"]),
    ("08-host-precheck-initial", [PY, "-I", "-B", Q0, "host-precheck", "--stage", "initial"]),
    ("09-execute-refused", [PY, "-I", "-B", Q0, "execute", "--owner", "author"]),
    ("10-write-requirements-refused", [PY, "-I", "-B", Q0, "write-requirements", ".scratch/never-written.txt"]),
    ("11-verify-wheelhouse-refused", [PY, "-I", "-B", Q0, "verify-wheelhouse", ".scratch"]),
]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def main():
    out_dir = HERE / sys.argv[1]
    if subprocess.run(["git", "diff", "--quiet", "HEAD"], cwd=ROOT).returncode != 0:
        raise SystemExit("tracked files differ from HEAD; refusing")
    out_dir.mkdir()
    storage = Path(r"C:\Users\jackg\eLedgerCare-Q0")
    summary = {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
               "status_before": git("status", "--porcelain=v1", "-uall").splitlines(),
               "python": sys.version, "python_executable": PY, "platform": platform.platform(),
               "external_storage_parent_exists_before": storage.exists(), "started_utc": utc(), "commands": []}
    for name, cmd in COMMANDS:
        t0, started = time.monotonic(), utc()
        cp = subprocess.run(cmd, cwd=ROOT, capture_output=True)
        out = cp.stdout + (b"\n--- stderr ---\n" + cp.stderr if cp.stderr else b"")
        path = out_dir / f"{name}.txt"
        with open(path, "xb") as f:
            f.write(out)
        summary["commands"].append({"name": name, "argv": ["python.exe" if a == PY else a for a in cmd],
                                    "exit_code": cp.returncode, "started_utc": started,
                                    "seconds": round(time.monotonic() - t0, 3), "output": path.name,
                                    "output_sha256": hashlib.sha256(out).hexdigest(), "output_bytes": len(out)})
    summary.update(finished_utc=utc(), external_storage_parent_exists_after=storage.exists(),
                   head_after=git("rev-parse", "HEAD"), tracked_diff_after=git("diff", "--name-only", "HEAD").splitlines(),
                   never_written_exists=(ROOT / ".scratch/never-written.txt").exists(),
                   scratch_test_dirs_left=sorted(p.name for p in (ROOT / ".scratch/q0-harness-tests").glob("*"))
                   if (ROOT / ".scratch/q0-harness-tests").exists() else [])
    data = (json.dumps(summary, indent=2) + "\n").encode("utf-8")
    with open(out_dir / "summary.json", "xb") as f:
        f.write(data)
    print(json.dumps({c["name"]: c["exit_code"] for c in summary["commands"]}))


if __name__ == "__main__":
    main()
