"""Real isolated-subprocess regression checks for COORD-Q0-01 (no mocks, no GPU, no installs).

Exercises the actual OS process boundary (`subprocess.run` and `supervise` with `-I -B` and
`-s -P -X utf8`) under both `build_stage_env` and `build_child_env`, proving that:
1. `PATH` remains stripped (`shutil.which('git') is None`) while `Q0_GIT_EXECUTABLE` pins the
   validated host `git.exe` with `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=NUL` and
   `GIT_TERMINAL_PROMPT=0`.
2. `release.code_identity` and `locks.git_blob_reader` / `validate_lock` succeed inside real
   spawned stage and runtime-child processes even when `cwd` is outside the worktree and the
   external runtime root does not exist.
3. Missing, invalid or untrusted Git configurations fail closed with `Q0Failure` (`BLOCKED`)
   rather than unhandled `FileNotFoundError` or `PATH` leakage.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

import support
from q0harness import locks
from q0harness.environment import (GIT_EXECUTABLE_VAR, GIT_ISOLATION_ENV, audit_child_env, audit_stage_env,
                                   build_child_env, build_stage_env, layout, validate_git_executable)
from q0harness.hashing import is_hex, sha256_bytes
from q0harness.outcome import QUALIFIED, Q0Failure
from q0harness.protocol import HARNESS_DIR, REPO_ROOT, load_protocol
from q0harness.release import code_identity
from q0harness.supervisor import supervise

LOCK_PATH = HARNESS_DIR / "locks" / "dependency-lock.json"

ISOLATED_PROBE = textwrap.dedent("""
    import json, os, shutil, sys
    from pathlib import Path

    harness, repo = Path(sys.argv[1]), Path(sys.argv[2])
    sys.path.insert(0, str(harness))
    from q0harness import locks
    from q0harness.environment import GIT_EXECUTABLE_VAR, GIT_ISOLATION_ENV
    from q0harness.outcome import Q0Failure
    from q0harness.release import code_identity

    out = {
        "cwd": os.getcwd(),
        "git_which_on_path": shutil.which("git"),
        "git_executable_var": os.environ.get(GIT_EXECUTABLE_VAR),
        "git_isolation_env": {k: os.environ.get(k) for k in GIT_ISOLATION_ENV},
        "leaked_keys": sorted(k for k in os.environ if k in {
            "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
            "GITHUB_TOKEN", "DASH_STAGE0", "TIME_DIAG", "PYTHONPATH", "PIP_INDEX_URL"
        }),
    }
    try:
        out["code_identity"] = code_identity(repo)
    except Exception as exc:
        out["code_error"] = {"type": type(exc).__name__, "failure_class": getattr(exc, "failure_class", None), "text": str(exc)}
    try:
        lock = locks.load_lock(harness / "locks" / "dependency-lock.json")
        pkgs = locks.validate_lock(lock, locks.git_blob_reader(repo))
        r = locks.readiness(pkgs)
        out["lock"] = {
            "artifacts": len(pkgs),
            "counts": r["counts"],
            "installable": r["installable"],
            "edges": sum(len(a["graph_requires"]) for a in pkgs.values()),
            "receipt_checks_ok": all(pkgs["torchvision"]["receipt_checks"].values()),
        }
    except Exception as exc:
        out["lock_error"] = {"type": type(exc).__name__, "failure_class": getattr(exc, "failure_class", None), "text": str(exc)}
    print(json.dumps(out))
""")

SUPERVISED_SESSION_CHILD = textwrap.dedent("""
    import json, os, sys, uuid
    from pathlib import Path

    harness, repo, root, run_dir, owner = (Path(sys.argv[1]), Path(sys.argv[2]),
                                           Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5])
    sys.path.insert(0, str(harness))
    sys.path.insert(0, str(harness / "tests"))
    import support
    from q0harness import locks
    from q0harness.environment import audit_child_env
    from q0harness.hashing import sha256_bytes
    from q0harness.protocol import load_protocol
    from q0harness.release import code_identity
    from q0harness.session import Session

    audit_child_env(dict(os.environ), root=root, owner=owner, run_dir=run_dir)
    protocol, p_sha = load_protocol()
    lock_raw = (harness / "locks" / "dependency-lock.json").read_bytes()
    lock = json.loads(lock_raw)
    live_code = code_identity(repo)
    # Exercise real git_blob_reader inside the isolated child process.
    reader = locks.git_blob_reader(repo)
    pkgs = locks.validate_lock(lock, reader)
    installed = {a["name"]: a["version"] for a in pkgs.values()}
    model_dir = root / protocol["storage"]["subdirs"]["models"]
    support.write_fake_model_dir(model_dir)
    support.write_notice_dir(root / protocol["storage"]["subdirs"]["notices"])
    manifest_path = run_dir / "model-files-test.json"
    manifest_path.write_text(json.dumps(support.manifest_for_dir(model_dir)), encoding="utf-8")

    # Bind release to the real HEAD observed inside the child (clean during candidate checks;
    # normalize only harness_clean when running uncommitted local edits before freeze).
    bound_code = {"head": live_code["head"], "harness_clean": True, "dirty": []}
    rel = support.fake_release(protocol, p_sha, sha256_bytes(lock_raw), root, owner=owner)
    rel["harness_commit"] = live_code["head"]

    backend = support.FakeBackend(protocol, pkg=f"child_{uuid.uuid4().hex[:8]}", model_dir=model_dir,
                                  modules_cache=Path(os.environ["HF_MODULES_CACHE"]), installed=installed)
    session = Session(protocol=protocol, protocol_sha256=p_sha, lock=lock, lock_sha256=sha256_bytes(lock_raw),
                      release=rel, root=root, owner=owner, run_dir=run_dir, backend=backend, repo_root=repo,
                      expected_root=str(root), forbidden_parents=[], code=bound_code, lock_reader=reader,
                      manifest_path=manifest_path)
    outcome = session.run()
    (run_dir / "child-git-observation.json").write_text(
        json.dumps({"live_code_identity": live_code, "artifacts_bound": len(pkgs)}), encoding="utf-8"
    )
    sys.exit(0 if outcome["status"] == "QUALIFIED_RUNTIME_OBSERVATION" else 1)
""")


class IsolatedGitSubprocess(unittest.TestCase):
    def setUp(self):
        self.scratch = support.new_scratch("git-subproc")
        self.protocol, self.p_sha = load_protocol()
        self.parent_code = code_identity(REPO_ROOT)

    def tearDown(self):
        support.remove_scratch(self.scratch)

    def _polluted_parent_env(self) -> dict:
        env = dict(os.environ)
        env.update({
            "HF_TOKEN": "secret-hf",
            "HUGGING_FACE_HUB_TOKEN": "secret-hub",
            "OPENAI_API_KEY": "secret-openai",
            "ANTHROPIC_API_KEY": "secret-anthropic",
            "GITHUB_TOKEN": "secret-gh",
            "DASH_STAGE0": "indexer",
            "TIME_DIAG": "1",
            "PYTHONPATH": str(self.scratch / "untrusted-py"),
            "PIP_INDEX_URL": "https://evil.example/simple",
        })
        return env

    def test_real_subprocess_git_identity_and_lock_in_stage_and_child_envs(self):
        external_root = Path(self.protocol["storage"]["root"])
        existed_before = external_root.exists()
        child_cwd = self.scratch / "outside-worktree-cwd"
        child_cwd.mkdir()
        parent = self._polluted_parent_env()
        gpu = self.protocol["gpu"]["uuid"]
        envs = {
            "install_stage_offline": build_stage_env(parent, root=external_root, protocol=self.protocol, network=False),
            "acquire_stage_network": build_stage_env(parent, root=external_root, protocol=self.protocol, network=True),
            "runtime_child_author": build_child_env(
                parent, root=external_root, owner="author",
                run_dir=external_root / "runs" / "author" / "readonly-probe", gpu_uuid=gpu,
            ),
            "runtime_child_reviewer": build_child_env(
                parent, root=external_root, owner="reviewer",
                run_dir=external_root / "runs" / "reviewer" / "readonly-probe", gpu_uuid=gpu,
            ),
        }
        for name, env in envs.items():
            for flags in (["-I", "-B"], ["-s", "-P", "-X", "utf8"]):
                with self.subTest(env=name, flags=" ".join(flags)):
                    cp = subprocess.run(
                        [sys.executable, *flags, "-c", ISOLATED_PROBE, str(HARNESS_DIR), str(REPO_ROOT)],
                        env=env, cwd=str(child_cwd), capture_output=True, text=True, timeout=120,
                    )
                    self.assertEqual(cp.returncode, 0, cp.stderr)
                    obs = json.loads(cp.stdout)
                    self.assertIsNone(obs["git_which_on_path"], "PATH must not expose Git's directory")
                    self.assertTrue(Path(obs["git_executable_var"]).is_file())
                    self.assertEqual(obs["git_isolation_env"], GIT_ISOLATION_ENV)
                    self.assertEqual(obs["leaked_keys"], [])
                    self.assertNotIn("code_error", obs, obs.get("code_error"))
                    self.assertNotIn("lock_error", obs, obs.get("lock_error"))
                    self.assertTrue(is_hex(obs["code_identity"]["head"], 40))
                    self.assertEqual(obs["code_identity"], self.parent_code)
                    self.assertEqual(obs["lock"], {
                        "artifacts": 32,
                        "counts": {"publisher-declared": 31, "local-sha256-TOFU": 1, "missing": 0},
                        "installable": True,
                        "edges": 850,
                        "receipt_checks_ok": True,
                    })
        self.assertEqual(external_root.exists(), existed_before, "probe must never create the external runtime root")

    def test_cli_commands_succeed_across_isolated_stage_and_child_envs(self):
        root = self.scratch / "sim-root"
        run_dir = layout(root, "author")["run_owner"] / "cli-probe"
        work_cwd = self.scratch / "cli-cwd"
        work_cwd.mkdir()
        parent = self._polluted_parent_env()
        stage_env = build_stage_env(parent, root=root, protocol=self.protocol, network=False)
        child_env = build_child_env(parent, root=root, owner="author", run_dir=run_dir,
                                    gpu_uuid=self.protocol["gpu"]["uuid"])
        q0_py = str(HARNESS_DIR / "q0.py")
        for label, env in (("stage", stage_env), ("child", child_env)):
            for cmd in (["status"], ["lock-check"]):
                with self.subTest(env=label, cmd=cmd[0]):
                    cp = subprocess.run([sys.executable, "-s", "-P", "-X", "utf8", q0_py, *cmd],
                                        env=env, cwd=str(work_cwd), capture_output=True, text=True, timeout=120)
                    self.assertEqual(cp.returncode, 0, cp.stderr)
                    payload = json.loads(cp.stdout)
                    if cmd[0] == "status":
                        self.assertEqual(payload["protocol_sha256"], self.p_sha)
                        self.assertEqual(payload["code_identity"], self.parent_code)
                    else:
                        self.assertEqual(payload["artifacts"], 32)
                        self.assertTrue(payload["readiness"]["installable"])

        # Exercise _install_gate (write-requirements) inside the offline stage environment.
        lock_sha = sha256_bytes(LOCK_PATH.read_bytes())
        rel = support.fake_release(self.protocol, self.p_sha, lock_sha, self.protocol["storage"]["root"], stage="install")
        rel["harness_commit"] = self.parent_code["head"]
        rel_path = self.scratch / "install-release.json"
        rel_path.write_text(json.dumps(rel), encoding="utf-8")
        req_out = self.scratch / "requirements.lock.txt"
        cp = subprocess.run([sys.executable, "-s", "-P", "-X", "utf8", q0_py, "write-requirements",
                             str(req_out), "--release", str(rel_path)],
                            env=stage_env, cwd=str(work_cwd), capture_output=True, text=True, timeout=120)
        if self.parent_code["harness_clean"]:
            self.assertEqual(cp.returncode, 0, cp.stderr)
            lines = req_out.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 32)
            self.assertTrue(any(l.startswith(f"torchvision==0.28.0+cu130 --hash=sha256:{support.TV_LOCAL_SHA}") for l in lines))
        else:
            self.assertEqual(cp.returncode, 2, cp.stderr)
            rec = json.loads(cp.stdout)
            self.assertEqual(rec["failures"][0]["failure_class"], "EXECUTION_NOT_RELEASED")
            self.assertIn("harness_commit/clean", rec["failures"][0]["evidence"])

    def test_supervised_child_session_runs_real_git_checks(self):
        root = self.scratch / "q0root"
        paths = layout(root, "author")
        run_dir = paths["run_owner"] / "run-subproc-1"
        for sub in ("tmp", "home", "hf-modules", "torch-home", "triton-cache", "inductor-cache",
                    "cuda-cache", "xdg-cache", "pip-cache", "uv-cache"):
            (run_dir / sub).mkdir(parents=True)
        script = self.scratch / "run_child_session.py"
        script.write_text(SUPERVISED_SESSION_CHILD, encoding="utf-8")
        env = build_child_env(self._polluted_parent_env(), root=root, owner="author", run_dir=run_dir,
                              gpu_uuid=self.protocol["gpu"]["uuid"])
        cmd = [sys.executable, "-s", "-P", "-X", "utf8", str(script), str(HARNESS_DIR), str(REPO_ROOT),
               str(root), str(run_dir), "author"]
        rec = supervise(cmd, env=env, cwd=run_dir, run_dir=run_dir, heartbeat_path=run_dir / "heartbeat.json",
                        session_timeout_s=120, stall_s=30, max_log_bytes=4 << 20, default_phase_timeout_s=60, poll_s=0.1)
        stderr_txt = (run_dir / "child.stderr.txt").read_text(encoding="utf-8", errors="replace")
        self.assertEqual(rec["verdict"], "CHILD_COMPLETED", stderr_txt)
        self.assertEqual(rec["child_outcome_status"], QUALIFIED)
        obs = json.loads((run_dir / "child-git-observation.json").read_text(encoding="utf-8"))
        self.assertEqual(obs["live_code_identity"], self.parent_code)
        self.assertEqual(obs["artifacts_bound"], 32)

    def test_missing_invalid_or_untrusted_git_fails_closed(self):
        root = self.scratch / "neg-root"
        run_dir = layout(root, "author")["run_owner"] / "r1"
        stage_env = build_stage_env(self._polluted_parent_env(), root=root, protocol=self.protocol, network=False)
        stripped = {k: v for k, v in stage_env.items() if k != GIT_EXECUTABLE_VAR}
        # In a real subprocess with neither Q0_GIT_EXECUTABLE nor Git on PATH, checks fail closed as Q0Failure.
        cp = subprocess.run([sys.executable, "-I", "-B", "-c", ISOLATED_PROBE, str(HARNESS_DIR), str(REPO_ROOT)],
                            env=stripped, cwd=str(self.scratch), capture_output=True, text=True, timeout=60)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        obs = json.loads(cp.stdout)
        self.assertEqual(obs["code_error"]["type"], "Q0Failure")
        self.assertEqual(obs["code_error"]["failure_class"], "HOST_PRECHECK_FAILED")
        self.assertEqual(obs["lock_error"]["type"], "Q0Failure")
        self.assertEqual(obs["lock_error"]["failure_class"], "DEPENDENCY_LOCK_PENDING")

        # CLI commands in the stripped environment return clean exit 2 BLOCKED JSON, never a traceback.
        # Note: `status` evaluates `_lock()` before `code_identity()`, while `execute` evaluates `code_identity()` first.
        q0_py = str(HARNESS_DIR / "q0.py")
        for subcmd, expected_cls in (
            (["status"], "DEPENDENCY_LOCK_PENDING"),
            (["lock-check"], "DEPENDENCY_LOCK_PENDING"),
            (["execute", "--owner", "author"], "HOST_PRECHECK_FAILED"),
        ):
            cp_cli = subprocess.run([sys.executable, "-I", "-B", q0_py, *subcmd],
                                    env=stripped, cwd=str(self.scratch), capture_output=True, text=True, timeout=60)
            self.assertEqual(cp_cli.returncode, 2, cp_cli.stderr)
            out_cli = json.loads(cp_cli.stdout)
            self.assertEqual(out_cli["status"], "BLOCKED")
            self.assertIsNone(out_cli["accuracy_score"])
            self.assertEqual(out_cli["failures"][0]["failure_class"], expected_cls)

        # Invalid git_executable pins and mutable-root git copies are rejected.
        fake_in_root = root / "venv" / "Scripts" / "git.exe"
        fake_in_root.parent.mkdir(parents=True)
        fake_in_root.write_bytes(b"MZ-fake")
        for bad_git in ("", "git.exe", str(self.scratch / "missing" / "git.exe"), sys.executable):
            with self.subTest(bad_git=bad_git):
                with self.assertRaises(Q0Failure):
                    validate_git_executable(bad_git)
                with self.assertRaises(Q0Failure):
                    build_stage_env(os.environ, root=root, protocol=self.protocol, network=False, git_executable=bad_git)
                with self.assertRaises(Q0Failure):
                    build_child_env(os.environ, root=root, owner="author", run_dir=run_dir,
                                    gpu_uuid=self.protocol["gpu"]["uuid"], git_executable=bad_git)
        with self.assertRaises(Q0Failure) as cm_stage:
            audit_stage_env(stage_env | {GIT_EXECUTABLE_VAR: str(fake_in_root)}, root=root, network=False)
        self.assertEqual(cm_stage.exception.failure_class, "SAFETY_VIOLATION")
        child_env = build_child_env(os.environ, root=root, owner="author", run_dir=run_dir,
                                    gpu_uuid=self.protocol["gpu"]["uuid"])
        with self.assertRaises(Q0Failure) as cm_child:
            audit_child_env(child_env | {GIT_EXECUTABLE_VAR: str(fake_in_root)}, root=root, owner="author", run_dir=run_dir)
        self.assertEqual(cm_child.exception.failure_class, "SAFETY_VIOLATION")

        # An untrusted directory prepended to parent PATH with a fake git.exe does not override system Git or leak to PATH.
        evil_dir = self.scratch / "evil-bin"
        evil_dir.mkdir()
        (evil_dir / "git.exe").write_bytes(b"MZ-untrusted")
        evil_parent = self._polluted_parent_env() | {"PATH": str(evil_dir) + os.pathsep + os.environ.get("PATH", "")}
        evil_parent.pop(GIT_EXECUTABLE_VAR, None)
        s_env = build_stage_env(evil_parent, root=root, protocol=self.protocol, network=False)
        c_env = build_child_env(evil_parent, root=root, owner="author", run_dir=run_dir,
                                gpu_uuid=self.protocol["gpu"]["uuid"])
        for built in (s_env, c_env):
            self.assertNotIn(str(evil_dir), built["PATH"])
            self.assertNotEqual(os.path.normcase(built[GIT_EXECUTABLE_VAR]),
                                os.path.normcase(str(evil_dir / "git.exe")))


if __name__ == "__main__":
    unittest.main()
