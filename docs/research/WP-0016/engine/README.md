# WP-0016 Engine Lane (`eld-rd-carbon`) — Gate G0 Freeze & Bounded CPU Telemetry

- **Owner / model:** `eld-rd-carbon` (Gemini 4 Carbon High)
- **Worktree / branch:** `gates-carbon` · `research/wp-0016-engine`
- **Engine base:** `61bec47689dcdf272a525185013f2dce6335fa24` (`7e70391cd790a95c68906902dbd9d5bc479aa9c0` + 6-line UTF-8 child stream reconfigure in `docs/research/WP-0015/astra/trial.py`)
- **Distinct G0 source freeze commit:** `c7b2ee3663317e42a0e9bdd7ff9e17f16747d2cf`
- **Execution status:** **CPU-only.** Zero GPU/CUDA execution performed. Canonical report `002` held until coordinator G0 disposition. G1 and G2 engine implementations remain held pending prerequisite gate acceptance.

## 1. Gate G0 Isolated Wrapper (`g0.py`)

`docs/research/WP-0016/engine/g0.py` (frozen at `c7b2ee3663317e42a0e9bdd7ff9e17f16747d2cf` and unchanged in subsequent CPU telemetry commits) loads `docs/research/WP-0015/carbon/launch.py` in process with:

- `PACKET = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0016")`
- `MODES = ("native", "carbon_bf16")`
- `SCOPES = (*SCOPES, "docs/research/WP-0016/engine/g0.py")` (verifies all five WP-0015 trees plus the exact `g0.py` blob and clean porcelain status)
- Unchanged CLI argv (`--owner review|carbon --source <40-hex> --plan <abs_plan_json> --sha256 <64-hex> --run <label> --lease <id> --seconds <1..10800> [--min-vram-mib 12000]`)
- Unchanged child command (`C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe -I -B <worktree>/docs/research/WP-0015/carbon/trial.py <seg_dir>`), which imports `<worktree>/docs/research/WP-0015/astra/trial.py` at module load time and therefore applies the `61bec476` UTF-8 `sys.stdout`/`sys.stderr` stream reconfiguration before `TextStreamer` prints under `-I`.

### Exact CLI invocation (`--owner review`)

```powershell
& "C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe" -I -B `
  "<REVIEW_WORKTREE>/docs/research/WP-0016/engine/g0.py" `
  --owner review `
  --source c7b2ee3663317e42a0e9bdd7ff9e17f16747d2cf `
  --plan <ABSOLUTE_PLAN_JSON> `
  --sha256 <PLAN_SHA256> `
  --run <UNIQUE_RUN_LABEL> `
  --lease <COORDINATOR_LEASE_ID> `
  --seconds <FINITE_BUDGET_1_TO_10800>
```

## 2. Early Source Verification, Memory Peak & Cache Instrumentation Concerns

1. **`--source` must contain `g0.py` (`c7b2ee36...` or descendant with identical `g0.py` blob):**
   - Because `g0.py` adds `"docs/research/WP-0016/engine/g0.py"` to `SCOPES` to prevent unstaged/hand-edited wrapper drift, passing pre-wrapper `--source 61bec47689dcdf272a525185013f2dce6335fa24` fails closed (`fatal: path 'docs/research/WP-0016/engine/g0.py' exists on disk, but not in '61bec476...'`). Scoping specifically to the file `g0.py` (rather than the directory `docs/research/WP-0016/engine`) allows `--source c7b2ee3663317e42a0e9bdd7ff9e17f16747d2cf` to remain valid even when `HEAD` includes later commits in `docs/research/WP-0016/engine/` or `docs/reviews/WP-0016/`.
   - `launch.py` checks `SCOPES` once before segment 1; multi-segment integrity relies on worktree isolation (`gates-review` not being mutated mid-run).
   - Plan request `label` values must match `[a-z0-9-]{1,28}` (lowercase ASCII alphanumeric and hyphens only; uppercase `"H"`/`"A"` or underscores fail `launch.py` validation).
   - Contiguous mode grouping (`split_contiguous_segments`) spawns one fresh `trial.py` child per contiguous mode run; keep all `native` requests (`3 warmups + H + A`) contiguous and all `carbon_bf16` requests (`3 warmups + H + A`) contiguous so each order (`AB`, `BA`) spawns exactly two fresh model processes (six warm-ups per order).
2. **Allocator vs. Device Memory Peak (`<= 10,000 MiB` G0 gate):**
   - `window-*.json` records PyTorch caching-allocator peaks (`vram.cuda_max_allocated_bytes`, `vram.cuda_max_reserved_bytes`) reset per 3-page window via `torch.cuda.reset_peak_memory_stats()`. These **exclude** ~300–900+ MiB of CUDA primary context, loaded cubins, cuBLASLt workspace, and WDDM driver overhead.
   - `CarbonEngine.__init__` packs MoE weights one layer at a time (`+420 MiB` transient allocation before freeing old expert modules), calls `torch.cuda.empty_cache()`, and records `weight_allocated_bytes_after_pack` / `weight_reserved_bytes_after_pack` in `load-carbon_bf16.json`; `Native.__init__` does not record post-load weight bytes in `load-native.json`.
   - `launch.py` polls board-wide `nvidia-smi` (`memory.used`, `memory.free`) only every **`5.0` seconds**, which aliases 2.2-second `carbon_bf16` windows and includes non-owned Windows desktop (`dwm.exe`) VRAM. Coordinator's separate high-rate external sampler is required for authoritative device-level peak verification, reported independently alongside PyTorch allocator peaks.
   - `launch.py` enforces `--min-vram-mib 12000` free VRAM before run and before each segment, and `<= 3.5 GiB` (`3,758,096,384` B) cumulative disk usage under `C:/Users/jackg/eLedgerCare-Speed/WP-0016/<owner>`.
3. **Static KV Contract Observability vs. Unverifiable Scope in Unmodified G0:**
   - **Directly observable in `carbon_bf16` logs:** `static_cache_reallocations`, `prompt_len` (`s_prefill`), `forward_count`, `burst_extra_forwards`, `len(window_token_ids)`, `vram.*`, and `load-carbon_bf16.json` packed weight bytes. (`native` uses HuggingFace `DynamicCache` with per-token `torch.cat` reallocation and has no static KV cache.)
   - **Deterministically reconstructible on CPU (`g0_telemetry.py`):** From `config.json` (`L=12, nkv=10, hd=128, block_size=32, index_dim=128`) and `engine.py`, `StaticDashCache` costs exactly **`67,776` bytes per token slot** (`277,610,496` B = **`264.75 MiB`** at default `init_cap_tok = 4096`; `555,220,992` B = **`529.50 MiB`** if a window exceeds `4096` total tokens and triggers `_grow()`). Also observable: `burst_extra_forwards` (`0..7`) post-EOS forward steps inside `carbon_bf16`'s 8-token burst DO append into the per-window `StaticDashCache` before host truncation; this is benign in G0 because `StaticDashCache` is discarded per window, whereas G2 persistent/batched `B=4` CUDA-graphed decode (`1,059.00 MiB` at `cap_tok = 4096`) MUST mask/suppress KV and `_dash_idx_k`/`k_bar` writes past live EOS!
   - **Explicitly unverifiable without changing unmodified control:** live `data_ptr()` stability across steps (only implied within-window by `static_cache_reallocations == 0`; not preserved across windows in G0 because `StaticDashCache` is re-instantiated per 3-page window after `DynamicCache` prefill), `Native` post-load weight-only allocator bytes, and exact separation of prefill activation peak vs. decode cache peak within a single window's `reset_peak_memory_stats()` span.

## 3. Passive CPU Telemetry, Gate Processor & Tokenizer Census (`g0_telemetry.py`, `verify_cpu.py`)

- `g0_telemetry.py`: Zero-`torch` passive run auditor, static-KV footprint reconstructor, malformed-header / invented-table classifier, dual-parser (`formats.native_page` + `0186467670074761a777602d77b53deff3451300` `title<LEVELn>` rule) wrapper over unchanged `score.py` (`1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7`), four-way critical transition & Windows crossover (`15.6546455 s` on A) calculator, and G0/G1/G2 numerical gate evaluator.
- `verify_cpu.py` / `cpu-preflight-receipt.json`: Verified on CPU (`CUDA_VISIBLE_DEVICES=""`, `torch_imported: false`, 26/26 `check_score.py` controls). Also records exact Q0 `tokenizer.json` composite-token findings for post-G0 G1 alignment:
  - `lm_head` width is `129,280`, while `tokenizer` maps `128,831` tokens (`0..128830`), leaving **`449` unmapped tail rows (`128831..129279`)** that must be masked.
  - Added structural tokens: `1` (EOS), `128821..128824` (`<td>`, `</td>`, `<tr>`, `</tr>`), `128827` (`<PAGE>`), `128828` (`<BLOCK>`), `128829` (`<FORK>`), `128830` (`<CHILD>`). `<LEVELn>` is **not** an added token.
  - BPE contains all `10` 1-digit, `100` 2-digit, and `1,000` 3-digit ASCII tokens (`0`..`999`), `0` 4+-digit tokens, `81` non-ASCII Unicode `\d+` tokens, label+bracket tokens (`46011` `"-["`, `54710` `"_["`), comma+whitespace tokens (`989` `",\n"`, `1537` `" ,"` [invalid in `formats.BLOCK`!], `2893` `",\n\n"`), and bracket+whitespace tokens (`6105` `" ]"` [valid before `<FORK>`], `2296` `"]\n"` [invalid before `<FORK>`!]). Each of the 4 coordinates therefore requires explicit `0/1/2/3`-digit sub-states rather than a single phase state.
