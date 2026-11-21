"""Run one released SHHS or HSSH process and seal each verified native return."""
from argparse import ArgumentParser
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SENSOR = ROOT / "docs/research/WP-0024/sensor"
sys.path.insert(0, str(SENSOR))
from run_sensor import GPU, Q0, read_images, record, shafile
from capture import LAYER, WIDTH, infer, pack_json, save
from local_ocr import protocol
from local_ocr.env_guard import REQUIRED_RUN_LOCAL_VARS, audit_worker_environment, current_process_create_filetime

SOURCE = "1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd"
HISTORICAL = ROOT / "docs/coordination/WP-0024/h0-r1-plan.json"
HISTORICAL_SHA = "0bf358c54fc97f32ca213d9a1dd10cfb2838f42f7c5dcded1625c0cca1fd2f89"
ARCHIVE_SHA = "37670af4116f543e2d0104b5d3599d88f2e2d06fc092418ee1cf839769430fc6"
PROMPT_SHA = "b03d548d131b2651d56c3457e4b60144ab128b21444f87e4c9138dce1e809f57"
TOKENIZER_SHA = "c55c165e32c5a67830362a53e1f548c8930dcc8469efa30ff3252a982799c589"
RUNS = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0025/review/runs")
ORDERS = {"P1": "SHHS", "P2": "HSSH"}
DEADLINE_NS = 1200 * 10**9
EOS = 1
GIT = "C:/Program Files/Git/cmd/git.exe"
HISTORICAL_PATHS = ("docs/research/WP-0024/sensor", "docs/research/WP-0023/trial/stock.py",
                    "docs/research/WP-0015/astra", "docs/research/WP-0014/eld-latency-author",
                    "workers/local_ocr")
COMMON_FILES = {"native.json", "metadata.json", "duration.json"}
HIDDEN_FILES = {"capture.json", "observed-positions.json", "token_hidden.bf16", "pooled.f32"}
EXTRA_CACHE_VARS = ("LOCALAPPDATA", "APPDATA", "PYTHONPYCACHEPREFIX", "TRITON_HOME",
                    "TORCH_EXTENSIONS_DIR", "MPLCONFIGDIR", "NUMBA_CACHE_DIR")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_bytes())


def validate_plan(plan):
    old_bytes = HISTORICAL.read_bytes()
    require(sha256(old_bytes).hexdigest() == HISTORICAL_SHA, "Historical plan changed")
    old = json.loads(old_bytes)
    pid = plan["process_id"]
    require(plan["packet"] == "WP-0025" and pid in ORDERS, "Unexpected packet or process")
    require(type(plan["process_ordinal"]) is int and plan["process_ordinal"] == int(pid[1]), "Process ordinal")
    require(type(plan["deadline_seconds"]) is int and plan["deadline_seconds"] == 1200, "Process deadline changed")
    require(plan["historical_plan_sha256"] == HISTORICAL_SHA and plan["historical_archive_sha256"] == ARCHIVE_SHA
            and plan["historical_sensor_revision"] == SOURCE, "Historical binding changed")
    require(old["candidate"] == SOURCE and plan["model_revision"] == old["model_revision"] == protocol.MODEL_REVISION
            and plan["module_sha256"] == old["module_sha256"] and plan["tokenizer_sha256"] == TOKENIZER_SHA,
            "Model or tokenizer binding changed")
    require(plan["api_prompt"] == protocol.PROMPT and type(plan["eos_id"]) is int and plan["eos_id"] == EOS
            and plan["prompt"] == "<PAGE><image>" * 3 + protocol.PROMPT and plan["prompt_sha256"] == PROMPT_SHA
            and sha256(pack_json(plan["prompt_token_ids"])).hexdigest() == PROMPT_SHA, "Prompt binding changed")
    protocol.validate_call_kwargs(plan["settings"], 3)
    require(plan["raster_root"] == old["raster_root"], "Raster root changed")
    original = old["calls"][0]
    require(original["tag"] == "b01w01S" and original["binder"] == "34054347f091c087a39efe17", "Source window")
    require(plan["requests"] == old["requests"][:1], "Historical PDF binding changed")
    for ordinal, (call, mode) in enumerate(zip(plan["calls"], ORDERS[pid], strict=True), 1):
        require(call["tag"] == f"{pid}J{ordinal}{mode}" and call["mode"] == mode and
                type(call["ordinal"]) is int and call["ordinal"] == ordinal and call["hooked"] is (mode == "H")
                and call["retain_hidden"] is (mode == "H"), "Frozen call order or capture mode changed")
        require(call["pages"] == original["pages"], "Ordered original PNG/RGB bindings changed")


def clean_source(candidate):
    def git(*args):
        return subprocess.check_output([GIT, "-C", str(ROOT), *args], text=True).strip()

    require(git("rev-parse", "HEAD") == candidate and not git("status", "--porcelain", "--untracked-files=all"),
            "Execution checkout must be clean at the exact candidate")
    git("diff", "--exit-code", "--no-ext-diff", SOURCE, "HEAD", "--", *HISTORICAL_PATHS)


def check_environment(folder, plan):
    require(Path(sys.executable).resolve() == (Q0 / "venv/Scripts/python.exe").resolve()
            and sys.flags.isolated and sys.dont_write_bytecode, "Use pinned Q0 Python with -I -B")
    env = dict(os.environ)
    require(env == {key.upper(): value for key, value in plan["environment"].items()}, "Actual environment differs from plan")
    require(Path(plan["q0_python"]).resolve() == Path(sys.executable).resolve() and plan["interpreter_flags"] == ["-I", "-B"]
            and shafile(sys.executable) == plan["executable_sha256"], "Interpreter differs from plan")
    audit_worker_environment(env, run_dir=folder, readonly_q0_root=Q0, leased_gpu_uuid=GPU)
    flags = {"HF_HUB_DISABLE_TELEMETRY": "1", "HF_HUB_DISABLE_PROGRESS_BARS": "1", "PIP_CONFIG_FILE": "NUL",
             "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf8"}
    require(all(env.get(k) == v for k, v in flags.items()), "Historical isolated runtime flags changed")
    require(Path(env["VIRTUAL_ENV"]).resolve() == (Q0 / "venv").resolve(), "Wrong virtual environment")
    for key in (*REQUIRED_RUN_LOCAL_VARS, *EXTRA_CACHE_VARS):
        path = Path(env[key]).resolve(strict=True)
        require(path.is_dir() and path.is_relative_to(folder / "cache"), "Cache outside fresh sensor: " + key)
    keys = (*REQUIRED_RUN_LOCAL_VARS, *EXTRA_CACHE_VARS, *flags, "VIRTUAL_ENV", "PATH", "CUDA_VISIBLE_DEVICES",
            "CUDA_DEVICE_ORDER", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "PIP_NO_INDEX", "HF_HUB_DISABLE_XET")
    return {k: env[k] for k in keys}


def validate_return(raw, plan):
    ids, prompt_ids = raw["token_ids"], raw["prompt_token_ids"]
    require(raw["prompt"] == plan["prompt"] and pack_json(prompt_ids) == pack_json(plan["prompt_token_ids"]),
            "Actual expanded prompt or full prefill IDs changed")
    require(isinstance(ids, list) and ids and all(type(i) is int and 0 <= i <= 0xffffffff for i in ids)
            and EOS not in ids, "Invalid native non-EOS token IDs")
    page_id = protocol.PAGE_TOKEN_ID
    require(ids[0] == page_id and ids.count(page_id) == 3 and raw["text"].startswith("<PAGE>")
            and raw["text"].count("<PAGE>") == 3, "Three output pages required")
    require(raw["finish_reason"] == "stop" and raw["stop_cause"] == "eos" and raw["eos_observed"] is True
            and type(raw["eos_id"]) is int and raw["eos_id"] == EOS
            and raw["expected_pages"] == raw["num_pages_out"] == 3, "Missing verified three-page EOS")
    expected_stop = {"nxt": EOS, "step": len(ids), "prompt_length": len(prompt_ids),
                     "max_length": plan["settings"]["max_length"], "max_new_tokens": plan["settings"]["max_new_tokens"],
                     "guard": {"scanned": len(ids), "marker_cum": 3, "page_len": ids[::-1].index(page_id)}}
    require(pack_json(raw["terminal_observation"]) == pack_json(expected_stop), "Invalid processed terminal receipt")
    require(len(ids) < expected_stop["max_new_tokens"] and len(ids) + len(prompt_ids) < expected_stop["max_length"],
            "EOS outside generation bounds")
    return struct.pack(f"<{len(ids) + 1}I", *ids, EOS)


def verify_artifacts(sample, hooked, duration, plan):
    files = COMMON_FILES | (HIDDEN_FILES if hooked else set())
    require({p.name for p in sample.iterdir()} == files, "Missing or unexpected native artifacts")
    hashes = {name: shafile(sample / name) for name in sorted(files)}
    raw, meta = read(sample / "native.json"), read(sample / "metadata.json")
    packed = validate_return(raw, plan)
    require(read(sample / "duration.json") == duration and hashes["metadata.json"] == duration["metadata_sha256"],
            "Native duration or metadata digest changed")
    for key in ("token_ids", "prompt_token_ids", "eos_id", "stop_cause", "eos_observed", "terminal_observation",
                "expected_pages", "num_pages_out"):
        require(pack_json(raw[key]) == pack_json(meta[key]), "Native metadata mismatch: " + key)
    ids = raw["token_ids"]
    n, offset, spans = len(ids), len(raw["prompt_token_ids"]), len(meta["spans"])
    require(meta["raw"] == raw["text"] and duration["token_sha256"] == sha256(pack_json(ids)).hexdigest()
            and duration["prompt_sha256"] == plan["prompt_sha256"] and duration["emitted"] == n
            and duration["eos"] == EOS and duration["spans"] == spans and len(meta["pages"]) == 3,
            "Native token/text/metadata receipt disagrees")
    require(duration["start_utc_ns"] <= duration["end_inference_utc_ns"] <= duration["end_capture_utc_ns"]
            and 0 < duration["wall_inference_ns"] <= duration["complete_window_wall_ns"], "Invalid inference clocks")
    if hooked:
        cap = read(sample / "capture.json")
        require(duration["capture"] == cap and cap["capture_layer"] == LAYER and cap["native_dtype"] == "bfloat16"
                and cap["pool_dtype"] == "little-endian float32" and cap["hidden_shape"] == [n, WIDTH]
                and cap["pool_shape"] == [spans, WIDTH] and cap["position_start"] == offset
                and cap["position_stop_exclusive"] == offset + n and cap["consumed_id_sha256"] == duration["token_sha256"],
                "Invalid hooked capture receipt")
        require(read(sample / "observed-positions.json") == {"ids": ids, "absolute_positions": list(range(offset, offset + n))},
                "Consumed token IDs or absolute positions changed")
        for name, key, size in (("token_hidden.bf16", "hidden_sha256", n * WIDTH * 2),
                                ("pooled.f32", "pooled_sha256", spans * WIDTH * 4)):
            require(hashes[name] == cap[key] and (sample / name).stat().st_size == size, "Invalid " + name)
    else:
        require(duration["capture"] is None, "Unexpected stock hidden capture")
    name = "through-eos.u32le"
    hashes[name] = save(sample / name, packed)
    require((sample / name).read_bytes() == packed, "Through-EOS artifact failed readback")
    return {"artifacts": hashes, "through_eos_sha256": hashes[name], "through_eos_length": n + 1}


def conduct(plan, digest, folder, monotonic_start):
    from spans import verify_parsers

    identity = {"packet": plan["packet"], "process_id": plan["process_id"], "process_ordinal": plan["process_ordinal"],
                "candidate": plan["candidate"], "plan_sha256": digest, "pid": os.getpid(), "parent_pid": os.getppid(),
                "process_create_filetime": current_process_create_filetime()}
    started, verified = [], []

    def check_clock():
        require(time.perf_counter_ns() - monotonic_start < DEADLINE_NS, "Process deadline exceeded")

    try:
        validate_plan(plan)
        clean_source(plan["candidate"])
        environment = check_environment(folder, plan)
        verify_parsers()
        os.chdir(folder)
        from native import MODEL, Native
        require(shafile(MODEL / "modeling_unlimitedocr.py") == plan["module_sha256"]
                and shafile(MODEL / "tokenizer.json") == plan["tokenizer_sha256"], "Runtime file digest changed")
        record(folder / "binding.json", dict(identity, utc_ns=time.time_ns(), monotonic_start_ns=monotonic_start,
               checkout=str(ROOT), cwd=str(Path.cwd()), python=sys.executable, environment=environment,
               sensor_candidate=SOURCE, model_revision=plan["model_revision"], module_sha256=plan["module_sha256"],
               tokenizer_sha256=plan["tokenizer_sha256"], settings=protocol.build_call_kwargs(3),
               request_prompt=protocol.PROMPT, prompt=plan["prompt"], prompt_sha256=plan["prompt_sha256"],
               order=[c["tag"] for c in plan["calls"]], pages=plan["calls"][0]["pages"], deadline_s=1200))
        check_clock()
        load_start = time.time_ns()
        with closing(Native(folder)) as native:
            record(folder / "cold.json", dict(identity, start_utc_ns=load_start, ready_utc_ns=time.time_ns(),
                                             model=native.info, loads=1))
            require(native.info["model_revision"] == plan["model_revision"]
                    and native.info["target_dtype"] == plan["target_dtype"] == "torch.bfloat16"
                    and native.info["platform"] == plan["historical_platform"]
                    and native.info["manifest_sha256"] == plan["model_manifest_sha256"]
                    and native.info["dependency_lock_sha256"] == plan["environment_lock_sha256"]
                    and native.info["tokenizer_sha256"] == plan["tokenizer_sha256"] and native.info["eos_id"] == EOS
                    and native.info["page_id"] == protocol.PAGE_TOKEN_ID, "Unexpected loaded runtime")
            for call in plan["calls"]:
                tag = call["tag"]
                images = read_images(call["pages"], Path(plan["raster_root"]).resolve())
                try:
                    check_clock()
                    slot = dict(identity, tag=tag, ordinal=call["ordinal"], mode=call["mode"])
                    record(folder / (tag + "-begin.json"), dict(slot, utc_ns=time.time_ns(), monotonic_ns=time.perf_counter_ns()))
                    started.append(tag)
                    duration = infer(native, images, folder / tag, call["hooked"], call["retain_hidden"])
                finally:
                    for image in images:
                        image.close()
                details = verify_artifacts(folder / tag, call["hooked"], duration, plan)
                check_clock()
                record(folder / tag / "receipt.json", dict(slot, **details, verified=True, utc_ns=time.time_ns(),
                                                         monotonic_ns=time.perf_counter_ns()))
                verified.append(tag)
        check_clock()
        record(folder / "outcome.json", dict(identity, status="complete", started_tags=started, verified_tags=verified,
               utc_ns=time.time_ns(), process_wall_ns=time.perf_counter_ns() - monotonic_start))
    except BaseException as exc:
        record(folder / "error.json", dict(identity, status="incomplete", started_tags=started, verified_tags=verified,
               utc_ns=time.time_ns(), process_wall_ns=time.perf_counter_ns() - monotonic_start,
               error_type=type(exc).__name__, message=str(exc), traceback=traceback.format_exc()))
        raise


def main():
    start = time.perf_counter_ns()
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("digest")
    args = parser.parse_args()
    require(args.plan.is_absolute(), "Absolute plan path required")
    data = args.plan.read_bytes()
    require(sha256(data).hexdigest() == args.digest, "Plan digest mismatch")
    plan = json.loads(data)
    pid = plan["process_id"]
    require(pid in ORDERS, "Unknown process")
    output = RUNS / pid.lower()
    require(Path(plan["output"]).is_absolute() and Path(plan["output"]).resolve() == output, "Unexpected output root")
    folder = output / "sensor"
    require(folder.resolve(strict=True) == folder and Path.cwd() in (ROOT, folder), "Unexpected process or sensor path")
    require({p.name for p in folder.iterdir()} == {"cache"} and (folder / "cache").is_dir()
            and all(p.is_dir() and p.resolve() == p for p in (folder / "cache").rglob("*"))
            and (folder / "cache").resolve() == folder / "cache", "Expected fresh per-process cache and output")
    sys.stdout.reconfigure(encoding="utf8")
    sys.stderr.reconfigure(encoding="utf8")
    conduct(plan, args.digest, folder, start)


if __name__ == "__main__":
    main()
