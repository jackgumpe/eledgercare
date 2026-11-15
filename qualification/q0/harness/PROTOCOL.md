# WP-0005 Q0 frozen qualification protocol (author: eld-q0-harness, /002)

Status: **FROZEN for the independent `/003` review. Not executable.** All 32 locked wheels now have an effective SHA-256: 31 publisher-declared, plus torchvision as `local-sha256-TOFU` bound to the independent reviewer receipt (§8). Coordinator `eldq0-release/2` records must still exist for the install and execute stages. Each record binds:
  - the accepted review;
  - the exact harness commit, clean;
  - the protocol and lock SHA-256 values;
  - any accepted provenance exceptions;
  - the storage root;
  - for execution only, an observed single-owner GPU lease.

The lock never names the review that accepts it. Only the release record binds these identities together, which removes the circular requirement from checkpoint 1.

The machine-readable source of truth is [`protocol.json`](protocol.json). Its SHA-256 is recorded in every run and must match the release record. Dependency lineage:

- Astra `/001`: `95ce0a8d…` / `2c32dde6…`;
- Astra `/007`: candidate `d666c416…`, evidence `6cb6a258…`, report `951d408a…`;
- reviewer phase A findings Q0R-01..09: `b75011da…`.

`protocol.json` `lineage` holds the full SHAs.

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
| Prefill-boundary memory (Q0R-04, F07 prefill VRAM) | allocator `max_memory_allocated/reserved` read once per call, at the first model-forward return. These are host-side allocator counters: no sync and no change to the model | direct (allocator peak through the prefill launch, not a kernel-level measurement) |
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

Exception events (`EXCEPTION_HANDLED`, `PY_UNWIND`) can only be global in 3.12, so their callbacks filter by code object. The derived label is one of:

- `triton_executed`
- `triton_import_failed_dense_fallback`
- `triton_returned_none_dense_fallback`
- `triton_exception_propagated`
- `triton_not_attempted`
- `mixed`

**Frozen baseline path (Q0R-04).** The lock contains no Triton, flash-attn or xformers. `find_spec('triton') is None` is asserted and recorded. Check 4 passes only when every call is labelled `triton_import_failed_dense_fallback`, the DynamicCache grows by +1 per decode step and no ring marker appears. The result is then labelled **"unmodified model on non-Triton fallback path"**. Any other label, including Triton actually executing, does not match the frozen baseline: `TELEMETRY_UNSUPPORTED` / NOT_QUALIFIED. `_orig_forward` calls (the base sparse-attention path) are counted per call. Without Triton, that path's eager block-mask fallback materializes `[B,H,Sq,Sk]` (`_sparse_base_impl` L1803–1811).

**Raw logs.** The supervisor preserves child stdout/stderr byte-for-byte and scans them (`logscan.py`) for the model's own diagnostic lines: `[SparseAttn] triton gather path failed` (L1761), `[DASH] Triton block-sparse path active` (L1224), `[CodeStamp]`, and others. These markers are supplementary. The DASH fallback is silent, so the **absence** of a marker is never treated as evidence of a path.

Unsupported (reported, not substituted): which GPU kernels Triton/SDPA dispatch internally, per-kernel GPU time and direct WDDM paging state. Overhead: self-timed callback nanoseconds and event counts per call. This is a lower bound, because interpreter dispatch and global exception-event filtering are not included. Telemetry runs identically for warmup and both repeats.

**Source inference (from pinned source, also observed where possible):** `_uocr_generate` sets `cfg._ring_window = cfg.sliding_window = None` and uses a fresh `DynamicCache` (L1149–1160). `_decode_attend` computes in fp32 (`modeling_deepseekv2.py` L455–481). The paper's constant-memory claim is not transferred to this native path.

## 5. Safety invariants

1. **Unreachable eval save path.** This is proven statically from the AST (`sourcecheck.analyze_entry_module`) on the committed snapshots now, and again on the hash-verified model directory before load:
   - the only `eval/exec/compile` is `extract_coordinates_and_label` L120;
   - its only caller chain is `draw_bounding_boxes ← process_image_with_refs ← _uocr_save_results ← infer`;
   - the single call is guarded by `if save_results and output_path:` (L1103);
   - no other module contains eval/exec/compile.

   The frozen kwargs pass **both** `save_results=False` and `output_path=""`. At runtime a `sys.monitoring` tripwire raises `SafetyTripwire` (a `BaseException`) at `PY_START` of any chain function, before its first instruction runs. It records the violation even if native bare `except:` (L194–197) swallows the exception. This tripwire is the only intervention, and it fires only on a path the protocol has made unreachable.
2. **Byte-for-byte code (18 runtime objects plus a separate notice, Q0R-09).** The model directory must contain exactly the **18 runtime objects**. 16 non-LFS files are checked by git-blob SHA-1 and size, and 2 shards by LFS SHA-256 and size, all from `research/astra/sources/hf-tree.json`. The checks are transport-independent: xetHash and LFS pointer OIDs are never used as payload digests. The model card `README.md` (blob `c79e1e33…`, 14,107 B) is a separately verified **notice** in `notices\…`, not a runtime object. A README inside the runtime directory is `UNEXPECTED_ARTIFACT`.

   Only `.cache/huggingface/**` download metadata without `.py` is tolerated. Symbolic links and reparse points are rejected. After load, every `transformers_modules.*` module file must lie in the run's own `HF_MODULES_CACHE` and be identical to the verified source, and every `.py` copied there is checked too. Nothing is patched or monkeypatched. A required source edit is `SOURCE_PATCH_REQUIRED`, a strict-baseline blocker.
3. **Normalized offline local loading (Q0R-06).** `normalize_model_dir` requires the model directory to be:
   - absolute and normalized, with no trailing separator;
   - existing, and not a reparse point;
   - equal to the protocol path;
   - named with a Python identifier as its basename (`Unlimited_OCR_2_04809669`). That basename becomes the `transformers_modules` package name: upstream's local branch uses `basename(path)`, and a missing directory would otherwise be parsed as a repo ID.

   The offline flags are set when the child process is created. `backend_torch.load` asserts they are present and that no HF module is imported yet. A DLL/ABI ImportError is a platform failure, and the harness never falls back to a repo ID.
4. **Isolated child environment (Q0R-05).** The environment is built from an allowlist, never inherited. It is offline (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_XET=1`, `PIP_NO_INDEX=1`, `local_files_only=True`) and has `CUDA_VISIBLE_DEVICES=<leased GPU UUID>`.
   - Under the run directory: `TEMP`/`TMP`/`TMPDIR`, `HF_MODULES_CACHE`, `TORCH_HOME`, `TORCHINDUCTOR_CACHE_DIR`, `TRITON_CACHE_DIR`, `CUDA_CACHE_PATH` (NVIDIA ComputeCache), `PIP_CACHE_DIR`, `UV_CACHE_DIR`, `XDG_CACHE_HOME` and home.
   - Under the task root: `HF_HOME`, `HF_HUB_CACHE`, `HUGGINGFACE_HUB_CACHE` and `TRANSFORMERS_CACHE`.

   Every model behaviour switch found in the pinned source is absent: `TIME_DIAG*`, `DASH_*`, `WARMUP_MAIN_LOCAL_WINDOW`, `PAGE_SCOPE_PREFILL`, `CODE_STAMP_LOG`, `INDEXER_SCORE_TRITON`, `FUSED_CHUNK_CE`, `CE_CHUNK_SIZE` and `KL_*`. So are `PYTORCH_CUDA_ALLOC_CONF` and every credential-shaped name. Both `build_stage_env` and `build_child_env` keep `PATH` restricted to `venv\Scripts`, `System32` and `SystemRoot`, and pin the validated host Git binary in `Q0_GIT_EXECUTABLE` alongside `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=NUL` and `GIT_TERMINAL_PROMPT=0` so mandatory read-only Git checks (`code_identity` and `git_blob_reader`, invoked via `run_git` with `--no-optional-locks`) work across isolated subprocess boundaries without exposing sibling executables on `PATH` or reading user/system Git configuration.
5. **Locked dependencies (bound lock).** `locks/dependency-lock.json` (`eldq0-lock/2`) reads the 32 artifacts from the exact Git blob `ec8c650e…` of Astra `/007` `metadata-lock.json`. It checks that blob's SHA-1, size, status and AMD64 marker environment, the 32/31/1 counts and the total bytes. It also checks the fixed versions transformers 4.52.1, pypdfium2 5.15.2, torch 2.13.0+cu130 and torchvision 0.28.0+cu130, and that no accelerated backend is present.

   The installed set must equal those 32 exactly; only `pip` may be unlocked. The PyPI CPU `torch 2.13.0` counts as a mismatch (Q0R-08). `flash_attn`, `xformers` and `triton` must not be importable (`find_spec is None`).

   **Every-wheel METADATA check before install (reviewer N-02).** `verify-wheelhouse` checks each of the 32 acquired wheels after its size and effective SHA-256. It reads the wheel's own top-level `dist-info/METADATA` from the ZIP, with no extraction or import. The check (`locks.verify_wheel_metadata`) requires:
   - `Name` and `Version` exactly as locked;
   - the multiset of `Requires-Dist` entries equal to that artifact's frozen graph edges. These are all 850 recorded requirements, active and inactive, and they reproduce each artifact's published Requires-Dist exactly. The comparison only normalizes formatting: canonical name, sorted extras and specifiers, marker whitespace and quote style. Nothing else is relaxed;
   - for torch and torchvision, METADATA bytes that hash to the official index's published PEP 658 digest. These digests are read from the bound `cuda-metadata.json` blob `bca91aaa…`, whose recorded bodies are re-hashed.

   Any divergence is `HASH_MISMATCH` and blocks installation.

## 6. Guards and failure accounting

Timeouts (harness policy, not measured performance): preflight 1800 s, load 1800 s, 1-page call 1800 s, 3-page call 3600 s, session 21600 s. A **stall** is no native model-forward return for 300 s inside a call (heartbeat every 5 s), which suggests a WDDM paging stall. The supervisor (`supervisor.py`) kills **only its own child** through its `Popen` handle. Log cap: 64 MiB. Raw output cap: 16 MiB per file.

**Free-space floor (Q0R-05).** At least 58 GiB must be free before the first download (`host-precheck --stage initial`). At least 20 GiB must remain at session preflight and on every supervisor poll; otherwise the supervisor raises `STORAGE_FLOOR` and kills its child. The floor is a stop buffer, not a measured bound. Pagefile growth and OS/driver allocations outside the root are unknown and additional. Commit limit, available commit and paging-file configuration are recorded read-only.

Fail-closed classes are listed in `outcome.FAILURE_CLASSES`, including hash mismatch, unsupported platform, dependency mismatch, OOM, timeout, severe stall, safety violation, source patch required, truncation, page-count mismatch, non-determinism, context budget and telemetry unsupported. Outcome records carry `accuracy_score: null`, and `assert_no_score` rejects any score-like field anywhere.

## 7. Resources

- Storage root: `C:\Users\jackg\eLedgerCare-Q0\WP-0005` (coordinator-selected). It must equal the release record and lie outside the repository, the worktrees, `TEMP`/`TMP`, `APPDATA`/`LOCALAPPDATA` and `~/.cache`.
- Each run gets a new `runs\<author|reviewer>\<UTC>-<id>` with its own `HF_MODULES_CACHE`, temp and caches.
- Model runtime directory `models\Unlimited_OCR_2_04809669` (identifier-safe; see §5.3). The coordinator accepted it in place of the originally proposed leaf `models\0480966…`, which starts with a digit. Notice: `notices\Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a\README.md`.
- GPU: `GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d` (RTX 5070 Ti, capability 12.0, `sm_120` in `torch.cuda.get_arch_list()`), concurrency 1, and exactly one visible device.
- **Observer plan (reconciled).** The checkpoint-1 single command that combined `--query-gpu` and `--query-compute-apps` is replaced by two separate read-only queries, both bound by `--id=<UUID>`:
  - **GPU query:** `--query-gpu=timestamp,uuid,name,driver_version,compute_cap,memory.total,memory.used,memory.free,utilization.gpu,pstate --format=csv,noheader,nounits`.
  - **Compute-apps query:** `--query-compute-apps=pid,process_name,used_memory --format=csv,noheader,nounits`.

  Both are the forms already exercised in the Astra `/001` host receipt. `q0.py host-precheck` validates them against this host: one line, the leased UUID, the name, and compute_cap 12.0. They run pre, every 60 s and post.

  Per-process VRAM is `[N/A]` under WDDM and is unsupported telemetry. Device `memory.used` includes the desktop and other processes; it is a confounder, never a reason to stop another process.
- **Host preconditions (Q0R-07),** read-only via `host-precheck`:
  - System32 `msvcp140.dll`, `vcruntime140.dll` and `vcruntime140_1.dll`: presence, size, SHA-256 and file version;
  - `LongPathsEnabled`. If it is not 1, every harness-known path must stay below 240 characters. The venv's longest installed path is checked after installation (`hostcheck.max_path_under`).

  DLL presence does not prove that torch's DLLs resolve; the later import gate does.

## 8. Remaining gates and open items

- **torchvision wheel digest: bound, local-sha256-TOFU.** Neither official index publishes a wheel SHA-256. The lock binds exactly one published independent receipt: `ef72849519c83a71e59e80c311b48719252d0cd6:docs/reviews/WP-0005/eld-q0-reviewer/pre-execution/response-2026-11-15/torchvision-acquisition-receipt.json` (blob `877d8220…`, 3,103 B). The bound values are:
  - local SHA-256 `5ae0ff50fcb43a189250a5fdb36a7dc780ea5caff469653cab1e3f32ed5d385c` and 9,091,113 B;
  - METADATA digest `f8e91ee9…`;
  - label **`local-sha256-TOFU; publisher wheel digest unavailable`**. It is never labelled publisher-verified.

  `validate_lock` re-reads that blob, checks its SHA-1 and size, and requires all of the following:
  - the label, `pass` and every recorded check true;
  - the exact URL, with no redirects and HTTP 200;
  - size, local SHA-256 and METADATA digest equal to the record;
  - name/version and `torch (==2.13.0)`.

  The receipt's `etag_matches_recorded_head: false` is the reviewer-disclosed header-case reporting defect (N-03). The ETag strings are identical, so the harness ignores that field. No cookies or unneeded headers are copied into the lock.

  Installation still requires the install release record to list `torchvision-local-sha256-TOFU` in `accepted_provenance_exceptions`. The coordinator's narrow acceptance for bounded local Q0 is recorded in its resume kickoff, not in the lock. Without a release, `execute`, `write-requirements`, `verify-wheelhouse` and `preflight-cpu` refuse with `EXECUTION_NOT_RELEASED`. With a release that omits the exception, they refuse with `ACQUISITION_PROVENANCE_PENDING`.

  TOFU limits: the hash proves only that later copies equal the bytes the reviewer received over TLS from the official origin (a Cloudflare edge). The METADATA match authenticates only that member.
- `torch.version.cuda == "13.0"` is inferred from `+cu130` and must be observed in the runtime precheck.
- Transformers 4.52.1 local-directory loading has not been executed. The reviewer's phase A read of upstream `dynamic_module_utils.py` is source evidence only: `check_imports` runs only on the entry module locally, while the remote ID would trip unconditional `import triton`. Module-cache identity is checked after load, and import failure is an honest blocker.
- The exact `pypdfium2.version.PDFIUM_INFO` string form is verified only by `preflight-cpu`, which fails closed if `159.0.8149.0` is absent.
- Astra `/007` closed the imports of `configuration_deepseek_v2.py`, `conversation.py` and `packing_patch.py` (Transformers, stdlib and torch only). The tokenizer is on the fast `tokenizer.json` path. All of this is static, and the actual tokenizer load is still unexecuted.
