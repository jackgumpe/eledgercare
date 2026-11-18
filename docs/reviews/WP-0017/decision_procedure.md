# WP-0017 reviewer decision procedure: synchronized with Astra design 1fad21c (pre-output)

Author: eld-rd-reviewer, independent of eld-rd-astra (design/fixtures) and eld-rd-carbon (switches/runtime).

The first version of this file was frozen at `9a1fbb9`. This revision follows the coordinator's synchronization instruction of 2026-11-18, which was received before any WP-0017 model output existed. It adopts the published design at `1fad21c3817be175628992a559e3947d5a88952a` (`PROTOCOL.md` `fe915bba…`, `rules.py` `678f27d5…`) and the coordinator interface in `WP-0017/coordination/roles-interface.txt`. No WP-0017 A1, A2 or A3 output has been produced or read.

My implementation is independent. Astra's `rules.py` is loaded from its pinned blob only as a cross-check of restoration ranking, pair eligibility and A2 arithmetic. Any disagreement between the two is recorded as a failure and is never resolved silently. Nothing is tuned after outputs exist.

## Common custody

1. **Release and command**
   - Root publishes `<name>-release.json` and its digest.
   - I independently review the release with `command.py review`. That review checks:
     - the release bytes and digest;
     - the operator, stage, GPU UUID and stage ceiling (A1/A2 14,500 MiB diagnostic guard, A3 10,000 MiB);
     - the executor `device_lease.py` and the carrier `review_command.py` against their reviewed digests;
     - the coordination files;
     - that the replay worktree's HEAD equals the candidate, that it is clean, and that every source-file digest matches;
     - that each order plan's digest, stage and source match, that each output root is new, that public input pins match, and that no custody or truth input is present.
   - Only after all of that do I write `commands/<name>.json` (`command.py issue`), commit it, and push it on `review/wp-0017-escrow`.
   - The coordinator's passive carrier executes that exact pinned lease once. It runs as an eld-coordinator Windows process using `docs/coordination/WP-0017/review_command.py` at `d17669e`, SHA-256 `c5596d0e…`.
2. **Hash before reading.** Right after the lease returns, I run `escrow.py --stage <A1|A2|A3>` over the run roots. It binds the release, plan and carrier receipts by digest. I commit and push that inventory before any tool parses an output.
3. **Keys.**
   - A1 opens no truth key.
   - For A2, the dev key `dfdf62cb…` is released only after the inventory commit and is passed only to the frozen `score.py` (`1ceb36fe…`) in a separate `-I -B` OS process.
   - For A3, the H/A keys are handled the same way.
   - Packet B is never resolved.
4. **Flags.** The original `flagged=false` behavior is left intact and checked. Margin flags are offline only, with a strict top-two gap below 0.125 logits as predeclared in `PROTOCOL.md`. A margin from a forced branch is never transferred to a free-emitted field.
5. **Infrastructure errors.** An A1/A2/A3 infrastructure error (crash, missing output, harness fault) is recorded as `INFRASTRUCTURE_ERROR`. It is not treated as an engine result. It needs cause inspection and a new source binding before any re-execution.

## A1 (windows 019 and 037), `a1_decide.py`

- **Anchors.** These are frozen before output in `evidence/A1-anchors-reviewer.json`, built from the audit `16eca676…` and the manifest `e7f47d14…`. Each field has a unique structural locator: site page (third page of 019, first page of 037), raw block ordinal 1 (the public `line/2`), block header type `text`, fixed label `Inspection `, and byte offset 11. The value runs to `\n` or the end of the block. The ordinal and header type are part of the locator because the page header `Inspection register` also begins with the label.
  - The ordinary free ID is read only at that site. I never search for either competing value.
  - A missing, malformed or moved field, or an abstention, fails restoration. It is counted separately and is never treated as a flip.
- **Prefixes and branches**
  - Each probe conditions on the frozen token-ID prefix: 019 uses the native 417-token prefix `0206cf30…`; 037 uses the native 41-token prefix `0df32b06…` plus each configuration's own free prefix, aligned structurally at that block's byte boundary (10 bytes for 019, 11 for 037).
  - The branches are the audited full spans: 019 `[342,3019,49,19,15,21895]` versus `[223,6924,49,19,15,21895]`; 037 `[26,90169,553,15,30591]` versus `[1892,43,553,15,30591]`. The first divergence is at span token 0. There is one FP32 log-softmax value per token. The top five and both competing logits are recorded.
  - Upstream history changes at 019 are reported separately.
- **Statistic.** D = ℓ(native ID) − ℓ(Carbon ID), summed in nats with no length normalization. A non-finite or masked value gets a status and is never used for selection.
  - The path effect is D_c(pN) − D_native(pN) on the frozen native history.
  - The 037 history-shift effect is D_c(p_free) − D_c(pN). The coordinate cascade cannot be attributed exclusively from this effect.
- **Endpoint parity.** The genuine native and carbon_bf16 endpoints must reproduce the complete frozen arrays. Harness endpoints must report any aliasing. A mismatch gives `ENDPOINT_PARITY_FAILED`, and attribution is withheld until a harness fix has a new source binding.
- **Matrix checks.** All 14 configurations, using rules.py ids and bits. Free timing must be uninstrumented. Implementation counters are recorded, and a requested kernel that falls back is treated as an implementation path.
  - S1c covers routed, shared and layer-0 dense projections; this is the engine's contract, and I verify the counters it reports.
  - Configurations with S3 on and S0 off (`add_S3`, `remove_S0`) must carry a label for deferred ordered stream callbacks.
- **Sufficiency and necessity are reported separately.** Additions on native test sufficiency per site. Removals from full test necessity per site.
- **Selection: one-switch restoration decides.** If any single removal restores both anchored free IDs, the outcome is `SINGLE_REMOVAL_RESTORES_BOTH`. This holds even if the isolated addition did not cause both flips. The winner is chosen by fewest switches removed, then the smallest ordinary 019+037 seconds, then switch order. It is cross-checked with `rules.rank_restorations`.
  - The label `unique_cause_pattern` is true only when exactly one single removal restores, its addition flips both sites, and no other addition flips anything. Even then it applies only to these two windows. A cascade-only effect or backend coupling prevents calling it a unique kernel cause.
  - Pair screening is omitted in this case.
- **Pair screening (only if no single removal restores)**
  - A switch is eligible if its addition changes a uniquely anchored, actually emitted native ID into a different complete identifier.
  - Otherwise it is eligible only if, on the frozen native histories, the first-pass displacement d1 = D_add1 − D_native1 exceeds E_w, and the repeat d2 = D_add2 − D_native2 has the same sign with min(|d1|, |d2|) > E_w on some window. Here E_w = max(1e-5 nats, |D_native1 − D_native2|, |D_full1 − D_full2|).
  - **Re-probes happen only when needed.** If repeats are missing, the outcome is `PAIR_SCREENING_REPROBE_REQUIRED`. The request lists the endpoint native/full repeats plus only those additions that are not already flip-eligible and have |d1| > 1e-5 nats; any other addition cannot qualify. The re-probes use fresh prefill/cache state and the original inputs.
  - Eligible pairs are unordered pairs in switch order (at most 15), cross-checked with `rules.qualifying_pairs`.
  - Outcomes: `PAIR_RUNS_REQUIRED`, then `PAIR_REMOVAL_RESTORES_BOTH` (described as interaction-compatible, not a unique pairwise mechanism), `UNRESOLVED_NO_ELIGIBLE_PAIR`, or `UNRESOLVED_NO_RESTORATION`. If the predeclared comparison is incomplete, the result is unresolved and no surgical arm is selected.
- **Speed is reported separately for free and probed runs.**
  - Ordinary uninstrumented free seconds are given per window and summed, along with output tokens and forwards. Addition saving T_native − T_add and removal cost T_remove − T_full are local marginal effects. They are not additive and do not forecast 60 pages.
  - Instrumented probe prefill ms and decode ms per token are listed separately, with their interval and denominator.
- **Freezing the candidate.** Root freezes at most one `carbon_surgical`, with its bit vector, engine SHA and all decision inputs, before any A2 output exists. I do not freeze it.

## A2 (dev/id_ablation, 18 pages), `a2_stoploss.py`

- **Runs.** Six fresh single-arm processes: AB = native, carbon_bf16, carbon_surgical; BA = carbon_surgical, carbon_bf16, native. These exact orders are enforced.
  - Each arm/order produces one complete 18-page document with 6 stopped windows (36 scored windows in total).
  - Excluded warm-ups are identical across arms and orders. The dev source and RGB are identical across all six arm requests (PDF `56033270…`, rasters `404712df…`).
  - The clock is durable `timing.json` `elapsed_s`, measured from acceptance to durable publication.
- **Views.** Frozen, and title (WP-0016 `title_adapt.py` in its own process, after blob verification). Every score comes from the separate-process `score.py`. Changed persistent errors are reported separately.
- **ADVANCE only if all of the following hold:**
  - complete, uniquely linked pairs, with zero newly unflagged criticals in all four native→surgical views/orders;
  - in both orders, F_o = T_native − T_full > 0 and S_o ≥ 0.60 F_o;
  - min_o S_o > max(|ΔT_native|, |ΔT_surgical|), compared strictly so that a tie rejects.

  The full-arm spread is reported separately. The result is cross-checked with `rules.a2`. Anything else gives `HALT_AT_A2`.
- **Current state.** The A2 source is staged. Its scoring keys have not been released.

## A3 (H and A only, as specified in the PDF)

- **Tools.** The A3 verifier and scorer are derived mechanically by `a3/derive.py` from the WP-0016 G0 tools at `1e75ebe`, using only the enumerated substitutions. They are committed before any A3 run exists.
- **Structure.** Native→surgical then surgical→native, isolated processes, 6 excluded and 44 scored windows per order.
- **Requirements**, on every H/A × frozen/title × AB/BA combination:
  - completeness, stops and source links;
  - 0 new wrong-source links;
  - ΔCER ≤ +0.01 and Δcell ≥ −0.02;
  - 0 newly unflagged criticals;
  - emitted flags unchanged.
- **`a3_gate.py`** adds three checks:
  - board peak ≤ 10,000 MiB from the coordinator sampler;
  - static-cache growth == 0 when S2 is on in the frozen candidate, or a dynamic-only label when S2 is off;
  - a positive A saving in both orders, with the smaller saving strictly greater than both the native and surgical spreads.
- **Scorecard.** `scorecard.py` reports the non-gate items: net repairs, repairs/sec against Windows (15.6546455 s), malformed headers, and offline simulated margin flags with coverage and missingness.
