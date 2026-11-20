# Engineering Review: `Windows-OCR-Fixed-Crop-Trial.md`

## 1. Verdict & Strategic Fit with the Architecture Redesign

Cloud Astra's specification asks the right final closure question for standalone Windows OCR after WP-0018 proved that $8/8$ Packet H and $92/94$ Packet A unflagged critical errors already existed inside raw WinRT output. Testing whether isolated, unscaled (`1x`) crops fix `Windows.Media.Ocr` separates **page-layout context interference** from **fundamental recognizer limits**.

However, **six targeted modifications are advisable before execution** (plus removing the duplicated prompt text accidentally appended to the bottom of the first uploaded file). Without these adjustments, the trial risks:
1. Spending a full multi-agent fixture-creation and blind-custody cycle even if `1x` crops fail immediately on known H/A examples;
2. Dragging black table grid rules into tight cell crops and breaking WinRT line detection;
3. Failing the $30\text{ pages/min}$ gate due to PowerShell subprocess/PNG disk overhead rather than actual OCR time; and
4. Leaving role custody ambiguous under repository policy.

Strategically, adding a **Stage 1 Go/No-Go Stop-Loss Gate** protects your return to the **Neural Engine & Architecture Redesign** track: if `1x` crops still misread `O/0` and `I/1` on exposed H and A (which is plausible given identical $300\text{-DPI}$ glyph pixels and WinRT's `en-US` prior), the lane terminates cleanly in Stage 1 with a definitive answer instead of burning extra sessions building 12 fresh pages.

---

## 2. What Astra's Draft Gets Right (Retained Intact)

- **Same-Installation Control:** Re-running full-page Windows OCR on the current Windows build avoids mistaking OS/WinRT package updates for crop improvements.
- **Strict `1x` Pixel Isolation:** Prohibiting scaling, thresholding, deskewing, and character rewriting cleanly isolates layout-segmentation effects inside `Windows.Media.Ocr`.
- **Pre-Unblinding Rule Freeze & Hard Safety Gate:** Requiring $\ge 1$ recovered critical ID, $0$ newly wrong critical IDs, intact blank semantics, and $\ge 30\text{ pages/min}$—while counting flagging separately from correction—prevents post-hoc cherry-picking.

---

## 3. Six Recommended Modifications (Applied in the Revised Spec)

| Area | Gap in Original Draft | Modification in Revised Spec |
| --- | --- | --- |
| **1. Stage 1 Stop-Loss Gate** | Builds and runs two fresh 6-page blind form families unconditionally, and checks only 4 witness fields in Stage 1 instead of checking all H/A baseline-correct IDs for regressions. | Evaluates the 4 witness fields, the 5 zero-word A cells, **and** full H/A critical-ID regression counts in Stage 1. **Stops and closes at Stage 1** if no frozen rule achieves net recovery $\ge 1$ with $0$ `right -> wrong` critical flips on exposed H/A. |
| **2. Table Cell Border Clipping** | "Fixed-padding integer crop... no border removal" pulls black $1\text{--}2\text{ px}$ table grid lines into cell crop edges, causing WinRT to merge strokes with borders or drop text. | Keeps pixel values $100\%$ untouched, while distinguishing **outward prose padding** from **cell-interior clipping** (cropping inside `visual.py:rule_tables` grid bounds by a fixed integer inset so border ink stays outside the crop). |
| **3. Zero-Word Cell Selection** | Assumes a deterministic selector cannot find the 5 nonempty A cells that had zero intersecting WinRT words. | Keeps all 5 in the denominator and forbids truth boxes, while allowing deterministic **grid-column selection** (selecting empty cells inside columns where neighboring rows carry IDs, tested against true blank cells). |
| **4. Persistent WinRT Execution** | Spawning PowerShell (`recognize.ps1`) or writing/hashing temporary PNGs per crop on disk adds hundreds of ms of OS I/O overhead and skews the $30\text{ pages/min}$ gate. | Requires both arms to run in a single persistent warm WinRT worker process per run using in-memory bitmap slicing (`SoftwareBitmap` / raw pixel views), verifying crop SHA-256 digests without disk-PNG bottlenecks. |
| **5. WinRT Zero-Confidence Reality & Hybrid Signal** | WinRT `OcrWord` exposes **no confidence score**, making silent text replacement between two valid-looking IDs dangerous unless triggered by structural defects; misses hybrid routing telemetry. | Keeps silent-replacement rules strict for the gate, and logs a **Full-vs-Crop Self-Disagreement Matrix** ($T_{\text{full}} \neq T_{\text{crop}}$) so the main neural architecture knows whether crop disagreement catches silent WinRT errors. |
| **6. Explicit Repo Role Custody** | Calls for "an uninvolved custodian" without mapping to `jackgumpe/eledgercare`'s active 4-role roster (`eld-coordinator`, `eld-rd-astra`, `eld-rd-carbon`, `eld-rd-reviewer`). | Assigns Stage 2 fixture commit and key escrow to `eld-coordinator`, blind selector/crop implementation to `eld-rd-astra` + `eld-rd-carbon`, and independent AB/BA execution + scoring to `eld-rd-reviewer` (Opus). |

---

## 4. Updated Approval Prompt (Ready to Copy-Paste to Local Coordinator)

> I approve the attached `Windows-OCR-Fixed-Crop-Trial.md` for execution. Reserve the next packet under current repo policy and run it through independent review and coordinator disposition. First establish the post-update full-page control on the current Windows installation inside a persistent warm WinRT worker. Run Stage 1 on H and A (the named witness fields, the five zero-word A cells, and full H/A critical-ID regression checks) using unmodified `1x` source pixels with grid-clipped cell interiors, and freeze the deterministic selector and merge rules. Enforce the Stage 1 Go/No-Go gate: proceed to Stage 2 fresh synthetic forms (`eld-coordinator` key custody, non-author `eld-rd-reviewer` execution) only if the frozen Stage 1 policy achieves net critical recovery with zero `right -> wrong` critical regressions on exposed H/A; otherwise close cleanly at Stage 1 and report the diagnostic crop findings. Stop after disposition with exact recoveries, regressions, full-vs-crop disagreement counts, and added ms/page. No production changes.