"""Bounded replay using the exact immutable memory, event and parser modules staged by inputs."""
import copy
import io
import json
import struct
from dataclasses import asdict
from hashlib import sha256

import matrix
import online
import torch

NAMES = ("Alder", "Cedar")


def digest(data):
    return sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def raw(tensor):
    assert tensor.device.type == "cpu" and tensor.dtype == torch.float32
    return tensor.contiguous().numpy().astype("<f4", copy=False).tobytes()


def matrix_bytes(state):
    return raw(torch.stack(state.matrices))


def discrete(state):
    return {"controller": asdict(state.controller),
            "registry": {name: sorted(items) for name, items in vars(state.registry).items()},
            "attempts": state.attempts.copy(), "trace": copy.deepcopy(state.trace),
            "growth": state.growth.copy(), "lookup_ns": state.lookup_ns}


def identity(state):
    return {"matrix_sha256": digest(matrix_bytes(state)), "discrete_sha256": digest(json_bytes(discrete(state)))}


def read(model, state, query, anchors, thresholds):
    vector = model.read(state.matrices, state.controller.depth, query, "owner")
    logits = anchors @ matrix.direction(vector)
    data = raw(logits)
    # Unpacking each binary32 to a Python binary64 preserves its exact value.
    scores = dict(zip(NAMES, struct.unpack("<2f", data), strict=True))
    margin = scores["Alder"] - scores["Cedar"]
    choices = {k: list(v) for k, v in state.registry.choices().items()}
    descending = logits.sort(descending=True).values
    return {"scores": scores, "score_f32le": data.hex(), "margin": margin,
            "margin_f64le": struct.pack("<d", margin).hex(),
            "top": "Alder" if margin > 0 else "Cedar" if margin < 0 else "tie",
            "controller": {**asdict(state.controller), "ambiguous_reason": state.controller.ambiguous()},
            "registry": choices, "owner_eligible": choices["owner"] == list(NAMES),
            "native_scope_clear": state.controller.ambiguous() == "", "zero_read": vector.norm().item() <= matrix.EPS,
            "top_score_pass": bool(descending[0] >= thresholds[0]),
            "top_gap_pass": bool(descending[0] - descending[1] >= thresholds[1]),
            "query_sha256": digest(raw(query)), "ordered_anchor_sha256": digest(raw(anchors)),
            "read_sha256": digest(raw(vector)), "read_f32le": raw(vector).hex(), **identity(state),
            "owner_columns_sha256": digest(raw(torch.stack(state.matrices)[:, :, :32]))}


def parity(observed, archived):
    """Compare every archived read field, explicitly translating the archive's fixed literal order."""
    return {key: ([observed[key][name] for name in NAMES] if key == "scores" else observed[key]) == value
            for key, value in archived.items()}


def hook(state, event):
    # Only directory events and OPEN_LEDGER are admitted before this cut, so no pop/target can be skipped.
    assert event.kind in {"DIRECTORY_SCHEMA", "DIRECTORY_UNITS", "DIRECTORY_OWNERS", "OPEN_LEDGER"}
    state.controller.apply(event)
    state.registry.update(event)


def prepare_prefix(model, window, key, rows, owner):
    keys, values, _, alphas, betas = model.project(window)
    state = matrix.NeuralState(model.zero())
    trajectory = []
    for idx in range(8):
        span = window.spans[idx]
        events = list(online.identify(span, 1))
        row = rows[idx + 1][owner]["source"]
        event_records = [asdict(e) for e in events]
        archive_events = [{k: v for k, v in e.items() if k != "ptr"} for e in event_records]
        feature = digest(raw(window.features[idx]))
        assert row["ptr"] == [1, span.page, idx] and span.index == idx
        assert row["text"] == span.text and row["bbox"] == list(span.box) and row["key"] == key
        assert row["feature_f32le_sha256"] == feature and json_bytes(row["events"]) == json_bytes(archive_events)
        if idx == 7:
            assert len(events) == 1 and events[0] == online.Event("OPEN_LEDGER", owner, (1, 1, 7), "Ledger: " + owner)
            assert span.box == (53, 486 if owner == "Alder" else 487, 339, 515)
            tensors = (keys[idx], values[idx], alphas[idx], betas[idx])
            values_by_name = dict(zip(("key", "value", "alpha", "beta"), tensors, strict=True))
            donor = {"owner": owner, "full_window_shape": list(window.features.shape), "pointer": row["ptr"],
                     "window_rgb_key": key, "bbox": span.box, "literal": span.text, "events": event_records,
                     "feature_sha256": feature, "projected_f32le": {k: raw(v).hex() for k, v in values_by_name.items()},
                     "projection_sha256": digest(b"".join(raw(v) for v in tensors))}
            # Include source binding and event list in the donor digest, separately retaining the numeric-only digest.
            return state, (events, tensors, donor, digest(json_bytes(donor))), trajectory
        before = sorted(state.registry.owners)
        for event in events:
            hook(state, event)
        if idx == 2:
            assert before == [] and sorted(state.registry.owners) == list(NAMES)
            assert [e.kind for e in events] == ["DIRECTORY_OWNERS"]
        state.matrices = model.write(state.matrices, state.controller.depth, keys[idx], values[idx], alphas[idx], betas[idx])
        trajectory.append({"write": idx + 1, "feature_sha256": feature, "events": event_records,
                           "owners_before": before, "owners_after": sorted(state.registry.owners),
                           "matrix_sha256": digest(matrix_bytes(state))})


def cell(model, row, donor, snapshots, donors, queries, anchors, thresholds, empty=False):
    before = {name: identity(state) for name, state in snapshots.items()}
    source = snapshots[row]
    state = copy.deepcopy(source)
    assert state.controller is not source.controller and state.controller.held is not source.controller.held
    assert state.registry is not source.registry
    assert all(items is not vars(source.registry)[k] for k, items in vars(state.registry).items())
    assert all(t.data_ptr() != src.data_ptr() for t, src in zip(state.matrices, source.matrices, strict=True))
    assert identity(state) == before[row]
    if empty:
        state.matrices = tuple(torch.zeros_like(t) for t in state.matrices)
    recipient = identity(state)
    events, tensors, bundle, donor_digest = donors[donor]
    assert len(events) == 1 and events[0].value == donor and bundle["owner"] == donor
    for event in events:
        hook(state, event)
    after_hook = identity(state)
    assert after_hook == recipient
    k, v, a, b = tensors
    old = state.matrices[0 if model.flat else state.controller.depth]
    residual = v - a * (old @ k)
    # Use the frozen algebra, including its alpha-scaled old matrix and FP32 operation order.
    state.matrices = model.write(state.matrices, state.controller.depth, k, v, a, b)
    observed = read(model, state, queries[row], anchors[row], thresholds)
    after = {name: identity(s) for name, s in snapshots.items()}
    assert before == after and digest(json_bytes(bundle)) == donor_digest
    return {"recipient": "zero" if empty else row, "control_registry_from": row, "donor": donor,
            "source_states_before": before, "source_states_after": after, "recipient_before_event": recipient,
            "donor_input_sha256": donor_digest, "after_donor_hook": after_hook, "fresh_residual_sha256": digest(raw(residual)),
            "read": observed}


def run_arm(arm, weights, cuts, expected_anchor, bindings, steps, captures, work, evidence, write):
    model = matrix.Memory(flat=arm == "M1").eval()
    model.load_state_dict(torch.load(io.BytesIO(weights), map_location="cpu", weights_only=True), strict=True)
    assert {p.device.type for p in model.parameters()} == {"cpu"}
    snapshots, donors, queries, anchors = {}, {}, {}, {}
    result = {"thresholds": cuts, "owner_order": NAMES, "sources": {}, "gates": {}, "cells": {},
              "contrasts": None, "trigger": None, "empty_cells": None}
    gate = result["gates"]
    rows, repeated = (steps[f"{arm}/{h}"] for h in (12, 30))
    # Single replay only. Hash the second horizon's archived cuts with their run label removed.
    for idx in (7, 8):
        strip_run = lambda r: {k: v for k, v in r.items() if k != "run"}
        h12, h30 = (digest(json_bytes(strip_run(r[idx]))) for r in (rows, repeated))
        gate[f"step_{idx}_12_30"] = {"pass": h12 == h30, "12_sha256": h12, "30_sha256": h30}

    for owner in NAMES:
        window = online.load_window(work / owner)
        state, donor, trajectory = prepare_prefix(model, window, captures[owner]["rgb_key"], rows, owner)
        snapshots[owner], donors[owner] = state, donor
        mat = matrix_bytes(state)
        snapshot_name = f"{arm}-{owner}-write7.f32"
        write(evidence / snapshot_name, mat)
        archive_runs = {}
        for horizon in (12, 30):
            run = f"{arm}/{horizon}"
            b = bindings[run]
            assert b[owner]["binder"] == captures[owner]["binders"][horizon]
            assert b[owner]["keys"][0] == captures[owner]["rgb_key"]
            archive_runs[run] = {"query_sha256": b[owner]["query_sha256"], "ordered_anchor_sha256": b["anchor_sha256"]}
        b = bindings[f"{arm}/12"][owner]
        # Restore each original's archived eventual query verbatim. No later window or posting executes.
        query_data = bytes.fromhex(b["query_f32le"])
        query = torch.frombuffer(bytearray(query_data), dtype=torch.float32)
        assert tuple(query.shape) == (128,)
        anchor = model.anchors("owner", NAMES)
        queries[owner], anchors[owner] = query, anchor
        native7 = read(model, state, query, anchor, cuts)
        cols = parity(native7, rows[7][owner]["read"])
        gate[f"{owner}_write7"] = {"pass": all(cols.values()), "fields": cols}
        for horizon in (12, 30):
            run = f"{arm}/{horizon}"
            ref = archive_runs[run]
            gate[f"{owner}_{run}_query_anchors"] = {"pass": (
                bytes.fromhex(bindings[run][owner]["query_f32le"]) == raw(query)
                and ref["query_sha256"] == native7["query_sha256"] == steps[run][8][owner]["read"]["query_sha256"]
                and ref["ordered_anchor_sha256"] == native7["ordered_anchor_sha256"] == expected_anchor),
                "archive": ref, "live": {"query_sha256": native7["query_sha256"],
                                         "ordered_anchor_sha256": native7["ordered_anchor_sha256"]}}
        result["sources"][owner] = {"prefix_writes": trajectory, "snapshot": {"matrices_file": snapshot_name,
            "shape": list(torch.stack(state.matrices).shape), "dtype": "float32-le", "discrete": discrete(state),
            **identity(state)}, "frozen_query_f32le": query_data.hex(), "ordered_anchors_f32le": raw(anchor).hex(),
            "donor": donor[2], "donor_input_sha256": donor[3], "write7_read": native7}
    gate["twins_live_query_anchors"] = {"pass": raw(queries["Alder"]) == raw(queries["Cedar"])
                                         and raw(anchors["Alder"]) == raw(anchors["Cedar"])}
    source = result["sources"]
    gate["independent_prefixes_distinct_features"] = {"pass": (
        identity(snapshots["Alder"])["matrix_sha256"] != identity(snapshots["Cedar"])["matrix_sha256"]
        and all(a["feature_sha256"] != c["feature_sha256"] for a, c in
                zip(source["Alder"]["prefix_writes"], source["Cedar"]["prefix_writes"], strict=True))
        and donors["Alder"][2]["feature_sha256"] != donors["Cedar"][2]["feature_sha256"])}

    def measure(row, col, empty=False):
        measured = cell(model, row, col, snapshots, donors, queries, anchors, cuts, empty)
        start = 0.0 if empty else source[row]["write7_read"]["margin"]
        measured["baseline_margin"] = start
        measured["increment"] = measured["read"]["margin"] - start
        return measured

    cells = result["cells"]
    for owner in NAMES:
        label = owner[0] * 2
        cells[label] = measure(owner, owner)
        fields = parity(cells[label]["read"], rows[8][owner]["read"])
        gate[label] = {"pass": all(fields.values()), "fields": fields}
    gate["native_diagonal_query_and_anchor"] = {"pass": all(
        cells["AA"]["read"][field] == cells["CC"]["read"][field]
        for field in ("query_sha256", "ordered_anchor_sha256"))}
    if arm == "M3":
        gate["M3_diagonal_orientation"] = {"pass": cells["AA"]["read"]["top"] == "Cedar"
                                           and cells["CC"]["read"]["top"] == "Alder"}
    if not all(g["pass"] for g in gate.values()):
        cells.update(AC=None, CA=None)
        result["status"] = "blocked"
        return result
    cells["AC"], cells["CA"] = measure("Alder", "Cedar"), measure("Cedar", "Alder")
    aa, ac, ca, cc = (cells[k]["read"]["margin"] for k in ("AA", "AC", "CA", "CC"))
    da, dc, pa, pc = aa - ac, ca - cc, aa - ca, ac - cc
    interaction, delta = da - dc, aa - cc
    assert interaction == pa - pc and delta == da + pc == pa + dc == rows[8]["delta"]
    assert da == cells["AA"]["increment"] - cells["AC"]["increment"]
    assert dc == cells["CA"]["increment"] - cells["CC"]["increment"]
    result["contrasts"] = dict(DA=da, DC=dc, PA=pa, PC=pc, I=interaction, delta_native=delta)
    result["contrasts_f64le"] = {name: struct.pack("<d", value).hex() for name, value in result["contrasts"].items()}
    limit = 0.05 * max(abs(da), abs(dc))
    triggered = da < 0 and dc < 0 and abs(interaction) <= limit
    result["trigger"] = {"DA": da, "DC": dc, "abs_I": abs(interaction), "five_percent_limit": limit, "run": triggered}
    if triggered:
        # Preserve the shared eligible discrete state and clear every matrix lane before the donor event.
        assert discrete(snapshots["Alder"]) == discrete(snapshots["Cedar"])
        za, zc = measure("Alder", "Alder", True), measure("Alder", "Cedar", True)
        result["empty_cells"] = {"0A": za, "0C": zc, "D0": za["read"]["margin"] - zc["read"]["margin"]}
    result["status"] = "completed"
    return result
