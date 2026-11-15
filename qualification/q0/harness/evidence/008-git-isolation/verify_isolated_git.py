"""Standalone real-subprocess verifier for COORD-Q0-01 on the frozen /008 candidate.

Evidence tooling only (not candidate code). Executes real isolated child Python processes
under both `build_stage_env` (offline and network) and `build_child_env` (author and reviewer)
against the clean frozen candidate commit, without creating `C:\\Users\\jackg\\eLedgerCare-Q0`,
installing packages, importing torch, or touching GPU resources.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
HARNESS = REPO / "qualification" / "q0" / "harness"
assert (REPO / ".git").exists() and (HARNESS / "q0.py").is_file(), REPO
sys.path.insert(0, str(HARNESS))

from q0harness.environment import (GIT_EXECUTABLE_VAR, GIT_ISOLATION_ENV, build_child_env,
                                   build_stage_env, layout)  # noqa: E402
from q0harness.hashing import sha256_bytes  # noqa: E402
from q0harness.protocol import load_protocol  # noqa: E402
from q0harness.release import code_identity  # noqa: E402

PROBE = """import json, os, shutil, sys
from pathlib import Path
harness, repo = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(harness))
from q0harness import locks
from q0harness.environment import GIT_EXECUTABLE_VAR, GIT_ISOLATION_ENV
from q0harness.release import code_identity

out = {
    "cwd": os.getcwd(),
    "git_which": shutil.which("git"),
    "q0_git_executable": os.environ.get(GIT_EXECUTABLE_VAR),
    "git_isolation_env": {k: os.environ.get(k) for k in GIT_ISOLATION_ENV},
}
out["code_identity"] = code_identity(repo)
lock = locks.load_lock(harness / "locks" / "dependency-lock.json")
pkgs = locks.validate_lock(lock, locks.git_blob_reader(repo))
r = locks.readiness(pkgs)
out["lock_check"] = {
    "artifacts": len(pkgs),
    "counts": r["counts"],
    "installable": r["installable"],
    "required_exceptions": r["required_exceptions"],
    "graph_edges": sum(len(a["graph_requires"]) for a in pkgs.values()),
    "published_metadata_sha256": {n: a["published_metadata_sha256"] for n, a in sorted(pkgs.items())
                                  if a.get("published_metadata_sha256")},
    "torchvision_receipt_checks_all_true": all(pkgs["torchvision"]["receipt_checks"].values()),
}
print(json.dumps(out, sort_keys=True))
"""


def main() -> int:
    protocol, p_sha = load_protocol()
    lock_raw = (HARNESS / "locks" / "dependency-lock.json").read_bytes()
    lock_sha = sha256_bytes(lock_raw)
    ext_root = Path(protocol["storage"]["root"])
    ext_parent = ext_root.parent
    before_exists = ext_parent.exists() or ext_root.exists()

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    parent_ci = code_identity(REPO)
    assert parent_ci == {"head": head, "harness_clean": True, "dirty": []}, parent_ci

    scratch = REPO / ".scratch" / f"verify-008-{uuid.uuid4().hex[:8]}"
    scratch.mkdir(parents=True)
    try:
        outside_cwd = scratch / "child-cwd"
        outside_cwd.mkdir()
        gpu = protocol["gpu"]["uuid"]
        envs = {
            "install_stage_offline": build_stage_env(dict(os.environ), root=ext_root, protocol=protocol, network=False),
            "acquire_stage_network": build_stage_env(dict(os.environ), root=ext_root, protocol=protocol, network=True),
            "runtime_child_author": build_child_env(
                dict(os.environ), root=ext_root, owner="author",
                run_dir=ext_root / "runs" / "author" / "coordinator-readonly-probe", gpu_uuid=gpu,
            ),
            "runtime_child_reviewer": build_child_env(
                dict(os.environ), root=ext_root, owner="reviewer",
                run_dir=ext_root / "runs" / "reviewer" / "coordinator-readonly-probe", gpu_uuid=gpu,
            ),
        }
        probe_rows = {}
        for name, env in envs.items():
            cp = subprocess.run([sys.executable, "-I", "-B", "-c", PROBE, str(HARNESS), str(REPO)],
                                env=env, cwd=outside_cwd, capture_output=True, text=True, timeout=120)
            assert cp.returncode == 0, f"{name} failed: {cp.stderr}"
            obs = json.loads(cp.stdout)
            assert obs["git_which"] is None, obs
            assert obs["code_identity"] == {"head": head, "harness_clean": True, "dirty": []}, obs
            assert obs["lock_check"]["artifacts"] == 32 and obs["lock_check"]["installable"] is True, obs
            assert obs["lock_check"]["graph_edges"] == 850 and obs["lock_check"]["torchvision_receipt_checks_all_true"], obs
            probe_rows[name] = obs

        sim_root = scratch / "sim-root"
        stage_env = build_stage_env(dict(os.environ), root=sim_root, protocol=protocol, network=False)
        child_env = build_child_env(
            dict(os.environ), root=sim_root, owner="author",
            run_dir=layout(sim_root, "author")["run_owner"] / "cli-probe", gpu_uuid=gpu,
        )

        # Real CLI invocations under offline stage and runtime child environments.
        cli_rows = {}
        for env_label, env in (("install_stage_offline", stage_env), ("runtime_child_author", child_env)):
            for subcmd in ("status", "lock-check"):
                cp_cli = subprocess.run(
                    [sys.executable, "-s", "-P", "-X", "utf8", str(HARNESS / "q0.py"), subcmd],
                    env=env, cwd=outside_cwd, capture_output=True, text=True, timeout=120,
                )
                assert cp_cli.returncode == 0, f"{env_label} {subcmd}: {cp_cli.stderr}"
                body = json.loads(cp_cli.stdout)
                if subcmd == "status":
                    assert body["code_identity"] == {"head": head, "harness_clean": True, "dirty": []}, body
                    cli_rows[f"{env_label}.{subcmd}"] = {"returncode": 0, "code_identity": body["code_identity"]}
                else:
                    assert body["artifacts"] == 32 and body["readiness"]["installable"] is True, body
                    cli_rows[f"{env_label}.{subcmd}"] = {
                        "returncode": 0, "artifacts": body["artifacts"], "counts": body["readiness"]["counts"]
                    }

        # Real CLI install-gate check (`q0.py write-requirements`) inside offline stage environment
        # bound to the clean frozen HEAD, writing only inside `.scratch`.
        rel = {
            "schema": "eldq0-release/2",
            "packet": "WP-0005",
            "stage": "install",
            "released_by": "eld-coordinator",
            "release_commit": "f" * 40,
            "harness_commit": head,
            "protocol_sha256": p_sha,
            "lock_sha256": lock_sha,
            "storage_root": protocol["storage"]["root"],
            "accepted_review": {"reviewer": "eld-q0-reviewer", "report_commit": "a" * 40, "evidence_commit": "b" * 40},
            "accepted_provenance_exceptions": ["torchvision-local-sha256-TOFU"],
        }
        rel_file = scratch / "synthetic-install-release.json"
        rel_file.write_text(json.dumps(rel), encoding="utf-8")
        req_file = scratch / "requirements.lock.txt"
        cp_req = subprocess.run(
            [sys.executable, "-s", "-P", "-X", "utf8", str(HARNESS / "q0.py"),
             "write-requirements", str(req_file), "--release", str(rel_file)],
            env=stage_env, cwd=outside_cwd, capture_output=True, text=True, timeout=120,
        )
        assert cp_req.returncode == 0, cp_req.stderr + cp_req.stdout
        req_bytes = req_file.read_bytes()
        req_lines = req_bytes.decode("utf-8").splitlines()
        assert len(req_lines) == 32, len(req_lines)

        # Unreleased write-requirements inside offline stage environment returns clean exit 2 BLOCKED (never WinError 2).
        never_req = scratch / "never-written.txt"
        cp_unrel = subprocess.run(
            [sys.executable, "-I", "-B", str(HARNESS / "q0.py"), "write-requirements", str(never_req)],
            env=stage_env, cwd=outside_cwd, capture_output=True, text=True, timeout=120,
        )
        assert cp_unrel.returncode == 2 and not never_req.exists(), (cp_unrel.returncode, cp_unrel.stderr)
        unrel_json = json.loads(cp_unrel.stdout)
        assert unrel_json["status"] == "BLOCKED"
        assert unrel_json["failures"][0]["failure_class"] == "EXECUTION_NOT_RELEASED"

        # Meta-check: run test_isolated_git_subprocess.py itself when parent is ALREADY offline stage_env.
        cp_nested = subprocess.run(
            [sys.executable, "-I", "-B", "-m", "unittest", "discover",
             "-s", str(HARNESS / "tests"), "-t", str(HARNESS / "tests"),
             "-p", "test_isolated_git_subprocess.py", "-v"],
            env=stage_env, cwd=REPO, capture_output=True, text=True, timeout=180,
        )
        assert cp_nested.returncode == 0, cp_nested.stderr + cp_nested.stdout
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    after_exists = ext_parent.exists() or ext_root.exists()
    assert not before_exists and not after_exists, (before_exists, after_exists)

    report = {
        "status": "pass",
        "frozen_harness_revision": head,
        "protocol_sha256": p_sha,
        "lock_sha256": lock_sha,
        "external_runtime_root_exists_before": before_exists,
        "external_runtime_root_exists_after": after_exists,
        "scratch_cleaned": not scratch.exists(),
        "isolated_probes": probe_rows,
        "isolated_cli_checks": cli_rows,
        "stage_install_gate_write_requirements_released": {
            "returncode": cp_req.returncode,
            "lines": len(req_lines),
            "sha256": hashlib.sha256(req_bytes).hexdigest(),
        },
        "stage_install_gate_write_requirements_unreleased": {
            "returncode": cp_unrel.returncode,
            "status": unrel_json["status"],
            "failure_class": unrel_json["failures"][0]["failure_class"],
            "file_created": False,
        },
        "nested_stage_unittest_returncode": cp_nested.returncode,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
