# WP-0028 / 002 — Frozen owner readout and controlled-pair admission

| Record | Value |
| --- | --- |
| Report path | `docs/agent-reports/eld-owner-probe/WP-0028/002_2026-11-22_research_eld-owner-probe.md` |
| Reservation and category | [WP-0028 /002, research](https://github.com/jackgumpe/eledgercare/blob/c000c0299619345c887859b95c45befbb0c68987/INDEX.md#wp-0028-owner-only-matched-binders) |
| Author and publisher | `eld-owner-probe`, native Codex session `/root/w28_probe`. Requested xhigh. Exact backend and effective effort setting unexposed. |
| Environment | Windows PowerShell entry point, isolated Q0 Python 3.12.10, Torch 2.13.0+cu130, deterministic FP32 CPU, one intra-op and one inter-op thread, CUDA hidden |
| Time (UTC) | 2026-11-22T07:49:01Z |
| Repository and branch | Private `jackgumpe/eledgercare`, `research/wp-0028-owner-probe`, worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w028-probe` |
| Base | `c000c0299619345c887859b95c45befbb0c68987` |
| Protocol freeze | `3780eab7919108bf37c7fc32adfce0adb30da4e0` |
| Executed deliverable | `9cb018cecab739097abb9e1554e8c61768b257b0` |
| Evidence revision | `fcaf30465f0ce120c8077369155e4b624044baad` |
| Previous and related evidence | First report by this owner in WP-0028. [WP-0028 /001 admission deliverable](https://github.com/jackgumpe/eledgercare/blob/ee8e96afcbd7a3c1f3eaa8125c05e68003c4a893/docs/fixtures/WP-0028/manifest.json) · [WP-0027 independent review](https://github.com/jackgumpe/eledgercare/blob/54eec948b5510601e2b06920e01f50e23722b58a/docs/agent-reports/eld-rd-reviewer/WP-0027/003_2026-11-22_review_eld-rd-reviewer.md) |
| Status and next owner | Ready for review by `eld-rd-reviewer`, WP-0028 /003 |

## Summary

Neither new owner-only pair had complete archived features. Both edited binders need the same Cedar opening window. The controlled study has **zero measured pairs** at both horizons for both arms. All 24 member/checkpoint slots and 48 owner score slots are keyed and null. No native OCR or GPU call occurred.

On the eight historical answerable pairs, every final owner read exactly reproduced the archived logits and typed decision in both arms. Each arm ranked one twin correctly in each pair and abstained on all 16 binders. Historical twins also vary other earlier inputs. Their measurements support replay parity and arithmetic verification.

## Objective and criteria

Measure the effect of the single printed parent-owner edit at three points if both members have source-bound features and an identical eventual target query within each frozen arm. Preserve the selected native posting gates, score ordering, exact ties and missing observations. The preregistration pins the unit of analysis, tolerance, checkpoints, comparison and repeat tests. [Frozen protocol](https://github.com/jackgumpe/eledgercare/blob/3780eab7919108bf37c7fc32adfce0adb30da4e0/docs/research/WP-0028/protocol.md)

## Controlled trajectories and unavailable inputs

| Template | Arm | Planned | Admitted | Completed | After parent write | End of first window | Final target before write |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| T1, 12 pages | M1 | 1 | 0 | 0 | Unmeasured | Unmeasured | Unmeasured |
| T1, 12 pages | M3 | 1 | 0 | 0 | Unmeasured | Unmeasured | Unmeasured |
| T1, 30 pages | M1 | 1 | 0 | 0 | Unmeasured | Unmeasured | Unmeasured |
| T1, 30 pages | M3 | 1 | 0 | 0 | Unmeasured | Unmeasured | Unmeasured |

Both trajectories depend on ordered RGB triple `33362fbbeb37e805a64acbf3afdc3ec04315a4706820ed634a8fe0fb865ce2d5`. Its two uses are window 1 of Cedar binder `b1319c493624d146b9905f68` at 12 pages and window 1 of Cedar binder `64ca02ee321c80c200e01a1a` at 30 pages. The /001 manifest binds 26 of 28 logical windows and 10 of 11 unique windows. Each available Alder sequence remains withheld with its partner. Query, state, scores, tie, decision, μ, δ, D, ratio and paired-win entries remain null across both members. Role and candidate slot labels show the planned observation. All source IDs, PDFs, ordered RGB lists, final targets and reason codes are retained. [Controlled rows](https://github.com/jackgumpe/eledgercare/blob/fcaf30465f0ce120c8077369155e4b624044baad/docs/research/WP-0028/evidence/controlled.json)

## Historical replay and control results

| Arm | Answerable pairs | Positive δ at t₁ / t₂ / t₃ | Correct paired wins at t₁ / t₂ / t₃ | Target owner top-score pass | Target owner gap pass | Final typed result |
| --- | ---: | --- | --- | --- | --- | --- |
| M1 | 8 | 0 / 8 / 8 | 0 / 0 / 0 | 0/16 | 0/16 | 16 `below_threshold_owner` abstentions |
| M3 | 8 | 4 / 8 / 8 | 0 / 0 / 0 | 0/16 | 14/16 | 16 `below_threshold_owner` abstentions |

The two historical no-target pairs were identified from the source grammar before joining development truth and excluded from the eight-pair scope. Within each answerable pair, both members had identical whole final-window inputs, raw projected query bytes, target event and both eligible literals. At t₁ the first-window parent OPEN_LEDGER had just written (1,1,7). At t₂ the last span (1,3,15) had written. At t₃ the sole TARGET at (4,2,3) or (10,2,3) was about to score before its own write. Depth was zero at each of these historical checkpoints. All three use the same eventual query within each arm and pair. Prospective posting eligibility and the actual typed decision are recorded at t₃. Separate unit and column scores are included.

For the formula PDF’s M3 pair `03fe821e0efada96bdc61e31`, the final Alder/Cedar scores on the Alder member were 0.13470865786075592 and 0.031690359115600586. On the Cedar member they were 0.13285057246685028 and 0.029965657740831375. The fixed-axis margins were +0.10301829874515533 and +0.1028849147260189. Their μ was +0.10295160673558712 and δ was +0.00013338401913642883. Both favored Alder. The negative initial δ of −0.02105000615119934 gives a signed final D of +0.02118339017033577 and ratio of −0.006336531123950725. All four numbers printed in the source example reproduced to seven decimal places.

Swapping only the member labels on the unchanged literal axis reversed δ and preserved μ for all 16 historical pair/arm target rows. The strict paired-win and `δ > 2|μ|` predicates agreed at every measured checkpoint. Equal 0.125 synthetic leaders returned a boundary tie and no paired win. A separate actual frozen attempt on zero matrices produced two exact zero owner logits in each arm and the native `zero_state_tie` abstention. Zero, sub-floor, exact-floor and missing initial δ produced null ratios. A missing current checkpoint yielded null D and ratio. Negative denominators preserved their sign. The frozen diagnostic floor is 0.000001. [Historical raw scores and controls](https://github.com/jackgumpe/eledgercare/blob/fcaf30465f0ce120c8077369155e4b624044baad/docs/research/WP-0028/evidence/historical.json)

## Decisions and parity evidence

The numerical functions receive ordered windows, the frozen arm and fixed thresholds. IDs and truth stay outside scoring. For each of 32 historical arm/binder combinations, the harness independently loaded and traced the same inputs twice, starting from zero matrices each time. Runtime equality checks cover checkpoint score bytes, query/read/matrix digests, all final field logits, decisions, matrices and registry/controller state. A plain `state_for` execution and a second plain repeat verify native t₃. An uninstrumented audited `advance` traversal also matches the recorder's complete source-event trace and registry growth. Every stored WP-0027 snapshot matched after decoding the original JSON. The collector uses the frozen write return and attempt entry without advancing memory for retrospective reads.

## Change inventory and review map

All seven source files were added under `docs/research/WP-0028/` on the owned branch. [Exact source diff](https://github.com/jackgumpe/eledgercare/compare/c000c0299619345c887859b95c45befbb0c68987...9cb018cecab739097abb9e1554e8c61768b257b0)

| Path under the source directory | Purpose |
| --- | --- |
| `protocol.md` | Frozen identities, event boundaries, data admission and reporting contract |
| `run.ps1` | Owned offline CPU scratch, interpreter and process guards |
| `replay.py` | Verify pinned sources, stage archived calibration features/weights, run frozen arms, record receipts |
| `measurement.py` | Check query comparability, observe source checkpoints, repeat native reads and compare bytes |
| `historical.py` | Compare against WP-0027 before aggregating, externally join labels, verify example and swaps |
| `score_math.py` | Fixed-axis margins, signed change, ratio and null/tie controls |
| `controlled.py` | Bind /001 identities, guard exact features, create complete controlled rows |

Later evidence files under `docs/research/WP-0028/evidence/` are `historical.json`, `historical-runtime.json`, `controlled.json` and `controlled-runtime.json`. The subsequent report commit adds only this report. The owned scratch contains fresh `historical-r1` and `controlled-r1` directories under `C:/Users/jackg/eLedgerCare-Speed/WP-0028/probe`, each with read-only-source copies, local feature staging, caches and results. Both source archives and model weights were read from pinned Git objects. The sole external truth sidecar was development calibration with SHA-256 `a227da1293bcd6f8b0f636ce3349abd12d02a52361a46b47dbf34969cc773ff1`.

## Verification

Both commands were run from the owned worktree. The complete input/source SHA-256 inventory, interpreter/weight identity, CPU settings, output digests, wall time and arm timings are in the two runtime receipts. Frozen scorer `7db67283a4ffd3e7a20bb8d80499572cc7118c71`, fitted weights and transport `6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc`, historical observations `0573f69c481eea2e815899e00ddd5e68bb4e3c42`. [Historical runtime](https://github.com/jackgumpe/eledgercare/blob/fcaf30465f0ce120c8077369155e4b624044baad/docs/research/WP-0028/evidence/historical-runtime.json) · [Controlled runtime](https://github.com/jackgumpe/eledgercare/blob/fcaf30465f0ce120c8077369155e4b624044baad/docs/research/WP-0028/evidence/controlled-runtime.json)

```powershell
./docs/research/WP-0028/run.ps1 -Role probe -RunName historical-r1 -Mode historical -Candidate 9cb018cecab739097abb9e1554e8c61768b257b0
./docs/research/WP-0028/run.ps1 -Role probe -RunName controlled-r1 -Mode controlled -Candidate 9cb018cecab739097abb9e1554e8c61768b257b0 -FixtureRevision ee8e96afcbd7a3c1f3eaa8125c05e68003c4a893
```

Historical replay exited 0 in 7.8484 wall seconds / 6.0000 process CPU seconds. Controlled admission exited 0 in 4.9311 wall seconds / 3.53125 process CPU seconds. Each mode wrote deterministic result JSON. `Get-FileHash docs/research/WP-0028/evidence/*.json` confirmed historical SHA-256 `0db140d33dcfedba8787316ad4ef51b6ef2574db3dd15310d867212d74789d89` and controlled SHA-256 `080fe21cc127cc36f86620ff28306bc154320617cfece01bb911958ea5f715f5`. A separate standard-library JSON inspection checked four sets of 1/0/0 counts, 24 explicit missing reasons, all 48 null literal scores, null typed decisions and all 12 null derived rows. The /001 manifest’s SHA-256 was `cb058f1931758c516e21e2d791d5b5dffd04646bc773b8e967a11024fdf58cf2`.

## Limitations and handoff

The missing whole-window feature prevents measurement of early response, persistence and winner changes for the controlled edit. Native acquisition, blind data, model fitting and treatment runs stayed outside this execution. Historical scores provide no owner-only effect estimate.

Review owner `eld-rd-reviewer` receives the exact source, fixture and evidence revisions for independent execution, including recomputation of signed ratios, source-event timing, admissions and keyed nulls. Coordinator `eld-coordinator` owns subsequent disposition. The owned source branch was pushed and verified at the exact executable revision before report preparation. Final report publication confirmation travels separately.
