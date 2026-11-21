"""Report Baidu wall time, board samples and cached probe costs from completed runs."""
from argparse import ArgumentParser
import json
from pathlib import Path
from statistics import mean


HOST = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024")


def read(path):
    return json.loads(path.read_bytes())


def gpu_phase(plan_path):
    plan = read(plan_path)
    label = plan["lease"]
    folder = HOST / "coordination/leases" / label
    sensor = Path(plan["output"]) / "sensor"
    if read(folder / "returned.json")["error"] is not None:
        raise ValueError("Guard did not return cleanly")
    order = read(folder / (label + "-returned.json"))
    samples = [json.loads(line) for line in (folder / (label + "-device.jsonl")).read_bytes().splitlines()]
    outcome = read(sensor / "outcome.json")
    cold = read(sensor / "cold.json")
    rows = outcome["rows"]
    if set(rows) != {call["tag"] for call in plan["calls"]} or not samples or order["exit"] != 0:
        raise ValueError("Incomplete device order")
    raster_keys = {tuple(page["rgb_sha256"] for page in call["pages"]) for call in plan["calls"]}
    delivery = plan.get("delivery") or {}
    return {
        "label": label, "phase": plan["phase"], "split": plan.get("split", "h0"),
        "unique_source_windows": len(raster_keys), "true_singleton_calls": len(rows),
        "emitted_tokens": sum(row["emitted"] for row in rows.values()),
        "whole_supervised_s": order["wall_s"], "complete_sensor_phase_s": outcome["complete_phase_s"],
        "sum_complete_window_s": outcome["window_metric_sum_s"],
        "sum_native_infer_s": sum(row["wall_inference_ns"] for row in rows.values()) / 1e9,
        "native_cold_load_s": cold["model"]["load_ms"] / 1000,
        "board_total_mib": max(s["total_mib"] for s in samples),
        "whole_board_peak_sampled_mib": max(s["used_mib"] for s in samples),
        "whole_board_samples": len(samples),
        "delivery_window_references": sum(
            len(t["windows"]) for pair in delivery.get("pairs", []) for t in pair["twins"]
        ),
    }


def cache_metrics(telemetry_path):
    telemetry = read(telemetry_path)
    rows = telemetry["cached_cpu"]
    ms = [ns / 1e6 for row in rows if row["arm"] == "M3" for ns in row["window_ns"]]
    host_bytes = [n for row in rows if row["arm"] == "M2" for n in row["live_host_bytes"]]
    if not ms or not host_bytes:
        raise ValueError("Missing M3 cached window or M2 memory evidence")
    registry = {}
    for arm in sorted({row["arm"] for row in rows}):
        records = [row for row in rows if row["arm"] == arm]
        # Each arm exports cumulative lookup time per binder. The number of calls
        # depends on the online records observed and is not emitted by the probe.
        totals = [row["lookup_ns"] for row in records]
        if any(type(ns) is not int or ns < 0 for ns in totals):
            raise ValueError("Invalid per-binder lookup total")
        registry[arm] = {
            "by_binder": [
                {"binder": row["binder"], "size_by_window": row["registry_growth"], "lookup_ns": row["lookup_ns"]}
                for row in records
            ],
            "binders": len(records), "lookup_total_ns": sum(totals), "mean_total_lookup_ns_per_binder": mean(totals),
        }
    return {
        "probe_vram_mib": telemetry["probe_cuda_allocated_bytes"] / 1024**2,
        "cached_probe_ms_per_window": mean(ms), "m2_host_bytes": max(host_bytes), "cached_window_count": len(ms),
        "cached_min_ms": min(ms), "cached_max_ms": max(ms), "registry": registry,
    }


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--plan", type=Path, action="append", default=[])
    parser.add_argument("--telemetry", type=Path)
    parser.add_argument("--fit", type=Path)
    parser.add_argument("--cpu-receipt", type=Path, action="append", default=[])
    args = parser.parse_args()
    phases = [gpu_phase(path) for path in args.plan]
    if len({p["label"] for p in phases}) != len(phases):
        raise ValueError("Cannot double-count a GPU release")
    result = {"sensor_phases": phases}
    if phases:
        result["complete_supervised_baidu_s"] = sum(p["whole_supervised_s"] for p in phases)
        result["sum_native_infer_s"] = sum(p["sum_native_infer_s"] for p in phases)
    if args.telemetry:
        result.update(cache_metrics(args.telemetry))
    if args.fit:
        fit = read(args.fit)
        result["training"] = fit["training"]
        result["model_calibration_thresholds"] = fit["thresholds"]
    result["cpu_operations"] = [read(path) for path in args.cpu_receipt]
    with args.out.open("x", encoding="utf8", newline="\n") as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write("\n")


if __name__ == "__main__":
    main()
