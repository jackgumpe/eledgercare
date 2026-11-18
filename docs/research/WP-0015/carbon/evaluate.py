"""Post-run CPU evaluator for WP-0015 Carbon runs.

Audits Exact-BF16 token/stop/page parity against matched Native baseline, invokes the
frozen custodian score.py for Changed-Output deltas and unattended quality gates, and
evaluates Carbon's pre-registered 60% stage-share and >=5x dense-speedup falsifiers.
Never imports torch or touches CUDA.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EVAL = ROOT / "docs/evaluation/WP-0015"
ASTRA = ROOT / "docs/research/WP-0015/astra"
sys.path[:0] = [str(HERE), str(EVAL), str(ASTRA)]

from formats import digest, publish
import score as common_score

BOX_RE = re.compile(r"<BLOCK>([\w-]+)\s*\[\s*\d+,\s*\d+,\s*\d+,\s*\d+\s*\]<FORK>")


def strip_box_coords(raw: str) -> str:
    return BOX_RE.sub(r"<BLOCK>\1<FORK>", raw)


def load_doc_artifacts(doc_dir: Path) -> dict:
    timing = json.loads((doc_dir / "timing.json").read_bytes())
    pred_bytes = (doc_dir / "prediction.json").read_bytes()
    assert digest(pred_bytes) == timing["prediction_sha256"], f"prediction hash mismatch in {doc_dir}"
    pred = json.loads(pred_bytes)
    windows = [json.loads(p.read_bytes()) for p in sorted(doc_dir.glob("window-*.json"))]
    raws = [json.loads(p.read_bytes()) for p in sorted(doc_dir.glob("raw-*.json"))]
    tok_totals = dict(page=0, block_geometry=0, table_syntax=0, content=0)
    total_tokens = 0
    for r in raws:
        total_tokens += int(r.get("token_count", 0))
        for k, v in (r.get("token_classes") or {}).items():
            tok_totals[k] = tok_totals.get(k, 0) + int(v)
    vram_alloc = max((w.get("vram", {}).get("cuda_max_allocated_bytes", 0) for w in windows), default=0)
    vram_res = max((w.get("vram", {}).get("cuda_max_reserved_bytes", 0) for w in windows), default=0)
    infer_ms = sum(int(w.get("native_infer_ms", 0)) for w in windows)
    return dict(
        folder=str(doc_dir),
        timing=timing,
        prediction=pred,
        windows=windows,
        raws=raws,
        total_tokens=total_tokens,
        token_classes=tok_totals,
        native_infer_ms_sum=infer_ms,
        decode_tokens_per_infer_s=(total_tokens / (infer_ms / 1000.0)) if infer_ms > 0 else None,
        max_cuda_allocated_bytes=vram_alloc,
        max_cuda_reserved_bytes=vram_res,
    )


def check_exact_parity(base_art: dict, trial_art: dict) -> dict:
    b_win, t_win = base_art["windows"], trial_art["windows"]
    same_win_count = len(b_win) == len(t_win)
    win_checks = []
    all_tokens_equal = same_win_count
    all_stops_equal = same_win_count
    all_coord_stripped_equal = same_win_count

    for wi, (bw, tw) in enumerate(zip(b_win, t_win), 1):
        b_ids = bw.get("window_token_ids") or []
        t_ids = tw.get("window_token_ids") or []
        tok_eq = b_ids == t_ids
        stop_eq = (
            bw.get("finish_reason") == tw.get("finish_reason") == "stop"
            and bw.get("expected_pages") == tw.get("expected_pages")
            and bw.get("num_pages_out") == tw.get("num_pages_out")
        )
        first_diff = None
        if not tok_eq:
            for idx, (x, y) in enumerate(zip(b_ids, t_ids)):
                if x != y:
                    first_diff = dict(index=idx, baseline_token_id=x, challenger_token_id=y)
                    break
            if first_diff is None:
                first_diff = dict(index=min(len(b_ids), len(t_ids)), length_baseline=len(b_ids), length_challenger=len(t_ids))
        coord_stripped_eq = strip_box_coords(bw.get("raw_output", "")) == strip_box_coords(tw.get("raw_output", ""))
        all_tokens_equal = all_tokens_equal and tok_eq
        all_stops_equal = all_stops_equal and stop_eq
        all_coord_stripped_equal = all_coord_stripped_equal and coord_stripped_eq
        win_checks.append(
            dict(
                window=wi,
                token_ids_equal=tok_eq,
                stop_and_page_counts_equal=stop_eq,
                text_excluding_box_coords_equal=coord_stripped_eq,
                baseline_tokens=len(b_ids),
                challenger_tokens=len(t_ids),
                first_token_divergence=first_diff,
            )
        )

    page_states_ok = [p.get("state") for p in base_art["prediction"]["pages"]] == [
        p.get("state") for p in trial_art["prediction"]["pages"]
    ]
    exact_bf16_qualified = bool(all_tokens_equal and all_stops_equal and page_states_ok)
    return dict(
        exact_bf16_qualified=exact_bf16_qualified,
        lost_exactness=not exact_bf16_qualified,
        all_window_token_ids_equal=all_tokens_equal,
        all_stops_and_page_counts_equal=all_stops_equal,
        all_page_states_equal=page_states_ok,
        diagnostic_coord_stripped_raw_equal=all_coord_stripped_equal,
        windows=win_checks,
    )


def evaluate_run(run_dir: Path, truth_root: Path, out_path: Path) -> dict:
    by_label_mode: dict[tuple[str, str], list[dict]] = {}
    loads = {}
    stage_profiles = []

    for seg_dir in sorted(run_dir.glob("segment-*")):
        for lp in seg_dir.glob("load-*.json"):
            loads[f"{seg_dir.name}/{lp.name}"] = json.loads(lp.read_bytes())
        for sub in sorted(seg_dir.iterdir()):
            if not sub.is_dir() or sub.name == "cache" or not (sub / "timing.json").exists():
                continue
            art = load_doc_artifacts(sub)
            req = art["timing"]["request"]
            for w in art["windows"]:
                if "decode_stage_profile" in w:
                    stage_profiles.append(
                        dict(label=req["label"], warmup=req["warmup"], first_page=w["first_page"], **w["decode_stage_profile"])
                    )
            if req["warmup"]:
                continue
            by_label_mode.setdefault((req["label"], req["mode"]), []).append(art)

    labels = sorted({lbl for lbl, _ in by_label_mode})
    comparisons = {}
    for lbl in labels:
        truth_file = truth_root / lbl / "truth.json"
        truth = common_score.read(truth_file) if truth_file.exists() else None
        base_candidates = by_label_mode.get((lbl, "native")) or by_label_mode.get((lbl, "native_profile")) or []
        base_art = base_candidates[0] if base_candidates else None
        base_sc = common_score.score(truth, base_art["prediction"]) if (truth and base_art) else None

        lbl_rows = {}
        for (l_key, mode), arts in sorted(by_label_mode.items()):
            if l_key != lbl:
                continue
            art = arts[0]
            t_rec = art["timing"]
            sc = common_score.score(truth, art["prediction"]) if truth else None
            comp = common_score.compare(base_sc, sc) if (base_sc and sc and mode not in ("native", "native_profile")) else None
            exact = check_exact_parity(base_art, art) if (base_art and mode not in ("native", "native_profile")) else None
            complete = sc["packet_complete"] if sc else (t_rec["complete_pages"] == t_rec["request"]["pages"])
            elapsed_s = t_rec["elapsed_s"]
            base_elapsed_s = base_art["timing"]["elapsed_s"] if base_art else None
            lbl_rows[mode] = dict(
                elapsed_s=elapsed_s,
                first_page_s=t_rec["first_page_s"],
                complete_pages=t_rec["complete_pages"],
                packet_complete=complete,
                pages_per_min=(60.0 * t_rec["complete_pages"] / elapsed_s) if complete else None,
                speedup_vs_baseline=(base_elapsed_s / elapsed_s) if (base_elapsed_s and complete) else None,
                total_output_tokens=art["total_tokens"],
                token_classes=art["token_classes"],
                decode_tokens_per_infer_s=art["decode_tokens_per_infer_s"],
                max_cuda_allocated_bytes=art["max_cuda_allocated_bytes"],
                max_cuda_reserved_bytes=art["max_cuda_reserved_bytes"],
                exact_parity=exact,
                score_counts=sc["counts"] if sc else None,
                comparison_vs_baseline=comp,
            )
        comparisons[lbl] = lbl_rows

    dense_carbon = comparisons.get("dense", {}).get("carbon_bf16")
    falsifiers = {
        "stage_profile_60pct_share": [
            dict(label=p["label"], fraction=p["targeted_subsystems_fraction_of_step_wall"], passed=p["falsifier_60pct_stage_share_passed"])
            for p in stage_profiles
            if not p["warmup"]
        ],
        "dense_5x_speedup_passed": (
            bool(dense_carbon["speedup_vs_baseline"] is not None and dense_carbon["speedup_vs_baseline"] >= 5.0)
            if dense_carbon
            else None
        ),
    }

    summary = dict(
        run_dir=str(run_dir),
        cold_loads=loads,
        stage_profiles=stage_profiles,
        packets=comparisons,
        falsifiers=falsifiers,
    )
    publish(out_path, summary)
    assert "torch" not in sys.modules
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_dir", type=Path)
    p.add_argument("--truth-root", type=Path, default=EVAL / "dev")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    res = evaluate_run(args.run_dir.resolve(), args.truth_root.resolve(), args.out.resolve())
    print(json.dumps(res["falsifiers"], indent=2))


if __name__ == "__main__":
    main()
