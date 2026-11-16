import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[6]
if not (REPO_ROOT / "ELedgerCare.slnx").is_file():
    raise RuntimeError(f"Resolved REPO_ROOT missing ELedgerCare.slnx: {REPO_ROOT}")

ACCEPTANCE_DIR = REPO_ROOT / "docs" / "reviews" / "WP-0008" / "eld-f3-reviewer" / "acceptance"
EVIDENCE_DIR = ACCEPTANCE_DIR / "evidence"
LOGS_DIR = EVIDENCE_DIR / "logs"
SCREENSHOTS_DIR = EVIDENCE_DIR / "screenshots"

API_PORT = 5490
UI_PORT = 4510
PG_PORT = 55437
SEED_DB = "eledgercare_f3_reviewer_seed_f2"
E2E_DB = "eledgercare_f3_rev_e2e"

AUTHOR_CANDIDATE_SHA = "62e8666af747c0040942cee20c0ed34f4d747e93"
AUTHOR_EVIDENCE_SHA = "724e3b601e40a7dd102d486043dec555d508b466"
AUTHOR_REPORT_003_SHA = "b77bc68a5b6878d2395cd76b0d0a858ae15cc249"
ROOT_AUTHORITY_SHA = "d38eca6b55b49a71f2bced304a486d9cf562487b"
DESIGN_CANDIDATE_SHA = "c5b5db3af96abf155c806082583b8a92c687f54d"
PRIOR_DESIGN_002_SHA = "bff139bcdf55df77a821b858513b7e6bf5d96b87"
PREPARATION_PUB_SHA = "9d99c3f42dda42ab691583f5b0c221b7be0bf5b6"

EXPECTED_PRE_MIGRATION_SEED_STATE_SHA256 = "77f301d929fd920d74cc2490dd47a7434a1ad386527ff84bec7804f11303ba81"
EXPECTED_WORKER_README_BLOB = "83ed6624f95c48bfbae4c466201774824f63ef5e"
EXPECTED_WORKER_README_SHA256 = "0b4d2604b95e90d083aeb5465690880550b99d6ae8c417769e25328244c22341"
EXPECTED_WORKER_SOURCE_SHA256 = "c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54"
EXPECTED_PACKAGE_LOCK_SHA256 = "93cc7b29d66ebfbe00437c886e57118bf455052def3e8acff08e7cb382ad0f53"

SEED1_DOC_ID = "01a1e571-2838-714b-861b-bf0835d7c90a"
SEED1_RES_ID = "01a1e573-a855-7735-96e1-f5d14cada602"
SEED1_PDF_SHA = "47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd"
SEED1_RAW_SHA = "7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95"

SEED2_DOC_ID = "01a1e573-ca14-72ba-a46a-c84690288e22"
SEED2_RES_ID = "01a1e578-8bfa-7bba-b104-ea8309dbfd9e"
SEED2_PDF_SHA = "15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3"
SEED2_RAW_SHA = "c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639"

SEED3_DOC_ID = "01a1e578-8f3a-7e0c-826b-a2c9dc066a8f"
SEED3_RES_ID = "01a1e57b-bfbd-7447-916c-92b386e5931d"

SEED4_DOC_ID = "01a1e580-0000-7000-8000-000000000001"
SEED4_PDF_SHA = "875a2d8c83c1c1002b38840f8136b60bd5ebcfe8d2df47187bf36454c59497cb"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_out(*args: str) -> str:
    cp = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    return cp.stdout.strip()


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
    """
    Checks strictly for processes referencing THIS reviewer worktree's workers/local_ocr path.
    Never queries GPU or inspects/touches concurrent WP-0009 or external Q0 processes.
    """
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


def invoke_psql(user: str, password: str, db: str, sql: str, *, expect_error: bool = False) -> subprocess.CompletedProcess[str]:
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
    if not expect_error and cp.returncode != 0:
        raise RuntimeError(f"psql failed on {db} as {user}: {cp.stderr.strip()}")
    return cp


def query_f2_seed_core_snapshot(db: str) -> dict:
    """
    Identical SQL projection used in preparation/helpers/prepare_and_verify_f2_seed.py
    so pre-migration state_sha256 equals 77f301d929fd920d74cc2490dd47a7434a1ad386527ff84bec7804f11303ba81
    and post-migration / post-restart F1+F2 tables remain 100% invariant.
    """
    s = load_pg_settings()
    snap_sql = """
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
    raw = invoke_psql(str(s["adminUser"]), str(s["adminPassword"]), db, snap_sql).stdout.strip()
    parsed = json.loads(raw)
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    f2_data_only = {
        "sequence": parsed["sequence"],
        "documents": parsed["documents"],
        "attempts": parsed["attempts"],
        "results": parsed["results"],
    }
    f2_data_sha = sha256_bytes(json.dumps(f2_data_only, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return {
        "snapshot": parsed,
        "state_sha256": sha256_bytes(canonical),
        "f1_f2_rows_and_seq_sha256": f2_data_sha,
    }


def compute_worker_source_digest() -> str:
    worker_root = REPO_ROOT / "workers" / "local_ocr"
    py_files = [
        worker_root / "run_worker.py",
        *sorted((worker_root / "local_ocr").glob("*.py"), key=lambda p: p.name),
    ]
    h = hashlib.sha256()
    for p in py_files:
        rel = p.relative_to(worker_root).as_posix()
        normalized = p.read_bytes().replace(b"\r\n", b"\n")
        file_sha = hashlib.sha256(normalized).hexdigest()
        h.update(f"{rel}:{len(normalized)}:{file_sha}\n".encode("utf-8"))
    return h.hexdigest()


def run_static_and_boundary_audit(frozen_head_sha: str) -> dict:
    # 1. Verify exact product/worker/deploy/test trees match author candidate 62e8666af747c0040942cee20c0ed34f4d747e93.
    tree_paths = ["src", "web", "tests", "deploy", "ELedgerCare.slnx", "workers"]
    tree_comparison: dict[str, dict[str, str | bool]] = {}
    for tp in tree_paths:
        head_oid = git_out("rev-parse", f"{frozen_head_sha}:{tp}")
        cand_oid = git_out("rev-parse", f"{AUTHOR_CANDIDATE_SHA}:{tp}")
        if head_oid != cand_oid:
            raise RuntimeError(f"Tree/blob mismatch on {tp}: HEAD={head_oid} vs author={cand_oid}")
        tree_comparison[tp] = {"oid": head_oid, "matches_author_candidate": True}

    # 2. Verify protected repository trees/blobs remained untouched relative to root authority / author report.
    protected_checks = {
        "AGENTS.md": git_out("rev-parse", f"{frozen_head_sha}:AGENTS.md") == git_out("rev-parse", f"{ROOT_AUTHORITY_SHA}:AGENTS.md"),
        "INDEX.md": git_out("rev-parse", f"{frozen_head_sha}:INDEX.md") == git_out("rev-parse", f"{ROOT_AUTHORITY_SHA}:INDEX.md"),
        "CURRENT.md": git_out("rev-parse", f"{frozen_head_sha}:CURRENT.md") == git_out("rev-parse", f"{ROOT_AUTHORITY_SHA}:CURRENT.md"),
        "docs/design/F3-review-correction.md": git_out("rev-parse", f"{frozen_head_sha}:docs/design/F3-review-correction.md")
        == git_out("rev-parse", f"{DESIGN_CANDIDATE_SHA}:docs/design/F3-review-correction.md"),
        "prior_002_report": git_out("rev-parse", f"{frozen_head_sha}:docs/agent-reports/eld-f3-reviewer/WP-0008/002_2026-11-16_review_eld-f3-reviewer.md")
        == git_out("rev-parse", f"{PRIOR_DESIGN_002_SHA}:docs/agent-reports/eld-f3-reviewer/WP-0008/002_2026-11-16_review_eld-f3-reviewer.md"),
        "author_003_report": git_out("rev-parse", f"{frozen_head_sha}:docs/agent-reports/eld-f3-implementer/WP-0008/003_2026-11-16_implementation_eld-f3-implementer.md")
        == git_out("rev-parse", f"{AUTHOR_REPORT_003_SHA}:docs/agent-reports/eld-f3-implementer/WP-0008/003_2026-11-16_implementation_eld-f3-implementer.md"),
        "reviewer_design_dir": git_out("rev-parse", f"{frozen_head_sha}:docs/reviews/WP-0008/eld-f3-reviewer/design")
        == git_out("rev-parse", f"{PRIOR_DESIGN_002_SHA}:docs/reviews/WP-0008/eld-f3-reviewer/design"),
        "reviewer_preparation_dir": git_out("rev-parse", f"{frozen_head_sha}:docs/reviews/WP-0008/eld-f3-reviewer/preparation")
        == git_out("rev-parse", f"{PREPARATION_PUB_SHA}:docs/reviews/WP-0008/eld-f3-reviewer/preparation"),
        "qualification_tree": git_out("rev-parse", f"{frozen_head_sha}:qualification") == git_out("rev-parse", f"{ROOT_AUTHORITY_SHA}:qualification"),
        "research_tree": git_out("rev-parse", f"{frozen_head_sha}:research") == git_out("rev-parse", f"{ROOT_AUTHORITY_SHA}:research"),
        "evaluation_tree": git_out("rev-parse", f"{frozen_head_sha}:evaluation") == git_out("rev-parse", f"{ROOT_AUTHORITY_SHA}:evaluation"),
        "worker_readme_blob": git_out("rev-parse", f"{frozen_head_sha}:workers/local_ocr/README.md") == EXPECTED_WORKER_README_BLOB,
    }
    if not all(protected_checks.values()):
        raise RuntimeError(f"Protected tree/blob verification failed: {protected_checks}")

    worker_digest = compute_worker_source_digest()
    if worker_digest != EXPECTED_WORKER_SOURCE_SHA256:
        raise RuntimeError(f"worker_source_sha256 changed: {worker_digest}")

    # 3. Scan product executable/source files (src/, web/src/, workers/*.py) for R&D imports, fake OCR, innerHTML, bypassSecurity, and browser storage.
    forbidden_rd = re.compile(r"(qualification[/\\]|research[/\\]|evaluation[/\\]|ELedgerCare\.(Qualification|Research|Evaluation))", re.IGNORECASE)
    rd_violations: list[str] = []
    for folder in (REPO_ROOT / "src", REPO_ROOT / "web" / "src", REPO_ROOT / "workers"):
        for p in folder.rglob("*"):
            if p.is_file() and p.suffix in {".cs", ".csproj", ".ts", ".html", ".py"}:
                if "bin" in p.parts or "obj" in p.parts or "dist" in p.parts:
                    continue
                txt = p.read_text(encoding="utf-8")
                if forbidden_rd.search(txt):
                    rd_violations.append(str(p.relative_to(REPO_ROOT)))
    if rd_violations:
        raise RuntimeError(f"Forbidden R&D reference in product code: {rd_violations}")

    def strip_ts_comments(source: str) -> str:
        without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
        return re.sub(r"(?m)^\s*//.*$", "", without_block)

    html_sink_violations: list[str] = []
    resource_url_files: list[str] = []
    storage_violations: list[str] = []
    storage_re = re.compile(r"\b(localStorage|sessionStorage|indexedDB)\s*\.")
    for p in (REPO_ROOT / "web" / "src").rglob("*"):
        if p.is_file() and p.suffix in {".ts", ".html"}:
            rel = str(p.relative_to(REPO_ROOT)).replace("\\", "/")
            code = strip_ts_comments(p.read_text(encoding="utf-8"))
            if "[innerHTML]" in code or "bypassSecurityTrustHtml" in code:
                html_sink_violations.append(rel)
            if "bypassSecurityTrustResourceUrl" in code:
                resource_url_files.append(rel)
            if "/review/" in rel and storage_re.search(code):
                storage_violations.append(rel)

    if html_sink_violations:
        raise RuntimeError(f"Forbidden HTML sink found: {html_sink_violations}")
    if resource_url_files != ["web/src/app/review/pdf-preview-url.ts"]:
        raise RuntimeError(f"Unexpected bypassSecurityTrustResourceUrl usage: {resource_url_files}")
    if storage_violations:
        raise RuntimeError(f"Browser storage API referenced in review UI: {storage_violations}")

    # 4. Reconcile Angular CLI documentation discrepancy (Kickoff L19).
    pkg_json = json.loads((REPO_ROOT / "web" / "package.json").read_text(encoding="utf-8"))
    lock_path = REPO_ROOT / "web" / "package-lock.json"
    lock_sha = sha256_file(lock_path)
    lock_json = json.loads(lock_path.read_text(encoding="utf-8"))
    installed_cli_json = json.loads((REPO_ROOT / "web" / "node_modules" / "@angular" / "cli" / "package.json").read_text(encoding="utf-8"))
    installed_core_json = json.loads((REPO_ROOT / "web" / "node_modules" / "@angular" / "core" / "package.json").read_text(encoding="utf-8"))
    report_003_txt = (REPO_ROOT / "docs" / "agent-reports" / "eld-f3-implementer" / "WP-0008" / "003_2026-11-16_implementation_eld-f3-implementer.md").read_text(encoding="utf-8")
    assert lock_sha == EXPECTED_PACKAGE_LOCK_SHA256
    assert installed_cli_json["version"] == "22.2.7"

    # 5. Audit author retained-failures (Kickoff L17: distinguish original logs from later author notes; verify Git blob LF vs Windows CRLF checkout).
    rf_smoke_rel = "docs/implementation/WP-0008/eld-f3-implementer/retained-failures/12645719-07-demo-smoke.log"
    rf_note_rel = "docs/implementation/WP-0008/eld-f3-implementer/retained-failures/c5c285d1-helper-self-match.txt"
    rf_smoke_git = subprocess.run(["git", "show", f"{frozen_head_sha}:{rf_smoke_rel}"], cwd=REPO_ROOT, capture_output=True, check=True).stdout
    rf_note_git = subprocess.run(["git", "show", f"{frozen_head_sha}:{rf_note_rel}"], cwd=REPO_ROOT, capture_output=True, check=True).stdout
    assert len(rf_smoke_git) == 745 and sha256_bytes(rf_smoke_git) == "74703d6732b4d2d7cc98dc1eb9e4a20089a10efc6760cf483840212041a826ca"
    assert len(rf_note_git) == 376 and sha256_bytes(rf_note_git) == "3617e7fd78fbf815abe98f80a41c3591da0341054a108d7d46b789ead361df07"

    # 6. Verify external Q0 directory untouched (read-only metadata check; zero GPU/process touch).
    q0_manifest = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005\manifests\model-source-manifest.json")
    q0_manifest_sha = sha256_file(q0_manifest) if q0_manifest.is_file() else None

    return {
        "frozen_head_sha": frozen_head_sha,
        "author_candidate_sha": AUTHOR_CANDIDATE_SHA,
        "product_trees": tree_comparison,
        "protected_checks": protected_checks,
        "worker_source_sha256": worker_digest,
        "zero_rd_imports": True,
        "zero_html_sinks": True,
        "scoped_resource_url_files": resource_url_files,
        "zero_review_storage_apis": True,
        "angular_cli_reconciliation": {
            "author_003_reported_text_contains_22_0_5": "Angular CLI `22.0.5`" in report_003_txt,
            "package_json_angular_cli": pkg_json["devDependencies"]["@angular/cli"],
            "package_json_angular_core": pkg_json["dependencies"]["@angular/core"],
            "package_lock_sha256": lock_sha,
            "package_lock_angular_cli": lock_json["packages"]["node_modules/@angular/cli"]["version"],
            "installed_node_modules_angular_cli": installed_cli_json["version"],
            "installed_node_modules_angular_core": installed_core_json["version"],
            "execution_consequence": "none_report_prose_typo_only_lockfile_unchanged",
        },
        "retained_failures_classification": {
            "12645719-07-demo-smoke.log": {
                "git_blob_bytes": len(rf_smoke_git),
                "git_blob_sha256": sha256_bytes(rf_smoke_git),
                "artifact_kind": "exact_original_inner_step_log_no_separate_outer_wrapper_log",
            },
            "c5c285d1-helper-self-match.txt": {
                "git_blob_bytes": len(rf_note_git),
                "git_blob_sha256": sha256_bytes(rf_note_git),
                "artifact_kind": "later_structured_author_summary_note_not_raw_wrapper_output",
            },
        },
        "external_q0_manifest_sha256_untouched": q0_manifest_sha,
    }


def verify_least_privilege_and_fks(db: str) -> dict:
    s = load_pg_settings()
    priv_sql = """
SELECT json_build_object(
  'tables', (
    SELECT json_agg(json_build_object(
      'table', c.relname,
      'select', has_table_privilege('eledgercare_app', c.oid, 'SELECT'),
      'insert', has_table_privilege('eledgercare_app', c.oid, 'INSERT'),
      'table_update', has_table_privilege('eledgercare_app', c.oid, 'UPDATE'),
      'any_col_update', has_any_column_privilege('eledgercare_app', c.oid, 'UPDATE'),
      'delete', has_table_privilege('eledgercare_app', c.oid, 'DELETE'),
      'truncate', has_table_privilege('eledgercare_app', c.oid, 'TRUNCATE')
    ) ORDER BY c.relname)
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'eledgercare' AND c.relkind = 'r' AND c.relname <> '__ef_migrations_history'
  ),
  'head_updatable_columns', (
    SELECT json_agg(a.attname ORDER BY a.attname)
    FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'eledgercare' AND c.relname = 'work_order_review_heads'
      AND a.attnum > 0 AND NOT a.attisdropped
      AND has_column_privilege('eledgercare_app', c.oid, a.attnum, 'UPDATE')
  ),
  'restrict_fk_count', (
    SELECT count(*) FROM pg_constraint con
    JOIN pg_namespace n ON n.oid = con.connamespace
    WHERE n.nspname = 'eledgercare' AND con.contype = 'f' AND con.confdeltype = 'r'
  ),
  'total_fk_count', (
    SELECT count(*) FROM pg_constraint con
    JOIN pg_namespace n ON n.oid = con.connamespace
    WHERE n.nspname = 'eledgercare' AND con.contype = 'f'
  )
)::text;
"""
    matrix = json.loads(invoke_psql(str(s["adminUser"]), str(s["adminPassword"]), db, priv_sql).stdout.strip())
    if matrix["head_updatable_columns"] != ["current_revision_id", "current_revision_number", "current_status", "updated_at"]:
        raise RuntimeError(f"Unexpected updatable columns on work_order_review_heads: {matrix['head_updatable_columns']}")
    if matrix["restrict_fk_count"] != 15 or matrix["total_fk_count"] != 15:
        raise RuntimeError(f"Expected 15 Restrict FKs, got {matrix}")

    denied_statements = [
        "UPDATE eledgercare.work_order_review_revisions SET status = 'reviewed'",
        "DELETE FROM eledgercare.work_order_review_revisions",
        "TRUNCATE eledgercare.work_order_review_revisions",
        "UPDATE eledgercare.work_order_review_fields SET human_value = 'tamper'",
        "DELETE FROM eledgercare.work_order_review_fields",
        "DELETE FROM eledgercare.work_order_review_heads",
        "UPDATE eledgercare.work_order_review_heads SET document_id = document_id",
        "UPDATE eledgercare.work_order_review_heads SET result_id = result_id",
        "UPDATE eledgercare.work_order_review_heads SET input_sha256 = input_sha256",
        "UPDATE eledgercare.work_order_review_heads SET raw_output_sha256 = raw_output_sha256",
        "UPDATE eledgercare.work_order_review_heads SET profile_id = profile_id",
        "UPDATE eledgercare.work_order_review_heads SET field_schema_version = field_schema_version",
        "UPDATE eledgercare.work_order_review_heads SET suggestion_policy_version = suggestion_policy_version",
        "UPDATE eledgercare.work_order_review_heads SET machine_snapshot_json = machine_snapshot_json",
        "UPDATE eledgercare.work_order_review_heads SET created_at = created_at",
        "UPDATE eledgercare.extraction_results SET raw_output_bytes = raw_output_bytes",
        "UPDATE eledgercare.original_artifacts SET bytes = bytes",
    ]
    for stmt in denied_statements:
        cp = invoke_psql(str(s["appUser"]), str(s["appPassword"]), db, f"{stmt};", expect_error=True)
        if cp.returncode == 0 or "permission denied" not in cp.stderr.lower():
            raise RuntimeError(f"Expected 42501 permission denied for '{stmt}', got rc={cp.returncode}, err={cp.stderr}")

    matrix["denied_app_probes_verified"] = len(denied_statements)
    return matrix


def wait_http_ready(url: str, timeout_s: float) -> None:
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
    conn = f"Host={s['host']};Port={s['port']};Database={db_name};Username={s['appUser']};Password={s['appPassword']}"
    env = os.environ.copy()
    env["ASPNETCORE_ENVIRONMENT"] = "Production"
    env["ConnectionStrings__Runtime"] = conn
    env["Api__Port"] = str(API_PORT)
    env["LocalOcr__Enabled"] = "false"
    env["DOTNET_NOLOGO"] = "1"
    log_f = open(LOGS_DIR / f"reviewer-api-{label}.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        ["dotnet", str(api_dir / "ELedgerCare.Api.dll")],
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
            raise RuntimeError(f"PID {proc.pid} startUtc changed ({current_ident['startUtc']} vs {recorded_ident['startUtc']}); refusing to terminate recycled PID!")
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


def http_request(
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    raw_body: bytes | None = None,
) -> tuple[int, dict[str, str], bytes]:
    url = f"http://127.0.0.1:{API_PORT}{path}"
    req = urllib.request.Request(url, data=raw_body, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=25.0) as resp:
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, resp_headers, resp.read()
    except urllib.error.HTTPError as err:
        err_headers = {k.lower(): v for k, v in err.headers.items()} if err.headers else {}
        return err.code, err_headers, err.read()


def make_review_payload(
    result_id: str,
    expected_rev: int,
    status: str,
    fields: list[dict],
    operator_label: str | None = None,
    profile_id: str = "maintenance-work-order/1",
) -> bytes:
    return json.dumps(
        {
            "profileId": profile_id,
            "resultId": result_id,
            "expectedRevision": expected_rev,
            "status": status,
            "operatorDisplayLabel": operator_label,
            "fields": fields,
        }
    ).encode("utf-8")


def default_seed3_fields(wo_value: str) -> list[dict]:
    return [
        {"fieldKey": "work_order_id", "decision": "edited", "value": wo_value, "unknownReason": None, "consultedSource": None},
        {"fieldKey": "property_name", "decision": "accepted", "value": "Cedar Hollow Apartments", "unknownReason": None, "consultedSource": None},
        {"fieldKey": "building_unit", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
        {"fieldKey": "requested_date", "decision": "accepted", "value": "2026-10-16", "unknownReason": None, "consultedSource": None},
        {"fieldKey": "issue_and_resolution", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
    ]


def run_direct_api_and_concurrency_probes_on_seed_db() -> dict:
    s = load_pg_settings()

    # 1. Pure-read GET /review on Seed 1 & Seed 2 creates zero rows; Seed 4 (awaiting_extraction) returns 409.
    st1, _, b1 = http_request("GET", f"/api/documents/{SEED1_DOC_ID}/review")
    assert st1 == 200
    j1 = json.loads(b1.decode("utf-8"))
    assert j1["currentRevisionNumber"] == 0 and j1["reviewState"] == "unreviewed"
    assert [f["machineCandidate"]["value"] for f in j1["fields"][:4]] == [
        "WO-004192",
        "Cedar Hollow Apartments",
        "Bldg B - Unit 204",
        "2026-10-16",
    ]
    assert len(j1["fields"][4]["machineCandidate"]["value"]) == 298

    st2, _, b2 = http_request("GET", f"/api/documents/{SEED2_DOC_ID}/review")
    assert st2 == 200
    j2 = json.loads(b2.decode("utf-8"))
    assert all(f["machineCandidate"]["status"] == "missing" and f["decision"] == "unreviewed" for f in j2["fields"])

    st4, _, b4 = http_request("GET", f"/api/documents/{SEED4_DOC_ID}/review")
    assert st4 == 409 and json.loads(b4.decode("utf-8"))["code"] == "extraction_not_completed"

    row_counts_after_pure_get = invoke_psql(
        str(s["appUser"]),
        str(s["appPassword"]),
        SEED_DB,
        "SELECT (SELECT count(*) FROM eledgercare.work_order_review_heads) || ',' || (SELECT count(*) FROM eledgercare.work_order_review_revisions);",
    ).stdout.strip()
    assert row_counts_after_pure_get == "0,0", f"Pure GET wrote rows: {row_counts_after_pure_get}"

    # 2. Inline /preview headers + Range 206 + /original attachment on Seed 1.
    p_st, p_hdrs, p_bytes = http_request("GET", f"/api/documents/{SEED1_DOC_ID}/preview")
    assert p_st == 200 and len(p_bytes) == 372258 and sha256_bytes(p_bytes) == SEED1_PDF_SHA
    assert "inline" in p_hdrs.get("content-disposition", "")
    assert p_hdrs.get("x-content-type-options") == "nosniff"
    assert p_hdrs.get("x-frame-options") == "SAMEORIGIN"
    assert p_hdrs.get("content-security-policy") == "frame-ancestors 'self'"

    r_st, _, r_bytes = http_request("GET", f"/api/documents/{SEED1_DOC_ID}/preview", headers={"Range": "bytes=0-63"})
    assert r_st == 206 and r_bytes == p_bytes[:64]

    o_st, o_hdrs, o_bytes = http_request("GET", f"/api/documents/{SEED1_DOC_ID}/original")
    assert o_st == 200 and o_bytes == p_bytes and "attachment" in o_hdrs.get("content-disposition", "")

    # 3. Strict payload/Unicode/UTF-16/provenance boundary rejections on Seed 1 & Seed 2 (creating 0 rows on Seed 1 & Seed 2).
    #    Includes astral UTF-16 pair straddling 64 code units: 63 'A' + U+1F527 (2 UTF-16 code units) = 65 UTF-16 code units!
    astral_65_utf16 = ("A" * 63) + "\U0001F527"
    assert len(astral_65_utf16.encode("utf-16-le")) // 2 == 65

    oversized_body = b'{"pad":"' + (b"X" * 33000) + b'"}'
    st_413, _, b_413 = http_request(
        "POST",
        f"/api/documents/{SEED1_DOC_ID}/review/revisions",
        headers={"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())},
        raw_body=oversized_body,
    )
    assert st_413 == 413 and json.loads(b_413.decode("utf-8"))["code"] == "review_request_too_large"

    st_astral, _, b_astral = http_request(
        "POST",
        f"/api/documents/{SEED1_DOC_ID}/review/revisions",
        headers={"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())},
        raw_body=make_review_payload(SEED1_RES_ID, 0, "draft", default_seed3_fields(astral_65_utf16)),
    )
    assert st_astral == 422 and json.loads(b_astral.decode("utf-8"))["code"] == "invalid_field_value"

    raw_surrogate = (
        f'{{"resultId":"{SEED1_RES_ID}","expectedRevision":0,"status":"draft","fields":['
        '{"fieldKey":"work_order_id","decision":"edited","value":"BAD\\uD800"},'
        '{"fieldKey":"property_name","decision":"unreviewed","value":null},'
        '{"fieldKey":"building_unit","decision":"unreviewed","value":null},'
        '{"fieldKey":"requested_date","decision":"unreviewed","value":null},'
        '{"fieldKey":"issue_and_resolution","decision":"unreviewed","value":null}]}}'
    ).encode("utf-8")
    st_sur, _, b_sur = http_request(
        "POST",
        f"/api/documents/{SEED1_DOC_ID}/review/revisions",
        headers={"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())},
        raw_body=raw_surrogate,
    )
    assert st_sur == 422 and json.loads(b_sur.decode("utf-8"))["code"] == "invalid_field_value"

    raw_prov_forbid = (
        f'{{"resultId":"{SEED1_RES_ID}","expectedRevision":0,"status":"draft","sourceQuote":"invented","fields":[]}}'
    ).encode("utf-8")
    st_prov, _, b_prov = http_request(
        "POST",
        f"/api/documents/{SEED1_DOC_ID}/review/revisions",
        headers={"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())},
        raw_body=raw_prov_forbid,
    )
    assert st_prov == 400 and json.loads(b_prov.decode("utf-8"))["code"] == "client_provenance_forbidden"

    assert (
        invoke_psql(
            str(s["appUser"]),
            str(s["appPassword"]),
            SEED_DB,
            "SELECT count(*) FROM eledgercare.work_order_review_revisions;",
        ).stdout.strip()
        == "0"
    )

    # 4. Concurrent races, replay-after-later-save, changed-body conflict, and 128-revision cap on Seed 3
    #    (leaving Seed 1 & Seed 2 completely untouched at Rev 0 for Microsoft Edge UI acceptance!).
    barrier0 = threading.Barrier(2)
    competing_keys = [str(uuid.uuid4()), str(uuid.uuid4())]

    def race_rev0(idx: int) -> tuple[int, dict, str]:
        barrier0.wait(timeout=10.0)
        st, _, body = http_request(
            "POST",
            f"/api/documents/{SEED3_DOC_ID}/review/revisions",
            headers={"Content-Type": "application/json", "Idempotency-Key": competing_keys[idx]},
            raw_body=make_review_payload(SEED3_RES_ID, 0, "draft", default_seed3_fields(f"WO-RACE-{idx}"), f"Race-{idx}"),
        )
        return st, json.loads(body.decode("utf-8")), competing_keys[idx]

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        r0_results = list(pool.map(race_rev0, [0, 1]))
    assert sorted(r[0] for r in r0_results) == [201, 409], f"Expected [201, 409] on competing rev0 race, got {[r[0] for r in r0_results]}"
    winner0 = next(r for r in r0_results if r[0] == 201)
    loser0 = next(r for r in r0_results if r[0] == 409)
    assert loser0[1]["code"] == "stale_expected_revision" and loser0[1]["currentRevisionNumber"] == 1
    op1_key = winner0[2]
    op1_wo_val = winner0[1]["fields"][0]["value"]
    op1_label = winner0[1]["revision"]["operatorDisplayLabel"]

    # Concurrent SAME-key duplicate race at expectedRevision = 1 -> [200, 201] or [201, 200] with identical revisionId!
    barrier1 = threading.Barrier(2)
    shared_key_rev2 = str(uuid.uuid4())

    def same_key_rev1(_: int) -> tuple[int, dict]:
        barrier1.wait(timeout=10.0)
        st, _, body = http_request(
            "POST",
            f"/api/documents/{SEED3_DOC_ID}/review/revisions",
            headers={"Content-Type": "application/json", "Idempotency-Key": shared_key_rev2},
            raw_body=make_review_payload(SEED3_RES_ID, 1, "draft", default_seed3_fields("WO-REV-2"), "DupRace"),
        )
        return st, json.loads(body.decode("utf-8"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        r1_results = list(pool.map(same_key_rev1, [0, 1]))
    assert sorted(r[0] for r in r1_results) == [200, 201], f"Expected [200, 201] on same-key race, got {[r[0] for r in r1_results]}"
    assert r1_results[0][1]["revision"]["revisionId"] == r1_results[1][1]["revision"]["revisionId"]

    # Replay op1_key (expectedRevision=0) AFTER Revision #2 committed -> 200 OK (isCurrentHead=false, currentRevisionNumber=2).
    st_rep1, _, b_rep1 = http_request(
        "POST",
        f"/api/documents/{SEED3_DOC_ID}/review/revisions",
        headers={"Content-Type": "application/json", "Idempotency-Key": op1_key},
        raw_body=make_review_payload(SEED3_RES_ID, 0, "draft", default_seed3_fields(op1_wo_val), op1_label),
    )
    j_rep1 = json.loads(b_rep1.decode("utf-8"))
    assert st_rep1 == 200 and j_rep1["replayed"] is True and j_rep1["isCurrentHead"] is False
    assert j_rep1["revision"]["revisionNumber"] == 1 and j_rep1["currentRevisionNumber"] == 2

    # Same key op1_key with mutated value -> 409 idempotency_key_conflict!
    st_mut, _, b_mut = http_request(
        "POST",
        f"/api/documents/{SEED3_DOC_ID}/review/revisions",
        headers={"Content-Type": "application/json", "Idempotency-Key": op1_key},
        raw_body=make_review_payload(SEED3_RES_ID, 0, "draft", default_seed3_fields("MUTATED-VALUE"), op1_label),
    )
    assert st_mut == 409 and json.loads(b_mut.decode("utf-8"))["code"] == "idempotency_key_conflict"

    # Advance Seed 3 from Revision #3 through #128, verify #129 -> 409 revision_limit_reached, and replay #128 -> 200 OK!
    key_128 = ""
    for expected_rev in range(2, 128):
        rev_num = expected_rev + 1
        k = str(uuid.uuid4())
        if rev_num == 128:
            key_128 = k
        st_n, _, _ = http_request(
            "POST",
            f"/api/documents/{SEED3_DOC_ID}/review/revisions",
            headers={"Content-Type": "application/json", "Idempotency-Key": k},
            raw_body=make_review_payload(SEED3_RES_ID, expected_rev, "draft", default_seed3_fields(f"WO-CAP-{rev_num}"), f"Cap-{rev_num}"),
        )
        assert st_n == 201, f"Expected 201 at rev {rev_num}, got {st_n}"

    st_129, _, b_129 = http_request(
        "POST",
        f"/api/documents/{SEED3_DOC_ID}/review/revisions",
        headers={"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())},
        raw_body=make_review_payload(SEED3_RES_ID, 128, "draft", default_seed3_fields("WO-CAP-129"), "Cap-129"),
    )
    assert st_129 == 409 and json.loads(b_129.decode("utf-8"))["code"] == "revision_limit_reached"

    st_r128, _, b_r128 = http_request(
        "POST",
        f"/api/documents/{SEED3_DOC_ID}/review/revisions",
        headers={"Content-Type": "application/json", "Idempotency-Key": key_128},
        raw_body=make_review_payload(SEED3_RES_ID, 127, "draft", default_seed3_fields("WO-CAP-128"), "Cap-128"),
    )
    j_r128 = json.loads(b_r128.decode("utf-8"))
    assert st_r128 == 200 and j_r128["replayed"] is True and j_r128["revision"]["revisionNumber"] == 128 and j_r128["canSaveRevision"] is False

    return {
        "pure_get_zero_rows_verified": True,
        "seed4_non_completed_409_verified": True,
        "preview_inline_and_range_206_verified": True,
        "oversized_32kib_413_verified": True,
        "astral_utf16_65_code_units_422_verified": True,
        "unpaired_surrogate_422_verified": True,
        "client_provenance_400_verified": True,
        "seed3_competing_rev0_statuses": sorted(r[0] for r in r0_results),
        "seed3_same_key_rev1_statuses": sorted(r[0] for r in r1_results),
        "seed3_replay_op1_after_rev2": {"status": st_rep1, "isCurrentHead": False, "currentRevisionNumber": 2},
        "seed3_mutated_key_conflict_status": st_mut,
        "seed3_cap_129_status": st_129,
        "seed3_replay_128_at_cap_status": st_r128,
    }


def main() -> int:
    # Step 0: Assert completely clean git status BEFORE creating acceptance/evidence outputs.
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

    try:
        # 1. Static & boundary audit.
        static_audit = run_static_and_boundary_audit(frozen_head_sha)
        initial_ports = query_port_listeners([API_PORT, UI_PORT, PG_PORT])
        if any(initial_ports.values()):
            raise RuntimeError(f"Reviewer ports must be unbound at start, got {initial_ports}")

        pg_ctl = REPO_ROOT / ".local" / "tools" / "pgsql-18.7-1" / "bin" / "pg_ctl.exe"
        pg_data = REPO_ROOT / ".local" / "postgres-data"
        pre_pg_status = subprocess.run([str(pg_ctl), "status", "-D", str(pg_data)], capture_output=True, text=True)
        if pre_pg_status.returncode != 3:
            raise RuntimeError(f"Expected stopped reviewer PG cluster (rc=3) at start, got rc={pre_pg_status.returncode}")

        # 2. Worker CPU regression + offline locked .NET build + Angular production build.
        steps.append(run_logged("01-worker-cpu-tests", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "workers/local_ocr/tests", "-v"], REPO_ROOT, settings))
        steps.append(run_logged("02-dotnet-restore-offline-locked", ["dotnet", "restore", "ELedgerCare.slnx", "--locked-mode", "--configfile", ".local/nuget/offline.nuget.config"], REPO_ROOT, settings))
        steps.append(run_logged("03-dotnet-build-release", ["dotnet", "build", "ELedgerCare.slnx", "-c", "Release", "--no-restore"], REPO_ROOT, settings))
        steps.append(run_logged("04-ng-build-production", ["node", "node_modules/@angular/cli/bin/ng.js", "build"], REPO_ROOT / "web", settings))

        # Verify builds left zero dirty files outside acceptance/evidence.
        post_build_dirty = [
            ln for ln in git_out("status", "--porcelain").splitlines()
            if "docs/reviews/WP-0008/eld-f3-reviewer/acceptance/evidence" not in ln
        ]
        if post_build_dirty:
            raise RuntimeError(f"Build mutated files outside acceptance/evidence: {post_build_dirty}")

        # 3. Start reviewer PG 55437 and verify PRE-MIGRATION eledgercare_f3_reviewer_seed_f2 state SHA-256!
        steps.append(run_logged("05-pg-start-initial", ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"], REPO_ROOT, settings))
        pm_pid_initial = int((pg_data / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        pm_ident_initial = get_process_identity(pm_pid_initial)
        service_ledger.append({"service": "postgresql-55437-initial", "identity": pm_ident_initial})

        pre_mig_seed = query_f2_seed_core_snapshot(SEED_DB)
        if pre_mig_seed["state_sha256"] != EXPECTED_PRE_MIGRATION_SEED_STATE_SHA256:
            raise RuntimeError(
                f"Pre-migration {SEED_DB} state_sha256 mismatch: got {pre_mig_seed['state_sha256']}, "
                f"expected {EXPECTED_PRE_MIGRATION_SEED_STATE_SHA256}"
            )

        # 4. Apply F3 forward migration (20261116200918_AddWorkOrderReview) + grant-runtime.sql to eledgercare_f3_reviewer_seed_f2,
        #    and prepare eledgercare_product_dev for demo smoke.
        steps.append(run_logged("06-migrate-reviewer-f2-seed-db", ["pwsh", "-NoProfile", "-File", "deploy/dev/database/prepare-database.ps1", "-Database", SEED_DB], REPO_ROOT, settings))
        steps.append(run_logged("07-prepare-reviewer-dev-db", ["pwsh", "-NoProfile", "-File", "deploy/dev/database/prepare-database.ps1"], REPO_ROOT, settings))

        post_mig_seed = query_f2_seed_core_snapshot(SEED_DB)
        expected_migrations = [
            "20261114182147_InitialDurableIntake",
            "20261116052029_AddLocalExtraction",
            "20261116200918_AddWorkOrderReview",
        ]
        if post_mig_seed["snapshot"]["migrations"] != expected_migrations:
            raise RuntimeError(f"Unexpected post-migration history: {post_mig_seed['snapshot']['migrations']}")
        if post_mig_seed["f1_f2_rows_and_seq_sha256"] != pre_mig_seed["f1_f2_rows_and_seq_sha256"]:
            raise RuntimeError("Forward F3 migration altered pre-existing F1/F2 rows or extraction_fencing_seq!")

        priv_audit = verify_least_privilege_and_fks(SEED_DB)

        # 5. Run full .NET test suite (85 tests: Domain + Infrastructure + real-PG Acceptance) + demo smoke + Playwright Edge E2E on 5490/4510.
        steps.append(run_logged("08-dotnet-test-release", ["dotnet", "test", "ELedgerCare.slnx", "-c", "Release", "--no-build"], REPO_ROOT, settings))
        demo_receipt_path = EVIDENCE_DIR / "demo-smoke-reviewer-receipt.json"
        steps.append(
            run_logged(
                "09-demo-smoke-port-5490",
                ["pwsh", "-NoProfile", "-File", "deploy/dev/smoke/run-demo-smoke.ps1", "-ApiPort", str(API_PORT), "-ReceiptPath", str(demo_receipt_path)],
                REPO_ROOT,
                settings,
            )
        )
        steps.append(
            run_logged(
                "10-playwright-edge-e2e-5490-4510",
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
                settings,
            )
        )
        wait_port_free(API_PORT, timeout_s=20.0)
        wait_port_free(UI_PORT, timeout_s=20.0)

        # 6. Start reviewer API (5490, LocalOcr:Enabled=false) + UI (4510) against forward-migrated eledgercare_f3_reviewer_seed_f2!
        pm_pid_phase1 = int((pg_data / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        pm_ident_phase1 = get_process_identity(pm_pid_phase1)

        api_proc, api_log, api_ident = start_owned_api(SEED_DB, "phase1")
        ui_proc, ui_log, ui_ident = start_owned_ui("phase1")
        service_ledger.append({"service": "api-5490-phase1", "identity": api_ident})
        service_ledger.append({"service": "ui-4510-phase1", "identity": ui_ident})

        direct_probes = run_direct_api_and_concurrency_probes_on_seed_db()

        edge_before_receipt = EVIDENCE_DIR / "edge-reviewer-before-restart.json"
        edge_before_cfg = Path(REPO_ROOT / ".scratch" / "edge-before-cfg.json")
        edge_before_cfg.parent.mkdir(parents=True, exist_ok=True)
        edge_before_cfg.write_text(
            json.dumps(
                {
                    "uiPort": UI_PORT,
                    "screenshotsDir": str(SCREENSHOTS_DIR),
                    "receiptPath": str(edge_before_receipt),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        steps.append(
            run_logged(
                "11-edge-reviewer-before-restart",
                ["node", "docs/reviews/WP-0008/eld-f3-reviewer/acceptance/helpers/verify_f3_edge_reviewer.mjs", "--phase", "before-restart", "--config", str(edge_before_cfg)],
                REPO_ROOT,
                settings,
            )
        )

        # 7. Stop UI + API, perform full PostgreSQL 18.7 cluster stop + start on 55437 (new postmaster PID), and restart API (5490) + UI (4510) with LocalOcr:Enabled=false!
        ui_stop_1 = stop_owned_proc(ui_proc, ui_log, ui_ident)
        ui_proc = ui_log = ui_ident = None
        api_stop_1 = stop_owned_proc(api_proc, api_log, api_ident)
        api_proc = api_log = api_ident = None
        service_ledger.append({"service": "ui-4510-phase1-stop", "stop": ui_stop_1})
        service_ledger.append({"service": "api-5490-phase1-stop", "stop": api_stop_1})

        steps.append(run_logged("12-pg-cluster-stop-for-restart", ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"], REPO_ROOT, settings))
        steps.append(run_logged("13-pg-cluster-start-after-restart", ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"], REPO_ROOT, settings))

        pm_pid_phase2 = int((pg_data / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        pm_ident_phase2 = get_process_identity(pm_pid_phase2)
        if pm_pid_phase2 == pm_pid_phase1 and pm_ident_phase2["startUtc"] == pm_ident_phase1["startUtc"]:
            raise RuntimeError("PostgreSQL postmaster identity did not change across stop/start!")
        service_ledger.append({"service": "postgresql-55437-phase2", "identity": pm_ident_phase2})

        api_proc, api_log, api_ident = start_owned_api(SEED_DB, "phase2")
        ui_proc, ui_log, ui_ident = start_owned_ui("phase2")
        service_ledger.append({"service": "api-5490-phase2", "identity": api_ident})
        service_ledger.append({"service": "ui-4510-phase2", "identity": ui_ident})

        # 8. Reopen in fresh Microsoft Edge after PG + API restart and verify Seed 1 + Seed 3 + F1/F2 invariance!
        edge_after_receipt = EVIDENCE_DIR / "edge-reviewer-after-restart.json"
        edge_after_cfg = Path(REPO_ROOT / ".scratch" / "edge-after-cfg.json")
        edge_after_cfg.write_text(
            json.dumps(
                {
                    "uiPort": UI_PORT,
                    "screenshotsDir": str(SCREENSHOTS_DIR),
                    "beforeReceiptPath": str(edge_before_receipt),
                    "receiptPath": str(edge_after_receipt),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        steps.append(
            run_logged(
                "14-edge-reviewer-after-restart",
                ["node", "docs/reviews/WP-0008/eld-f3-reviewer/acceptance/helpers/verify_f3_edge_reviewer.mjs", "--phase", "after-restart", "--config", str(edge_after_cfg)],
                REPO_ROOT,
                settings,
            )
        )

        # Verify Seed 3's 128 revisions also survived PG + API restart intact!
        st_s3_after, _, b_s3_after = http_request("GET", f"/api/documents/{SEED3_DOC_ID}/review")
        j_s3_after = json.loads(b_s3_after.decode("utf-8"))
        assert st_s3_after == 200 and j_s3_after["currentRevisionNumber"] == 128 and j_s3_after["canSaveRevision"] is False

        final_seed_snap = query_f2_seed_core_snapshot(SEED_DB)
        if final_seed_snap["f1_f2_rows_and_seq_sha256"] != pre_mig_seed["f1_f2_rows_and_seq_sha256"]:
            raise RuntimeError("F1/F2 rows or extraction_fencing_seq changed during F3 acceptance or restart!")

        review_counts_sql = """
SELECT json_build_object(
  'heads', (SELECT count(*) FROM eledgercare.work_order_review_heads),
  'revisions', (SELECT count(*) FROM eledgercare.work_order_review_revisions),
  'fields', (SELECT count(*) FROM eledgercare.work_order_review_fields)
)::text;
"""
        review_counts = json.loads(
            invoke_psql(str(settings["appUser"]), str(settings["appPassword"]), SEED_DB, review_counts_sql).stdout.strip()
        )
        assert review_counts == {"heads": 2, "revisions": 132, "fields": 660}, f"Unexpected review row counts: {review_counts}"

        owned_ocr_workers = check_owned_local_ocr_workers()
        if owned_ocr_workers:
            raise RuntimeError(f"Observed unexpected local_ocr worker under reviewer worktree: {owned_ocr_workers}")

        # 9. Stop all owned services and confirm stopped state.
        ui_stop_2 = stop_owned_proc(ui_proc, ui_log, ui_ident)
        ui_proc = ui_log = ui_ident = None
        api_stop_2 = stop_owned_proc(api_proc, api_log, api_ident)
        api_proc = api_log = api_ident = None
        service_ledger.append({"service": "ui-4510-phase2-stop", "stop": ui_stop_2})
        service_ledger.append({"service": "api-5490-phase2-stop", "stop": api_stop_2})

        steps.append(run_logged("15-pg-cluster-stop-final", ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"], REPO_ROOT, settings))
        wait_port_free(API_PORT, timeout_s=15.0)
        wait_port_free(UI_PORT, timeout_s=15.0)
        wait_port_free(PG_PORT, timeout_s=15.0)

        final_pg_status = subprocess.run([str(pg_ctl), "status", "-D", str(pg_data)], capture_output=True, text=True)
        if final_pg_status.returncode != 3:
            raise RuntimeError(f"PostgreSQL cluster still running at completion: rc={final_pg_status.returncode}")

        final_ports = query_port_listeners([API_PORT, UI_PORT, PG_PORT])
        if any(final_ports.values()):
            raise RuntimeError(f"Owned reviewer ports not free at completion: {final_ports}")

        summary = {
            "schema": "eledgercare.wp0008.f3-independent-acceptance/1",
            "reviewer_id": "eld-f3-reviewer",
            "session_id": "025f1605-d7e3-4fea-8255-907c2b07b55f",
            "started_utc": started_utc,
            "completed_utc": utc_now(),
            "frozen_executing_head_sha": frozen_head_sha,
            "reviewed_author_candidate_sha": AUTHOR_CANDIDATE_SHA,
            "reviewed_author_evidence_sha": AUTHOR_EVIDENCE_SHA,
            "reviewed_author_report_003_sha": AUTHOR_REPORT_003_SHA,
            "reviewer_ports": {"api": API_PORT, "ui": UI_PORT, "postgresql": PG_PORT},
            "local_ocr_enabled": False,
            "static_and_boundary_audit": static_audit,
            "seed_migration_verification": {
                "database": SEED_DB,
                "pre_migration_state_sha256": pre_mig_seed["state_sha256"],
                "expected_pre_migration_state_sha256": EXPECTED_PRE_MIGRATION_SEED_STATE_SHA256,
                "pre_migration_f1_f2_rows_and_seq_sha256": pre_mig_seed["f1_f2_rows_and_seq_sha256"],
                "post_migration_f1_f2_rows_and_seq_sha256": post_mig_seed["f1_f2_rows_and_seq_sha256"],
                "post_restart_f1_f2_rows_and_seq_sha256": final_seed_snap["f1_f2_rows_and_seq_sha256"],
                "all_4_documents_4_attempts_3_results_and_seq4_untouched": True,
                "applied_migrations": post_mig_seed["snapshot"]["migrations"],
                "final_f3_review_row_counts": review_counts,
            },
            "least_privilege_and_fk_audit": priv_audit,
            "direct_api_and_concurrency_probes": direct_probes,
            "restart_identities": {
                "phase1_postmaster": pm_ident_phase1,
                "phase2_postmaster": pm_ident_phase2,
                "owned_local_ocr_worker_processes_observed": 0,
            },
            "service_ledger": service_ledger,
            "final_stopped_state": {
                "pg_ctl_status_exit_code": final_pg_status.returncode,
                "pg_ctl_status_output": final_pg_status.stdout.strip(),
                "port_listeners": final_ports,
            },
            "steps": steps,
        }
        summary_path = EVIDENCE_DIR / "acceptance-verification-summary.json"
        summary_txt = scrub_secrets(json.dumps(summary, indent=2), settings)
        summary_path.write_text(summary_txt + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "summary": str(summary_path.relative_to(REPO_ROOT)), "steps": len(steps)}))
        return 0
    finally:
        stop_owned_proc(ui_proc, ui_log, ui_ident)
        stop_owned_proc(api_proc, api_log, api_ident)
        subprocess.run(
            ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"],
            cwd=str(REPO_ROOT),
            capture_output=True,
        )


if __name__ == "__main__":
    raise SystemExit(main())
