# WP-0004 final coordinator disposition

Status: ACCEPTED for the bounded synthetic corpus/backlog milestone on the published independent /009 verdict. Final integration verification is in progress. This acceptance releases only normal integration and final reporting, followed by the bootstrap stop boundary.

Owner: eld-coordinator, Codex session 01a1d895-c605-7ab2-b7ec-c3159c0634ba; actual model/effort not exposed. Execution base: 299d60480dd69d3632fdcc709ea3f4b6cb6abdd9. Binding: [coordinator kickoff](../../kickoffs/WP-0004-eld-coordinator-disposition.md) and INDEX WP-0004 /006. All author and reviewer publications remain immutable.

## Exact inputs

| Input | Revision |
| --- | --- |
| Seed | 35f6090a9b2e16c7645b56f34b104eb3126d5c90 |
| Astra initial plus single exchange publication | c3215f75fc311c2e3c61a8ecc5da7d950f933157 |
| Original complete Carbon corpus candidate /004 | fca8f16e51359d6895dca27a05fe76af82f58ff4 |
| Corrected provenance/corpus candidate /007 | 29b2000265ae6068d9c86818622c81a40cadd961 |
| Independent /005 evidence / report | 1787e942412f7a6981c7a6d730c44a83034ad0ef / 8f9a3281fa223d25447677b8ed8b873bf9e5cd01 |
| Final Carbon definition/documentation candidate /008 | 54c7f6fe062720cbdf92e6bcd7476b697fc4afe1 |
| Author /008 evidence / report | fb2d8e616ad375ac7ccfa5f9000ba3340476c148 / f69c9e4fdec2e12f481e6131965b5e4e184e013f |
| Independent /009 evidence / accepted report | a79fb29f3d89fde938ebfe92d7455a441bd5f4a6 / da58038960eb5c4cc83be76e26d917ee378b2f07 |
| Actual coordinator integration | Not performed |

The /009 evidence and canonical accepted report are published with exact origin verified. The coordinator executed [audit-closure-inputs.py](audit-closure-inputs.py) against evidence a79fb29f3d89fde938ebfe92d7455a441bd5f4a6 and author evidence fb2d8e616ad375ac7ccfa5f9000ba3340476c148. [All eight exact fixture mappings passed](closure-input-binding.json): rendered RGB SHA-256, dimensions, estimated/applied angles and trigger decisions agree. This is a comparison of published evidence, not a second CPU experiment.

[Publication-byte reconciliation](closure-publication-bytes.json) confirms that the executed reviewer helper is byte-identical to its Git publication (SHA-256 775e278d86d7799d0ff3c4749c75b91508c9fd53db1327dd0103ee192c28e0ab). The closure README's JSON checksum c364c4ed7101ebab3b0b17702e43b8afb60575bf3d7b38efba64a5b87470d616 describes the executed Windows file with 495 CRLF line endings. Git normalizes those to LF, yielding published SHA-256 74f76f434298c4694353aa66153b22f19689468a45fcb6c3b654ef6874976358; no other byte or JSON value differs. The reviewer also observed the normalized Git hash at step 299. No rerun of an unchanged algorithm is warranted for that normalization.

## Prior independent evidence, with attribution

The uninvolved Opus reviewer executed the original full corpus review in conversation 2777c262-ec6c-4b3e-9d77-2e7f3d9dcd82, selected claude-opus-5-5-high/high. Its /005 report recommends scoped corpus admission and requests RV-01..03 corrections to the backlog/documentation; RV-04 identifies inaccurate historical author-report descriptions. A published author correction does not close those findings independently.

At /005, the reviewer verified 98 Git objects, all three pinned CPU wheels, four generation/check scripts, eight original source records, 26 fixture hashes, 18 parent links, 12 raster reproductions and 12 skew reproductions. Its independent integer-cent arithmetic and source/expected/visible-text binding completed 3,760 assertions with zero binding failures, including 58 table rows, 1,801 cells, 361 fields, 40 invoice rows and 32 summary values. A planted source defect and a planted expected-data defect were both detected. Glyph checks covered 16 text pages with zero outside-page glyphs, crossings or overlaps; minimum glyph-to-rule gap was 3.76 pt.

Both independent reviewer regeneration runs reproduced all 53 generated artifacts byte-for-byte, with zero missing, extra or different files. All 40 pages across 26 PDFs were visually inspected through 82 required views. The coordinator matched 82 actual completed image-read operations to the inspection index and verified all 82 retained image hashes; [the attributed observation receipt](reviewer-visual-execution-receipt.json) records that audit. It is evidence of the reviewer's execution, not a second visual review by the coordinator.

All 28 image-bearing pages passed the reviewer's structural display-faithfulness checks. The 12 v1 pages are pixel-identical to direct PDFium renders; the 12 v2 pages are renderer-resampled and are not universally pixel-identical. The clarified input contract documents the stored/rendered distinction. No unchanged visual review or full regeneration is repeated solely for documentation/integration work.

## Findings and record reconciliation

RV-01..04 are CLOSED by uninvolved Opus /009 at da58038960eb5c4cc83be76e26d917ee378b2f07. The author /008 response defines estimated CCW skew, mask leveling by its negative, a single BILINEAR RGB correction and consistent metrics; freezes the PDFium rendering input; corrects pixel dimensions and hybrid stamp areas; and supplies source-grounded errata for /004. Opus's separate implementation from the card passed all eight dev controls on review merge dfcf4b52a7d697af0cf0f38c98464aee8d4929ed: four clean byte-identical no-ops and four correctly signed skew corrections with zero analytic and measured residuals. It verified the renderer source against the pinned wheel, 77 protected source/corpus objects and 20 preserved /005 review objects, the exact author delta and the corrected AST/JSON/path references. Its initial import-path failure was corrected before the successful run; an authentication interruption occurred afterward, and a continuation published the preserved results without rerunning unchanged checks. The coordinator accepts the corpus and proposals within the explicit limits below.

Precise scope of /009: only the eight dev PDF pages were rendered and deskewed. RV-04 inspection also read original source JSONs across all eight families and corpus metadata, including held-out-family source records; the closure README's phrase "no holdout file opened" must be read as no holdout PDF diagnostic, not absence of all held-out-family metadata inspection. No holdout tuning or OCR occurred. The exact package sizing operations are ceil(get_width() * scale) and ceil(get_height() * scale), separately, as preserved in closure-check.json B_renderer_sizing. /009 explicitly corrects the approximate /005 label count to seven valid notation labels, six inaccurate headings and 37 nonexistent symbols/keys; that correction governs.

The immutable /004 report is not a reliable source map for the claims identified by RV-04. Canonical source governs; the new [author correction record](../../../research/carbon/reconciliation/03-review-response.md) and final independent closure govern their corrected interpretation. Preserve the original report rather than silently rewriting history. /007 repaired the truncated wheel checksum; the independent /005 review verified all three complete hashes and sizes.

The /005 header says 2026-11-14T23:50:00Z, while its actual Git report commit was 2026-11-14T23:47:17Z and observed publication occurred before the header time. This receipt uses the observed/Git chronology and preserves the report unchanged. The coordinator's earlier note that full regeneration was still pending was incorrect: step 89 had already completed both 53-artifact runs. The published correction at ac4fabe538db8803063dc72342abea3472bbb975 records that tracking error. Neither discrepancy changes the executed evidence.

Likewise, /009 labels its 2026-11-15T01:40:00Z header as approximate; the actual Git report commit was 2026-11-15T01:39:08Z, with push output observed by 01:39:15Z. Root independently verified origin at da58038960eb5c4cc83be76e26d917ee378b2f07. The initial PowerShell publication command reported exit 1 despite successful push output; actual remote verification establishes publication. Preserve the report and use observed/Git times for chronology.

## Verification and disposition to complete

After published independent closure supports acceptance, record its exact pins and verdict, normally merge the unchanged Astra and accepted Carbon/reviewer lineages, and run verify-integration.py against the actual merge. Also run the existing WP-0003 integration verifier to establish that all 94 accepted candidate paths, 90 application inputs and 28 product evidence additions remain identical. Record all Git-object comparisons and the complete base-to-deliverable path inventory. The scoped R&D .gitattributes addition is only *.py text eol=lf; no global Git configuration change is involved.

The acceptance scope remains a fictional synthetic starter corpus: 26 PDFs /40 pages, eight families, dev F01/F02/F04/F07 (13 PDFs/19 pages), fixed eval_holdout F03/F05/F06/F08 (13 PDFs/21 pages). This is a fixed non-blind partition, with printed-font, small-sample, no-real-scan and no-handwriting limits. Both public candidates remain unadmitted and zero non-fixture PDFs are admitted. The three-card backlog is a set of proposals; Q0 qualification, model/OCR/GPU execution, throughput/quality claims, customer data and deployment remain unperformed and unreleased. Source assessment used pinned captured upstream files; the reviewer did not re-fetch upstream or give a legal license opinion.

External effects of this coordinator assignment: own coordination records, read-only inspection of owned branches/logs, normal Git integration/publication when released, and ignored scratch preparation. No production implementation, packages, services/databases, authentication/global configuration or model execution. Stop after final admission/integration and user handoff; the accepted F1 product milestone is already complete.
