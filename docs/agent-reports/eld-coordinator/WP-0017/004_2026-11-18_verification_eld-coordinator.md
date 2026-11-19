# WP-0017 · The bounded switch-removal trial ended without a qualifying engine

**Keep ordinary Baidu as the reviewable OCR reference.** Across 19 configurations on the RTX 5070 Ti, none of the six individual or three eligible paired removals restored both inspection identifiers that full Carbon had regressed on Packet A. All three pairs recovered the page 37 identifier. All three still changed the initial capital I to a digit 1 on page 21. The trial closed at A1. [Coordinator decision](../../../coordination/WP-0017/decision.json) · [Independent combined decision](../../../reviews/WP-0017/evidence/A1-combined-decision.json)

| Publication field | Record |
| --- | --- |
| Coordinator | eld-coordinator, continuous local Codex CLI, verification 004, 18 November 2026 |
| Repository | jackgumpe/eledgercare, coordination/bootstrap |
| Starting integration revision | `1e75ebe25814227ef6450913bce301ba9e2ef0f2` |
| Tested research engine | `c235bc61820def84142480e6e2a7a2e5485176d6`, frozen BF16 checkpoint `0480966938291445591f69f08a13b041c073a96a` |
| Frozen coordinator disposition | `b95e329f54ecbb389c2db65a7dbe7d825874a234` |

## What changed the readings

On page 21, ordinary Baidu emitted `I08O1-388`. Batched expert decode, fused gate and up projections, and gathered sparse attention each changed it to `108O1-388` when added individually to the otherwise native configuration. Their respective single removals from full Carbon also left that field wrong. On the shared token history, the native model favored the correct full identifier by 0.056 nats and full Carbon favored the incorrect one by 0.069 nats. Small numeric changes at this decision mattered. The data establish three sufficient additions in this context and leave a unique culprit unresolved. [Initial switch measurements](../../../coordination/WP-0017/a1-initial-findings.md)

On page 37, the historical free runs first diverged at coordinate token 7, before the identifier. Ordinary Baidu emitted coordinate 291 and ID `8OI10-774`. Full Carbon emitted 290 and `80I10-774`. Turning off gathered sparse attention alone restored the ID. All three eligible pairs restored both the earlier coordinate and the ID. On the original full Carbon path, replaying its own token history shifted the full-identifier score difference another 0.131 nats toward the wrong reading. The matched-history probes and free output support contributions from both execution and preceding tokens. [Prefix audit](../../../reviews/WP-0017/evidence/A1-prefix-audit.json) · [Pair readings and probe results](../../../reviews/WP-0017/evidence/A1-combined-decision.json)

## Measured speed and accuracy

Each time below sums two ordinary, three-page window reads after warm-up. Instrumented forced-token probes and model loading have separate clocks. Within the switchable implementation, adding batched expert decode alone saved 12.44 seconds, and removing it from full Carbon cost 13.41 seconds. That was the largest speed contribution observed. Each configuration supplied one timing per window. [All six switch effects and endpoint timings](../../../coordination/WP-0017/a1-initial-findings.md)

| Configuration | Combined time | Page 21 ID | Page 37 ID |
| --- | ---: | --- | --- |
| Ordinary Baidu | 99.33 s | Correct | Correct |
| Full Carbon BF16 | 85.00 s | Wrong | Wrong |
| Remove batched expert decode and fused projections | 104.66 s | Wrong | Correct |
| Remove batched expert decode and gathered attention | 99.04 s | Wrong | Correct |
| Remove fused projections and gathered attention | 87.93 s | Wrong | Correct |

The fastest pair retained batched expert decode and still failed the two-ID requirement. The 18-page development evaluation and the 60-page replay therefore had no eligible candidate. This experiment measured six previously exposed synthetic pages. It provided neither a new 60-page speed estimate nor evidence of faster first-upload latency in the application. The production, qualification and deployment trees match their starting Git objects. [Scope and checks](../../../coordination/WP-0017/decision.json) · [Engineering report 002](../../eld-rd-carbon/WP-0017/002_2026-11-18_research_eld-rd-carbon.md)

## Confidence in the decision

Four control paths exactly reproduced the historical token sequences, stops, page text and source links on both windows. The pair reviewer independently checked 19 configurations, 84 probe passes and the frozen ranking rules. Of 42 tied passes, the first token in the sorted top-five list differed from the model's actual greedy choice in 16. The corrected analysis used the recorded argmax. For one pair on page 37, the model chose the correct first token on a tie even though the competing full identifier had the higher summed probability. The advancement decision used the complete ID actually emitted. [Corrected reviewer evidence](../../../reviews/WP-0017/evidence/A1-combined-decision.json) · [All tied-step corrections](../../../coordination/WP-0017/a1-p1-probe-ties.json)

Opus reran a separate CPU publication check after its quota reset. All 712 checks passed and reproduced the terminal pair verdict. [Publication cross-check](../../../reviews/WP-0017/evidence/A1-003-crosscheck.json)

The coordinator compared the blind inventories, rehashed all 1,379 captured files and reread both IDs directly from the second source block for all 19 configurations. The three supervised orders took 81 minutes 42 seconds including startup, 57 warm-up windows, 38 ordinary windows and the diagnostic probes. All 19 workers exited. Peak sampled board usage was 9,394 MiB across the initial sweep and 13,053 MiB during the pairs, within the A1 diagnostic limit of 14,500 MiB. These are board-wide samples. Human active time was unmeasured. [Initial GPU receipts](../../../coordination/WP-0017/a1-r1-return.json) · [Pair GPU receipts](../../../coordination/WP-0017/a1-p1-return.json) · [Coordinator reproduction](../../../coordination/WP-0017/decide_a1.py)

Astra designed the experiment at xhigh and Carbon implemented the six switches at High. Opus audited the prefix evidence and issued the initial GPU command. When both Opus routes reached their limits, Jack authorized a separate fresh Codex xhigh reviewer for exactly the three pair tests. That reviewer validated the inputs, issued its own command and adjudicated the pair results. The coordinator's Windows carrier executed each reviewer-issued command once. The research weights stayed frozen, the development scoring key stayed in custody and Packet B stayed sealed. [Astra design 001](../../eld-rd-astra/WP-0017/001_2026-11-18_design_eld-rd-astra.md) · [Operator authorization](../../../coordination/WP-0017/pair-operator-addendum.md) · [Independent report 003](../../eld-rd-reviewer/WP-0017/003_2026-11-18_review_eld-rd-reviewer.md)
