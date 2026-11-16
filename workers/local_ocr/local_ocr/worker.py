"""Production F2 worker execution and atomic eledgercare.local-extraction/1 envelope writer."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata as importlib_md
import importlib.util
import json
import os
import platform
import sys
import time
from pathlib import Path

from . import ENVELOPE_SCHEMA, REQUEST_SCHEMA, WORKER_ID
from .env_guard import (
    WorkerHeartbeat,
    audit_worker_environment,
    is_inside,
    verify_storage_guards,
)
from .observer import InferenceMonitor, SafetyTripwire, resolve_monitoring_targets
from .pdf_render import read_and_render_pdf, verify_renderer_identity
from .protocol import (
    DEPENDENCY_LOCK_PATH,
    FAILURE_CODES,
    MAX_RAW_OUTPUT_BYTES,
    MODEL_MANIFEST_PATH,
    MODEL_REPO_ID,
    MODEL_REVISION,
    PAGE_TOKEN_ID,
    PROMPT,
    WorkerError,
    build_call_kwargs,
    call_timeout_for_pages,
    compute_config_digest,
    compute_worker_source_sha256,
    sha256_bytes,
)
from .verify_runtime import (
    is_reparse_or_link,
    load_json_checked,
    normalize_and_verify_model_dir,
    verify_dependency_lock,
    verify_loaded_module_cache,
    verify_model_sources_ast_safety,
    verify_platform_and_gpu,
)

DIAGNOSTIC_PREVIEW_CAP_BYTES = 65536


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_exclusive_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite output artifact: {path}")
    partial = path.with_name(path.name + ".partial")
    with open(partial, "xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.rename(partial, path)


def write_envelope_atomic(path: Path, envelope: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(envelope, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _validate_request(req: dict, request_path: Path) -> tuple[Path, Path, Path]:
    if req.get("schema") != REQUEST_SCHEMA:
        raise WorkerError("invalid_request", f"Unsupported request schema: {req.get('schema')!r}")
    for key in (
        "document_id", "job_id", "attempt_id", "fencing_token",
        "writable_runtime_root", "readonly_q0_root", "input_pdf_path",
        "expected_input_sha256", "expected_input_byte_length", "expected_page_count",
        "model_dir", "notice_dir", "leased_gpu_uuid",
        "expected_model_manifest_sha256", "expected_dependency_lock_sha256",
        "expected_worker_source_sha256", "expected_worker_config_sha256",
    ):
        if key not in req or req[key] is None:
            raise WorkerError("invalid_request", f"Missing required request field: {key}")

    run_dir = request_path.resolve().parent
    writable_root = Path(os.path.abspath(str(req["writable_runtime_root"])))
    readonly_q0 = Path(os.path.abspath(str(req["readonly_q0_root"])))
    if not is_inside(run_dir, writable_root / "runs"):
        raise WorkerError("invalid_request", "Attempt run directory is outside configured writable_runtime_root/runs.")
    if is_inside(writable_root, readonly_q0) or is_inside(readonly_q0, writable_root):
        raise WorkerError("invalid_request", "Writable runtime root overlaps read-only Q0 root.")
    input_pdf = Path(os.path.abspath(str(req["input_pdf_path"])))
    if not is_inside(input_pdf, run_dir / "input"):
        raise WorkerError("invalid_request", "Input PDF path must lie inside the attempt input directory.")
    return run_dir, writable_root, readonly_q0


class RealTorchRuntime:
    """Thin production adapter keeping torch/transformers/pypdfium2 imports strictly deferred."""

    def installed_distributions(self) -> dict[str, str]:
        return {d.metadata["Name"]: d.version for d in importlib_md.distributions()}

    def is_importable(self, module_name: str) -> bool:
        return importlib.util.find_spec(module_name) is not None

    def dist_version(self, name: str) -> str:
        return importlib_md.version(name)

    def import_pdfium(self):
        import pypdfium2
        return pypdfium2

    def query_platform(self) -> dict:
        if "transformers" in sys.modules or "huggingface_hub" in sys.modules:
            raise WorkerError("environment_isolation_failed", "HF modules imported before offline environment check.")
        import torch
        info: dict = {
            "os": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "torch_cuda_version": torch.version.cuda,
            "cuda_available": bool(torch.cuda.is_available()),
        }
        if info["cuda_available"]:
            props = torch.cuda.get_device_properties(0)
            info.update({
                "device_count": torch.cuda.device_count(),
                "device_name": props.name,
                "device_capability": list(torch.cuda.get_device_capability(0)),
                "arch_list": torch.cuda.get_arch_list(),
                "device_uuid": str(getattr(props, "uuid", "") or ""),
            })
        return info

    def load_model(self, model_dir: Path):
        import torch
        from transformers import AutoModel, AutoTokenizer

        t0 = time.perf_counter()
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir), trust_remote_code=True, local_files_only=True)
        model = AutoModel.from_pretrained(
            str(model_dir),
            trust_remote_code=True,
            use_safetensors=True,
            torch_dtype=torch.bfloat16,
            local_files_only=True,
        )
        model = model.eval().cuda()
        torch.cuda.synchronize()
        load_ms = int(round((time.perf_counter() - t0) * 1000))
        return tokenizer, model, load_ms

    def run_infer_multi(self, model, tokenizer, images: list, call_kwargs: dict) -> tuple[str, int, int, dict]:
        import torch

        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        text, out_token_count = model.infer_multi(tokenizer, prompt=PROMPT, image_files=list(images), **call_kwargs)
        torch.cuda.synchronize()
        infer_ms = int(round((time.perf_counter() - t0) * 1000))
        mem = {
            "cuda_max_allocated_bytes": int(torch.cuda.max_memory_allocated()),
            "cuda_max_reserved_bytes": int(torch.cuda.max_memory_reserved()),
        }
        return text, int(out_token_count), infer_ms, mem

    def is_oom(self, exc: BaseException) -> bool:
        if isinstance(exc, MemoryError):
            return True
        torch_mod = sys.modules.get("torch")
        oom_cls = getattr(getattr(torch_mod, "cuda", None), "OutOfMemoryError", None) if torch_mod else None
        return bool(oom_cls and isinstance(exc, oom_cls))


def execute_request_file(request_path: Path, runtime=None) -> int:
    """Execute one bounded F2 extraction attempt. Returns 0 on completed, 2 on classified failure."""
    rt = runtime or RealTorchRuntime()
    started_utc = _utc_iso()
    t_total_start = time.perf_counter()
    req: dict = {}
    run_dir = request_path.resolve().parent
    output_dir = run_dir / "output"
    envelope_path = output_dir / "envelope.json"
    raw_output_path = output_dir / "raw_output.utf8.bin"
    heartbeat: WorkerHeartbeat | None = None
    monitor: InferenceMonitor | None = None
    diagnostic_raw_preview: str | None = None
    diagnostics: dict = {}

    try:
        if not request_path.is_file() or is_reparse_or_link(request_path):
            raise WorkerError("invalid_request", "Request JSON is missing or symlinked.")
        try:
            req = json.loads(request_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise WorkerError("invalid_request", "Request JSON could not be parsed.") from exc

        run_dir, writable_root, readonly_q0 = _validate_request(req, request_path)
        output_dir = run_dir / "output"
        envelope_path = output_dir / "envelope.json"
        raw_output_path = output_dir / "raw_output.utf8.bin"
        guards = req.get("guards") or {}
        hb_interval = float(guards.get("heartbeat_interval_s", 5.0))

        heartbeat = WorkerHeartbeat(
            output_dir / "heartbeat.json",
            attempt_id=str(req["attempt_id"]),
            fencing_token=int(req["fencing_token"]),
            interval_s=hb_interval,
            progress_fn=lambda: monitor.forward_progress if monitor is not None else 0,
        ).start()
        heartbeat.set_phase("preflight", int(guards.get("load_timeout_s", 1800)))

        # 1. Source, config, manifest, environment, and storage verification
        worker_source_sha = compute_worker_source_sha256()
        if worker_source_sha != str(req["expected_worker_source_sha256"]).lower():
            raise WorkerError("invalid_request", "Worker source digest disagreed with supervisor expectation.")

        page_count = int(req["expected_page_count"])
        config_sha = compute_config_digest(page_count)
        if config_sha != str(req["expected_worker_config_sha256"]).lower():
            raise WorkerError("invalid_request", "Worker configuration digest disagreed with supervisor expectation.")

        model_manifest, model_manifest_sha = load_json_checked(
            MODEL_MANIFEST_PATH, str(req["expected_model_manifest_sha256"]), "model-files.json"
        )
        dep_lock, dep_lock_sha = load_json_checked(
            DEPENDENCY_LOCK_PATH, str(req["expected_dependency_lock_sha256"]), "dependency-lock.json"
        )

        audit_worker_environment(
            dict(os.environ),
            run_dir=run_dir,
            readonly_q0_root=readonly_q0,
            leased_gpu_uuid=str(req["leased_gpu_uuid"]),
        )
        storage_obs = verify_storage_guards(
            writable_root,
            min_free_bytes=int(guards.get("min_free_disk_bytes", 20 * 1024**3)),
            max_root_bytes=int(guards.get("max_runtime_root_bytes", 4 * 1024**3)),
        )
        diagnostics["storage_before"] = storage_obs

        # 2. Dependency lock, platform/GPU, model directory, and static AST checks
        lock_obs = verify_dependency_lock(
            dep_lock,
            accepted_provenance_exceptions=list(req.get("accepted_provenance_exceptions") or []),
            installed_distributions=rt.installed_distributions(),
            is_importable_fn=rt.is_importable,
        )
        plat_obs = rt.query_platform()
        verify_platform_and_gpu(dep_lock, plat_obs, str(req["leased_gpu_uuid"]))
        model_dir = normalize_and_verify_model_dir(str(req["model_dir"]), str(req["notice_dir"]), model_manifest)
        verify_model_sources_ast_safety(model_dir)

        # 3. Render committed PDF bytes at 300 DPI RGB
        heartbeat.set_phase("rendering", int(guards.get("load_timeout_s", 1800)))
        t_render_start = time.perf_counter()
        pdfium = rt.import_pdfium()
        renderer_id = verify_renderer_identity(pdfium, rt.dist_version, dep_lock)
        images, page_summaries = read_and_render_pdf(
            pdfium,
            Path(str(req["input_pdf_path"])),
            expected_sha256=str(req["expected_input_sha256"]),
            expected_byte_length=int(req["expected_input_byte_length"]),
            expected_page_count=page_count,
        )
        render_ms = int(round((time.perf_counter() - t_render_start) * 1000))
        diagnostics["rendered_pages"] = page_summaries

        # 4. Offline model load + HF_MODULES_CACHE identity check
        heartbeat.set_phase("loading_model", int(guards.get("load_timeout_s", 1800)))
        tokenizer, model, load_ms = rt.load_model(model_dir)
        verified_cached_modules = verify_loaded_module_cache(
            Path(os.environ["HF_MODULES_CACHE"]), model_dir, sys.modules
        )
        diagnostics["verified_cached_modules"] = verified_cached_modules

        # 5. Non-modifying PEP 669 monitor + frozen infer_multi execution
        pkg_prefix = type(model).__module__.rsplit(".", 1)[0] + "."
        targets = resolve_monitoring_targets(sys.modules, prefix=pkg_prefix)
        call_kwargs = build_call_kwargs(page_count)
        call_timeout_s = int(guards.get("call_timeout_s") or call_timeout_for_pages(page_count))

        monitor = InferenceMonitor(targets)
        with monitor:
            heartbeat.set_phase("inferring", call_timeout_s, stall_monitored=True)
            try:
                raw_text, out_token_count, infer_ms, cuda_mem = rt.run_infer_multi(
                    model, tokenizer, images, call_kwargs
                )
            except SafetyTripwire as trip:
                raise WorkerError("safety_violation", str(trip)) from trip

        heartbeat.set_phase("validating", 300)
        if monitor.tripwire_hits:
            raise WorkerError("safety_violation", "Forbidden save/eval chain entered.")
        if len(monitor.native_results) != 1:
            raise WorkerError(
                "telemetry_mismatch",
                f"Expected 1 captured native infer() return dict, observed {len(monitor.native_results)}.",
            )
        nat = monitor.native_results[0]
        if nat["text"] != raw_text or len(nat["token_ids"]) != out_token_count:
            raise WorkerError("telemetry_mismatch", "Captured native result disagreed with infer_multi return.")

        kernel_label = monitor.kernel_path_label()
        if kernel_label != "triton_import_failed_dense_fallback":
            raise WorkerError("telemetry_mismatch", f"Unexpected attention kernel path: {kernel_label}")

        try:
            raw_utf8 = raw_text.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise WorkerError("worker_runtime_error", "Native model text was not valid UTF-8.") from exc

        diagnostic_raw_preview = raw_utf8[:DIAGNOSTIC_PREVIEW_CAP_BYTES].decode("utf-8", errors="replace")
        max_raw_bytes = int(guards.get("max_raw_output_bytes", MAX_RAW_OUTPUT_BYTES))

        prompt_len = int(nat["prompt_len"])
        if prompt_len + int(call_kwargs["max_new_tokens"]) > int(call_kwargs["max_length"]):
            raise WorkerError(
                "context_budget_exceeded",
                f"prompt_len ({prompt_len}) + max_new_tokens ({call_kwargs['max_new_tokens']}) > {call_kwargs['max_length']}.",
            )
        if nat["finish_reason"] != "stop":
            raise WorkerError(
                "model_output_truncated",
                f"Native finish_reason was {nat['finish_reason']!r} instead of 'stop'.",
            )
        page_marker_count = sum(1 for tok_id in nat["token_ids"] if tok_id == PAGE_TOKEN_ID)
        if (
            nat["expected_pages"] != page_count
            or nat["num_pages_out"] != page_count
            or page_marker_count != page_count
        ):
            raise WorkerError(
                "page_count_mismatch",
                f"Page count mismatch: input={page_count}, native_out={nat['num_pages_out']}, markers={page_marker_count}.",
            )
        if len(raw_utf8) > max_raw_bytes:
            raise WorkerError(
                "output_cap_exceeded",
                f"Raw UTF-8 output length {len(raw_utf8)} exceeded {max_raw_bytes}-byte cap.",
            )

        write_exclusive_bytes(raw_output_path, raw_utf8)
        raw_sha256 = sha256_bytes(raw_utf8)
        completed_utc = _utc_iso()
        total_ms = int(round((time.perf_counter() - t_total_start) * 1000))

        diagnostics.update({
            "prompt_token_count": prompt_len,
            "output_token_count": out_token_count,
            "page_marker_count": page_marker_count,
            "kernel_path": kernel_label,
            "provenance_exceptions": lock_obs["provenance_exceptions"],
            **cuda_mem,
        })

        envelope = {
            "schema": ENVELOPE_SCHEMA,
            "worker_id": WORKER_ID,
            "status": "completed",
            "document_id": str(req["document_id"]),
            "job_id": str(req["job_id"]),
            "attempt_id": str(req["attempt_id"]),
            "fencing_token": int(req["fencing_token"]),
            "input": {
                "sha256": str(req["expected_input_sha256"]).lower(),
                "byte_length": int(req["expected_input_byte_length"]),
                "page_count": page_count,
            },
            "output": {
                "raw_file_name": raw_output_path.name,
                "byte_length": len(raw_utf8),
                "sha256": raw_sha256,
                "finish_reason": "stop",
                "output_page_count": int(nat["num_pages_out"]),
                "output_token_count": out_token_count,
            },
            "provenance": {
                "model_repo_id": MODEL_REPO_ID,
                "model_revision": MODEL_REVISION,
                "model_manifest_sha256": model_manifest_sha,
                "dependency_lock_sha256": dep_lock_sha,
                "worker_source_sha256": worker_source_sha,
                "worker_config_sha256": config_sha,
                "renderer_identity": renderer_id,
                "generation_settings": call_kwargs,
                "provenance_exceptions": lock_obs["provenance_exceptions"],
            },
            "timings": {
                "started_at_utc": started_utc,
                "completed_at_utc": completed_utc,
                "load_duration_ms": load_ms,
                "render_duration_ms": render_ms,
                "infer_duration_ms": infer_ms,
                "total_duration_ms": total_ms,
            },
            "diagnostics": diagnostics,
            "failure": None,
        }
        write_envelope_atomic(envelope_path, envelope)
        heartbeat.set_phase("completed", None, stall_monitored=False)
        return 0

    except WorkerError as werr:
        _write_failure_envelope(
            envelope_path=envelope_path,
            req=req,
            code=werr.code,
            detail=werr.detail,
            started_utc=started_utc,
            total_ms=int(round((time.perf_counter() - t_total_start) * 1000)),
            diagnostic_raw_preview=diagnostic_raw_preview,
            diagnostics=diagnostics,
        )
        if heartbeat is not None:
            heartbeat.set_phase("failed", None, stall_monitored=False)
        return 2
    except BaseException as exc:
        code = "cuda_oom" if rt.is_oom(exc) else "worker_runtime_error"
        detail = FAILURE_CODES[code] + f" ({type(exc).__name__})"
        _write_failure_envelope(
            envelope_path=envelope_path,
            req=req,
            code=code,
            detail=detail,
            started_utc=started_utc,
            total_ms=int(round((time.perf_counter() - t_total_start) * 1000)),
            diagnostic_raw_preview=diagnostic_raw_preview,
            diagnostics=diagnostics,
        )
        if heartbeat is not None:
            heartbeat.set_phase("failed", None, stall_monitored=False)
        return 2
    finally:
        if heartbeat is not None:
            heartbeat.stop()


def _write_failure_envelope(
    *,
    envelope_path: Path,
    req: dict,
    code: str,
    detail: str,
    started_utc: str,
    total_ms: int,
    diagnostic_raw_preview: str | None,
    diagnostics: dict,
) -> None:
    try:
        envelope = {
            "schema": ENVELOPE_SCHEMA,
            "worker_id": WORKER_ID,
            "status": "failed",
            "document_id": str(req.get("document_id") or ""),
            "job_id": str(req.get("job_id") or ""),
            "attempt_id": str(req.get("attempt_id") or ""),
            "fencing_token": int(req.get("fencing_token") or 0),
            "input": None,
            "output": None,
            "provenance": None,
            "timings": {
                "started_at_utc": started_utc,
                "completed_at_utc": _utc_iso(),
                "load_duration_ms": 0,
                "render_duration_ms": 0,
                "infer_duration_ms": 0,
                "total_duration_ms": max(0, total_ms),
            },
            "diagnostics": diagnostics,
            "failure": {
                "code": code,
                "message": FAILURE_CODES.get(code, FAILURE_CODES["worker_runtime_error"]),
                "detail": detail[:500],
                "diagnostic_raw_output_utf8": diagnostic_raw_preview,
            },
        }
        write_envelope_atomic(envelope_path, envelope)
    except OSError:
        pass
