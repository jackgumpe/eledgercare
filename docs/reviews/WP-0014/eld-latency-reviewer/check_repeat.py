"""Reduce independent repeat records with the standard library and explicit timing boundaries."""

import hashlib
import json
import re
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
FIXTURES = HERE.parents[2] / "research/WP-0014/eld-latency-author"
SHORT_TRUTH = {
    "A": "The garden crew left a clean watering can beside the greenhouse door. "
         "A gray rabbit crossed the gravel path before the morning bell. "
         "When the sun reached the bench, two sparrows landed near the empty basket.",
    "B": "The print shop set a blue notebook on the counter near the window. "
         "A bicycle courier rang the silver bell just before lunch. "
         "After the rain passed, the clerk carried the parcels to the yellow van.",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def score(folder, key):
    envelope = read(folder / "envelope.json")
    raw = (folder / "raw_output.utf8.bin").read_bytes()
    assert envelope["status"] == "completed"
    assert envelope["input"]["sha256"] == sha((FIXTURES / (key + ".pdf")).read_bytes())
    assert envelope["output"]["sha256"] == sha(raw)
    assert envelope["output"]["finish_reason"] == "stop"
    assert envelope["input"]["page_count"] == envelope["output"]["output_page_count"] == 1
    raw_text = raw.decode("utf-8", "strict")
    assert raw_text.startswith("<PAGE>") and raw_text.count("<PAGE>") == 1
    block_pattern = re.compile(r"<BLOCK>(\w+)\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]<FORK>")
    blocks = block_pattern.sub(" ", raw_text.removeprefix("<PAGE>"))
    observed = " ".join(blocks.split())
    timings = envelope["timings"]
    return {
        "fixture": key,
        "document_id": envelope["document_id"], "job_id": envelope["job_id"], "attempt_id": envelope["attempt_id"],
        "raw_sha256": sha(raw), "raster_sha256": envelope["diagnostics"]["rendered_pages"][0]["rgb_sha256"],
        "exact_ordered_text": observed == SHORT_TRUTH[key],
        "layout_blocks": [dict(kind=m[1], bounds=[int(c) for c in m.groups()[1:]]) for m in block_pattern.finditer(raw_text)],
        "raw_without_bound_values_sha256": sha(block_pattern.sub(r"<BLOCK>\1[]<FORK>", raw_text).encode("utf-8")),
        "prompt_positions": envelope["diagnostics"]["prompt_token_count"],
        "returned_tokens": envelope["output"]["output_token_count"],
        "kernel": envelope["diagnostics"]["kernel_path"],
        "worker_s": timings["total_duration_ms"] / 1000, "infer_s": timings["infer_duration_ms"] / 1000,
        "load_s": timings["load_duration_ms"] / 1000, "render_s": timings["render_duration_ms"] / 1000,
        "peak_allocated_bytes_inference": envelope["diagnostics"]["cuda_max_allocated_bytes"],
        "peak_reserved_bytes_inference": envelope["diagnostics"]["cuda_max_reserved_bytes"],
    }


def reduce_repeat(runs):
    fresh = score(runs / "fresh-A/output", "A")
    fresh_receipt = read(runs / "fresh-A/process.json")
    resident_receipt = read(runs / "resident-short/process.json")
    assert fresh_receipt["exit_code"] == resident_receipt["exit_code"] == 0
    assert fresh_receipt["launched_pid"] != resident_receipt["launched_pid"]
    published = fresh_receipt["envelope_observed_ns"]
    origin = fresh_receipt["process_start_ns"]
    fresh["launch_to_envelope_observed_s"] = None if published is None else (published - origin) / 1e9
    fresh["launch_to_exit_observed_s"] = (fresh_receipt["process_observed_exit_ns"] - origin) / 1e9
    resident = []
    for index, key in enumerate("ABA", 1):
        folder = runs / "resident-short" / f"{index}-{key}"
        row = score(folder, key)
        events = read(folder / "events.json")
        native = read(folder / "native.json")
        clock = native["native"]
        marks = native["marks_ns"]
        tokens = native["token_ids"]
        assert len(tokens) == row["returned_tokens"] == native["forward_count"] - 1
        assert row["prompt_positions"] == clock["prompt_len"]
        assert native["dense_starts"] == native["triton_starts"] == native["triton_none_returns"] == 12
        assert clock["finish_reason"] == "stop" and clock["expected_pages"] == clock["num_pages_out"] == 1
        row["pid"] = events["pid"]
        row["native_ids_sha256"] = sha(json.dumps(tokens, separators=(",", ":")).encode("ascii"))
        row["image_positions"] = native.get("image_tokens")
        row["slotted_request_s"] = (events["output_complete_ns"] - events["request_start_ns"]) / 1e9
        row["launch_to_completion_s"] = (events["output_complete_ns"] - resident_receipt["process_start_ns"]) / 1e9
        row["time_to_first_selected_token_s"] = clock["prefill_time_s"]
        row["post_first_through_eos_and_native_cleanup_s"] = clock["time_s"] - clock["prefill_time_s"]
        visible_span = (marks["last_token_streamer_enter"] - marks["first_token_streamer_enter_synced"]) / 1e9
        row["visible_emissions_after_first_per_s"] = (len(tokens) - 1) / visible_span
        resident.append(row)
    rows = [fresh, *resident]
    for key in ("document_id", "job_id", "attempt_id"):
        assert len({row[key] for row in rows}) == len(rows)
    assert len({row["pid"] for row in resident}) == 1
    a_rows = [row for row in rows if row["fixture"] == "A"]
    warm_a = resident[-1]["slotted_request_s"]
    return {
        "fresh": fresh, "resident": resident, "all_short_texts_exact": all(row["exact_ordered_text"] for row in rows),
        "A_raw_identical": len({row["raw_sha256"] for row in a_rows}) == 1,
        "A_rasters_identical": len({row["raster_sha256"] for row in a_rows}) == 1,
        "matched_A_fresh_to_warm_ratio": None if published is None else fresh["launch_to_envelope_observed_s"] / warm_a,
    }


if __name__ == "__main__":
    print(json.dumps(reduce_repeat(Path(sys.argv[1])), indent=2))
