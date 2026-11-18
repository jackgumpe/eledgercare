"""Reconcile durable publications with original input, raw pages, native windows and outer clocks."""
import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_document(folder, request):
    timing = read(folder / "timing.json")
    pred_file = folder / "prediction.json"
    pred = read(pred_file)
    n = request["pages"]
    sid = request["sha256"]
    assert sha(Path(request["pdf"])) == sid
    assert timing["status"] == "completed" and timing["request"] == request
    assert timing["complete_pages"] == n == len(pred["pages"])
    assert sha(pred_file) == timing["prediction_sha256"] and pred["source_sha256"] == sid
    times = [timing["accepted_ns"], *timing["page_committed_ns"], timing["document_committed_ns"]]
    assert len(times) == n + 2 and times == sorted(times) and times[1] == timing["first_page_committed_ns"]
    assert timing["elapsed_s"] == (times[-1] - times[0]) / 1e9
    rows = []
    for i, page in enumerate(pred["pages"], 1):
        raw = read(folder / f"raw-{i:03d}.json")
        assert read(folder / f"page-{i:03d}.json") == page and page["state"] == "complete"
        assert page["source_sha256"] == raw["source_sha256"] == sid and page["page"] == raw["page"] == i
        assert raw["rgb_sha256"] == request["rgb_sha256"][i-1]
        if request["mode"] == "native":
            assert len(raw["token_ids"]) == raw["token_count"] == sum(raw["token_classes"].values())
        else:
            assert raw["word_count"] == sum(len(line["words"]) for line in raw["reader_result"]["lines"])
        rows.append(raw)
    position, engine_ns = 0, 0
    windows = []
    for file in sorted(folder.glob("window-*.json")):
        win = read(file)
        batch = rows[position:position+win["pages"]]
        assert batch and win["first_page"] == position + 1 and len(batch) == win["pages"] and win["source_sha256"] == sid
        delta = win["engine_end_ns"] - win["engine_begin_ns"]
        assert times[0] <= win["engine_begin_ns"] <= win["engine_end_ns"] <= times[-1]
        engine_ns += delta
        if request["mode"] == "native":
            assert [i for row in batch for i in row["token_ids"]] == win["window_token_ids"]
            assert "".join(row["raw_output"] for row in batch) == win["raw_output"]
            assert win["finish_reason"] == "stop" and win["expected_pages"] == win["num_pages_out"] == len(batch)
        windows.append({"first_page": win["first_page"], "pages": len(batch), "engine_s": delta / 1e9})
        position += len(batch)
    assert position == n
    return {"label": request["label"], "mode": request["mode"], "warmup": request["warmup"],
            "source_sha256": sid, "pages": n, "elapsed_s": timing["elapsed_s"], "first_page_s": timing["first_page_s"],
            "pages_per_minute_before_quality": n * 60 / timing["elapsed_s"], "prediction_sha256": sha(pred_file),
            "render_s": sum(r["render_ns"] for r in rows) / 1e9, "engine_s": engine_ns / 1e9,
            "tokens_per_page": [r["token_count"] for r in rows], "windows": windows}


def verify(run, release):
    assert sha(run / "plan.json") == release["plan_sha256"]
    plan = read(run / "plan.json")["requests"]
    launch, proc, session = (read(run / name) for name in ("launch.json", "process.json", "session.json"))
    assert launch["source"] == release["source"] and launch["lease"] == release["lease"]
    assert proc["returncode"] == 0 and proc["reason"] is None
    assert len(plan) == len(session) and proc["elapsed_s"] <= release["seconds"] + 2
    docs = []
    for i, (req, released) in enumerate(zip(plan, release["ordered_requests"]), 1):
        assert all(req[k] == v for k, v in released.items())
        folder = run / f"{i:02d}-{req['label']}-{req['mode']}"
        assert read(folder / "timing.json") == session[i-1]
        docs.append(verify_document(folder, req))
    return {"lease": release["lease"], "source": release["source"], "process_exit": proc["returncode"],
            "supervised_wall_s": proc["elapsed_s"], "documents": docs,
            "limits": "Successful observation and durable identity audit. Apply frozen OCR quality and eligibility checks separately."}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("release", type=Path)
    args = p.parse_args()
    print(json.dumps(verify(args.run, read(args.release)), indent=2))
