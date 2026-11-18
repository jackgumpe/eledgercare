# WP-0016 / 003: Independent G0 escrow review: hard fail on Packet A, published from the original auditor's frozen evidence

- Report path: `docs/agent-reports/eld-rd-reviewer/WP-0016/003_2026-11-18_review_eld-rd-reviewer.md`
- Sequence reservation: [INDEX.md WP-0016 / 003](https://github.com/jackgumpe/eledgercare/blob/9522d7d181958eb87636a94a5e8588388cf537fb/INDEX.md#wp-0016-grammar-and-cuda-graphed-multi-window-trial) · [assignment](https://github.com/jackgumpe/eledgercare/blob/9522d7d181958eb87636a94a5e8588388cf537fb/docs/coordination/WP-0016/assignment.md)
- Category: review
- Author / agent ID: `eld-rd-reviewer`. Two sessions held this role. They are listed separately under *Roles and route*.
- Actual model / effort:
  - **Original auditor.** Native Claude Code session `266a0f58-0cb0-4fad-9999-bd642bf58a77`, Claude Opus 5.5, dispatched with `--effort xhigh`. Its own frozen records say "applied effort not exposed".
  - **Publication continuation (this text).** Antigravity CLI, catalog model ID `claude-opus-5-5-high` (Claude Opus 5.5), explicit effort `high`. The provider rejected xhigh before the session started.
- Execution environment: Windows PowerShell; system Python 3.12.10 (`-I -B`) for the CPU checks; worktree `gates-review`. No GPU, model, torch or Q0 interpreter was used.
- Published by: `eld-rd-reviewer` (publication continuation session)
- Timestamp: 2026-11-18T15:34:02Z
- Repository / branch: `jackgumpe/eledgercare` · `review/wp-0016-escrow`
- Base revision: `7b70d674457a23a9254756c958db87d68a81da23` (verified clean Stage 1)
- Deliverable revisions:
  - Publication tools: `843a7ca86e6b2ce735a23494cfa610672209877f` and `d01bd7fc04ebfc0b7711c93426107cb271149d08`.
  - Derived evidence: `edb119924f400250cd966730686eb434a7faa3d6` and `8fa91bc90736df7c062ba51ab70d681b1779f363`.
  - Frozen scoring output that was reviewed: `c9bfa545069496bc7ab863aabeb7bf3e257b3c21:docs/coordination/WP-0016/escrow-stage2.json`.
- Previous report: none by `eld-rd-reviewer` in WP-0016
- Related or reviewed reports:
  - WP-0016 / 001, `eld-rd-astra` design, at [`b7323ea`](https://github.com/jackgumpe/eledgercare/blob/b7323eaf2d901f3c4c1566f1dcee7a54391bbca3/docs/agent-reports/eld-rd-astra/WP-0016/001_2026-11-18_design_eld-rd-astra.md).
  - WP-0016 / 002, `eld-rd-carbon` research, at [`c7acd43`](https://github.com/jackgumpe/eledgercare/blob/c7acd437795f37eac2633b8635a0760ceab9df4c/docs/agent-reports/eld-rd-carbon/WP-0016/002_2026-11-18_research_eld-rd-carbon.md).
  - WP-0016 / 004 is the coordinator's.
- Status: ready-for-review (independent disposition: **G0 hard fail**)
- Next owner: `eld-coordinator`

## Summary

This is an **independent review**. I authored neither candidate, the G0 launcher, the design nor any scorer. It publishes the original auditor's evidence and adds my own CPU corroboration.

**G0 failed.** Four of the eight gate comparisons pass: Packet H passes in both process orders and under both parsers. The other four fail: Packet A fails in both orders and under both parsers. All four A failures have the same cause, two **new unflagged critical regressions** at `page/21/line/2` and `page/37/line/2`. The pre-registered rule makes one such path a hard fail, regardless of the aggregate result.

Everything else in the gate held on A:
- CER and cell budgets were met. The title-parser CER delta was −0.00159 and the cell delta was +0.00254.
- There were zero new wrong-source links and the critical paths were matched.
- Memory stayed under the ceiling.
- carbon_bf16 was faster in both orders: 1.106× AB and 1.195× BA on A, 1.194× and 1.162× on H.

My CPU cross-check ran **515 checks with 0 failures**. It rebinds the frozen 145-check output to its mirror, Stage 1, the blind inventory, the scorer and the title rule. It also recomputes every transition, four-way table, delta, budget, gate decision, timing pair and recovery rate from score.py's per-path rows. A mutation negative control produced 27 failures, so the check is not vacuous.

Per the pre-registered sequence rule, G1 and G2 stay withheld for candidate `c7b2ee3`.

The exhaustive numeric record is the immutable original output. I cite it rather than copy it: [`escrow-stage2.json` at c9bfa54](https://github.com/jackgumpe/eledgercare/blob/c9bfa545069496bc7ab863aabeb7bf3e257b3c21/docs/coordination/WP-0016/escrow-stage2.json) (81,308 bytes, SHA-256 `b5d711606b1a6e93ac26a5b69a1643c1565cf9178699c8dae04a5203e7a506bf`).

## Roles and route

| Role | Identity | What it did |
| --- | --- | --- |
| Original independent auditor (`eld-rd-reviewer`) | Native Claude Code, Opus 5.5, session `266a0f58-…`, `--effort xhigh` | Froze the tools (`df07eea`) and forecast (`f39c8c4`). Operated `g0-ab` and `g0-ba` once each from `--source c7b2ee3`. Froze the blind inventory (`6f32732`) and Stage 1 (`7b70d67`). After the key release (`1c19444`), ran the frozen `score_all.py`: 145 checks, `g0_pass=false`. Its credits ran out **after** scoring, before it could write this Markdown. |
| Publication continuation (`eld-rd-reviewer`, this text) | Antigravity CLI `claude-opus-5-5-high`, effort high (xhigh rejected by provider) | Read the existing evidence only and ran new CPU checks. No GPU, model run, re-scoring with truth, new candidate, Packet B or threshold change. Narrative judgements here are mine. I do not attribute narrative to the original session beyond its frozen records. |
| Coordinator (`eld-coordinator`) | Coordinator session | Lease, hardware return (`07cbb88`), key release, verbatim mirror (`c9bfa54`), and title cross-check with the 0186467 rule in independent scorer subprocesses (`2a5c0f0`). |
| G0 source author (`eld-rd-carbon`) | Gemini 4 Carbon High (per its 002) | `g0.py` (`c7b2ee3`), CPU telemetry (`bdb5054`), report 002 (`c7acd43`). |
| Design author (`eld-rd-astra`) | Codex `gpt-6.2-astra`, xhigh (per its 001) | Grammar, plans and gate design, report 001 (`b7323ea`). |

## Provenance and hard gate (verified by my CPU check)

| Link | Result |
| --- | --- |
| Original `stage2-g0/summary.json` and the coordinator mirror `c9bfa54:…/escrow-stage2.json` | Byte-identical. SHA-256 `b5d71160…06bf`, git blob `bc3e39ed…`. Stage 2, `checks_run=145`, `failures=[]`. |
| `stage2-g0/files.json` | All 76 listed artifacts (scores, compares, title predictions/receipts, details) match their SHA-256 values. |
| Summary pins | `stage1_sha256 = 4e1c0fd4…6e1e` matches `G0-stage1.json` at `7b70d67`. `inventory_sha256 = 366bf5eb…ac04` matches the blind inventory at `6f32732`. `score.py` = `1ceb36fe…` at `61bec47`. Title rule `rescore.py` = `86b96064…` at `0186467`. |
| Tool freeze order | `score_all.py`, `title_adapt.py`, `common.py`, `grammar.py` and `verify.py` are byte-identical to the `df07eea` freeze. Ancestry runs `df07eea` → `6f32732` (inventory) → `1c19444` (keys). |
| Predictions | Both orders report source = head = `c7b2ee3`. All 8 frozen prediction hashes in Stage 1 appear in the blind inventory. Each title receipt's source hash equals the Stage 1 frozen hash, and its corrected hash equals the title prediction file. The Windows prediction hashes (H `c86d80cf…`, A `1f075d9b…`) equal the key-release record. |
| Determinism | Within each arm, AB and BA are byte-identical: native H `f2669bfa…`, native A `cd009c42…`, carbon H `67fb1b25…`, carbon A `204af33d…`. Native differs from carbon on both families. |
| Coordinator title cross-check `2a5c0f0` | All 8 `full_score_sha256` values equal my SHA-256 of the corresponding `scores/*-title.json`. |
| Gate recomputation | My own transition code reproduces every frozen count, four-way table, `net_recovery`, new-unflagged path list and matched-path flag for all 40 comparisons. The set regress ∪ abstain ∪ persist_changed equals score.py's `compare()` list in all 40. The 8 gate decisions and overall `g0_pass=false` reproduce. |

## Clocked AB/BA results (one observation per arm and order; warm-ups excluded)

| Family | Order | native s | carbon_bf16 s | Saving s | Speedup |
| --- | --- | ---: | ---: | ---: | ---: |
| H (4 pp) | AB | 59.5956 | 49.9047 | 9.6908 | 1.1942 |
| H | BA | 61.2407 | 52.6969 | 8.5438 | 1.1621 |
| A (60 pp) | AB | 1032.0600 | 933.1995 | 98.8606 | 1.1059 |
| A | BA | 1100.7799 | 921.1412 | 179.6387 | 1.1950 |

Repeat spread |AB−BA|:
- H: native 1.645 s, carbon 2.792 s.
- A: native 68.720 s (6.4% of the native mean), carbon 12.058 s.

The smaller saving exceeds both spreads in each family. Clocks include cold first-page latency of 39.5–49.6 s, which is the end-to-end "document ready" time. [Stage 1 timing](../../../reviews/WP-0016/evidence/G0-stage1.json)

**Memory (G0 rule ≤ 10,000 MiB).**
- Launcher 5 s samples, carbon arm: device peaks 9,526 / 9,577 MiB, allocator `max_reserved` 7,106 MiB in both orders.
- Launcher samples, native arm: 9,695 / 9,765 MiB device, 7,134 MiB allocator.
- Coordinator's external sampler, whole order: 9,691 MiB (949 samples, AB) and 9,782 MiB (931 samples, BA). Exit 0 in both orders.

**Engine counters.**
- carbon_bf16: `static_cache_reallocations = 0`, `prefill_moe_fallback_layer_calls = 0`, `prefill_grouped_mm_layer_calls = 3,509`, `burst_extra_forwards = 102` per order.
- Every **native** measured window recorded `kernel_path = triton_import_failed_dense_fallback` (22/22 per order). The speed anchor is therefore the frozen native control *as it ran in this environment*.

## Two parsers: character edits, cells including extras, critical errors (AB; BA byte-identical)

Here "frozen" means the stored WP-0015 `formats.native_page` parser. "Title" means the same predictions after the public 0186467 `title<LEVELn>` rule.

| Family · arm | Parser | Edits / ref chars | CER | Cells correct / ref (+extra) | Cell acc | Lines | Unflagged critical / 252 (H 19) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H native | frozen | 178 / 570 | 0.31228 | 18 / 20 (+0) | 0.9000 | 12 / 16 | 2 |
| H carbon | frozen | 178 / 570 | 0.31228 | 18 / 20 (+0) | 0.9000 | 12 / 16 | 2 |
| H native = carbon | title | 2 / 570 | 0.00351 | 18 / 20 (+0) | 0.9000 | 16 / 16 | 2 |
| H Windows | stored | 15 / 570 | 0.02632 | 15 / 20 (+0) | 0.7500 | 13 / 16 | 8 |
| A native | frozen | 2,492 / 8,821 | 0.28251 | 288 / 300 (+37) | 0.85460 | 195 / 288 | 38 |
| A carbon | frozen | 2,522 / 8,821 | 0.28591 | 288 / 300 (+36) | 0.85714 | 193 / 288 | 39 |
| A native | title | 1,303 / 8,821 | 0.14772 | 288 / 300 (+37) | 0.85460 | 220 / 288 | 37 |
| A carbon | title | 1,289 / 8,821 | 0.14613 | 288 / 300 (+36) | 0.85714 | 217 / 288 | 38 |
| A Windows | stored | 257 / 8,821 | 0.02914 | 235 / 300 (+0) | 0.78333 | 237 / 288 | 94 |

A also had unmatched predicted tables, which are invented-table candidates and not proven: native 3, carbon 2, Windows 0. Two neural tables fell on table-free pages.

## G0 gate comparisons (native → carbon_bf16, same process order)

| Gate | ΔCER | Δcell | Budget | Critical (stable/regress/abstain/repair/same/changed) | New unflagged | Cells CC/CW/WC/WW | Pass |
| --- | ---: | ---: | :-: | --- | --- | --- | :-: |
| H frozen AB, BA | 0 | 0 | yes | 17/0/0/0/2/0 | 0 | 18/0/0/2 | **yes** |
| H title AB, BA | 0 | 0 | yes | 17/0/0/0/2/0 | 0 | 18/0/0/2 | **yes** |
| A frozen AB, BA | +0.003401 | +0.002543 | yes | 212/2/0/1/36/1 | `page/21/line/2`, `page/37/line/2` | 288/0/0/12 | **no** |
| A title AB, BA | −0.001587 | +0.002543 | yes | 213/2/0/1/35/1 | `page/21/line/2`, `page/37/line/2` | 288/0/0/12 | **no** |

New wrong-source links were 0 in all 8 comparisons. The controls show no change in either family or parser: native AB→BA and carbon AB→BA are all-CC/WW with zero deltas.

**Representative synthetic error example.** These are paths in the synthetic public-fixture packet, A title view, AB order. The BA order is identical.

| Path | Transition | Expected | native | carbon_bf16 | Stored Windows |
| --- | --- | --- | --- | --- | --- |
| `page/21/line/2` | regress (unflagged) | `I08O1-388` | `Inspection I08O1-388` ✓ | `Inspection 108O1-388` | `Inspection 10801-388` |
| `page/37/line/2` | regress (unflagged) | `8OI10-774` | `Inspection 8OI10-774` ✓ | `Inspection 80I10-774` | `Inspection 80110-774` |
| `page/48/line/2` | persist_changed | `OO011-274` | `Inspection O0011-274` | `Inspection 00011-274` | `Inspection 00011-274` |
| `page/17/line/4` | repair | `45.10` | no value (abstain) | `Discharge 45.10 kPa.` ✓ | `Discharge 45.10 kPa.` ✓ |

Each regression is a single I/1 or O/0 homoglyph change inside an identifier, and every span is emitted `flagged: false`. [Examples in evidence](../../../reviews/WP-0016/evidence/G0-publication-crosscheck.json)

## Malformed raw headers (Stage 1 grammar `rd-wp0016-native-structure-v1`; not a G0 criterion)

| Arm (each order identical) | H pages malformed | A pages malformed | A malformed headers | Reasons | `title<LEVELn>` headers (H+A) |
| --- | ---: | ---: | ---: | --- | ---: |
| native | 0 / 4 | 26 / 60 | 30 | 14 no-fork-before-next-block, 16 bad-box-syntax | 31 |
| carbon_bf16 | 0 / 4 | 26 / 60 | 30 | 12 no-fork, 18 bad-box | 32 |

Page 21 is malformed in both arms. Page 37 is valid in both, so a structural defect does not explain the page-37 regression. Token parity on A, carbon vs native:
- 13 of 60 pages are token-identical.
- 35 of 60 have identical text outside boxes.
- The first mismatch is at token 32.
- The largest coordinate delta is 697.

On H, carbon and native differ only by box coordinates of ±1.

## Windows → neural: four-way and signed recovery per extra second

Signed net recovery = repair − regress − abstain on critical paths, divided by the extra neural seconds (neural `complete_s` − Windows `complete_s`). Windows adds zero GPU cost. The primary Windows clock is 15.6546 s for A and 1.0232 s for H. The sensitivity clock is 15.9099 s and 1.0533 s.

| Family · parser · trial | Critical CC/CW/WC/WW | Net | New unflagged vs Windows | Extra s (primary) | Net / extra s (primary · sensitivity) | Cells gained / s | Edits saved / s |
| --- | --- | ---: | --- | ---: | --- | ---: | ---: |
| A frozen native-ab | 155/3/59/35 | +56 | 3 | 1016.405 | 0.05510 · 0.05511 | 0.05215 | −2.1989 |
| A frozen carbon-ab | 156/2/57/37 | +55 | 2 | 917.545 | 0.05994 · 0.05996 | 0.05776 | −2.4685 |
| A frozen native-ba | 155/3/59/35 | +56 | 3 | 1085.125 | 0.05161 · 0.05162 | 0.04884 | −2.0597 |
| A frozen carbon-ba | 156/2/57/37 | +55 | 2 | 905.487 | 0.06074 · 0.06076 | 0.05853 | −2.5014 |
| A title native-ab | 155/3/60/34 | +57 | 3 | 1016.405 | 0.05608 · 0.05609 | 0.05215 | −1.0291 |
| A title carbon-ab | 156/2/58/36 | +56 | 2 | 917.545 | 0.06103 · 0.06105 | 0.05776 | −1.1247 |
| A title native-ba | 155/3/60/34 | +57 | 3 | 1085.125 | 0.05253 · 0.05254 | 0.04884 | −0.9639 |
| A title carbon-ba | 156/2/58/36 | +56 | 2 | 905.487 | 0.06185 · 0.06186 | 0.05853 | −1.1397 |
| H either parser, native AB / BA | 11/0/6/2 | +6 | 0 | 58.572 / 60.217 | 0.10244 / 0.09964 | — | — |
| H either parser, carbon AB / BA | 11/0/6/2 | +6 | 0 | 48.882 / 51.674 | 0.12275 / 0.11611 | — | — |

On A, every Windows→neural CW is an abstention: native abstains at `page/17/line/4`, `page/24/line/2` and `page/33/line/4`; carbon at the last two.

Cells four-way on A is 235/0/53/12 for every neural trial. Neural recovers about 56 critical values and 53 cells at a cost of roughly 900–1,085 extra seconds. It also adds character edits (negative edits saved) and 36–37 extra cells.

carbon's per-second rate is higher than native's only because it is faster. Its net count is one lower.

## Inspection of upstream deliverables

- **Design 001 (`b7323ea`).** The plans, six excluded warm-ups and 44 scored windows per order match Stage 1: 3 warm-up and 22 measured windows per arm, and 100 windows in total ended with `stop`. G0 does not exercise the 367-state grammar. Both regressions are inside valid post-`<FORK>` prose (page 37 is structurally valid), so a structural grammar would not have prevented them. I agree with 001's own limit: "A legal coordinate string may still encode the wrong geometry".
- **Carbon source (`c7b2ee3`).** The diff from `61bec47` is exactly one added file, `docs/research/WP-0016/engine/g0.py` (56 lines). It redirects `PACKET`, restricts `MODES` to `native`/`carbon_bf16`, and adds itself to `SCOPES`. The inference code and child command are unchanged. Stage 1 recorded source = head = `c7b2ee3` for both orders.
- **Telemetry (`bdb5054`).** This is CPU-only and post-freeze, and the G0 run did not use it. Its warning about 5 s device sampling is noted. The coordinator's faster whole-order sampler peaked at 9,691 / 9,782 MiB. Those peaks are not separable by arm, and they did not exceed the launcher's native-arm peaks (9,695 / 9,765 MiB). All samples are under the ceiling, but a short carbon-arm spike between samples cannot be excluded.
- **Carbon 002 (`c7acd43`, present at publication).** It agrees with the gate failure and the G1/G2 hold. Its numbers match the evidence, with one clarification: the 9,691 / 9,782 MiB peaks are whole-order board peaks from the coordinator's sampler, not carbon-arm-only peaks.

  Its root-cause account is an **author hypothesis that I did not verify**. That account covers the token IDs `' I'+'08'` → `' '+'108'` and `'8'+'OI'` → `'80'+'I'`, BF16 reduction-order perturbation, and the explanation of the A speedup by fsync/prefill share. It rests on reading token streams in the reviewer's run root after scoring. I opened no run tree, and my result does not depend on 002. The scored text is consistent with the reported homoglyph flips.

  Its forward proposals are outside this packet's release: margin flagging, Windows-disagreement flagging and WP-0017. One post-hoc observation only: at both regressed paths, the stored Windows text also differs from carbon's. This is not a tested treatment.

## Frozen-forecast scoring (calibration only, not a gate)

The original auditor's forecast (`f39c8c4`, frozen before any run) says it is scored in 003. Result:
- **9 of 22** interval values fell inside their 80% intervals.
- Mean Brier score is **0.249** over 16 probability items.

Misses:
- H absolute times: observed 59.6–61.2 s and 49.9–52.7 s against forecasts of 50–57 s and 43–47.5 s.
- A native spread: 6.4% observed against a forecast of ≤3%.
- Carbon allocator reserve: 7,106 MiB observed against 8,300–9,300 MiB.
- Malformed headers: 30 per arm observed against 0–4.
- Title-header equality: 31 vs 32.
- H Windows net: +6 observed against −2 to 4.
- |ΔCER| ≤ 0.003: 0.0034 on A frozen.

Hits include A native time, A speedup, A Windows net (+56) and its per-second rate (0.052–0.055), F24, and the probabilities on determinism and the H gate. The forecasts were overconfident on absolute clocks and on structure. [Forecast score](../../../reviews/WP-0016/evidence/G0-forecast-score.json)

## Change inventory (base `7b70d67` → `8fa91bc`; report committed afterward)

| Action | Path | What and why |
| --- | --- | --- |
| Added | `docs/reviews/WP-0016/publication_check.py` (`843a7ca`, SHA-256 `b657529e…`) | Independent CPU recomputation of provenance, per-arm counts, transitions, four-way tables, deltas, budgets, gates, timing, recovery, structure and examples from the frozen stage-2 directory. Opens no truth and runs no model or scorer. |
| Added | `docs/reviews/WP-0016/evidence/G0-publication-crosscheck.json` (`edb1199`, `0b327ea8…`) | Output: 515 checks, 0 failures |
| Added | `docs/reviews/WP-0016/forecast_check.py` (`d01bd7f`, `64ba120d…`) | Scores the frozen forecast against committed evidence |
| Added | `docs/reviews/WP-0016/evidence/G0-forecast-score.json` (`8fa91bc`, `2d18dd99…`) | Forecast score |
| Added afterward | this report | Report only |

No ledger, coordinator, author, production or WP-0015 path was changed. There were no external effects other than pushes of this owned branch.

## Verification

| Check / command | Revision | Result | Evidence |
| --- | --- | --- | --- |
| `python -I -B docs/reviews/WP-0016/publication_check.py --stage2 C:/Users/jackg/eLedgerCare-Speed/WP-0016/review/escrow/stage2-g0 --out docs/reviews/WP-0016/evidence/G0-publication-crosscheck.json` | tool at `843a7ca` | exit 0; 515 checks, 0 failures; recomputed 4/8 gates pass, `g0_pass=false` | [crosscheck](../../../reviews/WP-0016/evidence/G0-publication-crosscheck.json) |
| Negative control: a scratch copy of stage2-g0 with `page/21/line/2` in `A-carbon-ab-title.json` flipped to correct, then the same tool | Pre-commit tool version, identical to `843a7ca` except that it lacked the `tool_sha256`/`head` output fields | exit 1; 27 failures (files.json, per-arm counts, coordinator hash, A title transitions/compare lists, Windows recovery); scratch deleted | not committed |
| `python -I -B docs/reviews/WP-0016/forecast_check.py --out docs/reviews/WP-0016/evidence/G0-forecast-score.json` | `d01bd7f` | exit 0; 9/22 inside, Brier 0.249 | [forecast score](../../../reviews/WP-0016/evidence/G0-forecast-score.json) |
| `git show` hash checks of `c9bfa54`, `2a5c0f0`, `1c19444`, `07cbb88`, `6f32732`, `61bec47`, `0186467`; `git diff --stat 61bec47 c7b2ee3` | — | as stated above | — |

**Checks not run, and why:**
- No truth or rasters were opened, and `score.py` and `title_adapt.py` were not re-executed. My recomputation consumes score.py's per-path rows, so the field-level correctness verdicts rest on the frozen scorer. The coordinator's separate subprocess re-score (`2a5c0f0`) independently matches all 8 title score files.
- Raw run trees were not opened, so the frozen prediction bytes were not re-hashed by me. They are bound through the Stage 1, inventory and title-receipt hashes.
- No GPU, model or Packet B work was done, by scope.

## Risks, disagreements, and unfinished work

- **No disagreement** with the original auditor's verdict, the coordinator's adjudication or Carbon 002 on the gate outcome.
- **Minor, non-blocking observations:**
  - Stage 1's top-level `bound_lease` is `null`, while the per-run lease labels are `g0-ab`/`g0-ba`. Lease custody is bound separately by the coordinator's return (`release_sha256 5595c8b7…`).
  - The native anchor ran Triton-fallback dense kernels, so the speedups are relative to that control.
  - Every speed figure is a single observation per arm and order.
- **Custody note for the coordinator:** Carbon 002 reports a post-scoring read of the reviewer run root `review/runs/g0-ab`. It happened after the frozen score (summary `created_utc 15:16:53Z`, 002 timestamp 15:23:30Z) and cannot have affected the result.

## Handoff

- Next owner: `eld-coordinator`, for G0 disposition and ledger publication in WP-0016 / 004. G1 and G2 remain withheld for `c7b2ee3`.
- Branch `review/wp-0016-escrow`. Deliverable/evidence SHA `8fa91bc90736df7c062ba51ab70d681b1779f363`, verified on origin by `git ls-remote` before this report was committed.
- Report path: `docs/agent-reports/eld-rd-reviewer/WP-0016/003_2026-11-18_review_eld-rd-reviewer.md`. The report publication SHA is supplied in the handoff message.
- No lease, GPU or background process is held.
