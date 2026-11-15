"""WP-0005 /009 Phase A independent reproduction of COORD-Q0-01 and /003 reconciliation.

Reviewer-owned helper for stable role eld-q0-reviewer, same uninvolved Gemini 4 Carbon
conversation 0815536f-045a-4112-8a89-ebf0e0cc782f. Runs strictly against this reviewer
worktree's unchanged 84cef5ef30685ffee46281fefc5fd1356dbc1876 harness source at continuation
base 4752128b8ceaa65b6d0caa9e44ef7a97d1675dc8 (never touching eld-q0-harness, C:\\Users\\jackg\\eLedgerCare-Q0,
or immutable /003 files). Spawns real separate Python child processes using build_stage_env
and build_child_env to reproduce COORD-Q0-01 and records machine-verified reconciliation of
the three /003 narrative discrepancies.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _find_repo_root(start: Path) -> Path:
    for p in (start, *start.parents):
        if (p / "qualification" / "q0" / "harness" / "q0.py").is_file():
            return p
    raise RuntimeError("Could not locate reviewer worktree root containing qualification/q0/harness/q0.py")


REPO_ROOT = _find_repo_root(HERE)
HARNESS_DIR = REPO_ROOT / "qualification" / "q0" / "harness"
SCRATCH_ROOT = REPO_ROOT / ".scratch"
EXTERNAL_STORAGE_PARENT = Path(r"C:\Users\jackg\eLedgerCare-Q0")

PINS = {
    "original_packet_base": "df9a2b50894f01987d779d7f9ae805794503ce6f",
    "harness_candidate": "84cef5ef30685ffee46281fefc5fd1356dbc1876",
    "harness_candidate_tree": "b7afcd512d508e43b874cf7b9857b7493359a879",
    "author_002_report": "2a52ea58fae2badcb4e9ef47d1cb416c006edca4",
    "opus_checkpoint_1": "b75011da408fed5d2cc4f9025416ead6c5632ceb",
    "opus_checkpoint_2": "ef72849519c83a71e59e80c311b48719252d0cd6",
    "carbon_003_helper": "17107f369a96d0f40d99c83f21ca72d902d3f035",
    "carbon_003_evidence": "f362a0fc748d1206fe24b4c60a0a74d98495524a",
    "carbon_003_report_base": "4752128b8ceaa65b6d0caa9e44ef7a97d1675dc8",
    "coord_diag_helper_commit": "73b5ba98d1e3834cc8c58768ff269730b867ee4c",
    "coord_diag_helper_sha256": "a2125bdc42bfdbf3aa84056f9f0736f438d9d272dfaa085dd2a58b9f036b1c52",
    "coord_diag_obs_commit": "8016f88f2e055e2a4e33335021824367e6230309",
    "coord_correction_kickoff_commit": "350097d06acbafe9323d89a8fb752a46bfccf5d0",
    "protocol_sha256": "dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309",
    "dependency_lock_sha256": "d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e",
    "model_manifest_sha256": "085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8",
    "metadata_lock_blob": "ec8c650ed5fbeb0a754e4daee53aad53753a57a3",
    "cuda_metadata_blob": "bca91aaa8e2d51eabb8e9d7d85c7f3602c4e8b8b",
    "torchvision_receipt_blob": "877d822099e7b3628d36f6b4a709d76ecad6de00",
}

CHILD_PROBE = """import json, os, shutil, sys
from pathlib import Path

harness_dir = Path(sys.argv[1])
repo_root = Path(sys.argv[2])
blob_oid = sys.argv[3]
sys.path.insert(0, str(harness_dir))

from q0harness import locks, release

def call_probe(fn):
    try:
        return {"ok": True, "value": fn()}
    except BaseException as exc:
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "errno": getattr(exc, "errno", None),
            "winerror": getattr(exc, "winerror", None),
            "text": str(exc),
        }

lock_obj = locks.load_lock(harness_dir / "locks" / "dependency-lock.json")
out = {
    "python": sys.executable,
    "cwd": os.getcwd(),
    "path_entries": os.environ.get("PATH", "").split(os.pathsep),
    "git_which": shutil.which("git"),
    "code_identity": call_probe(lambda: release.code_identity(repo_root)),
    "git_blob_reader": call_probe(lambda: len(locks.git_blob_reader(repo_root)(blob_oid))),
    "validate_lock_with_git_reader": call_probe(lambda: len(locks.validate_lock(lock_obj, locks.git_blob_reader(repo_root)))),
}
print(json.dumps(out))
"""


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_bytes(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=str(REPO_ROOT))


def _git(*args: str) -> str:
    return _git_bytes(*args).decode("utf-8")


def _check_output_allowed(out_dir: Path) -> Path:
    resolved = out_dir.resolve()
    for root in (SCRATCH_ROOT.resolve(), HERE.resolve()):
        try:
            if resolved.relative_to(root) != Path("."):
                return resolved
        except ValueError:
            continue
    raise SystemExit(f"Refusing output path outside reviewer .scratch/ or correction-009/: {resolved}")


def _verify_immutability_and_pins() -> dict:
    assert "eld-q0-reviewer-carbon" in str(REPO_ROOT), f"Unexpected worktree: {REPO_ROOT}"
    branch = _git("rev-parse", "--abbrev-ref", "HEAD").strip()
    assert branch == "review/wp-0005-q0-carbon", f"Unexpected branch: {branch}"
    head = _git("rev-parse", "HEAD").strip()
    status_before = [ln for ln in _git("status", "--porcelain=v1", "-uall").splitlines() if ln]

    for key in (
        "original_packet_base",
        "harness_candidate",
        "author_002_report",
        "opus_checkpoint_1",
        "opus_checkpoint_2",
        "carbon_003_helper",
        "carbon_003_evidence",
        "carbon_003_report_base",
        "coord_diag_helper_commit",
        "coord_diag_obs_commit",
        "coord_correction_kickoff_commit",
    ):
        got = _git("rev-parse", f"{PINS[key]}^{{commit}}").strip()
        assert got == PINS[key], f"Pin mismatch for {key}: {got}"

    # Continuation base 4752128b... must be an ancestor of HEAD, and all /003 + harness files must be unchanged.
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", PINS["carbon_003_report_base"], "HEAD"],
        cwd=str(REPO_ROOT),
        check=True,
    )
    immutable_paths = (
        "qualification/q0/harness",
        "docs/agent-reports/eld-q0-reviewer/WP-0005/003_2026-11-15_review_eld-q0-reviewer.md",
        "docs/reviews/WP-0005/eld-q0-reviewer/pre-execution",
    )
    diff_since_003 = [
        ln for ln in _git("diff", "--name-status", PINS["carbon_003_report_base"], "HEAD", "--", *immutable_paths).splitlines() if ln
    ]
    assert diff_since_003 == [], f"Immutable /003 or harness paths changed since 4752128b: {diff_since_003}"

    cand_diff = [
        ln for ln in _git("diff", "--name-status", PINS["harness_candidate"], "HEAD", "--", "qualification/q0/harness").splitlines()
        if ln and not ln.startswith("A\tqualification/q0/harness/evidence/002-final/")
    ]
    assert cand_diff == [], f"Harness source differs from 84cef5ef candidate: {cand_diff}"

    assert _sha256((HARNESS_DIR / "protocol.json").read_bytes()) == PINS["protocol_sha256"]
    assert _sha256((HARNESS_DIR / "locks" / "dependency-lock.json").read_bytes()) == PINS["dependency_lock_sha256"]
    assert _sha256((HARNESS_DIR / "manifests" / "model-files.json").read_bytes()) == PINS["model_manifest_sha256"]

    report_003_sha256 = _sha256(
        (REPO_ROOT / "docs" / "agent-reports" / "eld-q0-reviewer" / "WP-0005" / "003_2026-11-15_review_eld-q0-reviewer.md").read_bytes()
    )

    # Verify coordinator diagnostic helper and observation in shared Git object store without running that script or touching eld-q0-harness.
    coord_helper_bytes = _git_bytes(
        "cat-file", "blob", f"{PINS['coord_diag_helper_commit']}:docs/coordination/WP-0005/diagnostics/worker-git-check.py"
    )
    assert _sha256(coord_helper_bytes) == PINS["coord_diag_helper_sha256"]
    coord_obs_bytes = _git_bytes(
        "cat-file", "blob", f"{PINS['coord_diag_obs_commit']}:docs/coordination/WP-0005/diagnostics/worker-git-observation.json"
    )
    coord_obs = json.loads(coord_obs_bytes.decode("utf-8"))

    return {
        "branch": branch,
        "head_at_check": head,
        "status_before": status_before,
        "continuation_base_verified": PINS["carbon_003_report_base"],
        "immutable_003_and_harness_unchanged": True,
        "report_003_sha256_preserved": report_003_sha256,
        "coordinator_diagnostic_verified_from_git_blob": {
            "helper_commit": PINS["coord_diag_helper_commit"],
            "helper_sha256": _sha256(coord_helper_bytes),
            "observation_commit": PINS["coord_diag_obs_commit"],
            "observation_sha256": _sha256(coord_obs_bytes),
            "recorded_harness_revision": coord_obs["harness_revision"],
        },
    }


def _reproduce_coord_q0_01(out_dir: Path) -> dict:
    sys.path.insert(0, str(HARNESS_DIR))
    from q0harness import environment, locks, protocol as proto_mod, release  # noqa: E402

    protocol, _ = proto_mod.load_protocol()
    root = Path(protocol["storage"]["root"])
    parent_env = dict(os.environ)

    # Control: parent Python process (inherits operator PATH with Git).
    lock_obj = locks.load_lock(HARNESS_DIR / "locks" / "dependency-lock.json")
    parent_control = {
        "git_which": shutil.which("git"),
        "code_identity": release.code_identity(REPO_ROOT),
        "git_blob_reader_bytes": len(locks.git_blob_reader(REPO_ROOT)(PINS["metadata_lock_blob"])),
        "validate_lock_artifact_count": len(locks.validate_lock(lock_obj, locks.git_blob_reader(REPO_ROOT))),
    }
    assert parent_control["git_which"] is not None
    assert parent_control["code_identity"]["head"] is not None
    assert parent_control["git_blob_reader_bytes"] == 123592
    assert parent_control["validate_lock_artifact_count"] == 32

    envs = {
        "install_stage_offline": environment.build_stage_env(parent_env, root=root, protocol=protocol, network=False),
        "acquire_stage_network": environment.build_stage_env(parent_env, root=root, protocol=protocol, network=True),
        "runtime_child": environment.build_child_env(
            parent_env,
            root=root,
            owner="reviewer",
            run_dir=root / "runs" / "reviewer" / "phase-a-readonly-probe",
            gpu_uuid=protocol["gpu"]["uuid"],
        ),
    }

    child_api_probes = {}
    for env_name, env_dict in envs.items():
        cp = subprocess.run(
            [sys.executable, "-I", "-B", "-c", CHILD_PROBE, str(HARNESS_DIR), str(REPO_ROOT), PINS["metadata_lock_blob"]],
            env=env_dict,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        parsed = json.loads(cp.stdout)
        # Confirm COORD-Q0-01 reproduction in every sanitized child environment:
        assert parsed["git_which"] is None, f"Expected git_which=None in {env_name}, got {parsed['git_which']}"
        for op in ("code_identity", "git_blob_reader", "validate_lock_with_git_reader"):
            assert parsed[op]["ok"] is False and parsed[op]["error_type"] == "FileNotFoundError", (
                f"Expected FileNotFoundError for {op} in {env_name}, got {parsed[op]}"
            )
            assert parsed[op]["winerror"] == 2
        child_api_probes[env_name] = parsed

    # Also invoke unmodified q0.py CLI commands as real child processes under install_stage_offline and runtime_child.
    py = sys.executable
    py_rel = Path(py).name
    q0 = "qualification/q0/harness/q0.py"
    never_file = SCRATCH_ROOT / "phase-a-never-written.txt"
    if never_file.exists():
        never_file.unlink()

    cli_specs = [
        ("01-stage-offline-q0-status", "install_stage_offline", [py, "-I", "-B", q0, "status"]),
        ("02-stage-offline-q0-lock-check", "install_stage_offline", [py, "-I", "-B", q0, "lock-check"]),
        ("03-stage-offline-q0-write-requirements", "install_stage_offline", [py, "-I", "-B", q0, "write-requirements", ".scratch/phase-a-never-written.txt"]),
        ("04-runtime-child-q0-status", "runtime_child", [py, "-I", "-B", q0, "status"]),
        ("05-runtime-child-q0-lock-check", "runtime_child", [py, "-I", "-B", q0, "lock-check"]),
    ]

    cli_failures = []
    for name, env_key, argv in cli_specs:
        t0 = time.perf_counter()
        started = _utc_now()
        cp = subprocess.run(argv, cwd=str(REPO_ROOT), env=envs[env_key], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        elapsed = round(time.perf_counter() - t0, 3)
        out_name = f"{name}.txt"
        (out_dir / out_name).write_bytes(cp.stdout)
        text = cp.stdout.decode("utf-8", errors="replace")
        assert cp.returncode == 1 and "FileNotFoundError: [WinError 2]" in text, (
            f"Expected exit 1 FileNotFoundError for {name}, got rc={cp.returncode}: {text[:300]}"
        )
        cli_failures.append({
            "name": name,
            "environment": env_key,
            "argv": [py_rel, *argv[1:]],
            "exit_code": cp.returncode,
            "started_utc": started,
            "seconds": elapsed,
            "output": out_name,
            "output_sha256": _sha256(cp.stdout),
            "output_bytes": len(cp.stdout),
            "observed_exception": "FileNotFoundError: [WinError 2] The system cannot find the file specified",
        })

    assert not never_file.exists(), ".scratch/phase-a-never-written.txt was unexpectedly created"
    return {
        "defect_id": "COORD-Q0-01",
        "classification": "harness_subprocess_environment_defect (NOT a model failure or OCR accuracy result)",
        "changes_earlier_003_readiness_conclusion": True,
        "updated_disposition_on_84cef5ef": "CHANGES_REQUESTED (awaiting /008 harness correction and /009 Phase B verification before any install/runtime release)",
        "why_003_missed_it": (
            "In /003 (17107f36), run_carbon_review_checks.py inspected build_child_env/build_stage_env dict keys in-process "
            "while running q0.py status and lock-check in the parent operator environment (where Git was on PATH), and "
            "author unit tests injected in-memory lock readers / precomputed code_identity dicts rather than spawning real "
            "child Python processes under build_stage_env or build_child_env."
        ),
        "parent_process_control": parent_control,
        "sanitized_child_api_probes": child_api_probes,
        "sanitized_child_q0_cli_failures": cli_failures,
    }


def _reconcile_003_discrepancies() -> dict:
    sys.path.insert(0, str(HARNESS_DIR))
    from q0harness import protocol as proto_mod  # noqa: E402

    protocol, proto_sha = proto_mod.load_protocol()
    assert proto_sha == PINS["protocol_sha256"]
    fx_by_family = {f["family_id"]: f for f in protocol["fixtures"]}
    f01 = fx_by_family["F01"]
    f07 = fx_by_family["F07"]

    assert f01["fixture_id"] == "SYN-WO-01-v0-clean" and f01["page_count"] == 1
    assert f07["fixture_id"] == "SYN-MP-01-v0-clean" and f07["page_count"] == 3 and len(f07["raster"]) == 3
    assert f07["max_new_tokens"] == 24000 == 8000 * 3
    assert protocol["guards"]["timeouts_s"]["call_pages_3"] == 3600

    assert f01["ngram_window"] == 128 == proto_mod.ngram_window_for(1)
    assert f07["ngram_window"] == 1024 == proto_mod.ngram_window_for(3)
    assert protocol["call"]["rules"]["ngram_window"] == "1024 if page_count > 1 else 128 (upstream README evaluation setup), no whitelist"

    cuda_meta = json.loads((REPO_ROOT / "qualification" / "q0" / "preflight" / "response" / "cuda-metadata.json").read_text(encoding="utf-8"))
    tv_meta = next(r for r in cuda_meta if r["name"] == "torchvision")
    receipt = json.loads(
        (
            REPO_ROOT
            / "docs"
            / "reviews"
            / "WP-0005"
            / "eld-q0-reviewer"
            / "pre-execution"
            / "response-2026-11-15"
            / "torchvision-acquisition-receipt.json"
        ).read_text(encoding="utf-8")
    )
    sig_keys = [k for k in (*tv_meta.keys(), *receipt.keys()) if "sig" in k.lower() or "pgp" in k.lower() or "gpg" in k.lower()]
    assert sig_keys == []

    return {
        "immutable_003_preserved": True,
        "protocol_unchanged_sha256": proto_sha,
        "reconciliations": [
            {
                "id": "R-003-01",
                "topic": "F07 (SYN-MP-01-v0-clean) page count",
                "erroneous_003_wording": "6 pages / 6-page F07 (003 report L62, L88)",
                "actual_verified_fact": {
                    "fixture_id": f07["fixture_id"],
                    "family_id": "F07",
                    "page_count": f07["page_count"],
                    "raster_page_entries": len(f07["raster"]),
                    "max_new_tokens": f07["max_new_tokens"],
                    "timeout_guard_key": "call_pages_3 (3600s)",
                },
            },
            {
                "id": "R-003-02",
                "topic": "Protocol ngram_window rule and per-fixture values",
                "erroneous_003_wording": "ngram_window=max(2048,512*N) (003 report L62)",
                "actual_verified_fact": {
                    "rule": protocol["call"]["rules"]["ngram_window"],
                    "F01_1_page_ngram_window": f01["ngram_window"],
                    "F07_3_page_ngram_window": f07["ngram_window"],
                },
            },
            {
                "id": "R-003-03",
                "topic": "PEP 658 METADATA digest provenance vs cryptographic signature",
                "erroneous_003_wording": "publisher-signed PEP 658 METADATA SHA-256 f8e91ee9... (003 report L86)",
                "actual_verified_fact": {
                    "metadata_published_sha256": tv_meta["metadata_published_sha256"],
                    "wheel_local_sha256_tofu": receipt["local_sha256"],
                    "cryptographic_signature_present_or_verified": False,
                    "actual_provenance": (
                        "Published PEP 658 data-dist-info-metadata SHA-256 attribute retrieved over HTTPS/TLS from the "
                        "official PyTorch cu130 index, matching the wheel's torchvision-0.28.0+cu130.dist-info/METADATA "
                        "bytes; no PGP/Sigstore/cryptographic publisher signature was published or verified, and wheel "
                        "body hash 5ae0ff50... remains trust-on-first-use (local-sha256-TOFU) over TLS."
                    ),
                    "receipt_recorded_limits": receipt["limits"],
                },
            },
        ],
    }


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: reproduce_coord_q0_01_phase_a.py <output_dir>")
    out_dir = _check_output_allowed(Path(sys.argv[1]))
    if out_dir.exists():
        raise SystemExit(f"Output directory already exists: {out_dir}")
    out_dir.mkdir(parents=True)

    started_utc = _utc_now()
    ext_before = EXTERNAL_STORAGE_PARENT.exists()

    immutability = _verify_immutability_and_pins()
    repro = _reproduce_coord_q0_01(out_dir)
    reconciliation = _reconcile_003_discrepancies()

    reconciliation_bytes = (json.dumps(reconciliation, indent=2) + "\n").encode("utf-8")
    (out_dir / "reconciliation-003.json").write_bytes(reconciliation_bytes)

    ext_after = EXTERNAL_STORAGE_PARENT.exists()
    head_after = _git("rev-parse", "HEAD").strip()
    status_after = [ln for ln in _git("status", "--porcelain=v1", "-uall").splitlines() if ln]

    assert not ext_before and not ext_after, "External runtime root C:\\Users\\jackg\\eLedgerCare-Q0 unexpectedly exists"
    assert status_after == immutability["status_before"], f"Git status changed during Phase A check: {status_after}"

    summary = {
        "schema": "eldq0-carbon-correction-009-phase-a/1",
        "packet": "WP-0005",
        "reserved_sequence": "009",
        "phase": "Phase A (original-source COORD-Q0-01 reproduction and /003 factual reconciliation; final /009 held for /008 pins)",
        "role": "eld-q0-reviewer",
        "reviewer_model": "Gemini 4 Carbon (High)",
        "reviewer_session_id": "0815536f-045a-4112-8a89-ebf0e0cc782f",
        "predecessor_opus_session_id": "e6147c9e-0303-475f-99ff-93ee38a681e4",
        "started_utc": started_utc,
        "finished_utc": _utc_now(),
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "worktree": str(REPO_ROOT),
        "external_storage_parent_exists_before": ext_before,
        "external_storage_parent_exists_after": ext_after,
        "immutability_and_pins": immutability,
        "coord_q0_01_reproduction": repro,
        "reconciliation_003_file": "reconciliation-003.json",
        "reconciliation_003_sha256": _sha256(reconciliation_bytes),
        "reconciliation_003_bytes": len(reconciliation_bytes),
        "head_after": head_after,
        "status_after": status_after,
    }
    summary_bytes = (json.dumps(summary, indent=2) + "\n").encode("utf-8")
    (out_dir / "summary.json").write_bytes(summary_bytes)
    print(json.dumps({
        "phase": "A",
        "coord_q0_01_reproduced": True,
        "changes_earlier_003_readiness": True,
        "reconciled_003_items": len(reconciliation["reconciliations"]),
        "head": head_after,
        "summary_sha256": _sha256(summary_bytes),
        "reconciliation_003_sha256": _sha256(reconciliation_bytes),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
