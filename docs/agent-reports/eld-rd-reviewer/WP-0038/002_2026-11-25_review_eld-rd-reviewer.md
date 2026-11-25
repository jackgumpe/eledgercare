# WP-0038 / 002 — Independent review of signed arithmetic ambiguity

| Report metadata | Value |
| --- | --- |
| Author, publisher, category | eld-rd-reviewer · eld-rd-reviewer · review |
| Path and slot | `docs/agent-reports/eld-rd-reviewer/WP-0038/002_2026-11-25_review_eld-rd-reviewer.md` · [reservation /002](https://github.com/jackgumpe/eledgercare/blob/0e31fd950c48a6548d19595b2cec326ce79021fe/INDEX.md#wp-0038-synthetic-arithmetic-ambiguity-comparison) |
| Timestamp | 2026-11-25T07:42:05Z |
| Actual session | Native Codex thread `01a2117e-d229-7ec2-8f8c-3164fc96cd12`. The coordinator confirmed launch configuration `gpt-6.2-astra`, `xhigh` from the original turn context. No separate backend attestation. |
| Environment | Windows PowerShell, Python 3.12.10, stdlib, sequential CPU |
| Repository and ownership | `jackgumpe/eledgercare` · `review/wp-0038-d53` · `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w038-review` |
| Base, own source, own frozen raw evidence | `0e31fd950c48a6548d19595b2cec326ce79021fe` · `779d0cf4e27e7fafa0b7b4b727b136a2481f90e4` · `5d55b11cd9b26369199a3944e533c108010f2311` |
| Author source, raw evidence, /001 | `e6cc29548480c8d6c0e364b6cab7e1a39528e6e4` · `5dfb081694470a3d6a681fefe07e6bebcb441f98` · `4dee32e61ef23463f703020de3bf3c9ebd0978a0` |
| Coordinator driver, scorer, keyed results | `3494da54b614e0bf6b5ce779c279d4fae457c483` · `bd1ce0964e510c14ff7398ac452dbe48639962d8` · `843fe0aad3a04025c8a18553c8e9b9f3d5abf19d` |
| Status and next owner | Accepted for the bounded arithmetic claims below · eld-coordinator for final disposition and public byte verification |
| Previous report | First reviewer report in WP-0038. Reviewed [author /001](https://github.com/jackgumpe/eledgercare/blob/4dee32e61ef23463f703020de3bf3c9ebd0978a0/docs/agent-reports/eld-owner-probe/WP-0038/001_2026-11-25_research_eld-owner-probe.md). |

## Finding and scope

Both routes returned the same full signed answer for all 288 generated cases and all 20 observations across 11 named assertions. Of 282 generated injections, 71 had a unique explanation, 205 had multiple finite explanations and six admitted infinitely many. Of the six controls, five had a unique explanation and one admitted infinitely many. All originating hypotheses were present. The two named trusted-opening conflicts were rejected before residual or candidate computation. [Grid](https://github.com/jackgumpe/eledgercare/blob/843fe0aad3a04025c8a18553c8e9b9f3d5abf19d/docs/coordination/WP-0038/results/grid.jsonl) · [Named outcomes](https://github.com/jackgumpe/eledgercare/blob/843fe0aad3a04025c8a18553c8e9b9f3d5abf19d/docs/coordination/WP-0038/results/named.jsonl)

I independently reviewed the support-equation author's source, evidence and /001 claims, the coordinator's driver, fixture generation, scoring and keyed results, and the supplied D5.3/D5.4 arguments. I wrote the reconstruction route and report its execution as author verification. Both agents knew the public brief and its examples. I saw the other route's source, raw answers and scorer only after both first raw outputs froze. The solver itself received five observed-input fields. The driver and both sources show that injection labels and oracle information were outside the call. [Assignment](https://github.com/jackgumpe/eledgercare/blob/0e31fd950c48a6548d19595b2cec326ce79021fe/docs/coordination/WP-0038/assignment.md) · [Operator](https://github.com/jackgumpe/eledgercare/blob/3494da54b614e0bf6b5ce779c279d4fae457c483/docs/coordination/WP-0038/operate.py)

## Mathematical review

**D5.3.** The author's amount column has −1 in its body row and +1 in D. The successive-balance columns encode the signed differences between neighboring rows, and T has −1 in D. Restore the negative sum of all rows as a ground row. Each column then describes a directed edge with opposite unit endpoints. The amount and T columns have determinant of magnitude one in the reduced matrix by expansion along T. Every square incidence minor is 0 or ±1 by induction. Expansion handles a column with at most one entry. If every column retains both entries, summing all rows gives zero.

A difference between two hypotheses of size at most two is an integral circulation on at most four active edges. For n≥2, the row-to-D amount edges, successive-row balance edges, endpoint-to-ground edges and D-to-ground total edge form a simple graph. The consistent trusted domain deletes the opening edge. Every active vertex has degree at least two by conservation. Two cyclic components would require six edges. In the connected active graph, three vertices allow just a triangle, and four vertices require exactly four edges and degree two everywhere. Conservation fixes a single integer multiplier around either cycle. The one-row trusted graph likewise allows just a triangle. On one OCR row, setting both discrepancies to zero yields the entire kernel in order (A,O,B,T),

```text
(t,s,s+t,t), for integers s,t.
```

For t=0 and s≠0, the difference has two changed cells. For t≠0, it has three when s is 0 or −t, and four otherwise. The latter includes composite changes invisible to a triangle-only account. The zero vector occurs at s=t=0. This proves the brief's support classification under the stated domain.

**D5.4 and completeness.** For each exact support S, extend its signed errors by zero outside S. Subtract them from the measurements to recover a true ledger. Its residual is the measured residual minus the residual of the error vector. It balances precisely when the support equations hold. Conversely subtract any such balanced ledger from the measurements and recover the same signed errors, including exact nonzero membership on S. The trusted opening stays fixed. These inverse maps include the empty support and every integer point of an affine family.

The author's code realizes the first map by checking a unit pivot against all remaining rows on singletons. On pairs it expresses the first error as an integer affine function of the second. All nonzero coefficients in the remaining equations must give the same integral quotient, and zero coefficients must have zero remainder. Exact supports discard zero coefficients in the solution. The sole rank-one pair is the two opposite endpoint-balance columns on one OCR row. Its total discrepancy must be zero. With c equal to the closing error the errors are (c−r,c), where c ranges over all integers except 0 and r. This also proves completeness for arbitrary signed values outside the fixture magnitudes. [Reviewed support solver](https://github.com/jackgumpe/eledgercare/blob/e6cc29548480c8d6c0e364b6cab7e1a39528e6e4/docs/research/WP-0038/solver.py)

My implementation removes the hypothesized cells, then reconstructs true balances by propagating observed differences. A fixed amount joins consecutive balance vertices, a fixed total joins the endpoints, and a fixed balance joins its vertex to the monetary origin. A cycle inconsistency rules out the support. Within a connected component all balances are determined up to translation, so a connected graph fixes every missing reading by subtraction. For n≥2, any proper nonempty subset of rim vertices has at least one spoke to the origin and at least two crossing rim edges. The whole rim has at least three spokes. Removing two edges therefore preserves connectivity. On one row the two parallel amount/total edges fix the endpoint difference if both remain and agree. Only loss of both balance readings can detach the endpoints as a group. Translating their common component recovers exactly the family above. This gives an independent implementation argument for complete enumeration. [Reconstruction solver](https://github.com/jackgumpe/eledgercare/blob/779d0cf4e27e7fafa0b7b4b727b136a2481f90e4/docs/reviews/WP-0038/solver.py)

## Executed verification

I read all six pages of advisory edition 03 using `pdftotext -layout` and verified SHA-256 `fcdf926d8474b4e67fd9266d0083b43cad967b3671eda5427ba9d47b348e204d`. The interrupted turn resumed on the original thread and branch at the clean reservation. Python 3.12.10 parsed the source and `git diff --cached --check` passed before the source commit. The coordinator's sole lease at `8033d0e85522d603b1a2a7590d9013d45b93024b` authorized this single invocation from the review worktree.

```powershell
python -I -B '../../eledgercare/docs/coordination/WP-0038/operate.py' --candidate 779d0cf4e27e7fafa0b7b4b727b136a2481f90e4 --solver docs/reviews/WP-0038/solver.py --observations C:/Users/jackg/eLedgerCare-Speed/WP-0038/review/observations.jsonl --input-sha 867cbfc7ca3a8945cd10c9987be578a48b8fe885bf9301d2ad1358e493ace40d --out C:/Users/jackg/eLedgerCare-Speed/WP-0038/review/run-01
```

The driver verified the candidate, clean status, interpreter digest and input digest. It exited 0. Per-call timers bracketed only `solve`, with batch wall time also covering serialization and output. Both schedules used a single sequential process. Observed times describe these two invocations. [First reconstruction output and runtime](https://github.com/jackgumpe/eledgercare/tree/5d55b11cd9b26369199a3944e533c108010f2311/docs/reviews/WP-0038/evidence/run-01) · [First support output and runtime](https://github.com/jackgumpe/eledgercare/tree/5dfb081694470a3d6a681fefe07e6bebcb441f98/docs/research/WP-0038/evidence/run-01)

| Runtime over 308 observations | Support equations | Reconstruction |
| --- | ---: | ---: |
| Sum of solve times, ms | 13.7560 | 31.5212 |
| Batch wall, ms | 16.9085 | 34.9268 |
| Batch process CPU, ms | 15.6250 | 31.2500 |
| Grid median / p95, µs | 48.50 / 63.00 | 111.95 / 157.10 |
| Named median / p95, µs | 33.85 / 60.40 | 71.50 / 143.90 |
| Exceptions | 0 | 0 |

After both raw freezes I extracted `score.py` and `fixtures.py` from the pinned scorer blobs with `git cat-file blob` to the review scratch directory. The following command exited 0. Its three files matched the published Git blobs byte for byte. SHA-256 values were `31c7caa313ea4f1d2f559d2df792f50c8790d8821e4345ae45d63ab4b72319eb` (grid), `482719a0dcc129524adb8644fe424cd541a6549921b5fdfc89e7c2a98b1687d8` (named) and `a6ef2fdc19c9f3fb98dfcb812aa6c1696227b2bfba34c144c6702cdb7eee6fda` (summary). [Scorer source](https://github.com/jackgumpe/eledgercare/blob/bd1ce0964e510c14ff7398ac452dbe48639962d8/docs/coordination/WP-0038/score.py) · [Scored summary](https://github.com/jackgumpe/eledgercare/blob/843fe0aad3a04025c8a18553c8e9b9f3d5abf19d/docs/coordination/WP-0038/results/summary.json)

```powershell
$scratchDir='C:/Users/jackg/eLedgerCare-Speed/WP-0038/review/score-reproduction'
python -I -B "$scratchDir/score.py" 5dfb081694470a3d6a681fefe07e6bebcb441f98 5d55b11cd9b26369199a3944e533c108010f2311 "$scratchDir/results"
```

I also used a separate stdlib readback via `python -I -B -`. It joined all 308 keyed records by slot to the executed observation file and both raw Git blobs, checked every complete signed answer by canonical JSON, and independently regenerated all six sets of injection patterns. Each admitted finite/clean reconstruction satisfied every true balance increment, closing minus opening equaled total, and every trusted anchor was preserved. The audit counted 668 grid and 36 named finite/clean reconstructions, plus seven grid and two named family representations. It recovered the originating hypotheses as follows.

| Evaluation set | Clean | Finite signed | Member of family | Anchor denied |
| --- | ---: | ---: | ---: | ---: |
| Grid, 6 controls + 33 singles + 249 pairs | 6 | 279 | 3 | 0 |
| Named, 20 observations under 11 assertions | 1 | 16 | 1 | 2 |

All 42 admitted one-row observations matched separate readback of the five signed two-cell formulas, exact singleton conditions, clean flag and family domain. With regime order (zero, row only, total only, opposite, generic), the one-row grid counts were (2,5,3,3,10) for OCR and (1,2,2,2,6) for trusted. C2 OCR had two singles, one signed pair and the full family excluding 0 and 6. The six inherited multi-row examples C3–C8 matched the complete signed table in both domains. Eleven named observations reused grid inputs.

C1's shifted OCR observation admitted clean and the family F(0), including its injected shift at c=6. Its consistent trusted version admitted only clean. Opening 106 against anchor 100 produced null residuals, `solve_skipped=true` and no candidates. C9a, grid entry `grid/OCR_OPEN/1/007`, returned (A1,B0)=(6,10), (A1,B1)=(6,−10), (A1,T)=(16,10), (B0,T)=(16,−6) and (B1,T)=(−16,−6). C9b returned the three pairs omitting B0 and preserved its off-grid injection (6,−10). Both had (r,D)=(−16,6). C9c's opening 110 conflicted with 100 and produced the same pre-solve rejection as C1. Source inspection confirmed that both guards precede all residual and support calculations.

## Inventory, limitations and handoff

The entire base-to-source diff adds `docs/reviews/WP-0038/solver.py`. The next commit adds `docs/reviews/WP-0038/evidence/run-01/outputs.jsonl`, `runtime.json` and `.gitattributes` in that directory. Git's default text rules would have changed the runtime blob on staging. The scoped attributes preserved the original bytes, verified by comparing staged object IDs to `git hash-object --no-filters` for both scratch files. Output SHA-256 is `09017a3276eaf3c450b41d0dd677e87b8f9d4f364f2dbdb9e0162d3ee1a9fcff`, runtime SHA-256 is `42fd260cef216b0ad38190c9eb4f134288e3f1e34ddbc7dfd6e11c7ecac0f4e6`. The later report commit adds this reserved report only. Owned scratch retains the first operator output and scorer reproduction. The packet push helper verified the source and raw evidence against the owned remote ref.

The frozen interface supplies n≥1, recognized domains, signed integer cents, n+1 balances and a matching-type anchor. On this interface there were zero scoring or input/output contract failures. Source inspection shows a difference outside it. The support solver checks the domain before the anchor guard and checks the vector lengths after it. The reconstruction solver assumes these input preconditions and treats an unknown domain as untrusted. Neither route supplies a printed-money parser. Malformed or off-contract inputs were untested. The algebra assumes correctly bound rows and at most two changed cells. No model execution, OCR, physical reconstruction, confidence estimate or hardware comparison was performed.

I accept the reviewed author implementation and its bounded /001 claims and the coordinator's scored result at the revisions above. The coordinator retains independent inspection of my route, integration, immutable public-byte checks and final disposition. There is no unresolved disagreement.
