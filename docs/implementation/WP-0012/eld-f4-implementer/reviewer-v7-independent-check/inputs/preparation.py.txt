"""Frozen independent reviewer orchestrator for WP-0012 (`eld-f4-reviewer`).

Supports two strictly separated modes:
  1. `--mode cpu-prep-validation` (EXECUTED NOW — CPU-only, zero GPU/model/venv execution):
     - Verifies clean Git state, exact accepted product/worker/test/deploy trees from
       `73c8d3c4f0a00312e3444328331b6cbd6406e882` / `47fbc7612e4a08cf1960ad7ac01bd2843ae645e5`,
       worker source/config digests, fixture SHA-256 digests, and pure-stdlib read-only Q0
       model/notice/dependency-lock file checks (`C:\\Users\\jackg\\eLedgerCare-Q0\\WP-0005`,
       without invoking Q0 `python.exe`, `torch`, `transformers`, or `nvidia-smi`).
     - Prepares empty non-reparse `C:\\Users\\jackg\\eLedgerCare-Demo\\WP-0012\\reviewer\\runs`
       (`>= 20 GiB` free disk floor, `0` bytes used).
     - Runs 5 negative fail-closed lease/cap refusal tests against `--mode live-leased-rehearsal`
       (all 5 must exit `2` before starting any service or model).
     - Starts owned PostgreSQL `18.7` (`127.0.0.1:55439`), verifies historical `WP-0010` databases
       (`eledgercare_f4_reviewer_seed_f3` and `eledgercare_f4_reviewer_migrated`) are bit-for-bit
       unchanged, prepares fresh owned `eledgercare_demo_wp0012_reviewer` (`4` migrations +
       `eledgercare_app` least-privilege matrix + SQL mutation denials), exercises real Microsoft
       Edge (`msedge`, `127.0.0.1:4710 -> 127.0.0.1:5690`) with `LocalOcr:Enabled=false` on a
       disposable scratch database (browser upload -> `extraction-unavailable` disabled guard ->
       `503 extraction_disabled` -> PG+API restart -> reopen with `0` attempts -> drop scratch DB)
       plus GET-only readiness verification on empty `eledgercare_demo_wp0012_reviewer` (`0` rows
       across all 10 tables, `fencing_seq = (1, false)`), and stops all owned services (`0` listeners).
  2. `--mode live-leased-rehearsal` (HELD for `/004` after author `/003` + coordinator sole GPU lease):
     - Fails closed unless supplied a valid coordinator sole-lease JSON (`owner_agent == "eld-f4-reviewer"`,
       `packet_id == "WP-0012"`, `max_attempts == 2`, `gpu_uuid`).
     - Enforces at most `2` extraction attempts (`0` SQL-seeded results, `0` warmups, `0` retries),
       stopping immediately and preserving diagnostics/returning lease on any failure, then restarts
       PG + API with `LocalOcr:Enabled=false`, verifies unchanged attempt count (`== 2`), stops all
       services, re-verifies Q0 immutability + idle GPU compute state, and writes lease-return receipt.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zlib

API_PORT = 5690
UI_PORT = 4710
PG_PORT = 55439
REVIEWER_PORTS = (API_PORT, UI_PORT, PG_PORT)

DEMO_DATABASE = "eledgercare_demo_wp0012_reviewer"
SCRATCH_PREFLIGHT_DATABASE = "eledgercare_demo_wp0012_reviewer_cpupreflight"
HISTORICAL_SEED_DB = "eledgercare_f4_reviewer_seed_f3"
HISTORICAL_MIGRATED_DB = "eledgercare_f4_reviewer_migrated"

EXPECTED_F3_SEED_8TABLE_SHA = "841a3c0a2fc6ff5bbf29d6da1feff35b53c0c35be33a89a9ea03cfe2c1a2c993"
EXPECTED_MIGRATED_PROJ_SHA = "0faf93dc12d8596df7435628ac3b797b8a703c8f0cd68614e11b9d8bb39c63fa"

ACCEPTED_PRODUCT_BASE_SHA = "73c8d3c4f0a00312e3444328331b6cbd6406e882"
AUTHORITY_WP0012_SHA = "47fbc7612e4a08cf1960ad7ac01bd2843ae645e5"

EXPECTED_PG_SUBSET_SHA = "47c3deb9c917f79c353b3683b2c2611ee975285ea06226c8f72444c96ce9051f"
EXPECTED_PG_CD_SHA = "3132ca63b424f7ec371eabe50753ad7cd036278d942a6ea465547b17bf90a149"
EXPECTED_PG_FILES = 1597
EXPECTED_PG_BYTES = 151_078_582

MODEL_MANIFEST_SHA256 = "0df07bc60abf6937c917040bced32afabd7e4d11bafc0bd99902abca610a81be"
DEPENDENCY_LOCK_SHA256 = "582071bf20eaca1836c3d1cef21d31cbdaa1e1407184033a918a40612c128111"
WORKER_SOURCE_SHA256 = "c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54"
WORKER_CONFIG_1P_SHA256 = "579aad63a9893a58466baf005ea63f87e92540d4c1f71f6b3c399e8b1e6b35ff"
WORKER_CONFIG_2P_SHA256 = "e4df504ddb51dcc8fb137e97f5af97c735252374738b1a1754a88b16a05de5df"
WORKER_CONFIG_3P_SHA256 = "ac90459ca4011b5859cfdd0b224d5ea247489b7c01775118736df7c1c9819e86"

SYN_WO_SHA256 = "47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd"
SYN_WO_BYTES = 372_258
SYN_MP_SHA256 = "15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3"
SYN_MP_BYTES = 8_422

READONLY_Q0_ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")
WRITABLE_DEMO_ROOT = Path(r"C:\Users\jackg\eLedgerCare-Demo\WP-0012\reviewer")
MIN_FREE_DISK_BYTES = 20 * 1024 * 1024 * 1024

EXPECTED_MIGRATIONS = [
    "20261114182147_InitialDurableIntake",
    "20261116052029_AddLocalExtraction",
    "20261116200918_AddWorkOrderReview",
    "20261117091519_AddSourceLinkedArchive",
]

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
    "rehearsal/wp-0012-product",
    "wp-0012\\author",
    "wp-0012/author",
    "wp-0013",
    "eld-vocab-",
    "eledgercare-mapping",
    "eledgercare-coverage",
    "eledgercare-f2",
)

REPARSE_ATTR = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256_hex(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def file_git_blob_sha1_hex(path: Path, expected_size: int) -> str:
    h = hashlib.sha1()
    h.update(f"blob {expected_size}\0".encode("ascii"))
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


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
    timeout_s: int = 300,
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


def compute_worker_source_sha256(worker_root: Path) -> str:
    py_files = [worker_root / "run_worker.py"]
    py_files.extend(sorted((worker_root / "local_ocr").glob("*.py"), key=lambda p: p.name))
    h = hashlib.sha256()
    for f in py_files:
        rel = f.relative_to(worker_root).as_posix()
        norm = f.read_bytes().replace(b"\r\n", b"\n")
        f_hex = sha256_hex(norm)
        h.update(f"{rel}:{len(norm)}:{f_hex}\n".encode("utf-8"))
    return h.hexdigest()


def compute_worker_config_sha256(page_count: int) -> str:
    max_new_tokens = 8000 * page_count
    ngram_window = 1024 if page_count > 1 else 128
    # Matches Utf8JsonWriter exact key order and raw 0.0 float formatting in ExtractionSettings.cs
    raw_json = (
        '{"call_kwargs":{'
        '"base_size":1024,'
        '"crop_mode":false,'
        '"dash_topm":16,'
        '"eval_mode":false,'
        '"image_size":640,'
        '"max_crops":16,'
        '"max_length":131072,'
        f'"max_new_tokens":{max_new_tokens},'
        '"max_page_tokens":20000,'
        '"ngram_whitelist_token_ids":null,'
        f'"ngram_window":{ngram_window},'
        '"no_repeat_ngram_size":35,'
        '"output_path":"",'
        '"page_count_guard":true,'
        '"save_results":false,'
        '"temperature":0.0,'
        '"test_compress":false,'
        '"tps_interval":0'
        '},'
        '"envelope_schema":"eledgercare.local-extraction/1",'
        '"model_repo_id":"baidu/Unlimited-OCR-2",'
        '"model_revision":"0480966938291445591f69f08a13b041c073a96a",'
        '"prompt":"Multi page parsing.",'
        '"render_dpi":300,'
        '"request_schema":"eledgercare.local-extraction-request/1",'
        '"worker_id":"eledgercare.local-ocr-worker/1"}'
    )
    return sha256_hex(raw_json.encode("utf-8"))


def verify_q0_readonly_pure_stdlib(repo_root: Path) -> dict:
    """Pure Python stdlib verification of read-only Q0 model, notices, and venv metadata.
    Spawns ZERO subprocesses and imports ZERO external/model packages.
    """
    model_manifest_path = guard_owned_repo_path(repo_root, "workers/local_ocr/manifests/model-files.json")
    dep_lock_path = guard_owned_repo_path(repo_root, "workers/local_ocr/manifests/dependency-lock.json")
    model_manifest_bytes = model_manifest_path.read_bytes()
    dep_lock_bytes = dep_lock_path.read_bytes()

    model_manifest = json.loads(model_manifest_bytes.decode("utf-8"))
    dep_lock = json.loads(dep_lock_bytes.decode("utf-8"))

    if not READONLY_Q0_ROOT.exists() or is_reparse_or_link(READONLY_Q0_ROOT):
        raise RuntimeError(f"Read-only Q0 root missing or reparse point: {READONLY_Q0_ROOT}")

    model_dir = READONLY_Q0_ROOT / "models" / model_manifest["model_dir_basename"]
    notice_dir = READONLY_Q0_ROOT / "notices" / model_manifest["notice_dir_basename"]
    venv_python = READONLY_Q0_ROOT / "venv" / "Scripts" / "python.exe"
    site_packages = READONLY_Q0_ROOT / "venv" / "Lib" / "site-packages"

    if not model_dir.is_dir() or is_reparse_or_link(model_dir):
        raise RuntimeError(f"Model directory invalid: {model_dir}")
    if not notice_dir.is_dir() or is_reparse_or_link(notice_dir):
        raise RuntimeError(f"Notice directory invalid: {notice_dir}")
    if not venv_python.is_file() or is_reparse_or_link(venv_python):
        raise RuntimeError(f"Venv python executable missing or reparse point: {venv_python}")

    verified_model_files: list[dict] = []
    total_model_bytes = 0
    for entry in model_manifest["files"]:
        fp = model_dir / entry["path"]
        if not fp.is_file() or is_reparse_or_link(fp):
            raise RuntimeError(f"Missing or linked model file: {fp}")
        st = fp.stat()
        if st.st_size != entry["size"]:
            raise RuntimeError(f"Size mismatch on {fp}: {st.st_size} != {entry['size']}")
        if entry["digest_kind"] == "git_blob_sha1":
            actual_digest = file_git_blob_sha1_hex(fp, st.st_size)
            expected_digest = entry["git_blob_sha1"]
        else:
            actual_digest = file_sha256_hex(fp)
            expected_digest = entry["sha256"]
        if actual_digest != expected_digest:
            raise RuntimeError(f"Digest mismatch on {fp}: {actual_digest} != {expected_digest}")
        total_model_bytes += st.st_size
        verified_model_files.append({
            "path": entry["path"],
            "size": st.st_size,
            "mtime_ns": st.st_mtime_ns,
            "digest_kind": entry["digest_kind"],
            "digest": actual_digest,
        })

    raw_extras = sorted(
        p.name for p in model_dir.iterdir() if p.name not in {e["path"] for e in model_manifest["files"]}
    )
    unexpected_extra_entries = [name for name in raw_extras if name != ".cache"]
    cache_py_files = (
        sorted(p.relative_to(model_dir).as_posix() for p in (model_dir / ".cache").rglob("*") if p.suffix in (".py", ".pyc"))
        if (model_dir / ".cache").is_dir()
        else []
    )
    if cache_py_files:
        unexpected_extra_entries.extend(cache_py_files)

    verified_notices: list[dict] = []
    for n_entry in model_manifest["notices"]:
        np = notice_dir / n_entry["path"]
        if not np.is_file() or is_reparse_or_link(np):
            raise RuntimeError(f"Missing or linked notice file: {np}")
        nst = np.stat()
        ndigest = file_git_blob_sha1_hex(np, nst.st_size)
        if nst.st_size != n_entry["size"] or ndigest != n_entry["git_blob_sha1"]:
            raise RuntimeError(f"Notice mismatch on {np}")
        verified_notices.append({
            "path": n_entry["path"],
            "size": nst.st_size,
            "mtime_ns": nst.st_mtime_ns,
            "git_blob_sha1": ndigest,
        })

    # Inspect locked distributions strictly via static .dist-info/METADATA text reads (zero code execution)
    installed_versions: dict[str, str] = {}
    for meta_file in site_packages.glob("*.dist-info/METADATA"):
        pkg_name = None
        pkg_ver = None
        for line in meta_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                break
            if line.startswith("Name:") and pkg_name is None:
                pkg_name = line.split(":", 1)[1].strip().lower().replace("_", "-")
            elif line.startswith("Version:") and pkg_ver is None:
                pkg_ver = line.split(":", 1)[1].strip()
        if pkg_name and pkg_ver:
            installed_versions[pkg_name] = pkg_ver

    missing_locked: list[str] = []
    for dist in dep_lock["distributions"]:
        norm_name = dist["name"].lower().replace("_", "-")
        if installed_versions.get(norm_name) != dist["version"]:
            missing_locked.append(f"{norm_name}=={dist['version']} (found {installed_versions.get(norm_name)})")

    forbidden_present = [
        mod for mod in dep_lock["forbidden_importable_modules"]
        if (site_packages / mod).exists() or (site_packages / f"{mod}.py").exists()
    ]

    return {
        "schema": "eledgercare.wp-0012.q0-readonly-manifest-check/1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "execution_method": "pure_python_stdlib_stat_and_hash_zero_venv_or_model_execution",
        "readonly_q0_root": str(READONLY_Q0_ROOT),
        "model_manifest_sha256": sha256_hex(model_manifest_bytes),
        "dependency_lock_sha256": sha256_hex(dep_lock_bytes),
        "verified_model_file_count": len(verified_model_files),
        "total_model_bytes": total_model_bytes,
        "tolerated_download_metadata_entries": [name for name in raw_extras if name == ".cache"],
        "unexpected_extra_model_entries": unexpected_extra_entries,
        "verified_model_files": verified_model_files,
        "verified_notices": verified_notices,
        "locked_distribution_count": len(dep_lock["distributions"]),
        "missing_or_mismatched_distributions": missing_locked,
        "forbidden_modules_present": forbidden_present,
        "venv_python_stat": {
            "size": venv_python.stat().st_size,
            "mtime_ns": venv_python.stat().st_mtime_ns,
        },
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
    sig_ps = f"(Get-AuthenticodeSignature -FilePath '{pg_root / 'bin' / 'postgres.exe'}').Status.ToString()"
    authenticode = run_cmd(["pwsh", "-NoProfile", "-Command", sig_ps], cwd=cwd).stdout.strip()

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
    cp = run_cmd(args, cwd=cwd, env=env, input_text=sql, timeout_s=120)
    if expect_success and cp.returncode != 0:
        raise RuntimeError(f"psql failed as {user} on {database} (exit {cp.returncode}): {cp.stderr}")
    return cp


def compute_canonical_8table_snapshot(psql_exe: Path, settings: dict, database: str, cwd: Path) -> dict:
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
    )
    parsed = json.loads(cp.stdout.strip())
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "canonical_8table_sha256": sha256_hex(canonical),
        "counts": {k: len(parsed[k]) for k in parsed if k != "fencing_seq"},
        "fencing_seq": parsed["fencing_seq"],
    }


def compute_projection_tables_snapshot(psql_exe: Path, settings: dict, database: str, cwd: Path) -> dict:
    sql = """
SELECT json_build_object(
  'projections', COALESCE((
    SELECT json_agg(row_to_json(t) ORDER BY t.result_id, t.projection_version) FROM (
      SELECT result_id::text, projection_version, document_id::text,
             encode(raw_output_sha256, 'hex') AS raw_output_sha256_hex,
             encode(projection_sha256, 'hex') AS projection_sha256_hex,
             unit_count, has_fallback
      FROM eledgercare.archive_result_projections
    ) t
  ), '[]'::json),
  'units', COALESCE((
    SELECT json_agg(row_to_json(t) ORDER BY t.result_id, t.projection_version, t.unit_ordinal) FROM (
      SELECT result_id::text, projection_version, unit_ordinal, document_id::text,
             page_number, unit_kind, is_fallback,
             char_length(search_text) AS char_len,
             encode(sha256(convert_to(search_text, 'UTF8')), 'hex') AS text_sha256_hex
      FROM eledgercare.archive_projection_units
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
    )
    parsed = json.loads(cp.stdout.strip())
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "projection_tables_sha256": sha256_hex(canonical),
        "projection_count": len(parsed["projections"]),
        "unit_count": len(parsed["units"]),
    }


def http_request(port: int, method: str, path_str: str, timeout_s: int = 20) -> tuple[int, bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout_s)
    try:
        conn.request(method, path_str, headers={"Host": f"127.0.0.1:{port}"})
        resp = conn.getresponse()
        return resp.status, resp.read()
    finally:
        conn.close()


def start_owned_api(
    *,
    api_dll: Path,
    settings: dict,
    database: str,
    ocr_enabled: bool,
    leased_gpu_uuid: str | None,
    log_path: Path,
    repo_root: Path,
) -> tuple[subprocess.Popen[bytes], dict]:
    if observe_ports((API_PORT,), repo_root)[str(API_PORT)]:
        raise RuntimeError(f"Port {API_PORT} already bound before starting owned API")

    api_env = dict(os.environ)
    api_env["ASPNETCORE_ENVIRONMENT"] = "Production"
    api_env["DOTNET_NOLOGO"] = "1"
    api_env["Api__Port"] = str(API_PORT)
    api_env["LocalOcr__Enabled"] = "true" if ocr_enabled else "false"
    api_env["LocalOcr__MaxExtractionPages"] = "3"
    api_env["LocalOcr__WorkerRootPath"] = str(repo_root / "workers" / "local_ocr")
    if ocr_enabled:
        if not leased_gpu_uuid:
            raise ValueError("leased_gpu_uuid required when ocr_enabled=True")
        api_env["LocalOcr__ReadOnlyQ0Root"] = str(READONLY_Q0_ROOT)
        api_env["LocalOcr__WritableRuntimeRoot"] = str(WRITABLE_DEMO_ROOT)
        api_env["LocalOcr__LeasedGpuUuid"] = leased_gpu_uuid
    api_env["ConnectionStrings__Runtime"] = (
        f"Host={settings['host']};Port={PG_PORT};Database={database};"
        f"Username={settings['appUser']};Password={settings['appPassword']}"
    )

    with log_path.open("ab") as fh:
        proc = subprocess.Popen(
            ["dotnet", str(api_dll)],
            cwd=str(api_dll.parent),
            env=api_env,
            stdout=fh,
            stderr=subprocess.STDOUT,
        )
    info = inspect_process(proc.pid, repo_root)
    deadline = time.monotonic() + 45.0
    ready = False
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"ELedgerCare.Api exited early with code {proc.returncode}")
        try:
            st, _ = http_request(API_PORT, "GET", "/api/archive?limit=1")
            if st == 200:
                ready = True
                break
        except OSError:
            pass
        time.sleep(0.25)
    if not ready or info is None:
        stop_owned_process(proc, info, repo_root)
        raise RuntimeError("ELedgerCare.Api failed readiness check on /api/archive?limit=1")
    return proc, info


def start_owned_ui(*, node_exe: Path, log_path: Path, repo_root: Path) -> tuple[subprocess.Popen[bytes], dict]:
    if observe_ports((UI_PORT,), repo_root)[str(UI_PORT)]:
        raise RuntimeError(f"Port {UI_PORT} already bound before starting owned UI")

    ui_env = dict(os.environ)
    ui_env["ELEDGERCARE_API_PORT"] = str(API_PORT)
    ui_env["NG_CLI_ANALYTICS"] = "false"

    with log_path.open("ab") as fh:
        proc = subprocess.Popen(
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
            stdout=fh,
            stderr=subprocess.STDOUT,
        )
    info = inspect_process(proc.pid, repo_root)
    deadline = time.monotonic() + 120.0
    ready = False
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"ng serve exited early with code {proc.returncode}")
        try:
            st, _ = http_request(UI_PORT, "GET", "/")
            if st == 200:
                ready = True
                break
        except OSError:
            pass
        time.sleep(0.5)
    if not ready or info is None:
        stop_owned_process(proc, info, repo_root)
        raise RuntimeError("ng serve failed readiness check on 127.0.0.1:4710")
    return proc, info


def validate_reviewer_lease_json(lease_path_str: str | None) -> dict:
    if not lease_path_str:
        raise ValueError("Refusing live-leased-rehearsal: --lease-json is required.")
    lp = Path(lease_path_str)
    if not lp.is_file():
        raise ValueError(f"Refusing live-leased-rehearsal: lease file not found: {lp}")
    lease = json.loads(lp.read_text(encoding="utf-8"))
    if lease.get("packet_id") != "WP-0012":
        raise ValueError(f"Refusing live-leased-rehearsal: packet_id must be 'WP-0012', got {lease.get('packet_id')!r}")
    if lease.get("owner_agent") != "eld-f4-reviewer":
        raise ValueError(
            f"Refusing live-leased-rehearsal: owner_agent must be 'eld-f4-reviewer', got {lease.get('owner_agent')!r}"
        )
    if lease.get("max_attempts") != 2:
        raise ValueError(f"Refusing live-leased-rehearsal: max_attempts must equal 2, got {lease.get('max_attempts')!r}")
    inputs = lease.get("permitted_inputs")
    expected_inputs = ["tests/fixtures/SYN-WO-01-v1-raster300.pdf", "tests/fixtures/SYN-MP-01-v0-clean.pdf"]
    if inputs != expected_inputs:
        raise ValueError(f"Refusing live-leased-rehearsal: permitted_inputs must equal {expected_inputs}")
    gpu_uuid = str(lease.get("gpu_uuid") or "").strip()
    if not gpu_uuid.startswith("GPU-") or len(gpu_uuid) < 16:
        raise ValueError(f"Refusing live-leased-rehearsal: invalid gpu_uuid {gpu_uuid!r}")
    return lease


def run_fail_closed_lease_self_tests(script_path: Path, repo_root: Path) -> list[dict]:
    cases = [
        ("missing_lease_arg", []),
        (
            "wrong_owner_agent",
            {
                "packet_id": "WP-0012",
                "owner_agent": "eld-f4-implementer",
                "max_attempts": 2,
                "permitted_inputs": [
                    "tests/fixtures/SYN-WO-01-v1-raster300.pdf",
                    "tests/fixtures/SYN-MP-01-v0-clean.pdf",
                ],
                "gpu_uuid": "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d",
            },
        ),
        (
            "wrong_packet_id",
            {
                "packet_id": "WP-0006",
                "owner_agent": "eld-f4-reviewer",
                "max_attempts": 2,
                "permitted_inputs": [
                    "tests/fixtures/SYN-WO-01-v1-raster300.pdf",
                    "tests/fixtures/SYN-MP-01-v0-clean.pdf",
                ],
                "gpu_uuid": "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d",
            },
        ),
        (
            "attempt_cap_above_two",
            {
                "packet_id": "WP-0012",
                "owner_agent": "eld-f4-reviewer",
                "max_attempts": 3,
                "permitted_inputs": [
                    "tests/fixtures/SYN-WO-01-v1-raster300.pdf",
                    "tests/fixtures/SYN-MP-01-v0-clean.pdf",
                ],
                "gpu_uuid": "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d",
            },
        ),
        (
            "missing_gpu_uuid",
            {
                "packet_id": "WP-0012",
                "owner_agent": "eld-f4-reviewer",
                "max_attempts": 2,
                "permitted_inputs": [
                    "tests/fixtures/SYN-WO-01-v1-raster300.pdf",
                    "tests/fixtures/SYN-MP-01-v0-clean.pdf",
                ],
                "gpu_uuid": "",
            },
        ),
    ]
    results: list[dict] = []
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for name, payload in cases:
            cmd = [
                sys.executable,
                "-B",
                str(script_path),
                "--mode",
                "live-leased-rehearsal",
                "--summary-output",
                str(td_path / "unused-summary.json"),
                "--q0-check-output",
                str(td_path / "unused-q0.json"),
                "--resource-return-output",
                str(td_path / "unused-rr.json"),
                "--logs-dir",
                str(td_path / "unused-logs"),
                "--screenshots-dir",
                str(td_path / "unused-shots"),
            ]
            if isinstance(payload, dict):
                lp = td_path / f"{name}.json"
                lp.write_text(json.dumps(payload), encoding="utf-8")
                cmd.extend(["--lease-json", str(lp)])
            cp = run_cmd(cmd, cwd=repo_root, timeout_s=30)
            results.append({
                "case": name,
                "returncode": cp.returncode,
                "refused_fail_closed": cp.returncode == 2 and "Refusing live-leased-rehearsal" in cp.stderr,
                "stderr": cp.stderr.strip(),
            })
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WP-0012 independent reviewer CPU prep & held live rehearsal runner.")
    parser.add_argument("--mode", choices=("cpu-prep-validation", "live-leased-rehearsal"), required=True)
    parser.add_argument("--lease-json", default=None, help="Coordinator sole-lease JSON (required for live-leased-rehearsal)")
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--q0-check-output", required=True)
    parser.add_argument("--resource-return-output", required=True)
    parser.add_argument("--logs-dir", required=True)
    parser.add_argument("--screenshots-dir", required=True)
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args(argv)

    # Immediate fail-closed gate for live mode BEFORE creating directories, starting PG/API/UI, or touching GPU
    lease_doc: dict | None = None
    if args.mode == "live-leased-rehearsal":
        try:
            lease_doc = validate_reviewer_lease_json(args.lease_json)
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 2

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[6]
    summary_out = guard_owned_repo_path(repo_root, args.summary_output)
    q0_out = guard_owned_repo_path(repo_root, args.q0_check_output)
    rr_out = guard_owned_repo_path(repo_root, args.resource_return_output)
    logs_dir = guard_owned_repo_path(repo_root, args.logs_dir)
    shots_dir = guard_owned_repo_path(repo_root, args.screenshots_dir)
    for d in (summary_out.parent, q0_out.parent, rr_out.parent, logs_dir, shots_dir):
        d.mkdir(parents=True, exist_ok=True)

    assertions: list[dict] = []

    def record_assert(name: str, cond: bool, detail: object) -> None:
        if not cond:
            raise AssertionError(f"Assertion failed [{name}]: {detail}")
        assertions.append({"check": name, "passed": True, "detail": detail})

    # 1. Clean Git status, branch identity, and unchanged product/worker/test/deploy trees
    status_porcelain = run_git(repo_root, "status", "--porcelain", "--untracked-files=normal")
    if args.require_clean:
        record_assert("clean_worktree_before_run", status_porcelain == "", {"status": status_porcelain})

    head_sha = run_git(repo_root, "rev-parse", "HEAD")
    branch_name = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    anc_base = run_cmd(["git", "merge-base", "--is-ancestor", ACCEPTED_PRODUCT_BASE_SHA, head_sha], cwd=repo_root).returncode == 0
    anc_auth = run_cmd(["git", "merge-base", "--is-ancestor", AUTHORITY_WP0012_SHA, head_sha], cwd=repo_root).returncode == 0
    record_assert(
        "owned_wp0012_branch_and_ancestry",
        branch_name == "review/wp-0012-product-rehearsal" and anc_base and anc_auth,
        {"branch": branch_name, "head_sha": head_sha, "anc_base": anc_base, "anc_auth": anc_auth},
    )

    tree_oids: dict[str, str] = {}
    for rel in PRESERVED_TREE_PATHS:
        expected_oid = run_git(repo_root, "rev-parse", f"{ACCEPTED_PRODUCT_BASE_SHA}:{rel}")
        actual_oid = run_git(repo_root, "rev-parse", f"{head_sha}:{rel}")
        tree_oids[rel] = actual_oid
        record_assert(f"unchanged_tree:{rel}", expected_oid == actual_oid, {"oid": actual_oid})

    # 2. Pinned fixtures, worker source/config digests, pure-stdlib Q0 read-only check, & writable demo root
    syn_wo = guard_owned_repo_path(repo_root, "tests/fixtures/SYN-WO-01-v1-raster300.pdf")
    syn_mp = guard_owned_repo_path(repo_root, "tests/fixtures/SYN-MP-01-v0-clean.pdf")
    record_assert(
        "permitted_fixture_digests",
        syn_wo.stat().st_size == SYN_WO_BYTES
        and file_sha256_hex(syn_wo) == SYN_WO_SHA256
        and syn_mp.stat().st_size == SYN_MP_BYTES
        and file_sha256_hex(syn_mp) == SYN_MP_SHA256,
        {"syn_wo_sha256": SYN_WO_SHA256, "syn_mp_sha256": SYN_MP_SHA256},
    )

    worker_root = guard_owned_repo_path(repo_root, "workers/local_ocr")
    w_src_sha = compute_worker_source_sha256(worker_root)
    w_c1 = compute_worker_config_sha256(1)
    w_c2 = compute_worker_config_sha256(2)
    w_c3 = compute_worker_config_sha256(3)
    record_assert(
        "worker_source_and_config_digests",
        w_src_sha == WORKER_SOURCE_SHA256
        and w_c1 == WORKER_CONFIG_1P_SHA256
        and w_c2 == WORKER_CONFIG_2P_SHA256
        and w_c3 == WORKER_CONFIG_3P_SHA256,
        {"worker_source_sha256": w_src_sha, "1p": w_c1, "2p": w_c2, "3p": w_c3},
    )

    q0_check = verify_q0_readonly_pure_stdlib(repo_root)
    q0_out.write_text(json.dumps(q0_check, indent=2) + "\n", encoding="utf-8", newline="\n")
    record_assert(
        "q0_readonly_pure_stdlib_manifest_verified",
        q0_check["model_manifest_sha256"] == MODEL_MANIFEST_SHA256
        and q0_check["dependency_lock_sha256"] == DEPENDENCY_LOCK_SHA256
        and q0_check["verified_model_file_count"] == 18
        and q0_check["total_model_bytes"] == 6_699_195_181
        and q0_check["unexpected_extra_model_entries"] == []
        and q0_check["missing_or_mismatched_distributions"] == []
        and q0_check["forbidden_modules_present"] == [],
        {
            "verified_model_file_count": q0_check["verified_model_file_count"],
            "total_model_bytes": q0_check["total_model_bytes"],
            "locked_distribution_count": q0_check["locked_distribution_count"],
        },
    )

    runs_dir = WRITABLE_DEMO_ROOT / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    free_disk = shutil.disk_usage(WRITABLE_DEMO_ROOT).free
    record_assert(
        "writable_demo_root_isolated_and_within_bounds",
        WRITABLE_DEMO_ROOT.is_dir()
        and not is_reparse_or_link(WRITABLE_DEMO_ROOT)
        and not is_reparse_or_link(runs_dir)
        and free_disk >= MIN_FREE_DISK_BYTES,
        {"writable_demo_root": str(WRITABLE_DEMO_ROOT), "free_disk_bytes": free_disk},
    )

    # 3. Pre-start port cleanliness
    ports_before = observe_ports(REVIEWER_PORTS, repo_root)
    record_assert(
        "disjoint_reviewer_ports_idle_before_start",
        all(len(ports_before[str(p)]) == 0 for p in REVIEWER_PORTS),
        ports_before,
    )

    local_dir = repo_root / ".local"
    pg_subset = verify_pg_subset(local_dir / "tools", repo_root)
    record_assert(
        "pg18_subset_manifest_verified",
        pg_subset["file_count"] == EXPECTED_PG_FILES
        and pg_subset["total_bytes"] == EXPECTED_PG_BYTES
        and pg_subset["missing_files"] == []
        and pg_subset["extra_files"] == []
        and pg_subset["mismatched_files"] == []
        and pg_subset["reparse_points"] == []
        and pg_subset["subset_manifest_sha256"] == EXPECTED_PG_SUBSET_SHA
        and pg_subset["central_directory_sha256"] == EXPECTED_PG_CD_SHA
        and pg_subset["authenticode_status"] == "Valid",
        {
            "file_count": pg_subset["file_count"],
            "subset_manifest_sha256": pg_subset["subset_manifest_sha256"],
            "authenticode_status": pg_subset["authenticode_status"],
        },
    )

    settings = json.loads((local_dir / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
    secrets = [
        str(settings["adminPassword"]),
        str(settings["migratorPassword"]),
        str(settings["appPassword"]),
    ]
    psql_exe = local_dir / "tools" / "pgsql-18.7-1" / "bin" / "psql.exe"
    pg_ctl_exe = local_dir / "tools" / "pgsql-18.7-1" / "bin" / "pg_ctl.exe"
    pg_data_dir = local_dir / "postgres-data"
    node_exe = Path(shutil.which("node") or "node")
    edge_driver = guard_owned_repo_path(
        repo_root, "docs/reviews/WP-0012/eld-f4-reviewer/preparation/helpers/drive_wp0012_edge_workflow.mjs"
    )

    # Ensure Release binary matches exact accepted HEAD src/ offline
    dotnet_env = dict(os.environ)
    dotnet_env["DOTNET_CLI_HOME"] = str(local_dir / "dotnet-home")
    dotnet_env["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1"
    dotnet_env["DOTNET_NOLOGO"] = "1"
    dotnet_env["NUGET_PACKAGES"] = str(local_dir / "nuget" / "packages")
    build_cp = run_cmd(
        ["dotnet", "build", "src/ELedgerCare.Api/ELedgerCare.Api.csproj", "-c", "Release", "--no-restore"],
        cwd=repo_root,
        env=dotnet_env,
    )
    (logs_dir / "00-dotnet-release-build.log").write_text(
        redact_secrets(build_cp.stdout + build_cp.stderr, secrets), encoding="utf-8", newline="\n"
    )
    record_assert("offline_dotnet_release_build_succeeded", build_cp.returncode == 0, {"exit_code": build_cp.returncode})
    api_dll = guard_owned_repo_path(repo_root, "src/ELedgerCare.Api/bin/Release/net10.0/ELedgerCare.Api.dll")

    api_proc: subprocess.Popen[bytes] | None = None
    api_info: dict | None = None
    ui_proc: subprocess.Popen[bytes] | None = None
    ui_info: dict | None = None
    postmaster_info: dict | None = None
    api_stop_receipts: list[dict] = []
    ui_stop_receipt: dict = {}

    api_log = logs_dir / "owned-api-5690.log"
    ui_log = logs_dir / "owned-ui-4710.log"
    for lf in (api_log, ui_log):
        if lf.exists():
            lf.unlink()

    try:
        if args.mode == "cpu-prep-validation":
            # 4. Run 5 negative fail-closed lease/cap refusal tests
            neg_lease_tests = run_fail_closed_lease_self_tests(script_path, repo_root)
            record_assert(
                "live_mode_fails_closed_without_valid_reviewer_lease",
                len(neg_lease_tests) == 5 and all(t["refused_fail_closed"] for t in neg_lease_tests),
                neg_lease_tests,
            )

            # 5. Start owned PG 18.7 on 55439 & verify historical WP-0010 DBs untouched
            start_pg = run_cmd(
                ["pwsh", "-NoProfile", "-File", str(repo_root / "deploy/dev/postgres/start-cluster.ps1")],
                cwd=repo_root,
            )
            (logs_dir / "01-pg-cluster-start.log").write_text(
                redact_secrets(start_pg.stdout + start_pg.stderr, secrets), encoding="utf-8", newline="\n"
            )
            record_assert("pg_cluster_55439_started", start_pg.returncode == 0, {"exit_code": start_pg.returncode})
            pm_pid = int((pg_data_dir / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
            postmaster_info = inspect_process(pm_pid, repo_root)

            hist_seed_before = compute_canonical_8table_snapshot(psql_exe, settings, HISTORICAL_SEED_DB, repo_root)
            hist_mig_8_before = compute_canonical_8table_snapshot(psql_exe, settings, HISTORICAL_MIGRATED_DB, repo_root)
            hist_mig_proj_before = compute_projection_tables_snapshot(psql_exe, settings, HISTORICAL_MIGRATED_DB, repo_root)
            record_assert(
                "historical_wp0010_databases_intact_before",
                hist_seed_before["canonical_8table_sha256"] == EXPECTED_F3_SEED_8TABLE_SHA
                and hist_mig_8_before["canonical_8table_sha256"] == EXPECTED_F3_SEED_8TABLE_SHA
                and hist_mig_proj_before["projection_tables_sha256"] == EXPECTED_MIGRATED_PROJ_SHA,
                {
                    "seed_f3_sha256": hist_seed_before["canonical_8table_sha256"],
                    "migrated_proj_sha256": hist_mig_proj_before["projection_tables_sha256"],
                },
            )

            # 6. Prepare fresh owned `eledgercare_demo_wp0012_reviewer` (empty, 4 migrations, least-privilege)
            for db_to_reset in (DEMO_DATABASE, SCRATCH_PREFLIGHT_DATABASE):
                invoke_psql(
                    psql_exe,
                    host=settings["host"],
                    port=PG_PORT,
                    user=settings["adminUser"],
                    password=settings["adminPassword"],
                    database="postgres",
                    sql=f"DROP DATABASE IF EXISTS {db_to_reset} WITH (FORCE);",
                    cwd=repo_root,
                )

            prep_demo = run_cmd(
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    str(repo_root / "deploy/dev/database/prepare-database.ps1"),
                    "-Database",
                    DEMO_DATABASE,
                ],
                cwd=repo_root,
                env=dotnet_env,
            )
            (logs_dir / "02-prepare-demo-db.log").write_text(
                redact_secrets(prep_demo.stdout + prep_demo.stderr, secrets), encoding="utf-8", newline="\n"
            )
            record_assert("prepare_demo_db_succeeded", prep_demo.returncode == 0, {"exit_code": prep_demo.returncode})

            mig_cp = invoke_psql(
                psql_exe,
                host=settings["host"],
                port=PG_PORT,
                user=settings["adminUser"],
                password=settings["adminPassword"],
                database=DEMO_DATABASE,
                sql='SELECT string_agg("MigrationId", \',\' ORDER BY "MigrationId") FROM eledgercare.__ef_migrations_history;',
                cwd=repo_root,
            )
            applied_migrations = mig_cp.stdout.strip().split(",") if mig_cp.stdout.strip() else []
            record_assert("demo_db_four_migrations_applied", applied_migrations == EXPECTED_MIGRATIONS, applied_migrations)

            denial_sqls = [
                "DELETE FROM eledgercare.documents;",
                "TRUNCATE eledgercare.documents;",
                "UPDATE eledgercare.extraction_results SET finish_reason = 'tampered';",
                "UPDATE eledgercare.work_order_review_revisions SET status = 'reviewed';",
                "DELETE FROM eledgercare.archive_result_projections;",
                "CREATE TABLE eledgercare.unauthorized_probe (id int);",
            ]
            denial_checks = []
            for dsql in denial_sqls:
                dcp = invoke_psql(
                    psql_exe,
                    host=settings["host"],
                    port=PG_PORT,
                    user=settings["appUser"],
                    password=settings["appPassword"],
                    database=DEMO_DATABASE,
                    sql=dsql,
                    cwd=repo_root,
                    expect_success=False,
                )
                denial_checks.append({
                    "verb": dsql.split(" ", 1)[0],
                    "returncode": dcp.returncode,
                    "denied": dcp.returncode != 0 and "permission denied" in dcp.stderr.lower(),
                })
            record_assert(
                "demo_db_app_role_least_privilege_enforced",
                all(d["denied"] for d in denial_checks),
                denial_checks,
            )

            # 7. Prepare scratch DB & run real Edge CPU preflight (`LocalOcr:Enabled=false` + PG/API restart)
            prep_scratch = run_cmd(
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    str(repo_root / "deploy/dev/database/prepare-database.ps1"),
                    "-Database",
                    SCRATCH_PREFLIGHT_DATABASE,
                ],
                cwd=repo_root,
                env=dotnet_env,
            )
            record_assert("prepare_scratch_preflight_db", prep_scratch.returncode == 0, {"exit_code": prep_scratch.returncode})

            api_proc, api_info = start_owned_api(
                api_dll=api_dll,
                settings=settings,
                database=SCRATCH_PREFLIGHT_DATABASE,
                ocr_enabled=False,
                leased_gpu_uuid=None,
                log_path=api_log,
                repo_root=repo_root,
            )
            ui_proc, ui_info = start_owned_ui(node_exe=node_exe, log_path=ui_log, repo_root=repo_root)

            scratch_receipt_rel = (summary_out.parent / "edge-cpu-preflight-scratch.json").relative_to(repo_root).as_posix()
            edge_scratch_cp = run_cmd(
                [
                    str(node_exe),
                    str(edge_driver),
                    "--mode",
                    "cpu-preflight",
                    "--target",
                    "scratch-guard",
                    "--ui-port",
                    str(UI_PORT),
                    "--api-port",
                    str(API_PORT),
                    "--output",
                    scratch_receipt_rel,
                    "--screenshot-dir",
                    args.screenshots_dir,
                ],
                cwd=repo_root,
                timeout_s=180,
            )
            (logs_dir / "03-edge-cpu-preflight-scratch.log").write_text(
                redact_secrets(edge_scratch_cp.stdout + edge_scratch_cp.stderr, secrets), encoding="utf-8", newline="\n"
            )
            record_assert(
                "edge_cpu_preflight_scratch_guard_passed",
                edge_scratch_cp.returncode == 0,
                {"stderr": edge_scratch_cp.stderr.strip()},
            )
            scratch_receipt = json.loads(guard_owned_repo_path(repo_root, scratch_receipt_rel).read_text(encoding="utf-8"))
            scratch_doc_id = scratch_receipt["documentId"]

            # Restart API + PG with LocalOcr:Enabled=false and verify 0 attempts & durable intake reopen
            api_stop_receipts.append(stop_owned_process(api_proc, api_info, repo_root))
            api_proc, api_info = None, None

            stop_pg_mid = run_cmd(
                ["pwsh", "-NoProfile", "-File", str(repo_root / "deploy/dev/postgres/stop-cluster.ps1")],
                cwd=repo_root,
            )
            start_pg_mid = run_cmd(
                ["pwsh", "-NoProfile", "-File", str(repo_root / "deploy/dev/postgres/start-cluster.ps1")],
                cwd=repo_root,
            )
            record_assert(
                "scratch_pg_restart_clean",
                stop_pg_mid.returncode == 0 and start_pg_mid.returncode == 0,
                {"stop_rc": stop_pg_mid.returncode, "start_rc": start_pg_mid.returncode},
            )
            pm_pid = int((pg_data_dir / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
            postmaster_info = inspect_process(pm_pid, repo_root)

            api_proc, api_info = start_owned_api(
                api_dll=api_dll,
                settings=settings,
                database=SCRATCH_PREFLIGHT_DATABASE,
                ocr_enabled=False,
                leased_gpu_uuid=None,
                log_path=api_log,
                repo_root=repo_root,
            )

            scratch_restart_rel = (summary_out.parent / "edge-cpu-preflight-scratch-restart.json").relative_to(repo_root).as_posix()
            edge_restart_cp = run_cmd(
                [
                    str(node_exe),
                    str(edge_driver),
                    "--mode",
                    "cpu-preflight",
                    "--target",
                    "scratch-post-restart",
                    "--document-id",
                    scratch_doc_id,
                    "--ui-port",
                    str(UI_PORT),
                    "--api-port",
                    str(API_PORT),
                    "--output",
                    scratch_restart_rel,
                    "--screenshot-dir",
                    args.screenshots_dir,
                ],
                cwd=repo_root,
                timeout_s=180,
            )
            record_assert(
                "edge_cpu_preflight_post_restart_passed",
                edge_restart_cp.returncode == 0,
                {"stderr": edge_restart_cp.stderr.strip()},
            )

            # Stop API on scratch DB, drop scratch DB cleanly, and verify empty ready `eledgercare_demo_wp0012_reviewer`
            api_stop_receipts.append(stop_owned_process(api_proc, api_info, repo_root))
            api_proc, api_info = None, None

            invoke_psql(
                psql_exe,
                host=settings["host"],
                port=PG_PORT,
                user=settings["adminUser"],
                password=settings["adminPassword"],
                database="postgres",
                sql=f"DROP DATABASE {SCRATCH_PREFLIGHT_DATABASE} WITH (FORCE);",
                cwd=repo_root,
            )

            api_proc, api_info = start_owned_api(
                api_dll=api_dll,
                settings=settings,
                database=DEMO_DATABASE,
                ocr_enabled=False,
                leased_gpu_uuid=None,
                log_path=api_log,
                repo_root=repo_root,
            )

            empty_ready_rel = (summary_out.parent / "edge-cpu-preflight-empty-ready.json").relative_to(repo_root).as_posix()
            edge_empty_cp = run_cmd(
                [
                    str(node_exe),
                    str(edge_driver),
                    "--mode",
                    "cpu-preflight",
                    "--target",
                    "empty-ready-db",
                    "--ui-port",
                    str(UI_PORT),
                    "--api-port",
                    str(API_PORT),
                    "--output",
                    empty_ready_rel,
                    "--screenshot-dir",
                    args.screenshots_dir,
                ],
                cwd=repo_root,
                timeout_s=180,
            )
            (logs_dir / "04-edge-cpu-preflight-empty-ready.log").write_text(
                redact_secrets(edge_empty_cp.stdout + edge_empty_cp.stderr, secrets), encoding="utf-8", newline="\n"
            )
            record_assert(
                "edge_empty_ready_demo_db_verified",
                edge_empty_cp.returncode == 0,
                {"stderr": edge_empty_cp.stderr.strip()},
            )

            ui_stop_receipt = stop_owned_process(ui_proc, ui_info, repo_root)
            ui_proc, ui_info = None, None
            api_stop_receipts.append(stop_owned_process(api_proc, api_info, repo_root))
            api_proc, api_info = None, None

            demo_8_after = compute_canonical_8table_snapshot(psql_exe, settings, DEMO_DATABASE, repo_root)
            demo_proj_after = compute_projection_tables_snapshot(psql_exe, settings, DEMO_DATABASE, repo_root)
            run_entries = list(runs_dir.iterdir())
            record_assert(
                "demo_db_and_runs_dir_completely_empty_for_future_004",
                all(v == 0 for v in demo_8_after["counts"].values())
                and demo_proj_after["projection_count"] == 0
                and demo_proj_after["unit_count"] == 0
                and demo_8_after["fencing_seq"] == {"last_value": 1, "is_called": False}
                and len(run_entries) == 0,
                {
                    "demo_counts": demo_8_after["counts"],
                    "demo_projections": demo_proj_after,
                    "fencing_seq": demo_8_after["fencing_seq"],
                    "run_dir_entries": len(run_entries),
                },
            )

            hist_seed_after = compute_canonical_8table_snapshot(psql_exe, settings, HISTORICAL_SEED_DB, repo_root)
            hist_mig_8_after = compute_canonical_8table_snapshot(psql_exe, settings, HISTORICAL_MIGRATED_DB, repo_root)
            hist_mig_proj_after = compute_projection_tables_snapshot(psql_exe, settings, HISTORICAL_MIGRATED_DB, repo_root)
            q0_after = verify_q0_readonly_pure_stdlib(repo_root)
            record_assert(
                "historical_databases_and_q0_root_unchanged_after_cpu_prep",
                hist_seed_after["canonical_8table_sha256"] == EXPECTED_F3_SEED_8TABLE_SHA
                and hist_mig_8_after["canonical_8table_sha256"] == EXPECTED_F3_SEED_8TABLE_SHA
                and hist_mig_proj_after["projection_tables_sha256"] == EXPECTED_MIGRATED_PROJ_SHA
                and q0_after["verified_model_files"] == q0_check["verified_model_files"]
                and q0_after["verified_notices"] == q0_check["verified_notices"],
                {
                    "seed_f3_sha256": hist_seed_after["canonical_8table_sha256"],
                    "migrated_proj_sha256": hist_mig_proj_after["projection_tables_sha256"],
                },
            )

        else:
            # HELD `/004` live-leased-rehearsal path (never executed during CPU preparation!)
            assert lease_doc is not None
            leased_gpu_uuid = str(lease_doc["gpu_uuid"]).strip()

            gpu_before = run_cmd(
                [
                    "nvidia-smi",
                    "--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory",
                    "--format=csv,noheader",
                ],
                cwd=repo_root,
            )
            record_assert(
                "leased_gpu_idle_before_rehearsal",
                gpu_before.returncode == 0 and gpu_before.stdout.strip() == "",
                {"stdout": gpu_before.stdout.strip()},
            )

            start_pg = run_cmd(
                ["pwsh", "-NoProfile", "-File", str(repo_root / "deploy/dev/postgres/start-cluster.ps1")],
                cwd=repo_root,
            )
            record_assert("pg_cluster_55439_started_live", start_pg.returncode == 0, {"exit_code": start_pg.returncode})
            pm_pid = int((pg_data_dir / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
            postmaster_info = inspect_process(pm_pid, repo_root)

            demo_pre = compute_canonical_8table_snapshot(psql_exe, settings, DEMO_DATABASE, repo_root)
            record_assert(
                "demo_db_zero_seeded_rows_before_live",
                all(v == 0 for v in demo_pre["counts"].values()) and list(runs_dir.iterdir()) == [],
                demo_pre["counts"],
            )

            api_proc, api_info = start_owned_api(
                api_dll=api_dll,
                settings=settings,
                database=DEMO_DATABASE,
                ocr_enabled=True,
                leased_gpu_uuid=leased_gpu_uuid,
                log_path=api_log,
                repo_root=repo_root,
            )
            ui_proc, ui_info = start_owned_ui(node_exe=node_exe, log_path=ui_log, repo_root=repo_root)

            phase1_out = summary_out.parent / "edge-live-phase1.json"
            p1_cp = run_cmd(
                [
                    str(node_exe),
                    str(edge_driver),
                    "--mode",
                    "live-phase1-leased",
                    "--ui-port",
                    str(UI_PORT),
                    "--api-port",
                    str(API_PORT),
                    "--output",
                    phase1_out.relative_to(repo_root).as_posix(),
                    "--screenshot-dir",
                    args.screenshots_dir,
                ],
                cwd=repo_root,
                timeout_s=1200,
            )
            (logs_dir / "05-edge-live-phase1.log").write_text(
                redact_secrets(p1_cp.stdout + p1_cp.stderr, secrets), encoding="utf-8", newline="\n"
            )
            record_assert("edge_live_phase1_completed", p1_cp.returncode == 0, {"stderr": p1_cp.stderr.strip()})
            p1_data = json.loads(phase1_out.read_text(encoding="utf-8"))

            # Restart PG + API with LocalOcr:Enabled=false
            api_stop_receipts.append(stop_owned_process(api_proc, api_info, repo_root))
            api_proc, api_info = None, None
            run_cmd(["pwsh", "-NoProfile", "-File", str(repo_root / "deploy/dev/postgres/stop-cluster.ps1")], cwd=repo_root)
            run_cmd(["pwsh", "-NoProfile", "-File", str(repo_root / "deploy/dev/postgres/start-cluster.ps1")], cwd=repo_root)
            pm_pid = int((pg_data_dir / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
            postmaster_info = inspect_process(pm_pid, repo_root)

            api_proc, api_info = start_owned_api(
                api_dll=api_dll,
                settings=settings,
                database=DEMO_DATABASE,
                ocr_enabled=False,
                leased_gpu_uuid=None,
                log_path=api_log,
                repo_root=repo_root,
            )

            phase2_out = summary_out.parent / "edge-live-phase2-post-restart.json"
            p2_cp = run_cmd(
                [
                    str(node_exe),
                    str(edge_driver),
                    "--mode",
                    "live-phase2-post-restart",
                    "--wo-document-id",
                    p1_data["woDocument"]["documentId"],
                    "--mp-document-id",
                    p1_data["mpDocument"]["documentId"],
                    "--ui-port",
                    str(UI_PORT),
                    "--api-port",
                    str(API_PORT),
                    "--output",
                    phase2_out.relative_to(repo_root).as_posix(),
                    "--screenshot-dir",
                    args.screenshots_dir,
                ],
                cwd=repo_root,
                timeout_s=180,
            )
            (logs_dir / "06-edge-live-phase2-post-restart.log").write_text(
                redact_secrets(p2_cp.stdout + p2_cp.stderr, secrets), encoding="utf-8", newline="\n"
            )
            record_assert("edge_live_phase2_post_restart_completed", p2_cp.returncode == 0, {"stderr": p2_cp.stderr.strip()})

            demo_8_after = compute_canonical_8table_snapshot(psql_exe, settings, DEMO_DATABASE, repo_root)
            demo_proj_after = compute_projection_tables_snapshot(psql_exe, settings, DEMO_DATABASE, repo_root)
            record_assert(
                "exact_two_attempts_and_unchanged_after_restart",
                demo_8_after["counts"]["documents"] == 2
                and demo_8_after["counts"]["execution_attempts"] == 2
                and demo_8_after["counts"]["extraction_results"] == 2
                and len(list(runs_dir.iterdir())) == 2,
                demo_8_after["counts"],
            )

    finally:
        if ui_proc is not None:
            ui_stop_receipt = stop_owned_process(ui_proc, ui_info, repo_root)
        if api_proc is not None:
            api_stop_receipts.append(stop_owned_process(api_proc, api_info, repo_root))

        stop_pg_final = run_cmd(
            ["pwsh", "-NoProfile", "-File", str(repo_root / "deploy/dev/postgres/stop-cluster.ps1")],
            cwd=repo_root,
        )
        (logs_dir / "99-pg-cluster-stop.log").write_text(
            redact_secrets(stop_pg_final.stdout + stop_pg_final.stderr, secrets), encoding="utf-8", newline="\n"
        )

        for lf in logs_dir.glob("*.log"):
            cleaned = redact_secrets(lf.read_text(encoding="utf-8", errors="replace"), secrets)
            lf.write_text(cleaned.replace("\r\n", "\n"), encoding="utf-8", newline="\n")

    pg_status_cp = run_cmd([str(pg_ctl_exe), "status", "-D", str(pg_data_dir)], cwd=repo_root)
    ports_after = observe_ports(REVIEWER_PORTS, repo_root)
    pm_alive = inspect_process(postmaster_info["pid"], repo_root) if postmaster_info else None

    record_assert(
        "all_owned_services_stopped_and_ports_released",
        pg_status_cp.returncode == 3
        and pm_alive is None
        and all(len(ports_after[str(p)]) == 0 for p in REVIEWER_PORTS),
        {"pg_ctl_status_exit": pg_status_cp.returncode, "ports_after": ports_after},
    )

    gpu_after_compute = None
    if args.mode == "live-leased-rehearsal":
        gpu_after_cp = run_cmd(
            ["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,process_name", "--format=csv,noheader"],
            cwd=repo_root,
        )
        gpu_after_compute = gpu_after_cp.stdout.strip()
        record_assert("leased_gpu_idle_on_return", gpu_after_cp.returncode == 0 and gpu_after_compute == "", gpu_after_compute)

    rr_payload = {
        "schema": "eledgercare.wp-0012.reviewer-resource-return/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "mode": args.mode,
        "live_model_or_gpu_executed": args.mode == "live-leased-rehearsal",
        "ports_after": ports_after,
        "pg_ctl_status_exit_code": pg_status_cp.returncode,
        "postmaster_recorded": postmaster_info,
        "postmaster_alive_after": pm_alive is not None,
        "api_stop_receipts": api_stop_receipts,
        "ui_stop_receipt": ui_stop_receipt,
        "retained_databases_in_stopped_cluster": [
            HISTORICAL_SEED_DB,
            HISTORICAL_MIGRATED_DB,
            DEMO_DATABASE,
        ],
        "writable_demo_root": str(WRITABLE_DEMO_ROOT),
        "writable_demo_run_dir_count": len(list(runs_dir.iterdir())),
        "gpu_compute_apps_after": gpu_after_compute,
    }
    rr_text = json.dumps(rr_payload, indent=2) + "\n"
    assert_no_secrets(rr_text, secrets, "resource-return.json")
    rr_out.write_text(rr_text, encoding="utf-8", newline="\n")

    helper_self_bytes = script_path.read_bytes()
    edge_driver_bytes = edge_driver.read_bytes()

    summary_payload = {
        "schema": "eledgercare.wp-0012.reviewer-execution-summary/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "conversation_id": "61105d43-7706-45f2-9176-69d3256248e0",
        "model": "gemini-4-carbon-high",
        "effort": "high",
        "mode": args.mode,
        "live_rehearsal_executed": args.mode == "live-leased-rehearsal",
        "model_or_venv_imported_in_this_run": args.mode == "live-leased-rehearsal",
        "canonical_002_published": False,
        "canonical_004_published": False,
        "branch": branch_name,
        "executing_head_sha": head_sha,
        "accepted_product_base_sha": ACCEPTED_PRODUCT_BASE_SHA,
        "authority_wp0012_sha": AUTHORITY_WP0012_SHA,
        "preserved_tree_oids": tree_oids,
        "helpers": {
            "run_wp0012_reviewer_rehearsal_py_sha256_lf": sha256_hex(helper_self_bytes.replace(b"\r\n", b"\n")),
            "drive_wp0012_edge_workflow_mjs_sha256_lf": sha256_hex(edge_driver_bytes.replace(b"\r\n", b"\n")),
        },
        "owned_resources": {
            "ports": {"api": API_PORT, "ui": UI_PORT, "postgres": PG_PORT},
            "demo_database": DEMO_DATABASE,
            "writable_demo_root": str(WRITABLE_DEMO_ROOT),
            "readonly_q0_root": str(READONLY_Q0_ROOT),
        },
        "demo_database_final_state": {
            "counts": demo_8_after["counts"],
            "projections": demo_proj_after,
            "fencing_seq": demo_8_after["fencing_seq"],
        },
        "assertion_count": len(assertions),
        "assertions": assertions,
    }
    summary_text = json.dumps(summary_payload, indent=2) + "\n"
    assert_no_secrets(summary_text, secrets, "summary-output")
    summary_out.write_text(summary_text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
