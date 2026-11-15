# WP-0005 Q0 frozen qualification protocol (author: eld-q0-harness, /002)

Status: **PREPARED, not executable.** It is frozen for the independent `/003` review. It runs only after the dependency lock is final (WP-0005 `/001` plus `/003` review) and a coordinator `/004` release record binds this protocol digest, the lock digest, the storage root and an observed single-owner GPU lease. The machine-readable source of truth is [`protocol.json`](protocol.json). Its SHA-256 is recorded in every run and must match the release record.

Q0 is an engineering qualification of the **unmodified** `baidu/Unlimited-OCR-2@0480966938291445591f69f08a13b041c073a96a` checkpoint (`research/carbon/reconciliation/02-ranked-experiment-backlog.md` §1.2, input contract §2). It is not an experiment and not production OCR integration. No accuracy is ever computed, and a failed run is a blocker. It is never recorded as 0 %.

## 1. Inputs (dev only)

| Fixture | Family / split | Pages | PDF SHA-256 | Git blob |
| --- | --- | --- | --- | --- |
| `SYN-WO-01-v0-clean` | F01 / dev | 1 | `893d08ddfc87ef6a18f846d9119d9ba68566d7914aef4bcdc47de0f991c7026f` | `ec3dd81ac80ed0a27f846868884822e1de77ee6d` |
| `SYN-MP-01-v0-clean` | F07 / dev | 3 | `15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3` | `63469e783b65f27893c9bfff94728a8feb44f12f` |

- These are the only PDFs the harness can open. `check_repo_path_allowed` refuses `evaluation/synthetic/expected/**`, `evaluation/synthetic/sources/**`, holdout families F03/F05/F06/F08, absolute paths and `..`. The harness never reads expected values, including dev expected values, because Q0 does not score.
- Rendering contract: `pypdfium2==5.15.2` (PDFium `159.0.8149.0`), `PdfDocument(verified_bytes)[i].render(scale=300.0 / 72.0).to_pil().convert('RGB')`. The bytes are read once and hash-verified before rendering, so there is no TOCTOU path. The resulting PIL RGB images go straight to `infer_multi`, with no intermediate image file.
- Frozen raster digests: each page must be `2550 x 3301` RGB and match `raster[].rgb_sha256`. These values are a **corpus-derived prediction**. `evaluation/generation/generate_corpus.py` (`rasterize_pdf_300dpi`, L783–794 and L907–916) built each dev `v1-raster300` child by applying this exact render call to these exact v0 bytes. It embedded `img.tobytes()` losslessly as one FlateDecode `/DeviceRGB` XObject per page (`pdf_writer.serialize_pdf`). `q0.py derive-rasters --check` inflates those streams with the stdlib and reproduces the digests. The released stage must render and match them; otherwise `RENDER_CONTRACT_MISMATCH`.

## 2. Native call (frozen)

```
model.infer_multi(tokenizer, prompt="Multi page parsing.", image_files=[pages in order],
                  crop_mode=False, save_results=False, output_path="", temperature=0.0,
                  max_length=131072, max_page_tokens=20000, page_count_guard=True,
                  image_size=640, base_size=1024, max_crops=16,
                  no_repeat_ngram_size=35, ngram_window=W, ngram_whitelist_token_ids=None,
                  dash_topm=16, tps_interval=0, test_compress=False, eval_mode=False,
                  max_new_tokens=8000 * pages)
```

- `prompt` is the native default string, passed explicitly. Native `infer` expands it to `'<PAGE><image>' * n + prompt` (`modeling_unlimitedocr.py` L1073–1082).
- `W = 1024 if pages > 1 else 128` and `ngram_size = 35`. Both follow the upstream README evaluation setup (`hf-README.md` L226–243). The values are identical for every call with the same page count.
- `max_new_tokens`: the accepted rule `min(8000 * pages, max_length - prompt_len)` equals `8000 * pages` whenever `prompt_len + 8000 * pages <= 131072`. After each call the harness verifies this from the native `prompt_token_ids`. Any violation is `CONTEXT_BUDGET_EXCEEDED`, a failed case, never silently clipped.
- All other values are explicit native defaults (`infer` signature, L1039–1043). `eval_mode=False` keeps the native `TextStreamer`. Its stdout goes to a bounded capture. `eval_mode` is unrelated to `eval()`.
- Stop policy is native only. EOS gives `finish_reason='stop'`. Reaching `max_new_tokens` or `max_length` gives `'length'`, which is a `TRUNCATION` failure. Native PageCountGuard (L583–605) forces `<PAGE>`/EOS. The harness adds no logits processors.
- `validate_call_kwargs` rejects any other key, value or type before every call (for example `crop_mode=0` or `temperature=0`).

## 3. Sequence and measurements

Sequence: one cold load, then one excluded warmup per fixture, then **exactly two** interleaved warm repeats per fixture: `W(F01) W(F07) R1(F01) R1(F07) R2(F01) R2(F07)`. Any classified failure stops further model calls.

| Measurement | How | Provenance |
| --- | --- | --- |
| Cold load | `perf_counter` around imports, tokenizer, `from_pretrained` (CPU), `.eval().cuda()` + `torch.cuda.synchronize()` | direct |
| Call wall time | `torch.cuda.synchronize()` before and after `infer_multi` | direct |
| Prefill | native `prefill_time = t_first - t0` in `_uocr_generate`. It is host-synchronized by `int(torch.argmax(...))` and includes vision encode, prefill and the first logits/processors | native |
| Generate total | native `time` | native |
| Decode | `time - prefill_time` | derived |
| Outside generate | wall minus native `time`: prompt build, `_uocr_build_inputs`, observer overhead, final sync | derived |
| CUDA memory | `reset_peak_memory_stats()` per call, then `max_memory_allocated/reserved`, `memory_allocated/reserved`, `mem_get_info` | direct (`device_free` includes other processes) |
| Process RSS | Windows `K32GetProcessMemoryInfo` start/end, plus a 100 ms sampler for the window peak (lower bound) and the page-fault delta | direct, sampled |
| Output tokens, finish, pages | native return dict captured at `infer` return (see §4); `<PAGE>` token positions | native and direct |
| Repeatability | exact equality of token-id SHA-256 between R1 and R2 per fixture (warmup vs R1 reported separately) | direct |

Raw output is written by the bounded stdlib writer (`writer.py`): the exact native string, plus token ids as JSON. Writes are exclusive-create, never overwrite, have a cap and report any truncation with the full digest. The model's save path is never used.

## 4. Telemetry (external, non-modifying)

`telemetry.py` uses PEP 669 `sys.monitoring` (Python ≥ 3.12, tool id 4). It sets local `PY_START`/`PY_RETURN` events on the code objects of these native functions (resolved after load from the entry module's own package and unwrapped through `torch.no_grad`):

| Target | Role / what it proves |
| --- | --- |
| `UnlimitedOCRForCausalLM.infer` (return) | captures the native dict: `finish_reason`, `num_pages_out`, `expected_pages`, `time`, `prefill_time`, `prompt`, `token_ids`, `prompt_token_ids`, `text`. `infer_multi` itself returns only `(text, len(token_ids))` (L1110–1123) |
| `UnlimitedOCRModel.forward` (return) | reads `past_key_values` metadata only (shapes/sizes, no sync): DynamicCache `seq_len` and K/V bytes per forward, `_dash_idx_k` bytes, `_prefill_length` ring-buffer marker; also the stall heartbeat |
| `DashAttention._forward_triton` | Triton attempted, non-None return = executed, `None` + handled exception = import fallback (source L1207–1211: only the import is caught) |
| `sparse_gather_e2e_triton.triton_gather_attention_e2e` (optional) | kernel entry; absent when the module cannot import |
| `DashAttention._forward_dense` | chunked-SDPA dense fallback (`q_chunk`) |
| `modeling_deepseekv2._infer_prefill_attend`, `_dash_decode_forward`, `_decode_attend`, `_orig_forward`, `configure_dash_inference` | DASH prefill/decode path, fp32 decode attend, any non-DASH attention |
| `_uocr_save_results`, `process_image_with_refs`, `draw_bounding_boxes`, `extract_coordinates_and_label` | **tripwire** (see §5) |

Exception events (`EXCEPTION_HANDLED`, `PY_UNWIND`) can only be global in 3.12, so their callbacks filter by code object. The derived label is one of `triton_executed`, `triton_import_failed_dense_fallback`, `triton_returned_none_dense_fallback`, `triton_exception_propagated`, `triton_not_attempted` or `mixed` (fail). Cache growth must be observed as +1 per decode step with no ring marker. Otherwise check 4 fails.

Unsupported (reported, not substituted): which GPU kernels Triton/SDPA dispatch internally, per-kernel GPU time and direct WDDM paging state. Overhead: self-timed callback nanoseconds and event counts per call. This is a lower bound, because interpreter dispatch and global exception-event filtering are not included. Telemetry runs identically for warmup and both repeats.

**Source inference (from pinned source, also observed where possible):** `_uocr_generate` sets `cfg._ring_window = cfg.sliding_window = None` and uses a fresh `DynamicCache` (L1149–1160). `_decode_attend` computes in fp32 (`modeling_deepseekv2.py` L455–481). The paper's constant-memory claim is not transferred to this native path.

## 5. Safety invariants

1. **Unreachable eval save path.** This is proven statically from the AST (`sourcecheck.analyze_entry_module`) on the committed snapshots now, and again on the hash-verified model directory before load:
   - the only `eval/exec/compile` is `extract_coordinates_and_label` L120;
   - its only caller chain is `draw_bounding_boxes ← process_image_with_refs ← _uocr_save_results ← infer`;
   - the single call is guarded by `if save_results and output_path:` (L1103);
   - no other module contains eval/exec/compile.

   The frozen kwargs pass **both** `save_results=False` and `output_path=""`. At runtime a `sys.monitoring` tripwire raises `SafetyTripwire` (a `BaseException`) at `PY_START` of any chain function, before its first instruction runs. It records the violation even if native bare `except:` (L194–197) swallows the exception. This tripwire is the only intervention, and it fires only on a path the protocol has made unreachable.
2. **Byte-for-byte code.** The model directory must contain exactly the 19 pinned files. Non-LFS files are checked by git-blob SHA-1 and LFS files by SHA-256 from `research/astra/sources/hf-tree.json`. Only `.cache/huggingface/**` download metadata without `.py` is tolerated. After load, every `transformers_modules.*` module file must lie in the run's own `HF_MODULES_CACHE` and be identical to the verified source. Every `.py` copied there is checked too. Nothing is patched or monkeypatched. A required source edit is `SOURCE_PATCH_REQUIRED`, a strict-baseline blocker.
3. **Isolated child environment.** The environment is built from an allowlist, never inherited. It is offline (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `local_files_only=True`), has `CUDA_VISIBLE_DEVICES=<leased GPU UUID>`, and keeps all caches/temp/home under the run directory. Every model behaviour switch found in the pinned source is absent: `TIME_DIAG*`, `DASH_*`, `WARMUP_MAIN_LOCAL_WINDOW`, `PAGE_SCOPE_PREFILL`, `CODE_STAMP_LOG`, `INDEXER_SCORE_TRITON`, `FUSED_CHUNK_CE`, `CE_CHUNK_SIZE` and `KL_*`. So are `PYTORCH_CUDA_ALLOC_CONF` and every credential-shaped name.
4. **Locked dependencies.** The installed set must equal the lock exactly (only `pip` may be unlocked). `flash_attn` and `xformers` must not be importable, because their presence changes `_sparse_base_impl` import-time paths (L165–175). `triton` must follow the lock's `triton_policy`.

## 6. Guards and failure accounting

Timeouts (harness policy, not measured performance): preflight 1800 s, load 1800 s, 1-page call 1800 s, 3-page call 3600 s, session 21600 s. A **stall** is no native model-forward return for 300 s inside a call (heartbeat every 5 s), which suggests a WDDM paging stall. The supervisor (`supervisor.py`) kills **only its own child** through its `Popen` handle. Log cap: 64 MiB. Raw output cap: 16 MiB per file.

Fail-closed classes are listed in `outcome.FAILURE_CLASSES`, including hash mismatch, unsupported platform, dependency mismatch, OOM, timeout, severe stall, safety violation, source patch required, truncation, page-count mismatch, non-determinism, context budget and telemetry unsupported. Outcome records carry `accuracy_score: null`, and `assert_no_score` rejects any score-like field anywhere.

## 7. Resources

- Storage root: `C:\Users\jackg\eLedgerCare-Q0\WP-0005` (coordinator-selected). It must equal the release record and lie outside the repository, the worktrees, `TEMP`/`TMP`, `APPDATA`/`LOCALAPPDATA` and `~/.cache`.
- Each run gets a new `runs\<author|reviewer>\<UTC>-<id>` with its own `HF_MODULES_CACHE`, temp and caches.
- GPU: `GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d` (RTX 5070 Ti, capability 12.0, `sm_120` in `torch.cuda.get_arch_list()`), concurrency 1, and exactly one visible device.
- Read-only `nvidia-smi` observations are taken pre, every 60 s and post. Desktop/WDDM activity is a recorded confounder, never a reason to stop another process.

## 8. Open items owned by `/001` and review

- The exact Python, torch/torchvision CUDA wheels, `torch.version.cuda`, `triton_policy`, every remaining wheel with SHA-256, and the index URLs are open. `locks/dependency-lock.json` stays `PENDING_ASTRA_001`, so `execute`, `write-requirements`, `verify-wheelhouse` and `preflight-cpu` all refuse.
- Transformers 4.52.1 local-directory dynamic loading with `local_files_only=True` is **not verified** by this author. The read-only fetch of upstream `dynamic_module_utils.py` was denied in this session. The design does not depend on it: the module-cache identity check runs after load, and an `IMPORT_FAILURE`/`SOURCE_PATCH_REQUIRED` blocker is reported honestly.
- The exact `pypdfium2.version.PDFIUM_INFO` string form is verified only by `preflight-cpu`, which fails closed if `159.0.8149.0` is absent from it.
- The `nvidia-smi` observer command combines two query modes in one call and is unvalidated. It must be run once read-only before the lease, and split by reviewed amendment if it errors. A failing observer is recorded, not fatal.
- The imports of `configuration_deepseek_v2.py`, `conversation.py` and `packing_patch.py` are not in the committed snapshots. They are statically checked after acquisition.
