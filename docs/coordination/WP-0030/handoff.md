# Release Instruction: CPU-Only Per-Span Opening & Inter-Checkpoint Trace

**Authorization:** Jack approves reserving the next packet under standard repo policy as a strictly **CPU-only** diagnostic on the cached `WP-0029` `Alder` and `Cedar` artifacts.

## 1. Context & Question

`WP-0029` already applied the same fixed final posting query at all measured checkpoints, proving that the transitions from `After owner write` (`M1: -0.022006`, `M3: -0.017752`) to `End of opening` (`M1: +0.019793`, `M3: +0.004570`) and `Final posting` (`M1: +0.009357 / +0.006276`, `M3: +0.000499 / +0.000499`) reflect state changes between checkpoints rather than query changes. This packet locates exactly what happened between those checkpoints.

## 2. Exact CPU Procedure

1. **Per-Span Frozen Readout:**
   - Using the verified cached `Alder` and `Cedar` opening captures (and cached downstream windows from `WP-0029` for the 12-page and 30-page binders) together with the unchanged frozen `WP-0026` `M1` and `M3` weights and fixed final posting query, read both probes on CPU **after each individual span write** from initial state (`step 0`) through the end of the 3-page opening window, and continue per span write across the remaining cached spans through the 12-page and 30-page final postings.
   - Verify that the trace reproduces the published `WP-0029` checkpoint numbers bit-for-bit at the `After owner write`, `End of opening`, `12-page posting`, and `30-page posting` boundaries. Run `Alder` and `Cedar` recurrent states independently with zero cross-twin state reuse.
   - For every step, retain `step_index`, `window_index`, `page`, span role/event label, source span digest/excerpt, controller depth, per-twin owner scores `(Alder, Cedar)`, per-twin top-ranked owner, and the signed response to changing `"Ledger: Alder"` to `"Ledger: Cedar"`.

2. **Two Separate Required Findings:**
   - **Finding (1) — First Favorable Shift:** Report separately for `M1` and `M3` the exact span write at which changing the printed name from `Alder` to `Cedar` **first moves the scores in the right direction** (signed response `> 0`), including the preceding step's value, the triggering span's page/type/content, and any subsequent sign reversals or attenuation steps through the final posting.
   - **Finding (2) — Same-Step Paired Owner Ranking:** Report separately for `M1` and `M3` whether either probe **ever ranks the correct owner first for both twins at the exact same step** (`Alder` ranked first on the `Alder` binder AND `Cedar` ranked first on the `Cedar` binder simultaneously) anywhere along the trace. Do not conflate positive directional movement with a paired ranking win.

## 3. Verification & Hard Lane Boundaries

- **Independent Non-Author Reproduction:** Bind a separate non-author reviewer (excluding both cloud design participants) to independently reproduce the complete per-span trace, checkpoint parity with `WP-0029`, and both separate findings from the cached artifacts before coordinator disposition.
- **Strict Exclusions:** Zero GPU calls or model loads, zero retraining or threshold tuning, and zero architecture, weight, parser, or production-code changes. Keep Packet B, `Q0`, and the blind held-out answer key sealed, and stop after verified publication.