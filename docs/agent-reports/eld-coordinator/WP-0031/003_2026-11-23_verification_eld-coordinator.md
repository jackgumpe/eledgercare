# WP-0031 / 003 · Bounded write-8 CPU replay

Both probes moved the literal Alder-minus-Cedar margin toward Cedar when the Alder declaration replaced the Cedar declaration at either fixed incoming prefix. With all incoming matrices zeroed, the direction reversed for M1 and persisted for M3. The non-author independently reconstructed all twelve cells and matched their score bytes, reads, matrices and contrasts. I accept these measurements for the one shared development opening. [Author /001](https://github.com/jackgumpe/eledgercare/blob/013499d9fdf5b19e587c91cd93dfd502c0448e04/docs/agent-reports/eld-owner-probe/WP-0031/001_2026-11-23_research_eld-owner-probe.md) · [Independent review /002](https://github.com/jackgumpe/eledgercare/blob/91d99471ff5d2a279e18525828d89b9f92fdd65b/docs/agent-reports/eld-rd-reviewer/WP-0031/002_2026-11-23_review_eld-rd-reviewer.md) · [Reconciled binary32 scores and binary64 contrasts](https://github.com/jackgumpe/eledgercare/blob/8962868f6476ce26b4c108daa960a13265db10cc/docs/coordination/WP-0031/reconciliation.json)

| Record | Binding |
| --- | --- |
| Author, publisher and category | eld-coordinator · verification · accepted and closed |
| Reservation and report path | 003 at 74f23b10d428acc3477db6ce4af7eb663e28d9f4 · docs/agent-reports/eld-coordinator/WP-0031/003_2026-11-23_verification_eld-coordinator.md |
| Session | Native Codex on Windows, thread 01a20a53-eec1-72c1-864c-9f8be8f4aff5, launch configuration gpt-6.2-astra / xhigh |
| Publication prepared | 2026-11-23T22:26:38Z |
| Repository, branch and worktree | Public jackgumpe/eledgercare · coordination/bootstrap · C:/Users/jackg/Asp.net Projects/eledgercare |
| Accepted base | 40fa358cd3c94efbf8fe9df93f188e7c02e1c6e4 |
| Disposition deliverable | 8962868f6476ce26b4c108daa960a13265db10cc |
| Author source, evidence and report | 5e1a464a38ad4213b94b3b25695bd70d9054a6a3 · 8f31cc66c4878ca086fa5da1498c4a73ed6a6306 · 013499d9fdf5b19e587c91cd93dfd502c0448e04 |
| Reviewer completed replay, comparison, evidence and report | 6260131f85ec3844acb54326799c7f6d48115323 · 2a1d1aa16be76fcb40a636b71e6cbe517cde38f3 · 6ee777088c7d6121611091556246bb964c5a4227 · 91d99471ff5d2a279e18525828d89b9f92fdd65b |
| Previous record and handoff | First coordinator report in this packet. The lane stops at the verified public closure. |

## Measurement

Each cell lists raw scores in literal Alder, Cedar order, followed by their difference and the change from the row's write-7 margin. AA and CC are native controls. AC and CA are retrospective interventions. All reads used the frozen eventual query at depth zero, with both names registered. All twelve were below the original score and gap thresholds.

### M1

| Incoming prefix and margin at write 7 | Alder declaration | Cedar declaration |
| --- | --- | --- |
| Alder · +0.025722913444042206 | **AA** · Cedar first<br>Scores -0.045244865119457245, +0.014514945447444916<br>Margin -0.05975981056690216<br>Change -0.08548272401094437 | **AC** · Cedar first<br>Scores +0.020283853635191917, +0.06048865616321564<br>Margin -0.04020480252802372<br>Change -0.06592771597206593 |
| Cedar · +0.028679117560386658 | **CA** · Cedar first<br>Scores -0.03879733383655548, +0.01913132146000862<br>Margin -0.0579286552965641<br>Change -0.08660777285695076 | **CC** · Cedar first<br>Scores +0.030345000326633453, +0.06809929758310318<br>Margin -0.03775429725646973<br>Change -0.06643341481685638 |

### M3

| Incoming prefix and margin at write 7 | Alder declaration | Cedar declaration |
| --- | --- | --- |
| Alder · +0.0011497139930725098 | **AA** · Cedar first<br>Scores +0.14160983264446259, +0.14292049407958984<br>Margin -0.0013106614351272583<br>Change -0.002460375428199768 | **AC** · Alder first<br>Scores +0.12284263968467712, +0.10693581402301788<br>Margin +0.01590682566165924<br>Change +0.014757111668586731 |
| Cedar · +0.0020220577716827393 | **CA** · Cedar first<br>Scores +0.142293781042099, +0.1432039588689804<br>Margin -0.0009101778268814087<br>Change -0.002932235598564148 | **CC** · Alder first<br>Scores +0.12342783063650131, +0.10698604583740234<br>Margin +0.01644178479909897<br>Change +0.01441972702741623 |

### Contrasts and empty-memory control

DA and DC compare declaration donors at the two fixed prefixes. PA and PC compare prefixes at the two fixed declarations. I is the difference between the two donor contrasts. The native contrast compares AA with CC.

| Probe | DA | DC | PA | PC | Interaction I | Native contrast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| M1 | -0.01955500803887844 | -0.020174358040094376 | -0.0018311552703380585 | -0.0024505052715539932 | +0.0006193500012159348 | -0.022005513310432434 |
| M3 | -0.0172174870967865 | -0.017351962625980377 | -0.0004004836082458496 | -0.0005349591374397278 | +0.00013447552919387817 | -0.017752446234226227 |

Both donor contrasts were negative on each probe. Both interactions met the inclusive 5% trigger. The empty controls retained the common discrete state and zeroed all matrices. D0 is the literal owner margin on 0A minus that on 0C.

| Probe | Absolute I | 5% limit | 0A margin | 0C margin | D0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | +0.0006193500012159348 | +0.0010087179020047189 | +0.07575222849845886 | +0.023101642727851868 | +0.052650585770606995 |
| M3 | +0.00013447552919387817 | +0.0008675981312990189 | -0.04664275050163269 | -0.012705639004707336 | -0.033937111496925354 |

M1 ranked Cedar first in all four populated cells. Its donor contrast changed sign when the incoming matrices were cleared. This supports inspecting how populated memory affects the declaration update and readout. M3 ranked Cedar first for the Alder donor and Alder first for the Cedar donor on both populated prefixes. Its negative donor contrast survived empty memory, supporting inspection of the full declaration projection and readout. The small positive interactions coexist with negative prefix effects on both probes. Even an exactly zero interaction could coexist with a nonzero additive prefix effect.

The two binder lengths share this opening and supply one specimen. The intervention changes the full donor bundle, including pooled features and a box coordinate. These observations cannot isolate a particular projection, box coordinate, residual term or earlier span. Held-out accuracy remains unmeasured.

## Source and gate reconciliation

The frozen active lane computes residual = v − a·(old @ k), then updated = a·old + b·outer(residual,k). Page 4 of the order omits the leading multiplier on old. Both operators invoked the unchanged frozen Memory.write. The reviewer independently compared its output with the actual native expression, including FP32 operation order. The empty-matrix identity holds in either written form.

Both native prefixes were independently built through write 7. The observed events entered both owner names at write 3. At write 8 both operators deep-cloned the recipient, applied the donor's OPEN_LEDGER event, verified unchanged controller/registry, and recomputed the write from the donor's full-window projection and the recipient's matrices. The named declaration boxes differ at y=486/487. Saved prefix matrices total 1,179,648 bytes. They and the full discrete state matched across implementations.

Native reads at writes 7 and 8 matched the archived score bytes, query/read digests, matrices and discrete controls. The archived steps associate with the ordered-anchor digest through their run in bindings.json. Both fresh twin tensors matched each other and that binding. The second horizon matched the same opening. Only after those controls passed did either operator interpret crossed reads. The reviewer reprojected the eventual query from its archived final window, while the author restored its archived FP32 bytes.

## Verification and preservation

| Check | Command or operation | Result |
| --- | --- | --- |
| Admission | Verify the six-page PDF digest and lineage. Inspect live refs, worktrees, ledgers and history. Run git merge --ff-only origin/coordination/bootstrap in the primary checkout. | Identity and lineage matched. No duplicate assignment found. The owner-only accepted INDEX change preceded the reservation and public visibility correction. |
| Author | Qualified WP-0030 venv python.exe -I -B docs/research/WP-0031/replay.py 5e1a464a38ad4213b94b3b25695bd70d9054a6a3 | One CPU thread in each pool, deterministic CPU build. Four native, four crossed and four triggered empty controls. |
| Reviewer | Same qualified venv, -I -B docs/reviews/WP-0031/replay.py 6260131f85ec3844acb54326799c7f6d48115323 and separately frozen comparison source 2a1d1aa16be76fcb40a636b71e6cbe517cde38f3 | The first reviewer candidate stopped before importing torch because it required admission in the earlier WP-0028 manifest. The corrected source checked the subsequent WP-0029 admission. Full reproduction and exact comparison passed. The original failure is preserved. |
| Root | python -B docs/coordination/WP-0031/reconcile.py 8f31cc66c4878ca086fa5da1498c4a73ed6a6306 docs/research/WP-0031/evidence 6ee777088c7d6121611091556246bb964c5a4227 docs/reviews/WP-0031/evidence/replay.json docs/coordination/WP-0031/reconciliation.json | Recomputed margins from FP32 bytes using exact rational differences. Every increment, both forms of I, both native decompositions, both trigger decisions and both D0 values matched. |
| Integration | Verify owned live tips, build each disjoint integration tree with git merge-tree --write-tree, verify all worker blobs, advance primary with git merge --ff-only. | Both independent histories retained. Changes since acceptance are restricted to WP-0031 and the two routing files. |
| Integrity | Compare historical worktrees, working-file hashes, stash, recovery copies and bundle against the succession snapshot. | All 94 pre-existing worktrees and 73 working-file identities preserved. The primary package file SHA-256 is 6af72a0583bf4a640633ac17b0cc3e9adc83a5f4df12d09b01ae70dcec0546e0. Stash bcc4b085be6b5f2c64bca52443f410398db15aa1 is intact. |

The next metadata commit records live publication and byte-level HTTP downloads using verify_publication.py. The coordinator verifies the receipt at the final head as well. The task used owned branches, worktrees and packet scratch. The previous CPU environment was read-only. Replay stopped immediately after write 8. GPU execution, OCR, held-out inputs, training and product changes were outside this release.

## Change inventory

The following paths are the complete accepted-base-to-deliverable diff, including the independent authors' integrated files. This report and its routing/receipt metadata are subsequent publications.

~~~text
CURRENT.md
INDEX.md
docs/agent-reports/eld-owner-probe/WP-0031/001_2026-11-23_research_eld-owner-probe.md
docs/agent-reports/eld-rd-reviewer/WP-0031/002_2026-11-23_review_eld-rd-reviewer.md
docs/coordination/WP-0031/assignment.md
docs/coordination/WP-0031/decision.json
docs/coordination/WP-0031/dispatch.json
docs/coordination/WP-0031/reconcile.py
docs/coordination/WP-0031/reconciliation.json
docs/coordination/WP-0031/verify_publication.py
docs/research/WP-0031/evidence/M1-Alder-write7.f32
docs/research/WP-0031/evidence/M1-Cedar-write7.f32
docs/research/WP-0031/evidence/M1.json
docs/research/WP-0031/evidence/M3-Alder-write7.f32
docs/research/WP-0031/evidence/M3-Cedar-write7.f32
docs/research/WP-0031/evidence/M3.json
docs/research/WP-0031/evidence/inputs.json
docs/research/WP-0031/evidence/runtime.json
docs/research/WP-0031/experiment.py
docs/research/WP-0031/inputs.py
docs/research/WP-0031/replay.py
docs/reviews/WP-0031/archive.py
docs/reviews/WP-0031/compare.py
docs/reviews/WP-0031/evidence/comparison.json
docs/reviews/WP-0031/evidence/prefixes.zip
docs/reviews/WP-0031/evidence/preflight-failure.txt
docs/reviews/WP-0031/evidence/replay.json
docs/reviews/WP-0031/replay.py
~~~
