# WP-0025 /004 — The four box changes followed the first read of each process

**Baseline variation observed on the exposed three-page window.** The first read after each fresh model load reproduced the historical stock stream. Every subsequent read in both processes reproduced the historical hooked stream. Stock alone produced both outputs, as did capture-enabled Baidu. The frozen SHHS/HSSH order makes the first-call association visible in both directions. The exact numerical cause and any additional contribution from the hooks remain unresolved. Both processes returned cleanly. WP-0025 is closed after independent review. [Coordinator decision](../../../coordination/WP-0025/decision.json) · [Independent reconstruction](../../../reviews/WP-0025/independent.json)

| Report record | Value |
| --- | --- |
| Path and category | `docs/agent-reports/eld-coordinator/WP-0025/004_2026-11-21_verification_eld-coordinator.md`, verification, packet-wide /004 |
| Author and publisher | `eld-coordinator`, continuous native Codex CLI on Windows. Served coordinator backend and effective effort unexposed. Three fresh role sessions requested xhigh. Cloud Astra co-designed the brief. Independent reviewer `eld-repeat-reviewer` authored neither the wrapper nor the analysis. |
| Repository and owned worktree | Private `jackgumpe/eledgercare`, `coordination/bootstrap`, `C:/Users/jackg/Asp.net Projects/eledgercare` |
| Base and reservation | `ceb54580d95310881da00a6b3ddef009b3e2a9f3` and `842f587e8d223360aaa6058518d999964d304278` |
| Clean GPU candidate and two-order release | `43b625bb97d403da99e888966dbf4e781e9674d1` and `88748016392246031d517efef22c4b3ef48f3057` |
| Independent raw evidence and coordinator deliverable | `60a9ffe3c610e06669daff98a88aa3da062df553` and `48445861c2b0d6675954a69c2111d5c0c8f3f61d` |
| Publication UTC | 2026-11-21T20:32:45Z |
| Status and handoff | Independent diagnostic accepted and packet closed. This is the coordinator's first report in WP-0025. |

## Eight reads on the same images

Each process loaded the same read-only native BF16 B=1 checkpoint once and read the original three images four times, starting with the first real call. S used the historical terminal-event recorder. H added the pinned decoder-input and LM-head pre-hooks. Both paths used the same 827 prompt IDs, parser and stop rules. Every call emitted 284 IDs followed by observed EOS ID 1. Each fresh stream was compared against both old streams using their complete little-endian uint32 bytes. [P1 plan](../../../coordination/WP-0025/p1-plan.json) · [P2 plan](../../../coordination/WP-0025/p2-plan.json) · [Original handoff](../../../coordination/WP-0025/chalkboard-v2.pdf)

| Process and recording order | Call 1 matched | Call 2 matched | Call 3 matched | Call 4 matched |
| --- | --- | --- | --- | --- |
| P1 · S H H S | Historical stock | Historical hooked | Historical hooked | Historical hooked |
| P2 · H S S H | Historical stock | Historical hooked | Historical hooked | Historical hooked |

**Agreement through EOS.** A 1 denotes byte-identical streams. Zero denotes a verified difference. The row/column labels give the process, within-process ordinal and recording mode.

| Run | P1J1S | P1J2H | P1J3H | P1J4S | P2J1H | P2J2S | P2J3S | P2J4H |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| P1J1S | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| P1J2H | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 |
| P1J3H | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 |
| P1J4S | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 |
| P2J1H | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| P2J2S | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 |
| P2J3S | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 |
| P2J4H | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 |

The 28 unique off-diagonal comparisons reuse eight reads. Stock versus stock matched 3/6, hooked versus hooked matched 3/6 and stock versus hooked matched 10/16. Of the 16 stock-to-hooked comparisons, three reproduced the historical four edits in the original direction, three reversed all four and ten matched exactly. All 12 discordant pairs across every mode first diverged at zero-based position 13. The subsequent three substitutions came after that shared prefix. [Analysis and all 16 historical comparisons](../../../research/WP-0025/analysis/result.json) · [Independent cross-check](../../../reviews/WP-0025/author-crosscheck.json)

| Zero-based index | Printed block on page 1 | First read, either process | Reads 2–4, either process |
| ---: | --- | ---: | ---: |
| 13 | Portfolio directory heading | 399 | 395 |
| 77 | First listed column schema | 388 | 387 |
| 100 | Second listed column schema | 388 | 387 |
| 146 | Active unit declaration | 202 | 201 |

These numbers are right edges on Baidu's native 0–999 coordinate scale. The extracted text, cells, other box coordinates and terminal record agreed. The four relevant printed source witnesses were the owner, unit, schema and ordinary table row. All four aligned uniquely on each of eight reads (32/32). The original final-window charge was outside these three pages. [Source and cell comparisons](../../../reviews/WP-0025/independent.json)

## Recorded activations

The reviewer reconstructed all 56 pooled vectors from the four H captures and matched their stored FP32 bytes. Among the six fresh H/H comparisons, the three pairs consisting of later reads had identical hidden and pooled bytes. Each also matched the retained WP-0024 H capture. For each of the other three pairs, the first-call H recording differed from a later H recording at hidden row 0 and pooled span 0. The FP32 maximum absolute difference was 0.09375 over the 13 consumed tokens before the first generated-token divergence, 0.890625 over the 280 rows with matching token IDs, absolute positions and span membership, and 0.1000976711511612 across all 14 comparable pooled spans. Four unmatched coordinate-token positions were excluded from the aligned-row maximum. Matching later token IDs can follow different earlier sequences. S recorded no hidden vectors, so stock-to-hooked hidden equality could not be observed. [Per-row and per-span results](../../../research/WP-0025/analysis/result.json)

This study identifies a first-call association on one ordered image triple across two processes. It did not measure logit margins, kernels or the cause of the numerical change. WP-0024's exact-token disposition stands. No fitting, hidden-state probe intervention or blind memory comparison was performed. The supplied PDF's original PGDA attachment matches the previously pinned four-page original byte-for-byte. [Handoff provenance](../../../coordination/WP-0025/source-receipt.json)

The independent review's erratum supplies the original publication time (2026-11-21T20:29:55Z) and the reviewed /002 publication (`95a15980f5de86bf7f13e3fcec37a46d265d60da`). It also identifies positions 827–1110 inclusive as absolute decoder positions for output rows 0–283. The reviewer verified those values in all four stored H position traces. [Verified erratum](https://github.com/jackgumpe/eledgercare/blob/b928859a332f2b2ee725f2f73611db82bb33656e/docs/agent-reports/eld-repeat-reviewer/WP-0025/005_2026-11-21_review_eld-repeat-reviewer.md)

## Resources, verification and publication

| Process | Cold model load | Guard wall time | Sampled whole-board peak | Samples |
| --- | ---: | ---: | ---: | ---: |
| P1 | 11.498 s | 172.297 s | 8,564 MiB | 83 |
| P2 | 10.918 s | 166.610 s | 8,551 MiB | 80 |

The two supervised orders used 338.907 s in total. Native inference across eight calls summed to 288.672 s. The under-lock observations identified no competing GPU workload before either process. The guard returned both jobs with exit 0 and retired at 20:25:37 UTC. The operator checked the process tree after exit. The before/after Q0 inventory matched across 30,938 entries, including hashes of all 37 checkpoint files. [Process and resource receipts](../../../reviews/WP-0025/process-return.json) · [Q0 readback](../../../coordination/WP-0025/q0-after.json)

The coordinator checked all 108 archived members and replayed the raw through-EOS bytes. Two separate CPU readbacks produced the same decision SHA-256, `cc59ece1eb6514c4753a41d664080c9b78160c14582f427be506183a6a625d31`. The archive SHA-256 is `85efa292f454eed04fe73a6d8c4280db619ca97b5a031dbb31e88b84804ff764` (2,780,891 bytes). Its contents include the eight returns, all four H captures, ordered plans, guard and cleanup evidence, and original PDF and PNG inputs. [Primary archive](../../../reviews/WP-0025/window-repeat-r1.zip) · [Member hashes](../../../reviews/WP-0025/window-repeat-r1-inventory.json)

The root CPU entry points below ran with Q0 Python 3.12.10 and fresh output filenames. The separate reviewer operated the live guard once using the release SHA-256. Its exact command and checks are in /003.

```powershell
& $py -I -B docs/coordination/WP-0025/bind.py $deviceWorktree 43b625bb97d403da99e888966dbf4e781e9674d1
& $py -I -B docs/coordination/WP-0024/q0_receipt.py $q0 docs/coordination/WP-0025/q0-after.json --compare docs/coordination/WP-0025/q0-before.json
& $py -I -B docs/coordination/WP-0025/decision.py docs/coordination/WP-0025/decision.json
```

The base-to-decision diff contains 38 files covering both root ledgers, 13 coordinator files, two runner files, six analysis files, 14 review files and the runner publication. The remaining reports and final ledger/publication metadata follow the decision. All 20 other top-level Git objects matched the base. External changes were limited to owned worktrees, private branches and packet scratch. The game, other user processes, production, sealed Packet B and the Q0 installation were outside the write scope. The unrelated working copy edit to `web/package.json` remained outside the commits. [Exact changed files](https://github.com/jackgumpe/eledgercare/compare/ceb54580d95310881da00a6b3ddef009b3e2a9f3...48445861c2b0d6675954a69c2111d5c0c8f3f61d) · [Runner /001](https://github.com/jackgumpe/eledgercare/blob/9064b7bed4beb1b900113460fd34734e42622948/docs/agent-reports/eld-repeat-runner/WP-0025/001_2026-11-21_research_eld-repeat-runner.md) · [Analysis /002](https://github.com/jackgumpe/eledgercare/blob/95a15980f5de86bf7f13e3fcec37a46d265d60da/docs/agent-reports/eld-repeat-analysis/WP-0025/002_2026-11-21_research_eld-repeat-analysis.md) · [Independent review /003](https://github.com/jackgumpe/eledgercare/blob/370963089407aea7942f60781051811ced537a27/docs/agent-reports/eld-repeat-reviewer/WP-0025/003_2026-11-21_review_eld-repeat-reviewer.md) · [Reviewer erratum /005](https://github.com/jackgumpe/eledgercare/blob/b928859a332f2b2ee725f2f73611db82bb33656e/docs/agent-reports/eld-repeat-reviewer/WP-0025/005_2026-11-21_review_eld-repeat-reviewer.md)
