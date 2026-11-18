"""WP-0017 AblationEngine and genuine endpoint factory compatible with Astra trial.document.

Binds:
  - 'native'       -> genuine docs/research/WP-0015/astra/native.py:Native
  - 'carbon_bf16'  -> genuine docs/research/WP-0015/carbon/engine.py:CarbonEngine('carbon_bf16')
  - 6-switch arms  -> AblationEngine ('all_off', 'all_on', 'add_*', 'remove_*', 's_*', 'carbon_surgical')

No torch or CUDA module is imported at module import time.
"""
from __future__ import annotations

import inspect
import os
import sys
import time
from pathlib import Path
from time import perf_counter_ns as clock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WP15_CARBON = ROOT / "docs/research/WP-0015/carbon"
WP15_ASTRA = ROOT / "docs/research/WP-0015/astra"
WP14 = ROOT / "docs/research/WP-0014/eld-latency-author"
WORKER = ROOT / "workers/local_ocr"
for _p in reversed((str(HERE), str(WP15_CARBON), str(WP15_ASTRA), str(WP14), str(WORKER))):
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

from formats import digest, native_page, token_classes
from generation import Generation
from local_ocr import observer, protocol, verify_runtime, worker
from native import GPU, LOCK_SHA, MANIFEST_SHA, MODEL, NOTICE, Native
from switches import (
    ResolvedMode,
    SwitchActivationCounters,
    SwitchConfig,
    apply_ablation_patches,
    resolve_mode,
    resolve_model_modules,
)

SAFETY_ONLY_SPECS = tuple(s for s in observer.DEFAULT_TARGETS if s.tripwire)
OBSERVER_GENUINE_NATIVE = "astra_stage_monitor_pep669"
OBSERVER_GENUINE_CARBON = "carbon_safety_monitor_wrapped"
OBSERVER_UNIFORM_ABLATION = "wp0017_uniform_ablation_observer"


def make_safety_monitor(model):
    module = sys.modules[type(model).__module__]
    targets = observer.resolve_monitoring_targets(
        sys.modules, prefix=module.__package__ + ".", specs=SAFETY_ONLY_SPECS
    )
    return observer.InferenceMonitor(targets)


def _sync_if_cuda(model_lm) -> None:
    torch_mod = sys.modules.get("torch")
    if torch_mod is not None and model_lm.lm_head.weight.is_cuda:
        torch_mod.cuda.synchronize()


def _effective_prefill_dispatch(switch_cfg: SwitchConfig, delta: dict) -> str:
    if not switch_cfg.packed_moe_prefill:
        return "native_linear_loop"
    grouped = int(delta.get("s1a_prefill_grouped_mm_calls", 0))
    fallback = int(delta.get("s1a_prefill_fallback_calls", 0))
    if grouped > 0 and fallback == 0:
        return "grouped_mm"
    if grouped > 0 and fallback > 0:
        return "partial_grouped_mm_with_fallback"
    if fallback > 0:
        return "fallback_linear_loop"
    return "no_moe_prefill_calls"


class AblationEngine:
    """Parameterized 6-switch Baidu Unlimited-OCR-2 runner matching Native and CarbonEngine contracts."""

    window = 3

    def __init__(
        self,
        run: Path,
        mode: str,
        *,
        surgical_override: str | None = None,
        runtime=None,
        skip_lock_and_pin: bool = False,
    ):
        resolved = resolve_mode(mode, surgical_override=surgical_override)
        if resolved.implementation != "ablation_engine":
            raise ValueError(f"AblationEngine is for parameterized switch modes, got {mode!r} ({resolved.implementation})")
        self.resolved: ResolvedMode = resolved
        self.mode: str = resolved.requested_name
        self.canonical_mode: str = resolved.canonical_name
        self.switch_cfg: SwitchConfig = resolved.switch_config
        self.observer_kind: str = OBSERVER_UNIFORM_ABLATION
        self.runtime = rt = runtime or worker.RealTorchRuntime()
        self.pin = None

        if not skip_lock_and_pin:
            lock, _ = verify_runtime.load_json_checked(protocol.DEPENDENCY_LOCK_PATH, LOCK_SHA, "lock")
            manifest, _ = verify_runtime.load_json_checked(protocol.MODEL_MANIFEST_PATH, MANIFEST_SHA, "manifest")
            deps = verify_runtime.verify_dependency_lock(
                lock,
                accepted_provenance_exceptions=["torchvision-local-sha256-TOFU"],
                installed_distributions=rt.installed_distributions(),
                is_importable_fn=rt.is_importable,
            )
            platform_info = rt.query_platform()
            verify_runtime.verify_platform_and_gpu(lock, platform_info, GPU)
            self.pin = Generation(str(MODEL), str(NOTICE), manifest, verify_runtime.normalize_and_verify_model_dir)
        else:
            deps = {"skipped_for_cpu_unit_test": True}
            platform_info = {"mode": "cpu_unit_test"}

        try:
            if not skip_lock_and_pin:
                verify_runtime.verify_model_sources_ast_safety(MODEL)
            self.tokenizer, self.model, base_load_ms = rt.load_model(MODEL)
            if not skip_lock_and_pin:
                modules = verify_runtime.verify_loaded_module_cache(
                    Path(os.environ["HF_MODULES_CACHE"]), MODEL, sys.modules
                )
            else:
                modules = 0

            import torch

            if not skip_lock_and_pin and self.model.lm_head.weight.dtype != torch.bfloat16:
                raise ValueError("native target dtype mismatch")

            t_pack = time.perf_counter()
            self.counters, self.static_cache_cls = apply_ablation_patches(self.model, switch_cfg=self.switch_cfg)
            _sync_if_cuda(self.model)
            pack_ms = int(round((time.perf_counter() - t_pack) * 1000))

            is_cuda = bool(self.model.lm_head.weight.is_cuda)
            alloc_bytes = int(torch.cuda.memory_allocated()) if is_cuda else 0
            res_bytes = int(torch.cuda.memory_reserved()) if is_cuda else 0
            tok_sha = digest((MODEL / "tokenizer.json").read_bytes()) if (MODEL / "tokenizer.json").is_file() else None

            self.info = dict(
                engine_mode=self.mode,
                canonical_mode=self.canonical_mode,
                implementation="ablation_engine",
                is_genuine_endpoint=False,
                observer_kind=self.observer_kind,
                switch_bits=self.switch_cfg.bits,
                switches_by_id=self.switch_cfg.by_id,
                switches_by_flag=self.switch_cfg.by_flag,
                enabled_switches=self.switch_cfg.enabled_switches,
                disabled_switches=self.switch_cfg.disabled_switches,
                family=self.resolved.family,
                model_revision=protocol.MODEL_REVISION,
                manifest_sha256=MANIFEST_SHA,
                dependency_lock_sha256=LOCK_SHA,
                platform=platform_info,
                dependencies=deps,
                verified_modules=modules,
                base_load_ms=base_load_ms,
                pack_patch_ms=pack_ms,
                load_ms=base_load_ms + pack_ms,
                weight_allocated_bytes_after_pack=alloc_bytes,
                weight_reserved_bytes_after_pack=res_bytes,
                tokenizer=type(self.tokenizer).__name__,
                tokenizer_sha256=tok_sha,
                eos_id=self.tokenizer.eos_token_id,
                page_id=protocol.PAGE_TOKEN_ID,
                target_dtype=str(self.model.lm_head.weight.dtype),
            )
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        if self.pin is not None:
            self.pin.close()

    def read(self, pages, folder):
        if self.pin is not None:
            self.pin.verify(str(MODEL), str(NOTICE), self.pin.manifest)
        cfg = protocol.build_call_kwargs(len(pages))
        uocr_mod, _, _, _ = resolve_model_modules(self.model)

        vision_marks = {}
        visual_tokens = None
        last_gen_dict = {}
        counters_before = self.counters.snapshot()

        orig_build = uocr_mod._uocr_build_inputs
        orig_sam = self.model.model.sam_model.forward
        orig_proj = self.model.model.projector.forward
        cur_gen = self.model._uocr_generate

        def wrapped_build(*a, **kw):
            nonlocal visual_tokens
            vision_marks["build_inputs_start"] = clock()
            res = orig_build(*a, **kw)
            vision_marks["build_inputs_end"] = clock()
            visual_tokens = int(res[2].sum())
            return res

        def wrapped_sam(*a, **kw):
            if "vision_start_start" not in vision_marks:
                _sync_if_cuda(self.model)
                vision_marks["vision_start_start"] = clock()
            return orig_sam(*a, **kw)

        def wrapped_proj(*a, **kw):
            res = orig_proj(*a, **kw)
            _sync_if_cuda(self.model)
            vision_marks["vision_end_end"] = clock()
            return res

        def wrapped_gen(*a, **kw):
            res = cur_gen(*a, **kw)
            last_gen_dict.update(res)
            return res

        uocr_mod._uocr_build_inputs = wrapped_build
        self.model.model.sam_model.forward = wrapped_sam
        self.model.model.projector.forward = wrapped_proj
        self.model._uocr_generate = wrapped_gen
        safety = make_safety_monitor(self.model) if self.pin is not None else None
        try:
            if safety is not None:
                with safety:
                    text, count, elapsed_ms, vram = self.runtime.run_infer_multi(
                        self.model, self.tokenizer, [p["image"] for p in pages], cfg
                    )
            else:
                text, count, elapsed_ms, vram = self.runtime.run_infer_multi(
                    self.model, self.tokenizer, [p["image"] for p in pages], cfg
                )
        finally:
            uocr_mod._uocr_build_inputs = orig_build
            self.model.model.sam_model.forward = orig_sam
            self.model.model.projector.forward = orig_proj
            self.model._uocr_generate = cur_gen

        if safety is not None and safety.tripwire_hits:
            raise ValueError(f"Forbidden save/eval chain entered: {safety.tripwire_hits}")
        ids = list(last_gen_dict["token_ids"])
        if last_gen_dict["text"] != text or len(ids) != count:
            raise ValueError("ablation generation output mismatch")

        counters_after = self.counters.snapshot()
        counter_delta = SwitchActivationCounters.delta(counters_before, counters_after)
        marks = {**vision_marks, **last_gen_dict.get("clock_marks_ns", {})}
        eff_dispatch = _effective_prefill_dispatch(self.switch_cfg, counter_delta)

        indices = [i for i, tok in enumerate(ids) if tok == protocol.PAGE_TOKEN_ID]
        raw_parts = text.split("<PAGE>")
        ok = (
            last_gen_dict["finish_reason"] == "stop"
            and last_gen_dict["expected_pages"] == last_gen_dict["num_pages_out"] == len(pages)
            and len(indices) == len(pages)
            and indices[0] == 0
            and len(raw_parts) == len(pages) + 1
            and not raw_parts[0]
        )
        details = dict(
            engine_mode=self.mode,
            canonical_mode=self.canonical_mode,
            implementation="ablation_engine",
            is_genuine_endpoint=False,
            observer_kind=self.observer_kind,
            switch_bits=self.switch_cfg.bits,
            switches_by_id=self.switch_cfg.by_id,
            switches_by_flag=self.switch_cfg.by_flag,
            effective_prefill_dispatch=eff_dispatch,
            cache_telemetry=last_gen_dict.get("cache_telemetry"),
            switch_counter_delta=counter_delta,
            switch_counter_cumulative=counters_after,
            finish_reason=last_gen_dict["finish_reason"],
            num_pages_out=last_gen_dict["num_pages_out"],
            expected_pages=last_gen_dict["expected_pages"],
            time_s=last_gen_dict["time"],
            prefill_time_s=last_gen_dict["prefill_time"],
            prompt_len=len(last_gen_dict["prompt_token_ids"]),
            native_call_kwargs=cfg,
            prompt=protocol.PROMPT,
            native_infer_ms=elapsed_ms,
            vram=vram,
            clock_marks_ns=marks,
            visual_tokens=visual_tokens,
            forward_count=last_gen_dict["executed_forwards"],
            burst_extra_forwards=last_gen_dict["burst_extra_forwards"],
            static_cache_reallocations=last_gen_dict["static_cache_reallocations"],
            prefill_grouped_mm_layer_calls=int(counter_delta.get("s1a_prefill_grouped_mm_calls", 0)),
            prefill_moe_fallback_layer_calls=int(counter_delta.get("s1a_prefill_fallback_calls", 0)),
            eos_id=self.tokenizer.eos_token_id,
            eos_is_excluded_from_returned_ids=True,
            window_token_ids=ids,
            raw_output=text,
        )
        output = []
        if ok:
            for i, (page, start) in enumerate(zip(pages, indices)):
                raw = "<PAGE>" + raw_parts[i + 1]
                toks = ids[start : indices[i + 1] if i + 1 < len(indices) else len(ids)]
                output.append(
                    (
                        native_page(raw, page["points"]),
                        dict(
                            raw_output=raw,
                            token_ids=toks,
                            token_classes=token_classes(toks, self.tokenizer),
                            token_count=len(toks),
                        ),
                    )
                )
        if self.pin is not None:
            self.pin.verify(str(MODEL), str(NOTICE), self.pin.manifest)
        return output, details


def create_wp0017_engine(mode: str, run: Path, *, surgical_override: str | None = None):
    """Instantiate either a genuine existing WP-0015 endpoint or the parameterized 6-switch AblationEngine."""
    resolved = resolve_mode(mode, surgical_override=surgical_override)
    if resolved.implementation == "genuine_native":
        eng = Native(run)
        eng.info["engine_mode"] = "native"
        eng.info["canonical_mode"] = "native"
        eng.info["implementation"] = "genuine_native"
        eng.info["is_genuine_endpoint"] = True
        eng.info["observer_kind"] = OBSERVER_GENUINE_NATIVE
        eng.info["switch_bits"] = "000000"
        return eng
    if resolved.implementation == "genuine_carbon_bf16":
        from engine import CarbonEngine

        eng = CarbonEngine(run, mode="carbon_bf16")
        eng.info["canonical_mode"] = "carbon_bf16"
        eng.info["implementation"] = "genuine_carbon_bf16"
        eng.info["is_genuine_endpoint"] = True
        eng.info["observer_kind"] = OBSERVER_GENUINE_CARBON
        eng.info["switch_bits"] = "111111"
        return eng
    return AblationEngine(run, mode=mode, surgical_override=surgical_override)


def extract_engine_runtime_hooks(eng) -> dict:
    """Return exact model/tokenizer/cache hooks for serial teacher-forced probing on any WP-0017 engine."""
    if isinstance(eng, AblationEngine):
        return {
            "model": eng.model,
            "tokenizer": eng.tokenizer,
            "use_gather_decode": eng.switch_cfg.gather_sparse_decode,
            "static_cache_cls": eng.static_cache_cls,
            "switch_bits": eng.switch_cfg.bits,
            "implementation": "ablation_engine",
            "observer_kind": eng.observer_kind,
        }
    if type(eng).__name__ == "Native":
        return {
            "model": eng.model,
            "tokenizer": eng.tokenizer,
            "use_gather_decode": False,
            "static_cache_cls": None,
            "switch_bits": "000000",
            "implementation": "genuine_native",
            "observer_kind": OBSERVER_GENUINE_NATIVE,
        }
    if type(eng).__name__ == "CarbonEngine":
        closure_vars = inspect.getclosurevars(eng.model._uocr_generate).nonlocals
        static_cache_cls = closure_vars.get("static_cache_cls")
        use_gather = bool(eng.spec.get("use_gather_decode"))
        if use_gather and static_cache_cls is None:
            raise RuntimeError("Failed to extract bound StaticDashCache class from genuine CarbonEngine closure")
        return {
            "model": eng.model,
            "tokenizer": eng.tokenizer,
            "use_gather_decode": use_gather,
            "static_cache_cls": static_cache_cls,
            "switch_bits": "111111",
            "implementation": "genuine_carbon_bf16",
            "observer_kind": OBSERVER_GENUINE_CARBON,
        }
    raise TypeError(f"Unsupported engine instance for WP-0017 probe: {type(eng)!r}")
