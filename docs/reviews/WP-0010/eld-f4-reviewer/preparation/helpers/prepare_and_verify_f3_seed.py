"""Frozen decisive helper for WP-0010 independent reviewer F4 resource preparation.

Operates strictly on owned reviewer resources (PostgreSQL 18.7 on 127.0.0.1:55439, unchanged pre-F4
ELedgerCare.Api on 127.0.0.1:5690 with LocalOcr:Enabled=false, and read-only Angular/Edge verification
on 127.0.0.1:4710). Independently constructs the 9-document pre-F4 F3 baseline in retained database
`eledgercare_f4_reviewer_seed_f3` combining attributed genuine WP-0006 F2 reviewer extraction artifacts
with real live F1/F3 HTTP API submissions and review revisions, verifies current-head vs. historical
latest-reviewed distinctions, least-privilege denials, Edge PDF/history rendering, and canonical 8-table
digest invariance, then stops all owned services cleanly while retaining `eledgercare_f4_reviewer_seed_f3`
on disk for later WP-0010 /004 forward-migration and F4 acceptance verification.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time
import zlib

API_PORT = 5690
UI_PORT = 4710
PG_PORT = 55439
REVIEWER_PORTS = (API_PORT, UI_PORT, PG_PORT)
SEED_DATABASE = "eledgercare_f4_reviewer_seed_f3"

EXPECTED_SUBSET_SHA = "47c3deb9c917f79c353b3683b2c2611ee975285ea06226c8f72444c96ce9051f"
EXPECTED_CD_SHA = "3132ca63b424f7ec371eabe50753ad7cd036278d942a6ea465547b17bf90a149"
EXPECTED_PG_FILES = 1597
EXPECTED_PG_BYTES = 151_078_582

PRIOR_DESIGN_002_SHA = "85d879a1adc0ee62090f4c6a5c9a7fb8eb5f3a96"
AUTHORITY_PREP_SHA = "7345ef03dfa4d5f039259d0b8b9505685112469d"
ACCEPTED_F3_SOURCE_SHA = "dda4b4d5856ac45105c31ba1d6d6813debdab8a7"
F2_SOURCE_SHA = "8a73b7a5dab51e3ccf803aceedded4929529dd35"
F2_EXECUTING_HEAD_SHA = "b343f6ff78aa41332ecbe957577b6776f8edc22f"
F2_REVIEWER_EVIDENCE_SHA = "7f0ec3a9338606ce54c4c6d2eeabab8a2c245e2a"
F2_REVIEWER_004_SHA = "c854a1d4c306c3b10d78df42a1a2552a06bb4a98"

F01_PDF_SHA256 = "47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd"
F01_RAW_SHA256 = "7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95"
F07_PDF_SHA256 = "15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3"
F07_RAW_SHA256 = "c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639"
F1_PDF_SHA256 = "875a2d8c83c1c1002b38840f8136b60bd5ebcfe8d2df47187bf36454c59497cb"

SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID = "01a1e571-0000-7000-8000-000000018496"
SYNTHESIZED_SUPERVISOR_RUN2_INSTANCE_ID = "01a1e578-0000-7000-8000-000000029208"

PRESERVED_TREE_PATHS = (
    "src",
    "tests",
    "web",
    "deploy",
    "ELedgerCare.slnx",
    "workers",
    "evaluation",
    "qualification",
    "research",
)

FORBIDDEN_PATH_TOKENS = (
    "eld-f4-implementer",
    "eledgercare-mapping",
    "eledgercare-coverage",
    "wp-0009/sealed",
    "wp-0009\\sealed",
    "wp-0009-fresh-families",
    "wp-0011-diagnostic-families",
    "eld-coverage-custodian",
    "eld-coverage-author",
    "eld-coverage-reviewer",
    "docs/evaluation/wp-0011",
    "docs\\evaluation\\wp-0011",
    "docs/reviews/wp-0011",
    "docs\\reviews\\wp-0011",
    "docs/kickoffs/wp-0011",
    "docs\\kickoffs\\wp-0011",
    "eledgercare-f2",
)
REPARSE_ATTR = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


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


def is_reparse_or_link(path: Path) -> bool:
    st = os.lstat(path)
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & REPARSE_ATTR)


def guard_owned_repo_path(repo_root: Path, rel_path: str) -> Path:
    target = (repo_root / rel_path).resolve()
    norm = str(target).lower()
    for bad in FORBIDDEN_PATH_TOKENS:
        if bad in norm:
            raise PermissionError(f"Refusing forbidden path: {target}")
    target.relative_to(repo_root.resolve())
    return target


def run_cmd(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    timeout_s: int = 240,
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
    cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps_script], cwd=cwd)
    if cp.returncode != 0:
        raise RuntimeError(f"Port observation failed: {cp.stderr}")
    return json.loads(cp.stdout)


def inspect_process(pid: int, cwd: Path) -> dict | None:
    ps = (
        f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
        "if ($null -eq $p) { 'null' } else { "
        "@{ pid = [int]$p.Id; name = $p.ProcessName; startUtc = $p.StartTime.ToUniversalTime().ToString('o') } | ConvertTo-Json -Compress }"
    )
    cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps], cwd=cwd)
    if cp.returncode != 0 or cp.stdout.strip() == "null":
        return None
    return json.loads(cp.stdout)


def stop_owned_process(proc: subprocess.Popen[bytes] | None, recorded_info: dict | None, cwd: Path) -> dict:
    if proc is None or recorded_info is None:
        return {"stopped": False, "reason": "not_started"}
    pid = recorded_info["pid"]
    expected_start = recorded_info["startUtc"]
    if proc.poll() is not None:
        return {"pid": pid, "startUtc": expected_start, "alreadyExitedCode": proc.returncode, "aliveAfter": False}
    cur = inspect_process(pid, cwd)
    if cur is None:
        return {"pid": pid, "startUtc": expected_start, "aliveAfter": False}
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


def verify_pg_subset(local_tools: Path, cwd: Path) -> dict:
    manifest_path = local_tools / "pgsql-18.7-1.subset-manifest.json"
    pg_root = local_tools / "pgsql-18.7-1"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    present_files: list[str] = []
    reparse_points: list[str] = []
    for dirpath, dirnames, filenames in os.walk(pg_root, followlinks=False):
        for dname in list(dirnames):
            dp = Path(dirpath) / dname
            if is_reparse_or_link(dp):
                reparse_points.append(dp.relative_to(pg_root).as_posix())
                dirnames.remove(dname)
        for fname in filenames:
            fp = Path(dirpath) / fname
            rel = fp.relative_to(pg_root).as_posix()
            present_files.append(rel)
            if is_reparse_or_link(fp):
                reparse_points.append(rel)

    expected_by_path = {e["path"]: e for e in manifest["files"]}
    missing = sorted(set(expected_by_path) - set(present_files))
    extra = sorted(set(present_files) - set(expected_by_path))
    mismatches: list[str] = []
    total_bytes = 0
    lines: list[str] = []
    for rel in sorted(expected_by_path):
        if rel in missing:
            continue
        exp = expected_by_path[rel]
        data = (pg_root / rel).read_bytes()
        sha = sha256_hex(data)
        crc = f"{zlib.crc32(data) & 0xFFFFFFFF:08x}"
        if len(data) != exp["bytes"] or sha != exp["sha256"] or crc != exp["crc32"]:
            mismatches.append(rel)
        total_bytes += len(data)
        lines.append(f"{sha}  {rel}")

    recomputed_subset_sha = sha256_hex("\n".join(lines).encode("utf-8"))
    versions = {}
    for exe in ("postgres.exe", "pg_ctl.exe", "initdb.exe", "psql.exe"):
        cp = run_cmd([str(pg_root / "bin" / exe), "--version"], cwd=cwd)
        if cp.returncode != 0:
            raise RuntimeError(f"{exe} --version failed: {cp.stderr}")
        versions[exe] = cp.stdout.strip()

    sig_ps = (
        f"(Get-AuthenticodeSignature -FilePath '{pg_root / 'bin' / 'postgres.exe'}').Status.ToString()"
    )
    sig_cp = run_cmd(["pwsh", "-NoProfile", "-Command", sig_ps], cwd=cwd)
    authenticode = sig_cp.stdout.strip()

    return {
        "file_count": len(present_files),
        "total_bytes": total_bytes,
        "missing_files": missing,
        "extra_files": extra,
        "mismatched_files": mismatches,
        "reparse_points": reparse_points,
        "subset_manifest_sha256": recomputed_subset_sha,
        "central_directory_sha256": manifest.get("central_directory_sha256"),
        "authenticode_status": authenticode,
        "versions": versions,
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
    cp = run_cmd(args, cwd=cwd, env=env, input_text=sql)
    if expect_success and cp.returncode != 0:
        raise RuntimeError(f"psql failed as {user} on {database} (exit {cp.returncode}): {cp.stderr}")
    return cp


def sql_lit(val: str | None) -> str:
    if val is None:
        return "NULL"
    escaped = val.replace("'", "''")
    return f"'{escaped}'"


def http_request(
    port: int,
    method: str,
    path_str: str,
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
        conn.request(method, path_str, body=body, headers=req_headers)
        resp = conn.getresponse()
        raw = resp.read()
        hdrs = {k.lower(): v for k, v in resp.getheaders()}
        return resp.status, hdrs, raw
    finally:
        conn.close()


def http_json(
    port: int,
    method: str,
    path_str: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict | None = None,
) -> tuple[int, dict[str, str], dict]:
    hdrs = dict(headers or {})
    raw_body = None
    if json_body is not None:
        raw_body = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    st, resp_hdrs, resp_bytes = http_request(port, method, path_str, headers=hdrs, body=raw_body)
    parsed = json.loads(resp_bytes.decode("utf-8")) if resp_bytes else {}
    return st, resp_hdrs, parsed


def build_single_attempt_seed_sql(
    *,
    document_id: str,
    idempotency_key: str,
    submitted_at_utc: str,
    pdf_bytes: bytes,
    pdf_sha_hex: str,
    page_count: int,
    job_id: str,
    queued_at_utc: str,
    attempt_id: str,
    supervisor_instance_id: str,
    supervisor_pid: int,
    supervisor_ft: int,
    launcher_pid: int,
    launcher_ft: int,
    worker_pid: int,
    worker_ft: int,
    attempt_started_utc: str,
    attempt_ended_utc: str,
    result_id: str,
    raw_bytes: bytes,
    raw_sha_hex: str,
    envelope: dict,
) -> str:
    prov = envelope["provenance"]
    timings = envelope["timings"]
    gen_json = json.dumps(prov["generation_settings"], sort_keys=True, separators=(",", ":"))
    diag_json = json.dumps(envelope["diagnostics"], sort_keys=True, separators=(",", ":"))
    pdf_hex = pdf_bytes.hex()
    raw_hex = raw_bytes.hex()

    return f"""
BEGIN;
SET LOCAL synchronous_commit = on;
SELECT nextval('eledgercare.extraction_fencing_seq');

INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
VALUES ('{document_id}', '{idempotency_key}', '{submitted_at_utc}'::timestamptz);

INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
VALUES ('{document_id}', decode('{pdf_hex}', 'hex'), decode('{pdf_sha_hex}', 'hex'), {len(pdf_bytes)}, 'application/pdf', {page_count});

INSERT INTO eledgercare.processing_jobs (
  job_id, document_id, status, requested_at, queued_at, updated_at, attempt_count, latest_fencing_token, retried_from_attempt_id
) VALUES (
  '{job_id}', '{document_id}', 'completed', '{submitted_at_utc}'::timestamptz, '{queued_at_utc}'::timestamptz,
  '{attempt_ended_utc}'::timestamptz, 1, currval('eledgercare.extraction_fencing_seq'), NULL
);

INSERT INTO eledgercare.execution_attempts (
  attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
  status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
  launcher_pid, launcher_create_filetime, worker_pid, worker_create_filetime,
  started_at, last_heartbeat_at, ended_at, exit_code, failure_code, failure_detail,
  diagnostic_raw_output_utf8, diagnostic_metadata_json
) VALUES (
  '{attempt_id}', '{job_id}', '{document_id}', 1, currval('eledgercare.extraction_fencing_seq'), NULL,
  'completed', 'completed', 'attempt-{attempt_id}', '{supervisor_instance_id}', {supervisor_pid}, {supervisor_ft},
  {launcher_pid}, {launcher_ft}, {worker_pid}, {worker_ft},
  '{attempt_started_utc}'::timestamptz, '{attempt_ended_utc}'::timestamptz, '{attempt_ended_utc}'::timestamptz,
  0, NULL, NULL, NULL, NULL
);

INSERT INTO eledgercare.extraction_results (
  result_id, document_id, job_id, attempt_id, fencing_token, schema_version,
  input_sha256, input_byte_length, page_count, raw_output_bytes, raw_output_byte_length, raw_output_sha256,
  model_repo_id, model_revision, model_manifest_sha256, dependency_lock_sha256, worker_source_digest, worker_config_digest,
  renderer_identity, generation_settings_json, finish_reason, output_page_count,
  started_at, completed_at, load_duration_ms, render_duration_ms, infer_duration_ms, total_duration_ms, diagnostic_metadata_json
) VALUES (
  '{result_id}', '{document_id}', '{job_id}', '{attempt_id}', currval('eledgercare.extraction_fencing_seq'), 'eledgercare.local-extraction/1',
  decode('{pdf_sha_hex}', 'hex'), {len(pdf_bytes)}, {page_count}, decode('{raw_hex}', 'hex'), {len(raw_bytes)}, decode('{raw_sha_hex}', 'hex'),
  {sql_lit(prov['model_repo_id'])}, {sql_lit(prov['model_revision'])},
  decode('{prov['model_manifest_sha256']}', 'hex'),
  decode('{prov['dependency_lock_sha256']}', 'hex'),
  decode('{prov['worker_source_sha256']}', 'hex'),
  decode('{prov['worker_config_sha256']}', 'hex'),
  {sql_lit(prov['renderer_identity'])}, {sql_lit(gen_json)}::jsonb, 'stop', {page_count},
  '{timings['started_at_utc']}'::timestamptz, '{timings['completed_at_utc']}'::timestamptz,
  {int(timings['load_duration_ms'])}, {int(timings['render_duration_ms'])}, {int(timings['infer_duration_ms'])}, {int(timings['total_duration_ms'])},
  {sql_lit(diag_json)}::jsonb
);
COMMIT;
"""


def build_scenario3_retry_seed_sql(
    *,
    scen3: dict,
    pdf_bytes: bytes,
    pdf_sha_hex: str,
    raw_bytes: bytes,
    raw_sha_hex: str,
    envelope: dict,
) -> str:
    sub = scen3["submission"]
    rec = sub["receipt"]
    doc_id = rec["documentId"]
    job_id = rec["jobId"]
    idem_key = sub["idempotency_key"]
    submitted_utc = rec["submittedAtUtc"]
    queued1_utc = scen3["reconciled_interrupted_view"]["queuedAtUtc"]
    att1 = scen3["retry_completion"]["db_attempts"][0]
    att2 = scen3["retry_completion"]["db_attempts"][1]
    res_id = scen3["retry_completion"]["db_result"]["result_id"]
    prov = envelope["provenance"]
    timings = envelope["timings"]
    gen_json = json.dumps(prov["generation_settings"], sort_keys=True, separators=(",", ":"))
    diag_json = json.dumps(envelope["diagnostics"], sort_keys=True, separators=(",", ":"))
    pdf_hex = pdf_bytes.hex()
    raw_hex = raw_bytes.hex()

    return f"""
BEGIN;
SET LOCAL synchronous_commit = on;
SELECT nextval('eledgercare.extraction_fencing_seq');

INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
VALUES ('{doc_id}', '{idem_key}', '{submitted_utc}'::timestamptz);

INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
VALUES ('{doc_id}', decode('{pdf_hex}', 'hex'), decode('{pdf_sha_hex}', 'hex'), {len(pdf_bytes)}, 'application/pdf', 1);

INSERT INTO eledgercare.processing_jobs (
  job_id, document_id, status, requested_at, queued_at, updated_at, attempt_count, latest_fencing_token, retried_from_attempt_id
) VALUES (
  '{job_id}', '{doc_id}', 'interrupted', '{submitted_utc}'::timestamptz, '{queued1_utc}'::timestamptz,
  '{att1['ended_at']}'::timestamptz, 1, currval('eledgercare.extraction_fencing_seq'), NULL
);

INSERT INTO eledgercare.execution_attempts (
  attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
  status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
  launcher_pid, launcher_create_filetime, worker_pid, worker_create_filetime,
  started_at, last_heartbeat_at, ended_at, exit_code, failure_code, failure_detail
) VALUES (
  '{att1['attempt_id']}', '{job_id}', '{doc_id}', 1, currval('eledgercare.extraction_fencing_seq'), NULL,
  'interrupted', 'interrupted', {sql_lit(att1['run_directory_name'])}, '{SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID}',
  {att1['supervisor_pid']}, {att1['supervisor_create_filetime']},
  {att1['launcher_pid']}, {att1['launcher_create_filetime']},
  {att1['worker_pid']}, {att1['worker_create_filetime']},
  '{att1['started_at']}'::timestamptz, '{att1['ended_at']}'::timestamptz, '{att1['ended_at']}'::timestamptz,
  NULL, {sql_lit(att1['failure_code'])}, {sql_lit(att1['failure_detail'])}
);

SELECT nextval('eledgercare.extraction_fencing_seq');

UPDATE eledgercare.processing_jobs
   SET status = 'completed',
       queued_at = '{att2['started_at']}'::timestamptz,
       updated_at = '{att2['ended_at']}'::timestamptz,
       attempt_count = 2,
       latest_fencing_token = currval('eledgercare.extraction_fencing_seq'),
       retried_from_attempt_id = '{att1['attempt_id']}'
 WHERE job_id = '{job_id}';

INSERT INTO eledgercare.execution_attempts (
  attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
  status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
  launcher_pid, launcher_create_filetime, worker_pid, worker_create_filetime,
  started_at, last_heartbeat_at, ended_at, exit_code, failure_code, failure_detail
) VALUES (
  '{att2['attempt_id']}', '{job_id}', '{doc_id}', 2, currval('eledgercare.extraction_fencing_seq'), '{att1['attempt_id']}',
  'completed', 'completed', {sql_lit(att2['run_directory_name'])}, '{SYNTHESIZED_SUPERVISOR_RUN2_INSTANCE_ID}',
  {att2['supervisor_pid']}, {att2['supervisor_create_filetime']},
  {att2['launcher_pid']}, {att2['launcher_create_filetime']},
  {att2['worker_pid']}, {att2['worker_create_filetime']},
  '{att2['started_at']}'::timestamptz, '{att2['ended_at']}'::timestamptz, '{att2['ended_at']}'::timestamptz,
  0, NULL, NULL
);

INSERT INTO eledgercare.extraction_results (
  result_id, document_id, job_id, attempt_id, fencing_token, schema_version,
  input_sha256, input_byte_length, page_count, raw_output_bytes, raw_output_byte_length, raw_output_sha256,
  model_repo_id, model_revision, model_manifest_sha256, dependency_lock_sha256, worker_source_digest, worker_config_digest,
  renderer_identity, generation_settings_json, finish_reason, output_page_count,
  started_at, completed_at, load_duration_ms, render_duration_ms, infer_duration_ms, total_duration_ms, diagnostic_metadata_json
) VALUES (
  '{res_id}', '{doc_id}', '{job_id}', '{att2['attempt_id']}', currval('eledgercare.extraction_fencing_seq'), 'eledgercare.local-extraction/1',
  decode('{pdf_sha_hex}', 'hex'), {len(pdf_bytes)}, 1, decode('{raw_hex}', 'hex'), {len(raw_bytes)}, decode('{raw_sha_hex}', 'hex'),
  {sql_lit(prov['model_repo_id'])}, {sql_lit(prov['model_revision'])},
  decode('{prov['model_manifest_sha256']}', 'hex'),
  decode('{prov['dependency_lock_sha256']}', 'hex'),
  decode('{prov['worker_source_sha256']}', 'hex'),
  decode('{prov['worker_config_sha256']}', 'hex'),
  {sql_lit(prov['renderer_identity'])}, {sql_lit(gen_json)}::jsonb, 'stop', 1,
  '{timings['started_at_utc']}'::timestamptz, '{timings['completed_at_utc']}'::timestamptz,
  {int(timings['load_duration_ms'])}, {int(timings['render_duration_ms'])}, {int(timings['infer_duration_ms'])}, {int(timings['total_duration_ms'])},
  {sql_lit(diag_json)}::jsonb
);
COMMIT;
"""


def compute_canonical_8table_snapshot(
    psql_exe: Path,
    settings: dict,
    database: str,
    cwd: Path,
) -> dict:
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
        tuples_only=True,
    )
    parsed = json.loads(cp.stdout.strip())
    canonical_bytes = json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "canonical_8table_sha256": sha256_hex(canonical_bytes),
        "counts": {
            "documents": len(parsed["documents"]),
            "original_artifacts": len(parsed["original_artifacts"]),
            "processing_jobs": len(parsed["processing_jobs"]),
            "execution_attempts": len(parsed["execution_attempts"]),
            "extraction_results": len(parsed["extraction_results"]),
            "work_order_review_heads": len(parsed["work_order_review_heads"]),
            "work_order_review_revisions": len(parsed["work_order_review_revisions"]),
            "work_order_review_fields": len(parsed["work_order_review_fields"]),
        },
        "fencing_seq": parsed["fencing_seq"],
        "snapshot": parsed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WP-0010 independent reviewer F3 seed preparation & verification.")
    parser.add_argument("--output", required=True, help="Output JSON preparation receipt path")
    parser.add_argument("--resource-return-output", required=True, help="Output JSON resource-return receipt path")
    parser.add_argument("--logs-dir", required=True, help="Directory for sanitized step logs")
    parser.add_argument("--edge-receipt-output", required=True, help="Output JSON Edge smoke receipt path")
    parser.add_argument("--require-clean", action="store_true", help="Require clean git status before starting")
    args = parser.parse_args(argv)

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[6]
    logs_dir = (repo_root / args.logs_dir).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)

    assertions: list[dict] = []

    def record_assert(name: str, condition: bool, detail: object) -> None:
        if not condition:
            raise AssertionError(f"Preparation assertion failed [{name}]: {detail}")
        assertions.append({"check": name, "passed": True, "detail": detail})

    # 1. Pre-flight Git & forbidden-path self-check
    status_porcelain = run_git(repo_root, "status", "--porcelain", "--untracked-files=normal")
    if args.require_clean:
        record_assert("clean_worktree_before_decisive_run", status_porcelain == "", {"status": status_porcelain})

    head_sha = run_git(repo_root, "rev-parse", "HEAD")
    branch_name = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    record_assert("owned_branch_identity", branch_name == "review/wp-0010-f4", {"branch": branch_name, "head": head_sha})

    anc_002 = run_cmd(["git", "merge-base", "--is-ancestor", PRIOR_DESIGN_002_SHA, head_sha], cwd=repo_root).returncode == 0
    anc_auth = run_cmd(["git", "merge-base", "--is-ancestor", AUTHORITY_PREP_SHA, head_sha], cwd=repo_root).returncode == 0
    design_diff = run_git(
        repo_root,
        "diff",
        "--name-status",
        PRIOR_DESIGN_002_SHA,
        head_sha,
        "--",
        "docs/agent-reports/eld-f4-reviewer/WP-0010/002_2026-11-17_review_eld-f4-reviewer.md",
        "docs/reviews/WP-0010/eld-f4-reviewer/design",
    )
    record_assert(
        "immutable_002_and_authority_preserved",
        anc_002 and anc_auth and design_diff == "",
        {"anc_002": anc_002, "anc_auth": anc_auth, "design_diff": design_diff},
    )

    for rel in PRESERVED_TREE_PATHS:
        auth_oid = run_git(repo_root, "rev-parse", f"{AUTHORITY_PREP_SHA}:{rel}")
        head_oid = run_git(repo_root, "rev-parse", f"{head_sha}:{rel}")
        record_assert(f"preserved_tree_oid:{rel}", auth_oid == head_oid, {"oid": head_oid})

    refused_author_and_sealed = []
    for bad_rel in (
        "docs/implementation/WP-0010/eld-f4-implementer/preparation/README.md",
        "docs/evaluation/WP-0011/reservation/README.md",
        "../eld-f4-implementer/README.md",
    ):
        try:
            guard_owned_repo_path(repo_root, bad_rel)
        except PermissionError:
            refused_author_and_sealed.append(bad_rel)
    record_assert(
        "author_and_wp0011_paths_blocked",
        len(refused_author_and_sealed) == 3,
        {"blocked_probes": refused_author_and_sealed},
    )

    # 2. Verify owned ports (5690, 4710, 55439) unbound before starting anything, and verify PG 18.7 subset
    ports_before = observe_ports(REVIEWER_PORTS, repo_root)
    record_assert(
        "reviewer_ports_free_before_start",
        all(len(ports_before[str(p)]) == 0 for p in REVIEWER_PORTS),
        ports_before,
    )

    local_dir = repo_root / ".local"
    pg_subset_info = verify_pg_subset(local_dir / "tools", repo_root)
    record_assert(
        "pg18_subset_verified_offline",
        (
            pg_subset_info["file_count"] == EXPECTED_PG_FILES
            and pg_subset_info["total_bytes"] == EXPECTED_PG_BYTES
            and pg_subset_info["missing_files"] == []
            and pg_subset_info["extra_files"] == []
            and pg_subset_info["mismatched_files"] == []
            and pg_subset_info["reparse_points"] == []
            and pg_subset_info["subset_manifest_sha256"] == EXPECTED_SUBSET_SHA
            and pg_subset_info["central_directory_sha256"] == EXPECTED_CD_SHA
            and pg_subset_info["authenticode_status"] == "Valid"
        ),
        {
            "file_count": pg_subset_info["file_count"],
            "subset_manifest_sha256": pg_subset_info["subset_manifest_sha256"],
            "authenticode_status": pg_subset_info["authenticode_status"],
        },
    )

    pg_settings_path = local_dir / "secrets" / "pg-local.json"
    settings = json.loads(pg_settings_path.read_text(encoding="utf-8"))
    secrets = [
        str(settings["adminPassword"]),
        str(settings["migratorPassword"]),
        str(settings["appPassword"]),
    ]
    record_assert(
        "owned_pg_settings_port_55439_and_distinct_secrets",
        int(settings["port"]) == PG_PORT
        and settings["host"] == "127.0.0.1"
        and len(set(secrets)) == 3
        and all(len(s) >= 24 for s in secrets),
        {"host": settings["host"], "port": settings["port"]},
    )

    psql_exe = local_dir / "tools" / "pgsql-18.7-1" / "bin" / "psql.exe"
    pg_ctl_exe = local_dir / "tools" / "pgsql-18.7-1" / "bin" / "pg_ctl.exe"
    pg_data_dir = local_dir / "postgres-data"
    api_dll = guard_owned_repo_path(repo_root, "src/ELedgerCare.Api/bin/Release/net10.0/ELedgerCare.Api.dll")
    node_exe = Path(shutil.which("node") or "node")

    # Read genuine committed F2 artifacts & fixtures
    f01_pdf = guard_owned_repo_path(repo_root, "tests/fixtures/SYN-WO-01-v1-raster300.pdf").read_bytes()
    f07_pdf = guard_owned_repo_path(repo_root, "tests/fixtures/SYN-MP-01-v0-clean.pdf").read_bytes()
    f1_pdf = guard_owned_repo_path(repo_root, "tests/fixtures/F1-SWO-001.pdf").read_bytes()

    trial_summary = json.loads(
        guard_owned_repo_path(
            repo_root, "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/trial-summary-reviewer-v2.json"
        ).read_text(encoding="utf-8")
    )
    run1_raw = guard_owned_repo_path(
        repo_root,
        "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4/output/raw_output.utf8.bin",
    ).read_bytes()
    run1_env = json.loads(
        guard_owned_repo_path(
            repo_root,
            "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4/output/envelope.json",
        ).read_text(encoding="utf-8")
    )
    run2_raw = guard_owned_repo_path(
        repo_root,
        "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d/output/raw_output.utf8.bin",
    ).read_bytes()
    run2_env = json.loads(
        guard_owned_repo_path(
            repo_root,
            "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d/output/envelope.json",
        ).read_text(encoding="utf-8")
    )
    run3_raw = guard_owned_repo_path(
        repo_root,
        "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e579-4599-7bed-acdc-2863c448c6fa/output/raw_output.utf8.bin",
    ).read_bytes()
    run3_env = json.loads(
        guard_owned_repo_path(
            repo_root,
            "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e579-4599-7bed-acdc-2863c448c6fa/output/envelope.json",
        ).read_text(encoding="utf-8")
    )

    record_assert(
        "genuine_wp0006_inputs_hash_verified",
        (
            sha256_hex(f01_pdf) == F01_PDF_SHA256
            and sha256_hex(f07_pdf) == F07_PDF_SHA256
            and sha256_hex(f1_pdf) == F1_PDF_SHA256
            and sha256_hex(run1_raw) == sha256_hex(run3_raw) == F01_RAW_SHA256
            and sha256_hex(run2_raw) == F07_RAW_SHA256
        ),
        {"f01_raw_sha256": F01_RAW_SHA256, "f07_raw_sha256": F07_RAW_SHA256},
    )

    api_proc: subprocess.Popen[bytes] | None = None
    api_info: dict | None = None
    ui_proc: subprocess.Popen[bytes] | None = None
    ui_info: dict | None = None
    postmaster_info: dict | None = None
    api_stop_receipt: dict = {}
    ui_stop_receipt: dict = {}
    pg_stop_log_text = ""

    api_log_file = logs_dir / "owned-api-5690.log"
    ui_log_file = logs_dir / "owned-ui-4710.log"

    try:
        # 3. Start owned PostgreSQL 18.7 cluster on 127.0.0.1:55439
        start_pg_cp = run_cmd(
            ["pwsh", "-NoProfile", "-File", str(repo_root / "deploy/dev/postgres/start-cluster.ps1")],
            cwd=repo_root,
        )
        if start_pg_cp.returncode != 0:
            raise RuntimeError(f"start-cluster.ps1 failed: {start_pg_cp.stderr}")
        (logs_dir / "01-pg-cluster-start.log").write_text(
            redact_secrets(start_pg_cp.stdout + start_pg_cp.stderr, secrets), encoding="utf-8", newline="\n"
        )

        pm_pid = int((pg_data_dir / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        postmaster_info = inspect_process(pm_pid, repo_root)
        record_assert("postmaster_55439_running", postmaster_info is not None, postmaster_info)

        # Reset and migrate `eledgercare_f4_reviewer_seed_f3` to accepted pre-F4 F3 schema + grant-runtime.sql
        invoke_psql(
            psql_exe,
            host=settings["host"],
            port=PG_PORT,
            user=settings["adminUser"],
            password=settings["adminPassword"],
            database="postgres",
            sql=f"DROP DATABASE IF EXISTS {SEED_DATABASE} WITH (FORCE);",
            cwd=repo_root,
        )

        prep_env = dict(os.environ)
        prep_env["DOTNET_CLI_HOME"] = str(local_dir / "dotnet-home")
        prep_env["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1"
        prep_env["DOTNET_NOLOGO"] = "1"
        prep_env["NUGET_PACKAGES"] = str(local_dir / "nuget" / "packages")

        prep_db_cp = run_cmd(
            [
                "pwsh",
                "-NoProfile",
                "-File",
                str(repo_root / "deploy/dev/database/prepare-database.ps1"),
                "-Database",
                SEED_DATABASE,
            ],
            cwd=repo_root,
            env=prep_env,
        )
        if prep_db_cp.returncode != 0:
            raise RuntimeError(f"prepare-database.ps1 failed: {prep_db_cp.stdout}\n{prep_db_cp.stderr}")
        sanitized_prep_log = redact_secrets(prep_db_cp.stdout + prep_db_cp.stderr, secrets)
        (logs_dir / "02-prepare-f3-seed-db.log").write_text(sanitized_prep_log, encoding="utf-8", newline="\n")

        # Verify cluster durability & C-locale collation settings on `eledgercare_f4_reviewer_seed_f3`
        pg_meta_cp = invoke_psql(
            psql_exe,
            host=settings["host"],
            port=PG_PORT,
            user=settings["adminUser"],
            password=settings["adminPassword"],
            database=SEED_DATABASE,
            sql="""
SELECT json_build_object(
  'server_version', current_setting('server_version'),
  'listen_addresses', current_setting('listen_addresses'),
  'port', current_setting('port'),
  'fsync', current_setting('fsync'),
  'full_page_writes', current_setting('full_page_writes'),
  'synchronous_commit', current_setting('synchronous_commit'),
  'password_encryption', current_setting('password_encryption'),
  'data_checksums', current_setting('data_checksums'),
  'lc_collate', (SELECT datcollate FROM pg_database WHERE datname = current_database()),
  'lc_ctype', (SELECT datctype FROM pg_database WHERE datname = current_database()),
  'migrations', (SELECT json_agg("MigrationId" ORDER BY "MigrationId") FROM eledgercare.__ef_migrations_history)
)::text;
""",
            cwd=repo_root,
        )
        pg_meta = json.loads(pg_meta_cp.stdout.strip())
        record_assert(
            "pg_durability_c_locale_and_pre_f4_migrations",
            (
                pg_meta["server_version"] == "18.7"
                and pg_meta["listen_addresses"] == "127.0.0.1"
                and pg_meta["port"] == str(PG_PORT)
                and pg_meta["fsync"] == "on"
                and pg_meta["full_page_writes"] == "on"
                and pg_meta["synchronous_commit"] == "on"
                and pg_meta["password_encryption"] == "scram-sha-256"
                and pg_meta["data_checksums"] == "on"
                and pg_meta["lc_collate"] == "C"
                and pg_meta["lc_ctype"] == "C"
                and pg_meta["migrations"]
                == [
                    "20261114182147_InitialDurableIntake",
                    "20261116052029_AddLocalExtraction",
                    "20261116200918_AddWorkOrderReview",
                ]
            ),
            pg_meta,
        )

        # 4. Insert 7 attributed genuine WP-0006 F2 extraction documents via least-privilege `eledgercare_app`
        scen1 = trial_summary["scenarios"]["1_f01_single_page_complete"]
        scen2 = trial_summary["scenarios"]["2_f07_three_page_complete"]
        scen3 = trial_summary["scenarios"]["3_live_supervisor_kill_and_explicit_retry"]
        s1_att = scen1["completion"]["db_attempts"][0]
        s2_att = scen2["completion"]["db_attempts"][0]

        seed_sql_blocks = [
            # SEED-R01: Exact Scenario 1 (SYN-WO-01, token=1)
            build_single_attempt_seed_sql(
                document_id=scen1["submission"]["receipt"]["documentId"],
                idempotency_key=scen1["submission"]["idempotency_key"],
                submitted_at_utc=scen1["submission"]["receipt"]["submittedAtUtc"],
                pdf_bytes=f01_pdf,
                pdf_sha_hex=F01_PDF_SHA256,
                page_count=1,
                job_id=scen1["submission"]["receipt"]["jobId"],
                queued_at_utc=s1_att["started_at"],
                attempt_id=s1_att["attempt_id"],
                supervisor_instance_id=SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID,
                supervisor_pid=s1_att["supervisor_pid"],
                supervisor_ft=s1_att["supervisor_create_filetime"],
                launcher_pid=s1_att["launcher_pid"],
                launcher_ft=s1_att["launcher_create_filetime"],
                worker_pid=s1_att["worker_pid"],
                worker_ft=s1_att["worker_create_filetime"],
                attempt_started_utc=s1_att["started_at"],
                attempt_ended_utc=s1_att["ended_at"],
                result_id=scen1["completion"]["db_result"]["result_id"],
                raw_bytes=run1_raw,
                raw_sha_hex=F01_RAW_SHA256,
                envelope=run1_env,
            ),
            # SEED-R02: Exact Scenario 2 (SYN-MP-01 3p, token=2)
            build_single_attempt_seed_sql(
                document_id=scen2["submission"]["receipt"]["documentId"],
                idempotency_key=scen2["submission"]["idempotency_key"],
                submitted_at_utc=scen2["submission"]["receipt"]["submittedAtUtc"],
                pdf_bytes=f07_pdf,
                pdf_sha_hex=F07_PDF_SHA256,
                page_count=3,
                job_id=scen2["submission"]["receipt"]["jobId"],
                queued_at_utc=s2_att["started_at"],
                attempt_id=s2_att["attempt_id"],
                supervisor_instance_id=SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID,
                supervisor_pid=s2_att["supervisor_pid"],
                supervisor_ft=s2_att["supervisor_create_filetime"],
                launcher_pid=s2_att["launcher_pid"],
                launcher_ft=s2_att["launcher_create_filetime"],
                worker_pid=s2_att["worker_pid"],
                worker_ft=s2_att["worker_create_filetime"],
                attempt_started_utc=s2_att["started_at"],
                attempt_ended_utc=s2_att["ended_at"],
                result_id=scen2["completion"]["db_result"]["result_id"],
                raw_bytes=run2_raw,
                raw_sha_hex=F07_RAW_SHA256,
                envelope=run2_env,
            ),
            # SEED-R03: Exact Scenario 3 (interrupted Attempt #1 token=3 + completed Retry Attempt #2 token=4)
            build_scenario3_retry_seed_sql(
                scen3=scen3,
                pdf_bytes=f01_pdf,
                pdf_sha_hex=F01_PDF_SHA256,
                raw_bytes=run3_raw,
                raw_sha_hex=F01_RAW_SHA256,
                envelope=run3_env,
            ),
            # SEED-R04: Remapped Scenario 2 (3p SYN-MP-01 for Page-2 provenance vs null-provenance review, token=5)
            build_single_attempt_seed_sql(
                document_id="01a20400-0000-7000-8000-000000000004",
                idempotency_key="01a20400-1000-7000-8000-000000000004",
                submitted_at_utc="2026-11-16T17:55:00.000000+00:00",
                pdf_bytes=f07_pdf,
                pdf_sha_hex=F07_PDF_SHA256,
                page_count=3,
                job_id="01a20400-2000-7000-8000-000000000004",
                queued_at_utc="2026-11-16T17:55:01.000000+00:00",
                attempt_id="01a20400-3000-7000-8000-000000000004",
                supervisor_instance_id=SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID,
                supervisor_pid=s2_att["supervisor_pid"],
                supervisor_ft=s2_att["supervisor_create_filetime"],
                launcher_pid=s2_att["launcher_pid"],
                launcher_ft=s2_att["launcher_create_filetime"],
                worker_pid=s2_att["worker_pid"],
                worker_ft=s2_att["worker_create_filetime"],
                attempt_started_utc="2026-11-16T17:55:01.000000+00:00",
                attempt_ended_utc="2026-11-16T17:56:00.000000+00:00",
                result_id="01a20400-4000-7000-8000-000000000004",
                raw_bytes=run2_raw,
                raw_sha_hex=F07_RAW_SHA256,
                envelope=run2_env,
            ),
            # SEED-R05: Remapped Scenario 1 (SYN-WO-01 for Draft-Only review state, token=6)
            build_single_attempt_seed_sql(
                document_id="01a20400-0000-7000-8000-000000000005",
                idempotency_key="01a20400-1000-7000-8000-000000000005",
                submitted_at_utc="2026-11-16T17:58:00.000000+00:00",
                pdf_bytes=f01_pdf,
                pdf_sha_hex=F01_PDF_SHA256,
                page_count=1,
                job_id="01a20400-2000-7000-8000-000000000005",
                queued_at_utc="2026-11-16T17:58:01.000000+00:00",
                attempt_id="01a20400-3000-7000-8000-000000000005",
                supervisor_instance_id=SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID,
                supervisor_pid=s1_att["supervisor_pid"],
                supervisor_ft=s1_att["supervisor_create_filetime"],
                launcher_pid=s1_att["launcher_pid"],
                launcher_ft=s1_att["launcher_create_filetime"],
                worker_pid=s1_att["worker_pid"],
                worker_ft=s1_att["worker_create_filetime"],
                attempt_started_utc="2026-11-16T17:58:01.000000+00:00",
                attempt_ended_utc="2026-11-16T17:59:00.000000+00:00",
                result_id="01a20400-4000-7000-8000-000000000005",
                raw_bytes=run1_raw,
                raw_sha_hex=F01_RAW_SHA256,
                envelope=run1_env,
            ),
            # SEED-R06: Remapped Scenario 1 (exact microsecond tie-breaker A, token=7)
            build_single_attempt_seed_sql(
                document_id="01a20400-0000-7000-8000-000000000006",
                idempotency_key="01a20400-1000-7000-8000-000000000006",
                submitted_at_utc="2026-11-16T18:00:00.123456+00:00",
                pdf_bytes=f01_pdf,
                pdf_sha_hex=F01_PDF_SHA256,
                page_count=1,
                job_id="01a20400-2000-7000-8000-000000000006",
                queued_at_utc="2026-11-16T18:00:01.000000+00:00",
                attempt_id="01a20400-3000-7000-8000-000000000006",
                supervisor_instance_id=SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID,
                supervisor_pid=s1_att["supervisor_pid"],
                supervisor_ft=s1_att["supervisor_create_filetime"],
                launcher_pid=s1_att["launcher_pid"],
                launcher_ft=s1_att["launcher_create_filetime"],
                worker_pid=s1_att["worker_pid"],
                worker_ft=s1_att["worker_create_filetime"],
                attempt_started_utc="2026-11-16T18:00:01.000000+00:00",
                attempt_ended_utc="2026-11-16T18:01:00.000000+00:00",
                result_id="01a20400-4000-7000-8000-000000000006",
                raw_bytes=run1_raw,
                raw_sha_hex=F01_RAW_SHA256,
                envelope=run1_env,
            ),
            # SEED-R07: Remapped Scenario 2 (exact microsecond tie-breaker B, token=8)
            build_single_attempt_seed_sql(
                document_id="01a20400-0000-7000-8000-000000000007",
                idempotency_key="01a20400-1000-7000-8000-000000000007",
                submitted_at_utc="2026-11-16T18:00:00.123456+00:00",
                pdf_bytes=f07_pdf,
                pdf_sha_hex=F07_PDF_SHA256,
                page_count=3,
                job_id="01a20400-2000-7000-8000-000000000007",
                queued_at_utc="2026-11-16T18:00:02.000000+00:00",
                attempt_id="01a20400-3000-7000-8000-000000000007",
                supervisor_instance_id=SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID,
                supervisor_pid=s2_att["supervisor_pid"],
                supervisor_ft=s2_att["supervisor_create_filetime"],
                launcher_pid=s2_att["launcher_pid"],
                launcher_ft=s2_att["launcher_create_filetime"],
                worker_pid=s2_att["worker_pid"],
                worker_ft=s2_att["worker_create_filetime"],
                attempt_started_utc="2026-11-16T18:00:02.000000+00:00",
                attempt_ended_utc="2026-11-16T18:02:00.000000+00:00",
                result_id="01a20400-4000-7000-8000-000000000007",
                raw_bytes=run2_raw,
                raw_sha_hex=F07_RAW_SHA256,
                envelope=run2_env,
            ),
        ]

        for block_sql in seed_sql_blocks:
            invoke_psql(
                psql_exe,
                host=settings["host"],
                port=PG_PORT,
                user=settings["appUser"],
                password=settings["appPassword"],
                database=SEED_DATABASE,
                sql=block_sql,
                cwd=repo_root,
            )

        # 5. Start owned unchanged ELedgerCare.Api on 127.0.0.1:5690 (LocalOcr:Enabled=false)
        api_env = dict(os.environ)
        api_env["ASPNETCORE_ENVIRONMENT"] = "Production"
        api_env["DOTNET_NOLOGO"] = "1"
        api_env["Api__Port"] = str(API_PORT)
        api_env["LocalOcr__Enabled"] = "false"
        api_env["ConnectionStrings__Runtime"] = (
            f"Host={settings['host']};Port={PG_PORT};Database={SEED_DATABASE};"
            f"Username={settings['appUser']};Password={settings['appPassword']}"
        )

        with api_log_file.open("wb") as api_out_fh:
            api_proc = subprocess.Popen(
                ["dotnet", str(api_dll)],
                cwd=str(api_dll.parent),
                env=api_env,
                stdout=api_out_fh,
                stderr=subprocess.STDOUT,
            )
        api_info = inspect_process(api_proc.pid, repo_root)

        api_ready = False
        deadline = time.monotonic() + 45.0
        while time.monotonic() < deadline:
            if api_proc.poll() is not None:
                raise RuntimeError(f"ELedgerCare.Api exited early with code {api_proc.returncode}")
            try:
                st, _, _ = http_request(API_PORT, "GET", "/api/documents/00000000-0000-7000-8000-999999999999")
                if st == 404:
                    api_ready = True
                    break
            except OSError:
                time.sleep(0.25)
        record_assert("owned_api_5690_listening_ocr_disabled", api_ready and api_info is not None, api_info)

        # 6. Execute live HTTP F1 intake submissions (SEED-R08 failed + SEED-R09 awaiting_extraction)
        st_r08, _, rec_r08 = http_json_or_raw_submit(
            API_PORT, "01a20400-1000-7000-8000-000000000008", f1_pdf
        )
        st_r09, _, rec_r09 = http_json_or_raw_submit(
            API_PORT, "01a20400-1000-7000-8000-000000000009", f1_pdf
        )
        record_assert(
            "live_f1_http_submissions_r08_and_r09",
            st_r08 == 201 and st_r09 == 201 and rec_r08["sha256"] == F1_PDF_SHA256 and rec_r09["sha256"] == F1_PDF_SHA256,
            {"seed_r08_doc_id": rec_r08["documentId"], "seed_r09_doc_id": rec_r09["documentId"]},
        )

        # Verify POST /extraction on SEED-R09 returns 503 extraction_disabled when LocalOcr:Enabled=false
        st_ext_503, _, body_ext_503 = http_json(API_PORT, "POST", f"/api/documents/{rec_r09['documentId']}/extraction")
        record_assert(
            "disabled_ocr_post_extraction_returns_503",
            st_ext_503 == 503 and body_ext_503.get("code") == "extraction_disabled",
            body_ext_503,
        )

        # Transition SEED-R08 via `eledgercare_app` SQL (token=9) to `failed` with partial diagnostic output
        r08_att_id = "01a20400-3000-7000-8000-000000000008"
        invoke_psql(
            psql_exe,
            host=settings["host"],
            port=PG_PORT,
            user=settings["appUser"],
            password=settings["appPassword"],
            database=SEED_DATABASE,
            sql=f"""
BEGIN;
SET LOCAL synchronous_commit = on;
SELECT nextval('eledgercare.extraction_fencing_seq');
UPDATE eledgercare.processing_jobs
   SET status = 'running',
       queued_at = now(),
       updated_at = now(),
       attempt_count = 1,
       latest_fencing_token = currval('eledgercare.extraction_fencing_seq')
 WHERE job_id = '{rec_r08['jobId']}' AND status = 'awaiting_extraction';

INSERT INTO eledgercare.execution_attempts (
  attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
  status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
  started_at, last_heartbeat_at
) VALUES (
  '{r08_att_id}', '{rec_r08['jobId']}', '{rec_r08['documentId']}', 1, currval('eledgercare.extraction_fencing_seq'), NULL,
  'running', 'inferring', 'attempt-{r08_att_id}', '{SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID}', 18496, 134393243591895019,
  now(), now()
);

UPDATE eledgercare.processing_jobs
   SET status = 'failed', updated_at = now()
 WHERE job_id = '{rec_r08['jobId']}' AND latest_fencing_token = currval('eledgercare.extraction_fencing_seq');

UPDATE eledgercare.execution_attempts
   SET status = 'failed',
       phase = 'failed',
       ended_at = now(),
       last_heartbeat_at = now(),
       exit_code = 2,
       failure_code = 'worker_nonzero_exit',
       failure_detail = 'DIAGNOSTIC-FAILURE-DETAIL-NOT-INDEXED',
       diagnostic_raw_output_utf8 = '<PAGE><BLOCK>text[0,0,10,10]<FORK>DIAGNOSTIC-PARTIAL-RAW-NEVER-SEARCHABLE',
       diagnostic_metadata_json = '{{"partial":true}}'::jsonb
 WHERE attempt_id = '{r08_att_id}';
COMMIT;
""",
            cwd=repo_root,
        )

        # 7. Execute 8 live F3 HTTP review revision saves across SEED-R01, SEED-R03, SEED-R04, SEED-R05, SEED-R06
        wo_narr = (
            "Air handler fan running continuously with warm supply air at 79 F setpoint. "
            "Inspected condensing unit CHP-B204: dual run capacitor measured 18.2 uF on 45 uF herm leg "
            "and contactor points pitted. Replaced capacitor and 2-pole contactor from van stock; "
            "verified 19.4 F delta-T across evaporator coil."
        )
        r01_doc = scen1["submission"]["receipt"]["documentId"]
        r01_res = scen1["completion"]["db_result"]["result_id"]
        r03_doc = scen3["submission"]["receipt"]["documentId"]
        r03_res = scen3["retry_completion"]["db_result"]["result_id"]
        r04_doc = "01a20400-0000-7000-8000-000000000004"
        r04_res = "01a20400-4000-7000-8000-000000000004"
        r05_doc = "01a20400-0000-7000-8000-000000000005"
        r05_res = "01a20400-4000-7000-8000-000000000005"
        r06_doc = "01a20400-0000-7000-8000-000000000006"
        r06_res = "01a20400-4000-7000-8000-000000000006"

        r01_rev2_key = "01a20400-5000-7000-8000-000000000102"
        r01_rev2_payload = {
            "profileId": "maintenance-work-order/1",
            "resultId": r01_res,
            "expectedRevision": 1,
            "status": "reviewed",
            "operatorDisplayLabel": "R4-OP-HIDDEN-BETA",
            "fields": [
                {"fieldKey": "work_order_id", "decision": "accepted", "value": "WO-004192", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 4, "tableRow": None, "tableColumn": None}},
                {"fieldKey": "property_name", "decision": "edited", "value": "Cedar Hollow Apartments — Verified North Wing (7.50% Cap_Rate \\ Literal)", "unknownReason": None, "consultedSource": None},
                {"fieldKey": "building_unit", "decision": "unknown", "value": None, "unknownReason": "R4-UNKNOWN-REASON-ILLEGIBLE-BADGE", "consultedSource": None},
                {"fieldKey": "requested_date", "decision": "accepted", "value": "2026-10-16", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 10, "tableRow": None, "tableColumn": None}},
                {"fieldKey": "issue_and_resolution", "decision": "edited", "value": "Condensing unit CHP-B204 serviced 🔧 astral-scalar check; Café Élite compressor relay verified.", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 24, "tableRow": None, "tableColumn": None}},
            ],
        }

        review_ops = [
            # SEED-R01 Rev #1 (reviewed, superseded later by Rev #2)
            (
                "r01_rev1_reviewed",
                r01_doc,
                "01a20400-5000-7000-8000-000000000101",
                {
                    "profileId": "maintenance-work-order/1",
                    "resultId": r01_res,
                    "expectedRevision": 0,
                    "status": "reviewed",
                    "operatorDisplayLabel": "R4-OP-HIDDEN-ALPHA",
                    "fields": [
                        {"fieldKey": "work_order_id", "decision": "accepted", "value": "WO-004192", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 4, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "property_name", "decision": "edited", "value": "Cedar Hollow Apartments — South Annex [REV1-SUPERSEDED]", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 6, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "building_unit", "decision": "edited", "value": "Bldg B - Unit 204-LEGACY-R1", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 8, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "requested_date", "decision": "accepted", "value": "2026-10-16", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 10, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "issue_and_resolution", "decision": "accepted", "value": wo_narr, "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 24, "tableRow": None, "tableColumn": None}},
                    ],
                },
            ),
            # SEED-R01 Rev #2 (reviewed, latest reviewed revision!)
            ("r01_rev2_latest_reviewed", r01_doc, r01_rev2_key, r01_rev2_payload),
            # SEED-R01 Rev #3 (draft, newer unapproved head!)
            (
                "r01_rev3_newer_draft_head",
                r01_doc,
                "01a20400-5000-7000-8000-000000000103",
                {
                    "profileId": "maintenance-work-order/1",
                    "resultId": r01_res,
                    "expectedRevision": 2,
                    "status": "draft",
                    "operatorDisplayLabel": "R4-OP-HIDDEN-DRAFT3",
                    "fields": [
                        {"fieldKey": "work_order_id", "decision": "accepted", "value": "WO-004192", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 4, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "property_name", "decision": "edited", "value": "UNAPPROVED-DRAFT-R3-DO-NOT-INDEX", "unknownReason": None, "consultedSource": None},
                        {"fieldKey": "building_unit", "decision": "unreviewed", "value": "DRAFT-UNIT-UNREVIEWED-999", "unknownReason": None, "consultedSource": None},
                        {"fieldKey": "requested_date", "decision": "accepted", "value": "2026-10-16", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 10, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "issue_and_resolution", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
                    ],
                },
            ),
            # SEED-R03 Rev #1 (reviewed, clean reviewed head)
            (
                "r03_rev1_clean_reviewed_head",
                r03_doc,
                "01a20400-5000-7000-8000-000000000301",
                {
                    "profileId": "maintenance-work-order/1",
                    "resultId": r03_res,
                    "expectedRevision": 0,
                    "status": "reviewed",
                    "operatorDisplayLabel": "R4-OP-HIDDEN-CLEAN",
                    "fields": [
                        {"fieldKey": "work_order_id", "decision": "edited", "value": "WO-009901-CLEAN-HEAD", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 4, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "property_name", "decision": "accepted", "value": "Cedar Hollow Apartments", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 6, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "building_unit", "decision": "accepted", "value": "Bldg B - Unit 204", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 8, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "requested_date", "decision": "accepted", "value": "2026-10-16", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 10, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "issue_and_resolution", "decision": "accepted", "value": wo_narr, "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 24, "tableRow": None, "tableColumn": None}},
                    ],
                },
            ),
            # SEED-R04 Rev #1 (reviewed on 3-page SYN-MP-01: Page-2 table provenance + null-provenance edit)
            (
                "r04_rev1_p2_and_null_provenance",
                r04_doc,
                "01a20400-5000-7000-8000-000000000401",
                {
                    "profileId": "maintenance-work-order/1",
                    "resultId": r04_res,
                    "expectedRevision": 0,
                    "status": "reviewed",
                    "operatorDisplayLabel": "R4-OP-HIDDEN-MP",
                    "fields": [
                        {"fieldKey": "work_order_id", "decision": "edited", "value": "WO-004724-MP-LINKED", "unknownReason": None, "consultedSource": {"pageNumber": 2, "blockOrdinal": 2, "tableRow": 3, "tableColumn": 1}},
                        {"fieldKey": "property_name", "decision": "edited", "value": "Maple Ridge Commons — Manual Entry ZeroCoords", "unknownReason": None, "consultedSource": None},
                        {"fieldKey": "building_unit", "decision": "edited", "value": "Unit 11A", "unknownReason": None, "consultedSource": {"pageNumber": 2, "blockOrdinal": 2, "tableRow": 3, "tableColumn": 2}},
                        {"fieldKey": "requested_date", "decision": "unknown", "value": None, "unknownReason": "Invoice statement covers monthly range", "consultedSource": None},
                        {"fieldKey": "issue_and_resolution", "decision": "edited", "value": "Cross-page evaporator motor L09 verified on Page 2.", "unknownReason": None, "consultedSource": None},
                    ],
                },
            ),
            # SEED-R05 Rev #1 & Rev #2 (draft-only document, never reviewed!)
            (
                "r05_rev1_draft_only",
                r05_doc,
                "01a20400-5000-7000-8000-000000000501",
                {
                    "profileId": "maintenance-work-order/1",
                    "resultId": r05_res,
                    "expectedRevision": 0,
                    "status": "draft",
                    "operatorDisplayLabel": "R4-OP-DRAFT-ONLY-1",
                    "fields": [
                        {"fieldKey": "work_order_id", "decision": "edited", "value": "WO-DRAFT-ONLY-R1", "unknownReason": None, "consultedSource": None},
                        {"fieldKey": "property_name", "decision": "edited", "value": "Draft Only Property Alpha", "unknownReason": None, "consultedSource": None},
                        {"fieldKey": "building_unit", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
                        {"fieldKey": "requested_date", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
                        {"fieldKey": "issue_and_resolution", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
                    ],
                },
            ),
            (
                "r05_rev2_draft_only",
                r05_doc,
                "01a20400-5000-7000-8000-000000000502",
                {
                    "profileId": "maintenance-work-order/1",
                    "resultId": r05_res,
                    "expectedRevision": 1,
                    "status": "draft",
                    "operatorDisplayLabel": "R4-OP-DRAFT-ONLY-2",
                    "fields": [
                        {"fieldKey": "work_order_id", "decision": "edited", "value": "WO-DRAFT-ONLY-R1", "unknownReason": None, "consultedSource": None},
                        {"fieldKey": "property_name", "decision": "edited", "value": "Draft Only Property Beta Never Reviewed", "unknownReason": None, "consultedSource": None},
                        {"fieldKey": "building_unit", "decision": "accepted", "value": "Bldg B - Unit 204", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 8, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "requested_date", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
                        {"fieldKey": "issue_and_resolution", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
                    ],
                },
            ),
            # SEED-R06 Rev #1 (reviewed, leading zeros WO-0006-TIE-LOW, timestamp tie-breaker A)
            (
                "r06_rev1_tie_low_leading_zeros",
                r06_doc,
                "01a20400-5000-7000-8000-000000000601",
                {
                    "profileId": "maintenance-work-order/1",
                    "resultId": r06_res,
                    "expectedRevision": 0,
                    "status": "reviewed",
                    "operatorDisplayLabel": "R4-OP-TIE-LOW",
                    "fields": [
                        {"fieldKey": "work_order_id", "decision": "edited", "value": "WO-0006-TIE-LOW", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 4, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "property_name", "decision": "accepted", "value": "Cedar Hollow Apartments", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 6, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "building_unit", "decision": "accepted", "value": "Bldg B - Unit 204", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 8, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "requested_date", "decision": "accepted", "value": "2026-10-16", "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 10, "tableRow": None, "tableColumn": None}},
                        {"fieldKey": "issue_and_resolution", "decision": "accepted", "value": wo_narr, "unknownReason": None, "consultedSource": {"pageNumber": 1, "blockOrdinal": 24, "tableRow": None, "tableColumn": None}},
                    ],
                },
            ),
        ]

        created_revisions: list[dict] = []
        for op_name, target_doc_id, idem_key, payload in review_ops:
            st, _, body = http_json(
                API_PORT,
                "POST",
                f"/api/documents/{target_doc_id}/review/revisions",
                headers={"Idempotency-Key": idem_key},
                json_body=payload,
            )
            record_assert(
                f"live_f3_review_save:{op_name}",
                st == 201 and body.get("replayed") is False,
                {
                    "documentId": target_doc_id,
                    "revisionNumber": body.get("revision", {}).get("revisionNumber"),
                    "revisionId": body.get("revision", {}).get("revisionId"),
                    "status": body.get("revision", {}).get("status"),
                },
            )
            created_revisions.append({
                "op": op_name,
                "documentId": target_doc_id,
                "revisionNumber": body["revision"]["revisionNumber"],
                "revisionId": body["revision"]["revisionId"],
                "status": body["revision"]["status"],
                "idempotencyKey": idem_key,
            })

        # 8. Capture canonical 8-table digest BEFORE read-only API, replay, privilege, and Edge checks!
        snap_before = compute_canonical_8table_snapshot(psql_exe, settings, SEED_DATABASE, repo_root)
        record_assert(
            "expected_8table_row_counts_and_seq_9",
            (
                snap_before["counts"]
                == {
                    "documents": 9,
                    "original_artifacts": 9,
                    "processing_jobs": 9,
                    "execution_attempts": 9,
                    "extraction_results": 7,
                    "work_order_review_heads": 5,
                    "work_order_review_revisions": 8,
                    "work_order_review_fields": 40,
                }
                and snap_before["fencing_seq"] == {"last_value": 9, "is_called": True}
            ),
            {"counts": snap_before["counts"], "fencing_seq": snap_before["fencing_seq"]},
        )

        # 9. Verify historical idempotent replay, non-completed review 409s, current-vs-latest-reviewed API reads, & Range /preview
        replay_st, _, replay_body = http_json(
            API_PORT,
            "POST",
            f"/api/documents/{r01_doc}/review/revisions",
            headers={"Idempotency-Key": r01_rev2_key},
            json_body=r01_rev2_payload,
        )
        st_r08_rev, _, body_r08_rev = http_json(API_PORT, "GET", f"/api/documents/{rec_r08['documentId']}/review")
        st_r09_rev, _, body_r09_rev = http_json(API_PORT, "GET", f"/api/documents/{rec_r09['documentId']}/review")
        _, _, r01_head_get = http_json(API_PORT, "GET", f"/api/documents/{r01_doc}/review")
        _, _, r01_rev2_get = http_json(API_PORT, "GET", f"/api/documents/{r01_doc}/review/revisions/2")
        _, _, r01_rev1_get = http_json(API_PORT, "GET", f"/api/documents/{r01_doc}/review/revisions/1")
        _, _, r04_head_get = http_json(API_PORT, "GET", f"/api/documents/{r04_doc}/review")
        st_range, range_hdrs, range_bytes = http_request(
            API_PORT, "GET", f"/api/documents/{r04_doc}/preview", headers={"Range": "bytes=0-63"}
        )

        r04_fields_by_key = {f["fieldKey"]: f for f in r04_head_get["fields"]}
        record_assert(
            "api_current_vs_latest_reviewed_provenance_and_range_verified",
            (
                replay_st == 200
                and replay_body["replayed"] is True
                and replay_body["isCurrentHead"] is False
                and replay_body["currentRevisionNumber"] == 3
                and replay_body["currentReviewState"] == "draft"
                and st_r08_rev == 409
                and body_r08_rev["code"] == "extraction_not_completed"
                and st_r09_rev == 409
                and body_r09_rev["code"] == "extraction_not_completed"
                and r01_head_get["currentRevisionNumber"] == 3
                and r01_head_get["reviewState"] == "draft"
                and r01_rev2_get["isCurrentHead"] is False
                and r01_rev2_get["revision"]["status"] == "reviewed"
                and r01_rev1_get["isCurrentHead"] is False
                and "[REV1-SUPERSEDED]" in r01_rev1_get["fields"][1]["value"]
                and r04_fields_by_key["work_order_id"]["consultedSource"]["pageNumber"] == 2
                and r04_fields_by_key["work_order_id"]["consultedSource"]["sourceQuote"] == "WO-004724"
                and r04_fields_by_key["property_name"]["consultedSource"] is None
                and st_range == 206
                and range_bytes == f07_pdf[:64]
                and range_hdrs.get("x-frame-options") == "SAMEORIGIN"
            ),
            {
                "r01_head": r01_head_get["currentRevisionNumber"],
                "r01_latest_reviewed": r01_rev2_get["revision"]["revisionNumber"],
                "r04_p2_quote": r04_fields_by_key["work_order_id"]["consultedSource"]["sourceQuote"],
                "r04_null_prov": r04_fields_by_key["property_name"]["consultedSource"],
            },
        )

        # 10. Direct negative least-privilege SQL probes as `eledgercare_app`
        denied_sql_statements = [
            "UPDATE eledgercare.original_artifacts SET bytes = bytes",
            "UPDATE eledgercare.documents SET submitted_at = submitted_at",
            "UPDATE eledgercare.extraction_results SET raw_output_bytes = raw_output_bytes",
            "DELETE FROM eledgercare.extraction_results",
            "UPDATE eledgercare.work_order_review_revisions SET status = 'reviewed'",
            "DELETE FROM eledgercare.work_order_review_revisions",
            "UPDATE eledgercare.work_order_review_fields SET human_value = 'tamper'",
            "DELETE FROM eledgercare.work_order_review_fields",
            "UPDATE eledgercare.work_order_review_heads SET machine_snapshot_json = machine_snapshot_json",
            "UPDATE eledgercare.work_order_review_heads SET raw_output_sha256 = raw_output_sha256",
            "DELETE FROM eledgercare.work_order_review_heads",
            "CREATE TABLE eledgercare.forbidden_probe (id int)",
            "SELECT count(*) FROM eledgercare.__ef_migrations_history",
        ]
        denied_results = []
        for bad_sql in denied_sql_statements:
            cp_den = invoke_psql(
                psql_exe,
                host=settings["host"],
                port=PG_PORT,
                user=settings["appUser"],
                password=settings["appPassword"],
                database=SEED_DATABASE,
                sql=bad_sql,
                cwd=repo_root,
                expect_success=False,
            )
            denied_results.append({
                "verb": bad_sql.split(" ", 1)[0],
                "returncode": cp_den.returncode,
                "permission_denied": "permission denied" in cp_den.stderr.lower(),
            })
        record_assert(
            "least_privilege_denies_all_13_unauthorized_mutations",
            all(r["returncode"] != 0 and r["permission_denied"] for r in denied_results),
            {"denied_count": len(denied_results)},
        )

        # 11. Launch owned Angular UI (`127.0.0.1:4710` -> `127.0.0.1:5690`) and run read-only Edge smoke
        ui_env = dict(os.environ)
        ui_env["ELEDGERCARE_API_PORT"] = str(API_PORT)
        ui_env["NG_CLI_ANALYTICS"] = "false"

        with ui_log_file.open("wb") as ui_out_fh:
            ui_proc = subprocess.Popen(
                [
                    str(node_exe),
                    "node_modules/@angular/cli/bin/ng.js",
                    "serve",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(UI_PORT),
                    "--proxy-config",
                    "proxy.conf.mjs",
                ],
                cwd=str(repo_root / "web"),
                env=ui_env,
                stdout=ui_out_fh,
                stderr=subprocess.STDOUT,
            )
        ui_info = inspect_process(ui_proc.pid, repo_root)

        ui_ready = False
        ui_deadline = time.monotonic() + 120.0
        while time.monotonic() < ui_deadline:
            if ui_proc.poll() is not None:
                raise RuntimeError(f"ng serve exited early with code {ui_proc.returncode}")
            try:
                st_ui, _, _ = http_request(UI_PORT, "GET", "/")
                if st_ui == 200:
                    ui_ready = True
                    break
            except OSError:
                time.sleep(0.5)
        record_assert("owned_ui_4710_listening", ui_ready and ui_info is not None, ui_info)

        edge_helper = guard_owned_repo_path(
            repo_root, "docs/reviews/WP-0010/eld-f4-reviewer/preparation/helpers/verify_f3_seed_ui_edge.mjs"
        )
        edge_cp = run_cmd(
            [
                str(node_exe),
                str(edge_helper),
                "--ui-port",
                str(UI_PORT),
                "--api-port",
                str(API_PORT),
                "--output",
                args.edge_receipt_output,
            ],
            cwd=repo_root,
            timeout_s=180,
        )
        (logs_dir / "03-edge-ui-readonly-smoke.log").write_text(
            redact_secrets(edge_cp.stdout + edge_cp.stderr, secrets), encoding="utf-8", newline="\n"
        )
        record_assert(
            "edge_ui_readonly_smoke_passed",
            edge_cp.returncode == 0,
            {"stdout": edge_cp.stdout.strip(), "stderr": edge_cp.stderr.strip()},
        )

        # Stop UI right away before re-checking DB digest
        ui_stop_receipt = stop_owned_process(ui_proc, ui_info, repo_root)
        ui_proc = None

        # 12. Re-verify canonical 8-table digest is 100% unchanged after replay, GETs, denials, and Edge smoke!
        snap_after = compute_canonical_8table_snapshot(psql_exe, settings, SEED_DATABASE, repo_root)
        record_assert(
            "canonical_8table_digest_invariant_across_readonly_checks",
            snap_before["canonical_8table_sha256"] == snap_after["canonical_8table_sha256"],
            {"canonical_8table_sha256": snap_after["canonical_8table_sha256"]},
        )

    finally:
        if ui_proc is not None:
            ui_stop_receipt = stop_owned_process(ui_proc, ui_info, repo_root)
        if api_proc is not None:
            api_stop_receipt = stop_owned_process(api_proc, api_info, repo_root)

        stop_pg_cp = run_cmd(
            ["pwsh", "-NoProfile", "-File", str(repo_root / "deploy/dev/postgres/stop-cluster.ps1")],
            cwd=repo_root,
        )
        pg_stop_log_text = redact_secrets(stop_pg_cp.stdout + stop_pg_cp.stderr, secrets)
        (logs_dir / "04-pg-cluster-stop.log").write_text(pg_stop_log_text, encoding="utf-8", newline="\n")

        # Sanitize API & UI logs in place so zero credentials or env strings can ever appear
        for lf in (api_log_file, ui_log_file):
            if lf.exists():
                cleaned = redact_secrets(lf.read_text(encoding="utf-8", errors="replace"), secrets)
                lf.write_text(cleaned.replace("\r\n", "\n"), encoding="utf-8", newline="\n")

    # 13. Post-shutdown verification: pg_ctl status == 3, all spawned PIDs absent, ports (5690, 4710, 55439) == 0 listeners
    pg_status_cp = run_cmd([str(pg_ctl_exe), "status", "-D", str(pg_data_dir)], cwd=repo_root)
    pm_alive_after = inspect_process(postmaster_info["pid"], repo_root) if postmaster_info else None
    api_alive_after = inspect_process(api_info["pid"], repo_root) if api_info else None
    ui_alive_after = inspect_process(ui_info["pid"], repo_root) if ui_info else None
    ports_after = observe_ports(REVIEWER_PORTS, repo_root)

    record_assert(
        "all_owned_services_stopped_and_ports_released",
        (
            pg_status_cp.returncode == 3
            and pm_alive_after is None
            and api_alive_after is None
            and ui_alive_after is None
            and all(len(ports_after[str(p)]) == 0 for p in REVIEWER_PORTS)
            and (pg_data_dir / "PG_VERSION").exists()
        ),
        {
            "pg_ctl_status_exit": pg_status_cp.returncode,
            "ports_after": ports_after,
            "seed_cluster_retained": (pg_data_dir / "PG_VERSION").exists(),
        },
    )

    helper_raw = script_path.read_bytes()
    edge_raw = (repo_root / "docs/reviews/WP-0010/eld-f4-reviewer/preparation/helpers/verify_f3_seed_ui_edge.mjs").read_bytes()
    inv_raw = (repo_root / "docs/reviews/WP-0010/eld-f4-reviewer/preparation/helpers/build_preparation_inventory.py").read_bytes()

    receipt_payload = {
        "schema": "eledgercare.wp-0010.reviewer-f3-seed-preparation-receipt/1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "conversation_id": "61105d43-7706-45f2-9176-69d3256248e0",
        "branch": branch_name,
        "frozen_head_sha": head_sha,
        "prior_design_002_sha": PRIOR_DESIGN_002_SHA,
        "authority_prep_sha": AUTHORITY_PREP_SHA,
        "accepted_f3_source_sha": ACCEPTED_F3_SOURCE_SHA,
        "imported_f2_provenance": {
            "f2_source_sha": F2_SOURCE_SHA,
            "f2_executing_head_sha": F2_EXECUTING_HEAD_SHA,
            "f2_reviewer_evidence_sha": F2_REVIEWER_EVIDENCE_SHA,
            "f2_reviewer_004_report_sha": F2_REVIEWER_004_SHA,
            "syn_wo_01_pdf_sha256": F01_PDF_SHA256,
            "syn_wo_01_raw_sha256": F01_RAW_SHA256,
            "syn_mp_01_pdf_sha256": F07_PDF_SHA256,
            "syn_mp_01_raw_sha256": F07_RAW_SHA256,
            "f1_swo_001_pdf_sha256": F1_PDF_SHA256,
        },
        "helpers": {
            "prepare_and_verify_f3_seed_py": {
                "path": "docs/reviews/WP-0010/eld-f4-reviewer/preparation/helpers/prepare_and_verify_f3_seed.py",
                "sha256_raw": sha256_hex(helper_raw),
                "sha256_lf": sha256_hex(helper_raw.replace(b"\r\n", b"\n")),
            },
            "verify_f3_seed_ui_edge_mjs": {
                "path": "docs/reviews/WP-0010/eld-f4-reviewer/preparation/helpers/verify_f3_seed_ui_edge.mjs",
                "sha256_raw": sha256_hex(edge_raw),
                "sha256_lf": sha256_hex(edge_raw.replace(b"\r\n", b"\n")),
            },
            "build_preparation_inventory_py": {
                "path": "docs/reviews/WP-0010/eld-f4-reviewer/preparation/helpers/build_preparation_inventory.py",
                "sha256_raw": sha256_hex(inv_raw),
                "sha256_lf": sha256_hex(inv_raw.replace(b"\r\n", b"\n")),
            },
        },
        "pg18_subset": pg_subset_info,
        "pg_database_metadata": pg_meta,
        "retained_database": SEED_DATABASE,
        "canonical_8table_sha256": snap_after["canonical_8table_sha256"],
        "table_counts": snap_after["counts"],
        "fencing_sequence": snap_after["fencing_seq"],
        "seed_attribution_summary": {
            "imported_f2_extraction_documents": [
                {
                    "seed_key": "SEED-R01",
                    "document_id": r01_doc,
                    "result_id": r01_res,
                    "fencing_tokens": [1],
                    "remapped": False,
                    "live_api_revisions": [1, 2, 3],
                    "latest_reviewed_revision": 2,
                    "current_head_revision": 3,
                    "current_head_status": "draft",
                },
                {
                    "seed_key": "SEED-R02",
                    "document_id": scen2["submission"]["receipt"]["documentId"],
                    "result_id": scen2["completion"]["db_result"]["result_id"],
                    "fencing_tokens": [2],
                    "remapped": False,
                    "live_api_revisions": [],
                    "latest_reviewed_revision": None,
                    "current_head_revision": 0,
                    "current_head_status": "unreviewed",
                },
                {
                    "seed_key": "SEED-R03",
                    "document_id": r03_doc,
                    "result_id": r03_res,
                    "fencing_tokens": [3, 4],
                    "remapped": False,
                    "live_api_revisions": [1],
                    "latest_reviewed_revision": 1,
                    "current_head_revision": 1,
                    "current_head_status": "reviewed",
                },
                {
                    "seed_key": "SEED-R04",
                    "document_id": r04_doc,
                    "result_id": r04_res,
                    "fencing_tokens": [5],
                    "remapped": True,
                    "live_api_revisions": [1],
                    "latest_reviewed_revision": 1,
                    "current_head_revision": 1,
                    "current_head_status": "reviewed",
                },
                {
                    "seed_key": "SEED-R05",
                    "document_id": r05_doc,
                    "result_id": r05_res,
                    "fencing_tokens": [6],
                    "remapped": True,
                    "live_api_revisions": [1, 2],
                    "latest_reviewed_revision": None,
                    "current_head_revision": 2,
                    "current_head_status": "draft",
                },
                {
                    "seed_key": "SEED-R06",
                    "document_id": r06_doc,
                    "result_id": r06_res,
                    "fencing_tokens": [7],
                    "remapped": True,
                    "live_api_revisions": [1],
                    "latest_reviewed_revision": 1,
                    "current_head_revision": 1,
                    "current_head_status": "reviewed",
                },
                {
                    "seed_key": "SEED-R07",
                    "document_id": "01a20400-0000-7000-8000-000000000007",
                    "result_id": "01a20400-4000-7000-8000-000000000007",
                    "fencing_tokens": [8],
                    "remapped": True,
                    "live_api_revisions": [],
                    "latest_reviewed_revision": None,
                    "current_head_revision": 0,
                    "current_head_status": "unreviewed",
                },
            ],
            "live_f1_http_documents": [
                {
                    "seed_key": "SEED-R08",
                    "document_id": rec_r08["documentId"],
                    "job_id": rec_r08["jobId"],
                    "attempt_id": r08_att_id,
                    "fencing_tokens": [9],
                    "status": "failed",
                    "has_diagnostic_partial_output": True,
                },
                {
                    "seed_key": "SEED-R09",
                    "document_id": rec_r09["documentId"],
                    "job_id": rec_r09["jobId"],
                    "attempt_id": None,
                    "fencing_tokens": [],
                    "status": "awaiting_extraction",
                    "has_diagnostic_partial_output": False,
                },
            ],
            "created_review_revisions": created_revisions,
        },
        "canonical_snapshot": snap_after["snapshot"],
        "assertion_count": len(assertions),
        "all_assertions_passed": True,
        "assertions": assertions,
    }

    resource_return = {
        "schema": "eledgercare.wp-0010.reviewer-resource-return/1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "owned_ports": {"api": API_PORT, "ui": UI_PORT, "postgres": PG_PORT},
        "ports_before": ports_before,
        "ports_after": ports_after,
        "processes": {
            "postgres_postmaster": {
                "started": postmaster_info,
                "pg_ctl_status_exit_after_stop": pg_status_cp.returncode,
                "alive_after_stop": pm_alive_after is not None,
            },
            "api_5690": api_stop_receipt,
            "ui_4710": ui_stop_receipt,
        },
        "retained_on_disk": {
            "postgres_data_dir": ".local/postgres-data",
            "database": SEED_DATABASE,
            "canonical_8table_sha256": snap_after["canonical_8table_sha256"],
            "credentials_gitignored": True,
        },
        "gpu_or_model_processes_started": 0,
    }

    out_receipt_path = (repo_root / args.output).resolve()
    out_return_path = (repo_root / args.resource_return_output).resolve()
    out_receipt_path.parent.mkdir(parents=True, exist_ok=True)
    out_return_path.parent.mkdir(parents=True, exist_ok=True)

    receipt_str = json.dumps(receipt_payload, indent=2, ensure_ascii=False) + "\n"
    return_str = json.dumps(resource_return, indent=2, ensure_ascii=False) + "\n"

    # Hard check that zero local secret values appear in any log or receipt!
    assert_no_secrets(receipt_str, secrets, str(out_receipt_path))
    assert_no_secrets(return_str, secrets, str(out_return_path))
    for log_f in logs_dir.glob("*.log"):
        assert_no_secrets(log_f.read_text(encoding="utf-8"), secrets, str(log_f))

    out_receipt_path.write_text(receipt_str, encoding="utf-8", newline="\n")
    out_return_path.write_text(return_str, encoding="utf-8", newline="\n")

    print(
        f"PASS: {len(assertions)} assertions verified; 8-table digest={snap_after['canonical_8table_sha256']}; "
        f"ports {REVIEWER_PORTS} released; {SEED_DATABASE} retained."
    )
    return 0


def http_json_or_raw_submit(port: int, idempotency_key: str, pdf_bytes: bytes) -> tuple[int, dict[str, str], dict]:
    st, hdrs, raw = http_request(
        port,
        "POST",
        "/api/documents",
        headers={
            "Idempotency-Key": idempotency_key,
            "Content-Type": "application/pdf",
        },
        body=pdf_bytes,
    )
    return st, hdrs, json.loads(raw.decode("utf-8"))


if __name__ == "__main__":
    sys.exit(main())
