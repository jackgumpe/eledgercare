"""Truth-independent paired inference. Only the two recurrent-matrix tuples cross twins."""
import copy
import hashlib
import json
import time

import torch

from matrix import NeuralState, advance, attempt, result
from online import Controller, Discrete, Event, Registry, abstain, identify, reachable_size, single


def matrices_digest(matrices):
    h = hashlib.sha256()
    for m in matrices:
        h.update(m.detach().contiguous().numpy().tobytes())
    return h.hexdigest()


def nonmatrix_digest(state):
    fields = {
        "held": state.controller.held, "depth": state.controller.depth,
        "fault": state.controller.fault, "growth": state.growth, "trace": state.trace,
        "registry": [sorted(state.registry.owners), sorted(state.registry.units),
                     sorted(state.registry.schemas)],
        "attempts": [(a.reason, a.zero, a.summary_target, a.summary_zero, a.choices, {k: v.tolist() for k, v in a.scores.items()})
                     for a in state.attempts]}
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def window_reg(window):
    registry = Registry()
    for span in window.spans:
        for event in identify(span, 1):
            registry.update(event)
    return registry


def candidate_receipt(window):
    registry = window_reg(window)
    payload = {"choices": registry.choices(), "ordered_schemas": sorted(registry.schemas)}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return {"inputs": payload, "sha256": hashlib.sha256(raw).hexdigest()}


def window1_audit(model, window, cuts):
    # Audit-only snapshot. The object is discarded and never used by any arm.
    events = [e for s in window.spans for e in identify(s, 1)
              if e.kind in {"OPEN_LEDGER", "DECLARE_UNIT", "HEADER"}]
    observed = [{"kind": e.kind, "value": e.value, "ptr": e.ptr, "literal": e.literal} for e in events]
    if not window.spans:
        return {"observed": observed, "encoded": abstain("empty_window"), "decoded_binding": None}
    last = window.spans[-1]
    probe = Event("AUDIT", ("Posting",), (1, last.page, last.index), last.text)
    if model is None:
        state = Discrete()
        state.window(window, 1)
        controller = state.controller
        state.controller = Controller()
        frame = state.frames[0]
        encoded = state.post(frame, probe)
    else:
        state = NeuralState(model.zero())
        advance(model, state, window, 1)
        controller = state.controller
        state.controller = Controller()
        q = model.project(window)[2][-1]
        encoded = attempt(model, state, q, probe).binding(cuts)
    schema = None
    if model is None and frame.header is not None:
        schema = frame.header.value
    elif encoded["type"] == "Posting":
        matches = [s for s in state.registry.schemas if len(s) > 1 and s[1] == encoded["column"]]
        if len(matches) == 1:
            schema = matches[0]
    decoded = {k: encoded[k] for k in ("owner", "unit", "column")} if encoded["type"] == "Posting" else None
    return {"observed": observed, "query_ptr": probe.ptr, "encoded": encoded, "encoded_schema": schema,
            "decoded_binding": decoded, "active_depth": controller.depth,
            "shadow_hold": controller.held[controller.depth], "audit_read_depth": 0}


def symbolic(windows, only_suffix):
    state = Discrete(window_reg(windows[0]) if only_suffix else None)
    times = []
    live, inclusive = [], []
    binding_outputs = []
    for ordinal, window in enumerate(windows, 1):
        if only_suffix and ordinal < len(windows):
            continue
        start = time.perf_counter_ns()
        for span in window.spans:
            for e in identify(span, ordinal):
                if e.kind == "TARGET":
                    frame = state.frames[state.controller.depth]
                    dummy = Event(e.kind, ("Posting", *e.value[1:]), e.ptr, e.literal)
                    # Kept outside decision state, using the same current frame.
                    binding_outputs.append(state.post(frame, dummy))
                state.consume(e)
        state.registry_growth.append(state.registry.size())
        times.append(time.perf_counter_ns() - start)
        live.append(reachable_size([state.frames, state.controller, state.registry, state.outputs]))
        inclusive.append(reachable_size(state))
    summary = single(state.summary_outputs) if state.summary_outputs else None
    return {"binding_diagnostic": single(binding_outputs), "subtotal_diagnostic": summary, "decision": single(state.outputs), "trace": state.trace, "window_ns": times,
            "registry_growth": state.registry_growth, "lookup_ns": state.lookup_ns,
            "live_host_bytes": live, "including_audit_host_bytes": inclusive}


def timed_window(model, state, window, ordinal, zero=False):
    start = time.perf_counter_ns()
    advance(model, state, window, ordinal, zero)
    return time.perf_counter_ns() - start


def finish(model, state, window, ordinal, prefix_times, thresholds, zero=False):
    elapsed = timed_window(model, state, window, ordinal, zero)
    start = time.perf_counter_ns()
    decision = result(state, thresholds)
    elapsed += time.perf_counter_ns() - start
    statuses = [a.summary(thresholds) for a in state.attempts if a.summary_target]
    return {"binding_diagnostic": single([a.binding(thresholds) for a in state.attempts]), "subtotal_diagnostic": single(statuses) if statuses else None, "decision": decision, "trace": state.trace, "window_ns": prefix_times + [elapsed],
            "registry_growth": state.growth, "lookup_ns": state.lookup_ns,
            "fixed_matrix_bytes": len(state.matrices) * 128 * 128 * 4,
            "target_scores": [{name: dict(zip(attempt.choices[name], scores.tolist()))
                               for name, scores in attempt.scores.items()} for attempt in state.attempts]}


@torch.inference_mode()
def predict_pair(m1, m3, thresholds, windows_a, windows_b):
    twins = (windows_a, windows_b)
    n = len(windows_a)
    if n not in (4, 10) or len(windows_b) != n:
        raise ValueError("paired binder horizons must match at four or ten windows")
    wa, wb = windows_a[-1], windows_b[-1]
    if wa.spans != wb.spans or wa.features.numpy().tobytes() != wb.features.numpy().tobytes():
        raise ValueError("pair final sensor suffix differs")
    outputs = [{}, {}]
    candidates = [candidate_receipt(w[0]) for w in twins]
    prefix_states, prefix_times = [], []
    for side, windows in enumerate(twins):
        for name, model, zero in (("M1", m1, False), ("M3-Zero", m3, True), ("M3", m3, False)):
            state = NeuralState(model.zero())
            timings = [timed_window(model, state, w, i, zero)
                       for i, w in enumerate(windows[:-1], 1)]
            if name == "M3":
                prefix_states.append(state)
                prefix_times.append(timings)
            else:
                cuts = thresholds["M1" if name == "M1" else "M3"]
                outputs[side][name] = finish(model, state, windows[-1], n, timings, cuts, zero)
        outputs[side]["M0"] = symbolic(windows, True)
        outputs[side]["M2"] = symbolic(windows, False)

    hashes = [matrices_digest(s.matrices) for s in prefix_states]
    controls = [nonmatrix_digest(s) for s in prefix_states]
    for side, windows in enumerate(twins):
        for name, donor in (("M3", side), ("M3-Swap", 1 - side)):
            state = copy.deepcopy(prefix_states[side])
            state.matrices = prefix_states[donor].matrices
            actual_matrix = matrices_digest(state.matrices)
            actual_aux = nonmatrix_digest(state)
            if (actual_matrix, actual_aux) != (hashes[donor], controls[side]) or state.lookup_ns != prefix_states[side].lookup_ns:
                raise AssertionError("incorrect matrix or nonmatrix boundary")
            output = finish(m3, state, windows[-1], n, prefix_times[side], thresholds["M3"])
            output["final_entry"] = {"matrix_sha256": actual_matrix, "nonmatrix_sha256": actual_aux,
                                     "original_matrix_sha256": hashes[side],
                                     "receiver_nonmatrix_sha256": controls[side]}
            outputs[side][name] = output
    identical = candidates[0]["sha256"] == candidates[1]["sha256"]
    for side, windows in enumerate(twins):
        for record in outputs[side].values():
            record["candidate_receipt"] = {**candidates[side], "pair_equal": identical}
        outputs[side]["M2"]["window1_audit"] = window1_audit(None, windows[0], None)
        outputs[side]["M3"]["window1_audit"] = window1_audit(m3, windows[0], thresholds["M3"])
    return outputs
