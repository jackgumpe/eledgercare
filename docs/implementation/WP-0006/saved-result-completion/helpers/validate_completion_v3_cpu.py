"""CPU-only post-freeze syntax and contract validator for WP-0006 saved-result completion v3."""

from __future__ import annotations

import ast
import io
import json
import py_compile
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest

SCRIPT_PATH = Path(__file__).resolve()
HELPERS_DIR = SCRIPT_PATH.parent
COMP_DIR = HELPERS_DIR.parent
ROOT = COMP_DIR.parent.parent.parent.parent

if str(HELPERS_DIR) not in sys.path:
    sys.path.insert(0, str(HELPERS_DIR))

import run_f2_saved_result_completion_v3 as v3  # noqa: E402

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


class SavedResultCompletionV3Tests(unittest.TestCase):
    def test_01_validate_completion_contract_passes_on_clean_head(self) -> None:
        res = v3.validate_completion_contract(ROOT, v3.EXPECTED_AUTHORITY_COMMIT)
        self.assertEqual(res["authority_commit"], "6dec634c81a4b2cbc1b492541697958cc0f76232")
        self.assertEqual(res["source_commit"], "8a73b7a5dab51e3ccf803aceedded4929529dd35")
        self.assertEqual(res["v2_evidence_base"], "48e8896d53fa001bba55276ac244f4adee377587")
        self.assertEqual(len(res["committed_helpers"]), 2)

    def test_02_rejects_wrong_authority_commit(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Unexpected authority commit"):
            v3.validate_completion_contract(ROOT, "e28471997f425b0e074f65432dccc3abf2116490")

    def test_03_node_ui_status_label_mapping_matches_angular_receipt_ts(self) -> None:
        node_code = (
            "import { UI_STATUS_LABELS, mapApiStatusToUiLabel } from './docs/implementation/WP-0006/saved-result-completion/helpers/verify_saved_results_ui_v3.mjs';"
            "console.log(JSON.stringify({labels: UI_STATUS_LABELS, interrupted: mapApiStatusToUiLabel('interrupted'), completed: mapApiStatusToUiLabel('completed')}));"
        )
        out = subprocess.check_output(["node", "--input-type=module", "-e", node_code], cwd=ROOT, text=True).strip()
        parsed = json.loads(out)
        self.assertEqual(parsed["interrupted"], "Extraction interrupted")
        self.assertEqual(parsed["completed"], "Completed (unreviewed)")
        self.assertEqual(parsed["labels"], v3.UI_STATUS_LABELS)

    def test_04_pinned_doc3_expects_exact_extraction_interrupted_and_completed_labels(self) -> None:
        doc3 = v3.PINNED_SAVED_DOCUMENTS[2]
        self.assertEqual(doc3["documentId"], "01a1e511-ae58-72ad-a79e-0b359340f539")
        self.assertEqual(doc3["expectedResultId"], "01a1e514-f736-732b-a901-b75406b5d076")
        self.assertEqual(doc3["expectedAttempts"][0]["attemptId"], "01a1e511-ae6a-74cf-b0c9-d6e5933a22ea")
        self.assertEqual(doc3["expectedAttempts"][0]["apiStatus"], "interrupted")
        self.assertEqual(doc3["expectedAttempts"][0]["expectedUiLabel"], "Extraction interrupted")
        self.assertEqual(doc3["expectedAttempts"][1]["attemptId"], "01a1e512-6a6d-7554-a1b6-352f03223bda")
        self.assertEqual(doc3["expectedAttempts"][1]["apiStatus"], "completed")
        self.assertEqual(doc3["expectedAttempts"][1]["expectedUiLabel"], "Completed (unreviewed)")

    def test_05_refuses_overwriting_historical_scratch_dirs(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(HELPERS_DIR / "run_f2_saved_result_completion_v3.py"),
                "--dry-run-validate",
                "--scratch-dir",
                str(ROOT / ".scratch" / "stage2-runtime-v2"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Refusing to write inside preserved scratch directory", proc.stderr)

    def test_06_zero_cuda_ml_queries_post_or_external_root_references(self) -> None:
        py_src = (HELPERS_DIR / "run_f2_saved_result_completion_v3.py").read_text(encoding="utf-8")
        mjs_src = (HELPERS_DIR / "verify_saved_results_ui_v3.mjs").read_text(encoding="utf-8")
        py_tree = ast.parse(py_src)
        docstrings: set[int] = set()
        for parent in ast.walk(py_tree):
            if isinstance(parent, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and parent.body:
                first_stmt = parent.body[0]
                if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Constant) and isinstance(first_stmt.value.value, str):
                    docstrings.add(id(first_stmt.value))
        for node in ast.walk(py_tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
                val = node.value
                for forbidden_tok in ("nvidia-smi", "eLedgerCare-F2", "eLedgerCare-Q0", "method=\"POST\"", "INSERT ", "UPDATE ", "DELETE "):
                    self.assertNotIn(forbidden_tok, val)
        for forbidden_mjs in ("method: 'POST'", 'method: "POST"', "nvidia-smi", "eLedgerCare-F2", "eLedgerCare-Q0"):
            self.assertNotIn(forbidden_mjs, mjs_src)
        leaked = [m for m in sys.modules if any(m == p or m.startswith(p + ".") for p in FORBIDDEN_IMPORT_PREFIXES)]
        self.assertEqual(leaked, [])


def main() -> int:
    porcelain = v3.git_stdout(ROOT, ["status", "--porcelain"])
    if porcelain != "":
        raise RuntimeError(f"Freeze violation: working tree must be clean before validation: {porcelain!r}")
    head_sha = v3.git_stdout(ROOT, ["rev-parse", "HEAD"]).lower()

    val_dir = ROOT / ".scratch" / "stage2-saved-result-completion" / "validation"
    if val_dir.exists():
        shutil.rmtree(val_dir)
    val_dir.mkdir(parents=True, exist_ok=True)

    steps = []

    # Step 01: Python py_compile + AST import check
    t0 = time.perf_counter()
    buf1 = io.StringIO()
    for pf in (HELPERS_DIR / "run_f2_saved_result_completion_v3.py", SCRIPT_PATH):
        tmp_pyc = val_dir / f"{pf.stem}.pyc"
        py_compile.compile(str(pf), cfile=str(tmp_pyc), doraise=True)
        tmp_pyc.unlink(missing_ok=True)
        t = ast.parse(pf.read_text(encoding="utf-8"))
        for n in ast.walk(t):
            if isinstance(n, ast.Import):
                for a in n.names:
                    if a.name.startswith(FORBIDDEN_IMPORT_PREFIXES):
                        raise RuntimeError(f"Forbidden import {a.name}")
            elif isinstance(n, ast.ImportFrom) and n.module and n.module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                raise RuntimeError(f"Forbidden from-import {n.module}")
        buf1.write(f"[PASS] py_compile + AST import safety: {pf.relative_to(ROOT).as_posix()}\n")
    dur1 = round((time.perf_counter() - t0) * 1000)
    raw1 = buf1.getvalue().encode("utf-8")
    (val_dir / "01-python-compile-and-ast.log").write_bytes(raw1)
    steps.append({"step": "01-python-compile-and-ast", "exit_code": 0, "duration_ms": dur1, "sha256": v3.sha256_bytes(raw1)})

    # Step 02: Node syntax check
    t0 = time.perf_counter()
    np = subprocess.run(["node", "--check", str(HELPERS_DIR / "verify_saved_results_ui_v3.mjs")], cwd=ROOT, capture_output=True, text=True)
    dur2 = round((time.perf_counter() - t0) * 1000)
    raw2 = f"$ node --check verify_saved_results_ui_v3.mjs\nexit_code={np.returncode}\n{np.stdout}{np.stderr}".replace("\r\n", "\n").encode("utf-8")
    (val_dir / "02-node-syntax-check.log").write_bytes(raw2)
    if np.returncode != 0:
        raise RuntimeError(raw2.decode("utf-8"))
    steps.append({"step": "02-node-syntax-check", "exit_code": 0, "duration_ms": dur2, "sha256": v3.sha256_bytes(raw2)})

    # Step 03: Unit tests
    t0 = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SavedResultCompletionV3Tests)
    ubuf = io.StringIO()
    ures = unittest.TextTestRunner(stream=ubuf, verbosity=2).run(suite)
    dur3 = round((time.perf_counter() - t0) * 1000)
    raw3 = ubuf.getvalue().replace("\r\n", "\n").encode("utf-8")
    (val_dir / "03-completion-v3-unit-tests.log").write_bytes(raw3)
    if not ures.wasSuccessful():
        raise RuntimeError(ubuf.getvalue())
    steps.append({"step": "03-completion-v3-unit-tests", "exit_code": 0, "tests_run": ures.testsRun, "duration_ms": dur3, "sha256": v3.sha256_bytes(raw3)})

    summary = {
        "schema": "eledgercare.wp-0006.saved-result-completion-cpu-validation/3",
        "validated_utc": v3.utc_now(),
        "frozen_helper_commit": head_sha,
        "steps": steps,
        "total_unittest_passed": ures.testsRun,
    }
    v3.write_json_lf(val_dir / "cpu-validation-summary-v3.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
