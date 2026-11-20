# WP-0020 / 004 · Archived identifier routing

**Close the packet as over budget.** Windows labels selected fields where ordinary Baidu could repair 2 critical readings on H and 60 on A. No correct critical became wrong. On the 60-page packet the rule requested every three-page window. The Windows pass consumed 15.65 seconds of the 120-second budget, and those Baidu windows used 1,056.21 seconds of archived engine time. The rule therefore fails the cost criterion for a fresh timed trial. [Coordinator measurements](../../../coordination/WP-0020/coordinator-results.json) · [Decision](../../../coordination/WP-0020/decision.json)

| Report record | Value |
| --- | --- |
| Path | `docs/agent-reports/eld-coordinator/WP-0020/004_2026-11-20_verification_eld-coordinator.md` |
| Author, publisher and category | eld-coordinator · verification |
| Environment | Continuous local Codex coordinator on Windows. Backend and applied effort unexposed. Three separately dispatched native Codex research sessions requested Astra and xhigh. |
| UTC | 2026-11-20T20:52:18Z |
| Repository and branch | Private jackgumpe/eledgercare · coordination/bootstrap |
| Starting integration and reservation | `d9b41fbcc0b2d5a7c0b5aa774cb9edc1ae2ce984` · `864753428a7afe5996fe1e411d286f58a6413b54` |
| Deliverable and disposition | `abb98468abf31efa8fc9e4ba8087dc7088adaf16` · completed and independently reviewed |
| Reports reviewed | [Routing /001](../../eld-routing-author/WP-0020/001_2026-11-20_research_eld-routing-author.md) · [Analysis /002](../../eld-routing-analysis/WP-0020/002_2026-11-20_research_eld-routing-analysis.md) · [Independent reviewer /003](../../eld-routing-reviewer/WP-0020/003_2026-11-20_review_eld-routing-reviewer.md) |
| Previous coordinator report | [WP-0019 /004](../WP-0019/004_2026-11-20_verification_eld-coordinator.md) |

## What the rule bought

| Exposed packet | Windows exact | Ordinary Baidu exact | Routed exact | Recovered | Regressed | Stayed right | Stayed wrong | Fields bound / selected | Windows bought / available |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H, 4 pages | 11/19 | 17/19 | 13/19 | 2 | 0 | 11 | 6 | 6/6 | 2/2 |
| A, 60 pages | 158/252 | 215/252 | 218/252 | 60 | 0 | 158 | 34 | 161/168 | 20/20 |

On H the rule recovered the two docket lines on pages 1 and 3. Page 1 had split the printed `88L1L-631` into `88L1 L-631`. Three table cells on page 2 and the handover line on page 4 accounted for all four missed native-right opportunities. Their labels did not trigger. The final one-page H window was purchased for one field.

On A, 29 inspection lines and 31 Valve ID cells recovered. The route preserved Windows on both discharge readings on pages 17 and 33 and on the unresolved inspection line on page 24. Those are the three locations where whole-document native scoring would have introduced critical errors. Every one of the 60 “Inspection register” headings also triggered. Of 168 selections, 60 contained no scored critical value. Seven selected prose fields retained Windows because five lacked usable single-line native text and two lacked sufficient overlap. Twenty-six of the 34 still-wrong criticals changed to a different wrong reading. The recovered total counts exact scorer transitions only. [Per-field opportunity and risk evidence](../../../research/WP-0020/analysis/evidence/A/fields.json) · [H field evidence](../../../research/WP-0020/analysis/evidence/H/fields.json)

The frozen scorer found no damage to previously correct noncritical fields, all 23 printed blanks, or previously correct spaced cells or full lines. H/A contain **zero critical identifiers with an intentional internal space**. That narrower protection remains untested. The route introduced zero review flags. [Cross-check across all scored fields](../../../coordination/WP-0020/scoring-reconciliation.json)

## Timing and cost

The full Windows times and actual native engine intervals come from matching archived ordinary runs, H `h-r1-ab` and A `a-recovery-ab`. The second H order supplies no additional cases. The serial lower bound adds the measured Windows document clock to the sum of the selected, nonoverlapping native engine intervals. It excludes native work outside those intervals and the router’s own manifest, binding and persistence overhead. The modeled sum of full document clocks includes the observed original native overhead because every native window was selected. Neither sum is a measured end-to-end hybrid run.

| Packet | Observed Windows s | Observed selected native engine s | Modeled serial lower bound s | Modeled sum of document clocks s | Target s |
| --- | ---: | ---: | ---: | ---: | ---: |
| H | 1.02 | 51.58 | 52.61 | 52.94 | 8 |
| A | 15.65 | 1,056.21 | 1,071.86 | 1,076.84 | 120 |

A had 104.35 seconds left for Baidu. Even the lower bound exceeded its total budget by 951.86 seconds. The accuracy screen identified valuable individual substitutions, while the archived inference unit remained a full three-page window. [Per-window timings and gate](../../../research/WP-0020/analysis/evidence/A/summary.json)

## Custody and reproduction

1. Verified the original archive inventories, page order, source hashes, WinRT spans, raw line boundaries and grids. The routing input contained only the Windows prediction, derived Windows layout and page/window schedule per family. Before the author manifest was committed, the coordinator inspected the key names of one historical H native window container through a metadata probe. Its text values were never shown to the selector, author or reviewer. The independent selection replay reproduced the manifest from the Windows-only allowlist. [Input admission](../../../coordination/WP-0020/windows-admission.json)
2. The label predicate used its original WP-0019 vocabulary without digit or crop heuristics. The candidate used top-left PDF-point coordinates, reciprocal unique overlap at IoU ≥ 0.5, equal table shapes for cell mapping and literal single-line native text for prose. Absent or ambiguous evidence retained Windows. Source froze at `b34c046e04ff98ddb0fb021ee8e8dade88a83126`; both manifests at `081acd13b7f26b3ea374a8ae3a2de79d71e9b0bf`. [Frozen method](../../../research/WP-0020/route/README.md) · [Manifest freeze](../../../coordination/WP-0020/manifest-freeze.json)
3. Admitted only the requested ordinary native windows, validated each original parse, and applied the title-level correction from `0186467670074761a777602d77b53deff3451300`. The routed predictions and reasons froze at `122652984a316c9b8963ec89cf1b61dd994aaf99` before keys entered scoring. Analyst source froze at `8ba03b56c2f99570c50b1d4782d38081f008c5a0`. [Native admission](../../../coordination/WP-0020/selected-admission.json) · [Immutable predictions](../../../coordination/WP-0020/predictions-freeze.json)
4. Ran `custody.py windows`, `selected` and `scoring` in sequence and `gate_check.py --scratch <wp0020-data> --archive <WP-0015/review> --out coordinator-results.json`. The coordinator invoked the frozen scorer six times in separate CPU processes. The common scorer SHA-256 was `1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7`. All 895 coordinator and analyst field entries matched across all three arms, as did all 174 binding decisions and both cost calculations. These 895 entries count the critical verdict separately from its containing line or cell. [Coordinator verification](../../../coordination/WP-0020/gate_check.py) · [Post-run integrity](../../../coordination/WP-0020/preservation.json)
5. A non-author independently rebuilt Windows selection, reproduced substituted/retained fields, and rescored the archive. Its pinned harness completed 15 CPU subprocesses, reproduced both manifests, decision lists and predictions byte-for-byte, and reconciled all three scorer arms. The independent disposition accepts the archive findings and closes the rule at the cost gate. [Independent reproduction](../../eld-routing-reviewer/WP-0020/003_2026-11-20_review_eld-routing-reviewer.md)

## Scope and handoff

The change inventory comprises packet-specific research, review, evidence, the four reports, and the two coordination ledgers. The work used CPU archive analysis of exposed H/A on isolated worktrees and normal private GitHub branches. It establishes retrospective accuracy and modeled serial cost for this candidate and archive. The 30-pages/minute gate stops this packet at disposition. [Complete inventory from base through disposition](https://github.com/jackgumpe/eledgercare/compare/d9b41fbcc0b2d5a7c0b5aa774cb9edc1ae2ce984...abb98468abf31efa8fc9e4ba8087dc7088adaf16)
