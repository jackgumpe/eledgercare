"""Normal entry for one WP-0044 author CPU route, and standalone offline scoring."""
import argparse
import json
from pathlib import Path
import sys
import time

import controls
from scoring import score

HERE = Path(__file__).resolve().parent
SCHEDULE = HERE.parents[1] / "coordination/WP-0044/schedule.json"


def load(path):
    return json.loads(path.read_bytes())


def run():
    import native
    expected = load(HERE / "expectations.json")
    manifest = load(HERE / "manifest.json")
    schedule = load(SCHEDULE)
    start = time.monotonic()
    directory = native.ROOT / "decisive-v1"
    blind = native.ROOT / "blind"
    directory.mkdir()
    returns, errors = {}, {}

    def emit(key, item):
        if key in returns:
            raise ValueError("duplicate case")
        returns[key] = item
        native.save(directory / (key + ".json"), item)

    try:
        native.run_live(directory, manifest, emit)
    except Exception as exc:
        errors["live"] = repr(exc)
    for row in schedule["rows"]:
        if row["interface"] != "constructed":
            continue
        key = row["id"]
        try:
            path = blind / (key + ".json")
            if path.stat().st_size > 1024 * 1024:
                raise ValueError("constructed record size")
            item = load(path)
            emit(key, {"verdict": score(item), "input_sha256": native.sha(path)})
        except Exception as exc:
            errors[key] = repr(exc)
    for route, operation in [("archive", controls.archive_rows), ("mathematical", controls.math_rows)]:
        try:
            for key, value in operation().items():
                emit(key, {"value": value, "matches": value == expected[key],
                           "source": "pinned public native index" if route == "archive" else "finite arithmetic control",
                           "phase": "score"})
        except Exception as exc:
            errors[route] = repr(exc)
    rows, counts = {}, {}
    for row in schedule["rows"]:
        key, route = row["id"], row["interface"]
        value = returns.get(key, {"error": errors.get(key, errors.get(route, "missing return"))})
        if "verdict" in value:
            verdict = value["verdict"]
            difference = {f: {"expected": v, "observed": verdict.get(f)}
                          for f, v in expected[key].items() if verdict.get(f) != v}
            observed = {k:v for k,v in value.items() if k != "record"}
        else:
            observed = value
            difference = {} if value.get("matches") else {"return": "failed or differing"}
        rows[key] = {"interface": route, **observed, "differences_from_author_target": difference}
        count = counts.setdefault(route, [0, 0])
        count[0] += int(not difference)
        count[1] += 1
    arms = []
    for label in ("first", "second"):
        receipts = directory / label
        if (receipts / "supervision.json").is_file():
            source = load(receipts / "supervision.json")
            source.pop("tag")
            source["all_job_creations"] = [load(p) for p in sorted(receipts.glob("creation-*.json"))]
            arms.append(source)
    duration = time.monotonic() - start
    prior_bytes = sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())
    report = {"denominator": schedule["denominator_per_route"], "rows": rows, "arms": arms,
              "author_target_counts": counts, "errors": errors, "wall_seconds": duration,
              "pre_summary_bytes": prior_bytes, "fixture_creations": sum(len(a["all_job_creations"]) for a in arms),
              "formal_oracle_status": "independent comparison pending"}
    native.save(directory / "public-results.json", report)
    total = sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())
    limits = duration < 300 and total <= 64 * 1024 * 1024 and report["fixture_creations"] <= 12
    print(json.dumps({"rows": len(returns), "author_target_counts": counts, "errors": errors,
                      "total_observation_bytes": total, "limits": limits, "elapsed_s": duration}))
    return 0 if limits and len(returns) == 33 and not errors else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    cmds = parser.add_subparsers(dest="verb", required=True)
    cmds.add_parser("run")
    entry = cmds.add_parser("score")
    entry.add_argument("record", type=Path)
    args = parser.parse_args()
    if args.verb == "score":
        print(json.dumps(score(load(args.record)), ensure_ascii=True, allow_nan=False))
    else:
        sys.exit(run())
