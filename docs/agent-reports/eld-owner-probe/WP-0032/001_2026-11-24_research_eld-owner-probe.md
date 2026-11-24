# WP-0032 / 001 — What reversed the write-8 owner margin?

On both populated M1 prefixes, the donor contrast favored Alder when the subtraction term was omitted from the read and favored Cedar when it was restored. The same term reversed all four individual rankings. On empty M3 memory, the Alder declaration raised the Cedar score more than twice as much as the Alder score. Both gains on the write were positive, so the scores followed the direction of the declaration values relative to the literal anchors.

| Record | Binding |
| --- | --- |
| Report and reservation | `docs/agent-reports/eld-owner-probe/WP-0032/001_2026-11-24_research_eld-owner-probe.md` · [WP-0032 / 001](https://github.com/jackgumpe/eledgercare/blob/537ab866bb5803328d378bc00f11f5782bb5ef00/INDEX.md#wp-0032-six-read-accounting-of-the-write-8-owner-margin) |
| Category and status | Research · ready for independent review |
| Author and publisher | eld-owner-probe · native Codex task `/root/account_author` · thread `01a20b1f-82d2-7583-ae45-ba050547c229` |
| Configuration | Dispatcher supplied `gpt-6.2-astra`, `xhigh`. The session identifies itself as GPT-6. The runtime exposed the thread ID and CLI version. There was no separate detailed model or effort readout. |
| Environment and timestamp | Codex CLI 0.171.0, Windows 11 PowerShell · 2026-11-24T01:22:57Z |
| Repository, branch and owned worktree | `jackgumpe/eledgercare` · `research/wp-0032-accounting` · `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w032-author` |
| Base, frozen source and evidence | `537ab866bb5803328d378bc00f11f5782bb5ef00` · `f17396bf4d3915b53cff0e22a37e1b928cdf2919` · `e7096ca975820e2be98c912d52c1a0a731de288f` |
| Previous and related reports | First /001 in this packet. [WP-0031 author /001](https://github.com/jackgumpe/eledgercare/blob/013499d9fdf5b19e587c91cd93dfd502c0448e04/docs/agent-reports/eld-owner-probe/WP-0031/001_2026-11-23_research_eld-owner-probe.md) · [WP-0031 coordinator /003](https://github.com/jackgumpe/eledgercare/blob/0e503aa6beb3dbc727c5b2a054c52cf48d2a656f/docs/agent-reports/eld-coordinator/WP-0031/003_2026-11-23_verification_eld-coordinator.md) |
| Next owner | eld-rd-reviewer for independent WP-0032 / 002 via eld-coordinator |

## Objective and admission

Reproduce six owner reads at the eighth write of the same synthetic development opening. The first character of each cell identifies its incoming prefix and the second identifies the declaration donor. A denotes Alder, C denotes Cedar, and 0 denotes eight cleared matrix lanes with the common registry and depth-zero controller from the archived Alder prefix. The owner margin is the Alder score minus the Cedar score. Every donor contrast changes the declaration from Cedar to Alder with the prefix held fixed. [Assignment and numerical gates](https://github.com/jackgumpe/eledgercare/blob/537ab866bb5803328d378bc00f11f5782bb5ef00/docs/coordination/WP-0032/assignment.md)

The accepted fit regenerated the original ordered anchors byte for byte. The native write, read and score call preserved the operation order in the frozen source. Each row matched its archived ordered scores, native read bytes, recipient, donor projection, query, anchor, updated matrix stack and owner-column digests. Both owners were eligible. Each cell missed the archived top-score and score-gap thresholds of 1.0 and 0.1. [M1 bytes and state](https://github.com/jackgumpe/eledgercare/blob/e7096ca975820e2be98c912d52c1a0a731de288f/docs/research/WP-0032/evidence/M1.json) · [M3 bytes and state](https://github.com/jackgumpe/eledgercare/blob/e7096ca975820e2be98c912d52c1a0a731de288f/docs/research/WP-0032/evidence/M3.json) · [Input pins and loaded code](https://github.com/jackgumpe/eledgercare/blob/e7096ca975820e2be98c912d52c1a0a731de288f/docs/research/WP-0032/evidence/runtime.json)

| Native FP32 cell | Alder score | Cedar score | Margin from promoted scores | Ordered 8 bytes, little endian |
| --- | ---: | ---: | ---: | --- |
| M1 AA | −0.045244865 | +0.014514945 | −0.059759811 | `ae5239bd18d06d3c` |
| M1 AC | +0.020283854 | +0.060488656 | −0.040204803 | `532aa63cf4c2773d` |
| M1 CA | −0.038797334 | +0.019131321 | −0.057928655 | `f4e91ebd4ab99c3c` |
| M1 CC | +0.030345000 | +0.068099298 | −0.037754297 | `1496f83ca5778b3d` |
| M3 0A | +0.097942188 | +0.144584939 | −0.046642751 | `ea95c83d130e143e` |
| M3 0C | +0.066684537 | +0.079390176 | −0.012705639 | `e791883d5197a23d` |

## M1 subtraction on the populated prefixes

Let `h` be the difference between the two retained anchors. For the incoming matrix `old`, declaration key `k`, value `v`, decay `a` and write gain `b`, let `u = q[:32] / (norm(q[:32]) + 1e-8)` and `z = k[:32] · u`. FP64 reconstruction yields three signed read vectors. The retained read is `R = a (old[:, :32] @ u)`, the direct write is `V = b z v`, and the subtraction is `E = −a b z (old @ k)`. The last multiplication uses the full 128-coordinate key. The JSON retains each signed 128-vector as little-endian FP64 bytes with a digest and norm. The displayed denominators use the FP64 norm of the promoted native read plus epsilon. Both the actual rounded FP32 divisor and the three contributions under that divisor are also retained. [Signed terms, native and analytic reads](https://github.com/jackgumpe/eledgercare/blob/e7096ca975820e2be98c912d52c1a0a731de288f/docs/research/WP-0032/evidence/M1.json)

| Cell | Common denominator | h·R | h·V | h·E | h·R / common | h·V / common | h·E / common |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AA | 0.696057669 | +0.013049887 | +0.039382709 | −0.094028881 | +0.018748285 | +0.056579663 | −0.135087773 |
| AC | 0.557415130 | +0.013046487 | +0.004628658 | −0.040085922 | +0.023405333 | +0.008303790 | −0.071913947 |
| CA | 0.692059417 | +0.014541540 | +0.039382709 | −0.094014325 | +0.021011981 | +0.056906543 | −0.135847187 |
| CC | 0.554235247 | +0.014537750 | +0.004628658 | −0.040091173 | +0.026230289 | +0.008351432 | −0.072336021 |

Each row below uses `R + V` for the omitted read and `R + V + E` for the restored read. Each sum is normalized once with its own norm plus epsilon. The numerator is `h · read`. The sign of the numerator and the normalized ranking both reverse in every cell.

| Cell | Omitted norm | Omitted numerator | Omitted margin | Restored norm | Restored numerator | Restored margin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AA | 0.854533786 | +0.052432596 | +0.061358130 | 0.696057656 | −0.041596285 | −0.059759825 |
| AC | 0.578971891 | +0.017675145 | +0.030528503 | 0.557415127 | −0.022410777 | −0.040204823 |
| CA | 0.853888648 | +0.053924248 | +0.063151381 | 0.692059396 | −0.040090077 | −0.057928664 |
| CC | 0.578073517 | +0.019166409 | +0.033155659 | 0.554235229 | −0.020924764 | −0.037754301 |

| Fixed prefix | Quantity | Omitted donor contrast | Restored donor contrast | Restored minus omitted |
| --- | --- | ---: | ---: | ---: |
| Alder | Numerator | +0.034757451 | −0.019185508 | −0.053942959 |
| Alder | Margin | +0.030829628 | −0.019555003 | −0.050384631 |
| Cedar | Numerator | +0.034757840 | −0.019165313 | −0.053923153 |
| Cedar | Margin | +0.029995722 | −0.020174363 | −0.050170086 |

At fixed values of the other terms, E is necessary both for the four individual Cedar-first rankings and for the negative donor contrast on each prefix. Omitting E ranks Alder first even with a Cedar declaration. The omitted donor-margin contrasts exceed their positive sign budgets of 0.00004184 and 0.00004193. Both restored contrasts clear their negative sign budgets of 0.00004200 and 0.00004192. The change is already visible in the unnormalized numerators. Normalization changes the size of the effect. [Exact donor differences and budgets](https://github.com/jackgumpe/eledgercare/blob/e7096ca975820e2be98c912d52c1a0a731de288f/docs/research/WP-0032/evidence/M1.json)

## M3 values on empty memory

All eight incoming lanes were zero. At depth zero, the read is `g v` with `g = b z`. Both measured gains were positive. For an original anchor `p`, the score is `(p · v / norm(v)) × (g norm(v) / (g norm(v) + 1e-8))`. The native anchor already carries its original normalization. Using the unit-value dot in this expression preserves its exact length. The table also gives the ordinary cosine, which divides by the measured anchor norm. [M3 alignments and reconstructed scores](https://github.com/jackgumpe/eledgercare/blob/e7096ca975820e2be98c912d52c1a0a731de288f/docs/research/WP-0032/evidence/M3.json)

| Donor | Owner-slice key · u | Beta | g | Value norm | Effective read norm | Denominator | Finite-epsilon factor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Alder | 0.173791594 | 1.374747515 | 0.238919562 | 3.582478126 | 0.855924104 | 0.855924114 | 0.999999988317 |
| Cedar | 0.175750783 | 1.305542588 | 0.229450132 | 3.426668904 | 0.786249634 | 0.786249644 | 0.999999987281 |

| Donor | Anchor | Raw value dot | Dot with unit value | Cosine | Recovered score |
| --- | --- | ---: | ---: | ---: | ---: |
| Alder | Alder | 0.350875821 | 0.097942209 | 0.097942228 | 0.097942208 |
| Alder | Cedar | 0.517972422 | 0.144584950 | 0.144584972 | 0.144584949 |
| Cedar | Alder | 0.228505813 | 0.066684532 | 0.066684545 | 0.066684531 |
| Cedar | Cedar | 0.272043814 | 0.079390166 | 0.079390178 | 0.079390165 |

The reconstructed margins were −0.046642741 for the Alder donor and −0.012705634 for the Cedar donor. Switching to Alder raised the reconstructed Alder score by +0.031257677 and Cedar score by +0.065194783, yielding D0 = −0.033937107. The corresponding native changes were +0.03125765174627304, +0.0651947632431984 and −0.033937111496925354. D0 clears its summed uncertainty budget of 0.00004119. The finite epsilon reduced each recovered score by less than 1.7 × 10⁻⁹ compared with taking the dot product with the exact unit value. Both donors favored the Cedar anchor, and the Alder donor increased this preference.

## Numerical verification

For each native reference x and FP64 reconstruction y the stored residual is y − x. The bound was `2e-5 × (1 + max(abs(x), abs(y)))` per scalar and per read coordinate. Donor differences used the sum of the two cell bounds. The policy includes an absolute floor near cancellation and scale allowance for FP32 reductions and normalization. Sign budgets serve as engineering thresholds. All 900 comparisons in 27 groups passed. FP32 numerator references use the actual FP32 projected read and anchor operands. The evidence also compares to direct FP64 projections of that same native read. [Every gate, location, residual, bound and maximum](https://github.com/jackgumpe/eledgercare/blob/e7096ca975820e2be98c912d52c1a0a731de288f/docs/research/WP-0032/evidence/gates.json)

| Native-vs-rearranged quantity | Largest absolute residual | Affected cell(s) |
| --- | ---: | --- |
| Read coordinate (read units) | 2.151 × 10⁻⁸, rounded up | M3 0A, coordinate 99 (zero-based) |
| Read norm (read units) | 8.513 × 10⁻⁸ | M3 0A |
| h·read (anchor dot read) | 7.961 × 10⁻⁹ | M3 0A |
| Alder score (normalized score) | 1.946 × 10⁻⁸ | M3 0A |
| Cedar score (normalized score) | 1.041 × 10⁻⁸ | M3 0C |
| Owner margin (score difference) | 2.013 × 10⁻⁸ | M1 AC |
| Donor difference in h·read | 1.002 × 10⁻⁸ | M3 0A − 0C |
| Donor difference in owner margin | 5.416 × 10⁻⁹ | M1 CA − CC |

The largest fraction of any allowed limit was 0.002294, rounded up, for the norm of M3 0A. The native FP32 score-byte requirement passed exactly for all six cells. The assignment requires a separately authored cross-implementation comparison before coordinator disposition.

## Change inventory and review map

All seven deliverable paths were added under `docs/research/WP-0032/`. The reserved report path in the metadata above is the sole report-phase addition. [Source diff](https://github.com/jackgumpe/eledgercare/compare/537ab866bb5803328d378bc00f11f5782bb5ef00...f17396bf4d3915b53cff0e22a37e1b928cdf2919) · [Evidence diff](https://github.com/jackgumpe/eledgercare/compare/f17396bf4d3915b53cff0e22a37e1b928cdf2919...e7096ca975820e2be98c912d52c1a0a731de288f)

| Path | Relevant contents |
| --- | --- |
| `run.py` | Checks source, pinned inputs, CPU runtime and thread counts, restricts the six-cell matrix, writes receipts and retains failures |
| `restore.py` | Restores literal anchors and projected donors, enforces common discrete state, invokes native write/read/score and compares bytes with three historical records |
| `account.py` | Computes signed terms, read-specific norms, alignment, donor differences and bounded residuals |
| `evidence/M1.json` | Four native and analytic rows with signed R, V, E vectors and two prefix-specific donor contrasts |
| `evidence/M3.json` | Two native and analytic rows, frozen values and anchors, effective norms, alignment and D0 |
| `evidence/gates.json` | All checked scalars and coordinate locations, per-comparison budgets and maxima |
| `evidence/runtime.json` | Exact executable, loaded source hashes, full input revisions, payload checksums, runtime and output locations |

## Executed checks and external effects

| Operation | Revision and outcome |
| --- | --- |
| `git status --short --branch`, `git rev-parse HEAD`, qualified Python `ast.parse` on all three source files, `git diff --cached --check` | Verified clean reserved worktree and base. Syntax and staged whitespace passed before freeze. |
| `& 'C:/Users/jackg/eLedgerCare-Speed/WP-0030/runtime/venv/Scripts/python.exe' -I -B docs/research/WP-0032/run.py f17396bf4d3915b53cff0e22a37e1b928cdf2919` | Root released this exact source and command. One invocation, exit 0. Python 3.12.10, torch 2.13.0+cpu, NumPy 2.2.6, deterministic CPU, one intra-op and one inter-op thread. The receipt records the venv launcher and underlying Windows interpreter. |
| Copy the new scratch evidence directory to the owned source directory, `git diff --cached --check`, commit, and read the four committed blobs with `git cat-file blob HEAD:<path>` | At `e7096ca975820e2be98c912d52c1a0a731de288f`, a stdlib audit compared every blob to its working and scratch copies and validated payload digests. Decoding the M1 signed vectors reconstructed the four omitted and restored vectors exactly. It checked all six score pairs, four M3 value-to-anchor scores, three donor-margin signs, and 900 residuals against their limits. |
| `& 'C:/Users/jackg/eLedgerCare-Speed/WP-0032/coordination/push.ps1' -ExpectedHead (git rev-parse HEAD)` | The non-force push published the evidence commit and frozen parent. The live owned branch returned `e7096ca975820e2be98c912d52c1a0a731de288f`. The coordinator receives the final report publication SHA after commit and remote verification. |

The retained scratch directory is `C:/Users/jackg/eLedgerCare-Speed/WP-0032/author/f17396bf4d3915b53cff0e22a37e1b928cdf2919`. A preflight directory listing found that the author scratch directory had not yet been created. The runner created it. One metadata inspection of historical WP-0031 records initially looked for 0A inside the independent archive's `zero` summary. Schema inspection located the row in `cells` before the candidate was frozen. The released run had no execution failures.

## Candidate priority and handoff

For a later M1 experiment, give first priority to decoupling the subtraction gain from the direct-write gain. Removing the signed subtraction exactly reversed the donor-contrast sign on both prefixes in this calculation. The observed beta values of 1.59436 and 1.54225 do not determine the effect of a particular bound. Omission sets the entire term to zero, whereas a bounded gain would retain some subtraction and change the normalized read. No particular bound or expected improvement can be selected from these observations.

For M3, investigate how the declaration value aligns with the frozen owner anchors. The empty-memory read already exhibits the Cedar-favoring shift. The positional and pooled-feature inputs changed together, so this accounting cannot apportion the effect between them. Both recommendations concern one shared synthetic opening at one write. Architecture efficacy, owner accuracy on other openings and held-out generalization remain unmeasured. No additional write, OCR, GPU execution, architectural treatment, training or product change was run. The independent reviewer receives the frozen source and evidence revisions above via eld-coordinator for numerical comparison and review.
