"""Stage 0: blind hash inventory of finished WP-0016 runs. Stdlib only. Run before anything parses outputs.

Records the SHA-256 of every file in each run tree (runtime cache files are hashed too, and listed
separately), plus the plan, source, lease and process-outcome bindings. It deliberately omits timings,
sizes, text, token values and every other observation, so it can be committed as an escrow receipt before
any prediction is inspected or any scoring key is released. Later stages re-verify every hash.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PINS, is_pinned, load, order_of, sha_file, utc, write_new  # noqa: E402


def inventory(run):
    files, cache = {}, {}
    for f in sorted(Path(run).rglob("*")):
        if f.is_file():
            rel = f.relative_to(run).as_posix()
            (cache if "/cache/" in f"/{rel}" else files)[rel] = sha_file(f)
    return files, cache


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, nargs="+", required=True)
    ap.add_argument("--plans", type=Path, required=True, help="coordinator plan record (pinned g0-plans.json)")
    ap.add_argument("--gate", default="G0")
    ap.add_argument("--out", type=Path, required=True, help="new file")
    a = ap.parse_args()
    record = load(a.plans)
    runs = []
    for run in a.runs:
        files, cache = inventory(run)
        launch = json.loads((run / "launch.json").read_bytes()) if (run / "launch.json").exists() else {}
        process = json.loads((run / "process.json").read_bytes()) if (run / "process.json").exists() else {}
        plan_sha = sha_file(run / "plan.json") if (run / "plan.json").exists() else None
        segs = process.get("segments") or []
        runs.append(dict(
            run=run.name, path=str(run), source=launch.get("source"), head=launch.get("head"), lease=launch.get("lease"),
            plan_sha256=plan_sha, launch_plan_sha256=launch.get("plan_sha256"), order=order_of(record, plan_sha),
            segment_modes=launch.get("segment_modes"), all_segments_completed=process.get("all_segments_completed"),
            overall_reason=process.get("overall_reason"),
            segment_outcomes=[dict(segment=s.get("segment"), mode=s.get("mode"), returncode=s.get("returncode"),
                                   reason=s.get("reason")) for s in segs],
            pending_files=[r for r in files if r.endswith(".pending")],
            failure_files=[r for r in files if r.rsplit("/", 1)[-1].startswith("failure")],
            predictions={r: h for r, h in files.items() if r.endswith("/prediction.json")},
            files=files, runtime_cache_files=cache))
    inv = dict(kind=f"WP-0016 {a.gate} reviewer blind pre-key inventory", reviewer="eld-rd-reviewer", created_utc=utc(),
               plans_record_sha256=sha_file(a.plans), plans_record_pinned=is_pinned(a.plans, "g0-plans.json"),
               pinned_plans_record_expected=PINS["g0-plans.json"][2],
               orders_present=sorted(r["order"] for r in runs if r["order"]), runs=runs)
    digest = write_new(a.out, inv)
    print(json.dumps(dict(inventory=str(a.out), sha256=digest, plans_record_pinned=inv["plans_record_pinned"],
                          runs=[dict(run=r["run"], order=r["order"], completed=r["all_segments_completed"],
                                     files=len(r["files"]), cache_files=len(r["runtime_cache_files"]),
                                     predictions=r["predictions"]) for r in runs]), indent=1))


if __name__ == "__main__":
    main()
