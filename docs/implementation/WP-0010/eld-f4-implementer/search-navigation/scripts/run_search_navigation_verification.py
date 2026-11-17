"""Decisive post-freeze verification runner for WP-0010 / 006 bounded search-navigation correction.

Executes against clean frozen HEAD with LocalOcr:Enabled=false and zero GPU/model calls:
  1. Verifies clean Git worktree, narrow permitted diff scope (web/src/app/archive/**,
     web/e2e/archive.spec.ts, docs/implementation/WP-0010/eld-f4-implementer/search-navigation/**),
     exact tree-OID identity of unchanged backend/tests/deploy/workers/lockfiles with c383021be177...,
     preservation of prior /003 report & dossier, and static TypeScript inertness/storage invariants.
  2. Runs Angular 22 production bundle build (`ng build`).
  3. Starts owned PostgreSQL 18.7 (`127.0.0.1:55438`) and verifies pre-run invariance of both
     retained `eledgercare_f4_author_seed_f3` (76e7970b...) and `eledgercare_f4_author_migrated`
     (core 8-table ad4f44bc..., projection 78f0f273...).
  4. Runs full Playwright Microsoft Edge E2E suite (`run-browser-checks.ps1` on 5590/4610 against
     disposable `eledgercare_f4_006_e2e`), covering F1-F4 plus new deterministic pending-navigation,
     out-of-order HTTP, external Back/Forward, and cursor/error consistency regressions.
  5. Starts owned API (`5590`, LocalOcr:Enabled=false) + UI (`4610`) against retained
     `eledgercare_f4_author_migrated` and executes both:
       - `verify_search_navigation_edge.mjs` (5 deterministic Promise-latched checks), and
       - `verify_f4_restart_edge.mjs` (integrated F4 PDF `#page=2`, pinned history, & saved-query
         canonical digest 4d314f16...).
  6. Re-verifies post-run invariance of `eledgercare_f4_author_seed_f3` and
     `eledgercare_f4_author_migrated`, stops all owned services (`5590/4610/55438` FREE), confirms
     0 OCR worker processes, removes `.scratch/`, and writes `evidence/verification-summary.json`
     and `resource-return.json` with explicit attribution of unchanged `/003` backend proofs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[6]
PRIOR_DOSSIER_DIR = REPO_ROOT / "docs" / "implementation" / "WP-0010" / "eld-f4-implementer"
SN_DOSSIER_DIR = PRIOR_DOSSIER_DIR / "search-navigation"
EVIDENCE_DIR = SN_DOSSIER_DIR / "evidence"
LOGS_DIR = EVIDENCE_DIR / "logs"
SCREENSHOTS_DIR = EVIDENCE_DIR / "screenshots"

SN_EDGE_HELPER = pathlib.Path(__file__).resolve().parent / "verify_search_navigation_edge.mjs"
PRIOR_REOPEN_EDGE_HELPER = PRIOR_DOSSIER_DIR / "scripts" / "verify_f4_restart_edge.mjs"

CONTINUATION_MERGE_BASE_SHA = "4b8e9b8231b9543b9a09cc8514a6876a70940d7b"
DISPATCH_AUTHORITY_SHA = "cd5237303beaa374c3a60e9de58e45808b55435f"
PRIOR_003_PUBLICATION_SHA = "7c578be6e8abff4d285ea1b519bbcfaeba1bb8c7"
PRIOR_003_SOURCE_SHA = "c383021be1774451ba3034d89255b38b4267353b"
PRIOR_003_EVIDENCE_SHA = "ceec957733d6c00c6b4277e7db3f391ab6ccb6b4"
PRIOR_003_REPORT_RELPATH = "docs/agent-reports/eld-f4-implementer/WP-0010/003_2026-11-17_implementation_eld-f4-implementer.md"
PRIOR_003_REPORT_SHA256 = "da29969c73a7abcb1405a0d809a7c5550f1de4e1f97ccf1df6cbd13f20752a34"
ACCEPTED_DESIGN_SHA = "01a6dab0695c93246b4cf04d1a2098d3b77248d8"

EXPECTED_UNCHANGED_TREES = {
    "src": "9760402fa88dcb343c28b14ad4de1bcb2fbafb2e",
    "tests": "25c21310699086acb818549b2a4c0b99469208f1",
    "deploy": "86e0c73d4b4c07bbdf92ebcd65a0903fc9c039f1",
    "workers/local_ocr": "dc9b69e480f93db1e73ebdd65719efaa9aeab298",
}
EXPECTED_SLNX_BLOB = "c00c2bc5ef46019fb4452fdf0bba7ca2271fc976"
EXPECTED_SEED_F3_SHA256 = "76e7970b50b8fbf968c44e534d6383bdd8251e9f285e2373ea026eeeea157085"
EXPECTED_MIGRATED_CORE_DATA_SHA256 = "ad4f44bcf7c0f7163e91cad81f569bfc4642cbb167c1eaf6c3d1ab9984b2e6d0"
EXPECTED_MIGRATED_PROJECTION_SHA256 = "78f0f273dbdb48629924752cba6f863f11f62764e27161d8df1549ad75ce2ac3"
EXPECTED_SAVED_QUERIES_SHA256 = "4d314f16874de13aefbc6378f560a3db115d2a8bf492e35b7a23be5642bcae7d"

API_PORT = 5590
UI_PORT = 4610
PG_PORT = 55438

SEED_DB = "eledgercare_f4_author_seed_f3"
MIGRATED_DB = "eledgercare_f4_author_migrated"
E2E_DB = "eledgercare_f4_006_e2e"

CANONICAL_8_TABLE_SQL = """
SELECT json_build_object(
  'collation', (
    SELECT json_build_object(
      'datcollate', datcollate,
      'datctype', datctype,
      'encoding', pg_encoding_to_char(encoding)
    ) FROM pg_database WHERE datname = current_database()
  ),
  'migrations', COALESCE((SELECT json_agg("MigrationId" ORDER BY "MigrationId") FROM eledgercare.__ef_migrations_history), '[]'::json),
  'sequence', (SELECT json_build_object('last_value', last_value, 'is_called', is_called) FROM eledgercare.extraction_fencing_seq),
  'row_counts', json_build_object(
    'documents', (SELECT count(*) FROM eledgercare.documents),
    'original_artifacts', (SELECT count(*) FROM eledgercare.original_artifacts),
    'processing_jobs', (SELECT count(*) FROM eledgercare.processing_jobs),
    'execution_attempts', (SELECT count(*) FROM eledgercare.execution_attempts),
    'extraction_results', (SELECT count(*) FROM eledgercare.extraction_results),
    'work_order_review_heads', (SELECT count(*) FROM eledgercare.work_order_review_heads),
    'work_order_review_revisions', (SELECT count(*) FROM eledgercare.work_order_review_revisions),
    'work_order_review_fields', (SELECT count(*) FROM eledgercare.work_order_review_fields)
  ),
  'documents', COALESCE((
    SELECT json_agg(json_build_object(
      'document_id', d.document_id::text,
      'idempotency_key', d.idempotency_key::text,
      'submitted_at', d.submitted_at,
      'byte_length', a.byte_length,
      'octet_length', octet_length(a.bytes),
      'declared_sha256', encode(a.sha256, 'hex'),
      'computed_sha256', encode(sha256(a.bytes), 'hex'),
      'page_count', a.page_count,
      'job_id', j.job_id::text,
      'job_status', j.status,
      'attempt_count', j.attempt_count,
      'latest_fencing_token', j.latest_fencing_token,
      'retried_from_attempt_id', j.retried_from_attempt_id::text
    ) ORDER BY d.submitted_at DESC, d.document_id DESC)
    FROM eledgercare.documents d
    JOIN eledgercare.original_artifacts a ON a.document_id = d.document_id
    JOIN eledgercare.processing_jobs j ON j.document_id = d.document_id
  ), '[]'::json),
  'attempts', COALESCE((
    SELECT json_agg(json_build_object(
      'attempt_id', at.attempt_id::text,
      'document_id', at.document_id::text,
      'attempt_number', at.attempt_number,
      'fencing_token', at.fencing_token,
      'retried_from_attempt_id', at.retried_from_attempt_id::text,
      'status', at.status,
      'phase', at.phase,
      'failure_code', at.failure_code,
      'exit_code', at.exit_code,
      'has_diagnostic_raw_output', (at.diagnostic_raw_output_utf8 IS NOT NULL)
    ) ORDER BY at.fencing_token)
    FROM eledgercare.execution_attempts at
  ), '[]'::json),
  'results', COALESCE((
    SELECT json_agg(json_build_object(
      'result_id', r.result_id::text,
      'document_id', r.document_id::text,
      'attempt_id', r.attempt_id::text,
      'fencing_token', r.fencing_token,
      'schema_version', r.schema_version,
      'input_sha256', encode(r.input_sha256, 'hex'),
      'page_count', r.page_count,
      'output_page_count', r.output_page_count,
      'raw_output_byte_length', r.raw_output_byte_length,
      'raw_octet_length', octet_length(r.raw_output_bytes),
      'declared_raw_sha256', encode(r.raw_output_sha256, 'hex'),
      'computed_raw_sha256', encode(sha256(r.raw_output_bytes), 'hex'),
      'worker_source_sha256', encode(r.worker_source_digest, 'hex'),
      'worker_config_sha256', encode(r.worker_config_digest, 'hex'),
      'finish_reason', r.finish_reason
    ) ORDER BY r.fencing_token)
    FROM eledgercare.extraction_results r
  ), '[]'::json),
  'review_heads', COALESCE((
    SELECT json_agg(json_build_object(
      'document_id', h.document_id::text,
      'result_id', h.result_id::text,
      'current_revision_number', h.current_revision_number,
      'current_revision_id', h.current_revision_id::text,
      'current_status', h.current_status,
      'greatest_reviewed_revision_number', (
        SELECT max(rv.revision_number)
        FROM eledgercare.work_order_review_revisions rv
        WHERE rv.document_id = h.document_id AND rv.status = 'reviewed'
      ),
      'input_sha256', encode(h.input_sha256, 'hex'),
      'raw_output_sha256', encode(h.raw_output_sha256, 'hex')
    ) ORDER BY h.document_id)
    FROM eledgercare.work_order_review_heads h
  ), '[]'::json),
  'review_revisions', COALESCE((
    SELECT json_agg(json_build_object(
      'revision_id', rv.revision_id::text,
      'document_id', rv.document_id::text,
      'result_id', rv.result_id::text,
      'revision_number', rv.revision_number,
      'previous_revision_number', rv.previous_revision_number,
      'status', rv.status,
      'idempotency_key', rv.idempotency_key::text,
      'request_sha256', encode(rv.request_sha256, 'hex'),
      'operator_display_label', rv.operator_display_label,
      'accepted_field_count', rv.accepted_field_count,
      'edited_field_count', rv.edited_field_count,
      'unknown_field_count', rv.unknown_field_count,
      'unreviewed_field_count', rv.unreviewed_field_count,
      'saved_at', rv.saved_at
    ) ORDER BY rv.document_id, rv.revision_number)
    FROM eledgercare.work_order_review_revisions rv
  ), '[]'::json),
  'review_fields', COALESCE((
    SELECT json_agg(json_build_object(
      'revision_id', rf.revision_id::text,
      'field_ordinal', rf.field_ordinal,
      'field_key', rf.field_key,
      'decision', rf.decision,
      'human_value', rf.human_value,
      'unknown_reason', rf.unknown_reason,
      'consulted_page_number', rf.consulted_page_number,
      'consulted_block_ordinal', rf.consulted_block_ordinal,
      'consulted_table_row', rf.consulted_table_row,
      'consulted_table_column', rf.consulted_table_column,
      'consulted_quote', rf.consulted_quote
    ) ORDER BY rf.revision_id, rf.field_ordinal)
    FROM eledgercare.work_order_review_fields rf
  ), '[]'::json)
)::text;
"""

PROJECTION_TABLES_SQL = """
SELECT json_build_object(
  'projection_count', (SELECT count(*) FROM eledgercare.archive_result_projections),
  'unit_count', (SELECT count(*) FROM eledgercare.archive_projection_units),
  'projections', COALESCE((
    SELECT json_agg(json_build_object(
      'result_id', p.result_id::text,
      'document_id', p.document_id::text,
      'projection_version', p.projection_version,
      'raw_output_sha256', encode(p.raw_output_sha256, 'hex'),
      'projection_sha256', encode(p.projection_sha256, 'hex'),
      'unit_count', p.unit_count,
      'has_fallback', p.has_fallback
    ) ORDER BY p.result_id)
    FROM eledgercare.archive_result_projections p
  ), '[]'::json),
  'units', COALESCE((
    SELECT json_agg(json_build_object(
      'result_id', u.result_id::text,
      'unit_ordinal', u.unit_ordinal,
      'document_id', u.document_id::text,
      'page_number', u.page_number,
      'unit_kind', u.unit_kind,
      'is_fallback', u.is_fallback,
      'search_text_sha256', encode(sha256(convert_to(u.search_text, 'UTF8')), 'hex'),
      'search_text_chars', char_length(u.search_text)
    ) ORDER BY u.result_id, u.unit_ordinal)
    FROM eledgercare.archive_projection_units u
  ), '[]'::json)
)::text;
"""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def scrub_secrets(text: str, secrets: list[str]) -> str:
    out = text
    for sec in secrets:
        if sec:
            out = out.replace(sec, "[REDACTED_LOCAL_SECRET]")
    return out


def run_cmd(
    cmd: list[str],
    cwd: pathlib.Path,
    extra_env: dict[str, str] | None = None,
    input_text: str | None = None,
    timeout_s: float = 600.0,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
        check=False,
    )


def run_logged(
    name: str,
    cmd: list[str],
    cwd: pathlib.Path,
    secrets: list[str],
    extra_env: dict[str, str] | None = None,
) -> dict:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    started = utc_now()
    proc = run_cmd(cmd, cwd=cwd, extra_env=extra_env)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    combined = (
        f"$ {' '.join(cmd)}\n"
        f"[exit={proc.returncode}, elapsed_ms={elapsed_ms}]\n"
        f"--- STDOUT ---\n{scrub_secrets(proc.stdout, secrets)}\n"
        f"--- STDERR ---\n{scrub_secrets(proc.stderr, secrets)}\n"
    )
    log_path = LOGS_DIR / f"{name}.log"
    log_path.write_text(combined, encoding="utf-8", newline="\n")
    if proc.returncode != 0:
        raise RuntimeError(f"Step '{name}' failed with exit code {proc.returncode}; see {log_path}")
    return {
        "step": name,
        "command": [scrub_secrets(c, secrets) for c in cmd],
        "cwd": "." if cwd == REPO_ROOT else cwd.relative_to(REPO_ROOT).as_posix(),
        "started_utc": started,
        "elapsed_ms": elapsed_ms,
        "exit_code": proc.returncode,
        "log_relpath": log_path.relative_to(REPO_ROOT).as_posix(),
        "log_sha256": sha256_file(log_path),
    }


def git_output(args: list[str]) -> str:
    cp = run_cmd(["git", *args], cwd=REPO_ROOT)
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr}")
    return cp.stdout.strip()


def invoke_psql(
    psql_exe: pathlib.Path,
    host: str,
    port: int,
    user: str,
    password: str,
    db: str,
    sql: str,
) -> subprocess.CompletedProcess[str]:
    cp = run_cmd(
        [
            str(psql_exe),
            "-X",
            "-q",
            "-A",
            "-t",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            host,
            "-p",
            str(port),
            "-U",
            user,
            "-d",
            db,
            "-f",
            "-",
        ],
        cwd=REPO_ROOT,
        extra_env={"PGPASSWORD": password},
        input_text=sql,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"psql query on {db} failed: {cp.stderr}")
    return cp


def query_canonical_8_table(psql_exe: pathlib.Path, settings: dict, db: str) -> dict:
    raw = invoke_psql(
        psql_exe,
        settings["host"],
        int(settings["port"]),
        settings["adminUser"],
        settings["adminPassword"],
        db,
        CANONICAL_8_TABLE_SQL,
    ).stdout.strip()
    parsed = json.loads(raw)
    full_sha = sha256_bytes(json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    data_only = {k: v for k, v in parsed.items() if k != "migrations"}
    data_only_sha = sha256_bytes(
        json.dumps(data_only, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    return {
        "canonical_8_table_and_migrations_sha256": full_sha,
        "core_data_without_migrations_sha256": data_only_sha,
    }


def query_projection_snapshot(psql_exe: pathlib.Path, settings: dict, db: str) -> str:
    raw = invoke_psql(
        psql_exe,
        settings["host"],
        int(settings["port"]),
        settings["adminUser"],
        settings["adminPassword"],
        db,
        PROJECTION_TABLES_SQL,
    ).stdout.strip()
    parsed = json.loads(raw)
    return sha256_bytes(json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def observe_ports(ports: tuple[int, ...]) -> dict[str, list[dict]]:
    ps = (
        "$out = @{}; "
        f"foreach ($p in @({','.join(str(p) for p in ports)})) {{ "
        "$conns = @(Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue | "
        "ForEach-Object { @{ localAddress = $_.LocalAddress; localPort = [int]$_.LocalPort; owningPid = [int]$_.OwningProcess } }); "
        "$out[\"$p\"] = $conns "
        "}; "
        "$out | ConvertTo-Json -Compress -Depth 4"
    )
    cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps], cwd=REPO_ROOT)
    if cp.returncode != 0:
        raise RuntimeError(f"Port check failed: {cp.stderr}")
    return json.loads(cp.stdout)


def assert_ports_unbound(ports: tuple[int, ...], timeout_s: float = 15.0) -> dict[str, list[dict]]:
    deadline = time.monotonic() + timeout_s
    latest = observe_ports(ports)
    while time.monotonic() < deadline:
        if all(len(latest[str(p)]) == 0 for p in ports):
            return latest
        time.sleep(0.25)
        latest = observe_ports(ports)
    raise RuntimeError(f"Expected ports {ports} to be unbound, found: {latest}")


def count_ocr_worker_processes() -> int:
    self_pid = os.getpid()
    ps = (
        "@(Get-CimInstance Win32_Process | Where-Object { "
        f"$_.ProcessId -ne {self_pid} -and $_.ProcessId -ne $PID -and "
        "$_.Name -like 'python*' -and $_.CommandLine -like '*local_ocr*run_worker*' "
        "}).Count"
    )
    cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps], cwd=REPO_ROOT)
    if cp.returncode != 0:
        raise RuntimeError(f"Worker process count check failed: {cp.stderr}")
    return int(cp.stdout.strip())


def is_permitted_006_path(rel: str) -> bool:
    return (
        rel.startswith("web/src/app/archive/")
        or rel == "web/e2e/archive.spec.ts"
        or rel.startswith("docs/implementation/WP-0010/eld-f4-implementer/search-navigation/")
    )


def run_static_and_git_audit(require_clean: bool) -> dict:
    status = git_output(["status", "--porcelain"])
    if require_clean and status:
        raise RuntimeError(f"Worktree must be clean before decisive post-freeze execution:\n{status}")

    head_sha = git_output(["rev-parse", "HEAD"])
    changed_paths = [
        ln.strip()
        for ln in git_output(["diff", "--name-only", CONTINUATION_MERGE_BASE_SHA, "HEAD"]).splitlines()
        if ln.strip()
    ]
    unpermitted = [p for p in changed_paths if not is_permitted_006_path(p)]
    if unpermitted:
        raise RuntimeError(f"Unpermitted paths modified outside WP-0010 / 006 scope: {unpermitted}")

    observed_trees = {
        rel: git_output(["rev-parse", f"HEAD:{rel}"])
        for rel in EXPECTED_UNCHANGED_TREES
    }
    for rel, expected_oid in EXPECTED_UNCHANGED_TREES.items():
        if observed_trees[rel] != expected_oid:
            raise RuntimeError(f"Unchanged tree {rel} drifted: expected {expected_oid}, got {observed_trees[rel]}")

    slnx_oid = git_output(["rev-parse", "HEAD:ELedgerCare.slnx"])
    if slnx_oid != EXPECTED_SLNX_BLOB:
        raise RuntimeError(f"ELedgerCare.slnx drifted: {slnx_oid}")

    prior_report_sha = sha256_file(REPO_ROOT / PRIOR_003_REPORT_RELPATH)
    if prior_report_sha != PRIOR_003_REPORT_SHA256:
        raise RuntimeError(f"Immutable /003 report drifted: {prior_report_sha}")

    ts_files = sorted((REPO_ROOT / "web" / "src").rglob("*.ts"))
    violations: list[str] = []
    for f in ts_files:
        txt = f.read_text(encoding="utf-8")
        code_only = "\n".join(
            ln for ln in txt.splitlines() if not ln.lstrip().startswith("//") and not ln.lstrip().startswith("*")
        )
        if "innerHTML" in code_only or "bypassSecurityTrustHtml" in code_only:
            violations.append(f"{f.relative_to(REPO_ROOT)}: prohibited innerHTML/bypassSecurityTrustHtml")
        if ("review" in f.parts or "archive" in f.parts) and (
            "localStorage" in code_only or "sessionStorage" in code_only or "indexedDB" in code_only
        ):
            violations.append(f"{f.relative_to(REPO_ROOT)}: prohibited browser storage call")

    if violations:
        raise RuntimeError(f"Static TypeScript audit failed: {violations}")

    return {
        "clean_worktree": status == "",
        "frozen_head_sha": head_sha,
        "continuation_merge_base_sha": CONTINUATION_MERGE_BASE_SHA,
        "dispatch_authority_sha": DISPATCH_AUTHORITY_SHA,
        "prior_003_publication_sha": PRIOR_003_PUBLICATION_SHA,
        "prior_003_source_sha": PRIOR_003_SOURCE_SHA,
        "prior_003_evidence_sha": PRIOR_003_EVIDENCE_SHA,
        "accepted_design_sha": ACCEPTED_DESIGN_SHA,
        "changed_paths_since_merge_base": changed_paths,
        "product_trees": {
            **observed_trees,
            "web": git_output(["rev-parse", "HEAD:web"]),
        },
        "unchanged_backend_and_worker_trees_verified": True,
        "prior_003_report_sha256_preserved": prior_report_sha,
        "audited_ts_files": len(ts_files),
        "violations": 0,
    }


def start_owned_api_and_ui(app_conn_str: str) -> tuple[subprocess.Popen[str], dict, subprocess.Popen[str], dict]:
    assert_ports_unbound((API_PORT, UI_PORT))
    api_dir = REPO_ROOT / "src" / "ELedgerCare.Api" / "bin" / "Release" / "net10.0"
    api_dll = api_dir / "ELedgerCare.Api.dll"
    if not api_dll.exists():
        raise RuntimeError(f"Expected prebuilt Release API assembly at {api_dll}")

    api_log = LOGS_DIR / f"owned-api-{API_PORT}.log"
    ui_log = LOGS_DIR / f"owned-ui-{UI_PORT}.log"

    api_env = {
        **os.environ,
        "ASPNETCORE_ENVIRONMENT": "Production",
        "ConnectionStrings__Runtime": app_conn_str,
        "Api__Port": str(API_PORT),
        "LocalOcr__Enabled": "false",
        "DOTNET_NOLOGO": "1",
    }
    api_fh = api_log.open("w", encoding="utf-8", newline="\n")
    api_proc = subprocess.Popen(
        ["dotnet", str(api_dll)],
        cwd=str(api_dir),
        env=api_env,
        stdout=api_fh,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )

    deadline = time.monotonic() + 45.0
    while time.monotonic() < deadline:
        if api_proc.poll() is not None:
            api_fh.close()
            raise RuntimeError(f"Owned API exited early ({api_proc.returncode}); see {api_log}")
        p = observe_ports((API_PORT,))
        if any(c["owningPid"] == api_proc.pid for c in p[str(API_PORT)]):
            break
        time.sleep(0.2)
    else:
        api_fh.close()
        raise RuntimeError(f"Owned API did not bind {API_PORT} within 45s")

    ui_env = {
        **os.environ,
        "ELEDGERCARE_API_PORT": str(API_PORT),
        "NG_CLI_ANALYTICS": "false",
    }
    ui_fh = ui_log.open("w", encoding="utf-8", newline="\n")
    ng_bin = REPO_ROOT / "web" / "node_modules" / "@angular" / "cli" / "bin" / "ng.js"
    ui_proc = subprocess.Popen(
        [
            "node",
            str(ng_bin),
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(UI_PORT),
            "--proxy-config",
            "proxy.conf.mjs",
        ],
        cwd=str(REPO_ROOT / "web"),
        env=ui_env,
        stdout=ui_fh,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )

    no_proxy_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    ui_deadline = time.monotonic() + 90.0
    while time.monotonic() < ui_deadline:
        if ui_proc.poll() is not None:
            ui_fh.close()
            raise RuntimeError(f"Owned UI exited early ({ui_proc.returncode}); see {ui_log}")
        try:
            with no_proxy_opener.open(f"http://127.0.0.1:{UI_PORT}/", timeout=2.0) as resp:
                if resp.status == 200:
                    break
        except Exception:
            pass
        time.sleep(0.3)
    else:
        ui_fh.close()
        raise RuntimeError(f"Owned UI did not respond 200 on {UI_PORT} within 90s")

    return (
        api_proc,
        {"pid": api_proc.pid, "port": API_PORT, "log": api_log.relative_to(REPO_ROOT).as_posix(), "fh": api_fh},
        ui_proc,
        {"pid": ui_proc.pid, "port": UI_PORT, "log": ui_log.relative_to(REPO_ROOT).as_posix(), "fh": ui_fh},
    )


def stop_owned_proc(proc: subprocess.Popen[str] | None, fh=None) -> None:
    try:
        if proc is not None and proc.poll() is None:
            run_cmd(["taskkill", "/PID", str(proc.pid), "/T", "/F"], cwd=REPO_ROOT)
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
    finally:
        if fh is not None:
            try:
                fh.close()
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()

    started_utc = utc_now()
    if EVIDENCE_DIR.exists():
        shutil.rmtree(EVIDENCE_DIR)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    settings = json.loads((REPO_ROOT / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
    secrets = [
        str(settings.get("adminPassword", "")),
        str(settings.get("migratorPassword", "")),
        str(settings.get("appPassword", "")),
    ]
    psql_exe = REPO_ROOT / ".local" / "tools" / "pgsql-18.7-1" / "bin" / "psql.exe"
    dotnet_env = {
        "DOTNET_CLI_HOME": str(REPO_ROOT / ".local" / "dotnet-home"),
        "NUGET_PACKAGES": str(REPO_ROOT / ".local" / "nuget" / "packages"),
        "DOTNET_NOLOGO": "1",
        "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
    }

    static_audit = run_static_and_git_audit(require_clean=args.require_clean)
    assert_ports_unbound((API_PORT, UI_PORT, PG_PORT))

    steps: list[dict] = []
    api_proc = None
    api_fh = None
    ui_proc = None
    ui_fh = None
    pg_started = False
    pg_pid = None
    api_pid = None
    ui_pid = None

    try:
        # 1. Angular 22 production bundle build
        steps.append(
            run_logged(
                "01-ng-build-production",
                ["node", "node_modules/@angular/cli/bin/ng.js", "build"],
                REPO_ROOT / "web",
                secrets,
                extra_env={"NG_CLI_ANALYTICS": "false"},
            )
        )

        # 2. Start owned PostgreSQL 18.7 cluster on 127.0.0.1:55438
        steps.append(
            run_logged(
                "02-pg-cluster-start",
                ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"],
                REPO_ROOT,
                secrets,
            )
        )
        pg_started = True
        pg_pid = int((REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0])

        # Verify untouched retained databases BEFORE tests
        seed_pre = query_canonical_8_table(psql_exe, settings, SEED_DB)
        migrated_core_pre = query_canonical_8_table(psql_exe, settings, MIGRATED_DB)
        migrated_proj_pre = query_projection_snapshot(psql_exe, settings, MIGRATED_DB)
        if seed_pre["canonical_8_table_and_migrations_sha256"] != EXPECTED_SEED_F3_SHA256:
            raise RuntimeError(f"Retained {SEED_DB} digest mismatch before tests: {seed_pre}")
        if migrated_core_pre["core_data_without_migrations_sha256"] != EXPECTED_MIGRATED_CORE_DATA_SHA256:
            raise RuntimeError(f"Retained {MIGRATED_DB} core data digest mismatch before tests: {migrated_core_pre}")
        if migrated_proj_pre != EXPECTED_MIGRATED_PROJECTION_SHA256:
            raise RuntimeError(f"Retained {MIGRATED_DB} projection digest mismatch before tests: {migrated_proj_pre}")

        # 3. Full Playwright Microsoft Edge E2E suite (F1-F4 + new pending-nav/out-of-order specs)
        steps.append(
            run_logged(
                "03-playwright-edge-e2e",
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
                REPO_ROOT,
                secrets,
                extra_env={
                    **dotnet_env,
                    "ELEDGERCARE_F3_SCREENSHOT_DIR": str(REPO_ROOT / ".scratch" / "f3-e2e-shots"),
                    "ELEDGERCARE_F4_SCREENSHOT_DIR": str(REPO_ROOT / ".scratch" / "f4-e2e-shots"),
                },
            )
        )

        # Drop disposable E2E database
        invoke_psql(
            psql_exe,
            settings["host"],
            int(settings["port"]),
            settings["adminUser"],
            settings["adminPassword"],
            "postgres",
            f"DROP DATABASE IF EXISTS {E2E_DB} WITH (FORCE); DROP DATABASE IF EXISTS eledgercare_f4_006_dryrun WITH (FORCE);",
        )

        # 4. Start owned API (5590, LocalOcr:Enabled=false) + UI (4610) on retained migrated DB
        app_conn_migrated = (
            f"Host={settings['host']};Port={settings['port']};Database={MIGRATED_DB};"
            f"Username={settings['appUser']};Password={settings['appPassword']}"
        )
        api_proc, api_meta, ui_proc, ui_meta = start_owned_api_and_ui(app_conn_migrated)
        api_fh = api_meta["fh"]
        ui_fh = ui_meta["fh"]
        api_pid = api_proc.pid
        ui_pid = ui_proc.pid

        # 4a. Focused deterministic Promise-latched search-navigation & out-of-order response checks
        sn_receipt_json = EVIDENCE_DIR / "search-navigation-edge-receipt.json"
        steps.append(
            run_logged(
                "04-edge-search-navigation-deterministic",
                [
                    "node",
                    str(SN_EDGE_HELPER),
                    "--mode",
                    "post-fix",
                    "--api-port",
                    str(API_PORT),
                    "--ui-port",
                    str(UI_PORT),
                    "--output",
                    str(sn_receipt_json),
                    "--screenshot-dir",
                    str(SCREENSHOTS_DIR),
                ],
                REPO_ROOT,
                secrets,
                extra_env={"PLAYWRIGHT_BROWSERS_PATH": str(REPO_ROOT / ".local" / "ms-playwright")},
            )
        )

        # 4b. Integrated F4 source reopening & saved-query regression against 7-seed migrated DB
        reopen_receipt_json = EVIDENCE_DIR / "edge-f4-reopen-post-006.json"
        steps.append(
            run_logged(
                "05-edge-f4-reopen-regression",
                [
                    "node",
                    str(PRIOR_REOPEN_EDGE_HELPER),
                    "--phase",
                    "post-006",
                    "--api-port",
                    str(API_PORT),
                    "--ui-port",
                    str(UI_PORT),
                    "--output",
                    str(reopen_receipt_json),
                    "--screenshot-dir",
                    str(SCREENSHOTS_DIR),
                ],
                REPO_ROOT,
                secrets,
                extra_env={"PLAYWRIGHT_BROWSERS_PATH": str(REPO_ROOT / ".local" / "ms-playwright")},
            )
        )
        reopen_receipt = json.loads(reopen_receipt_json.read_text(encoding="utf-8"))
        if reopen_receipt["savedQueryResponsesCanonicalSha256"] != EXPECTED_SAVED_QUERIES_SHA256:
            raise RuntimeError(
                f"Saved query canonical digest drifted: {reopen_receipt['savedQueryResponsesCanonicalSha256']}"
            )

        stop_owned_proc(ui_proc, ui_fh)
        ui_proc, ui_fh = None, None
        stop_owned_proc(api_proc, api_fh)
        api_proc, api_fh = None, None

        # Verify untouched retained databases AFTER all checks
        seed_post = query_canonical_8_table(psql_exe, settings, SEED_DB)
        migrated_core_post = query_canonical_8_table(psql_exe, settings, MIGRATED_DB)
        migrated_proj_post = query_projection_snapshot(psql_exe, settings, MIGRATED_DB)
        if seed_post["canonical_8_table_and_migrations_sha256"] != EXPECTED_SEED_F3_SHA256:
            raise RuntimeError(f"Retained {SEED_DB} digest mutated during /006 verification!")
        if migrated_core_post["core_data_without_migrations_sha256"] != EXPECTED_MIGRATED_CORE_DATA_SHA256:
            raise RuntimeError(f"Retained {MIGRATED_DB} core data mutated during /006 verification!")
        if migrated_proj_post != EXPECTED_MIGRATED_PROJECTION_SHA256:
            raise RuntimeError(f"Retained {MIGRATED_DB} projections mutated during /006 verification!")

        retained_dbs = [
            ln.strip()
            for ln in invoke_psql(
                psql_exe,
                settings["host"],
                int(settings["port"]),
                settings["adminUser"],
                settings["adminPassword"],
                "postgres",
                "SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres' ORDER BY datname;",
            ).stdout.splitlines()
            if ln.strip()
        ]

        # 5. Stop PostgreSQL 18.7 cluster cleanly
        steps.append(
            run_logged(
                "06-pg-cluster-stop-final",
                ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"],
                REPO_ROOT,
                secrets,
            )
        )
        pg_started = False
        listeners_final = assert_ports_unbound((API_PORT, UI_PORT, PG_PORT))
        worker_procs = count_ocr_worker_processes()
        if worker_procs != 0:
            raise RuntimeError(f"Expected 0 OCR worker processes, found {worker_procs}")

        shutil.rmtree(REPO_ROOT / ".scratch", ignore_errors=True)
        completed_utc = utc_now()

        summary = {
            "packet": "WP-0010",
            "sequence": "006",
            "slice": "F4 bounded search-navigation correction",
            "author": "eld-f4-implementer",
            "started_utc": started_utc,
            "completed_utc": completed_utc,
            "static_and_git_audit": static_audit,
            "retained_database_invariance": {
                "seed_database": SEED_DB,
                "seed_sha256_before": seed_pre["canonical_8_table_and_migrations_sha256"],
                "seed_sha256_after": seed_post["canonical_8_table_and_migrations_sha256"],
                "seed_unchanged": True,
                "migrated_database": MIGRATED_DB,
                "migrated_core_8_table_sha256_before": migrated_core_pre["core_data_without_migrations_sha256"],
                "migrated_core_8_table_sha256_after": migrated_core_post["core_data_without_migrations_sha256"],
                "migrated_projection_sha256_before": migrated_proj_pre,
                "migrated_projection_sha256_after": migrated_proj_post,
                "saved_queries_canonical_sha256": reopen_receipt["savedQueryResponsesCanonicalSha256"],
                "migrated_unchanged": True,
            },
            "executed_steps": steps,
            "attributed_unchanged_backend_proofs": {
                "attributed_to_author_003_source_sha": PRIOR_003_SOURCE_SHA,
                "attributed_to_author_003_evidence_sha": PRIOR_003_EVIDENCE_SHA,
                "attributed_to_author_003_publication_sha": PRIOR_003_PUBLICATION_SHA,
                "unchanged_trees_verified": EXPECTED_UNCHANGED_TREES,
                "note": (
                    "Backend src/, tests/, deploy/, and workers/local_ocr/ trees are byte-identical to "
                    "c383021be1774451ba3034d89255b38b4267353b. Prior /003 worker CPU unit tests (9/9), "
                    ".NET Release test suite (95/95), runtime 42501 privilege audit (13/13), forward "
                    "migration, and PostgreSQL+API restart proofs remain attributed to ceec957733d6... / "
                    "7c578be6e8ab... and were not gratuitously repeated."
                ),
            },
            "zero_ocr_worker_processes": True,
            "zero_gpu_or_model_calls": True,
            "all_ports_unbound_after_cleanup": True,
        }
        (EVIDENCE_DIR / "verification-summary.json").write_text(
            json.dumps(summary, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        resource_return = {
            "verified_utc": completed_utc,
            "ports": {str(API_PORT): "FREE", str(UI_PORT): "FREE", str(PG_PORT): "FREE"},
            "observed_listeners": listeners_final,
            "stopped_processes": {
                "postmaster_pid": pg_pid,
                "api_pid": api_pid,
                "ui_pid": ui_pid,
            },
            "ocr_worker_processes_running": 0,
            "scratch_directory_present": (REPO_ROOT / ".scratch").exists(),
            "retained_databases_in_local_cluster": retained_dbs,
            "seed_f3_sha256_preserved": seed_post["canonical_8_table_and_migrations_sha256"],
            "migrated_core_8_table_sha256_preserved": migrated_core_post["core_data_without_migrations_sha256"],
            "migrated_projection_sha256_preserved": migrated_proj_post,
        }
        (SN_DOSSIER_DIR / "resource-return.json").write_text(
            json.dumps(resource_return, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print("WP-0010 / 006 decisive verification PASSED (6/6 executed steps green; all owned ports FREE).")
    finally:
        stop_owned_proc(ui_proc, ui_fh)
        stop_owned_proc(api_proc, api_fh)
        if pg_started:
            run_cmd(["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"], cwd=REPO_ROOT)
        shutil.rmtree(REPO_ROOT / ".scratch", ignore_errors=True)


if __name__ == "__main__":
    main()
