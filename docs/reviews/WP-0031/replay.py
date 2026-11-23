"""Independent bounded WP-0031 replay. Run from the owned worktree with the frozen HEAD as argument."""
import copy
import datetime as dt
import io
import json
import math
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from archive import ACCESSED, NAMES, RESERVATION, ROOT, blob, read_archive, sha

RUNTIME = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0030/runtime/venv/Scripts/python.exe")
SCRATCH = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0031/review")


def normalized(obj):
    return json.loads(json.dumps(obj, allow_nan=False))


def f32(t):
    assert t.device.type == "cpu" and t.dtype == torch.float32
    return t.detach().contiguous().numpy().tobytes()


def matrix_bytes(state):
    return b"".join(f32(m) for m in state.matrices)


def controls(s):
    return {"controller": {"depth": s.controller.depth, "fault": s.controller.fault,
                           "held": list(s.controller.held), "ambiguous_reason": s.controller.ambiguous()},
            "registry": normalized(s.registry.choices()),
            "full_registry": {"owners": sorted(s.registry.owners), "units": sorted(s.registry.units),
                              "schemas": sorted(map(list, s.registry.schemas))}}


def identity(s):
    return {**controls(s), "matrix_sha256": sha(matrix_bytes(s))}


def clone(source):
    result = copy.deepcopy(source)
    result.matrices = tuple(t.clone() for t in source.matrices)
    assert result.controller is not source.controller and result.controller.held is not source.controller.held
    assert result.registry is not source.registry and all(
        getattr(result.registry, k) is not getattr(source.registry, k) for k in ("owners", "units", "schemas"))
    assert {t.data_ptr() for t in result.matrices}.isdisjoint(t.data_ptr() for t in source.matrices)
    assert identity(result) == identity(source)
    return result


def measured(model, state, query, anchors):
    vector = model.read(state.matrices, state.controller.depth, query, "owner")
    logits = anchors @ matrix.direction(vector)
    data = f32(logits)
    scores = dict(zip(NAMES, struct.unpack("<ff", data), strict=True))
    assert all(map(math.isfinite, scores.values()))
    margin = scores["Alder"] - scores["Cedar"]
    winner = "Alder" if margin > 0 else "Cedar" if margin < 0 else "tie"
    return {**identity(state), "scores": scores, "score_f32le": data.hex(), "margin": margin,
            "margin_f64le": struct.pack("<d", margin).hex(), "top": winner,
            "owner_eligible": state.registry.choices()["owner"] == NAMES,
            "native_scope_clear": state.controller.ambiguous() == "", "zero_read": vector.norm().item() <= matrix.EPS,
            "query_sha256": sha(f32(query)), "anchor_sha256": sha(f32(anchors)), "read_sha256": sha(f32(vector)),
            "read_f32le": f32(vector).hex(),
            "owner_columns_sha256": sha(b"".join(f32(t[:, :32]) for t in state.matrices))}


def archive_agreement(actual, historic):
    matched = {k: (list(actual["scores"].values()) if k == "scores" else actual[k]) == v for k,v in historic.items()}
    return matched


def apply_events(state, events):
    for e in events:
        assert e.kind not in ("CONFIRM_POP", "TARGET", "OPEN_CHILD")
        state.controller.apply(e)
        state.registry.update(e)


def prepare_prefix(model, probe, owner, window, meta, source_binding, trace):
    projected = model.project(window)
    assert len(window.spans) == len(projected[0]) == 16
    state = matrix.NeuralState(model.zero())
    details = []
    for i, span in enumerate(window.spans[:8]):
        assert i == span.index
        record = meta["spans"][i]
        original = trace[f"{probe}/12", i+1][owner]["source"]
        assert original == trace[f"{probe}/30", i+1][owner]["source"]
        events = list(online.identify(span, 1))
        event_data = [{"kind": e.kind, "value": normalized(e.value), "literal": e.literal} for e in events]
        assert event_data == original["events"] and all(e.ptr == (1, span.page, i) for e in events)
        source_row = {"ptr": [1, span.page, i], "text": span.text, "bbox": list(span.box),
                      "key": source_binding["rgb_key"], "feature_f32le_sha256": sha(f32(window.features[i])),
                      "metadata_sha256": sha(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()),
                      "events": event_data}
        assert all(original[k] == value for k,value in source_row.items())
        details.append(source_row)
        if i == 7:
            assert span.text == "Ledger: " + owner and (span.page,i) == (1,7)
            assert len(events) == 1 and events[0].kind == "OPEN_LEDGER" and events[0].value == owner
            assert list(span.box) == [53, 486 if owner == "Alder" else 487, 339, 515]
            break
        apply_events(state, events)
        assert state.registry.choices()["owner"] == (NAMES if i >= 2 else ())
        k, v, _, a, b = (t[i] for t in projected)
        state.matrices = model.write(state.matrices, state.controller.depth, k, v, a, b)
    return state, tuple(t[7] for t in projected), events, details


def algebra(cells):
    aa, ac, ca, cc = (cells[k]["post"]["margin"] for k in ("AA", "AC", "CA", "CC"))
    da, dc, pa, pc = aa-ac, ca-cc, aa-ca, ac-cc
    interaction, native = da-dc, aa-cc
    assert interaction == pa-pc and native == da+pc == pa+dc
    return {"DA": da, "DC": dc, "PA": pa, "PC": pc, "I": interaction, "delta_native": native}


def probe_replay(work, probe, weights, bindings, trace, anchor_history, sources, windows):
    model = matrix.Memory(flat=probe == "M1").eval()
    model.load_state_dict(torch.load(io.BytesIO(weights), map_location="cpu", weights_only=True), strict=True)
    assert all(p.device.type == "cpu" for p in model.parameters())
    target = windows["posting_query"]
    event, = online.identify(target.spans[3], 4)
    assert (event.kind, event.ptr, event.literal) == ("TARGET", (4,2,3), "Posting 241 851")
    live_query = model.project(target)[2][3]
    prefixes, donors, before, anchor_tensors, snapshots = {}, {}, {}, {}, {}
    rows, input_log, gates = {}, {}, {}
    for name in NAMES:
        meta = json.loads((work / name / "metadata.json").read_bytes())
        s, projection, events, details = prepare_prefix(model, probe, name, windows[name], meta,
                                                      sources["windows"][name], trace)
        rows[name] = details
        prefixes[name] = s
        k, v, q, a, b = projection
        donors[name] = (k, v, a, b, events)
        raw = {key: f32(t).hex() for key,t in zip(("k","v","q","a","b"), projection, strict=True)}
        inputs = b"".join(f32(t) for t in (k, v, a, b))
        input_log[name] = {"fields_f32le": raw, "tensor_sha256": {k: sha(bytes.fromhex(v)) for k,v in raw.items()},
                           "k_v_a_b_sha256": sha(inputs), "feature_sha256": details[-1]["feature_f32le_sha256"]}
        anchors = model.anchors("owner", s.registry.choices()["owner"])
        anchor_tensors[name] = anchors
        before[name] = measured(model, s, live_query, anchors)
        snapshots[name] = identity(s)
        (work / f"{probe}-{name}-write7.f32").write_bytes(matrix_bytes(s))
        gates[name] = {}
        for horizon in (12,30):
            assoc = bindings[f"{probe}/{horizon}"]
            r = trace[f"{probe}/{horizon}",7]
            gates[name][f"anchors{horizon}"] = anchor_history[probe] == assoc["anchor_sha256"] == sha(f32(anchors))
            gates[name][f"query{horizon}"] = (assoc[name]["query_f32le"] == f32(live_query).hex() and
                                              assoc[name]["query_sha256"] == sha(f32(live_query)))
            gates[name][f"write7_{horizon}"] = all(archive_agreement(before[name],r[name]["read"]).values())
    assert all(rows["Alder"][i]["feature_f32le_sha256"] != rows["Cedar"][i]["feature_f32le_sha256"] for i in range(8))
    assert all(rows["Alder"][i]["text"] == rows["Cedar"][i]["text"] for i in range(7))
    assert snapshots["Alder"]["matrix_sha256"] != snapshots["Cedar"]["matrix_sha256"]
    assert controls(prefixes["Alder"]) == controls(prefixes["Cedar"])
    cells = {}

    def execute(recipient, donor):
        # The empty control keeps the common literal registry and controller, while clearing all matrix lanes.
        before_all = {owner: identity(x) for owner,x in prefixes.items()}
        assert before_all == snapshots
        state = clone(prefixes["Alder" if recipient == "0" else recipient])
        if recipient == "0":
            state.matrices = tuple(torch.zeros_like(t) for t in state.matrices)
        state_id = identity(state)
        k,v,a,b,events = donors[donor]
        assert events[0].value == donor
        apply_events(state, events)
        assert identity(state) == state_id
        lane = 0 if model.flat else state.controller.depth
        old = state.matrices[lane]
        residual = v - a * (old @ k)
        state.matrices = model.write(state.matrices, state.controller.depth, k, v, a, b)
        # Compare to the actual frozen expression, including the leading decay and scalar-after-outer order.
        assert f32(state.matrices[lane]) == f32(a * old + b * torch.outer(residual, k))
        if recipient == "0":
            assert torch.equal(residual, v) and torch.equal(state.matrices[lane], b * torch.outer(v,k))
        after = measured(model, state, live_query, anchor_tensors["Alder" if recipient == "0" else recipient])
        assert {owner: identity(x) for owner,x in prefixes.items()} == before_all
        baseline = 0. if recipient == "0" else before[recipient]["margin"]
        return {"recipient": recipient, "donor": donor, "recipient_matrix_sha256": state_id["matrix_sha256"],
                "donor_k_v_a_b_sha256": input_log[donor]["k_v_a_b_sha256"], "event_literal": events[0].literal,
                "registry_controller_unchanged": controls(state) == {k:v for k,v in state_id.items() if k!="matrix_sha256"},
                "source_snapshot_sha256_before_and_after": {n:s["matrix_sha256"] for n,s in before_all.items()},
                "residual_sha256": sha(f32(residual)), "post": after, "row_baseline": baseline,
                "increment": after["margin"] - baseline}

    for name in NAMES:
        cell = execute(name, name)
        cells[name[0]*2] = cell
        for horizon in (12,30):
            gated = archive_agreement(cell["post"],trace[f"{probe}/{horizon}",8][name]["read"])
            gates[name][f"write8_{horizon}"] = all(gated.values())
            if not all(gated.values()):
                gates[name]["failed_fields"] = [k for k,v in gated.items() if not v]
        if probe == "M3":
            gates[name]["rank"] = cell["post"]["top"] == ("Cedar" if name == "Alder" else "Alder")
    shared = all(cells["AA"]["post"][k] == cells["CC"]["post"][k] for k in ("query_sha256","anchor_sha256"))
    success = shared and all(all(checks.values()) for checks in gates.values())
    result = {"native_gate": success, "shared_query_anchor": shared, "checks": gates, "write7": before,
              "donor": input_log, "rows": rows, "cells": cells, "contrasts": None, "zero": None}
    if not success:
        cells.update(AC=None, CA=None)
        return result
    cells["AC"] = execute("Alder", "Cedar")
    cells["CA"] = execute("Cedar", "Alder")
    contrasts = algebra(cells)
    result["contrasts"] = contrasts
    da, dc, i = (contrasts[k] for k in ("DA","DC","I"))
    limit = .05 * max(abs(da),abs(dc))
    trigger = da < 0 and dc < 0 and abs(i) <= limit
    result["zero"] = {"DA": da, "DC": dc, "abs_I": abs(i), "limit": limit, "trigger": trigger, "D0": None}
    if trigger:
        for name in NAMES:
            cells["0"+name[0]] = execute("0", name)
        result["zero"]["D0"] = cells["0A"]["post"]["margin"] - cells["0C"]["post"]["margin"]
    return result


def main(candidate):
    global torch, matrix, online
    assert sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize
    assert Path.cwd().resolve() == ROOT and Path(sys.executable).resolve() == RUNTIME and sys.byteorder == "little"
    assert sha(RUNTIME.read_bytes()) == "0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14"
    assert subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip() == candidate
    for name in ("replay.py","archive.py"):
        path = Path(__file__).with_name(name)
        assert path.read_bytes().replace(b"\r\n",b"\n") == blob(candidate,path.relative_to(ROOT).as_posix())
    work = SCRATCH / candidate
    work.mkdir(parents=True, exist_ok=False)
    for key in ("TMP","TEMP","TORCH_HOME","HF_HOME","XDG_CACHE_HOME","TORCHINDUCTOR_CACHE_DIR"):
        path = work / key
        path.mkdir()
        os.environ[key] = str(path)
    os.environ.update(CUDA_VISIBLE_DEVICES="-1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                      OPENBLAS_NUM_THREADS="1", PIP_NO_INDEX="1", HF_HUB_OFFLINE="1")
    start = time.perf_counter()
    weights, bindings, trace, anchors, sources = read_archive(work)
    sys.path.insert(0,str(work))
    import torch, matrix, online, numpy
    assert platform.python_version() == "3.12.10" and str(torch.__version__) == "2.13.0+cpu"
    assert numpy.__version__ == "2.2.6" and torch.version.cuda is None
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.default_generator.manual_seed(2401)
    assert torch.get_num_threads() == torch.get_num_interop_threads() == 1
    windows = {name: online.load_window(work / name) for name in sources["windows"]}
    with torch.inference_mode():
        probes = {p:probe_replay(work,p,w,bindings,trace,anchors,sources,windows) for p,w in weights.items()}
    result = {"base": RESERVATION, "candidate": candidate, "argv": sys.orig_argv, "platform": platform.platform(),
              "torch": str(torch.__version__), "numpy": numpy.__version__, "python": sys.version,
              "python_sha256": sha(RUNTIME.read_bytes()), "threads": [torch.get_num_threads(),torch.get_num_interop_threads()],
              "cuda_build": torch.version.cuda, "deterministic": torch.are_deterministic_algorithms_enabled(),
              "blobs_sha256": ACCESSED, "sources": sources, "probes": probes, "wall_seconds": time.perf_counter()-start,
              "finished_utc": dt.datetime.now(dt.UTC).isoformat()}
    (work / "replay.json").write_bytes((json.dumps(result, indent=2, allow_nan=False)+"\n").encode())
    for p,r in probes.items():
        print(p, r["native_gate"], r["contrasts"], r["zero"])


if __name__ == "__main__":
    main(*sys.argv[1:])
