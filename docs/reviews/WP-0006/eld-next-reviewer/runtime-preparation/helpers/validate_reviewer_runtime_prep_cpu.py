"""CPU-only post-freeze validator for WP-0006 independent reviewer runtime preparation (eld-next-reviewer).

Executes against clean frozen Git HEAD without starting any service/database, without querying GPU
or importing ML/CUDA libraries, and without creating or touching external F2/Q0 roots or B0 resources.
All synthetic release/evidence inputs are explicitly labeled TEST_FIXTURE_ONLY.
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
ROOT = PREP_DIR.parents[4]

if str(HELPERS_DIR) not in sys.path:
    sys.path.insert(0, str(HELPERS_DIR))

import run_f2_reviewer_runtime as rdrv  # noqa: E402

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

SYNTHETIC_AUTHOR_EVIDENCE_COMMIT = "1111111111111111111111111111111111111111"
SYNTHETIC_AUTHOR_003_COMMIT = "2222222222222222222222222222222222222222"
SYNTHETIC_AUTHOR_NO_003_COMMIT = "3333333333333333333333333333333333333333"
SYNTHETIC_RELEASE_COMMIT = "4444444444444444444444444444444444444444"
SYNTHETIC_RELEASE_PATH = "docs/coordination/WP-0006/releases/reviewer-runtime.json"


def make_synthetic_valid_reviewer_release(actual_head: str, now_utc: datetime) -> tuple[dict, dict[str, bytes]]:
    obs_blobs = {
        "docs/coordination/WP-0006/gpu-reviewer-release/host-before.json": (
            b'{"test_fixture_only": true, "ok": true, "kind": "host"}\r\n'
        ),
        "docs/coordination/WP-0006/gpu-reviewer-release/processes-before.json": (
            b'{"test_fixture_only": true, "ok": true, "kind": "procs"}\n'
        ),
        "docs/coordination/WP-0006/gpu-reviewer-release/model-before.json": (
            b'{"test_fixture_only": true, "ok": true, "kind": "model"}\n'
        ),
    }
    obs_meta = {
        "host-before.json": {
            "path": "docs/coordination/WP-0006/gpu-reviewer-release/host-before.json",
            # Deliberately use LF-normalized hash on CRLF blob to verify dual raw/LF representation support:
            "sha256": rdrv.sha256_bytes(
                obs_blobs["docs/coordination/WP-0006/gpu-reviewer-release/host-before.json"].replace(b"\r\n", b"\n")
            ),
        },
        "processes-before.json": {
            "path": "docs/coordination/WP-0006/gpu-reviewer-release/processes-before.json",
            "sha256": rdrv.sha256_bytes(
                obs_blobs["docs/coordination/WP-0006/gpu-reviewer-release/processes-before.json"]
            ),
        },
        "model-before.json": {
            "path": "docs/coordination/WP-0006/gpu-reviewer-release/model-before.json",
            "sha256": rdrv.sha256_bytes(
                obs_blobs["docs/coordination/WP-0006/gpu-reviewer-release/model-before.json"]
            ),
        },
    }
    rel = {
        "_synthetic_label": "TEST_FIXTURE_ONLY_NOT_A_LIVE_COORDINATOR_RELEASE",
        "schema": "eledgercare.f2-reviewer-runtime-release/1",
        "owner": "eld-next-reviewer",
        "conversation_id": "101b19cf-3133-4ead-91cb-9ca6068e3e72",
        "model": "gemini-4-carbon-high",
        "effort": "high",
        "source_commit": rdrv.EXPECTED_SOURCE_COMMIT,
        "executing_head": actual_head,
        "accepted_design_review": rdrv.EXPECTED_ACCEPTED_DESIGN_REVIEW,
        "accepted_source_review": rdrv.EXPECTED_ACCEPTED_SOURCE_REVIEW,
        "author_runtime_evidence": SYNTHETIC_AUTHOR_EVIDENCE_COMMIT,
        "author_003": SYNTHETIC_AUTHOR_003_COMMIT,
        "product_tree_objects": {
            "src": rdrv.EXPECTED_PRODUCT_TREES["src"],
            "workers/local_ocr": rdrv.EXPECTED_PRODUCT_TREES["workers/local_ocr"],
            "web": rdrv.EXPECTED_PRODUCT_TREES["web"],
            "tests": rdrv.EXPECTED_PRODUCT_TREES["tests"],
            "deploy": rdrv.EXPECTED_PRODUCT_TREES["deploy"],
        },
        "pinned_digests": dict(rdrv.EXPECTED_PINNED_DIGESTS),
        "lease_id": "WP-0006-reviewer-runtime-20261116T200000Z",
        "gpu_uuid": rdrv.EXPECTED_GPU_UUID,
        "released_utc": (now_utc - timedelta(minutes=2)).isoformat(),
        "expires_utc": (now_utc + timedelta(hours=4)).isoformat(),
        "max_model_attempts": 4,
        "readonly_q0_root": r"C:\Users\jackg\eLedgerCare-Q0\WP-0005",
        "runtime_root": r"C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer",
        "ports": {"api": 5290, "ui": 4310, "postgres": 55435},
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


class ReviewerRuntimePrepValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now_utc = datetime(2026, 11, 16, 20, 5, 0, tzinfo=timezone.utc)
        self.actual_head = rdrv.git_stdout(ROOT, ["rev-parse", "HEAD"]).lower()
        self.valid_rel, self.obs_blobs = make_synthetic_valid_reviewer_release(self.actual_head, self.now_utc)

    def _validate(
        self,
        rel_doc: dict,
        *,
        release_commit: str = SYNTHETIC_RELEASE_COMMIT,
        release_path: str = SYNTHETIC_RELEASE_PATH,
        database_name: str = rdrv.DEFAULT_REVIEWER_DATABASE_NAME,
    ) -> dict:
        synthetic_commits = {
            SYNTHETIC_AUTHOR_EVIDENCE_COMMIT,
            SYNTHETIC_AUTHOR_003_COMMIT,
            SYNTHETIC_AUTHOR_NO_003_COMMIT,
        }
        return rdrv.validate_reviewer_release_contract(
            rel_doc,
            root=ROOT,
            release_commit=release_commit,
            release_path=release_path,
            now_utc=self.now_utc,
            blob_loader=lambda p: self.obs_blobs[p],
            commit_exists_fn=lambda sha: sha in synthetic_commits or rdrv.git_object_exists(ROOT, f"{sha}^{{commit}}"),
            tree_has_path_fn=lambda sha, rel_p: (
                sha == SYNTHETIC_AUTHOR_003_COMMIT and rel_p == rdrv.CANONICAL_AUTHOR_003_PATH
            )
            or rdrv.git_object_exists(ROOT, f"{sha}:{rel_p}"),
            database_name=database_name,
        )

    def test_01_cli_rejects_missing_release_args(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-B", str(HELPERS_DIR / "run_f2_reviewer_runtime.py"), "--dry-run-validate"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--release-commit", proc.stderr)

    def test_02_cli_rejects_returned_author_release_717a7689(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(HELPERS_DIR / "run_f2_reviewer_runtime.py"),
                "--dry-run-validate",
                "--release-commit",
                "717a768994bbbabf75b8ee96b3b1aadca1bc5df3",
                "--release-path",
                "docs/coordination/WP-0006/releases/author-runtime.json",
            ],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("historical/returned/preparation-only", proc.stderr)

    def test_03_cli_rejects_preparation_only_0e16cfd4_and_35e2f44d_authorities(self) -> None:
        for prep_sha in (
            "0e16cfd473b1dab3b6109c6fba8e7425e91c4ae5",
            "35e2f44d788a99ad1b2d10d1af95536cf1d1981a",
            "2ce3366d6aada92068088090bb026d4579b20e61",
        ):
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(HELPERS_DIR / "run_f2_reviewer_runtime.py"),
                    "--dry-run-validate",
                    "--release-commit",
                    prep_sha,
                    "--release-path",
                    "docs/coordination/WP-0006/releases/reviewer-runtime.json",
                ],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("historical/returned/preparation-only", proc.stderr)

    def test_04_accepts_valid_synthetic_future_reviewer_release_with_ancestry(self) -> None:
        first_parent = rdrv.git_stdout(ROOT, ["rev-parse", "HEAD^1"]).lower()
        self.assertNotEqual(first_parent, rdrv.EXPECTED_SOURCE_COMMIT)
        out = self._validate(self.valid_rel)
        self.assertEqual(out["owner"], "eld-next-reviewer")
        self.assertEqual(out["executing_head"], self.actual_head)
        self.assertEqual(out["source_commit"], rdrv.EXPECTED_SOURCE_COMMIT)
        self.assertEqual(out["accepted_source_review"], rdrv.EXPECTED_ACCEPTED_SOURCE_REVIEW)
        self.assertEqual(out["author_runtime_evidence_commit"], SYNTHETIC_AUTHOR_EVIDENCE_COMMIT)
        self.assertEqual(out["author_003_commit"], SYNTHETIC_AUTHOR_003_COMMIT)
        self.assertEqual(
            out["pinned_digests"]["worker_source_sha256"],
            "c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54",
        )
        self.assertEqual(out["verified_observations"]["host-before.json"]["matched_representation"], "lf_normalized")
        self.assertEqual(len(out["committed_helpers"]), 3)

    def test_05_supports_flexible_source_review_and_author_handoff_shapes(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc.pop("accepted_source_review")
        doc.pop("author_runtime_evidence")
        doc.pop("author_003")
        doc["accepted_reviews"] = {"source_reconciliation": rdrv.EXPECTED_ACCEPTED_SOURCE_REVIEW}
        doc["author_runtime"] = {
            "evidence_commit": SYNTHETIC_AUTHOR_EVIDENCE_COMMIT,
            "report_commit": SYNTHETIC_AUTHOR_003_COMMIT,
        }
        out = self._validate(doc)
        self.assertEqual(out["accepted_source_review"], rdrv.EXPECTED_ACCEPTED_SOURCE_REVIEW)
        self.assertEqual(out["author_runtime_evidence_commit"], SYNTHETIC_AUTHOR_EVIDENCE_COMMIT)
        self.assertEqual(out["author_003_commit"], SYNTHETIC_AUTHOR_003_COMMIT)

    def test_06_rejects_missing_or_unverified_author_003_unless_explicitly_bounded(self) -> None:
        missing_003 = copy.deepcopy(self.valid_rel)
        missing_003.pop("author_003")
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "author_003"):
            self._validate(missing_003)

        no_file_in_commit = copy.deepcopy(self.valid_rel)
        no_file_in_commit["author_003"] = SYNTHETIC_AUTHOR_NO_003_COMMIT
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "does not contain canonical"):
            self._validate(no_file_in_commit)

        bounded = copy.deepcopy(missing_003)
        bounded["allow_bounded_sequencing_without_003_prose"] = True
        out = self._validate(bounded)
        self.assertTrue(out["bounded_sequencing_without_003_prose"])
        self.assertIsNone(out["author_003_commit"])

    def test_07_rejects_missing_or_historical_author_runtime_evidence(self) -> None:
        missing_ev = copy.deepcopy(self.valid_rel)
        missing_ev.pop("author_runtime_evidence")
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "author_runtime_evidence"):
            self._validate(missing_ev)

        for bad_ev in (
            "7280463accdf0ff9fb3a218299193eeff2ec9c9e",  # Pre-model startup failure
            "882438d037fdb754df487c1d20a8bc958f81aeb2",  # CPU driver prep
            "386d5c30809c3c04d6640d9433eb4263306ac126",  # CPU source response
        ):
            bad = copy.deepcopy(self.valid_rel)
            bad["author_runtime_evidence"] = bad_ev
            with self.assertRaisesRegex(rdrv.ReleaseValidationError, "author_runtime_evidence"):
                self._validate(bad)

    def test_08_rejects_wrong_owner_session_or_author_release_path(self) -> None:
        bad_owner = copy.deepcopy(self.valid_rel)
        bad_owner["owner"] = "eld-f2-implementer"
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "owner"):
            self._validate(bad_owner)

        bad_conv = copy.deepcopy(self.valid_rel)
        bad_conv["conversation_id"] = "2b6861af-031b-4e8b-9ce9-2a6d476f9da0"
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "conversation_id"):
            self._validate(bad_conv)

        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "release_path"):
            self._validate(self.valid_rel, release_path="docs/coordination/WP-0006/releases/author-runtime-v2.json")

    def test_09_rejects_unaccepted_or_wrong_source_review_binding(self) -> None:
        for bad_rev in (
            "10193e2c904f99cfc23c97367f1e5d881b0630f2",
            "e2452e1ab3d8937868c07ffb30ce430715b5be78",
            "5555555555555555555555555555555555555555",
        ):
            bad = copy.deepcopy(self.valid_rel)
            bad["accepted_source_review"] = bad_rev
            with self.assertRaisesRegex(rdrv.ReleaseValidationError, "source-review"):
                self._validate(bad)

    def test_10_rejects_old_source_commit_and_pre_prep_or_mismatched_executing_head(self) -> None:
        old_src = copy.deepcopy(self.valid_rel)
        old_src["source_commit"] = "0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978"
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "source_commit"):
            self._validate(old_src)

        for bad_head in (
            "82e8f732afbf038bfb5b6c560f1b1219aaa4e40f",
            "10193e2c904f99cfc23c97367f1e5d881b0630f2",
            "882438d037fdb754df487c1d20a8bc958f81aeb2",
            "6666666666666666666666666666666666666666",
        ):
            bad = copy.deepcopy(self.valid_rel)
            bad["executing_head"] = bad_head
            with self.assertRaisesRegex(rdrv.ReleaseValidationError, "executing_head"):
                self._validate(bad)

    def test_11_rejects_tampered_product_tree_oid_and_old_worker_digest(self) -> None:
        bad_tree = copy.deepcopy(self.valid_rel)
        bad_tree["product_tree_objects"]["workers/local_ocr"] = "304aed238813f5cf6d2c74f6565fc7a8b4c62a23"
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "workers/local_ocr"):
            self._validate(bad_tree)

        bad_dig = copy.deepcopy(self.valid_rel)
        bad_dig["pinned_digests"]["worker_source_sha256"] = (
            "01ad2fa1d6dcf8643ecb5801a934b37bae4630faca2f70959b4a85cc4480eb01"
        )
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "worker_source_sha256"):
            self._validate(bad_dig)

    def test_12_rejects_author_leases_wp0007_leases_expired_premature_and_over_6h_window(self) -> None:
        for bad_lease in (
            "WP-0006-author-runtime-20261116T062318Z",
            "WP-0006-author-runtime-20261116T190000Z",
            "WP-0007-author-heldout-20261116T145544Z",
            "WP-0007-reviewer-005-20261116T200000Z",
        ):
            bad = copy.deepcopy(self.valid_rel)
            bad["lease_id"] = bad_lease
            with self.assertRaisesRegex(rdrv.ReleaseValidationError, "lease_id"):
                self._validate(bad)

        expired = copy.deepcopy(self.valid_rel)
        expired["expires_utc"] = (self.now_utc - timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "expired"):
            self._validate(expired)

        premature = copy.deepcopy(self.valid_rel)
        premature["released_utc"] = (self.now_utc + timedelta(minutes=10)).isoformat()
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "not yet active"):
            self._validate(premature)

        over_6h = copy.deepcopy(self.valid_rel)
        over_6h["expires_utc"] = (self.now_utc + timedelta(hours=6, minutes=5)).isoformat()
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "6h"):
            self._validate(over_6h)

    def test_13_rejects_author_ports_author_runtime_root_and_author_db_names(self) -> None:
        bad_ports = copy.deepcopy(self.valid_rel)
        bad_ports["ports"] = {"api": 5190, "ui": 4210, "postgres": 55434}
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "ports"):
            self._validate(bad_ports)

        for bad_rt in (
            r"C:\Users\jackg\eLedgerCare-F2\WP-0006\author",
            r"C:\Users\jackg\eLedgerCare-F2\WP-0006\author-v2",
            r"C:\Users\jackg\eLedgerCare-F2\WP-0006",
            r"C:\Users\jackg\eLedgerCare-Q0\WP-0005\reviewer",
            str(ROOT / ".scratch" / "reviewer"),
        ):
            bad = copy.deepcopy(self.valid_rel)
            bad["runtime_root"] = bad_rt
            with self.assertRaisesRegex(rdrv.ReleaseValidationError, "runtime_root"):
                self._validate(bad)

        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "Database name"):
            self._validate(self.valid_rel, database_name="eledgercare_f2_runtime_author_v2")

    def test_14_rejects_warmups_holdouts_and_non_4_attempt_matrix(self) -> None:
        warmup_doc = copy.deepcopy(self.valid_rel)
        warmup_doc["plan"][0]["expected"] = "warmup then completed"
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "warmup"):
            self._validate(warmup_doc)

        holdout_doc = copy.deepcopy(self.valid_rel)
        holdout_doc["plan"][0]["fixture_id"] = "SYN-INV-03-v1-raster300"
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "holdout"):
            self._validate(holdout_doc)

        bad_counts = copy.deepcopy(self.valid_rel)
        bad_counts["plan"][2]["model_attempts"] = 3
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "attempt counts"):
            self._validate(bad_counts)

    def test_15_clean_runtime_root_checker_rejects_nonempty_or_unexpected_entries(self) -> None:
        tmp_parent = ROOT / ".scratch" / "reviewer-runtime-prep" / "unit-tmp"
        tmp_parent.mkdir(parents=True, exist_ok=True)
        td = Path(tempfile.mkdtemp(prefix="rev-rt-", dir=str(tmp_parent)))
        try:
            # Absent directory with create_if_missing=False stays absent!
            absent = td / "reviewer-absent"
            self.assertEqual(rdrv.ensure_clean_reviewer_runtime_root(absent, create_if_missing=False), [])
            self.assertFalse(absent.exists())

            # Pre-populated run directory fails closed
            dirty = td / "reviewer-dirty"
            (dirty / "runs" / "attempt-stale").mkdir(parents=True)
            with self.assertRaisesRegex(RuntimeError, "refusing mutable reuse"):
                rdrv.ensure_clean_reviewer_runtime_root(dirty, create_if_missing=False)
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_16_safe_evidence_packager_blocks_secrets_holdouts_and_immutable_dirs(self) -> None:
        tmp_parent = ROOT / ".scratch" / "reviewer-runtime-prep" / "unit-tmp"
        tmp_parent.mkdir(parents=True, exist_ok=True)
        td = Path(tempfile.mkdtemp(prefix="rev-pkg-", dir=str(tmp_parent)))
        try:
            fake_repo = td / "fake_repo"
            src_scratch = td / "scratch_in"
            src_scratch.mkdir(parents=True)
            (src_scratch / "trial-summary-reviewer.json").write_bytes(b'{"test_fixture": true, "ok": 1}\n')

            # 1. Refuses to overwrite immutable review folder names
            imm_dest = fake_repo / "docs" / "reviews" / "WP-0006" / "eld-next-reviewer" / "source-reconciliation"
            with self.assertRaisesRegex(rdrv.ReleaseValidationError, "immutable"):
                rdrv.package_runtime_evidence(src_scratch, imm_dest, root=fake_repo)

            # 2. Clean packaging produces inventory + .gitattributes
            ok_dest = fake_repo / "docs" / "reviews" / "WP-0006" / "eld-next-reviewer" / "runtime-execution"
            inv = rdrv.package_runtime_evidence(src_scratch, ok_dest, root=fake_repo, extra_secrets=["SUPER_SECRET_PW"])
            self.assertEqual(inv["file_count"], 1)
            self.assertTrue((ok_dest / ".gitattributes").is_file())

            # 3. Secret string in scratch fails closed
            (src_scratch / "leak.log").write_bytes(b"conn=SUPER_SECRET_PW\n")
            with self.assertRaisesRegex(rdrv.ReleaseValidationError, "Secret value detected"):
                rdrv.package_runtime_evidence(
                    src_scratch,
                    fake_repo / "docs" / "reviews" / "WP-0006" / "eld-next-reviewer" / "runtime-execution-2",
                    root=fake_repo,
                    extra_secrets=["SUPER_SECRET_PW"],
                )
            (src_scratch / "leak.log").unlink()

            # 4. Holdout token in scratch fails closed
            (src_scratch / "holdout.log").write_bytes(b"read SYN-MP-02 unexpectedly\n")
            with self.assertRaisesRegex(rdrv.ReleaseValidationError, "Forbidden holdout token"):
                rdrv.package_runtime_evidence(
                    src_scratch,
                    fake_repo / "docs" / "reviews" / "WP-0006" / "eld-next-reviewer" / "runtime-execution-3",
                    root=fake_repo,
                )
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_17_zero_ml_cuda_imports_zero_external_reviewer_root_and_ports_unbound(self) -> None:
        leaked = sorted(
            m for m in sys.modules if any(m == pref or m.startswith(pref + ".") for pref in FORBIDDEN_IMPORT_PREFIXES)
        )
        self.assertEqual(leaked, [])
        self.assertFalse(rdrv.EXPECTED_REVIEWER_RUNTIME_ROOT.exists())
        for port in (5290, 4310, 55435):
            self.assertFalse(rdrv.check_port_bound(port), f"Owned reviewer port {port} unexpectedly bound!")


def check_ast_and_digests() -> tuple[int, str]:
    buf = io.StringIO()
    for py_file in (HELPERS_DIR / "run_f2_reviewer_runtime.py", SCRIPT_PATH):
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

    drv_src = (HELPERS_DIR / "run_f2_reviewer_runtime.py").read_text(encoding="utf-8")
    drv_tree = ast.parse(drv_src, filename=str(HELPERS_DIR / "run_f2_reviewer_runtime.py"))
    docstring_ids: set[int] = set()
    for parent in ast.walk(drv_tree):
        if isinstance(parent, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and parent.body:
            first_stmt = parent.body[0]
            if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Constant) and isinstance(first_stmt.value.value, str):
                docstring_ids.add(id(first_stmt.value))
    for node in ast.walk(drv_tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstring_ids:
            if "HEAD~1" in node.value:
                raise RuntimeError("Reviewer driver executable string constant still assumes immediate-parent HEAD~1!")
    buf.write("[PASS] Confirmed zero immediate-parent HEAD~1 assumptions in executable AST of run_f2_reviewer_runtime.py\n")

    local_digests = rdrv.compute_local_worktree_digests(ROOT)
    for k, want in rdrv.EXPECTED_PINNED_DIGESTS.items():
        got = local_digests[k]
        if got != want:
            raise RuntimeError(f"Digest mismatch for {k}: {got} != {want}")
        buf.write(f"[PASS] Pinned digest {k} == {got}\n")

    head_sha = rdrv.git_stdout(ROOT, ["rev-parse", "HEAD"]).lower()
    slnx_oid = rdrv.git_stdout(ROOT, ["rev-parse", f"{head_sha}:ELedgerCare.slnx"]).lower()
    if slnx_oid != rdrv.EXPECTED_SLNX_BLOB:
        raise RuntimeError(f"ELedgerCare.slnx OID mismatch: {slnx_oid} != {rdrv.EXPECTED_SLNX_BLOB}")
    buf.write(f"[PASS] Product solution ELedgerCare.slnx == {slnx_oid}\n")

    for t_path, want_oid in {**rdrv.EXPECTED_PRODUCT_TREES, **rdrv.EXPECTED_IMMUTABLE_TREES_AND_BLOBS}.items():
        got_oid = rdrv.git_stdout(ROOT, ["rev-parse", f"{head_sha}:{t_path}"]).lower()
        if got_oid != want_oid:
            raise RuntimeError(f"OID mismatch for {t_path}: {got_oid} != {want_oid}")
        buf.write(f"[PASS] Verified exact Git OID {t_path} == {got_oid}\n")

    if rdrv.git_object_exists(ROOT, f"{head_sha}:{rdrv.CANONICAL_REVIEWER_004_PATH}"):
        raise RuntimeError("Canonical /004 report unexpectedly exists during runtime preparation!")
    buf.write(f"[PASS] Confirmed canonical {rdrv.CANONICAL_REVIEWER_004_PATH} remains held (absent)\n")

    if rdrv.EXPECTED_REVIEWER_RUNTIME_ROOT.exists():
        raise RuntimeError(f"External reviewer runtime root unexpectedly exists: {rdrv.EXPECTED_REVIEWER_RUNTIME_ROOT}")
    buf.write(f"[PASS] Confirmed external reviewer runtime root absent: {rdrv.EXPECTED_REVIEWER_RUNTIME_ROOT}\n")

    return 0, buf.getvalue()


def main() -> int:
    head_sha = rdrv.git_stdout(ROOT, ["rev-parse", "HEAD"]).lower()
    porcelain = rdrv.git_stdout(ROOT, ["status", "--porcelain"])
    if porcelain != "":
        raise RuntimeError(f"Freeze violation: working tree must be clean before validation, got: {porcelain!r}")

    if rdrv.EXPECTED_REVIEWER_RUNTIME_ROOT.exists():
        raise RuntimeError(f"External reviewer runtime root must not exist: {rdrv.EXPECTED_REVIEWER_RUNTIME_ROOT}")

    out_dir = ROOT / ".scratch" / "reviewer-runtime-prep"
    logs_dir = out_dir / "logs"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    ports_before = {str(p): rdrv.check_port_bound(p) for p in (5290, 4310, 55435)}
    if any(ports_before.values()):
        raise RuntimeError(f"Owned reviewer ports bound before CPU validation: {ports_before}")

    steps_summary: list[dict] = []

    # Step 01: Python compile, AST guard, digest & Git tree/blob verification
    t0 = time.perf_counter()
    rc1, out1 = check_ast_and_digests()
    dur1 = round((time.perf_counter() - t0) * 1000)
    raw1 = out1.replace("\r\n", "\n").encode("utf-8")
    (logs_dir / "01-python-compile-ast-and-tree-guard.log").write_bytes(raw1)
    steps_summary.append({
        "step": "01-python-compile-ast-and-tree-guard",
        "exit_code": rc1,
        "duration_ms": dur1,
        "log_file": "logs/01-python-compile-ast-and-tree-guard.log",
        "byte_length": len(raw1),
        "raw_file_sha256": rdrv.sha256_bytes(raw1),
        "lf_normalized_sha256": rdrv.sha256_bytes(raw1),
    })

    # Step 02: Node syntax check on verify_ui_reviewer_real_results.mjs
    t0 = time.perf_counter()
    node_proc = subprocess.run(
        ["node", "--check", str(HELPERS_DIR / "verify_ui_reviewer_real_results.mjs")],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    dur2 = round((time.perf_counter() - t0) * 1000)
    out2 = (
        "$ node --check docs/reviews/WP-0006/eld-next-reviewer/runtime-preparation/helpers/verify_ui_reviewer_real_results.mjs\n"
        f"exit_code={node_proc.returncode}\n"
        f"{node_proc.stdout}{node_proc.stderr}"
    ).replace("\r\n", "\n")
    raw2 = out2.encode("utf-8")
    (logs_dir / "02-node-syntax-check.log").write_bytes(raw2)
    if node_proc.returncode != 0:
        raise RuntimeError(f"node --check failed:\n{out2}")
    steps_summary.append({
        "step": "02-node-syntax-check",
        "exit_code": node_proc.returncode,
        "duration_ms": dur2,
        "log_file": "logs/02-node-syntax-check.log",
        "byte_length": len(raw2),
        "raw_file_sha256": rdrv.sha256_bytes(raw2),
        "lf_normalized_sha256": rdrv.sha256_bytes(raw2),
    })

    # Step 03: Focused unit & subprocess release-validator tests (17 test methods)
    t0 = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReviewerRuntimePrepValidationTests)
    u_buf = io.StringIO()
    runner = unittest.TextTestRunner(stream=u_buf, verbosity=2)
    u_res = runner.run(suite)
    dur3 = round((time.perf_counter() - t0) * 1000)
    raw3 = u_buf.getvalue().replace("\r\n", "\n").encode("utf-8")
    (logs_dir / "03-reviewer-release-validator-tests.log").write_bytes(raw3)
    rc3 = 0 if u_res.wasSuccessful() else 1
    steps_summary.append({
        "step": "03-reviewer-release-validator-tests",
        "exit_code": rc3,
        "tests_run": u_res.testsRun,
        "failures": len(u_res.failures),
        "errors": len(u_res.errors),
        "duration_ms": dur3,
        "log_file": "logs/03-reviewer-release-validator-tests.log",
        "byte_length": len(raw3),
        "raw_file_sha256": rdrv.sha256_bytes(raw3),
        "lf_normalized_sha256": rdrv.sha256_bytes(raw3),
    })
    if rc3 != 0:
        raise RuntimeError(f"Reviewer runtime prep unit validation failed:\n{u_buf.getvalue()}")

    # Remove unit-tmp inside scratch while retaining raw logs
    shutil.rmtree(out_dir / "unit-tmp", ignore_errors=True)

    ports_after = {str(p): rdrv.check_port_bound(p) for p in (5290, 4310, 55435)}
    porcelain_after = rdrv.git_stdout(ROOT, ["status", "--porcelain"])
    external_root_after = rdrv.EXPECTED_REVIEWER_RUNTIME_ROOT.exists()
    if any(ports_after.values()) or porcelain_after != "" or external_root_after:
        raise RuntimeError(
            f"Post-validation invariant violated: ports={ports_after}, porcelain={porcelain_after!r}, ext_root={external_root_after}"
        )

    summary = {
        "schema": "eledgercare.wp-0006.reviewer-runtime-preparation-summary/1",
        "reviewer": rdrv.EXPECTED_OWNER,
        "conversation_id": rdrv.EXPECTED_CONVERSATION_ID,
        "model": rdrv.EXPECTED_MODEL,
        "effort": rdrv.EXPECTED_EFFORT,
        "validated_utc": rdrv.utc_now(),
        "preparation_authority_commit": "0e16cfd473b1dab3b6109c6fba8e7425e91c4ae5",
        "clean_start_accepted_source_review": rdrv.EXPECTED_ACCEPTED_SOURCE_REVIEW,
        "inspected_author_driver_prep_commit": rdrv.AUTHOR_DRIVER_PREP_COMMIT,
        "inspected_author_driver_freeze_commit": rdrv.AUTHOR_DRIVER_FREEZE_COMMIT,
        "frozen_reviewer_helper_commit": head_sha,
        "protected_source_commit": rdrv.EXPECTED_SOURCE_COMMIT,
        "accepted_design_review_002": rdrv.EXPECTED_ACCEPTED_DESIGN_REVIEW,
        "canonical_004_status": "held_pending_released_independent_runtime_and_author_003_disposition",
        "git_clean_before_and_after": porcelain_after == "",
        "reviewer_ports_bound_before": ports_before,
        "reviewer_ports_bound_after": ports_after,
        "external_reviewer_runtime_root_exists_before": False,
        "external_reviewer_runtime_root_exists_after": external_root_after,
        "ml_or_cuda_modules_imported": [],
        "gpu_queries_executed": 0,
        "services_or_databases_started": False,
        "test_data_labeling": "TEST_FIXTURE_ONLY synthetic release & scratch fixtures; zero holdout access",
        "pinned_digests_verified": rdrv.compute_local_worktree_digests(ROOT),
        "product_tree_objects_verified": dict(rdrv.EXPECTED_PRODUCT_TREES),
        "immutable_trees_and_blobs_verified": dict(rdrv.EXPECTED_IMMUTABLE_TREES_AND_BLOBS),
        "committed_helpers_verified": rdrv.verify_committed_helpers_unchanged(ROOT, head_sha),
        "steps": steps_summary,
        "total_unittest_methods_passed": u_res.testsRun,
    }
    rdrv.write_json_lf(out_dir / "validation-summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
