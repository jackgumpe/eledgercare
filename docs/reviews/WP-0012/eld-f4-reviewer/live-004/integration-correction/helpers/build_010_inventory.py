"""Copy completed /010 observations without rereading another owner's live state."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[7]
AREA = Path(__file__).resolve().parent.parent
EXTERNAL = Path("C:/Users/jackg/eLedgerCare-Demo/WP-0012/reviewer/rehearsal-evidence")
BASE = "ae71a7362718f36e351e3fd442d9751d875146fe"
SOURCE = "5e75cacd11f18bf6135376e3e1e10887c1447e1f"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    assert not path.exists(), path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def tree(commit):
    rows = {}
    for entry in git("ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
        if entry:
            metadata, name = entry.split(b"\t", 1)
            rows[name.decode()] = metadata.decode()
    return rows


def main():
    before, current = tree(BASE), tree("HEAD")
    assert all(current.get(k) == v for k, v in before.items())
    prefix = AREA.relative_to(ROOT).as_posix() + "/"
    assert all(p.startswith(prefix) for p in set(current) - set(before))
    settings = json.loads((ROOT / ".local/secrets/pg-local.json").read_text())
    secrets = [settings[k].encode() for k in ("adminPassword", "appPassword", "migratorPassword")]
    copies, source_bindings = [], []

    def copy_file(source, target):
        data = source.read_bytes()
        assert not any(secret in data for secret in secrets), "Local secret found in copy input"
        assert not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        copies.append(dict(source=str(source), copy=target.relative_to(ROOT).as_posix(), bytes=len(data), sha256=sha(data)))

    mappings = (("WP-0012-reviewer-v7-cpu-controls-01", "evidence/controls-01"),
                ("WP-0012-reviewer-v7-cpu-lifecycle-01", "evidence/lifecycle-01"),
                ("WP-0012-reviewer-v7-cpu-lifecycle-02", "evidence/lifecycle-02"))
    for name, dest in mappings:
        source = EXTERNAL / name
        for path in sorted(source.rglob("*")):
            if path.is_file():
                copy_file(path, AREA / dest / path.relative_to(source))
        result = json.loads((source / "result.json").read_text())
        for path, expected in result["source_files"].items():
            data = git("show", f"{result['executing_head']}:{path}")
            assert sha(data) == expected
            source_bindings.append(dict(evidence=dest + "/result.json", commit=result["executing_head"], path=path, sha256=expected))
    launch = ROOT / ".local/wp0012-reviewer004-r2-20261117T173846Z"
    for path in sorted(launch.iterdir()):
        if path.is_file():
            copy_file(path, AREA / "native-02-refusal" / path.name)
    for name in ("cpu-release-validation.json", "q0-check.json"):
        copy_file(EXTERNAL / "WP-0012-reviewer-004-native-02" / name, AREA / "native-02-refusal" / name)
    closure = "bc5b345d812fdd3bdcf6eb7ae6b5a43b895d8113:docs/coordination/WP-0012/reviewer-004-second-refusal/root-reconciliation.json"
    data = git("show", closure)
    p = AREA / "native-02-refusal/root-reconciliation.json"
    p.write_bytes(data)
    copies.append(dict(source_git=closure, copy=p.relative_to(ROOT).as_posix(), bytes=len(data), sha256=sha(data)))
    dump(AREA / "copy-inventory.json", copies)
    dump(AREA / "evidence/tool-receipts.json", [
        dict(case="controls-01", tool_chunk="9ee9a5", exit_code=0),
        dict(case="lifecycle-01", initial_tool_chunk="1cccf1", completion_tool_chunk="1b76d3", session_id=18960, exit_code=1, limitation="Historical F3 seed has no F4 projection tables; original adapter queried them. Preserved, then new adapter v2 corrected only that check."),
        dict(case="lifecycle-02", initial_tool_chunk="1820db", completion_tool_chunk="f0f063", session_id=51595, exit_code=0),
        dict(case="native-02-runtime-refusal", tool_chunk="f941c2", exit_code=1, validation_exit=0, live_exit=1, wrapper_exit=1, no_model_attempts=True)])
    inputs = []
    for relative in ("workers/local_ocr/manifests/model-files.json", "workers/local_ocr/manifests/dependency-lock.json", "web/package-lock.json", "web/package.json", "deploy/dev/postgres/start-cluster.ps1", "deploy/dev/postgres/stop-cluster.ps1", ".local/tools/pgsql-18.7-1.subset-manifest.json", "src/ELedgerCare.Api/bin/Release/net10.0/ELedgerCare.Api.dll", "src/ELedgerCare.Api/bin/Release/net10.0/ELedgerCare.Api.runtimeconfig.json", "src/ELedgerCare.Api/bin/Release/net10.0/ELedgerCare.Api.deps.json"):
        path = ROOT / relative
        data = path.read_bytes()
        inputs.append(dict(path=str(path), bytes=len(data), sha256=sha(data), disposition="retained locally; existing dependency/source input, no installation"))
    q0 = json.loads((AREA / "evidence/controls-01/actual-q0.json").read_text())
    model_manifest = json.loads((ROOT / "workers/local_ocr/manifests/model-files.json").read_text())
    for row in q0["verified_model_files"]:
        inputs.append(dict(path=str(Path(q0["readonly_q0_root"]) / "models" / model_manifest["model_dir_basename"] / row["path"]), **{k:v for k,v in row.items() if k != "path"}, disposition="read-only pinned Q0 file; stat/hash only, not copied/imported/executed"))
    for row in q0["verified_notices"]:
        inputs.append(dict(path=str(Path(q0["readonly_q0_root"]) / "notices" / model_manifest["notice_dir_basename"] / row["path"]), **{k:v for k,v in row.items() if k != "path"}, disposition="read-only notice; not copied"))
    dump(AREA / "input-inventory.json", dict(inputs=inputs, sensitive_input=dict(path=str(ROOT / ".local/secrets/pg-local.json"), disposition="existing local configuration used in memory; content not copied or exposed"), dependency_manifest_note="Existing PostgreSQL subset actual 1597 files and byte/hash/signature identities are verified by postgres-subset.json against its pinned manifest; Node/Angular/Playwright use existing locked web dependencies, no installs."))
    for name in ("run_wp0012_reviewer_rehearsal_v7.py", "ownership_v6.py"):
        p = AREA / "helpers" / name
        assert p.read_bytes() == git("show", f"{SOURCE}:{p.relative_to(ROOT).as_posix()}")
    artifacts = []
    for p in sorted(AREA.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            data = p.read_bytes()
            assert not any(secret in data for secret in secrets)
            artifacts.append(dict(path=p.relative_to(ROOT).as_posix(), bytes=len(data), sha256=sha(data)))
    dump(AREA / "final-inventory.json", dict(base=BASE, source=SOURCE, inventory_executing_head=git("rev-parse", "HEAD").decode().strip(), observed_utc=datetime.now(timezone.utc).isoformat(), inherited_paths_preserved=len(before), source_bindings=source_bindings, copies=len(copies), input_descriptors=len(inputs), artifacts=artifacts, metadata_after_inventory=[prefix + "final-inventory.json", "docs/agent-reports/eld-f4-reviewer/WP-0012/010_2026-11-17_implementation_eld-f4-reviewer.md"], resource_observation_note="Own completed lifecycle02 receipts at17:52:52Z establish return before sequential independent011 use. This inventory performs no current service/GPU/database observation or mutation."))
    print(json.dumps(dict(preserved=len(before), artifacts=len(artifacts), copies=len(copies), source_bindings=len(source_bindings), input_descriptors=len(inputs), secret_scan_passed=True)))


if __name__ == "__main__":
    main()
