"""Self-test of analyze.py on FABRICATED run trees (test double; no OCR, no model, no sealed data).

Builds two processes (ab, ba) with the same file layout trial.py publishes, from public dev truth,
then checks: clean trees verify; tampered RGB, reordered page and broken token reassembly are caught;
scoring stage runs the frozen scorer in a separate process. Nothing here enters result tables.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEV = ROOT / "docs/evaluation/WP-0015/dev"
SOURCE = "82206bc4b77654010ac02364adaaf589d1f36780"
PAGE_ID = 128827


def put(path, value):
    data = (json.dumps(value) + "\n").encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def fabricate(run, order, family, elapsed):
    truth = json.loads((DEV / family / "truth.json").read_text())
    man = json.loads((DEV / family / "rasters.json").read_text())
    pins = [p["rgb_sha256"] for p in man["pages"]]
    doc = dict(label=family, pdf=str(DEV / family / "source.pdf"), pages=len(pins), warmup=False,
               sha256=truth["source_sha256"], rgb_sha256=pins)
    modes = ("native", "windows") if order == "ab" else ("windows", "native")
    reqs = [dict(doc, mode=m) for m in modes]
    run.mkdir(parents=True)
    plan = put(run / "plan.json", dict(requests=reqs))
    put(run / "launch.json", dict(source=SOURCE, plan_sha256=plan, test_double=True))
    put(run / "process.json", dict(returncode=0, reason=None, elapsed_s=sum(elapsed.values()) + 30, gpu_samples=[]))
    put(run / "child.json", dict(test_double=True))
    put(run / "session.json", [])
    put(run / "load-native.json", dict(elapsed_s=30.0, page_id=PAGE_ID))
    put(run / "load-windows.json", dict(elapsed_s=1.0))
    for i, req in enumerate(reqs, 1):
        f = run / f"{i:02d}-{family}-{req['mode']}"
        f.mkdir()
        pages = []
        win = 3 if req["mode"] == "native" else 1
        for ref in truth["pages"]:
            pred = dict(source_sha256=doc["sha256"], page=ref["page"], state="complete", text=ref["text"],
                        spans=[dict(text=l["text"], bbox=l["bbox"], flagged=False) for l in ref["lines"]],
                        tables=[dict(bbox=t["bbox"], rows=[[c["text"] for c in r] for r in t["rows"]])
                                for t in ref["tables"]])
            toks = [PAGE_ID, 1000 + ref["page"], 7] if req["mode"] == "native" else None
            raw = dict(page=ref["page"], rgb_sha256=pins[ref["page"] - 1], source_sha256=doc["sha256"],
                       raw_output=f"<PAGE>p{ref['page']}" if toks else None, token_ids=toks,
                       token_classes=dict(page=1, content=2) if toks else None)
            put(f / f"raw-{ref['page']:03d}.json", raw)
            put(f / f"page-{ref['page']:03d}.json", pred)
            pages.append((pred, raw))
        for first in range(1, len(pages) + 1, win):
            span = pages[first - 1:first - 1 + win]
            w = dict(source_sha256=doc["sha256"], first_page=first, pages=len(span), engine_begin_ns=0,
                     engine_end_ns=int(1e9))
            if req["mode"] == "native":
                w.update(finish_reason="stop", num_pages_out=len(span), expected_pages=len(span), time_s=1.0,
                         prefill_time_s=0.1, prompt_len=279, forward_count=7, kernel_path="dense", triton_starts=0,
                         dense_starts=12, clock_marks_ns=dict(generate_start=0, first_token=int(4e8),
                         last_token=int(9e8), generate_end=int(1e9), vision_start=0, vision_end=int(3e7)),
                         window_token_ids=[t for _, r in span for t in r["token_ids"]],
                         raw_output="".join(r["raw_output"] for _, r in span))
            else:
                w.update(windows_ocr_words=10, recognize_ms=50.0, reader_and_layout_ns=int(1e8))
            put(f / f"window-{first:03d}.json", w)
        pred_sha = put(f / "prediction.json", dict(source_sha256=doc["sha256"], pages=[p for p, _ in pages]))
        put(f / "timing.json", dict(request=req, prediction_sha256=pred_sha, status="completed", accepted_ns=0,
                                    first_page_committed_ns=1, document_committed_ns=2,
                                    elapsed_s=elapsed[req["mode"]], first_page_s=0.5, complete_pages=len(pages)))
    return DEV / family / "rasters.json"


def analyze(runs, pins, out, *extra):
    cmd = [sys.executable, "-B", str(HERE / "analyze.py"), "--runs", *map(str, runs), "--pins", str(pins),
           "--family", "boundary", "--out", str(out), *extra]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stderr


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out", type=Path, help="new directory")
    out = ap.parse_args().out
    out.mkdir(parents=True)
    r1, r2 = out / "runs/t-r1-ab", out / "runs/t-r2-ba"
    pins = fabricate(r1, "ab", "boundary", dict(native=100.0, windows=20.0))
    fabricate(r2, "ba", "boundary", dict(native=104.0, windows=21.0))
    results = {}
    code, res = analyze([r1, r2], pins, out / "a-clean")
    results["clean_stage1"] = dict(code=code, failures=res["failures"], spread=res["timing"]["control_spread_s"],
                                   gate=res["timing"]["every_pair_saving_exceeds_control_spread"])
    assert code == 0 and res["timing"]["control_spread_s"] == 4.0 and res["timing"]["both_orders_present"], res
    code, res = analyze([r1, r2], pins, out / "a-score", "--truth", str(DEV / "boundary/truth.json"),
                        "--rasters", str(pins))
    assert code == 0, res
    analysis = json.loads((out / "a-score/analysis.json").read_text())
    s = analysis["scores"]["t-r1-ab-windows"]
    assert s["packet_complete"] and s["comparison"]["inside_quality_budget"] and s["counts"]["cer"] == 0
    results["clean_stage2"] = dict(code=code, windows_unattended=s["comparison"]["unattended_quality_gate"],
                                   control_repeat=len(analysis["control_quality_repeat"]))
    # Tamper 1: RGB pin in a raw page record.
    raw = r2 / "02-boundary-native/raw-002.json"
    keep = raw.read_bytes()
    raw.write_text(raw.read_text().replace(json.loads(keep)["rgb_sha256"], "0" * 64))
    code, res = analyze([r1, r2], pins, out / "a-rgb")
    raw.write_bytes(keep)
    assert code == 1 and any("raw rgb" in f for f in res["failures"]), res
    results["tampered_rgb"] = res["failures"]
    # Tamper 2: native window tokens do not reassemble from page tokens.
    win = r1 / "01-boundary-native/window-001.json"
    keep = win.read_bytes()
    w = json.loads(keep)
    w["window_token_ids"] = w["window_token_ids"][::-1]
    win.write_text(json.dumps(w))
    code, res = analyze([r1, r2], pins, out / "a-tok")
    win.write_bytes(keep)
    assert code == 1 and any("reassemble" in f for f in res["failures"]), res
    results["tampered_tokens"] = res["failures"]
    # Tamper 3: prediction edited after its timing record (hash) and page order swapped.
    pred = r1 / "02-boundary-windows/prediction.json"
    keep = pred.read_bytes()
    p = json.loads(keep)
    p["pages"][0], p["pages"][1] = p["pages"][1], p["pages"][0]
    pred.write_text(json.dumps(p))
    code, res = analyze([r1, r2], pins, out / "a-order")
    pred.write_bytes(keep)
    assert code == 1 and any("prediction hash" in f for f in res["failures"]) and any(
        "ordinals" in f for f in res["failures"]), res
    results["tampered_prediction"] = res["failures"]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
