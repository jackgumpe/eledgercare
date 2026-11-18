"""Independently reduce the nine archived calls and check the supplied inventory and summary."""

import io
import json
import re
import statistics
import subprocess
import zipfile

from check_repeat import FIXTURES, read, score, sha

REV = "46657096c11befc72a4e629ca688ee7755a2fbc5"
PREFIX = "docs/research/WP-0014/eld-latency-author/evidence"
COORDINATES = re.compile(rb"(<BLOCK>\w+)\[([\d, ]+)\](<FORK>)")


def check():
    archive = subprocess.check_output(["git", "archive", "--format=zip", REV, PREFIX])
    root = zipfile.Path(zipfile.ZipFile(io.BytesIO(archive)), PREFIX + "/")
    inventory = read(root / "inventory.json")
    for name, expected in inventory.items():
        data = (root / name).read_bytes()
        assert (len(data), sha(data)) == (expected["bytes"], expected["sha256"]), name
    summary = read(root / "summary.json")["rows"]
    stages = [("fresh-" + k, k) for k in "ABS"] + [(f"resident/{i}-{k}", k) for i, k in enumerate("ABABAS", 1)]
    assert len(stages) == len(summary) == 9
    rows, baseline = [], {}
    for (stage, key), supplied in zip(stages, summary):
        fresh = stage.startswith("fresh-")
        f = root / stage
        out = f / "output" if fresh else f
        env = read(out / "envelope.json")
        raw = (out / "raw_output.utf8.bin").read_bytes()
        assert env["status"] == "completed" and env["output"]["finish_reason"] == "stop"
        assert sha(raw) == env["output"]["sha256"] == supplied["score_sha"]
        row = dict(stage=stage, fixture=key, raw_sha256=sha(raw), tokens=env["output"]["output_token_count"])
        if key != "S":
            row["exact_text"] = score(out, key)["exact_ordered_text"]
            assert row["exact_text"]
        if fresh:
            receipt = read(f / "process.json")
            row["wait_s"] = (receipt["envelope_observed_ns"] - receipt["process_start_ns"]) / 1e9
            baseline[key] = raw, row["wait_s"]
        else:
            t, n = read(f / "events.json"), read(f / "native.json")
            row["wait_s"] = (t["output_complete_ns"] - t["request_start_ns"]) / 1e9
            row["ttft_s"] = n["native"]["prefill_time_s"]
            row["post_first_s"] = n["native"]["time_s"] - row["ttft_s"]
            m = n["marks_ns"]
            row["emissions_after_first_per_s"] = (len(n["token_ids"]) - 1) * 1e9 / (m["last_token_streamer_enter"] - m["first_token_streamer_enter_synced"])
            assert n["image_tokens"] == 273 and n["native"]["prompt_len"] == 279 and len(n["token_ids"]) == row["tokens"]
            prior, wait = baseline[key]
            a, b = COORDINATES.findall(prior), COORDINATES.findall(raw)
            assert len(a) == len(b)
            row["raw_equal"] = prior == raw
            row["equal_except_bbox_values"] = COORDINATES.sub(rb"\1[]\3", prior) == COORDINATES.sub(rb"\1[]\3", raw)
            row["differing_box_count"] = sum(x != y for x, y in zip(a, b))
            row["box_count"] = len(b)
            row["fresh_wait_over_request_wait"] = wait / row["wait_s"]
        assert abs(row["wait_s"] - supplied["envelope_wait_s" if fresh else "request_to_completed_s"]) < 1e-9
        assert supplied["tokens"] == row["tokens"]
        rows.append(row)
    truth = read(FIXTURES.parents[3] / "evaluation/synthetic/expected/SYN-WO-01-v1-raster300_expected.json")
    table_scores = []
    for field in ("fresh-S/output", "resident/6-S"):
        raw = (root / field / "raw_output.utf8.bin").read_bytes().decode()
        tables = re.findall(r"<table>(.*?)</table>", raw, re.S)
        cells = []
        for expected, markup in zip(truth["expected_tables"], tables, strict=True):
            rows_html = re.findall(r"<tr>(.*?)</tr>", markup, re.S)[1:]
            for expected_row, row_html in zip(expected["rows"], rows_html, strict=True):
                cols = re.findall(r"<td>(.*?)</td>", row_html)
                cells += [(k, expected_row["cells"][k]["printed_text"], v) for k, v in zip(expected["column_ids"], cols, strict=True)]
        printed = []
        for item in truth["expected_fields"]:
            text = item["printed_text"]
            if item["value_type"] == "boolean_mark":
                text = item["label_printed"] + " " + text
            printed.append(text in raw)
        table_scores.append(dict(stage=field, number_of_cells=len(cells), wrong=[c for c in cells if c[1] != c[2]],
                                 printed_value_occurrences=sum(printed), expected_fields=len(printed)))
    return dict(source=REV, inventory_entries_verified=len(inventory), rows=rows, structured=table_scores,
                ready_short_median_s=statistics.median(r["wait_s"] for r in rows[4:8]))


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
