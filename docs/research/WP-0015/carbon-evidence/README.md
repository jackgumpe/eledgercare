# WP-0015 Carbon Public Evidence Archive (`carbon-moe-01`, `carbon-dense-ab`, `carbon-dense-ba`)

Bounded, reproducible CPU-verifiable archive of all three coordinator-executed public runs on frozen candidate `7e70391cd790a95c68906902dbd9d5bc479aa9c0`, authored by `eld-rd-carbon` (**Gemini 4 Carbon**, High effort).

Stored outside the five `launch.py` `SCOPES` so frozen candidate `7e70391cd790a95c68906902dbd9d5bc479aa9c0` remains untouched and admissible. Contains **126 JSON/UTF-8 receipt files (`232,882` bytes total)** across `carbon-moe-01/` (`42` files, `83,957` B), `carbon-dense-ab/` (`42` files, `74,276` B), and `carbon-dense-ba/` (`42` files, `74,649` B) — zero runtime caches, PDFs, or model weights — using public `dev` keys only.

## 1. Reproducible CPU Verification Commands (Zero `torch` / CUDA)

```powershell
$env:CUDA_VISIBLE_DEVICES=""
& "C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe" -I -B `
  "C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/speed-carbon/docs/research/WP-0015/carbon-evidence/verify_carbon_moe_01.py"
& "C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe" -I -B `
  "C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/speed-carbon/docs/research/WP-0015/carbon-evidence/verify_all_public_runs.py"
```

Verifies every archived receipt SHA-256 against `manifest.json` and `manifest-ab-ba.json`, confirms `ProfiledNative`'s 363 `dev/dense` token IDs and 57 `warm` token IDs equal ordinary `Native` in both `AB` and `BA`, recomputes paired crossover timings/noise and `score.py` quality outputs, and regenerates `analysis-summary.json` and `ab-ba-summary.json`.

---

## 2. Paired Crossover Comparison (`carbon-dense-ab` & `carbon-dense-ba`) + Ablation (`carbon-moe-01`)

| Run / Segment (`dev/dense`, 1 page, `363` tokens) | Mode | Cold Load (`load_ms`) | `warm` (`A.pdf`) | `dev/dense` Elapsed (`prefill` / `post-first`) | Pages / min | Forwards (`burst_extra`) | Peak CUDA Alloc |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| `carbon-moe-01` / seg 1 | `native_profile` | `22.432 s` (`11,402`) | `26.002 s` | `44.7370 s` (`0.395 s` / `44.136 s`) | `1.341` | `364` (`0`) | `7,293,326,848 B` |
| `carbon-moe-01` / seg 2 | `carbon_moe` | `22.089 s` (`11,960`) | `24.406 s` | `35.8320 s` (`0.310 s` / `35.325 s`) | `1.674` | `364` (`0`) | `7,210,620,416 B` |
| `carbon-dense-ab` / seg 1 | `native` | `20.942 s` (`10,840`) | `24.752 s` | **`36.5720 s`** (`0.338 s` / `36.051 s`) | `1.641` | `364` (`0`) | `7,293,326,848 B` |
| `carbon-dense-ab` / seg 2 | `carbon_bf16` | `21.270 s` (`11,152`) | `23.385 s` | **`31.8116 s`** (`0.311 s` / `31.326 s`) | `1.886` | `370` (`6`) | `7,210,620,416 B` |
| `carbon-dense-ba` / seg 1 | `carbon_bf16` | `21.613 s` (`11,396`) | `24.778 s` | **`38.1219 s`** (`0.310 s` / `37.271 s`) | `1.574` | `370` (`6`) | `7,210,620,416 B` |
| `carbon-dense-ba` / seg 2 | `native` | `21.387 s` (`11,039`) | `24.589 s` | **`40.3937 s`** (`0.374 s` / `39.837 s`) | `1.485` | `364` (`0`) | `7,293,326,848 B` |

- **Profiler 363-ID Identity Confirmed:** `ProfiledNative` (`carbon-moe-01` seg 1) emitted the **exact same 363 token IDs on `dev/dense` and exact same 57 token IDs on `warm`** as ordinary `native` in **both** `carbon-dense-ab` and `carbon-dense-ba`. Measured `ProfiledNative` instrumentation overhead on `dev/dense` is `6.254 s` vs mean `native` (`38.4828 s`).
- **Paired Noise vs Savings (Falsifier Failed):**
  - `AB` saving: `4.7604 s` (`1.1496×`); `BA` saving: `2.2718 s` (`1.0596×`); mean saving: `3.5161 s` (`1.1006×`).
  - Ordinary `native` paired-control drift (`|40.3937 - 36.5720|`) = **`3.8217 s`** (`carbon_bf16` drift = `6.3103 s`). The **`BA` saving (`2.2718 s`) is smaller than ordinary `native` noise (`3.8217 s`)**, and both orders miss the pre-registered **`>= 5.0×` (`<= 7.7 s`) falsifier** and `30 pages/min` customer floor (`1.57–1.89 pages/min`).

---

## 3. Causal Bottleneck Attribution, Fidelity & Small Harness Findings

1. **Why Gains Were Small (`~9–13%`) & What Actually Helped:**
   - Packed BF16 MoE (`index_select + bmm` decode, `torch._grouped_mm` prefill with `22/22` layer calls and `0` fallbacks, `-78.9 MiB` allocated VRAM) + `no_text_streamer` accounted for the reliable ~`2.6–5.2 s` improvement by collapsing 198 per-token Python expert GEMV launches into 22 batched `bmm`s.
   - `native_profile` proved `tokens_per_expert.cpu().numpy()` was only `1.126 ms/step` (`0.93%`), `moe + streamer` was `22.07%`, and **`attn_router` (`_dash_decode_forward`) is `69.03%` host (`83.94 ms/step`) / `69.95%` GPU event (`85.05 ms/step`)** with **zero `.cpu()` syncs** — caused by **`~180–200` eager Python/ATen/WDDM kernel launches per layer (`~2,200` ops/token across 12 layers)** at `9%–19%` GPU utilization. Even with `StaticDashCache` (`0` reallocations) and `gather_sparse_decode_step`, ungraphed `carbon_bf16` still launches `~1,500+` eager Python ops/token, leaving it host-dispatch bound (`86–101 ms/step`).
2. **Exact-BF16 Disqualification & Common-Scorer Quality Parity:**
   - `carbon_bf16` matched itself 100% across `AB` and `BA` (`363/363` `dense`, `57/57` `warm`) and matched ordinary `native` through token `#340` on `dev/dense`, diverging at **1 token (`#341`: `28800 '719' -> 28787 '718'` in `<BLOCK>text[60, 719, 614, 739]<FORK>`)** — **failing Exact-BF16 (`exact_bf16_qualified = false`, `lost_exactness = true`)**.
   - On `score.py`, `native`, `carbon_moe`, and `carbon_bf16` all produced **identical** scores: `39/42` cells (`0.9286`), `4/24` unflagged critical confusable (`I/1`, `O/0`) errors (`WO-O1I8 -> WO-O118`, `10-7O1 -> I0-701`, `PX-I10 -> PX-110`, `L1I -> L11`), `0` wrong-source links, and `48/496` raw edits (`0.0968` CER; `inside_quality_budget = true`, `unattended_quality_gate = false`).
3. **Small Harness & Adapter Findings (`ab-ba-summary.json`):**
   - `HARNESS-01`: `launch.py` at `55b57427` used `int(row[3])` on decimal `temperature_c` (`'46.64'`), fixed to `float(row[3])` in `7e70391c`.
   - `HARNESS-02`: `carbon_bf16` `burst_stride=8` executed `8` speculative post-EOS forwards on `warm` (`66` vs `58`) and `6` on `dense` (`370` vs `364`, `~0.52–0.62 s` penalty), truncated cleanly before token return.
   - `HARNESS-03`: `evaluate.py`'s diagnostic `BOX_RE` omitted `<LEVEL\d+>` in `<BLOCK>title<LEVEL1>[...]`.
   - `HARNESS-04`: Shared `astra/formats.py:native_page` `BLOCK_RE` also omits `<LEVEL\d+>`, leaving `<BLOCK>title<LEVEL1>[57, 61, 618, 93]<FORK>` in `pages[0]["text"]` and accounting for `43` of `48` character edits on `dev/dense` (stripping `<LEVEL1>` lowers `dev/dense` CER from `0.0968` to **`0.0101` [`5/496`]** and raises lines from `4/6` to `5/6`). Upstream `Native`'s `TextStreamer` also lacks UTF-8 child stdio enforcement (`cp1252` abort at `36/60` on `A` prior to UTF-8 replay).
