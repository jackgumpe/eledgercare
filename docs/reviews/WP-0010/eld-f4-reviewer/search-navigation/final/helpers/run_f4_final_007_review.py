"""Frozen independent WP-0010 / 007 final search-navigation acceptance runner (`eld-f4-reviewer`).

Executes strictly on owned reviewer loopback resources (`127.0.0.1:5690` API, `127.0.0.1:4710` UI,
`127.0.0.1:55439` PostgreSQL `18.7`) with `LocalOcr:Enabled=false`, zero GPU/model/subagent calls,
zero production edits, and full preservation of `/002`, `preparation`, `runtime`, `/004`, and
`/007` preparation (`b12664dfbfd533f177a4e1089c983952d485b8c2`).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True

API_PORT = 5690
UI_PORT = 4710
PG_PORT = 55439
REVIEWER_PORTS = (API_PORT, UI_PORT, PG_PORT)

SEED_DB = "eledgercare_f4_reviewer_seed_f3"
MIGRATED_DB = "eledgercare_f4_reviewer_migrated"
E2E_007_DB = "eledgercare_f4_reviewer_007_e2e"

EXPECTED_SEED_8TABLE_SHA256 = "841a3c0a2fc6ff5bbf29d6da1feff35b53c0c35be33a89a9ea03cfe2c1a2c993"
EXPECTED_PROJECTIONS_SHA256 = "0faf93dc12d8596df7435628ac3b797b8a703c8f0cd68614e11b9d8bb39c63fa"
EXPECTED_SAVED_QUERIES_SHA256 = "53d353351b8cababc0daa6b37dd2f96d4e48c890c7b9b9242cb2b3c85d566e4d"

PRIOR_002_SHA = "85d879a1adc0ee62090f4c6a5c9a7fb8eb5f3a96"
PRIOR_PREP_SHA = "349c29773009abdf1bc228d01696d58a83d3eaa2"
PRIOR_004_SHA = "324f09934b0aa2ee8e7bed7e8118c6109effb918"
PRIOR_SN_PREP_FROZEN_SHA = "32836fbbac3eebf2773711f51557c4a128463e98"
PRIOR_SN_PREP_PUB_SHA = "b12664dfbfd533f177a4e1089c983952d485b8c2"
ROOT_FINAL_AUTHORITY_SHA = "deba1aeba80967ca6d0bce2f14da09716118ba44"
AUTHOR_C383_SHA = "c383021be1774451ba3034d89255b38b4267353b"
AUTHOR_006_BASE_SHA = "4b8e9b8231b9543b9a09cc8514a6876a70940d7b"
AUTHOR_006_CANDIDATE_SHA = "c1fed68020ae67e8b4763bc6ea5473adaa86de2b"
AUTHOR_006_EVIDENCE_SHA = "9e1d6c4211daadfb82f67911ece04568ed8610fe"
AUTHOR_006_PUB_SHA = "0f689d9b6eaf415d17095f14ad57dff2d716bac5"
MERGED_FINAL_007_BASE_SHA = "b9bf6f1d99617445b7b1b91c09088c8ecac70f1c"

EXPECTED_TREES = {
    "src": "9760402fa88dcb343c28b14ad4de1bcb2fbafb2e",
    "web": "50fbbee1f58aace4e6ec36bd64203146d23aa96f",
    "tests": "25c21310699086acb818549b2a4c0b99469208f1",
    "deploy": "86e0c73d4b4c07bbdf92ebcd65a0903fc9c039f1",
    "ELedgerCare.slnx": "c00c2bc5ef46019fb4452fdf0bba7ca2271fc976",
    "workers": "9b548ddcc73cfba8e7683d132840b08afa5a67a3",
}

EXPECTED_PREPARED_PROBE_SHA256 = "2e133f961f592fae2e1e9b604f4f794281624ca68640f0246c9f72de3795e6f0"
EXPECTED_RUNTIME_EDGE_HELPER_SHA256 = "5b2fb58b2ca9c73174e400bd3b3bd20ec2930c074f9fbe6cdd820ac50c513492"


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
    timeout_s: int = 420,
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


def run_git_raw(repo_root: Path, *args: str) -> str:
    cp = run_cmd(["git", *args], cwd=repo_root)
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr}")
    return cp.stdout


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


def load_readonly_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WP-0010 / 007 final search-navigation acceptance verifier.")
    parser.add_argument("--output", required=True, help="Output JSON verification summary path")
    parser.add_argument("--prepared-probe-output", required=True, help="Output JSON for reused 6-scenario probe")
    parser.add_argument("--extras-output", required=True, help="Output JSON for supplementary Edge checks")
    parser.add_argument("--reopen-output", required=True, help="Output JSON for F4 PDF/history reopen regression")
    parser.add_argument("--resource-return-output", required=True, help="Output JSON resource-return receipt path")
    parser.add_argument("--logs-dir", required=True, help="Directory for sanitized execution logs")
    parser.add_argument("--screenshots-dir", required=True, help="Directory for Edge PNG screenshots")
    parser.add_argument("--require-clean", action="store_true", help="Require clean worktree before running")
    parser.add_argument("--skip-full-e2e-dryrun", action="store_true", help="Scratch dry-run flag; forbidden with --require-clean")
    args = parser.parse_args(argv)
    if args.require_clean and args.skip_full_e2e_dryrun:
        raise ValueError("--skip-full-e2e-dryrun cannot be combined with --require-clean")

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[7]
    if not (repo_root / "ELedgerCare.slnx").exists():
        raise RuntimeError(f"Resolved unexpected repo_root: {repo_root}")

    logs_dir = (repo_root / args.logs_dir).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)

    assertions: list[dict] = []
    step_receipts: list[dict] = []

    def record_assert(name: str, passed: bool, detail: dict) -> None:
        assertions.append({"check": name, "passed": bool(passed), "detail": detail})
        if not passed:
            raise AssertionError(f"Assertion failed [{name}]: {json.dumps(detail)}")

    if args.require_clean:
        wt = run_git_raw(repo_root, "status", "--porcelain", "--untracked-files=all").strip()
        record_assert("clean_worktree_before_decisive_run", wt == "", {"status": wt})

    branch = run_git_raw(repo_root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    head_sha = run_git_raw(repo_root, "rev-parse", "HEAD").strip()
    record_assert("owned_review_branch", branch == "review/wp-0010-f4", {"branch": branch, "head": head_sha})

    for label, anc in (
        ("prior_002", PRIOR_002_SHA),
        ("prior_prep", PRIOR_PREP_SHA),
        ("prior_004", PRIOR_004_SHA),
        ("prior_sn_prep_frozen", PRIOR_SN_PREP_FROZEN_SHA),
        ("prior_sn_prep_pub", PRIOR_SN_PREP_PUB_SHA),
        ("root_final_authority", ROOT_FINAL_AUTHORITY_SHA),
        ("author_006_candidate", AUTHOR_006_CANDIDATE_SHA),
        ("author_006_evidence", AUTHOR_006_EVIDENCE_SHA),
        ("author_006_pub", AUTHOR_006_PUB_SHA),
        ("merged_final_007_base", MERGED_FINAL_007_BASE_SHA),
    ):
        ok = run_cmd(["git", "merge-base", "--is-ancestor", anc, head_sha], cwd=repo_root).returncode == 0
        record_assert(f"ancestor_verified:{label}", ok, {"sha": anc})

    for rel, exp_oid in EXPECTED_TREES.items():
        actual_oid = run_git_raw(repo_root, "rev-parse", f"HEAD:{rel}").strip()
        cand_oid = run_git_raw(repo_root, "rev-parse", f"{AUTHOR_006_CANDIDATE_SHA}:{rel}").strip()
        record_assert(
            f"exact_tree_oid:{rel}",
            actual_oid == exp_oid and cand_oid == exp_oid,
            {"oid": actual_oid},
        )

    # Verify author /006 touched strictly archive-page.ts and archive.spec.ts in existing source
    cand_diff = [
        ln.strip()
        for ln in run_git_raw(repo_root, "diff", "--name-only", AUTHOR_006_BASE_SHA, AUTHOR_006_CANDIDATE_SHA).splitlines()
        if ln.strip()
    ]
    non_dossier_cand = [p for p in cand_diff if not p.startswith("docs/implementation/WP-0010/eld-f4-implementer/search-navigation/")]
    pub_diff = [
        ln.strip()
        for ln in run_git_raw(repo_root, "diff", "--name-only", AUTHOR_006_EVIDENCE_SHA, AUTHOR_006_PUB_SHA).splitlines()
        if ln.strip()
    ]
    record_assert(
        "author_006_scope_and_report_only_publication_verified",
        (
            sorted(non_dossier_cand) == ["web/e2e/archive.spec.ts", "web/src/app/archive/archive-page.ts"]
            and len(cand_diff) == 11
            and pub_diff == ["docs/agent-reports/eld-f4-implementer/WP-0010/006_2026-11-17_implementation_eld-f4-implementer.md"]
        ),
        {"cand_paths": len(cand_diff), "non_dossier_cand": non_dossier_cand, "pub_diff": pub_diff},
    )

    # Verify TypeScript static security/storage scan across all 15 web/src/**/*.ts files
    ts_files = sorted((repo_root / "web/src").rglob("*.ts"))
    ts_violations: list[str] = []
    for tsf in ts_files:
        rel_ts = tsf.relative_to(repo_root).as_posix()
        txt = tsf.read_text(encoding="utf-8")
        no_comments = "\n".join(ln for ln in txt.splitlines() if not ln.strip().startswith(("//", "*", "/*")))
        for forbidden in ("innerHTML", "bypassSecurityTrustHtml", "localStorage"):
            if forbidden in no_comments:
                ts_violations.append(f"{rel_ts}:{forbidden}")
        if rel_ts != "web/src/app/intake/submission-api.ts" and "sessionStorage" in no_comments:
            ts_violations.append(f"{rel_ts}:sessionStorage")
    record_assert("web_ts_static_xss_and_storage_scan_clean", ts_violations == [], {"ts_count": len(ts_files), "violations": ts_violations})

    # Verify unchanged prepared probe & runtime Edge helper byte identities + zero arbitrary sleeps
    prepared_probe = repo_root / "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/helpers/probe_f4_search_navigation.mjs"
    runtime_edge_helper = repo_root / "docs/reviews/WP-0010/eld-f4-reviewer/runtime/helpers/verify_f4_independent_edge.mjs"
    extras_helper = script_path.parent / "verify_f4_final_navigation_extras.mjs"
    runtime_py_path = repo_root / "docs/reviews/WP-0010/eld-f4-reviewer/runtime/helpers/run_f4_independent_review.py"

    prepared_probe_sha = sha256_hex(prepared_probe.read_bytes().replace(b"\r\n", b"\n"))
    runtime_edge_sha = sha256_hex(runtime_edge_helper.read_bytes().replace(b"\r\n", b"\n"))
    extras_no_comments = "\n".join(
        ln for ln in extras_helper.read_text(encoding="utf-8").splitlines() if not ln.strip().startswith(("//", "*", "/*"))
    )
    record_assert(
        "reused_prepared_probe_and_runtime_helpers_unchanged_and_zero_sleeps",
        (
            prepared_probe_sha == EXPECTED_PREPARED_PROBE_SHA256
            and runtime_edge_sha == EXPECTED_RUNTIME_EDGE_HELPER_SHA256
            and "waitForTimeout" not in extras_no_comments
            and "setTimeout" not in extras_no_comments
        ),
        {"prepared_probe_sha256": prepared_probe_sha, "runtime_edge_helper_sha256": runtime_edge_sha},
    )

    # Verify zero files outside search-navigation/final/ modified since MERGED_FINAL_007_BASE_SHA
    since_merge_diff = [
        ln.strip()
        for ln in run_git_raw(repo_root, "diff", "--name-only", MERGED_FINAL_007_BASE_SHA, head_sha).splitlines()
        if ln.strip()
    ]
    record_assert(
        "only_final_namespace_added_since_merged_base",
        all(p.startswith("docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/final/") for p in since_merge_diff),
        {"paths": since_merge_diff},
    )

    runtime_mod = load_readonly_module("f4_runtime_helpers", runtime_py_path)
    sn_prep_mod = load_readonly_module(
        "f4_sn_prep_helpers",
        repo_root / "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/helpers/run_f4_search_navigation_prep.py",
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

    def run_logged_step(step_id: str, argv: list[str], *, cwd_override: Path | None = None, timeout_s: int = 420) -> subprocess.CompletedProcess[str]:
        t0 = time.monotonic()
        started_utc = datetime.now(timezone.utc).isoformat()
        exec_cwd = cwd_override or repo_root
        cp = run_cmd(argv, cwd=exec_cwd, timeout_s=timeout_s)
        elapsed_ms = round((time.monotonic() - t0) * 1000.0, 1)
        combined = redact_secrets((cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else ""), secrets).replace("\r\n", "\n")
        lf = logs_dir / f"{step_id}.log"
        lf.write_text(combined, encoding="utf-8", newline="\n")
        step_receipts.append({
            "step": step_id,
            "command": [redact_secrets(a, secrets) for a in argv],
            "cwd": "." if exec_cwd == repo_root else exec_cwd.relative_to(repo_root).as_posix(),
            "started_utc": started_utc,
            "elapsed_ms": elapsed_ms,
            "exit_code": cp.returncode,
            "log_relpath": lf.relative_to(repo_root).as_posix(),
            "log_sha256": sha256_hex(lf.read_bytes()),
        })
        if cp.returncode != 0:
            raise RuntimeError(f"Step {step_id} failed (exit {cp.returncode}); see {lf}")
        return cp

    spawned_processes: list[dict] = []
    active_api_proc: subprocess.Popen[bytes] | None = None
    active_api_info: dict | None = None
    active_ui_proc: subprocess.Popen[bytes] | None = None
    active_ui_info: dict | None = None

    try:
        # Step 01: Angular production bundle build (`ng build`)
        ng_cp = run_logged_step(
            "01-angular-production-build",
            [str(node_exe), "node_modules/@angular/cli/bin/ng.js", "build"],
            cwd_override=repo_root / "web",
        )
        record_assert(
            "angular_production_build_clean",
            ng_cp.returncode == 0 and "Application bundle generation complete." in (ng_cp.stdout + ng_cp.stderr),
            {"exit_code": ng_cp.returncode},
        )

        if not api_dll.exists():
            run_logged_step("01b-dotnet-build-release", ["dotnet", "build", "ELedgerCare.slnx", "-c", "Release", "--no-restore"])

        # Step 02: Start owned PostgreSQL 55439 & verify retained seed/migrated digests before tests
        run_logged_step("02-pg-cluster-start", ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"])
        pm_pid = int((pg_data_dir / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        spawned_processes.append({"role": "postmaster_55439", "info": inspect_process(pm_pid, repo_root)})

        seed_before = sn_prep_mod.compute_8table_sha256(psql_exe, settings, SEED_DB, repo_root)
        mig_8_before = sn_prep_mod.compute_8table_sha256(psql_exe, settings, MIGRATED_DB, repo_root)
        mig_proj_before = sn_prep_mod.compute_projections_sha256(psql_exe, settings, MIGRATED_DB, repo_root)
        record_assert(
            "retained_seed_and_migrated_digests_intact_before_runs",
            (
                seed_before == EXPECTED_SEED_8TABLE_SHA256
                and mig_8_before == EXPECTED_SEED_8TABLE_SHA256
                and mig_proj_before == EXPECTED_PROJECTIONS_SHA256
            ),
            {"seed_before": seed_before, "mig_8_before": mig_8_before, "mig_proj_before": mig_proj_before},
        )

        # Step 03: Full 16-spec Playwright Microsoft Edge E2E suite on separate disposable database
        if not args.skip_full_e2e_dryrun:
            e2e_cp = run_logged_step(
                "03-playwright-edge-16-e2e-5690-4710",
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    "deploy/dev/smoke/run-browser-checks.ps1",
                    "-Database",
                    E2E_007_DB,
                    "-ApiPort",
                    str(API_PORT),
                    "-UiPort",
                    str(UI_PORT),
                ],
                timeout_s=420,
            )
            record_assert(
                "playwright_edge_16_e2e_all_passed",
                "16 passed" in (e2e_cp.stdout + e2e_cp.stderr),
                {"exit_code": e2e_cp.returncode},
            )
            invoke_psql(
                psql_exe,
                host=settings["host"],
                port=int(settings["port"]),
                user=settings["adminUser"],
                password=settings["adminPassword"],
                database="postgres",
                sql=f"DROP DATABASE IF EXISTS {E2E_007_DB} WITH (FORCE);",
                cwd=repo_root,
            )

        # Start owned API 5690 (`LocalOcr:Enabled=false`) + UI 4710 against retained 9-document `MIGRATED_DB`
        active_api_proc, active_api_info = start_owned_api(
            api_dll, API_PORT, settings, MIGRATED_DB, logs_dir / "owned-api-5690.log", repo_root
        )
        active_ui_proc, active_ui_info = start_owned_ui(
            node_exe, UI_PORT, API_PORT, logs_dir / "owned-ui-4710.log", repo_root
        )

        # Step 04: Re-run UNCHANGED prepared 6-scenario probe (`SN-01A..SN-04`) against `c1fed680`
        run_logged_step(
            "04-prepared-6scenario-probe-post-fix",
            [
                str(node_exe),
                str(prepared_probe),
                "--mode",
                "enforce-ownership",
                "--tag",
                "c1fed680-fixed",
                "--ui-port",
                str(UI_PORT),
                "--api-port",
                str(API_PORT),
                "--output",
                args.prepared_probe_output,
                "--screenshot-dir",
                args.screenshots_dir,
            ],
        )

        # Step 05: Focused supplementary checks (`FX-01..FX-03`: prolonged latch, NavigationSkipped, late 503 + 400 clearing)
        run_logged_step(
            "05-focused-navigation-extras-edge",
            [
                str(node_exe),
                str(extras_helper),
                "--ui-port",
                str(UI_PORT),
                "--api-port",
                str(API_PORT),
                "--output",
                args.extras_output,
                "--screenshot-dir",
                args.screenshots_dir,
            ],
        )

        # Step 06: Saved source / readable PDF #page=2 / pinned review-history reopening + 31 saved HTTP queries
        saved_queries_result = runtime_mod.run_saved_archive_query_suite(API_PORT)
        record_assert(
            "saved_31_archive_queries_match_004_canonical_digest",
            saved_queries_result["saved_queries_sha256"] == EXPECTED_SAVED_QUERIES_SHA256,
            saved_queries_result,
        )

        run_logged_step(
            "06-saved-source-pdf-history-reopen-edge",
            [
                str(node_exe),
                str(runtime_edge_helper),
                "--phase",
                "post-006",
                "--ui-port",
                str(UI_PORT),
                "--api-port",
                str(API_PORT),
                "--output",
                args.reopen_output,
                "--screenshot-dir",
                args.screenshots_dir,
            ],
        )

        ui_stop = stop_owned_process(active_ui_proc, active_ui_info, repo_root)
        api_stop = stop_owned_process(active_api_proc, active_api_info, repo_root)
        spawned_processes.append({"role": "ui_4710", "stop": ui_stop})
        spawned_processes.append({"role": "api_5690", "stop": api_stop})
        active_ui_proc, active_ui_info = None, None
        active_api_proc, active_api_info = None, None

        seed_after = sn_prep_mod.compute_8table_sha256(psql_exe, settings, SEED_DB, repo_root)
        mig_8_after = sn_prep_mod.compute_8table_sha256(psql_exe, settings, MIGRATED_DB, repo_root)
        mig_proj_after = sn_prep_mod.compute_projections_sha256(psql_exe, settings, MIGRATED_DB, repo_root)
        record_assert(
            "retained_seed_and_migrated_digests_unchanged_after_runs",
            (
                seed_after == EXPECTED_SEED_8TABLE_SHA256
                and mig_8_after == EXPECTED_SEED_8TABLE_SHA256
                and mig_proj_after == EXPECTED_PROJECTIONS_SHA256
            ),
            {"seed_after": seed_after, "mig_8_after": mig_8_after, "mig_proj_after": mig_proj_after},
        )

        run_logged_step("07-pg-cluster-stop-final", ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"])
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

    # Compare original c383 reproduction receipt (`4 failed / 2 passed`) vs. fixed c1fed680 receipt (`0 failed / 6 passed`)
    orig_c383_receipt = json.loads(
        (repo_root / "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/observations/c383-reproduction-probe-receipt.json").read_text(
            encoding="utf-8"
        )
    )
    fixed_probe_receipt = json.loads((repo_root / args.prepared_probe_output).read_text(encoding="utf-8"))
    extras_receipt = json.loads((repo_root / args.extras_output).read_text(encoding="utf-8"))
    reopen_receipt = json.loads((repo_root / args.reopen_output).read_text(encoding="utf-8"))

    record_assert(
        "before_vs_after_6scenario_ownership_comparison_verified",
        (
            orig_c383_receipt["failed_scenario_ids"] == ["SN-01A", "SN-01B", "SN-02A", "SN-03"]
            and orig_c383_receipt["passed_scenario_ids"] == ["SN-02B", "SN-04"]
            and fixed_probe_receipt["all_ownership_passed"] is True
            and fixed_probe_receipt["failed_scenario_ids"] == []
            and fixed_probe_receipt["passed_scenario_ids"] == ["SN-01A", "SN-01B", "SN-02A", "SN-02B", "SN-03", "SN-04"]
            and extras_receipt["all_passed"] is True
            and reopen_receipt["all_passed"] is True
        ),
        {
            "c383_failed": orig_c383_receipt["failed_scenario_ids"],
            "c1fed680_passed": fixed_probe_receipt["passed_scenario_ids"],
            "c1fed680_failed": fixed_probe_receipt["failed_scenario_ids"],
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

    inv_script = script_path.parent / "build_final_007_inventory.py"
    summary_payload = {
        "schema": "eledgercare.wp-0010.reviewer-final-007-verification-summary/1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "conversation_id": "61105d43-7706-45f2-9176-69d3256248e0",
        "branch": branch,
        "executing_head_sha": head_sha,
        "merged_final_007_base_sha": MERGED_FINAL_007_BASE_SHA,
        "root_final_authority_sha": ROOT_FINAL_AUTHORITY_SHA,
        "author_006_revisions": {
            "base_sha": AUTHOR_006_BASE_SHA,
            "tested_candidate_sha": AUTHOR_006_CANDIDATE_SHA,
            "evidence_sha": AUTHOR_006_EVIDENCE_SHA,
            "report_006_publication_sha": AUTHOR_006_PUB_SHA,
            "prior_c383_source_sha": AUTHOR_C383_SHA,
        },
        "verified_trees": EXPECTED_TREES,
        "attributed_unchanged_004_backend_evidence": {
            "report_004_publication_sha": PRIOR_004_SHA,
            "evidence_sha": "41efc840a874601acfa711f27073d2c90ad35c32",
            "unchanged_trees": ["src", "tests", "deploy", "ELedgerCare.slnx", "workers"],
            "attributed_checks": [
                "9/9 worker CPU unit tests",
                "95/95 Release .NET Domain/Infrastructure/Acceptance tests",
                "5690 intake durability restart smoke",
                "forward migration 20261117091519_AddSourceLinkedArchive + 7-result/13-unit backfill",
                "23/23 raw HTTP socket 400 rejections",
                "19/19 eledgercare_app PostgreSQL 42501 mutation denials",
                "API + PostgreSQL fast-restart invariance and live fallback/503 conflict probes",
            ],
        },
        "helpers": {
            "run_f4_final_007_review_py_sha256": sha256_hex(script_path.read_bytes().replace(b"\r\n", b"\n")),
            "verify_f4_final_navigation_extras_mjs_sha256": sha256_hex(extras_helper.read_bytes().replace(b"\r\n", b"\n")),
            "build_final_007_inventory_py_sha256": sha256_hex(inv_script.read_bytes().replace(b"\r\n", b"\n")),
            "reused_prepared_probe_mjs_sha256": prepared_probe_sha,
            "reused_runtime_edge_helper_mjs_sha256": runtime_edge_sha,
        },
        "before_vs_after_6scenario_probe": {
            "unchanged_c383_failed": orig_c383_receipt["failed_scenario_ids"],
            "unchanged_c383_passed": orig_c383_receipt["passed_scenario_ids"],
            "corrected_c1fed680_failed": fixed_probe_receipt["failed_scenario_ids"],
            "corrected_c1fed680_passed": fixed_probe_receipt["passed_scenario_ids"],
            "arbitrary_sleep_calls": 0,
        },
        "retained_databases_verified_unchanged": {
            "seed_f3_8table_sha256": seed_after,
            "migrated_8table_sha256": mig_8_after,
            "migrated_projections_sha256": mig_proj_after,
            "saved_31_queries_sha256": saved_queries_result["saved_queries_sha256"],
        },
        "logged_steps": step_receipts,
        "assertion_count": len(assertions),
        "all_assertions_passed": True,
        "assertions": assertions,
        "zero_gpu_or_subagent_calls": True,
    }

    resource_return = {
        "schema": "eledgercare.wp-0010.reviewer-final-007-resource-return/1",
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
        "dropped_temporary_databases": [] if args.skip_full_e2e_dryrun else [E2E_007_DB],
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
        f"PASS [final-007]: {len(step_receipts)} steps & {len(assertions)} assertions verified; "
        f"6/6 prepared probe scenarios PASSED; saved_queries={saved_queries_result['saved_queries_sha256'][:12]}...; "
        f"ports {REVIEWER_PORTS} FREE."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
