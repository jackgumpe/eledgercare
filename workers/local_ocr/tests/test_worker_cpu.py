"""Stdlib CPU unit tests for workers/local_ocr (no GPU, no torch/model imports)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

WORKER_ROOT = Path(__file__).resolve().parent.parent
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from local_ocr import ENVELOPE_SCHEMA, REQUEST_SCHEMA
from local_ocr.env_guard import audit_worker_environment, current_process_create_filetime
from local_ocr.observer import InferenceMonitor, SafetyTripwire, resolve_monitoring_targets
from local_ocr.protocol import (
    DEPENDENCY_LOCK_PATH,
    MODEL_MANIFEST_PATH,
    PAGE_TOKEN_ID,
    WorkerError,
    build_call_kwargs,
    call_timeout_for_pages,
    compute_config_digest,
    compute_worker_source_sha256,
    file_digests,
    git_blob_sha1_bytes,
    sha256_bytes,
)
from local_ocr.verify_runtime import (
    MODEL_PY_MODULES,
    verify_dependency_lock,
    verify_model_sources_ast_safety,
)
from local_ocr.worker import execute_request_file


def _valid_entry_source(extra_code: str = "", guard_expr: str = "save_results and output_path") -> str:
    return f"""
def extract_coordinates_and_label(s):
    return eval(s)

def draw_bounding_boxes(img, refs):
    return extract_coordinates_and_label(refs)

def process_image_with_refs(img, refs):
    return draw_bounding_boxes(img, refs)

class UnlimitedOCRModel:
    def forward(self, x):
        return x

class UnlimitedOCRForCausalLM:
    def _uocr_save_results(self, out):
        return process_image_with_refs(None, out)

    def infer(self, tokenizer, prompt='', save_results=False, output_path='', **kwargs):
        if {guard_expr}:
            self._uocr_save_results('1+1')
        return {{
            'finish_reason': 'stop',
            'num_pages_out': 1,
            'expected_pages': 1,
            'time': 1.0,
            'prefill_time': 0.2,
            'prompt_token_ids': [1, 2, 3],
            'token_ids': [{PAGE_TOKEN_ID}, 42],
            'text': '<PAGE>ok',
        }}

    def infer_multi(self, tokenizer, prompt='', image_files=None, **kwargs):
        res = self.infer(tokenizer, prompt=prompt, **kwargs)
        return res['text'], len(res['token_ids'])
{extra_code}
"""


def _build_env(run_dir: Path, gpu_uuid: str = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d") -> dict[str, str]:
    c = run_dir / "cache"
    return {
        "SystemRoot": r"C:\Windows",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_XET": "1",
        "PIP_NO_INDEX": "1",
        "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
        "CUDA_VISIBLE_DEVICES": gpu_uuid,
        "TEMP": str(c / "tmp"),
        "TMP": str(c / "tmp"),
        "TMPDIR": str(c / "tmp"),
        "USERPROFILE": str(c / "home"),
        "HOME": str(c / "home"),
        "HF_HOME": str(c / "hf-home"),
        "HF_HUB_CACHE": str(c / "hf-home" / "hub"),
        "HUGGINGFACE_HUB_CACHE": str(c / "hf-home" / "hub"),
        "TRANSFORMERS_CACHE": str(c / "hf-home" / "transformers"),
        "HF_MODULES_CACHE": str(c / "hf-modules"),
        "TORCH_HOME": str(c / "torch-home"),
        "TRITON_CACHE_DIR": str(c / "triton-cache"),
        "TORCHINDUCTOR_CACHE_DIR": str(c / "inductor-cache"),
        "CUDA_CACHE_PATH": str(c / "cuda-cache"),
        "XDG_CACHE_HOME": str(c / "xdg-cache"),
        "PIP_CACHE_DIR": str(c / "pip-cache"),
        "UV_CACHE_DIR": str(c / "uv-cache"),
    }


class WorkerCpuTests(unittest.TestCase):
    def test_worker_sources_have_zero_qualification_research_evaluation_or_git_calls(self):
        py_files = [WORKER_ROOT / "run_worker.py", *sorted((WORKER_ROOT / "local_ocr").glob("*.py"))]
        for p in py_files:
            src = p.read_text(encoding="utf-8")
            for forbidden in ("qualification", "evaluation", "q0harness", "git.exe", "cat-file"):
                self.assertNotIn(forbidden, src, f"Forbidden token {forbidden!r} in {p}")

    def test_self_contained_manifests_match_contract_pins(self):
        model_man = json.loads(MODEL_MANIFEST_PATH.read_text(encoding="utf-8"))
        dep_lock = json.loads(DEPENDENCY_LOCK_PATH.read_text(encoding="utf-8"))
        self.assertEqual(model_man["runtime_object_count"], 18)
        self.assertEqual(len(model_man["files"]), 18)
        self.assertEqual(len(model_man["notices"]), 1)
        self.assertEqual(dep_lock["distribution_count"], 32)
        self.assertEqual(len(dep_lock["distributions"]), 32)
        self.assertEqual(dep_lock["required_provenance_exceptions"], ["torchvision-local-sha256-TOFU"])

        installed = {d["name"]: d["version"] for d in dep_lock["distributions"]}
        installed["pip"] = "25.0.1"
        res = verify_dependency_lock(
            dep_lock,
            accepted_provenance_exceptions=["torchvision-local-sha256-TOFU"],
            installed_distributions=installed,
            is_importable_fn=lambda _m: False,
        )
        self.assertEqual(res["verified_distribution_count"], 32)

        with self.assertRaises(WorkerError):
            verify_dependency_lock(
                dep_lock,
                accepted_provenance_exceptions=[],
                installed_distributions=installed,
                is_importable_fn=lambda _m: False,
            )
        with self.assertRaises(WorkerError):
            verify_dependency_lock(
                dep_lock,
                accepted_provenance_exceptions=["torchvision-local-sha256-TOFU"],
                installed_distributions=installed,
                is_importable_fn=lambda m: m == "triton",
            )

    def test_call_kwargs_and_page_timeouts(self):
        kw1 = build_call_kwargs(1)
        self.assertEqual(kw1["max_new_tokens"], 8000)
        self.assertEqual(kw1["ngram_window"], 128)
        self.assertIs(kw1["save_results"], False)
        self.assertEqual(kw1["output_path"], "")

        kw3 = build_call_kwargs(3)
        self.assertEqual(kw3["max_new_tokens"], 24000)
        self.assertEqual(kw3["ngram_window"], 1024)
        self.assertEqual(call_timeout_for_pages(1), 1800)
        self.assertEqual(call_timeout_for_pages(2), 2700)
        self.assertEqual(call_timeout_for_pages(3), 3600)
        with self.assertRaises(WorkerError):
            build_call_kwargs(4)

    def test_environment_guard_and_process_filetime(self):
        ft = current_process_create_filetime()
        self.assertGreater(ft, 130_000_000_000_000_000)
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            run_dir = base / "f2" / "runs" / "attempt-1"
            q0_root = base / "q0"
            env = _build_env(run_dir)
            audit_worker_environment(
                env,
                run_dir=run_dir,
                readonly_q0_root=q0_root,
                leased_gpu_uuid="GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d",
            )

            bad_secret = dict(env, ConnectionStrings__Runtime="Host=127.0.0.1;Password=secret")
            with self.assertRaises(WorkerError):
                audit_worker_environment(
                    bad_secret,
                    run_dir=run_dir,
                    readonly_q0_root=q0_root,
                    leased_gpu_uuid="GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d",
                )

            bad_cache = dict(env, HF_HOME=str(q0_root / "hf-home"))
            with self.assertRaises(WorkerError):
                audit_worker_environment(
                    bad_cache,
                    run_dir=run_dir,
                    readonly_q0_root=q0_root,
                    leased_gpu_uuid="GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d",
                )

    def test_static_ast_verifier_enforces_unreachable_eval_guard(self):
        with tempfile.TemporaryDirectory() as td:
            mdir = Path(td)
            for name in MODEL_PY_MODULES:
                (mdir / name).write_text("x = 1\n", encoding="utf-8")
            (mdir / "modeling_unlimitedocr.py").write_text(_valid_entry_source(), encoding="utf-8")
            verify_model_sources_ast_safety(mdir)

            (mdir / "modeling_unlimitedocr.py").write_text(
                _valid_entry_source(guard_expr="save_results or True"), encoding="utf-8"
            )
            with self.assertRaises(WorkerError):
                verify_model_sources_ast_safety(mdir)

            (mdir / "modeling_unlimitedocr.py").write_text(_valid_entry_source(), encoding="utf-8")
            (mdir / "dash_attention.py").write_text("def bad(x): return eval(x)\n", encoding="utf-8")
            with self.assertRaises(WorkerError):
                verify_model_sources_ast_safety(mdir)

    def test_sys_monitoring_captures_native_dict_and_fires_tripwire_before_eval(self):
        eval_executed = False

        mod_uocr = types.ModuleType("transformers_modules.test_pkg.modeling_unlimitedocr")
        mod_dash = types.ModuleType("transformers_modules.test_pkg.dash_attention")

        def extract_coordinates_and_label(_s):
            nonlocal eval_executed
            eval_executed = True
            return 123

        def draw_bounding_boxes(img, refs):
            return extract_coordinates_and_label(refs)

        def process_image_with_refs(img, refs):
            return draw_bounding_boxes(img, refs)

        class UnlimitedOCRModel:
            def forward(self, x):
                return x

        class UnlimitedOCRForCausalLM:
            def _uocr_save_results(self, out):
                return process_image_with_refs(None, out)

            def infer(self, trip=False):
                UnlimitedOCRModel().forward(1)
                DashAttention()._forward_triton()
                DashAttention()._forward_dense()
                if trip:
                    self._uocr_save_results("bad")
                return {
                    "finish_reason": "stop",
                    "num_pages_out": 1,
                    "expected_pages": 1,
                    "time": 0.5,
                    "prefill_time": 0.1,
                    "prompt_token_ids": [10, 11],
                    "token_ids": [PAGE_TOKEN_ID, 99],
                    "text": "<PAGE>hello",
                }

        class DashAttention:
            def _forward_triton(self):
                try:
                    raise ImportError("No module named 'triton'")
                except ImportError:
                    return None

            def _forward_dense(self):
                return "dense"

        mod_uocr.extract_coordinates_and_label = extract_coordinates_and_label
        mod_uocr.draw_bounding_boxes = draw_bounding_boxes
        mod_uocr.process_image_with_refs = process_image_with_refs
        mod_uocr.UnlimitedOCRModel = UnlimitedOCRModel
        mod_uocr.UnlimitedOCRForCausalLM = UnlimitedOCRForCausalLM
        mod_dash.DashAttention = DashAttention

        fake_modules = {
            "transformers_modules.test_pkg.modeling_unlimitedocr": mod_uocr,
            "transformers_modules.test_pkg.dash_attention": mod_dash,
        }
        targets = resolve_monitoring_targets(fake_modules, prefix="transformers_modules.test_pkg.")

        with InferenceMonitor(targets) as mon:
            UnlimitedOCRForCausalLM().infer(trip=False)
            self.assertEqual(mon.forward_progress, 1)
            self.assertEqual(len(mon.native_results), 1)
            self.assertEqual(mon.kernel_path_label(), "triton_import_failed_dense_fallback")

            with self.assertRaises(SafetyTripwire):
                UnlimitedOCRForCausalLM().infer(trip=True)

        self.assertFalse(eval_executed)

    def test_execute_request_file_completes_and_handles_truncation_honestly(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            q0_root = base / "q0"
            writable_root = base / "f2-author"
            model_dir = q0_root / "models" / "Unlimited_OCR_2_04809669"
            notice_dir = q0_root / "notices" / "Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"
            model_dir.mkdir(parents=True)
            notice_dir.mkdir(parents=True)

            # Build matching synthetic model_dir + custom manifest for offline unit verification
            custom_files = []
            for fname in MODEL_PY_MODULES:
                body = _valid_entry_source() if fname == "modeling_unlimitedocr.py" else "x = 1\n"
                raw = body.encode("utf-8")
                (model_dir / fname).write_bytes(raw)
                custom_files.append({
                    "path": fname,
                    "size": len(raw),
                    "git_blob_sha1": git_blob_sha1_bytes(raw),
                    "digest_kind": "git_blob_sha1",
                })
            for idx in range(18 - len(MODEL_PY_MODULES)):
                fname = f"asset_{idx}.json"
                raw = b"{}"
                (model_dir / fname).write_bytes(raw)
                custom_files.append({
                    "path": fname,
                    "size": len(raw),
                    "git_blob_sha1": git_blob_sha1_bytes(raw),
                    "digest_kind": "git_blob_sha1",
                })
            notice_raw = b"# Model Card\n"
            (notice_dir / "README.md").write_bytes(notice_raw)
            custom_manifest = {
                "schema": "eledgercare.local-ocr-model-manifest/1",
                "repo_id": "baidu/Unlimited-OCR-2",
                "revision": "0480966938291445591f69f08a13b041c073a96a",
                "model_dir_basename": "Unlimited_OCR_2_04809669",
                "runtime_object_count": 18,
                "files": custom_files,
                "notices": [{
                    "path": "README.md",
                    "size": len(notice_raw),
                    "git_blob_sha1": git_blob_sha1_bytes(notice_raw),
                    "digest_kind": "git_blob_sha1",
                }],
            }
            custom_manifest_path = base / "custom-model-files.json"
            custom_manifest_path.write_text(json.dumps(custom_manifest), encoding="utf-8")
            dep_lock = json.loads(DEPENDENCY_LOCK_PATH.read_text(encoding="utf-8"))

            def make_attempt(name: str, finish_reason: str):
                run_dir = writable_root / "runs" / name
                (run_dir / "input").mkdir(parents=True)
                hf_mods = run_dir / "cache" / "hf-modules" / "Unlimited_OCR_2_04809669"
                hf_mods.mkdir(parents=True)
                (hf_mods / "__init__.py").write_bytes(b"")
                (hf_mods / "modeling_unlimitedocr.py").write_bytes((model_dir / "modeling_unlimitedocr.py").read_bytes())

                pdf_bytes = b"%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF\n"
                pdf_path = run_dir / "input" / "document.pdf"
                pdf_path.write_bytes(pdf_bytes)

                req = {
                    "schema": REQUEST_SCHEMA,
                    "document_id": "019a0000-0000-7000-8000-000000000001",
                    "job_id": "019a0000-0000-7000-8000-000000000002",
                    "attempt_id": "019a0000-0000-7000-8000-000000000003",
                    "fencing_token": 7,
                    "writable_runtime_root": str(writable_root),
                    "readonly_q0_root": str(q0_root),
                    "input_pdf_path": str(pdf_path),
                    "expected_input_sha256": sha256_bytes(pdf_bytes),
                    "expected_input_byte_length": len(pdf_bytes),
                    "expected_page_count": 1,
                    "model_dir": str(model_dir),
                    "notice_dir": str(notice_dir),
                    "leased_gpu_uuid": "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d",
                    "expected_model_manifest_sha256": file_digests(custom_manifest_path)["sha256"],
                    "expected_dependency_lock_sha256": file_digests(DEPENDENCY_LOCK_PATH)["sha256"],
                    "expected_worker_source_sha256": compute_worker_source_sha256(),
                    "expected_worker_config_sha256": compute_config_digest(1),
                    "accepted_provenance_exceptions": ["torchvision-local-sha256-TOFU"],
                    "guards": {
                        "load_timeout_s": 60,
                        "call_timeout_s": 60,
                        "heartbeat_interval_s": 0.5,
                        "max_raw_output_bytes": 16 * 1024 * 1024,
                        "min_free_disk_bytes": 1024,
                        "max_runtime_root_bytes": 4 * 1024 * 1024 * 1024,
                    },
                }
                req_path = run_dir / "request.json"
                req_path.write_text(json.dumps(req), encoding="utf-8")

                # Build dynamic modules in sys.modules for monitor + cache check
                pkg = f"transformers_modules.pkg_{name.replace('-', '_')}"
                mod_root = types.ModuleType("transformers_modules")
                mod_pkg = types.ModuleType(pkg)
                mod_pkg.__file__ = str(hf_mods / "__init__.py")
                mod_uocr = types.ModuleType(f"{pkg}.modeling_unlimitedocr")
                mod_uocr.__file__ = str(hf_mods / "modeling_unlimitedocr.py")
                mod_dash = types.ModuleType(f"{pkg}.dash_attention")

                class DashAttention:
                    def _forward_triton(self):
                        try:
                            raise ImportError("no triton")
                        except ImportError:
                            return None

                    def _forward_dense(self):
                        return 1

                class UnlimitedOCRModel:
                    def forward(self, x):
                        return x

                class UnlimitedOCRForCausalLM:
                    def _uocr_save_results(self, x):
                        return x

                    def infer(self, _tok, **_kw):
                        UnlimitedOCRModel().forward(1)
                        DashAttention()._forward_triton()
                        DashAttention()._forward_dense()
                        return {
                            "finish_reason": finish_reason,
                            "num_pages_out": 1,
                            "expected_pages": 1,
                            "time": 0.25,
                            "prefill_time": 0.05,
                            "prompt_token_ids": [1, 2, 3],
                            "token_ids": [PAGE_TOKEN_ID, 77],
                            "text": "<PAGE><BLOCK>text[1,2,3,4]<FORK>Synthetic Maintenance Record",
                        }

                    def infer_multi(self, tok, prompt="", image_files=None, **kw):
                        res = self.infer(tok, prompt=prompt, **kw)
                        return res["text"], len(res["token_ids"])

                UnlimitedOCRForCausalLM.__module__ = f"{pkg}.modeling_unlimitedocr"
                mod_uocr.UnlimitedOCRForCausalLM = UnlimitedOCRForCausalLM
                mod_uocr.UnlimitedOCRModel = UnlimitedOCRModel
                mod_uocr.process_image_with_refs = lambda *a: None
                mod_uocr.draw_bounding_boxes = lambda *a: None
                mod_uocr.extract_coordinates_and_label = lambda *a: None
                mod_dash.DashAttention = DashAttention

                class StubImg:
                    mode = "RGB"
                    width = 2550
                    height = 3301

                    def convert(self, _m):
                        return self

                    def tobytes(self):
                        return b"rgb-bytes"

                class StubPage:
                    def render(self, scale):
                        class Bmp:
                            def to_pil(self_inner):
                                return StubImg()
                        return Bmp()

                    def close(self):
                        pass

                class StubPdfium:
                    version = types.SimpleNamespace(PDFIUM_INFO="159.0.8149.0")

                    class PdfDocument:
                        def __init__(self, _b):
                            pass

                        def __len__(self):
                            return 1

                        def __getitem__(self, _i):
                            return StubPage()

                        def close(self):
                            pass

                class StubRuntime:
                    def installed_distributions(self):
                        d = {x["name"]: x["version"] for x in dep_lock["distributions"]}
                        d["pip"] = "25.0.1"
                        return d

                    def is_importable(self, _n):
                        return False

                    def dist_version(self, _n):
                        return "5.15.2"

                    def import_pdfium(self):
                        return StubPdfium

                    def query_platform(self):
                        return {
                            "os": "Windows",
                            "machine": "AMD64",
                            "python": "3.12.10",
                            "cuda_available": True,
                            "torch_cuda_version": "13.0",
                            "device_count": 1,
                            "device_capability": [12, 0],
                            "arch_list": ["sm_120"],
                            "device_uuid": "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d",
                        }

                    def load_model(self, _mdir):
                        return object(), UnlimitedOCRForCausalLM(), 12

                    def run_infer_multi(self, model, tok, images, call_kwargs):
                        text, ntok = model.infer_multi(tok, image_files=images, **call_kwargs)
                        return text, ntok, 34, {"cuda_max_allocated_bytes": 100, "cuda_max_reserved_bytes": 200}

                    def is_oom(self, exc):
                        return isinstance(exc, MemoryError)

                env = _build_env(run_dir)
                mod_patch = {
                    "transformers_modules": mod_root,
                    pkg: mod_pkg,
                    f"{pkg}.modeling_unlimitedocr": mod_uocr,
                    f"{pkg}.dash_attention": mod_dash,
                }
                with patch("local_ocr.worker.MODEL_MANIFEST_PATH", custom_manifest_path), patch.dict(
                    os.environ, env, clear=True
                ), patch.dict(sys.modules, mod_patch):
                    rc = execute_request_file(req_path, runtime=StubRuntime())
                return rc, run_dir

            rc_ok, dir_ok = make_attempt("attempt-ok", "stop")
            self.assertEqual(rc_ok, 0)
            env_ok = json.loads((dir_ok / "output" / "envelope.json").read_text(encoding="utf-8"))
            self.assertEqual(env_ok["schema"], ENVELOPE_SCHEMA)
            self.assertEqual(env_ok["status"], "completed")
            raw_bytes = (dir_ok / "output" / "raw_output.utf8.bin").read_bytes()
            self.assertEqual(sha256_bytes(raw_bytes), env_ok["output"]["sha256"])

            rc_trunc, dir_trunc = make_attempt("attempt-trunc", "length")
            self.assertEqual(rc_trunc, 2)
            env_trunc = json.loads((dir_trunc / "output" / "envelope.json").read_text(encoding="utf-8"))
            self.assertEqual(env_trunc["status"], "failed")
            self.assertEqual(env_trunc["failure"]["code"], "model_output_truncated")
            self.assertIn("Synthetic Maintenance Record", env_trunc["failure"]["diagnostic_raw_output_utf8"])
            self.assertFalse((dir_trunc / "output" / "raw_output.utf8.bin").exists())


if __name__ == "__main__":
    unittest.main()
