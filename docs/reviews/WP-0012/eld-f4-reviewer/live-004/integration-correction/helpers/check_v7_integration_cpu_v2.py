"""CPU adapter v2: preserve original; correct historical F3/F4 schema distinction.

Every API process is forced disabled and checked again at Popen. Live browser
modes are blocked and replaced by actual read-only empty-archive browser checks.
Synthetic phase IDs test argv plumbing only. No upload/queue/model is executed.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import traceback
from types import SimpleNamespace
from unittest.mock import patch

import run_wp0012_reviewer_rehearsal_v7 as runner
import ownership_v6

ROOT = Path(__file__).resolve().parents[7]
PREP_PATH = ROOT / "docs/reviews/WP-0012/eld-f4-reviewer/preparation/helpers"
sys.path.insert(0, str(PREP_PATH))
import run_wp0012_reviewer_rehearsal as prep

AUTH = "ddeeaba37868ee635c8f9e5641e3c0fc04404156"
SOURCE = "5e75cacd11f18bf6135376e3e1e10887c1447e1f"
BASE = "ae71a7362718f36e351e3fd442d9751d875146fe"
PWSH = "pwsh"
SYNTHETIC_IDS = ("00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002")


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    assert not path.exists(), f"New evidence required: {path}"
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def load_json_git(spec):
    return json.loads(git("show", spec))


def source_check():
    paths = (Path(runner.__file__), Path(ownership_v6.__file__))
    for p in paths:
        assert p.read_bytes() == git("show", f"{SOURCE}:{p.relative_to(ROOT).as_posix()}")
    assert prep.MODEL_MANIFEST_SHA256 == "0df07bc60abf6937c917040bced32afabd7e4d11bafc0bd99902abca610a81be"
    for p in (Path(prep.__file__), PREP_PATH / "drive_wp0012_edge_workflow.mjs"):
        assert p.read_bytes() == git("show", f"{BASE}:{p.relative_to(ROOT).as_posix()}")


def pure_controls(output):
    actual = prep.verify_q0_readonly_pure_stdlib(ROOT)
    write(output / "actual-q0.json", actual)
    runner.verify_q0_receipt_contract(actual, prep)
    cases = [dict(name="actual_q0_schema", passed=True)]
    try:
        actual["demo_root_bytes"]
        cases.append(dict(name="original_v6_missing_disk_key", passed=False))
    except KeyError as exc:
        cases.append(dict(name="original_v6_missing_disk_key", passed=True, original_error=repr(exc)))
    for key, value in (("missing_or_mismatched_distributions", ["synthetic missing"]), ("unexpected_extra_model_entries", ["synthetic.py"]), ("forbidden_modules_present", ["synthetic_forbidden"]), ("verified_model_files", []), ("model_manifest_sha256", "0" * 64)):
        bad = copy.deepcopy(actual)
        bad[key] = value
        try:
            runner.verify_q0_receipt_contract(bad, prep)
            passed = False
        except runner.ReviewerLeaseGuardError:
            passed = True
        cases.append(dict(name=f"q0_reject_{key}", passed=passed))
    with tempfile.TemporaryDirectory(prefix="wp0012-v7-owned-disk-") as directory:
        root = Path(directory)
        (root / "one.bin").write_bytes(b"1234567")
        (root / "nested").mkdir()
        (root / "nested/two.bin").write_bytes(b"123")
        result = runner.measure_owned_demo_storage(root)
        cases.append(dict(name="actual_file_size_measurement", passed=result["demo_root_bytes"] == 10 and result["file_count"] == 2 and result["demo_drive_free_bytes"] == __import__('shutil').disk_usage(root).free, result=result))
        for label, patches in (("over_cap", {"STORAGE_CAP_BYTES": 9}), ("below_floor", {"MIN_FREE_DISK_BYTES": 10**30})):
            with patch.multiple(runner, **patches):
                try:
                    runner.measure_owned_demo_storage(root)
                    passed = False
                except runner.ReviewerLeaseGuardError:
                    passed = True
            cases.append(dict(name=label, passed=passed))
        with patch.object(runner.shutil, "disk_usage", side_effect=OSError("deliberate failed disk observation")):
            try:
                runner.measure_owned_demo_storage(root)
                passed = False
            except OSError:
                passed = True
        cases.append(dict(name="failed_disk_observation", passed=passed))
        with patch.object(runner, "is_reparse_or_link", side_effect=lambda p: Path(p).name == "nested"):
            try:
                runner.measure_owned_demo_storage(root)
                passed = False
            except runner.ReviewerLeaseGuardError:
                passed = True
        cases.append(dict(name="linked_descendant", passed=passed))
    write(output / "controls.json", dict(cases=cases, passed=sum(r["passed"] for r in cases), total=len(cases)))
    assert all(r["passed"] for r in cases)


def dependencies(output):
    pg = prep.verify_pg_subset(ROOT / ".local/tools", ROOT)
    write(output / "postgres-subset.json", pg)
    assert pg["file_count"] == prep.EXPECTED_PG_FILES and pg["total_bytes"] == prep.EXPECTED_PG_BYTES
    assert all(pg[k] == [] for k in ("missing_files", "extra_files", "mismatched_files", "reparse_points"))
    assert pg["subset_manifest_sha256"] == prep.EXPECTED_PG_SUBSET_SHA and pg["central_directory_sha256"] == prep.EXPECTED_PG_CD_SHA and pg["authenticode_status"] == "Valid"
    env = dict(os.environ, DOTNET_CLI_HOME=str(ROOT / ".local/dotnet-home"), DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1", DOTNET_NOLOGO="1", NUGET_PACKAGES=str(ROOT / ".local/nuget/packages"))
    command = ["dotnet", "build", "src/ELedgerCare.Api/ELedgerCare.Api.csproj", "-c", "Release", "--no-restore"]
    cp = runner.run_cmd(command, cwd=ROOT, env=env)
    (output / "offline-build.log").write_text(cp.stdout + cp.stderr, encoding="utf-8")
    assert cp.returncode == 0
    write(output / "dependency-check.json", dict(build_command=command, build_exit=cp.returncode, api_dll_exists=(ROOT / "src/ELedgerCare.Api/bin/Release/net10.0/ELedgerCare.Api.dll").is_file(), angular_cli_exists=(ROOT / "web/node_modules/@angular/cli/bin/ng.js").is_file(), playwright_exists=(ROOT / "web/node_modules/@playwright/test/package.json").is_file()))


class DeliberateBoundaryStop(RuntimeError):
    pass


def lifecycle(output, deliberate):
    output.mkdir(exist_ok=False)
    events = []
    receipts = []
    history = {}
    started = utc()
    settings = json.loads((ROOT / ".local/secrets/pg-local.json").read_text())
    secrets = [settings[k] for k in ("adminPassword", "appPassword", "migratorPassword")]
    psql = ROOT / ".local/tools/pgsql-18.7-1/bin/psql.exe"
    pgctl = ROOT / ".local/tools/pgsql-18.7-1/bin/pg_ctl.exe"
    pgdata = ROOT / ".local/postgres-data"
    assert all(v == [] for v in runner.observe_ports(runner.REVIEWER_PORTS, ROOT).values())
    assert runner.run_cmd([str(pgctl), "status", "-D", str(pgdata)], cwd=ROOT).returncode == 3
    assert list((runner.WRITABLE_DEMO_ROOT / "runs").iterdir()) == []
    baseline = load_json_git(f"{AUTH}:docs/coordination/WP-0012/reviewer-004-release-r2/final/ownership-before.json")
    real_popen, real_run = subprocess.Popen, runner.run_cmd
    real_start = runner.start_owned_services_atomic
    real_snapshot = prep.compute_canonical_8table_snapshot
    real_q0 = prep.verify_q0_readonly_pure_stdlib
    stage = 0

    def event(value):
        events.append(dict(utc=utc(), **value))
        with (output / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(events[-1]) + "\n")

    def safe_popen(argv, *args, **kwargs):
        assert isinstance(argv, (list, tuple)), "CPU integration forbids shell command strings"
        command = [str(v) for v in argv]
        base = Path(command[0]).name.lower()
        if base in ("python", "python.exe", "pythonw.exe"):
            raise AssertionError("CPU integration forbids child Python/model execution")
        if base in ("dotnet", "dotnet.exe"):
            assert command[1:] == [str(ROOT / "src/ELedgerCare.Api/bin/Release/net10.0/ELedgerCare.Api.dll")]
            assert kwargs.get("env", {}).get("LocalOcr__Enabled") == "false", "Enabled API launch forbidden"
        if base in ("node", "node.exe"):
            if "drive_wp0012_edge_workflow.mjs" in command[1]:
                assert command[command.index("--mode") + 1] == "cpu-preflight"
                assert command[command.index("--target") + 1] == "empty-ready-db"
            else:
                assert command[1] == "node_modules/@angular/cli/bin/ng.js" and command[2] == "serve"
        if base == "ollama.exe":
            assert command[1:] == ["ps"]
        proc = real_popen(argv, *args, **kwargs)
        event(dict(event="subprocess_started", pid=proc.pid, executable=base,
                   creation_utc=ownership_v6.popen_creation_utc(proc),
                   command_sha256=sha(json.dumps(command).encode()),
                   api_enabled=kwargs.get("env", {}).get("LocalOcr__Enabled") if base.startswith("dotnet") else None))
        return proc

    def disabled_start(**kwargs):
        requested = kwargs["api_env"]["LocalOcr__Enabled"]
        kwargs["api_env"] = dict(kwargs["api_env"], LocalOcr__Enabled="false")
        result = real_start(**kwargs)
        event(dict(event="owned_services_ready", original_requested_enabled=requested, actual_enabled="false", api_identity=result[1], ui_identity=result[3]))
        return result

    def snapshot(*args, **kwargs):
        result = real_snapshot(*args, **kwargs)
        assert all(v == 0 for v in result["counts"].values())
        for db in (runner.HISTORICAL_SEED_DB, runner.HISTORICAL_MIGRATED_DB):
            state = dict(core=real_snapshot(psql, settings, db, ROOT))
            if db == runner.HISTORICAL_MIGRATED_DB:
                state["projection"] = prep.compute_projection_tables_snapshot(psql, settings, db, ROOT)
            if db in history:
                assert history[db] == state, "Historical database changed"
            else:
                history[db] = state
        receipts.append(dict(kind="canonical8table", actual=result))
        return result

    def q0(*args, **kwargs):
        result = real_q0(*args, **kwargs)
        receipts.append(dict(kind="actual_q0", actual=result))
        return result

    def browser_adapter(argv, **kwargs):
        nonlocal stage
        if len(argv) > 1 and str(argv[1]).endswith("drive_wp0012_edge_workflow.mjs"):
            mode = argv[argv.index("--mode") + 1]
            assert mode == ("live-phase1-leased" if stage == 0 else "live-phase2-post-restart")
            event(dict(event="live_browser_intercepted_not_executed", original_argv=argv, synthetic_only=True))
            if deliberate:
                raise DeliberateBoundaryStop("Deliberate CPU stop before browser phase one; no upload/model")
            if stage:
                assert argv[argv.index("--wo-document-id") + 1] == SYNTHETIC_IDS[0]
                assert argv[argv.index("--mp-document-id") + 1] == SYNTHETIC_IDS[1]
            target = Path(argv[argv.index("--output") + 1])
            actual_receipt = output / f"actual-empty-browser-{stage + 1}.json"
            actual_shots = output / f"actual-empty-screens-{stage + 1}"
            command = [argv[0], argv[1], "--mode", "cpu-preflight", "--target", "empty-ready-db", "--ui-port", str(runner.UI_PORT), "--api-port", str(runner.API_PORT), "--output", str(actual_receipt), "--screenshot-dir", str(actual_shots)]
            cp = real_run(command, cwd=ROOT, timeout_s=240)
            event(dict(event="actual_read_only_browser_completed", argv=command, exit_code=cp.returncode))
            if cp.returncode != 0:
                return cp
            observed = json.loads(actual_receipt.read_text())
            assert all(observed[k] == 0 for k in ("allEmptyCount", "machineEmptyCount", "reviewedEmptyCount", "nonGetApiCallCount"))
            synthetic = dict(schema="CPU-ONLY-NOT-LIVE-PHASE-RECEIPT", synthetic_test_only=True,
                             woDocument={"documentId": SYNTHETIC_IDS[0]}, mpDocument={"documentId": SYNTHETIC_IDS[1]},
                             actual_empty_browser_receipt=str(actual_receipt), actual_attempt_count=0, actual_result_count=0)
            write(target, synthetic)
            stage += 1
            return cp
        return real_run(argv, **kwargs)

    def cpu_validation(*args, **kwargs):
        return dict(lease_id="CPU-INTEGRATION-NOT-A-LEASE", parsed_pre_lease_blobs={"explicit_root_idle_cpu_fixture": baseline}, synthetic_test_only=True)

    command = ["--mode", "live-leased-rehearsal", "--release-commit", AUTH,
               "--release-path", "docs/coordination/WP-0012/releases/reviewer-004-r2.json",
               "--summary-output", str(output / "cpu-main-summary.json"), "--q0-check-output", str(output / "q0.json"),
               "--resource-return-output", str(output / "cpu-resource-return.json"), "--logs-dir", str(output / "logs"),
               "--screenshots-dir", str(output / "synthetic-phase-screens-unused")]
    outcome = {}
    try:
        with patch.object(subprocess, "Popen", side_effect=safe_popen), patch.object(runner, "validate_reviewer_release_contract", side_effect=cpu_validation), patch.object(runner, "start_owned_services_atomic", side_effect=disabled_start), patch.object(runner, "run_cmd", side_effect=browser_adapter), patch.object(prep, "compute_canonical_8table_snapshot", side_effect=snapshot), patch.object(prep, "verify_q0_readonly_pure_stdlib", side_effect=q0):
            try:
                outcome["main_exit"] = runner.main(command)
            except DeliberateBoundaryStop as exc:
                outcome["expected_deliberate_exception"] = str(exc)
    except BaseException as exc:
        outcome["unexpected_exception"] = {"type": type(exc).__name__, "message": runner.redact_secrets(str(exc), secrets), "traceback": runner.redact_secrets(traceback.format_exc(), secrets)}
    finally:
        final_ports = runner.observe_ports(runner.REVIEWER_PORTS, ROOT)
        pg_status = real_run([str(pgctl), "status", "-D", str(pgdata)], cwd=ROOT).returncode
        outcome.update(started_utc=started, finished_utc=utc(), synthetic_cpu_adapter=True,
                       runtime_authorization=False, services_forced_disabled=True,
                       actual_browser_phases=stage, actual_live_browser_phases=0,
                       actual_model_attempts=0, live_two_attempt_success_criterion_fulfilled=False,
                       final_ports=final_ports, pg_status_exit=pg_status,
                       runs=sorted(p.name for p in (runner.WRITABLE_DEMO_ROOT / "runs").iterdir()),
                       actual_boundary_receipts=receipts, historical_databases_unchanged=history)
        write(output / "adapter-result.json", outcome)
    assert "unexpected_exception" not in outcome, outcome.get("unexpected_exception")
    assert outcome["final_ports"] == {str(p): [] for p in runner.REVIEWER_PORTS}
    assert outcome["pg_status_exit"] == 3 and outcome["runs"] == []
    returned = json.loads((output / "cpu-resource-return.json").read_text())
    assert returned["lease_id"] == "CPU-INTEGRATION-NOT-A-LEASE" and returned["clean_return_verified"] is True
    assert all(v == 0 for v in returned["persisted_counts"].values())
    assert len([r for r in receipts if r["kind"] == "actual_q0"]) == 2
    if deliberate:
        assert "expected_deliberate_exception" in outcome and not (output / "cpu-main-summary.json").exists()
    else:
        assert outcome["main_exit"] == 0 and stage == 2
    return outcome


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("controls", "lifecycle"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    source_check()
    record = dict(started_utc=utc(), source=SOURCE, executing_head=git("rev-parse", "HEAD").decode().strip(),
                  mode=args.mode, command=sys.argv, runtime_authorization=False,
                  source_files={p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in (Path(__file__).resolve(), Path(runner.__file__), Path(ownership_v6.__file__), Path(prep.__file__), PREP_PATH / "drive_wp0012_edge_workflow.mjs")})
    exitcode = 0
    try:
        if args.mode == "controls":
            pure_controls(args.output_dir)
        else:
            dependencies(args.output_dir)
            lifecycle(args.output_dir / "complete-cpu-lifecycle", False)
            lifecycle(args.output_dir / "deliberate-boundary-failure", True)
    except BaseException as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        exitcode = 1
    record.update(finished_utc=utc(), exit_code=exitcode)
    write(args.output_dir / "result.json", record)
    print(json.dumps({k:record[k] for k in ("source", "executing_head", "mode", "started_utc", "finished_utc", "exit_code")}))
    return exitcode


if __name__ == "__main__":
    raise SystemExit(main())
