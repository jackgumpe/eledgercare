# WP-0011 /001: staged coverage diagnosis and finite protocol candidate

- Report path: `docs/agent-reports/eld-mapping-author/WP-0011/001_2026-11-17_research_eld-mapping-author.md`
- Sequence reservation: `8d23d755a35be26ff29c319c527bd770abdcae4b:INDEX.md`, WP-0011 /001.
- Category: research.
- Author / agent ID: eld-mapping-author, stable native session `/root/mapping_author`.
- Actual model / effort: not exposed; existing Codex session continues the user-requested xhigh assignment. No backend/model identity inferred from role naming. No subagents.
- Execution environment: native Codex tools; Windows, PowerShell7.7.0, Python3.12.10; CPU only.
- Published by: author.
- Timestamp: 2026-11-17T08:45:46Z.
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git`, `research/wp-0011-coverage`.
- Owned worktree: `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-coverage-author`.
- Accepted lane base: `956c056be2ec970340074871ecdd7e1a9855d944`.
- Base revision / root authority: `8d23d755a35be26ff29c319c527bd770abdcae4b`.
- Frozen corrected source: `adb51ac317db18950f3f1ef4629864127956eddc`.
- Coverage source tree: `ed07a273a57a71b43b0fed9cea12a2245d7c7958`.
- Deliverable revision: `57feb11a66924fdc610dbe08737b09ed276c6773`.
- Inventory metadata revision: `6017c266b9a4922a7acacf6a5b7c5dc322d4e073`.
- Previous report: first author report in WP-0011; historical [WP-0009 /007](../WP-0009/007_2026-11-16_implementation_eld-mapping-author.md) remains immutable.
- Related reports/evidence: accepted WP-0009 /006 and /008; independent WP-0011 preliminary source note `05b599f311a8b0b84c5fa3461a373d24bf701fd0`; public reservation `98a3a3f73df0e578ae98ebf3923db7ba4882d018`; root adapter scope `784e687b25aca3d726c5fbfed3c1b14745cb865d`. Root reports corpus /004 accepted at `021dc265790c90ae83f1afa24fc3f2a71eae41e1`; this author did not inspect sealed evidence.
- Status: ready-for-review; author verification only.
- Next owner: eld-mapping-reviewer /002 under coordinator dispatch.

## Summary

Added a runnable, separately versioned CPU diagnostic and finite adapter under `qualification/coverage_v1`. The corrected frozen candidate passed22/22 CPU checks, reproduced all26 original full B0/v1 score objects and four exposed WP9 complete paired predictions/scores, and reproduced the separate recovery. The historical primary diagnosis keeps30 documents/29 completed and2,291 field/cell slots, with2,096 eligible and195 unavailable presence slots. No mapper, model, conversion or historical score definition changed.

The [diagnosis dossier](../../../research/WP-0011/eld-mapping-author/001/README.md) provides exact raw/expected pointers and distinguishes recognition substitutions, structure/header barriers, vocabulary/association failures, normalization limits and unadjudicated cases. WP9's four exposed documents still score0/39 fields and0/90 cells under both mappers, despite38/39 field strings and88/90 cell strings appearing in same-page visible payload. Exact field-label support is0/39. This supports a structured-coverage limitation; it is not a character-accuracy estimate or proof of correct semantic association.

Source, interface, matching/denominator definitions, fixed12-primary/two-warmup and one-sentinel/two-warmup schedules, failure retention and future release gates are reviewable now. Fresh WP11 payload remains unread by this author. No inference, GPU query, model import, download, service or future runtime-root creation occurred. /005 remains held for independent /002 acceptance, accepted admission, root unseal and separately observed exact runtime release.

## Objective and acceptance criteria

Executed the authorized CPU diagnosis and protocol/scoring preparation, including root's explicit bounded adapter extension. Criteria were: inspect actual immutable raw/scoring evidence; retain original failure and separate recovery; freeze helpers before decisive checks; produce deterministic stage metrics with explicit uncertainty; coordinate a public schema without examples; implement finite runtime/release/scoring plumbing before unseal; test meaningful counterexamples and failure denominators; preserve all prior source/data/reports; inventory and publish exact owned revisions. All author-side criteria are complete. Independent source acceptance and actual controlled results are not claimed.

## Change inventory

The [machine-readable deliverable inventory](../../../research/WP-0011/eld-mapping-author/001/deliverable-inventory.json) lists every added path's committed size, SHA256 and Git blob. All2,704 authority-base paths retain exactly the same mode/type/blob; no prior path is modified, deleted or renamed. The28 additions are:

| Action | Exact path | Purpose / relevant symbols |
| --- | --- | --- |
| Added | `qualification/coverage_v1/__init__.py` | Separate namespace. |
| Added | `qualification/coverage_v1/common.py` | Read-only B0/v1 imports, pinned tree verification, protocol access. |
| Added | `qualification/coverage_v1/contract.py` | `validate`, `semantic_signature`, `validate_family`, `support_control`; semantic pairing and both-mapper ideal control witness. |
| Added | `qualification/coverage_v1/diagnostics.py` | `visible_units`, `presence`, `row_binding`, `unit_agreement`, `diagnose`, `paired_conditions`; reference-side stage evidence. |
| Added | `qualification/coverage_v1/cli.py` | CPU support check; separately released execute/worker/score-run entry points. |
| Added | `qualification/coverage_v1/INTERFACE.md` | Public expected/reference/annotation shape and private witness constraints. |
| Added | `qualification/coverage_v1/README.md` | Metric semantics, limits, runtime provenance, future root release fields. |
| Added | `qualification/coverage_v1/protocol.json` | Twelve opaque inputs/48 public descriptors, exact settings,14/3 schedules, one preselected sentinel, stage definitions. |
| Added | `qualification/coverage_v1/release.py` | Exact source/review/admission/unseal/input/lease binding before fresh reads. |
| Added | `qualification/coverage_v1/runtime.py` | Attributed bounded adaptation of accepted mapping-v1 operational code. |
| Added | `qualification/coverage_v1/scoring.py` | Unchanged full B0/v1 scores plus distinct diagnostics, all author rows/pairs or sole reviewer sentinel. |
| Added | `qualification/coverage_v1/run_checks.py` | Frozen CPU suite, exact historical reproduction, anchored stage ledger and input inventory. |
| Added | `qualification/coverage_v1/tests/test_diagnostics.py` | Eleven semantic/uncertainty/visibility/pairing tests. |
| Added | `qualification/coverage_v1/tests/test_release.py` | Five schedule/proof/failure-denominator tests. |
| Added | `qualification/coverage_v1/tests/test_runtime.py` | Six ownership/observer/guard/supervisor/source-isolation tests. |
| Added | `docs/research/WP-0011/eld-mapping-author/001/README.md` | Actual findings, evidence anchors, failures and prospective protocol dossier. |
| Added | `docs/research/WP-0011/eld-mapping-author/001/package_inventory.py` | Frozen Git-object inventory/preservation helper. |
| Added | `docs/research/WP-0011/eld-mapping-author/001/attempt-1/execution.json` | First frozen source/command/timestamps/exit1. |
| Added | `docs/research/WP-0011/eld-mapping-author/001/attempt-1/tests.json` |22 checks,21 pass/one invocation error. |
| Added | `docs/research/WP-0011/eld-mapping-author/001/attempt-1/stdout.txt` | Retained first CPU operational probes. |
| Added | `docs/research/WP-0011/eld-mapping-author/001/attempt-1/stderr.txt` | Test outcomes and missing-argument traceback. |
| Added | `docs/research/WP-0011/eld-mapping-author/001/attempt-2/execution.json` | Corrected frozen source/command/timestamps/exit0. |
| Added | `docs/research/WP-0011/eld-mapping-author/001/attempt-2/tests.json` |22 passed, no failures/errors/skips. |
| Added | `docs/research/WP-0011/eld-mapping-author/001/attempt-2/stdout.txt` | Successful Windows job test, supervisor scenarios and diagnosis accounting. |
| Added | `docs/research/WP-0011/eld-mapping-author/001/attempt-2/stderr.txt` | Complete22-test results. |
| Added | `docs/research/WP-0011/eld-mapping-author/001/attempt-2/summary.json` | Historical reproduction, primary/eligible/unavailable counts and nonexclusive flags. |
| Added | `docs/research/WP-0011/eld-mapping-author/001/attempt-2/input-inventory.json` |144 consumed files and one public Git object, byte/hash/blob identities, original missing raw path. |
| Added | `docs/research/WP-0011/eld-mapping-author/001/attempt-2/diagnostic-ledger.json` | Every historical primary slot, separate recovery and reused prior attribution anchors. |

Post-deliverable metadata is separately committed: `docs/research/WP-0011/eld-mapping-author/001/deliverable-inventory.json` at `6017c266b9a4922a7acacf6a5b7c5dc322d4e073`, followed by this reserved report. Shared routing is unchanged. Ignored `.scratch/wp0011-coverage/` holds bounded test-only temporary resources and capture files. Two owned standard-library children were started and cleaned in each CPU suite; no other process was terminated. There are no database, product, external service or model-cache changes. The prior WP9 worktree was not touched.

## Decisions and rationale

The diagnostic uses decoded visible leaves, exact case-sensitive NFC/whitespace-normalized matches and word boundaries on the correct page. Coordinates, native tag syntax, HTML attributes/comments and script/style text are excluded. Occurrence counts, expected-value reuse, page/block/row/cell locations and snippets remain visible. Unique row-key evidence may locate a cell, while a matching value in another row cannot establish association. Field label/value presence alone remains explicitly unadjudicated as a relationship. Missing or globally parse-invalid output has unavailable stage rates; locally parsed positive evidence can survive separately. Original B0/v1 eligibility and scores remain unchanged.

Controls require both frozen mappers to recover the canonical ideal-native witness's intended supported fields/tables/absences; familiar labels alone are insufficient. Condition-specific annotations remain reference-side. Semantic signatures bind canonical IDs, stable rows, printed/normalized values, types, optional quantity_unit presence/value and explicit absent_blank state. Expected and annotation absence labels must match. Public checkpoint63a14ca omitted the latter additive pairing constraints; reviewer identified the gap, and it was corrected with generic negative tests before final source freeze. Custodian confirmed schema-only compatibility with the unchanged sealed candidate. No identifying example was provided to this author.

The original typed quantity comparison remains numeric after unit grammar validation. A separate literal-unit diagnostic exposes unit disagreement without relabelling historical credit; identifiers retain leading zeroes. Absence unverified/blank/violation semantics and unmatched candidates remain historical evidence, not a comprehensive invention detector. Overlapping flags are not forced into causal percentages. Old data lacks new table annotations, so automated table support/local association is unknown there; reviewed manual anchors are attributed separately.

The matrix is three families by four conditions, with all nine within-family control comparisons retained. Failed/not-run rows remain in the twelve-primary frame; paired presence deltas report eligible and unavailable pairs. Fixed family-major order is an acknowledged time/order confound. Sentinel `WP11-F03-degraded-v0` was fixed before outputs. The finite adapter retains the accepted model/session/render/telemetry/guard/cleanup behavior, scoped to the new namespace and owner denominators. Runtime source-isolation testing verifies those bounded differences.

B0 source `522f15f1f6e399c36b9c6c107fc08f51862f1fc1`, tree `deae8e826f4770e880374c68e6a56c8c65b6f8a3`; mapping-v1 source `23e023045b335540d830ce01b75be247552a63f1`, tree `59f66d0d3d9be145a43efcc9258eb260d3ef2f00`; and Q0 core tree `fee7218eb233438cce7c583be1527b5c549930f0` remain immutable. Future runtime reuses the pinned external qualified dependencies/model read-only, including the existing explicitly acknowledged torchvision local-SHA TOFU exception. Desktop GPU activity/[N/A] values remain honest observations; exact root sole-model-job ownership is not OS-exclusive hardware proof. No other-app termination is authorized or implemented.

## Verification

| Check / exact command | Environment and revision | Actual result | Evidence |
| --- | --- | --- | --- |
| `python -I -B qualification/coverage_v1/run_checks.py --out docs/research/WP-0011/eld-mapping-author/001/attempt-1` | Clean `67615d2b76a92f42a65901deffcc47937f7615fc`, Python3.12.10 | Exit1;21/22 passed, one test invocation missing required completion argument; no historical diagnosis run. | attempt-1 four files; retained at `69bc9d7d39b583a06e3d2aa2c948d7017b36800e`. |
| Same command with `attempt-2` | Clean corrected source `adb51ac317db18950f3f1ef4629864127956eddc` | Exit0;22/22, no skips; all26 original full scores, four exposed paired prediction/score packets and separate recovery reproduce exactly. | attempt-2 seven files. |
| CPU runtime ownership/fault probes within above suite | Same frozen source, mocked observations/model execution | Owned Windows job cleanup passed; normal, first failure, malformed record/outcome and post-observer failure preserve14 scheduled calls/12 primary rows. Failed paired-scoring probe preserves12 and nine unavailable pairs; reviewer retains one denominator. | `tests/test_runtime.py`, `tests/test_release.py`, stdout/stderr. |
| Source isolation/guards within above suite | Same frozen source | New runtime differs from accepted source only in named scope/provenance/schema metadata. Resource/model/render/call/guard/warmup pins agree; source proof failure blocks fresh artifact reads. | Runtime/release test results and actual source. |
| `python -I -B docs/research/WP-0011/eld-mapping-author/001/package_inventory.py --deliverable 57feb11a66924fdc610dbe08737b09ed276c6773 --out docs/research/WP-0011/eld-mapping-author/001/deliverable-inventory.json` | Clean deliverable; helper frozen in that commit | Exit0;28 added paths inventoried,2,704 original path mode/type/blob identities preserved, unchanged tested coverage tree. | Inventory metadata `6017c266b9a4922a7acacf6a5b7c5dc322d4e073`. |
| `git diff --cached --check` before commits | Owned worktree | Passed. Existing Git attributes normalize console CRLF to LF; inventory hashes committed bytes explicitly. | Git commits and inventory. |

No fresh input, model, actual inference, GPU query, new runtime environment or service check was run. Those are gated later work, not missing CPU execution. The successful decisive suite was not repeated during packaging. The initial invocation failure remains visible; it was not represented as a model or production failure. A routine attempted read of nonexistent `docs/agent-reports/REPORTING.md` returned path-not-found; the actual applicable `README.md` reporting guide and template were read. Two earlier patch-context mismatches made no edits. No functional failure was hidden by those preparatory command errors.

## Review map

- [Exact base-to-deliverable diff](https://github.com/jackgumpe/eledgercare/compare/8d23d755a35be26ff29c319c527bd770abdcae4b...57feb11a66924fdc610dbe08737b09ed276c6773).
- [Source README](../../../../qualification/coverage_v1/README.md), [public interface](../../../../qualification/coverage_v1/INTERFACE.md), [diagnostics](../../../../qualification/coverage_v1/diagnostics.py), [contract](../../../../qualification/coverage_v1/contract.py).
- [Release gate](../../../../qualification/coverage_v1/release.py), [runtime](../../../../qualification/coverage_v1/runtime.py), [score-run](../../../../qualification/coverage_v1/scoring.py), [protocol](../../../../qualification/coverage_v1/protocol.json).
- [Findings and exact anchors](../../../research/WP-0011/eld-mapping-author/001/README.md), [full ledger](../../../research/WP-0011/eld-mapping-author/001/attempt-2/diagnostic-ledger.json), [consumed-input inventory](../../../research/WP-0011/eld-mapping-author/001/attempt-2/input-inventory.json), [deliverable inventory](../../../research/WP-0011/eld-mapping-author/001/deliverable-inventory.json).

Protocol SHA256 `b5b2b051d7b154d2696c83b99ce7712490686508147fe267a462c7b73db56ec8`; CPU helper SHA256 `63af560c2ac535bd03711802949ff5689e01206e91095a409551fe2edf44add0`; contract SHA256 `7437f87cc6cfc2df58ebd6102b95951d3b0199e609e85b39c965e648bf6ec73d`. All source/evidence file hashes are in the inventory.

## Risks, disagreements, and unfinished work

No unresolved public schema disagreement remains. Independent /002 must inspect actual implementation and challenge the visibility, support, row-identity, semantic-pairing, unavailable-denominator and runtime-boundary logic. Historical text presence is neither full OCR accuracy nor semantic correctness; exact absence of text can reflect recognition, omission or segmentation. The old missing raw's cause remains unproven; the recovery is separate. New annotations are not retrofitted into old evidence. Private witness visual fidelity and one-factor constraints belong to independent admission.

No quality treatment is selected or implemented here. The controlled supported-control experiment is the next evidence needed before another treatment recommendation. Three families and one fixed degraded severity cannot establish broad generalization. Neutral finite results complete the later experiment; retries/tuning need a separate recorded disposition. The candidate itself grants no fresh access or runtime lease.

## Handoff

Coordinator should dispatch independent /002 on source `adb51ac317db18950f3f1ef4629864127956eddc`, unchanged coverage tree `ed07a273a57a71b43b0fed9cea12a2245d7c7958`, deliverable `57feb11a66924fdc610dbe08737b09ed276c6773` and inventory `6017c266b9a4922a7acacf6a5b7c5dc322d4e073`. Reviewer should reproduce the CPU evidence in isolated scratch without accessing fresh content through the author path. Later root release fields and exact proof routes are in source README/release.py; current canonical source acceptance is not assumed.

Publication receipt: this report is committed after its deliverable/inventory. Normal owned-branch push and exact-origin verification follow; the author sends their full publication SHA and result to root without rewriting this immutable report. Root alone updates routing/index. Actual /005 execution remains separately held.
