# WP-0017 / 003: Independent A1 escrow review and publication cross-check, closed at A1 with no restoring removal

- Report path: `docs/agent-reports/eld-rd-reviewer/WP-0017/003_2026-11-18_review_eld-rd-reviewer.md`
- Sequence reservation: INDEX.md on `coordination/bootstrap` at `9cfe4b9`, WP-0017 table row 003, eld-rd-reviewer
- Category: review
- Author / agent ID: eld-rd-reviewer
- Actual model / effort: `claude-opus-5-5`; requested effort xhigh (the exposed dispatch setting)
- Execution environment: native Claude Code CLI, session `e2d32880-3555-4a4d-b695-b7963a903c2c`; Q0 Python 3.12.10 (`-I -B`), `tokenizers` 0.21.4; CPU only for this report
- Published by: author (push to `review/wp-0017-escrow`)
- Timestamp: 2026-11-18T23:57:00Z
- Repository / branch: `jackgumpe/eledgercare`, `review/wp-0017-escrow`, worktree `eledgercare-worktrees/ablation-review`
- Base revision: `e479b8c8a39bf5703ee084d89527dbe3b872bf8f`, the combined decision my worktree was fast-forwarded to
- Deliverable revision: `f6645cfa05d98e3f2608e6571f1a7473c65f656e` (cross-check tool `a6e2321e…` plus its evidence)
- Previous report: none by this agent in WP-0017
- Related or reviewed reports: WP-0017/001 eld-rd-astra (design `1fad21c`, report `ba6db76`); WP-0017/002 eld-rd-carbon (engine `c235bc61`, report `cdb58f0`); coordinator disposition `b95e329f54ecbb389c2db65a7dbe7d825874a234`
- Status: accepted. This is an independent concurrence: WP-0017 closes at A1, `UNRESOLVED_NO_RESTORATION`, with no surgical mask.
- Next owner: eld-coordinator (report 004, INDEX/CURRENT)

## Summary

I independently re-derived the terminal A1 outcome from the immutable captures and concur with it: **no removal of one or two switches restored both anchored free identifiers**, so no `carbon_surgical` mask exists and A2/A3 were correctly never released. There were 19 configurations: 16 in the initial wave and 3 eligible pair removals.

- **Page 37 (window 037)** was restored by `remove_S2` and by all three pairs.
- **Page 21 (window 019)** was restored by no single or pair removal.

What I verified:
- All 1,379 inventoried files are unchanged against all three published blind inventories.
- My frozen normalizer and decision rerun the initial wave byte-identically to the coordinator's mirror, apart from timestamps.
- Re-deciding all 19 configurations gives 0 field, second or D mismatches with the pair reviewer's combined decision `e479b8c`.
- Its rule agrees with Astra's pinned `rules.py`.

This is independent review, not author verification. I authored no WP-0017 design, fixture, engine, pair runner or coordinator tool.

## Authorship and custody (preserved)

| Role | Identity | Contributions in this lane |
| --- | --- | --- |
| eld-rd-reviewer, initial | Antigravity CLI, Claude Opus 5.5 High, session `5ab6a228-4214-49e5-aa83-c00fe9315782` | Frozen A1 prefix audit tool `61c2734` and evidence `1b519d8` (180 checks, 0 failures). Frozen CPU escrow tools `9a1fbb9`, `64583bf`, `b74c588`, `90747b3`. Ran out of provider credits after `90747b3`. |
| eld-rd-reviewer, continuation (this author) | native Claude Code, `claude-opus-5-5` xhigh, session `e2d32880-…` | Pushed `90747b3` unchanged. Receipts `d29a3b5`. 16-wave binding, normalizer, A2 adapter and release review `3ee83ab` / `9ec255c`. Re-bind to `c235bc61` at `8fe0ece` after a preserved refused attempt `2d61067`. **Issued `a1-r1` at `62f4ce4`, commanding the 16 initial configurations.** This report: `a6e2321`, `f6645cf`. |
| eld-rd-reviewer, pair operator | fresh Codex `gpt-6.2-astra` xhigh, session `/root/wp17_pair_reviewer`, thread `01a1f0ec-5fe5-7480-a809-6fda624e72e0`; authorized by Jack only for the three pair tests | Rechecked the 16. Issued `a1-p1` at `188e681` (86 reviewer checks). `pair_combined.py` `03762a1`. Combined inventory `e6738a7`. Combined decision `e479b8c`. |
| eld-coordinator | continuous Codex | Releases `a1-r1` (`3e9780f`) and `a1-p1` (`270306c`). Passive OS carrier. Evidence mirror `e9c4532`, `f9190a1`, `2530e44`, `14bfa12`, `a2b4f74`. Disposition `b95e329`. |
| eld-rd-astra / eld-rd-carbon | design / engine authors | Design `1fad21c`; engine `c235bc61` (Astra peer-fix patch applied by Carbon in `cd277b5`). |

## Objective and acceptance criteria

The scope is the assignment at `0d50f40` and design `1fad21c` (A1 section).
- All four endpoints must replay their frozen WP-0016 arrays.
- Eight endpoint windows and 14 unique bit vectors plus 2 endpoint controls are compared on anchored free identifiers.
- A single removal that restores both fields decides.
- Otherwise the predeclared eligible pairs are run. A restoring pair is selected by fewest removed, then fastest ordinary seconds, then switch order.
- An incomplete or failing comparison ends unresolved without a surgical arm.

Thresholds are frozen. Nothing was tuned, and no key was opened.

## Results

### Run custody

| Lease | Release | Command (operator) | Carrier exit | Orders: wall, exit, guard, executor-sampled board peak |
| --- | --- | --- | --- | --- |
| `a1-r1` | `c7fe5ad7…` (integration `3e9780f`) | `62f4ce4` (this author), file `15c6d301…` | 0 | endpoints 1,044.4 s, 0, none, 9,304 MiB; switches 3,103.3 s, 0, none, 9,394 MiB |
| `a1-p1` | `02eef093…` (`270306c`) | `188e681` (Codex pair reviewer) | 0 | pairs 754.5 s, 0, none, **13,053 MiB** |

- Both commands equal their signed releases on every field the carrier checks.
- Both leases returned with `error: null`. Total supervised time was 4,902.2 s, with no guard interruption.
- The highest board use, 13,053 MiB, was seen only by the executor's device log during the pair order (362 samples). The launcher's own 5-second samples peaked at 9,718 MiB for that order. Both are below the 14,500 MiB A1 diagnostic guard.

### Endpoints and noise

- All 8 endpoint windows replay their complete frozen arrays: `native` and `all_off` match native 501/396 tokens, and `carbon_bf16` and `all_on` match Carbon 501/391. My independent parity agrees with the coordinator's `endpoint-check.json`.
- Forced-probe repeats are bit-identical. The harness-versus-genuine probe gap is 0.0 nats on every endpoint and window, so E_w = 1e-5 nats on both windows.
- The conservative sensitivity floor changes nothing.

### Both sites per configuration

- **Anchored emitted IDs.** Native is `I08O1-388` on page 21 and `8OI10-774` on page 37; Carbon is `108O1-388` and `80I10-774`. Every field read was structurally `ok`.
- **D.** D = ℓ(native ID) − ℓ(Carbon ID) over the common-boundary span, in guarded FP32 nats.
  - "D 019/037" is measured on the frozen native history; repeated passes were identical.
  - "D 037 own" is measured on the configuration's own free history.
- **m.** The guarded top-1 minus top-2 margin at the first divergent identifier token.
- **t7.** The free token at window 037 index 7: 17979 `291` (native) or 16234 `290` (Carbon).
- **Seconds** are ordinary free engine.read seconds, one fresh process per mode, with no repeat.

| Config | Bits | Page 21 | Page 37 | D 019 | D 037 | D 037 own | m 019 / 037 | t7 | s 019 / 037 / sum |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 000000 | I08O1 | 8OI10 | +0.055984 | +0.069615 | +0.069615 | 0.125 / 0.125 | 291 | 55.764 / 43.570 / 99.334 |
| all_off | 000000 | I08O1 | 8OI10 | +0.055984 | +0.069615 | +0.069615 | 0.125 / 0.125 | 291 | 54.710 / 43.435 / 98.145 |
| carbon_bf16 | 111111 | 108O1 | 80I10 | −0.068936 | −0.055425 | −0.186242 | 0 / 0 | 290 | 47.694 / 37.304 / 84.998 |
| all_on | 111111 | 108O1 | 80I10 | −0.068936 | −0.055425 | −0.186242 | 0 / 0 | 290 | 49.349 / 37.855 / 87.205 |
| add_S0 | 100000 | I08O1 | 8OI10 | +0.055984 | +0.069615 | +0.069615 | 0.125 / 0.125 | 291 | 54.855 / 43.299 / 98.154 |
| add_S1a | 010000 | I08O1 | 8OI10 | +0.055984 | +0.069615 | +0.069615 | 0.125 / 0.125 | 291 | 63.882 / 48.673 / 112.555 |
| add_S1b | 001000 | **108O1** | 8OI10 | −0.047005 | +0.062851 | +0.062851 | 0 / 0.125 | 291 | 47.628 / 38.079 / 85.707 |
| add_S1c | 000100 | **108O1** | 8OI10 | −0.047353 | −0.063018 | −0.063018 | 0 / 0 | 291 | 56.994 / 44.493 / 101.487 |
| add_S2 | 000010 | **108O1** | 8OI10 | −0.068594 | +0.069669 | +0.069669 | 0 / 0.125 | 291 | 56.052 / 44.361 / 100.413 |
| add_S3 | 000001 | I08O1 | 8OI10 | +0.055984 | +0.069615 | +0.069615 | 0.125 / 0.125 | 291 | 55.701 / 44.278 / 99.980 |
| remove_S0 | 011111 | 108O1 | 80I10 | −0.068936 | −0.055425 | −0.186242 | 0 / 0 | 290 | 48.827 / 38.060 / 86.887 |
| remove_S1a | 101111 | 108O1 | 80I10 | −0.068936 | −0.055425 | −0.186242 | 0 / 0 | 290 | 48.562 / 37.919 / 86.481 |
| remove_S1b | 110111 | 108O1 | 80I10 | −0.047133 | −0.069261 | −0.185975 | 0 / 0 | 290 | 55.958 / 44.661 / 100.619 |
| remove_S1c | 111011 | 108O1 | 80I10 | −0.083124 | −0.061867 | −0.310724 | 0 / 0 | 290 | 49.072 / 39.916 / 88.988 |
| remove_S2 | 111101 | 108O1 | **8OI10** | −0.045764 | −0.061819 | −0.061819 | 0 / 0 | 291 | 47.948 / 38.032 / 85.979 |
| remove_S3 | 111110 | 108O1 | 80I10 | −0.068936 | −0.055425 | −0.186242 | 0 / 0 | 290 | 47.867 / 38.228 / 86.096 |
| remove_S1b+S1c | 110011 | 108O1 | **8OI10** | −0.068594 | +0.069669 | +0.069669 | 0 / 0.125 | 291 | 58.588 / 46.075 / 104.663 |
| remove_S1b+S2 | 110101 | 108O1 | **8OI10** | −0.047353 | −0.063018 | −0.063018 | 0 / 0 | 291 | 55.408 / 43.629 / 99.037 |
| remove_S1c+S2 | 111001 | 108O1 | **8OI10** | −0.047005 | +0.062851 | +0.062851 | 0 / 0.125 | 291 | 48.537 / 39.397 / 87.934 |

Identifiers are abbreviated to their first five characters; the suffixes are `-388` and `-774`.
- **037 at t=7.** On the frozen native history, the guarded t=7 step gives `291` over `290` by 0.25 logits in every configuration whose page-37 ID is native. In every configuration whose ID is Carbon, the two tie (margin 0.0) and the engine's guarded argmax takes `290`.
- **Pair D values.** Each pair's D values equal those of the single addition with the same active subset of {S1b, S1c, S2}. S0, S1a and S3 leave the forced-span arithmetic unchanged, to within the 1e-5 floor.

### Necessity, sufficiency and interaction, per site

These statements are confined to these two windows and the tested backgrounds.
- **Page 21 (window 019).**
  - Sufficiency on the native background: adding any one of S1b, S1c or S2 moves the emitted ID to the Carbon value. S0, S1a and S3 do not.
  - Necessity in the full background: none. No single or pair removal restores it, because every tested removal leaves at least one of S1b, S1c and S2 active.
  - So the page-21 flip is redundant across three switches. Restoring it would need all three removed, which is outside the predeclared ≤2-removal design and was not run.
- **Page 37 (window 037).**
  - No single addition flips it, so there is no single-switch sufficiency.
  - Removing S2 from the full background restores it, so S2 is necessary there. All three pairs also restore it, including `remove_S1b+S1c`, which keeps S2 on.
  - On the tested configurations, the Carbon page-37 ID appears exactly when S2 is on together with S1b or S1c, with S0/S1a/S3 on. That is an interaction, not a single cause.
  - It is mediated by the early t=7 coordinate (`290` versus `291`), which shifts the history before the identifier. The own-history D falls to −0.186 / −0.311 nats when that happens. This is a history-shift cascade, which the design says cannot be attributed to one kernel.
- **Mechanism (descriptive, not causal).**
  - In the native arms, every decisive margin is exactly one BF16 ulp at its logit scale: 0.125 at about 19–22 and 0.25 at about 34.
  - In the Carbon-like arms those margins become exact ties. Ties go to the lower token id: 223 `' '` at page 21 and 16234 `290` at t=7. At page 37's first divergence a tie goes to 26 `'8'`, the native path.
  - The full-span D sign therefore need not agree with the emitted ID, as `add_S1c` on page 37 shows.

### Conditional speed (ordinary free engine.read, two-window sum; instrumented time separate)

| Switch | Native − add (vs `all_off`) | vs genuine `native` | Remove − full (vs `all_on`) | vs genuine `carbon_bf16` |
| --- | --- | --- | --- | --- |
| S0 | −0.009 s | +1.180 s | −0.318 s | +1.889 s |
| S1a | −14.410 s | −13.221 s | −0.724 s | +1.482 s |
| S1b | **+12.438 s** | +13.627 s | **+13.414 s** | +15.620 s |
| S1c | −3.342 s | −2.153 s | +1.784 s | +3.990 s |
| S2 | −2.269 s | −1.079 s | −1.225 s | +0.981 s |
| S3 | −1.835 s | −0.645 s | −1.109 s | +1.098 s |

- **Pair removal cost versus `all_on`:** S1b+S1c +17.458 s; S1b+S2 +11.832 s; S1c+S2 +0.729 s.
- **Endpoint residuals:**
  - `all_off − native`: −1.055 s on 019, −0.135 s on 037, −1.189 s in sum.
  - `all_on − carbon_bf16`: +1.655 s, +0.551 s, +2.206 s.
- **Endpoint gaps:** genuine native − Carbon is 14.336 s; harness `all_off − all_on` is 10.940 s.
- **How far to read these:** they are single observations per mode and local marginal effects, not additive and not a 60-page forecast. Only S1b (and S1a when added alone, which is slower) exceeds the roughly ±2 s endpoint residuals.
- **Instrumented probe time (separate):** per-configuration medians are 352–457 ms prefill and 93–112 ms per forwarded decode token.

### Findings from the cross-check

1. **Tie labelling defect in my frozen `a1_decide.greedy()` (reporting only).** It labels the top-five-first token, but under exact ties `torch.topk` order is not the engine's guarded argmax.
   - Of 84 probe passes, 42 are tied at the divergence step, and in 16 the top-five-first token differs from the argmax. This equals the pair reviewer's and coordinator's counts.
   - Selection never uses this label; restoration and eligibility use anchored emitted IDs. The engine's guarded argmax equals the token the free run emitted on the same history in **66 of 66** comparable passes.
   - The `greedy` diagnostic in my frozen initial-wave decision (mirrored at `f9190a1`) is therefore wrong in those passes. Use the engine argmax recorded in `A1-003-crosscheck.json`.
2. **Adapter gap, not evidence: pair naming.** My frozen normalizer expects `remove_S1b+S1c`, but the engine names pairs `remove_S1b_S1c`.
   - Run as published on the pair tree, it records 18 identity failures (child, ordinary-timing, window and probe bit checks), all caused by that naming.
   - `crosscheck_003.py` corrects only that, in-process, and reverses the patch afterwards. Its adapter check count of 1,261 then equals the pair reviewer's.
3. **Probe guards.** Every S3-on probe recorded device guards and every S3-off probe host guards. This is the `c235bc61` peer-review fix, now confirmed in actual data.

## Change inventory

| Action | Exact path | What and why |
| --- | --- | --- |
| Added | `docs/reviews/WP-0017/crosscheck_003.py` (`a6e2321`) | Publication cross-check described above (CPU, stdlib, frozen tools imported unchanged) |
| Added | `docs/reviews/WP-0017/evidence/A1-003-crosscheck.json` (`f6645cf`, SHA-256 `5d48bccb…`) | 712 checks, 0 failures: per-configuration table, probe audit, speeds, peaks, receipts |
| Added | this report (separate commit after `f6645cf`) | Canonical 003 |

Not published: my uncommitted conditional A2/A3 binding edits to `command.py` and `common.py`.
- They are kept in stash commit `bcc4b085be6b5f2c64bca52443f410398db15aa1`, tagged `wp17-reviewer-e2d32880-uncommitted-a2a3-doc-binding-wip`.
- Copies are in `WP-0017/review/scratch-e2d32880/wip-a2a3-binding/` (`command.py` `3c7d0097…`, `common.py` `33c8c471…`, patch `9cbfab68…`).
- They are moot, because A2/A3 are not released.

## Verification

| Check / exact command | Revision | Result | Evidence |
| --- | --- | --- | --- |
| `escrow.verify_unchanged` over the combined (`e6738a7`, `6b1ee895…`), initial mirror (`e9c4532`, `2e3edc90…`) and pair (`14bfa12`, `a4039a47…`) inventories | tools `62f4ce4` (unchanged in `e479b8c`) | `[]` for all three; 6 runs, 1,379 files | this report |
| `python -I -B docs/reviews/WP-0017/a1_normalize.py --inventory <a1-r1-blind-inventory.json from bootstrap> --endpoints …/review/runs/a1-r1-endpoints --switches …/review/runs/a1-r1-switches --out <scratch>` | `e479b8c` | BOUND, 16 configurations, 0 failures; equal to mirror `a1-r1-normalized.json` except `created_utc` | scratch `9ef2c0dc…` |
| `python -I -B docs/reviews/WP-0017/a1_decide.py --audit docs/reviews/WP-0017/evidence/A1-prefix-audit.json --audit-sha256 16eca676… --inventory <same> --results <scratch> --out <scratch>` | `e479b8c` | `PAIR_RUNS_REQUIRED`, 0 failures; eligible {S1b,S1c}, {S1b,S2}, {S1c,S2}; Astra agrees; equal to mirror `a1-r1-machine-decision.json` except `created_utc`/`results_sha256` | scratch `1eea9aca…` |
| `python -I -B docs/reviews/WP-0017/crosscheck_003.py --audit … --audit-sha256 16eca676… --out docs/reviews/WP-0017/evidence/A1-003-crosscheck.json` | `a6e2321` | 712 checks, 0 failures; `UNRESOLVED_NO_RESTORATION`; 0 mismatches with `e479b8c`; probes 84/42/16; argmax = emission 66/66 | `f6645cf` |
| Coordinator `decision.json` (`b95e329`) | — | `CLOSED_AT_A1_UNRESOLVED_NO_RESTORATION`; `reviewer_decision_sha256` `8e99460e…` equals the `e479b8c` blob, which I recomputed | — |

Not run:
- No GPU or model of any kind, and no new inference.
- No dev, H, A or B key; Packet B stays sealed.
- No A2/A3 plan, binding completion or derivation.
- I did not re-execute the pair reviewer's `pair_combined.py`; my decision path is independent of it.

## Scientific limits

- The unit is two fixed three-page windows (019, 037) of one previously exposed packet (A). Nothing generalizes to other pages, fonts, documents or Packet B.
- Timing is one observation per mode. Initial and pair runs are separate releases about 2.5 h apart, with fresh processes per configuration. Emitted-ID comparability across releases rests on exact endpoint replay; second-level timing comparisons across releases may drift.
- Forced probes are deterministic, so the 1e-5 nat floor, not run-to-run noise, governed pair eligibility. All three eligible pairs qualified by anchored ID flips.
- The identifier differences come from one-ulp BF16 logit shifts at near-ties, resolved by lowest-token-id tie-breaking. They are not evidence of a semantic kernel error.
- The page-37 effect is a history cascade through an early coordinate token.
- The triple removal (S1b, S1c and S2) is untested and outside the predeclared surgical definition. Any such trial would need a separately authorized design.

## Risks, disagreements and unfinished work

- **No disagreement** with the pair reviewer's decision `e479b8c` or the coordinator's disposition `b95e329`.
- **F2 (carried over).** `device_lease.bind_inputs` binds HEAD and `*.py` digests only. Issue-time checks covered the non-`.py` engine files for both A1 commands.
- **For any future document release (not now).**
  - The A3 derivation would need one more enumerated substitution, because the WP-0017 `launch.py` segment `plan.json` adds `surgical_override`.
  - The coordinator's `prepare_doc_orders.py` working copy ends in one CRLF (disk `cb73c2d4…`, blob `008b4163…`), so any plan it writes would bind the raw disk digest. Restore LF bytes first.
- **The 13,053 MiB executor-observed peak during the pair order** exceeds the 10,000 MiB A3 ceiling and is not visible in the launcher samples. It does not bear on A1. If a later packet runs pair-like configurations under an A3 ceiling, it should establish the source of that transient.

## Handoff

- Next owner is eld-coordinator: report 004, and the INDEX/CURRENT update for 003.
- Branch `review/wp-0017-escrow`. Deliverable `f6645cfa05d98e3f2608e6571f1a7473c65f656e`. The report publication SHA is given in the handoff message.
- Publication receipt: remote confirmation for the report commit is given in the handoff message after the push. This report does not contain its own commit SHA.
