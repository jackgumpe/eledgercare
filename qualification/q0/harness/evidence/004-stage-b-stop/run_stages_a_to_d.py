"""Small operational wrapper for accepted WP-0005 /004 Stages A-D (no GPU, no torch import).

Runs entirely from `.scratch/004-staging/` while keeping the executing worktree clean at
`460e1d81de14c6f77ea4a026bc4b3ab36407bdf7`. Invokes the accepted `q0.py`, `venv`, `pip`,
and `huggingface_hub.snapshot_download` commands under their designated environments:
- `host` (normal operator environment): read-only `q0.py host-precheck --stage during`
- `stage_network` (`build_stage_env(..., network=True)`): wheel and model acquisition workers
- `stage_offline` (`build_stage_env(..., network=False)`): `venv`, `verify-wheelhouse`,
  `write-requirements`, offline hash-only `pip install`, `pip check`, `verify-model`,
  `preflight-cpu`, `status`, and path-length checks.

Stops immediately on the first non-zero exit code, free-space floor breach, or path-length
violation without silent retries or source patches.
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
REPO_ROOT = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness")
HARNESS_DIR = REPO_ROOT / "qualification" / "q0" / "harness"
Q0_PY = HARNESS_DIR / "q0.py"
MANIFEST_JSON = HARNESS_DIR / "manifests" / "model-files.json"
HOST_PY = Path(r"C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe")
ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")
INSTALL_RELEASE = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare\docs\coordination\WP-0005\releases\author-install.json")
STORAGE_RECEIPT = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare\docs\coordination\WP-0005\acquisition-release\storage-created.json")
WHEEL_WORKER = HERE / "download_wheels_worker.py"
EXPECTED_HEAD = "460e1d81de14c6f77ea4a026bc4b3ab36407bdf7"

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


def env_keys_without_secrets(env: dict[str, str]) -> list[str]:
    return sorted(env.keys())


def stage_env_sanitized_view(env: dict[str, str]) -> dict[str, str]:
    out = {}
    for k in sorted(env):
        if any(rx.search(k) for rx in FORBIDDEN_PATTERNS):
            out[k] = "<REDACTED>"
        else:
            out[k] = env[k]
    return out


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
    out_dir = HERE / "outputs"
    if out_dir.exists():
        raise SystemExit(f"refusing to overwrite existing {out_dir}")
    out_dir.mkdir(parents=True)

    protocol, p_sha = load_protocol()
    initial_floor = int(protocol["storage"]["free_space"]["initial_min_bytes"])
    during_floor = int(protocol["storage"]["free_space"]["during_min_bytes"])

    head_before = git_str("rev-parse", "HEAD")
    status_before = git_str("status", "--porcelain=v1", "-uall")
    if head_before != EXPECTED_HEAD or status_before != "":
        raise SystemExit(f"worktree not clean at {EXPECTED_HEAD}: head={head_before!r} status={status_before!r}")
    if not ROOT.is_dir() or is_reparse_or_link(ROOT):
        raise SystemExit(f"runtime root missing or reparse point: {ROOT}")
    initial_entries = [p.name for p in ROOT.iterdir()]
    if initial_entries:
        raise SystemExit(f"runtime root not empty before Stage A: {initial_entries}")

    free_initial = shutil.disk_usage("C:\\").free
    if free_initial < initial_floor:
        raise SystemExit(f"free space {free_initial} < initial floor {initial_floor}")

    parent_env = dict(os.environ)
    env_offline = build_stage_env(parent_env, root=ROOT, protocol=protocol, network=False)
    env_network = build_stage_env(parent_env, root=ROOT, protocol=protocol, network=True)
    envs = {
        "host": parent_env,
        "stage_offline": env_offline,
        "stage_network": env_network,
    }

    summary: dict = {
        "schema": "eldq0-stage-a-d-execution/1",
        "packet": "WP-0005",
        "sequence": "004",
        "stages_covered": ["A", "B", "C", "D"],
        "started_utc": utc(),
        "repo_root": str(REPO_ROOT),
        "branch": git_str("branch", "--show-current"),
        "head_before": head_before,
        "status_before": status_before,
        "protocol_sha256": p_sha,
        "install_release": {"path": str(INSTALL_RELEASE), **file_digests(INSTALL_RELEASE, git_blob=True)},
        "storage_creation_receipt": {"path": str(STORAGE_RECEIPT), **file_digests(STORAGE_RECEIPT, git_blob=True)},
        "wrapper_script": {"name": Path(__file__).name, **file_digests(Path(__file__), git_blob=True)},
        "wheel_worker_script": {"name": WHEEL_WORKER.name, **file_digests(WHEEL_WORKER, git_blob=True)},
        "host_python": sys.version,
        "host_python_executable": str(HOST_PY),
        "platform": platform.platform(),
        "runtime_root": str(ROOT),
        "runtime_root_reparse_before": is_reparse_or_link(ROOT),
        "runtime_root_initial_entries": initial_entries,
        "free_bytes_before_all": free_initial,
        "floors": {"initial_min_bytes": initial_floor, "during_min_bytes": during_floor},
        "environment_profiles": {
            "host_key_names": env_keys_without_secrets(parent_env),
            "stage_offline": stage_env_sanitized_view(env_offline),
            "stage_network": stage_env_sanitized_view(env_network),
        },
        "steps": [],
    }

    def save_summary() -> None:
        (out_dir / "summary.json").write_bytes((json.dumps(summary, indent=2) + "\n").encode("utf-8"))

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
        out_file = out_dir / f"{name}.txt"
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

    # Pre-stage boundary checks
    run_step("01-pre-stage-host-precheck-during",
             [str(HOST_PY), "-I", "-B", str(Q0_PY), "host-precheck", "--stage", "during"],
             env_profile="host")
    run_step("02-pre-stage-status",
             [str(HOST_PY), "-I", "-B", str(Q0_PY), "status"],
             env_profile="stage_offline")

    # Stage A: create owned directory layout from protocol.json storage.subdirs
    t_a0, s_a0 = time.monotonic(), utc()
    free_a0 = shutil.disk_usage("C:\\").free
    check_storage_root(ROOT, expected_root=protocol["storage"]["root"],
                       forbidden_parents=default_forbidden_parents(REPO_ROOT, parent_env))
    sd = protocol["storage"]["subdirs"]
    created_dirs: list[str] = []
    for key, rel in sd.items():
        if key == "venv":
            continue  # created by `python -m venv` in Stage B.1
        rels = rel if isinstance(rel, list) else [rel]
        for r in rels:
            target = ROOT / r
            target.mkdir(parents=True, exist_ok=False)
            if is_reparse_or_link(target):
                raise SystemExit(f"reparse point detected at {target}")
            created_dirs.append(str(target))
    stage_a_bytes = (json.dumps({"created_dirs": created_dirs, "root_checked": str(ROOT)}, indent=2) + "\n").encode("utf-8")
    (out_dir / "03-stage-a-layout.txt").write_bytes(stage_a_bytes)
    free_a1 = shutil.disk_usage("C:\\").free
    summary["steps"].append({
        "name": "03-stage-a-layout",
        "env_profile": "in_process_stdlib",
        "argv": ["mkdir_owned_layout_from_protocol_subdirs"],
        "exit_code": 0,
        "expected_exit_code": 0,
        "started_utc": s_a0,
        "finished_utc": utc(),
        "seconds": round(time.monotonic() - t_a0, 3),
        "free_bytes_before": free_a0,
        "free_bytes_after": free_a1,
        "output": "03-stage-a-layout.txt",
        "output_bytes": len(stage_a_bytes),
        "output_sha256": hashlib.sha256(stage_a_bytes).hexdigest(),
    })

    run_step("04-after-stage-a-host-precheck-during",
             [str(HOST_PY), "-I", "-B", str(Q0_PY), "host-precheck", "--stage", "during"],
             env_profile="host")

    # Stage B: venv, exact 32 wheels, verify-wheelhouse, write-requirements, offline install, pip check, max_path
    venv_dir = ROOT / sd["venv"]
    venv_py = venv_dir / "Scripts" / "python.exe"
    wheelhouse = ROOT / sd["wheelhouse"]
    req_lock = wheelhouse / "requirements.lock.txt"

    run_step("05-stage-b-venv-create",
             [str(HOST_PY), "-m", "venv", str(venv_dir)],
             env_profile="stage_offline")
    run_step("06-stage-b-bundled-pip-version",
             [str(venv_py), "-s", "-m", "pip", "--version"],
             env_profile="stage_offline")
    run_step("06b-stage-b-initial-pip-list",
             [str(venv_py), "-s", "-m", "pip", "list", "--format=json"],
             env_profile="stage_offline")
    run_step("07-stage-b-download-wheels",
             [str(venv_py), "-s", "-P", "-X", "utf8", str(WHEEL_WORKER), str(HARNESS_DIR), str(REPO_ROOT), str(wheelhouse)],
             env_profile="stage_network",
             timeout_s=3600)
    run_step("08-stage-b-verify-wheelhouse",
             [str(venv_py), "-s", str(Q0_PY), "verify-wheelhouse", str(wheelhouse), "--release", str(INSTALL_RELEASE)],
             env_profile="stage_offline")
    run_step("09-stage-b-write-requirements",
             [str(venv_py), "-s", str(Q0_PY), "write-requirements", str(req_lock), "--release", str(INSTALL_RELEASE)],
             env_profile="stage_offline")
    run_step("10-stage-b-pip-install-offline",
             [str(venv_py), "-s", "-m", "pip", "install", "--no-index", "--no-deps", "--only-binary=:all:",
              "--require-hashes", "--find-links", str(wheelhouse), "-r", str(req_lock)],
             env_profile="stage_offline",
             timeout_s=1800)
    run_step("11-stage-b-pip-check",
             [str(venv_py), "-s", "-m", "pip", "check"],
             env_profile="stage_offline")
    run_step("11b-stage-b-installed-pip-list",
             [str(venv_py), "-s", "-m", "pip", "list", "--format=json"],
             env_profile="stage_offline")

    max_path_code = (
        "import json, sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); "
        "from q0harness.hostcheck import FS_KEY, LEGACY_MAX_PATH, PATH_MARGIN, max_path_under, read_registry; "
        "r = max_path_under(Path(sys.argv[2])); lpe = read_registry(FS_KEY, 'LongPathsEnabled'); "
        "r['long_paths_enabled'] = lpe; r['limit_when_disabled'] = LEGACY_MAX_PATH - PATH_MARGIN; "
        "ok = ((lpe or {}).get('value') == 1) or (r['max_len'] < LEGACY_MAX_PATH - PATH_MARGIN); "
        "r['pass'] = ok; print(json.dumps(r, indent=2)); sys.exit(0 if ok else 4)"
    )
    run_step("12-stage-b-venv-max-path",
             [str(venv_py), "-s", "-P", "-X", "utf8", "-c", max_path_code, str(HARNESS_DIR), str(venv_dir)],
             env_profile="stage_offline")
    run_step("13-after-stage-b-host-precheck-during",
             [str(HOST_PY), "-I", "-B", str(Q0_PY), "host-precheck", "--stage", "during"],
             env_profile="host")

    # Stage C: pinned 18 model runtime objects + separate notice download & byte verification
    model_dir = ROOT / sd["models"]
    notice_dir = ROOT / sd["notices"]
    hf_download_code = (
        "import json, sys; from pathlib import Path; from huggingface_hub import snapshot_download; "
        "m = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')); "
        "r = '0480966938291445591f69f08a13b041c073a96a'; "
        "md = snapshot_download('baidu/Unlimited-OCR-2', revision=r, local_dir=sys.argv[2], "
        "allow_patterns=[f['path'] for f in m['files']]); "
        "nd = snapshot_download('baidu/Unlimited-OCR-2', revision=r, local_dir=sys.argv[3], "
        "allow_patterns=[n['path'] for n in m['notices']]); "
        "assert 'torch' not in sys.modules and 'transformers' not in sys.modules; "
        "print(json.dumps({'revision': r, 'model_dir': md, 'notice_dir': nd, "
        "'torch_imported': 'torch' in sys.modules, 'transformers_imported': 'transformers' in sys.modules}, indent=2))"
    )
    run_step("14-stage-c-model-download",
             [str(venv_py), "-s", "-c", hf_download_code, str(MANIFEST_JSON), str(model_dir), str(notice_dir)],
             env_profile="stage_network",
             timeout_s=3600)
    run_step("15-stage-c-verify-model",
             [str(venv_py), "-s", str(Q0_PY), "verify-model", str(model_dir), "--notices", str(notice_dir)],
             env_profile="stage_offline")
    run_step("16-after-stage-c-host-precheck-during",
             [str(HOST_PY), "-I", "-B", str(Q0_PY), "host-precheck", "--stage", "during"],
             env_profile="host")

    # Stage D: real task-venv preflight-cpu (installed set, PDFium 159.0.8149.0, 4-page RGB rasters, model/notice/static)
    run_step("17-stage-d-preflight-cpu",
             [str(venv_py), "-s", "-P", "-X", "utf8", str(Q0_PY), "preflight-cpu",
              "--release", str(INSTALL_RELEASE), "--model-dir", str(model_dir), "--notices", str(notice_dir)],
             env_profile="stage_offline")
    run_step("18-after-stage-d-host-precheck-during",
             [str(HOST_PY), "-I", "-B", str(Q0_PY), "host-precheck", "--stage", "during"],
             env_profile="host")
    run_step("19-post-stage-status",
             [str(HOST_PY), "-I", "-B", str(Q0_PY), "status"],
             env_profile="stage_offline")

    # Compact machine byte/path/reparse inventory of C:\Users\jackg\eLedgerCare-Q0\WP-0005
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
        raise SystemExit(f"root max path {root_max['max_len']} >= {LEGACY_MAX_PATH - PATH_MARGIN}")
    if root_inv["reparse_points"]:
        raise SystemExit(f"reparse points found under root: {root_inv['reparse_points']}")

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
    (out_dir / "20-resource-inventory.json").write_bytes(inv_bytes)

    head_after = git_str("rev-parse", "HEAD")
    status_after = git_str("status", "--porcelain=v1", "-uall")
    summary.update({
        "status": "pass",
        "head_after": head_after,
        "status_after": status_after,
        "head_unchanged_throughout": head_after == EXPECTED_HEAD and status_after == "",
        "free_bytes_after_all": inv_doc["free_bytes_after_all"],
        "resource_inventory_file": "20-resource-inventory.json",
        "resource_inventory_sha256": hashlib.sha256(inv_bytes).hexdigest(),
        "resource_inventory_bytes": len(inv_bytes),
        "finished_utc": utc(),
    })
    save_summary()
    print(json.dumps({"status": "pass", "steps": len(summary["steps"]), "free_bytes_after": inv_doc["free_bytes_after_all"]}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
