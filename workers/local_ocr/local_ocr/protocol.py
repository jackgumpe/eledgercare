"""Frozen unmodified inference protocol, digest helpers, and failure taxonomy for F2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import ENVELOPE_SCHEMA, REQUEST_SCHEMA, WORKER_ID

WORKER_ROOT = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = WORKER_ROOT / "manifests"
MODEL_MANIFEST_PATH = MANIFESTS_DIR / "model-files.json"
DEPENDENCY_LOCK_PATH = MANIFESTS_DIR / "dependency-lock.json"

MODEL_REPO_ID = "baidu/Unlimited-OCR-2"
MODEL_REVISION = "0480966938291445591f69f08a13b041c073a96a"
PROMPT = "Multi page parsing."
PAGE_TOKEN_ID = 128827
RENDER_DPI = 300
RENDER_SCALE = 300.0 / 72.0
MAX_PAGES_PROFILE = 3
MAX_RASTER_AXIS_PX = 6000
MAX_RAW_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_LOG_BYTES = 64 * 1024 * 1024
MIN_FREE_DISK_BYTES = 20 * 1024 * 1024 * 1024
MAX_RUNTIME_ROOT_BYTES = 4 * 1024 * 1024 * 1024

FIXED_CALL_KWARGS: dict[str, object] = {
    "crop_mode": False,
    "save_results": False,
    "output_path": "",
    "temperature": 0.0,
    "max_length": 131072,
    "max_page_tokens": 20000,
    "page_count_guard": True,
    "image_size": 640,
    "base_size": 1024,
    "max_crops": 16,
    "no_repeat_ngram_size": 35,
    "ngram_whitelist_token_ids": None,
    "dash_topm": 16,
    "tps_interval": 0,
    "test_compress": False,
    "eval_mode": False,
}

TOKENS_PER_PAGE = 8000

FAILURE_CODES: dict[str, str] = {
    "invalid_request": "The worker request manifest was malformed or failed validation.",
    "environment_isolation_failed": "The isolated offline worker environment check failed.",
    "storage_limit_exceeded": "Disk free-space floor or runtime-root ceiling check failed.",
    "platform_mismatch": "Host Python, OS, or leased CUDA GPU did not match the frozen lock.",
    "dependency_lock_mismatch": "Installed Python packages did not match the 32-package lock.",
    "model_integrity_failed": "Model runtime files, notice, or module cache failed digest verification.",
    "safety_violation": "Static AST safety check or runtime save/eval tripwire failed.",
    "input_integrity_failed": "Materialized PDF bytes or page count disagreed with committed metadata.",
    "render_failed": "300-DPI PDFium RGB rendering failed or exceeded raster dimension bounds.",
    "context_budget_exceeded": "Prompt tokens plus max_new_tokens exceeded the model context window.",
    "model_output_truncated": "Model generation stopped before completion (length limit reached).",
    "page_count_mismatch": "Native output page count or <PAGE> markers disagreed with input pages.",
    "output_cap_exceeded": "Raw UTF-8 model output exceeded the 16 MiB cap.",
    "telemetry_mismatch": "Required native inference result or fallback telemetry was ambiguous.",
    "cuda_oom": "GPU or host out-of-memory occurred during model load or inference.",
    "worker_runtime_error": "Unhandled exception inside the local OCR worker.",
}


class WorkerError(Exception):
    """Classified fail-closed worker error with safe code and bounded diagnostic detail."""

    def __init__(self, code: str, detail: str, extra: dict | None = None):
        if code not in FAILURE_CODES:
            raise ValueError(f"Unknown failure code: {code!r}")
        super().__init__(detail)
        self.code = code
        self.detail = detail[:500]
        self.extra = extra or {}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1_bytes(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    h = hashlib.sha1()
    h.update(header)
    h.update(data)
    return h.hexdigest()


def file_digests(path: Path, *, include_git_blob: bool = False) -> dict:
    h256 = hashlib.sha256()
    hgit = hashlib.sha1() if include_git_blob else None
    size = path.stat().st_size
    if hgit is not None:
        hgit.update(f"blob {size}\0".encode("ascii"))
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h256.update(chunk)
            if hgit is not None:
                hgit.update(chunk)
    out = {"size": size, "sha256": h256.hexdigest()}
    if hgit is not None:
        out["git_blob_sha1"] = hgit.hexdigest()
    return out


def compute_worker_source_sha256(worker_root: Path = WORKER_ROOT) -> str:
    """Deterministic SHA-256 across all production worker .py files (CRLF->LF normalized)."""
    py_files = [
        worker_root / "run_worker.py",
        *sorted((worker_root / "local_ocr").glob("*.py"), key=lambda p: p.name),
    ]
    h = hashlib.sha256()
    for p in py_files:
        rel = p.relative_to(worker_root).as_posix()
        normalized = p.read_bytes().replace(b"\r\n", b"\n")
        file_sha = hashlib.sha256(normalized).hexdigest()
        h.update(f"{rel}:{len(normalized)}:{file_sha}\n".encode("utf-8"))
    return h.hexdigest()


def call_timeout_for_pages(page_count: int) -> int:
    if page_count == 1:
        return 1800
    if page_count == 2:
        return 2700
    if page_count == 3:
        return 3600
    raise WorkerError("input_integrity_failed", f"Unsupported page_count={page_count}; expected 1..3.")


def build_call_kwargs(page_count: int) -> dict[str, object]:
    if page_count < 1 or page_count > MAX_PAGES_PROFILE:
        raise WorkerError("input_integrity_failed", f"page_count {page_count} outside 1..{MAX_PAGES_PROFILE}.")
    kwargs = dict(FIXED_CALL_KWARGS)
    kwargs["max_new_tokens"] = TOKENS_PER_PAGE * page_count
    kwargs["ngram_window"] = 1024 if page_count > 1 else 128
    validate_call_kwargs(kwargs, page_count)
    return kwargs


def validate_call_kwargs(kwargs: dict[str, object], page_count: int) -> None:
    expected_keys = set(FIXED_CALL_KWARGS) | {"max_new_tokens", "ngram_window"}
    if set(kwargs) != expected_keys:
        raise WorkerError("safety_violation", "Call kwargs keys diverge from frozen Q0/F2 contract.")
    for k, want in FIXED_CALL_KWARGS.items():
        got = kwargs[k]
        if type(got) is not type(want) or got != want:
            raise WorkerError("safety_violation", f"Frozen kwarg {k} diverged from contract.")
    want_tokens = TOKENS_PER_PAGE * page_count
    want_window = 1024 if page_count > 1 else 128
    if type(kwargs["max_new_tokens"]) is not int or kwargs["max_new_tokens"] != want_tokens:
        raise WorkerError("safety_violation", "max_new_tokens diverged from 8000 * pages.")
    if type(kwargs["ngram_window"]) is not int or kwargs["ngram_window"] != want_window:
        raise WorkerError("safety_violation", "ngram_window diverged from frozen 128/1024 rule.")


def compute_config_digest(page_count: int) -> str:
    payload = {
        "worker_id": WORKER_ID,
        "envelope_schema": ENVELOPE_SCHEMA,
        "request_schema": REQUEST_SCHEMA,
        "model_repo_id": MODEL_REPO_ID,
        "model_revision": MODEL_REVISION,
        "prompt": PROMPT,
        "render_dpi": RENDER_DPI,
        "call_kwargs": build_call_kwargs(page_count),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256_bytes(encoded)
