"""Observe a frozen advance call at its native posting and each individual write."""
import datetime
import json
import os
from pathlib import Path
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inputs30 import NAMES, RESULT_SHA, admit, catalog, check, guards, packed, save, sha


def tensor_bytes(tensor):
    check(str(tensor.dtype) == "torch.float32" and tensor.device.type == "cpu", "expected CPU FP32")
    return tensor.detach().contiguous().numpy().tobytes()


def location(span, ordinal, events, key, record):
    meta = record["metadata"]
    check((span.index, span.page, span.kind, span.block_kind, span.text, list(span.box)) ==
          (meta["index"], meta["page"], meta["kind"], meta["block_kind"], meta["text"], meta["bbox999"]),
          "frozen reader differs from source")
    ptr = [ordinal, span.page, span.index]
    check(all(list(ev.ptr) == ptr for ev in events), "parser event pointer")
    return {"pointer": ptr, "window_index": ordinal, "absolute_page": 3 * (ordinal - 1) + span.page,
            "kind": span.kind, "block_kind": span.block_kind, "literal": span.text, "cells": list(span.cells),
            "events": [dict(kind=e.kind, value=e.value, literal=e.literal) for e in events],
            "rgb_key": key, **{k: record[k] for k in ("metadata_sha256", "raw_span_sha256", "literal_sha256",
                                                       "feature_sha256", "selected_token_ids_u32le_sha256")}}


def observe(model, state, matrices, query, query_sha, anchors, cuts):
    import matrix
    import torch
    depth = state.controller.depth
    full = torch.stack(matrices)
    response = model.read(matrices, depth, query, "owner")
    logits = anchors @ matrix.direction(response)
    scores = logits.tolist()
    check(torch.isfinite(logits).all().item(), "nonfinite owner scores")
    margin = scores[0] - scores[1]
    leader = "Alder" if margin > 0 else "Cedar" if margin < 0 else None
    registry = state.registry.choices()
    top = logits.topk(2).values
    return {"controller": {"depth": depth, "held": list(state.controller.held), "fault": state.controller.fault,
                           "ambiguous_reason": state.controller.ambiguous()},
            "registry": registry, "owner_eligible": tuple(registry["owner"]) == NAMES,
            "scope_clear": not state.controller.ambiguous(),
            "query_sha256": query_sha, "matrix_sha256": sha(tensor_bytes(full)),
            "owner_columns_sha256": sha(tensor_bytes(full[:, :, :32])),
            "read_sha256": sha(tensor_bytes(response)), "zero_read": response.norm().item() <= matrix.EPS,
            "scores": dict(zip(NAMES, scores, strict=True)), "scores_f32le_hex": tensor_bytes(logits).hex(),
            "margin": margin, "margin_f64le_hex": struct.pack("<d", margin).hex(),
            "top_owner": leader, "exact_top_tie": leader is None, "rank": {name: 1 if leader in (name, None) else 2
                                                                         for name in NAMES},
            "top_score_pass": bool(top[0] >= cuts[0]), "top_gap_pass": bool(top[0] - top[1] >= cuts[1])}


class Readout:
    """matrix.advance owns control/pop/attempt/write order; observe its actual write boundary."""

    def __init__(self, model, window, view, ordinal, state, source_rows, rgb_key, query, query_sha,
                 anchors, cuts, rows, prior_writes, owner_ptr, target_ptr):
        self.model = model
        self.window = window
        self.view = view
        self.ordinal = ordinal
        self.state = state
        self.source_rows = source_rows
        self.rgb_key = rgb_key
        self.query = query
        self.query_sha = query_sha
        self.owner_anchors = anchors
        self.cuts = cuts
        self.rows = rows
        self.prior_writes = prior_writes
        self.owner_ptr = owner_ptr
        self.target_ptr = target_ptr
        self.index = 0

    def __getattr__(self, name):
        return getattr(self.model, name)

    def project(self, view):
        check(view is self.view, "wrong projected window")
        # The last traversal stops immediately after the target write. The actual
        # original full window, including its original batch shape, is projected.
        return self.model.project(self.window)

    def write(self, matrices, depth, k, v, a, b):
        import online
        span = self.view.spans[self.index]
        check(span.index == self.index and self.state.controller.depth == depth, "write order or active depth")
        events = list(online.identify(span, self.ordinal))
        source = location(span, self.ordinal, events, self.rgb_key, self.source_rows[span.index])
        controls = self.state.trace[-len(events):] if events else []
        check([(e["event"], e["literal"], list(e["ptr"])) for e in controls] ==
              [(e.kind, e.literal, list(e.ptr)) for e in events], "audit and parser events disagree")
        before = self.prior_writes + self.index

        def row(phase, step, at, labels):
            return {"phase": phase, "step_index": step, "source": source,
                    "control_events": list(controls), "checkpoints": labels,
                    **observe(self.model, self.state, at, self.query, self.query_sha, self.owner_anchors, self.cuts)}

        ptr = tuple(source["pointer"])
        if ptr == self.target_ptr:
            native, = self.state.attempts
            pre = row("native_pre_target", before, matrices, ["t3"])
            check(tuple(native.choices["owner"]) == NAMES and
                  tensor_bytes(native.scores["owner"]).hex() == pre["scores_f32le_hex"],
                  "native and retrospective owner reads differ")
            pre["native"] = {"typed": native.typed(self.cuts), "reason": native.reason, "zero": native.zero,
                             "summary_target": native.summary_target, "summary_zero": native.summary_zero,
                             "choices": native.choices,
                             "logit_sha256": {f: sha(tensor_bytes(t)) for f, t in native.scores.items()}}
            self.rows.append(pre)
        updated = self.model.write(matrices, depth, k, v, a, b)
        labels = []
        if ptr == self.owner_ptr:
            labels.append("t1")
        if self.ordinal == 1 and self.index == len(self.window.spans) - 1:
            labels.append("t2")
        self.rows.append(row("post_write", before + 1, updated, labels))
        self.index += 1
        return updated


def traverse(model, cuts, anchors, work, member, sources, ref):
    import matrix
    import online
    from measurement import query_context
    windows = [online.load_window(work / "windows" / w["rgb_key"]) for w in member["windows"]]
    context, reason = query_context(model, windows)
    check(reason is None, "unqualified native posting")
    ptr = context["ptr"]
    owner_ptr = context["parent_ptr"]
    query = model.project(windows[ptr[0] - 1])[2][ptr[2]]
    qraw = tensor_bytes(query)
    qsha = sha(qraw)
    check(qsha == context["query_sha256"] and list(context["candidate_order"]) == list(NAMES) and
          ptr == (len(windows), 2, 3) and context["literal"] == "Posting 241 851", "posting identity")
    state = matrix.NeuralState(model.zero())
    zero = observe(model, state, state.matrices, query, qsha, anchors, cuts)
    check(zero["scores_f32le_hex"] == "00"*8 and zero["exact_top_tie"] and not zero["owner_eligible"],
          "step-zero tie or eligibility")
    rows = [{"phase": "zero", "step_index": 0, "source": None, "control_events": [], "checkpoints": [], **zero}]
    writes = 0
    for wi, (window, binding) in enumerate(zip(windows, member["windows"], strict=True), 1):
        check(binding["window"] == wi, "window order")
        key = binding["rgb_key"]
        spans = sources[key]["spans"]
        check(len(spans) == len(window.spans) and all(
            sha(tensor_bytes(window.features[s.index])) == spans[s.index]["feature_sha256"] for s in window.spans),
            "loaded feature order")
        view = window
        if wi == ptr[0]:
            view = online.Window(window.spans[:ptr[2] + 1], window.features[:ptr[2] + 1])
        observer = Readout(model, window, view, wi, state, spans, key, query, qsha, anchors, cuts,
                           rows, writes, owner_ptr, ptr)
        matrix.advance(observer, state, view, wi)
        check(observer.index == len(view.spans), "write count")
        writes += observer.index
    check(len(state.attempts) == 1 and len(rows) == writes + 2 and
          rows[-2]["phase"] == "native_pre_target" and rows[-1]["source"]["pointer"] == list(ptr),
          "native target order")
    parity = {}
    for label, expected in ref["checkpoints"].items():
        actual, = [r for r in rows if label in r["checkpoints"]]
        raw = bytes.fromhex(actual["scores_f32le_hex"])
        expected_raw = struct.pack("<ff", *(expected["scores"][n] for n in NAMES))
        expected_margin = struct.pack("<d", expected["scores"]["Alder"] - expected["scores"]["Cedar"])
        check(raw == expected_raw and sha(raw) == expected["score_bytes_f32le_sha256"] and
              actual["margin_f64le_hex"] == expected_margin.hex() and actual["source"]["pointer"] == expected["pointer"],
              "original score/margin/pointer mismatch " + label)
        for field in ("controller", "query_sha256", "matrix_sha256", "read_sha256", "owner_columns_sha256",
                      "exact_top_tie", "zero_read", "top_score_pass", "top_gap_pass"):
            check(actual[field] == expected[field], "WP-0029 " + label + "/" + field)
        check(actual["owner_eligible"] and list(actual["registry"]["owner"]) == expected["candidate_order"],
              "frozen checkpoint registry")
        parity[label] = {"step_index": actual["step_index"], "phase": actual["phase"], "pointer": expected["pointer"],
                         "scores_f32le_hex": raw.hex(), "original_scores_f32le_hex": expected_raw.hex(),
                         "margin_f64le_hex": expected_margin.hex(), "query_sha256": qsha}
        if label == "t1":
            check(any(e["kind"] == "OPEN_LEDGER" and e["literal"] == "Ledger: " + member["owner"]
                      for e in actual["source"]["events"]), "actual parent declaration")
        if label == "t3":
            attempt, = ref["parity"]["plain_target"]["attempts"]
            check(packed(actual["native"]) == packed(attempt) and actual["native"]["typed"] == expected["typed"],
                  "original native attempt or typed decision changed")
            parity[label]["native"] = actual["native"]
    check(set(parity) == {"t1", "t2", "t3"}, "checkpoint denominator")
    return rows, {"query_f32le_hex": qraw.hex(), "query_sha256": qsha, "target": context, "checks": parity,
                  "binder": member["binder"], "target_id": member["target"], "owner": member["owner"],
                  "source_pdf": member["source_pdf"], "source_pdf_sha256": member["source_pdf_sha256"],
                  "rgb_keys_by_window": [w["rgb_key"] for w in member["windows"]]}


def main(candidate, work):
    start = time.perf_counter()
    cpu = time.process_time()
    entry_sources = guards(candidate, work)
    pairs, inventory, reference, fit, hashes = admit(work)
    import matrix
    import numpy
    import torch
    from findings import pair_rows, summarize
    check(torch.version.cuda is None and str(torch.__version__).split("+")[0] == "2.13.0", "CPU-only torch 2.13.0")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.default_generator.manual_seed(2401)
    check(torch.get_default_dtype() == torch.float32 and torch.get_default_device().type == "cpu", "CPU FP32")
    sources = catalog(work, inventory)
    output = work / "evidence"
    output.mkdir()
    save(output / "sources.json", sources)
    parity, findings = {}, {}
    with torch.inference_mode():
        for arm in ("M1", "M3"):
            model = matrix.Memory(flat=(arm == "M1")).eval()
            weights = torch.load(work / (arm + ".pt"), map_location="cpu", weights_only=True)
            model.load_state_dict(weights, strict=True)
            check(all(p.device.type == "cpu" and p.dtype == torch.float32 for p in model.parameters()), "CPU tensors")
            anchors = model.anchors("owner", NAMES)
            cuts = fit["thresholds"][arm]
            check(sha(tensor_bytes(anchors)) == reference["owner_anchor_sha256"][arm] and cuts == [1., .1], arm)
            for pair in pairs:
                key = arm + "-" + str(pair["horizon"])
                hist, = [r for r in reference["arms"][arm] if r["pair"] == pair["pair"]]
                rows, checks = {}, {}
                for member in pair["members"]:
                    owner = member["owner"]
                    ref, = [r for r in hist["members"] if r["binder"] == member["binder"] and r["owner"] == owner]
                    rows[owner], checks[owner] = traverse(model, cuts, anchors, work, member, sources, ref)
                check(checks["Alder"]["query_f32le_hex"] == checks["Cedar"]["query_f32le_hex"], "two queries differ")
                paired = pair_rows(rows)
                for t, published in hist["metrics"].items():
                    row, = [r for r in paired if t in r["checkpoints"]]
                    check(struct.pack("<d", row["delta"]) == struct.pack("<d", published["delta"]) and
                          row["paired_win"] == published["correct_paired_win"], "published signed checkpoint")
                parity[key] = {"pair": pair["pair"], "members": checks, "anchor_order": NAMES,
                               "anchors_sha256": sha(tensor_bytes(anchors)), "cuts": cuts, "arm_weight_sha256": fit["weights"][arm]}
                findings[key] = summarize(paired)
                save(output / (key + ".json"), paired, rows=True)
    save(output / "findings.json", findings)
    save(output / "parity.json", parity)
    digests = {p.name: sha(p.read_bytes()) for p in sorted(output.iterdir())}
    save(output / "runtime.json", {"candidate": candidate, "candidate_sources": entry_sources, "git_blobs": hashes,
         "original_result_sha256": RESULT_SHA, "deterministic_files_sha256": digests, "python": sys.version,
         "executable": sys.executable, "executable_sha256": sha(Path(sys.executable).read_bytes()),
         "torch": str(torch.__version__), "numpy": numpy.__version__, "torch_cuda_build": torch.version.cuda,
         "visible_devices": os.environ["CUDA_VISIBLE_DEVICES"], "threads": torch.get_num_threads(),
         "interop_threads": torch.get_num_interop_threads(), "deterministic": torch.are_deterministic_algorithms_enabled(),
         "command": sys.orig_argv, "cpu_seconds": time.process_time() - cpu, "wall_seconds": time.perf_counter() - start,
         "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    print(json.dumps(digests, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]).resolve())
