# WP-0017 reviewer decision procedure (pre-registered before any WP-0017 output exists)

Author: eld-rd-reviewer, independent of eld-rd-astra (design/fixtures) and eld-rd-carbon (switches/runtime). These rules are frozen with the tools at the commit that first contains this file. Each rule uses exact equality, an exact sign, or a number fixed by the specification. Where an author design (Astra 001) later declares a different rule for the same question, I do not choose between them. Root decides, and I bind a fresh tool SHA before the affected stage runs. No rule here is tuned or revised after outputs exist.

## Common custody (every stage)

1. **Release first.** Root signs a SHA-pinned outer lease: release file, digest, source, worktree, plan, and output root. I start exactly that command through `operate.py launch` and start a reviewer-owned detached `operate.py monitor`. There are no retries. A failed run stays visible, and a corrected harness needs a fresh source binding.
2. **Hash before reading.** Immediately after the lease returns, run `escrow.py --stage <A1|A2|A3>` over the run roots and bind the release/plan records and operator receipts by digest. Commit and push this inventory before any tool parses an output. Every later tool re-hashes the whole tree against the inventory and fails closed on any difference.
3. **Truth stays sealed.** A1 opens no truth key at all. In A2 and A3, keys are released by root only after the inventory commit and are passed only to the frozen `score.py` (SHA-256 `1ceb36fe…f4bf7`) in a separate `-I -B` OS process. Packet B is never resolved.
4. **Flags stay locked.** `flagged: false` remains on every span/cell (checked by `all_flags_false`). Margin flags are offline simulations only.

## A1: prefix-conditioned window forensics (windows 019 and 037)

Inputs are bound against [A1-prefix-audit.json](evidence/A1-prefix-audit.json) (SHA-256 `16eca676…63b3`). Tool: `a1_decide.py`, which works through an adapter that cites every source file by its inventory digest.

0. **Binding.** All 14 configurations are present exactly once: native, carbon_bf16, `add:Si` and `drop:Si` for Si ∈ {S0, S1a, S1b, S1c, S2, S3}.
   - Each switch vector must equal its configuration id.
   - Free windows must be uninstrumented and timed apart from the probes.
   - Probe spans must equal the audited spans. Native 019 is `" I08O1-388"` = `[342,3019,49,19,15,21895]`; carbon is `[223,6924,49,19,15,21895]`. Native 037 is `[26,90169,553,15,30591]`; carbon is `[1892,43,553,15,30591]`.
   - Probe prefixes must equal the audited digests: 019 common 417-token prefix `0206cf30…`, and 037 forced native 41-token prefix `0df32b06…`.
   - Each 037 free probe prefix must equal that configuration's own emitted prefix up to the audited line boundary.
1. **Replay gate.** The all-off free windows must reproduce the WP-0016 native sequences exactly: 019 `795dd68a…`, 037 `2fe3906d…`. The all-on free windows must reproduce the carbon_bf16 sequences: 019 `6dfc195c…`, 037 `aab3cbf2…`. If either fails, the outcome is `REPLAY_FAILED`. All telemetry is still published, but no switch effect is attributed.
2. **Reading per configuration and site.** The site page (page 21 of 019; page 37 of 037) emits `native`, `carbon_bf16`, `both` or `neither`, judged by byte containment of the public strings in the decoded tokens. A configuration **restores** when both sites read `native`.
3. **Attribution.**
   - `R` = {Si : drop:Si restores}. One member gives `SINGLE_CULPRIT`; more than one gives `MULTIPLE_SINGLE_REMOVALS`.
   - If `R` is empty, define the qualifying set `Q` = {Si : add:Si changes a site reading, or changes the exact FP32 value of ℓ(native) − ℓ(carbon) at the 019 common or 037 forced-native probe relative to all-off}.
   - The requested pair removals are all 2-subsets of `Q` and need a further root release. Once they have run:
     - one restoring pair gives `PAIR_CULPRIT`, and more than one gives `MULTIPLE_PAIR_REMOVALS`;
     - otherwise, if all-off restores, the outcome is `INTERACTION_ONLY`; if not, `UNRESOLVED`.
   - Clean unresolved and interaction-only outcomes are allowed.
4. **Window-037 prefix isolation**, per configuration, using the sign of ℓ(native) − ℓ(carbon):
   - favors carbon under the forced native prefix → `direct_at_identifier`;
   - favors native under the forced prefix and carbon under the free prefix → `upstream_prefix_cascade`;
   - favors native under both → `no_flip_under_either_prefix`;
   - anything else → `tie_or_mixed`.
   - The greedy top-1 at t* is reported beside the sequence log-probability, because the two can disagree.
5. **Margins.** These are reported only. For each probe: FP32 top-5, the margin z(1) − z(2) as reported and recomputed from the top-5, and both full-span log-probability sums.
6. **Local speed.** Uninstrumented free-window seconds summed over the two windows. Addition saving = T(native) − T(add:Si); removal cost = T(drop:Si) − T(carbon). These are single observations and local two-window effects, never generalised.
7. **Candidate list.** This is advisory. Restoring configurations are ordered by two-window time cost against carbon_bf16, with ties broken by switch order. Root freezes at most one `carbon_surgical` before any A2 output exists. I do not freeze it.

## A2: generalisation and speed stop-loss (dev/id_ablation, 18 pages)

Tool: `a2_stoploss.py`.

- **Orders.** Two orders. Each contains native, carbon_bf16 and carbon_surgical exactly once, and order 2 is the exact reverse of order 1. Each arm runs in a fresh process. The dev source and RGB pins are identical across all six arm requests. Position balance is reported: the middle arm keeps the middle position.
- **Rule.** ADVANCE only if, in **both** orders:
  - a complete matched native/surgical pair, matched critical paths, and every window stopped;
  - zero newly unflagged critical errors native→surgical in the same order. This means the trial is wrong and unflagged where the base was correct or flagged; one such path fails;
  - full-Carbon saving C = T(native) − T(carbon) > 0;
  - retention (T(native) − T(surgical)) / C ≥ 0.60.

  In addition, min over orders of (T(native) − T(surgical)) must exceed both repeat spreads, |ΔT(native)| and |ΔT(surgical)|.
- **Clock.** The durable `timing.json` `elapsed_s` (document committed − accepted).
- **Interpretation to be reconciled with Astra 001.** The rule is applied per order (both orders must pass), not pooled. Pooled retention is reported as telemetry only.
- **Otherwise.** `HALT_AT_A2`, with no 60-page GPU time.

## A3: full AB/BA escrow (H and A only)

The A3 tools are derived mechanically by `a3/derive.py` from the committed WP-0016 G0 escrow tools at `1e75ebe`. Only enumerated literal substitutions are allowed (carbon_bf16 → carbon_surgical, the A3 plan pin, the repo depth, record kind strings). The derived bytes are committed before any A3 run exists. G0 is applied unchanged:

- 100% complete pages, stops, and 0 new wrong-source links;
- ΔCER ≤ +0.01 and Δcell_acc ≥ −0.02, for both views and both orders;
- 0 newly unflagged criticals against the matched-order native;
- device peak ≤ 10,000 MiB, `static_cache_reallocations == 0`, and a positive A saving in both orders whose smaller value exceeds both |AB − BA| spreads.

`scorecard.py` adds the non-gate product scorecard: net repairs, repairs/sec against Windows (15.6546455 s), malformed headers, and flagged=false lock checks. It simulates margin flags only from a threshold file predeclared by SHA before A3 output exists.
