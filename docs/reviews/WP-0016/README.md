# WP-0016 independent escrow tooling (eld-rd-reviewer)

Working notes for reservation 003. This is **not** the canonical report. Sequence 003 is reserved for the final independent disposition: `docs/agent-reports/eld-rd-reviewer/WP-0016/003_2026-11-18_review_eld-rd-reviewer.md`.

- **Author:** eld-rd-reviewer. Fresh Claude Code session on Opus 5.5 (`claude-opus-5-5`); the requested effort was xhigh, and the applied effort is not exposed.
- **Branch and worktree:** `review/wp-0016-escrow`, `gates-review`, base `61bec47689dcdf272a525185013f2dce6335fa24`.
- **Independence:** I authored neither WP-0016 candidate. I authored no WP-0016 design, engine or scoring code. The scorer, adapter and title rule I use are frozen third-party bytes.
- **Prior role:** This role ID authored the WP-0015 replay tooling at `565d674`. It is reused here only as reading material.

## Exposure state when the tools were frozen

| Item | State |
| --- | --- |
| H/A truth | Not read. Bound by hash only: commitments `5ee817bd…` at custody `7598bf4`, re-checked against `g0-plans.json`. |
| WP-0016 predictions | None existed. The runtime root held only inputs, plans and dispatch texts. |
| Stored WP-0015 Windows outputs | Not read. Bound by hash to the committed WP-0015 inventories: H `c86d80cf…` and A `1f075d9b…`, identical bytes in both WP-0015 orders. |
| Packet B | Not resolved, read or listed by any tool. `FAMILIES = ("H", "A")`. |
| Model, torch, CUDA, devices | Not invoked. The Q0 interpreter printed only `sys.version`. |

## Pinned bytes (materialised from Git blobs by `common.materialize`, SHA-256 verified before use)

| Name | Commit:path | SHA-256 |
| --- | --- | --- |
| score.py | `61bec47:docs/evaluation/WP-0015/score.py` (also identical at 9522d7d and 565d674) | `1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7` |
| formats.py | `61bec47:docs/research/WP-0015/astra/formats.py` | `b832a7ee452f807a01a4acaa4d63fed927241f73b75fc1a47c7ae830ce28c0a6` |
| rescore.py | `0186467:docs/research/WP-0015/astra/sensitivity-title-level/rescore.py` | `86b9606468d12afff952b0b24dc7fcd1de932aa9c18400c966a3789e1609b700` |
| commitments.json | `7598bf4:docs/evaluation/WP-0015/commitments.json` | `5ee817bdd5b7b776c5098186b425b6039ab224abb0ae37a081917dc4148606db` |
| g0-plans.json | `be8c7f1:docs/coordination/WP-0016/g0-plans.json` | `53be595ad05302c43aadf76bc8e04af929532877aed2a9ee08c12f32923854fb` |
| WP-0015 inventories | `565d674:docs/reviews/WP-0015/evidence/{H-blind,A-recovery-blind,A-blind}-inventory.json` | `32274a74…`, `54c9a7cb…`, `84eee0e2…` |

The plan files on disk match the record:
- AB: `b705772d04e1cab173096bd9fb779a57f71e68af1eaccc4f7dc107a0432fffbf`, native then carbon_bf16.
- BA: `7a48e28f6ef5f736d4fed0c89a28e07800ecf827a8ad646197fc3fa9aac924a9`.
- Each arm runs 3 one-page warm-ups (excluded), then H (4 pages, 2 windows) and A (60 pages, 20 windows).

The input-only raster inventories match: H `cde8a5a9…`, A `54ac6864…`.

**Title rule.** `TITLE` and its `"\1"` template are extracted from the committed `rescore.py` by AST and compared with the expected literal. The file is never executed. The scorer and adapter run as separate OS processes with `-I -B`.

## Tools

| File | Stage | Purpose |
| --- | --- | --- |
| `common.py` | all | Pins, materialisation, AST rule extraction, separate-process `score.py` and adapter runners, the segmented-layout map (same contiguous split as the frozen Carbon launcher), pre-registered constants |
| `escrow.py` | 0, blind | Hashes every file in both run trees, with `cache/` listed separately. Records plan/source/lease/order and process outcome only, with no timings, sizes or text. Committed before anything parses a prediction. |
| `verify.py` | 1, no truth | Checks immutability against the inventory, plan/source/lease/order binding, input-only RGB pins, per-segment plan/child/load/session/started records and the frozen re-projection of every raw page. Also checks `<PAGE>` starts, token and raw reassembly, stops and page counts, coverage, clocks, and 3 warm plus 22 measured windows per arm. It records grammar per raw source/page, cache and burst counters, allocator versus device memory, cold-load/serving/segment walls, paired timing and the repeat spread in both orders, and token parity. |
| `title_adapt.py` | 2 | Separate process. Requires every raw page to re-project to its stored page, then applies the public rule. Writes the corrected prediction and a header receipt. |
| `score_all.py` | 2, after release | Truth/rasters commitments, released rasters equal the inference pins, and Windows prediction/clock binding. All scores and comparisons come from `score.py` in separate processes. Computes transitions, gates, Windows→both, recovery per extra second, invented-table and numeric-surplus diagnostics, and 5-arm critical patterns. |
| `grammar.py` | 1 | Named structural grammar `rd-wp0016-native-structure-v1` |
| `selftest.py` | CPU | Synthetic segmented run trees through every CLI stage, plus a public-dev regression against the committed sensitivity outputs |

## Pre-registered rules (frozen with the tools, before any WP-0016 output exists)

1. **Views.** "Frozen" uses the stored predictions. "Title" applies the 0186467 rule to both native and carbon_bf16. The stored Windows prediction is the same in both views.
2. **Critical transition** per matched reference path, base → trial:
   - `stable_correct`.
   - `regress`: wrong value.
   - `abstain`: no value.
   - `repair`.
   - `persist_same` / `persist_changed`: both wrong; same or different (observed, flagged).
   - The four-way table is CC / CW (`regress` + `abstain`) / WC / WW.
   - Cells and lines also get a four-way table.
   - Cross-check: the set `regress` ∪ `abstain` ∪ `persist_changed` must equal the frozen `compare()` list `new_or_changed_critical_errors`.
3. **New unflagged critical** at a path: the trial is wrong and unflagged where the base was correct or flagged. **One such path is a hard fail** for that gate comparison, even if the net count is flat or positive.
4. **G0 gate comparison** per family × order × view, native → carbon_bf16 in the same process order (8 in total). It passes only with all of:
   - a complete matched pair;
   - the frozen `inside_quality_budget` (CER Δ ≤ 0.01 and cell Δ ≥ −0.02, re-derived and required to agree);
   - zero new wrong-source links;
   - matched reference paths;
   - zero new unflagged critical.
5. **G0 memory.** On the carbon_bf16 arm in each order, the sampled device `used_mib` peak and the allocator `max_memory_reserved` peak are each ≤ 10,000 MiB. Native is reported. Device and allocator are reported separately. Device samples arrive every 5 s, so short peaks can be missed.
6. **G0 overall** also requires a clean stage 1, a clean stage 2 and a real (pinned) binding. Missing evidence fails closed. A synthetic or unpinned record is labelled "NOT A GATE RESULT".
7. **Structure.** Malformed versus valid structure is recorded per raw source/page and is **not a G0 criterion**. A syntactically valid header establishes neither a correct box nor the existence of a table. Better-formed tags never earn score credit.
8. **Windows → neural.** Uses the stored WP-0015 Windows prediction, with Windows using zero GPU.
   - **Signed net recovery** = repair − regress − abstain, divided by the extra neural seconds (neural `complete_s` minus Windows `complete_s`).
   - Cells gained and edits saved are reported per extra second too.
   - **Primary clock** is the Windows run paired with a complete native in AB order: H `h-r1-ab/04-h-windows` (1.023… s) and A `a-recovery-ab/04-a-windows` (15.6546455 s).
   - **Sensitivity clock** is the BA run: H `h-r2-ba` (1.053… s) and A `a-scale-ba` (15.91 s; that run's native failed).
9. **Comparisons computed.** Per family and view:
   - gate native→carbon in AB and BA;
   - control native AB→BA and carbon AB→BA;
   - cross native AB→carbon BA and native BA→carbon AB;
   - Windows→each of the four neural arms;
   - the frozen→title correction for each neural arm.
10. **Timing.**
    - One observation per arm and order, with no percentiles.
    - Paired saving and speedup per order.
    - The repeat spread per arm and family (A and H).
    - Whether both savings exceed the native spread and the larger of the two spreads.
    - Cold load, segment wall, in-child serving span, and their difference: an upper bound on start-to-ready, which includes teardown.
    - Warm-ups are excluded and recorded.

## Operator procedure (awaiting exact coordinator binding)

1. **GPU release.** The coordinator binds the exact G0 source commit (Carbon's `docs/research/WP-0016/engine/g0.py`), worktree, ceiling, plan hashes, lease and fresh ownership. Each order runs once as a fresh process, sequentially, with no duplicate attempt. Long runs go in the background under an outer supervisor with an output receipt. Interventions and monitoring are logged apart from measured inference.
2. **Stage 0**, immediately after both orders finish:
   `python -I -B docs/reviews/WP-0016/escrow.py --runs <ab run> <ba run> --plans <pins>/g0-plans.json --out docs/reviews/WP-0016/evidence/G0-blind-inventory.json`
   Commit and push this before any further reading.
3. **Stage 1:**
   `python -I -B docs/reviews/WP-0016/verify.py --inventory <inv> --plans <pins>/g0-plans.json --inputs C:/Users/jackg/eLedgerCare-Speed/WP-0016/review/inputs --pins <pins> --source <bound G0 SHA> --lease <bound lease> --out <new dir>`
4. **Scoring release, then stage 2:**
   `python -I -B docs/reviews/WP-0016/score_all.py --stage1 <stage1.json> --inventory <inv> --plans <pins>/g0-plans.json --pins <pins> --scoring <released dir with H/ and A/> --windows-store <dir> --out <new private dir>`

## Needed from the coordinator before stage 2

- **Stored Windows copies.** This session cannot read `C:/Users/jackg/eLedgerCare-Speed/WP-0015/review/runs` (outside its permitted paths). Copy `prediction.json` and `timing.json` from `h-r1-ab/04-h-windows`, `h-r2-ba/03-h-windows`, `a-recovery-ab/04-a-windows` and `a-scale-ba/03-a-windows` into a new `…/WP-0016/review/inputs/windows-store/<run>/<folder>/`. Read access is an alternative. The tool hash-binds whatever is supplied against the WP-0015 inventories.
- **Scoring release** of H/A `truth.json` and `rasters.json`, only after the blind inventory is committed.
- **Exact G0 source/worktree.** The frozen launcher checks that the five WP-0015 scopes are clean and equal at `--source`. It does **not** cover `docs/research/WP-0016/engine/g0.py`. Stage 1 verifies the reported source. The wrapper diff itself (61bec47 → G0) needs inspection before launch.
