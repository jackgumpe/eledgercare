"""Small preserved diagnostic runner for frozen WP-0005 /010 candidate verification.

Executes justified positive/negative lock unit tests, isolated-Git subprocess regression tests,
and direct read-only 32-wheel `verify_wheelhouse` under both `stage_offline` (`build_stage_env`)
and stdlib bootstrap Python (`-I -B`), while verifying `C:\\Users\\jackg\\eLedgerCare-Q0\\WP-0005`
remains 100% unchanged (read-only).
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "outputs"
REPO_ROOT = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness")
HARNESS_DIR = REPO_ROOT / "qualification" / "q0" / "harness"
Q0_PY = HARNESS_DIR / "q0.py"
HOST_PY = Path(r"C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe")
ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")
VENV_PY = ROOT / "venv" / "Scripts" / "python.exe"
WHEELHOUSE = ROOT / "wheelhouse"
OLD_INSTALL_RELEASE = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare\docs\coordination\WP-0005\releases\author-install.json")
WHEEL_VERIFIER = HERE / "verify_32_wheels_readonly.py"

sys.path.insert(0, str(HARNESS_DIR))
from q0harness.environment import FORBIDDEN_PATTERNS, build_stage_env  # noqa: E402
from q0harness.hashing import file_digests  # noqa: E402
from q0harness.modelfiles import is_reparse_or_link  # noqa: E402
from q0harness.protocol import load_protocol  # noqa: E402


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def git_str(*args: str) -> str:
    cp = subprocess.run(["git", "--no-optional-locks", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return cp.stdout.strip()


def snapshot_runtime_root(base: Path) -> dict:
    files = 0
    total_bytes = 0
    reparse = []
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        for d in list(dirnames):
            dp = Path(dirpath) / d
            if is_reparse_or_link(dp):
                reparse.append(str(dp))
                dirnames.remove(d)
        for fn in filenames:
            fp = Path(dirpath) / fn
            files += 1
            if is_reparse_or_link(fp):
                reparse.append(str(fp))
            else:
                total_bytes += fp.stat().st_size
    return {"files": files, "bytes": total_bytes, "reparse_points": reparse}


def main() -> int:
    expected_head = sys.argv[1]
    if OUT_DIR.exists():
        raise SystemExit(f"refusing to overwrite {OUT_DIR}")
    OUT_DIR.mkdir(parents=True)

    head_before = git_str("rev-parse", "HEAD")
    status_before = git_str("status", "--porcelain=v1", "-uall")
    if head_before != expected_head or status_before != "":
        raise SystemExit(f"worktree not clean at {expected_head}: head={head_before!r} status={status_before!r}")

    protocol, p_sha = load_protocol()
    parent_env = dict(os.environ)
    env_offline = build_stage_env(parent_env, root=ROOT, protocol=protocol, network=False)
    envs = {"host": parent_env, "stage_offline": env_offline}

    root_before = snapshot_runtime_root(ROOT)
    pip_before = json.loads(
        subprocess.check_output([str(VENV_PY), "-s", "-B", "-m", "pip", "list", "--format=json"], cwd=REPO_ROOT, env=env_offline, text=True)
    )

    summary: dict = {
        "schema": "eldq0-010-verification/1",
        "packet": "WP-0005",
        "sequence": "010",
        "candidate": expected_head,
        "harness_tree": git_str("rev-parse", "HEAD:qualification/q0/harness"),
        "started_utc": utc(),
        "protocol_sha256": p_sha,
        "lock_sha256": file_digests(HARNESS_DIR / "locks" / "dependency-lock.json")["sha256"],
        "manifest_sha256": file_digests(HARNESS_DIR / "manifests" / "model-files.json")["sha256"],
        "runner_script": {"name": Path(__file__).name, **file_digests(Path(__file__), git_blob=True)},
        "wheel_verifier_script": {"name": WHEEL_VERIFIER.name, **file_digests(WHEEL_VERIFIER, git_blob=True)},
        "stage_offline_env": {
            k: ("<REDACTED>" if any(rx.search(k) for rx in FORBIDDEN_PATTERNS) else v)
            for k, v in sorted(env_offline.items())
        },
        "runtime_root_before": root_before,
        "venv_pip_list_before": pip_before,
        "steps": [],
    }

    def run_step(name: str, argv: list[str], *, env_profile: str, expect_rc: int = 0) -> None:
        started = utc()
        t0 = time.monotonic()
        cp = subprocess.run(argv, cwd=REPO_ROOT, env=envs[env_profile], capture_output=True, timeout=300)
        elapsed = round(time.monotonic() - t0, 3)
        finished = utc()
        raw = cp.stdout + (b"\n--- stderr ---\n" + cp.stderr if cp.stderr else b"")
        out_path = OUT_DIR / f"{name}.txt"
        out_path.write_bytes(raw)
        summary["steps"].append({
            "name": name,
            "env_profile": env_profile,
            "argv": argv,
            "exit_code": cp.returncode,
            "expected_exit_code": expect_rc,
            "started_utc": started,
            "finished_utc": finished,
            "seconds": elapsed,
            "output": out_path.name,
            "output_bytes": len(raw),
            "output_sha256": hashlib.sha256(raw).hexdigest(),
        })
        if cp.returncode != expect_rc:
            (OUT_DIR / "summary.json").write_bytes((json.dumps(summary, indent=2) + "\n").encode("utf-8"))
            raise SystemExit(f"step {name} failed: rc={cp.returncode} != {expect_rc}")

    run_step(
        "01-unittest-locks-preflight",
        [str(HOST_PY), "-I", "-B", "-m", "unittest", "discover", "-s", "qualification/q0/harness/tests",
         "-t", "qualification/q0/harness/tests", "-p", "test_locks_preflight.py", "-v"],
        env_profile="host",
    )
    run_step(
        "02-unittest-isolated-git-subprocess",
        [str(HOST_PY), "-I", "-B", "-m", "unittest", "discover", "-s", "qualification/q0/harness/tests",
         "-t", "qualification/q0/harness/tests", "-p", "test_isolated_git_subprocess.py", "-v"],
        env_profile="host",
    )
    run_step(
        "03-lock-check-stage-offline",
        [str(VENV_PY), "-s", "-B", str(Q0_PY), "lock-check"],
        env_profile="stage_offline",
    )
    run_step(
        "04-status-stage-offline",
        [str(VENV_PY), "-s", "-B", str(Q0_PY), "status"],
        env_profile="stage_offline",
    )
    run_step(
        "05-verify-wheelhouse-stale-release-refused",
        [str(VENV_PY), "-s", "-B", str(Q0_PY), "verify-wheelhouse", str(WHEELHOUSE), "--release", str(OLD_INSTALL_RELEASE)],
        env_profile="stage_offline",
        expect_rc=2,
    )
    run_step(
        "06-readonly-32-wheel-verify-stage-offline",
        [str(VENV_PY), "-s", "-B", "-P", "-X", "utf8", str(WHEEL_VERIFIER), str(HARNESS_DIR), str(REPO_ROOT), str(WHEELHOUSE), "stage_offline"],
        env_profile="stage_offline",
    )
    run_step(
        "06b-readonly-32-wheel-verify-stdlib-host",
        [str(HOST_PY), "-I", "-B", str(WHEEL_VERIFIER), str(HARNESS_DIR), str(REPO_ROOT), str(WHEELHOUSE), "stdlib_host"],
        env_profile="host",
    )

    root_after = snapshot_runtime_root(ROOT)
    pip_after = json.loads(
        subprocess.check_output([str(VENV_PY), "-s", "-B", "-m", "pip", "list", "--format=json"], cwd=REPO_ROOT, env=env_offline, text=True)
    )
    head_after = git_str("rev-parse", "HEAD")
    status_after = git_str("status", "--porcelain=v1", "-uall")
    scratch_left = [p.name for p in (REPO_ROOT / ".scratch" / "q0-harness-tests").glob("*")] if (REPO_ROOT / ".scratch" / "q0-harness-tests").exists() else []

    summary.update({
        "status": "pass",
        "head_after": head_after,
        "status_after": status_after,
        "head_and_worktree_unchanged": head_after == expected_head and status_after == "",
        "runtime_root_after": root_after,
        "runtime_root_unchanged": root_before == root_after,
        "venv_pip_list_after": pip_after,
        "venv_unchanged": pip_before == pip_after == [{"name": "pip", "version": "25.0.1"}],
        "scratch_test_dirs_left": scratch_left,
        "finished_utc": utc(),
    })
    if not (summary["head_and_worktree_unchanged"] and summary["runtime_root_unchanged"] and summary["venv_unchanged"] and not scratch_left):
        raise SystemExit(f"post-check invariant failed: {summary}")
    (OUT_DIR / "summary.json").write_bytes((json.dumps(summary, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({
        "status": summary["status"],
        "candidate": summary["candidate"],
        "steps": [(s["name"], s["exit_code"], s["seconds"]) for s in summary["steps"]],
        "runtime_root_unchanged": summary["runtime_root_unchanged"],
        "venv_unchanged": summary["venv_unchanged"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
