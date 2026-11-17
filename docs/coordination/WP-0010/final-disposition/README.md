# WP-0010: searchable source-linked maintenance archive

Accepted and integrated within Jack's authorized local synthetic one-to-three-page scope. Final source **c1fed68020ae67e8b4763bc6ea5473adaa86de2b**; author006 publication **0f689d9b6eaf415d17095f14ad57dff2d716bac5**; final independent007 **ce4109a1515af1a8583a208e8085f2fa3bfa2d72**. Coordinator005 and its later publication receipt close this feature. No next feature or treatment is released.

## Delivered behavior

The archive finds saved documents through extracted text or the latest explicitly reviewed field values, identifies the source of each match, and opens the matching original page or historical reviewed revision. Newer drafts are labelled and do not replace reviewed search values. Empty queries browse saved submissions, including honest processing/failure states. Retrieval and history reopening survive API/PostgreSQL restarts with OCR disabled. Original PDFs, raw extraction, provenance, attempts and append-only review history remain intact.

Search uses bounded literal keywords and stable pagination. It escapes wildcard characters, applies the same rules to matching and displayed evidence, and rejects malformed requests. Machine text is projected once into immutable searchable units, including explicit empty-result markers, with atomic result publication and bounded backfill for existing documents. Runtime privileges protect those units. Search imports no research mapper and performs no model inference.

## Exact acceptance chain

| Gate | Frozen source / publication | Outcome |
| --- | --- | --- |
| Design | 01a6dab0695c93246b4cf04d1a2098d3b77248d8 / independent00285d879a1adc0ee62090f4c6a5c9a7fb8eb5f3a96 |56independent CPU assertions; accepted before implementation |
| Original implementation | c383021be1774451ba3034d89255b38b4267353b / author0037c578be6e8abff4d285ea1b519bbcfaeba1bb8c7 |15steps including95.NET,15Edge,9workerCPU and actual migration/restart |
| Original independent review | helpers85d3c36c874026a8e9166f29259fb44755422de0 / independent004324f09934b0aa2ee8e7bed7e8118c6109effb918 |16steps/34assertions; independent9-document seed,31queries,23raw400 cases,19denied privilege probes and restart; original navigation failure preserved |
| Narrow navigation correction | c1fed68020ae67e8b4763bc6ea5473adaa86de2b / author0060f689d9b6eaf415d17095f14ad57dff2d716bac5 |6steps,16Edge regressions,5controlled checks and retained-data preservation |
| Final independent reconciliation | fbbc46261b6dec4b1273c7391f58712f9ac17465 / independent007ce4109a1515af1a8583a208e8085f2fa3bfa2d72 |7 steps / 30 assertions passed; 16 Edge regressions, all six unchanged race probes, three supplementary checks, 31 saved queries and source/history reopening passed |

Root rejected the original inference that a pending-navigation input race was unreachable by humans. The independent reviewer reconsidered the actual source and reproduced four failures with two passing controls on unchanged c383; its new reconciliation retracts that inference while preserving004. The correction changes only `web/src/app/archive/archive-page.ts` and `web/e2e/archive.spec.ts`: self-initiated route completion respects newer input/search ownership, while external navigation still synchronizes the screen. Existing cancellation remains, and stale cards clear during new/error searches. The same original failing scenarios pass in the final independent run. No disagreement remains.

Backend, worker, dependency and migration identities are unchanged by006. Original004's independently executed backend/privilege/restart proof remains attributed to its actual source; it was not unnecessarily rerun. The final frontend has fresh independent browser/build/source-reopening proof.

## Evidence and limits

Root audits cover original [author](../author-implementation-audit.json), [independent004](../independent004-audit.json), [original-code reproduction](../search-navigation-preparation-audit.json), [author006](../search-navigation-author-audit.json) and [final007](../search-navigation-reviewer-audit.json). The complete [final preservation inventory](../../WP-0010-0011/final-preservation.json) and execution receipt bind exact accepted product/research/corpus trees and all protected historical records. Publication metadata is recorded afterward; no canonical report is rewritten.

All owned test services are stopped and retained test databases remain intact. Author006 preserved seed digest76e7970b50b8fbf968c44e534d6383bdd8251e9f285e2373ea026eeeea157085, migrated coread4f44bcf7c0f7163e91cad81f569bfc4642cbb167c1eaf6c3d1ab9984b2e6d0 and projections78f0f273dbdb48629924752cba6f863f11f62764e27161d8df1549ad75ce2ac3. Final reviewer preserves its independently seeded core841a3c0a2fc6ff5bbf29d6da1feff35b53c0c35be33a89a9ea03cfe2c1a2c993 and projections0faf93dc12d8596df7435628ac3b797b8a703c8f0cd68614e11b9d8bb39c63fa.

All meaningful failed attempts remain in their dossiers, including the original race and helper/fixture corrections. Provider DNS/resultERROR endings after successful publication are recorded separately from actual test execution and exact-origin verification. No CLI SUCCESS is inferred from wrapper0; the original003 wrapper exit remains unknown.

Acceptance is local and synthetic. A reviewed value is a user's decision, not factual certification or authenticated identity. Small-seed default PostgreSQL plans used sequential scans; index existence and forced usability do not demonstrate default index adoption or a measured speed gain. The extraction-status and human-review badges describe distinct states. OS outbound network denial remains unverified. No customer-data qualification, deployment, semantic search, generalized structured extraction or model improvement is claimed.

The parallel [WP-0011 disposition](../../WP-0011/final-disposition/README.md), coordinator007062b5f54c106305bb6ade6a493d86e95723a1eb9, is independently complete. It diagnoses wording coverage using three matched families and preserves both unchanged mappers and the original baseline. It does not release a quality treatment or product import.
