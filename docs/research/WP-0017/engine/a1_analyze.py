"""Deterministic Stage A1 endpoint-parity gate, causal score table, and Astra-rule selector.

Enforces mandatory whole-token-array & SHA-256 parity on anchored endpoints ('native',
'carbon_bf16', plus 'all_off' and 'all_on' when present) BEFORE computing switch attribution
or candidate selection. Mirrors the exact decision arithmetic of docs/research/WP-0017/design/rules.py.
"""
from __future__ import annotations

from itertools import combinations
import json
import math
from pathlib import Path

from span_probe import token_ids_sha256
from switches import SWITCH_ORDER

A1_SUMMARY_SCHEMA = "eledgercare.wp0017.a1-summary/1"

NUMERIC_FLOOR_NATS = 1e-5
EXPECTED_NATIVE_IDS = ("I08O1-388", "8OI10-774")
EXPECTED_CARBON_IDS = ("108O1-388", "80I10-774")


def _finite_pair(vals) -> bool:
    return (
        isinstance(vals, (list, tuple))
        and len(vals) == 2
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in vals)
    )


def verify_endpoint_anchors(segments_by_canon: dict[str, dict], a1_manifest: dict) -> dict:
    """Verify complete emitted token arrays and stop/EOS invariants against frozen WP-0016 traces."""
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
    # Must have at least one native-bit ('native' or 'all_off') and one full-bit ('carbon_bf16' or 'all_on'),
    # and every present endpoint/proof arm must match its WP-0016 anchor 100%.
    arm_targets = [
        ("native", "native", True),
        ("all_off", "native", False),
        ("carbon_bf16", "carbon_bf16", True),
        ("all_on", "carbon_bf16", False),
    ]
    present_native_family = 0
    present_carbon_family = 0
    all_present_ok = True

    for arm_name, ref_mode, _is_genuine in arm_targets:
        seg = segments_by_canon.get(arm_name)
        if seg is None:
            checks[arm_name] = {"present": False}
            continue
        if ref_mode == "native":
            present_native_family += 1
        else:
            present_carbon_family += 1

        win_ok_list = []
        for w_idx, free_w in enumerate(seg["free_windows"]):
            obs_sha = free_w["window_token_ids_sha256"]
            exp_sha = expected_shas[ref_mode][w_idx]
            ep = free_w.get("endpoint_parity") or {}
            exact_arr = bool(ep.get("exact_token_array_match")) and (obs_sha == exp_sha)
            stop_ok = (free_w.get("finish_reason") == "stop")
            eos_ok = bool(free_w.get("eos_excluded_verified"))
            w_pass = exact_arr and stop_ok and eos_ok
            win_ok_list.append(
                {
                    "window_label": free_w["window_label"],
                    "passed": w_pass,
                    "exact_token_array_match": exact_arr,
                    "observed_token_ids_sha256": obs_sha,
                    "expected_token_ids_sha256": exp_sha,
                    "finish_reason": free_w.get("finish_reason"),
                    "eos_excluded_verified": eos_ok,
                    "first_diff": ep.get("first_diff"),
                }
            )
        arm_pass = all(w["passed"] for w in win_ok_list)
        if not arm_pass:
            all_present_ok = False
        checks[arm_name] = {
            "present": True,
            "reference_anchor": ref_mode,
            "implementation": seg.get("implementation"),
            "observer_kind": seg.get("observer_kind"),
            "passed": arm_pass,
            "windows": win_ok_list,
        }

    # Explicit cross-observer equivalence check when both genuine and parameterized endpoints ran.
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

    gate_passed = bool(present_native_family >= 1 and present_carbon_family >= 1 and all_present_ok)
    return {
        "anchor_gate_passed": gate_passed,
        "has_native_endpoint": (present_native_family >= 1),
        "has_carbon_endpoint": (present_carbon_family >= 1),
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


def _endpoint_two_passes(primary_seg: dict | None, secondary_seg: dict | None) -> list[list[float]] | None:
    passes: list[list[float]] = []
    if primary_seg is not None:
        passes.extend(_extract_probe_passes(primary_seg))
    if len(passes) < 2 and secondary_seg is not None:
        passes.extend(_extract_probe_passes(secondary_seg))
    return passes[:2] if len(passes) >= 2 else None


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


def analyze_a1_segments(segment_summaries: list[dict], a1_manifest: dict) -> dict:
    """Produce complete A1 verification & attribution report, gated strictly on endpoint parity."""
    by_canon: dict[str, dict] = {}
    for s in segment_summaries:
        by_canon[s["canonical_mode"]] = s

    anchor_verdict = verify_endpoint_anchors(by_canon, a1_manifest)
    if not anchor_verdict["anchor_gate_passed"]:
        return {
            "schema": A1_SUMMARY_SCHEMA,
            "anchor_verification": anchor_verdict,
            "attribution_status": "blocked_endpoint_parity_mismatch",
            "surgical_selection_status": "blocked_endpoint_parity_mismatch",
            "recommended_surgical_mode": None,
            "recommended_surgical_bits": None,
            "eligible_pair_removals": [],
            "segment_count": len(segment_summaries),
        }

    nat_ref = by_canon.get("all_off") or by_canon.get("native")
    car_ref = by_canon.get("all_on") or by_canon.get("carbon_bf16")
    nat_genuine = by_canon.get("native")
    car_genuine = by_canon.get("carbon_bf16")

    nat_D_p1 = [w["forced_native_D_passes_guarded_nats"][0] for w in nat_ref["probe_windows"]]
    car_D_p1 = [w["forced_native_D_passes_guarded_nats"][0] for w in car_ref["probe_windows"]]
    nat_times = nat_ref["ordinary_window_seconds"]
    car_times = car_ref["ordinary_window_seconds"]

    # Build single-addition & single-removal tables.
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
            # Anchored ID flip: aligned complete identifier changed away from native on either window.
            id_flipped = aligned and any(
                obs is not None and obs != exp for obs, exp in zip(free_ids, EXPECTED_NATIVE_IDS)
            )
            single_additions[sw] = {
                "mode": add_seg["canonical_mode"],
                "switch_bits": add_seg["switch_bits"],
                "free_ids": list(free_ids),
                "all_free_fields_aligned": aligned,
                "anchored_id_flip": id_flipped if aligned else None,
                "forced_native_D_pass1_nats": d1,
                "forced_native_D_pass2_nats": add_passes[1] if len(add_passes) >= 2 else None,
                "path_effect_D_add_minus_D_native_pass1_nats": (
                    [d1[w] - nat_D_p1[w] for w in range(2)] if _finite_pair(d1) else None
                ),
                "window_037_history_shift_D_free_minus_D_native_nats": add_seg["probe_windows"][1][
                    "history_shift_D_free_minus_D_native_guarded_nats"
                ],
                "ordinary_window_seconds": add_seg["ordinary_window_seconds"],
                "ordinary_two_window_sum_s": add_seg["ordinary_two_window_sum_s"],
                "local_saving_vs_native_window_s": [
                    nat_times[w] - add_seg["ordinary_window_seconds"][w] for w in range(2)
                ],
                "local_saving_vs_native_sum_s": nat_ref["ordinary_two_window_sum_s"] - add_seg["ordinary_two_window_sum_s"],
            }

        rem_seg = by_canon.get(f"remove_{sw}")
        if rem_seg is not None:
            rem_passes = _extract_probe_passes(rem_seg)
            rd1 = rem_passes[0] if rem_passes else [None, None]
            r_ids = tuple(rem_seg["free_ids"])
            ev_ok = _removal_evidence_complete(rem_seg)
            restores_both = ev_ok and bool(rem_seg["all_free_fields_aligned"]) and (r_ids == EXPECTED_NATIVE_IDS)
            single_removals[sw] = {
                "mode": rem_seg["canonical_mode"],
                "switch_bits": rem_seg["switch_bits"],
                "free_ids": list(r_ids),
                "restores_both_native_ids": restores_both,
                "evidence_complete": ev_ok,
                "forced_native_D_pass1_nats": rd1,
                "path_effect_D_remove_minus_D_full_pass1_nats": (
                    [rd1[w] - car_D_p1[w] for w in range(2)] if _finite_pair(rd1) else None
                ),
                "window_037_history_shift_D_free_minus_D_native_nats": rem_seg["probe_windows"][1][
                    "history_shift_D_free_minus_D_native_guarded_nats"
                ],
                "ordinary_window_seconds": rem_seg["ordinary_window_seconds"],
                "ordinary_two_window_sum_s": rem_seg["ordinary_two_window_sum_s"],
                "local_cost_vs_full_window_s": [
                    rem_seg["ordinary_window_seconds"][w] - car_times[w] for w in range(2)
                ],
                "local_cost_vs_full_sum_s": rem_seg["ordinary_two_window_sum_s"] - car_ref["ordinary_two_window_sum_s"],
                "local_saving_vs_native_sum_s": nat_ref["ordinary_two_window_sum_s"] - rem_seg["ordinary_two_window_sum_s"],
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
    if len(single_removal_rows_for_ranking) == len(SWITCH_ORDER):
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
            "endpoints": {
                "native_genuine_two_window_s": nat_genuine["ordinary_two_window_sum_s"] if nat_genuine else None,
                "all_off_two_window_s": by_canon["all_off"]["ordinary_two_window_sum_s"] if "all_off" in by_canon else None,
                "carbon_bf16_genuine_two_window_s": car_genuine["ordinary_two_window_sum_s"] if car_genuine else None,
                "all_on_two_window_s": by_canon["all_on"]["ordinary_two_window_sum_s"] if "all_on" in by_canon else None,
                "native_forced_D_pass1_nats": nat_D_p1,
                "carbon_forced_D_pass1_nats": car_D_p1,
            },
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
            "single_additions": single_additions,
            "single_removals": single_removals,
            "segment_count": len(segment_summaries),
        }

    nat_2p = _endpoint_two_passes(nat_ref, nat_genuine if nat_ref is not nat_genuine else None)
    car_2p = _endpoint_two_passes(car_ref, car_genuine if car_ref is not car_genuine else None)
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
            "single_additions": single_additions,
            "single_removals": single_removals,
            "segment_count": len(segment_summaries),
        }

    # Check if all eligible pair removals have already been executed.
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
        pair_results[pmode] = {
            "removed_switches": [s1, s2],
            "switch_bits": pseg["switch_bits"],
            "free_ids": list(p_ids),
            "restores_both_native_ids": restores,
            "ordinary_window_seconds": pseg["ordinary_window_seconds"],
            "ordinary_two_window_sum_s": pseg["ordinary_two_window_sum_s"],
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
        "single_additions": single_additions,
        "single_removals": single_removals,
        "segment_count": len(segment_summaries),
    }
