"""Decisive verification helper for WP-0006 F2 independent reviewer resource preparation.

Verifies isolated reviewer resources under C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\eld-next-reviewer:
1. Clean tracked repository/lockfile state and absence of premature external F2 runtime roots.
2. PostgreSQL 18.7 server subset integrity (1,597 files, 151,078,582 bytes, zero reparse points,
   subset_manifest_sha256, central_directory_sha256, binary versions, and Authenticode signatures).
3. Owned .local/secrets/pg-local.json metadata and distinctness without exposing any secret value.
4. Loopback port availability (5290, 4310, 55435), owned PostgreSQL 18.7 start on 127.0.0.1:55435,
   SCRAM-SHA-256 role/durability queries, clean fast stop, process exit, and retained cluster state.
5. Locked .NET/NuGet/dotnet-ef, Node/npm/Angular/Playwright, and local Microsoft Edge readiness.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import pathlib
import stat
import subprocess
import sys
import zlib

EXPECTED_SUBSET_SHA = "47c3deb9c917f79c353b3683b2c2611ee975285ea06226c8f72444c96ce9051f"
EXPECTED_CD_SHA = "3132ca63b424f7ec371eabe50753ad7cd036278d942a6ea465547b17bf90a149"
EXPECTED_PG_FILES = 1597
EXPECTED_PG_BYTES = 151_078_582
REVIEWER_PORTS = (5290, 4310, 55435)
REPARSE_ATTR = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def is_reparse_or_link(path: pathlib.Path) -> bool:
    st = os.lstat(path)
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & REPARSE_ATTR)


def run_cmd(argv: list[str], *, cwd: pathlib.Path, env: dict[str, str] | None = None, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        env=env,
        input=input_text,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=120,
        check=False,
    )


def observe_ports(ports: tuple[int, ...], cwd: pathlib.Path) -> dict[str, list[dict]]:
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


def verify_pg_subset(local_tools: pathlib.Path, cwd: pathlib.Path) -> dict:
    manifest_path = local_tools / "pgsql-18.7-1.subset-manifest.json"
    pg_root = local_tools / "pgsql-18.7-1"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    present_files: list[str] = []
    reparse_points: list[str] = []
    for dirpath, dirnames, filenames in os.walk(pg_root, followlinks=False):
        for dname in list(dirnames):
            dp = pathlib.Path(dirpath) / dname
            if is_reparse_or_link(dp):
                reparse_points.append(dp.relative_to(pg_root).as_posix())
                dirnames.remove(dname)
        for fname in filenames:
            fp = pathlib.Path(dirpath) / fname
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
        sha = hashlib.sha256(data).hexdigest()
        crc = f"{zlib.crc32(data) & 0xFFFFFFFF:08x}"
        if len(data) != exp["bytes"] or sha != exp["sha256"] or crc != exp["crc32"]:
            mismatches.append(rel)
        total_bytes += len(data)
        lines.append(f"{sha}  {rel}")

    recomputed_subset_sha = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()

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
        "source_url": manifest["source_url"],
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


def verify_nuget_locks(repo_root: pathlib.Path, nuget_packages_dir: pathlib.Path) -> dict:
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


def invoke_psql(psql_exe: pathlib.Path, host: str, port: int, user: str, password: str, db: str, sql: str, cwd: pathlib.Path) -> str:
    env = dict(os.environ)
    env["PGPASSWORD"] = password
    cp = run_cmd(
        [str(psql_exe), "-X", "-q", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-h", host, "-p", str(port), "-U", user, "-d", db, "-f", "-"],
        cwd=cwd,
        env=env,
        input_text=sql,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"psql query failed for role {user}: {cp.stderr.strip()}")
    return cp.stdout.strip()


def inspect_process(pid: int, cwd: pathlib.Path) -> dict | None:
    ps = (
        f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
        "if ($null -eq $p) { 'null' } else { "
        "@{ pid = [int]$p.Id; name = $p.ProcessName; startUtc = $p.StartTime.ToUniversalTime().ToString('o') } | ConvertTo-Json -Compress }"
    )
    cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps], cwd=cwd)
    if cp.returncode != 0 or cp.stdout.strip() == "null":
        return None
    return json.loads(cp.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(pathlib.Path(__file__).resolve().parents[5]))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repo_root = pathlib.Path(args.repo_root).resolve()
    local_dir = repo_root / ".local"
    local_tools = local_dir / "tools"
    pg_data = local_dir / "postgres-data"
    settings_path = local_dir / "secrets" / "pg-local.json"
    psql_exe = local_tools / "pgsql-18.7-1" / "bin" / "psql.exe"
    pg_ctl_exe = local_tools / "pgsql-18.7-1" / "bin" / "pg_ctl.exe"

    head_sha = run_cmd(["git", "--no-optional-locks", "rev-parse", "HEAD"], cwd=repo_root).stdout.strip()
    branch = run_cmd(["git", "--no-optional-locks", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root).stdout.strip()
    git_status_before = run_cmd(["git", "--no-optional-locks", "status", "--porcelain=v1"], cwd=repo_root).stdout.strip()

    # Load secret settings internally; extract secrets ONLY into local variables for connection & leak-scrubbing
    raw_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    secrets_to_scrub = [
        str(raw_settings.get("adminPassword", "")),
        str(raw_settings.get("migratorPassword", "")),
        str(raw_settings.get("appPassword", "")),
    ]
    if any(len(s) < 32 for s in secrets_to_scrub) or len(set(secrets_to_scrub)) != 3:
        raise RuntimeError("Owned cluster credentials do not meet >=32-char distinct secret requirement.")

    safe_cluster_config = {
        "host": raw_settings["host"],
        "port": int(raw_settings["port"]),
        "admin_role": raw_settings["adminUser"],
        "migrator_role": raw_settings["migratorUser"],
        "app_role": raw_settings["appUser"],
        "configured_dev_database": raw_settings["devDatabase"],
        "credentials_distinct_and_min_32_chars": True,
        "secret_values_redacted": True,
    }

    pg_subset_report = verify_pg_subset(local_tools, repo_root)
    ports_before = observe_ports(REVIEWER_PORTS, repo_root)
    if any(ports_before[str(p)] for p in REVIEWER_PORTS):
        raise RuntimeError(f"Expected all reviewer ports {REVIEWER_PORTS} unbound before start, got: {ports_before}")

    postmaster_info = None
    ports_during = None
    server_settings = {}
    role_catalog = []
    databases_present = []
    role_login_probes = {}
    stop_exit_code = None

    start_script = repo_root / "deploy" / "dev" / "postgres" / "start-cluster.ps1"
    stop_script = repo_root / "deploy" / "dev" / "postgres" / "stop-cluster.ps1"

    start_cp = run_cmd(["pwsh", "-NoProfile", "-File", str(start_script)], cwd=repo_root)
    if start_cp.returncode != 0:
        raise RuntimeError(f"start-cluster.ps1 failed ({start_cp.returncode}): {start_cp.stderr}")

    try:
        pid_file = pg_data / "postmaster.pid"
        pm_pid = int(pid_file.read_text(encoding="utf-8").splitlines()[0].strip())
        postmaster_info = inspect_process(pm_pid, repo_root)
        if postmaster_info is None:
            raise RuntimeError(f"Started postmaster PID {pm_pid} not observable via Get-Process")

        ports_during = observe_ports(REVIEWER_PORTS, repo_root)

        settings_rows = invoke_psql(
            psql_exe,
            raw_settings["host"],
            int(raw_settings["port"]),
            raw_settings["adminUser"],
            raw_settings["adminPassword"],
            "postgres",
            "SELECT name || '=' || setting FROM pg_settings "
            "WHERE name IN ('server_version','listen_addresses','port','password_encryption',"
            "'fsync','full_page_writes','synchronous_commit','wal_level','data_checksums','default_transaction_isolation') "
            "ORDER BY name;",
            repo_root,
        )
        for line in settings_rows.splitlines():
            k, v = line.split("=", 1)
            server_settings[k] = v

        roles_raw = invoke_psql(
            psql_exe,
            raw_settings["host"],
            int(raw_settings["port"]),
            raw_settings["adminUser"],
            raw_settings["adminPassword"],
            "postgres",
            "SELECT rolname || '|' || rolcanlogin || '|' || rolsuper || '|' || rolcreatedb || '|' || "
            "rolcreaterole || '|' || rolinherit || '|' || (rolpassword LIKE 'SCRAM-SHA-256$%') "
            "FROM pg_authid WHERE rolname IN ('eledgercare_admin','eledgercare_migrator','eledgercare_app') "
            "ORDER BY rolname;",
            repo_root,
        )
        for row in roles_raw.splitlines():
            rname, login, sup, cdb, crl, inh, scram = row.split("|")
            role_catalog.append(
                {
                    "role": rname,
                    "can_login": login in ("t", "true"),
                    "superuser": sup in ("t", "true"),
                    "create_db": cdb in ("t", "true"),
                    "create_role": crl in ("t", "true"),
                    "inherit": inh in ("t", "true"),
                    "has_scram_sha256_verifier": scram in ("t", "true"),
                }
            )

        dbs_raw = invoke_psql(
            psql_exe,
            raw_settings["host"],
            int(raw_settings["port"]),
            raw_settings["adminUser"],
            raw_settings["adminPassword"],
            "postgres",
            "SELECT datname FROM pg_database WHERE NOT datistemplate ORDER BY datname;",
            repo_root,
        )
        databases_present = [d for d in dbs_raw.splitlines() if d]

        for role_key, pass_key in (("migratorUser", "migratorPassword"), ("appUser", "appPassword")):
            probe = invoke_psql(
                psql_exe,
                raw_settings["host"],
                int(raw_settings["port"]),
                raw_settings[role_key],
                raw_settings[pass_key],
                "postgres",
                "SELECT current_user || '|' || inet_server_addr()::text || '|' || inet_server_port()::text;",
                repo_root,
            )
            c_user, s_addr, s_port = probe.split("|")
            role_login_probes[c_user] = {"server_addr": s_addr.split("/")[0], "server_port": int(s_port)}
    finally:
        stop_cp = run_cmd(["pwsh", "-NoProfile", "-File", str(stop_script)], cwd=repo_root)
        stop_exit_code = stop_cp.returncode

    pg_ctl_after = run_cmd([str(pg_ctl_exe), "status", "-D", str(pg_data)], cwd=repo_root)
    proc_after = inspect_process(postmaster_info["pid"], repo_root) if postmaster_info else None
    postmaster_still_alive = (
        proc_after is not None and proc_after.get("startUtc") == postmaster_info.get("startUtc")
    )
    ports_after = observe_ports(REVIEWER_PORTS, repo_root)

    # Toolchain & locked package cache checks
    dotnet_env = dict(os.environ)
    dotnet_env["NUGET_PACKAGES"] = str(local_dir / "nuget" / "packages")
    dotnet_env["DOTNET_CLI_HOME"] = str(local_dir / "dotnet-home")
    dotnet_env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    dotnet_env["DOTNET_NOLOGO"] = "1"

    sdk_ver = run_cmd(["dotnet", "--version"], cwd=repo_root, env=dotnet_env).stdout.strip()
    runtimes = [
        line.strip()
        for line in run_cmd(["dotnet", "--list-runtimes"], cwd=repo_root, env=dotnet_env).stdout.splitlines()
        if line.strip()
    ]
    ef_cp = run_cmd(["dotnet", "tool", "run", "dotnet-ef", "--version"], cwd=repo_root, env=dotnet_env)
    ef_ver = ef_cp.stdout.strip().splitlines()[-1].strip() if ef_cp.returncode == 0 and ef_cp.stdout.strip() else ""

    nuget_audit = verify_nuget_locks(repo_root, local_dir / "nuget" / "packages")

    node_ver = run_cmd(["node", "--version"], cwd=repo_root).stdout.strip()
    npm_ver = run_cmd(["npm.cmd" if os.name == "nt" else "npm", "--version"], cwd=repo_root).stdout.strip()
    pw_cli = repo_root / "web" / "node_modules" / "@playwright" / "test" / "cli.js"
    pw_ver = run_cmd(["node", str(pw_cli), "--version"], cwd=repo_root / "web").stdout.strip() if pw_cli.is_file() else ""
    ng_pkg = repo_root / "web" / "node_modules" / "@angular" / "cli" / "package.json"
    ng_ver = json.loads(ng_pkg.read_text(encoding="utf-8"))["version"] if ng_pkg.is_file() else ""

    edge_candidates = [
        pathlib.Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        pathlib.Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]
    edge_path = next((p for p in edge_candidates if p.is_file()), None)
    edge_ver = ""
    if edge_path is not None:
        edge_ps = f"(Get-Item -LiteralPath '{str(edge_path)}').VersionInfo.ProductVersion"
        edge_ver = run_cmd(["pwsh", "-NoProfile", "-Command", edge_ps], cwd=repo_root).stdout.strip()

    f2_reviewer_runtime_root = pathlib.Path(r"C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer")
    git_status_after = run_cmd(["git", "--no-optional-locks", "status", "--porcelain=v1"], cwd=repo_root).stdout.strip()

    assertions = {
        "clean_git_tree_before_and_after": git_status_before == "" and git_status_after == "",
        "pg_subset_1597_files_exact_hashes_and_no_reparse": (
            pg_subset_report["expected_subset_manifest_sha256_match"]
            and pg_subset_report["expected_central_directory_sha256_match"]
            and pg_subset_report["verified_file_count"] == EXPECTED_PG_FILES
            and pg_subset_report["verified_total_bytes"] == EXPECTED_PG_BYTES
            and not pg_subset_report["missing_files"]
            and not pg_subset_report["extra_files"]
            and not pg_subset_report["hash_or_crc_mismatches"]
            and not pg_subset_report["reparse_points"]
        ),
        "pg_core_binaries_authenticode_valid": all(
            v["status"] == "Valid" for v in pg_subset_report["authenticode_core_binaries"].values()
        ),
        "ports_5290_4310_55435_free_before_start": all(not ports_before[str(p)] for p in REVIEWER_PORTS),
        "cluster_bound_strictly_loopback_55435_during_run": (
            ports_during is not None
            and len(ports_during["55435"]) == 1
            and ports_during["55435"][0]["localAddress"] == "127.0.0.1"
            and ports_during["55435"][0]["owningPid"] == postmaster_info["pid"]
        ),
        "server_durability_and_scram_settings_verified": (
            server_settings.get("server_version") == "18.7"
            and server_settings.get("listen_addresses") == "127.0.0.1"
            and server_settings.get("port") == "55435"
            and server_settings.get("password_encryption") == "scram-sha-256"
            and server_settings.get("fsync") == "on"
            and server_settings.get("full_page_writes") == "on"
            and server_settings.get("synchronous_commit") == "on"
            and server_settings.get("wal_level") == "replica"
        ),
        "roles_and_scram_logins_verified": (
            len(role_catalog) == 3
            and all(r["has_scram_sha256_verifier"] for r in role_catalog)
            and set(role_login_probes) == {"eledgercare_migrator", "eledgercare_app"}
            and all(v == {"server_addr": "127.0.0.1", "server_port": 55435} for v in role_login_probes.values())
        ),
        "no_premature_product_db_or_f2_migrations_applied": databases_present == ["postgres"],
        "cluster_stopped_cleanly_and_files_retained": (
            stop_exit_code == 0
            and pg_ctl_after.returncode != 0
            and not (pg_data / "postmaster.pid").exists()
            and not postmaster_still_alive
            and not ports_after["55435"]
            and (pg_data / "PG_VERSION").read_text(encoding="utf-8").strip() == "18"
        ),
        "toolchain_and_locked_caches_ready": (
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
        "external_f2_reviewer_runtime_root_not_created": not f2_reviewer_runtime_root.exists(),
    }

    helper_bytes = pathlib.Path(__file__).read_bytes()
    payload = {
        "schema": "eld-wp0006-reviewer-preparation-receipt/1",
        "observed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": branch,
        "executing_head": head_sha,
        "helper_path": "docs/reviews/WP-0006/eld-next-reviewer/preparation/verify_preparation.py",
        "helper_sha256": hashlib.sha256(helper_bytes).hexdigest(),
        "scope_note": "Isolated reviewer resource preparation only at pre-F2 application base; not canonical WP-0006 /004 acceptance.",
        "assertions": assertions,
        "all_assertions_passed": all(assertions.values()),
        "postgres_binary_provenance": pg_subset_report,
        "owned_cluster": {
            "config": safe_cluster_config,
            "ports_before_start": ports_before,
            "started_postmaster": postmaster_info,
            "ports_during_run": ports_during,
            "server_settings": server_settings,
            "roles": role_catalog,
            "non_template_databases": databases_present,
            "scram_role_login_probes": role_login_probes,
            "stop_exit_code": stop_exit_code,
            "pg_ctl_status_rc_after_stop": pg_ctl_after.returncode,
            "postmaster_alive_after_stop": postmaster_still_alive,
            "ports_after_stop": ports_after,
            "retained_owned_paths": {
                "pg_binaries": str(local_tools / "pgsql-18.7-1"),
                "pg_subset_manifest": str(local_tools / "pgsql-18.7-1.subset-manifest.json"),
                "pg_data_dir": str(pg_data),
                "pg_log": str(local_dir / "logs" / "postgres.log"),
                "pg_secrets_file": str(settings_path),
                "nuget_packages": str(local_dir / "nuget" / "packages"),
                "dotnet_cli_home": str(local_dir / "dotnet-home"),
                "npm_cache": str(local_dir / "npm-cache"),
                "web_node_modules": str(repo_root / "web" / "node_modules"),
            },
        },
        "toolchain_and_caches": {
            "dotnet_sdk": sdk_ver,
            "dotnet_runtimes": runtimes,
            "dotnet_ef_local_tool": ef_ver,
            "nuget_lock_audit": nuget_audit,
            "nodejs": node_ver,
            "npm": npm_ver,
            "angular_cli_local": ng_ver,
            "playwright_cli_local": pw_ver,
            "msedge_path": str(edge_path) if edge_path else None,
            "msedge_version": edge_ver,
        },
        "external_f2_reviewer_runtime_root": {
            "path": str(f2_reviewer_runtime_root),
            "exists": f2_reviewer_runtime_root.exists(),
        },
    }

    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    for secret in secrets_to_scrub:
        if secret and secret in serialized:
            raise RuntimeError("Refusing to write receipt: secret substring detected in output!")

    out_path = pathlib.Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(serialized.encode("utf-8"))
    return 0 if payload["all_assertions_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
