"""WP-0029 orchestration. All numerical checkpoints come from unmodified WP-0028."""
import datetime
import json
import os
import struct
import subprocess
import sys
import time
from pathlib import Path
from zipfile import BadZipFile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from admission import BASE, CEDAR, FIXTURE, GATE, HISTORY, Inputs, require, route_inputs, sha


def examine(windows):
    """Describe the grammar's actual events and choices without admitting from truth."""
    import online
    controller, registry = online.Controller(), online.Registry()
    parents, targets = [], []
    end = None
    for ordinal, window in enumerate(windows, 1):
        for span in window.spans:
            events = list(online.identify(span, ordinal))
            for event in events:
                controller.apply(event)
                registry.update(event)
            for event in events:
                if event.kind == "TARGET" or (event.kind == "OPEN_LEDGER" and ordinal == 1 and
                                                controller.depth == 0):
                    row = {"pointer": list(event.ptr), "literal": event.literal, "value": event.value,
                           "choices": registry.choices(), "depth": controller.depth,
                           "ambiguous": controller.ambiguous()}
                    (targets if event.kind == "TARGET" else parents).append(row)
            if ordinal == 1:
                end = {"pointer": [ordinal, span.page, span.index], "choices": registry.choices(),
                       "depth": controller.depth, "ambiguous": controller.ambiguous()}
    return {"depth_zero_opening_parents": parents, "opening_end": end, "targets": targets}


def eligible(events, owner, horizon):
    from score_math import NAMES
    parents, targets = events["depth_zero_opening_parents"], events["targets"]
    if len(parents) != 1 or parents[0]["pointer"][:2] != [1, 1]:
        return "opening_parent_identity"
    if parents[0]["value"] != owner:
        return "actual_opening_owner_differs_from_printed_owner"
    if len(targets) != 1:
        return "target_count_" + str(len(targets))
    target = targets[0]
    if (target["pointer"] != [horizon // 3, 2, 3] or target["value"] != ("Posting", "241", "851")
            or target["literal"] != "Posting 241 851" or target["ambiguous"]):
        return "actual_final_posting_identity_or_scope"
    for event in (parents[0], events["opening_end"], target):
        if event["choices"]["owner"] != NAMES:
            return "owner_candidates_unavailable"
    if any(len(target["choices"][field]) < 2 for field in ("unit", "column")):
        return "native_final_field_candidates_unavailable"
    return None


def empty_pair(pair, arm, reason):
    from controlled import empty
    from score_math import TIMES, trajectory
    members = [{"owner": m["owner"], "binder": m["binder"], "target": m["target"],
                "source_pdf": m["source_pdf"], "source_pdf_sha256": m["source_pdf_sha256"],
                "rgb_keys_by_window": [w["rgb_key"] for w in m["windows"]],
                "eligibility_observations": None, "parity": None,
                "checkpoints": {t: empty(t, reason) for t in TIMES}} for m in pair["members"]]
    return {"arm": arm, "pair": pair["pair"], "template": pair["template"], "horizon": pair["horizon"],
            "source_target": pair["base_target"], "reason": reason, "members": members,
            "counts": {"planned": 1, "admitted": 0, "completed": 0}, "metrics": trajectory(members)}


def pair_run(work, pair, arm, model, cuts, inventory, gate):
    import online
    from measurement import comparable, measure, query_context
    from observe import tbytes
    from score_math import TIMES, trajectory
    def deny(reason, observed=None):
        row = empty_pair(pair, arm, reason)
        if observed:
            for member, events in zip(row["members"], observed, strict=True):
                member["eligibility_observations"] = events
        return row, {}

    if not gate["authenticated"]:
        return deny("capture_unauthenticated: " + gate["reason"])
    members = pair["members"]
    sequences = [[work / "windows" / w["rgb_key"] for w in m["windows"]] for m in members]
    ends = [m["windows"][-1]["rgb_key"] for m in members]
    if ends[0] != ends[1] or inventory[ends[0]] != inventory[ends[1]]:
        return deny("different_final_source_or_features")
    windows = [[online.load_window(p) for p in seq] for seq in sequences]
    observed = [examine(ws) for ws in windows]
    reasons = [eligible(ev, m["owner"], pair["horizon"]) for ev, m in zip(observed, members, strict=True)]
    if not gate["eligible_owner_cue"]:
        reasons.append("independent_owner_cue_ineligible")
    if any(reasons):
        return deny("; ".join(r for r in reasons if r), observed)
    contexts = [query_context(model, ws) for ws in windows]
    reason = comparable(contexts)
    if reason:
        return deny(reason, observed)
    queries = [tbytes(model.project(ws[-1])[2][context["ptr"][2]]) for ws, (context, _) in
               zip(windows, contexts, strict=True)]
    if queries[0] != queries[1]:
        return deny("projected_query_bytes_differ", observed)
    rows = empty_pair(pair, arm, None)
    comparison_bytes = {}
    for member, seq, query, ev in zip(rows["members"], sequences, queries, observed, strict=True):
        checkpoints, parity, _ = measure(model, seq, cuts)
        member.update(checkpoints=checkpoints, parity=parity, eligibility_observations=ev)
        scores = {}
        for t in TIMES:
            cp = checkpoints[t]
            require(sha(query) == cp["query_sha256"], "actual projected query differs at " + t)
            scores[t] = struct.pack("<ff", *(cp["scores"][name] for name in ("Alder", "Cedar")))
            require(sha(scores[t]) == cp["score_bytes_f32le_sha256"], "invalid score byte receipt")
        comparison_bytes[member["owner"]] = query, scores
    rows.update(counts={"planned": 1, "admitted": 1, "completed": 1}, metrics=trajectory(rows["members"]),
                final_rgb_key=ends[0], within_pair_query_bytes_equal=queries[0] == queries[1])
    return rows, comparison_bytes


def cross_horizon(arms):
    result = {}
    for arm, pairs in arms.items():
        rows = {}
        for owner in ("Alder", "Cedar"):
            checks = {}
            for t in ("t1", "t2"):
                if any(owner not in p for p in pairs):
                    checks[t] = {"query_bytes_equal": None, "score_bytes_equal": None, "shared": None}
                    continue
                (q12, s12), (q30, s30) = [p[owner] for p in pairs]
                checks[t] = {"query_bytes_equal": q12 == q30, "score_bytes_equal": s12[t] == s30[t],
                             "score_f32le_hex_by_horizon": {"12": s12[t].hex(), "30": s30[t].hex()},
                             "query_sha256_by_horizon": {"12": sha(q12), "30": sha(q30)},
                             "shared": q12 == q30 and s12[t] == s30[t]}
            rows[owner] = checks
        result[arm] = rows
    return result


def control_run(work, pairs, arm, model, cuts, history):
    import online
    from measurement import measure, zero_control
    from score_math import controls, derived, margin
    rows = []
    for pair in pairs:
        source = next(m for m in pair["members"] if m["owner"] == "Alder")
        paths = [work / "windows" / w["rgb_key"] for w in source["windows"]]
        windows = [online.load_window(p) for p in paths]
        observed = examine(windows)
        require(eligible(observed, "Alder", pair["horizon"]) is None and
                eligible(observed, "Cedar", pair["horizon"]) == "actual_opening_owner_differs_from_printed_owner",
                "historical authentic-parent positive/negative control")
        row, parity, _ = measure(model, paths, cuts)
        ref, = [m for p in history["arms"][arm]["pairs"] for m in p["members"] if m["binder"] == pair["base_binder"]]
        require(json.loads(json.dumps([row, parity])) == [ref["checkpoints"], ref["parity"]],
                "historical control differs from published WP-0028 run")
        zero = zero_control(model, windows, cuts)
        rows.append({"horizon": pair["horizon"], "binder": pair["base_binder"], "all_checkpoint_and_parity_equal": True,
                     "eligibility_observations": observed, "wrong_owner_rejected": True, "zero_state": zero})
    denied = {"authenticated": False, "reason": "historical denial control"}
    for pair in pairs:
        null_pair, retained = pair_run(work, pair, arm, model, cuts, {}, denied)
        require(not retained and null_pair["counts"] == {"planned": 1, "admitted": 0, "completed": 0}
                and all(value is None for row in null_pair["metrics"].values() for value in row.values())
                and all(m["parity"] is None and all(cp["typed"] is None and
                        all(value is None for value in cp["scores"].values())
                        for cp in m["checkpoints"].values()) for m in null_pair["members"]),
                "failed gate emitted a measurement")
    pdf = None
    if arm == "M3":
        example, = [row for row in history["arms"][arm]["pairs"] if row["pair"] == "03fe821e0efada96bdc61e31"]
        by_owner = {m["owner"]: margin(m["checkpoints"]["t3"]["scores"]) for m in example["members"]}
        actual = derived(by_owner["Alder"], by_owner["Cedar"], example["metrics"]["t1"]["delta"])
        swapped = derived(by_owner["Cedar"], by_owner["Alder"], -example["metrics"]["t1"]["delta"])
        require([format(actual[k], ".7f") for k in ("margin_Alder_input", "margin_Cedar_input", "mu", "delta")]
                == ["0.1030183", "0.1028849", "0.1029516", "0.0001334"] and
                actual["mu"] == swapped["mu"] and actual["delta"] == -swapped["delta"],
                "owner-math PDF or label-exchange control failed")
        pdf = {"pair": example["pair"], "actual": actual, "binder_labels_exchanged": swapped}
    return {"old_binders": rows, "arithmetic_controls": controls(), "denied_horizons_have_null_scores": True,
            "historical_M3_formula_example": pdf}


def main(work, mode, candidate, *gate_args):
    start, cpu_start = time.perf_counter(), time.process_time()
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize, "use -I -B")
    require(work.parent.parent == Path("C:/Users/jackg/eLedgerCare-Speed/WP-0029") and
            work.parent.name in {"scoring", "review", "coordination"}, "unexpected scratch")
    guards = ("HF_HUB_OFFLINE", "HF_DATASETS_OFFLINE", "TRANSFORMERS_OFFLINE", "PIP_NO_INDEX",
              "OMP_NUM_THREADS", "MKL_NUM_THREADS")
    require(os.environ.get("CUDA_VISIBLE_DEVICES") == "-1" and all(os.environ.get(k) == "1" for k in guards)
            and all(Path(os.environ[k]).parent == work for k in ("TEMP", "TMP", "TORCH_HOME", "HF_HOME",
                                                                "XDG_CACHE_HOME", "TORCHINDUCTOR_CACHE_DIR")),
            "CPU or cache guard missing")
    inputs = Inputs()
    fit = inputs.stage(work, candidate)
    sys.path.insert(0, str(work / "library"))
    import matrix
    import run
    import torch
    from inputs import record
    from observe import tbytes
    from score_math import FLOOR, NAMES
    require(mode in ("controls", "released") and len(gate_args) == (2 if mode == "released" else 0),
            "invalid mode or gate arguments")
    gate = inputs.gate(*gate_args) if mode == "released" else None
    manifest = json.loads(inputs.blob(FIXTURE, "docs/fixtures/WP-0028/manifest.json"))
    pairs = sorted(manifest["pairs"], key=lambda p: p["horizon"])
    require([p["horizon"] for p in pairs] == [12, 30], "wrong horizon denominator")
    run.setup()
    require(torch.get_default_dtype() == torch.float32 and not torch.cuda.is_available() and
            torch.cuda.device_count() == 0 and torch.get_num_threads() == torch.get_num_interop_threads() == 1
            and torch.are_deterministic_algorithms_enabled(), "requires deterministic CPU FP32")
    inventory, integrity_failure = {}, None
    try:
        inventory = route_inputs(inputs, work, pairs, gate)
    except (ValueError, KeyError, OSError, RuntimeError, BadZipFile, subprocess.SubprocessError) as exc:
        if mode == "controls":
            raise
        integrity_failure = f"capture_routing_integrity: {type(exc).__name__}: {exc}"
    history = None
    if mode == "controls":
        history = json.loads(inputs.blob(HISTORY, "docs/research/WP-0028/evidence/historical.json"))
    result = {"mode": mode, "gate": {"revision": gate_args[0], "path": GATE, "sha256": gate_args[1],
                                      "authenticated": gate["authenticated"]} if gate else None,
              "capture_inventory": inventory, "cedar_rgb_key": CEDAR, "arms": {},
              "weights_sha256": fit["weights"], "thresholds": fit["thresholds"], "owner_anchor_sha256": {},
              "ratio_denominator_floor": FLOOR, "integrity_failure": integrity_failure}
    byte_pairs = {}
    with torch.inference_mode():
        for arm in ("M1", "M3"):
            model = matrix.Memory(flat=arm == "M1").eval()
            model.load_state_dict(torch.load(work / (arm + ".pt"), weights_only=True, map_location="cpu"))
            cuts = fit["thresholds"][arm]
            require(cuts == [1., .1] and all(p.device.type == "cpu" for p in model.parameters()), "wrong frozen arm")
            result["owner_anchor_sha256"][arm] = sha(tbytes(model.anchors("owner", NAMES)))
            if mode == "controls":
                result["arms"][arm] = control_run(work, pairs, arm, model, cuts, history)
                continue
            try:
                if integrity_failure:
                    results = [(empty_pair(p, arm, integrity_failure), {}) for p in pairs]
                else:
                    results = [pair_run(work, p, arm, model, cuts, inventory, gate) for p in pairs]
            except (ValueError, KeyError, IndexError, AssertionError, RuntimeError) as exc:
                reason = f"arm_parity_or_integrity: {type(exc).__name__}: {exc}"
                results = [(empty_pair(p, arm, reason), {}) for p in pairs]
            result["arms"][arm] = [r for r, _ in results]
            byte_pairs[arm] = [b for _, b in results]
    if mode == "released":
        result["cross_horizon"] = cross_horizon(byte_pairs)
        result["arm_pair_counts"] = {key: sum(p["counts"][key] for rows in result["arms"].values() for p in rows)
                                     for key in ("planned", "admitted", "completed")}
    record(work / "result.json", result)
    record(work / "runtime.json", {"candidate": candidate, "base": BASE, "mode": mode, "command": sys.orig_argv,
           "executable": sys.executable, "executable_sha256": sha(Path(sys.executable).read_bytes()),
           "python": sys.version, "torch": str(torch.__version__), "deterministic": True, "threads": 1,
           "interop_threads": 1, "cuda_visible_devices": "-1", "native_ocr_or_gpu_calls": 0,
           "git_inputs_sha256": inputs.hashes, "wall_seconds": time.perf_counter() - start,
           "cpu_seconds": time.process_time() - cpu_start, "result_sha256": sha((work / "result.json").read_bytes()),
           "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    print(mode, sha((work / "result.json").read_bytes()), result.get("arm_pair_counts", ""))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(), *sys.argv[2:])
