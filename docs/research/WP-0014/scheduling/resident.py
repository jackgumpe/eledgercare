"""One diagnostic process owns one verified model and at most one synchronous inference."""
import functools
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from local_ocr import worker
from local_ocr.protocol import compute_worker_source_sha256, compute_config_digest, MODEL_MANIFEST_PATH, DEPENDENCY_LOCK_PATH
from local_ocr import REQUEST_SCHEMA
from local_ocr.pins import ReadOnlyGeneration


def write(path, data):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data), encoding="utf8")
    tmp.replace(path)


def mem():
    import torch
    return {"allocated": torch.cuda.memory_allocated(), "reserved": torch.cuda.memory_reserved()}


class Resident(worker.RealTorchRuntime):
    def __init__(self, trace):
        self.trace = trace
        self.pair = None
        self.anchor = None

    @functools.cache
    def installed_distributions(self):
        return super().installed_distributions()

    @functools.cache
    def query_platform(self):
        return super().query_platform()

    def verified_dir(self, model, notices, manifest):
        identity = (model, notices, json.dumps(manifest, sort_keys=True))
        if self.anchor is None:
            self.pins = ReadOnlyGeneration(model, notices)
            self.anchor = (identity, worker.normalize_and_verify_model_dir(model, notices, manifest))
        self.pins.check()
        assert identity == self.anchor[0]
        return self.anchor[1]

    def load_model(self, path):
        if self.pair is None:
            self.trace("model_load_start")
            tokenizer, model, elapsed = super().load_model(path)
            self.pair = (tokenizer, model)
            self.trace("model_load_end", **mem())
            return tokenizer, model, elapsed
        return *self.pair, 0

    def run_infer_multi(self, model, tokenizer, images, kwargs):
        self.trace("infer_start", **mem())
        result = super().run_infer_multi(model, tokenizer, images, kwargs)
        self.trace("infer_end", **mem(), peak=result[3])
        return result


def main(root):
    args = json.loads((root / "config.json").read_text())
    ctl = root / "control"
    current = "W"
    def trace(event, **kwargs):
        with (root / "engine.jsonl").open("a", encoding="utf8") as out:
            print(json.dumps(dict(event=event, t_ms=time.time_ns()/1e6, mono_ns=time.perf_counter_ns(), pid=os.getpid(), item=current, **kwargs)), file=out)
    trace("engine_entry")
    if args["cpu_crash"]:
        trace("injected_cpu_crash")
        os._exit(37)
    q0 = Path(args["q0"])
    warm_dir = root / "runs/warmup"
    pdf = warm_dir / "input/document.pdf"
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == args["hashes"]["W"]
    paths = {"schema":REQUEST_SCHEMA,"document_id":"warmup","job_id":"warmup","attempt_id":"warmup","fencing_token":1,
             "writable_runtime_root":str(root),"readonly_q0_root":str(q0),"input_pdf_path":str(pdf),
             "expected_input_sha256":args["hashes"]["W"],"expected_input_byte_length":pdf.stat().st_size,"expected_page_count":1,
             "model_dir":str(q0 / "models/Unlimited_OCR_2_04809669"),
             "notice_dir":str(q0 / "notices/Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"),
             "leased_gpu_uuid":args["gpu"],"accepted_provenance_exceptions":["torchvision-local-sha256-TOFU"],
             "expected_worker_source_sha256":compute_worker_source_sha256(),"expected_worker_config_sha256":compute_config_digest(1),
             "expected_model_manifest_sha256":hashlib.sha256(MODEL_MANIFEST_PATH.read_bytes()).hexdigest(),
             "expected_dependency_lock_sha256":hashlib.sha256(DEPENDENCY_LOCK_PATH.read_bytes()).hexdigest()}
    req_path = warm_dir / "request.json"
    write(req_path, paths)
    rt = Resident(trace)
    if args["mode"] != "demandfirst":
        trace("warmup_start")
        if worker.execute_request_file(req_path, rt):
            raise RuntimeError("warmup failed; inspect its envelope")
        trace("ready_after_warmup", **mem())
        write(ctl / "ready", {"pid":os.getpid(),"t_ms":time.time_ns()/1e6})
    processed = set()
    admitted = sorted(args["inputs"])
    seen = []
    while len(seen) < len(admitted):
        for item in sorted(ctl.glob("*.job")):
            if item in processed:
                continue
            entry = json.loads(item.read_text())
            req_path = Path(entry["path"]).resolve()
            assert req_path.parent.parent == root / "runs" and req_path.name == "request.json"
            req = json.loads(req_path.read_text())
            assert item.stem == req["attempt_id"] and req["expected_page_count"] == 1
            for key in ("writable_runtime_root","readonly_q0_root","model_dir","notice_dir","leased_gpu_uuid",
                        "expected_worker_source_sha256","expected_worker_config_sha256","expected_model_manifest_sha256","expected_dependency_lock_sha256"):
                assert req[key] == paths[key], key
            current = next(k for k in set(admitted) if args["hashes"][k] == req["expected_input_sha256"])
            seen.append(current)
            assert seen.count(current) <= admitted.count(current)
            trace("job_start", attempt=item.stem)
            code = worker.execute_request_file(req_path, rt)
            trace("job_end", attempt=item.stem, code=code, **mem())
            item.with_suffix(".done").write_text(str(code))
            processed.add(item)
            if code:
                raise RuntimeError("real job failed; no retry")
        time.sleep(.02)
    trace("idle_after_all_jobs", **mem())
    while not (ctl / "retire").exists():
        time.sleep(.03)
    trace("retire")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
