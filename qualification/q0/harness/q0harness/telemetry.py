"""External, non-modifying observation of the native code path via PEP 669 sys.monitoring.

No model source is edited and no attribute of the model or its modules is replaced. The
observer registers callbacks for the code objects of named native functions and reads
(never writes) arguments of return events. The ONLY intervention is a fail-closed tripwire
on the eval-containing save path, which the frozen protocol has already made unreachable:
if that path is ever entered the callback raises SafetyTripwire (a BaseException) before
its first instruction runs, and the violation is recorded independently of whether any
native bare `except:` later swallows it.

Provenance labels used in summaries:
  direct     - counted/measured by this observer or harness at runtime
  native     - value reported by the model's own return dictionary
  derived    - arithmetic over direct/native values
  source     - inference from pinned source reading, not observed
  unsupported- not observable without modifying the model (reported as such)
"""

from __future__ import annotations

import inspect
import sys
import time
from array import array
from dataclasses import dataclass, field

from .outcome import Q0Failure

TOOL_ID = 4
TOOL_NAME = "eldq0-observer"
MAX_EXC_RECORDS = 16


class SafetyTripwire(BaseException):
    """Raised from the monitoring callback when the forbidden save path is entered."""


@dataclass(frozen=True)
class TargetSpec:
    module_suffix: str          # e.g. "modeling_unlimitedocr" (matched as the last dotted component)
    qualname: str               # attribute path inside the module, e.g. "DashAttention._forward_triton"
    role: str
    required: bool = True
    tripwire: bool = False
    capture: str | None = None  # "native_result" | "cache_probe"


TARGETS = (
    TargetSpec("modeling_unlimitedocr", "UnlimitedOCRForCausalLM.infer", "native_infer", capture="native_result"),
    TargetSpec("modeling_unlimitedocr", "UnlimitedOCRForCausalLM._uocr_generate", "native_generate"),
    TargetSpec("modeling_unlimitedocr", "UnlimitedOCRModel.forward", "model_forward", capture="cache_probe"),
    TargetSpec("modeling_unlimitedocr", "UnlimitedOCRForCausalLM._uocr_save_results", "forbidden_save_path", tripwire=True),
    TargetSpec("modeling_unlimitedocr", "process_image_with_refs", "forbidden_save_path", tripwire=True),
    TargetSpec("modeling_unlimitedocr", "draw_bounding_boxes", "forbidden_save_path", tripwire=True),
    TargetSpec("modeling_unlimitedocr", "extract_coordinates_and_label", "forbidden_eval_site", tripwire=True),
    TargetSpec("modeling_deepseekv2", "configure_dash_inference", "dash_infer_switch"),
    TargetSpec("modeling_deepseekv2", "_infer_prefill_attend", "prefill_attend"),
    TargetSpec("modeling_deepseekv2", "_dash_decode_forward", "decode_forward"),
    TargetSpec("modeling_deepseekv2", "_decode_attend", "decode_attend_fp32"),
    TargetSpec("modeling_deepseekv2", "_orig_forward", "non_dash_attention_forward"),
    TargetSpec("dash_attention", "DashAttention._forward_triton", "triton_attempt"),
    TargetSpec("dash_attention", "DashAttention._forward_dense", "dense_sdpa_fallback"),
    TargetSpec("sparse_gather_e2e_triton", "triton_gather_attention_e2e", "triton_kernel_entry", required=False),
)


@dataclass
class _Stat:
    spec: TargetSpec
    starts: int = 0
    returns: int = 0
    returns_none: int = 0
    unwinds: int = 0
    handled: int = 0
    exc_records: list = field(default_factory=list)

    def counts(self) -> dict:
        return {"starts": self.starts, "returns": self.returns, "returns_none": self.returns_none,
                "unwinds": self.unwinds, "handled_exceptions": self.handled}


def find_module(modules: dict, suffix: str, prefix: str):
    hits = [m for name, m in modules.items()
            if name.startswith(prefix) and name.rsplit(".", 1)[-1] == suffix and m is not None]
    if len(hits) > 1:
        raise Q0Failure("TELEMETRY_UNSUPPORTED", f"ambiguous dynamic modules for {suffix}: {len(hits)}")
    return hits[0] if hits else None


def resolve_targets(modules: dict, prefix: str = "transformers_modules.", specs=TARGETS) -> tuple[dict, list]:
    resolved, unresolved = {}, []
    for spec in specs:
        mod = find_module(modules, spec.module_suffix, prefix)
        obj = mod
        try:
            for part in spec.qualname.split("."):
                obj = getattr(obj, part)
            fn = inspect.unwrap(obj)
            code = fn.__code__
        except AttributeError:
            code = None
        if code is None:
            if spec.required:
                raise Q0Failure("TELEMETRY_UNSUPPORTED", f"required native target not found: {spec.module_suffix}:{spec.qualname}")
            unresolved.append(f"{spec.module_suffix}:{spec.qualname}")
            continue
        if code in resolved:
            raise Q0Failure("TELEMETRY_UNSUPPORTED", f"two targets share one code object: {spec.qualname}")
        resolved[code] = spec
    return resolved, unresolved


def _tensor_bytes(t) -> int:
    try:
        return int(t.numel()) * int(t.element_size())
    except Exception:
        return 0


def probe_cache(cache) -> dict | None:
    """Read-only metadata of a transformers DynamicCache (shapes/sizes only; no device sync)."""
    if cache is None:
        return None
    keys = getattr(cache, "key_cache", None)
    values = getattr(cache, "value_cache", None)
    if keys is None and hasattr(cache, "layers"):  # newer transformers layout
        keys = [getattr(l, "keys", None) for l in cache.layers]
        values = [getattr(l, "values", None) for l in cache.layers]
    keys, values = list(keys or []), list(values or [])
    seq = None
    for t in keys:
        shape = getattr(t, "shape", None)
        if shape is not None and len(shape) >= 2 and int(shape[-2]) > 0:
            seq = int(shape[-2])
            break
    idx = getattr(cache, "_dash_idx_k", None) or {}
    return {
        "type": type(cache).__name__,
        "seq_len": seq,
        "layers": len(keys),
        "kv_bytes": sum(_tensor_bytes(t) for t in keys + values if t is not None),
        "dash_idx_bytes": sum(_tensor_bytes(t) for t in idx.values()),
        "ring_marker": hasattr(cache, "_prefill_length"),
    }


def summarize_native(res: dict) -> dict:
    token_ids = list(res.get("token_ids") or [])
    prompt_ids = list(res.get("prompt_token_ids") or [])
    return {
        "provenance": "native",
        "finish_reason": res.get("finish_reason"),
        "num_pages_out": res.get("num_pages_out"),
        "expected_pages": res.get("expected_pages"),
        "time_s": res.get("time"),
        "prefill_time_s": res.get("prefill_time"),
        "prompt": res.get("prompt"),
        "prompt_len": len(prompt_ids),
        "output_tokens": len(token_ids),
        "token_ids": token_ids,
        "text": res.get("text"),
    }


class NativeObserver:
    def __init__(self, resolved: dict, unresolved: list | None = None, clock=time.perf_counter_ns):
        if sys.version_info < (3, 12) or not hasattr(sys, "monitoring"):
            raise Q0Failure("TELEMETRY_UNSUPPORTED", "sys.monitoring (Python >= 3.12) is required")
        self.stats = {code: _Stat(spec) for code, spec in resolved.items()}
        self.unresolved = list(unresolved or [])
        self.clock = clock
        self.callback_ns = 0
        self.events = 0
        self.progress = 0                       # model forward returns (heartbeat)
        self.violations: list[dict] = []
        self.native_results: list[dict] = []
        self.cache_seq = array("q")
        self.cache_kv = array("q")
        self.cache_idx = array("q")
        self.cache_types: set = set()
        self.ring_marker_seen = False
        self.installed = False

    # -- callbacks ---------------------------------------------------------
    def _on_start(self, code, offset):
        t0 = self.clock()
        st = self.stats.get(code)
        try:
            if st is not None:
                self.events += 1
                st.starts += 1
                if st.spec.tripwire:
                    self.violations.append({"target": st.spec.qualname, "role": st.spec.role, "event": "PY_START"})
                    raise SafetyTripwire(f"forbidden save/eval path entered: {st.spec.qualname}")
        finally:
            self.callback_ns += self.clock() - t0

    def _on_return(self, code, offset, retval):
        t0 = self.clock()
        try:
            st = self.stats.get(code)
            if st is None:
                return
            self.events += 1
            st.returns += 1
            if retval is None:
                st.returns_none += 1
            cap = st.spec.capture
            if cap == "native_result" and isinstance(retval, dict) and "finish_reason" in retval:
                self.native_results.append(summarize_native(retval))
            elif cap == "cache_probe":
                self.progress += 1
                info = probe_cache(getattr(retval, "past_key_values", None))
                if info is not None:
                    self.cache_seq.append(info["seq_len"] if info["seq_len"] is not None else -1)
                    self.cache_kv.append(info["kv_bytes"])
                    self.cache_idx.append(info["dash_idx_bytes"])
                    self.cache_types.add(info["type"])
                    self.ring_marker_seen |= info["ring_marker"]
        finally:
            self.callback_ns += self.clock() - t0

    def _on_exc(self, kind):
        def cb(code, offset, exc):
            t0 = self.clock()
            try:
                st = self.stats.get(code)
                if st is None:
                    return
                self.events += 1
                if kind == "handled":
                    st.handled += 1
                else:
                    st.unwinds += 1
                if len(st.exc_records) < MAX_EXC_RECORDS:
                    st.exc_records.append({"kind": kind, "type": f"{type(exc).__module__}.{type(exc).__qualname__}",
                                           "message": str(exc)[:400]})
            finally:
                self.callback_ns += self.clock() - t0
        return cb

    # -- lifecycle ---------------------------------------------------------
    def install(self):
        mon = sys.monitoring
        E = mon.events
        try:
            mon.use_tool_id(TOOL_ID, TOOL_NAME)
        except ValueError as e:
            raise Q0Failure("TELEMETRY_UNSUPPORTED", f"monitoring tool id {TOOL_ID} unavailable: {e}")
        mon.register_callback(TOOL_ID, E.PY_START, self._on_start)
        mon.register_callback(TOOL_ID, E.PY_RETURN, self._on_return)
        mon.register_callback(TOOL_ID, E.EXCEPTION_HANDLED, self._on_exc("handled"))
        mon.register_callback(TOOL_ID, E.PY_UNWIND, self._on_exc("unwind"))
        for code in self.stats:
            mon.set_local_events(TOOL_ID, code, E.PY_START | E.PY_RETURN)
        # Exception events can only be enabled globally in 3.12; callbacks filter by code object.
        mon.set_events(TOOL_ID, E.EXCEPTION_HANDLED | E.PY_UNWIND)
        self.installed = True
        return self

    def uninstall(self):
        if not self.installed:
            return
        mon = sys.monitoring
        E = mon.events
        mon.set_events(TOOL_ID, 0)
        for code in self.stats:
            mon.set_local_events(TOOL_ID, code, 0)
        for ev in (E.PY_START, E.PY_RETURN, E.EXCEPTION_HANDLED, E.PY_UNWIND):
            mon.register_callback(TOOL_ID, ev, None)
        mon.free_tool_id(TOOL_ID)
        self.installed = False

    def __enter__(self):
        return self.install()

    def __exit__(self, *exc):
        self.uninstall()
        return False

    # -- windows -----------------------------------------------------------
    def begin_window(self) -> dict:
        return {"counts": {code: st.counts() for code, st in self.stats.items()},
                "exc_len": {code: len(st.exc_records) for code, st in self.stats.items()},
                "native": len(self.native_results), "cache": len(self.cache_seq),
                "violations": len(self.violations), "callback_ns": self.callback_ns, "events": self.events}

    def end_window(self, mark: dict) -> dict:
        targets = {}
        for code, st in self.stats.items():
            now, then = st.counts(), mark["counts"][code]
            targets[f"{st.spec.module_suffix}:{st.spec.qualname}"] = {
                "role": st.spec.role, **{k: now[k] - then[k] for k in now},
                "exceptions": st.exc_records[mark["exc_len"][code]:]}
        natives = self.native_results[mark["native"]:]
        seq = list(self.cache_seq[mark["cache"]:])
        kv = list(self.cache_kv[mark["cache"]:])
        idx = list(self.cache_idx[mark["cache"]:])
        return {
            "targets": targets,
            "unresolved_optional_targets": self.unresolved,
            "native_results": natives,
            "cache": summarize_cache(seq, kv, idx, self.cache_types, self.ring_marker_seen),
            "violations": self.violations[mark["violations"]:],
            "observer_overhead": {"provenance": "direct", "callback_ns": self.callback_ns - mark["callback_ns"],
                                  "events": self.events - mark["events"],
                                  "note": "Self-timed callback cost only; interpreter dispatch and global exception-event "
                                          "filtering overhead are not included (lower bound)."},
            "kernel_path": classify_kernel_path(targets),
        }


def summarize_cache(seq, kv, idx, types, ring_seen) -> dict:
    n = len(seq)
    out = {"provenance": "direct", "forward_returns": n, "cache_types": sorted(types),
           "ring_buffer_marker_seen": ring_seen}
    if n == 0:
        out["observed"] = False
        return out
    diffs = [b - a for a, b in zip(seq, seq[1:])]
    out.update({
        "observed": True,
        "prefill_seq_len": seq[0], "final_seq_len": seq[-1],
        "decode_steps_observed": n - 1,
        "grows_by_one_each_decode_step": all(d == 1 for d in diffs),
        "kv_bytes_after_prefill": kv[0], "kv_bytes_final": kv[-1], "kv_bytes_max": max(kv),
        "dash_idx_bytes_final": idx[-1],
        "kv_bytes_per_token_derived": ((kv[-1] - kv[0]) / (seq[-1] - seq[0])) if seq[-1] > seq[0] else None,
        "seq_len_samples_head": seq[:4], "seq_len_samples_tail": seq[-4:],
    })
    return out


def classify_kernel_path(targets: dict) -> dict:
    def t(role):
        return [v for v in targets.values() if v["role"] == role]
    tri = t("triton_attempt")[0]
    dense = t("dense_sdpa_fallback")[0]
    kern = t("triton_kernel_entry")
    kern_starts = kern[0]["starts"] if kern else 0
    handled_types = sorted({e["type"] for e in tri["exceptions"] if e["kind"] == "handled"})
    if tri["starts"] == 0:
        label = "triton_not_attempted"
    elif tri["returns"] - tri["returns_none"] == tri["starts"] and tri["starts"] > 0:
        label = "triton_executed"
    elif tri["unwinds"] > 0:
        label = "triton_exception_propagated"
    elif tri["returns_none"] == tri["starts"] and kern_starts == 0 and tri["handled_exceptions"] > 0:
        label = "triton_import_failed_dense_fallback"
    elif tri["returns_none"] == tri["starts"]:
        label = "triton_returned_none_dense_fallback"
    else:
        label = "mixed"
    return {
        "provenance": "direct",
        "label": label,
        "triton_attempts": tri["starts"],
        "triton_non_null_returns": tri["returns"] - tri["returns_none"],
        "triton_kernel_entries": kern_starts if kern else None,
        "triton_import_exception_types": handled_types,
        "dense_sdpa_calls": dense["starts"],
        "prefill_attend_calls": t("prefill_attend")[0]["starts"],
        "decode_forward_calls": t("decode_forward")[0]["starts"],
        "decode_attend_fp32_calls": t("decode_attend_fp32")[0]["starts"],
        "non_dash_attention_calls": t("non_dash_attention_forward")[0]["starts"],
        "unobservable": "Which GPU kernels Triton/SDPA dispatch internally is not observed (unsupported without profiler hooks).",
    }
