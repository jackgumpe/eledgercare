"""CPU-only post-freeze validator for WP-0006 reviewer UI-expectation reconciliation v2 (eld-next-reviewer).

Executes against clean frozen Git HEAD without starting any service/database, without querying GPU
or importing ML/CUDA libraries, and without creating or touching external F2/Q0 roots or B0 resources.
All synthetic release, UI observation, and scratch inputs are explicitly labeled TEST_FIXTURE_ONLY.
"""

from __future__ import annotations

import ast
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import py_compile
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT_PATH = Path(__file__).resolve()
HELPERS_DIR = SCRIPT_PATH.parent
RECON_DIR = HELPERS_DIR.parent
ROOT = RECON_DIR.parents[4]

if str(HELPERS_DIR) not in sys.path:
    sys.path.insert(0, str(HELPERS_DIR))

import run_f2_reviewer_runtime_v2 as rdrv  # noqa: E402

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


def parse_accepted_ui_status_labels(root: Path = ROOT) -> dict[str, str]:
    """Extracts the exact statusLabels map from accepted web/src/app/intake/receipt.ts."""
    receipt_ts = (root / "web" / "src" / "app" / "intake" / "receipt.ts").read_text(encoding="utf-8")
    m = re.search(r"const\s+statusLabels\s*:\s*Record<string,\s*string>\s*=\s*\{([^}]+)\};", receipt_ts, re.DOTALL)
    if not m:
        raise RuntimeError("Could not locate statusLabels mapping in web/src/app/intake/receipt.ts")
    pairs = re.findall(r"([a-z_]+)\s*:\s*'([^']+)'", m.group(1))
    if not pairs:
        raise RuntimeError("No key/value pairs parsed from statusLabels in web/src/app/intake/receipt.ts")
    return dict(pairs)


def audit_document_page_template_selectors(root: Path = ROOT) -> dict:
    """Verifies every data-testid and attempt-row binding used by verify_ui_reviewer_real_results_v2.mjs against document-page.ts."""
    doc_page_ts = (root / "web" / "src" / "app" / "intake" / "document-page.ts").read_text(encoding="utf-8")
    required_static_testids = (
        "document-id",
        "document-job-id",
        "document-status",
        "document-page-count",
        "document-byte-length",
        "document-sha256",
        "document-download",
        "extraction-unsupported",
        "extraction-unavailable",
        "extraction-active",
        "extraction-failure",
        "request-extraction",
        "refresh-extraction",
        "retry-extraction",
        "attempt-history",
        "extraction-result",
        "unreviewed-banner",
        "result-id",
        "result-attempt-id",
        "result-model",
        "result-renderer",
        "result-raw-byte-length",
        "result-raw-sha256",
        "result-raw-details",
        "result-raw-text",
    )
    missing_static = [tid for tid in required_static_testids if f'data-testid="{tid}"' not in doc_page_ts]
    if missing_static:
        raise RuntimeError(f"Missing expected data-testid(s) in document-page.ts: {missing_static}")

    required_dynamic_bindings = (
        "[attr.data-testid]=\"'attempt-row-' + att.attemptNumber\"",
        "[attr.data-testid]=\"'result-page-' + page.pageNumber\"",
        "<td>{{ att.attemptNumber }}</td>",
        "<td><code>{{ att.attemptId }}</code></td>",
        "<td>{{ statusLabel(att.status) }}</td>",
        "<td>{{ att.phase }}</td>",
        "<td>{{ att.startedAtUtc }}</td>",
        "<td>{{ att.endedAtUtc ?? '—' }}</td>",
        "Unreviewed raw extraction output ({{ res.reviewStatus }})",
        "Attempt history ({{ ext.attempts.length }})",
    )
    missing_bindings = [b for b in required_dynamic_bindings if b not in doc_page_ts]
    if missing_bindings:
        raise RuntimeError(f"Missing expected template binding(s) in document-page.ts: {missing_bindings}")

    return {
        "static_testids_verified": len(required_static_testids),
        "dynamic_template_bindings_verified": len(required_dynamic_bindings),
    }


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
        "schema": "eledgercare.f2-reviewer-runtime-release/2",
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
        "lease_id": "WP-0006-reviewer-runtime-20261116T220000Z",
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


class ReviewerExpectationReconciliationValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now_utc = datetime(2026, 11, 16, 22, 5, 0, tzinfo=timezone.utc)
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
            [sys.executable, "-B", str(HELPERS_DIR / "run_f2_reviewer_runtime_v2.py"), "--dry-run-validate"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--release-commit", proc.stderr)

    def test_02_cli_rejects_returned_author_releases_717a7689_and_e2847199(self) -> None:
        for auth_sha, rel_p in (
            ("717a768994bbbabf75b8ee96b3b1aadca1bc5df3", "docs/coordination/WP-0006/releases/author-runtime.json"),
            ("e28471997f425b0e074f65432dccc3abf2116490", "docs/coordination/WP-0006/releases/author-corrected-runtime.json"),
        ):
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(HELPERS_DIR / "run_f2_reviewer_runtime_v2.py"),
                    "--dry-run-validate",
                    "--release-commit",
                    auth_sha,
                    "--release-path",
                    rel_p,
                ],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("historical/returned/preparation-only", proc.stderr)

    def test_03_cli_rejects_preparation_only_0e16cfd4_35e2f44d_and_6dec634c_authorities(self) -> None:
        for prep_sha in (
            "6dec634c81a4b2cbc1b492541697958cc0f76232",
            "0e16cfd473b1dab3b6109c6fba8e7425e91c4ae5",
            "35e2f44d788a99ad1b2d10d1af95536cf1d1981a",
            "2ce3366d6aada92068088090bb026d4579b20e61",
        ):
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(HELPERS_DIR / "run_f2_reviewer_runtime_v2.py"),
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

    def test_04_accepts_valid_synthetic_future_reviewer_release_with_v1_ancestry(self) -> None:
        first_parent = rdrv.git_stdout(ROOT, ["rev-parse", "HEAD^1"]).lower()
        self.assertNotEqual(first_parent, rdrv.EXPECTED_SOURCE_COMMIT)
        out = self._validate(self.valid_rel)
        self.assertEqual(out["driver_version"], "v2")
        self.assertEqual(out["owner"], "eld-next-reviewer")
        self.assertEqual(out["executing_head"], self.actual_head)
        self.assertEqual(out["prior_prep_v1_checkpoint"], rdrv.EXPECTED_PRIOR_PREP_V1_CHECKPOINT)
        self.assertEqual(out["source_commit"], rdrv.EXPECTED_SOURCE_COMMIT)
        self.assertEqual(out["accepted_source_review"], rdrv.EXPECTED_ACCEPTED_SOURCE_REVIEW)
        self.assertEqual(
            out["immutable_trees_and_blobs"]["docs/reviews/WP-0006/eld-next-reviewer/runtime-preparation"],
            "70e22361b7eca2915b0e3da43975da7dec7f0c92",
        )
        self.assertEqual(out["expected_ui_status_labels"]["interrupted"], "Extraction interrupted")
        self.assertEqual(out["expected_ui_status_labels"]["completed"], "Completed (unreviewed)")
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
            "7280463accdf0ff9fb3a218299193eeff2ec9c9e",
            "882438d037fdb754df487c1d20a8bc958f81aeb2",
            "386d5c30809c3c04d6640d9433eb4263306ac126",
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
            "bc91d331979ed5fbcf4f38b3f359a1cf71cd9960",
        ):
            bad = copy.deepcopy(self.valid_rel)
            bad["accepted_source_review"] = bad_rev
            with self.assertRaisesRegex(rdrv.ReleaseValidationError, "source-review"):
                self._validate(bad)

    def test_10_rejects_old_source_commit_and_pre_v2_executing_heads(self) -> None:
        old_src = copy.deepcopy(self.valid_rel)
        old_src["source_commit"] = "0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978"
        with self.assertRaisesRegex(rdrv.ReleaseValidationError, "source_commit"):
            self._validate(old_src)

        for bad_head in (
            "82e8f732afbf038bfb5b6c560f1b1219aaa4e40f",
            "863fcd3a94188aa5a09b4e53f0f7192022950cbd",
            "bc91d331979ed5fbcf4f38b3f359a1cf71cd9960",
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
            "WP-0006-author-corrected-20261116T154140Z",
            "WP-0007-author-heldout-20261116T145544Z",
            "WP-0007-reviewer-dev-20261116T160924Z",
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
        tmp_parent = ROOT / ".scratch" / "reviewer-expectation-reconciliation" / "unit-tmp"
        tmp_parent.mkdir(parents=True, exist_ok=True)
        td = Path(tempfile.mkdtemp(prefix="rev-rt2-", dir=str(tmp_parent)))
        try:
            absent = td / "reviewer-absent"
            self.assertEqual(rdrv.ensure_clean_reviewer_runtime_root(absent, create_if_missing=False), [])
            self.assertFalse(absent.exists())

            dirty = td / "reviewer-dirty"
            (dirty / "runs" / "attempt-stale").mkdir(parents=True)
            with self.assertRaisesRegex(RuntimeError, "refusing mutable reuse"):
                rdrv.ensure_clean_reviewer_runtime_root(dirty, create_if_missing=False)
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_16_safe_evidence_packager_blocks_secrets_holdouts_and_all_immutable_dirs(self) -> None:
        tmp_parent = ROOT / ".scratch" / "reviewer-expectation-reconciliation" / "unit-tmp"
        tmp_parent.mkdir(parents=True, exist_ok=True)
        td = Path(tempfile.mkdtemp(prefix="rev-pkg2-", dir=str(tmp_parent)))
        try:
            fake_repo = td / "fake_repo"
            src_scratch = td / "scratch_in"
            src_scratch.mkdir(parents=True)
            (src_scratch / "trial-summary-reviewer-v2.json").write_bytes(b'{"test_fixture": true, "ok": 1}\n')

            for protected_dir in (
                "source-reconciliation",
                "runtime-preparation",
                "runtime-expectation-reconciliation",
            ):
                imm_dest = fake_repo / "docs" / "reviews" / "WP-0006" / "eld-next-reviewer" / protected_dir
                with self.assertRaisesRegex(rdrv.ReleaseValidationError, "immutable"):
                    rdrv.package_runtime_evidence(src_scratch, imm_dest, root=fake_repo)

            ok_dest = fake_repo / "docs" / "reviews" / "WP-0006" / "eld-next-reviewer" / "runtime-execution"
            inv = rdrv.package_runtime_evidence(src_scratch, ok_dest, root=fake_repo, extra_secrets=["SUPER_SECRET_PW"])
            self.assertEqual(inv["file_count"], 1)
            self.assertTrue((ok_dest / ".gitattributes").is_file())

            (src_scratch / "leak.log").write_bytes(b"conn=SUPER_SECRET_PW\n")
            with self.assertRaisesRegex(rdrv.ReleaseValidationError, "Secret value detected"):
                rdrv.package_runtime_evidence(
                    src_scratch,
                    fake_repo / "docs" / "reviews" / "WP-0006" / "eld-next-reviewer" / "runtime-execution-2",
                    root=fake_repo,
                    extra_secrets=["SUPER_SECRET_PW"],
                )
            (src_scratch / "leak.log").unlink()

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

    def test_18_recognizes_real_author_v2_gpu_evidence_commit_and_extracts_digests_readonly(self) -> None:
        real_ev = copy.deepcopy(self.valid_rel)
        real_ev["author_runtime_evidence"] = rdrv.AUTHOR_V2_GPU_EVIDENCE_COMMIT
        out = self._validate(real_ev)
        self.assertEqual(out["author_runtime_evidence_commit"], rdrv.AUTHOR_V2_GPU_EVIDENCE_COMMIT)

        digests = rdrv.try_extract_author_published_raw_shas(ROOT, rdrv.AUTHOR_V2_GPU_EVIDENCE_COMMIT)
        self.assertEqual(
            digests["author_f01_1p_raw_sha256"],
            "7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95",
        )
        self.assertEqual(
            digests["author_f07_3p_raw_sha256"],
            "c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639",
        )
        self.assertEqual(digests["author_f01_retry_raw_sha256"], digests["author_f01_1p_raw_sha256"])

    def test_19_build_ui_document_spec_binds_interrupted_and_completed_attempts_and_rejects_invalid_history(self) -> None:
        sub = {"expected_sha256": "a" * 64, "expected_byte_length": 12345}
        comp_2att = {
            "document_id": "01a1e500-0000-7000-8000-000000000003",
            "winning_attempt_id": "01a1e512-0000-7000-8000-000000000002",
            "db_result": {
                "result_id": "01a1e520-0000-7000-8000-000000000099",
                "raw_output_byte_length": 1574,
                "raw_output_sha256": "b" * 64,
            },
            "db_attempts": [
                {
                    "attempt_number": 1,
                    "attempt_id": "01a1e511-0000-7000-8000-000000000001",
                    "status": "interrupted",
                    "phase": "interrupted",
                },
                {
                    "attempt_number": 2,
                    "attempt_id": "01a1e512-0000-7000-8000-000000000002",
                    "status": "completed",
                    "phase": "completed",
                },
            ],
        }
        spec = rdrv.build_ui_document_spec(
            label="TEST_FIXTURE_ONLY Doc 3 interrupted+completed",
            submission=sub,
            completion=comp_2att,
            expected_pages=1,
        )
        self.assertEqual(len(spec["expectedAttempts"]), 2)
        self.assertEqual(
            spec["expectedAttempts"][0],
            {
                "attemptNumber": 1,
                "attemptId": "01a1e511-0000-7000-8000-000000000001",
                "apiStatus": "interrupted",
                "expectedUiStatusLabel": "Extraction interrupted",
                "expectedPhase": "interrupted",
            },
        )
        self.assertEqual(
            spec["expectedAttempts"][1],
            {
                "attemptNumber": 2,
                "attemptId": "01a1e512-0000-7000-8000-000000000002",
                "apiStatus": "completed",
                "expectedUiStatusLabel": "Completed (unreviewed)",
                "expectedPhase": "completed",
            },
        )

        # Rejects non-sequential attempt numbers or wrong winning attempt ID
        bad_seq = copy.deepcopy(comp_2att)
        bad_seq["db_attempts"][1]["attempt_number"] = 3
        with self.assertRaisesRegex(ValueError, "Non-sequential"):
            rdrv.build_ui_document_spec(label="bad", submission=sub, completion=bad_seq, expected_pages=1)

        bad_win = copy.deepcopy(comp_2att)
        bad_win["winning_attempt_id"] = "01a1e511-0000-7000-8000-000000000001"
        with self.assertRaisesRegex(ValueError, "winning completed attempt"):
            rdrv.build_ui_document_spec(label="bad", submission=sub, completion=bad_win, expected_pages=1)


def check_ast_ui_source_and_digests() -> tuple[int, str, dict[str, str], dict]:
    buf = io.StringIO()
    for py_file in (HELPERS_DIR / "run_f2_reviewer_runtime_v2.py", SCRIPT_PATH):
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

    drv_src = (HELPERS_DIR / "run_f2_reviewer_runtime_v2.py").read_text(encoding="utf-8")
    drv_tree = ast.parse(drv_src, filename=str(HELPERS_DIR / "run_f2_reviewer_runtime_v2.py"))
    docstring_ids: set[int] = set()
    for parent in ast.walk(drv_tree):
        if isinstance(parent, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and parent.body:
            first_stmt = parent.body[0]
            if (
                isinstance(first_stmt, ast.Expr)
                and isinstance(first_stmt.value, ast.Constant)
                and isinstance(first_stmt.value.value, str)
            ):
                docstring_ids.add(id(first_stmt.value))
    for node in ast.walk(drv_tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstring_ids:
            if "HEAD~1" in node.value:
                raise RuntimeError("Reviewer v2 driver executable string constant assumes immediate-parent HEAD~1!")
    buf.write("[PASS] Confirmed zero immediate-parent HEAD~1 assumptions in executable AST of run_f2_reviewer_runtime_v2.py\n")

    parsed_labels = parse_accepted_ui_status_labels(ROOT)
    if parsed_labels != rdrv.EXPECTED_UI_STATUS_LABELS:
        raise RuntimeError(
            f"statusLabels in web/src/app/intake/receipt.ts ({parsed_labels}) != "
            f"rdrv.EXPECTED_UI_STATUS_LABELS ({rdrv.EXPECTED_UI_STATUS_LABELS})"
        )
    for k, v in parsed_labels.items():
        buf.write(f"[PASS] Accepted UI receipt.ts statusLabels[{k!r}] == {v!r}\n")

    template_audit = audit_document_page_template_selectors(ROOT)
    buf.write(
        f"[PASS] Audited web/src/app/intake/document-page.ts: "
        f"{template_audit['static_testids_verified']} static data-testids & "
        f"{template_audit['dynamic_template_bindings_verified']} dynamic attempt/result bindings verified\n"
    )

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
        raise RuntimeError("Canonical /004 report unexpectedly exists during UI expectation reconciliation!")
    buf.write(f"[PASS] Confirmed canonical {rdrv.CANONICAL_REVIEWER_004_PATH} remains held (absent)\n")

    if rdrv.EXPECTED_REVIEWER_RUNTIME_ROOT.exists():
        raise RuntimeError(f"External reviewer runtime root unexpectedly exists: {rdrv.EXPECTED_REVIEWER_RUNTIME_ROOT}")
    buf.write(f"[PASS] Confirmed external reviewer runtime root absent: {rdrv.EXPECTED_REVIEWER_RUNTIME_ROOT}\n")

    return 0, buf.getvalue(), parsed_labels, template_audit


def run_node_ui_expectation_deterministic_suite(
    out_dir: Path,
    parsed_receipt_labels: dict[str, str],
) -> tuple[int, str, int]:
    """Executes node --check plus 12 deterministic Node ESM tests against verify_ui_reviewer_real_results_v2.mjs."""
    mjs_path = HELPERS_DIR / "verify_ui_reviewer_real_results_v2.mjs"
    chk = subprocess.run(
        ["node", "--check", str(mjs_path)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    if chk.returncode != 0:
        raise RuntimeError(f"node --check failed:\n{chk.stdout}{chk.stderr}")

    raw_1p = b"SYNTHETIC_TEST_FIXTURE_ONLY_1P_RAW_UTF8\n"
    raw_1p_sha = hashlib.sha256(raw_1p).hexdigest()
    raw_3p = b"SYNTHETIC_TEST_FIXTURE_ONLY_3P_RAW_UTF8\n"
    raw_3p_sha = hashlib.sha256(raw_3p).hexdigest()
    orig_1p_sha = rdrv.EXPECTED_PINNED_DIGESTS["syn_wo_01_sha256"]
    orig_3p_sha = rdrv.EXPECTED_PINNED_DIGESTS["syn_mp_01_sha256"]

    spec_1p = rdrv.build_ui_document_spec(
        label="TEST_FIXTURE_ONLY 1p completed",
        submission={"expected_sha256": orig_1p_sha, "expected_byte_length": 44253},
        completion={
            "document_id": "01a1e500-0000-7000-8000-000000000001",
            "winning_attempt_id": "01a1e510-0000-7000-8000-000000000001",
            "db_result": {
                "result_id": "01a1e520-0000-7000-8000-000000000001",
                "raw_output_byte_length": len(raw_1p),
                "raw_output_sha256": raw_1p_sha,
            },
            "db_attempts": [
                {
                    "attempt_number": 1,
                    "attempt_id": "01a1e510-0000-7000-8000-000000000001",
                    "status": "completed",
                    "phase": "completed",
                }
            ],
        },
        expected_pages=1,
    )

    spec_3p = rdrv.build_ui_document_spec(
        label="TEST_FIXTURE_ONLY 3p completed",
        submission={"expected_sha256": orig_3p_sha, "expected_byte_length": 4416},
        completion={
            "document_id": "01a1e500-0000-7000-8000-000000000002",
            "winning_attempt_id": "01a1e510-0000-7000-8000-000000000002",
            "db_result": {
                "result_id": "01a1e520-0000-7000-8000-000000000002",
                "raw_output_byte_length": len(raw_3p),
                "raw_output_sha256": raw_3p_sha,
            },
            "db_attempts": [
                {
                    "attempt_number": 1,
                    "attempt_id": "01a1e510-0000-7000-8000-000000000002",
                    "status": "completed",
                    "phase": "completed",
                }
            ],
        },
        expected_pages=3,
    )

    spec_2att = rdrv.build_ui_document_spec(
        label="TEST_FIXTURE_ONLY 1p interrupted + completed retry",
        submission={"expected_sha256": orig_1p_sha, "expected_byte_length": 44253},
        completion={
            "document_id": "01a1e500-0000-7000-8000-000000000003",
            "winning_attempt_id": "01a1e512-0000-7000-8000-000000000002",
            "db_result": {
                "result_id": "01a1e520-0000-7000-8000-000000000003",
                "raw_output_byte_length": len(raw_1p),
                "raw_output_sha256": raw_1p_sha,
            },
            "db_attempts": [
                {
                    "attempt_number": 1,
                    "attempt_id": "01a1e511-0000-7000-8000-000000000001",
                    "status": "interrupted",
                    "phase": "interrupted",
                },
                {
                    "attempt_number": 2,
                    "attempt_id": "01a1e512-0000-7000-8000-000000000002",
                    "status": "completed",
                    "phase": "completed",
                },
            ],
        },
        expected_pages=1,
    )

    fixture_payload_path = out_dir / "unit-tmp" / "ui-deterministic-fixtures.json"
    rdrv.write_json_lf(
        fixture_payload_path,
        {
            "_synthetic_label": "TEST_FIXTURE_ONLY_UI_EXPECTATION_RECONCILIATION",
            "helper_url": mjs_path.as_uri(),
            "parsed_receipt_labels": parsed_receipt_labels,
            "spec_1p": spec_1p,
            "spec_3p": spec_3p,
            "spec_2att": spec_2att,
        },
    )

    node_test_script = r"""
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const payload = JSON.parse(readFileSync(process.argv[1], 'utf8'));
const mod = await import(payload.helper_url);
const {
  EXPECTED_UI_STATUS_LABELS,
  EXPECTED_MODEL_CHECKPOINT_TEXT,
  EXPECTED_UNREVIEWED_STRONG_TEXT,
  validateDocumentUiObservation,
} = mod;

function clone(x) {
  return JSON.parse(JSON.stringify(x));
}

function makeMatchingApiAndDom(spec, expectOcrDisabled) {
  const jobId = `job-${spec.documentId}`;
  const apiAttempts = spec.expectedAttempts.map((a, idx) => ({
    attemptId: a.attemptId,
    attemptNumber: a.attemptNumber,
    status: a.apiStatus,
    phase: a.expectedPhase,
    startedAtUtc: `2026-11-16T15:5${idx}:00.123456+00:00`,
    lastHeartbeatAtUtc: `2026-11-16T15:5${idx}:20.123456+00:00`,
    endedAtUtc: `2026-11-16T15:5${idx}:45.654321+00:00`,
    failureCode: a.apiStatus === 'interrupted' ? 'supervisor_interrupted' : null,
    failureMessage: a.apiStatus === 'interrupted' ? 'Interrupted' : null,
  }));
  const api = {
    documentId: spec.documentId,
    jobId,
    status: 'completed',
    workerEnabled: !expectOcrDisabled,
    canRequestExtraction: false,
    canRetryExtraction: false,
    attempts: apiAttempts,
    result: {
      resultId: spec.expectedResultId,
      attemptId: spec.expectedWinningAttemptId,
      reviewStatus: 'unreviewed',
      rawByteLength: spec.expectedRawByteLength,
      rawSha256: spec.expectedRawSha256,
    },
  };
  const pageWord = spec.expectedPages === 1 ? 'page' : 'pages';
  const dom = {
    documentIdText: spec.documentId,
    jobIdText: jobId,
    statusText: payload.parsed_receipt_labels.completed,
    documentPageCountText: String(spec.expectedPages),
    documentByteLengthText: `${spec.expectedOriginalBytes} bytes`,
    documentSha256Text: spec.expectedOriginalSha256,
    unsupportedCount: 0,
    unavailableCount: 0,
    activePanelCount: 0,
    failurePanelCount: 0,
    actionButtonsCount: 0,
    unreviewedBannerStrongText: EXPECTED_UNREVIEWED_STRONG_TEXT,
    resultIdText: spec.expectedResultId,
    resultAttemptIdText: spec.expectedWinningAttemptId,
    modelText: EXPECTED_MODEL_CHECKPOINT_TEXT,
    rendererText: 'pypdfium2==5.15.2 / pdfium=159.0.8149.0 (300 DPI RGB)',
    rawByteLengthText: `${spec.expectedRawByteLength} bytes (${spec.expectedPages} ${pageWord})`,
    uiRawSha256: spec.expectedRawSha256,
    pageHeadings: Array.from({ length: spec.expectedPages }, (_, i) => `Page ${i + 1} of ${spec.expectedPages}`),
    forbiddenDomTagCount: 0,
    inlineEventAttrCount: 0,
    renderedTableCount: 1,
    renderedBlockCount: 4,
    rawPreElementSha256: spec.expectedRawSha256,
    attemptHistorySummaryText: `Attempt history (${apiAttempts.length})`,
    attemptRows: apiAttempts.map((att) => ({
      testId: `attempt-row-${att.attemptNumber}`,
      codeAttemptId: att.attemptId,
      cells: [
        String(att.attemptNumber),
        att.attemptId,
        payload.parsed_receipt_labels[att.status],
        att.phase,
        att.startedAtUtc,
        att.endedAtUtc,
      ],
    })),
    downloadedFilename: `${spec.documentId}.pdf`,
    downloadedByteLength: spec.expectedOriginalBytes,
    downloadedSha256: spec.expectedOriginalSha256,
  };
  return { api, dom };
}

const logs = [];
let passed = 0;

// Case 01: Exact statusLabels parity with accepted receipt.ts
assert.deepEqual(EXPECTED_UI_STATUS_LABELS, payload.parsed_receipt_labels);
assert.equal(EXPECTED_UI_STATUS_LABELS.interrupted, 'Extraction interrupted');
assert.equal(EXPECTED_UI_STATUS_LABELS.completed, 'Completed (unreviewed)');
passed++;
logs.push('[PASS] case_01_status_labels_match_accepted_receipt_ts_6_of_6');

// Case 02: 1-page single completed attempt (OCR enabled)
{
  const { api, dom } = makeMatchingApiAndDom(payload.spec_1p, false);
  const res = validateDocumentUiObservation(payload.spec_1p, api, dom, false);
  assert.equal(res.attemptHistoryRowCount, 1);
  assert.equal(res.verifiedAttempts[0].uiStatusLabel, 'Completed (unreviewed)');
  passed++;
  logs.push('[PASS] case_02_single_page_completed_1_attempt_passes');
}

// Case 03: 3-page completed attempt with ordered pages 1..3 (OCR disabled reopen)
{
  const { api, dom } = makeMatchingApiAndDom(payload.spec_3p, true);
  const res = validateDocumentUiObservation(payload.spec_3p, api, dom, true);
  assert.deepEqual(res.pageHeadings, ['Page 1 of 3', 'Page 2 of 3', 'Page 3 of 3']);
  assert.equal(res.expectOcrDisabled, true);
  passed++;
  logs.push('[PASS] case_03_three_page_completed_reopen_ocr_disabled_passes');
}

// Case 04: 2-attempt interrupted + completed history tied to exact attemptIds, numbers, and API statuses
{
  const { api, dom } = makeMatchingApiAndDom(payload.spec_2att, true);
  const res = validateDocumentUiObservation(payload.spec_2att, api, dom, true);
  assert.equal(res.attemptHistoryRowCount, 2);
  assert.equal(res.verifiedAttempts[0].attemptNumber, 1);
  assert.equal(res.verifiedAttempts[0].attemptId, '01a1e511-0000-7000-8000-000000000001');
  assert.equal(res.verifiedAttempts[0].apiStatus, 'interrupted');
  assert.equal(res.verifiedAttempts[0].uiStatusLabel, 'Extraction interrupted');
  assert.equal(res.verifiedAttempts[1].attemptNumber, 2);
  assert.equal(res.verifiedAttempts[1].attemptId, '01a1e512-0000-7000-8000-000000000002');
  assert.equal(res.verifiedAttempts[1].apiStatus, 'completed');
  assert.equal(res.verifiedAttempts[1].uiStatusLabel, 'Completed (unreviewed)');
  assert.equal(res.winningAttemptId, '01a1e512-0000-7000-8000-000000000002');
  passed++;
  logs.push('[PASS] case_04_two_attempt_interrupted_plus_completed_history_passes');
}

// Case 05: Stale v1/author 'Interrupted' substring spec fails closed
{
  const badSpec = clone(payload.spec_2att);
  badSpec.expectedAttempts[0].expectedUiStatusLabel = 'Interrupted';
  const { api, dom } = makeMatchingApiAndDom(payload.spec_2att, true);
  assert.throws(() => validateDocumentUiObservation(badSpec, api, dom, true), /Invalid spec expectedUiStatusLabel/);
  passed++;
  logs.push('[PASS] case_05_stale_capital_Interrupted_spec_expectation_rejected');
}

// Case 06: Wrong DOM cell label ('Interrupted' instead of 'Extraction interrupted') fails closed
{
  const { api, dom } = makeMatchingApiAndDom(payload.spec_2att, true);
  dom.attemptRows[0].cells[2] = 'Interrupted';
  assert.throws(() => validateDocumentUiObservation(payload.spec_2att, api, dom, true), /UI status label 'Interrupted' != 'Extraction interrupted'/);
  passed++;
  logs.push('[PASS] case_06_wrong_dom_status_cell_label_rejected');
}

// Case 07: Attempt ID mismatch between API and DOM row <code> cell fails closed
{
  const { api, dom } = makeMatchingApiAndDom(payload.spec_2att, true);
  dom.attemptRows[0].cells[1] = '01a1e512-0000-7000-8000-000000000002';
  assert.throws(() => validateDocumentUiObservation(payload.spec_2att, api, dom, true), /attemptId cell/);
  passed++;
  logs.push('[PASS] case_07_attempt_id_swap_or_mismatch_rejected');
}

// Case 08: Underlying API status drift ('failed' while spec/UI says 'interrupted') fails closed
{
  const { api, dom } = makeMatchingApiAndDom(payload.spec_2att, true);
  api.attempts[0].status = 'failed';
  assert.throws(() => validateDocumentUiObservation(payload.spec_2att, api, dom, true), /API attempt #1 mismatch/);
  passed++;
  logs.push('[PASS] case_08_underlying_api_status_drift_rejected');
}

// Case 09: result-attempt-id pointing to interrupted Attempt #1 instead of completed Attempt #2 fails closed
{
  const { api, dom } = makeMatchingApiAndDom(payload.spec_2att, true);
  dom.resultAttemptIdText = '01a1e511-0000-7000-8000-000000000001';
  assert.throws(() => validateDocumentUiObservation(payload.spec_2att, api, dom, true), /result-attempt-id/);
  passed++;
  logs.push('[PASS] case_09_wrong_winning_result_attempt_id_rejected');
}

// Case 10: Visible request/refresh/retry button or workerEnabled=true when OCR disabled fails closed
{
  const { api, dom } = makeMatchingApiAndDom(payload.spec_2att, true);
  dom.actionButtonsCount = 1;
  assert.throws(() => validateDocumentUiObservation(payload.spec_2att, api, dom, true), /action button/);
  dom.actionButtonsCount = 0;
  api.workerEnabled = true;
  assert.throws(() => validateDocumentUiObservation(payload.spec_2att, api, dom, true), /workerEnabled=false/);
  passed++;
  logs.push('[PASS] case_10_unexpected_action_button_or_worker_enabled_rejected');
}

// Case 11: Unsafe DOM tag or inline event attribute inside extraction-result fails closed
{
  const { api, dom } = makeMatchingApiAndDom(payload.spec_2att, true);
  dom.forbiddenDomTagCount = 1;
  assert.throws(() => validateDocumentUiObservation(payload.spec_2att, api, dom, true), /Unsafe DOM/);
  dom.forbiddenDomTagCount = 0;
  dom.inlineEventAttrCount = 1;
  assert.throws(() => validateDocumentUiObservation(payload.spec_2att, api, dom, true), /Unsafe DOM/);
  passed++;
  logs.push('[PASS] case_11_unsafe_dom_tag_or_inline_handler_rejected');
}

// Case 12: Raw <pre> UTF-8 SHA-256 or downloaded original PDF SHA-256 mismatch fails closed
{
  const { api, dom } = makeMatchingApiAndDom(payload.spec_2att, true);
  dom.rawPreElementSha256 = '0'.repeat(64);
  assert.throws(() => validateDocumentUiObservation(payload.spec_2att, api, dom, true), /Rendered raw-text SHA-256/);
  dom.rawPreElementSha256 = payload.spec_2att.expectedRawSha256;
  dom.downloadedSha256 = 'f'.repeat(64);
  assert.throws(() => validateDocumentUiObservation(payload.spec_2att, api, dom, true), /Downloaded original mismatch/);
  passed++;
  logs.push('[PASS] case_12_raw_pre_or_original_download_sha256_mismatch_rejected');
}

console.log(`NODE_UI_DETERMINISTIC_CASES_PASSED=${passed}`);
for (const ln of logs) {
  console.log(ln);
}
"""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", node_test_script, str(fixture_payload_path)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    combined = (
        f"$ node --check {mjs_path.relative_to(ROOT).as_posix()}\n"
        f"exit_code={chk.returncode}\n"
        f"$ node --input-type=module <12_deterministic_ui_expectation_cases>\n"
        f"exit_code={proc.returncode}\n"
        f"{proc.stdout}{proc.stderr}"
    ).replace("\r\n", "\n")
    if proc.returncode != 0:
        raise RuntimeError(f"Node UI deterministic expectation suite failed:\n{combined}")
    return 0, combined, 12


def main() -> int:
    head_sha = rdrv.git_stdout(ROOT, ["rev-parse", "HEAD"]).lower()
    porcelain = rdrv.git_stdout(ROOT, ["status", "--porcelain"])
    if porcelain != "":
        raise RuntimeError(f"Freeze violation: working tree must be clean before validation, got: {porcelain!r}")

    if rdrv.EXPECTED_REVIEWER_RUNTIME_ROOT.exists():
        raise RuntimeError(f"External reviewer runtime root must not exist: {rdrv.EXPECTED_REVIEWER_RUNTIME_ROOT}")

    out_dir = ROOT / ".scratch" / "reviewer-expectation-reconciliation"
    logs_dir = out_dir / "logs"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    ports_before = {str(p): rdrv.check_port_bound(p) for p in (5290, 4310, 55435)}
    if any(ports_before.values()):
        raise RuntimeError(f"Owned reviewer ports bound before CPU validation: {ports_before}")

    steps_summary: list[dict] = []

    # Step 01: Python compile, AST guard, UI source audit, digest & Git tree/blob verification
    t0 = time.perf_counter()
    rc1, out1, parsed_labels, template_audit = check_ast_ui_source_and_digests()
    dur1 = round((time.perf_counter() - t0) * 1000)
    raw1 = out1.replace("\r\n", "\n").encode("utf-8")
    (logs_dir / "01-python-compile-ast-and-ui-source-audit.log").write_bytes(raw1)
    steps_summary.append({
        "step": "01-python-compile-ast-and-ui-source-audit",
        "exit_code": rc1,
        "duration_ms": dur1,
        "log_file": "logs/01-python-compile-ast-and-ui-source-audit.log",
        "byte_length": len(raw1),
        "raw_file_sha256": rdrv.sha256_bytes(raw1),
        "lf_normalized_sha256": rdrv.sha256_bytes(raw1),
    })

    # Step 02: Node syntax check + 12 deterministic UI expectation & interrupted+completed history tests
    t0 = time.perf_counter()
    rc2, out2, node_cases = run_node_ui_expectation_deterministic_suite(out_dir, parsed_labels)
    dur2 = round((time.perf_counter() - t0) * 1000)
    raw2 = out2.encode("utf-8")
    (logs_dir / "02-node-ui-expectation-deterministic-tests.log").write_bytes(raw2)
    steps_summary.append({
        "step": "02-node-ui-expectation-deterministic-tests",
        "exit_code": rc2,
        "deterministic_cases_passed": node_cases,
        "duration_ms": dur2,
        "log_file": "logs/02-node-ui-expectation-deterministic-tests.log",
        "byte_length": len(raw2),
        "raw_file_sha256": rdrv.sha256_bytes(raw2),
        "lf_normalized_sha256": rdrv.sha256_bytes(raw2),
    })

    # Step 03: Focused unit & subprocess v2 release-validator tests (19 test methods)
    t0 = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReviewerExpectationReconciliationValidationTests)
    u_buf = io.StringIO()
    runner = unittest.TextTestRunner(stream=u_buf, verbosity=2)
    u_res = runner.run(suite)
    dur3 = round((time.perf_counter() - t0) * 1000)
    raw3 = u_buf.getvalue().replace("\r\n", "\n").encode("utf-8")
    (logs_dir / "03-reviewer-v2-release-validator-tests.log").write_bytes(raw3)
    rc3 = 0 if u_res.wasSuccessful() else 1
    steps_summary.append({
        "step": "03-reviewer-v2-release-validator-tests",
        "exit_code": rc3,
        "tests_run": u_res.testsRun,
        "failures": len(u_res.failures),
        "errors": len(u_res.errors),
        "duration_ms": dur3,
        "log_file": "logs/03-reviewer-v2-release-validator-tests.log",
        "byte_length": len(raw3),
        "raw_file_sha256": rdrv.sha256_bytes(raw3),
        "lf_normalized_sha256": rdrv.sha256_bytes(raw3),
    })
    if rc3 != 0:
        raise RuntimeError(f"Reviewer v2 release validator unit tests failed:\n{u_buf.getvalue()}")

    shutil.rmtree(out_dir / "unit-tmp", ignore_errors=True)
    for pyc_dir in HELPERS_DIR.rglob("__pycache__"):
        shutil.rmtree(pyc_dir, ignore_errors=True)

    ports_after = {str(p): rdrv.check_port_bound(p) for p in (5290, 4310, 55435)}
    porcelain_after = rdrv.git_stdout(ROOT, ["status", "--porcelain"])
    external_root_after = rdrv.EXPECTED_REVIEWER_RUNTIME_ROOT.exists()
    if any(ports_after.values()) or porcelain_after != "" or external_root_after:
        raise RuntimeError(
            f"Post-validation invariant violated: ports={ports_after}, porcelain={porcelain_after!r}, ext_root={external_root_after}"
        )

    summary = {
        "schema": "eledgercare.wp-0006.reviewer-expectation-reconciliation-summary/1",
        "reviewer": rdrv.EXPECTED_OWNER,
        "driver_version": "v2",
        "conversation_id": rdrv.EXPECTED_CONVERSATION_ID,
        "model": rdrv.EXPECTED_MODEL,
        "effort": rdrv.EXPECTED_EFFORT,
        "validated_utc": rdrv.utc_now(),
        "reconciliation_authority_commit": "6dec634c81a4b2cbc1b492541697958cc0f76232",
        "clean_start_prep_v1_checkpoint": rdrv.EXPECTED_PRIOR_PREP_V1_CHECKPOINT,
        "preserved_prep_v1_helper_commit": rdrv.EXPECTED_PRIOR_PREP_V1_HELPER,
        "accepted_source_review_commit": rdrv.EXPECTED_ACCEPTED_SOURCE_REVIEW,
        "accepted_design_review_002": rdrv.EXPECTED_ACCEPTED_DESIGN_REVIEW,
        "protected_source_commit": rdrv.EXPECTED_SOURCE_COMMIT,
        "observed_author_v2_gpu_evidence_commit": rdrv.AUTHOR_V2_GPU_EVIDENCE_COMMIT,
        "frozen_reviewer_v2_helper_commit": head_sha,
        "canonical_004_status": "held_pending_released_independent_runtime_and_author_003_disposition",
        "git_clean_before_and_after": porcelain_after == "",
        "reviewer_ports_bound_before": ports_before,
        "reviewer_ports_bound_after": ports_after,
        "external_reviewer_runtime_root_exists_before": False,
        "external_reviewer_runtime_root_exists_after": external_root_after,
        "ml_or_cuda_modules_imported": [],
        "gpu_queries_executed": 0,
        "services_or_databases_started": False,
        "test_data_labeling": "TEST_FIXTURE_ONLY synthetic release & UI DOM fixtures; zero holdout access",
        "verified_ui_status_labels": parsed_labels,
        "document_page_template_audit": template_audit,
        "pinned_digests_verified": rdrv.compute_local_worktree_digests(ROOT),
        "product_tree_objects_verified": dict(rdrv.EXPECTED_PRODUCT_TREES),
        "immutable_trees_and_blobs_verified": dict(rdrv.EXPECTED_IMMUTABLE_TREES_AND_BLOBS),
        "committed_helpers_verified": rdrv.verify_committed_helpers_unchanged(ROOT, head_sha),
        "steps": steps_summary,
        "total_node_ui_deterministic_cases_passed": node_cases,
        "total_python_unittest_methods_passed": u_res.testsRun,
    }
    rdrv.write_json_lf(out_dir / "validation-summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
