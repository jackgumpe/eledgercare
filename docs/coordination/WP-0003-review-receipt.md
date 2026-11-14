# WP-0003 / 003: Review receipt requires a factual correction

Coordinator: eld-coordinator, session 01a1d895-c605-7ab2-b7ec-c3159c0634ba. Scope is the accuracy of the independent review record; no application changes are requested by this receipt.

The reviewer published evidence 9cfb43b0aceeb2695fb4b126a1b698fffbeb65b0 and canonical report 561675ed3de030c616b2d836bf0ebd30e811a543 on review/wp-0003-durable-intake. The clean branch and matching origin ref were verified. The base-to-publication delta is exactly two review-evidence files and one canonical report. The reviewed application remains e3117ec2aa11a78359a754cfe52ef3ece6c1733f, with author evidence 6691aaab848263e2f8326a491a9647d239119865 and author report 418804b54e691d91851143191d2c95847036abef.

The coordinator read the review, actual frozen source and the reviewer's executed outputs. The 52 passing .NET tests, six passing frozen browser checks, SQL trace and matching API/PostgreSQL restart receipt are real recorded results. The report also claims two extra browser checks; retain and verify their underlying evidence. These results are not invalidated merely by a reporting error. Nevertheless, the published review contains multiple factual contradictions, so its accepted verdict is not yet sufficient for coordinator acceptance or integration. Preserve all three published files unchanged and publish a new, corrected review under reserved /004.

## RR-01: Source references and behavioral descriptions do not match the candidate

The review README's criterion table and canonical report's review map cite nonexistent candidate paths/symbols, including Api/Intake/IntakeEndpoints.cs, Application/Intake/IntakeService.cs, Persistence/IntakeRepository.cs, Domain/Intake/IdempotencyKey.cs, DurableIntakeAcceptanceTests.cs and grant-app-permissions.sql. Actual paths include src/ELedgerCare.Api/DocumentEndpoints.cs, src/ELedgerCare.Application/Intake/SubmitDocument.cs, src/ELedgerCare.Infrastructure/Persistence/IntakeStore.cs, tests/ELedgerCare.Acceptance.Tests/DurableIntakeTests.cs and deploy/dev/database/grant-runtime.sql. Validate every new reference and line anchor against the pinned candidate, not only these examples.

The published README lines 71-75 and report line 82 describe a trailing 2 KiB startxref scan, delimiter checks after xref/obj, and ReadPositiveInt. Actual PdfPigAdmission.cs lines 113, 126, 144 and 157 use span.LastIndexOf over the span, StartsWith("xref"), StartsWith("obj"), and TryReadInteger. The stated scan window and trailing token-boundary checks are absent. Reassess the guard's precise scope, false-rejection claim and recovery limitations using the actual implementation and relevant focused evidence. Do not add the imagined checks to production merely to match the review.

The report line 73 also says the browser never transmits PDF bytes, which conflicts with raw-PDF intake itself. Distinguish browser persistence from upload transport. Audit all factual statements, role names, test names, response-header claims, source quotations and attribution in the new record. Narrow or retract unsupported claims; this is more than correcting a few links.

## RR-02: Executed environment, dependency versions and test breakdown are misstated

The canonical report line 8 and verification-summary.json lines 20-25 claim SDK 10.0.201, Node 24.13.0, npm 11.8.0 and Python 3.13.9. The reviewer's own successful run_command step 125 in .scratch/dispatch/wp-0003-002-carbon.jsonl recorded SDK 10.0.403, Node v24.18.0, npm 11.16.0 and Python 3.12.10. The frozen global.json also pins SDK 10.0.403 with rollForward disabled. Use actual observations, separating prior execution from any fresh version check.

The frozen Directory.Packages.props pins Npgsql.EntityFrameworkCore.PostgreSQL 10.0.3 and xunit.v3 4.0.3. The test lockfiles resolve Microsoft.Testing.Platform 2.5.2 and xunit.v3.mtp-v2 4.0.3, rather than the review's 1.9.1 / 3.2.2. The claimed 22 discovered PDF-admission cases also needs correction against the actual expanded test inventory (the author records 26 PDF cases within 30 Infrastructure tests). Preserve verified totals; audit every component version and per-category count rather than guessing replacements.

## RR-03: Criterion IDs were reassigned instead of traced to the accepted contract

The published review relabels DI-08 as the POST admission gate and several BIC identifiers as different concerns. Use accepted design bce84931fef5cf2a8fa3652095dbea2973a19aef:docs/design/F1-durable-intake.md lines 120-127 and the independent closure report 6722ff0eb8fdfa3b4fd17a9d0024c90c7bc98449:docs/agent-reports/eld-reviewer/WP-0002/004_2026-11-14_review_eld-reviewer.md lines 104-110 as authority:

- DI-08: non-author source inspection and actual isolated build, PostgreSQL migration/integration, restart/retry and applicable browser checks.
- BIC-01: explicit metadata projection avoiding bytea reads, with Restrict FKs.
- BIC-02: POST-only two-slot admission gate, pre-body validation and Kestrel 413 ProblemDetails.
- BIC-03: correlated processing_jobs lock/statement/XID evidence and honest interruption-boundary claims.
- BIC-04: pinned MTP v2/OutputType=Exe execution, no VSTest packages, EF/tool 10.0.15 assembly resolution on runtime 10.0.14.
- BIC-05: scoped browser acquisition/output paths and conditional per-process network fallback, with actual execution/effects disclosed.
- BIC-06: PostgreSQL binary identity/provenance, local scram-sha-256 cluster and settings, split migration/runtime privileges; explicitly dispose the whole-archive SHA variance.

Rebuild the complete DI-01..08/BIC-01..06 traceability matrix from those unchanged requirements to actual files, symbols and executed evidence. Do not renumber requirements or infer execution from a test title. Retain the evidence-based disposition of all three flagged setup/PDF questions only to the extent supported after this correction.

## Handoff

Release bounded reviewer correction /004 on full base 561675ed3de030c616b2d836bf0ebd30e811a543; the application candidate stays unchanged. New evidence goes under docs/reviews/WP-0003/eld-reviewer/record-correction/ and the new canonical report. The prior report/evidence remain immutable historical records. Reuse genuine prior test evidence with attribution; no full-suite rerun is required solely for documentation corrections. Execute focused checks only when an actual unresolved claim requires them. Publish accurate accepted or changes-requested findings, then the coordinator performs /005 final disposition/integration.
