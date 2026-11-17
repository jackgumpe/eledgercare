# WP-0013 /005: guarded vocabulary mapper and finite runtime adapter

- Report path: `docs/agent-reports/eld-mapping-author/WP-0013/005_2026-11-17_implementation_eld-mapping-author.md`.
- Sequence reservation: `ad7309f2079ed11bc4a63e52567e6a1e5fba1868:INDEX.md`, WP-0013 /005; [implementation kickoff](../../../kickoffs/WP-0013-eld-mapping-author-implementation.md).
- Category: implementation.
- Author / agent ID: eld-mapping-author, stable native `/root/mapping_author`; no subagents.
- Actual model / effort: backend and effort are not exposed; same user-requested xhigh session.
- Execution environment: Windows 11, PowerShell, Python 3.12.10; CPU-only checks and two short-lived owned CPU child processes for Windows job verification.
- Published by: author.
- Timestamp: 2026-11-17T15:22:51.273904+00:00.
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git`, `research/wp-0013-vocabulary`.
- Owned worktree: `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-vocabulary-author`.
- Base / implementation authority: `ad7309f2079ed11bc4a63e52567e6a1e5fba1868`; merged normally from a clean owned worktree.
- Frozen tested source: `c0a1af638e807803b6014b3a93ecb7f9946ce6e1`.
- Mapping-v2 tree: `4477104eb2a3c73f496ef451cef9578f54d96518`.
- Runtime protocol SHA256: `46a0d3e7bec0f14a3911eb7365385b7d132db8e8a72c8edb3f030aeeda124ec2`.
- CPU evidence checkpoint: `93d6edb6656be30ff8c99fb908fe5cb64a2fcb43`, normally pushed and exact-origin verified before independent early /006 dispatch.
- Publication-accounting helper freeze: `08a2730f184b992e952c87c7978596371121a88c`.
- Deliverable revision: `492a7184c833f1077c59d91312d3ea4b895599c6`.
- Inventory metadata revision: `0119f550e198b707034ef19d68af6f2990c5a359`.
- Previous report: [WP-0013 /001](001_2026-11-17_research_eld-mapping-author.md), publication `9b90528f4dbd0ea1ff61c86d0d4040decf178a0a`.
- Related accepted review: [WP-0013 /002](../../eld-mapping-reviewer/WP-0013/002_2026-11-17_review_eld-mapping-reviewer.md), `bb66c7261339a1e5b36a826e949b1eb6f8d62cd8`.
- Public final reservation: `b50b2a3bc22927890c8f391943f2a3fe9168d0da:docs/evaluation/WP-0013/reservation/reservation.json`, SHA256 `533f4be35fb89efd9e288c0470201457b5ab32373eab3112ae283b42febcfea5`.
- Accepted protocol/catalog remain exact: source `6207daf1dc9cbdd141d083ca2d8d1e7507c63b09`, protocol SHA256 `aa0d8f183f9f0161c6e47b56a6f2cd844d6ad3f31e772b9761aa0ad618f6a372`, catalog SHA256 `35a99a213b80476747c7a136a4109ac45bc7944c77b0a3dcf0f348f107dd37a2`.
- Status: ready-for-review; CPU implementation complete, fresh execution unreleased.
- Next owner: eld-mapping-reviewer /006, with root's exact source binding; canonical acceptance awaits this final publication audit.

## Summary

Implemented the one research-only guarded alias/schema mapper and its finite runtime/release/scoring adapter in new mapping_v2 files. Native evidence alone determines profile, field association and table mapping. Affected legacy output is removed before guarded resolution, so rejected identities cannot reappear through v1 fallback. The accepted catalog, protocol, validator, policy scorer and every older source/data/report path remain unchanged.

The first frozen CPU run passed all 61 tests, reproduced 35 independent public protocol probes and mapped 12 independent tiny public native examples with no required-abstention violations. It reproduced full B0/v1 scores for all 42 exposed historical primaries and the separate recovery. Actual v2 predictions, full scores, traces, gains/losses and 193 input identities are retained. No fresh private corpus or model was accessed.

The exposed regression has both gains and losses: WP11 gains 23 field credits, 43 cell credits and seven rows; original WP7 loses 26 field credits. Twelve verified-absence credits are withheld across WP7/WP11 because the native output lacks an explicit empty adjacent cell. No source change follows these outcomes. These are honest guard/coverage tradeoffs, not a guarantee of fresh performance or production promotion.

## Objective and acceptance criteria

Implement only the accepted finite vocabulary treatment after independent protocol acceptance and final reserved bytes; preserve reference/scoring/normalization/model boundaries; exercise actual native guards and full historical regressions; prepare the later exact 14-call author and three-call reviewer adapter; freeze source/helpers before decisive CPU checks; retain every failure/denominator and publish complete evidence/inventory. Independent /006, accepted corpus publication, root unseal and separately observed sole leases remain prerequisites for /007 or reviewer inference.

## Decisions and rationale

`mapper.py:extract_prediction` accepts parsed native data, frozen B0 rules and the finite catalog. Complete exact native headers establish a unique profile and column bijection, supporting mixed aliases/canonical headers and permutations without rewriting raw text. Table guards reject duplicate schemas, conflicting/missing profiles, collisions, repeated headers, non-unit spans, invalid row widths and empty/duplicate row keys. Canonical-only active-profile tables are suppressed and checked too.

Field occurrence counts span the whole page and combine canonical/alias targets, including duplicate-equal occurrences. Inline, immediate-right, direct-below and original-threshold geometric candidates remain separate; multiple candidate orientations, extra plain cells and unsafe label-like values abstain. Multi-label native leaves are treated as ambiguous field boundaries. Non-table markup is not used as a field/value association surface. An explicit empty adjacent cell may produce a blank assignment, while a standalone empty label is withheld. No inferred values, nearest-candidate fallback, fuzzy matching, case/space repair or unit conversion is added. Untouched v1 output and native pages/unmapped content remain visible. Bounded decision traces record source locations, counts, suppression and reasons.

`scoring.py` produces v2 independently, then calls the accepted original-comparison wrapper and original scorer unchanged. Its reference-side policy calls use the already accepted policy scorer. Full candidate cardinality, unknown/ambiguous truth, partial rows, original extra_cells limitations, unavailable records and surplus outputs retain their prior meanings. No policy/reference object enters the mapper.

The runtime adapts accepted coverage_v1 supervision and Q0 primitives. Tests compare model/render/prompt/decoding/guard settings and the worker body after only namespace and owned-process identity additions. It records supervisor/launcher/worker creation identities, verifies the parent identity before model import, keeps owned Windows job cleanup, and retains unsuccessful returned pre/post observer records. First failure stops; no retry/substitution is added; later planned rows remain not-run. A finalization failure preserves genuinely completed calls while returning a failed run. Every scheduled warmup and primary is validated before scoring.

Future roots are `C:/Users/jackg/eLedgerCare-Vocabulary/WP-0013/{author,reviewer}`. No runtime root was created. A future root-owned release must bind exact clean executing HEAD/source/tree, runtime and accepted-contract digests, unchanged comparator/core identities, reservation, corpus commit, accepted /006 and /004 proof objects, explicit unseal, owner/GPU/sole-model-job lease and fresh observed ownership evidence. Only then can the adapter open fresh files. Reused model/dependency/notice roots remain read-only. WDDM sharing, nonexclusive hardware, library-offline versus OS-network limits and torchvision local-SHA TOFU remain explicit.

## Exposed regression results

| Population | Documents | Fields v1 -> v2 | Cells v1 -> v2 | Rows v1 -> v2 | Verified absences v1 -> v2 |
| --- | ---: | --- | --- | --- | --- |
| Original WP7 primaries | 26, including original failed call | 220/361 -> 194/361 | 730/1801 -> 730/1801 | 82/248 -> 82/248 | 9/26 -> 6/26 |
| WP9 exposed set | 4 | 0/39 -> 0/39 | 0/90 -> 0/90 | 0/15 -> 0/15 | 0/4 -> 0/4 |
| WP11 exposed set | 12 | 69/92 -> 92/92 | 129/172 -> 172/172 | 21/28 -> 28/28 | 9/12 -> 0/12 |
| Separate original recovery | 1 | 0/15 -> 0/15 | 0/180 -> 0/180 | 0/20 -> 0/20 | 0/1 -> 0/1 |

All 26 field losses are traced withholding: six ambiguous geometric candidates, five additional plain cells, two duplicate labels, six unsafe label/markup payloads and seven ambiguous multi-label leaves. The twelve absence losses all have no explicit native value candidate. No lost field credit becomes a newly wrong assigned value. The [loss ledger](../../../research/WP-0013/eld-mapping-author/005/evidence/loss-ledger.json) binds each exact before/after slot, raw path, native location and suppression reason.

WP11 gains occur only in its three exposed vocabulary variants, which supplied this public dictionary. They are regression evidence, not blind generalization. Original typed field changes equal printed field changes; original WP7 typed cell credit remains 724/1801 versus printed 730/1801. Quantity-unit semantics and partial-row interpretation remain limited as previously declared. No character-accuracy, semantic completeness, model quality or speed improvement is claimed. Fresh outcomes may be positive, neutral or negative.

## Change inventory

The [complete inventory](../../../research/WP-0013/eld-mapping-author/005/deliverable-inventory.json) enumerates all 27 added deliverable files with Git mode/blob and committed/working sizes/SHA256. All 3,720 base paths remain identical, including accepted protocol/catalog/validator/scorer, old source/corpora/raw/failures/reports and shared routing. No prior path is modified, renamed or deleted.

| Added paths | Count | Purpose |
| --- | ---: | --- |
| `qualification/mapping_v2/{mapper.py,common.py,release.py,runtime.py,runtime_protocol.json,process_identity.py,scoring.py,cli.py,run_checks.py}` | 9 | Guarded extraction, exact later release/runtime/scoring plumbing, owned creation identities and frozen CPU runner. |
| `qualification/mapping_v2/tests/{test_mapper.py,test_release.py,test_runtime.py}` | 3 | Native positives/negatives, release/progression/denominator checks and CPU supervision/owned-job tests. |
| `docs/research/WP-0013/eld-mapping-author/005/{prepare_adapter.py,prepare_runtime_tests.py,.gitattributes,publication.py,README.md}` | 5 | Auditable adaptations, original evidence byte preservation, frozen accounting/inventory helper and concise dossier. |
| `docs/research/WP-0013/eld-mapping-author/005/evidence/attempt-1/{actual-public-native-probes.json,execution.json,historical-regression.json,inputs.json,reused-public-probes.json,stderr.txt,stdout.txt,summary.json,tests.json}` | 9 | Complete actual CPU results, full predictions/scores, retained injected-failure evidence, exact streams and 193 consumed input identities. |
| `docs/research/WP-0013/eld-mapping-author/005/evidence/loss-ledger.json` | 1 | Exact reconciliation of all 26 field and 12 absence-credit losses. |

Post-deliverable metadata: `deliverable-inventory.json` at `0119f550e198b707034ef19d68af6f2990c5a359`, followed by this report. Original command captures remain in ignored `.scratch/wp0013-implementation/attempt-1/` and are byte-identical to published copies. CPU temporary directories lived under `.scratch/wp0013-vocabulary`; owned test children and temporary directories were cleaned up. No model/runtime root, service, installed dependency or other owner's process was changed.

## Verification

| Actual command / check | Exact source and result | Evidence |
| --- | --- | --- |
| `python -I -B qualification/mapping_v2/run_checks.py --out docs/research/WP-0013/eld-mapping-author/005/evidence/attempt-1` | Frozen `c0a1af638e807803b6014b3a93ecb7f9946ce6e1`; exit 0, tool session 44219. All 61 tests pass; 35 reused public probes pass; 12 actual tiny-native cases pass; 42 historical primaries and separate recovery reproduce original full scores. | [Summary](../../../research/WP-0013/eld-mapping-author/005/evidence/attempt-1/summary.json), actual execution receipt/streams, full regression and public-case packets. |
| Same run: native/mapper guards | Actual alias/header mapping, duplicate equal/conflicting/canonical-alias suppression, missing/multiple profile, header collision/unknown/case/colon/span, row shape/key/repeated-header, geometry/inline/extra-cell and explicit-empty cases pass. | `test_mapper.py`, test names/streams, public native predictions and policy scores. |
| Same run: runtime/release/score accounting | Exact 14/3 schedules, source/proof failure before fresh reads, otherwise-valid completed-after-failed rejection, full all-not-run/partial/finalization-failure scoring, resource/time limits, malformed outcome/observation and returned pre/post failures pass. Owned Windows job closes its child while preserving the separately owned control until its own cleanup. | `test_release.py`, `test_runtime.py`, retained injected-state summaries and test streams. |
| `python -I -B docs/research/WP-0013/eld-mapping-author/005/publication.py analyze --output docs/research/WP-0013/eld-mapping-author/005/evidence/loss-ledger.json` | Frozen helper `08a2730f184b992e952c87c7978596371121a88c`; exit 0. Every loss has one exact abstention trace. | Loss ledger at deliverable `492a7184c833f1077c59d91312d3ea4b895599c6`. |
| Same helper `inventory --deliverable 492a7184c833f1077c59d91312d3ea4b895599c6 --output docs/research/WP-0013/eld-mapping-author/005/deliverable-inventory.json` | Exit 0; 27 additions, 3,720 preserved paths, exact tested trees, 193 input files, one public reservation object and all three original capture copies verified. | Inventory metadata revision above. |
| `git diff --cached --check` before commits | Passed. | Owned commit chain. |

No actual CPU attempt failed. Expected injected failures remain explicitly recorded; no original source/test/evaluation failure was erased. The original `SYN-MP-01-v2-skew-pos4deg` failed primary retains its denominator and missing-raw status, while the later recovery stays separate. No source edit followed the decisive test/regression run.

Not run: private fresh validation or scoring, model/renderer invocation, live GPU/process scan, product tests and actual runtime execution. Those are outside this CPU release. The creation-time check queries only the current owned CPU process; orchestration observers are fake. Source freeze and passing CPU tests do not constitute runtime qualification or independent /006 acceptance.

## Review map, risks and handoff

Inspect [mapper](../../../../qualification/mapping_v2/mapper.py), [release](../../../../qualification/mapping_v2/release.py), [runtime](../../../../qualification/mapping_v2/runtime.py), [scoring](../../../../qualification/mapping_v2/scoring.py), [runtime protocol](../../../../qualification/mapping_v2/runtime_protocol.json), tests and the [dossier](../../../research/WP-0013/eld-mapping-author/005/README.md). [Exact base-to-deliverable diff](https://github.com/jackgumpe/eledgercare/compare/ad7309f2079ed11bc4a63e52567e6a1e5fba1868...492a7184c833f1077c59d91312d3ea4b895599c6). The independent reviewer was dispatched against the frozen source/evidence checkpoint while this final packaging completed; this author does not claim that review's result.

The principal tradeoff is deliberate abstention at uncertain native boundaries, with demonstrated losses on exposed canonical documents. Four reserved families/three cases each are not twelve independent families, and the finite public dictionary does not test discovery of unseen aliases. An actual OCR serialization may omit or distort the required structure. Every such outcome remains valid evidence; no catalog/scorer retuning follows fresh evaluation.

Root should bind this final /005 publication for independent /006 reconciliation. Author /007 remains held for accepted /006, admitted/published unchanged fresh bytes, explicit unseal and a separate observed sole-model-job lease after product priority. No fresh content was inspected during implementation. No additional user permission is needed within the authorized lane; root's exact execution gates still apply.

Publication receipt: source, evidence, loss reconciliation and inventory are committed before this report. Normal owned push, exact-origin/clean-state verification and full publication identities follow in the handoff; this immutable report does not claim its own commit SHA. Root alone updates shared routing.
