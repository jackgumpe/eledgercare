# WP-0035 / 002 Independent full-horizon and calibration review

- Report path: `docs/agent-reports/eld-rd-reviewer/WP-0035/002_2026-11-24_review_eld-rd-reviewer.md`
- Reservation: WP-0035 /002 at `d8db225dae2c2ea4d70896c1936a1e1e22a104e2`
- Category and author: review, eld-rd-reviewer
- Execution environment: fresh local Codex subagent, thread `01a20bdc-db62-7fe1-8b1b-d4dd9b47ae36`, coordinator-assigned gpt-6.2-astra/xhigh. The thread ID was exposed locally. The parent supplied the model/effort configuration.
- Timestamp: 2026-11-24T04:57:57Z
- Repository and branch: jackgumpe/eledgercare, `review/wp-0035-trajectory`, worktree `w035-review`
- Base revision: `d8db225dae2c2ea4d70896c1936a1e1e22a104e2`
- Reviewed deliverable and evidence: `98328bf4e6fd240fecbf0ae91c2a03ad95071a6b` and `65df68e86fe540c4c61ec2deba813e8d95b10da9`
- Independent deliverable, numerical evidence and later cross-check: `520c3dab56ce12976616a4b6c654613e6e285155`, `43a3464b50154a1d800ce9fe3b56f3c226e574b4`, `e7646336c8fc720d84dd46cdfca4caf4a3400ee4`
- Related report: [WP-0035 /001](https://github.com/jackgumpe/eledgercare/blob/67f085fa55ade219ae5381b8b467c9ebc1656da3/docs/agent-reports/eld-owner-probe/WP-0035/001_2026-11-24_research_eld-owner-probe.md). Previous report in this assignment: none.
- Status: accepted for the bounded diagnostic. The next owner is eld-coordinator for /003.

## Summary

Every neural write/readout combination ranked both binders correctly in **0/2 development horizon pairs** and **0/8 answerable exposed calibration pairs** at the true posting read. Per combination, neural typed outcomes were 0 correct postings, 0 wrong postings and 4 abstentions on development, and 0 correct, 0 wrong and 16 abstentions on answerable calibration. All four safety binders returned `no_target` in every arm. Symbolic M2 produced four correct development postings and sixteen correct calibration postings, plus four safety abstentions. The two development horizons share one opening. The eight calibration pairs were already exposed. These cohorts provide no empirical basis for capturing the 16 proposed fresh pairs to validate these variants.

The independent run reproduced all archived native readings and all four write-8 crossed controls, then generated its evidence before seeing the new author's source, evidence or report. Subsequent comparison matched all 2,880 member score rows, 1,440 paired FP64 rows, 312 binder decisions and 10 ordered calibration custody records. The score comparisons include exact FP32 logits, binary64 scores and gaps, cutoff decisions and matrix, owner-column, query and response hashes. [Cross-check](https://github.com/jackgumpe/eledgercare/blob/e7646336c8fc720d84dd46cdfca4caf4a3400ee4/docs/reviews/WP-0035/evidence/cross-check.json) · [Auxiliary verification](https://github.com/jackgumpe/eledgercare/blob/e7646336c8fc720d84dd46cdfca4caf4a3400ee4/docs/reviews/WP-0035/evidence/auxiliary-cross-check.json)

## Objective and acceptance criteria

Jack's five-page release (SHA-256 `e7efb9a2371fedb28e6bbd43c00ac88f8128e73239e62a87d5eb2addd175a749`) requested a full trajectory, authenticated calibration custody, four terminal decision metrics and independent reproduction. The frozen data plan bound the actual per-binder window order, target and exposed expected fields. The independent implementation re-read the original captures, reproduced native gates first, then applied the prescribed writes/readouts and native symbolic control. It checked the author's actual implementation, computed evidence and /001 after its independent publication.

## Results and interpretation

Every neural terminal top score fell below the fixed 1.0 cutoff. The table counts single-binder terminal failures in the order **score only / both score and gap**, with zero gap-only failures and zero passages throughout. Each Task A column covers four binders and each Task B column covers sixteen answerable binders. At each of 12 and 30 pages, Task A has one pair and two answerable binders. Task B has four answerable pairs and eight answerable binders, plus one separate safety pair and two safety binders. Thus each neural regime ranked both members in 0/1 and 0/4 pairs respectively at each horizon. Gap cutoff was 0.1 under native FP32 subtraction. Owner-only and complete typed C/W/A counts coincide here. Retrospective scores before candidate registration and scores inside an ambiguous scope retain their eligibility flags and do not count as native postings.

| Model and write | A R0 | A R1 | B R0 | B R1 |
| --- | ---: | ---: | ---: | ---: |
| M1 W0 | 0 / 4 | 4 / 0 | 0 / 16 | 15 / 1 |
| M1 W1 | 0 / 4 | 1 / 3 | 6 / 10 | 10 / 6 |
| M1 W2a | 0 / 4 | 3 / 1 | 0 / 16 | 15 / 1 |
| M1 W2b | 0 / 4 | 3 / 1 | 0 / 16 | 15 / 1 |
| M3 W0 | 4 / 0 | 4 / 0 | 14 / 2 | 16 / 0 |
| M3 W1 | 4 / 0 | 4 / 0 | 16 / 0 | 16 / 0 |

- **Declaration erasure.** M1 W1-R0 recovered all four write-8 donor rankings. On each development horizon it ranked both original binders correctly at writes 8, 10 and 11. Its terminal differential improved from 0.0093574785 to 0.0144119393 on 12 pages and from 0.0062760673 to 0.0107951984 on 30 pages. Terminal simultaneous-win margins remained negative at −0.07131602 and −0.05196982.
- **Downstream erasure and retention.** Under R0, M1 W2a reduced W1's terminal differential to 0.0129089057 and 0.0093246717. Changing retention to one raised those to 0.0130291097 and 0.0094138682. The measured conventional loss in absolute separation from write 8 to 11 is **39.6554% for native M1** (with a sign reversal) and **98.4977% for native M3**. For M1 W1-R0, absolute separation increased over that interval. Both horizons have 13 relevant post-declaration root writes before posting. Every measured αβ on those writes was below one. Native cumulative root retention was about 0.9786–0.9787 on M1 and 0.9627–0.9632 on M3. These observables qualify the PDF's causal hypothesis. They do not isolate causation during the remaining child events.
- **Readout.** R1 centered the final raw anchor rows within each binder and normalized using native EPS and the native response direction. Raw anchor norms differed for both models (M1 0.09315 and 0.07098, M3 0.05446 and 0.06174). R1 and native difference axes had cosines about 0.9233 and 0.9909. The maximum component of the centered unit-row sum was 6.71e−8 and 3.91e−8 respectively. The equal-norm scalar magnification formula does not specify the observed score ratio. Across the eight answerable calibration pairs, every combination ranked exactly one member correctly. Native δ was positive on 8/8 for each model, while M1 W1-R1 and M3 W0-R1 each had positive δ on 6/8. Positive directional change and correct ranking for both binders are distinct measurements.
- **Custody and symbolic controls.** The exposed calibration had ten tier-1 pairs, twenty binders, 140 ordered window references and 29 physical captures. The two safety pairs had full streams and zero target events. The development construction used four distinct binder IDs, 28 ordered windows and eleven physical captures. It inherited unchanged non-owner fields through each public base binder and target. Both runs preserved the two cohorts. All input windows and all 24 binder outcomes per model/write/read configuration defined for that model are accounted for. Full numerical evidence includes the required write 7, 8, 9, 11, 12, child, pop and terminal checkpoints, all signed effects, and the separately labeled post-target diagnostic.

## Verification and review map

| Check on exact revisions | Result |
| --- | --- |
| Authenticate PDF, read scope, source and exposure rules, and join calibration transport to WP-0027 public records. Run `python -I -B docs/reviews/WP-0035/bind.py preflight-01` then `preflight-02` using the frozen runtime, adding the prior WP-0033 parity receipt to the second binding. | Both completed. The historical private truth loader was never called. The [bindings](https://github.com/jackgumpe/eledgercare/blob/520c3dab56ce12976616a4b6c654613e6e285155/docs/reviews/WP-0035/bindings.json) record the exact archive-member hashes, binder, target, and byte order. |
| From w035-review under CPU release `296e32ad26fb2ad931248ff45fe143192a688d1b`, execute `C:/Users/jackg/eLedgerCare-Speed/WP-0030/runtime/venv/Scripts/python.exe -I -B docs/reviews/WP-0035/run.py 520c3dab56ce12976616a4b6c654613e6e285155`. | Exit 0 on the first and only trial attempt. CPU-only Torch 2.13.0, Python 3.12.10, deterministic algorithms, offline library flags, one intra-op thread and one inter-op thread. Tool session 44782. [Timing and hashes](https://github.com/jackgumpe/eledgercare/blob/43a3464b50154a1d800ce9fe3b56f3c226e574b4/docs/reviews/WP-0035/evidence/execution.json) |
| Compare honest native W0-R0, fresh W1-R0 crossed substitutions, and exposed native calibration. | All 224 paired native points matched original score, margin, δ, controller, registry and available tensor identities. AA/AC/CA/CC scores, matrices and reads matched WP-0033. All 40 native calibration binder/probe outputs matched the original under frozen cutoffs, with exact field logits and available query/response identities. |
| Inspect the six author source files via `git show 98328bf4e6fd240fecbf0ae91c2a03ad95071a6b:docs/research/WP-0035/<file>`. Read the native `matrix.advance`, `attempt`, `anchors`, `online.identify`, `Discrete` and original receipt loader. | The author wraps native advance and observes writes after native event/target handling. The reviewer independently walks the stream, preserves the native pop, and calls actual attempt before writing. The terminal variant swaps only owner logits. Full-window projections, batch shapes and per-binder raw anchor identities agree. The source is [pinned here](https://github.com/jackgumpe/eledgercare/tree/98328bf4e6fd240fecbf0ae91c2a03ad95071a6b/docs/research/WP-0035). |
| Compare public bytes via `python -I -B docs/reviews/WP-0035/compare.py 65df68e86fe540c4c61ec2deba813e8d95b10da9` then `python -I -B docs/reviews/WP-0035/audit_comparison.py` under the same WP-0030 interpreter. | Both exit 0. Matches include 144 raw/native/centered anchor records, 816 terminal field score vectors, 1,680 signed effects, 117 population/arm entries, 144 downstream summaries, all 24 attenuation records, 203 calibration archive member hashes and 66 development member hashes. |
| Inspect author /001 at `67f085fa55ade219ae5381b8b467c9ebc1656da3`. | The zero simultaneous rankings, cutoff breakdown, M2 results, maximum top score 0.2970581352710724, transient write-8/10/11 wins, and fresh-capture recommendation agree with my evidence. /001 explicitly discloses the 48 trailing updates across answerable calibration binders per neural write configuration. |

The author completed the final calibration window after each answerable terminal attempt. My independent calibration replay stopped at the last native prewrite target. We compared **7,752 shared writes** (1,296 development and 6,456 calibration), including every write through the measured terminal state, the development post-target diagnostic, and complete no-target safety streams. The author-only suffix comprises **288 updates** (96 writes of the target span, 192 later writes) across 16 answerable binders × 6 neural write configurations. Both runs excluded these from terminal scores and preposting dynamics. No additional outputs or targets occurred. These 288 unscored updates were counted and inspected in the author's evidence, with no independent inference claimed for them.

## Change inventory and handoff

| Revision | Exact paths and effects |
| --- | --- |
| `520c3dab56ce12976616a4b6c654613e6e285155` | Added `docs/reviews/WP-0035/{README.md,bind.py,bindings.json,metrics.py,observe.py,run.py}`. These files contain source, procedures and pre-execution custody. |
| `43a3464b50154a1d800ce9fe3b56f3c226e574b4` | Added `docs/reviews/WP-0035/evidence/{anchor_geometry.json.gz,attenuation.json.gz,contrasts.json.gz,custody.json.gz,execution.json,mechanism_differences.json.gz,metrics.json.gz,parity.json,scores.json.gz,stock_calibration.json.gz,terminals.json.gz,writes.json.gz}`. |
| `e7646336c8fc720d84dd46cdfca4caf4a3400ee4` | Added `docs/reviews/WP-0035/{compare.py,audit_comparison.py}` and `docs/reviews/WP-0035/evidence/{cross-check.json,auxiliary-cross-check.json}`. |
| Report publication | Added only this reserved /002. Used `coordination/push.ps1` for owned branch publications. Before this report the remote contained all three listed independent revisions. |
| Local scratch | `C:/Users/jackg/eLedgerCare-Speed/WP-0035/review/{preflight-01,preflight-02,520c3dab56ce12976616a4b6c654613e6e285155}` retain checked bytes, caches and execution evidence. The CPU process exited and the lease was returned before author evaluation. |

The diagnostic warrants closure within its exposed-data scope. The four safety abstentions and zero wrong postings establish behavior for the observed inputs at the frozen thresholds. Every answerable neural attempt also abstained. No fresh-cohort accuracy or posting performance was measured. No GPU, OCR, model fit or acquisition was run.
