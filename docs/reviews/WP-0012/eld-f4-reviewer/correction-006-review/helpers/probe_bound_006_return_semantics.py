"""Independent exact-source CPU reproduction of F12-B2 return semantics.

No service, model, GPU, author resource or external data access. The real helper
is compiled from exact Git-matched Python source; all operational boundaries are
mocked and all writes use a temporary directory. This is not resource-return proof.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[6]
PREFIX = "docs/implementation/WP-0012/eld-f4-implementer"
OWNED = ROOT / "docs/reviews/WP-0012/eld-f4-reviewer/correction-006-review"


def load_exact(commit, path, name):
    expected = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
    current = (ROOT / path).read_bytes()
    if current.replace(b"\r\n", b"\n") != expected.replace(b"\r\n", b"\n"):
        raise AssertionError(f"Candidate working bytes differ from {commit}:{path}")
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / path)
    sys.modules[name] = module
    exec(compile(current, module.__file__, "exec"), module.__dict__)
    return module, {"commit": commit, "path": path, "bytes": len(current),
                    "sha256_raw": hashlib.sha256(current).hexdigest(),
                    "sha256_git": hashlib.sha256(expected).hexdigest()}


def simulate_first_failure(mod, workers_after, fail_at="none"):
    with tempfile.TemporaryDirectory(prefix="wp0012-independent-return-") as scratch:
        temp = Path(scratch)
        (temp / "runs").mkdir()
        calls = {"browser": 0, "stop_pg": 0, "worker_observations": 0, "attempt_query": 0,
                 "q0_observations": 0, "port_observations": 0}
        real_read = Path.read_text
        def read(path, *args, **kwargs):
            if path.name == "pg-local.json":
                return json.dumps(dict(host="127.0.0.1", port=55438, appUser="synthetic",
                    appPassword="SYNTHETIC-APP-SECRET", adminPassword="SYNTHETIC-ADMIN-SECRET",
                    migratorPassword="SYNTHETIC-MIGRATION-SECRET"))
            if path.name == "postmaster.pid":
                return "999999\n"
            return real_read(path, *args, **kwargs)
        def command(argv, **kwargs):
            text = " ".join(map(str, argv))
            if "drive_rehearsal_edge.mjs" in text:
                calls["browser"] += 1
                return subprocess.CompletedProcess(argv, 1, "Password=SYNTHETIC-APP-SECRET", "first attempt failed")
            if "stop-cluster.ps1" in text:
                calls["stop_pg"] += 1
                if fail_at == "postgres_stop":
                    raise subprocess.TimeoutExpired("synthetic stop", 1)
            return subprocess.CompletedProcess(argv, 0, "", "")
        def workers():
            calls["worker_observations"] += 1
            return 0 if calls["worker_observations"] == 1 else workers_after
        def query(settings, db, sql, **kwargs):
            if "count(*)" in sql:
                return "0"
            calls["attempt_query"] += 1
            if fail_at == "query":
                raise OSError("synthetic query unavailable")
            return json.dumps([{"attempt_id": "synthetic-1", "status": "failed"}])
        def q0(**kwargs):
            calls["q0_observations"] += 1
            if fail_at == "q0" and calls["q0_observations"] > 1:
                raise OSError("synthetic q0 check failed")
            return {"writable_demo_root_exists": True}
        def ports(*args, **kwargs):
            calls["port_observations"] += 1
            if fail_at == "ports" and calls["port_observations"] > 1:
                raise OSError("synthetic ports unavailable")
            return {"5590": [], "4610": [], "55438": []}
        def start(**kwargs):
            (kwargs["log_dir"] / "synthetic-api.log").write_text("Password=SYNTHETIC-APP-SECRET\n")
            return (mock.Mock(pid=999998), {"identity": {"pid": 999998, "create_filetime": 1}, "fh": None},
                    mock.Mock(pid=999997), {"identity": {"pid": 999997, "create_filetime": 2}, "fh": None})
        def stop(*args, **kwargs):
            if fail_at == "child_stop":
                raise OSError("synthetic child stop failed")
        # Replace the module's subprocess reference, never the global stdlib
        # subprocess object used by the surrounding test or other owners.
        proxy = types.SimpleNamespace(run=command, Popen=subprocess.Popen, CompletedProcess=subprocess.CompletedProcess)
        patches = dict(EXPECTED_DEMO_RUNTIME_ROOT=temp, subprocess=proxy,
            git_object_exists=mock.Mock(return_value=True), git_bytes=mock.Mock(return_value=b"{}"),
            validate_release_contract=mock.Mock(return_value={"lease_id": "WP-0012-independent-synthetic", "gpu_uuid": mod.EXPECTED_GPU_UUID}),
            inspect_readonly_q0_and_demo_roots_cpu=q0, assert_ports_unbound=ports,
            observe_ports=mock.Mock(return_value={}), count_ocr_worker_processes=workers,
            get_win32_process_identity=mock.Mock(return_value={"pid": 999999, "alive": False, "create_filetime": 3}),
            is_exact_process_alive=mock.Mock(return_value=False), run_psql_query=query,
            start_api_and_ui=start, stop_proc=stop, ProcessMemorySampler=mock.Mock())
        error = None
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(Path, "read_text", read))
            for name, value in patches.items():
                stack.enter_context(mock.patch.object(mod, name, value))
            if hasattr(mod, "scrub_directory_secrets") and fail_at == "scrub":
                stack.enter_context(mock.patch.object(mod, "scrub_directory_secrets", side_effect=OSError("synthetic scrub failed")))
            mod.ProcessMemorySampler.return_value.stop.return_value = {}
            try:
                mod.execute_live_rehearsal(release_commit="9" * 40, release_path="docs/coordination/WP-0012/synthetic.json")
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
        receipt_path = temp / "rehearsal-evidence/WP-0012-independent-synthetic/owner-lease-return.json"
        receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
        redacted = all("SYNTHETIC-APP-SECRET" not in p.read_text(errors="replace") for p in temp.rglob("*") if p.is_file())
        return {"simulation_only": True, "calls": calls, "exception": error, "receipt": receipt,
                "synthetic_secret_removed_from_outputs": redacted}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT).strip():
        raise RuntimeError("Frozen clean reviewer worktree required")
    output = (ROOT / args.output_dir).resolve()
    if not output.is_relative_to(OWNED) or output.exists():
        raise RuntimeError("Brand-new owned output directory required")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    old, old_input = load_exact("ad5202a029a7a86bea5fa3e3d97760d0a9cc673a", PREFIX + "/helpers/run_wp0012_rehearsal.py", "independent_old_return")
    new, new_input = load_exact(args.candidate_commit, PREFIX + "/correction-006/helpers/run_wp0012_rehearsal.py", "independent_new_return")
    results = {"old_first_failure": simulate_first_failure(old, 0), "new_clean_stop": simulate_first_failure(new, 0),
               "new_worker_remains": simulate_first_failure(new, 1)}
    for fail_at in ("postgres_stop", "query", "q0", "ports", "child_stop", "scrub"):
        results["new_" + fail_at] = simulate_first_failure(new, 0, fail_at)
    checks = {
        "old_first_failure_no_receipt_reproduced": results["old_first_failure"]["receipt"] is None,
        "new_clean_stop_verified": results["new_clean_stop"]["receipt"]["clean_return_verified"] is True,
        "new_clean_stop_scrubbed": results["new_clean_stop"]["synthetic_secret_removed_from_outputs"],
        "all_new_failures_stop_after_first_browser": all(v["calls"]["browser"] == 1 for k, v in results.items() if k.startswith("new_")),
        "all_cleanup_failures_emit_unclean_receipt": all(v["receipt"] and v["receipt"]["clean_return_verified"] is False for k, v in results.items() if k.startswith("new_") and k != "new_clean_stop"),
        "all_cleanup_failures_explicitly_unreturned": all(v["receipt"].get("lease_returned") is False and v["receipt"].get("returned_utc") is None for k, v in results.items() if k.startswith("new_") and k != "new_clean_stop"),
    }
    output.mkdir(parents=True, exist_ok=False)
    document = {"schema": "eledgercare.wp0012.independent-return-probe/1", "utc": datetime.now(timezone.utc).isoformat(),
                "source_candidate": args.candidate_commit, "reviewer_frozen_head": head,
                "inputs": [old_input, new_input], "checks": checks, "results": results,
                "actual_service_model_gpu_activity": False, "author_resources_touched": False}
    (output / "return-probe.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
