"""Failure classes and outcome records. A Q0 record never carries an accuracy score."""

from __future__ import annotations

import re
from typing import Any

from . import SCHEMA_VERSION

# Every class is a runtime/qualification result, never an OCR quality result.
FAILURE_CLASSES = {
    "DEPENDENCY_LOCK_PENDING": "Exact dependency lock is not final (awaiting WP-0005 /001 and review).",
    "EXECUTION_NOT_RELEASED": "No coordinator runtime/GPU-lease release record was supplied or it does not match.",
    "UNSUPPORTED_PLATFORM": "Host, interpreter, CUDA runtime, device or capability differs from the frozen lock.",
    "DEPENDENCY_MISMATCH": "Installed distributions differ from the lock, or a forbidden optional backend is importable.",
    "STORAGE_NOT_OWNED": "Storage root or a writable path is not the owned task root, or budget does not fit.",
    "HASH_MISMATCH": "A fixture, model, tokenizer, custom-code, module-cache or raster digest differs from its pin.",
    "UNEXPECTED_ARTIFACT": "Unexpected file (for example an extra .py) present in a verified directory.",
    "HOLDOUT_ACCESS_REFUSED": "A holdout family or an expected-value path was requested.",
    "SAFETY_VIOLATION": "save_results/output_path freeze broken, or the eval-containing save path was entered.",
    "SOURCE_PATCH_REQUIRED": "The unmodified source cannot run without editing; strict-baseline blocker.",
    "IMPORT_FAILURE": "Native dynamic-module import or dependency import failed.",
    "LOAD_FAILURE": "Tokenizer/model load or device placement failed.",
    "RENDER_CONTRACT_MISMATCH": "Renderer version/API, page count, dimensions or raster bytes differ from the contract.",
    "CONTEXT_BUDGET_EXCEEDED": "prompt_len + max_new_tokens exceeds max_length; recorded as unsupported, never truncated.",
    "OOM": "CUDA or host out-of-memory.",
    "TIMEOUT": "A phase exceeded its frozen wall-clock budget; the supervisor terminated its own child.",
    "SEVERE_STALL": "No native forward progress within the frozen stall window (suspected WDDM paging stall).",
    "LOG_CAP_EXCEEDED": "Child output exceeded the bounded log cap; the supervisor terminated its own child.",
    "TRUNCATION": "Native finish_reason is 'length' (output budget or max_length reached).",
    "PAGE_COUNT_MISMATCH": "Native num_pages_out differs from expected_pages / input page count.",
    "NONDETERMINISTIC_OUTPUT": "The two warm repeats of one fixture produced different token ids.",
    "TELEMETRY_UNSUPPORTED": "A required observation mechanism is unavailable; no silent substitute is used.",
    "RUNTIME_ERROR": "Any other exception from the native call; traceback preserved.",
    "CHILD_EXIT_NONZERO": "Execution child exited without a valid result record.",
}

QUALIFIED = "QUALIFIED_RUNTIME_OBSERVATION"
BLOCKED = "BLOCKED"
NOT_QUALIFIED = "NOT_QUALIFIED"

_SCORE_TOKENS = {"accuracy", "score", "scores", "cer", "wer", "f1", "precision", "recall", "matched"}


class _ScoreKey:
    """Key names are split on '_', '-' and camel case; any score token marks a score-like key."""

    _split = re.compile(r"[_\-\s]+|(?<=[a-z0-9])(?=[A-Z])")

    def search(self, key: str) -> bool:
        return any(tok.lower() in _SCORE_TOKENS for tok in self._split.split(key) if tok)


_SCORE_KEY = _ScoreKey()


class Q0Failure(Exception):
    """A classified, fail-closed stop. Never caught to continue silently."""

    def __init__(self, failure_class: str, detail: str, evidence: Any = None):
        if failure_class not in FAILURE_CLASSES:
            raise ValueError(f"unknown failure class {failure_class!r}")
        super().__init__(f"{failure_class}: {detail}")
        self.failure_class = failure_class
        self.detail = detail
        self.evidence = evidence

    def as_record(self) -> dict:
        return {
            "failure_class": self.failure_class,
            "description": FAILURE_CLASSES[self.failure_class],
            "detail": self.detail,
            "evidence": self.evidence,
        }


def assert_no_score(record: Any, path: str = "$") -> None:
    """Reject any non-null score-like field anywhere in a record (the only allowed one is accuracy_score: null)."""
    if isinstance(record, dict):
        for key, value in record.items():
            here = f"{path}.{key}"
            if isinstance(key, str) and _SCORE_KEY.search(key) and value is not None:
                raise ValueError(f"score-like field with a value is forbidden in Q0 records: {here}")
            assert_no_score(value, here)
    elif isinstance(record, (list, tuple)):
        for i, value in enumerate(record):
            assert_no_score(value, f"{path}[{i}]")


def make_outcome(status: str, *, failures: list[dict] | None = None, checks: dict | None = None,
                 observations: list | None = None, context: dict | None = None) -> dict:
    if status not in (QUALIFIED, BLOCKED, NOT_QUALIFIED):
        raise ValueError(status)
    failures = failures or []
    if status == QUALIFIED and failures:
        raise ValueError("a qualified outcome cannot carry failures")
    if status != QUALIFIED and not failures:
        raise ValueError("a non-qualified outcome must name at least one failure class")
    record = {
        "schema": SCHEMA_VERSION,
        "status": status,
        "accuracy_score": None,
        "q0_scope_note": "Q0 is runtime qualification only; no OCR quality value is computed, and a failed run is a blocker, not 0%.",
        "failures": failures,
        "checks": checks or {},
        "observations": observations or [],
        "context": context or {},
    }
    assert_no_score({k: v for k, v in record.items() if k != "accuracy_score"})
    return record
