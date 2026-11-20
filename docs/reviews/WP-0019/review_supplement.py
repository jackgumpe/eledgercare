"""WP-0019 reviewer supplementary checks (post-freeze Addendum 1; eld-rd-reviewer). They add evidence and
never replace a frozen check. Written after reading the frozen PROTOCOL.md/policy.py/run.py/engine.py.

Subcommands
  rebuild   Independently re-derive, from each page's raw full words, detected grids and (B) crop words:
            cell/prose regions, rectangles (inset 4; prose pad 12 x / 8 y; cap 32), eligibility, selection and
            omission reasons; every crop decision; the page-pixel projection; and both arms' complete page
            predictions using the hash-pinned original WP-0015 visual.layout. Compare everything with the author
            records and durable predictions. Optionally re-run the pinned rule_tables on the admitted bitmap.
  timing    Per-run, per-arm, per-family metrics from the candidate's measured boundary (receipt elapsed_ns),
            same-worker/language proof from every recognizer response, execution order, warm-up exclusion,
            run seriality from execute.py receipts, bound output digests.
  control   Current full-pass raw words/boxes versus the pinned current control (8220701 reference-evidence).
No WinRT/OCR, GPU or network. Truth is never read here.
"""
import argparse
import bisect
import gzip
import importlib.util
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_common import Checks, read_json, sha256_bytes, sha256_file, write_new

VISUAL_SHA256 = "93480f58e05760d02b1c4d8a78c488e2eb616fda1b8f2dc70751fb519ea26287"
FORMATS_SHA256 = "b832a7ee452f807a01a4acaa4d63fed927241f73b75fc1a47c7ae830ce28c0a6"
INSET, PAD_X, PAD_Y, CAP = 4, 12, 8, 32
# Frozen vocabulary declared by the protocol ("the complete generic vocabulary is in policy.py").
LABEL_WORDS = {"id", "identifier", "code", "docket", "serial", "tag", "ref", "reference",
               "asset", "batch", "lot", "inspection"}
SEPARATED_ID = re.compile(r"[A-Za-z0-9]{2,}(?:-[A-Za-z0-9]{2,})+")
ALNUM_ONLY = re.compile(r"[A-Za-z0-9]+")


def load_visual(historical_dir):
    d = Path(historical_dir)
    if sha256_file(d / "visual.py") != VISUAL_SHA256 or sha256_file(d / "formats.py") != FORMATS_SHA256:
        raise ValueError("historical layout source mismatch")
    sys.path.insert(0, str(d))
    spec = importlib.util.spec_from_file_location("pinned_visual", d / "visual.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def digit(t):
    return any(c.isdigit() for c in t)


def is_code(t):
    return bool(SEPARATED_ID.fullmatch(t)) and digit(t)


def is_label(t):
    return bool(LABEL_WORDS & set(re.findall(r"[a-z]+", t.lower())))


def pin(box, size, pts):
    return [round(v * pts[i % 2] / size[i % 2], 3) for i, v in enumerate(box)]


def rect_area(r):
    return max(0, r[2] - r[0]) * max(0, r[3] - r[1])


def inter(a, b):
    return [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]


def union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def derive_regions(full, grids, pts, page):
    """Independent implementation of PROTOCOL steps 1-4."""
    size = (full["width"], full["height"])
    W, H = size
    words = {(li, wi): w for li, ln in enumerate(full["lines"]) for wi, w in enumerate(ln["words"])}
    cells, prose = defaultdict(list), defaultdict(list)
    for (li, wi), w in words.items():
        b = pin(w["bbox"], size, pts)
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        owned = False
        for ti, g in enumerate(grids):
            if g["xs"][0] <= cx < g["xs"][-1] and g["ys"][0] <= cy < g["ys"][-1]:
                cells[ti, bisect.bisect_right(g["ys"], cy) - 1, bisect.bisect_right(g["xs"], cx) - 1].append((li, wi))
                owned = True
        if not owned:
            prose[li].append((li, wi))
    out = []
    for ti, g in enumerate(grids):
        xs, ys = g["xs"], g["ys"]
        values = [[" ".join(words[r]["text"] for r in sorted(cells[ti, ri, ci], key=lambda r: (r[0], pin(words[r]["bbox"], size, pts)[0])))
                   for ci in range(len(xs) - 1)] for ri in range(len(ys) - 1)]
        idcol = [is_label(values[0][ci]) or any(digit(row[ci]) and ("-" in row[ci] or any(c.isalpha() for c in row[ci])) for row in values[1:])
                 for ci in range(len(xs) - 1)]
        for ri in range(len(ys) - 1):
            for ci in range(len(xs) - 1):
                px = [xs[ci] * W / pts[0], ys[ri] * H / pts[1], xs[ci + 1] * W / pts[0], ys[ri + 1] * H / pts[1]]
                rect = [max(0, math.ceil(px[0]) + INSET), max(0, math.ceil(px[1]) + INSET),
                        min(W, math.floor(px[2]) - INSET), min(H, math.floor(px[3]) - INSET)]
                v = values[ri][ci]
                reason = "numeric_cell" if digit(v) else ("identifier_column_body" if ri > 0 and idcol[ci] else "no_id_signal")
                refs = sorted(cells[ti, ri, ci], key=lambda r: (r[0], pin(words[r]["bbox"], size, pts)[0]))
                out.append(dict(id=f"page/{page}/table/{ti + 1}/row/{ri + 1}/col/{ci + 1}", kind="cell", rect_px=rect,
                                full_word_refs=[list(r) for r in refs], full_value=v, reason=reason))
    for li in sorted(prose):
        refs = prose[li]
        u = union([words[r]["bbox"] for r in refs])
        rect = [max(0, math.floor(u[0]) - PAD_X), max(0, math.floor(u[1]) - PAD_Y), min(W, math.ceil(u[2]) + PAD_X), min(H, math.ceil(u[3]) + PAD_Y)]
        v = " ".join(words[r]["text"] for r in refs)
        reason = "numeric_line" if digit(v) else ("identifier_label" if is_label(v) else "no_id_signal")
        out.append(dict(id=f"page/{page}/raw_line/{li + 1}", kind="prose", rect_px=rect, full_word_refs=[list(r) for r in refs],
                        full_value=v, reason=reason))
    chosen, used = [], set()
    for r in out:
        r["eligible"] = r["reason"] != "no_id_signal"
        r["selected"] = False
        if not r["eligible"]:
            continue
        refs = {tuple(x) for x in r["full_word_refs"]}
        if rect_area(r["rect_px"]) == 0:
            r["reason"] = "empty_clip"
        elif refs & used or any(2 * rect_area(inter(r["rect_px"], c)) >= min(rect_area(r["rect_px"]), rect_area(c)) for c in chosen):
            r["reason"] = "overlapping_region"
        elif len(chosen) >= CAP:
            r["reason"] = "page_cap"
        else:
            r["selected"] = True
            used |= refs
            chosen.append(r["rect_px"])
    return out


def derive_decision(full_words, crop, kind, rect):
    """Independent implementation of PROTOCOL steps 5-6. Returns (decision, projected, crop_value)."""
    projected = [dict(text=w["text"], bbox=[w["bbox"][0] + rect[0], w["bbox"][1] + rect[1], w["bbox"][2] + rect[0], w["bbox"][3] + rect[1]])
                 for ln in crop["lines"] for w in ln["words"]]
    old, new = [w["text"] for w in full_words], [w["text"] for w in projected]
    value = " ".join(new)
    if old == new:
        d = "keep_agree"
    elif not new:
        d = "keep_empty_read"
    elif len(crop["lines"]) != 1:
        d = "keep_multiline"
    elif not old:
        d = "use_detected_empty_cell_read" if kind == "cell" and len(new) == 1 and is_code(new[0]) else "keep_no_supported_replacement"
    else:
        i = 0
        while i < min(len(old), len(new)) and old[i] == new[i]:
            i += 1
        j = 0
        while j < min(len(old), len(new)) - i and old[len(old) - 1 - j] == new[len(new) - 1 - j]:
            j += 1
        a, b = full_words[i:len(old) - j], new[i:len(new) - j]
        d = "keep_no_supported_replacement"
        if len(b) == 1 and is_code(b[0]) and a and not any(is_code(w["text"]) for w in a):
            if len(a) == 1:
                if ALNUM_ONLY.fullmatch(a[0]["text"]) and a[0]["text"] == b[0].replace("-", ""):
                    d = "use_crop_delimiter"
            else:
                med = statistics.median([w["bbox"][3] - w["bbox"][1] for w in a])
                gaps_ok = all(0 <= nxt["bbox"][0] - cur["bbox"][2] <= 0.35 * med for cur, nxt in zip(a, a[1:]))
                if gaps_ok and "".join(w["text"] for w in a) == b[0]:
                    d = "use_crop_single_word"
    if d.startswith("use_") and full_words:
        ob, nb = union([w["bbox"] for w in full_words]), union([w["bbox"] for w in projected])
        if rect_area(inter(ob, nb)) < 0.5 * max(rect_area(ob), rect_area(nb)):
            d = "keep_location_mismatch"
    return d, projected, value


def rebuild_prediction(visual, full, grids, pts, regions):
    """Independent PROTOCOL step 7 using the pinned original layout."""
    edits, flagged_refs, extra = {}, set(), []
    for r in regions:
        refs = [tuple(x) for x in r["full_word_refs"]]
        if r.get("flagged"):
            flagged_refs.update(refs)
        if str(r.get("decision", "")).startswith("use_"):
            repl = [dict(text=w["text"], bbox=w["bbox"]) for w in r["projected_words"]]
            for ref in refs:
                edits[ref] = []
            if refs:
                edits[refs[0]] = repl
            else:
                extra.append(dict(words=repl))
    lines, flags = [], []
    for li, ln in enumerate(full["lines"]):
        ws = []
        for wi, w in enumerate(ln["words"]):
            rep = edits.get((li, wi), [w])
            ws.extend(rep)
            flags.extend([(li, wi) in flagged_refs] * len(rep))
        lines.append(dict(words=ws))
    for ln in extra:
        flags.extend([False] * len(ln["words"]))
    out = visual.layout(dict(full, lines=lines + extra), grids, pts)
    if len(out["spans"]) != len(flags):
        raise ValueError("span count")
    for s, f in zip(out["spans"], flags):
        s["flagged"] = f
    for r in regions:
        if r["kind"] == "cell" and r.get("flagged"):
            ti, ri, ci = r["grid_index"]
            out["tables"][ti]["rows"][ri][ci] = dict(text=out["tables"][ti]["rows"][ri][ci], flagged=True)
    return out


def cmd_rebuild(args):
    checks = Checks()
    visual = load_visual(args.historical)
    root = Path(args.root)
    stats = {}
    rule_cache = {}
    witnesses = {}
    for run in args.runs:
        folder = root / run
        fam = run.split("-")[0]
        receipt = read_json(folder / "receipt.json")
        mpages = {p["page"]: p for p in read_json(receipt["manifest"])["pages"]}
        st = Counter()
        omitted, selected_ids, decisions = [], [], Counter()
        for arm in ("A", "B"):
            pred = read_json(folder / arm / "prediction.json")
            mismatch_pages = []
            for page_pred in pred["pages"]:
                n = page_pred["page"]
                ev = read_json(folder / arm / f"page-{n:03d}.json")
                full, grids, pts = ev["full"], ev["grids"], ev["bitmap"]["points"]
                if args.rule_tables and (fam, n) not in rule_cache:
                    from PIL import Image
                    with Image.open(mpages[n]["bmp"]) as im:
                        rule_cache[fam, n] = visual.rule_tables(im.convert("RGB"), pts)
                if args.rule_tables:
                    checks.add(f"R0.grids.{run}.{arm}.{n}", rule_cache[fam, n] == grids, "recorded grids equal pinned rule_tables re-run on the admitted bitmap")
                if arm == "A":
                    regions = []
                    checks.add(f"R1.no_regions_A.{run}.{n}", not ev.get("regions"), "full-only arm has no selector/crop records", len(ev.get("regions") or []))
                else:
                    mine = derive_regions(full, grids, pts, n)
                    theirs = ev["regions"]
                    keys = ("id", "kind", "rect_px", "full_word_refs", "full_value", "eligible", "selected", "reason")
                    same = len(mine) == len(theirs) and all(all(m[k] == t[k] for k in keys) for m, t in zip(mine, theirs))
                    checks.add(f"R2.regions.{run}.{n}", same, "independent regions/rects/refs/eligibility/selection/reasons equal author records",
                               None if same else dict(mine=len(mine), theirs=len(theirs),
                                                      first_diff=next(([m, {k: t.get(k) for k in keys}] for m, t in zip(mine, theirs)
                                                                       if any(m[k] != t[k] for k in keys)), None)))
                    regions = []
                    for t in theirs:
                        st["candidates"] += 1
                        st["eligible"] += bool(t["eligible"])
                        st["selected"] += bool(t["selected"])
                        st["reason_" + t["reason"]] += 1
                        if t["eligible"] and not t["selected"]:
                            omitted.append(dict(id=t["id"], reason=t["reason"], full_value=t["full_value"]))
                        if not t["selected"]:
                            ok = t["decision"] == "not_selected" and t["emitted_value"] == t["full_value"] and not t["flagged"] and t["crop"] is None
                            checks.add(f"R3.unselected.{run}.{t['id']}", ok, "unselected region emits its full value unflagged, no crop") if not ok else None
                            st["unselected_ok"] += ok
                            regions.append(t)
                            continue
                        selected_ids.append(t["id"])
                        fw = [full["lines"][li]["words"][wi] for li, wi in t["full_word_refs"]]
                        d, proj, val = derive_decision(fw, t["crop"], t["kind"], t["rect_px"])
                        use = d.startswith("use_")
                        exp = dict(decision=d, projected_words=[dict(text=p["text"], bbox=p["bbox"]) for p in proj], crop_value=val,
                                   disagreement=val != t["full_value"], flagged=(val != t["full_value"]) and not use,
                                   emitted_value=val if use else t["full_value"])
                        got = dict(decision=t["decision"], projected_words=[dict(text=p["text"], bbox=p["bbox"]) for p in t["projected_words"]],
                                   crop_value=t["crop_value"], disagreement=t["disagreement"], flagged=t["flagged"], emitted_value=t["emitted_value"])
                        checks.add(f"R4.decision.{run}.{t['id']}", exp == got, "independent decision, page-px projection, crop/emitted value and flag equal author record",
                                   None if exp == got else dict(mine=exp, theirs=got))
                        decisions[d] += 1
                        st["disagree_" + str(val != t["full_value"])] += 1
                        regions.append(t)
                rebuilt = dict(page=n, source_sha256=pred["source_sha256"], state="complete",
                               **(visual.layout(full, grids, pts) if arm == "A" else rebuild_prediction(visual, full, grids, pts, regions)))
                if rebuilt != page_pred:
                    mismatch_pages.append(n)
            checks.add(f"R5.prediction.{run}.{arm}", not mismatch_pages, "independent rebuild equals every durable prediction page (text/spans/flags/tables)", mismatch_pages)
        stats[run] = dict(regions=dict(st), decisions=dict(decisions), selected=len(selected_ids), omitted_eligible=omitted,
                          selected_ids_sha256=sha256_bytes("\n".join(selected_ids).encode()))
    finish(args.out, "wp0019-review-supplement-rebuild", checks, dict(runs=stats, constants=dict(inset=INSET, pad_x=PAD_X, pad_y=PAD_Y, cap=CAP),
                                                                     rule_tables_rerun=bool(args.rule_tables)))


def cmd_timing(args):
    checks = Checks()
    root = Path(args.root)
    rows, intervals = {}, []
    for run in args.runs:
        folder = root / run
        fam, order = run.split("-")
        rc = read_json(folder / "receipt.json")
        bound = read_json(root / f"{run}.bound.json")
        eng = rc["engine"]
        checks.add(f"P1.order.{run}", list(rc["arms"]) == list(order), "arm execution order (receipt key order) equals the order label", list(rc["arms"]))
        checks.add(f"P2.warmup.{run}", rc["warmup"]["excluded"] is True and rc["warmup"]["page"] == 1 and
                   all(rc["arms"][a]["full_identities"][0] == rc["warmup"]["full_identity"] for a in "AB"),
                   "excluded warm-up on page 1; both arms' page-1 full identity equals it", rc["warmup"])
        pids, langs, calls = Counter(), Counter(), Counter()
        for arm in "AB":
            for p in sorted((folder / arm).glob("page-*.json")):
                ev = read_json(p)
                pids[ev["full"]["pid"]] += 1
                langs[ev["full"]["language"]] += 1
                calls[arm + "_full"] += 1
                for r in ev.get("regions") or []:
                    if r.get("crop"):
                        pids[r["crop"]["pid"]] += 1
                        langs[r["crop"]["language"]] += 1
                        calls[arm + "_crop"] += 1
        checks.add(f"P3.same_worker.{run}", set(pids) == {eng["pid"]} and set(langs) == {"en-US"},
                   "every full and crop response in both arms came from the single warmed worker PID, en-US", dict(pids=dict(pids), langs=dict(langs)))
        checks.add(f"P4.identities.{run}", rc["arms"]["A"]["full_identities"] == rc["arms"]["B"]["full_identities"], "both arms' semantic full identities equal page by page")
        outs = bound.get("outputs", {})
        okd = bound["exit"] == 0 and outs and all(sha256_file(folder / k) == v for k, v in outs.items())
        checks.add(f"P5.bound_outputs.{run}", okd, "execute.py exit 0 and every bound output digest re-verifies", dict(exit=bound["exit"], files=len(outs)))
        checks.add(f"P6.no_crops_A.{run}", rc["arms"]["A"]["crops"] == 0 and calls["A_crop"] == 0, "full-only arm attempted no crop")
        pages = rc["pages"]
        a, b = rc["arms"]["A"], rc["arms"]["B"]
        rows[run] = dict(family=fam, order=order, pages=pages, startup_ms=rc["startup_ns"] / 1e6, warmup_ms=rc["warmup"]["elapsed_ns"] / 1e6,
                         engine_startup_ms=eng.get("startup_ms"), engine_pid=eng["pid"], python_pid=eng["python_pid"],
                         A=dict(seconds=a["elapsed_ns"] / 1e9, pages_per_min=60e9 * pages / a["elapsed_ns"], ms_per_page=a["elapsed_ns"] / 1e6 / pages),
                         B=dict(seconds=b["elapsed_ns"] / 1e9, pages_per_min=60e9 * pages / b["elapsed_ns"], ms_per_page=b["elapsed_ns"] / 1e6 / pages,
                                crops=b["crops"], crops_per_page=b["crops"] / pages, crop_calls_observed=calls["B_crop"]),
                         added_ms_per_page=(b["elapsed_ns"] - a["elapsed_ns"]) / 1e6 / pages, author_added_ms_per_page=rc["added_ms_per_page"],
                         wrapper_seconds=bound["wrapperSeconds"], startUtc=bound["startUtc"], endUtc=bound["endUtc"])
        checks.add(f"P7.arithmetic.{run}", abs(rows[run]["added_ms_per_page"] - rc["added_ms_per_page"]) < 1e-9 and b["crops"] == calls["B_crop"],
                   "receipt added ms/page and crop count reproduce from elapsed_ns and observed calls")
        intervals.append((run, datetime.fromisoformat(bound["startUtc"]), datetime.fromisoformat(bound["endUtc"])))
    over = [[x[0], y[0]] for i, x in enumerate(intervals) for y in intervals[i + 1:] if x[1] < y[2] and y[1] < x[2]]
    checks.add("P8.serial", not over, "the timed runs never overlapped (execute.py UTC receipts)", over)
    pooled = {}
    for scope, sel in (("all", lambda r: True), ("H", lambda r: r["family"] == "H"), ("A", lambda r: r["family"] == "A"),
                       ("AB", lambda r: r["order"] == "AB"), ("BA", lambda r: r["order"] == "BA")):
        rs = [r for r in rows.values() if sel(r)]
        if not rs:
            continue
        pg = sum(r["pages"] for r in rs)
        sa, sb = sum(r["A"]["seconds"] for r in rs), sum(r["B"]["seconds"] for r in rs)
        pooled[scope] = dict(pages=pg, A_seconds=sa, B_seconds=sb, A_pages_per_min=60 * pg / sa, B_pages_per_min=60 * pg / sb,
                             added_ms_per_page=1000 * (sb - sa) / pg, crops_per_page=sum(r["B"]["crops"] for r in rs) / pg)
    finish(args.out, "wp0019-review-supplement-timing", checks,
           dict(runs=rows, pooled=pooled, boundary="run.py arm clock: ready-input page loop + output dir through durable prediction write; "
                "startup, warm-up, module load, receipt and shutdown excluded and reported separately"))


def cmd_control(args):
    checks = Checks()
    root = Path(args.root)
    result = {}
    for fam, path in (kv.split("=", 1) for kv in args.control):
        data = json.loads(gzip.decompress(Path(path).read_bytes()))
        pages = data["pages"] if isinstance(data, dict) and "pages" in data else data
        ctl = {}
        for p in pages:
            r = p.get("raw", p.get("full", p))
            ctl[p.get("page")] = dict(width=r["width"], height=r["height"], text=r["text"],
                                      lines=[dict(text=l["text"], words=[dict(text=w["text"], bbox=[float(v) for v in w["bbox"]]) for w in l["words"]]) for l in r["lines"]],
                                      bgra=r.get("bgra_sha256"))
        for run in [r for r in args.runs if r.startswith(fam + "-")]:
            same = []
            for arm in "AB":
                for pth in sorted((root / run / arm).glob("page-*.json")):
                    ev = read_json(pth)
                    f = ev["full"]
                    cur = dict(width=f["width"], height=f["height"], text=f["text"],
                               lines=[dict(text=l["text"], words=[dict(text=w["text"], bbox=[float(v) for v in w["bbox"]]) for w in l["words"]]) for l in f["lines"]],
                               bgra=f["bgra_sha256"])
                    c = ctl.get(ev["page"])
                    eq = c is not None and all(c[k] == cur[k] for k in ("width", "height", "text", "lines")) and c["bgra"] in (None, cur["bgra"])
                    same.append(eq)
                    if not eq:
                        checks.add(f"C1.control.{run}.{arm}.{ev['page']}", False, "full pass equals pinned current control", None)
            result[run] = dict(pages_compared=len(same), equal=sum(same))
            checks.add(f"C1.control.{run}", bool(same) and all(same), "every full pass in both arms equals the pinned current control raw (text, lines, words, boxes, size, input digest)",
                       result[run])
        result[f"control_{fam}"] = dict(path=path, sha256=sha256_file(path), pages=len(ctl))
    finish(args.out, "wp0019-review-supplement-control", checks, dict(results=result))


def finish(out, kind, checks, extra):
    doc = dict(kind=kind, checks=checks.rows, check_summary=checks.summary(), failed_checks=checks.failed(), **extra)
    sha = write_new(Path(out), doc)
    print(json.dumps(dict(out=str(out), sha256=sha, check_summary=doc["check_summary"], failed=doc["failed_checks"][:20]), indent=1))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rebuild")
    r.add_argument("--root", required=True)
    r.add_argument("--runs", nargs="+", required=True)
    r.add_argument("--historical", required=True, help="docs/research/WP-0015/astra of the candidate (hash-pinned)")
    r.add_argument("--rule-tables", action="store_true")
    r.add_argument("--out", required=True)
    t = sub.add_parser("timing")
    t.add_argument("--root", required=True)
    t.add_argument("--runs", nargs="+", required=True)
    t.add_argument("--out", required=True)
    c = sub.add_parser("control")
    c.add_argument("--root", required=True)
    c.add_argument("--runs", nargs="+", required=True)
    c.add_argument("--control", nargs="+", required=True, help="FAMILY=raw.json.gz")
    c.add_argument("--out", required=True)
    a = p.parse_args()
    dict(rebuild=cmd_rebuild, timing=cmd_timing, control=cmd_control)[a.cmd](a)


if __name__ == "__main__":
    main()
