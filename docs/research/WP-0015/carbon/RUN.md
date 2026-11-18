# WP-0015 Carbon Baidu BF16 Challenger, Ablations & Stage Profiler

## 1. Candidate Reconciliation & Attribution

Both independent R&D positions are frozen and preserved unchanged:
- **`eld-rd-astra` (`7aa1d14c25b9317fd791aa8981816bc78e2d46a6`, report `0f65eb6e580a91ac5276440e4d052ebb596d26ca`, common harness `6f14c8733da33fa144f3924f9929c9c748b21586`):** Installed Windows `en-US` optical character recognizer (`Windows.Media.Ocr`, `Windows.Media.Ocr.dll` `10.0.26100.9278`) with pixel word rectangles and ruled-grid table reconstruction, eliminating Baidu's serial autoregressive decoding and evaluated under **Changed-Output**.
- **`eld-rd-carbon` (`8acea1ca42aa23ad48a752c642107b9e9f883f47`, report `28336734741c1ed33f1e6fd7b19dd6268a04fe93`):** Materially different **Baidu BF16 Challenger** (`carbon_bf16`, plus isolated single-variable ablations `carbon_moe` and `carbon_gather`, and stage profiler `native_profile`) running on the **unmodified `baidu/Unlimited-OCR-2` (`0480966938291445591f69f08a13b041c073a96a`) BF16 checkpoint**, `3`-page windows, `300`-DPI PDFium RGB rasters (`pypdfium2==5.15.2` / `pdfium=159.0.8149.0`), greedy decoding (`temperature=0.0`, `crop_mode=False`, `no_repeat_ngram_size=35`, `page_count_guard=True`), and Astra's shared `formats.native_page` projection (`6f14c8733da33fa144f3924f9929c9c748b21586`) + custodian's frozen 26-control scorer (`7598bf4155452c4a1294b7421595009d39ea1bc9`).

## 2. Modes, Single-Variable Ablations & Group Label

Each contiguous mode block in a plan executes inside its **own fresh, isolated child process** (`concurrency = 1`, `~7.5 GiB` peak VRAM per process, zero dual-model VRAM residency or shared-module state spillover):

| Mode | Changed Variable(s) vs `native` | Purpose |
| --- | --- | --- |
| `native` | None (reuses `astra/native.py` unmodified) | Matched Resident Native BF16 speed & quality control (`window=3`). |
| `native_profile` | Non-modifying deferred `cuda.Event` pool (`<=256` steps, synced once post-call) + host `perf_counter_ns` spans | Tests Carbon's `>=60%` decode-stage falsifier on `dense`; records GPU stream spans separately from post-sync host stalls and documents async launch coupling. |
| `carbon_moe` | `["packed_bf16_moe", "no_text_streamer"]` | **Single-variable MoE dispatch ablation:** packs 64 routed experts in-place (`[64,1792,1280]` / `[64,1280,896]` BF16, zero net weight VRAM delta), runs decode (`N=1`) via GPU `index_select + bmm` (eliminating all 11 `tokens_per_expert.cpu().numpy()` syncs + 64-way Python loops) and prefill via `torch._grouped_mm` (with logged fallback if rejected on `sm_120`), and disables `TextStreamer` stdout printing. |
| `carbon_gather` | `["static_kv_gather_sparse_decode", "no_text_streamer"]` | **Single-variable attention/cache ablation:** replaces `DynamicCache` & `_dash_idx_k` `torch.cat` reallocations, full `head_cls` recomputations, and full-KV FP32 `_decode_attend` with pre-allocated static BF16 KV buffers, incremental tail-block `k_bar`, and disjoint gather-only `<=512`-key sparse decode attention (`12×32` routed blocks `∪` `128` local window). |
| `carbon_bf16` | `["packed_bf16_moe", "static_kv_gather_sparse_decode", "gpu_logit_guards_burst8", "no_text_streamer"]` | **Group-integrated Baidu BF16 challenger:** combines `carbon_moe` + `carbon_gather` + sync-free GPU 35-gram (`unfold` + dummy-slot `scatter_`) & GPU `PageCountGuard` + `stride=8` async GPU decode bursts (1st token synced for exact `first_token` mark; subsequent steps polled every 8 tokens and truncated cleanly at first `EOS`). |

## 3. Commands, Resource Ceilings & Post-Run Scoring

- **CPU preflight & real-module CPU unit tests (zero CUDA queries, `torch.cuda.*` hard-blocked):**
  ```powershell
  $env:CUDA_VISIBLE_DEVICES=""
  & "C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe" -I -B `
    "C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/speed-carbon/docs/research/WP-0015/carbon/prepare.py" `
    --label <NEW_PREP_LABEL>
  ```
- **Coordinator-released GPU execution (`launch.py`):**
  ```powershell
  & "C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe" -I -B `
    "C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/speed-carbon/docs/research/WP-0015/carbon/launch.py" `
    --source <FULL_40_HEX_COMMIT> `
    --plan <ABSOLUTE_PLAN_JSON> `
    --sha256 <PLAN_SHA256> `
    --owner carbon `
    --run <NEW_RUN_LABEL> `
    --seconds <FINITE_SECONDS> `
    --lease <COORDINATOR_LEASE_ID> `
    --min-vram-mib 12000
  ```
  - **Enforced ceilings:** single GPU `GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d`, `>= 12,000 MiB` free VRAM before launch and before each segment, `>= 20 GiB` free disk (`21,474,836,480` B), `<= 3.5 GiB` (`3,758,096,384` B) under `C:/Users/jackg/eLedgerCare-Speed/WP-0015/carbon/`, clean Git trees across all 5 dependent scopes, `taskkill /PID <child> /T /F` on timeout or guard breach.
- **Post-run CPU Exact-BF16 & Changed-Output evaluation (`evaluate.py`, zero `torch` import):**
  ```powershell
  & "C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe" -I -B `
    "C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/speed-carbon/docs/research/WP-0015/carbon/evaluate.py" `
    "C:/Users/jackg/eLedgerCare-Speed/WP-0015/carbon/runs/<RUN_LABEL>" `
    --out "C:/Users/jackg/eLedgerCare-Speed/WP-0015/carbon/runs/<RUN_LABEL>/evaluation-summary.json"
  ```
  - Checks strict token-by-token, stop/EOS, `<PAGE>` count, and page-state equality (`exact_bf16_qualified`; any mismatch sets `lost_exactness: true` even if coordinate-stripped text matches) AND runs custodian `score.py` (`<= +0.01` CER, `>= -0.02` cell accuracy, zero new wrong-source/unflagged critical errors).
