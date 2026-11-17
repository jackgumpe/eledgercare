"""Frozen independent CPU verifier for WP-0012 / 002 (`eld-f4-reviewer`).

Executes strictly on CPU without touching author resources (`5590/4610/55438`,
`eledgercare_demo_wp0012_author`, `eld-f4-implementer` worktree, or `C:\\Users\\jackg\\eLedgerCare-Demo\\WP-0012\\author`),
without importing or invoking any ML/CUDA/venv runtime, and without overwriting retained `preparation/`
artifacts (`7f3f8626489e898a50d275e93ee904660e97fd59`):

  1. Audits exact merged `eld-f4-implementer` `WP-0012 / 001` revisions:
     - Frozen deliverable `ad5202a029a7a86bea5fa3e3d97760d0a9cc673a` (`9` added paths)
     - Post-freeze CPU evidence/inventory `32465da577237827c3ac9d8ed5ee608c8e5668cf` (`14` added paths)
     - Canonical report `165b2421b297bf49181c91af8d05a449ad69e9b5` (`1` report-only path, `69` links)
     - `3,615` unchanged base paths from `47fbc7612e4a08cf1960ad7ac01bd2843ae645e5`, AST import audit,
       `node --check` syntax verification, SHA-256 manifest verification, and secret scan.
  2. Independently executes all `18` `Wp0012PreparationGuardTests` against pinned author `ad5202a0`
     Git state in memory.
  3. Deterministically reproduces author helper blockers & `/001` prose discrepancies on CPU:
     - `F12-B1`: `start_api_and_ui` (`run_wp0012_rehearsal.py:846-900`) leaks an alive orphaned
       `api_proc` (and open `api_fh`) on partial startup failure (`ui_proc` early exit or `api_proc`
       bind timeout), leaving caller `finally:` with `api_proc = None` unable to clean up.
     - `F12-B2`: `execute_live_rehearsal` (`run_wp0012_rehearsal.py:1211-1350`) stop-on-failure path
       bypasses `persisted_attempts` inspection, `launcher_pid`/`worker_pid` exit verification,
       `count_ocr_worker_processes() == 0`, `assert_ports_unbound`, log secret scrubbing, and
       `owner-lease-return.json` emission.
     - `F12-B3`: `_extract_independent_review_002_sha` (`run_wp0012_rehearsal.py:406-413`) rejects
       key `"independent_preparation_review_002_sha"` even though `/001` lines 64 & 114 instruct
       `eld-coordinator` to bind that exact key name.
     - `F12-D1`..`D4`: `/001` prose discrepancies (`--release` vs `--release-commit`/`--release-path`;
       `live-phase1`/`live-phase2` vs `live-phase-a`/`live-phase-b-reopen`; unsupported `/001` L64
       `git merge-base --is-ancestor` claim on `/002` SHA and overstated Step `04` unit-test claims;
       unverified literal `ocrEnabledDuringReopen: false` in `drive_rehearsal_edge.mjs:675`).
  4. Executes `24` CPU unit & subprocess tests against reconciled reviewer helper
     `run_wp0012_reviewer_rehearsal_v3.py` (`RG-01` exact Git release/accepted-002/003/lease-return/
     observation checks, `RG-02` WDDM desktop sharing vs. competing model ownership, `RG-03`
     refusing-overwrite output paths, and atomic partial-startup process cleanup).
  5. Verifies all `30` initial reviewer `preparation/` artifacts (`7f3f8626`), empty reviewer `runs/`
     directory, stopped `.local/postgres-data`, and `0` listeners on reviewer ports `5690/4710/55439`.
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
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

AUTHOR_DELIVERABLE_SHA = "ad5202a029a7a86bea5fa3e3d97760d0a9cc673a"
AUTHOR_EVIDENCE_SHA = "32465da577237827c3ac9d8ed5ee608c8e5668cf"
AUTHOR_PUBLICATION_SHA = "165b2421b297bf49181c91af8d05a449ad69e9b5"
AUTHORITY_WP0012_SHA = "47fbc7612e4a08cf1960ad7ac01bd2843ae645e5"
ACCEPTED_PRODUCT_BASE_SHA = "73c8d3c4f0a00312e3444328331b6cbd6406e882"
REVIEWER_INITIAL_PREP_PUB_SHA = "7f3f8626489e898a50d275e93ee904660e97fd59"
REVIEWER_INITIAL_PREP_HELPER_SHA = "c09cf1aa8282e440e364c6020152dd257355643b"

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[6]
REVIEWER_HELPERS_DIR = SCRIPT_PATH.parent
AUTHOR_HELPERS_DIR = REPO_ROOT / "docs" / "implementation" / "WP-0012" / "eld-f4-implementer" / "helpers"

sys.path.insert(0, str(REVIEWER_HELPERS_DIR))
import run_wp0012_reviewer_rehearsal_v3 as rv3  # noqa: E402

sys.path.insert(0, str(AUTHOR_HELPERS_DIR))
import run_wp0012_rehearsal as author_drv  # noqa: E402
import validate_wp0012_preparation_cpu as author_val  # noqa: E402

MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#?\s]+)(?:#[^)\s]*)?\)")
FORBIDDEN_ML_IMPORTS = (
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


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=str(REPO_ROOT), text=True, encoding="utf-8").strip()


def make_synthetic_reviewer_v3_release(actual_head: str, now_utc: datetime) -> tuple[dict, dict[str, bytes]]:
    ownership_blob = json.dumps(
        {
            "schema": "eld-wp12-wp13-ownership-observation/1",
            "observed_utc": (now_utc - timedelta(minutes=3)).isoformat(),
            "gpu_exit": 0,
            "apps_exit": 0,
            "apps": ["1840, C:\\Windows\\System32\\dwm.exe, 142"],
            "candidate_and_gpu_processes": [
                {
                    "ProcessId": 1840,
                    "Name": "dwm.exe",
                    "ExecutablePath": r"C:\Windows\System32\dwm.exe",
                    "CreationDate": "20261117000000.000000-300",
                },
                {
                    "ProcessId": 9412,
                    "Name": "CustomDesktopHelper.exe",
                    "ExecutablePath": r"C:\Program Files\Vendor\CustomDesktopHelper.exe",
                    "CreationDate": "20261117010000.000000-300",
                },
            ],
            "ollama_ps_exit": 0,
            "ollama_ps": ["NAME    ID    SIZE    PROCESSOR    UNTIL"],
        },
        indent=2,
    ).encode("utf-8") + b"\r\n"
    model_blob = b'{"ok": true, "model_objects": 18}\n'
    author_ret_blob = b'{"schema": "eledgercare.wp0012-owner-lease-return/1", "owner": "eld-f4-implementer"}\n'

    blobs = {
        "docs/coordination/WP-0012-0013/reviewer-004/ownership-before.json": ownership_blob,
        "docs/coordination/WP-0012/reviewer-004/model-before.json": model_blob,
        "docs/coordination/WP-0012/reviewer-004/author-lease-return-audit.json": author_ret_blob,
    }
    rel = {
        "schema": "eledgercare.wp0012-rehearsal-release/1",
        "synthetic_test_only": True,
        "packet": "WP-0012",
        "owner": "eld-f4-reviewer",
        "conversation_id": "61105d43-7706-45f2-9176-69d3256248e0",
        "model": "gemini-4-carbon-high",
        "effort": "high",
        "source_commit": rv3.ACCEPTED_F4_FINAL_SOURCE_SHA,
        "executing_head": actual_head,
        "accepted_review_002": "1111111111111111111111111111111111111111",
        "accepted_author_003": "2222222222222222222222222222222222222222",
        "author_lease_return": {
            "commit": "3333333333333333333333333333333333333333",
            "path": "docs/coordination/WP-0012/reviewer-004/author-lease-return-audit.json",
            "sha256": sha256_hex(author_ret_blob),
        },
        "product_tree_objects": dict(rv3.EXPECTED_PRODUCT_TREES),
        "pinned_digests": dict(rv3.EXPECTED_PINNED_DIGESTS),
        "lease_id": "WP-0012-reviewer-004-SYNTHETIC-TEST-20261117T160000Z",
        "gpu_uuid": rv3.EXPECTED_GPU_UUID,
        "released_utc": (now_utc - timedelta(minutes=2)).isoformat(),
        "expires_utc": (now_utc + timedelta(hours=4)).isoformat(),
        "max_model_attempts": 2,
        "readonly_q0_root": r"C:\Users\jackg\eLedgerCare-Q0\WP-0005",
        "runtime_root": r"C:\Users\jackg\eLedgerCare-Demo\WP-0012\reviewer",
        "database": rv3.DEMO_DATABASE,
        "ports": {"api": 5690, "ui": 4710, "postgres": 55439},
        "storage_cap_bytes": 4_294_967_296,
        "free_floor_bytes": 21_474_836_480,
        "allow_test_content": False,
        "torchvision_local_sha256_TOFU_accepted": True,
        "observation_files": {
            "ownership-before.json": {
                "path": "docs/coordination/WP-0012-0013/reviewer-004/ownership-before.json",
                "sha256": sha256_hex(ownership_blob.replace(b"\r\n", b"\n")),
            },
            "model-before.json": {
                "path": "docs/coordination/WP-0012/reviewer-004/model-before.json",
                "sha256": sha256_hex(model_blob),
            },
        },
    }
    return rel, blobs


class ReviewerV3GuardReconciliationTests(unittest.TestCase):
    SYNTH_COMMIT = "9999999999999999999999999999999999999999"
    SYNTH_PATH = "docs/coordination/WP-0012/releases/reviewer-004-synthetic.json"

    def setUp(self) -> None:
        self.now_utc = datetime(2026, 11, 17, 16, 5, 0, tzinfo=timezone.utc)
        self.actual_head = run_git("rev-parse", "HEAD").lower()
        self.valid_rel, self.blobs = make_synthetic_reviewer_v3_release(self.actual_head, self.now_utc)
        self.edge_driver = (
            REPO_ROOT / "docs/reviews/WP-0012/eld-f4-reviewer/preparation/helpers/drive_wp0012_edge_workflow.mjs"
        )
        self.v3_script = REVIEWER_HELPERS_DIR / "run_wp0012_reviewer_rehearsal_v3.py"

    def _validate(
        self,
        doc: dict,
        *,
        release_commit: str | None = None,
        release_path: str | None = None,
        require_clean_worktree: bool = False,
        allow_synthetic: bool = True,
    ) -> dict:
        synth_commits = {
            "1111111111111111111111111111111111111111",
            "2222222222222222222222222222222222222222",
            "3333333333333333333333333333333333333333",
        }
        return rv3.validate_reviewer_release_contract(
            doc,
            repo_root=REPO_ROOT,
            release_commit=release_commit or self.SYNTH_COMMIT,
            release_path=release_path or self.SYNTH_PATH,
            now_utc=self.now_utc,
            blob_loader=lambda p: self.blobs[p],
            commit_exists_fn=lambda sha: (sha in synth_commits) or rv3.git_object_exists(REPO_ROOT, f"{sha}^{{commit}}"),
            helper_paths_to_bind=(self.v3_script, self.edge_driver),
            require_clean_worktree=require_clean_worktree,
            allow_synthetic_test_only=allow_synthetic,
        )

    # --- RG-01: Exact Git release, accepted /002 + /003 + author lease return, expiry, & observation hashes ---
    def test_01_synthetic_valid_contract_passes_only_in_explicit_synthetic_cpu_test_mode(self) -> None:
        out = self._validate(self.valid_rel, allow_synthetic=True)
        self.assertEqual(out["gpu_uuid"], rv3.EXPECTED_GPU_UUID)
        with self.assertRaisesRegex(rv3.ReviewerLeaseGuardError, "synthetic_test_only"):
            self._validate(self.valid_rel, allow_synthetic=False)

    def test_02_rejects_authority_and_preparation_commits_as_release_commit(self) -> None:
        for bad_sha in (
            rv3.ACCEPTED_PRODUCT_BASE_SHA,
            rv3.AUTHORITY_WP0012_SHA,
            rv3.AUTHORITY_002_DISPATCH_SHA,
            REVIEWER_INITIAL_PREP_PUB_SHA,
            AUTHOR_PUBLICATION_SHA,
        ):
            doc = copy.deepcopy(self.valid_rel)
            doc["synthetic_test_only"] = False
            with self.assertRaises(rv3.ReviewerLeaseGuardError):
                self._validate(doc, release_commit=bad_sha, allow_synthetic=False)

    def test_03_rejects_missing_or_unverified_accepted_002_or_author_003_or_lease_return(self) -> None:
        for missing_key in ("accepted_review_002", "accepted_author_003", "author_lease_return"):
            doc = copy.deepcopy(self.valid_rel)
            doc.pop(missing_key)
            with self.assertRaises(rv3.ReviewerLeaseGuardError):
                self._validate(doc)

        doc_bad_003 = copy.deepcopy(self.valid_rel)
        doc_bad_003["accepted_author_003"] = "deadbeef" * 5
        with self.assertRaisesRegex(rv3.ReviewerLeaseGuardError, "003"):
            self._validate(doc_bad_003)

    def test_04_accepts_independent_preparation_review_002_sha_alias_key(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        val = doc.pop("accepted_review_002")
        doc["independent_preparation_review_002_sha"] = val
        out = self._validate(doc)
        self.assertEqual(out["accepted_review_002"], {"independent_preparation_review_002_sha": val})

    def test_05_rejects_mismatched_executing_head_or_uncommitted_helper_drift(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["executing_head"] = "4444444444444444444444444444444444444444"
        with self.assertRaisesRegex(rv3.ReviewerLeaseGuardError, "executing_head"):
            self._validate(doc)

        with tempfile.TemporaryDirectory() as td:
            fake_helper = Path(td) / "uncommitted.py"
            fake_helper.write_text("# drift\n", encoding="utf-8")
            with self.assertRaises(Exception):
                rv3.validate_reviewer_release_contract(
                    self.valid_rel,
                    repo_root=REPO_ROOT,
                    release_commit=self.SYNTH_COMMIT,
                    release_path=self.SYNTH_PATH,
                    now_utc=self.now_utc,
                    blob_loader=lambda p: self.blobs[p],
                    commit_exists_fn=lambda _: True,
                    helper_paths_to_bind=(fake_helper,),
                    require_clean_worktree=True,
                    allow_synthetic_test_only=True,
                )

    def test_06_rejects_gpu_prefix_only_mismatch_and_enforces_exact_gpu_uuid(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["gpu_uuid"] = "GPU-00000000-1111-2222-3333-444444444444"
        with self.assertRaisesRegex(rv3.ReviewerLeaseGuardError, "gpu_uuid"):
            self._validate(doc)

    def test_07_rejects_expired_over_6h_future_or_under_300s_lease_windows(self) -> None:
        for delta_rel, delta_exp in (
            (timedelta(minutes=-10), timedelta(seconds=120)),
            (timedelta(minutes=-2), timedelta(hours=6, minutes=1)),
            (timedelta(minutes=5), timedelta(hours=2)),
            (timedelta(hours=-3), timedelta(minutes=-1)),
        ):
            doc = copy.deepcopy(self.valid_rel)
            doc["released_utc"] = (self.now_utc + delta_rel).isoformat()
            doc["expires_utc"] = (self.now_utc + delta_exp).isoformat()
            with self.assertRaises(rv3.ReviewerLeaseGuardError):
                self._validate(doc)

    def test_08_rejects_wrong_owner_ports_database_roots_or_attempt_cap(self) -> None:
        for mut in (
            {"owner": "eld-f4-implementer"},
            {"ports": {"api": 5590, "ui": 4610, "postgres": 55438}},
            {"database": "eledgercare_demo_wp0012_author"},
            {"database": "eledgercare_f4_reviewer_seed_f3"},
            {"runtime_root": r"C:\Users\jackg\eLedgerCare-Demo\WP-0012\author"},
            {"max_model_attempts": 1},
            {"max_model_attempts": 3},
        ):
            doc = copy.deepcopy(self.valid_rel)
            doc.update(mut)
            with self.assertRaises(rv3.ReviewerLeaseGuardError):
                self._validate(doc)

    def test_09_rejects_corrupted_observation_or_lease_return_blob_sha256(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["observation_files"]["ownership-before.json"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(rv3.ReviewerLeaseGuardError, "SHA-256 mismatch"):
            self._validate(doc)

        doc2 = copy.deepcopy(self.valid_rel)
        doc2["author_lease_return"]["sha256"] = "f" * 64
        with self.assertRaisesRegex(rv3.ReviewerLeaseGuardError, "SHA-256 mismatch"):
            self._validate(doc2)

    def test_10_rejects_product_tree_or_fixture_digest_drift(self) -> None:
        doc = copy.deepcopy(self.valid_rel)
        doc["product_tree_objects"]["src"] = "f" * 40
        with self.assertRaisesRegex(rv3.ReviewerLeaseGuardError, "product_tree_objects"):
            self._validate(doc)

        doc2 = copy.deepcopy(self.valid_rel)
        doc2["pinned_digests"]["syn_mp_01_sha256"] = "e" * 64
        with self.assertRaisesRegex(rv3.ReviewerLeaseGuardError, "syn_mp_01_sha256"):
            self._validate(doc2)

    # --- RG-02: Desktop/WDDM sharing vs. unaccounted competing model ownership ---
    def test_11_allows_benign_wddm_desktop_and_prelease_accounted_non_model_apps(self) -> None:
        validated = self._validate(self.valid_rel)
        snap = {
            "apps": [
                "1840, C:\\Windows\\System32\\dwm.exe, 185",
                "7720, C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe, 94",
                "9412, C:\\Program Files\\Vendor\\CustomDesktopHelper.exe, 32",
            ],
            "candidate_and_gpu_processes": [
                {"ProcessId": 1840, "Name": "dwm.exe", "ExecutablePath": r"C:\Windows\System32\dwm.exe"},
                {"ProcessId": 7720, "Name": "msedge.exe", "ExecutablePath": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"},
                {"ProcessId": 9412, "Name": "CustomDesktopHelper.exe", "ExecutablePath": r"C:\Program Files\Vendor\CustomDesktopHelper.exe"},
            ],
            "ollama_ps": ["NAME    ID    SIZE    PROCESSOR    UNTIL"],
        }
        res = rv3.evaluate_gpu_and_model_ownership(snap, pre_lease_blobs=validated["parsed_pre_lease_blobs"], self_pid=99999)
        self.assertTrue(res["sole_model_job_verified"])
        self.assertFalse(res["hardware_exclusivity_claimed"])
        self.assertTrue(res["wddm_desktop_sharing_observed"])
        self.assertEqual(len(res["wddm_desktop_sharing_entries"]), 3)

    def test_12_fails_closed_on_competing_python_gpu_compute_process(self) -> None:
        snap = {
            "apps": ["41200, C:\\Users\\jackg\\eLedgerCare-Q0\\WP-0005\\venv\\Scripts\\python.exe, 7012"],
            "candidate_and_gpu_processes": [
                {
                    "ProcessId": 41200,
                    "Name": "python.exe",
                    "ExecutablePath": r"C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe",
                    "CommandLine": "python.exe workers/local_ocr/run_worker.py --request req.json",
                }
            ],
            "ollama_ps": None,
        }
        with self.assertRaises(rv3.CompetingModelOwnershipError):
            rv3.evaluate_gpu_and_model_ownership(snap, self_pid=99999)

    def test_13_fails_closed_on_competing_wp0013_rd_or_q0_harness_host_process(self) -> None:
        snap = {
            "apps": ["1840, C:\\Windows\\System32\\dwm.exe, 120"],
            "candidate_and_gpu_processes": [
                {
                    "ProcessId": 45100,
                    "Name": "python.exe",
                    "ExecutablePath": r"C:\Python312\python.exe",
                    "CommandLine": "python -m qualification.mapping_v2.run_eval",
                }
            ],
            "ollama_ps": None,
        }
        with self.assertRaises(rv3.CompetingModelOwnershipError):
            rv3.evaluate_gpu_and_model_ownership(snap, self_pid=99999)

    def test_14_fails_closed_on_active_ollama_or_local_llm_server(self) -> None:
        snap_ollama = {
            "apps": [],
            "candidate_and_gpu_processes": [],
            "ollama_ps": [
                "NAME          ID              SIZE      PROCESSOR    UNTIL",
                "qwen2.5:7b    abc123def456    4.7 GB    100% GPU     4 minutes from now",
            ],
        }
        with self.assertRaises(rv3.CompetingModelOwnershipError):
            rv3.evaluate_gpu_and_model_ownership(snap_ollama, self_pid=99999)

        snap_vllm = {
            "apps": [],
            "candidate_and_gpu_processes": [{"ProcessId": 50001, "Name": "llama-server.exe", "ExecutablePath": "C:\\llm\\llama-server.exe"}],
            "ollama_ps": None,
        }
        with self.assertRaises(rv3.CompetingModelOwnershipError):
            rv3.evaluate_gpu_and_model_ownership(snap_vllm, self_pid=99999)

    def test_15_fails_closed_on_unaccounted_unknown_gpu_compute_binary(self) -> None:
        snap = {
            "apps": ["61000, C:\\Unknown\\custom_cuda_job.exe, 512"],
            "candidate_and_gpu_processes": [],
            "ollama_ps": None,
        }
        with self.assertRaises(rv3.CompetingModelOwnershipError):
            rv3.evaluate_gpu_and_model_ownership(snap, pre_lease_blobs={}, self_pid=99999)

    # --- RG-03: Refusing-overwrite output destinations ---
    def test_16_refuses_writing_into_retained_preparation_or_author_001_review_namespaces(self) -> None:
        for protected_rel in (
            "docs/reviews/WP-0012/eld-f4-reviewer/preparation/observations/new.json",
            "docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/observations/new.json",
            "docs/reviews/WP-0010/eld-f4-reviewer/runtime/new.json",
            "docs/implementation/WP-0012/eld-f4-implementer/new.json",
        ):
            with self.assertRaises(rv3.ReviewerLeaseGuardError):
                rv3.guard_new_non_overwriting_output_targets(
                    REPO_ROOT,
                    file_targets=[REPO_ROOT / protected_rel],
                    dir_targets=[],
                )

    def test_17_refuses_overwriting_existing_file_or_nonempty_directory_in_demo_root(self) -> None:
        with tempfile.TemporaryDirectory(dir=str(rv3.WRITABLE_DEMO_ROOT)) as td:
            td_p = Path(td)
            existing_file = td_p / "summary.json"
            existing_file.write_text("{}", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                rv3.guard_new_non_overwriting_output_targets(
                    REPO_ROOT,
                    file_targets=[existing_file],
                    dir_targets=[],
                )

            non_empty_dir = td_p / "logs"
            non_empty_dir.mkdir()
            (non_empty_dir / "prior.log").write_text("x", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                rv3.guard_new_non_overwriting_output_targets(
                    REPO_ROOT,
                    file_targets=[td_p / "fresh-summary.json"],
                    dir_targets=[non_empty_dir],
                )

    def test_18_accepts_brand_new_runtime_004_and_demo_root_destinations(self) -> None:
        rv3.guard_new_non_overwriting_output_targets(
            REPO_ROOT,
            file_targets=[REPO_ROOT / "docs/reviews/WP-0012/eld-f4-reviewer/runtime-004/observations/live-summary.json"],
            dir_targets=[REPO_ROOT / "docs/reviews/WP-0012/eld-f4-reviewer/runtime-004/observations/logs"],
        )

    def test_19_cli_live_mode_exits_2_on_existing_preparation_path_or_non_git_release(self) -> None:
        cp = rv3.run_cmd(
            [
                sys.executable,
                "-B",
                str(self.v3_script),
                "--mode",
                "live-leased-rehearsal",
                "--release-commit",
                rv3.AUTHORITY_WP0012_SHA,
                "--release-path",
                self.SYNTH_PATH,
                "--summary-output",
                "docs/reviews/WP-0012/eld-f4-reviewer/preparation/observations/cpu-prep-validation-summary.json",
                "--q0-check-output",
                "docs/reviews/WP-0012/eld-f4-reviewer/runtime-004/q0.json",
                "--resource-return-output",
                "docs/reviews/WP-0012/eld-f4-reviewer/runtime-004/rr.json",
                "--logs-dir",
                "docs/reviews/WP-0012/eld-f4-reviewer/runtime-004/logs",
                "--screenshots-dir",
                "docs/reviews/WP-0012/eld-f4-reviewer/runtime-004/shots",
            ],
            cwd=REPO_ROOT,
        )
        self.assertEqual(cp.returncode, 2)
        self.assertIn("Refusing live-leased-rehearsal", cp.stderr)

    # --- Atomic partial-startup process cleanup in reviewer v3 ---
    def test_20_atomic_service_startup_terminates_api_child_when_ui_exits_early(self) -> None:
        recorded_api_pid: list[int] = []
        orig_inspect = rv3.inspect_process

        def spy_inspect(pid: int, cwd: Path):
            res = orig_inspect(pid, cwd)
            if not recorded_api_pid and res is not None:
                recorded_api_pid.append(pid)
            return res

        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            with mock.patch.object(rv3, "inspect_process", side_effect=spy_inspect):
                with self.assertRaisesRegex(RuntimeError, "Owned UI exited early"):
                    rv3.start_owned_services_atomic(
                        api_cmd=[sys.executable, "-B", "-c", "import time; time.sleep(60)"],
                        api_cwd=td_p,
                        api_env=dict(os.environ),
                        api_log_path=td_p / "api.log",
                        ui_cmd=[sys.executable, "-B", "-c", "import sys; sys.exit(1)"],
                        ui_cwd=td_p,
                        ui_env=dict(os.environ),
                        ui_log_path=td_p / "ui.log",
                        repo_root=REPO_ROOT,
                        api_ready_fn=lambda: True,
                        ui_ready_fn=lambda: False,
                        api_timeout_s=5.0,
                        ui_timeout_s=5.0,
                    )
            self.assertEqual(len(recorded_api_pid), 1)
            self.assertIsNone(rv3.inspect_process(recorded_api_pid[0], REPO_ROOT))

    def test_21_atomic_service_startup_terminates_api_child_on_api_readiness_timeout(self) -> None:
        recorded_api_pid: list[int] = []
        orig_inspect = rv3.inspect_process

        def spy_inspect(pid: int, cwd: Path):
            res = orig_inspect(pid, cwd)
            if not recorded_api_pid and res is not None:
                recorded_api_pid.append(pid)
            return res

        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            with mock.patch.object(rv3, "inspect_process", side_effect=spy_inspect):
                with self.assertRaisesRegex(RuntimeError, "Owned API failed readiness check"):
                    rv3.start_owned_services_atomic(
                        api_cmd=[sys.executable, "-B", "-c", "import time; time.sleep(60)"],
                        api_cwd=td_p,
                        api_env=dict(os.environ),
                        api_log_path=td_p / "api.log",
                        ui_cmd=[sys.executable, "-B", "-c", "import sys; sys.exit(0)"],
                        ui_cwd=td_p,
                        ui_env=dict(os.environ),
                        ui_log_path=td_p / "ui.log",
                        repo_root=REPO_ROOT,
                        api_ready_fn=lambda: False,
                        ui_ready_fn=lambda: False,
                        api_timeout_s=0.4,
                        ui_timeout_s=0.4,
                    )
            self.assertEqual(len(recorded_api_pid), 1)
            self.assertIsNone(rv3.inspect_process(recorded_api_pid[0], REPO_ROOT))

    def test_22_v3_ast_contains_zero_forbidden_ml_or_research_imports(self) -> None:
        tree = ast.parse(self.v3_script.read_text(encoding="utf-8"), filename=str(self.v3_script))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertFalse(alias.name.startswith(FORBIDDEN_ML_IMPORTS), alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                self.assertFalse(node.module.startswith(FORBIDDEN_ML_IMPORTS), node.module)

    def test_23_local_pinned_digests_match_accepted_f4_product(self) -> None:
        self.assertEqual(rv3.compute_local_pinned_digests(REPO_ROOT), rv3.EXPECTED_PINNED_DIGESTS)

    def test_24_redact_secrets_scrubs_all_credentials(self) -> None:
        raw = "ConnectionStrings__Runtime=Host=127.0.0.1;Password=super_secret_pw_123"
        self.assertNotIn("super_secret_pw_123", rv3.redact_secrets(raw, ["super_secret_pw_123"]))


def reproduce_author_001_findings() -> dict:
    """Executes deterministic pure-CPU reproductions against merged `ad5202a0` author helpers
    without binding or touching any author port (`5590/4610/55438`), DB, or writable root.
    """
    findings: dict[str, dict] = {}

    # 1. Reproduce F12-B1 Case A: `ui_proc` early exit leaks alive `api_proc` + open `api_fh`
    spawned_procs: list[subprocess.Popen] = []
    captured_fhs_a: list = []
    real_popen = subprocess.Popen

    def fake_popen_case_a(cmd, *args, **kwargs):
        if kwargs.get("stdout") is not None:
            captured_fhs_a.append(kwargs["stdout"])
        if cmd and Path(str(cmd[0])).stem.lower() == "dotnet":
            p = real_popen([sys.executable, "-B", "-c", "import time; time.sleep(60)"], *args, **kwargs)
        else:
            p = real_popen([sys.executable, "-B", "-c", "import sys; sys.exit(1)"], *args, **kwargs)
        spawned_procs.append(p)
        return p

    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        try:
            with (
                mock.patch.object(author_drv, "assert_ports_unbound", return_value={"5590": [], "4610": []}),
                mock.patch.object(
                    author_drv,
                    "observe_ports",
                    side_effect=lambda ports=(5590,): {"5590": [{"owningPid": spawned_procs[0].pid}]} if spawned_procs else {"5590": []},
                ),
                mock.patch.object(author_drv.subprocess, "Popen", side_effect=fake_popen_case_a),
            ):
                raised_msg_a = ""
                api_fh_leaked_open_a = False
                try:
                    author_drv.start_api_and_ui(
                        app_conn_str="Host=127.0.0.1;Port=55438;Database=dummy",
                        ocr_enabled=True,
                        leased_gpu_uuid=author_drv.EXPECTED_GPU_UUID,
                        log_dir=td_p,
                        tag="repro-b1a",
                    )
                except RuntimeError as exc:
                    raised_msg_a = str(exc)
                    api_fh_leaked_open_a = bool(captured_fhs_a and not captured_fhs_a[0].closed)

            api_test_proc = spawned_procs[0]
            api_ident = author_drv.get_win32_process_identity(api_test_proc.pid)
            leaked_alive_a = bool(api_ident and api_ident["alive"])
        finally:
            for p in spawned_procs:
                if p.poll() is None:
                    p.kill()
                    p.wait(timeout=10)
            for fh in captured_fhs_a:
                if hasattr(fh, "close") and not fh.closed:
                    fh.close()
            cleaned_after_a = all(author_drv.get_win32_process_identity(p.pid) is None or not author_drv.get_win32_process_identity(p.pid)["alive"] for p in spawned_procs)

    # 2. Reproduce F12-B1 Case B: `api_proc` bind timeout leaks alive `api_proc`
    spawned_procs_b: list[subprocess.Popen] = []
    captured_fhs_b: list = []

    def fake_popen_case_b(cmd, *args, **kwargs):
        if kwargs.get("stdout") is not None:
            captured_fhs_b.append(kwargs["stdout"])
        p = real_popen([sys.executable, "-B", "-c", "import time; time.sleep(60)"], *args, **kwargs)
        spawned_procs_b.append(p)
        return p

    clock_vals = iter([100.0, 100.1, 146.0])
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        try:
            with (
                mock.patch.object(author_drv, "assert_ports_unbound", return_value={"5590": [], "4610": []}),
                mock.patch.object(author_drv, "observe_ports", return_value={"5590": []}),
                mock.patch.object(author_drv.subprocess, "Popen", side_effect=fake_popen_case_b),
                mock.patch.object(author_drv.time, "monotonic", side_effect=lambda: next(clock_vals, 200.0)),
            ):
                raised_msg_b = ""
                try:
                    author_drv.start_api_and_ui(
                        app_conn_str="Host=127.0.0.1;Port=55438;Database=dummy",
                        ocr_enabled=False,
                        leased_gpu_uuid="",
                        log_dir=td_p,
                        tag="repro-b1b",
                    )
                except RuntimeError as exc:
                    raised_msg_b = str(exc)

            api_b_proc = spawned_procs_b[0]
            api_b_ident = author_drv.get_win32_process_identity(api_b_proc.pid)
            leaked_alive_b = bool(api_b_ident and api_b_ident["alive"])
        finally:
            for p in spawned_procs_b:
                if p.poll() is None:
                    p.kill()
                    p.wait(timeout=10)
            for fh in captured_fhs_b:
                if hasattr(fh, "close") and not fh.closed:
                    fh.close()
            cleaned_after_b = all(
                author_drv.get_win32_process_identity(p.pid) is None or not author_drv.get_win32_process_identity(p.pid)["alive"]
                for p in spawned_procs_b
            )

    findings["F12-B1_partial_startup_orphan_process_leak"] = {
        "reproduced": leaked_alive_a and api_fh_leaked_open_a and leaked_alive_b,
        "case_a_ui_early_exit": {
            "exception": raised_msg_a,
            "api_proc_leaked_alive_after_exception": leaked_alive_a,
            "api_fh_leaked_open_after_exception": api_fh_leaked_open_a,
            "test_child_reaped_by_reviewer_harness": cleaned_after_a,
        },
        "case_b_api_bind_timeout": {
            "exception": raised_msg_b,
            "api_proc_leaked_alive_after_exception": leaked_alive_b,
            "test_child_reaped_by_reviewer_harness": cleaned_after_b,
        },
    }

    # 3. Reproduce F12-B2: `execute_live_rehearsal` stop-on-failure skips worker/port checks & `owner-lease-return.json`
    orig_read_text = Path.read_text

    def safe_mock_read_text(self_path: Path, *a, **k) -> str:
        if self_path.name == "pg-local.json":
            return '{"host":"127.0.0.1","port":55438,"appUser":"u","appPassword":"p","adminUser":"a","adminPassword":"ap"}'
        if self_path.name == "postmaster.pid":
            return "12345\n"
        return orig_read_text(self_path, *a, **k)

    def fake_start_api_and_ui(*, log_dir: Path, **kw):
        log_dir.mkdir(parents=True, exist_ok=True)
        return (
            mock.MagicMock(pid=999991, poll=lambda: 0),
            {"fh": None, "identity": {"pid": 999991}},
            mock.MagicMock(pid=999992, poll=lambda: 0),
            {"fh": None, "identity": {"pid": 999992}},
        )

    with tempfile.TemporaryDirectory() as td:
        fake_demo_root = Path(td) / "author-demo-sim"
        (fake_demo_root / "runs").mkdir(parents=True)
        fake_validated = {
            "lease_id": "WP-0012-sim-stop-on-failure",
            "gpu_uuid": author_drv.EXPECTED_GPU_UUID,
        }
        worker_check_Spy = mock.MagicMock(return_value=0)
        with (
            mock.patch.object(author_drv, "EXPECTED_DEMO_RUNTIME_ROOT", fake_demo_root),
            mock.patch.object(author_drv, "git_object_exists", return_value=True),
            mock.patch.object(author_drv, "git_bytes", return_value=b"{}"),
            mock.patch.object(author_drv, "validate_release_contract", return_value=fake_validated),
            mock.patch.object(
                author_drv,
                "inspect_readonly_q0_and_demo_roots_cpu",
                return_value={"writable_demo_root_exists": True},
            ),
            mock.patch.object(author_drv, "assert_ports_unbound", return_value={"5590": [], "4610": [], "55438": []}),
            mock.patch.object(author_drv, "get_win32_process_identity", return_value={"pid": 12345, "alive": True}),
            mock.patch.object(author_drv, "run_psql_query", return_value="0"),
            mock.patch.object(author_drv, "start_api_and_ui", side_effect=fake_start_api_and_ui),
            mock.patch.object(author_drv, "ProcessMemorySampler") as mock_sampler_cls,
            mock.patch.object(author_drv, "stop_proc"),
            mock.patch.object(author_drv, "count_ocr_worker_processes", worker_check_Spy),
            mock.patch.object(
                author_drv.subprocess,
                "run",
                side_effect=lambda argv, **kw: subprocess.CompletedProcess(
                    argv,
                    1 if "drive_rehearsal_edge.mjs" in " ".join(map(str, argv)) else 0,
                    stdout="",
                    stderr="STOP-ON-FAILURE",
                ),
            ),
            mock.patch.object(Path, "read_text", safe_mock_read_text),
        ):
            mock_sampler_cls.return_value.stop.return_value = {}
            raised_f2 = ""
            try:
                author_drv.execute_live_rehearsal(
                    release_commit="d" * 40,
                    release_path="docs/coordination/WP-0012/sim.json",
                )
            except RuntimeError as exc:
                raised_f2 = str(exc)

        lease_return_written = (
            fake_demo_root / "rehearsal-evidence" / "WP-0012-sim-stop-on-failure" / "owner-lease-return.json"
        ).exists()
        findings["F12-B2_stop_on_failure_skips_lease_return_and_worker_audit"] = {
            "reproduced": ("Live Phase A stopped/failed" in raised_f2) and (not lease_return_written) and (worker_check_Spy.call_count == 0),
            "exception": raised_f2,
            "owner_lease_return_json_written_on_failure": lease_return_written,
            "post_failure_worker_process_checks_executed": worker_check_Spy.call_count,
        }

    # 4. Reproduce F12-B3 & prose/claim discrepancies F12-D1..D4
    b3_rejected = False
    b3_err = ""
    try:
        author_drv._extract_independent_review_002_sha(
            {"independent_preparation_review_002_sha": "a" * 40}
        )
    except author_drv.RehearsalGuardError as exc:
        b3_rejected = True
        b3_err = str(exc)

    cli_shorthand_cp = subprocess.run(
        [
            sys.executable,
            "-B",
            str(AUTHOR_HELPERS_DIR / "run_wp0012_rehearsal.py"),
            "--execute-live",
            "--release",
            "dummy.json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )

    edge_src = (AUTHOR_HELPERS_DIR / "drive_rehearsal_edge.mjs").read_text(encoding="utf-8")
    findings["F12-B3_and_001_prose_discrepancies"] = {
        "F12-B3_handoff_key_independent_preparation_review_002_sha_rejected": b3_rejected,
        "F12-B3_error": b3_err,
        "F12-D1_cli_release_shorthand_flag_rejected_returncode": cli_shorthand_cp.returncode,
        "F12-D2_edge_modes_are_live_phase_a_and_b_not_phase1_phase2": (
            "mode === 'live-phase-a'" in edge_src
            and "mode === 'live-phase-b-reopen'" in edge_src
            and "live-phase1" not in edge_src
        ),
        "F12-D3_002_review_sha_not_checked_via_merge_base_is_ancestor": (
            "git_is_ancestor(root, rev_sha" not in (AUTHOR_HELPERS_DIR / "run_wp0012_rehearsal.py").read_text(encoding="utf-8")
        ),
        "F12-D4_phase_b_ocrEnabledDuringReopen_is_literal_without_workerEnabled_assertion": (
            "ocrEnabledDuringReopen: false" in edge_src and "workerEnabled" not in edge_src
        ),
    }

    if not (
        findings["F12-B1_partial_startup_orphan_process_leak"]["reproduced"]
        and findings["F12-B2_stop_on_failure_skips_lease_return_and_worker_audit"]["reproduced"]
        and findings["F12-B3_and_001_prose_discrepancies"]["F12-B3_handoff_key_independent_preparation_review_002_sha_rejected"]
    ):
        raise AssertionError(f"Expected deterministic reproduction of F12-B1..B3, got: {findings}")

    return findings


def verify_author_001_artifacts_and_run_18_tests() -> dict:
    # 1. Verify exact commit lineage & diffs
    diff_deliv = run_git("diff", "--name-only", AUTHORITY_WP0012_SHA, AUTHOR_DELIVERABLE_SHA).splitlines()
    diff_ev = run_git("diff", "--name-only", AUTHOR_DELIVERABLE_SHA, AUTHOR_EVIDENCE_SHA).splitlines()
    diff_pub = run_git("diff", "--name-only", AUTHOR_EVIDENCE_SHA, AUTHOR_PUBLICATION_SHA).splitlines()

    if len(diff_deliv) != 9 or not all(p.startswith("docs/implementation/WP-0012/eld-f4-implementer/") for p in diff_deliv):
        raise AssertionError(f"Unexpected author deliverable diff: {diff_deliv}")
    if len(diff_ev) != 14 or not all(p.startswith("docs/implementation/WP-0012/eld-f4-implementer/") for p in diff_ev):
        raise AssertionError(f"Unexpected author evidence diff: {diff_ev}")
    if diff_pub != ["docs/agent-reports/eld-f4-implementer/WP-0012/001_2026-11-17_implementation_eld-f4-implementer.md"]:
        raise AssertionError(f"Author 001 publication commit is not report-only: {diff_pub}")

    # 2. Verify inventory.json SHA-256s, log SHA-256s, node --check, AST, links, & zero secrets
    inv = json.loads((REPO_ROOT / "docs/implementation/WP-0012/eld-f4-implementer/inventory.json").read_text(encoding="utf-8"))
    for entry in inv["base_to_deliverable_paths"]:
        fp = REPO_ROOT / entry["path"]
        if fp.stat().st_size != entry["bytes"] or rv3.file_sha256_hex(fp) != entry["sha256"]:
            raise AssertionError(f"Author deliverable hash mismatch: {entry['path']}")
    for entry in inv["post_freeze_evidence_paths"]:
        fp = REPO_ROOT / entry["path"]
        if fp.stat().st_size != entry["bytes"] or rv3.file_sha256_hex(fp) != entry["sha256"]:
            raise AssertionError(f"Author evidence hash mismatch: {entry['path']}")

    node_check = rv3.run_cmd(
        ["node", "--check", str(AUTHOR_HELPERS_DIR / "drive_rehearsal_edge.mjs")],
        cwd=REPO_ROOT,
    )
    if node_check.returncode != 0:
        raise AssertionError(f"node --check failed on drive_rehearsal_edge.mjs: {node_check.stderr}")

    for pyf in sorted(AUTHOR_HELPERS_DIR.glob("*.py")):
        py_compile.compile(str(pyf), doraise=True)
        tree = ast.parse(pyf.read_text(encoding="utf-8"), filename=str(pyf))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(FORBIDDEN_ML_IMPORTS):
                        raise AssertionError(f"Forbidden import {alias.name} in {pyf}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith(FORBIDDEN_ML_IMPORTS):
                    raise AssertionError(f"Forbidden import {node.module} in {pyf}")

    settings = json.loads((REPO_ROOT / ".local/secrets/pg-local.json").read_text(encoding="utf-8"))
    reviewer_secrets = [
        str(settings["adminPassword"]),
        str(settings["migratorPassword"]),
        str(settings["appPassword"]),
    ]

    link_count = 0
    for md_rel in (
        "docs/agent-reports/eld-f4-implementer/WP-0012/001_2026-11-17_implementation_eld-f4-implementer.md",
        "docs/implementation/WP-0012/eld-f4-implementer/RUNBOOK.md",
        "docs/implementation/WP-0012/eld-f4-implementer/retained-failures/README.md",
    ):
        md_fp = REPO_ROOT / md_rel
        txt = md_fp.read_text(encoding="utf-8")
        for s in reviewer_secrets:
            if s and s in txt:
                raise AssertionError(f"Secret found in {md_rel}")
        for m in MD_LINK_RE.finditer(txt):
            tgt = m.group(1)
            if tgt.startswith(("http://", "https://", "mailto:", "conversation://", "file://")):
                continue
            if not (md_fp.parent / tgt).resolve().exists():
                raise AssertionError(f"Broken link in {md_rel}: {tgt}")
            link_count += 1

    # 3. Execute all 18 Wp0012PreparationGuardTests pinned to author deliverable SHA ad5202a0 in memory
    orig_git_stdout = author_drv.git_stdout

    def pinned_author_git_stdout(root: Path, args: list[str]) -> str:
        if args == ["rev-parse", "HEAD"]:
            return AUTHOR_DELIVERABLE_SHA
        if len(args) >= 4 and args[:2] == ["diff", "--name-only"] and args[2] == AUTHORITY_WP0012_SHA:
            return orig_git_stdout(root, ["diff", "--name-only", AUTHORITY_WP0012_SHA, AUTHOR_DELIVERABLE_SHA])
        return orig_git_stdout(root, args)

    buf = io.StringIO()
    with mock.patch.object(author_drv, "git_stdout", side_effect=pinned_author_git_stdout):
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(author_val.Wp0012PreparationGuardTests)
        res = unittest.TextTestRunner(stream=buf, verbosity=2).run(suite)
    if not res.wasSuccessful() or res.testsRun != 18:
        raise AssertionError(f"Author 18 guard tests failed:\n{buf.getvalue()}")

    return {
        "author_deliverable_sha": AUTHOR_DELIVERABLE_SHA,
        "author_evidence_sha": AUTHOR_EVIDENCE_SHA,
        "author_publication_sha": AUTHOR_PUBLICATION_SHA,
        "deliverable_file_count": len(diff_deliv),
        "evidence_file_count": len(diff_ev),
        "publication_report_only": True,
        "markdown_links_verified": link_count,
        "author_guard_unit_tests_run": res.testsRun,
        "author_guard_unit_tests_passed": res.wasSuccessful(),
        "node_check_passed": True,
        "ast_ml_import_violations": 0,
        "author_unit_test_log": buf.getvalue(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument(
        "--output",
        default="docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/observations/author-001-and-v3-verification.json",
    )
    parser.add_argument(
        "--log-output",
        default="docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/observations/logs/verify-author-001-and-v3.log",
    )
    parser.add_argument(
        "--resource-return-output",
        default="docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/resource-return.json",
    )
    args = parser.parse_args(argv)

    porcelain = run_git("status", "--porcelain", "--untracked-files=all")
    if args.require_clean and porcelain != "":
        raise AssertionError(f"Worktree must be clean before decisive /002 verification:\n{porcelain}")

    executing_head = run_git("rev-parse", "HEAD")

    # 1. Verify initial reviewer preparation (7f3f8626) is 100% untouched
    prep_diff = run_git(
        "diff",
        "--name-only",
        REVIEWER_INITIAL_PREP_PUB_SHA,
        executing_head,
        "--",
        "docs/reviews/WP-0012/eld-f4-reviewer/preparation",
    )
    if prep_diff != "":
        raise AssertionError(f"Initial reviewer preparation was modified: {prep_diff}")

    # 2. Audit author /001 artifacts & run author's 18 guard tests
    author_audit = verify_author_001_artifacts_and_run_18_tests()
    author_ut_log = author_audit.pop("author_unit_test_log")

    # 3. Deterministically reproduce F12-B1, F12-B2, F12-B3, & F12-D1..D4
    reproduced_findings = reproduce_author_001_findings()

    # 4. Run 24 reviewer v3 guard reconciliation tests
    v3_buf = io.StringIO()
    v3_suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReviewerV3GuardReconciliationTests)
    v3_res = unittest.TextTestRunner(stream=v3_buf, verbosity=2).run(v3_suite)
    if not v3_res.wasSuccessful() or v3_res.testsRun != 24:
        raise AssertionError(f"Reviewer v3 guard tests failed:\n{v3_buf.getvalue()}")

    # 5. Verify stopped services, idle ports (reviewer + author observed read-only), and empty demo runs dir
    ports_rev = rv3.observe_ports(rv3.REVIEWER_PORTS, REPO_ROOT)
    pg_ctl = REPO_ROOT / ".local/tools/pgsql-18.7-1/bin/pg_ctl.exe"
    pg_rc = rv3.run_cmd([str(pg_ctl), "status", "-D", str(REPO_ROOT / ".local/postgres-data")], cwd=REPO_ROOT).returncode
    runs_dir = rv3.WRITABLE_DEMO_ROOT / "runs"
    run_entries = sorted(p.name for p in runs_dir.iterdir()) if runs_dir.is_dir() else []

    if any(len(ports_rev[str(p)]) != 0 for p in rv3.REVIEWER_PORTS) or pg_rc != 3 or run_entries != []:
        raise AssertionError(f"Unexpected active reviewer resource: ports={ports_rev}, pg_rc={pg_rc}, runs={run_entries}")

    out_path = (REPO_ROOT / args.output).resolve()
    log_path = (REPO_ROOT / args.log_output).resolve()
    rr_path = (REPO_ROOT / args.resource_return_output).resolve()
    for p in (out_path.parent, log_path.parent, rr_path.parent):
        p.mkdir(parents=True, exist_ok=True)

    combined_log = (
        "=== Author Wp0012PreparationGuardTests (18 tests, pinned to ad5202a0) ===\n"
        + author_ut_log
        + "\n=== ReviewerV3GuardReconciliationTests (24 tests) ===\n"
        + v3_buf.getvalue()
    )
    log_path.write_text(combined_log, encoding="utf-8", newline="\n")

    rr_payload = {
        "schema": "eledgercare.wp-0012.reviewer-002-resource-return/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "phase": "WP-0012 / 002 CPU preparation review & own-guard reconciliation",
        "live_model_or_gpu_executed": False,
        "author_resources_touched": False,
        "reviewer_ports_after": ports_rev,
        "pg_ctl_status_exit_code": pg_rc,
        "retained_cluster_present": (REPO_ROOT / ".local/postgres-data/PG_VERSION").is_file(),
        "writable_demo_root": str(rv3.WRITABLE_DEMO_ROOT),
        "writable_demo_run_dir_count": len(run_entries),
        "initial_preparation_7f3f8626_untouched": True,
    }
    rr_path.write_text(json.dumps(rr_payload, indent=2) + "\n", encoding="utf-8", newline="\n")

    summary_payload = {
        "schema": "eledgercare.wp-0012.reviewer-002-verification/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "conversation_id": "61105d43-7706-45f2-9176-69d3256248e0",
        "model": "gemini-4-carbon-high",
        "effort": "high",
        "executing_head_sha": executing_head,
        "live_rehearsal_executed": False,
        "model_or_venv_imported": False,
        "disposition_on_author_001": "changes-requested",
        "initial_reviewer_preparation_preserved": {
            "publication_sha": REVIEWER_INITIAL_PREP_PUB_SHA,
            "helper_sha": REVIEWER_INITIAL_PREP_HELPER_SHA,
            "untouched": True,
        },
        "author_001_audit": author_audit,
        "reproduced_author_findings": reproduced_findings,
        "reviewer_v3_guard_reconciliation": {
            "helper_path": "docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/helpers/run_wp0012_reviewer_rehearsal_v3.py",
            "helper_sha256_lf": sha256_hex((REVIEWER_HELPERS_DIR / "run_wp0012_reviewer_rehearsal_v3.py").read_bytes().replace(b"\r\n", b"\n")),
            "unit_tests_run": v3_res.testsRun,
            "unit_tests_passed": v3_res.wasSuccessful(),
            "reconciled_root_concerns": ["RG-01_exact_git_release_and_upstream_bindings", "RG-02_wddm_vs_competing_model_ownership", "RG-03_refusing_overwrite_new_destinations"],
        },
    }
    out_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
