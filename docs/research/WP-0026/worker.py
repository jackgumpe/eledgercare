"""Run exactly one signed W0-conditioned resident process. Usage: worker.py PLAN SHA256."""
from argparse import ArgumentParser
from contextlib import closing, contextmanager, redirect_stdout
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNS = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0026/review/runs")
sys.path.insert(0, str(ROOT / "docs/research/WP-0025/runner"))
import process as previous
from capture import infer, pack_json, save
from run_sensor import read_images, record, shafile
from spans import verify_parsers
from stock import stock

require = previous.require
read = previous.read
H0_MODES = {"p1": "SSSSHHHH", "p2": "HHHHSSSS"}
HEX = re.compile(r"[0-9a-f]{64}")


def validate_plan(plan):
    require(plan["packet"] == "WP-0026", "Unexpected packet")
    pid, phase, split = (plan[k] for k in ("process_id", "phase", "split"))
    require(type(plan["deadline_seconds"]) is int and plan["deadline_seconds"] > 0, "Bad deadline")
    reference = read(ROOT / "docs/coordination/WP-0025/p1-plan.json")
    for key in ("model_revision", "module_sha256", "tokenizer_sha256", "model_manifest_sha256",
                "environment_lock_sha256", "target_dtype", "historical_platform", "settings",
                "q0_python", "executable_sha256", "interpreter_flags", "prompt", "api_prompt",
                "prompt_token_ids", "prompt_sha256", "eos_id"):
        require(pack_json(plan[key]) == pack_json(reference[key]), "Changed native identity: " + key)
    require(len(plan["prompt_token_ids"]) == 827 and sha256(pack_json(plan["prompt_token_ids"])).hexdigest()
            == plan["prompt_sha256"] == previous.PROMPT_SHA, "Invalid full three-page prompt")

    calls = plan["calls"]
    if phase == "h0":
        require(split == "h0" and pid in H0_MODES and plan["lease"] == "h0-r1", "Unexpected H0 release")
        historical = read(previous.HISTORICAL)
        modes = H0_MODES[pid]
        require(len(calls) == len(modes) and not plan.get("check_groups"), "H0 comparison is across processes")
        for index, (call, mode) in enumerate(zip(calls, modes, strict=True)):
            old = historical["calls"][2 * index + (mode == "H")]
            for key in ("tag", "binder", "window", "hooked", "retain_hidden"):
                require(call[key] == old[key], "Changed H0 " + key)
            for p, q in zip(call["pages"], old["pages"], strict=True):
                require((p["sha256"], p["rgb_sha256"]) == (q["sha256"], q["rgb_sha256"]), "Changed H0 raster")
    else:
        require(phase in ("c1", "features") and split in ("train", "cal", "blind")
                and pid == plan["lease"] == f"{split}-{phase}-r1", "Unexpected study release")
        if phase == "c1":
            require(split in ("train", "blind") and len(calls) == 28 and len(plan["check_groups"]) == 12,
                    "C1 requires 28 uncached calls and 12 comparisons")
        else:
            counts = {"train": 11, "cal": 29, "blind": 248}
            require(len(calls) == counts[split] and not plan["check_groups"], "Unexpected feature count")

    warm = plan["warmup"]
    wr = warm["request"]
    guard_warm, *study_requests = plan["requests"]
    require(guard_warm == wr, "First guard request must bind W0")
    reqs = {Path(r["pdf"]).stem: r for r in study_requests}
    warm_ids = [p["rgb_sha256"] for p in warm["pages"]]
    require(len(set(warm_ids)) == 3 and wr["pages"] == 3 and warm_ids == wr["rgb_sha256"]
            and HEX.fullmatch(warm["fixture_sha256"]), "Invalid W0 fixture identity")
    require(len(reqs) == len(study_requests) and set(reqs) == {c["binder"] for c in calls}, "Unbound binder PDFs")
    for req in [wr, *reqs.values()]:
        path = Path(req["pdf"])
        require(path.is_absolute() and path.suffix.lower() == ".pdf" and len(req["rgb_sha256"]) == req["pages"]
                and shafile(path) == req["sha256"], "PDF binding changed")
    require(all(not set(warm_ids).intersection(r["rgb_sha256"]) and wr["sha256"] != r["sha256"]
                for r in reqs.values()), "W0 overlaps study data")
    tags = set()
    for ordinal, call in enumerate(calls, 2):
        mode, tag = call["mode"], call["tag"]
        require(type(call["ordinal"]) is int and call["ordinal"] == ordinal and mode in ("S", "H")
                and call["hooked"] is (mode == "H") and call["retain_hidden"] is (mode == "H" and phase != "features"),
                "Changed mode, capture policy or model ordinal")
        require(re.fullmatch(r"(?:b0[12]w0[1-4][SH]|k[0-9]{4})", tag) and tag not in tags, "Invalid tag")
        if phase != "h0":
            require(tag == f"k{ordinal-1:04d}" and mode == "H", "Expected planner tag and hooked acquisition")
        start = 3 * (call["window"] - 1)
        require(start >= 0 and len(call["pages"]) == 3 and [p["rgb_sha256"] for p in call["pages"]]
                == reqs[call["binder"]]["rgb_sha256"][start:start+3], "Window disagrees with source PDF")
        tags.add(tag)


@contextmanager
def images_for(pages, root):
    images = read_images(pages, Path(root).resolve(strict=True))
    try:
        yield images
    finally:
        for image in images:
            image.close()


def run_warmup(native, warm, plan, folder, identity):
    import torch
    from native import MODEL, NOTICE

    receipt = dict(identity, tag="W0", ordinal=1, mode="S", fixture_sha256=warm["fixture_sha256"],
                   request=warm["request"], pages=warm["pages"], prompt=plan["prompt"],
                   prompt_sha256=plan["prompt_sha256"], prompt_token_ids=plan["prompt_token_ids"],
                   prompt_shape=[1, 827], scored=False, start_utc_ns=time.time_ns())
    start = time.perf_counter_ns()
    record(folder / "warmup-begin.json", receipt)
    try:
        with images_for(warm["pages"], warm["raster_root"]) as images:
            native.pin.verify(str(MODEL), str(NOTICE), native.pin.manifest)
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            t0 = time.perf_counter_ns()
            # The upstream stock streamer can print page text. Keep it ephemeral along with the native return.
            with redirect_stdout(io.StringIO()):
                raw = stock(native.model, native.tokenizer, images)
            torch.cuda.synchronize()
            receipt.update(wall_inference_ns=time.perf_counter_ns() - t0,
                           cuda_peak_allocated=torch.cuda.max_memory_allocated(),
                           cuda_peak_reserved=torch.cuda.max_memory_reserved(),
                           observed_prompt=raw["prompt"], observed_prompt_token_ids=raw["prompt_token_ids"],
                           observed_prompt_shape=[1, len(raw["prompt_token_ids"])],
                           finish_reason=raw["finish_reason"], eos_observed=raw["eos_observed"],
                           terminal_observation=raw["terminal_observation"])
            packed = previous.validate_return(raw, plan)
            receipt.update(eos_id=raw["eos_id"], emitted=len(raw["token_ids"]), through_eos_sha256=sha256(packed).hexdigest())
            native.pin.verify(str(MODEL), str(NOTICE), native.pin.manifest)
        receipt["success"] = True
    except BaseException as exc:
        receipt.update(success=False, error_type=type(exc).__name__, message=str(exc))
        raise
    finally:
        receipt.update(end_utc_ns=time.time_ns(), elapsed_ns=time.perf_counter_ns() - start)
        record(folder / "warmup.json", receipt)
    return receipt


def seal_sample(sample, call, duration, plan):
    # The historical verifier seals stock and fully retained hooked calls. Ordinary
    # feature acquisition deliberately omits token_hidden.bf16 and absolute positions.
    if not call["hooked"] or call["retain_hidden"]:
        return previous.verify_artifacts(sample, call["hooked"], duration, plan)
    files = previous.COMMON_FILES | {"pooled.f32", "capture.json"}
    require({p.name for p in sample.iterdir()} == files, "Unexpected feature-only artifacts")
    hashes = {name: shafile(sample / name) for name in sorted(files)}
    raw, meta, cap = (read(sample / name) for name in ("native.json", "metadata.json", "capture.json"))
    packed = previous.validate_return(raw, plan)
    for key in ("token_ids", "prompt_token_ids", "eos_id", "stop_cause", "eos_observed",
                "terminal_observation", "expected_pages", "num_pages_out"):
        require(pack_json(raw[key]) == pack_json(meta[key]), "Mismatched native metadata: " + key)
    n, spans = len(raw["token_ids"]), len(meta["spans"])
    require(meta["raw"] == raw["text"] and len(meta["pages"]) == 3 and read(sample / "duration.json") == duration
            and hashes["metadata.json"] == duration["metadata_sha256"] and cap == duration["capture"]
            and duration["prompt_sha256"] == plan["prompt_sha256"] and duration["eos"] == previous.EOS
            and duration["emitted"] == n and duration["spans"] == spans, "Invalid feature receipt")
    require(cap["capture_layer"] == previous.LAYER and cap["pool_dtype"] == "little-endian float32"
            and cap["native_dtype"] == "bfloat16" and cap["hidden_shape"] == [n, previous.WIDTH]
            and cap["pool_shape"] == [spans, previous.WIDTH] and cap["position_start"] == 827
            and cap["position_stop_exclusive"] == 827 + n and cap["consumed_id_sha256"] == duration["token_sha256"]
            == sha256(pack_json(raw["token_ids"])).hexdigest() and cap["pooled_sha256"] == hashes["pooled.f32"]
            and (sample / "pooled.f32").stat().st_size == spans * previous.WIDTH * 4, "Invalid pooled feature")
    hashes["through-eos.u32le"] = save(sample / "through-eos.u32le", packed)
    return {"artifacts": hashes, "through_eos_sha256": hashes["through-eos.u32le"], "through_eos_length": n + 1}


def duplicate_checks(plan, rows):
    groups = []
    for check in plan.get("check_groups", []):
        left, right = (rows[check[k]] for k in ("left", "right"))
        require(check["mode"] == "duplicate" and check["left"] != check["right"], "Invalid duplicate comparison")
        names = ("metadata.json", "through-eos.u32le", "observed-positions.json", "token_hidden.bf16", "pooled.f32", "capture.json")
        differing = [name for name in names if left["artifacts"][name] != right["artifacts"][name]]
        groups.append(dict(check, differing=differing, passed=not differing))
    return groups


def conduct(plan, digest, folder):
    start = time.perf_counter_ns()
    identity = {k: plan[k] for k in ("packet", "lease", "phase", "split", "process_id", "candidate", "model_revision")}
    identity.update(plan_sha256=digest, gpu_uuid=previous.GPU, pid=os.getpid(), parent_pid=os.getppid(),
                    process_create_filetime=previous.current_process_create_filetime())
    identity["model_load_id"] = f"{identity['pid']}-{identity['process_create_filetime']}-1"
    rows, started = {}, []

    def deadline():
        require(time.perf_counter_ns() - start < plan["deadline_seconds"] * 10**9, "Process deadline exceeded")

    try:
        validate_plan(plan)
        previous.clean_source(plan["candidate"])
        environment = previous.check_environment(folder, plan)
        verify_parsers()
        from native import MODEL, Native
        require(shafile(MODEL / "modeling_unlimitedocr.py") == plan["module_sha256"]
                and shafile(MODEL / "tokenizer.json") == plan["tokenizer_sha256"], "Runtime file digest changed")
        record(folder / "binding.json", dict(identity, checkout=str(ROOT), cwd=str(Path.cwd()), python=sys.executable,
               sensor_candidate=previous.SOURCE, warmup_fixture_sha256=plan["warmup"]["fixture_sha256"],
               environment=environment, settings=plan["settings"], request_prompt=plan["api_prompt"],
               prompt=plan["prompt"], prompt_token_ids=plan["prompt_token_ids"], prompt_sha256=plan["prompt_sha256"],
               order=[c["tag"] for c in plan["calls"]], utc_ns=time.time_ns()))
        deadline()
        load_utc, load_clock = time.time_ns(), time.perf_counter_ns()
        with closing(Native(folder)) as native:
            load_ns = time.perf_counter_ns() - load_clock
            record(folder / "cold.json", dict(identity, start_utc_ns=load_utc, ready_utc_ns=time.time_ns(),
                                              elapsed_ns=load_ns, loads=1, model=native.info))
            for key, expected in (("model_revision", plan["model_revision"]), ("platform", plan["historical_platform"]),
                                  ("manifest_sha256", plan["model_manifest_sha256"]), ("target_dtype", plan["target_dtype"]),
                                  ("dependency_lock_sha256", plan["environment_lock_sha256"]),
                                  ("tokenizer_sha256", plan["tokenizer_sha256"]), ("eos_id", previous.EOS),
                                  ("page_id", previous.protocol.PAGE_TOKEN_ID)):
                require(native.info[key] == expected, "Unexpected loaded runtime: " + key)
            deadline()
            warm = run_warmup(native, plan["warmup"], plan, folder, identity)
            warm_pin = shafile(folder / "warmup.json")
            for call in plan["calls"]:
                deadline()
                tag = call["tag"]
                sample = folder / tag
                slot = dict(identity, tag=tag, binder=call["binder"], window=call["window"], ordinal=call["ordinal"],
                            mode=call["mode"], pages=call["pages"], warmup_sha256=warm_pin,
                            warmup_fixture_sha256=warm["fixture_sha256"], sensor_candidate=previous.SOURCE)
                with images_for(call["pages"], plan["raster_root"]) as images:
                    record(folder / (tag + "-begin.json"), dict(slot, utc_ns=time.time_ns()))
                    started.append(tag)
                    duration = infer(native, images, sample, call["hooked"], call["retain_hidden"])
                details = seal_sample(sample, call, duration, plan)
                record(sample / "receipt.json", dict(slot, **details, verified=True, utc_ns=time.time_ns()))
                rows[tag] = dict(duration, **details)
        deadline()
        checks = duplicate_checks(plan, rows)
        passed = all(g["passed"] for g in checks)
        record(folder / "outcome.json", dict(identity, status="complete" if passed else "c1-mismatch",
               checks=checks, all_equal=passed, rows=rows, started_tags=started, verified_tags=list(rows),
               real_inference_calls=len(rows), warmup_calls=1, total_inference_calls=len(rows)+1,
               load_s=load_ns/1e9, warmup_s=warm["elapsed_ns"]/1e9,
               window_metric_sum_s=sum(r["complete_window_wall_ns"] for r in rows.values())/1e9,
               scored_inference_s=sum(r["wall_inference_ns"] for r in rows.values())/1e9,
               complete_phase_s=(time.perf_counter_ns()-start)/1e9))
        require(passed, "C1 duplicate mismatch")
    except BaseException as exc:
        record(folder / "error.json", dict(identity, status="incomplete", started_tags=started, verified_tags=list(rows),
               elapsed_ns=time.perf_counter_ns()-start, utc_ns=time.time_ns(), error_type=type(exc).__name__,
               message=str(exc), traceback=traceback.format_exc()))
        raise


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("digest")
    a = parser.parse_args()
    require(a.plan.is_absolute(), "Absolute plan path required")
    data = a.plan.read_bytes()
    require(sha256(data).hexdigest() == a.digest, "Plan digest mismatch")
    plan = json.loads(data)
    pid = plan["process_id"]
    require(re.fullmatch(r"(?:p[12]|(?:train|cal|blind)-(?:c1|features)-r1)", pid), "Unbound process")
    out = RUNS / pid
    require(Path(plan["output"]).is_absolute() and Path(plan["output"]).resolve(strict=True) == out, "Wrong output")
    folder = out / "sensor"
    cache = folder / "cache"
    require(folder.resolve(strict=True) == folder and Path.cwd() in (ROOT, folder) and
            {p.name for p in folder.iterdir()} == {"cache"} and cache.is_dir() and cache.resolve() == cache
            and all(p.is_dir() and p.resolve() == p for p in cache.rglob("*")), "Fresh process-local cache required")
    os.chdir(folder)
    sys.stdout.reconfigure(encoding="utf8")
    sys.stderr.reconfigure(encoding="utf8")
    conduct(plan, a.digest, folder)


if __name__ == "__main__":
    main()
