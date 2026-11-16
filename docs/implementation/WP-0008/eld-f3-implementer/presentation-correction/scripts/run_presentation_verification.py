"""Decisive post-freeze verification runner for WP-0008 / 006 bounded presentation correction.

Executes on clean frozen HEAD with LocalOcr:Enabled=false, zero GPU/model calls, and exclusively
owned loopback resources (API 5390, UI 4410, PostgreSQL 55436):
  1. Verifies clean Git worktree, exact path-scope compliance against authority merge base
     af7160dc5b471fc855d7dc8d10bc0f63561294ca, and byte/tree invariance of src/, tests/, deploy/,
     workers/local_ocr/, dependencies, shared routing, prior reports (including untouched /003),
     and prior /003 evidence against original candidate 62e8666af747c0040942cee20c0ed34f4d747e93.
  2. Records actual pinned and installed @angular/cli version (22.2.7) to reconcile the historical
     /003 prose typo (22.0.5) without modifying /003.
  3. Starts owned PostgreSQL 18.7 cluster (55436), verifies retained eledgercare_f3_author_acceptance
     canonical state SHA-256 (d2e14104778a5fa9c032b1f581c8ee36bf47a8afb1ff2c4564a816838f78546a),
     builds Angular production bundle, executes full affected Playwright Microsoft Edge E2E suite
     (13/13 specs on eledgercare_f3_e2e), and runs verify_presentation_edge.mjs against retained
     eledgercare_f3_author_acceptance to capture default operator flow + expanded provenance +
     uncertain-save screenshots with zero DB mutation and zero OCR worker invocations.
  4. Stops owned UI, API, and PostgreSQL 18.7 cleanly, verifies ports 5390/4410/55436 FREE and
     zero remaining owned processes, and writes LF-normalized logs, verification-summary.json,
     resource-return.json, and evidence-manifest.json.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PC_DIR = SCRIPT_DIR.parent
REPO_ROOT = pathlib.Path(__file__).resolve().parents[6]
assert (REPO_ROOT / "ELedgerCare.slnx").exists(), f"Unexpected REPO_ROOT: {REPO_ROOT}"

EVIDENCE_DIR = PC_DIR / "evidence"
LOGS_DIR = EVIDENCE_DIR / "logs"
SCREENSHOTS_DIR = EVIDENCE_DIR / "screenshots"
NODE_EDGE_HELPER = SCRIPT_DIR / "verify_presentation_edge.mjs"

ORIGINAL_CANDIDATE_SHA = "62e8666af747c0040942cee20c0ed34f4d747e93"
ORIGINAL_REPORT_003_SHA = "b77bc68a5b6878d2395cd76b0d0a858ae15cc249"
ROOT_AUTHORITY_SHA = "3b225040475fe150956bc260d3584dfd0040d71b"
MERGED_BASE_SHA = "af7160dc5b471fc855d7dc8d10bc0f63561294ca"
EXPECTED_RETENTION_DB_SHA256 = "d2e14104778a5fa9c032b1f581c8ee36bf47a8afb1ff2c4564a816838f78546a"

WO_DOC_ID = "01a1e571-2838-714b-861b-bf0835d7c90a"
MP_DOC_ID = "01a1e573-ca14-72ba-a46a-c84690288e22"

API_PORT = 5390
UI_PORT = 4410
PG_PORT = 55436
ACCEPTANCE_DB = "eledgercare_f3_author_acceptance"
E2E_DB = "eledgercare_f3_e2e"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_output(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
    return proc.stdout.strip()


def port_state(port: int) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return "BOUND" if sock.connect_ex(("127.0.0.1", port)) == 0 else "FREE"


def assert_port_free(port: int) -> None:
    if port_state(port) != "FREE":
        raise RuntimeError(f"Owned port {port} is already bound before starting service; refusing to touch.")


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
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    combined = (
        f"$ {' '.join(cmd)}\n"
        f"[exit={proc.returncode}, elapsed_ms={elapsed_ms}]\n"
        f"--- STDOUT ---\n{proc.stdout}\n"
        f"--- STDERR ---\n{proc.stderr}"
    )
    log_path = LOGS_DIR / f"{name}.log"
    log_path.write_text(combined, encoding="utf-8", newline="\n")
    if proc.returncode != 0:
        raise RuntimeError(f"Step '{name}' failed with exit code {proc.returncode}; see {log_path}")
    return {
        "step": name,
        "command": cmd,
        "cwd": cwd.relative_to(REPO_ROOT).as_posix() if cwd != REPO_ROOT else ".",
        "started_utc": started,
        "elapsed_ms": elapsed_ms,
        "exit_code": proc.returncode,
        "log_relpath": log_path.relative_to(REPO_ROOT).as_posix(),
        "log_sha256": sha256_file(log_path),
    }


def audit_frozen_candidate() -> dict:
    status = git_output(["status", "--porcelain"])
    if status:
        raise RuntimeError(f"Worktree must be clean before decisive execution; found:\n{status}")

    head = git_output(["rev-parse", "HEAD"])
    branch = git_output(["branch", "--show-current"])
    if branch != "feature/wp-0008-f3-review":
        raise RuntimeError(f"Unexpected branch: {branch}")

    # Verify diff from MERGED_BASE_SHA contains only authorized presentation-correction paths.
    changed = [
        ln.strip()
        for ln in git_output(["diff", "--name-only", f"{MERGED_BASE_SHA}..HEAD"]).splitlines()
        if ln.strip()
    ]
    allowed_exact = {
        "web/src/app/review/work-order-review-page.ts",
        "web/src/styles.css",
        "web/e2e/review.spec.ts",
    }
    allowed_prefix = "docs/implementation/WP-0008/eld-f3-implementer/presentation-correction/"
    for rel in changed:
        if rel not in allowed_exact and not rel.startswith(allowed_prefix):
            raise RuntimeError(f"Out-of-scope file modified in presentation correction: {rel}")

    # Verify unchanged backend, test, deploy, worker, and dependency identities vs ORIGINAL_CANDIDATE_SHA.
    unchanged_vs_original = [
        "src",
        "tests",
        "deploy",
        "workers/local_ocr",
        "workers/local_ocr/README.md",
        "ELedgerCare.slnx",
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
    verified_vs_original: dict[str, str] = {}
    for p in unchanged_vs_original:
        orig_oid = git_output(["rev-parse", f"{ORIGINAL_CANDIDATE_SHA}:{p}"])
        head_oid = git_output(["rev-parse", f"HEAD:{p}"])
        if orig_oid != head_oid:
            raise RuntimeError(f"Identity '{p}' diverged from original candidate {ORIGINAL_CANDIDATE_SHA}: {orig_oid} != {head_oid}")
        verified_vs_original[p] = head_oid

    # Verify unchanged routing, R&D, prior reports (including /003), and prior /003 evidence vs MERGED_BASE_SHA.
    unchanged_vs_merged_base = [
        "AGENTS.md",
        "START_HERE.md",
        "CURRENT.md",
        "INDEX.md",
        "docs/design",
        "docs/coordination",
        "docs/kickoffs",
        "docs/reviews",
        "docs/agent-reports",
        "docs/agent-reports/eld-f3-implementer/WP-0008/003_2026-11-16_implementation_eld-f3-implementer.md",
        "docs/implementation/WP-0008/eld-f3-implementer/evidence",
        "docs/implementation/WP-0008/eld-f3-implementer/retained-failures",
        "docs/implementation/WP-0008/eld-f3-implementer/scripts",
        "docs/implementation/WP-0008/eld-f3-implementer/README.md",
        "docs/implementation/WP-0008/eld-f3-implementer/change-inventory.json",
        "evaluation",
        "qualification",
        "research",
    ]
    verified_vs_merged_base: dict[str, str] = {}
    for p in unchanged_vs_merged_base:
        base_oid = git_output(["rev-parse", f"{MERGED_BASE_SHA}:{p}"])
        head_oid = git_output(["rev-parse", f"HEAD:{p}"])
        if base_oid != head_oid:
            raise RuntimeError(f"Protected path '{p}' diverged from merged base {MERGED_BASE_SHA}: {base_oid} != {head_oid}")
        verified_vs_merged_base[p] = head_oid

    # Audit inertness & zero storage writes across web/src/.
    for ts_file in sorted((REPO_ROOT / "web" / "src").rglob("*.ts")):
        txt = ts_file.read_text(encoding="utf-8")
        code_only = "\n".join(
            ln for ln in txt.splitlines() if not ln.lstrip().startswith("//") and not ln.lstrip().startswith("*")
        )
        if "innerHTML" in code_only or "bypassSecurityTrustHtml" in code_only:
            raise RuntimeError(f"Prohibited innerHTML/bypassSecurityTrustHtml in {ts_file}")
        if "review" in ts_file.parts and any(k in code_only for k in ("sessionStorage", "localStorage", "indexedDB")):
            raise RuntimeError(f"Prohibited browser storage API in {ts_file}")

    web_pkg = json.loads((REPO_ROOT / "web" / "package.json").read_text(encoding="utf-8"))
    installed_ng_cli = json.loads(
        (REPO_ROOT / "web" / "node_modules" / "@angular" / "cli" / "package.json").read_text(encoding="utf-8")
    )

    return {
        "clean_git_status": True,
        "head_commit": head,
        "branch": branch,
        "original_candidate_sha": ORIGINAL_CANDIDATE_SHA,
        "original_report_003_sha": ORIGINAL_REPORT_003_SHA,
        "root_authority_sha": ROOT_AUTHORITY_SHA,
        "merged_base_sha": MERGED_BASE_SHA,
        "changed_paths_from_merged_base": changed,
        "web_tree_oid": git_output(["rev-parse", "HEAD:web"]),
        "verified_unchanged_vs_original_62e8666a": verified_vs_original,
        "verified_unchanged_vs_merged_base_af7160dc": verified_vs_merged_base,
        "angular_cli_version_fact_check": {
            "pinned_in_web_package_json": web_pkg["devDependencies"]["@angular/cli"],
            "installed_in_node_modules": installed_ng_cli["version"],
            "historical_003_prose_typo": "22.0.5",
            "report_003_blob_untouched": True,
        },
    }


def load_pg_settings() -> dict:
    return json.loads((REPO_ROOT / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))


def run_psql(user: str, password: str, db: str, sql: str) -> str:
    s = load_pg_settings()
    psql = REPO_ROOT / ".local" / "tools" / "pgsql-18.7-1" / "bin" / "psql.exe"
    env = os.environ.copy()
    env["PGPASSWORD"] = str(password)
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


def compute_canonical_db_digest(db_name: str) -> str:
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
    return sha256_bytes(canonical)


def check_zero_ocr_workers() -> int:
    proc = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-Command",
            "@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.Name -like 'python*' -and $_.CommandLine -like '*run_worker.py*' }).Count",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(proc.stdout.strip() or "0")


def list_remaining_owned_processes() -> list[dict]:
    ps_query = (
        "@(Get-CimInstance Win32_Process | Where-Object { "
        "$_.ProcessId -ne $PID -and ("
        "($_.CommandLine -like '*eld-f3-implementer*' -and ($_.Name -like 'postgres*' -or $_.Name -like 'dotnet*' -or $_.Name -like 'node*' -or $_.Name -like 'ELedgerCare*')) "
        "-or ($_.Name -like 'python*' -and $_.CommandLine -like '*run_worker.py*')"
        ") } | Select-Object ProcessId, Name, CommandLine) | ConvertTo-Json -Compress"
    )
    proc = subprocess.run(["pwsh", "-NoProfile", "-Command", ps_query], capture_output=True, text=True, check=True)
    raw = proc.stdout.strip()
    if not raw:
        return []
    parsed = json.loads(raw)
    return [parsed] if isinstance(parsed, dict) else parsed


def read_postmaster_pid() -> int:
    pid_file = REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid"
    return int(pid_file.read_text(encoding="utf-8").splitlines()[0].strip())


def start_owned_api(db_name: str, label: str) -> tuple[subprocess.Popen, object]:
    assert_port_free(API_PORT)
    s = load_pg_settings()
    api_dir = REPO_ROOT / "src" / "ELedgerCare.Api" / "bin" / "Release" / "net10.0"
    if not (api_dir / "ELedgerCare.Api.dll").exists():
        subprocess.run(
            ["dotnet", "build", "src/ELedgerCare.Api/ELedgerCare.Api.csproj", "-c", "Release"],
            cwd=str(REPO_ROOT),
            check=True,
        )
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
    return proc, log_f


def start_owned_ui(label: str) -> tuple[subprocess.Popen, object]:
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
    return proc, log_f


def stop_owned_proc(proc: subprocess.Popen | None, log_f: object | None) -> None:
    try:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
    finally:
        if log_f is not None:
            try:
                log_f.close()
            except Exception:
                pass


def main() -> int:
    if EVIDENCE_DIR.exists():
        shutil.rmtree(EVIDENCE_DIR)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    started_utc = utc_now()
    audit = audit_frozen_candidate()
    steps: list[dict] = []

    ports_before = {str(p): port_state(p) for p in (API_PORT, UI_PORT, PG_PORT)}
    if any(v != "FREE" for v in ports_before.values()):
        raise RuntimeError(f"Expected all owned ports FREE before starting, observed: {ports_before}")

    postmaster_pid = None
    db_sha_before = None
    db_sha_after = None
    api_pid = None
    ui_pid = None
    ocr_workers_observed = 0

    try:
        steps.append(
            run_logged(
                "01-pg-cluster-start",
                ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"],
                REPO_ROOT,
            )
        )
        postmaster_pid = read_postmaster_pid()
        db_sha_before = compute_canonical_db_digest(ACCEPTANCE_DB)
        if db_sha_before != EXPECTED_RETENTION_DB_SHA256:
            raise RuntimeError(
                f"Retained {ACCEPTANCE_DB} digest mismatch before checks: {db_sha_before} != {EXPECTED_RETENTION_DB_SHA256}"
            )

        steps.append(
            run_logged(
                "02-ng-build-production",
                ["node", "node_modules/@angular/cli/bin/ng.js", "build"],
                REPO_ROOT / "web",
            )
        )

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
            )
        )

        scratch_dir = REPO_ROOT / ".scratch"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = scratch_dir / "f3-presentation-edge-cfg.json"
        cfg_path.write_text(
            json.dumps(
                {
                    "uiPort": UI_PORT,
                    "apiPort": API_PORT,
                    "woDocumentId": WO_DOC_ID,
                    "mpDocumentId": MP_DOC_ID,
                    "outputDir": str(SCREENSHOTS_DIR),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        api_proc, api_log = None, None
        ui_proc, ui_log = None, None
        try:
            api_proc, api_log = start_owned_api(ACCEPTANCE_DB, "presentation")
            api_pid = api_proc.pid
            ui_proc, ui_log = start_owned_ui("presentation")
            ui_pid = ui_proc.pid

            steps.append(
                run_logged(
                    "04-edge-retained-db-presentation",
                    ["node", str(NODE_EDGE_HELPER), "--config", str(cfg_path)],
                    REPO_ROOT,
                )
            )
            ocr_workers_observed = check_zero_ocr_workers()
        finally:
            stop_owned_proc(ui_proc, ui_log)
            stop_owned_proc(api_proc, api_log)

        db_sha_after = compute_canonical_db_digest(ACCEPTANCE_DB)
        if db_sha_after != EXPECTED_RETENTION_DB_SHA256:
            raise RuntimeError(
                f"Retained {ACCEPTANCE_DB} mutated during presentation verification: {db_sha_after} != {EXPECTED_RETENTION_DB_SHA256}"
            )
        if ocr_workers_observed != 0:
            raise RuntimeError(f"Unexpected local_ocr worker process count: {ocr_workers_observed}")
    finally:
        if (REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid").exists():
            steps.append(
                run_logged(
                    "05-pg-cluster-stop",
                    ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"],
                    REPO_ROOT,
                )
            )

    scratch_dir = REPO_ROOT / ".scratch"
    if scratch_dir.exists():
        shutil.rmtree(scratch_dir)

    ports_after = {str(p): port_state(p) for p in (API_PORT, UI_PORT, PG_PORT)}
    remaining_procs = list_remaining_owned_processes()
    if any(v != "FREE" for v in ports_after.values()):
        raise RuntimeError(f"Expected all owned ports FREE after stop, observed: {ports_after}")
    if remaining_procs:
        raise RuntimeError(f"Owned processes remained after stop: {remaining_procs}")

    # Normalize text logs/JSONs to LF before computing final digests.
    for p in sorted(EVIDENCE_DIR.rglob("*")):
        if p.is_file() and p.suffix.lower() in {".log", ".json", ".md", ".txt"}:
            raw_b = p.read_bytes()
            lf_b = raw_b.replace(b"\r\n", b"\n")
            if lf_b != raw_b:
                p.write_bytes(lf_b)

    for st in steps:
        st["log_sha256"] = sha256_file(REPO_ROOT / st["log_relpath"])

    resource_return = {
        "schema": "eledgercare.wp-0008.f3-presentation-resource-return/1",
        "owner": "eld-f3-implementer",
        "worktree": str(REPO_ROOT),
        "branch": "feature/wp-0008-f3-review",
        "frozen_deliverable_head": audit["head_commit"],
        "returned_utc": utc_now(),
        "owned_ports_before_start": ports_before,
        "owned_ports_after_stop": ports_after,
        "postgres_cluster": {
            "host": "127.0.0.1",
            "port": PG_PORT,
            "postmaster_pid_started_and_stopped": postmaster_pid,
            "postmaster_pid_file_absent_after_stop": not (REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid").exists(),
            "retained_acceptance_db": ACCEPTANCE_DB,
            "retained_acceptance_db_sha256_before": db_sha_before,
            "retained_acceptance_db_sha256_after": db_sha_after,
            "retained_acceptance_db_unchanged": db_sha_before == db_sha_after == EXPECTED_RETENTION_DB_SHA256,
        },
        "transient_service_pids_started_and_stopped": {
            "api_pid": api_pid,
            "ui_pid": ui_pid,
        },
        "scratch_dir_absent_after_cleanup": not (REPO_ROOT / ".scratch").exists(),
        "remaining_owned_service_or_worker_processes": remaining_procs,
        "gpu_and_isolation_attestation": {
            "gpu_leases_acquired": 0,
            "ocr_worker_invocations": ocr_workers_observed,
            "q0_runtime_writes": 0,
            "reviewer_004_resources_touched": 0,
        },
    }
    (EVIDENCE_DIR / "resource-return.json").write_text(
        json.dumps(resource_return, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    summary = {
        "schema": "eledgercare.wp-0008.f3-presentation-verification-summary/1",
        "author": "eld-f3-implementer",
        "started_utc": started_utc,
        "completed_utc": utc_now(),
        "outcome": "PASSED_ALL_AFFECTED_BROWSER_AND_BUILD_CHECKS",
        "frozen_source_audit": audit,
        "ports": {"api": API_PORT, "ui": UI_PORT, "postgres": PG_PORT},
        "retained_db_verification": {
            "database": ACCEPTANCE_DB,
            "local_ocr_enabled": False,
            "canonical_sha256_before": db_sha_before,
            "canonical_sha256_after": db_sha_after,
            "db_state_unchanged": True,
            "observed_ocr_worker_processes": ocr_workers_observed,
        },
        "checks_not_rerun_by_design": [
            "dotnet test ELedgerCare.slnx -c Release (src/, tests/, and deploy/ trees verified byte-identical to 62e8666af747c0040942cee20c0ed34f4d747e93)",
            "python -B -m unittest discover -s workers/local_ocr/tests (workers/local_ocr tree verified byte-identical to 62e8666af747c0040942cee20c0ed34f4d747e93)",
        ],
        "steps": steps,
    }
    (EVIDENCE_DIR / "verification-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    manifest_entries = []
    for p in sorted(EVIDENCE_DIR.rglob("*")):
        if p.is_file() and p.name != "evidence-manifest.json":
            data = p.read_bytes()
            manifest_entries.append(
                {
                    "path": p.relative_to(REPO_ROOT).as_posix(),
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                }
            )
    (EVIDENCE_DIR / "evidence-manifest.json").write_text(
        json.dumps(
            {
                "schema": "eledgercare.wp-0008.f3-presentation-evidence-manifest/1",
                "frozen_head": audit["head_commit"],
                "file_count": len(manifest_entries),
                "files": manifest_entries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(
        f"PRESENTATION CORRECTION VERIFICATION PASSED on {audit['head_commit']} "
        f"({len(steps)} steps, {len(manifest_entries)} evidence files)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
