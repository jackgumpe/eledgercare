"""Verify the durably published prefix of a FAILED native document (no timing.json). Stdlib only.

Checks each published window: source identity, contiguous coverage from page 1, RGB pin per page,
page-file/raw source links, <PAGE> starts, token and raw-text reassembly, stop/page state. Reports
the last durably completed page, the failing window boundary and failure timing. Never infers pages
past the failure; a failed document has no complete-document pages/min.
"""
import argparse
import hashlib
import json
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--page-id", type=int, required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    f = a.folder
    run = f.parent
    started = next(load(p) for p in sorted(run.glob("started-*.json"))
                   if f.name.startswith(p.stem.split("-")[1] + "-"))
    req = started["request"]
    fail = load(f / "failure.json")
    problems, windows, expected = [], [], 1
    for w in sorted(f.glob("window-*.json")):
        d = load(w)
        span = list(range(d["first_page"], d["first_page"] + d["pages"]))
        if d["first_page"] != expected:
            problems.append(f"{w.name}: gap before page {d['first_page']}")
        expected = span[-1] + 1
        toks, text = [], ""
        for i in span:
            raw, page = load(f / f"raw-{i:03d}.json"), load(f / f"page-{i:03d}.json")
            if not (raw["source_sha256"] == page["source_sha256"] == req["sha256"] == d["source_sha256"]):
                problems.append(f"p{i}: source link")
            if raw["page"] != i or page["page"] != i or raw["rgb_sha256"] != req["rgb_sha256"][i - 1]:
                problems.append(f"p{i}: page ordinal or RGB pin")
            if raw["token_ids"][:1] != [a.page_id] or page["state"] != "complete":
                problems.append(f"p{i}: <PAGE> start or state")
            toks += raw["token_ids"]
            text += raw["raw_output"]
        if toks != d["window_token_ids"] or text != d["raw_output"]:
            problems.append(f"{w.name}: reassembly")
        if not (d["finish_reason"] == "stop" and d["num_pages_out"] == d["expected_pages"] == d["pages"]):
            problems.append(f"{w.name}: stop/page state")
        windows.append(dict(first_page=d["first_page"], pages=d["pages"], tokens=len(toks),
                            engine_s=(d["engine_end_ns"] - d["engine_begin_ns"]) / 1e9))
    stray = sorted(p.name for p in f.glob("*") if p.name.startswith(("raw-", "page-")) and int(p.stem[-3:]) >= expected)
    if stray or list(f.glob("*.pending")):
        problems.append(f"pages published past the last complete window or pending writes: {stray}")
    out = dict(folder=str(f), pages_requested=req["pages"], last_durable_page=expected - 1,
               failing_window_first_page=expected, windows_published=len(windows),
               failure_elapsed_since_dispatch_s=fail["elapsed_since_dispatch_s"],
               failure_type=fail["error"].split("(")[0], published_engine_s=sum(w["engine_s"] for w in windows),
               published_tokens=sum(w["tokens"] for w in windows), windows=windows, problems=problems,
               failure_sha256=hashlib.sha256((f / "failure.json").read_bytes()).hexdigest())
    text = json.dumps(out, indent=1) + "\n"
    if a.out:
        with a.out.open("x", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    print(json.dumps({k: v for k, v in out.items() if k != "windows"}, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
