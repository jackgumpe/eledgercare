"""Apply the same single-object evaluator to committed public or staged blind inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

from clauses import evaluate

HERE = Path(__file__).resolve().parent
SCHEDULE = HERE.parent / "schedule.json"
if not SCHEDULE.exists():
    SCHEDULE = HERE.parents[1] / "coordination" / "WP-0045" / "schedule.json"


def save(path, value):
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["blind", "public"])
    parser.add_argument("out", type=Path)
    parser.add_argument("--inputs", type=Path)
    args = parser.parse_args()
    if sys.version_info[:3] != (3, 12, 10):
        raise ValueError("qualification uses CPython 3.12.10")
    args.out.mkdir(parents=True, exist_ok=False)
    if args.mode == "public":
        fixtures = json.loads((HERE / "fixtures.json").read_bytes())
        cases = [(k, lambda k=k: json.dumps(fixtures[k]["input"], separators=(",", ":")).encode())
                 for k in fixtures]
    else:
        schedule = json.loads(SCHEDULE.read_bytes())["rows"]
        cases = [(k, lambda k=k: (args.inputs / (k + ".json")).read_bytes())
                 for clause in ("A1", "A2", "C1") for k in schedule[clause]]
    returns, digests, failures = {}, {}, {}
    start = time.monotonic()
    for key, read in cases:
        try:
            before = time.monotonic()
            raw = read()
            digests[key] = hashlib.sha256(raw).hexdigest()
            returns[key] = evaluate(json.loads(raw))
            if time.monotonic() - before > 30:
                raise TimeoutError("30 seconds per fixture")
            if args.mode == "public" and returns[key] != fixtures[key]["expected"]:
                raise AssertionError("independently predicted row differs")
        except Exception:
            failures[key] = traceback.format_exc()
    save(args.out / "returns.json", returns)
    save(args.out / "input-sha256.json", digests)
    save(args.out / "failures.json", failures)
    elapsed = time.monotonic() - start
    print(f"{len(returns)} of {len(cases)} returned; {len(failures)} failures, {elapsed:.4f} seconds")
    if failures or elapsed > 300 or sum(p.stat().st_size for p in args.out.iterdir()) > 64 << 20:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
