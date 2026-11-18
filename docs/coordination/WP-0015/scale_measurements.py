"""Export per-page measurements without copying evaluation keys, source images or predictions."""
import argparse
import json
from pathlib import Path

from verify_trial import read, sha, verify_document


def collect(run):
    plan = read(run / "plan.json")
    proc = read(run / "process.json")
    docs = []
    for i, request in enumerate(plan["requests"], 1):
        if request["warmup"]:
            continue
        mode = request["mode"]
        folder = run / f"{i:02d}-{request['label']}-{mode}"
        complete = (folder / "timing.json").is_file()
        timing = read(folder / "timing.json") if complete else {}
        if complete:
            verify_document(folder, request)
        source = request["sha256"]
        assert sha(Path(request["pdf"])) == source
        pages, windows = [], []
        for path in sorted(folder.glob("window-*.json")):
            w = read(path)
            assert w["source_sha256"] == source and w["first_page"] == len(pages) + 1
            windows.append({"first_page": w["first_page"], "pages": w["pages"], "evidence_sha256": sha(path),
                            "finish_reason": w.get("finish_reason"), "engine_s": (w["engine_end_ns"] - w["engine_begin_ns"]) / 1e9,
                            "visual_tokens": w.get("visual_tokens"), "prefill_s": w.get("prefill_time_s"),
                            "native_output_tokens": len(w["window_token_ids"]) if mode == "native" else None})
            for page in range(w["first_page"], w["first_page"] + w["pages"]):
                raw_path = folder / f"raw-{page:03d}.json"
                page_path = folder / f"page-{page:03d}.json"
                raw, prediction = read(raw_path), read(page_path)
                assert raw["page"] == prediction["page"] == page
                assert raw["source_sha256"] == prediction["source_sha256"] == source
                assert raw["rgb_sha256"] == request["rgb_sha256"][page-1]
                pages.append({"page": page, "window_first_page": w["first_page"], "state": prediction["state"],
                              "render_rgb_sha256": raw["rgb_sha256"], "raw_sha256": sha(raw_path),
                              "prediction_page_sha256": sha(page_path), "render_s": raw["render_ns"] / 1e9,
                              "elapsed_to_page_commit_s": (timing["page_committed_ns"][page-1] - timing["accepted_ns"]) / 1e9 if complete else None,
                              "output_tokens": raw["token_count"], "output_words": raw.get("word_count")})
        assert len(pages) == len(list(folder.glob("raw-*.json"))) == len(list(folder.glob("page-*.json")))
        elapsed = timing.get("elapsed_s")
        failure = None if complete else read(folder / "failure.json")
        load = read(run / f"load-{mode}.json")
        docs.append({"mode": mode, "complete": complete, "source_sha256": source, "requested_pages": request["pages"],
                     "published_pages": len(pages), "service_load_s": load["elapsed_s"], "elapsed_s": elapsed,
                     "pages_per_minute": 60 * len(pages) / elapsed if complete else None,
                     "prediction_sha256": timing.get("prediction_sha256"), "first_page_s": timing.get("first_page_s"),
                     "failure_elapsed_s": failure["elapsed_since_dispatch_s"] if failure else None,
                     "failure_type": failure["error"].split("(", 1)[0] if failure else None,
                     "windows": windows, "pages": pages})
    return {"run": run.name, "source": read(run / "launch.json")["source"], "plan_sha256": sha(run / "plan.json"),
            "process_exit": proc["returncode"], "process_elapsed_s": proc["elapsed_s"], "documents": docs}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path, nargs="+")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    records = [collect(run) for run in args.runs]
    with args.out.open("x", encoding="utf8", newline="\n") as file:
        json.dump(records, file, indent=2)
        file.write("\n")
