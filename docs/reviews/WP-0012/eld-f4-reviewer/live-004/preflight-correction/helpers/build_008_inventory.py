"""Read-only resource reconciliation and exact scoped /008 byte inventory."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[7]
AREA = Path(__file__).resolve().parent.parent
BASE = "36580948f4efe28e35f08762e6bcc1cc4368bb55"
SOURCE = "6fe4a537eb94fb75776f772e3c37fd5a90101fed"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def tree(commit):
    result = {}
    for entry in git("ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
        if entry:
            metadata, path = entry.split(b"\t", 1)
            result[path.decode()] = metadata.decode()
    return result


def main():
    out = AREA / "final-inventory.json"
    assert not out.exists(), "Inventory must be new"
    head = git("rev-parse", "HEAD").decode().strip()
    before, after = tree(BASE), tree(head)
    assert all(after.get(path) == value for path, value in before.items())
    prefix = AREA.relative_to(ROOT).as_posix() + "/"
    additions = sorted(set(after) - set(before))
    assert all(p.startswith(prefix) for p in additions)
    copies = json.loads((AREA / "first-refusal/copy-inventory.json").read_text())
    for item in copies:
        original = Path(item["source"]).read_bytes() if "source" in item else git("show", item["source_git"])
        assert original == (ROOT / item["copy"]).read_bytes()
        assert len(original) == item["bytes"] and digest(original) == item["sha256"]
    root_copies = json.loads((AREA / "root-alias-failure/copy-inventory.json").read_text())
    for item in root_copies:
        data = git("show", item["source_git"])
        assert data == (ROOT / item["copy"]).read_bytes() and digest(data) == item["sha256"]
    source_bindings = []
    for result_path in sorted((AREA / "evidence").glob("*/result.json")):
        record = json.loads(result_path.read_text())
        for path, expected in record["source_files"].items():
            data = git("show", f"{record['executing_head']}:{path}")
            assert digest(data) == expected, (result_path, path)
            source_bindings.append(dict(evidence=result_path.relative_to(ROOT).as_posix(), commit=record["executing_head"], path=path, sha256=expected))
    for name in ("ownership_v6.py", "run_wp0012_reviewer_rehearsal_v6.py", "check_ownership_v6_cpu.py", "check_ownership_v6_cpu_v2.py"):
        path = AREA / "helpers" / name
        assert path.read_bytes() == git("show", f"{SOURCE}:{path.relative_to(ROOT).as_posix()}")

    observed = json.loads((AREA / "evidence/read-only-01/result.json").read_text())["actual_read_only_observation"]
    owned_rows = [r for r in observed["candidate_and_gpu_processes"] if r["ProcessId"] == observed["observer"]["ProcessId"] or r["Name"].lower() == "python.exe"]
    # The only Python in this recorded observation was this lane's exact probe.
    assert [r["ProcessId"] for r in owned_rows] == [34192, 26276]
    ids = ",".join(str(r["ProcessId"]) for r in owned_rows)
    script = "$ErrorActionPreference='Stop'; $owned=@(" + ids + "); $ports=@(5690,4710,55439); @{ports=@(Get-NetTCPConnection -State Listen | Where-Object {$ports -contains $_.LocalPort} | Select-Object LocalPort,OwningProcess); processes=@(Get-CimInstance Win32_Process | Where-Object {$owned -contains $_.ProcessId} | Select-Object ProcessId,Name,CreationDate,ExecutablePath)} | ConvertTo-Json -Compress -Depth 5"
    cp = subprocess.run(["pwsh", "-NoProfile", "-Command", script], cwd=ROOT, capture_output=True, text=True, check=True)
    observation = json.loads(cp.stdout)
    pg = ROOT / ".local/tools/pgsql-18.7-1/bin/pg_ctl.exe"
    pgcp = subprocess.run([str(pg), "status", "-D", str(ROOT / ".local/postgres-data")], cwd=ROOT, capture_output=True, text=True)
    runs = Path("C:/Users/jackg/eLedgerCare-Demo/WP-0012/reviewer/runs")
    run_entries = sorted(p.name for p in runs.iterdir())
    assert observation["ports"] == [] and observation["processes"] == [] and pgcp.returncode == 3 and run_entries == []
    resource = dict(observed_utc=datetime.now(timezone.utc).isoformat(), recorded_probe_processes=owned_rows,
                    current=observation, pg_status_exit=pgcp.returncode, runtime_run_entries=run_entries,
                    no_service_or_model_started=True, no_live_lease_in_this_correction=True,
                    first_lease_closed_by_root="8b6224a44ddbf4658abc5ae1fe3ac0cd2bb96938",
                    missing_original_004_return_receipt_preserved=True)
    resource_path = AREA / "evidence/post-correction-resources.json"
    assert not resource_path.exists()
    resource_path.write_text(json.dumps(resource, indent=2) + "\n", encoding="utf-8")
    artifacts = []
    for path in sorted(AREA.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            data = path.read_bytes()
            artifacts.append(dict(path=path.relative_to(ROOT).as_posix(), bytes=len(data), sha256=digest(data)))
    result = dict(base=BASE, source=SOURCE, executing_inventory_head=head,
                  observed_utc=datetime.now(timezone.utc).isoformat(), inherited_paths_preserved=len(before),
                  inherited_git_metadata_identical=True, own_committed_additions=additions,
                  first_refusal_copies_verified=len(copies), root_failure_copies_verified=len(root_copies),
                  source_bindings=source_bindings, artifacts=artifacts,
                  metadata_after_inventory=[out.relative_to(ROOT).as_posix(), "docs/agent-reports/eld-f4-reviewer/WP-0012/008_2026-11-17_implementation_eld-f4-reviewer.md"],
                  status="own implementation and evidence ready for independent review; no runtime release")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"preserved":len(before), "artifacts":len(artifacts), "source_bindings":len(source_bindings), "copies":len(copies)+len(root_copies), "resources_clear":True}))


if __name__ == "__main__":
    main()
