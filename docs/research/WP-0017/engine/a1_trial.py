"""Execute one Stage A1 configuration in an isolated child process.

Phase 1 runs uncontaminated ordinary free generation on the exact 3-page windows
(019 and 037) rendered at 300-DPI RGB via original Astra trial.inputs and freezes
all free-run timings and outputs on disk BEFORE Phase 2 starts.
Phase 2 runs serial 1-token-at-a-time teacher-forced BPE span-logit probes.
"""
from __future__ import annotations

from contextlib import ExitStack
import importlib.util
from io import TextIOWrapper
import json
import os
import sys
import traceback
from pathlib import Path
from time import perf_counter_ns as clock

# Windows redirected handles can default to CP1252 under python -I; reconfigure for TextStreamer (S0=False).
for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, TextIOWrapper):
        _stream.reconfigure(encoding="utf-8", errors=_stream.errors)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WP15_CARBON = ROOT / "docs/research/WP-0015/carbon"
WP15_ASTRA = ROOT / "docs/research/WP-0015/astra"
WP14 = ROOT / "docs/research/WP-0014/eld-latency-author"
WORKER = ROOT / "workers/local_ocr"
for _p in reversed((str(HERE), str(WP15_CARBON), str(WP15_ASTRA), str(WP14), str(WORKER))):
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

from ablation_engine import create_wp0017_engine, extract_engine_runtime_hooks
from formats import digest, publish
from local_ocr import protocol, verify_runtime, worker
from local_ocr.env_guard import audit_worker_environment, current_process_create_filetime
from local_ocr.pdf_render import verify_renderer_identity
from native import GPU, LOCK_SHA, Q0
from span_probe import (
    build_frozen_field_locator,
    evaluate_offline_margin_flag,
    extract_free_field_at_locator,
    run_teacher_forced_window_probe,
    token_ids_sha256,
)
from switches import resolve_mode

_astra_spec = importlib.util.spec_from_file_location("astra_trial", WP15_ASTRA / "trial.py")
_astra_trial = importlib.util.module_from_spec(_astra_spec)
_astra_spec.loader.exec_module(_astra_trial)
astra_inputs = _astra_trial.inputs
astra_document = _astra_trial.document


def _anchor_reference_mode(resolved_bits: str) -> str | None:
    if resolved_bits == "000000":
        return "native"
    if resolved_bits == "111111":
        return "carbon_bf16"
    return None


def _compute_free_window_metrics(details: dict, engine_read_s: float, window_wall_s: float) -> dict:
    marks = details.get("clock_marks_ns") or {}
    prefill_s = details.get("prefill_time_s")
    if prefill_s is None and "first_token" in marks and "generate_start" in marks:
        prefill_s = (marks["first_token"] - marks["generate_start"]) / 1e9
    prefill_ms = (prefill_s * 1000.0) if prefill_s is not None else None

    post_first_ms = None
    if "generate_end" in marks and "first_token" in marks:
        post_first_ms = (marks["generate_end"] - marks["first_token"]) / 1e6
    elif details.get("time_s") is not None and prefill_s is not None:
        post_first_ms = max(0.0, (float(details["time_s"]) - float(prefill_s)) * 1000.0)

    fwd_count = int(details.get("forward_count") or 0)
    decode_forwards = max(0, fwd_count - 1)
    out_toks = len(details.get("window_token_ids") or [])
    decode_ms_per_fwd = (post_first_ms / decode_forwards) if (post_first_ms is not None and decode_forwards > 0) else None
    decode_ms_per_emitted = (post_first_ms / out_toks) if (post_first_ms is not None and out_toks > 0) else None

    return {
        "ordinary_engine_read_s": engine_read_s,
        "window_render_read_publish_s": window_wall_s,
        "native_infer_ms": details.get("native_infer_ms"),
        "generate_time_s": details.get("time_s"),
        "prefill_ms": prefill_ms,
        "post_first_token_decode_ms": post_first_ms,
        "forward_count_total": fwd_count,
        "decode_forwarded_tokens": decode_forwards,
        "burst_extra_forwards": int(details.get("burst_extra_forwards") or 0),
        "emitted_token_count": out_toks,
        "decode_ms_per_forwarded_token": decode_ms_per_fwd,
        "decode_ms_per_emitted_token": decode_ms_per_emitted,
    }


def execute_a1_segment(
    seg_dir: Path,
    *,
    engine_factory=create_wp0017_engine,
    skip_env_and_lock_audit: bool = False,
    pdfium_override=None,
) -> dict:
    seg_plan = json.loads((seg_dir / "segment-plan.json").read_bytes())
    mode = str(seg_plan["mode"])
    surgical_override = seg_plan.get("surgical_override")
    resolved = resolve_mode(mode, surgical_override=surgical_override)

    a1_manifest_path = Path(seg_plan["a1_manifest"])
    a1_bytes = a1_manifest_path.read_bytes()
    if digest(a1_bytes) != str(seg_plan["a1_manifest_sha256"]).lower():
        raise ValueError("A1 input manifest SHA-256 mismatch inside child process")
    a1_obj = json.loads(a1_bytes)

    if not skip_env_and_lock_audit:
        audit_worker_environment(dict(os.environ), run_dir=seg_dir, readonly_q0_root=Q0, leased_gpu_uuid=GPU)
        rt = worker.RealTorchRuntime()
        lock, _ = verify_runtime.load_json_checked(protocol.DEPENDENCY_LOCK_PATH, LOCK_SHA, "lock")
        pdfium_mod = rt.import_pdfium()
        renderer = verify_renderer_identity(pdfium_mod, rt.dist_version, lock)
    else:
        import pypdfium2

        pdfium_mod = pdfium_override or pypdfium2
        renderer = "cpu_synthetic_stub_renderer"

    publish(
        seg_dir / "child.json",
        dict(
            pid=os.getpid(),
            creation_filetime=current_process_create_filetime(),
            mode=mode,
            canonical_mode=resolved.canonical_name,
            switch_bits=resolved.switch_config.bits,
            implementation=resolved.implementation,
        ),
    )

    warmups = list(seg_plan.get("warmups") or [])
    forced_repeats = int(seg_plan.get("forced_native_probe_repeats", 1))
    if forced_repeats < 1:
        raise ValueError("forced_native_probe_repeats must be >= 1")

    with ExitStack() as resources:
        load_t0 = clock()
        eng = engine_factory(mode, seg_dir, surgical_override=surgical_override)
        resources.callback(eng.close)
        load_elapsed_s = (clock() - load_t0) / 1e9
        publish(
            seg_dir / f"load-{mode}.json",
            dict(elapsed_s=load_elapsed_s, renderer=renderer, **eng.info),
        )

        # Untimed cold-initialization settling warmups (identical to WP-0016 g0-ab warm-1..3).
        warmup_records = []
        if warmups:
            warm_root = seg_dir / "warmups"
            warm_root.mkdir(parents=True, exist_ok=False)
            for w_idx, w_req in enumerate(warmups, 1):
                w_req_bound = dict(w_req, mode=mode)
                w_folder = warm_root / f"{w_idx:02d}-{w_req_bound['label']}-{mode}"
                rec = astra_document(w_req_bound, eng, w_folder, renderer)
                warmup_records.append(
                    {
                        "index": w_idx,
                        "label": w_req_bound["label"],
                        "elapsed_s": rec["elapsed_s"],
                        "prediction_sha256": rec["prediction_sha256"],
                    }
                )
            settled = (
                warmup_records[-1]["prediction_sha256"] == warmup_records[-2]["prediction_sha256"]
                if len(warmup_records) >= 2
                else None
            )
            publish(
                warm_root / "warmups-summary.json",
                {"count": len(warmup_records), "settled_last_two_equal": settled, "records": warmup_records},
            )

        hooks = extract_engine_runtime_hooks(eng)
        tokenizer = hooks["tokenizer"]

        # Freeze structural locators on anchored A1 manifest BEFORE running target windows.
        request = dict(a1_obj["request"])
        pdf_bytes = Path(request["pdf"]).read_bytes()
        if digest(pdf_bytes) != str(request["sha256"]).lower():
            raise ValueError("Source PDF SHA-256 disagreed with frozen A1 manifest")

        locators: list[dict] = []
        for win_spec in a1_obj["windows"]:
            nat_ids = [int(t) for t in win_spec["by_mode"]["native"]["token_ids"]]
            car_ids = [int(t) for t in win_spec["by_mode"]["carbon_bf16"]["token_ids"]]
            loc = build_frozen_field_locator(
                first_page=int(win_spec["first_page"]),
                identifier_page=int(win_spec["identifier_page"]),
                alternatives=list(win_spec["alternatives"]),
                native_token_ids=nat_ids,
                carbon_token_ids=car_ids,
                tokenizer=tokenizer,
            )
            locators.append(loc)

        # =====================================================================
        # PHASE 1: Uncontaminated Ordinary Free Run (timing frozen immediately)
        # =====================================================================
        free_dir = seg_dir / "free"
        free_dir.mkdir(parents=True, exist_ok=False)
        free_windows_summary = []

        with pdfium_mod.PdfDocument(pdf_bytes) as doc:
            if len(doc) != int(request["pages"]) or not 1 <= len(doc) <= 60:
                raise ValueError(f"Unexpected PDF page count: {len(doc)} vs {request['pages']}")

            for win_spec, locator in zip(a1_obj["windows"], locators):
                first_page = int(win_spec["first_page"])
                first0 = first_page - 1
                last0 = min(first0 + eng.window, len(doc))
                w_wall_t0 = clock()
                batch = astra_inputs(doc, first0, last0, request)
                try:
                    eng_t0 = clock()
                    outputs, details = eng.read(batch, free_dir)
                    eng_t1 = clock()
                    win_record = {
                        "source_sha256": request["sha256"],
                        "first_page": first_page,
                        "pages": len(batch),
                        "engine_begin_ns": eng_t0,
                        "engine_end_ns": eng_t1,
                        **details,
                    }
                    win_sha = publish(free_dir / f"window-{first_page:03d}.json", win_record)
                    if len(outputs) != len(batch):
                        raise ValueError(f"Incomplete window-{first_page:03d}; raw evidence retained")
                    for row, (content, raw) in zip(batch, outputs):
                        physical = row["page"]
                        evidence = {k: v for k, v in row.items() if k != "image"}
                        link = dict(source_sha256=request["sha256"], page=physical)
                        pred = dict(**link, state="complete", **content)
                        publish(free_dir / f"raw-{physical:03d}.json", dict(**evidence, source_sha256=request["sha256"], **raw))
                        publish(free_dir / f"page-{physical:03d}.json", pred)
                    w_wall_t1 = clock()
                finally:
                    for row in batch:
                        row["image"].close()

                emitted_ids = [int(t) for t in details["window_token_ids"]]
                eos_id = int(tokenizer.eos_token_id)
                eos_absent = (eos_id not in emitted_ids)
                emitted_sha = token_ids_sha256(emitted_ids)

                nat_anchor_ids = [int(t) for t in win_spec["by_mode"]["native"]["token_ids"]]
                car_anchor_ids = [int(t) for t in win_spec["by_mode"]["carbon_bf16"]["token_ids"]]
                ref_mode = _anchor_reference_mode(resolved.switch_config.bits)
                endpoint_parity = None
                if ref_mode is not None:
                    expected_ids = nat_anchor_ids if ref_mode == "native" else car_anchor_ids
                    expected_sha = token_ids_sha256(expected_ids)
                    first_diff = None
                    for idx in range(min(len(emitted_ids), len(expected_ids))):
                        if emitted_ids[idx] != expected_ids[idx]:
                            first_diff = {
                                "index": idx,
                                "observed_token_id": emitted_ids[idx],
                                "expected_token_id": expected_ids[idx],
                            }
                            break
                    if first_diff is None and len(emitted_ids) != len(expected_ids):
                        first_diff = {
                            "index": min(len(emitted_ids), len(expected_ids)),
                            "length_mismatch": [len(emitted_ids), len(expected_ids)],
                        }
                    endpoint_parity = {
                        "reference_anchor": ref_mode,
                        "exact_token_array_match": (emitted_ids == expected_ids),
                        "observed_token_ids_sha256": emitted_sha,
                        "expected_token_ids_sha256": expected_sha,
                        "eos_excluded_verified": eos_absent,
                        "finish_reason_stop": (details.get("finish_reason") == "stop"),
                        "first_diff": first_diff,
                    }

                free_field = extract_free_field_at_locator(
                    emitted_ids,
                    tokenizer,
                    locator,
                    native_window_token_ids=nat_anchor_ids,
                )
                free_metrics = _compute_free_window_metrics(
                    details,
                    engine_read_s=(eng_t1 - eng_t0) / 1e9,
                    window_wall_s=(w_wall_t1 - w_wall_t0) / 1e9,
                )
                free_windows_summary.append(
                    {
                        "window_label": f"{first_page:03d}",
                        "first_page": first_page,
                        "identifier_page": int(win_spec["identifier_page"]),
                        "window_json_sha256": win_sha,
                        "finish_reason": details.get("finish_reason"),
                        "num_pages_out": details.get("num_pages_out"),
                        "expected_pages": details.get("expected_pages"),
                        "eos_excluded_verified": eos_absent,
                        "window_token_count": len(emitted_ids),
                        "window_token_ids_sha256": emitted_sha,
                        "matches_wp0016_native_tokens": (emitted_ids == nat_anchor_ids),
                        "matches_wp0016_carbon_tokens": (emitted_ids == car_anchor_ids),
                        "endpoint_parity": endpoint_parity,
                        "free_field": {k: v for k, v in free_field.items() if k != "free_prefix_tokens"},
                        "_free_prefix_tokens": free_field.get("free_prefix_tokens"),
                        "timing": free_metrics,
                        "effective_prefill_dispatch": details.get("effective_prefill_dispatch"),
                        "cache_telemetry": details.get("cache_telemetry"),
                        "switch_counter_delta": details.get("switch_counter_delta"),
                        "vram": details.get("vram"),
                    }
                )

        ordinary_two_window_s = sum(w["timing"]["ordinary_engine_read_s"] for w in free_windows_summary)
        ordinary_timing_doc = {
            "mode": mode,
            "canonical_mode": resolved.canonical_name,
            "switch_bits": resolved.switch_config.bits,
            "implementation": resolved.implementation,
            "observer_kind": eng.info.get("observer_kind"),
            "ordinary_window_seconds": [w["timing"]["ordinary_engine_read_s"] for w in free_windows_summary],
            "ordinary_two_window_sum_s": ordinary_two_window_s,
            "windows": [
                {k: v for k, v in w.items() if not k.startswith("_")}
                for w in free_windows_summary
            ],
        }
        publish(free_dir / "ordinary-timing.json", ordinary_timing_doc)

        # =====================================================================
        # PHASE 2: Separate Serial-Decode Teacher-Forced BPE Span-Logit Probes
        # =====================================================================
        probe_dir = seg_dir / "probe"
        probe_dir.mkdir(parents=True, exist_ok=False)
        probe_windows_summary = []

        with pdfium_mod.PdfDocument(pdf_bytes) as doc:
            for win_spec, locator, free_w in zip(a1_obj["windows"], locators, free_windows_summary):
                first_page = int(win_spec["first_page"])
                first0 = first_page - 1
                last0 = min(first0 + eng.window, len(doc))
                p_batch = astra_inputs(doc, first0, last0, request)
                try:
                    images = [r["image"] for r in p_batch]
                    call_kwargs = protocol.build_call_kwargs(len(images))

                    forced_passes = []
                    for rep_idx in range(forced_repeats):
                        p_res = run_teacher_forced_window_probe(
                            engine_hooks=hooks,
                            images=images,
                            locator=locator,
                            prefix_tokens=locator["native_prefix_tokens"],
                            prefix_label="forced_native" if rep_idx == 0 else f"forced_native_repeat_{rep_idx + 1}",
                            call_kwargs=call_kwargs,
                            prompt_text=protocol.PROMPT,
                        )
                        forced_passes.append(p_res)

                    free_prefix_tokens = free_w["_free_prefix_tokens"]
                    free_probe = None
                    # Always execute an explicit free_running prefix replay on window 037
                    # (and on 019 whenever the free prefix diverged from native).
                    if free_prefix_tokens is not None and (
                        first_page == 37 or not free_w["free_field"]["prefix_identical_to_native"]
                    ):
                        free_probe = run_teacher_forced_window_probe(
                            engine_hooks=hooks,
                            images=images,
                            locator=locator,
                            prefix_tokens=free_prefix_tokens,
                            prefix_label="free_running",
                            call_kwargs=call_kwargs,
                            prompt_text=protocol.PROMPT,
                        )

                    effective_free_probe_for_margin = (
                        free_probe
                        if free_probe is not None
                        else (forced_passes[0] if free_w["free_field"]["prefix_identical_to_native"] else None)
                    )
                    offline_margin = evaluate_offline_margin_flag(
                        free_w["free_field"], effective_free_probe_for_margin
                    )
                finally:
                    for r in p_batch:
                        r["image"].close()

                probe_doc = {
                    "mode": mode,
                    "canonical_mode": resolved.canonical_name,
                    "switch_bits": resolved.switch_config.bits,
                    "window_label": f"{first_page:03d}",
                    "first_page": first_page,
                    "identifier_page": int(win_spec["identifier_page"]),
                    "locator": {k: v for k, v in locator.items() if k != "native_prefix_tokens"},
                    "forced_native_passes": forced_passes,
                    "free_running_probe": free_probe,
                    "free_prefix_reused_forced_native_for_margin": (
                        free_probe is None and bool(free_w["free_field"]["prefix_identical_to_native"])
                    ),
                    "history_shift_D_free_minus_D_native_guarded_nats": (
                        (
                            free_probe["D_native_minus_carbon_guarded_nats"]
                            - forced_passes[0]["D_native_minus_carbon_guarded_nats"]
                        )
                        if (
                            free_probe is not None
                            and free_probe["D_native_minus_carbon_guarded_nats"] is not None
                            and forced_passes[0]["D_native_minus_carbon_guarded_nats"] is not None
                        )
                        else (0.0 if free_w["free_field"]["prefix_identical_to_native"] else None)
                    ),
                    "offline_margin_flag_diagnostic": offline_margin,
                }
                probe_sha = publish(probe_dir / f"window-{first_page:03d}-probe.json", probe_doc)
                probe_windows_summary.append(
                    {
                        "window_label": f"{first_page:03d}",
                        "first_page": first_page,
                        "identifier_page": int(win_spec["identifier_page"]),
                        "probe_json_sha256": probe_sha,
                        "forced_native_D_passes_guarded_nats": [
                            p["D_native_minus_carbon_guarded_nats"] for p in forced_passes
                        ],
                        "forced_native_D_pass1_raw_nats": forced_passes[0]["D_native_minus_carbon_raw_nats"],
                        "forced_native_ell_native_id_guarded_nats": forced_passes[0]["branches"][0]["ell_common_boundary_guarded_nats"],
                        "forced_native_ell_carbon_id_guarded_nats": forced_passes[0]["branches"][1]["ell_common_boundary_guarded_nats"],
                        "forced_native_divergence_margin_guarded_fp32": forced_passes[0]["divergence_step_summary"]["guarded_margin_top1_top2_fp32"],
                        "forced_native_early_divergence_telemetry": forced_passes[0]["early_pre_id_divergence_telemetry"],
                        "free_running_D_guarded_nats": (
                            free_probe["D_native_minus_carbon_guarded_nats"]
                            if free_probe is not None
                            else (
                                forced_passes[0]["D_native_minus_carbon_guarded_nats"]
                                if free_w["free_field"]["prefix_identical_to_native"]
                                else None
                            )
                        ),
                        "free_running_probe_executed_separately": (free_probe is not None),
                        "history_shift_D_free_minus_D_native_guarded_nats": probe_doc[
                            "history_shift_D_free_minus_D_native_guarded_nats"
                        ],
                        "probe_pass1_timing": forced_passes[0]["probe_timing"],
                        "offline_margin_flag_diagnostic": offline_margin,
                    }
                )

    seg_summary = {
        "mode": mode,
        "canonical_mode": resolved.canonical_name,
        "family": resolved.family,
        "implementation": resolved.implementation,
        "is_genuine_endpoint": (resolved.implementation != "ablation_engine"),
        "observer_kind": eng.info.get("observer_kind"),
        "switch_bits": resolved.switch_config.bits,
        "switches_by_id": resolved.switch_config.by_id,
        "removed_switches": list(resolved.removed_switches),
        "added_switches": list(resolved.added_switches),
        "load_elapsed_s": load_elapsed_s,
        "warmup_count": len(warmup_records),
        "ordinary_window_seconds": [w["timing"]["ordinary_engine_read_s"] for w in free_windows_summary],
        "ordinary_two_window_sum_s": ordinary_two_window_s,
        "free_ids": [w["free_field"]["observed_id"] for w in free_windows_summary],
        "all_free_fields_aligned": all(bool(w["free_field"]["aligned"]) for w in free_windows_summary),
        "all_windows_finished_stop": all(w["finish_reason"] == "stop" for w in free_windows_summary),
        "all_windows_eos_excluded": all(bool(w["eos_excluded_verified"]) for w in free_windows_summary),
        "free_windows": [{k: v for k, v in w.items() if not k.startswith("_")} for w in free_windows_summary],
        "probe_windows": probe_windows_summary,
    }
    publish(seg_dir / "segment-summary.json", seg_summary)
    return seg_summary


def main(seg_dir: Path) -> None:
    attempted = clock()
    try:
        execute_a1_segment(seg_dir)
    except Exception as exc:
        publish(
            seg_dir / "failure.json",
            dict(
                status="failed",
                elapsed_s=(clock() - attempted) / 1e9,
                error=repr(exc),
                traceback=traceback.format_exc(),
            ),
        )
        raise


if __name__ == "__main__":
    main(Path(sys.argv[1]))
