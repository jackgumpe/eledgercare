# eLedgerCare work and report index

Sole writer: **eld-coordinator**, session `01a1d895-c605-7ab2-b7ec-c3159c0634ba`. All numbers below are newly allocated in this repository; none are Workspace Ledger reservations.

## Bootstrap exception

WP-0001 is the coordination/authority seed. Its first deliverable commit is a root commit with **no parent and no prior base SHA**. A base SHA must not be fabricated. The seed report follows that commit and records its full SHA. All subsequent execution requires an actual full base revision.

| Packet | Sequence | Owner | Branch / worktree | Base | Exact report path | Status / next owner |
| --- | --- | --- | --- | --- | --- | --- |
| WP-0001 | 001 | eld-coordinator | coordination/bootstrap; C:\Users\jackg\Asp.net Projects\eledgercare | none: new root commit | docs/agent-reports/eld-coordinator/WP-0001/001_2026-11-14_verification_eld-coordinator.md | reserved before seed; next eld-reviewer for the combined startup review |

## Planned packets, not yet execution releases

- WP-0002: cohesive contract/model/design and Carbon review. Bind full base and report sequences before design execution.
- WP-0003: Opus scaffold/durable-intake feature and Carbon verification. Held until exact design acceptance.
- WP-0004: independent Astra/Carbon source hypotheses, corpus, one exchange/reconciliation, and uninvolved Opus review. Bind separate worktrees and initial reservations before execution.

The seed deliverable is `35f6090a9b2e16c7645b56f34b104eb3126d5c90` (root commit, no parent), published on coordination/bootstrap. Remote: https://github.com/jackgumpe/eledgercare, private confirmed through authenticated GitHub API.

## Reserved subsequent work

The authoritative reservation may be delivered from a later coordinator commit than the worker's base. A worker starting at the listed base must read the separately supplied, exact kickoff and this coordinator reservation, which supersede stale routing in that base. The worker does not copy later coordinator files into its branch or edit INDEX.md/CURRENT.md.

| Packet / sequence | Owner / requested model | Branch / worktree | Full base | Exact report path | Release / next owner |
| --- | --- | --- | --- | --- | --- |
| WP-0002 / 001 | eld-coordinator / actual model not exposed | coordination/bootstrap; main checkout | 35f6090a9b2e16c7645b56f34b104eb3126d5c90 | docs/agent-reports/eld-coordinator/WP-0002/001_2026-11-14_design_eld-coordinator.md | released for cohesive contract/model/design; next eld-reviewer |
| WP-0002 / 002 | eld-reviewer / Carbon | review/wp-0002-contract; eledgercare-worktrees/eld-reviewer | frozen design candidate to be bound before release | docs/agent-reports/eld-reviewer/WP-0002/002_2026-11-14_review_eld-reviewer.md | reserved, not started; next eld-coordinator |
| WP-0002 / 003 | eld-coordinator | coordination/bootstrap; main checkout | review publication to be bound before disposition | docs/agent-reports/eld-coordinator/WP-0002/003_2026-11-14_verification_eld-coordinator.md | reserved, gated by independent review |
| WP-0003 / 001 | eld-implementer / Opus | feature/wp-0003-durable-intake; eledgercare-worktrees/eld-implementer | frozen reviewed design candidate to be bound before release | docs/agent-reports/eld-implementer/WP-0003/001_2026-11-14_implementation_eld-implementer.md | held for WP-0002 acceptance; next eld-reviewer |
| WP-0003 / 002 | eld-reviewer / Carbon | review/wp-0003-durable-intake; later isolated product-review worktree | actual product candidate to be bound before release | docs/agent-reports/eld-reviewer/WP-0003/002_2026-11-14_review_eld-reviewer.md | reserved, not started; next eld-coordinator |
| WP-0003 / 003 | eld-coordinator | coordination/bootstrap; main checkout | reviewed product candidate to be bound before disposition | docs/agent-reports/eld-coordinator/WP-0003/003_2026-11-14_verification_eld-coordinator.md | reserved, not started |
| WP-0004 / 001 | eld-rd-astra / gpt-6-astra, high | research/wp-0004-astra; C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-rd-astra | 35f6090a9b2e16c7645b56f34b104eb3126d5c90 | docs/agent-reports/eld-rd-astra/WP-0004/001_2026-11-14_research_eld-rd-astra.md | released independent source assessment; next eld-coordinator, then one exchange after Carbon's first assessment |
| WP-0004 / 002 | eld-rd-carbon / Carbon | research/wp-0004-carbon; C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-rd-carbon | 35f6090a9b2e16c7645b56f34b104eb3126d5c90 | docs/agent-reports/eld-rd-carbon/WP-0004/002_2026-11-14_research_eld-rd-carbon.md | released independent assessment when dispatch exists; next eld-coordinator |
| WP-0004 / 003 | eld-rd-astra / gpt-6-astra, high | research/wp-0004-astra; its own worktree | initial proposals to be pinned before exchange | docs/agent-reports/eld-rd-astra/WP-0004/003_2026-11-14_research_eld-rd-astra.md | reserved for one exchange/reconciliation, not started |
| WP-0004 / 004 | eld-rd-carbon / Carbon | research/wp-0004-carbon; its own worktree | proposal/exchange revisions to be pinned before corpus work | docs/agent-reports/eld-rd-carbon/WP-0004/004_2026-11-14_research_eld-rd-carbon.md | reserved for deterministic corpus and ranked backlog, not started |
| WP-0004 / 005 | eld-rd-reviewer / uninvolved Opus | review/wp-0004-rd; eledgercare-worktrees/eld-rd-reviewer | joint backlog/corpus candidate to be bound before release | docs/agent-reports/eld-rd-reviewer/WP-0004/005_2026-11-14_review_eld-rd-reviewer.md | held for actual candidate; next eld-coordinator |
| WP-0004 / 006 | eld-coordinator | coordination/bootstrap; main checkout | joint output and independent review to be bound before disposition | docs/agent-reports/eld-coordinator/WP-0004/006_2026-11-14_verification_eld-coordinator.md | reserved, not started |

Worktree paths shown as relative names are under C:\Users\jackg\Asp.net Projects. Placeholder bases are unreleased future steps, not executable assignments. Exact initial research kickoffs are docs/kickoffs/WP-0004-eld-rd-astra.md and docs/kickoffs/WP-0004-eld-rd-carbon.md.
