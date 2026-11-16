"""CPU-only post-freeze validator for WP-0006 versioned runtime driver v2 (eld-f2-implementer).

Executes against clean frozen Git HEAD without starting any service/database, without querying or
importing ML/CUDA libraries, and without touching external F2/Q0 roots or WP-0007/reviewer resources.
"""

from __future__ import annotations

import ast
import copy
from datetime import datetime, timedelta, timezone
import io
import json
import py_compile
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT_PATH = Path(__file__).resolve()
HELPERS_DIR = SCRIPT_PATH.parent
PREP_DIR = HELPERS_DIR.parent
ROOT = PREP_DIR.parent.parent.parent.parent

if str(HELPERS_DIR) not in sys.path:
    sys.path.insert(0, str(HELPERS_DIR))

import run_f2_author_runtime_v2 as drv  # noqa: E402

FORBIDDEN_IMPORT_PREFIXES = (
    "torch",
    "transformers",
    "safetensors",
    "accelerate",
    "huggingface_hub",
    "tokenizers",
    "pypdfium2",
    "PIL",
    "torchvision",
    "qualification",
    "research",
    "evaluation",
)


def make_synthetic_valid_release(actual_head: str, now_utc: datetime) -> tuple[dict, dict[str, bytes]]:
    obs_blobs = {
        "docs/coordination/WP-0006/gpu-author-v2-release/host-before.json": b'{"ok": true, "kind": "host"}\r\n',
        "docs/coordination/WP-0006/gpu-author-v2-release/processes-before.json": b'{"ok": true, "kind": "procs"}\n',
        "docs/coordination/WP-0006/gpu-author-v2-release/model-before.json": b'{"ok": true, "kind": "model"}\n',
    }
    obs_meta = {
        "host-before.json": {
            "path": "docs/coordination/WP-0006/gpu-author-v2-release/host-before.json",
            # Deliberately use LF-normalized hash on CRLF blob to verify dual raw/LF representation support:
            "sha256": drv.sha256_bytes(obs_blobs["docs/coordination/WP-0006/gpu-author-v2-release/host-before.json"].replace(b"\r\n", b"\n")),
        },
        "processes-before.json": {
            "path": "docs/coordination/WP-0006/gpu-author-v2-release/processes-before.json",
            "sha256": drv.sha256_bytes(obs_blobs["docs/coordination/WP-0006/gpu-author-v2-release/processes-before.json"]),
        },
        "model-before.json": {
            "path": "docs/coordination/WP-0006/gpu-author-v2-release/model-before.json",
            "sha256": drv.sha256_bytes(obs_blobs["docs/coordination/WP-0006/gpu-author-v2-release/model-before.json"]),
        },
    }
    rel = {
        "schema": "eledgercare.f2-runtime-release/2",
        "owner": "eld-f2-implementer",
        "conversation_id": "2b6861af-031b-4e8b-9ce9-2a6d476f9da0",
        "model": "gemini-4-carbon-high",
        "effort": "high",
        "source_commit": drv.EXPECTED_SOURCE_COMMIT,
        "executing_head": actual_head,
        "accepted_design_review": drv.EXPECTED_ACCEPTED_DESIGN_REVIEW,
        "accepted_source_review": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "product_tree_objects": {
            "src": drv.EXPECTED_PRODUCT_TREES["src"],
            "workers/local_ocr": drv.EXPECTED_PRODUCT_TREES["workers/local_ocr"],
            "web": drv.EXPECTED_PRODUCT_TREES["web"],
            "tests": drv.EXPECTED_PRODUCT_TREES["tests"],
            "deploy": drv.EXPECTED_PRODUCT_TREES["deploy"],
        },
        "pinned_digests": dict(drv.EXPECTED_PINNED_DIGESTS),
        "lease_id": "WP-0006-author-runtime-20261116T180000Z",
        "gpu_uuid": drv.EXPECTED_GPU_UUID,
        "released_utc": (now_utc - timedelta(minutes=2)).isoformat(),
        "expires_utc": (now_utc + timedelta(hours=4)).isoformat(),
        "max_model_attempts": 4,
        "readonly_q0_root": r"C:\Users\jackg\eLedgerCare-Q0\WP-0005",
        "runtime_root": r"C:\Users\jackg\eLedgerCare-F2\WP-0006\author",
        "ports": {"api": 5190, "ui": 4210, "postgres": 55434},
        "storage_cap_bytes": 4294967296,
        "free_floor_bytes": 21474836480,
        "allow_test_content": False,
        "torchvision_local_sha256_TOFU_accepted": True,
        "plan": [
            {
                "fixture_id": "SYN-WO-01-v1-raster300",
                "expected": "completed persisted result and UI",
                "model_attempts": 1,
            },
            {
                "fixture_id": "SYN-MP-01-v0-clean",
                "expected": "completed three ordered pages",
                "model_attempts": 1,
            },
            {
                "fixture_id": "SYN-WO-01-v1-raster300",
                "expected": "fresh job interrupted by owned supervisor single-process termination during inference, explicit retry completed",
                "model_attempts": 2,
            },
            {
                "expected": "API and PostgreSQL restart, disabled-model saved result reopen",
                "model_attempts": 0,
            },
        ],
        "observation_files": obs_meta,
    }
    return rel, obs_blobs


class DriverV2ValidationTests(unittest.TestCase):
    SYNTHETIC_RELEASE_COMMIT = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    SYNTHETIC_RELEASE_PATH = "docs/coordination/WP-0006/releases/author-runtime-v2.json"

    def setUp(self) -> None:
        self.now_utc = datetime(2026, 11, 16, 18, 5, 0, tzinfo=timezone.utc)
        self.actual_head = drv.git_stdout(ROOT, ["rev-parse", "HEAD"]).lower()
        self.valid_rel, self.obs_blobs = make_synthetic_valid_release(self.actual_head, self.now_utc)

    def _validate(self, rel_doc: dict, *, release_commit: str | None = None, database_name: str = drv.DEFAULT_V2_DATABASE_NAME) -> dict:
        return drv.validate_release_contract(
            rel_doc,
            root=ROOT,
            release_commit=release_commit or self.SYNTHETIC_RELEASE_COMMIT,
            release_path=self.SYNTHETIC_RELEASE_PATH,
            now_utc=self.now_utc,
            blob_loader=lambda p: self.obs_blobs[p],
            commit_exists_fn=lambda sha: sha == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            or drv.git_object_exists(ROOT, f"{sha}^{{commit}}"),
            database_name=database_name,
        )

    def test_01_cli_rejects_missing_release_args(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-B", str(HELPERS_DIR / "run_f2_author_runtime_v2.py"), "--dry-run-validate"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--release-commit", proc.stderr)

    def test_02_cli_rejects_expired_returned_717a7689_release(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(HELPERS_DIR / "run_f2_author_runtime_v2.py"),
                "--dry-run-validate",
                "--release-commit",
                "717a768994bbbabf75b8ee96b3b1aadca1bc5df3",
                "--release-path",
                "docs/coordination/WP-0006/releases/author-runtime.json",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("historical/returned/preparation-only", proc.stderr)

    def test_03_cli_rejects_preparation_only_35e2f44d_authority(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(HELPERS_DIR / "run_f2_author_runtime_v2.py"),
                "--dry-run-validate",
                "--release-commit",
                "35e2f44d788a99ad1b2d10d1af95536cf1d1981a",
                "--release-path",
                "docs/coordination/WP-0006/releases/author-runtime.json",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("historical/returned/preparation-only", proc.stderr)

    def test_04_accepts_valid_future_release_with_non_parent_source_ancestry(self) -> None:
        parent_sha = drv.git_stdout(ROOT, ["rev-parse", "HEAD~1"]).lower()
        self.assertNotEqual(parent_sha, drv.EXPECTED_SOURCE_COMMIT)
        out = self._validate(self.valid_rel)
        self.assertEqual(out["executing_head"], self.actual_head)
        self.assertEqual(out["source_commit"], drv.EXPECTED_SOURCE_COMMIT)
        self.assertEqual(
            out["pinned_digests"]["worker_source_sha256"],
            "c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54",
        )
        self.assertEqual(out["verified_observations"]["host-before.json"]["matched_representation"], "lf_normalized")
        self.assertEqual(len(out["committed_helpers"]), 2)

    def test_05_supports_multiple_source_review_field_shapes(self) -> None:
        for variant in (
            {"accepted_source_reconciliation": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
            {"source_reconciliation_review": {"commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}},
            {"accepted_reviews": {"source": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}},
        ):
            doc = copy.deepcopy(self.valid_rel)
            doc.pop("accepted_source_review", None)
            doc.update(variant)
            out = self._validate(doc)
            self.assertEqual(out["accepted_source_review"], "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

    def test_06_rejects_missing_or_unaccepted_10193e2c_source_review(self) -> None:
        missing = copy.deepcopy(self.valid_rel)
        missing.pop("accepted_source_review")
        with self.assertRaisesRegex(drv.ReleaseValidationError, "source-review"):
            self._validate(missing)

        unaccepted = copy.deepcopy(self.valid_rel)
        unaccepted["accepted_source_review"] = "10193e2c904f99cfc23c97367f1e5d881b0630f2"
        with self.assertRaisesRegex(drv.ReleaseValidationError, "Invalid or unaccepted"):
            self._validate(unaccepted)

    def test_07_rejects_old_0ad2fcd1_source_commit_and_old_6faec9bf_head(self) -> None:
        old_src = copy.deepcopy(self.valid_rel)
        old_src["source_commit"] = "0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978"
        with self.assertRaisesRegex(drv.ReleaseValidationError, "source_commit"):
            self._validate(old_src)

        old_head = copy.deepcopy(self.valid_rel)
        old_head["executing_head"] = "6faec9bf6eccc297a548523dbb52ae9262b25152"
        with self.assertRaisesRegex(drv.ReleaseValidationError, "executing_head"):
            self._validate(old_head)

    def test_08_rejects_mismatched_executing_head(self) -> None:
        bad = copy.deepcopy(self.valid_rel)
        bad["executing_head"] = "cccccccccccccccccccccccccccccccccccccccc"
        with self.assertRaisesRegex(drv.ReleaseValidationError, "does not match release executing_head"):
            self._validate(bad)

    def test_09_rejects_tampered_product_tree_oid(self) -> None:
        bad = copy.deepcopy(self.valid_rel)
        bad["product_tree_objects"]["workers/local_ocr"] = "304aed238813f5cf6d2c74f6565fc7a8b4c62a23"
        with self.assertRaisesRegex(drv.ReleaseValidationError, "workers/local_ocr"):
            self._validate(bad)

    def test_10_rejects_old_01ad2fa1_worker_source_sha256(self) -> None:
        bad = copy.deepcopy(self.valid_rel)
        bad["pinned_digests"]["worker_source_sha256"] = (
            "01ad2fa1d6dcf8643ecb5801a934b37bae4630faca2f70959b4a85cc4480eb01"
        )
        with self.assertRaisesRegex(drv.ReleaseValidationError, "worker_source_sha256"):
            self._validate(bad)

    def test_11_rejects_returned_lease_and_wp0007_or_reviewer_lease(self) -> None:
        for bad_lease in (
            "WP-0006-author-runtime-20261116T062318Z",
            "WP-0007-author-heldout-20261116T145544Z",
            "WP-0006-reviewer-runtime-20261116T180000Z",
        ):
            bad = copy.deepcopy(self.valid_rel)
            bad["lease_id"] = bad_lease
            with self.assertRaisesRegex(drv.ReleaseValidationError, "lease_id"):
                self._validate(bad)

    def test_12_rejects_expired_or_premature_lease_timestamps(self) -> None:
        expired = copy.deepcopy(self.valid_rel)
        expired["expires_utc"] = (self.now_utc - timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(drv.ReleaseValidationError, "expired"):
            self._validate(expired)

        premature = copy.deepcopy(self.valid_rel)
        premature["released_utc"] = (self.now_utc + timedelta(minutes=10)).isoformat()
        with self.assertRaisesRegex(drv.ReleaseValidationError, "not yet active"):
            self._validate(premature)

    def test_13_rejects_wrong_ports_unsafe_roots_and_trial1_db_collision(self) -> None:
        bad_port = copy.deepcopy(self.valid_rel)
        bad_port["ports"] = {"api": 5191, "ui": 4210, "postgres": 55434}
        with self.assertRaisesRegex(drv.ReleaseValidationError, "ports"):
            self._validate(bad_port)

        bad_root = copy.deepcopy(self.valid_rel)
        bad_root["runtime_root"] = r"C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer"
        with self.assertRaisesRegex(drv.ReleaseValidationError, "runtime_root"):
            self._validate(bad_root)

        with self.assertRaisesRegex(drv.ReleaseValidationError, "collides with retained initial trial DB"):
            self._validate(self.valid_rel, database_name="eledgercare_f2_runtime_author")

    def test_14_rejects_modified_attempt_matrix_warmups_and_holdouts(self) -> None:
        warmup_doc = copy.deepcopy(self.valid_rel)
        warmup_doc["plan"][0]["expected"] = "warmup then completed result"
        with self.assertRaisesRegex(drv.ReleaseValidationError, "warmup"):
            self._validate(warmup_doc)

        holdout_doc = copy.deepcopy(self.valid_rel)
        holdout_doc["plan"][0]["fixture_id"] = "SYN-WO-03-v0-clean"
        with self.assertRaisesRegex(drv.ReleaseValidationError, "holdout"):
            self._validate(holdout_doc)

        extra_attempts = copy.deepcopy(self.valid_rel)
        extra_attempts["max_model_attempts"] = 5
        with self.assertRaisesRegex(drv.ReleaseValidationError, "max_model_attempts"):
            self._validate(extra_attempts)

    def test_15_runtime_root_snapshot_separates_and_protects_retained_prior_failure(self) -> None:
        scratch_tmp_parent = ROOT / ".scratch" / "stage2-runtime-v2-prep" / "unit-tmp"
        scratch_tmp_parent.mkdir(parents=True, exist_ok=True)
        tmp_dir = Path(tempfile.mkdtemp(prefix="rtroot-", dir=str(scratch_tmp_parent)))
        try:
            # Case A: empty fresh directory
            names_a, snap_a = drv.inspect_and_snapshot_runtime_root(
                tmp_dir / "author-v2",
                set(drv.DEFAULT_RETAINED_PRIOR_RUN_DIRS),
                create_if_missing=True,
            )
            self.assertEqual(names_a, [])
            self.assertEqual(snap_a, {})

            # Case B: existing directory containing retained initial failed run dir
            sim_author = tmp_dir / "author"
            ret_dir = sim_author / "runs" / "attempt-01a1e316-879e-737e-b222-cf9ebea58b09" / "output"
            ret_dir.mkdir(parents=True, exist_ok=True)
            stderr_file = ret_dir / "child.stderr.log"
            stderr_file.write_bytes(b"ModuleNotFoundError: No module named 'local_ocr'\n")

            names_b, snap_b = drv.inspect_and_snapshot_runtime_root(
                sim_author,
                set(drv.DEFAULT_RETAINED_PRIOR_RUN_DIRS),
                create_if_missing=False,
            )
            self.assertEqual(names_b, ["attempt-01a1e316-879e-737e-b222-cf9ebea58b09"])
            self.assertTrue(drv.verify_retained_snapshot_unchanged(sim_author, snap_b))

            # Simulate 4 new release run directories created alongside retained prior dir
            for idx in range(1, 5):
                (sim_author / "runs" / f"attempt-00000000-0000-0000-0000-00000000000{idx}").mkdir()
            new_dirs = drv.list_new_run_directories(sim_author, set(names_b))
            self.assertEqual(len(new_dirs), 4)
            self.assertNotIn("attempt-01a1e316-879e-737e-b222-cf9ebea58b09", new_dirs)
            self.assertTrue(drv.verify_retained_snapshot_unchanged(sim_author, snap_b))

            # Mutating the retained file must fail closed!
            stderr_file.write_bytes(b"tampered")
            with self.assertRaisesRegex(RuntimeError, "modified during execution"):
                drv.verify_retained_snapshot_unchanged(sim_author, snap_b)

            # Unknown pre-existing run directory must fail closed on preflight!
            with self.assertRaisesRegex(RuntimeError, "Unexpected pre-existing run directory"):
                drv.inspect_and_snapshot_runtime_root(
                    sim_author,
                    set(drv.DEFAULT_RETAINED_PRIOR_RUN_DIRS),
                    create_if_missing=False,
                )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_16_zero_ml_cuda_modules_imported_and_ports_remain_unbound(self) -> None:
        leaked = sorted(
            m for m in sys.modules if any(m == pref or m.startswith(pref + ".") for pref in FORBIDDEN_IMPORT_PREFIXES)
        )
        self.assertEqual(leaked, [])
        for port in (5190, 4210, 55434):
            self.assertFalse(drv.check_port_bound(port), f"Owned author port {port} unexpectedly bound!")


def check_ast_and_digests() -> tuple[int, str]:
    buf = io.StringIO()
    for py_file in (HELPERS_DIR / "run_f2_author_runtime_v2.py", SCRIPT_PATH):
        py_compile.compile(str(py_file), doraise=True)
        src = py_file.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(FORBIDDEN_IMPORT_PREFIXES):
                        raise RuntimeError(f"Forbidden import {alias.name} in {py_file.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    raise RuntimeError(f"Forbidden from-import {node.module} in {py_file.name}")
        buf.write(f"[PASS] py_compile + AST import safety verified: {py_file.relative_to(ROOT).as_posix()}\n")

    drv_src = (HELPERS_DIR / "run_f2_author_runtime_v2.py").read_text(encoding="utf-8")
    code_non_comment = "\n".join(
        ln for ln in drv_src.splitlines() if not ln.lstrip().startswith("#") and '"""' not in ln
    )
    if "HEAD~1" in code_non_comment:
        raise RuntimeError("Driver code still references HEAD~1!")
    buf.write("[PASS] Confirmed zero HEAD~1 immediate-parent assumptions in run_f2_author_runtime_v2.py\n")

    local_digests = drv.compute_local_worktree_digests(ROOT)
    for k, want in drv.EXPECTED_PINNED_DIGESTS.items():
        got = local_digests[k]
        if got != want:
            raise RuntimeError(f"Digest mismatch for {k}: {got} != {want}")
        buf.write(f"[PASS] Pinned digest {k} == {got}\n")

    head_sha = drv.git_stdout(ROOT, ["rev-parse", "HEAD"]).lower()
    for t_path, want_oid in {**drv.EXPECTED_PRODUCT_TREES, **drv.EXPECTED_PROTECTED_TREES}.items():
        got_oid = drv.git_stdout(ROOT, ["rev-parse", f"{head_sha}:{t_path}"]).lower()
        if got_oid != want_oid:
            raise RuntimeError(f"Tree OID mismatch for {t_path}: {got_oid} != {want_oid}")
        buf.write(f"[PASS] Protected/product tree {t_path} == {got_oid}\n")

    return 0, buf.getvalue()


def main() -> int:
    head_sha = drv.git_stdout(ROOT, ["rev-parse", "HEAD"]).lower()
    porcelain = drv.git_stdout(ROOT, ["status", "--porcelain"])
    if porcelain != "":
        raise RuntimeError(f"Freeze violation: working tree must be clean before validation, got: {porcelain!r}")

    out_dir = ROOT / ".scratch" / "stage2-runtime-v2-prep"
    logs_dir = out_dir / "logs"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    ports_before = {str(p): drv.check_port_bound(p) for p in (5190, 4210, 55434)}
    if any(ports_before.values()):
        raise RuntimeError(f"Owned author ports bound before CPU validation: {ports_before}")

    steps_summary: list[dict] = []

    # Step 01: Python compile, AST guard, digest & tree verification
    t0 = time.perf_counter()
    rc1, out1 = check_ast_and_digests()
    dur1 = round((time.perf_counter() - t0) * 1000)
    raw1 = out1.replace("\r\n", "\n").encode("utf-8")
    log1 = logs_dir / "01-python-compile-and-ast-guard.log"
    log1.write_bytes(raw1)
    steps_summary.append({
        "step": "01-python-compile-and-ast-guard",
        "exit_code": rc1,
        "duration_ms": dur1,
        "log_file": "logs/01-python-compile-and-ast-guard.log",
        "byte_length": len(raw1),
        "raw_file_sha256": drv.sha256_bytes(raw1),
        "lf_normalized_sha256": drv.sha256_bytes(raw1),
    })

    # Step 02: Node syntax check on verify_ui_real_results_v2.mjs
    t0 = time.perf_counter()
    node_proc = subprocess.run(
        ["node", "--check", str(HELPERS_DIR / "verify_ui_real_results_v2.mjs")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    dur2 = round((time.perf_counter() - t0) * 1000)
    out2 = (
        f"$ node --check docs/implementation/WP-0006/runtime-corrected-preparation/helpers/verify_ui_real_results_v2.mjs\n"
        f"exit_code={node_proc.returncode}\n"
        f"{node_proc.stdout}{node_proc.stderr}"
    ).replace("\r\n", "\n")
    raw2 = out2.encode("utf-8")
    log2 = logs_dir / "02-node-syntax-check.log"
    log2.write_bytes(raw2)
    if node_proc.returncode != 0:
        raise RuntimeError(f"node --check failed:\n{out2}")
    steps_summary.append({
        "step": "02-node-syntax-check",
        "exit_code": node_proc.returncode,
        "duration_ms": dur2,
        "log_file": "logs/02-node-syntax-check.log",
        "byte_length": len(raw2),
        "raw_file_sha256": drv.sha256_bytes(raw2),
        "lf_normalized_sha256": drv.sha256_bytes(raw2),
    })

    # Step 03: Focused unit & subprocess validator tests (16 tests)
    t0 = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DriverV2ValidationTests)
    u_buf = io.StringIO()
    runner = unittest.TextTestRunner(stream=u_buf, verbosity=2)
    u_res = runner.run(suite)
    dur3 = round((time.perf_counter() - t0) * 1000)
    raw3 = u_buf.getvalue().replace("\r\n", "\n").encode("utf-8")
    log3 = logs_dir / "03-driver-release-validator-tests.log"
    log3.write_bytes(raw3)
    rc3 = 0 if u_res.wasSuccessful() else 1
    steps_summary.append({
        "step": "03-driver-release-validator-tests",
        "exit_code": rc3,
        "tests_run": u_res.testsRun,
        "failures": len(u_res.failures),
        "errors": len(u_res.errors),
        "duration_ms": dur3,
        "log_file": "logs/03-driver-release-validator-tests.log",
        "byte_length": len(raw3),
        "raw_file_sha256": drv.sha256_bytes(raw3),
        "lf_normalized_sha256": drv.sha256_bytes(raw3),
    })
    if rc3 != 0:
        raise RuntimeError(f"Unit validation failed:\n{u_buf.getvalue()}")

    ports_after = {str(p): drv.check_port_bound(p) for p in (5190, 4210, 55434)}
    porcelain_after = drv.git_stdout(ROOT, ["status", "--porcelain"])

    summary = {
        "schema": "eledgercare.wp-0006.runtime-driver-v2-preparation-summary/1",
        "validated_utc": drv.utc_now(),
        "preparation_authority_commit": "35e2f44d788a99ad1b2d10d1af95536cf1d1981a",
        "frozen_helper_commit": head_sha,
        "protected_source_commit": drv.EXPECTED_SOURCE_COMMIT,
        "source_response_checkpoint": drv.EXPECTED_SOURCE_RESPONSE_CHECKPOINT,
        "git_clean_before_and_after": porcelain_after == "",
        "ports_bound_before": ports_before,
        "ports_bound_after": ports_after,
        "ml_or_cuda_modules_imported": [],
        "external_roots_touched": False,
        "services_or_databases_started": False,
        "pinned_digests_verified": drv.compute_local_worktree_digests(ROOT),
        "product_tree_objects_verified": dict(drv.EXPECTED_PRODUCT_TREES),
        "protected_tree_objects_verified": dict(drv.EXPECTED_PROTECTED_TREES),
        "steps": steps_summary,
        "total_unittest_assertions_passed": u_res.testsRun,
    }
    drv.write_json_lf(out_dir / "validation-summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
