"""Deterministic Stage A1 4-endpoint × 2-window gate, causal score table, and Astra-rule selector.

Enforces mandatory whole-token-array, SHA-256, page-count, and EOS-exclusion parity across
ALL FOUR endpoint modes ('native', 'all_off', 'carbon_bf16', 'all_on') × BOTH 3-page windows
(8 complete endpoint windows) PLUS coordinator's external check_endpoints.py receipt BEFORE
computing any switch attribution or surgical candidate selection.

Uses instrument-matched 'all_off' and 'all_on' (wp0017_uniform_ablation_observer) as the
baselines for single-switch causal contrasts while cross-checking genuine 'native' and
'carbon_bf16' token parity and comparing ordinary implementation wall (including counters)
against raw kernel inference time.
"""
from __future__ import annotations

import argparse
import hashlib
from io import TextIOWrapper
from itertools import combinations
import json
import math
import os
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, TextIOWrapper):
        _stream.reconfigure(encoding="utf-8", errors=_stream.errors)

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from span_probe import token_ids_sha256
from switches import SWITCH_ORDER

A1_SUMMARY_SCHEMA = "eledgercare.wp0017.a1-summary/1"
DEFAULT_A1_MANIFEST = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0017/coordination/a1-inputs.json")

NUMERIC_FLOOR_NATS = 1e-5
EXPECTED_NATIVE_IDS = ("I08O1-388", "8OI10-774")
EXPECTED_CARBON_IDS = ("108O1-388", "80I10-774")
REQUIRED_ENDPOINT_ARMS = (
    ("native", "native", True),
    ("all_off", "native", False),
    ("carbon_bf16", "carbon_bf16", True),
    ("all_on", "carbon_bf16", False),
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write_json(path: Path, obj: dict) -> str:
    encoded = (json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".pending")
    with tmp.open("xb") as f:
        f.write(encoded)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)
    return _sha256_bytes(encoded)


def _finite_pair(vals) -> bool:
    return (
        isinstance(vals, (list, tuple))
        and len(vals) == 2
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in vals)
    )


def _extract_raw_kernel_pair(seg: dict) -> list[float] | None:
    top = seg.get("raw_kernel_infer_window_seconds")
    if _finite_pair(top):
        return [float(top[0]), float(top[1])]
    wins = seg.get("free_windows") or []
    if len(wins) == 2:
        vals = []
        for w in wins:
            t = w.get("timing") or {}
            rk = t.get("raw_kernel_infer_s")
            if rk is None and t.get("native_infer_ms") is not None:
                rk = float(t["native_infer_ms"]) / 1000.0
            vals.append(rk)
        if _finite_pair(vals):
            return [float(vals[0]), float(vals[1])]
    return None


def _extract_generate_pair(seg: dict) -> list[float] | None:
    top = seg.get("generate_window_seconds")
    if _finite_pair(top):
        return [float(top[0]), float(top[1])]
    wins = seg.get("free_windows") or []
    if len(wins) == 2:
        vals = [(w.get("timing") or {}).get("generate_time_s") for w in wins]
        if _finite_pair(vals):
            return [float(vals[0]), float(vals[1])]
    return None


def verify_external_endpoint_check(external_check: dict | None, a1_manifest: dict) -> dict:
    """Validate coordinator check_endpoints.py output (4 endpoint modes × 2 complete windows = 8 checks)."""
    required_modes = tuple(m for m, _, _ in REQUIRED_ENDPOINT_ARMS)
    expected_tok_counts: dict[tuple[str, int], int] = {}
    for w in a1_manifest["windows"]:
        fp = int(w["first_page"])
        nat_len = len(w["by_mode"]["native"]["token_ids"])
        car_len = len(w["by_mode"]["carbon_bf16"]["token_ids"])
        expected_tok_counts[("native", fp)] = nat_len
        expected_tok_counts[("all_off", fp)] = nat_len
        expected_tok_counts[("carbon_bf16", fp)] = car_len
        expected_tok_counts[("all_on", fp)] = car_len

    required_pairs = set(expected_tok_counts.keys())
    if external_check is None:
        return {
            "present": False,
            "passed": False,
            "verified_pairs": 0,
            "required_pairs": len(required_pairs),
            "required_modes": list(required_modes),
            "reason": "missing_external_endpoint_check",
        }

    checks = external_check.get("checks")
    if not isinstance(checks, list):
        return {
            "present": True,
            "passed": False,
            "verified_pairs": 0,
            "required_pairs": len(required_pairs),
            "required_modes": list(required_modes),
            "reason": "invalid_checks_list",
        }

    seen_pairs: set[tuple[str, int]] = set()
    bad_rows: list[dict] = []
    for row in checks:
        if not isinstance(row, dict):
            bad_rows.append({"error": "non_dict_row"})
            continue
        mode = str(row.get("mode", ""))
        fp_raw = row.get("first_page")
        if not isinstance(fp_raw, int) or isinstance(fp_raw, bool):
            bad_rows.append({"mode": mode, "error": "invalid_first_page"})
            continue
        pair = (mode, fp_raw)
        if pair not in expected_tok_counts or pair in seen_pairs:
            bad_rows.append({"mode": mode, "first_page": fp_raw, "error": "unexpected_or_duplicate_pair"})
            continue
        seen_pairs.add(pair)
        exp_len = expected_tok_counts[pair]
        errs = row.get("errors")
        if (
            not isinstance(errs, list)
            or len(errs) > 0
            or row.get("first_mismatch") is not None
            or row.get("tokens") != exp_len
            or row.get("expected_tokens") != exp_len
        ):
            bad_rows.append(
                {
                    "mode": mode,
                    "first_page": fp_raw,
                    "errors": errs,
                    "first_mismatch": row.get("first_mismatch"),
                    "tokens": row.get("tokens"),
                    "expected_tokens": row.get("expected_tokens"),
                }
            )

    missing_pairs = sorted(required_pairs - seen_pairs)
    passed = (
        external_check.get("passed") is True
        and len(checks) == len(required_pairs)
        and not missing_pairs
        and not bad_rows
    )
    reason = None
    if not passed:
        if external_check.get("passed") is not True:
            reason = "external_check_reported_failed"
        elif missing_pairs:
            reason = "external_check_missing_endpoint_windows"
        else:
            reason = "external_check_row_validation_failed"

    return {
        "present": True,
        "passed": passed,
        "verified_pairs": len(seen_pairs) - len(bad_rows),
        "required_pairs": len(required_pairs),
        "missing_pairs": [{"mode": m, "first_page": fp} for m, fp in missing_pairs],
        "failed_rows": bad_rows,
        "reason": reason,
    }


def verify_endpoint_anchors(
    segments_by_canon: dict[str, dict],
    a1_manifest: dict,
    *,
    external_endpoint_check: dict | None = None,
    require_external_endpoint_check: bool = True,
) -> dict:
    """Verify all 4 endpoint modes × 2 complete windows (8/8) + optional/required external check_endpoints.py."""
    expected_window_labels = [f"{int(w['first_page']):03d}" for w in a1_manifest["windows"]]
    expected_by_mode = {
        "native": [
            [int(t) for t in w["by_mode"]["native"]["token_ids"]]
            for w in a1_manifest["windows"]
        ],
        "carbon_bf16": [
            [int(t) for t in w["by_mode"]["carbon_bf16"]["token_ids"]]
            for w in a1_manifest["windows"]
        ],
    }
    expected_shas = {
        m: [token_ids_sha256(ids) for ids in wins]
        for m, wins in expected_by_mode.items()
    }

    checks = {}
    present_endpoint_arms = 0
    verified_endpoint_windows = 0
    missing_endpoint_arms: list[str] = []
    failed_present_arms: list[str] = []

    for arm_name, ref_mode, _is_genuine in REQUIRED_ENDPOINT_ARMS:
        seg = segments_by_canon.get(arm_name)
        if seg is None:
            checks[arm_name] = {"present": False, "reference_anchor": ref_mode}
            missing_endpoint_arms.append(arm_name)
            continue

        present_endpoint_arms += 1
        free_wins = seg.get("free_windows") or []
        win_count_ok = (len(free_wins) == len(expected_window_labels))
        win_ok_list = []

        for w_idx, free_w in enumerate(free_wins[: len(expected_window_labels)]):
            obs_sha = free_w.get("window_token_ids_sha256")
            exp_sha = expected_shas[ref_mode][w_idx]
            ep = free_w.get("endpoint_parity") or {}
            lbl_ok = (free_w.get("window_label") == expected_window_labels[w_idx])
            exact_arr = bool(ep.get("exact_token_array_match")) and (obs_sha == exp_sha)
            stop_ok = (free_w.get("finish_reason") == "stop")
            eos_ok = bool(free_w.get("eos_excluded_verified"))
            num_p = free_w.get("num_pages_out")
            exp_p = free_w.get("expected_pages")
            pages_ok = (num_p is None or num_p == 3) and (exp_p is None or exp_p == 3)
            w_pass = lbl_ok and exact_arr and stop_ok and eos_ok and pages_ok
            if w_pass:
                verified_endpoint_windows += 1
            win_ok_list.append(
                {
                    "window_label": free_w.get("window_label"),
                    "passed": w_pass,
                    "exact_token_array_match": exact_arr,
                    "observed_token_ids_sha256": obs_sha,
                    "expected_token_ids_sha256": exp_sha,
                    "finish_reason": free_w.get("finish_reason"),
                    "num_pages_out": num_p,
                    "expected_pages": exp_p,
                    "eos_excluded_verified": eos_ok,
                    "first_diff": ep.get("first_diff"),
                }
            )

        arm_pass = win_count_ok and len(win_ok_list) == len(expected_window_labels) and all(
            w["passed"] for w in win_ok_list
        )
        if not arm_pass:
            failed_present_arms.append(arm_name)
        checks[arm_name] = {
            "present": True,
            "reference_anchor": ref_mode,
            "implementation": seg.get("implementation"),
            "observer_kind": seg.get("observer_kind"),
            "passed": arm_pass,
            "windows": win_ok_list,
        }

    observer_equivalence = {}
    if checks.get("native", {}).get("present") and checks.get("all_off", {}).get("present"):
        nat_shas = [w["observed_token_ids_sha256"] for w in checks["native"]["windows"]]
        off_shas = [w["observed_token_ids_sha256"] for w in checks["all_off"]["windows"]]
        observer_equivalence["native_vs_all_off"] = {
            "genuine_observer": checks["native"]["observer_kind"],
            "ablation_observer": checks["all_off"]["observer_kind"],
            "identical_token_streams": (nat_shas == off_shas),
            "both_match_wp0016_anchor": bool(checks["native"]["passed"] and checks["all_off"]["passed"]),
        }
    if checks.get("carbon_bf16", {}).get("present") and checks.get("all_on", {}).get("present"):
        car_shas = [w["observed_token_ids_sha256"] for w in checks["carbon_bf16"]["windows"]]
        on_shas = [w["observed_token_ids_sha256"] for w in checks["all_on"]["windows"]]
        observer_equivalence["carbon_bf16_vs_all_on"] = {
            "genuine_observer": checks["carbon_bf16"]["observer_kind"],
            "ablation_observer": checks["all_on"]["observer_kind"],
            "identical_token_streams": (car_shas == on_shas),
            "both_match_wp0016_anchor": bool(checks["carbon_bf16"]["passed"] and checks["all_on"]["passed"]),
        }

    required_window_total = len(REQUIRED_ENDPOINT_ARMS) * len(expected_window_labels)
    cross_obs_ok = (
        observer_equivalence.get("native_vs_all_off", {}).get("identical_token_streams") is True
        and observer_equivalence.get("native_vs_all_off", {}).get("both_match_wp0016_anchor") is True
        and observer_equivalence.get("carbon_bf16_vs_all_on", {}).get("identical_token_streams") is True
        and observer_equivalence.get("carbon_bf16_vs_all_on", {}).get("both_match_wp0016_anchor") is True
    )
    internal_eight_ok = (
        present_endpoint_arms == len(REQUIRED_ENDPOINT_ARMS)
        and verified_endpoint_windows == required_window_total
        and not failed_present_arms
        and cross_obs_ok
    )

    ext_verdict = verify_external_endpoint_check(external_endpoint_check, a1_manifest)
    ext_gate_ok = ext_verdict["passed"] if (require_external_endpoint_check or external_endpoint_check is not None) else True
    gate_passed = bool(internal_eight_ok and ext_gate_ok)

    return {
        "anchor_gate_passed": gate_passed,
        "internal_eight_window_gate_passed": internal_eight_ok,
        "external_endpoint_check_required": bool(require_external_endpoint_check),
        "external_endpoint_check": ext_verdict,
        "present_endpoint_arms": present_endpoint_arms,
        "required_endpoint_arms": len(REQUIRED_ENDPOINT_ARMS),
        "verified_endpoint_windows": verified_endpoint_windows,
        "required_endpoint_windows": required_window_total,
        "missing_endpoint_arms": missing_endpoint_arms,
        "failed_present_arms": failed_present_arms,
        "arms": checks,
        "observer_equivalence": observer_equivalence,
    }


def _extract_probe_passes(seg: dict) -> list[list[float]]:
    """Return [[w0_pass1, w1_pass1], [w0_pass2, w1_pass2], ...] of forced_native guarded D in nats."""
    pw = seg["probe_windows"]
    n_passes = min(len(w["forced_native_D_passes_guarded_nats"]) for w in pw)
    passes: list[list[float]] = []
    for p_idx in range(n_passes):
        row = [w["forced_native_D_passes_guarded_nats"][p_idx] for w in pw]
        if _finite_pair(row):
            passes.append([float(row[0]), float(row[1])])
    return passes


def _build_endpoint_timing_and_probe_table(by_canon: dict[str, dict]) -> dict:
    """Summarize ordinary implementation wall (including counters) vs raw kernel time across all 4 endpoints."""
    arm_rows = {}
    for arm_name, _ref_mode, is_genuine in REQUIRED_ENDPOINT_ARMS:
        seg = by_canon[arm_name]
        ord_w = [float(v) for v in seg["ordinary_window_seconds"]]
        ord_sum = float(seg["ordinary_two_window_sum_s"])
        raw_w = _extract_raw_kernel_pair(seg)
        raw_sum = sum(raw_w) if raw_w is not None else None
        gen_w = _extract_generate_pair(seg)
        gen_sum = sum(gen_w) if gen_w is not None else None
        passes = _extract_probe_passes(seg)
        arm_rows[arm_name] = {
            "implementation": seg.get("implementation"),
            "is_genuine_endpoint": is_genuine,
            "observer_kind": seg.get("observer_kind"),
            "switch_bits": seg.get("switch_bits"),
            "free_ids": list(seg.get("free_ids") or []),
            "ordinary_window_seconds": ord_w,
            "ordinary_two_window_sum_s": ord_sum,
            "raw_kernel_infer_window_seconds": raw_w,
            "raw_kernel_infer_two_window_sum_s": raw_sum,
            "wrapper_and_counter_overhead_two_window_s": (ord_sum - raw_sum) if raw_sum is not None else None,
            "generate_window_seconds": gen_w,
            "generate_two_window_sum_s": gen_sum,
            "forced_native_D_passes_guarded_nats": passes,
        }

    nat_ord = arm_rows["native"]["ordinary_two_window_sum_s"]
    off_ord = arm_rows["all_off"]["ordinary_two_window_sum_s"]
    car_ord = arm_rows["carbon_bf16"]["ordinary_two_window_sum_s"]
    on_ord = arm_rows["all_on"]["ordinary_two_window_sum_s"]

    nat_rk = arm_rows["native"]["raw_kernel_infer_two_window_sum_s"]
    off_rk = arm_rows["all_off"]["raw_kernel_infer_two_window_sum_s"]
    car_rk = arm_rows["carbon_bf16"]["raw_kernel_infer_two_window_sum_s"]
    on_rk = arm_rows["all_on"]["raw_kernel_infer_two_window_sum_s"]

    return {
        "causal_contrast_baselines": {
            "addition_baseline_mode": "all_off",
            "removal_baseline_mode": "all_on",
            "observer_kind": arm_rows["all_off"]["observer_kind"],
        },
        "by_mode": arm_rows,
        "native_genuine_two_window_s": nat_ord,
        "all_off_two_window_s": off_ord,
        "carbon_bf16_genuine_two_window_s": car_ord,
        "all_on_two_window_s": on_ord,
        "all_off_forced_D_pass1_nats": (
            arm_rows["all_off"]["forced_native_D_passes_guarded_nats"][0]
            if arm_rows["all_off"]["forced_native_D_passes_guarded_nats"]
            else None
        ),
        "all_on_forced_D_pass1_nats": (
            arm_rows["all_on"]["forced_native_D_passes_guarded_nats"][0]
            if arm_rows["all_on"]["forced_native_D_passes_guarded_nats"]
            else None
        ),
        "cross_endpoint_deltas": {
            "observer_delta_all_off_minus_native_ordinary_s": off_ord - nat_ord,
            "observer_delta_all_off_minus_native_raw_kernel_s": (
                (off_rk - nat_rk) if (off_rk is not None and nat_rk is not None) else None
            ),
            "observer_delta_all_on_minus_carbon_bf16_ordinary_s": on_ord - car_ord,
            "observer_delta_all_on_minus_carbon_bf16_raw_kernel_s": (
                (on_rk - car_rk) if (on_rk is not None and car_rk is not None) else None
            ),
            "genuine_native_minus_carbon_bf16_ordinary_s": nat_ord - car_ord,
            "genuine_native_minus_carbon_bf16_raw_kernel_s": (
                (nat_rk - car_rk) if (nat_rk is not None and car_rk is not None) else None
            ),
            "matched_all_off_minus_all_on_ordinary_s": off_ord - on_ord,
            "matched_all_off_minus_all_on_raw_kernel_s": (
                (off_rk - on_rk) if (off_rk is not None and on_rk is not None) else None
            ),
        },
    }


def _removal_evidence_complete(seg: dict) -> bool:
    if not seg.get("all_windows_finished_stop") or not seg.get("all_windows_eos_excluded"):
        return False
    times = seg.get("ordinary_window_seconds")
    if not _finite_pair(times) or any(t <= 0 for t in times):
        return False
    if len(seg.get("free_ids") or []) != 2:
        return False
    for w in seg.get("free_windows") or []:
        if w.get("switch_bits") != "000000" and w.get("effective_prefill_dispatch") in (
            "fallback_linear_loop",
            "partial_grouped_mm_with_fallback",
        ):
            return False
    for pw in seg.get("probe_windows") or []:
        passes = pw.get("forced_native_D_passes_guarded_nats") or []
        if not passes or passes[0] is None or not math.isfinite(passes[0]):
            return False
    return True


def analyze_a1_segments(
    segment_summaries: list[dict],
    a1_manifest: dict,
    *,
    external_endpoint_check: dict | None = None,
    require_external_endpoint_check: bool = True,
) -> dict:
    """Produce complete A1 verification & attribution report, gated strictly on 4 endpoints × 2 windows + external check."""
    by_canon: dict[str, dict] = {}
    for s in segment_summaries:
        canon = s["canonical_mode"]
        if canon in by_canon:
            raise ValueError(f"Duplicate canonical_mode in Stage A1 analysis: {canon!r}")
        by_canon[canon] = s

    anchor_verdict = verify_endpoint_anchors(
        by_canon,
        a1_manifest,
        external_endpoint_check=external_endpoint_check,
        require_external_endpoint_check=require_external_endpoint_check,
    )
    if not anchor_verdict["anchor_gate_passed"]:
        ext_info = anchor_verdict["external_endpoint_check"]
        has_all_switches = all(
            f"add_{sw}" in by_canon and f"remove_{sw}" in by_canon for sw in SWITCH_ORDER
        )
        if anchor_verdict["failed_present_arms"]:
            att_status = "blocked_endpoint_parity_mismatch"
            sel_status = "blocked_endpoint_parity_mismatch"
        elif ext_info["present"] and not ext_info["passed"]:
            att_status = "blocked_external_endpoint_check_failed"
            sel_status = "blocked_external_endpoint_check_failed"
        elif not anchor_verdict["internal_eight_window_gate_passed"]:
            att_status = "awaiting_all_four_endpoints"
            sel_status = "blocked_awaiting_all_four_endpoints"
        elif not has_all_switches:
            att_status = "four_endpoints_verified_awaiting_external_check_and_switch_suborder"
            sel_status = "awaiting_external_check_and_switch_suborder"
        else:
            att_status = "blocked_missing_external_endpoint_check"
            sel_status = "blocked_missing_external_endpoint_check"

        return {
            "schema": A1_SUMMARY_SCHEMA,
            "anchor_verification": anchor_verdict,
            "attribution_status": att_status,
            "surgical_selection_status": sel_status,
            "recommended_surgical_mode": None,
            "recommended_surgical_bits": None,
            "eligible_pair_removals": [],
            "segment_count": len(segment_summaries),
        }

    # Instrument-matched ablation baselines ('all_off' and 'all_on') for individual switch attribution.
    nat_ref = by_canon["all_off"]
    car_ref = by_canon["all_on"]
    endpoints_table = _build_endpoint_timing_and_probe_table(by_canon)

    nat_D_p1 = [w["forced_native_D_passes_guarded_nats"][0] for w in nat_ref["probe_windows"]]
    car_D_p1 = [w["forced_native_D_passes_guarded_nats"][0] for w in car_ref["probe_windows"]]
    nat_times = nat_ref["ordinary_window_seconds"]
    car_times = car_ref["ordinary_window_seconds"]
    nat_rk_times = _extract_raw_kernel_pair(nat_ref)
    car_rk_times = _extract_raw_kernel_pair(car_ref)

    single_additions = {}
    single_removals = {}
    single_removal_rows_for_ranking = {}

    for sw in SWITCH_ORDER:
        add_seg = by_canon.get(f"add_{sw}")
        if add_seg is not None:
            add_passes = _extract_probe_passes(add_seg)
            d1 = add_passes[0] if add_passes else [None, None]
            free_ids = tuple(add_seg["free_ids"])
            aligned = bool(add_seg["all_free_fields_aligned"])
            id_flipped = aligned and any(
                obs is not None and obs != exp for obs, exp in zip(free_ids, EXPECTED_NATIVE_IDS)
            )
            add_rk = _extract_raw_kernel_pair(add_seg)
            single_additions[sw] = {
                "mode": add_seg["canonical_mode"],
                "switch_bits": add_seg["switch_bits"],
                "baseline_mode": "all_off",
                "free_ids": list(free_ids),
                "all_free_fields_aligned": aligned,
                "anchored_id_flip": id_flipped if aligned else None,
                "forced_native_D_pass1_nats": d1,
                "forced_native_D_pass2_nats": add_passes[1] if len(add_passes) >= 2 else None,
                "path_effect_D_add_minus_D_all_off_pass1_nats": (
                    [d1[w] - nat_D_p1[w] for w in range(2)] if _finite_pair(d1) else None
                ),
                "path_effect_D_add_minus_D_native_pass1_nats": (
                    [d1[w] - nat_D_p1[w] for w in range(2)] if _finite_pair(d1) else None
                ),
                "window_037_history_shift_D_free_minus_D_native_nats": add_seg["probe_windows"][1][
                    "history_shift_D_free_minus_D_native_guarded_nats"
                ],
                "ordinary_window_seconds": add_seg["ordinary_window_seconds"],
                "ordinary_two_window_sum_s": add_seg["ordinary_two_window_sum_s"],
                "raw_kernel_infer_window_seconds": add_rk,
                "raw_kernel_infer_two_window_sum_s": sum(add_rk) if add_rk is not None else None,
                "local_saving_vs_all_off_window_s": [
                    nat_times[w] - add_seg["ordinary_window_seconds"][w] for w in range(2)
                ],
                "local_saving_vs_all_off_sum_s": nat_ref["ordinary_two_window_sum_s"] - add_seg["ordinary_two_window_sum_s"],
                "local_saving_vs_all_off_raw_kernel_sum_s": (
                    (sum(nat_rk_times) - sum(add_rk))
                    if (nat_rk_times is not None and add_rk is not None)
                    else None
                ),
            }

        rem_seg = by_canon.get(f"remove_{sw}")
        if rem_seg is not None:
            rem_passes = _extract_probe_passes(rem_seg)
            rd1 = rem_passes[0] if rem_passes else [None, None]
            r_ids = tuple(rem_seg["free_ids"])
            ev_ok = _removal_evidence_complete(rem_seg)
            restores_both = ev_ok and bool(rem_seg["all_free_fields_aligned"]) and (r_ids == EXPECTED_NATIVE_IDS)
            rem_rk = _extract_raw_kernel_pair(rem_seg)
            single_removals[sw] = {
                "mode": rem_seg["canonical_mode"],
                "switch_bits": rem_seg["switch_bits"],
                "baseline_mode": "all_on",
                "free_ids": list(r_ids),
                "restores_both_native_ids": restores_both,
                "evidence_complete": ev_ok,
                "forced_native_D_pass1_nats": rd1,
                "path_effect_D_remove_minus_D_all_on_pass1_nats": (
                    [rd1[w] - car_D_p1[w] for w in range(2)] if _finite_pair(rd1) else None
                ),
                "path_effect_D_remove_minus_D_full_pass1_nats": (
                    [rd1[w] - car_D_p1[w] for w in range(2)] if _finite_pair(rd1) else None
                ),
                "window_037_history_shift_D_free_minus_D_native_nats": rem_seg["probe_windows"][1][
                    "history_shift_D_free_minus_D_native_guarded_nats"
                ],
                "ordinary_window_seconds": rem_seg["ordinary_window_seconds"],
                "ordinary_two_window_sum_s": rem_seg["ordinary_two_window_sum_s"],
                "raw_kernel_infer_window_seconds": rem_rk,
                "raw_kernel_infer_two_window_sum_s": sum(rem_rk) if rem_rk is not None else None,
                "local_cost_vs_all_on_window_s": [
                    rem_seg["ordinary_window_seconds"][w] - car_times[w] for w in range(2)
                ],
                "local_cost_vs_all_on_sum_s": rem_seg["ordinary_two_window_sum_s"] - car_ref["ordinary_two_window_sum_s"],
                "local_cost_vs_all_on_raw_kernel_sum_s": (
                    (sum(rem_rk) - sum(car_rk_times))
                    if (rem_rk is not None and car_rk_times is not None)
                    else None
                ),
                "local_saving_vs_all_off_sum_s": nat_ref["ordinary_two_window_sum_s"] - rem_seg["ordinary_two_window_sum_s"],
            }
            if ev_ok:
                single_removal_rows_for_ranking[(sw,)] = {
                    "mode": rem_seg["canonical_mode"],
                    "switch_bits": rem_seg["switch_bits"],
                    "ordinary_window_seconds": rem_seg["ordinary_window_seconds"],
                    "free_ids": list(r_ids),
                    "probe_and_bindings_verified": True,
                }

    # Step 1: Check if all 6 single removals ran and whether any single removal restores both IDs.
    single_winner = None
    if len(single_removal_rows_for_ranking) == len(SWITCH_ORDER) and len(single_additions) == len(SWITCH_ORDER):
        candidates = []
        for rem_tuple, row in single_removal_rows_for_ranking.items():
            if tuple(row["free_ids"]) == EXPECTED_NATIVE_IDS:
                candidates.append(
                    (
                        len(rem_tuple),
                        sum(row["ordinary_window_seconds"]),
                        tuple(SWITCH_ORDER.index(s) for s in rem_tuple),
                        rem_tuple,
                        row,
                    )
                )
        if candidates:
            best = min(candidates)
            single_winner = {
                "removed_switches": list(best[3]),
                "mode": best[4]["mode"],
                "switch_bits": best[4]["switch_bits"],
                "ordinary_two_window_sum_s": best[1],
            }

    if single_winner is not None:
        return {
            "schema": A1_SUMMARY_SCHEMA,
            "anchor_verification": anchor_verdict,
            "attribution_status": "complete_single_switch_restoration",
            "surgical_selection_status": "selected_single_removal",
            "recommended_surgical_mode": single_winner["mode"],
            "recommended_surgical_bits": single_winner["switch_bits"],
            "recommended_removed_switches": single_winner["removed_switches"],
            "pair_removals_needed": False,
            "eligible_pair_removals": [],
            "endpoints": endpoints_table,
            "single_additions": single_additions,
            "single_removals": single_removals,
            "segment_count": len(segment_summaries),
        }

    # Step 2: No single removal restored both IDs (or single sweep incomplete). Evaluate pair admission.
    if len(single_removals) < len(SWITCH_ORDER) or len(single_additions) < len(SWITCH_ORDER):
        return {
            "schema": A1_SUMMARY_SCHEMA,
            "anchor_verification": anchor_verdict,
            "attribution_status": "partial_single_sweep_incomplete",
            "surgical_selection_status": "incomplete_sweep_no_selection",
            "recommended_surgical_mode": None,
            "recommended_surgical_bits": None,
            "pair_removals_needed": None,
            "eligible_pair_removals": [],
            "endpoints": endpoints_table,
            "single_additions": single_additions,
            "single_removals": single_removals,
            "segment_count": len(segment_summaries),
        }

    nat_passes = _extract_probe_passes(nat_ref)
    car_passes = _extract_probe_passes(car_ref)
    nat_2p = nat_passes[:2] if len(nat_passes) >= 2 else None
    car_2p = car_passes[:2] if len(car_passes) >= 2 else None
    if nat_2p is None or car_2p is None:
        return {
            "schema": A1_SUMMARY_SCHEMA,
            "anchor_verification": anchor_verdict,
            "attribution_status": "needs_endpoint_probe_repeat_for_pair_qualification",
            "surgical_selection_status": "awaiting_pair_qualification_repeats",
            "recommended_surgical_mode": None,
            "recommended_surgical_bits": None,
            "pair_removals_needed": True,
            "eligible_pair_removals": [],
            "endpoints": endpoints_table,
            "single_additions": single_additions,
            "single_removals": single_removals,
            "segment_count": len(segment_summaries),
        }

    noise_floor = [
        max(NUMERIC_FLOOR_NATS, abs(nat_2p[0][w] - nat_2p[1][w]), abs(car_2p[0][w] - car_2p[1][w]))
        for w in range(2)
    ]
    qualifying_switches = []
    missing_repeat_switches = []
    qualification_reasons = {}

    for sw in SWITCH_ORDER:
        add_info = single_additions[sw]
        if add_info["anchored_id_flip"] is True:
            qualifying_switches.append(sw)
            qualification_reasons[sw] = "anchored_free_id_flip"
            continue
        if add_info["anchored_id_flip"] is None:
            missing_repeat_switches.append(sw)
            qualification_reasons[sw] = "ambiguous_unaligned_free_field"
            continue
        d1 = add_info["forced_native_D_pass1_nats"]
        deltas1 = [d1[w] - nat_2p[0][w] for w in range(2)]
        if any(abs(deltas1[w]) > noise_floor[w] for w in range(2)):
            d2 = add_info["forced_native_D_pass2_nats"]
            if d2 is None:
                missing_repeat_switches.append(sw)
                qualification_reasons[sw] = "needs_second_probe_pass"
                continue
            matched_win = False
            for w in range(2):
                again = d2[w] - nat_2p[1][w]
                if min(abs(deltas1[w]), abs(again)) > noise_floor[w] and (deltas1[w] * again > 0):
                    matched_win = True
                    break
            if matched_win:
                qualifying_switches.append(sw)
                qualification_reasons[sw] = "reproducible_above_noise_span_shift"
            else:
                qualification_reasons[sw] = "failed_repeat_sign_or_noise_floor"
        else:
            qualification_reasons[sw] = "below_noise_floor_pass1"

    if missing_repeat_switches:
        return {
            "schema": A1_SUMMARY_SCHEMA,
            "anchor_verification": anchor_verdict,
            "attribution_status": "needs_addition_probe_repeats",
            "surgical_selection_status": "awaiting_addition_repeats",
            "missing_repeat_switches": missing_repeat_switches,
            "noise_floor_nats": noise_floor,
            "qualification_reasons": qualification_reasons,
            "recommended_surgical_mode": None,
            "recommended_surgical_bits": None,
            "pair_removals_needed": True,
            "eligible_pair_removals": [],
            "endpoints": endpoints_table,
            "single_additions": single_additions,
            "single_removals": single_removals,
            "segment_count": len(segment_summaries),
        }

    eligible_pairs = list(combinations(qualifying_switches, 2))
    eligible_pair_modes = [f"remove_{a}_{b}" for a, b in eligible_pairs]

    if not eligible_pairs:
        return {
            "schema": A1_SUMMARY_SCHEMA,
            "anchor_verification": anchor_verdict,
            "attribution_status": "unresolved_no_qualifying_switch_pairs",
            "surgical_selection_status": "unresolved_halt_at_a1",
            "noise_floor_nats": noise_floor,
            "qualifying_switches": qualifying_switches,
            "qualification_reasons": qualification_reasons,
            "recommended_surgical_mode": None,
            "recommended_surgical_bits": None,
            "pair_removals_needed": False,
            "eligible_pair_removals": [],
            "endpoints": endpoints_table,
            "single_additions": single_additions,
            "single_removals": single_removals,
            "segment_count": len(segment_summaries),
        }

    pair_results = {}
    missing_pair_modes = []
    pair_candidates = []
    for s1, s2 in eligible_pairs:
        pmode = f"remove_{s1}_{s2}"
        pseg = by_canon.get(pmode)
        if pseg is None or not _removal_evidence_complete(pseg):
            missing_pair_modes.append(pmode)
            continue
        p_ids = tuple(pseg["free_ids"])
        restores = bool(pseg["all_free_fields_aligned"]) and (p_ids == EXPECTED_NATIVE_IDS)
        p_rk = _extract_raw_kernel_pair(pseg)
        pair_results[pmode] = {
            "removed_switches": [s1, s2],
            "switch_bits": pseg["switch_bits"],
            "free_ids": list(p_ids),
            "restores_both_native_ids": restores,
            "ordinary_window_seconds": pseg["ordinary_window_seconds"],
            "ordinary_two_window_sum_s": pseg["ordinary_two_window_sum_s"],
            "raw_kernel_infer_window_seconds": p_rk,
            "raw_kernel_infer_two_window_sum_s": sum(p_rk) if p_rk is not None else None,
        }
        if restores:
            pair_candidates.append(
                (
                    2,
                    sum(pseg["ordinary_window_seconds"]),
                    (SWITCH_ORDER.index(s1), SWITCH_ORDER.index(s2)),
                    (s1, s2),
                    pmode,
                    pseg["switch_bits"],
                )
            )

    if missing_pair_modes:
        return {
            "schema": A1_SUMMARY_SCHEMA,
            "anchor_verification": anchor_verdict,
            "attribution_status": "pair_removals_required",
            "surgical_selection_status": "awaiting_eligible_pair_removals",
            "noise_floor_nats": noise_floor,
            "qualifying_switches": qualifying_switches,
            "qualification_reasons": qualification_reasons,
            "recommended_surgical_mode": None,
            "recommended_surgical_bits": None,
            "pair_removals_needed": True,
            "eligible_pair_removals": eligible_pair_modes,
            "missing_pair_removals": missing_pair_modes,
            "evaluated_pair_removals": pair_results,
            "endpoints": endpoints_table,
            "single_additions": single_additions,
            "single_removals": single_removals,
            "segment_count": len(segment_summaries),
        }

    if pair_candidates:
        best_p = min(pair_candidates)
        return {
            "schema": A1_SUMMARY_SCHEMA,
            "anchor_verification": anchor_verdict,
            "attribution_status": "interaction_compatible_pair_restoration",
            "surgical_selection_status": "selected_pair_removal",
            "noise_floor_nats": noise_floor,
            "qualifying_switches": qualifying_switches,
            "qualification_reasons": qualification_reasons,
            "recommended_surgical_mode": best_p[4],
            "recommended_surgical_bits": best_p[5],
            "recommended_removed_switches": list(best_p[3]),
            "pair_removals_needed": True,
            "eligible_pair_removals": eligible_pair_modes,
            "evaluated_pair_removals": pair_results,
            "endpoints": endpoints_table,
            "single_additions": single_additions,
            "single_removals": single_removals,
            "segment_count": len(segment_summaries),
        }

    return {
        "schema": A1_SUMMARY_SCHEMA,
        "anchor_verification": anchor_verdict,
        "attribution_status": "unresolved_after_eligible_pairs",
        "surgical_selection_status": "unresolved_halt_at_a1",
        "noise_floor_nats": noise_floor,
        "qualifying_switches": qualifying_switches,
        "qualification_reasons": qualification_reasons,
        "recommended_surgical_mode": None,
        "recommended_surgical_bits": None,
        "pair_removals_needed": True,
        "eligible_pair_removals": eligible_pair_modes,
        "evaluated_pair_removals": pair_results,
        "endpoints": endpoints_table,
        "single_additions": single_additions,
        "single_removals": single_removals,
        "segment_count": len(segment_summaries),
    }


def load_segments_from_run_dirs(run_dirs: list[Path], a1_manifest: dict) -> list[dict]:
    """Load and cross-verify segment-summary.json against raw free/window-*.json across suborder directories."""
    expected_first_pages = [int(w["first_page"]) for w in a1_manifest["windows"]]
    segments: list[dict] = []
    seen_canons: dict[str, Path] = {}

    for rdir in run_dirs:
        if not rdir.is_dir():
            raise FileNotFoundError(f"Run directory does not exist: {rdir}")
        proc_path = rdir / "process.json"
        if proc_path.is_file():
            proc = json.loads(proc_path.read_bytes())
            if not proc.get("all_segments_completed"):
                raise ValueError(f"Run directory did not complete all segments cleanly: {rdir}")
        seg_dirs = sorted(p for p in rdir.iterdir() if p.is_dir() and p.name.startswith("segment-"))
        if not seg_dirs:
            raise ValueError(f"No segment-* directories found in {rdir}")
        for sdir in seg_dirs:
            child = json.loads((sdir / "child.json").read_bytes())
            summary = json.loads((sdir / "segment-summary.json").read_bytes())
            if child.get("mode") != summary.get("mode") or child.get("canonical_mode") != summary.get("canonical_mode"):
                raise ValueError(f"child.json / segment-summary.json mode mismatch in {sdir}")
            canon = str(summary["canonical_mode"])
            if canon in seen_canons:
                raise ValueError(f"Duplicate canonical mode {canon!r} in {sdir} and {seen_canons[canon]}")
            seen_canons[canon] = sdir

            free_wins = summary.get("free_windows") or []
            if len(free_wins) != len(expected_first_pages):
                raise ValueError(f"Unexpected window count in {sdir}: {len(free_wins)}")
            for w_idx, fp in enumerate(expected_first_pages):
                raw_win_path = sdir / "free" / f"window-{fp:03d}.json"
                raw_win = json.loads(raw_win_path.read_bytes())
                tok_sha = token_ids_sha256([int(t) for t in raw_win["window_token_ids"]])
                if tok_sha != free_wins[w_idx].get("window_token_ids_sha256"):
                    raise ValueError(f"Raw window-{fp:03d}.json token SHA disagreed with segment-summary in {sdir}")
                if (
                    raw_win.get("pages") != 3
                    or raw_win.get("num_pages_out") != 3
                    or raw_win.get("finish_reason") != "stop"
                    or raw_win.get("eos_id") in raw_win["window_token_ids"]
                ):
                    raise ValueError(f"Incomplete or malformed raw window-{fp:03d}.json in {sdir}")

            segments.append(summary)
    return segments


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dirs", nargs="+", type=Path, required=True, help="One or more Stage A1 suborder run directories")
    ap.add_argument(
        "--endpoint-check",
        type=Path,
        required=True,
        help="Path to external check_endpoints.py JSON receipt (4 endpoints × 2 windows = 8 checks)",
    )
    ap.add_argument("--a1-manifest", type=Path, default=DEFAULT_A1_MANIFEST, help="Path to frozen a1-inputs.json")
    ap.add_argument("--a1-manifest-sha256", help="Optional expected 64-hex SHA-256 of --a1-manifest")
    ap.add_argument("--out", type=Path, required=True, help="Destination path for combined a1-summary.json")
    args = ap.parse_args(argv)

    m_bytes = args.a1_manifest.read_bytes()
    if args.a1_manifest_sha256 and _sha256_bytes(m_bytes) != args.a1_manifest_sha256.lower():
        raise ValueError("a1-manifest SHA-256 mismatch")
    a1_manifest = json.loads(m_bytes)
    ext_check = json.loads(args.endpoint_check.read_bytes())

    segs = load_segments_from_run_dirs([p.resolve() for p in args.run_dirs], a1_manifest)
    summary = analyze_a1_segments(
        segs,
        a1_manifest,
        external_endpoint_check=ext_check,
        require_external_endpoint_check=True,
    )
    summary["combined_run_dirs"] = [str(p.resolve()) for p in args.run_dirs]
    summary["endpoint_check_path"] = str(args.endpoint_check.resolve())
    summary["endpoint_check_sha256"] = _sha256_bytes(args.endpoint_check.read_bytes())
    out_sha = _atomic_write_json(args.out.resolve(), summary)
    print(
        json.dumps(
            {
                "out_path": str(args.out.resolve()),
                "a1_summary_sha256": out_sha,
                "anchor_gate_passed": summary["anchor_verification"]["anchor_gate_passed"],
                "attribution_status": summary["attribution_status"],
                "surgical_selection_status": summary["surgical_selection_status"],
                "recommended_surgical_mode": summary.get("recommended_surgical_mode"),
                "eligible_pair_removals": summary.get("eligible_pair_removals", []),
            }
        )
    )
    return 0 if summary["anchor_verification"]["anchor_gate_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
