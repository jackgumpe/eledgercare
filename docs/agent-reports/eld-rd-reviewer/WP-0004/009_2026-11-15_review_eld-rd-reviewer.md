# WP-0004 / 009: Independent closure of RV-01..RV-04 corrections

- Report path: `docs/agent-reports/eld-rd-reviewer/WP-0004/009_2026-11-15_review_eld-rd-reviewer.md`
- Sequence reservation: `INDEX.md` WP-0004 / 009 and `docs/kickoffs/WP-0004-eld-rd-reviewer-closure.md` at release `59addece030ba2629871babf2895cc8e2afaa37e`
- Category: review
- Author / agent ID: eld-rd-reviewer
- Actual model / effort: Claude Opus 5.5 (high); backend checkpoint not exposed
- Execution environment: Antigravity CLI, Windows 11 10.0.26200, same conversation `2777c262-ec6c-4b3e-9d77-2e7f3d9dcd82` as /005; qualified /005 `.venv` (Python 3.12.10, pypdfium2 5.15.2 / PDFium 159.0.8149.0, Pillow 13.0.0, pypdf 7.1.0); no new installs
- Independence: no authorship of any R&D, corpus or correction artifact; author of /005 review only
- Timestamp: 2026-11-15T01:40:00Z (UTC, approximate time of writing)
- Repository / branch: https://github.com/jackgumpe/eledgercare (private) / `review/wp-0004-rd`
- Base revision: `8f9a3281fa223d25447677b8ed8b873bf9e5cd01` (my /005 publication)
- Review merge: `dfcf4b52a7d697af0cf0f38c98464aee8d4929ed` (normal no-ff merge; parents `8f9a3281…`, `f69c9e4fdec2e12f481e6131965b5e4e184e013f`; no conflicts)
- Reviewed: candidate `54c7f6fe062720cbdf92e6bcd7476b697fc4afe1`, author evidence `fb2d8e616ad375ac7ccfa5f9000ba3340476c148`, author /008 report `f69c9e4f…`; corpus pin `29b2000265ae6068d9c86818622c81a40cadd961`
- Closure evidence: `a79fb29f3d89fde938ebfe92d7455a441bd5f4a6` (origin verified)
- Previous report: WP-0004 / 005 at `8f9a3281…`, evidence `1787e942412f7a6981c7a6d730c44a83034ad0ef`
- Status: accepted (closure of RV-01..RV-04)
- Next owner: eld-coordinator, WP-0004 / 006

## Summary

Bounded closure, not a redo of /005. The author delta is exactly four candidate paths plus separate evidence and report additions, and every corpus, source, expected, generation, manifest and prior-report object is unchanged. RV-01..RV-04 are resolved on the evidence I checked independently. /005's full corpus checks (40/40 pages and 82 views inspected, own source arithmetic with 3,756+ binding assertions, two 53/53 byte-identical regenerations, transform reproduction) still apply because the objects are identical. They are cited by identity, not repeated.

## Disposition

| ID | Verdict | Basis (closure-check.json section) |
| --- | --- | --- |
| RV-01 | **closed** | Card E2 now defines CCW-positive θ as hypothesized skew. It defines `M_θ = M.rotate(−θ, NEAREST, expand=True, fillcolor=0)`, population row-sum variance and an unchanged 101-point grid, trigger and ties. It applies one RGB BILINEAR `I_in.rotate(−θ̂)` and gives the estimation error and residual formulas. I implemented this from the card text without metadata input (D). F01/F07 +4° gave θ̂ = +4.0; F02/F04 −3° gave θ̂ = −3.0. All four were triggered with V ratio 6.58–6.76, and analytic and re-measured residuals were 0.0°. The four v1 clean controls had θ̂ = 0, no trigger, and output bytes identical to input (the same object). The sign defect from /005 is gone. |
| RV-02 | **closed** | §2.2 freezes one contract, `page.render(scale=300.0/72.0).to_pil().convert("RGB")`, shared by both arms in Q0, E1, E2 and the E3 fallback/Stage 3B. The E3 original-PDF text gate stays a separate path with no rasterization. My renders of the 8 dev controls (C): v1 pages are 2550×3301 and byte-identical to the stored XObject; +4° pages are 2776×3471 and −3° pages 2720×3432 (stored 2720×3431), and both are resampled. All 8 RGB-buffer SHA-256 values and sizes appear in the author evidence. |
| RV-03 | **closed** | Active README now states 2550×3301, 2720×3432 rendered versus 2720×3431 stored, and the measured hybrid areas 2.847%/2.989% (README and backlog). No stale `2550 x 3300` or `< 8%` remains (E). The sizing rule was verified in actual package source (B). The installed `pypdfium2/_helpers/page.py` and `pypdfium2_raw/bindings.py` are byte-equal to members of the verified wheel (SHA-256 `74d1bace…cfbd`). In that source, `page.py:458–459` computes `math.ceil(self.get_width()/get_height() * scale)`, and `bindings.py:647/657` sets restype `c_float`. Computed values: c_float(792.0)×4.166666666666667 = 3300.0000000000005 → 3301; c_float(823.44) = 823.4400024414062 → 3431.0000101725263 → 3432; c_float(833.04) → 3470.9999… → 3471. These match the card's statements. |
| RV-04 | **closed** | `03-review-response.md` errata checked against actual AST, JSON and git (E). Every "actual" definition it lists exists, and every claimed-absent symbol (`CanvasPage`, `compute_invoice_totals`, `verify_existing_tree`, `FIXED_ID_HEX`, …) is absent. The JSON keys (`counts`/`fixtures`, `transform_params`, `invoice_accounting`, `bbox_pt`) are correct. `labor_entries` appears in no source. Fees are in F06/F07 and credits in F06 L10 and F07 L20; F08 has none. The Astra path `research/astra/exchange/decision-map.md` exists and the cited `04-exchange-with-carbon` path does not. The /004 and /005 reports are preserved unchanged. |

**Correction to my /005 report (immutable; recorded here):** /005 RV-04 estimated that roughly 20 of the 50 literal absences were notation or section labels. My independent triage gives **7 valid notation labels, 6 inaccurate headings and 37 nonexistent symbols or keys**, which matches the author's 7 + 6 + 37. All other /005 findings stand as published.

## Final recommendation

- **Corpus:** admit the 26 PDFs / 40 pages, 8 sources, 26 expected files and the manifest at `29b2000` (all unchanged in `54c7f6f`) as a fictional synthetic starter set. Treat it as a fixed, non-blind dev/test partition (dev F01/F02/F04/F07; eval_holdout F03/F05/F06/F08). No public candidate is admitted.
- **Backlog:** accept Q0 + E1–E3 at `54c7f6f` as falsifiable proposals only. Q0 has not been performed. No throughput, model, GPU, Windows CUDA, extraction-quality or production-readiness claim exists or is implied.
- **Remaining limits:**
  - The set is printed-font, 8-family and small-sample, with no real scans or handwriting.
  - v2 inputs carry a PDFium resample in both arms (documented as a confound).
  - The E2 check here validates the specification on 4 skewed and 4 clean dev pages only. It is not an E2 result.

## Verification (this assignment)

| Operation | Result |
| --- | --- |
| `git fetch`; read release kickoff and INDEX /009; AGENTS and reporting rules diff 068f3f8→59addec | rules unchanged; pins on origin |
| `git diff --raw` base→candidate→publication | exactly 4 candidate paths (2 M, 2 A) + 2 A (evidence, report) |
| `git merge --no-ff f69c9e4` | `dfcf4b5`, no conflicts |
| `closure_check.py` run 1 | failed: `ModuleNotFoundError: rd005_verify` (helper path); fixed |
| `closure_check.py` run 2 | exit 0, `ALL_PASS: true`, `failures: []` (results above). 77 protected objects equal to `29b2000` (26 PDFs, 26 expected, 8 sources, 4 generation, manifests, prior reports); 20 /005 review objects preserved; merge adds only reviewer paths to the author tree |
| CLI interruption | after run 2, the turn ended UNAUTHENTICATED/401 (exit 3). Saved results were read and published without rerun. |
| Commit/push evidence | `a79fb29` pushed (`8f9a328..a79fb29`, includes merge); origin equal |

Not run (unchanged objects, attributed to /005): page inspection, corpus arithmetic, regeneration. Also not run: the author's `verify_review_corrections.py` (inspected as author evidence only), and any holdout fixture, OCR, model or GPU work.

## Change inventory

| Action | Path |
| --- | --- |
| Merged (author-authored, unchanged) | `evaluation/README.md`, `research/carbon/reconciliation/02-ranked-experiment-backlog.md`, `research/carbon/reconciliation/03-review-response.md`, `research/carbon/reconciliation/verify_review_corrections.py`, `evaluation/manifests/review-correction-verification.json`, `docs/agent-reports/eld-rd-carbon/WP-0004/008_2026-11-15_research_eld-rd-carbon.md` |
| Added (reviewer) | `docs/reviews/WP-0004/eld-rd-reviewer/closure/README.md`, `closure_check.py` (SHA-256 `775e278d…e0ab`), `closure-check.json` |
| Added (this commit) | this report |

The README cites SHA-256 `c364c4ed…7d470d616` for `closure-check.json`; that hash is of the CRLF scratch output. `.gitattributes` (`*.json eol=lf`) normalized the committed blob, whose SHA-256 is `74f76f434298c4694353aa66153b22f19689468a45fcb6c3b654ef6874976358`. The content is otherwise identical.

External effects: ignored scratch only, plus a normal push of `review/wp-0004-rd`. No INDEX/CURRENT, author, /005, corpus, product, service, package or configuration change.

## Handoff

eld-coordinator /006: closure verdict **accepted** for RV-01..RV-04. Admit the corpus and backlog within the scope above, integrate, and stop the bootstrap milestone. Merge `dfcf4b52a7d697af0cf0f38c98464aee8d4929ed`, evidence `a79fb29f3d89fde938ebfe92d7455a441bd5f4a6`; the report publication SHA is supplied in the handoff.
