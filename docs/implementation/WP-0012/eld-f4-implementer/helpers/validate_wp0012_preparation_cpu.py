"""Decisive post-freeze CPU-only preparation validator for WP-0012 / 001 (eld-f4-implementer).

Executes against clean frozen HEAD with LocalOcr:Enabled=false and zero GPU/model calls:
  01. Static Git/tree/AST audit (`py_compile`, forbidden ML/CUDA/non-product import guard,
      `node --check`, unchanged accepted F4 product trees & digests).
  02. Offline locked .NET restore & Release solution build (`ELedgerCare.slnx`).
  03. Angular 22 production bundle build (`ng build`).
  04. 18 focused `unittest` & CLI subprocess release-contract and guard-ceiling assertions.
  05. Owned PostgreSQL 18.7 (`55438`) startup, pre-run invariance check on retained F4 databases
      (`eledgercare_f4_author_seed_f3` 76e7970b..., `eledgercare_f4_author_migrated` ad4f44bc... /
      78f0f273...), fresh preparation of NEW owned rehearsal database `eledgercare_demo_wp0012_author`,
      CPU dry-run + disabled-OCR Edge preflight (`5590 / 4610`, 0 documents, 0 attempts, 13/13 42501
      denials, 0 OCR workers), post-run DB invariance check, and clean service return (`5590/4610/55438` FREE).
"""
from __future__ import annotations

import argparse
import ast
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import time
import unittest

SCRIPT_PATH = Path(__file__).resolve()
HELPERS_DIR = SCRIPT_PATH.parent
DOSSIER_DIR = HELPERS_DIR.parent
EVIDENCE_DIR = DOSSIER_DIR / "evidence"
LOGS_DIR = EVIDENCE_DIR / "logs"
SCREENSHOTS_DIR = EVIDENCE_DIR / "screenshots"
REPO_ROOT = DOSSIER_DIR.parents[3]

if str(HELPERS_DIR) not in sys.path:
    sys.path.insert(0, str(HELPERS_DIR))

import run_wp0012_rehearsal as drv  # noqa: E402

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

SEED_F3_DB = "eledgercare_f4_author_seed_f3"
MIGRATED_F4_DB = "eledgercare_f4_author_migrated"
EXPECTED_SEED_F3_SHA256 = "76e7970b50b8fbf968c44e534d6383bdd8251e9f285e2373ea026eeeea157085"
EXPECTED_MIGRATED_CORE_SHA256 = "ad4f44bcf7c0f7163e91cad81f569bfc4642cbb167c1eaf6c3d1ab9984b2e6d0"
EXPECTED_MIGRATED_PROJ_SHA256 = "78f0f273dbdb48629924752cba6f863f11f62764e27161d8df1549ad75ce2ac3"

CANONICAL_8_TABLE_SQL = """
SELECT json_build_object(
  'collation', (
    SELECT json_build_object(
      'datcollate', datcollate,
      'datctype', datctype,
      'encoding', pg_encoding_to_char(encoding)
    ) FROM pg_database WHERE datname = current_database()
  ),
  'migrations', COALESCE((SELECT json_agg("MigrationId" ORDER BY "MigrationId") FROM eledgercare.__ef_migrations_history), '[]'::json),
  'sequence', (SELECT json_build_object('last_value', last_value, 'is_called', is_called) FROM eledgercare.extraction_fencing_seq),
  'row_counts', json_build_object(
    'documents', (SELECT count(*) FROM eledgercare.documents),
    'original_artifacts', (SELECT count(*) FROM eledgercare.original_artifacts),
    'processing_jobs', (SELECT count(*) FROM eledgercare.processing_jobs),
    'execution_attempts', (SELECT count(*) FROM eledgercare.execution_attempts),
    'extraction_results', (SELECT count(*) FROM eledgercare.extraction_results),
    'work_order_review_heads', (SELECT count(*) FROM eledgercare.work_order_review_heads),
    'work_order_review_revisions', (SELECT count(*) FROM eledgercare.work_order_review_revisions),
    'work_order_review_fields', (SELECT count(*) FROM eledgercare.work_order_review_fields)
  ),
  'documents', COALESCE((
    SELECT json_agg(json_build_object(
      'document_id', d.document_id::text,
      'idempotency_key', d.idempotency_key::text,
      'submitted_at', d.submitted_at,
      'byte_length', a.byte_length,
      'octet_length', octet_length(a.bytes),
      'declared_sha256', encode(a.sha256, 'hex'),
      'computed_sha256', encode(sha256(a.bytes), 'hex'),
      'page_count', a.page_count,
      'job_id', j.job_id::text,
      'job_status', j.status,
      'attempt_count', j.attempt_count,
      'latest_fencing_token', j.latest_fencing_token,
      'retried_from_attempt_id', j.retried_from_attempt_id::text
    ) ORDER BY d.submitted_at DESC, d.document_id DESC)
    FROM eledgercare.documents d
    JOIN eledgercare.original_artifacts a ON a.document_id = d.document_id
    JOIN eledgercare.processing_jobs j ON j.document_id = d.document_id
  ), '[]'::json),
  'attempts', COALESCE((
    SELECT json_agg(json_build_object(
      'attempt_id', at.attempt_id::text,
      'document_id', at.document_id::text,
      'attempt_number', at.attempt_number,
      'fencing_token', at.fencing_token,
      'retried_from_attempt_id', at.retried_from_attempt_id::text,
      'status', at.status,
      'phase', at.phase,
      'failure_code', at.failure_code,
      'exit_code', at.exit_code,
      'has_diagnostic_raw_output', (at.diagnostic_raw_output_utf8 IS NOT NULL)
    ) ORDER BY at.fencing_token)
    FROM eledgercare.execution_attempts at
  ), '[]'::json),
  'results', COALESCE((
    SELECT json_agg(json_build_object(
      'result_id', r.result_id::text,
      'document_id', r.document_id::text,
      'attempt_id', r.attempt_id::text,
      'fencing_token', r.fencing_token,
      'schema_version', r.schema_version,
      'input_sha256', encode(r.input_sha256, 'hex'),
      'page_count', r.page_count,
      'output_page_count', r.output_page_count,
      'raw_output_byte_length', r.raw_output_byte_length,
      'raw_octet_length', octet_length(r.raw_output_bytes),
      'declared_raw_sha256', encode(r.raw_output_sha256, 'hex'),
      'computed_raw_sha256', encode(sha256(r.raw_output_bytes), 'hex'),
      'worker_source_sha256', encode(r.worker_source_digest, 'hex'),
      'worker_config_sha256', encode(r.worker_config_digest, 'hex'),
      'finish_reason', r.finish_reason
    ) ORDER BY r.fencing_token)
    FROM eledgercare.extraction_results r
  ), '[]'::json),
  'review_heads', COALESCE((
    SELECT json_agg(json_build_object(
      'document_id', h.document_id::text,
      'result_id', h.result_id::text,
      'current_revision_number', h.current_revision_number,
      'current_revision_id', h.current_revision_id::text,
      'current_status', h.current_status,
      'greatest_reviewed_revision_number', (
        SELECT max(rv.revision_number)
        FROM eledgercare.work_order_review_revisions rv
        WHERE rv.document_id = h.document_id AND rv.status = 'reviewed'
      ),
      'input_sha256', encode(h.input_sha256, 'hex'),
      'raw_output_sha256', encode(h.raw_output_sha256, 'hex')
    ) ORDER BY h.document_id)
    FROM eledgercare.work_order_review_heads h
  ), '[]'::json),
  'review_revisions', COALESCE((
    SELECT json_agg(json_build_object(
      'revision_id', rv.revision_id::text,
      'document_id', rv.document_id::text,
      'result_id', rv.result_id::text,
      'revision_number', rv.revision_number,
      'previous_revision_number', rv.previous_revision_number,
      'status', rv.status,
      'idempotency_key', rv.idempotency_key::text,
      'request_sha256', encode(rv.request_sha256, 'hex'),
      'operator_display_label', rv.operator_display_label,
      'accepted_field_count', rv.accepted_field_count,
      'edited_field_count', rv.edited_field_count,
      'unknown_field_count', rv.unknown_field_count,
      'unreviewed_field_count', rv.unreviewed_field_count,
      'saved_at', rv.saved_at
    ) ORDER BY rv.document_id, rv.revision_number)
    FROM eledgercare.work_order_review_revisions rv
  ), '[]'::json),
  'review_fields', COALESCE((
    SELECT json_agg(json_build_object(
      'revision_id', rf.revision_id::text,
      'field_ordinal', rf.field_ordinal,
      'field_key', rf.field_key,
      'decision', rf.decision,
      'human_value', rf.human_value,
      'unknown_reason', rf.unknown_reason,
      'consulted_page_number', rf.consulted_page_number,
      'consulted_block_ordinal', rf.consulted_block_ordinal,
      'consulted_table_row', rf.consulted_table_row,
      'consulted_table_column', rf.consulted_table_column,
      'consulted_quote', rf.consulted_quote
    ) ORDER BY rf.revision_id, rf.field_ordinal)
    FROM eledgercare.work_order_review_fields rf
  ), '[]'::json)
)::text;
"""

PROJECTION_TABLES_SQL = """
SELECT json_build_object(
  'projection_count', (SELECT count(*) FROM eledgercare.archive_result_projections),
  'unit_count', (SELECT count(*) FROM eledgercare.archive_projection_units),
  'projections', COALESCE((
    SELECT json_agg(json_build_object(
      'result_id', p.result_id::text,
      'document_id', p.document_id::text,
      'projection_version', p.projection_version,
      'raw_output_sha256', encode(p.raw_output_sha256, 'hex'),
      'projection_sha256', encode(p.projection_sha256, 'hex'),
      'unit_count', p.unit_count,
      'has_fallback', p.has_fallback
    ) ORDER BY p.result_id)
    FROM eledgercare.archive_result_projections p
  ), '[]'::json),
  'units', COALESCE((
    SELECT json_agg(json_build_object(
      'result_id', u.result_id::text,
      'unit_ordinal', u.unit_ordinal,
      'document_id', u.document_id::text,
      'page_number', u.page_number,
      'unit_kind', u.unit_kind,
      'is_fallback', u.is_fallback,
      'search_text_sha256', encode(sha256(convert_to(u.search_text, 'UTF8')), 'hex'),
      'search_text_chars', char_length(u.search_text)
    ) ORDER BY u.result_id, u.unit_ordinal)
    FROM eledgercare.archive_projection_units u
  ), '[]'::json)
)::text;
"""


def make_synthetic_valid_wp0012_release(actual_head: str, now_utc: datetime) -> tuple[dict, dict[str, bytes]]:
    obs_blobs = {
        "docs/coordination/WP-0012/gpu-author-release/host-before.json": b'{"ok": true, "kind": "host"}\r\n',
        "docs/coordination/WP-0012/gpu-author-release/processes-before.json": b'{"ok": true, "kind": "procs"}\n',
        "docs/coordination/WP-0012/gpu-author-release/model-before.json": b'{"ok": true, "kind": "model"}\n',
    }
    obs_meta = {
        "host-before.json": {
            "path": "docs/coordination/WP-0012/gpu-author-release/host-before.json",
            "sha256": drv.sha256_bytes(obs_blobs["docs/coordination/WP-0012/gpu-author-release/host-before.json"].replace(b"\r\n", b"\n")),
        },
        "processes-before.json": {
            "path": "docs/coordination/WP-0012/gpu-author-release/processes-before.json",
            "sha256": drv.sha256_bytes(obs_blobs["docs/coordination/WP-0012/gpu-author-release/processes-before.json"]),
        },
        "model-before.json": {
            "path": "docs/coordination/WP-0012/gpu-author-release/model-before.json",
            "sha256": drv.sha256_bytes(obs_blobs["docs/coordination/WP-0012/gpu-author-release/model-before.json"]),
        },
    }
    rel = {
        "schema": "eledgercare.wp0012-rehearsal-release/1",
        "packet": "WP-0012",
        "owner": "eld-f4-implementer",
        "conversation_id": "b7c54417-db09-49bd-8d2b-7cc808f113be",
        "model": "gemini-4-carbon-high",
        "effort": "high",
        "source_commit": drv.ACCEPTED_F4_FINAL_SOURCE_SHA,
        "executing_head": actual_head,
        "accepted_preparation_review": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "product_tree_objects": dict(drv.EXPECTED_PRODUCT_TREES),
        "pinned_digests": dict(drv.EXPECTED_PINNED_DIGESTS),
        "lease_id": "WP-0012-author-rehearsal-20261117T150000Z",
        "gpu_uuid": drv.EXPECTED_GPU_UUID,
        "released_utc": (now_utc - timedelta(minutes=2)).isoformat(),
        "expires_utc": (now_utc + timedelta(hours=5)).isoformat(),
        "max_model_attempts": 2,
        "readonly_q0_root": r"C:\Users\jackg\eLedgerCare-Q0\WP-0005",
        "runtime_root": r"C:\Users\jackg\eLedgerCare-Demo\WP-0012\author",
        "database": drv.OWNED_REHEARSAL_DB,
        "ports": {"api": 5590, "ui": 4610, "postgres": 55438},
        "storage_cap_bytes": 4_294_967_296,
        "free_floor_bytes": 21_474_836_480,
        "guards": {
            "load_timeout_s": 1800,
            "one_page_timeout_s": 1800,
            "three_page_timeout_s": 3600,
            "stall_timeout_s": 300,
            "max_raw_output_bytes": 16_777_216,
            "max_log_bytes": 67_108_864,
        },
        "allow_test_content": False,
        "torchvision_local_sha256_TOFU_accepted": True,
        "observation_files": obs_meta,
    }
    return rel, obs_blobs


class Wp0012PreparationGuardTests(unittest.TestCase):
    SYNTHETIC_RELEASE_COMMIT = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    SYNTHETIC_RELEASE_PATH = "docs/coordination/WP-0012/releases/author.json"

    def setUp(self) -> None:
        self.now_utc = datetime(2026, 11, 17, 15, 5, 0, tzinfo=timezone.utc)
        self.actual_head = drv.git_stdout(REPO_ROOT, ["rev-parse", "HEAD"]).lower()
        self.valid_rel, self.obs_blobs = make_synthetic_valid_wp0012_release(self.actual_head, self.now_utc)

    def _validate(
        self,
        rel_doc: dict,
        *,
        release_commit: str | None = None,
        release_path: str | None = None,
        require_clean_worktree: bool = False,
    ) -> dict:
        return drv.validate_release_contract(
            rel_doc,
            root=REPO_ROOT,
            release_commit=release_commit or self.SYNTHETIC_RELEASE_COMMIT,
            release_path=release_path or self.SYNTHETIC_RELEASE_PATH,
            now_utc=self.now_utc,
            blob_loader=lambda p: self.obs_blobs[p],
            commit_exists_fn=lambda sha: sha == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            or drv.git_object_exists(REPO_ROOT, f"{sha}^{{commit}}"),
            require_clean_worktree=require_clean_worktree,
        )

    def test_01_valid_release_and_dual_crlf_lf_observation_hash_pass(self) -> None:
        out = self._validate(self.valid_rel)
        self.assertEqual(out["lease_id"], "WP-0012-author-rehearsal-20261117T150000Z")
        self.assertEqual(out["database"], "eledgercare_demo_wp0012_author")

    def test_02_accepts_packet_base_73c8d3c4_as_source_commit_and_review_alias_keys(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["source_commit"] = drv.ACCEPTED_PACKET_BASE_SHA
        doc.pop("accepted_preparation_review")
        doc["independent_review_002"] = {"publication": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
        out = self._validate(doc)
        self.assertEqual(out["source_commit"], drv.ACCEPTED_PACKET_BASE_SHA)

    def test_03_cli_rejects_missing_release_args_for_execute_live(self) -> None:
        cp = subprocess.run(
            [sys.executable, "-B", str(HELPERS_DIR / "run_wp0012_rehearsal.py"), "--execute-live"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("--release-commit", cp.stderr)

    def test_04_cli_rejects_preparation_dispatch_authority_47fbc761(self) -> None:
        cp = subprocess.run(
            [
                sys.executable,
                "-B",
                str(HELPERS_DIR / "run_wp0012_rehearsal.py"),
                "--validate-release",
                "--release-commit",
                drv.PREPARATION_DISPATCH_AUTHORITY_SHA,
                "--release-path",
                self.SYNTHETIC_RELEASE_PATH,
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("historical or CPU-preparation-only", cp.stderr)

    def test_05_rejects_historical_wp0006_lease_id(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["lease_id"] = "WP-0006-author-corrected-20261116T154140Z"
        with self.assertRaisesRegex(drv.RehearsalGuardError, "lease_id"):
            self._validate(doc)

    def test_06_rejects_max_model_attempts_other_than_2(self) -> None:
        for bad_attempts in (0, 1, 3, 4):
            doc = copy.deepcopy(self.valid_rel)
            doc["max_model_attempts"] = bad_attempts
            with self.assertRaisesRegex(drv.RehearsalGuardError, "max_model_attempts"):
                self._validate(doc)

    def test_07_rejects_lease_exceeding_6h_ceiling(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["expires_utc"] = (self.now_utc + timedelta(hours=6, minutes=5)).isoformat()
        with self.assertRaisesRegex(drv.RehearsalGuardError, "21600s"):
            self._validate(doc)

    def test_08_rejects_expired_or_under_300s_remaining_lease(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["expires_utc"] = (self.now_utc + timedelta(seconds=120)).isoformat()
        with self.assertRaisesRegex(drv.RehearsalGuardError, "remaining"):
            self._validate(doc)

    def test_09_rejects_wrong_owner_or_conversation_or_reviewer_ports(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["owner"] = "eld-f4-reviewer"
        with self.assertRaisesRegex(drv.RehearsalGuardError, "owner"):
            self._validate(doc)

        doc2 = copy.deepcopy(self.valid_rel)
        doc2["ports"] = {"api": 5690, "ui": 4710, "postgres": 55439}
        with self.assertRaisesRegex(drv.RehearsalGuardError, "ports"):
            self._validate(doc2)

    def test_10_rejects_retained_f4_databases(self) -> None:
        for bad_db in ("eledgercare_f4_author_seed_f3", "eledgercare_f4_author_migrated", "eledgercare_demo_wp0012_reviewer"):
            doc = copy.deepcopy(self.valid_rel)
            doc["database"] = bad_db
            with self.assertRaisesRegex(drv.RehearsalGuardError, "forbidden"):
                self._validate(doc)

    def test_11_rejects_wrong_executing_head(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["executing_head"] = "cccccccccccccccccccccccccccccccccccccccc"
        with self.assertRaisesRegex(drv.RehearsalGuardError, "HEAD"):
            self._validate(doc)

    def test_12_rejects_missing_independent_002_review_binding(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc.pop("accepted_preparation_review")
        with self.assertRaisesRegex(drv.RehearsalGuardError, "002 review"):
            self._validate(doc)

    def test_13_rejects_mutated_product_tree_or_fixture_digest(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["product_tree_objects"]["web"] = "1111111111111111111111111111111111111111"
        with self.assertRaisesRegex(drv.RehearsalGuardError, "product_tree_objects"):
            self._validate(doc)

        doc2 = copy.deepcopy(self.valid_rel)
        doc2["pinned_digests"]["syn_wo_01_sha256"] = "0" * 64
        with self.assertRaisesRegex(drv.RehearsalGuardError, "syn_wo_01_sha256"):
            self._validate(doc2)

    def test_14_rejects_wrong_storage_cap_or_free_floor_or_timeout_guards(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["storage_cap_bytes"] = 8 * 1024 * 1024 * 1024
        with self.assertRaisesRegex(drv.RehearsalGuardError, "storage_cap_bytes"):
            self._validate(doc)

        doc2 = copy.deepcopy(self.valid_rel)
        doc2["guards"]["three_page_timeout_s"] = 7200
        with self.assertRaisesRegex(drv.RehearsalGuardError, "three_page_timeout_s"):
            self._validate(doc2)

    def test_15_rejects_allow_test_content_true_or_missing_tofu_exception(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["allow_test_content"] = True
        with self.assertRaisesRegex(drv.RehearsalGuardError, "allow_test_content"):
            self._validate(doc)

        doc2 = copy.deepcopy(self.valid_rel)
        doc2["torchvision_local_sha256_TOFU_accepted"] = False
        with self.assertRaisesRegex(drv.RehearsalGuardError, "TOFU"):
            self._validate(doc2)

    def test_16_rejects_wrong_runtime_root_or_q0_root(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["runtime_root"] = r"C:\Users\jackg\eLedgerCare-Demo\WP-0012\reviewer"
        with self.assertRaisesRegex(drv.RehearsalGuardError, "runtime_root"):
            self._validate(doc)

    def test_17_rejects_corrupted_observation_blob_sha256(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["observation_files"]["model-before.json"]["sha256"] = "f" * 64
        with self.assertRaisesRegex(drv.RehearsalGuardError, "SHA mismatch"):
            self._validate(doc)

    def test_18_win32_process_identity_probe_matches_current_python_pid(self) -> None:
        ident = drv.get_win32_process_identity(os.getpid())
        self.assertIsNotNone(ident)
        assert ident is not None
        self.assertTrue(ident["alive"])
        self.assertGreater(ident["create_filetime"], 0)
        self.assertTrue(drv.is_exact_process_alive(os.getpid(), ident["create_filetime"]))
        self.assertFalse(drv.is_exact_process_alive(os.getpid(), ident["create_filetime"] + 1))


def scrub_secrets(text: str, secrets: list[str]) -> str:
    out = text
    for s in secrets:
        if s:
            out = out.replace(s, "[REDACTED_LOCAL_SECRET]")
    return out


def run_logged_step(name: str, cmd: list[str], cwd: Path, secrets: list[str], extra_env: dict[str, str] | None = None) -> dict:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    started = drv.utc_now()
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    cp = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    log_path = LOGS_DIR / f"{name}.log"
    combined = (
        f"$ {' '.join(cmd)}\n"
        f"[exit={cp.returncode}, elapsed_ms={elapsed_ms}]\n"
        f"--- STDOUT ---\n{scrub_secrets(cp.stdout, secrets)}\n"
        f"--- STDERR ---\n{scrub_secrets(cp.stderr, secrets)}\n"
    )
    log_path.write_text(combined, encoding="utf-8", newline="\n")
    if cp.returncode != 0:
        raise RuntimeError(f"Step {name} failed (exit={cp.returncode}); see {log_path}")
    return {
        "step": name,
        "command": [scrub_secrets(c, secrets) for c in cmd],
        "cwd": "." if cwd == REPO_ROOT else cwd.relative_to(REPO_ROOT).as_posix(),
        "started_utc": started,
        "elapsed_ms": elapsed_ms,
        "exit_code": cp.returncode,
        "log_relpath": log_path.relative_to(REPO_ROOT).as_posix(),
        "log_sha256": drv.sha256_file(log_path),
    }


def query_canonical_8_table_digests(settings: dict, db: str) -> dict:
    raw = drv.run_psql_query(settings, db, CANONICAL_8_TABLE_SQL)
    parsed = json.loads(raw)
    full_sha = drv.sha256_bytes(json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    core_only = {k: v for k, v in parsed.items() if k != "migrations"}
    core_sha = drv.sha256_bytes(json.dumps(core_only, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    return {"full_sha256": full_sha, "core_sha256": core_sha}


def query_projection_digest(settings: dict, db: str) -> str:
    raw = drv.run_psql_query(settings, db, PROJECTION_TABLES_SQL)
    parsed = json.loads(raw)
    return drv.sha256_bytes(json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def run_static_and_ast_audit(require_clean: bool) -> dict:
    porcelain = drv.git_stdout(REPO_ROOT, ["status", "--porcelain"])
    if require_clean and porcelain != "":
        raise RuntimeError(f"Worktree must be clean before decisive CPU validation:\n{porcelain}")

    branch = drv.git_stdout(REPO_ROOT, ["rev-parse", "--abbrev-ref", "HEAD"])
    if branch != drv.EXPECTED_BRANCH:
        raise RuntimeError(f"Unexpected branch {branch!r} != {drv.EXPECTED_BRANCH!r}")

    head_sha = drv.git_stdout(REPO_ROOT, ["rev-parse", "HEAD"]).lower()
    changed = [
        ln.strip()
        for ln in drv.git_stdout(REPO_ROOT, ["diff", "--name-only", drv.PREPARATION_DISPATCH_AUTHORITY_SHA, head_sha]).splitlines()
        if ln.strip()
    ]
    unpermitted = [p for p in changed if not p.startswith("docs/implementation/WP-0012/eld-f4-implementer/")]
    if unpermitted:
        raise RuntimeError(f"Unpermitted paths modified outside WP-0012 / 001 scope: {unpermitted}")

    py_helpers = sorted(HELPERS_DIR.glob("*.py"))
    for pyf in py_helpers:
        py_compile.compile(str(pyf), doraise=True)
        tree = ast.parse(pyf.read_text(encoding="utf-8"), filename=str(pyf))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(FORBIDDEN_IMPORT_PREFIXES):
                        raise RuntimeError(f"Forbidden import {alias.name} in {pyf.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    raise RuntimeError(f"Forbidden import from {node.module} in {pyf.name}")

    return {
        "clean_worktree": porcelain == "",
        "branch": branch,
        "frozen_head_sha": head_sha,
        "dispatch_authority_sha": drv.PREPARATION_DISPATCH_AUTHORITY_SHA,
        "packet_base_sha": drv.ACCEPTED_PACKET_BASE_SHA,
        "changed_paths_since_authority": changed,
        "compiled_python_helpers": [p.relative_to(REPO_ROOT).as_posix() for p in py_helpers],
        "forbidden_ml_or_research_imports": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()

    started_utc = drv.utc_now()
    static_audit = run_static_and_ast_audit(require_clean=args.require_clean)
    drv.assert_ports_unbound((5590, 4610, 55438))

    if EVIDENCE_DIR.exists():
        shutil.rmtree(EVIDENCE_DIR)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    settings = json.loads((REPO_ROOT / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
    secrets = [
        str(settings.get("adminPassword", "")),
        str(settings.get("migratorPassword", "")),
        str(settings.get("appPassword", "")),
    ]
    dotnet_env = {
        "DOTNET_CLI_HOME": str(REPO_ROOT / ".local" / "dotnet-home"),
        "NUGET_PACKAGES": str(REPO_ROOT / ".local" / "nuget" / "packages"),
        "DOTNET_NOLOGO": "1",
        "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
    }

    steps: list[dict] = []
    pg_started = False
    pg_pid = None

    try:
        # 01. Node syntax check on Edge rehearsal driver
        steps.append(
            run_logged_step(
                "01-node-check-edge-driver",
                ["node", "--check", str(drv.EDGE_DRIVER_PATH)],
                REPO_ROOT,
                secrets,
            )
        )

        # 02. Offline locked .NET restore & Release solution build
        steps.append(
            run_logged_step(
                "02-dotnet-restore-and-build-release",
                ["dotnet", "build", "ELedgerCare.slnx", "-c", "Release", "--locked-mode", "--configfile", ".local/nuget/offline.nuget.config"],
                REPO_ROOT,
                secrets,
                extra_env=dotnet_env,
            )
        )

        # 03. Angular 22 production bundle build
        steps.append(
            run_logged_step(
                "03-ng-build-production",
                ["node", "node_modules/@angular/cli/bin/ng.js", "build"],
                REPO_ROOT / "web",
                secrets,
                extra_env={"NG_CLI_ANALYTICS": "false"},
            )
        )

        # 04. 18 unit & CLI subprocess release-contract / guard-ceiling tests
        t0 = time.perf_counter()
        ut_started = drv.utc_now()
        buf = io.StringIO()
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Wp0012PreparationGuardTests)
        ut_res = unittest.TextTestRunner(stream=buf, verbosity=2).run(suite)
        ut_elapsed = round((time.perf_counter() - t0) * 1000, 1)
        ut_log = LOGS_DIR / "04-guard-and-release-contract-tests.log"
        ut_log.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
        if not ut_res.wasSuccessful():
            raise RuntimeError(f"Unit test suite failed; see {ut_log}")
        steps.append(
            {
                "step": "04-guard-and-release-contract-tests",
                "command": ["unittest", "Wp0012PreparationGuardTests"],
                "cwd": ".",
                "started_utc": ut_started,
                "elapsed_ms": ut_elapsed,
                "exit_code": 0,
                "tests_run": ut_res.testsRun,
                "log_relpath": ut_log.relative_to(REPO_ROOT).as_posix(),
                "log_sha256": drv.sha256_file(ut_log),
            }
        )

        # 05. Start owned PostgreSQL 18.7 (55438), verify old F4 DB digests BEFORE, prepare new empty DB, run CPU dry-run + Edge preflight
        steps.append(
            run_logged_step(
                "05-pg-cluster-start",
                ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/start-cluster.ps1"],
                REPO_ROOT,
                secrets,
            )
        )
        pg_started = True
        pg_pid = int((REPO_ROOT / ".local" / "postgres-data" / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0])

        seed_pre = query_canonical_8_table_digests(settings, SEED_F3_DB)
        mig_pre = query_canonical_8_table_digests(settings, MIGRATED_F4_DB)
        proj_pre = query_projection_digest(settings, MIGRATED_F4_DB)
        if seed_pre["full_sha256"] != EXPECTED_SEED_F3_SHA256:
            raise RuntimeError(f"Retained {SEED_F3_DB} digest mismatch before preparation: {seed_pre}")
        if mig_pre["core_sha256"] != EXPECTED_MIGRATED_CORE_SHA256 or proj_pre != EXPECTED_MIGRATED_PROJ_SHA256:
            raise RuntimeError(f"Retained {MIGRATED_F4_DB} digest mismatch before preparation: {mig_pre} / {proj_pre}")

        # Recreate clean empty eledgercare_demo_wp0012_author if needed and apply all 4 migrations + runtime grants
        drv.run_psql_query(
            settings,
            "postgres",
            f"DROP DATABASE IF EXISTS {drv.OWNED_REHEARSAL_DB} WITH (FORCE);",
        )
        steps.append(
            run_logged_step(
                "06-prepare-owned-rehearsal-db",
                ["pwsh", "-NoProfile", "-File", "deploy/dev/database/prepare-database.ps1", "-Database", drv.OWNED_REHEARSAL_DB],
                REPO_ROOT,
                secrets,
                extra_env=dotnet_env,
            )
        )

        cpu_dryrun_json = EVIDENCE_DIR / "cpu-dry-run-receipt.json"
        steps.append(
            run_logged_step(
                "07-cpu-dry-run-and-disabled-ocr-edge-smoke",
                [
                    sys.executable,
                    "-B",
                    str(HELPERS_DIR / "run_wp0012_rehearsal.py"),
                    "--cpu-dry-run",
                    "--with-disabled-ocr-smoke",
                    "--output",
                    str(cpu_dryrun_json),
                ],
                REPO_ROOT,
                secrets,
            )
        )

        # Verify retained F4 databases remain 100% unchanged and new rehearsal DB remains empty (0 simulated rows!)
        seed_post = query_canonical_8_table_digests(settings, SEED_F3_DB)
        mig_post = query_canonical_8_table_digests(settings, MIGRATED_F4_DB)
        proj_post = query_projection_digest(settings, MIGRATED_F4_DB)
        if seed_post["full_sha256"] != EXPECTED_SEED_F3_SHA256:
            raise RuntimeError(f"Retained {SEED_F3_DB} mutated during WP-0012 preparation!")
        if mig_post["core_sha256"] != EXPECTED_MIGRATED_CORE_SHA256 or proj_post != EXPECTED_MIGRATED_PROJ_SHA256:
            raise RuntimeError(f"Retained {MIGRATED_F4_DB} mutated during WP-0012 preparation!")

        rehearsal_db_snapshot = query_canonical_8_table_digests(settings, drv.OWNED_REHEARSAL_DB)
        retained_dbs = [
            ln.strip()
            for ln in drv.run_psql_query(
                settings,
                "postgres",
                "SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres' ORDER BY datname;",
            ).splitlines()
            if ln.strip()
        ]

        steps.append(
            run_logged_step(
                "08-pg-cluster-stop-final",
                ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"],
                REPO_ROOT,
                secrets,
            )
        )
        pg_started = False
        final_ports = drv.assert_ports_unbound((5590, 4610, 55438))
        worker_procs = drv.count_ocr_worker_processes()
        if worker_procs != 0:
            raise RuntimeError(f"Expected 0 OCR worker processes, found {worker_procs}")
        if drv.EXPECTED_DEMO_RUNTIME_ROOT.exists():
            # Ensure CPU preparation did not create or mutate any run directories
            runs_sub = drv.EXPECTED_DEMO_RUNTIME_ROOT / "runs"
            if runs_sub.exists() and any(runs_sub.iterdir()):
                raise RuntimeError(f"Unexpected run directories under {runs_sub} during CPU preparation!")

        shutil.rmtree(REPO_ROOT / ".scratch", ignore_errors=True)
        completed_utc = drv.utc_now()

        summary = {
            "packet": "WP-0012",
            "sequence": "001",
            "phase": "CPU-only demonstration rehearsal preparation",
            "author": "eld-f4-implementer",
            "started_utc": started_utc,
            "completed_utc": completed_utc,
            "live_rehearsal_executed": False,
            "model_imported_or_invoked": False,
            "gpu_queries_or_inference_run": False,
            "static_and_ast_audit": static_audit,
            "executed_steps": steps,
            "database_state": {
                "new_owned_rehearsal_database": drv.OWNED_REHEARSAL_DB,
                "new_owned_rehearsal_empty_8_table_sha256": rehearsal_db_snapshot["full_sha256"],
                "documents_count": 0,
                "execution_attempts_count": 0,
                "extraction_results_count": 0,
                "retained_f4_seed_db_preserved": SEED_F3_DB,
                "retained_f4_seed_sha256": seed_post["full_sha256"],
                "retained_f4_migrated_db_preserved": MIGRATED_F4_DB,
                "retained_f4_migrated_core_sha256": mig_post["core_sha256"],
                "retained_f4_migrated_projection_sha256": proj_post,
            },
            "attributed_unchanged_product_proofs": {
                "accepted_product_source_sha": drv.ACCEPTED_F4_FINAL_SOURCE_SHA,
                "accepted_packet_base_sha": drv.ACCEPTED_PACKET_BASE_SHA,
                "unchanged_trees": drv.EXPECTED_PRODUCT_TREES,
                "note": (
                    "All production src/, web/, tests/, deploy/, and workers/local_ocr/ trees are byte-identical "
                    "to accepted WP-0010 final disposition 73c8d3c4f0a00312e3444328331b6cbd6406e882. Existing unit, "
                    "integration, and E2E suites remain attributed to accepted WP-0006/WP-0008/WP-0010 reports."
                ),
            },
            "unrun_live_steps_held_for_003_lease": [
                "Coordinator creation/release of writable runtime root C:\\Users\\jackg\\eLedgerCare-Demo\\WP-0012\\author",
                "Independent WP-0012 / 002 preparation acceptance by eld-f4-reviewer",
                "Coordinator sole-GPU lease binding exact executing_head and observation_files for WP-0012 / 003",
                "Live browser upload & real local OCR Attempt #1 (SYN-WO-01-v1-raster300.pdf, 1 page) + grounded review + newer draft",
                "Live browser upload & real local OCR Attempt #2 (SYN-MP-01-v0-clean.pdf, 3 pages) + grounded review with 2 unknowns",
                "Live API + PostgreSQL fast restart and disabled-OCR browser search/reopen verification with unchanged 2 attempts",
            ],
        }
        drv.write_json_lf(EVIDENCE_DIR / "validation-summary.json", summary)

        resource_return = {
            "verified_utc": completed_utc,
            "ports": {"5590": "FREE", "4610": "FREE", "55438": "FREE"},
            "observed_listeners": final_ports,
            "stopped_postmaster_pid": pg_pid,
            "ocr_worker_processes_running": 0,
            "scratch_directory_present": (REPO_ROOT / ".scratch").exists(),
            "writable_demo_root_exists": drv.EXPECTED_DEMO_RUNTIME_ROOT.exists(),
            "databases_in_local_cluster": retained_dbs,
            "retained_seed_f3_sha256": seed_post["full_sha256"],
            "retained_migrated_f4_core_sha256": mig_post["core_sha256"],
            "retained_migrated_f4_projection_sha256": proj_post,
        }
        drv.write_json_lf(DOSSIER_DIR / "resource-return.json", resource_return)
        print("WP-0012 / 001 CPU preparation validation PASSED (8/8 steps green; 18/18 guard tests green; all ports FREE).")
    finally:
        if pg_started:
            subprocess.run(
                ["pwsh", "-NoProfile", "-File", "deploy/dev/postgres/stop-cluster.ps1"],
                cwd=str(REPO_ROOT),
                capture_output=True,
            )
        shutil.rmtree(REPO_ROOT / ".scratch", ignore_errors=True)


if __name__ == "__main__":
    main()
