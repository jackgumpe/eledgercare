# Frozen proposed treatment and measurement rules

## Scope and prediction boundary

One treatment is proposed: a finite exact alias/schema mapper with mandatory
abstention guards. The catalog contains 26 field/absence aliases and 17 headers
from three exposed WP11 vocabulary documents. Each entry records its canonical
target and exposed source. There are no known values, fresh fixture identities,
expected boxes or reference-side profiles in extraction. No replacement in raw
text, fuzzy matching, case folding, whitespace collapse, unit repair or model
change is allowed. B0, v1, coverage_v1, typed conversion and original scoring
remain immutable. Actual v2 implementation is held until accepted /002 plus
exact fresh reserved bytes are bound by root.

## Native profile and table requirements

Only a fully parsed native table can establish profile context. Its first
nonempty row must resolve each complete cell, using exact canonical or alias
headers in one catalog schema, to a unique canonical column; all and only that
schema's columns must appear once. Mixed canonical/alias headers and column
permutations are allowed because the resulting full bijection is explicit.
Every header/data cell must have unit row/column spans. Header colons are not
stripped. A complete valid header gives profile evidence even if a later data
row fails a guard. A page must have exactly one distinct profile and exactly one
candidate table for its schema. Multiple tables for the same schema are duplicate
schema candidates; multiple different profiles are ambiguous. Both abstain from
alias mapping. Missing/invalid native structure cannot be inferred from the PDF.

All rows must have exact header width, and the schema row-key column must contain
unique nonempty exact strings. Empty keys, duplicate-equal keys, duplicate
conflicting keys, repeated headers, spanning or short/long rows make the entire
affected table abstain. Native header order determines column correspondence;
native data-row order remains unchanged. No row sorting, padding or inferred
cell values. Unknown headers are unsupported. A header collision is a row
containing two recognized headers for one canonical column; it never chooses the
first or last. No valid table profile means no alias field assignment.

## Field identities, association and suppression

Text matching uses original NFC and outer trim only. One terminal label colon
is optional; internal whitespace and case remain exact. Complete labels in
cells/blocks and inline labels followed by a colon or whitespace boundary are
recognized; substrings inside words are not. Counts include canonical and alias
occurrences throughout the native page, including prose. A label-like value is
unsafe. Counts are by canonical target, not spelling or chosen value. Exactly
one occurrence is required, even when duplicate values agree.

Supported structural associations are: an inline label followed by one nonempty
payload in the same native text/cell; an immediate right cell in a unit-span
non-data table row; the cell directly below in the next equal-width row; or one
separate non-table/non-footer text block satisfying the unchanged B0 coordinate
thresholds (right with vertical difference <=5, or below gap 0..25 and left
difference <=12). All qualifying candidates are counted. More than one possible
orientation/value occurrence, an empty value, a value containing any recognized
field label, unknown trailing label with colon, or an intervening additional
plain cell causes abstention. No nearest-candidate tiebreak or recursive fallback.
An explicit empty field may be emitted only when a unique recognized label has
one structurally explicit empty adjacent cell and no nonempty candidate. This
allows original absence verification without inferring absence from omission.

The affected field set is every catalog field in a unique active native profile,
plus any canonical target whose catalog alias occurs on the page even if profile
selection fails. For these targets v2 must suppress every v1 candidate first,
then emit at most one guarded assignment or none. Rejected right-neighbor
association must not fall back to old below-row/inline candidates. Canonical plus
alias duplicates and duplicate-equal values remain abstentions. For multiple or
missing profiles, alias-affected fields abstain; unrelated untouched v1 results
remain visible. In a unique profile its canonical fields use the same guards.

Any catalog alias header or collision in a table's first nonempty row marks the
corresponding schema affected; its v1 table output is suppressed before guarded
resolution. Multiple-profile/duplicate-schema context suppresses all involved
catalog tables. Unaffected v1 predictions are copied unchanged. This permits an
explicit regression where a formerly credited first candidate is now withheld.
The later mapper must retain reasons/native locations in a diagnostic decision
trace, but policy scoring counts actual output candidates, not self-reported
success. No expected policy object is passed to the mapper.

## Original scores and independent policy counts

For each unchanged raw document, B0/v1 use their frozen extractors. The future v2
extractor receives only parsed native output and the catalog. Every prediction
is passed unchanged to original `score_document(pred, expected, reference,
completion)` and original summarize. The B0 scorer's first field candidate and
ordinal table-row semantics are preserved, including surplus accounting. Typed
quantity credit validates supported units but compares numeric magnitude; it is
not unit-semantic correctness. Literal quantity-unit/identifier diagnostics from
coverage_v1 may be retained separately without changing scores.

Separate policy scoring groups all field candidates by page/field identity and
cell candidates by page/table/zero-based row ordinal/canonical column. Row ordinal
resets per emitted table, so duplicate tables contribute multiple candidates to
the same opportunity. Repeated output columns likewise retain every candidate.
Blank candidates are assignments, not abstention. Field and absence identities
share one candidate pool. Unknown output identities/rows/columns are surplus
assignments and never disappear from accounting.

For each scheduled slot report truth status, action/reason, candidate count,
values and assignment provenance. Completed parse-valid native evidence with no
unsupported visibility grammar is eligible. A missing native page, parse error,
failed/not-run document or unavailable visibility makes every slot unavailable:
no recognition or abstention success is inferred. Still retain observed candidate
counts separately for those unavailable rows.

Among eligible known-truth candidates, count exact printed assignments and
incorrect assignments individually. Duplicate-equal assignments may both match
the value, but strict-correct-slot credit requires exactly one candidate. Semantic
ambiguous/unknown assignments are counted separately and receive neither exact
nor incorrect semantic credit. Surplus assignments are unjudged, never dropped.

Report coverage as slots with any candidate / all policy slots and also / eligible
slots, with unavailable counts. Report abstentions as eligible slots with zero
candidates, split by truth status and required action. Required-abstention
violations count every eligible abstain slot with any candidate, including blank
and duplicate-equal output. Zero-candidate required-abstention observations are
reported separately for known/ambiguous/unknown truth; they are policy observations,
never an exact-value correctness measure or proof of semantic success. Do not
combine exact assignments and abstentions into an overall accuracy rate.

All 12 scheduled documents and four families remain in the frame. Failed/not-run
rows keep their full expected and policy denominators; conditional rates show
eligible and unavailable counts, with null for empty eligible denominators.
Summaries report pooled counts, each case, each family, and equal-family means
with the number of families supplying eligible denominators. Pairwise B0/v1/v2
deltas are on the identical raw outputs. No causal independence is claimed among
the three cases in a family, and no unseen-alias generalization is claimed.

## Finite later runtime specification

Author order: historical SYN-WO-01-v0-clean and SYN-MP-01-v0-clean as two excluded
warmups, then F01 supported/conflict/unsupported through F04 in family order.
Independent reviewer: the same two excluded warmups, then only
WP13-F04-conflict-v0. One cold load per owner; first unexpected inference or
infrastructure failure stops without retry, substitution or hidden calls. All
remaining planned cases become not_run_after_failure. No source/catalog/scorer
changes after fresh evaluation begins. The later adapter must preserve accepted
coverage_v1 first-failure progression and nonzero post-observer rejection, actual
wrapper/worker exits, complete raw/token/render/resource identities and lease
cleanup. It will live only in mapping_v2 and be independently reviewed at /006.
No runtime is executable in /001; product rehearsal has first GPU priority.
