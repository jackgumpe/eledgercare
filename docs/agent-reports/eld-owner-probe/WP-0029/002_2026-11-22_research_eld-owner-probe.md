# WP-0029 / 002 — The printed owner changed scores at both horizons

| Report field | Value |
| --- | --- |
| Author and publisher | eld-owner-probe, research |
| Reserved path | `docs/agent-reports/eld-owner-probe/WP-0029/002_2026-11-22_research_eld-owner-probe.md` |
| Reservation and base | [INDEX at 4d94271a56f550bcf96b76d970f54e4c8b845ad5](https://github.com/jackgumpe/eledgercare/blob/4d94271a56f550bcf96b76d970f54e4c8b845ad5/INDEX.md) |
| Session | Native Codex collaborator `/root/w29_score`, exposed thread `01a204af-e0b1-7b53-8b8d-a593452facc8`. Requested effort xhigh. The tool exposes neither the resolved backend model identifier nor the applied effort. |
| Environment | Windows PowerShell launcher, CPython 3.12.10, PyTorch 2.13.0+cu130 operating on CPU with one thread and one interop thread |
| Repository and branch | Private `jackgumpe/eledgercare`, `research/wp-0029-cedar-scoring`, worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w029-score` |
| Frozen executable | `23c072549886ad9b5f2ab6bb08a98b0fcae423ff` |
| Deliverable with evidence | `841233517b4694d18d144f6d2d2b17e0d0a8b444` |
| Authored | 2026-11-22T19:27:32Z |
| Status and next owner | Ready for independent review by eld-rd-reviewer, WP-0029 /003 |
| Related records | [WP-0028 controlled measurement protocol](https://github.com/jackgumpe/eledgercare/blob/3780eab7919108bf37c7fc32adfce0adb30da4e0/docs/research/WP-0028/protocol.md) · [WP-0029 independent capture gate](https://github.com/jackgumpe/eledgercare/blob/f51fa1dadec3e3f0e61b1d3ddade1891e24779e2/docs/reviews/WP-0029/capture-gate.json) |

## Finding

Changing the printed parent from Alder to Cedar changed the owner scores at every observed checkpoint. Immediately after the owner write, the change moved both arms in the wrong direction. By the end of the first three pages it moved both in the expected direction. That positive response was smaller at the final posting and remained positive at both horizons. At no observed checkpoint did both twins rank their respective owner first, so there is no observed interval in which a correct paired win was lost.

M1 ranked Cedar first on both inputs throughout. Immediately after the owner write, M3 ranked Cedar on the Alder input and Alder on the Cedar input. By the end of the opening, M3 ranked Alder on both and kept that ranking through the posting. All eight final binder-by-arm decisions were `ABSTAIN / below_threshold_owner`. Only the final read had a native posting opportunity. The raw results include all 24 member-by-checkpoint reads and the original field scores, threshold checks and typed outcomes. [Controlled results](https://github.com/jackgumpe/eledgercare/blob/841233517b4694d18d144f6d2d2b17e0d0a8b444/docs/research/WP-0029/scoring/evidence/result.json)

## Fixed-axis scores

Each margin subtracts the Cedar candidate score from the Alder candidate score, including on Cedar inputs. A positive edit response δ means movement toward the correct owner. The strict joint criterion δ > 2|μ| failed at every checkpoint. There were zero exact owner-score ties. The signed ratio uses the immediately-after-write δ for its own arm and pair. Both denominator magnitudes exceeded the frozen 0.000001 floor. Values below are rounded for display. The JSON preserves the full precision and both raw scores on each member.

| Arm | Pages | Checkpoint | Alder-input margin | Cedar-input margin | Shared preference μ | Edit response δ | Change from first δ | Signed ratio |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| M1 | 12 and 30 | Just after owner write | −0.059760 | −0.037754 | −0.048757 | −0.022006 | 0 | 1 |
| M1 | 12 and 30 | End of opening | −0.103874 | −0.123667 | −0.113770 | +0.019793 | +0.041799 | −0.899458 |
| M1 | 12 | Before posting write | −0.062611 | −0.071969 | −0.067290 | +0.009357 | +0.031363 | −0.425233 |
| M1 | 30 | Before posting write | −0.047820 | −0.054096 | −0.050958 | +0.006276 | +0.028282 | −0.285204 |
| M3 | 12 and 30 | Just after owner write | −0.001311 | +0.016442 | +0.007566 | −0.017752 | 0 | 1 |
| M3 | 12 and 30 | End of opening | +0.087505 | +0.082935 | +0.085220 | +0.004570 | +0.022323 | −0.257452 |
| M3 | 12 | Before posting write | +0.100969 | +0.100470 | +0.100719 | +0.000499 | +0.018251 | −0.028099 |
| M3 | 30 | Before posting write | +0.100969 | +0.100470 | +0.100719 | +0.000499 | +0.018251 | −0.028099 |

The two early rows per arm combine horizons after byte comparison of projected queries and both owner scores for each member. At the final posting, both M3 raw float32 score pairs were also byte-identical across horizons. Both M1 score pairs differed. The longer fixture adds six interruption windows to the same opening intervention.

## Objective and evidence chain

The release covered one independently authenticated opening and two matched development pairs scored against two fixed arms. All four planned arm-by-horizon pairs were admitted and completed. The scorer matched all 28 logical uses to 11 physical triples. The ten archived triples supplied 26 uses. Both Cedar binders independently loaded the same eleventh record at window one. Each numerical traversal began with fresh zero matrices, controller, registry and attempts. Each member's input comprised only the frozen sequence of original spans and FP32 features.

The original grammar found a unique depth-zero parent at (1, 1, 7) on both inputs. Its value matched the printed owner in each case. Both owner candidates were present at all three checkpoints. The last opening span was (1, 3, 15). The target row was `Posting 241 851` in both twins at (4, 2, 3) or (10, 2, 3). The final source triple and feature bytes were common to the twins, and the projected arm-specific query bytes matched within each pair. The 12-page and 30-page members reused this source at different ordinals. The observer read immediately after the parent write, after the final opening span write, and on entry to the posting attempt before its own write. The earlier reads used the eventual target query.

The independent gate on archive revision `48016df280f8f0c2f4a807955d9f431744347ecc` authenticated the native return, SHA-256 `0346091957994fcfc5c12d8d87e40ce177bb0c1ff0cc376b5ba8f4fb7cb2522f`. After the coordinator released the exact gate digest, the adapter checked the archive, each gate-listed ZIP member, ordered source PNG/RGB values, original receipt-to-artifact links and pooled-feature identity. It routed the old windows from the immutable original manifest and independently compared their six record digests against the manifest. The runtime receipt lists every consumed Git object and digest. [Independent authentication](https://github.com/jackgumpe/eledgercare/blob/f51fa1dadec3e3f0e61b1d3ddade1891e24779e2/docs/reviews/WP-0029/capture-gate.json) · [CPU runtime](https://github.com/jackgumpe/eledgercare/blob/841233517b4694d18d144f6d2d2b17e0d0a8b444/docs/research/WP-0029/scoring/evidence/runtime.json)

## Verification and change inventory

The exact invocations from the owned worktree follow. Both exited 0. They wrote only beneath the role's fresh `C:/Users/jackg/eLedgerCare-Speed/WP-0029/scoring/{controls-r1,released-r1}` directories. The Q0 interpreter ran with CUDA hidden and offline library settings. Neither invocation issued a native OCR or GPU call.

```powershell
pwsh -NoProfile -File docs/research/WP-0029/scoring/run.ps1 -Role scoring -RunName controls-r1 -Mode controls -Candidate 23c072549886ad9b5f2ab6bb08a98b0fcae423ff
pwsh -NoProfile -File docs/research/WP-0029/scoring/run.ps1 -Role scoring -RunName released-r1 -Mode released -Candidate 23c072549886ad9b5f2ab6bb08a98b0fcae423ff -GateRevision f51fa1dadec3e3f0e61b1d3ddade1891e24779e2 -GateSha256 03e7eb07feae1f25c8db1fb4a7141820f0bda8497ab1b539bb4dbe169c51f870
```

| Check | Author observation |
| --- | --- |
| Historical controls | The complete WP-0028 Alder checkpoints and parity receipts matched at both horizons on both arms. Each authentic Alder opening failed an expectation of Cedar. Denied pairs retained nulls. Both arms passed the native zero-state tie and signed arithmetic controls. The M3 PDF example reproduced at seven places. |
| Numerical parity | On every scored member, two fresh source loads and independent traversals agreed on all checkpoint records. Plain, repeated plain, audited and both observed final-state receipts matched. Audit traces agreed. Native target logits for all fields and final matrices passed the frozen observer parity checks. |
| Costs and identities | Controls used 7.7221 seconds wall and 4.09375 seconds CPU. Released scoring used 5.6643 seconds wall and 4.265625 seconds CPU. Result SHA-256 `93a6054a9f8b4db7a9e231e843ee6681cf55968e85e6adde5d31959c2cdeae1e`. Control SHA-256 `b3a3aaa3b4c99c59571f192c0231911f7abcb111daa1be7d2c08e9a2e897c44d`. |
| Post-run checks | `Get-FileHash` verified the published copies. For each owner and arm, the final score values were packed with Python `struct.pack("<ff", alder, cedar)` and compared across horizons. `git diff --cached --check` passed before the source and evidence commits. `git ls-remote --heads origin refs/heads/research/wp-0029-cedar-scoring` returned the published evidence revision. |

| Added path beneath `docs/research/WP-0029/scoring/` | Contents |
| --- | --- |
| `admission.py` | Pinned library, weights, ten historical routes and authenticated Cedar admission |
| `scoring.py` | Actual eligibility, isolated original measurements, parity, paired arithmetic, cross-horizon bytes and negative controls |
| `run.ps1` | Isolated Q0 interpreter, CPU guards, role-owned fresh scratch and gate arguments |
| `evidence/result.json`, `evidence/runtime.json` | Released controlled trajectories and input, source and runtime digests |
| `evidence/controls.json`, `evidence/controls-runtime.json` | Historical regression, denial and signed arithmetic controls with CPU receipt |

The reserved report is publication metadata committed after the evidence. The exact source and evidence revisions are on the owned branch. [Source diff](https://github.com/jackgumpe/eledgercare/compare/4d94271a56f550bcf96b76d970f54e4c8b845ad5...23c072549886ad9b5f2ab6bb08a98b0fcae423ff) · [Control results](https://github.com/jackgumpe/eledgercare/blob/841233517b4694d18d144f6d2d2b17e0d0a8b444/docs/research/WP-0029/scoring/evidence/controls.json) · [Control runtime](https://github.com/jackgumpe/eledgercare/blob/841233517b4694d18d144f6d2d2b17e0d0a8b444/docs/research/WP-0029/scoring/evidence/controls-runtime.json)

## Limits and handoff

The observations cover one opening edit, two related development fixtures and two fixed probes. Checkpoint comparisons locate a change in direction between the owner write and the end of the opening. They leave its exact span and mechanism unresolved. Held-out memory accuracy and product behavior remain unmeasured. The acquisition operator owns the device execution evidence and the independent reviewer owns its authentication. The remaining /003 work is non-author verification of the controlled scoring source, arithmetic, state resets, eligibility, capture reuse, repeated traversals and native parity. The coordinator owns the final disposition.
