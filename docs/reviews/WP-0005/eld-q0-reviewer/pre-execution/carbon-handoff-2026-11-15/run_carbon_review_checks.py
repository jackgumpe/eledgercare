"""Independent pre-execution CPU check runner for WP-0005 /003 (Carbon handoff).

Reviewer-owned helper for stable role eld-q0-reviewer (new uninvolved Gemini 4 Carbon
session 0815536f-045a-4112-8a89-ebf0e0cc782f). Never writes under qualification/** or
any immutable predecessor/author path; outputs are restricted to this directory's owned
subpaths or the worktree's .scratch/ directory. Stdlib CPU + read-only Git/host checks only.
"""

from __future__ import annotations

import copy
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
    raise RuntimeError("Could not locate repository worktree root containing qualification/q0/harness/q0.py")


REPO_ROOT = _find_repo_root(HERE)
HARNESS_DIR = REPO_ROOT / "qualification" / "q0" / "harness"
SCRATCH_ROOT = REPO_ROOT / ".scratch"
EXTERNAL_STORAGE_PARENT = Path(r"C:\Users\jackg\eLedgerCare-Q0")
OPUS_SCRATCH_REL = Path(".scratch") / "torchvision-provenance"

EXPECTED_PINS = {
    "original_packet_base": "df9a2b50894f01987d779d7f9ae805794503ce6f",
    "astra_001_deliverable": "b8112ca27b8f7d5bcba7171ab0f1bd5907fae1f6",
    "astra_001_report": "2c32dde602b274251043bb216752f5d7fe9593be",
    "astra_007_deliverable": "d666c4163b8b6bdf5f6c69b455c30f3c377cbdc5",
    "astra_007_evidence": "6cb6a258b9652b7becd3fca9c7cf2f04866c3ec3",
    "astra_007_report": "951d408aabf7bdad3602c0e7698869e2e2457aed",
    "opus_checkpoint_1": "b75011da408fed5d2cc4f9025416ead6c5632ceb",
    "opus_checkpoint_2": "ef72849519c83a71e59e80c311b48719252d0cd6",
    "harness_candidate_parent": "912f4f4f991977cca83bb40928cff45ac525efaa",
    "harness_candidate": "84cef5ef30685ffee46281fefc5fd1356dbc1876",
    "harness_candidate_tree": "b7afcd512d508e43b874cf7b9857b7493359a879",
    "author_final_evidence": "0331efd71ef17e5485adac5a53d864c6d96e8f4a",
    "author_002_report": "2a52ea58fae2badcb4e9ef47d1cb416c006edca4",
    "carbon_handoff_base": "2e41d3a91b8f08b53d643b20a1fb038b5aec1500",
    "protocol_sha256": "dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309",
    "dependency_lock_sha256": "d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e",
    "model_manifest_sha256": "085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8",
    "metadata_lock_blob": "ec8c650ed5fbeb0a754e4daee53aad53753a57a3",
    "cuda_metadata_blob": "bca91aaa8e2d51eabb8e9d7d85c7f3602c4e8b8b",
    "torchvision_receipt_blob": "877d822099e7b3628d36f6b4a709d76ecad6de00",
}


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_blob_sha1(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode("ascii"))
    h.update(data)
    return h.hexdigest()


def _git(*args: str) -> str:
    cp = subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return cp.stdout


def _check_output_allowed(out_dir: Path) -> Path:
    resolved = out_dir.resolve()
    allowed_roots = (SCRATCH_ROOT.resolve(), HERE.resolve())
    for root in allowed_roots:
        try:
            rel = resolved.relative_to(root)
            if rel != Path("."):
                return resolved
        except ValueError:
            continue
    raise SystemExit(f"Refusing output path outside reviewer .scratch/ or owned review subdir: {resolved}")


def _verify_git_and_author_evidence() -> dict:
    branch = _git("rev-parse", "--abbrev-ref", "HEAD").strip()
    head = _git("rev-parse", "HEAD").strip()
    status_before = [ln for ln in _git("status", "--porcelain=v1", "-uall").splitlines() if ln]

    resolved_commits = {}
    for key in (
        "original_packet_base",
        "astra_001_deliverable",
        "astra_001_report",
        "astra_007_deliverable",
        "astra_007_evidence",
        "astra_007_report",
        "opus_checkpoint_1",
        "opus_checkpoint_2",
        "harness_candidate_parent",
        "harness_candidate",
        "author_final_evidence",
        "author_002_report",
        "carbon_handoff_base",
    ):
        oid = _git("rev-parse", f"{EXPECTED_PINS[key]}^{{commit}}").strip()
        assert oid == EXPECTED_PINS[key], f"commit mismatch for {key}: {oid}"
        resolved_commits[key] = oid

    cand_tree = _git("rev-parse", f"{EXPECTED_PINS['harness_candidate']}:qualification/q0/harness").strip()
    assert cand_tree == EXPECTED_PINS["harness_candidate_tree"], f"unexpected candidate harness tree {cand_tree}"

    handoff_parents = _git("rev-list", "--parents", "-n", "1", EXPECTED_PINS["carbon_handoff_base"]).strip().split()[1:]
    assert handoff_parents == [EXPECTED_PINS["opus_checkpoint_2"], EXPECTED_PINS["author_002_report"]], (
        f"unexpected handoff merge parents: {handoff_parents}"
    )

    cand_to_head_harness = [
        ln for ln in _git("diff", "--name-status", EXPECTED_PINS["harness_candidate"], "HEAD", "--", "qualification/q0/harness").splitlines() if ln
    ]
    non_evidence_harness_diffs = [
        ln for ln in cand_to_head_harness if not ln.startswith("A\tqualification/q0/harness/evidence/002-final/")
    ]
    assert non_evidence_harness_diffs == [], f"harness source modified after candidate: {non_evidence_harness_diffs}"

    base_to_evid = [
        ln for ln in _git("diff", "--name-status", EXPECTED_PINS["original_packet_base"], EXPECTED_PINS["author_final_evidence"], "--", "qualification/q0/harness").splitlines() if ln
    ]
    cand_to_evid = [
        ln for ln in _git("diff", "--name-status", EXPECTED_PINS["harness_candidate"], EXPECTED_PINS["author_final_evidence"], "--", "qualification/q0/harness").splitlines() if ln
    ]
    evid_to_rep = [
        ln for ln in _git("diff", "--name-status", EXPECTED_PINS["author_final_evidence"], EXPECTED_PINS["author_002_report"]).splitlines() if ln
    ]

    proto_bytes = (HARNESS_DIR / "protocol.json").read_bytes()
    lock_bytes = (HARNESS_DIR / "locks" / "dependency-lock.json").read_bytes()
    manifest_bytes = (HARNESS_DIR / "manifests" / "model-files.json").read_bytes()
    meta_lock_bytes = (REPO_ROOT / "qualification" / "q0" / "preflight" / "response" / "metadata-lock.json").read_bytes()
    cuda_meta_bytes = (REPO_ROOT / "qualification" / "q0" / "preflight" / "response" / "cuda-metadata.json").read_bytes()
    receipt_bytes = (
        REPO_ROOT
        / "docs"
        / "reviews"
        / "WP-0005"
        / "eld-q0-reviewer"
        / "pre-execution"
        / "response-2026-11-15"
        / "torchvision-acquisition-receipt.json"
    ).read_bytes()

    assert _sha256(proto_bytes) == EXPECTED_PINS["protocol_sha256"]
    assert _sha256(lock_bytes) == EXPECTED_PINS["dependency_lock_sha256"]
    assert _sha256(manifest_bytes) == EXPECTED_PINS["model_manifest_sha256"]
    assert _git_blob_sha1(meta_lock_bytes) == EXPECTED_PINS["metadata_lock_blob"] and len(meta_lock_bytes) == 123592
    assert _git_blob_sha1(cuda_meta_bytes) == EXPECTED_PINS["cuda_metadata_blob"] and len(cuda_meta_bytes) == 57150
    assert _git_blob_sha1(receipt_bytes) == EXPECTED_PINS["torchvision_receipt_blob"] and len(receipt_bytes) == 3103

    # Verify all 11 raw author evidence files match summary.json byte-for-byte.
    evid_dir = HARNESS_DIR / "evidence" / "002-final" / "84cef5ef"
    author_summary = json.loads((evid_dir / "summary.json").read_text(encoding="utf-8"))
    verified_author_outputs = []
    for cmd in author_summary["commands"]:
        raw = (evid_dir / cmd["output"]).read_bytes()
        got_sha = _sha256(raw)
        assert got_sha == cmd["output_sha256"] and len(raw) == cmd["output_bytes"], f"author output mismatch: {cmd['output']}"
        verified_author_outputs.append({"name": cmd["name"], "output": cmd["output"], "bytes": len(raw), "sha256": got_sha, "exit_code": cmd["exit_code"]})

    unittest_tail = [
        ln.strip()
        for ln in (evid_dir / "01-unittest.txt").read_text(encoding="utf-8", errors="replace").splitlines()
        if ln.startswith("Ran ") or ln.startswith("OK ")
    ]

    return {
        "branch": branch,
        "head_at_check": head,
        "status_before": status_before,
        "resolved_commits": resolved_commits,
        "candidate_harness_tree": cand_tree,
        "handoff_merge_parents": handoff_parents,
        "harness_source_unchanged_from_candidate": True,
        "diff_counts_reconciliation": {
            "base_to_author_final_evidence_harness_files": len(base_to_evid),
            "base_to_candidate_harness_files": len(base_to_evid) - len(cand_to_evid),
            "candidate_to_author_final_evidence_files": len(cand_to_evid),
            "author_final_evidence_to_002_report_files": len(evid_to_rep),
            "note_002_report_errata": (
                "/002 report L91 states 14 evidence-only additions for 84cef5ef -> 0331efd7; "
                f"actual git diff count is {len(cand_to_evid)} (11 command outputs + summary.json + .gitattributes + README.md + run_checks.py). "
                f"/002 report L40/L162 phrase '75 tests OK, 1 skipped'; unittest summary lines are {unittest_tail!r} (74 passed + 1 skipped = 75 total)."
            ),
        },
        "verified_author_002_final_outputs_count": len(verified_author_outputs),
        "verified_author_002_final_outputs_all_match_summary": True,
    }


def _run_independent_assertions() -> dict:
    sys.path.insert(0, str(HARNESS_DIR))
    from q0harness import environment, hashing, locks, modelfiles, outcome, protocol, sourcecheck  # noqa: E402

    tmp_dir = SCRATCH_ROOT / "carbon-assert-tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        # 1. Assemble all 10 retained model .py files and verify digests + AST safety across all 10.
        model10_dir = tmp_dir / "Unlimited_OCR_2_04809669"
        model10_dir.mkdir()
        manifest = modelfiles.load_manifest(HARNESS_DIR / "manifests" / "model-files.json")
        manifest_by_path = {f["path"]: f for f in manifest["files"]}

        astra_src = REPO_ROOT / "research" / "astra" / "sources"
        preflight_src = REPO_ROOT / "qualification" / "q0" / "preflight" / "response" / "sources"
        source_origins = {
            "_sparse_base_impl.py": astra_src / "hf-_sparse_base_impl.py.txt",
            "dash_attention.py": astra_src / "hf-dash_attention.py.txt",
            "deepencoder.py": astra_src / "hf-deepencoder.py.txt",
            "modeling_deepseekv2.py": astra_src / "hf-modeling_deepseekv2.py.txt",
            "modeling_unlimitedocr.py": astra_src / "hf-modeling_unlimitedocr.py.txt",
            "sparse_gather_e2e_triton.py": astra_src / "hf-sparse_gather_e2e_triton.py.txt",
            "sparse_gather_triton.py": astra_src / "hf-sparse_gather_triton.py.txt",
            "configuration_deepseek_v2.py": preflight_src / "configuration_deepseek_v2.py",
            "conversation.py": preflight_src / "conversation.py",
            "packing_patch.py": preflight_src / "packing_patch.py",
        }
        assert set(source_origins) == set(sourcecheck.MODEL_DIR_NAMES.values())
        verified_py_blobs = {}
        for py_name, src_path in sorted(source_origins.items()):
            raw = src_path.read_bytes()
            blob_oid = hashing.git_blob_sha1_bytes(raw)
            mf_entry = manifest_by_path[py_name]
            assert mf_entry["digest_kind"] == "git_blob_sha1"
            assert blob_oid == mf_entry["git_blob_sha1"] and len(raw) == mf_entry["size"], f"mismatch on {py_name}"
            (model10_dir / py_name).write_bytes(raw)
            verified_py_blobs[py_name] = {"git_blob_sha1": blob_oid, "size": len(raw)}

        ast_facts_10 = sourcecheck.analyze_model_sources(model10_dir, sourcecheck.MODEL_DIR_NAMES)
        assert ast_facts_10["eval_exec_compile_sites_all_modules"] == [{
            "builtin": "eval",
            "file": "modeling_unlimitedocr.py",
            "line": 120,
        }]
        assert ast_facts_10["entry"]["save_guard_lines"] == [1103]
        assert ast_facts_10["entry"]["decode_disables_ring_window"] is True
        assert ast_facts_10["entry"]["uses_dynamic_cache"] is True

        # 2. Verify model-card notice separation and model directory identifier rules (Q0R-06, Q0R-09).
        notice_bytes = (preflight_src / "model-card.md").read_bytes()
        notice_entry = manifest["notices"][0]
        assert notice_entry["path"] == "README.md"
        assert hashing.git_blob_sha1_bytes(notice_bytes) == notice_entry["git_blob_sha1"] == "c79e1e3362c8fd2f9193d79c1db80fbf7f041c45"
        assert len(notice_bytes) == notice_entry["size"] == 14107
        assert "README.md" not in manifest_by_path

        norm_ok = modelfiles.normalize_model_dir(model10_dir, model10_dir)
        assert norm_ok == model10_dir.resolve() and norm_ok.name.isidentifier()
        trailing_rejected = False
        try:
            modelfiles.normalize_model_dir(str(model10_dir) + "\\", model10_dir)
        except outcome.Q0Failure as exc:
            trailing_rejected = exc.failure_class == "UNSUPPORTED_PLATFORM"
        assert trailing_rejected

        bad_ident_dir = tmp_dir / "Unlimited-OCR-2.bad"
        bad_ident_dir.mkdir()
        bad_ident_rejected = False
        try:
            modelfiles.normalize_model_dir(bad_ident_dir, bad_ident_dir)
        except outcome.Q0Failure as exc:
            bad_ident_rejected = exc.failure_class == "UNSUPPORTED_PLATFORM"
        assert bad_ident_rejected

        # 3. Non-circular lock, cookie hygiene, and receipt mutation rejection (N-01, N-03, Q0R-08).
        lock_raw_text = (HARNESS_DIR / "locks" / "dependency-lock.json").read_text(encoding="utf-8")
        assert "003_2026-11-15_review_eld-q0-reviewer" not in lock_raw_text
        assert "accepted_review" not in lock_raw_text
        assert "__cf_bm" not in lock_raw_text and "set-cookie" not in lock_raw_text.lower()

        lock_obj = locks.load_lock(HARNESS_DIR / "locks" / "dependency-lock.json")
        reader = locks.git_blob_reader(REPO_ROOT)
        pkgs = locks.validate_lock(lock_obj, reader)
        assert len(pkgs) == 32
        assert locks.readiness(pkgs) == {
            "installable": True,
            "missing_wheel_sha256": [],
            "required_exceptions": ["torchvision-local-sha256-TOFU"],
            "counts": {"publisher-declared": 31, "local-sha256-TOFU": 1, "missing": 0},
        }

        circular_lock = copy.deepcopy(lock_obj)
        circular_lock["accepted_review"] = "docs/agent-reports/eld-q0-reviewer/WP-0005/003_2026-11-15_review_eld-q0-reviewer.md"
        circular_rejected = False
        try:
            locks.validate_lock(circular_lock, reader)
        except outcome.Q0Failure as exc:
            circular_rejected = exc.failure_class == "DEPENDENCY_LOCK_PENDING"
        assert circular_rejected

        unaccepted_release_rejected = False
        try:
            locks.require_installable(pkgs, {"accepted_provenance_exceptions": []})
        except outcome.Q0Failure as exc:
            unaccepted_release_rejected = exc.failure_class == "ACQUISITION_PROVENANCE_PENDING"
        assert unaccepted_release_rejected

        # 4. Holdout and expected-value path refusal without reading forbidden files.
        forbidden_probes = (
            "evaluation/synthetic/expected/F01/SYN-WO-01.json",
            "evaluation/synthetic/sources/F01/SYN-WO-01.tex",
            "evaluation/synthetic/pdfs/F03/SYN-F03-v0-clean.pdf",
            "evaluation/synthetic/pdfs/F05/SYN-F05-v0-clean.pdf",
            "evaluation/synthetic/pdfs/F06/SYN-F06-v0-clean.pdf",
            "evaluation/synthetic/pdfs/F08/SYN-F08-v0-clean.pdf",
        )
        refused_probes = {}
        for probe in forbidden_probes:
            try:
                protocol.check_repo_path_allowed(probe)
                raise AssertionError(f"failed to refuse {probe}")
            except outcome.Q0Failure as exc:
                assert exc.failure_class == "HOLDOUT_ACCESS_REFUSED"
                refused_probes[probe] = exc.failure_class

        # 5. Child and stage environment allowlist & offline isolation (Q0R-05, Q0R-06).
        proto_obj, _ = protocol.load_protocol()
        fake_root = Path(proto_obj["storage"]["root"])
        fake_run = fake_root / "runs" / "reviewer" / "run-check"
        dirty_parent = {
            "SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
            "HF_TOKEN": "secret-token",
            "OPENAI_API_KEY": "secret-key",
            "TIME_DIAG": "1",
            "DASH_FORCE_EAGER": "1",
            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
            "PYTHONPATH": r"C:\bad",
        }
        child_env = environment.build_child_env(
            dirty_parent,
            root=fake_root,
            owner="reviewer",
            run_dir=fake_run,
            gpu_uuid=proto_obj["gpu"]["uuid"],
        )
        stage_offline_env = environment.build_stage_env(dirty_parent, root=fake_root, protocol=proto_obj, network=False)
        for leaked in ("HF_TOKEN", "OPENAI_API_KEY", "TIME_DIAG", "DASH_FORCE_EAGER", "PYTORCH_CUDA_ALLOC_CONF", "PYTHONPATH"):
            assert leaked not in child_env and leaked not in stage_offline_env
        assert child_env["HF_HUB_OFFLINE"] == "1" and child_env["TRANSFORMERS_OFFLINE"] == "1"
        assert stage_offline_env["PIP_NO_INDEX"] == "1" and stage_offline_env["HF_HUB_OFFLINE"] == "1"

        return {
            "all_10_model_py_verified": True,
            "verified_model_py_count": len(verified_py_blobs),
            "verified_model_py_blobs": verified_py_blobs,
            "ast_eval_exec_compile_sites": ast_facts_10["eval_exec_compile_sites_all_modules"],
            "entry_static_facts": ast_facts_10["entry"],
            "notice_readme_separated_and_verified": True,
            "model_dir_identifier_and_trailing_sep_enforced": True,
            "lock_non_circular_and_cookie_free": True,
            "tofu_exception_gate_enforced": True,
            "holdout_and_expected_paths_refused": refused_probes,
            "child_and_stage_env_allowlist_verified": True,
        }
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: run_carbon_review_checks.py <output_dir>")
    out_dir = _check_output_allowed(Path(sys.argv[1]))
    if out_dir.exists():
        raise SystemExit(f"Output directory already exists: {out_dir}")
    out_dir.mkdir(parents=True)

    started_utc = _utc_now()
    ext_before = EXTERNAL_STORAGE_PARENT.exists()
    opus_scratch_present = (REPO_ROOT / OPUS_SCRATCH_REL).exists()
    never_written = SCRATCH_ROOT / "carbon-never-written.txt"
    if never_written.exists():
        never_written.unlink()

    git_and_author = _verify_git_and_author_evidence()

    py = sys.executable
    py_rel = Path(py).name
    q0 = "qualification/q0/harness/q0.py"
    specs = [
        ("01-unittest", [py, "-I", "-B", "-m", "unittest", "discover", "-s", "qualification/q0/harness/tests", "-t", "qualification/q0/harness/tests", "-v"], 0),
        ("02-verify-snapshots", [py, "-I", "-B", q0, "verify-snapshots"], 0),
        ("03-derive-rasters-check", [py, "-I", "-B", q0, "derive-rasters", "--check"], 0),
        ("04-model-manifest-check", [py, "-I", "-B", q0, "build-model-manifest", "--check"], 0),
        ("05-check-protocol", [py, "-I", "-B", q0, "check-protocol"], 0),
        ("06-lock-check", [py, "-I", "-B", q0, "lock-check"], 0),
        ("07-status", [py, "-I", "-B", q0, "status"], 0),
        ("08-host-precheck-initial", [py, "-I", "-B", q0, "host-precheck", "--stage", "initial"], 0),
        ("09-execute-author-refused", [py, "-I", "-B", q0, "execute", "--owner", "author"], 2),
        ("10-execute-reviewer-refused", [py, "-I", "-B", q0, "execute", "--owner", "reviewer"], 2),
        ("11-write-requirements-refused", [py, "-I", "-B", q0, "write-requirements", ".scratch/carbon-never-written.txt"], 2),
        ("12-verify-wheelhouse-refused", [py, "-I", "-B", q0, "verify-wheelhouse", ".scratch"], 2),
    ]

    commands = []
    for name, argv, expected_rc in specs:
        t0 = time.perf_counter()
        c_start = _utc_now()
        cp = subprocess.run(argv, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        elapsed = round(time.perf_counter() - t0, 3)
        out_name = f"{name}.txt"
        out_path = out_dir / out_name
        out_path.write_bytes(cp.stdout)
        rec = {
            "name": name,
            "argv": [py_rel, *argv[1:]],
            "expected_exit_code": expected_rc,
            "exit_code": cp.returncode,
            "matched_expected": cp.returncode == expected_rc,
            "started_utc": c_start,
            "seconds": elapsed,
            "output": out_name,
            "output_sha256": _sha256(cp.stdout),
            "output_bytes": len(cp.stdout),
        }
        commands.append(rec)
        if cp.returncode != expected_rc:
            raise RuntimeError(f"Command {name} returned {cp.returncode}, expected {expected_rc}")

    assertions = _run_independent_assertions()
    assertions_bytes = (json.dumps(assertions, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (out_dir / "independent-assertions.json").write_bytes(assertions_bytes)

    never_written_after = never_written.exists()
    ext_after = EXTERNAL_STORAGE_PARENT.exists()
    head_after = _git("rev-parse", "HEAD").strip()
    status_after = [ln for ln in _git("status", "--porcelain=v1", "-uall").splitlines() if ln]
    scratch_leftovers = sorted(
        p.name for p in SCRATCH_ROOT.iterdir() if p.resolve() != out_dir.resolve()
    ) if SCRATCH_ROOT.exists() else []

    assert not ext_before and not ext_after, "External storage root C:\\Users\\jackg\\eLedgerCare-Q0 unexpectedly exists"
    assert not never_written_after, ".scratch/carbon-never-written.txt was unexpectedly created"
    assert status_after == git_and_author["status_before"], f"Git status changed during check run: {status_after}"

    summary = {
        "schema": "eldq0-carbon-review-checks/1",
        "role": "eld-q0-reviewer",
        "reviewer_model": "Gemini 4 Carbon (High)",
        "reviewer_session_id": "0815536f-045a-4112-8a89-ebf0e0cc782f",
        "predecessor_opus_session_id": "e6147c9e-0303-475f-99ff-93ee38a681e4",
        "started_utc": started_utc,
        "finished_utc": _utc_now(),
        "python": sys.version,
        "python_executable": py,
        "platform": platform.platform(),
        "worktree": str(REPO_ROOT),
        "external_storage_parent_exists_before": ext_before,
        "external_storage_parent_exists_after": ext_after,
        "opus_scratch_present_in_carbon_worktree": opus_scratch_present,
        "git_and_author_evidence": git_and_author,
        "commands": commands,
        "independent_assertions_file": "independent-assertions.json",
        "independent_assertions_sha256": _sha256(assertions_bytes),
        "independent_assertions_bytes": len(assertions_bytes),
        "head_after": head_after,
        "status_after": status_after,
        "never_written_exists_after": never_written_after,
        "other_scratch_entries_after": scratch_leftovers,
        "all_passed": True,
    }
    summary_bytes = (json.dumps(summary, indent=2) + "\n").encode("utf-8")
    (out_dir / "summary.json").write_bytes(summary_bytes)
    print(json.dumps({
        "all_passed": True,
        "head": head_after,
        "commands_run": len(commands),
        "summary_sha256": _sha256(summary_bytes),
        "independent_assertions_sha256": _sha256(assertions_bytes),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
