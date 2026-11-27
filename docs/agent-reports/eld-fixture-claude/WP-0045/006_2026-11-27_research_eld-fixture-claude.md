# WP-0045 / 006: A2 page-phase reconciliation and post-opening oracle correction r1

- Report path: `docs/agent-reports/eld-fixture-claude/WP-0045/006_2026-11-27_research_eld-fixture-claude.md`
- Sequence reservation: INDEX.md § "WP-0045 A2 oracle reconciliation" on `coordination/bootstrap` at `ae6e60fd2890ac99b2a42204ca3339c61e8375e0`
- Category: research (supplemental to /001)
- Author / agent ID: eld-fixture-claude, the same role and source author as the sealed oracle
- Actual model / effort: Claude Code, model `claude-opus-5-5`. The applied effort is not exposed; INDEX requested high.
- Execution environment: Claude Code CLI on Windows 11 under an ordinary user account. CPython 3.12.10 ran with `-I -B`, standard library only.
- Published by: eld-coordinator transports this branch unchanged
- Timestamp: 2026-11-27T18:09:13Z
- Repository / branch: jackgumpe/eledgercare, `research/wp-0045-fixtures`, worktree `eledgercare-worktrees/w045-fixtures`
- Base revision: `803150533a0fa74e78ad556cf03f1961c4af75dc` (the unchanged /001 report commit). Its ancestors include the opened artifacts at `3d8a82ed0cdf21f000c0eb612b3c48c6f6cb0d32`.
- Deliverable revisions:
  - correction and regression frozen before execution: `cd8e4796ff89da361e89aed8d96267f213bdcc96`
  - first-execution results: `fc46492bd115a8547b155b0e71c919ff375c7edc`
- Previous report: WP-0045 /001, which is unchanged and immutable
- Related reports: /004 (eld-rd-reviewer) verifies this independently. I have not read any candidate implementation, output or report.
- Status: ready-for-review
- Next owner: eld-rd-reviewer for independent verification, then eld-coordinator for disposition

## Summary

The coordinator reported that the sealed oracle and both frozen blind candidates agree on `A2.illegal_repeat`: status `M` and `first` = `["repeat",1]`. They disagree on whether `["page",2]` is a conflict. I conclude that **the sealed oracle is wrong on this row and the pair `["page",2]` belongs in `conflicts`**.

The pre-input wire says each later phase changes only its own blocked IDs. It also says each phase is compared with "its immediate supplied predecessor and its stipulated own mask". The sealed oracle, by its disclosed choice I6, compared the page phase against the *cumulative* mask instead. The wire is not silent on this point, so I6 conflicted with it.

I froze a separately versioned correction, `wp0045.expected.r1`, together with a six-case regression. I committed them before running either. On first execution:

- The opened v1 oracle still reproduces all 32 rows byte for byte.
- r1 agrees with my hand-written intent on 32/32 rows.
- **Exactly one row differs from v1**, and only in one field: `A2.illegal_repeat` `conflicts`, which gains `["page",2]`.
- The regression passes 6/6 as frozen.

The opened oracle, its expected rows, the inputs and the commitment are unchanged. **The original blind A2 count of 5/6 stands.** r1 is a post-opening reconciliation and not a blind result.

## Question and the evidence that decides it

**Question.** On a cell blocked at the repeat phase only, where the supplied repeat word is not exact −∞, should the page phase be checked against the cumulative mask (page must be −∞) or against its own mask and its immediate predecessor (page must equal the repeat word bit for bit)?

**The input.** `A2.illegal_repeat` has input SHA-256 `9905e9981430bd723678c67c16478d2f20138eacf62ee3790a855ba2aed2d042` in the manifest. Its opened v1 expected row has SHA-256 `d8ac676a25c2…`. Its arrays are:

- raw = [3f800000, 40000000, 40400000, 3f000000, c0000000]
- repeat = [3f800000, 40000001, **ff7fffff**, 3f000000, c0000000]
- page = [ff800000, 40000001, **ff800000**, 3f000000, 40000000]
- repeat_block = [2], page_block = [0]

At index 2 the repeat phase wrote ff7fffff (−3.4028235e38, the most negative finite value) where it should have written ff800000. The page phase then changed that word to ff800000, although index 2 is not in its own block [0].

**Source 1: the pre-input wire, the governing interface.** This is `docs/coordination/WP-0045/wire.md` at reservation `1439d0c944a38d0993283b0485f59daa15b73be4`, SHA-256 `dbff3deec5b6791377fd6e55b6b41cdb7d0e29b36955933e780cbc9adb7c4c30`. It has not changed since, and its A2 paragraph says:

> (W1) "Later phase adds exactly its native blocked IDs to cumulative support exclusion, changing **those words only** to exact negative infinity and preserving every unmasked word bit-for-bit."
>
> (W2) "Report all conflicting [phase,index] pairs ordered by phase then index, **comparing each phase to its immediate supplied predecessor and its stipulated own mask**; this lets independent defects coexist."

In W1, "those words" refers to the phase's own blocked IDs. Cumulative exclusion appears only as what the phase *adds to*, which is support. W2 gives the comparison basis for conflicts, and it names the phase's *own* mask and its *immediate supplied* predecessor. At page index 2, the own mask is {0} and the predecessor is ff7fffff. The page phase changed a word outside its own block, so `["page",2]` is a conflict.

**Source 2: Paper I, Edition 02, clause (A2).** This is the shared `tex/model.tex`, SHA-256 `44785632…c179`, pinned in `source-pins.json`. Clause (A2) has only the final-readout validity bracket `[A ≠ ∅, z_{2,A} ∈ ℝ^{|A|}, z_{2,A^c} = −∞]`. Paper I p. 2 adds "Fail closed on an empty or inconsistent mask, unexpected nonfinite values… Preserve the original phase bytes." The bracket is a precondition on the final array z₂ for decoding. It does not define a phase-to-phase conflict list.

Gemini's advisory objection 2 makes the same point: Edition 02 lacked bitwise preservation between phases, and the wire's W1 and W2 supply it. Paper I therefore does not support using a cumulative mask as the *comparison basis* for the page phase, and the wire, which is more specific and post-dates it, excludes that basis.

**Counter-reading considered and rejected.** One could read "every unmasked word" in W1 cumulatively and conclude that a cumulatively masked word only has to be −∞. That reading contradicts "changing those words only" in W1 and "its stipulated own mask" in W2. It also prevents "independent defects [from] coexist[ing]": the page phase's own unauthorized write at index 2 would be absorbed by the earlier repeat defect.

## The corrected rule and what it can change

For phase f ∈ {repeat, page} with immediate supplied predecessor π (raw for repeat, repeat for page) and own block b_f:

  conflict [f, i]  ⇔  f_i ≠ (ff800000 if i ∈ b_f else π_i),  compared bitwise.

`allowed` = [0, n) ∖ (b_repeat ∪ b_page) is unchanged, so cumulative exclusion governs support only. The raw-finiteness conflicts, the ordering, `["support",-1]`, the status, `first` and `winner` rules are all the same as in v1.

**Claim (difference locus).** For any well-formed A2 input, v1 and r1 can differ only in the page entries of `conflicts`. They differ only when the same input already has a repeat conflict, so `status`, `first`, `allowed` and `winner` are always equal.

*Proof.* Let X₁ = b_repeat and X₂ = X₁ ∪ b_page. The raw and repeat checks are identical in v1 and r1, because for repeat the own block is X₁. At a page index i there are three cases:

1. If i ∈ b_page, both versions require ff800000.
2. If i ∉ X₂, both require repeat_i.
3. If i ∈ X₁ ∖ b_page, v1 requires ff800000 and r1 requires repeat_i.

The two requirements in case 3 coincide unless repeat_i ≠ ff800000. Since i ∈ X₁, that same condition is a repeat conflict `["repeat", i]` in both versions. Hence any difference comes with a shared repeat conflict, which gives status M (and winner null) in both. `first` is the earliest conflict in phase order, and raw and repeat conflicts precede every page conflict and are identical in both versions, so `first` agrees. `allowed` does not depend on conflicts. ∎

*Worked example.* In `A2.illegal_repeat`, i = 2 ∈ X₁ ∖ b_page and repeat₂ = ff7fffff ≠ ff800000. v1 requires page₂ = ff800000, which holds, so it reports no page conflict. r1 requires page₂ = ff7fffff, which fails, so it reports `["page",2]`. Both versions already have `["repeat",2]`, and both give status M, `first` `["repeat",1]` and winner null. This is exactly the reported disagreement.

*Boundary.* If the predecessor's masked cell is correct (ff800000), the two readings coincide. This covers regression cases G3 and G4, and A2.clean, masked_nan, raw_inf, signed_zero and empty.

## Distinguishing experiment (frozen before execution)

The regression file `reconciliation/regression.json` holds six hand-specified cases on 3-word arrays. Each records the r1 fields, the v1 conflicts and whether the two readings should differ:

| Case | Page behaviour at a repeat-blocked cell | r1 conflicts | v1 conflicts | Differs |
| --- | --- | --- | --- | --- |
| G1 restore_after_defect | Rewrites a defective ff7fffff to −∞ | [repeat,1],[page,1] | [repeat,1] | yes |
| G2 carry_defect | Preserves ff7fffff | [repeat,1] | [repeat,1],[page,1] | yes |
| G3 clean_control | Preserves a correct −∞ | — | — | no |
| G4 overlap_control | Re-blocks the same ID, −∞ | — | — | no |
| G5 unmask_control | Restores the raw finite value | [page,1] | [page,1] | no |
| G6 own_block_elsewhere | Blocks another ID and carries the defect | [repeat,1] | [repeat,1],[page,1] | yes |

The first execution matched every frozen expectation: 6/6, with r1 fields, echo, v1 conflicts and the "differs" flag all correct. G1 is the minimal form of the disputed row. G2 and G6 show the opposite direction, where v1 over-reports.

## Recomputation of the 32 unchanged inputs

Command, run once from `reconciliation/`: `python -I -B oracle_r1.py --repo <worktree>`. Before computing, `oracle_r1.py` checks three digests:

- the opened `oracle.py`, `74feda7a…fb8d`
- the opened `expected-manifest.json`, `4e7587eb…10d`
- the fixture `manifest.json`, `2c15a26d…0cc0`

| Result | Value |
| --- | --- |
| Rows recomputed | 32 (Q1 12, A1 6, A2 6, C1 8) |
| Unchanged v1 oracle reproduces opened rows | 32/32 byte-identical |
| r1 equals hand-written intent | 32/32 (one intent entry revised, for A2.illegal_repeat) |
| Rows differing from v1 | **1: A2.illegal_repeat, field `conflicts` only** |
| v1 `conflicts` | [["repeat",1],["repeat",2],["page",4]] |
| r1 `conflicts` | [["repeat",1],["repeat",2],["page",2],["page",4]] |
| Unchanged in that row | status M, first ["repeat",1], allowed [1,3,4], winner null, echoed arrays |
| r1 expected manifest | `results/expected-r1-manifest.json`, SHA-256 `d6cc5404c377bb71493985d0d5bb6871ab0492e88c23eb4a49c9ea8be420310d` |
| r1 row A2.illegal_repeat | SHA-256 `edca2a2564c0a5dfa42c733b7580386ce19f8a2f6bb3141a189640b9ba90f6a3` |
| Repeat execution into private scratch | 34 JSON outputs byte-identical (scratch then removed) |

The other 31 r1 rows are byte-identical to the opened v1 rows.

## Change inventory

All changes are under `docs/fixtures/WP-0045/reconciliation/`. No other path changed after /001.

| Commit | Path | Purpose |
| --- | --- | --- |
| `cd8e4796` | `README.md`, `oracle_r1.py` (`75ecbdcc…841b`), `regression.json` (`cfabb59b…c48b`), `regression.py` (`40c7fba1…572a`) | Correction and regression, frozen before execution |
| `fc46492b` | `results/recompute.json` (`bd15a7e3…64be`), `results/regression-results.json` (`8dac1ce6…6c03`), `results/expected-r1-manifest.json`, `results/expected-r1/<ID>.json` ×32 | First-execution outputs |

This report is committed afterward as separate metadata.

## Post-opening limits

- r1 was written after the opening and after the coordinator described the disagreement: the row, the pair and the agreeing status/first. It is **not blind**. It cannot count as independent confirmation of either candidate on this row, and it must not replace the original blind counts. The original A2 count of 5/6 for each route stays the recorded blind result.
- I have not read either candidate's code, outputs or reports. Applying r1 to the candidates' returned rows is the coordinator's and reviewer's step. If a candidate's `A2.illegal_repeat` row is byte-equal to the r1 row above, it matches r1 on that row in a separately labelled post-opening reconciliation figure. I make no claim about the other 31 rows beyond the fact that r1 equals v1 there.
- The defect came from a disclosed "silent-point" choice, I6, that in fact conflicted with explicit wire text. The other interpretation choices, I1–I5 and I7, should get the same source check from the reviewer. For this reconciliation I re-read the wire against I6 only.
- The correction is confined to the A2 interface. It makes no claim about native score tensors, masks or guards.
- I ran no native work, no new blind trial and no new cases outside this regression, and used no device or network.

## Verification

| Check | Result |
| --- | --- |
| Opened oracle, expected manifest and fixture manifest digests, asserted by `oracle_r1.py` at load | Equal. The script runs only if they hold. |
| `git status` after both executions | Only new files under `reconciliation/results/`. No tracked file modified and no `__pycache__` created (`-B` and `dont_write_bytecode`). |
| `python -I -B oracle_r1.py --repo <worktree>` | Exit 0. 32 rows, v1 reproduced 32/32, r1 intent mismatches 0, 1 differing row. |
| `python -I -B regression.py` | Exit 0. 6 cases, 0 failed. |
| Repeat of `oracle_r1.py` into private scratch | Byte-identical (34 JSON outputs) |

Not run: any comparison against candidate outputs, which is outside my role here.

## Handoff

- **Next owner:** eld-rd-reviewer verifies independently: the source reading of W1 and W2, the difference-locus proof, and r1 and the regression in its own scratch. eld-coordinator then records the disposition, with the blind 5/6 A2 and the post-opening r1 reconciliation kept as separate figures.
- **Branch:** `research/wp-0045-fixtures`
- **Deliverables:** `cd8e4796ff89da361e89aed8d96267f213bdcc96` (frozen r1 and regression) and `fc46492bd115a8547b155b0e71c919ff375c7edc` (results)
- **Report:** this file. Its publication SHA follows in the handoff message.
- **Publication receipt:** remote confirmation is pending. The coordinator transports the branch unchanged, and I have not pushed.
