"""Native adaptation of Carbon old-/001 baseline function, preserving original file.

Corrects the preliminary test's tuple-vs-string comparison: the actual old
extractor returns (key, SHA). First frozen failing evidence remains retained.
"""
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock
from probe_correction_006_failure_paths_cpu import (
    load_module_from_path, AUTHOR_001_HELPERS_DIR, REVIEW_002_PUB_SHA,
)

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

    extracted_key, extracted_002_sha = old_drv._extract_independent_review_002_sha({"accepted_review_002": REVIEW_002_PUB_SHA})
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

