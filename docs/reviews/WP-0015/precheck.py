"""eld-rd-reviewer CPU precheck for WP-0015. Standard library only; no model, GPU or sealed material.

Imports the frozen custodian scorer (score.py) and the frozen native adapter (formats.native_page)
read-only, and records how they behave on public development truth. Probe predictions are fabricated
here for scorer/adaptor testing ONLY and never enter result tables.
"""
import argparse
import hashlib
import json
import re
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVAL = ROOT / "docs/evaluation/WP-0015"
ASTRA = ROOT / "docs/research/WP-0015/astra"
sys.path[:0] = [str(EVAL), str(ASTRA), str(Path(__file__).resolve().parent)]
import score as frozen  # noqa: E402  frozen custodian scorer
from formats import native_page  # noqa: E402  frozen Astra native adapter (stdlib + ctypes only)
from analyze import diagnostics  # noqa: E402  reviewer-only supplemental checks


def caught(truth, pred):
    d = diagnostics(truth, pred)
    return dict(numeric_surplus_pages=sorted(d["numeric_surplus_by_page"]),
                misplaced=d["numeric_tokens_printed_on_other_pages"],
                better_other_truth=[a["page"] for a in d["pages_better_matching_other_truth"]],
                flagged_entries=d["flagged_entries"])

WARM_PDF = ROOT / "docs/research/WP-0014/eld-latency-author/A.pdf"
WARM_SHA = "25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------- identity checks ----------

def identities():
    out, ok = {}, True
    ver = load(EVAL / "verification.json")["development"]
    for fam in ("short", "dense", "boundary"):
        d = EVAL / "dev" / fam
        got = {n: sha(d / n) for n in ("source.pdf", "truth.json", "rasters.json")}
        man, truth = load(d / "rasters.json"), load(d / "truth.json")
        checks = {
            "pdf_vs_rasters_manifest": got["source.pdf"] == man["pdf_sha256"],
            "truth_vs_rasters_manifest": got["truth.json"] == man["truth_sha256"],
            "truth_binds_pdf": truth["source_sha256"] == got["source.pdf"],
            "matches_custodian_rebuild_record": got == ver[fam]["byte_identical_rebuild"],
            "page_count_agrees": len(man["pages"]) == len(truth["pages"]),
            "all_pages_2550x3301": all((p["width_px"], p["height_px"]) == (2550, 3301) for p in man["pages"]),
        }
        ok &= all(checks.values())
        out[fam] = dict(sha256=got, pages=len(man["pages"]),
                        rgb_sha256=[p["rgb_sha256"] for p in man["pages"]], checks=checks)
    com, sealed = load(EVAL / "commitments.json")["packets"], load(EVAL / "verification.json")["sealed"]
    for fam in ("H", "A", "B"):
        c = com[fam]
        checks = {
            "hex_commitments": all(re.fullmatch("[0-9a-f]{64}", v) for v in c["files"].values()),
            "ciphertexts_match_custody_record": all(
                c["sealed"][s]["sha256"] == sealed[fam][s]["ciphertext_sha256"] for s in ("input", "scoring")),
        }
        ok &= all(checks.values())
        out[fam] = dict(pages=c["pages"], source_pdf_sha256=c["files"]["source.pdf"], checks=checks)
    warm = sha(WARM_PDF)
    out["warmup_A_pdf"] = dict(sha256=warm, matches_prepare_pin=warm == WARM_SHA)
    ok &= warm == WARM_SHA
    return ok, out


# ---------- fabricated probe predictions ----------

def perfect(truth, grid=True):
    pages = []
    for ref in truth["pages"]:
        spans = [dict(text=ln["text"], bbox=ln["bbox"]) for ln in ref["lines"]]
        tables = [dict(bbox=t["bbox"], rows=[[c["text"] for c in r] for r in t["rows"]]) for t in ref["tables"]]
        pages.append(dict(page=ref["page"], source_sha256=truth["source_sha256"], state="complete",
                          text=ref["text"], spans=spans, tables=tables if grid else []))
    return dict(source_sha256=truth["source_sha256"], pages=pages)


def composite(parts, name):
    """Replicate public dev pages to reach a held-out-scale denominator (arithmetic demonstration only).

    parts: [(truth, copies), ...]; the LAST page is always a copy of the first part's page.
    """
    t = dict(family=name, source_sha256=parts[0][0]["source_sha256"], pages=[])
    order = [tr["pages"][0] for tr, n in parts[1:] for _ in range(n)]
    order += [parts[0][0]["pages"][0]] * parts[0][1]
    t["pages"] = [dict(deepcopy(p), page=i + 1) for i, p in enumerate(order)]
    return t


def run(truth, pred, base=None):
    s = frozen.score(truth, pred)
    if base is not None:
        s["comparison"] = frozen.compare(frozen.score(truth, base), s)
    return s


def summary(s):
    c, cmp = s["counts"], s.get("comparison", {})
    return dict(packet_complete=s["packet_complete"], cer=c["cer"], cell_accuracy=c["cell_accuracy"],
                critical_errors=c["critical_errors"], unflagged_critical_errors=c["unflagged_critical_errors"],
                wrong_source=c["wrong_source"], extra_cells=c["extra_cells"],
                faults=sorted({f["issue"] for f in s["faults"]}),
                delta=cmp.get("delta"), inside_quality_budget=cmp.get("inside_quality_budget"),
                unattended_quality_gate=cmp.get("unattended_quality_gate"),
                new_or_changed_critical=len(cmp.get("new_or_changed_critical_errors", [])))


def to999(box, w=612, h=792):
    return [round(v * 999 / (w, h)[i % 2]) for i, v in enumerate(box)]


def block(label, box, body):
    x1, y1, x2, y2 = to999(box)
    return f"<BLOCK>{label}[{x1}, {y1}, {x2}, {y2}]<FORK>{body}"


def union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def native_doc(truth, pages_raw):
    pages = []
    for ref, raw in zip(truth["pages"], pages_raw):
        pages.append(dict(page=ref["page"], source_sha256=truth["source_sha256"], state="complete",
                          **native_page(raw, (ref["width"], ref["height"]))))
    return dict(source_sha256=truth["source_sha256"], pages=pages)


def table_html(rows):
    return "<table>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>"


def probes():
    short, dense, boundary = (load(EVAL / "dev" / f / "truth.json") for f in ("short", "dense", "boundary"))
    res = {}

    # S1. Flag-everything: all critical values wrong but surfaced -> unattended gate alone stays true.
    p = perfect(dense)
    pg = p["pages"][0]
    rows = pg["tables"][0]["rows"]
    ref = dense["pages"][0]
    for ri, r in enumerate(ref["tables"][0]["rows"]):
        for ci, cell in enumerate(r):
            if cell["critical"]:
                rows[ri][ci] = dict(text=cell["text"] + "9", flagged=True)
    for sp, ln in zip(pg["spans"], ref["lines"]):
        if ln["critical"]:
            sp["text"], sp["flagged"] = ln["text"].replace(ln["critical"], ln["critical"] + "9"), True
    res["S1_flag_all_wrong_critical"] = dict(summary(run(dense, p, perfect(dense))), reviewer=caught(dense, p))

    # S2. Page 4 critical values copied onto known-blank page 3 with plausible geometry.
    p = perfect(boundary)
    src = boundary["pages"][3]
    p["pages"][2].update(text="Return tag RT-0O1 Witness recorded 0.19 bar.",
                         spans=[dict(text=ln["text"], bbox=ln["bbox"]) for ln in src["lines"][1:3]])
    res["S2_foreign_critical_on_blank_page"] = dict(summary(run(boundary, p, perfect(boundary))),
                                                    reviewer=caught(boundary, p))

    # Scales: one dense page; 7 dense pages; an A-like denominator (7 dense + 37 short pages,
    # ~8.8k reference chars and 294 cells, close to A's published 8,821 chars / 300 cells).
    scales = {"x1": [(dense, 1)], "x7": [(dense, 7)], "a_like": [(dense, 7), (short, 37)]}
    res["scale_denominators"] = {}
    for tag, parts in scales.items():
        t = composite(parts, "dense-" + tag)
        c = frozen.score(t, perfect(t))["counts"]
        res["scale_denominators"][tag] = dict(pages=len(t["pages"]), reference_chars=c["reference_chars"],
                                              reference_cells=c["reference_cells"])

        # S3. Fabricated off-line critical amount (an unprinted second total).
        p = perfect(t)
        p["pages"][-1]["text"] += "\nNet total USD 57.33"
        p["pages"][-1]["spans"].append(dict(text="Net total USD 57.33", bbox=[375.0, 700.0, 523.0, 711.5]))
        res[f"S3_offline_fabricated_total_{tag}"] = dict(summary(run(t, p, perfect(t))), reviewer=caught(t, p))

        # S4. Duplicated critical row appended to the grid (double-counted amount).
        p = perfect(t)
        rows = p["pages"][-1]["tables"][0]["rows"]
        rows.append(list(rows[-1]))
        p["pages"][-1]["text"] += "\n" + " ".join(rows[-1])
        res[f"S4_appended_duplicate_row_{tag}"] = dict(summary(run(t, p, perfect(t))), reviewer=caught(t, p))

    # S5. Content swap between non-blank pages 1 and 4 with ordinals kept -> category, not just gate.
    p = perfect(boundary)
    a, b = p["pages"][0], p["pages"][3]
    for k in ("text", "spans", "tables"):
        a[k], b[k] = b[k], a[k]
    res["S5_page_content_swap_ordinals_kept"] = dict(summary(run(boundary, p, perfect(boundary))),
                                                     reviewer=caught(boundary, p))

    # N1. Native adapter, one block per printed line -> criticals localize (adapter positive control).
    ref = short["pages"][0]
    raw = "<PAGE>" + "".join(block("text", ln["bbox"], ln["text"]) for ln in ref["lines"])
    res["N1_native_single_line_blocks"] = summary(run(short, native_doc(short, [raw])))

    # N2. Same exact text, but the model groups lines 2-4 into one paragraph block.
    lines = ref["lines"]
    raw = ("<PAGE>" + block("title", lines[0]["bbox"], lines[0]["text"]) +
           block("text", union([ln["bbox"] for ln in lines[1:]]), "\n".join(ln["text"] for ln in lines[1:])))
    s = run(short, native_doc(short, [raw]))
    res["N2_native_multiline_block_exact_text"] = summary(s)
    res["N2_native_multiline_block_exact_text"]["critical_detail"] = [
        dict(expected=c["expected"], correct=c["correct"], observed=c["observed"]) for c in s["pages"][0]["critical"]]

    # N3. Native dense: line blocks + table block with HTML rows -> grid scored by ordinal.
    ref = dense["pages"][0]
    tab = ref["tables"][0]
    grid = [[c["text"] for c in r] for r in tab["rows"]]

    def dense_raw(rows):
        return ("<PAGE>" + "".join(block("text", ln["bbox"], ln["text"]) for ln in ref["lines"][:4]) +
                block("table", tab["bbox"], table_html(rows)) +
                "".join(block("text", ln["bbox"], ln["text"]) for ln in ref["lines"][4:]))
    res["N3_native_table_block"] = summary(run(dense, native_doc(dense, [dense_raw(grid)])))
    res["N3b_native_table_header_omitted"] = summary(run(dense, native_doc(dense, [dense_raw(grid[1:])])))
    # N3c. Every box in the alternative padded-square convention (x compressed by 2550/3301).
    k = 2550 / 3301

    def squeeze(box):
        return [box[0] * k, box[1], box[2] * k, box[3]]
    raw = ("<PAGE>" + "".join(block("text", squeeze(ln["bbox"]), ln["text"]) for ln in ref["lines"][:4]) +
           block("table", squeeze(tab["bbox"]), table_html(grid)) +
           "".join(block("text", squeeze(ln["bbox"]), ln["text"]) for ln in ref["lines"][4:]))
    pred = native_doc(dense, [raw])
    res["N3c_native_boxes_padded_square_x"] = dict(
        table_iou=round(frozen.iou(tab["bbox"], pred["pages"][0]["tables"][0]["bbox"]), 3),
        **summary(run(dense, pred)))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    ok, ids = identities()
    data = dict(reviewer="eld-rd-reviewer", python=sys.version.split()[0], identities_ok=ok,
                identities=ids, probes=probes())
    text = json.dumps(data, indent=2) + "\n"
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("x", encoding="utf-8") as fh:
            fh.write(text)
    print(text, end="")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
