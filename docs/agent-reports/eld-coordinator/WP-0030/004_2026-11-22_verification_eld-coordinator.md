# WP-0030 / 004 · Precision correction to the 30-page M1 table entry

The 30-page M1 response at the native posting is **+0.006276067346334457**, which rounds to **+0.006276067** at nine decimal places. I transcribed the last two displayed digits as 69 in the table in /003. The author trace, independent replay and machine-readable reconciliation all contain the correct value. The number remains positive and the two owners were never ranked correctly together. [Original report](https://github.com/jackgumpe/eledgercare/blob/df8c8a4e3d94592165fa371d55aa25380f1dcf38/docs/agent-reports/eld-coordinator/WP-0030/003_2026-11-22_verification_eld-coordinator.md) · [Underlying trace](https://github.com/jackgumpe/eledgercare/blob/6c9ecae26aff3b2faa47d90d2f16bcee12b8a191/docs/research/WP-0030/trace/evidence/M1-30.json)

| Report field | Record |
| --- | --- |
| Author, publisher, category and state | eld-coordinator · verification · accepted numerical correction |
| Execution and time | Receiving native Codex CLI, effective backend and effort unexposed · 2026-11-22 20:19:48 UTC |
| Repository, branch and worktree | Private jackgumpe/eledgercare · coordination/bootstrap · C:/Users/jackg/Asp.net Projects/eledgercare |
| Report path and reservation base | docs/agent-reports/eld-coordinator/WP-0030/004_2026-11-22_verification_eld-coordinator.md · `df0bbe3fa2b6a1a4a91d8dd7564ea7909d00014f` |
| Verified deliverable | `777903d87bcbf7c61efd7d99a9566ec83c0612f3` · [reconciled raw scores](https://github.com/jackgumpe/eledgercare/blob/777903d87bcbf7c61efd7d99a9566ec83c0612f3/docs/coordination/WP-0030/reconciliation.json) |
| Independent corroboration | [002 independent review](https://github.com/jackgumpe/eledgercare/blob/e792840e6358ae2fe9a31dac1360383c0514f65c/docs/agent-reports/eld-rd-reviewer/WP-0030/002_2026-11-22_review_eld-rd-reviewer.md) · [replayed score bytes](https://github.com/jackgumpe/eledgercare/blob/7d65875a1ff2d7ad8a008ea83f5484507dbd5db3/docs/reviews/WP-0030/evidence/steps.jsonl) |
| Change inventory and handoff | This one report and its reservation in INDEX.md. Coordinator will attest all four private report publications in the closure receipt. |

I read the `native_posting.delta` field for every arm and horizon and formatted each with Python's `.9f` rounding. In table order the four values are `+0.009357478`, `+0.006276067`, `+0.000498828` and `+0.000498828`. The check was a CPU read of published evidence; the native extraction and model weights were outside the correction.
