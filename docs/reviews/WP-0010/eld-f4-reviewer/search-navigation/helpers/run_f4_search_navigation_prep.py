"""Frozen independent WP-0010 / 007 search-navigation preparation & deterministic reproduction runner.

Executes strictly on owned reviewer loopback resources (`127.0.0.1:5690` API, `127.0.0.1:4710` UI,
`127.0.0.1:55439` PostgreSQL `18.7`, retained `eledgercare_f4_reviewer_migrated` + untouched
`eledgercare_f4_reviewer_seed_f3`) with `LocalOcr:Enabled=false`, zero GPU/model/subagent calls,
zero production edits, and zero arbitrary timer sleeps in the browser ownership probe.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import time

API_PORT = 5690
UI_PORT = 4710
PG_PORT = 55439
REVIEWER_PORTS = (API_PORT, UI_PORT, PG_PORT)

SEED_DB = "eledgercare_f4_reviewer_seed_f3"
MIGRATED_DB = "eledgercare_f4_reviewer_migrated"

EXPECTED_SEED_8TABLE_SHA256 = "841a3c0a2fc6ff5bbf29d6da1feff35b53c0c35be33a89a9ea03cfe2c1a2c993"
EXPECTED_PROJECTIONS_SHA256 = "0faf93dc12d8596df7435628ac3b797b8a703c8f0cd68614e11b9d8bb39c63fa"

PRIOR_002_SHA = "85d879a1adc0ee62090f4c6a5c9a7fb8eb5f3a96"
PRIOR_PREP_SHA = "349c29773009abdf1bc228d01696d58a83d3eaa2"
PRIOR_004_SHA = "324f09934b0aa2ee8e7bed7e8118c6109effb918"
ROOT_CORRECTION_AUTHORITY_SHA = "6daa37223b81335c686e7afae8fc376d2f8abfeb"
MERGED_PREP_BASE_SHA = "e59232e0f1466b8d56dfe062994c112a632f8769"
AUTHOR_C383_SHA = "c383021be1774451ba3034d89255b38b4267353b"

EXPECTED_C383_TREES = {
    "src": "9760402fa88dcb343c28b14ad4de1bcb2fbafb2e",
    "web": "2aeddf8ec2e1f3d4e3dc40517866d975efadcd3e",
    "tests": "25c21310699086acb818549b2a4c0b99469208f1",
    "deploy": "86e0c73d4b4c07bbdf92ebcd65a0903fc9c039f1",
    "ELedgerCare.slnx": "c00c2bc5ef46019fb4452fdf0bba7ca2271fc976",
    "workers": "9b548ddcc73cfba8e7683d132840b08afa5a67a3",
}


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def redact_secrets(text: str, secrets: list[str]) -> str:
    out = text
    for s in secrets:
        if s:
            out = out.replace(s, "[REDACTED-LOCAL-SECRET]")
    return out


def assert_no_secrets(text: str, secrets: list[str], label: str) -> None:
    for s in secrets:
        if s and s in text:
            raise AssertionError(f"Secret value leaked into {label}!")


def run_cmd(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    timeout_s: int = 300,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        env=env,
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )


def run_git(repo_root: Path, *args: str) -> str:
    cp = run_cmd(["git", *args], cwd=repo_root)
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr}")
    return cp.stdout.rstrip("\r\n")


def observe_ports(ports: tuple[int, ...], cwd: Path) -> dict[str, list[dict]]:
    ps_script = (
        "$out = @{}; "
        f"foreach ($p in @({','.join(str(p) for p in ports)})) {{ "
        "$conns = @(Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue | "
        "ForEach-Object { @{ localAddress = $_.LocalAddress; localPort = [int]$_.LocalPort; owningPid = [int]$_.OwningProcess } }); "
        "$out[\"$p\"] = $conns "
        "}; "
        "$out | ConvertTo-Json -Compress -Depth 4"
    )
    cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps_script], cwd=cwd)
    if cp.returncode != 0:
        raise RuntimeError(f"Port observation failed: {cp.stderr}")
    return json.loads(cp.stdout)


def inspect_process(pid: int, cwd: Path) -> dict | None:
    ps_script = (
        f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
        "if ($null -eq $p) { 'null' } else { "
        "@{ pid = [int]$p.Id; name = [string]$p.ProcessName; "
        "startUtc = $p.StartTime.ToUniversalTime().ToString('o'); "
        "workingSetBytes = [int64]$p.WorkingSet64 } | ConvertTo-Json -Compress }"
    )
    cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps_script], cwd=cwd)
    if cp.returncode != 0 or cp.stdout.strip() == "null":
        return None
    return json.loads(cp.stdout)


def stop_owned_process(proc: subprocess.Popen[bytes] | None, recorded_info: dict | None, cwd: Path) -> dict | None:
    if proc is None or recorded_info is None:
        return None
    pid = int(recorded_info["pid"])
    expected_start = recorded_info["startUtc"]
    if proc.poll() is not None:
        return {
            "pid": pid,
            "name": recorded_info["name"],
            "startUtc": expected_start,
            "alreadyExitedCode": proc.returncode,
            "aliveAfter": False,
        }
    cur = inspect_process(pid, cwd)
    if cur is None:
        return {"pid": pid, "name": recorded_info["name"], "startUtc": expected_start, "aliveAfter": False}
    if cur["startUtc"] != expected_start:
        raise RuntimeError(f"Refusing to terminate PID {pid}: startUtc changed ({cur['startUtc']} != {expected_start})")
    proc.kill()
    proc.wait(timeout=30)
    after = inspect_process(pid, cwd)
    return {
        "pid": pid,
        "name": recorded_info["name"],
        "startUtc": expected_start,
        "exitCode": proc.returncode,
        "aliveAfter": after is not None,
    }


def invoke_psql(
    psql_exe: Path,
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
    sql: str,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PGPASSWORD"] = password
    args = [
        str(psql_exe),
        "-X",
        "-q",
        "-v",
        "ON_ERROR_STOP=1",
        "-h",
        host,
        "-p",
        str(port),
        "-U",
        user,
        "-d",
        database,
        "-A",
        "-t",
        "-f",
        "-",
    ]
    cp = run_cmd(args, cwd=cwd, env=env, input_text=sql, timeout_s=120)
    if cp.returncode != 0:
        raise RuntimeError(f"psql failed as {user} on {database} (exit {cp.returncode}): {cp.stderr}")
    return cp


def compute_8table_sha256(psql_exe: Path, settings: dict, database: str, cwd: Path) -> str:
    sql = """
SELECT json_build_object(
  'fencing_seq', (SELECT json_build_object('last_value', last_value, 'is_called', is_called) FROM eledgercare.extraction_fencing_seq),
  'documents', COALESCE((
    SELECT json_agg(row_to_json(t) ORDER BY t.document_id) FROM (
      SELECT document_id::text, idempotency_key::text, to_char(submitted_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS submitted_at_utc
      FROM eledgercare.documents
    ) t
  ), '[]'::json),
  'original_artifacts', COALESCE((
    SELECT json_agg(row_to_json(t) ORDER BY t.document_id) FROM (
      SELECT document_id::text, byte_length, media_type, page_count,
             encode(sha256, 'hex') AS sha256_hex,
             encode(sha256(bytes), 'hex') AS computed_bytes_sha256_hex
      FROM eledgercare.original_artifacts
    ) t
  ), '[]'::json),
  'processing_jobs', COALESCE((
    SELECT json_agg(row_to_json(t) ORDER BY t.job_id) FROM (
      SELECT job_id::text, document_id::text, status, attempt_count, latest_fencing_token,
             retried_from_attempt_id::text,
             to_char(requested_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS requested_at_utc,
             CASE WHEN queued_at IS NULL THEN NULL ELSE to_char(queued_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') END AS queued_at_utc,
             to_char(updated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS updated_at_utc
      FROM eledgercare.processing_jobs
    ) t
  ), '[]'::json),
  'execution_attempts', COALESCE((
    SELECT json_agg(row_to_json(t) ORDER BY t.attempt_id) FROM (
      SELECT attempt_id::text, job_id::text, document_id::text, attempt_number, fencing_token,
             retried_from_attempt_id::text, status, phase, run_directory_name,
             supervisor_instance_id::text, supervisor_pid, supervisor_create_filetime,
             launcher_pid, launcher_create_filetime, worker_pid, worker_create_filetime,
             exit_code, failure_code, failure_detail, diagnostic_raw_output_utf8,
             diagnostic_metadata_json::text AS diagnostic_metadata_json,
             to_char(started_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS started_at_utc,
             CASE WHEN ended_at IS NULL THEN NULL ELSE to_char(ended_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') END AS ended_at_utc
      FROM eledgercare.execution_attempts
    ) t
  ), '[]'::json),
  'extraction_results', COALESCE((
    SELECT json_agg(row_to_json(t) ORDER BY t.result_id) FROM (
      SELECT result_id::text, document_id::text, job_id::text, attempt_id::text, fencing_token, schema_version,
             encode(input_sha256, 'hex') AS input_sha256_hex, input_byte_length, page_count,
             raw_output_byte_length, encode(raw_output_sha256, 'hex') AS raw_output_sha256_hex,
             encode(sha256(raw_output_bytes), 'hex') AS computed_raw_sha256_hex,
             model_repo_id, model_revision,
             encode(model_manifest_sha256, 'hex') AS model_manifest_sha256_hex,
             encode(dependency_lock_sha256, 'hex') AS dependency_lock_sha256_hex,
             encode(worker_source_digest, 'hex') AS worker_source_sha256_hex,
             encode(worker_config_digest, 'hex') AS worker_config_sha256_hex,
             renderer_identity, finish_reason, output_page_count,
             load_duration_ms, render_duration_ms, infer_duration_ms, total_duration_ms
      FROM eledgercare.extraction_results
    ) t
  ), '[]'::json),
  'work_order_review_heads', COALESCE((
    SELECT json_agg(row_to_json(t) ORDER BY t.document_id) FROM (
      SELECT document_id::text, result_id::text,
             encode(input_sha256, 'hex') AS input_sha256_hex,
             encode(raw_output_sha256, 'hex') AS raw_output_sha256_hex,
             profile_id, field_schema_version, suggestion_policy_version,
             current_revision_number, current_revision_id::text, current_status,
             machine_snapshot_json::text AS machine_snapshot_json
      FROM eledgercare.work_order_review_heads
    ) t
  ), '[]'::json),
  'work_order_review_revisions', COALESCE((
    SELECT json_agg(row_to_json(t) ORDER BY t.revision_id) FROM (
      SELECT revision_id::text, document_id::text, result_id::text, revision_number, previous_revision_number,
             status, idempotency_key::text,
             encode(request_sha256, 'hex') AS request_sha256_hex,
             encode(input_sha256, 'hex') AS input_sha256_hex,
             encode(raw_output_sha256, 'hex') AS raw_output_sha256_hex,
             profile_id, field_schema_version, suggestion_policy_version, operator_display_label,
             accepted_field_count, edited_field_count, unknown_field_count, unreviewed_field_count,
             to_char(saved_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS saved_at_utc
      FROM eledgercare.work_order_review_revisions
    ) t
  ), '[]'::json),
  'work_order_review_fields', COALESCE((
    SELECT json_agg(row_to_json(t) ORDER BY t.revision_id, t.field_ordinal) FROM (
      SELECT revision_id::text, field_ordinal, field_key, decision, human_value, unknown_reason,
             consulted_page_number, consulted_block_ordinal, consulted_table_row, consulted_table_column, consulted_quote
      FROM eledgercare.work_order_review_fields
    ) t
  ), '[]'::json)
)::text;
"""
    cp = invoke_psql(
        psql_exe,
        host=settings["host"],
        port=int(settings["port"]),
        user=settings["appUser"],
        password=settings["appPassword"],
        database=database,
        sql=sql,
        cwd=cwd,
    )
    parsed = json.loads(cp.stdout.strip())
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_hex(canonical)


def compute_projections_sha256(psql_exe: Path, settings: dict, database: str, cwd: Path) -> str:
    sql = """
SELECT json_build_object(
  'projections', COALESCE((
    SELECT json_agg(row_to_json(t) ORDER BY t.result_id, t.projection_version) FROM (
      SELECT result_id::text, projection_version, document_id::text,
             encode(raw_output_sha256, 'hex') AS raw_output_sha256_hex,
             encode(projection_sha256, 'hex') AS projection_sha256_hex,
             unit_count, has_fallback
      FROM eledgercare.archive_result_projections
    ) t
  ), '[]'::json),
  'units', COALESCE((
    SELECT json_agg(row_to_json(t) ORDER BY t.result_id, t.projection_version, t.unit_ordinal) FROM (
      SELECT result_id::text, projection_version, unit_ordinal, document_id::text,
             page_number, unit_kind, is_fallback,
             char_length(search_text) AS char_len,
             encode(sha256(convert_to(search_text, 'UTF8')), 'hex') AS text_sha256_hex
      FROM eledgercare.archive_projection_units
    ) t
  ), '[]'::json)
)::text;
"""
    cp = invoke_psql(
        psql_exe,
        host=settings["host"],
        port=int(settings["port"]),
        user=settings["appUser"],
        password=settings["appPassword"],
        database=database,
        sql=sql,
        cwd=cwd,
    )
    parsed = json.loads(cp.stdout.strip())
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_hex(canonical)


def http_status(port: int, path_str: str) -> int:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request("GET", path_str)
        resp = conn.getresponse()
        resp.read()
        return resp.status
    finally:
        conn.close()


def start_owned_api(api_dll: Path, port: int, settings: dict, database: str, log_path: Path, cwd: Path) -> tuple[subprocess.Popen[bytes], dict]:
    ports_now = observe_ports((port,), cwd)
    if ports_now[str(port)]:
        raise RuntimeError(f"Port {port} already bound: {ports_now}")
    api_env = dict(os.environ)
    api_env["ASPNETCORE_ENVIRONMENT"] = "Production"
    api_env["DOTNET_NOLOGO"] = "1"
    api_env["Api__Port"] = str(port)
    api_env["LocalOcr__Enabled"] = "false"
    api_env["ConnectionStrings__Runtime"] = (
        f"Host={settings['host']};Port={settings['port']};Database={database};"
        f"Username={settings['appUser']};Password={settings['appPassword']}"
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("wb") as fh:
        proc = subprocess.Popen(
            ["dotnet", str(api_dll)],
            cwd=str(api_dll.parent),
            env=api_env,
            stdout=fh,
            stderr=subprocess.STDOUT,
        )
    info = inspect_process(proc.pid, cwd)
    deadline = time.monotonic() + 60.0
    ready = False
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"ELedgerCare.Api exited early with code {proc.returncode}")
        try:
            if http_status(port, "/api/documents/00000000-0000-7000-8000-999999999999") == 404:
                ready = True
                break
        except OSError:
            time.sleep(0.2)
    if not ready or info is None:
        stop_owned_process(proc, info, cwd)
        raise RuntimeError(f"ELedgerCare.Api failed to listen on 127.0.0.1:{port}")
    return proc, info


def start_owned_ui(node_exe: Path, ui_port: int, api_port: int, log_path: Path, repo_root: Path) -> tuple[subprocess.Popen[bytes], dict]:
    ports_now = observe_ports((ui_port,), repo_root)
    if ports_now[str(ui_port)]:
        raise RuntimeError(f"Port {ui_port} already bound: {ports_now}")
    ui_env = dict(os.environ)
    ui_env["ELEDGERCARE_API_PORT"] = str(api_port)
    ui_env["NG_CLI_ANALYTICS"] = "false"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("wb") as fh:
        proc = subprocess.Popen(
            [
                str(node_exe),
                "node_modules/@angular/cli/bin/ng.js",
                "serve",
                "--host",
                "127.0.0.1",
                "--port",
                str(ui_port),
                "--proxy-config",
                "proxy.conf.mjs",
            ],
            cwd=str(repo_root / "web"),
            env=ui_env,
            stdout=fh,
            stderr=subprocess.STDOUT,
        )
    info = inspect_process(proc.pid, repo_root)
    deadline = time.monotonic() + 90.0
    ready = False
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Angular dev server exited early with code {proc.returncode}")
        try:
            if http_status(ui_port, "/archive") == 200:
                ready = True
                break
        except OSError:
            time.sleep(0.25)
    if not ready or info is None:
        stop_owned_process(proc, info, repo_root)
        raise RuntimeError(f"Angular dev server failed to listen on 127.0.0.1:{ui_port}")
    return proc, info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WP-0010 / 007 search-navigation preparation & reproduction runner.")
    parser.add_argument(
        "--expect",
        choices=("unchanged-c383-reproduction", "ownership-pass"),
        default="unchanged-c383-reproduction",
        help="Expected outcome of the enforce-ownership Edge probe",
    )
    parser.add_argument("--output", required=True, help="Output JSON preparation summary path")
    parser.add_argument("--probe-output", required=True, help="Output JSON Edge probe receipt path")
    parser.add_argument("--resource-return-output", required=True, help="Output JSON resource-return receipt path")
    parser.add_argument("--logs-dir", required=True, help="Directory for sanitized execution logs")
    parser.add_argument("--screenshots-dir", required=True, help="Directory for Edge PNG screenshots")
    parser.add_argument("--require-clean", action="store_true", help="Require clean worktree before running")
    args = parser.parse_args(argv)

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[6]
    logs_dir = (repo_root / args.logs_dir).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)

    assertions: list[dict] = []
    step_receipts: list[dict] = []

    def record_assert(name: str, passed: bool, detail: dict) -> None:
        assertions.append({"check": name, "passed": bool(passed), "detail": detail})
        if not passed:
            raise AssertionError(f"Assertion failed [{name}]: {json.dumps(detail)}")

    if args.require_clean:
        wt = run_git(repo_root, "status", "--porcelain", "--untracked-files=all")
        record_assert("clean_worktree_before_decisive_run", wt == "", {"status": wt})

    branch = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    head_sha = run_git(repo_root, "rev-parse", "HEAD")
    record_assert("owned_review_branch", branch == "review/wp-0010-f4", {"branch": branch, "head": head_sha})

    for label, anc in (
        ("prior_002", PRIOR_002_SHA),
        ("prior_prep", PRIOR_PREP_SHA),
        ("prior_004", PRIOR_004_SHA),
        ("root_correction_authority", ROOT_CORRECTION_AUTHORITY_SHA),
        ("merged_prep_base", MERGED_PREP_BASE_SHA),
    ):
        ok = run_cmd(["git", "merge-base", "--is-ancestor", anc, head_sha], cwd=repo_root).returncode == 0
        record_assert(f"ancestor_verified:{label}", ok, {"sha": anc})

    if args.expect == "unchanged-c383-reproduction":
        for rel, exp_oid in EXPECTED_C383_TREES.items():
            actual_oid = run_git(repo_root, "rev-parse", f"HEAD:{rel}")
            record_assert(f"unchanged_c383_tree:{rel}", actual_oid == exp_oid, {"oid": actual_oid})

    prior_reviewer_diff = run_git(
        repo_root,
        "diff",
        "--name-only",
        PRIOR_004_SHA,
        head_sha,
        "--",
        "docs/reviews/WP-0010/eld-f4-reviewer/design",
        "docs/reviews/WP-0010/eld-f4-reviewer/preparation",
        "docs/reviews/WP-0010/eld-f4-reviewer/runtime",
        "docs/agent-reports/eld-f4-reviewer/WP-0010/002_2026-11-17_review_eld-f4-reviewer.md",
        "docs/agent-reports/eld-f4-reviewer/WP-0010/004_2026-11-17_review_eld-f4-reviewer.md",
    )
    record_assert("immutable_002_prep_runtime_and_004_untouched", prior_reviewer_diff == "", {"diff": prior_reviewer_diff})

    canonical_007_path = repo_root / "docs/agent-reports/eld-f4-reviewer/WP-0010/007_2026-11-17_review_eld-f4-reviewer.md"
    record_assert("canonical_007_held_until_author_006_binding", not canonical_007_path.exists(), {})

    probe_mjs = script_path.parent / "probe_f4_search_navigation.mjs"
    probe_text_no_comments = "\n".join(
        ln for ln in probe_mjs.read_text(encoding="utf-8").splitlines() if not ln.strip().startswith(("//", "*", "/*"))
    )
    record_assert(
        "probe_uses_zero_arbitrary_timer_sleeps",
        "waitForTimeout" not in probe_text_no_comments and "setTimeout" not in probe_text_no_comments,
        {"probe": probe_mjs.relative_to(repo_root).as_posix()},
    )

    pg_settings_path = repo_root / ".local/secrets/pg-local.json"
    settings = json.loads(pg_settings_path.read_text(encoding="utf-8"))
    secrets = [str(settings["adminPassword"]), str(settings["migratorPassword"]), str(settings["appPassword"])]

    psql_exe = repo_root / ".local/tools/pgsql-18.7-1/bin/psql.exe"
    pg_ctl_exe = repo_root / ".local/tools/pgsql-18.7-1/bin/pg_ctl.exe"
    pg_data_dir = repo_root / ".local/postgres-data"
    api_dll = repo_root / "src/ELedgerCare.Api/bin/Release/net10.0/ELedgerCare.Api.dll"
    node_cp = run_cmd(["pwsh", "-NoProfile", "-Command", "(Get-Command node).Source"], cwd=repo_root)
    node_exe = Path(node_cp.stdout.strip())

    ports_before = observe_ports(REVIEWER_PORTS, repo_root)
    record_assert(
        "reviewer_ports_5690_4710_55439_free_before_start",
        all(len(ports_before[str(p)]) == 0 for p in REVIEWER_PORTS),
        ports_before,
    )

    def run_logged_step(step_id: str, argv: list[str], *, allow_nonzero: bool = False) -> subprocess.CompletedProcess[str]:
        t0 = time.monotonic()
        started_utc = datetime.now(timezone.utc).isoformat()
        cp = run_cmd(argv, cwd=repo_root, timeout_s=240)
        elapsed_ms = round((time.monotonic() - t0) * 1000.0, 1)
        combined = redact_secrets((cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else ""), secrets).replace("\r\n", "\n")
        lf = logs_dir / f"{step_id}.log"
        lf.write_text(combined, encoding="utf-8", newline="\n")
        step_receipts.append({
            "step": step_id,
            "command": [redact_secrets(a, secrets) for a in argv],
            "started_utc": started_utc,
            "elapsed_ms": elapsed_ms,
            "exit_code": cp.returncode,
            "log_relpath": lf.relative_to(repo_root).as_posix(),
            "log_sha256": sha256_hex(lf.read_bytes()),
        })
        if cp.returncode != 0 and not allow_nonzero:
            raise RuntimeError(f"Step {step_id} failed (exit {cp.returncode}); see {lf}")
        return cp

    spawned_processes: list[dict] = []
    active_api_proc: subprocess.Popen[bytes] | None = None
    active_api_info: dict | None = None
    active_ui_proc: subprocess.Popen[bytes] | None = None
    active_ui_info: dict | None = None

    try:
        if not api_dll.exists():
            run_logged_step("00-dotnet-build-release", ["dotnet", "build", "ELedgerCare.slnx", "-c", "Release", "--no-restore"])

        run_logged_step("01-pg-cluster-start", ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"])
        pm_pid = int((pg_data_dir / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        spawned_processes.append({"role": "postmaster_55439", "info": inspect_process(pm_pid, repo_root)})

        seed_before = compute_8table_sha256(psql_exe, settings, SEED_DB, repo_root)
        mig_8_before = compute_8table_sha256(psql_exe, settings, MIGRATED_DB, repo_root)
        mig_proj_before = compute_projections_sha256(psql_exe, settings, MIGRATED_DB, repo_root)
        record_assert(
            "retained_seed_and_migrated_digests_intact_before_probe",
            (
                seed_before == EXPECTED_SEED_8TABLE_SHA256
                and mig_8_before == EXPECTED_SEED_8TABLE_SHA256
                and mig_proj_before == EXPECTED_PROJECTIONS_SHA256
            ),
            {"seed_before": seed_before, "mig_8_before": mig_8_before, "mig_proj_before": mig_proj_before},
        )

        active_api_proc, active_api_info = start_owned_api(
            api_dll, API_PORT, settings, MIGRATED_DB, logs_dir / "owned-api-5690.log", repo_root
        )
        active_ui_proc, active_ui_info = start_owned_ui(
            node_exe, UI_PORT, API_PORT, logs_dir / "owned-ui-4710.log", repo_root
        )

        tag = "c383-repro" if args.expect == "unchanged-c383-reproduction" else "candidate-verify"
        probe_cp = run_logged_step(
            "02-edge-ownership-probe",
            [
                str(node_exe),
                str(probe_mjs),
                "--mode",
                "enforce-ownership",
                "--tag",
                tag,
                "--ui-port",
                str(UI_PORT),
                "--api-port",
                str(API_PORT),
                "--output",
                args.probe_output,
                "--screenshot-dir",
                args.screenshots_dir,
            ],
            allow_nonzero=(args.expect == "unchanged-c383-reproduction"),
        )

        ui_stop = stop_owned_process(active_ui_proc, active_ui_info, repo_root)
        api_stop = stop_owned_process(active_api_proc, active_api_info, repo_root)
        spawned_processes.append({"role": "ui_4710", "stop": ui_stop})
        spawned_processes.append({"role": "api_5690", "stop": api_stop})
        active_ui_proc, active_ui_info = None, None
        active_api_proc, active_api_info = None, None

        seed_after = compute_8table_sha256(psql_exe, settings, SEED_DB, repo_root)
        mig_8_after = compute_8table_sha256(psql_exe, settings, MIGRATED_DB, repo_root)
        mig_proj_after = compute_projections_sha256(psql_exe, settings, MIGRATED_DB, repo_root)
        record_assert(
            "retained_seed_and_migrated_digests_unchanged_after_probe",
            (
                seed_after == EXPECTED_SEED_8TABLE_SHA256
                and mig_8_after == EXPECTED_SEED_8TABLE_SHA256
                and mig_proj_after == EXPECTED_PROJECTIONS_SHA256
            ),
            {"seed_after": seed_after, "mig_8_after": mig_8_after, "mig_proj_after": mig_proj_after},
        )

        run_logged_step("03-pg-cluster-stop", ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"])
    finally:
        if active_ui_proc is not None:
            stop_owned_process(active_ui_proc, active_ui_info, repo_root)
        if active_api_proc is not None:
            stop_owned_process(active_api_proc, active_api_info, repo_root)
        if (pg_data_dir / "postmaster.pid").exists():
            run_cmd(["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"], cwd=repo_root)
        for lf in logs_dir.glob("*.log"):
            cleaned = redact_secrets(lf.read_text(encoding="utf-8", errors="replace"), secrets)
            lf.write_text(cleaned.replace("\r\n", "\n"), encoding="utf-8", newline="\n")

    probe_receipt = json.loads((repo_root / args.probe_output).read_text(encoding="utf-8"))
    if args.expect == "unchanged-c383-reproduction":
        record_assert(
            "unchanged_c383_deterministically_reproduces_pending_navigation_ownership_failures",
            (
                probe_cp.returncode == 1
                and "SN-01A" in probe_receipt["failed_scenario_ids"]
                and "SN-01B" in probe_receipt["failed_scenario_ids"]
                and "SN-02A" in probe_receipt["failed_scenario_ids"]
                and "SN-03" in probe_receipt["failed_scenario_ids"]
                and "SN-04" in probe_receipt["passed_scenario_ids"]
                and probe_receipt["observed_non_get_api_count"] == 0
                and probe_receipt["local_storage_keys"] == 0
                and probe_receipt["session_storage_keys"] == 0
            ),
            {
                "probe_exit_code": probe_cp.returncode,
                "passed": probe_receipt["passed_scenario_ids"],
                "failed": probe_receipt["failed_scenario_ids"],
            },
        )
    else:
        record_assert(
            "candidate_passes_all_6_search_navigation_ownership_scenarios",
            probe_cp.returncode == 0 and probe_receipt["all_ownership_passed"] is True,
            {
                "probe_exit_code": probe_cp.returncode,
                "passed": probe_receipt["passed_scenario_ids"],
                "failed": probe_receipt["failed_scenario_ids"],
            },
        )

    pg_status_cp = run_cmd([str(pg_ctl_exe), "status", "-D", str(pg_data_dir)], cwd=repo_root)
    ports_after = observe_ports(REVIEWER_PORTS, repo_root)
    record_assert(
        "all_owned_services_stopped_and_ports_5690_4710_55439_released",
        (
            pg_status_cp.returncode == 3
            and all(len(ports_after[str(p)]) == 0 for p in REVIEWER_PORTS)
            and (pg_data_dir / "PG_VERSION").exists()
        ),
        {"pg_ctl_status_exit": pg_status_cp.returncode, "ports_after": ports_after},
    )

    inv_script = script_path.parent / "build_search_navigation_inventory.py"
    summary_payload = {
        "schema": "eledgercare.wp-0010.reviewer-search-navigation-prep-summary/1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "conversation_id": "61105d43-7706-45f2-9176-69d3256248e0",
        "branch": branch,
        "executing_head_sha": head_sha,
        "tested_product_source_sha": AUTHOR_C383_SHA if args.expect == "unchanged-c383-reproduction" else head_sha,
        "prior_004_publication_sha": PRIOR_004_SHA,
        "root_correction_authority_sha": ROOT_CORRECTION_AUTHORITY_SHA,
        "merged_prep_base_sha": MERGED_PREP_BASE_SHA,
        "expect_mode": args.expect,
        "helpers": {
            "run_f4_search_navigation_prep_py_sha256": sha256_hex(script_path.read_bytes().replace(b"\r\n", b"\n")),
            "probe_f4_search_navigation_mjs_sha256": sha256_hex(probe_mjs.read_bytes().replace(b"\r\n", b"\n")),
            "build_search_navigation_inventory_py_sha256": sha256_hex(inv_script.read_bytes().replace(b"\r\n", b"\n")),
        },
        "probe_outcome": {
            "probe_exit_code": probe_cp.returncode,
            "arbitrary_sleep_calls": probe_receipt["arbitrary_sleep_calls"],
            "browser_version": probe_receipt["browser_version"],
            "passed_scenario_ids": probe_receipt["passed_scenario_ids"],
            "failed_scenario_ids": probe_receipt["failed_scenario_ids"],
        },
        "retained_databases_verified_unchanged": {
            "seed_f3_8table_sha256": seed_after,
            "migrated_8table_sha256": mig_8_after,
            "migrated_projections_sha256": mig_proj_after,
        },
        "logged_steps": step_receipts,
        "assertion_count": len(assertions),
        "all_assertions_passed": True,
        "assertions": assertions,
        "canonical_007_published": False,
        "zero_gpu_or_subagent_calls": True,
    }

    resource_return = {
        "schema": "eledgercare.wp-0010.reviewer-search-navigation-resource-return/1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "owned_ports": {"api": API_PORT, "ui": UI_PORT, "postgres": PG_PORT},
        "ports_before": ports_before,
        "ports_after": ports_after,
        "pg_ctl_status_exit_after_stop": pg_status_cp.returncode,
        "spawned_processes": spawned_processes,
        "retained_databases": {
            SEED_DB: seed_after,
            MIGRATED_DB: {"core_8table_sha256": mig_8_after, "projections_sha256": mig_proj_after},
        },
        "credentials_gitignored": True,
        "gpu_or_model_processes_started": 0,
    }

    out_summary = (repo_root / args.output).resolve()
    out_return = (repo_root / args.resource_return_output).resolve()
    out_summary.parent.mkdir(parents=True, exist_ok=True)
    out_return.parent.mkdir(parents=True, exist_ok=True)

    summary_str = json.dumps(summary_payload, indent=2, ensure_ascii=False) + "\n"
    return_str = json.dumps(resource_return, indent=2, ensure_ascii=False) + "\n"
    assert_no_secrets(summary_str, secrets, str(out_summary))
    assert_no_secrets(return_str, secrets, str(out_return))
    for log_f in logs_dir.glob("*.log"):
        assert_no_secrets(log_f.read_text(encoding="utf-8"), secrets, str(log_f))

    out_summary.write_text(summary_str, encoding="utf-8", newline="\n")
    out_return.write_text(return_str, encoding="utf-8", newline="\n")

    print(
        f"PASS [{args.expect}]: {len(assertions)} assertions verified; "
        f"probe exit={probe_cp.returncode} (passed={probe_receipt['passed_scenario_ids']}, "
        f"failed={probe_receipt['failed_scenario_ids']}); ports {REVIEWER_PORTS} FREE."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
