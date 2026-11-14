#!/usr/bin/env python3
"""Check symbol/path/claim references in the published author reports against actual artifacts
(reviewer-authored). Usage: python rd005_report_claims.py <fca8f16 export> <29b2000 export> <out.json>

Reads the /004 report at its publication (identical bytes in the 29b2000 export) and tests:
  * every backticked identifier in the 'Relevant symbols / sections' column of inventory section 2
    against the actual content of the referenced file at fca8f16 (substring presence);
  * selected factual claims (resampler, hybrid area, stream compression, JSON key names, paths).
"""
import json, pathlib, re, subprocess, sys

c004, c29, outp = map(pathlib.Path, sys.argv[1:4])
rep = (c29 / "docs/agent-reports/eld-rd-carbon/WP-0004/004_2026-11-14_research_eld-rd-carbon.md").read_text(encoding="utf-8")
sec2 = rep.split("### 2. Complete original-author-base-to-candidate inventory")[1].split("### 3.")[0]
rows = [l for l in sec2.splitlines() if l.startswith("| ") and "`" in l]
generic = {"family_id", "split"}
sym_results = []
for l in rows:
    cells = [c.strip() for c in l.strip("|").split("|")]
    if len(cells) < 6 or not re.findall(r"`([^`]+)`", cells[2]):
        continue
    path = re.findall(r"`([^`]+)`", cells[2])[0]
    syms = re.findall(r"`([^`]+)`", cells[-1])
    p = c004 / path
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    for s in syms:
        probe = s.split("(")[0].strip()
        if probe in generic:
            continue
        found = probe in text
        sym_results.append({"file": path, "symbol_label": s, "present_in_file": found})
uniq = {}
for r in sym_results:
    uniq.setdefault((r["file"].rsplit("/", 1)[0] if "expected" in r["file"] or "pdfs" in r["file"] else r["file"], r["symbol_label"]), r["present_in_file"])
missing = sorted({(k[1], k[0]) for k, v in uniq.items() if not v})

pdfw = (c004 / "evaluation/generation/pdf_writer.py").read_text(encoding="utf-8")
gen = (c004 / "evaluation/generation/generate_corpus.py").read_text(encoding="utf-8")
backlog = (c004 / "research/carbon/reconciliation/02-ranked-experiment-backlog.md").read_text(encoding="utf-8")
readme = (c004 / "evaluation/README.md").read_text(encoding="utf-8")
exp0 = json.loads((c004 / "evaluation/synthetic/expected/SYN-INV-01-v0-clean_expected.json").read_text(encoding="utf-8"))
astra_path_ok = subprocess.run(["git", "cat-file", "-e", "e0b0228428cc77409f41a55ac11fb71fb9323ba4:research/astra/04-exchange-with-carbon/decision-map.md"], capture_output=True).returncode == 0
astra_real_ok = subprocess.run(["git", "cat-file", "-e", "e0b0228428cc77409f41a55ac11fb71fb9323ba4:research/astra/exchange/decision-map.md"], capture_output=True).returncode == 0
claims = [
    {"claim": "/004 report: E2/review map use 'bicubic' RGB rotation", "report_says_bicubic": "bicubic" in rep.lower(),
     "backlog_says": "BILINEAR" if "BILINEAR" in backlog else "?", "generator_uses": "BILINEAR" if "Resampling.BILINEAR" in gen else "?"},
    {"claim": "/004 report: hybrid areas 1.88% / 2.16% / '<3%'", "report_mentions_1.88": "1.88%" in rep, "report_mentions_2.16": "2.16%" in rep,
     "actual_area_from_box_pt": {"SYN-WO-02-v3-hybrid-note": round(300 * 46 / (612 * 792), 5), "SYN-MP-02-v3-hybrid-stamp": round(315 * 46 / (612 * 792), 5)},
     "readme_bound": "< 5%" if "< 5%" in readme else None, "backlog_bound": "< 8%" if "< 8%" in backlog else None},
    {"claim": "/004 report: pdf_writer 'uncompressed/deterministic streams', FIXED_ID_HEX", "report_says_uncompressed": "uncompressed" in rep,
     "writer_uses_FlateDecode": "/FlateDecode" in pdfw, "FIXED_ID_HEX_in_writer": "FIXED_ID_HEX" in pdfw,
     "actual_id_rule": "trailer /ID = first 32 hex of sha256(body before xref)" if "hashlib.sha256(bytes(out)).hexdigest()[:32]" in pdfw else "?"},
    {"claim": "/004 report: expected JSON keys token_bboxes / accounting_summary / transform_parameters", "actual_top_keys": sorted(exp0.keys()),
     "token_bboxes_present": "token_bboxes" in exp0, "accounting_summary_present": "accounting_summary" in exp0, "transform_parameters_present": "transform_parameters" in exp0},
    {"claim": "/004 report: E3 'char_count >= 64'", "report_has": "char_count \u003e= 64" in rep or "char_count >= 64" in rep, "backlog_has_64": "64" in backlog.split("E3")[-1]},
    {"claim": "/004 report path research/astra/04-exchange-with-carbon/decision-map.md @e0b0228", "exists": astra_path_ok, "actual_path_exists": astra_real_ok},
    {"claim": "/004 report: 'negative warranty credits (F06), non-taxable permits (F08)'", "report_has": "non-taxable permits (`F08`)" in rep,
     "F08_doc_kind": json.loads((c004 / "evaluation/synthetic/sources/F08_SYN-MP-02_source.json").read_text(encoding="utf-8"))["doc_kind"],
     "F06_credit_description": [i["description"] for i in json.loads((c004 / "evaluation/synthetic/sources/F06_SYN-INV-03_source.json").read_text(encoding="utf-8"))["accounting_spec"]["line_items"] if i["unit_price"].startswith("-")]},
    {"claim": "/004 report E1 description 'on 3-page 300 DPI fixtures'", "report_has": "on 3-page `300 DPI` fixtures" in rep, "backlog_E1_scope_all_8_originals": "all 8 clean originals" in backlog},
    {"claim": "README '2550 x 3300' v1 pixels", "readme_has": "2550 x 3300" in readme},
]
res = {"tool": "docs/reviews/WP-0004/eld-rd-reviewer/helpers/rd005_report_claims.py", "symbol_labels_checked": len(uniq),
       "symbol_labels_absent_from_target_file": [{"label": a, "file_or_group": b} for a, b in missing], "claims": claims}
outp.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
print(json.dumps({"checked": len(uniq), "absent": len(missing)}))
for a, b in missing:
    print("  ABSENT", a, "|", b)
for c in claims:
    print(json.dumps(c))
