"""Real backend for the released stage. Every heavy import is local to a method so the CPU
checks never import torch/transformers/pypdfium2 or the model's remote code.

Load recipe = upstream README, made local and offline:
  AutoTokenizer.from_pretrained(dir, trust_remote_code=True, local_files_only=True)
  AutoModel.from_pretrained(dir, trust_remote_code=True, use_safetensors=True,
                            torch_dtype=torch.bfloat16, local_files_only=True).eval().cuda()
"""

from __future__ import annotations

import importlib.metadata as md
import importlib.util
import platform
import sys
import time


class TorchBackend:
    def platform(self) -> dict:
        import torch
        out = {"os": platform.system(), "machine": platform.machine(), "python": platform.python_version(),
               "torch": torch.__version__, "torch_cuda_version": torch.version.cuda,
               "cuda_available": bool(torch.cuda.is_available())}
        if out["cuda_available"]:
            props = torch.cuda.get_device_properties(0)
            out.update({"device_count": torch.cuda.device_count(), "device_name": props.name,
                        "device_capability": list(torch.cuda.get_device_capability(0)),
                        "device_total_memory": props.total_memory, "arch_list": torch.cuda.get_arch_list(),
                        "device_uuid": str(getattr(props, "uuid", "")) or None,
                        "cudnn": torch.backends.cudnn.version()})
        return out

    def installed(self) -> dict:
        return {d.metadata["Name"]: d.version for d in md.distributions()}

    def importable(self, name: str) -> bool:
        return importlib.util.find_spec(name) is not None

    def dist_version(self, name: str) -> str:
        return md.version(name)

    def pdfium(self):
        import pypdfium2
        return pypdfium2

    def load(self, model_dir, protocol):
        t = {}
        s = time.perf_counter()
        import torch
        from transformers import AutoModel, AutoTokenizer
        t["import_torch_transformers_s"] = time.perf_counter() - s
        s = time.perf_counter()
        tok = AutoTokenizer.from_pretrained(str(model_dir), trust_remote_code=True, local_files_only=True)
        t["tokenizer_s"] = time.perf_counter() - s
        s = time.perf_counter()
        model = AutoModel.from_pretrained(str(model_dir), trust_remote_code=True, use_safetensors=True,
                                          torch_dtype=torch.bfloat16, local_files_only=True)
        t["from_pretrained_cpu_s"] = time.perf_counter() - s
        s = time.perf_counter()
        model = model.eval().cuda()
        torch.cuda.synchronize()
        t["to_cuda_synchronized_s"] = time.perf_counter() - s
        return tok, model, t

    def sync(self):
        import torch
        torch.cuda.synchronize()

    def reset_peak(self):
        import torch
        torch.cuda.reset_peak_memory_stats()

    def cuda_memory(self) -> dict:
        import torch
        free, total = torch.cuda.mem_get_info()
        return {"provenance": "direct", "max_allocated": torch.cuda.max_memory_allocated(),
                "max_reserved": torch.cuda.max_memory_reserved(), "allocated": torch.cuda.memory_allocated(),
                "reserved": torch.cuda.memory_reserved(), "device_free": free, "device_total": total,
                "note": "device_free includes other processes' use (WDDM/desktop confounder)."}

    def invoke(self, model, tokenizer, prompt, images, kwargs):
        return model.infer_multi(tokenizer, prompt=prompt, image_files=list(images), **kwargs)

    def is_oom(self, exc: BaseException) -> bool:
        if isinstance(exc, MemoryError):
            return True
        torch = sys.modules.get("torch")
        oom = getattr(getattr(torch, "cuda", None), "OutOfMemoryError", None) if torch else None
        return bool(oom and isinstance(exc, oom))
