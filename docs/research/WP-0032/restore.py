"""Restore lossless historical inputs and reproduce the original depth-zero write/read."""
import io
import json
from dataclasses import asdict
from hashlib import sha256

import matrix
import online
import torch

NAMES = ["Alder", "Cedar"]


def sha(data):
    return sha256(data).hexdigest()


def record_sha(value):
    return sha((json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode())


def raw(tensor):
    assert tensor.device.type == "cpu" and tensor.dtype in (torch.float32, torch.float64)
    return tensor.contiguous().numpy().tobytes()


def f32(data, shape):
    result = torch.frombuffer(bytearray(data), dtype=torch.float32).reshape(shape)
    assert result.isfinite().all() and raw(result) == data
    return result


def prepare(arm, archived, params, snapshot_blob):
    model = matrix.Memory(flat=arm == "M1").eval()
    model.load_state_dict(torch.load(io.BytesIO(params), map_location="cpu", weights_only=True), strict=True)
    assert {p.device.type for p in model.parameters()} == {"cpu"}
    assert archived["status"] == "completed" and archived["owner_order"] == NAMES
    live_anchors = model.anchors("owner", NAMES)
    sources = {}
    for owner in NAMES:
        src = archived["sources"][owner]
        snap = src["snapshot"]
        shape = (1 if arm == "M1" else 8, 128, 128)
        assert tuple(snap["shape"]) == shape and snap["dtype"] == "float32-le"
        if arm == "M1":
            data = snapshot_blob(snap["matrices_file"])
            assert sha(data) == snap["matrix_sha256"]
            matrices = f32(data, shape)
        else:
            matrices = torch.zeros(shape, dtype=torch.float32)
            assert all(torch.count_nonzero(lane).item() == 0 for lane in matrices)
        discrete = snap["discrete"]
        assert record_sha(discrete) == snap["discrete_sha256"]
        bundle = src["donor"]
        tensors = tuple(f32(bytes.fromhex(bundle["projected_f32le"][name]), shape)
                        for name, shape in (("key", (128,)), ("value", (128,)), ("alpha", ()), ("beta", ())))
        projection_sha = sha(b"".join(raw(t) for t in tensors))
        assert projection_sha == bundle["projection_sha256"] and record_sha(bundle) == src["donor_input_sha256"]
        assert bundle["owner"] == owner and bundle["events"] == [
            {"kind": "OPEN_LEDGER", "value": owner, "ptr": [1, 1, 7], "literal": "Ledger: " + owner}]
        query = f32(bytes.fromhex(src["frozen_query_f32le"]), (128,))
        anchors = f32(bytes.fromhex(src["ordered_anchors_f32le"]), (2, 128))
        assert raw(anchors) == raw(live_anchors)
        sources[owner] = dict(matrices=matrices, discrete=discrete, bundle=bundle, tensors=tensors, query=query, anchors=anchors)
    for key in ("query", "anchors"):
        assert raw(sources["Alder"][key]) == raw(sources["Cedar"][key])
    assert sources["Alder"]["discrete"] == sources["Cedar"]["discrete"]
    return model, sources


def controls(discrete, event):
    ctrl = online.Controller(**discrete["controller"])
    reg = discrete["registry"]
    registry = online.Registry(set(reg["owners"]), set(reg["units"]), set(tuple(s) for s in reg["schemas"]))
    event = online.Event(event["kind"], event["value"], tuple(event["ptr"]), event["literal"])
    ctrl.apply(event)
    registry.update(event)
    assert asdict(ctrl) == discrete["controller"] and ctrl.depth == 0 and ctrl.ambiguous() == ""
    assert reg == {k: sorted(list(x) if isinstance(x, tuple) else x for x in s) for k, s in vars(registry).items()}
    assert registry.choices()["owner"] == tuple(NAMES)
    return ctrl, registry


def native_read(arm, label, model, sources, archived, review, closure):
    empty = arm == "M3"
    cell = archived["empty_cells" if empty else "cells"][label]
    owner = "Cedar" if label[0] == "C" else "Alder"
    donor = "Alder" if label[1] == "A" else "Cedar"
    assert cell["recipient"] == ("zero" if empty else owner) and cell["control_registry_from"] == owner and cell["donor"] == donor
    recipient = sources[owner]
    tensors = sources[donor]["tensors"]
    bundle = sources[donor]["bundle"]
    discrete = recipient["discrete"]
    ctrl, registry = controls(discrete, bundle["events"][0])
    old = recipient["matrices"]
    identity = {"matrix_sha256": sha(raw(old)), "discrete_sha256": record_sha(discrete)}
    assert identity == cell["recipient_before_event"] == cell["after_donor_hook"]
    assert identity["matrix_sha256"] == review["recipient_matrix_sha256"]
    assert bundle["projection_sha256"] == review["donor_k_v_a_b_sha256"]
    assert record_sha(bundle) == cell["donor_input_sha256"]
    query, anchors = recipient["query"], recipient["anchors"]
    # The archived native call order preserves the GEMV, direction epsilon and two-row GEMV.
    new = model.write(tuple(old.unbind()), ctrl.depth, *tensors)
    vector = model.read(new, ctrl.depth, query, "owner")
    scores = anchors @ matrix.direction(vector)
    post = cell["read"]
    independent = review["post"]
    hashes = {"query_sha256": sha(raw(query)), "ordered_anchor_sha256": sha(raw(anchors)),
              "matrix_sha256": sha(raw(torch.stack(new))), "owner_columns_sha256": sha(raw(torch.stack(new)[:, :, :32])),
              "read_sha256": sha(raw(vector))}
    for key, digest in hashes.items():
        review_key = "anchor_sha256" if key == "ordered_anchor_sha256" else key
        assert digest == post[key] == independent[review_key], (arm, label, key)
    score_bytes = raw(scores).hex()
    assert len(score_bytes) == 16 and score_bytes == post["score_f32le"] == independent["score_f32le"] == closure["score_f32le"]
    assert raw(vector).hex() == post["read_f32le"] == independent["read_f32le"]
    assert record_sha(discrete) == post["discrete_sha256"] and {k: list(v) for k,v in registry.choices().items()} == post["registry"]
    assert post["owner_eligible"] and post["native_scope_clear"] and not post["top_score_pass"] and not post["top_gap_pass"]
    assert post["scores"] == closure["scores"] == dict(zip(NAMES, scores.tolist(), strict=True))
    assert scores[0].item() - scores[1].item() == post["margin"] == closure["margin"]
    assert sha(raw(old)) == identity["matrix_sha256"]
    bindings = {"recipient": cell["recipient"], "discrete_from": owner, "donor": donor, "discrete": discrete,
                "recipient_before": identity, "matrix_shape": list(old.shape), "literal": bundle["literal"], "bbox": bundle["bbox"],
                "donor_event": bundle["events"][0], "bundle_sha256": record_sha(bundle), "donor_projection_sha256": bundle["projection_sha256"],
                "projected_f32le": bundle["projected_f32le"], "query_f32le": raw(query).hex(), "ordered_anchor_f32le": raw(anchors).hex(),
                "recipient_lane_sha256": [sha(raw(lane)) for lane in old], "updated_lane_sha256": [sha(raw(lane)) for lane in new],
                "updated": hashes, "native_score_f32le": score_bytes, "archived_score_f32le": post["score_f32le"],
                "independent_archived_score_f32le": independent["score_f32le"], "closure_score_f32le": closure["score_f32le"]}
    return old[0], tensors, query, anchors, vector, scores, bindings
