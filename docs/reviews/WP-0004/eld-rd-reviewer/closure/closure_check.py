#!/usr/bin/env python3
"""WP-0004 / 009 eld-rd-reviewer closure checks (reviewer-authored, CPU-only, dev fixtures only).

Run from the review worktree root after the normal merge of f69c9e4. Uses only the qualified
three-wheel environment. No OCR/model/GPU; no eval_holdout fixture is opened.
  A. Git mode/blob invariance across base, candidate, author publication and the review merge.
  B. pypdfium2 render sizing source (installed files == verified wheel members) and c_float/binary64 arithmetic.
  C. Frozen input contract: PDFium render of the eight dev controls (F01/F02/F04/F07 p1, v1+v2),
     sizes, RGB-buffer SHA-256, stored-XObject vs rendered distinction; comparison with author evidence.
  D. Corrected E2 algorithm, implemented by the reviewer from the card text, applied to I_in.
  E. RV-04: AST definitions / JSON keys vs the /008 errata and triage; RV-03 README statements.
"""
from __future__ import annotations

import ast, ctypes, hashlib, json, math, pathlib, re, subprocess, sys, zipfile, zlib

import pypdfium2 as pdfium
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "helpers"))
from rd005_verify import MiniPdf  # reviewer-owned /005 parser  # noqa: E402

PINS = {"author_base": "068f3f83bb532160b56e00f071f8badd8d3f51b0", "corpus": "29b2000265ae6068d9c86818622c81a40cadd961",
        "candidate": "54c7f6fe062720cbdf92e6bcd7476b697fc4afe1", "evidence": "fb2d8e616ad375ac7ccfa5f9000ba3340476c148",
        "author_report": "f69c9e4fdec2e12f481e6131965b5e4e184e013f", "review_base": "8f9a3281fa223d25447677b8ed8b873bf9e5cd01"}
OUT: dict = {"tool": "docs/reviews/WP-0004/eld-rd-reviewer/closure/closure_check.py", "pins": PINS}
FAIL: list[str] = []


def git(*a: str) -> str:
    return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout


def tree(rev: str) -> dict:
    out = {}
    for ln in git("ls-tree", "-r", rev).splitlines():
        meta, path = ln.split("\t", 1)
        mode, _, oid = meta.split()
        out[path] = (mode, oid)
    return out


def diff(a: dict, b: dict) -> dict:
    return {"added": sorted(set(b) - set(a)), "deleted": sorted(set(a) - set(b)),
            "modified": sorted(p for p in set(a) & set(b) if a[p] != b[p])}


def need(cond: bool, msg: str) -> None:
    if not cond:
        FAIL.append(msg)


# ---------------- A. git invariance ----------------
head = git("rev-parse", "HEAD").strip()
T = {k: tree(v) for k, v in PINS.items()}
T["merge"] = tree(head)
A = {"merge_head": head, "merge_parents": git("log", "-1", "--format=%P", head).split(),
     "author_base_to_candidate": diff(T["author_base"], T["candidate"]),
     "candidate_to_author_report": diff(T["candidate"], T["author_report"]),
     "review_base_to_merge": diff(T["review_base"], T["merge"]),
     "author_report_to_merge": diff(T["author_report"], T["merge"])}
need(A["author_base_to_candidate"] == {"added": ["research/carbon/reconciliation/03-review-response.md", "research/carbon/reconciliation/verify_review_corrections.py"],
     "deleted": [], "modified": ["evaluation/README.md", "research/carbon/reconciliation/02-ranked-experiment-backlog.md"]}, "candidate path scope")
need(A["candidate_to_author_report"] == {"added": ["docs/agent-reports/eld-rd-carbon/WP-0004/008_2026-11-15_research_eld-rd-carbon.md",
     "evaluation/manifests/review-correction-verification.json"], "deleted": [], "modified": []}, "evidence/report scope")
need(set(A["review_base_to_merge"]["added"]) == set(A["author_base_to_candidate"]["added"] + A["candidate_to_author_report"]["added"])
     and set(A["review_base_to_merge"]["modified"]) == set(A["author_base_to_candidate"]["modified"]) and not A["review_base_to_merge"]["deleted"], "merge brings exactly author delta")
need(not A["author_report_to_merge"]["modified"] and not A["author_report_to_merge"]["deleted"]
     and all(p.startswith(("docs/reviews/WP-0004/eld-rd-reviewer/", "docs/agent-reports/eld-rd-reviewer/")) for p in A["author_report_to_merge"]["added"]), "merge adds only review paths to author publication")
prefixes = ("evaluation/synthetic/", "evaluation/generation/", "evaluation/manifests/corpus-manifest.json", "evaluation/manifests/public-candidates.json",
            "evaluation/manifests/tooling-provenance.json", "evaluation/manifests/provenance-correction-verification.json",
            "evaluation/manifests/recovery-verification/", "docs/agent-reports/eld-rd-carbon/WP-0004/00", "research/carbon/0", "research/carbon/README.md",
            "research/carbon/reconciliation/01-exchange-disposition.md", "research/carbon/reconciliation/README.md", ".gitattributes")
protected = sorted(p for p in T["corpus"] if p.startswith(prefixes))
changed = [p for p in protected if T["merge"].get(p) != T["corpus"][p]]
need(changed == [], f"protected objects changed: {changed}")
rev_paths = [p for p in T["review_base"] if p.startswith(("docs/reviews/WP-0004/eld-rd-reviewer/", "docs/agent-reports/eld-rd-reviewer/"))]
need(all(T["merge"].get(p) == T["review_base"][p] for p in rev_paths), "/005 review objects preserved")
A.update({"protected_objects_checked_vs_29b2000": len(protected), "protected_changed": changed,
          "protected_groups": {"pdfs": sum(p.endswith(".pdf") for p in protected), "expected": sum("/expected/" in p for p in protected),
                               "sources": sum("/sources/" in p for p in protected), "generation": sum("/generation/" in p for p in protected)},
          "review_005_objects_preserved": len(rev_paths)})
OUT["A_git"] = A

# ---------------- B. renderer sizing source ----------------
site = pathlib.Path(pdfium.__file__).resolve().parent.parent
whl = pathlib.Path(".scratch/wheels/pypdfium2-5.15.2-py3-none-win_amd64.whl")
wh = hashlib.sha256(whl.read_bytes()).hexdigest()
z = zipfile.ZipFile(whl)
src_eq = {}
for member in ("pypdfium2/_helpers/page.py", "pypdfium2_raw/bindings.py"):
    inst = (site / member).read_bytes()
    src_eq[member] = hashlib.sha256(inst).hexdigest() == hashlib.sha256(z.read(member)).hexdigest()
page_src = (site / "pypdfium2/_helpers/page.py").read_text(encoding="utf-8").splitlines()
bind_src = (site / "pypdfium2_raw/bindings.py").read_text(encoding="utf-8").splitlines()
lines = {f"page.py:{i+1}": l.strip() for i, l in enumerate(page_src) if re.search(r"FPDF_GetPage(Width|Height)F\(self\)|src_(width|height)\s*=\s*math\.ceil", l)}
lines.update({f"bindings.py:{i+1}": l.strip() for i, l in enumerate(bind_src) if re.search(r"FPDF_GetPage(Width|Height)F\.restype", l)})
scale = 300.0 / 72.0
sizing = {}
for pt in (612.0, 792.0, 792.24, 652.8, 823.44, 666.24, 833.04):
    f = ctypes.c_float(pt).value
    sizing[str(pt)] = {"c_float": repr(f), "times_scale": repr(f * scale), "ceil_px": math.ceil(f * scale)}
need(all(src_eq.values()), "installed pypdfium2 sources differ from verified wheel")
need(sizing["792.0"]["ceil_px"] == 3301 and sizing["792.24"]["ceil_px"] == 3301 and sizing["823.44"]["ceil_px"] == 3432 and sizing["833.04"]["ceil_px"] == 3471, "sizing arithmetic")
OUT["B_renderer_sizing"] = {"wheel_sha256": wh, "installed_equals_wheel_member": src_eq, "source_lines": lines, "scale_repr": repr(scale), "sizing": sizing}

# ---------------- C/D. eight dev controls and corrected E2 ----------------
ANG = [(k - 50) / 10 for k in range(101)]


def otsu(gray: Image.Image) -> int:
    h = gray.histogram(); n = sum(h); tot = sum(i * c for i, c in enumerate(h))
    wb = sb = 0; best = -1.0; thr = 0
    for t in range(256):
        wb += h[t]
        if wb == 0:
            continue
        wf = n - wb
        if wf == 0:
            break
        sb += t * h[t]
        bv = wb * wf * (sb / wb - (tot - sb) / wf) ** 2
        if bv > best:  # first maximum
            best, thr = bv, t
    return thr


def V(mask: Image.Image, theta: float) -> float:
    r = mask.rotate(-theta, resample=Image.Resampling.NEAREST, expand=True, fillcolor=0)  # M_theta per card step 2
    w, h = r.size
    col = r.convert("F").resize((1, h), Image.Resampling.BOX)
    s = [col.getpixel((0, y)) * w for y in range(h)]
    mu = sum(s) / h
    return sum((v - mu) ** 2 for v in s) / h


def e2(I_in: Image.Image) -> tuple[Image.Image, dict]:
    g = I_in.convert("L")
    T_ = otsu(g)
    M = g.point(lambda v: 1 if v <= T_ else 0)  # L-mode 0/1 mask
    sc = {t: V(M, t) for t in ANG}
    best = max(sc.values())
    th = sorted([t for t, v in sc.items() if v == best], key=lambda t: (abs(t), -t))[0]
    trig = abs(th) >= 1.0 and sc[th] >= 1.10 * sc[0.0]
    out = I_in.rotate(-th, resample=Image.Resampling.BILINEAR, expand=True, fillcolor=(255, 255, 255)) if trig else I_in
    return out, {"otsu": T_, "theta_hat": th, "V_ratio": round(sc[th] / sc[0.0], 4), "triggered": trig, "phi_applied": -th if trig else 0.0}


def residual(img: Image.Image) -> float:
    """Re-estimate remaining CCW skew of an output buffer with the same card estimator on a +/-10 deg grid (2:1 BOX)."""
    g = img.convert("L").resize((img.width // 2, img.height // 2), Image.Resampling.BOX)
    T_ = otsu(g)
    M = g.point(lambda v: 1 if v <= T_ else 0)
    grid = [(k - 100) / 10 for k in range(201)]
    sc = {t: V(M, t) for t in grid}
    return max(sc, key=lambda t: (sc[t], -abs(t)))


man = json.loads(pathlib.Path("evaluation/manifests/corpus-manifest.json").read_text(encoding="utf-8"))
dev = [f for f in man["fixtures"] if f["split"] == "dev" and f["variant_kind"] in ("v1_raster300", "v2_skew")]
need(len(dev) == 8 and all(f["family_id"] in ("F01", "F02", "F04", "F07") for f in dev), "eight dev controls")
ctrl = []
for f in sorted(dev, key=lambda z: (z["family_id"], z["variant_kind"])):
    data = pathlib.Path(f["file_path"]).read_bytes()
    pg = MiniPdf(data).pages()[0]
    im = pg["images"]["Im1"]
    stored = zlib.decompress(im["raw"])
    doc = pdfium.PdfDocument(data)
    I_in = doc[0].render(scale=300.0 / 72.0).to_pil().convert("RGB")  # frozen contract, card §2.2
    doc.close()
    true = float(f["generation_or_transform_params"].get("signed_angle_degrees_ccw", 0.0))  # used only after estimation for residual
    out, r = e2(I_in)
    rec = {"fixture_page": f["fixture_id"] + "#p1", "variant": f["variant_kind"], "stored_xobject_px": [im["w"], im["h"]],
           "rendered_px": list(I_in.size), "rendered_rgb_sha256": hashlib.sha256(I_in.tobytes()).hexdigest(),
           "stored_rgb_sha256": hashlib.sha256(stored).hexdigest(), "rendered_equals_stored": I_in.size == (im["w"], im["h"]) and I_in.tobytes() == stored,
           **r, "true_ccw_deg_post_hoc": true, "analytic_residual_deg": round(true + r["phi_applied"], 2)}
    if r["triggered"]:
        rec["output_px"] = list(out.size)
        rec["empirical_residual_deg"] = residual(out)
        rec["outcome"] = "corrected" if abs(rec["analytic_residual_deg"]) < 0.05 and abs(rec["empirical_residual_deg"]) <= 0.1 else "NOT corrected"
    else:
        rec["output_is_input_object"] = out is I_in
        rec["output_bytes_identical"] = out.tobytes() == I_in.tobytes()
        rec["outcome"] = "byte-identical pass-through" if rec["output_bytes_identical"] and true == 0.0 else "UNEXPECTED"
    ctrl.append(rec)
    print(json.dumps({k: rec[k] for k in ("fixture_page", "rendered_px", "theta_hat", "triggered", "analytic_residual_deg", "outcome")}))
for rec in ctrl:
    need(rec["outcome"] in ("corrected", "byte-identical pass-through"), f"E2 outcome {rec['fixture_page']}: {rec['outcome']}")
ae = json.loads(git("show", f"{PINS['evidence']}:evaluation/manifests/review-correction-verification.json"))
ae_s = json.dumps(ae)
cmp_ = []
for rec in ctrl:
    cmp_.append({"fixture_page": rec["fixture_page"], "rendered_sha256_in_author_evidence": rec["rendered_rgb_sha256"] in ae_s,
                 "rendered_size_in_author_evidence": f"{rec['rendered_px'][0]}" in ae_s and f"{rec['rendered_px'][1]}" in ae_s})
OUT["C_input_contract_dev_controls"] = ctrl
OUT["C_author_evidence_comparison"] = cmp_
OUT["C_author_diagnostic_summary"] = {k: v for k, v in ae["executed_dev_diagnostic"].items() if not isinstance(v, (list, dict))}

# ---------------- E. RV-04 AST/JSON and RV-03 README ----------------
def defs(path: str) -> list[str]:
    t = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
    return sorted({n.name for n in ast.walk(t) if isinstance(n, (ast.FunctionDef, ast.ClassDef))} |
                  {tg.id for n in t.body if isinstance(n, ast.Assign) for tg in n.targets if isinstance(tg, ast.Name)})


resp = pathlib.Path("research/carbon/reconciliation/03-review-response.md").read_text(encoding="utf-8")
astd = {p: defs(p) for p in ("evaluation/generation/pdf_writer.py", "evaluation/generation/generate_corpus.py",
                             "evaluation/generation/verify_arithmetic_independent.py", "evaluation/generation/verify_corpus_integrity.py")}
claimed_actual = {"evaluation/generation/pdf_writer.py": ["EmbeddedRgbImage", "PdfPageCanvas", "estimate_text_width_pt", "wrap_text_deterministic", "pdf_escape", "serialize_pdf", "build_image_only_pdf", "LETTER_WIDTH_PT", "LETTER_HEIGHT_PT", "FIXED_PDF_DATE", "PRODUCER_TAG", "FONT_MAP"],
                  "evaluation/generation/generate_corpus.py": ["compute_invoice_accounting", "draw_invoice", "draw_work_order_or_packet", "make_hybrid_stamp_rgb", "rasterize_pdf_300dpi", "build_expected_payload", "generate_all", "main"],
                  "evaluation/generation/verify_arithmetic_independent.py": ["rhu_cents", "parse_printed_usd", "parse_printed_pct", "parse_printed_qty", "check_expected_file", "main"],
                  "evaluation/generation/verify_corpus_integrity.py": ["verify_evaluation_tree", "check_two_run_regeneration", "count_page_images_and_fonts", "sha256_file", "git_hash_file", "main"]}
claimed_absent = ["CanvasPage", "build_vector_pdf", "build_raster_pdf", "build_hybrid_stamped_pdf", "compute_invoice_totals", "render_invoice_pages", "render_work_order_pages",
                  "q2", "verify_invoice_doc", "verify_work_order_doc", "verify_existing_tree", "verify_deterministic_regeneration", "FIXED_ID_HEX"]
all_defs = set().union(*astd.values())
ast_res = {"claimed_actual_present": {p: [s for s in v if s not in astd[p]] for p, v in claimed_actual.items()},
           "claimed_absent_actually_absent": [s for s in claimed_absent if s in all_defs]}
need(all(not v for v in ast_res["claimed_actual_present"].values()) and not ast_res["claimed_absent_actually_absent"], "RV-04 AST claims")
cm_keys = sorted(man.keys())
ex = json.loads(pathlib.Path("evaluation/synthetic/expected/SYN-INV-01-v0-clean_expected.json").read_text(encoding="utf-8"))
srcs = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in pathlib.Path("evaluation/synthetic/sources").glob("*.json")}
json_res = {"corpus_manifest_keys": cm_keys, "expected_keys": sorted(ex.keys()),
            "labor_entries_in_any_source": any("labor_entries" in json.dumps(s) for s in srcs.values()),
            "line_items_in_work_order_sources": [n for n, s in srcs.items() if s["doc_kind"] != "invoice" and "line_items" in json.dumps(s)],
            "fees_by_family": {s["family_id"]: [f["fee_id"] for f in s.get("accounting_spec", {}).get("fees", [])] for s in srcs.values()},
            "credit_rows": {s["family_id"]: [i["row_id"] for i in s.get("accounting_spec", {}).get("line_items", []) if i["unit_price"].startswith("-")] for s in srcs.values()}}
need("totals" not in man and "split_summary" not in man and "token_bboxes" not in ex and "accounting_summary" not in ex and "transform_parameters" not in ex, "RV-04 JSON keys")
need(subprocess.run(["git", "cat-file", "-e", "e0b0228428cc77409f41a55ac11fb71fb9323ba4:research/astra/exchange/decision-map.md"]).returncode == 0
     and subprocess.run(["git", "cat-file", "-e", "e0b0228428cc77409f41a55ac11fb71fb9323ba4:research/astra/04-exchange-with-carbon/decision-map.md"], capture_output=True).returncode != 0, "Astra path")
# Triage of the /005 list of 50 absent labels into notation / inaccurate headings / nonexistent symbols-keys
rc = json.loads(git("show", "1787e942412f7a6981c7a6d730c44a83034ad0ef:docs/reviews/WP-0004/eld-rd-reviewer/evidence/report-claims.json"))
absent = rc["symbol_labels_absent_from_target_file"]
notation, headings, genuine = [], [], []
heads = {"evaluation/README.md": [l for l in pathlib.Path("evaluation/README.md").read_text(encoding="utf-8").splitlines() if l.startswith("#")]}
for a_ in absent:
    lab, f_ = a_["label"], a_["file_or_group"]
    if lab in ("fixtures[0..25]", "candidates[0..1]", "Q0.1", "Q0.6") or (lab.startswith("§") and not (lab == "§3" and f_.endswith("01-exchange-disposition.md"))):
        notation.append(a_)
    elif lab.startswith("§") or " " in lab:
        headings.append(a_)
    else:
        genuine.append(a_)
triage = {"total": len(absent), "notation": len(notation), "inaccurate_headings": len(headings), "nonexistent_symbols_or_keys": len(genuine),
          "author_triage_7_6_37_in_response": "7 + 6 + 37 = 50" in resp}
need((triage["notation"], triage["inaccurate_headings"], triage["nonexistent_symbols_or_keys"]) == (7, 6, 37), f"triage {triage}")
readme = pathlib.Path("evaluation/README.md").read_text(encoding="utf-8")
backlog = pathlib.Path("research/carbon/reconciliation/02-ranked-experiment-backlog.md").read_text(encoding="utf-8")
doc_res = {"readme_2550x3301": "2550 x 3301" in readme, "readme_still_2550x3300": "2550 x 3300" in readme,
           "readme_2720x3432": "2720 x 3432" in readme, "readme_2720x3431": "2720 x 3431" in readme,
           "readme_areas": "2.847%" in readme and "2.989%" in readme, "backlog_areas": "2.847%" in backlog and "2.989%" in backlog,
           "backlog_still_lt8pct": "< 8%" in backlog, "readme_still_lt8pct": "< 8%" in readme,
           "backlog_ceil_rule": "math.ceil" in backlog and "c_float" in backlog}
need(doc_res["readme_2550x3301"] and not doc_res["readme_still_2550x3300"] and doc_res["readme_2720x3432"] and doc_res["readme_2720x3431"]
     and doc_res["readme_areas"] and doc_res["backlog_areas"] and not doc_res["backlog_still_lt8pct"] and not doc_res["readme_still_lt8pct"], f"RV-03 docs {doc_res}")
OUT["E_rv04"] = {"ast": ast_res, "json": json_res, "triage_of_005_absences": triage}
OUT["E_rv03_docs"] = doc_res
OUT["failures"] = FAIL
OUT["all_pass"] = not FAIL
pathlib.Path(sys.argv[1]).write_text(json.dumps(OUT, indent=1) + "\n", encoding="utf-8")
print("FAILURES", FAIL)
print("ALL_PASS", not FAIL)
