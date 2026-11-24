"""Authenticate both full windows and reconstruct the write-seven states and original controls."""
import copy
import io
from dataclasses import asdict, replace

import experiment as history
import matrix
import online
import torch

from metrics import CELLS, OWNERS, digest, observe, pack, raw


def verify_arm(arm, work, weights, thresholds, captures, steps, bindings, archive, prior, snapshot):
    cuts = thresholds[arm]
    assert cuts == archive["thresholds"] == [1.0, 0.1]
    model = matrix.Memory(flat=arm == "M1").eval()
    model.load_state_dict(torch.load(io.BytesIO(weights[arm]), map_location="cpu", weights_only=True), strict=True)
    assert all(p.device.type == "cpu" for p in model.parameters())
    anchors = model.anchors("owner", OWNERS)
    windows, sources, manifest = {}, {}, {}
    for owner in OWNERS:
        window = online.load_window(work / owner)
        assert window.features.shape == (16, 1280) and len(window.spans) == 16
        pooled = raw(window.features)
        capture = captures[owner]
        assert digest(pooled) == capture["members"]["pooled.f32"]
        for n in (7, 8):
            cut12, cut30 = (steps[f"{arm}/{h}"][n] for h in (12, 30))
            assert {k:v for k,v in cut12.items() if k != "run"} == {k:v for k,v in cut30.items() if k != "run"}
        state, (events, tensors, donor, donor_sha), trajectory = history.prepare_prefix(
            model, window, capture["rgb_key"], steps[f"{arm}/12"], owner)
        src = archive["sources"][owner]
        snap = src["snapshot"]
        assert history.json_bytes(trajectory) == history.json_bytes(src["prefix_writes"])
        assert history.json_bytes(donor) == history.json_bytes(src["donor"])
        assert history.identity(state) == {k:snap[k] for k in ("matrix_sha256", "discrete_sha256")}
        assert history.matrix_bytes(state) == snapshot(snap["matrices_file"])
        assert list(torch.stack(state.matrices).shape) == snap["shape"] == [1 if arm == "M1" else 8, 128, 128]
        assert history.json_bytes(history.discrete(state)) == history.json_bytes(snap["discrete"])
        assert raw(anchors).hex() == src["ordered_anchors_f32le"] and donor_sha == src["donor_input_sha256"]
        q = torch.frombuffer(bytearray.fromhex(src["frozen_query_f32le"]), dtype=torch.float32)
        assert q.shape == (128,) and state.registry.choices()["owner"] == OWNERS
        for h in (12, 30):
            b = bindings[f"{arm}/{h}"]
            assert b[owner]["query_f32le"] == raw(q).hex() and b["anchor_sha256"] == digest(raw(anchors))
            assert b[owner]["keys"][0] == capture["rgb_key"] and b[owner]["binder"] == capture["binders"][h]
        windows[owner[0]] = window
        sources[owner[0]] = dict(state=state, tensors=tensors, events=events, query=q)
        manifest[owner] = dict(capture=capture, donor=donor, matrices_blob=snap["matrices_file"],
                               snapshot=snap, write7_trajectory=trajectory, anchor=pack(anchors), eventual_query=pack(q),
                               full_pooled_sha256=digest(pooled), all_rows_sha256=[digest(raw(f)) for f in window.features],
                               all_metadata_sha256=digest(history.json_bytes([asdict(s) for s in window.spans])))
    assert raw(sources["A"]["query"]) == raw(sources["C"]["query"])
    assert history.discrete(sources["A"]["state"]) == history.discrete(sources["C"]["state"])
    controls = {}
    for label in (CELLS if arm == "M1" else ("0A", "0C")):
        prefix = label[0] if arm == "M1" else "A"
        donor = label[1]
        state, bindings_at_write = opened(sources[prefix], sources[donor]["events"], arm == "M3")
        state.matrices = model.write(state.matrices, 0, *sources[donor]["tensors"])
        native, _, _ = observe(model, state, sources[prefix]["query"], anchors, cuts)
        ref = archive["cells" if arm == "M1" else "empty_cells"][label]["read"]
        assert all(native[k] == v for k,v in ref.items()), (arm,label,"original primitive parity")
        p = prior["cells"][label]["binding"]
        assert native["score_f32le"] == p["native_score_f32le"] == p["independent_archived_score_f32le"]
        for k in ("read_sha256","matrix_sha256","ordered_anchor_sha256","query_sha256","owner_columns_sha256"):
            assert native[k] == p["updated"][k]
        controls[label] = dict(native=native, at_declaration=bindings_at_write, historical_score_f32le=p["native_score_f32le"])
    return model, sources, windows, anchors, manifest, controls


def opened(src, events, empty):
    original = src["state"]
    state = copy.deepcopy(original)
    assert all(a.data_ptr() != b.data_ptr() for a,b in zip(original.matrices, state.matrices, strict=True))
    before = history.identity(state)
    assert before == history.identity(original)
    if empty:
        state.matrices = tuple(torch.zeros_like(x) for x in state.matrices)
        assert len(state.matrices) == 8 and not torch.stack(state.matrices).count_nonzero().item()
    before_event = history.identity(state)
    assert len(events) == 1 and events[0].kind == "OPEN_LEDGER" and events[0].ptr == (1,1,7)
    history.hook(state, events[0])
    after_event = history.identity(state)
    assert before_event == after_event and state.controller.depth == 0 and state.registry.choices()["owner"] == OWNERS
    return state, {"original":before, "before_event":before_event, "after_event":after_event,
                   "event":asdict(events[0]), "depth":0, "registered":OWNERS}


def hybrid_window(windows, label):
    pool, box = (windows[i] for i in label)
    old_span = pool.spans[7]
    replacement = replace(old_span, box=box.spans[7].box)
    window = replace(pool, spans=pool.spans[:7]+(replacement,)+pool.spans[8:])
    assert window.features is pool.features and len(window.spans) == 16
    assert replace(window.spans[7], box=old_span.box) == old_span
    assert all(x is y for i,(x,y) in enumerate(zip(window.spans,pool.spans,strict=True)) if i != 7)
    assert window.spans[7].box == (53,486 if label[1]=="A" else 487,339,515)
    native = matrix.blocks(pool.spans, pool.features)
    blocks = matrix.blocks(window.spans, window.features)
    assert raw(blocks[:,:1280]) == raw(native[:,:1280]) == raw(pool.features)
    assert raw(blocks[:7]) == raw(native[:7]) and raw(blocks[8:]) == raw(native[8:])
    assert raw(blocks[7,1280:]) == raw(matrix.blocks(box.spans,box.features)[7,1280:])
    return window, blocks
