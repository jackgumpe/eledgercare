# eLedgerCare | What reverses the owner ranking at write 8?
**Cloud review + local coordinator handoff · 2026-11-22 · Proposed CPU diagnostic, unnumbered**

Jack: give this document to Gemini Cloud with Prompt 1. Then give the local coordinator the same document with Prompt 2 and Gemini’s verdict or amendments. The operating instructions are in the two prompts; the shared math and evidence below apply to both. This document does not reserve a packet or release a job.

## Prompt 1 — Gemini Cloud: review the intervention

Review the proposed four-way replay in Prompt 2 against the pinned source and WP-0030 evidence below. We want to distinguish the effect of the state entering the owner declaration from the effect of the declaration’s complete input on a frozen probe. M3 ranked the two binders backwards immediately after that write. The posting query was **already fixed**. Do not propose another per-span trace.

Return **accept**, **amend**, or **blocked**, with the smallest necessary change. In particular, check (1) the boundary between the saved state and the donor event, (2) whether the donor input preserves native full-window projection and event ordering, (3) whether the two diagonal controls really establish comparability, and (4) what a crossed result can and cannot tell us about the model. Cite exact files or source functions for objections. Treat combinations that never occurred in an original binder as interventions. If you see a cheaper discriminating control, state which ambiguity it resolves. Return your advice to Jack; no repository writes, execution, assignment or independent-verifier signoff.

## Prompt 2 — Local coordinator: bounded CPU replay

**Decision to support.** At the actual page-one declaration, does changing the declaration input move the owner margin the wrong way even when the incoming state is held fixed? Or does the preceding state change the response to that declaration? Test both frozen probes, M1 and M3, on the one shared development opening. A favorable or unfavorable finding is equally acceptable.

1. **Admit the lane.** Check the live eLedgerCare CURRENT.md, INDEX.md and AGENTS.md against the pinned closeout. If this experiment has already been run or assigned, return its actual status instead of duplicating it. Under normal local release authority, record the adopted design and any Gemini amendments, reserve the lane and assign a fresh non-author reviewer. Use the qualified one-thread CPU replay. Keep model weights, queries, candidate anchors/order, original captures and thresholds unchanged. Do not open held-out material, run OCR, lease the GPU, retrain, or change production code.
2. **Snapshot before either owner event.** For each probe, replay each original opening through write 7. Save two independent states, including all matrices, controller and registry. The fork point is **before any write-8 event or update**, at the aligned pointer (window 1, page 1, span index 7). Confirm that the actual literals there are “Ledger: Alder” and “Ledger: Cedar.” Check the native write-7 reads against the archived trace. Do not substitute one shared pre-state merely because the preceding printed text agrees.
3. **Apply a complete donor update.** For each cell in the table below, start from a fresh copy of the row state. Take the column donor’s original write-8 span, ordered events and its native projected write inputs (key, value, alpha, beta) from the original full window. Preserve the donor’s feature/box binding and apply events, controller and registry transitions, then the matrix write in the original order. Projecting a one-span minibatch or swapping only the name string is a different experiment. Read immediately after the write using the frozen eventual posting query and the frozen literal owner anchors. Record both raw scores, their margin, winner or tie, eligibility, depth and relevant input/state digests. This is a retrospective read; do not create a posting or assign a correctness label to an artificial binder.

| State after write 7 ↓ / donor at write 8 → | Alder declaration | Cedar declaration |
|---|---|---|
| Alder prefix | AA — original control | AC — intervention |
| Cedar prefix | CA — intervention | CC — original control |

4. **Gate the swaps on native parity.** Reproduce both original diagonals for each probe: exact score bytes, query and read digests, post-write matrix identity, registry and controller state as available in the frozen trace. M3 must reproduce Cedar first on AA and Alder first on CC. Match archive bytes; the printed decimal values below are orientation checks only. A mismatch blocks interpretation for that probe. Do not adjust inputs or thresholds until the result looks plausible. The 12- and 30-page originals share the same opening: use the second horizon as a digest check, not another specimen.
5. **Return the result.** Publish one labeled 2×2 margin table per probe, backed by raw per-candidate scores and all contrasts below. Recreate the results in a separate non-author CPU replay from the pinned inputs; check donor orientation, state isolation and phase ordering explicitly. Report any blocked cells as missing, not zero. State which contrast would justify inspecting the declaration update, the prefix, or their interaction next. Stop at write 8. No tuning, new binder, or architecture change is included.

## Math reference — the quantity to measure

Use the same Alder-minus-Cedar axis everywhere. For one probe at a time, let \(i\) denote the prefix donor and \(j\) the declaration donor, each in \(\{A,C\}\). Let \(S_i^{(7)}\) be the complete pre-event state; \(U_j^{(8)}\) the full declaration update; and \(q_\star\) the fixed, arm-specific eventual posting query. With \(F\) the frozen transition and \(\ell_o\) the frozen owner score,

$$
S_{ij}^{(8)}=F(S_i^{(7)},U_j^{(8)}),\qquad
m_{ij}=\ell_A(S_{ij}^{(8)},q_\star)-\ell_C(S_{ij}^{(8)},q_\star).
$$

A positive \(m\) ranks Alder first; a negative \(m\) ranks Cedar first; zero is a tie. The observed native difference is \(\delta_{\rm native}=m_{AA}-m_{CC}\): approximately −0.022005513 for M1 and −0.017752446 for M3. A negative native difference alone does **not** mean both owners rank backwards: that requires \(m_{AA}<0<m_{CC}\), observed for M3.

At fixed incoming state, compare the declaration donors. At fixed declaration, compare the prefix donors:

$$
D_A=m_{AA}-m_{AC},\quad D_C=m_{CA}-m_{CC};
\qquad
P_A=m_{AA}-m_{CA},\quad P_C=m_{AC}-m_{CC}.
$$

Report the interaction and the algebra check:

$$
I=D_A-D_C=P_A-P_C,\qquad
\delta_{\rm native}=D_A+P_C=P_A+D_C.
$$

Compute contrasts from losslessly retained native scores using the same arithmetic convention as WP-0030. If both \(D\)'s are negative, changing Cedar’s declaration bundle to Alder’s shifts the margin toward Cedar at either fixed prefix. Opposite signs indicate that the direction depends on the incoming state. Report magnitudes even when no winner flips. Exact zero, a small nonzero contrast and a missing result are different outcomes. No significance test is warranted for one opening edit. A bundle effect does not by itself distinguish the hidden vector from the box, parser, controller or readout; a prefix effect does not identify an earlier line as its cause.

## Pinned evidence and implementation references

- [Coordinator routing at the checked head](https://github.com/jackgumpe/eledgercare/blob/a33ac75d454e33c74183a85670daa3bf9980d7cb/CURRENT.md) · [reservation index](https://github.com/jackgumpe/eledgercare/blob/a33ac75d454e33c74183a85670daa3bf9980d7cb/INDEX.md) · [governance](https://github.com/jackgumpe/eledgercare/blob/a33ac75d454e33c74183a85670daa3bf9980d7cb/AGENTS.md). At drafting, WP-0030 is closed. Live routing governs admission.
- [WP-0030 disposition](https://github.com/jackgumpe/eledgercare/blob/df8c8a4e3d94592165fa371d55aa25380f1dcf38/docs/agent-reports/eld-coordinator/WP-0030/003_2026-11-22_verification_eld-coordinator.md) · [precision correction](https://github.com/jackgumpe/eledgercare/blob/c76c313f06393b3172a06cdc4098130f3b8d5f2d/docs/agent-reports/eld-coordinator/WP-0030/004_2026-11-22_verification_eld-coordinator.md) · [independent review](https://github.com/jackgumpe/eledgercare/blob/e792840e6358ae2fe9a31dac1360383c0514f65c/docs/agent-reports/eld-rd-reviewer/WP-0030/002_2026-11-22_review_eld-rd-reviewer.md).
- [Frozen transition: matrix.advance and model.project](https://github.com/jackgumpe/eledgercare/blob/7db67283a4ffd3e7a20bb8d80499572cc7118c71/docs/research/WP-0024/probe/matrix.py) · [independent replay with fixed query](https://github.com/jackgumpe/eledgercare/blob/603cfbc85c259112fb76ea7c1b9c514557149653/docs/reviews/WP-0030/replay.py) · [authenticated step records](https://github.com/jackgumpe/eledgercare/blob/7d65875a1ff2d7ad8a008ea83f5484507dbd5db3/docs/reviews/WP-0030/evidence/steps.jsonl).
