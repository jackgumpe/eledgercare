# WP-0004 / 005: Independent review of joint R&D backlog and synthetic corpus

- Report path: `docs/agent-reports/eld-rd-reviewer/WP-0004/005_2026-11-14_review_eld-rd-reviewer.md`
- Sequence reservation: coordinator `INDEX.md` WP-0004 / 005 and `docs/kickoffs/WP-0004-eld-rd-reviewer.md` at release `2242223e59925ce9e52205d5af9be2ea0c140fac`
- Category: review
- Author / agent ID: eld-rd-reviewer
- Actual model / effort: Claude Opus 5.5 (high); backend checkpoint not exposed
- Execution environment: Antigravity CLI (agy), Windows 11 10.0.26200, conversation `2777c262-ec6c-4b3e-9d77-2e7f3d9dcd82`, spanning three CLI turns (two ended with UNAUTHENTICATED/401 exit 3; work preserved, nothing redone or inferred). Own `.venv` Python 3.12.10 with offline wheels pypdfium2 5.15.2 (PDFium 159.0.8149.0), Pillow 13.0.0, pypdf 7.1.0.
- Independence: no prior involvement in Astra/Carbon proposals, exchange, corpus, generator, expected data or backlog; not the product implementer.
- Timestamp: 2026-11-14T23:50:00Z
- Repository / branch: https://github.com/jackgumpe/eledgercare (private) / `review/wp-0004-rd`
- Base revision: `068f3f83bb532160b56e00f071f8badd8d3f51b0`
- Reviewed candidate: `29b2000265ae6068d9c86818622c81a40cadd961` (/007 evidence `85ab359ba3348e6323b531c5f8c2677d6775687e`, report at base); original /004 candidate `fca8f16e51359d6895dca27a05fe76af82f58ff4`, evidence `1ef33dcddf324a6a48285a6e302af5d1528b3c34`, report `fabddf72a80337a98ddb777c901edac11f9163fe`
- Review deliverable: `1787e942412f7a6981c7a6d730c44a83034ad0ef` (evidence/helpers, origin verified)
- Related: Astra /001 `1eb6f4af…`/`189d4cb4…`, Carbon /002 `39f475c1…`/`fef02d64…`, Astra /003 `e0b02284…`/`c3215f75…` (full pins in kickoff)
- Status: changes-requested (backlog card E2 and documentation); corpus ground truth independently verified, admission scope below
- Next owner: eld-coordinator (/006); bounded E2/doc correction by responsible author eld-rd-carbon

## Summary

Independent non-author review of the complete joint milestone, not only the /007 checksum patch. Corpus bytes, sources, expected data and visible page content agree under my own arithmetic, parser and visual inspection; deterministic regeneration reproduces all 53 artifacts byte-for-byte. One substantive backlog defect: E2 never defines `M_θ`, and under the most direct reading (same PIL CCW rotation used by the correction step and the corpus generator) the written correction doubles skew. Several documentation and /004-report statements are inaccurate. No OCR, model, GPU or runtime claim is made or supported.

## Disposition and corpus admission scope

- **Corpus (recommend admit, scoped):** 26 PDFs / 40 pages, 8 source JSONs, 26 expected JSONs and `corpus-manifest.json` at `29b2000` as a fictional synthetic starter set and **fixed test partition, not blind validation** (dev F01/F02/F04/F07 = 13 PDFs/19 p; eval_holdout F03/F05/F06/F08 = 13 PDFs/21 p). Printed-font, 8-family, small-sample, no-handwriting/no-real-scan limits stand. Requested doc corrections do not change any fixture or truth byte.
- **Backlog (changes requested):** Q0 separation, E1 and E3 are acceptable as falsifiable proposals; E2 needs RV-01 and RV-02 before it can be frozen.
- **Public candidates:** both remain `candidate_unadmitted`; 0 non-fixture PDFs in tree.

## Findings (source-pinned)

| ID | Sev | Finding | Evidence | Requested action |
| --- | --- | --- | --- | --- |
| RV-01 | high (card) | E2 (`02-ranked-experiment-backlog.md` §3 Rank 2 steps 2/5) maximizes `V(θ)` over undefined `M_θ`, then rotates by `−θ̂`. Reading A `M_θ = rotate(M, +θ)` (PIL CCW, same operator as step 5 and generator `signed_angle_degrees_ccw`) gives θ̂ = −4 on +4° pages and applies +4 → residual **+8°**; −3° → **−6°**. Reading B `rotate(M, −θ)` corrects to 0°. Clean v1 pages: θ̂ = 0, no trigger under both. The `|θ̂ − θ_true|` diagnostic inherits the ambiguity. Carbon /002 H-C3 defined θ̂ as the skew; the reconciled card lost that. | evidence/e2-diagnostic.json (dev F01/F02/F04/F07 p1, analytic and empirical residuals agree) | Author: define `M_θ` and sign explicitly (e.g. θ̂ = estimated CCW skew, `M_θ = rotate_ccw(M, −θ)`, apply `rotate_ccw(−θ̂)`), state mask rotation resampler. |
| RV-02 | medium (protocol) | Input path for image-only fixtures is unspecified. PDFium render at 300/72 is pixel-exact for all 12 v1 pages but resamples all 12 v2 pages (mean |Δ| 0.38–1.34 gray, ≤1 px offset) and renders −3° pages 2720×**3432** vs metadata `expanded_pixel_size_per_page` 2720×3431. E2 lists "300 DPI raster base pixels" as controlled. | evidence/display-faithfulness.json | Author: freeze one path (embedded-raster extraction or frozen renderer) for E2/E3 inputs and document the dimension. |
| RV-03 | low (doc) | `evaluation/README.md` §3 says v1 pages are 2550×3300; actual 2550×3301 (MediaBox 612×792.24). Hybrid bound stated "< 5%" (README) vs "< 8%" (backlog); actual 2.847% / 2.989%. | verify-summary.json DOC-PIXELS; arithmetic.json hybrid_area | Author: correct README wording. |
| RV-04 | medium (report accuracy; immutable) | /004 report misdescribes artifacts: "bicubic" rotation (actual BILINEAR in backlog and generator), hybrid areas 1.88%/2.16% (actual 2.85%/2.99%), "uncompressed" streams (FlateDecode), `FIXED_ID_HEX` (ID is sha256 prefix of body), keys `token_bboxes`/`accounting_summary`/`transform_parameters` (actual `bbox_pt`/`invoice_accounting`/`transform_params`), E1 "on 3-page fixtures" (backlog: all 8 originals), E3 "char_count >= 64" (backlog: τ calibrated on dev), path `research/astra/04-exchange-with-carbon/…` (actual `research/astra/exchange/…`), "non-taxable permits (F08)" (F08 has no fees; fees are F06/F07). Of 78 symbol labels, 50 are not literally present; after triage ~20 are notation/section labels, the rest are nonexistent functions/classes/keys (e.g. `CanvasPage`, `compute_invoice_totals`, `verify_existing_tree`, `labor_entries`; actual writer class `PdfPageCanvas`). | evidence/report-claims.json | Coordinator: record that the /004 report is not an accurate review map; canonical sources govern. Optional author correction report under a new sequence. |
| RV-05 | info | /004 receipt claimed wheel hashes matched while the manifest held a 55-char pypdfium2 hash; /007 correction verified: all 3 wheels now match size and 64-char SHA-256, single-field diff. | verify-summary.json wheels | None. |

## Verification (reviewer-executed)

| Check | Result | Evidence |
| --- | --- | --- |
| Remote pins (release, 12 author commits) | all present on origin | session log |
| Wheels rehash vs corrected provenance, copy, own offline `.venv` | 3/3 size+SHA-256 match (pre- and post-copy) | verify-summary.json |
| Export of `29b2000` vs `git ls-tree` | 98/98 blobs equal; candidate→base delta = 2 author evidence/report files | inventory.json |
| Manifest: fixture/source/expected hashes, sizes, blob OIDs, pages, parents, splits | 26/26, 8/8, 18 parent links; every variant in parent family/split; 0 cross-split shared identifiers | verify-summary.json |
| Own PDF parse vs PDFium page counts; v0/v3 Base-14, no embedded fonts; v1/v2 one image, no text | 26 PDFs / 40 pages, all pass | pdf-structure.json |
| Transform reproduction | v1: 12/12 pages pixel-identical to own PDFium render of v0; v2: 12/12 pixel-identical to Pillow rotate of v1 with declared angle | pdf-structure.json |
| Own arithmetic from sources (integer cents, half-away-from-zero) bound to expected JSON and to visible Tj text by row/label position | 3,756+ assertions, 0 failures; 40 invoice rows, 32 summary values, 58 table rows, 361 fields, 1,801 cells; notice/remittance literals (F05, F06, F07) match; one rounding tie exercised (F05 L04 26.985→26.99) | arithmetic.json |
| Negative control (planted source and expected defects) | both detected (52 and 1 findings) | rd005_mutation_control.py |
| Glyph geometry (PDFium tight boxes vs stroked rules, page bounds, glyph overlap) on 16 text pages | 0 crossings, 0 outside, 0 overlaps; min glyph-to-rule gap 3.76 pt | glyph-geometry.json |
| Deterministic regeneration: author generator from export, two isolated runs | 53/53 byte-identical to candidate in both | regeneration-compare.json |
| Display faithfulness of decoded views (coordinator audit) | 28/28 structural (exact full-page `cm`, no clip/CropBox/Rotate; hybrid = v0 content + one image op at declared box); 12 render pixel-exact, 12 v2 renderer-resampled (RV-02) | display-faithfulness.json |
| Visual inspection | 40/40 pages, 26/26 PDFs, 82 views, both halves each; values, page order, sentinels, continuation markers, repeated headers, final-page-only totals, serial integrity, stamps legible; no clipping/overlap; +4° CCW / −3° CW verified | visual-coverage.json |
| E2 sign diagnostic (CPU, dev only, no OCR) | RV-01 | e2-diagnostic.json |
| Upstream claims vs Astra pinned snapshots (`1eb6f4af`): `eval(ref_text[2])` L120; `infer` auto-crop L541; `infer_multi` `setdefault('crop_mode', False)`; client `infer.py` L74 `crop_mode = True` (with L81–83 multi-page fallback to False); `q_chunk` default 2048; `_forward_triton`/`_forward_dense` present; safetensors LFS total 6,688,305,576 B; `_sparse_base_impl.py` Apache-2.0 header and `transformers` imports | consistent | git show at pin |

Author checkers were not used as substitutes. Not run: upstream re-download (snapshots are author-retrieved; HF/GitHub pins not re-fetched), OCR/model/GPU, holdout E2 diagnostic (dev only by design), license legal review.

## Change inventory

| Action | Path | Purpose |
| --- | --- | --- |
| Added | `docs/reviews/WP-0004/eld-rd-reviewer/README.md` | Evidence index |
| Added | `docs/reviews/WP-0004/eld-rd-reviewer/helpers/{rd005_verify,rd005_mutation_control,rd005_regen_compare,rd005_render_pages,rd005_display_faithfulness,e2_sign_diagnostic,rd005_report_claims}.py` | Reviewer helpers (7) |
| Added | `docs/reviews/WP-0004/eld-rd-reviewer/evidence/*.json` | 11 evidence files |
| Added (this commit) | this report | Canonical /005 report |

External effects: read-only wheel copy into ignored `.scratch/wheels`; own ignored `.venv`, `.scratch` exports/renders/regenerations; normal push of `review/wp-0004-rd` only. No candidate, author report, INDEX/CURRENT, product, service, database, GPU or global change.

## Handoff

eld-coordinator /006: record corpus admission scope as above if accepted; route RV-01/RV-02/RV-03 as one bounded eld-rd-carbon correction (backlog + README only, no fixture bytes); note RV-04. Deliverable `1787e942412f7a6981c7a6d730c44a83034ad0ef`; report publication SHA supplied in handoff after push.
