# WP-0016 · The 60-page OCR control failed on two inspection IDs

**Disposition. Keep ordinary Baidu as the reviewable reference.** On the 60-page Packet A, the existing Carbon BF16 engine finished 99 and 180 seconds sooner in the two run orders. Both times it silently changed two inspection identifiers that ordinary Baidu read correctly. The agreed limit was zero. G0 therefore ends this candidate's trial. The four-page Packet H passed every quality comparison. [Frozen gate decision](../../../coordination/WP-0016/decision.json) · [Independent review](../../eld-rd-reviewer/WP-0016/003_2026-11-18_review_eld-rd-reviewer.md)

| Publication field | Record |
| --- | --- |
| Author and publisher | eld-coordinator, continuous local Codex CLI, verification 004, 18 November 2026 UTC |
| Repository and branch | jackgumpe/eledgercare, coordination/bootstrap |
| Base and frozen decision | `774c71fc9aa9f60e751be0fe8cc364ccff5343bc` · `9510d089c074288f9ba5a4bc6e18d7e48e899034` |
| Tested source | `c7b2ee3663317e42a0e9bdd7ff9e17f16747d2cf` on engine `61bec47689dcdf272a525185013f2dce6335fa24` |
| Related publications | [Astra design 001](../../eld-rd-astra/WP-0016/001_2026-11-18_design_eld-rd-astra.md) · [Carbon engine 002](../../eld-rd-carbon/WP-0016/002_2026-11-18_research_eld-rd-carbon.md) · [Opus review 003](../../eld-rd-reviewer/WP-0016/003_2026-11-18_review_eld-rd-reviewer.md) |

## Two repeatable identifier substitutions

| Source | Ordinary Baidu and printed value | Carbon BF16 | Effect |
| --- | --- | --- | --- |
| A, page 21, line 2 | `I08O1-388` | `108O1-388` | Initial capital I became the digit 1 |
| A, page 37, line 2 | `8OI10-774` | `80I10-774` | Capital O became zero |

Both parsers found both regressions in both orders. On page 17, Carbon recovered the omitted discharge value 45.10. On page 48 an identifier both engines already read incorrectly changed again. Neither event offsets the two new silent errors. Both occur in prose after a valid block header, outside the coordinate syntax targeted by G1. The token traces show where selections diverge. The runs did not isolate a kernel, accumulation order or top-two logit margin as their cause. [Author token-trace analysis](../../eld-rd-carbon/WP-0016/002_2026-11-18_research_eld-rd-carbon.md) · [Unmodified independent score](../../../coordination/WP-0016/escrow-stage2.json)

## What the GPU measured

| Document and order | Ordinary Baidu | Carbon BF16 | Time saved | Speedup |
| --- | ---: | ---: | ---: | ---: |
| H, 4 pages, native first | 59.60 s | 49.90 s | 9.69 s | 1.194× |
| H, 4 pages, Carbon first | 61.24 s | 52.70 s | 8.54 s | 1.162× |
| A, 60 pages, native first | 1,032.06 s | 933.20 s | 98.86 s | 1.106× |
| A, 60 pages, Carbon first | 1,100.78 s | 921.14 s | 179.64 s | 1.195× |

These are complete-document times after warm-up on the 16 GB RTX 5070 Ti. The ordinary native control used its recorded dense fallback path, so these speedups apply to that configuration. The A repeat spans were 68.72 seconds for native and 12.06 seconds for Carbon. Both observed savings exceeded both spans. With one observation per mode per order, they do not establish a latency percentile. Both modes emitted identical predictions across their own repeats. On A, 35 of 60 pages had identical text outside boxes across engines. On H, all four did, with coordinate differences of at most one unit. [Warm-ups, process returns and sampled memory](../../../coordination/WP-0016/g0-return.json) · [Per-window timing and parity](../../../reviews/WP-0016/evidence/G0-stage1.json)

The reviewer completed 88 measured three-page-or-shorter windows and 12 excluded single-window warm-ups across both orders. It verified 256 measured source-page observations across the four H and four A extractions. The outer GPU lease lasted 4,475.05 seconds. The order-level guard sampled peaks of 9,691 and 9,782 MiB against the 10,000 MiB ceiling. The internal process sampler has its own cadence. Carbon's allocator peaked at 6,893.12 MiB allocated and 7,106 MiB reserved. Both Carbon orders recorded 3,509 grouped prefill layer calls, zero reported prefill fallback calls and zero static-cache reallocations within windows. G0 builds a fresh cache for each window. The lease returned, the operating-system lock could be reacquired, and the reviewer found no surviving inference processes. No human intervention was observed during the runs. Human review/correction time was unmeasured. [Lease and process verification](../../../reviews/WP-0016/evidence/G0-prekey-receipt.json)

## Quality under the two frozen parsers

| Packet and parser | Character edits, native → Carbon | Correct reference cells, native → Carbon | Extra cells, native → Carbon | Unflagged critical errors, native → Carbon |
| --- | ---: | ---: | ---: | ---: |
| H, frozen | 178 → 178 of 570 characters | 18 → 18 of 20 | 0 → 0 | 2 → 2 of 19 |
| H, title correction | 2 → 2 of 570 | 18 → 18 of 20 | 0 → 0 | 2 → 2 of 19 |
| A, frozen | 2,492 → 2,522 of 8,821 | 288 → 288 of 300 | 37 → 36 | 38 → 39 of 252 |
| A, title correction | 1,303 → 1,289 of 8,821 | 288 → 288 of 300 | 37 → 36 | 37 → 38 of 252 |

The frozen character error rate rose by 0.340 percentage points on A. The title-corrected rate fell by 0.159 points. The cell score counts extra output cells in its denominator, so one fewer extra improved it by 0.254 points with the same 288 correctly placed cells. Both aggregate metrics passed their budgets. On A, both modes emitted 30 malformed headers on 26 pages and produced valid parsed tables on two table-free pages. H had zero malformed headers. A header grammar would address a separate, demonstrated error class. [Numeric adjudication and affected pages](../../../coordination/WP-0016/g0-quality-return.json)

## Windows comparisons

The archived Windows predictions cost 15.6546455 seconds on A and 1.0232249 seconds on H. The following comparisons use the same 252 critical source positions on A. A repair means Windows was wrong and the neural engine was right. A regression reverses that transition. Both historical Windows timing references and the H results are in the linked record. No additional GPU run was needed. [Four-way counts and both timing sensitivities](../../../coordination/WP-0016/g0-quality-return.json)

| A engine and parser | Both right | Repairs | Regressions | Both wrong | Net repairs per extra second, native-first / Carbon-first |
| --- | ---: | ---: | ---: | ---: | ---: |
| Native, frozen | 155 | 59 | 3 | 35 | 0.05510 / 0.05161 |
| Carbon, frozen | 156 | 57 | 2 | 37 | 0.05994 / 0.06074 |
| Native, title correction | 155 | 60 | 3 | 34 | 0.05608 / 0.05253 |
| Carbon, title correction | 156 | 58 | 2 | 36 | 0.06103 / 0.06185 |

## Design, independence and release boundary

Astra's CPU proof covered 129,280 output columns, including 449 unnamed columns. The proposed eleven logical grammar phases expand to 367 reachable states and 341 token-transition classes once digit counts, composite tokens and UTF-8 are represented. Its compressed lookup, completion distances and four lane states occupy 509,604 bytes before GPU scratch. B=4 at the supported maximum was estimated to require 6,420.19 MiB for KV, router keys and summaries before weights and CUDA graph allocations. I reproduced the CPU proof and protocol outputs. G1 device grammar, G2 graph capture and B=4 throughput received no GPU release. The 2.50× target remains untested. [Grammar and invariants](../../../research/WP-0016/design/grammar.md) · [Batch contract](../../../research/WP-0016/design/batch-and-gates.md)

The original independent Opus 5.5 session, dispatched at xhigh, operated the exclusive lease, froze all predictions before key release and ran the scorer in separate OS processes. It exhausted its five-hour allowance and overage credits after producing the complete machine verdict. The coordinator published that output byte for byte. A separate Opus 5.5 session handled the publication review at High, the highest setting offered by that CLI route. Its 515 CPU checks independently reproduced the gate decision from the retained evidence, with zero check failures. The verified GPU and primary scoring records both belong to the original reviewer. Astra and Carbon were joint design and implementation partners. Neither adjudicated its own work. Carbon inspected the two retained native and Carbon token traces after the scored result was frozen. The outer lease and inner order labels were verified against their individual receipts. [Reviewer record](../../eld-rd-reviewer/WP-0016/003_2026-11-18_review_eld-rd-reviewer.md) · [Escrow output](../../../coordination/WP-0016/escrow-stage2.json) · [Publication cross-check](../../../reviews/WP-0016/evidence/G0-publication-crosscheck.json)

The UTF-8 receipt in the brief points to the same runner bytes as the source fix. The scorer shorthand in the brief had a suffix typo. We used the canonical scorer bytes throughout. The published title CLI takes hardcoded development inputs, so the independent auditor applied its pinned public rule to H and A. I also reran the original CLI on its development inputs, imported its original projection against H and A and ran the frozen scorer in separate processes. All eight full title score files matched the independent scores byte for byte. [Source identities](../../../coordination/WP-0016/assignment.md) · [Title verification](../../../coordination/WP-0016/g0-quality-return.json)

This decision applies to previously exposed synthetic H and A. Packet B stays sealed and Windows geometry never clipped, suppressed or overwrote any Baidu input or output. The shipping application receives no architecture change from this trial. A future bounded experiment could compare one Carbon engine change at a time against ordinary Baidu and trace the first identifier-token divergence on separate development material. Any claim that disagreement flags help should count caught errors, missed errors and human review burden. FP8, speculative decoding and selective Windows routing remain unreleased. [Trial contract](../../../coordination/WP-0016/assignment.md)
