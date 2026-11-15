"""WP-0005 Q0 harness command line (research qualification only; not product code).

CPU commands (stdlib only, safe now):
  verify-snapshots          upstream snapshots == pinned HF blobs; static save-path safety facts
  build-model-manifest      (re)derive manifests/model-files.json from the pinned HF tree; --check compares
  derive-rasters            predicted 300-DPI RGB digests from committed dev v1-raster300 PDFs; --check compares
  check-protocol            validate protocol.json and the dev fixture digests
  status                    readiness of every execution gate (lock, release, storage)
  verify-model DIR          verify an acquired model directory (acquisition stage; reads only)

Installation-stage commands (refuse while the lock is not final):
  write-requirements FILE   hash-pinned requirements for pip --no-index --require-hashes
  verify-wheelhouse DIR     wheelhouse holds exactly the locked wheels with matching SHA-256
  preflight-cpu [--model-dir DIR]  task-venv CPU preflight: installed set, renderer, rasters, model files

Released-stage commands (refuse unless the lock is final and a coordinator release binds the run):
  execute --owner author|reviewer --release FILE   supervise one child run
  child ...                                         internal; started only by execute
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))  # explicit: works under -P/-I, which do not add the script dir

from q0harness import modelfiles, sourcecheck  # noqa: E402
from q0harness.environment import build_child_env, default_forbidden_parents, layout  # noqa: E402
from q0harness.fixtures import derive_predicted_rasters, read_verified_fixture  # noqa: E402
from q0harness.hashing import sha256_bytes  # noqa: E402
from q0harness.locks import load_lock, validate_lock  # noqa: E402
from q0harness.outcome import BLOCKED, Q0Failure, make_outcome  # noqa: E402
from q0harness.protocol import HARNESS_DIR, REPO_ROOT, load_protocol  # noqa: E402

LOCK_PATH = HARNESS_DIR / "locks" / "dependency-lock.json"
MANIFEST_PATH = HARNESS_DIR / "manifests" / "model-files.json"


def _print(obj):
    sys.stdout.write(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def cmd_verify_snapshots(_):
    rows = sourcecheck.verify_snapshots(REPO_ROOT)
    facts = sourcecheck.analyze_model_sources(sourcecheck.SNAPSHOT_DIR, sourcecheck.SNAPSHOT_NAMES)
    _print({"snapshots_verified": len(rows), "snapshots": rows, "static_safety_facts": facts})


def cmd_build_model_manifest(a):
    tree = json.loads(sourcecheck.HF_TREE.read_text(encoding="utf-8"))
    manifest = modelfiles.build_manifest_from_tree(tree)
    text = json.dumps(manifest, indent=2) + "\n"
    if a.check:
        same = MANIFEST_PATH.read_text(encoding="utf-8") == text
        _print({"manifest": str(MANIFEST_PATH), "identical_to_derivation": same})
        return 0 if same else 1
    if MANIFEST_PATH.exists():
        raise SystemExit("refusing to overwrite an existing manifest; use --check")
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "x", encoding="utf-8", newline="\n") as f:
        f.write(text)
    _print({"written": str(MANIFEST_PATH)})


def cmd_derive_rasters(a):
    protocol, _ = load_protocol() if a.check else (json.loads((HARNESS_DIR / "protocol.json").read_text(encoding="utf-8")), None)
    out = {f["fixture_id"]: derive_predicted_rasters(f) for f in protocol["fixtures"]}
    if a.check:
        same = {fid: out[fid] == [{k: p[k] for k in ("page", "width", "height", "rgb_sha256")} for p in f["raster"]]
                for fid, f in ((f["fixture_id"], f) for f in protocol["fixtures"])}
        _print({"derived": out, "identical_to_protocol": same})
        return 0 if all(same.values()) else 1
    _print(out)


def cmd_check_protocol(_):
    protocol, digest = load_protocol()
    fixtures = {f["fixture_id"]: len(read_verified_fixture(f)) for f in protocol["fixtures"]}
    _print({"protocol_sha256": digest, "fixtures_verified_bytes": fixtures})


def cmd_status(_):
    protocol, digest = load_protocol()
    lock_raw = LOCK_PATH.read_bytes()
    gates = {"protocol_sha256": digest, "lock_sha256": sha256_bytes(lock_raw)}
    try:
        validate_lock(json.loads(lock_raw))
        gates["dependency_lock"] = "final"
    except Q0Failure as f:
        gates["dependency_lock"] = f.as_record()
    root = Path(protocol["storage"]["root"])
    gates["storage_root_exists"] = root.exists()
    gates["execution_release"] = "none supplied (WP-0005 /004 not released)"
    _print(gates)


def cmd_verify_model(a):
    manifest = modelfiles.load_manifest(MANIFEST_PATH)
    report = modelfiles.verify_model_dir(Path(a.model_dir), manifest)
    facts = sourcecheck.analyze_model_sources(Path(a.model_dir), sourcecheck.MODEL_DIR_NAMES)
    _print({"verified_files": len(report["files"]), "report": report, "static_safety_facts": facts})


def _final_lock_or_block():
    lock = load_lock(LOCK_PATH)
    validate_lock(lock)  # raises DEPENDENCY_LOCK_PENDING while the lock is not final
    return lock


def cmd_write_requirements(a):
    from q0harness.locks import requirements_text
    lock = _final_lock_or_block()
    out = Path(a.output)
    with open(out, "x", encoding="utf-8", newline="\n") as f:
        f.write(requirements_text(lock))
    _print({"written": str(out), "sha256": sha256_bytes(out.read_bytes())})


def cmd_verify_wheelhouse(a):
    from q0harness.locks import verify_wheelhouse
    _print(verify_wheelhouse(_final_lock_or_block(), Path(a.wheelhouse)))


def cmd_preflight_cpu(a):
    import importlib.metadata as md
    import importlib.util
    from q0harness.preflight import cpu_preflight
    lock = _final_lock_or_block()
    protocol, digest = load_protocol()
    import pypdfium2  # only in the task venv, after the locked install
    rep = cpu_preflight(protocol=protocol, lock=lock, pdfium=pypdfium2,
                        installed={d.metadata["Name"]: d.version for d in md.distributions()},
                        importable=lambda m: importlib.util.find_spec(m) is not None, dist_version=md.version,
                        model_dir=Path(a.model_dir) if a.model_dir else None, manifest_path=MANIFEST_PATH)
    rep["protocol_sha256"] = digest
    _print(rep)


def _blocked(failure: Q0Failure) -> int:
    _print(make_outcome(BLOCKED, failures=[failure.as_record()]))
    return 2


def cmd_execute(a):
    from q0harness.supervisor import supervise
    protocol, p_sha = load_protocol()
    lock_raw = LOCK_PATH.read_bytes()
    try:
        validate_lock(json.loads(lock_raw))
        if not a.release:
            raise Q0Failure("EXECUTION_NOT_RELEASED", "no --release record supplied")
    except Q0Failure as f:
        return _blocked(f)  # refuse before creating any directory or process
    root = Path(protocol["storage"]["root"])
    paths = layout(root, a.owner)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    run_dir = paths["run_owner"] / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    for sub in ("tmp", "home", "hf-modules", "torch-home", "triton-cache", "inductor-cache", "xdg-cache"):
        (run_dir / sub).mkdir()
    env = build_child_env(dict(os.environ), root=root, owner=a.owner, run_dir=run_dir, gpu_uuid=protocol["gpu"]["uuid"])
    # The child cannot see the operator's TEMP/APPDATA (its env is rebuilt); hand over the forbidden parents.
    with open(run_dir / "parent-context.json", "x", encoding="utf-8") as f:
        json.dump({"forbidden_parents": default_forbidden_parents(REPO_ROOT, dict(os.environ))}, f, indent=2)
    python = paths["venv"] / "Scripts" / "python.exe"
    cmd = [str(python), "-s", "-P", "-X", "utf8", str(HERE / "q0.py"), "child", "--owner", a.owner,
           "--release", str(Path(a.release).resolve()), "--run-dir", str(run_dir)]
    g = protocol["guards"]
    rec = supervise(cmd, env=env, cwd=run_dir, run_dir=run_dir, heartbeat_path=run_dir / "heartbeat.json",
                    session_timeout_s=g["timeouts_s"]["session"], stall_s=g["stall_s"], max_log_bytes=g["max_log_bytes"],
                    default_phase_timeout_s=g["timeouts_s"]["preflight"],
                    observer_cmd=protocol["gpu"].get("observer_cmd"), observer_every_s=protocol["gpu"].get("observer_every_s", 60))
    _print(rec)
    return 0 if rec["verdict"] == "CHILD_COMPLETED" else 3


def cmd_child(a):
    from q0harness.backend_torch import TorchBackend
    from q0harness.session import Session
    protocol, p_sha = load_protocol()
    lock_raw = LOCK_PATH.read_bytes()
    release = json.loads(Path(a.release).read_text(encoding="utf-8"))
    root = Path(protocol["storage"]["root"])
    session = Session(protocol=protocol, protocol_sha256=p_sha, lock=json.loads(lock_raw), lock_sha256=sha256_bytes(lock_raw),
                      release=release, root=root, owner=a.owner, run_dir=Path(a.run_dir), backend=TorchBackend(),
                      repo_root=REPO_ROOT, expected_root=protocol["storage"]["root"],
                      forbidden_parents=json.loads((Path(a.run_dir) / "parent-context.json").read_text(encoding="utf-8"))["forbidden_parents"],
                      manifest_path=MANIFEST_PATH)
    outcome = session.run()
    return 0 if outcome else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="q0.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify-snapshots").set_defaults(fn=cmd_verify_snapshots)
    s = sub.add_parser("build-model-manifest"); s.add_argument("--check", action="store_true"); s.set_defaults(fn=cmd_build_model_manifest)
    s = sub.add_parser("derive-rasters"); s.add_argument("--check", action="store_true"); s.set_defaults(fn=cmd_derive_rasters)
    sub.add_parser("check-protocol").set_defaults(fn=cmd_check_protocol)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    s = sub.add_parser("verify-model"); s.add_argument("model_dir"); s.set_defaults(fn=cmd_verify_model)
    s = sub.add_parser("write-requirements"); s.add_argument("output"); s.set_defaults(fn=cmd_write_requirements)
    s = sub.add_parser("verify-wheelhouse"); s.add_argument("wheelhouse"); s.set_defaults(fn=cmd_verify_wheelhouse)
    s = sub.add_parser("preflight-cpu"); s.add_argument("--model-dir"); s.set_defaults(fn=cmd_preflight_cpu)
    s = sub.add_parser("execute"); s.add_argument("--owner", choices=("author", "reviewer"), required=True)
    s.add_argument("--release"); s.set_defaults(fn=cmd_execute)
    s = sub.add_parser("child"); s.add_argument("--owner", required=True); s.add_argument("--release", required=True)
    s.add_argument("--run-dir", required=True); s.set_defaults(fn=cmd_child)
    a = ap.parse_args(argv)
    try:
        return a.fn(a) or 0
    except Q0Failure as f:
        return _blocked(f)


if __name__ == "__main__":
    sys.exit(main())
