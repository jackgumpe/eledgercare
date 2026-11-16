import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[6]
if not (REPO_ROOT / "ELedgerCare.slnx").is_file():
    raise RuntimeError(f"Resolved REPO_ROOT missing ELedgerCare.slnx: {REPO_ROOT}")

RECON_DIR = REPO_ROOT / "docs" / "reviews" / "WP-0008" / "eld-f3-reviewer" / "presentation-reconciliation"
EVIDENCE_DIR = RECON_DIR / "evidence"
LOGS_DIR = EVIDENCE_DIR / "logs"
SCREENSHOTS_DIR = EVIDENCE_DIR / "screenshots"

API_PORT = 5490
UI_PORT = 4510
PG_PORT = 55437
SEED_DB = "eledgercare_f3_reviewer_seed_f2"
P007_E2E_DB = "eledgercare_f3_rev_p007_e2e"

ORIGINAL_F3_CANDIDATE_SHA = "62e8666af747c0040942cee20c0ed34f4d747e93"
ORIGINAL_AUTHOR_003_SHA = "b77bc68a5b6878d2395cd76b0d0a858ae15cc249"
PRIOR_DESIGN_002_SHA = "bff139bcdf55df77a821b858513b7e6bf5d96b87"
PREPARATION_PUB_SHA = "9d99c3f42dda42ab691583f5b0c221b7be0bf5b6"
PRIOR_ACCEPTANCE_004_SHA = "99bc14b29dd433d7328c0b9c43dc0a6ea0c79f28"
ROOT_AUTHORITY_007_SHA = "1f9be230b648a0bf1d2d9d44e7a97b12d9d3b1fb"
AUTHOR_INITIAL_P006_SHA = "bc82102bc5a59663942c717d31acbc02d32be2a2"
AUTHOR_FINAL_P006_CANDIDATE_SHA = "dda4b4d5856ac45105c31ba1d6d6813debdab8a7"
AUTHOR_FINAL_P006_EVIDENCE_SHA = "8ac598062925ea114e251c447df0464ec88ecf89"
AUTHOR_FINAL_P006_REPORT_SHA = "ac997eed58f2f10d79dfeb7b4e23819ee347c49a"
EXPECTED_WEB_TREE_OID = "381d5e754ea7d7e8612c4c19d07f7d7aafb6ffdd"

EXPECTED_POST_MIGRATION_SEED_CORE_SHA256 = "734cc7eee1f8477dc41676382157039a405bb7b20faec2c24841a9409aab4a2f"
EXPECTED_F1_F2_ROWS_AND_SEQ_SHA256 = "b903028ae3ad1c163aa614455b606a845639ebba1060d1e79571cf2afbce8305"
EXPECTED_PACKAGE_LOCK_SHA256 = "93cc7b29d66ebfbe00437c886e57118bf455052def3e8acff08e7cb382ad0f53"
EXPECTED_AUTHOR_003_BLOB = "4582c30e48f9490fda57f468fcd4958e29c55a95"
EXPECTED_AUTHOR_RETAINED_LOG_SHA256 = "8c75e17102a16c83c64e82ebba52a7b112fe87fac7c73c740d6a7a1849cff4c0"

SEED1_DOC_ID = "01a1e571-2838-714b-861b-bf0835d7c90a"
SEED1_REV4_ID = "01a1e670-c6bf-7f1b-97ff-9d72031ceb16"
SEED3_DOC_ID = "01a1e578-8f3a-7e0c-826b-a2c9dc066a8f"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_out(*args: str) -> str:
    cp = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    return cp.stdout.strip()


def git_bytes(*args: str) -> bytes:
    cp = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, check=True)
    return cp.stdout


def load_pg_settings() -> dict:
    s = json.loads((REPO_ROOT / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
    if int(s["port"]) != PG_PORT:
        raise RuntimeError(f"Expected reviewer PostgreSQL port {PG_PORT}, got {s['port']}")
    return s


def scrub_secrets(text: str, settings: dict) -> str:
    out = text
    for key in ("adminPassword", "migratorPassword", "appPassword"):
        val = str(settings.get(key, ""))
        if val:
            out = out.replace(val, "<REDACTED_SECRET>")
    return out


def run_logged(step_id: str, cmd: list[str], cwd: Path, settings: dict, extra_env: dict[str, str] | None = None) -> dict:
    env = os.environ.copy()
    env["NUGET_PACKAGES"] = str((REPO_ROOT / ".local" / "nuget" / "packages").resolve())
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"
    env["NG_CLI_ANALYTICS"] = "false"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra_env:
        env.update(extra_env)

    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)

    safe_cmd_str = scrub_secrets(" ".join(cmd), settings)
    safe_stdout = scrub_secrets(proc.stdout, settings)
    safe_stderr = scrub_secrets(proc.stderr, settings)

    log_path = LOGS_DIR / f"{step_id}.log"
    log_content = (
        f"$ {safe_cmd_str}\n"
        f"[cwd={cwd}]\n"
        f"[exit={proc.returncode}, elapsed_ms={elapsed_ms}]\n"
        f"--- STDOUT ---\n{safe_stdout}\n"
        f"--- STDERR ---\n{safe_stderr}\n"
    )
    log_path.write_text(log_content, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"Step {step_id} failed with exit code {proc.returncode}. See {log_path}")

    return {
        "step": step_id,
        "command": safe_cmd_str,
        "exit_code": proc.returncode,
        "elapsed_ms": elapsed_ms,
        "log_file": str(log_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "log_bytes": log_path.stat().st_size,
        "log_sha256": sha256_file(log_path),
    }


def is_port_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.35)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def wait_port_free(port: int, timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if not is_port_listening(port):
            return
        time.sleep(0.25)
    raise RuntimeError(f"Port {port} remained bound after {timeout_s}s; refusing to touch non-owned or stuck listener.")


def query_port_listeners(ports: list[int]) -> dict[str, list[int]]:
    port_list = ",".join(str(p) for p in ports)
    ps = (
        f"$res = @{{}}; foreach ($p in @({port_list})) {{ "
        f"$c = @(Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); "
        f"$res[[string]$p] = $c }}; $res | ConvertTo-Json -Compress"
    )
    cp = subprocess.run(["pwsh", "-NoProfile", "-Command", ps], capture_output=True, text=True, check=True)
    raw = json.loads(cp.stdout.strip())
    return {k: ([v] if isinstance(v, int) else list(v or [])) for k, v in raw.items()}


def get_process_identity(pid: int) -> dict | None:
    ps = (
        f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
        f"if ($null -eq $p) {{ 'null' }} else {{ "
        f"[ordered]@{{ pid = $p.Id; name = $p.ProcessName; path = $p.Path; startUtc = $p.StartTime.ToUniversalTime().ToString('o') }} | ConvertTo-Json -Compress }}"
    )
    cp = subprocess.run(["pwsh", "-NoProfile", "-Command", ps], capture_output=True, text=True, check=True)
    txt = cp.stdout.strip()
    return None if txt == "null" or not txt else json.loads(txt)


def check_owned_local_ocr_workers() -> list[dict]:
    owned_worker_dir = str((REPO_ROOT / "workers" / "local_ocr").resolve()).lower()
    owned_worker_dir_slash = owned_worker_dir.replace("\\", "/")
    ps = (
        "$selfPid = $PID; "
        "Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $selfPid -and $null -ne $_.CommandLine } | "
        "Select-Object ProcessId, Name, CommandLine | ConvertTo-Json -Compress"
    )
    cp = subprocess.run(["pwsh", "-NoProfile", "-Command", ps], capture_output=True, text=True, check=True)
    txt = cp.stdout.strip()
    if not txt:
        return []
    items = json.loads(txt)
    if isinstance(items, dict):
        items = [items]
    matches = []
    for item in items:
        cmd_lower = str(item.get("CommandLine") or "").lower()
        if owned_worker_dir in cmd_lower or owned_worker_dir_slash in cmd_lower:
            matches.append({"pid": item["ProcessId"], "name": item["Name"]})
    return matches


def invoke_psql(user: str, password: str, db: str, sql: str) -> subprocess.CompletedProcess[str]:
    s = load_pg_settings()
    psql = REPO_ROOT / ".local" / "tools" / "pgsql-18.7-1" / "bin" / "psql.exe"
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    cp = subprocess.run(
        [
            str(psql),
            "-X",
            "-q",
            "-A",
            "-t",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            str(s["host"]),
            "-p",
            str(s["port"]),
            "-U",
            user,
            "-d",
            db,
            "-f",
            "-",
        ],
        input=sql,
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=env,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"psql failed on {db} as {user}: {cp.stderr.strip()}")
    return cp


def query_seed_db_complete_snapshot(db: str) -> dict:
    """
    Captures both the exact F1/F2 core digest from /004 AND a complete 8-table canonical
    SHA-256 over all F1/F2/F3 rows so we prove zero database mutation in eledgercare_f3_reviewer_seed_f2!
    """
    s = load_pg_settings()
    core_sql = """
SELECT json_build_object(
  'migrations', COALESCE((SELECT json_agg("MigrationId" ORDER BY "MigrationId") FROM eledgercare.__ef_migrations_history), '[]'::json),
  'sequence', (SELECT json_build_object('last_value', last_value, 'is_called', is_called) FROM eledgercare.extraction_fencing_seq),
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
    ) ORDER BY d.submitted_at, d.document_id)
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
      'exit_code', at.exit_code
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
  ), '[]'::json)
)::text;
"""
    core_parsed = json.loads(invoke_psql(str(s["adminUser"]), str(s["adminPassword"]), db, core_sql).stdout.strip())
    core_sha = sha256_bytes(json.dumps(core_parsed, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    f2_data_only = {
        "sequence": core_parsed["sequence"],
        "documents": core_parsed["documents"],
        "attempts": core_parsed["attempts"],
        "results": core_parsed["results"],
    }
    f2_rows_sha = sha256_bytes(json.dumps(f2_data_only, sort_keys=True, separators=(",", ":")).encode("utf-8"))

    f3_sql = """
SELECT json_build_object(
  'heads', COALESCE((
    SELECT json_agg(row_to_json(h) ORDER BY h.document_id, h.profile_id)
    FROM (
      SELECT document_id::text, result_id::text,
             encode(input_sha256, 'hex') AS input_sha256,
             encode(raw_output_sha256, 'hex') AS raw_output_sha256,
             profile_id, field_schema_version, suggestion_policy_version,
             machine_snapshot_json, current_revision_number,
             current_revision_id::text, current_status, created_at, updated_at
      FROM eledgercare.work_order_review_heads
    ) h
  ), '[]'::json),
  'revisions', COALESCE((
    SELECT json_agg(row_to_json(rv) ORDER BY rv.document_id, rv.revision_number)
    FROM (
      SELECT revision_id::text, document_id::text, result_id::text,
             revision_number, previous_revision_number,
             status, idempotency_key::text,
             encode(request_sha256, 'hex') AS request_sha256,
             encode(input_sha256, 'hex') AS input_sha256,
             encode(raw_output_sha256, 'hex') AS raw_output_sha256,
             profile_id, field_schema_version, suggestion_policy_version,
             operator_display_label,
             accepted_field_count, edited_field_count, unknown_field_count, unreviewed_field_count,
             saved_at
      FROM eledgercare.work_order_review_revisions
    ) rv
  ), '[]'::json),
  'fields', COALESCE((
    SELECT json_agg(row_to_json(fd) ORDER BY fd.revision_id, fd.field_ordinal)
    FROM (
      SELECT revision_id::text, field_ordinal, field_key, decision,
             human_value, unknown_reason,
             consulted_page_number, consulted_block_ordinal,
             consulted_table_row, consulted_table_column, consulted_quote
      FROM eledgercare.work_order_review_fields
    ) fd
  ), '[]'::json)
)::text;
"""
    f3_parsed = json.loads(invoke_psql(str(s["adminUser"]), str(s["adminPassword"]), db, f3_sql).stdout.strip())
    combined = {"f1_f2_core": core_parsed, "f3_review": f3_parsed}
    full_sha = sha256_bytes(json.dumps(combined, sort_keys=True, separators=(",", ":")).encode("utf-8"))

    heads_by_doc = {h["document_id"]: h for h in f3_parsed["heads"]}
    return {
        "core_state_sha256": core_sha,
        "f1_f2_rows_and_seq_sha256": f2_rows_sha,
        "full_8_table_sha256": full_sha,
        "counts": {
            "documents": len(core_parsed["documents"]),
            "attempts": len(core_parsed["attempts"]),
            "results": len(core_parsed["results"]),
            "heads": len(f3_parsed["heads"]),
            "revisions": len(f3_parsed["revisions"]),
            "fields": len(f3_parsed["fields"]),
        },
        "seed1_head": heads_by_doc.get(SEED1_DOC_ID),
        "seed3_head": heads_by_doc.get(SEED3_DOC_ID),
    }


def wait_http_ready(url: str, timeout_s: float = 90.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                if resp.status < 500:
                    return
        except urllib.error.HTTPError as e:
            if e.code < 500:
                return
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError(f"Service did not become ready at {url} within {timeout_s}s")


def start_owned_api(db_name: str, label: str) -> tuple[subprocess.Popen, object, dict]:
    wait_port_free(API_PORT, timeout_s=15.0)
    s = load_pg_settings()
    api_dir = REPO_ROOT / "src" / "ELedgerCare.Api" / "bin" / "Release" / "net10.0"
    api_dll = api_dir / "ELedgerCare.Api.dll"
    if not api_dll.is_file():
        raise RuntimeError(f"Expected prebuilt Release API binary at {api_dll}")
    conn = f"Host={s['host']};Port={s['port']};Database={db_name};Username={s['appUser']};Password={s['appPassword']}"
    env = os.environ.copy()
    env["ASPNETCORE_ENVIRONMENT"] = "Production"
    env["ConnectionStrings__Runtime"] = conn
    env["Api__Port"] = str(API_PORT)
    env["LocalOcr__Enabled"] = "false"
    env["DOTNET_NOLOGO"] = "1"
    log_f = open(LOGS_DIR / f"reviewer-api-{label}.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        ["dotnet", str(api_dll)],
        cwd=str(api_dir),
        env=env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )
    wait_http_ready(f"http://127.0.0.1:{API_PORT}/api/documents/00000000-0000-0000-0000-000000000000", timeout_s=60.0)
    ident = get_process_identity(proc.pid)
    if not ident:
        raise RuntimeError("Could not capture owned API process identity.")
    return proc, log_f, ident


def start_owned_ui(label: str) -> tuple[subprocess.Popen, object, dict]:
    wait_port_free(UI_PORT, timeout_s=15.0)
    web_dir = REPO_ROOT / "web"
    ng_cli = web_dir / "node_modules" / "@angular" / "cli" / "bin" / "ng.js"
    env = os.environ.copy()
    env["ELEDGERCARE_API_PORT"] = str(API_PORT)
    env["NG_CLI_ANALYTICS"] = "false"
    log_f = open(LOGS_DIR / f"reviewer-ui-{label}.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        ["node", str(ng_cli), "serve", "--host", "127.0.0.1", "--port", str(UI_PORT), "--proxy-config", "proxy.conf.mjs"],
        cwd=str(web_dir),
        env=env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )
    wait_http_ready(f"http://127.0.0.1:{UI_PORT}/", timeout_s=120.0)
    ident = get_process_identity(proc.pid)
    if not ident:
        raise RuntimeError("Could not capture owned UI process identity.")
    return proc, log_f, ident


def stop_owned_proc(proc: subprocess.Popen | None, log_f: object | None, recorded_ident: dict | None) -> dict | None:
    try:
        if proc is None:
            return None
        if proc.poll() is not None:
            return {"pid": proc.pid, "stopped": "already_exited", "exit_code": proc.returncode}
        current_ident = get_process_identity(proc.pid)
        if recorded_ident and current_ident and current_ident["startUtc"] != recorded_ident["startUtc"]:
            raise RuntimeError(
                f"PID {proc.pid} startUtc changed ({current_ident['startUtc']} vs {recorded_ident['startUtc']}); refusing to terminate recycled PID!"
            )
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
        return {
            "pid": proc.pid,
            "verified_start_utc": recorded_ident["startUtc"] if recorded_ident else None,
            "stopped_utc": utc_now(),
            "exit_code": proc.returncode,
        }
    finally:
        if log_f is not None:
            try:
                log_f.close()  # type: ignore[attr-defined]
            except Exception:
                pass


def run_static_and_author_audit(frozen_head_sha: str) -> dict:
    # 1. Verify web/ tree matches author's dda4b4d5 & bc82102b (381d5e754ea7d7e8612c4c19d07f7d7aafb6ffdd).
    head_web_oid = git_out("rev-parse", f"{frozen_head_sha}:web")
    cand_web_oid = git_out("rev-parse", f"{AUTHOR_FINAL_P006_CANDIDATE_SHA}:web")
    init_web_oid = git_out("rev-parse", f"{AUTHOR_INITIAL_P006_SHA}:web")
    if not (head_web_oid == cand_web_oid == init_web_oid == EXPECTED_WEB_TREE_OID):
        raise RuntimeError(f"web/ tree mismatch: HEAD={head_web_oid}, dda4b4d5={cand_web_oid}, bc82102b={init_web_oid}")

    # 2. Verify all non-web product/worker/deploy/test/dependency identities are 100% unchanged from accepted 62e8666a.
    unchanged_from_62e8666a_paths = [
        "src",
        "tests",
        "deploy",
        "ELedgerCare.slnx",
        "workers",
        "Directory.Build.props",
        "Directory.Packages.props",
        "web/package.json",
        "web/package-lock.json",
        "web/angular.json",
        "web/playwright.config.ts",
        "web/src/app/review/pdf-preview-url.ts",
        "web/src/app/review/review-api.ts",
        "web/src/app/review/review-models.ts",
        "web/src/app/intake/document-page.ts",
    ]
    unchanged_product_oids: dict[str, str] = {}
    for rel in unchanged_from_62e8666a_paths:
        head_oid = git_out("rev-parse", f"{frozen_head_sha}:{rel}")
        orig_oid = git_out("rev-parse", f"{ORIGINAL_F3_CANDIDATE_SHA}:{rel}")
        if head_oid != orig_oid:
            raise RuntimeError(f"Expected {rel} unchanged from {ORIGINAL_F3_CANDIDATE_SHA}: HEAD={head_oid} vs orig={orig_oid}")
        unchanged_product_oids[rel] = head_oid

    # 3. Verify exact product diff 62e8666a..dda4b4d5 is strictly the 3 expected web files.
    product_diff_files = sorted(
        ln.strip()
        for ln in git_out(
            "diff",
            "--name-only",
            f"{ORIGINAL_F3_CANDIDATE_SHA}..{AUTHOR_FINAL_P006_CANDIDATE_SHA}",
            "--",
            "src",
            "tests",
            "web",
            "deploy",
            "ELedgerCare.slnx",
            "workers",
        ).splitlines()
        if ln.strip()
    )
    expected_diff_files = [
        "web/e2e/review.spec.ts",
        "web/src/app/review/work-order-review-page.ts",
        "web/src/styles.css",
    ]
    if product_diff_files != expected_diff_files:
        raise RuntimeError(f"Unexpected product diff files: {product_diff_files}")

    # 4. Verify protected shared routing, R&D trees, and immutable prior reports/dossiers.
    protected_checks = {
        "AGENTS.md": git_out("rev-parse", f"{frozen_head_sha}:AGENTS.md") == git_out("rev-parse", f"{ROOT_AUTHORITY_007_SHA}:AGENTS.md"),
        "START_HERE.md": git_out("rev-parse", f"{frozen_head_sha}:START_HERE.md") == git_out("rev-parse", f"{ROOT_AUTHORITY_007_SHA}:START_HERE.md"),
        "CURRENT.md": git_out("rev-parse", f"{frozen_head_sha}:CURRENT.md") == git_out("rev-parse", f"{ROOT_AUTHORITY_007_SHA}:CURRENT.md"),
        "INDEX.md": git_out("rev-parse", f"{frozen_head_sha}:INDEX.md") == git_out("rev-parse", f"{ROOT_AUTHORITY_007_SHA}:INDEX.md"),
        "docs/design": git_out("rev-parse", f"{frozen_head_sha}:docs/design") == git_out("rev-parse", f"{ROOT_AUTHORITY_007_SHA}:docs/design"),
        "docs/coordination": git_out("rev-parse", f"{frozen_head_sha}:docs/coordination") == git_out("rev-parse", f"{ROOT_AUTHORITY_007_SHA}:docs/coordination"),
        "docs/kickoffs": git_out("rev-parse", f"{frozen_head_sha}:docs/kickoffs") == git_out("rev-parse", f"{ROOT_AUTHORITY_007_SHA}:docs/kickoffs"),
        "evaluation": git_out("rev-parse", f"{frozen_head_sha}:evaluation") == git_out("rev-parse", f"{ROOT_AUTHORITY_007_SHA}:evaluation"),
        "qualification": git_out("rev-parse", f"{frozen_head_sha}:qualification") == git_out("rev-parse", f"{ROOT_AUTHORITY_007_SHA}:qualification"),
        "research": git_out("rev-parse", f"{frozen_head_sha}:research") == git_out("rev-parse", f"{ROOT_AUTHORITY_007_SHA}:research"),
        "reviewer_design_dir": git_out("rev-parse", f"{frozen_head_sha}:docs/reviews/WP-0008/eld-f3-reviewer/design")
        == git_out("rev-parse", f"{PRIOR_DESIGN_002_SHA}:docs/reviews/WP-0008/eld-f3-reviewer/design"),
        "reviewer_preparation_dir": git_out("rev-parse", f"{frozen_head_sha}:docs/reviews/WP-0008/eld-f3-reviewer/preparation")
        == git_out("rev-parse", f"{PRIOR_ACCEPTANCE_004_SHA}:docs/reviews/WP-0008/eld-f3-reviewer/preparation"),
        "reviewer_acceptance_dir": git_out("rev-parse", f"{frozen_head_sha}:docs/reviews/WP-0008/eld-f3-reviewer/acceptance")
        == git_out("rev-parse", f"{PRIOR_ACCEPTANCE_004_SHA}:docs/reviews/WP-0008/eld-f3-reviewer/acceptance"),
        "report_002": git_out("rev-parse", f"{frozen_head_sha}:docs/agent-reports/eld-f3-reviewer/WP-0008/002_2026-11-16_review_eld-f3-reviewer.md")
        == git_out("rev-parse", f"{PRIOR_DESIGN_002_SHA}:docs/agent-reports/eld-f3-reviewer/WP-0008/002_2026-11-16_review_eld-f3-reviewer.md"),
        "report_003": git_out("rev-parse", f"{frozen_head_sha}:docs/agent-reports/eld-f3-implementer/WP-0008/003_2026-11-16_implementation_eld-f3-implementer.md")
        == EXPECTED_AUTHOR_003_BLOB,
        "report_004": git_out("rev-parse", f"{frozen_head_sha}:docs/agent-reports/eld-f3-reviewer/WP-0008/004_2026-11-16_review_eld-f3-reviewer.md")
        == git_out("rev-parse", f"{PRIOR_ACCEPTANCE_004_SHA}:docs/agent-reports/eld-f3-reviewer/WP-0008/004_2026-11-16_review_eld-f3-reviewer.md"),
        "report_006": git_out("rev-parse", f"{frozen_head_sha}:docs/agent-reports/eld-f3-implementer/WP-0008/006_2026-11-16_implementation_eld-f3-implementer.md")
        == git_out("rev-parse", f"{AUTHOR_FINAL_P006_REPORT_SHA}:docs/agent-reports/eld-f3-implementer/WP-0008/006_2026-11-16_implementation_eld-f3-implementer.md"),
    }
    if not all(protected_checks.values()):
        raise RuntimeError(f"Protected path verification failed: {protected_checks}")

    # 5. Verify Angular CLI factual version (22.2.7) and lockfile SHA-256.
    pkg_json = json.loads((REPO_ROOT / "web" / "package.json").read_text(encoding="utf-8"))
    installed_cli_json = json.loads((REPO_ROOT / "web" / "node_modules" / "@angular" / "cli" / "package.json").read_text(encoding="utf-8"))
    lock_blob = git_bytes("show", f"{frozen_head_sha}:web/package-lock.json")
    lock_sha = sha256_bytes(lock_blob)
    if pkg_json["devDependencies"]["@angular/cli"] != "22.2.7" or installed_cli_json["version"] != "22.2.7":
        raise RuntimeError("Unexpected Angular CLI version")
    if lock_sha != EXPECTED_PACKAGE_LOCK_SHA256:
        raise RuntimeError(f"web/package-lock.json SHA-256 mismatch: {lock_sha}")

    # 6. Verify product code boundary & security guards (zero R&D imports, zero innerHTML/bypassSecurityTrustHtml, zero review storage).
    forbidden_rd = re.compile(r"(qualification[/\\]|research[/\\]|evaluation[/\\]|ELedgerCare\.(Qualification|Research|Evaluation))", re.IGNORECASE)
    for folder in (REPO_ROOT / "src", REPO_ROOT / "web" / "src", REPO_ROOT / "workers"):
        for p in folder.rglob("*"):
            if p.is_file() and p.suffix in {".cs", ".csproj", ".ts", ".html", ".py"}:
                if "bin" in p.parts or "obj" in p.parts or "dist" in p.parts:
                    continue
                if forbidden_rd.search(p.read_text(encoding="utf-8")):
                    raise RuntimeError(f"Forbidden R&D reference in {p}")

    def strip_ts_comments(source: str) -> str:
        without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
        return re.sub(r"(?m)^\s*//.*$", "", without_block)

    storage_re = re.compile(r"\b(localStorage|sessionStorage|indexedDB)\s*\.")
    resource_url_files: list[str] = []
    for p in (REPO_ROOT / "web" / "src").rglob("*"):
        if p.is_file() and p.suffix in {".ts", ".html"}:
            rel = str(p.relative_to(REPO_ROOT)).replace("\\", "/")
            code = strip_ts_comments(p.read_text(encoding="utf-8"))
            if "[innerHTML]" in code or "bypassSecurityTrustHtml" in code:
                raise RuntimeError(f"Forbidden HTML sink in {rel}")
            if "bypassSecurityTrustResourceUrl" in code:
                resource_url_files.append(rel)
            if "/review/" in rel and storage_re.search(code):
                raise RuntimeError(f"Forbidden browser storage reference in {rel}")
    if resource_url_files != ["web/src/app/review/pdf-preview-url.ts"]:
        raise RuntimeError(f"Unexpected bypassSecurityTrustResourceUrl usage: {resource_url_files}")

    # 7. Verify author /006 evidence-manifest.json & retained-failure blob hashes via Git object store.
    manifest_raw = git_bytes(
        "show",
        f"{AUTHOR_FINAL_P006_EVIDENCE_SHA}:docs/implementation/WP-0008/eld-f3-implementer/presentation-correction/evidence/evidence-manifest.json",
    )
    manifest = json.loads(manifest_raw.decode("utf-8"))
    for entry in manifest["files"]:
        rel_p = entry["path"]
        blob = git_bytes("show", f"{AUTHOR_FINAL_P006_EVIDENCE_SHA}:{rel_p}")
        if len(blob) != entry["bytes"] or sha256_bytes(blob) != entry["sha256"]:
            raise RuntimeError(f"Author /006 manifest mismatch on {rel_p}")

    ret_blob = git_bytes(
        "show",
        f"{AUTHOR_FINAL_P006_CANDIDATE_SHA}:docs/implementation/WP-0008/eld-f3-implementer/presentation-correction/retained-failures/bc82102b-04-edge-retained-db-presentation.log",
    )
    ret_sha = sha256_bytes(ret_blob)
    if ret_sha != EXPECTED_AUTHOR_RETAINED_LOG_SHA256:
        raise RuntimeError(f"Author retained failure log SHA-256 mismatch: {ret_sha}")

    return {
        "frozen_reviewer_helper_sha": frozen_head_sha,
        "author_final_candidate_sha": AUTHOR_FINAL_P006_CANDIDATE_SHA,
        "web_tree_oid": head_web_oid,
        "product_diff_files_vs_62e8666a": product_diff_files,
        "unchanged_product_oids_vs_62e8666a": unchanged_product_oids,
        "protected_checks_all_true": True,
        "angular_cli_version_verified": "22.2.7",
        "package_lock_sha256": lock_sha,
        "author_evidence_manifest_files_verified": len(manifest["files"]),
        "author_retained_failure_log_bytes": len(ret_blob),
        "author_retained_failure_log_sha256": ret_sha,
    }


def main() -> int:
    initial_dirty = git_out("status", "--porcelain")
    if initial_dirty:
        raise RuntimeError(f"Worktree must be clean (frozen helper committed) before decisive execution:\n{initial_dirty}")

    frozen_head_sha = git_out("rev-parse", "HEAD")
    settings = load_pg_settings()

    if EVIDENCE_DIR.exists():
        shutil.rmtree(EVIDENCE_DIR)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    started_utc = utc_now()
    steps: list[dict] = []
    service_ledger: list[dict] = []

    api_proc: subprocess.Popen | None = None
    api_log: object | None = None
    api_ident: dict | None = None
    ui_proc: subprocess.Popen | None = None
    ui_log: object | None = None
    ui_ident: dict | None = None

    pg_ctl = REPO_ROOT / ".local" / "tools" / "pgsql-18.7-1" / "bin" / "pg_ctl.exe"
    pg_data = REPO_ROOT / ".local" / "postgres-data"

    try:
        # 1. Static, Git-tree, boundary, and author-manifest audit.
        static_audit = run_static_and_author_audit(frozen_head_sha)

        initial_ports = query_port_listeners([API_PORT, UI_PORT, PG_PORT])
        if any(initial_ports.values()):
            raise RuntimeError(f"Owned reviewer ports must be unbound at start, got {initial_ports}")

        pre_pg = subprocess.run([str(pg_ctl), "status", "-D", str(pg_data)], capture_output=True, text=True)
        if pre_pg.returncode != 3:
            raise RuntimeError(f"Expected stopped reviewer PG cluster (rc=3) at start, got rc={pre_pg.returncode}")

        # 2. Start reviewer PG 55437 and capture full pre-check snapshot of preserved /004 eledgercare_f3_reviewer_seed_f2.
        steps.append(run_logged("01-pg-cluster-start", ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"], REPO_ROOT, settings))
        pm_pid = int((pg_data / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        pm_ident = get_process_identity(pm_pid)
        service_ledger.append({"service": "postgresql-55437-start", "identity": pm_ident})

        seed_before = query_seed_db_complete_snapshot(SEED_DB)
        if seed_before["core_state_sha256"] != EXPECTED_POST_MIGRATION_SEED_CORE_SHA256:
            raise RuntimeError(f"Unexpected {SEED_DB} core_state_sha256: {seed_before['core_state_sha256']}")
        if seed_before["f1_f2_rows_and_seq_sha256"] != EXPECTED_F1_F2_ROWS_AND_SEQ_SHA256:
            raise RuntimeError(f"Unexpected {SEED_DB} f1_f2_rows_and_seq_sha256: {seed_before['f1_f2_rows_and_seq_sha256']}")
        if seed_before["counts"] != {"documents": 4, "attempts": 4, "results": 3, "heads": 2, "revisions": 132, "fields": 660}:
            raise RuntimeError(f"Unexpected {SEED_DB} preserved /004 counts: {seed_before['counts']}")
        if not seed_before["seed1_head"] or seed_before["seed1_head"]["current_revision_id"] != SEED1_REV4_ID or seed_before["seed1_head"]["current_revision_number"] != 4:
            raise RuntimeError(f"Unexpected Seed 1 head state: {seed_before['seed1_head']}")
        if not seed_before["seed3_head"] or seed_before["seed3_head"]["current_revision_number"] != 128:
            raise RuntimeError(f"Unexpected Seed 3 head state: {seed_before['seed3_head']}")

        # 3. Run production Angular build (ng build).
        steps.append(run_logged("02-ng-build-production", ["node", "node_modules/@angular/cli/bin/ng.js", "build"], REPO_ROOT / "web", settings))
        post_build_dirty = [
            ln for ln in git_out("status", "--porcelain").splitlines()
            if "docs/reviews/WP-0008/eld-f3-reviewer/presentation-reconciliation/evidence" not in ln
        ]
        if post_build_dirty:
            raise RuntimeError(f"ng build mutated tracked/unignored files outside evidence/: {post_build_dirty}")

        # 4. Run full 13-spec Playwright Microsoft Edge suite against disposable eledgercare_f3_rev_p007_e2e on 5490/4510.
        steps.append(
            run_logged(
                "03-playwright-edge-e2e-5490-4510",
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    "deploy/dev/smoke/run-browser-checks.ps1",
                    "-Database",
                    P007_E2E_DB,
                    "-ApiPort",
                    str(API_PORT),
                    "-UiPort",
                    str(UI_PORT),
                ],
                REPO_ROOT,
                settings,
            )
        )
        wait_port_free(API_PORT, timeout_s=20.0)
        wait_port_free(UI_PORT, timeout_s=20.0)

        # 5. Start reviewer API (5490, LocalOcr__Enabled=false) + UI (4510) bound to preserved eledgercare_f3_reviewer_seed_f2
        #    and run independent Microsoft Edge presentation & saved-/004-state verification!
        api_proc, api_log, api_ident = start_owned_api(SEED_DB, "p007")
        ui_proc, ui_log, ui_ident = start_owned_ui("p007")
        service_ledger.append({"service": "api-5490-p007", "identity": api_ident})
        service_ledger.append({"service": "ui-4510-p007", "identity": ui_ident})

        edge_receipt_path = EVIDENCE_DIR / "edge-reviewer-p007-receipt.json"
        edge_cfg_path = REPO_ROOT / ".scratch" / "edge-reviewer-p007-cfg.json"
        edge_cfg_path.parent.mkdir(parents=True, exist_ok=True)
        edge_cfg_path.write_text(
            json.dumps(
                {
                    "uiPort": UI_PORT,
                    "screenshotsDir": str(SCREENSHOTS_DIR),
                    "receiptPath": str(edge_receipt_path),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        steps.append(
            run_logged(
                "04-edge-reviewer-seed-db-presentation",
                [
                    "node",
                    "docs/reviews/WP-0008/eld-f3-reviewer/presentation-reconciliation/helpers/verify_f3_presentation_reviewer.mjs",
                    "--config",
                    str(edge_cfg_path),
                ],
                REPO_ROOT,
                settings,
            )
        )

        ui_stop = stop_owned_proc(ui_proc, ui_log, ui_ident)
        ui_proc = ui_log = ui_ident = None
        api_stop = stop_owned_proc(api_proc, api_log, api_ident)
        api_proc = api_log = api_ident = None
        service_ledger.append({"service": "ui-4510-p007-stop", "stop": ui_stop})
        service_ledger.append({"service": "api-5490-p007-stop", "stop": api_stop})
        wait_port_free(UI_PORT, timeout_s=15.0)
        wait_port_free(API_PORT, timeout_s=15.0)

        # 6. Verify 100% zero mutation of preserved eledgercare_f3_reviewer_seed_f2 across all 8 tables + sequence!
        seed_after = query_seed_db_complete_snapshot(SEED_DB)
        if seed_after["full_8_table_sha256"] != seed_before["full_8_table_sha256"]:
            raise RuntimeError(
                f"Preserved {SEED_DB} mutated during /007 reconciliation! before={seed_before['full_8_table_sha256']} after={seed_after['full_8_table_sha256']}"
            )
        if seed_after["f1_f2_rows_and_seq_sha256"] != EXPECTED_F1_F2_ROWS_AND_SEQ_SHA256:
            raise RuntimeError("F1/F2 rows or extraction_fencing_seq changed!")

        owned_ocr_workers = check_owned_local_ocr_workers()
        if owned_ocr_workers:
            raise RuntimeError(f"Observed unexpected local_ocr worker under reviewer worktree: {owned_ocr_workers}")

        # 7. Stop PostgreSQL 55437 cleanly and verify all owned services/ports are stopped.
        steps.append(run_logged("05-pg-cluster-stop", ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"], REPO_ROOT, settings))
        wait_port_free(PG_PORT, timeout_s=20.0)

        post_pg = subprocess.run([str(pg_ctl), "status", "-D", str(pg_data)], capture_output=True, text=True)
        final_ports = query_port_listeners([PG_PORT, UI_PORT, API_PORT])
        if post_pg.returncode != 3 or any(final_ports.values()):
            raise RuntimeError(f"Services not cleanly stopped: pg_ctl={post_pg.returncode}, ports={final_ports}")

        summary = {
            "schema": "eledgercare.wp-0008.f3-reviewer-p007-summary/1",
            "reviewer": "eld-f3-reviewer",
            "started_utc": started_utc,
            "completed_utc": utc_now(),
            "outcome": "PASSED_ALL_INDEPENDENT_PRESENTATION_RECONCILIATION_CHECKS",
            "static_and_author_audit": static_audit,
            "reused_accepted_004_backend_evidence": {
                "accepted_004_report_sha": PRIOR_ACCEPTANCE_004_SHA,
                "accepted_004_evidence_sha": "7675ba2494fb951252bdcfb52661572e0f822c56",
                "accepted_004_helper_sha": "4a00f1a41588b54b4cd36d7c10d42550f59a0f19",
                "checks_reused_without_rerun_because_backend_trees_identical": [
                    "workers/local_ocr CPU unit suite (9/9 passed in /004; workers/ tree 9b548ddcc73cfba8e7683d132840b08afa5a67a3 unchanged)",
                    "dotnet test ELedgerCare.slnx -c Release (85/85 passed in /004; src/ e0dc8651..., tests/ 838979ed..., deploy/ 4c410b6c... unchanged)",
                    "Forward F2->F3 migration & least-privilege/FK catalog audit & PG+API full restart reopen (verified in /004; schema & migrations unchanged)",
                ],
            },
            "preserved_seed_db_invariance": {
                "database": SEED_DB,
                "core_state_sha256": seed_after["core_state_sha256"],
                "f1_f2_rows_and_seq_sha256": seed_after["f1_f2_rows_and_seq_sha256"],
                "full_8_table_sha256_before": seed_before["full_8_table_sha256"],
                "full_8_table_sha256_after": seed_after["full_8_table_sha256"],
                "zero_mutation_verified": True,
                "counts": seed_after["counts"],
                "seed1_head": seed_after["seed1_head"],
                "seed3_head": seed_after["seed3_head"],
                "observed_owned_local_ocr_workers": 0,
            },
            "service_ledger": service_ledger,
            "final_stopped_state": {
                "pg_ctl_status_exit_code": post_pg.returncode,
                "pg_ctl_status_output": post_pg.stdout.strip(),
                "port_listeners": final_ports,
            },
            "steps": steps,
        }
        (EVIDENCE_DIR / "reconciliation-verification-summary.json").write_text(
            json.dumps(summary, indent=2) + "\n",
            encoding="utf-8",
        )
        print("ALL /007 PRESENTATION RECONCILIATION CHECKS PASSED.")
        return 0
    finally:
        if ui_proc is not None:
            stop_owned_proc(ui_proc, ui_log, ui_ident)
        if api_proc is not None:
            stop_owned_proc(api_proc, api_log, api_ident)
        if is_port_listening(PG_PORT):
            subprocess.run(["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"], cwd=str(REPO_ROOT), capture_output=True)


if __name__ == "__main__":
    raise SystemExit(main())
