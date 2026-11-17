# WP-0013 /001: finite guarded vocabulary protocol and policy scoring

- Report path: `docs/agent-reports/eld-mapping-author/WP-0013/001_2026-11-17_research_eld-mapping-author.md`.
- Sequence reservation: `47fbc7612e4a08cf1960ad7ac01bd2843ae645e5:INDEX.md`, WP-0013 /001; [kickoff](../../../kickoffs/WP-0013-eld-mapping-author.md).
- Category: research.
- Author / agent ID: eld-mapping-author, stable native `/root/mapping_author`; no subagents.
- Actual model / effort: backend and effort are not exposed; same user-requested xhigh session.
- Execution environment: Windows 11 build 26200, PowerShell, Python 3.12.10; CPU-only protocol checks and Git-object verification.
- Published by: author.
- Timestamp: 2026-11-17T14:12:06.914285+00:00.
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git`, `research/wp-0013-vocabulary`.
- Owned worktree: `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-vocabulary-author`.
- Base / exact authority: `47fbc7612e4a08cf1960ad7ac01bd2843ae645e5`.
- Tested source revision: `6207daf1dc9cbdd141d083ca2d8d1e7507c63b09`.
- Mapping-v2 protocol tree: `e424945507bb1d7ebf70e18e6d26bf808270bb66`.
- Deliverable / inventory-helper revision: `a887615dbc609f245683a46f9333bbd22b66f360`.
- Inventory metadata revision: `76fc3ed5ac71d43496ea4a132d70639da5e4af53`.
- Catalog SHA256: `35a99a213b80476747c7a136a4109ac45bc7944c77b0a3dcf0f348f107dd37a2`.
- Protocol SHA256: `aa0d8f183f9f0161c6e47b56a6f2cd844d6ad3f31e772b9761aa0ad618f6a372`.
- Previous report: [WP-0011 /005](../WP-0011/005_2026-11-17_research_eld-mapping-author.md), completed controlled diagnosis; that lane remains closed.
- Related independent preparation: `fd9e6b9da0e8aa3aadaa18d9261f6e69b7ee4557:docs/reviews/WP-0013/eld-mapping-reviewer/preliminary/proposal-findings.md`; this is preliminary feedback, not canonical /002 acceptance.
- Status: ready-for-review; protocol preparation complete, mapper implementation held.
- Next owner: eld-mapping-reviewer /002, under root's exact publication binding.

## Summary

Published a finite, source-attributed catalog of 26 field/absence aliases and 17 table headers from three already exposed WP11 vocabulary documents. The new namespace contains the public treatment specification, runnable reference validator, unchanged original-score invocation, separate policy scorer, CPU tests and inventories. It contains no v2 mapper or executable model runtime.

Final frozen checks passed 26 tests and reproduced exact B0/v1 predictions and full original scores for all 12 exposed WP11 documents. The deliverable adds 33 owned files; all 3,615 base files remain identical as Git mode/type/blob objects. Forty-one exposed input identities, 14 tested source files and both actual CPU attempts are retained. No fresh private corpus, model, live GPU/process observation, service or download was accessed.

This is author verification of a proposed protocol. Independent /002 acceptance and the exact fresh final reservation remain required before implementation /005. No recovery or positive evaluation result is promised.

## Objective and acceptance criteria

Complete initial CPU protocol work only: freeze a small auditable alias catalog and native-only context/guard policy; define unchanged B0/v1/v2 end-to-end comparison plus separate assignment/coverage/abstention metrics; give the custodian an explicit ground-truth interface; test meaningful public counterexamples; preserve all historical source/data/failures; publish complete evidence and identities. Source acceptance and live evaluation remain separate later gates. The [authority](../../../coordination/WP-0012-0013-authority.md) explicitly requires protocol acceptance and final reserved bytes before any mapper implementation.

## Decisions and rationale

The catalog's aliases come solely from exposed WP11 expected labels and annotation headers, with each proposed mapping linked to its canonical target and source path. Exact NFC/outer trim is retained; internal whitespace and case are exact. One optional terminal colon is allowed for field labels, never table headers. No fuzzy replacement, inferred values, altered typed normalization or model change is proposed.

Profile context must come from complete native table-header evidence, never fixture/family/profile ground truth. A full unique column bijection can mix canonical and catalog aliases or reorder columns. Missing/multiple profiles, duplicate schema candidates, header collisions, invalid spans/widths, repeated headers and duplicate/empty row keys cause conservative abstention as specified. Field identities count canonical and alias occurrences across the entire native page, including duplicate-equal values. All affected v1 candidates are suppressed before guarded resolution; rejection cannot re-enter legacy below-row/inline fallback. Canonical-only tables in an active profile receive the same guards. Untouched v1 output remains explicit.

These prospective guards can reduce original coverage, including losing first-candidate credits that B0/v1 would receive. All gains, losses and neutral results must be retained. No fresh-result-driven catalog or scorer adjustment is allowed. The actual mapper and its guard enforcement tests remain /005 work.

The reference interface keeps B0 expected/reference objects unchanged and places policy truth/action/source evidence separately. Known values bind printed/normalized/type data and quantity_unit presence/value; known absences explicitly mean absent_blank. Ambiguous/unknown values have null policy truth and no invented expected answer. Every opportunity remains in policy. A known row-key cell is required in every expected table row, preserving original row ordinals while preventing empty-row vacuous credit. Original row credit means agreement on declared known cells. Original extra_cells can include declared unjudged cells and is retained without calling those cells inventions.

Policy scoring counts actual emitted candidates, including duplicates, blank outputs, duplicated tables/columns and surplus identities. Exact known assignments, incorrect assignments, strict single-candidate correctness, ambiguous/unknown assignments, abstentions, required-abstention violations and unavailable slots remain separate. An empty output is not exact-value credit. Invalid/missing native evidence does not become successful abstention. Summaries retain all 12 documents/four families with eligible/unavailable denominators and null conditional rates where no eligible denominator exists. Typed quantity scoring still validates supported units while comparing numeric magnitude; no broader semantic claim is made.

The later finite schedule is specified as two excluded historical warmups plus 12 author primaries, followed under a separate lease by the same two warmups and only prespecified `WP13-F04-conflict-v0`. First unexpected failure stops without retry. Product rehearsal has GPU priority. Runtime adaptation is specified only here and must be implemented/reviewed in /005 and /006 before any unseal or model run.

## Change inventory

All paths below are additions. The [complete machine inventory](../../../research/WP-0013/eld-mapping-author/001/deliverable-inventory.json) lists every file's mode, blob, committed/working byte count and SHA256. No base path is modified, deleted or renamed.

| Added paths | Count | Purpose |
| --- | ---: | --- |
| `qualification/mapping_v2/{README.md,__init__.py}` | 2 | Phase boundaries and namespace. |
| `qualification/mapping_v2/protocol/{INTERFACE.md,POLICY.md,__init__.py,catalog.json,protocol.json}` | 5 | Public finite vocabulary, native guard policy, reference interface and machine-readable schedule/metric gates. |
| `qualification/mapping_v2/protocol/{common.py,contract.py,scoring.py,cli.py,run_checks.py}` | 5 | Immutable comparator pins, reference validation, separate policy counts, CPU-only commands and frozen test/reproduction runner. |
| `qualification/mapping_v2/protocol/tests/test_protocol.py` | 1 | Public tiny synthetic reference/prediction counterexamples. |
| `docs/research/WP-0013/eld-mapping-author/001/{.gitattributes,README.md,build_catalog.py,inventory.py}` | 4 | Concise dossier, reproducible exposed-label catalog builder, byte-preserving evidence attributes and frozen inventory helper. |
| `docs/research/WP-0013/eld-mapping-author/001/evidence/attempt-1/{execution.json,historical-comparison.json,inputs.json,source-inventory.json,stderr.txt,stdout.txt,summary.json,tests.json}` | 8 | Original 25-test pass and complete exposed historical reproduction accounting. |
| `docs/research/WP-0013/eld-mapping-author/001/evidence/attempt-2/{execution.json,historical-comparison.json,inputs.json,source-inventory.json,stderr.txt,stdout.txt,summary.json,tests.json}` | 8 | Final 26-test pass, actual streams/receipt and exact input/source/historical accounting. |

Post-deliverable metadata is separate: `deliverable-inventory.json` at `76fc3ed5ac71d43496ea4a132d70639da5e4af53`, then this canonical report. Ignored original command captures remain under `.scratch/wp0013-protocol/attempt-{1,2}/`; the inventory verifies all six published captures against their original bytes. No external runtime, model or service resources were changed. Old worktrees remain untouched.

## Verification

| Actual check | Exact candidate / result | Evidence |
| --- | --- | --- |
| `python -I -B qualification/mapping_v2/protocol/run_checks.py --out docs/research/WP-0013/eld-mapping-author/001/evidence/attempt-1` | Frozen `66204677ee7c84a13c98bf1702d03640e603745f`: exit 0, 25 tests, exact B0/v1 predictions/full scores on all 12 exposed WP11 outputs. | [First summary](../../../research/WP-0013/eld-mapping-author/001/evidence/attempt-1/summary.json), execution receipt and streams. |
| Same command with `--out docs/research/WP-0013/eld-mapping-author/001/evidence/attempt-2` | Frozen `6207daf1dc9cbdd141d083ca2d8d1e7507c63b09`: exit 0, 26 tests, all 12 original predictions/full scores equal; 41 exposed input hashes and 14 source files bound. | [Final summary](../../../research/WP-0013/eld-mapping-author/001/evidence/attempt-2/summary.json), all test names and retained streams. |
| `python -I -B docs/research/WP-0013/eld-mapping-author/001/inventory.py --deliverable a887615dbc609f245683a46f9333bbd22b66f360 --output docs/research/WP-0013/eld-mapping-author/001/deliverable-inventory.json` | Frozen helper/deliverable `a887615dbc609f245683a46f9333bbd22b66f360`: exit 0; 33 additions, 3,615 unchanged base files, exact tested trees, 14 source files, 41 inputs and six original capture copies verified. | Complete inventory at metadata revision `76fc3ed5ac71d43496ea4a132d70639da5e4af53`. |
| `git diff --cached --check` before commits | Passed. | Owned commit chain. |

No executed test/check failed. The first passing attempt is preserved. Subsequent source inspection found the validator applying optional field-colon stripping to headers contrary to the public policy; the final candidate fixes that distinction and adds its negative test. The second decisive run targets the exact correction. Independent preliminary empty-row/partial-row feedback was reconciled before both decisive runs and remains independently attributed. Prior packet failures are preserved in unchanged base objects.

Not run: actual v2 extraction/guard execution (implementation held), private corpus validation/admission (separate custodian/reviewer authority), fresh model calls/live observers (no runtime release), product tests (no product changes) and another full WP7/WP9 suite (unchanged comparator trees; this protocol invokes the original scorers and reproduces all relevant exposed WP11 outcomes). Later /005 implementation requires its own full regression and independent source review.

## Review map, limits and handoff

Start with the [catalog](../../../../qualification/mapping_v2/protocol/catalog.json), [policy](../../../../qualification/mapping_v2/protocol/POLICY.md), [interface](../../../../qualification/mapping_v2/protocol/INTERFACE.md), `contract.py`, `scoring.py` and public tests. The [dossier](../../../research/WP-0013/eld-mapping-author/001/README.md) and [inventory](../../../research/WP-0013/eld-mapping-author/001/deliverable-inventory.json) link exact evidence. [Base-to-deliverable diff](https://github.com/jackgumpe/eledgercare/compare/47fbc7612e4a08cf1960ad7ac01bd2843ae645e5...a887615dbc609f245683a46f9333bbd22b66f360).

Independent /002 must inspect the actual public policy, source and tests, including candidate cardinality, partial/unknown truth, native-only profile selection, explicit legacy suppression and all denominators. A reference validator cannot prove PDF boxes or ideal witness fidelity; independent sealed admission remains required. Public dictionary exposure is deliberate: later evaluation tests fresh facts/layouts and guard behavior, not discovery of unseen aliases. Four content families, one-page scope and fixed conditions limit generalization. Native OCR serialization can fail the conservative structural requirements even on a correctly printed document.

Root should bind this exact publication for /002. Implementation /005 remains held until accepted /002 and the exact final fresh rendered-byte reservation. The custodian's foundation receipt alone is not that reservation. No further user approval is pending within the authorized lane, but this report does not bypass root's sequence/source/corpus/lease gates. No source or alias tuning follows fresh evaluation.

Publication receipt: deliverables and inventory are committed before this report. A normal owned push and exact-origin/clean-state verification follow; the full report publication SHA will be sent to root without rewriting this immutable report. Root alone updates shared routing.
