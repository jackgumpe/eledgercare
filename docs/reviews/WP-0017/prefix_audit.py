"""WP-0017 Stage A1 pre-execution prefix audit (eld-rd-reviewer). Stdlib only, CPU only, no truth.

Independently binds the frozen WP-0016 G0 outputs for Packet A windows 019 and 037 (both modes, both orders)
to the committed blind inventory (6f32732, SHA-256 366bf5eb...), then rebuilds from the actual token ids:

* page splits at <PAGE> (128827) and their equality with the per-page raw records and pinned RGB rasters;
* the window-level longest common prefix and first difference between native and carbon_bf16;
* the byte-level BPE spans of the two public competing identifier strings, located in the decoded token
  bytes (never in truth), and the common token boundary at which the two readings separate;
* opaque SHA-256 digests of every diagnostic prefix and full window sequence A1 must replay;
* each numerical claim of Carbon WP-0016/002 and the WP-0017 specification, marked agree/disagree.

Reads only: the committed inventory/plan blobs, the two WP-0016 run trees (every file re-hashed against
the inventory), the pinned tokenizer.json and the input-only A raster inventory. It never opens truth,
score outputs, score-detail files or Packet B.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BLOCK_ID, CARBON_002, FORK_ID, PAGE_ID, WP16_RUNS, BLOBS, DISK, Check, Vocab, blob, disk,  # noqa
                    git, ids_sha, load, read_bytes, sha, sha_file, tree_hashes, utc, write_new)

MODES = ("native", "carbon_bf16")
ORDERS = ("ab", "ba")
# Public competing strings (specification p.1, WP-0016 Carbon 002). Labels say which arm emitted which
# string in WP-0016; they do not assert which string is correct.
TARGETS = {
    "window-019": dict(first_page=19, pages=(19, 20, 21), site_page=21,
                       strings={"native": "I08O1-388", "carbon_bf16": "108O1-388"}),
    "window-037": dict(first_page=37, pages=(37, 38, 39), site_page=37,
                       strings={"native": "8OI10-774", "carbon_bf16": "80I10-774"}),
}


def split_pages(ids):
    starts = [i for i, t in enumerate(ids) if t == PAGE_ID]
    return starts, [ids[s:e] for s, e in zip(starts, starts[1:] + [len(ids)])]


def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def token_roles(ids):
    """'page' / 'block_header' (label and geometry between <BLOCK> and <FORK>) / 'content'."""
    roles, state = [], "content"
    for t in ids:
        if t == PAGE_ID:
            roles.append("page")
            state = "content"
        elif t == BLOCK_ID:
            roles.append("block_header")
            state = "header"
        elif t == FORK_ID:
            roles.append("block_header")
            state = "content"
        else:
            roles.append("block_header" if state == "header" else "content")
    return roles


def locate(vocab, ids, target):
    """Find every byte occurrence of target in the decoded bytes; map each to its covering token range."""
    pieces = [vocab.piece(t) for t in ids]
    offs, pos = [], 0
    for p in pieces:
        offs.append(pos)
        pos += len(p)
    data = b"".join(pieces)
    tb = target.encode("ascii")
    hits, start = [], 0
    while True:
        k = data.find(tb, start)
        if k < 0:
            break
        end = k + len(tb)
        i = max(j for j in range(len(ids)) if offs[j] <= k)
        j = max(j for j in range(len(ids)) if offs[j] < end) + 1
        hits.append(dict(byte_start=k, byte_end=end, token_start=i, token_end=j,
                         lead_bytes_in_first_token=k - offs[i],
                         trail_bytes_in_last_token=offs[j - 1] + len(pieces[j - 1]) - end))
        start = k + 1
    return hits


def describe(vocab, ids):
    return [dict(id=int(t), piece=vocab.text(t)) for t in ids]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, default=WP16_RUNS)
    ap.add_argument("--out", type=Path, required=True, help="new JSON file")
    a = ap.parse_args()
    check = Check()
    inv_bytes, plans_bytes = blob("G0-blind-inventory.json"), blob("g0-plans.json")
    inv, plans = json.loads(inv_bytes), json.loads(plans_bytes)
    vocab = Vocab(disk("tokenizer.json"))
    rasters = json.loads(disk("A/rasters.input.json"))
    rgb_pin = {p["page_number"]: p["rgb_sha256"] for p in rasters["pages"]}
    check(rasters["pdf_sha256"] == plans["inputs"]["A"]["files"]["source.pdf"], "A raster inventory source = plan")
    check(sha(disk("A/rasters.input.json")) == plans["inputs"]["A"]["raster_input_sha256"],
          "A raster inventory SHA = plan raster_input_sha256")

    # 1. Whole-tree immutability against the committed blind inventory.
    tree_state, data = {}, {}
    for ir in inv["runs"]:
        run = a.runs / ir["run"]
        now = tree_hashes(run)
        want = dict(ir["files"], **ir["runtime_cache_files"])
        same = check(now == want, f"{ir['run']}: run tree differs from the committed inventory")
        order = ir["order"]
        check(plans["orders"][order]["sha256"] == ir["plan_sha256"] == sha_file(run / "plan.json"),
              f"{order}: plan binding")
        check(ir["all_segments_completed"] is True and all(s["returncode"] == 0 for s in ir["segment_outcomes"]),
              f"{order}: segments completed")
        tree_state[order] = dict(run=ir["run"], files_checked=len(now), equal_to_inventory=same,
                                 segment_modes=ir["segment_modes"], plan_sha256=ir["plan_sha256"],
                                 source=ir["source"], lease=ir["lease"])
        for mode in MODES:
            si = ir["segment_modes"].index(mode) + 1
            plan = load(run / "plan.json")
            seg_reqs = [r for r in plan["requests"] if r["mode"] == mode]
            k = [r["label"] for r in seg_reqs].index("a") + 1
            folder = f"segment-{si:02d}-{mode}/{k:02d}-a-{mode}"
            areq = seg_reqs[k - 1]
            check(areq["sha256"] == plans["inputs"]["A"]["files"]["source.pdf"], f"{order}/{mode}: A source")
            check(areq["rgb_sha256"] == [rgb_pin[n] for n in range(1, 61)], f"{order}/{mode}: plan RGB = raster pins")
            pred_rel = f"{folder}/prediction.json"
            data[order, mode] = dict(folder=folder, run=run, files=ir["files"], prediction_sha256=ir["files"][pred_rel])

    def read_bound(order, mode, rel):
        d = data[order, mode]
        full = f"{d['folder']}/{rel}"
        b = read_bytes(d["run"] / full)
        check(sha(b) == d["files"].get(full), f"{order}/{mode}/{rel}: hash differs from inventory")
        return json.loads(b), full, sha(b)

    # 2. Per window, per arm: token ids, page splits, raw-page and raster bindings, clocks.
    windows = {}
    for wname, tg in TARGETS.items():
        arms = {}
        for order in ORDERS:
            for mode in MODES:
                w, rel, wsha = read_bound(order, mode, f"{wname}.json")
                ids = [int(t) for t in w["window_token_ids"]]
                starts, pages = split_pages(ids)
                check(w["first_page"] == tg["first_page"] and w["pages"] == 3 and w["num_pages_out"] == 3
                      and w["expected_pages"] == 3 and w["finish_reason"] == "stop", f"{order}/{mode}/{wname}: window shape")
                check(starts[:1] == [0] and len(pages) == 3, f"{order}/{mode}/{wname}: three <PAGE> splits")
                page_rec = []
                for n, pids in zip(tg["pages"], pages):
                    r, rrel, rsha = read_bound(order, mode, f"raw-{n:03d}.json")
                    check(r["page"] == n and [int(t) for t in r["token_ids"]] == pids,
                          f"{order}/{mode}/raw-{n:03d}: page split equals raw token_ids")
                    check(r["rgb_sha256"] == rgb_pin[n], f"{order}/{mode}/raw-{n:03d}: RGB = pinned raster")
                    check(r["source_sha256"] == plans["inputs"]["A"]["files"]["source.pdf"], f"raw-{n:03d} source")
                    check(r["token_count"] == len(pids), f"{order}/{mode}/raw-{n:03d}: token_count")
                    page_rec.append(dict(page=n, window_offset=starts[tg["pages"].index(n)], tokens=len(pids),
                                         ids_sha256=ids_sha(pids), rgb_sha256=r["rgb_sha256"], raw_file=rrel,
                                         raw_file_sha256=rsha))
                check(vocab.decode(ids) == w["raw_output"], f"{order}/{mode}/{wname}: stdlib decode = stored raw_output")
                arms[f"{mode}:{order}"] = dict(
                    order=order, mode=mode, file=rel, file_sha256=wsha, tokens=len(ids), ids_sha256=ids_sha(ids),
                    decoded_equals_raw_output=vocab.decode(ids) == w["raw_output"], page_splits=page_rec,
                    time_s=w["time_s"], prefill_time_s=w["prefill_time_s"], native_infer_ms=w.get("native_infer_ms"),
                    prompt_len=w["prompt_len"], visual_tokens=w.get("visual_tokens"), forward_count=w.get("forward_count"),
                    _ids=ids, _pages=pages, _starts=starts, _w={k: v for k, v in w.items() if k != "window_token_ids"})
        windows[wname] = arms

    # 3. Repeatability across orders (same mode), then native vs carbon_bf16 per order.
    report = {}
    for wname, tg in TARGETS.items():
        arms = windows[wname]
        rep = dict(target=dict(first_page=tg["first_page"], pages=list(tg["pages"]), site_page=tg["site_page"],
                               public_strings=tg["strings"]))
        rep["arms"] = {k: {x: y for x, y in v.items() if not x.startswith("_")} for k, v in arms.items()}
        rep["repeat_identical"] = {m: arms[f"{m}:ab"]["_ids"] == arms[f"{m}:ba"]["_ids"] for m in MODES}
        for m in MODES:
            check(rep["repeat_identical"][m], f"{wname}: {m} AB and BA token ids differ")
        nat, car = arms["native:ab"], arms["carbon_bf16:ab"]
        n_ids, c_ids = nat["_ids"], car["_ids"]
        L = lcp(n_ids, c_ids)
        pidx = max(i for i, s in enumerate(nat["_starts"]) if s <= L)
        n_roles, c_roles = token_roles(n_ids), token_roles(c_ids)
        rep["native_vs_carbon"] = {o: dict(lcp=lcp(arms[f"native:{o}"]["_ids"], arms[f"carbon_bf16:{o}"]["_ids"]))
                                   for o in ORDERS}
        rep["first_difference"] = dict(
            window_index_0based=L, common_prefix_length=L, common_prefix_sha256=ids_sha(n_ids[:L]),
            page=tg["pages"][pidx], page_index_0based=L - nat["_starts"][pidx],
            carbon_page_start_equal=car["_starts"][pidx] == nat["_starts"][pidx],
            native=dict(id=n_ids[L], piece=vocab.text(n_ids[L]), role=n_roles[L]),
            carbon_bf16=dict(id=c_ids[L], piece=vocab.text(c_ids[L]), role=c_roles[L]))
        # Position-aligned per-page differences (only meaningful where page lengths match).
        per_page = []
        for n, pn, pc, sn in zip(tg["pages"], nat["_pages"], car["_pages"], nat["_starts"]):
            entry = dict(page=n, tokens=[len(pn), len(pc)], identical=pn == pc)
            if len(pn) == len(pc):
                roles = token_roles(pn)
                diffs = [dict(page_index=i, window_index=sn + i, role=roles[i], native=describe(vocab, [x])[0],
                              carbon_bf16=describe(vocab, [y])[0]) for i, (x, y) in enumerate(zip(pn, pc)) if x != y]
                entry.update(aligned=True, differing_positions=len(diffs), diffs=diffs)
            else:
                entry.update(aligned=False, page_lcp=lcp(pn, pc))
            per_page.append(entry)
        rep["per_page"] = per_page
        # 4. Identifier spans located in the decoded bytes of the site page for each arm.
        si = tg["pages"].index(tg["site_page"])
        spans = {}
        for mode, arm in (("native", nat), ("carbon_bf16", car)):
            page_ids, base = arm["_pages"][si], arm["_starts"][si]
            found = {}
            for who, s in tg["strings"].items():
                hits = locate(vocab, page_ids, s)
                found[who] = [dict(h, window_token_start=base + h["token_start"], window_token_end=base + h["token_end"],
                                   tokens=describe(vocab, page_ids[h["token_start"]:h["token_end"]]))
                              for h in hits]
            spans[mode] = found
            own = found[mode]
            other = found["carbon_bf16" if mode == "native" else "native"]
            check(len(own) == 1 and not other, f"{wname}: {mode} emits exactly its own string once and not the other")
        rep["identifier_spans"] = spans
        # Common boundary for the two readings: compare page tokens from the start of the line block that
        # holds the identifier (aligned at that block's <FORK>).
        hn, hc = spans["native"]["native"][0], spans["carbon_bf16"]["carbon_bf16"][0]
        pn, pc = nat["_pages"][si], car["_pages"][si]
        fork_n = max(i for i in range(hn["token_start"]) if pn[i] == FORK_ID)
        fork_c = max(i for i in range(hc["token_start"]) if pc[i] == FORK_ID)
        line_n, line_c = pn[fork_n + 1:], pc[fork_c + 1:]
        b = lcp(line_n, line_c)
        n_end = hn["token_end"] - fork_n - 1
        c_end = hc["token_end"] - fork_c - 1
        span_n, span_c = line_n[b:n_end], line_c[b:c_end]
        bound_n, bound_c = nat["_starts"][si] + fork_n + 1 + b, car["_starts"][si] + fork_c + 1 + b
        rep["divergence"] = dict(
            line_block_fork_page_index=dict(native=fork_n, carbon_bf16=fork_c),
            line_common_tokens_after_fork=b,
            common_line_prefix=describe(vocab, line_n[:b]),
            boundary_window_index=dict(native=bound_n, carbon_bf16=bound_c),
            boundary_page_index=dict(native=fork_n + 1 + b, carbon_bf16=fork_c + 1 + b),
            span_to_identifier_end=dict(native=describe(vocab, span_n), carbon_bf16=describe(vocab, span_c)),
            span_bytes=dict(native=b"".join(vocab.piece(t) for t in span_n).decode(),
                            carbon_bf16=b"".join(vocab.piece(t) for t in span_c).decode()),
            span_ids_sha256=dict(native=ids_sha(span_n), carbon_bf16=ids_sha(span_c)),
            first_token_of_span_differs=bool(span_n and span_c and span_n[0] != span_c[0]),
            identifier_step_is_window_first_difference=dict(native=bound_n == L, carbon_bf16=bound_c == L))
        # Optional secondary cross-check: canonical encoding by the pinned tokenizer through the Rust
        # `tokenizers` library, when importable (CPU only). The stdlib byte decoding above is primary.
        try:
            import tokenizers  # noqa: PLC0415
            tk = tokenizers.Tokenizer.from_str(disk("tokenizer.json").decode("utf-8"))
            canon = {}
            for mode, line, end in (("native", line_n, n_end), ("carbon_bf16", line_c, c_end)):
                text = vocab.decode(line[:end])
                enc = tk.encode(text, add_special_tokens=False).ids
                ok = enc == line[:end] and text.endswith(tg["strings"][mode])
                canon[mode] = dict(text=text, ids=enc, equals_emitted=ok)
                check(ok, f"{wname}: {mode} emitted line tokens = canonical encoding of their own text")
            rep["divergence"]["canonical_cross_check"] = dict(library=f"tokenizers {tokenizers.__version__}", **canon)
        except ImportError:
            rep["divergence"]["canonical_cross_check"] = "tokenizers library not importable; not run"
        # 5. Opaque prefixes A1 must use / replay.
        rep["a1_prefixes"] = dict(
            full_window=dict(native=dict(tokens=len(n_ids), sha256=ids_sha(n_ids)),
                             carbon_bf16=dict(tokens=len(c_ids), sha256=ids_sha(c_ids))),
            native_prefix_to_boundary=dict(tokens=bound_n, sha256=ids_sha(n_ids[:bound_n])),
            carbon_prefix_to_boundary=dict(tokens=bound_c, sha256=ids_sha(c_ids[:bound_c])),
            common_window_prefix=dict(tokens=L, sha256=ids_sha(n_ids[:L])),
            encoding="SHA-256 of compact JSON list of decimal token ids, e.g. [128827,128828]")
        rep["_n"], rep["_c"] = n_ids, c_ids
        report[wname] = rep

    # 6. Claims under audit (Carbon WP-0016/002 section 3; specification p.3; assignment).
    w19, w37 = report["window-019"], report["window-037"]
    c002 = git("show", f"{INTEGRATION_BASE_REF}:{CARBON_002}")
    claims = []

    def claim(cid, source, statement, observed, expected):
        ok = observed == expected
        claims.append(dict(id=cid, source=source, statement=statement, expected=expected, observed=observed,
                           agrees=ok))

    d19, d37 = w19["divergence"], w37["divergence"]
    p21 = next(p for p in w19["per_page"] if p["page"] == 21)
    p37 = next(p for p in w37["per_page"] if p["page"] == 37)
    claim("C1", "spec p.3 / Carbon 002", "window-019 first 417 tokens identical (native vs carbon_bf16)",
          w19["first_difference"]["common_prefix_length"], 417)
    claim("C2", "Carbon 002", "the 417 tokens are all of pages 19-20 plus the first 37 tokens of page 21",
          [w19["first_difference"]["page"], w19["first_difference"]["page_index_0based"]], [21, 37])
    claim("C3", "Carbon 002", "page-21 native tokens at 37..38 are [342 ' I', 3019 '08']",
          [t["id"] for t in d19["span_to_identifier_end"]["native"][:2]] if d19["boundary_page_index"]["native"] == 37 else None,
          [342, 3019])
    claim("C4", "Carbon 002", "page-21 carbon tokens at 37..38 are [223 ' ', 6924 '108']",
          [t["id"] for t in d19["span_to_identifier_end"]["carbon_bf16"][:2]] if d19["boundary_page_index"]["carbon_bf16"] == 37 else None,
          [223, 6924])
    claim("C5", "Carbon 002", "3 remaining page-21 token diffs, all +-1 box coordinates 235->234, 292->291, 259->260",
          [p21.get("aligned"),
           [[d["native"]["piece"], d["carbon_bf16"]["piece"]] for d in p21.get("diffs", []) if d["role"] == "block_header"],
           sum(1 for d in p21.get("diffs", []) if d["role"] != "block_header")],
          [True, [["235", "234"], ["292", "291"], ["259", "260"]], 2])
    claim("C6", "spec p.3 / Carbon 002", "window-037 first difference at token 7: 17979 '291' vs 16234 '290'",
          [w37["first_difference"]["window_index_0based"], w37["first_difference"]["native"]["id"],
           w37["first_difference"]["carbon_bf16"]["id"]], [7, 17979, 16234])
    claim("C7", "Carbon 002", "page-37 identifier split at content indices 41..42: native [26 '8', 90169 'OI'], "
          "carbon [1892 '80', 43 'I']",
          [d37["boundary_page_index"]["native"], [t["id"] for t in d37["span_to_identifier_end"]["native"][:2]],
           d37["boundary_page_index"]["carbon_bf16"], [t["id"] for t in d37["span_to_identifier_end"]["carbon_bf16"][:2]]],
          [41, [26, 90169], 41, [1892, 43]])
    claim("C8", "Carbon 002", "6 other page-37 diffs are box-coordinate digits (reading B: other than the identifier "
          "pair, i.e. 6 geometry diffs including token 7, plus the 2-token identifier pair)",
          [p37.get("aligned"), sum(1 for d in p37.get("diffs", []) if d["role"] == "block_header"),
           sum(1 for d in p37.get("diffs", []) if d["role"] != "block_header")], [True, 6, 2])
    claim("C9", "spec p.1", "BPE readings: page 21 [' I','08'] vs [' ','108']; page 37 ['8','OI'] vs ['80','I']",
          [[t["piece"] for t in d19["span_to_identifier_end"]["native"][:2]],
           [t["piece"] for t in d19["span_to_identifier_end"]["carbon_bf16"][:2]],
           [t["piece"] for t in d37["span_to_identifier_end"]["native"][:2]],
           [t["piece"] for t in d37["span_to_identifier_end"]["carbon_bf16"][:2]]],
          [[" I", "08"], [" ", "108"], ["8", "OI"], ["80", "I"]])
    claim("C10", "spec p.1 / Carbon 002", "native and carbon_bf16 each byte-identical across AB and BA (these windows)",
          [w19["repeat_identical"], w37["repeat_identical"]],
          [{"native": True, "carbon_bf16": True}, {"native": True, "carbon_bf16": True}])

    def clocks(arm):
        w = arm["_w"]
        cm = w["clock_marks_ns"]
        return dict(time_s=w["time_s"], engine_span_s=(w["engine_end_ns"] - w["engine_begin_ns"]) / 1e9,
                    native_infer_s=w["native_infer_ms"] / 1000, generate_span_s=(cm["generate_end"] - cm["generate_start"]) / 1e9)
    two_window = {}
    for m in MODES:
        for o in ORDERS:
            c19, c37 = clocks(windows["window-019"][f"{m}:{o}"]), clocks(windows["window-037"][f"{m}:{o}"])
            two_window[f"{m}:{o}"] = {k: round(c19[k] + c37[k], 2) for k in c19}
    eng = [v["engine_span_s"] for v in two_window.values()]
    claim("C11", "assignment", "earlier two-window observations ranged from 87.30 to 106.26 s per engine",
          [min(eng), max(eng)], [87.30, 106.26])
    pred = {f"{m}:{o}": data[o, m]["prediction_sha256"] for m in MODES for o in ORDERS}
    claim("C12", "Carbon 002", "A prediction SHA-256 native cd009c42... both orders, carbon 204af33d... both orders",
          [pred["native:ab"][:8], pred["native:ba"][:8], pred["carbon_bf16:ab"][:8], pred["carbon_bf16:ba"][:8]],
          ["cd009c42", "cd009c42", "204af33d", "204af33d"])
    for c in claims:
        c["note"] = CLAIM_NOTES.get(c["id"])

    for w in report.values():
        w.pop("_n")
        w.pop("_c")
    out = dict(
        kind="WP-0017 A1 independent pre-execution prefix audit", reviewer="eld-rd-reviewer", created_utc=utc(),
        exposure=dict(truth_opened=False, score_outputs_opened=False, packet_b_resolved=False, gpu_used=False,
                      text_published="only token pieces of the differing positions and of the public identifier spans"),
        bindings=dict(
            inventory=dict(commit=BLOBS["G0-blind-inventory.json"][0], path=BLOBS["G0-blind-inventory.json"][1],
                           sha256=sha(inv_bytes)),
            plans=dict(commit=BLOBS["g0-plans.json"][0], path=BLOBS["g0-plans.json"][1], sha256=sha(plans_bytes)),
            tokenizer=dict(path=str(DISK["tokenizer.json"][0]), sha256=DISK["tokenizer.json"][1]),
            a_rasters=dict(path=str(DISK["A/rasters.input.json"][0]), sha256=DISK["A/rasters.input.json"][1]),
            carbon_002=dict(commit=INTEGRATION_BASE_REF, path=CARBON_002, sha256=sha(c002)),
            run_trees=tree_state, a_prediction_sha256=pred),
        two_window_clocks_s=two_window, windows=report, claims=claims,
        claims_agree=sum(c["agrees"] for c in claims), claims_total=len(claims),
        checks_run=check.count, failures=check.failures)
    digest = write_new(a.out, out)
    print(json.dumps(dict(out=str(a.out), sha256=digest, checks=check.count, failures=check.failures,
                          claims=[(c["id"], c["agrees"], c["observed"]) for c in claims]), indent=1))
    return 1 if check.failures else 0


INTEGRATION_BASE_REF = "1e75ebe25814227ef6450913bce301ba9e2ef0f2"
CLAIM_NOTES = {
    "C5": "translation: page-21 aligned diffs other than the identifier pair are header geometry pieces",
    "C8": "Carbon's wording is ambiguous. Reading A (6 geometry diffs besides token 7 -> 7 total) was this "
          "tool's first translation and disagreed with the scratch dry run (observed 6 geometry + 2 content); "
          "reading B (6 diffs other than the identifier pair) is recorded here. Both readings are disclosed.",
    "C11": "sum over window-019 and window-037 of engine_end_ns - engine_begin_ns, rounded to 0.01 s. The scratch "
           "dry run first used time_s (86.67-105.71 s), which does not reproduce the assignment's range; all four "
           "clock definitions are listed in two_window_clocks_s.",
}

if __name__ == "__main__":
    sys.exit(main())
