"""WP-0019 reviewer script validation (eld-rd-reviewer). NOT a WP-0019 result and NOT an OCR run.

Uses only (a) the previously exposed WP-0015 archive copies admitted for WP-0018 and (b) constructed
controls built in scratch. Every constructed control is labelled as such. No WinRT, GPU or network.

usage: python -I review_selftest.py --archive-root <wp0018-data/coordinator/inputs> --scorer <score.py> --out <new dir>
"""
import argparse
import copy
import json
import os
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
from review_common import (FAMILY_PINS, WITNESSES, ZERO_WORD_CELLS, Checks, FrozenScorer, overlap_area, project_pinned,
                           read_bmp, read_json, sha256_bytes, sha256_file, slice_bgra, write_bmp24, write_new)

PY = sys.executable


def run(args, expect_ok=True):
    p = subprocess.run([PY, "-I", "-B"] + [str(a) for a in args], capture_output=True, text=True)
    return p


def archive_full(raw_path):
    raw = read_json(raw_path)
    rr = raw["reader_result"]
    return dict(width=rr["width"], height=rr["height"], bgra_sha256=None, pixel_format=None, text=rr["text"],
                lines=[dict(text=l["text"], words=[dict(text=w["text"], bbox=w["bbox"]) for w in l["words"]]) for l in rr["lines"]])


def bundle(name, order, fam_preds, fam_fulls, crops=None, clock0=1_000_000_000):
    """Constructed canonical bundle. fam_preds: {fam: {arm: path}}; crops: {(fam,page): [crop]} for treatment."""
    crops = crops or {}
    arms = ["baseline", "treatment"] if order == "AB" else ["treatment", "baseline"]
    t = clock0 + 10_000
    out_arms = []
    for arm in arms:
        a_start = t
        fams = []
        for fam, preds in fam_preds.items():
            f_start = t
            pages = []
            for num, full in fam_fulls[fam].items():
                p_start = t
                t += 1000
                pages.append(dict(page=num, start_ns=p_start, durable_ns=t, full=full,
                                  crops=(crops.get((fam, num), []) if arm == "treatment" else [])))
                t += 10
            fams.append(dict(family=fam, prediction=str(preds[arm]), start_ns=f_start, end_ns=t, pages=pages))
        out_arms.append(dict(arm=arm, pid=4242, start_ns=a_start, end_ns=t, setup_ns=5, families=fams))
        t += 100
    return dict(schema="wp0019-review-run/1", run=name, order=order, clock="constructed",
                worker=dict(pid=4242, info=dict(language="en-US", note="constructed control"), startup_ns=7),
                warmup=dict(input="constructed", excluded=True, start_ns=clock0, end_ns=clock0 + 5000, pid=4242),
                arms=out_arms)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive-root", required=True)
    ap.add_argument("--scorer", required=True)
    ap.add_argument("--repo-scorer", required=True)
    ap.add_argument("--pdf-H", help="read-only historical H source.pdf for the constructed render control")
    ap.add_argument("--rasters-H", help="H rasters.json pin")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    root = Path(args.archive_root)
    checks = Checks()
    scorer = FrozenScorer(args.scorer)
    checks.add("V1.scorer", FrozenScorer(args.repo_scorer).bytes == scorer.bytes, "archive control scorer bytes equal repository WP-0015 score.py (frozen SHA)", scorer.sha256)

    # V2 denominators and blanks from truth
    truths = {}
    for fam in ("H", "A"):
        tp = root / fam / "truth.json"
        truths[fam] = read_json(tp)
        t = truths[fam]
        cl = sum(1 for p in t["pages"] for l in p["lines"] if l["critical"])
        cc = sum(1 for p in t["pages"] for tb in p["tables"] for r in tb["rows"] for c in r if c["critical"])
        cells = [c for p in t["pages"] for tb in p["tables"] for r in tb["rows"] for c in r]
        pins = FAMILY_PINS[fam]
        obs = dict(sha=sha256_file(tp), critical_lines=cl, critical_cells=cc, cells=len(cells),
                   blanks=sum(c["text"] == "" for c in cells), pages=len(t["pages"]))
        checks.add(f"V2.truth.{fam}", (obs["sha"], cl, cc, len(cells), obs["blanks"], obs["pages"]) ==
                   (pins["truth_sha256"], pins["critical_lines"], pins["critical_cells"], pins["cells"], pins["blanks"], pins["pages"]),
                   "truth digest, critical lines/cells, cells, blanks, pages", obs)

    # V3 archive baseline reproduces historical score byte for byte
    for fam in ("H", "A"):
        o = out / f"archive-score-{fam}.json"
        r = scorer.run(root / fam / "truth.json", root / fam / "windows" / "prediction.json", o)
        hist = read_json(root / fam / "historical-score.json")
        extra_keys = sorted(set(hist) - set(read_json(o))) if r["returncode"] == 0 else None
        hist.pop("comparison", None)  # historical file was scored with --baseline (native arm, not admitted here)
        same = r["returncode"] == 0 and read_json(o) == hist and extra_keys == ["comparison"]
        c = read_json(o)["counts"] if r["returncode"] == 0 else {}
        arch = FAMILY_PINS[fam]["archive"]
        checks.add(f"V3.archive_baseline.{fam}", same and all(c.get(k) == v for k, v in arch.items()),
                   "archive prediction rescored in separate process equals historical-score.json (excluding its native-arm "
                   "'comparison' block) and pinned counts", dict({k: c.get(k) for k in arch}, historical_extra_keys=extra_keys))

    # V4 zero-word cells derived independently from archive raw words
    found = []
    for fam in ("H", "A"):
        hs = read_json(root / fam / "historical-score.json")
        sc = {c["at"]: c for p in hs["pages"] for c in p["cells"]}
        for p in truths[fam]["pages"]:
            raw = read_json(root / fam / "windows" / f"raw-{p['page']:03d}.json")["reader_result"]
            words = [project_pinned(w["bbox"], raw["width"], raw["height"], (p["width"], p["height"])) for l in raw["lines"] for w in l["words"]]
            for ti, tb in enumerate(p["tables"]):
                for ri, row in enumerate(tb["rows"]):
                    for ci, c in enumerate(row):
                        if c["text"] and not any(overlap_area(w, c["bbox"]) > 0 for w in words):
                            at = f"page/{p['page']}/table/{ti + 1}/row/{ri + 1}/col/{ci + 1}"
                            found.append((fam, at, c["critical"], sc[at]["observed"], sc[at]["correct"]))
    checks.add("V4.zero_word_cells", sorted((f, a) for f, a, *_ in found) == sorted(ZERO_WORD_CELLS.values()) and
               sum(1 for x in found if x[2]) == 2 and all(x[3] == "" and not x[4] for x in found),
               "exactly the five preregistered A cells lack any intersecting archive word; 2 critical; all observed '' and wrong", found)

    # V5 pinned projection reproduces every stored archive span
    mism = 0
    total = 0
    for fam in ("H", "A"):
        for p in truths[fam]["pages"]:
            raw = read_json(root / fam / "windows" / f"raw-{p['page']:03d}.json")["reader_result"]
            page = read_json(root / fam / "windows" / f"page-{p['page']:03d}.json")
            words = [w for l in raw["lines"] for w in l["words"]]
            for w, s in zip(words, page["spans"]):
                total += 1
                mism += (project_pinned(w["bbox"], raw["width"], raw["height"], (p["width"], p["height"])) != s["bbox"]) or w["text"] != s["text"]
            mism += len(words) != len(page["spans"])
    checks.add("V5.projection", mism == 0 and total > 0, "pinned round-3 projection equals every archive span", dict(spans=total, mismatches=mism))

    # V6 self-join (archive as both arms, no crops): zero transitions, gate must not pass
    fulls = {fam: {p["page"]: archive_full(root / fam / "windows" / f"raw-{p['page']:03d}.json") for p in truths[fam]["pages"]} for fam in ("H", "A")}
    preds = {fam: {"baseline": root / fam / "windows" / "prediction.json", "treatment": root / fam / "windows" / "prediction.json"} for fam in ("H", "A")}
    b_ab = out / "ctl-self-AB.json"
    b_ba = out / "ctl-self-BA.json"
    write_new(b_ab, bundle("self-AB", "AB", preds, fulls))
    write_new(b_ba, bundle("self-BA", "BA", preds, fulls))
    so = out / "score-self"
    p = run([HERE / "review_score.py", "score", "--scorer", args.scorer, "--truth", f"H={root / 'H/truth.json'}", "--truth", f"A={root / 'A/truth.json'}",
             "--archive-score", f"H={root / 'H/historical-score.json'}", "--archive-score", f"A={root / 'A/historical-score.json'}",
             "--run", f"self-AB={b_ab}", "--run", f"self-BA={b_ba}", "--out", so])
    ok = p.returncode == 0
    res = read_json(so / "stage1-score.json") if ok else {}
    if ok:
        sH, sA = res["runs"]["self-AB"]["families"]["H"]["summary"], res["runs"]["self-AB"]["families"]["A"]["summary"]
        ind = {**res["runs"]["self-AB"]["families"]["H"]["individual"], **res["runs"]["self-AB"]["families"]["A"]["individual"]}
        expect_wrong = {"W1": False, "W2": False, "W3": False, "W4": True, "Z1": False, "Z2": False, "Z3": False, "Z4": False, "Z5": False}
        ind_ok = all(ind[k]["base"]["ok"] == v and ind[k]["selected"] is False and ind[k]["transition"] == ("RR" if v else "WW") for k, v in expect_wrong.items())
        cond = (sH["criticals"], sA["criticals"], sH["WR"] + sH["RW"] + sA["WR"] + sA["RW"], sH["base_unflagged_wrong"], sA["base_unflagged_wrong"]) == (19, 252, 0, 8, 94)
        checks.add("V6.self_join", cond and ind_ok and res["gate"]["score_component"] == "FAIL_QUALITY" and res["reproducibility"]["H"]["identical"]
                   and res["runs"]["self-AB"]["families"]["A"]["baseline_vs_archive"]["equal_counts"] and not res["failed_checks"],
                   "archive vs itself: 19/252 criticals, 8/94 unflagged wrong, zero transitions, witnesses/zero-word individually traced, gate FAIL_QUALITY",
                   dict(H=sH["all_positions"], A=sA["all_positions"], gate=res["gate"]["score_component"], failed=res["failed_checks"]))
    else:
        checks.add("V6.self_join", False, "review_score ran", p.stderr[-2000:])

    # V7 constructed H treatment with known transitions + one constructed crop
    hpred = read_json(root / "H/windows/prediction.json")
    t = copy.deepcopy(hpred)
    tH = truths["H"]
    p2 = t["pages"][1]
    rows = p2["tables"][0]["rows"]
    ref_rows = tH["pages"][1]["tables"][0]["rows"]
    w1_value = ref_rows[1][0]["text"]  # read from truth, never a literal (static scan stays clean)
    rows[1][0] = w1_value                                             # W1 wrong -> right
    rows[1][1] = rows[1][1].replace("1", "l", 1)                       # right critical -> wrong
    rows[2][3] = "x"                                                   # blank -> text
    rows[3][0] = dict(text=rows[3][0], flagged=True)                   # wrong critical stays wrong, now flagged
    rows[1][2] = rows[1][2].replace(" ", "")                           # legitimate space removed (non-critical)
    p1 = t["pages"][0]
    sp = p1["spans"]
    i88 = next(i for i, s in enumerate(sp) if s["text"] == "88L1")
    merged = dict(text=sp[i88]["text"] + sp[i88 + 1]["text"], bbox=[sp[i88]["bbox"][0], sp[i88]["bbox"][1], sp[i88 + 1]["bbox"][2], sp[i88 + 1]["bbox"][3]], flagged=False)
    p1["spans"] = sp[:i88] + [merged] + sp[i88 + 2:]                   # W3 split token merged -> right
    tp = out / "ctl-H-treatment.json"
    write_new(tp, t)
    cell = ref_rows[1][0]["bbox"]
    W, Hh = 2550, 3301
    rect = [int(cell[0] * W / 612) + 4, int(cell[1] * Hh / 792) + 4, int(cell[2] * W / 612) - 4, int(cell[3] * Hh / 792) - 4]
    crop = dict(id="ctl-w1", rect=rect, kind="cell", region="t0r1c0", decision="constructed", width=rect[2] - rect[0], height=rect[3] - rect[1],
                lines=[dict(text=w1_value, words=[dict(text=w1_value, bbox=[20, 30, 240, 70])])])
    preds_c = {"H": {"baseline": root / "H/windows/prediction.json", "treatment": tp}, "A": preds["A"]}
    ca, cb = out / "ctl-mixed-AB.json", out / "ctl-mixed-BA.json"
    write_new(ca, bundle("ctl-AB", "AB", preds_c, fulls, crops={("H", 2): [crop]}))
    write_new(cb, bundle("ctl-BA", "BA", preds_c, fulls, crops={("H", 2): [crop]}))
    so = out / "score-mixed"
    p = run([HERE / "review_score.py", "score", "--scorer", args.scorer, "--truth", f"H={root / 'H/truth.json'}", "--truth", f"A={root / 'A/truth.json'}",
             "--run", f"ctl-AB={ca}", "--run", f"ctl-BA={cb}", "--out", so])
    if p.returncode == 0:
        res = read_json(so / "stage1-score.json")
        s = res["runs"]["ctl-AB"]["families"]["H"]["summary"]
        ind = res["runs"]["ctl-AB"]["families"]["H"]["individual"]
        want = dict(WR=2, RW=1, flag01=1, newly_unflagged=1, blanks_lost=1, space_removed=2, space_removed_RW=1, merge=1, covered=1,
                    disagree=1, decision="took_crop", W1="WR", W3="WR", W4="RR", gate="FAIL_QUALITY")
        got = dict(WR=s["WR"], RW=s["RW"], flag01=s["flag_transitions"].get("01", 0), newly_unflagged=s["newly_unflagged"],
                   blanks_lost=s["blanks"]["lost_to_text"], space_removed=s["legitimate_space"]["space_removed"],
                   space_removed_RW=s["legitimate_space"]["space_removed_RW"],
                   merge=s["legitimate_space"]["critical_merge_recoveries"], covered=s["coverage"]["critical_covered"],
                   disagree=s["disagreements"]["critical"], decision=next((r for r in read_json(so / "joins/ctl-AB/H-rows.json") if r["at"] == WITNESSES["W1"][1]))["inferred_decision"],
                   W1=ind["W1"]["transition"], W3=ind["W3"]["transition"], W4=ind["W4"]["transition"], gate=res["gate"]["score_component"])
        checks.add("V7.constructed_transitions", got == want and s["frozen_compare_consistent"],
                   "constructed control: 2 recoveries, 1 harm (newly unflagged), 1 flag-only, 1 blank loss, 1 space loss, 1 merge, crop coverage/diagnostic/decision", dict(want=want, got=got))
    else:
        checks.add("V7.constructed_transitions", False, "review_score ran", p.stderr[-2000:])

    # V8 positive gate path: only W1 recovered, identical AB/BA -> PASS; changed BA -> FAIL_NOT_REPRODUCIBLE
    t2 = copy.deepcopy(hpred)
    t2["pages"][1]["tables"][0]["rows"][1][0] = w1_value
    tp2 = out / "ctl-H-recover-only.json"
    write_new(tp2, t2)
    t3 = copy.deepcopy(t2)
    t3["pages"][1]["tables"][0]["rows"][4][2] = "Outlet  seat!"
    tp3 = out / "ctl-H-recover-variant.json"
    write_new(tp3, t3)
    for label, ba_pred, want in (("pass", tp2, "PASS"), ("unrepro", tp3, "FAIL_NOT_REPRODUCIBLE")):
        pa = {"H": {"baseline": root / "H/windows/prediction.json", "treatment": tp2}, "A": preds["A"]}
        pb = {"H": {"baseline": root / "H/windows/prediction.json", "treatment": ba_pred}, "A": preds["A"]}
        xa, xb = out / f"ctl-{label}-AB.json", out / f"ctl-{label}-BA.json"
        write_new(xa, bundle(f"{label}-AB", "AB", pa, fulls))
        write_new(xb, bundle(f"{label}-BA", "BA", pb, fulls))
        so = out / f"score-{label}"
        p = run([HERE / "review_score.py", "score", "--scorer", args.scorer, "--truth", f"H={root / 'H/truth.json'}", "--truth", f"A={root / 'A/truth.json'}",
                 "--run", f"{label}-AB={xa}", "--run", f"{label}-BA={xb}", "--require-runs", f"{label}-AB", f"{label}-BA", "--out", so])
        g = read_json(so / "stage1-score.json")["gate"]["score_component"] if p.returncode == 0 else p.stderr[-800:]
        checks.add(f"V8.gate_{label}", g == want, f"gate returns {want}", g)

    # V9 BMP parser and slicing (constructed images)
    rnd = random.Random(19)
    w, h = 37, 23
    bgra = bytearray(rnd.randrange(256) for _ in range(w * h * 4))
    bgra[3::4] = b"\xff" * (w * h)
    bgra = bytes(bgra)
    ok = True
    for td in (False, True):
        ok &= read_bmp(write_bmp24(w, h, bgra, top_down=td))["bgra"] == bgra
    from PIL import Image
    import numpy as np
    arr = np.frombuffer(bgra, dtype=np.uint8).reshape(h, w, 4)
    img = Image.fromarray(arr[:, :, [2, 1, 0]].copy(), "RGB")
    pb = out / "ctl-pillow.bmp"
    img.save(pb)
    ok &= read_bmp(pb)["bgra"] == bgra
    rect = [3, 2, 30, 20]
    ok &= slice_bgra(bgra, w, h, rect) == arr[2:20, 3:30, :].tobytes()
    try:
        slice_bgra(bgra, w, h, [0, 0, w + 1, h])
        ok = False
    except ValueError:
        pass
    checks.add("V9.bmp_slice", ok, "own BMP parser equals constructed BGRA (24-bit bottom-up/top-down, Pillow BMP); half-open slice equals numpy; out-of-page refused")

    # V10 geometry/identity/timing checks on a constructed synthetic page (not H/A)
    gdir = out / "geom"
    gdir.mkdir()
    W2, H2 = 120, 90
    pix = bytearray(rnd.randrange(256) for _ in range(W2 * H2 * 4))
    pix[3::4] = b"\xff" * (W2 * H2)
    pix = bytes(pix)
    bmp_path = gdir / "page-001.bmp"
    bmp_path.write_bytes(write_bmp24(W2, H2, pix))
    page_sha = sha256_bytes(pix)
    man = dict(family="H", source_sha256="constructed", pages=[dict(page=1, bmp=str(bmp_path), width=W2, height=H2, points=[612.0, 792.0],
                                                                    rgb_sha256="constructed", bgra_sha256=page_sha)])
    write_new(gdir / "manifest.json", man)
    full = dict(width=W2, height=H2, bgra_sha256=page_sha, pixel_format="Bgra8", text="a", lines=[dict(text="a", words=[dict(text="a", bbox=[10, 10, 20, 20])])])
    good = [10, 10, 50, 40]
    goodsha = sha256_bytes(slice_bgra(pix, W2, H2, good))
    words = [dict(text="z", bbox=[1, 1, 5, 5])]
    proj = [dict(text="z", bbox=project_pinned([11, 11, 15, 15], W2, H2, (612.0, 792.0)))]
    crops = [dict(id="ok", rect=good, kind="cell", width=40, height=30, source_rect_sha256=goodsha, bgra_sha256=goodsha, full_sha256=page_sha,
                  pixel_format="Bgra8", lines=[dict(text="z", words=words)], projected_words=proj),
             dict(id="bad", rect=good, kind="cell", width=40, height=30, source_rect_sha256="0" * 64, full_sha256=page_sha,
                  pixel_format="Bgra8", lines=[], projected_words=[])]
    full_t = copy.deepcopy(full)
    full_t["lines"][0]["words"][0]["bbox"] = [10, 10, 21, 20]
    gb = dict(schema="wp0019-review-run/1", run="geo-AB", order="AB", clock="constructed",
              worker=dict(pid=1, info=dict(language="en-US"), startup_ns=1), warmup=dict(input="c", excluded=True, start_ns=0, end_ns=5, pid=1),
              arms=[dict(arm="baseline", pid=1, start_ns=10, end_ns=20, families=[dict(family="H", prediction="x", start_ns=10, end_ns=20,
                    pages=[dict(page=1, start_ns=11, durable_ns=19, full=full, crops=[])])]),
                    dict(arm="treatment", pid=1, start_ns=30, end_ns=50, families=[dict(family="H", prediction="x", start_ns=30, end_ns=50,
                    pages=[dict(page=1, start_ns=31, durable_ns=49, full=full_t, crops=crops)])])])
    gpath = gdir / "bundle.json"
    write_new(gpath, gb)
    am = dict(family="A", source_sha256="constructed", pages=[])
    write_new(gdir / "manifest-A.json", am)
    p = run([HERE / "review_checks.py", "geometry", "--manifest", f"H={gdir / 'manifest.json'}", "--manifest", f"A={gdir / 'manifest-A.json'}",
             "--run", f"geo-AB={gpath}", "--out", gdir / "geometry.json"])
    gres = read_json(gdir / "geometry.json") if p.returncode == 0 else {}
    checks.add("V10.geometry", gres.get("failed_checks") == ["G3.crop.geo-AB.H.1.1"] and gres.get("projection_modes") == {"pinned": 1},
               "constructed: good crop passes, wrong source-rect hash fails, pinned projection detected", gres.get("failed_checks") or p.stderr[-1500:])
    p = run([HERE / "review_checks.py", "identity", "--manifest", f"H={gdir / 'manifest.json'}", "--manifest", f"A={gdir / 'manifest-A.json'}",
             "--run", f"geo-AB={gpath}", "--out", gdir / "identity.json"])
    ires = read_json(gdir / "identity.json") if p.returncode == 0 else {}
    checks.add("V11.identity", ires.get("failed_checks") == ["I1.arms_equal.geo-AB.H.1"],
               "constructed: one-box full-pass difference between arms is detected", ires.get("failed_checks") or p.stderr[-1500:])
    gb2 = copy.deepcopy(gb)
    gb2["order"] = "BA"
    gb2["run"] = "geo-BA"
    g2 = gdir / "bundle-mislabel.json"
    write_new(g2, gb2)
    p = run([HERE / "review_checks.py", "timing", "--run", f"geo-AB={gpath}", "--run", f"geo-BA={g2}", "--out", gdir / "timing.json"])
    tres = read_json(gdir / "timing.json") if p.returncode == 0 else {}
    want_fail = {"T1.order.geo-BA", "T6.same_pages.geo-AB.H", "T6.same_pages.geo-BA.H", "T7.baseline_no_crops.geo-AB"} - {"T7.baseline_no_crops.geo-AB"}
    checks.add("V12.timing", set(tres.get("failed_checks", [])) == want_fail | {"T8.runs_serial"} and
               tres["metrics"]["geo-AB"]["arms"]["treatment"]["pages_per_min"] == 60 * 1 / (20 / 1e9),
               "constructed: mislabeled order, incomplete page set and overlapping runs detected; pages/min arithmetic", tres.get("failed_checks") or p.stderr[-1500:])

    # V13 audit wrapper (constructed scripts)
    adir = out / "audit"
    adir.mkdir()
    denied = adir / "denied"
    denied.mkdir()
    (denied / "secret.json").write_text("{}")
    (adir / "ok.txt").write_text("ok")
    script = adir / "probe.py"
    script.write_text("import subprocess, sys\nopen(sys.argv[1]).read()\nsubprocess.run([sys.executable, '-I', '-c', 'pass'], check=True)\n"
                      "try:\n    open(sys.argv[2]).read()\n    print('READ')\nexcept PermissionError:\n    print('DENIED')\n")
    log = adir / "log.json"
    p = run([HERE / "review_audit.py", "--log", log, "--deny", denied, "--", script, adir / "ok.txt", denied / "secret.json"])
    alog = read_json(log) if log.exists() else {}
    q = run([HERE / "review_checks.py", "audit", "--log", f"probe={log}", "--allow-exe", "python.exe", "--out", adir / "audit-summary.json"])
    asum = read_json(adir / "audit-summary.json") if q.returncode == 0 else {}
    checks.add("V13.audit", p.stdout.strip() == "DENIED" and len(alog.get("violations", [])) == 1 and
               any(e.get("path", "").endswith("ok.txt") for e in alog.get("events", [])) and
               asum.get("failed_checks") == ["A1.no_denied_reads.probe"] and asum["logs"]["probe"]["executables"] == ["python.exe"],
               "audit hook records allowed opens, the launched executable, and denies/records reads below a deny prefix; summarizer flags only the denial",
               dict(stdout=p.stdout.strip(), violations=alog.get("violations"), summary_failed=asum.get("failed_checks"),
                    exes=asum.get("logs", {}).get("probe", {}).get("executables"), stderr=(p.stderr + q.stderr)[-800:]))

    # V14 static scan: reviewer code is clean; a constructed file with a reference token is caught
    sdir = out / "static-ctl"
    sdir.mkdir()
    token = next(l["critical"] for p_ in truths["A"]["pages"] for l in p_["lines"] if l["critical"] and len(l["critical"]) >= 6)
    (sdir / "leak.py").write_text(f"X = '{token}'\n")
    p = run([HERE / "review_checks.py", "static", "--source", sdir, "--truth-H", root / "H/truth.json", "--truth-A", root / "A/truth.json", "--out", out / "static-ctl.json"])
    s1 = read_json(out / "static-ctl.json") if p.returncode == 0 else {}
    p = run([HERE / "review_checks.py", "static", "--source", HERE, "--truth-H", root / "H/truth.json", "--truth-A", root / "A/truth.json", "--out", out / "static-self.json"])
    s2 = read_json(out / "static-self.json") if p.returncode == 0 else {}
    checks.add("V14.static", s1.get("failed_checks") == ["K1.no_reference_tokens_in_code"] and s2.get("failed_checks") == [],
               "constructed leak detected; reviewer code contains no reference token", dict(ctl=s1.get("failed_checks"), self=s2.get("failed_checks")))

    # V15 constructed H input manifest: reviewer's own 300-DPI render saved as Pillow BMP, then the inputs check
    if args.pdf_H and args.rasters_H:
        from review_common import render_rgb_pages
        idir = out / "inputs-ctl" / "H"
        idir.mkdir(parents=True)
        pages = []
        for r in render_rgb_pages(Path(args.pdf_H).read_bytes()):
            img = Image.frombytes("RGB", (r["width"], r["height"]), r["rgb"])
            bp = idir / f"page-{r['page']:03d}.bmp"
            img.save(bp, format="BMP")
            img.close()
            parsed = read_bmp(bp)
            pages.append(dict(page=r["page"], bmp=str(bp), width=r["width"], height=r["height"], points=r["points"],
                              rgb_sha256=sha256_bytes(r["rgb"]), bgra_sha256=sha256_bytes(parsed["bgra"])))
        write_new(idir / "manifest.json", dict(family="H", source_sha256=FAMILY_PINS["H"]["source_sha256"], pages=pages))
        p = run([HERE / "review_checks.py", "inputs", "--families", "H", "--manifest-H", idir / "manifest.json", "--pdf-H", args.pdf_H,
                 "--rasters-H", args.rasters_H, "--copy-to", out / "inputs-ctl-copy", "--out", out / "inputs-ctl.json"])
        ires = read_json(out / "inputs-ctl.json") if p.returncode == 0 else {}
        checks.add("V15.inputs_render", ires.get("failed_checks") == [] and ires.get("check_summary", {}).get("PASS") == 13,
                   "constructed H manifest: independent render equals rasters.json pins; own BMP parser equals Pillow BMP; copies identical",
                   dict(summary=ires.get("check_summary"), failed=ires.get("failed_checks"), stderr=p.stderr[-800:],
                        bgra_sha256=[pg["bgra_sha256"] for pg in pages]))
        # V16 Stage-2 code path on a constructed "fresh" family F1 (H content relabelled; not a fresh family)
        pins_path = out / "ctl-pins.json"
        write_new(pins_path, {"F1": dict(truth_sha256=FAMILY_PINS["H"]["truth_sha256"], source_sha256=FAMILY_PINS["H"]["source_sha256"],
                                         pages=4, criticals=19, cells=20, lines=16)})
        com_path = out / "ctl-commitments.json"
        write_new(com_path, {"F1": dict(source_sha256=FAMILY_PINS["H"]["source_sha256"],
                                        pages=[dict(page=pg["page"], bgra_sha256=pg["bgra_sha256"], rgb_sha256=pg["rgb_sha256"]) for pg in pages])})
        fman = out / "ctl-F1-manifest.json"
        write_new(fman, dict(family="F1", source_sha256=FAMILY_PINS["H"]["source_sha256"], pages=pages))
        p = run([HERE / "review_checks.py", "inputs-fresh", "--manifest", f"F1={fman}", "--pdf", f"F1={args.pdf_H}",
                 "--commitments", com_path, "--pins", pins_path, "--out", out / "inputs-fresh-ctl.json"])
        fres = read_json(out / "inputs-fresh-ctl.json") if p.returncode == 0 else {}
        t4 = copy.deepcopy(t2)
        t4["pages"][1]["tables"][0]["rows"][2][3] = "x"   # W1 recovered and one correct blank lost
        tp4 = out / "ctl-H-recover-blank-lost.json"
        write_new(tp4, t4)
        fulls_f = {"F1": fulls["H"]}
        verdicts = {}
        for stage in ("1", "2"):
            for label, pred in (("ok", tp2), ("blank", tp4)):
                pf = {"F1": {"baseline": root / "H/windows/prediction.json", "treatment": pred}}
                xa, xb = out / f"ctl-s{stage}-{label}-AB.json", out / f"ctl-s{stage}-{label}-BA.json"
                write_new(xa, bundle(f"s{stage}{label}-AB", "AB", pf, fulls_f))
                write_new(xb, bundle(f"s{stage}{label}-BA", "BA", pf, fulls_f))
                so = out / f"score-s{stage}-{label}"
                q = run([HERE / "review_score.py", "score", "--scorer", args.scorer, "--truth", f"F1={root / 'H/truth.json'}", "--pins", pins_path,
                         "--stage", stage, "--run", f"s{stage}{label}-AB={xa}", "--run", f"s{stage}{label}-BA={xb}", "--out", so])
                verdicts[f"s{stage}-{label}"] = read_json(so / "stage1-score.json")["gate"]["score_component"] if q.returncode == 0 else q.stderr[-600:]
        want = {"s1-ok": "PASS", "s1-blank": "PASS", "s2-ok": "PASS", "s2-blank": "FAIL_QUALITY"}
        checks.add("V16.stage2_paths", verdicts == want and fres.get("failed_checks") == [],
                   "constructed fresh-family pins/commitments: inputs-fresh passes; a lost blank fails Stage 2 but not Stage 1",
                   dict(verdicts=verdicts, inputs_fresh=fres.get("check_summary"), stderr=p.stderr[-600:]))
    else:
        checks.add("V15.inputs_render", None, "constructed H render/BMP control (requires --pdf-H/--rasters-H)")
        checks.add("V16.stage2_paths", None, "requires --pdf-H/--rasters-H")

    sources ={p.name: sha256_file(p) for p in sorted(HERE.iterdir()) if p.is_file()}
    sha = write_new(out / "selftest.json", dict(kind="wp0019-review-selftest", note="script validation on archive and constructed controls only; not a WP-0019 result",
                                                 sources_sha256=sources, python=sys.version, executable=sys.executable,
                                                 checks=checks.rows, check_summary=checks.summary(), failed_checks=checks.failed()))
    print(json.dumps(dict(out=str(out / "selftest.json"), sha256=sha, summary=checks.summary(), failed=checks.failed()), indent=1))


if __name__ == "__main__":
    main()
