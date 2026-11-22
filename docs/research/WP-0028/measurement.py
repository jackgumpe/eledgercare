"""Numerical functions accept only a frozen model, windows and fixed cuts."""
import hashlib
import json
import struct

import matrix
import online
import run
import torch
from inputs import check, sha
from observe import control, tbytes, trace
from score_math import NAMES, TIMES


def digest_object(obj):
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def query_context(model, windows):
    registry, controller = online.Registry(), online.Controller()
    targets, parents = [], []
    for wi, window in enumerate(windows, 1):
        for span in window.spans:
            events = list(online.identify(span, wi))
            for ev in events:
                controller.apply(ev)
                registry.update(ev)
                if ev.kind == "OPEN_LEDGER" and wi == 1 and controller.depth == 0:
                    parents.append(ev.ptr)
            for ev in events:
                if ev.kind == "TARGET":
                    targets.append((ev, tuple(registry.choices()["owner"]), controller.ambiguous()))
    if len(targets) != 1:
        return None, "target_count_" + str(len(targets))
    event, keys, fault = targets[0]
    ordinal, page, index = event.ptr
    if len(parents) != 1 or parents[0][:2] != (1,1):
        return None, "parent_event_identity"
    if fault or ordinal != len(windows) or page != 2 or set(keys) != set(NAMES):
        return None, "target_scope_identity_or_candidates"
    window = windows[ordinal-1]
    projected = model.project(window)[2][index]
    return {"ptr": event.ptr, "literal": event.literal, "cells": event.value,
            "candidate_order": keys, "query_sha256": sha(tbytes(projected)),
            "parent_ptr": parents[0]}, None


def comparable(contexts):
    if any(reason for _, reason in contexts):
        return ",".join(sorted({reason for _, reason in contexts if reason}))
    first, second = (entry for entry, _ in contexts)
    for name in ("ptr", "literal", "cells", "candidate_order", "query_sha256"):
        if first[name] != second[name]:
            return "target_mismatch_" + name
    return None


def state_receipt(state, cuts):
    attempts = []
    for item in state.attempts:
        attempts.append({"reason": item.reason, "choices": item.choices, "zero": item.zero,
                         "summary_target": item.summary_target, "summary_zero": item.summary_zero,
                         "logit_sha256": {f: sha(tbytes(x)) for f,x in item.scores.items()},
                         "typed": item.typed(cuts)})
    return {"matrix_sha256": sha(tbytes(torch.stack(state.matrices))),
            "controller": control(state), "registry": state.registry.choices(),
            "attempts": attempts, "typed": matrix.result(state, cuts)}


def choose_snapshots(snapshots, context, windows):
    selection = {"t1": "after-open-ledger/w1/depth0/1", "t2": "end/w1",
                 "t3": "before-target/" + "/".join(map(str, context["ptr"]))}
    last = windows[0].spans[-1]
    expected = (context["parent_ptr"], (1, last.page, last.index), context["ptr"])
    for key, ptr in zip(selection.values(), expected, strict=True):
        snap = snapshots[key]
        check(snap["ptr"] == ptr and snap["query_sha256"] == context["query_sha256"],
              "checkpoint pointer or query changed")
        check(set(snap["registry"]["owner"].values()) == set(NAMES), "owner keys missing")
    return selection


def observe_once(model, windows, cuts, original):
    state, contexts, snapshots, tensors = trace(model, windows, original)
    context, reason = query_context(model, windows)
    check(reason is None and len(contexts) == 1, "target admission changed")
    selected = choose_snapshots(snapshots, context, windows)
    rows = {}
    for t, key in selected.items():
        snap = snapshots[key]
        full, _, _, query = tensors[key]
        choices = snap["registry"]
        values = {literal: snap["owner_scores"][online.key(literal)] for literal in NAMES}
        scores_raw = b"".join(struct.pack("<f", value) for value in values.values())
        top = torch.tensor(list(values.values()), dtype=torch.float32).topk(2).values
        evidence = {}
        for field in ("unit", "column"):
            literals = tuple(choices[field].values())
            scores = None
            if len(literals) >= 2:
                response = model.read(tuple(full.unbind()), snap["controller"]["depth"], query, field)
                logits = model.anchors(field, literals) @ matrix.direction(response)
                scores = {v: float(s) for v,s in zip(literals, logits, strict=True)}
                if t == "t3":
                    check(tbytes(logits) == tbytes(original.attempts[0].scores[field]),
                          "control read inconsistent with native attempt")
            evidence[field] = scores
        if t == "t3":
            actual = original.attempts[0]
            check(tuple(actual.choices["owner"]) == NAMES, "unexpected native candidate order")
            check(scores_raw == tbytes(actual.scores["owner"]), "native t3 owner scores changed")
            actual_read = contexts[0]["actual_reads"]["owner"]
            check((actual_read["read_sha256"], actual_read["query_sha256"]) ==
                  (snap["owner_read_sha256"], snap["query_sha256"]), "native t3 read changed")
        rows[t] = {"pointer": list(snap["ptr"]), "source_checkpoint": key, "role":
                   "normal_target_before_write" if t == "t3" else "retrospective",
                   "target_available": True, "candidate_order": list(context["candidate_order"]),
                   "controller": snap["controller"], "query_sha256": snap["query_sha256"],
                   "matrix_sha256": snap["matrix_sha256"], "read_sha256": snap["owner_read_sha256"],
                   "owner_columns_sha256": snap["owner_columns_sha256"], "scores": values,
                   "score_bytes_f32le_sha256": sha(scores_raw), "exact_top_tie": bool(top[0] == top[1]),
                   "zero_read": snap["owner_read_norm"] <= matrix.EPS,
                   "top_score_pass": bool(top[0] >= cuts[0]), "top_gap_pass": bool(top[0]-top[1] >= cuts[1]),
                   "unit_column_controls": evidence,
                   "typed": matrix.result(state, cuts) if t == "t3" else None, "reason": None}
    return rows, state, snapshots


def measure(model, paths, cuts):
    load = lambda: [online.load_window(p) for p in paths]
    windows = load()
    plain = run.state_for(model, windows)
    audited = matrix.NeuralState(model.zero())
    for ordinal, window in enumerate(windows, 1):
        matrix.advance(model, audited, window, ordinal)
    first, s1, snaps = observe_once(model, windows, cuts, plain)
    # Fresh load and a fresh zero state, including a second plain target execution.
    again = load()
    plain2 = run.state_for(model, again)
    second, s2, _ = observe_once(model, again, cuts, plain2)
    states = {name: digest_object(state_receipt(state, cuts)) for name,state in
              (("plain", plain), ("plain_repeat", plain2), ("audit_on", audited),
               ("recorded", s1), ("recorded_repeat", s2))}
    traces = {name: digest_object([s.trace, s.growth]) for name,s in
              (("audit_on", audited), ("recorded", s1), ("recorded_repeat", s2))}
    check(len(set(states.values())) == len(set(traces.values())) == 1, "state or audit trajectory mismatch")
    check(digest_object(first) == digest_object(second), "duplicate read mismatch")
    receipts = {"final_state": states, "trajectory": traces, "first_checkpoints": digest_object(first),
                "repeat_checkpoints": digest_object(second), "plain_target": state_receipt(plain, cuts)}
    return first, receipts, snaps


def zero_control(model, window, cuts):
    # Real registry candidates and real final source query, fresh all-zero frozen state.
    state = matrix.NeuralState(model.zero())
    for span in window[0].spans:
        for event in online.identify(span, 1):
            state.registry.update(event)
    targets = [e for span in window[-1].spans for e in online.identify(span,len(window)) if e.kind == "TARGET"]
    target, = targets
    query = model.project(window[-1])[2][target.ptr[2]]
    item = matrix.attempt(model, state, query, target)
    decision = item.typed(cuts)
    logits = item.scores["owner"]
    check(item.zero and tbytes(logits) == bytes(8) and decision == online.abstain("zero_state_tie"),
          "zero-read tie control failed")
    return {"scores": dict(zip(item.choices["owner"], logits.tolist(), strict=True)),
            "decision": decision, "zero": item.zero, "query_sha256": sha(tbytes(query))}
