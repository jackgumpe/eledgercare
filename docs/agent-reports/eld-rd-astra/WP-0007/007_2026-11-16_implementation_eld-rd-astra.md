# WP-0007 /007: consolidated CPU parser, accounting and typed-metric response

- Report path: `docs/agent-reports/eld-rd-astra/WP-0007/007_2026-11-16_implementation_eld-rd-astra.md`
- Reservation / authority: [INDEX and correction release](https://github.com/jackgumpe/eledgercare/blob/d106db76de6dc8d9b52770d405ca95300b6dacd6/INDEX.md), exact kickoff `docs/kickoffs/WP-0007-eld-rd-astra-correction.md`; coordinator deliverable `be3de3c1f17d5177cba87f589752c646b37d356c`, /008 publication `d106db76de6dc8d9b52770d405ca95300b6dacd6`.
- Category / author / publisher: implementation; eld-rd-astra, same native `/root/rd_astra`.
- Actual model / effort: inherited dispatched `gpt-6-astra` / `high`; backend checkpoint and backend session UUID not exposed. Earlier WP-0004/0005/0007 authorship remains. No delegated agent or external model invocation.
- Environment: Windows PowerShell, native Codex shell tools; registered CPython 3.12.10, MSC v.1943 AMD64, `C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe` with `-I -B` for captured execution.
- Timestamp: 2026-11-16T04:55:16.996623+00:00
- Repository / branch / worktree: private `jackgumpe/eledgercare`; `research/wp-0007-vanilla-baseline`; `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-baseline-astra`.
- Base: `7abf4c1f6c3e6d8d92b6ddb8e45ec75e8daaf4d2`.
- Authorized coordinator merge: `0b22877ad9f453bb2e642935d2883ad3d32304f1` (normal merge, no source conflict); its imported routing/design/other-author files are inventoried separately below.
- Initial correction freeze: `86c21a7be0177718ddb506c4a8ae3c3f1a51fdea`.
- Final source deliverable: `f807e0ac737df4e9e0aeeb96f716afec57f58ff6`; `qualification/baseline` tree `df44162c62641596032df04bc834754da38a5f7b`.
- Evidence publication: `f186c687d15a3f73841e0fcc1fd225b9ae571096`; same source tree, no post-check scorer changes.
- Previous report: [immutable /002](https://github.com/jackgumpe/eledgercare/blob/7abf4c1f6c3e6d8d92b6ddb8e45ec75e8daaf4d2/docs/agent-reports/eld-rd-astra/WP-0007/002_2026-11-16_implementation_eld-rd-astra.md).
- Reviewed input: [independent complete findings](https://github.com/jackgumpe/eledgercare/blob/c4b0688604caa08a042f9629896b844e7258b50a/docs/reviews/WP-0007/eld-baseline-reviewer/003/findings.md), actual `review_checks.py` and recorded evidence at that revision; no reviewer evidence edited or claimed as author execution.
- Status / next owner: ready-for-review; same independent eld-baseline-reviewer for one /003 reconciliation. No self-acceptance or runtime release.

## Outcome and review response

This is one consolidated response to B0-R1 through B0-R4, plus the coordinator's separately authorized typed-metric scope clarification. Printed field/cell definitions remain unchanged. Strict normalized-value fields/cells are additional labeled metrics, frozen using dev-only schema/printed forms before any held-out access. All 37 applicable CPU tests pass on the final candidate, including targeted malformed/excess/absence/routing cases and dev typed-boundary checks. The dev audit observed 18 admitted paths and no held-out content. This is author verification, not independent reproduction or acceptance.

| Finding / scope | Final behavior and focused evidence |
| --- | --- |
| B0-R1 malformed grammar / uncaught TypeError | `native.TableParser` enforces one closed, nested table root and explicit attributes. Valueless/duplicate/unsupported attributes, mismatched/missing closes, structural self-closing tags and unsupported markup fail. `parse_native` retains malformed native body and a table diagnostic; `baseline.prediction` catches TypeError at its boundary. Parse-invalid documents receive no printed or typed exact credit. `test_malformed_closed_grammar_retained_without_credit`, boundary test and mocked two-document `score_run` test retain both denominators and continue after the malformed first document. |
| B0-R2 dropped short/spanning rows | Every non-header physical row under a recognized header occupies its encounter ordinal. Short rows map available cells and retain missing slots. Spanning rows preserve physical cells but map no columns; diagnostics retain both. Physical excess counts and unmapped physical row/cell coverage are explicit; no colspan-expanded imaginary cells or factual-hallucination assertion. Focused tests cover trailing excess and expected-row slots. |
| B0-R3 absence duplicates | Only the first candidate consumes an expected-absence slot. Every subsequent candidate, including empty ones, remains unmatched and contributes to `surplus_candidates`; any nonempty occurrence independently causes the per-absence violation. Three repeated-empty/nonempty/mixed cases verify both counters. |
| B0-R4 reviewer identity | `release.REVIEW_PATH` binds exactly `docs/agent-reports/eld-baseline-reviewer/WP-0007/003_2026-11-16_review_eld-baseline-reviewer.md`, checked in pure release validation before runtime side effects. Old owner, /005 and suffix variants reject. This repairs coordinator routing drift after original freeze; /002 remains unchanged. |
| Typed metric scope clarification | `typed_values.convert` accepts only raw text, declared type and explicit slot; it cannot accept an expected answer. Comparison happens afterward. Separate `normalized_fields`/`normalized_cells` retain the printed denominators and completed/parse-valid credit gate, conversion reasons and raw values. Wrong digits/signs/identifier zeros, invalid grouping, ambiguous units, unsupported types and precision changes do not receive repair credit. This addition is not attributed retroactively as an original author defect. |

The full bounded grammar is in the frozen [README](https://github.com/jackgumpe/eledgercare/blob/f807e0ac737df4e9e0aeeb96f716afec57f58ff6/qualification/baseline/README.md) and `typed_values.py`: exact text/identifier strings, valid ASCII ISO dates, `[X]`/`[ ]`, strict USD/decimal/percent lexical forms and exact Decimal canonicalization. Amounts/quantities require an exact two-place value; percentages divide by 100 into an exact four-place fraction. Additional fractional zeros are allowed; value-changing rounding, exponent syntax, invalid grouping, negative zero and unsupported structures fail. Limits are 128 characters for typed scalars, at most 24 integer digits and six fractional digits, precision 40.

The dev `qty_unit` slot requires one space and BX/EA/HR/KT/PR. Its normalized schema target is numeric only: a wrong but supported unit may still get normalized numeric credit while printed equality fails. The unit stays visible in diagnostics. Text/addresses are never joined or reordered; identifiers never lose leading zeros. No new table-header repair or expected-value-driven mapping was introduced. Raw lexical errors, mapping failures, excess/duplicates and absence remain separately visible.

Unchanged sentinel selection at `a8fb2137e559bfeb453bc184c78fab4989c99ecf`: SYN-WO-02-v3-hybrid-note, SYN-INV-03-v1-raster300, SYN-MP-02-v0-clean. Only public metadata was used. Actual model/test execution still needs independent /003 acceptance and a coordinator lease binding the clean executing HEAD, reviewed source tree, review report and fixed sentinels.

## Verification and retained failure

Exact subprocess argv, interpreter, timestamps, exit codes and artifact size/SHA-256 inventories are in [final checks.json](https://github.com/jackgumpe/eledgercare/blob/f186c687d15a3f73841e0fcc1fd225b9ae571096/docs/evidence/WP-0007/eld-rd-astra/f807e0ac/checks.json). Every shell command used the owned worktree explicitly.

| Executed check | Result |
| --- | --- |
| `python -I -B qualification/baseline/run_checks.py` at initial freeze 86c21a7be0177718ddb506c4a8ae3c3f1a51fdea | Exit 1; 36/37 tests passed, existing NFC expected literal failed after my editing helper decoded that preexisting non-ASCII literal with the Windows default encoding. Scorer behavior was not the failure. Full initial evidence is retained in `86c21a7b/`. |
| Literal correction and new freeze | Changed only that test literal to explicit `\u00e9`; committed final candidate `f807e0ac737df4e9e0aeeb96f716afec57f58ff6`. No failed evidence was replaced. |
| Same `run_checks.py` at final freeze | Exit 0. `python.exe -I -B qualification/baseline/tests/test_baseline.py -v`: 37/37 pass. Includes owned Windows job-child exit, pre-read holdout refusal, release/resource guards, all original parser/scorer cases and 12 added correction test methods. |
| `python.exe -I -B qualification/baseline/baseline.py dev-check --output docs/evidence/WP-0007/eld-rd-astra/f807e0ac/dev` and captured audit helper | Both exit 0; 13 dev reference/expected records, two retained Q0 outputs; 18 distinct dev content paths (13 expected, four clean-parent PDFs, one hybrid source), zero unexpected/held-out paths. No model imports or inference are part of these commands. |
| Dev typed grammar audit | All 949 dev expected items convert from their printed form to their declared normalized string; all 949 appended-`?` mutations fail equality. Counts: identifiers 289, text 198, dates 18, booleans 24, decimals 84, USD 264, percentages 72. This tests reference grammar coverage, not model accuracy. |
| `git diff --check 0b22877ad9f453bb2e642935d2883ad3d32304f1 f807e0ac737df4e9e0aeeb96f716afec57f58ff6` | Exit 0. Seven owned source paths changed. |
| Git-object / hash reconciliation | All 20 protected tree/blob identities equal base; source tree unchanged in evidence commit. Both check manifests' 23 listed artifacts match committed size/hash, all 49 committed evidence files match on-disk bytes, no mismatch. See `f807e0ac/reconciliation.json`. |

Preparation inspected only dev expected values to freeze type/unit grammar. The actual audit covers executed dev-check file opens; it is not a claim to an independent whole-process security monitor. Author checks do not perform or substitute for the reviewer's denied/held work. No packages, services, model imports, GPU operations, Q0 changes or held-out PDF/source/expected reads occurred. Both separate author and reviewer B0 runtime roots remain absent. External model files were not reopened/rehashed; their accepted pinned manifest and Q0 tree remain identical.

## Retrospective Q0 comparison

The same F01/F07 warm1 raw bytes from accepted Q0 run 20261115T202627Z-eb5bf7da were rescored without any model call. Compared with original /002 evidence, each complete printed fields object, printed cells object, source identity and raw token-error object is identical.

| Historical dev output | Printed fields | Printed cells | Typed fields | Typed cells |
| --- | ---: | ---: | ---: | ---: |
| F01 | 15/15 | 18/19 | 15/15 | 18/19 |
| F07 | 13/15 | 72/180 | 13/15 | 72/180 |

F07 still maps only 72/180 expected cells because later headers are not exact dev headers; 108 missing typed cells remain in denominator, 12 unsupported/missing rows and 50 unclassified content records remain visible. New physical-unmapped accounting reports 25 rows /149 cells across all its unclassified table content, including headers and schema-unmatched content; these counts are not asserted inventions or character-reading errors. Its two field normalized mismatches remain mismatches. F01 retains one cell mismatch. The raw token errors remain 0.2025862069 and 0.1775836972 respectively, including native-versus-reference ordering differences. These are retrospective diagnostics, not the new 26-document B0 result.

## Complete path inventory and attribution

The approved normal coordinator merge imported these 17 paths. They retain coordinator/other-author attribution; this author did not implement their product/design content.

| Git action | Imported path |
| --- | --- |
| M | `AGENTS.md` |
| M | `CURRENT.md` |
| M | `INDEX.md` |
| A | `docs/agent-reports/eld-coordinator/WP-0007/008_2026-11-16_design_eld-coordinator.md` |
| A | `docs/agent-reports/eld-next-reviewer/WP-0006/002_2026-11-16_review_eld-next-reviewer.md` |
| A | `docs/coordination/WP-0006/design-acceptance.md` |
| A | `docs/coordination/WP-0006/design-publication-audit.json` |
| A | `docs/coordination/WP-0006/dispatch.json` |
| A | `docs/coordination/WP-0007/cpu-publication-audit.json` |
| A | `docs/coordination/WP-0007/scoring-disposition.md` |
| A | `docs/implementation/WP-0006/plan.md` |
| A | `docs/kickoffs/WP-0006-eld-f2-implementation.md` |
| A | `docs/kickoffs/WP-0007-eld-baseline-reviewer.md` |
| A | `docs/kickoffs/WP-0007-eld-rd-astra-correction.md` |
| A | `docs/reviews/WP-0006/eld-next-reviewer/design/README.md` |
| A | `docs/reviews/WP-0006/eld-next-reviewer/design/verification-receipt.json` |
| A | `docs/reviews/WP-0006/eld-next-reviewer/design/verify_design_contracts.py` |

The author's source correction contains these seven paths. `native.py`, `score.py`, `release.py` and `baseline.py` implement the findings; `typed_values.py` supplies candidate-only conversion; README and tests freeze the reviewed rules and their checks.

| Git action | Authored source path |
| --- | --- |
| M | `qualification/baseline/README.md` |
| M | `qualification/baseline/baseline.py` |
| M | `qualification/baseline/native.py` |
| M | `qualification/baseline/release.py` |
| M | `qualification/baseline/score.py` |
| M | `qualification/baseline/tests/test_baseline.py` |
| A | `qualification/baseline/typed_values.py` |

The separate evidence commit adds these 49 paths. Initial failure evidence and final passing evidence are both retained; generated audit scripts are captured products of the already frozen `run_checks.py`, not independently authored reviewer tools.

| Git action | Evidence path |
| --- | --- |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/01.stderr.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/01.stdout.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/02.stderr.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/02.stdout.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/03.audit.stderr.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/03.audit.stdout.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/audit-dev/F01.prediction.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/audit-dev/F01.reference.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/audit-dev/F01.score.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/audit-dev/F07.prediction.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/audit-dev/F07.reference.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/audit-dev/F07.score.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/audit-dev/summary.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/audit-dev/typed-dev-coverage.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/audit_dev_reads.py` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/checks.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/dev/F01.prediction.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/dev/F01.reference.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/dev/F01.score.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/dev/F07.prediction.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/dev/F07.reference.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/dev/F07.score.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/dev/summary.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/86c21a7b/dev/typed-dev-coverage.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/01.stderr.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/01.stdout.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/02.stderr.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/02.stdout.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/03.audit.stderr.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/03.audit.stdout.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/audit-dev/F01.prediction.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/audit-dev/F01.reference.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/audit-dev/F01.score.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/audit-dev/F07.prediction.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/audit-dev/F07.reference.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/audit-dev/F07.score.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/audit-dev/summary.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/audit-dev/typed-dev-coverage.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/audit_dev_reads.py` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/checks.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/dev/F01.prediction.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/dev/F01.reference.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/dev/F01.score.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/dev/F07.prediction.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/dev/F07.reference.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/dev/F07.score.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/dev/summary.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/dev/typed-dev-coverage.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/f807e0ac/reconciliation.json` |

The only later authored path is this canonical /007 report. Shared INDEX/CURRENT, other authors' reports/evidence, accepted evaluation/Q0/research and product trees received no author modifications; imported coordinator routing changes are separately listed above. `protocol.json`, `mapping.json`, runtime/reference/job helpers and original /002 are exact protected objects. No historical report was rewritten.

## Handoff and limits

Review the [source response diff](https://github.com/jackgumpe/eledgercare/compare/0b22877ad9f453bb2e642935d2883ad3d32304f1...f807e0ac737df4e9e0aeeb96f716afec57f58ff6) and evidence commit `f186c687d15a3f73841e0fcc1fd225b9ae571096`. Same independent eld-baseline-reviewer should reconcile R1-R4 and the scoped typed rules once against this exact source, preserving its earlier findings and sentinel choice. Original /002's historical reviewer routing is superseded here without rewriting it.

No new baseline inference, held-out accuracy measurement, PDFium/model execution, lease, GPU host verification or independent acceptance is claimed. The unchanged finite CUDA runner remains unexecuted under B0. Offline `score-run` still requires an exact valid release/HEAD, as disclosed by the reviewer; this response does not expand post-expiry access. Typed unsupported cases stay counted and may constrain later descriptive accuracy; no holdout-based tuning is authorized by this report.

Normal owned-branch push and exact-origin verification follow this report commit. Publication confirmation and the report's own full SHA are supplied separately to the coordinator; this immutable report does not claim its own commit SHA.
