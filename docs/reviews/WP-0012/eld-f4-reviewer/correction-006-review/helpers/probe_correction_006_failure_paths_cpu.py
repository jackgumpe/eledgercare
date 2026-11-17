"""Focused independent CPU failure-path & guard probe suite for WP-0012 / 007 (`eld-f4-reviewer`).

Modes:
  1. `--mode preflight-self-and-old-001` (Preliminary overlap checkpoint — CPU-only):
     - Runs baseline `old-fails` probes (`P06-01`..`P06-06`) against immutable merged `/001` author helpers
       (`docs/implementation/WP-0012/eld-f4-implementer/helpers`, `ad5202a029a7a86bea5fa3e3d97760d0a9cc673a`).
     - Executes `16` CPU unit & subprocess tests against reconciled reviewer helper
       `run_wp0012_reviewer_rehearsal_v4.py` (`RG-04` `/007` sequence + `/002` `changes-requested` exclusion +
       unreturned author lease rejection; `RG-05` explicit `lease_returned: False` / `returned_utc: None` /
       `cleanup_failed_lease_unreturned` on failed cleanup + `correction-006-review/**` output protection).
     - Records a strictly read-only byte/SHA-256 snapshot of provisional working files in
       `eld-f4-implementer`'s `correction-006/` directory (`decisive=False`, `executed=False`) for later
       byte-reconciliation when frozen `/006` is bound by `eld-coordinator`.
  2. `--mode verify-bound-006` (Held for exact frozen `/006` dispatch):
     - Executes `P06-01`..`P06-06` (`old-fails` vs `new-passes` + failed-cleanup unreturned checks + loopback
       HTTP `workerEnabled` contract checks on OS-ephemeral port `0`) against the merged committed
       `correction-006` directory and writes into `correction-006-review/final/` without touching `preliminary/`.
"""

from __future__ import annotations

import argparse
import ast
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import http.server
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[6]
HELPERS_DIR = SCRIPT_PATH.parent

AUTHOR_001_HELPERS_DIR = REPO_ROOT / "docs" / "implementation" / "WP-0012" / "eld-f4-implementer" / "helpers"
PROVISIONAL_EXT_006_DIR = Path(
    r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f4-implementer\docs\implementation\WP-0012\eld-f4-implementer\correction-006"
)

INITIAL_PREP_PUB_SHA = "7f3f8626489e898a50d275e93ee904660e97fd59"
REVIEW_002_PUB_SHA = "379d8c5d607fd248d7f272e412b4ed4a97bc64f6"
REVIEW_002_SOURCE_SHA = "0cabb137e71454d13342148a5652a5034df018ba"
REVIEW_002_EVIDENCE_SHA = "8eec97ce301059f81ffacb04fc0144b3c33a248e"
AUTHOR_001_PUB_SHA = "165b2421b297bf49181c91af8d05a449ad69e9b5"

sys.path.insert(0, str(HELPERS_DIR))
import run_wp0012_reviewer_rehearsal_v4 as rv4  # noqa: E402


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_module_from_path(mod_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(mod_name, str(file_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module {mod_name} from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def snapshot_provisional_author_006_readonly(ext_dir: Path) -> dict:
    """Strictly read-only byte & SHA-256 inspection of provisional working files (zero execution, non-decisive)."""
    if not ext_dir.is_dir():
        return {"observed": False, "reason": "directory_not_present"}
    files = []
    for fp in sorted(p for p in ext_dir.rglob("*") if p.is_file()):
        raw = fp.read_bytes()
        lf = raw.replace(b"\r\n", b"\n")
        files.append({
            "relative_path": fp.relative_to(ext_dir).as_posix(),
            "byte_length": len(raw),
            "sha256_raw": sha256_hex(raw),
            "sha256_lf": sha256_hex(lf),
        })
    return {
        "observed": True,
        "provisional_mutable_working_tree": True,
        "decisive_evaluation_claimed": False,
        "provisional_code_executed": False,
        "file_count": len(files),
        "files": files,
    }


def run_old_001_baseline_probes() -> dict:
    """Executes P06-01..P06-06 against immutable merged /001 helpers (ad5202a0) to confirm old-fails detection."""
    old_drv = load_module_from_path("author_001_drv_baseline", AUTHOR_001_HELPERS_DIR / "run_wp0012_rehearsal.py")
    old_edge_src = (AUTHOR_001_HELPERS_DIR / "drive_rehearsal_edge.mjs").read_text(encoding="utf-8")
    real_popen = subprocess.Popen

    # P06-01: Partial-startup leak across UI early exit (Case A), API bind timeout (Case B), & UI readiness timeout (Case C)
    procs_a: list[subprocess.Popen] = []
    fhs_a: list = []

    def popen_a(cmd, *a, **kw):
        if kw.get("stdout") is not None:
            fhs_a.append(kw["stdout"])
        is_api = bool(cmd and Path(str(cmd[0])).stem.lower() == "dotnet")
        p = real_popen([sys.executable, "-B", "-c", "import time; time.sleep(60)" if is_api else "import sys; sys.exit(1)"], *a, **kw)
        procs_a.append(p)
        return p

    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        try:
            with (
                mock.patch.object(old_drv, "assert_ports_unbound", return_value={"5590": [], "4610": []}),
                mock.patch.object(
                    old_drv,
                    "observe_ports",
                    side_effect=lambda ports=(5590,): {"5590": [{"owningPid": procs_a[0].pid}]} if procs_a else {"5590": []},
                ),
                mock.patch.object(old_drv.subprocess, "Popen", side_effect=popen_a),
            ):
                fh_open_a = False
                try:
                    old_drv.start_api_and_ui(app_conn_str="dummy", ocr_enabled=True, leased_gpu_uuid=old_drv.EXPECTED_GPU_UUID, log_dir=td_p, tag="p06a")
                except RuntimeError:
                    fh_open_a = bool(fhs_a and not fhs_a[0].closed)
            ident_a = old_drv.get_win32_process_identity(procs_a[0].pid)
            leaked_a = bool(ident_a and ident_a["alive"])
        finally:
            for p in procs_a:
                if p.poll() is None:
                    p.kill()
                    p.wait(timeout=10)
            for fh in fhs_a:
                if hasattr(fh, "close") and not fh.closed:
                    fh.close()

    procs_c: list[subprocess.Popen] = []
    fhs_c: list = []

    def popen_c(cmd, *a, **kw):
        if kw.get("stdout") is not None:
            fhs_c.append(kw["stdout"])
        p = real_popen([sys.executable, "-B", "-c", "import time; time.sleep(60)"], *a, **kw)
        procs_c.append(p)
        return p

    # monotonic ticks: api deadline=145 (100.1 < 145 -> binds immediately), ui deadline=190 (100.2 < 190 -> 1 loop, then 250 >= 190 -> timeout!)
    ticks_c = iter([100.0, 100.1, 100.2, 100.3, 250.0])
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        try:
            with (
                mock.patch.object(old_drv, "assert_ports_unbound", return_value={"5590": [], "4610": []}),
                mock.patch.object(
                    old_drv,
                    "observe_ports",
                    side_effect=lambda ports=(5590,): {"5590": [{"owningPid": procs_c[0].pid}]} if procs_c else {"5590": []},
                ),
                mock.patch.object(old_drv.subprocess, "Popen", side_effect=popen_c),
                mock.patch.object(old_drv.time, "monotonic", side_effect=lambda: next(ticks_c, 300.0)),
                mock.patch.object(old_drv.time, "sleep"),
            ):
                try:
                    old_drv.start_api_and_ui(app_conn_str="dummy", ocr_enabled=False, leased_gpu_uuid="", log_dir=td_p, tag="p06c")
                except RuntimeError:
                    pass
            leaked_c_api = bool((old_drv.get_win32_process_identity(procs_c[0].pid) or {}).get("alive"))
            leaked_c_ui = bool((old_drv.get_win32_process_identity(procs_c[1].pid) or {}).get("alive"))
        finally:
            for p in procs_c:
                if p.poll() is None:
                    p.kill()
                    p.wait(timeout=10)
            for fh in fhs_c:
                if hasattr(fh, "close") and not fh.closed:
                    fh.close()

    # P06-05: /001 rejects independent_preparation_review_002_sha AND accepts changes-requested /002 SHA 379d8c5d... if passed as accepted_review_002!
    b3_rejected = False
    try:
        old_drv._extract_independent_review_002_sha({"independent_preparation_review_002_sha": "a" * 40})
    except old_drv.RehearsalGuardError:
        b3_rejected = True

    extracted_002_sha = old_drv._extract_independent_review_002_sha({"accepted_review_002": REVIEW_002_PUB_SHA})
    old_accepts_changes_requested_002 = extracted_002_sha == REVIEW_002_PUB_SHA and REVIEW_002_PUB_SHA not in getattr(
        old_drv, "REJECTED_RELEASE_COMMITS", set()
    )

    out = {
        "P06-01_old_001_partial_startup_leaks_detected": leaked_a and fh_open_a and leaked_c_api and leaked_c_ui,
        "P06-01_detail": {
            "ui_early_exit_leaked_api_proc": leaked_a,
            "ui_early_exit_leaked_api_fh": fh_open_a,
            "ui_timeout_leaked_both_api_and_ui_procs": leaked_c_api and leaked_c_ui,
        },
        "P06-02_and_03_old_001_lacks_failure_lease_return_and_unreturned_cleanup_guard": (
            not hasattr(old_drv, "guard_decisive_output_destinations")
            and "clean_return_verified" not in Path(old_drv.__file__).read_text(encoding="utf-8")
        ),
        "P06-04_old_001_allows_existing_ev_out_dir_exist_ok_true": (
            "ev_out_dir.mkdir(parents=True, exist_ok=True)" in Path(old_drv.__file__).read_text(encoding="utf-8")
        ),
        "P06-05_old_001_key_mismatch_and_002_changes_requested_not_excluded": (
            b3_rejected and old_accepts_changes_requested_002
        ),
        "P06-06_old_001_edge_lacks_workerEnabled_api_assertion": (
            "ocrEnabledDuringReopen: false" in old_edge_src and "workerEnabled" not in old_edge_src
        ),
    }
    if not all(
        out[k]
        for k in (
            "P06-01_old_001_partial_startup_leaks_detected",
            "P06-02_and_03_old_001_lacks_failure_lease_return_and_unreturned_cleanup_guard",
            "P06-04_old_001_allows_existing_ev_out_dir_exist_ok_true",
            "P06-05_old_001_key_mismatch_and_002_changes_requested_not_excluded",
            "P06-06_old_001_edge_lacks_workerEnabled_api_assertion",
        )
    ):
        raise AssertionError(f"Unexpected old-001 baseline probe result: {out}")
    return out


def run_bound_006_candidate_probes(cand_dir: Path) -> dict:
    """Executes P06-01..P06-06 against a merged, frozen author correction-006 directory (held until /006 dispatch)."""
    drv_path = cand_dir / "helpers" / "run_wp0012_rehearsal.py"
    edge_path = cand_dir / "helpers" / "drive_rehearsal_edge.mjs"
    sample_path = cand_dir / "sample-synthetic-release.json"
    mod = load_module_from_path("author_006_drv_bound", drv_path)
    real_popen = subprocess.Popen

    # 1. P06-01: Partial-startup cleanup on UI early exit, API bind timeout, & UI readiness timeout
    leaked_any = False
    for mode_case in ("ui_exit", "api_timeout", "ui_timeout"):
        spawned: list[subprocess.Popen] = []
        fhs: list = []

        def fake_popen(cmd, *a, **kw):
            if kw.get("stdout") is not None:
                fhs.append(kw["stdout"])
            is_api = bool(cmd and Path(str(cmd[0])).stem.lower() == "dotnet")
            code = "import time; time.sleep(60)" if (is_api or mode_case != "ui_exit") else "import sys; sys.exit(1)"
            p = real_popen([sys.executable, "-B", "-c", code], *a, **kw)
            spawned.append(p)
            return p

        ticks = (
            iter([100.0, 100.1, 150.0])
            if mode_case == "api_timeout"
            else iter([100.0, 100.1, 100.2, 100.3, 250.0])
        )
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            try:
                obs_fn = (
                    (lambda ports=(5590,): {"5590": []})
                    if mode_case == "api_timeout"
                    else (lambda ports=(5590,): {"5590": [{"owningPid": spawned[0].pid}]} if spawned else {"5590": []})
                )
                ctx_patches = [
                    mock.patch.object(mod, "assert_ports_unbound", return_value={"5590": [], "4610": []}),
                    mock.patch.object(mod, "observe_ports", side_effect=obs_fn),
                    mock.patch.object(mod.subprocess, "Popen", side_effect=fake_popen),
                ]
                if mode_case in ("api_timeout", "ui_timeout"):
                    ctx_patches.append(mock.patch.object(mod.time, "monotonic", side_effect=lambda: next(ticks, 300.0)))
                    ctx_patches.append(mock.patch.object(mod.time, "sleep"))
                with ctx_patches[0], ctx_patches[1], ctx_patches[2]:
                    if len(ctx_patches) > 3:
                        with ctx_patches[3], ctx_patches[4]:
                            try:
                                mod.start_api_and_ui(
                                    app_conn_str="Host=127.0.0.1;Password=top_secret_xyz",
                                    ocr_enabled=True,
                                    leased_gpu_uuid=mod.EXPECTED_GPU_UUID,
                                    log_dir=td_p,
                                    tag=mode_case,
                                    secrets=["top_secret_xyz"],
                                )
                            except RuntimeError:
                                pass
                    else:
                        try:
                            mod.start_api_and_ui(
                                app_conn_str="Host=127.0.0.1;Password=top_secret_xyz",
                                ocr_enabled=True,
                                leased_gpu_uuid=mod.EXPECTED_GPU_UUID,
                                log_dir=td_p,
                                tag=mode_case,
                                secrets=["top_secret_xyz"],
                            )
                        except RuntimeError:
                            pass
                for p in spawned:
                    ident = mod.get_win32_process_identity(p.pid)
                    if ident and ident["alive"]:
                        leaked_any = True
                if any(not getattr(fh, "closed", True) for fh in fhs):
                    leaked_any = True
            finally:
                for p in spawned:
                    if p.poll() is None:
                        p.kill()
                        p.wait(timeout=10)
                for fh in fhs:
                    if hasattr(fh, "close") and not fh.closed:
                        fh.close()

    # 2. P06-02 & P06-03: Phase A stop-on-failure clean return vs. simulated failed cleanup (stuck worker)
    orig_read_text = Path.read_text

    def safe_read_text(self_p: Path, *a, **k) -> str:
        if self_p.name == "pg-local.json":
            return '{"host":"127.0.0.1","port":55438,"appUser":"u","appPassword":"secret_app_pw_99","adminUser":"a","adminPassword":"secret_adm_pw_99","migratorPassword":"secret_mig_pw_99"}'
        if self_p.name == "postmaster.pid":
            return "12345\n"
        return orig_read_text(self_p, *a, **k)

    def run_sim_live(*, workers_after: int) -> tuple[str, dict]:
        with tempfile.TemporaryDirectory() as td:
            fake_demo = Path(td) / "demo-sim"
            (fake_demo / "runs").mkdir(parents=True)

            def fake_start(*, log_dir: Path, **kw):
                log_dir.mkdir(parents=True, exist_ok=True)
                (log_dir / "api-5590-phase-a-leased.log").write_text("Conn Password=secret_app_pw_99\n", encoding="utf-8")
                return (
                    mock.MagicMock(pid=999991, poll=lambda: 0),
                    {"fh": None, "identity": {"pid": 999991, "create_filetime": 1}},
                    mock.MagicMock(pid=999992, poll=lambda: 0),
                    {"fh": None, "identity": {"pid": 999992, "create_filetime": 2}},
                )

            worker_counts = iter([0, workers_after])
            with (
                mock.patch.object(mod, "EXPECTED_DEMO_RUNTIME_ROOT", fake_demo),
                mock.patch.object(mod, "git_object_exists", return_value=True),
                mock.patch.object(mod, "git_bytes", return_value=b"{}"),
                mock.patch.object(mod, "validate_release_contract", return_value={"lease_id": "WP-0012-sim", "gpu_uuid": mod.EXPECTED_GPU_UUID}),
                mock.patch.object(mod, "inspect_readonly_q0_and_demo_roots_cpu", return_value={"writable_demo_root_exists": True}),
                mock.patch.object(mod, "assert_ports_unbound", return_value={"5590": [], "4610": [], "55438": []}),
                mock.patch.object(mod, "count_ocr_worker_processes", side_effect=lambda: next(worker_counts, workers_after)),
                mock.patch.object(mod, "get_win32_process_identity", return_value={"pid": 12345, "alive": False, "create_filetime": 1}),
                mock.patch.object(mod, "run_psql_query", side_effect=lambda s, db, sql, **k: "0" if "count(*)" in sql else '[{"attempt_id":"a1","status":"failed"}]'),
                mock.patch.object(mod, "start_api_and_ui", side_effect=fake_start),
                mock.patch.object(mod, "ProcessMemorySampler") as m_samp,
                mock.patch.object(mod, "stop_proc"),
                mock.patch.object(
                    mod.subprocess,
                    "run",
                    side_effect=lambda argv, **kw: subprocess.CompletedProcess(
                        argv,
                        1 if "drive_rehearsal_edge.mjs" in " ".join(map(str, argv)) else 0,
                        stdout="pw=secret_app_pw_99",
                        stderr="STOP-ON-FAILURE",
                    ),
                ),
                mock.patch.object(Path, "read_text", safe_read_text),
            ):
                m_samp.return_value.stop.return_value = {}
                err_msg = ""
                try:
                    mod.execute_live_rehearsal(release_commit="d" * 40, release_path="docs/coordination/WP-0012/sim.json")
                except BaseException as exc:
                    err_msg = str(exc)
            lr_file = fake_demo / "rehearsal-evidence" / "WP-0012-sim" / "owner-lease-return.json"
            lr_doc = json.loads(lr_file.read_text(encoding="utf-8"))
            all_txt = "\n".join(
                p.read_text(encoding="utf-8")
                for p in (fake_demo / "rehearsal-evidence" / "WP-0012-sim").rglob("*")
                if p.is_file()
            )
            assert "secret_app_pw_99" not in all_txt, "Secret leaked in failure logs/receipt!"
            return err_msg, lr_doc

    err_clean_stop, lr_clean_stop = run_sim_live(workers_after=0)
    err_failed_cleanup, lr_failed_cleanup = run_sim_live(workers_after=1)

    # 3. P06-05: Synthetic sample passes CPU mode, rejected in live mode, and /002 SHA 379d8c5d... rejected!
    synth_res = mod.validate_synthetic_sample_file(sample_path)

    # 4. P06-06: Loopback HTTP test of drive_rehearsal_edge.mjs --mode verify-worker-enabled-guard on ephemeral port 0
    node_exe = shutil.which("node") or "node"
    current_worker_flag: dict[str, object] = {"val": False}

    class MockExtHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            payload = {
                "status": "completed",
                "workerEnabled": current_worker_flag["val"],
                "attempts": [{"attemptId": "1"}],
                "result": {"rawSha256": "a" * 64 if "0001" in self.path else "b" * 64},
            }
            if current_worker_flag["val"] == "OMIT":
                payload.pop("workerEnabled")
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, fmt, *args):
            return

    with socketserver.TCPServer(("127.0.0.1", 0), MockExtHandler) as srv:
        eph_port = srv.server_address[1]
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                out_ok = Path(td) / "d4-ok.json"
                current_worker_flag["val"] = False
                cp_ok = subprocess.run(
                    [node_exe, str(edge_path), "--mode", "verify-worker-enabled-guard", "--apiPort", str(eph_port), "--expectWorkerEnabled", "false", "--output", str(out_ok)],
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                )
                current_worker_flag["val"] = True
                cp_mismatch = subprocess.run(
                    [node_exe, str(edge_path), "--mode", "verify-worker-enabled-guard", "--apiPort", str(eph_port), "--expectWorkerEnabled", "false", "--output", str(Path(td) / "d4-bad.json")],
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                )
                current_worker_flag["val"] = "OMIT"
                cp_omit = subprocess.run(
                    [node_exe, str(edge_path), "--mode", "verify-worker-enabled-guard", "--apiPort", str(eph_port), "--expectWorkerEnabled", "false", "--output", str(Path(td) / "d4-omit.json")],
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                )
        finally:
            srv.shutdown()

    return {
        "P06-01_partial_startup_zero_leaks": not leaked_any,
        "P06-02_clean_stop_on_failure_receipt": {
            "error": err_clean_stop,
            "clean_return_verified": lr_clean_stop.get("clean_return_verified"),
            "status": lr_clean_stop.get("status"),
            "lease_returned": lr_clean_stop.get("lease_returned"),
            "returned_utc": lr_clean_stop.get("returned_utc"),
        },
        "P06-03_failed_cleanup_unreturned_receipt": {
            "error": err_failed_cleanup,
            "clean_return_verified": lr_failed_cleanup.get("clean_return_verified"),
            "status": lr_failed_cleanup.get("status"),
            "lease_returned": lr_failed_cleanup.get("lease_returned"),
            "returned_utc": lr_failed_cleanup.get("returned_utc"),
            "cleanup_errors": lr_failed_cleanup.get("cleanup_errors"),
        },
        "P06-05_synthetic_sample": {
            "cpu_ok": synth_res["synthetic_sample_validated_on_cpu"],
            "live_rejected": synth_res["live_mode_rejected_synthetic_sample"],
        },
        "P06-06_worker_enabled_http_guard": {
            "false_matches_false_rc": cp_ok.returncode,
            "true_rejected_when_expecting_false_rc": cp_mismatch.returncode,
            "missing_boolean_rejected_rc": cp_omit.returncode,
        },
    }


def make_synthetic_v4_release(actual_head: str, now_utc: datetime) -> tuple[dict, dict[str, bytes]]:
    ownership_blob = json.dumps(
        {
            "schema": "eld-wp12-wp13-ownership-observation/1",
            "observed_utc": (now_utc - timedelta(minutes=3)).isoformat(),
            "gpu_exit": 0,
            "apps_exit": 0,
            "apps": ["1840, C:\\Windows\\System32\\dwm.exe, 142"],
            "candidate_and_gpu_processes": [
                {"ProcessId": 1840, "Name": "dwm.exe", "ExecutablePath": r"C:\Windows\System32\dwm.exe"},
            ],
            "ollama_ps_exit": 0,
            "ollama_ps": ["NAME    ID    SIZE    PROCESSOR    UNTIL"],
        },
        indent=2,
    ).encode("utf-8") + b"\n"
    model_blob = b'{"ok": true, "model_objects": 18}\n'
    author_ret_blob = json.dumps(
        {
            "schema": "eledgercare.wp0012-owner-lease-return/1",
            "owner": "eld-f4-implementer",
            "status": "completed",
            "clean_return_verified": True,
            "lease_returned": True,
            "ocr_worker_processes_running": 0,
            "lingering_attempt_processes": [],
            "cleanup_errors": [],
        }
    ).encode("utf-8") + b"\n"

    blobs = {
        "docs/coordination/WP-0012-0013/reviewer-004/ownership-before.json": ownership_blob,
        "docs/coordination/WP-0012/reviewer-004/model-before.json": model_blob,
        "docs/coordination/WP-0012/reviewer-004/author-lease-return-audit.json": author_ret_blob,
    }
    rel = {
        "schema": "eledgercare.wp0012-rehearsal-release/1",
        "synthetic_test_only": True,
        "packet": "WP-0012",
        "owner": "eld-f4-reviewer",
        "conversation_id": "61105d43-7706-45f2-9176-69d3256248e0",
        "model": "gemini-4-carbon-high",
        "effort": "high",
        "source_commit": rv4.ACCEPTED_F4_FINAL_SOURCE_SHA,
        "executing_head": actual_head,
        "prior_changes_requested_review_002": REVIEW_002_PUB_SHA,
        "accepted_preparation_review": "7777777777777777777777777777777777777777",
        "accepted_author_003": "3333333333333333333333333333333333333333",
        "author_lease_return": {
            "commit": "5555555555555555555555555555555555555555",
            "path": "docs/coordination/WP-0012/reviewer-004/author-lease-return-audit.json",
            "sha256": sha256_hex(author_ret_blob),
        },
        "product_tree_objects": dict(rv4.EXPECTED_PRODUCT_TREES),
        "pinned_digests": dict(rv4.EXPECTED_PINNED_DIGESTS),
        "lease_id": "WP-0012-reviewer-004-SYNTHETIC-V4-TEST",
        "gpu_uuid": rv4.EXPECTED_GPU_UUID,
        "released_utc": (now_utc - timedelta(minutes=2)).isoformat(),
        "expires_utc": (now_utc + timedelta(hours=4)).isoformat(),
        "max_model_attempts": 2,
        "readonly_q0_root": r"C:\Users\jackg\eLedgerCare-Q0\WP-0005",
        "runtime_root": r"C:\Users\jackg\eLedgerCare-Demo\WP-0012\reviewer",
        "database": rv4.DEMO_DATABASE,
        "ports": {"api": 5690, "ui": 4710, "postgres": 55439},
        "storage_cap_bytes": 4_294_967_296,
        "free_floor_bytes": 21_474_836_480,
        "allow_test_content": False,
        "torchvision_local_sha256_TOFU_accepted": True,
        "observation_files": {
            "ownership-before.json": {
                "path": "docs/coordination/WP-0012-0013/reviewer-004/ownership-before.json",
                "sha256": sha256_hex(ownership_blob),
            },
            "model-before.json": {
                "path": "docs/coordination/WP-0012/reviewer-004/model-before.json",
                "sha256": sha256_hex(model_blob),
            },
        },
    }
    return rel, blobs


class ReviewerV4ReconciliationTests(unittest.TestCase):
    SYNTH_COMMIT = "9999999999999999999999999999999999999999"
    SYNTH_PATH = "docs/coordination/WP-0012/releases/reviewer-004-v4-synthetic.json"

    def setUp(self) -> None:
        self.now_utc = datetime(2026, 11, 17, 16, 10, 0, tzinfo=timezone.utc)
        self.actual_head = rv4.run_git(REPO_ROOT, "rev-parse", "HEAD").lower()
        self.valid_rel, self.blobs = make_synthetic_v4_release(self.actual_head, self.now_utc)
        self.v4_script = HELPERS_DIR / "run_wp0012_reviewer_rehearsal_v4.py"
        self.edge_driver = REPO_ROOT / "docs/reviews/WP-0012/eld-f4-reviewer/preparation/helpers/drive_wp0012_edge_workflow.mjs"

    def _validate(self, doc: dict, *, blobs: dict[str, bytes] | None = None, allow_synth: bool = True) -> dict:
        use_blobs = blobs if blobs is not None else self.blobs
        synth_commits = {
            "7777777777777777777777777777777777777777",
            "3333333333333333333333333333333333333333",
            "5555555555555555555555555555555555555555",
        }
        return rv4.validate_reviewer_release_contract(
            doc,
            repo_root=REPO_ROOT,
            release_commit=self.SYNTH_COMMIT,
            release_path=self.SYNTH_PATH,
            now_utc=self.now_utc,
            blob_loader=lambda p: use_blobs[p],
            commit_exists_fn=lambda sha: (sha in synth_commits) or rv4.git_object_exists(REPO_ROOT, f"{sha}^{{commit}}"),
            helper_paths_to_bind=(self.v4_script, self.edge_driver),
            require_clean_worktree=False,
            allow_synthetic_test_only=allow_synth,
        )

    def test_01_valid_synthetic_007_bound_envelope_passes_cpu_and_fails_live_mode(self) -> None:
        res = self._validate(self.valid_rel, allow_synth=True)
        self.assertEqual(
            res["accepting_preparation_review_007"],
            {"accepted_preparation_review": "7777777777777777777777777777777777777777"},
        )
        self.assertEqual(res["prior_changes_requested_review_002"], REVIEW_002_PUB_SHA)
        self.assertNotIn("accepted_review_002", res)
        with self.assertRaisesRegex(rv4.ReviewerLeaseGuardError, "synthetic_test_only"):
            self._validate(self.valid_rel, allow_synth=False)

    def test_02_rejects_changes_requested_002_publication_and_ancestors_as_accepting_review(self) -> None:
        for bad_sha in (
            REVIEW_002_PUB_SHA,
            REVIEW_002_SOURCE_SHA,
            REVIEW_002_EVIDENCE_SHA,
            INITIAL_PREP_PUB_SHA,
            AUTHOR_001_PUB_SHA,
        ):
            doc = copy.deepcopy(self.valid_rel)
            doc["accepted_preparation_review"] = bad_sha
            with self.assertRaises(rv4.ReviewerLeaseGuardError):
                self._validate(doc)

    def test_03_accepts_007_specific_alias_keys_and_rejects_non_accepted_disposition_dict(self) -> None:
        for alias_key in ("accepted_review_007", "independent_preparation_review_007_sha", "independent_review_007"):
            doc = copy.deepcopy(self.valid_rel)
            val = doc.pop("accepted_preparation_review")
            doc[alias_key] = val
            out = self._validate(doc)
            self.assertEqual(out["accepting_preparation_review_007"], {alias_key: val})

        doc_bad_disp = copy.deepcopy(self.valid_rel)
        doc_bad_disp["accepted_preparation_review"] = {
            "commit": "7777777777777777777777777777777777777777",
            "disposition": "changes-requested",
        }
        with self.assertRaisesRegex(rv4.ReviewerLeaseGuardError, "non-accepting disposition"):
            self._validate(doc_bad_disp)

    def test_04_rejects_wrong_prior_changes_requested_review_002_sha(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["prior_changes_requested_review_002"] = "1" * 40
        with self.assertRaisesRegex(rv4.ReviewerLeaseGuardError, "prior_changes_requested_review_002"):
            self._validate(doc)

    def test_05_rejects_author_lease_return_blob_when_cleanup_failed_or_unreturned(self) -> None:
        for bad_ret in (
            {"clean_return_verified": False, "status": "failed_stopped"},
            {"clean_return_verified": True, "lease_returned": False, "status": "cleanup_failed_unreturned"},
            {"clean_return_verified": True, "ocr_worker_processes_running": 1, "status": "failed_stopped"},
            {"clean_return_verified": True, "lingering_attempt_processes": [{"pid": 4444}], "status": "failed_stopped"},
            {"clean_return_verified": True, "cleanup_errors": ["postgres_stop_failed"], "status": "failed_stopped"},
        ):
            raw_b = json.dumps(bad_ret).encode("utf-8")
            blobs = dict(self.blobs)
            blobs["docs/coordination/WP-0012/reviewer-004/author-lease-return-audit.json"] = raw_b
            doc = copy.deepcopy(self.valid_rel)
            doc["author_lease_return"]["sha256"] = sha256_hex(raw_b)
            with self.assertRaises(rv4.ReviewerLeaseGuardError):
                self._validate(doc, blobs=blobs)

    def test_06_reviewer_lease_return_receipt_marks_completed_clean_return(self) -> None:
        rr = rv4.build_reviewer_lease_return_receipt(
            lease_id="WP-0012-test",
            run_error=None,
            cleanup_errors=[],
            ports_after={"5690": [], "4710": [], "55439": []},
            pg_ctl_status_exit_code=3,
            api_stop_receipts=[{"aliveAfter": False}],
            ui_stop_receipts=[{"aliveAfter": False}],
            pre_ownership={"sole_model_job_verified": True},
            post_ownership={"sole_model_job_verified": True},
            q0_model_immutability_verified=True,
            persisted_counts={"documents": 2},
            run_directories=["r1", "r2"],
            postmaster_recorded={"pid": 100},
            secrets=["sec123"],
            now_utc=self.now_utc,
        )
        self.assertEqual(rr["status"], "completed")
        self.assertTrue(rr["lease_returned"])
        self.assertTrue(rr["clean_return_verified"])
        self.assertIsNotNone(rr["returned_utc"])

    def test_07_reviewer_lease_return_receipt_distinguishes_clean_stop_on_failure_from_failed_cleanup(self) -> None:
        rr_clean_fail = rv4.build_reviewer_lease_return_receipt(
            lease_id="WP-0012-test",
            run_error="Attempt 1 failed Password=sec123",
            cleanup_errors=[],
            ports_after={"5690": [], "4710": [], "55439": []},
            pg_ctl_status_exit_code=3,
            api_stop_receipts=[{"aliveAfter": False}],
            ui_stop_receipts=[{"aliveAfter": False}],
            pre_ownership={"sole_model_job_verified": True},
            post_ownership={"sole_model_job_verified": True},
            q0_model_immutability_verified=True,
            persisted_counts={"documents": 1},
            run_directories=["r1"],
            postmaster_recorded={"pid": 100},
            secrets=["sec123"],
            now_utc=self.now_utc,
        )
        self.assertEqual(rr_clean_fail["status"], "failed_stopped_lease_returned")
        self.assertTrue(rr_clean_fail["lease_returned"])
        self.assertTrue(rr_clean_fail["clean_return_verified"])
        self.assertIsNotNone(rr_clean_fail["returned_utc"])
        self.assertNotIn("sec123", rr_clean_fail["failure_detail"])

    def test_08_reviewer_lease_return_receipt_remains_explicitly_unreturned_on_lingering_port(self) -> None:
        rr = rv4.build_reviewer_lease_return_receipt(
            lease_id="WP-0012-test",
            run_error=None,
            cleanup_errors=[],
            ports_after={"5690": [{"owningPid": 9999}], "4710": [], "55439": []},
            pg_ctl_status_exit_code=3,
            api_stop_receipts=[{"aliveAfter": False}],
            ui_stop_receipts=[{"aliveAfter": False}],
            pre_ownership={"sole_model_job_verified": True},
            post_ownership={"sole_model_job_verified": True},
            q0_model_immutability_verified=True,
            persisted_counts={},
            run_directories=[],
            postmaster_recorded=None,
            secrets=[],
            now_utc=self.now_utc,
        )
        self.assertEqual(rr["status"], "cleanup_failed_lease_unreturned")
        self.assertFalse(rr["lease_returned"])
        self.assertFalse(rr["clean_return_verified"])
        self.assertIsNone(rr["returned_utc"])

    def test_09_reviewer_lease_return_receipt_remains_unreturned_on_lingering_worker_or_pg_running(self) -> None:
        for pg_rc, post_own in (
            (0, {"sole_model_job_verified": True}),
            (3, {"sole_model_job_verified": False, "error": "Competing python worker"}),
        ):
            rr = rv4.build_reviewer_lease_return_receipt(
                lease_id="WP-0012-test",
                run_error="Phase 1 failed",
                cleanup_errors=[],
                ports_after={"5690": [], "4710": [], "55439": []},
                pg_ctl_status_exit_code=pg_rc,
                api_stop_receipts=[],
                ui_stop_receipts=[],
                pre_ownership={"sole_model_job_verified": True},
                post_ownership=post_own,
                q0_model_immutability_verified=True,
                persisted_counts={},
                run_directories=[],
                postmaster_recorded=None,
                secrets=[],
                now_utc=self.now_utc,
            )
            self.assertEqual(rr["status"], "cleanup_failed_lease_unreturned")
            self.assertFalse(rr["lease_returned"])
            self.assertIsNone(rr["returned_utc"])

    def test_10_reviewer_lease_return_receipt_remains_unreturned_when_child_alive_or_q0_drifted(self) -> None:
        rr = rv4.build_reviewer_lease_return_receipt(
            lease_id="WP-0012-test",
            run_error=None,
            cleanup_errors=[],
            ports_after={"5690": [], "4710": [], "55439": []},
            pg_ctl_status_exit_code=3,
            api_stop_receipts=[{"aliveAfter": True}],
            ui_stop_receipts=[],
            pre_ownership={"sole_model_job_verified": True},
            post_ownership={"sole_model_job_verified": True},
            q0_model_immutability_verified=False,
            persisted_counts={},
            run_directories=[],
            postmaster_recorded=None,
            secrets=[],
            now_utc=self.now_utc,
        )
        self.assertFalse(rr["lease_returned"])
        self.assertIsNone(rr["returned_utc"])
        self.assertIn("api_child_alive_after_stop", rr["cleanup_errors"])
        self.assertIn("q0_model_immutability_check_failed", rr["cleanup_errors"])

    def test_11_protects_correction_006_review_namespace_in_addition_to_preparation_and_002(self) -> None:
        for rel_p in (
            "docs/reviews/WP-0012/eld-f4-reviewer/preparation/out.json",
            "docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/out.json",
            "docs/reviews/WP-0012/eld-f4-reviewer/correction-006-review/preliminary/out.json",
            "docs/reviews/WP-0012/eld-f4-reviewer/correction-006-review/final/out.json",
        ):
            with self.assertRaises(rv4.ReviewerLeaseGuardError):
                rv4.guard_new_non_overwriting_output_targets(
                    REPO_ROOT,
                    file_targets=[REPO_ROOT / rel_p],
                    dir_targets=[],
                )

    def test_12_accepts_brand_new_runtime_004_namespace(self) -> None:
        rv4.guard_new_non_overwriting_output_targets(
            REPO_ROOT,
            file_targets=[REPO_ROOT / "docs/reviews/WP-0012/eld-f4-reviewer/runtime-004/observations/summary.json"],
            dir_targets=[REPO_ROOT / "docs/reviews/WP-0012/eld-f4-reviewer/runtime-004/observations/logs"],
        )

    def test_13_wddm_desktop_allowed_and_competing_module_worker_blocked(self) -> None:
        ok = rv4.evaluate_gpu_and_model_ownership(
            {"apps": ["1840, C:\\Windows\\System32\\dwm.exe, 150"], "candidate_and_gpu_processes": [], "ollama_ps": []},
            self_pid=99999,
        )
        self.assertTrue(ok["sole_model_job_verified"])
        self.assertFalse(ok["hardware_exclusivity_claimed"])

        with self.assertRaises(rv4.CompetingModelOwnershipError):
            rv4.evaluate_gpu_and_model_ownership(
                {
                    "apps": [],
                    "candidate_and_gpu_processes": [
                        {"ProcessId": 50000, "Name": "python.exe", "CommandLine": "python -m qualification.mapping_v2.run"}
                    ],
                    "ollama_ps": None,
                },
                self_pid=99999,
            )

    def test_14_atomic_startup_kills_api_when_api_dies_or_ui_fails(self) -> None:
        recorded: list[int] = []
        orig_insp = rv4.inspect_process

        def spy(pid: int, cwd: Path):
            r = orig_insp(pid, cwd)
            if not recorded and r is not None:
                recorded.append(pid)
            return r

        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            with mock.patch.object(rv4, "inspect_process", side_effect=spy):
                with self.assertRaisesRegex(RuntimeError, "Owned UI exited early"):
                    rv4.start_owned_services_atomic(
                        api_cmd=[sys.executable, "-B", "-c", "import time; time.sleep(60)"],
                        api_cwd=td_p,
                        api_env=dict(os.environ),
                        api_log_path=td_p / "api.log",
                        ui_cmd=[sys.executable, "-B", "-c", "import sys; sys.exit(1)"],
                        ui_cwd=td_p,
                        ui_env=dict(os.environ),
                        ui_log_path=td_p / "ui.log",
                        repo_root=REPO_ROOT,
                        api_ready_fn=lambda: True,
                        ui_ready_fn=lambda: False,
                        api_timeout_s=5.0,
                        ui_timeout_s=5.0,
                    )
            self.assertIsNone(rv4.inspect_process(recorded[0], REPO_ROOT))

    def test_15_v4_contains_zero_ml_or_research_ast_imports(self) -> None:
        tree = ast.parse(self.v4_script.read_text(encoding="utf-8"), filename=str(self.v4_script))
        bad = ("torch", "transformers", "safetensors", "accelerate", "pypdfium2", "PIL", "qualification", "research", "evaluation")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.assertFalse(a.name.startswith(bad), a.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                self.assertFalse(node.module.startswith(bad), node.module)

    def test_16_cli_refuses_changes_requested_002_commit_as_release_commit(self) -> None:
        cp = rv4.run_cmd(
            [
                sys.executable,
                "-B",
                str(self.v4_script),
                "--mode",
                "validate-release-cpu",
                "--release-commit",
                REVIEW_002_PUB_SHA,
                "--release-path",
                self.SYNTH_PATH,
                "--summary-output",
                "docs/reviews/WP-0012/eld-f4-reviewer/runtime-004/check.json",
            ],
            cwd=REPO_ROOT,
        )
        self.assertEqual(cp.returncode, 2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight-self-and-old-001", "verify-bound-006"), required=True)
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--candidate-dir", default="docs/implementation/WP-0012/eld-f4-implementer/correction-006")
    parser.add_argument("--output", required=True)
    parser.add_argument("--log-output", required=True)
    parser.add_argument("--resource-return-output", required=True)
    args = parser.parse_args(argv)

    porcelain = rv4.run_git(REPO_ROOT, "status", "--porcelain", "--untracked-files=all")
    if args.require_clean and porcelain != "":
        raise AssertionError(f"Worktree must be clean before probe run:\n{porcelain}")

    executing_head = rv4.run_git(REPO_ROOT, "rev-parse", "HEAD")

    # Verify immutable prior reviewer artifacts are untouched
    if rv4.run_git(
        REPO_ROOT,
        "diff",
        "--name-only",
        REVIEW_002_PUB_SHA,
        executing_head,
        "--",
        "docs/reviews/WP-0012/eld-f4-reviewer/preparation",
        "docs/reviews/WP-0012/eld-f4-reviewer/author-001-review",
        "docs/agent-reports/eld-f4-reviewer/WP-0012/002_2026-11-17_review_eld-f4-reviewer.md",
    ):
        raise AssertionError("Immutable preparation, author-001-review, or /002 report was modified!")

    old_001_probes = run_old_001_baseline_probes()

    v4_buf = io.StringIO()
    v4_suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReviewerV4ReconciliationTests)
    v4_res = unittest.TextTestRunner(stream=v4_buf, verbosity=2).run(v4_suite)
    if not v4_res.wasSuccessful() or v4_res.testsRun != 16:
        raise AssertionError(f"Reviewer v4 tests failed:\n{v4_buf.getvalue()}")

    provisional_obs = None
    bound_006_probes = None
    if args.mode == "preflight-self-and-old-001":
        provisional_obs = snapshot_provisional_author_006_readonly(PROVISIONAL_EXT_006_DIR)
    else:
        cand_dir = (REPO_ROOT / args.candidate_dir).resolve()
        bound_006_probes = run_bound_006_candidate_probes(cand_dir)

    ports_rev = rv4.observe_ports(rv4.REVIEWER_PORTS, REPO_ROOT)
    pg_ctl = REPO_ROOT / ".local/tools/pgsql-18.7-1/bin/pg_ctl.exe"
    pg_rc = rv4.run_cmd([str(pg_ctl), "status", "-D", str(REPO_ROOT / ".local/postgres-data")], cwd=REPO_ROOT).returncode
    runs_dir = rv4.WRITABLE_DEMO_ROOT / "runs"
    run_entries = sorted(p.name for p in runs_dir.iterdir()) if runs_dir.is_dir() else []
    if any(len(ports_rev[str(p)]) != 0 for p in rv4.REVIEWER_PORTS) or pg_rc != 3 or run_entries != []:
        raise AssertionError(f"Reviewer resources not idle: ports={ports_rev}, pg_rc={pg_rc}, runs={run_entries}")

    out_p = (REPO_ROOT / args.output).resolve()
    log_p = (REPO_ROOT / args.log_output).resolve()
    rr_p = (REPO_ROOT / args.resource_return_output).resolve()
    for d in (out_p.parent, log_p.parent, rr_p.parent):
        d.mkdir(parents=True, exist_ok=True)

    log_p.write_text(
        f"=== ReviewerV4ReconciliationTests ({v4_res.testsRun} tests) ===\n{v4_buf.getvalue()}",
        encoding="utf-8",
        newline="\n",
    )

    rr_p.write_text(
        json.dumps(
            {
                "schema": "eledgercare.wp-0012.reviewer-007-probe-resource-return/1",
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "mode": args.mode,
                "canonical_007_published": False,
                "live_model_or_gpu_executed": False,
                "author_resources_touched": False,
                "reviewer_ports_after": ports_rev,
                "pg_ctl_status_exit_code": pg_rc,
                "writable_demo_run_dir_count": len(run_entries),
                "immutable_002_and_v3_preserved": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    out_p.write_text(
        json.dumps(
            {
                "schema": "eledgercare.wp-0012.reviewer-007-probe-summary/1",
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "mode": args.mode,
                "executing_head_sha": executing_head,
                "canonical_007_disposition": "held_for_exact_frozen_006_dispatch" if args.mode == "preflight-self-and-old-001" else "evaluated_bound_006",
                "live_model_or_gpu_executed": False,
                "old_001_baseline_probes": old_001_probes,
                "reviewer_v4_guard_reconciliation": {
                    "helper_path": "docs/reviews/WP-0012/eld-f4-reviewer/correction-006-review/helpers/run_wp0012_reviewer_rehearsal_v4.py",
                    "helper_sha256_lf": sha256_hex((HELPERS_DIR / "run_wp0012_reviewer_rehearsal_v4.py").read_bytes().replace(b"\r\n", b"\n")),
                    "unit_tests_run": v4_res.testsRun,
                    "unit_tests_passed": v4_res.wasSuccessful(),
                },
                "provisional_author_006_readonly_snapshot": provisional_obs,
                "bound_006_candidate_probes": bound_006_probes,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
