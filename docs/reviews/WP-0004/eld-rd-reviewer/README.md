# WP-0004 / 005 eld-rd-reviewer independent evidence

Reviewer-authored (eld-rd-reviewer; Claude Opus 5.5, high; conversation 2777c262-ec6c-4b3e-9d77-2e7f3d9dcd82). No author module is imported by `rd005_verify.py`; the author generator was executed only for isolated regeneration. Candidate: `29b2000265ae6068d9c86818622c81a40cadd961` (exported with `git archive`, all 98 blobs re-hashed equal to `git ls-tree`).

| File | Content |
| --- | --- |
| helpers/rd005_verify.py | Own PDF/xref/content parser, integer-cent half-away-from-zero arithmetic from sources, source↔expected↔visible text binding, v1/v2 transform reproduction, PDFium glyph clipping/overlap geometry, manifest/split/provenance/wheel checks |
| helpers/rd005_mutation_control.py | Negative control: planted source and expected defects are both detected |
| helpers/rd005_regen_compare.py | Byte comparison of two isolated author-generator runs with the candidate |
| helpers/rd005_render_pages.py | Renders the 82 inspection views for all 40 pages |
| helpers/rd005_display_faithfulness.py | Page dict/content/matrix/clip assertions and direct PDFium render correspondence for 28 image-bearing pages |
| helpers/e2_sign_diagnostic.py | CPU-only E2 angle-sign diagnostic on dev v1/v2 page 1 (F01, F02, F04, F07), two readings of undefined `M_theta` |
| helpers/rd005_report_claims.py | Symbol/path/claim audit of the published /004 report |
| evidence/verify-summary.json | Counts, wheel/script/source/fixture matches, binding totals (3,756+ assertions, 0 failures), rounding ties, findings |
| evidence/inventory.json, pdf-structure.json, arithmetic.json, glyph-geometry.json | Per-file hashes; per-page structure; per-invoice own arithmetic; per-page glyph geometry |
| evidence/regeneration-compare.json | 53/53 artifacts byte-identical in two isolated runs |
| evidence/display-faithfulness.json | 28/28 structural; 12 v1 pages PDFium pixel-exact; 12 v2 pages PDFium-resampled |
| evidence/e2-diagnostic.json | Reading A amplifies (+4→+8, −3→−6), reading B corrects; 0 clean false triggers |
| evidence/visual-coverage.json, render-index.json | 40 pages / 26 PDFs / 82 views, per-page record and view hashes |
| evidence/report-claims.json | 78 symbol labels checked, 50 not literally present (triaged in report) |
