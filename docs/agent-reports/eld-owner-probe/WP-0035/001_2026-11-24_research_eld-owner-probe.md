# WP-0035 / 001 — Write-8 recovery did not reach the posting target

| Report metadata | Binding |
| --- | --- |
| Author and publisher | eld-owner-probe |
| Report path | `docs/agent-reports/eld-owner-probe/WP-0035/001_2026-11-24_research_eld-owner-probe.md` |
| Sequence and category | WP-0035 / 001, research, reserved in INDEX.md at `d8db225dae2c2ea4d70896c1936a1e1e22a104e2` |
| Actual execution environment | Fresh native local Codex session `01a20bdc-a2ce-7342-af1f-cf3cfccd2285`. The coordinator's dispatch records gpt-6.2-astra, xhigh, fresh fork with no shared history. Windows, PowerShell and qualified CPU Python |
| Timestamp | 2026-11-24T04:55:35Z |
| Repository, branch and worktree | jackgumpe/eledgercare, `research/wp-0035-trajectory`, `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w035-author` |
| Accepted base and assigned base | `d9741d6e880d06192b9f3e56ab8056d391da1b9e` and `d8db225dae2c2ea4d70896c1936a1e1e22a104e2` |
| Frozen deliverable | `98328bf4e6fd240fecbf0ae91c2a03ad95071a6b` |
| Numerical evidence | `65df68e86fe540c4c61ec2deba813e8d95b10da9` |
| Status and next owner | Ready for independent review by eld-rd-reviewer and disposition by eld-coordinator |

## Summary

Every neural regime ranked both twins correctly at the posting target on **0/2 matched development horizons and 0/8 exposed calibration pairs**. Every neural regime abstained on all 20 answerable binders. No wrong non-abstaining owner decisions or wrong complete postings occurred. M2's symbolic control posted all 20 correctly and withheld all four no-target safety binders. These counts compare the same binders across arms. The two matched horizons reuse one development opening.

Neither declaration damping, downstream root erasure damping, root decay freeze, within-binder anchor centering, nor any released combination solved terminal twin ranking. **I recommend against capturing the 16 fresh pairs on the strength of these treatments.** The numerical failure precedes an expensive fresh test, and the positive control reads the existing streams successfully.

## Objective and acceptance criteria

Reproduce all 224 original paired points on both literal-score bytes and available state/read/query digests, and reproduce the four write-8 W1 crosses before measuring treatments. Run M1 W0/W1/W2a/W2b, M3 W0/W1 and both readouts, plus symbolic M2, on two matched horizons and all authenticated calibration pairs. Evaluate the true pre-write posting, complete typed correctness, owner-only cutoffs and four no-target safety binders. Preserve exact inputs, controls and per-point values. The packet builds on the [WP-0030 traces](https://github.com/jackgumpe/eledgercare/blob/d9741d6e880d06192b9f3e56ab8056d391da1b9e/docs/reviews/WP-0030/evidence/steps.jsonl) and [WP-0033 reconciliation](https://github.com/jackgumpe/eledgercare/blob/d9741d6e880d06192b9f3e56ab8056d391da1b9e/docs/coordination/WP-0033/reconciliation.json).

## Custody and parity

All eight exposed answerable pairs and two exposed safety pairs have tier-1 streams. The cal-only transport references 140 ordered logical windows backed by 29 unique physical windows. Each binder's ordered tags match the published by_binder record. Each archived receipt, metadata and pooled feature digest matches the public inventory and the original receipt bindings. There are zero tier-2 pairs, zero tier-3 pairs and zero missing results. The two safety pairs have complete streams and zero grammar-recognized targets. Their four binders stay outside the owner-ranking denominator. Their prediction is `ABSTAIN/no_target` in every arm. [Ordered custody](https://github.com/jackgumpe/eledgercare/blob/65df68e86fe540c4c61ec2deba813e8d95b10da9/docs/research/WP-0035/evidence/custody.json)

The archive gate passed 224 paired rows including both members, all 448 score vectors, the initial state, the pre-target read and the subsequent write. It matched all FP64 paired deltas and available read, query, full-matrix and owner-column digests. The write-8 native and damped score bytes matched on AA, AC, CA and CC. The damped cells in that order were `48a9e43d89bdd53d`, `1d8bd83d6339e13d`, `2943f43ddd25e13d` and `18b2ee3d64eef13d`. All four ranked the donor first. Stock calibration matched all published per-field score bytes and typed outcomes across 20 binders for each model. [Admission evidence](https://github.com/jackgumpe/eledgercare/blob/65df68e86fe540c4c61ec2deba813e8d95b10da9/docs/research/WP-0035/evidence/admission.json.gz) · [Calibration parity](https://github.com/jackgumpe/eledgercare/blob/65df68e86fe540c4c61ec2deba813e8d95b10da9/docs/research/WP-0035/evidence/calibration-parity.json)

## Terminal decision table

Each neural arm produced **0 correct, 0 wrong, 4 abstentions** on Task A and **0 correct, 0 wrong, 16 abstentions** on answerable Task B, under both the eligible owner-only rule and the complete typed decision. All those full abstentions carried `below_threshold_owner`. The table partitions numerical failures as absolute-score-only / gap-only / both using the actual FP32 comparisons. The largest terminal top score was 0.2970581352710724 against the fixed cutoff of 1.0. The required gap was 0.1. All columns cover observed terminal target attempts. [Per-binder typed outputs and all field scores](https://github.com/jackgumpe/eledgercare/blob/65df68e86fe540c4c61ec2deba813e8d95b10da9/docs/research/WP-0035/evidence/terminals.json.gz)

| Model | Write | Read | Both ranked A | Both ranked B | Positive δ A / B | A failure partition | B failure partition |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| M1 | W0 | R0 | 0/2 | 0/8 | 2 / 8 | 0 / 0 / 4 | 0 / 0 / 16 |
| M1 | W0 | R1 | 0/2 | 0/8 | 2 / 8 | 4 / 0 / 0 | 15 / 0 / 1 |
| M1 | W1 | R0 | 0/2 | 0/8 | 2 / 8 | 0 / 0 / 4 | 6 / 0 / 10 |
| M1 | W1 | R1 | 0/2 | 0/8 | 2 / 6 | 1 / 0 / 3 | 10 / 0 / 6 |
| M1 | W2a | R0 | 0/2 | 0/8 | 2 / 8 | 0 / 0 / 4 | 0 / 0 / 16 |
| M1 | W2a | R1 | 0/2 | 0/8 | 2 / 8 | 3 / 0 / 1 | 15 / 0 / 1 |
| M1 | W2b | R0 | 0/2 | 0/8 | 2 / 8 | 0 / 0 / 4 | 0 / 0 / 16 |
| M1 | W2b | R1 | 0/2 | 0/8 | 2 / 8 | 3 / 0 / 1 | 15 / 0 / 1 |
| M3 | W0 | R0 | 0/2 | 0/8 | 2 / 8 | 4 / 0 / 0 | 14 / 0 / 2 |
| M3 | W0 | R1 | 0/2 | 0/8 | 2 / 6 | 4 / 0 / 0 | 16 / 0 / 0 |
| M3 | W1 | R0 | 0/2 | 0/8 | 2 / 8 | 4 / 0 / 0 | 16 / 0 / 0 |
| M3 | W1 | R1 | 0/2 | 0/8 | 2 / 8 | 4 / 0 / 0 | 16 / 0 / 0 |

M2 produced 4 correct, 0 wrong, 0 abstentions on Task A and 16 correct, 0 wrong, 0 abstentions on answerable Task B. Each arm, including M2, withheld all four separate no-target safety binders with zero postings. M2 produces complete typed results directly. Numerical rank and cutoff columns do not apply.

## Where the rankings changed

M1 W1-R0 on the shared opening won both members at writes 8, 10 and 11. It lost the simultaneous win at the actual targets. The following examples are rounded for reading. The [full 1,440 paired rows](https://github.com/jackgumpe/eledgercare/blob/65df68e86fe540c4c61ec2deba813e8d95b10da9/docs/research/WP-0035/evidence/contrasts.json.gz) preserve binary64 margins for both members, δ, μ, Γ, strict win count, both pointers and checkpoint labels for every arm. The [2,880 literal-score rows](https://github.com/jackgumpe/eledgercare/blob/65df68e86fe540c4c61ec2deba813e8d95b10da9/docs/research/WP-0035/evidence/scores.json.gz) supply original FP32 bytes, unrounded promoted top and gap, separate cutoff booleans, registry eligibility, state and query digests. The same pair, horizon, model, W, R, phase and step identify the companion rows. Only the native pre-target phase is the posting decision.

| M1 W1-R0 checkpoint | Write | δ | μ | Γ | Owners correct |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pre-declaration, both horizons | 7 | −0.002956 | +0.027201 | −0.057358 | 1/2 |
| Root declaration | 8 | +0.008865 | +0.002853 | +0.003160 | 2/2 |
| Unit text | 9 | +0.020974 | +0.028351 | −0.035729 | 1/2 |
| Before service row | 11 | +0.025888 | −0.007481 | +0.010926 | 2/2 |
| First service row | 12 | +0.027545 | −0.020038 | −0.012531 | 1/2 |
| Child entry | 17 | +0.030378 | −0.057084 | −0.083791 | 1/2 |
| 12-page pop | 31 | +0.016670 | −0.058808 | −0.100947 | 1/2 |
| 12-page pre-target | 35 | +0.014412 | −0.042864 | −0.071316 | 1/2 |
| 30-page pop | 67 | +0.011953 | −0.042616 | −0.073280 | 1/2 |
| 30-page pre-target | 71 | +0.010795 | −0.031383 | −0.051970 | 1/2 |

The 98.5% attenuation hypothesis describes the absolute native **M3** twin differential between writes 8 and 11 on this opening. It moved from −0.017752446234226227 to −0.00026670098304748535, a 98.4976663% reduction in magnitude. Native M1 changed sign over that interval, from −0.022005513310432434 to +0.0132791418582201, a 39.6553869% reduction in magnitude. M1 W1-R0 *increased* from +0.008865438401699066 to +0.025887567549943924. A universal 98.5% collapse would misdescribe these measurements.

Across each Task A stream, 13 post-declaration root writes preceded the target. None had αβ above one. At writes 9–12, M1's αβ ranged from 0.760779 to 0.779470 and M3's from 0.655877 to 0.788712. By the actual target the M1 root-only native retention product was 0.978580 for Alder and 0.978745 for Cedar, and M3's was 0.962699 and 0.963239. On M1 W2b that product was 1. The 30-page binder adds child writes. M1's flat memory also accepts those native writes. Products over the designated root stratum describe only one component of that recurrence. [Every write, original α, β, αβ and effective gates](https://github.com/jackgumpe/eledgercare/blob/65df68e86fe540c4c61ec2deba813e8d95b10da9/docs/research/WP-0035/evidence/writes.json.gz)

At the 12-page terminal under M1-R0, W1 raised δ from 0.009357478469610214 to 0.014411939308047295. W2a reduced it to 0.012908905744552612 and W2b raised it slightly to 0.013029109686613083. At 30 pages, the corresponding sequence was 0.006276067346334457, 0.010795198380947113, 0.00932467170059681 and 0.009413868188858032. All eight terminal Γ values remained negative. The comparison file records 1,680 signed effects for W1−W0, W2a−W1, W2b−W2a and R1−R0. [Signed differences on every observed step](https://github.com/jackgumpe/eledgercare/blob/65df68e86fe540c4c61ec2deba813e8d95b10da9/docs/research/WP-0035/evidence/effects.json.gz)

R1 centered raw anchors within each binder. M1's two raw norms were 0.0931481 and 0.0709802, with angle 0.627893 radians. M3's were 0.0544639 and 0.0617380, with angle 0.862228. The two centered normalized vectors summed to residual norms of 1.72e−7 for M1 and 1.36e−7 for M3. The measured axis-length gains were 3.23819 and 2.39301. Unequal raw norms violate the collinearity hypothesis used to derive a uniform gain for directional scores. The vector residual relative to the equal-norm axis prediction was 0.78333 on M1 and 0.27032 on M3. For example, R1 raised 12-page M1-W1 terminal δ from 0.014412 to 0.049703 and enlarged |μ| from 0.042864 to 0.095147. Γ declined from −0.071316 to −0.140592. In exposed calibration W1-R1 on M1 and W0-R1 on M3 each reversed the positive differential on two pairs. [Anchor bytes and geometry](https://github.com/jackgumpe/eledgercare/blob/65df68e86fe540c4c61ec2deba813e8d95b10da9/docs/research/WP-0035/evidence/anchors.json.gz)

## Decisions and verification

The exact public label and target joins define Alder as the first member and Cedar as the second. Both actual owner directories contained those two literals. Native full-window projections, active depth, event-before-write and pop behavior stay in the pinned primitive. W treatments select the first unambiguous observed root declaration and subsequent qualified writes. Actual R1 typed decisions replace only the owner logits in the observed attempt and retain native arbitration. Task A retains the target span's subsequent write for archive parity. Task B traverses each complete native window. After the sole target attempt in each of the 16 answerable calibration binders, it records the target span write and two trailing span writes, three diagnostic writes per binder and 48 per write trajectory across that population. All 48 are excluded from posting and preposting mechanism counts. The four safety binders each traverse their complete streams with zero attempts.

| Executed check | Actual result |
| --- | --- |
| Static Python AST parse, PowerShell parser, `git diff --cached --check` before source freeze | All four Python modules and the launcher parsed. Staged diff passed. |
| `pwsh -NoProfile -File docs/research/WP-0035/run.ps1 -Candidate 98328bf4e6fd240fecbf0ae91c2a03ad95071a6b -RunName attempt-01` in the owned worktree, under coordinator release `5d01bf758292da6e9d2b23d2d32521d89fe862ca` | One attempt, wrapper exit 0, empty stderr, 12.215 wall seconds, 10.5 process CPU seconds. Native admission passed before the matrix ran. |
| Qualified CPU executable SHA-256 `0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14`, Python 3.12.10, torch 2.13.0+cpu, NumPy 2.2.6 | Isolated and bytecode-disabled execution, deterministic FP32, one inter-op and one intra-op thread. Per-attempt temp/cache, CPU visibility and offline library settings passed. Runtime records the Windows Python redirector's underlying original argv and the verified venv executable hash. |
| Staged artifact SHA-256 against runtime manifest, read through `git cat-file blob :<path>` | All eleven deterministic evidence payload digests matched. |
| Packet `coordination/push.ps1 -ExpectedHead <full SHA>` from the author branch | Source and evidence commits published and remote refs verified. |
| Task-specific operating boundary | No new OCR, GPU release, training, generation, private truth, held-out data, external corpus acquisition, model download or threshold fitting. This author has not performed the independent review. |

## Change inventory and review map

All paths below are within `docs/research/WP-0035/` unless noted.

| Commit group | Exact changed files | Review focus |
| --- | --- | --- |
| Frozen sources | `admit35.py`, `trajectory35.py`, `measure35.py`, `trial.py`, `run.ps1`, `protocol.md` | Input authentication, observed designation and native execution, lossless measurement, execution controls and bound command |
| Evidence under `evidence/` | `admission.json.gz`, `anchors.json.gz`, `bindings.json.gz`, `calibration-parity.json`, `contrasts.json.gz`, `custody.json`, `effects.json.gz`, `metrics.json`, `runtime.json`, `scores.json.gz`, `terminals.json.gz`, `writes.json.gz`, `exit.txt`, `stdout.txt`, `stderr.txt` | Gates, binding receipts, raw results and terminal/trajectory analyses, runtime and process exit |
| Report metadata | `docs/agent-reports/eld-owner-probe/WP-0035/001_2026-11-24_research_eld-owner-probe.md` | Author interpretation and independent review handoff |
| External effects | `C:/Users/jackg/eLedgerCare-Speed/WP-0035/author/attempt-01`, public owned branch | Persistent authenticated staging and execution receipts, fast-forward publications |

The full numerical evidence includes separate per-horizon, answerability and safety counts. [Frozen author source](https://github.com/jackgumpe/eledgercare/tree/98328bf4e6fd240fecbf0ae91c2a03ad95071a6b/docs/research/WP-0035) · [All evidence and output files](https://github.com/jackgumpe/eledgercare/tree/65df68e86fe540c4c61ec2deba813e8d95b10da9/docs/research/WP-0035/evidence)

## Limits and handoff

These are exposed, synthetic development streams. Repeated physical pages and the matched opening limit claims about independent samples. The threshold produced no neural postings, so wrong-posting counts provide no evidence of precision at positive neural coverage. The observed scalar gates do not isolate every effect of vector erasure, child writes, pop and geometry. No follow-on execution is released. Independent numerical comparison and the coordinator's disposition remain pending. eld-rd-reviewer receives frozen source `98328bf4e6fd240fecbf0ae91c2a03ad95071a6b` and evidence `65df68e86fe540c4c61ec2deba813e8d95b10da9`.
