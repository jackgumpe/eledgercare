"""WP-0023 single-resident, externally leased research trial."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
Q0 = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005")
RUNS = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0023/review/runs")
MANIFEST = ROOT / "docs/coordination/WP-0023/fixtures/manifest.json"
SOURCE_SHA = "f6df813cef23cc28b1daca40fd8cb20740d05a238e7b9dfa2334531fdcf39f1f"
GPU_ID = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"
sys.path[:0] = [str(HERE), str(HERE.parent / "engine"), str(ROOT / "docs/research/WP-0015/astra"),
                str(ROOT / "docs/research/WP-0014/eld-latency-author"), str(ROOT / "workers/local_ocr")]
from gates import ORDER, compare
from stock import stock


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(folder, name, data):
    blob = (json.dumps(data, sort_keys=True, indent=1, ensure_ascii=True, allow_nan=False) + "\n").encode()
    path = folder / (name + ".json")
    pending = path.with_suffix(".pending")
    if path.exists():
        raise FileExistsError(path)
    with pending.open("xb") as f:
        f.write(blob)
        f.flush()
        os.fsync(f.fileno())
    pending.rename(path)


def setup(output, plan_path):
    plan_bytes = plan_path.read_bytes()
    plan = json.loads(plan_bytes)
    if output.parent != RUNS.resolve() or Path(plan["output"]).resolve() != output or not plan["lease"]:
        raise ValueError("Run directory or lease identifier differs from plan")
    if Path(sys.executable).resolve() != (Q0 / "venv/Scripts/python.exe").resolve() or not sys.flags.isolated:
        raise ValueError("Use the pinned Q0 Python with -I -B")
    if not sys.flags.dont_write_bytecode or os.environ.get("CUDA_VISIBLE_DEVICES") != GPU_ID:
        raise ValueError("Need -B and the leased CUDA visibility")
    # The external guard may use a minimal PATH without Git. Resolve the host's installed Git explicitly.
    git = Path("C:/Program Files/Git/cmd/git.exe")
    def revision(*args):
        return subprocess.check_output([str(git), "-C", str(ROOT), *args], text=True).strip()
    if revision("rev-parse", "HEAD") != plan["candidate"] or revision("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Trial checkout is not clean at the leased candidate")
    manifest_bytes = MANIFEST.read_bytes()
    if sha(manifest_bytes) != plan["manifest_sha256"]:
        raise ValueError("Fixture manifest digest differs from frozen plan")
    folder = output / "trial"
    folder.mkdir(parents=True, exist_ok=False)
    # Run before any torch/HF/Triton import. -B protects startup and the effective flag protects imports;
    # the env also applies to any non-isolated interpreter child started by a compiler.
    from probe import isolated_env
    env = isolated_env(folder)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for name, rel in (("LOCALAPPDATA", "app/local"), ("APPDATA", "app/roaming"), ("PYTHONPYCACHEPREFIX", "pycache"),
                      ("TRITON_HOME", "triton-home"), ("TORCH_EXTENSIONS_DIR", "extensions"),
                      ("MPLCONFIGDIR", "mpl"), ("NUMBA_CACHE_DIR", "numba")):
        path = folder / "cache" / rel
        path.mkdir(parents=True, exist_ok=True)
        env[name] = str(path)
    os.environ.clear()
    os.environ.update(env)
    os.chdir(folder)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    from local_ocr.env_guard import audit_worker_environment
    audit_worker_environment(dict(os.environ), run_dir=folder, readonly_q0_root=Q0, leased_gpu_uuid=GPU_ID)
    write(folder, "binding", dict(plan=plan, plan_sha256=sha(plan_bytes), manifest_sha256=sha(manifest_bytes),
                                  candidate=plan["candidate"], python=sys.executable, pid=os.getpid(),
                                  started_ns=time.time_ns(), dont_write_bytecode=sys.dont_write_bytecode,
                                  environment=env))
    return folder, json.loads(manifest_bytes)


def load_images(manifest):
    from PIL import Image
    images = {}
    seen = set()
    for key in ORDER:
        pages = manifest["windows"][key]
        if len(pages) != 3:
            raise ValueError("Expected three pages per inner window")
        images[key] = []
        for row in pages:
            path = (MANIFEST.parent / row["image"]).resolve()
            if not path.is_relative_to(MANIFEST.parent) or row["page"] in seen:
                raise ValueError("Unexpected reused page or fixture path")
            seen.add(row["page"])
            data = path.read_bytes()
            if sha(data) != row["sha256"]:
                raise ValueError(f"Changed fixture {path}")
            with Image.open(io.BytesIO(data)) as opened:
                image = opened.convert("RGB")
            if image.size != (row["width"], row["height"]) or sha(image.tobytes()) != row["rgb_sha256"]:
                raise ValueError(f"Changed decoded RGB {path}")
            images[key].append(image)
    return images


class Trial:
    def __init__(self, folder, native, images):
        import native_batch
        import torch
        self.folder = folder
        self.native = native
        self.images = images
        self.batch = native_batch.run
        self.cuda = torch.cuda
        self.control = {}
        self.calls = []

    def measured(self, name, fn):
        from native import MODEL, NOTICE
        n = self.native
        n.pin.verify(str(MODEL), str(NOTICE), n.pin.manifest)
        self.cuda.synchronize()
        self.cuda.reset_peak_memory_stats()
        write(self.folder, name + "-begin", {"utc_ns": time.time_ns()})
        utc = time.time_ns()
        start = time.perf_counter_ns()
        result = fn()
        self.cuda.synchronize()
        elapsed = time.perf_counter_ns() - start
        end = time.time_ns()
        metrics = dict(start_utc_ns=utc, end_utc_ns=end, wall_ns=elapsed,
                       cuda_peak_allocated_bytes=self.cuda.max_memory_allocated(),
                       cuda_peak_reserved_bytes=self.cuda.max_memory_reserved())
        write(self.folder, name, dict(metrics=metrics, result=result))
        self.calls.append({"name": name, **metrics})
        n.pin.verify(str(MODEL), str(NOTICE), n.pin.manifest)
        return result

    def single(self, key, **kwargs):
        return stock(self.native.model, self.native.tokenizer, self.images[key], **kwargs)

    def wrapped(self, order, probe=None):
        return self.batch(self.native.model, self.native.tokenizer, [self.images[k] for k in order], probe=probe)

    def verify_order(self, arm, order, result):
        lanes = result["lanes"]
        if len(lanes) != len(order):
            raise ValueError("Engine output cardinality mismatch")
        if arm == "batch":
            forwards = result["forwards"]
            if forwards["batch_size"] != len(order) or forwards["prefill"] != 1 or forwards["decode"] < 1:
                raise ValueError("Expected one batched prefill and simultaneous native decode")
        return {k: compare(self.control[k], row) for k, row in zip(order, lanes)}

    def timing(self):
        results = []
        for label, order, arms in (("warmup", ORDER, ("native", "batch")),
                                   ("ab", ORDER, ("native", "batch")),
                                   ("ba", ORDER[::-1], ("batch", "native"))):
            for arm in arms:
                name = f"g3-{label}-{arm}"
                def go():
                    if arm == "native":
                        return {"lanes": [self.single(key) for key in order]}
                    return self.wrapped(order)
                out = self.measured(name, go)
                checks = self.verify_order(arm, order, out)
                results.append(dict(name=name, order=order, checks=checks, excluded=label == "warmup",
                                    metrics=self.calls[-1]))
                passed = all(check["passed"] for check in checks.values())
                write(self.folder, name + "-check", {"passed": passed, "checks": checks})
                if not passed:
                    return {"status": "timing-parity-failed", "arms": results}
        ratios = {}
        for label in ("ab", "ba"):
            a, b = (next(x["metrics"]["wall_ns"] for x in results if x["name"] == f"g3-{label}-{arm}")
                    for arm in ("native", "batch"))
            ratios[label] = a / b
        for x in results:
            x["pages_per_minute"] = 6 * 60e9 / x["metrics"]["wall_ns"]
        return {"status": "timing-completed", "arms": results, "native_over_batch_speedup": ratios}

    def execute(self):
        for key in ORDER:
            self.control[key] = self.measured("g1-stock-" + key, lambda: self.single(key))
        first = {}
        for key in ORDER:
            result = self.measured("g1-wrapper-" + key, lambda: self.wrapped((key,)))
            first[key] = self.verify_order("batch", (key,), result)[key]
        write(self.folder, "g1", first)
        if not all(x["passed"] for x in first.values()):
            return {"status": "g1-failed"}
        batches, checks = {}, {}
        for order in (ORDER, ORDER[::-1]):
            name = "-".join(order)
            batches[order] = self.measured("g2-" + name, lambda: self.wrapped(order))
            checks[name] = self.verify_order("batch", order, batches[order])
        write(self.folder, "g2", checks)
        if all(check["passed"] for rows in checks.values() for check in rows.values()):
            return self.timing()
        from diagnostic import diagnose
        return {"status": "g2-failed", "diagnostics": diagnose(self, batches, checks)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    folder, manifest = setup(args.output.resolve(), args.plan.resolve())
    native = None
    try:
        from native import MODEL, NOTICE, Native
        images = load_images(manifest)
        if sha((MODEL / "modeling_unlimitedocr.py").read_bytes()) != SOURCE_SHA:
            raise ValueError("Pinned stock generator digest changed")
        start = time.time_ns()
        write(folder, "cold-begin", {"utc_ns": start})
        native = Native(folder)
        from torch import cuda
        write(folder, "cold", dict(start_utc_ns=start, end_utc_ns=time.time_ns(), model=native.info,
                                   cuda_peak_allocated_bytes=cuda.max_memory_allocated(),
                                   cuda_peak_reserved_bytes=cuda.max_memory_reserved()))
        result = Trial(folder, native, images).execute()
        native.pin.verify(str(MODEL), str(NOTICE), native.pin.manifest)
        write(folder, "decision", dict(**result, finished_utc_ns=time.time_ns()))
    except BaseException as exc:
        write(folder, "error", dict(type=type(exc).__name__, message=str(exc), trace=traceback.format_exc(),
                                   utc_ns=time.time_ns()))
        raise
    finally:
        if native is not None:
            native.close()


if __name__ == "__main__":
    main()
