# WP-0007 /003: Independent B0 design, scorer and finite-runner source acceptance

- Report path: `docs/agent-reports/eld-baseline-reviewer/WP-0007/003_2026-11-16_review_eld-baseline-reviewer.md`
- Sequence reservation: `8228bfbebddc132ba5d26b98300f3dc5dda99b5a:INDEX.md`, exact `docs/kickoffs/WP-0007-eld-baseline-reviewer.md`; same /003 reservation retained through coordinator /008.
- Category: review
- Author / publisher: `eld-baseline-reviewer`, native `/root/baseline_reviewer`.
- Actual model / effort: not exposed in this reviewer context.
- Execution environment: native Codex tools, Windows PowerShell, registered CPython 3.12.10 x64 with `-I -B`; read-only existing Q0 venv for CPU PDFium/reference and sleeping-child tests only.
- Timestamp: 2026-11-16T05:05:18Z.
- Repository / branch: private `jackgumpe/eledgercare`; `review/wp-0007-baseline`.
- Owned worktree: `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-baseline-reviewer`.
- Initial clean review base: `8228bfbebddc132ba5d26b98300f3dc5dda99b5a`; original packet base `8e80a42c29c0fc27a4af6348cfb1ec22cab3764d`.
- Accepted source deliverable: `f807e0ac737df4e9e0aeeb96f716afec57f58ff6`; `qualification/baseline` tree `df44162c62641596032df04bc834754da38a5f7b`.
- Reviewed author publication/evidence: /007 `e22c6730d19a6d616f0e7afb00b9416635799c16` / `f186c687d15a3f73841e0fcc1fd225b9ae571096`.
- Reviewed coordinator designs: initial B0 `efa9cb986711f82a886f917e68142a7a59319bba`, initial /001 `c08d50e204395e60a88ce25f70e25bd29b97b8c6`; typed clarification deliverable `be3de3c1f17d5177cba87f589752c646b37d356c`, /008 publication `d106db76de6dc8d9b52770d405ca95300b6dacd6`.
- Reviewer check freeze: `8e227abce27cd39087b11bf5285b230d3e684fb5`; passing reconciliation evidence `517018a8c98af8ca893481ddf87181444c99948b`; inventory audit metadata `6d94801c3f6605c4892f95bc616f8624203fc0eb`.
- Previous report: no earlier canonical reviewer report in WP-0007. Published initial findings/evidence `c4b0688604caa08a042f9629896b844e7258b50a` remain immutable.
- Status: **accepted — bounded CPU source/design freeze; actual B0 execution and final results remain pending**.
- Next owner: eld-coordinator for exact staged runtime/test-content releases, then eld-rd-astra /004 and this independent reviewer /005 under separate leases.

## Summary and independence

Accept the corrected parser, mapper, scorer, typed conversion rules, reference construction, protocol and finite-runner source at the exact revision above, together with the coordinator's /008 clarification. The single author response resolves all four independently reproduced initial findings. All 13 original independent probes and eight new typed/denominator probe groups pass. The author's 37-test suite passes independently, all eight regenerated dev artifacts are byte-identical to /007, and no substantive source/design issue remains after this one reconciliation.

I authored none of the reviewed design, source, model configuration, admitted corpus or expected answers. I made no source fixes. The initial source /002 was normally merged at `0b93a5cecb01337ec2c76974214f13a0c2a3caf5`; the exact correction /007 was normally merged at `7efbc442dd9f87a729c63470180e088c1bfbc9d0`. Imported files retain their original author attribution. Carbon's independently published design dossier at `e2452e1ab3d8937868c07ffb30ce430715b5be78` was secondary attributable input; my verdict follows actual source inspection and executed checks.

No held-out PDF, source-record or expected-answer content was read. No model/tokenizer import, inference, GPU observation/lease, external baseline runtime-root creation, package installation or product modification occurred. Public manifest metadata alone determined the fixed sentinels before any new B0 measured result.

## Objective and criteria

The gate is trustworthy, reproducible measurement, independent of how well the model scores. Prediction extraction must not use expected answers to find or repair values; printed and typed metrics must preserve missing/failed/unsupported denominators and expose extras and mapping failures. Full-text reference construction must be explicit despite the corpus lacking a standalone transcript. The fixed 26-document protocol must retain warm-ups, ordering, guards, resource identities and later independent reproduction without releasing model or held-out execution through this report alone.

## One response and reconciliation

The [initial findings](../../../reviews/WP-0007/eld-baseline-reviewer/003/findings.md) preserve the original failing evidence on `a998b765f7734453d27ec4a189a2156778f0913d`. The [single reconciliation](../../../reviews/WP-0007/eld-baseline-reviewer/003/reconciliation.md) records the corrected disposition.

| Finding | Independent disposition on f807e0ac |
| --- | --- |
| B0-R1: malformed HTML abort or incorrect parse-valid credit | Resolved. Valueless/unsupported attributes and missing/mismatched structural closes produce retained diagnostics; malformed documents receive no printed or typed exact credit. A malformed first document no longer aborts later valid/missing document scoring. |
| B0-R2: dropped short/spanning rows | Resolved. Physical rows keep encounter ordinals; short rows preserve available cells and missing slots; spanning rows preserve physical content without inventing expanded cells. Excess and mapping-coverage counts retain the previously dropped cases. |
| B0-R3: absent-field duplicate accounting | Resolved. Surplus candidates, including empty candidates, remain counted separately from the per-absence violation. Three empty occurrences produce two surplus candidates without fabricating a violation. |
| B0-R4: superseded reviewer path | Resolved. The actual exact canonical `eld-baseline-reviewer` /003 path validates; old owner, wrong sequence and suffix variants refuse. This corrects routing drift after the initial source freeze. |
| Coordinator /008 typed-metric clarification | Independently accepted as implemented. Separate normalized fields/cells retain the printed expected-item denominators. Candidate conversion precedes target comparison and uses strict dev-frozen type grammars with exact arithmetic. |

My initial printed-only interpretation was defensible under the initial lexical-normalization wording. The coordinator selected both printed and typed metrics before test access, reconciling that interpretation with Carbon's PBIC-01. This is a scope clarification; it is not a retroactive accusation that the author concealed its initial metrics. Original reports and findings remain unchanged.

## Source assessment and limits

`native.py` receives raw-derived structures and frozen dev label/header rules. `typed_values.convert(raw, value_type, slot)` has no expected-answer parameter. The comparison layer may use declared type/slot metadata, then compares the resulting canonical string to the expected target. Independent changed-target checks confirm that targets do not change conversion. No digit/sign repair, identifier-zero stripping, total inference, fuzzy alignment, model judge or unsafe eval was found.

Printed comparison still permits only NFC, line-ending conversion and outer trimming. Additional typed rules support strict currency/decimal/percentage forms, boolean marks, valid ISO dates and exact text/identifiers. Value-changing rounding, invalid grouping/sign syntax, ambiguous/unknown units, unsupported structures/types and missing candidates fail explicitly while staying in denominators. Addresses and text are not joined or reordered. Quantity units are validated against a frozen dev vocabulary and retained, while the normalized schema compares the numeric quantity only: a wrong but supported unit can receive numeric typed credit while printed equality fails. That limitation is explicit and independently demonstrated.

The separate reference builder verifies clean-parent PDF hashes and includes all supported writer text operators in declared page/y/x order, plus both declared hybrid-addendum lines. Independent PDFium extraction in the first review matched the non-whitespace character multiset on each of all six dev clean pages; hybrid lines also matched. This establishes per-page inclusion on these dev inputs, not a unique human reading order or a general PDF extractor. Native block order is preserved; deterministic SequenceMatcher token errors are explicitly not minimum-Levenshtein WER. Mapping failures remain separate from raw lexical errors. The corrected source did not change the reference builder, mapping, protocol, runtime or job helper.

Exact dev headers remain deliberately conservative. Historical F07 output still maps 72/180 cells; 108 missing typed cells remain counted. Unknown/duplicate content is retained and counted as schema-relative excess or mapping coverage, without claiming comprehensive factual-hallucination detection. This small fixed synthetic corpus supports no population/generalization or E1–E3 improvement claim. One measured completion per document remains descriptive.

The runner source preserves accepted Q0 model/library/renderer/call/observer primitives and exact release bindings, offline owned caches, storage/free-space caps, phase/stall/session/output guards and no automatic retry. A CPU timeout test exercised the real supervisor against an owned sleeping worker: the active warm-up failed, the remaining 14 planned calls stayed `not_run_after_failure`, and all 13 measured dev document denominators remained in `score_run`. Earlier abrupt-supervisor testing observed distinct venv launcher and actual-worker process handles exit while an unrelated owned sleeping sentinel survived. This source is unchanged, so that evidence remains applicable; it is not represented as newly rerun here. Actual B0 CUDA execution remains untested.

## Executed verification

All commands ran in the owned reviewer worktree. Full argv, outcomes, script revisions and generated files are retained in [reconciliation evidence](../../../reviews/WP-0007/eld-baseline-reviewer/003/reconciliation/8e227abc-050110/results.json).

| Check / exact operation | Actual result |
| --- | --- |
| `python -I -B docs/reviews/WP-0007/eld-baseline-reviewer/003/reconcile_checks.py` at frozen 8e227abce27cd39087b11bf5285b230d3e684fb5 | Exit 0; all 13 original independent probes and eight new groups pass. |
| Subprocess `python.exe -I -B qualification/baseline/tests/test_baseline.py -v` | 37/37 pass. Includes 949 dev printed-value conversions and 949 append-`?` mutation comparisons; grammar coverage, not model accuracy. |
| Independent typed-value checks | 763 conversions checked against integer-scaled expected strings, 39 invalid numeric forms, maximum supported grouped amount, boolean/calendar/text/identifier boundaries, quantity-unit behavior and 30 changed-answer cases pass. |
| Failure/unsupported accounting | Five completion states, missing candidates, unsupported types/target structures, parse-invalid zero credit, empty absence duplicates and malformed/valid/missing document sequence all preserve expected denominators. |
| Independent dev regeneration with pre-open allowlist | All eight generated artifacts byte-identical to /007. Exactly 18 admitted dev synthetic paths; no denied/held-out content and no torch/transformers modules. Both actual B0 runtime roots absent. |
| Retrospective metric preservation | Complete printed-field/printed-cell objects, raw token-error objects and raw-source identity unchanged for both retained Q0 dev outputs versus /002. Typed denominators equal printed denominators. No new model call. |
| Exact Git source/preservation checks | Baseline tree equals df44162c62641596032df04bc834754da38a5f7b; reference/mapping/protocol/runtime/job, Q0/corpus/product/research identities unchanged as scoped. `git diff --check` passes. |
| `publication_audit.py --revision e620a8822652caff71a76c19d999e00f4fd1e816 --output .../publication-audit.json` | Exit 0; 199 changed paths inventoried, 66 reviewer-owned paths, 55 retained evidence-manifest entries match exact Git bytes/digests, and all six protected trees unchanged. |

Retained failures are not hidden. The initial independent review exposed seven failing cases grouped into B0-R1–R4; a separate initial reviewer timeout probe used an invalid `None` argument and was corrected/reexecuted with the original failure preserved. The author retained its initial 36/37 run where an edited Unicode test literal failed, then froze the corrected explicit Unicode literal and passed 37/37. A reviewer publication-audit attempt hit Windows `git show revision:long/path` stat handling; its observed failure summary is retained, and only the audit helper changed to tree/blob-ID reads before the successful audit. No source or evidence bytes, global settings or execution settings changed to bypass these failures.

Not run: any new model execution, held-out reference/scoring, full 26-document B0 result, actual new finite CUDA runtime, product acceptance or /005 sentinel reproduction. CPU sleeping-worker tests and retrospective Q0 scoring do not substitute for those later released checks.

## Complete change inventory and external effects

The [publication audit](../../../reviews/WP-0007/eld-baseline-reviewer/003/publication-audit.json) lists every exact base-to-review-evidence path with action, attribution, byte count, SHA-256 and Git blob, comparing initial reviewer base 8228bfb... to audited e620a882.... The 199 paths comprise 66 reviewer-owned review/helper/evidence paths and 133 normal-merged author/coordinator/other-attributed paths. The original findings, raw failed/passing CPU outputs, actual scratch helpers, dev artifacts, timeout run records, reproduction outputs and inventories are retained.

| Ownership / later metadata | Scope |
| --- | --- |
| Reviewer-owned additions | Only `docs/reviews/WP-0007/eld-baseline-reviewer/**`: sentinel checkpoint, initial probes/findings, actual CPU evidence, one reconciliation helper/results, disposition and publication audit tooling. |
| Imported baseline publication | Author-owned `qualification/baseline/**`, its own /002 and /007 reports and initial/corrected CPU evidence. No reviewer modifications to these paths. |
| Imported coordination/other publications | Shared routing, coordinator /008/design/disposition and attributable F2 review/planning records arrive through the exact normal author merge; they are not reviewer-authored changes. |
| Post-evidence audit metadata | Only `docs/reviews/WP-0007/eld-baseline-reviewer/003/publication-audit.json` at 6d94801c...; excluded from its own pinned inventory by construction. |
| Subsequent report metadata | Only this canonical /003 file; its publication SHA follows separately. |

External effects were owned ignored `.scratch/wp0007-review-003/**` CPU files and short-lived owned Python processes; exact generated artifacts were copied into review evidence. They remain retained. No actual B0 runtime directory, model/library write, package/service/configuration change, unrelated process termination or GPU operation occurred. Normal owned-branch publication is authorized.

## Fixed sentinels and handoff

The immutable pre-result selection at `a8fb2137e559bfeb453bc184c78fab4989c99ecf` remains:

| Fixture | Split | Pages / input type |
| --- | --- | --- |
| `SYN-WO-02-v3-hybrid-note` | dev | 1 / hybrid |
| `SYN-INV-03-v1-raster300` | eval_holdout | 1 / raster |
| `SYN-MP-02-v0-clean` | eval_holdout | 3 / clean |

The coordinator may now bind the accepted source and this report to the exact staged execution/test-content releases, unchanged protocol/mapping/lock/model identities, input order, exclusions, these sentinels, runtime root and observed sole GPU lease. This report itself grants no model/GPU or held-out access. Source/scoring changes after test results remain prohibited without explicit defect disposition.

Later /005 must independently reproduce all retained raw-output scores and execute only these released sentinels under a separate sole lease, observing actual child exits and explicitly returning the lease. `score-run` still enforces a live exact release/HEAD; the coordinator must supply a compatible scoring authority/procedure for later offline reproduction. Neither an expired lease nor this acceptance silently bypasses that check.

Exact author /007 origin was independently verified. Normal reviewer-branch publication follows this report commit; the handoff supplies the actual canonical report publication SHA and exact-origin receipt. This report makes no claim to contain its own commit SHA. No further source correction or review exchange is requested.
