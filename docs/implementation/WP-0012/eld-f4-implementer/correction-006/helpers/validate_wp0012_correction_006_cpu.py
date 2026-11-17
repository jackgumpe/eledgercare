"""CPU-only correction verification: syntax, synthetic release, actual old/new fault injection.
No model/renderer imports, GPU queries, database startup or API/UI service startup.
Original Carbon/high draft preserved at d9de3bf; native continuation keeps affected tests
and removes the unnecessary broad live disabled-OCR and database rerun.
"""
from __future__ import annotations

import argparse
import ast
import copy
from datetime import datetime, timedelta, timezone
from contextlib import ExitStack
import hashlib
import http.server
import importlib.util
import io
import json
import os
from pathlib import Path
import py_compile
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

SCRIPT_PATH = Path(__file__).resolve()
HELPERS_DIR = SCRIPT_PATH.parent
CORRECTION_DIR = HELPERS_DIR.parent
AUTHOR_WP0012_DIR = CORRECTION_DIR.parent
EVIDENCE_DIR = CORRECTION_DIR / "evidence"
LOGS_DIR = EVIDENCE_DIR / "logs"
SCREENSHOTS_DIR = EVIDENCE_DIR / "screenshots"
if str(HELPERS_DIR) not in sys.path:
    sys.path.insert(0, str(HELPERS_DIR))

import run_wp0012_rehearsal as drv  # noqa: E402

REPO_ROOT = drv.REPO_ROOT


def _load_preserved_001_driver():
    old_path = AUTHOR_WP0012_DIR / "helpers" / "run_wp0012_rehearsal.py"
    spec = importlib.util.spec_from_file_location("author_001_rehearsal_readonly", str(old_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load preserved /001 helper: {old_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


OLD_001_DRV = _load_preserved_001_driver()

FORBIDDEN_IMPORT_PREFIXES = (
    "torch",
    "transformers",
    "safetensors",
    "accelerate",
    "huggingface_hub",
    "tokenizers",
    "pypdfium2",
    "PIL",
    "torchvision",
    "qualification",
    "research",
    "evaluation",
)

EXPECTED_PRESERVED_006_BASE_COUNT = 3683


def make_synthetic_valid_006_release(actual_head: str, now_utc: datetime) -> tuple[dict, dict[str, bytes]]:
    blobs = dict(drv.SYNTHETIC_SAMPLE_BLOBS)
    rel = {
        "schema": "eledgercare.wp0012-rehearsal-release/1",
        "synthetic_test_only": True,
        "packet": "WP-0012",
        "owner": "eld-f4-implementer",
        "conversation_id": "/root/product_author_continuation",
        "model": "native-codex-backend-unexposed",
        "effort": "xhigh-requested",
        "source_commit": drv.ACCEPTED_F4_FINAL_SOURCE_SHA,
        "executing_head": actual_head,
        "prior_changes_requested_review_002": drv.PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA,
        "accepted_preparation_review": drv.SYNTHETIC_PLACEHOLDER_ACCEPTING_007,
        "product_tree_objects": dict(drv.EXPECTED_PRODUCT_TREES),
        "pinned_digests": dict(drv.EXPECTED_PINNED_DIGESTS),
        "lease_id": "WP-0012-author-003-SYNTHETIC-TEST-20261117T163000Z",
        "gpu_uuid": drv.EXPECTED_GPU_UUID,
        "released_utc": (now_utc - timedelta(minutes=5)).isoformat(),
        "expires_utc": (now_utc + timedelta(hours=3)).isoformat(),
        "max_model_attempts": 2,
        "readonly_q0_root": str(drv.EXPECTED_Q0_ROOT),
        "runtime_root": str(drv.EXPECTED_DEMO_RUNTIME_ROOT),
        "database": drv.OWNED_REHEARSAL_DB,
        "ports": {"api": 5590, "ui": 4610, "postgres": 55438},
        "storage_cap_bytes": 4_294_967_296,
        "free_floor_bytes": 21_474_836_480,
        "guards": {
            "load_timeout_s": 1800,
            "one_page_timeout_s": 1800,
            "three_page_timeout_s": 3600,
            "stall_timeout_s": 300,
            "max_raw_output_bytes": 16_777_216,
            "max_log_bytes": 67_108_864,
        },
        "allow_test_content": False,
        "torchvision_local_sha256_TOFU_accepted": True,
        "observation_files": {
            "ownership-before.json": {
                "path": "docs/coordination/WP-0012-0013/synthetic-author-003/ownership-before.json",
                "sha256": drv.sha256_bytes(blobs["docs/coordination/WP-0012-0013/synthetic-author-003/ownership-before.json"]),
            },
            "host-before.json": {
                "path": "docs/coordination/WP-0012-0013/synthetic-author-003/host-before.json",
                "sha256": drv.sha256_bytes(blobs["docs/coordination/WP-0012-0013/synthetic-author-003/host-before.json"]),
            },
            "model-before.json": {
                "path": "docs/coordination/WP-0012-0013/synthetic-author-003/model-before.json",
                "sha256": drv.sha256_bytes(blobs["docs/coordination/WP-0012-0013/synthetic-author-003/model-before.json"]),
            },
        },
    }
    return rel, blobs


def _reap_owned_test_children(procs_and_idents: list[tuple[subprocess.Popen, dict | None]], fhs: list) -> bool:
    """Safely terminates only short-lived CPU test children spawned by this test suite (verified by PID + CreateFileTime)."""
    for proc, ident in procs_and_idents:
        if proc.poll() is None:
            if ident and ident.get("create_filetime") is not None:
                if drv.is_exact_process_alive(int(proc.pid), int(ident["create_filetime"])):
                    proc.kill()
                    proc.wait(timeout=10)
            else:
                proc.kill()
                proc.wait(timeout=10)
    for fh in fhs:
        if fh is not None and not getattr(fh, "closed", True):
            fh.close()
    return all(
        (ident is None) or (not drv.is_exact_process_alive(int(proc.pid), int(ident["create_filetime"])))
        for proc, ident in procs_and_idents
    )


class Wp0012Correction006GuardTests(unittest.TestCase):
    SYNTH_REL_COMMIT = drv.SYNTHETIC_PLACEHOLDER_RELEASE_COMMIT
    SYNTH_REL_PATH = "docs/coordination/WP-0012/releases/synthetic-author.json"

    def setUp(self) -> None:
        self.now_utc = datetime(2026, 11, 17, 16, 30, 0, tzinfo=timezone.utc)
        self.actual_head = drv.git_stdout(REPO_ROOT, ["rev-parse", "HEAD"]).lower()
        self.valid_rel, self.blobs = make_synthetic_valid_006_release(self.actual_head, self.now_utc)

    def _validate(
        self,
        doc: dict,
        *,
        release_commit: str | None = None,
        release_path: str | None = None,
        require_clean_worktree: bool = False,
        allow_synthetic: bool = True,
    ) -> dict:
        synth_ok = {drv.SYNTHETIC_PLACEHOLDER_ACCEPTING_007, "9" * 40}
        return drv.validate_release_contract(
            doc,
            root=REPO_ROOT,
            release_commit=release_commit or self.SYNTH_REL_COMMIT,
            release_path=release_path or self.SYNTH_REL_PATH,
            now_utc=self.now_utc,
            blob_loader=lambda p: self.blobs[p],
            commit_exists_fn=lambda sha: (sha in synth_ok) or drv.git_object_exists(REPO_ROOT, f"{sha}^{{commit}}"),
            require_clean_worktree=require_clean_worktree,
            allow_synthetic_test_only=allow_synthetic,
        )

    # --- 1. F12-B1 Old-Fails / New-Passes Partial-Startup Cleanup ---
    def test_01_f12_b1_case_a_ui_early_exit_old_leaks_and_new_cleans_up_with_secret_scrub(self) -> None:
        real_popen = subprocess.Popen
        fake_secret = "FAKE_TEST_SECRET_TOKEN_B1A_99281"

        # Old /001 behavior: leaks api_proc alive & api_fh open
        old_procs: list[tuple[subprocess.Popen, dict | None]] = []
        old_fhs: list = []

        def fake_popen_old(cmd, *args, **kwargs):
            if Path(str(cmd[0])).name.lower() not in ("dotnet", "dotnet.exe", "node", "node.exe"):
                return real_popen(cmd, *args, **kwargs)
            if kwargs.get("stdout") is not None:
                old_fhs.append(kwargs["stdout"])
            if len(old_procs) == 0:
                p = real_popen([sys.executable, "-B", "-c", "import time; time.sleep(60)"], *args, **kwargs)
            else:
                p = real_popen([sys.executable, "-B", "-c", "import sys; sys.exit(1)"], *args, **kwargs)
            old_procs.append((p, drv.get_win32_process_identity(p.pid)))
            return p

        with tempfile.TemporaryDirectory() as td_old:
            try:
                with (
                    mock.patch.object(OLD_001_DRV, "assert_ports_unbound", return_value={"5590": [], "4610": []}),
                    mock.patch.object(
                        OLD_001_DRV,
                        "observe_ports",
                        side_effect=lambda ports=(5590,): {"5590": [{"owningPid": old_procs[0][0].pid}]} if old_procs else {"5590": []},
                    ),
                    mock.patch.object(OLD_001_DRV.subprocess, "Popen", side_effect=fake_popen_old),
                ):
                    with self.assertRaisesRegex(RuntimeError, "Owned UI exited early"):
                        OLD_001_DRV.start_api_and_ui(
                            app_conn_str="Host=127.0.0.1;Port=55438;Database=dummy",
                            ocr_enabled=True,
                            leased_gpu_uuid=drv.EXPECTED_GPU_UUID,
                            log_dir=Path(td_old),
                            tag="old-b1a",
                        )
                    old_api_proc, old_api_ident = old_procs[0]
                    self.assertTrue(drv.is_exact_process_alive(old_api_proc.pid, old_api_ident["create_filetime"]))
                    self.assertFalse(old_fhs[0].closed)
            finally:
                self.assertTrue(_reap_owned_test_children(old_procs, old_fhs))

        # New /006 behavior: kills api_proc, closes api_fh & ui_fh, and scrubs secrets
        new_procs: list[tuple[subprocess.Popen, dict | None]] = []
        new_fhs: list = []

        def fake_popen_new(cmd, *args, **kwargs):
            if Path(str(cmd[0])).name.lower() not in ("dotnet", "dotnet.exe", "node", "node.exe"):
                return real_popen(cmd, *args, **kwargs)
            if kwargs.get("stdout") is not None:
                new_fhs.append(kwargs["stdout"])
            if len(new_procs) == 0:
                p = real_popen(
                    [sys.executable, "-B", "-c", f"import sys, time; print('conn={fake_secret}', flush=True); time.sleep(60)"],
                    *args,
                    **kwargs,
                )
            else:
                p = real_popen(
                    [sys.executable, "-B", "-c", f"import sys; print('ui_err={fake_secret}', flush=True); sys.exit(1)"],
                    *args,
                    **kwargs,
                )
            new_procs.append((p, drv.get_win32_process_identity(p.pid)))
            return p

        with tempfile.TemporaryDirectory() as td_new:
            td_p = Path(td_new)
            try:
                with (
                    mock.patch.object(drv, "assert_ports_unbound", return_value={"5590": [], "4610": []}),
                    mock.patch.object(
                        drv,
                        "observe_ports",
                        side_effect=lambda ports=(5590,): {"5590": [{"owningPid": new_procs[0][0].pid}]} if new_procs else {"5590": []},
                    ),
                    mock.patch.object(drv.subprocess, "Popen", side_effect=fake_popen_new),
                ):
                    with self.assertRaisesRegex(RuntimeError, "Owned UI exited early"):
                        drv.start_api_and_ui(
                            app_conn_str=f"Host=127.0.0.1;Port=55438;Database=dummy;Password={fake_secret}",
                            ocr_enabled=True,
                            leased_gpu_uuid=drv.EXPECTED_GPU_UUID,
                            log_dir=td_p,
                            tag="new-b1a",
                            secrets=[fake_secret],
                        )
                new_api_proc, new_api_ident = new_procs[0]
                self.assertFalse(drv.is_exact_process_alive(new_api_proc.pid, new_api_ident["create_filetime"]))
                self.assertTrue(all(fh.closed for fh in new_fhs))
                for lf in td_p.glob("*.log"):
                    txt = lf.read_text(encoding="utf-8")
                    self.assertNotIn(fake_secret, txt)
            finally:
                self.assertTrue(_reap_owned_test_children(new_procs, new_fhs))

    def test_02_f12_b1_case_b_api_bind_timeout_old_leaks_and_new_cleans_up(self) -> None:
        real_popen = subprocess.Popen

        # Old /001 leaks api_proc on 45s bind timeout
        old_procs: list[tuple[subprocess.Popen, dict | None]] = []
        old_fhs: list = []

        def fake_popen_old(cmd, *args, **kwargs):
            if Path(str(cmd[0])).name.lower() not in ("dotnet", "dotnet.exe", "node", "node.exe"):
                return real_popen(cmd, *args, **kwargs)
            if kwargs.get("stdout") is not None:
                old_fhs.append(kwargs["stdout"])
            p = real_popen([sys.executable, "-B", "-c", "import time; time.sleep(60)"], *args, **kwargs)
            old_procs.append((p, drv.get_win32_process_identity(p.pid)))
            return p

        old_clock = iter([100.0, 100.1, 146.0])
        with tempfile.TemporaryDirectory() as td_old:
            try:
                with (
                    mock.patch.object(OLD_001_DRV, "assert_ports_unbound", return_value={"5590": [], "4610": []}),
                    mock.patch.object(OLD_001_DRV, "observe_ports", return_value={"5590": []}),
                    mock.patch.object(OLD_001_DRV.subprocess, "Popen", side_effect=fake_popen_old),
                    mock.patch.object(OLD_001_DRV.time, "monotonic", side_effect=lambda: next(old_clock, 200.0)),
                ):
                    with self.assertRaisesRegex(RuntimeError, "did not bind 5590"):
                        OLD_001_DRV.start_api_and_ui(
                            app_conn_str="Host=127.0.0.1;Port=55438;Database=dummy",
                            ocr_enabled=False,
                            leased_gpu_uuid="",
                            log_dir=Path(td_old),
                            tag="old-b1b",
                        )
                    self.assertTrue(drv.is_exact_process_alive(old_procs[0][0].pid, old_procs[0][1]["create_filetime"]))
            finally:
                self.assertTrue(_reap_owned_test_children(old_procs, old_fhs))

        # New /006 kills api_proc & closes api_fh on 45s bind timeout
        new_procs: list[tuple[subprocess.Popen, dict | None]] = []
        new_fhs: list = []

        def fake_popen_new(cmd, *args, **kwargs):
            if Path(str(cmd[0])).name.lower() not in ("dotnet", "dotnet.exe", "node", "node.exe"):
                return real_popen(cmd, *args, **kwargs)
            if kwargs.get("stdout") is not None:
                new_fhs.append(kwargs["stdout"])
            p = real_popen([sys.executable, "-B", "-c", "import time; time.sleep(60)"], *args, **kwargs)
            new_procs.append((p, drv.get_win32_process_identity(p.pid)))
            return p

        new_clock = iter([100.0, 100.1, 146.0])
        with tempfile.TemporaryDirectory() as td_new:
            try:
                with (
                    mock.patch.object(drv, "assert_ports_unbound", return_value={"5590": [], "4610": []}),
                    mock.patch.object(drv, "observe_ports", return_value={"5590": []}),
                    mock.patch.object(drv.subprocess, "Popen", side_effect=fake_popen_new),
                    mock.patch.object(drv.time, "monotonic", side_effect=lambda: next(new_clock, 200.0)),
                ):
                    with self.assertRaisesRegex(RuntimeError, "did not bind 5590"):
                        drv.start_api_and_ui(
                            app_conn_str="Host=127.0.0.1;Port=55438;Database=dummy",
                            ocr_enabled=False,
                            leased_gpu_uuid="",
                            log_dir=Path(td_new),
                            tag="new-b1b",
                        )
                self.assertFalse(drv.is_exact_process_alive(new_procs[0][0].pid, new_procs[0][1]["create_filetime"]))
                self.assertTrue(all(fh.closed for fh in new_fhs))
            finally:
                self.assertTrue(_reap_owned_test_children(new_procs, new_fhs))

    def test_03_f12_b1_case_c_ui_readiness_timeout_cleans_both_api_and_ui(self) -> None:
        real_popen = subprocess.Popen
        procs: list[tuple[subprocess.Popen, dict | None]] = []
        fhs: list = []

        def fake_popen_both(cmd, *args, **kwargs):
            if Path(str(cmd[0])).name.lower() not in ("dotnet", "dotnet.exe", "node", "node.exe"):
                return real_popen(cmd, *args, **kwargs)
            if kwargs.get("stdout") is not None:
                fhs.append(kwargs["stdout"])
            p = real_popen([sys.executable, "-B", "-c", "import time; time.sleep(60)"], *args, **kwargs)
            procs.append((p, drv.get_win32_process_identity(p.pid)))
            return p

        clock_vals = iter([100.0, 100.1, 200.0, 200.1, 295.0])
        with tempfile.TemporaryDirectory() as td:
            try:
                with (
                    mock.patch.object(drv, "assert_ports_unbound", return_value={"5590": [], "4610": []}),
                    mock.patch.object(
                        drv,
                        "observe_ports",
                        side_effect=lambda ports=(5590,): {"5590": [{"owningPid": procs[0][0].pid}]} if procs else {"5590": []},
                    ),
                    mock.patch.object(drv.subprocess, "Popen", side_effect=fake_popen_both),
                    mock.patch.object(drv.time, "monotonic", side_effect=lambda: next(clock_vals, 400.0)),
                ):
                    with self.assertRaisesRegex(RuntimeError, "did not respond 200 on 4610"):
                        drv.start_api_and_ui(
                            app_conn_str="Host=127.0.0.1;Port=55438;Database=dummy",
                            ocr_enabled=True,
                            leased_gpu_uuid=drv.EXPECTED_GPU_UUID,
                            log_dir=Path(td),
                            tag="new-b1c",
                        )
                self.assertEqual(len(procs), 2)
                for p, ident in procs:
                    self.assertFalse(drv.is_exact_process_alive(p.pid, ident["create_filetime"]))
                self.assertTrue(all(fh.closed for fh in fhs))
            finally:
                self.assertTrue(_reap_owned_test_children(procs, fhs))

    def test_04_stop_proc_never_taskkills_mismatched_create_filetime(self) -> None:
        fake_proc = mock.MagicMock()
        fake_proc.pid = os.getpid()
        fake_proc.poll.return_value = None
        fake_proc.terminate.side_effect = lambda: setattr(fake_proc.poll, "return_value", 0)
        fh = io.StringIO()
        with mock.patch.object(drv.subprocess, "run") as spy_run:
            drv.stop_proc(fake_proc, fh, expected_identity={"pid": os.getpid(), "create_filetime": 1})
            taskkill_calls = [c for c in spy_run.call_args_list if "taskkill" in str(c)]
            self.assertEqual(len(taskkill_calls), 0)
        self.assertTrue(fh.closed)

    # --- 2. F12-B2 Stop-on-Failure Audits, Secret Scrubbing, Lease Return, & Output Guard ---
    def test_05_f12_b2_stop_on_failure_old_skips_and_new_executes_audits_scrubs_and_writes_lease_return(self) -> None:
        fake_pwd = "SUPER_SECRET_PG_PASS_F12B2_7741"
        orig_read_text = Path.read_text

        def mock_read_text(self_path: Path, *a, **k) -> str:
            if self_path.name == "pg-local.json":
                return json.dumps(
                    {
                        "host": "127.0.0.1",
                        "port": 55438,
                        "appUser": "app_u",
                        "appPassword": fake_pwd,
                        "migratorUser": "mig_u",
                        "migratorPassword": "MIG_" + fake_pwd,
                        "adminUser": "adm_u",
                        "adminPassword": "ADM_" + fake_pwd,
                    }
                )
            if self_path.name == "postmaster.pid":
                return "54321\n"
            return orig_read_text(self_path, *a, **k)

        fake_att_rows = json.dumps(
            [
                {
                    "attempt_id": "11111111-1111-1111-1111-111111111111",
                    "document_id": "22222222-2222-2222-2222-222222222222",
                    "attempt_number": 1,
                    "fencing_token": 1,
                    "status": "failed",
                    "phase": "inferring",
                    "run_directory_name": "run-01",
                    "supervisor_pid": 999991,
                    "supervisor_create_filetime": 101,
                    "launcher_pid": 999993,
                    "launcher_create_filetime": 103,
                    "worker_pid": 999994,
                    "worker_create_filetime": 104,
                    "exit_code": 1,
                }
            ]
        )

        # Verify old /001 skips worker checks and owner-lease-return.json on Phase A failure
        with tempfile.TemporaryDirectory() as td_old:
            old_demo = Path(td_old) / "demo-old"
            (old_demo / "runs").mkdir(parents=True)
            old_worker_spy = mock.MagicMock(return_value=0)
            with (
                mock.patch.object(OLD_001_DRV, "EXPECTED_DEMO_RUNTIME_ROOT", old_demo),
                mock.patch.object(OLD_001_DRV, "git_object_exists", return_value=True),
                mock.patch.object(OLD_001_DRV, "git_bytes", return_value=b"{}"),
                mock.patch.object(
                    OLD_001_DRV,
                    "validate_release_contract",
                    return_value={"lease_id": "WP-0012-old-fail", "gpu_uuid": drv.EXPECTED_GPU_UUID},
                ),
                mock.patch.object(OLD_001_DRV, "inspect_readonly_q0_and_demo_roots_cpu", return_value={"writable_demo_root_exists": True}),
                mock.patch.object(OLD_001_DRV, "assert_ports_unbound", return_value={"5590": [], "4610": [], "55438": []}),
                mock.patch.object(OLD_001_DRV, "get_win32_process_identity", return_value={"pid": 54321, "alive": True}),
                mock.patch.object(OLD_001_DRV, "run_psql_query", return_value="0"),
                mock.patch.object(
                    OLD_001_DRV,
                    "start_api_and_ui",
                    side_effect=lambda *, log_dir, **kw: (
                        log_dir.mkdir(parents=True, exist_ok=True)
                        or (
                            mock.MagicMock(pid=999991, poll=lambda: 0),
                            {"fh": None, "identity": {"pid": 999991}},
                            mock.MagicMock(pid=999992, poll=lambda: 0),
                            {"fh": None, "identity": {"pid": 999992}},
                        )
                    ),
                ),
                mock.patch.object(OLD_001_DRV, "ProcessMemorySampler") as old_samp,
                mock.patch.object(OLD_001_DRV, "stop_proc"),
                mock.patch.object(OLD_001_DRV, "count_ocr_worker_processes", old_worker_spy),
                mock.patch.object(
                    OLD_001_DRV.subprocess,
                    "run",
                    side_effect=lambda argv, **kw: subprocess.CompletedProcess(
                        argv,
                        1 if "drive_rehearsal_edge.mjs" in " ".join(map(str, argv)) else 0,
                        stdout="",
                        stderr=f"STOP-ON-FAILURE Password={fake_pwd}",
                    ),
                ),
                mock.patch.object(Path, "read_text", mock_read_text),
            ):
                old_samp.return_value.stop.return_value = {}
                with self.assertRaisesRegex(RuntimeError, "Live Phase A stopped/failed"):
                    OLD_001_DRV.execute_live_rehearsal(release_commit="d" * 40, release_path="docs/coordination/WP-0012/sim.json")
            self.assertEqual(old_worker_spy.call_count, 0)
            self.assertFalse((old_demo / "rehearsal-evidence" / "WP-0012-old-fail" / "owner-lease-return.json").exists())

        # Verify corrected /006 runs worker/port/model audits, scrubs secrets, writes owner-lease-return.json, and stops after 1 Edge call
        with tempfile.TemporaryDirectory() as td_new:
            new_demo = Path(td_new) / "demo-new"
            (new_demo / "runs" / "run-01").mkdir(parents=True)
            new_worker_spy = mock.MagicMock(return_value=0)
            new_ports_spy = mock.MagicMock(return_value={"5590": [], "4610": [], "55438": []})
            edge_invocations = 0

            def fake_subproc_run(argv, **kw):
                nonlocal edge_invocations
                joined = " ".join(map(str, argv))
                if "drive_rehearsal_edge.mjs" in joined:
                    edge_invocations += 1
                    return subprocess.CompletedProcess(
                        argv,
                        1,
                        stdout=f"conn_leak={fake_pwd}",
                        stderr=f"STOP-ON-FAILURE Password={fake_pwd}",
                    )
                return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

            def fake_psql(settings, db, sql, as_app_user=False):
                if "count(*)" in sql:
                    return "0"
                return fake_att_rows

            def fake_start_new(*, log_dir: Path, **kw):
                log_dir.mkdir(parents=True, exist_ok=True)
                (log_dir / "api-5590-phase-a-leased.log").write_text(
                    f"Startup ConnectionStrings__Runtime=...Password={fake_pwd}\n",
                    encoding="utf-8",
                )
                return (
                    mock.MagicMock(pid=999991, poll=lambda: 0),
                    {"fh": None, "identity": {"pid": 999991, "create_filetime": 101}},
                    mock.MagicMock(pid=999992, poll=lambda: 0),
                    {"fh": None, "identity": {"pid": 999992, "create_filetime": 102}},
                )

            explicit_out = Path(td_new) / "explicit-return.json"
            with (
                mock.patch.object(drv, "EXPECTED_DEMO_RUNTIME_ROOT", new_demo),
                mock.patch.object(drv, "git_object_exists", return_value=True),
                mock.patch.object(drv, "git_bytes", return_value=b"{}"),
                mock.patch.object(
                    drv,
                    "validate_release_contract",
                    return_value={"lease_id": "WP-0012-new-fail", "gpu_uuid": drv.EXPECTED_GPU_UUID},
                ),
                mock.patch.object(drv, "inspect_readonly_q0_and_demo_roots_cpu", return_value={"writable_demo_root_exists": True}),
                mock.patch.object(drv, "assert_ports_unbound", new_ports_spy),
                mock.patch.object(drv, "get_win32_process_identity", return_value={"pid": 54321, "create_filetime": 555, "alive": True}),
                mock.patch.object(drv, "is_exact_process_alive", return_value=False),
                mock.patch.object(drv, "run_psql_query", side_effect=fake_psql),
                mock.patch.object(drv, "start_api_and_ui", side_effect=fake_start_new),
                mock.patch.object(drv, "ProcessMemorySampler") as new_samp,
                mock.patch.object(drv, "stop_proc"),
                mock.patch.object(drv, "count_ocr_worker_processes", new_worker_spy),
                mock.patch.object(drv.subprocess, "run", side_effect=fake_subproc_run),
                mock.patch.object(Path, "read_text", mock_read_text),
            ):
                new_samp.return_value.stop.return_value = {"api_pid": 999991, "worker_peak_working_set_bytes": 0}
                with self.assertRaisesRegex(RuntimeError, "Live Phase A stopped/failed"):
                    drv.execute_live_rehearsal(
                        release_commit="d" * 40,
                        release_path="docs/coordination/WP-0012/sim.json",
                        explicit_output_path=explicit_out,
                    )

            self.assertEqual(edge_invocations, 1)  # Zero automatic retries!
            self.assertGreaterEqual(new_worker_spy.call_count, 2)  # Pre-launch + post-failure!
            self.assertGreaterEqual(new_ports_spy.call_count, 2)  # Pre-launch + post-failure!

            ret_file = new_demo / "rehearsal-evidence" / "WP-0012-new-fail" / "owner-lease-return.json"
            self.assertTrue(ret_file.is_file())
            self.assertTrue(explicit_out.is_file())
            ret_doc = json.loads(ret_file.read_text(encoding="utf-8"))
            self.assertEqual(ret_doc["status"], "failed_stopped")
            self.assertTrue(ret_doc["clean_return_verified"])
            self.assertEqual(ret_doc["failure_stage"], "phase-a-live-browser")
            self.assertEqual(ret_doc["model_attempts_executed"], 1)
            self.assertEqual(ret_doc["ocr_worker_processes_running"], 0)
            self.assertTrue(ret_doc["ports_unbound_verified"])
            self.assertTrue(ret_doc["q0_model_18_objects_sha256_verified_after_run"])
            self.assertTrue(ret_doc["logs_scrubbed"])

            for artifact in (new_demo / "rehearsal-evidence" / "WP-0012-new-fail").rglob("*"):
                if artifact.is_file():
                    self.assertNotIn(fake_pwd, artifact.read_text(encoding="utf-8"))

    def test_06_f12_b2_lingering_worker_sets_clean_return_verified_false_honestly(self) -> None:
        orig_read_text = Path.read_text

        def mock_read_text(self_path: Path, *a, **k) -> str:
            if self_path.name == "pg-local.json":
                return '{"host":"127.0.0.1","port":55438,"appUser":"u","appPassword":"p","adminUser":"a","adminPassword":"ap"}'
            if self_path.name == "postmaster.pid":
                return "54321\n"
            return orig_read_text(self_path, *a, **k)

        with tempfile.TemporaryDirectory() as td:
            sim_demo = Path(td) / "demo-linger"
            (sim_demo / "runs").mkdir(parents=True)
            # 0 workers pre-launch, 1 lingering worker post-failure
            worker_counts = iter([0, 1])
            with (
                mock.patch.object(drv, "EXPECTED_DEMO_RUNTIME_ROOT", sim_demo),
                mock.patch.object(drv, "git_object_exists", return_value=True),
                mock.patch.object(drv, "git_bytes", return_value=b"{}"),
                mock.patch.object(
                    drv,
                    "validate_release_contract",
                    return_value={"lease_id": "WP-0012-linger", "gpu_uuid": drv.EXPECTED_GPU_UUID},
                ),
                mock.patch.object(drv, "inspect_readonly_q0_and_demo_roots_cpu", return_value={"writable_demo_root_exists": True}),
                mock.patch.object(drv, "assert_ports_unbound", return_value={"5590": [], "4610": [], "55438": []}),
                mock.patch.object(drv, "get_win32_process_identity", return_value={"pid": 54321, "create_filetime": 1, "alive": True}),
                mock.patch.object(drv, "run_psql_query", side_effect=lambda s, d, q, **kw: "0" if "count(*)" in q else "[]"),
                mock.patch.object(
                    drv,
                    "start_api_and_ui",
                    return_value=(
                        mock.MagicMock(pid=11, poll=lambda: 0),
                        {"fh": None, "identity": {"pid": 11}},
                        mock.MagicMock(pid=12, poll=lambda: 0),
                        {"fh": None, "identity": {"pid": 12}},
                    ),
                ),
                mock.patch.object(drv, "ProcessMemorySampler") as samp,
                mock.patch.object(drv, "stop_proc"),
                mock.patch.object(drv, "count_ocr_worker_processes", side_effect=lambda: next(worker_counts, 1)),
                mock.patch.object(
                    drv.subprocess,
                    "run",
                    side_effect=lambda argv, **kw: subprocess.CompletedProcess(
                        argv,
                        1 if "drive_rehearsal_edge.mjs" in " ".join(map(str, argv)) else 0,
                        stdout="",
                        stderr="FAIL",
                    ),
                ),
                mock.patch.object(Path, "read_text", mock_read_text),
            ):
                samp.return_value.stop.return_value = {}
                with self.assertRaises(RuntimeError):
                    drv.execute_live_rehearsal(release_commit="d" * 40, release_path="docs/coordination/WP-0012/sim.json")

            ret_doc = json.loads(
                (sim_demo / "rehearsal-evidence" / "WP-0012-linger" / "owner-lease-return.json").read_text(encoding="utf-8")
            )
            self.assertEqual(ret_doc["status"], "failed_stopped")
            self.assertFalse(ret_doc["clean_return_verified"])
            self.assertEqual(ret_doc["ocr_worker_processes_running"], 1)
            self.assertTrue(any("ocr_worker_processes_running=1" in e for e in ret_doc["cleanup_errors"]))

    def test_07_f12_b2_refuses_existing_decisive_output_or_protected_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            existing_ev = td_p / "rehearsal-evidence" / "WP-0012-dup"
            existing_ev.mkdir(parents=True)
            with self.assertRaisesRegex(drv.RehearsalGuardError, "already exists"):
                drv.guard_decisive_output_destinations(existing_ev)

            brand_new_ev = td_p / "rehearsal-evidence" / "WP-0012-fresh"
            existing_out = td_p / "already.json"
            existing_out.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(drv.RehearsalGuardError, "existing --output"):
                drv.guard_decisive_output_destinations(brand_new_ev, existing_out)

            for protected_rel in (
                "docs/implementation/WP-0012/eld-f4-implementer/evidence/overwrite.json",
                "docs/implementation/WP-0012/eld-f4-implementer/inventory.json",
                "docs/implementation/WP-0012/eld-f4-implementer/correction-006/evidence/overwrite.json",
                "docs/reviews/WP-0012/eld-f4-reviewer/leak.json",
                "docs/agent-reports/eld-f4-implementer/WP-0012/leak.json",
                "src/ELedgerCare.Api/leak.json",
            ):
                with self.assertRaisesRegex(drv.RehearsalGuardError, "protected|existing"):
                    drv.guard_decisive_output_destinations(brand_new_ev, REPO_ROOT / protected_rel)

    # --- 3. F12-B3 Key Compatibility & /007 vs /002 Gate ---
    def test_08_f12_b3_old_rejects_and_new_accepts_all_documented_review_keys_for_accepting_007(self) -> None:
        with self.assertRaises(OLD_001_DRV.RehearsalGuardError):
            OLD_001_DRV._extract_independent_review_002_sha(
                {"independent_preparation_review_002_sha": "9" * 40}
            )

        for alias_key in (
            "accepted_preparation_review",
            "accepted_preparation_review_sha",
            "accepted_review_007",
            "independent_preparation_review_007_sha",
            "independent_review_007",
            "accepted_007",
            "independent_preparation_review_sha",
            "accepted_review",
            "independent_preparation_review_002_sha",
            "accepted_review_002",
            "independent_review_002",
            "accepted_002",
            "preparation_review",
        ):
            doc = copy.deepcopy(self.valid_rel)
            doc.pop("accepted_preparation_review")
            doc[alias_key] = "9" * 40
            res = self._validate(doc)
            self.assertEqual(res["accepting_preparation_review"], {alias_key: "9" * 40})

            doc_dict = copy.deepcopy(self.valid_rel)
            doc_dict.pop("accepted_preparation_review")
            doc_dict[alias_key] = {"commit": "9" * 40, "disposition": "accepted"}
            res_dict = self._validate(doc_dict)
            self.assertEqual(res_dict["accepting_preparation_review"], {f"{alias_key}.commit": "9" * 40})

    def test_09_rejects_changes_requested_002_and_all_pre_006_or_self_commits_as_accepting_review(self) -> None:
        for rejected_rev in (
            drv.PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA,
            "0cabb137e71454d13342148a5652a5034df018ba",
            "8eec97ce301059f81ffacb04fc0144b3c33a248e",
            "7f3f8626489e898a50d275e93ee904660e97fd59",
            drv.PRIOR_AUTHOR_001_PUBLICATION_SHA,
            drv.PRIOR_AUTHOR_001_DELIVERABLE_SHA,
            drv.PREPARATION_DISPATCH_AUTHORITY_SHA,
            drv.CORRECTION_006_DISPATCH_AUTHORITY_SHA,
            drv.ACCEPTED_PACKET_BASE_SHA,
            drv.ACCEPTED_F4_FINAL_SOURCE_SHA,
            self.actual_head,
        ):
            doc = copy.deepcopy(self.valid_rel)
            doc["accepted_preparation_review"] = rejected_rev
            with self.assertRaises(drv.RehearsalGuardError):
                self._validate(doc)

        doc_cr = copy.deepcopy(self.valid_rel)
        doc_cr["accepted_preparation_review"] = {"commit": "9" * 40, "disposition": "changes-requested"}
        with self.assertRaisesRegex(drv.RehearsalGuardError, "non-accepting disposition"):
            self._validate(doc_cr)

    # --- 4. F12-D4 Actual API workerEnabled === false Assertion in Edge Driver ---
    def test_10_f12_d4_edge_driver_rejects_worker_enabled_true_on_reopen_and_accepts_false(self) -> None:
        wo_sha = "a" * 64
        mp_sha = "b" * 64
        state = {"worker_enabled": True}

        class MockExtHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                sha = wo_sha if "0001" in self.path else mp_sha
                payload = json.dumps(
                    {
                        "workerEnabled": state["worker_enabled"],
                        "status": "completed",
                        "attempts": [{"attemptNumber": 1}],
                        "result": {"rawSha256": sha},
                    }
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, fmt, *args):  # silence test HTTP logs
                return

        with socketserver.TCPServer(("127.0.0.1", 0), MockExtHandler) as srv:
            port = srv.server_address[1]
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            try:
                with tempfile.TemporaryDirectory() as td:
                    out_fail = Path(td) / "d4-fail.json"
                    cp_fail = subprocess.run(
                        [
                            "node",
                            str(HELPERS_DIR / "drive_rehearsal_edge.mjs"),
                            "--mode",
                            "verify-worker-enabled-guard",
                            "--apiPort",
                            str(port),
                            "--woRawSha256",
                            wo_sha,
                            "--mpRawSha256",
                            mp_sha,
                            "--expectWorkerEnabled",
                            "false",
                            "--output",
                            str(out_fail),
                        ],
                        cwd=str(REPO_ROOT),
                        capture_output=True,
                        text=True,
                    )
                    self.assertNotEqual(cp_fail.returncode, 0)
                    self.assertIn("F12-D4 workerEnabled mismatch", cp_fail.stderr)

                    state["worker_enabled"] = False
                    out_pass = Path(td) / "d4-pass.json"
                    cp_pass = subprocess.run(
                        [
                            "node",
                            str(HELPERS_DIR / "drive_rehearsal_edge.mjs"),
                            "--mode",
                            "verify-worker-enabled-guard",
                            "--apiPort",
                            str(port),
                            "--woRawSha256",
                            wo_sha,
                            "--mpRawSha256",
                            mp_sha,
                            "--expectWorkerEnabled",
                            "false",
                            "--output",
                            str(out_pass),
                        ],
                        cwd=str(REPO_ROOT),
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(cp_pass.returncode, 0, msg=cp_pass.stderr)
                    doc_pass = json.loads(out_pass.read_text(encoding="utf-8"))
                    self.assertIs(doc_pass["workerEnabledWo"], False)
                    self.assertIs(doc_pass["workerEnabledMp"], False)
            finally:
                srv.shutdown()

    # --- 5. Full Release Contract, Observation, Storage, Symlink, & AST Guards ---
    def test_11_synthetic_sample_file_passes_cpu_mode_and_is_rejected_by_live_mode(self) -> None:
        sample_path = CORRECTION_DIR / "sample-synthetic-release.json"
        res = drv.validate_synthetic_sample_file(sample_path)
        self.assertTrue(res["synthetic_sample_validated_on_cpu"])
        self.assertTrue(res["live_mode_rejected_synthetic_sample"])

        with self.assertRaisesRegex(drv.RehearsalGuardError, "synthetic_test_only"):
            self._validate(self.valid_rel, allow_synthetic=False)

    def test_12_dual_crlf_lf_and_wp0012_or_wp0012_0013_observation_layouts_pass(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        crlf_model = b'{"ok": true}\r\n'
        self.blobs["docs/coordination/WP-0012/obs/processes-before.json"] = b'{"apps": []}\n'
        self.blobs["docs/coordination/WP-0012/obs/model-before.json"] = crlf_model
        doc["observation_files"] = {
            "processes-before.json": {
                "path": "docs/coordination/WP-0012/obs/processes-before.json",
                "sha256": drv.sha256_bytes(b'{"apps": []}\n'),
            },
            "model-before.json": {
                "path": "docs/coordination/WP-0012/obs/model-before.json",
                "sha256": drv.sha256_bytes(b'{"ok": true}\n'),
            },
        }
        out = self._validate(doc)
        self.assertEqual(len(out["verified_observation_files"]), 2)

    def test_13_rejects_missing_ownership_or_model_observation_or_bad_hash(self) -> None:
        doc_no_model = copy.deepcopy(self.valid_rel)
        doc_no_model["observation_files"].pop("model-before.json")
        with self.assertRaisesRegex(drv.RehearsalGuardError, "model snapshot"):
            self._validate(doc_no_model)

        doc_bad_sha = copy.deepcopy(self.valid_rel)
        doc_bad_sha["observation_files"]["model-before.json"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(drv.RehearsalGuardError, "SHA-256 mismatch"):
            self._validate(doc_bad_sha)

    def test_14_cli_rejects_missing_release_args_and_rejected_authority_commits(self) -> None:
        cp1 = subprocess.run(
            [sys.executable, "-B", str(HELPERS_DIR / "run_wp0012_rehearsal.py"), "--execute-live"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(cp1.returncode, 2)

        for bad_sha in (
            drv.PREPARATION_DISPATCH_AUTHORITY_SHA,
            drv.CORRECTION_006_DISPATCH_AUTHORITY_SHA,
            drv.PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA,
            drv.PRIOR_AUTHOR_001_PUBLICATION_SHA,
        ):
            cp2 = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(HELPERS_DIR / "run_wp0012_rehearsal.py"),
                    "--validate-release",
                    "--release-commit",
                    bad_sha,
                    "--release-path",
                    "docs/coordination/WP-0012/releases/author.json",
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(cp2.returncode, 1)

    def test_15_rejects_historical_lease_prefixes_and_synthetic_lease_in_live_mode(self) -> None:
        for bad_lease in ("WP-0006-author-1", "WP-0010-author-1", "WP-0013-author-1", "random-lease"):
            doc = copy.deepcopy(self.valid_rel)
            doc["lease_id"] = bad_lease
            with self.assertRaises(drv.RehearsalGuardError):
                self._validate(doc)

        doc_live = copy.deepcopy(self.valid_rel)
        doc_live["synthetic_test_only"] = False
        with self.assertRaisesRegex(drv.RehearsalGuardError, "lease_id|synthetic|Authority"):
            self._validate(doc_live, release_commit="a" * 40, allow_synthetic=False)

    def test_16_rejects_max_model_attempts_other_than_2(self) -> None:
        for bad_attempts in (0, 1, 3, 4, None):
            doc = copy.deepcopy(self.valid_rel)
            doc["max_model_attempts"] = bad_attempts
            with self.assertRaisesRegex(drv.RehearsalGuardError, "max_model_attempts"):
                self._validate(doc)

    def test_17_rejects_lease_exceeding_6h_expired_future_or_under_300s(self) -> None:
        for d_rel, d_exp in (
            (timedelta(minutes=-5), timedelta(hours=6, seconds=1)),
            (timedelta(hours=-2), timedelta(seconds=-1)),
            (timedelta(minutes=-10), timedelta(seconds=180)),
            (timedelta(minutes=5), timedelta(hours=2)),
        ):
            doc = copy.deepcopy(self.valid_rel)
            doc["released_utc"] = (self.now_utc + d_rel).isoformat()
            doc["expires_utc"] = (self.now_utc + d_exp).isoformat()
            with self.assertRaises(drv.RehearsalGuardError):
                self._validate(doc)

    def test_18_rejects_wrong_owner_conversation_model_ports_database_or_roots(self) -> None:
        for mut in (
            {"owner": "eld-f4-reviewer"},
            {"conversation_id": "61105d43-7706-45f2-9176-69d3256248e0"},
            {"model": "gpt-6-astra"},
            {"ports": {"api": 5690, "ui": 4710, "postgres": 55439}},
            {"database": "eledgercare_f4_author_seed_f3"},
            {"database": "eledgercare_f4_author_migrated"},
            {"database": "eledgercare_demo_wp0012_reviewer"},
            {"readonly_q0_root": r"C:\Temp\fake-q0"},
            {"runtime_root": r"C:\Users\jackg\eLedgerCare-Demo\WP-0012\reviewer"},
        ):
            doc = copy.deepcopy(self.valid_rel)
            doc.update(mut)
            with self.assertRaises(drv.RehearsalGuardError):
                self._validate(doc)

    def test_19_rejects_dirty_worktree_when_require_clean_worktree_true(self) -> None:
        orig_git_stdout = drv.git_stdout

        def dirty_git_stdout(root: Path, args: list[str]) -> str:
            if args[:2] == ["status", "--porcelain"]:
                return " M docs/implementation/WP-0012/eld-f4-implementer/correction-006/RUNBOOK.md"
            return orig_git_stdout(root, args)

        with mock.patch.object(drv, "git_stdout", side_effect=dirty_git_stdout):
            with self.assertRaisesRegex(drv.RehearsalGuardError, "must be clean"):
                self._validate(self.valid_rel, require_clean_worktree=True)

    def test_20_rejects_mutated_product_tree_or_fixture_digest(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["product_tree_objects"]["web"] = "0" * 40
        with self.assertRaisesRegex(drv.RehearsalGuardError, "product_tree_objects"):
            self._validate(doc)

        doc2 = copy.deepcopy(self.valid_rel)
        doc2["pinned_digests"]["syn_wo_01_sha256"] = "f" * 64
        with self.assertRaisesRegex(drv.RehearsalGuardError, "syn_wo_01_sha256"):
            self._validate(doc2)

    def test_21_rejects_wrong_contract_storage_cap_free_floor_or_timeout_guards(self) -> None:
        for mut in (
            {"storage_cap_bytes": 8_589_934_592},
            {"free_floor_bytes": 1_073_741_824},
            {"guards": {"three_page_timeout_s": 7200}},
            {"allow_test_content": True},
            {"torchvision_local_sha256_TOFU_accepted": False},
        ):
            doc = copy.deepcopy(self.valid_rel)
            doc.update(mut)
            with self.assertRaises(drv.RehearsalGuardError):
                self._validate(doc)

    def test_22_live_filesystem_checks_reject_over_4gib_demo_usage_or_under_20gib_free_space(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_demo = Path(td) / "demo"
            fake_demo.mkdir()
            f = fake_demo / "big.bin"
            f.write_bytes(b"x")
            with (
                mock.patch.object(drv, "EXPECTED_DEMO_RUNTIME_ROOT", fake_demo),
                mock.patch.dict(drv.GUARD_CEILINGS, {"storage_cap_bytes": 0}),
            ):
                with self.assertRaisesRegex(drv.RehearsalGuardError, "exceeds 4 GiB cap"):
                    drv.inspect_readonly_q0_and_demo_roots_cpu(verify_model_sha256=False)

        fake_usage = shutil._ntuple_diskusage(total=100, used=90, free=10)
        with mock.patch.object(drv.shutil, "disk_usage", return_value=fake_usage):
            with self.assertRaisesRegex(drv.RehearsalGuardError, "20 GiB safety floor"):
                drv.inspect_readonly_q0_and_demo_roots_cpu(verify_model_sha256=False)

    def test_23_rejects_reparse_point_on_roots_or_output_destinations(self) -> None:
        with mock.patch.object(drv, "is_reparse_point", side_effect=lambda p: p == drv.EXPECTED_Q0_ROOT):
            with self.assertRaisesRegex(drv.RehearsalGuardError, "reparse point"):
                drv.inspect_readonly_q0_and_demo_roots_cpu(verify_model_sha256=False)

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ev"
            with mock.patch.object(drv, "is_reparse_point", return_value=True):
                with self.assertRaisesRegex(drv.RehearsalGuardError, "Reparse point"):
                    drv.guard_decisive_output_destinations(p)

    def test_24_rejects_commit_containing_non_accepting_007_report(self) -> None:
        fake_007_sha = "5" * 40
        orig_exists = drv.git_object_exists
        orig_stdout = drv.git_stdout
        orig_bytes = drv.git_bytes

        def fake_exists(root: Path, spec: str) -> bool:
            if spec == f"{fake_007_sha}^{{commit}}":
                return True
            return orig_exists(root, spec)

        def fake_stdout(root: Path, args: list[str]) -> str:
            if args[:4] == ["ls-tree", "-r", "--name-only", fake_007_sha]:
                return "docs/agent-reports/eld-f4-reviewer/WP-0012/007_2026-11-17_review_eld-f4-reviewer.md"
            return orig_stdout(root, args)

        def fake_bytes(root: Path, args: list[str]) -> bytes:
            if len(args) >= 3 and args[2].startswith(f"{fake_007_sha}:"):
                return b"# WP-0012 / 007\n\n- Status: changes-requested\n"
            return orig_bytes(root, args)

        doc = copy.deepcopy(self.valid_rel)
        doc["accepted_preparation_review"] = fake_007_sha
        with (
            mock.patch.object(drv, "git_object_exists", side_effect=fake_exists),
            mock.patch.object(drv, "git_is_ancestor", side_effect=lambda r, a, d: False if a == fake_007_sha else drv.git_stdout(r, ["rev-parse", "HEAD"]) != ""),
            mock.patch.object(drv, "git_stdout", side_effect=fake_stdout),
            mock.patch.object(drv, "git_bytes", side_effect=fake_bytes),
        ):
            with self.assertRaisesRegex(drv.RehearsalGuardError, "Status: 'changes-requested'"):
                self._validate(doc)

    def test_25_win32_process_identity_probe_matches_current_python_pid(self) -> None:
        ident = drv.get_win32_process_identity(os.getpid())
        self.assertIsNotNone(ident)
        assert ident is not None
        self.assertTrue(ident["alive"])
        self.assertGreater(ident["create_filetime"], 0)
        self.assertTrue(drv.is_exact_process_alive(os.getpid(), ident["create_filetime"]))
        self.assertFalse(drv.is_exact_process_alive(os.getpid(), ident["create_filetime"] + 1))

    def test_26_ast_contains_zero_forbidden_ml_or_research_imports(self) -> None:
        for py_file in sorted(HELPERS_DIR.glob("*.py")):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for bad in FORBIDDEN_IMPORT_PREFIXES:
                            self.assertFalse(
                                alias.name == bad or alias.name.startswith(bad + "."),
                                msg=f"Forbidden import {alias.name} in {py_file.name}",
                            )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    for bad in FORBIDDEN_IMPORT_PREFIXES:
                        self.assertFalse(
                            node.module == bad or node.module.startswith(bad + "."),
                            msg=f"Forbidden from-import {node.module} in {py_file.name}",
                        )


    def test_27_cleanup_exceptions_preserve_primary_failure_and_honest_return(self) -> None:
        # Exercise actual orchestrator finally under independent failure at each cleanup boundary.
        for fault in ("stop_proc", "run_psql_query", "_collect_lingering_attempt_processes", "count_ocr_worker_processes", "postgres_stop", "scrub_directory_secrets"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as td, ExitStack() as stack:
                demo = Path(td) / "demo"
                (demo / "runs").mkdir(parents=True)
                original_read = Path.read_text
                def read(path, *args, **kwargs):
                    if path.name == "pg-local.json":
                        return json.dumps({"host":"127.0.0.1", "port":55438, "appUser":"fake", "appPassword":"fake-password"})
                    if path.name == "postmaster.pid":
                        return "54321\n"
                    return original_read(path, *args, **kwargs)
                stack.enter_context(mock.patch.object(Path, "read_text", read))
                stack.enter_context(mock.patch.object(drv, "EXPECTED_DEMO_RUNTIME_ROOT", demo))
                stack.enter_context(mock.patch.object(drv, "git_object_exists", return_value=True))
                stack.enter_context(mock.patch.object(drv, "git_bytes", return_value=b"{}"))
                stack.enter_context(mock.patch.object(drv, "validate_release_contract", return_value={"lease_id":"WP-0012-cleanup-fault"}))
                roots = stack.enter_context(mock.patch.object(drv, "inspect_readonly_q0_and_demo_roots_cpu", return_value={"writable_demo_root_exists":True}))
                ports = stack.enter_context(mock.patch.object(drv, "assert_ports_unbound", return_value={"5590":[], "4610":[], "55438":[]}))
                stack.enter_context(mock.patch.object(drv, "get_win32_process_identity", return_value={"pid":54321, "create_filetime":1, "alive":True}))
                stack.enter_context(mock.patch.object(drv, "is_exact_process_alive", return_value=False))
                stack.enter_context(mock.patch.object(drv, "start_api_and_ui", return_value=(mock.Mock(pid=11), {"fh":None,"identity":{"pid":11,"create_filetime":1}}, mock.Mock(pid=12), {"fh":None,"identity":{"pid":12,"create_filetime":1}})))
                sampler = stack.enter_context(mock.patch.object(drv, "ProcessMemorySampler"))
                sampler.return_value.stop.return_value = {}
                stop = stack.enter_context(mock.patch.object(drv, "stop_proc", side_effect=OSError("injected-stop") if fault=="stop_proc" else None))
                workers = stack.enter_context(mock.patch.object(drv, "count_ocr_worker_processes", side_effect=[0,OSError("injected-count")] if fault=="count_ocr_worker_processes" else [0,0]))
                audit = stack.enter_context(mock.patch.object(drv, "_collect_lingering_attempt_processes", side_effect=OSError("injected-audit") if fault=="_collect_lingering_attempt_processes" else None, return_value=[]))
                scrub = stack.enter_context(mock.patch.object(drv, "scrub_directory_secrets", side_effect=OSError("injected-scrub") if fault=="scrub_directory_secrets" else None, return_value=0))
                def query(settings, db, sql, **kw):
                    if "count(*)" in sql:
                        return "0"
                    if fault=="run_psql_query":
                        raise OSError("injected-query")
                    return "[]"
                stack.enter_context(mock.patch.object(drv, "run_psql_query", side_effect=query))
                calls=[]
                def run(argv, **kw):
                    calls.append(argv)
                    if any("stop-cluster.ps1" in str(x) for x in argv) and fault=="postgres_stop":
                        raise OSError("injected-pg-stop")
                    edge = any("drive_rehearsal_edge.mjs" in str(x) for x in argv)
                    return subprocess.CompletedProcess(argv, 1 if edge else 0, stdout="", stderr="PRIMARY")
                stack.enter_context(mock.patch.object(drv.subprocess, "run", side_effect=run))
                with self.assertRaisesRegex(RuntimeError, "Live Phase A stopped/failed"):
                    drv.execute_live_rehearsal(release_commit="d"*40, release_path="docs/coordination/WP-0012/fake.json")
                receipt=json.loads((demo/"rehearsal-evidence/WP-0012-cleanup-fault/owner-lease-return.json").read_text())
                self.assertFalse(receipt["clean_return_verified"])
                self.assertEqual(receipt["status"],"failed_stopped")
                self.assertTrue(receipt["cleanup_errors"])
                self.assertEqual(stop.call_count,2)
                self.assertEqual(audit.call_count,1)
                self.assertEqual(workers.call_count,2)
                self.assertEqual(scrub.call_count,1)
                self.assertEqual(roots.call_count,2)
                self.assertEqual(ports.call_count,2)
                self.assertTrue(any("stop-cluster.ps1" in str(x) for call in calls for x in call))
                if fault=="run_psql_query":
                    self.assertIsNone(receipt["model_attempts_executed"])
                if fault=="scrub_directory_secrets":
                    self.assertFalse(receipt["logs_scrubbed"])

    def test_28_stop_proc_taskkill_error_still_reaps_exact_cpu_child(self) -> None:
        child=subprocess.Popen([sys.executable,"-B","-c","import time; time.sleep(30)"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        identity=drv.get_win32_process_identity(child.pid)
        fh=io.StringIO()
        try:
            with mock.patch.object(drv.subprocess,"run",side_effect=OSError("taskkill unavailable")):
                drv.stop_proc(child,fh,expected_identity=identity)
            self.assertIsNotNone(child.poll())
            self.assertTrue(fh.closed)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)

    def test_29_live_review_gate_rejects_no_report_and_accepts_007_status(self) -> None:
        doc=copy.deepcopy(self.valid_rel)
        doc["synthetic_test_only"]=False
        doc["accepted_preparation_review"]="9"*40
        doc["lease_id"]="WP-0012-author-003-test-contract-only"
        with mock.patch.object(drv,"_commit_inspects_as_accepting_007",return_value=(False,None)):
            with self.assertRaisesRegex(drv.RehearsalGuardError,"no accepted independent"):
                self._validate(doc,release_commit="d"*40,allow_synthetic=False)
        with mock.patch.object(drv,"_commit_inspects_as_accepting_007",return_value=(True,None)):
            self._validate(doc,release_commit="d"*40,allow_synthetic=False)

    def test_31_refuses_lease_path_escape_and_q0_output(self) -> None:
        doc=copy.deepcopy(self.valid_rel)
        doc["lease_id"]="WP-0012/../../escape"
        with self.assertRaises(drv.RehearsalGuardError):
            self._validate(doc)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(drv.RehearsalGuardError):
                drv.guard_decisive_output_destinations(Path(td)/"new", drv.EXPECTED_Q0_ROOT/"never-write-correction006.json")

    def test_30_short_password_scrub_preserves_status_and_always_scrubs_connection_password(self) -> None:
        secrets=drv.load_local_secrets({"appPassword":"p"})
        text='{"status":"failed_stopped", "password":"p", "connection":"Password=p;"}'
        result=drv.scrub_text(text,secrets)
        self.assertEqual(json.loads(result)["status"],"failed_stopped")
        self.assertNotIn('"p"',result)
        self.assertIn("Password=[REDACTED];",result)
        self.assertEqual(drv.scrub_text("Password=short;",[]),"Password=[REDACTED];")


def run_logged_step(
    step_name: str,
    cmd: list[str],
    cwd: Path,
    secrets: list[str],
    *,
    extra_env: dict[str, str] | None = None,
) -> dict:
    started_utc = drv.utc_now()
    t0 = time.monotonic()
    env = {**os.environ, **(extra_env or {})}
    cp = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    elapsed_ms = round((time.monotonic() - t0) * 1000.0, 1)
    combined = f"$ {' '.join(cmd)}\n[exit_code={cp.returncode} elapsed_ms={elapsed_ms}]\n\n" + cp.stdout
    if cp.stderr:
        combined += "\n--- STDERR ---\n" + cp.stderr
    scrubbed = drv.scrub_text(combined, secrets)
    log_path = LOGS_DIR / f"{step_name}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(scrubbed.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    if cp.returncode != 0:
        raise RuntimeError(f"Step {step_name} failed with exit code {cp.returncode}; see {log_path}")
    return {
        "step": step_name,
        "command": [drv.scrub_text(c, secrets) for c in cmd],
        "cwd": str(cwd.relative_to(REPO_ROOT)) if cwd != REPO_ROOT else ".",
        "started_utc": started_utc,
        "elapsed_ms": elapsed_ms,
        "exit_code": cp.returncode,
        "log_relpath": log_path.relative_to(REPO_ROOT).as_posix(),
        "log_sha256": drv.sha256_file(log_path),
    }


def run_static_and_ast_audit(*, require_clean: bool) -> dict:
    porcelain = drv.git_stdout(REPO_ROOT, ["status", "--porcelain", "--untracked-files=all"])
    if require_clean and porcelain != "":
        raise RuntimeError(f"Worktree must be clean before decisive /006 CPU validation:\n{porcelain}")

    head_sha = drv.git_stdout(REPO_ROOT, ["rev-parse", "HEAD"])
    branch = drv.git_stdout(REPO_ROOT, ["rev-parse", "--abbrev-ref", "HEAD"])
    if branch != drv.EXPECTED_BRANCH:
        raise RuntimeError(f"Expected branch {drv.EXPECTED_BRANCH}, got {branch}")
    if not drv.git_is_ancestor(REPO_ROOT, drv.CORRECTION_006_BASE_SHA, head_sha):
        raise RuntimeError(f"Expected {drv.CORRECTION_006_BASE_SHA} to be an ancestor of {head_sha}")

    preserved_count = len(
        [
            ln
            for ln in drv.git_stdout(REPO_ROOT, ["ls-tree", "-r", "--name-only", drv.CORRECTION_006_BASE_SHA]).splitlines()
            if ln.strip()
        ]
    )
    if preserved_count != EXPECTED_PRESERVED_006_BASE_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_PRESERVED_006_BASE_COUNT} preserved paths at /006 base, got {preserved_count}")

    mutated_prior = [
        ln.strip()
        for ln in drv.git_stdout(
            REPO_ROOT,
            ["diff", "--diff-filter=MD", "--name-only", drv.CORRECTION_006_BASE_SHA, head_sha],
        ).splitlines()
        if ln.strip()
    ]
    if mutated_prior:
        raise RuntimeError(f"Immutable /001, /002, or base files modified/deleted: {mutated_prior}")

    changed_since_006_base = [
        ln.strip()
        for ln in drv.git_stdout(REPO_ROOT, ["diff", "--name-only", drv.CORRECTION_006_BASE_SHA, head_sha]).splitlines()
        if ln.strip()
    ]
    outside_006 = [
        p
        for p in changed_since_006_base
        if not p.startswith("docs/implementation/WP-0012/eld-f4-implementer/correction-006/")
    ]
    if outside_006:
        raise RuntimeError(f"Changed files outside correction-006 namespace: {outside_006}")

    compiled_py: list[str] = []
    with tempfile.TemporaryDirectory() as pyc_td:
        for py_file in sorted(HELPERS_DIR.glob("*.py")):
            py_compile.compile(str(py_file), cfile=str(Path(pyc_td) / (py_file.name + "c")), doraise=True)
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for bad in FORBIDDEN_IMPORT_PREFIXES:
                            if alias.name == bad or alias.name.startswith(bad + "."):
                                raise RuntimeError(f"Forbidden import '{alias.name}' in {py_file}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    for bad in FORBIDDEN_IMPORT_PREFIXES:
                        if node.module == bad or node.module.startswith(bad + "."):
                            raise RuntimeError(f"Forbidden from-import '{node.module}' in {py_file}")
            compiled_py.append(py_file.relative_to(REPO_ROOT).as_posix())

    return {
        "clean_worktree": porcelain == "",
        "branch": branch,
        "frozen_006_head_sha": head_sha,
        "correction_006_base_sha": drv.CORRECTION_006_BASE_SHA,
        "prior_author_001_publication_sha": drv.PRIOR_AUTHOR_001_PUBLICATION_SHA,
        "prior_changes_requested_review_002_sha": drv.PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA,
        "dispatch_authority_006_inspected_readonly_sha": drv.CORRECTION_006_DISPATCH_AUTHORITY_SHA,
        "preserved_006_base_paths_verified_unchanged": preserved_count,
        "changed_paths_since_006_base": changed_since_006_base,
        "compiled_python_helpers": compiled_py,
        "forbidden_ml_or_research_imports": 0,
    }


def main() -> None:
    global EVIDENCE_DIR, LOGS_DIR
    parser = argparse.ArgumentParser(description="CPU-only frozen correction006 verification.")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--evidence-name", default="evidence", help="New directory name inside correction-006; never overwritten.")
    args = parser.parse_args()
    if not args.evidence_name or Path(args.evidence_name).name != args.evidence_name:
        raise RuntimeError("evidence-name must be one directory name")
    EVIDENCE_DIR = CORRECTION_DIR / args.evidence_name
    LOGS_DIR = EVIDENCE_DIR / "logs"
    started_utc = drv.utc_now()
    static_audit = run_static_and_ast_audit(require_clean=args.require_clean)
    if EVIDENCE_DIR.exists():
        raise RuntimeError(f"Refusing existing evidence directory: {EVIDENCE_DIR}")
    # Observation only: no product service or model is started by this verifier.
    final_ports = drv.assert_ports_unbound((5590, 4610, 55438))
    demo_entries_before = sorted(p.name for p in drv.EXPECTED_DEMO_RUNTIME_ROOT.iterdir())
    LOGS_DIR.mkdir(parents=True, exist_ok=False)
    secrets = drv.load_local_secrets()
    steps = []
    steps.append(run_logged_step("01-node-check-edge-driver", ["node", "--check", str(HELPERS_DIR / "drive_rehearsal_edge.mjs")], REPO_ROOT, secrets))
    steps.append(run_logged_step("02-validate-synthetic-sample-cli", [sys.executable, "-B", str(HELPERS_DIR / "run_wp0012_rehearsal.py"), "--validate-synthetic-sample", str(CORRECTION_DIR / "sample-synthetic-release.json"), "--output", str(EVIDENCE_DIR / "synthetic-sample-validation.json")], REPO_ROOT, secrets))
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Wp0012Correction006GuardTests)
    stream = io.StringIO()
    t0 = time.monotonic()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    log = LOGS_DIR / "03-old-fails-new-passes-and-guard-tests.log"
    log.write_text(drv.scrub_text(stream.getvalue(), secrets), encoding="utf-8", newline="\n")
    steps.append({"step": "03-old-fails-new-passes-and-guard-tests", "command": ["unittest", "Wp0012Correction006GuardTests"], "tests_run": result.testsRun, "elapsed_ms": round((time.monotonic()-t0)*1000, 1), "exit_code": 0 if result.wasSuccessful() else 1, "log_relpath": log.relative_to(REPO_ROOT).as_posix(), "log_sha256": drv.sha256_file(log)})
    final_ports = drv.assert_ports_unbound((5590, 4610, 55438))
    demo_entries_after = sorted(p.name for p in drv.EXPECTED_DEMO_RUNTIME_ROOT.iterdir())
    if demo_entries_before != demo_entries_after:
        raise RuntimeError("Runtime root entries changed during CPU verification")
    pg_status = subprocess.run([str(REPO_ROOT / ".local/tools/pgsql-18.7-1/bin/pg_ctl.exe"), "status", "-D", str(REPO_ROOT / ".local/postgres-data")], capture_output=True, text=True)
    if pg_status.returncode != 3:
        raise RuntimeError(f"Owned PostgreSQL expected stopped, status={pg_status.returncode}")
    summary = {"schema": "eledgercare.wp0012-correction-006-validation-summary/1", "packet": "WP-0012", "sequence": "006", "author": "eld-f4-implementer", "started_utc": started_utc, "completed_utc": drv.utc_now(), "passed": result.wasSuccessful(), "static_and_ast_audit": static_audit, "executed_steps": steps, "live_rehearsal_executed": False, "model_imported_or_invoked": False, "gpu_queries_or_inference_run": False, "product_services_or_databases_started": False, "database_preservation": "No database operations; prior001 evidence remains attributed, not rerun", "native_session": drv.EXPECTED_CONVERSATION_ID, "native_model_marker": drv.EXPECTED_MODEL, "effort_disclosure": drv.EXPECTED_EFFORT}
    drv.write_json_lf(EVIDENCE_DIR / "validation-summary.json", summary)
    returned = {"verified_utc": drv.utc_now(), "ports": final_ports, "postgres_status_exit": pg_status.returncode, "product_services_started": False, "database_operations": False, "gpu_queries": False, "model_calls": 0, "owned_cpu_children_reaped": result.wasSuccessful(), "writable_demo_root_entries_before": demo_entries_before, "writable_demo_root_entries_after": demo_entries_after, "writable_demo_root_mutated": False, "q0_accessed": "Read-only source/manifest guards; no model import or renderer", "tests_passed": result.wasSuccessful()}
    drv.write_json_lf(EVIDENCE_DIR / "resource-return.json", returned)
    if not result.wasSuccessful():
        raise RuntimeError(f"CPU verification failed; preserved evidence in {EVIDENCE_DIR}")
    print(f"PASS {result.testsRun} affected CPU tests; product ports free and PostgreSQL stopped; no live service/model calls.")


if __name__ == "__main__":
    main()
