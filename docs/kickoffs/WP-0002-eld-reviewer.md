# WP-0002 / 002: Carbon combined startup design review

Status: READY FOR THE REQUESTED CARBON SESSION; NOT STARTED. Product implementation remains held until this review is dispositioned. Missing Carbon dispatch is not permission to impersonate Carbon.

- Stable ID: eld-reviewer, separate from eld-coordinator, eld-implementer and eld-rd-carbon.
- Requested model: Carbon. Disclose actual selected provider/model, effort and session if exposed; otherwise say not exposed. Do not turn a requested name into a claimed backend identity.
- Repository: https://github.com/jackgumpe/eledgercare, PRIVATE.
- Owned branch: review/wp-0002-contract.
- Owned worktree: C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-reviewer.
- Full base and frozen reviewed candidate: e90c71817bc793dfbfc7576006be3cbf0b4310bf.
- Reservation: coordinator INDEX.md, WP-0002 / 002. This separately delivered kickoff supersedes older planned-only routing in the base.
- Exact report: docs/agent-reports/eld-reviewer/WP-0002/002_2026-11-14_review_eld-reviewer.md.
- Next owner: eld-coordinator, reserved WP-0002 / 003 disposition.

Read AGENTS.md, START_HERE.md, the authoritative coordinator reservation, docs/agent-reports/TEMPLATE.md and the assigned candidate. Review together: the supplied 01 contract/02 product brief/03 R&D separation rules; the seed AGENTS/reporting/authority profile; docs/design/F1-durable-intake.md; docs/design/dependency-metadata-2026-11-14.json; and the actual seed verification report. No old checkouts, unrelated transcripts or historical indexes.

Objective: one bounded non-author technical review of the coherent contract/model/F1 design. Inspect actual pinned files, the no-parent seed and dependency/source evidence. Assess transaction atomicity and acknowledgement, UUID retry/concurrent conflict semantics, interrupted/uncertain submissions, strict PDF admission limits, test mechanisms, local-only resource isolation, dependency/runner choices, source/research separation and role/report independence.

Allowed edits: docs/reviews/WP-0002/eld-reviewer/** and your exact report. Owned ignored .scratch/ may hold deterministic inspection evidence. Read-only primary-source verification is allowed. No product implementation, design fixes, shared INDEX.md/CURRENT.md edits, other authors' reports, installations, services, databases, model downloads or GPU work. Do not author a fix and then approve it yourself.

Pins: exact candidate above; SDK 10.0.403, Node 24.18.0/npm 11.16.0; Angular 22.2.6 framework/22.2.7 tooling, TypeScript 6.0.3; EF 10.0.15/Npgsql EF 10.0.3; PostgreSQL 18.7 proposed; PdfPig 0.1.16. Full pins and inspected package metadata are in the design. Treat PostgreSQL vendor build/launch, lockfile resolution, builds/tests and OCR runtime as unexecuted. Docker daemon access failed; no installed PostgreSQL server was established by the bounded checks.

Success: issue accepted or changes-requested for the exact candidate, separating substantive blockers from bounded implementation checks and optional suggestions. Never label document inspection as executed application tests. Preserve unresolved risks (including parser resource limits, server launch and unqualified OCR). If needed, allow one coordinator correction exchange and one evidence reconciliation; then escalate only a substantive unresolved question.

Commit any review deliverable first, then publish your report with full inspected candidate SHA, own branch base/deliverable SHA, complete file/effect inventory, UTC timestamp and actual checks. If the report is the sole artifact, the inspected candidate is its deliverable and the report is a subsequent metadata commit; state that explicitly. Push only your review branch without force and verify remote objects. Return branch, report path/publication SHA, reviewed candidate, verdict and findings to eld-coordinator.
