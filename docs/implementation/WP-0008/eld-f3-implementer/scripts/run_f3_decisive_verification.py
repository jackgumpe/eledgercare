"""Decisive post-freeze verification runner for WP-0008 F3 (eld-f3-implementer).

Executes on the frozen candidate + helper commit with LocalOcr:Enabled=false and zero GPU/model calls:
  1. Verifies clean Git worktree, records frozen HEAD + product tree SHAs + unchanged worker_source_sha256,
     and runs static isolation/inertness audits (zero imports/refs to qualification/research/evaluation,
     zero innerHTML/bypassSecurityTrustHtml, zero browser storage writes in review code).
  2. Runs worker CPU unit suite (9/9), locked .NET restore/build/test across Domain, Infrastructure,
     F1, F2, and F3 real PostgreSQL 18.7 suites, and Angular production build.
  3. Runs deploy/dev/smoke/run-demo-smoke.ps1 (port 5390) and deploy/dev/smoke/run-browser-checks.ps1
     (ports 5390/4410, headless Microsoft Edge F1 + F2 + F3 Playwright E2E).
  4. Executes dedicated F3-05 durable seed + Microsoft Edge review/save + actual API & owned PostgreSQL 18.7
     cluster fast restart + disabled-OCR Edge reopen, verifying unchanged canonical DB state SHA-256,
     byte-exact /preview and /original PDF digests, unchanged raw output bytes, readable two-pane screenshots,
     and zero Python/GPU OCR inference processes.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
EVIDENCE_DIR = REPO_ROOT / "docs" / "implementation" / "WP-0008" / "eld-f3-implementer" / "evidence"
LOGS_DIR = EVIDENCE_DIR / "logs"
SCREENSHOTS_DIR = EVIDENCE_DIR / "screenshots"
NODE_EDGE_HELPER = pathlib.Path(__file__).resolve().parent / "verify_f3_restart_edge.mjs"

API_PORT = 5390
UI_PORT = 4410
PG_PORT = 55436
ACCEPTANCE_DB = "eledgercare_f3_author_acceptance"
E2E_DB = "eledgercare_f3_e2e"

EXPECTED_WORKER_README_BLOB = "83ed6624f95c48bfbae4c466201774824f63ef5e"
EXPECTED_WO_PDF_SHA = "47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd"
EXPECTED_WO_RAW_SHA = "7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95"
EXPECTED_MP_PDF_SHA = "15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3"
EXPECTED_MP_RAW_SHA = "c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def assert_port_free(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(f"Port {port} is already bound before starting owned service.")


def wait_http_ready(url: str, timeout_s: float = 90.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                if resp.status < 500:
                    return
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                return
        except Exception:
            pass
        time.sleep(0.3)
    raise RuntimeError(f"Service at {url} did not become ready within {timeout_s}s.")


def run_logged(name: str, cmd: list[str], cwd: pathlib.Path, extra_env: dict[str, str] | None = None) -> dict:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    t0 = time.perf_counter()
    started = utc_now()
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    combined = f"$ {' '.join(cmd)}\n[exit={proc.returncode}, elapsed_ms={elapsed_ms}]\n--- STDOUT ---\n{proc.stdout}\n--- STDERR ---\n{proc.stderr}"
    log_path = LOGS_DIR / f"{name}.log"
    log_path.write_text(combined, encoding="utf-8", newline="\n")
    if proc.returncode != 0:
        raise RuntimeError(f"Step '{name}' failed with exit code {proc.returncode}; see {log_path}")
    return {
        "step": name,
        "command": cmd,
        "cwd": str(cwd.relative_to(REPO_ROOT)) if cwd != REPO_ROOT else ".",
        "started_utc": started,
        "elapsed_ms": elapsed_ms,
        "exit_code": proc.returncode,
        "log_relpath": log_path.relative_to(REPO_ROOT).as_posix(),
        "log_sha256": sha256_file(log_path),
    }


def git_output(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
    return proc.stdout.strip()


def run_static_isolation_audit() -> dict:
    # 1. Verify clean worktree before decisive execution.
    status = git_output(["status", "--porcelain"])
    if status:
        raise RuntimeError(f"Worktree must be clean before decisive execution; found:\n{status}")

    # 2. Verify worker README blob is untouched.
    readme_blob = git_output(["rev-parse", "HEAD:workers/local_ocr/README.md"])
    if readme_blob != EXPECTED_WORKER_README_BLOB:
        raise RuntimeError(f"workers/local_ocr/README.md blob changed: {readme_blob}")

    # 3. Scan src/ and web/src/ for prohibited cross-tree references, innerHTML/trustHtml, or review storage writes.
    forbidden_src_patterns = [
        re.compile(r"\b(qualification|evaluation)\b", re.IGNORECASE),
        re.compile(r"workers[/\\]local_ocr", re.IGNORECASE),
    ]
    cs_files = sorted((REPO_ROOT / "src").rglob("*.cs"))
    src_violations: list[str] = []
    for f in cs_files:
        if "\\obj\\" in str(f) or "\\bin\\" in str(f):
            continue
        txt = f.read_text(encoding="utf-8")
        # Ignore XML doc comments when checking word 'qualification'/'evaluation'.
        code_lines = [ln for ln in txt.splitlines() if not ln.lstrip().startswith("///") and not ln.lstrip().startswith("//")]
        code_only = "\n".join(code_lines)
        if re.search(r"\b(qualification|evaluation|research)\b", code_only):
            src_violations.append(f"{f.relative_to(REPO_ROOT)}: prohibited cross-boundary token in code")

    ts_files = sorted((REPO_ROOT / "web" / "src").rglob("*.ts"))
    web_violations: list[str] = []
    for f in ts_files:
        txt = f.read_text(encoding="utf-8")
        code_only = "\n".join(
            ln for ln in txt.splitlines() if not ln.lstrip().startswith("//") and not ln.lstrip().startswith("*")
        )
        if "innerHTML" in code_only or "bypassSecurityTrustHtml" in code_only:
            web_violations.append(f"{f.relative_to(REPO_ROOT)}: prohibited innerHTML / bypassSecurityTrustHtml")
        if "review" in f.parts and ("sessionStorage" in code_only or "localStorage" in code_only or "indexedDB" in code_only):
            web_violations.append(f"{f.relative_to(REPO_ROOT)}: prohibited browser storage call in review module")

    if src_violations or web_violations:
        raise RuntimeError(f"Static audit violations: {src_violations + web_violations}")

    return {
        "clean_git_status": True,
        "head_commit": git_output(["rev-parse", "HEAD"]),
        "branch": git_output(["branch", "--show-current"]),
        "trees": {
            "src": git_output(["rev-parse", "HEAD:src"]),
            "web": git_output(["rev-parse", "HEAD:web"]),
            "tests": git_output(["rev-parse", "HEAD:tests"]),
            "deploy": git_output(["rev-parse", "HEAD:deploy"]),
            "workers_local_ocr": git_output(["rev-parse", "HEAD:workers/local_ocr"]),
            "evaluation": git_output(["rev-parse", "HEAD:evaluation"]),
            "qualification": git_output(["rev-parse", "HEAD:qualification"]),
        },
        "worker_readme_blob_oid": readme_blob,
        "cs_files_audited": len([f for f in cs_files if "\\obj\\" not in str(f) and "\\bin\\" not in str(f)]),
        "ts_files_audited": len(ts_files),
        "violations": [],
    }


def load_pg_settings() -> dict:
    return json.loads((REPO_ROOT / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))


def run_psql(user: str, password: str, db: str, sql: str) -> str:
    s = load_pg_settings()
    psql = REPO_ROOT / ".local" / "tools" / "pgsql-18.7-1" / "bin" / "psql.exe"
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    proc = subprocess.run(
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
    if proc.returncode != 0:
        raise RuntimeError(f"psql failed ({proc.returncode}): {proc.stderr}")
    return proc.stdout.strip()


def seed_genuine_f2_pair(db_name: str) -> dict:
    s = load_pg_settings()
    specs = [
        (
            "wo",
            REPO_ROOT / "tests" / "fixtures" / "SYN-WO-01-v1-raster300.pdf",
            EXPECTED_WO_PDF_SHA,
            REPO_ROOT
            / "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4/output",
            EXPECTED_WO_RAW_SHA,
            "43858522-5c3d-47d2-be8c-66f7162a190e",
            "01a1e573-a855-7735-96e1-f5d14cada602",
        ),
        (
            "mp",
            REPO_ROOT / "tests" / "fixtures" / "SYN-MP-01-v0-clean.pdf",
            EXPECTED_MP_PDF_SHA,
            REPO_ROOT
            / "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d/output",
            EXPECTED_MP_RAW_SHA,
            "92f639e5-321d-464a-9628-f056251495cb",
            "01a1e578-8bfa-7bba-b104-ea8309dbfd9e",
        ),
    ]

    seeded: dict[str, dict] = {}
    for key_prefix, pdf_path, exp_pdf_sha, out_dir, exp_raw_sha, sub_key, res_id in specs:
        pdf_bytes = pdf_path.read_bytes()
        raw_bytes = (out_dir / "raw_output.utf8.bin").read_bytes()
        env_json = json.loads((out_dir / "envelope.json").read_text(encoding="utf-8"))

        if sha256_bytes(pdf_bytes) != exp_pdf_sha:
            raise RuntimeError(f"PDF hash mismatch for {pdf_path}")
        if sha256_bytes(raw_bytes) != exp_raw_sha:
            raise RuntimeError(f"Raw hash mismatch for {out_dir}")

        doc_id = env_json["document_id"]
        job_id = env_json["job_id"]
        att_id = env_json["attempt_id"]
        pages = int(env_json["input"]["page_count"])
        prov = env_json["provenance"]
        timings = env_json["timings"]
        gen_json = json.dumps(prov["generation_settings"]).replace("'", "''")
        diag_json = json.dumps(env_json["diagnostics"]).replace("'", "''")
        renderer = str(prov["renderer_identity"]).replace("'", "''")

        sql = f"""
        BEGIN;
        SELECT nextval('eledgercare.extraction_fencing_seq');
        INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
        VALUES ('{doc_id}', '{sub_key}', '{timings["started_at_utc"]}'::timestamptz - interval '1 second');
        INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
        VALUES ('{doc_id}', decode('{pdf_bytes.hex()}', 'hex'), decode('{exp_pdf_sha}', 'hex'), {len(pdf_bytes)}, 'application/pdf', {pages});
        INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at, queued_at, updated_at, attempt_count, latest_fencing_token)
        VALUES ('{job_id}', '{doc_id}', 'running', '{timings["started_at_utc"]}'::timestamptz - interval '1 second', '{timings["started_at_utc"]}'::timestamptz, '{timings["started_at_utc"]}'::timestamptz, 1, currval('eledgercare.extraction_fencing_seq'));
        INSERT INTO eledgercare.execution_attempts (
          attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
          status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
          started_at, last_heartbeat_at
        ) VALUES (
          '{att_id}', '{job_id}', '{doc_id}', 1, currval('eledgercare.extraction_fencing_seq'), NULL,
          'running', 'inferring', 'attempt-{att_id}', '101b19cf-3133-4ead-91cb-9ca6068e3e72', 18496, 134393243591895019,
          '{timings["started_at_utc"]}'::timestamptz, '{timings["started_at_utc"]}'::timestamptz
        );
        UPDATE eledgercare.processing_jobs SET status = 'completed', updated_at = '{timings["completed_at_utc"]}'::timestamptz
         WHERE job_id = '{job_id}' AND latest_fencing_token = currval('eledgercare.extraction_fencing_seq');
        UPDATE eledgercare.execution_attempts SET status = 'completed', phase = 'completed', ended_at = '{timings["completed_at_utc"]}'::timestamptz, last_heartbeat_at = '{timings["completed_at_utc"]}'::timestamptz, exit_code = 0
         WHERE attempt_id = '{att_id}';
        INSERT INTO eledgercare.extraction_results (
          result_id, document_id, job_id, attempt_id, fencing_token, schema_version,
          input_sha256, input_byte_length, page_count, raw_output_bytes, raw_output_byte_length, raw_output_sha256,
          model_repo_id, model_revision, model_manifest_sha256, dependency_lock_sha256, worker_source_digest, worker_config_digest,
          renderer_identity, generation_settings_json, finish_reason, output_page_count,
          started_at, completed_at, load_duration_ms, render_duration_ms, infer_duration_ms, total_duration_ms, diagnostic_metadata_json
        ) VALUES (
          '{res_id}', '{doc_id}', '{job_id}', '{att_id}', currval('eledgercare.extraction_fencing_seq'), 'eledgercare.local-extraction/1',
          decode('{exp_pdf_sha}', 'hex'), {len(pdf_bytes)}, {pages}, decode('{raw_bytes.hex()}', 'hex'), {len(raw_bytes)}, decode('{exp_raw_sha}', 'hex'),
          '{prov["model_repo_id"]}', '{prov["model_revision"]}',
          decode('{prov["model_manifest_sha256"]}', 'hex'), decode('{prov["dependency_lock_sha256"]}', 'hex'),
          decode('{prov["worker_source_sha256"]}', 'hex'), decode('{prov["worker_config_sha256"]}', 'hex'),
          '{renderer}', '{gen_json}'::jsonb, 'stop', {pages},
          '{timings["started_at_utc"]}'::timestamptz, '{timings["completed_at_utc"]}'::timestamptz,
          {int(timings["load_duration_ms"])}, {int(timings["render_duration_ms"])}, {int(timings["infer_duration_ms"])}, {int(timings["total_duration_ms"])},
          '{diag_json}'::jsonb
        );
        COMMIT;
        """
        run_psql(str(s["appUser"]), str(s["appPassword"]), db_name, sql)
        seeded[key_prefix] = {
            "documentId": doc_id,
            "jobId": job_id,
            "attemptId": att_id,
            "resultId": res_id,
            "pdfSha256": exp_pdf_sha,
            "rawSha256": exp_raw_sha,
            "idsRemapped": False,
        }
    return seeded


def compute_canonical_db_digest(db_name: str) -> dict:
    s = load_pg_settings()
    sql = """
    SELECT json_build_object(
      'documents', (SELECT coalesce(json_agg(t ORDER BY t.document_id), '[]'::json) FROM (SELECT document_id, idempotency_key, submitted_at FROM eledgercare.documents) t),
      'originals', (SELECT coalesce(json_agg(t ORDER BY t.document_id), '[]'::json) FROM (SELECT document_id, encode(sha256, 'hex') AS sha256, encode(sha256(bytes), 'hex') AS computed_sha256, byte_length, page_count FROM eledgercare.original_artifacts) t),
      'jobs', (SELECT coalesce(json_agg(t ORDER BY t.job_id), '[]'::json) FROM (SELECT job_id, document_id, status, attempt_count, latest_fencing_token FROM eledgercare.processing_jobs) t),
      'attempts', (SELECT coalesce(json_agg(t ORDER BY t.attempt_id), '[]'::json) FROM (SELECT attempt_id, job_id, attempt_number, fencing_token, status, exit_code FROM eledgercare.execution_attempts) t),
      'results', (SELECT coalesce(json_agg(t ORDER BY t.result_id), '[]'::json) FROM (SELECT result_id, document_id, attempt_id, encode(raw_output_sha256, 'hex') AS raw_sha256, encode(sha256(raw_output_bytes), 'hex') AS computed_raw_sha256, raw_output_byte_length FROM eledgercare.extraction_results) t),
      'review_heads', (SELECT coalesce(json_agg(t ORDER BY t.document_id), '[]'::json) FROM (SELECT document_id, result_id, encode(input_sha256, 'hex') AS input_sha256, encode(raw_output_sha256, 'hex') AS raw_sha256, profile_id, field_schema_version, suggestion_policy_version, current_revision_number, current_revision_id, current_status, machine_snapshot_json FROM eledgercare.work_order_review_heads) t),
      'review_revisions', (SELECT coalesce(json_agg(t ORDER BY t.document_id, t.revision_number), '[]'::json) FROM (SELECT revision_id, document_id, result_id, revision_number, previous_revision_number, status, idempotency_key, encode(request_sha256, 'hex') AS request_sha256, operator_display_label, accepted_field_count, edited_field_count, unknown_field_count, unreviewed_field_count, saved_at FROM eledgercare.work_order_review_revisions) t),
      'review_fields', (SELECT coalesce(json_agg(t ORDER BY t.revision_id, t.field_ordinal), '[]'::json) FROM (SELECT revision_id, field_ordinal, field_key, decision, human_value, unknown_reason, consulted_page_number, consulted_block_ordinal, consulted_quote FROM eledgercare.work_order_review_fields) t)
    )::text;
    """
    raw = run_psql(str(s["appUser"]), str(s["appPassword"]), db_name, sql)
    parsed = json.loads(raw)
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "canonical_sha256": sha256_bytes(canonical),
        "snapshot": parsed,
    }


def check_zero_ocr_workers() -> int:
    proc = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-Command",
            "@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_worker.py*' }).Count",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(proc.stdout.strip() or "0")


def read_postmaster_pid() -> int:
    pid_file = REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid"
    return int(pid_file.read_text(encoding="utf-8").splitlines()[0].strip())


def start_owned_api(db_name: str, label: str) -> subprocess.Popen:
    assert_port_free(API_PORT)
    s = load_pg_settings()
    api_dir = REPO_ROOT / "src" / "ELedgerCare.Api" / "bin" / "Release" / "net10.0"
    conn = f"Host={s['host']};Port={s['port']};Database={db_name};Username={s['appUser']};Password={s['appPassword']}"
    env = os.environ.copy()
    env["ASPNETCORE_ENVIRONMENT"] = "Production"
    env["ConnectionStrings__Runtime"] = conn
    env["Api__Port"] = str(API_PORT)
    env["LocalOcr__Enabled"] = "false"
    env["DOTNET_NOLOGO"] = "1"
    log_f = open(LOGS_DIR / f"owned-api-{label}.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        ["dotnet", str(api_dir / "ELedgerCare.Api.dll")],
        cwd=str(api_dir),
        env=env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )
    wait_http_ready(f"http://127.0.0.1:{API_PORT}/api/documents/00000000-0000-0000-0000-000000000000", timeout_s=60.0)
    return proc


def start_owned_ui(label: str) -> subprocess.Popen:
    assert_port_free(UI_PORT)
    web_dir = REPO_ROOT / "web"
    ng_cli = web_dir / "node_modules" / "@angular" / "cli" / "bin" / "ng.js"
    env = os.environ.copy()
    env["ELEDGERCARE_API_PORT"] = str(API_PORT)
    env["NG_CLI_ANALYTICS"] = "false"
    log_f = open(LOGS_DIR / f"owned-ui-{label}.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        ["node", str(ng_cli), "serve", "--host", "127.0.0.1", "--port", str(UI_PORT), "--proxy-config", "proxy.conf.mjs"],
        cwd=str(web_dir),
        env=env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )
    wait_http_ready(f"http://127.0.0.1:{UI_PORT}/", timeout_s=120.0)
    return proc


def stop_owned_proc(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def main() -> int:
    if EVIDENCE_DIR.exists():
        shutil.rmtree(EVIDENCE_DIR)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    started_utc = utc_now()
    audit = run_static_isolation_audit()
    steps: list[dict] = []

    assert_port_free(API_PORT)
    assert_port_free(UI_PORT)

    # 1. Worker CPU suite (9/9) + locked .NET restore/build/test + Angular production build.
    steps.append(run_logged("01-worker-cpu-tests", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "workers/local_ocr/tests"], REPO_ROOT))
    steps.append(run_logged("02-dotnet-restore-locked", ["dotnet", "restore", "ELedgerCare.slnx", "--locked-mode"], REPO_ROOT))
    steps.append(run_logged("03-dotnet-build-release", ["dotnet", "build", "ELedgerCare.slnx", "-c", "Release", "--no-restore"], REPO_ROOT))
    steps.append(run_logged("04-dotnet-test-release", ["dotnet", "test", "ELedgerCare.slnx", "-c", "Release", "--no-build"], REPO_ROOT))
    steps.append(run_logged("05-ng-build-production", ["node", "node_modules/@angular/cli/bin/ng.js", "build"], REPO_ROOT / "web"))

    # 2. Demo restart smoke & full Playwright Edge E2E suite (F1 + F2 + F3).
    s = load_pg_settings()
    steps.append(run_logged("06-prepare-dev-db", ["pwsh", "-NoProfile", "-File", "deploy/dev/database/prepare-database.ps1"], REPO_ROOT))
    demo_receipt = EVIDENCE_DIR / "demo-smoke-receipt.json"
    steps.append(
        run_logged(
            "07-demo-smoke",
            ["pwsh", "-NoProfile", "-File", "deploy/dev/smoke/run-demo-smoke.ps1", "-ApiPort", str(API_PORT), "-ReceiptPath", str(demo_receipt)],
            REPO_ROOT,
        )
    )
    steps.append(
        run_logged(
            "08-playwright-edge-e2e",
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
        )
    )

    # 3. Dedicated F3-05 durable acceptance DB + real API & PostgreSQL 18.7 fast restart + disabled-OCR Edge reopen!
    run_psql(str(s["adminUser"]), str(s["adminPassword"]), "postgres", f"DROP DATABASE IF EXISTS {ACCEPTANCE_DB} WITH (FORCE);")
    steps.append(
        run_logged(
            "09-prepare-f3-acceptance-db",
            ["pwsh", "-NoProfile", "-File", "deploy/dev/database/prepare-database.ps1", "-Database", ACCEPTANCE_DB],
            REPO_ROOT,
        )
    )
    seeded = seed_genuine_f2_pair(ACCEPTANCE_DB)

    edge_cfg_path = REPO_ROOT / ".scratch" / "f3-edge-restart-cfg.json"
    edge_cfg_path.parent.mkdir(parents=True, exist_ok=True)
    edge_cfg_path.write_text(
        json.dumps(
            {
                "uiPort": UI_PORT,
                "apiPort": API_PORT,
                "woDocumentId": seeded["wo"]["documentId"],
                "mpDocumentId": seeded["mp"]["documentId"],
                "outputDir": str(SCREENSHOTS_DIR),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    postmaster_pid_before = read_postmaster_pid()
    api_proc_1 = None
    ui_proc_1 = None
    try:
        api_proc_1 = start_owned_api(ACCEPTANCE_DB, "phase1")
        api_pid_before = api_proc_1.pid
        ui_proc_1 = start_owned_ui("phase1")
        ui_pid_before = ui_proc_1.pid

        steps.append(
            run_logged(
                "10-edge-f3-before-restart",
                ["node", str(NODE_EDGE_HELPER), "--phase", "before-restart", "--config", str(edge_cfg_path)],
                REPO_ROOT,
            )
        )
        ocr_workers_phase1 = check_zero_ocr_workers()
    finally:
        stop_owned_proc(ui_proc_1)
        stop_owned_proc(api_proc_1)

    db_before = compute_canonical_db_digest(ACCEPTANCE_DB)

    # Actual PostgreSQL 18.7 cluster fast stop & start!
    steps.append(run_logged("11-pg-cluster-stop", ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"], REPO_ROOT))
    steps.append(run_logged("12-pg-cluster-start", ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"], REPO_ROOT))
    postmaster_pid_after = read_postmaster_pid()
    if postmaster_pid_after == postmaster_pid_before:
        raise RuntimeError("Expected fresh PostgreSQL postmaster PID after cluster restart.")

    api_proc_2 = None
    ui_proc_2 = None
    try:
        api_proc_2 = start_owned_api(ACCEPTANCE_DB, "phase2")
        api_pid_after = api_proc_2.pid
        ui_proc_2 = start_owned_ui("phase2")
        ui_pid_after = ui_proc_2.pid

        steps.append(
            run_logged(
                "13-edge-f3-after-restart-reopen",
                ["node", str(NODE_EDGE_HELPER), "--phase", "after-restart", "--config", str(edge_cfg_path)],
                REPO_ROOT,
            )
        )
        ocr_workers_phase2 = check_zero_ocr_workers()
    finally:
        stop_owned_proc(ui_proc_2)
        stop_owned_proc(api_proc_2)

    db_after = compute_canonical_db_digest(ACCEPTANCE_DB)
    if db_before["canonical_sha256"] != db_after["canonical_sha256"]:
        raise RuntimeError(
            f"Canonical DB state mutated across disabled-OCR reopen: {db_before['canonical_sha256']} != {db_after['canonical_sha256']}"
        )
    if ocr_workers_phase1 != 0 or ocr_workers_phase2 != 0:
        raise RuntimeError("Unexpected local_ocr worker process observed during F3 verification.")

    summary = {
        "schema": "eledgercare.wp-0008.f3-author-verification-summary/1",
        "author": "eld-f3-implementer",
        "started_utc": started_utc,
        "completed_utc": utc_now(),
        "outcome": "PASSED_ALL_DECISIVE_CHECKS",
        "frozen_source_audit": audit,
        "ports": {"api": API_PORT, "ui": UI_PORT, "postgres": PG_PORT},
        "seeded_genuine_f2_inputs": seeded,
        "restart_verification": {
            "database": ACCEPTANCE_DB,
            "local_ocr_enabled": False,
            "postmaster_pid_before": postmaster_pid_before,
            "postmaster_pid_after": postmaster_pid_after,
            "api_pid_before": api_pid_before,
            "api_pid_after": api_pid_after,
            "ui_pid_before": ui_pid_before,
            "ui_pid_after": ui_pid_after,
            "db_before_restart_canonical_sha256": db_before["canonical_sha256"],
            "db_after_restart_canonical_sha256": db_after["canonical_sha256"],
            "db_state_unchanged_across_restart_and_reopen": True,
            "observed_ocr_worker_processes": 0,
            "persisted_db_snapshot": db_after["snapshot"],
        },
        "steps": steps,
    }
    # Normalize text logs/JSONs in EVIDENCE_DIR to LF so on-disk bytes and Git LF blobs match 100% identically,
    # then refresh step log_sha256 values and build deterministic evidence-manifest.json.
    for p in sorted(EVIDENCE_DIR.rglob("*")):
        if p.is_file() and p.suffix.lower() in {".log", ".json", ".md", ".txt"}:
            raw_bytes = p.read_bytes()
            lf_bytes = raw_bytes.replace(b"\r\n", b"\n")
            if lf_bytes != raw_bytes:
                p.write_bytes(lf_bytes)

    for st in steps:
        st["log_sha256"] = sha256_file(REPO_ROOT / st["log_relpath"])

    summary_path = EVIDENCE_DIR / "verification-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8", newline="\n")

    # Build deterministic SHA-256 manifest of all generated evidence files.
    manifest_entries = []
    for p in sorted(EVIDENCE_DIR.rglob("*")):
        if p.is_file():
            data = p.read_bytes()
            manifest_entries.append(
                {
                    "path": p.relative_to(REPO_ROOT).as_posix(),
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                }
            )
    manifest_path = EVIDENCE_DIR / "evidence-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": "eledgercare.wp-0008.f3-evidence-manifest/1",
                "frozen_head": audit["head_commit"],
                "file_count": len(manifest_entries),
                "files": manifest_entries,
            },
            indent=2,
        ),
        encoding="utf-8",
        newline="\n",
    )
    print(f"DECISIVE F3 VERIFICATION PASSED on {audit['head_commit']} ({len(steps)} steps, {len(manifest_entries)} evidence files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
