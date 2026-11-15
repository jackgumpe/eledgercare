"""Read-only post-stop boundary snapshot after fail-closed stop at 08-stage-b-verify-wheelhouse.

Executed while worktree HEAD remains clean at 460e1d81de14c6f77ea4a026bc4b3ab36407bdf7.
Captures:
- `09-post-stop-host-precheck-during.txt` (normal host env)
- `10-post-stop-status.txt` (`stage_offline` env)
- `11-post-stop-resource-inventory.json` (exact byte/path/reparse state of `C:\\Users\\jackg\\eLedgerCare-Q0\\WP-0005` and `venv` installed distributions)
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "outputs"
REPO_ROOT = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness")
HARNESS_DIR = REPO_ROOT / "qualification" / "q0" / "harness"
Q0_PY = HARNESS_DIR / "q0.py"
HOST_PY = Path(r"C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe")
ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")
VENV_PY = ROOT / "venv" / "Scripts" / "python.exe"

sys.path.insert(0, str(HARNESS_DIR))
from q0harness.environment import build_stage_env  # noqa: E402
from q0harness.hostcheck import FS_KEY, max_path_under, read_registry  # noqa: E402
from q0harness.modelfiles import is_reparse_or_link  # noqa: E402
from q0harness.protocol import load_protocol  # noqa: E402


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


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
    protocol, _ = load_protocol()
    env_offline = build_stage_env(dict(os.environ), root=ROOT, protocol=protocol, network=False)

    cp_hp = subprocess.run(
        [str(HOST_PY), "-I", "-B", str(Q0_PY), "host-precheck", "--stage", "during"],
        cwd=REPO_ROOT, env=dict(os.environ), capture_output=True, timeout=120,
    )
    hp_bytes = cp_hp.stdout + (b"\n--- stderr ---\n" + cp_hp.stderr if cp_hp.stderr else b"")
    (OUT_DIR / "09-post-stop-host-precheck-during.txt").write_bytes(hp_bytes)

    cp_st = subprocess.run(
        [str(HOST_PY), "-I", "-B", str(Q0_PY), "status"],
        cwd=REPO_ROOT, env=env_offline, capture_output=True, timeout=120,
    )
    st_bytes = cp_st.stdout + (b"\n--- stderr ---\n" + cp_st.stderr if cp_st.stderr else b"")
    (OUT_DIR / "10-post-stop-status.txt").write_bytes(st_bytes)

    cp_pip = subprocess.run(
        [str(VENV_PY), "-s", "-m", "pip", "list", "--format=json"],
        cwd=REPO_ROOT, env=env_offline, capture_output=True, text=True, timeout=120,
    )

    root_inv = walk_inventory(ROOT)
    by_sub = {
        p.name: walk_inventory(p)
        for p in sorted(ROOT.iterdir(), key=lambda x: x.name)
        if p.is_dir()
    }
    inv = {
        "schema": "eldq0-post-stop-resource-inventory/1",
        "observed_utc": utc(),
        "post_stop_host_precheck_rc": cp_hp.returncode,
        "post_stop_host_precheck_sha256": hashlib.sha256(hp_bytes).hexdigest(),
        "post_stop_status_rc": cp_st.returncode,
        "post_stop_status_sha256": hashlib.sha256(st_bytes).hexdigest(),
        "venv_pip_list_after_stop": json.loads(cp_pip.stdout),
        "wheelhouse_installed_into_venv": False,
        "model_or_notice_files_downloaded": False,
        "torch_or_transformers_or_pypdfium2_imported": False,
        "gpu_context_created": False,
        "long_paths_enabled": read_registry(FS_KEY, "LongPathsEnabled"),
        "venv_max_path": max_path_under(ROOT / "venv"),
        "root_max_path": max_path_under(ROOT),
        "root": root_inv,
        "subdirs": by_sub,
        "free_bytes_after_stop": shutil.disk_usage("C:\\").free,
    }
    inv_bytes = (json.dumps(inv, indent=2) + "\n").encode("utf-8")
    (OUT_DIR / "11-post-stop-resource-inventory.json").write_bytes(inv_bytes)
    print(json.dumps({
        "hp_rc": cp_hp.returncode,
        "st_rc": cp_st.returncode,
        "venv_pip_list": inv["venv_pip_list_after_stop"],
        "root_files": root_inv["files"],
        "root_bytes": root_inv["bytes"],
        "reparse_points": root_inv["reparse_points"],
        "root_max_path_len": inv["root_max_path"]["max_len"],
        "free_bytes_after_stop": inv["free_bytes_after_stop"],
        "subdirs_bytes": {k: {"files": v["files"], "bytes": v["bytes"]} for k, v in by_sub.items()},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
