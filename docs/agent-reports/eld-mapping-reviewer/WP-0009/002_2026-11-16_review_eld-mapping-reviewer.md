# WP-0009 /002: Independent diagnosis and protocol acceptance

- Report path: `docs/agent-reports/eld-mapping-reviewer/WP-0009/002_2026-11-16_review_eld-mapping-reviewer.md`
- Sequence reservation: [exact authority INDEX](https://github.com/jackgumpe/eledgercare/blob/a5cca9f434b494368af7cd28a2958feaa0702b69/INDEX.md), WP-0009 /002.
- Category: review.
- Author / agent ID: **eld-mapping-reviewer**, native session `/root/mapping_reviewer`; independent of all reviewed diagnosis, mapper, scorer and corpus authors.
- Actual model / effort: native Codex; backend model/checkpoint and actual effort not exposed. Fresh xhigh explicitly requested by dispatch; no stronger identity claim.
- Execution environment: Windows PowerShell, host CPython 3.12.10, isolated `-I -B`; unchanged pure baseline modules, CPU only.
- Published by: eld-mapping-reviewer on owned branch.
- Timestamp: 2026-11-16T19:40:24.586057+00:00; actual review start 2026-11-16T19:35:45.8867214Z.
- Repository / branch / worktree: private `jackgumpe/eledgercare`; `review/wp-0009-mapping`; `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-mapping-reviewer`.
- Initial base: **5e1241d6d365d664f12619d415f48ec3d3b7ddca**; fast-forward authority **a5cca9f434b494368af7cd28a2958feaa0702b69**.
- Review work base after exact input merges: **8549ecd92eae045b15cd04a068cb7cb54ed9716c**; diagnosis merge **a335dcf09e7fbcc06427ad9d36a57272bbf29fba**, then public reservation merge.
- Frozen review helper: **b0255e08c675ca5fbd40b930bfb306c3e4496aba**.
- Deliverable revision: **f248c401c2e5e39da13af84e62001d8290325a46**.
- Evidence inventory revision: **463049f157545bcd17c3caaa4b712ec1be6fe37f**.
- Previous report: none by this reviewer in WP-0009.
- Reviewed report: [author /001](../../eld-mapping-author/WP-0009/001_2026-11-16_research_eld-mapping-author.md), publication **f6c7c7e8922b73ac58cdeebc198ed098d88a9c80**; deliverable **cffa140058cb4fac7eec59a3eb60c11074678af6**, helper **d4503ea6f8f384f29de8c84de2c83f451c05e817**, evidence **bb84d5147ade525932aa3b2e024562dfb6bbba19**.
- Status: **accepted**, independent diagnosis/protocol review only.
- Next owner: eld-coordinator for one-change selection; this reviewer continues separate sealed corpus admission /004.

## Summary

Accept the diagnosis and recommend selecting exactly the guarded immediate-right-neighbor field association. Independently reproduced all 26 original full scores and split/family summaries plus separate recovery, verified all 27 cited associations and 795 native-cell evidence locations, and retained the explicit unknowns and overlapping attribution. No blocking protocol issue. This is neither implementation acceptance nor a measured gain.

## Objective and acceptance criteria

Under the [exact review release](../../../kickoffs/WP-0009-eld-mapping-reviewer-diagnosis-admission.md), independently inspect underlying source/raw/expected evidence, preserve original primary denominators and supplemental separation, challenge causal claims and guard limitations, and recommend one bounded treatment without implementing it. Criteria met. Corpus admission, selected source acceptance, unsealing and runtime release remain separate gates.

## Change inventory

All six deliverable additions are under `docs/reviews/WP-0009/eld-mapping-reviewer/002/`: `review_checks.py`, `PROCEDURE.md`, `results.json`, `attempt-1.json`, `attempt-1.log`, and `disposition.md`. [Complete inventory](../../../reviews/WP-0009/eld-mapping-reviewer/002/inventory.json) records every path, Git blob, normalized publication bytes/SHA256 and worktree hash. Metadata afterward: that inventory and this canonical report. No existing path modified or deleted; 13 protected tree/file identities match the review-input base, including all prior reports, baseline/corpus/product and shared routing.

External effects: owned normal Git commits/push; ignored `.scratch/wp0009-reviewer/diagnosis/` contains three exact author-helper reproduction outputs, hashed in results.json. No service, model, dependency, GPU, database or runtime-directory change.

## Decisions and rationale

All 27 opportunities have exact known labels, correct immediate adjacent values and unique label occurrences in their native blocks, across nine documents/five families. All satisfy the proposed basic guards. Existing wrong below-row choices are directly reproducible. The reviewed diagnosis labels these as opportunities, not promised improvements or recognition accuracy.

The finite old-data inspection finds 30 label-like neighbors, 17 absent neighbors and one overlapping span context. No duplicate-label or empty-right-neighbor case was present among exact known table labels. Therefore later implementation/source acceptance must include explicit crafted positive/negative cases for duplicates, ambiguous neighbors, empty values, spans, all-label/column-header rows and label-containing values. It must define ambiguity scope and prevent duplicate emission for one label occurrence. These are source acceptance criteria already required by /001, not evidence of implemented protections.

The 361 field and 1,801 cell denominators, 1,245 printed-or-typed failed slots, 150 unadjudicated slots and 17 unverified absences reproduce. Nonexclusive category counts are retained as 61 recognition/omission, 12 structure, 873 mapping, 16 typed/scoring, 195 runtime-unavailable and 150 unknown. They must not be summed as a causal partition. Of 795 explicitly located native cell observations, 784 equal expected text and 11 differ. The 48 omitted deployment cells cannot be rescued by matching serials in retrieval records. Unknown/unsupported mappings and zero detected inventions do not imply correct reading or complete hallucination detection.

Original failed document retains 15 fields/180 cells and no retained raw; the empty prediction is accounting only. Its separate completed recovery remains parse-ineligible and excluded from primary. Typed-unit and address normalization weaknesses remain outside the selected association change. Old holdout is exposed regression data, and future mapper effects must remain separate from model recognition claims.

## Verification

| Check / exact operation | Revision / environment | Actual result | Evidence |
| --- | --- | --- | --- |
| Startup status/branch/HEAD and authorized FF/input merges | Exact initial/authority/input SHAs above | Clean owned worktree and exact inputs; merge identities retained | [Procedure](../../../reviews/WP-0009/eld-mapping-reviewer/002/PROCEDURE.md) |
| Syntax `ast.parse` before helper freeze | Host Python 3.12.10 | PASS | Frozen helper |
| `python -I -B docs/reviews/WP-0009/eld-mapping-reviewer/002/review_checks.py` | Clean frozen b0255e08c675ca5fbd40b930bfb306c3e4496aba | Exit0; 26 primary + one supplemental score objects exactly equal; full summary equality; all opportunity and denominator checks PASS | [Attempt](../../../reviews/WP-0009/eld-mapping-reviewer/002/attempt-1.json), [log](../../../reviews/WP-0009/eld-mapping-reviewer/002/attempt-1.log), [results](../../../reviews/WP-0009/eld-mapping-reviewer/002/results.json) |
| Exact author helper invoked from frozen review wrapper, only output-containment root redirected | Same frozen review HEAD; author source unchanged | Ledger differs only in executing HEAD; all remaining content and 108-input inventory equal | Results and ignored reproduction hashes |
| Read actual `native.py`, `score.py`, `corpus.py`, diagnosis source/method/raw evidence | Baseline **522f15f1f6e399c36b9c6c107fc08f51862f1fc1**, unchanged tree `deae8e826f4770e880374c68e6a56c8c65b6f8a3` | Association, eligibility, reference, aggregation and limits substantiated | [Disposition](../../../reviews/WP-0009/eld-mapping-reviewer/002/disposition.md) |
| Post-deliverable exact diff and protected identities | f248c401c2e5e39da13af84e62001d8290325a46 | Six additions only; 13 protected identities equal | Inventory |
| `git diff --cached --check` | Helper/deliverable commits | PASS | Git commits |

No decisive failure or rerun. Exploratory reads requested nonexistent `qualification/mapping_v1` and `map_native.py`; resulting missing-path diagnostics were discovery only. No treatment tests/deltas, model/GPU runs, services, transformed old-PDF visual re-adjudication or comprehensive hallucination audit were executed; those were outside this diagnosis review. No fresh sealed content was accessed before /002 disposition.

## Review map

[Pinned review deliverable diff](https://github.com/jackgumpe/eledgercare/compare/8549ecd92eae045b15cd04a068cb7cb54ed9716c...f248c401c2e5e39da13af84e62001d8290325a46); exact author source/evidence and helper identities above. Read `review_checks.py:main`, all raw-located opportunities and negative contexts in results.json, and the acceptance boundary in disposition.md. This is independent executed review, not author assertion reuse.

## Risks, disagreements, and unfinished work

No unresolved blocking disagreement. The 27 opportunities are correlated exposed-data observations. Later source review must verify no regression to previously correct fields/cells and unchanged table/absence/typed/eligibility behavior; any score loss must be reported separately. Empty/duplicate/ambiguous protection is unproven until implemented and tested. No reviewed source was authored by this reviewer. Fresh admission and all later gates remain unfinished in their own reservations.

## Handoff

Root may select the single bounded association change based on this acceptance. Bind deliverable f248c401c2e5e39da13af84e62001d8290325a46 and inventory 463049f157545bcd17c3caaa4b712ec1be6fe37f. Owned branch `review/wp-0009-mapping`; canonical /002 path above. Report publication SHA and exact-origin verification follow in the handoff message; no self-publication SHA is claimed. Only root updates routing. Independent /004 proceeds separately; no user permission is pending.
