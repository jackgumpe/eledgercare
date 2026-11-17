# Independent WP-0013 protocol review

Disposition: **accepted for the bounded public protocol stage**. This is an
independent review of author /001 at
`9b90528f4dbd0ea1ff61c86d0d4040decf178a0a`, source
`6207daf1dc9cbdd141d083ca2d8d1e7507c63b09`, mapping_v2 tree
`e424945507bb1d7ebf70e18e6d26bf808270bb66`. It does not accept a mapper,
corpus, runtime adapter or inference result; none is implemented or evaluated here.
Root release is
`45817cfb7f56c119986b8e4f5bb7cc3ea252d56f:docs/coordination/WP-0013/protocol-final-review-release.json`.

The [start record](start.json) retains both exact review inputs. Source
`66204677ee7c84a13c98bf1702d03640e603745f` was inspected after the first merge;
no decisive executable check used that early source. The final author publication
was normally merged to clean review base
`dc69bbabfb233cb021b3edd5ddb7264119ca081c` before helpers and decisive execution.
The only early-to-final source changes distinguish exact header punctuation from
the single optional field colon and add the matching negative test.

## Independent findings and disposition

| Checkpoint | Evidence and disposition |
| --- | --- |
| P13-01: empty and partially known rows | Resolved. Final validation requires a known canonical row-key cell in every expected row. Independent empty-row and missing-row-key mutations reject at that guard. A partially known row retains the original one-row credit and one original extra_cell, while policy retains its ambiguous opportunity and reports zero out-of-universe surplus. Original row credit means declared-known-cell agreement, never whole-row semantic certainty. |
| P13-02: affected canonical-only tables | Resolved in the public policy. Canonical-only tables in the unique active native profile are explicitly affected and suppressed before all guard decisions. Alias/header collision and missing/ambiguous profile paths cannot silently reuse affected v1 output. Enforcement remains an implementation /005 and source /006 obligation. |
| First-candidate score credit versus policy | Resolved by separate accounting. An equal duplicate still receives historical first-candidate field credit but has two policy candidates, a surplus candidate within its slot, no strict-single-candidate credit, and a required-abstention violation. Conflicting/blank/duplicate-table/duplicate-column candidates and out-of-universe output remain visible. |
| Ambiguous, unknown, unavailable and abstention | Preserved separately. Assigned and withheld ambiguous/unknown slots never receive exact-value credit. Failed/not-run/invalid-parser/missing-page/empty-block/unsupported-markup observations retain opportunities and observed candidate counts, with no eligible correctness or successful-abstention credit and null conditional rates. A mixed full frame retains 12 documents/four families; only three eligible families contribute to that conditional macro mean. |
| Context and scope | Accepted as a prospective finite treatment specification. Profile selection uses one complete unique native table-header resolution; no fixture/family ground truth routes extraction. Exact NFC/trim dictionary matching, page-wide duplicate counting, structural/value guards, affected-output suppression, and no nearest/fallback repair are explicit. Four families each have three conditions, not twelve independent families. |
| Frozen comparators and public-only development | Exact B0/v1/coverage/Q0 pins pass. Full B0/v1 predictions and full score objects reproduce on all 12 exposed WP11 documents. No v2 extractor exists in this source; the scorer accepts provided prediction objects solely for protocol tests. No private foundation/corpus, live observer, model, service or download was accessed. |

The finite 26-field/absence-alias and 17-header catalog is source-attributed to
already exposed WP11 inputs. The validator/scorer provides an adequate finite
interface for later independent admission; it cannot prove that evidence boxes,
truth, ideal-native witnesses or declared guard reasons actually match rendered
documents. Admission must establish those facts from the reserved originals.
Known quantity-unit identity is retained across paired references; historical
typed quantity comparison remains numeric-magnitude scoring after unit validation.
No new unit semantic score is silently substituted for the frozen comparator.

## Actual CPU checks

All three decisive semantic phases used frozen helper commit
`a75bc9c4ee1b2be26ca23acbede886a1cae424fe` against the final candidate. The helper
imports are guarded against model/backend/raster imports. The public examples
are independently constructed prediction/reference probes, not a mapper or a
copy of the author's test fixture.

| Command (relative to this worktree) | Actual result | Evidence |
| --- | --- | --- |
| `python -I -B docs/reviews/WP-0013/eld-mapping-reviewer/protocol-review/review_checks.py probes --out docs/reviews/WP-0013/eld-mapping-reviewer/protocol-review/attempt-1/probes` | Exit 0; 35 independent checks passed. | [Results](attempt-1/probes/result.json), all names, values and exceptions retained per check. |
| Same helper, `author-tests --out .../attempt-1/author-tests` | Exit 0; independently executed all 26 candidate tests, zero failures/errors/skips. | [Results](attempt-1/author-tests/result.json), [actual test stream](attempt-1/author-tests/author-tests.txt). |
| Same helper, `history --out .../attempt-1/history` | Exit 0; direct unchanged extraction and original scoring reproduce all 12 complete B0/v1 prediction and score objects, independently compared with old WP11 packets and new protocol wrapper. | [Results](attempt-1/history/result.json), 37 actual input identities and 12 complete-object digest pairs. |

These executions ran 2026-11-17T14:26:25Z through 14:26:36Z. Each result binds all
77 actual candidate/comparator/core source files, Git blobs, committed and working
byte identities. [Actual tool receipts](attempt-1/tool-receipts.json) retain
original process/session/exit outputs, including the historical phase's separate
completion receipt.

## Publication evidence and retained reviewer failure

The initial frozen `audit_inventory.py` incorrectly compared the author's
recorded working-byte identity directly with this reviewer's checkout for every
file. It failed on the author's `.gitattributes`: original/committed bytes are
30; this checkout has 31 bytes because of CRLF. That actual failed audit and
original helper are retained in [attempt-1/author-audit.json](attempt-1/author-audit.json).
This is a reviewer audit-method error, not a candidate source or evidence defect.

The corrected separate `audit_inventory_v2.py` was frozen at
`66c69cf83d50a6f12cc280f0023ba991802f7ef2` before re-execution. It compares author
working bytes, committed objects and reviewer checkout representations separately,
while requiring exact evidence bytes. The [second audit](attempt-2/author-audit.json)
and [actual receipt](attempt-2/tool-receipt.json) pass: 33 complete deliverable
entries, all 3,615 original base objects unchanged, two post-deliverable metadata
additions only, all 14 source and 41 input identities for each attempt, six actual
original capture copies exact, and 11 report links valid. All author's original
working representations match their inventory; only the reviewer's non-evidence
`.gitattributes` differs by the explained newline representation. Author execution
receipts remain attributed to the author; independent runs above are separate.

No semantic test failed or was rerun for this audit correction. Earlier preliminary
reviewer invoice-target metadata correction and all initial proposal probes remain
unchanged at `fd9e6b9da0e8aa3aadaa18d9261f6e69b7ee4557`. The independent review
does not overwrite author attempts or hide the initial 25-test source.

## Limits and handoff

No final fresh corpus exists in this review input; the foundation-only reservation
does not establish rendered-case membership or ground truth. Implementation may
proceed only after root separately binds the final reserved originals and this
protocol acceptance. The future runtime adapter's finite 14/3-call schedules,
first-failure stopping, no retry, source/input receipts, process cleanup and lease
boundary must be implemented and independently reviewed in /006. The sentinel
remains `WP13-F04-conflict-v0`; no selection change follows results. Product gets
the first GPU slots. No current execution release or source-quality result is
inferred from this protocol acceptance.

The catalog's deliberate public exposure tests fresh facts/layouts and guard
behavior, not unseen-vocabulary discovery. Conservative guards may reduce valid
historical first-candidate credits. Gains, losses, neutral results, failed cases
and all truth-status denominators must remain visible. Root alone owns shared
routing and each later gate.
