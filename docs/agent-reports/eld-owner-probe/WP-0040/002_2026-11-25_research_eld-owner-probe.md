# WP-0040 / 002. Selective reread decisions on signed-ledger CPU controls

| Report field | Record |
| --- | --- |
| Author and publisher | eld-owner-probe |
| Category and status | Research, ready for independent review |
| Report path | `docs/agent-reports/eld-owner-probe/WP-0040/002_2026-11-25_research_eld-owner-probe.md` |
| Reservation and base | [WP-0040 / 002 at 2a9b44f](https://github.com/jackgumpe/eledgercare/blob/2a9b44f86151f6976846094259771a14efcdbfcd/INDEX.md#wp-0040-selective-reread-custody-intake-and-cpu-decision-controls), full base `2a9b44f86151f6976846094259771a14efcdbfcd` |
| Repository and branch | jackgumpe/eledgercare, `research/wp-0040-reread`, worktree `w040-author` |
| Actual model, effort and execution environment | Native gpt-6.2-astra, xhigh, Codex CLI 0.171.0 on Windows, thread `01a213b4-fab2-7ba3-9fdd-1daa2732ef50`, parent `01a20a53-eec1-72c1-864c-9f8be8f4aff5`. Own session metadata and turn context verified. |
| Frozen policy | `9502f458a89f48523714cf03ac3d4c7d9cdc69f0` |
| Raw evidence | `aecab0939edf1945221a0614f0d558131a7556f6` |
| Related prior author report | [WP-0039 / 001](https://github.com/jackgumpe/eledgercare/blob/633c4e14f291fc15b841dc337a49cac1bad6b204/docs/agent-reports/eld-owner-probe/WP-0039/001_2026-11-25_research_eld-owner-probe.md) |
| Timestamp | 2026-11-25T17:25:06Z |
| Next owner | eld-rd-reviewer for non-author source audit and WP-0040 / 003, then eld-coordinator for disposition |

## Objective and outcome

Implement a planner and decoder that consumes the frozen distances, preserves signed ledger values, and returns the entire compatible set for each complete reread. The coordinator's blinded schedule produced 1,623 author returns with zero exceptions. The coordinator found agreement with the independently frozen route on all 1,623. These calls comprised 1,440 synthetic grid-arm calls, 100 named-arm calls and 83 constructed controls. The coordinator owns the schedule, scorer, reconciliation and custody decision. [Frozen dispatch](https://github.com/jackgumpe/eledgercare/blob/c7a8d2d0343ee5aa286709a9af56eafc3080fcd0/docs/coordination/WP-0040/dispatch.json)

## Decision and decoder

E chooses the fewest cells attaining distance one and decodes exactly. R chooses the fewest attaining the lesser of three and the prior full distance, then allows one mismatch. Both retain all minimum-cardinality feasible masks and choose among them by summed area and numeric mask. B passes through a singleton and withholds on ambiguity. The other four real arms inherit the same singleton at zero views. R, F and T require full distance of at least two on ambiguous inputs. F and T decode their respective supplied full reads separately. The selected mask and prior distance remain available on a failed or incomplete return.

For a nonconstant affine family, a moving cell improves the generic mismatch count only at its exact integer root. Signed divisibility and the exclusion list determine whether that root contributes. All other allowed integers have the same cost. If they fit the radius, the result includes the original family with its exclusions and all surviving finite points outside it. Otherwise only qualifying roots and finite points survive. Deduplication uses every signed coordinate. For primary queries with distance at least two, two distinct family members already differ on at least two selected coordinates. Generic parameters therefore exceed radius one and the set of survivors is finite.

The full distance guard is defensive for balanced admitted ledgers. A difference in a single coordinate cannot solve the homogeneous balance equations because each mutable coordinate has a nonzero column. An isolated malformed pair exercises the guard. A repeated identical ledger exercises singleton inheritance. The slope-two helper with y=(3,4) on both coordinates has just the integral root c=2, unless excluded. Querying only the first coordinate gives one mismatch for every parameter and an infinite radius-one result.

## Control evidence

In the 288-case grid, 76 singletons were inherited in all five arms. The other 212 records had full distances of two, three and four in 23, 155 and 34 cases respectively. The 34 distance-four cases comprised 6 at two rows with an OCR opening, 4 at two rows with a trusted opening, 16 at three rows with an OCR opening and 8 at three rows with a trusted opening. A distance of four between candidates requires disjoint two-cell error supports. An incidence-graph difference with four edges in these simple graphs is supported on a four-cycle. The 189 cases with at least distance three can guarantee correction of one wrong cell under in-set truth and correct binding. The constructed rereads on the grid resolved all 848 E/R/F/T ambiguous calls. [Coordinator score and grid partition](https://github.com/jackgumpe/eledgercare/blob/fa2d1ccd375b746f140bf3c781fb0aa8db891e3b/docs/coordination/WP-0040/results/summary.json)

For C9a the two minimum distance-two triples were masks 7 and 14 in (amount, opening, closing, total) order. Changing the constructed areas selected each triple in turn. Equal areas selected mask 7. A wrong amount on the first triple or a wrong total on the second left two compatible ledgers in R. F and T each recovered (11,100,111,11) from those returns. The C9b one-error return had full distance three and resolved to (11,111,11). In C2 the wrong resolutions on `c2_allowed` and `c2_hole0` each had two wrong returned endpoint values against the constructed in-set truth, exceeding the radius-one premise. The separate absent-truth example resolved wrongly even on an exact candidate readout. In the E-only control, E was wrong and all three redundant arms were correct. [Signed decisions and returns](https://github.com/jackgumpe/eledgercare/blob/fa2d1ccd375b746f140bf3c781fb0aa8db891e3b/docs/coordination/WP-0040/results/control.jsonl)

| C1 constructed endpoints | Returned amount and total | Active survivors | Shared errors | F and T full result |
| --- | --- | ---: | ---: | --- |
| 100, 112 | 11, 11 | 2 | 0 | Ambiguous, 2 |
| 100, 112 | 11, 12 | 2 | 1 | Inconsistent, 0 |
| 100, 111 | 11, 12 | 1 exact | 1 | Resolved, 1 |
| 100, 111 | 12, 12 | 1 exact | 2 | Inconsistent, 0 |

Every candidate has the same mismatch cost on a shared cell. If two candidates survive at active radius one, neither can match exactly, because distinct candidates differ in at least two active cells. A shared error eliminates both. A separate C9a control had minimum active mismatch four, so F and T were already empty on the active cells alone.

In the author raw rows, 486 complete F/T calls returned diagnostics. Nine full decisions were empty. For seven of those, the active-only radius-one set was still nonempty. For two, active errors alone excluded every candidate. The full and active-only counts make this attribution possible from the same readout. A full exact match requires zero errors in both groups.

On the C6 illustration, three selected moving balances, all four moving balances and all eight cells have theoretical recovery probabilities of 97.20%, 94.77% and 81.31% respectively. With in-set truth and minimum distance at least three, correct recovery occurs exactly for zero or one returned errors. Independent identical error probability 0.10 gives these numbers by the binomial formula. The fourth moving balance accounts for the first reduction and the four constant cells for the second. Splitting the remaining probability between wrong resolutions and abstentions requires a wrong-value distribution.

## Change inventory and verification

| Revision | Exact paths or external effect |
| --- | --- |
| Candidate `9502f458a89f48523714cf03ac3d4c7d9cdc69f0` | Added `docs/research/WP-0040/policy.py`. The sole entry point is `evaluate(r)`. The helpers `_select`, `_decode` and `_constant_cells` implement acquisition choice, signed set intersection and shared-cell classification. |
| Evidence `aecab0939edf1945221a0614f0d558131a7556f6` | Added `docs/research/WP-0040/evidence/.gitattributes`, `docs/research/WP-0040/evidence/run-01/outputs.jsonl.gz` and `docs/research/WP-0040/evidence/run-01/runtime.json`. The attributes keep the two raw file blobs byte-identical to the original output. |
| Report metadata | Added this reserved report after the source and evidence freezes. |
| Local and remote effects | The serial run wrote raw bytes under `C:/Users/jackg/eLedgerCare-Speed/WP-0040/author/run-01`. Author-only local scratch held report notes. The scoped publication helper performed normal pushes to the owned public branch and verified the candidate and raw remote tips. |

The coordinator froze the driver, input schedule and scorer at `c7a8d2d0343ee5aa286709a9af56eafc3080fcd0` before releasing the serial lane. CPython 3.12.10 executable SHA-256 was `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`. Policy SHA-256 was `d56afc94840b177d06ad205b01f2a8b3efd669512938a9bc44453c0ffce73096`. The PDF SHA-256 matched the assignment. The author and independent raw returns froze before cross-exposure.

```powershell
python -I -B '../../eledgercare/docs/coordination/WP-0040/operate.py' --candidate 9502f458a89f48523714cf03ac3d4c7d9cdc69f0 --planner docs/research/WP-0040/policy.py --observations 'C:/Users/jackg/eLedgerCare-Speed/WP-0040/author/inputs.jsonl' --input-sha 5d6b94d6ff62f5b6be389bd079fde9e52f9c33e513ba5fc20c1edaa853638a61 --out 'C:/Users/jackg/eLedgerCare-Speed/WP-0040/author/run-01'
```

One run exited 0. The retained interval was 17:21:24.900689–17:21:24.945284 UTC. The sequential loop took 37,708,200 ns wall and 31,250,000 ns process CPU, including compressed-output writes. Per-call evaluate time summed to 22,904,500 ns, ranging from 1,000 to 96,000 ns. No inference or reader acquisition time was measured. SHA-256 for the compressed output was `2f0bb4fb03c30bd73881aea9c963ccd1b2853539b7d651b88fcd58a068398684`, and the runtime receipt was `df132a0a0eb46eef92eb9b5461f6e3cfcc65d422b15cfd860253d2dcea603436`. [Raw evidence and timings](https://github.com/jackgumpe/eledgercare/tree/aecab0939edf1945221a0614f0d558131a7556f6/docs/research/WP-0040/evidence/run-01)

AST parsing and `git diff --cached --check` passed for the source. After copying the evidence, the first `git rev-parse` check used Windows path separators for an index path and failed before commit. The corrected check used slash-separated Git paths and compared both staged blob IDs with `git hash-object --no-filters` on the originals. Both matched. This packaging correction did not rerun the experiment. The exact source and dataflow are available for independent inspection. [Candidate diff](https://github.com/jackgumpe/eledgercare/compare/2a9b44f86151f6976846094259771a14efcdbfcd...9502f458a89f48523714cf03ac3d4c7d9cdc69f0)

## Limits and handoff

The page 5 decision hierarchy places any leak, failed in-model CPU control or newly wrong R/F/T resolution versus B ahead of a winner decision. Every E-only new error is reportable and by itself leaves R and T eligible. Insufficient families, no ambiguous pages or missing cost evidence gives a feasibility result. H1 requires a new correct recovery on an ambiguous family, zero newly wrong resolutions and zero lost correct B resolutions. H2 requires strictly fewer aggregate R views than F with at least as many correct outcomes and no more wrong on the eligible matched pages. In a complete clean comparison, R must pass recovery H1 and cost criterion H2, be at least as often correct and no more often wrong than T, and finish strictly faster. T must pass H1, be at least as often correct and no more often wrong than R, and use no greater aggregate serial reader time. A tie in time precludes an R win. If neither contender satisfies its conditions, report the trade-off.

The recorded physical cohort contained zero families, so the full-cohort and ambiguous-stratum event rates and limits are undefined. In an illustrative independent representative sample with zero observed events, the one-sided 95% upper limits would be 11.73% at n=24 and 25.89% at n=10. [Physical feasibility record](https://github.com/jackgumpe/eledgercare/blob/fa2d1ccd375b746f140bf3c781fb0aa8db891e3b/docs/coordination/WP-0040/physical.json)

This work covers bounded synthetic decisions. Physical truth membership, OCR return quality and correlations, authentic box binding, costs, recovery and safety rates require independently admitted physical families and frozen real reader returns. No physical, protected, device or production resources were used here. eld-rd-reviewer owns acceptance of this exact candidate and inspection of the coordinator's scorer. eld-coordinator owns the intake disposition and public byte receipt.
