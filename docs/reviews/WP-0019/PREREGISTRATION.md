# WP-0019 / 003 reviewer preregistration (eld-rd-reviewer)

The independent non-author reviewer wrote this file and every script in `docs/reviews/WP-0019`. They are committed on `review/wp-0019-fixed-crop` before any decisive execution, from base `fc15d1bd3af1b4c7dfbfbf1eac2680b9ae9ac1af`.

- **Session and model:** fresh local subscription Claude Opus 5.5 (`claude-opus-5-5`); xhigh effort was requested but the applied effort is not exposed. Session file `wp0019-data/review/session.private`.
- **Authorship:** the reviewer authored none of the WP-0019 selector, merge, runner or worker, and none of the WP-0015 scorer or adapter.
- **What this turn did not do:** it ran no WinRT, OCR, timed or crop operation on H or A, used no GPU or network, opened no fresh label, and touched no product or published report.

## 0. What the reviewer saw before this freeze

**Read:**
- AGENTS, START_HERE, CURRENT, the INDEX WP-0019 reservation and `docs/coordination/WP-0019/assignment.md`
- the frozen scorer `docs/evaluation/WP-0015/score.py`
- the pinned adapter at `a0e738bc`: `recognize.ps1`, `visual.py`, `formats.py`, `prepare.py` and `trial.py` (render recipe), plus `workers/local_ocr/local_ocr/protocol.py` (render constants)
- WP-0018 `decision.json`, its witness traces and its reviewer preregistration
- the admitted archive copies `wp0018-data/coordinator/inputs/{H,A}`: truth, historical score, plan, rasters, raw/page/window files and prediction. **H and A truth were opened, so this review is not label-blind on H/A.** That is the stated Stage 1 condition; Stage 2 uses fresh, sealed keys.

**Not read:** any WP-0019 author source, evidence, result or summary.
- Directory listings showed the file names in `wp0019-data/carbon` (`initial-prompt.txt`, `initial-output.private`, `initial-error.private`) and `wp0019-data/coordinator/provider.py`. None was opened.
- `wp0019-data/inputs` was empty, and no coordinator manifest or BMP existed at freeze.

**Late exposure (disclosed before this freeze).** All scripts, thresholds and the text of §§1–11 were already written when the reviewer ran `git branch -vv` to check upstream tracking. That listing showed the subjects of other branches' latest commits:
- `coordination/bootstrap` `a1aba59`: "Record the single exposed critical recovery and release fresh-form custody"
- `coordination/wp-0019-replay` `9418bcc` (worktree `crop19-run`): "Assemble frozen Windows worker and fixed crop policy for local replay"

The reviewer opened neither commit and no file or diff from them. The first subject suggests a headline Stage 1 outcome, so this review is **not blind to that one-line headline**.

The only change made after the observation is this paragraph: no check, rule, threshold or script was edited. The replay's per-position results come from the frozen code, and the coordinator's claim gets no special treatment.

**Pre-freeze development runs.** All of them were CPU-only, used the archive and constructed controls, and wrote to scratch `wp0019-data/review`.
- `prefreeze-selftest-1` failed V3. The historical score files carry an extra `comparison` block, because they were scored with `--baseline` against the native arm. V3 now compares the score body without that block and asserts that it is the only extra key.
- `prefreeze-selftest-2` through `-5` passed 17/17, 17/17, 18/18 and 19/19 as controls were added.
- `prefreeze-env.json` holds the environment snapshot (§2).
- `expected-bgra.json` (committed) holds an independent render of all 64 pages (§3).

## 1. Scope and exclusions

This review covers Stage 1 on the exposed synthetic H (4 pages) and A (60 pages), with the same-pixel fixed crops and local `Windows.Media.Ocr` en-US on CPU only.

- **Out of scope:** Packet B, GPU, Baidu, training, automated correction, product or production code, and deployment.
- **Stage 2** is held. It runs only on a passing Stage 1 and a coordinator release (§9).
- The reviewer writes only to `docs/reviews/WP-0019`, its reserved report `docs/agent-reports/eld-rd-reviewer/WP-0019/003_2026-11-20_review_eld-rd-reviewer.md`, and scratch `wp0019-data/review`.

## 2. Runtime and asset identity (observed at freeze; re-observed on replay)

`review_checks.py env` reads files and the registry only.

| Item | At freeze | Historical (WP-0015) |
|---|---|---|
| OS | Windows 11 Home 26H2, build 10.0.26300.9974. The registry ProductName says "Windows 10 Home"; the CIM caption says 11. | not recorded; the adapter hard-codes `engine_version` 10.0.26100.9278 |
| `System32/Windows.Media.Ocr.dll` | `0db8e48e…ea1`, 876,544 B, fixed version 10.0.26100.9278 | `0db8e48e…ea1` (pin) |
| `OCR/en-us/MsOcrRes.orp` | `81771d77…908`, 219,754 B | `81771d77…908` (pin) |
| `WindowsCodecs.dll` | `df01c4d5…631`, 10.0.26100.9974 | not recorded |
| `windows.storage.dll` / `combase.dll` / `Windows.Graphics.dll` / `Windows.Globalization.dll` | `d31d1130…` / `b9136a89…` / `2a756ff3…` / `33c951cb…` | not recorded |
| Windows PowerShell | `d8f18256…52d`, 10.0.26100.9818 | not recorded |
| OCR languages | en-us only | en-US |
| Python (WP-0005 venv, read-only) | 3.12.10, exe `0b471133…c14`; numpy 2.2.6, Pillow 13.0.0, pypdfium2 5.15.2, PDFium 159.0.8149.0 | renderer identical (rasters.json) |
| CPU / power | AMD Ryzen 5 3600 (6C/12T); Balanced plan | — |

The OCR DLL and the en-US model are byte-identical to the historical pins, but the OS build and some imaging and runtime DLLs have changed since WP-0015. **Archive-versus-current differences are therefore disclosed, never assumed away (§5 X1/X2).**

On replay, the reviewer also records the worker's SDK identity from the frozen candidate:
- for C#: target framework, Windows SDK projection, CsWinRT and dotnet SDK versions, and the built binary hash
- for PowerShell: the projection path
- `worker.info`: language, `MaxImageDimension`, and any build or asset hashes it reports

## 3. Frozen pins and denominators

- **Scorer:** `1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7`. It always runs unchanged in a separate `python -I -B` process. The in-process copy is loaded from hash-verified bytes, without bytecode, and is used only for predicates and for the per-crop diagnostic reading (§6.5).
- **Baseline adapter:** commit `a0e738bc03e515999659dda09c5ee76d08fb37df` (`recognize.ps1` blob `897e294c`, `visual.py` `bb6e041d`, `formats.py` `596266b7`). Projection is `round(px*pt/size, 3)`.

**H pins:**
- source `e5270d9e…7eca7`, truth `91fd9ebc…e8ac`, rasters `b6342013…0947`
- 4 pages
- **19 criticals** (8 lines + 11 cells), 20 cells, 16 lines
- 1 blank cell (non-critical) and 6 spaced cells (non-critical)
- archive baseline 15/20 cells, 13/16 lines, 8/19 unflagged critical errors

**A pins:**
- source `671e8e18…d113c5b`, truth `0ec7d6a7…f99e6d`, rasters `0559c970…dfde336`
- 60 pages
- **252 criticals** (108 lines + 144 cells), 300 cells, 288 lines
- 22 blank cells (all non-critical, all correct at baseline) and 12 spaced cells
- archive baseline 235/300 cells, 237/288 lines, 94/252 unflagged critical errors

All criticals of both families stay in every denominator, whether or not they are selected (check S2).

**Witnesses** (as in WP-0018):

| ID | Location | Archive state |
|---|---|---|
| W1 | H p2 t1 r2 c1 | wrong, one word `IL801493` |
| W2 | A p60 t1 r2 c2 | wrong, one word |
| W3 | H p1 line 2 | wrong, split ID |
| W4 | H p2 line 2 | correct positive control |

**Zero-word A cells.** These were derived independently by self-test V4: no archive word box intersects a nonempty reference cell anywhere else in H or A.

| ID | Location | Critical |
|---|---|---|
| Z1 | p5 r5c1 | no |
| Z2 | p15 r4c2 | **yes** |
| Z3 | p20 r5c1 | no |
| Z4 | p30 r3c2 | **yes** |
| Z5 | p30 r5c1 | no |

All five archive observations are `''` and wrong.

**Expected admitted pixels.** `expected-bgra.json` holds the reviewer's independent 300-DPI PDFium render of all 64 pages. Every RGB digest equals `rasters.json`. It also lists the derived opaque top-to-bottom BGRA digest (H p1–p4: `d95c797a…`, `a7aa8b70…`, `f72b6826…`, `973e6f3b…`). The coordinator's manifests must match it (N2.expected).

## 4. Canonical run bundle and adapter rule

Every check consumes one JSON per run and order, with schema `wp0019-review-run/1`:

```
{schema, run, order: "AB"|"BA", clock,
 worker: {pid, info, startup_ns},
 warmup: {input, excluded: true, start_ns, end_ns, pid},
 arms: [{arm: "baseline"|"treatment", pid, start_ns, end_ns, setup_ns,
         families: [{family, prediction, start_ns, end_ns,
                     pages: [{page, start_ns, durable_ns,
                              full: {width, height, bgra_sha256, pixel_format, text,
                                     lines: [{text, words: [{text, bbox}]}], start_ns?, end_ns?},
                              grids?: [{xs, ys}],
                              crops: [{id, rect: [l,t,r,b], kind: "cell"|"line", region, width, height,
                                       bgra_sha256, source_rect_sha256, full_sha256, pixel_format, text,
                                       lines: [...crop px...], projected_words?: [{text, bbox}],
                                       decision, flagged}]}]}]}]}
```

- Arms are listed in execution order.
- Run names are `<source>-<order>`, for example `author-AB`, `author-BA`, `replay-AB` and `replay-BA`.
- `projected_words` follows the order of the crop's flattened words.
- An attempted crop that errored still appears, with its error; it counts as attempted.

**Adapter rule.**
- Author formats are unknown at freeze. A post-freeze adapter (`adapt_*.py`) may only rename, restructure or align fields into this schema.
- It is committed and pushed before its output is scored. It is first exercised on the reviewer's own replay output, so that author results are not seen before the replay (§8).
- Any field it cannot fill stays `null`. A null that a check needs makes that check fail or `NOT_RUN`, as written; nothing is synthesized.
- **No classification, gate, threshold or check definition may change after freeze.** A defect in reviewer code found later gets a dated addendum here with the diff, and both the pre- and post-fix outputs are retained.

## 5. Control checks (`review_checks.py`) — gating unless marked *obs*

| ID | Check |
|---|---|
| E1–E5 | **env.** E1 asset hashes versus pins and E2 OCR DLL version are *obs*. E3: en-US present. E4: renderer stack equals rasters.json. E5 on replay: assets and OS equal the freeze snapshot; a difference is disclosed, and a runtime change between the author and replay runs stops the affected comparison. |
| N0–N3 | **inputs (H/A).** Manifest keys, family and source digest equal the pins. Pages are 1..N and equal the PDF page count. The independent render RGB equals the rasters.json pin and the manifest `rgb_sha256`. The BMP, decoded by the reviewer's own parser (no Pillow), gives opaque BGRA equal to the manifest `bgra_sha256`, and that BMP's RGB equals the render byte for byte. Points equal the PDF size. The digest equals `expected-bgra.json`. Reviewer copies are byte-identical. |
| I0–I4 | **identity.** I0: worker language en-US and `worker.info` recorded. I1: within every run, the baseline and treatment full passes are equal on every page (width, height, input BGRA hash, pixel format, text, line texts, word texts and boxes; clocks excluded). I2: the full-pass input equals the admitted page and there is no resize. I3: the full pass is identical across all runs (author and replay, both orders). I4: the detected grid is identical in both arms. A failure stops the affected family comparison. |
| X1–X2 *obs* | The current full pass compared with the WP-0015 archive raw, classified per page as `identical`, `boxes_differ`, `order_or_grouping_differs`, `text_differs` (with word multiset differences) or `size_differs`. The archive raster digest equals the admitted RGB. The current grid compared with the archive `rule_tables`. Both archive and current outputs are preserved. |
| G0–G6 | **geometry and hashes.** G1: full-pass input equals the admitted page. G2: the baseline arm attempts no crop. G3, per crop: integer half-open rectangle with `0≤l<r≤W` and `0≤t<b≤H`; width and height equal the rectangle; the **reviewer's own slice** of the admitted BGRA (packed rows, no stride) hashes to the worker's `source_rect_sha256`, and to `bgra_sha256` when given; `full_sha256` equals the admitted page and that page's own full pass (*full-attach*: the crop is taken from the retained current page). G4: every projected word box follows one rule, either pinned round-3 or float within 1e-6 pt, from crop px plus (l, t). G5: one pixel format. G6 *obs*: cell crops sit at the declared integer inset inside the detected grid cell, and prose crops equal the nearest full-pass line union plus the declared padding, within 1 px. |
| T1–T8 | **timing and fairness.** T1: AB is full-only then full-plus-crops; BA is the reverse. T2: the warm-up and both arms run in the same worker PID. T3: the excluded warm-up precedes both arms. T4: the arms do not overlap. T5: every page, and the treatment's **own** full pass, starts and becomes durable inside its arm. T6: identical complete page sequence in both arms. T7: the baseline attempts no crop. T8: timed runs never overlap one another. The T checks are recorded for Stage 1 and gate only Stage 2 (§9). |
| K1–K2 | **static.** No critical reference token (≥6 characters, containing a digit; read from truth) appears in author code (`.py`, `.ps1`, `.cs`) at the frozen candidate revision. Keyword hits (`truth`, `historical-score`, `wp0018-data`, `critical`, `expected`, …) are listed and inspected by hand. K1 also guards against key-derived selection. |
| A0–A6 | **audit of reviewer replays** (`review_audit.py`). The Python audit hook blocks and records opens or listings below the deny prefixes (`wp0018-data`, `%USERPROFILE%/eLedgerCare-Speed`, `wp0019-data/{astra,carbon,coordinator}`, `docs/evaluation`, and any key directory). It also requires: no network events; only the declared worker executable launched; no image file written (crops stay in memory); no truth-, score- or key-named file opened; an untruncated log. |

The reviewer also inspects by hand, without execution:
- that the selector and merge read only full raw words, geometry and the detected grid
- that duplicate, blank and missing semantics are declared
- that setup is identical in both arms (the timed region starts at the admitted bitmaps in both)
- the worker's byte-equality proof before recognition
- the absence of resizing, pixel edits, border erasure or ID repair

## 6. Field-level scoring (`review_score.py`)

For each run and family, both arms are scored by the frozen scorer in separate processes, plus `--baseline` for `compare()`. Positions are joined by the scorer's `at` key over **every** reference cell and line. Critical records are merged in.

1. **Correctness `ok`:**
   - critical line: the scorer's standalone-token rule
   - critical cell: equality
   - non-critical: line or cell equality

   Flags never make a position correct.
2. **Transitions per critical:** WR, RW, WW and RR, with WW split into `WW_changed` and `WW_same` by (observed, flagged). The consistency check S3 requires `RW + WW_changed` to equal the length of the frozen `compare().new_or_changed_critical_errors`.
3. **Newly wrong = RW**, counted regardless of flag. **Newly unflagged** = a treatment that is wrong and unflagged where the baseline was not (correct, or wrong but flagged). Flag transitions are reported as 00/01/10/11. Flagged-but-wrong positions are reported as `flagged_recoveries_excluded`.
4. **Blanks** (expected `''`):
   - **Preserved** = right in both arms.
   - **Lost** = right then wrong, split into lost to `None` and lost to text.
   - **Recovered** = wrong then right.

   **Legitimate spaces** are measured on whitespace-token counts of the normalized observations:
   - `space_removed`: a spaced reference whose token count fell
   - `space_removed_RW`: the harmful subset
   - `critical_merge_recoveries`: a token count that fell and turned a critical from WR
   - `tokens_increased`

   Results are also reported per class (blank, spaced, single).
5. **Coverage and diagnostic crop reading.**
   - Crop rectangles are projected to points. A position is **covered** if a crop rectangle contains its reference-box centre; the crop with the largest overlap is chosen.
   - **Diagnostic reading:** the frozen `layout()` is applied to that one crop's projected words alone, using the fallback span joins with `tables=[]`. The reviewer computes this independently of the author's merge. It is the "diagnostic crop reading"; the treatment prediction is the "actual" reading.
   - Grid-mode baseline cells use the adapter's join order, while the diagnostic uses the scorer's (x0, y0) join. This difference is disclosed.
   - **Missed regions** are:
     - wrong-at-baseline criticals that are unselected (`missed_wrong_unselected`)
     - covered criticals whose crop reads zero words (`covered_zero_words`)
6. **Disagreement split.** `full_vs_crop` is `agree` or `disagree` between the baseline observation and the diagnostic reading, with `None` treated as `''`; unselected positions are labelled `unselected`.
   - The inferred decision is one of: `kept_full`, `took_crop` (each with or without a flag), `agree_*`, `unselected`, `unselected_changed` or `other`.
   - The author's recorded decision and region are attached as given.
   - The critical disagreement matrix is keyed by coverage, agreement, full R/W, crop R/W, decision and transition.
   - Its safe-replacement cells are:
     - (full W, crop R, took_crop) — recovery
     - (full R, crop W, took_crop) — harm
     - (full W, crop R, kept_full) — missed recovery
7. **Full-attach observation (S5, *obs*).** A position with no covering crop must keep its own full-pass (observed, flagged) in the treatment. Every violation is listed.
8. **Per-family baselines.** The current baseline counts are compared with the archive counts in §3, with the position-level differences listed. The gate always uses the **current same-run baseline**. Archive differences are disclosed, never substituted.
9. **Individual evidence** for W1–W4 and Z1–Z5 in every run:
   - the joined row (archive, current baseline and treatment)
   - nearby full-pass words (px and pt)
   - every touching crop, with rectangle, crop-px and projected words, its own reading, and the author's decision and region
   - selection or explicit non-selection
10. **Reproducibility (S4).** The per-position (observed, flagged) values of both arms must be identical across every run: author AB and BA, and replay AB and BA.

## 7. Stage-1 decision rule (frozen thresholds)

The per-run quality rule requires all of the following:
- **pooled H+A net critical recoveries (WR−RW) ≥ 1**
- **RW_H = 0 and RW_A = 0**
- the rule holds in **every** run (`author-AB`, `author-BA`, `replay-AB`, `replay-BA`), with all 19 + 252 criticals evaluable

`review_score.py` returns one score component:
- `PASS`: the quality rule holds in every run, and the runs are identical (S4)
- `FAIL_QUALITY`: the quality rule fails in any run
- `FAIL_NOT_REPRODUCIBLE`: the quality rule holds, but the runs differ
- `INCONCLUSIVE`: a required run is missing or not evaluable

`review_checks.py decision` then combines the gating failures of env, inputs, identity, geometry, static, audit and score:
- **STAGE2_RELEASE_SUPPORTED** requires zero gating failures and `PASS`.
- **CLOSE_AT_STAGE1** applies to `FAIL_QUALITY` or `FAIL_NOT_REPRODUCIBLE` when every control passed.
- **INCONCLUSIVE_CONTROL** applies to any gating control failure, which is listed per family. Stage 2 is then not supported, and the control issue is recorded separately from quality.

WW_changed, newly unflagged, blank, space and timing results are reported but do not gate Stage 1. A wrong-but-flagged critical is never a recovery. The reviewer's verdict is a recommendation; the coordinator makes the disposition.

## 8. Replay plan (this session, when resumed)

1. **Bind.** Fetch and verify on `origin` the coordinator-bound candidate SHA or SHAs and their trees. Extract them with `git archive` into `wp0019-data/review/replay/candidate-<sha12>`; no branch is switched and no shared checkout is staged. Then run K1/K2 static checks at those revisions (`--git REV:docs/research/WP-0019`).
2. **Env and inputs.**
   - `env --expect prefreeze-env.json --extra <worker binary>`
   - `inputs --expected expected-bgra.json --copy-to wp0019-data/review/replay/inputs` against the coordinator's `inputs/{H,A}/manifest.json`
   - compare the coordinator's current-control record (build, assets, startup) with E5
3. **Replay.** Run AB, then BA, serially and once each. Each order uses a new warm worker process, the author's exact frozen commands, the reviewer's manifests and BMP copies, and a fresh output directory. Each runs under `python -I review_audit.py --log … --deny … -- <author entry> …`.
   - The audit hook is active in both arms, and this is disclosed in the timing results.
   - The reviewer records wall clock and a process snapshot before and after, and confirms that no other timed WinRT run overlaps. No other owner's process is touched.
   - At most one documented infrastructure restart per order is allowed, and only before any output of that order is inspected. There is no outcome-driven retry.
4. **Freeze.** Hash every replay output into `replay-receipt.json`, then commit and push the receipt (and small outputs) before scoring.
5. **Adapter.** Write `adapt_*.py` from the author documentation and source, test it on the replay output, and commit and push it. Only then read the author evidence and adapt it.
6. **Execute.** Run `identity`, `geometry` (with the declared inset and padding), `timing`, `audit`, then `review_score.py score` on all four runs (archive scores attached), then `decision`.
7. **Report /003.** Record actual commands and results, failures, every changed file and external effect, and the checks not run.

**Needed from the coordinator to resume:**
- the bound candidate SHA or SHAs (Astra policy and runner; Carbon `engine.py` worker), plus any integration commit
- the exact AB and BA commands with the warm-up input
- the admitted `wp0019-data/inputs/{H,A}/manifest.json` and BMPs, with their admission receipt
- the current full-page control record
- the author evidence paths and format notes
- the declared inset and padding constants
- confirmation of the sole local CPU and WinRT timing window
- the explicit release to execute WinRT replay in reviewer scratch

## 9. Stage 2 (held; only after STAGE2_RELEASE_SUPPORTED and a coordinator release)

1. **Commitments.** The coordinator alone admits two fresh synthetic six-page families. It commits raster digests and answer-key digests separately, before execution, as `--pins` and `--commitments` JSON. The reviewer never receives keys before freezing.
2. **Check inputs.** `inputs-fresh`: the own-parser BGRA and RGB must equal the manifest and the commitment, plus the render when a PDF is supplied.
3. **Execute.** Run the same frozen candidate, unchanged, as a non-author without labels, in AB and BA orders under the audit hook, with key directories denied. There is no retuning and no outcome-driven retry.
4. **Freeze.** Commit and push the hash receipt of the durable predictions and run receipts, and send the SHA to the coordinator.
5. **Score.** After the coordinator releases the keys, verify each key digest against its commitment, then run `review_score.py score --stage 2 --pins …` and `timing --pins … --ppm-threshold 30`.
6. **Recommendation.** A larger research trial is recommended only if all of the following hold:
   - all controls and custody checks pass
   - **pooled fresh critical WR ≥ 1** (with RW = 0, which equals net ≥ 1)
   - **RW = 0 per family**
   - **zero lost blanks per family**
   - **treatment pages/min ≥ 30.0 in both AB and BA**, computed as 60 × pages divided by ready-input-through-durable seconds of the treatment arm; startup is excluded and reported separately

   Inconclusive controls and custody issues are recorded separately. No product change is promoted.

## 10. Timing definitions (both stages)

- **Per-arm figures:**
  - **ready-to-durable** = `end_ns − start_ns`, from the first admitted bitmap consumed to the last durable prediction write; it includes selection, cropping, recognition, layout/merge and writes
  - pages/min and ms/page
  - attempted crops and crops/page over **all** pages
  - per-family breakdown
  - `setup_ns` and worker `startup_ns`, reported separately
- **Added ms/page** = (treatment − baseline) / pages, for AB and BA separately and as their mean. A single order is never quoted as the effect.
- **Disclosure:** the CPU, the power plan, the active audit hook, and the process snapshot.

## 11. Script validation receipt

Run `review_selftest.py` (archive plus constructed controls) at the frozen revision. Its check groups are:

| Checks | What they confirm |
|---|---|
| V1–V5 | scorer identity; denominators and blanks; archive baselines (separate process) equal the historical body; the five zero-word cells; pinned projection of all 1,389 archive spans |
| V6 | self-join: zero transitions and `FAIL_QUALITY` |
| V7 | constructed transitions: WR 2, RW 1, flag-only, newly unflagged, blank loss, space loss, a merge recovery, plus crop coverage, the diagnostic reading, disagreement and `took_crop` |
| V8 | the `PASS` and `FAIL_NOT_REPRODUCIBLE` gate paths |
| V9 | the BMP parser and slicing |
| V10–V12 | the geometry, identity and timing detectors |
| V13 | the audit hook and summarizer |
| V14 | the static leak detector |
| V15 | the H render/BMP/inputs path |
| V16 | the Stage-2 pins and commitments path: a lost blank fails Stage 2 but not Stage 1 |

The receipt records the SHA-256 of every review source it used. It is committed after this freeze as evidence; it is not a WP-0019 result.
