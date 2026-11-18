"""Recompute measurements from small retained process/envelope/phase records and compare outputs."""
import argparse
import json
import statistics
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def secs(a, b):
    return (b-a)/1e9


def stats(seq):
    return {"n": len(seq), "median": statistics.median(seq), "range": [min(seq), max(seq)]}


def summarize(root):
    fresh = {}
    rows = []
    for key in "ABS":
        folder = root / ("fresh-" + key)
        receipt = read(folder / "process.json")
        score = fresh[key] = read(folder / "score.json")
        rows.append(dict(stage="fresh", fixture=key, score_sha=score["sha256"], tokens=score["output_tokens"],
                         worker_s=score["timings"]["total_duration_ms"]/1000, process_wait_s=receipt["process_wait_s"],
                         envelope_wait_s=receipt["envelope_wait_s"], inference_s=score["timings"]["infer_duration_ms"]/1000,
                         exact_text=score.get("exact_ordered_text")))
    folder = root / "resident"
    process = read(folder / "process.json")
    for fs in sorted(folder.glob("[1-6]-*")):
        key = fs.name[-1]
        t = read(fs / "events.json")
        score = read(fs / "score.json")
        native = read(fs / "native.json")
        m, n = native["marks_ns"], native["native"]
        nt = len(native["token_ids"])
        fwd = native["forward_count"]
        infer_s = score["timings"]["infer_duration_ms"]/1000
        first, last = m["first_token_streamer_enter_synced"], m["last_token_streamer_enter"]
        selected = ("import_torch", "query_platform_with_cuda", "normalize_and_verify_model_dir",
                    "verify_model_sources_ast_safety", "import_transformers_AutoModel_AutoTokenizer", "named_load_real",
                    "read_and_render_pdf", "verify_loaded_module_cache", "installed_distributions")
        spans = {e["label"]: secs(e["start_ns"],e["end_ns"]) for e in t["spans"] if e["label"] in selected}
        weight_files = {Path(e["file"]).name: secs(e["start_ns"], e["end_ns"]) for e in t["spans"]
                        if e["label"] == "file_digests" and e["file"].endswith(".safetensors")}
        base = fresh[key]
        compare = dict(raw_identical=score["sha256"] == base["sha256"], raster_identical=score["raster"] == base["raster"])
        if key == "S":
            compare["lost_previous_correct_cells"] = [c for c, v in base["table_cells"].items()
                                                       if v["exact"] and not score["table_cells"][c]["exact"]]
            compare["lost_previous_present_fields"] = [k for k, v in base["printed_fields_present"].items()
                                                        if v and not score["printed_fields_present"][k]]
            compare["structured_incorrect_cells"] = {k:v for k,v in score["table_cells"].items() if not v["exact"]}
        rows.append(dict(stage=fs.name, fixture=key, score_sha=score["sha256"], tokens=nt, prompt_tokens=n["prompt_len"],
                         worker_s=score["timings"]["total_duration_ms"]/1000, inference_s=infer_s,
                         request_to_completed_s=secs(t["request_start_ns"],t["output_complete_ns"]),
                         launch_to_first_completion_s=secs(process["process_start_ns"], t["output_complete_ns"]) if fs.name.startswith("1-") else None,
                         launch_to_script_entry_s=secs(process["process_start_ns"],t["child_entry_ns"]) if fs.name.startswith("1-") else None,
                         script_entry_to_imported_s=secs(t["child_entry_ns"],t["worker_imported_ns"]),
                         phase_s=spans, model_weight_hash_s=weight_files, native_ttft_s=n["prefill_time_s"],
                         native_generation_s=n["time_s"], native_post_first_s=n["time_s"]-n["prefill_time_s"],
                         call_to_first_emission_s=secs(m["infer_multi_start"], first),
                         input_build_s=secs(m["build_inputs_start"], m["build_inputs_end"]),
                         sam_enter_to_projector_return_s=secs(m["vision_first_sam_start"], m["vision_last_projector_end"]),
                         after_first_to_call_end_s=secs(first, m["infer_multi_end"]),
                         last_visible_token_to_call_end_s=secs(last, m["infer_multi_end"]),
                         emitted_after_first_per_s=(nt-1)/secs(first, last), native_forward_count=fwd,
                         output_tokens_per_total_infer_s=nt/infer_s, exact_text=score.get("exact_ordered_text"), **compare))
    warm = [r for r in rows if r["stage"] in ("2-B", "3-A", "4-B", "5-A")]
    for r in warm:
        baseline = next(x for x in rows if x["stage"] == "fresh" and x["fixture"] == r["fixture"])
        r["matched_ready_speedup"] = baseline["envelope_wait_s"] / r["request_to_completed_s"]
    return dict(rows=rows, warm_short_request_s=stats([r["request_to_completed_s"] for r in warm]),
                matched_ready_speedup=stats([r["matched_ready_speedup"] for r in warm]),
                resident_process_exit_code=process["exit_code"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("evidence_root", type=Path)
    print(json.dumps(summarize(parser.parse_args().evidence_root), indent=2, ensure_ascii=False))
