"""WP-0017 A3 hard-gate combinator (eld-rd-reviewer). Stdlib only. Never changes a frozen score.

A3 passes only if ALL hold (specification p.5, assignment), missing evidence failing closed:
  1. derived stage-2 verdict g0_pass is true (completeness, stops, 0 new wrong-source links, CER/cell budget in
     both views and orders, 0 newly unflagged critical vs matched-order native, launcher-sampled device and
     allocator peaks <= 10,000 MiB, clean stage 1/2, real binding);
  2. trial arm static_cache_reallocations == 0 in both orders, with the counter present, when S2 is on in the
     frozen candidate; with S2 off it is reported as dynamic-only;
  3. coordinator external sampler: board used_mib peak <= 10,000 over every sample of each order's lease;
  4. Packet A speed: saving > 0 in both orders and the smaller saving exceeds both |AB - BA| repeat spreads.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Check, load, sha_file, utc, write_new  # noqa: E402

PEAK_MAX = 10000


def gate(s1, s2, device, trial="carbon_surgical", s2_enabled=True):
    """Pure. device = {order: [used_mib, ...]} from the coordinator sampler. s2_enabled from the frozen
    candidate bit vector: with S2 off the static-cache criterion is reported as dynamic-only (not applicable)."""
    res = {}
    res["stage2_g0_pass"] = bool(s2.get("verdict", {}).get("g0_pass"))
    cache = {}
    for name, r in s1["runs"].items():
        o = r["order"]
        s = r["arms"].get(trial, {}).get("summary", {})
        present = s.get("counters_present", {}).get("static_cache_reallocations")
        cache[o] = dict(present=bool(present), value=s.get("counters", {}).get("static_cache_reallocations"))
    res["static_cache"] = cache
    if s2_enabled:
        res["static_cache_mode"] = "static (S2 on): counter must be present and zero in both orders"
        res["static_cache_ok"] = sorted(cache) == ["ab", "ba"] and all(v["present"] and v["value"] == 0 for v in cache.values())
    else:
        res["static_cache_mode"] = "dynamic-only (S2 off): static-cache growth not applicable"
        res["static_cache_ok"] = sorted(cache) == ["ab", "ba"]
    peaks = {o: (max(v) if v else None) for o, v in device.items()}
    res["board_peak_mib"] = peaks
    res["board_peak_ok"] = sorted(peaks) == ["ab", "ba"] and all(p is not None and p <= PEAK_MAX for p in peaks.values())
    t = s1.get("timing", {}).get("A", {})
    pairs = t.get("pairs", {})
    sv = [pairs.get(o, {}).get("saving_s") for o in ("ab", "ba")]
    spread = t.get("repeat_spread_s", {})
    sp = [spread.get("native"), spread.get(trial)]
    ok = None not in sv and None not in sp and min(sv) > 0 and min(sv) > max(sp)
    res["speed"] = dict(savings_s=sv, spreads_s=dict(native=sp[0], trial=sp[1]), ok=bool(ok))
    res["a3_pass"] = bool(res["stage2_g0_pass"] and res["static_cache_ok"] and res["board_peak_ok"] and ok)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage1", type=Path, required=True)
    ap.add_argument("--stage2", type=Path, required=True)
    ap.add_argument("--device", nargs=2, action="append", metavar=("ORDER", "JSONL"), required=True,
                    help="coordinator sampler jsonl per order (ab/ba)")
    ap.add_argument("--trial", default="carbon_surgical")
    ap.add_argument("--candidate-bits", required=True, help="frozen 6-bit S0..S3 vector of carbon_surgical")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    check = Check()
    s1, s2 = load(a.stage1), load(a.stage2)
    check(s2["stage1_sha256"] == sha_file(a.stage1), "stage 2 was produced from this stage 1")
    device, dev_sha = {}, {}
    for order, path in a.device:
        rows = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
        device[order] = [r["used_mib"] for r in rows]
        dev_sha[order] = sha_file(path)
    check(len(a.candidate_bits) == 6 and set(a.candidate_bits) <= {"0", "1"}, "candidate bit vector")
    res = gate(s1, s2, device, a.trial, s2_enabled=a.candidate_bits[4] == "1")
    res["a3_pass"] = res["a3_pass"] and not check.failures
    rec = dict(kind="WP-0017 A3 reviewer hard gate", reviewer="eld-rd-reviewer", created_utc=utc(),
               stage1_sha256=sha_file(a.stage1), stage2_sha256=sha_file(a.stage2), device_jsonl_sha256=dev_sha,
               result=res, checks_run=check.count, failures=check.failures)
    digest = write_new(a.out, rec)
    print(json.dumps(dict(out=str(a.out), sha256=digest, a3_pass=res["a3_pass"], failures=check.failures), indent=1))
    return 0 if res["a3_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
