# WP-0015 independent H replay: Carbon `carbon_bf16` vs ordinary native (eld-rd-reviewer)

This is a working evidence summary, not canonical report 006. The full record is [evidence/scored-H-carbon.json](evidence/scored-H-carbon.json), produced by [verify_carbon.py](verify_carbon.py), plus [token_diff.py](token_diff.py). All inputs are synthetic.

**Scope:** the four-page held-out H only. There is no A, B or 60-page Carbon measurement, and no customer, search or unattended claim.

## Execution

| Item | Value |
| --- | --- |
| Source | Detached clean reviewer worktree `speed-review-carbon` at `7e70391cd790a95c68906902dbd9d5bc479aa9c0`. Its Astra `trial.py` has no UTF-8 console change, so a non-cp1252 output would reproduce the A crash. |
| Launcher | Coordinator's bound `launch-bound-carbon-pair.py`. It ran only the published per-order releases `h-carbon-ab` (native first) and then `h-carbon-ba` (`carbon_bf16` first). |
| Plans and budget | Plan SHA-256 `5a627aee…a764` / `50244b39…6862`, 600 s each |
| Process outcome | Each run completed all segments with exit 0 and no guard stop: 189.1 s and 190.2 s |
| Process cleanup | Every supervisor, venv launcher and trial child was absent afterwards |
| Isolation | Each mode ran in its own fresh child process with an excluded public warm-up: 6 native-model windows per order |
| GPU | Peak 9,201 MiB used, minimum 6,797 MiB free, maximum 57.6 °C |
| Inputs | H PDF, truth and rasters match their commitments, and the request pins equal the released rasters |
| Verifier | **0 failures** across durable files, RGB pins, page/window coverage, `<PAGE>` starts, token and raw reassembly, stop/page state and clock order |

`carbon_bf16` combines four changes: packed BF16 MoE, static-KV gather-sparse decode, GPU logit guards with 8-step bursts, and no text streamer. The load records show `use_packed_moe`, `use_gather_decode` and `use_gpu_burst` all true, with burst stride 8. Prefill used `_grouped_mm` with 0 fallback layer calls and 0 static-cache reallocations. Each window ran 4–5 extra burst forwards past EOS, which were truncated.

## Timing: accepted input to durable final `prediction.json` (four pages)

| Run | Arm | Load s | Warm-up s | First page s | Last page s | Complete s | Pages/min |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `h-carbon-ab` | native | 21.323 | 24.035 | 41.426 | 51.210 | **51.214** | 4.69 |
| `h-carbon-ab` | carbon_bf16 | 21.045 | 23.521 | 35.911 | 44.562 | **44.566** | 5.39 |
| `h-carbon-ba` | carbon_bf16 | 22.090 | 23.731 | 36.214 | 45.390 | **45.393** | 5.29 |
| `h-carbon-ba` | native | 20.683 | 23.852 | 41.282 | 50.978 | **50.982** | 4.71 |
| earlier `h-r1-ab` / `h-r2-ba` | Windows | — | — | 0.259 / 0.253 | — | 1.023 / 1.053 | 234.6 / 227.9 |

**Savings and noise:**
- Carbon saves **6.648 s and 5.589 s**, a speedup of 1.149× and 1.123×.
- The native spread within this pair is 0.232 s. Across all four ordinary native H runs (51.916, 55.262, 51.214, 50.982 s) it is 4.280 s.
- Both savings exceed both spreads.
- Carbon's own spread is 0.827 s.

**Per window, Carbon versus native:**
| Window | Tokens | Engine time, Carbon vs native | Time to first token, Carbon vs native |
| --- | ---: | --- | --- |
| Pages 1–3 | 405 | 35.69–35.96 s vs 41.05–41.19 s | 0.36–0.42 s vs 0.46–0.49 s |
| Page 4 | 92 | 8.56–9.08 s vs 9.60–9.69 s | — |

## Exactness

| Comparison | Token result |
| --- | --- |
| Native AB vs BA, and both vs the original H native | identical, 497 tokens |
| carbon_bf16 AB vs BA | identical, 497 tokens |
| carbon_bf16 vs native, both orders | **not identical**: first mismatch at token 10 |

The divergence from native is limited to geometry:
- 12 of 497 positions differ, with equal lengths per page (97, 213, 95, 92).
- Every difference is a box coordinate changed by **±1** model unit: 12 coordinates in 9 of 17 boxes.
- Raw text outside the boxes is identical on all four pages, and every stop and page count is identical.

**Classification:** Carbon fails Exact mode and is judged under Changed-output mode.

## Quality (frozen `score.py`, separate process; public title-level rule from commit `0186467`)

| Arm, both orders | Edits / 570 frozen → corrected | Cells | Lines frozen → corrected | Unflagged critical |
| --- | --- | --- | --- | --- |
| native | 178 → 2 | 18 / (20 + 0) | 12 → 16 / 16 | 2 / 19 |
| carbon_bf16 | 178 → 2 | 18 / (20 + 0) | 12 → 16 / 16 | 2 / 19 |
| Windows (earlier) | 15 | 15 / (20 + 0) | 13 / 16 | 8 / 19 |

**Carbon against same-run native:**
- ΔCER 0.0000 and Δcells 0.000, under both the frozen and the corrected parser, in both orders.
- Critical values: 0 new, 0 changed; the 2 existing errors are the same.
- Inside the budget, with no new wrong-source link.

**Both arms, closure and source:**
- complete and in order;
- no missing, duplicate or blank-page faults;
- no wrong-source links and no flags.

**Supplemental checks (corrected parser):** 2 surplus and 2 missing numerals on one page, nothing printed on another page, and no page that better matches another page's truth.

## H decision across the three arms

| Arm | Complete | Inside budget vs matched native | Exact | Pages/min (best order) | Unattended |
| --- | --- | --- | --- | ---: | --- |
| Windows OCR | yes | **no**: cells −0.150, corrected CER +0.0228 | n/a | 234.6 | no |
| carbon_bf16 | yes | **yes**: Δ 0 / 0 | no (±1 coordinates) | 5.39 | no (2 existing unflagged critical) |
| native | yes | control | — | 4.71 | no |

- **Fastest complete:** Windows.
- **Fastest complete inside the budget on H:** `carbon_bf16`, about 1.13–1.15× native. Both orders exceed the native control spread.
- **What this doesn't establish:**
  - It is a single four-page family.
  - It is not a full-A result. A's only complete native and Windows measurements are in [scored-summary.md](scored-summary.md), and Carbon has none on A.
  - It is far from the 30 pages/min customer floor.
- **Unattended use:** no arm qualifies.
