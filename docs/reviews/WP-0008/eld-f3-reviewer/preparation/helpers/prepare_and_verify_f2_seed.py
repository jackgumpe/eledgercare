"""Frozen decisive helper for WP-0008 independent F3 persistence & seed preparation.

Executes against owned reviewer resources ONLY (127.0.0.1:55437 PostgreSQL 18.7 and brief read-only
LocalOcr:Enabled=false API observation on 127.0.0.1:5490), constructs the attributed genuine F2
durable seed in owned database `eledgercare_f3_reviewer_seed_f2` using accepted F1/F2 migrations
and least-privilege `eledgercare_app` SQL, verifies byte/digest/sequence/privilege invariants and
live EF Core API deserialization, then stops all owned services cleanly while retaining the seeded
cluster on disk for future WP-0008 /004 forward-migration and F3 acceptance testing.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zlib

REVIEWER_PORTS = (5490, 4510, 55437)
SEED_DATABASE = "eledgercare_f3_reviewer_seed_f2"
EXPECTED_SUBSET_SHA = "47c3deb9c917f79c353b3683b2c2611ee975285ea06226c8f72444c96ce9051f"
EXPECTED_CD_SHA = "3132ca63b424f7ec371eabe50753ad7cd036278d942a6ea465547b17bf90a149"
EXPECTED_PG_FILES = 1597
EXPECTED_PG_BYTES = 151_078_582

PRIOR_DESIGN_002_SHA = "bff139bcdf55df77a821b858513b7e6bf5d96b87"
AUTHORITY_PREP_SHA = "ef152e1cfcc57b1404aa242a3e96d18843c4c10c"
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
SEED_DOC4_ID = "01a1e580-0000-7000-8000-000000000001"
SEED_DOC4_KEY = "01a1e580-0000-7000-8000-000000000002"
SEED_DOC4_JOB_ID = "01a1e580-0000-7000-8000-000000000003"
SEED_DOC4_SUBMITTED_UTC = "2026-11-16T17:51:00.000000+00:00"

FORBIDDEN_PATH_TOKENS = (
    "eld-f3-implementer",
    "eledgercare-mapping",
    "wp-0009/sealed",
    "wp-0009\\sealed",
    "wp-0009-fresh-families",
    "eld-eval-custodian",
    "eledgercare-f2",
)
REPARSE_ATTR = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
    timeout_s: int = 180,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        env=env,
        input=input_text,
        text=True,
        encoding="utf-8",
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
    f01_pdf = guard_owned_repo_path(repo_root, "tests/fixtures/SYN-WO-01-v1-raster300.pdf").read_bytes()
    f07_pdf = guard_owned_repo_path(repo_root, "tests/fixtures/SYN-MP-01-v0-clean.pdf").read_bytes()
    f1_pdf = guard_owned_repo_path(repo_root, "tests/fixtures/F1-SWO-001.pdf").read_bytes()
    assert sha256_hex(f01_pdf) == F01_PDF_SHA256 and len(f01_pdf) == 372258
    assert sha256_hex(f07_pdf) == F07_PDF_SHA256 and len(f07_pdf) == 8422
    assert sha256_hex(f1_pdf) == F1_PDF_SHA256 and len(f1_pdf) == 887

    trial = json.loads(
        guard_owned_repo_path(
            repo_root,
            "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/trial-summary-reviewer-v2.json",
        ).read_text(encoding="utf-8")
    )
    runs_dir = "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs"

    raw_s1 = guard_owned_repo_path(
        repo_root, f"{runs_dir}/attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4/output/raw_output.utf8.bin"
    ).read_bytes()
    env_s1 = json.loads(
        guard_owned_repo_path(
            repo_root, f"{runs_dir}/attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4/output/envelope.json"
        ).read_text(encoding="utf-8")
    )
    raw_s2 = guard_owned_repo_path(
        repo_root, f"{runs_dir}/attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d/output/raw_output.utf8.bin"
    ).read_bytes()
    env_s2 = json.loads(
        guard_owned_repo_path(
            repo_root, f"{runs_dir}/attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d/output/envelope.json"
        ).read_text(encoding="utf-8")
    )
    raw_s4 = guard_owned_repo_path(
        repo_root, f"{runs_dir}/attempt-01a1e579-4599-7bed-acdc-2863c448c6fa/output/raw_output.utf8.bin"
    ).read_bytes()
    env_s4 = json.loads(
        guard_owned_repo_path(
            repo_root, f"{runs_dir}/attempt-01a1e579-4599-7bed-acdc-2863c448c6fa/output/envelope.json"
        ).read_text(encoding="utf-8")
    )

    assert sha256_hex(raw_s1) == F01_RAW_SHA256 == sha256_hex(raw_s4) and len(raw_s1) == 3236
    assert sha256_hex(raw_s2) == F07_RAW_SHA256 and len(raw_s2) == 7511

    sc1 = trial["scenarios"]["1_f01_single_page_complete"]
    sc2 = trial["scenarios"]["2_f07_three_page_complete"]
    sc3 = trial["scenarios"]["3_live_supervisor_kill_and_explicit_retry"]

    f01_hex = f01_pdf.hex()
    f07_hex = f07_pdf.hex()
    f1_hex = f1_pdf.hex()
    raw_s1_hex = raw_s1.hex()
    raw_s2_hex = raw_s2.hex()
    raw_s4_hex = raw_s4.hex()

    def result_insert_sql(doc_id: str, job_id: str, db_res: dict, env_doc: dict, raw_hex: str) -> str:
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
    {sql_literal(db_res['result_id'])},
    {sql_literal(doc_id)},
    {sql_literal(job_id)},
    {sql_literal(db_res['attempt_id'])},
    {int(db_res['fencing_token'])},
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
    {sql_literal(env_doc['timings']['started_at_utc'])},
    {sql_literal(env_doc['timings']['completed_at_utc'])},
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

-- Seed 1: Genuine accepted F2 Scenario 1 (SYN-WO-01-v1-raster300.pdf, 1p completed, token 1)
INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
VALUES ({sql_literal(doc1_id)}, {sql_literal(sc1['submission']['idempotency_key'])}, {sql_literal(sub1_ts)});

INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
VALUES ({sql_literal(doc1_id)}, decode({sql_literal(f01_hex)}, 'hex'), decode({sql_literal(F01_PDF_SHA256)}, 'hex'), 372258, 'application/pdf', 1);

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

{result_insert_sql(doc1_id, job1_id, res1, env_s1, raw_s1_hex)}

-- Seed 2: Genuine accepted F2 Scenario 2 (SYN-MP-01-v0-clean.pdf, 3p completed, token 2)
INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
VALUES ({sql_literal(doc2_id)}, {sql_literal(sc2['submission']['idempotency_key'])}, {sql_literal(sub2_ts)});

INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
VALUES ({sql_literal(doc2_id)}, decode({sql_literal(f07_hex)}, 'hex'), decode({sql_literal(F07_PDF_SHA256)}, 'hex'), 8422, 'application/pdf', 3);

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

{result_insert_sql(doc2_id, job2_id, res2, env_s2, raw_s2_hex)}

-- Seed 3: Genuine accepted F2 Scenario 3 (SYN-WO-01-v1-raster300.pdf, Attempt #1 interrupted token 3 + Attempt #2 completed token 4)
INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
VALUES ({sql_literal(doc3_id)}, {sql_literal(sc3['submission']['idempotency_key'])}, {sql_literal(sub3_ts)});

INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
VALUES ({sql_literal(doc3_id)}, decode({sql_literal(f01_hex)}, 'hex'), decode({sql_literal(F01_PDF_SHA256)}, 'hex'), 372258, 'application/pdf', 1);

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

{result_insert_sql(doc3_id, job3_id, res3, env_s4, raw_s4_hex)}

-- Seed 4: Genuine F1-SWO-001 awaiting_extraction baseline row for F3 forward-migration & non-completed rejection check
INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
VALUES ({sql_literal(SEED_DOC4_ID)}, {sql_literal(SEED_DOC4_KEY)}, {sql_literal(SEED_DOC4_SUBMITTED_UTC)});

INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
VALUES ({sql_literal(SEED_DOC4_ID)}, decode({sql_literal(f1_hex)}, 'hex'), decode({sql_literal(F1_PDF_SHA256)}, 'hex'), 887, 'application/pdf', 1);

INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at, updated_at)
VALUES ({sql_literal(SEED_DOC4_JOB_ID)}, {sql_literal(SEED_DOC4_ID)}, 'awaiting_extraction', {sql_literal(SEED_DOC4_SUBMITTED_UTC)}, {sql_literal(SEED_DOC4_SUBMITTED_UTC)});

COMMIT;
"""

    manifest = {
        "attribution": {
            "imported_seed_only_not_new_inference": True,
            "f2_product_source_sha": F2_SOURCE_SHA,
            "f2_reviewer_executing_head_sha": F2_EXECUTING_HEAD_SHA,
            "f2_reviewer_runtime_evidence_sha": F2_REVIEWER_EVIDENCE_SHA,
            "f2_reviewer_report_004_sha": F2_REVIEWER_004_SHA,
            "identity_remapping": {
                "document_job_attempt_result_idempotency_ids": "exact_original_preserved_for_seeds_1_to_3",
                "synthesized_internal_supervisor_instance_ids": {
                    "api_rev_run1_pid_18496": SYNTHESIZED_SUPERVISOR_RUN1_INSTANCE_ID,
                    "api_rev_run2_pid_29208": SYNTHESIZED_SUPERVISOR_RUN2_INSTANCE_ID,
                    "reason": "Internal ExtractionAttemptCoordinator.supervisorInstanceId was not projected into trial-summary-reviewer-v2.json; deterministic UUIDs bound per historical supervisor PID.",
                },
                "seed_4_f1_awaiting_extraction_row": {
                    "document_id": SEED_DOC4_ID,
                    "idempotency_key": SEED_DOC4_KEY,
                    "job_id": SEED_DOC4_JOB_ID,
                    "fixture": "tests/fixtures/F1-SWO-001.pdf",
                    "sha256": F1_PDF_SHA256,
                    "purpose": "Pre-extraction F1 row to verify F3 forward migration and non-completed review rejection.",
                },
            },
        },
        "seeded_documents": [
            {
                "seed_index": 1,
                "document_id": doc1_id,
                "job_id": job1_id,
                "idempotency_key": sc1["submission"]["idempotency_key"],
                "fixture": "tests/fixtures/SYN-WO-01-v1-raster300.pdf",
                "input_sha256": F01_PDF_SHA256,
                "input_bytes": 372258,
                "pages": 1,
                "status": "completed",
                "attempt_ids": [att1["attempt_id"]],
                "fencing_tokens": [1],
                "result_id": res1["result_id"],
                "raw_output_sha256": F01_RAW_SHA256,
                "raw_output_bytes": 3236,
            },
            {
                "seed_index": 2,
                "document_id": doc2_id,
                "job_id": job2_id,
                "idempotency_key": sc2["submission"]["idempotency_key"],
                "fixture": "tests/fixtures/SYN-MP-01-v0-clean.pdf",
                "input_sha256": F07_PDF_SHA256,
                "input_bytes": 8422,
                "pages": 3,
                "status": "completed",
                "attempt_ids": [att2["attempt_id"]],
                "fencing_tokens": [2],
                "result_id": res2["result_id"],
                "raw_output_sha256": F07_RAW_SHA256,
                "raw_output_bytes": 7511,
            },
            {
                "seed_index": 3,
                "document_id": doc3_id,
                "job_id": job3_id,
                "idempotency_key": sc3["submission"]["idempotency_key"],
                "fixture": "tests/fixtures/SYN-WO-01-v1-raster300.pdf",
                "input_sha256": F01_PDF_SHA256,
                "input_bytes": 372258,
                "pages": 1,
                "status": "completed",
                "attempt_ids": [att3_int["attempt_id"], att4_ok["attempt_id"]],
                "fencing_tokens": [3, 4],
                "result_id": res3["result_id"],
                "raw_output_sha256": F01_RAW_SHA256,
                "raw_output_bytes": 3236,
            },
            {
                "seed_index": 4,
                "document_id": SEED_DOC4_ID,
                "job_id": SEED_DOC4_JOB_ID,
                "idempotency_key": SEED_DOC4_KEY,
                "fixture": "tests/fixtures/F1-SWO-001.pdf",
                "input_sha256": F1_PDF_SHA256,
                "input_bytes": 887,
                "pages": 1,
                "status": "awaiting_extraction",
                "attempt_ids": [],
                "fencing_tokens": [],
                "result_id": None,
                "raw_output_sha256": None,
                "raw_output_bytes": None,
            },
        ],
    }
    return sql, manifest


def query_db_snapshot(psql_exe: Path, host: str, port: int, user: str, password: str, db: str, cwd: Path) -> dict:
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
    raw = invoke_psql(psql_exe, host, port, user, password, db, snap_sql, cwd).stdout.strip()
    parsed = json.loads(raw)
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"snapshot": parsed, "state_sha256": sha256_hex(canonical)}


def http_get_json(url: str) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def http_get_bytes(url: str) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=20) as resp:
        headers = {k.lower(): v for k, v in resp.headers.items()}
        return resp.status, headers, resp.read()


def observe_disabled_ocr_api_5490(
    repo_root: Path,
    app_conn_str: str,
    seed_manifest: dict,
) -> dict:
    api_dir = repo_root / "src" / "ELedgerCare.Api" / "bin" / "Release" / "net10.0"
    api_dll = api_dir / "ELedgerCare.Api.dll"
    if not api_dll.is_file():
        raise FileNotFoundError(f"Built ELedgerCare.Api.dll missing at {api_dll}")

    env = dict(os.environ)
    env["ASPNETCORE_ENVIRONMENT"] = "Production"
    env["ConnectionStrings__Runtime"] = app_conn_str
    env["Api__Port"] = "5490"
    env["LocalOcr__Enabled"] = "false"
    env["DOTNET_NOLOGO"] = "1"
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"

    api_log_path = repo_root / ".scratch" / "prep-api-5490.log"
    api_log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fh = api_log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        ["dotnet", str(api_dll)],
        cwd=str(api_dir),
        env=env,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    api_pid = proc.pid
    api_proc_meta = None
    try:
        deadline = time.monotonic() + 45.0
        bound = False
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                log_fh.flush()
                out = api_log_path.read_text(encoding="utf-8", errors="replace")
                raise RuntimeError(f"API exited early ({proc.returncode}): {out}")
            ports_now = observe_ports((5490,), repo_root)
            if any(c["owningPid"] == api_pid for c in ports_now["5490"]):
                bound = True
                break
            time.sleep(0.2)
        if not bound:
            raise RuntimeError("Owned API did not bind 127.0.0.1:5490 within 45s")

        api_proc_meta = inspect_process(api_pid, repo_root)
        base_url = "http://127.0.0.1:5490"
        checks: list[dict] = []

        for item in seed_manifest["seeded_documents"]:
            doc_id = item["document_id"]
            st_doc, doc_body = http_get_json(f"{base_url}/api/documents/{doc_id}")
            st_ext, ext_body = http_get_json(f"{base_url}/api/documents/{doc_id}/extraction")
            st_sub, sub_body = http_get_json(f"{base_url}/api/submissions/{item['idempotency_key']}")
            st_orig, orig_headers, orig_bytes = http_get_bytes(f"{base_url}/api/documents/{doc_id}/original")

            res_obj = ext_body.get("result")
            checks.append({
                "seed_index": item["seed_index"],
                "document_id": doc_id,
                "get_document_status": st_doc,
                "get_extraction_status": st_ext,
                "get_submission_status": st_sub,
                "get_original_status": st_orig,
                "doc_wire_status": doc_body["status"],
                "worker_enabled": ext_body["workerEnabled"],
                "can_request_extraction": ext_body["canRequestExtraction"],
                "can_retry_extraction": ext_body["canRetryExtraction"],
                "attempt_count_api": len(ext_body["attempts"]),
                "accepted_result_id_api": doc_body["acceptedResultId"],
                "result_raw_sha256_api": res_obj["rawSha256"] if res_obj else None,
                "result_review_status_api": res_obj["reviewStatus"] if res_obj else None,
                "page_numbers_api": [p["pageNumber"] for p in res_obj["pages"]] if res_obj else [],
                "page_block_counts_api": [len(p["blocks"]) for p in res_obj["pages"]] if res_obj else [],
                "original_download_bytes": len(orig_bytes),
                "original_download_sha256": sha256_hex(orig_bytes),
                "original_nosniff": orig_headers.get("x-content-type-options"),
                "submission_matches_doc_id": sub_body["documentId"] == doc_id,
            })
        return {
            "api_process": api_proc_meta,
            "port": 5490,
            "local_ocr_enabled": False,
            "verified_documents": checks,
        }
    finally:
        current = inspect_process(api_pid, repo_root)
        if proc.poll() is None and current is not None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
        log_fh.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Output JSON receipt path")
    parser.add_argument("--require-clean", action="store_true", help="Require clean git status before writing receipt")
    args = parser.parse_args(argv)

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[6]
    local_dir = repo_root / ".local"
    local_tools = local_dir / "tools"
    pg_data = local_dir / "postgres-data"
    settings_path = local_dir / "secrets" / "pg-local.json"
    psql_exe = local_tools / "pgsql-18.7-1" / "bin" / "psql.exe"
    pg_ctl_exe = local_tools / "pgsql-18.7-1" / "bin" / "pg_ctl.exe"

    head_sha = run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD"], cwd=repo_root).stdout.strip()
    branch = run_cmd(["git", "--no-optional-locks", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root).stdout.strip()
    git_status_before = run_cmd(
        ["git", "--no-optional-locks", "status", "--porcelain=v1", "--untracked-files=normal"], cwd=repo_root
    ).stdout.strip()
    if args.require_clean and git_status_before != "":
        raise RuntimeError(f"Expected clean git worktree before decisive execution, got:\n{git_status_before}")

    # Verify immutable /002 and retained pre-freeze design failure log byte parity
    retained_fail_rel = "docs/reviews/WP-0008/eld-f3-reviewer/preparation/retained-failures/design-prefreeze-failure-01.txt"
    retained_fail_path = guard_owned_repo_path(repo_root, retained_fail_rel)
    retained_fail_bytes = retained_fail_path.read_bytes()
    retained_fail_sha = sha256_hex(retained_fail_bytes)
    scratch_fail_path = repo_root / ".scratch" / "pre-freeze-failure-01.txt"
    scratch_fail_match = scratch_fail_path.is_file() and scratch_fail_path.read_bytes() == retained_fail_bytes
    git_blob_cp = subprocess.run(
        ["git", "cat-file", "blob", f"HEAD:{retained_fail_rel}"],
        cwd=str(repo_root),
        capture_output=True,
        check=False,
    )
    git_blob_match = git_blob_cp.returncode == 0 and git_blob_cp.stdout == retained_fail_bytes

    imm_diff = run_cmd(
        [
            "git",
            "--no-optional-locks",
            "diff",
            "--name-status",
            PRIOR_DESIGN_002_SHA,
            head_sha,
            "--",
            "docs/agent-reports/eld-f3-reviewer/WP-0008/002_2026-11-16_review_eld-f3-reviewer.md",
            "docs/reviews/WP-0008/eld-f3-reviewer/design",
        ],
        cwd=repo_root,
    ).stdout.strip()

    raw_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    secrets_to_scrub = [
        str(raw_settings.get("adminPassword", "")),
        str(raw_settings.get("migratorPassword", "")),
        str(raw_settings.get("appPassword", "")),
    ]
    if any(len(s) < 32 for s in secrets_to_scrub) or len(set(secrets_to_scrub)) != 3:
        raise RuntimeError("Owned cluster credentials do not meet >=32-char distinct secret requirement.")
    if int(raw_settings["port"]) != 55437 or raw_settings["host"] != "127.0.0.1":
        raise RuntimeError("Owned cluster settings must bind strictly to 127.0.0.1:55437.")

    pg_subset_report = verify_pg_subset(local_tools, repo_root)
    nuget_audit = verify_nuget_locks(repo_root, local_dir / "nuget" / "packages")

    ports_before = observe_ports(REVIEWER_PORTS, repo_root)
    if any(ports_before[str(p)] for p in REVIEWER_PORTS):
        raise RuntimeError(f"Expected reviewer ports {REVIEWER_PORTS} unbound before start, got: {ports_before}")

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
    db_before_api = None
    db_after_api = None
    api_observation = None
    seed_manifest = None
    stop_exit_code = None

    start_cp = run_cmd(["pwsh", "-NoProfile", "-File", str(start_script)], cwd=repo_root)
    if start_cp.returncode != 0:
        raise RuntimeError(f"start-cluster.ps1 failed ({start_cp.returncode}): {start_cp.stderr}")

    try:
        pm_pid = int((pg_data / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
        postmaster_info = inspect_process(pm_pid, repo_root)
        if postmaster_info is None:
            raise RuntimeError(f"Started postmaster PID {pm_pid} not found.")
        ports_during_pg = observe_ports(REVIEWER_PORTS, repo_root)

        settings_rows = invoke_psql(
            psql_exe,
            raw_settings["host"],
            55437,
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

        # Drop & freshly prepare owned seed database with accepted F1+F2 migrations + grant-runtime.sql
        invoke_psql(
            psql_exe,
            raw_settings["host"],
            55437,
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
        if prep_cp.returncode != 0:
            raise RuntimeError(f"prepare-database.ps1 failed ({prep_cp.returncode}): {prep_cp.stderr}\n{prep_cp.stdout}")
        privilege_matrix_lines = [ln.strip() for ln in prep_cp.stdout.splitlines() if ln.strip()]

        # Seed the 4 genuine F1/F2 documents connected strictly as least-privilege runtime role eledgercare_app
        seed_sql, seed_manifest = build_seed_sql(repo_root)
        invoke_psql(
            psql_exe,
            raw_settings["host"],
            55437,
            raw_settings["appUser"],
            raw_settings["appPassword"],
            SEED_DATABASE,
            seed_sql,
            repo_root,
        )

        # Negative privilege probes as eledgercare_app
        neg_queries = {
            "deny_update_original_artifacts": "UPDATE eledgercare.original_artifacts SET media_type = 'application/pdf';",
            "deny_update_extraction_results": "UPDATE eledgercare.extraction_results SET finish_reason = 'stop';",
            "deny_update_documents": "UPDATE eledgercare.documents SET submitted_at = now();",
            "deny_delete_extraction_results": "DELETE FROM eledgercare.extraction_results WHERE false;",
            "deny_create_table": "CREATE TABLE eledgercare.unauthorized_probe (id int);",
        }
        for pname, nsql in neg_queries.items():
            ncp = invoke_psql(
                psql_exe,
                raw_settings["host"],
                55437,
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

        db_before_api = query_db_snapshot(
            psql_exe,
            raw_settings["host"],
            55437,
            raw_settings["adminUser"],
            raw_settings["adminPassword"],
            SEED_DATABASE,
            repo_root,
        )

        app_conn_str = (
            f"Host=127.0.0.1;Port=55437;Database={SEED_DATABASE};"
            f"Username={raw_settings['appUser']};Password={raw_settings['appPassword']}"
        )
        api_observation = observe_disabled_ocr_api_5490(repo_root, app_conn_str, seed_manifest)

        db_after_api = query_db_snapshot(
            psql_exe,
            raw_settings["host"],
            55437,
            raw_settings["adminUser"],
            raw_settings["adminPassword"],
            SEED_DATABASE,
            repo_root,
        )
    finally:
        stop_cp = run_cmd(["pwsh", "-NoProfile", "-File", str(stop_script)], cwd=repo_root)
        stop_exit_code = stop_cp.returncode

    pg_ctl_after = run_cmd([str(pg_ctl_exe), "status", "-D", str(pg_data)], cwd=repo_root)
    pm_after = inspect_process(postmaster_info["pid"], repo_root) if postmaster_info else None
    pm_alive_after = pm_after is not None and pm_after.get("startUtc") == postmaster_info.get("startUtc")
    api_pid_done = api_observation["api_process"]["pid"] if api_observation and api_observation["api_process"] else None
    api_after = inspect_process(api_pid_done, repo_root) if api_pid_done else None
    api_alive_after = (
        api_after is not None
        and api_observation is not None
        and api_after.get("startUtc") == api_observation["api_process"].get("startUtc")
    )
    ports_after = observe_ports(REVIEWER_PORTS, repo_root)

    sdk_ver = run_cmd(["dotnet", "--version"], cwd=repo_root, env=dotnet_env).stdout.strip()
    ef_cp = run_cmd(["dotnet", "tool", "run", "dotnet-ef", "--version"], cwd=repo_root, env=dotnet_env)
    ef_ver = ef_cp.stdout.strip().splitlines()[-1].strip() if ef_cp.returncode == 0 and ef_cp.stdout.strip() else ""
    node_ver = run_cmd(["node", "--version"], cwd=repo_root).stdout.strip()
    npm_ver = run_cmd(["npm.cmd", "--version"], cwd=repo_root).stdout.strip()
    pw_cli = repo_root / "web" / "node_modules" / "@playwright" / "test" / "cli.js"
    pw_ver = run_cmd(["node", str(pw_cli), "--version"], cwd=repo_root / "web").stdout.strip() if pw_cli.is_file() else ""
    ng_pkg = repo_root / "web" / "node_modules" / "@angular" / "cli" / "package.json"
    ng_ver = json.loads(ng_pkg.read_text(encoding="utf-8"))["version"] if ng_pkg.is_file() else ""
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

    git_status_after = run_cmd(
        ["git", "--no-optional-locks", "status", "--porcelain=v1", "--untracked-files=normal"], cwd=repo_root
    ).stdout.strip()

    snap = db_after_api["snapshot"]
    api_docs = api_observation["verified_documents"]
    assertions = {
        "clean_git_before_and_after_before_receipt_write": (
            (not args.require_clean or git_status_before == "") and (not args.require_clean or git_status_after == "")
        ),
        "immutable_002_and_design_dossier_preserved": imm_diff == "",
        "retained_design_prefreeze_failure_byte_exact": (
            len(retained_fail_bytes) > 0
            and scratch_fail_match
            and (not args.require_clean or git_blob_match)
        ),
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
        "ports_5490_4510_55437_free_before_start": all(not ports_before[str(p)] for p in REVIEWER_PORTS),
        "pg_55437_durability_and_scram_verified": (
            ports_during_pg is not None
            and len(ports_during_pg["55437"]) == 1
            and ports_during_pg["55437"][0]["localAddress"] == "127.0.0.1"
            and server_settings.get("server_version") == "18.7"
            and server_settings.get("port") == "55437"
            and server_settings.get("password_encryption") == "scram-sha-256"
            and server_settings.get("fsync") == "on"
            and server_settings.get("full_page_writes") == "on"
            and server_settings.get("synchronous_commit") == "on"
        ),
        "accepted_f1_f2_migrations_only": snap["migrations"] == [
            "20261114182147_InitialDurableIntake",
            "20261116052029_AddLocalExtraction",
        ],
        "seed_row_counts_and_fencing_sequence_4": (
            len(snap["documents"]) == 4
            and len(snap["attempts"]) == 4
            and len(snap["results"]) == 3
            and snap["sequence"] == {"last_value": 4, "is_called": True}
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
            == [F01_RAW_SHA256, F07_RAW_SHA256, F01_RAW_SHA256]
        ),
        "least_privilege_negative_probes_all_denied": all(
            v["rejected"] for v in negative_privilege_probes.values()
        ),
        "disabled_ocr_api_5490_read_parity_and_zero_db_mutation": (
            db_before_api["state_sha256"] == db_after_api["state_sha256"]
            and len(api_docs) == 4
            and all(
                d["get_document_status"] == 200
                and d["get_extraction_status"] == 200
                and d["get_submission_status"] == 200
                and d["get_original_status"] == 200
                and d["worker_enabled"] is False
                and d["can_request_extraction"] is False
                and d["can_retry_extraction"] is False
                and d["original_nosniff"] == "nosniff"
                and d["submission_matches_doc_id"] is True
                for d in api_docs
            )
            and api_docs[0]["page_block_counts_api"] == [36]
            and api_docs[0]["original_download_sha256"] == F01_PDF_SHA256
            and api_docs[1]["page_block_counts_api"] == [16, 5, 4]
            and api_docs[1]["original_download_sha256"] == F07_PDF_SHA256
            and api_docs[2]["attempt_count_api"] == 2
            and api_docs[3]["doc_wire_status"] == "awaiting_extraction"
        ),
        "all_owned_services_stopped_and_ports_unbound_with_seed_retained": (
            stop_exit_code == 0
            and pg_ctl_after.returncode != 0
            and not (pg_data / "postmaster.pid").exists()
            and not pm_alive_after
            and not api_alive_after
            and all(not ports_after[str(p)] for p in REVIEWER_PORTS)
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
    receipt = {
        "schema": "eledgercare.wp-0008.f3-reviewer-seed-preparation-receipt/1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f3-reviewer",
        "branch": branch,
        "frozen_executing_head_sha": head_sha,
        "authority_preparation_sha": AUTHORITY_PREP_SHA,
        "prior_accepted_design_002_sha": PRIOR_DESIGN_002_SHA,
        "helper_path": "docs/reviews/WP-0008/eld-f3-reviewer/preparation/helpers/prepare_and_verify_f2_seed.py",
        "helper_sha256_raw": sha256_hex(helper_bytes),
        "helper_sha256_lf": sha256_hex(helper_bytes.replace(b"\r\n", b"\n")),
        "scope_disclosure": (
            "Independent F2 durable seed preparation on owned reviewer PostgreSQL 18.7 (127.0.0.1:55437, "
            f"database {SEED_DATABASE}) and brief LocalOcr:Enabled=false read-only API observation on 127.0.0.1:5490. "
            "Zero GPU/model/worker calls, zero network downloads, zero unfrozen author or sealed WP-0009 reads, "
            "and zero F3 acceptance claims."
        ),
        "retained_design_prefreeze_failure": {
            "git_retained_path": retained_fail_rel,
            "byte_length": len(retained_fail_bytes),
            "sha256": retained_fail_sha,
            "matches_scratch_original_bytes": scratch_fail_match,
            "matches_committed_git_blob_bytes": git_blob_match,
        },
        "postgres_binary_provenance": pg_subset_report,
        "owned_cluster_and_services": {
            "host": "127.0.0.1",
            "configured_ports": {"api": 5490, "ui": 4510, "postgres": 55437},
            "seeded_database": SEED_DATABASE,
            "credentials_distinct_min_32_chars": True,
            "secret_values_redacted": True,
            "ports_before_start": ports_before,
            "started_postmaster": postmaster_info,
            "ports_during_pg": ports_during_pg,
            "server_settings": server_settings,
            "privilege_matrix_summary": privilege_matrix_lines,
            "negative_privilege_probes": negative_privilege_probes,
            "disabled_ocr_api_5490_observation": api_observation,
            "stop_exit_code": stop_exit_code,
            "pg_ctl_status_rc_after_stop": pg_ctl_after.returncode,
            "postmaster_alive_after_stop": pm_alive_after,
            "api_5490_alive_after_stop": api_alive_after,
            "ports_after_stop": ports_after,
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
        "database_state": {
            "state_sha256_before_api": db_before_api["state_sha256"],
            "state_sha256_after_api": db_after_api["state_sha256"],
            "snapshot": snap,
        },
        "toolchain_and_caches": {
            "dotnet_sdk": sdk_ver,
            "dotnet_ef_local_tool": ef_ver,
            "nuget_lock_audit": nuget_audit,
            "nodejs": node_ver,
            "npm": npm_ver,
            "angular_cli_local": ng_ver,
            "playwright_cli_local": pw_ver,
            "msedge_path": str(edge_path) if edge_path else None,
            "msedge_version": edge_ver,
        },
        "assertions": assertions,
        "assertion_count": len(assertions),
        "all_assertions_passed": all(assertions.values()),
    }

    serialized = json.dumps(receipt, indent=2, sort_keys=False) + "\n"
    for secret in secrets_to_scrub:
        if secret and secret in serialized:
            raise RuntimeError("Refusing to write receipt: secret substring detected!")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(serialized.encode("utf-8"))
    failed = [k for k, v in assertions.items() if not v]
    if failed:
        raise AssertionError(f"Preparation assertions failed: {failed}")
    print(f"OK: {len(assertions)} assertions passed; receipt written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
