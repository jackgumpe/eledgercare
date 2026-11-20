# WP-0019 / 001 · Fixed-crop policy and exposed Stage 1 results

| Report metadata | Binding |
| --- | --- |
| Report | `docs/agent-reports/eld-rd-astra/WP-0019/001_2026-11-20_research_eld-rd-astra.md` |
| Sequence | [WP-0019 / 001 reservation](https://github.com/jackgumpe/eledgercare/blob/fc15d1bd3af1b4c7dfbfbf1eac2680b9ae9ac1af/INDEX.md#wp-0019-windows-ocr-fixed-crop-trial) |
| Category / author / publisher | Research · eld-rd-astra · author |
| Session | Fresh native Codex subagent `/root/crop19_astra`, Astra/xhigh requested. Applied backend and effort unexposed. Local Windows PowerShell, WP-0005 Python 3.12 environment. |
| Published UTC | 2026-11-20T19:43:17Z |
| Repository / owned branch | jackgumpe/eledgercare · research/wp-0019-crop-policy |
| Base | `fc15d1bd3af1b4c7dfbfbf1eac2680b9ae9ac1af` |
| Deliverable | `2b47c31201a14488fd835b8e6e47b2f82b5ad854`, containing source and author evidence |
| Running policy / joint execution candidate | `d62a96f8145345ce4c43544850d20fce13659879` / `9418bccd339dea1d89445f2fec93927168c7a5f0` |
| Score join / evidence packager | `3ba937fa8177a05d8d62c7b42a04bd0fa0def47a` / `b0249f272db89caa1c84f6384caaf62d8c93f03e` |
| Previous report | First report in WP-0019. Prior [WP-0018 independent witness diagnosis](https://github.com/jackgumpe/eledgercare/blob/e5cecfaf3ed762c3844aed06ba21acbabbec90d9/docs/agent-reports/eld-rd-reviewer/WP-0018/003_2026-11-20_review_eld-rd-reviewer.md). |
| Status / next owner | Ready for independent review by eld-rd-reviewer under WP-0019 / 003 |

## Summary

The frozen crop policy recovered one critical field in both run orders. On A page 50, table 1, row 2, column 2, full-page Windows OCR returned `80808479`. The crop returned the literal word `80808-479`, which the structural delimiter rule accepted. No previously correct critical field became wrong. All 23 originally correct blank cells stayed explicitly empty.

I authored the policy, paired runner and separate scoring analysis, executed constructed checks, and scored the coordinator's frozen H/A outputs. The coordinator operated all four real Windows crossovers. This is author verification on exposed regression data. The Stage 1 results meet the registered condition for a separately controlled fresh check.

## Objective and criteria

Test whether an extra same-pixel cell or prose recognition recovers a critical value without damaging a previously correct value. Keep source pixels, language, original layout and evaluator fixed. Include all expected critical fields, all explicit blanks, four historical witnesses and five nonempty reference cells without intersecting full-page words. Evaluate both AB and BA. Stage 1 requires at least one net critical recovery and zero newly wrong criticals across H and A.

## Quality and disagreement

Counts apply to the unique fields in either order. Every critical field had a selected application region. The post-score ledger joins all 36 H and 588 A reference positions individually.

| Family | Critical full → treatment | Wrong → right | Right → wrong | Wrong → wrong | Right → right | New unflagged | Remaining unflagged errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H | 11 → 11 / 19 | 0 | 0 | 8 | 11 | 0 | 8 |
| A | 158 → 159 / 252 | 1 | 0 | 93 | 158 | 0 | 84 |

| Critical-field outcome | H agreed | H disagreed | A agreed | A disagreed |
| --- | ---: | ---: | ---: | ---: |
| Right → right | 11 | 0 | 152 | 6 |
| Right → wrong | 0 | 0 | 0 | 0 |
| Wrong → right | 0 | 0 | 0 | 1 |
| Wrong → wrong | 7 | 1 | 83 | 10 |

Disagreement compares the literal field readings assembled from each recognizer's ordered words. All 20 H selections produced 19 agreements and one accepted delimiter. The 460 A selections produced 433 agreements, two accepted delimiters and 25 retained-and-flagged disagreements. Of 15 A critical fields flagged, nine remained wrong and six were correct. Two accepted critical delimiter readings remained wrong across H/A. No selected critical field had a diagnostic-only exact crop while its final value remained wrong.

All 20 H and 300 A reference cells used matched grids. Correct cells changed from 15 to 15 and 235 to 236. Correct prose lines stayed 13/16 and 237/288. The sole H ground-truth blank was unselected. Sixteen of the 22 A blanks were selected. Every blank retained its empty string, with zero missing blank observations.

Using the full emitted line or cell for the surface classification, H's eight wrong criticals comprised six character differences and two whitespace-only differences before and after. A started with 69 character differences, 20 mixed character/whitespace, three whitespace-only and two no-word readings. One character difference became exact. The scorer's critical-token test remains authoritative for correctness.

## Located witnesses

All nine positions were selected in both orders. Empty refers to an explicit empty grid value. The raw full lines, ordered words/boxes, crop-local words/boxes, translated page boxes, decisions, field locations and reference boxes are preserved for each example. [Nine individual traces](https://github.com/jackgumpe/eledgercare/blob/2b47c31201a14488fd835b8e6e47b2f82b5ad854/docs/research/WP-0019/astra/evidence/nine-fields.json)

| Position | Expected | Full | Crop | Final |
| --- | --- | --- | --- | --- |
| H p2 t1 r2 c1 | `1L8O1-493` | `IL801493` | `IL801-493` | `IL801-493`, still wrong |
| A p60 t1 r2 c2 | `0I8O1-139` | `01801-139` | `01801-139` | `01801-139`, still wrong |
| H p1 line 2 | `Docket 88L1L-631` | `Docket 88L1 L-631` | same | same, still split |
| H p2 line 2 | `Docket 880LO-977` | `Docket 880LO-977` | same | same, correct |
| A p5 t1 r5 c1 | `5-4` | empty | empty | empty |
| A p15 t1 r4 c2 | `11III-558` | empty | empty | empty |
| A p20 t1 r5 c1 | `20-4` | empty | `20—4` | empty, flagged |
| A p30 t1 r3 c2 | `11I18-710` | empty | empty | empty |
| A p30 t1 r5 c1 | `30-4` | empty | `30—4` | empty, flagged |

## Timing

Each order started its own persistent en-US WinRT process and excluded one admitted first-page warmup. A is full-only and B is full-plus-crops. Arm clocks include ready-input acquisition, independent pixel verification, recognition, layout/selection/merge, per-page evidence writes and durable final prediction. The worker startup and warmup are separately measured. Evidence-write duration has no separate timer.

| Family/order | Pages | Full seconds / pages per min | Treatment seconds / pages per min | Added ms/page | Crops/page | Startup / warmup ms | Sum of in-engine crop recognition ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H AB | 4 | 1.322 / 181.6 | 1.476 / 162.6 | 38.5 | 5.00 | 733.6 / 332.0 | 65.8 |
| H BA | 4 | 1.296 / 185.1 | 1.427 / 168.2 | 32.7 | 5.00 | 553.5 / 308.7 | 58.8 |
| A AB | 60 | 19.115 / 188.3 | 21.337 / 168.7 | 37.0 | 7.67 | 556.6 / 318.1 | 1441.2 |
| A BA | 60 | 18.455 / 195.1 | 21.575 / 166.9 | 52.0 | 7.67 | 549.5 / 315.3 | 1465.6 |

## Change inventory and decisions

All listed paths start in `docs/research/WP-0019/astra/`. The owned worktree is `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\crop19-astra`. The report path above is committed separately after this evidence freeze.

| Added paths | Purpose |
| --- | --- |
| `PROTOCOL.md`, `policy.py` | Freeze eligibility, four-pixel grid inset, 12×8 outward prose padding, overlap suppression, 32-call cap and strict structural merge. A comparison can remove spaces/hyphens only internally. An accepted value always comes from literal crop words. |
| `run.py` | Pair separate full passes using one warm worker, compare admitted/sliced bytes and raw full identities, record all application decisions, and run historical layout on the resulting projected spans and complete grids. |
| `constructed.py` | Test synthetic color pixels and words, blank and omitted cells, accepted structural changes, rejected disagreements, overlap/cap and both order paths. These checks use a test double. |
| `account.py` | After output freeze, call the unchanged scorer, map actual reference fields to detected grid cells or spans, classify transitions and retain diagnostic-only crop reads separately. |
| `preserve.py` | Verify 268 assigned output digests, both orders' page records and the post-score bundle. |
| `evidence/summary.json`, `evidence/nine-fields.json`, `evidence/post-score-files.zip` | Four timing/quality summaries, nine located traces and 20 machine-readable score/field files with per-member SHA-256. |

## Verification and review map

I used the existing interpreter `C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe` with `-B`. In the commands below, `SRC` means `docs/research/WP-0019/astra`, `DATA` means `../wp0019-data` and `KEYS` means `../wp0018-data/coordinator/inputs`, relative to my assigned worktree.

| Actual operation | Revision, result and evidence |
| --- | --- |
| `SRC/constructed.py --out DATA/astra/constructed-d62a96f` | Frozen running policy passed AB/BA. Synthetic prediction hashes were `9bcf4b9a97d1b26f74a385dda89d2090fa8744f93ae73925fb02c6f8ca0f137a` (A) and `7511ca2cada912c5929f868a69711bc771c4e8eeae01e90b8ec78d49eb155c04` (B). I also executed the ordinary run.py CLI against the same synthetic engine in `DATA/astra/constructed-cli-d62a96f`. |
| `SRC/account.py --truth KEYS/{family}/truth.json --paired DATA/coordinator/stage1/{family}-{order} --out DATA/astra/scored-{family}-{order}` | Actual H-AB, A-BA, H-BA and A-AB after root's return. Each launched the frozen scorer with `-I -B score.py TRUTH PREDICTION --out SCORE` separately for each arm. Scorer SHA-256 `1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7`. All eight scores complete with zero faults. |
| `SRC/preserve.py --stage DATA/coordinator/stage1 --scratch DATA/astra --out SRC/evidence` | All 268 files matched root's returned hashes. Durable predictions and complete score JSON were byte-identical across orders for each arm/family. All page records and field ledgers matched after dropping only PID, `recognize_ms` and `call_ms`. All 20 ZIP members passed digest and integrity checks. |
| Coordinator real crossovers | Each exited 0. Current build 26300.9974, en-US, maximum dimension 10,000. The coordinator's unchanged control had already matched the historic raw and predicted pages on 64/64. Trial return SHA-256 `9d115d9cc2942b18d0b603cdc58b566d53205b49ad61f264be671d98deac31f6`. [Frozen raw runs and receipt](https://github.com/jackgumpe/eledgercare/tree/a1aba59e7d3a645e1ddf44e599d0704aa7fe5ec1/docs/coordination/WP-0019/stage1-runs) |

The post-score ZIP SHA-256 is `7595516b59836f09ec8631a2550c47f5d05f331ef35cccd615bcc12a252f8d0c`. Its four folders contain the two complete scorer outputs, all-fields ledger, located witnesses and summary for that order. The readable summary supplies every member digest. [Frozen evidence](https://github.com/jackgumpe/eledgercare/tree/2b47c31201a14488fd835b8e6e47b2f82b5ad854/docs/research/WP-0019/astra/evidence) · [Owned source and evidence diff](https://github.com/jackgumpe/eledgercare/compare/fc15d1bd3af1b4c7dfbfbf1eac2680b9ae9ac1af...2b47c31201a14488fd835b8e6e47b2f82b5ad854)

## Limitations and handoff

One exposed recovery gives no estimate of generalization. Disagreement also flagged six correct criticals, and 84 unflagged A critical errors remained. The five absent full-page word groups still had zero exact end-to-end recoveries. The scope of my execution ended at constructed checks and post-scoring. The coordinator owns fresh key custody and execution releases. The non-author reviewer owns the independent replay and disposition. Production and historical code did not change. Normal owned-branch pushes published the source, accounting and verified evidence.
