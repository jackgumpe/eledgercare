"""Summarize issued physical device calls, including incomplete work and excluded W0 time."""
from argparse import ArgumentParser
from datetime import datetime
import json
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
HOST = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0026")


def read(path):
    return json.loads(path.read_bytes()) if path.exists() else {}


def order_cost(order, lease, run):
    folder = Path(order["output"]) / "sensor"
    plan = read(Path(order["plan"]))
    guard = HOST / "coordination/leases" / lease
    issued = read(guard / (run+"-issued.json"))
    returned = read(guard / (run+"-returned.json"))
    telemetry = guard / (run+"-device.jsonl")
    samples = [json.loads(line) for line in telemetry.read_bytes().splitlines()] if telemetry.exists() else []
    cold = read(folder/"cold.json")
    warm = read(folder/"warmup.json")
    rows, started = {}, []
    for call in plan["calls"]:
        tag = call["tag"]
        if (folder / (tag+"-begin.json")).exists():
            started.append(tag)
        result = read(folder / tag / "duration.json")
        if result and (folder / tag / "receipt.json").exists():
            rows[tag] = result
    captured_s = sum(r["complete_window_wall_ns"] for r in rows.values()) / 1e9
    wall_s = sum(r["wall_inference_ns"] for r in rows.values()) / 1e9
    w0_s = warm.get("elapsed_ns")
    observed_start = (folder/"warmup-begin.json").exists()
    return {"phase":plan["phase"], "split":plan["split"], "lease":lease, "process":run,
            "guard_issued_utc":issued.get("issued"), "guard_returned_utc":returned.get("utc"),
            "supervised_s":returned.get("wall_s"), "exit":returned.get("exit"), "guard_reason":returned.get("guard"),
            "pid":cold.get("pid"), "model_load_id":cold.get("model_load_id"), "completed_loads":int(bool(cold)),
            "load_s":cold["elapsed_ns"]/1e9 if cold else None,
            "w0_calls_started":int(observed_start), "w0_qualified":bool(warm.get("success")),
            "w0_s":w0_s/1e9 if w0_s is not None else None,
            "w0_inference_s":warm["wall_inference_ns"]/1e9 if "wall_inference_ns" in warm else None,
            "scored_started":len(started), "scored_verified":len(rows), "scored_inference_s":wall_s,
            "scored_with_capture_s":captured_s, "unverified_scored_tags":[t for t in started if t not in rows],
            "board_samples":len(samples), "board_sampled_peak_mib":max((r["used_mib"] for r in samples),default=None),
            "board_total_mib":max((r["total_mib"] for r in samples),default=None),
            "board_mean_used_mib":round(mean(r["used_mib"] for r in samples),2) if samples else None,
            "scored_emitted_before_eos":sum(r["emitted"] for r in rows.values()),
            "evidence":str(folder)}


def summarize(releases):
    records = []
    seen = set()
    for path in releases:
        release = read(path)
        for order in release["orders"]:
            key = (release["name"], order["run"])
            if key in seen:
                raise ValueError("Repeated physical order")
            seen.add(key)
            records.append(order_cost(order,*key))
    totals = {key:sum(r[key] or 0 for r in records) for key in
              ("completed_loads","load_s","w0_calls_started","w0_qualified","w0_s","w0_inference_s","scored_started",
               "scored_verified","scored_inference_s","scored_with_capture_s","supervised_s","board_samples")}
    totals["physical_calls_started"] = totals["w0_calls_started"] + totals["scored_started"]
    totals["peak_board_mib"] = max((r["board_sampled_peak_mib"] for r in records if r["board_samples"]), default=None)
    times = [datetime.fromisoformat(r[k]) for r in records for k in ("guard_issued_utc","guard_returned_utc") if r[k]]
    totals["first_issue_to_last_return_s_including_interphase_gaps"] = (max(times)-min(times)).total_seconds() if times else None
    return {"orders":records,"totals":totals,
            "timing_basis":"Elapsed load is the Native constructor. W0 includes raster I/O and terminal checks. "
            "Scored inference times the stock model call; the capture measure includes the instrumented serialization. "
            "Each supervised order includes Python startup and checks. Board memory is the maximum whole-board sample."}


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("releases",type=Path,nargs="+")
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    report=summarize(args.releases)
    if args.out:
        with args.out.open("x",encoding="utf8",newline="\n") as f:
            json.dump(report,f,indent=2)
            f.write("\n")
    else:
        print(json.dumps(report["totals"],indent=2))
