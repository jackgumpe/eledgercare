# Public reference and policy interface, version 1

This is a proposed WP13 contract awaiting independent /002. It is not a mapper
implementation, source acceptance, corpus admission or inference release.

The finite schedule has WP13-F01 through WP13-F04, each with supported, conflict
and unsupported cases, in that order. F01/F04 are independent work-order families,
F02 service-invoice and F03 inspection/checklist. Each fixture ID is
`<family_id>-<case>-v0`, each PDF has one page, and the fixed independent sentinel
is `WP13-F04-conflict-v0`. The public reservation may use four artifact roles:
`pdf`, `expected`, `reference`, `policy`, under
`evaluation/mapping_v2/corpus/r1/{pdfs,expected,reference,policy}/`.

`expected.json` keeps the original B0 structure and scoring definitions. It has
fixture_id, family_id, doc_kind, split=`vocabulary_eval`, variant_kind equal to
case, page_count=1, and the original expected_fields, expected_tables,
expected_absences, page_sentinels, expected_adjacent_page_pairs and cross_page_links
lists. The last three are empty for this one-page scope. Inspection's doc_kind is
`inspection_service_checklist`; its policy profile is `inspection`.
`reference.json` retains `pages: list[str]` and `coverage: object`; auxiliary
reference metadata is permitted. Neither object enters prediction extraction.

`policy.json` has schema=`eld-mapping-v2-policy/1`, fixture_id, family_id, case,
profile (`work_order`, `service_invoice`, `inspection`), page_count=1,
catalog_sha256 (exact catalog.json bytes), ideal_native (nonempty faithful ideal
native witness), tables and slots. Profile here is reference-side metadata only;
the future mapper must infer context solely from native output. Each tables entry
has table_id, column_ids (catalog canonical order) and unique nonempty row_ids in
source row order. Expected tables retain the same table and row order, including
empty cells objects when all row truth is ambiguous. Original exact scoring only
has adjudicable known cells in its denominator; the full policy universe remains.

Each slot has kind (`field`, `cell`, `absence`), page_number=1,
truth_status (`known`, `ambiguous`, `unknown`), action (`assign`, `abstain`), reason,
truth and evidence. Field/absence slots have field_id. Cell slots have table_id,
row_ordinal (zero-based within that table), row_id and column_id. Identities are
unique; a field cannot also be an absence. Every declared table row and column
has exactly one cell policy slot, even if semantic truth cannot be resolved.

Known field/cell truth contains printed_text, normalized_value, value_type and
optional quantity_unit. Presence and exact value of quantity_unit are bound;
empty unit strings are rejected. These keys must exactly match the corresponding
unchanged expected slot. Known absence truth is
`{"printed_text":"", "expected_state":"absent_blank"}` and must match an
expected_absences entry with that state. Ambiguous/unknown truth is null and has
no expected value/absence entry. Conflicting values must not be resolved by picking
the first source occurrence. Duplicate-equal values may have known truth while
requiring abstention; that can reduce original end-to-end accuracy while satisfying
the guard policy. Abstention is never counted as an exact field or cell.

Evidence is a nonempty list of source occurrences, each with label_printed,
value_printed (string or null when unavailable), label_bbox_pt (four finite page
points) and value_bbox_pt (box or null). Field/absence label is the exact printed
label; cell label is its printed column header. Known field/absence expected
label_printed must equal at least one evidence label. Known slot truth must have
an exact matching evidence value. Distinct boxes/values retain duplicates rather
than deduplicating them. Evidence is reference-side admission material, never
mapper input. A validator cannot prove that boxes or the witness match the PDF;
independent visual admission remains required.

Reasons are `supported`, `duplicate_equal`, `conflicting_values`,
`header_collision`, `unsupported_vocabulary`, `missing_structure`,
`ambiguous_profile`. assign requires known truth and reason supported; abstain
requires a different reason. A supported case has only assign slots. A conflict
case contains at least one duplicate_equal, conflicting_values or header_collision
abstention. An unsupported case contains at least one unsupported_vocabulary
abstention. Unaffected slots retain their declared action; case labels never
override per-slot policy. Catalog spelling/structure admission is independently
checked against the source document and ideal witness before implementation.

All three cases within each family bind the same slot identities/table row IDs.
Whenever semantic truth is known in multiple cases it must agree byte-for-byte,
including unit metadata and absence meaning. Ambiguous cases do not supply a
replacement answer. Different families use independently created fictional facts.

The CPU entry point is `python -I -B qualification/mapping_v2/protocol/cli.py
validate --expected PATH --reference PATH --policy PATH --output NEW_PATH`.
Only the custodian/reviewer may use it on their authorized sealed material. The
author uses exposed historical material and public tiny synthetic tests. There
is no execute/model or v2 prediction command in /001.
