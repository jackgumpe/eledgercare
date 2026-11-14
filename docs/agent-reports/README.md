# Product reporting guide

Read AGENTS.md, CURRENT.md and your exact INDEX.md reservation. Use TEMPLATE.md. This guide adapts the ownership/reporting rules inspected at Workspace Ledger commit `7462b744689adba897730ff4b9e35f2194b60950`; it grants no authority in that repository.

Reports: `docs/agent-reports/<agent-id>/WP-NNNN/SSS_YYYY-MM-DD_category_agent-id.md`. Stable ID must agree in directory, filename and author metadata. Categories: research, design, implementation, review, verification, incident. Dates and timestamps use UTC. Sequence is reserved across the entire packet, not per author.

Before work, the coordinator records objective, full base revision, branch/worktree, owner, report path/sequence, criteria and next reviewer. The root seed is the only no-parent/no-base exception. A date rollover must preserve the reserved owner, category and sequence and be reconciled before publication.

Commit deliverables first and pin the exact candidate. Record actual checks, failures, changes and external effects. Commit report/evidence metadata afterward and identify these separately from the deliverable inventory. Do not include secrets, raw private transcripts, or customer documents. Reports may name a prior candidate's SHA, never pretend to include their own publication SHA.

Review actual diffs/source/evidence on exact revisions in the reviewer's own worktree. Record inspection separately from executed/reproduced checks. Report independence and upstream participation. An author cannot accept their own fixes or joint outputs under a new identity.

Push only the owned branch, verify remote objects, and send deliverable SHA, report path/publication SHA and next action to eld-coordinator. If publication is unavailable, state local-only/pending. Only the coordinator edits INDEX.md and CURRENT.md. Published reports are immutable; substantive corrections use another reserved sequence. A push does not start another session.
