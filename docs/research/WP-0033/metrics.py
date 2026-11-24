"""Lossless observations, deterministic scalar budgets and signed comparisons."""
import hashlib
import math

import torch

EPS = 1e-8
OWNERS = ("Alder", "Cedar")
LITERALS = (*OWNERS, "h")
CELLS = ("AA", "AC", "CA", "CC")


def raw(x):
    assert x.device.type == "cpu" and x.dtype in (torch.float32, torch.float64) and x.isfinite().all()
    return x.contiguous().numpy().tobytes()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pack(x):
    b = raw(x)
    return {"shape": list(x.shape), "dtype": "f32le" if x.dtype == torch.float32 else "f64le",
            "bytes": b.hex(), "sha256": digest(b)}


def limit(a, b=0.0):
    assert math.isfinite(a) and math.isfinite(b)
    return 2e-5 * (1 + max(abs(a), abs(b)))


def sign(x, budget=None):
    b = limit(x) if budget is None else budget
    return {"value": x, "zero_budget": b, "sign": "unresolved" if abs(x) <= b else "positive" if x > 0 else "negative"}


class Checks:
    def __init__(self):
        self.rows = []

    def scalar(self, name, observed, predicted, budget=None):
        observed, predicted = float(observed), float(predicted)
        b = limit(observed, predicted) if budget is None else budget
        d = observed - predicted
        self.rows.append(dict(at=name, observed=observed, predicted=predicted, residual=d, budget=b, passed=abs(d) <= b))

    def vector(self, name, observed, predicted):
        a, b = observed.double(), predicted.double()
        assert a.shape == b.shape
        delta = a - b
        limits = 2e-5 * (1 + torch.maximum(a.abs(), b.abs()))
        self.rows.append(dict(at=name, observed=pack(a), predicted=pack(b), residual=pack(delta), budget=pack(limits),
                              compared=a.numel(), failures=int((delta.abs() > limits).sum()), passed=bool((delta.abs() <= limits).all())))


def metrics(vector, anchors):
    a, c = anchors.unbind()
    norm = vector.norm().item()
    denom = norm + EPS
    na, nc, nh = (float(x @ vector) for x in (a, c, a-c))
    return {"Alder": na/denom, "Cedar": nc/denom, "margin": nh/denom, "numerator": nh,
            "Alder_numerator": na, "Cedar_numerator": nc, "read_norm": norm, "denominator": denom}


def observe(model, state, query, anchors, cuts):
    import experiment
    native = experiment.read(model, state, query, anchors, cuts)
    assert native["owner_eligible"] and native["native_scope_clear"] and state.controller.depth == 0
    v = torch.frombuffer(bytearray.fromhex(native["read_f32le"]), dtype=torch.float32)
    observed = metrics(v.double(), anchors.double())
    native["gap_f32"] = float(torch.diff(torch.tensor(sorted(native["scores"].values())))[0])
    native["owner_top1"] = native["top"]
    native["owner_thresholds_met"] = (not native["zero_read"] and native["top"] != "tie"
                                      and native["top_score_pass"] and native["top_gap_pass"])
    # Isolated owner instrumentation never invokes the subsequent typed posting.
    a, c = anchors.unbind()
    native["scalar_f32"] = {k: pack(x) for k, x in (("read_norm", v.norm()), ("denominator", v.norm()+EPS),
                              ("Alder_numerator", a @ v), ("Cedar_numerator", c @ v), ("numerator", (a-c) @ v))}
    return native, v, observed


def compare_read(tag, native, vector, observed, predicted_vector, anchors, checks):
    forecast = metrics(predicted_vector, anchors.double())
    checks.vector(tag+"/owner_read", vector, predicted_vector)
    for k, pred in forecast.items():
        val = native["scores"][k] if k in OWNERS else native["margin"] if k == "margin" else observed[k]
        checks.scalar(tag+"/"+k, val, pred)
    return forecast


def parity(arm, mode, point, cell, native, observed):
    return {"arm": arm, "mode": mode, "point": point, "cell": cell, "score_f32le": native["score_f32le"],
            "read_sha256": native["read_sha256"], "matrix_sha256": native["matrix_sha256"],
            "numerator": observed["numerator"], "margin": native["margin"], "read_norm": observed["read_norm"]}


def effect(values, coeffs, predicted=None):
    """A contrast sums its own corner budgets. Each weight also scales the associated budget."""
    value = sum(values[k]*a for k, a in coeffs)
    uncertainty = sum(abs(a)*limit(values[k]) for k, a in coeffs)
    result = sign(value, uncertainty)
    if predicted is not None:
        prediction = sum(predicted[k]*a for k, a in coeffs)
        budget = sum(abs(a)*limit(values[k], predicted[k]) for k, a in coeffs)
        result.update(predicted=prediction, residual=value-prediction, budget=budget, passed=abs(value-prediction) <= budget)
    return result
