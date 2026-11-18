"""CPU self-test of the WP-0017 reviewer tools (eld-rd-reviewer). Stdlib only; no GPU, no truth.

Synthetic A1 result sets are built from the REAL WP-0016 token sequences of windows 019 and 037 (bound by the
frozen audit), so the decision procedure is exercised on actual ids, page splits and spans. Also covers the
A2 order check and stop-loss rule, the A3 gate combinator, the scorecard simulation, the blind inventory,
the sealed-path guard and the detached operator/monitor with a dummy lease executor.
"""
import argparse
import copy
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a1_decide as A1  # noqa: E402
import a2_stoploss as A2  # noqa: E402
import a3_gate as G3  # noqa: E402
import escrow  # noqa: E402
import scorecard  # noqa: E402
from common import (WP16_RUNS, Check, Vocab, blob, disk, guard_path, ids_sha, load, sha, sha_file, utc,  # noqa: E402
                    write_new)

AUDIT = HERE / "evidence/A1-prefix-audit.json"
AUDIT_SHA = "16eca676114e847059503290b3c4a620eb1625769dd7f3a3e0a39ab252d263b3"
FOLDER = {"native": "g0-ab/segment-01-native/05-a-native", "carbon_bf16": "g0-ab/segment-02-carbon_bf16/05-a-carbon_bf16"}


def real_ids(audit):
    inv = json.loads(blob("G0-blind-inventory.json"))
    files = {f"{r['run']}/{k}": v for r in inv["runs"] for k, v in r["files"].items()}
    out = {}
    for arm, folder in FOLDER.items():
        for w in A1.WINDOWS:
            rel = f"{folder}/{w}.json"
            b = (WP16_RUNS / rel).read_bytes()
            assert sha(b) == files[rel], rel
            ids = [int(t) for t in json.loads(b)["window_token_ids"]]
            assert ids_sha(ids) == audit["windows"][w]["a1_prefixes"]["full_window"][arm]["sha256"]
            out[arm, w] = ids
    return out


def probe(audit, w, prefix, favor, step=0.0):
    sp = audit["windows"][w]["divergence"]["span_to_identifier_end"]
    n, c = [t["id"] for t in sp["native"]], [t["id"] for t in sp["carbon_bf16"]]
    first, second = (n[0], c[0]) if favor == "native" else (c[0], n[0])
    top = [[first, 20.0 + step], [second, 19.5], [11, 10.0], [12, 9.0], [13, 8.0]]
    lp = {"native": -0.5 - step, "carbon_bf16": -0.9} if favor == "native" else {"native": -0.9, "carbon_bf16": -0.5 - step}
    return dict(prefix_sha256=ids_sha(prefix), prefix_tokens=len(prefix), t_star_top5=top,
                margin=top[0][1] - top[1][1], logprob=lp, span_ids={"native": n, "carbon_bf16": c})


def config(audit, vocab, ids, cid, switches, flips, step=0.0, t=(40.0, 40.0)):
    """flips: set of windows where this configuration emits the carbon_bf16 sequence."""
    wins = {}
    for k, w in enumerate(A1.WINDOWS):
        arm = "carbon_bf16" if w in flips else "native"
        seq = ids[arm, w]
        free = dict(token_ids=seq, time_s=t[k], prefill_ms=400.0, decode_ms_per_token=100.0, instrumented=False)
        a = audit["windows"][w]["a1_prefixes"]
        if w == "window-019":
            common = ids["native", w][:a["common_window_prefix"]["tokens"]]
            probes = {"common": probe(audit, w, common, arm, step)}
        else:
            forced = ids["native", w][:a["native_prefix_to_boundary"]["tokens"]]
            b = A1.boundary(vocab, seq, w, audit)
            probes = {"forced_native": probe(audit, w, forced, "native", step),
                      "free": probe(audit, w, seq[:b], arm, step)}
        wins[w] = dict(free=free, probes=probes)
    return dict(id=cid, switches=switches, windows=wins)


def scenario(audit, vocab, ids, culprit_fn, extra_pairs=(), shift=lambda s: 0.0, times=None):
    m = A1.matrix()
    res = []
    for cid, vec in m.items():
        on = {s for s, v in vec.items() if v}
        flips = culprit_fn(on)
        step = sum(shift(s) for s in on)
        res.append(config(audit, vocab, ids, cid, vec, flips, step, (times or {}).get(cid, (40.0, 40.0))))
    for pair in extra_pairs:
        vec = A1.pair_vector(pair)
        on = {s for s, v in vec.items() if v}
        res.append(config(audit, vocab, ids, A1.pair_id(pair), vec, culprit_fn(on), sum(shift(s) for s in on)))
    return res


def run_a1(audit, vocab, results):
    check = Check()
    by = A1.bind(results, audit, vocab, check)
    return check, A1.decide(by, audit, vocab)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True, help="new scratch directory")
    ap.add_argument("--receipt", type=Path, help="new JSON receipt")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    T = Check()
    names = []

    def expect(ok, what):
        names.append(what)
        T(ok, what)

    assert sha_file(AUDIT) == AUDIT_SHA
    audit = load(AUDIT)
    vocab = Vocab(disk("tokenizer.json"))
    ids = real_ids(audit)
    # Boundary helper reproduces the audited 037 boundary on both real sequences.
    expect(A1.boundary(vocab, ids["native", "window-037"], "window-037", audit) == 41
           and A1.boundary(vocab, ids["carbon_bf16", "window-037"], "window-037", audit) == 41, "037 boundary = 41")
    expect(A1.boundary(vocab, ids["native", "window-019"], "window-019", audit) == 417
           and A1.boundary(vocab, ids["carbon_bf16", "window-019"], "window-019", audit) == 417, "019 boundary = 417")
    expect(A1.reading(vocab, ids["native", "window-019"], "window-019") == "native"
           and A1.reading(vocab, ids["carbon_bf16", "window-037"], "window-037") == "carbon_bf16", "readings")
    # 1. Single culprit S1b: any configuration with S1b on emits both carbon windows.
    single = lambda on: set(A1.WINDOWS) if "S1b" in on else set()
    c, d = run_a1(audit, vocab, scenario(audit, vocab, ids, single, shift=lambda s: 0.25 if s == "S1b" else 0.0))
    expect(not c.failures, f"single: binding clean {c.failures[:3]}")
    expect(d["replay"]["ok"] and d["outcome"] == "SINGLE_CULPRIT" and d["single_removal_restorers"] == ["S1b"],
           "single culprit S1b")
    expect(d["window_037_cascade"]["carbon_bf16"] == "upstream_prefix_cascade", "037 cascade classified (forced favors native)")
    # 2. Replay failure: all-off does not reproduce native.
    res = scenario(audit, vocab, ids, single)
    nat = next(r for r in res if r["id"] == "native")
    nat["windows"]["window-019"]["free"]["token_ids"] = nat["windows"]["window-019"]["free"]["token_ids"][:-1] + [5]
    c, d = run_a1(audit, vocab, res)
    expect(d["outcome"] == "REPLAY_FAILED" and "single_removal_restorers" not in d, "replay failure withholds attribution")
    # 3. Either of S1a or S2 suffices: no single removal restores; pairs requested, then resolved.
    either = lambda on: set(A1.WINDOWS) if ({"S1a", "S2"} & on) else set()
    sh = lambda s: {"S1a": 0.3, "S2": 0.2, "S1c": 0.1}.get(s, 0.0)
    c, d = run_a1(audit, vocab, scenario(audit, vocab, ids, either, shift=sh))
    expect(d["outcome"] == "PAIR_REMOVALS_REQUIRED" and d["qualifying_shift_switches"] == ["S1a", "S1c", "S2"]
           and d["requested_pair_removals"] == ["drop:S1a+S1c", "drop:S1a+S2", "drop:S1c+S2"], "pairs requested over Q")
    pairs = [("S1a", "S1c"), ("S1a", "S2"), ("S1c", "S2")]
    c, d = run_a1(audit, vocab, scenario(audit, vocab, ids, either, pairs, shift=sh))
    expect(not c.failures and d["outcome"] == "PAIR_CULPRIT" and d["pair_removal_restorers"] == ["drop:S1a+S2"],
           "pair culprit S1a+S2")
    # 4. Interaction only: flips need >= 3 of {S1a,S1b,S1c,S2}; no single or pair removal (of Q) restores.
    inter = lambda on: set(A1.WINDOWS) if len({"S1a", "S1b", "S1c", "S2"} & on) >= 3 else set()
    c, d = run_a1(audit, vocab, scenario(audit, vocab, ids, inter))
    expect(d["outcome"] == "INTERACTION_ONLY" and d["qualifying_shift_switches"] == [], "interaction-only outcome")
    # 5. Site split: S1b flips 019 only, S2 flips 037 only -> no single restorer.
    split = lambda on: ({"window-019"} if "S1b" in on else set()) | ({"window-037"} if "S2" in on else set())
    c, d = run_a1(audit, vocab, scenario(audit, vocab, ids, split, shift=lambda s: 0.1 if s in ("S1b", "S2") else 0.0))
    expect(d["single_removal_restorers"] == [] and d["single_removal_restorers_per_site"]["window-019"] == ["S1b"]
           and d["single_removal_restorers_per_site"]["window-037"] == ["S2"] and d["outcome"] == "PAIR_REMOVALS_REQUIRED",
           "site split recorded")
    # 6. Multiple single restorers ranked by local time cost.
    both = lambda on: set(A1.WINDOWS) if {"S1b", "S3"} <= on else set()
    times = {"drop:S1b": (45.0, 45.0), "drop:S3": (41.0, 41.0)}
    c, d = run_a1(audit, vocab, scenario(audit, vocab, ids, both, times=times))
    expect(d["outcome"] == "MULTIPLE_SINGLE_REMOVALS" and
           [x["config"] for x in d["candidates_by_local_time_cost"]] == ["drop:S3", "drop:S1b"], "candidates ranked")
    # 7. Binding failures.
    res = scenario(audit, vocab, ids, single)
    bad = copy.deepcopy(res)
    bad[0]["windows"]["window-019"]["probes"]["common"]["prefix_sha256"] = "0" * 64
    c, _ = run_a1(audit, vocab, bad)
    expect(any("417-token prefix" in f for f in c.failures), "wrong prefix digest detected")
    bad = copy.deepcopy(res)
    bad[3]["switches"]["S0"] = not bad[3]["switches"]["S0"]
    c, _ = run_a1(audit, vocab, bad)
    expect(any("switch vector" in f for f in c.failures), "wrong switch vector detected")
    bad = copy.deepcopy(res)[:-1]
    c, _ = run_a1(audit, vocab, bad)
    expect(any("missing configuration" in f for f in c.failures), "missing configuration detected")
    bad = copy.deepcopy(res)
    bad[2]["windows"]["window-037"]["free"]["instrumented"] = True
    c, _ = run_a1(audit, vocab, bad)
    expect(any("uninstrumented" in f for f in c.failures), "instrumented free timing detected")
    # A2 order check and stop-loss rule.
    chk = Check()
    o = A2.check_orders(dict(orders={"o1": dict(order=["native", "carbon_bf16", "carbon_surgical"]),
                                     "o2": dict(order=["carbon_surgical", "carbon_bf16", "native"])}), chk)
    expect(not chk.failures and o["position_balanced"] == {"native": True, "carbon_bf16": False, "carbon_surgical": True},
           "A2 reversed orders accepted; middle arm reported")
    chk = Check()
    A2.check_orders(dict(orders={"o1": dict(order=["native", "carbon_bf16", "carbon_surgical"]),
                                 "o2": dict(order=["carbon_bf16", "native", "carbon_surgical"])}), chk)
    expect(any("reverse" in f for f in chk.failures), "A2 non-reversed orders rejected")
    good_t = {("o1", "native"): 300.0, ("o1", "carbon_bf16"): 250.0, ("o1", "carbon_surgical"): 265.0,
              ("o2", "native"): 305.0, ("o2", "carbon_bf16"): 252.0, ("o2", "carbon_surgical"): 268.0}
    safe = {o: dict(new_unflagged=0, matched=True, complete=True) for o in ("o1", "o2")}
    r = A2.stoploss(good_t, safe)
    expect(r["advance"] and abs(r["o1"]["retention"] - 0.7) < 1e-12, "A2 pass case")
    t2 = {**good_t, ("o2", "carbon_surgical"): 290.0}
    expect(not A2.stoploss(t2, safe)["advance"], "A2 retention below 0.60 halts")
    t3 = {**good_t, ("o2", "native"): 340.0, ("o2", "carbon_bf16"): 280.0, ("o2", "carbon_surgical"): 300.0}
    expect(not A2.stoploss(t3, safe)["advance"], "A2 saving inside the native spread halts")
    expect(not A2.stoploss(good_t, dict(safe, o2=dict(new_unflagged=1, matched=True, complete=True)))["advance"],
           "A2 one new unflagged critical halts")
    t4 = {**good_t, ("o1", "carbon_bf16"): 301.0}
    expect(not A2.stoploss(t4, safe)["advance"], "A2 non-positive carbon saving halts")
    expect(not A2.stoploss({k: v for k, v in good_t.items() if k != ("o2", "carbon_surgical")}, safe)["advance"],
           "A2 missing arm fails closed")
    # A3 gate combinator.
    s1 = dict(runs={"a3-ab": dict(order="ab", arms={"carbon_surgical": dict(summary=dict(
                  counters=dict(static_cache_reallocations=0), counters_present=dict(static_cache_reallocations=True)))}),
                    "a3-ba": dict(order="ba", arms={"carbon_surgical": dict(summary=dict(
                        counters=dict(static_cache_reallocations=0), counters_present=dict(static_cache_reallocations=True)))})},
              timing=dict(A=dict(pairs=dict(ab=dict(saving_s=90.0), ba=dict(saving_s=120.0)),
                                 repeat_spread_s=dict(native=60.0, carbon_surgical=10.0))))
    s2 = dict(verdict=dict(g0_pass=True))
    dev = dict(ab=[2000, 9600], ba=[2100, 9700])
    expect(G3.gate(s1, s2, dev)["a3_pass"], "A3 gate pass case")
    expect(not G3.gate(s1, s2, dict(dev, ba=[10001]))["a3_pass"], "A3 board peak above 10,000 MiB fails")
    s1b = copy.deepcopy(s1)
    s1b["runs"]["a3-ba"]["arms"]["carbon_surgical"]["summary"]["counters"]["static_cache_reallocations"] = 1
    expect(not G3.gate(s1b, s2, dev)["a3_pass"], "A3 static cache reallocation fails")
    s1c = copy.deepcopy(s1)
    s1c["timing"]["A"]["repeat_spread_s"]["native"] = 95.0
    expect(not G3.gate(s1c, s2, dev)["a3_pass"], "A3 saving inside spread fails")
    expect(not G3.gate(s1, dict(verdict=dict(g0_pass=False)), dev)["a3_pass"], "A3 stage-2 G0 failure fails")
    # Scorecard simulation.
    crit = [dict(at="p/1", correct=True), dict(at="p/2", correct=False), dict(at="p/3", correct=False),
            dict(at="p/4", correct=True)]
    s = scorecard.simulate(crit, {"p/1": 0.1, "p/2": 0.2, "p/3": 5.0}, 1.0)
    expect((s["false_alarms"], s["caught"], s["missed"], s["missing_margin"], s["coverage"]) == (1, 1, 1, 1, 0.75),
           "scorecard simulation counts")
    # Blind inventory immutability and guard.
    run = a.out / "runs" / "r1"
    (run / "seg/cache").mkdir(parents=True)
    (run / "plan.json").write_text("{}")
    (run / "seg/prediction.json").write_text('{"pages": []}')
    (run / "seg/cache/k.bin").write_bytes(b"x")
    inv = escrow.build("A1", [run], [])
    expect(not escrow.verify_unchanged(inv) and list(inv["runs"][0]["runtime_cache_files"]) == ["seg/cache/k.bin"],
           "inventory clean; cache listed separately")
    (run / "seg/prediction.json").write_text('{"pages": [1]}')
    expect(escrow.verify_unchanged(inv) == ["r1"], "inventory detects a changed file")
    for p in ("x/truth.json", "y/details.json", "C:/z/inputs/B/source.pdf"):
        try:
            guard_path(p)
            expect(False, f"guard refuses {p}")
        except SystemExit:
            expect(True, f"guard refuses {p}")
    # Detached operator and monitor with a dummy lease executor (no GPU, no model).
    op = a.out / "operator"
    leases = a.out / "leases"
    leases.mkdir()
    dummy = a.out / "dummy_lease.py"
    dummy.write_text("import sys,time,json,pathlib\n"
                     f"d=pathlib.Path(r'{leases}')\n"
                     "(d/'acquired.json').write_text(json.dumps({'argv':sys.argv[1:]}))\n"
                     "open(d/'x-device.jsonl','w').write(json.dumps({'utc':'t','used_mib':1})+'\\n')\n"
                     "time.sleep(3)\n(d/'returned.json').write_text('{}')\n")
    release = a.out / "release.json"
    release.write_text('{"name": "selftest"}')
    py = sys.executable
    cmd = [py, "-I", "-B", str(HERE / "operate.py")]
    bad = subprocess.run(cmd + ["launch", "--opdir", str(op), "--release", str(release), "--digest", "0" * 64,
                                "--lease-py", str(dummy), "--lease-py-sha256", sha_file(dummy), "--leases-dir", str(leases)],
                         capture_output=True, text=True)
    expect(bad.returncode != 0 and not op.exists(), "operator refuses a wrong release digest")
    ok = subprocess.run(cmd + ["launch", "--opdir", str(op), "--release", str(release), "--digest", sha_file(release),
                               "--lease-py", str(dummy), "--lease-py-sha256", sha_file(dummy), "--leases-dir", str(leases)],
                        capture_output=True, text=True)
    expect(ok.returncode == 0, f"operator launches detached ({ok.stderr.strip()[-200:]})")
    mon = subprocess.run(cmd + ["monitor", "--opdir", str(op), "--interval", "0.5", "--limit", "30"],
                         capture_output=True, text=True)
    expect(mon.returncode == 0, f"monitor starts detached ({mon.stderr.strip()[-200:]})")
    deadline = time.monotonic() + 30
    lines = []
    while time.monotonic() < deadline:
        f = op / "monitor.jsonl"
        lines = f.read_text(encoding="utf-8").splitlines() if f.is_file() else []
        if lines and "watch_end" in lines[-1]:
            break
        time.sleep(0.5)
    end = json.loads(lines[-1]) if lines else {}
    expect(end.get("watch_end") == "exited" and end.get("exit_code") == 0, "monitor observed the supervisor exit 0")
    st = subprocess.run(cmd + ["status", "--opdir", str(op)], capture_output=True, text=True)
    stj = json.loads(st.stdout) if st.returncode == 0 else {}
    expect("returned.json" in stj.get("receipts", {}) and json.loads((leases / "acquired.json").read_text())["argv"]
           == [str(release), sha_file(release)], "status prints receipts; executor got exactly <release> <digest>")
    result = dict(kind="WP-0017 reviewer CPU self-test", created_utc=utc(), interpreter=sys.version,
                  tests=len(names), failures=T.failures, passed=len(names) - len(T.failures),
                  tool_sha256={p.name: sha_file(p) for p in sorted(HERE.glob("*.py"))},
                  audit_sha256=AUDIT_SHA)
    if a.receipt:
        write_new(a.receipt, result)
    print(json.dumps(result, indent=1))
    return 0 if not T.failures else 1


if __name__ == "__main__":
    sys.exit(main())
