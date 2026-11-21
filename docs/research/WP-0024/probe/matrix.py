"""A single matched parameterization, used flat or depth-stratified. CPU FP32."""
import hashlib
import math
import time
from dataclasses import dataclass, field
from functools import lru_cache

import torch
from torch import nn
from torch.nn import functional as F

from online import Controller, Registry, abstain, identify, key, single

WIDTH = 128
PROTECTED = 96
RANK = 4
RANK_EPS = 1e-6
EPS = 1e-8


def direction(v):
    return v / (v.norm(dim=-1, keepdim=True) + EPS)


def blocks(spans, features):
    if not spans:
        return features.new_empty((0, 1312))
    boxes = features.new_tensor([span.box for span in spans]) / 999.0
    phases = boxes.unsqueeze(-1) * features.new_tensor([1., 2., 4., 8.]) * (2 * math.pi)
    return torch.cat((features, phases.sin().flatten(1), phases.cos().flatten(1)), dim=1)


@lru_cache(maxsize=256)
def lexical_input(field_name, value):
    """Content-only, signed boundary-marked char ngrams. Cache carries no binder state."""
    text = "^" + field_name + "=" + key(value) + "$"
    result = torch.zeros(1312)
    for length in (1, 2, 3, 4):
        for index in range(len(text) - length + 1):
            digest = hashlib.sha256(text[index:index + length].encode("utf8")).digest()
            slot = int.from_bytes(digest[:4], "little") % result.numel()
            result[slot] += 1 if digest[4] & 1 else -1
    return direction(result)


def masked_basis(projected):
    """Run QR strictly inside the 32 summary coordinates, then mask by |Rjj|."""
    q, r = torch.linalg.qr(projected, mode="reduced")
    keep = r.diag().abs() >= RANK_EPS
    # Unpivoted QR's PyTorch backward is undefined for rank deficiency. The
    # forward formula and threshold are unmodified. Only its ill-conditioned
    # basis derivative is stopped; Vsum and WVpop still receive value gradients.
    if torch.is_grad_enabled() and not bool(torch.all(keep)):
        q = q.detach()
    return q * keep.to(q.dtype), keep


class Memory(nn.Module):
    def __init__(self, flat):
        super().__init__()
        self.flat = flat
        self.write_key = nn.Linear(1312, PROTECTED, bias=False)
        self.write_value = nn.Linear(1312, WIDTH, bias=False)
        self.query = nn.Linear(1312, WIDTH, bias=False)
        self.gates = nn.Linear(1312, 2)
        self.anchor_value = nn.Linear(1312, 139, bias=False)
        self.anchor_gate = nn.Linear(1312, 139, bias=False)
        self.anchor_output = nn.Linear(139, WIDTH, bias=False)
        self.summary_query = nn.Parameter(torch.empty(WIDTH, RANK))
        self.pop_key = nn.Linear(WIDTH, WIDTH, bias=False)
        self.pop_value = nn.Linear(WIDTH, WIDTH, bias=False)
        nn.init.orthogonal_(self.summary_query)
        with torch.no_grad():
            self.gates.bias.copy_(torch.tensor([4., 0.]))

    def zero(self):
        z = self.summary_query.new_zeros((WIDTH, WIDTH))
        return (z,) * (1 if self.flat else 8)

    def project(self, window):
        u = blocks(window.spans, window.features)
        k = self.write_key(u)
        q = self.query(u)
        # PDS omits the structurally zero rows. The flat comparator has a
        # full-space key, tying its last 32 projected coordinates to its query.
        k = torch.cat((k, q[:, PROTECTED:]), 1) if self.flat else F.pad(k, (0, WIDTH - PROTECTED))
        a, b = self.gates(u).sigmoid().unbind(-1)
        return direction(k), self.write_value(u), q, a, 2.0 * b

    def write(self, matrices, depth, k, v, a, b):
        lane = 0 if self.flat else depth
        old = matrices[lane]
        # Every inactive lane has masked decay 1 and key 0. Reusing that
        # tensor is the exact (and cheapest) realization of its recurrence.
        residual = v - a * (old @ k)
        updated = a * old + b * torch.outer(residual, k)
        return matrices[:lane] + (updated,) + matrices[lane + 1:]

    def pop(self, matrices, depth):
        if self.flat:
            return matrices, None
        if not 1 <= depth < 8:
            raise ValueError("a pop requires an active child")
        child = matrices[depth]
        parent = matrices[depth - 1]
        values = child @ self.summary_query
        basis, keep = masked_basis(self.pop_key(values.T).T[PROTECTED:])
        old = parent[:, PROTECTED:]
        new_summary = old + (self.pop_value(values.T).T - old @ basis) @ basis.T
        parent_new = torch.cat((parent[:, :PROTECTED], new_summary), dim=1)
        committed = matrices[:depth - 1] + (parent_new, torch.zeros_like(child)) + matrices[depth + 1:]
        return committed, keep

    def anchors(self, name, values):
        x = torch.stack([lexical_input(name, v) for v in values])
        literal = self.anchor_output(self.anchor_value(x) * self.anchor_gate(x).sigmoid())
        # Both models use exactly these parameters in the same anchor function.
        # The rank-four adapter shares the pop transforms without adding a
        # second memory to the flat arm.
        adapter = ((self.pop_key(literal) @ self.summary_query) @ self.summary_query.T)
        return direction(literal + self.pop_value(adapter))

    def read(self, matrices, depth, raw_query, field_name):
        if field_name == "subtotal_status":
            q = direction(raw_query[PROTECTED:])
            return matrices[0 if self.flat else depth][:, PROTECTED:] @ q
        start, stop = (32, PROTECTED) if field_name == "column" else (0, 32)
        q = direction(raw_query[start:stop])
        if self.flat:
            return matrices[0][:, start:stop] @ q
        # Ordered depth scores derive exclusively from the observed controller.
        weights = raw_query.new_tensor(range(depth + 1)).softmax(dim=0)
        return sum(weights[i] * (matrices[i][:, start:stop] @ q) for i in range(depth + 1))


@dataclass
class Attempt:
    reason: str = ""
    scores: dict = field(default_factory=dict)
    choices: dict = field(default_factory=dict)
    zero: bool = False
    summary_target: bool = False
    summary_zero: bool = False

    def binding(self, thresholds):
        names = ("owner", "unit", "column")
        if not all(k in self.scores for k in names):
            return abstain(self.reason or "incomplete_binding")
        isolated = Attempt(scores={k: self.scores[k] for k in names}, choices=self.choices)
        value = isolated.typed(thresholds)
        if value["type"] == "Posting":
            del value["subtotal_status"]
        return value

    def summary(self, thresholds):
        if not self.summary_target:
            return None
        if "subtotal_status" not in self.scores:
            return abstain(self.reason or "unobserved_subtotal")
        isolated = Attempt(scores={"subtotal_status": self.scores["subtotal_status"]},
                           choices=self.choices, zero=self.summary_zero)
        value = isolated.typed(thresholds)
        if value["type"] == "Posting":
            value["type"] = "STATUS"
        return value

    def typed(self, thresholds):
        if self.reason:
            return abstain(self.reason)
        if self.zero:
            return abstain("zero_state_tie")
        output = {"type": "Posting", "subtotal_status": None}
        for name, logits in self.scores.items():
            top, indices = logits.detach().topk(2)
            if top[0] == top[1]:
                return abstain("zero_state_tie")
            if top[0] < thresholds[0] or top[0] - top[1] < thresholds[1]:
                return abstain("below_threshold_" + name)
            output[name] = self.choices[name][indices[0].item()]
        return output


@dataclass
class NeuralState:
    matrices: tuple
    controller: Controller = field(default_factory=Controller)
    registry: Registry = field(default_factory=Registry)
    attempts: list = field(default_factory=list)
    trace: list = field(default_factory=list)
    growth: list = field(default_factory=list)
    lookup_ns: int = 0


def attempt(model, state, q, target):
    begin = time.perf_counter_ns()
    choices = state.registry.choices()
    state.lookup_ns += time.perf_counter_ns() - begin
    reason = state.controller.ambiguous()
    summary = key(target.value[0]) == "maint-summary"
    if reason:
        return Attempt(reason=reason, summary_target=summary)
    fields = ["owner", "unit", "column"] + (["subtotal_status"] if summary else [])
    result = Attempt(choices=choices, summary_target=summary)
    for name in fields:
        if len(choices[name]) < 2:
            result.reason = "incomplete_candidates"
            continue
        response = model.read(state.matrices, state.controller.depth, q, name)
        zero = response.detach().norm().item() <= EPS
        result.zero |= zero
        if name == "subtotal_status":
            result.summary_zero = zero
        result.scores[name] = model.anchors(name, choices[name]) @ direction(response)
    return result


def advance(model, state, window, ordinal, zero=False, audit=True):
    keys, values, queries, alphas, betas = model.project(window)
    for span in window.spans:
        events = list(identify(span, ordinal))
        i = span.index
        # Control transitions precede the current observation. A pop commits
        # child memory as of the prior span; the closing cue writes to the parent.
        for event in events:
            prior_depth = state.controller.depth
            state.controller.apply(event)
            state.registry.update(event)
            rank = None
            if event.kind == "CONFIRM_POP" and state.controller.depth < prior_depth and not zero:
                state.matrices, kept = model.pop(state.matrices, prior_depth)
                if kept is not None and audit:
                    rank = int(kept.sum())
            if audit:
                state.trace.append({"event": event.kind, "literal": event.literal, "ptr": event.ptr,
                                    "depth_after": state.controller.depth, "pop_rank": rank,
                                    "shadow_hold": state.controller.held[state.controller.depth]})
        for event in events:
            if event.kind == "TARGET":
                # Read BEFORE writing this target so its own residual cannot act
                # as an independent matrix-free posting.
                state.attempts.append(attempt(model, state, queries[i], event))
        if not zero:
            state.matrices = model.write(state.matrices, state.controller.depth,
                                         keys[i], values[i], alphas[i], betas[i])
    if audit:
        state.growth.append(state.registry.size())


def result(state, thresholds):
    return single([item.typed(thresholds) for item in state.attempts])
