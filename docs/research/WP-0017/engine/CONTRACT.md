# WP-0017 Engine & Probe Interface Contract (`eld-rd-carbon`)

- **Engine schema:** `eledgercare.wp0017.ablation-engine/1`
- **Probe schema:** `eledgercare.wp0017.span-logit-probe/1`
- **A1 summary schema:** `eledgercare.wp0017.a1-summary/1`
- **Model & weights pin:** `baidu/Unlimited-OCR-2` (`0480966938291445591f69f08a13b041c073a96a`, BF16 unmodified)
- **Engine & wrapper base:** `61bec47689dcdf272a525185013f2dce6335fa24` / `c7b2ee3663317e42a0e9bdd7ff9e17f16747d2cf`
- **Scorer & title pins (external, unchanged):** `score.py` (`1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7`), title rule (`0186467670074761a777602d77b53deff3451300`)

---

## 1. Orthogonal 6-Switch Decomposition (`switches.py`)

Bit order matches `docs/research/WP-0017/design/rules.py:SWITCHES = ("S0", "S1a", "S1b", "S1c", "S2", "S3")`.

| Bit | Switch ID | Flag Name | `False` (Native Path) | `True` (Carbon Path) | Window Activation Telemetry |
| --- | --- | --- | --- | --- | --- |
| 0 | `S0` | `no_text_streamer` | Upstream `TextStreamer.put` per returned non-EOS token + `end()` (with `S3=True`, streams accepted pre-EOS chunk tokens on burst return) | Silent token accumulation (`UTF-8` safe) | `s0_streamer_put_calls`, `s0_streamer_end_calls`, `s0_silent_accum_tokens` |
| 1 | `S1a` | `packed_moe_prefill` | Per-expert `F.linear` loop + `.cpu().numpy()` sync during multi-token prefill (honors `S1c`) | Sorted `torch._grouped_mm` over packed routed experts during prefill (honors `S1c`; explicit per-layer fallback counter if unsupported) | `s1a_prefill_grouped_mm_calls`, `s1a_prefill_fallback_calls`, `s1a_prefill_linear_loop_calls`, `per_layer_prefill_*`, `effective_prefill_dispatch` |
| 2 | `S1b` | `packed_moe_decode_bmm` | Per-expert `F.linear` loop + `.cpu().numpy()` sync during `q_len == 1` decode (honors `S1c`) | Selected-expert `index_select` + `torch.bmm` dispatch during `q_len == 1` decode (honors `S1c`) | `s1b_decode_bmm_calls`, `s1b_decode_linear_loop_calls`, `s1b_decode_linear_expert_calls` |
| 3 | `S1c` | `fused_gate_up_proj` | Separate `gate_proj` and `up_proj` GEMMs across Layer-0 dense MLP, shared experts, and routed experts in both prefill and decode | Concatenated `[gate_proj; up_proj]` GEMM + `.split(inter, dim=-1)` before `SiLU` across Layer-0 dense, shared, and routed experts in both prefill and decode | `s1c_dense_{fused,unfused}_calls`, `s1c_shared_{fused,unfused}_calls`, `s1c_routed_{fused,unfused}_op_calls` |
| 4 | `S2` | `gather_sparse_decode` | `DynamicCache` + upstream `_dash_decode_forward` / `_decode_attend` over full KV | `StaticDashCache` (`init_cap = max(4096, s_prefill + 2048)` rounded to `block_size=32`) + 512-key `gather_sparse_decode_step` | `s2_static_gather_decode_calls`, `s2_dynamic_masked_decode_calls`, `cache_telemetry.{init_cap_tok,final_cap_tok,max_cap_tok,peak_seq_len,reallocations,gathered_key_width}` |
| 5 | `S3` | `gpu_burst_stride_8` | 1-step host guarded greedy loop (`_uocr_no_repeat_ngram`, `_uocr_page_count_guard`) with immediate EOS stop | 8-step device guarded greedy burst (`gpu_no_repeat_ngram`, `gpu_page_count_guard`) with post-EOS host truncation | `s3_single_step_iters`, `s3_burst_chunks`, `s3_burst_steps_launched`, `s3_burst_extra_forwards` |

### Endpoint Bindings & Observer Disclosure (`ablation_engine.py`)
- `native`: binds genuine `docs/research/WP-0015/astra/native.py:Native` (`observer_kind = "astra_stage_monitor_pep669"`).
- `carbon_bf16`: binds genuine `docs/research/WP-0015/carbon/engine.py:CarbonEngine("carbon_bf16")` (`observer_kind = "carbon_safety_monitor_wrapped"`).
- `all_off` (`000000`), `all_on` (`111111`), `add_S0..add_S3`, `remove_S0..remove_S3` (alias `rem_S0..rem_S3`), `remove_<Si>_<Sj>` (all 15 pairs), `s_000000..s_111111`, and `carbon_surgical`: bind `AblationEngine` (`observer_kind = "wp0017_uniform_ablation_observer"`).
- Stage A1 canonical sweep runs **16 isolated child processes**: `native`, `all_off`, `carbon_bf16`, `all_on`, 6 single additions, and 6 single removals, proving both genuine endpoint replay and parameterized `000000`/`111111` cross-observer equivalence before attributing any switch effect.

---

## 2. Stage A1 Two-Phase Isolation & Output Schema (`a1_trial.py`, `span_probe.py`, `a1_analyze.py`)

Each isolated child directory `<packet_root>/<owner>/runs/<run>/segment-XX-<mode>/` executes:
1. **Untimed Cold-Init Settling (`warmups/`):** Runs configurable 1-page warmups (default `3`, matching WP-0016 `g0-ab` `warm-1..warm-3` on `docs/research/WP-0014/eld-latency-author/A.pdf`) via `astra_trial.document` and records `warmups/warmups-summary.json`.
2. **Phase 1 — Ordinary Free Run (`free/`):** Renders exact 3-page slices (`window-019`: pages 19–21; `window-037`: pages 37–39) from full 60-page `source.pdf` using original `astra_trial.inputs` (pre-verifying 300-DPI RGB SHA-256) and calls `eng.read(batch, free_dir)` with **zero probe hooks**. Freezes `free/window-{019,037}.json`, `free/raw-*.json`, `free/page-*.json`, and `free/ordinary-timing.json` before Phase 2 starts.
3. **Phase 2 — Serial-Decode Teacher-Forced Span-Logit Probe (`probe/`):**
   - Structural locators are frozen from the anchored native token histories (`<PAGE>` index, `<BLOCK>` ordinal `1`, fixed label `"Inspection "`) and never search new outputs for competing ID strings.
   - Replays prompt prefill once, then steps **1 token at a time (`q_len == 1`)** through all prefix tokens and branches via `clone_kv_cache` across the competing identifier tokenizations:
     - `window-019`: `[' I', '08', 'O', '1', '-', '388']` (`[342, 3019, 49, 19, 15, 21895]`) vs `[' ', '108', 'O', '1', '-', '388']` (`[223, 6924, 49, 19, 15, 21895]`) at `t* = 417`.
     - `window-037`: `['8', 'OI', '10', '-', '774']` (`[26, 90169, 553, 15, 30591]`) vs `['80', 'I', '10', '-', '774']` (`[1892, 43, 553, 15, 30591]`) at `t* = 41` (with shared `' '` `223` at `t = 40` also logged), evaluated on **both** `forced_native` (`291` at `t = 7`, with `t = 7` top-5/margin logged) and `free_running` window prefixes.
   - Records full-vocabulary FP32 `log_softmax` sums (`ell_common_boundary_guarded_nats`, `ell_full_with_space_guarded_nats`, `ell_common_boundary_raw_nats`), odds contrast `D = ell(native_id) - ell(carbon_id)`, top-5 candidates, explicit ranks/logits of both competing branch tokens even below rank 5, `margin_top1_top2_fp32`, tie status, device-synchronized probe prefill/decode ms, and offline `< 0.125` logit-margin diagnostics (`flagged: false` in emitted pages remains untouched).
4. **Run-Level Summary (`<run_dir>/a1-summary.json` & `<run_dir>/process.json`):**
   - `a1_analyze.py` gates all attribution and surgical selection on `anchor_verification.anchor_gate_passed == true` (whole-array token equality, SHA-256 match, `finish_reason == "stop"`, `eos_id` excluded across all present endpoints).
   - `process.json` exposes `segments` and `all_segments_completed` directly compatible with `device_lease.py`.

---

## 3. Stage A2 / A3 Document Harness (`doc_trial.py`, `launch.py`)

When `--plan` supplies `{"requests": [...]}` (the WP-0015/WP-0016 request schema), `launch.py` dispatches `doc_trial.py` per contiguous mode segment (`native`, `carbon_bf16`, `carbon_surgical`, or any explicit switch name) and invokes original `docs/research/WP-0015/astra/trial.py:document` directly, preserving identical `prediction.json`, `timing.json`, `window-NNN.json`, `raw-NNN.json`, and `page-NNN.json` schemas. `surgical.json` keeps `carbon_surgical` locked (`frozen_switch_config: null`) until Stage A1 disposition freezes at most one pruned configuration.
