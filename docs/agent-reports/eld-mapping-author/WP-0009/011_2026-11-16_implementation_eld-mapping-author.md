# WP-0009 /011: F006-01 sentinel policy consistency correction

- Report path: `docs/agent-reports/eld-mapping-author/WP-0009/011_2026-11-16_implementation_eld-mapping-author.md`
- Sequence reservation / authority: [exact INDEX](https://github.com/jackgumpe/eledgercare/blob/35c095943e71f76b8bfe4f9d6a76e38dd55182e0/INDEX.md), [correction kickoff](../../../kickoffs/WP-0009-eld-mapping-author-protocol-correction.md), **35c095943e71f76b8bfe4f9d6a76e38dd55182e0**.
- Category / author / publisher: implementation; **eld-mapping-author**, same native Codex `/root/mapping_author`; normal owned publication.
- Actual model / effort: native Codex; backend model/checkpoint and actual effort not separately exposed. Continuing the same session requested xhigh by Jack; no stronger identity claim.
- Execution environment: Windows PowerShell; CPython **3.12.10**, isolated `-I -B`; CPU-only runner blocks model/renderer imports.
- Timestamp: **2026-11-16T20:31:11.0220639Z**, UTC report preparation after frozen verification.
- Repository / branch / worktree: private `jackgumpe/eledgercare`; `research/wp-0009-mapping`; `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-mapping-author`.
- Initial clean /005 publication: **8942eb843c635ef381da11d9d5ce95524eeb979e**; original source **b95c12d2fd8d71598a1e9c523182cd1a2f3ee121**.
- Exact work base after authorized normal authority merge: **213bd0d509a8db3518946d64293e7d183dc06d40**.
- Independent initial F006-01 finding: **93dd59606c39f2cd7dca77c7773ffac0b2eb0e81**, [pinned findings](https://github.com/jackgumpe/eledgercare/blob/93dd59606c39f2cd7dca77c7773ffac0b2eb0e81/docs/reviews/WP-0009/eld-mapping-reviewer/006/initial-findings.md).
- **Corrected frozen source/helper: 23e023045b335540d830ce01b75be247552a63f1**.
- Mapping namespace tree: **59f66d0d3d9be145a43efcc9258eb260d3ef2f00**; protocol SHA256 **f54214cc42307eb955f44f4c6470311f01ff7cf93887ea21d024feaa08a63e42**.
- **Deliverable / CPU evidence / frozen inventory helper: 05b14c9b4e7a9bdb36fb6d82397c260db21e4579**.
- Post-deliverable complete inventory: **1674c3c280f6173998ea673e92b7af08cb6eb6cd**.
- Previous report: [author /005](005_2026-11-16_implementation_eld-mapping-author.md), publication **8942eb843c635ef381da11d9d5ce95524eeb979e**; unchanged.
- Related reports: independent diagnosis /002 **ca96f769c822b1b5ef28b377e27d665e2f1f8b98** and admission /004 **3e5d305d0cdcb2666ba56912ba6c06dc19d74c8b**; canonical source /006 awaits reconciliation.
- Status: **ready-for-review**, author correction and CPU verification only.
- Next owner: same independent **eld-mapping-reviewer /006**, then root for later gates.

## Summary

Corrected the sole independent finding F006-01: the sentinel declaration now describes exactly one preselected three-page clean-digital reviewer sentinel. It no longer claims single-page or raster/hybrid sentinel coverage. A new test checks this declaration against the actual finite reviewer schedule and public fixture metadata.

The corrected frozen source passed **23 CPU tests**, all **26 original full-score reproductions** and separate recovery. Results remain **27 printed-field gains, 27 typed-field gains, zero losses**. The entire regression payload equals /005 except the source revision/tree fields. Mapper, scoring, operational runtime, release behavior and every other protocol setting are unchanged. This report supersedes the /005 source candidate only for this correction; prior reports and evidence remain immutable.

## Objective and acceptance criteria

Resolve F006-01 within root's narrow release: change only declarative sentinel policy and add a meaningful consistency test; freeze before full CPU regression; preserve all prior source/evidence outside those two paths; publish a new correction dossier, inventory and reserved /011. No new quality treatment, fixture, warmup, sentinel, model call or executable behavior is authorized by this correction. These author criteria are met; independent /006 acceptance is pending.

## Change inventory

The exact work-base-to-deliverable diff contains **11 paths: two modifications and nine additions**. [Complete inventory](../../../research/WP-0009/eld-mapping-author/correction-011/deliverable-verification.json) lists every path, Git identity, size and published/worktree SHA256, with all **2,133 other work-base files** verified unchanged.

| Action | Exact path | Change |
| --- | --- | --- |
| Modified | `qualification/mapping_v1/protocol.json` | Only `sentinel_policy`: multi-page category, one measured document, three pages, clean-digital-only scope and explicit uncovered categories |
| Modified | `qualification/mapping_v1/tests/test_release.py` | `test_declared_sentinel_policy_matches_finite_schedule_and_scope` checks actual measured/warmup entries, fixed count/page coverage and policy scope |
| Added | `docs/evidence/WP-0009/eld-mapping-author/011/attempt-1/comparison.json` | Full paired scores and all primary/supplemental rows |
| Added | `docs/evidence/WP-0009/eld-mapping-author/011/attempt-1/execution.json` | Exact command, source, timing and exit |
| Added | `docs/evidence/WP-0009/eld-mapping-author/011/attempt-1/input-inventory.json` | All 123 consumed input identities |
| Added | `docs/evidence/WP-0009/eld-mapping-author/011/attempt-1/stderr.txt` | All 23 named test outcomes |
| Added | `docs/evidence/WP-0009/eld-mapping-author/011/attempt-1/stdout.txt` | Real owned cleanup and deliberate mocked-failure observations, regression receipt |
| Added | `docs/evidence/WP-0009/eld-mapping-author/011/attempt-1/summary.md` | All 26 primary rows and retained denominator summary |
| Added | `docs/evidence/WP-0009/eld-mapping-author/011/attempt-1/tests.json` | Frozen source and test totals |
| Added | `docs/research/WP-0009/eld-mapping-author/correction-011/RESULTS.md` | Correction rationale, evidence and limits |
| Added | `docs/research/WP-0009/eld-mapping-author/correction-011/verify_correction.py` | Frozen Git/CPU preservation and complete inventory helper |

Post-deliverable metadata is separate: `docs/research/WP-0009/eld-mapping-author/correction-011/deliverable-verification.json` at **1674c3c280f6173998ea673e92b7af08cb6eb6cd**, then this report. Shared routing was received only through the supplied authority merge; the author did not edit it. Source README needed no change.

External effects: normal owned Git commits/push, ignored `.scratch/wp0009-mapping` captures and temporary CPU test directories, two short owned standard-library Python children for Windows-job isolation, both cleaned. No service, database, package/model environment, external runtime root or other owner's process changed. No fresh content or GPU query occurred.

## Decisions and rationale

The executable reviewer schedule was already correct: two excluded historical warmups, then exactly `WP09-F04-v0`. The stale declaration inherited three B0 sentinel categories. The correction changes that declaration to `required_categories=[multi_page]`, `measured_document_count=1`, `page_counts=[3]`, `content_scope=clean_digital_only`, and `not_covered_categories=[single_page,raster_or_hybrid]`. Existing preselection and release-binding fields remain.

The new consistency test derives measured IDs and page categories from `release.schedule(protocol, reviewer)` and the public opaque fixture metadata. It checks one measured document, three pages, two excluded warmups, category agreement, explicit clean scope and nonoverlapping uncovered categories. The old category declaration fails this check. No fresh labels, values, layouts or expected answers were read.

`mapper.py`, `scoring.py`, `runtime.py`, `release.py` and `run_checks.py` retain exact /005 Git blobs. Every protocol value outside `sentinel_policy` is structurally identical. All original B0/Q0/parser/typed rules, fixture matrices, model/render parameters, guards, admission/source routes and expected answers remain unchanged.

## Verification

| Actual command / operation | Exact revision | Result / evidence |
| --- | --- | --- |
| Startup branch/status/HEAD; normal merge of authority **35c095943e71f76b8bfe4f9d6a76e38dd55182e0**; complete kickoff and exact finding read | Initial /005; work base **213bd0d509a8db3518946d64293e7d183dc06d40** | Clean owned branch; conflict-free merge; no fresh content |
| `python -I -B qualification/mapping_v1/run_checks.py --out docs/evidence/WP-0009/eld-mapping-author/011/attempt-1` | **23e023045b335540d830ce01b75be247552a63f1** | **Exit 0**, 23 tests, zero failures/errors/skips; 26 original full scores plus separate recovery reproduce; 27 printed/typed gains, zero losses; 123 inputs. [Execution receipt](../../../evidence/WP-0009/eld-mapping-author/011/attempt-1/execution.json) |
| Existing generic guard, ambiguity, duplicate, parser-limit and comparator-independence tests; mocked supervisor faults and real owned Windows-job cleanup | Same frozen source | All pass; fault statuses remain deliberate test results, with all four planned author primary rows retained. [Test log](../../../evidence/WP-0009/eld-mapping-author/011/attempt-1/stderr.txt), [runtime CPU observations](../../../evidence/WP-0009/eld-mapping-author/011/attempt-1/stdout.txt) |
| `python -I -B docs/research/WP-0009/eld-mapping-author/correction-011/verify_correction.py --deliverable 05b14c9b4e7a9bdb36fb6d82397c260db21e4579 --out docs/research/WP-0009/eld-mapping-author/correction-011/deliverable-verification.json` | Helper frozen in **05b14c9b4e7a9bdb36fb6d82397c260db21e4579** | **Exit 0**; all 11 changes inventoried, 2,133 protected paths unchanged, 123 input hashes verified, all /005 comparison objects identical apart from source identities, only two allowed source changes |
| `git diff --check`, staged checks; inventory helper AST syntax check | Source/deliverable/inventory freezes | Pass |

Primary denominators remain **361 fields and 1,801 cells**, including the original failed primary document and its unknown raw output. The separate recovery remains parse-ineligible and supplemental. All non-field score objects are unchanged. These are exposed historical regression results; they do not establish generalization, model recognition improvement or fresh runtime success.

## Failures, risks and checks not run

No correction CPU test failed. Before the authority merge, a kickoff read failed because its new path was absent. A fast-forward-only merge then correctly refused divergent history; the authorized normal merge succeeded without conflict. No history was rewritten. Prior /005 attempts, original runtime failure/recovery and independent initial F006-01/reviewer AST-helper failure evidence remain unchanged. Deliberately injected supervisor failure statuses are retained as test evidence, distinct from genuine model execution.

Not run: fresh-content reads/unsealing, GPU/process queries, model/renderer imports or preflight, inference, services, actual finite runtime, future release loading or product tests. These are outside this correction and remain gated by independent /006 and root. The finite runtime still requires a reviewed root sole-model-job lease and retained observations; this correction makes no hardware exclusivity claim.

## Review map

- [Pinned correction deliverable diff](https://github.com/jackgumpe/eledgercare/compare/213bd0d509a8db3518946d64293e7d183dc06d40...05b14c9b4e7a9bdb36fb6d82397c260db21e4579).
- [Protocol](../../../../qualification/mapping_v1/protocol.json), `sentinel_policy`; [test](../../../../qualification/mapping_v1/tests/test_release.py), `test_declared_sentinel_policy_matches_finite_schedule_and_scope`.
- [Correction dossier](../../../research/WP-0009/eld-mapping-author/correction-011/RESULTS.md), [full regression](../../../evidence/WP-0009/eld-mapping-author/011/attempt-1/comparison.json), [input inventory](../../../evidence/WP-0009/eld-mapping-author/011/attempt-1/input-inventory.json), [complete preservation inventory](../../../research/WP-0009/eld-mapping-author/correction-011/deliverable-verification.json).

## Handoff

Same independent **eld-mapping-reviewer /006** reconciles F006-01 on corrected source **23e023045b335540d830ce01b75be247552a63f1**, tree **59f66d0d3d9be145a43efcc9258eb260d3ef2f00**, deliverable/evidence **05b14c9b4e7a9bdb36fb6d82397c260db21e4579**, and inventory **1674c3c280f6173998ea673e92b7af08cb6eb6cd**. This is author verification, not independent acceptance. No extra correction or scope dispute remains known.

Owned branch and canonical report path are above. Normal push and exact-origin verification follow the report commit; full publication SHA and remote receipt are supplied to root separately, without claiming this report contains its own SHA. Root alone edits routing and releases later /010 unsealing or /007 execution.
