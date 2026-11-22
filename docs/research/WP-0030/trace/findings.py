"""Align the independently replayed members before computing signed pair statistics."""
import struct

from inputs30 import NAMES, check


def sign(value):
    return int(value > 0) - int(value < 0)


def align(a, c):
    left, right = a["source"], c["source"]
    if left is None or right is None:
        check(left is right is None and a["phase"] == "zero", "null source outside initial state")
        return None
    for key in ("pointer", "window_index", "absolute_page", "kind", "block_kind"):
        check(left[key] == right[key], "unaligned source " + key)
    roles = lambda s: [e["kind"] for e in s["events"]]
    check(roles(left) == roles(right), "unaligned parser event roles")
    control_structure = lambda r: [(e["event"], e["ptr"], e["depth_after"], e["shadow_hold"])
                                   for e in r["control_events"]]
    # Pop rank depends on neural content. Report it independently of alignment.
    check(control_structure(a) == control_structure(c), "control ordering")
    check(a["controller"] == c["controller"] and a["registry"] == c["registry"], "twin control structure")
    fields = ("rgb_key", "literal", "cells", "events", "metadata_sha256", "feature_sha256",
              "raw_span_sha256", "selected_token_ids_u32le_sha256")
    differences = [k for k in fields if left[k] != right[k]]
    if left["rgb_key"] == right["rgb_key"]:
        check(not differences, "different row in a shared triple")
    return {"pointer": left["pointer"], "ordered_roles": roles(left), "different_fields": differences}


def pair_rows(rows):
    check(set(rows) == set(NAMES), "expected one independent member per owner")
    result = []
    for i, (a, c) in enumerate(zip(rows["Alder"], rows["Cedar"], strict=True)):
        for key in ("phase", "step_index", "checkpoints", "query_sha256"):
            check(a[key] == c[key], "pair alignment " + key)
        alignment = align(a, c)
        delta = a["margin"] - c["margin"]
        win = a["margin"] > 0 > c["margin"]
        check(win == (a["top_owner"] == "Alder" and c["top_owner"] == "Cedar"), "strict rank equivalence")
        result.append({"observation_index": i, "phase": a["phase"], "step_index": a["step_index"],
                       "checkpoints": a["checkpoints"], "alignment": alignment, "members": dict(zip(NAMES, (a, c))),
                       "delta": delta, "delta_f64le_hex": struct.pack("<d", delta).hex(), "sign": sign(delta),
                       "paired_win": win, "both_owner_eligible": a["owner_eligible"] and c["owner_eligible"]})
    writes = [r["step_index"] for r in result if r["phase"] == "post_write"]
    check(writes == list(range(1, len(writes)+1)) and result[-2]["phase"] == "native_pre_target" and
          result[-2]["step_index"] == result[-1]["step_index"]-1, "noncontinuous write indexing")
    return result


def point(row):
    source = row["members"]["Alder"]["source"]
    return {"observation_index": row["observation_index"], "phase": row["phase"], "step_index": row["step_index"],
            "pointer": source["pointer"] if source else None, "absolute_page": source["absolute_page"] if source else None,
            "kind": source["kind"] if source else None, "block_kind": source["block_kind"] if source else None,
            "ordered_roles": row["alignment"]["ordered_roles"] if source else [],
            "literals": {n: row["members"][n]["source"]["literal"] for n in NAMES} if source else None,
            "delta": row["delta"], "delta_f64le_hex": row["delta_f64le_hex"], "paired_win": row["paired_win"]}


def summarize(rows):
    owner, = [r for r in rows if "t1" in r["checkpoints"]]
    owner_index = owner["observation_index"]
    first = after_owner = None
    flags = {"sign_transitions": [], "sign_reversals": [], "absolute_attenuation": [],
             "positive_response_decreases": []}
    for prev, current in zip(rows, rows[1:]):
        before, now = prev["delta"], current["delta"]
        change = {"previous": point(prev), "current": point(current)}
        if current["phase"] == "post_write" and now > 0:
            if first is None:
                first = change
            if after_owner is None and current["observation_index"] > owner_index:
                after_owner = change
        tests = {"sign_transitions": sign(before) != sign(now), "sign_reversals": before * now < 0,
                 "absolute_attenuation": abs(now) < abs(before),
                 "positive_response_decreases": before > 0 and now < before}
        for key, present in tests.items():
            if present:
                flags[key].append(change)
    writes = [r for r in rows if r["phase"] == "post_write"]
    return {"observations": len(rows), "writes": len(writes), "owner_write": point(owner),
            "first_favorable_from_zero": first, "first_favorable_after_owner_write": after_owner,
            "zero_response": [point(r) for r in rows if r["delta"] == 0],
            "paired_wins": [point(r) for r in rows if r["paired_win"]],
            "eligible_paired_wins": [point(r) for r in rows if r["paired_win"] and r["both_owner_eligible"]],
            "before_owner_write": [point(r) for r in writes if r["observation_index"] < owner_index],
            "native_posting": point(rows[-2]), "post_target_write": point(rows[-1]),
            "source_difference_steps": {k: [r["step_index"] for r in writes if k in r["alignment"]["different_fields"]]
                       for k in ("rgb_key", "literal", "cells", "events", "metadata_sha256", "feature_sha256",
                                 "raw_span_sha256", "selected_token_ids_u32le_sha256")}, **flags}
