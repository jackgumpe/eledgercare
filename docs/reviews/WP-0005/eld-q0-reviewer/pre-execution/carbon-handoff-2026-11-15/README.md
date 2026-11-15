# WP-0005 /003: Carbon Handoff Independent Pre-Execution Harness Evidence (`eld-q0-reviewer`)

## Attribution and Session Disclosure

- **Stable review role:** `eld-q0-reviewer` (user-authorized provider/model handoff per `docs/kickoffs/WP-0005-eld-q0-reviewer-carbon.md` at `ce204bc5cba1d813ba645657bb82a48af9ca0ca6`).
- **Active Carbon session:** Fresh conversation **`0815536f-045a-4112-8a89-ebf0e0cc782f`**, model **Gemini 4 Carbon (High)** (`gemini-4-carbon-high`, explicit `high` effort via `agy.exe`, PID `21144`, provider init permission mode `always-proceed` despite launcher selection `accept-edits`, no bypass flags or global settings changes). Distinct from availability probe `0dea04b7-ac6c-451b-9428-691b76c93089` and uninvolved in harness, preflight, corpus, or backlog authorship.
- **Predecessor Opus attribution (preserved unchanged):** Stopped Claude Opus 5.5 (High) conversation **`e6147c9e-0303-475f-99ff-93ee38a681e4`** authored Phase A review notes (`b75011da408fed5d2cc4f9025416ead6c5632ceb`) and the Astra `/007` response verification + single-wheel `torchvision` provenance acquisition checkpoint (`ef72849519c83a71e59e80c311b48719252d0cd6`, receipt blob `877d822099e7b3628d36f6b4a709d76ecad6de00`). None of those earlier Opus executions or network acquisitions were re-run or re-attributed here.
- **Scope boundary:** Bounded pre-execution CPU, static-source, Git-object, and read-only host readiness verification only. **Not** model or runtime qualification.

## Exact Revision and Digest Pins

| Artifact / Revision | Exact Identity | Verified Fact |
| --- | --- | --- |
| Owned worktree / branch | `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-reviewer-carbon` / `review/wp-0005-q0-carbon` | Clean before and after check execution |
| Handoff / execution base | `2e41d3a91b8f08b53d643b20a1fb038b5aec1500` | Normal merge of `ef72849519c83a71e59e80c311b48719252d0cd6` + `2a52ea58fae2badcb4e9ef47d1cb416c006edca4` |
| Original packet / report base | `df9a2b50894f01987d779d7f9ae805794503ce6f` | Ancestor verified |
| Frozen reviewer check revision | `17107f369a96d0f40d99c83f21ca72d902d3f035` | Helper frozen before decisive run `17107f36/` |
| Harness candidate (`eld-q0-harness`) | `84cef5ef30685ffee46281fefc5fd1356dbc1876` | Tree `qualification/q0/harness` = `b7afcd512d508e43b874cf7b9857b7493359a879`; parent `912f4f4f991977cca83bb40928cff45ac525efaa` |
| Harness final author evidence | `0331efd71ef17e5485adac5a53d864c6d96e8f4a` | 15 evidence-only files under `qualification/q0/harness/evidence/002-final/**`; 11/11 raw outputs match `summary.json` |
| Harness canonical `/002` report | `2a52ea58fae2badcb4e9ef47d1cb416c006edca4` | Adds `docs/agent-reports/eld-q0-harness/WP-0005/002_2026-11-15_implementation_eld-q0-harness.md` |
| Astra `/001` deliverable / report | `b8112ca27b8f7d5bcba7171ab0f1bd5907fae1f6` / `2c32dde602b274251043bb216752f5d7fe9593be` | Initial preflight baseline |
| Astra `/007` candidate / evidence / report | `d666c4163b8b6bdf5f6c69b455c30f3c377cbdc5` / `6cb6a258b9652b7becd3fca9c7cf2f04866c3ec3` / `951d408aabf7bdad3602c0e7698869e2e2457aed` | Verified by Opus at `ef72849519c83a71e59e80c311b48719252d0cd6` |
| `qualification/q0/harness/protocol.json` | SHA-256 `dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309` | Identical to candidate `84cef5ef…` |
| `qualification/q0/harness/locks/dependency-lock.json` | SHA-256 `d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e` | Identical to candidate `84cef5ef…`; non-circular (`eldq0-lock/2`) |
| `qualification/q0/harness/manifests/model-files.json` | SHA-256 `085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8` | Identical to candidate `84cef5ef…` (`eldq0-model-files/2`, 18 runtime + 1 notice) |
| Bound `metadata-lock.json` / `cuda-metadata.json` | Git blobs `ec8c650ed5fbeb0a754e4daee53aad53753a57a3` (123,592 B) / `bca91aaa8e2d51eabb8e9d7d85c7f3602c4e8b8b` (57,150 B) | Verified byte-for-byte via `git cat-file blob` |
| Bound `torchvision-acquisition-receipt.json` | Git blob `877d822099e7b3628d36f6b4a709d76ecad6de00` (3,103 B) | Local SHA-256 `5ae0ff50fcb43a189250a5fdb36a7dc780ea5caff469653cab1e3f32ed5d385c` (9,091,113 B) |

## Finding Closure Matrix (`Q0R-01..09` and `N-01..04`)

| ID | Pre-execution Requirement | Closure Evidence and Residual Boundary | Status |
| --- | --- | --- | --- |
| `Q0R-01`..`Q0R-03` | Complete 32-wheel metadata graph, CUDA PEP 658 metadata, 10-module remote-code + tokenizer static closure | Closed at metadata/static-source level by Astra `/007` (`d666c416…`) and independently verified by Opus (`ef728495…`, 25/25 checks + both verifiers). Carbon additionally ran `q0harness.sourcecheck.analyze_model_sources` across all 10 assembled `.py` blobs (`17107f36/independent-assertions.json`). | Closed (pre-exec) |
| `Q0R-04` / `N-01` / `N-02` / `N-03` | Exact every-wheel SHA-256 + every-wheel ZIP `METADATA` graph check; truthful `torchvision` TOFU receipt pin; non-circular release binding | `locks/dependency-lock.json` (`eldq0-lock/2`) pins 31 publisher SHA-256s + 1 `torchvision==0.28.0+cu130` `local-sha256-TOFU` record bound to `ef728495…` blob `877d8220…`, rejects any embedded `/003` or `accepted_review` field, copies no CDN cookies (`__cf_bm` absent), and ignores `etag_matches_recorded_head=false` (N-03). `verify_wheelhouse` enforces exact 32-wheel set, sizes, SHA-256s, top-level `*.dist-info/METADATA` `Name`/`Version`, normalized `Requires-Dist` multiset against all 850 graph edges, and PEP 658 `METADATA` SHA-256 for `torch` + `torchvision`. `release.py` (`eldq0-release/2`) binds accepted review + commit + lock/protocol SHA-256 + `accepted_provenance_exceptions`. Real wheel payloads remain unacquired. | Closed (pre-exec) |
| `Q0R-05` | Owned storage root, child/stage env allowlist, redirected caches/temp, initial & runtime free-space floors | `environment.py` builds allowlisted environments (`build_child_env`, `build_stage_env`) redirecting `TEMP`/`TMP`/`TMPDIR`, `USERPROFILE`/`HOME`, `HF_HOME`, `HF_MODULES_CACHE`, `TORCH_HOME`, `TRITON_CACHE_DIR`, `TORCHINDUCTOR_CACHE_DIR`, `CUDA_CACHE_PATH`, `PIP_CACHE_DIR`, `UV_CACHE_DIR`, `XDG_CACHE_HOME` inside `C:\Users\jackg\eLedgerCare-Q0\WP-0005`, setting `HF_HUB_OFFLINE=1`/`TRANSFORMERS_OFFLINE=1` (and `PIP_NO_INDEX=1`), and stripping credentials and model switches. Enforces 58 GiB initial and 20 GiB runtime C: floors (`hostcheck.py`, `supervisor.py`). Pagefile/OS/driver growth outside root remains disclosed as unbounded by task dir. | Closed (pre-exec) |
| `Q0R-06` / `N-04` | Valid Python identifier model leaf, no trailing separator, offline local loader, dynamic module cache digest audit | `protocol.json` freezes `C:\Users\jackg\eLedgerCare-Q0\WP-0005\models\Unlimited_OCR_2_04809669` (`isidentifier() == True`). `modelfiles.normalize_model_dir` rejects trailing separators, relative paths, links/reparse points, and non-identifier basenames; `backend_torch.py` enforces `local_files_only=True` and offline env vars pre-import; `verify_module_cache` verifies loaded `transformers_modules.*` files live under run-local `HF_MODULES_CACHE` and match verified model `.py` digests. | Closed (pre-exec) |
| `Q0R-07` | Separate functioning `nvidia-smi` GPU and compute-app queries, honest WDDM `[N/A]` per-process VRAM handling | `hostcheck.py` runs two separate `--id=GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d` queries (`--query-gpu=...` and `--query-compute-apps=pid,process_name,used_memory`), both exit 0 on this host (`17107f36/08-host-precheck-initial.txt`). `[N/A]` per-process VRAM under WDDM is recorded truthfully (`per_process_vram_supported=False`), never fabricated or substituted for PyTorch CUDA allocator stats. | Closed (pre-exec) |
| `Q0R-08` | Non-circular coordinator release gate for install (`/004` prep) and GPU execution (`/004`) | `q0.py` fails closed (`EXECUTION_NOT_RELEASED`, exit 2) for `execute` (`--owner author` and `--owner reviewer`), `write-requirements`, and `verify-wheelhouse` without a matching `eldq0-release/2` JSON file (`17107f36/09..12-*.txt`). | Closed (pre-exec) |
| `Q0R-09` | Transport-independent 18-object runtime manifest + separate `README.md` license notice | `manifests/model-files.json` (`eldq0-model-files/2`) pins 16 `git_blob_sha1` + 2 `lfs_sha256` runtime objects (ignoring `xetHash`/pointer OIDs) and separates `README.md` (`c79e1e3362c8fd2f9193d79c1db80fbf7f041c45`, 14,107 B) into `notices` (`notices\Unlimited_OCR_2_04809669\README.md`), rejecting `README.md` inside the runtime model directory while tolerating non-Python `.cache/huggingface/**` metadata. | Closed (pre-exec) |

## Verification Layer Separation (Actual vs Synthetic vs Static vs Unexecuted)

1. **Independently executed by Carbon on `17107f369a96d0f40d99c83f21ca72d902d3f035` (`17107f36/`):**
   - Full `unittest` discovery (`75` tests run in `29.668s`: `74` passed, `1` skipped `test_links_rejected` due to Windows symlink privilege `[WinError 1314]`).
   - All 11 CLI verification and fail-closed commands (`verify-snapshots`, `derive-rasters --check`, `build-model-manifest --check`, `check-protocol`, `lock-check`, `status`, `host-precheck --stage initial`, and `execute --owner author`, `execute --owner reviewer`, `write-requirements`, `verify-wheelhouse` refusals).
   - Direct programmatic assertions (`independent-assertions.json`): 10-module AST safety/blob check across all 10 retained model `.py` files, notice separation, identifier/separator enforcement, non-circular/cookie-free lock & TOFU release gate, holdout/expected path refusal (`F03`/`F05`/`F06`/`F08`, `expected/`, `sources/`), and allowlisted child/stage environment scrubbing.
   - Read-only host snapshot (`08-host-precheck-initial.txt`): Python `3.12.10` AMD64, C: free `68,527,251,456` B (`63.82 GiB`, above `58 GiB` floor), MSVC `14.51.36247.0` DLLs present, `LongPathsEnabled=0` (known harness paths max `162` chars), RTX 5070 Ti `GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d` compute cap `12.0` / driver `621.01`, `C:\Users\jackg\eLedgerCare-Q0` absent before and after.
2. **Predecessor Opus executions attributed unchanged (`b75011da…`, `ef728495…`):**
   - Astra `/007` preflight verifiers + 25 independent checks (`docs/reviews/WP-0005/eld-q0-reviewer/pre-execution/response-2026-11-15/review-checks-result.json`).
   - Single-wheel `torchvision-0.28.0+cu130-cp312-cp312-win_amd64.whl` retrieval into the old Opus worktree's `.scratch/torchvision-provenance/` (absent in this Carbon worktree) and receipt `torchvision-acquisition-receipt.json` (`877d8220…`).
3. **Synthetic test doubles (harness mechanics only, NOT model qualification):**
   - `tests/fakemodel/` (`modeling_unlimitedocr.py`, `modeling_deepseekv2.py`, `dash_attention.py`), `FakeBackend`, `FakePdfium`, and synthetic wheel ZIPs test `sys.monitoring` probes, `SafetyTripwire(BaseException)` firing before bare `except:` at `modeling_unlimitedocr.py:196`, cache progression, timeout/stall child kill, score-key bans, and ZIP `METADATA` validation.
4. **Static source cross-checks of `backend_torch.py` & `telemetry.py` against pinned `04809669…` blobs:**
   - Verified `UnlimitedOCRForCausalLM.infer` (L1038) and `_uocr_generate` (L1125) `@torch.no_grad()` wrappers are unwrapped via `inspect.unwrap` in `telemetry.resolve_targets`.
   - Verified `UnlimitedOCRModel.forward` (L647) delegates to `DeepseekV2Model.forward` (L3889), returning `BaseModelOutputWithPast` with `DynamicCache` (both `.layers` and legacy `.key_cache`/`.value_cache` handled in `telemetry.inspect_cache_object`).
   - Verified all 12 layers (`sparse_attention_freq=[1]*12`, `training_stage="dash"`) instantiate `DeepseekV2Indexer` (`_sparse_base_impl.py:1385`) and `DashAttention` (`modeling_deepseekv2.py:78`), matching all 7 attention code-object hooks in `telemetry.resolve_targets`.
   - Verified `session.py:226` accepts `TorchBackend.platform_facts()["device_uuid"]` with or without the `GPU-` prefix (`gpu["uuid"]` vs `gpu["uuid"].removeprefix("GPU-")`).
5. **Unexecuted later runtime gates (held pending coordinator release):**
   - Full 32-wheel download + real every-wheel `METADATA` check, venv creation/install, `pip check`, installed venv path lengths under `LongPathsEnabled=0`, model snapshot download (`~6.30 GiB`) + notice placement, `pypdfium2==5.15.2` F01/F07 rendering against predicted raster digests, `torch`/`transformers`/remote-code import (`backend_torch.py` has zero runtime execution yet), `sm_120` CUDA allocation, and GPU inference (`/004`, `/005`).

## Author `/002` Report Errata Reconciled (Immutable Report Preserved)

- **Diff count (`002_2026-11-15_implementation_eld-q0-harness.md` L91):** States `14` evidence-only additions for `84cef5ef → 0331efd7`; actual `git diff --name-status` count is **`15`** (`11` command outputs + `summary.json` + `.gitattributes` + `README.md` + `run_checks.py`), making `df9a2b50 → 0331efd7` **`88`** harness additions (`41` source/docs/config/tests + `18` `/002-initial` + `14` `/002-checkpoint2` + `15` `/002-final`) plus `1` `/002` report commit (`2a52ea58…`).
- **Unittest phrasing (`002_2026-11-15_implementation_eld-q0-harness.md` L40, L162):** Phrases `75 tests OK, 1 skipped`; Python `unittest` ran **`75` total tests: `74` passed and `1` skipped** (`OK (skipped=1)`).

## Decisive Run `17107f36/` File Inventory

Outputs in `17107f36/` were captured on clean HEAD `17107f369a96d0f40d99c83f21ca72d902d3f035` (`2026-11-15T17:36:04.277693Z` to `17:36:38.120199Z`) and stored with `* -text` so committed Git blobs match raw byte SHA-256 digests:

| File | Exit | Bytes | Raw SHA-256 |
| --- | --- | --- | --- |
| `17107f36/01-unittest.txt` | 0 | 9,386 | `1498e15aaf72dd37d52221b0dbbca3745244f01f9b4598c295b6bc78f47dbeb7` |
| `17107f36/02-verify-snapshots.txt` | 0 | 7,100 | `ab0d1999b41619f51cb0a3204c96864275663ae6184f128bfa3842804ada3d6b` |
| `17107f36/03-derive-rasters-check.txt` | 0 | 911 | `3830bbd14720b6c09320d263ccfe3ac9888040e09865e4d0eca4df3198d94500` |
| `17107f36/04-model-manifest-check.txt` | 0 | 198 | `b6dd29721724bf2a57940ef535ce23069fca3648060ee46af18ba3b38741837e` |
| `17107f36/05-check-protocol.txt` | 0 | 198 | `3698b7f74d5aa896221dc05930aaa6421f0b4b19c36ca600cf1f9d329bd5379e` |
| `17107f36/06-lock-check.txt` | 0 | 3,708 | `e1769d403a348e107d262ed12140eb8b6907233348a9b000a40aad590c51ca93` |
| `17107f36/07-status.txt` | 0 | 703 | `545e490ed4e84b7c2f4d5bf5cb8ff1c1691c1dcc96c2b6b5aba946753fa0b1ce` |
| `17107f36/08-host-precheck-initial.txt` | 0 | 5,424 | `e9092934c9bfb5e81767048cbc2b4c95e62475da247cddba4619f8bcb1505da8` |
| `17107f36/09-execute-author-refused.txt` | 2 (expected) | 566 | `f6c35002dab1e3f784df0c918653c6a6d1a88af2f7f159e318690e598e727050` |
| `17107f36/10-execute-reviewer-refused.txt` | 2 (expected) | 566 | `f6c35002dab1e3f784df0c918653c6a6d1a88af2f7f159e318690e598e727050` |
| `17107f36/11-write-requirements-refused.txt` | 2 (expected) | 566 | `7237b13dba7996e3ed2969de44da309a02033d31ef0c77b668ec7b6f5d2deeb4` |
| `17107f36/12-verify-wheelhouse-refused.txt` | 2 (expected) | 566 | `7237b13dba7996e3ed2969de44da309a02033d31ef0c77b668ec7b6f5d2deeb4` |
| `17107f36/independent-assertions.json` | — | 3,921 | `710b53d0d0ba3d3c36cb291bbe1426a0512447998b937bd6533fe42d70ef7d56` |
| `17107f36/summary.json` | — | 10,331 | `7bb595f46ceafb5e9c9d35e66141c4ea12a0564cdce4ad1fd34a09f1e28d6763` |
