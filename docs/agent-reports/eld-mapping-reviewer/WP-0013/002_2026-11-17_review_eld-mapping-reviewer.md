# WP-0013 /002: independent acceptance of the finite vocabulary protocol

- Report path: `docs/agent-reports/eld-mapping-reviewer/WP-0013/002_2026-11-17_review_eld-mapping-reviewer.md`.
- Sequence reservation: `47fbc7612e4a08cf1960ad7ac01bd2843ae645e5:INDEX.md`; [review kickoff](../../../kickoffs/WP-0013-eld-mapping-reviewer.md).
- Exact review release: `45817cfb7f56c119986b8e4f5bb7cc3ea252d56f:docs/coordination/WP-0013/protocol-final-review-release.json`.
- Category: review.
- Author / agent ID: eld-mapping-reviewer, stable native `/root/mapping_reviewer`; independent of author and custodian; no subagents.
- Actual model / effort: not exposed; continuing the user-requested xhigh session.
- Execution environment: Windows PowerShell, Python 3.12.10, Git 2.55.0.windows.1; CPU only.
- Published by: reviewer.
- Timestamp: 2026-11-17T14:33:00Z.
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git`, `review/wp-0013-vocabulary`.
- Owned worktree: `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-vocabulary-reviewer`.
- Initial clean reviewer publication: `fd9e6b9da0e8aa3aadaa18d9261f6e69b7ee4557`.
- Final merged review base: `dc69bbabfb233cb021b3edd5ddb7264119ca081c`.
- Reviewed author publication: `9b90528f4dbd0ea1ff61c86d0d4040decf178a0a`; author deliverable `a887615dbc609f245683a46f9333bbd22b66f360`; author inventory revision `76fc3ed5ac71d43496ea4a132d70639da5e4af53`.
- Tested source: `6207daf1dc9cbdd141d083ca2d8d1e7507c63b09`; mapping_v2 tree `e424945507bb1d7ebf70e18e6d26bf808270bb66`.
- Catalog SHA256: `35a99a213b80476747c7a136a4109ac45bc7944c77b0a3dcf0f348f107dd37a2`.
- Protocol SHA256: `aa0d8f183f9f0161c6e47b56a6f2cd844d6ad3f31e772b9761aa0ad618f6a372`.
- Independent semantic helper freeze: `a75bc9c4ee1b2be26ca23acbede886a1cae424fe`; corrected evidence-audit helper freeze: `66c69cf83d50a6f12cc280f0023ba991802f7ef2`.
- Reviewer deliverable: `34af3c179fe8bff6de963b0307902256774f1352`; inventory metadata revision `6bcffe23a433e5d49967243e32466cde9d6b2c69`.
- Inventory SHA256: `0983598143b11b9217f7e9ec9a22e7652d4c77891eedd30e6664012401aa4ac9`.
- Previous report: [WP-0011 /006](../WP-0011/006_2026-11-17_review_eld-mapping-reviewer.md); that lane remains closed.
- Related reviewed report: [author WP-0013 /001](../../eld-mapping-author/WP-0013/001_2026-11-17_research_eld-mapping-author.md).
- Status: accepted, bounded protocol stage only.
- Next owner: root for exact acceptance binding and custodian final reservation; subsequent implementation and review remain gated.

## Summary

Accept the finite public vocabulary protocol, reference contract and separate
policy scorer at the exact tested source. Independent execution passed 35 public
counterexample/positive checks, all 26 candidate tests, and complete B0/v1
prediction/full-score reproduction for all 12 exposed WP11 documents. The author
publication audit passes. No unresolved protocol blocker was established.

This accepts a specification and pure reference/scoring interface. No v2 mapper
or runtime adapter is implemented here. Corpus admission, implemented guard
enforcement, source acceptance and live evaluation remain separate requirements.

## Objective and acceptance criteria

Independently inspect the finite source-attributed catalog, native-only profile
selection, exact matching, conflict/duplicate/header/unknown guards, affected-v1
suppression, unchanged historical comparators and honest candidate/truth/status
denominators. Reconcile preliminary P13-01/P13-02 using the exact final source,
execute meaningful CPU probes and verify complete source/evidence preservation.
The [dossier](../../../reviews/WP-0013/eld-mapping-reviewer/protocol-review/README.md)
records the detailed review map and limitations.

## Decisions and rationale

- **P13-01 resolved.** Every expected table row now requires known canonical
  row-key truth. Independent empty-row and missing-row-key cases reject at that
  guard. Partial rows retain all policy opportunities; original row credit means
  agreement on declared known cells. Original extra_cells can include declared
  unjudged cells and is not an invented-cell count.
- **P13-02 resolved at specification level.** Canonical-only tables in a uniquely
  active native profile explicitly receive the same suppression and guards as
  alias tables. All affected v1 output is suppressed before resolution; rejected
  affected identities cannot re-enter legacy fallback. Actual enforcement must
  be demonstrated by later implementation/source review.
- **Candidate and truth accounting accepted.** Equal duplicates retain historical
  first-candidate credit while policy counts both assignments, surplus cardinality,
  absent strict-single-candidate correctness and required-abstention violation.
  Blank, conflicting, duplicated-table/column and outside-universe outputs remain
  visible. Ambiguous/unknown truth is unjudged; withheld assignments are not exact
  values. Unavailable observations retain denominators and observed candidates
  without successful-abstention or semantic credit. Full-frame summaries retain
  12 documents/four families and disclose conditional macro contributors.
- **Treatment boundary accepted.** The 26 field/absence aliases and 17 headers
  are finite and attributed to exposed inputs. Profile context is resolved from
  complete unique native table headers, not fixture/family ground truth. No fuzzy
  replacement, case repair, inferred values, unit repair or scoring change is
  authorized. Guards may lose historical credit; losses and neutral results are
  valid outcomes.

The first inspected source `66204677ee7c84a13c98bf1702d03640e603745f` was superseded
before independent decisive execution. Its exact two-file correction distinguishes
one optional field colon from exact header punctuation and adds a negative test.
The author retained both passing attempts; this review's header punctuation and
case probes independently pass against the final candidate.

## Change inventory

The [complete inventory](../../../reviews/WP-0013/eld-mapping-reviewer/protocol-review/deliverable-inventory.json)
lists all 15 reviewer additions with byte counts, SHA256, Git blobs and modes.
All 3,663 merged-base paths, including author inputs and preliminary reviewer
artifacts, are unchanged. No source, corpus, shared routing or prior report changed.

| Added paths beneath `docs/reviews/WP-0013/eld-mapping-reviewer/protocol-review/` | Count | Purpose |
| --- | ---: | --- |
| `.gitattributes`, `start.json`, `README.md` | 3 | Exact starts, byte-preserving namespace and independent disposition. |
| `public_examples.py`, `review_checks.py`, `audit_inventory.py`, `audit_inventory_v2.py` | 4 | Frozen public probes/reproduction and retained original/corrected audit helpers. |
| `attempt-1/{author-audit.json,tool-receipts.json,probes/result.json,author-tests/result.json,author-tests/author-tests.txt,history/result.json}` | 6 | Actual semantic results and retained initial reviewer audit failure. |
| `attempt-2/{author-audit.json,tool-receipt.json}` | 2 | Corrected independent evidence audit and actual tool receipt. |

Post-deliverable metadata: `deliverable-inventory.json` and `inventory-receipt.json`
at the inventory revision above; this canonical report is committed afterward.
No external runtime or service resources changed.

## Verification

Actual commands run from the owned worktree are recorded in the
[tool receipts](../../../reviews/WP-0013/eld-mapping-reviewer/protocol-review/attempt-1/tool-receipts.json).
All semantic phases ran 2026-11-17T14:26:25Z–14:26:36Z at frozen helper a75bc9c.

| Executed check | Actual result | Evidence |
| --- | --- | --- |
| `python -I -B .../protocol-review/review_checks.py probes --out .../attempt-1/probes` | Exit 0; 35 independent checks pass. | [Full probes](../../../reviews/WP-0013/eld-mapping-reviewer/protocol-review/attempt-1/probes/result.json). |
| Same helper, `author-tests --out .../attempt-1/author-tests` | Exit 0; 26 tests, zero failures/errors/skips. | [Independent execution](../../../reviews/WP-0013/eld-mapping-reviewer/protocol-review/attempt-1/author-tests/result.json). |
| Same helper, `history --out .../attempt-1/history` | Exit 0; all 12 complete predictions and scores equal old immutable outputs and the new wrapper. | [Direct reproduction](../../../reviews/WP-0013/eld-mapping-reviewer/protocol-review/attempt-1/history/result.json); 37 actual input identities. |
| `audit_inventory_v2.py author --out .../attempt-2/author-audit.json` | Exit 0; 33 author artifacts, 3,615 preserved original paths, both 14-source/41-input inventories, six original capture copies and 11 report links verified. | [Independent audit](../../../reviews/WP-0013/eld-mapping-reviewer/protocol-review/attempt-2/author-audit.json). |
| `audit_inventory_v2.py own --deliverable 34af3c179fe8bff6de963b0307902256774f1352 --out .../deliverable-inventory.json` | Exit 0; 15 additions, 3,663 unchanged paths. | [Inventory receipt](../../../reviews/WP-0013/eld-mapping-reviewer/protocol-review/inventory-receipt.json). |
| `git ls-remote origin refs/heads/research/wp-0013-vocabulary` | Exact author publication `9b90528f4dbd0ea1ff61c86d0d4040decf178a0a`. | Inventory receipt. |
| `git diff --cached --check` | Passed before each owned commit. | Owned commit sequence. |

Each semantic result binds 77 candidate/comparator/core source files and both Git
and working identities. No source trees changed during execution. Author receipts
remain attributed to the author; these independent runs are separately evidenced.

## Failures, limits and unfinished work

The initial reviewer audit failed because it assumed this checkout's working bytes
must equal the author's recorded working bytes. The non-evidence `.gitattributes`
is 30 original/committed bytes and 31 reviewer checkout bytes due to CRLF. Original
helper, actual failure and partial evidence are retained. The separately frozen
v2 helper distinguishes all representations; every author working identity and
all original evidence captures match exactly. This was a reviewer audit error,
not a candidate defect. No semantic check failed or required rerunning.

The preliminary reviewer invoice-target metadata correction remains untouched at
fd9e6b9, with its original and corrected checks. No historical failure is erased.
No private corpus, live GPU/process observer, model import/inference, service or
download was used. Product tests and implemented-v2/runtime tests were not run
because this changes neither product nor implemented extraction/runtime.

Reference validation cannot prove rendered truth, ideal-witness fidelity or
source boxes. Independent admission must inspect all reserved originals. Later
source /006 must verify executable suppression, every guard, full regression,
finite 14/3-call adapter behavior, no retry, first-failure stopping and exact
source/input/process/lease receipts. Four families and one-page scope limit any
later inference; deliberate public vocabulary exposure does not test unseen aliases.

## Review map and handoff

Inspect [policy](../../../../qualification/mapping_v2/protocol/POLICY.md),
[interface](../../../../qualification/mapping_v2/protocol/INTERFACE.md),
[contract](../../../../qualification/mapping_v2/protocol/contract.py),
[scoring](../../../../qualification/mapping_v2/protocol/scoring.py), and the linked
independent dossier/results. [Reviewer base-to-deliverable diff](https://github.com/jackgumpe/eledgercare/compare/dc69bbabfb233cb021b3edd5ddb7264119ca081c...34af3c179fe8bff6de963b0307902256774f1352).

Root may record exact protocol acceptance and coordinate the final reserved corpus.
Implementation /005 still requires that exact reservation; foundation-only custody
is insufficient. Admission, source /006, unseal and later sole runtime leases remain
separate. Sentinel stays `WP13-F04-conflict-v0`, and product rehearsal gets first
GPU slots. No result-driven catalog/scorer revision or user reapproval is implied.

Publication receipt: deliverable and inventory are committed before this report.
A normal owned push, report-only final-diff check and exact-origin/clean verification
follow. The immutable publication SHA will be sent to root without rewriting this
report. Root alone updates shared routing.
