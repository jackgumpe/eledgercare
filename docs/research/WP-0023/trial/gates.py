"""Token, terminal, page and replay comparisons shared by all stages."""
import math


ORDER = ("short", "long")
PAGE = 128827
FIELDS = ("prompt_token_ids", "token_ids", "text", "eos_id", "eos_observed", "stop_cause",
          "finish_reason", "num_pages_out", "expected_pages")


def decisions(row):
    return row["token_ids"] + ([row["eos_id"]] if row["eos_observed"] else [])


def structure(row):
    ids = row["token_ids"]
    return bool(row["eos_observed"] and row["stop_cause"] == "eos" and row["finish_reason"] == "stop"
                and row["expected_pages"] == row["num_pages_out"] == ids.count(PAGE) == 3
                and row["prompt_token_ids"].count(PAGE) == 3 and ids[0] == PAGE and row["eos_id"] not in ids
                and row["text"].startswith("<PAGE>") and row["text"].count("<PAGE>") == 3)


def compare(control, trial):
    fields = [k for k in FIELDS if control[k] != trial[k]]
    left, right = decisions(control), decisions(trial)
    common = 0
    for a, b in zip(left, right):
        if a != b:
            break
        common += 1
    first = None
    if common < max(len(left), len(right)):
        first = {"step_zero_based": common,
                 "native_id": left[common] if common < len(left) else None,
                 "batch_id": right[common] if common < len(right) else None}
    return dict(passed=not fields and structure(control) and structure(trial),
                native_structure=structure(control), trial_structure=structure(trial), different_fields=fields,
                shared_decisions=common, first=first)


def deltas(singleton, batch, candidates):
    out = {}
    for stage in ("raw", "processed"):
        a, b = singleton[stage], batch[stage]
        out[stage] = {}
        for token in candidates:
            key = str(token)
            x, y = float(a["candidates"][key]), float(b["candidates"][key])
            if math.isnan(x) or math.isnan(y):
                raise ValueError("NaN candidate score")
            d = y - x
            signed = ("undefined-equal-infinities" if math.isnan(d) else
                      ("-inf" if d < 0 else "+inf") if math.isinf(d) else d)
            out[stage][key] = {"b1": a["candidates"][key], "b2": b["candidates"][key], "b2_minus_b1": signed}
    return out


def check_probe(probe, token):
    for stage in ("raw", "processed"):
        if len(probe[stage]["top2"]) != 2:
            raise ValueError("Expected two diagnostic logits")
    if probe["processed"]["argmax"] != token:
        raise ValueError("BF16 matched-prefix replay failed to reproduce selected token")
