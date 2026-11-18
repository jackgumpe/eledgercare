"""WP-0017 Stage A2 balanced-order check and stop-loss decision (eld-rd-reviewer). Stdlib only, CPU only.

Three arms (native, carbon_bf16, frozen carbon_surgical) on the fresh 18-page dev/id_ablation packet, in two
matched reversed orders, each arm a fresh process (segment). This tool:

1. `orders`: checks a coordinator A2 plan record: exactly the three arms once per order, order 2 = reverse
   of order 1, the dev packet's source/RGB pins identical across all six arm requests, and records which arm
   positions are balanced (the middle arm keeps the middle position in both orders; this is reported).
2. `decide`: after the committed blind inventory (escrow.py --stage A2) and the separate dev-key release,
   re-verifies the run trees against that inventory, reads each arm's durable clock (timing.json
   elapsed_s = document_committed_ns - accepted_ns) and completeness, requires flagged == false on every
   span/cell, scores every arm with the frozen score.py in its own OS process, and applies the frozen rule:

   ADVANCE iff, in BOTH orders o:
     a. complete matched native/surgical pair, matched critical paths, all windows stopped;
     b. zero newly unflagged critical errors native_o -> surgical_o (README rule 3);
     c. full-Carbon saving C_o = T(native_o) - T(carbon_o) > 0;
     d. retention R_o = (T(native_o) - T(surgical_o)) / C_o >= 0.60;
   and min_o (T(native_o) - T(surgical_o)) > max(|T(native_o1) - T(native_o2)|, |T(surgical_o1) - T(surgical_o2)|).
   Missing evidence fails closed. Pooled retention and carbon_bf16's own safety are telemetry only.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Check, all_flags_false, load, run_score, sha, sha_file, transitions, utc, write_new  # noqa: E402

ARMS = ("native", "carbon_bf16", "carbon_surgical")
RETENTION_MIN = 0.60  # specification p.4 and assignment; not tunable


def check_orders(record, check):
    orders = record["orders"]
    names = sorted(orders)
    check(len(names) == 2, "exactly two A2 orders")
    seqs = {o: list(orders[o]["order"]) for o in names}
    for o, s in seqs.items():
        check(sorted(s) == sorted(ARMS), f"{o}: each of the three arms exactly once")
    if len(names) == 2:
        check(seqs[names[1]] == seqs[names[0]][::-1], "order 2 is the exact reverse of order 1")
    pos = {m: [seqs[o].index(m) for o in names] for m in ARMS if all(m in seqs[o] for o in names)}
    return dict(orders=seqs, positions=pos,
                position_balanced={m: len(set(p)) == len(p) for m, p in pos.items()},
                note="matched reversed orders balance first/last position; the middle arm stays in the middle")


def split_segments(requests):
    segments = []
    for req in requests:
        if not segments or segments[-1][0] != req["mode"]:
            segments.append((req["mode"], [req]))
        else:
            segments[-1][1].append(req)
    return segments


def read_run(run, check, label):
    """Measured (non-warm-up) documents per arm in the WP-0016 segmented layout."""
    plan = load(run / "plan.json")
    arms = {}
    for si, (mode, reqs) in enumerate(split_segments(plan["requests"]), 1):
        seg = run / f"segment-{si:02d}-{mode}"
        for i, req in enumerate(reqs, 1):
            folder = seg / f"{i:02d}-{req['label']}-{req['mode']}"
            if req.get("warmup"):
                continue
            t = load(folder / "timing.json")
            pred = folder / "prediction.json"
            ok = check(t.get("status") == "completed" and t.get("complete_pages") == req["pages"]
                       and t["prediction_sha256"] == sha_file(pred), f"{run.name}/{mode}/{req['label']}: complete and bound")
            check(abs(t["elapsed_s"] - (t["document_committed_ns"] - t["accepted_ns"]) / 1e9) < 1e-6,
                  f"{run.name}/{mode}/{req['label']}: elapsed = committed - accepted")
            stops = []
            for w in sorted(folder.glob("window-*.json")):
                d = load(w)
                stops.append(d.get("finish_reason") == "stop" and d.get("num_pages_out") == d.get("expected_pages"))
            check(stops and all(stops), f"{run.name}/{mode}/{req['label']}: every window stopped with full pages")
            p = load(pred)
            check(all_flags_false(p), f"{run.name}/{mode}/{req['label']}: flagged == false everywhere (locked)")
            check(mode not in arms, f"{run.name}: one measured document per arm")
            arms[mode] = dict(folder=str(folder), prediction=str(pred), prediction_sha256=sha_file(pred),
                              complete_s=t["elapsed_s"], pages=req["pages"], complete=ok,
                              windows=len(stops), source_sha256=req["sha256"], rgb_sha256=req["rgb_sha256"])
    return arms


def stoploss(T, safety):
    """Pure rule. T[(order, arm)] = seconds; safety[order] = dict(new_unflagged, matched, complete)."""
    orders = sorted({o for o, _ in T})
    res, ok = {}, len(orders) == 2
    for o in orders:
        tn, tc, ts = T.get((o, "native")), T.get((o, "carbon_bf16")), T.get((o, "carbon_surgical"))
        if None in (tn, tc, ts) or o not in safety:
            res[o] = dict(missing=True)
            ok = False
            continue
        c, s = tn - tc, tn - ts
        r = s / c if c > 0 else None
        sf = safety[o]
        passed = dict(complete=bool(sf["complete"]), matched=bool(sf["matched"]), safety=sf["new_unflagged"] == 0,
                      carbon_saving_positive=c > 0, retention=r is not None and r >= RETENTION_MIN)
        res[o] = dict(native_s=tn, carbon_s=tc, surgical_s=ts, carbon_saving_s=c, surgical_saving_s=s,
                      retention=r, new_unflagged=sf["new_unflagged"], passed=passed)
        ok = ok and all(passed.values())
    if len(orders) == 2 and all(not res[o].get("missing") for o in orders):
        o1, o2 = orders
        spread_n = abs(T[(o1, "native")] - T[(o2, "native")])
        spread_s = abs(T[(o1, "carbon_surgical")] - T[(o2, "carbon_surgical")])
        spread_c = abs(T[(o1, "carbon_bf16")] - T[(o2, "carbon_bf16")])
        min_saving = min(res[o]["surgical_saving_s"] for o in orders)
        outside = min_saving > max(spread_n, spread_s)
        pooled_c = sum(res[o]["carbon_saving_s"] for o in orders)
        res["spreads"] = dict(native_s=spread_n, surgical_s=spread_s, carbon_s=spread_c, min_surgical_saving_s=min_saving,
                              saving_exceeds_both_spreads=outside,
                              pooled_retention_telemetry=(sum(res[o]["surgical_saving_s"] for o in orders) / pooled_c)
                              if pooled_c > 0 else None)
        ok = ok and outside
    else:
        ok = False
    res["advance"] = bool(ok)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("orders")
    o.add_argument("--plans", type=Path, required=True)
    o.add_argument("--plans-sha256", required=True)
    d = sub.add_parser("decide")
    d.add_argument("--plans", type=Path, required=True)
    d.add_argument("--plans-sha256", required=True)
    d.add_argument("--inventory", type=Path, required=True)
    d.add_argument("--pins", type=Path, required=True, help="materialized pins dir containing score.py")
    d.add_argument("--truth", type=Path, required=True, help="released dev key (passed only to score.py)")
    d.add_argument("--truth-sha256", required=True, help="custody commitment of the dev key")
    d.add_argument("--out", type=Path, required=True, help="new private directory")
    a = ap.parse_args()
    check = Check()
    check(sha_file(a.plans) == a.plans_sha256, "A2 plan record digest")
    record = load(a.plans)
    orders = check_orders(record, check)
    if a.cmd == "orders":
        print(json.dumps(dict(orders, checks=check.count, failures=check.failures), indent=1))
        return 0 if not check.failures else 1
    from escrow import verify_unchanged  # noqa: PLC0415
    inv = load(a.inventory)
    check(not verify_unchanged(inv), "A2 run tree changed since the blind inventory")
    check(sha_file(a.truth) == a.truth_sha256, "dev key equals its custody commitment")
    a.out.mkdir(parents=True, exist_ok=False)
    T, safety, arms_all, comps = {}, {}, {}, {}
    plan_by_sha = {b["sha256"]: name for name, b in record["orders"].items()}
    for ir in inv["runs"]:
        run = Path(ir["path"])
        oname = plan_by_sha.get(ir["plan_sha256"])
        if not check(oname is not None, f"{ir['run']}: plan not in the A2 record"):
            continue
        arms = read_run(run, check, oname)
        check(sorted(arms) == sorted(ARMS), f"{oname}: all three arms measured")
        src = {(x["source_sha256"], tuple(x["rgb_sha256"])) for x in arms.values()}
        check(len(src) == 1, f"{oname}: identical dev source/RGB across arms")
        scores = {}
        for m, x in arms.items():
            T[(oname, m)] = x["complete_s"]
            scores[m] = run_score(a.pins, a.truth, x["prediction"], a.out / f"{oname}-{m}.score.json")
        for trial in ("carbon_surgical", "carbon_bf16"):
            if "native" in scores and trial in scores:
                cmp = run_score(a.pins, a.truth, arms[trial]["prediction"], a.out / f"{oname}-native__{trial}.json",
                                arms["native"]["prediction"])["comparison"]
                tr, rows = transitions(scores["native"], scores[trial])
                novel = {c["at"] for c in cmp["new_or_changed_critical_errors"]}
                mine = {r["at"] for r in rows if r["kind"] in ("regress", "abstain", "persist_changed")}
                check(novel == mine, f"{oname} native->{trial}: transitions agree with frozen compare")
                comps[f"{oname}:native->{trial}"] = dict(critical=tr, complete_matched_pair=cmp["complete_matched_pair"],
                                                        delta=cmp["delta"], new_wrong_source_links=len(cmp["new_wrong_source_links"]))
                write_new(a.out / f"{oname}-native__{trial}.details.json", dict(note="PRIVATE", rows=rows))
        g = comps.get(f"{oname}:native->carbon_surgical")
        if g:
            safety[oname] = dict(new_unflagged=g["critical"]["new_unflagged"], matched=g["critical"]["matched_paths"],
                                 complete=g["complete_matched_pair"] and arms["native"]["complete"] and arms["carbon_surgical"]["complete"])
        arms_all[oname] = {m: {k: v for k, v in x.items() if k not in ("rgb_sha256",)} for m, x in arms.items()}
    rule = stoploss(T, safety)
    advance = rule["advance"] and not check.failures
    summary = dict(kind="WP-0017 A2 reviewer stop-loss decision", reviewer="eld-rd-reviewer", created_utc=utc(),
                   plans_sha256=a.plans_sha256, inventory_sha256=sha_file(a.inventory), truth_sha256=a.truth_sha256,
                   orders=orders, arms=arms_all, comparisons=comps, rule=rule, checks_run=check.count,
                   failures=check.failures, advance_to_A3=advance,
                   outcome="ADVANCE_TO_A3" if advance else "HALT_AT_A2")
    digest = write_new(a.out / "summary.json", summary)
    print(json.dumps(dict(summary=str(a.out / "summary.json"), sha256=digest, outcome=summary["outcome"],
                          failures=check.failures[:20]), indent=1))
    return 0 if advance else 1


if __name__ == "__main__":
    sys.exit(main())
