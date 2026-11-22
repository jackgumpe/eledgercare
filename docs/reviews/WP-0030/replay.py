"""Full, independently implemented observer over the frozen public transition primitives."""
import datetime
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import struct
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inputs import BASE, NAMES, RECEIPTS, ROOT, blob, encoded, prepare, sha, write

SCRATCH = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0030")
RUNTIME = SCRATCH / "runtime/venv/Scripts/python.exe"


def raw(tensor):
    assert tensor.device.type == "cpu" and tensor.dtype == torch.float32
    return tensor.contiguous().numpy().astype("<f4", copy=False).tobytes()


def f64(value):
    assert math.isfinite(value)
    return struct.pack("<d", value).hex()


def pack(value):
    return json.loads(json.dumps(value, allow_nan=False))


def controller(state):
    c = state.controller
    return {"depth": c.depth, "held": list(c.held), "fault": c.fault, "ambiguous_reason": c.ambiguous()}


def read(model, query, anchors, state):
    vec = model.read(state.matrices, state.controller.depth, query, "owner")
    logits = anchors @ matrix.direction(vec)
    scores = logits.tolist()
    assert len(scores) == 2 and all(map(math.isfinite, scores))
    margin = scores[0] - scores[1]
    ranking = "Alder" if margin > 0 else "Cedar" if margin < 0 else "tie"
    data = raw(logits)
    assert struct.pack("<ff", *scores) == data
    matrices = torch.stack(state.matrices)
    return {"controller": controller(state), "registry": pack(state.registry.choices()),
            "owner_eligible": state.registry.choices()["owner"] == NAMES,
            "native_scope_clear": state.controller.ambiguous() == "",
            "matrix_sha256": sha(raw(matrices)), "owner_columns_sha256": sha(raw(matrices[:, :, :32])),
            "read_sha256": sha(raw(vec)), "query_sha256": sha(raw(query)),
            "zero_read": float(vec.norm()) <= matrix.EPS, "scores": scores, "score_f32le": data.hex(),
            "margin": margin, "margin_f64le": f64(margin), "top": ranking}


def source_of(catalog, key, ordinal, span, events):
    item = catalog["captures"][key]["spans"][span.index]
    record = item["raw_record"]
    assert (record["index"], record["page"], record["text"], record["kind"], record["block_kind"]) == (
        span.index, span.page, span.text, span.kind, span.block_kind)
    assert tuple(record["bbox999"]) == span.box
    clean_cells = tuple(online.clean(x if isinstance(x, str) else x["text"]) for x in record["cells"])
    assert span.cells == clean_cells
    return {"ptr": [ordinal, span.page, span.index], "page": 3*(ordinal-1) + span.page, "key": key,
            "text": span.text, "cells": list(span.cells), "kind": span.kind, "block": span.block_kind,
            "bbox": list(span.box), "metadata_sha256": item["metadata_sha256"], "text_sha256": item["text_sha256"],
            "raw_slice_sha256": item["raw_slice_sha256"], "feature_f32le_sha256": item["feature_f32le_sha256"],
            "events": [{"kind": e.kind, "literal": e.literal, "value": pack(e.value)} for e in events]}


def verify_boundary(row, cp, state, query, model, native=None):
    obs = row["read"]
    assert row["source"]["ptr"] == cp["pointer"] and cp["controller"] == obs["controller"]
    assert cp["candidate_order"] == list(NAMES) and obs["owner_eligible"]
    assert all(obs[k] == cp[k] for k in ("query_sha256", "matrix_sha256", "read_sha256", "owner_columns_sha256",
                                         "zero_read"))
    assert bytes.fromhex(obs["score_f32le"]) == struct.pack("<ff", *(cp["scores"][o] for o in NAMES))
    assert sha(bytes.fromhex(obs["score_f32le"])) == cp["score_bytes_f32le_sha256"]
    assert (obs["top"] == "tie") == cp["exact_top_tie"]
    desc = torch.tensor(obs["scores"], dtype=torch.float32).sort(descending=True).values
    assert bool(desc[0] >= 1.0) == cp["top_score_pass"] and bool(desc[0] - desc[1] >= 0.1) == cp["top_gap_pass"]
    for field, old in cp["unit_column_controls"].items():
        literals = state.registry.choices()[field]
        assert old is not None and set(literals) == set(old)
        read_vec = model.read(state.matrices, state.controller.depth, query, field)
        scored = model.anchors(field, literals) @ matrix.direction(read_vec)
        assert raw(scored) == struct.pack(f"<{len(literals)}f", *(old[x] for x in literals))
    assert cp["typed"] == (native["typed"] if native else None)


def binder(model, anchors, work, catalog, m, history, cuts):
    assert all(history[k] == m[k] for k in ("owner", "binder", "target", "source_pdf", "source_pdf_sha256"))
    keys = [w["rgb_key"] for w in m["windows"]]
    assert keys == history["rgb_keys_by_window"]
    windows = [online.load_window(work / "captures" / key) for key in keys]
    targets = [e for i,w in enumerate(windows, 1) for s in w.spans for e in online.identify(s,i) if e.kind == "TARGET"]
    target, = targets
    assert target.ptr == (len(windows), 2, 3) and target.literal == "Posting 241 851"
    query = model.project(windows[-1])[2][target.ptr[2]]
    assert {sha(raw(query))} == {cp["query_sha256"] for cp in history["checkpoints"].values()}
    state = matrix.NeuralState(model.zero())
    assert all(torch.count_nonzero(t).item() == 0 for t in state.matrices)
    rows = [{"step": 0, "phase": "initial", "source": None, "read": read(model, query, anchors, state),
             "events_applied": [], "boundaries": []}]
    assert rows[0]["read"]["score_f32le"] == "00"*8
    hit = []
    step = 0
    for ordinal, (key, window) in enumerate(zip(keys, windows, strict=True), 1):
        k, v, q, a, b = model.project(window)
        for s in window.spans:
            i = s.index
            events = tuple(online.identify(s, ordinal))
            source = source_of(catalog, key, ordinal, s, events)
            assert source["feature_f32le_sha256"] == sha(raw(window.features[i]))
            applied = []
            for event in events:
                depth = state.controller.depth
                state.controller.apply(event)
                state.registry.update(event)
                rank = None
                if event.kind == "CONFIRM_POP" and depth > state.controller.depth:
                    state.matrices, kept = model.pop(state.matrices, depth)
                    rank = int(kept.sum()) if kept is not None else None
                applied.append({"kind": event.kind, "before_depth": depth, "after_depth": state.controller.depth,
                                "pop_rank": rank, "held_here": state.controller.held[state.controller.depth]})
            if target in events:
                assert raw(q[i]) == raw(query)
                native = matrix.attempt(model, state, q[i], target)
                assert native.choices["owner"] == NAMES and len(state.attempts) == 0
                state.attempts.append(native)
                typed = matrix.result(state, cuts)
                actual = {"typed": typed, "choices": pack(native.choices), "reason": native.reason,
                          "zero": native.zero, "summary_zero": native.summary_zero, "summary_target": native.summary_target,
                          "score_bytes": {f: raw(vals).hex() for f, vals in native.scores.items()}}
                old_attempt, = history["parity"]["plain_target"]["attempts"]
                for field in ("typed", "choices", "reason", "zero", "summary_zero", "summary_target"):
                    assert actual[field] == old_attempt[field]
                assert {f: sha(bytes.fromhex(x)) for f,x in actual["score_bytes"].items()} == old_attempt["logit_sha256"]
                pre = {"step": step, "phase": "native_pre", "source": source, "read": read(model, query, anchors, state),
                       "events_applied": applied, "boundaries": ["t3"], "native": actual}
                assert pre["read"]["score_f32le"] == actual["score_bytes"]["owner"]
                verify_boundary(pre, history["checkpoints"]["t3"], state, query, model, actual)
                rows.append(pre)
                hit.append("t3")
            state.matrices = model.write(state.matrices, state.controller.depth, k[i], v[i], a[i], b[i])
            step += 1
            cp = []
            if ordinal == 1 and state.controller.depth == 0 and any(e.kind == "OPEN_LEDGER" for e in events):
                decl, = (e for e in events if e.kind == "OPEN_LEDGER")
                assert decl.literal == "Ledger: " + m["owner"] and decl.ptr == (1, 1, 7)
                cp.append("t1")
            if ordinal == 1 and i == len(window.spans)-1:
                cp.append("t2")
            row = {"step": step, "phase": "post", "source": source, "read": read(model, query, anchors, state),
                   "events_applied": applied, "boundaries": cp}
            for label in cp:
                verify_boundary(row, history["checkpoints"][label], state, query, model)
                hit.append(label)
            rows.append(row)
            if target in events:
                assert hit == ["t1", "t2", "t3"]
                return {"binder": m["binder"], "owner": m["owner"], "query_f32le": raw(query).hex(),
                        "query_sha256": sha(raw(query)), "keys": keys, "rows": rows}
    raise ValueError("posting not reached")


def join_rows(a, c, metrics):
    assert a["query_f32le"] == c["query_f32le"]
    result = []
    for x, y in zip(a["rows"], c["rows"], strict=True):
        assert all(x[k] == y[k] for k in ("step","phase","boundaries","events_applied"))
        if x["source"]:
            left, right = x["source"], y["source"]
            assert all(left[k] == right[k] for k in ("ptr", "page", "kind", "block"))
            assert [e["kind"] for e in left["events"]] == [e["kind"] for e in right["events"]]
            if left["ptr"][0] > 1:
                assert left == right
        obs, other = x["read"], y["read"]
        assert obs["controller"] == other["controller"] and obs["registry"] == other["registry"]
        am, cm = obs["margin"], other["margin"]
        delta = am - cm
        win = am > 0 > cm
        assert win == (obs["top"] == "Alder" and other["top"] == "Cedar")
        for cp in x["boundaries"]:
            baseline = metrics[cp]
            assert [f64(val) for val in (am, cm, delta)] == [f64(baseline[k]) for k in
                    ("margin_Alder_input", "margin_Cedar_input", "delta")]
            assert baseline["correct_paired_win"] == win and baseline["positive_response"] == (delta > 0)
        result.append({"step": x["step"], "phase": x["phase"], "boundaries": x["boundaries"],
                       "delta": delta, "delta_f64le": f64(delta), "paired_win": win,
                       "Alder": x, "Cedar": y})
    return result


def sign(value):
    return (value > 0) - (value < 0)


def findings(rows):
    transitions = []
    for index,(prior, row) in enumerate(zip(rows, rows[1:]), 1):
        before, after = prior["delta"], row["delta"]
        transitions.append({"index": index, "step": row["step"], "phase": row["phase"],
                            "from_step": prior["step"], "from_phase": prior["phase"], "previous": before, "current": after,
                            "sign_change": sign(after) != sign(before), "strict_crossing": sign(after)*sign(before) < 0,
                            "touches_zero": sign(after)*sign(before) == 0, "absolute_reduction": abs(after) < abs(before),
                            "positive_decrease": before > 0 and after < before})
    own, = [i for i,r in enumerate(rows) if "t1" in r["boundaries"]]
    def at(i):
        r = rows[i]
        return {"index": i, "step": r["step"], "phase": r["phase"], "previous": rows[i-1]["delta"] if i else None,
                "delta": r["delta"], "ptr": r["Alder"]["source"]["ptr"] if r["Alder"]["source"] else None,
                "sources": {k: r[k]["source"] for k in NAMES},
                "tops": [r[k]["read"]["top"] for k in NAMES], "owner_eligible": r["Alder"]["read"]["owner_eligible"],
                "clear_scope": r["Alder"]["read"]["native_scope_clear"], "after_owner": i > own}
    def first(start):
        return next((at(i) for i in range(start,len(rows)) if rows[i]["phase"] == "post" and rows[i]["delta"]>0), None)
    return {"observations": len(rows), "writes": rows[-1]["step"], "owner": at(own), "first_positive": first(0),
            "first_positive_after_owner": first(own+1),
            "wins": [at(i) for i,r in enumerate(rows) if r["paired_win"]],
            "sign_changes": [t for t in transitions if t["sign_change"]],
            "absolute_reductions": [t for t in transitions if t["absolute_reduction"]],
            "decreases_from_positive": [t for t in transitions if t["positive_decrease"]],
            "certified_boundaries": {cp: at(i) for i,r in enumerate(rows) for cp in r["boundaries"]},
            "post_target": at(len(rows)-1)}


def main(candidate):
    global torch, matrix, online
    assert sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize
    assert sys.byteorder == "little" and Path(sys.executable).resolve() == RUNTIME.resolve()
    assert re.fullmatch("[a-f0-9]{40}", candidate)
    assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip() == candidate
    for name in ("inputs.py", "replay.py"):
        p = Path(__file__).with_name(name)
        assert p.read_bytes().replace(b"\r\n",b"\n") == blob(candidate, p.relative_to(ROOT).as_posix()).replace(b"\r\n",b"\n")
    work = SCRATCH / "review" / candidate
    work.mkdir(parents=True, exist_ok=False)
    for key in ("TEMP", "TMP", "HF_HOME", "TORCH_HOME", "XDG_CACHE_HOME", "TORCHINDUCTOR_CACHE_DIR"):
        dest = work / key
        dest.mkdir()
        os.environ[key] = str(dest)
    os.environ.update(CUDA_VISIBLE_DEVICES="-1", HF_HUB_OFFLINE="1", HF_DATASETS_OFFLINE="1",
                      TRANSFORMERS_OFFLINE="1", PIP_NO_INDEX="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    start, cpu = time.perf_counter(), time.process_time()
    manifest, baseline, fit, weights, catalog = prepare(work)
    sys.path.insert(0,str(work / "library"))
    import torch, matrix, online, numpy
    assert str(torch.__version__).split("+")[0] == "2.13.0" and torch.version.cuda is None
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.default_generator.manual_seed(2401)
    assert torch.get_default_dtype() == torch.float32 and torch.get_num_threads() == torch.get_num_interop_threads() == 1
    runs, summaries, members = {}, {}, {}
    with torch.inference_mode():
        for arm in ("M1", "M3"):
            model = matrix.Memory(flat=arm == "M1").eval()
            model.load_state_dict(torch.load(io.BytesIO(weights[arm]),map_location="cpu",weights_only=True),strict=True)
            assert {p.device.type for p in model.parameters()} == {"cpu"}
            anchors = model.anchors("owner", NAMES)
            assert sha(raw(anchors)) == baseline["owner_anchor_sha256"][arm]
            for pair in manifest["pairs"]:
                old, = [p for p in baseline["arms"][arm] if p["pair"] == pair["pair"]]
                assert old["horizon"] == pair["horizon"]
                tag = f"{arm}/{pair['horizon']}"
                by_owner = {}
                for m in pair["members"]:
                    hist, = [h for h in old["members"] if h["owner"] == m["owner"]]
                    by_owner[m["owner"]] = binder(model, anchors, work, catalog, m, hist, fit["thresholds"][arm])
                runs[tag] = join_rows(*(by_owner[n] for n in NAMES),old["metrics"])
                summaries[tag] = findings(runs[tag])
                members[tag] = {name:{k:v for k,v in obj.items() if k != "rows"} for name,obj in by_owner.items()}
                members[tag]["anchor_sha256"] = sha(raw(anchors))
    assert set(runs) == {"M1/12","M1/30","M3/12","M3/30"}
    artifacts = {"catalog.json": encoded(catalog)+b"\n", "bindings.json": encoded(members)+b"\n",
                 "steps.jsonl": b"".join(encoded({"run": tag, **r})+b"\n" for tag, rows in runs.items() for r in rows),
                 "findings.json": json.dumps(summaries, indent=2, allow_nan=False).encode()+b"\n"}
    for filename, payload in artifacts.items():
        write(work / filename, payload)
    receipt = {"candidate": candidate, "base": BASE, "command": sys.orig_argv, "python": sys.version,
               "python_sha256":sha(RUNTIME.read_bytes()), "torch":str(torch.__version__), "cuda_build":torch.version.cuda,
               "numpy": numpy.__version__, "platform":platform.platform(), "deterministic":torch.are_deterministic_algorithms_enabled(),
               "threads":torch.get_num_threads(), "interop_threads":torch.get_num_interop_threads(),
               "read_git_blobs":RECEIPTS, "evidence_sha256":{k:sha(v) for k,v in artifacts.items()},
               "cpu_seconds": time.process_time()-cpu, "wall_seconds":time.perf_counter()-start,
               "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write(work / "runtime.json", json.dumps(receipt,indent=2).encode()+b"\n")
    for tag,s in summaries.items():
        print(tag,s["writes"],len(s["wins"]),s["first_positive"]["step"],s["first_positive_after_owner"]["step"])


if __name__ == "__main__":
    main(*sys.argv[1:])
