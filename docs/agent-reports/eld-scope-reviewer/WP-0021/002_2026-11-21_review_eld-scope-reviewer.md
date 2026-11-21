# WP-0021 /002 · Independent review of saved-frame scope binding

**Accepted as a synthetic feasibility result.** Adding observed word left edges raised exact page-two bindings from 4/10 to 10/10 on identifiable rows. Both modes abstained on both indistinguishable continuations. The combined mode restored the correct parent on all five identifiable parent rows. The relevant next experiment is a fresh synthetic run with actual Windows OCR line grouping and word boxes. This pilot supplies no evidence for a matrix-memory advantage.

| Report metadata | Value |
| --- | --- |
| Author and publisher | eld-scope-reviewer, independent non-author |
| Report path | `docs/agent-reports/eld-scope-reviewer/WP-0021/002_2026-11-21_review_eld-scope-reviewer.md` |
| Reservation | [INDEX at assigned base](https://github.com/jackgumpe/eledgercare/blob/7a8b0a8b0ffbf2b6670584eff768a0513074c1dd/INDEX.md#wp-0021-windows-ledger-scope-feasibility) |
| Category, UTC, status | review · 2026-11-21T05:31:02Z · accepted within the declared gate |
| Actual execution | Fresh native Codex session `/root/scope21_review`, thread `01a1fc8c-938e-72e3-825e-defaf68c9b3e`. Requested xhigh. Backend identifier and applied effort unexposed. Windows, CPython 3.12.10, Git 2.55.0.windows.1, Pillow 13.0.0, NumPy 2.2.6. |
| Repo, branch, worktree | Private jackgumpe/eledgercare · `review/wp-0021-scope-baseline` · `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/scope21-review` |
| Reviewer base / deliverable / evidence | `7a8b0a8b0ffbf2b6670584eff768a0513074c1dd` / `c8fcbc301c88c144f4e9eda48b097b15def42cb5` / `8562dab962becb4d809caad78f4561abdd894120` |
| Reviewed candidate and publication | `613a5ff92e9dd6783b8950529fbda76f6c21e9d3` · [Author /001](https://github.com/jackgumpe/eledgercare/blob/24eb1dd1afa6925d07571cd9ff86116c01572537/docs/agent-reports/eld-scope-author/WP-0021/001_2026-11-21_research_eld-scope-author.md) |
| Previous report / next owner | First WP-0021 report by this reviewer. eld-coordinator owns the disposition and /003. |

## Decisive results

Each exact binding requires the original property, unit and their references, table scope, Amount role, unmodified literal and source pointer. The coordinator's entire scorer result, each case and both aggregate counts reproduced. [Independent row decisions](../../../reviews/WP-0021/evidence/reconciliation.json) · [Published scores](https://github.com/jackgumpe/eledgercare/blob/66e9cb7da495f8d65bf6eecb4db7b2b8be3e7579/docs/coordination/WP-0021/primary-scores.json)

| Unit of measurement | Grid only | Grid and word left edges |
| --- | ---: | ---: |
| Page-one setup rows exactly bound | 20/20 | 20/20 |
| Identifiable page-two scope and context exactly bound | 4/10 | 10/10 |
| Identifiable resumed-parent rows exactly bound | 2/5 | 5/5 |
| Page-two rows abstained, including ambiguous rows | 8/12 | 2/12 |
| Opposite-scope twins with flagged abstention | 2/2 | 2/2 |
| Silent wrong assignments on registered page-two rows | 0 | 0 |
| Exact page-two amount literals and references, including abstentions | 12/12 | 12/12 |
| Exact page-two body words and references, including amounts | 45/45 | 45/45 |

All three rows with an omitted third source word retained their three actual tokens. The saved property and unit references resolved to the page-one “Harbor View” and “2B” banner values on every row. No blank-cell or missing-ink classification was evaluated. In each mode all twelve page-two decision prefixes matched the corresponding complete-output prefix. Replacing all 45 body literals while retaining their original boxes and source references preserved scope and the complete decision trace. The in-memory reader ran under a guard preventing file, network and process access during binding. Source inspection confirmed that the binder receives a document and mode, uses typed banners and headers, and creates a new frame list per document. [Reader source](https://github.com/jackgumpe/eledgercare/blob/613a5ff92e9dd6783b8950529fbda76f6c21e9d3/docs/research/WP-0021/read_scope.py) · [Replay evidence](../../../reviews/WP-0021/evidence/prediction-replay.json)

## Geometry and failure evidence

The original detector reproduced all ten exported pages. D03 retained two four-column page-two grids. D11 supplied only two horizontal boundaries per band, below the detector's minimum of three. D19's nearby tables shared outer margins, so their horizontal rules grouped together and none of the interior verticals covered the required combined height. The detector returned no grid. Independent raster controls also reproduced a partially merged grid when one internal divider remained common. The idealized word positions supplied the six extra bindings on D11 and D19. [Detector evidence](../../../reviews/WP-0021/evidence/detector.json)

D27 and D32 have opposite semantic labels and byte-identical complete word/grid observations. In both modes, their complete predictions were identical. Their second-page **rasters do differ**. The gray fill changes 42,508 grayscale pixels, including 72 mask bits at the detector's `<215` threshold. The aggregate detected grids stay identical. An initial reviewer assertion requiring full threshold-mask equality failed. The corrected, frozen checker records the raster differences and tests identity at the binder's actual input. [Ambiguity evidence](../../../reviews/WP-0021/evidence/reconciliation.json)

A separate reviewer control kept one amount-like word on each D03 row and placed its entire box in the right margin beyond every detected table. Grid-only still bound all four lines without a flag because it associates rows with a grid using vertical location alone. Combined mode abstained on all four. The control is outside the preregistered twelve-row denominator. The zero-silent-error result applies only to those registered rows. [Per-mode control results](../../../reviews/WP-0021/evidence/prediction-replay.json)

## Reproduction and handoff

I independently executed the unmodified detector from `a0e738bc03e515999659dda09c5ee76d08fb37df` and reader from its frozen Git source on renamed input files in owned scratch. The /001 author report and its ten audit rows agree with the independent scope counts, full-file digests and source-word totals. All ten full outputs matched the [author prediction freeze](https://github.com/jackgumpe/eledgercare/commit/263f7263d654faedb17be096699c47d6050315ab) and [coordinator prediction freeze](https://github.com/jackgumpe/eledgercare/commit/91b8f778cc4bea4c804a0809cdff423e4b107fa1). After their freezes I inspected the supplied generator and answer key and regenerated every input byte, all ten raster PNGs and the full semantic key. Six independent detector controls and all nine author unit checks passed. The supplied PDF digest also matched. [Commands, revisions and failure evidence](../../../reviews/WP-0021/evidence/commands.md) · [Regenerated hashes](../../../reviews/WP-0021/evidence/regeneration.json)

The generator supplies typeface-derived word boxes, correct line grouping, one token per occupied cell and an observed amount in the final occupied column. Real OCR may split a token, misgroup columns or shift its left edge by more than the three-point tolerance. A fresh evaluation can measure how often actual WinRT receipts support the same binding, including off-grid text, before comparing memory designs. This two-level pilot ran no live OCR, GPU work, protected Packet B, product integration, matrix comparison, latency benchmark or held-out 24-document suite.

The reviewer did not author the reader, generator, detector or official scorer. All reviewer source changes are under `docs/reviews/WP-0021/` in `PLAN.md`, `replay_detector.py`, `replay_reader.py` and `reconcile.py`. Subsequent evidence adds `evidence/commands.md`, `detector.json`, `prediction-replay.json`, `reconciliation.json` and `regeneration.json` in that evidence directory. The only other new path is this report. Local scratch is retained at `../wp0021-data/reviewer`. The evidence tip was verified on the owned remote branch before this report. The coordinator receives the separate report-publication receipt for its disposition. [Reviewer deliverable](https://github.com/jackgumpe/eledgercare/commit/c8fcbc301c88c144f4e9eda48b097b15def42cb5) · [Independent evidence](https://github.com/jackgumpe/eledgercare/commit/8562dab962becb4d809caad78f4561abdd894120)
