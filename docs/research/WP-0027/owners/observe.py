"""Observe frozen operations. Checkpoint scores replay each binder's own eventual query."""
from collections import Counter
import sys

import torch

import matrix
import online
from inputs import check, sha


def tbytes(t):
    return t.contiguous().numpy().tobytes()


def control(state):
    return {"depth": state.controller.depth, "held": list(state.controller.held),
            "fault": state.controller.fault, "ambiguous_reason": state.controller.ambiguous()}


def values(choices):
    return {name: {online.key(val): val for val in vals} for name, vals in choices.items()}


def numerics(model, matrices, state, query):
    depth = state.controller.depth
    full = torch.stack(matrices)
    # These columns are exactly the source read by Memory.read for owner.
    slices = full[:, :, :32]
    response = model.read(matrices, depth, query, "owner")
    choices = state.registry.choices()["owner"]
    scores = {}
    if len(choices) >= 2:
        logits = model.anchors("owner", choices) @ matrix.direction(response)
        scores = {online.key(v): float(s) for v, s in zip(choices, logits, strict=True)}
    leaders = sorted(k for k in scores if scores[k] == max(scores.values()))
    desc = {"controller": control(state), "registry": values(state.registry.choices()),
            "matrix_norm": float(full.norm()), "matrix_sha256": sha(tbytes(full)),
            "owner_columns_norm": float(slices.norm()), "owner_columns_sha256": sha(tbytes(slices)),
            "query_sha256": sha(tbytes(query)), "owner_read_norm": float(response.norm()),
            "owner_read_sha256": sha(tbytes(response)), "owner_scores": scores, "leaders": leaders}
    return desc, (full, slices, response, query)


def parity(original, observed):
    check(len(original.attempts) == len(observed.attempts), "observer changed attempt count")
    check(all(torch.equal(a,b) for a,b in zip(original.matrices,observed.matrices,strict=True)),
          "observer changed final matrices")
    for a,b in zip(original.attempts, observed.attempts, strict=True):
        check((a.reason,a.choices,a.zero,a.summary_target,a.summary_zero) ==
              (b.reason,b.choices,b.zero,b.summary_target,b.summary_zero), "observer changed attempt")
        check(a.scores.keys() == b.scores.keys() and all(torch.equal(a.scores[f],b.scores[f]) for f in a.scores),
              "observer changed scores")


def trace(model, windows, original):
    events = {ordinal: [event for span in window.spans for event in online.identify(span, ordinal)]
              for ordinal, window in enumerate(windows, 1)}
    targets = [event for wr in events.values() for event in wr if event.kind == "TARGET"]
    query = None
    if len(targets) == 1:
        ordinal, _, index = targets[0].ptr
        query = model.project(windows[ordinal-1])[2][index]
    state = matrix.NeuralState(model.zero())
    snapshots, tensors, contexts = {}, {}, []
    cue_count = Counter()

    def snapshot(name, matrices, ptr):
        if query is None:
            return
        check(name not in snapshots, "ambiguous checkpoint identity")
        data, tensors[name] = numerics(model, matrices, state, query)
        snapshots[name] = {"ptr": ptr, **data}

    def observe(frame, event, arg):
        code = frame.f_code
        if event == "call" and code is matrix.attempt.__code__:
            local = frame.f_locals
            target = local["target"]
            snapshot("before-target/" + "/".join(map(str, target.ptr)), state.matrices, target.ptr)
            contexts.append({"ptr": target.ptr, "literal": target.literal, "raw_cells": target.value,
                             "controller": control(state), "registry": values(state.registry.choices()),
                             "actual_reads": {}})
        if event == "return" and code is matrix.Memory.read.__code__:
            local = frame.f_locals
            contexts[-1]["actual_reads"][local["field_name"]] = {
                "read_norm": float(arg.norm()), "read_sha256": sha(tbytes(arg)),
                "query_sha256": sha(tbytes(local["raw_query"]))}
        if event == "call" and code is matrix.Memory.write.__code__:
            for cue in frame.f_back.f_locals["events"]:
                if cue.kind == "OPEN_LEDGER":
                    ordinal = cue.ptr[0]
                    prefix = f"after-open-ledger/w{ordinal}/depth{state.controller.depth}"
                    snapshot(f"before-open-ledger/w{ordinal}/depth{state.controller.depth}/{cue_count[prefix]+1}",
                             frame.f_locals["matrices"], cue.ptr)
        if event == "return" and code is matrix.Memory.write.__code__:
            outer = frame.f_back.f_locals
            ordinal, span = outer["ordinal"], outer["span"]
            for cue in outer["events"]:
                if cue.kind == "DIRECTORY_OWNERS":
                    prefix = f"after-owner-directory/w{ordinal}"
                    cue_count[prefix] += 1
                    snapshot(f"{prefix}/{cue_count[prefix]}", arg, cue.ptr)
                if cue.kind == "OPEN_LEDGER":
                    prefix = f"after-open-ledger/w{ordinal}/depth{state.controller.depth}"
                    cue_count[prefix] += 1
                    snapshot(f"{prefix}/{cue_count[prefix]}", arg, cue.ptr)
            if span.index == len(outer["window"].spans) - 1:
                snapshot(f"end/w{ordinal}", arg, (ordinal, span.page, span.index))

    check(sys.getprofile() is None, "unexpected profiler")
    sys.setprofile(observe)
    try:
        for ordinal, window in enumerate(windows, 1):
            matrix.advance(model, state, window, ordinal)
    finally:
        sys.setprofile(None)
    parity(original, state)
    check(len(contexts) == len(state.attempts), "attempt context mismatch")
    return state, contexts, snapshots, tensors


def paired_checkpoints(members):
    first, second = sorted(members)
    a,b = members[first],members[second]
    out = {}
    for name in sorted(a.keys() | b.keys()):
        if name not in a or name not in b:
            out[name] = {"comparable": False, "reason": "missing_corresponding_checkpoint"}
            continue
        out[name] = {"comparable": True}
        for label, x, y in zip(("all_matrices","owner_columns","owner_read","own_target_query"),a[name],b[name],strict=True):
            out[name][label] = {"l2_difference": float((x-y).norm()), "equal": torch.equal(x,y)}
    return out
