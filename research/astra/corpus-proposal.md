# Corpus and admission proposal — eight synthetic families, two public candidates

Author: eld-rd-astra, WP-0004 / 001. Proposed specification only: **zero fixtures generated, zero admitted items, zero checked ground-truth records**. No writes to evaluation or shared staging occurred. Coordinator-authorized corpus preparation and uninvolved Opus verification remain required.

## Family membership and split, frozen before tuning

Propose exactly 8 originals, with at most 2 derived documents per original: an image-only unrotated version and a +3.0-degree raster version. Maximum 24 PDFs across 8 families, not 24 independent samples. Each page of a rotated document receives the same recorded transform. Keep a raw pixel/page artifact mapping for scoring. No additional degradation sweep, extra templates, or real handwriting in this milestone.

| Family | Original and intended distinction | Pages | Split | Ground-truth focus |
| --- | --- | ---: | --- | --- |
| WO-01 | Fictional Maple Court unit A-001; compact form with label/value pairs | 1 | development | Work-order ID with leading zeros, unit, requested date, priority, issue, assignee |
| WO-02 | Fictional Cedar Annex unit B-020; two-column form, table rules | 1 | development | Reading order, contact fields, task list, deliberate blank optional field |
| WO-03 | Fictional Birch House unit C-003; sparse memo with footer reference | 1 | held out | Long description, footer ID, no invented table or blank-field value |
| INV-01 | Fictional maintenance vendor; plain table, no tax/discount | 1 | development | Exact quantities, rates, amounts, subtotal, total |
| INV-02 | Different fictional vendor/layout; tax applied after a fixed discount | 1 | development | Decimal arithmetic, discount basis, tax rounding and totals |
| INV-03 | Dense table, different fictional vendor/layout, negative credit line | 1 | held out | Small type, signs, leading-zero part IDs, row association, exact total |
| MP-01 | Work order plus ordered task continuation, safety notes and signoff; page-specific sentinel IDs | 4 | development | Task continuation across page 2/3, repeated work-order ID, page order and absent signatures |
| MP-02 | Maintenance invoice and line-item continuation with repeated headers and final totals; page-specific sentinel IDs | 12 | held out | Continuations across page 2/3 and 10/11, all line rows exactly once, total only on page 12 |

Split unit is the entire family: original, pages, renderings, crops, reordered negative controls and future variants cannot cross splits. No content from MP-02 may be sliced into a development sample. Family layouts and data must be authored before inference. This table is a proposed split for the corpus owner to accept/freeze, not a claim that hidden test files already exist. A held-out partition is not truly blind to the agent who authored its contents; the executing tuner should receive hashes/IDs but not expected answers. If that separation cannot be maintained, label it a fixed test partition rather than blind validation.

## Deterministic generation and truthful expected data

Use fictional properties/vendors/names and no customer material. Author structured JSON first with literal values and row IDs. Proposed seed `4004001` must be recorded if randomness is used; preferably specify every value explicitly. Record generator revision, exact PDF renderer and font file digests, locale, page geometry, embedding settings and fixed metadata timestamps. Renderer/font selection is not yet qualified or installed. Reproducible source does not guarantee byte-identical PDFs; if timestamps/object ordering prevent identical bytes, correct the generator before admission or document the exact repeatability limit.

Use decimal minor-unit arithmetic, never binary floating point: row amount = quantity * unit price with explicit permitted quantity precision and per-row rounding; subtotal = sum(row amounts); discount before tax for INV-02; tax = round-half-up((subtotal - discount) * tax rate) to two decimals; total = subtotal - discount + tax. INV-03's signed credit is included in subtotal. Display the same rule on-page. Record currency and decimal separator. MP-02 has unique row IDs and exactly one authoritative summary; repeated headers are not line items. Define expected blanks as absent values; expected page text and layout/table ground truth stay distinct from business-field JSON.

Render originals, then render raster variants at fixed 300 DPI with a pinned renderer. The image-only version must have no embedded text layer; +3-degree variant derives from those same pixels with declared rotation direction, resampling, padding and canvas bounds. Every variant retains parent SHA-256 and family ID. The deskew algorithm never receives the transform's known angle during prediction. Font-rendered cursive is not real handwriting and no handwriting capability is claimed.

## Admission and independent checks

1. Corpus author freezes structured data and independently specifies expected calculations/order from it; generate PDFs and hashes, without running OCR to create answers.
2. A non-author checker recomputes all row/subtotal/tax/discount/total arithmetic from displayed operands using an independently written method. Sharing the generator's arithmetic function is not independent verification.
3. The checker views EVERY rendered original page and derived page at legible resolution, checks all expected visible fields/rows against the source, page sequence, clipping, embedded-text/visible consistency, plus cross-page continuation and repeated headers. Ground truth in source alone is insufficient when rendering can omit a row.
4. Check file digests, byte count, page count and image-only status; ensure every variant remains in its original family/split. Resolve discrepancies in the source and rerender; record the corrected hashes and checker identity.
5. Freeze manifest, expected-data digests and split before tuning. The uninvolved Opus reviewer verifies admitted ground truth and actual evidence on exact revisions. Astra/Carbon joint authors cannot independently accept their own joint corpus. Ambiguous/unreadable fields block admission or are explicitly marked unscorable BEFORE model output, with counts; never exclude errors after seeing predictions.

Required per-item manifest fields: fixture ID; family ID; synthetic/public status; admission state and reason; exact origin URL/revision and Git blob if public; file path, SHA-256, bytes and pages; source/license/internal-notice references; generator/tool/font pins and seed; parent digest and all transformations; expected fields/table rows/cells/order/cross-page links and expected-data digest; split; author; independent checker identity, timestamp, checked revision and verification evidence. Use null with explanation for unresolved values, not fabricated hashes, page counts, checker names or license clearance.

The small set is diagnostic. Only three families are held out, including one long invoice. It cannot support population accuracy, handwriting, camera-photo, language/domain-generalization, provider-ranking or statistical significance claims. Report per-family results and paired failures. Public candidates, if admitted, stay in a separate external-probe stratum; do not use them to inflate the eight-family denominator.

## Public candidates remain unadmitted

Exact directory metadata was refreshed at 2026-11-14T15:05:31Z and retained in [public-candidate-metadata.json](sources/public-candidate-metadata.json). GitHub root license text was read; it is MIT with Microsoft's copyright and a third-party-program note. That alone does not verify the individual PDFs' internal notices or establish every possible use. No PDF bytes were fetched in this source-only assignment.

| Candidate at Azure-Samples/cognitive-services-REST-api-samples revision `4a3c5ca76318feb3f7cfb109e1f79c542eb14d01` | Verified metadata | Unresolved admission evidence |
| --- | --- | --- |
| [sample-invoice.pdf](https://github.com/Azure-Samples/cognitive-services-REST-api-samples/blob/4a3c5ca76318feb3f7cfb109e1f79c542eb14d01/curl/form-recognizer/sample-invoice.pdf) | Git blob `1e7c93c6f70ccd74697b7a74cbb6a19fa6d5d6d8`; 104430 bytes | SHA-256, page count, visible content/internal notices, scope of permitted copying, independent expected fields/tables: all unknown |
| [Invoice-6.pdf](https://github.com/Azure-Samples/cognitive-services-REST-api-samples/blob/4a3c5ca76318feb3f7cfb109e1f79c542eb14d01/curl/form-recognizer/Invoice-6.pdf) | Git blob `1c24566e64aa6cdab8bb229c3b1ac64e750fa235`; 167063 bytes | Same unresolved items; family relationship to first candidate also unverified |

Future admission must inspect exact bytes/pages/notices, compute SHA-256, preserve applicable license/attribution, document allowed local evaluation/redistribution scope, and establish expected data through non-author visible-page inspection. Do not use adjacent cloud OCR JSON as truth or call Azure. If rights, privacy or truth remain uncertain, omit the candidate and keep the synthetic milestone moving. No training use is proposed. If both examples share a source template/document lineage, keep them one family and one split; do not assume independence from different filenames.
