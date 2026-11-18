"""WP-0017 blind pre-key hash inventory (stage 0 for A1, A2 and A3). Stdlib only. Run before any parse.

Records the SHA-256 of every file in each finished run tree (runtime cache files listed separately), the
coordinator's plan/release record digests, and the process outcome fields of launch.json/process.json when
present. It deliberately omits timings, sizes, text, token values, logits and every other observation, so
the receipt can be committed and pushed before any output is inspected or any scoring key is released.
Every later stage re-verifies the whole tree against this inventory (immutability) before reading.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import sha_file, utc, write_new  # noqa: E402

OUTCOME_KEYS = ("source", "head", "lease", "plan_sha256", "segment_modes", "segment_count")


def inventory(run):
    files, cache = {}, {}
    for f in sorted(Path(run).rglob("*")):
        if f.is_file():
            rel = f.relative_to(run).as_posix()
            (cache if "/cache/" in f"/{rel}" else files)[rel] = sha_file(f)
    return files, cache


def outcome(run):
    launch = run / "launch.json"
    process = run / "process.json"
    lj = json.loads(launch.read_bytes()) if launch.is_file() else {}
    pj = json.loads(process.read_bytes()) if process.is_file() else {}
    segs = pj.get("segments") or []
    return dict(launch={k: lj.get(k) for k in OUTCOME_KEYS if k in lj},
                all_segments_completed=pj.get("all_segments_completed"), overall_reason=pj.get("overall_reason"),
                segment_outcomes=[dict(segment=s.get("segment"), mode=s.get("mode"), returncode=s.get("returncode"),
                                       reason=s.get("reason")) for s in segs])


def build(stage, runs, records, operator=None):
    out = []
    for run in runs:
        run = Path(run)
        files, cache = inventory(run)
        out.append(dict(run=run.name, path=str(run), plan_sha256=sha_file(run / "plan.json") if (run / "plan.json").is_file() else None,
                        **outcome(run),
                        pending_files=sorted(r for r in files if r.endswith(".pending")),
                        failure_files=sorted(r for r in files if r.rsplit("/", 1)[-1].startswith("failure")),
                        predictions={r: h for r, h in files.items() if r.endswith("prediction.json")},
                        files=files, runtime_cache_files=cache))
    return dict(kind=f"WP-0017 {stage} reviewer blind pre-key inventory", reviewer="eld-rd-reviewer", created_utc=utc(),
                stage=stage, records={str(p): sha_file(p) for p in records},
                operator_receipts={str(p): sha_file(p) for p in (operator or [])}, runs=out)


def verify_unchanged(inv):
    """Return the list of runs whose tree differs from the inventory (empty = immutable)."""
    bad = []
    for r in inv["runs"]:
        files, cache = inventory(Path(r["path"]))
        if files != r["files"] or cache != r["runtime_cache_files"]:
            bad.append(r["run"])
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", required=True, choices=["A1", "A2", "A3"])
    ap.add_argument("--runs", type=Path, nargs="+", required=True)
    ap.add_argument("--records", type=Path, nargs="*", default=[], help="release/plan records to bind by digest")
    ap.add_argument("--operator", type=Path, nargs="*", default=[], help="operator receipts to bind by digest")
    ap.add_argument("--out", type=Path, required=True, help="new file")
    a = ap.parse_args()
    inv = build(a.stage, a.runs, a.records, a.operator)
    digest = write_new(a.out, inv)
    print(json.dumps(dict(inventory=str(a.out), sha256=digest,
                          runs=[dict(run=r["run"], completed=r["all_segments_completed"], files=len(r["files"]),
                                     cache_files=len(r["runtime_cache_files"]), pending=len(r["pending_files"]),
                                     failures=len(r["failure_files"])) for r in inv["runs"]]), indent=1))


if __name__ == "__main__":
    main()
