# WP-0025 / 005 Erratum to the independent eight-call review

**The first call of each fresh process matched the historical stock stream, and the six later calls matched the historical hooked stream.** Both modes varied within this window. The disposition remains baseline variation observed. This erratum corrects two publication fields and the decoder-position label in /003. [Original /003](https://github.com/jackgumpe/eledgercare/blob/370963089407aea7942f60781051811ced537a27/docs/agent-reports/eld-repeat-reviewer/WP-0025/003_2026-11-21_review_eld-repeat-reviewer.md)

1. The /003 UTC publication timestamp is **2026-11-21T20:29:55Z**, from Git publication `370963089407aea7942f60781051811ced537a27`.
2. The reviewed /002 report publication is **`95a15980f5de86bf7f13e3fcec37a46d265d60da`**, committed **2026-11-21T20:29:22Z**. Its machine result was published at `a7962d81c3e339f73e30c27eda5ea5bef51e23b3` at 20:26:53Z. [Analysis /002](https://github.com/jackgumpe/eledgercare/blob/95a15980f5de86bf7f13e3fcec37a46d265d60da/docs/agent-reports/eld-repeat-analysis/WP-0025/002_2026-11-21_research_eld-repeat-analysis.md)
3. **827–1110 inclusive are absolute decoder positions.** The 827-token prompt occupies absolute positions 0–826. The 284 consumed-output rows have indices 0–283. Consumed row `i` is at absolute position `827 + i`. EOS was selected after the 284th output token. It has no consumed hidden row. [Verified trace and numerical evidence](https://github.com/jackgumpe/eledgercare/blob/60a9ffe3c610e06669daff98a88aa3da062df553/docs/reviews/WP-0025/independent.json)

| Record | Value |
| --- | --- |
| Author, category and status | `eld-repeat-reviewer`, review, self-published, corrected metadata verified. Fresh native Codex role `/root/repeat25_review`, requested xhigh. Actual served backend and effective effort were unexposed. |
| UTC report timestamp | 2026-11-21T20:31:36Z |
| Branch and worktree | `jackgumpe/eledgercare`, `review/wp-0025-window-repeat`, `eledgercare-worktrees/replay25-review` |
| Reservation | `4f1a66f3a5f6f12e846aaec2e7b7f14e4dcc6e0c`, packet sequence 005. [Reservation](https://github.com/jackgumpe/eledgercare/blob/4f1a66f3a5f6f12e846aaec2e7b7f14e4dcc6e0c/INDEX.md#wp-0025-h0-window-repeatability) |
| Erratum base and reviewed deliverable | Original /003 publication `370963089407aea7942f60781051811ced537a27`. Reviewer evidence and exact analyst cross-check `f45254227cac696e7f11bb5478a18a12e56e6c3e`. |
| Change inventory | One report addition, `docs/agent-reports/eld-repeat-reviewer/WP-0025/005_2026-11-21_review_eld-repeat-reviewer.md`. |
| Next owner | `eld-coordinator` for /004 disposition and publication receipts. |

I checked the historical publication timestamps with `git show -s --format=%cI`, and verified the original reports' remote heads. I read the four raw H position traces from the SHA-256-verified primary ZIP and compared each position list with the integer sequence from 827 through 1110. The eight original streams, 28 current comparisons, 16 historical comparisons, 32 source-witness bindings and 56 bit-exact pool reconstructions retain their archived results. The original primary archive SHA-256 is `85efa292f454eed04fe73a6d8c4280db619ca97b5a031dbb31e88b84804ff764`. [Primary archive and inventory](https://github.com/jackgumpe/eledgercare/tree/60a9ffe3c610e06669daff98a88aa3da062df553/docs/reviews/WP-0025)

A Windows text-read default failed to decode the UTF-8 draft of /003, and the surrounding shell continued to publication. This correction was validated with explicit UTF-8 decoding and a separate staged-file check. All work on /005 used CPU readback of existing evidence.
