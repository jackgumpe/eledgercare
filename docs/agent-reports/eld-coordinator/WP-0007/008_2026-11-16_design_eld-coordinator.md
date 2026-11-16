# WP-0007 /008: Printed and typed-value metric clarification before test access

- Report path: `docs/agent-reports/eld-coordinator/WP-0007/008_2026-11-16_design_eld-coordinator.md`
- Sequence reservation: WP-0007 /008 in deliverable INDEX.md.
- Category: design
- Author / publisher: eld-coordinator, Codex session 01a1d895-c605-7ab2-b7ec-c3159c0634ba; actual model/effort not exposed.
- Execution environment: Windows PowerShell and host CPython 3.12.10.
- Timestamp: 2026-11-16T04:44:23.938Z
- Repository / branch: private https://github.com/jackgumpe/eledgercare / coordination/bootstrap.
- Base revision: `fbf6507b50a5ee1f5c8a3c3313e3c0b8d49e5362`; original packet base `8e80a42c29c0fc27a4af6348cfb1ec22cab3764d`.
- Deliverable revision: `be3de3c1f17d5177cba87f589752c646b37d356c`.
- Previous report: root WP-0007 /001 at `c08d50e204395e60a88ce25f70e25bd29b97b8c6`.
- Related reports/findings: author /002 `7abf4c1f6c3e6d8d92b6ddb8e45ec75e8daaf4d2`; native independent findings `c4b0688604caa08a042f9629896b844e7258b50a`; Carbon F2/B0 design review `e2452e1ab3d8937868c07ffb30ce430715b5be78`.
- Status: ready-for-review; coordinator clarification, not independent scorer acceptance.
- Next owners: same eld-rd-astra /007 bounded response, then independent eld-baseline-reviewer /003 reconciliation.

## Decision and rationale

B0 will retain strict printed-string exact metrics and add a separately labeled typed normalized-value metric before any held-out content is opened. The [exact disposition](../../../coordination/WP-0007/scoring-disposition.md) freezes the distinction between lexical normalization and declared lossless type canonicalization. Prediction extraction remains independent of expected answer values; identifiers keep their zeros, signs/digits are never repaired, no totals are inferred, and missing/unsupported/failed values stay in denominators. Raw candidates, printed metrics, mapping coverage and excess/duplicate/absence counts remain visible.

The initial author's printed-only metric was clearly disclosed. The native reviewer reasonably interpreted B0's lexical-normalization language narrowly; Carbon's provisional design review required typed definitions as well. This coordinator choice reconciles that scope before test access and prevents a later metric change after answers are visible. It is not a retroactive accusation that the author concealed its metric. The independently reproduced B0-R1..R4 parser/accounting/reviewer-path defects remain separate factual findings.

One consolidated author response covers both those defects and this clarification. No second response per issue, model change, E1-E3 treatment, rerun-until-pass or paired performance claim is authorized. The same independent reviewer assesses the exact corrected source and this clarification's implementation, then accepts or escalates the remaining concrete question. Fixed sentinel selection at `a8fb2137e559bfeb453bc184c78fab4989c99ecf` is unchanged.

## Complete change inventory

The base-to-deliverable diff contains exactly seven paths:

| Action | Exact path | Purpose |
| --- | --- | --- |
| Modified | `CURRENT.md` | Current accepted F2 design and pending B0 correction/review states |
| Modified | `INDEX.md` | Full pins, one-response routing and /007-/008 reservations |
| Added | `docs/coordination/WP-0006/design-acceptance.md` | F2 design disposition only; carried implementation checks |
| Added | `docs/coordination/WP-0006/design-publication-audit.json` | Four exact reviewed Git blobs, published identities and actual assertion receipt |
| Added | `docs/kickoffs/WP-0006-eld-f2-implementation.md` | Already-authorized F2 code/CPU/database/browser release; no GPU lease |
| Added | `docs/coordination/WP-0007/scoring-disposition.md` | Printed/typed metric decision, exact limits and review reconciliation |
| Added | `docs/kickoffs/WP-0007-eld-rd-astra-correction.md` | Single author CPU response and new /007 reservation |

This canonical /008 file is the only later report-metadata addition. Root owns these records; no product/scorer/model/corpus source, original report or external runtime state changes in this deliverable. F2's separately accepted design can proceed while B0 correction is reviewed.

## Verification and handoff

Actual `git ls-remote` checks confirmed exact independent review refs e2452e1... and c4b0688.... Root inspected the canonical F2 review, B0 findings, actual source/evidence receipts and conflicting scope interpretations. The publication audit verifies all four F2 review additions and unchanged integrated bytes, with the actual 15/15 design assertions; this is not runtime/application acceptance. `git diff --cached --check` passed. `git diff-tree --no-commit-id --name-status -r be3de3c1f17d5177cba87f589752c646b37d356c` produced the seven paths above.

No new product/CPU scorer suite, held-out-content read, model execution or GPU lease occurred during this coordination change. Those checks belong to the assigned author and independent reviewer on the corrected candidate. Existing reports/findings remain immutable; new publication and dispatch receipts will bind this report's actual commit separately. Normal owned GitHub publication follows this report; no additional user permission is pending.
