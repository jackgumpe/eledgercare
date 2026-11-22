# WP-0029 / 004 · Cedar capture and owner readout disposition

**Accepted and closed.** Changing the printed owner changed both frozen probes’ scores. Neither probe ranked the correct owner first for both twins at any measured checkpoint. All eight original final posting decisions were `ABSTAIN` with reason `below_threshold_owner`. [Machine-readable disposition](https://github.com/jackgumpe/eledgercare/blob/1839f0b405eebb3bc5989ecf5443b02b08dec485/docs/coordination/WP-0029/decision.json)

| Report field | Record |
| --- | --- |
| Author and publisher | eld-coordinator, receiving Codex CLI session registered in CURRENT.md. The effective backend and effort were unexposed. The operator, scorer and independent reviewer worked in three fresh native sessions, each requested at xhigh. |
| Status, category, timestamp | Accepted · verification · 2026-11-22 19:31:55 UTC |
| Repository, branch, worktree | Private jackgumpe/eledgercare · coordination/bootstrap · C:/Users/jackg/Asp.net Projects/eledgercare |
| Canonical report | docs/agent-reports/eld-coordinator/WP-0029/004_2026-11-22_verification_eld-coordinator.md |
| Base and reservation | `1b5fad0140e1c54c636b2348ae6dc6c6610c8b21` and `4d94271a56f550bcf96b76d970f54e4c8b845ad5` |
| Deliverable | `1839f0b405eebb3bc5989ecf5443b02b08dec485` includes the decision and the three integrated roles. |
| Previous report | [WP-0028 / 004](https://github.com/jackgumpe/eledgercare/blob/eb82bd6bcbad5da0f33c335fb731996647175699/docs/agent-reports/eld-coordinator/WP-0028/004_2026-11-22_verification_eld-coordinator.md) |
| Reviewed work | [001 acquisition](https://github.com/jackgumpe/eledgercare/blob/eb932d8aa5daf8d0f5f378c8f1276172678042e3/docs/agent-reports/eld-cedar-operator/WP-0029/001_2026-11-22_research_eld-cedar-operator.md) · [002 CPU scoring](https://github.com/jackgumpe/eledgercare/blob/bb1e075268d06dfa866d46b6a6b9815baa94fe22/docs/agent-reports/eld-owner-probe/WP-0029/002_2026-11-22_research_eld-owner-probe.md) · [003 independent acceptance](https://github.com/jackgumpe/eledgercare/blob/7d87328e2650d7583f4fe3a805f70f9c5081b76c/docs/agent-reports/eld-rd-reviewer/WP-0029/003_2026-11-22_review_eld-rd-reviewer.md) |
| Next owner | Jack and the cloud coordinators for a decision on the single recommendation below. |

## Native acquisition

The reviewer confirmed that the opening actually emitted **“Ledger: Cedar”** at window 1, page 1, span 7, with both Alder and Cedar eligible. The operator used one fresh native Baidu BF16 load at batch size one. Its excluded W0 matched all 62 pre-EOS IDs and the archived through-EOS hash. Cedar returned 332 token IDs plus EOS. The independent verifier traced 332 normalized decoder rows into the language-model head and reproduced all 16 FP32 pooled span vectors from 118 selections of those rows. All 18 Q0 model objects and the notice matched their original identities after the release. [Raw return](https://github.com/jackgumpe/eledgercare/blob/48016df280f8f0c2f4a807955d9f431744347ecc/docs/research/WP-0029/acquisition/native-return.zip) · [Independent capture gate](https://github.com/jackgumpe/eledgercare/blob/f51fa1dadec3e3f0e61b1d3ddade1891e24779e2/docs/reviews/WP-0029/capture-gate.json)

| Resource | Observed |
| --- | ---: |
| Cold model load | 34.322 s |
| Excluded W0 | 26.788 s |
| Cedar window including capture | 37.641 s |
| Complete supervised job | 101.125 s of 180 s |
| Peak sampled board memory | 8,580 MiB across 239 samples, with a 12,500 MiB ceiling |
| Free board memory at admission and return | 14,799 MiB at each check |
| Native calls, retries | 2 calls, 0 retries |

## What the printed edit changed

The signed response δ measures how much the Alder-owned input favors Alder relative to the Cedar-owned input, on the same scale. A positive value means the edit moved the relative scores in the expected direction. Both rankings are correct only when the Alder-owned margin is strictly positive and the Cedar-owned margin strictly negative. The response and the shared preference μ jointly determine that condition. The subsequent table gives δ in native score units. [Raw scores, margins, μ, δ, ratios and typed decisions](https://github.com/jackgumpe/eledgercare/blob/3b38b3d87c8a76e5b5106938771e0731f7647b8d/docs/coordination/WP-0029/reconciliation.json)

| Frozen probe | Immediately after owner write | End of opening window | Final posting, 12 pages | Final posting, 30 pages |
| --- | ---: | ---: | ---: | ---: |
| M1 | −0.022006 | +0.019793 | +0.009357 | +0.006276 |
| M3 | −0.017752 | +0.004570 | +0.000499 | +0.000499 |

M1 ranked Cedar first on both inputs at every checkpoint. M3 initially reversed the two owners, ranking Cedar first on the Alder input and Alder first on the Cedar input. By the end of the opening M3 ranked Alder first on both inputs and retained that ranking at each final posting. The direction of the edit response reversed between the owner write and the end of the first window for both probes. It remained positive, with smaller magnitude, at both final postings. A correct paired ranking never held at an observed checkpoint, so there is no observed interval of loss. Intermediate writes were unobserved. [Per-member events and final decisions](https://github.com/jackgumpe/eledgercare/blob/841233517b4694d18d144f6d2d2b17e0d0a8b444/docs/research/WP-0029/scoring/evidence/result.json)

Each arm at each horizon planned, admitted and completed one pair. The four arm–horizon comparisons give 12 paired checkpoints and 24 individual reads. The two horizons reuse one physical name edit and one Cedar capture. Ten historical captures supply the remaining inputs. Fresh recurrent state was used for each binder and arm. Candidate names, source-bound final posting, final features and projected query agreed within each twin pair. Each arm’s early queries and scores were byte-equal across horizons. The longer fixture adds six interruption windows. At the posting the M3 owner scores were also byte-equal across lengths even though its full matrices differed. M1’s final scores differed across lengths. [Independent recomputation and parity evidence](https://github.com/jackgumpe/eledgercare/blob/9371eafa5dc3fde10bc512d401a31fb5076d2f80/docs/reviews/WP-0029/score-comparison.json)

## Source, changes and verification

| Scope | Exact revisions and checks |
| --- | --- |
| Intake and resource authority | The supplied Markdown and PDF bytes matched their committed objects at `4d94271a56f550bcf96b76d970f54e4c8b845ad5`. INDEX.md and CURRENT.md identify the roles, paths and prior reservation. |
| Coordinator integration | In docs/coordination/WP-0029, assignment.md, handoff.md and owner-math.pdf record scope. cedar_plan.py binds W0 and the matched three-page Cedar opening. cedar_worker.py invokes the historical worker. cedar_guard.py owns the exclusive hardware lock, Windows job and independent deadline. These scripts froze at `5014124e485d5ce89b9191e23458f12cc178bdcd`. The bound plan/release JSON at `fc42ba82075e10114855b3ac648cff7a5c562466` pin 52 source entries. device-dispatch.json and score-dispatch.json record separate live and CPU gates. reconcile.py, reconciliation.json and decision.json record arithmetic and disposition. |
| Operator | docs/research/WP-0029/acquisition contains the CPU identity and packaging scripts, three evidence JSON files and the 770,072-byte native ZIP. The operator checked all 31 fixture rasters before running the single released guard. Raw ZIP SHA-256 `0346091957994fcfc5c12d8d87e40ce177bb0c1ff0cc376b5ba8f4fb7cb2522f`. |
| CPU author | docs/research/WP-0029/scoring contains admission.py, scoring.py, run.ps1 and the archived control, result and runtime records. The frozen adapter at `23c072549886ad9b5f2ab6bb08a98b0fcae423ff` ran with CUDA hidden on one CPU thread. It retained the original weights, thresholds, measurement code and scorer. |
| Independent reviewer | docs/reviews/WP-0029 contains the preflight, raw authentication, score reconstruction, comparison, replay receipts and their Python sources. The reviewer verified the job/deadline and six PNG/RGB pairs before dispatch, then authenticated the stream before scoring. All 48 native field logits checked at the final postings and all eight final typed/state comparisons agreed. |
| External effects | Four dedicated sibling worktrees, owned scratch under C:/Users/jackg/eLedgerCare-Speed/WP-0029, one exclusive GPU order, immutable primary archive and normal private branch pushes. The reviewer confirmed the guard, launcher and native PIDs exited. |
| Reports and ledger | Each author published their own canonical report. This /004 and the final closure/publication receipt are later metadata. The exact changed paths through the deliverable are in the [integrated comparison](https://github.com/jackgumpe/eledgercare/compare/1b5fad0140e1c54c636b2348ae6dc6c6610c8b21...1839f0b405eebb3bc5989ecf5443b02b08dec485). |

The binding and launcher commands are recorded with absolute paths, exact SHA-256 arguments and execution worktree. The independent preflight approved the 180-second watchdog and verified job closure on a disposable CPU process before native dispatch. [Device order](https://github.com/jackgumpe/eledgercare/blob/72bfa494e280020e3d7f306f75d3812e75eb90c8/docs/coordination/WP-0029/device-dispatch.json) · [Preflight findings](https://github.com/jackgumpe/eledgercare/blob/3674ed58b88184abaececbef601c49602af69489/docs/reviews/WP-0029/preflight.json)

The CPU author and independent reviewer reproduced result SHA-256 `93a6054a9f8b4db7a9e231e843ee6681cf55968e85e6adde5d31959c2cdeae1e`. I separately ran the command below with Q0 Python 3.12.10 and verified the resulting SHA-256 `28275d953b8ff6f81acba27309133bd42c793fb1ffefc0a5ca5c3a238d0a4165`. It recomputes the margins and both-owner test, preserves the signed initial denominator and verifies the early score bytes and query identities across lengths. [CPU dispatch](https://github.com/jackgumpe/eledgercare/blob/55c4011d7ce6032d3c7888fcecdf1a56f292755e/docs/coordination/WP-0029/score-dispatch.json) · [Independent score comparison](https://github.com/jackgumpe/eledgercare/blob/9371eafa5dc3fde10bc512d401a31fb5076d2f80/docs/reviews/WP-0029/score-comparison.json)

```powershell
& 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe' -I -B docs/coordination/WP-0029/reconcile.py 841233517b4694d18d144f6d2d2b17e0d0a8b444 f51fa1dadec3e3f0e61b1d3ddade1891e24779e2 docs/coordination/WP-0029/reconciliation.json
```

## Recommendation

Use the cached Alder and Cedar opening features to read both frozen probes after each remaining span write in window one, holding the eventual target query fixed. This CPU diagnostic would locate the first write after which the response becomes favorable and show whether both owners ever rank correctly between the two observed checkpoints. The present measurements establish the interval on this single development edit.
