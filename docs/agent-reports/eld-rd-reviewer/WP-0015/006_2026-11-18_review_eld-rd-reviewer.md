# WP-0015 / 006: Independent held-out replay and disposition of the scanned-packet OCR architecture trial

- Report path: `docs/agent-reports/eld-rd-reviewer/WP-0015/006_2026-11-18_review_eld-rd-reviewer.md`
- Sequence reservation: [INDEX.md WP-0015](../../../../INDEX.md#wp-0015-scanned-packet-ocr-architecture-trial), sequence 006 (review), reserved at `c4d7734d0be6302e667d290698bc671631c71ce9`
- Category: review
- Author / agent ID: `eld-rd-reviewer`
- Actual model / effort: Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code. Applied effort is not exposed to the session. One continuous session from the readiness check to this report.
- Execution environment:
  - CLI: Claude Code on Windows 11, Git Bash.
  - CPU analysis: system CPython 3.12.10, standard library only.
  - Model launches: Q0 interpreter `C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe -I -B`, on RTX 5070 Ti `GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d`, driver 621.01.
- Published by: `eld-rd-reviewer`
- Timestamp: 2026-11-18T05:23:47Z
- Repository / branch: `jackgumpe/eledgercare`, `review/wp-0015-architecture`, worktree `eledgercare-worktrees/speed-review`
- Base revision: `c4d7734d0be6302e667d290698bc671631c71ce9`
- Deliverable revision: `db4a6df932a74535c9d677c2db561594b4368624`. This is the last evidence commit before this report. The scored H and A evidence is at `ce4206f20d63101f6344121eaaeeeb86d2ec85a0`.
- Previous report: none by this author in WP-0015
- Related or reviewed reports:
  - [Astra 001](https://github.com/jackgumpe/eledgercare/blob/0f65eb6e580a91ac5276440e4d052ebb596d26ca/docs/agent-reports/eld-rd-astra/WP-0015/001_2026-11-18_research_eld-rd-astra.md) at `0f65eb6`
  - [Carbon 002](https://github.com/jackgumpe/eledgercare/blob/28336734741c1ed33f1e6fd7b19dd6268a04fe93/docs/agent-reports/eld-rd-carbon/WP-0015/002_2026-11-18_research_eld-rd-carbon.md) at `2833673`
  - [Custodian 003](https://github.com/jackgumpe/eledgercare/blob/3db4b71fd6ef5f947eadd4d64b63108d8b1650e2/docs/agent-reports/eld-eval-custodian/WP-0015/003_2026-11-18_verification_eld-eval-custodian.md) at `3db4b71`
  - **[Astra 004](https://github.com/jackgumpe/eledgercare/blob/9a8ac1e68849a8871c6e7ca5a61c3c2cf3b7d731/docs/agent-reports/eld-rd-astra/WP-0015/004_2026-11-18_research_eld-rd-astra.md) at `9a8ac1e68849a8871c6e7ca5a61c3c2cf3b7d731`**
  - **[Carbon 005](https://github.com/jackgumpe/eledgercare/blob/9f0f9e9f79f01264b9828e838055d521f1269235/docs/agent-reports/eld-rd-carbon/WP-0015/005_2026-11-18_research_eld-rd-carbon.md) at `9f0f9e9f79f01264b9828e838055d521f1269235`**
- Status: accepted as an independent review. I recommend the coordinator accept the retain-baseline disposition with the limitations below.
- Next owner: `eld-coordinator` (WP-0015 / 007)

## Summary

This is an independent review. I authored none of the reviewed treatment, harness, scorer or fixture code. My helpers are confined to `docs/reviews/WP-0015/`.

On fresh synthetic held-out packets, I independently executed:
- the ordinary native Baidu BF16 control and the Windows OCR challenger on the four-page H packet, twice, in opposite orders;
- the full 60-page A packet, once as a primary attempt that failed, and once as a UTF-8 recovery that completed;
- Carbon's frozen `carbon_bf16` compound against ordinary native on H, in both orders.

**Results by arm:**
- **Native:**
  - It is the only complete arm inside the quality budget at full scale.
  - It is slow: **1,061.187 s** for 60 pages, or 3.39 pages/min.
  - It is not unattended-safe: **38/252** unflagged critical errors.
- **Windows OCR:**
  - It is about 68× faster: **15.655 s** for 60 pages.
  - It fails the budget on tables: **235/300** cells against native's **288/(300+37)**.
  - It nearly triples the unflagged critical errors: **94/252**.
- **Carbon:**
  - On H it gives a real but small gain inside the quality budget: **44.566 / 45.393 s** against native's **51.214 / 50.982 s**.
  - It does not have exact token parity.
  - It was never run at 60 pages.

**No arm qualifies unattended or production use.** B and any 60-page Carbon run remain unrun. I concur with both authors' convergent disposition: retain resident native BF16 as the source-linked reference for operator-reviewed extraction, and defer any production architecture change.

## Objective and acceptance criteria

The [assignment](../../../coordination/WP-0015/assignment.md) asks for:
- an uninvolved reviewer who executes real held-out pairs on frozen source;
- alternating order in fresh warmed processes;
- immutable raw output and tokens;
- the frozen scorer.

It also requires reporting:
- fastest complete and fastest inside budget;
- fidelity deltas against +0.01 CER and −0.02 cell accuracy;
- new critical or wrong-source errors;
- noise from paired controls;
- whether any author claim survives independent replay.

The [analysis plan](https://github.com/jackgumpe/eledgercare/blob/592a657645765ee458e7e19a105a22c4a4b41bfe/docs/coordination/WP-0015/analysis-plan.md) at `592a657` was read before any held-out access. Its rule: improvement in both orders beyond the control spread, then a reviewer effect of the same sign.

## Change inventory

All added paths are under `docs/reviews/WP-0015/` or this report directory, on `review/wp-0015-architecture`. No production, research-author, evaluation, coordination, INDEX or CURRENT path was edited.

| Action | Path | Purpose |
| --- | --- | --- |
| Merged | `82206bc` (Astra harness), `3db4b71` (custodian, custody source `7598bf41`) | Frozen inputs for replay (merges `1db8787`, `888af5a`) |
| Added | `README.md`, `precheck.py`, `make_plans.py`, `analyze.py`, `selftest.py`, `evidence/precheck-03.json` (`4d2767d`) | CPU scorer and adapter probes, plan generator, two-stage verifier and its self-test |
| Added | `child_gone.py`, `freeze.py`, `evidence/H-blind-inventory.json` (`bd48af1`) | Process-absence check; blind pre-key hash inventory |
| Added | `evidence/H-scored-receipt.json` (`d4f52a0`) | Non-revealing H scoring receipt |
| Added | `partial.py`, `evidence/A-blind-inventory.json`, `evidence/A-blind-receipt.json` (`6bfe778`) | Verifier for a failed document's durable prefix; A primary inventory |
| Added | `compare_runs.py`, `evidence/A-recovery-blind-inventory.json`, `evidence/A-recovery-blind-receipt.json` (`9fca3b9`) | Cross-run agreement; A recovery inventory |
| Added | `scored_summary.py`, `scored-summary.md`, `evidence/scored-H-A.json` (`ce4206f`) | Scored H and A evidence |
| Added | `verify_carbon.py`, `token_diff.py`, `scored-H-carbon.md`, `evidence/scored-H-carbon.json` (`db4a6df`) | Scored Carbon H evidence |
| Added (this commit) | `docs/agent-reports/eld-rd-reviewer/WP-0015/006_2026-11-18_review_eld-rd-reviewer.md` | This report |

One merge commit, `ce49e57`, prepared by the coordinator, brought Astra's later commits `0186467`, `a114c8d` and `a0e738b` onto this branch for the UTF-8 recovery. Neither the merge nor those commits is reviewer-authored. No path outside `docs/reviews`, `docs/research`, `docs/evaluation` or `docs/agent-reports` differs from the base.

**External effects**, all under `C:/Users/jackg/eLedgerCare-Speed/WP-0015/review/`:
- `runs/` holds six reviewer run directories;
- `analysis-*` holds private score files;
- `private-tools/sensitivity.py` is an early private header sensitivity, superseded by the author's public rule;
- small dry-run and self-test folders;
- about 0.3 GiB in total.

No Q0, model, product, service or global configuration was modified.

## What I reproduced (executed) and what I only inspected

### Executed by this reviewer

| Run (release) | Source | Order | Outcome | Supervised wall |
| --- | --- | --- | --- | ---: |
| `h-r1-ab` ([release](../../../coordination/WP-0015/h-r1-ab-release.json), umbrella `1af7fcc3`) | `82206bc` | native, then Windows | exit 0 | 101.550 s |
| `h-r2-ba` ([release](../../../coordination/WP-0015/h-r2-ba-release.json)) | `82206bc` | Windows, then native | exit 0 | 103.905 s |
| `a-scale-ba` ([release](../../../coordination/WP-0015/a-scale-ba-release.json), `01af1e6c`) | `82206bc` | Windows, then native | **exit 1**: native failed after 36/60 durable pages | 710.358 s |
| `a-recovery-ab` ([release](../../../coordination/WP-0015/a-recovery-ab-release.json), `e4bbeae7`) | `a0e738bc` (UTF-8 stdio only) | native, then Windows | exit 0 | 1,126.825 s |
| `h-carbon-ab` ([release](../../../coordination/WP-0015/h-carbon-ab-release.json)) | `7e70391c` | native, then carbon_bf16 | all segments exit 0 | 189.135 s |
| `h-carbon-ba` ([release](../../../coordination/WP-0015/h-carbon-ba-release.json)) | `7e70391c` | carbon_bf16, then native | all segments exit 0 | 190.187 s |

**Resource returns:**
- There were six launches, with no retries and no guard stops. Total supervised GPU wall time was 2,421.96 s.
- After every run, a PID and creation-time check found the supervisor, venv launcher and trial child all absent.
- The coordinator's return records are `*-return.json` alongside each release.

**CPU checks I executed:**
- `check_score.py`: 26/26 controls pass.
- My scorer and adapter probes.
- A self-test of my verifier.
- Stage 1 verification before any key: 0 failures on every complete run.
- The A primary failure, recorded as the expected three failures.
- Prefix verification of the failed native A document.
- Blind hash inventories, committed before each key request.
- Re-checks against those inventories before scoring: H 106 files, A primary 293 files, 0 mismatches.
- The frozen `score.py` in a separate process for every prediction, cross-checked in-process.
- The public title-level rule from commit `0186467`, unchanged.
- Critical transitions, supplemental numeric and page checks, token-parity and token-diff analysis.

### Inspected only (not reproduced)

- **Author development runs and dense crossovers:** Astra's `dev-ab-01` and `dev-ba-01`; Carbon's `carbon-moe-01`, `carbon-dense-ab` and `carbon-dense-ba`.
- **Carbon's profiler stage attribution.**
- **Custodian material:** the fixture rebuild (`development.py`) and raster audit (`audit.py`). They need PIL and pypdfium2, which this session's permitted Python lacks; Q0 execution was approved only for the bound launches. Dev files are matched by hash only.
- **Not accessed:** B (sealed), any 60-page Carbon run (none exists), product admission or search, and the original briefs.

## Key held-out results

All timings run from the accepted-input clock to the durable final `prediction.json`.

### Full-scale A (60 pages: 8,821 characters, 300 cells, 252 critical values)

| Measure | Native (`a-recovery-ab`) | Windows (`a-recovery-ab`) |
| --- | --- | --- |
| Complete document / first page / last page | **1,061.187 s** / 49.372 / 1,061.178 | **15.655 s** / 0.266 / 15.648 |
| Pages/min | 3.39 | 229.96 |
| Position-correct cells | **288 / (300 + 37 extra)** = 0.855 | **235 / 300** = 0.783 |
| CER, frozen adapter / title-level corrected | 0.2825 / 0.1477 | 0.0291 |
| Unflagged critical errors | **38 / 252** (37 corrected) | **94 / 252** |
| Windows critical transitions vs corrected native | — | 60 new where native was correct, 27 changed, 7 same, 3 repaired |
| Budget vs matched native | control | **fails**: cells −0.071 |

**Source trace:**
- All 60 page identities and RGB pins were verified in both arms.
- Page 60 traces to the A PDF `671e8e18…3c5b` and its pin `3c8cdf6d…bc17`.
- Page 60's critical cell at row 2, column 2, expected `0I8O1-139`:
  - native reads it correctly, but only by table-block ordinal, with no word geometry;
  - Windows reads `01801-139`, from a word box `[128.4, 233.9, 178.8, 242.1]` inside the truth cell `[123, 226, 258, 256]`.
- Both arms misread page 60's critical line `L8O8I-395`.
- No identifier or amount moved to another page, and no page-content swap was detected.

**A has one complete independent native baseline.** The primary attempt stays in the attempt count as a failure, with no rate:
- it failed 645.350 s after dispatch;
- the cause was a cp1252 `UnicodeEncodeError` in the native per-token streamer writing to the trial child's redirected stdout;
- its 36 durable pages and 12 windows are token-, raw- and stop-identical to the recovery, and serve only as a diagnostic.

The Windows A prediction is byte-identical across both A runs.

### H (4 pages: 570 characters, 20 cells, 19 critical values)

| Arm | Complete s, both orders | Cells | Corrected CER | Unflagged critical |
| --- | --- | --- | ---: | --- |
| native (ordinary, four runs) | 51.916 / 55.262; 51.214 / 50.982 | 18 / 20 | 0.0035 | 2 / 19 |
| **carbon_bf16** | **44.566 / 45.393** | 18 / 20 | 0.0035 | 2 / 19 |
| Windows | 1.023 / 1.053 | 15 / 20 | 0.0263 | 8 / 19 |

- **Carbon's saving:**
  - 6.648 s and 5.589 s, or 1.149× and 1.123×.
  - Both exceed the native spread within its pair (0.232 s) and across all four native H runs (4.280 s).
  - Quality change against same-run native is ΔCER 0 and Δcells 0, under both parsers, with 0 new or changed critical values.
- **Carbon's exactness:**
  - Native is token-identical across all four runs (497 tokens).
  - Carbon is token-identical between its own two orders but differs from native in **12 of 497 tokens**. All are box coordinates moved by ±1 model unit.
  - It therefore has **no exact parity**.
- **Windows on H:** it fails the budget, with cells −0.150 and corrected CER +0.0228.

**H decision:**
- fastest complete: Windows;
- fastest complete inside the budget: carbon_bf16;
- no arm unattended-eligible.

## Cross-check of the author reports

**Astra 004.** Every held-out figure matches my evidence:
- H and A timings, cells and critical counts;
- the 37 extra native cells;
- corrected CER deltas of +2.28 and −11.86 points;
- transitions 59/3/28/7 against frozen native and 60/3/27/7 against corrected native;
- the page-60 example and the Carbon H pair.

Two notes:
- **Wording:** Astra says the A failure was "a diagnostic write ... in the Windows child console stream". It was the native arm's per-token `TextStreamer` writing to the trial child's cp1252 stdout. The Windows OCR reader was not involved.
- **Rounding:** the AB Carbon saving is 6.647 s in both reports from unrounded clocks, and 6.648 s in my table from rounded ones.

Astra's development results and title-level sensitivity are consistent with my H and A rescoring under the same public rule.

**Carbon 005.** Every held-out H and A figure it attributes to my commits matches: timings, 18/20 and 2/19, the 0.232 s spread, coordinate-only token differences, and the A counts.

Its own claims that I did not reproduce:
- the dense crossover, where its own BA saving of 2.272 s sits below the 3.822 s native spread, as Carbon discloses;
- the profiler stage attribution.

**I agree with Carbon** that:
- its pre-registered ≥5× falsifier failed;
- its earlier ">97% sync/MoE-loop" attribution is withdrawn.

**Its replacement diagnosis is not yet causal.** The diagnosis says the cost is eager-kernel launch overhead in `_dash_decode_forward` on WDDM. That is inferred from deferred CUDA-event spans and host spans, a source operation count, and low GPU utilisation; it was not tested by intervention. The profiler itself added 6.254 s (about 17%).

Carbon's proposed single-step CUDA-graph capture is the right intervention test. It is untested.

**Retain-baseline disposition.** Both authors converge on the same disposition:
- retain unmodified resident native BF16 as the reviewable reference;
- don't promote `carbon_bf16`;
- don't use Windows OCR as an authoritative or unattended replacement;
- human review stays mandatory.

My independent evidence supports all four points. I concur, and I don't dissent on the disposition.

## Decisions and rationale

**Fixed rules.** Decisions use the pre-registered rules unchanged: complete document, matched control, both orders beyond control spread, +0.01 CER and −0.02 cells, and unattended-gate exclusions.

**Sensitivity is reported, not substituted.** The title-level correction is reported alongside the frozen adapter. It reverses the H CER sign for Windows, but on cells Windows fails either way, so no decision depends on choosing the adapter.

**Residual native markup.** I didn't correct malformed native box headers: 26 of 60 A pages have them, and they fall outside the documented grammar. They stay charged to native.

**Scope of each conclusion.** A conclusions rest on one complete native observation. H conclusions rest on four native and two Carbon observations of one four-page family. Neither supports a population percentile.

## Risks, disagreements, and unfinished work

1. **Scorer limits found in CPU probes** ([precheck evidence](../../../reviews/WP-0015/evidence/precheck-03.json)):
   - At 60-page denominators, a fabricated off-line critical amount, or a duplicated critical row exactly at −0.020 cells, passes every frozen gate.
   - Flagged errors satisfy the unattended gate.
   - `wrong_source` is structurally zero for this harness, because page links are stamped from request position.
   - None of these changed a held-out decision here, since both arms failed anyway. My numeric-surplus and page-alignment checks found no such pattern beyond native's invented tables on A pages 41 and 56, which were charged as extra cells.
   - **Any future unattended claim needs hardened scoring:** surplus and missing-value checks, flag-rate limits, and evidence-based page provenance.
2. **Harness defects disclosed:**
   - the cp1252 streamer crash, fixed only in `a0e738bc`; Carbon's candidate `7e70391c` still lacks the fix in its native path, though `carbon_bf16` disables streaming;
   - the title-level parse;
   - malformed native headers;
   - RGB pins optional in `launch.py`;
   - VRAM and temperature sampled but not enforced during runs;
   - a document failure stops the rest of its plan.
3. **Unrun:**
   - B;
   - any 60-page Carbon run;
   - A control noise;
   - a second unseen 60-page family;
   - product admission, database commit, search, and operator Extract-to-search time;
   - human review time.
4. **Not exposed:** the Windows OCR backend is opaque. The OS file cache and device clocks were uncontrolled.
5. **Remaining disagreement:** none on the disposition. Carbon's dissent against using Windows OCR to prefill F3 fields, route on IDs or amounts, or populate F4 search is recorded. My A evidence (94/252 unflagged critical errors, 60 new) supports that caution.

## Narrower directions that survive

These are R&D candidates, each needing a separate authorization. None is a product release.

1. **carbon_bf16 as a changed-output native accelerator.** It needs:
   - matched 60-page A and B runs in both orders, with the UTF-8 and title-level fixes;
   - a critical-error check per source position.

   On H it gave about 1.13–1.15× with zero quality change. Even sustained, that would leave a 60-page packet at about 15 minutes.
2. **Single-step CUDA-graph capture over carbon_bf16** (Carbon's proposal). It is the cheapest causal test of the launch-overhead hypothesis. If it misses ≥5×, close single-GPU eager decode work on this model.
3. **Windows OCR as a badged, non-persisted, source-linked review preview** (Astra's assisted-workflow proposal). The selector, fallback, persistence and human verification time must be measured on new matched scans, scoring missed critical values per source position. Carbon's dissent sets the limits.
4. **Product hygiene before any reuse:** UTF-8 worker stdio, title-level parsing, malformed-header handling, and the scorer hardening in risk 1.

## Verification

| Check | Environment / revision | Result | Evidence |
| --- | --- | --- | --- |
| `python -B docs/evaluation/WP-0015/check_score.py` | system CPython 3.12.10 / `888af5a` | 26/26 pass | [README](../../../reviews/WP-0015/README.md) |
| `precheck.py`, `selftest.py` | same / `4d2767d` | identities pass; probes S1–S5, N1–N3c; self-test catches all tampering cases | [precheck-03.json](../../../reviews/WP-0015/evidence/precheck-03.json) |
| Six bound launches (table above) | Q0 interpreter, sources as listed | as listed; process trees absent | `*-release.json` / `*-return.json`; [H inventory](../../../reviews/WP-0015/evidence/H-blind-inventory.json), [A inventory](../../../reviews/WP-0015/evidence/A-blind-inventory.json), [A recovery inventory](../../../reviews/WP-0015/evidence/A-recovery-blind-inventory.json) |
| `analyze.py` stages 1 and 2; `partial.py`; `compare_runs.py` | CPython / `bd48af1`…`9fca3b9` | 0 failures on complete runs; A primary has the 3 expected; prefix 36/36 identical; Windows A repeat identical | private `analysis-*`, hashed in the receipts |
| `scored_summary.py`, `verify_carbon.py`, `token_diff.py` | CPython / `ce4206f`, `db4a6df` | figures as reported above; truth, rasters, pins, scorer and inventories all verified | [scored-summary.md](../../../reviews/WP-0015/scored-summary.md), [scored-H-carbon.md](../../../reviews/WP-0015/scored-H-carbon.md) |

**Checks not run:**
- `audit.py` and the `development.py` rebuild (no PDFium in the permitted CPU interpreter);
- the authors' development and profiler runs;
- B;
- any 60-page Carbon run.

**Permission denials (actual):**
- the Q0 interpreter at CPU-preparation time;
- `tasklist`;
- file-tool reads of the Carbon worktree (I read the same commit through `git`);
- one inline command containing `#`.

## Review map

- **Scored evidence:**
  - [scored-summary.md](https://github.com/jackgumpe/eledgercare/blob/ce4206f20d63101f6344121eaaeeeb86d2ec85a0/docs/reviews/WP-0015/scored-summary.md) at `ce4206f`;
  - [scored-H-carbon.md](https://github.com/jackgumpe/eledgercare/blob/db4a6df932a74535c9d677c2db561594b4368624/docs/reviews/WP-0015/scored-H-carbon.md) at `db4a6df`;
  - JSON under `docs/reviews/WP-0015/evidence/`.
- **Frozen sources:**
  - harness `82206bc` and `a0e738bc`;
  - Carbon `7e70391c`;
  - custody `7598bf41`, scorer `1ceb36fe…f7bf7`;
  - model revision `0480966938291445591f69f08a13b041c073a96a`.
- **Reviewed reports:** Astra 004 at `9a8ac1e6`; Carbon 005 at `9f0f9e9f`.

## Handoff

- **Next owner:** `eld-coordinator`, for WP-0015 / 007 disposition and INDEX and CURRENT updates.
- **Branch:** `review/wp-0015-architecture`.
- **Report path:** `docs/agent-reports/eld-rd-reviewer/WP-0015/006_2026-11-18_review_eld-rd-reviewer.md`.
- **Deliverable SHA:** `db4a6df932a74535c9d677c2db561594b4368624`. The report publication SHA is supplied in the handoff message after the push.
- **Publication receipt:** remote confirmation follows in the handoff message. This report is not rewritten to add it.
