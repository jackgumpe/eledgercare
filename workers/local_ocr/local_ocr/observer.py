"""PEP 669 sys.monitoring safety tripwire and non-modifying native result observer."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
import sys

from .protocol import WorkerError

TOOL_ID = 4
TOOL_NAME = "eledgercare-f2-observer"


class SafetyTripwire(BaseException):
    """Raised immediately before executing any instruction on the forbidden save/eval chain."""


@dataclass(frozen=True)
class TargetSpec:
    module_suffix: str
    qualname: str
    role: str
    tripwire: bool = False
    capture: str | None = None


DEFAULT_TARGETS = (
    TargetSpec("modeling_unlimitedocr", "UnlimitedOCRForCausalLM.infer", "native_infer", capture="native_result"),
    TargetSpec("modeling_unlimitedocr", "UnlimitedOCRModel.forward", "model_forward", capture="forward_step"),
    TargetSpec("modeling_unlimitedocr", "UnlimitedOCRForCausalLM._uocr_save_results", "save_chain", tripwire=True),
    TargetSpec("modeling_unlimitedocr", "process_image_with_refs", "save_chain", tripwire=True),
    TargetSpec("modeling_unlimitedocr", "draw_bounding_boxes", "save_chain", tripwire=True),
    TargetSpec("modeling_unlimitedocr", "extract_coordinates_and_label", "eval_site", tripwire=True),
    TargetSpec("dash_attention", "DashAttention._forward_triton", "triton_attempt"),
    TargetSpec("dash_attention", "DashAttention._forward_dense", "dense_fallback"),
)


def resolve_monitoring_targets(modules: dict, *, prefix: str, specs=DEFAULT_TARGETS) -> dict:
    resolved = {}
    for spec in specs:
        hits = [
            m for name, m in modules.items()
            if name.startswith(prefix) and name.rsplit(".", 1)[-1] == spec.module_suffix and m is not None
        ]
        if len(hits) != 1:
            raise WorkerError("telemetry_mismatch", f"Could not uniquely resolve dynamic module {spec.module_suffix}.")
        obj = hits[0]
        try:
            for attr in spec.qualname.split("."):
                obj = getattr(obj, attr)
            code = inspect.unwrap(obj).__code__
        except AttributeError as exc:
            raise WorkerError("telemetry_mismatch", f"Missing native target {spec.qualname}.") from exc
        resolved[code] = spec
    return resolved


class InferenceMonitor:
    """Observes native infer() return dict, forward progress, dense fallback, and eval tripwires."""

    def __init__(self, resolved_targets: dict):
        if sys.version_info < (3, 12) or not hasattr(sys, "monitoring"):
            raise WorkerError("platform_mismatch", "Python >= 3.12 sys.monitoring is required.")
        self.targets = dict(resolved_targets)
        self.forward_progress = 0
        self.tripwire_hits: list[str] = []
        self.native_results: list[dict] = []
        self.triton_starts = 0
        self.triton_none_returns = 0
        self.triton_handled_exceptions = 0
        self.dense_starts = 0
        self._installed = False

    def _on_start(self, code, _offset):
        spec = self.targets.get(code)
        if spec is None:
            return
        if spec.tripwire:
            self.tripwire_hits.append(spec.qualname)
            raise SafetyTripwire(f"Forbidden save/eval target entered: {spec.qualname}")
        if spec.role == "triton_attempt":
            self.triton_starts += 1
        elif spec.role == "dense_fallback":
            self.dense_starts += 1

    def _on_return(self, code, _offset, retval):
        spec = self.targets.get(code)
        if spec is None:
            return
        if spec.capture == "forward_step":
            self.forward_progress += 1
        elif spec.capture == "native_result" and isinstance(retval, dict) and "finish_reason" in retval:
            self.native_results.append({
                "finish_reason": retval.get("finish_reason"),
                "num_pages_out": retval.get("num_pages_out"),
                "expected_pages": retval.get("expected_pages"),
                "time_s": retval.get("time"),
                "prefill_time_s": retval.get("prefill_time"),
                "prompt_len": len(retval.get("prompt_token_ids") or []),
                "token_ids": list(retval.get("token_ids") or []),
                "text": retval.get("text"),
            })
        elif spec.role == "triton_attempt" and retval is None:
            self.triton_none_returns += 1

    def _on_exception_handled(self, code, _offset, _exc):
        spec = self.targets.get(code)
        if spec is not None and spec.role == "triton_attempt":
            self.triton_handled_exceptions += 1

    def install(self) -> "InferenceMonitor":
        mon = sys.monitoring
        ev = mon.events
        try:
            mon.use_tool_id(TOOL_ID, TOOL_NAME)
        except ValueError as exc:
            raise WorkerError("telemetry_mismatch", f"sys.monitoring tool id {TOOL_ID} unavailable.") from exc
        mon.register_callback(TOOL_ID, ev.PY_START, self._on_start)
        mon.register_callback(TOOL_ID, ev.PY_RETURN, self._on_return)
        mon.register_callback(TOOL_ID, ev.EXCEPTION_HANDLED, self._on_exception_handled)
        for code in self.targets:
            mon.set_local_events(TOOL_ID, code, ev.PY_START | ev.PY_RETURN)
        mon.set_events(TOOL_ID, ev.EXCEPTION_HANDLED)
        self._installed = True
        return self

    def uninstall(self) -> None:
        if not self._installed:
            return
        mon = sys.monitoring
        ev = mon.events
        mon.set_events(TOOL_ID, 0)
        for code in self.targets:
            mon.set_local_events(TOOL_ID, code, 0)
        for flag in (ev.PY_START, ev.PY_RETURN, ev.EXCEPTION_HANDLED):
            mon.register_callback(TOOL_ID, flag, None)
        mon.free_tool_id(TOOL_ID)
        self._installed = False

    def __enter__(self) -> "InferenceMonitor":
        return self.install()

    def __exit__(self, *_exc) -> bool:
        self.uninstall()
        return False

    def kernel_path_label(self) -> str:
        if (
            self.triton_starts > 0
            and self.triton_none_returns == self.triton_starts
            and self.triton_handled_exceptions > 0
            and self.dense_starts > 0
        ):
            return "triton_import_failed_dense_fallback"
        if self.triton_starts == 0 and self.dense_starts > 0:
            return "dense_only"
        return "unexpected_kernel_path"
