"""Frozen independent F4 source & live runtime verification runner (`WP-0010 / 004`, `eld-f4-reviewer`).

Executes strictly on owned reviewer loopback resources (`127.0.0.1:5690` API, `127.0.0.1:4710` UI,
`127.0.0.1:55439` PostgreSQL `18.7`) with `LocalOcr:Enabled=false` and zero GPU/model/subagent calls:
  1. Static, Git-tree, author-diff, dependency-pin, and XSS/import boundary audit against frozen
     author candidate `c383021be1774451ba3034d89255b38b4267353b` and design `01a6dab0695c93246b4cf04d1a2098d3b77248d8`.
  2. Worker CPU unit suite (`9/9`), offline locked `.NET` Release build (`0` warnings/errors),
     and Angular `22.2.7` production bundle build (`0` errors).
  3. Owned PostgreSQL `18.7` (`55439`) startup and preservation check of independently constructed
     pre-F4 F3 seed database `eledgercare_f4_reviewer_seed_f3` (`841a3c0a...`).
  4. Full `.NET` test suite (`95/95`: Domain + Infrastructure + PostgreSQL Acceptance), `5690` demo
     restart smoke, and `15/15` Playwright Microsoft Edge E2E specs on `5690 / 4710 / 55439`.
  5. Forward migration of cloned `eledgercare_f4_reviewer_migrated` (`TEMPLATE eledgercare_f4_reviewer_seed_f3`)
     via `prepare-database.ps1` while preserving `eledgercare_f4_reviewer_seed_f3` untouched.
  6. Live HTTP `503 archive_not_ready` check (`Archive__DeferStartupInitialization=true`), followed by
     normal `LocalOcr:Enabled=false` startup backfill (`7` projections / `13` units), `30` saved canonical
     archive queries (browse, filters, keyset microsecond tie-break, `C`-locale metacharacters/emojis,
     mixed-source AND, superseded/unknown/draft/diagnostic exclusions), `18` raw HTTP socket `400` rejections,
     `19` PostgreSQL `42501` least-privilege denials, and `EXPLAIN (ANALYZE, BUFFERS)` + warm latency/working-set.
  7. Before-restart Microsoft Edge runtime verification (`4710 -> 5690`), real stop + fast restart of
     PostgreSQL `55439`, API `5690`, and UI `4710`, and after-restart Microsoft Edge + saved-query +
     8-table/projection digest invariance verification (`0` new extraction attempts).
  8. Isolated scratch-DB live HTTP verification of malformed-table (`<caption>`), missing-`<FORK>`, `\0 -> U+FFFD`
     without truncation, unbound-`<PAGE>` document fallback (`pageNumber=null`), and `503 archive_projection_conflict`.
  9. Clean termination of all owned services (`5690 / 4710 / 55439` `0` listeners, `pg_ctl status` exit `3`),
     retaining `eledgercare_f4_reviewer_seed_f3` and `eledgercare_f4_reviewer_migrated` on disk.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
import urllib.parse

API_PORT = 5690
UI_PORT = 4710
PG_PORT = 55439
REVIEWER_PORTS = (API_PORT, UI_PORT, PG_PORT)

SEED_DB = "eledgercare_f4_reviewer_seed_f3"
MIGRATED_DB = "eledgercare_f4_reviewer_migrated"
E2E_DB = "eledgercare_f4_reviewer_e2e"
PROBE_DB = "eledgercare_f4_reviewer_probe"

EXPECTED_REVIEWER_SEED_8TABLE_SHA256 = "841a3c0a2fc6ff5bbf29d6da1feff35b53c0c35be33a89a9ea03cfe2c1a2c993"

DESIGN_CANDIDATE_SHA = "01a6dab0695c93246b4cf04d1a2098d3b77248d8"
PRIOR_DESIGN_002_SHA = "85d879a1adc0ee62090f4c6a5c9a7fb8eb5f3a96"
REVIEWER_PREP_SHA = "349c29773009abdf1bc228d01696d58a83d3eaa2"
ROOT_RUNTIME_AUTHORITY_SHA = "d8e4c9b86af5e61157bf55675037c6ddd95efeff"
AUTHOR_BASE_SHA = "7345ef03dfa4d5f039259d0b8b9505685112469d"
AUTHOR_FIRST_FROZEN_SHA = "74555395e8ed55020ffd004369b30581bfa7963c"
AUTHOR_CANDIDATE_SHA = "c383021be1774451ba3034d89255b38b4267353b"
AUTHOR_EVIDENCE_SHA = "ceec957733d6c00c6b4277e7db3f391ab6ccb6b4"
AUTHOR_003_PUB_SHA = "7c578be6e8abff4d285ea1b519bbcfaeba1bb8c7"
MERGED_REVIEW_BASE_SHA = "8f2932c00fa01b46a8262fe7965d953cc966146e"

EXPECTED_PRODUCT_TREES = {
    "src": "9760402fa88dcb343c28b14ad4de1bcb2fbafb2e",
    "web": "2aeddf8ec2e1f3d4e3dc40517866d975efadcd3e",
    "tests": "25c21310699086acb818549b2a4c0b99469208f1",
    "deploy": "86e0c73d4b4c07bbdf92ebcd65a0903fc9c039f1",
    "ELedgerCare.slnx": "c00c2bc5ef46019fb4452fdf0bba7ca2271fc976",
    "workers": "9b548ddcc73cfba8e7683d132840b08afa5a67a3",
}

SEED_R01 = "01a1e571-2838-714b-861b-bf0835d7c90a"
SEED_R02 = "01a1e573-ca14-72ba-a46a-c84690288e22"
SEED_R03 = "01a1e578-8f3a-7e0c-826b-a2c9dc066a8f"
SEED_R04 = "01a20400-0000-7000-8000-000000000004"
SEED_R05 = "01a20400-0000-7000-8000-000000000005"
SEED_R06 = "01a20400-0000-7000-8000-000000000006"
SEED_R07 = "01a20400-0000-7000-8000-000000000007"
SEED_R08 = "01a1e8cf-ec7a-744c-bbd4-04074813c931"
SEED_R09 = "01a1e8cf-ed70-7826-a834-61d5a3ce13bd"

F1_PDF_SHA256 = "875a2d8c83c1c1002b38840f8136b60bd5ebcfe8d2df47187bf36454c59497cb"


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
    timeout_s: int = 600,
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
    cp = run_cmd(["git", *args], cwd=repo_root, timeout_s=60)
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr}")
    return cp.stdout.strip()


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
    cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps_script], cwd=cwd, timeout_s=30)
    if cp.returncode != 0:
        raise RuntimeError(f"Port observation failed: {cp.stderr}")
    return json.loads(cp.stdout)


def inspect_process(pid: int, cwd: Path) -> dict | None:
    ps = (
        f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
        "if ($null -eq $p) { 'null' } else { "
        "@{ pid = [int]$p.Id; name = $p.ProcessName; workingSetBytes = [int64]$p.WorkingSet64; startUtc = $p.StartTime.ToUniversalTime().ToString('o') } | ConvertTo-Json -Compress }"
    )
    cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps], cwd=cwd, timeout_s=30)
    if cp.returncode != 0 or cp.stdout.strip() == "null":
        return None
    return json.loads(cp.stdout)


def stop_owned_process(proc: subprocess.Popen[bytes] | None, recorded_info: dict | None, cwd: Path) -> dict:
    if proc is None or recorded_info is None:
        return {"stopped": False, "reason": "not_started"}
    pid = recorded_info["pid"]
    expected_start = recorded_info["startUtc"]
    if proc.poll() is not None:
        return {"pid": pid, "name": recorded_info["name"], "startUtc": expected_start, "alreadyExitedCode": proc.returncode, "aliveAfter": False}
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
    tuples_only: bool = True,
    expect_success: bool = True,
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
    ]
    if tuples_only:
        args.extend(["-A", "-t"])
    args.extend(["-f", "-"])
    cp = run_cmd(args, cwd=cwd, env=env, input_text=sql, timeout_s=120)
    if expect_success and cp.returncode != 0:
        raise RuntimeError(f"psql failed as {user} on {database} (exit {cp.returncode}): {cp.stderr}")
    return cp


def http_request_raw(
    port: int,
    method: str,
    raw_target: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout_s: int = 30,
) -> tuple[int, dict[str, str], bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout_s)
    try:
        req_headers = {"Host": f"127.0.0.1:{port}"}
        if headers:
            req_headers.update(headers)
        conn.putrequest(method, raw_target, skip_host=True)
        for k, v in req_headers.items():
            conn.putheader(k, v)
        if body is not None:
            conn.putheader("Content-Length", str(len(body)))
        conn.endheaders(body)
        resp = conn.getresponse()
        raw = resp.read()
        hdrs = {k.lower(): v for k, v in resp.getheaders()}
        return resp.status, hdrs, raw
    finally:
        conn.close()


def http_get_json(port: int, raw_target: str) -> tuple[int, dict[str, str], dict]:
    st, hdrs, raw = http_request_raw(port, "GET", raw_target)
    return st, hdrs, (json.loads(raw.decode("utf-8")) if raw else {})


def compute_canonical_8table_snapshot(psql_exe: Path, settings: dict, database: str, cwd: Path) -> dict:
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
    return {
        "canonical_8table_sha256": sha256_hex(canonical),
        "counts": {k: len(parsed[k]) for k in parsed if k != "fencing_seq"},
        "fencing_seq": parsed["fencing_seq"],
    }


def compute_projection_tables_snapshot(psql_exe: Path, settings: dict, database: str, cwd: Path) -> dict:
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
    return {
        "projection_tables_sha256": sha256_hex(canonical),
        "projection_count": len(parsed["projections"]),
        "unit_count": len(parsed["units"]),
        "projections": parsed["projections"],
        "units": parsed["units"],
    }


def start_owned_api(
    *,
    api_dll: Path,
    port: int,
    settings: dict,
    database: str,
    log_path: Path,
    cwd: Path,
    extra_env: dict[str, str] | None = None,
) -> tuple[subprocess.Popen[bytes], dict]:
    ports_now = observe_ports((port,), cwd)
    if ports_now[str(port)]:
        raise RuntimeError(f"Port {port} already bound before starting owned API: {ports_now}")

    api_env = dict(os.environ)
    api_env["ASPNETCORE_ENVIRONMENT"] = "Production"
    api_env["DOTNET_NOLOGO"] = "1"
    api_env["Api__Port"] = str(port)
    api_env["LocalOcr__Enabled"] = "false"
    api_env["ConnectionStrings__Runtime"] = (
        f"Host={settings['host']};Port={settings['port']};Database={database};"
        f"Username={settings['appUser']};Password={settings['appPassword']}"
    )
    if extra_env:
        api_env.update(extra_env)

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
            st, _, _ = http_request_raw(port, "GET", "/api/documents/00000000-0000-7000-8000-999999999999")
            if st == 404:
                ready = True
                break
        except OSError:
            time.sleep(0.2)
    if not ready or info is None:
        stop_owned_process(proc, info, cwd)
        raise RuntimeError(f"ELedgerCare.Api failed to listen on 127.0.0.1:{port}")
    return proc, info


def start_owned_ui(
    *,
    node_exe: Path,
    ui_port: int,
    api_port: int,
    log_path: Path,
    repo_root: Path,
) -> tuple[subprocess.Popen[bytes], dict]:
    ports_now = observe_ports((ui_port,), repo_root)
    if ports_now[str(ui_port)]:
        raise RuntimeError(f"Port {ui_port} already bound before starting owned UI: {ports_now}")

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
    deadline = time.monotonic() + 120.0
    ready = False
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"ng serve exited early with code {proc.returncode}")
        try:
            st, _, _ = http_request_raw(ui_port, "GET", "/")
            if st == 200:
                ready = True
                break
        except OSError:
            time.sleep(0.4)
    if not ready or info is None:
        stop_owned_process(proc, info, repo_root)
        raise RuntimeError(f"ng serve failed to listen on 127.0.0.1:{ui_port}")
    return proc, info


def run_saved_archive_query_suite(api_port: int) -> dict:
    """Executes 30 deterministic HTTP archive queries against `eledgercare_f4_reviewer_migrated`."""
    saved_cases = [
        ("browse_all", "/api/archive"),
        ("browse_machine", "/api/archive?source=machine"),
        ("browse_reviewed", "/api/archive?source=reviewed"),
        ("literal_metachar_r01", "/api/archive?q=" + urllib.parse.quote("7.50% Cap_Rate \\") + "&source=reviewed"),
        ("literal_wildcard_non_expansion_1", "/api/archive?q=" + urllib.parse.quote("7%50%") + "&source=reviewed"),
        ("literal_wildcard_non_expansion_2", "/api/archive?q=" + urllib.parse.quote("Cap%Literal") + "&source=reviewed"),
        ("astral_wrench_emoji", "/api/archive?q=" + urllib.parse.quote("🔧") + "&source=reviewed"),
        ("c_locale_cafe_exact_match", "/api/archive?q=" + urllib.parse.quote("café") + "&source=reviewed"),
        ("c_locale_cafe_non_ascii_upper_miss", "/api/archive?q=" + urllib.parse.quote("CAFÉ") + "&source=reviewed"),
        ("leading_zero_reviewed_r06", "/api/archive?q=WO-0006-TIE-LOW&source=reviewed"),
        ("leading_zero_machine_qc", "/api/archive?q=0018-TERM-QC&source=machine"),
        ("multipage_colspan_p1_p3_and", "/api/archive?q=MP01-P3+MP01-P1&source=machine"),
        ("multipage_currency_p3", "/api/archive?q=" + urllib.parse.quote("$1,535.35") + "&source=machine"),
        ("table_tag_not_indexed", "/api/archive?q=" + urllib.parse.quote("<table>") + "&source=all"),
        ("colspan_attr_not_indexed", "/api/archive?q=colspan&source=all"),
        ("cross_doc_and_empty", "/api/archive?q=WO-004192+MP01-P2&source=all"),
        ("mixed_source_and_r01_all", "/api/archive?q=North+Wing+0018-TERM-QC&source=all"),
        ("mixed_source_and_r01_reviewed_miss", "/api/archive?q=North+Wing+0018-TERM-QC&source=reviewed"),
        ("mixed_source_and_r01_machine_miss", "/api/archive?q=North+Wing+0018-TERM-QC&source=machine"),
        ("unit_204_removed_on_r01_reviewed", "/api/archive?q=Unit+204&source=reviewed"),
        ("unit_204_retained_on_r01_machine_in_all", "/api/archive?q=Unit+204&source=all"),
        ("superseded_rev1_excluded", "/api/archive?q=" + urllib.parse.quote("[REV1-SUPERSEDED]") + "&source=all"),
        ("newer_draft_r3_excluded", "/api/archive?q=UNAPPROVED-DRAFT-R3-DO-NOT-INDEX&source=all"),
        ("draft_unreviewed_field_excluded", "/api/archive?q=DRAFT-UNIT-UNREVIEWED-999&source=all"),
        ("draft_only_doc_r05_excluded", "/api/archive?q=WO-DRAFT-ONLY-R1&source=all"),
        ("unknown_reason_excluded", "/api/archive?q=R4-UNKNOWN-REASON-ILLEGIBLE-BADGE&source=all"),
        ("operator_label_excluded", "/api/archive?q=R4-OP-HIDDEN-BETA&source=all"),
        ("failed_diagnostic_raw_excluded", "/api/archive?q=DIAGNOSTIC-PARTIAL-RAW-NEVER-SEARCHABLE&source=all"),
        ("interrupted_failure_code_excluded", "/api/archive?q=supervisor_interrupted&source=all"),
        ("internal_uuid_excluded", f"/api/archive?q={SEED_R01}&source=all"),
    ]

    results: dict[str, dict] = {}
    for name, url in saved_cases:
        st, hdrs, body = http_get_json(api_port, url)
        if st != 200 or hdrs.get("cache-control") != "no-store":
            raise AssertionError(f"Saved archive query {name} ({url}) failed: status={st}, hdrs={hdrs}")
        results[name] = body

    # Keyset walk across all 9 documents with limit=2 (5 pages)
    walked_ids: list[str] = []
    after: str | None = None
    pages = 0
    while True:
        q_url = "/api/archive?limit=2" if after is None else f"/api/archive?limit=2&after={urllib.parse.quote(after)}"
        st, _, pg = http_get_json(api_port, q_url)
        if st != 200:
            raise AssertionError(f"Keyset walk failed at page {pages + 1}: {st}")
        pages += 1
        walked_ids.extend(it["documentId"] for it in pg["items"])
        if not pg["hasMore"]:
            if pg["nextCursor"] is not None:
                raise AssertionError("Expected nextCursor=None when hasMore=False")
            break
        after = pg["nextCursor"]

    expected_order = [SEED_R09, SEED_R08, SEED_R07, SEED_R06, SEED_R05, SEED_R04, SEED_R03, SEED_R02, SEED_R01]
    if pages != 5 or walked_ids != expected_order:
        raise AssertionError(f"Keyset pagination mismatch: pages={pages}, ids={walked_ids}")

    # Semantic assertions on the 30 saved queries
    if [it["documentId"] for it in results["browse_all"]["items"]] != expected_order:
        raise AssertionError("browse_all order mismatch")
    if len(results["browse_machine"]["items"]) != 7:
        raise AssertionError("Expected 7 completed machine results in browse_machine")
    if [it["documentId"] for it in results["browse_reviewed"]["items"]] != [SEED_R06, SEED_R04, SEED_R03, SEED_R01]:
        raise AssertionError(f"Unexpected browse_reviewed items: {[it['documentId'] for it in results['browse_reviewed']['items']]}")

    for must_hit_exact, exp_docs in (
        ("literal_metachar_r01", [SEED_R01]),
        ("astral_wrench_emoji", [SEED_R01]),
        ("c_locale_cafe_exact_match", [SEED_R01]),
        ("leading_zero_reviewed_r06", [SEED_R06]),
        ("mixed_source_and_r01_all", [SEED_R01]),
        ("unit_204_removed_on_r01_reviewed", [SEED_R06, SEED_R03]),
    ):
        items = results[must_hit_exact]["items"]
        if [it["documentId"] for it in items] != exp_docs:
            raise AssertionError(f"Query {must_hit_exact} expected {exp_docs}, got {[it['documentId'] for it in items]}")

    mixed_card = results["mixed_source_and_r01_all"]["items"][0]
    if (
        mixed_card["contributingSources"] != ["reviewed", "machine"]
        or mixed_card["hasNewerDraft"] is not True
        or len(mixed_card["witnesses"]) != 2
        or mixed_card["witnesses"][0]["consultedPageNumber"] is not None
        or mixed_card["witnesses"][1]["pageNumber"] != 1
    ):
        raise AssertionError(f"Mixed-source card mismatch: {mixed_card}")

    r01_in_unit204_all = next(it for it in results["unit_204_all"]["items"] if it["documentId"] == SEED_R01) if "unit_204_all" in results else next(
        it for it in results["unit_204_retained_on_r01_machine_in_all"]["items"] if it["documentId"] == SEED_R01
    )
    if r01_in_unit204_all["contributingSources"] != ["machine"]:
        raise AssertionError(f"Expected SEED-R01 Unit 204 match to be strictly machine, got {r01_in_unit204_all['contributingSources']}")

    for must_be_zero in (
        "literal_wildcard_non_expansion_1",
        "literal_wildcard_non_expansion_2",
        "c_locale_cafe_non_ascii_upper_miss",
        "table_tag_not_indexed",
        "colspan_attr_not_indexed",
        "cross_doc_and_empty",
        "mixed_source_and_r01_reviewed_miss",
        "mixed_source_and_r01_machine_miss",
        "superseded_rev1_excluded",
        "newer_draft_r3_excluded",
        "draft_unreviewed_field_excluded",
        "draft_only_doc_r05_excluded",
        "unknown_reason_excluded",
        "operator_label_excluded",
        "failed_diagnostic_raw_excluded",
        "interrupted_failure_code_excluded",
        "internal_uuid_excluded",
    ):
        if len(results[must_be_zero]["items"]) != 0:
            raise AssertionError(f"Expected 0 hits for {must_be_zero}, got {len(results[must_be_zero]['items'])}")

    canonical = json.dumps(
        {"saved_queries": results, "keyset_walk_limit_2": walked_ids},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return {
        "saved_query_count": len(saved_cases),
        "keyset_pages_limit_2": pages,
        "saved_queries_sha256": sha256_hex(canonical),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WP-0010 / 004 independent source & live runtime verifier.")
    parser.add_argument("--output", required=True, help="Output JSON verification summary path")
    parser.add_argument("--resource-return-output", required=True, help="Output JSON resource-return receipt path")
    parser.add_argument("--explain-output", required=True, help="Output text path for EXPLAIN plans")
    parser.add_argument("--logs-dir", required=True, help="Directory for sanitized execution logs")
    parser.add_argument("--screenshots-dir", required=True, help="Directory for Edge PNG screenshots")
    parser.add_argument("--edge-before-output", required=True, help="Before-restart Edge receipt path")
    parser.add_argument("--edge-after-output", required=True, help="After-restart Edge receipt path")
    parser.add_argument("--demo-smoke-output", required=True, help="5690 demo smoke receipt path")
    parser.add_argument("--require-clean", action="store_true", help="Require clean worktree before starting")
    args = parser.parse_args(argv)

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[6]
    logs_dir = (repo_root / args.logs_dir).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)

    assertions: list[dict] = []
    step_receipts: list[dict] = []
    spawned_processes: list[dict] = []

    def record_assert(name: str, cond: bool, detail: object) -> None:
        if not cond:
            raise AssertionError(f"Independent runtime assertion failed [{name}]: {detail}")
        assertions.append({"check": name, "passed": True, "detail": detail})

    # -------------------------------------------------------------------------
    # Step 01: Static, Git-tree, Author-diff, & Port Pre-flight Audit
    # -------------------------------------------------------------------------
    status_porcelain = run_git(repo_root, "status", "--porcelain", "--untracked-files=normal")
    if args.require_clean:
        record_assert("clean_worktree_before_decisive_run", status_porcelain == "", {"status": status_porcelain})

    head_sha = run_git(repo_root, "rev-parse", "HEAD")
    branch_name = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    record_assert("owned_review_branch", branch_name == "review/wp-0010-f4", {"branch": branch_name, "head": head_sha})

    for anc_name, anc_sha in (
        ("design_002", PRIOR_DESIGN_002_SHA),
        ("reviewer_prep", REVIEWER_PREP_SHA),
        ("root_runtime_authority", ROOT_RUNTIME_AUTHORITY_SHA),
        ("author_003_pub", AUTHOR_003_PUB_SHA),
        ("merged_review_base", MERGED_REVIEW_BASE_SHA),
    ):
        is_anc = run_cmd(["git", "merge-base", "--is-ancestor", anc_sha, head_sha], cwd=repo_root).returncode == 0
        record_assert(f"ancestor_verified:{anc_name}", is_anc, {"sha": anc_sha})

    for tree_rel, exp_oid in EXPECTED_PRODUCT_TREES.items():
        head_oid = run_git(repo_root, "rev-parse", f"{head_sha}:{tree_rel}")
        cand_oid = run_git(repo_root, "rev-parse", f"{AUTHOR_CANDIDATE_SHA}:{tree_rel}")
        first_oid = run_git(repo_root, "rev-parse", f"{AUTHOR_FIRST_FROZEN_SHA}:{tree_rel}")
        record_assert(
            f"product_tree_oid_exact:{tree_rel}",
            head_oid == cand_oid == first_oid == exp_oid,
            {"oid": head_oid},
        )

    prior_reviewer_diff = run_git(
        repo_root,
        "diff",
        "--name-status",
        REVIEWER_PREP_SHA,
        head_sha,
        "--",
        "docs/agent-reports/eld-f4-reviewer/WP-0010/002_2026-11-17_review_eld-f4-reviewer.md",
        "docs/reviews/WP-0010/eld-f4-reviewer/design",
        "docs/reviews/WP-0010/eld-f4-reviewer/preparation",
    )
    record_assert("immutable_002_design_and_preparation_untouched", prior_reviewer_diff == "", {"diff": prior_reviewer_diff})

    author_cand_paths = [
        ln for ln in run_git(repo_root, "diff", "--name-only", AUTHOR_BASE_SHA, AUTHOR_CANDIDATE_SHA).splitlines() if ln.strip()
    ]
    author_ev_paths = [
        ln for ln in run_git(repo_root, "diff", "--name-only", AUTHOR_CANDIDATE_SHA, AUTHOR_EVIDENCE_SHA).splitlines() if ln.strip()
    ]
    author_pub_paths = [
        ln for ln in run_git(repo_root, "diff", "--name-only", AUTHOR_EVIDENCE_SHA, AUTHOR_003_PUB_SHA).splitlines() if ln.strip()
    ]
    dep_pin_Touches = [
        p
        for p in author_cand_paths
        if p.endswith((".csproj", "packages.lock.json", "package-lock.json", "Directory.Packages.props"))
        or p.startswith(("workers/", "research/", "evaluation/", "qualification/", "docs/design/"))
    ]
    record_assert(
        "author_commit_structure_and_dependency_pins_preserved",
        (
            len(author_cand_paths) == 52
            and len(author_ev_paths) == 39
            and author_pub_paths == ["docs/agent-reports/eld-f4-implementer/WP-0010/003_2026-11-17_implementation_eld-f4-implementer.md"]
            and dep_pin_Touches == []
        ),
        {
            "candidate_paths": len(author_cand_paths),
            "evidence_paths": len(author_ev_paths),
            "report_only_pub": True,
            "dependency_or_worker_edits": 0,
        },
    )

    # Scan production C# and TS files for forbidden imports, mocks, innerHTML, or browser storage
    cs_files = sorted((repo_root / "src").rglob("*.cs"))
    cs_files = [f for f in cs_files if "bin" not in f.parts and "obj" not in f.parts]
    ts_files = sorted((repo_root / "web" / "src").rglob("*.ts"))
    static_violations: list[str] = []
    for csf in cs_files:
        txt = csf.read_text(encoding="utf-8")
        for forbidden in ("Qualification", "Evaluation", "MockOcr", "FakeOcr"):
            if forbidden in txt:
                static_violations.append(f"{csf.relative_to(repo_root).as_posix()}:{forbidden}")
    for tsf in ts_files:
        rel_ts = tsf.relative_to(repo_root).as_posix()
        txt = tsf.read_text(encoding="utf-8")
        lines_no_comments = "\n".join(
            ln for ln in txt.splitlines() if not ln.strip().startswith(("//", "*", "/*"))
        )
        for forbidden_ts in ("innerHTML", "bypassSecurityTrustHtml", "localStorage"):
            if forbidden_ts in lines_no_comments:
                static_violations.append(f"{rel_ts}:{forbidden_ts}")
        # F1 submission-api.ts stores only the accepted WP-0003 upload idempotency key in sessionStorage;
        # all other 14 TS files (including all F3 review and F4 archive files) must have zero sessionStorage.
        if rel_ts != "web/src/app/intake/submission-api.ts" and "sessionStorage" in lines_no_comments:
            static_violations.append(f"{rel_ts}:sessionStorage")

    sub_api_base_oid = run_git(repo_root, "rev-parse", f"{AUTHOR_BASE_SHA}:web/src/app/intake/submission-api.ts")
    sub_api_head_oid = run_git(repo_root, "rev-parse", f"{head_sha}:web/src/app/intake/submission-api.ts")
    if sub_api_base_oid != sub_api_head_oid:
        static_violations.append("web/src/app/intake/submission-api.ts:modified_since_f3")
    record_assert(
        "production_cs_and_ts_static_boundary_scan_clean",
        static_violations == [],
        {"cs_files": len(cs_files), "ts_files": len(ts_files), "violations": static_violations},
    )

    ports_before = observe_ports(REVIEWER_PORTS, repo_root)
    record_assert(
        "reviewer_ports_5690_4710_55439_free_before_start",
        all(len(ports_before[str(p)]) == 0 for p in REVIEWER_PORTS),
        ports_before,
    )

    local_dir = repo_root / ".local"
    settings = json.loads((local_dir / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
    secrets = [str(settings["adminPassword"]), str(settings["migratorPassword"]), str(settings["appPassword"])]
    psql_exe = local_dir / "tools" / "pgsql-18.7-1" / "bin" / "psql.exe"
    pg_ctl_exe = local_dir / "tools" / "pgsql-18.7-1" / "bin" / "pg_ctl.exe"
    pg_data_dir = local_dir / "postgres-data"
    api_dll = repo_root / "src" / "ELedgerCare.Api" / "bin" / "Release" / "net10.0" / "ELedgerCare.Api.dll"
    node_exe = Path(shutil.which("node") or "node")

    dotnet_env = dict(os.environ)
    dotnet_env["DOTNET_CLI_HOME"] = str(local_dir / "dotnet-home")
    dotnet_env["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1"
    dotnet_env["DOTNET_NOLOGO"] = "1"
    dotnet_env["NUGET_PACKAGES"] = str(local_dir / "nuget" / "packages")

    tool_versions = {
        "git": run_cmd(["git", "--version"], cwd=repo_root).stdout.strip(),
        "python": sys.version.split()[0],
        "dotnet_sdk": run_cmd(["dotnet", "--version"], cwd=repo_root, env=dotnet_env).stdout.strip(),
        "dotnet_ef": run_cmd(["dotnet", "tool", "run", "dotnet-ef", "--version"], cwd=repo_root, env=dotnet_env).stdout.splitlines()[-1].strip(),
        "node": run_cmd([str(node_exe), "--version"], cwd=repo_root).stdout.strip(),
        "postgres": run_cmd([str(psql_exe), "--version"], cwd=repo_root).stdout.strip(),
    }

    def run_logged_step(
        step_id: str,
        argv: list[str],
        *,
        step_cwd: Path = repo_root,
        step_env: dict[str, str] | None = None,
        timeout_s: int = 600,
    ) -> subprocess.CompletedProcess[str]:
        t0 = time.monotonic()
        started_utc = datetime.now(timezone.utc).isoformat()
        cp = run_cmd(argv, cwd=step_cwd, env=step_env, timeout_s=timeout_s)
        elapsed_ms = round((time.monotonic() - t0) * 1000.0, 1)
        log_file = logs_dir / f"{step_id}.log"
        sanitized = redact_secrets((cp.stdout + cp.stderr).replace("\r\n", "\n"), secrets)
        log_file.write_text(sanitized, encoding="utf-8", newline="\n")
        step_receipts.append({
            "step": step_id,
            "command": argv,
            "cwd": "." if step_cwd == repo_root else step_cwd.relative_to(repo_root).as_posix(),
            "started_utc": started_utc,
            "elapsed_ms": elapsed_ms,
            "exit_code": cp.returncode,
            "log_relpath": log_file.relative_to(repo_root).as_posix(),
            "log_sha256": sha256_hex(log_file.read_bytes()),
        })
        if cp.returncode != 0:
            raise RuntimeError(f"Step {step_id} failed (exit {cp.returncode}); see {log_file}")
        return cp

    active_api_proc: subprocess.Popen[bytes] | None = None
    active_api_info: dict | None = None
    active_ui_proc: subprocess.Popen[bytes] | None = None
    active_ui_info: dict | None = None

    try:
        # ---------------------------------------------------------------------
        # Step 02: Worker CPU tests + Offline .NET Release build + Angular build
        # ---------------------------------------------------------------------
        run_logged_step(
            "01-worker-cpu-tests",
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", "workers/local_ocr/tests", "-v"],
        )
        run_logged_step(
            "02-dotnet-restore-offline",
            ["dotnet", "restore", "ELedgerCare.slnx", "--locked-mode", "--configfile", ".local/nuget/offline.nuget.config"],
            step_env=dotnet_env,
        )
        build_cp = run_logged_step(
            "03-dotnet-build-release",
            ["dotnet", "build", "ELedgerCare.slnx", "-c", "Release", "--no-restore"],
            step_env=dotnet_env,
        )
        record_assert(
            "dotnet_release_build_zero_warnings_and_errors",
            "0 Warning(s)" in build_cp.stdout and "0 Error(s)" in build_cp.stdout,
            {"dll_exists": api_dll.exists()},
        )
        run_logged_step(
            "04-angular-production-build",
            [str(node_exe), "node_modules/@angular/cli/bin/ng.js", "build"],
            step_cwd=repo_root / "web",
        )

        # ---------------------------------------------------------------------
        # Step 03: Start owned PostgreSQL 18.7 (55439) & verify retained F3 seed
        # ---------------------------------------------------------------------
        run_logged_step(
            "05-pg-cluster-start-initial",
            ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"],
        )
        pm_pid_before = int((pg_data_dir / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        pm_info_before = inspect_process(pm_pid_before, repo_root)
        spawned_processes.append({"role": "postmaster_initial", "info": pm_info_before})

        seed_before = compute_canonical_8table_snapshot(psql_exe, settings, SEED_DB, repo_root)
        record_assert(
            "retained_f3_seed_intact_before_tests",
            seed_before["canonical_8table_sha256"] == EXPECTED_REVIEWER_SEED_8TABLE_SHA256,
            {"seed_sha256": seed_before["canonical_8table_sha256"], "counts": seed_before["counts"]},
        )

        # ---------------------------------------------------------------------
        # Step 04: Full .NET test suite (95/95 tests against owned PG 55439)
        # ---------------------------------------------------------------------
        test_cp = run_logged_step(
            "06-dotnet-test-release",
            ["dotnet", "test", "ELedgerCare.slnx", "-c", "Release", "--no-build"],
            step_env=dotnet_env,
            timeout_s=600,
        )
        record_assert(
            "dotnet_test_all_suites_passed",
            "Failed:     0" in test_cp.stdout or "failed: 0" in test_cp.stdout.lower(),
            {"exit_code": test_cp.returncode},
        )

        # ---------------------------------------------------------------------
        # Step 05: 5690 Demo Restart Smoke + 15/15 Playwright Edge E2E (5690/4710)
        # ---------------------------------------------------------------------
        run_logged_step(
            "07-prepare-dev-db",
            ["pwsh", "-NoProfile", "-File", "deploy/dev/database/prepare-database.ps1"],
            step_env=dotnet_env,
        )
        demo_out_abs = (repo_root / args.demo_smoke_output).resolve()
        demo_out_abs.parent.mkdir(parents=True, exist_ok=True)
        run_logged_step(
            "08-demo-smoke-5690",
            [
                "pwsh",
                "-NoProfile",
                "-File",
                "deploy/dev/smoke/run-demo-smoke.ps1",
                "-ApiPort",
                str(API_PORT),
                "-ReceiptPath",
                str(demo_out_abs),
            ],
            step_env=dotnet_env,
        )
        demo_json = json.loads(demo_out_abs.read_text(encoding="utf-8-sig"))
        demo_out_abs.write_text(json.dumps(demo_json, indent=2) + "\n", encoding="utf-8", newline="\n")
        record_assert("demo_smoke_5690_all_match", demo_json.get("allMatch") is True, {"apiPort": demo_json.get("apiPort")})

        # Note: run-demo-smoke.ps1 performed a PG stop/start, so refresh current postmaster PID
        pm_pid_mid = int((pg_data_dir / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        spawned_processes.append({"role": "postmaster_after_demo_smoke", "info": inspect_process(pm_pid_mid, repo_root)})

        run_logged_step(
            "09-playwright-edge-e2e-5690-4710",
            [
                "pwsh",
                "-NoProfile",
                "-File",
                "deploy/dev/smoke/run-browser-checks.ps1",
                "-Database",
                E2E_DB,
                "-ApiPort",
                str(API_PORT),
                "-UiPort",
                str(UI_PORT),
            ],
            step_env=dotnet_env,
            timeout_s=600,
        )

        # ---------------------------------------------------------------------
        # Step 06: Clone `eledgercare_f4_reviewer_seed_f3` -> `eledgercare_f4_reviewer_migrated` & forward-migrate
        # ---------------------------------------------------------------------
        invoke_psql(
            psql_exe,
            host=settings["host"],
            port=PG_PORT,
            user=settings["adminUser"],
            password=settings["adminPassword"],
            database="postgres",
            sql=f"""
DROP DATABASE IF EXISTS {MIGRATED_DB} WITH (FORCE);
CREATE DATABASE {MIGRATED_DB} OWNER {settings['migratorUser']} TEMPLATE {SEED_DB};
REVOKE ALL ON DATABASE {MIGRATED_DB} FROM PUBLIC;
GRANT CONNECT ON DATABASE {MIGRATED_DB} TO {settings['appUser']};
""",
            cwd=repo_root,
        )
        clone_pre_mig = compute_canonical_8table_snapshot(psql_exe, settings, MIGRATED_DB, repo_root)
        record_assert(
            "cloned_db_matches_seed_before_forward_migration",
            clone_pre_mig["canonical_8table_sha256"] == EXPECTED_REVIEWER_SEED_8TABLE_SHA256,
            {"pre_migration_8table_sha256": clone_pre_mig["canonical_8table_sha256"]},
        )

        run_logged_step(
            "10-forward-migrate-reviewer-seed-clone",
            ["pwsh", "-NoProfile", "-File", "deploy/dev/database/prepare-database.ps1", "-Database", MIGRATED_DB],
            step_env=dotnet_env,
        )

        mig_list_cp = invoke_psql(
            psql_exe,
            host=settings["host"],
            port=PG_PORT,
            user=settings["adminUser"],
            password=settings["adminPassword"],
            database=MIGRATED_DB,
            sql='SELECT json_agg("MigrationId" ORDER BY "MigrationId")::text FROM eledgercare.__ef_migrations_history;',
            cwd=repo_root,
        )
        applied_migrations = json.loads(mig_list_cp.stdout.strip())
        clone_post_mig = compute_canonical_8table_snapshot(psql_exe, settings, MIGRATED_DB, repo_root)
        pre_startup_proj = compute_projection_tables_snapshot(psql_exe, settings, MIGRATED_DB, repo_root)
        record_assert(
            "forward_migration_preserves_all_8_core_tables_and_adds_f4_schema",
            (
                applied_migrations
                == [
                    "20261114182147_InitialDurableIntake",
                    "20261116052029_AddLocalExtraction",
                    "20261116200918_AddWorkOrderReview",
                    "20261117091519_AddSourceLinkedArchive",
                ]
                and clone_post_mig["canonical_8table_sha256"] == EXPECTED_REVIEWER_SEED_8TABLE_SHA256
                and pre_startup_proj["projection_count"] == 0
            ),
            {
                "applied_migrations": applied_migrations,
                "post_migration_8table_sha256": clone_post_mig["canonical_8table_sha256"],
                "projections_before_api_startup": pre_startup_proj["projection_count"],
            },
        )

        # ---------------------------------------------------------------------
        # Step 07A: Verify deferred startup serves 503 archive_not_ready while unprojected
        # ---------------------------------------------------------------------
        active_api_proc, active_api_info = start_owned_api(
            api_dll=api_dll,
            port=API_PORT,
            settings=settings,
            database=MIGRATED_DB,
            log_path=logs_dir / "owned-api-5690-deferred-503.log",
            cwd=repo_root,
            extra_env={"Archive__DeferStartupInitialization": "true"},
        )
        st_503, hdrs_503, body_503 = http_get_json(API_PORT, "/api/archive")
        deferred_stop = stop_owned_process(active_api_proc, active_api_info, repo_root)
        spawned_processes.append({"role": "api_5690_deferred_503", "stop": deferred_stop})
        active_api_proc, active_api_info = None, None
        record_assert(
            "deferred_startup_serves_503_archive_not_ready_never_empty_200",
            st_503 == 503 and body_503.get("code") == "archive_not_ready" and hdrs_503.get("retry-after") == "1",
            {"status": st_503, "code": body_503.get("code"), "retry_after": hdrs_503.get("retry-after")},
        )

        # ---------------------------------------------------------------------
        # Step 07B: Start normal API (LocalOcr:Enabled=false) -> backfills 7 results / 13 units,
        #           run 30 saved queries, 18 raw 400 checks, 19 privilege denials, EXPLAIN & metrics
        # ---------------------------------------------------------------------
        active_api_proc, active_api_info = start_owned_api(
            api_dll=api_dll,
            port=API_PORT,
            settings=settings,
            database=MIGRATED_DB,
            log_path=logs_dir / "owned-api-5690-before-restart.log",
            cwd=repo_root,
        )
        proj_before_restart = compute_projection_tables_snapshot(psql_exe, settings, MIGRATED_DB, repo_root)
        record_assert(
            "startup_backfill_projected_all_7_genuine_results_and_13_units_with_ocr_disabled",
            (
                proj_before_restart["projection_count"] == 7
                and proj_before_restart["unit_count"] == 13
                and all(p["has_fallback"] is False for p in proj_before_restart["projections"])
            ),
            {
                "projection_count": proj_before_restart["projection_count"],
                "unit_count": proj_before_restart["unit_count"],
                "projection_tables_sha256": proj_before_restart["projection_tables_sha256"],
            },
        )

        queries_before_restart = run_saved_archive_query_suite(API_PORT)
        record_assert(
            "saved_30_archive_queries_and_keyset_walk_passed_before_restart",
            queries_before_restart["saved_query_count"] == 30 and queries_before_restart["keyset_pages_limit_2"] == 5,
            queries_before_restart,
        )

        # Obtain a valid cursor and test 18 raw HTTP socket 400 rejections
        _, _, p1_cursor_body = http_get_json(API_PORT, "/api/archive?limit=2")
        valid_cursor = p1_cursor_body["nextCursor"]
        tampered_ver_cursor = base64.urlsafe_b64encode(
            json.dumps({
                "v": "archive-cursor/999",
                "t": 1794852000123456,
                "id": SEED_R07,
                "s": "all",
                "qh": "0" * 64,
            }).encode("utf-8")
        ).decode("ascii").rstrip("=")
        tampered_range_cursor = base64.urlsafe_b64encode(
            json.dumps({
                "v": "archive-cursor/1",
                "t": 100,
                "id": SEED_R07,
                "s": "all",
                "qh": "0" * 64,
            }).encode("utf-8")
        ).decode("ascii").rstrip("=")

        bad_raw_targets = [
            "/api/archive?unknown=1",
            "/api/archive?Q=upper",
            "/api/archive?q=a&q=b",
            "/api/archive?source=all&source=reviewed",
            "/api/archive?q=%2",
            "/api/archive?q=%FF",
            "/api/archive?q=%C3%28",
            "/api/archive?q=%ED%A0%80",
            "/api/archive?q=test%00nul",
            "/api/archive?q=test%07bell",
            "/api/archive?q=test%7Fdel",
            "/api/archive?source=invalid",
            "/api/archive?limit=0",
            "/api/archive?limit=51",
            "/api/archive?limit=02",
            "/api/archive?q=" + ("x" * 161),
            "/api/archive?q=t1+t2+t3+t4+t5+t6+t7+t8+t9",
            "/api/archive?q=" + ("z" * 65),
            "/api/archive?after=" + ("a" * 257),
            f"/api/archive?after={tampered_ver_cursor}",
            f"/api/archive?after={tampered_range_cursor}",
            f"/api/archive?q=changed&limit=2&after={urllib.parse.quote(valid_cursor)}",
            f"/api/archive?source=machine&limit=2&after={urllib.parse.quote(valid_cursor)}",
        ]
        bad_statuses = []
        for bt in bad_raw_targets:
            st_b, _, raw_b = http_request_raw(API_PORT, "GET", bt)
            parsed_b = json.loads(raw_b.decode("utf-8"))
            bad_statuses.append((bt, st_b, parsed_b.get("code")))
        record_assert(
            "raw_http_socket_400_validation_matrix_passed",
            (
                all(st == 400 for _, st, _ in bad_statuses)
                and bad_statuses[-1][2] == "cursor_query_mismatch"
                and bad_statuses[-2][2] == "cursor_query_mismatch"
            ),
            {"tested_count": len(bad_statuses)},
        )

        # Direct PostgreSQL 18.7 least-privilege denials (including new F4 projection tables!)
        denied_sqls = [
            "UPDATE eledgercare.archive_result_projections SET has_fallback = true",
            "DELETE FROM eledgercare.archive_result_projections",
            "TRUNCATE eledgercare.archive_result_projections",
            "UPDATE eledgercare.archive_projection_units SET search_text = 'tamper'",
            "DELETE FROM eledgercare.archive_projection_units",
            "TRUNCATE eledgercare.archive_projection_units",
            "UPDATE eledgercare.original_artifacts SET bytes = bytes",
            "DELETE FROM eledgercare.original_artifacts",
            "UPDATE eledgercare.documents SET submitted_at = submitted_at",
            "DELETE FROM eledgercare.documents",
            "UPDATE eledgercare.extraction_results SET raw_output_bytes = raw_output_bytes",
            "DELETE FROM eledgercare.extraction_results",
            "UPDATE eledgercare.work_order_review_revisions SET status = 'reviewed'",
            "DELETE FROM eledgercare.work_order_review_revisions",
            "UPDATE eledgercare.work_order_review_fields SET human_value = 'tamper'",
            "DELETE FROM eledgercare.work_order_review_fields",
            "UPDATE eledgercare.work_order_review_heads SET machine_snapshot_json = machine_snapshot_json",
            "DELETE FROM eledgercare.work_order_review_heads",
            "CREATE TABLE eledgercare.reviewer_forbidden_probe (id int)",
        ]
        priv_denials = []
        for dsql in denied_sqls:
            cp_d = invoke_psql(
                psql_exe,
                host=settings["host"],
                port=PG_PORT,
                user=settings["appUser"],
                password=settings["appPassword"],
                database=MIGRATED_DB,
                sql=dsql,
                cwd=repo_root,
                expect_success=False,
            )
            priv_denials.append(cp_d.returncode != 0 and "permission denied" in cp_d.stderr.lower())
        record_assert(
            "least_privilege_denies_all_19_mutations_including_f4_projections",
            all(priv_denials),
            {"denied_count": len(priv_denials)},
        )

        # Capture EXPLAIN (ANALYZE, BUFFERS) both default and with enable_seqscan=off + warm query metrics
        explain_sql = """
ANALYZE;
SELECT '=== 1. DEFAULT 9-ROW KEYSET BROWSE PLAN ===';
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT d.document_id, d.submitted_at
FROM eledgercare.documents d
WHERE (d.submitted_at, d.document_id) < ('2099-01-01T00:00:00Z'::timestamptz, 'ffffffff-ffff-ffff-ffff-ffffffffffff'::uuid)
ORDER BY d.submitted_at DESC, d.document_id DESC
LIMIT 21;

BEGIN;
SET LOCAL enable_seqscan = off;
SELECT '=== 2. FORCED INDEX-SCAN KEYSET BROWSE PLAN (enable_seqscan = off) ===';
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT d.document_id, d.submitted_at
FROM eledgercare.documents d
WHERE (d.submitted_at, d.document_id) < ('2099-01-01T00:00:00Z'::timestamptz, 'ffffffff-ffff-ffff-ffff-ffffffffffff'::uuid)
ORDER BY d.submitted_at DESC, d.document_id DESC
LIMIT 21;
COMMIT;

SELECT '=== 3. SINGLE-SNAPSHOT MIXED-SOURCE KEYWORD + LATERAL LATEST-REVIEWED PLAN ===';
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT d.document_id, d.submitted_at, lr.revision_id
FROM eledgercare.documents d
LEFT JOIN eledgercare.extraction_results er ON er.document_id = d.document_id
LEFT JOIN LATERAL (
    SELECT r.revision_id, r.revision_number
    FROM eledgercare.work_order_review_revisions r
    WHERE r.document_id = d.document_id AND r.status = 'reviewed'
    ORDER BY r.revision_number DESC
    LIMIT 1
) lr ON TRUE
WHERE (er.result_id IS NOT NULL OR lr.revision_id IS NOT NULL)
  AND (
      EXISTS (
          SELECT 1 FROM eledgercare.archive_projection_units apu
          WHERE apu.document_id = d.document_id
            AND apu.projection_version = 'archive-machine-projection/1'
            AND apu.search_text ILIKE '%North%' ESCAPE '\\'
      )
      OR (
          lr.revision_id IS NOT NULL AND EXISTS (
              SELECT 1 FROM eledgercare.work_order_review_fields rf
              WHERE rf.revision_id = lr.revision_id
                AND rf.decision IN ('accepted', 'edited')
                AND rf.human_value IS NOT NULL
                AND rf.human_value ILIKE '%North%' ESCAPE '\\'
          )
      )
  )
ORDER BY d.submitted_at DESC, d.document_id DESC
LIMIT 21;
"""
        explain_cp = invoke_psql(
            psql_exe,
            host=settings["host"],
            port=PG_PORT,
            user=settings["adminUser"],
            password=settings["adminPassword"],
            database=MIGRATED_DB,
            sql=explain_sql,
            cwd=repo_root,
        )
        explain_text = explain_cp.stdout.replace("\r\n", "\n").strip() + "\n"
        explain_out_path = (repo_root / args.explain_output).resolve()
        explain_out_path.parent.mkdir(parents=True, exist_ok=True)
        explain_out_path.write_text(explain_text, encoding="utf-8", newline="\n")
        record_assert(
            "explain_plans_captured_and_keyset_index_usable",
            "Index Only Scan" in explain_text or "Index Scan using ix_documents_submitted_at_document_id_desc" in explain_text,
            {"explain_sha256": sha256_hex(explain_out_path.read_bytes())},
        )

        latencies_ms = []
        for _ in range(10):
            t_q = time.perf_counter()
            st_q, _, _ = http_get_json(API_PORT, "/api/archive?q=North+Wing+0018-TERM-QC&source=all")
            latencies_ms.append(round((time.perf_counter() - t_q) * 1000.0, 2))
            if st_q != 200:
                raise AssertionError("Warm query probe failed")
        api_mem_info = inspect_process(active_api_info["pid"], repo_root)
        modest_metrics = {
            "declared_archive_documents": 9,
            "declared_projected_results": 7,
            "warm_query_count": len(latencies_ms),
            "p50_ms": round(statistics.median(latencies_ms), 2),
            "max_ms": max(latencies_ms),
            "samples_ms": latencies_ms,
            "api_working_set_bytes": api_mem_info["workingSetBytes"] if api_mem_info else None,
            "api_working_set_mib": round(api_mem_info["workingSetBytes"] / (1024 * 1024), 2) if api_mem_info else None,
            "scope_note": "Local synthetic 9-document reviewer archive on loopback; not an enterprise scalability claim.",
        }

        # ---------------------------------------------------------------------
        # Step 08: Microsoft Edge verification BEFORE restart (4710 -> 5690)
        # ---------------------------------------------------------------------
        active_ui_proc, active_ui_info = start_owned_ui(
            node_exe=node_exe,
            ui_port=UI_PORT,
            api_port=API_PORT,
            log_path=logs_dir / "owned-ui-4710-before-restart.log",
            repo_root=repo_root,
        )
        edge_helper = repo_root / "docs/reviews/WP-0010/eld-f4-reviewer/runtime/helpers/verify_f4_independent_edge.mjs"
        run_logged_step(
            "11-edge-f4-before-restart",
            [
                str(node_exe),
                str(edge_helper),
                "--phase",
                "before-restart",
                "--ui-port",
                str(UI_PORT),
                "--api-port",
                str(API_PORT),
                "--output",
                args.edge_before_output,
                "--screenshot-dir",
                args.screenshots_dir,
            ],
            timeout_s=240,
        )

        # ---------------------------------------------------------------------
        # Step 09: Stop UI + API + PostgreSQL 55439, restart all three, and re-verify!
        # ---------------------------------------------------------------------
        ui_before_stop = stop_owned_process(active_ui_proc, active_ui_info, repo_root)
        api_before_stop = stop_owned_process(active_api_proc, active_api_info, repo_root)
        spawned_processes.append({"role": "ui_4710_before_restart", "stop": ui_before_stop})
        spawned_processes.append({"role": "api_5690_before_restart", "stop": api_before_stop})
        active_ui_proc, active_ui_info = None, None
        active_api_proc, active_api_info = None, None

        run_logged_step(
            "12-pg-cluster-stop-for-restart",
            ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"],
        )
        ports_mid_restart = observe_ports(REVIEWER_PORTS, repo_root)
        record_assert(
            "all_ports_unbound_during_full_restart_gap",
            all(len(ports_mid_restart[str(p)]) == 0 for p in REVIEWER_PORTS),
            ports_mid_restart,
        )

        run_logged_step(
            "13-pg-cluster-start-after-restart",
            ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"],
        )
        pm_pid_after = int((pg_data_dir / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        pm_info_after = inspect_process(pm_pid_after, repo_root)
        spawned_processes.append({"role": "postmaster_after_restart", "info": pm_info_after})

        active_api_proc, active_api_info = start_owned_api(
            api_dll=api_dll,
            port=API_PORT,
            settings=settings,
            database=MIGRATED_DB,
            log_path=logs_dir / "owned-api-5690-after-restart.log",
            cwd=repo_root,
        )
        active_ui_proc, active_ui_info = start_owned_ui(
            node_exe=node_exe,
            ui_port=UI_PORT,
            api_port=API_PORT,
            log_path=logs_dir / "owned-ui-4710-after-restart.log",
            repo_root=repo_root,
        )

        queries_after_restart = run_saved_archive_query_suite(API_PORT)
        run_logged_step(
            "14-edge-f4-after-restart-reopen",
            [
                str(node_exe),
                str(edge_helper),
                "--phase",
                "after-restart",
                "--ui-port",
                str(UI_PORT),
                "--api-port",
                str(API_PORT),
                "--output",
                args.edge_after_output,
                "--screenshot-dir",
                args.screenshots_dir,
            ],
            timeout_s=240,
        )

        ui_after_stop = stop_owned_process(active_ui_proc, active_ui_info, repo_root)
        api_after_stop = stop_owned_process(active_api_proc, active_api_info, repo_root)
        spawned_processes.append({"role": "ui_4710_after_restart", "stop": ui_after_stop})
        spawned_processes.append({"role": "api_5690_after_restart", "stop": api_after_stop})
        active_ui_proc, active_ui_info = None, None
        active_api_proc, active_api_info = None, None

        migrated_after_restart = compute_canonical_8table_snapshot(psql_exe, settings, MIGRATED_DB, repo_root)
        proj_after_restart = compute_projection_tables_snapshot(psql_exe, settings, MIGRATED_DB, repo_root)
        seed_after_all = compute_canonical_8table_snapshot(psql_exe, settings, SEED_DB, repo_root)

        record_assert(
            "restart_invariance_verified_for_queries_projections_8tables_and_seed_f3",
            (
                queries_before_restart["saved_queries_sha256"] == queries_after_restart["saved_queries_sha256"]
                and proj_before_restart["projection_tables_sha256"] == proj_after_restart["projection_tables_sha256"]
                and migrated_after_restart["canonical_8table_sha256"] == EXPECTED_REVIEWER_SEED_8TABLE_SHA256
                and seed_after_all["canonical_8table_sha256"] == EXPECTED_REVIEWER_SEED_8TABLE_SHA256
                and migrated_after_restart["counts"]["execution_attempts"] == 9
            ),
            {
                "saved_queries_sha256": queries_after_restart["saved_queries_sha256"],
                "projection_tables_sha256": proj_after_restart["projection_tables_sha256"],
                "migrated_8table_sha256": migrated_after_restart["canonical_8table_sha256"],
                "retained_seed_f3_sha256": seed_after_all["canonical_8table_sha256"],
                "execution_attempts_unchanged": migrated_after_restart["counts"]["execution_attempts"],
            },
        )

        # ---------------------------------------------------------------------
        # Step 10: Isolated scratch-DB live HTTP probe for malformed-table/NUL/unbound
        #          fallbacks AND 503 archive_projection_conflict
        # ---------------------------------------------------------------------
        run_logged_step(
            "15-prepare-scratch-fallback-probe-db",
            ["pwsh", "-NoProfile", "-File", "deploy/dev/database/prepare-database.ps1", "-Database", PROBE_DB],
            step_env=dotnet_env,
        )
        try:
            f1_bytes = (repo_root / "tests/fixtures/F1-SWO-001.pdf").read_bytes()
            f1_hex = f1_bytes.hex()
            dummy_sha = "11" * 32

            # Doc A: 1-page result with <caption> table + missing-<FORK> block + embedded NUL + >10k chars tail
            mal_raw = (
                "<PAGE>\n"
                "<BLOCK>table[[1,1,50,50]]<FORK><table><caption>CAPTION-FALLBACK-701</caption><tr><td>CellOK701</td></tr></table>\n"
                "<BLOCK>RAW-NO-FORK-702\n"
                "<BLOCK>text[[1,60,50,80]]<FORK>" + ("M" * 9000) + "\x00TAIL-AFTER-NUL-703\n"
            ).encode("utf-8")
            mal_sha = sha256_hex(mal_raw)

            # Doc B: 2-page admitted result whose raw output has NO <PAGE> markers -> document_fallback (pageNumber=null)
            unb_raw = b"UNBOUND-DOC-FALLBACK-704 without any page markers"
            unb_sha = sha256_hex(unb_raw)

            probe_seed_sql = f"""
BEGIN;
SET LOCAL synchronous_commit = on;
SELECT nextval('eledgercare.extraction_fencing_seq');
INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
VALUES ('01a20900-0000-7000-8000-000000000001', '01a20900-1000-7000-8000-000000000001', '2026-11-17T09:00:00Z');

INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
VALUES ('01a20900-0000-7000-8000-000000000001', decode('{f1_hex}', 'hex'), decode('{F1_PDF_SHA256}', 'hex'), {len(f1_bytes)}, 'application/pdf', 1);

INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at, queued_at, updated_at, attempt_count, latest_fencing_token, retried_from_attempt_id)
VALUES ('01a20900-2000-7000-8000-000000000001', '01a20900-0000-7000-8000-000000000001', 'completed', '2026-11-17T09:00:00Z', '2026-11-17T09:00:01Z', '2026-11-17T09:00:02Z', 1, currval('eledgercare.extraction_fencing_seq'), NULL);

INSERT INTO eledgercare.execution_attempts (attempt_id, job_id, document_id, attempt_number, fencing_token, status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime, started_at, last_heartbeat_at, ended_at, exit_code)
VALUES ('01a20900-3000-7000-8000-000000000001', '01a20900-2000-7000-8000-000000000001', '01a20900-0000-7000-8000-000000000001', 1, currval('eledgercare.extraction_fencing_seq'), 'completed', 'completed', 'attempt-probe-1', '01a1e571-0000-7000-8000-000000018496', 18496, 134393243591895019, '2026-11-17T09:00:01Z', '2026-11-17T09:00:02Z', '2026-11-17T09:00:02Z', 0);

INSERT INTO eledgercare.extraction_results (
  result_id, document_id, job_id, attempt_id, fencing_token, schema_version,
  input_sha256, input_byte_length, page_count, raw_output_bytes, raw_output_byte_length, raw_output_sha256,
  model_repo_id, model_revision, model_manifest_sha256, dependency_lock_sha256, worker_source_digest, worker_config_digest,
  renderer_identity, generation_settings_json, finish_reason, output_page_count,
  started_at, completed_at, load_duration_ms, render_duration_ms, infer_duration_ms, total_duration_ms, diagnostic_metadata_json
) VALUES (
  '01a20900-4000-7000-8000-000000000001', '01a20900-0000-7000-8000-000000000001', '01a20900-2000-7000-8000-000000000001', '01a20900-3000-7000-8000-000000000001',
  currval('eledgercare.extraction_fencing_seq'), 'eledgercare.local-extraction/1',
  decode('{F1_PDF_SHA256}', 'hex'), {len(f1_bytes)}, 1, decode('{mal_raw.hex()}', 'hex'), {len(mal_raw)}, decode('{mal_sha}', 'hex'),
  'baidu/Unlimited-OCR-2', '0480966938291445591f69f08a13b041c073a96a',
  decode('{dummy_sha}', 'hex'), decode('{dummy_sha}', 'hex'), decode('{dummy_sha}', 'hex'), decode('{dummy_sha}', 'hex'),
  'pypdfium2', '{{}}'::jsonb, 'stop', 1, '2026-11-17T09:00:01Z', '2026-11-17T09:00:02Z', 5, 5, 10, 20, '{{}}'::jsonb
);

SELECT nextval('eledgercare.extraction_fencing_seq');
INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
VALUES ('01a20900-0000-7000-8000-000000000002', '01a20900-1000-7000-8000-000000000002', '2026-11-17T09:01:00Z');

INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
VALUES ('01a20900-0000-7000-8000-000000000002', decode('{f1_hex}', 'hex'), decode('{F1_PDF_SHA256}', 'hex'), {len(f1_bytes)}, 'application/pdf', 2);

INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at, queued_at, updated_at, attempt_count, latest_fencing_token, retried_from_attempt_id)
VALUES ('01a20900-2000-7000-8000-000000000002', '01a20900-0000-7000-8000-000000000002', 'completed', '2026-11-17T09:01:00Z', '2026-11-17T09:01:01Z', '2026-11-17T09:01:02Z', 1, currval('eledgercare.extraction_fencing_seq'), NULL);

INSERT INTO eledgercare.execution_attempts (attempt_id, job_id, document_id, attempt_number, fencing_token, status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime, started_at, last_heartbeat_at, ended_at, exit_code)
VALUES ('01a20900-3000-7000-8000-000000000002', '01a20900-2000-7000-8000-000000000002', '01a20900-0000-7000-8000-000000000002', 1, currval('eledgercare.extraction_fencing_seq'), 'completed', 'completed', 'attempt-probe-2', '01a1e571-0000-7000-8000-000000018496', 18496, 134393243591895019, '2026-11-17T09:01:01Z', '2026-11-17T09:01:02Z', '2026-11-17T09:01:02Z', 0);

INSERT INTO eledgercare.extraction_results (
  result_id, document_id, job_id, attempt_id, fencing_token, schema_version,
  input_sha256, input_byte_length, page_count, raw_output_bytes, raw_output_byte_length, raw_output_sha256,
  model_repo_id, model_revision, model_manifest_sha256, dependency_lock_sha256, worker_source_digest, worker_config_digest,
  renderer_identity, generation_settings_json, finish_reason, output_page_count,
  started_at, completed_at, load_duration_ms, render_duration_ms, infer_duration_ms, total_duration_ms, diagnostic_metadata_json
) VALUES (
  '01a20900-4000-7000-8000-000000000002', '01a20900-0000-7000-8000-000000000002', '01a20900-2000-7000-8000-000000000002', '01a20900-3000-7000-8000-000000000002',
  currval('eledgercare.extraction_fencing_seq'), 'eledgercare.local-extraction/1',
  decode('{F1_PDF_SHA256}', 'hex'), {len(f1_bytes)}, 2, decode('{unb_raw.hex()}', 'hex'), {len(unb_raw)}, decode('{unb_sha}', 'hex'),
  'baidu/Unlimited-OCR-2', '0480966938291445591f69f08a13b041c073a96a',
  decode('{dummy_sha}', 'hex'), decode('{dummy_sha}', 'hex'), decode('{dummy_sha}', 'hex'), decode('{dummy_sha}', 'hex'),
  'pypdfium2', '{{}}'::jsonb, 'stop', 2, '2026-11-17T09:01:01Z', '2026-11-17T09:01:02Z', 5, 5, 10, 20, '{{}}'::jsonb
);
COMMIT;
"""
            invoke_psql(
                psql_exe,
                host=settings["host"],
                port=PG_PORT,
                user=settings["appUser"],
                password=settings["appPassword"],
                database=PROBE_DB,
                sql=probe_seed_sql,
                cwd=repo_root,
            )

            active_api_proc, active_api_info = start_owned_api(
                api_dll=api_dll,
                port=API_PORT,
                settings=settings,
                database=PROBE_DB,
                log_path=logs_dir / "owned-api-5690-fallback-probe.log",
                cwd=repo_root,
            )
            _, _, hit_cap = http_get_json(API_PORT, "/api/archive?q=CAPTION-FALLBACK-701")
            _, _, hit_nofork = http_get_json(API_PORT, "/api/archive?q=RAW-NO-FORK-702")
            _, _, hit_nul = http_get_json(API_PORT, "/api/archive?q=TAIL-AFTER-NUL-703")
            _, _, hit_unb = http_get_json(API_PORT, "/api/archive?q=UNBOUND-DOC-FALLBACK-704")

            probe_stop_1 = stop_owned_process(active_api_proc, active_api_info, repo_root)
            spawned_processes.append({"role": "api_5690_fallback_probe", "stop": probe_stop_1})
            active_api_proc, active_api_info = None, None

            record_assert(
                "live_http_fallback_caption_nofork_nul_and_unbound_page_verified",
                (
                    len(hit_cap["items"]) == 1
                    and hit_cap["items"][0]["witnesses"][0]["isFallback"] is True
                    and hit_cap["items"][0]["witnesses"][0]["pageNumber"] == 1
                    and len(hit_nofork["items"]) == 1
                    and len(hit_nul["items"]) == 1
                    and len(hit_unb["items"]) == 1
                    and hit_unb["items"][0]["witnesses"][0]["isFallback"] is True
                    and hit_unb["items"][0]["witnesses"][0]["pageNumber"] is None
                ),
                {"unbound_page_number": hit_unb["items"][0]["witnesses"][0]["pageNumber"]},
            )

            # Tamper projection_sha256 as admin and verify live HTTP 503 archive_projection_conflict!
            invoke_psql(
                psql_exe,
                host=settings["host"],
                port=PG_PORT,
                user=settings["adminUser"],
                password=settings["adminPassword"],
                database=PROBE_DB,
                sql="UPDATE eledgercare.archive_result_projections SET projection_sha256 = decode(repeat('aa', 32), 'hex') WHERE result_id = '01a20900-4000-7000-8000-000000000001';",
                cwd=repo_root,
            )
            active_api_proc, active_api_info = start_owned_api(
                api_dll=api_dll,
                port=API_PORT,
                settings=settings,
                database=PROBE_DB,
                log_path=logs_dir / "owned-api-5690-conflict-503.log",
                cwd=repo_root,
            )
            st_conf, _, body_conf = http_get_json(API_PORT, "/api/archive?q=CellOK701")
            st_doc_ok, _, _ = http_get_json(API_PORT, "/api/documents/01a20900-0000-7000-8000-000000000001")
            probe_stop_2 = stop_owned_process(active_api_proc, active_api_info, repo_root)
            spawned_processes.append({"role": "api_5690_conflict_503", "stop": probe_stop_2})
            active_api_proc, active_api_info = None, None

            record_assert(
                "live_http_503_archive_projection_conflict_preserves_document_endpoint",
                st_conf == 503 and body_conf.get("code") == "archive_projection_conflict" and st_doc_ok == 200,
                {"archive_status": st_conf, "code": body_conf.get("code"), "doc_status": st_doc_ok},
            )
        finally:
            invoke_psql(
                psql_exe,
                host=settings["host"],
                port=PG_PORT,
                user=settings["adminUser"],
                password=settings["adminPassword"],
                database="postgres",
                sql=f"DROP DATABASE IF EXISTS {PROBE_DB} WITH (FORCE);",
                cwd=repo_root,
            )

        # Final Stop of owned PostgreSQL 55439
        run_logged_step(
            "16-pg-cluster-stop-final",
            ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"],
        )

    finally:
        if active_ui_proc is not None:
            stop_owned_process(active_ui_proc, active_ui_info, repo_root)
        if active_api_proc is not None:
            stop_owned_process(active_api_proc, active_api_info, repo_root)
        # Ensure PG cluster is stopped even on error
        if (pg_data_dir / "postmaster.pid").exists():
            run_cmd(["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"], cwd=repo_root)

        for lf in logs_dir.glob("*.log"):
            cleaned = redact_secrets(lf.read_text(encoding="utf-8", errors="replace"), secrets)
            lf.write_text(cleaned.replace("\r\n", "\n"), encoding="utf-8", newline="\n")

    # -------------------------------------------------------------------------
    # Step 11: Final shutdown, port-release, and secret-redaction verification
    # -------------------------------------------------------------------------
    pg_status_cp = run_cmd([str(pg_ctl_exe), "status", "-D", str(pg_data_dir)], cwd=repo_root)
    ports_after = observe_ports(REVIEWER_PORTS, repo_root)
    record_assert(
        "all_owned_services_stopped_and_ports_5690_4710_55439_released",
        (
            pg_status_cp.returncode == 3
            and all(len(ports_after[str(p)]) == 0 for p in REVIEWER_PORTS)
            and (pg_data_dir / "PG_VERSION").exists()
        ),
        {
            "pg_ctl_status_exit": pg_status_cp.returncode,
            "ports_after": ports_after,
            "postgres_data_retained": True,
        },
    )

    edge_script = repo_root / "docs/reviews/WP-0010/eld-f4-reviewer/runtime/helpers/verify_f4_independent_edge.mjs"
    inv_script = repo_root / "docs/reviews/WP-0010/eld-f4-reviewer/runtime/helpers/build_runtime_review_inventory.py"

    summary_payload = {
        "schema": "eledgercare.wp-0010.reviewer-f4-runtime-verification-summary/1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "conversation_id": "61105d43-7706-45f2-9176-69d3256248e0",
        "branch": branch_name,
        "executing_head_sha": head_sha,
        "design_candidate_sha": DESIGN_CANDIDATE_SHA,
        "prior_design_002_sha": PRIOR_DESIGN_002_SHA,
        "reviewer_preparation_sha": REVIEWER_PREP_SHA,
        "root_runtime_authority_sha": ROOT_RUNTIME_AUTHORITY_SHA,
        "author_revisions": {
            "base_sha": AUTHOR_BASE_SHA,
            "first_helper_candidate_sha": AUTHOR_FIRST_FROZEN_SHA,
            "tested_candidate_sha": AUTHOR_CANDIDATE_SHA,
            "evidence_sha": AUTHOR_EVIDENCE_SHA,
            "report_003_publication_sha": AUTHOR_003_PUB_SHA,
        },
        "verified_product_trees": EXPECTED_PRODUCT_TREES,
        "tool_versions": tool_versions,
        "helpers": {
            "run_f4_independent_review_py_sha256": sha256_hex(script_path.read_bytes().replace(b"\r\n", b"\n")),
            "verify_f4_independent_edge_mjs_sha256": sha256_hex(edge_script.read_bytes().replace(b"\r\n", b"\n")),
            "build_runtime_review_inventory_py_sha256": sha256_hex(inv_script.read_bytes().replace(b"\r\n", b"\n")),
        },
        "retained_seed_preservation": {
            "database": SEED_DB,
            "expected_8table_sha256": EXPECTED_REVIEWER_SEED_8TABLE_SHA256,
            "observed_before_sha256": seed_before["canonical_8table_sha256"],
            "observed_after_sha256": seed_after_all["canonical_8table_sha256"],
            "unchanged": True,
        },
        "forward_migration_and_restart": {
            "migrated_database": MIGRATED_DB,
            "applied_migrations": applied_migrations,
            "core_8table_sha256_before_migration": clone_pre_mig["canonical_8table_sha256"],
            "core_8table_sha256_after_migration": clone_post_mig["canonical_8table_sha256"],
            "core_8table_sha256_after_restart": migrated_after_restart["canonical_8table_sha256"],
            "projection_count": proj_after_restart["projection_count"],
            "projection_unit_count": proj_after_restart["unit_count"],
            "projection_tables_sha256_before_restart": proj_before_restart["projection_tables_sha256"],
            "projection_tables_sha256_after_restart": proj_after_restart["projection_tables_sha256"],
            "saved_queries_sha256_before_restart": queries_before_restart["saved_queries_sha256"],
            "saved_queries_sha256_after_restart": queries_after_restart["saved_queries_sha256"],
            "postmaster_pid_before_restart": pm_pid_mid,
            "postmaster_pid_after_restart": pm_pid_after,
            "execution_attempts_count_unchanged": 9,
        },
        "modest_archive_measurements": modest_metrics,
        "logged_steps": step_receipts,
        "assertion_count": len(assertions),
        "all_assertions_passed": True,
        "assertions": assertions,
        "zero_gpu_or_ocr_worker_processes": True,
    }

    resource_return = {
        "schema": "eledgercare.wp-0010.reviewer-runtime-resource-return/1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "owned_ports": {"api": API_PORT, "ui": UI_PORT, "postgres": PG_PORT},
        "ports_before": ports_before,
        "ports_after": ports_after,
        "pg_ctl_status_exit_after_stop": pg_status_cp.returncode,
        "spawned_processes": spawned_processes,
        "retained_databases_on_disk": [
            {
                "database": SEED_DB,
                "role": "untouched pre-F4 F3 baseline seed",
                "canonical_8table_sha256": seed_after_all["canonical_8table_sha256"],
            },
            {
                "database": MIGRATED_DB,
                "role": "forward-migrated + backfilled F4 verification database",
                "canonical_8table_sha256": migrated_after_restart["canonical_8table_sha256"],
                "projection_tables_sha256": proj_after_restart["projection_tables_sha256"],
            },
            {
                "database": E2E_DB,
                "role": "Playwright Microsoft Edge E2E database (5690/4710)",
            },
        ],
        "dropped_temporary_databases": [PROBE_DB],
        "credentials_gitignored": True,
        "gpu_or_model_processes_started": 0,
    }

    out_summary_path = (repo_root / args.output).resolve()
    out_return_path = (repo_root / args.resource_return_output).resolve()
    out_summary_path.parent.mkdir(parents=True, exist_ok=True)
    out_return_path.parent.mkdir(parents=True, exist_ok=True)

    summary_str = json.dumps(summary_payload, indent=2, ensure_ascii=False) + "\n"
    return_str = json.dumps(resource_return, indent=2, ensure_ascii=False) + "\n"

    assert_no_secrets(summary_str, secrets, str(out_summary_path))
    assert_no_secrets(return_str, secrets, str(out_return_path))
    assert_no_secrets(explain_out_path.read_text(encoding="utf-8"), secrets, str(explain_out_path))
    for log_f in logs_dir.glob("*.log"):
        assert_no_secrets(log_f.read_text(encoding="utf-8"), secrets, str(log_f))

    out_summary_path.write_text(summary_str, encoding="utf-8", newline="\n")
    out_return_path.write_text(return_str, encoding="utf-8", newline="\n")

    print(
        f"PASS: {len(step_receipts)} steps & {len(assertions)} assertions verified; "
        f"seed_f3={seed_after_all['canonical_8table_sha256'][:12]}...; "
        f"projections={proj_after_restart['projection_tables_sha256'][:12]}...; "
        f"saved_queries={queries_after_restart['saved_queries_sha256'][:12]}...; "
        f"ports {REVIEWER_PORTS} FREE."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
