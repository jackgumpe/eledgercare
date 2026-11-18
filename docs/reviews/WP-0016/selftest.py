"""CPU self-test for the WP-0016 escrow tools. Synthetic fixtures and public development demos only.

No H/A truth or prediction, no Packet B, no model, no torch and no device query. Every stage runs as its own
CLI process exactly as in the real escrow (escrow.py -> verify.py -> score_all.py; score.py and
title_adapt.py in further processes). Usage: python -I -B selftest.py --out <new directory>
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import (COORD, LABEL_FAMILY, MIB, PAGE_ID, REPO, git_blob, load, load_formats, materialize,  # noqa: E402
                    run_score, run_title_adapter, sha, split_segments, title_rule, utc, write_new)
from grammar import classify_page  # noqa: E402

PTS = [612.0, 792.0]
SOURCE = "a" * 40
LEASE = "synthetic-lease"
FILLER = ("Synthetic filler text used only to give every page a realistic character denominator for the "
          "quality budget; it carries no values and no identifiers. ") * 3
FAILS, PASSES = [], []


def expect(ok, what):
    print(("PASS " if ok else "FAIL ") + what)
    (PASSES if ok else FAILS).append(what)


def mbox(b):
    return [round(v * PTS[j % 2] / 999, 3) for j, v in enumerate(b)]


def dump(path, obj):
    data = (json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("xb") as fh:
        fh.write(data)
    return data


def spec_page(spec, num):
    blocks, lines, tables, vis = [], [], [], []
    for item in spec:
        kind, box = item[0], item[1]
        if kind in ("title", "text"):
            text = item[2]
            blocks.append((kind, box, text, item[3] if kind == "title" else None))
            lines.append(dict(text=text, bbox=mbox(box), critical=item[3] if kind == "text" else ""))
            vis.append(text)
        else:
            rows, crit = item[2], item[3]
            html = "<table>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>"
            blocks.append(("table", box, html, None))
            tb, nr, nc = mbox(box), len(rows), len(rows[0])
            w, h = tb[2] - tb[0], tb[3] - tb[1]
            cells = [[dict(text=c, critical=(ri, ci) in crit,
                           bbox=[tb[0] + w * ci / nc, tb[1] + h * ri / nr, tb[0] + w * (ci + 1) / nc, tb[1] + h * (ri + 1) / nr])
                      for ci, c in enumerate(r)] for ri, r in enumerate(rows)]
            tables.append(dict(bbox=tb, rows=cells))
            vis.append(" ".join(c for r in rows for c in r))
    return blocks, dict(page=num, width=612, height=792, text=" ".join(vis), lines=lines, tables=tables)


def raw_page(blocks, extra=""):
    s = "<PAGE>"
    for label, box, content, level in blocks:
        s += f"<BLOCK>{label}{f'<LEVEL{level}>' if level else ''}[{box[0]}, {box[1]}, {box[2]}, {box[3]}]<FORK>{content}\n"
    return s + extra


def tokens(raw):
    body = raw[len("<PAGE>"):]
    return [PAGE_ID] + [1000 + int.from_bytes(hashlib.sha256(body[i:i + 4].encode()).digest()[:2], "big")
                        for i in range(0, len(body), 4)]


SPECS = {
    "H": [[("title", [100, 40, 600, 70], "Synthetic Work Order", 1), ("text", [100, 120, 500, 140], "Order 4471 issued", "4471"),
           ("text", [100, 300, 950, 330], FILLER, "")],
          [("text", [100, 100, 400, 120], "See table", ""), ("table", [100, 300, 900, 400], [["Item", "Amount"], ["Valve", "12.50"]], {(1, 1)}),
           ("text", [100, 600, 950, 630], FILLER, "")],
          [("text", [100, 100, 400, 120], "Notes only", ""), ("text", [100, 300, 950, 330], FILLER, "")],
          [("text", [100, 100, 500, 120], "Total due 57.33", "57.33"), ("text", [100, 300, 950, 330], FILLER, "")]],
    "A": [[("text", [100, 100, 500, 120], "Ref 9001 opened", "9001"), ("text", [100, 300, 950, 330], FILLER, "")],
          [("table", [100, 300, 900, 400], [["Part", "Cost"], ["Seal", "88.10"]], {(1, 1)}), ("text", [100, 600, 950, 630], FILLER, "")],
          [("text", [100, 100, 400, 120], "Line three", ""), ("text", [100, 300, 950, 330], FILLER, "")],
          [("text", [100, 100, 500, 120], "Due 15.75 now", "15.75"), ("text", [100, 300, 950, 330], FILLER, "")],
          [("title", [100, 40, 600, 70], "Closing Section", 2), ("text", [100, 300, 950, 330], FILLER, "")]],
}
WARM = [[("text", [100, 100, 500, 120], "Warm page", "")]]


def edit(spec, page, old, new):
    out = [list(p) for p in spec]
    out[page] = [tuple(new if (isinstance(x, str) and x == old) else x for x in item) for item in out[page]]
    return out


def drop(spec, page, text):
    out = [list(p) for p in spec]
    out[page] = [item for item in out[page] if item[2] != text]
    return out


class Clock:
    def __init__(self, start, step):
        self.t, self.step = start, step

    def tick(self):
        self.t += self.step
        return self.t


def write_doc(folder, req, raws, fmt, clock, mode):
    folder.mkdir(parents=True)
    accepted = clock.tick()
    pages, milestones = [], []
    n = req["pages"]
    for first in range(0, n, 3):
        span = list(range(first, min(first + 3, n)))
        begin = clock.tick()
        toks = [tokens(raws[i]) for i in span]
        ids = [x for t in toks for x in t]
        marks = dict(generate_start=clock.tick(), first_token=clock.tick(), last_token=clock.tick(), generate_end=clock.tick())
        window = dict(source_sha256=req["sha256"], first_page=first + 1, pages=len(span), engine_begin_ns=begin,
                      engine_end_ns=clock.tick(), finish_reason="stop", num_pages_out=len(span), expected_pages=len(span),
                      time_s=1.0, prefill_time_s=0.1, prompt_len=100, visual_tokens=10, kernel_path="synthetic",
                      vram=dict(cuda_max_allocated_bytes=7000 * MIB, cuda_max_reserved_bytes=7600 * MIB),
                      clock_marks_ns=marks, forward_count=len(ids), window_token_ids=ids, raw_output="".join(raws[i] for i in span))
        if mode == "carbon_bf16":
            window.update(burst_extra_forwards=3, static_cache_reallocations=0, prefill_grouped_mm_layer_calls=12,
                          prefill_moe_fallback_layer_calls=0)
        dump(folder / f"window-{first + 1:03d}.json", window)
        for j, i in enumerate(span):
            dump(folder / f"raw-{i + 1:03d}.json", dict(page=i + 1, points=PTS, rgb_sha256=req["rgb_sha256"][i], width=2550,
                                                        height=3300, render_ns=5, source_sha256=req["sha256"],
                                                        raw_output=raws[i], token_ids=toks[j], token_classes={},
                                                        token_count=len(toks[j])))
            page = dict(source_sha256=req["sha256"], page=i + 1, state="complete", **fmt.native_page(raws[i], PTS))
            dump(folder / f"page-{i + 1:03d}.json", page)
            pages.append(page)
            milestones.append(clock.tick())
    pb = dump(folder / "prediction.json", dict(source_sha256=req["sha256"], pages=pages))
    committed = clock.tick()
    rec = dict(request=req, renderer={}, prediction_sha256=sha(pb), status="completed", accepted_ns=accepted,
               first_page_committed_ns=milestones[0], page_committed_ns=milestones, document_committed_ns=committed,
               elapsed_s=(committed - accepted) / 1e9, first_page_s=(milestones[0] - accepted) / 1e9, complete_pages=n)
    dump(folder / "timing.json", rec)
    return rec


def build_fixture(root, fmt, raws_for, device_peak=None):
    """Synthetic coordinator record, inputs, truth, plans and both segmented runs."""
    files, truth, inputs = {}, {}, {}
    warm_pdf = b"%PDF-synthetic-warm"
    warm_rgb = sha(b"warm-rgb")
    for fam, spec in SPECS.items():
        pdf = f"%PDF-synthetic-{fam}".encode()
        d = root / "inputs" / fam
        d.mkdir(parents=True)
        (d / "source.pdf").write_bytes(pdf)
        rgb = [sha(f"{fam}-rgb-{i}".encode()) for i in range(1, len(spec) + 1)]
        rin = dump(d / "rasters.input.json", dict(family=fam, pdf_sha256=sha(pdf), pdf_bytes=len(pdf), renderer={},
                                                   pages=[dict(page_number=i, rgb_sha256=r, width_px=2550, height_px=3300)
                                                          for i, r in enumerate(rgb, 1)]))
        t = dict(family=fam, source_sha256=sha(pdf), pages=[spec_page(p, i)[1] for i, p in enumerate(spec, 1)])
        tb = dump(root / "scoring" / fam / "truth.json", t)
        rb = dump(root / "scoring" / fam / "rasters.json", dict(pages=[dict(page_number=i, rgb_sha256=r) for i, r in enumerate(rgb, 1)]))
        files[fam] = {"source.pdf": sha(pdf), "truth.json": sha(tb), "rasters.json": sha(rb)}
        inputs[fam] = dict(files=files[fam], pages=len(spec), raster_input_sha256=sha(rin), rgb=rgb, pdf=str(d / "source.pdf"))
        truth[fam] = t
    (root / "warm.pdf").write_bytes(warm_pdf)
    common = [dict(label=f"warm-{i}", warmup=True, pages=1, pdf=str(root / "warm.pdf"), sha256=sha(warm_pdf), rgb_sha256=[warm_rgb])
              for i in (1, 2, 3)]
    common += [dict(label=f.lower(), warmup=False, pages=inputs[f]["pages"], pdf=inputs[f]["pdf"], sha256=files[f]["source.pdf"],
                    rgb_sha256=inputs[f]["rgb"]) for f in ("H", "A")]
    orders = {}
    for order, modes in (("ab", ["native", "carbon_bf16"]), ("ba", ["carbon_bf16", "native"])):
        data = dump(root / "coordination" / "plans" / f"g0-{order}.json", dict(requests=[dict(r, mode=m) for m in modes for r in common]))
        orders[order] = dict(path=str(root / "coordination" / "plans" / f"g0-{order}.json"), sha256=sha(data), order=modes)
    dump(root / "g0-plans.json", dict(gate="G0", warm_sha256=sha(warm_pdf), warm_rgb_sha256=warm_rgb, orders=orders,
                                      inputs={f: {k: v for k, v in i.items() if k in ("files", "pages", "raster_input_sha256")}
                                              for f, i in inputs.items()}))
    dump(root / "commitments.json", dict(packets={f: dict(pages=inputs[f]["pages"], files=files[f]) for f in files}))
    runs = []
    for order, b in orders.items():
        run = root / "runs" / f"g0-{order}"
        plan_bytes = Path(b["path"]).read_bytes()
        run.mkdir(parents=True)
        (run / "plan.json").write_bytes(plan_bytes)
        requests = json.loads(plan_bytes)["requests"]
        segs = split_segments(requests)
        dump(run / "launch.json", dict(source=SOURCE, head=SOURCE, lease=LEASE, plan_sha256=sha(plan_bytes),
                                       segment_modes=[m for m, _ in segs], plan_path=b["path"]))
        samples, receipts = [], []
        for si, (mode, reqs) in enumerate(segs, 1):
            seg = run / f"segment-{si:02d}-{mode}"
            seg.mkdir()
            dump(seg / "plan.json", dict(mode=mode, requests=reqs))
            dump(seg / "child.json", dict(pid=4000 + si, creation_filetime=1, mode=mode))
            (seg / "cache").mkdir()
            (seg / "cache" / "module.bin").write_bytes(b"synthetic runtime cache")
            clock = Clock(10 ** 12 * si, 50_000_000 if mode == "native" else 20_000_000)
            extra = {"weight_allocated_bytes_after_pack": 6000 * MIB} if mode == "carbon_bf16" else {}
            dump(seg / f"load-{mode}.json", dict(elapsed_s=12.5, renderer={}, model_revision="synthetic", manifest_sha256="m",
                                                 dependency_lock_sha256="l", tokenizer_sha256="t", eos_id=1, page_id=PAGE_ID,
                                                 target_dtype="torch.bfloat16", **extra))
            results = []
            for i, req in enumerate(reqs, 1):
                dump(seg / f"started-{i:02d}.json", dict(request=req, start_ns=clock.tick()))
                fam = "W" if req["warmup"] else LABEL_FAMILY[req["label"]]
                results.append(write_doc(seg / f"{i:02d}-{req['label']}-{mode}", req, raws_for(order, mode, fam), fmt, clock, mode))
            dump(seg / "session.json", results)
            (seg / "stdout.txt").write_bytes(b"")
            (seg / "stderr.txt").write_bytes(b"")
            used = device_peak.get((order, mode), 7800) if device_peak else 7800
            samples.append(dict(s=5.0 * si, segment=si, mode=mode, uuid="GPU-synthetic", free_mib=16000 - used, used_mib=used,
                                temperature_c=55.0, utilization_percent=90, driver="synthetic"))
            rec = dict(segment=si, mode=mode, cmd=[], pid=4000 + si, child_meta={}, returncode=0, elapsed_s=60.0, reason=None,
                       storage_before_segment={}, gpu_before_segment=dict(used_mib=600, free_mib=15400),
                       gpu_after_segment=dict(used_mib=600, free_mib=15400))
            dump(seg / "segment-process.json", rec)
            receipts.append(rec)
        dump(run / "process.json", dict(segments=receipts, all_segments_completed=True, overall_reason=None, elapsed_s=130.0,
                                        gpu_samples=samples, final_gpu={}, storage_after={}, end_utc=""))
        runs.append(run)
    return runs, truth


def windows_store(root, wrong):
    """Synthetic stored Windows predictions/timings and the hash-only inventories that bind them."""
    store, invd = root / "windows-store", root / "wp15"
    invd.mkdir()
    names = {"H": ("wp15-H-inventory.json", [("h-r1-ab", "04-h-windows", 1.0), ("h-r2-ba", "03-h-windows", 1.05)]),
             "A": (None, [("a-recovery-ab", "04-a-windows", 2.0), ("a-scale-ba", "03-a-windows", 2.2)])}
    invs = {"wp15-H-inventory.json": [], "wp15-A-recovery-inventory.json": [], "wp15-A-inventory.json": []}
    for fam, (_, refs) in names.items():
        src = sha(f"%PDF-synthetic-{fam}".encode())
        pages = []
        for i, spec in enumerate(SPECS[fam], 1):
            _, tp = spec_page(spec, i)
            spans = [dict(text=wrong.get((fam, ln["text"]), ln["text"]), bbox=ln["bbox"]) for ln in tp["lines"]]
            spans += [dict(text=wrong.get((fam, c["text"]), c["text"]), bbox=[c["bbox"][0] + 1, c["bbox"][1] + 1, c["bbox"][2] - 1, c["bbox"][3] - 1])
                      for t in tp["tables"] for r in t["rows"] for c in r]
            pages.append(dict(source_sha256=src, page=i, state="complete", text=" ".join(s["text"] for s in spans), spans=spans, tables=[]))
        for run, folder, secs in refs:
            d = store / run / folder
            pb = dump(d / "prediction.json", dict(source_sha256=src, pages=pages))
            tb = dump(d / "timing.json", dict(request=dict(mode="windows", label=fam.lower()), prediction_sha256=sha(pb), elapsed_s=secs))
            key = ("wp15-H-inventory.json" if fam == "H" else
                   "wp15-A-recovery-inventory.json" if run == "a-recovery-ab" else "wp15-A-inventory.json")
            invs[key].append(dict(run=run, files={f"{folder}/prediction.json": sha(pb), f"{folder}/timing.json": sha(tb)}))
    for name, runs in invs.items():
        dump(invd / name, dict(runs=runs))
    return store, invd


def py(script, *args):
    return subprocess.run([sys.executable, "-I", "-B", str(HERE / script), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", stdin=subprocess.DEVNULL)


def stages(root, pins, runs, store=None, invd=None, mutate_after_inventory=None, score=True):
    inv = root / "escrow" / "blind-inventory.json"
    r0 = py("escrow.py", "--runs", *runs, "--plans", root / "g0-plans.json", "--out", inv)
    if r0.returncode:
        raise SystemExit(r0.stderr)
    if mutate_after_inventory:
        mutate_after_inventory()
    r1 = py("verify.py", "--inventory", inv, "--plans", root / "g0-plans.json", "--inputs", root / "inputs", "--pins", pins,
            "--source", SOURCE, "--lease", LEASE, "--out", root / "escrow" / "stage1")
    s1 = load(root / "escrow" / "stage1" / "stage1.json") if (root / "escrow" / "stage1" / "stage1.json").exists() else None
    if s1 is None:
        raise SystemExit(r1.stderr)
    if not score:
        return load(inv), s1, None
    r2 = py("score_all.py", "--stage1", root / "escrow" / "stage1" / "stage1.json", "--inventory", inv, "--plans",
            root / "g0-plans.json", "--pins", pins, "--scoring", root / "scoring", "--commitments", root / "commitments.json",
            "--windows-store", store, "--wp15-inventories", invd, "--out", root / "escrow" / "stage2")
    if not (root / "escrow" / "stage2" / "summary.json").exists():
        raise SystemExit(r2.stderr)
    return load(inv), s1, load(root / "escrow" / "stage2" / "summary.json")


def base_raws(spec_for, extra_for=None):
    def raws_for(order, mode, fam):
        spec = WARM if fam == "W" else spec_for(order, mode, fam)
        return [raw_page(spec_page(p, i)[0], (extra_for or (lambda *k: ""))(order, mode, fam, i))
                for i, p in enumerate(spec, 1)]
    return raws_for


def scenario_clean(out, pins, fmt):
    root = out / "clean"
    runs, _ = build_fixture(root, fmt, base_raws(lambda o, m, f: SPECS[f]))
    store, invd = windows_store(root, {("H", "Order 4471 issued"): "Order 4411 issued", ("H", "12.50"): "12.80"})
    inv, s1, s2 = stages(root, pins, runs, store, invd)
    expect(not s1["failures"] and s1["checks_run"] > 200, f"clean: stage 1 has no failures ({s1['checks_run']} checks)")
    expect(not inv["plans_record_pinned"] and not s1["real_binding"], "clean: synthetic record is never reported as pinned")
    expect(all(len(r["runtime_cache_files"]) == 2 for r in inv["runs"]), "clean: runtime cache files hashed separately")
    expect(all(v["identical"] for f in s1["token_parity"].values() for v in f.values()), "clean: token parity identical everywhere")
    expect(s1["timing"]["A"]["pairs"]["ab"]["saving_s"] > 0, "clean: carbon saving recorded")
    expect(s1["runs"]["g0-ab"]["arms"]["native"]["summary"]["grammar_measured"]["header_title_level"] == 2,
           "clean: H/A title<LEVELn> headers classified title_level (2)")
    expect(s1["runs"]["g0-ab"]["arms"]["native"]["summary"]["grammar_measured"]["parser_disagreements"] == 0,
           "clean: grammar agrees with pinned BLOCK and TITLE regexes")
    v = s2["verdict"]
    expect(not s2["failures"], f"clean: stage 2 has no failures {s2['failures'][:3]}")
    expect(len(v["gate_comparisons"]) == 8 and all(v["gate_comparisons"].values()), "clean: all 8 gate comparisons pass")
    expect(v["g0_pass"] is False and "NOT A GATE RESULT" in v.get("label", ""), "clean: synthetic binding cannot yield a G0 pass")
    c = s2["comparisons"]["H:frozen:windows->native-ab"]
    rec = c["recovery"]["primary"]
    expect(c["critical"]["counts"]["repair"] == 2 and c["critical"]["net_recovery"] == 2, "clean: Windows->native repairs 2 criticals")
    expect(abs(rec["net_critical_per_extra_s"] - 2 / (rec["neural_s"] - 1.0)) < 1e-12, "clean: recovery per extra neural second")
    fr = s2["per_arm"]["H:native-ab:frozen"]
    ti = s2["per_arm"]["H:native-ab:title"]
    expect(ti["edits"] == 0 and fr["edits"] > 0, "clean: title view removes the frozen header misparse (edits -> 0)")
    expect(s2["title_correction"]["H:native-ab"]["recognized_headers"] == 1, "clean: title adapter receipt counts 1 H header")
    expect(s2["critical_patterns"]["H:frozen"]["counts"].get("CCCCW") == 2, "clean: 5-arm pattern CCCCW for 2 Windows misses")
    return s2


def scenario_faults(out, pins, fmt):
    root = out / "faults"

    def spec_for(order, mode, fam):
        if fam == "H" and mode == "native":
            return edit(SPECS["H"], 0, "Order 4471 issued", "Order 4477 issued")
        if fam == "H":
            return edit(SPECS["H"], 3, "Total due 57.33", "Total due 57.38")
        if fam == "A" and mode == "carbon_bf16":
            return drop(SPECS["A"], 3, "Due 15.75 now")
        return SPECS[fam]
    runs, _ = build_fixture(root, fmt, base_raws(spec_for), device_peak={("ab", "carbon_bf16"): 10500})
    store, invd = windows_store(root, {})
    _, s1, s2 = stages(root, pins, runs, store, invd)
    g = s2["comparisons"]["H:frozen:native-ab->carbon-ab"]
    expect(g["critical"]["counts"]["regress"] == 1 and g["critical"]["counts"]["repair"] == 1 and g["critical"]["net_recovery"] == 0,
           "faults: H net-flat swap (1 regress, 1 repair)")
    expect(g["inside_quality_budget"] and g["critical"]["new_unflagged"] == 1 and g["g0_pass"] is False,
           "faults: one new unflagged critical is a hard fail although inside budget and net flat")
    expect(g["critical"]["four_way"] == dict(CC=1, CW=1, WC=1, WW=0), "faults: four-way CC/CW/WC/WW")
    a = s2["comparisons"]["A:title:native-ba->carbon-ba"]
    expect(a["critical"]["counts"]["abstain"] == 1 and a["critical"]["new_unflagged"] == 1 and not a["g0_pass"],
           "faults: A dropped critical counted as abstain and fails")
    expect(s2["per_arm"]["A:carbon-ab:frozen"]["critical_abstentions"] == 1, "faults: per-arm abstention count")
    expect(s1["memory"]["ab:carbon_bf16"]["device_within_g0"] is False and not s2["verdict"]["memory_within"]["ab"],
           "faults: 10,500 MiB device sample fails the memory gate")
    expect(not s1["token_parity"]["H"]["ab:carbon_vs_native"]["identical"], "faults: H token parity broken and located")


def scenario_malformed(out, pins, fmt):
    root = out / "malformed"
    extra = lambda o, m, f, i: "<BLOCK>t[1" if (f == "A" and m == "carbon_bf16" and i == 3) else ""
    runs, _ = build_fixture(root, fmt, base_raws(lambda o, m, f: SPECS[f], extra))
    store, invd = windows_store(root, {})
    _, s1, s2 = stages(root, pins, runs, store, invd)
    gm = s1["runs"]["g0-ab"]["arms"]["carbon_bf16"]["summary"]["grammar_measured"]
    gn = s1["runs"]["g0-ab"]["arms"]["native"]["summary"]["grammar_measured"]
    expect(gm["header_malformed"] == 1 and gm["malformed_reasons"] == {"no_fork_before_next_block_or_end": 1}
           and gn.get("header_malformed", 0) == 0, "malformed: header recorded with named reason on carbon only")
    page = s1["runs"]["g0-ab"]["arms"]["carbon_bf16"]["grammar_pages"]["A"][2]
    expect(page["page"] == 3 and page["source_sha256"] and not page["structurally_valid"], "malformed: located by source/page")
    ok = all(s2["comparisons"][f"A:{v}:native-{o}->carbon-{o}"]["g0_pass"] for v in ("frozen", "title") for o in ("ab", "ba"))
    expect(ok, "malformed: G0 gate comparisons still pass (zero malformed is not a G0 criterion)")


def scenario_tamper(out, pins, fmt):
    cases = {
        "after-inventory": (None, "differs from blind inventory"),
        "tokens": ("window", "token reassembly"),
        "rgb": ("rgb", "rgb pin"),
        "projection": ("projection", "not the frozen projection"),
        "stop": ("stop", "finish_reason"),
        "source": ("source", "launched source"),
    }
    for name, (kind, needle) in cases.items():
        root = out / "tamper" / name
        runs, _ = build_fixture(root, fmt, base_raws(lambda o, m, f: SPECS[f]))
        doc = runs[0] / "segment-02-carbon_bf16" / "04-h-carbon_bf16"

        def rewrite(path, fn):
            obj = json.loads(path.read_bytes())
            fn(obj)
            path.write_bytes((json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode())
        if kind == "window":
            rewrite(doc / "window-001.json", lambda o: o["window_token_ids"].__setitem__(5, 7))
        elif kind == "rgb":
            rewrite(doc / "raw-002.json", lambda o: o.__setitem__("rgb_sha256", "0" * 64))
        elif kind == "projection":
            for p in (doc / "page-001.json",):
                rewrite(p, lambda o: o.__setitem__("text", o["text"] + " 99.99"))
            pred = json.loads((doc / "prediction.json").read_bytes())
            pred["pages"][0]["text"] += " 99.99"
            pb = (json.dumps(pred, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
            (doc / "prediction.json").write_bytes(pb)
            rewrite(doc / "timing.json", lambda o: o.__setitem__("prediction_sha256", sha(pb)))
            seg = doc.parent
            sess = json.loads((seg / "session.json").read_bytes())
            sess[3]["prediction_sha256"] = sha(pb)
            (seg / "session.json").write_bytes((json.dumps(sess, ensure_ascii=False, separators=(",", ":")) + "\n").encode())
        elif kind == "stop":
            rewrite(doc / "window-004.json", lambda o: o.__setitem__("finish_reason", "length"))
        elif kind == "source":
            rewrite(runs[1] / "launch.json", lambda o: o.__setitem__("source", "b" * 40))
        after = (lambda: (doc / "prediction.json").write_bytes((doc / "prediction.json").read_bytes() + b" ")) if kind is None else None
        _, s1, _ = stages(root, pins, runs, mutate_after_inventory=after, score=False)
        expect(any(needle in f for f in s1["failures"]), f"tamper {name}: caught ({needle})")


def public_dev(out, pins, fmt):
    """Reproduce the committed public title<LEVELn> sensitivity with the isolated adapter + separate scorer."""
    root = out / "public-dev"
    rule = title_rule(pins)
    listing = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", COORD, "--",
                              "docs/research/WP-0015/astra/evidence/dev-ab-01", "docs/research/WP-0015/astra/evidence/dev-ba-01",
                              "docs/research/WP-0015/astra/sensitivity-title-level/scores", "docs/evaluation/WP-0015/dev"],
                             check=True, capture_output=True, text=True).stdout.split()
    for path in listing:
        dest = root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(git_blob(COORD, path))
    ev = root / "docs/research/WP-0015/astra/evidence"
    sens = root / "docs/research/WP-0015/astra/sensitivity-title-level/scores"
    summary = load(sens / "summary.json")
    n = 0
    for order in ("dev-ab-01", "dev-ba-01"):
        for case in ("short", "dense", "boundary"):
            folder, = (ev / order).glob(f"[0-9][0-9]-{case}-native")
            truth = root / "docs/evaluation/WP-0015/dev" / case / "truth.json"
            committed = load(sens / f"{order}-{case}.json")
            work = root / "work" / f"{order}-{case}"
            pred, receipt = run_title_adapter(pins, folder, work / "title.prediction.json", work / "title.receipt.json")
            expect(pred == committed["corrected_native_prediction"], f"public {order}/{case}: corrected prediction identical")
            got = run_score(pins, truth, work / "title.prediction.json", work / "title.score.json")
            expect(got == committed["corrected_native_score"], f"public {order}/{case}: separate-process corrected score identical")
            off = run_score(pins, truth, folder / "prediction.json", work / "official.score.json")
            expect(off == load(ev / order / "scores" / f"{folder.name}-score.json"), f"public {order}/{case}: official score identical")
            want = [len(p["recognized_headers"]) for p in summary[order][case]["pages"]]
            have = [r["recognized_headers"] for r in receipt["pages"]]
            grams = [classify_page(load(folder / f"raw-{i:03d}.json")["raw_output"], fmt.BLOCK, rule) for i in range(1, len(have) + 1)]
            expect(have == want and [g["classes"].get("title_level", 0) for g in grams] == want
                   and all(g["agrees_with_frozen_block"] and g["agrees_with_title_rule"] for g in grams),
                   f"public {order}/{case}: header counts {have} match rule, receipt and grammar")
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True, help="new directory")
    ap.add_argument("--receipt", type=Path, help="new JSON receipt binding results to the committed tool bytes")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    pins = a.out / "pins"
    manifest = materialize(pins)
    fmt = load_formats(pins)
    expect(manifest["score.py"]["sha256"].endswith("f4bf7"), "pins: frozen score.py ...f4bf7 materialised and verified")
    expect(manifest["title_rule"]["extracted_by"] == "ast", "pins: title rule extracted by AST from committed rescore.py")
    g = classify_page("<PAGE><BLOCK>title<LEVEL1>[1, 2, 3, 4]<FORK>A\n<BLOCK>text[5, 6, 7, 8]<FORK><BLOCK>x[9, 9"
                      "<BLOCK>sub<LEVEL2>[1, 2, 3, 4]<FORK>C<FORK><BLOCK>text[9, 1, 2, 1000]<FORK><ODD><table><tr>",
                      fmt.BLOCK, title_rule(pins))
    expect(g["classes"] == dict(title_level=1, frozen=2, malformed=1, undocumented_level=1) and g["orphan_fork"] == 1
           and g["box_invalid"] == 1 and g["unknown_specials"] == {"<ODD>": 1} and g["table_unbalanced"]
           and g["empty_blocks"] == 1 and not g["structurally_valid"] and g["agrees_with_frozen_block"]
           and g["agrees_with_title_rule"], "grammar: all header classes and structure faults on a synthetic page")
    scenario_clean(a.out, pins, fmt)
    scenario_faults(a.out, pins, fmt)
    scenario_malformed(a.out, pins, fmt)
    scenario_tamper(a.out, pins, fmt)
    n = public_dev(a.out, pins, fmt)
    print(json.dumps(dict(failures=FAILS, public_dev_cases=n), indent=1))
    if a.receipt:
        git = lambda *k: subprocess.run(["git", "-C", str(REPO), *k], check=True, capture_output=True, text=True).stdout.strip()
        write_new(a.receipt, dict(kind="WP-0016 escrow tooling CPU self-test receipt", reviewer="eld-rd-reviewer",
                                  created_utc=utc(), head=git("rev-parse", "HEAD"),
                                  tools_clean_at_head=git("status", "--porcelain", "--", str(HERE)) == "",
                                  tools={p.name: sha(p.read_bytes()) for p in sorted(HERE.glob("*.py"))},
                                  interpreter=sys.version, flags="-I -B", scratch=str(a.out), pins=manifest,
                                  inputs="synthetic fixtures and public development demos only; no H/A truth or "
                                         "prediction, no Packet B, no model, torch or device query",
                                  passed=len(PASSES), failed=len(FAILS), checks=PASSES, failures=FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
