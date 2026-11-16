# WP-0007 /001: Descriptive vanilla accuracy baseline contract

- Report path: `docs/agent-reports/eld-coordinator/WP-0007/001_2026-11-16_design_eld-coordinator.md`.
- Sequence reservation: WP-0007 /001 in candidate INDEX.md.
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

[B0 design](../../../design/B0-vanilla-accuracy-baseline.md) releases dev-only deterministic parser/scorer preparation, then independently accepted source/protocol freeze before fixed test access. Use all 26 admitted PDFs/40 pages with explicit dev/test summaries, raw text/provenance, failures in denominators, important fields, table cells, omissions/inventions and per-document latency/memory observations. Predictions cannot be obtained or repaired using ground truth.

One measured completion per document is a bounded descriptive census. This new baseline does not claim to execute or satisfy the E1-E3 three-repeat paired timing protocol. No treatment, tuning against test answers, LLM scoring or population-generalization claim is permitted. Native Astra authors CPU source and later released runtime evidence; the uninvolved reviewer validates the scorer, predeclares sentinels, reproduces all raw-output scoring and conducts bounded independent runtime checks. Accurate measurement is the acceptance condition even when model scores are poor.

Initial independent review covers the written B0 contract alongside F2; canonical WP-0007 /003 closes both that contract and the actual scorer/runner gate. No holdout PDF/source/expected data is available for code development. Existing Q0 raw dev outputs can exercise parsing without spending GPU time.
