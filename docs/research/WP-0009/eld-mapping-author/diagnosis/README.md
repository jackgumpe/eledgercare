# WP-0009 saved-output diagnosis and one-change recommendation

Recommend exactly **one mapping change** for coordinator selection: in the field-extraction branch of a native table, prefer a conservatively identified same-row value immediately beside an exact existing known label before applying B0's below-row rule. Do not expand labels, table schemas, typed units, parsing, normalization, or scoring in the same change. This recommendation is ready for independent diagnosis/protocol review; it is not implemented or accepted.

Frozen helper `d4503ea6f8f384f29de8c84de2c83f451c05e817` reproduced **all 26 primary score objects and the original split/family summaries exactly**, plus the separate supplemental score. [Method](METHOD.md), [all-document accounting](results/accounting.md), [full item ledger](results/ledger.json), [108-file input inventory](results/input-inventory.json), and [actual execution](execution/attempt-1.json) make the result reviewable. The initial raw packets, corpus, model, scorer and mapper are unchanged. Original dev13 and formerly heldout13 are now exposed regression inputs; this is not a fresh evaluation.

## Accounting and attribution limits

| Original split | Complete/planned | Printed fields | Printed cells | Typed fields | Typed cells | Rows | Absences |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 12/13 | 146/196 | 304/753 | 146/196 | 304/753 | 40/96 | 9/13 |
| eval_holdout, exposed | 13/13 | 47/165 | 426/1048 | 47/165 | 420/1048 | 42/152 | 0/13 |

These counts audit denominators, not a replacement for the unchanged equal-family means. Dev printed field/cell means remain 0.734982639 / 0.648903509; exposed heldout remains 0.262962963 / 0.493827160, with typed cells 0.488271605. All page-count, sentinel, adjacency and cross-page-link denominators and original scores are in the ledger. Counts sum to 361 expected fields and 1,801 expected cells across 26 documents; correlated variants are not independent families.

The primary `SYN-MP-01-v2-skew-pos4deg` failure keeps 15 fields and 180 cells with zero credit. Its final raw output is unavailable. The helper's empty prediction reproduces accounting; it does not assert the model saw no text. The original `FileNotFoundError` has no retained path/stack proving its historical cause. The separate recovery completed, but page-three `rowspan="2"` caused `page_3:table:unsupported_span`; all 195 field/cell slots remain ineligible, despite 5 observed-exact fields and 70 observed-exact cells in the original supplemental score. Recovery never replaces the primary failure.

The ledger assigns demonstrated categories to local field/cell failures and leaves residual uncertainty explicit:

| Nonexclusive category | Affected primary field/cell slots | Interpretation |
| --- | ---: | --- |
| Text recognition or omission | 61 | 48 absent deployment cells, 11 different mapped cell strings, two corrupted hybrid fields |
| Native parse or structure | 12 | F02 skew spanning header/expanded table rows; primary completed documents all parse-valid |
| Field/table mapping | 873 | Includes unsupported schemas/headers, same-row mistakes and overlaps; **not 873 recoverable correct values** |
| Typed conversion or scoring semantics | 16 | Six exact printed quantities rejected for units; ten address line-join representations |
| Runtime unavailable output | 195 | The original failed document's field/cell denominators |
| Ambiguous/unadjudicated | 150 | Failed printed/typed field or cell items with no asserted local cause in this finite audit |

These categories overlap. For example, the 48 missing deployment cells also face an unsupported table schema; their absence cannot be repaired by a mapper. An identified credit barrier does not exhaust underlying recognition causes. The 150 unknown count describes this finite adjudication, not irreducible uncertainty. Absence uncertainty is separate: 17/26 original slots are unmapped/unverified (four dev, including the failed call, and all 13 exposed heldout). Row/page/link metrics retain baseline results but are not assigned exhaustive causal percentages.

## Concrete causal evidence

Native locations below use page numbers starting at 1 and block/row/cell indices starting at 0. Every evidence row in `ledger.json` binds the exact retained raw path and expected item ID. This table includes both positive and negative evidence; seeing a matching string elsewhere does not establish the correct item.

| Document and expected item | Native location / literal observation | Demonstrated cause |
| --- | --- | --- |
| SYN-WO-01-v2-skew-pos4deg; `field:p1:work_order_id:0`, expected `WO-004192` | p1/b0/r2/c0-c1: `Work Order ID:` / `WO-004192`; B0 predicts `Property:` from r3/c0 | Same-row value is present; below-row field association is wrong |
| SYN-INV-02-v0-clean; `field:p1:subtotal:8`, expected `$766.36` | p1/b4/r0/c1-c2: `Line Net Subtotal:` / `$766.36`; B0 predicts `Taxable Subtotal (Tax=T Rows):` | Same mapping error in invoice summary, repeated in raster variant |
| SYN-WO-03-v0-clean; `cell:p1:safety_checklist:C01:item_id`, expected `CHK-01` | p1/b13/r1/c0 `CHK-01`, under exact native header `Item`, `Inspection Point`, `Location`, `Pass`, `Fail`, `N/A`, `Measured Reading / Notes` | All 56 cells/document are unmapped because no safety-checklist schema exists in dev mapping; the bound rows across three variants contain 168 exact values |
| SYN-MP-01-v0-clean; `cell:p2:line_items:L09:row_id`, expected `L09` | p2/b2/r3/c0 `L09`; header r2 ends `Net Liner`; page-three header uses `Disc%*` | Strict header failure leaves 108 cells/document unmapped despite 216 exact audited values across clean/raster; recognition noise in headers coexists with mapping rejection |
| SYN-WO-02-v2-skew-neg3deg; `cell:p1:turnover_tasks:TK01:pressure_psi`, expected `68.0 PSI` | p1/b10 header has `<td colspan="2">Action Performed</td>`; body row has an extra empty cell before `68.0 PSI` | Accepted native structure is incompatible with exact unit-span header/column mapping; 12 cells affected. No silent span expansion is assumed |
| All four SYN-MP-02 variants; page-three `equipment_deployment:E07` and `E08`, six columns each | p3/b4, or b7 in skew, contains only the deployment header; raw has no E07/E08 row keys | Actual omitted native deployment rows: 48 cells. Retrieval R07/R08 still mention serials, which does not recover placement, initial humidity or initial GPP |
| SYN-WO-01-v0-clean; `cell:p1:stock_parts:P01:part_sku` | p1/b28/r1/c0 `CAP-45-SMFD-440V`, expected `CAP-45-5MFD-440V` | Native character substitution survives mapping; no identifier repair is justified |
| SYN-WO-02-v3-hybrid-note; `field:p1:hybrid_field_addendum:15` | raw footer `FIELD-ADDENHUM RISER VALVE VLV-02B TAGGED CLOSED`; label `TRASTER FIELD-ADDENHUM` | Content is present but corrupted, with label mismatch; not complete reading omission |
| SYN-MP-02-v3-hybrid-stamp; `field:p3:hybrid_holdover_stamp:11` | raw `RASTER STAMP: HOLD EQUIP DH-00855 - 24H - AUTH J. RIVERA`, expected `+24H` | Sign/text recognition error plus unmapped field; cannot credit by finding the equipment serial |
| All three SYN-INV-03 variants; `line_items:L04:qty_unit`, `L05:qty_unit` | Native/mapped `2.00 GL` and `5.00 ST` equal printed targets | Six typed failures come from dev-only accepted unit grammar, not six recognition failures |

F08 has 448 unmapped table cells: 400 exact audited native cells plus the 48 absent deployment cells. F03/F08 together therefore have 616 affected denominators with 568 exact locally aligned values, not perfect recognition. The F07 header case additionally contains trailing blank physical cells and summary material; broad header tolerance could capture non-data rows and is not selected here.

## Absence and invention blind spots

All 26 absence denominators are retained with zero detected nonempty violations. This cannot establish zero inventions. Direct native inspection of clean exposed examples finds `Re-Inspection Date:` with no value (F03 p1/b10), `Warranty Claim Auth #:` alone in a table cell (F05 p1/b1/r2/c2), `Resident Chargeback Code:` with the next-row cell empty (F06 p1/b2/r2-c2 and r3-c2), and a spanning `Insurance Adjuster Claim #:` with no value (F08 p1/b7/r3). Their labels are outside B0's vocabulary, so they remain unmapped/unverified. The full ledger retains all variants' label locations; no new absence credit is awarded by this audit.

Native `Property Manager Ack:` in F08 p3/b7/r0/c2 is partially matched as known `Property`, yielding an unmatched `property_name='Manager Ack:'` candidate. This is mapper-created misassociation, not evidence that the model invented a property. It stays uncorrected by the recommended change. Schema-relative extra rows/cells are zero even while entire unsupported tables and malformed structures remain outside mapped tables. Those zeros are not comprehensive hallucination detection. Unmatched field candidates, raw text and absence locations remain available for independent inspection.

The counterfactual `2.00 HR` receives typed credit against numeric target `2.00`, because B0 validates supported unit spelling but compares only the number. This is a demonstrated scoring-semantic blind spot, not an observed wrong-unit model prediction in this corpus. Expanding units alone would not fix it. Likewise, address newlines versus target comma-space joins account for ten exact string mismatches; a normalization change would change comparability, not recognition.

## Ranked single-change options

| Rank | Candidate | Bound evidence / affected denominators | Decision |
| --- | --- | --- | --- |
| 1 | Prefer an unambiguous same-row adjacent value for existing exact field labels in native tables | **27 existing failed field slots**, nine documents, five families: F01 4, F02 4, F03 1, F05 14, F08 4; eight dev and 19 exposed heldout | **Recommend this one change**. It corrects an observed association error across several layouts without new vocabulary, fuzzy text repair or scoring changes |
| 2 | Add supported table schemas for current F03/F08 headers | 616 unmapped cells; 568 locally exact, 48 absent | Defer: larger apparent benefit but introduces several table schemas and exposed-family vocabulary; cannot recover omitted rows |
| 3 | Tolerate limited known-table header deviations | 216 F07 cell denominators in two variants | Defer: corrupted headers plus trailing/summary rows make a narrow safe matching contract more complex; would risk overfitting two raw spellings |
| 4 | Extend typed quantity unit coverage | Six printed-correct cells across three F06 variants | Defer: improves converter coverage only; numeric-only unit comparison remains a separate semantic defect |
| 5 | Normalize address line joining | Ten observed representation-only mismatches | Defer: would alter scoring/normalization meaning and requires carefully bounded address semantics |

Rank 1's 27 entries are named in `same_row_observed_opportunities`. This is an expected effect supported by exact local evidence, **not a measured improvement or promised headline score**. A future implementation may reveal ambiguity; any shortfall requires explanation on exact items rather than tuning to force credit.

## Proposed implementation and independent acceptance boundary

After coordinator selection and independent review only, implement the single mapping change under `qualification/mapping_v1/`. In the existing no-active-table field branch, an exact existing label cell may take its immediate right neighbor when both cells have unit spans, the neighbor is nonempty, is not a label-like cell ending in a colon, and contains no recognized field-label match. Retain the existing below-row behavior when this test does not apply. Do not alter recognized data-table extraction, native parsing, labels, header schemas, values, printed comparison, typed conversion, absence semantics or document eligibility. Never use expected answers, fixture identity or boxes to decide the pairing. Duplicate-label and ambiguous layouts need explicit tests; ambiguity must not produce a confident new association.

Independent acceptance should require:

1. Same retained 26 primary inputs and separate recovery, exact raw/input hashes, original failed denominator, unchanged old B0 packet/source/corpus identities. Reproduce old scores first. Verify no new model/GPU run or sealed-content exposure during tuning.
2. All 27 cited field opportunities reviewed individually against raw locations. Target the exact adjacent value and avoid a duplicate candidate. Report actual printed and typed deltas by document and unchanged split/family aggregation; this is a mapper effect, not improved model reading. Preserve every previously correct field/cell and report any regression without net-score masking.
3. Unchanged table-cell outputs, absent-slot rules, parse eligibility and typed conversion. Existing header-row/next-row layouts, all-label rows, empty right neighbors, spanning cells, unknown labels ending in colons, text containing known labels, repeated labels and ambiguous neighbors must have meaningful positive/negative cases with no expected-answer access in extraction.
4. Preserve corrupted identifiers, the omitted F08 deployment rows, hybrid signs/text, unknown headers and unsupported units; do not create values or claim these are repaired. Record unmatched fields, duplicates and absence violations alongside exact credit.
5. Freeze source, scoring definition and protocol before independent acceptance and any new four-family evaluation release. The custodian's fresh PDFs, expected values, native output and identifying layouts remain unread by this author. Stage C and all GPU work still need their separately bound release.

## Executed checks, failures and unrun work

The one decisive helper execution exited 0 against the frozen helper and reproduced all 27 score objects (26 primary plus one separate recovery). No score mismatch or helper correction occurred. Syntax parsing preceded freeze; source identity, input hashes and full-score/summary equality were checked during execution. Exact run stdout/stderr and command/HEAD are retained. The Windows exploratory `rg` call with a literal wildcard file path produced error 123; rerunning with `-g` correctly found no E07/E08 keys (exit 1 means no matches). An initial discovery command searched absent `docs/research`/`evidence` directories and produced missing-path diagnostics; the authorized new owned directory was subsequently created. Neither error changed data or scoring.

No selected-change implementation/tests, application/product tests, runtime/model import, fresh inference, GPU checks, service startup, dependency installation or fresh sealed-family inspection was performed. The accepted transformed PDFs were not newly rendered or visually re-adjudicated; this diagnosis trusts admitted ground truth and the frozen reference constructor. Native reading-order error remains SequenceMatcher token alignment, not minimum-Levenshtein WER/CER. No exhaustive hallucination audit or character-level causal percentage is claimed.
