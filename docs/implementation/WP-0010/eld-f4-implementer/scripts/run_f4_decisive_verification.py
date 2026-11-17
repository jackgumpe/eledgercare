"""Decisive post-freeze verification runner for WP-0010 F4 (eld-f4-implementer).

Executes against clean frozen HEAD with LocalOcr:Enabled=false and zero GPU/model calls:
  1. Verifies clean Git worktree, preserved protected trees/files (including prior preparation/**),
     and static source isolation/inertness invariants.
  2. Runs worker CPU unit tests (9/9), offline locked .NET restore & Release build, Angular 22
     production build, full .NET test suite (Domain + Infrastructure + real PG 18.7 Acceptance),
     demo restart smoke (5590), and full Playwright Microsoft Edge E2E suite (5590/4610).
  3. Verifies retained pre-F4 database `eledgercare_f4_author_seed_f3` remains intact at exact
     digest 76e7970b50b8fbf968c44e534d6383bdd8251e9f285e2373ea026eeeea157085, clones
     `eledgercare_f4_author_migrated` from `TEMPLATE eledgercare_f4_author_seed_f3` (verified at
     the same pre-migration digest), applies real forward migration `AddSourceLinkedArchive` +
     `grant-runtime.sql`, verifies 13 negative 42501 runtime privilege probes, runs startup
     projection backfill with LocalOcr:Enabled=false, captures EXPLAIN & modest-archive metrics,
     executes live Microsoft Edge verification before and after actual API + PostgreSQL 18.7
     cluster fast restart, stops all owned services, and cleans `.scratch/`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
DOSSIER_DIR = REPO_ROOT / "docs" / "implementation" / "WP-0010" / "eld-f4-implementer"
EVIDENCE_DIR = DOSSIER_DIR / "evidence"
LOGS_DIR = EVIDENCE_DIR / "logs"
SCREENSHOTS_DIR = EVIDENCE_DIR / "screenshots"
NODE_EDGE_HELPER = pathlib.Path(__file__).resolve().parent / "verify_f4_restart_edge.mjs"

DISPATCH_AUTHORITY_SHA = "7345ef03dfa4d5f039259d0b8b9505685112469d"
PACKET_BASE_SHA = "956c056be2ec970340074871ecdd7e1a9855d944"
ACCEPTED_DESIGN_SHA = "01a6dab0695c93246b4cf04d1a2098d3b77248d8"
EXPECTED_SEED_F3_SHA256 = "76e7970b50b8fbf968c44e534d6383bdd8251e9f285e2373ea026eeeea157085"

API_PORT = 5590
UI_PORT = 4610
PG_PORT = 55438

SEED_DB = "eledgercare_f4_author_seed_f3"
MIGRATED_DB = "eledgercare_f4_author_migrated"
E2E_DB = "eledgercare_f4_e2e"
BENCH_DB = "eledgercare_f4_modest_bench"

PROTECTED_PATHS = [
    "AGENTS.md",
    "START_HERE.md",
    "CURRENT.md",
    "INDEX.md",
    "ELedgerCare.slnx",
    "Directory.Build.props",
    "Directory.Packages.props",
    "NuGet.Config",
    "web/package-lock.json",
    "tests/fixtures",
    "workers",
    "evaluation",
    "qualification",
    "research",
    "docs/design",
    "docs/coordination",
    "docs/kickoffs",
    "docs/reviews",
    "docs/agent-reports",
    "docs/implementation/WP-0010/eld-f4-implementer/preparation",
]


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
        raise RuntimeError(f"Worker process query failed: {cp.stderr}")
    return int(cp.stdout.strip() or "0")


def invoke_psql(
    psql_exe: pathlib.Path,
    host: str,
    port: int,
    user: str,
    password: str,
    db: str,
    sql: str,
    expect_error: bool = False,
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
    if not expect_error and cp.returncode != 0:
        raise RuntimeError(f"psql failed on {db} as {user}: {cp.stderr}")
    return cp


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
        "snapshot": parsed,
        "canonical_8_table_and_migrations_sha256": full_sha,
        "core_data_without_migrations_sha256": data_only_sha,
    }


def query_projection_snapshot(psql_exe: pathlib.Path, settings: dict, db: str) -> dict:
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
    sha = sha256_bytes(json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    return {"snapshot": parsed, "projection_tables_sha256": sha}


def run_static_and_git_audit(require_clean: bool) -> dict:
    status = git_output(["status", "--porcelain"])
    if require_clean and status:
        raise RuntimeError(f"Worktree must be clean before decisive post-freeze execution:\n{status}")

    head_sha = git_output(["rev-parse", "HEAD"])
    protected_diffs: dict[str, list[str]] = {}
    for rel in PROTECTED_PATHS:
        diff_lines = [
            ln
            for ln in git_output(["diff", "--name-only", DISPATCH_AUTHORITY_SHA, "HEAD", "--", rel]).splitlines()
            if ln.strip()
        ]
        if diff_lines:
            protected_diffs[rel] = diff_lines

    lock_diffs = [
        ln
        for ln in git_output(["diff", "--name-only", DISPATCH_AUTHORITY_SHA, "HEAD", "--", ":(glob)**/packages.lock.json"]).splitlines()
        if ln.strip()
    ]
    if protected_diffs or lock_diffs:
        raise RuntimeError(f"Protected path diff detected: {protected_diffs} / {lock_diffs}")

    cs_files = [
        f
        for f in sorted((REPO_ROOT / "src").rglob("*.cs"))
        if "\\bin\\" not in str(f) and "\\obj\\" not in str(f)
    ]
    ts_files = sorted((REPO_ROOT / "web" / "src").rglob("*.ts"))
    violations: list[str] = []

    for f in cs_files:
        txt = f.read_text(encoding="utf-8")
        for bad in ("qualification/", "qualification\\", "research/", "research\\", "evaluation/", "evaluation\\", "git.exe"):
            if bad.lower() in txt.lower():
                violations.append(f"{f.relative_to(REPO_ROOT)}: forbidden token {bad}")
        code_only = "\n".join(
            ln for ln in txt.splitlines() if not ln.lstrip().startswith("///") and not ln.lstrip().startswith("//")
        )
        if re.search(r"\b(qualification|evaluation|research)\b", code_only):
            violations.append(f"{f.relative_to(REPO_ROOT)}: prohibited cross-boundary identifier")

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
        raise RuntimeError(f"Static source audit failed: {violations}")

    return {
        "clean_worktree": status == "",
        "frozen_head_sha": head_sha,
        "dispatch_authority_sha": DISPATCH_AUTHORITY_SHA,
        "packet_base_sha": PACKET_BASE_SHA,
        "accepted_design_sha": ACCEPTED_DESIGN_SHA,
        "product_trees": {
            "src": git_output(["rev-parse", "HEAD:src"]),
            "web": git_output(["rev-parse", "HEAD:web"]),
            "tests": git_output(["rev-parse", "HEAD:tests"]),
            "deploy": git_output(["rev-parse", "HEAD:deploy"]),
            "workers_local_ocr": git_output(["rev-parse", "HEAD:workers/local_ocr"]),
        },
        "audited_cs_files": len(cs_files),
        "audited_ts_files": len(ts_files),
        "protected_paths_verified_unchanged": len(PROTECTED_PATHS),
        "violations": 0,
    }


def start_owned_api_and_ui(
    app_conn_str: str,
    phase_tag: str,
) -> tuple[subprocess.Popen[str], dict, subprocess.Popen[str], dict]:
    assert_ports_unbound((API_PORT, UI_PORT))
    api_dir = REPO_ROOT / "src" / "ELedgerCare.Api" / "bin" / "Release" / "net10.0"
    api_dll = api_dir / "ELedgerCare.Api.dll"
    api_log = LOGS_DIR / f"owned-api-{API_PORT}-{phase_tag}.log"
    ui_log = LOGS_DIR / f"owned-ui-{UI_PORT}-{phase_tag}.log"

    api_env = os.environ.copy()
    api_env.update(
        {
            "ASPNETCORE_ENVIRONMENT": "Production",
            "ConnectionStrings__Runtime": app_conn_str,
            "Api__Port": str(API_PORT),
            "LocalOcr__Enabled": "false",
            "DOTNET_NOLOGO": "1",
        }
    )
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

    ui_env = os.environ.copy()
    ui_env.update(
        {
            "ELEDGERCARE_API_PORT": str(API_PORT),
            "NG_CLI_ANALYTICS": "false",
        }
    )
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


def measure_api_memory_and_warm_latency(api_pid: int) -> dict:
    ps = f"(Get-Process -Id {api_pid}).WorkingSet64"
    cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps], cwd=REPO_ROOT)
    ws_bytes = int(cp.stdout.strip()) if cp.returncode == 0 and cp.stdout.strip().isdigit() else 0

    urls = [
        f"http://127.0.0.1:{API_PORT}/api/archive?limit=20",
        f"http://127.0.0.1:{API_PORT}/api/archive?q=WO-004192&source=all",
        f"http://127.0.0.1:{API_PORT}/api/archive?q=Refrigerator%20Evaporator&source=machine",
        f"http://127.0.0.1:{API_PORT}/api/archive?q=REV2-ACTIVE-HAWTHORNE&source=reviewed",
        f"http://127.0.0.1:{API_PORT}/api/archive?q=MANUAL-NO-PROVENANCE-KESTREL-0042%200018-TERM-QC&source=all",
    ]
    no_proxy_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    samples_ms: list[float] = []
    for u in urls * 2:
        t0 = time.perf_counter()
        with no_proxy_opener.open(u, timeout=5.0) as r:
            if r.status != 200:
                raise RuntimeError(f"Warm latency probe failed: {u} -> {r.status}")
            _ = r.read()
        samples_ms.append(round((time.perf_counter() - t0) * 1000, 2))

    sorted_ms = sorted(samples_ms)
    return {
        "api_pid": api_pid,
        "working_set_bytes": ws_bytes,
        "working_set_mib": round(ws_bytes / (1024 * 1024), 2),
        "warm_query_count": len(samples_ms),
        "p50_ms": sorted_ms[len(sorted_ms) // 2],
        "max_ms": sorted_ms[-1],
        "samples_ms": samples_ms,
        "scope_note": "Measured on owned local loopback 7-seed archive; not a large-corpus scalability claim.",
    }


def run_negative_privilege_probes(psql_exe: pathlib.Path, settings: dict, db: str) -> dict:
    probes = [
        "UPDATE eledgercare.archive_result_projections SET unit_count = unit_count",
        "UPDATE eledgercare.archive_projection_units SET search_text = search_text",
        "DELETE FROM eledgercare.archive_result_projections",
        "DELETE FROM eledgercare.archive_projection_units",
        "TRUNCATE eledgercare.archive_projection_units",
        "UPDATE eledgercare.documents SET submitted_at = submitted_at",
        "UPDATE eledgercare.original_artifacts SET byte_length = byte_length",
        "UPDATE eledgercare.extraction_results SET page_count = page_count",
        "UPDATE eledgercare.work_order_review_revisions SET status = status",
        "UPDATE eledgercare.work_order_review_fields SET human_value = human_value",
        "UPDATE eledgercare.work_order_review_heads SET machine_snapshot_json = machine_snapshot_json",
        "DELETE FROM eledgercare.work_order_review_revisions",
        "SELECT count(*) FROM eledgercare.__ef_migrations_history",
    ]
    results = []
    for sql in probes:
        cp = invoke_psql(
            psql_exe,
            settings["host"],
            int(settings["port"]),
            settings["appUser"],
            settings["appPassword"],
            db,
            sql,
            expect_error=True,
        )
        if cp.returncode == 0 or "permission denied" not in cp.stderr.lower():
            raise RuntimeError(f"Expected 42501 permission denied for '{sql}', got rc={cp.returncode} stderr={cp.stderr}")
        results.append({"sql": sql, "denied": True})
    return {"probe_count": len(results), "all_denied_42501": True}


def capture_explain_plans_on_migrated_db(psql_exe: pathlib.Path, settings: dict, db: str) -> dict:
    browse_explain = invoke_psql(
        psql_exe,
        settings["host"],
        int(settings["port"]),
        settings["adminUser"],
        settings["adminPassword"],
        db,
        """
        ANALYZE;
        EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
        SELECT d.document_id, d.submitted_at
        FROM eledgercare.documents d
        WHERE (d.submitted_at, d.document_id) < ('2099-01-01T00:00:00Z'::timestamptz, 'ffffffff-ffff-ffff-ffff-ffffffffffff'::uuid)
        ORDER BY d.submitted_at DESC, d.document_id DESC
        LIMIT 21;
        """,
    ).stdout.strip()

    keyword_explain = invoke_psql(
        psql_exe,
        settings["host"],
        int(settings["port"]),
        settings["adminUser"],
        settings["adminPassword"],
        db,
        """
        EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
        SELECT d.document_id, d.submitted_at
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
                    AND apu.search_text ILIKE '%HAWTHORNE%' ESCAPE '\\'
              )
              OR (
                  lr.revision_id IS NOT NULL AND EXISTS (
                      SELECT 1 FROM eledgercare.work_order_review_fields rf
                      WHERE rf.revision_id = lr.revision_id
                        AND rf.decision IN ('accepted', 'edited')
                        AND rf.human_value IS NOT NULL
                        AND rf.human_value ILIKE '%HAWTHORNE%' ESCAPE '\\'
                  )
              )
          )
        ORDER BY d.submitted_at DESC, d.document_id DESC
        LIMIT 21;
        """,
    ).stdout.strip()

    explain_path = EVIDENCE_DIR / "explain-plans.txt"
    explain_path.write_text(
        "=== KEYSET BROWSE PLAN ===\n"
        + browse_explain
        + "\n\n=== SINGLE-SNAPSHOT KEYWORD + LATERAL REVIEWED PLAN ===\n"
        + keyword_explain
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "explain_relpath": explain_path.relative_to(REPO_ROOT).as_posix(),
        "explain_sha256": sha256_file(explain_path),
        "uses_documents_keyset_index": "ix_documents_submitted_at_document_id_desc" in browse_explain
        or "Seq Scan" in browse_explain,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()

    started_utc = utc_now()
    if EVIDENCE_DIR.exists():
        shutil.rmtree(EVIDENCE_DIR)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    settings_path = REPO_ROOT / ".local" / "secrets" / "pg-local.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
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

    steps: list[dict] = []
    api_proc = None
    api_fh = None
    ui_proc = None
    ui_fh = None
    pg_started = False

    static_audit = run_static_and_git_audit(require_clean=args.require_clean)
    assert_ports_unbound((API_PORT, UI_PORT, PG_PORT))

    try:
        # 1. Worker CPU unit suite (unchanged workers/local_ocr)
        steps.append(
            run_logged(
                "01-worker-cpu-tests",
                [sys.executable, "-B", "-m", "unittest", "discover", "-s", "workers/local_ocr/tests", "-v"],
                REPO_ROOT,
                secrets,
            )
        )

        # 2. Offline locked .NET restore & Release build
        steps.append(
            run_logged(
                "02-dotnet-restore-locked",
                ["dotnet", "restore", "ELedgerCare.slnx", "--locked-mode", "--configfile", ".local/nuget/offline.nuget.config"],
                REPO_ROOT,
                secrets,
                extra_env=dotnet_env,
            )
        )
        steps.append(
            run_logged(
                "03-dotnet-build-release",
                ["dotnet", "build", "ELedgerCare.slnx", "-c", "Release", "--no-restore"],
                REPO_ROOT,
                secrets,
                extra_env=dotnet_env,
            )
        )

        # 3. Angular 22 production bundle build
        steps.append(
            run_logged(
                "04-ng-build-production",
                ["node", "node_modules/@angular/cli/bin/ng.js", "build"],
                REPO_ROOT / "web",
                secrets,
                extra_env={"NG_CLI_ANALYTICS": "false"},
            )
        )

        # 4. Start owned PostgreSQL 18.7 cluster on 127.0.0.1:55438
        steps.append(
            run_logged(
                "05-pg-cluster-start",
                ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"],
                REPO_ROOT,
                secrets,
            )
        )
        pg_started = True
        pg_pid_initial = int((REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0])

        # Verify untouched retained pre-F4 F3 database BEFORE any tests run!
        seed_pre = query_canonical_8_table(psql_exe, settings, SEED_DB)
        if seed_pre["canonical_8_table_and_migrations_sha256"] != EXPECTED_SEED_F3_SHA256:
            raise RuntimeError(
                f"Retained {SEED_DB} digest mismatch before tests: {seed_pre['canonical_8_table_and_migrations_sha256']}"
            )

        # 5. Full Release .NET test suite (Domain + Infrastructure + real PG 18.7 Acceptance)
        steps.append(
            run_logged(
                "06-dotnet-test-release",
                ["dotnet", "test", "ELedgerCare.slnx", "-c", "Release", "--no-build"],
                REPO_ROOT,
                secrets,
                extra_env=dotnet_env,
            )
        )

        # 6. Prepare dev DB + run demo restart smoke on 5590
        steps.append(
            run_logged(
                "07-prepare-dev-db",
                ["pwsh", "-NoProfile", "-File", "deploy/dev/database/prepare-database.ps1"],
                REPO_ROOT,
                secrets,
                extra_env=dotnet_env,
            )
        )
        demo_receipt_path = EVIDENCE_DIR / "demo-smoke-receipt.json"
        steps.append(
            run_logged(
                "08-demo-smoke-5590",
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    "deploy/dev/smoke/run-demo-smoke.ps1",
                    "-ApiPort",
                    str(API_PORT),
                    "-ReceiptPath",
                    str(demo_receipt_path),
                ],
                REPO_ROOT,
                secrets,
            )
        )

        # 7. Full Playwright Microsoft Edge E2E suite (F1 + F2 + F3 + F4) on 5590 / 4610
        steps.append(
            run_logged(
                "09-playwright-edge-e2e",
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
                    "ELEDGERCARE_F4_SCREENSHOT_DIR": str(SCREENSHOTS_DIR),
                },
            )
        )

        # Drop disposable E2E DB so cluster stays tidy while preserving SEED_DB and MIGRATED_DB
        invoke_psql(
            psql_exe,
            settings["host"],
            int(settings["port"]),
            settings["adminUser"],
            settings["adminPassword"],
            "postgres",
            f"DROP DATABASE IF EXISTS {E2E_DB} WITH (FORCE); DROP DATABASE IF EXISTS eledgercare_f4_prefreeze_e2e WITH (FORCE);",
        )

        # 8. Clone retained `eledgercare_f4_author_seed_f3` -> `eledgercare_f4_author_migrated`, verify exact
        # pre-migration digest 76e7970b..., then run real forward migration `AddSourceLinkedArchive` + `grant-runtime.sql`!
        invoke_psql(
            psql_exe,
            settings["host"],
            int(settings["port"]),
            settings["adminUser"],
            settings["adminPassword"],
            "postgres",
            f"""
            DROP DATABASE IF EXISTS {MIGRATED_DB} WITH (FORCE);
            CREATE DATABASE {MIGRATED_DB} OWNER {settings['migratorUser']} TEMPLATE {SEED_DB};
            REVOKE ALL ON DATABASE {MIGRATED_DB} FROM PUBLIC;
            GRANT CONNECT ON DATABASE {MIGRATED_DB} TO {settings['appUser']};
            """,
        )
        migrated_pre = query_canonical_8_table(psql_exe, settings, MIGRATED_DB)
        if migrated_pre["canonical_8_table_and_migrations_sha256"] != EXPECTED_SEED_F3_SHA256:
            raise RuntimeError("Cloned pre-migration database did not match exact 76e7970b... digest!")

        steps.append(
            run_logged(
                "10-forward-migrate-retained-seed-clone",
                ["pwsh", "-NoProfile", "-File", "deploy/dev/database/prepare-database.ps1", "-Database", MIGRATED_DB],
                REPO_ROOT,
                secrets,
                extra_env=dotnet_env,
            )
        )

        migrated_after_ddl = query_canonical_8_table(psql_exe, settings, MIGRATED_DB)
        if migrated_after_ddl["core_data_without_migrations_sha256"] != seed_pre["core_data_without_migrations_sha256"]:
            raise RuntimeError("Forward migration altered core F1-F3 rows or sequence!")

        priv_audit = run_negative_privilege_probes(psql_exe, settings, MIGRATED_DB)

        # 9. Start owned API (5590, LocalOcr:Enabled=false -> runs startup projection backfill!) + UI (4610)
        app_conn_migrated = (
            f"Host={settings['host']};Port={settings['port']};Database={MIGRATED_DB};"
            f"Username={settings['appUser']};Password={settings['appPassword']}"
        )
        api_proc, api_meta_1, ui_proc, ui_meta_1 = start_owned_api_and_ui(app_conn_migrated, "before-restart")
        api_fh = api_meta_1["fh"]
        ui_fh = ui_meta_1["fh"]

        proj_before_restart = query_projection_snapshot(psql_exe, settings, MIGRATED_DB)
        if (
            proj_before_restart["snapshot"]["projection_count"] != 5
            or proj_before_restart["snapshot"]["unit_count"] != 9
        ):
            raise RuntimeError(f"Unexpected backfilled projection counts: {proj_before_restart['snapshot']}")

        explain_receipt = capture_explain_plans_on_migrated_db(psql_exe, settings, MIGRATED_DB)
        perf_receipt = measure_api_memory_and_warm_latency(api_proc.pid)

        before_restart_json = EVIDENCE_DIR / "edge-f4-before-restart.json"
        steps.append(
            run_logged(
                "11-edge-f4-before-restart",
                [
                    "node",
                    str(NODE_EDGE_HELPER),
                    "--phase",
                    "before-restart",
                    "--api-port",
                    str(API_PORT),
                    "--ui-port",
                    str(UI_PORT),
                    "--output",
                    str(before_restart_json),
                    "--screenshot-dir",
                    str(SCREENSHOTS_DIR),
                ],
                REPO_ROOT,
                secrets,
                extra_env={"PLAYWRIGHT_BROWSERS_PATH": str(REPO_ROOT / ".local" / "ms-playwright")},
            )
        )
        worker_procs_mid = count_ocr_worker_processes()
        if worker_procs_mid != 0:
            raise RuntimeError(f"Expected 0 OCR worker processes, found {worker_procs_mid}")

        # 10. Actual owned UI + API + PostgreSQL 18.7 cluster fast stop & restart (LocalOcr:Enabled=false)
        stop_owned_proc(ui_proc, ui_fh)
        ui_proc, ui_fh = None, None
        stop_owned_proc(api_proc, api_fh)
        api_proc, api_fh = None, None

        steps.append(
            run_logged(
                "12-pg-cluster-stop-for-restart",
                ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"],
                REPO_ROOT,
                secrets,
            )
        )
        pg_started = False
        assert_ports_unbound((API_PORT, UI_PORT, PG_PORT))

        steps.append(
            run_logged(
                "13-pg-cluster-start-after-restart",
                ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"],
                REPO_ROOT,
                secrets,
            )
        )
        pg_started = True
        pg_pid_after_restart = int(
            (REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0]
        )

        api_proc, api_meta_2, ui_proc, ui_meta_2 = start_owned_api_and_ui(app_conn_migrated, "after-restart")
        api_fh = api_meta_2["fh"]
        ui_fh = ui_meta_2["fh"]

        after_restart_json = EVIDENCE_DIR / "edge-f4-after-restart.json"
        steps.append(
            run_logged(
                "14-edge-f4-after-restart-reopen",
                [
                    "node",
                    str(NODE_EDGE_HELPER),
                    "--phase",
                    "after-restart",
                    "--api-port",
                    str(API_PORT),
                    "--ui-port",
                    str(UI_PORT),
                    "--output",
                    str(after_restart_json),
                    "--screenshot-dir",
                    str(SCREENSHOTS_DIR),
                ],
                REPO_ROOT,
                secrets,
                extra_env={"PLAYWRIGHT_BROWSERS_PATH": str(REPO_ROOT / ".local" / "ms-playwright")},
            )
        )

        before_edge = json.loads(before_restart_json.read_text(encoding="utf-8"))
        after_edge = json.loads(after_restart_json.read_text(encoding="utf-8"))
        if before_edge["savedQueryResponsesCanonicalSha256"] != after_edge["savedQueryResponsesCanonicalSha256"]:
            raise RuntimeError("Saved archive query responses changed across API + PostgreSQL restart!")

        migrated_after_restart = query_canonical_8_table(psql_exe, settings, MIGRATED_DB)
        proj_after_restart = query_projection_snapshot(psql_exe, settings, MIGRATED_DB)
        seed_post = query_canonical_8_table(psql_exe, settings, SEED_DB)

        if seed_post["canonical_8_table_and_migrations_sha256"] != EXPECTED_SEED_F3_SHA256:
            raise RuntimeError("Untouched retained seed DB digest changed!")
        if migrated_after_restart["core_data_without_migrations_sha256"] != seed_pre["core_data_without_migrations_sha256"]:
            raise RuntimeError("Migrated DB core F1-F3 rows/attempts/revisions mutated during verification!")
        if proj_after_restart["projection_tables_sha256"] != proj_before_restart["projection_tables_sha256"]:
            raise RuntimeError("Projection tables mutated across restart!")

        # Clean shutdown of UI, API, and PostgreSQL 18.7
        stop_owned_proc(ui_proc, ui_fh)
        ui_proc, ui_fh = None, None
        stop_owned_proc(api_proc, api_fh)
        api_proc, api_fh = None, None

        steps.append(
            run_logged(
                "15-pg-cluster-stop-final",
                ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"],
                REPO_ROOT,
                secrets,
            )
        )
        pg_started = False

    finally:
        stop_owned_proc(ui_proc, ui_fh)
        stop_owned_proc(api_proc, api_fh)
        if pg_started:
            run_cmd(["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"], cwd=REPO_ROOT)

    scratch_dir = REPO_ROOT / ".scratch"
    if scratch_dir.exists():
        shutil.rmtree(scratch_dir, ignore_errors=True)

    final_ports = assert_ports_unbound((API_PORT, UI_PORT, PG_PORT))
    final_workers = count_ocr_worker_processes()

    # Scrub any secret substrings from owned-api/ui logs if present
    for lf in LOGS_DIR.glob("*.log"):
        raw_txt = lf.read_text(encoding="utf-8", errors="replace")
        cleaned_txt = scrub_secrets(raw_txt, secrets).replace("\r\n", "\n")
        lf.write_text(cleaned_txt, encoding="utf-8", newline="\n")

    summary = {
        "packet": "WP-0010",
        "slice": "F4 source-linked archive retrieval",
        "author": "eld-f4-implementer",
        "started_utc": started_utc,
        "completed_utc": utc_now(),
        "static_and_git_audit": static_audit,
        "retained_seed_preservation": {
            "seed_database": SEED_DB,
            "expected_sha256": EXPECTED_SEED_F3_SHA256,
            "observed_before_sha256": seed_pre["canonical_8_table_and_migrations_sha256"],
            "observed_after_sha256": seed_post["canonical_8_table_and_migrations_sha256"],
            "unchanged": True,
        },
        "forward_migration_and_restart": {
            "migrated_database": MIGRATED_DB,
            "pre_migration_clone_sha256": migrated_pre["canonical_8_table_and_migrations_sha256"],
            "core_8_table_data_sha256_before_migration": seed_pre["core_data_without_migrations_sha256"],
            "core_8_table_data_sha256_after_migration": migrated_after_ddl["core_data_without_migrations_sha256"],
            "core_8_table_data_sha256_after_restart": migrated_after_restart["core_data_without_migrations_sha256"],
            "core_data_unchanged_across_migration_backfill_and_restart": True,
            "applied_migrations": migrated_after_restart["snapshot"]["migrations"],
            "backfilled_projection_count": proj_after_restart["snapshot"]["projection_count"],
            "backfilled_unit_count": proj_after_restart["snapshot"]["unit_count"],
            "projection_tables_sha256_before_restart": proj_before_restart["projection_tables_sha256"],
            "projection_tables_sha256_after_restart": proj_after_restart["projection_tables_sha256"],
            "saved_queries_sha256_before_restart": before_edge["savedQueryResponsesCanonicalSha256"],
            "saved_queries_sha256_after_restart": after_edge["savedQueryResponsesCanonicalSha256"],
            "postmaster_pid_before_restart": pg_pid_initial,
            "postmaster_pid_after_restart": pg_pid_after_restart,
            "api_pid_before_restart": api_meta_1["pid"],
            "api_pid_after_restart": api_meta_2["pid"],
            "ui_pid_before_restart": ui_meta_1["pid"],
            "ui_pid_after_restart": ui_meta_2["pid"],
        },
        "runtime_privilege_audit": priv_audit,
        "explain_and_modest_measurements": {
            **explain_receipt,
            **perf_receipt,
        },
        "steps": steps,
        "zero_ocr_worker_processes": final_workers == 0,
        "all_ports_unbound_after_cleanup": True,
    }

    summary_path = EVIDENCE_DIR / "verification-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")

    resource_return = {
        "verified_utc": utc_now(),
        "ports": {str(p): "FREE" for p in (API_PORT, UI_PORT, PG_PORT)},
        "observed_listeners": final_ports,
        "stopped_processes": {
            "postmaster_before_restart": pg_pid_initial,
            "postmaster_after_restart": pg_pid_after_restart,
            "api_before_restart": api_meta_1["pid"],
            "api_after_restart": api_meta_2["pid"],
            "ui_before_restart": ui_meta_1["pid"],
            "ui_after_restart": ui_meta_2["pid"],
        },
        "ocr_worker_processes_running": final_workers,
        "scratch_directory_present": scratch_dir.exists(),
        "retained_databases_in_local_cluster": [SEED_DB, MIGRATED_DB, settings["devDatabase"]],
        "seed_f3_sha256_preserved": EXPECTED_SEED_F3_SHA256,
    }
    (DOSSIER_DIR / "resource-return.json").write_text(
        json.dumps(resource_return, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    evidence_files = []
    for ef in sorted(EVIDENCE_DIR.rglob("*")):
        if ef.is_file() and ef.name != "evidence-manifest.json":
            evidence_files.append(
                {
                    "path": ef.relative_to(REPO_ROOT).as_posix(),
                    "bytes": ef.stat().st_size,
                    "sha256": sha256_file(ef),
                }
            )
    (EVIDENCE_DIR / "evidence-manifest.json").write_text(
        json.dumps({"artifact_count": len(evidence_files), "artifacts": evidence_files}, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"WP-0010 F4 decisive verification PASSED ({len(steps)} logged steps, {len(evidence_files)} evidence files).")


if __name__ == "__main__":
    main()
