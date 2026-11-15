# Deterministic Synthetic Corpus Plan and Public Candidate Audit (WP-0004 / 002)

> **Scope & Ownership Note:** Per `docs/kickoffs/WP-0004-eld-rd-carbon.md`, actual fixture materialization and shared manifest emission in `evaluation/` are reserved for **`WP-0004 / 004`** after both independent initial assessments (`WP-0004 / 001` and `WP-0004 / 002`) are published and `eld-coordinator` pins the Astra/Carbon exchange (`WP-0004 / 003`). No public sample is admitted in this packet, and no adjacent model JSON is accepted as ground truth.

---

## 1. Eight-Family Source-First Synthetic Maintenance Corpus Plan

This initial starter set comprises **eight synthetic property-maintenance document families** (`F01`–`F08`: 3 single-page work orders, 3 single-page invoices, 2 multi-page documents). It is designed to falsify layout, arithmetic, page-ordering, and routing failure modes—**not** to claim statistical benchmark significance or generalize to handwriting, clinical records, or legal contracts.

All entities use strictly fictional property/vendor names, reserved `555-01XX` telephone numbers, and `.example` domains (`RFC 2606`) so zero real PII or third-party company identities appear. Printed script/italic fonts must **not** be used to claim handwriting performance.

| Family ID | Fixture Prefix | Category & Pages | Fictional Scenario & Distinct Layout Structure | Targeted Failure Modes & Ground-Truth Elements | Assigned Split |
| --- | --- | --- | --- | --- | --- |
| `F01` | `SYN-WO-01` | Single-page Work Order (1p) | **HVAC Corrective Dispatch** (*Cedar Hollow Apartments, Bldg B, Unit 204*): Two-column top metadata header, printed checkbox status row (`Priority: Urgent [X]`, `Permission to Enter: Yes [X]`, `Pets on Premises: No [ ]`), technician labor time-in/time-out table, internal stock parts list (quantities & part SKUs, no billing totals). | Side-by-side column reading-order confusion, checkbox state association, alphanumeric part SKU fidelity (`CAP-45-5MFD-440V`), timestamp parsing. | `dev` |
| `F02` | `SYN-WO-02` | Single-page Work Order (1p) | **Plumbing Leak & Unit-Turnover Ticket** (*Maple Ridge Commons, Unit 12B*): Dense boxed grid form, lockbox/key code field, multi-paragraph technician root-cause and resolution prose block, SLA reported/dispatched/completed timestamps, printed technician/supervisor sign-off names. | Dense narrow form cells, multi-line prose truncation inside bordered boxes, distinguishing `WO-2026-0418` from asset tag `WH-40G-8821`. | `dev` |
| `F03` | `SYN-WO-03` | Single-page Work Order (1p) | **Electrical & Appliance Safety Inspection Ticket** (*Harborview Lofts, Unit 509*): 8-row structured inspection checklist table (`Item`, `Location`, `Pass`, `Fail`, `N/A`, `Reading/Notes` with GFCI trip ms / breaker amperage values) plus follow-up parts requisition footer. | Narrow single-character symbol/mark columns (`X` / `-`), row alignment across wide sparse cells, unit suffixes (`15A`, `20A`, `4.2 mA`). | `eval_holdout` |
| `F04` | `SYN-INV-01` | Single-page Maintenance Invoice (1p) | **Plumbing Contractor Repair Invoice** (*Summit Drain & Pipe LLC -> Cedar Hollow Apartments*): Classic header (`Invoice #`, `Work Order Ref`, `Invoice Date`, `Due Date`, `Net 30`), 4 line items mixing **tax-exempt labor** (`2` rows) and **taxable materials** (`2` rows), zero discount, state sales tax (`6.25%`) applied strictly to taxable materials subtotal. | Naive arithmetic checkers assuming `tax = subtotal * rate` fail unless per-line taxability (`T`/`N`) is respected; cross-reference link to `WO` ID. | `dev` |
| `F05` | `SYN-INV-02` | Single-page Maintenance Invoice (1p) | **HVAC Service & Parts Supplier Invoice** (*Northstar Mechanical Supply -> Harborview Lofts*): Three-block address band (`Bill To`, `Service Location`, `Remit To`), 6 line items with fractional labor hours (`1.50`, `2.25`), per-line percentage contractor discount (`10%`, `15%`) on parts rows, `8.00%` tax on discounted taxable parts, nonzero `previous_balance`, and distinct `invoice_total` vs. `amount_due`. | Multi-column address disentanglement, fractional-quantity `Decimal` rounding (`ROUND_HALF_UP`), distinguishing current `invoice_total` from `amount_due`. | `eval_holdout` |
| `F06` | `SYN-INV-03` | Single-page Maintenance Invoice (1p) | **Dense Multi-Trade Unit-Turnover Invoice** (*Keystone Property Services -> Birchwood Terrace, Unit 301*): 10 compact 8.5-pt line items with non-round unit prices (e.g., `$14.37`, `$8.95`), one negative core-return/credit adjustment row (`-$25.00`), flat environmental disposal fee (`$18.50`, non-taxable), and exact total reconciliation. | Small-glyph resolution under base vs. gundam mode (`H-C2`), signed negative credit line handling, non-taxable fee ordering in total block. | `eval_holdout` |
| `F07` | `SYN-MP-01` | Multi-page Consolidated Invoice (3p) | **Monthly Multi-Unit Maintenance Billing Statement** (*Apex Facility Maintenance -> Maple Ridge Commons*, 3 pages): Page 1 carries header + line items `1–8`; Page 2 continues the **same table** (`items 9–18`) with repeated column header row; Page 3 carries `items 19–21`, subtotal/tax/total summary block, and remittance stub. Every page carries `Invoice No: INV-2026-1190`, `Contract ID: CTR-8840`, and `Page p of 3`. | Cross-page table continuation (`cross_table`/`append_table` header deduplication in `process_unlimitedOCR2.py`), `<PAGE>` emission order `1 -> 2 -> 3`, summary totals appearing only on final page, cross-page ID consistency. | `dev` |
| `F08` | `SYN-MP-02` | Multi-page Work-Order Packet (3p) | **Emergency Water-Mitigation Packet** (*DryFast Restoration -> Harborview Lofts, Units 402 & 302*, 3 pages): Page 1 dispatch scope, affected units, and authorization metadata; Page 2 room-by-room moisture reading & dehumidifier placement table (`Serial #`, `RH %`, `GPP`) continuing onto top of Page 3; Page 3 equipment removal log referencing Page 2 serial numbers plus final technician sign-off. Every page carries `Packet ID: WMP-2026-0073` and explicit `Page p of 3`. | Deliberate page ordering, cross-page equipment serial-number referential integrity (Page 3 removal rows must match Page 2 deployed serials), multi-unit scope header vs. per-room table rows. | `eval_holdout` |

---

## 2. Deterministic Source-First Generation & Exact Arithmetic Rules

### 2.1 Source-First Pipeline Order

Ground truth is **never** reverse-engineered from rendered PDFs or OCR outputs:

1. **Canonical Structured Specification (`source_record.json`):** Deterministic Python `3.12` generator seeded with an explicit integer seed per family (`random.Random(family_seed)` where used at all, or fully literal declarative Python records) emits `source_record.json` containing exact strings, ISO-8601 dates (`YYYY-MM-DD`), exact `Decimal` strings (`"14.37"`), page placement directives, and expected cross-page anchors.
2. **Independent Pre-Render Arithmetic Audit (Gate A):** A standalone stdlib verifier using `decimal.Decimal` only (**zero `float` operations permitted**) validates every monetary equation in `source_record.json` before PDF rendering begins.
3. **Deterministic PDF Synthesis:** A pinned open-source PDF renderer generates the clean vector PDF (`v0_clean.pdf`) using embedded permissively licensed fonts (e.g., `Liberation Sans` / `DejaVu Sans` under SIL OFL / Bitstream Vera—avoiding proprietary Microsoft/Monotype font EULAs), fixed metadata timestamps (`CreationDate = ModDate = 2026-11-14T00:00:00Z`), and deterministic PDF `/ID` trailers so two runs on the same platform produce **identical SHA-256 bytes**.
4. **Independent Post-Render Round-Trip Audit (Gate B):** A separate stdlib/`pypdf` checker inspects `v0_clean.pdf` to verify exact page count, confirm zero text clipping/missing fields per target page `1..P`, and confirm that every literal formatted currency string and identifier in `source_record.json` appears on the expected rendered page.
5. **Derived Degradation Variants (`WP-0004 / 004`):** Scan/capture variants (e.g., `v1_raster300` pure image PDF at 300 DPI; `v2_skew_pos4deg` bicubic `+4.0°` rotation on white canvas; `v3_skew_neg3deg` `-3.0°` rotation) are deterministically derived from `v0_clean.pdf` with recorded transformation parameters, SHA-256 hashes, and strict inheritance of parent `family_id` and `split`.

### 2.2 Exact `Decimal` Accounting Invariants (`ROUND_HALF_UP`)

Every synthetic invoice (`F04`, `F05`, `F06`, `F07`) must obey line-level GAAP ledger rounding in USD cents (`Q = Decimal("0.01")`, `R = decimal.ROUND_HALF_UP`) so printed line totals **always** sum literally to the printed subtotal with zero hidden sub-cent residual:

1. **Inputs:** `quantity` quantized to `0.01`; `unit_price` quantized to `0.01` (or signed negative `unit_price` solely on explicit credit/return adjustment lines such as `F06`); `line_discount_rate` in `[Decimal("0"), Decimal("1"))` quantized to `0.0001`.
2. **Line Extension:**
   - `gross_line = (quantity * unit_price).quantize(Q, rounding=R)`
   - `line_discount = (gross_line * line_discount_rate).quantize(Q, rounding=R)`
   - `net_line = gross_line - line_discount` *(exact value printed in the row's `Line Total` cell)*
3. **Subtotals (Exact Sum of Printed `net_line` Values):**
   - `subtotal = sum((line.net_line for line in lines), Decimal("0.00"))`
   - `taxable_subtotal = sum((line.net_line for line in lines if line.is_taxable), Decimal("0.00"))`
   - *(Rule against ambiguity: discounts are applied at the line level via `line_discount_rate`—or, if an invoice-level discount is ever used, all lines on that invoice must share the same `is_taxable` flag so `taxable_base` is uniquely determined from visible numbers without hidden pro-rata allocation rules.)*
4. **Tax, Fees, Invoice Total, and Balance Due:**
   - `tax_amount = (taxable_subtotal * tax_rate).quantize(Q, rounding=R)` *(assert `taxable_subtotal >= Decimal("0.00")`)*
   - `non_taxable_fees = sum((fee.amount for fee in fees), Decimal("0.00"))`
   - `invoice_total = subtotal + tax_amount + non_taxable_fees`
   - `amount_due = invoice_total + previous_balance - payments_credits_applied`
5. **Dual Formatting Rule:** Both the canonical normalized decimal string (`"10375.00"`) and the exact surface string printed on the page (`"$10,375.00"`) are recorded in `source_record.json` so evaluation separates OCR character fidelity from numeric normalization.

---

## 3. Family-Level Split and Provenance Manifest Schema

### 3.1 Leak-Free Family Split (`4 dev` / `4 eval_holdout`)

- **`dev` (4 families):** `F01` (`SYN-WO-01`), `F02` (`SYN-WO-02`), `F04` (`SYN-INV-01`), `F07` (`SYN-MP-01`). Used for prompt/post-processor debugging, text-layer gate threshold calibration (`H-C1`), and skew-estimator sanity checks (`H-C3`).
- **`eval_holdout` (4 families):** `F03` (`SYN-WO-03`), `F05` (`SYN-INV-02`), `F06` (`SYN-INV-03`), `F08` (`SYN-MP-02`). **Frozen prior to tuning.** Every derived scan/skew variant of `F03`, `F05`, `F06`, or `F08` remains permanently in `eval_holdout`; variants of one base document are correlated observations, never independent samples.

### 3.2 Provenance Manifest Fields (Required for `WP-0004 / 004` Materialization)

Every entry in `evaluation/manifest.json` (when materialized in `WP-0004 / 004`) must populate:

| Field | Type & Requirement |
| --- | --- |
| `fixture_id` | Unique immutable ID (e.g., `SYN-INV-02-v0-clean`, `SYN-INV-02-v2-skew-pos4deg`). |
| `family_id` | Parent document family (`F01`–`F08`, or `PUB-AZ-01`/`02` if a public sample is later admitted). |
| `classification` | `"synthetic"` or `"public"`. |
| `admission_status` | `"admitted"` (only after non-author check) or `"candidate_unadmitted"`. |
| `origin_url` / `origin_revision` | `null` for repository-generated synthetic items (use repo deliverable SHA + generator script path); full HTTPS URL + 40-char commit SHA for public items. |
| `file_path` | Relative path under `evaluation/` (never `workers/ocr/` or `src/`). |
| `git_blob_oid` & `sha256` | Exact 40-char Git blob SHA-1 and 64-char lowercase SHA-256 of the PDF bytes. |
| `size_bytes` & `page_count` | Exact integer byte count and integer page count ($\ge 1$). |
| `source_license_and_notices` | Generator license (`MIT`/product-owned + font SIL OFL refs) or upstream `LICENSE.md` blob + internal PDF/font notice summary and required attribution text. |
| `generation_or_transform_params` | Seed, generator/renderer tool versions, DPI, rotation angle $\theta$, border fill, noise parameters, and parent `fixture_id` if derived. |
| `expected_ground_truth_ref` | Relative path to canonical `source_record.json` (with page-indexed fields, tables, and `Decimal` totals). |
| `ground_truth_checker` | Exact command/script + non-author reviewer identity (`eld-rd-reviewer` in `WP-0004 / 005`). |
| `split` | `"dev"` or `"eval_holdout"` (invariant across all variants of the same `family_id`). |

---

## 4. Public Candidate Primary-Source Inspection & Admission/Notice Audit

Both candidates from `Azure-Samples/cognitive-services-REST-api-samples` at commit `4a3c5ca76318feb3f7cfb109e1f79c542eb14d01` were fetched read-only into ephemeral session scratch outside the Git worktree, hash-verified, inspected at the raw PDF object/stream level, visually read, and audited line-by-line against their adjacent repository JSON files.

**Current Status of Both Candidates: `NOT ADMITTED` (`candidate_unadmitted`).**

### 4.1 Byte, Hash, Metadata, and Internal Notice Findings

| Property | Candidate 1: `curl/form-recognizer/sample-invoice.pdf` | Candidate 2: `curl/form-recognizer/Invoice-6.pdf` |
| --- | --- | --- |
| **Pinned Commit** | `4a3c5ca76318feb3f7cfb109e1f79c542eb14d01` | `4a3c5ca76318feb3f7cfb109e1f79c542eb14d01` |
| **Verified Git Blob OID** | `1e7c93c6f70ccd74697b7a74cbb6a19fa6d5d6d8` (matches brief) | `1c24566e64aa6cdab8bb229c3b1ac64e750fa235` (matches brief) |
| **Verified Size & SHA-256** | `104,430` bytes; `c2ce1edcbb91cf8f6685f4749a5eedcb752795e5e8f0a126f13953a0f3974f69` | `167,063` bytes; `aaaffcf69aa5485f64adf6ddec35249b0319cc8bc9e4e27bb6257d970fa97c03` |
| **Page Count & Stream Type** | 1 page (`%PDF-1.7`); born-digital tagged PDF (`BT..ET` vector text stream, no page-scan image). | 1 page (`%PDF-1.7`); born-digital untagged print-to-PDF (`BT..ET` vector text + small vector/image elements). |
| **PDF `/Info` Metadata** | `/Author (Anatoly Ponomarev)`, `/Creator` & `/Producer (Microsoft Word for Microsoft 365)`, `/CreationDate (D:20200929094453-07'00')`. XMP packet (`stream[4]`) carries no restrictive rights statement. | `/Author (anroth)`, `/Producer (Microsoft: Print To PDF)`, `/Title (Microsoft Word - Sales Receipt.docx)`, `/CreationDate (D:20200820112834-07'00')`. No XMP packet. |
| **Depicted Content / PII Check** | Fictional Microsoft demo personas only (`CONTOSO LTD.`, `Microsoft Corp`, `123 456th St`, `123 Bill/Ship/Service/Remit St`, `INV-100`, `CID-12345`, `PO-3333`). Zero real PII. | Fictional Microsoft demo personas only (`Contoso, Ltd.`, `Wingtip Toys`, `554 Magnolia Way, Walnut, WY, 98432`, `ID#: 5554443`, `Receipt # No.: 9876`). Zero real PII. |
| **Repository License (`LICENSE.md`)** | Blob `b5f17c02bce61a15a953244b8587cb468b273644` (`1,410` B, SHA-256 `7bfe2b013928fed5a817a3e797f01f6fca2ec6b2dcc31bbefc1b48e5c78da3ee`): **MIT License** (`Copyright (c) Microsoft Corporation`) covering repository software and associated documentation files, plus a *Third Party Programs* informational notice clause. | Same root `LICENSE.md` (`b5f17c02...`). |
| **Internal Embedded Font Notices** | Subsetted TrueType `BCDEEE+Calibri-Bold` & `BCDFEE+Calibri` carry standard Microsoft font EULA text (`© 2018 Microsoft Corporation. All Rights Reserved. You may use this font to create, display, and print content as permitted... Any other use is prohibited`) plus MIT notice for Biblical Hebrew OpenType layout logic. | Subsetted CID fonts (`Century Gothic`, `Segoe UI Symbol`, `Arial Bold`, `Haettenschweiler`) carry Monotype / Microsoft font EULA notices (`© 1990-91 / 2017 The Monotype Corporation`, `© 1995 / 2016 Microsoft Corporation`). Display/rasterization of the intact PDF is standard document use; extracting or redistributing standalone font programs is prohibited. |

### 4.2 Audit of Adjacent Model-Output JSON vs. Actual Source Pages (Why Adjacent JSON Is Disqualified as Ground Truth)

Inspecting the actual PDF pages and decompressed `BT..ET` text operators against the adjacent Form Recognizer v2.1.0 JSON files in the same directory proves concrete factual errors and omissions in both JSON files:

1. **`sample-invoice.pdf` vs. `sample-invoice-output.json` (blob `253706b7af3b0926f2bd6801e4c9161782302281`):**
   - **Phantom Hallucinated / Stale Fields in JSON:** `sample-invoice-output.json` (`lines 604–633`, `prebuilt:invoice`) asserts `"ServiceStartDate": "2019-10-14"` (`text: "10/14/2019"`, confidence `0.995`) and `"ServiceEndDate": "2019-11-14"` (`text: "11/14/2019"`, confidence `0.997`). **Neither date string (`10/14/2019` nor `11/14/2019`) exists anywhere on the rendered page or inside the decompressed PDF content stream of blob `1e7c93c6...`!** The JSON output was generated on `2020-11-06` against a different/earlier version of the template (explaining why the line item reads `"Test for 23 fields"` while only 21 labeled fields remain on `sample-invoice.pdf`). Any evaluator trusting `sample-invoice-output.json` as ground truth would falsely penalize every accurate OCR system for "missing" two non-existent dates.
   - **Missing Line-Item Fields in JSON:** `documentResults[0].fields` omits the `Items` array altogether (line items appear only as raw geometric cells in `pageResults[0].tables[0]`, alongside an empty 3rd row).
   - **Source-Document Arithmetic Defect in `sample-invoice.pdf` Itself:** Row 1 of the PDF table literally prints `QUANTITY = 1`, `DESCRIPTION = Test for 23 fields`, `UNIT PRICE = 1`, `TOTAL = $100.00` (`1 × 1 = 1 ≠ 100.00`), followed by `SUBTOTAL $100.00`, `SALES TAX $10.00`, `TOTAL $110.00`, `PREVIOUS BALANCE $500.00`, `TOTAL DUE $610.00`.
2. **`Invoice-6.pdf` vs. `analyze-result-invoice-6.pdf.json` (blob `2dfff4e1af1c0b9839c734733da40b705d930674`):**
   - **Narrow Demo Schema Omissions in JSON:** `documentResults[0]` uses `docType: "custom:custom-form-demo"` and labels **only 6 fields** (`Receipt No: "9876"`, `Sold To: "Wingtip Toys"`, `ID #: "5554443"`, `Live Delivery?: "selected"`, `Online Delivery?: "selected"`, `Video Delivery?: "unselected"`). It completely omits `VendorName` (`Contoso, Ltd.`), document title (`Project Statement`), `InvoiceDate` (`9/10/2020`), `CustomerAddress` (`554 Magnolia Way, Walnut, WY, 98432`), `SubTotal` (`$10,375`), `SalesTax` (printed as rate `"3%"`, **not** dollar tax `$311.25`), `Total` (`$10,686.25`), and structured line-item records (`12/5/2020 Manager Training $3,500`, `12/10/2020 Manager Training $3,500`, `12/11/2020 Leadership Training $4,500 / 25% discount / $3,375`).
   - **Domain Mismatch:** `Invoice-6.pdf` is a corporate training statement rather than a property maintenance document, though its printed arithmetic (`3500 + 3500 + 4500*(1 - 0.25) = 10375`; `10375 * 1.03 = 10686.25`) is internally consistent.

### 4.3 Admission Recommendation for `WP-0004 / 004` Reconciliation

1. **Keep both candidates unadmitted now (`WP-0004 / 002`).** Primary evaluation must rely on the deterministic synthetic maintenance corpus (`F01`–`F08`) whose domain, font licensing, and `Decimal` ground truth are completely controlled.
2. **In `WP-0004 / 004` (subject to Astra/Carbon reconciliation and `WP-0004 / 005` Opus review):**
   - `Invoice-6.pdf` may be admitted as an optional external format-sanity fixture **only** if retained intact alongside Microsoft's MIT `LICENSE.md` copyright/permission notice, never stripped for embedded fonts, labeled explicitly as out-of-domain non-maintenance developer material, and paired with a **page-inspected ground-truth record** authored from the PDF bytes rather than `analyze-result-invoice-6.pdf.json`.
   - `sample-invoice.pdf` should **either** remain excluded from standard invoice evaluation **or** be segregated as a dedicated `"source_arithmetic_mismatch"` edge-case fixture (`expected literal unit_price = "1"`, `expected literal line_total = "$100.00"`, `expected arithmetic_warning = true`, `ServiceStartDate = absent`, `ServiceEndDate = absent`) to verify that eLedgerCare extracts printed numbers faithfully and flags vendor math errors instead of hallucinating reconciled numbers.
