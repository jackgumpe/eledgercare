# eLedgerCare Synthetic Evaluation Corpus (`WP-0004 / 004` Candidate)

- **Prepared By:** `eld-rd-carbon` (`research/wp-0004-carbon-recovery`, continued from preserved draft checkpoint `8fb7e3ca537b1710fe231dad0cf5d177c6e5d733` atop original base `fef02d64aca2594e146930e4a0cb3ec18e355ed5`)
- **Current Admission Status:** Corpus bytes and ground truth at `29b2000265ae6068d9c86818622c81a40cadd961` were independently verified by uninvolved Opus (`eld-rd-reviewer`, `WP-0004 / 005` @ `8f9a3281fa223d25447677b8ed8b873bf9e5cd01`), which recommended scoped starter-set admission while requesting bounded `RV-01`–`RV-03` backlog/README updates (`WP-0004 / 008`); **final milestone acceptance remains pending** `eld-rd-reviewer` (`WP-0004 / 009`) closure and `eld-coordinator` (`WP-0004 / 006`) disposition.
- **Corpus Bounds:** `8` fictional property-maintenance families (`F01`–`F08`), **`26` deterministic PDFs / `40` total pages** ([corpus-manifest.json](manifests/corpus-manifest.json)), `0` admitted public PDFs ([public-candidates.json](manifests/public-candidates.json) retains both Microsoft Form Recognizer candidates as `candidate_unadmitted` without copying their bytes).

---

## 1. Purpose, Partition Discipline, and Explicit Limitations

1. **Diagnostic Starter Set Only:** Eight families (`4` in `dev`, `4` in `eval_holdout`) are designed to falsify concrete OCR/extraction failure modes (dense small-type tables, mixed taxability, line discounts, signed negative credits, post-tax fees, prior-balance vs. current-invoice totals, multi-page table continuation, cross-page serial referential integrity, `300 DPI` pure rasters, signed rotational skew, and `< 3%`-area [`2.847%` / `2.989%`, within `< 5%` design bound] hybrid raster counterexamples). They **do not** establish population accuracy, statistical significance, real handwriting performance, camera-perspective robustness, or non-maintenance domain generalization.
2. **Fixed Test Partition (Not Blind to Corpus Author):**
   - `dev` (`4` families, `13` PDFs / `19` pages): `F01` (`SYN-WO-01`), `F02` (`SYN-WO-02` + hybrid `v3`), `F04` (`SYN-INV-01`), `F07` (`SYN-MP-01`, 3p).
   - `eval_holdout` (`4` families, `13` PDFs / `21` pages): `F03` (`SYN-WO-03`), `F05` (`SYN-INV-02`), `F06` (`SYN-INV-03`), `F08` (`SYN-MP-02`, 3p + hybrid `v3`).
   - Every derived variant stays in its source family and split. Because `eld-rd-carbon` authored the declarative source records, `eval_holdout` is a **fixed test partition** rather than blind validation to its author. Future experiment runners must tune prompts/thresholds on `dev` only and never read `evaluation/synthetic/expected/*` for `F03, F05, F06, F08` during development.
3. **Separable Inputs vs. Ground Truth:** Input PDFs live solely under `evaluation/synthetic/pdfs/<family_id>/`, cleanly separated from declarative inputs (`evaluation/synthetic/sources/`) and expected answers (`evaluation/synthetic/expected/`). Product projects (`ELedgerCare.slnx`) must never reference `evaluation/` or `research/`.

---

## 2. Corpus Accounting Convention (`eledgercare_synthetic_decimal_round_half_up_v1`)

All four invoice families (`F04`, `F05`, `F06`, `F07`) follow an explicit, on-page printed `decimal.Decimal` (`ROUND_HALF_UP` to `$0.01`) convention (declared as **this synthetic corpus's rule**, not a claim of universal tax/GAAP law):

- `gross_line = round_half_up(quantity * unit_price, 0.01)`
- `line_discount = round_half_up(gross_line * discount_rate, 0.01)` *(both `Disc%` and `Disc Amt` are printed visibly on every row)*
- `net_line = gross_line - line_discount` *(signed negative credit rows carry `0.00%` discount and `Tax = N`)*
- `subtotal = sum(net_line for all rows)`
- `taxable_subtotal = sum(net_line for rows visibly marked Tax = T)` *(assert `taxable_subtotal >= 0.00`)*
- `tax_amount = round_half_up(taxable_subtotal * tax_rate, 0.01)`
- `invoice_total = subtotal + tax_amount + sum(non_taxable_fees)`
- `amount_due = invoice_total + previous_balance - payments_credits_applied`

Both canonical normalized strings (`"794.67"`, `"-25.00"`) and literal printed strings (`"$794.67"`, `"-$25.00"`) are retained in `evaluation/synthetic/expected/*_expected.json`, alongside explicit `expected_absences` for blank optional boxes.

---

## 3. Variant Matrix (`26 PDFs / 40 Pages`)

| Variant Kind | Count | Modality & Transform Specification |
| --- | ---: | --- |
| `v0_clean` | `8` PDFs / `12` pages | Deterministic PDF 1.4 vector originals (`evaluation/generation/pdf_writer.py`, `MediaBox [0, 0, 612.0, 792.0]` pt) using standard PDF Base-14 Type1 font names (`/Helvetica`, `/Helvetica-Bold`, `/Courier`, `/Courier-Bold`, `/WinAnsiEncoding`) with zero embedded third-party font binaries and zero image XObjects (`2550 x 3301` RGB px/page when rendered by `pypdfium2==5.15.2` at `scale=300.0/72.0`, since `math.ceil(792.0 * (300.0 / 72.0)) = math.ceil(3300.0000000000005) = 3301`). |
| `v1_raster300` | `8` PDFs / `12` pages | Pure image-only PDFs (`0` `/Font` objects, `0` `BT..ET` text operators) rendered from `v0_clean` via `pypdfium2==5.15.2` (`PDFium 159.0.8149.0`, `scale=300.0/72.0`) at **`2550 x 3301` RGB pixels/page** (`pypdfium2/_helpers/page.py` L458–459 computes `math.ceil(get_height() * scale)` where exact `792.0` times Python binary64 `300.0 / 72.0 = 4.166666666666667` equals `3300.0000000000005`) and wrapped by `build_image_only_pdf` in `MediaBox [0, 0, 612.0, 792.24]` pt (`3301 * 72 / 300 = 792.24`), which re-renders pixel-identically at **`2550 x 3301` px** (`c_float(792.24) * scale = 3300.999959309896`, ceiling `3301`) under the frozen `pypdfium2` VLM input contract. |
| `v2_skew` | `8` PDFs / `12` pages | Pure image-only `300 DPI` PDFs rotated from `v1_raster300` via `Pillow==13.0.0` `Image.rotate(angle, resample=BILINEAR, expand=True, fillcolor=(255,255,255))`: **`+4.0°` CCW** on odd families (`F01, F03, F05, F07`; stored XObject `2776 x 3471` px in `MediaBox [0, 0, 666.24, 833.04]` pt, `pypdfium2` `300/72` render `2776 x 3471` px resampled via `math.ceil(3470.999908447266) = 3471`) and **`-3.0°` CW** on even families (`F02, F04, F06, F08`; stored XObject `2720 x 3431` px in `MediaBox [0, 0, 652.80, 823.44]` pt, `pypdfium2` `300/72` render **`2720 x 3432` px** resampled since `FPDF_GetPageHeightF`'s `c_float(823.44) = 823.4400024414062` times Python `scale` equals `3431.0000101725263`, ceiling `3432`). See [02-ranked-experiment-backlog.md](../research/carbon/reconciliation/02-ranked-experiment-backlog.md) `§2.2` for the frozen `pypdfium2` OCR input contract vs. stored XObject dimensions. |
| `v3_hybrid` | `2` PDFs / `4` pages | Linked hybrid negative controls for `E3` (`MediaBox [0, 0, 612.0, 792.0]` pt): `SYN-WO-02-v3-hybrid-note` on `F02` p1 in `dev` (`[40, 62, 340, 108]` pt = `13,800 / 484,704 sq pt` = **`2.847%`** page area, `1250 x 192` px stamp XObject) and `SYN-MP-02-v3-hybrid-stamp` on `F08` p3 in `eval_holdout` (`[40, 62, 355, 108]` pt = `14,490 / 484,704 sq pt` = **`2.989%`** page area, `1312 x 192` px stamp XObject), each embedding a **`< 3%`-page-area** (within `< 5%` design bound) `300 DPI` RGB raster addendum/stamp whose text is absent from the PDF `BT..ET` stream. |

---

## 4. Reproducible CPU Commands (No GPU / No Model Weights Required)

Using a scoped Python `3.12.10` virtual environment with the three hash-pinned CPU wheels recorded in [tooling-provenance.json](manifests/tooling-provenance.json) (`pypdfium2==5.15.2`, `Pillow==13.0.0`, `pypdf==7.1.0`):

```powershell
# 1. Regenerate all 26 PDFs, 26 expected JSONs, and corpus-manifest.json
.\.venv\Scripts\python.exe evaluation/generation/generate_corpus.py

# 2. Run independent stdlib Decimal arithmetic & cross-page serial author check (Gate A)
.\.venv\Scripts\python.exe evaluation/generation/verify_arithmetic_independent.py

# 3. Verify hashes, Git blob OIDs, PDF text/image-only/hybrid invariants, and 2-run byte identity
.\.venv\Scripts\python.exe evaluation/generation/verify_corpus_integrity.py --check-regeneration .scratch/regen_verify
```
