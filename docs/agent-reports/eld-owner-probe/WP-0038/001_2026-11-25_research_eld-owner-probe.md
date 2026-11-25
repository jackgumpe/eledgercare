# WP-0038 / 001 — Exact signed support equations for ledger discrepancies

| Report metadata | Value |
| --- | --- |
| Reservation | [WP-0038 / 001](https://github.com/jackgumpe/eledgercare/blob/0e31fd950c48a6548d19595b2cec326ce79021fe/INDEX.md#wp-0038-synthetic-arithmetic-ambiguity-comparison) |
| Report path | `docs/agent-reports/eld-owner-probe/WP-0038/001_2026-11-25_research_eld-owner-probe.md` |
| Category / author / publisher | Research / eld-owner-probe / eld-owner-probe |
| Session and configuration | Native Codex thread `01a2117e-a21e-7811-8289-093475101f1e`. The coordinator recorded initial turn configuration `gpt-6.2-astra`, `xhigh`. Service-side execution identity and effort lack separate attestation. |
| Execution environment | Local Windows PowerShell, Python 3.12.10, isolated mode, standard library, sequential CPU |
| Timestamp | 2026-11-25T07:36:16Z |
| Repository / branch / worktree | `jackgumpe/eledgercare` / `research/wp-0038-d53` / `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w038-author` |
| Base revision | `0e31fd950c48a6548d19595b2cec326ce79021fe` |
| Deliverable revision | `e6cc29548480c8d6c0e364b6cab7e1a39528e6e4` |
| Raw evidence / scored handoff | `5dfb081694470a3d6a681fefe07e6bebcb441f98` / `843fe0aad3a04025c8a18553c8e9b9f3d5abf19d` |
| Previous report / related review | First author report in WP-0038. Independent review is reserved as WP-0038 / 002. |
| Status / next owner | Ready for review / eld-rd-reviewer, then eld-coordinator |

## Summary

The two frozen solvers agreed on every complete signed answer across 288 generated cases and 20 observations for 11 named assertions. Only 71 of 282 generated nonempty injections had a unique explanation. Another 205 had several finite explanations and six admitted infinitely many. Of six clean controls, five had only the empty support. The one-row OCR-read control also allowed a common shift of both balances by any nonzero integer. All six controls and all 282 injections retained their originating explanation. These are author observations on constructed integer ledgers. [Keyed grid](https://github.com/jackgumpe/eledgercare/blob/843fe0aad3a04025c8a18553c8e9b9f3d5abf19d/docs/coordination/WP-0038/results/grid.jsonl)

## Objective and acceptance criteria

Given observed amounts, balances, an observed printed total, an opening regime and any external anchor, enumerate every explanation of support size zero, one or two. Errors are signed observed-minus-true integer cents. Preserve every admissible alternative. Reject a conflicting trusted opening before residual computation. Compare against the independent reconstruction, all five one-row residual regimes in both domains and the named examples under the frozen scores. This author had access to the public six-page brief, including its examples. Both sources and first raw results froze before the coordinator disclosed the keyed results. [Assignment](https://github.com/jackgumpe/eledgercare/blob/0e31fd950c48a6548d19595b2cec326ce79021fe/docs/coordination/WP-0038/assignment.md) · [Dispatch and separation record](https://github.com/jackgumpe/eledgercare/blob/843fe0aad3a04025c8a18553c8e9b9f3d5abf19d/docs/coordination/WP-0038/dispatch.json)

## Change inventory

| Revision or resource | Added paths and effects |
| --- | --- |
| Source candidate | `docs/research/WP-0038/solver.py` adds the pure `solve(observed)` function, ordered constraint columns and integer elimination on pairs. This is the entire base-to-deliverable diff. |
| Subsequent raw evidence | `docs/research/WP-0038/evidence/run-01/outputs.jsonl`, `runtime.json` and `.gitattributes` in the same directory. The two filename-specific attributes preserve the original operator bytes in Git. |
| External effects | The authorized operator read the copied shuffled batch and created the two original files under `C:/Users/jackg/eLedgerCare-Speed/WP-0038/author/run-01`. The source and evidence were published to the owned branch. |
| Subsequent report metadata | This reserved report only. |

## Decisions and proof

For row i, the residual is observed closing minus previous balance minus amount. The final coordinate D is the sum of amounts minus the printed total. Each amount column thus has −1 in its row and +1 in D. Each balance column contributes +1 at its closing row and −1 at its succeeding row wherever these rows exist. The total column contributes −1 in D. A consistent trusted opening removes the opening column. A conflict returns before the code even reads the amounts.

Write y for the residual vector. The empty support is admissible exactly when y is zero. On a singleton support every column has a unit pivot, fixing its only possible coefficient. The code checks all rows and requires a nonzero coefficient. On a pair with columns a and b, use the first unit pivot of a to express the two errors as (u+vc,c) with integer u and v. Every row then imposes (aᵢv+bᵢ)c = yᵢ−aᵢu. A zero multiplier requires a zero right side. Each nonzero multiplier must yield the same integral quotient. Such a quotient fixes the unique solution on this support, subject to both coordinates being nonzero.

If all multipliers vanish, the columns are parallel. Amount columns have distinct row positions and a total component. Only the total column has just a total component. Interior balance columns touch distinct consecutive row pairs, and endpoints touch opposite ends. Thus the only parallel pair occurs when the opening is mutable and one row makes both endpoints touch the same row. Here D must vanish and r = −β₀+β₁. Taking c=β₁ gives (β₀,β₁)=(c−r,c) for every integer except 0 and r. These two exclusions coincide when r=0. This derives the complete family directly from the support equations. Each finite support is visited once in coordinate order. An observation may still admit many other supports.

For every returned error vector x, subtracting x from the observation yields a balanced ledger since its residual is y−Ax=0. Conversely every balanced ledger agreeing with the observations outside an exact support gives one solution by taking the signed difference. Both maps preserve the anchor, and are inverses. This establishes the intended equivalence to balanced-ledger reconstruction for each support, including the infinite family. [Frozen source](https://github.com/jackgumpe/eledgercare/blob/e6cc29548480c8d6c0e364b6cab7e1a39528e6e4/docs/research/WP-0038/solver.py)

## Verification

The initial turn was interrupted before any source commit or CPU lease. The coordinator resumed the same role thread in the same worktree. `git status --short --branch` and `git rev-parse HEAD` had confirmed the clean reservation. The author read all six pages of the Downloads brief and verified SHA-256 `fcdf926d8474b4e67fd9266d0083b43cad967b3671eda5427ba9d47b348e204d`. The candidate passed `git diff --cached --check`, was committed, and returned an empty `git status --porcelain=v1` before execution.

The coordinator released one command at integration revision `79409eac12b85fcb2b037e6d7b6c917606cab1cc`. It ran once from the owned worktree and exited 0.

```powershell
python -I -B '../../eledgercare/docs/coordination/WP-0038/operate.py' --candidate e6cc29548480c8d6c0e364b6cab7e1a39528e6e4 --solver docs/research/WP-0038/solver.py --observations C:/Users/jackg/eLedgerCare-Speed/WP-0038/author/observations.jsonl --input-sha 867cbfc7ca3a8945cd10c9987be578a48b8fe885bf9301d2ad1358e493ace40d --out C:/Users/jackg/eLedgerCare-Speed/WP-0038/author/run-01
```

| Check | Actual result |
| --- | --- |
| Interpreter and source SHA-256 | Python executable `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`. Solver working bytes `9e30cb2be3f5a4813ab4fa036804edf3cbf8e38f721568e7efeb62141267dd00`. |
| Operator | 308 sequential solves, zero exceptions. Batch wall 16.9085 ms including serialization and output. Process CPU 15.625 ms. Sum of solve times 13.756 ms. Grid median 48.5 µs, 95th percentile 63.0 µs. Named median 33.85 µs, 95th percentile 60.4 µs. |
| Raw evidence freeze | Git initially proposed text normalization. After applying the evidence attributes, a byte comparison using `git show :<path>` against both scratch and working files passed. Outputs 68,545 bytes, SHA-256 `bd45348a78d35604b56a9d2ce5c3e0d3916b834c9fb9ec0e969b9db3c0182c1d`. Runtime 914 bytes, SHA-256 `a1bce6bfb6dd6d130cf246990f59c56deb041ea7727aa7c367e2674a46c98d96`. |
| Generated grid | 6 clean, 33 single, 249 paired. Across the 36 one-row grid cases, the five regimes (zero, row only, total only, opposite, generic) occurred 2/5/3/3/10 times for OCR and 1/2/2/2/6 for trusted openings. All signed comparisons passed. |
| Named assertions | 20/20 agreed across 11 names, including 11 observations that also occur in the grid. C9a retained five pairs, off-grid C9b retained three. C1’s conflicting input and C9c both skipped the solve, with null residuals and zero candidates. The consistent trusted C1 control returned only clean. |
| Author readback of scored files | Read the two JSONL blobs with `git show 843fe0aad3a04025c8a18553c8e9b9f3d5abf19d:docs/coordination/WP-0038/results/<section>.jsonl` under Python `-I -B`. Subtracted each finite/clean signed answer and checked every row, total and trusted opening. All 668 grid reconstructions and 36 named reconstructions balanced. All seven grid and two named families matched the derived form and exclusions. Injection membership passed for all 288 grid and all 18 admitted named inputs. No signed disagreement, reported scoring/contract failure or exception. |
| Evidence publication | The packet `push.ps1 -ExpectedHead 5dfb081694470a3d6a681fefe07e6bebcb441f98` exited 0 and read back that full remote branch head. |

## Review map and limits

The per-call output records carry observed results and timing. The coordinator's named rows include the keyed examples, both paths' times, and conflict outcomes. The signed error model assumes correctly associated integer-cent cells and at most two affected coordinates. The physical frequency of these cases, OCR repair accuracy and larger ledgers' measured runtime remain open. The trial used synthetic CPU inputs only. No winning repair was applied. [Raw evidence](https://github.com/jackgumpe/eledgercare/tree/5dfb081694470a3d6a681fefe07e6bebcb441f98/docs/research/WP-0038/evidence/run-01) · [Named assertions](https://github.com/jackgumpe/eledgercare/blob/843fe0aad3a04025c8a18553c8e9b9f3d5abf19d/docs/coordination/WP-0038/results/named.jsonl) · [Scored summary](https://github.com/jackgumpe/eledgercare/blob/843fe0aad3a04025c8a18553c8e9b9f3d5abf19d/docs/coordination/WP-0038/results/summary.json)

## Handoff

Independent review of the frozen source, evidence, mathematical argument and scoring belongs to eld-rd-reviewer. Integration and final disposition belong to eld-coordinator. The author will hand off the report publication SHA after remote verification.
