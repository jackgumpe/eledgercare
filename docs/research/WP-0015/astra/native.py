"""Resident, unmodified BF16 native control. The observer captures upstream tokens and EOS state."""
import inspect
import os
import sys
from pathlib import Path
from time import perf_counter_ns as clock

from formats import digest, native_page, token_classes
from local_ocr import observer, protocol, verify_runtime, worker
from generation import Generation

Q0 = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005")
GPU = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"
MODEL = Q0 / "models/Unlimited_OCR_2_04809669"
NOTICE = Q0 / "notices" / ("Unlimited-OCR-2_" + protocol.MODEL_REVISION)
LOCK_SHA = "582071bf20eaca1836c3d1cef21d31cbdaa1e1407184033a918a40612c128111"
MANIFEST_SHA = "0df07bc60abf6937c917040bced32afabd7e4d11bafc0bd99902abca610a81be"


class StageMonitor(observer.InferenceMonitor):
    def __init__(self, model):
        module = sys.modules[type(model).__module__]
        targets = observer.resolve_monitoring_targets(sys.modules, prefix=module.__package__ + ".")
        extra = {
            "build_inputs": module._uocr_build_inputs, "vision_start": model.model.sam_model.forward,
            "vision_end": model.model.projector.forward, "generate": model._uocr_generate,
            "stream": module.TextStreamer.put,
        }
        self.extra = {inspect.unwrap(f).__code__: name for name, f in extra.items()}
        for code in self.extra:
            targets[code] = observer.TargetSpec("", self.extra[code], "timing")
        super().__init__(targets)
        self.marks = {}
        self.visual_tokens = None

    def _on_start(self, code, offset):
        key = self.extra.get(code)
        if key == "stream":
            self.marks.setdefault("first_token", clock())
            self.marks["last_token"] = clock()
        elif key:
            if key == "vision_start":
                sys.modules["torch"].cuda.synchronize()
            self.marks.setdefault(key + "_start", clock())
        super()._on_start(code, offset)

    def _on_return(self, code, offset, result):
        key = self.extra.get(code)
        if key and key != "stream":
            if key == "vision_end":
                sys.modules["torch"].cuda.synchronize()
            self.marks[key + "_end"] = clock()
            if key == "build_inputs":
                self.visual_tokens = int(result[2].sum())
        super()._on_return(code, offset, result)


class Native:
    window = 3

    def __init__(self, run):
        rt = self.runtime = worker.RealTorchRuntime()
        lock, _ = verify_runtime.load_json_checked(protocol.DEPENDENCY_LOCK_PATH, LOCK_SHA, "lock")
        manifest, _ = verify_runtime.load_json_checked(protocol.MODEL_MANIFEST_PATH, MANIFEST_SHA, "manifest")
        deps = verify_runtime.verify_dependency_lock(lock, accepted_provenance_exceptions=["torchvision-local-sha256-TOFU"],
                        installed_distributions=rt.installed_distributions(), is_importable_fn=rt.is_importable)
        platform = rt.query_platform()
        verify_runtime.verify_platform_and_gpu(lock, platform, GPU)
        self.pin = Generation(str(MODEL), str(NOTICE), manifest, verify_runtime.normalize_and_verify_model_dir)
        try:
            verify_runtime.verify_model_sources_ast_safety(MODEL)
            self.tokenizer, self.model, load_ms = rt.load_model(MODEL)
            modules = verify_runtime.verify_loaded_module_cache(Path(os.environ["HF_MODULES_CACHE"]), MODEL, sys.modules)
            from torch import bfloat16
            if self.model.lm_head.weight.dtype != bfloat16:
                raise ValueError("native target dtype mismatch")
            self.info = dict(model_revision=protocol.MODEL_REVISION, manifest_sha256=MANIFEST_SHA,
                  dependency_lock_sha256=LOCK_SHA, platform=platform, dependencies=deps, verified_modules=modules,
                  load_ms=load_ms, tokenizer=type(self.tokenizer).__name__, tokenizer_sha256=digest((MODEL/"tokenizer.json").read_bytes()),
                  eos_id=self.tokenizer.eos_token_id, page_id=protocol.PAGE_TOKEN_ID, target_dtype=str(bfloat16))
        except BaseException:
            self.close()
            raise

    def close(self):
        self.pin.close()

    def read(self, pages, folder):
        self.pin.verify(str(MODEL), str(NOTICE), self.pin.manifest)
        cfg = protocol.build_call_kwargs(len(pages))
        monitor = StageMonitor(self.model)
        with monitor:
            text, count, elapsed_ms, vram = self.runtime.run_infer_multi(
                self.model, self.tokenizer, [p["image"] for p in pages], cfg)
        if len(monitor.native_results) != 1 or monitor.tripwire_hits:
            raise ValueError("native observer lost window evidence")
        result = dict(monitor.native_results[0])
        ids = result.pop("token_ids")
        if result.pop("text") != text or len(ids) != count:
            raise ValueError("raw native result mismatch")
        indices = [i for i, tok in enumerate(ids) if tok == protocol.PAGE_TOKEN_ID]
        raw_parts = text.split("<PAGE>")
        ok = (result["finish_reason"] == "stop" and result["expected_pages"] == result["num_pages_out"] == len(pages)
              and len(indices) == len(pages) and indices[0] == 0 and len(raw_parts) == len(pages) + 1 and not raw_parts[0])
        details = dict(**result, native_call_kwargs=cfg, prompt=protocol.PROMPT, native_infer_ms=elapsed_ms, vram=vram,
                   clock_marks_ns=monitor.marks, visual_tokens=monitor.visual_tokens, forward_count=monitor.forward_progress,
                   kernel_path=monitor.kernel_path_label(), triton_starts=monitor.triton_starts,
                   triton_none_returns=monitor.triton_none_returns, dense_starts=monitor.dense_starts,
                   eos_id=self.tokenizer.eos_token_id, eos_is_excluded_from_returned_ids=True,
                   window_token_ids=ids, raw_output=text)
        output = []
        if ok:
            for i, (page, start) in enumerate(zip(pages, indices)):
                raw = "<PAGE>" + raw_parts[i + 1]
                toks = ids[start:indices[i + 1] if i + 1 < len(indices) else len(ids)]
                output.append((native_page(raw, page["points"]), dict(raw_output=raw, token_ids=toks,
                        token_classes=token_classes(toks, self.tokenizer), token_count=len(toks))))
        self.pin.verify(str(MODEL), str(NOTICE), self.pin.manifest)
        return output, details
