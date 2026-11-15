# WP-0004 / 008: Resolve WP-0004 / 005 review findings RV-01 through RV-04

- Report path: `docs/agent-reports/eld-rd-carbon/WP-0004/008_2026-11-15_research_eld-rd-carbon.md`
- Sequence reservation: Coordinator `INDEX.md` (`WP-0004 / 008`, initially bound at `d216bdcd9aa65632ed1556899fda191c56cc2800` and UTC-date-reconciled to `2026-11-15` at `7a21fdbb154f735656bbfc7602ad84e8d05b17ab`), `docs/kickoffs/WP-0004-eld-rd-carbon-review-correction.md` (@ `d216bdcd9aa65632ed1556899fda191c56cc2800` & `7a21fdbb154f735656bbfc7602ad84e8d05b17ab`), and `docs/coordination/WP-0004-render-rounding-preflight.md` (@ `7a21fdbb154f735656bbfc7602ad84e8d05b17ab`)
- Category: research
- Author / agent ID: `eld-rd-carbon`
- Actual model / effort: Gemini 4 Carbon (High effort; backend checkpoint ID not exposed)
- Execution environment: CLI (Antigravity CLI on Windows 11 x64 `10.0.26200`, PowerShell, author continuation conversation `993d4f08-72d0-479c-9e6c-047280cedf95` continuing `eld-rd-carbon` author lineage from `74513d00-ee88-4e85-a554-120908615b21`; owned `.venv` Python `3.12.10`, `pypdfium2==5.15.2` / `PDFium 159.0.8149.0@sourcebuild-toolchained`, `Pillow==13.0.0`, `pypdf==7.1.0`)
- Published by: `eld-rd-carbon` (self-published on owned branch `research/wp-0004-carbon-recovery`)
- Timestamp: 2026-11-15T00:18:00Z
- Repository / branch: `https://github.com/jackgumpe/eledgercare` (`PRIVATE`) / `research/wp-0004-carbon-recovery` (owned worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-rd-carbon-recovery`)
- Base revision: `068f3f83bb532160b56e00f071f8badd8d3f51b0` (`WP-0004 / 007` report publication commit; unchanged corpus candidate `29b2000265ae6068d9c86818622c81a40cadd961`)
- Deliverable revision: `54c7f6fe062720cbdf92e6bcd7476b697fc4afe1` (4-file bounded review-correction candidate; focused verification receipt committed separately at `fb2d8e616ad375ac7ccfa5f9000ba3340476c148`)
- Previous report: [`WP-0004 / 007`](./007_2026-11-14_research_eld-rd-carbon.md) (@ `068f3f83bb532160b56e00f071f8badd8d3f51b0`; `/007` candidate `29b2000265ae6068d9c86818622c81a40cadd961`; `/007` evidence `85ab359ba3348e6323b531c5f8c2677d6775687e`)
- Related or reviewed reports: Uninvolved Opus independent review `WP-0004 / 005` (`8f9a3281fa223d25447677b8ed8b873bf9e5cd01:docs/agent-reports/eld-rd-reviewer/WP-0004/005_2026-11-14_review_eld-rd-reviewer.md`, evidence/helpers `1787e942412f7a6981c7a6d730c44a83034ad0ef`); [`WP-0004 / 004`](./004_2026-11-14_research_eld-rd-carbon.md) (@ `fabddf72a80337a98ddb777c901edac11f9163fe`); [`WP-0004 / 002`](./002_2026-11-14_research_eld-rd-carbon.md) (@ `fef02d64aca2594e146930e4a0cb3ec18e355ed5`); `WP-0004 / 001` (@ `189d4cb444c5afde059e6e1d2bee37c8294509d0`); `WP-0004 / 003` (@ `c3215f75fc311c2e3c61a8ecc5da7d950f933157`)
- Status: ready-for-review
- Next owner: `eld-coordinator`

## Summary

Completed bounded `WP-0004 / 008` responsible-author review correction on `research/wp-0004-carbon-recovery` from clean base `068f3f83bb532160b56e00f071f8badd8d3f51b0` addressing uninvolved Opus (`eld-rd-reviewer`) `WP-0004 / 005` findings `RV-01`, `RV-02`, `RV-03`, and `RV-04` (`8f9a3281fa223d25447677b8ed8b873bf9e5cd01` / `1787e942412f7a6981c7a6d730c44a83034ad0ef`):

1. **`RV-01` (`E2` sign convention & mask leveling operator):** Defined positive angles throughout `E2` as CCW degrees (`+` = CCW, `-` = CW), candidate $\theta \in [-5.0^\circ, +5.0^\circ]$ (`101` points, `0.1°` step) as hypothesized CCW page skew, diagnostic leveling operator $M_\theta = M.\text{rotate}(-\theta, \text{resample}=\text{PIL.Image.Resampling.NEAREST}, \text{expand}=\text{True}, \text{fillcolor}=0)$, applied correction $\phi_{\text{applied}} = -\hat{\theta}$ via one `BILINEAR` resample on original RGB $I_{\text{in}}$, and error metrics $e_{\text{est}} = |\hat{\theta} - \theta_{\text{true}}|$ and $|\theta_{\text{res}}| = |\theta_{\text{true}} + \phi_{\text{applied}}|$.
2. **`RV-02` (Frozen PDF-to-RGB input path):** Froze `pypdfium2==5.15.2` (`PDFium 159.0.8149.0`, `page.render(scale=300.0 / 72.0).to_pil().convert("RGB")`) across `Q0`, `E1`, `E2`, and `E3`'s Stage 3B VLM baseline/fallback (`source_mode: "ocr_vlm"`), explicitly distinguishing `E3`'s raw-PDF text-layer gate (`source_mode: "pdf_text_layer"`) and stored XObject vs. PDFium-rendered dimensions without claiming pixel identity on `v2-skew` pages where PDFium resamples.
3. **`RV-03` (`evaluation/README.md`, `pypdfium2` bitmap-sizing arithmetic, & hybrid stamp areas):** Corrected `v1_raster300` size to `2550 x 3301` px, verified the exact `math.ceil(get_width() * scale)` / `math.ceil(get_height() * scale)` sizing mechanism in `pypdfium2/_helpers/page.py` (`L58/L65`, `L458–459`) and `pypdfium2_raw/bindings.py` (`L647/L657`), and aligned hybrid stamp descriptions with the measured `2.847%` (`F02` p1) and `2.989%` (`F08` p3) page-area ratios (`< 3%` of Letter page area, within the `< 5%` design bound).
4. **`RV-04` (Source-grounded `/004` errata):** Added [`research/carbon/reconciliation/03-review-response.md`](../../../../research/carbon/reconciliation/03-review-response.md) correcting all 8 factual prose misstatements in immutable `/004` (`fabddf72a80337a98ddb777c901edac11f9163fe`) and partitioning the `50` substring absences from `/005` `report-claims.json` into `7` valid slice/section notations, `6` inaccurate Markdown heading labels, and `37` nonexistent AST/constant/JSON labels (`7 + 6 + 37 = 50`).

This publication is **author correction only** (`ready-for-review`), not independent acceptance or corpus promotion. All `26` corpus PDFs (`40` pages), `8` source JSONs, `26` expected JSONs, `4` generation/check scripts, `5` existing manifests/receipts, and `3` historical Carbon reports (`/002`, `/004`, `/007`) are byte-for-byte unchanged (`98/100` base files identical). Uninvolved Opus closure (`WP-0004 / 009`) and coordinator disposition (`WP-0004 / 006`) follow.

## Objective and acceptance criteria

Per `7a21fdbb154f735656bbfc7602ad84e8d05b17ab:docs/kickoffs/WP-0004-eld-rd-carbon-review-correction.md` (amending `d216bdcd9aa65632ed1556899fda191c56cc2800` for UTC `2026-11-15` report date and `RV-03` bitmap-sizing causal precision):

1. Resolve `RV-01`, `RV-02`, and `RV-03` in `02-ranked-experiment-backlog.md` and `evaluation/README.md` while keeping the backlog at 3 proposals, `Q0` unperformed, and all corpus/source/expected/generator/manifest/report bytes untouched.
2. Provide a bounded source-grounded `RV-04` response/errata record (`03-review-response.md`) using verified AST symbols, JSON keys, and source values without editing immutable `/004`.
3. Freeze the 4-file candidate before executing a `dev`-only (`F01, F02, F04, F07` page 1, `v1`/`v2` only; zero `eval_holdout` reads, zero OCR/GPU/weights) CPU diagnostic proving blind angle estimation, clean `v1` byte-identical no-op, exact `0.0°` residual on both `+4.0°` and `-3.0°` `v2` controls, `pypdfium2` `math.ceil` sizing arithmetic, and Git-tree invariance across all `98` untouched tracked files.
4. Commit compact verification receipt `evaluation/manifests/review-correction-verification.json` and this reconciled `2026-11-15` canonical report separately (strictly six tracked paths total from `068f3f83bb532160b56e00f071f8badd8d3f51b0`), normal-push `research/wp-0004-carbon-recovery`, and verify `origin`.

## Change inventory

### 1. Deliverable diff (`068f3f83bb532160b56e00f071f8badd8d3f51b0..54c7f6fe062720cbdf92e6bcd7476b697fc4afe1` — 4 paths: 2 modified, 2 added)

| Action | Exact path | What changed and why | Exact verified headings / AST symbols |
| --- | --- | --- | --- |
| Modified | `evaluation/README.md` | Updated admission-status note to reflect `/005` scoped recommendation pending `/009` & `/006`; corrected `v1_raster300` size to `2550 x 3301` px; documented `MediaBox` (`792.0` vs. `792.24` pt), `pypdfium2` `math.ceil(get_height() * scale)` sizing arithmetic, and `v2_skew` stored-vs-rendered dimensions; aligned hybrid stamp areas to `2.847%` and `2.989%` (`< 3%`, within `< 5%` design bound). (`+6/-6`, `8,034` B, blob `98ba33a1dcd1769a46214e11ee233455a1f6df9e`, SHA-256 `25ea822a0c4258864030e3031e49d771b6547aeba5051328d3b763ed9c143ac5`). | `## 1. Purpose, Partition Discipline, and Explicit Limitations`, `## 3. Variant Matrix (\`26 PDFs / 40 Pages\`)` |
| Modified | `research/carbon/reconciliation/02-ranked-experiment-backlog.md` | Froze `pypdfium2==5.15.2` (`scale=300.0/72.0`) PDF-to-RGB input path and `math.ceil` sizing rule (`RV-02`/`RV-03`); defined `E2` CCW sign convention, $M_\theta = M.\text{rotate}(-\theta, \text{NEAREST}, \text{expand=True}, \text{fillcolor=0})$, $\phi_{\text{applied}} = -\hat{\theta}$, and error metrics (`RV-01`); distinguished `E3` raw-PDF text gate (`pdf_text_layer`) from `pypdfium2` VLM fallback (`ocr_vlm`) and aligned hybrid stamp percentages (`2.847%` / `2.989%`). (`+24/-14`, `25,676` B, blob `28f7e3e8ae4d6dc9cfaacd8758c60e6a187ddd81`, SHA-256 `9199735a676c3b82ee021429916996952bf8f2bf553a34ea8177994de1b91178`). | `## 2. Common Paired Comparison Protocol (\`E1\`–\`E3\`)`, `### Rank 2 — \`E2\`: Conditional Non-Binarizing Projection-Variance Deskew vs. Uncorrected Raster Pass-Through`, `### Rank 3 — \`E3\`: Two-Stage Conservative Zero-Image-Abstaining PDF Text-Layer Routing vs. Unconditional VLM OCR` |
| Added | `research/carbon/reconciliation/03-review-response.md` | Bounded author response summarizing `RV-01`–`RV-03` resolutions and recording source-grounded `RV-04` errata for immutable `/004` (8 prose corrections + `7 + 6 + 37 = 50` triage of `report-claims.json` substring absences). (`+65/-0`, `14,387` B, blob `96a2ba5973acc44856298b799bdd5410fa42cdaa`, SHA-256 `c0140af687d51fa202c80099c67b61ed5d1dd8315555966a1e2e2cd50eab9d72`). | `## 1. Resolution Summary for \`RV-01\`, \`RV-02\`, and \`RV-03\``, `## 2. Source-Grounded Errata for Immutable Report \`WP-0004 / 004\` (\`RV-04\`)`, `### 2.1 Eight Factual / Prose Misstatements in \`/004\` Corrected Against Pinned Source`, `### 2.2 Triage of the 50 Substring Absences Flagged in \`WP-0004 / 005\` \`report-claims.json\`` |
| Added | `research/carbon/reconciliation/verify_review_corrections.py` | Reproducible CPU-only `dev` diagnostic (`F01, F02, F04, F07` p1 `v1`/`v2`), `pypdfium2` `math.ceil` sizing verifier, Markdown relative-link checker, and frozen-candidate Git-tree invariance verifier; attributes the positive/negative skew residual check structure to `1787e942412f7a6981c7a6d730c44a83034ad0ef:docs/reviews/WP-0004/eld-rd-reviewer/helpers/e2_sign_diagnostic.py`. (`+476/-0`, `22,870` B, blob `4be3d46316befbc0a8c0dbb4ba3e0d0f09fa317b`, SHA-256 `c4932ec301f0c4ee1ad50c6642b10daa72aed5664f8a723980855e9f71920aa4`). | `otsu_foreground_mask`, `row_projection_variance_leveling`, `run_frozen_e2_gate`, `measure_empirical_residual_ccw_deg`, `render_frozen_pdfium_rgb`, `extract_stored_xobject_info`, `run_dev_e2_and_doc_checks`, `parse_tree`, `get_software_versions`, `main` |

### 2. Post-candidate evidence and report metadata committed separately (`2` added paths; `6` total paths from `068f3f83bb532160b56e00f071f8badd8d3f51b0`)

| Commit | Action | Exact path | What changed and why |
| --- | --- | --- | --- |
| `fb2d8e616ad375ac7ccfa5f9000ba3340476c148` | Added | `evaluation/manifests/review-correction-verification.json` | Focused decisive verification receipt (`14,496` B, blob `103b630e7d99a4652fe49641370a14a672969f34`, SHA-256 `7f2ec61e3b968716600c618d186f495314c96ccae3a9533055bd9fe6d26b164c`) executed against frozen candidate `54c7f6fe062720cbdf92e6bcd7476b697fc4afe1`. |
| Report publication commit (immediately atop `fb2d8e6...`) | Added | `docs/agent-reports/eld-rd-carbon/WP-0004/008_2026-11-15_research_eld-rd-carbon.md` | This concise `WP-0004 / 008` author correction report (records `54c7f6fe062720cbdf92e6bcd7476b697fc4afe1` and `fb2d8e616ad375ac7ccfa5f9000ba3340476c148`; does not claim to contain its own SHA). `INDEX.md` and `CURRENT.md` untouched. |

### 3. External effects & local pre-push refreeze note

- **Read-only Git fetch, local refreeze before push, & normal push:** Ran `git fetch origin` read-only (no merge) to inspect `d216bdcd9aa65632ed1556899fda191c56cc2800`, `8f9a3281fa223d25447677b8ed8b873bf9e5cd01`, `1787e942412f7a6981c7a6d730c44a83034ad0ef`, and post-midnight coordinator release `7a21fdbb154f735656bbfc7602ad84e8d05b17ab`. When `7a21fdb...` added `WP-0004-render-rounding-preflight.md` clarifying `pypdfium2`'s `math.ceil(c_float_extent * binary64_scale)` sizing arithmetic prior to any remote push, the unpublished local draft commits (`9bac4ce` / `837fc89`) were reset back to `068f3f83bb532160b56e00f071f8badd8d3f51b0`, the 4 candidate files were updated against installed `pypdfium2` source, refrozen at `54c7f6fe062720cbdf92e6bcd7476b697fc4afe1`, and re-verified cleanly at `fb2d8e616ad375ac7ccfa5f9000ba3340476c148` before normal fast-forward push of `research/wp-0004-carbon-recovery`.
- **Zero unauthorized effects:** Used existing owned `.venv` (`Python 3.12.10` + 3 hash-verified wheels); wrote one read-only inspection helper under ignored `.scratch/inspect_actual_source_facts.py`; zero package installs, downloads, services, databases, OCR/model/GPU runs, or edits to other branches/worktrees.

## Decisions and rationale

1. **Consistent CCW sign and leveling operator (`RV-01`):** Defining $\theta$ as hypothesized CCW page skew and $M_\theta = M.\text{rotate}(-\theta, \text{NEAREST}, \text{expand=True}, \text{fillcolor=0})$ makes $\hat{\theta}$ equal $\theta_{\text{true}}$ (`+4.0°` on `+4.0°` CCW fixtures; `-3.0°` on `-3.0°` CW fixtures) so $\phi_{\text{applied}} = -\hat{\theta}$ cancels both positive and negative skew instead of doubling skew to `-6.0°` on `-3.0°` fixtures.
2. **Single `pypdfium2` PDF-to-RGB contract (`RV-02`):** Raw PDF XObject extraction cannot render `v0-clean` (zero XObjects) and would silently drop vector body text on `v3-hybrid`. Freezing `pypdfium2==5.15.2` (`scale=300.0/72.0`) across all VLM OCR arms (`Q0`, `E1`, `E2`, and `E3` Stage 3B VLM baseline/fallback) guarantees identical pre-gate RGB buffers $I_{\text{in}}$ while documenting PDFium resampling on `v2-skew` pages (`2776 x 3471` px on `+4.0°`, `2720 x 3432` px on `-3.0°`) and pixel-exact `2550 x 3301` px reproduction on `v1-raster300`.
3. **Package-verified bitmap sizing & hybrid stamp area bounds (`RV-03`):** Direct inspection of `.venv/Lib/site-packages/pypdfium2/_helpers/page.py` (`L58/L65`, `L458–459`) and `pypdfium2_raw/bindings.py` (`L647/L657`) confirms `math.ceil(get_width() * scale)` / `math.ceil(get_height() * scale)`: `792.0 * (300.0 / 72.0) = 3300.0000000000005 -> ceil 3301` arises from Python binary64 `scale = 4.166666666666667` (exact `792.0` has zero `c_float` rounding), whereas `-3.0°` `823.44 pt` combines `FPDF_GetPageHeightF`'s `c_float(823.44) = 823.4400024414062` with binary64 `scale` (`3431.0000101725263 -> ceil 3432`). Active hybrid-stamp prose now cites exact `2.847%` and `2.989%` (`< 3%` of page area, within the `< 5%` design bound) without touching fixture bytes.
4. **Honest attribution of unchanged corpus checks:** Because `git ls-tree -r` proves all `26` PDFs, `8` sources, `26` expected JSONs, and `4` generator scripts at `54c7f6fe062720cbdf92e6bcd7476b697fc4afe1` match `29b2000265ae6068d9c86818622c81a40cadd961` verbatim, the `40/40` page visual inspection, `3,756+` arithmetic assertions, and two-run `53/53` deterministic regeneration remain attributed to `eld-rd-reviewer`'s `/005` review (`1787e942412f7a6981c7a6d730c44a83034ad0ef` / `8f9a3281fa223d25447677b8ed8b873bf9e5cd01`) rather than re-run.

## Verification

### 1. Blind `dev` `E2` & `pypdfium2` input-path results (`verify_review_corrections.py` on `54c7f6fe062720cbdf92e6bcd7476b697fc4afe1`)

| `dev` fixture page | Stored XObject px | Rendered `300/72` px | XObject exact? | Known $\theta_{\text{true}}$ | Blind $\hat{\theta}$ | $V(\hat{\theta})/V(0)$ | Triggered / $\phi_{\text{applied}}$ | Analytic / empirical residual |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `SYN-WO-01-v1-raster300.pdf#p1` (`F01`) | `2550 x 3301` | `2550 x 3301` | `True` | `0.0°` | `0.0°` | `1.0000` | `False` / `0.0°` (`0` byte diff) | `0.0°` / `0.0°` |
| `SYN-WO-01-v2-skew-pos4deg.pdf#p1` (`F01`) | `2776 x 3471` | `2776 x 3471` | `False` | `+4.0°` | `+4.0°` | `6.5750` | `True` / `-4.0°` (`3012 x 3657`) | `0.0°` / `0.0°` |
| `SYN-WO-02-v1-raster300.pdf#p1` (`F02`) | `2550 x 3301` | `2550 x 3301` | `True` | `0.0°` | `0.0°` | `1.0000` | `False` / `0.0°` (`0` byte diff) | `0.0°` / `0.0°` |
| `SYN-WO-02-v2-skew-neg3deg.pdf#p1` (`F02`) | `2720 x 3431` | `2720 x 3432` | `False` | `-3.0°` | `-3.0°` | `6.7632` | `True` / `+3.0°` (`2896 x 3570`) | `0.0°` / `0.0°` |
| `SYN-INV-01-v1-raster300.pdf#p1` (`F04`) | `2550 x 3301` | `2550 x 3301` | `True` | `0.0°` | `0.0°` | `1.0000` | `False` / `0.0°` (`0` byte diff) | `0.0°` / `0.0°` |
| `SYN-INV-01-v2-skew-neg3deg.pdf#p1` (`F04`) | `2720 x 3431` | `2720 x 3432` | `False` | `-3.0°` | `-3.0°` | `6.5802` | `True` / `+3.0°` (`2896 x 3570`) | `0.0°` / `0.0°` |
| `SYN-MP-01-v1-raster300.pdf#p1` (`F07`) | `2550 x 3301` | `2550 x 3301` | `True` | `0.0°` | `0.0°` | `1.0000` | `False` / `0.0°` (`0` byte diff) | `0.0°` / `0.0°` |
| `SYN-MP-01-v2-skew-pos4deg.pdf#p1` (`F07`) | `2776 x 3471` | `2776 x 3471` | `False` | `+4.0°` | `+4.0°` | `6.7206` | `True` / `-4.0°` (`3012 x 3657`) | `0.0°` / `0.0°` |

### 2. Executed commands vs. checks not re-run

| Check / exact command | Revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| Source AST/JSON/PDFium inspection (`.\.venv\Scripts\python.exe .scratch/inspect_actual_source_facts.py` + `inspect.getsource(pdfium.PdfPage.render)`) | Base `068f3f83bb532160b56e00f071f8badd8d3f51b0` | Verified all AST symbols, JSON keys, `MediaBox` extents, hybrid areas (`2.847%` / `2.989%`), `7 + 6 + 37 = 50` `/004` label partition, and `pypdfium2/_helpers/page.py` `L58/L65`, `L458–459` `math.ceil` sizing rule. | [`03-review-response.md`](../../../../research/carbon/reconciliation/03-review-response.md), [`review-correction-verification.json`](../../../../evaluation/manifests/review-correction-verification.json) |
| Decisive frozen-candidate verification (`.\.venv\Scripts\python.exe -W error research/carbon/reconciliation/verify_review_corrections.py --write-manifest evaluation/manifests/review-correction-verification.json`) | Frozen candidate `54c7f6fe062720cbdf92e6bcd7476b697fc4afe1` | `exit 0` (`DECISIVE_008_VERIFICATION_PASS`): `8` `dev` pages (`0` `eval_holdout` pages read), `4/4` `v1` byte-identical no-ops, `4/4` `v2` exact `0.0°` analytic & empirical residuals, `4/4` `math.ceil` sizing checks, `13` relative Markdown links verified, pure LF, and `98/100` base files identical (`26` PDFs, `8` sources, `26` expected JSONs, `4` scripts, `5` manifests/receipts, `3` historical Carbon reports). | [`review-correction-verification.json`](../../../../evaluation/manifests/review-correction-verification.json) (@ `fb2d8e616ad375ac7ccfa5f9000ba3340476c148`) |

- **Checks not run in `/008` and why:** `40`-page visual inspection, `3,756+` arithmetic assertions, and two-run `53`-file corpus regeneration were not repeated per kickoff instructions because all `64` corpus/source/expected/generator blobs are proven `100%` identical to `29b2000265ae6068d9c86818622c81a40cadd961` (independently verified by `eld-rd-reviewer` in `/005` @ `1787e942412f7a6981c7a6d730c44a83034ad0ef` / `8f9a3281fa223d25447677b8ed8b873bf9e5cd01`). `Q0` and `E1`–`E3` OCR/model/GPU runs remain unreleased.

## Review map

1. `git diff 068f3f83bb532160b56e00f071f8badd8d3f51b0..54c7f6fe062720cbdf92e6bcd7476b697fc4afe1` — Inspect the exact 4-file candidate diff ([`evaluation/README.md`](../../../../evaluation/README.md), [`02-ranked-experiment-backlog.md`](../../../../research/carbon/reconciliation/02-ranked-experiment-backlog.md), [`03-review-response.md`](../../../../research/carbon/reconciliation/03-review-response.md), [`verify_review_corrections.py`](../../../../research/carbon/reconciliation/verify_review_corrections.py)).
2. [`evaluation/manifests/review-correction-verification.json`](../../../../evaluation/manifests/review-correction-verification.json) (`fb2d8e616ad375ac7ccfa5f9000ba3340476c148`) — Inspect per-page `dev` blind `E2` estimates/residuals, RGB SHA-256 digests, `pypdfium2` `math.ceil` sizing products, and Git-blob invariance counts against `29b2000265ae6068d9c86818622c81a40cadd961` and `068f3f83bb532160b56e00f071f8badd8d3f51b0`.

## Risks, disagreements, and unfinished work

- **No substantive disagreement with `WP-0004 / 005`:** All four reviewer findings (`RV-01`–`RV-04`) and the coordinator's `RV-03` bitmap-sizing causal clarification were verified against actual repository and `pypdfium2==5.15.2` package source and resolved in full.
- **Pending independent closure (`WP-0004 / 009`) and coordinator disposition (`WP-0004 / 006`):** `verify_review_corrections.py` is a `dev`-only CPU specification diagnostic, not a production extractor or a completed `E2` benchmark; final R&D milestone acceptance awaits uninvolved Opus `eld-rd-reviewer` `/009` closure and `eld-coordinator` `/006` integration.

## Handoff

- **Next owner:** `eld-coordinator` (to bind uninvolved Opus `eld-rd-reviewer` for `WP-0004 / 009` closure, followed by `WP-0004 / 006` disposition).
- **Coordinator index inputs:**
  - **Branch:** `research/wp-0004-carbon-recovery`
  - **Base SHA (`/007` report):** `068f3f83bb532160b56e00f071f8badd8d3f51b0`
  - **Unchanged corpus candidate SHA:** `29b2000265ae6068d9c86818622c81a40cadd961`
  - **Frozen `/008` candidate SHA:** `54c7f6fe062720cbdf92e6bcd7476b697fc4afe1`
  - **Verification evidence SHA:** `fb2d8e616ad375ac7ccfa5f9000ba3340476c148`
  - **Exact reconciled report path:** `docs/agent-reports/eld-rd-carbon/WP-0004/008_2026-11-15_research_eld-rd-carbon.md`
  - **Publication receipt:** Committed immediately atop `fb2d8e616ad375ac7ccfa5f9000ba3340476c148` and normal-pushed to `origin`; exact report publication SHA and `git ls-remote` verification are supplied in the handoff message to `eld-coordinator`.
