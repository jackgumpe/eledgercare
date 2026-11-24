# WP-0032 / 002 Independent review of the write-8 owner margin

| Report metadata | Value |
| --- | --- |
| Report path | `docs/agent-reports/eld-rd-reviewer/WP-0032/002_2026-11-24_review_eld-rd-reviewer.md` |
| Sequence and category | WP-0032 /002, review, [reservation](https://github.com/jackgumpe/eledgercare/blob/537ab866bb5803328d378bc00f11f5782bb5ef00/INDEX.md#wp-0032-six-read-accounting-of-the-write-8-owner-margin) |
| Author and publisher | eld-rd-reviewer |
| Execution environment and identity | Native Codex reviewer thread `01a20b1f-b484-7ce0-82b6-35c697f780f8`, dispatcher-reported `gpt-6.2-astra/xhigh` without a separate model/effort readout, Windows 11 CPU. Parent/host session `01a20a53-eec1-72c1-864c-9f8be8f4aff5`. |
| Timestamp (UTC) | 2026-11-24T01:25:51Z |
| Repository, branch and worktree | [jackgumpe/eledgercare](https://github.com/jackgumpe/eledgercare), `review/wp-0032-accounting`, `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w032-review` |
| Base | `537ab866bb5803328d378bc00f11f5782bb5ef00` |
| Independent source and tables | `6281121dd59aa1602e6fc872e9bca885bb91eeb0`, `be72e777178fe627f355ad240598c14217e267e8` |
| Comparison source and final deliverable | `4f013c667db719aab745cba75ce672c3ef22ec74`, `0bf997ef2ac4c42801dfa6fc5d07406301431a0d` |
| Reviewed source and evidence | `f17396bf4d3915b53cff0e22a37e1b928cdf2919`, `e7096ca975820e2be98c912d52c1a0a731de288f` |
| Reviewed author report | [WP-0032 /001](https://github.com/jackgumpe/eledgercare/blob/707794967c4505131d8d8b5f9e08313d3e7ffa7f/docs/agent-reports/eld-owner-probe/WP-0032/001_2026-11-24_research_eld-owner-probe.md) |
| Previous report by this reviewer in WP-0032 | First report |
| Status and next owner | Accepted for the six authorized numerical reads. eld-coordinator owns architectural disposition, integration and publication verification. |

## Summary

Both independent tables agree. All six native FP32 score pairs reproduce the archived eight bytes in Alder/Cedar order. Restoring the signed subtraction reverses each M1 cell's owner ranking and also reverses the donor contrast on each incoming prefix. On empty M3 memory, the Alder declaration increases both anchor scores. The larger increase for the Cedar anchor makes the donor margin contrast negative.

## Objective and acceptance criteria

The assignment covers four populated M1 reads and two empty M3 reads from one synthetic development opening, all after write 8 at depth zero. The original FP32 ordered scores must agree exactly. For each scalar, including every read coordinate, the permitted magnitude of a reconstruction difference is `2e-5 * (1 + max(abs(reference), abs(reconstruction)))`. Differences of two cells receive the sum of their scalar limits. A difference between omitted and restored contrasts receives the sum of the two contrast limits. A sign is resolved only beyond the corresponding limit. These are engineering tolerances. [Frozen criteria](https://github.com/jackgumpe/eledgercare/blob/537ab866bb5803328d378bc00f11f5782bb5ef00/docs/coordination/WP-0032/assignment.md)

## Decisions and rationale

I froze and published the independent code, executed the six reads once on the coordinator's exact-SHA release and published the tables before opening this packet's author source or results. I authored no part of the reviewed source or the frozen upstream model. For native parity I used the accepted matrix module's write, read and ordering of normalization and scoring, with the original FP32 inputs. For independent FP64 reconstruction I used Python floats and `math.fsum` dot products. The author used Torch FP64 matrix/vector operations.

### Four M1 populated reads

In the following tables a positive margin favors Alder. Each prefix/donor name is abbreviated by its initial. The signs of all three components include their signs in the update. The numerator is the frozen Alder-minus-Cedar anchor dotted with the read. The subtraction uses the complete 128-coordinate incoming key. Only the read contracts the 32 owner columns. Contributions share one denominator per row, computed by widening the native FP32 read and adding 1e−8 to its FP64 norm. Each omitted or restored margin uses its own summed vector's denominator. Both native-denominator precision conventions and all twelve lossless signed FP64 vectors are retained. [Independent tables](https://github.com/jackgumpe/eledgercare/blob/be72e777178fe627f355ad240598c14217e267e8/docs/reviews/WP-0032/evidence/tables.json)

| Prefix / donor | Numerator R | Numerator V | Numerator E | Common denominator | h·R / denominator | h·V / denominator | h·E / denominator |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AA | .013050 | .039383 | −.094029 | .696058 | .018748 | .056580 | −.135088 |
| AC | .013046 | .004629 | −.040086 | .557415 | .023405 | .008304 | −.071914 |
| CA | .014542 | .039383 | −.094014 | .692059 | .021012 | .056907 | −.135847 |
| CC | .014538 | .004629 | −.040091 | .554235 | .026230 | .008351 | −.072336 |


| Cell | Omitted norm | Restored norm | Omitted numerator | Restored numerator | Omitted margin | Restored margin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AA | .854534 | .696058 | .052433 | −.041596 | .061358 | −.059760 |
| AC | .578972 | .557415 | .017675 | −.022411 | .030529 | −.040205 |
| CA | .853889 | .692059 | .053924 | −.040090 | .063151 | −.057929 |
| CC | .578074 | .554235 | .019166 | −.020925 | .033156 | −.037754 |

| Prefix | Quantity | Alder donor minus Cedar, omitted | Alder donor minus Cedar, restored | Restored minus omitted |
| --- | --- | ---: | ---: | ---: |
| Alder | Numerator | +.03475745 | −.01918551 | −.05394296 |
| Alder | Margin | +.03082963 | −.01955500 | −.05038463 |
| Cedar | Numerator | +.03475784 | −.01916531 | −.05392315 |
| Cedar | Margin | +.02999572 | −.02017436 | −.05017009 |

Even the smallest absolute cell margin exceeds .0305. The subtraction is necessary for each observed Cedar-first cell ranking under this omission comparison. The separate donor test holds the incoming prefix fixed. It finds a positive contrast on both omitted reads and a negative contrast after restoration on both prefixes. For these numerator and margin contrasts, all paired-cell limits are below .0000421, and all four-cell limits below .000084. Omitting the term yields Alder-first on every cell, including both Cedar declarations. These results motivate testing separate erasure and direct-write gains first for M1. They do not establish a successful clamp, an optimal gain, or joint correct ranking.

### Two M3 empty-memory reads

The archived discrete state admits the same two owners at depth zero, with all eight incoming matrices zero. The read simplifies to `s v`, where `s = beta * dot(key[:32], direction(query[:32]))`. Both positive scalars preserve the declaration value direction. For anchor L, the normalized score is `s * dot(L,v) / (abs(s) * norm(v) + 1e-8)`. The two finite-epsilon factors are .999999988317 and .999999987281. The original FP32 anchor norms are retained in the scores. Cosine uses each actual anchor norm as well as the declaration value norm.

| Donor | Owner query-key dot | Beta | Product | Value norm | Effective read norm | Denominator |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Alder | .173791594 | 1.374747515 | .238919562 | 3.582478126 | .855924104 | .855924114 |
| Cedar | .175750783 | 1.305542588 | .229450132 | 3.426668904 | .786249634 | .786249644 |

| Donor | Alder raw dot | Cedar raw dot | Alder cosine | Cedar cosine | Alder score | Cedar score | Margin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Alder | .350875821 | .517972422 | .097942228 | .144584972 | .097942208 | .144584949 | −.046642741 |
| Cedar | .228505813 | .272043814 | .066684545 | .079390178 | .066684531 | .079390165 | −.012705634 |

Changing Cedar donor to Alder donor raises the analytic Alder score by .031257677 and the Cedar score by .065194783. Their difference is −.033937107. The original FP32 scores give −.033937111496925354. The two-score-change limits are .000043293 and .000044480, and the margin contrast limit is .000041187. The epsilon effect is below the comparison uncertainty. On this empty control the subtraction term is zero. Examining value-to-anchor alignment has priority for M3. A declaration changes its pooled feature and its box together, so these data cannot assign a separate cause to either.

## Change inventory

All entries below are additions under `docs/reviews/WP-0032/`. Exact revisions and contents are available in the [review diff](https://github.com/jackgumpe/eledgercare/compare/537ab866bb5803328d378bc00f11f5782bb5ef00...0bf997ef2ac4c42801dfa6fc5d07406301431a0d).

| File | Purpose |
| --- | --- |
| `run.py` | Verify candidate, runtime, pinned sources, archive, native calls, byte equality and discrete state. |
| `account.py` | Compute signed owner components, factorized scores, independent normalization, contrasts and engineering bounds. |
| `evidence/tables.json` | Independent numerical rows, literal/recipient/donor/read bindings, signed vectors and contrast error budgets. |
| `evidence/gates.json` | Counts and worst residuals by independently checked quantity. |
| `evidence/run.json` | Exact argv, input SHA-256 inventory, output digests and runtime receipt. |
| `compare.py` | Compare pinned tables and recompute individual author gate budgets, pass flags and maxima. |
| `evidence/comparison.json` | Exact equality ledger and numerical maxima from cross-implementation review. |

The reserved report is the only later metadata addition. Candidate-specific review scratch directories under `C:/Users/jackg/eLedgerCare-Speed/WP-0032/review/` retain staged pinned modules, outputs and temporary/cache directories. The supplied ownership script advanced only the review branch.

## Verification and review map

The interpreter for the two commands below was `C:/Users/jackg/eLedgerCare-Speed/WP-0030/runtime/venv/Scripts/python.exe`, SHA-256 `0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14`. CPython 3.12.10, Torch 2.13.0+cpu, NumPy 2.2.6, deterministic algorithms and one intra-op/one inter-op thread were verified. The Windows venv launcher records the base interpreter in `sys.orig_argv`, and the qualified venv path in `sys.executable`. [Run receipt](https://github.com/jackgumpe/eledgercare/blob/be72e777178fe627f355ad240598c14217e267e8/docs/reviews/WP-0032/evidence/run.json)

| Check and command | Result |
| --- | --- |
| Independent execution, `-I -B docs/reviews/WP-0032/run.py 6281121dd59aa1602e6fc872e9bca885bb91eeb0` | Exit 0. All six reads and 48 ordered score bytes exact. All 1,417 numerical checks passed, including coordinatewise native and omitted reconstruction. |
| Source inspection, `git show f17396bf4d3915b53cff0e22a37e1b928cdf2919:docs/research/WP-0032/<name>.py` for `run`, `restore`, `account` | Inspected all three files. Verified the finite matrix, executable/loaded-module pins, threshold and anchor identity, all zero lanes, native FP32 call order, full-key subtraction, per-sum normalization, common denominator, both lexical alignments, contrast direction and propagated bounds. |
| Pinned cross-comparison, `-I -B docs/reviews/WP-0032/compare.py e7096ca975820e2be98c912d52c1a0a731de288f 4f013c667db719aab745cba75ce672c3ef22ec74` | Exit 0. All 3,548 FP64 comparisons and 150 exact comparisons passed. Independently recalculated all 900 author gate residuals, limits, fractions and grouped maxima. |
| `git diff --cached --check` and `C:/Users/jackg/eLedgerCare-Speed/WP-0032/coordination/push.ps1 -ExpectedHead (git rev-parse HEAD)` on owned branch | Whitespace checks passed. Author-independent source, tables and subsequent comparison evidence were published with remote head verification. |

The largest independent reconstructed-vs-native coordinate discrepancy was 2.15003e−8 read units in M3 0A coordinate 99. Maximum disagreements were 7.96115e−9 numerator units (M3 0A), 1.94571e−8 score units (M3 0A/Alder) and 2.01265e−8 margin units (M1 AC). The largest across all native quantities was 8.51297e−8 read units for the M3 0A native FP32 norm. All are absolute residuals. Across implementations the largest residual was 4.44090e−16 value-norm units for M3 0A, against 9.16496e−5. The highest fraction of a budget was 6.21539e−12, for the M3 0C effective norm. All coordinatewise signed-component discrepancies were at most 2.776e−17 read units. [Independent gate maxima](https://github.com/jackgumpe/eledgercare/blob/be72e777178fe627f355ad240598c14217e267e8/docs/reviews/WP-0032/evidence/gates.json) · [Cross-comparison](https://github.com/jackgumpe/eledgercare/blob/0bf997ef2ac4c42801dfa6fc5d07406301431a0d/docs/reviews/WP-0032/evidence/comparison.json) · [Reviewed source](https://github.com/jackgumpe/eledgercare/tree/f17396bf4d3915b53cff0e22a37e1b928cdf2919/docs/research/WP-0032)

## Risks, disagreements and handoff

No decisive execution or comparison failed. An exploratory file read requested a nonexistent historical evidence manifest. The historical `runtime.json` contains the published evidence digests and the frozen verifier used that file. No architecture modification, model training, OCR acquisition, later write, or held-out evaluation was part of the review. These six algebraic reads reuse one exposed development opening and support no estimate of treatment efficacy or generalization. The two mechanisms apply to different probe/control conditions. I checked the six native byte strings, the rounded M1 and M3 tables, the direction of the three donor contrasts and the scope of the recommendations in /001 at `707794967c4505131d8d8b5f9e08313d3e7ffa7f`. The report agrees with the independent evidence.

eld-coordinator can integrate the reviewed source/evidence and this review, and record the packet-wide disposition from the exact revisions above. The report publication SHA and live remote verification follow separately in the handoff.
