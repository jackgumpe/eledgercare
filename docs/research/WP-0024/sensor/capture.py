"""Observe the frozen singleton's consumed token positions, then pool final normalized states on CPU."""
from contextlib import ExitStack, contextmanager
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "docs/research/WP-0023/trial"))
from spans import map_window
from stock import stock

LAYER = "native model.model final normalized decoder state, lm_head input, after consuming emitted token"
WIDTH = 1280


def pack_json(data):
    return (json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",",":"), allow_nan=False)+"\n").encode()


def save(path, raw):
    pending = path.with_suffix(path.suffix+".pending")
    with pending.open("xb") as out:
        out.write(raw)
        out.flush()
    if path.exists():
        raise FileExistsError(path)
    pending.rename(path)
    return sha256(raw).hexdigest()


@contextmanager
def observer(model):
    import torch
    state = {"inputs":[], "positions":[], "states":[], "prompt_length":None, "next":"input"}

    def read_input(_module, _args, kw):
        if state["next"] != "input":
            raise ValueError("Decoder/head callbacks out of order")
        ids = kw["input_ids"]
        positions = kw["position_ids"]
        if state["prompt_length"] is None:
            if len(ids.shape) != 2 or ids.shape[0] != 1 or ids.shape[1] <= 1:
                raise ValueError("Unexpected singleton prefill")
            state["prompt_length"] = ids.shape[1]
            state["prefill_ids"] = ids[0].detach().cpu().tolist()
            state["next"] = "prefill head"
        else:
            if tuple(ids.shape) != (1,1) or tuple(positions.shape) != (1,1):
                raise ValueError("Capture requires unmodified singleton decode")
            state["inputs"].append(int(ids[0,0].detach().cpu()))
            state["positions"].append(int(positions[0,0].detach().cpu()))
            state["next"] = "token head"

    def read_state(_module, args):
        h, = args
        if tuple(h.shape)!=(1,1,WIDTH) or h.dtype != torch.bfloat16:
            raise ValueError("Unexpected native head state shape/dtype")
        if state["next"] == "token head":
            # BF16 bits are copied verbatim. No tensor is returned to the underlying model.
            state["states"].append(h[0,0].detach().contiguous().view(torch.uint16).cpu().numpy().copy())
        elif state["next"] != "prefill head":
            raise ValueError("Head observation has no matching decoder input")
        state["next"] = "input"

    with ExitStack() as handles:
        handles.callback(model.model.register_forward_pre_hook(read_input,with_kwargs=True).remove)
        handles.callback(model.lm_head.register_forward_pre_hook(read_state).remove)
        yield state


def make_record(result, tokenizer):
    added = {int(i): str(v) for i,v in tokenizer.added_tokens_decoder.items()}
    mapped = map_window(result["text"],result["token_ids"],tokenizer.convert_ids_to_tokens,added)
    if result["stop_cause"]!="eos" or result["expected_pages"]!=3 or result["num_pages_out"]!=3:
        raise ValueError("Native generation did not report three complete pages and EOS")
    return dict(**mapped,raw=result["text"],token_ids=result["token_ids"],prompt_token_ids=result["prompt_token_ids"],
                eos_id=result["eos_id"],stop_cause=result["stop_cause"],eos_observed=result["eos_observed"],
                expected_pages=result["expected_pages"],num_pages_out=result["num_pages_out"],
                terminal_observation=result["terminal_observation"])


def finish_capture(trace, meta, folder, retain):
    import numpy as np
    prompt = trace["prompt_length"]
    ids = meta["token_ids"]
    if (trace["next"] != "input" or trace["prefill_ids"] != meta["prompt_token_ids"] or
            trace["inputs"] != ids or trace["positions"] != list(range(prompt,prompt+len(ids))) or
            len(trace["states"]) != len(ids)):
        raise ValueError("Captured consumed tokens or source positions diverge from the native return")
    hidden = np.stack(trace["states"]).astype("<u2",copy=False)
    floats = (hidden.astype("<u4") << 16).view("<f4")
    if hidden.shape!=(len(ids),WIDTH) or not np.isfinite(floats).all():
        raise ValueError("Invalid final decoder states")
    pooled = np.empty((len(meta["spans"]),WIDTH), dtype="<f4")
    for row in meta["spans"]:
        pooled[row["index"]] = floats[row["token_indices"]].mean(axis=0,dtype=np.float32)
    hidden_bytes = hidden.tobytes()
    obs = {"capture_layer":LAYER,"native_dtype":"bfloat16","hidden_shape":list(hidden.shape),
           "pool_dtype":"little-endian float32","pool_shape":list(pooled.shape),"hidden_sha256":sha256(hidden_bytes).hexdigest(),
           "pooled_sha256":save(folder/"pooled.f32",pooled.tobytes()), "consumed_id_sha256":sha256(pack_json(trace["inputs"])).hexdigest(),
           "position_start":prompt,"position_stop_exclusive":prompt+len(ids)}
    if retain:
        save(folder/"token_hidden.bf16", hidden_bytes)
        save(folder/"observed-positions.json",pack_json({"ids":trace["inputs"],"absolute_positions":trace["positions"]}))
    save(folder/"capture.json",pack_json(obs))
    return obs


def infer(native, images, folder, hooked, retain):
    import torch
    from native import MODEL, NOTICE
    folder.mkdir(parents=True,exist_ok=False)
    native.pin.verify(str(MODEL),str(NOTICE),native.pin.manifest)
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    t0=time.perf_counter_ns()
    start=time.time_ns()
    if hooked:
        with observer(native.model) as trace:
            result=stock(native.model,native.tokenizer,images)
    else:
        result=stock(native.model,native.tokenizer,images)
    torch.cuda.synchronize()
    elapsed=time.perf_counter_ns()-t0
    end=time.time_ns()
    save(folder/"native.json",pack_json(result))
    meta=make_record(result,native.tokenizer)
    meta_sha=save(folder/"metadata.json",pack_json(meta))
    capture=finish_capture(trace,meta,folder,retain) if hooked else None
    native.pin.verify(str(MODEL),str(NOTICE),native.pin.manifest)
    record={"start_utc_ns":start,"end_inference_utc_ns":end,"wall_inference_ns":elapsed,
            "end_capture_utc_ns":time.time_ns(),"complete_window_wall_ns":time.perf_counter_ns()-t0,
            "cuda_peak_allocated":torch.cuda.max_memory_allocated(),"cuda_peak_reserved":torch.cuda.max_memory_reserved(),
            "metadata_sha256":meta_sha,"token_sha256":sha256(pack_json(meta["token_ids"])).hexdigest(),
            "prompt_sha256":sha256(pack_json(meta["prompt_token_ids"])).hexdigest(),"capture":capture,
            "spans":len(meta["spans"]),"emitted":len(meta["token_ids"]),"eos":meta["eos_id"]}
    save(folder/"duration.json",pack_json(record))
    return record
