"""Research-only in-process instrumentation around the unchanged F2 request entry and native model."""
from time import perf_counter_ns as now
ENTRY = now()
import contextlib
import functools
import inspect
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cases import GPU, PAGES, Q0, REFERENCE, SHA, TEXT, WORKER, assess, digest, dump, materialize, read
from fixtures import scan_pdf
sys.path.insert(0, str(WORKER))
from local_ocr import observer, protocol, verify_runtime, worker
from local_ocr.env_guard import audit_worker_environment
from local_ocr.pdf_render import read_and_render_pdf, verify_renderer_identity

events = []
monitors = []


@contextlib.contextmanager
def span(label, **details):
    begin = now()
    try:
        yield
    finally:
        events.append(dict(label=label, start_ns=begin, end_ns=now(), **details))


def measure(owner, name):
    original = getattr(owner, name)
    @functools.wraps(original)
    def observed(*args, **kwargs):
        details = {"file": str(args[0])} if name == "file_digests" else {}
        with span(name, **details):
            return original(*args, **kwargs)
    setattr(owner, name, observed)


def verify_cpu(run):
    import pypdfium2 as pdfium
    from tokenizers import Tokenizer
    req = read(run / "request.json")
    audit_worker_environment(dict(os.environ), run_dir=run, readonly_q0_root=Q0, leased_gpu_uuid=GPU)
    assert protocol.compute_worker_source_sha256() == req["expected_worker_source_sha256"]
    assert protocol.compute_config_digest(1) == req["expected_worker_config_sha256"]
    manifest, _ = verify_runtime.load_json_checked(protocol.MODEL_MANIFEST_PATH, req["expected_model_manifest_sha256"], "manifest")
    lock, _ = verify_runtime.load_json_checked(protocol.DEPENDENCY_LOCK_PATH, req["expected_dependency_lock_sha256"], "lock")
    rt = worker.RealTorchRuntime()
    verify_runtime.verify_dependency_lock(lock, accepted_provenance_exceptions=req["accepted_provenance_exceptions"],
                                          installed_distributions=rt.installed_distributions(), is_importable_fn=rt.is_importable)
    renderer = verify_renderer_identity(pdfium, rt.dist_version, lock)
    model_dir = Path(req["model_dir"])
    verify_runtime.verify_model_sources_ast_safety(model_dir)
    tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
    observations = {}
    for key, path in PAGES.items():
        if key in TEXT:
            assert scan_pdf(TEXT[key]) == path.read_bytes()
        materialize(run, key)
        case = read(run / "request.json")
        with pdfium.PdfDocument(path) as doc:
            page = doc[0]
            textpage = page.get_textpage()
            assert textpage.count_chars() == 0
            textpage.close()
            page.close()
        images, rasters = read_and_render_pdf(pdfium, path, expected_sha256=SHA[key],
                                              expected_byte_length=case["expected_input_byte_length"], expected_page_count=1)
        observations[key] = dict(sha256=SHA[key], bytes=path.stat().st_size, text_layer_chars=0, rasters=rasters)
        if key in TEXT:
            observations[key]["expected_plain_text_tokens_without_structure"] = len(tokenizer.encode(TEXT[key], add_special_tokens=False).ids)
        images[0].close()
    reference = assess("S", REFERENCE / "output")
    assert sum(x["exact"] for x in reference["table_cells"].values()) == 18
    assert len(reference["table_cells"]) == 19
    assert all(reference["printed_fields_present"].values())
    assert "torch" not in sys.modules
    dump(run / "cpu.json", dict(fixtures=observations, renderer=renderer, model_revision=manifest["revision"],
                                worker_source=req["expected_worker_source_sha256"], config=req["expected_worker_config_sha256"],
                                dependency_lock=req["expected_dependency_lock_sha256"], model_manifest=req["expected_model_manifest_sha256"],
                                reference_S=reference, production_call_kwargs=protocol.build_call_kwargs(1)))


class PhaseMonitor(observer.InferenceMonitor):
    """Additional local PEP 669 events record boundaries without replacing any native method."""
    def __init__(self, targets):
        super().__init__(targets)
        model = runtime.loaded[1]
        module = sys.modules[type(model).__module__]
        streamer = module.TextStreamer if hasattr(module, "TextStreamer") else sys.modules["transformers"].TextStreamer
        watched = {
            "infer_multi": model.infer_multi, "build_inputs": module._uocr_build_inputs, "generate": model._uocr_generate,
            "vision_first_sam": model.model.sam_model.forward, "vision_last_projector": model.model.projector.forward,
            "streamer_put": streamer.put,
        }
        self.extra = {inspect.unwrap(obj).__code__: label for label, obj in watched.items()}
        for code, label in self.extra.items():
            self.targets[code] = observer.TargetSpec("", label, "wp0014_clock")
        self.marks = {}
        self.emitted = 0
        monitors.append(self)

    def _on_start(self, code, offset):
        label = self.extra.get(code)
        if label == "streamer_put":
            self.emitted += 1
            if self.emitted == 1:
                sys.modules["torch"].cuda.synchronize()
                self.marks["first_token_streamer_enter_synced"] = now()
            self.marks["last_token_streamer_enter"] = now()
        elif label:
            if label == "vision_first_sam":
                sys.modules["torch"].cuda.synchronize()
            self.marks[label + "_start"] = now()
        super()._on_start(code, offset)

    def _on_return(self, code, offset, result):
        label = self.extra.get(code)
        if label and label != "streamer_put":
            if label == "vision_last_projector":
                sys.modules["torch"].cuda.synchronize()
            self.marks[label + "_end"] = now()
        super()._on_return(code, offset, result)


class ResidentRuntime(worker.RealTorchRuntime):
    loaded = None
    platform = None

    def query_platform(self):
        if self.platform is None:
            with span("import_torch"):
                import torch
            with span("query_platform_with_cuda"):
                self.platform = super().query_platform()
        return self.platform

    def load_model(self, model_dir):
        if self.loaded is None:
            with span("import_transformers_AutoModel_AutoTokenizer"):
                from transformers import AutoModel, AutoTokenizer
            with span("named_load_real"):
                tokenizer, model, ms = super().load_model(model_dir)
            self.loaded = tokenizer, model
            self.model_dir = model_dir
            return tokenizer, model, ms
        assert model_dir == self.model_dir
        return *self.loaded, 0


def measure_integrity_once():
    # Process-owned Q0 model is fixed, read-only by assignment. Per-request pinned manifests, input bytes,
    # worker configuration, renderer, loaded custom module cache and all result checks still run.
    original = worker.normalize_and_verify_model_dir
    bound = None
    result = None
    def verified(model, notice, manifest):
        nonlocal bound, result
        key = (model, notice, manifest)
        if bound is None:
            with span("normalize_and_verify_model_dir"):
                result = original(*key)
            bound = key
        assert key == bound
        return result
    worker.normalize_and_verify_model_dir = verified
    worker.verify_model_sources_ast_safety = functools.lru_cache(maxsize=1)(worker.verify_model_sources_ast_safety)


def resident(run, sequence):
    global runtime
    runtime = ResidentRuntime()
    worker.InferenceMonitor = PhaseMonitor
    for name in ("compute_worker_source_sha256", "compute_config_digest", "load_json_checked", "audit_worker_environment",
                 "verify_storage_guards", "verify_dependency_lock", "verify_platform_and_gpu", "verify_model_sources_ast_safety",
                 "verify_renderer_identity", "read_and_render_pdf", "verify_loaded_module_cache", "resolve_monitoring_targets",
                 "write_exclusive_bytes", "write_envelope_atomic"):
        measure(worker, name)
    for name in ("installed_distributions", "import_pdfium", "run_infer_multi"):
        measure(runtime, name)
    measure(verify_runtime, "file_digests")
    measure_integrity_once()
    for index, key in enumerate(sequence, 1):
        events.clear()
        begin = now()
        materialize(run, key)
        request_ready = now()
        rc = worker.execute_request_file(run / "request.json", runtime)
        done = now()
        out = run / f"{index}-{key}"
        (run / "output").rename(out)
        dump(out / "events.json", dict(child_entry_ns=ENTRY, worker_imported_ns=IMPORTED, pid=os.getpid(),
                                       request_start_ns=begin, request_ready_ns=request_ready, output_complete_ns=done,
                                       exit_code=rc, spans=events))
        assert rc == 0, read(out / "envelope.json").get("failure")
        m = monitors.pop()
        native = m.native_results[0]
        ids = native["token_ids"]
        assert m.emitted == len(ids) and m.forward_progress == len(ids) + 1
        dump(out / "native.json", dict(native={k: v for k, v in native.items() if k not in ("token_ids", "text")},
                                       token_ids=ids, marks_ns=m.marks, forward_count=m.forward_progress,
                                       dense_starts=m.dense_starts, triton_starts=m.triton_starts, triton_none_returns=m.triton_none_returns))
        dump(out / "score.json", assess(key, out))
        print(f"WP-0014 completed {index}-{key}", flush=True)


IMPORTED = now()
if __name__ == "__main__":
    mode, path = sys.argv[1:]
    if mode == "cpu":
        verify_cpu(Path(path))
    elif mode in ("resident", "resident-short"):
        resident(Path(path), "ABABAS" if mode == "resident" else "ABA")
    else:
        raise ValueError(mode)
