"""Read-only accounting after actual reviewer004 and explicit root ACK.

Uses the same inventory/read-only SQL approach as author003's collector, but
independently binds reviewer resources, historical snapshots and actual return.
No API/UI/model invocation, source repair, retry, migration or database write.
"""
from datetime import datetime, timezone
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
BASE = "bf2172c9ecaab63de038300960082f3b521f8074"
AUTH = "2d19a46b0d5e31995c5a00720faa285a61ab4fa8"
ACK = "6a3408747201693a45aa09228af58420ea07cdef"
LEASE = "WP-0012-reviewer-004-r3-20261117T181101Z"
AREA = ROOT / "docs/reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004"
OUT = AREA / "evidence"
RUNTIME = Path("C:/Users/jackg/eLedgerCare-Demo/WP-0012/reviewer")
LIVE = RUNTIME / "rehearsal-evidence/WP-0012-reviewer-004-native-03"
LAUNCH = ROOT / ".local/wp0012-reviewer004-r3-20261117T181101Z"
sys.path.insert(0, str(ROOT / "docs/reviews/WP-0012/eld-f4-reviewer/preparation/helpers"))
import run_wp0012_reviewer_rehearsal as prep


def utc(): return datetime.now(timezone.utc).isoformat()
def sha(data): return hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.check_output(["git", *args], cwd=ROOT)
def put(path, data):
    target = OUT / path
    assert not target.exists(), target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return dict(path=target.relative_to(ROOT).as_posix(), bytes=len(data), sha256=sha(data))
def js(path, obj): return put(path, (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode())


def exact_filetime_alive(pid, creation):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4)]
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        assert error == 87, f"Unknown process observation error {error}"
        return False
    try:
        values = [wintypes.FILETIME() for _ in range(4)]
        assert kernel.GetProcessTimes(handle, *(ctypes.byref(x) for x in values))
        actual = (values[0].dwHighDateTime << 32) | values[0].dwLowDateTime
        return actual == creation
    finally:
        kernel.CloseHandle(handle)


def main():
    head = git("rev-parse", "HEAD").decode().strip()
    assert not git("status", "--porcelain", "--untracked-files=all").strip()
    changes = git("diff", "--name-only", BASE, head).decode().splitlines()
    prefix = AREA.relative_to(ROOT).as_posix() + "/"
    assert changes and all(p.startswith(prefix) for p in changes)
    assert not git("diff", "--diff-filter=MD", "--name-only", BASE, head).strip()
    assert not OUT.exists()
    ack_path = "docs/coordination/WP-0012/reviewer-004-after/lease-return-ack.json"
    ack = json.loads(git("show", f"{ACK}:{ack_path}"))
    assert ack["status"] == "RETURN_ACKNOWLEDGED" and ack["lease_id"] == LEASE
    assert ack["lease_returned"] is True and ack["clean_return_verified"] is True
    launch = json.loads((LAUNCH / "launcher-receipt.json").read_text())
    returned = json.loads((LIVE / "resource-return.json").read_text())
    assert launch["executing_head"] == BASE and launch["wrapper_exit_code"] == 0
    assert [r["mode"] for r in launch["invocations"]] == ["validate-release-cpu", "live-leased-rehearsal"]
    assert all(r["exit_code"] == 0 for r in launch["invocations"])
    assert returned["lease_id"] == LEASE and returned["clean_return_verified"] is True
    OUT.mkdir(parents=True, exist_ok=False)
    settings = json.loads((ROOT / ".local/secrets/pg-local.json").read_text())
    secrets = [settings[k] for k in ("adminPassword", "migratorPassword", "appPassword")]
    artifacts = []
    for source_root, target_root in ((RUNTIME / "runs", Path("attempts")), (LIVE, Path("browser")), (LAUNCH, Path("launch"))):
        for path in sorted(source_root.rglob("*")):
            if not path.is_file(): continue
            assert not prep.is_reparse_or_link(path)
            data = path.read_bytes()
            relative = path.relative_to(source_root)
            item = dict(source_root=str(source_root), source_path=relative.as_posix(), bytes=len(data), sha256=sha(data))
            if "cache" in relative.parts:
                item["disposition"] = "retained-only-generated-cache"
            else:
                assert not any(secret.encode() in data for secret in secrets), "Credential in original artifact; preserve and stop"
                item.update(disposition="copied-byte-identical", copy=put(target_root / relative, data))
            artifacts.append(item)
    release_path = "docs/coordination/WP-0012/releases/reviewer-004-r3.json"
    release = json.loads(git("show", f"{AUTH}:{release_path}"))
    bindings = [(AUTH, release_path), (AUTH, "docs/kickoffs/WP-0012-eld-f4-reviewer-live-004-r3.md"), (ACK, ack_path),
                (ACK, "docs/coordination/WP-0012/reviewer-004-after/root-receipt-writer-correction.json"),
                ("ed9651edfb4206cb13d564924a342b91679277c2", "docs/agent-reports/eld-f4-implementer/WP-0012/011_2026-11-17_review_eld-f4-implementer.md"),
                ("bd21e07eb322ea64dee59ba5562ee6b03087d079", "docs/agent-reports/eld-f4-implementer/WP-0012/003_2026-11-17_verification_eld-f4-implementer.md")]
    bindings += [(AUTH, d["path"]) for d in release["observation_files"].values()]
    git_inputs = []
    for index, (commit, path) in enumerate(bindings):
        data = git("show", f"{commit}:{path}")
        git_inputs.append(dict(commit=commit, path=path, sha256=sha(data), copy=put(Path("bindings") / f"{index:02d}-{Path(path).name}", data)))
    prior_count = 0
    for inventory in ("preflight-correction/first-refusal/copy-inventory.json", "integration-correction/copy-inventory.json"):
        rows = json.loads((AREA.parent / inventory).read_text())
        for row in rows:
            if "source" in row:
                data = Path(row["source"]).read_bytes()
                assert sha(data) == row["sha256"] and len(data) == row["bytes"]
                prior_count += 1

    pgctl = ROOT / ".local/tools/pgsql-18.7-1/bin/pg_ctl.exe"
    psql = ROOT / ".local/tools/pgsql-18.7-1/bin/psql.exe"
    pgdata = ROOT / ".local/postgres-data"
    assert all(v == [] for v in prep.observe_ports((5690,4710,55439), ROOT).values())
    assert prep.run_cmd([str(pgctl), "status", "-D", str(pgdata)], cwd=ROOT).returncode == 3
    commands, database, preservation = [], {}, {}
    def command(argv):
        cp = prep.run_cmd(argv, cwd=ROOT)
        commands.append(dict(command=argv, exit_code=cp.returncode, utc=utc(), stdout=prep.redact_secrets(cp.stdout, secrets), stderr=prep.redact_secrets(cp.stderr, secrets)))
        assert cp.returncode == 0, "Owned accounting command failed"
    def query(db, sql):
        cp = prep.run_cmd([str(psql), "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-h", settings["host"], "-p", str(settings["port"]), "-U", settings["adminUser"], "-d", db, "-c", sql], cwd=ROOT,
                          env={**os.environ, "PGPASSWORD":settings["adminPassword"], "PGOPTIONS":"-c default_transaction_read_only=on"})
        assert cp.returncode == 0, prep.redact_secrets(cp.stderr, secrets)
        return cp.stdout.strip()
    accounting_started = utc()
    assert accounting_started > ack["utc"]
    old_options = os.environ.get("PGOPTIONS")
    try:
        command(["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"])
        assert query("eledgercare_demo_wp0012_reviewer", "SHOW transaction_read_only;") == "on"
        tables = query("eledgercare_demo_wp0012_reviewer", "SELECT tablename FROM pg_tables WHERE schemaname='eledgercare' ORDER BY tablename;").splitlines()
        for table in tables:
            assert re.fullmatch(r"[A-Za-z0-9_]+", table)
            sql = "SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text), '[]'::jsonb) FROM eledgercare." + chr(34) + table + chr(34) + " t;"
            database[table] = json.loads(query("eledgercare_demo_wp0012_reviewer", sql))
        js("database/post-restart-tables.json", database)
        baseline = json.loads((AREA.parent / "integration-correction/evidence/lifecycle-02/complete-cpu-lifecycle/adapter-result.json").read_text())["historical_databases_unchanged"]
        os.environ["PGOPTIONS"] = "-c default_transaction_read_only=on"
        for db in baseline:
            state = dict(core=prep.compute_canonical_8table_snapshot(psql, settings, db, ROOT))
            if "projection" in baseline[db]: state["projection"] = prep.compute_projection_tables_snapshot(psql, settings, db, ROOT)
            preservation[db] = state
            assert state == baseline[db], "Historical database changed"
    finally:
        if old_options is None: os.environ.pop("PGOPTIONS", None)
        else: os.environ["PGOPTIONS"] = old_options
        try:
            command(["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"])
        finally:
            js("database/accounting-commands.json", dict(started_utc=accounting_started, finished_utc=utc(), root_ack=ACK, commands=commands))
    js("database/historical-preservation.json", preservation)
    ports = prep.observe_ports((5690,4710,55439), ROOT)
    assert all(v == [] for v in ports.values())
    assert prep.run_cmd([str(pgctl), "status", "-D", str(pgdata)], cwd=ROOT).returncode == 3
    identities = [launch["wrapper_identity"], *[i["identity"] for i in launch["invocations"]]]
    for row in database["execution_attempts"]:
        for role in ("supervisor", "launcher", "worker"):
            if row.get(role+"_pid") and row.get(role+"_create_filetime"):
                identities.append(dict(role=role, pid=row[role+"_pid"], create_filetime=row[role+"_create_filetime"]))
    for item in identities:
        assert not exact_filetime_alive(int(item["pid"]), int(item["create_filetime"])), "Owned exact process remains alive"
    for row in database["execution_attempts"]:
        assert row["attempt_number"] == 1 and row["retried_from_attempt_id"] is None
    assert len(database["execution_attempts"]) == 2 and len(database["extraction_results"]) == 2
    source_paths = changes
    source_inventory = [dict(path=p, sha256=sha((ROOT/p).read_bytes()), git_blob_oid=git("rev-parse", f"{head}:{p}").decode().strip()) for p in source_paths]
    js("collection-inventory.json", dict(schema="eledgercare.wp0012.reviewer004-collection/1", collected_utc=utc(), runtime_head=BASE, collector_head=head, source_inventory=source_inventory, inherited_paths_unchanged=len(git("ls-tree","-r","--name-only",BASE).decode().splitlines()), release=AUTH, root_ack=ACK, lease_id=LEASE, originals=artifacts, git_inputs=git_inputs, prior_external_artifacts_unchanged=prior_count, table_row_counts={k:len(v) for k,v in database.items()}, historical_preservation=preservation, owned_exact_identities_exited=identities, ports_after_accounting=ports, pg_status=3, no_additional_model_calls=True, copied_files=[dict(path=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size, sha256=sha(p.read_bytes())) for p in sorted(OUT.rglob("*")) if p.is_file()]))
    print(json.dumps(dict(status="collected", external_files=len(artifacts), retained_cache=sum(i["disposition"] == "retained-only-generated-cache" for i in artifacts), table_rows={k:len(v) for k,v in database.items()}, pg_status=3, ports=ports)))


if __name__ == "__main__":
    main()
