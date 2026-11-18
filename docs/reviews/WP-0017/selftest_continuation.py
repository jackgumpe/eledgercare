"""CPU self-test of the continuation revision (eld-rd-reviewer, common.OPERATOR). Stdlib only; no GPU, no truth.

Covers, before any WP-0017 output or frozen engine candidate exists:
  A. a1_decide: the coordinator's sixteen-configuration initial wave (14 unique bit vectors + all_off/all_on
     endpoint controls), parity on all four endpoints, implementation/alias labels, optional genuine probes,
     instrument-matched speed contrasts and harness overhead, the E_w noise rule on all_off/all_on repeats with
     a reported conservative sensitivity (cross-checked with the pinned design/rules.py), re-probe requests,
     agreement with the coordinator's eight-window endpoint check, and backend-coupling labelling;
  B. command.py: EOL-only variants versus content changes of pinned coordinator files, and the independent A1
     plan re-derivation compared with plans produced by the pinned prepare_a1.py blob in scratch;
  C. a1_normalize: combined endpoint/switch run directories built from the REAL frozen 019/037 arrays, raw
     reassembly, RGB/source pins, released-config composition, immutability, and a full pipeline into a1_decide;
  D. a2_views: synthetic WP-0016-layout A2 runs validated from raw captures with the pinned formats.py, then a
     SYNTHETIC key (never the dev key) scored in both views by the frozen score.py and WP-0016 title_adapt.py in
     their own processes, path/metric validation, stop-loss outcomes and tamper detection.
"""
import argparse
import copy
import importlib.util
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a1_decide as A1  # noqa: E402
import a1_normalize as N  # noqa: E402
import a2_views as V  # noqa: E402
import command as C  # noqa: E402
import escrow  # noqa: E402
from common import (A1_MANIFEST, DEV_PDF_SHA256, PAGE_ID, REPO, Check, blob, eol_status, ids_sha, load,  # noqa: E402
                    materialize, sha, sha_file, utc, write_new)
from selftest import Fx  # noqa: E402

PTS = [595.0, 842.0]


def jdump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


# ---- A1 run trees from the real frozen arrays --------------------------------------------------------------

def split_pages(ids):
    starts = [i for i, t in enumerate(ids) if t == PAGE_ID]
    return [ids[s:e] for s, e in zip(starts, starts[1:] + [len(ids)])]


SPANS = {"019": (0, [342, 3019, 49, 19, 15, 21895], [223, 6924, 49, 19, 15, 21895]),       # (lcp, native, carbon)
         "037": (1, [223, 26, 90169, 553, 15, 30591], [223, 1892, 43, 553, 15, 30591])}  # engine pre-space spans
SOURCE = N.BOUND_CANDIDATE[0]


def engine_probe(history, boundary, w, D, device=False, label="forced_native"):
    """A span-logit probe record in the bound engine schema (span_probe.py at eb16708)."""
    lcp, nat, car = SPANS[w]
    P = boundary - lcp

    def steps(ids, first):
        rows = []
        for k, t in enumerate(ids):
            lp = -0.01 if k < lcp else (first if k == lcp else -0.001)
            s = dict(target_token_id=t, target_logprob_fp32=lp, target_is_finite=True)
            rows.append(dict(window_step=P + k, span_offset=k, in_common_boundary_suffix=k >= lcp,
                             is_first_divergent_step=k == lcp, guarded=s, raw=dict(s)))
        return rows
    sn, sc = steps(nat, -1.0), steps(car, -1.0 - D)
    import math  # noqa: PLC0415
    ell = lambda rows: math.fsum(r["guarded"]["target_logprob_fp32"] for r in rows if r["in_common_boundary_suffix"])  # noqa: E731
    first, second = (nat[lcp], car[lcp]) if D >= 0 else (car[lcp], nat[lcp])
    top = [dict(rank=1, token_id=first, logit_fp32=20.0), dict(rank=2, token_id=second, logit_fp32=19.9)] + \
          [dict(rank=r, token_id=10 + r, logit_fp32=12.0 - r) for r in (3, 4, 5)]
    comp = [dict(token_id=nat[lcp], logit_fp32=20.0 if D >= 0 else 19.9), dict(token_id=car[lcp], logit_fp32=19.9 if D >= 0 else 20.0)]
    meta = dict(implementation="device") if device else {}
    branch = lambda role, ids, rows: dict(role=role, pre_space_token_ids=ids, common_boundary_token_ids=ids[lcp:],  # noqa: E731
                                          all_targets_finite_guarded=True, all_targets_finite_raw=True, steps=rows)
    return dict(prefix_mode=label, prefix_token_len=P, prefix_sha256=ids_sha(history[:P]), lcp_offset_from_pre_space=lcp,
                serial_single_token_decode_enforced=True, both_branches_finite_guarded=True, both_branches_finite_raw=True,
                divergence_step_summary=dict(guarded_top5=top, guarded_competing_candidates=comp, guard_meta=meta),
                D_native_minus_carbon_guarded_nats=ell(sn) - ell(sc),
                probe_timing=dict(device_synchronized=True, prefill_ms=400.0, decode_ms_per_forwarded_token=60.0,
                                  total_forwarded_decode_tokens=P + 10, denominator_note="synthetic"),
                branches=[branch("native_id", nat, sn), branch("carbon_id", car, sc)])


def a1_tree(root, fx, arrays, request, tag="t1", flips=None, source=SOURCE, device_s3=True):
    """arrays: {mode: {'019': ids, '037': ids}} -> endpoint and switch run dirs (engine schema) + run_order receipts."""
    runs = {}
    impl = {"native": "genuine_native", "carbon_bf16": "genuine_carbon_bf16"}
    for group, modes in N.INITIAL.items():
        run = root / f"a1-{tag}-{group}"
        jdump(run / "launch.json", dict(stage="A1", source=source, head=source, a1_manifest_sha256=A1_MANIFEST[1],
                                       planned_configs=list(modes), auto_pair_removals=False))
        for si, mode in enumerate(modes, 1):
            seg = run / f"segment-{si:02d}-{mode}"
            bits = A1.initial_wave()[mode]
            on = {s for s, b in zip(A1.SWITCHES, bits) if b == "1"}
            jdump(seg / "child.json", dict(mode=mode, pid=1000 + si, switch_bits=bits,
                                           implementation=impl.get(mode, "ablation_engine")))
            secs = []
            for w in A1.WINDOWS:
                first = int(w)
                ids = arrays[mode][w]
                ctr = dict(s3_burst_chunks=12 if "S3" in on else 0, s0_streamer_put_calls=0 if "S0" in on else 99)
                span = 40 * 10 ** 9 + si
                secs.append(span / 1e9)
                jdump(seg / "free" / f"window-{first:03d}.json",
                      dict(source_sha256=request["sha256"], first_page=first, pages=3, num_pages_out=3,
                           finish_reason="stop", eos_id=1, window_token_ids=ids, forward_count=len(ids) + 1,
                           switch_counter_delta=ctr, engine_begin_ns=10 ** 9, engine_end_ns=10 ** 9 + span))
                for k, page_ids in enumerate(split_pages(ids)):
                    page = first + k
                    jdump(seg / "free" / f"raw-{page:03d}.json",
                          dict(source_sha256=request["sha256"], page=page, rgb_sha256=request["rgb_sha256"][page - 1],
                               token_ids=page_ids, raw_output=fx.vocab.decode(page_ids)))
                D = (-0.4 if (flips or (lambda o: set()))(on) & {w} else 0.4)
                nb = fx.pref[w]["tokens"]
                reps = 1 if mode.startswith("remove_") else 2
                passes = [engine_probe(fx.man[w]["native"], nb, w, D + 0.001 * r, device="S3" in on and device_s3)
                          for r in range(reps)]
                fb = A1.free_boundary(fx.vocab, ids, fx.locs[w], fx.bb[w])
                free = engine_probe(ids, fb, w, D, device="S3" in on and device_s3, label="free_running") \
                    if w == "037" and fb is not None else None
                jdump(seg / "probe" / f"window-{first:03d}-probe.json",
                      dict(mode=mode, switch_bits=bits, first_page=first, forced_native_passes=passes,
                           free_running_probe=free))
            jdump(seg / "free" / "ordinary-timing.json", dict(mode=mode, switch_bits=bits, ordinary_window_seconds=secs))
        jdump(run / "process.json", dict(all_segments_completed=True, overall_reason=None))
        outer = root / f"a1-{tag}-{group}-order"
        jdump(outer / "process.json", dict(plan_sha256="0" * 64, all_segments_completed=True,
                                           segments=[dict(label=run.name, returncode=0)]))
        if group == "endpoints":
            jdump(outer / "endpoint-check.json", dict(passed=True, checks=[
                dict(mode=m, first_page=int(w), errors=[]) for m in A1.ENDPOINTS for w in A1.WINDOWS]))
        runs[group] = run
    return runs


def a1_inventory(runs):
    roots = []
    for run in runs.values():
        roots += [run, run.parent / (run.name + "-order")]
    return escrow.build("A1", roots, [])


# ---- A2 synthetic documents (WP-0016 segmented layout) ------------------------------------------------------

def box(v):
    return [round(v[j] * PTS[j % 2] / 999, 3) for j in range(4)]


def page_ids(i):
    return (f"IL0O{i % 10}-R17{200 + i}", f"1O0IL-R17{300 + i}", f"L0I1O-R17{400 + i}")


def raw_page(i, hid, r1, r2):
    head = "<BLOCK>title<LEVEL1>" if i == 1 else "<BLOCK>title"
    return (f"<PAGE>{head}[50, 40, 600, 70]<FORK>Inspection register\n"
            f"<BLOCK>text[50, 100, 600, 130]<FORK>Inspection ID: {hid}\n"
            "<BLOCK>table[50, 200, 900, 400]<FORK><table><tr><td>Asset ID</td><td>Location</td><td>Status</td></tr>"
            f"<tr><td>{r1}</td><td>North</td><td>Open</td></tr><tr><td>{r2}</td><td>South</td><td>Held</td></tr></table>\n")


def synthetic_truth(sha_src):
    pages = []
    for i in range(1, 19):
        hid, r1, r2 = page_ids(i)
        xs, ys = [50, 333, 616, 900], [200, 266, 333, 400]
        rows = [["Asset ID", "Location", "Status"], [r1, "North", "Open"], [r2, "South", "Held"]]
        cells = [[dict(text=rows[r][c], bbox=box([xs[c], ys[r], xs[c + 1], ys[r + 1]]), critical=bool(r and c == 0))
                  for c in range(3)] for r in range(3)]
        pages.append(dict(page=i, width=PTS[0], height=PTS[1],
                          text="Inspection register\nInspection ID: " + hid + "\n" + " ".join(x for r in rows for x in r),
                          lines=[dict(text="Inspection register", bbox=box([50, 40, 600, 70]), critical=None),
                                 dict(text="Inspection ID: " + hid, bbox=box([50, 100, 600, 130]), critical=hid)],
                          tables=[dict(bbox=box([50, 200, 900, 400]), rows=cells)]))
    return dict(family="id_ablation", source_sha256=sha_src, pages=pages)


def write_doc(folder, req, fmt, seconds, damage=None):
    n = req["pages"]
    pages, raws = [], []
    for i in range(1, n + 1):
        hid, r1, r2 = page_ids(i) if n > 1 else ("WARM0-R17000", "WARM1-R17001", "WARM2-R17002")
        if damage and i == damage:
            hid = hid.replace("I", "1", 1)
        raw = raw_page(i, hid, r1, r2)
        ids = [PAGE_ID] + [10 + i] * 7
        rec = dict(source_sha256=req["sha256"], page=i, rgb_sha256=req["rgb_sha256"][i - 1], token_ids=ids,
                   token_count=len(ids), raw_output=raw, points=PTS)
        jdump(folder / f"raw-{i:03d}.json", rec)
        page = dict(page=i, source_sha256=req["sha256"], state="complete", **fmt.native_page(raw, PTS))
        jdump(folder / f"page-{i:03d}.json", page)
        pages.append(page)
        raws.append(rec)
    for s in range(1, n + 1, 3):
        span = raws[s - 1:s + 2]
        ids = [x for r in span for x in r["token_ids"]]
        jdump(folder / f"window-{s:03d}.json", dict(source_sha256=req["sha256"], first_page=s, pages=len(span),
                                                   window_token_ids=ids, raw_output="".join(r["raw_output"] for r in span),
                                                   finish_reason="stop", num_pages_out=len(span), expected_pages=len(span)))
    pred = dict(source_sha256=req["sha256"], pages=pages)
    pb = json.dumps(pred).encode()
    (folder / "prediction.json").write_bytes(pb)
    acc = 10 ** 12
    pc = [acc + 10 ** 6 * (k + 1) for k in range(n)]
    doc = acc + int(seconds * 1e9)
    jdump(folder / "timing.json", dict(request=req, prediction_sha256=sha(pb), status="completed", complete_pages=n,
                                       accepted_ns=acc, first_page_committed_ns=pc[0], page_committed_ns=pc,
                                       document_committed_ns=doc, elapsed_s=(doc - acc) / 1e9, first_page_s=0.001))


def a2_tree(root, fmt, times, rgb, damage=None, warm_rgb="a" * 64):
    warm = [dict(label=f"w{k}", mode=None, warmup=True, pages=1, sha256="25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858",
                 rgb_sha256=[warm_rgb]) for k in (1, 2, 3)]
    runs = []
    for o, seq in V.A2.ORDERS.items():
        run = root / f"a2-{o}"
        reqs = []
        for mode in seq:
            reqs += [dict(r, mode=mode) for r in warm] + [dict(label="dev", mode=mode, warmup=False, pages=18,
                                                              sha256=DEV_PDF_SHA256, rgb_sha256=rgb)]
        jdump(run / "plan.json", dict(requests=reqs))
        for si, (mode, rs) in enumerate(V.A2.split_segments(reqs), 1):
            for i, req in enumerate(rs, 1):
                folder = run / f"segment-{si:02d}-{mode}" / f"{i:02d}-{req['label']}-{mode}"
                folder.mkdir(parents=True)
                write_doc(folder, req, fmt, 1.0 if req["warmup"] else times[(o, mode)],
                          damage=(damage or {}).get((o, mode)) if not req["warmup"] else None)
        runs.append(run)
    return runs


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
    single = lambda on: set(A1.WINDOWS) if "S1b" in on else set()  # noqa: E731
    either = lambda on: set(A1.WINDOWS) if ({"S1a", "S2"} & on) else set()  # noqa: E731
    sh = lambda s: {"S1c": 0.3, "S0": 0.000001}.get(s, 0.0)  # noqa: E731

    # ---- A. sixteen-configuration wave -------------------------------------------------------------------
    wave = A1.initial_wave()
    expect(len(wave) == 16 and len(set(wave.values())) == 14 and wave["all_off"] == wave["native"] == "000000"
           and wave["all_on"] == wave["carbon_bf16"] == "111111", "initial wave: 16 configurations, 14 unique bit vectors")
    c, d = fx.run(fx.scenario(single))
    expect(not c.failures and d["outcome"] == "SINGLE_REMOVAL_RESTORES_BOTH" and d["initial_wave"]["configurations"] == 16
           and d["initial_wave"]["unique_bit_vectors"] == 14 and len(d["endpoint_parity"]) == 8,
           f"16-wave single culprit decided with eight endpoint parities {c.failures[:2]}")
    for cid, w in (("all_off", "019"), ("all_on", "037")):
        n = fx.scenario(single)
        row = next(r for r in n["configurations"] if r["id"] == cid)
        row["windows"][w]["free"]["token_ids"] = row["windows"][w]["free"]["token_ids"][:-1]
        c, d = fx.run(n)
        expect(d["outcome"] == "ENDPOINT_PARITY_FAILED" and d["endpoint_parity"][f"{cid}:{w}"]["equal"] is False
               and "selected_removal" not in d, f"{cid} parity failure on {w} withholds attribution")
    n = fx.scenario(single)
    next(r for r in n["configurations"] if r["id"] == "native")["implementation"] = "switch_harness"
    c, _ = fx.run(n)
    expect(any("implementation/alias label" in f for f in c.failures), "genuine endpoint mislabelled as harness detected")
    n = fx.scenario(single)
    row = next(r for r in n["configurations"] if r["id"] == "all_off")
    row.update(implementation="genuine_native", aliases="native")
    c, d = fx.run(n)
    expect(not c.failures and d["endpoint_parity"]["all_off:019"]["aliases"] == "native", "recorded alias accepted")
    n = fx.scenario(single)
    for r in n["configurations"]:
        if r["id"] in A1.GENUINE:
            for w in A1.WINDOWS:
                r["windows"][w]["probes"] = {}
    c, d = fx.run(n)
    expect(not c.failures and d["path_effect_vs_genuine_native"] == "genuine native not probed"
           and d["outcome"] == "SINGLE_REMOVAL_RESTORES_BOTH", "genuine endpoint probes optional")
    times = {"all_off": (50.0, 50.0), "native": (40.0, 40.0), "add_S1b": (45.0, 45.0), "all_on": (30.0, 30.0),
             "carbon_bf16": (28.0, 28.0), "remove_S1b": (33.0, 34.0)}
    c, d = fx.run(fx.scenario(single, times=times))
    sp = d["ordinary_speed_s"]
    expect(sp["addition_saving"]["S1b"]["sum"] == 10.0 and sp["addition_saving_vs_genuine_native"]["S1b"]["sum"] == -10.0
           and sp["harness_overhead"]["all_off_minus_native"]["sum"] == 20.0 and sp["removal_cost"]["S1b"]["sum"] == 7.0
           and sp["removal_cost_vs_genuine_carbon"]["S1b"]["sum"] == 11.0, "instrument-matched speed contrasts")
    c, d = fx.run(fx.scenario(either, shift=sh))
    expect(d["outcome"] == "PAIR_SCREENING_REPROBE_REQUIRED" and d["reprobe"]["endpoint_repeat"] == ["all_off", "all_on"],
           "re-probe requests the instrument-matched endpoint repeats")

    def rep(cid, D):
        bump = 0.5 if cid == "native" else 0.001
        return {w: D[w] + bump for w in A1.WINDOWS} if cid in A1.ENDPOINTS or cid.startswith("add_") else None
    c, d = fx.run(fx.scenario(either, shift=sh, repeat=rep))
    sens = d.get("noise_floor_sensitivity", {})
    expect(d["qualifying_switches"] == ["S1a", "S1c", "S2"] and abs(d["noise_floor_E"]["019"] - 0.001) < 1e-9
           and isinstance(sens, dict) and sens["changes_qualification"] is True and sens["qualifying_switches"] == ["S1a", "S2"]
           and d["astra_rules_cross_check"]["pairs"]["agree"],
           "E_w from all_off/all_on repeats decides; conservative genuine-noise floor reported as sensitivity")
    good = dict(passed=True, checks=[dict(mode=m, first_page=int(w), errors=[]) for m in A1.ENDPOINTS for w in A1.WINDOWS])
    by = A1.bind(fx.scenario(single), fx.audit, fx.man, fx.vocab, Check())[0]
    d = A1.decide(by, fx.audit, fx.man, fx.vocab, fx.locs, fx.bb, coordinator_check=good)
    bad = copy.deepcopy(good)
    bad["checks"][3]["errors"] = ["token/EOS parity"]
    bad["passed"] = False
    d2 = A1.decide(by, fx.audit, fx.man, fx.vocab, fx.locs, fx.bb, coordinator_check=bad)
    expect(d["coordinator_endpoint_check"]["agrees"] and not d2["coordinator_endpoint_check"]["agrees"],
           "agreement with the coordinator's eight-window endpoint check is checked")
    n = fx.scenario(single)
    row = next(r for r in n["configurations"] if r["id"] == "all_off")
    pre = fx.man["019"]["native"][:fx.pref["019"]["tokens"]]
    row["windows"]["019"]["probes"]["native_prefix"] = [fx.probe("019", pre, 0.41)]
    c, d = fx.run(n)
    expect(d["selected_removal"] == ["S1b"] and d["causal_label"]["unique_cause_pattern"] is False
           and d["causal_label"]["backend_coupling"]["gap_exceeds_floor_1e_5_nats"] is True,
           "harness-vs-genuine probe gap > 1e-5 nats blocks the unique-cause label")

    # ---- B. command.py ------------------------------------------------------------------------------------
    rc = blob("coord/review_command.py")
    expect(eol_status(rc, "coord/review_command.py") == "identical"
           and eol_status(rc[:-1] + b"\r\n", "coord/review_command.py") == "eol_variant"
           and eol_status(rc.replace(b"execute once", b"execute twice"), "coord/review_command.py") == "different",
           "pinned coordinator file: identical / EOL-only variant / content change")
    gen = a.out / "prepare" / "docs" / "coordination" / "WP-0017"
    gen.mkdir(parents=True)
    (gen / "prepare_a1.py").write_bytes(blob("coord/prepare_a1.py"))
    (gen / "check_endpoints.py").write_bytes(blob("coord/check_endpoints.py"))
    packet = a.out / "packet"
    (packet / "coordination").mkdir(parents=True)
    shutil.copyfile(A1_MANIFEST[0], packet / "coordination/a1-inputs.json")
    spec = importlib.util.spec_from_file_location("pinned_prepare_a1", gen / "prepare_a1.py")
    prep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prep)
    prep.PACKET = packet
    prep.main(REPO, "t1")
    plans = {g: packet / "coordination/plans/t1" / f"a1-t1-{g}.json" for g, _, _ in C.A1_GROUPS}
    ok = []
    for group, configs, seconds in C.A1_GROUPS:
        cfg = json.loads(plans[group].read_bytes())
        exp = C.a1_expected(plans[group], cfg, group, configs, seconds, gen.resolve(), packet=packet,
                            anchor_pin=(packet / "coordination/a1-inputs.json", A1_MANIFEST[1]))[0]
        ok.append(cfg == exp)
        for what, mut in (("swapped configs", lambda x: x["commands"][0]["argv"].__setitem__(-1, "native")),
                          ("budget", lambda x: x["commands"][0]["argv"].__setitem__(17, "1")),
                          ("extra bound file", lambda x: x["bound_files"].__setitem__("C:/custody/truth.json", "0")),
                          ("dropped endpoint gate", lambda x: x["commands"].__delitem__(slice(1, None)))):
            if what == "dropped endpoint gate" and group != "endpoints":
                continue
            m = copy.deepcopy(cfg)
            mut(m)
            ok.append(m != exp)
    expect(all(ok), "A1 plan re-derivation equals pinned prepare_a1.py output; mutations differ")
    r1, r2 = C.a1_candidate_ready("eb16708886226436de85abe0e224391a88537a72"), C.a1_candidate_ready("f" * 40)
    expect(len(r1) == 1 and "device guards" in r1[0] and len(r2) == 1 and "no reviewed" in r2[0],
           "A1 issuance refuses an unbound candidate and eb16708's host-guarded S3 probes")

    # ---- C. a1_normalize ----------------------------------------------------------------------------------
    request = load(A1_MANIFEST[0])["request"]
    on_bits = lambda mode: {s for s, b in zip(A1.SWITCHES, A1.initial_wave()[mode]) if b == "1"}  # noqa: E731
    arrays = {m: {w: fx.man[w]["carbon_bf16" if "S1b" in on_bits(m) else "native"] for w in A1.WINDOWS}
              for m in A1.initial_wave()}
    runs = a1_tree(a.out / "a1runs", fx, arrays, request, flips=single)
    inv = a1_inventory(runs)
    chk = Check()
    norm = N.normalize(inv, runs, check=chk)
    expect(not chk.failures and norm["adapter_status"] == "BOUND" and len(norm["configurations"]) == 16
           and norm["coordinator_endpoint_check"]["passed"] and not norm["infrastructure_errors"]
           and all(r["windows"]["019"]["free"]["seconds"] > 40 for r in norm["configurations"]),
           f"combined endpoint+switch runs normalize in the bound engine schema {chk.failures[:3]}")
    expect(all(v is not None for v in norm["source_files"].values()) and
           any(k.endswith("endpoint-check.json") for k in norm["source_files"]) and
           any(k.endswith("window-037-probe.json") for k in norm["source_files"]), "every read file is cited by digest")
    rows = {r["id"]: r for r in norm["configurations"]}
    p37 = rows["all_off"]["windows"]["037"]["probes"]["native_prefix"][0]
    expect(p37["prefix_tokens"] == 41 and p37["prefix_sha256"] == fx.pref["037"]["sha256"]
           and p37["branches"]["native"]["ids"] == fx.spans["037"]["native"] and len(rows["all_off"]["windows"]["019"]
                                                                                   ["probes"]["native_prefix"]) == 2
           and len(rows["remove_S1b"]["windows"]["019"]["probes"]["native_prefix"]) == 1,
           "037 shared ' ' moved into the 41-token frozen prefix; two passes for endpoints, one for removals")
    expect(rows["add_S3"]["stream_cadence_label"] and rows["remove_S0"]["stream_cadence_label"]
           and rows["add_S0"]["stream_cadence_label"] is None and rows["all_off"]["implementation"] == "switch_harness"
           and rows["carbon_bf16"]["implementation"] == "genuine_carbon", "labels from the bound contract and counters")
    c, d = fx.run(norm)
    expect(not c.failures and d["outcome"] == "SINGLE_REMOVAL_RESTORES_BOTH" and d["selected_removal"] == ["S1b"]
           and d["astra_rules_cross_check"]["single_rank"]["agree"],
           f"engine-schema run trees -> normalizer -> a1_decide {c.failures[:2]}")

    def probe_edit(rr, mode, w, fn):
        seg = next(s for m, s in N.segments(rr["switches"] if mode.startswith(("add_", "remove_")) else rr["endpoints"]) if m == mode)
        f = seg / "probe" / f"window-{w}-probe.json"
        doc = load(f)
        fn(doc)
        jdump(f, doc)
    for what, kw, mut, key in (
            ("unbound source", dict(source="f" * 40), None, None),
            ("engine D", {}, lambda rr: probe_edit(rr, "add_S1a", "019", lambda d: d["forced_native_passes"][0].__setitem__(
                "D_native_minus_carbon_guarded_nats", d["forced_native_passes"][0]["D_native_minus_carbon_guarded_nats"] + 0.01)),
             "recomputed D"),
            ("prefix digest", {}, lambda rr: probe_edit(rr, "all_on", "037", lambda d: d["forced_native_passes"][1].__setitem__(
                "prefix_sha256", "0" * 64)), "prefix digest"),
            ("S3 host guards", dict(device_s3=False), None, "device guards"),
            ("auto pairs", {}, lambda rr: jdump(rr["switches"] / "launch.json", dict(load(rr["switches"] / "launch.json"),
                                                                                    auto_pair_removals=True)), "automatic pair")):
        rr = a1_tree(a.out / f"a1-{what.replace(' ', '-')}", fx, arrays, request, flips=single, **kw)
        if mut:
            mut(rr)
        ch = Check()
        nn = N.normalize(a1_inventory(rr), rr, check=ch)
        ok = nn["adapter_status"] == "UNBOUND" and nn["unbound"] if key is None else any(key in f for f in ch.failures)
        expect(bool(ok), f"normalizer refuses: {what}")
    for what, mut in (
            ("RGB", lambda r: jdump(r["endpoints"] / "segment-02-all_off/free/raw-020.json",
                                    dict(load(r["endpoints"] / "segment-02-all_off/free/raw-020.json"), rgb_sha256="0" * 64))),
            ("reassembly", lambda r: jdump(r["switches"] / "segment-03-add_S1b/free/raw-038.json",
                                           dict(load(r["switches"] / "segment-03-add_S1b/free/raw-038.json"), token_ids=[PAGE_ID, 5]))),
            ("composition", lambda r: shutil.copytree(r["endpoints"] / "segment-01-native", r["endpoints"] / "segment-05-add_S0"))):
        root = a.out / f"a1-{what}"
        rr = a1_tree(root, fx, arrays, request, flips=single)
        mut(rr)
        ch = Check()
        N.normalize(a1_inventory(rr), rr, check=ch)
        expect(bool(ch.failures), f"normalizer detects a {what} defect")
    rr = a1_tree(a.out / "a1-mutated", fx, arrays, request, flips=single)
    inv2 = a1_inventory(rr)
    jdump(rr["switches"] / "segment-01-add_S0/child.json", dict(mode="add_S0", pid=1))
    ch = Check()
    N.normalize(inv2, rr, check=ch)
    expect(any("unchanged since the blind inventory" in f for f in ch.failures), "normalizer refuses a changed tree")

    # ---- D. a2_views (synthetic key, never the dev key) ---------------------------------------------------
    pins = a.out / "pins"
    materialize(pins, ("score.py", "formats.py", "rescore.py"))
    fmt = V.load_formats(pins)
    rgb = V.dev_rgb(Check())
    Tg = {("ab", "native"): 300.0, ("ab", "carbon_bf16"): 250.0, ("ab", "carbon_surgical"): 265.0,
          ("ba", "native"): 305.0, ("ba", "carbon_bf16"): 252.0, ("ba", "carbon_surgical"): 268.0}
    a2runs = a2_tree(a.out / "a2", fmt, Tg, rgb)
    inv3 = escrow.build("A2", a2runs, [])
    chk = Check()
    pre_runs = V.prekey(inv3, pins, None, chk)
    expect(not chk.failures and sorted(pre_runs) == ["ab", "ba"] and all(len(r["arms"]) == 3 for r in pre_runs.values()),
           f"A2 pre-key validation from raw captures {chk.failures[:3]}")
    truth = a.out / "synthetic-key" / "key.json"
    jdump(truth, synthetic_truth(DEV_PDF_SHA256))
    pre = dict(runs=pre_runs, inventory_sha256="x", failures=[])
    chk = Check()
    res = V.score(pre, inv3, pins, truth, a.out / "a2-scored", chk, truth_sha256=sha_file(truth))
    Tt, silent, complete, comps, details, per_arm = res
    rule = V.A2.stoploss(Tt, silent, complete)
    expect(not chk.failures and complete and set(silent.values()) == {0} and rule["advance"]
           and all(v["critical_values"] == 54 and v["critical_errors"] == 0 for k, v in per_arm.items() if k.endswith("title")),
           f"both views scored in separate processes; paths/metrics validated; synthetic ADVANCE {chk.failures[:3]}")
    fr = per_arm["ab/native/frozen"]
    expect(fr["cer"] > per_arm["ab/native/title"]["cer"] == 0.0, "title view recovers the title<LEVELn> header (frozen CER > 0)")
    a2bad = a2_tree(a.out / "a2-damaged", fmt, Tg, rgb, damage={("ba", "carbon_surgical"): 5})
    inv4 = escrow.build("A2", a2bad, [])
    chk = Check()
    pre4 = dict(runs=V.prekey(inv4, pins, None, chk), inventory_sha256="x", failures=[])
    Tt, silent, complete, comps, _, _ = V.score(pre4, inv4, pins, truth, a.out / "a2-damaged-scored", chk,
                                                truth_sha256=sha_file(truth))
    rule = V.A2.stoploss(Tt, silent, complete)
    expect(not chk.failures and silent[("ba", "frozen")] == 1 and silent[("ba", "title")] == 1
           and silent[("ab", "frozen")] == 0 and not rule["advance"], "one new silent critical in BA halts at A2")
    s = load(a.out / "a2-scored" / "scores" / "ab-native-frozen.json")
    t1 = copy.deepcopy(s)
    t1["counts"]["critical_errors"] += 1
    t2 = copy.deepcopy(s)
    t2["pages"][4]["critical"] = t2["pages"][4]["critical"][:2]
    ch1, ch2 = Check(), Check()
    V.validate_score("tampered-count", t1, ch1)
    V.validate_score("missing-path", t2, ch2)
    expect(any("critical_errors" in f for f in ch1.failures) and any("54 distinct" in f for f in ch2.failures),
           "metric and path validation detect tampered scorer output")
    for what, path, field in (("projection", "a2-ab/segment-01-native/04-dev-native/page-003.json", "text"),
                              ("flag", "a2-ab/segment-01-native/04-dev-native/page-003.json", "spans")):
        root = a.out / f"a2-{what}"
        rr = a2_tree(root, fmt, Tg, rgb)
        f = root / path
        p = load(f)
        p[field] = (p["text"] + " extra") if field == "text" else [dict(x, flagged=True) for x in p["spans"]]
        jdump(f, p)
        pred = root / "a2-ab/segment-01-native/04-dev-native/prediction.json"
        pd = load(pred)
        pd["pages"][2] = p
        pred.write_bytes(json.dumps(pd).encode())
        tm = root / "a2-ab/segment-01-native/04-dev-native/timing.json"
        jdump(tm, dict(load(tm), prediction_sha256=sha_file(pred)))
        ch = Check()
        V.prekey(escrow.build("A2", rr, []), pins, None, ch)
        key = "frozen projection" if what == "projection" else "flagged == false"
        expect(any(key in x for x in ch.failures), f"pre-key detects a {what} defect from raw captures")
    expect(not V.pushed(truth, "0" * 40) and not V.pushed(HERE / "a2_views.py", "0" * 40),
           "pushed() refuses a file outside the repository or not at the given commit")
    result = dict(kind="WP-0017 reviewer continuation CPU self-test", created_utc=utc(), interpreter=sys.version,
                  tests=len(names), failures=T.failures, passed=len(names) - len(T.failures), test_names=names,
                  tool_sha256={p.name: sha_file(p) for p in sorted(HERE.glob("*.py"))},
                  note="synthetic key only; no dev, H, A or B key opened; no GPU")
    if a.receipt:
        write_new(a.receipt, result)
    print(json.dumps({k: v for k, v in result.items() if k != "test_names"}, indent=1))
    return 0 if not T.failures else 1


if __name__ == "__main__":
    sys.exit(main())
