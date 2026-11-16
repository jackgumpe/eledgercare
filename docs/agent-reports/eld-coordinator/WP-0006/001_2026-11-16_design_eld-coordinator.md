# WP-0006 /001: Durable local extraction contract

- Report path: `docs/agent-reports/eld-coordinator/WP-0006/001_2026-11-16_design_eld-coordinator.md`.
- Sequence reservation: WP-0006 /001 in candidate INDEX.md.
- Category: design
- Author / agent ID: eld-coordinator, Codex session 01a1d895-c605-7ab2-b7ec-c3159c0634ba.
- Actual model / effort: not exposed.
- Execution environment: Windows PowerShell and host CPython 3.12.10.
- Published by: eld-coordinator.
- Timestamp: 2026-11-16T04:10:06Z.
- Repository / branch: private https://github.com/jackgumpe/eledgercare / coordination/bootstrap.
- Base revision: `8e80a42c29c0fc27a4af6348cfb1ec22cab3764d`.
- Deliverable revision: `efa9cb986711f82a886f917e68142a7a59319bba`.
- Previous report: WP-0005 /006, publication `8d9334147040e994ca007536bf61974f7de07a61`.
- Status: ready-for-review.
- Next owner: independent eld-next-reviewer; assigned authors as phase gates permit.

## Authority and inventory

Jack explicitly authorized the two-track comparison proposal. The root design candidate changes exactly eight paths: `AGENTS.md`, `CURRENT.md`, `INDEX.md`, `docs/design/F2-local-extraction.md`, `docs/design/B0-vanilla-accuracy-baseline.md`, `docs/kickoffs/WP-0006-eld-f2-implementer.md`, `docs/kickoffs/WP-0007-eld-rd-astra.md`, and `docs/kickoffs/WP-0006-0007-eld-next-reviewer.md`. The shared routing changes bind authority, roles, branches/worktrees, resources and packet-wide report reservations. The paired root /001 reports are metadata added after this frozen candidate. No application, model, scorer, fixture, prior report or external runtime resource changed in this deliverable.

## Verification and limits

Inspected accepted F1 domain/persistence/endpoints, Q0 protocol and final qualification, current admission and experiment protocol, prior isolated worktree/tool setup and exact current remote. `git ls-remote origin refs/heads/coordination/bootstrap` confirmed the base. `git diff --cached --check` passed before commit; `git diff-tree --no-commit-id --name-status -r efa9cb986711f82a886f917e68142a7a59319bba` enumerated the eight declared paths. These are source/design checks, not executed feature or accuracy acceptance. No model run, accuracy scoring, held-out-data read or database mutation occurred. Agents were prepared, not yet dispatched at candidate freeze. No GPU lease is active.

Designs and contracts are coordinator-authored and need non-author review. Routine implementation choices remain with assigned authors; substantive findings receive one combined response/evidence reconciliation. Source freezes precede decisive execution; author and reviewer evidence/publications remain separate. The next receipt records actual dispatch/session identities and remote publication. No new user approval is needed for the already authorized bounded work; later improvements/customer use/deployment remain excluded.

## Objective and review map

[F2 design](../../../design/F2-local-extraction.md) specifies the customer outcome: extract a submitted admitted maintenance PDF and reopen its saved unreviewed result. F2-01..07 require actual unchanged-model execution, durable requests/attempts, bounded provenance-validated output, honest failure/interruption, stale-worker fencing, replay-safe result publication, PostgreSQL/API restart, browser usability and independent checks.

The production Python worker stays separate from research/qualification/evaluation code. Existing pinned model/venv reuse is read-only; application and model writable state is owned per worktree/run. Product implementation starts after exact independent /002 design acceptance; GPU acceptance requires a later exclusive release. First inputs are admitted synthetic 1-3-page PDFs, including a real raster-only dev fixture. No quality threshold or optimization success blocks correct persistence/recovery behavior. Field correction and approval remain F3.
