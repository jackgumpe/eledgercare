"""CPU self-test of the WP-0017 reviewer tools (eld-rd-reviewer), synchronized with design 1fad21c.

Stdlib only; no GPU, no truth. Synthetic A1 result sets are built from the REAL frozen WP-0016 token arrays
of windows 019 and 037 (A1 manifest e7f47d14..., audit 16eca676...), so field anchoring, prefixes, spans and
selection run on actual ids. Reviewer arithmetic is cross-checked against the pinned design/rules.py.
Also covers A2 orders/stop-loss (with the Astra cross-check), the A3 gate, scorecard simulation, the blind
inventory, the sealed-path guard and the reviewer command check against a synthetic release.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a1_decide as A1  # noqa: E402
import a2_stoploss as A2  # noqa: E402
import a3_gate as G3  # noqa: E402
import escrow  # noqa: E402
import scorecard  # noqa: E402
from common import Check, Vocab, blob_module, disk, guard_path, ids_sha, load, sha_file, utc, write_new  # noqa: E402

AUDIT = HERE / "evidence/A1-prefix-audit.json"
AUDIT_SHA = "16eca676114e847059503290b3c4a620eb1625769dd7f3a3e0a39ab252d263b3"


class Fx:
    def __init__(self):
        assert sha_file(AUDIT) == AUDIT_SHA
        self.audit = load(AUDIT)
        self.vocab = Vocab(disk("tokenizer.json"))
        self.man = A1.load_manifest()
        self.locs, self.spans, self.pref, self.bb = A1.anchors(self.audit, self.man, self.vocab)
        self.rules = blob_module("design/rules.py", "astra_rules")

    def probe(self, w, prefix, D):
        n, c = self.spans[w]["native"], self.spans[w]["carbon_bf16"]
        # put the whole contrast on the first token of each branch; remaining tokens near-certain
        lpn = [-1.0] + [-0.001] * (len(n) - 1)
        lpc = [-1.0 - D] + [-0.001] * (len(c) - 1)
        first, second = (n[0], c[0]) if D >= 0 else (c[0], n[0])
        top = [[first, 20.0], [second, 19.9], [11, 10.0], [12, 9.0], [13, 8.0]]
        return dict(prefix_sha256=ids_sha(prefix), prefix_tokens=len(prefix),
                    branches={"native": dict(ids=n, logprobs=lpn), "carbon_bf16": dict(ids=c, logprobs=lpc)},
                    first_divergence=0, top5=top, competing_logits={"native": top[0][1] if D >= 0 else 19.9,
                                                                   "carbon_bf16": 19.9 if D >= 0 else 20.0},
                    guard_status="finite", timing=dict(prefill_ms=400.0, decode_ms_per_token=60.0, decode_tokens=6,
                                                       interval="device-synchronized forced span"))

    def config(self, cid, bitvec, flips, D, D2=None, t=(40.0, 40.0), seqs=None):
        wins = {}
        for k, w in enumerate(A1.WINDOWS):
            arm = "carbon_bf16" if w in flips else "native"
            seq = (seqs or {}).get(w) or self.man[w][arm]
            nat_prefix = self.man[w]["native"][:self.pref[w]["tokens"]]
            passes = [self.probe(w, nat_prefix, D[w])] + ([self.probe(w, nat_prefix, D2[w])] if D2 else [])
            probes = {"native_prefix": passes}
            if w == "037":
                b = A1.free_boundary(self.vocab, seq, self.locs[w], self.bb[w])
                probes["free_prefix"] = [None if b is None else self.probe(w, seq[:b], -abs(D[w]) if arm != "native" else D[w])]
            wins[w] = dict(free=dict(token_ids=seq, seconds=t[k], output_tokens=len(seq), forwards=len(seq) + 1,
                                     counters={"forward_count": len(seq) + 1}, instrumented=False), probes=probes)
        on = {s for s, b in zip(A1.SWITCHES, bitvec) if b == "1"}
        label = "ordered stream callbacks deferred to burst return" if ("S3" in on and "S0" not in on) else None
        impl = {"native": "genuine_native", "carbon_bf16": "genuine_carbon"}.get(cid, "switch_harness")
        return dict(id=cid, bits=bitvec, implementation=impl, aliases=None, stream_cadence_label=label, windows=wins)

    def scenario(self, flipfn, base_D=0.40, shift=lambda s: 0.0, repeat=None, pairs=(), times=None, endpoint_noise=0.0):
        # Continuation revision: the coordinator's initial wave has 16 configurations (14 unique vectors plus the
        # all_off / all_on switch-harness endpoint controls); matrix() order is kept, controls come last.
        rows = []
        items = list(A1.initial_wave().items()) + [(A1.removal_id(p), A1.bits(set(A1.SWITCHES) - set(p))) for p in pairs]
        for cid, bv in items:
            on = {s for s, b in zip(A1.SWITCHES, bv) if b == "1"}
            flips = flipfn(on)
            D = {w: (-base_D if w in flips else base_D) + sum(shift(s) for s in on) for w in A1.WINDOWS}
            D2 = None
            if repeat is not None:
                D2 = repeat(cid, D)
            rows.append(self.config(cid, bv, flips, D, D2, (times or {}).get(cid, (40.0, 40.0))))
        return dict(configurations=rows, source_files={}, infrastructure_errors=[])

    def run(self, norm):
        c = Check()
        by, locs, bb = A1.bind(norm, self.audit, self.man, self.vocab, c)
        return c, A1.decide(by, self.audit, self.man, self.vocab, locs, bb, rules=self.rules)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True, help="new scratch directory")
    ap.add_argument("--receipt", type=Path, help="new JSON receipt")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    T, names = Check(), []

    def expect(ok, what):
        names.append(what)
        T(ok, what)

    fx = Fx()
    v = fx.vocab
    # Anchors on the frozen histories.
    expect(fx.locs["019"]["frozen_value"] == "I08O1-388" and fx.locs["037"]["frozen_value"] == "8OI10-774",
           "frozen locators read the native IDs structurally")
    expect([A1.field(v, fx.man[w]["carbon_bf16"], fx.locs[w])[:2] for w in A1.WINDOWS]
           == [("ok", "108O1-388"), ("ok", "80I10-774")], "carbon histories read at the same structural site")
    expect([A1.free_boundary(v, fx.man[w][m], fx.locs[w], fx.bb[w]) for w in A1.WINDOWS for m in ("native", "carbon_bf16")]
           == [417, 417, 41, 41], "free boundaries 417/41 from structure, not global index")
    # 1. Single culprit S1b.
    c, d = fx.run(fx.scenario(lambda on: set(A1.WINDOWS) if "S1b" in on else set()))
    expect(not c.failures, f"single: binding clean {c.failures[:2]}")
    expect(d["outcome"] == "SINGLE_REMOVAL_RESTORES_BOTH" and d["selected_removal"] == ["S1b"]
           and d["causal_label"]["unique_cause_pattern"] is True, "single culprit S1b, unique-cause pattern")
    expect(d["astra_rules_cross_check"]["single_rank"]["agree"], "single rank agrees with Astra")
    expect(d["history_shift_effect_037"]["carbon_bf16"] is not None and d["configurations"]["carbon_bf16"]["fields"]["037"]
           ["upstream_history_changed"] is True and d["configurations"]["native"]["fields"]["019"]["upstream_history_changed"] is False,
           "037 history shift and 019 upstream-history flags")
    # 2. Two restorers ranked by ordinary time; not unique.
    times = {"remove_S1b": (45.0, 45.0), "remove_S3": (41.0, 41.0)}
    c, d = fx.run(fx.scenario(lambda on: set(A1.WINDOWS) if {"S1b", "S3"} <= on else set(), times=times))
    expect(d["selected_removal"] == ["S3"] and d["causal_label"]["unique_cause_pattern"] is False
           and d["astra_rules_cross_check"]["single_rank"]["agree"], "fastest of two restorers; not unique; Astra agrees")
    expect(d["sufficiency_add_on_native"]["S3"] == [] and d["necessity_remove_from_full"]["S3"] == ["019", "037"],
           "sufficiency distinguished from necessity")
    # 3. Endpoint parity failure blocks attribution.
    norm = fx.scenario(lambda on: set(A1.WINDOWS) if "S1b" in on else set())
    norm["configurations"][0]["windows"]["019"]["free"]["token_ids"] = fx.man["019"]["native"][:-1] + [5]
    c, d = fx.run(norm)
    expect(d["outcome"] == "ENDPOINT_PARITY_FAILED" and "selected_removal" not in d, "endpoint parity failure withholds")
    # 4. Either S1a or S2 suffices: re-probe needed, then pairs, then pair restoration.
    either = lambda on: set(A1.WINDOWS) if ({"S1a", "S2"} & on) else set()
    sh = lambda s: {"S1c": 0.3, "S0": 0.000001}.get(s, 0.0)
    c, d = fx.run(fx.scenario(either, shift=sh))
    expect(d["outcome"] == "PAIR_SCREENING_REPROBE_REQUIRED" and d["anchored_flip_switches"] == ["S1a", "S2"]
           and d["reprobe"]["additions"] == ["S1c"], "re-probe only the additions that could qualify")

    def rep(cid, D):  # endpoints repeat with 0.001 noise; S1c repeats same sign; S3 shifts once only
        if cid in A1.ENDPOINTS or cid.startswith("add_"):
            return {w: D[w] + 0.001 for w in A1.WINDOWS}
        return None
    c, d = fx.run(fx.scenario(either, shift=sh, repeat=rep))
    expect(d["outcome"] == "PAIR_RUNS_REQUIRED" and d["qualifying_switches"] == ["S1a", "S1c", "S2"]
           and d["pair_runs"] == ["remove_S1a+S1c", "remove_S1a+S2", "remove_S1c+S2"], "eligible pairs over qualifiers")
    expect(d["astra_rules_cross_check"]["pairs"]["agree"], f"pair eligibility agrees with Astra {d['astra_rules_cross_check']}")
    pairs = [("S1a", "S1c"), ("S1a", "S2"), ("S1c", "S2")]
    c, d = fx.run(fx.scenario(either, shift=sh, repeat=rep, pairs=pairs))
    expect(not c.failures and d["outcome"] == "PAIR_REMOVAL_RESTORES_BOTH" and d["selected_removal"] == ["S1a", "S2"],
           "pair removal S1a+S2 restores")
    # 5. Opposite-sign repeat does not qualify.
    def rep_flip(cid, D):
        if cid == "add_S1c":
            return {w: -D[w] for w in A1.WINDOWS}
        return {w: D[w] + 0.001 for w in A1.WINDOWS}
    c, d = fx.run(fx.scenario(either, shift=sh, repeat=rep_flip))
    expect("S1c" not in d["qualifying_switches"] and d["astra_rules_cross_check"]["pairs"]["agree"],
           "opposite-sign repeat excluded; Astra agrees")
    # 6. A missing field is counted separately, never as a flip.
    norm = fx.scenario(either, shift=sh)
    seq = list(fx.man["019"]["native"])
    seq[416] = 1124  # 'spection' -> 'In': the frozen block no longer carries the label
    row = next(r for r in norm["configurations"] if r["id"] == "add_S0")
    row["windows"]["019"]["free"]["token_ids"] = seq
    c, d = fx.run(norm)
    expect(d["configurations"]["add_S0"]["field_failures"] == {"019": "moved"}
           and "S0" not in d["anchored_flip_switches"] and "S0" in d["missing_or_malformed_fields"] if "missing_or_malformed_fields" in d else False,
           "moved field counted separately, not as a flip")
    # 7. Binding failures.
    base = fx.scenario(lambda on: set(A1.WINDOWS) if "S1b" in on else set())
    for what, mut in (
            ("native-prefix probe uses the frozen native prefix",
             lambda n: n["configurations"][2]["windows"]["019"]["probes"]["native_prefix"][0].__setitem__("prefix_sha256", "0" * 64)),
            ("S3 with S0 off must label", lambda n: next(r for r in n["configurations"] if r["id"] == "add_S3").__setitem__("stream_cadence_label", None)),
            ("bit vector differs", lambda n: n["configurations"][3].__setitem__("bits", "111111")),
            ("uninstrumented", lambda n: n["configurations"][4]["windows"]["037"]["free"].__setitem__("instrumented", True)),
            ("competing first-divergence logits", lambda n: n["configurations"][5]["windows"]["037"]["probes"]["native_prefix"][0].pop("competing_logits")),
            ("own aligned prefix", lambda n: n["configurations"][6]["windows"]["037"]["probes"]["free_prefix"][0].__setitem__("prefix_tokens", 40))):
        n = copy.deepcopy(base)
        mut(n)
        c, _ = fx.run(n)
        expect(any(what in f for f in c.failures), f"binding detects: {what}")
    n = copy.deepcopy(base)
    n["configurations"] = n["configurations"][:-1]
    c, d = fx.run(n)
    expect(d["outcome"] == "INCOMPLETE_MATRIX", "incomplete matrix")
    # A2.
    chk = Check()
    names_ = A2.check_orders(dict(orders={"x": dict(order=list(A2.ORDERS["ab"])), "y": dict(order=list(A2.ORDERS["ba"]))}), chk)
    expect(not chk.failures and names_ == {"x": "ab", "y": "ba"}, "A2 exact AB/BA orders accepted")
    chk = Check()
    A2.check_orders(dict(orders={"x": dict(order=["carbon_bf16", "native", "carbon_surgical"]),
                                 "y": dict(order=["carbon_surgical", "native", "carbon_bf16"])}), chk)
    expect(len(chk.failures) >= 2, "A2 other reversed orders rejected")
    Tg = {("ab", "native"): 300.0, ("ab", "carbon_bf16"): 250.0, ("ab", "carbon_surgical"): 265.0,
          ("ba", "native"): 305.0, ("ba", "carbon_bf16"): 252.0, ("ba", "carbon_surgical"): 268.0}
    zero = {(o, vw): 0 for o in ("ab", "ba") for vw in ("frozen", "title")}
    cases = [("pass", Tg, zero, True, True),
             ("retention < 0.60", {**Tg, ("ba", "carbon_surgical"): 290.0}, zero, True, False),
             ("inside native spread", {**Tg, ("ba", "native"): 340.0, ("ba", "carbon_bf16"): 280.0,
                                       ("ba", "carbon_surgical"): 300.0}, zero, True, False),
             ("one new silent in BA/title", Tg, {**zero, ("ba", "title"): 1}, True, False),
             ("non-positive full saving", {**Tg, ("ab", "carbon_bf16"): 301.0}, zero, True, False),
             ("incomplete", Tg, zero, False, False),
             ("strict spread tie rejects", {("ab", "native"): 300.0, ("ab", "carbon_bf16"): 280.0, ("ab", "carbon_surgical"): 290.0,
                                            ("ba", "native"): 310.0, ("ba", "carbon_bf16"): 290.0, ("ba", "carbon_surgical"): 300.0},
              zero, True, False)]
    for what, t, s, comp, want in cases:
        r = A2.stoploss(t, s, comp)
        ast = A2.astra_a2(fx.rules, t, s, comp)
        expect(r["advance"] is want and ast["advance"] is want, f"A2 {what}: reviewer and Astra = {want}")
    # A3 gate.
    s1 = dict(runs={f"a3-{o}": dict(order=o, arms={"carbon_surgical": dict(summary=dict(
        counters=dict(static_cache_reallocations=0), counters_present=dict(static_cache_reallocations=True)))}) for o in ("ab", "ba")},
        timing=dict(A=dict(pairs=dict(ab=dict(saving_s=90.0), ba=dict(saving_s=120.0)),
                           repeat_spread_s=dict(native=60.0, carbon_surgical=10.0))))
    s2 = dict(verdict=dict(g0_pass=True))
    dev = dict(ab=[2000, 9600], ba=[2100, 9700])
    expect(G3.gate(s1, s2, dev)["a3_pass"], "A3 pass")
    expect(not G3.gate(s1, s2, dict(dev, ba=[10001]))["a3_pass"], "A3 board peak > 10,000 MiB fails")
    s1b = copy.deepcopy(s1)
    s1b["runs"]["a3-ba"]["arms"]["carbon_surgical"]["summary"]["counters"]["static_cache_reallocations"] = 1
    expect(not G3.gate(s1b, s2, dev)["a3_pass"], "A3 static growth fails with S2 on")
    s1d = copy.deepcopy(s1)
    for r in s1d["runs"].values():
        r["arms"]["carbon_surgical"]["summary"] = dict(counters={}, counters_present={})
    g = G3.gate(s1d, s2, dev, s2_enabled=False)
    expect(g["a3_pass"] and g["static_cache_mode"].startswith("dynamic-only"), "A3 dynamic-only labelled when S2 off")
    expect(not G3.gate(s1d, s2, dev, s2_enabled=True)["a3_pass"], "A3 missing static counter fails when S2 on")
    s1c = copy.deepcopy(s1)
    s1c["timing"]["A"]["repeat_spread_s"]["native"] = 95.0
    expect(not G3.gate(s1c, s2, dev)["a3_pass"], "A3 saving inside spread fails")
    # Scorecard.
    s = scorecard.simulate([dict(at="p/1", correct=True), dict(at="p/2", correct=False), dict(at="p/3", correct=False),
                            dict(at="p/4", correct=True)], {"p/1": 0.1, "p/2": 0.124, "p/3": 0.125}, 0.125)
    expect((s["false_alarms"], s["caught"], s["missed"], s["missing_margin"]) == (1, 1, 1, 1), "strict < 0.125 simulation")
    # Inventory and guard.
    run = a.out / "runs" / "r1"
    (run / "seg/cache").mkdir(parents=True)
    (run / "plan.json").write_text("{}")
    (run / "seg/prediction.json").write_text('{"pages": []}')
    (run / "seg/cache/k.bin").write_bytes(b"x")
    inv = escrow.build("A1", [run], [])
    expect(not escrow.verify_unchanged(inv) and list(inv["runs"][0]["runtime_cache_files"]) == ["seg/cache/k.bin"],
           "inventory clean; cache separate")
    (run / "seg/prediction.json").write_text('{"pages": [1]}')
    expect(escrow.verify_unchanged(inv) == ["r1"], "inventory detects change")
    for p in ("x/truth.json", "y/details.json", "C:/z/inputs/B/source.pdf"):
        try:
            guard_path(p)
            expect(False, f"guard refuses {p}")
        except SystemExit:
            expect(True, f"guard refuses {p}")
    result = dict(kind="WP-0017 reviewer CPU self-test (synchronized with design 1fad21c)", created_utc=utc(),
                  interpreter=sys.version, tests=len(names), failures=T.failures, passed=len(names) - len(T.failures),
                  tool_sha256={p.name: sha_file(p) for p in sorted(HERE.glob("*.py"))}, audit_sha256=AUDIT_SHA)
    if a.receipt:
        write_new(a.receipt, result)
    print(json.dumps(result, indent=1))
    return 0 if not T.failures else 1


if __name__ == "__main__":
    sys.exit(main())
