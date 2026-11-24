# WP-0032 /003 · Accounting for the write-8 owner contrast

**Accepted after independent reproduction.** On this opening the signed key-projected subtraction changed every M1 cell from Alder-first to Cedar-first and reversed the donor contrast on both incoming prefixes. M3's empty-memory donor contrast was negative even though both effective key–query dots were positive. The Alder donor raised both candidate scores, with a larger increase for the Cedar anchor. [Author /001](https://github.com/jackgumpe/eledgercare/blob/707794967c4505131d8d8b5f9e08313d3e7ffa7f/docs/agent-reports/eld-owner-probe/WP-0032/001_2026-11-24_research_eld-owner-probe.md) · [Independent review /002](https://github.com/jackgumpe/eledgercare/blob/bbb0e63f505fb0fae151592709d39ad8afd4bd04/docs/agent-reports/eld-rd-reviewer/WP-0032/002_2026-11-24_review_eld-rd-reviewer.md) · [Full numerical reconciliation](https://github.com/jackgumpe/eledgercare/blob/fe97734d3ad68c8fea5b3d9e6bfccacc9f65711e/docs/coordination/WP-0032/reconciliation.json)

| Record | Verified binding |
| --- | --- |
| Report and reservation | docs/agent-reports/eld-coordinator/WP-0032/003_2026-11-24_verification_eld-coordinator.md · sequence 003 · reservation 537ab866bb5803328d378bc00f11f5782bb5ef00 |
| Author, publisher and category | eld-coordinator · verification · 2026-11-24T01:28:45Z |
| Environment | Native local Codex on Windows · thread 01a20a53-eec1-72c1-864c-9f8be8f4aff5 · launch configuration gpt-6.2-astra, xhigh |
| Repository | Public jackgumpe/eledgercare · coordination/bootstrap · C:/Users/jackg/Asp.net Projects/eledgercare |
| Accepted base and disposition deliverable | a9c7669f15dba6f4948e8ac83a0632c72bfc252c · fe97734d3ad68c8fea5b3d9e6bfccacc9f65711e |
| Author source, evidence and report | f17396bf4d3915b53cff0e22a37e1b928cdf2919 · e7096ca975820e2be98c912d52c1a0a731de288f · 707794967c4505131d8d8b5f9e08313d3e7ffa7f |
| Independent source, evidence, comparison source, comparison evidence and review | 6281121dd59aa1602e6fc872e9bca885bb91eeb0 · be72e777178fe627f355ad240598c14217e267e8 · 4f013c667db719aab745cba75ce672c3ef22ec74 · 0bf997ef2ac4c42801dfa6fc5d07406301431a0d · bbb0e63f505fb0fae151592709d39ad8afd4bd04 |
| Previous record and next owner | First coordinator report in WP-0032. Verified public publication completes the released packet. |

## M1 · populated owner reads

R is the retained prefix, V the direct declaration write, and E the signed key-projected subtraction. At depth zero let u be the original posting query restricted to its first 32 coordinates and epsilon-normalized, z the dot of the first 32 key coordinates with u, and h the literal Alder anchor minus the Cedar anchor. The three terms are α·old[:,0:32]·u, βz·v and −αβz·(old·k). M1’s β was 1.59436 for the Alder donor and 1.54225 for the Cedar donor. The last product uses all 128 key coordinates. Each numerator below is the dot of h with that term. The three common-denominator contributions divide those numerators by the same norm of the archived native read plus epsilon. For the omitted and restored margins the corresponding vectors are summed first and each sum is normalized once. Positive margins favor Alder.

| Prefix / donor | R, V, E numerators | R, V, E contributions on common denominator | Omitted numerator / margin | Restored numerator / native margin |
| --- | ---: | ---: | ---: | ---: |
| AA | +0.013049887, +0.039382709, -0.094028881 | +0.018748285, +0.056579663, -0.135087773 | +0.052432596 / +0.061358130 | -0.041596285 / -0.059759811 |
| AC | +0.013046487, +0.004628658, -0.040085922 | +0.023405333, +0.008303790, -0.071913947 | +0.017675145 / +0.030528503 | -0.022410777 / -0.040204803 |
| CA | +0.014541540, +0.039382709, -0.094014325 | +0.021011981, +0.056906543, -0.135847187 | +0.053924248 / +0.063151381 | -0.040090077 / -0.057928655 |
| CC | +0.014537750, +0.004628658, -0.040091173 | +0.026230289, +0.008351432, -0.072336021 | +0.019166409 / +0.033155659 | -0.020924764 / -0.037754297 |

At each fixed prefix, subtract the Cedar donor result from the Alder donor result. The following differences use the FP64 component reconstruction. The archived native margins, after promotion of the individual FP32 scores, give restored contrasts of −0.01955500803887844 and −0.020174358040094376.

| Prefix | Omitted numerator → restored | Omitted margin → restored | Restoring E changed the margin contrast by |
| --- | ---: | ---: | ---: |
| A | +0.034757451 → -0.019185508 | +0.030829628 → -0.019555003 | -0.050384631 |
| C | +0.034757840 → -0.019165313 | +0.029995722 → -0.020174363 | -0.050170086 |

Both donor contrasts reversed before normalization. Normalizing each summed read changed the magnitude of the contrast. With E omitted, both Cedar declarations also rank Alder first.

## M3 · empty-memory owner reads

Both donors started from eight zero matrices and the common write-7 discrete state. The owner read at depth zero is βz·v. For each original lexical anchor g the reconstructed score is βz·(g·v) / (|βz|·‖v‖ + 1e−8). The alignment column gives the raw dot divided by ‖v‖+1e−8. Every pair of values is in literal Alder, Cedar order.

| Donor | z / β / βz | Value norm | Raw anchor–value dots | Normalized value alignments | Native candidate scores | Native margin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0A | +0.173791594 / +1.374747515 / +0.238919562 | +3.582478126 | +0.350875821, +0.517972422 | +0.097942209, +0.144584950 | +0.097942188, +0.144584939 | -0.046642751 |
| 0C | +0.175750783 / +1.305542588 / +0.229450132 | +3.426668904 | +0.228505813, +0.272043814 | +0.066684532, +0.079390166 | +0.066684537, +0.079390176 | -0.012705639 |

Swapping Cedar's declaration for Alder's raised the archived Alder score by +0.03125765174627304 and Cedar's by +0.0651947632431984, giving D0 = −0.033937111496925354. The FP64 reconstruction gives +0.031257676512, +0.065194783497 and -0.033937106985, respectively. The positive retrieval scale nearly cancels under normalization. Its finite-epsilon factor remains in the calculation.

## Architectural verdict

**The first candidate for a separately authorized M1 test is an independent erasure gain.** Decouple the gain on key-projected erasure from β on direct value injection, holding the original prefix retention, write vectors, query and readout fixed. E was necessary for both observed ranking and contrast reversals. Omitting E measures the zero-erasure endpoint. This evidence establishes neither the result at an erasure cap of one nor an optimum, improved accuracy, or preserved performance elsewhere.

For M3, the erasure term vanishes in empty memory. Both effective key–query dots are positive. The informative next target for that failure is the declaration value's alignment with the two lexical anchors. This packet cannot choose between changing a value projection and changing the anchor representation, or isolate pooled features from box geometry. One synthetic opening, two frozen probes and six retrospective reads place no bound on held-out accuracy. The original posting rule abstained on all six reads.

## Verification, execution and custody

- Both fresh native Codex sessions ran in independently owned branches/worktrees at dispatcher configuration gpt-6.2-astra/xhigh. The reviewer completed and froze independent evidence before reading the new author source. Root released each exact SHA and argv separately. [Dispatch and inputs](../../../coordination/WP-0032/dispatch.json)
- Author ran the qualified CPU venv python.exe -I -B docs/research/WP-0032/run.py f17396bf4d3915b53cff0e22a37e1b928cdf2919. Reviewer separately ran python.exe -I -B docs/reviews/WP-0032/run.py 6281121dd59aa1602e6fc872e9bca885bb91eeb0. Both used the pinned WP-0030 Python 3.12.10, torch 2.13.0+cpu, deterministic mode, one intra-op/interop thread and the WP-0031 archived tensors. Each verified the native ordered FP32 candidate bytes at all six reads along with the archived read and post-write matrix identities. No input, threshold or frozen recurrence was altered.
- Before either run the reservation fixed the scalar bound at 2e−5 × (1 + max of the two absolute magnitudes), with the sum of cell bounds for donor differences. The author passed 900 gates and the independent replay passed 1,417. The largest absolute native-versus-rearranged residual was 8.513e−8 read-norm units on M3 0A, below 3.712e−5. The largest native margin residual was 2.013e−8 on M1 AC, below 2.081e−5. These are observed residuals on this input. [Author numerical gates](../../../research/WP-0032/evidence/gates.json) · [Independent numerical gates](../../../reviews/WP-0032/evidence/gates.json)
- The reviewer compared 3,548 FP64 scalars across the tables, including signed owner vectors, alongside 150 exact checks and verification of the author's 900 gates. The largest table discrepancy was 4.441e−16 in M3 0A value norm. The author corrected an exploratory archive lookup and created the missing scratch directory. The reviewer located the archived evidence digests in runtime.json after an exploratory manifest lookup. Both decisive runs and their comparison completed on the frozen candidates.
- Root froze accounting_check.py at d8f412d82ed260e1d8a84de743284463d22a8c22 and compare_tables.py at 2594e50edc84cfd74bea5d94e1eaa644feec4010. Root recomputed the scalar decompositions directly from published FP32 data, cross-checked the tables and 1,536 signed-component coordinates, and verified six pairs of native score bytes. Exact commands from the primary checkout are below. The scratch variable denotes C:/Users/jackg/eLedgerCare-Speed/WP-0032/coordination.

~~~powershell
python -I -B docs/coordination/WP-0032/accounting_check.py "$scratch/scalar.json"
python -I -B docs/coordination/WP-0032/compare_tables.py e7096ca975820e2be98c912d52c1a0a731de288f be72e777178fe627f355ad240598c14217e267e8 "$scratch/scalar.json" docs/coordination/WP-0032/reconciliation.json
~~~

Root verified the remote head, custody, prior closure, uniqueness of the assignment, and the existing worktrees and recovery inventory. Both published worker histories were integrated through checked disjoint merge trees and fast-forward advances of the primary checkout. The stash and dirty package file retained their original identities. The release used only packet scratch, the two role branches/worktrees, the coordinator metadata and the read-only CPU environment. The packet ended at write 8. Production code, OCR, accelerators and held-out data were outside the release.

## Change inventory and publication

The following accepted-base-to-disposition diff lists every path, including integrated worker source and evidence. Publication adds this report and its ledger status. The public download receipt binds all three reports to their original publication commits.

~~~text
CURRENT.md
INDEX.md
docs/agent-reports/eld-owner-probe/WP-0032/001_2026-11-24_research_eld-owner-probe.md
docs/agent-reports/eld-rd-reviewer/WP-0032/002_2026-11-24_review_eld-rd-reviewer.md
docs/coordination/WP-0032/accounting_check.py
docs/coordination/WP-0032/assignment.md
docs/coordination/WP-0032/compare_tables.py
docs/coordination/WP-0032/decision.json
docs/coordination/WP-0032/dispatch.json
docs/coordination/WP-0032/reconciliation.json
docs/research/WP-0032/account.py
docs/research/WP-0032/evidence/M1.json
docs/research/WP-0032/evidence/M3.json
docs/research/WP-0032/evidence/gates.json
docs/research/WP-0032/evidence/runtime.json
docs/research/WP-0032/restore.py
docs/research/WP-0032/run.py
docs/reviews/WP-0032/account.py
docs/reviews/WP-0032/compare.py
docs/reviews/WP-0032/evidence/comparison.json
docs/reviews/WP-0032/evidence/gates.json
docs/reviews/WP-0032/evidence/run.json
docs/reviews/WP-0032/evidence/tables.json
docs/reviews/WP-0032/run.py
~~~
