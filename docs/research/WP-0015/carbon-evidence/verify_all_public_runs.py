"""Reproducible CPU-only archiver and verifier for WP-0015 Carbon public runs
(carbon-moe-01, carbon-dense-ab, carbon-dense-ba).

Copies bounded JSON/UTF-8 receipts (excluding cache/, PDFs, and weights) for AB and BA
when --sync-runs-root is passed, verifies all 126 archived receipts against manifests,
confirms ProfiledNative's 363 dev/dense token IDs and 57 warm token IDs equal ordinary
Native in both AB and BA, recomputes paired timing noise, Exact-BF16 parity, and frozen
common score.py outputs on public dev keys, and records small harness findings.
Never imports torch or touches CUDA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EVAL = ROOT / "docs/evaluation/WP-0015"
ASTRA = ROOT / "docs/research/WP-0015/astra"
TOKENIZER_JSON = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/models/Unlimited_OCR_2_04809669/tokenizer.json")

sys.path[:0] = [str(EVAL), str(ASTRA)]
import formats  # noqa: E402
import score as common_score  # noqa: E402

FORBIDDEN_SUFFIXES = {".pdf", ".safetensors", ".bin", ".pt", ".pth", ".pyc", ".pyd", ".dll", ".exe"}
FULL_BOX_RE = re.compile(r"<BLOCK>([\w-]+(?:<LEVEL\d+>)?)\s*\[\s*\d+,\s*\d+,\s*\d+,\s*\d+\s*\]<FORK>")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sync_one_run(src_run: Path, dst_run: Path) -> list[dict]:
    if dst_run.exists():
        shutil.rmtree(dst_run)
    entries = []
    for p in sorted(src_run.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(src_run)
        if "cache" in rel.parts:
            continue
        if p.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise ValueError(f"Refusing forbidden artifact suffix: {rel}")
        raw = p.read_bytes()
        target = dst_run / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        entries.append({"path": rel.as_posix(), "bytes": len(raw), "sha256": sha256_bytes(raw)})
    return entries


def verify_run_manifest(dst_run: Path, entries: list[dict]) -> int:
    actual = sorted(p.relative_to(dst_run).as_posix() for p in dst_run.rglob("*") if p.is_file())
    expected = [e["path"] for e in entries]
    if actual != expected:
        raise ValueError(f"File list mismatch in {dst_run.name}: actual={len(actual)} expected={len(expected)}")
    for e in entries:
        p = dst_run / e["path"]
        if p.suffix.lower() in FORBIDDEN_SUFFIXES or "cache" in Path(e["path"]).parts:
            raise ValueError(f"Forbidden path in {dst_run.name}: {e['path']}")
        raw = p.read_bytes()
        if len(raw) != e["bytes"] or sha256_bytes(raw) != e["sha256"]:
            raise ValueError(f"Digest mismatch for {dst_run.name}/{e['path']}")
    return sum(e["bytes"] for e in entries)


def decode_tokens(ids: list[int]) -> list[str] | None:
    if not TOKENIZER_JSON.exists():
        return None
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(TOKENIZER_JSON))
    return [tok.decode([tid], skip_special_tokens=False) for tid in ids]


def token_diffs(ids_a: list[int], ids_b: list[int]) -> list[dict]:
    pa = decode_tokens(ids_a)
    pb = decode_tokens(ids_b)
    out = []
    for idx, (a, b) in enumerate(zip(ids_a, ids_b)):
        if a != b:
            lo, hi = max(0, idx - 4), min(len(ids_a), idx + 5)
            out.append(
                {
                    "token_index": idx,
                    "baseline_token_id": a,
                    "challenger_token_id": b,
                    "baseline_piece": pa[idx] if pa else None,
                    "challenger_piece": pb[idx] if pb else None,
                    "baseline_context": "".join(pa[lo:hi]) if pa else None,
                    "challenger_context": "".join(pb[lo:hi]) if pb else None,
                }
            )
    return out


def load_doc_bundle(doc_dir: Path) -> dict:
    t = json.loads((doc_dir / "timing.json").read_bytes())
    w = json.loads((doc_dir / "window-001.json").read_bytes())
    r = json.loads((doc_dir / "raw-001.json").read_bytes())
    p_bytes = (doc_dir / "prediction.json").read_bytes()
    assert sha256_bytes(p_bytes) == t["prediction_sha256"], f"prediction_sha256 mismatch in {doc_dir}"
    p = json.loads(p_bytes)
    marks = w["clock_marks_ns"]
    return {
        "timing": t,
        "window": w,
        "raw": r,
        "prediction": p,
        "post_first_ms": (marks["generate_end"] - marks["first_token"]) / 1e6,
        "vision_ms": ((marks["vision_end_end"] - marks["vision_start_start"]) / 1e6) if "vision_end_end" in marks else None,
    }


def summarize_crossover_run(run_dir: Path, truth: dict, nat_seg: str, cbf_seg: str) -> dict:
    launch_j = json.loads((run_dir / "launch.json").read_bytes())
    proc_j = json.loads((run_dir / "process.json").read_bytes())
    load_nat = json.loads((run_dir / nat_seg / "load-native.json").read_bytes())
    load_cbf = json.loads((run_dir / cbf_seg / "load-carbon_bf16.json").read_bytes())

    warm_nat = load_doc_bundle(run_dir / nat_seg / "01-warm-native")
    dense_nat = load_doc_bundle(run_dir / nat_seg / "02-dense-native")
    warm_cbf = load_doc_bundle(run_dir / cbf_seg / "01-warm-carbon_bf16")
    dense_cbf = load_doc_bundle(run_dir / cbf_seg / "02-dense-carbon_bf16")

    sc_nat = common_score.score(truth, dense_nat["prediction"])
    sc_cbf = common_score.score(truth, dense_cbf["prediction"])
    comp = common_score.compare(sc_nat, sc_cbf)

    nat_ids = dense_nat["window"]["window_token_ids"]
    cbf_ids = dense_cbf["window"]["window_token_ids"]
    d_diffs = token_diffs(nat_ids, cbf_ids)
    w_diffs = token_diffs(warm_nat["window"]["window_token_ids"], warm_cbf["window"]["window_token_ids"])

    nat_s = dense_nat["timing"]["elapsed_s"]
    cbf_s = dense_cbf["timing"]["elapsed_s"]

    return {
        "run_id": run_dir.name,
        "frozen_candidate_source": launch_j["source"],
        "executing_head": launch_j["head"],
        "plan_sha256": launch_j["plan_sha256"],
        "segment_order": launch_j["segment_modes"],
        "supervisor_elapsed_s": proc_j["elapsed_s"],
        "all_segments_completed": proc_j["all_segments_completed"],
        "cold_loads": {
            "native_elapsed_s": load_nat["elapsed_s"],
            "native_load_ms": load_nat["load_ms"],
            "carbon_bf16_elapsed_s": load_cbf["elapsed_s"],
            "carbon_bf16_base_load_ms": load_cbf["base_load_ms"],
            "carbon_bf16_pack_patch_ms": load_cbf["pack_patch_ms"],
            "carbon_bf16_total_load_ms": load_cbf["load_ms"],
            "carbon_bf16_combination": load_cbf["combination"],
        },
        "warm_1p": {
            "native_elapsed_s": warm_nat["timing"]["elapsed_s"],
            "native_prefill_s": warm_nat["window"]["prefill_time_s"],
            "native_forwards": warm_nat["window"]["forward_count"],
            "carbon_bf16_elapsed_s": warm_cbf["timing"]["elapsed_s"],
            "carbon_bf16_prefill_s": warm_cbf["window"]["prefill_time_s"],
            "carbon_bf16_forwards": warm_cbf["window"]["forward_count"],
            "carbon_bf16_burst_extra_forwards": warm_cbf["window"]["burst_extra_forwards"],
            "token_count_both": warm_nat["raw"]["token_count"],
            "differing_tokens": w_diffs,
        },
        "dense_1p": {
            "native_elapsed_s": nat_s,
            "native_first_page_s": dense_nat["timing"]["first_page_s"],
            "native_infer_ms": dense_nat["window"]["native_infer_ms"],
            "native_prefill_s": dense_nat["window"]["prefill_time_s"],
            "native_post_first_ms": dense_nat["post_first_ms"],
            "native_forwards": dense_nat["window"]["forward_count"],
            "native_pages_per_min": 60.0 / nat_s,
            "native_max_cuda_allocated_bytes": dense_nat["window"]["vram"]["cuda_max_allocated_bytes"],
            "native_max_cuda_reserved_bytes": dense_nat["window"]["vram"]["cuda_max_reserved_bytes"],
            "carbon_bf16_elapsed_s": cbf_s,
            "carbon_bf16_first_page_s": dense_cbf["timing"]["first_page_s"],
            "carbon_bf16_infer_ms": dense_cbf["window"]["native_infer_ms"],
            "carbon_bf16_prefill_s": dense_cbf["window"]["prefill_time_s"],
            "carbon_bf16_post_first_ms": dense_cbf["post_first_ms"],
            "carbon_bf16_forwards": dense_cbf["window"]["forward_count"],
            "carbon_bf16_burst_extra_forwards": dense_cbf["window"]["burst_extra_forwards"],
            "carbon_bf16_static_cache_reallocations": dense_cbf["window"]["static_cache_reallocations"],
            "carbon_bf16_grouped_mm_calls_cumulative": dense_cbf["window"]["prefill_grouped_mm_layer_calls"],
            "carbon_bf16_fallback_calls_cumulative": dense_cbf["window"]["prefill_moe_fallback_layer_calls"],
            "carbon_bf16_pages_per_min": 60.0 / cbf_s,
            "carbon_bf16_max_cuda_allocated_bytes": dense_cbf["window"]["vram"]["cuda_max_allocated_bytes"],
            "carbon_bf16_max_cuda_reserved_bytes": dense_cbf["window"]["vram"]["cuda_max_reserved_bytes"],
            "wall_saving_s": nat_s - cbf_s,
            "speedup_vs_native": nat_s / cbf_s,
            "token_count_both": dense_nat["raw"]["token_count"],
            "token_classes_both": dense_nat["raw"]["token_classes"],
            "exact_bf16_qualified": nat_ids == cbf_ids,
            "lost_exactness": nat_ids != cbf_ids,
            "differing_tokens": d_diffs,
            "equal_after_stripping_all_block_coords": (
                FULL_BOX_RE.sub(r"<BLOCK>\1<FORK>", dense_nat["raw"]["raw_output"])
                == FULL_BOX_RE.sub(r"<BLOCK>\1<FORK>", dense_cbf["raw"]["raw_output"])
            ),
            "common_scorer_counts_native": sc_nat["counts"],
            "common_scorer_counts_carbon_bf16": sc_cbf["counts"],
            "common_scorer_comparison": comp,
        },
        "_nat_dense_ids": nat_ids,
        "_cbf_dense_ids": cbf_ids,
        "_nat_warm_ids": warm_nat["window"]["window_token_ids"],
        "_cbf_warm_ids": warm_cbf["window"]["window_token_ids"],
        "_nat_dense_raw": dense_nat["raw"]["raw_output"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sync-runs-root", type=Path, default=None)
    args = p.parse_args()

    moe_dir = HERE / "carbon-moe-01"
    ab_dir = HERE / "carbon-dense-ab"
    ba_dir = HERE / "carbon-dense-ba"
    moe_manifest_path = HERE / "manifest.json"
    abba_manifest_path = HERE / "manifest-ab-ba.json"
    out_summary_path = HERE / "ab-ba-summary.json"

    if args.sync_runs_root is not None:
        rroot = args.sync_runs_root.resolve()
        ab_entries = sync_one_run(rroot / "carbon-dense-ab", ab_dir)
        ba_entries = sync_one_run(rroot / "carbon-dense-ba", ba_dir)
        abba_manifest = {
            "schema": "eledgercare.wp0015.carbon-ab-ba-manifest/1",
            "runs": {
                "carbon-dense-ab": {
                    "file_count": len(ab_entries),
                    "total_bytes": sum(e["bytes"] for e in ab_entries),
                    "files": ab_entries,
                },
                "carbon-dense-ba": {
                    "file_count": len(ba_entries),
                    "total_bytes": sum(e["bytes"] for e in ba_entries),
                    "files": ba_entries,
                },
            },
        }
        abba_manifest_path.write_text(json.dumps(abba_manifest, indent=2) + "\n", encoding="utf-8", newline="\n")

    moe_manifest = json.loads(moe_manifest_path.read_text(encoding="utf-8"))
    abba_manifest = json.loads(abba_manifest_path.read_text(encoding="utf-8"))
    b_moe = verify_run_manifest(moe_dir, moe_manifest["files"])
    b_ab = verify_run_manifest(ab_dir, abba_manifest["runs"]["carbon-dense-ab"]["files"])
    b_ba = verify_run_manifest(ba_dir, abba_manifest["runs"]["carbon-dense-ba"]["files"])

    truth = common_score.read(EVAL / "dev/dense/truth.json")
    ab_sum = summarize_crossover_run(ab_dir, truth, "segment-01-native", "segment-02-carbon_bf16")
    ba_sum = summarize_crossover_run(ba_dir, truth, "segment-02-native", "segment-01-carbon_bf16")

    prof_dense_w = json.loads((moe_dir / "segment-01-native_profile/02-dense-native_profile/window-001.json").read_bytes())
    prof_warm_w = json.loads((moe_dir / "segment-01-native_profile/01-warm-native_profile/window-001.json").read_bytes())

    prof_eq_ab_dense = prof_dense_w["window_token_ids"] == ab_sum["_nat_dense_ids"]
    prof_eq_ba_dense = prof_dense_w["window_token_ids"] == ba_sum["_nat_dense_ids"]
    prof_eq_ab_warm = prof_warm_w["window_token_ids"] == ab_sum["_nat_warm_ids"]
    prof_eq_ba_warm = prof_warm_w["window_token_ids"] == ba_sum["_nat_warm_ids"]
    cbf_ab_eq_ba_dense = ab_sum["_cbf_dense_ids"] == ba_sum["_cbf_dense_ids"]
    cbf_ab_eq_ba_warm = ab_sum["_cbf_warm_ids"] == ba_sum["_cbf_warm_ids"]
    assert prof_eq_ab_dense and prof_eq_ba_dense and prof_eq_ab_warm and prof_eq_ba_warm

    # Diagnostic check of shared astra/formats.py title-<LEVEL1> adapter artifact on dev/dense
    raw_title_fixed = ab_sum["_nat_dense_raw"].replace("<BLOCK>title<LEVEL1>[", "<BLOCK>title[")
    page_title_fixed = formats.native_page(raw_title_fixed, (612.0, 792.0))
    sc_title_fixed = common_score.score(
        truth,
        {
            "family": "dense",
            "source_sha256": truth["source_sha256"],
            "pages": [dict(page=1, state="complete", source_sha256=truth["source_sha256"], **page_title_fixed)],
        },
    )

    for d in (ab_sum, ba_sum):
        for k in list(d.keys()):
            if k.startswith("_"):
                del d[k]

    nat_ab = ab_sum["dense_1p"]["native_elapsed_s"]
    nat_ba = ba_sum["dense_1p"]["native_elapsed_s"]
    cbf_ab = ab_sum["dense_1p"]["carbon_bf16_elapsed_s"]
    cbf_ba = ba_sum["dense_1p"]["carbon_bf16_elapsed_s"]
    nat_noise_s = abs(nat_ba - nat_ab)
    cbf_noise_s = abs(cbf_ba - cbf_ab)
    nat_mean_s = 0.5 * (nat_ab + nat_ba)
    cbf_mean_s = 0.5 * (cbf_ab + cbf_ba)

    summary = {
        "schema": "eledgercare.wp0015.carbon-ab-ba-summary/1",
        "frozen_candidate_source": "7e70391cd790a95c68906902dbd9d5bc479aa9c0",
        "archived_receipt_totals": {
            "run_count": 3,
            "file_count": moe_manifest["file_count"]
            + abba_manifest["runs"]["carbon-dense-ab"]["file_count"]
            + abba_manifest["runs"]["carbon-dense-ba"]["file_count"],
            "total_bytes": b_moe + b_ab + b_ba,
        },
        "profiler_ordinary_native_identity_confirmation": {
            "dev_dense_363_token_ids_equal_ab_ordinary_native": prof_eq_ab_dense,
            "dev_dense_363_token_ids_equal_ba_ordinary_native": prof_eq_ba_dense,
            "warm_a_pdf_57_token_ids_equal_ab_and_ba_ordinary_native": (prof_eq_ab_warm and prof_eq_ba_warm),
            "carbon_bf16_ab_equals_ba_363_dense_and_57_warm_tokens": (cbf_ab_eq_ba_dense and cbf_ab_eq_ba_warm),
            "measured_profiler_overhead_on_dev_dense_s": {
                "native_profile_s": 44.7369747,
                "ordinary_native_mean_s": nat_mean_s,
                "profiler_overhead_vs_mean_native_s": 44.7369747 - nat_mean_s,
            },
        },
        "paired_crossover_comparison_dev_dense": {
            "ab_native_s": nat_ab,
            "ab_carbon_bf16_s": cbf_ab,
            "ab_saving_s": nat_ab - cbf_ab,
            "ab_speedup": nat_ab / cbf_ab,
            "ba_native_s": nat_ba,
            "ba_carbon_bf16_s": cbf_ba,
            "ba_saving_s": nat_ba - cbf_ba,
            "ba_speedup": nat_ba / cbf_ba,
            "ordinary_native_paired_noise_s": nat_noise_s,
            "carbon_bf16_paired_noise_s": cbf_noise_s,
            "ba_saving_smaller_than_native_noise": (nat_ba - cbf_ba) < nat_noise_s,
            "mean_native_s": nat_mean_s,
            "mean_carbon_bf16_s": cbf_mean_s,
            "mean_saving_s": nat_mean_s - cbf_mean_s,
            "mean_speedup": nat_mean_s / cbf_mean_s,
            "falsifier_dense_5x_speedup_passed": False,
            "exact_bf16_qualified": False,
            "inside_changed_output_quality_budget": True,
            "unattended_quality_gate_both": False,
        },
        "runs": {
            "carbon-dense-ab": ab_sum,
            "carbon-dense-ba": ba_sum,
        },
        "small_harness_and_adapter_findings": [
            {
                "id": "HARNESS-01",
                "component": "docs/research/WP-0015/carbon/launch.py (at 55b57427c14d3e1884a06b8986999b76801ff241)",
                "finding": "gpu_observation() parsed temperature_c with int(row[3]) and raised ValueError on decimal telemetry ('46.64') before any model run; fixed to float(row[3]) in 7e70391cd790a95c68906902dbd9d5bc479aa9c0.",
            },
            {
                "id": "HARNESS-02",
                "component": "docs/research/WP-0015/carbon/engine.py (carbon_bf16 burst_stride=8)",
                "finding": "Speculative 8-step GPU decode bursts executed 8 post-EOS extra forwards on warm (66 vs 58 forwards) and 6 post-EOS extra forwards on dev/dense (370 vs 364 forwards, ~0.52-0.62s wasted GPU/dispatch time); truncated cleanly before decoding so returned token counts remained exact (57 and 363).",
            },
            {
                "id": "HARNESS-03",
                "component": "docs/research/WP-0015/carbon/evaluate.py (BOX_RE)",
                "finding": "Diagnostic BOX_RE omitted optional `<LEVEL\\d+>` in `<BLOCK>title<LEVEL1>[57, 61, 618, 93]<FORK>`, reporting diagnostic_coord_stripped_raw_equal=False on carbon-moe-01 (token #7 diff in title box) vs True on carbon-dense-ab/ba (token #341 diff in plain `<BLOCK>text[...]`). Official Exact-BF16 and score.py results were unaffected.",
            },
            {
                "id": "HARNESS-04",
                "component": "docs/research/WP-0015/astra/formats.py (native_page BLOCK_RE) & upstream TextStreamer stdio",
                "finding": (
                    f"Shared native_page BLOCK_RE leaves `<BLOCK>title<LEVEL1>[57, 61, 618, 93]<FORK>` unparsed in page text, accounting for 43 of 48 character edits on dev/dense "
                    f"(CER {ab_sum['dense_1p']['common_scorer_counts_native']['cer']:.6f} -> {sc_title_fixed['counts']['cer']:.6f} [{sc_title_fixed['counts']['edits']}/496] and lines 4/6 -> {sc_title_fixed['counts']['correct_lines']}/6 when stripped, matching the 2/570 title-corrected CER finding on H). "
                    "Separately, upstream Native's TextStreamer prints raw UTF-8 text to child stdout without UTF-8 stdio enforcement, which caused the 36/60 cp1252 failure on 60-page packet A before UTF-8 replay."
                ),
            },
        ],
    }
    out_summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    assert "torch" not in sys.modules
    print(
        json.dumps(
            {
                "verified_files_total": summary["archived_receipt_totals"]["file_count"],
                "verified_bytes_total": summary["archived_receipt_totals"]["total_bytes"],
                "prof_363_eq_ab_and_ba_native": (prof_eq_ab_dense and prof_eq_ba_dense),
                "ab_speedup": round(ab_sum["dense_1p"]["speedup_vs_native"], 4),
                "ba_speedup": round(ba_sum["dense_1p"]["speedup_vs_native"], 4),
                "native_noise_s": round(nat_noise_s, 4),
                "ba_saving_s": round(nat_ba - cbf_ba, 4),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
