"""Freeze output-only identities after the G0 orders. No access to truth or expected text."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(lease):
    orders = []
    for order in lease["orders"]:
        run = Path(order["output"])
        reqs = read(Path(order["plan"]))["requests"]
        assert sha(run / "plan.json") == order["plan_sha256"]
        launch = read(run / "launch.json")
        process = read(run / "process.json")
        assert launch["source"] == lease["review_worktree_head"] and launch["lease"] == order["run"]
        assert process["all_segments_completed"] and len(process["segments"]) == 2
        docs, modes = [], []
        for seg in process["segments"]:
            mode = seg["mode"]
            modes.append(mode)
            folder = run / f"segment-{seg['segment']:02d}-{mode}"
            subplan = read(folder / "plan.json")["requests"]
            assert subplan == [r for r in reqs if r["mode"] == mode] and len(subplan) == 5
            session = read(folder / "session.json")
            assert len(session) == len(subplan) and not seg["returncode"] and not seg["reason"]
            for i, req in enumerate(subplan, 1):
                request = folder / f"{i:02d}-{req['label']}-{mode}"
                timing = read(request / "timing.json")
                pred = read(request / "prediction.json")
                assert timing == session[i-1] and timing["request"] == req and timing["status"] == "completed"
                assert pred["source_sha256"] == req["sha256"] == sha(Path(req["pdf"]))
                assert len(pred["pages"]) == req["pages"] == timing["complete_pages"]
                assert timing["prediction_sha256"] == sha(request / "prediction.json")
                stops = []
                for first in range(1,req["pages"]+1,3):
                    w = read(request / f"window-{first:03d}.json")
                    n = min(3,req["pages"]-first+1)
                    assert w["first_page"] == first and w["source_sha256"] == req["sha256"]
                    assert w["finish_reason"] == "stop" and w["num_pages_out"] == n == w["expected_pages"]
                    ids, strings = [], []
                    for page in range(first,first+n):
                        raw = read(request / f"raw-{page:03d}.json")
                        p = read(request / f"page-{page:03d}.json")
                        assert p == pred["pages"][page-1] and p["state"] == "complete"
                        assert p["page"] == raw["page"] == page and p["source_sha256"] == raw["source_sha256"] == req["sha256"]
                        assert raw["rgb_sha256"] == req["rgb_sha256"][page-1]
                        ids.extend(raw["token_ids"])
                        strings.append(raw["raw_output"])
                    assert ids == w["window_token_ids"] and "".join(strings) == w["raw_output"]
                    stops.append({"from":first,"pages":n,"tokens":len(ids),"finish":w["finish_reason"],
                                  "reserved_bytes":w["vram"]["cuda_max_reserved_bytes"],
                                  "allocated_bytes":w["vram"]["cuda_max_allocated_bytes"],
                                  "cache_reallocations":w.get("static_cache_reallocations"),
                                  "prefill_fallback_layer_calls":w.get("prefill_moe_fallback_layer_calls")})
                docs.append({"mode":mode,"label":req["label"],"excluded":req["warmup"],"pages":req["pages"],
                             "elapsed_s":timing["elapsed_s"],"windows":stops,"source_sha256":req["sha256"],
                             "prediction_sha256":timing["prediction_sha256"],
                             "blobs":{p.name:sha(p) for p in sorted(request.glob("*.json"))}})
        assert modes == list(dict.fromkeys(r["mode"] for r in reqs))
        assert sum(len(d["windows"]) for d in docs if d["excluded"]) == 6
        assert sum(len(d["windows"]) for d in docs if not d["excluded"]) == 44
        orders.append({"name":order["run"],"process_sha256":sha(run/"process.json"),"docs":docs})
    return {"gate":"G0","source":lease["review_worktree_head"],"orders":orders}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("release",type=Path)
    p.add_argument("out",type=Path)
    a = p.parse_args()
    result = inspect(read(a.release))
    with a.out.open("x",encoding="utf8",newline="\n") as out:
        json.dump(result,out,indent=2)
        out.write("\n")
