# WP-0002 / 003: disposition of Carbon findings and bounded design correction

- Report path: docs/agent-reports/eld-coordinator/WP-0002/003_2026-11-14_verification_eld-coordinator.md.
- Reservation: INDEX.md at 4ecc3ffe1d2842decf19ecdcfec0f5424fb4ac8b, WP-0002 / 003, bound before correction.
- Category / author: verification / eld-coordinator.
- Actual model / effort: not exposed; requested labels are not backend identity.
- Session: 01a1d895-c605-7ab2-b7ec-c3159c0634ba, local Codex/PowerShell on Windows.
- Published by: eld-coordinator.
- Timestamp: 2026-11-14T17:27:23Z.
- Repository / branch: private jackgumpe/eledgercare / coordination/bootstrap.
- Full base: 11926d7021044450aa44a44a893575d0eb98d442.
- Corrected deliverable: bce84931fef5cf2a8fa3652095dbea2973a19aef.
- Previous report: WP-0002 / 001 at 9b49c0f330ea5a71263432cbc3f785b51767b304.
- Reviewed report: Carbon WP-0002 / 002 at 266a80bf7a123496ef0d0c848fbd521b117f4543; evidence b279d28879316939b308cf50b8f5cc792a235775.
- Status: ready-for-review; findings accepted for correction, corrected design NOT self-accepted.
- Next owner: eld-reviewer, WP-0002 / 004; then coordinator /005.

## Disposition

Carbon's actual report/evidence and remote publication were verified. The verdict was changes-requested, with architecture approved in principle. SB-01..03 are valid, bounded specification defects and have been corrected in the cohesive F1 design. There is no substantive architectural disagreement or renewed human product-direction decision. Implementation remains held until the non-author correction review and coordinator release disposition.

| Finding | Correction / evidence reconciliation |
| --- | --- |
| SB-01 | Restrict new submissions to byte-zero PDF 1.0..1.7; explicitly reject 2.0/FDF/leading junk with 422. Preserve strict parser options. Independently inspected pinned FileHeaderParser.cs and confirmed non-PDF-1/FDF-1 header rejection under strict parsing; runtime parser tests remain future implementation work. |
| SB-02 | Require immediate IsEncrypted rejection after Open and NumberOfPages bounds before GetPage; cover empty-user-password owner encryption and over-page-limit inputs. Clarify that application code does not consume/return/persist text while library internals may parse glyphs, inspect local fonts and use fallback recovery. Use embedded/standard-14 fonts in product fixtures. Pinned PdfDocument.cs exposes the required IsEncrypted/NumberOfPages properties; the review's broader source dossier supplies the related internal-behavior evidence. |
| SB-03 | Network errors, timeouts and HTTP 5xx enter unknown-outcome reconciliation with the same key; 429 retains the key and does not classify the original as invalid. A later 429 cannot resolve earlier uncertainty. Add corresponding browser evidence obligations. |
| BIC-01/02 | Carry explicit metadata projection/bytea loading, Restrict FKs, pre-body validation, POST-only concurrency and 413 ProblemDetails into the design. |
| BIC-03 | Specify a processing_jobs table lock and owned-connection/statement/lock evidence. Require honest distinction between observed waiting and a proven earlier completed insert; a lock mode/timing guess is insufficient for the latter. Carbon will reconcile this clarification in /004. |
| BIC-04/05 | Carry MTP global.json/Exe configuration, no VSTest mixing, runtime assembly qualification, local browser/output directories and conditional per-process IPv4 DNS-order fallback into bootstrap obligations. No global network changes or completed builds claimed. |
| BIC-06 | Carry exact PostgreSQL binary identity/hash, SCRAM authentication, local-only cluster and distinct migration/runtime privileges into setup obligations. No server installation/startup is claimed. |
| OPT-01/02/03 | Keep page count internal and clarify GET UUID validation. Optional browser digest caching remains deferred to avoid unnecessary work. |

## Complete base-to-deliverable inventory

| Action | Exact path | Purpose |
| --- | --- | --- |
| Modified | INDEX.md | Record both Carbon report publications; bind coordinator correction and reserve /004 non-author closure and /005 release; bind Astra's single R&D exchange |
| Modified | CURRENT.md | Record completed external Carbon sessions, review findings, R&D handoff, actual remote state and reported incidental development-certificate creation |
| Modified | docs/design/F1-durable-intake.md | Cohesive SB-01..03 corrections, implementation-check carry-forward and scope/claim clarifications |
| Added | docs/kickoffs/WP-0004-eld-rd-astra-exchange.md | Independent-lane exchange release after both initial proposals were published |

Post-deliverable metadata: this exact /003 report and docs/kickoffs/WP-0002-eld-reviewer-reconciliation.md. Published reviewer reports were not edited or reattributed. No application code was authored.

## Verification and external effects

- Read actual Carbon report/dossier on clean review/wp-0002-contract at 266a80bf7a123496ef0d0c848fbd521b117f4543; its base-to-report diff is exactly its dossier and /002 report, preserving the frozen prior design.
- Confirmed the private remote and authenticated jackgumpe account; git ls-remote returned Carbon product report 266a80bf7a123496ef0d0c848fbd521b117f4543 and Carbon R&D report fef02d64aca2594e146930e4a0cb3ec18e355ed5. The GitHub connector also returned the exact review commit/report object.
- Retrieved pinned PdfPig FileHeaderParser.cs and PdfDocument.cs through read-only GitHub requests; confirmed the SB-01 strict-header behavior and SB-02 public properties. This was source inspection, not parser execution.
- Inspected existing agy --help and agy models. The launcher explicitly exposes gemini-4-carbon-high and claude-opus-5-5-high with noninteractive print and conversation continuation. No authentication change, installation or paid account creation was performed.
- git diff --cached --check passed on correction/reservation changes; commits 4ecc3ffe1d2842decf19ecdcfec0f5424fb4ac8b and bce84931fef5cf2a8fa3652095dbea2973a19aef were pushed normally.
- Read Carbon's independent R&D report at fef02d64aca2594e146930e4a0cb3ec18e355ed5 and its independence disclosure. Released Astra's single exchange on exact initial pins in its owned worktree; did not merge or accept either research proposal.

Current-turn effects are scoped coordination/design writes, normal pushes, read-only primary-source/CLI queries, and resumed Astra source exchange. The prior Carbon review reported dotnet test --help incidentally creating an untrusted development certificate; this was not repeated, trusted, or broadly reconfigured by the coordinator. No database/service, package restore, production build/test, model download or GPU execution occurred in this correction.

## Handoff and limits

The exact /004 kickoff binds reviewer branch base 266a80bf7a123496ef0d0c848fbd521b117f4543 and reviewed corrected candidate bce84931fef5cf2a8fa3652095dbea2973a19aef. Its full publication SHA will be communicated after metadata commit. Resume the existing independent Carbon product-review session through its supported launcher; maintain original authorship/independence. After non-author closure, bind /005 and refresh Opus's prepared base/kickoff before release.

All real restore/build, PostgreSQL launch, parser-behavior, durability/retry/UI checks remain unexecuted. Product acceptance, R&D corpus admission and joint-backlog acceptance are still outstanding. Continue only the authorized bounded lanes.
