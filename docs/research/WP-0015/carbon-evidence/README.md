# WP-0015 Early Public Screen Archive: `carbon-moe-01`

Bounded, reproducible CPU-verifiable evidence archive for coordinator-executed run `carbon-moe-01` on frozen candidate `7e70391cd790a95c68906902dbd9d5bc479aa9c0` (`smoke-moe-dense.json`, SHA-256 `54ef3ccfcf9a7b28172dbac3f5c3502d6b6b995f5467b006b2a556ff33ca39e9`), authored by `eld-rd-carbon` (**Gemini 4 Carbon**, High effort).

Stored outside the five `launch.py` `SCOPES` so frozen candidate `7e70391cd790a95c68906902dbd9d5bc479aa9c0` remains admissible for subsequent `ab-dev` / `ba-dev` compound runs. Contains **42 JSON/UTF-8 receipt files (`83,957` bytes total)** — zero runtime caches, PDFs, or model weights — using public `dev` keys only.

## 1. Reproducible CPU Verification Command (Zero `torch` / CUDA)

```powershell
$env:CUDA_VISIBLE_DEVICES=""
& "C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe" -I -B `
  "C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/speed-carbon/docs/research/WP-0015/carbon-evidence/verify_carbon_moe_01.py"
```

Verifies every archived receipt in `carbon-moe-01/` against `manifest.json`, cross-checks profiler token IDs against WP-0014 ordinary `Native` `A.pdf` receipts, re-scores `dev/dense` with `docs/evaluation/WP-0015/score.py`, and regenerates `analysis-summary.json`.

---

## 2. Cold Loads, Process Isolation & GPU Telemetry

| Metric | Segment 1: `native_profile` | Segment 2: `carbon_moe` (`["packed_bf16_moe", "no_text_streamer"]`) |
| --- | ---: | ---: |
| Isolated child PID / exit code | `6928` / `0` | `22264` / `0` |
| Segment wall time (`segment-process.json`) | `94.744 s` | `83.820 s` |
| Cold load wall (`load-*.json`) | `22.432 s` (`11,402 ms` `load_model`) | `22.089 s` (`11,405 ms` base + `555 ms` pack = `11,960 ms`) |
| Weight allocated after in-place MoE pack | — | `6,702,833,664 B` (`6.243 GiB`) |
| Peak CUDA allocated (`dense` window) | `7,293,326,848 B` (`6.792 GiB`) | `7,210,620,416 B` (`6.715 GiB`, **`-78.9 MiB`**) |
| Peak CUDA reserved (`dense` window) | `7,480,541,184 B` (`6.967 GiB`) | `7,451,181,056 B` (`6.940 GiB`, **`-28.0 MiB`**) |
| `torch._grouped_mm` prefill layer calls / fallbacks | — | `22` cumulative (`11` warm + `11` dense) / **`0` fallbacks** |
| Sampled `nvidia-smi` GPU utilization / temp | `1%–15%` / `44.05–50.64 °C` | `1%–18%` / `47.07–53.10 °C` |

---

## 3. Timings, First Decode Stage Profile & Causal Decomposition

### Per-Request Timings

| Packet (`1` page, `279` prompt / `273` visual tokens) | `native_profile` elapsed (`prefill` / `post-first`) | Ordinary `native` dev reference | `carbon_moe` elapsed (`prefill` / `post-first`) | Output tokens (`forwards`) |
| --- | --- | --- | --- | --- |
| `warm` (`WP-0014/A.pdf`, warmup) | `26.002 s` (`18.735 s` / `7.073 s`) | — | `24.406 s` (`18.508 s` / `5.700 s`) | `57` (`58`) |
| `dense` (`dev/dense/source.pdf`, scored) | `44.737 s` (`0.395 s` / `44.136 s` = `121.59 ms/step`) | `~41.0 s` (`~111.4 ms/step`) | **`35.832 s`** (`0.310 s` / `35.325 s` = `97.31 ms/step`) | `363` (`364`) |

- **Pages/min on `dev/dense`:** `1.674 pages/min` (`carbon_moe`) vs `1.341 pages/min` (`native_profile`) and `~1.46 pages/min` (ordinary `native`).
- **Speedup accounting:** Raw `44.737 s -> 35.832 s` (`-8.905 s`, `1.249×`) includes **`~3.74 s` (`~10.3 ms/step`) of non-causal `ProfiledNative` instrumentation overhead** (`124` `cudaEventRecord` calls + `98` Python wrapper/clock hooks per token) plus **`~5.17 s` (`~1.14×` vs ordinary `~41 s` `native`) of true causal `carbon_moe` savings** (`85.8 ms` prefill via `torch._grouped_mm` + `~14.0 ms/step` decode).

### First Stage Profile on `dev/dense` (`363` steps; `256` CUDA-event sampled steps, `121.588 ms/step` wall)

| Subsystem Bracket | Mean GPU CUDA-Event (`ms/step`) | Mean Host Span (`ms/step`) | Share of Profiled Step Wall | Causal Status |
| --- | ---: | ---: | ---: | --- |
| `attn_router` (`_dash_decode_forward`, 12 layers) | **`85.049 ms`** | **`83.936 ms`** | **`69.03%` host / `69.95%` GPU** | **Untouched in `carbon_moe`; true primary bottleneck.** Zero `.cpu()` syncs inside `_dash_decode_forward`, yet host dispatch equals `98.7%` of GPU event span at `11–18%` GPU util: caused by `~180–200` tiny eager Python/ATen/WDDM kernel launches/layer (`~2,200` ops/token across 2D page RoPE, `_RMSNorm`, `head_cls` block summaries, `1.5-entmax` top-M sort/cumsum, and `_decode_attend`). |
| `moe_gate_and_sort` (11 MoE layers) | `6.169 ms` | `5.694 ms` | `4.68%` | Eager gate/routing launch overhead (`gate` + `scatter_` + `argsort` in baseline; reduced to `gate + index_select` in `carbon_moe`). |
| `moe_cpu_numpy_call` (11× `.cpu().numpy()`) | — | **`1.126 ms`** | **`0.93%`** | Coupled WDDM D2H sync + completion of preceding async `MoEGate`/`argsort` ops (`0.102 ms/layer`). **Falsifies Turn 1's claim that `.cpu().numpy()` alone caused `>97%` of decode latency.** |
| `moe_python_expert_loop` (11× 64-expert loop) | `19.753 ms` *(incl. shared/combine)* | **`14.342 ms`** | **`11.80%`** | **Primary source of `carbon_moe`'s `~14.0 ms/step` causal decode gain:** collapsed 198 per-token Python expert GEMV launches into 22 batched `torch.bmm` launches. |
| `moe_shared_and_combine` (11 MoE layers) | *(in `19.753 ms` above)* | `5.528 ms` | `4.55%` | Partially reduced by fused `sh_gate_up` and direct weighted `bmm` reduction. |
| `mlp0_dense` (Layer 0 MLP) | `0.276 ms` | `0.227 ms` | `0.19%` | Minor (`gate_up` fused in `carbon_moe`). |
| `lm_head` + CPU `ngram`/`page` guards | `0.842 ms` (GPU) | `0.124 ms` | `0.10%` host | Negligible at `363` tokens (`0.062 ms/step` 35-gram + `0.003 ms/step` page guard). |
| `streamer_put_post_sync` (`TextStreamer.put`) | — (GPU idle) | **`0.144 ms`** | **`0.12%`** | **Strictly causal post-`argmax` GPU-idle stall, but tiny (`52.30 ms` total over `363` steps)** when stdout is redirected to `stdout.txt`. |

- **60% Stage-Share Falsifier Nuance:** Compound targeted subsystems (`attn_router + moe + guards + streamer`) span `91.16%` (`110.83 / 121.59 ms/step`), passing the compound `>=60%` gate, **but `moe + streamer` alone accounted for only `22.07%` (`26.83 ms/step`)**, capping any MoE-only ablation below `1.3×` while `attn_router`'s ~2,200 eager Python ops/token remain ungraphed/uncompiled.

---

## 4. Independent Profiler Token-ID Verification & Output Fidelity / Quality

1. **Profiler Token-ID Verification vs Ordinary `Native`:**
   - **`warm` (`WP-0014/A.pdf`):** `01-warm-native_profile` (`57` tokens) matched WP-0014's uninstrumented cold-process `resident/1-A/native.json` and `raw_output.utf8.bin` **100% token-for-token and byte-for-byte**. Notably, `01-warm-carbon_moe` (`57` tokens) differed at 1 token (`#7`: `6650 '103' -> 7163 '104'`), matching WP-0014's documented uninstrumented `resident/3-A` and `5-A` runs (`[73, 104, 770, 203]`).
   - **`dev/dense`:** No ordinary uninstrumented `native` `dev/dense` artifact is in this worktree yet; `ProfiledNative` wraps unmodified upstream forward functions without altering tensor values, and direct `dev/dense` token-ID verification against ordinary `native` will complete once public `ab-dev` / `ba-dev` runs are delivered.
2. **Exact-BF16 Disqualification & Token-Class / Error Equivalence (`dev/dense`):**
   - **Not an Exact-BF16 parity win (`exact_bf16_qualified = false`, `lost_exactness = true`):** `carbon_moe` and `native_profile` both stopped cleanly (`finish_reason = "stop"`, `1/1` page, `363` tokens, identical token classes `{page: 1, block_geometry: 108, table_syntax: 98, content: 156}`), but differed at **6 of 363 token positions** (`#7`: `'57'->'59'`, `#27`: `'60'->'62'`, `#47`: `'60'->'61'`, `#53`: `'426'->'425'`, `#72`: `'60'->'61'`, `#321`: `'858'->'857'`).
   - **100% of token differences are `±1..2` `/1000` horizontal bounding-box coordinates (`0.61–1.22 pt`):** Caused by BF16 non-associativity in `torch._grouped_mm` prefill and `bmm` / fused `gate_up` decode. Stripping all `<BLOCK>type(<LEVEL1>)?[x1,y1,x2,y2]<FORK>` coordinates yields **100% identical prose and HTML table strings** (`evaluate.py`'s `BOX_RE` missed `<LEVEL1>` on line 1).
   - **Identical `score.py` quality & error profile:** Both modes scored `CER = 0.096774` (`48/496` edits, `delta = 0.0`), `cell_accuracy = 0.928571` (`39/42` cells, `delta = 0.0`), `4/6` lines, `0` wrong-source links, and the **exact same 3 missed cells and 4 unflagged critical confusable-glyph (`I/1`, `O/0`) errors** (`WO-O1I8 -> WO-O118`, `10-7O1 -> I0-701`, `PX-I10 -> PX-110`, `L1I -> L11`). Thus `carbon_moe` satisfies Changed-Output relative parity (`inside_quality_budget = true`), while both baseline and challenger fail `unattended_quality_gate` on unflagged confusable IDs.
