# eLedgerCare handoff | Does changing the ledger name change the memory readout?

**Recipient:** local `eld-coordinator` · **Prepared for Jack:** 22 November 2026, Eastern · **Status:** handoff for coordinator intake; unnumbered, not a GPU release.  
**Companion:** `Twin-Binder-Owner-Math-Reference.pdf` (one page). The formulas are also given below for CLI use.

## Mission and decision

Construct otherwise identical development binders in which the active parent named on the opening ledger declaration is **Alder** in one twin and **Cedar** in the other. Both names remain available in both. Measure the two **already trained, frozen** probes at the same three points. Decide whether a change in the name alone (a) is detectable to the frozen readout immediately, (b) remains detectable at the final posting, and (c) actually changes the winning owner in the correct direction. These are three different outcomes.

The [WP-0027 disposition](https://github.com/jackgumpe/eledgercare/blob/aa3bbd49e3cbe33cd8180b57108234c7056f3eda/docs/agent-reports/eld-coordinator/WP-0027/004_2026-11-22_verification_eld-coordinator.md) established that both probes ranked both original twins correctly in **0/8** answerable calibration pairs. Both scores moved toward the corresponding owner in **8/8**, but other earlier cues also varied. Sixteen answerable binders failed the owner threshold; four ambiguous binders lacked a target. At the permissive setting, eight owners per arm were correct but their postings failed another field. These facts motivate this experiment; they are not results on the new twins. The corrected terminal reader is closed on its reviewed cases. No parser work is needed here.

## 0 · Intake and scope

- Read `START_HERE.md`, `AGENTS.md`, `CURRENT.md`, and `INDEX.md` on `jackgumpe/eledgercare`. At drafting, `coordination/bootstrap` was [71e451d8eafdfa15245e522d347bdf781b0c57b7](https://github.com/jackgumpe/eledgercare/tree/71e451d8eafdfa15245e522d347bdf781b0c57b7). Re-resolve it locally. Reuse any existing equivalent reservation. Only the coordinator assigns an ID, paths, worktrees, authors, reviewer and report sequences.
- Research only, synthetic development material, frozen WP-0026 M1/M3 weights, original scorer and CPU probe runtime. No blind truth or new held-out examples, Packet B access, retraining, threshold tuning, embedding centering, donor swaps, production changes, or GPU calls under this handoff. Design authors may not independently accept their own work.
- Freeze the selected templates, identities, event definitions, controls, reporting schema, repeatability tolerance and stop conditions before looking at the controlled scores. Use the eight old answerable pairs as a **historical replay check**, never as eight new interventions.

## 1 · Admit the inputs before interpreting the scores

1. Aim for one pair on an existing short development layout and one on a longer layout (prefer the 12- and 30-page horizons if available). For each template, render the identical document twice with only the opening declaration's owner literal exchanged. Keep name list and order, font, cue box location, DPI, unit, schema, child/interruption, final target, geometry and ordering fixed. Record the source diff. Require exact pixel identity outside the declared cue-text region and byte-identical canonical rasters on every untouched page. Do not require byte-identical *PDF containers* or identical pixels inside the edited word. Freeze the manifest/target mapping; prevent truth labels entering the readout.
2. **Feature admission:** for each twin, bind each archived feature object to its actual source raster sequence, model/worker/recording revision and feature digest. Require authentic whole-window features for every edited-window input. Reuse identical suffix windows only under the accepted source-binding rules. A matching filename, decoded owner string or visually similar page is insufficient. Do not copy the old cue vector or modify parser text and call it an image-level experiment.
3. **If exact features are absent:** finish the fixture manifests, the historical CPU replay and a list of missing windows. Return the smallest separate native B=1/W0 acquisition proposal (exact unique windows, cached reuse, call/cost bound, independent verifier). Do not run it. A future intervention on cached internal state would test a narrower question and requires an explicit, separate label. If only one template is admissible, report exactly one pair, with the other blocked; do not substitute a confounded pair.
4. Repeat one identical-input read on CPU to verify deterministic scores and decisions. Check source-bound target query bytes, both eligible owner keys, and corresponding target identity within each admitted pair. If these differ, explain where comparability failed; a different target query cannot stand in for the fixed-query experiment. Do not demand identical downstream hidden states for the edited window: that is part of the response being measured.

## 2 · Replay the frozen readout

Use each arm's own frozen parameters. Within that arm and pair, hold its eventual target query fixed for all retrospective reads. No diagnostic read may write memory, advance the controller, or insert a target. Use a stable semantic candidate order for reporting (Alder, Cedar) while preserving native scoring. Key records by template, pair, binder, target, arm, checkpoint and candidate literal.

| Checkpoint | Capture at this exact boundary |
| --- | --- |
| t₁ · Opening cue | Immediately **after the write** for the active parent declaration. The registry update alone is too early. Record span/event pointer, depth, candidates, matrix/readout evidence, and query digest. |
| t₂ · End of first window | After all events and writes in window one, before window two. Query the actual state and actual depth. |
| t₃ · Final posting | At the original target's normal read **before its own write**. Require agreement with the frozen run's owner scores and typed decision. |
| Optional explanatory witness | If an actual `CONFIRM_POP` changes depth, label before/after snapshots at its true location with the same retrospective query. Keep those observations separate from t₃. Do not invent a pop for M1, or assume the final target coincides with a pop. |

Keep original scope/registry/target eligibility and exact zero/tie semantics. Log both owner scores, query and state/read digests, typed decision or abstention reason, target and candidate availability, and stable input links. At t₁/t₂ label all readouts retrospective; only t₃ is an actual posting opportunity. If unit/column scores are already recoverable as controls, log them separately without making them additional success gates. Check that enabling the recorder leaves the original trajectory and t₃ decision unchanged.

## 3 · Mathematics and interpretation

Use one axis for **both** twins at every checkpoint: Δ = score(Alder) − score(Cedar), not true owner minus rival. Let Δ_A and Δ_C denote this margin on the Alder- and Cedar-owned inputs. Then μ = (Δ_A + Δ_C)/2; δ = Δ_A − Δ_C; Δ_A = μ + δ/2; Δ_C = μ − δ/2. Positive δ is a correctly directed response; a **correct paired win** requires Δ_A > 0 > Δ_C. A tie on either twin is not a paired win. A negative δ must remain negative in the report.

Record the raw scores and signed μ, δ at all three checkpoints. Report absolute score-unit change δ(t) − δ(t₁) even when ratios are undefined. Report δ(t)/δ(t₁) only when the initial magnitude exceeds the preregistered repeatability/near-zero floor. Show raw precision; distinguish an exact native tie from an effect too small to interpret. A zero or missing denominator is not zero retention. Rankings are separate from the frozen minimum top-score and top-two-gap gates and from correctness of the complete posting. Do not apply the historical 85% fallback threshold to this diagnostic.

| Observed trajectory on admitted twins | Bounded conclusion / next engineering question |
| --- | --- |
| Little or no interpretable response already at t₁, or direction reversed | This frozen query does not discriminate correctly there. Check the input, first write, query and owner anchors before proposing longer memory. No proof that no owner information exists. |
| Correct separation early, lost by t₂ or t₃ | Name the first observed interval where separation is lost. Check whether δ shrank, μ grew, or both. Narrow the interval before attributing it to overwrite, decay, depth routing or a pop. |
| Positive δ persists but both twins favor the same name | There is a measured response to the controlled edit, smaller than the common preference for this pair. Investigate how the existing readout chooses a winner. No automatic threshold or centering patch. |
| Both owners win correctly at t₃ | Report the exact count, templates, horizons and typed gate outcomes. This is a development result on named fixtures, not blind accuracy, generalization or an M3 advantage over M2. |
| Mixed, tied, non-comparable, missing or unreproducible | Preserve each case and its reason. No pooling across arms or converting missing observations to zeros. |

## 4 · Independent review and closeout

Return (1) frozen fixture/source/feature manifest with matched-region checks and explicit missing inputs; (2) historical-replay receipt; (3) machine-readable raw scores, checkpoint pointers, derived μ/δ and decisions, with one readable trajectory per template and arm; (4) independent replay and coordinator disposition. Report planned/admitted/completed pair counts separately by arm and horizon. No sample expansion or picking a better seed after seeing results. Include command, candidate, weights and exact evidence revisions, inputs unavailable, and GPU calls (expected zero).

The non-author verifies fixture identity and separation, recomputes μ, δ, ties and paired winners from raw scores, checks the t₁/t₃ ordering and confirms frozen final decisions against uninstrumented results. Include controls for swapped reporting labels (holding the Alder-minus-Cedar score axis fixed, swapping binder labels reverses δ), an actual tie, and a near-zero or absent denominator. A blocked intake or negative finding can close this diagnostic honestly. Stop after review; recommend **one** follow-up, without treating it as a release.

### Pinned implementation and research references

- [Frozen owner scoring, reads, writes and pop ordering](https://github.com/jackgumpe/eledgercare/blob/7db67283a4ffd3e7a20bb8d80499572cc7118c71/docs/research/WP-0024/probe/matrix.py) · [Frozen calibration and whole-posting scorer](https://github.com/jackgumpe/eledgercare/blob/7db67283a4ffd3e7a20bb8d80499572cc7118c71/docs/research/WP-0024/probe/run.py) · [Fit and weights](https://github.com/jackgumpe/eledgercare/tree/6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc/docs/research/WP-0026/fit)
- [WP-0027 per-binder scores](https://github.com/jackgumpe/eledgercare/blob/0573f69c481eea2e815899e00ddd5e68bb4e3c42/docs/research/WP-0027/owners/owner-rankings.json) · [Checkpoint traces](https://github.com/jackgumpe/eledgercare/blob/0573f69c481eea2e815899e00ddd5e68bb4e3c42/docs/research/WP-0027/owners/owner-progression.json) · [Independent review](https://github.com/jackgumpe/eledgercare/blob/54eec948b5510601e2b06920e01f50e23722b58a/docs/agent-reports/eld-rd-reviewer/WP-0027/003_2026-11-22_review_eld-rd-reviewer.md)
- [Gemini's original mathematical proposal, pp. 1–3](https://chatgpt.com/library?file_id=libfile_fde3_f-470b63e8e9908191bb8996d9d8f35462_39f0d462e004819188632c0bb985a104&account_id=personal), retained for provenance. The tests above distinguish its hypotheses from measured findings; the coordinator need not access that private conversation to execute this handoff.
