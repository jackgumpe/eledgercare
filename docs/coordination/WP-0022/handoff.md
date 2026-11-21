# WP-0022 (Proposed): Frozen Saved-Frame Reader on Rendered versus WinRT Word Positions

**Status & Authorization:** Jack and both cloud advisers approved this bounded research handoff on November 21, 2026 for local `eld-coordinator` execution on Windows (`jackgumpe/eledgercare`, branch `coordination/bootstrap`). Current `INDEX.md` ends at `WP-0021` (`81ea3627de2a580130c4bd8d73515063515864b0`); `WP-0022` is a **proposed** packet designation, not an active reservation or session launch. Refresh `HEAD`, read `START_HERE.md`, `AGENTS.md`, `CURRENT.md`, and `INDEX.md`, check for any intervening reservation, and reserve the next available packet number, isolated worktrees, custodian/implementer/independent-reviewer lanes, and report slots under repository policy. Cloud advisers participated in experimental design and may not act as the independent non-author reviewer.

**Single Bounded Question:** Does the exact frozen `WP-0021` saved-frame + word-position reader survive real `Windows.Media.Ocr.OcrEngine` output on interrupted multi-page property/contractor ledgers when ownership is scored separately from character transcription, and if any row fails, does the failure occur in WinRT observation, frozen layout/line-parsing rules, or saved-frame parent memory?

---

## 1. Freeze the Comparison (Zero Mid-Trial Reader Changes)

1. **Unmodified WP-0021 Reader:** Pin the exact `WP-0021` saved-frame + word-position reader revision and every internal heuristic—specifically including its **$3\text{-pt}$ left-edge ($x_0$) saved-header tolerance** and its rule treating the **last word of a body line as the candidate amount**. Do **not** switch to right-edge ($x_1$) alignment, widen tolerances, alter wrapped-line candidate extraction, or add `SPDB` matrix memory during this packet.
2. **Measure WinRT Geometry Rather Than Assuming It:** Microsoft's `Windows.Media.Ocr` API documents recognized `OcrLine` groupings, `OcrWord.Text` strings, and pixel `BoundingRect` rectangles; it promises neither a tight ink contour nor a specific public line-grouping algorithm. Project both renderer word rectangles and WinRT pixel rectangles into the identical top-left PDF-point coordinate frame ($612 \times 792\text{ pt}$) using the same page raster dimensions, hold the reader fixed, and *measure* where the two inputs first diverge.
3. **Same Raster, Same Detected Grid, Paired Input Replay:**
   - Record Windows OS build, `Windows.Media.Ocr` DLL/resource digests, language (`en-US`), raster pixel dimensions, pixel format, reader commit SHA, and scorer SHA.
   - Run `Windows.Media.Ocr.OcrEngine` **once** per fresh page and archive its immutable raw lines, ordered words, pixel rectangles, projected PDF-point rectangles, and source-word IDs.
   - Run table-grid detection **once** per page so both arms receive the byte-identical page raster and derived grid geometry:
     - **Arm R (Rendered Input):** Replay the frozen reader using renderer-supplied lines, words, and PDF-point word rectangles.
     - **Arm W (WinRT Input):** Replay the exact same frozen reader using actual WinRT lines, words, and projected PDF-point word rectangles.
   - Freeze all predictions and blind pre-key file digests for both arms before releasing truth keys.

---

## 2. Fresh Custodian Suite & Blind Custody

Before any reader execution, an uninvolved custodian creates fresh synthetic multi-page property/contractor ledgers ($300\text{ DPI}$ RGB rasters, $612 \times 792\text{ pt}$) and commits separately to input raster digests and sealed truth keys. Do not reuse `WP-0021` pilot pages, `H`, `A`, `LIFT`, or `VALVE` as fresh test pages, and keep `Packet B` sealed.

Include balanced, pre-counted test rows covering:
- **Variable-width right-aligned amounts:** Narrow and wide numbers sharing a right margin while differing in left-edge $x_0$ (e.g., `9.00` vs. `12,450.00`, plus parenthetical/negative amounts);
- **Wrapped multi-line descriptions:** 2-to-3 line body descriptions paired with row amounts (testing body-line grouping and last-word candidate selection in both arms);
- **Parent returns & rapid re-interruptions:** Single-row parent ledger resumptions, cross-page child continuations with missing/corrupted headers, and `Parent` $\to$ `Child A` $\to$ `1-Row Parent` $\to$ `Child B` $\to$ `Parent` sequences;
- **Same-height right-margin numeric notes:** Margin numbers placed level with table rows opposite **both** populated `Amount` cells and **explicitly empty** `Amount` cells;
- **Ambiguous continuations & explicit blanks:** Indistinguishable post-break rows where abstention/review is required, alongside true empty cells.

---

## 3. Score Ownership Separately from Transcription

Link evaluated cells and body rows to ground-truth targets by spatial region and source-word provenance so recognition typos and ledger-ownership errors never mask each other:

| Dimension | Scoring Rule & Required Breakdown |
| --- | --- |
| **1. Ledger Ownership (Primary Scope Metric)** | Score whether the emitted field is bound to the exact expected `(property/parent, table_scope, column_role)` or rightly left for review on ambiguous rows. If WinRT reads `1,45O.00` for `1,450.00` and the frozen reader attaches that literal word reference to the right resumed parent ledger and column, record **Ownership = Correct** and **Transcription = Mismatch** separately. |
| **2. Silent Margin-to-Blank Capture** | If WinRT reads `1,450.00` accurately from a right-margin note and the reader posts it into an explicitly empty `Amount` cell (or wrong row) with `flagged == false`, score **Ownership = Silent Wrong Assignment**. Never credit string equality drawn from the wrong spatial source. |
| **3. Blank vs. Missing Source Words** | Separate positively preserved empty cells from target positions where WinRT returned zero intersecting words or split/merged tokens. Never convert missing OCR evidence into an unflagged blank value. |
| **4. Per-Arm Counts** | For both Arm R and Arm W, report: exact ownership assignments, silent wrong assignments, explicit abstentions/flags (on unambiguous vs. truly ambiguous rows), margin-note false captures (opposite populated vs. empty cells), preserved blanks, transcription-only mismatches on rightly owned values, and total elapsed CPU ms/page. |

---

## 4. Complete $2 \times 2$ Paired Outcome Matrix & First-Divergence Trace

Classify every target evaluation row across `(Arm R, Arm W)` without treating the matrix cell itself as a pre-assumed root-cause verdict:

| Paired Outcome (`Arm R` vs. `Arm W`) | Observational Meaning & Required Diagnostic Inspection |
| --- | --- |
| **`Arm R` Pass / `Arm W` Pass** | Frozen saved-frame reader survives end-to-end on both rendered and real WinRT observations. |
| **`Arm R` Pass / `Arm W` Fail** | Rendered geometry succeeded while WinRT output failed. Record the **first observable difference** between R and W on that row/page: missing or split/merged word, `OcrLine` grouping change, text discrepancy, or projected rectangle shift ($\Delta x_0, \Delta y_0, \Delta x_1, \Delta y_1$). |
| **`Arm R` Fail / `Arm W` Pass** | Rendered input failed while WinRT input succeeded. Inspect how WinRT's line segmentation, word splitting, or bounding rectangle placement satisfied a frozen reader rule (such as last-word candidate selection or $3\text{-pt}$ $x_0$ alignment) that rendered boxes violated. |
| **`Arm R` Fail / `Arm W` Fail** | Both inputs failed on the same target. **Do not assume parent memory failed.** Inspect whether the saved-frame stack still held the right parent while a deterministic extraction/alignment rule failed in both arms (e.g., right-aligned `9.00` missing the $3\text{-pt}$ left-edge header tolerance, or a wrapped description violating the last-word-of-body-line assumption), versus actual wrong-frame restoration. |

---

## 5. Mandatory Witness-Row Trace, One-Study Cutoff & Disposition Rule

This lane enforces a **one-study cutoff**: run this single paired Windows replay through non-author independent reproduction and stop at coordinator disposition.

1. **Witness-Row Trace Requirement:** If *any* target row fails in Arm W (or both arms), aggregate metrics alone are insufficient. The research and review reports must include at least one complete **witness-row trace** per failure pattern showing:
   - Page/row locator, ground-truth scope, and spatial target box;
   - Exact Arm R and Arm W lines, ordered words, and PDF-point boxes (`[x0, y0, x1, y1]`);
   - Candidate-amount word selection and measured header-alignment delta ($\Delta x_0$);
   - Exact **saved-frame stack state immediately before and immediately after** the row was processed.
2. **Pre-Registered Decision Gate:**
   - **End-to-End Survival:** Retain the discrete saved-frame reader for the tested Windows scout layouts, keep `SPDB` matrix memory parked, and **return R&D focus immediately to the Baidu Unlimited-OCR 2 neural architecture redesign**.
   - **Rule Defect with Intact Memory:** If witness traces show the active/saved frame stack still held the correct parent while the $3\text{-pt}$ left-edge rule or last-word-of-body-line rule rejected or mispicked the row candidate, record a **layout-rule defect** (do not schedule `SPDB`).
   - **Strict `SPDB` Trigger:** Recommend testing `SPDB` matrix memory on Windows **only** if a witness trace demonstrates that the parent ledger was captured, an observable return cue was present in the WinRT input, and the saved-frame reader still restored or retained the wrong ledger in frame state.

No GPU lease, Baidu inference, model training, `SPDB` implementation, unsealing of `Packet B`, or production `src/`/`web/`/`workers/` modifications are part of this packet.

---

## Appendix: Copy-Paste Launch Instruction for Local Coordinator

> I approve the attached `WP-0022-Rendered-vs-WinRT-Scope-Survival.md` handoff for execution under current repository policy. Refresh `HEAD`, verify `WP-0021` is the latest indexed packet, and reserve the next packet with isolated worktrees and non-author independent review custody. Keep the `WP-0021` saved-frame + word-position reader completely frozen (including its 3-pt left-edge tolerance and last-word-of-body-line rule). Have an uninvolved custodian commit fresh multi-page nested ledgers covering variable-width right-aligned amounts, wrapped descriptions, single-row/sibling parent returns, and same-height margin notes opposite both populated and empty cells. Run Windows OCR once per page, replay the identical raster, detected grid, and frozen reader on rendered versus WinRT word boxes, score ownership separately from transcription across the full 2x2 paired matrix, include full before/after stack traces on any witness failure, and stop after coordinator disposition. Keep `SPDB` matrix memory and production code untouched.