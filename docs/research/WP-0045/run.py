"""Frozen normal route. Native, abstract and archive requests are distinguished by content."""
import argparse
import hashlib
from pathlib import Path
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native
import score
import state as s
import win

OLD = s.HERE.parents[1] / "coordination/WP-0044/disposition.json"

def archive(raw):
    if raw != {"clause": "archive", "packet": "WP-0044"}:
        raise ValueError("unknown archived request")
    if s.sha(OLD) != "f0a126012df16c2df2695f072d300fdb3b3196780c8cef183e66a42ca74e3a14" or s.sha(s.HERE.parent / "WP-0044/blind-results.json") != "4a407a3c75ac4e1447a8cdc4bd5d2553fef72b3f7f4cec8ad302cfd7f6764502":
        raise ValueError("archive pin mismatch")
    old = s.read(OLD)
    count = old["genuine_all_P"]
    gap = old["smallest_shared_unmet_obligation"]
    if "E.parent" not in gap or "do not identify this caller" not in gap:
        raise ValueError("superseded archive record")
    old_rows = s.read(s.HERE.parent / "WP-0044/blind-results.json")
    # This historical projection selects the two genuine outcomes in joint custody.
    old_status = [old_rows["rows"][name]["verdict"]["joint"] for name in ("W1.A", "W1.B")]
    if old_status != ["U", "U"]:
        raise ValueError("unexpected old genuine results")
    return {"old_joint": old_status[0], "author_genuine_P": count["author"],
            "reviewer_genuine_P": count["reviewer"], "genuine_per_route": count["scheduled_per_route"],
            "direct_edge": "unobserved"}

def evaluate(raw, dest, manifest):
    if "expected" in raw:
        return score.project(raw)
    if raw.get("clause") == "archive":
        return archive(raw)
    if raw.get("clause") == "Q1" and set(raw) == {"clause","selection","payload_hex"}:
        return native.collect(dest / ("arm-" + str(raw["selection"])), raw, manifest)
    raise ValueError("unknown typed request")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["run","dev","record"])
    p.add_argument("arg", nargs="?")
    p.add_argument("--manifest", type=Path, default=s.HERE / "manifest.json")
    args = p.parse_args()
    if args.mode == "record":
        raw = s.read(args.arg)
        if "expected" not in raw and raw.get("clause") != "archive":
            raise ValueError("single-record offline entry accepts constructed or archive only")
        print(s.encode(evaluate(raw, None, None)).decode())
        return
    win.ordinary()
    start = time.monotonic()
    root = s.role_root()
    manifest = s.read(args.manifest)
    if args.mode == "dev":
        dest = root / args.arg
        if dest.parent != root or not dest.name.startswith("smoke-"):
            raise ValueError("use distinct owned smoke directory")
        dest.mkdir()
        answer = evaluate({"clause":"Q1","selection":0,"payload_hex":"44657621"},dest,manifest)
        s.save(dest / "dev-result.json",answer)
        print(answer["status"],answer["conflicts"],answer["missing"])
        return
    if args.arg is not None:
        raise ValueError("no decisive override")
    schedule = score.SCHEDULE["rows"]
    ids = schedule["live"] + schedule["constructed"] + schedule["archive"]
    dest = root / "decisive-01"
    dest.mkdir()
    (dest / "rows").mkdir()
    hashes, results, failures = {}, {}, {}
    expected_inputs = s.read(root / "blind-digests.json")
    for case in ids:
        try:
            if time.monotonic() - start > 270:
                raise TimeoutError("route ceiling")
            f = root / "blind" / (case + ".json")
            payload = f.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            if expected_inputs[case] != digest:
                raise ValueError("precommitted input digest mismatch")
            import json
            result = evaluate(json.loads(payload), dest, manifest)
            s.save(dest / "rows" / (case + ".json"), result)
            results[case], hashes[case] = result, digest
        except Exception:
            failures[case] = traceback.format_exc()
    s.save(dest / "results.json", results)
    s.save(dest / "input-sha256.json", hashes)
    s.save(dest / "errors.json", failures)
    measured = {f.relative_to(dest).as_posix(): s.sha(f) for f in sorted(dest.rglob("*")) if f.is_file()}
    s.save(dest / "private-commitments.json", measured)
    size = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
    s.save(dest / "capacities.json", {"elapsed_s": time.monotonic()-start, "bytes_before_capacity_record":size,
                                     "rows":len(results),"error_rows":list(failures)})
    job_counts = [s.read(f).get("job_total_processes") for f in dest.glob("arm-*/supervisor-call.json")]
    if (len(job_counts) != 2 or any(x is None for x in job_counts)
            or sum(job_counts) + 2 > 12 or size > 64*1024*1024 or time.monotonic()-start > 300 or failures):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
