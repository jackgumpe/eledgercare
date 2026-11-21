"""Recompute primary parity, diagnostic evidence and timed ratios from reviewer-owned records."""
import argparse
import hashlib
from itertools import zip_longest
import json
import math
from pathlib import Path


PAGE = 128827
WINDOWS = ["short", "long"]


def load(folder, name):
    return json.loads((folder / (name + ".json")).read_bytes())


def stream(row):
    return row["token_ids"] + ([row["eos_id"]] if row["eos_observed"] else [])


def first(left, right):
    return next((dict(step=n, singleton=a, candidate=b)
                 for n, (a, b) in enumerate(zip_longest(left, right)) if a != b), None)


def markers(ids):
    return [i for i, tok in enumerate(ids) if tok == PAGE]


def compare(stock, cand):
    keys = ("text", "prompt_token_ids", "finish_reason", "stop_cause", "eos_observed",
            "eos_id", "expected_pages", "num_pages_out")
    special = {key: stock[key] == cand[key] for key in keys}
    pos = markers(cand["token_ids"])
    valid = (cand["stop_cause"] == "eos" and cand["finish_reason"] == "stop" and cand["eos_observed"]
             and cand["eos_id"] not in cand["token_ids"] and len(pos) == cand["expected_pages"] == 3
             and cand["num_pages_out"] == 3 and pos[0] == 0 and cand["text"].startswith("<PAGE>")
             and cand["text"].count("<PAGE>") == len(markers(cand["prompt_token_ids"])) == 3)
    delta = first(stream(stock), stream(cand))
    return dict(passes=all(special.values()) and valid and delta is None, same=special, first=delta,
                emitted=len(cand["token_ids"]), stop=cand["stop_cause"], pages=pos)


def shape_check(result, size):
    calls = result["forwards"]
    assert calls["batch_size"] == size and calls["prefill"] == 1
    if all(row["eos_observed"] for row in result["lanes"]):
        assert calls["decode"] == max(len(row["token_ids"]) for row in result["lanes"])
    for phase in ("prefill_shapes", "first_decode_shapes"):
        shape = calls[phase]
        assert all(v[0] == size for v in shape.values())
        assert shape["hidden"][:2] == shape["input_ids"]
        assert shape["lm_head"][:2] == [size, 1]
    assert calls["prefill_shapes"]["input_ids"][1] > 1
    assert calls["first_decode_shapes"]["input_ids"] == [size, 1]
    for row in result["lanes"]:
        if row["eos_observed"]:
            assert row["last_selected_step"] == len(row["token_ids"])
            assert row["last_selected_token"] == row["eos_id"]
            assert row["last_guard_scan"] == guards(row["token_ids"], row["eos_id"], [])[0]
    c = result["prefill_cache_shapes"]
    assert c["kv"] and all(v[0] == size and len(v) == 4 for v in c["kv"])
    assert c["dash_index_keys"] and all(v[0] == size for v in c["dash_index_keys"].values())
    assert c["page_rope"] and all(v[0] == size for v in c["page_rope"].values())
    assert all(v[0] == size for v in c["page_state"].values())
    return dict(batch=size, decode=calls["decode"], prefill_kv=c["kv"][0],
                prefill_shapes=calls["prefill_shapes"], first_decode_shapes=calls["first_decode_shapes"],
                kv_layers=len(c["kv"]), dash_layers=len(c["dash_index_keys"]), page_rope_layers=len(c["page_rope"]))


def guards(prefix, eos, candidates):
    pages = markers(prefix)
    tail = len(prefix) - 1 - pages[-1] if pages else len(prefix)
    banned = {prefix[j+34] for j in range(max(0, len(prefix) - 1024), len(prefix)-34)
              if prefix[j:j+34] == prefix[-34:]}
    force = None
    if len(pages) > 3 or (len(pages) == 3 and tail >= 20000):
        force = eos
    elif tail >= 20000:
        force = PAGE
    restricted = [(c in banned, (c == eos and len(pages) < 3) if force is None else c != force)
                  for c in candidates]
    return dict(scanned=len(prefix), marker_cum=len(pages), page_len=tail), restricted


def signed(x, y):
    value = float(y) - float(x)
    if math.isnan(value):
        return "undefined-equal-infinities"
    return value if math.isfinite(value) else ("+inf" if value > 0 else "-inf")


def verified_top(obs):
    top = obs["top2"]
    assert len(top) == 2 and top[0]["id"] != top[1]["id"]
    assert float(top[0]["logit"]) >= float(top[1]["logit"])
    if obs["argmax"] != top[0]["id"]:
        # torch.argmax uses first-index tie ordering; torch.topk can select another tied id.
        assert float(top[0]["logit"]) == float(top[1]["logit"])
    for entry in top:
        score = obs["candidates"].get(str(entry["id"]))
        if score is not None:
            assert float(score) == float(entry["logit"])
    return top


def vector_deltas(single, double):
    def norm(v):
        return math.sqrt(sum(x*x for x in v))
    assert len(single) == len(double)
    records = []
    for i, (a, b) in enumerate(zip(single, double)):
        assert len(a) == len(b)
        diff = [y-x for x, y in zip(a, b)]
        records.append(dict(layer_boundary=i, width=len(a), equal=a==b,
                            max_abs=max(map(abs,diff)), relative_l2=norm(diff) / max(norm(a), 1e-30)))
    return records


def diagnose(folder, order, key, slot, diff, native, observed):
    compare_row = load(folder, "diag-" + "-".join(order) + "-" + key + "-compare")
    candidates = [diff["singleton"], diff["candidate"]]
    prefix = stream(native[key])[:diff["step"]]
    assert prefix == stream(observed["lanes"][slot])[:diff["step"]]
    digest = hashlib.sha256(json.dumps(prefix, separators=(",", ":")).encode()).hexdigest()
    assert digest == compare_row["target_history"]["sha256"]
    state, restrictions = guards(prefix, native[key]["eos_id"], candidates)
    peer = stream(observed["lanes"][1-slot])[:diff["step"]]
    assert hashlib.sha256(json.dumps(peer, separators=(",", ":")).encode()).hexdigest() == compare_row["peer_history"]["sha256"]
    found = {}
    for label, src in compare_row["source_files"].items():
        record = load(folder, src)["result"]
        probe = record if label == "stock" else record["probe"]
        guard = probe["guard"] if label == "stock" else probe["guard"]["after"]
        assert guard == state
        assert probe["step"] == diff["step"]
        if label != "stock":
            assert record["lanes"][probe["lane"]]["token_ids"] == prefix
        found[label] = probe
    s, w, b = (found[k] for k in ("stock", "wrapper_b1", "wrapper_b2"))
    cross = {}
    for stage in ("raw", "processed"):
        cross[stage] = {}
        for label, probe in found.items():
            verified_top(probe[stage])
        for i, token in enumerate(candidates):
            k = str(token)
            for probe in found.values():
                raw = float(probe["raw"]["candidates"][k])
                expected = -math.inf if any(restrictions[i]) else raw
                assert float(probe["processed"]["candidates"][k]) == expected
            x, y = s[stage]["candidates"][k], b[stage]["candidates"][k]
            delta = signed(x, y)
            assert delta == compare_row["stock_to_b2"][stage][k]["b2_minus_b1"]
            cross[stage][k] = dict(stock=x, b2=y, b2_minus_stock=delta)
    return dict(order=order, key=key, slot=slot, prefix_sha256=digest, peer_prefix_length=len(peer),
                guard=state, token_restrictions=restrictions, observed_choice=candidates,
                replay_winners={label: probe["processed"]["argmax"] for label, probe in found.items()},
                processed_top2={label: probe["processed"]["top2"] for label, probe in found.items()},
                raw_top2={label: probe["raw"]["top2"] for label, probe in found.items()},
                cross=cross, page_cache_same=w["dash_page_state"]==b["dash_page_state"],
                rope_same=w["page_rope"]==b["page_rope"],
                bf16_hidden=vector_deltas(w["hidden_states"], b["hidden_states"]),
                fp32_head={label: probe["fp32_head"]["processed"] for label, probe in [("b1", w), ("b2", b)]})


def audit(folder):
    decision = load(folder, "decision")
    controls = {k:load(folder,"g1-stock-"+k)["result"] for k in WINDOWS}
    output = dict(status=decision["status"], control={}, G1={}, G2={}, shapes={}, diagnostics=[])
    for key, value in controls.items():
        terminal = value["terminal_observation"]
        if value["eos_observed"]:
            assert terminal["nxt"] == value["eos_id"] and terminal["step"] == len(value["token_ids"])
        else:
            assert terminal["nxt"] != value["eos_id"] and terminal["step"] + 1 == len(value["token_ids"])
        output["control"][key] = dict(emitted=len(value["token_ids"]), eos=terminal["nxt"],
                                      pages=markers(value["token_ids"]), last_guard=terminal["guard"])
        raw = load(folder,"g1-wrapper-"+key)["result"]
        output["shapes"]["g1-"+key] = shape_check(raw, 1)
        output["G1"][key] = compare(value, raw["lanes"][0])
    eligible = output["control"]["long"]["emitted"] > output["control"]["short"]["emitted"]
    assert eligible == load(folder, "g1-lengths")["short_less_than_long"]
    pass1 = all(row["passes"] for row in output["G1"].values())
    assert pass1 == (decision["status"] != "g1-failed")
    if not pass1 or not eligible:
        assert decision["status"] == ("g1-ineligible-window-lengths" if pass1 else "g1-failed")
        assert not any(folder.glob("g2-*.json")) and not any(folder.glob("g3-*.json"))
        return output
    for order in (WINDOWS, WINDOWS[::-1]):
        name = "-".join(order)
        raw = load(folder,"g2-"+name)["result"]
        output["shapes"]["g2-"+name] = shape_check(raw, 2)
        output["G2"][name] = {}
        for slot, key in enumerate(order):
            row = compare(controls[key], raw["lanes"][slot])
            output["G2"][name][key] = row
            assert row["passes"] == load(folder, "g2")[name][key]["passed"]
            if row["first"] and None not in row["first"].values():
                output["diagnostics"].append(diagnose(folder, order, key, slot, row["first"], controls, raw))
    pass2 = all(row["passes"] for order in output["G2"].values() for row in order.values())
    if not pass2:
        assert decision["status"] == "g2-failed" and not any(folder.glob("g3-*.json"))
        receipt = load(folder, "diagnostic-fp32")
        output["fp32"] = receipt
        if receipt["status"] == "completed":
            spine = []
            for b in ("b1", "b2"):
                probe = load(folder,receipt["representative"]+"-fp32-"+b)["result"]["probe"]
                assert probe["hidden_dtype"] == probe["raw_head_dtype"] == "torch.float32"
                assert probe["processed"]["argmax"] == receipt[b+"_selected"]
                spine.append(probe)
            output["fp32"]["hidden_deltas"] = vector_deltas(*[row["hidden_states"] for row in spine])
            output["fp32"]["precision_scope"] = [row["precision_scope"] for row in spine]
        return output
    times = {}
    for name in ("warmup-native","warmup-batch","ab-native","ab-batch","ba-batch","ba-native"):
        filename = "g3-"+name
        record = load(folder,filename)
        order = WINDOWS[::-1] if name.startswith("ba-") else WINDOWS
        checks = [compare(controls[key], row)["passes"] for key, row in zip(order, record["result"]["lanes"], strict=True)]
        assert all(checks) == load(folder,filename+"-check")["passed"]
        times[name] = record["metrics"]
        if not all(checks):
            assert decision["status"] == "timing-parity-failed"
            output["partial_timing"] = times
            return output
    assert decision["status"] == "timing-completed"
    ratios = {r: times[r+"-native"]["wall_ns"] / times[r+"-batch"]["wall_ns"] for r in ("ab","ba")}
    assert ratios == decision["native_over_batch_speedup"]
    output["timed_arms"] = times
    output["speedup"] = ratios
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trial", type=Path)
    print(json.dumps(audit(parser.parse_args().trial), indent=2, allow_nan=False))
