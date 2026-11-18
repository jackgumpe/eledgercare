"""Passive CPU-only telemetry, static-KV contract reconstructor, and WP-0016 gate processor.

Operates strictly on published JSON artifacts and public/escrow truth files without
modifying docs/research/WP-0016/engine/g0.py or any WP-0015 / workers/local_ocr file.
Never imports torch or queries CUDA/nvidia-smi. G1 and G2 engine implementations remain
unreleased and unactivated; only passive scoring and gate-threshold verification are defined.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EVAL_WP15 = ROOT / "docs/evaluation/WP-0015"
ASTRA_WP15 = ROOT / "docs/research/WP-0015/astra"
if str(EVAL_WP15) not in sys.path:
    sys.path.insert(0, str(EVAL_WP15))
if str(ASTRA_WP15) not in sys.path:
    sys.path.insert(0, str(ASTRA_WP15))

from formats import BLOCK as STRICT_BLOCK_RE, digest, native_page, publish
import score as frozen_scorer

EXPECTED_SCORER_SHA256 = "1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7"
WINDOWS_A_CLOCK_S = 15.6546455

# Public title<LEVELn> sensitivity rule from commit 0186467670074761a777602d77b53deff3451300
TITLE_LEVEL_RE = re.compile(
    r"(<BLOCK>title)<LEVEL(\d+)>(?=\s*\[\s*\d+,\s*\d+,\s*\d+,\s*\d+\s*\]<FORK>)"
)
RAW_BLOCK_OPEN_RE = re.compile(r"<BLOCK>")
RAW_FORK_RE = re.compile(r"<FORK>")

# Pinned Unlimited-OCR-2 (0480966938291445591f69f08a13b041c073a96a) static KV geometry
PINNED_CACHE_GEOMETRY = {
    "num_layers": 12,
    "num_kv_heads": 10,
    "head_dim": 128,
    "kv_dtype_bytes": 2,  # bfloat16
    "sparse_block_size": 32,
    "sparse_index_dim": 128,
    "index_dtype_bytes": 4,  # float32
    "init_min_cap_tok": 4096,
    "init_extra_cap_tok": 2048,
    "max_cap_pad_tok": 32,
    "tokens_per_page_cap": 8000,
    "max_length": 131072,
}

MIB = 1024 * 1024


def verify_scorer_pin(score_py_path: Path = EVAL_WP15 / "score.py") -> str:
    actual = hashlib.sha256(score_py_path.read_bytes()).hexdigest()
    if actual != EXPECTED_SCORER_SHA256:
        raise ValueError(f"Frozen score.py SHA-256 mismatch: expected {EXPECTED_SCORER_SHA256}, got {actual}")
    return actual


def static_cache_bytes_for_cap(cap_tok: int, batch_size: int = 1, geom: dict = PINNED_CACHE_GEOMETRY) -> dict:
    L = int(geom["num_layers"])
    nkv = int(geom["num_kv_heads"])
    hd = int(geom["head_dim"])
    kv_b = int(geom["kv_dtype_bytes"])
    bs = int(geom["sparse_block_size"])
    idx_d = int(geom["sparse_index_dim"])
    idx_b = int(geom["index_dtype_bytes"])
    if cap_tok % bs != 0:
        raise ValueError(f"cap_tok ({cap_tok}) must be a multiple of block_size ({bs})")
    cap_blk = cap_tok // bs
    k_bytes = L * batch_size * nkv * cap_tok * hd * kv_b
    v_bytes = L * batch_size * nkv * cap_tok * hd * kv_b
    idx_k_bytes = L * batch_size * cap_tok * idx_d * idx_b
    k_bar_bytes = L * batch_size * cap_blk * idx_d * idx_b
    total = k_bytes + v_bytes + idx_k_bytes + k_bar_bytes
    return {
        "batch_size": batch_size,
        "cap_tok": cap_tok,
        "cap_blk": cap_blk,
        "k_buf_bytes": k_bytes,
        "v_buf_bytes": v_bytes,
        "dash_idx_k_bytes": idx_k_bytes,
        "k_bar_buf_bytes": k_bar_bytes,
        "total_bytes": total,
        "total_mib": round(total / MIB, 6),
    }


def reconstruct_window_static_kv(window_obj: dict, load_obj: dict | None = None) -> dict:
    """Reconstruct static KV trajectory and classify observable vs unverifiable contracts for one window."""
    mode = window_obj.get("engine_mode") or ("carbon_bf16" if "static_cache_reallocations" in window_obj else "native")
    vram = window_obj.get("vram") or {}
    alloc_peak = int(vram.get("cuda_max_allocated_bytes", 0))
    res_peak = int(vram.get("cuda_max_reserved_bytes", 0))
    weight_alloc = int((load_obj or {}).get("weight_allocated_bytes_after_pack", 0)) or None
    weight_res = int((load_obj or {}).get("weight_reserved_bytes_after_pack", 0)) or None

    base_mem = {
        "engine_mode": mode,
        "first_page": window_obj.get("first_page"),
        "pages": window_obj.get("pages"),
        "allocator_max_allocated_bytes": alloc_peak,
        "allocator_max_allocated_mib": round(alloc_peak / MIB, 4),
        "allocator_max_reserved_bytes": res_peak,
        "allocator_max_reserved_mib": round(res_peak / MIB, 4),
        "model_weight_allocated_bytes": weight_alloc,
        "model_weight_reserved_bytes": weight_res,
        "transient_and_cache_peak_over_weights_bytes": (alloc_peak - weight_alloc) if weight_alloc is not None else None,
        "transient_and_cache_peak_over_weights_mib": (
            round((alloc_peak - weight_alloc) / MIB, 4) if weight_alloc is not None else None
        ),
    }

    if mode == "native":
        return {
            **base_mem,
            "has_static_kv_cache": False,
            "cache_implementation": "transformers.DynamicCache (per-step torch.cat reallocation)",
            "observable_fields": [
                "prompt_len",
                "forward_count",
                "window_token_ids",
                "kernel_path",
                "triton_starts",
                "triton_none_returns",
                "dense_starts",
                "vram.cuda_max_allocated_bytes",
                "vram.cuda_max_reserved_bytes",
            ],
            "unverifiable_without_control_change": [
                "native post-load model weight-only allocator bytes (not emitted in load-native.json)",
                "per-step DynamicCache reallocation byte counts",
                "non-allocator CUDA context / cuBLASLt / WDDM device bytes inside window-*.json",
            ],
        }

    geom = PINNED_CACHE_GEOMETRY
    bs = geom["sparse_block_size"]
    s0 = int(window_obj["prompt_len"])
    pages = int(window_obj["pages"])
    fwd = int(window_obj["forward_count"])
    burst_extra = int(window_obj.get("burst_extra_forwards", 0))
    logged_reallocs = int(window_obj["static_cache_reallocations"])
    gen_tokens = len(window_obj.get("window_token_ids") or [])

    max_new = geom["tokens_per_page_cap"] * pages
    max_tokens_eff = min(max_new, max(0, geom["max_length"] - s0))
    max_cap_arg = max(s0 + 1, s0 + max_tokens_eff + geom["max_cap_pad_tok"])
    init_cap_raw = min(max_cap_arg, max(geom["init_min_cap_tok"], s0 + geom["init_extra_cap_tok"], s0 + 1))
    init_cap_blk = -(-init_cap_raw // bs)
    init_cap_tok = init_cap_blk * bs

    decode_forwards = max(0, fwd - 1)
    cap_tok = init_cap_tok
    sim_reallocs = 0
    seq_len = s0
    for _ in range(decode_forwards):
        seq_len += 1
        if seq_len > cap_tok:
            new_tok = max(seq_len, cap_tok * 2)
            cap_tok = (-(-new_tok // bs)) * bs
            sim_reallocs += 1

    init_footprint = static_cache_bytes_for_cap(init_cap_tok, batch_size=1, geom=geom)
    final_footprint = static_cache_bytes_for_cap(cap_tok, batch_size=1, geom=geom)
    return {
        **base_mem,
        "has_static_kv_cache": True,
        "cache_implementation": "StaticDashCache (per-window after DynamicCache prefill; B=1)",
        "prompt_len": s0,
        "generated_tokens_returned": gen_tokens,
        "executed_forwards": fwd,
        "decode_forwards_appended_to_cache": decode_forwards,
        "burst_extra_post_eos_forwards_written": burst_extra,
        "final_kv_seq_len_written": seq_len,
        "logged_static_cache_reallocations": logged_reallocs,
        "reconstructed_static_cache_reallocations": sim_reallocs,
        "reallocation_formula_matches_logged": (logged_reallocs == sim_reallocs),
        "init_static_cache_footprint": init_footprint,
        "final_static_cache_footprint": final_footprint,
        "observable_fields": [
            "static_cache_reallocations",
            "prompt_len",
            "forward_count",
            "burst_extra_forwards",
            "window_token_ids",
            "prefill_grouped_mm_layer_calls",
            "prefill_moe_fallback_layer_calls",
            "vram.cuda_max_allocated_bytes",
            "vram.cuda_max_reserved_bytes",
            "load.weight_allocated_bytes_after_pack",
            "load.weight_reserved_bytes_after_pack",
        ],
        "unverifiable_without_control_change": [
            "live tensor data_ptr() addresses across steps (only implied within-window when static_cache_reallocations == 0; not persistent across windows in G0 because StaticDashCache is re-allocated per 3-page window)",
            "exact split of transient_and_cache_peak_over_weights between prefill DynamicCache/vision activations and decode StaticDashCache/scratch (single reset_peak_memory_stats span per window)",
            "transient +420 MiB per-layer MoE pack spike during CarbonEngine.__init__ (cleared by empty_cache() + reset_peak_memory_stats() before window-001)",
            "sub-5s WDDM non-allocator device memory peak without coordinator external high-rate sampler",
        ],
    }


def inspect_raw_headers_and_tables(
    raw_pages: list[dict],
    prediction: dict,
    truth: dict | None = None,
) -> dict:
    """Inspect per-page raw output for malformed <BLOCK> headers and invented tables."""
    strict_malformed_total = 0
    adapted_malformed_total = 0
    title_level_headers_total = 0
    bad_box_headers_total = 0
    corrupt_syntax_headers_total = 0
    stray_fork_total = 0
    page_details = []

    for rp in raw_pages:
        page_num = int(rp["page"])
        raw = rp["raw_output"]
        body = raw.removeprefix("<PAGE>")
        n_block_opens = len(RAW_BLOCK_OPEN_RE.findall(body))
        n_forks = len(RAW_FORK_RE.findall(body))

        strict_matches = list(STRICT_BLOCK_RE.finditer(body))
        title_lvl_matches = list(TITLE_LEVEL_RE.finditer(body))

        adapted_body = TITLE_LEVEL_RE.sub(r"\1", body)
        adapted_matches = list(STRICT_BLOCK_RE.finditer(adapted_body))

        bad_boxes_strict = 0
        for m in strict_matches:
            vals = [int(v) for v in m.groups()[1:]]
            if not (max(vals) <= 999 and vals[0] < vals[2] and vals[1] < vals[3]):
                bad_boxes_strict += 1

        bad_boxes_adapted = 0
        for m in adapted_matches:
            vals = [int(v) for v in m.groups()[1:]]
            if not (max(vals) <= 999 and vals[0] < vals[2] and vals[1] < vals[3]):
                bad_boxes_adapted += 1

        # Every <BLOCK> in adapted_body that still fails STRICT_BLOCK_RE is syntax-corrupt
        corrupt_syntax = max(0, n_block_opens - len(adapted_matches))
        # Under strict parser, both corrupt_syntax, title<LEVELn>, and out-of-bounds/inverted boxes fail valid header criteria
        strict_malformed = max(0, n_block_opens - len(strict_matches)) + bad_boxes_strict
        adapted_malformed = corrupt_syntax + bad_boxes_adapted
        stray_forks = max(0, n_forks - n_block_opens)

        strict_malformed_total += strict_malformed
        adapted_malformed_total += adapted_malformed
        title_level_headers_total += len(title_lvl_matches)
        bad_box_headers_total += bad_boxes_adapted
        corrupt_syntax_headers_total += corrupt_syntax
        stray_fork_total += stray_forks

        page_details.append(
            {
                "page": page_num,
                "block_open_count": n_block_opens,
                "fork_count": n_forks,
                "strict_valid_box_headers": len(strict_matches) - bad_boxes_strict,
                "title_level_headers": len(title_lvl_matches),
                "out_of_bounds_or_inverted_boxes": bad_boxes_adapted,
                "corrupt_syntax_headers": corrupt_syntax,
                "stray_forks": stray_forks,
                "strict_malformed_headers": strict_malformed,
                "adapted_malformed_headers": adapted_malformed,
            }
        )

    invented_info = None
    if truth is not None:
        pred_by_page = {int(p["page"]): p for p in prediction.get("pages", [])}
        invented_on_table_free = 0
        unmatched_on_table_pages = 0
        invented_pages = []
        for ref in truth["pages"]:
            pno = int(ref["page"])
            width, height = ref["width"], ref["height"]
            p_obj = pred_by_page.get(pno, {})
            valid_pred_tables = [
                t for t in p_obj.get("tables", []) if isinstance(t, dict) and frozen_scorer.valid_box(t.get("bbox"), width, height)
            ]
            ref_tables = ref.get("tables", [])
            if not ref_tables:
                if valid_pred_tables:
                    invented_on_table_free += len(valid_pred_tables)
                    invented_pages.append({"page": pno, "kind": "table_free_page", "count": len(valid_pred_tables)})
            else:
                pairs = sorted(
                    (
                        (-frozen_scorer.iou(rt["bbox"], pt["bbox"]), ti, pi)
                        for ti, rt in enumerate(ref_tables)
                        for pi, pt in enumerate(valid_pred_tables)
                    ),
                    key=lambda item: item,
                )
                matched_t, used_p = set(), set()
                for neg_iou, ti, pi in pairs:
                    if -neg_iou >= 0.5 and ti not in matched_t and pi not in used_p:
                        matched_t.add(ti)
                        used_p.add(pi)
                unmatched = len(valid_pred_tables) - len(used_p)
                if unmatched > 0:
                    unmatched_on_table_pages += unmatched
                    invented_pages.append({"page": pno, "kind": "unmatched_extra_table", "count": unmatched})
        invented_info = {
            "invented_tables_on_table_free_pages": invented_on_table_free,
            "unmatched_predicted_tables_on_table_pages": unmatched_on_table_pages,
            "total_invented_tables": invented_on_table_free + unmatched_on_table_pages,
            "pages_with_invented_tables": invented_pages,
        }

    return {
        "strict_malformed_headers": strict_malformed_total,
        "adapted_malformed_headers": adapted_malformed_total,
        "title_level_headers": title_level_headers_total,
        "out_of_bounds_or_inverted_boxes": bad_box_headers_total,
        "corrupt_syntax_headers": corrupt_syntax_headers_total,
        "stray_forks": stray_fork_total,
        "invented_tables": invented_info,
        "per_page": page_details,
    }


def build_title_adapted_prediction(prediction: dict, raw_pages: list[dict]) -> dict:
    raw_by_page = {int(r["page"]): r for r in raw_pages}
    adapted_pages = []
    for page in prediction["pages"]:
        pno = int(page["page"])
        rp = raw_by_page[pno]
        adapted_raw = TITLE_LEVEL_RE.sub(r"\1", rp["raw_output"])
        proj = native_page(adapted_raw, rp["points"])
        adapted_pages.append({**page, **proj})
    return {**prediction, "pages": adapted_pages}


def four_way_critical_transitions(control_score: dict, trial_score: dict) -> dict:
    """Compute four-way critical transitions and separate unflagged critical regressions/repairs."""
    ctrl_map = {c["at"]: c for p in control_score["pages"] for c in p["critical"]}
    repaired = []
    regressions = []
    same_error = []
    changed_error = []
    newly_unflagged = []
    repaired_unflagged = []

    for p in trial_score["pages"]:
        for cur in p["critical"]:
            prev = ctrl_map[cur["at"]]
            prev_unflagged_err = (not prev["correct"]) and (not prev["flagged"])
            cur_unflagged_err = (not cur["correct"]) and (not cur["flagged"])

            if (not prev_unflagged_err) and cur_unflagged_err:
                newly_unflagged.append(
                    {
                        "at": cur["at"],
                        "expected": cur["expected"],
                        "control_observed": prev["observed"],
                        "control_correct": prev["correct"],
                        "control_flagged": prev["flagged"],
                        "trial_observed": cur["observed"],
                        "trial_flagged": cur["flagged"],
                    }
                )
            elif prev_unflagged_err and (not cur_unflagged_err):
                repaired_unflagged.append(
                    {
                        "at": cur["at"],
                        "expected": cur["expected"],
                        "control_observed": prev["observed"],
                        "trial_observed": cur["observed"],
                        "trial_correct": cur["correct"],
                        "trial_flagged": cur["flagged"],
                    }
                )

            entry = {
                "at": cur["at"],
                "expected": cur["expected"],
                "control_observed": prev["observed"],
                "trial_observed": cur["observed"],
                "control_flagged": prev["flagged"],
                "trial_flagged": cur["flagged"],
            }
            if prev["correct"] and not cur["correct"]:
                regressions.append(entry)
            elif (not prev["correct"]) and cur["correct"]:
                repaired.append(entry)
            elif not cur["correct"]:
                if (prev["observed"], prev["flagged"]) == (cur["observed"], cur["flagged"]):
                    same_error.append(entry)
                else:
                    changed_error.append(entry)

    return {
        "counts": {
            "total_critical": sum(len(p["critical"]) for p in trial_score["pages"]),
            "repaired": len(repaired),
            "new_error_regressions": len(regressions),
            "same_error": len(same_error),
            "changed_error": len(changed_error),
            "net_critical_recovery": len(repaired) - len(regressions),
            "newly_unflagged_critical_errors": len(newly_unflagged),
            "repaired_unflagged_critical_errors": len(repaired_unflagged),
            "net_unflagged_critical_recovery": len(repaired_unflagged) - len(newly_unflagged),
        },
        "repaired": repaired,
        "new_error_regressions": regressions,
        "changed_error": changed_error,
        "newly_unflagged_critical_errors": newly_unflagged,
        "repaired_unflagged_critical_errors": repaired_unflagged,
    }


def score_dual_parsers(truth: dict, prediction: dict, raw_pages: list[dict]) -> dict:
    verify_scorer_pin()
    # Verify published prediction matches unmodified formats.native_page on raw_pages
    for page, rp in zip(prediction["pages"], raw_pages):
        if int(page["page"]) != int(rp["page"]):
            raise ValueError("Mismatched page order between prediction.json and raw-*.json")
        recomputed = native_page(rp["raw_output"], rp["points"])
        if {k: page[k] for k in ("text", "spans", "tables")} != recomputed:
            raise ValueError(f"prediction.json page {page['page']} disagrees with formats.native_page(raw)")

    adapted_pred = build_title_adapted_prediction(prediction, raw_pages)
    strict_sc = frozen_scorer.score(truth, prediction)
    adapted_sc = frozen_scorer.score(truth, adapted_pred)
    return {
        "strict_native_page": strict_sc,
        "title_level_adapted": adapted_sc,
    }


def compare_dual_parsers(control_dual: dict, trial_dual: dict) -> dict:
    out = {}
    for parser_name in ("strict_native_page", "title_level_adapted"):
        c_sc = control_dual[parser_name]
        t_sc = trial_dual[parser_name]
        comp = frozen_scorer.compare(c_sc, t_sc)
        trans = four_way_critical_transitions(c_sc, t_sc)
        out[parser_name] = {
            "control_counts": c_sc["counts"],
            "trial_counts": t_sc["counts"],
            "scorer_compare": comp,
            "four_way_critical": trans,
        }
    return out


def compute_windows_crossover(
    truth: dict,
    windows_prediction: dict,
    neural_dual_scores: dict,
    *,
    neural_elapsed_s: float,
    windows_elapsed_s: float = WINDOWS_A_CLOCK_S,
) -> dict:
    """Compute four-way critical transitions vs frozen Windows prediction and signed net recovery/s."""
    verify_scorer_pin()
    win_sc = frozen_scorer.score(truth, windows_prediction)
    extra_neural_s = neural_elapsed_s - windows_elapsed_s
    by_parser = {}
    for parser_name in ("strict_native_page", "title_level_adapted"):
        n_sc = neural_dual_scores[parser_name]
        trans = four_way_critical_transitions(win_sc, n_sc)
        net_total = trans["counts"]["net_critical_recovery"]
        net_unflagged = trans["counts"]["net_unflagged_critical_recovery"]
        by_parser[parser_name] = {
            "windows_counts": win_sc["counts"],
            "neural_counts": n_sc["counts"],
            "four_way_critical_vs_windows": trans,
            "extra_neural_seconds": extra_neural_s,
            "signed_net_critical_recovery_per_extra_neural_s": (
                net_total / extra_neural_s if extra_neural_s > 0 else None
            ),
            "signed_net_unflagged_recovery_per_extra_neural_s": (
                net_unflagged / extra_neural_s if extra_neural_s > 0 else None
            ),
        }
    return {
        "windows_elapsed_s": windows_elapsed_s,
        "neural_elapsed_s": neural_elapsed_s,
        "extra_neural_seconds": extra_neural_s,
        "parsers": by_parser,
    }


def compute_repeat_spread(elapsed_samples_s: list[float]) -> dict:
    if not elapsed_samples_s:
        return {"n": 0, "min_s": None, "max_s": None, "mean_s": None, "spread_s": None, "rel_spread": None}
    mn = min(elapsed_samples_s)
    mx = max(elapsed_samples_s)
    mean = sum(elapsed_samples_s) / len(elapsed_samples_s)
    spread = mx - mn
    return {
        "n": len(elapsed_samples_s),
        "samples_s": list(elapsed_samples_s),
        "min_s": mn,
        "max_s": mx,
        "mean_s": mean,
        "spread_s": spread,
        "rel_spread": (spread / mean) if mean > 0 else None,
    }


def evaluate_gate_criteria(
    gate: str,
    *,
    dual_comparison: dict,
    peak_allocator_mib: float,
    peak_device_mib: float | None,
    malformed_headers_strict: int = 0,
    a_speedup_vs_g0: float | None = None,
    a_time_savings_s: float | None = None,
    control_spread_s: float | None = None,
    grammar_failures: int = 0,
    static_cache_reallocations: int = 0,
    vs_g1_dual_comparison: dict | None = None,
    graph_replays_verified: bool = False,
) -> dict:
    """Evaluate numerical WP-0016 gate pass/fail criteria without running any model."""
    parsers = ("strict_native_page", "title_level_adapted")
    complete_ok = all(dual_comparison[p]["scorer_compare"]["complete_matched_pair"] for p in parsers)
    zero_new_unflagged = all(
        dual_comparison[p]["four_way_critical"]["counts"]["newly_unflagged_critical_errors"] == 0 for p in parsers
    )
    zero_new_wrong_src = all(
        len(dual_comparison[p]["scorer_compare"]["new_wrong_source_links"]) == 0 for p in parsers
    )

    def cer_ok(limit: float) -> bool:
        for p in parsers:
            d = dual_comparison[p]["scorer_compare"]["delta"]["cer"]
            if d is not None and d > limit + 1e-12:
                return False
        return True

    def cell_ok(floor: float) -> bool:
        for p in parsers:
            d = dual_comparison[p]["scorer_compare"]["delta"]["cell_accuracy"]
            if d is not None and d < floor - 1e-12:
                return False
        return True

    def mem_ok(ceiling_mib: float) -> tuple[bool, dict]:
        alloc_pass = peak_allocator_mib <= ceiling_mib
        dev_pass = (peak_device_mib <= ceiling_mib) if peak_device_mib is not None else False
        return (
            alloc_pass and dev_pass,
            {
                "ceiling_mib": ceiling_mib,
                "peak_allocator_mib": peak_allocator_mib,
                "allocator_within_ceiling": alloc_pass,
                "peak_device_mib": peak_device_mib,
                "device_within_ceiling": dev_pass,
                "external_device_peak_supplied": peak_device_mib is not None,
            },
        )

    if gate == "G0":
        m_pass, m_detail = mem_ok(10000.0)
        checks = {
            "all_original_pages_complete": complete_ok,
            "both_parsers_cer_delta_le_pos_0_01": cer_ok(0.01),
            "both_parsers_cell_delta_ge_neg_0_02": cell_ok(-0.02),
            "zero_newly_unflagged_critical_errors": zero_new_unflagged,
            "zero_new_wrong_source": zero_new_wrong_src,
            "peak_memory_le_10000_mib": m_pass,
        }
        return {"gate": "G0", "passed": all(checks.values()), "checks": checks, "memory": m_detail}

    if gate == "G1":
        m_pass, m_detail = mem_ok(10200.0)
        speed_ok = a_speedup_vs_g0 is not None and a_speedup_vs_g0 >= 0.98 - 1e-12
        checks = {
            "all_original_pages_complete": complete_ok,
            "zero_malformed_headers": malformed_headers_strict == 0,
            "both_parsers_cer_delta_le_0": cer_ok(0.0),
            "both_parsers_cell_delta_ge_0": cell_ok(0.0),
            "zero_newly_unflagged_critical_errors": zero_new_unflagged,
            "zero_new_wrong_source": zero_new_wrong_src,
            "peak_memory_le_10200_mib": m_pass,
            "a_speed_ge_0_98x_g0": speed_ok,
        }
        return {"gate": "G1", "passed": all(checks.values()), "checks": checks, "memory": m_detail}

    if gate == "G2":
        m_pass, m_detail = mem_ok(14500.0)
        speed_ok = a_speedup_vs_g0 is not None and a_speedup_vs_g0 >= 2.50 - 1e-12
        noise_ok = (
            a_time_savings_s is not None
            and control_spread_s is not None
            and a_time_savings_s > control_spread_s
        )
        no_g1_reg = False
        if vs_g1_dual_comparison is not None:
            no_g1_reg = all(
                (
                    vs_g1_dual_comparison[p]["scorer_compare"]["delta"]["cer"] is None
                    or vs_g1_dual_comparison[p]["scorer_compare"]["delta"]["cer"] <= 0.001 + 1e-12
                )
                and vs_g1_dual_comparison[p]["four_way_critical"]["counts"]["new_error_regressions"] == 0
                and vs_g1_dual_comparison[p]["four_way_critical"]["counts"]["newly_unflagged_critical_errors"] == 0
                for p in parsers
            )
        checks = {
            "all_original_pages_complete": complete_ok,
            "both_parsers_cer_delta_le_pos_0_001": cer_ok(0.001),
            "both_parsers_cell_delta_ge_neg_0_005": cell_ok(-0.005),
            "zero_newly_unflagged_critical_errors": zero_new_unflagged,
            "no_text_or_critical_regression_vs_g1": no_g1_reg,
            "zero_grammar_failures": grammar_failures == 0,
            "zero_static_cache_reallocations": static_cache_reallocations == 0,
            "cuda_graph_capture_and_replay_verified": bool(graph_replays_verified),
            "peak_memory_le_14500_mib": m_pass,
            "a_speed_ge_2_50x_g0": speed_ok,
            "savings_exceed_control_noise": noise_ok,
        }
        return {"gate": "G2", "passed": all(checks.values()), "checks": checks, "memory": m_detail}

    raise ValueError(f"Unsupported gate: {gate!r}")


def audit_run_directory(run_dir: Path, truth_by_label: dict[str, Path] | None = None) -> dict:
    """Passively audit a completed G0 run directory on CPU without importing torch."""
    launch_meta = json.loads((run_dir / "launch.json").read_bytes()) if (run_dir / "launch.json").exists() else None
    proc_meta = json.loads((run_dir / "process.json").read_bytes()) if (run_dir / "process.json").exists() else None

    segments_summary = []
    docs_by_label_mode: dict[tuple[str, str], list[dict]] = {}

    for seg_dir in sorted(run_dir.glob("segment-*")):
        seg_proc = (
            json.loads((seg_dir / "segment-process.json").read_bytes())
            if (seg_dir / "segment-process.json").exists()
            else None
        )
        loads = {lp.name: json.loads(lp.read_bytes()) for lp in sorted(seg_dir.glob("load-*.json"))}
        load_obj = next(iter(loads.values()), None)
        failures = [fp.name for fp in sorted(seg_dir.glob("failure*.json"))]
        doc_entries = []

        for sub in sorted(seg_dir.iterdir()):
            if not sub.is_dir() or sub.name == "cache":
                continue
            if (sub / "failure.json").exists():
                failures.append(f"{sub.name}/failure.json")
            if not (sub / "timing.json").exists():
                continue
            timing = json.loads((sub / "timing.json").read_bytes())
            pred_bytes = (sub / "prediction.json").read_bytes()
            if digest(pred_bytes) != timing["prediction_sha256"]:
                raise ValueError(f"prediction.json digest mismatch in {sub}")
            pred = json.loads(pred_bytes)
            windows = [json.loads(w.read_bytes()) for w in sorted(sub.glob("window-*.json"))]
            raws = [json.loads(r.read_bytes()) for r in sorted(sub.glob("raw-*.json"))]
            kv_windows = [reconstruct_window_static_kv(w, load_obj=load_obj) for w in windows]
            req = timing["request"]
            lbl = req["label"]
            truth_obj = None
            if truth_by_label and lbl in truth_by_label and truth_by_label[lbl].exists():
                truth_obj = frozen_scorer.read(truth_by_label[lbl])
            hdr_tbl = inspect_raw_headers_and_tables(raws, pred, truth=truth_obj)
            dual_sc = score_dual_parsers(truth_obj, pred, raws) if truth_obj is not None else None

            entry = {
                "folder": str(sub),
                "label": lbl,
                "mode": req["mode"],
                "warmup": bool(req["warmup"]),
                "pages": int(req["pages"]),
                "complete_pages": int(timing["complete_pages"]),
                "ready_wall_elapsed_s": float(timing["elapsed_s"]),
                "first_page_s": float(timing["first_page_s"]),
                "peak_window_allocator_allocated_mib": max(
                    (w["allocator_max_allocated_mib"] for w in kv_windows), default=0.0
                ),
                "peak_window_allocator_reserved_mib": max(
                    (w["allocator_max_reserved_mib"] for w in kv_windows), default=0.0
                ),
                "total_static_cache_reallocations": sum(
                    w.get("logged_static_cache_reallocations", 0) for w in kv_windows
                ),
                "headers_and_tables": hdr_tbl,
                "windows_telemetry": kv_windows,
                "dual_scores": dual_sc,
            }
            doc_entries.append(entry)
            if not req["warmup"]:
                docs_by_label_mode.setdefault((lbl, req["mode"]), []).append(entry)

        # Board-wide nvidia-smi samples recorded by launch.py (5s cadence caveat)
        seg_idx = seg_proc["segment"] if seg_proc else None
        seg_samples = [
            s for s in (proc_meta or {}).get("gpu_samples", []) if seg_idx is None or s.get("segment") == seg_idx
        ]
        pre_used = (seg_proc or {}).get("gpu_before_segment", {}).get("used_mib")
        post_used = (seg_proc or {}).get("gpu_after_segment", {}).get("used_mib")
        sampled_board_peak = max(
            [x for x in ([pre_used, post_used] + [s.get("used_mib") for s in seg_samples]) if x is not None],
            default=None,
        )
        segments_summary.append(
            {
                "segment_dir": seg_dir.name,
                "cold_loads": loads,
                "failures": failures,
                "gpu_before_segment": (seg_proc or {}).get("gpu_before_segment"),
                "gpu_after_segment": (seg_proc or {}).get("gpu_after_segment"),
                "sampled_board_used_peak_mib_5s_cadence": sampled_board_peak,
                "sampled_delta_over_pre_segment_mib": (
                    (sampled_board_peak - pre_used) if (sampled_board_peak is not None and pre_used is not None) else None
                ),
                "documents": doc_entries,
            }
        )

    assert "torch" not in sys.modules
    return {
        "run_dir": str(run_dir),
        "launch": launch_meta,
        "all_segments_completed": (proc_meta or {}).get("all_segments_completed"),
        "segments": segments_summary,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_dir", type=Path, help="Completed G0 run directory to passively audit on CPU")
    p.add_argument("--out", type=Path, required=True, help="Output JSON path for passive audit summary")
    args = p.parse_args()
    summary = audit_run_directory(args.run_dir.resolve())
    publish(args.out.resolve(), summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
