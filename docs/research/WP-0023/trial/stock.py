"""Read actual stock stop events and bounded prefix logits without replacing model code."""
import inspect
import math
import sys
from contextlib import contextmanager


def encoded(value):
    value = float(value)
    if math.isnan(value):
        raise ValueError("NaN logit")
    return value if math.isfinite(value) else ("-inf" if value < 0 else "+inf")


def scores(logits, candidates):
    top = logits.topk(2)
    return {
        "argmax": int(logits.argmax()),
        "top2": [{"id": i, "logit": encoded(v)} for i, v in zip(top.indices.tolist(), top.values.tolist())],
        "candidates": {str(i): encoded(logits[i]) for i in candidates},
    }


class AtDecision(Exception):
    """Stop a diagnostic replay after the requested stock argmax, through upstream finally."""


@contextmanager
def observe(generate, receipt, *, prefix=None, candidates=()):
    fn = inspect.unwrap(generate)
    code = fn.__code__
    mon = sys.monitoring
    tool = 3
    events = mon.events.PY_RETURN

    def returned(_code, _offset, _result):
        state = sys._getframe(1).f_locals
        receipt.update(nxt=int(state["nxt"]), step=int(state["step"]), prompt_length=int(state["S"]),
                       max_new_tokens=state["max_new_tokens"], max_length=state["max_length"],
                       guard=dict(state["guard_st"]))

    if prefix is not None:
        events |= mon.events.LINE
        lines, first = inspect.getsourcelines(fn)
        targets = {}
        for stage, source in (("raw", "if ngram_size > 0:"), ("processed", "if t_first is None:")):
            hits = [first + i for i, line in enumerate(lines) if line.strip() == source]
            if len(hits) != 1:
                raise ValueError(f"Ambiguous stock monitoring point {stage}")
            targets[hits[0]] = stage

        def at_line(_code, line):
            stage = targets.get(line)
            if stage is None:
                return mon.DISABLE
            state = sys._getframe(1).f_locals
            if state["step"] == len(prefix):
                if state["gen"] != prefix:
                    raise ValueError("Stock prefix replay selected different earlier tokens")
                receipt[stage] = scores(state["logits"], candidates)
                if stage == "processed":
                    receipt.update(selected=int(state["nxt"]), guard=dict(state["guard_st"]),
                                   step=state["step"], prompt_length=state["S"])
                    raise AtDecision

    mon.use_tool_id(tool, "wp0023-stock")
    try:
        mon.register_callback(tool, mon.events.PY_RETURN, returned)
        if prefix is not None:
            mon.register_callback(tool, mon.events.LINE, at_line)
        mon.set_local_events(tool, code, events)
        yield
    finally:
        mon.set_local_events(tool, code, 0)
        mon.register_callback(tool, mon.events.PY_RETURN, None)
        if prefix is not None:
            mon.register_callback(tool, mon.events.LINE, None)
        mon.free_tool_id(tool)


def stock(model, tokenizer, images, *, prefix=None, candidates=()):
    from local_ocr import protocol
    receipt = {}
    try:
        with observe(model._uocr_generate, receipt, prefix=prefix, candidates=candidates):
            result = model.infer(tokenizer, prompt=protocol.PROMPT, image_file=images, return_dict=True,
                                 **protocol.build_call_kwargs(3))
    except AtDecision:
        return receipt
    if prefix is not None:
        raise ValueError("Stock replay stopped before the requested prefix")
    eos = int(tokenizer.eos_token_id)
    ids = result["token_ids"]
    saw_eos = result["finish_reason"] == "stop" and receipt["nxt"] == eos and receipt["step"] == len(ids)
    if saw_eos:
        cause = "eos"
    elif (result["finish_reason"] == "length" and receipt["nxt"] != eos and ids
          and ids[-1] == receipt["nxt"] and receipt["step"] == len(ids) - 1):
        cause = "max_length" if receipt["prompt_length"] + len(ids) >= receipt["max_length"] else "max_new_tokens"
        if cause == "max_new_tokens" and len(ids) != receipt["max_new_tokens"]:
            raise ValueError("Stock length stop does not match either native bound")
    else:
        raise ValueError("Stock terminal event and public finish state disagree")
    return dict(result, eos_id=eos, eos_observed=saw_eos, stop_cause=cause, terminal_observation=receipt)
