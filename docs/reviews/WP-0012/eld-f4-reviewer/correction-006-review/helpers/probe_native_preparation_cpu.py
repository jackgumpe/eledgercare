"""Frozen independent native CPU preparation; no author correction execution or model access.

Carbon's unfinished probe/v4 remain unchanged. This adapts its 16 reviewer tests
to v5's native identity and synthetic Git-report boundary, and adds demonstrated
missing-proof/cleanup failures. Mocked workflow tests are not live resource proof.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
import urllib.request
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
sys.path.insert(0, str(HERE))
import probe_correction_006_failure_paths_cpu as inherited
import run_wp0012_reviewer_rehearsal_v4 as carbon
import run_wp0012_reviewer_rehearsal_v5 as native

# Reuse inherited test logic, preserving its exact file and attributing its author.
inherited.rv4 = native
PRIOR = "379d8c5d607fd248d7f272e412b4ed4a97bc64f6"
CHECKPOINT = "8729db9323e4d2945a30d525b0d67e5ad2a1692e"
SYNTH_REVIEW = "7" * 40
REPORT_PATH = "docs/agent-reports/eld-f4-reviewer/WP-0012/007_2026-11-17_review_eld-f4-reviewer.md"
OUTCOMES: dict = {}


class AdaptedCarbonReviewerTests(inherited.ReviewerV4ReconciliationTests):
    def setUp(self):
        super().setUp()
        self.v4_script = HERE / "run_wp0012_reviewer_rehearsal_v5.py"
        self.valid_rel.update(conversation_id=native.EXPECTED_CONVERSATION_ID,
                              model=native.EXPECTED_MODEL, effort=native.EXPECTED_EFFORT)
        binding = self.valid_rel["author_lease_return"]
        payload = json.loads(self.blobs[binding["path"]])
        payload.update(lease_id="WP-0012-author-SYNTHETIC", returned_utc=self.now_utc.isoformat())
        self.blobs[binding["path"]] = json.dumps(payload).encode()
        binding["sha256"] = native.sha256_hex(self.blobs[binding["path"]])

    def _validate(self, doc, *, blobs=None, allow_synth=True):
        # Synthetic commit/report bytes are supplied only by this CPU test's Git
        # boundary adapter. The actual production validator has no report bypass.
        real_exists, real_cmd, real_bytes = native.git_object_exists, native.run_cmd, native.git_bytes
        def exists(repo, spec):
            return True if spec == f"{SYNTH_REVIEW}^{{commit}}" else real_exists(repo, spec)
        def command(argv, **kwargs):
            if argv[:3] == ["git", "ls-tree", "-r"] and SYNTH_REVIEW in argv:
                return subprocess.CompletedProcess(argv, 0, REPORT_PATH + "\n", "")
            return real_cmd(argv, **kwargs)
        def git_bytes(repo, *args):
            if args == ("cat-file", "-p", f"{SYNTH_REVIEW}:{REPORT_PATH}"):
                return b"# Synthetic CPU-only /007\n- Status: accepted\n"
            return real_bytes(repo, *args)
        with mock.patch.object(native, "git_object_exists", side_effect=exists), \
             mock.patch.object(native, "run_cmd", side_effect=command), \
             mock.patch.object(native, "git_bytes", side_effect=git_bytes):
            return super()._validate(doc, blobs=blobs, allow_synth=allow_synth)


def receipt_kwargs():
    return dict(lease_id="WP-0012-SYNTHETIC-REVIEWER", run_error="Attempt 1 failed",
                cleanup_errors=[], ports_after={"5690": [], "4710": [], "55439": []},
                pg_ctl_status_exit_code=3, api_stop_receipts=[], ui_stop_receipts=[],
                pre_ownership={"sole_model_job_verified": True}, post_ownership={"sole_model_job_verified": True},
                q0_model_immutability_verified=True, persisted_counts={}, run_directories=[],
                postmaster_recorded=None, secrets=[])


def simulated_first_failure(module, fail_at):
    """Only temporary files and mocked service/ownership boundaries; zero actual services."""
    with tempfile.TemporaryDirectory(prefix="wp0012-reviewer-native-") as scratch:
        root = Path(scratch)
        logs = root / "logs"
        out = root / "return.json"
        calls = {"browser": 0, "stop": 0, "status": 0, "ports": 0}
        prep = types.ModuleType("run_wp0012_reviewer_rehearsal")
        prep.verify_q0_readonly_pure_stdlib = lambda repo: {
            "verified_model_files": [], "demo_root_bytes": 0, "demo_drive_free_bytes": 10**12}
        prep.compute_canonical_8table_snapshot = lambda *args: {"counts": {"documents": 0}}
        real_read = Path.read_text
        def read(path, *args, **kwargs):
            if path.name == "pg-local.json":
                return json.dumps(dict(adminPassword="syntheticAdmin", migratorPassword="syntheticMigration",
                                       appPassword="syntheticApp", host="127.0.0.1", appUser="synthetic"))
            if path.name == "postmaster.pid":
                return "999999\n"
            if fail_at == "scrub" and path.name == "owned-api-5690.log":
                raise OSError("synthetic log read failure")
            return real_read(path, *args, **kwargs)
        def run(argv, **kwargs):
            joined = " ".join(map(str, argv))
            if "stop-cluster.ps1" in joined:
                calls["stop"] += 1
                if fail_at == "stop":
                    raise subprocess.TimeoutExpired("synthetic stop", 1)
            if "pg_ctl.exe" in joined:
                calls["status"] += 1
                if fail_at == "status":
                    raise OSError("synthetic status failure")
                return subprocess.CompletedProcess(argv, 3, "", "")
            if "drive_wp0012_edge_workflow.mjs" in joined:
                calls["browser"] += 1
                return subprocess.CompletedProcess(argv, 1, "synthetic first attempt failed", "")
            return subprocess.CompletedProcess(argv, 0, "", "")
        def ports(*args):
            calls["ports"] += 1
            if fail_at == "ports" and calls["ports"] > 1:
                raise OSError("synthetic ports observation failure")
            return {"5690": [], "4710": [], "55439": []}
        def start(**kwargs):
            kwargs["api_log_path"].write_text("Password=syntheticApp\n")
            return mock.Mock(), {"pid": 999998}, mock.Mock(), {"pid": 999997}
        def stop(*args):
            if fail_at == "child":
                raise OSError("synthetic child-stop failure")
            return {"aliveAfter": False}
        args = ["--mode", "live-leased-rehearsal", "--release-commit", "9" * 40,
                "--release-path", "docs/coordination/WP-0012/SYNTHETIC.json",
                "--summary-output", str(root / "summary.json"), "--q0-check-output", str(root / "q0.json"),
                "--resource-return-output", str(out), "--logs-dir", str(logs),
                "--screenshots-dir", str(root / "screenshots")]
        patches = {
            "WRITABLE_DEMO_ROOT": root / "demo", "guard_new_non_overwriting_output_targets": mock.Mock(),
            "git_object_exists": mock.Mock(return_value=True), "git_bytes": mock.Mock(return_value=b"{}"),
            "validate_reviewer_release_contract": mock.Mock(return_value={"lease_id": "WP-0012-SYNTHETIC", "parsed_pre_lease_blobs": {}}),
            "collect_live_ownership_snapshot": mock.Mock(return_value={}),
            "evaluate_gpu_and_model_ownership": mock.Mock(return_value={"sole_model_job_verified": True}),
            "observe_ports": ports, "run_cmd": run, "inspect_process": mock.Mock(return_value={"pid": 999999}),
            "start_owned_services_atomic": start, "stop_owned_process": stop,
        }
        error = None
        with ExitStack() as stack:
            stack.enter_context(mock.patch.dict(sys.modules, {prep.__name__: prep}))
            stack.enter_context(mock.patch.object(Path, "read_text", read))
            for name, value in patches.items():
                stack.enter_context(mock.patch.object(module, name, value))
            try:
                rc = module.main(args)
            except Exception as exc:
                rc = None
                error = f"{type(exc).__name__}: {exc}"
        payload = json.loads(out.read_text()) if out.exists() else None
        return {"receipt": payload, "calls": calls, "exit_code": rc, "error": error,
                "simulation_only": True, "actual_services_started": False}


class NativeSpecificTests(unittest.TestCase):
    def test_missing_007_report_old_accepts_native_rejects(self):
        carbon._verify_commit_has_no_non_accepting_007_report(ROOT, CHECKPOINT)
        with self.assertRaisesRegex(native.ReviewerLeaseGuardError, "Exactly one"):
            native._verify_commit_has_no_non_accepting_007_report(ROOT, CHECKPOINT)
        OUTCOMES["missing_report"] = {"carbon_v4_accepted": True, "native_v5_rejected": True, "real_commit": CHECKPOINT}

    def test_empty_and_commit_only_author_return_old_accepts_native_rejects(self):
        for value in ("5" * 40, {"commit": "5" * 40},
                      {"commit": "5" * 40, "path": "docs/coordination/WP-0012/return.json", "sha256": native.sha256_hex(b"{}") } ):
            doc = {"author_lease_return": value}
            carbon._extract_author_lease_return_binding(doc, lambda path: b"{}", lambda sha: True)
            with self.assertRaises(native.ReviewerLeaseGuardError):
                native._extract_author_lease_return_binding(doc, lambda path: b"{}", lambda sha: True)
        OUTCOMES["missing_return_proof"] = {"carbon_v4_accepted": 3, "native_v5_rejected": 3}

    def test_missing_port_observations_are_unreturned(self):
        kw = receipt_kwargs()
        kw["ports_after"] = {}
        self.assertTrue(carbon.build_reviewer_lease_return_receipt(**kw)["lease_returned"])
        ret = native.build_reviewer_lease_return_receipt(**kw)
        self.assertFalse(ret["lease_returned"])
        self.assertIsNone(ret["returned_utc"])
        OUTCOMES["missing_ports"] = {"carbon_v4_claimed_return": True, "native_v5_return": ret}

    def test_cleanup_exceptions_still_emit_unreturned_receipt(self):
        old = simulated_first_failure(carbon, "stop")
        self.assertIsNone(old["receipt"])
        OUTCOMES["carbon_v4_stop_exception"] = old
        results = {}
        for fail_at in ("clean", "stop", "status", "ports", "scrub", "child"):
            with self.subTest(fail_at=fail_at):
                result = simulated_first_failure(native, fail_at)
                ret = result["receipt"]
                self.assertIsNotNone(ret)
                self.assertEqual(result["calls"]["browser"], 1)
                self.assertEqual(result["calls"]["stop"], 1)
                self.assertEqual(result["calls"]["status"], 1)
                self.assertEqual(result["calls"]["ports"], 2)
                self.assertEqual(ret["lease_returned"], fail_at == "clean")
                if fail_at != "clean":
                    self.assertIsNone(ret["returned_utc"])
                    self.assertEqual(ret["status"], "cleanup_failed_lease_unreturned")
                self.assertNotIn("syntheticApp", json.dumps(ret))
                results[fail_at] = result
        OUTCOMES["native_v5_all_exit_simulations"] = results

    def test_partial_startup_attempts_api_stop_after_ui_stop_exception(self):
        def stops(proc, info, repo):
            if proc is None:
                raise OSError("synthetic UI-stop exception")
            return {"aliveAfter": False}
        with tempfile.TemporaryDirectory() as scratch, \
             mock.patch.object(native.subprocess, "Popen", return_value=mock.Mock(poll=mock.Mock(return_value=1))), \
             mock.patch.object(native, "inspect_process", return_value={"pid": 999998}), \
             mock.patch.object(native, "stop_owned_process", side_effect=stops) as stop:
            path = Path(scratch)
            with self.assertRaisesRegex(native.ReviewerLeaseGuardError, "cleanup unverified"):
                native.start_owned_services_atomic(api_cmd=["synthetic"], api_cwd=path, api_env={},
                    api_log_path=path / "api.log", ui_cmd=["synthetic"], ui_cwd=path, ui_env={},
                    ui_log_path=path / "ui.log", repo_root=ROOT, api_ready_fn=lambda: False)
            self.assertEqual(stop.call_count, 2)


class NativeIdentityTests(AdaptedCarbonReviewerTests):
    # Loaded explicitly to avoid rerunning inherited tests from this subclass.
    def test_native_identity_rejects_each_legacy_field(self):
        self._validate(self.valid_rel)
        for key, value in (("conversation_id", carbon.EXPECTED_CONVERSATION_ID),
                           ("model", carbon.EXPECTED_MODEL), ("effort", carbon.EXPECTED_EFFORT)):
            doc = dict(self.valid_rel)
            doc[key] = value
            with self.assertRaises(native.ReviewerLeaseGuardError):
                self._validate(doc)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if native.run_git(ROOT, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("Freeze helpers and require clean worktree before execution")
    output = (ROOT / args.output_dir).resolve()
    owned = ROOT / "docs/reviews/WP-0012/eld-f4-reviewer/correction-006-review"
    if not output.is_relative_to(owned.resolve()) or output.exists():
        raise RuntimeError("Use a brand-new owned output directory")
    head = native.run_git(ROOT, "rev-parse", "HEAD")
    output.mkdir(parents=True, exist_ok=False)
    stream = io.StringIO()
    result = None
    error = None
    old = None
    owned_children = []
    real_popen = subprocess.Popen
    def tracked_popen(argv, *args, **kwargs):
        proc = real_popen(argv, *args, **kwargs)
        if isinstance(argv, (list, tuple)) and str(argv[0]) == sys.executable and "-c" in argv:
            owned_children.append(proc)
        return proc
    try:
        with mock.patch.object(subprocess, "Popen", side_effect=tracked_popen):
            opener = mock.Mock()
            opener.open.side_effect = OSError("CPU boundary: no author HTTP access")
            with mock.patch.object(urllib.request, "build_opener", return_value=opener):
                old = inherited.run_old_001_baseline_probes()
            suite = unittest.TestSuite([
                unittest.defaultTestLoader.loadTestsFromTestCase(AdaptedCarbonReviewerTests),
                unittest.defaultTestLoader.loadTestsFromTestCase(NativeSpecificTests),
                NativeIdentityTests("test_native_identity_rejects_each_legacy_field"),
            ])
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    except BaseException as exc:
        error = f"{type(exc).__name__}: {exc}"
        stream.write(error + "\n")
    finally:
        (output / "tests.log").write_text(stream.getvalue(), encoding="utf-8", newline="\n")
        child_receipts = []
        for proc in owned_children:
            lingering = proc.poll() is None
            if lingering:
                proc.kill()
                proc.wait(timeout=10)
            child_receipts.append({"pid": proc.pid, "exit_code": proc.poll(), "harness_last_resort_cleanup": lingering})
        ports = native.observe_ports(native.REVIEWER_PORTS, ROOT)
        pg = native.run_cmd([str(ROOT / ".local/tools/pgsql-18.7-1/bin/pg_ctl.exe"), "status", "-D", str(ROOT / ".local/postgres-data")], cwd=ROOT)
        runs = native.WRITABLE_DEMO_ROOT / "runs"
        run_entries = sorted(p.name for p in runs.iterdir()) if runs.exists() else []
        resources = {"reviewer_ports": ports, "pg_status_exit": pg.returncode, "run_entries": run_entries,
                     "actual_services_started": False, "model_import_gpu_query_inference": False, "owned_cpu_children": child_receipts}
        clean = all(ports.get(str(p)) == [] for p in native.REVIEWER_PORTS) and pg.returncode == 3 and run_entries == [] and all(not r["harness_last_resort_cleanup"] for r in child_receipts)
        (output / "resource-observation.json").write_text(json.dumps(resources, indent=2) + "\n")
        summary = {"schema": "eledgercare.wp0012.native-reviewer-preparation/1", "utc": datetime.now(timezone.utc).isoformat(),
                   "executing_head": head, "checkpoint": CHECKPOINT, "authority": "3bc2ba5cf5db6698d71c99fccc957e54936fb6c2",
                   "canonical_007": "held", "author_correction_executed": False,
                   "old_001_baseline": old, "tests_run": result.testsRun if result else 0,
                   "tests_passed": result.wasSuccessful() if result else False, "exception": error,
                   "own_resources_idle": clean, "findings": OUTCOMES}
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0 if result and result.wasSuccessful() and clean and error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
