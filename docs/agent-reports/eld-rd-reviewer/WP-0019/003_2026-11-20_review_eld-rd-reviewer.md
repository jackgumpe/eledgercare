# WP-0019 / 003: Independent review of the same-pixel fixed-crop trial

- Report path: `docs/agent-reports/eld-rd-reviewer/WP-0019/003_2026-11-20_review_eld-rd-reviewer.md`
- Sequence reservation: [INDEX.md WP-0019 / 003 at `fc15d1bd`](https://github.com/jackgumpe/eledgercare/blob/fc15d1bd3af1b4c7dfbfbf1eac2680b9ae9ac1af/INDEX.md#wp-0019-windows-ocr-fixed-crop-trial)
- Category: review
- Author / agent ID: eld-rd-reviewer. I am a fresh non-author and wrote none of the WP-0019 policy, worker, runner, coordinator tools or fixtures.
- Actual model / effort: Claude Opus 5.5 (`claude-opus-5-5`) in a native local subscription Claude Code session. xhigh effort was requested; the applied effort is not exposed.
- Execution environment:
  - CLI (Claude Code) on Windows 11 Home 26H2, build 10.0.26300.9974, AMD Ryzen 5 3600, Balanced power plan
  - read-only WP-0005 Python 3.12.10 (numpy 2.2.6, Pillow 13.0.0, pypdfium2 5.15.2 / PDFium 159.0.8149.0), Git 2.55.0
  - local `Windows.Media.Ocr` en-US on CPU only; no GPU
- Published by: the author, by normal push of the owned branch
- Timestamp: 2026-11-20T20:13:12Z
- Repository / branch: private `jackgumpe/eledgercare` · `review/wp-0019-fixed-crop` · worktree `eledgercare-worktrees/crop19-review` · scratch `wp0019-data/review`
- Base revision: `fc15d1bd3af1b4c7dfbfbf1eac2680b9ae9ac1af`
- Deliverable revision: `a78798e6c1a5ce8d43a9fd08d2561651fa7d9b52`, the final independent evidence. The intermediate freezes are listed under Change inventory.
- Previous report: none by this reviewer in WP-0019
- Related or reviewed reports and records:
  - WP-0019 / 001 eld-rd-astra, publication `c4686e0b90a4acf3e1170730d7995e94826ceff0`. Its policy is `d62a96f8145345ce4c43544850d20fce13659879` and its post-score accounting `3ba937fa8177a05d8d62c7b42a04bd0fa0def47a`.
  - WP-0019 / 002 eld-rd-carbon, publication `bcd88c82382d2e7eef42bf2eac2ddbf28259fbbc`. Its worker is `793fbb7a2a5a3a9354bb753c39b29fcdda959160`.
  - Combined candidate `9418bccd339dea1d89445f2fec93927168c7a5f0`.
  - Coordinator records:
    - current control `8220701429c3f754e27fdfd436915e6f9f8c696c`
    - gate `dd81aa35ea60238a8a68e44e3ead0203f0bfa045`
    - Stage 1 plan `49e106e16a6e848cd0e5ee0a6ab3c87606c0a50c`
    - Stage 1 gate `a1aba59e7d3a645e1ddf44e599d0704aa7fe5ec1`
    - fresh method `19b98baa253de3139e1f65807b26723294480359`
    - raster commitment `9610737251545cbf2577c4c5035cf36365f9bc29`
    - key commitment `962bfefd5eb6f84a0be34970b8547a7668897bd9`
    - Stage 2 plan `b141fbb36da39bf82c5c4f6c059f3b060f038a31`
    - blind archive `810cf72aa2af3c4bc5fff4711e892ca44e2cecca`
    - key release `0d34800ded1c5284257a7f3a2c2f72411c64188b`
    - coordinator fresh scoring `1f9fbd59651c0fd57262e75b084e8ec23eba255c`
- Status: accepted as independent review. The evidence and computations were reproduced. **The Stage 1 rule is met, and the Stage 2 larger-research criterion fails.** The coordinator's disposition is pending.
- Next owner: eld-coordinator

## Summary

**Stage 1 (exposed H and A): the registered rule is met.** I ran the bound command myself: four warm runs, each exit 0 at the first attempt. In every run, both orders give the same result:
- **H:** 0 wrong→right, 0 right→wrong.
- **A:** 1 wrong→right, 0 right→wrong.
- **Pooled net critical recovery:** +1.

The one recovery is **A page 50, table 1, row 2, column 2**. The full-page read was `80808479`; the crop's literal word `80808-479` was accepted by the delimiter rule. My predictions are byte-identical to the primary runs, and the reproducibility rule passes across all four runs (primary and replay, AB and BA).

**Stage 2 (12 fresh pages, operated blind by me): the larger-research criterion FAILS.**
- **Recoveries:** 0 fresh critical recoveries in both families and both orders. LIFT and VALVE are each 0 WR / 0 RW / 9 WW / 21 RR over 30 criticals.
- **The other components pass:**
  - zero newly wrong
  - all 18 correct blanks preserved
  - no legitimately spaced identifier damaged
  - treatment speed 149.09 pages/min under the primary rule (AB 149.93, BA 148.26), against the 30 pages/min threshold

All nine fresh errors in each family are on confusable identifiers. The crop either repeated the same wrong reading or produced a different wrong one, which was kept with a flag.

**Mechanical frozen verdicts and their weight.** My frozen combinator reports `INCONCLUSIVE_CONTROL` for both stages.
- **Stage 1:** the only cause is the preregistered static check K1. It fails strictly because the public WP-0018 witness strings appear in Carbon's test-only `test_worker.py`.
- **Stage 2:** the causes are K1 and the absence of an audited fresh run.

I judge K1 not material; my reasoning is under Decisions. Neither shortfall concerns how predictions were produced, and neither can create or hide a recovery.

**Independent and coordinator computations agree exactly on every count.**
- **Stage 2:** the coordinator's fresh scoring (`1f9fbd5`, committed after my published scores) is byte-identical in all eight frozen-scorer outputs. Its 684 field records show zero differences, and every stratum matches.
- **Stage 1:** its gate equals my transitions. The author's ledger matches mine at every one of the 624 positions in each run, except a non-critical prose-line flag that my frozen join does not compute.

**Custody.**
- The fresh keys, generator and seed equal the commitments.
- Re-running the released generator with the released seed regenerates the key commitment, fixture counts, both TIFFs and all 12 RGB pages exactly.
- No fresh label was exposed to me before my predictions were pushed.

This is independent review, not author verification.

## Objective and acceptance criteria

The authorized scope is the assignment (`docs/coordination/WP-0019/assignment.md`, frozen in my preregistration at `c0db9e43`). It asks whether a second recognition of the same admitted pixels can recover a critical value without harming a correct one, under these fixed conditions:
- WinRT engine and en-US language
- 300-DPI source pixels
- WP-0015 layout and scorer
- an excluded warm-up, a persistent worker, and AB/BA order balancing

Preregistered rules (`PREREGISTRATION.md` §7 and §9):
- **Stage 1** requires pooled H+A net critical WR−RW ≥ 1 and RW = 0 per family, in every run, with reproducible per-position outputs and all controls passing.
- **Stage 2 recommends a larger research trial only if** all of the following hold:
  - pooled fresh WR ≥ 1
  - RW = 0 per family
  - zero lost blanks
  - treatment ≥ 30 pages/min
  - controls and custody intact

  The coordinator's primary speed rule is combined treatment pages divided by the sum of treatment durations. Mine is that rate measured in each order.

## Change inventory

Every path is under `docs/reviews/WP-0019/` unless stated otherwise. All were added in `fc15d1bd..a78798e6`. No other path changed, and I touched no candidate, author, coordinator or product file.

| Revision | Paths | Purpose |
|---|---|---|
| `c0db9e43` (freeze) | `PREREGISTRATION.md`, `review_common.py`, `review_score.py`, `review_checks.py`, `review_audit.py`, `review_selftest.py`, `expected-bgra.json` | Frozen preregistration, field joins, control checks, audit hook, self-tests and the independent BGRA expectation for all 64 H/A pages |
| `78a359e3` | `evidence/freeze-c0db9e4/{README.md, selftest.json, env.json, env-frozen-code.json}` | Self-test 19/19 at the frozen tree; environment snapshots |
| `99404fe1` | `adapt_wp0019.py`, `review_supplement.py`, Addendum 1, `evidence/stage1-replay/{return.json, *.bound.json, stage1-freeze-receipt.json}` | Rename-only adapter, supplementary checks, and the hash receipt for 284 replay files, frozen **before scoring** |
| `fe2c439f` | `review_checks.py` (one-token audit fix), Addendum 2, `evidence/stage1-replay/STAGE1-RETURN.json`, `evidence/stage1-replay/checks/*` | Independent Stage 1 observations, published before any primary result was read |
| `3f48b04f` | `evidence/stage2-blind/*` | Blind Stage 2 receipt (`aeac58d0`), pushed **before key release** |
| `bb1c5e52` | `review_stage2_summary.py`, Addendum 3, `evidence/stage2-score/*` | Fresh scores, stratum joins and key custody, published before any coordinator fresh total was read |
| `a78798e6` | Addendum 4, `evidence/reconciliation/*` | Primary, author ledger, coordinator gate, coordinator fresh scoring and fixture-regeneration comparisons |

This report is committed separately after `a78798e6`. External effects:
- scratch writes only under `wp0019-data/review`
- WinRT used under the shared `winrt.lock` for four timed Stage 1 runs, two audited untimed Stage 1 runs and four timed Stage 2 runs, with no OCR after key release
- no other owner's process or resource was touched

## Decisions and rationale

1. **Stage 1 rule: met.** The quality rule holds in four of four runs and is reproducible. The only frozen control failure is K1.

   **K1 is not material:**
   - **Where the tokens are.** The three strings (`1L8O1-493`, `0I8O1-139`, `88L1L-631`) occur only in `carbon/test_worker.py` lines 131 and 144–145. There they are drawn into synthetic test images; /002 also says so.
   - **Not executed.** `run.py` hashes that file but never imports or runs it.
   - **Runtime path is clean.** `run.py`, `policy.py`, `visual.py`, `formats.py`, `engine.py`, `worker.ps1` and `execute.py` contain no reference token.
   - **Selection is generic.** My independent selector, rebuilt from the declared generic protocol, reproduced every region, rectangle, eligibility, reason and selection exactly. No witness or answer participates in selection.

   The coordinator also reported this test-source finding (`791cf82`). I concur with its `GO_STAGE_2`.
2. **Stage 2 larger-research criterion: FAIL.** No fresh critical was recovered in either family or order. Because the quality component fails, the result is a fail, not inconclusive. The control shortfalls (K1, no audited fresh run) concern isolation from labels and could only weaken a positive result. I concur with the coordinator's `FRESH_PROMOTION_CRITERIA_NOT_MET`. **No larger research trial of this fixed-crop policy is supported, and no product change follows.**
3. **Use of crops vs merge.** The rubric distinguishes three readings:
   - the diagnostic crop-alone reading, computed independently by the frozen scorer from a single crop's words
   - the merged end-to-end treatment prediction
   - the author's recorded decision

   Crop-alone would have harmed correct criticals: 6 in A, 1 in LIFT (`MCU46-461` became `MCU46—4`) and 1 in VALVE (`UJ 5197` became `I-JJ 5197`). The strict merge kept the full read in each case and flagged it. End-to-end, nothing became newly wrong.
4. **Instrumentation boundary.** Timing uses the candidate's measured arm clock. It runs from the ready-input page loop through the durable prediction write, and includes pixel checks, recognition, selection, crops, merge, layout and evidence writes. Worker startup and the excluded warm-up are reported separately. The frozen T-checks needed absolute clocks that the candidate does not record. They were replaced by supplementary checks (Addendum 1):
   - P1: order
   - P2: warm-up identity
   - P3: one worker PID and en-US on every response
   - P5: bound digests
   - P6: no crop in arm A
   - P8: run seriality

## Verification

### Custody and inputs (executed)

| Check | Result |
|---|---|
| Plan bytes | Stage 1 `ef3b9463…` and Stage 2 `5de1997b…` match on disk and in Git; manifest paths are absolute and confined to `wp0019-data/inputs`. |
| H/A admission (`review_checks.py inputs --expected`) | **139/139.** My PDFium render equals the WP-0015 raster pins. My own BMP parser (no Pillow) gives opaque BGRA equal to the manifest and to my preregistered `expected-bgra.json` on all 64 pages. |
| Fresh inputs (pre-run and `inputs-fresh` 16/16) | Manifests equal the plan, the commitment and the committed gzip copies. The BMP file, BGRA and RGB digests equal the commitment and my decode of the committed TIFF frames. |
| Released keys | LIFT/VALVE truth and strata equal `962bfefd`. Generator `b1323f04` equals the commitment and `fresh-method` `19b98baa`. SHA-256 of the decoded seed bytes equals `seed_sha256`. |
| Fixture regeneration | Re-running the released generator with the released seed in my scratch reproduces the key commitment and fixture counts **byte for byte**, both TIFFs and all 12 RGB pages. Only the manifests differ, because they embed absolute BMP paths. |
| Timeline (UTC) | Key commitment 19:44:15 → my blind runs 19:59:19–19:59:42 → my receipt commit 20:00:43 → coordinator escrow 20:01:18–19, which records my exact hashes → key release 20:04:13 → my scores `bb1c5e52` 20:07:49 → coordinator scores `1f9fbd5` 20:09:15 |
| Untouched captures | All 79 Stage 2 files re-hash equal to my frozen receipt. |

### Runtime, identity, geometry and source (executed)

| Check | Result |
|---|---|
| Environment | OCR DLL `0db8e48e…` and en-US model `81771d77…` equal the WP-0015 pins on build 26300.9974. E5 passes in both stages. |
| Full-pass identity (four runs, 64 pages, both arms) | **968/968.** The current full pass equals the WP-0015 archive raw words/boxes on 64/64 pages, the grids equal the archive `rule_tables`, and it equals the pinned current control `8220701` (4/4). This holds even though Carbon's worker replaced the original `recognize.ps1` for recognition. |
| Crop bytes and geometry | **1,345 PASS (Stage 1) and 301 (Stage 2).** Every crop is an in-page integer half-open rectangle. My own slice of the admitted BGRA hashes to the worker's source-rectangle and crop digests, and each crop is attached to its page's own full pass. G4 is not applicable (page-pixel projections). G6 deviates only by the isotropic-padding limit, exactly 4 px vertical on prose. |
| Independent rebuild (`review_supplement.py rebuild --rule-tables`) | **1,480 (Stage 1) and 332 (Stage 2) PASS.** All of these are re-derived exactly: regions, the 4 px inset, 12×8 padding and cap 32; eligibility and reasons; every crop decision and page-pixel projection; and **every durable page prediction in both arms**, using the hash-pinned original layout. `rule_tables` re-run on the bitmaps equals the recorded grids. No eligible region was omitted by overlap or the cap in any run. |
| Worker and policy source | Inspected `engine.py`, `worker.ps1`, `policy.py`, `run.py`, `execute.py` and `PROTOCOL.md`. Decode is 1x `BitmapDecoder` Bgra8/Ignore. Crops are sliced in memory from the retained bytes and byte-verified before recognition with the same `RecognizeAsync`. There is no resize, pixel edit or ID repair. The merge emits only literal crop words. |
| Audit (Stage 1, separate untimed runs) | **14/14.** No denied path opened, no network, only `powershell.exe` launched, no image written, no truth- or key-named file opened. Predictions are byte-identical to the timed runs. |
| Static K1 | **FAIL (frozen)**, as described under Decisions 1. |

### Stage 1 field results (H 4 pages / A 60 pages; identical in AB, BA and primary)

| | H | A |
|---|---:|---:|
| Criticals (lines + cells) | 19 (8 + 11) | 252 (108 + 144) |
| Selected / unselected criticals | 19 / 0 | 252 / 0 |
| WR / RW / WW / RR | 0 / 0 / 8 / 11 | **1** / 0 / 93 / 158 |
| WW with changed output | 1 (W1, accepted delimiter, still wrong) | 10 (9 flag-only; 1 accepted delimiter at p45 t1 r3 c2, still wrong) |
| Newly unflagged / unflagged wrong before→after | 0 / 8→8 | 0 / 94→84 |
| Critical flags 0→1 | 0 | 15 (9 wrong, 6 right) |
| Candidate regions / eligible / selected / differing crop reads | 36 / 20 / 20 / 1 | 588 / 460 / 460 / 27 |
| Crop decisions | 19 agree, 1 delimiter | 433 agree, 2 delimiter, 20 no-supported (flagged), 5 empty crop read (flagged) |
| Blanks preserved / lost (selected) | 1/1 / 0 (0 of 1 selected) | 22/22 / 0 (16 of 22 selected) |
| Spaced non-critical cells changed | 0 of 6 | 0 of 12 |
| Cells / prose lines correct | 15→15 /20 · 13→13 /16 | 235→236 /300 · 237→237 /288 |

Critical hybrid matrix for A (coverage, full vs crop, full R/W, crop-alone R/W, decision, transition):
- 152 agree R/R kept → RR
- 83 agree W/W kept → WW
- 6 disagree, full R, crop W, kept and flagged → RR
- **1 disagree, full W, crop R, took crop → WR**
- 9 disagree, full W, crop W, kept and flagged → WW
- 1 disagree, full W, crop W, took crop → WW

For H: 11 agree RR, 7 agree WW, and 1 W/W taken → WW (W1).

**Located cases** (per-run individual evidence in `evidence/stage1-replay/checks/*individual-evidence.json`). All were selected.

| Case | Full | Crop | Final |
|---|---|---|---|
| W1 H p2 t1 r2 c1 | `IL801493` | `IL801-493` | accepted delimiter, still wrong (`1L8O1-493`) |
| W2 A p60 t1 r2 c2 | `01801-139` | `01801-139` | unchanged, wrong |
| W3 H p1 line 2 | `Docket 88L1 L-631` | same split | unchanged, wrong |
| W4 H p2 line 2 | `Docket 880LO-977` | same | correct control |
| Z1 A p5 r5c1 | empty | no words | empty |
| Z2 A p15 r4c2 (critical) | empty | no words | empty |
| Z3 A p20 r5c1 | empty | `20—4` (U+2014) | empty and flagged |
| Z4 A p30 r3c2 (critical) | empty | no words | empty |
| Z5 A p30 r5c1 | empty | `30—4` (U+2014) | empty and flagged |
| **A50** p50 t1 r2 c2 | `80808479` | `80808-479` | **correct; the only recovery** |

The five empty crop reads in A are on A p5 column 1 (rows 2–4) and A p10 and p15 row 5 column 1. They are non-critical; each kept the full value and was flagged.

### Stage 2 field results (fresh, 6 pages per family; identical AB/BA)

| | LIFT | VALVE |
|---|---:|---:|
| Criticals (lines + cells) | 30 (12 + 18) | 30 (12 + 18) |
| Selected / unselected criticals | 30 / 0 | 30 / 0 |
| WR / RW / WW / RR | **0** / 0 / 9 / 21 | **0** / 0 / 9 / 21 |
| Confusable IDs | 9 WW (5 flagged after a differing crop) | 9 WW (crop read the same wrong string) |
| Ordinary IDs | 9 RR (1 flagged) | 9 RR |
| Legitimately spaced IDs | 12 RR, no space removed | 12 RR (1 flagged; crop `I-JJ 5197`) |
| Numeric negatives | 6 RR | 12 RR |
| Text negatives | 6 RR, plus 6 WW in both arms, unselected (`Pending` read `pending`) | 12 RR |
| Blanks preserved / lost | 6/6 / 0 | 12/12 / 0 |
| Candidate regions / eligible / selected / differing | 126 / 48 / 48 / 6 | 156 / 66 / 66 / 1 |
| Decisions | 42 agree, 6 no-supported (flagged), 0 accepted | 65 agree, 1 no-supported (flagged), 0 accepted |
| Unflagged wrong criticals before→after | 9→4 | 9→9 |
| Crop-alone critical right / wrong | 20 / 10; 0 W→R, 1 R→W | 20 / 10; 0 W→R, 1 R→W |

Hybrid matrices:

| Family | agree R/R → RR | agree W/W → WW | disagree full R, crop W, kept flagged → RR | disagree full W, crop W, kept flagged → WW |
|---|---:|---:|---:|---:|
| LIFT | 20 | 4 | 1 | 5 |
| VALVE | 20 | 9 | 1 | 0 |

### Timing (measured boundary; startup and warm-up excluded and shown separately)

| Run | Startup / warm-up ms | Full-only s · pages/min | Treatment s · pages/min | Added ms/page | Crops/page |
|---|---|---|---|---:|---:|
| H-AB | 592.5 / 331.0 | 1.319 · 182.0 | 1.479 · 162.3 | 39.97 | 5.00 |
| A-BA | 561.8 / 311.2 | 18.256 · 197.2 | 21.419 · 168.1 | 52.71 | 7.67 |
| H-BA | 547.1 / 309.7 | 1.279 · 187.7 | 1.424 · 168.5 | 36.43 | 5.00 |
| A-AB | 551.8 / 314.8 | 18.922 · 190.3 | 21.109 · 170.5 | 36.45 | 7.67 |
| LIFT-AB | 578.3 / 345.4 | 2.059 · 174.8 | 2.378 · 151.4 | 53.14 | 8.00 |
| VALVE-BA | 553.5 / 348.3 | 1.970 · 182.7 | 2.469 · 145.8 | 83.15 | 11.00 |
| LIFT-BA | 557.7 / 342.5 | 2.002 · 179.8 | 2.387 · 150.8 | 64.23 | 8.00 |
| VALVE-AB | 563.1 / 348.6 | 2.001 · 179.9 | 2.424 · 148.5 | 70.56 | 11.00 |

**Stage 1 pooled (128 page-passes):**
- full-only 193.08 pages/min; treatment 169.05 pages/min
- +44.18 ms/page overall: AB 36.67, BA 51.69
- 7.5 crops/page

The coordinator's primary Stage 1 runs gave 167.63 pages/min and +43.96 ms/page. Those are separate executions, so their clocks are not expected to match.

**Stage 2:**
- **Primary rule:** 24 treatment pages over the summed treatment durations gives **149.09 pages/min**. Full-only is 179.32, and the treatment adds 67.77 ms/page.
- **By order:** AB 149.93 and BA 148.26 pages/min (+61.8 and +73.7 ms/page). My preregistered per-order minimum is 148.26.
- **Threshold:** both rules pass the 30 pages/min threshold.

The coordinator's figure is identical because it used the receipts from my blind runs. It is not an independent re-timing.

### Reconciliation (executed after my own counts were published)

- **Primary Stage 1** (`a1aba59` ZIPs): the predictions are byte-identical to my replay, and the four-run identity and score both pass.
- **Coordinator Stage 1 gate:** its transitions, gain, blanks and crop tallies (H 20 attempted, 1 different; A 460 attempted, 27 different, 25 flagged, 2 accepted) equal mine.
- **Author /001:**
  - Its tables equal mine: the disagreement split, 15 flagged A criticals, two still-wrong delimiter acceptances, 23/23 blanks, the 16 of 22 A blanks selected, and all nine located traces.
  - Its timings are from the primary runs.
  - Its ledger (`account.py`, unchanged since `3ba937fa`) agrees with my rows at all 36 H and 588 A positions in each run. The one exception is the A p54 line 5 flag: the author records a disagreement flag on that non-critical prose line, and my frozen join leaves non-critical line flags null.
- **Author /002:** its contract, byte semantics and synthetic suite match my source inspection.
- **Coordinator fresh scoring:** all 8 frozen-scorer outputs are byte-identical, the 684 field records show zero differences, all 12 stratum summaries are equal, and the decision `FRESH_PROMOTION_CRITERIA_NOT_MET` uses the same throughput.

No per-location scoring-helper bug was found, so no correction or recomputation was needed.

### Checks not run, and why

- **Audit of the bound timed runs.** `execute.py` starts children; the audit was applied to separate untimed runs instead.
- **Audit of any fresh run.** This was not done before key release, and no OCR is allowed after it.
- **Frozen T1–T8 and G4.** The candidate does not record the fields they need; they were replaced as described above.
- **Independent re-timing of the coordinator's primary runs.** Not applicable.
- **`account.py` re-execution.** I compared its published outputs instead.
- **Coordinator files inspected only partially or not at all:** `preservation.json`, `stage1-verified.json`, `stage2-verified.json`, `verify_run.py` and `pack.py`.

## Review map

- **Preregistration and addenda 1–4:** [`PREREGISTRATION.md`](https://github.com/jackgumpe/eledgercare/blob/a78798e6c1a5ce8d43a9fd08d2561651fa7d9b52/docs/reviews/WP-0019/PREREGISTRATION.md)
- **Evidence trees** at [`a78798e6`](https://github.com/jackgumpe/eledgercare/tree/a78798e6c1a5ce8d43a9fd08d2561651fa7d9b52/docs/reviews/WP-0019/evidence):
  - `stage1-replay/STAGE1-RETURN.json`
  - `stage1-replay/checks/`
  - `stage2-blind/stage2-blind-freeze-receipt.json`
  - `stage2-score/STAGE2-RESULT.json` and `stage2-score/key-custody-verification.json`
  - `reconciliation/`
- **Reviewer diff:** [`fc15d1bd...a78798e6`](https://github.com/jackgumpe/eledgercare/compare/fc15d1bd3af1b4c7dfbfbf1eac2680b9ae9ac1af...a78798e6c1a5ce8d43a9fd08d2561651fa7d9b52)
- **Candidate source:** `9418bccd:docs/research/WP-0019/{astra,carbon}` and `docs/coordination/WP-0019/execute.py`
- **Coordinator sources inspected:** `reference.py`, `control.json`, `gate.py`, `score_pair.py`, `fresh_strata.py`, `fresh-keys/forms.py`, `fresh-method.json`, `blind-escrow-return.json`, `stage1-gate.json`, `stage2-gate.json` and `fresh-field-analysis.json`

## Risks, disagreements and unfinished work

There are no substantive disagreements with either author or with the coordinator. The shortcomings and limits are:
- **K1 fails strictly as preregistered.** The failure is kept, not rewritten, and judged non-material (Decisions 1).
- **Prior exposures, disclosed in §0.** At freeze I had already opened the H/A truth (an authorized reviewer condition), and I had seen the coordinator's commit subject "Record the single exposed critical recovery…". My counts come from the frozen code and the byte-level evidence.
- **Supplementary controls replaced frozen ones that could not run** (T1–T8, G4, G6 exactness). One reviewer-code defect, a null path in the audit summarizer, was fixed by one token (Addendum 2).
- **Audit coverage is partial.** There is none for the timed runs or for Stage 2. Label isolation for those runs rests on the unchanged static source path, the Stage 1 audited runs and the DPAPI custody chain.
- **Fresh labels.** No fresh label, count or strata file was opened before my blind receipt was pushed and the keys were released.
- **Timing scope.** Timing uses the candidate's own instrumentation and an uncontrolled desktop (idle interactive shells present, Balanced power plan). Stage 2 timing is a single execution per order.
- **Generality.** The fresh check is small and synthetic: 2 families × 6 pages, and 18 baseline-wrong criticals, all confusable. The zero-recovery result shows only that this policy recovered no fresh errors on these fixtures. It is not an estimate of any rate.

## Handoff

The coordinator records the disposition:
- **Stage 1:** the rule is met and independently reproduced.
- **Stage 2:** the larger-research criterion is not met, and no product change follows.

Identifiers:
- Deliverable (independent evidence): `a78798e6c1a5ce8d43a9fd08d2561651fa7d9b52`
- Branch: `review/wp-0019-fixed-crop`
- Report: `docs/agent-reports/eld-rd-reviewer/WP-0019/003_2026-11-20_review_eld-rd-reviewer.md`; its publication SHA follows in the handoff message.

Publication receipt: `origin` was verified to contain `a78798e6` before this report was committed. Remote confirmation of the report commit follows in the handoff.
