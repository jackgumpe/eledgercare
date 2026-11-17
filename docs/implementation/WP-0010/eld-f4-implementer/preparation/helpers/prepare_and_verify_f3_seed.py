"""Frozen decisive seed & verification helper for WP-0010 F4 author preparation (`eld-f4-implementer`).

Executes strictly against owned `eld-f4-implementer` worktree resources:
  - Loopback PostgreSQL 18.7: `127.0.0.1:55438` (`.local/postgres-data`, database `eledgercare_f4_author_seed_f3`)
  - Loopback unchanged F3 API (`LocalOcr:Enabled=false`): `127.0.0.1:5590`
  - Loopback unchanged F3 Angular dev UI: `127.0.0.1:4610`

Constructs the 7-document retained pre-F4 seed database using accepted WP-0006 F2 extraction artifacts
(`SYN-WO-01-v1-raster300.pdf` 1p and `SYN-MP-01-v0-clean.pdf` 3p) via `eledgercare_app` least-privilege SQL
plus real unchanged F1/F3 HTTP API intake and review-revision operations, verifies negative privilege probes,
API/byte parity, and read-only headless Microsoft Edge UI rendering, then stops all owned services cleanly
while retaining `eledgercare_f4_author_seed_f3` on disk for later F4 forward-migration and archive acceptance.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zlib

API_PORT = 5590
UI_PORT = 4610
PG_PORT = 55438
AUTHOR_PORTS = (API_PORT, UI_PORT, PG_PORT)
SEED_DATABASE = "eledgercare_f4_author_seed_f3"

INITIAL_BASE_SHA = "956c056be2ec970340074871ecdd7e1a9855d944"
INITIAL_AUTHORITY_SHA = "8d23d755a35be26ff29c319c527bd770abdcae4b"
MERGED_COORDINATOR_AUTHORITY_SHA = "419159c0c35f8adccae88ca65b5d7d72ccdde729"

F2_SOURCE_SHA = "8a73b7a5dab51e3ccf803aceedded4929529dd35"
F2_EXECUTING_HEAD_SHA = "b343f6ff78aa41332ecbe957577b6776f8edc22f"
F2_REVIEWER_EVIDENCE_SHA = "7f0ec3a9338606ce54c4c6d2eeabab8a2c245e2a"
F2_REVIEWER_004_SHA = "c854a1d4c306c3b10d78df42a1a2552a06bb4a98"

EXPECTED_SUBSET_SHA = "47c3deb9c917f79c353b3683b2c2611ee975285ea06226c8f72444c96ce9051f"
EXPECTED_CD_SHA = "3132ca63b424f7ec371eabe50753ad7cd036278d942a6ea465547b17bf90a149"
EXPECTED_PG_FILES = 1597
EXPECTED_PG_BYTES = 151_078_582

F01_PDF_SHA256 = "47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd"
F01_PDF_BYTES = 372_258
F01_RAW_SHA256 = "7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95"
F01_RAW_BYTES = 3_236
F01_ENV_S1_SHA256 = "8e6e5b81c5bc1fb6e102438daef815bf19f4722994ba5acf737b732e703779ee"

F07_PDF_SHA256 = "15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3"
F07_PDF_BYTES = 8_422
F07_RAW_SHA256 = "c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639"
F07_RAW_BYTES = 7_511
F07_ENV_S2_SHA256 = "7fd536919461171d933cb1e8db36a21164db5b7b04bcf364c094cace3c012d96"

F1_PDF_SHA256 = "875a2d8c83c1c1002b38840f8136b60bd5ebcfe8d2df47187bf36454c59497cb"
F1_PDF_BYTES = 887

SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID = "01a1e571-0000-7000-8000-000000018496"
SYNTHESIZED_SUPERVISOR_RUN2_INSTANCE_ID = "01a1e578-0000-7000-8000-000000029208"

# Deterministic remapped IDs for Seeds 4, 5, 6 and deterministic Idempotency-Keys for Seed 7 + F3 API saves
SEED4_DOC_ID = "01a1f400-0000-7000-8000-000000000401"
SEED4_SUB_KEY = "01a1f400-0000-7000-8000-000000000402"
SEED4_JOB_ID = "01a1f400-0000-7000-8000-000000000403"
SEED4_ATT_ID = "01a1f400-0000-7000-8000-000000000404"
SEED4_RES_ID = "01a1f400-0000-7000-8000-000000000405"
SEED4_SUBMITTED_UTC = "2026-11-16T18:10:00.000000+00:00"
SEED4_STARTED_UTC = "2026-11-16T18:10:01.000000+00:00"
SEED4_COMPLETED_UTC = "2026-11-16T18:12:42.300000+00:00"

SEED5_DOC_ID = "01a1f400-0000-7000-8000-000000000501"
SEED5_SUB_KEY = "01a1f400-0000-7000-8000-000000000502"
SEED5_JOB_ID = "01a1f400-0000-7000-8000-000000000503"
SEED5_ATT_ID = "01a1f400-0000-7000-8000-000000000504"
SEED5_RES_ID = "01a1f400-0000-7000-8000-000000000505"
SEED5_SUBMITTED_UTC = "2026-11-16T18:20:00.000000+00:00"
SEED5_STARTED_UTC = "2026-11-16T18:20:01.000000+00:00"
SEED5_COMPLETED_UTC = "2026-11-16T18:25:11.217000+00:00"

SEED6_DOC_ID = "01a1f400-0000-7000-8000-000000000601"
SEED6_SUB_KEY = "01a1f400-0000-7000-8000-000000000600"
SEED6_JOB_ID = "01a1f400-0000-7000-8000-000000000603"
SEED6_ATT_ID = "01a1f400-0000-7000-8000-000000000604"
SEED6_SUBMITTED_UTC = "2026-11-16T18:30:00.000000+00:00"
SEED6_STARTED_UTC = "2026-11-16T18:30:01.000000+00:00"
SEED6_ENDED_UTC = "2026-11-16T18:30:04.500000+00:00"

SEED7_SUB_KEY = "01a1f400-0000-7000-8000-000000000702"

REVIEW_IDEMPOTENCY_KEYS = {
    "seed1_rev1_reviewed": "01a1f400-0000-7000-8000-000000000111",
    "seed1_rev2_reviewed": "01a1f400-0000-7000-8000-000000000112",
    "seed1_rev3_draft": "01a1f400-0000-7000-8000-000000000113",
    "seed3_rev1_draft": "01a1f400-0000-7000-8000-000000000311",
    "seed3_rev2_reviewed": "01a1f400-0000-7000-8000-000000000312",
    "seed4_rev1_draft": "01a1f400-0000-7000-8000-000000000411",
    "seed5_rev1_reviewed": "01a1f400-0000-7000-8000-000000000511",
}

FORBIDDEN_EXTERNAL_TOKENS = (
    "eld-f3-implementer",
    "eld-f3-reviewer",
    "eld-f4-reviewer",
    "eld-coverage-author",
    "eld-coverage-reviewer",
    "eld-coverage-custodian",
    "eledgercare-q0",
    "eledgercare-f2",
    "wp-0009/sealed",
    "wp-0009\\sealed",
    "wp-0011/sealed",
    "wp-0011\\sealed",
)
REPARSE_ATTR = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scrub_secrets(text: str, secrets: list[str]) -> str:
    out = text
    for s in secrets:
        if s:
            out = out.replace(s, "<REDACTED>")
    return out


def is_reparse_or_link(path: Path) -> bool:
    st = os.lstat(path)
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & REPARSE_ATTR)


def guard_owned_repo_path(repo_root: Path, rel_path: str) -> Path:
    target = (repo_root / rel_path).resolve()
    norm = str(target).lower()
    for bad in FORBIDDEN_EXTERNAL_TOKENS:
        if bad in norm:
            raise PermissionError(f"Refusing forbidden external path: {target}")
    target.relative_to(repo_root.resolve())
    return target


def run_cmd(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    timeout_s: int = 180,
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


def wait_ports_unbound(ports: tuple[int, ...], cwd: Path, timeout_s: float = 15.0) -> dict[str, list[dict]]:
    deadline = time.monotonic() + timeout_s
    latest = observe_ports(ports, cwd)
    while time.monotonic() < deadline:
        if all(not latest[str(p)] for p in ports):
            return latest
        time.sleep(0.25)
        latest = observe_ports(ports, cwd)
    return latest


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


def count_ocr_worker_processes(cwd: Path) -> int:
    ps = (
        "@(Get-CimInstance Win32_Process | Where-Object { "
        "$_.ProcessId -ne $PID -and $_.Name -like 'python*' -and $_.CommandLine -like '*local_ocr*run_worker*' "
        "}).Count"
    )
    cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps], cwd=cwd)
    if cp.returncode != 0:
        raise RuntimeError(f"Worker process check failed: {cp.stderr}")
    return int(cp.stdout.strip() or "0")


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
        "$bins = @('postgres.exe','pg_ctl.exe','initdb.exe','psql.exe'); "
        "$res = @{}; "
        f"$binDir = '{str(pg_root / 'bin').replace(chr(39), chr(39)*2)}'; "
        "foreach ($b in $bins) { "
        "$s = Get-AuthenticodeSignature -LiteralPath (Join-Path $binDir $b); "
        "$res[$b] = @{ status = $s.Status.ToString(); signer = $s.SignerCertificate.Subject } "
        "}; "
        "$res | ConvertTo-Json -Compress -Depth 4"
    )
    sig_cp = run_cmd(["pwsh", "-NoProfile", "-Command", sig_ps], cwd=cwd)
    if sig_cp.returncode != 0:
        raise RuntimeError(f"Authenticode check failed: {sig_cp.stderr}")
    signatures = json.loads(sig_cp.stdout)

    return {
        "archive_content_length": manifest["archive_content_length"],
        "central_directory_sha256": manifest["central_directory_sha256"],
        "expected_central_directory_sha256_match": manifest["central_directory_sha256"] == EXPECTED_CD_SHA,
        "subset_manifest_sha256": recomputed_subset_sha,
        "expected_subset_manifest_sha256_match": recomputed_subset_sha == EXPECTED_SUBSET_SHA,
        "verified_file_count": len(present_files),
        "verified_total_bytes": total_bytes,
        "missing_files": missing,
        "extra_files": extra,
        "hash_or_crc_mismatches": mismatches,
        "reparse_points": reparse_points,
        "binary_versions": versions,
        "authenticode_core_binaries": signatures,
    }


def verify_nuget_locks(repo_root: Path, nuget_packages_dir: Path) -> dict:
    lock_files = sorted(
        list((repo_root / "src").rglob("packages.lock.json"))
        + list((repo_root / "tests").rglob("packages.lock.json"))
    )
    total_entries = 0
    unique_packages: set[tuple[str, str]] = set()
    missing_packages: list[str] = []
    hash_mismatches: list[str] = []
    for lf in lock_files:
        data = json.loads(lf.read_text(encoding="utf-8"))
        for _tfm, deps in data.get("dependencies", {}).items():
            for pkg_name, meta in deps.items():
                if meta.get("type") == "Project":
                    continue
                resolved_ver = meta["resolved"]
                expected_hash = meta["contentHash"]
                total_entries += 1
                unique_packages.add((pkg_name.lower(), resolved_ver.lower()))
                meta_file = nuget_packages_dir / pkg_name.lower() / resolved_ver.lower() / ".nupkg.metadata"
                if not meta_file.is_file():
                    missing_packages.append(f"{pkg_name}@{resolved_ver}")
                else:
                    cached_meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    if cached_meta.get("contentHash") != expected_hash:
                        hash_mismatches.append(f"{pkg_name}@{resolved_ver}")
    return {
        "lockfile_count": len(lock_files),
        "package_entries_checked": total_entries,
        "unique_packages_verified": len(unique_packages),
        "missing_cached_packages": sorted(set(missing_packages)),
        "content_hash_mismatches": sorted(set(hash_mismatches)),
    }


def invoke_psql(
    psql_exe: Path,
    host: str,
    port: int,
    user: str,
    password: str,
    db: str,
    sql: str,
    cwd: Path,
    *,
    expect_error: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PGPASSWORD"] = password
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
        cwd=cwd,
        env=env,
        input_text=sql,
    )
    if not expect_error and cp.returncode != 0:
        raise RuntimeError(f"psql failed for role {user} on {db}: {cp.stderr.strip()}")
    return cp


def sql_literal(val: str) -> str:
    return "'" + val.replace("'", "''") + "'"


def build_seed_sql(repo_root: Path) -> tuple[str, dict]:
    f01_rel = "tests/fixtures/SYN-WO-01-v1-raster300.pdf"
    f07_rel = "tests/fixtures/SYN-MP-01-v0-clean.pdf"
    f1_rel = "tests/fixtures/F1-SWO-001.pdf"

    f01_pdf = guard_owned_repo_path(repo_root, f01_rel).read_bytes()
    f07_pdf = guard_owned_repo_path(repo_root, f07_rel).read_bytes()
    f1_pdf = guard_owned_repo_path(repo_root, f1_rel).read_bytes()

    assert len(f01_pdf) == F01_PDF_BYTES and sha256_hex(f01_pdf) == F01_PDF_SHA256
    assert len(f07_pdf) == F07_PDF_BYTES and sha256_hex(f07_pdf) == F07_PDF_SHA256
    assert len(f1_pdf) == F1_PDF_BYTES and sha256_hex(f1_pdf) == F1_PDF_SHA256

    trial_rel = "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/trial-summary-reviewer-v2.json"
    trial_bytes = guard_owned_repo_path(repo_root, trial_rel).read_bytes()
    trial = json.loads(trial_bytes.decode("utf-8"))
    runs_dir = "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs"

    raw_s1_rel = f"{runs_dir}/attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4/output/raw_output.utf8.bin"
    env_s1_rel = f"{runs_dir}/attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4/output/envelope.json"
    raw_s2_rel = f"{runs_dir}/attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d/output/raw_output.utf8.bin"
    env_s2_rel = f"{runs_dir}/attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d/output/envelope.json"
    raw_s4_rel = f"{runs_dir}/attempt-01a1e579-4599-7bed-acdc-2863c448c6fa/output/raw_output.utf8.bin"
    env_s4_rel = f"{runs_dir}/attempt-01a1e579-4599-7bed-acdc-2863c448c6fa/output/envelope.json"

    raw_s1 = guard_owned_repo_path(repo_root, raw_s1_rel).read_bytes()
    env_s1_bytes = guard_owned_repo_path(repo_root, env_s1_rel).read_bytes()
    raw_s2 = guard_owned_repo_path(repo_root, raw_s2_rel).read_bytes()
    env_s2_bytes = guard_owned_repo_path(repo_root, env_s2_rel).read_bytes()
    raw_s4 = guard_owned_repo_path(repo_root, raw_s4_rel).read_bytes()
    env_s4_bytes = guard_owned_repo_path(repo_root, env_s4_rel).read_bytes()

    assert len(raw_s1) == F01_RAW_BYTES and sha256_hex(raw_s1) == F01_RAW_SHA256
    assert sha256_hex(env_s1_bytes) == F01_ENV_S1_SHA256
    assert len(raw_s2) == F07_RAW_BYTES and sha256_hex(raw_s2) == F07_RAW_SHA256
    assert sha256_hex(env_s2_bytes) == F07_ENV_S2_SHA256
    assert len(raw_s4) == F01_RAW_BYTES and sha256_hex(raw_s4) == F01_RAW_SHA256

    env_s1 = json.loads(env_s1_bytes.decode("utf-8"))
    env_s2 = json.loads(env_s2_bytes.decode("utf-8"))
    env_s4 = json.loads(env_s4_bytes.decode("utf-8"))

    sc1 = trial["scenarios"]["1_f01_single_page_complete"]
    sc2 = trial["scenarios"]["2_f07_three_page_complete"]
    sc3 = trial["scenarios"]["3_live_supervisor_kill_and_explicit_retry"]

    f01_hex = f01_pdf.hex()
    f07_hex = f07_pdf.hex()
    f1_hex = f1_pdf.hex()
    raw_s1_hex = raw_s1.hex()
    raw_s2_hex = raw_s2.hex()
    raw_s4_hex = raw_s4.hex()

    def result_insert_sql(
        result_id: str,
        doc_id: str,
        job_id: str,
        attempt_id: str,
        fencing_tok: int,
        db_res: dict,
        env_doc: dict,
        raw_hex: str,
        started_utc: str,
        completed_utc: str,
    ) -> str:
        gen_json = json.dumps(env_doc["provenance"]["generation_settings"], separators=(",", ":"), sort_keys=True)
        diag_json = json.dumps(db_res["diagnostic_metadata_json"], separators=(",", ":"), sort_keys=True)
        return f"""
INSERT INTO eledgercare.extraction_results (
    result_id, document_id, job_id, attempt_id, fencing_token, schema_version,
    input_sha256, input_byte_length, page_count, raw_output_bytes, raw_output_byte_length, raw_output_sha256,
    model_repo_id, model_revision, model_manifest_sha256, dependency_lock_sha256, worker_source_digest, worker_config_digest,
    renderer_identity, generation_settings_json, finish_reason, output_page_count,
    started_at, completed_at, load_duration_ms, render_duration_ms, infer_duration_ms, total_duration_ms, diagnostic_metadata_json
) VALUES (
    {sql_literal(result_id)},
    {sql_literal(doc_id)},
    {sql_literal(job_id)},
    {sql_literal(attempt_id)},
    {int(fencing_tok)},
    {sql_literal(db_res['schema_version'])},
    decode({sql_literal(db_res['input_sha256'])}, 'hex'),
    {int(db_res['input_byte_length'])},
    {int(db_res['page_count'])},
    decode({sql_literal(raw_hex)}, 'hex'),
    {int(db_res['raw_output_byte_length'])},
    decode({sql_literal(db_res['raw_output_sha256'])}, 'hex'),
    {sql_literal(db_res['model_repo_id'])},
    {sql_literal(db_res['model_revision'])},
    decode({sql_literal(db_res['model_manifest_sha256'])}, 'hex'),
    decode({sql_literal(db_res['dependency_lock_sha256'])}, 'hex'),
    decode({sql_literal(db_res['worker_source_sha256'])}, 'hex'),
    decode({sql_literal(db_res['worker_config_sha256'])}, 'hex'),
    {sql_literal(db_res['renderer_identity'])},
    {sql_literal(gen_json)}::jsonb,
    {sql_literal(db_res['finish_reason'])},
    {int(db_res['output_page_count'])},
    {sql_literal(started_utc)},
    {sql_literal(completed_utc)},
    {int(db_res['load_duration_ms'])},
    {int(db_res['render_duration_ms'])},
    {int(db_res['infer_duration_ms'])},
    {int(db_res['total_duration_ms'])},
    {sql_literal(diag_json)}::jsonb
);
"""

    att1 = sc1["completion"]["db_attempts"][0]
    res1 = sc1["completion"]["db_result"]
    doc1_id = sc1["submission"]["receipt"]["documentId"]
    job1_id = sc1["submission"]["receipt"]["jobId"]
    sub1_ts = sc1["submission"]["receipt"]["submittedAtUtc"]
    q1_ts = sc1["completion"]["timeline"][0]["observed_utc"]

    att2 = sc2["completion"]["db_attempts"][0]
    res2 = sc2["completion"]["db_result"]
    doc2_id = sc2["submission"]["receipt"]["documentId"]
    job2_id = sc2["submission"]["receipt"]["jobId"]
    sub2_ts = sc2["submission"]["receipt"]["submittedAtUtc"]
    q2_ts = sc2["completion"]["timeline"][0]["observed_utc"]

    att3_int = sc3["retry_completion"]["db_attempts"][0]
    att4_ok = sc3["retry_completion"]["db_attempts"][1]
    res3 = sc3["retry_completion"]["db_result"]
    doc3_id = sc3["submission"]["receipt"]["documentId"]
    job3_id = sc3["submission"]["receipt"]["jobId"]
    sub3_ts = sc3["submission"]["receipt"]["submittedAtUtc"]
    q3_ts = sc3["reconciled_interrupted_view"]["queuedAtUtc"]
    q4_ts = sc3["retry_completion"]["timeline"][0]["observed_utc"]

    sql = f"""
BEGIN;
SET LOCAL synchronous_commit = on;

-- Seed 1 (ids_remapped=false): Genuine accepted F2 Scenario 1 (SYN-WO-01 1p, token 1)
INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
VALUES ({sql_literal(doc1_id)}, {sql_literal(sc1['submission']['idempotency_key'])}, {sql_literal(sub1_ts)});

INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
VALUES ({sql_literal(doc1_id)}, decode({sql_literal(f01_hex)}, 'hex'), decode({sql_literal(F01_PDF_SHA256)}, 'hex'), {F01_PDF_BYTES}, 'application/pdf', 1);

INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at, updated_at)
VALUES ({sql_literal(job1_id)}, {sql_literal(doc1_id)}, 'awaiting_extraction', {sql_literal(sub1_ts)}, {sql_literal(sub1_ts)});

DO $$ DECLARE tok bigint; BEGIN
  tok := nextval('eledgercare.extraction_fencing_seq');
  IF tok <> 1 THEN RAISE EXCEPTION 'Expected fencing_token 1, got %', tok; END IF;
END $$;

UPDATE eledgercare.processing_jobs
   SET status = 'queued', queued_at = {sql_literal(q1_ts)}, updated_at = {sql_literal(q1_ts)}
 WHERE job_id = {sql_literal(job1_id)};

UPDATE eledgercare.processing_jobs
   SET status = 'running', attempt_count = 1, latest_fencing_token = 1, updated_at = {sql_literal(att1['started_at'])}
 WHERE job_id = {sql_literal(job1_id)};

INSERT INTO eledgercare.execution_attempts (
    attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
    status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
    started_at, last_heartbeat_at
) VALUES (
    {sql_literal(att1['attempt_id'])}, {sql_literal(job1_id)}, {sql_literal(doc1_id)}, 1, 1, NULL,
    'running', 'starting', {sql_literal(att1['run_directory_name'])}, {sql_literal(SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID)},
    {int(att1['supervisor_pid'])}, {int(att1['supervisor_create_filetime'])},
    {sql_literal(att1['started_at'])}, {sql_literal(att1['started_at'])}
);

UPDATE eledgercare.execution_attempts
   SET status = 'completed', phase = 'completed',
       launcher_pid = {int(att1['launcher_pid'])}, launcher_create_filetime = {int(att1['launcher_create_filetime'])},
       worker_pid = {int(att1['worker_pid'])}, worker_create_filetime = {int(att1['worker_create_filetime'])},
       last_heartbeat_at = {sql_literal(att1['ended_at'])}, ended_at = {sql_literal(att1['ended_at'])}, exit_code = 0
 WHERE attempt_id = {sql_literal(att1['attempt_id'])};

UPDATE eledgercare.processing_jobs
   SET status = 'completed', updated_at = {sql_literal(att1['ended_at'])}
 WHERE job_id = {sql_literal(job1_id)} AND latest_fencing_token = 1;

{result_insert_sql(res1['result_id'], doc1_id, job1_id, res1['attempt_id'], 1, res1, env_s1, raw_s1_hex, env_s1['timings']['started_at_utc'], env_s1['timings']['completed_at_utc'])}

-- Seed 2 (ids_remapped=false): Genuine accepted F2 Scenario 2 (SYN-MP-01 3p unreviewed, token 2)
INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
VALUES ({sql_literal(doc2_id)}, {sql_literal(sc2['submission']['idempotency_key'])}, {sql_literal(sub2_ts)});

INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
VALUES ({sql_literal(doc2_id)}, decode({sql_literal(f07_hex)}, 'hex'), decode({sql_literal(F07_PDF_SHA256)}, 'hex'), {F07_PDF_BYTES}, 'application/pdf', 3);

INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at, updated_at)
VALUES ({sql_literal(job2_id)}, {sql_literal(doc2_id)}, 'awaiting_extraction', {sql_literal(sub2_ts)}, {sql_literal(sub2_ts)});

DO $$ DECLARE tok bigint; BEGIN
  tok := nextval('eledgercare.extraction_fencing_seq');
  IF tok <> 2 THEN RAISE EXCEPTION 'Expected fencing_token 2, got %', tok; END IF;
END $$;

UPDATE eledgercare.processing_jobs
   SET status = 'queued', queued_at = {sql_literal(q2_ts)}, updated_at = {sql_literal(q2_ts)}
 WHERE job_id = {sql_literal(job2_id)};

UPDATE eledgercare.processing_jobs
   SET status = 'running', attempt_count = 1, latest_fencing_token = 2, updated_at = {sql_literal(att2['started_at'])}
 WHERE job_id = {sql_literal(job2_id)};

INSERT INTO eledgercare.execution_attempts (
    attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
    status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
    started_at, last_heartbeat_at
) VALUES (
    {sql_literal(att2['attempt_id'])}, {sql_literal(job2_id)}, {sql_literal(doc2_id)}, 1, 2, NULL,
    'running', 'starting', {sql_literal(att2['run_directory_name'])}, {sql_literal(SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID)},
    {int(att2['supervisor_pid'])}, {int(att2['supervisor_create_filetime'])},
    {sql_literal(att2['started_at'])}, {sql_literal(att2['started_at'])}
);

UPDATE eledgercare.execution_attempts
   SET status = 'completed', phase = 'completed',
       launcher_pid = {int(att2['launcher_pid'])}, launcher_create_filetime = {int(att2['launcher_create_filetime'])},
       worker_pid = {int(att2['worker_pid'])}, worker_create_filetime = {int(att2['worker_create_filetime'])},
       last_heartbeat_at = {sql_literal(att2['ended_at'])}, ended_at = {sql_literal(att2['ended_at'])}, exit_code = 0
 WHERE attempt_id = {sql_literal(att2['attempt_id'])};

UPDATE eledgercare.processing_jobs
   SET status = 'completed', updated_at = {sql_literal(att2['ended_at'])}
 WHERE job_id = {sql_literal(job2_id)} AND latest_fencing_token = 2;

{result_insert_sql(res2['result_id'], doc2_id, job2_id, res2['attempt_id'], 2, res2, env_s2, raw_s2_hex, env_s2['timings']['started_at_utc'], env_s2['timings']['completed_at_utc'])}

-- Seed 3 (ids_remapped=false): Genuine accepted F2 Scenario 3 (SYN-WO-01 1p, interrupted token 3 + completed token 4)
INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
VALUES ({sql_literal(doc3_id)}, {sql_literal(sc3['submission']['idempotency_key'])}, {sql_literal(sub3_ts)});

INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
VALUES ({sql_literal(doc3_id)}, decode({sql_literal(f01_hex)}, 'hex'), decode({sql_literal(F01_PDF_SHA256)}, 'hex'), {F01_PDF_BYTES}, 'application/pdf', 1);

INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at, updated_at)
VALUES ({sql_literal(job3_id)}, {sql_literal(doc3_id)}, 'awaiting_extraction', {sql_literal(sub3_ts)}, {sql_literal(sub3_ts)});

DO $$ DECLARE tok bigint; BEGIN
  tok := nextval('eledgercare.extraction_fencing_seq');
  IF tok <> 3 THEN RAISE EXCEPTION 'Expected fencing_token 3, got %', tok; END IF;
END $$;

UPDATE eledgercare.processing_jobs
   SET status = 'queued', queued_at = {sql_literal(q3_ts)}, updated_at = {sql_literal(q3_ts)}
 WHERE job_id = {sql_literal(job3_id)};

UPDATE eledgercare.processing_jobs
   SET status = 'running', attempt_count = 1, latest_fencing_token = 3, updated_at = {sql_literal(att3_int['started_at'])}
 WHERE job_id = {sql_literal(job3_id)};

INSERT INTO eledgercare.execution_attempts (
    attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
    status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
    started_at, last_heartbeat_at
) VALUES (
    {sql_literal(att3_int['attempt_id'])}, {sql_literal(job3_id)}, {sql_literal(doc3_id)}, 1, 3, NULL,
    'running', 'inferring', {sql_literal(att3_int['run_directory_name'])}, {sql_literal(SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID)},
    {int(att3_int['supervisor_pid'])}, {int(att3_int['supervisor_create_filetime'])},
    {sql_literal(att3_int['started_at'])}, {sql_literal(att3_int['started_at'])}
);

UPDATE eledgercare.execution_attempts
   SET status = 'interrupted', phase = 'interrupted',
       launcher_pid = {int(att3_int['launcher_pid'])}, launcher_create_filetime = {int(att3_int['launcher_create_filetime'])},
       worker_pid = {int(att3_int['worker_pid'])}, worker_create_filetime = {int(att3_int['worker_create_filetime'])},
       last_heartbeat_at = {sql_literal(att3_int['ended_at'])}, ended_at = {sql_literal(att3_int['ended_at'])},
       failure_code = {sql_literal(att3_int['failure_code'])}, failure_detail = {sql_literal(att3_int['failure_detail'])}
 WHERE attempt_id = {sql_literal(att3_int['attempt_id'])};

UPDATE eledgercare.processing_jobs
   SET status = 'interrupted', updated_at = {sql_literal(att3_int['ended_at'])}
 WHERE job_id = {sql_literal(job3_id)} AND latest_fencing_token = 3;

DO $$ DECLARE tok bigint; BEGIN
  tok := nextval('eledgercare.extraction_fencing_seq');
  IF tok <> 4 THEN RAISE EXCEPTION 'Expected fencing_token 4, got %', tok; END IF;
END $$;

UPDATE eledgercare.processing_jobs
   SET status = 'queued', queued_at = {sql_literal(q4_ts)}, updated_at = {sql_literal(q4_ts)},
       retried_from_attempt_id = {sql_literal(att3_int['attempt_id'])}
 WHERE job_id = {sql_literal(job3_id)};

UPDATE eledgercare.processing_jobs
   SET status = 'running', attempt_count = 2, latest_fencing_token = 4, updated_at = {sql_literal(att4_ok['started_at'])}
 WHERE job_id = {sql_literal(job3_id)};

INSERT INTO eledgercare.execution_attempts (
    attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
    status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
    started_at, last_heartbeat_at
) VALUES (
    {sql_literal(att4_ok['attempt_id'])}, {sql_literal(job3_id)}, {sql_literal(doc3_id)}, 2, 4, {sql_literal(att3_int['attempt_id'])},
    'running', 'starting', {sql_literal(att4_ok['run_directory_name'])}, {sql_literal(SYNTHESIZED_SUPERVISOR_RUN2_INSTANCE_ID)},
    {int(att4_ok['supervisor_pid'])}, {int(att4_ok['supervisor_create_filetime'])},
    {sql_literal(att4_ok['started_at'])}, {sql_literal(att4_ok['started_at'])}
);

UPDATE eledgercare.execution_attempts
   SET status = 'completed', phase = 'completed',
       launcher_pid = {int(att4_ok['launcher_pid'])}, launcher_create_filetime = {int(att4_ok['launcher_create_filetime'])},
       worker_pid = {int(att4_ok['worker_pid'])}, worker_create_filetime = {int(att4_ok['worker_create_filetime'])},
       last_heartbeat_at = {sql_literal(att4_ok['ended_at'])}, ended_at = {sql_literal(att4_ok['ended_at'])}, exit_code = 0
 WHERE attempt_id = {sql_literal(att4_ok['attempt_id'])};

UPDATE eledgercare.processing_jobs
   SET status = 'completed', updated_at = {sql_literal(att4_ok['ended_at'])}
 WHERE job_id = {sql_literal(job3_id)} AND latest_fencing_token = 4;

{result_insert_sql(res3['result_id'], doc3_id, job3_id, res3['attempt_id'], 4, res3, env_s4, raw_s4_hex, env_s4['timings']['started_at_utc'], env_s4['timings']['completed_at_utc'])}

-- Seed 4 (ids_remapped=true): Explicitly remapped SYN-WO-01 1p completed result for draft-only state (token 5)
INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
VALUES ({sql_literal(SEED4_DOC_ID)}, {sql_literal(SEED4_SUB_KEY)}, {sql_literal(SEED4_SUBMITTED_UTC)});

INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
VALUES ({sql_literal(SEED4_DOC_ID)}, decode({sql_literal(f01_hex)}, 'hex'), decode({sql_literal(F01_PDF_SHA256)}, 'hex'), {F01_PDF_BYTES}, 'application/pdf', 1);

INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at, updated_at)
VALUES ({sql_literal(SEED4_JOB_ID)}, {sql_literal(SEED4_DOC_ID)}, 'awaiting_extraction', {sql_literal(SEED4_SUBMITTED_UTC)}, {sql_literal(SEED4_SUBMITTED_UTC)});

DO $$ DECLARE tok bigint; BEGIN
  tok := nextval('eledgercare.extraction_fencing_seq');
  IF tok <> 5 THEN RAISE EXCEPTION 'Expected fencing_token 5, got %', tok; END IF;
END $$;

UPDATE eledgercare.processing_jobs
   SET status = 'running', queued_at = {sql_literal(SEED4_STARTED_UTC)}, attempt_count = 1, latest_fencing_token = 5, updated_at = {sql_literal(SEED4_STARTED_UTC)}
 WHERE job_id = {sql_literal(SEED4_JOB_ID)};

INSERT INTO eledgercare.execution_attempts (
    attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
    status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
    started_at, last_heartbeat_at
) VALUES (
    {sql_literal(SEED4_ATT_ID)}, {sql_literal(SEED4_JOB_ID)}, {sql_literal(SEED4_DOC_ID)}, 1, 5, NULL,
    'running', 'starting', {sql_literal('attempt-' + SEED4_ATT_ID)}, {sql_literal(SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID)},
    {int(att1['supervisor_pid'])}, {int(att1['supervisor_create_filetime'])},
    {sql_literal(SEED4_STARTED_UTC)}, {sql_literal(SEED4_STARTED_UTC)}
);

UPDATE eledgercare.execution_attempts
   SET status = 'completed', phase = 'completed',
       last_heartbeat_at = {sql_literal(SEED4_COMPLETED_UTC)}, ended_at = {sql_literal(SEED4_COMPLETED_UTC)}, exit_code = 0
 WHERE attempt_id = {sql_literal(SEED4_ATT_ID)};

UPDATE eledgercare.processing_jobs
   SET status = 'completed', updated_at = {sql_literal(SEED4_COMPLETED_UTC)}
 WHERE job_id = {sql_literal(SEED4_JOB_ID)} AND latest_fencing_token = 5;

{result_insert_sql(SEED4_RES_ID, SEED4_DOC_ID, SEED4_JOB_ID, SEED4_ATT_ID, 5, res1, env_s1, raw_s1_hex, SEED4_STARTED_UTC, SEED4_COMPLETED_UTC)}

-- Seed 5 (ids_remapped=true): Explicitly remapped SYN-MP-01 3p completed result for reviewed Page 2/3 provenance (token 6)
INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
VALUES ({sql_literal(SEED5_DOC_ID)}, {sql_literal(SEED5_SUB_KEY)}, {sql_literal(SEED5_SUBMITTED_UTC)});

INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
VALUES ({sql_literal(SEED5_DOC_ID)}, decode({sql_literal(f07_hex)}, 'hex'), decode({sql_literal(F07_PDF_SHA256)}, 'hex'), {F07_PDF_BYTES}, 'application/pdf', 3);

INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at, updated_at)
VALUES ({sql_literal(SEED5_JOB_ID)}, {sql_literal(SEED5_DOC_ID)}, 'awaiting_extraction', {sql_literal(SEED5_SUBMITTED_UTC)}, {sql_literal(SEED5_SUBMITTED_UTC)});

DO $$ DECLARE tok bigint; BEGIN
  tok := nextval('eledgercare.extraction_fencing_seq');
  IF tok <> 6 THEN RAISE EXCEPTION 'Expected fencing_token 6, got %', tok; END IF;
END $$;

UPDATE eledgercare.processing_jobs
   SET status = 'running', queued_at = {sql_literal(SEED5_STARTED_UTC)}, attempt_count = 1, latest_fencing_token = 6, updated_at = {sql_literal(SEED5_STARTED_UTC)}
 WHERE job_id = {sql_literal(SEED5_JOB_ID)};

INSERT INTO eledgercare.execution_attempts (
    attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
    status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
    started_at, last_heartbeat_at
) VALUES (
    {sql_literal(SEED5_ATT_ID)}, {sql_literal(SEED5_JOB_ID)}, {sql_literal(SEED5_DOC_ID)}, 1, 6, NULL,
    'running', 'starting', {sql_literal('attempt-' + SEED5_ATT_ID)}, {sql_literal(SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID)},
    {int(att2['supervisor_pid'])}, {int(att2['supervisor_create_filetime'])},
    {sql_literal(SEED5_STARTED_UTC)}, {sql_literal(SEED5_STARTED_UTC)}
);

UPDATE eledgercare.execution_attempts
   SET status = 'completed', phase = 'completed',
       last_heartbeat_at = {sql_literal(SEED5_COMPLETED_UTC)}, ended_at = {sql_literal(SEED5_COMPLETED_UTC)}, exit_code = 0
 WHERE attempt_id = {sql_literal(SEED5_ATT_ID)};

UPDATE eledgercare.processing_jobs
   SET status = 'completed', updated_at = {sql_literal(SEED5_COMPLETED_UTC)}
 WHERE job_id = {sql_literal(SEED5_JOB_ID)} AND latest_fencing_token = 6;

{result_insert_sql(SEED5_RES_ID, SEED5_DOC_ID, SEED5_JOB_ID, SEED5_ATT_ID, 6, res2, env_s2, raw_s2_hex, SEED5_STARTED_UTC, SEED5_COMPLETED_UTC)}

-- Seed 6 (ids_remapped=true): Deterministic failed-attempt diagnostic fixture (0 extraction_results, token 7)
INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
VALUES ({sql_literal(SEED6_DOC_ID)}, {sql_literal(SEED6_SUB_KEY)}, {sql_literal(SEED6_SUBMITTED_UTC)});

INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
VALUES ({sql_literal(SEED6_DOC_ID)}, decode({sql_literal(f1_hex)}, 'hex'), decode({sql_literal(F1_PDF_SHA256)}, 'hex'), {F1_PDF_BYTES}, 'application/pdf', 1);

INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at, updated_at)
VALUES ({sql_literal(SEED6_JOB_ID)}, {sql_literal(SEED6_DOC_ID)}, 'awaiting_extraction', {sql_literal(SEED6_SUBMITTED_UTC)}, {sql_literal(SEED6_SUBMITTED_UTC)});

DO $$ DECLARE tok bigint; BEGIN
  tok := nextval('eledgercare.extraction_fencing_seq');
  IF tok <> 7 THEN RAISE EXCEPTION 'Expected fencing_token 7, got %', tok; END IF;
END $$;

UPDATE eledgercare.processing_jobs
   SET status = 'running', queued_at = {sql_literal(SEED6_STARTED_UTC)}, attempt_count = 1, latest_fencing_token = 7, updated_at = {sql_literal(SEED6_STARTED_UTC)}
 WHERE job_id = {sql_literal(SEED6_JOB_ID)};

INSERT INTO eledgercare.execution_attempts (
    attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
    status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
    started_at, last_heartbeat_at
) VALUES (
    {sql_literal(SEED6_ATT_ID)}, {sql_literal(SEED6_JOB_ID)}, {sql_literal(SEED6_DOC_ID)}, 1, 7, NULL,
    'running', 'inferring', {sql_literal('attempt-' + SEED6_ATT_ID)}, {sql_literal(SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID)},
    {int(att1['supervisor_pid'])}, {int(att1['supervisor_create_filetime'])},
    {sql_literal(SEED6_STARTED_UTC)}, {sql_literal(SEED6_STARTED_UTC)}
);

UPDATE eledgercare.execution_attempts
   SET status = 'failed', phase = 'failed',
       last_heartbeat_at = {sql_literal(SEED6_ENDED_UTC)}, ended_at = {sql_literal(SEED6_ENDED_UTC)}, exit_code = 1,
       failure_code = 'worker_failed',
       failure_detail = 'NONSEARCH-FAILURE-DETAIL-719: Synthetic failed-attempt fixture for archive non-searchability verification',
       diagnostic_raw_output_utf8 = '<PAGE><BLOCK>text[0, 0, 10, 10]<FORK>NONSEARCH-DIAGNOSTIC-PARTIAL-719',
       diagnostic_metadata_json = '{{"fixture":"f4_author_prep_failed_attempt"}}'::jsonb
 WHERE attempt_id = {sql_literal(SEED6_ATT_ID)};

UPDATE eledgercare.processing_jobs
   SET status = 'failed', updated_at = {sql_literal(SEED6_ENDED_UTC)}
 WHERE job_id = {sql_literal(SEED6_JOB_ID)} AND latest_fencing_token = 7;

COMMIT;
"""

    input_inventory = [
        {"path": f01_rel, "bytes": len(f01_pdf), "sha256": sha256_hex(f01_pdf)},
        {"path": f07_rel, "bytes": len(f07_pdf), "sha256": sha256_hex(f07_pdf)},
        {"path": f1_rel, "bytes": len(f1_pdf), "sha256": sha256_hex(f1_pdf)},
        {"path": trial_rel, "bytes": len(trial_bytes), "sha256": sha256_hex(trial_bytes)},
        {"path": raw_s1_rel, "bytes": len(raw_s1), "sha256": sha256_hex(raw_s1)},
        {"path": env_s1_rel, "bytes": len(env_s1_bytes), "sha256": sha256_hex(env_s1_bytes)},
        {"path": raw_s2_rel, "bytes": len(raw_s2), "sha256": sha256_hex(raw_s2)},
        {"path": env_s2_rel, "bytes": len(env_s2_bytes), "sha256": sha256_hex(env_s2_bytes)},
        {"path": raw_s4_rel, "bytes": len(raw_s4), "sha256": sha256_hex(raw_s4)},
        {"path": env_s4_rel, "bytes": len(env_s4_bytes), "sha256": sha256_hex(env_s4_bytes)},
    ]

    seed_manifest = {
        "attribution": {
            "imported_extraction_seeds_not_fresh_inference": True,
            "f2_product_source_sha": F2_SOURCE_SHA,
            "f2_reviewer_executing_head_sha": F2_EXECUTING_HEAD_SHA,
            "f2_reviewer_runtime_evidence_sha": F2_REVIEWER_EVIDENCE_SHA,
            "f2_reviewer_report_004_sha": F2_REVIEWER_004_SHA,
            "review_revisions_created_via_real_unchanged_f3_api": True,
            "seed7_unprocessed_submitted_via_real_unchanged_f1_api": True,
            "identity_remapping": {
                "seeds_1_to_3": "exact_original_ids_preserved (ids_remapped=false)",
                "seed_4": {
                    "ids_remapped": True,
                    "source_f2_scenario": "1_f01_single_page_complete",
                    "original_document_id": doc1_id,
                    "remapped_document_id": SEED4_DOC_ID,
                    "remapped_job_id": SEED4_JOB_ID,
                    "remapped_attempt_id": SEED4_ATT_ID,
                    "remapped_result_id": SEED4_RES_ID,
                    "fencing_token": 5,
                    "purpose": "Distinct completed work-order document carrying draft-only Rev #1 (zero reviewed revisions).",
                },
                "seed_5": {
                    "ids_remapped": True,
                    "source_f2_scenario": "2_f07_three_page_complete",
                    "original_document_id": doc2_id,
                    "remapped_document_id": SEED5_DOC_ID,
                    "remapped_job_id": SEED5_JOB_ID,
                    "remapped_attempt_id": SEED5_ATT_ID,
                    "remapped_result_id": SEED5_RES_ID,
                    "fencing_token": 6,
                    "purpose": "Distinct 3-page completed multipage document carrying reviewed Rev #1 with Page 2 & Page 3 spanning-table provenance.",
                },
                "seed_6": {
                    "ids_remapped": True,
                    "source_fixture": f1_rel,
                    "remapped_document_id": SEED6_DOC_ID,
                    "remapped_job_id": SEED6_JOB_ID,
                    "remapped_attempt_id": SEED6_ATT_ID,
                    "fencing_token": 7,
                    "purpose": "Deterministic failed-extraction fixture (0 extraction_results) with diagnostic_raw_output_utf8 sentinel NONSEARCH-DIAGNOSTIC-PARTIAL-719.",
                },
                "synthesized_internal_supervisor_instance_ids": {
                    "api_rev_run1_pid_18496": SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID,
                    "api_rev_run2_pid_29208": SYNTHESIZED_SUPERVISOR_RUN2_INSTANCE_ID,
                },
            },
        },
        "verified_input_artifacts": input_inventory,
        "sql_seeded_documents": [
            {
                "seed_index": 1,
                "label": "wo_reviewed_rev2_then_newer_draft_rev3",
                "document_id": doc1_id,
                "idempotency_key": sc1["submission"]["idempotency_key"],
                "job_id": job1_id,
                "result_id": res1["result_id"],
                "pages": 1,
                "input_sha256": F01_PDF_SHA256,
                "raw_output_sha256": F01_RAW_SHA256,
                "fencing_tokens": [1],
                "ids_remapped": False,
            },
            {
                "seed_index": 2,
                "label": "mp_3page_completed_unreviewed",
                "document_id": doc2_id,
                "idempotency_key": sc2["submission"]["idempotency_key"],
                "job_id": job2_id,
                "result_id": res2["result_id"],
                "pages": 3,
                "input_sha256": F07_PDF_SHA256,
                "raw_output_sha256": F07_RAW_SHA256,
                "fencing_tokens": [2],
                "ids_remapped": False,
            },
            {
                "seed_index": 3,
                "label": "wo_interrupted_retry_completed_reviewed_head",
                "document_id": doc3_id,
                "idempotency_key": sc3["submission"]["idempotency_key"],
                "job_id": job3_id,
                "result_id": res3["result_id"],
                "pages": 1,
                "input_sha256": F01_PDF_SHA256,
                "raw_output_sha256": F01_RAW_SHA256,
                "fencing_tokens": [3, 4],
                "ids_remapped": False,
            },
            {
                "seed_index": 4,
                "label": "wo_draft_only_never_reviewed_remapped",
                "document_id": SEED4_DOC_ID,
                "idempotency_key": SEED4_SUB_KEY,
                "job_id": SEED4_JOB_ID,
                "result_id": SEED4_RES_ID,
                "pages": 1,
                "input_sha256": F01_PDF_SHA256,
                "raw_output_sha256": F01_RAW_SHA256,
                "fencing_tokens": [5],
                "ids_remapped": True,
            },
            {
                "seed_index": 5,
                "label": "mp_3page_reviewed_page2_page3_provenance_remapped",
                "document_id": SEED5_DOC_ID,
                "idempotency_key": SEED5_SUB_KEY,
                "job_id": SEED5_JOB_ID,
                "result_id": SEED5_RES_ID,
                "pages": 3,
                "input_sha256": F07_PDF_SHA256,
                "raw_output_sha256": F07_RAW_SHA256,
                "fencing_tokens": [6],
                "ids_remapped": True,
            },
            {
                "seed_index": 6,
                "label": "f1_failed_attempt_diagnostic_partial_nonsearchable",
                "document_id": SEED6_DOC_ID,
                "idempotency_key": SEED6_SUB_KEY,
                "job_id": SEED6_JOB_ID,
                "result_id": None,
                "pages": 1,
                "input_sha256": F1_PDF_SHA256,
                "raw_output_sha256": None,
                "fencing_tokens": [7],
                "ids_remapped": True,
            },
        ],
    }
    return sql, seed_manifest


def http_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout_s: float = 30.0,
) -> tuple[int, dict[str, str], bytes]:
    req_headers = dict(headers or {})
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, resp_headers, resp.read()
    except urllib.error.HTTPError as exc:
        resp_headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
        return exc.code, resp_headers, exc.read()


def http_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict | None = None,
) -> tuple[int, dict[str, str], dict]:
    h = {"Accept": "application/json"}
    if headers:
        h.update(headers)
    raw_body = None
    if payload is not None:
        h["Content-Type"] = "application/json"
        raw_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    status, resp_headers, data = http_request(url, method=method, headers=h, body=raw_body)
    return status, resp_headers, json.loads(data.decode("utf-8")) if data else {}


def find_table_cell_coord(pages: list[dict], target_page: int, exact_text: str) -> dict:
    for p in pages:
        if int(p["pageNumber"]) != target_page:
            continue
        for b_idx, block in enumerate(p["blocks"]):
            rows = block.get("tableRows")
            if block.get("kind") == "table" and rows:
                for r_idx, row in enumerate(rows):
                    for c_idx, cell in enumerate(row):
                        if cell == exact_text:
                            return {
                                "pageNumber": target_page,
                                "blockOrdinal": b_idx,
                                "tableRow": r_idx,
                                "tableColumn": c_idx,
                            }
    raise RuntimeError(f"Could not find table cell '{exact_text}' on page {target_page}")


def src_to_coord(src_obj: dict | None) -> dict | None:
    if src_obj is None:
        return None
    return {
        "pageNumber": src_obj["pageNumber"],
        "blockOrdinal": src_obj["blockOrdinal"],
        "tableRow": src_obj["tableRow"],
        "tableColumn": src_obj["tableColumn"],
    }


def query_canonical_f3_db_state(
    psql_exe: Path, host: str, port: int, user: str, password: str, db: str, cwd: Path
) -> dict:
    snap_sql = """
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
    raw = invoke_psql(psql_exe, host, port, user, password, db, snap_sql, cwd).stdout.strip()
    parsed = json.loads(raw)
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {"snapshot": parsed, "canonical_sha256": sha256_hex(canonical)}


def stop_proc_tree(proc: subprocess.Popen | None, cwd: Path) -> None:
    if proc is None or proc.poll() is not None:
        return
    pid = proc.pid
    # Terminate child tree cleanly on Windows if owned PID is still alive (e.g. node -> ng serve).
    run_cmd(["taskkill", "/PID", str(pid), "/T", "/F"], cwd=cwd)
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def execute_api_seed_and_ui_smoke(
    repo_root: Path,
    app_conn_str: str,
    seed_manifest: dict,
    logs_dir: Path,
    secrets_to_scrub: list[str],
    psql_exe: Path,
    raw_settings: dict,
) -> tuple[dict, dict, dict, dict]:
    api_dir = repo_root / "src" / "ELedgerCare.Api" / "bin" / "Release" / "net10.0"
    api_dll = api_dir / "ELedgerCare.Api.dll"
    if not api_dll.is_file():
        raise FileNotFoundError(f"Built ELedgerCare.Api.dll missing at {api_dll}")

    api_env = dict(os.environ)
    api_env["ASPNETCORE_ENVIRONMENT"] = "Production"
    api_env["ConnectionStrings__Runtime"] = app_conn_str
    api_env["Api__Port"] = str(API_PORT)
    api_env["LocalOcr__Enabled"] = "false"
    api_env["DOTNET_NOLOGO"] = "1"
    api_env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"

    api_log_file = logs_dir / "owned-api-5590.log"
    api_fh = api_log_file.open("w", encoding="utf-8", newline="\n")
    api_proc = subprocess.Popen(
        ["dotnet", str(api_dll)],
        cwd=str(api_dir),
        env=api_env,
        stdout=api_fh,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    api_pid = api_proc.pid
    api_proc_meta = None
    ui_proc = None
    ui_proc_meta = None
    ui_log_file = logs_dir / "owned-ui-4610.log"
    ui_fh = None

    try:
        deadline = time.monotonic() + 45.0
        bound = False
        while time.monotonic() < deadline:
            if api_proc.poll() is not None:
                api_fh.flush()
                raise RuntimeError(f"API exited early ({api_proc.returncode})")
            ports_now = observe_ports((API_PORT,), repo_root)
            if any(c["owningPid"] == api_pid for c in ports_now[str(API_PORT)]):
                bound = True
                break
            time.sleep(0.2)
        if not bound:
            raise RuntimeError(f"Owned API did not bind 127.0.0.1:{API_PORT} within 45s")

        api_proc_meta = inspect_process(api_pid, repo_root)
        base_url = f"http://127.0.0.1:{API_PORT}"
        f1_bytes = guard_owned_repo_path(repo_root, "tests/fixtures/F1-SWO-001.pdf").read_bytes()

        # 1. Submit Seed 7 (F1-SWO-001.pdf) via real unchanged POST /api/documents + verify replay + 503 extraction + 409 review
        st_sub7, _, body_sub7_raw = http_request(
            f"{base_url}/api/documents",
            method="POST",
            headers={
                "Content-Type": "application/pdf",
                "Idempotency-Key": SEED7_SUB_KEY,
                "Accept": "application/json",
            },
            body=f1_bytes,
        )
        body_sub7 = json.loads(body_sub7_raw.decode("utf-8"))
        if st_sub7 != 201:
            raise RuntimeError(f"Expected 201 Created for Seed 7 submission, got {st_sub7}: {body_sub7}")
        seed7_doc_id = body_sub7["documentId"]

        st_rep7, _, body_rep7_raw = http_request(
            f"{base_url}/api/documents",
            method="POST",
            headers={
                "Content-Type": "application/pdf",
                "Idempotency-Key": SEED7_SUB_KEY,
                "Accept": "application/json",
            },
            body=f1_bytes,
        )
        body_rep7 = json.loads(body_rep7_raw.decode("utf-8"))
        st_ext_req7, _, body_ext_req7 = http_json(f"{base_url}/api/documents/{seed7_doc_id}/extraction", method="POST")
        st_rev_7, _, body_rev_7 = http_json(f"{base_url}/api/documents/{seed7_doc_id}/review")
        st_rev_6, _, body_rev_6 = http_json(f"{base_url}/api/documents/{SEED6_DOC_ID}/review")

        # 2. Seed 1 (01a1e571-2838-714b-861b-bf0835d7c90a): Rev #1 reviewed -> Rev #2 reviewed -> Rev #3 draft + replay of Rev #2
        doc1_id = seed_manifest["sql_seeded_documents"][0]["document_id"]
        res1_id = seed_manifest["sql_seeded_documents"][0]["result_id"]
        st_r0_1, _, rev0_1 = http_json(f"{base_url}/api/documents/{doc1_id}/review")
        assert st_r0_1 == 200 and rev0_1["currentRevisionNumber"] == 0
        mc1 = {f["fieldKey"]: f["machineCandidate"] for f in rev0_1["fields"]}

        seed1_rev1_payload = {
            "profileId": "maintenance-work-order/1",
            "resultId": res1_id,
            "expectedRevision": 0,
            "status": "reviewed",
            "operatorDisplayLabel": "OP-NONSEARCH-LABEL-ALPHA",
            "fields": [
                {"fieldKey": "work_order_id", "decision": "accepted", "value": mc1["work_order_id"]["value"], "unknownReason": None, "consultedSource": None},
                {"fieldKey": "property_name", "decision": "edited", "value": "Cedar Hollow North Annex [SUPERSEDED-REV1-BIRCHWOOD]", "unknownReason": None, "consultedSource": src_to_coord(mc1["property_name"]["source"])},
                {"fieldKey": "building_unit", "decision": "edited", "value": "Bldg B - Unit 204 [SUPERSEDED-UNIT-TAG-991]", "unknownReason": None, "consultedSource": src_to_coord(mc1["building_unit"]["source"])},
                {"fieldKey": "requested_date", "decision": "accepted", "value": mc1["requested_date"]["value"], "unknownReason": None, "consultedSource": None},
                {"fieldKey": "issue_and_resolution", "decision": "accepted", "value": mc1["issue_and_resolution"]["value"], "unknownReason": None, "consultedSource": None},
            ],
        }
        st_s1_r1, _, resp_s1_r1 = http_json(
            f"{base_url}/api/documents/{doc1_id}/review/revisions",
            method="POST",
            headers={"Idempotency-Key": REVIEW_IDEMPOTENCY_KEYS["seed1_rev1_reviewed"]},
            payload=seed1_rev1_payload,
        )
        if st_s1_r1 != 201:
            raise RuntimeError(f"Seed 1 Rev #1 failed ({st_s1_r1}): {resp_s1_r1}")

        seed1_rev2_payload = {
            "profileId": "maintenance-work-order/1",
            "resultId": res1_id,
            "expectedRevision": 1,
            "status": "reviewed",
            "operatorDisplayLabel": "OP-NONSEARCH-LABEL-BETA",
            "fields": [
                {"fieldKey": "work_order_id", "decision": "accepted", "value": mc1["work_order_id"]["value"], "unknownReason": None, "consultedSource": None},
                {"fieldKey": "property_name", "decision": "edited", "value": "Cedar Hollow West Wing \u2014 Caf\u00e9_100% \\ [REV2-ACTIVE-HAWTHORNE]", "unknownReason": None, "consultedSource": src_to_coord(mc1["property_name"]["source"])},
                {"fieldKey": "building_unit", "decision": "unknown", "value": None, "unknownReason": "NONSEARCH-UNKNOWN-REASON-PLACARD-772: Unit door placard obstructed on raster scan", "consultedSource": None},
                {"fieldKey": "requested_date", "decision": "accepted", "value": mc1["requested_date"]["value"], "unknownReason": None, "consultedSource": None},
                {"fieldKey": "issue_and_resolution", "decision": "edited", "value": "Replaced 45/5 uF capacitor & contactor \U0001f527; calibrated supply damper <script>alert('inert')</script> [MANUAL-NO-PROVENANCE-KESTREL-0042].", "unknownReason": None, "consultedSource": None},
            ],
        }
        st_s1_r2, _, resp_s1_r2 = http_json(
            f"{base_url}/api/documents/{doc1_id}/review/revisions",
            method="POST",
            headers={"Idempotency-Key": REVIEW_IDEMPOTENCY_KEYS["seed1_rev2_reviewed"]},
            payload=seed1_rev2_payload,
        )
        if st_s1_r2 != 201:
            raise RuntimeError(f"Seed 1 Rev #2 failed ({st_s1_r2}): {resp_s1_r2}")

        seed1_rev3_payload = {
            "profileId": "maintenance-work-order/1",
            "resultId": res1_id,
            "expectedRevision": 2,
            "status": "draft",
            "operatorDisplayLabel": "OP-NONSEARCH-LABEL-GAMMA",
            "fields": [
                {"fieldKey": "work_order_id", "decision": "accepted", "value": mc1["work_order_id"]["value"], "unknownReason": None, "consultedSource": None},
                {"fieldKey": "property_name", "decision": "edited", "value": "DRAFT-ONLY-UNAPPROVED-JUNIPER-883", "unknownReason": None, "consultedSource": None},
                {"fieldKey": "building_unit", "decision": "unreviewed", "value": "DRAFT-UNREVIEWED-UNIT-999", "unknownReason": None, "consultedSource": None},
                {"fieldKey": "requested_date", "decision": "accepted", "value": mc1["requested_date"]["value"], "unknownReason": None, "consultedSource": None},
                {"fieldKey": "issue_and_resolution", "decision": "edited", "value": "Pending supervisor callback DRAFT-ONLY-FOLLOWUP-883", "unknownReason": None, "consultedSource": None},
            ],
        }
        st_s1_r3, _, resp_s1_r3 = http_json(
            f"{base_url}/api/documents/{doc1_id}/review/revisions",
            method="POST",
            headers={"Idempotency-Key": REVIEW_IDEMPOTENCY_KEYS["seed1_rev3_draft"]},
            payload=seed1_rev3_payload,
        )
        if st_s1_r3 != 201:
            raise RuntimeError(f"Seed 1 Rev #3 failed ({st_s1_r3}): {resp_s1_r3}")

        # Verify historical idempotent replay of Rev #2 after Rev #3 is current head
        st_s1_r2_rep, _, resp_s1_r2_rep = http_json(
            f"{base_url}/api/documents/{doc1_id}/review/revisions",
            method="POST",
            headers={"Idempotency-Key": REVIEW_IDEMPOTENCY_KEYS["seed1_rev2_reviewed"]},
            payload=seed1_rev2_payload,
        )
        if st_s1_r2_rep != 200 or not resp_s1_r2_rep.get("replayed") or resp_s1_r2_rep.get("isCurrentHead") is not False:
            raise RuntimeError(f"Unexpected Rev #2 historical replay response ({st_s1_r2_rep}): {resp_s1_r2_rep}")

        # 3. Seed 3 (01a1e578-8f3a-7e0c-826b-a2c9dc066a8f): Rev #1 draft -> Rev #2 reviewed head
        doc3_id = seed_manifest["sql_seeded_documents"][2]["document_id"]
        res3_id = seed_manifest["sql_seeded_documents"][2]["result_id"]
        st_r0_3, _, rev0_3 = http_json(f"{base_url}/api/documents/{doc3_id}/review")
        assert st_r0_3 == 200
        mc3 = {f["fieldKey"]: f["machineCandidate"] for f in rev0_3["fields"]}

        seed3_rev1_payload = {
            "profileId": "maintenance-work-order/1",
            "resultId": res3_id,
            "expectedRevision": 0,
            "status": "draft",
            "operatorDisplayLabel": "OP-NONSEARCH-LABEL-DELTA",
            "fields": [
                {"fieldKey": "work_order_id", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
                {"fieldKey": "property_name", "decision": "edited", "value": "DRAFT-PREDECESSOR-WILLOW-301", "unknownReason": None, "consultedSource": None},
                {"fieldKey": "building_unit", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
                {"fieldKey": "requested_date", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
                {"fieldKey": "issue_and_resolution", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
            ],
        }
        st_s3_r1, _, resp_s3_r1 = http_json(
            f"{base_url}/api/documents/{doc3_id}/review/revisions",
            method="POST",
            headers={"Idempotency-Key": REVIEW_IDEMPOTENCY_KEYS["seed3_rev1_draft"]},
            payload=seed3_rev1_payload,
        )
        if st_s3_r1 != 201:
            raise RuntimeError(f"Seed 3 Rev #1 failed ({st_s3_r1}): {resp_s3_r1}")

        seed3_rev2_payload = {
            "profileId": "maintenance-work-order/1",
            "resultId": res3_id,
            "expectedRevision": 1,
            "status": "reviewed",
            "operatorDisplayLabel": "OP-NONSEARCH-LABEL-EPSILON",
            "fields": [
                {"fieldKey": "work_order_id", "decision": "edited", "value": "WO-009450", "unknownReason": None, "consultedSource": src_to_coord(mc3["work_order_id"]["source"])},
                {"fieldKey": "property_name", "decision": "edited", "value": "Sycamore Ridge Residences [REVIEWED-HEAD-SYCAMORE-402]", "unknownReason": None, "consultedSource": src_to_coord(mc3["property_name"]["source"])},
                {"fieldKey": "building_unit", "decision": "edited", "value": "Bldg C - Boiler Room 09", "unknownReason": None, "consultedSource": src_to_coord(mc3["building_unit"]["source"])},
                {"fieldKey": "requested_date", "decision": "accepted", "value": mc3["requested_date"]["value"], "unknownReason": None, "consultedSource": None},
                {"fieldKey": "issue_and_resolution", "decision": "accepted", "value": mc3["issue_and_resolution"]["value"], "unknownReason": None, "consultedSource": None},
            ],
        }
        st_s3_r2, _, resp_s3_r2 = http_json(
            f"{base_url}/api/documents/{doc3_id}/review/revisions",
            method="POST",
            headers={"Idempotency-Key": REVIEW_IDEMPOTENCY_KEYS["seed3_rev2_reviewed"]},
            payload=seed3_rev2_payload,
        )
        if st_s3_r2 != 201:
            raise RuntimeError(f"Seed 3 Rev #2 failed ({st_s3_r2}): {resp_s3_r2}")

        # 4. Seed 4 (01a1f400-0000-7000-8000-000000000401): Rev #1 draft-only (never reviewed)
        st_r0_4, _, rev0_4 = http_json(f"{base_url}/api/documents/{SEED4_DOC_ID}/review")
        assert st_r0_4 == 200
        mc4 = {f["fieldKey"]: f["machineCandidate"] for f in rev0_4["fields"]}

        seed4_rev1_payload = {
            "profileId": "maintenance-work-order/1",
            "resultId": SEED4_RES_ID,
            "expectedRevision": 0,
            "status": "draft",
            "operatorDisplayLabel": "OP-NONSEARCH-LABEL-ZETA",
            "fields": [
                {"fieldKey": "work_order_id", "decision": "accepted", "value": mc4["work_order_id"]["value"], "unknownReason": None, "consultedSource": None},
                {"fieldKey": "property_name", "decision": "edited", "value": "Draft-Only Pinecrest Annex [NEVER-REVIEWED-DRAFT-PINECREST-501]", "unknownReason": None, "consultedSource": None},
                {"fieldKey": "building_unit", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
                {"fieldKey": "requested_date", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
                {"fieldKey": "issue_and_resolution", "decision": "unreviewed", "value": None, "unknownReason": None, "consultedSource": None},
            ],
        }
        st_s4_r1, _, resp_s4_r1 = http_json(
            f"{base_url}/api/documents/{SEED4_DOC_ID}/review/revisions",
            method="POST",
            headers={"Idempotency-Key": REVIEW_IDEMPOTENCY_KEYS["seed4_rev1_draft"]},
            payload=seed4_rev1_payload,
        )
        if st_s4_r1 != 201:
            raise RuntimeError(f"Seed 4 Rev #1 failed ({st_s4_r1}): {resp_s4_r1}")

        # 5. Seed 5 (01a1f400-0000-7000-8000-000000000501, 3-page SYN-MP-01): Rev #1 reviewed with Page 2 & Page 3 table-cell provenance
        st_ext5, _, ext5 = http_json(f"{base_url}/api/documents/{SEED5_DOC_ID}/extraction")
        assert st_ext5 == 200
        pages5 = ext5["result"]["pages"]
        coord_p2_wo = find_table_cell_coord(pages5, 2, "WO-004731")
        coord_p2_boiler = find_table_cell_coord(pages5, 2, "Bldg B Boiler - Brass Auto Air Vent Valve 1/8 NPT")
        coord_p3_lamp = find_table_cell_coord(pages5, 3, "Laundry Rm B - Tombstone Rewire & Lamp Retrofit")
        coord_p1_date = find_table_cell_coord(pages5, 1, "2026-10-31")

        seed5_rev1_payload = {
            "profileId": "maintenance-work-order/1",
            "resultId": SEED5_RES_ID,
            "expectedRevision": 0,
            "status": "reviewed",
            "operatorDisplayLabel": "OP-NONSEARCH-LABEL-ETA",
            "fields": [
                {"fieldKey": "work_order_id", "decision": "edited", "value": "WO-004731", "unknownReason": None, "consultedSource": coord_p2_wo},
                {"fieldKey": "property_name", "decision": "edited", "value": "Maple Ridge Boiler Loop [MULTIPAGE-REVIEWED-ALDER-P2]", "unknownReason": None, "consultedSource": coord_p2_boiler},
                {"fieldKey": "building_unit", "decision": "edited", "value": "Laundry Rm B \u2014 Lamp Retrofit", "unknownReason": None, "consultedSource": coord_p3_lamp},
                {"fieldKey": "requested_date", "decision": "edited", "value": "2026-10-31", "unknownReason": None, "consultedSource": coord_p1_date},
                {"fieldKey": "issue_and_resolution", "decision": "unknown", "value": None, "unknownReason": "NONSEARCH-MP-SUMMARY-OMITTED-604: Consolidated monthly statement spans multiple line items", "consultedSource": None},
            ],
        }
        st_s5_r1, _, resp_s5_r1 = http_json(
            f"{base_url}/api/documents/{SEED5_DOC_ID}/review/revisions",
            method="POST",
            headers={"Idempotency-Key": REVIEW_IDEMPOTENCY_KEYS["seed5_rev1_reviewed"]},
            payload=seed5_rev1_payload,
        )
        if st_s5_r1 != 201:
            raise RuntimeError(f"Seed 5 Rev #1 failed ({st_s5_r1}): {resp_s5_r1}")

        # 6. Verify read parity across all 7 documents on 127.0.0.1:5590
        all_doc_specs = list(seed_manifest["sql_seeded_documents"]) + [
            {
                "seed_index": 7,
                "label": "f1_unprocessed_submitted_via_real_api",
                "document_id": seed7_doc_id,
                "idempotency_key": SEED7_SUB_KEY,
                "job_id": body_sub7["jobId"],
                "result_id": None,
                "pages": 1,
                "input_sha256": F1_PDF_SHA256,
                "raw_output_sha256": None,
                "fencing_tokens": [],
                "ids_remapped": False,
            }
        ]

        verified_docs: list[dict] = []
        for item in all_doc_specs:
            did = item["document_id"]
            st_d, _, d_body = http_json(f"{base_url}/api/documents/{did}")
            st_e, _, e_body = http_json(f"{base_url}/api/documents/{did}/extraction")
            st_s, _, s_body = http_json(f"{base_url}/api/submissions/{item['idempotency_key']}")
            st_o, o_hdr, o_bytes = http_request(f"{base_url}/api/documents/{did}/original")
            st_p, p_hdr, p_bytes = http_request(f"{base_url}/api/documents/{did}/preview")
            res_obj = e_body.get("result")
            wo_rev_summary = d_body.get("workOrderReview")

            verified_docs.append(
                {
                    "seed_index": item["seed_index"],
                    "label": item["label"],
                    "document_id": did,
                    "ids_remapped": item["ids_remapped"],
                    "get_document_status": st_d,
                    "get_extraction_status": st_e,
                    "get_submission_status": st_s,
                    "get_original_status": st_o,
                    "get_preview_status": st_p,
                    "doc_wire_status": d_body["status"],
                    "worker_enabled": e_body["workerEnabled"],
                    "can_request_extraction": e_body["canRequestExtraction"],
                    "can_retry_extraction": e_body["canRetryExtraction"],
                    "attempt_count_api": len(e_body["attempts"]),
                    "accepted_result_id_api": d_body["acceptedResultId"],
                    "result_raw_sha256_api": res_obj["rawSha256"] if res_obj else None,
                    "page_numbers_api": [p["pageNumber"] for p in res_obj["pages"]] if res_obj else [],
                    "page_block_counts_api": [len(p["blocks"]) for p in res_obj["pages"]] if res_obj else [],
                    "original_bytes": len(o_bytes),
                    "original_sha256": sha256_hex(o_bytes),
                    "preview_exact_match": o_bytes == p_bytes and p_hdr.get("x-frame-options") == "SAMEORIGIN",
                    "submission_matches_doc_id": s_body["documentId"] == did,
                    "work_order_review_head_api": wo_rev_summary,
                }
            )

        # 7. Capture canonical 8-table DB state before launching Angular UI + headless Edge smoke
        db_before_ui = query_canonical_f3_db_state(
            psql_exe,
            raw_settings["host"],
            PG_PORT,
            raw_settings["adminUser"],
            raw_settings["adminPassword"],
            SEED_DATABASE,
            repo_root,
        )

        # 8. Launch owned Angular UI on 127.0.0.1:4610 proxying /api -> 127.0.0.1:5590 and run read-only Edge smoke
        web_dir = repo_root / "web"
        ng_cli = web_dir / "node_modules" / "@angular" / "cli" / "bin" / "ng.js"
        ui_env = dict(os.environ)
        ui_env["ELEDGERCARE_API_PORT"] = str(API_PORT)
        ui_env["NG_CLI_ANALYTICS"] = "false"

        ui_fh = ui_log_file.open("w", encoding="utf-8", newline="\n")
        ui_proc = subprocess.Popen(
            ["node", str(ng_cli), "serve", "--host", "127.0.0.1", "--port", str(UI_PORT), "--proxy-config", "proxy.conf.mjs"],
            cwd=str(web_dir),
            env=ui_env,
            stdout=ui_fh,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )
        ui_deadline = time.monotonic() + 120.0
        ui_ready = False
        while time.monotonic() < ui_deadline:
            if ui_proc.poll() is not None:
                ui_fh.flush()
                raise RuntimeError(f"Angular dev UI exited early ({ui_proc.returncode})")
            try:
                st_ui, _, _ = http_request(f"http://127.0.0.1:{UI_PORT}/", timeout_s=2.0)
                if st_ui == 200:
                    ui_ready = True
                    break
            except Exception:
                pass
            time.sleep(0.3)
        if not ui_ready:
            raise RuntimeError(f"Owned Angular UI did not bind 127.0.0.1:{UI_PORT} within 120s")

        ui_proc_meta = inspect_process(ui_proc.pid, repo_root)
        scratch_dir = repo_root / ".scratch"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        edge_cfg_path = scratch_dir / "f4-prep-edge-cfg.json"
        edge_out_path = logs_dir.parent / "edge-ui-smoke-receipt.json"
        edge_cfg_path.write_text(
            json.dumps(
                {
                    "uiPort": UI_PORT,
                    "seed1DocumentId": doc1_id,
                    "seed5DocumentId": SEED5_DOC_ID,
                    "outputJsonPath": str(edge_out_path),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        edge_helper = Path(__file__).resolve().parent / "verify_f3_seed_ui_edge.mjs"
        edge_cp = run_cmd(["node", str(edge_helper), "--config", str(edge_cfg_path)], cwd=repo_root, timeout_s=120)
        edge_log_path = logs_dir / "03-edge-ui-readonly-smoke.log"
        edge_log_path.write_text(
            scrub_secrets(
                f"$ node {edge_helper.relative_to(repo_root).as_posix()} --config .scratch/f4-prep-edge-cfg.json\n"
                f"[exit={edge_cp.returncode}]\n--- STDOUT ---\n{edge_cp.stdout}\n--- STDERR ---\n{edge_cp.stderr}",
                secrets_to_scrub,
            ),
            encoding="utf-8",
            newline="\n",
        )
        if edge_cp.returncode != 0:
            raise RuntimeError(f"Edge UI read-only smoke failed ({edge_cp.returncode}): {edge_cp.stderr}")

        edge_receipt = json.loads(edge_out_path.read_text(encoding="utf-8"))
        ocr_workers_during_run = count_ocr_worker_processes(repo_root)

        stop_proc_tree(ui_proc, repo_root)
        ui_proc = None
        if ui_fh:
            ui_fh.close()
            ui_fh = None

        db_after_ui = query_canonical_f3_db_state(
            psql_exe,
            raw_settings["host"],
            PG_PORT,
            raw_settings["adminUser"],
            raw_settings["adminPassword"],
            SEED_DATABASE,
            repo_root,
        )

        api_operations = {
            "api_process": api_proc_meta,
            "ui_process": ui_proc_meta,
            "api_port": API_PORT,
            "ui_port": UI_PORT,
            "local_ocr_enabled": False,
            "observed_ocr_worker_processes": ocr_workers_during_run,
            "seed7_real_intake": {
                "idempotency_key": SEED7_SUB_KEY,
                "created_status": st_sub7,
                "document_id": seed7_doc_id,
                "job_id": body_sub7["jobId"],
                "replay_status": st_rep7,
                "replay_same_document_id": body_rep7["documentId"] == seed7_doc_id,
                "disabled_ocr_post_extraction_status": st_ext_req7,
                "disabled_ocr_post_extraction_code": body_ext_req7.get("code"),
                "uncompleted_get_review_status": st_rev_7,
                "uncompleted_get_review_code": body_rev_7.get("code"),
            },
            "seed6_failed_get_review": {
                "document_id": SEED6_DOC_ID,
                "status": st_rev_6,
                "code": body_rev_6.get("code"),
            },
            "f3_review_revisions_created_via_api": [
                {"seed_index": 1, "document_id": doc1_id, "revision_number": 1, "status": "reviewed", "http_status": st_s1_r1, "revision_id": resp_s1_r1["revision"]["revisionId"]},
                {"seed_index": 1, "document_id": doc1_id, "revision_number": 2, "status": "reviewed", "http_status": st_s1_r2, "revision_id": resp_s1_r2["revision"]["revisionId"]},
                {"seed_index": 1, "document_id": doc1_id, "revision_number": 3, "status": "draft", "http_status": st_s1_r3, "revision_id": resp_s1_r3["revision"]["revisionId"]},
                {"seed_index": 3, "document_id": doc3_id, "revision_number": 1, "status": "draft", "http_status": st_s3_r1, "revision_id": resp_s3_r1["revision"]["revisionId"]},
                {"seed_index": 3, "document_id": doc3_id, "revision_number": 2, "status": "reviewed", "http_status": st_s3_r2, "revision_id": resp_s3_r2["revision"]["revisionId"]},
                {"seed_index": 4, "document_id": SEED4_DOC_ID, "revision_number": 1, "status": "draft", "http_status": st_s4_r1, "revision_id": resp_s4_r1["revision"]["revisionId"]},
                {"seed_index": 5, "document_id": SEED5_DOC_ID, "revision_number": 1, "status": "reviewed", "http_status": st_s5_r1, "revision_id": resp_s5_r1["revision"]["revisionId"]},
            ],
            "seed1_rev2_historical_replay_after_rev3_head": {
                "http_status": st_s1_r2_rep,
                "replayed": resp_s1_r2_rep["replayed"],
                "is_current_head": resp_s1_r2_rep["isCurrentHead"],
                "current_revision_number": resp_s1_r2_rep["currentRevisionNumber"],
                "current_review_state": resp_s1_r2_rep["currentReviewState"],
            },
            "verified_documents": verified_docs,
            "edge_ui_readonly_smoke": edge_receipt,
        }
        return api_operations, db_before_ui, db_after_ui, {"seed7_document_id": seed7_doc_id, "seed7_job_id": body_sub7["jobId"]}
    finally:
        stop_proc_tree(ui_proc, repo_root)
        if ui_fh:
            ui_fh.close()
        stop_proc_tree(api_proc, repo_root)
        api_fh.close()
        for lf in (api_log_file, ui_log_file):
            if lf.is_file():
                cleaned = scrub_secrets(lf.read_text(encoding="utf-8", errors="replace"), secrets_to_scrub).replace("\r\n", "\n")
                lf.write_bytes(cleaned.encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Output JSON receipt path")
    parser.add_argument("--require-clean", action="store_true", help="Require clean git status before decisive execution")
    args = parser.parse_args(argv)

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[6]
    local_dir = repo_root / ".local"
    local_tools = local_dir / "tools"
    pg_data = local_dir / "postgres-data"
    settings_path = local_dir / "secrets" / "pg-local.json"
    psql_exe = local_tools / "pgsql-18.7-1" / "bin" / "psql.exe"
    pg_ctl_exe = local_tools / "pgsql-18.7-1" / "bin" / "pg_ctl.exe"

    out_path = Path(args.output).resolve()
    logs_dir = out_path.parent / "logs"

    head_sha = run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD"], cwd=repo_root).stdout.strip()
    branch = run_cmd(["git", "--no-optional-locks", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root).stdout.strip()
    git_status_before = run_cmd(
        ["git", "--no-optional-locks", "status", "--porcelain=v1", "--untracked-files=normal"], cwd=repo_root
    ).stdout.strip()
    if args.require_clean and git_status_before != "":
        raise RuntimeError(f"Expected clean git worktree before decisive execution, got:\n{git_status_before}")

    # Verify zero diff outside docs/implementation/WP-0010/eld-f4-implementer/preparation/ relative to merged coordinator authority
    diff_outside = run_cmd(
        ["git", "--no-optional-locks", "diff", "--name-only", MERGED_COORDINATOR_AUTHORITY_SHA, head_sha],
        cwd=repo_root,
    ).stdout.strip()
    outside_paths = [
        p
        for p in diff_outside.splitlines()
        if p and not p.startswith("docs/implementation/WP-0010/eld-f4-implementer/preparation/")
    ]
    if outside_paths:
        raise RuntimeError(f"Prohibited modifications outside owned preparation directory: {outside_paths}")

    protected_trees = {
        "src": run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD:src"], cwd=repo_root).stdout.strip(),
        "web": run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD:web"], cwd=repo_root).stdout.strip(),
        "tests": run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD:tests"], cwd=repo_root).stdout.strip(),
        "deploy": run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD:deploy"], cwd=repo_root).stdout.strip(),
        "ELedgerCare.slnx": run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD:ELedgerCare.slnx"], cwd=repo_root).stdout.strip(),
        "workers_local_ocr": run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD:workers/local_ocr"], cwd=repo_root).stdout.strip(),
        "evaluation": run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD:evaluation"], cwd=repo_root).stdout.strip(),
        "qualification": run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD:qualification"], cwd=repo_root).stdout.strip(),
        "research": run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD:research"], cwd=repo_root).stdout.strip(),
        "docs_design": run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD:docs/design"], cwd=repo_root).stdout.strip(),
        "docs_coordination": run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD:docs/coordination"], cwd=repo_root).stdout.strip(),
        "docs_kickoffs": run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD:docs/kickoffs"], cwd=repo_root).stdout.strip(),
        "docs_agent_reports": run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD:docs/agent-reports"], cwd=repo_root).stdout.strip(),
    }

    raw_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    secrets_to_scrub = [
        str(raw_settings.get("adminPassword", "")),
        str(raw_settings.get("migratorPassword", "")),
        str(raw_settings.get("appPassword", "")),
    ]
    if any(len(s) < 32 for s in secrets_to_scrub) or len(set(secrets_to_scrub)) != 3:
        raise RuntimeError("Owned cluster credentials do not meet >=32-char distinct secret requirement.")
    if int(raw_settings["port"]) != PG_PORT or raw_settings["host"] != "127.0.0.1":
        raise RuntimeError(f"Owned cluster settings must bind strictly to 127.0.0.1:{PG_PORT}.")

    pg_subset_report = verify_pg_subset(local_tools, repo_root)
    nuget_audit = verify_nuget_locks(repo_root, local_dir / "nuget" / "packages")

    ports_before = observe_ports(AUTHOR_PORTS, repo_root)
    if any(ports_before[str(p)] for p in AUTHOR_PORTS):
        raise RuntimeError(f"Expected author ports {AUTHOR_PORTS} unbound before start, got: {ports_before}")

    if logs_dir.exists():
        shutil.rmtree(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    start_script = repo_root / "deploy" / "dev" / "postgres" / "start-cluster.ps1"
    stop_script = repo_root / "deploy" / "dev" / "postgres" / "stop-cluster.ps1"
    prepare_db_script = repo_root / "deploy" / "dev" / "database" / "prepare-database.ps1"

    dotnet_env = dict(os.environ)
    dotnet_env["NUGET_PACKAGES"] = str(local_dir / "nuget" / "packages")
    dotnet_env["DOTNET_CLI_HOME"] = str(local_dir / "dotnet-home")
    dotnet_env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    dotnet_env["DOTNET_NOLOGO"] = "1"

    postmaster_info = None
    ports_during_pg = None
    server_settings: dict[str, str] = {}
    privilege_matrix_lines: list[str] = []
    negative_privilege_probes: dict[str, dict] = {}
    api_operations = None
    db_before_ui = None
    db_after_ui = None
    seed_manifest = None
    seed7_ids = None
    stop_exit_code = None

    start_cp = run_cmd(["pwsh", "-NoProfile", "-File", str(start_script)], cwd=repo_root)
    (logs_dir / "01-pg-cluster-start.log").write_text(
        scrub_secrets(
            f"$ pwsh -NoProfile -File deploy/dev/postgres/start-cluster.ps1\n[exit={start_cp.returncode}]\n{start_cp.stdout}\n{start_cp.stderr}",
            secrets_to_scrub,
        ).replace("\r\n", "\n"),
        encoding="utf-8",
        newline="\n",
    )
    if start_cp.returncode != 0:
        raise RuntimeError(f"start-cluster.ps1 failed ({start_cp.returncode}): {start_cp.stderr}")

    try:
        pm_pid = int((pg_data / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        postmaster_info = inspect_process(pm_pid, repo_root)
        if postmaster_info is None:
            raise RuntimeError(f"Started postmaster PID {pm_pid} not found.")
        ports_during_pg = observe_ports(AUTHOR_PORTS, repo_root)

        settings_rows = invoke_psql(
            psql_exe,
            raw_settings["host"],
            PG_PORT,
            raw_settings["adminUser"],
            raw_settings["adminPassword"],
            "postgres",
            "SELECT name || '=' || setting FROM pg_settings "
            "WHERE name IN ('server_version','listen_addresses','port','password_encryption',"
            "'fsync','full_page_writes','synchronous_commit','wal_level','data_checksums','default_transaction_isolation') "
            "ORDER BY name;",
            repo_root,
        ).stdout.strip()
        for line in settings_rows.splitlines():
            k, v = line.split("=", 1)
            server_settings[k] = v

        # Drop (if exists) and freshly prepare eledgercare_f4_author_seed_f3 with unchanged F1+F2+F3 migrations + grant-runtime.sql
        invoke_psql(
            psql_exe,
            raw_settings["host"],
            PG_PORT,
            raw_settings["adminUser"],
            raw_settings["adminPassword"],
            "postgres",
            f"DROP DATABASE IF EXISTS {SEED_DATABASE} WITH (FORCE);",
            repo_root,
        )
        prep_cp = run_cmd(
            ["pwsh", "-NoProfile", "-File", str(prepare_db_script), "-Database", SEED_DATABASE],
            cwd=repo_root,
            env=dotnet_env,
            timeout_s=180,
        )
        (logs_dir / "02-prepare-f3-seed-db.log").write_text(
            scrub_secrets(
                f"$ pwsh -NoProfile -File deploy/dev/database/prepare-database.ps1 -Database {SEED_DATABASE}\n"
                f"[exit={prep_cp.returncode}]\n--- STDOUT ---\n{prep_cp.stdout}\n--- STDERR ---\n{prep_cp.stderr}",
                secrets_to_scrub,
            ).replace("\r\n", "\n"),
            encoding="utf-8",
            newline="\n",
        )
        if prep_cp.returncode != 0:
            raise RuntimeError(f"prepare-database.ps1 failed ({prep_cp.returncode}): {prep_cp.stderr}\n{prep_cp.stdout}")
        privilege_matrix_lines = [ln.strip() for ln in prep_cp.stdout.splitlines() if ln.strip()]

        # Seed extraction/attempt records (Seeds 1..6) strictly as least-privilege runtime role eledgercare_app
        seed_sql, seed_manifest = build_seed_sql(repo_root)
        invoke_psql(
            psql_exe,
            raw_settings["host"],
            PG_PORT,
            raw_settings["appUser"],
            raw_settings["appPassword"],
            SEED_DATABASE,
            seed_sql,
            repo_root,
        )

        # Negative privilege probes across F1 + F2 + F3 tables as eledgercare_app
        neg_queries = {
            "deny_update_original_artifacts": "UPDATE eledgercare.original_artifacts SET media_type = 'application/pdf';",
            "deny_update_extraction_results": "UPDATE eledgercare.extraction_results SET finish_reason = 'stop';",
            "deny_update_documents": "UPDATE eledgercare.documents SET submitted_at = now();",
            "deny_delete_extraction_results": "DELETE FROM eledgercare.extraction_results WHERE false;",
            "deny_update_review_revisions": "UPDATE eledgercare.work_order_review_revisions SET status = 'draft' WHERE false;",
            "deny_update_review_fields": "UPDATE eledgercare.work_order_review_fields SET human_value = 'x' WHERE false;",
            "deny_update_review_head_immutable_col": "UPDATE eledgercare.work_order_review_heads SET profile_id = 'x' WHERE false;",
            "deny_select_ef_migrations_history": "SELECT 1 FROM eledgercare.__ef_migrations_history;",
            "deny_create_table": "CREATE TABLE eledgercare.unauthorized_probe (id int);",
        }
        for pname, nsql in neg_queries.items():
            ncp = invoke_psql(
                psql_exe,
                raw_settings["host"],
                PG_PORT,
                raw_settings["appUser"],
                raw_settings["appPassword"],
                SEED_DATABASE,
                nsql,
                repo_root,
                expect_error=True,
            )
            negative_privilege_probes[pname] = {
                "rejected": ncp.returncode != 0 and "permission denied" in ncp.stderr.lower(),
                "exit_code": ncp.returncode,
            }

        app_conn_str = (
            f"Host=127.0.0.1;Port={PG_PORT};Database={SEED_DATABASE};"
            f"Username={raw_settings['appUser']};Password={raw_settings['appPassword']}"
        )
        api_operations, db_before_ui, db_after_ui, seed7_ids = execute_api_seed_and_ui_smoke(
            repo_root,
            app_conn_str,
            seed_manifest,
            logs_dir,
            secrets_to_scrub,
            psql_exe,
            raw_settings,
        )
        seed_manifest["api_submitted_seed_7"] = {
            "seed_index": 7,
            "label": "f1_unprocessed_submitted_via_real_api",
            "document_id": seed7_ids["seed7_document_id"],
            "idempotency_key": SEED7_SUB_KEY,
            "job_id": seed7_ids["seed7_job_id"],
            "fixture": "tests/fixtures/F1-SWO-001.pdf",
            "input_sha256": F1_PDF_SHA256,
            "pages": 1,
            "status": "awaiting_extraction",
            "ids_remapped": False,
        }
    finally:
        stop_cp = run_cmd(["pwsh", "-NoProfile", "-File", str(stop_script)], cwd=repo_root)
        stop_exit_code = stop_cp.returncode
        (logs_dir / "04-pg-cluster-stop.log").write_text(
            scrub_secrets(
                f"$ pwsh -NoProfile -File deploy/dev/postgres/stop-cluster.ps1\n[exit={stop_cp.returncode}]\n{stop_cp.stdout}\n{stop_cp.stderr}",
                secrets_to_scrub,
            ).replace("\r\n", "\n"),
            encoding="utf-8",
            newline="\n",
        )

    # Clean up temporary .scratch directory so zero transient files remain
    scratch_dir = repo_root / ".scratch"
    scratch_existed = scratch_dir.exists()
    if scratch_existed:
        shutil.rmtree(scratch_dir)

    pg_ctl_after = run_cmd([str(pg_ctl_exe), "status", "-D", str(pg_data)], cwd=repo_root)
    pm_after = inspect_process(postmaster_info["pid"], repo_root) if postmaster_info else None
    pm_alive_after = pm_after is not None and pm_after.get("startUtc") == postmaster_info.get("startUtc")

    api_pid_done = api_operations["api_process"]["pid"] if api_operations and api_operations["api_process"] else None
    api_after = inspect_process(api_pid_done, repo_root) if api_pid_done else None
    api_alive_after = (
        api_after is not None
        and api_operations is not None
        and api_after.get("startUtc") == api_operations["api_process"].get("startUtc")
    )

    ui_pid_done = api_operations["ui_process"]["pid"] if api_operations and api_operations["ui_process"] else None
    ui_after = inspect_process(ui_pid_done, repo_root) if ui_pid_done else None
    ui_alive_after = (
        ui_after is not None
        and api_operations is not None
        and ui_after.get("startUtc") == api_operations["ui_process"].get("startUtc")
    )

    ports_after = wait_ports_unbound(AUTHOR_PORTS, repo_root)
    ocr_workers_after = count_ocr_worker_processes(repo_root)

    sdk_ver = run_cmd(["dotnet", "--version"], cwd=repo_root, env=dotnet_env).stdout.strip()
    ef_cp = run_cmd(["dotnet", "tool", "run", "dotnet-ef", "--version"], cwd=repo_root, env=dotnet_env)
    ef_ver = ef_cp.stdout.strip().splitlines()[-1].strip() if ef_cp.returncode == 0 and ef_cp.stdout.strip() else ""
    node_ver = run_cmd(["node", "--version"], cwd=repo_root).stdout.strip()
    npm_ver = run_cmd(["npm.cmd", "--version"], cwd=repo_root).stdout.strip()
    pw_cli = repo_root / "web" / "node_modules" / "@playwright" / "test" / "cli.js"
    pw_ver = run_cmd(["node", str(pw_cli), "--version"], cwd=repo_root / "web").stdout.strip() if pw_cli.is_file() else ""
    ng_pkg = repo_root / "web" / "node_modules" / "@angular" / "cli" / "package.json"
    ng_ver = json.loads(ng_pkg.read_text(encoding="utf-8"))["version"] if ng_pkg.is_file() else ""
    py_ver = sys.version.split()[0]
    edge_path = next(
        (
            p
            for p in (
                Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
                Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            )
            if p.is_file()
        ),
        None,
    )
    edge_ver = (
        run_cmd(
            ["pwsh", "-NoProfile", "-Command", f"(Get-Item -LiteralPath '{edge_path}').VersionInfo.ProductVersion"],
            cwd=repo_root,
        ).stdout.strip()
        if edge_path
        else ""
    )

    snap = db_after_ui["snapshot"]
    counts = snap["row_counts"]
    api_docs = api_operations["verified_documents"]
    heads_by_doc = {h["document_id"]: h for h in snap["review_heads"]}

    assertions = {
        "clean_git_before_decisive_execution": not args.require_clean or git_status_before == "",
        "zero_changes_outside_owned_preparation_dir": len(outside_paths) == 0,
        "pg_subset_1597_files_and_authenticode_valid": (
            pg_subset_report["expected_subset_manifest_sha256_match"]
            and pg_subset_report["expected_central_directory_sha256_match"]
            and pg_subset_report["verified_file_count"] == EXPECTED_PG_FILES
            and pg_subset_report["verified_total_bytes"] == EXPECTED_PG_BYTES
            and not pg_subset_report["missing_files"]
            and not pg_subset_report["extra_files"]
            and not pg_subset_report["hash_or_crc_mismatches"]
            and not pg_subset_report["reparse_points"]
            and all(v["status"] == "Valid" for v in pg_subset_report["authenticode_core_binaries"].values())
        ),
        "ports_5590_4610_55438_free_before_start": all(not ports_before[str(p)] for p in AUTHOR_PORTS),
        "pg_55438_durability_scram_and_c_locale_verified": (
            ports_during_pg is not None
            and len(ports_during_pg[str(PG_PORT)]) == 1
            and ports_during_pg[str(PG_PORT)][0]["localAddress"] == "127.0.0.1"
            and server_settings.get("server_version") == "18.7"
            and server_settings.get("port") == str(PG_PORT)
            and server_settings.get("password_encryption") == "scram-sha-256"
            and server_settings.get("fsync") == "on"
            and server_settings.get("full_page_writes") == "on"
            and server_settings.get("synchronous_commit") == "on"
            and snap["collation"] == {"datcollate": "C", "datctype": "C", "encoding": "UTF8"}
        ),
        "unchanged_f1_f2_f3_migrations_only": snap["migrations"] == [
            "20261114182147_InitialDurableIntake",
            "20261116052029_AddLocalExtraction",
            "20261116200918_AddWorkOrderReview",
        ],
        "seed_row_counts_and_fencing_sequence_7": (
            counts
            == {
                "documents": 7,
                "original_artifacts": 7,
                "processing_jobs": 7,
                "execution_attempts": 7,
                "extraction_results": 5,
                "work_order_review_heads": 4,
                "work_order_review_revisions": 7,
                "work_order_review_fields": 35,
            }
            and snap["sequence"] == {"last_value": 7, "is_called": True}
        ),
        "pg_bytea_sha256_exact_parity_all_originals_and_results": (
            all(
                d["byte_length"] == d["octet_length"] and d["declared_sha256"] == d["computed_sha256"]
                for d in snap["documents"]
            )
            and all(
                r["raw_output_byte_length"] == r["raw_octet_length"]
                and r["declared_raw_sha256"] == r["computed_raw_sha256"]
                for r in snap["results"]
            )
            and [r["computed_raw_sha256"] for r in snap["results"]]
            == [F01_RAW_SHA256, F07_RAW_SHA256, F01_RAW_SHA256, F01_RAW_SHA256, F07_RAW_SHA256]
        ),
        "f3_review_states_and_greatest_reviewed_vs_newer_draft_verified": (
            heads_by_doc["01a1e571-2838-714b-861b-bf0835d7c90a"]["current_revision_number"] == 3
            and heads_by_doc["01a1e571-2838-714b-861b-bf0835d7c90a"]["current_status"] == "draft"
            and heads_by_doc["01a1e571-2838-714b-861b-bf0835d7c90a"]["greatest_reviewed_revision_number"] == 2
            and heads_by_doc["01a1e578-8f3a-7e0c-826b-a2c9dc066a8f"]["current_revision_number"] == 2
            and heads_by_doc["01a1e578-8f3a-7e0c-826b-a2c9dc066a8f"]["current_status"] == "reviewed"
            and heads_by_doc["01a1e578-8f3a-7e0c-826b-a2c9dc066a8f"]["greatest_reviewed_revision_number"] == 2
            and heads_by_doc[SEED4_DOC_ID]["current_revision_number"] == 1
            and heads_by_doc[SEED4_DOC_ID]["current_status"] == "draft"
            and heads_by_doc[SEED4_DOC_ID]["greatest_reviewed_revision_number"] is None
            and heads_by_doc[SEED5_DOC_ID]["current_revision_number"] == 1
            and heads_by_doc[SEED5_DOC_ID]["current_status"] == "reviewed"
            and heads_by_doc[SEED5_DOC_ID]["greatest_reviewed_revision_number"] == 1
        ),
        "least_privilege_negative_probes_all_9_denied": all(
            v["rejected"] for v in negative_privilege_probes.values()
        ),
        "disabled_ocr_api_5590_and_edge_4610_parity_with_zero_ui_db_mutation": (
            db_before_ui["canonical_sha256"] == db_after_ui["canonical_sha256"]
            and len(api_docs) == 7
            and all(
                d["get_document_status"] == 200
                and d["get_extraction_status"] == 200
                and d["get_submission_status"] == 200
                and d["get_original_status"] == 200
                and d["get_preview_status"] == 200
                and d["preview_exact_match"] is True
                and d["worker_enabled"] is False
                and d["can_request_extraction"] is False
                and d["can_retry_extraction"] is False
                and d["submission_matches_doc_id"] is True
                for d in api_docs
            )
            and api_operations["seed7_real_intake"]["disabled_ocr_post_extraction_status"] == 503
            and api_operations["seed7_real_intake"]["uncompleted_get_review_status"] == 409
            and api_operations["seed6_failed_get_review"]["status"] == 409
            and api_operations["edge_ui_readonly_smoke"]["ok"] is True
            and api_operations["observed_ocr_worker_processes"] == 0
            and ocr_workers_after == 0
        ),
        "all_owned_services_stopped_ports_unbound_scratch_cleaned_and_seed_retained": (
            stop_exit_code == 0
            and pg_ctl_after.returncode != 0
            and not (pg_data / "postmaster.pid").exists()
            and not pm_alive_after
            and not api_alive_after
            and not ui_alive_after
            and all(not ports_after[str(p)] for p in AUTHOR_PORTS)
            and not scratch_dir.exists()
            and (pg_data / "PG_VERSION").read_text(encoding="utf-8").strip() == "18"
        ),
        "offline_toolchain_and_locked_caches_ready": (
            sdk_ver == "10.0.403"
            and ef_ver == "10.0.15"
            and nuget_audit["lockfile_count"] == 7
            and nuget_audit["package_entries_checked"] == 126
            and not nuget_audit["missing_cached_packages"]
            and not nuget_audit["content_hash_mismatches"]
            and node_ver == "v24.18.0"
            and npm_ver == "11.16.0"
            and ng_ver == "22.2.7"
            and "1.65.1" in pw_ver
            and edge_path is not None
        ),
    }

    helper_bytes = script_path.read_bytes()
    edge_helper_path = script_path.parent / "verify_f3_seed_ui_edge.mjs"
    edge_helper_bytes = edge_helper_path.read_bytes()

    receipt = {
        "schema": "eledgercare.wp-0010.f4-author-seed-preparation-receipt/1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "author": "eld-f4-implementer",
        "conversation_id": "b7c54417-db09-49bd-8d2b-7cc808f113be",
        "model": "Gemini 4 Carbon (High)",
        "effort": "high",
        "branch": branch,
        "initial_base_sha": INITIAL_BASE_SHA,
        "initial_authority_sha": INITIAL_AUTHORITY_SHA,
        "merged_coordinator_authority_sha": MERGED_COORDINATOR_AUTHORITY_SHA,
        "frozen_helper_head_sha": head_sha,
        "helpers": {
            "python_seed_helper": {
                "path": "docs/implementation/WP-0010/eld-f4-implementer/preparation/helpers/prepare_and_verify_f3_seed.py",
                "bytes": len(helper_bytes),
                "sha256": sha256_hex(helper_bytes),
            },
            "node_edge_ui_smoke_helper": {
                "path": "docs/implementation/WP-0010/eld-f4-implementer/preparation/helpers/verify_f3_seed_ui_edge.mjs",
                "bytes": len(edge_helper_bytes),
                "sha256": sha256_hex(edge_helper_bytes),
            },
        },
        "scope_disclosure": (
            f"Test-only isolated pre-F4 author seed preparation in owned PostgreSQL 18.7 (127.0.0.1:{PG_PORT}, "
            f"retained database {SEED_DATABASE}), unchanged F3 API (127.0.0.1:{API_PORT}, LocalOcr:Enabled=false), "
            f"and read-only Angular/Microsoft Edge smoke (127.0.0.1:{UI_PORT}). Extraction rows for Seeds 1-5 are "
            "attributed test-only SQL imports of accepted WP-0006 F2 artifacts via runtime role eledgercare_app; "
            "Seed 6 is a deterministic failed-attempt diagnostic fixture; Seed 7 and all 7 review revisions are "
            "created through real unchanged F1/F3 HTTP API calls. Zero F4 production/test/deploy edits, zero "
            "GPU/model/worker calls, zero subagents, and zero canonical /003 claims."
        ),
        "protected_tree_oids": protected_trees,
        "postgres_binary_provenance": pg_subset_report,
        "toolchain_and_caches": {
            "dotnet_sdk": sdk_ver,
            "dotnet_ef_local_tool": ef_ver,
            "nuget_lock_audit": nuget_audit,
            "nodejs": node_ver,
            "npm": npm_ver,
            "angular_cli_local": ng_ver,
            "playwright_cli_local": pw_ver,
            "python": py_ver,
            "msedge_path": str(edge_path) if edge_path else None,
            "msedge_version": edge_ver,
        },
        "owned_cluster_and_services": {
            "host": "127.0.0.1",
            "configured_ports": {"api": API_PORT, "ui": UI_PORT, "postgres": PG_PORT},
            "retained_database": SEED_DATABASE,
            "credentials_distinct_min_32_chars": True,
            "secret_values_redacted": True,
            "ports_before_start": ports_before,
            "started_postmaster": postmaster_info,
            "ports_during_pg": ports_during_pg,
            "server_settings": server_settings,
            "privilege_matrix_summary": privilege_matrix_lines,
            "negative_privilege_probes": negative_privilege_probes,
            "api_and_ui_operations": api_operations,
            "stop_exit_code": stop_exit_code,
            "pg_ctl_status_rc_after_stop": pg_ctl_after.returncode,
            "postmaster_alive_after_stop": pm_alive_after,
            "api_5590_alive_after_stop": api_alive_after,
            "ui_4610_alive_after_stop": ui_alive_after,
            "ports_after_stop": ports_after,
            "scratch_existed_during_run": scratch_existed,
            "scratch_absent_after_cleanup": not scratch_dir.exists(),
            "retained_local_paths": {
                "pg_binaries": str(local_tools / "pgsql-18.7-1"),
                "pg_subset_manifest": str(local_tools / "pgsql-18.7-1.subset-manifest.json"),
                "pg_data_dir": str(pg_data),
                "pg_secrets_file": str(settings_path),
                "nuget_packages": str(local_dir / "nuget" / "packages"),
                "offline_nuget_config": str(local_dir / "nuget" / "offline.nuget.config"),
                "dotnet_cli_home": str(local_dir / "dotnet-home"),
                "npm_cache": str(local_dir / "npm-cache"),
                "web_node_modules": str(repo_root / "web" / "node_modules"),
            },
        },
        "seed_manifest": seed_manifest,
        "retained_f3_database_state": {
            "canonical_sha256_before_ui": db_before_ui["canonical_sha256"],
            "canonical_sha256_after_ui": db_after_ui["canonical_sha256"],
            "unchanged_across_readonly_ui_smoke": db_before_ui["canonical_sha256"] == db_after_ui["canonical_sha256"],
            "snapshot": snap,
        },
        "assertions": assertions,
        "assertion_count": len(assertions),
        "all_assertions_passed": all(assertions.values()),
    }

    serialized = json.dumps(receipt, indent=2, ensure_ascii=False).replace("\r\n", "\n") + "\n"
    for secret in secrets_to_scrub:
        if secret and secret in serialized:
            raise RuntimeError("Refusing to write receipt: secret substring detected!")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(serialized.encode("utf-8"))

    failed = [k for k, v in assertions.items() if not v]
    if failed:
        raise AssertionError(f"Preparation assertions failed: {failed}")
    print(f"OK: {len(assertions)} assertions passed; retained DB {SEED_DATABASE} canonical SHA-256 = {db_after_ui['canonical_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
