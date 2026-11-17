# WP-0010 /005: Final verification of the searchable source-linked archive

- Report path: `docs/agent-reports/eld-coordinator/WP-0010/005_2026-11-17_verification_eld-coordinator.md`
- Reservation: WP-0010/005 in [INDEX.md](../../../../INDEX.md), under [Jack's bounded authorization](../../../coordination/WP-0010-0011-authority.md).
- Category / author / publisher: verification; **eld-coordinator**, sole coordinator.
- Actual model / effort: not exposed. Assigned Carbon author and independent reviewer used gemini-4-carbon-high/high; fresh Codex sessions remain restricted to requested xhigh.
- Environment: Windows PowerShell, CPython 3.12.10 and Git; independent application checks used .NET 10.0.403, PostgreSQL 18.7, Angular 22.2.6 / CLI 22.2.7 and real Edge 157.0.4341.60.
- Timestamp: 2026-11-17T12:16:12.815636+00:00.
- Repository / branch / worktree: private jackgumpe/eledgercare; coordination/bootstrap; C:/Users/jackg/Asp.net Projects/eledgercare.
- Authorized base: **956c056be2ec970340074871ecdd7e1a9855d944**.
- Accepted product source: **c1fed68020ae67e8b4763bc6ea5473adaa86de2b**.
- Frozen integrated disposition: **43ad69569a7a7f610e058bc076daa237f346aeba**.
- Post-deliverable preservation evidence: **202f704c89c8d1cbca082b25ed098c21bd3b3810**.
- Previous coordinator product report: [WP-0008/005](../WP-0008/005_2026-11-16_verification_eld-coordinator.md), publication 3282b9db7b7f05bbb14fd000591a732bbda581bc, unchanged.
- Related reports: original [author003](../../eld-f4-implementer/WP-0010/003_2026-11-17_implementation_eld-f4-implementer.md), [independent004](../../eld-f4-reviewer/WP-0010/004_2026-11-17_review_eld-f4-reviewer.md), correction [author006](../../eld-f4-implementer/WP-0010/006_2026-11-17_implementation_eld-f4-implementer.md), final [independent007](../../eld-f4-reviewer/WP-0010/007_2026-11-17_review_eld-f4-reviewer.md), publication **ce4109a1515af1a8583a208e8085f2fa3bfa2d72**.
- Status: **accepted and integrated; WP-0010 complete**.
- Next owner: root publishes this report's receipt/routing; Jack controls any next bounded lane.

## Outcome and acceptance

F4 completes the authorized local workflow: submit/extract, compare and review, find a saved document through machine text or reviewed values, then reopen its original/source and review history. Results distinguish machine extraction from the latest explicitly reviewed revision, mark newer drafts, and link matching pages/fields. Retrieval survives PostgreSQL/API restarts with OCR disabled. Existing original bytes, raw extraction, attempts, provenance and immutable history remain intact. This remains the synthetic one-to-three-page scope.

The [accepted design](../../../design/F4-source-linked-archive.md) passed independent002 before implementation. Final source passed independent007 after a narrow navigation correction. The [disposition](../../../coordination/WP-0010/final-disposition/README.md) binds the exact source/evidence chain and limits. No product code imports the research/evaluation mapper; F4 validation made no model calls.

## Change inventory and decisions

The [complete integrated inventory](../../../coordination/WP-0010-0011/final-preservation.json) accounts for **932 changed paths**, verifies **2570 protected historical paths**, all six accepted product/research/corpus trees and **22 publication ancestries**. Its [execution receipt](../../../coordination/WP-0010-0011/final-preservation-execution.json) records the frozen helper, candidate, command and exit 0. Every before/after Git identity and changed-file size/hash is retained.

| Group | Delivered change |
| --- | --- |
| Application/domain/API/infrastructure archive code | Bounded literal-query contract, snapshot-consistent search, keyset pagination, strict raw request/cursor validation and source-linked evidence |
| PostgreSQL migration/initialization and grants | Immutable machine projection/units, atomic result publication, bounded existing-result backfill, readiness gating and restricted runtime privileges |
| Archive screen, routes and review return links | Source-labelled matches, original-page/review-revision navigation, pagination, draft indicators and preserved newer input/search authority |
| Tests, isolated runtime helpers and dossiers | Genuine attributed F2 seeds, real PG/Edge proof, inventories, screenshots, failures and independent review |
| Coordinator documentation | Accepted design, exact role/resource releases, audits, reconciliation, final disposition and integration preservation |
| Parallel WP-0011 changes | Separately accepted controlled diagnosis/corpus/results; complete inventory includes them without treating them as product code |

Post-deliverable metadata consists of preservation evidence, this report and the later publication/routing receipt. Normal commits/pushes and isolated local test resources are the external effects. Retained databases remain present; owned services are stopped. No customer data, deployment or model treatment was introduced.

Search requires every literal term within the same document's eligible sources, preserves punctuation/leading zeros, escapes SQL wildcards and applies matching rules consistently to snippets. Reviewed search uses the latest explicit reviewed revision; unknown fields remove prior reviewed values, and newer drafts remain distinct. Immutable projection markers handle even empty results; result publication is atomic and backfill is bounded. A read-only repeatable snapshot keeps result evidence coherent.

## Actual verification

| Check | Evidence / result |
| --- | --- |
| Independent design002 | Publication85d879a1adc0ee62090f4c6a5c9a7fb8eb5f3a96;56 CPU assertions/zero blockers |
| Original author003 | Source c383021be1774451ba3034d89255b38b4267353b;15 steps including95 .NET / 15 Edge / 9 worker CPU tests, migration, privileges and restart |
| Original independent004 | Publication324f09934b0aa2ee8e7bed7e8118c6109effb918;16 steps / 34 assertions,95 .NET / 15 Edge / 9 worker CPU tests, independent nine-document seed,31 query cases / 23 raw 400 cases / 19 privilege probes, real PG/API restart |
| Controlled original-code reproduction | Preparationb12664dfbfd533f177a4e1089c983952d485b8c2; six real Edge navigation scenarios, four failures/two passing controls, zero arbitrary sleeps |
| Correction author006 | Publication0f689d9b6eaf415d17095f14ad57dff2d716bac5;6 steps / 16 Edge regressions / 5 controlled checks and retained-source/history reopening |
| Final independent007 | Publicationce4109a1515af1a8583a208e8085f2fa3bfa2d72; helpers fbbc46261b6dec4b1273c7391f58712f9ac17465; 7 steps / 30 assertions, 16 Edge regressions, all six unchanged navigation scenarios, three supplementary checks, 31 saved queries and source/history reopening passed |
| Root evidence/publication audit | Exact inventories, unchanged prior paths, attributed inputs, report-only commits, local links, resource return and exact origin verified; [final audit](../../../coordination/WP-0010/search-navigation-reviewer-audit.json) |
| Root integration preservation | Frozen candidate 43ad69569a7a7f610e058bc076daa237f346aeba; 2,570 protected files/932 changes / 6 trees / 22 ancestries; PASS/exit 0 |

The original independent004 helper waited for route settlement before checking obsolete HTTP suppression. Its retained earlier attempt showed a distinct newer-input overwrite during pending navigation. Root held acceptance rather than accepting the reviewer's timing-based dismissal. The reviewer independently reproduced four failures and retracted that inference in new evidence. Author006 corrected ownership of self-initiated navigation while preserving external URL behavior; the same prepared failure cases pass in final007. Original reports and failures remain immutable, with no unresolved disagreement.

The correction changes only archive-page.ts and its browser regression file. Exact backend/deploy/worker/dependency identities preserve original004 backend, migration, privilege and restart evidence; final007 freshly tests the affected frontend. No repeated backend or GPU execution is claimed. Retained independent core/projection digests remain841a3c0a2fc6ff5bbf29d6da1feff35b53c0c35be33a89a9ea03cfe2c1a2c993/0faf93dc12d8596df7435628ac3b797b8a703c8f0cd68614e11b9d8bb39c63fa.

Root inspected the final screenshot of the preserved newer draft subsequently submitted as WO-004724-MP-LINKED, its matching reviewed-revision card, and the linked readable three-page PDF opened at page2 beside pinned revision1. Root also directly observed all bound author006 and independent007 test-service PIDs absent and ports free in the [author](../../../coordination/WP-0010/search-navigation-author-stopped.json) and [reviewer](../../../coordination/WP-0010/search-navigation-reviewer-stopped.json) observations. These are actual image/process inspections, distinct from attributed runtime checks.

## Limits and handoff

No unresolved acceptance finding or required work remains. Small-seed default query plans used sequential scans; index existence/forced usability is not a measured speed benefit. Human review is a user decision, not authenticated identity or factual certification. Search is bounded keyword retrieval; general structured extraction, semantic search, customer data and deployment remain outside this lane. OS outbound network isolation remains unverified.

Meaningful failures are preserved: the true navigation defect, earlier fixture/expectation/helper corrections and their failed executions. Post-publication provider DNS/resultERROR endings are separate from successful frozen tests and exact remote publication. No CLI SUCCESS is inferred; original003's wrapper exit remains unknown. Final turn completion details are in the root receipts.

Parallel WP-0011 is already accepted at coordinator007 062b5f54c106305bb6ade6a493d86e95723a1eb9. On three matched families, unchanged v1 produced69/92 fields versus B0 42/92; both 129/172 cells. Unfamiliar wording remained0/23 fields and 0/43 cells despite 66/66 expected values present. These are pipeline metrics, not character accuracy or generalization evidence. All twelve exposed documents are now regression material; both leases are returned, and no treatment or further inference is authorized.

Root records this report's publication SHA in the later receipt and marks both tracks complete. No further implementation, review or user permission is pending within the authorized lane.
