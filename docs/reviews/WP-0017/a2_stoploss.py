"""WP-0017 Stage A2 order check and stop-loss decision (eld-rd-reviewer), synchronized with design 1fad21c.

Stdlib only, CPU only. Three fresh single-arm processes per order on the 18-page dev/id_ablation packet:
AB = native, carbon_bf16, carbon_surgical; BA = carbon_surgical, carbon_bf16, native. One complete 18-page
document per arm/order with six scored three-page windows (36 scored windows), identical excluded warm-up
requests across all arms and orders.

`orders` checks a coordinator A2 plan record and the run plans. `decide`, after the committed blind
inventory and the separate dev-key release, re-verifies the trees, reads durable clocks (timing.json
elapsed_s = document_committed_ns - accepted_ns, WP-0015 document boundary), requires stops/full pages,
6 windows, original flagged == false, then scores every arm in two views (frozen; public title<LEVELn>
rule applied by the WP-0016 title_adapt.py in its own OS process) with the frozen score.py in its own OS
process. Rule (design PROTOCOL.md A2, specification p.4):

  ADVANCE iff complete uniquely linked pairs in all four native->surgical views/orders, ZERO newly unflagged
  critical errors in each of the four, and for BOTH orders F_o = T_native - T_full > 0 and
  S_o = T_native - T_surgical >= 0.60 F_o, and min_o S_o > max(|T_native,AB - T_native,BA|,
  |T_surgical,AB - T_surgical,BA|) (strict; ties reject). Full-arm spread and changed persistent errors are
  reported separately. Missing evidence fails closed. design/rules.py:a2 is run on the same inputs as a
  cross-check; disagreement is a failure.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DEV_TRUTH_SHA256, HERE, Check, all_flags_false, blob_module, load, run_score,  # noqa: E402
                    sha, sha_file, transitions, utc, write_new)

ARMS = ("native", "carbon_bf16", "carbon_surgical")
ORDERS = {"ab": ("native", "carbon_bf16", "carbon_surgical"), "ba": ("carbon_surgical", "carbon_bf16", "native")}
RETENTION_MIN = 0.60  # specification p.4; not tunable
WINDOWS_PER_ARM = 6
TITLE_ADAPT = HERE.parent / "WP-0016" / "title_adapt.py"
TITLE_ADAPT_BLOB = ("1e75ebe25814227ef6450913bce301ba9e2ef0f2", "docs/reviews/WP-0016/title_adapt.py")


def check_orders(record, check):
    orders = record["orders"]
    names = {}
    for name, b in orders.items():
        seq = tuple(b["order"])
        hit = [k for k, v in ORDERS.items() if v == seq]
        check(len(hit) == 1, f"{name}: order {list(seq)} is neither AB nor BA")
        if hit:
            names[name] = hit[0]
    check(sorted(names.values()) == ["ab", "ba"], "exactly one AB and one BA order")
    return names


def split_segments(requests):
    segments = []
    for req in requests:
        if not segments or segments[-1][0] != req["mode"]:
            segments.append((req["mode"], [req]))
        else:
            segments[-1][1].append(req)
    return segments


def read_run(run, check):
    plan = load(run / "plan.json")
    arms, warm = {}, {}
    segs = split_segments(plan["requests"])
    for si, (mode, reqs) in enumerate(segs, 1):
        seg = run / f"segment-{si:02d}-{mode}"
        warm[mode] = [(r["label"], r["sha256"], tuple(r["rgb_sha256"])) for r in reqs if r.get("warmup")]
        for i, req in enumerate(reqs, 1):
            if req.get("warmup"):
                continue
            folder = seg / f"{i:02d}-{req['label']}-{req['mode']}"
            t = load(folder / "timing.json")
            pred = folder / "prediction.json"
            ok = check(t.get("status") == "completed" and t.get("complete_pages") == req["pages"] == 18
                       and t["prediction_sha256"] == sha_file(pred), f"{run.name}/{mode}: complete 18 pages, bound")
            check(abs(t["elapsed_s"] - (t["document_committed_ns"] - t["accepted_ns"]) / 1e9) < 1e-6,
                  f"{run.name}/{mode}: elapsed = committed - accepted")
            stops = [d.get("finish_reason") == "stop" and d.get("num_pages_out") == d.get("expected_pages")
                     for d in (load(w) for w in sorted(folder.glob("window-*.json")))]
            check(len(stops) == WINDOWS_PER_ARM and all(stops), f"{run.name}/{mode}: six windows, all stopped")
            check(all_flags_false(load(pred)), f"{run.name}/{mode}: original flagged == false everywhere")
            check(mode not in arms, f"{run.name}: one measured document per arm")
            arms[mode] = dict(folder=str(folder), prediction=str(pred), prediction_sha256=sha_file(pred),
                              complete_s=t["elapsed_s"], complete=ok, windows=len(stops),
                              source_sha256=req["sha256"], rgb=tuple(req["rgb_sha256"]))
    check(len(segs) == 3, f"{run.name}: three single-arm segments (fresh processes)")
    return arms, warm, tuple(m for m, _ in segs)


def stoploss(T, silent, complete):
    """Pure. T[(order, arm)] seconds; silent[(order, view)] new unflagged counts; complete bool."""
    res = {}
    for o in ("ab", "ba"):
        tn, tf, ts = T.get((o, "native")), T.get((o, "carbon_bf16")), T.get((o, "carbon_surgical"))
        if None in (tn, tf, ts):
            res[o] = dict(missing=True)
            continue
        F, S = tn - tf, tn - ts
        res[o] = dict(native_s=tn, full_s=tf, surgical_s=ts, full_saving_s=F, surgical_saving_s=S,
                      retention=S / F if F > 0 else None, full_positive=F > 0, retention_ok=F > 0 and S >= RETENTION_MIN * F)
    views = [("ab", "frozen"), ("ab", "title"), ("ba", "frozen"), ("ba", "title")]
    res["new_unflagged"] = {f"{o}/{v}": silent.get((o, v)) for o, v in views}
    ok = complete and all(silent.get(k) == 0 for k in views) and all(not res[o].get("missing") for o in ("ab", "ba"))
    if ok:
        sp = {a: abs(T[("ab", a)] - T[("ba", a)]) for a in ARMS}
        mn = min(res[o]["surgical_saving_s"] for o in ("ab", "ba"))
        res["spreads_s"] = dict(native=sp["native"], surgical=sp["carbon_surgical"], full_reported=sp["carbon_bf16"])
        res["min_surgical_saving_s"] = mn
        res["saving_exceeds_spreads"] = mn > max(sp["native"], sp["carbon_surgical"])
        ok = all(res[o]["full_positive"] and res[o]["retention_ok"] for o in ("ab", "ba")) and res["saving_exceeds_spreads"]
    res["advance"] = bool(ok)
    return res


def astra_a2(rules, T, silent, complete):
    times = {a: [T[("ab", a)], T[("ba", a)]] for a in ARMS}
    ns = [silent[("ab", "frozen")], silent[("ab", "title")], silent[("ba", "frozen")], silent[("ba", "title")]]
    return rules.a2(times, ns, complete)


def title_view(pins, folder, out_pred, out_receipt):
    src = subprocess.run(["git", "-C", str(HERE), "cat-file", "blob", ":".join(TITLE_ADAPT_BLOB)],
                         check=True, capture_output=True).stdout
    if sha(src) != sha_file(TITLE_ADAPT):
        raise SystemExit("WP-0016 title_adapt.py differs from its committed blob")
    subprocess.run([sys.executable, "-I", "-B", str(TITLE_ADAPT), "--pins", str(pins), "--doc", str(folder),
                    "--out", str(out_pred), "--receipt", str(out_receipt)], check=True, cwd=str(pins),
                   stdin=subprocess.DEVNULL)
    return out_pred


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
    d.add_argument("--pins", type=Path, required=True, help="materialized pins: score.py, formats.py, rescore.py")
    d.add_argument("--truth", type=Path, required=True, help="released dev key (passed only to score.py)")
    d.add_argument("--out", type=Path, required=True, help="new private directory")
    a = ap.parse_args()
    check = Check()
    check(sha_file(a.plans) == a.plans_sha256, "A2 plan record digest")
    record = load(a.plans)
    names = check_orders(record, check)
    if a.cmd == "orders":
        print(json.dumps(dict(orders=names, checks=check.count, failures=check.failures), indent=1))
        return 0 if not check.failures else 1
    from escrow import verify_unchanged  # noqa: PLC0415
    inv = load(a.inventory)
    check(not verify_unchanged(inv), "A2 run tree changed since the blind inventory")
    check(sha_file(a.truth) == DEV_TRUTH_SHA256, "dev key equals its custody commitment (dfdf62cb...)")
    a.out.mkdir(parents=True, exist_ok=False)
    for v in ("title", "scores", "compare"):
        (a.out / v).mkdir()
    by_sha = {b["sha256"]: n for n, b in record["orders"].items()}
    T, silent, comps, arms_all, warms, srcs = {}, {}, {}, {}, [], set()
    complete = True
    for ir in inv["runs"]:
        run = Path(ir["path"])
        name = by_sha.get(ir["plan_sha256"])
        if not check(name in names, f"{ir['run']}: plan not in the A2 record"):
            complete = False
            continue
        o = names[name]
        arms, warm, seq = read_run(run, check)
        check(seq == ORDERS[o], f"{o}: segment order {list(seq)} = {list(ORDERS[o])}")
        complete &= sorted(arms) == sorted(ARMS) and all(x["complete"] for x in arms.values())
        warms.extend(warm.values())
        srcs |= {(x["source_sha256"], x["rgb"]) for x in arms.values()}
        preds = {}
        for m, x in arms.items():
            T[(o, m)] = x["complete_s"]
            preds[(m, "frozen")] = Path(x["prediction"])
            preds[(m, "title")] = title_view(a.pins, Path(x["folder"]), a.out / "title" / f"{o}-{m}.prediction.json",
                                             a.out / "title" / f"{o}-{m}.receipt.json")
        scores = {k: run_score(a.pins, a.truth, p, a.out / "scores" / f"{o}-{k[0]}-{k[1]}.json") for k, p in preds.items()}
        for view in ("frozen", "title"):
            for trial in ("carbon_surgical", "carbon_bf16"):
                if ("native", view) not in preds or (trial, view) not in preds:
                    complete = False
                    continue
                cmp = run_score(a.pins, a.truth, preds[(trial, view)], a.out / "compare" / f"{o}-{view}-native__{trial}.json",
                                preds[("native", view)])["comparison"]
                tr, rows = transitions(scores[("native", view)], scores[(trial, view)])
                novel = {c["at"] for c in cmp["new_or_changed_critical_errors"]}
                mine = {r["at"] for r in rows if r["kind"] in ("regress", "abstain", "persist_changed")}
                check(novel == mine, f"{o}/{view} native->{trial}: transitions agree with frozen compare")
                key = f"{o}:{view}:native->{trial}"
                comps[key] = dict(critical={k: v for k, v in tr.items() if k != "new_unflagged_paths"},
                                  changed_persistent=tr["counts"]["persist_changed"],
                                  complete_matched_pair=cmp["complete_matched_pair"], matched_paths=tr["matched_paths"],
                                  delta=cmp["delta"], new_wrong_source_links=len(cmp["new_wrong_source_links"]))
                write_new(a.out / f"{o}-{view}-native__{trial}.details.json", dict(note="PRIVATE", rows=rows))
                if trial == "carbon_surgical":
                    silent[(o, view)] = tr["new_unflagged"]
                    complete &= bool(cmp["complete_matched_pair"] and tr["matched_paths"])
        arms_all[o] = {m: {k: v for k, v in x.items() if k != "rgb"} for m, x in arms.items()}
    check(len(srcs) == 1, "identical dev source/RGB across all six arm requests")
    check(len({tuple(w) for w in warms}) == 1, "identical excluded warm-up requests across arms and orders")
    rule = stoploss(T, silent, complete)
    try:
        astra = astra_a2(blob_module("design/rules.py", "astra_rules"), T, silent, complete)
        check(astra["advance"] == rule["advance"], "reviewer and Astra A2 arithmetic agree")
    except (KeyError, ValueError, TypeError) as exc:
        astra = dict(error=repr(exc))
        check(not rule["advance"], "Astra A2 arithmetic could not run; advance must then be false")
    advance = rule["advance"] and not check.failures
    summary = dict(kind="WP-0017 A2 reviewer stop-loss decision", reviewer="eld-rd-reviewer", created_utc=utc(),
                   plans_sha256=a.plans_sha256, inventory_sha256=sha_file(a.inventory), truth_sha256=DEV_TRUTH_SHA256,
                   orders=names, arms=arms_all, comparisons=comps, rule=rule, astra_rules_a2=astra,
                   checks_run=check.count, failures=check.failures, advance_to_A3=advance,
                   outcome="ADVANCE_TO_A3" if advance else "HALT_AT_A2")
    digest = write_new(a.out / "summary.json", summary)
    print(json.dumps(dict(summary=str(a.out / "summary.json"), sha256=digest, outcome=summary["outcome"],
                          failures=check.failures[:20]), indent=1))
    return 0 if advance else 1


if __name__ == "__main__":
    sys.exit(main())
