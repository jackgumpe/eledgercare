# WP-0007 independent initial findings checkpoint

Status: **changes requested; canonical /003 held for one bounded author response and independent reconciliation**. This is an owned evidence checkpoint, not the canonical acceptance report and not authorization for test-content or model access.

- Reviewer: `eld-baseline-reviewer`, `/root/baseline_reviewer`; actual backend model/effort not exposed.
- Independence: no authorship of reviewed B0 design, admitted corpus, scorer, parser, mapping or runner; no source fixes made by this reviewer.
- Initial clean reviewer base/routing: `8228bfbebddc132ba5d26b98300f3dc5dda99b5a`; original packet base `8e80a42c29c0fc27a4af6348cfb1ec22cab3764d`.
- B0 design candidate: `efa9cb986711f82a886f917e68142a7a59319bba`; coordinator /001 publication `c08d50e204395e60a88ce25f70e25bd29b97b8c6`.
- Exact author source: `a998b765f7734453d27ec4a189a2156778f0913d`; evidence `a853ad80a3cb92412c3d4ac0962e6c8e8b252310`; /002 publication `7abf4c1f6c3e6d8d92b6ddb8e45ec75e8daaf4d2`. Exact origin author ref independently verified.
- Normal merge into reviewer branch: `0b93a5cecb01337ec2c76974214f13a0c2a3caf5`; baseline/Q0/corpus trees unchanged from the author candidate.
- Independent probe freeze/execution: `97249fa673319e9466f14b3ebe3abb5de0d03aa9`; reviewer-only probe correction/targeted rerun `ef5e68c593b3e4ac9601d66eab87838b468621c4`.
- Sentinels fixed before results at `a8fb2137e559bfeb453bc184c78fab4989c99ecf`: `SYN-WO-02-v3-hybrid-note`, `SYN-INV-03-v1-raster300`, `SYN-MP-02-v0-clean`. Selection used public metadata only.

## Consolidated corrective findings

### B0-R1 — Malformed HTML can abort scoring, or receive parse-valid exact credit

`qualification/baseline/native.py:34` converts a valueless `colspan`/`rowspan` attribute with `int(None)`. `baseline.prediction` catches `ParseError` and `ValueError`, but the resulting **TypeError escapes**. A single malformed model table can therefore stop `score_run` rather than preserve that document and all following planned denominators. Independently reproduced with `<td colspan>A</td>`; no source/truth input is needed.

The same parser tracks rows/cells but no table/section stack. `<table>` with complete rows but no `</table>` produces no parse errors and credits both expected cells. Unsupported attributes on `table` similarly pass. This contradicts the candidate README's explicit closed grammar and invalidation policy. These are correctness/measurement defects; no code execution or unsafe `eval` was observed.

Required outcome: make the declared bounded grammar real, convert malformed attribute/structure failures into retained parse diagnostics, and preserve per-document failure accounting without granting exact credit. Include missing/mismatched closes and valueless/unsupported attributes in the author's regression evidence. Do not recover values from expected answers.

### B0-R2 — Short and spanning rows vanish from excess and unmapped accounting

After a recognized table header, `native.py:113` accepts only rows at least as wide as the header with all colspans equal to one. The fallthrough at line 120 retains an unmapped row **only when there is no active recognized table**. Consequently a trailing one-cell `EXTRA` row or a `colspan="2"` `EXTRA` row after a valid two-column row leaves `extra_rows=0`, `extra_cells=0`, and `unmapped=[]`, while the valid cells get full credit. The full parsed block/text still contains the content, so it has not been erased from raw evidence, but structured invention/mapping accounting silently omits it.

Required outcome: retain every non-header physical row/cell in mapped or explicitly unmapped accounting, including short/spanning rows within a recognized table. Expose coverage and schema-relative excess/duplicate counts without calling legitimate furniture a factual hallucination. Keep expected rows/cells in denominators.

### B0-R3 — Duplicate expected-absence candidates are consumed without an excess count

`score.py:36` marks every candidate for an expected-absence field as used. Two identical `Optional: EXTRA` candidates yield one absence violation (appropriate per-absence denominator) but `fields.unmatched_candidates=0`. Their two values remain visible in detail, yet there is no duplicate/excess count despite the explicit repeated-output requirement.

Required outcome: retain the per-absence violation metric and also count surplus candidate occurrences. Empty duplicate candidates must not disappear either. Existing ordinary-field duplicate accounting passed.

### B0-R4 — Runtime review binding still requires the superseded reviewer identity

`release.py:47` requires `docs/agent-reports/eld-next-reviewer/WP-0007/003_`. The coordinator reassigned the unpublished review slots after the source freeze; this is attributable routing drift, not author concealment. A pure release-reader probe reproduces `Wrong independent review report` for the actual reserved `eld-baseline-reviewer` canonical path.

Required outcome: bind the actual canonical reviewer path/identity under the coordinator's new routing. This belongs in the same bounded response, with no separate review cycle. Old published /002 prose stays immutable; the correction report supplies current routing.

## Contract interpretation and review limits

**Printed versus normalized money.** The implementation clearly labels exact printed-string metrics and retains normalized field values diagnostically. It does not claim normalized currency exactness. This is a conservative, defensible B0 measurement under the new contract's explicit NFC/line-ending/outer-whitespace-only normalization rule. The earlier exact normalized two-decimal currency requirement appears under `research/carbon/reconciliation/02-ranked-experiment-backlog.md:27`, the **Common Paired Comparison Protocol (E1–E3)**. B0 expressly is a new descriptive baseline and cannot establish compliance with that future comparison protocol. I do not treat absence of an additional semantic-money metric as a demonstrated B0 scoring bug. The author/coordinator should reaffirm this scope in the one response/disposition: literal printed metrics are not interchangeable with E1–E3 normalized currency metrics, and those future metrics remain unimplemented. No expected-driven digit repair or total inference is acceptable.

**Reference construction.** Source inspection confirms prediction extraction receives raw-derived structures and frozen dev label/header rules, while `corpus.reference_for` is separate. It verifies clean-parent hashes and constructs a declared spatial row-major reference from all supported writer text operators, then adds the hybrid source label/body. Independent PDFium text extraction matched the non-whitespace character multiset on each of all six clean dev pages; the declared hybrid lines also matched. This verifies per-page inclusion independently, not a unique human reading order. Native block order and deterministic SequenceMatcher alignment may penalize spatial reading-order differences; this is explicitly disclosed and is not minimum-Levenshtein WER. No holdout reference was inspected.

**Runtime source and limits.** The finite runner reuses accepted Q0 observer/call/renderer/model/lock primitives without editing them; source inspection found no model-setting substitution. Source-tree/protocol/mapping/lock identities, a clean executing HEAD, exact reviewer report and coordinator release gate execution. Worker joins the named kill-on-close job before model imports. The tests below exercise CPU supervisor/lifetime behavior only. Model load, actual new baseline runtime, all 26-document results and final /005 reproduction remain unreleased and untested. `score-run` currently shares the live runtime release/HEAD checks; later offline reproduction must be explicitly bound by the coordinator to exact accepted scorer/raw evidence, and must not be described as automatically enabled after lease expiry.

## Executed verification and preserved failures

| Check | Actual outcome | Evidence |
| --- | --- | --- |
| Registered CPython 3.12.10 `-I -B .../review_checks.py`, frozen at 97249fa6 | 13 independent probes: seven substantive failing cases grouped into B0-R1–R4; five passed; one reviewer harness error, corrected below | `evidence/97249fa6-043410/results.json` |
| Rerun author test suite in reviewer worktree | 25/25 pass, including ordinary duplicates, failed exact denominators, strict labels, holdout gate, guard checks and normal job close | `evidence/97249fa6-043410/author-tests.stderr.txt` |
| Independent dev reproduction with pre-open allowlist audit | All seven generated dev prediction/reference/score/summary files byte-identical to author evidence; 18 allowed synthetic paths; no held-out content/model modules | `results.json`; actual generated copies in `retained-scratch/dev/` |
| Existing pinned Q0 venv, CPU PDFium text extraction only | Four clean dev documents/six pages have exact non-whitespace character inclusion; hybrid declared label/body preserved; no torch/transformers import | `pdfium-reference.stdout.txt` |
| Abrupt owned supervisor termination, actual pinned venv child | Distinct launcher PID 27972 and actual worker PID 16364 both observed exited via already-open OS process handles; unrelated owned sleeping sentinel survived | `results.json:abrupt_supervisor_lifetime`; actual helper source/output in `retained-scratch/lifetime/` |
| Real supervisor timeout with a sleeping worker and mocked release/observer boundary in ignored scratch | First attempt had reviewer-supplied `None` release-path argument, so Popen refused before a child existed. This is a reviewer probe defect, not an author finding. Source/probe/output preserved | Initial `results.json` and `retained-scratch/supervisor-root/` |
| Targeted corrected supervisor probe at ef5e68c5 | Actual PHASE_TIMEOUT; active warm-up failed, remaining 14 planned calls `not_run_after_failure`; actual child launcher exit observed. Production `score_run` with CPU release stub preserves all 13 measured dev document denominators and matches independent direct scoring | `evidence/ef5e68c5-043506/supervisor-recheck.json`; exact generated run/score/helper files retained |
| Source preservation / release refusal | Baseline source tree unchanged; no-authority refused before runtime imports; holdout PDF/expected/reference gates refused before content reader | `results.json`, Git tree comparison |

The timeout test intentionally substitutes a sleeping CPU helper and a synthetic release reader at the orchestration boundary. It creates state only under this worktree's ignored `.scratch/wp0007-review-003/`; it is not a model run, GPU lease or actual coordinator release. GPU observers were stubbed rather than invoked. Neither real baseline runtime root exists. No global packages, configuration, model files or other owners' processes were changed.

## Handoff

The author owns all B0-R1–R4 source corrections and its new reserved response/report; root owns routing and any B0 scope clarification. This reviewer will inspect the exact corrected source/evidence publication and execute relevant independent checks, then publish canonical /003 if the corrected measurement is trustworthy. No test-content or model access should be released before that disposition. The sentinel declaration remains fixed. Publish this checkpoint and its exact evidence normally on `review/wp-0007-baseline`; final canonical /003 remains pending the bounded author response.
