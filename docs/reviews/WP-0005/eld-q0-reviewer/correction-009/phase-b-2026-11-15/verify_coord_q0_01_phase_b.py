"""WP-0005 /009 Phase B independent reviewer verification helper (stdlib-only, CPU-only).

Author: eld-q0-reviewer (Gemini 4 Carbon (High), conversation 0815536f-045a-4112-8a89-ebf0e0cc782f)
Target candidate: 24a5866b505532fd03e7db62a4e57875e4c5a170 (parent 2a52ea58fae2badcb4e9ef47d1cb416c006edca4)
Author evidence:  b70ff45f2c7aa4b2e454429e76a15fa09887fa9d
Author /008 tip:  460e1d81de14c6f77ea4a026bc4b3ab36407bdf7

Independently verifies on merged /008 publication:
  1. Exact 14-file source diff (2a52ea58..24a5866b), 18-file /008 evidence diff (24a5866b..b70ff45f),
     1-file /008 report diff (b70ff45f..460e1d81), zero core harness diffs between 24a5866b and HEAD,
     and byte-for-byte preservation of protocol.json, dependency-lock.json, model-files.json,
     research/**, evaluation/**, prior evidence/reports (/002, /003, Opus pre-execution, Phase A),
     plus direct measurement of Phase A summary.json actual byte size (10,039 vs README 8,370).
  2. Full stdlib unittest discovery suite (80 tests: 79 passed, 1 Windows symlink privilege skip).
  3. Real OS child Python subprocesses across all 4 isolated environments
     (build_stage_env network=False/True, build_child_env author/reviewer) and both flag sets
     ([-I, -B] and [-s, -P, -X, utf8]) with outside-worktree cwd and absent external root:
       - PATH remains restricted (shutil.which('git') is None; no Git directory on PATH);
       - Q0_GIT_EXECUTABLE pins validated host git.exe outside task root;
       - GIT_CONFIG_NOSYSTEM=1, GIT_CONFIG_GLOBAL=NUL, GIT_TERMINAL_PROMPT=0 scrub global/system
         Git config (proven via `run_git config --list --show-origin`);
       - Parent credentials, model switches, and Git overrides (GIT_DIR, GIT_WORK_TREE,
         GIT_ASKPASS, SSH_AUTH_SOCK, GIT_CONFIG_PARAMETERS) are stripped;
       - Live release.code_identity and locks.git_blob_reader / validate_lock succeed.
  4. Real q0.py CLI subprocesses inside isolated stage and child environments (status,
     lock-check, check-protocol, host-precheck --stage initial, and fail-closed release gates).
  5. Negative/adversarial real-subprocess fail-closed probes:
       - Stripped Q0_GIT_EXECUTABLE;
       - Non-existent Q0_GIT_EXECUTABLE path;
       - Corrupt non-PE git.exe binary triggering CreateProcess OSError [WinError 193];
       - Mutable-root git.exe and altered GIT_ISOLATION_ENV rejected by audit_stage_env / audit_child_env;
       - Direct `q0.py child` (cmd_child) live code_identity verification, parent/child TOCTOU
         mismatch detection, broken-Git fail-closed handling, and live child lock blob reading
         without creating C:\\Users\\jackg\\eLedgerCare-Q0 or importing torch.
  6. Heartbeat thread-serialization, real Windows concurrent file-reader contention stress,
     bounded PermissionError retry/exhaustion, and tight-polled (poll_s=0.02) supervised child
     Session execution (explicitly distinguishing synthetic FakeBackend from real GPU runtime).
  7. Audit of published /008 author evidence (b70ff45f) and /008 report narrative reconciliations
     (F01=3,482 B / F07=8,422 B; Heartbeat 5 attempts with 4 sleeps of 10/20/30/40 ms = 100 ms max).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[6]
HARNESS_DIR = REPO_ROOT / "qualification" / "q0" / "harness"
Q0_PY = HARNESS_DIR / "q0.py"
assert Q0_PY.is_file(), f"unexpected REPO_ROOT={REPO_ROOT}"

CANDIDATE_002 = "84cef5ef30685ffee46281fefc5fd1356dbc1876"
CANDIDATE_COMMIT = "24a5866b505532fd03e7db62a4e57875e4c5a170"
CANDIDATE_PARENT = "2a52ea58fae2badcb4e9ef47d1cb416c006edca4"
AUTHOR_EVIDENCE_008 = "b70ff45f2c7aa4b2e454429e76a15fa09887fa9d"
AUTHOR_REPORT_008 = "460e1d81de14c6f77ea4a026bc4b3ab36407bdf7"
CONTINUATION_BASE = "ca81c44ed3114439036a2e95e2c20d6f6d5f7500"

EXPECTED_DIFF = {
    "qualification/q0/harness/ACQUISITION.md": "M",
    "qualification/q0/harness/PROTOCOL.md": "M",
    "qualification/q0/harness/README.md": "M",
    "qualification/q0/harness/q0.py": "M",
    "qualification/q0/harness/q0harness/environment.py": "M",
    "qualification/q0/harness/q0harness/hostcheck.py": "M",
    "qualification/q0/harness/q0harness/locks.py": "M",
    "qualification/q0/harness/q0harness/release.py": "M",
    "qualification/q0/harness/q0harness/session.py": "M",
    "qualification/q0/harness/tests/test_environment_writer_memory.py": "M",
    "qualification/q0/harness/tests/test_host_model_env.py": "M",
    "qualification/q0/harness/tests/test_isolated_git_subprocess.py": "A",
    "qualification/q0/harness/tests/test_locks_preflight.py": "M",
    "qualification/q0/harness/tests/test_session.py": "M",
}

EXPECTED_FROZEN_INPUTS = {
    "qualification/q0/harness/protocol.json": (
        11885,
        "dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309",
    ),
    "qualification/q0/harness/locks/dependency-lock.json": (
        6461,
        "d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e",
    ),
    "qualification/q0/harness/manifests/model-files.json": (
        3986,
        "085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8",
    ),
}

if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))

from q0harness import locks  # noqa: E402
from q0harness.environment import (  # noqa: E402
    GIT_EXECUTABLE_VAR,
    GIT_ISOLATION_ENV,
    audit_child_env,
    audit_stage_env,
    build_child_env,
    build_stage_env,
    default_forbidden_parents,
    layout,
)
from q0harness.hashing import sha256_bytes  # noqa: E402
from q0harness.outcome import QUALIFIED, Q0Failure  # noqa: E402
from q0harness.protocol import load_protocol  # noqa: E402
from q0harness.release import code_identity  # noqa: E402
from q0harness.session import Heartbeat  # noqa: E402
from q0harness.supervisor import _read_heartbeat, supervise  # noqa: E402


def load_lock_git_blobs() -> list[str]:
    lock = json.loads((HARNESS_DIR / "locks" / "dependency-lock.json").read_text(encoding="utf-8"))
    return [
        lock["source"]["git_blob"],
        lock["metadata_digest_source"]["git_blob"],
        lock["local_hash_records"][0]["receipt"]["git_blob"],
    ]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def host_git(*args: str, binary: bool = False) -> subprocess.CompletedProcess:
    cp = subprocess.run(
        ["git", "--no-optional-locks", *args],
        cwd=str(REPO_ROOT),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=not binary,
        timeout=60,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"git {args} failed ({cp.returncode}): {cp.stderr}")
    return cp


def write_bytes_recorded(out_dir: Path, name: str, data: bytes, inventory: list[dict]) -> Path:
    p = out_dir / name
    p.write_bytes(data)
    inventory.append({
        "file": name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    })
    return p


def write_json_recorded(out_dir: Path, name: str, obj: dict, inventory: list[dict]) -> Path:
    raw = (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return write_bytes_recorded(out_dir, name, raw, inventory)


def polluted_parent_env(scratch: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.update({
        "HF_TOKEN": "leak-hf-token",
        "HUGGING_FACE_HUB_TOKEN": "leak-hub-token",
        "OPENAI_API_KEY": "leak-openai-key",
        "ANTHROPIC_API_KEY": "leak-anthropic-key",
        "GITHUB_TOKEN": "leak-gh-token",
        "DASH_STAGE0": "indexer",
        "KL_QUERY_STRIDE": "8",
        "TIME_DIAG": "1",
        "PYTHONPATH": str(scratch / "untrusted-pythonpath"),
        "PIP_INDEX_URL": "https://untrusted.invalid/simple",
        "GIT_DIR": str(scratch / "hijack.git"),
        "GIT_WORK_TREE": str(scratch / "hijack-wt"),
        "GIT_ASKPASS": str(scratch / "askpass.bat"),
        "SSH_AUTH_SOCK": str(scratch / "ssh.sock"),
        "GIT_CONFIG_PARAMETERS": "'core.sshCommand=evil'",
        "GCM_INTERACTIVE": "always",
    })
    return env


CHILD_GIT_MATRIX_PROBE = textwrap.dedent("""
    import json, os, shutil, sys
    from pathlib import Path

    harness_dir = Path(sys.argv[1])
    repo_root = Path(sys.argv[2])
    blobs = json.loads(sys.argv[3])
    sys.path.insert(0, str(harness_dir))

    from q0harness import locks
    from q0harness.environment import GIT_EXECUTABLE_VAR, GIT_ISOLATION_ENV, run_git
    from q0harness.hashing import git_blob_sha1_bytes
    from q0harness.release import code_identity

    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    cfg_cp = run_git(("config", "--list", "--show-origin"), cwd=repo_root, text=True)
    cfg_origins = sorted({
        line.split("\\t", 1)[0]
        for line in cfg_cp.stdout.splitlines()
        if "\\t" in line
    })

    leaked = sorted(k for k in os.environ if k in {
        "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
        "GITHUB_TOKEN", "DASH_STAGE0", "KL_QUERY_STRIDE", "TIME_DIAG", "PYTHONPATH",
        "PIP_INDEX_URL", "GIT_DIR", "GIT_WORK_TREE", "GIT_ASKPASS", "SSH_AUTH_SOCK",
        "GIT_CONFIG_PARAMETERS", "GCM_INTERACTIVE",
    })

    reader = locks.git_blob_reader(repo_root)
    blob_checks = {}
    for oid in blobs:
        raw = reader(oid)
        blob_checks[oid] = {
            "bytes": len(raw),
            "git_blob_sha1_ok": git_blob_sha1_bytes(raw) == oid,
        }

    lock = locks.load_lock(harness_dir / "locks" / "dependency-lock.json")
    pkgs = locks.validate_lock(lock, reader)
    r = locks.readiness(pkgs)

    print(json.dumps({
        "cwd": os.getcwd(),
        "path_entries": path_entries,
        "git_on_path": shutil.which("git"),
        "any_git_dir_on_path": any("git" in p.lower() for p in path_entries),
        "git_executable_var": os.environ.get(GIT_EXECUTABLE_VAR),
        "git_isolation_env": {k: os.environ.get(k) for k in GIT_ISOLATION_ENV},
        "git_config_rc": cfg_cp.returncode,
        "git_config_origins": cfg_origins,
        "leaked_parent_keys": leaked,
        "code_identity": code_identity(repo_root),
        "blob_checks": blob_checks,
        "lock_readiness": {
            "artifacts": len(pkgs),
            "counts": r["counts"],
            "installable": r["installable"],
            "total_graph_edges": sum(len(a["graph_requires"]) for a in pkgs.values()),
            "torchvision_receipt_ok": all(pkgs["torchvision"]["receipt_checks"].values()),
        },
    }))
""")


NEGATIVE_GIT_PROBE = textwrap.dedent("""
    import json, sys
    from pathlib import Path

    harness_dir = Path(sys.argv[1])
    repo_root = Path(sys.argv[2])
    oid = sys.argv[3]
    sys.path.insert(0, str(harness_dir))

    from q0harness import locks
    from q0harness.release import code_identity

    out = {}
    try:
        out["code_identity"] = code_identity(repo_root)
    except Exception as exc:
        out["code_error"] = {
            "type": type(exc).__name__,
            "failure_class": getattr(exc, "failure_class", None),
            "detail": getattr(exc, "detail", str(exc)),
        }
    try:
        data = locks.git_blob_reader(repo_root)(oid)
        out["blob_bytes"] = len(data)
    except Exception as exc:
        out["blob_error"] = {
            "type": type(exc).__name__,
            "failure_class": getattr(exc, "failure_class", None),
            "detail": getattr(exc, "detail", str(exc)),
        }
    print(json.dumps(out))
""")


SUPERVISED_REVIEWER_CHILD = textwrap.dedent("""
    import json, os, sys, uuid
    from pathlib import Path

    harness_dir, repo_root, root, run_dir = (
        Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    )
    sys.path.insert(0, str(harness_dir))
    sys.path.insert(0, str(harness_dir / "tests"))

    import support
    from q0harness import locks
    from q0harness.environment import audit_child_env
    from q0harness.hashing import sha256_bytes
    from q0harness.protocol import load_protocol
    from q0harness.release import code_identity
    from q0harness.session import Session

    audit_child_env(dict(os.environ), root=root, owner="reviewer", run_dir=run_dir)
    protocol, p_sha = load_protocol()
    lock_raw = (harness_dir / "locks" / "dependency-lock.json").read_bytes()
    lock = json.loads(lock_raw)
    live_code = code_identity(repo_root)
    reader = locks.git_blob_reader(repo_root)
    pkgs = locks.validate_lock(lock, reader)
    installed = {a["name"]: a["version"] for a in pkgs.values()}

    model_dir = root / protocol["storage"]["subdirs"]["models"]
    support.write_fake_model_dir(model_dir)
    support.write_notice_dir(root / protocol["storage"]["subdirs"]["notices"])
    manifest_path = run_dir / "model-files-synthetic.json"
    manifest_path.write_text(json.dumps(support.manifest_for_dir(model_dir)), encoding="utf-8")

    rel = support.fake_release(protocol, p_sha, sha256_bytes(lock_raw), root, owner="reviewer")
    rel["harness_commit"] = live_code["head"]

    backend = support.FakeBackend(
        protocol,
        pkg=f"reviewer_subproc_{uuid.uuid4().hex[:8]}",
        model_dir=model_dir,
        modules_cache=Path(os.environ["HF_MODULES_CACHE"]),
        installed=installed,
    )
    session = Session(
        protocol=protocol,
        protocol_sha256=p_sha,
        lock=lock,
        lock_sha256=sha256_bytes(lock_raw),
        release=rel,
        root=root,
        owner="reviewer",
        run_dir=run_dir,
        backend=backend,
        repo_root=repo_root,
        expected_root=str(root),
        forbidden_parents=[],
        code=live_code,
        lock_reader=reader,
        manifest_path=manifest_path,
    )
    outcome = session.run()
    (run_dir / "reviewer-child-summary.json").write_text(
        json.dumps({
            "backend_kind": "synthetic_FakeBackend_no_torch_no_gpu",
            "live_code_identity": live_code,
            "artifacts_verified": len(pkgs),
            "outcome_status": outcome["status"],
            "observations": len(outcome["observations"]),
        }),
        encoding="utf-8",
    )
    sys.exit(0 if outcome["status"] == "QUALIFIED_RUNTIME_OBSERVATION" else 1)
""")


def check_01_diff_and_immutability(*, allow_untracked_helper: bool) -> dict:
    head = host_git("rev-parse", "HEAD").stdout.strip()
    branch = host_git("branch", "--show-current").stdout.strip()
    status_lines = [l for l in host_git("status", "--porcelain=v1", "-uall").stdout.splitlines() if l]
    if branch != "review/wp-0005-q0-carbon":
        raise AssertionError(f"unexpected branch: {branch}")
    if not allow_untracked_helper and status_lines:
        raise AssertionError(f"worktree must be clean before decisive run, got: {status_lines}")

    cand_parent = host_git("rev-parse", f"{CANDIDATE_COMMIT}^").stdout.strip()
    if cand_parent != CANDIDATE_PARENT:
        raise AssertionError(f"candidate parent {cand_parent} != {CANDIDATE_PARENT}")

    for req_anc in (CANDIDATE_COMMIT, AUTHOR_EVIDENCE_008, AUTHOR_REPORT_008):
        anc = subprocess.run(
            ["git", "--no-optional-locks", "merge-base", "--is-ancestor", req_anc, "HEAD"],
            cwd=str(REPO_ROOT),
        )
        if anc.returncode != 0:
            raise AssertionError(f"{req_anc} is not merged into HEAD {head}")

    # 1. Exact 14-file source diff between 2a52ea58 and 24a5866b.
    diff_lines = host_git("diff", "--name-status", CANDIDATE_PARENT, CANDIDATE_COMMIT).stdout.splitlines()
    observed_diff = {}
    for line in diff_lines:
        st, path = line.split("\t", 1)
        observed_diff[path] = st
    if observed_diff != EXPECTED_DIFF:
        raise AssertionError(f"candidate diff mismatch: {observed_diff}")

    # 2. Exact 18-file evidence diff between 24a5866b and b70ff45f.
    ev_lines = host_git("diff", "--name-status", CANDIDATE_COMMIT, AUTHOR_EVIDENCE_008).stdout.splitlines()
    ev_paths = []
    for line in ev_lines:
        st, path = line.split("\t", 1)
        if st != "A" or not path.startswith("qualification/q0/harness/evidence/008-git-isolation/"):
            raise AssertionError(f"unexpected /008 evidence change: {line}")
        ev_paths.append(path)
    if len(ev_paths) != 18:
        raise AssertionError(f"expected 18 /008 evidence additions, got {len(ev_paths)}")

    # 3. Exact 1-file report diff between b70ff45f and 460e1d81.
    rep_lines = host_git("diff", "--name-status", AUTHOR_EVIDENCE_008, AUTHOR_REPORT_008).stdout.splitlines()
    if rep_lines != ["A\tdocs/agent-reports/eld-q0-harness/WP-0005/008_2026-11-15_implementation_eld-q0-harness.md"]:
        raise AssertionError(f"unexpected /008 report diff: {rep_lines}")

    # 4. Zero core harness differences between candidate 24a5866b and HEAD (only the 18 /008 evidence files).
    harness_since_cand = sorted(
        l for l in host_git("diff", "--name-only", CANDIDATE_COMMIT, "HEAD", "--", "qualification/q0/harness").stdout.splitlines() if l
    )
    if harness_since_cand != sorted(ev_paths):
        raise AssertionError(f"unexpected harness changes since {CANDIDATE_COMMIT}: {harness_since_cand}")

    # 5. Frozen protocol, lock, and model manifest digests match 84cef5ef byte-for-byte.
    frozen_inputs = {}
    for rel_path, (want_size, want_sha) in EXPECTED_FROZEN_INPUTS.items():
        raw = (REPO_ROOT / rel_path).read_bytes()
        blob_002 = host_git("cat-file", "blob", f"{CANDIDATE_002}:{rel_path}", binary=True).stdout
        got_sha = sha256_bytes(raw)
        if len(raw) != want_size or got_sha != want_sha or raw != blob_002:
            raise AssertionError(f"frozen input changed for {rel_path}: size={len(raw)} sha={got_sha}")
        frozen_inputs[rel_path] = {"bytes": len(raw), "sha256": got_sha, "byte_identical_to_84cef5ef": True}

    # 6. Zero modifications to prior immutable paths since continuation base ca81c44e.
    immutable_paths = [
        "docs/agent-reports/eld-q0-reviewer",
        "docs/agent-reports/eld-rd-astra",
        "docs/agent-reports/eld-q0-harness/WP-0005/002_2026-11-15_implementation_eld-q0-harness.md",
        "docs/reviews/WP-0005/eld-q0-reviewer/pre-execution",
        "docs/reviews/WP-0005/eld-q0-reviewer/correction-009/.gitattributes",
        "docs/reviews/WP-0005/eld-q0-reviewer/correction-009/README.md",
        "docs/reviews/WP-0005/eld-q0-reviewer/correction-009/reproduce_coord_q0_01_phase_a.py",
        "docs/reviews/WP-0005/eld-q0-reviewer/correction-009/phase-a-b5f2f8ab",
        "research",
        "evaluation",
        "qualification/q0/harness/evidence/002-cpu",
        "qualification/q0/harness/evidence/002-checkpoint-2",
        "qualification/q0/harness/evidence/002-final",
    ]
    imm_delta = host_git("diff", "--name-only", CONTINUATION_BASE, "HEAD", "--", *immutable_paths).stdout.strip()
    if imm_delta != "":
        raise AssertionError(f"immutable paths changed since {CONTINUATION_BASE}: {imm_delta}")

    # 7. Measure Phase A summary.json directly to reconcile Phase A README byte-count erratum.
    phase_a_summary = (
        REPO_ROOT
        / "docs/reviews/WP-0005/eld-q0-reviewer/correction-009/phase-a-b5f2f8ab/summary.json"
    )
    pa_bytes = phase_a_summary.read_bytes()
    pa_sha = sha256_bytes(pa_bytes)
    if len(pa_bytes) != 10039 or pa_sha != "0000fb0ef296a1b476aeaa3e2c404124c67fa7dc094462ea63140feca38b3d35":
        raise AssertionError(f"unexpected Phase A summary.json bytes={len(pa_bytes)} sha={pa_sha}")

    return {
        "status": "pass",
        "head": head,
        "branch": branch,
        "worktree_status_before": status_lines,
        "candidate_commit": CANDIDATE_COMMIT,
        "candidate_parent": cand_parent,
        "author_008_evidence_commit": AUTHOR_EVIDENCE_008,
        "author_008_report_commit": AUTHOR_REPORT_008,
        "continuation_base": CONTINUATION_BASE,
        "candidate_changed_files_count": len(observed_diff),
        "candidate_changed_files": observed_diff,
        "author_008_evidence_files_count": len(ev_paths),
        "core_harness_identical_to_candidate": True,
        "frozen_inputs": frozen_inputs,
        "immutable_paths_unchanged": True,
        "phase_a_summary_reconciliation": {
            "path": "docs/reviews/WP-0005/eld-q0-reviewer/correction-009/phase-a-b5f2f8ab/summary.json",
            "actual_bytes": len(pa_bytes),
            "phase_a_readme_reported_bytes": 8370,
            "sha256": pa_sha,
            "sha256_matches_phase_a_readme": True,
        },
    }


def check_02_unittests() -> tuple[dict, bytes]:
    t0 = time.perf_counter()
    cp = subprocess.run(
        [
            sys.executable, "-I", "-B", "-m", "unittest", "discover",
            "-s", "qualification/q0/harness/tests",
            "-t", "qualification/q0/harness/tests",
            "-v",
        ],
        cwd=str(REPO_ROOT),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=240,
    )
    elapsed_s = round(time.perf_counter() - t0, 4)
    combined = cp.stdout + (b"\n--- stderr ---\n" if cp.stdout else b"") + cp.stderr
    txt = combined.decode("utf-8", errors="replace")
    m = re.search(r"Ran (\d+) tests in ([0-9.]+)s", txt)
    ran = int(m.group(1)) if m else None
    m_skip = re.search(r"OK \(skipped=(\d+)\)", txt)
    skipped = int(m_skip.group(1)) if m_skip else 0
    if cp.returncode != 0 or ran != 80 or "OK" not in txt.splitlines()[-1]:
        raise AssertionError(f"unittest failed rc={cp.returncode} ran={ran}:\n{txt[-2000:]}")
    return {
        "status": "pass",
        "returncode": cp.returncode,
        "tests_ran": ran,
        "tests_passed": ran - skipped,
        "tests_skipped": skipped,
        "elapsed_s": elapsed_s,
    }, combined


def check_03_real_subprocess_git_matrix(scratch: Path, protocol: dict) -> dict:
    external_root = Path(protocol["storage"]["root"])
    if external_root.exists():
        raise AssertionError(f"external runtime root must not exist: {external_root}")
    outside_cwd = scratch / "outside-cwd"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    parent = polluted_parent_env(scratch)
    parent_code = code_identity(REPO_ROOT)
    if not parent_code["harness_clean"]:
        raise AssertionError(f"expected clean harness in parent_code: {parent_code}")

    lock_blobs = load_lock_git_blobs()
    gpu = protocol["gpu"]["uuid"]
    envs = {
        "stage_offline": build_stage_env(parent, root=external_root, protocol=protocol, network=False),
        "stage_network": build_stage_env(parent, root=external_root, protocol=protocol, network=True),
        "child_author": build_child_env(
            parent, root=external_root, owner="author",
            run_dir=external_root / "runs" / "author" / "probe-readonly", gpu_uuid=gpu,
        ),
        "child_reviewer": build_child_env(
            parent, root=external_root, owner="reviewer",
            run_dir=external_root / "runs" / "reviewer" / "probe-readonly", gpu_uuid=gpu,
        ),
    }

    rows = []
    for env_name, env in envs.items():
        for flags in (["-I", "-B"], ["-s", "-P", "-X", "utf8"]):
            cp = subprocess.run(
                [sys.executable, *flags, "-c", CHILD_GIT_MATRIX_PROBE,
                 str(HARNESS_DIR), str(REPO_ROOT), json.dumps(lock_blobs)],
                env=env,
                cwd=str(outside_cwd),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=90,
            )
            if cp.returncode != 0:
                raise AssertionError(f"{env_name} {flags} failed rc={cp.returncode}: {cp.stderr}")
            obs = json.loads(cp.stdout)
            if obs["git_on_path"] is not None or obs["any_git_dir_on_path"]:
                raise AssertionError(f"PATH exposed Git in {env_name}: {obs['path_entries']}")
            if not Path(obs["git_executable_var"]).is_file():
                raise AssertionError(f"invalid Q0_GIT_EXECUTABLE in {env_name}: {obs['git_executable_var']}")
            if obs["git_isolation_env"] != GIT_ISOLATION_ENV:
                raise AssertionError(f"git isolation env mismatch in {env_name}: {obs['git_isolation_env']}")
            if obs["leaked_parent_keys"] != []:
                raise AssertionError(f"leaked parent keys in {env_name}: {obs['leaked_parent_keys']}")
            bad_origins = [
                o for o in obs["git_config_origins"]
                if "program files" in o.lower()
                or ("/users/" in o.lower() and ".gitconfig" in o.lower())
                or ("\\users\\" in o.lower() and ".gitconfig" in o.lower())
            ]
            if bad_origins:
                raise AssertionError(f"global/system gitconfig leaked in {env_name}: {bad_origins}")
            if obs["code_identity"] != parent_code:
                raise AssertionError(f"code_identity mismatch in {env_name}: {obs['code_identity']} != {parent_code}")
            if not all(v["git_blob_sha1_ok"] for v in obs["blob_checks"].values()):
                raise AssertionError(f"blob check failed in {env_name}: {obs['blob_checks']}")
            if obs["lock_readiness"] != {
                "artifacts": 32,
                "counts": {"publisher-declared": 31, "local-sha256-TOFU": 1, "missing": 0},
                "installable": True,
                "total_graph_edges": 850,
                "torchvision_receipt_ok": True,
            }:
                raise AssertionError(f"unexpected lock readiness in {env_name}: {obs['lock_readiness']}")
            rows.append({
                "env": env_name,
                "python_flags": flags,
                "git_on_path": obs["git_on_path"],
                "any_git_dir_on_path": obs["any_git_dir_on_path"],
                "git_executable": obs["git_executable_var"],
                "git_isolation_env": obs["git_isolation_env"],
                "git_config_origins": obs["git_config_origins"],
                "leaked_parent_keys": obs["leaked_parent_keys"],
                "code_identity": obs["code_identity"],
                "blob_checks": obs["blob_checks"],
                "lock_readiness": obs["lock_readiness"],
            })

    if external_root.exists():
        raise AssertionError(f"probe created external runtime root: {external_root}")
    return {
        "status": "pass",
        "subprocesses_executed": len(rows),
        "lock_git_blobs_checked": lock_blobs,
        "external_root_exists_after": external_root.exists(),
        "results": rows,
    }


def check_04_cli_in_isolated_envs(scratch: Path, protocol: dict, p_sha: str) -> dict:
    external_root = Path(protocol["storage"]["root"])
    outside_cwd = scratch / "cli-outside-cwd"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    parent = polluted_parent_env(scratch)
    parent_code = code_identity(REPO_ROOT)

    # 1. Stage A0 host-precheck in parent/operator environment (per ACQUISITION.md L25).
    cp_hp_parent = subprocess.run(
        [sys.executable, "-I", "-B", str(Q0_PY), "host-precheck", "--stage", "initial"],
        cwd=str(outside_cwd),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=90,
    )
    if cp_hp_parent.returncode != 0:
        raise AssertionError(f"parent host-precheck failed rc={cp_hp_parent.returncode}: {cp_hp_parent.stdout}")
    hp_parent = json.loads(cp_hp_parent.stdout)
    if hp_parent["status"] != "pass" or not hp_parent["git_runtime"]["present"]:
        raise AssertionError(f"parent host-precheck unexpected payload: {hp_parent}")

    envs = {
        "stage_offline": build_stage_env(parent, root=external_root, protocol=protocol, network=False),
        "child_reviewer": build_child_env(
            parent, root=external_root, owner="reviewer",
            run_dir=external_root / "runs" / "reviewer" / "cli-readonly",
            gpu_uuid=protocol["gpu"]["uuid"],
        ),
    }
    never_req = scratch / "never-created-requirements.txt"
    commands = [
        ("status", ["status"], 0, None),
        ("lock-check", ["lock-check"], 0, None),
        ("check-protocol", ["check-protocol"], 0, None),
        ("verify-snapshots", ["verify-snapshots"], 0, None),
        ("derive-rasters-check", ["derive-rasters", "--check"], 0, None),
        ("build-model-manifest-check", ["build-model-manifest", "--check"], 0, None),
        ("write-requirements-unreleased", ["write-requirements", str(never_req)], 2, "EXECUTION_NOT_RELEASED"),
        ("verify-wheelhouse-unreleased", ["verify-wheelhouse", str(outside_cwd)], 2, "EXECUTION_NOT_RELEASED"),
        ("execute-author-unreleased", ["execute", "--owner", "author"], 2, "EXECUTION_NOT_RELEASED"),
        ("execute-reviewer-unreleased", ["execute", "--owner", "reviewer"], 2, "EXECUTION_NOT_RELEASED"),
    ]
    rows = []
    for env_name, env in envs.items():
        for label, argv, want_rc, want_fail_cls in commands:
            cp = subprocess.run(
                [sys.executable, "-s", "-P", "-X", "utf8", str(Q0_PY), *argv],
                env=env,
                cwd=str(outside_cwd),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=90,
            )
            if cp.returncode != want_rc:
                raise AssertionError(
                    f"CLI {label} in {env_name}: rc={cp.returncode} want={want_rc}\nstderr={cp.stderr}\nstdout={cp.stdout}"
                )
            payload = json.loads(cp.stdout)
            summary_fields = {}
            if want_rc == 0:
                if label == "status":
                    if payload["code_identity"] != parent_code or payload["protocol_sha256"] != p_sha:
                        raise AssertionError(f"status mismatch in {env_name}: {payload}")
                    summary_fields = {
                        "head": payload["code_identity"]["head"],
                        "harness_clean": payload["code_identity"]["harness_clean"],
                        "installable": payload["lock_readiness"]["installable"],
                        "storage_root_exists": payload["storage_root_exists"],
                    }
                elif label == "lock-check":
                    if payload["artifacts"] != 32 or not payload["readiness"]["installable"]:
                        raise AssertionError(f"lock-check mismatch in {env_name}: {payload}")
                    summary_fields = {"artifacts": payload["artifacts"], "counts": payload["readiness"]["counts"]}
                elif label == "check-protocol":
                    summary_fields = {"protocol_sha256": payload["protocol_sha256"], "fixtures": payload["fixtures_verified_bytes"]}
                elif label == "verify-snapshots":
                    summary_fields = {"snapshots_verified": payload["snapshots_verified"]}
                elif label == "derive-rasters-check":
                    summary_fields = {"identical_to_protocol": payload["identical_to_protocol"]}
                elif label == "build-model-manifest-check":
                    summary_fields = {"identical_to_derivation": payload["identical_to_derivation"]}
            else:
                if payload["status"] != "BLOCKED" or payload["accuracy_score"] is not None:
                    raise AssertionError(f"expected BLOCKED outcome for {label}: {payload}")
                got_cls = payload["failures"][0]["failure_class"]
                if got_cls != want_fail_cls:
                    raise AssertionError(f"expected {want_fail_cls} for {label}, got {got_cls}")
                summary_fields = {"status": payload["status"], "failure_class": got_cls}
            rows.append({
                "env": env_name,
                "command": label,
                "returncode": cp.returncode,
                "summary": summary_fields,
            })

    # Empirical boundary note: inside stripped stage_offline (which omits ProgramFiles),
    # host-precheck's git_runtime check still passes, while Windows System32\nvidia-smi.exe
    # requires ProgramFiles (supplied in Stage A0 / Stage E parent shells).
    cp_hp_stage = subprocess.run(
        [sys.executable, "-s", "-P", "-X", "utf8", str(Q0_PY), "host-precheck", "--stage", "initial"],
        env=envs["stage_offline"],
        cwd=str(outside_cwd),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=90,
    )
    hp_stage = json.loads(cp_hp_stage.stdout)
    if not hp_stage["git_runtime"]["present"]:
        raise AssertionError(f"expected git_runtime.present=True inside stage_offline: {hp_stage}")

    if never_req.exists() or external_root.exists():
        raise AssertionError("unreleased CLI command created side-effect file or external root")
    return {
        "status": "pass",
        "parent_stage_a0_host_precheck": {
            "returncode": cp_hp_parent.returncode,
            "status": hp_parent["status"],
            "git_runtime": hp_parent["git_runtime"],
            "free_bytes": hp_parent["free_space"]["free_bytes"],
            "gpu_observer_returncodes": [r["returncode"] for r in hp_parent["gpu_observer"]],
        },
        "stage_offline_host_precheck_boundary_note": {
            "returncode": cp_hp_stage.returncode,
            "git_runtime_present": hp_stage["git_runtime"]["present"],
            "gpu_observer_returncodes_without_ProgramFiles": [r["returncode"] for r in hp_stage["gpu_observer"]],
            "note": (
                "Stage A0 host-precheck and Stage E supervisor.run_observers execute in the operator/parent "
                "process where ProgramFiles is set (rc=0); stripped stage_env omits ProgramFiles, which "
                "Windows System32\\nvidia-smi.exe reads during NVML init."
            ),
        },
        "cli_invocations": len(rows),
        "never_requirements_created": never_req.exists(),
        "external_root_exists_after": external_root.exists(),
        "results": rows,
    }


def check_05_fail_closed_negative_git_probes(scratch: Path, protocol: dict, p_sha: str) -> dict:
    external_root = Path(protocol["storage"]["root"])
    sim_root = scratch / "neg-sim-root"
    sim_run = layout(sim_root, "reviewer")["run_owner"] / "neg-r1"
    parent = polluted_parent_env(scratch)
    base_stage = build_stage_env(parent, root=sim_root, protocol=protocol, network=False)
    base_child = build_child_env(parent, root=sim_root, owner="reviewer", run_dir=sim_run, gpu_uuid=protocol["gpu"]["uuid"])

    corrupt_dir = scratch / "corrupt-git-bin"
    corrupt_dir.mkdir(parents=True, exist_ok=True)
    corrupt_git = corrupt_dir / "git.exe"
    corrupt_git.write_bytes(b"NOT_A_VALID_WIN32_PE_EXECUTABLE")

    missing_git = scratch / "does-not-exist" / "git.exe"
    first_blob = load_lock_git_blobs()[0]

    bad_env_cases = {
        "stage_stripped_git_var": {k: v for k, v in base_stage.items() if k != GIT_EXECUTABLE_VAR},
        "child_stripped_git_var": {k: v for k, v in base_child.items() if k != GIT_EXECUTABLE_VAR},
        "stage_missing_git_path": base_stage | {GIT_EXECUTABLE_VAR: str(missing_git)},
        "child_corrupt_git_binary": base_child | {GIT_EXECUTABLE_VAR: str(corrupt_git)},
    }

    subproc_neg_rows = []
    for case_name, bad_env in bad_env_cases.items():
        cp = subprocess.run(
            [sys.executable, "-I", "-B", "-c", NEGATIVE_GIT_PROBE,
             str(HARNESS_DIR), str(REPO_ROOT), first_blob],
            env=bad_env,
            cwd=str(scratch),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if cp.returncode != 0:
            raise AssertionError(f"negative probe crashed for {case_name}: {cp.stderr}")
        obs = json.loads(cp.stdout)
        if obs.get("code_error", {}).get("type") != "Q0Failure" or obs["code_error"]["failure_class"] != "HOST_PRECHECK_FAILED":
            raise AssertionError(f"expected HOST_PRECHECK_FAILED in {case_name}, got: {obs}")
        if obs.get("blob_error", {}).get("type") != "Q0Failure" or obs["blob_error"]["failure_class"] != "DEPENDENCY_LOCK_PENDING":
            raise AssertionError(f"expected DEPENDENCY_LOCK_PENDING in {case_name}, got: {obs}")

        cli_checks = {}
        for subcmd, want_cls in (
            (["status"], "DEPENDENCY_LOCK_PENDING"),
            (["lock-check"], "DEPENDENCY_LOCK_PENDING"),
            (["write-requirements", str(scratch / "neg-never.txt")], "DEPENDENCY_LOCK_PENDING"),
            (["execute", "--owner", "reviewer"], "HOST_PRECHECK_FAILED"),
        ):
            cp_cli = subprocess.run(
                [sys.executable, "-s", "-P", "-X", "utf8", str(Q0_PY), *subcmd],
                env=bad_env,
                cwd=str(scratch),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if cp_cli.returncode != 2:
                raise AssertionError(f"expected exit 2 BLOCKED in {case_name} {subcmd}, got {cp_cli.returncode}: {cp_cli.stderr}")
            rec = json.loads(cp_cli.stdout)
            if rec["status"] != "BLOCKED" or rec["accuracy_score"] is not None:
                raise AssertionError(f"unexpected CLI outcome in {case_name}: {rec}")
            if rec["failures"][0]["failure_class"] != want_cls:
                raise AssertionError(f"expected {want_cls} in {case_name} {subcmd}, got {rec['failures'][0]}")
            cli_checks[subcmd[0]] = {"returncode": cp_cli.returncode, "failure_class": want_cls}

        subproc_neg_rows.append({
            "case": case_name,
            "code_error": obs["code_error"],
            "blob_error": obs["blob_error"],
            "cli_fail_closed": cli_checks,
        })

    # Verify audit_stage_env / audit_child_env reject mutable-root git.exe and altered GIT_ISOLATION_ENV.
    mutable_git = sim_root / "venv" / "Scripts" / "git.exe"
    mutable_git.parent.mkdir(parents=True, exist_ok=True)
    mutable_git.write_bytes(b"MZ-mutable")
    audit_rejections = []
    for label, fn, base_env, kwargs in (
        ("stage_mutable_root_git", audit_stage_env, base_stage | {GIT_EXECUTABLE_VAR: str(mutable_git)}, {"root": sim_root, "network": False}),
        ("child_mutable_root_git", audit_child_env, base_child | {GIT_EXECUTABLE_VAR: str(mutable_git)}, {"root": sim_root, "owner": "reviewer", "run_dir": sim_run}),
        ("stage_nosystem_off", audit_stage_env, base_stage | {"GIT_CONFIG_NOSYSTEM": "0"}, {"root": sim_root, "network": False}),
        ("child_global_config_leak", audit_child_env, base_child | {"GIT_CONFIG_GLOBAL": r"C:\Users\x\.gitconfig"}, {"root": sim_root, "owner": "reviewer", "run_dir": sim_run}),
        ("child_prompt_enabled", audit_child_env, base_child | {"GIT_TERMINAL_PROMPT": "1"}, {"root": sim_root, "owner": "reviewer", "run_dir": sim_run}),
    ):
        try:
            fn(base_env, **kwargs)
        except Q0Failure as exc:
            audit_rejections.append({"case": label, "failure_class": exc.failure_class, "detail": exc.detail})
        else:
            raise AssertionError(f"expected Q0Failure for {label}")

    # Direct `q0.py child` (cmd_child) subprocess verification:
    # Exercises q0.py lines 224-245 inside real isolated build_child_env WITHOUT creating C:\Users\jackg\eLedgerCare-Q0!
    live_code = code_identity(REPO_ROOT)
    lock_sha = sha256_bytes((HARNESS_DIR / "locks" / "dependency-lock.json").read_bytes())
    valid_rel = {
        "schema": "eldq0-release/2",
        "packet": "WP-0005",
        "stage": "execute",
        "sequence": "005",
        "released_by": "eld-coordinator",
        "release_commit": "a" * 40,
        "harness_commit": live_code["head"],
        "protocol_sha256": p_sha,
        "lock_sha256": lock_sha,
        "storage_root": protocol["storage"]["root"],
        "gpu_uuid": protocol["gpu"]["uuid"],
        "lease_id": "synthetic-phase-b-cmd-child-probe",
        "accepted_review": {
            "reviewer": "eld-q0-reviewer",
            "report_commit": "b" * 40,
            "evidence_commit": "c" * 40,
        },
        "accepted_provenance_exceptions": ["torchvision-local-sha256-TOFU"],
    }
    rel_file = scratch / "cmd-child-release.json"
    rel_file.write_text(json.dumps(valid_rel), encoding="utf-8")

    cmd_child_cases = []
    for case_label, parent_ctx_code, child_env, want_fail_cls, want_dirty_substr in (
        (
            "toctou_parent_child_mismatch",
            {"head": "0" * 40, "harness_clean": True, "dirty": []},
            base_child,
            "EXECUTION_NOT_RELEASED",
            "parent/child code_identity mismatch",
        ),
        (
            "missing_git_in_cmd_child",
            live_code,
            {k: v for k, v in base_child.items() if k != GIT_EXECUTABLE_VAR},
            "EXECUTION_NOT_RELEASED",
            "HOST_PRECHECK_FAILED",
        ),
        (
            "matching_live_code_and_lock_blobs_then_scratch_run_dir_guard",
            live_code,
            base_child,
            "STORAGE_NOT_OWNED",
            None,
        ),
    ):
        c_run = scratch / f"cmd-child-{case_label}"
        c_run.mkdir(parents=True, exist_ok=True)
        (c_run / "parent-context.json").write_text(
            json.dumps({
                "forbidden_parents": default_forbidden_parents(REPO_ROOT, dict(os.environ)),
                "code_identity": parent_ctx_code,
            }),
            encoding="utf-8",
        )
        cp_c = subprocess.run(
            [
                sys.executable, "-s", "-P", "-X", "utf8", str(Q0_PY), "child",
                "--owner", "reviewer", "--release", str(rel_file), "--run-dir", str(c_run),
            ],
            env=child_env,
            cwd=str(c_run),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
        )
        outcome = json.loads((c_run / "evidence" / "outcome.json").read_text(encoding="utf-8"))
        if cp_c.returncode != 0 or outcome["status"] != "BLOCKED" or outcome["accuracy_score"] is not None:
            raise AssertionError(f"unexpected cmd_child result for {case_label}: rc={cp_c.returncode} outcome={outcome}")
        got_cls = outcome["failures"][0]["failure_class"]
        if got_cls != want_fail_cls:
            raise AssertionError(f"cmd_child {case_label}: expected {want_fail_cls}, got {got_cls} ({outcome['failures']})")
        dirty_joined = " | ".join(outcome["context"]["code_identity"].get("dirty", []))
        if want_dirty_substr and want_dirty_substr not in dirty_joined:
            raise AssertionError(f"cmd_child {case_label}: expected {want_dirty_substr!r} in dirty={dirty_joined!r}")
        if case_label == "matching_live_code_and_lock_blobs_then_scratch_run_dir_guard":
            if not outcome["context"].get("lock_readiness", {}).get("installable"):
                raise AssertionError(f"cmd_child did not reach lock_readiness: {outcome['context']}")
        cmd_child_cases.append({
            "case": case_label,
            "returncode": cp_c.returncode,
            "outcome_status": outcome["status"],
            "failure_class": got_cls,
            "recorded_code_identity": outcome["context"]["code_identity"],
            "lock_readiness_verified_in_child": bool(outcome["context"].get("lock_readiness", {}).get("installable")),
        })

    if external_root.exists():
        raise AssertionError(f"cmd_child probe created external root: {external_root}")

    return {
        "status": "pass",
        "subprocess_negative_cases": subproc_neg_rows,
        "audit_rejections": audit_rejections,
        "cmd_child_direct_probes": cmd_child_cases,
        "external_root_exists_after": external_root.exists(),
    }


def check_06_heartbeat_and_supervised_child(scratch: Path, protocol: dict) -> dict:
    hb_dir = scratch / "hb-stress"
    hb_dir.mkdir(parents=True, exist_ok=True)
    hb_path = hb_dir / "heartbeat.json"
    progress_counter = {"v": 0}
    hb = Heartbeat(hb_path, 0.005, lambda: progress_counter["v"])
    writer_errors: list[str] = []
    reader_errors: list[str] = []
    snapshots_read = {"valid": 0}
    stop_readers = threading.Event()

    def writer_worker(tid: int):
        try:
            for step in range(50):
                progress_counter["v"] = tid * 1000 + step
                hb.set_phase(f"w{tid}_s{step}", 30, step % 2 == 0)
                hb.beat()
        except BaseException as exc:
            writer_errors.append(f"{type(exc).__name__}: {exc}")

    def reader_worker():
        while not stop_readers.is_set():
            try:
                raw = hb_path.read_text(encoding="utf-8")
                parsed = json.loads(raw)
                if "phase" not in parsed or "progress" not in parsed:
                    reader_errors.append(f"incomplete heartbeat payload: {parsed}")
                else:
                    snapshots_read["valid"] += 1
            except FileNotFoundError:
                pass
            except PermissionError:
                pass
            except ValueError as exc:
                reader_errors.append(f"torn JSON read: {exc}")
            except OSError:
                pass
            time.sleep(0.005)  # 200x faster than supervisor.py default poll_s=1.0s

    hb.start()
    readers = [threading.Thread(target=reader_worker, daemon=True)]
    writers = [threading.Thread(target=writer_worker, args=(i,)) for i in range(4)]
    for r in readers:
        r.start()
    for w in writers:
        w.start()
    for w in writers:
        w.join(timeout=15)
    stop_readers.set()
    for r in readers:
        r.join(timeout=5)
    hb.set_phase("finished", None, False)
    hb.stop()

    if writer_errors or reader_errors:
        raise AssertionError(f"heartbeat stress errors: writers={writer_errors} readers={reader_errors}")
    final_hb = _read_heartbeat(hb_path)
    if not final_hb or final_hb.get("phase") != "finished":
        raise AssertionError(f"unexpected final heartbeat: {final_hb}")
    tmp_leftover = hb_path.with_suffix(".tmp").exists()
    if tmp_leftover:
        raise AssertionError("heartbeat .tmp leftover remained after final replace")

    # Verify exact sleep schedule (10, 20, 30, 40 ms across 5 attempts = 100 ms total, NO 50 ms 5th sleep!).
    retry_hb = Heartbeat(hb_dir / "retry.json", 1.0, lambda: 42)
    real_replace = os.replace
    attempts = {"n": 0}
    recorded_sleeps_ms: list[int] = []

    def transient_4_failures(src, dst):
        attempts["n"] += 1
        if attempts["n"] <= 4:
            raise PermissionError(5, "Access is denied")
        return real_replace(src, dst)

    def record_sleep(sec: float):
        recorded_sleeps_ms.append(round(sec * 1000))

    with patch("q0harness.session.os.replace", side_effect=transient_4_failures), \
            patch("q0harness.session.time.sleep", side_effect=record_sleep):
        retry_hb.set_phase("recovered_after_4", 60, True)
    if attempts["n"] != 5 or recorded_sleeps_ms != [10, 20, 30, 40]:
        raise AssertionError(f"expected 5 attempts & [10,20,30,40] ms sleeps, got n={attempts['n']} sleeps={recorded_sleeps_ms}")

    exhaust_attempts = {"n": 0}
    exhaust_sleeps_ms: list[int] = []

    def persistent_5_failures(src, dst):
        exhaust_attempts["n"] += 1
        raise PermissionError(5, "Access is denied")

    raised_on_5th = False
    with patch("q0harness.session.os.replace", side_effect=persistent_5_failures), \
            patch("q0harness.session.time.sleep", side_effect=lambda s: exhaust_sleeps_ms.append(round(s * 1000))):
        try:
            retry_hb.beat()
        except PermissionError:
            raised_on_5th = True
    if not raised_on_5th or exhaust_attempts["n"] != 5 or exhaust_sleeps_ms != [10, 20, 30, 40]:
        raise AssertionError(
            f"expected PermissionError after 5 attempts & [10,20,30,40] ms sleeps, "
            f"got raised={raised_on_5th} n={exhaust_attempts['n']} sleeps={exhaust_sleeps_ms}"
        )

    # Real supervised child process (poll_s=0.02 tight supervisor loop, owner='reviewer').
    sup_root = scratch / "sup-reviewer-root"
    paths = layout(sup_root, "reviewer")
    sup_run = paths["run_owner"] / "run-reviewer-tightpoll"
    for sub in ("tmp", "home", "hf-modules", "torch-home", "triton-cache", "inductor-cache",
                "cuda-cache", "xdg-cache", "pip-cache", "uv-cache"):
        (sup_run / sub).mkdir(parents=True, exist_ok=True)
    child_script = scratch / "supervised_reviewer_child.py"
    child_script.write_text(SUPERVISED_REVIEWER_CHILD, encoding="utf-8")
    child_env = build_child_env(
        polluted_parent_env(scratch),
        root=sup_root,
        owner="reviewer",
        run_dir=sup_run,
        gpu_uuid=protocol["gpu"]["uuid"],
    )
    cmd = [
        sys.executable, "-s", "-P", "-X", "utf8", str(child_script),
        str(HARNESS_DIR), str(REPO_ROOT), str(sup_root), str(sup_run),
    ]
    sup_rec = supervise(
        cmd,
        env=child_env,
        cwd=sup_run,
        run_dir=sup_run,
        heartbeat_path=sup_run / "heartbeat.json",
        session_timeout_s=120,
        stall_s=30,
        max_log_bytes=4 << 20,
        default_phase_timeout_s=60,
        poll_s=0.02,
    )
    stderr_txt = (sup_run / "child.stderr.txt").read_text(encoding="utf-8", errors="replace")
    if sup_rec["verdict"] != "CHILD_COMPLETED" or sup_rec["child_outcome_status"] != QUALIFIED:
        raise AssertionError(f"supervised child failed: {sup_rec}\nstderr={stderr_txt}")
    child_obs = json.loads((sup_run / "reviewer-child-summary.json").read_text(encoding="utf-8"))
    if child_obs["live_code_identity"] != code_identity(REPO_ROOT) or child_obs["artifacts_verified"] != 32:
        raise AssertionError(f"unexpected child git observation: {child_obs}")

    tl = subprocess.run(
        ["tasklist", "/FI", f"PID eq {sup_rec['child_pid']}", "/NH"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    child_still_running = str(sup_rec["child_pid"]) in tl
    if child_still_running:
        raise AssertionError(f"supervised child PID {sup_rec['child_pid']} still running: {tl}")

    return {
        "status": "pass",
        "thread_and_reader_stress": {
            "writer_threads": 4,
            "writes_per_thread": 100,
            "reader_threads": 1,
            "reader_poll_s": 0.005,
            "valid_snapshots_observed": snapshots_read["valid"],
            "writer_errors": writer_errors,
            "reader_errors": reader_errors,
            "tmp_leftover": tmp_leftover,
        },
        "bounded_permission_error_retry": {
            "transient_4_failures_recovered_on_attempt": attempts["n"],
            "sleeps_ms_observed": recorded_sleeps_ms,
            "total_max_sleep_ms": sum(exhaust_sleeps_ms),
            "persistent_5_failures_raised_permission_error": raised_on_5th,
            "max_attempts": exhaust_attempts["n"],
        },
        "supervised_reviewer_child": {
            "poll_s": 0.02,
            "verdict": sup_rec["verdict"],
            "child_returncode": sup_rec["child_returncode"],
            "child_outcome_status": sup_rec["child_outcome_status"],
            "child_still_running_after_supervise": child_still_running,
            "backend_kind": child_obs["backend_kind"],
            "live_code_identity": child_obs["live_code_identity"],
            "artifacts_verified_in_child": child_obs["artifacts_verified"],
            "observations_recorded": child_obs["observations"],
        },
    }


def check_07_author_008_evidence_audit() -> dict:
    ev_dir = HARNESS_DIR / "evidence" / "008-git-isolation" / "24a5866b"
    summary = json.loads((ev_dir / "summary.json").read_text(encoding="utf-8"))
    if summary["head"] != CANDIDATE_COMMIT or summary["head_after"] != CANDIDATE_COMMIT:
        raise AssertionError(f"author summary head mismatch: {summary['head']} / {summary['head_after']}")
    if summary["tracked_diff_after"] != [] or summary["external_storage_parent_exists_before"] or summary["external_storage_parent_exists_after"]:
        raise AssertionError("author summary cleanliness/external-root flags failed")

    verified_blobs = []
    for cmd in summary["commands"]:
        p = ev_dir / cmd["output"]
        raw = p.read_bytes()
        sha = sha256_bytes(raw)
        if len(raw) != cmd["output_bytes"] or sha != cmd["output_sha256"]:
            raise AssertionError(f"author evidence mismatch for {cmd['output']}: got {len(raw)}/{sha}")
        verified_blobs.append({
            "name": cmd["name"],
            "exit_code": cmd["exit_code"],
            "bytes": len(raw),
            "sha256": sha,
        })

    coord_diag = json.loads((ev_dir / "coordinator-worker-git-check.txt").read_text(encoding="utf-8"))
    if coord_diag.get("runtime_root_exists") is not False:
        raise AssertionError(f"unexpected runtime_root_exists in coordinator-worker-git-check.txt: {coord_diag}")
    for env_key in ("install_stage", "runtime_child"):
        entry = coord_diag["observations"][env_key]
        parsed_out = json.loads(entry["stdout"])
        if entry["returncode"] != 0 or parsed_out["git_which"] is not None:
            raise AssertionError(f"unexpected {env_key} result in coordinator-worker-git-check.txt: {entry}")
        if parsed_out["code_identity"] != {"head": CANDIDATE_COMMIT, "harness_clean": True, "dirty": []}:
            raise AssertionError(f"unexpected code_identity in {env_key}: {parsed_out['code_identity']}")

    check_proto = json.loads((ev_dir / "05-check-protocol.txt").read_text(encoding="utf-8"))
    fixtures_bytes = check_proto["fixtures_verified_bytes"]
    if fixtures_bytes != {"SYN-MP-01-v0-clean": 8422, "SYN-WO-01-v0-clean": 3482}:
        raise AssertionError(f"unexpected fixture bytes in 05-check-protocol.txt: {fixtures_bytes}")

    return {
        "status": "pass",
        "author_candidate_head": summary["head"],
        "author_evidence_commands_verified": len(verified_blobs),
        "commands": verified_blobs,
        "coordinator_diag_on_24a5866b": {
            "sha256": sha256_bytes((ev_dir / "coordinator-worker-git-check.txt").read_bytes()),
            "install_stage_rc": coord_diag["observations"]["install_stage"]["returncode"],
            "runtime_child_rc": coord_diag["observations"]["runtime_child"]["returncode"],
        },
        "reconciled_008_report_narrative_errata": {
            "fixture_verified_bytes_actual": fixtures_bytes,
            "report_008_line_118_stated": {"F01": 1490, "F07": 4060},
            "heartbeat_retry_actual": {
                "max_attempts": 5,
                "sleeps_ms": [10, 20, 30, 40],
                "total_max_sleep_ms": 100,
            },
            "report_008_lines_32_67_103_stated": "10..50 ms",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", required=True, help="Directory to write Phase B evidence artifacts")
    ap.add_argument("--allow-untracked-helper", action="store_true",
                    help="Smoke-test mode only before freezing helper commit")
    args = ap.parse_args(argv)

    started_utc = utc_now()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    scratch_base = REPO_ROOT / ".scratch"
    scratch_base.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="phase-b-check-", dir=str(scratch_base)))

    inventory: list[dict] = []
    try:
        protocol, p_sha = load_protocol()
        external_root = Path(protocol["storage"]["root"])
        external_root_before = external_root.exists()

        c01 = check_01_diff_and_immutability(allow_untracked_helper=args.allow_untracked_helper)
        write_json_recorded(out_dir, "01-diff-and-immutability.json", c01, inventory)

        c02_meta, c02_raw = check_02_unittests()
        write_bytes_recorded(out_dir, "02-unittest.txt", c02_raw, inventory)

        c03 = check_03_real_subprocess_git_matrix(scratch, protocol)
        write_json_recorded(out_dir, "03-real-subprocess-git-matrix.json", c03, inventory)

        c04 = check_04_cli_in_isolated_envs(scratch, protocol, p_sha)
        write_json_recorded(out_dir, "04-cli-isolated-envs.json", c04, inventory)

        c05 = check_05_fail_closed_negative_git_probes(scratch, protocol, p_sha)
        write_json_recorded(out_dir, "05-fail-closed-git-probes.json", c05, inventory)

        c06 = check_06_heartbeat_and_supervised_child(scratch, protocol)
        write_json_recorded(out_dir, "06-heartbeat-and-supervisor.json", c06, inventory)

        c07 = check_07_author_008_evidence_audit()
        write_json_recorded(out_dir, "07-author-008-evidence-audit.json", c07, inventory)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    status_after = [l for l in host_git("status", "--porcelain=v1", "-uall").stdout.splitlines() if l]
    if not args.allow_untracked_helper and not str(out_dir).startswith(str(REPO_ROOT / "docs")) and status_after:
        raise AssertionError(f"worktree dirty after Phase B checks: {status_after}")

    external_root_after = Path(protocol["storage"]["root"]).exists()
    if external_root_before or external_root_after:
        raise AssertionError(f"external runtime root must remain absent: before={external_root_before} after={external_root_after}")

    summary = {
        "schema": "eld-q0-reviewer-phase-b/1",
        "reviewer": "eld-q0-reviewer",
        "session_id": "0815536f-045a-4112-8a89-ebf0e0cc782f",
        "model": "Gemini 4 Carbon (High)",
        "started_utc": started_utc,
        "finished_utc": utc_now(),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "helper_path": str(THIS_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
        "helper_sha256": sha256_bytes(THIS_FILE.read_bytes()),
        "worktree_head": c01["head"],
        "candidate_commit": CANDIDATE_COMMIT,
        "candidate_parent": CANDIDATE_PARENT,
        "author_008_evidence_commit": AUTHOR_EVIDENCE_008,
        "author_008_report_commit": AUTHOR_REPORT_008,
        "continuation_base": CONTINUATION_BASE,
        "smoke_mode": bool(args.allow_untracked_helper),
        "external_runtime_root": protocol["storage"]["root"],
        "external_runtime_root_exists_before": external_root_before,
        "external_runtime_root_exists_after": external_root_after,
        "worktree_status_after": status_after,
        "checks": {
            "01_diff_and_immutability": c01["status"],
            "02_harness_unittests": c02_meta,
            "03_real_subprocess_git_matrix": {
                "status": c03["status"],
                "subprocesses_executed": c03["subprocesses_executed"],
            },
            "04_cli_in_isolated_envs": {
                "status": c04["status"],
                "cli_invocations": c04["cli_invocations"],
            },
            "05_fail_closed_negative_git_probes": {
                "status": c05["status"],
                "subprocess_negative_cases": len(c05["subprocess_negative_cases"]),
                "audit_rejections": len(c05["audit_rejections"]),
                "cmd_child_direct_probes": len(c05["cmd_child_direct_probes"]),
            },
            "06_heartbeat_and_supervised_child": {
                "status": c06["status"],
                "valid_heartbeat_snapshots_read": c06["thread_and_reader_stress"]["valid_snapshots_observed"],
                "retry_sleeps_ms": c06["bounded_permission_error_retry"]["sleeps_ms_observed"],
                "supervised_child_verdict": c06["supervised_reviewer_child"]["verdict"],
                "backend_kind": c06["supervised_reviewer_child"]["backend_kind"],
            },
            "07_author_008_evidence_audit": {
                "status": c07["status"],
                "author_evidence_commands_verified": c07["author_evidence_commands_verified"],
            },
        },
        "evidence_files": inventory,
    }
    summary_bytes = (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (out_dir / "summary.json").write_bytes(summary_bytes)
    print(json.dumps({
        "status": "PASS",
        "head": c01["head"],
        "candidate_commit": CANDIDATE_COMMIT,
        "summary_bytes": len(summary_bytes),
        "summary_sha256": hashlib.sha256(summary_bytes).hexdigest(),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
