"""Concise operational continuation wrapper for WP-0005 /004 Stages B.3 through D.

Resumes existing `C:\\Users\\jackg\\eLedgerCare-Q0\\WP-0005` (exact 32 downloaded wheels and
pip-25.0.1-only CPython 3.12.10 venv) with clean executing HEAD
`099a2fa74cdc2df6068c437edf3971eb37e9f07d` (accepted core `41d6204648e4115ab197507d1a22f6d5c7f3e784`)
and bound install release `author-install-after-011.json`.

Performs zero redownloads of verified wheels, zero venv recreation, zero torch/transformers/model
imports, and zero GPU allocation. Stops fail-closed at the first non-zero exit code, free-space
floor breach, reparse point, or path-length violation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "outputs"
REPO_ROOT = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness")
HARNESS_DIR = REPO_ROOT / "qualification" / "q0" / "harness"
Q0_PY = HARNESS_DIR / "q0.py"
MANIFEST_JSON = HARNESS_DIR / "manifests" / "model-files.json"
LOCK_JSON = HARNESS_DIR / "locks" / "dependency-lock.json"
HOST_PY = Path(r"C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe")
ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")
INSTALL_RELEASE = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare\docs\coordination\WP-0005\releases\author-install-after-011.json")
EXPECTED_HEAD = "099a2fa74cdc2df6068c437edf3971eb37e9f07d"
MODEL_REV = "0480966938291445591f69f08a13b041c073a96a"

sys.path.insert(0, str(HARNESS_DIR))
from q0harness.environment import (  # noqa: E402
    FORBIDDEN_PATTERNS,
    build_stage_env,
    check_storage_root,
    default_forbidden_parents,
)
from q0harness.hashing import file_digests  # noqa: E402
from q0harness.hostcheck import FS_KEY, LEGACY_MAX_PATH, PATH_MARGIN, max_path_under, read_registry  # noqa: E402
from q0harness.modelfiles import is_reparse_or_link  # noqa: E402
from q0harness.protocol import load_protocol  # noqa: E402


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def git_str(*args: str) -> str:
    cp = subprocess.run(["git", "--no-optional-locks", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return cp.stdout.strip()


def stage_env_sanitized_view(env: dict[str, str]) -> dict[str, str]:
    return {
        k: ("<REDACTED>" if any(rx.search(k) for rx in FORBIDDEN_PATTERNS) else env[k])
        for k in sorted(env)
    }


def walk_inventory(base: Path) -> dict:
    total_files = 0
    total_dirs = 0
    total_bytes = 0
    reparse_points: list[str] = []
    longest = ""
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        for d in list(dirnames):
            dp = Path(dirpath) / d
            total_dirs += 1
            if is_reparse_or_link(dp):
                reparse_points.append(str(dp))
                dirnames.remove(d)
        for fn in filenames:
            fp = Path(dirpath) / fn
            p_str = str(fp)
            total_files += 1
            if len(p_str) > len(longest):
                longest = p_str
            if is_reparse_or_link(fp):
                reparse_points.append(p_str)
            else:
                total_bytes += fp.stat().st_size
    return {
        "path": str(base),
        "files": total_files,
        "dirs": total_dirs,
        "bytes": total_bytes,
        "max_path_len": len(longest),
        "longest_path": longest,
        "reparse_points": reparse_points,
    }


def main() -> int:
    if OUT_DIR.exists():
        raise SystemExit(f"refusing to overwrite existing {OUT_DIR}")
    OUT_DIR.mkdir(parents=True)

    protocol, p_sha = load_protocol()
    during_floor = int(protocol["storage"]["free_space"]["during_min_bytes"])

    head_before = git_str("rev-parse", "HEAD")
    status_before = git_str("status", "--porcelain=v1", "-uall")
    if head_before != EXPECTED_HEAD or status_before != "":
        raise SystemExit(f"worktree not clean at {EXPECTED_HEAD}: head={head_before!r} status={status_before!r}")

    parent_env = dict(os.environ)
    check_storage_root(
        ROOT,
        expected_root=protocol["storage"]["root"],
        forbidden_parents=default_forbidden_parents(REPO_ROOT, parent_env),
    )
    if not ROOT.is_dir() or is_reparse_or_link(ROOT):
        raise SystemExit(f"runtime root missing or reparse point: {ROOT}")

    sd = protocol["storage"]["subdirs"]
    for key, rel in sd.items():
        rels = rel if isinstance(rel, list) else [rel]
        for r in rels:
            dp = ROOT / r
            if not dp.is_dir() or is_reparse_or_link(dp):
                raise SystemExit(f"missing or reparse subdir for {key}: {dp}")

    venv_dir = ROOT / sd["venv"]
    venv_py = venv_dir / "Scripts" / "python.exe"
    wheelhouse = ROOT / sd["wheelhouse"]
    req_lock = wheelhouse / "requirements.lock.txt"
    model_dir = ROOT / sd["models"]
    notice_dir = ROOT / sd["notices"]

    wheel_entries_before = sorted(p.name for p in wheelhouse.iterdir())
    if len(wheel_entries_before) != 32 or req_lock.exists():
        raise SystemExit(f"unexpected wheelhouse entries before B.3 ({len(wheel_entries_before)}): {wheel_entries_before}")
    if any(model_dir.iterdir()) or any(notice_dir.iterdir()):
        raise SystemExit("model_dir or notice_dir unexpectedly non-empty before Stage C")

    root_before = walk_inventory(ROOT)
    if root_before["reparse_points"]:
        raise SystemExit(f"reparse points found before resumption: {root_before['reparse_points']}")

    free_before_all = shutil.disk_usage("C:\\").free
    if free_before_all < during_floor:
        raise SystemExit(f"free space {free_before_all} < during floor {during_floor}")

    env_offline = build_stage_env(parent_env, root=ROOT, protocol=protocol, network=False)
    env_network = build_stage_env(parent_env, root=ROOT, protocol=protocol, network=True)
    envs = {
        "host": parent_env,
        "stage_offline": env_offline,
        "stage_network": env_network,
    }

    summary: dict = {
        "schema": "eldq0-stage-b3-d-resumption/1",
        "packet": "WP-0005",
        "sequence": "004",
        "stages_covered": ["B.3", "B.4", "B.5", "B.6", "C.1", "C.2", "D"],
        "started_utc": utc(),
        "repo_root": str(REPO_ROOT),
        "branch": git_str("branch", "--show-current"),
        "head_before": head_before,
        "accepted_core": "41d6204648e4115ab197507d1a22f6d5c7f3e784",
        "harness_tree": git_str("rev-parse", "HEAD:qualification/q0/harness"),
        "status_before": status_before,
        "protocol_sha256": p_sha,
        "lock_sha256": file_digests(LOCK_JSON)["sha256"],
        "manifest_sha256": file_digests(MANIFEST_JSON)["sha256"],
        "install_release": {"path": str(INSTALL_RELEASE), **file_digests(INSTALL_RELEASE, git_blob=True)},
        "wrapper_script": {"name": Path(__file__).name, **file_digests(Path(__file__), git_blob=True)},
        "host_python": sys.version,
        "host_python_executable": str(HOST_PY),
        "platform": platform.platform(),
        "runtime_root": str(ROOT),
        "runtime_root_before": root_before,
        "free_bytes_before_all": free_before_all,
        "during_min_bytes": during_floor,
        "environment_profiles": {
            "host_key_names": sorted(parent_env.keys()),
            "stage_offline": stage_env_sanitized_view(env_offline),
            "stage_network": stage_env_sanitized_view(env_network),
        },
        "steps": [],
    }

    def save_summary() -> None:
        (OUT_DIR / "summary.json").write_bytes((json.dumps(summary, indent=2) + "\n").encode("utf-8"))

    def run_step(name: str, argv: list[str], *, env_profile: str, timeout_s: int = 900, expect_rc: int = 0) -> bytes:
        started = utc()
        t0 = time.monotonic()
        free_b = shutil.disk_usage("C:\\").free
        print(f"[{started}] START {name} ({env_profile}) free={free_b:,} B", flush=True)
        cp = subprocess.run(argv, cwd=REPO_ROOT, env=envs[env_profile], capture_output=True, timeout=timeout_s)
        elapsed = round(time.monotonic() - t0, 3)
        finished = utc()
        free_a = shutil.disk_usage("C:\\").free
        raw = cp.stdout + (b"\n--- stderr ---\n" + cp.stderr if cp.stderr else b"")
        out_file = OUT_DIR / f"{name}.txt"
        with open(out_file, "xb") as f:
            f.write(raw)
        rec = {
            "name": name,
            "env_profile": env_profile,
            "argv": argv,
            "exit_code": cp.returncode,
            "expected_exit_code": expect_rc,
            "started_utc": started,
            "finished_utc": finished,
            "seconds": elapsed,
            "free_bytes_before": free_b,
            "free_bytes_after": free_a,
            "output": out_file.name,
            "output_bytes": len(raw),
            "output_sha256": hashlib.sha256(raw).hexdigest(),
        }
        summary["steps"].append(rec)
        print(f"[{finished}] DONE  {name} rc={cp.returncode} ({elapsed}s) free={free_a:,} B", flush=True)
        if cp.returncode != expect_rc:
            summary["aborted_at_step"] = name
            summary["abort_reason"] = f"unexpected exit_code {cp.returncode} != {expect_rc}"
            summary["finished_utc"] = utc()
            save_summary()
            raise SystemExit(f"STOP at {name}: exit_code={cp.returncode} (see {out_file})")
        if free_a < during_floor:
            summary["aborted_at_step"] = name
            summary["abort_reason"] = f"free_bytes {free_a} < during_min_bytes {during_floor}"
            summary["finished_utc"] = utc()
            save_summary()
            raise SystemExit(f"STOP at {name}: free space {free_a} below floor {during_floor}")
        return cp.stdout

    # Pre-resumption boundary & existing pip-only venv checks
    run_step("01-pre-resume-host-precheck-during",
             [str(HOST_PY), "-I", "-B", str(Q0_PY), "host-precheck", "--stage", "during"],
             env_profile="host")
    run_step("02-pre-resume-status",
             [str(venv_py), "-s", str(Q0_PY), "status"],
             env_profile="stage_offline")
    run_step("02b-pre-resume-pip-version",
             [str(venv_py), "-s", "-m", "pip", "--version"],
             env_profile="stage_offline")
    pip_before_raw = run_step("02c-pre-resume-pip-list",
                              [str(venv_py), "-s", "-m", "pip", "list", "--format=json"],
                              env_profile="stage_offline")
    if json.loads(pip_before_raw.decode("utf-8")) != [{"name": "pip", "version": "25.0.1"}]:
        summary["aborted_at_step"] = "02c-pre-resume-pip-list"
        summary["abort_reason"] = "venv was not pip-25.0.1-only before Stage B.3"
        summary["finished_utc"] = utc()
        save_summary()
        raise SystemExit("STOP: venv was not pip-25.0.1-only before Stage B.3")

    # Stage B.3 - B.6: wheelhouse verification, requirements.lock.txt, offline hash-only install, pip check, path & set check
    run_step("03-stage-b3-verify-wheelhouse",
             [str(venv_py), "-s", str(Q0_PY), "verify-wheelhouse", str(wheelhouse), "--release", str(INSTALL_RELEASE)],
             env_profile="stage_offline")
    run_step("04-stage-b4-write-requirements",
             [str(venv_py), "-s", str(Q0_PY), "write-requirements", str(req_lock), "--release", str(INSTALL_RELEASE)],
             env_profile="stage_offline")
    run_step("05-stage-b5-pip-install-offline",
             [str(venv_py), "-s", "-m", "pip", "install", "--no-index", "--no-deps", "--only-binary=:all:",
              "--require-hashes", "--find-links", str(wheelhouse), "-r", str(req_lock)],
             env_profile="stage_offline",
             timeout_s=1800)
    run_step("06-stage-b5-pip-check",
             [str(venv_py), "-s", "-m", "pip", "check"],
             env_profile="stage_offline")
    pip_after_raw = run_step("06b-stage-b5-installed-pip-list",
                             [str(venv_py), "-s", "-m", "pip", "list", "--format=json"],
                             env_profile="stage_offline")
    pip_after = json.loads(pip_after_raw.decode("utf-8"))
    if len(pip_after) != 33 or {"name": "pip", "version": "25.0.1"} not in pip_after:
        summary["aborted_at_step"] = "06b-stage-b5-installed-pip-list"
        summary["abort_reason"] = f"unexpected post-install pip list count={len(pip_after)}"
        summary["finished_utc"] = utc()
        save_summary()
        raise SystemExit(f"STOP: unexpected post-install pip list count={len(pip_after)}")

    venv_check_code = (
        "import importlib.metadata as md, importlib.util, json, sys; from pathlib import Path; "
        "sys.path.insert(0, sys.argv[1]); "
        "from q0harness import locks; "
        "from q0harness.hostcheck import FS_KEY, LEGACY_MAX_PATH, PATH_MARGIN, max_path_under, read_registry; "
        "repo = Path(sys.argv[2]); venv_dir = Path(sys.argv[3]); "
        "lock = json.loads((Path(sys.argv[1]) / 'locks' / 'dependency-lock.json').read_text(encoding='utf-8')); "
        "pkgs = locks.validate_lock(lock, locks.git_blob_reader(repo)); "
        "inst = locks.verify_installed(pkgs, lock, {d.metadata['Name']: d.version for d in md.distributions()}, "
        "lambda m: importlib.util.find_spec(m) is not None); "
        "mp = max_path_under(venv_dir); lpe = read_registry(FS_KEY, 'LongPathsEnabled'); "
        "limit = LEGACY_MAX_PATH - PATH_MARGIN; "
        "ok = ((lpe or {}).get('value') == 1) or (mp['max_len'] < limit); "
        "assert 'torch' not in sys.modules and 'transformers' not in sys.modules; "
        "out = {'installed_check': inst, 'venv_max_path': mp, 'long_paths_enabled': lpe, "
        "'limit_when_disabled': limit, 'path_ok': ok, "
        "'torch_imported': 'torch' in sys.modules, 'transformers_imported': 'transformers' in sys.modules}; "
        "print(json.dumps(out, indent=2)); sys.exit(0 if ok else 4)"
    )
    run_step("07-stage-b6-venv-max-path-and-set",
             [str(venv_py), "-s", "-P", "-X", "utf8", "-c", venv_check_code,
              str(HARNESS_DIR), str(REPO_ROOT), str(venv_dir)],
             env_profile="stage_offline")
    run_step("08-after-stage-b-host-precheck-during",
             [str(HOST_PY), "-I", "-B", str(Q0_PY), "host-precheck", "--stage", "during"],
             env_profile="host")

    # Stage C: exact 18 runtime objects + separate notice acquisition & verification
    hf_download_code = (
        "import json, sys; from pathlib import Path; from huggingface_hub import snapshot_download; "
        "m = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')); "
        f"r = '{MODEL_REV}'; "
        "md = snapshot_download('baidu/Unlimited-OCR-2', revision=r, local_dir=sys.argv[2], "
        "allow_patterns=[f['path'] for f in m['files']]); "
        "nd = snapshot_download('baidu/Unlimited-OCR-2', revision=r, local_dir=sys.argv[3], "
        "allow_patterns=[n['path'] for n in m['notices']]); "
        "assert 'torch' not in sys.modules and 'transformers' not in sys.modules; "
        "print(json.dumps({'repo_id': 'baidu/Unlimited-OCR-2', 'revision': r, 'model_dir': md, 'notice_dir': nd, "
        "'torch_imported': 'torch' in sys.modules, 'transformers_imported': 'transformers' in sys.modules}, indent=2))"
    )
    run_step("09-stage-c1-model-and-notice-download",
             [str(venv_py), "-s", "-c", hf_download_code, str(MANIFEST_JSON), str(model_dir), str(notice_dir)],
             env_profile="stage_network",
             timeout_s=3600)
    run_step("10-stage-c2-verify-model",
             [str(venv_py), "-s", str(Q0_PY), "verify-model", str(model_dir), "--notices", str(notice_dir)],
             env_profile="stage_offline")
    run_step("11-after-stage-c-host-precheck-during",
             [str(HOST_PY), "-I", "-B", str(Q0_PY), "host-precheck", "--stage", "during"],
             env_profile="host")

    # Stage D: task-venv CPU & 4-page PDFium raster preflight (no torch/model import)
    run_step("12-stage-d-preflight-cpu",
             [str(venv_py), "-s", "-P", "-X", "utf8", str(Q0_PY), "preflight-cpu",
              "--release", str(INSTALL_RELEASE), "--model-dir", str(model_dir), "--notices", str(notice_dir)],
             env_profile="stage_offline")
    run_step("13-after-stage-d-host-precheck-during",
             [str(HOST_PY), "-I", "-B", str(Q0_PY), "host-precheck", "--stage", "during"],
             env_profile="host")
    run_step("14-post-stage-status",
             [str(venv_py), "-s", str(Q0_PY), "status"],
             env_profile="stage_offline")

    # Compact machine inventory of C:\Users\jackg\eLedgerCare-Q0\WP-0005
    lpe_now = read_registry(FS_KEY, "LongPathsEnabled")
    root_inv = walk_inventory(ROOT)
    by_top_subdir = {
        p.name: walk_inventory(p)
        for p in sorted(ROOT.iterdir(), key=lambda x: x.name)
        if p.is_dir()
    }
    venv_max = max_path_under(venv_dir)
    root_max = max_path_under(ROOT)
    if (lpe_now or {}).get("value") != 1 and root_max["max_len"] >= LEGACY_MAX_PATH - PATH_MARGIN:
        summary["aborted_at_step"] = "15-resource-inventory"
        summary["abort_reason"] = f"root max path {root_max['max_len']} >= {LEGACY_MAX_PATH - PATH_MARGIN}"
        summary["finished_utc"] = utc()
        save_summary()
        raise SystemExit(f"STOP: root max path {root_max['max_len']} >= {LEGACY_MAX_PATH - PATH_MARGIN}")
    if root_inv["reparse_points"]:
        summary["aborted_at_step"] = "15-resource-inventory"
        summary["abort_reason"] = f"reparse points found under root: {root_inv['reparse_points']}"
        summary["finished_utc"] = utc()
        save_summary()
        raise SystemExit(f"STOP: reparse points found under root: {root_inv['reparse_points']}")

    inv_doc = {
        "schema": "eldq0-runtime-root-inventory/1",
        "observed_utc": utc(),
        "root": root_inv,
        "venv_max_path": venv_max,
        "root_max_path": root_max,
        "long_paths_enabled": lpe_now,
        "requirements_lock_txt": file_digests(req_lock, git_blob=True),
        "subdirs": by_top_subdir,
        "free_bytes_after_all": shutil.disk_usage("C:\\").free,
    }
    inv_bytes = (json.dumps(inv_doc, indent=2) + "\n").encode("utf-8")
    (OUT_DIR / "15-resource-inventory.json").write_bytes(inv_bytes)

    head_after = git_str("rev-parse", "HEAD")
    status_after = git_str("status", "--porcelain=v1", "-uall")
    if head_after != EXPECTED_HEAD or status_after != "":
        summary["aborted_at_step"] = "post-worktree-check"
        summary["abort_reason"] = f"worktree mutated during execution: head={head_after!r} status={status_after!r}"
        summary["finished_utc"] = utc()
        save_summary()
        raise SystemExit(f"STOP: worktree mutated during execution: head={head_after!r} status={status_after!r}")

    summary.update({
        "status": "pass",
        "head_after": head_after,
        "status_after": status_after,
        "head_unchanged_throughout": True,
        "runtime_root_after": root_inv,
        "venv_max_path": venv_max,
        "root_max_path": root_max,
        "free_bytes_after_all": inv_doc["free_bytes_after_all"],
        "resource_inventory_file": "15-resource-inventory.json",
        "resource_inventory_bytes": len(inv_bytes),
        "resource_inventory_sha256": hashlib.sha256(inv_bytes).hexdigest(),
        "finished_utc": utc(),
    })
    save_summary()
    print(json.dumps({
        "status": "pass",
        "steps": len(summary["steps"]),
        "venv_max_path_len": venv_max["max_len"],
        "root_max_path_len": root_max["max_len"],
        "root_files": root_inv["files"],
        "root_bytes": root_inv["bytes"],
        "free_bytes_after": inv_doc["free_bytes_after_all"],
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
