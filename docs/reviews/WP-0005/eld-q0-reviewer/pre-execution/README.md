# WP-0005 /003 phase A: interim pre-execution evidence checkpoint (eld-q0-reviewer)

**Status: INTERIM CHECKPOINT, not the canonical /003 report and not an acceptance.** The final ACCEPTED / CHANGES REQUESTED disposition and the canonical report `docs/agent-reports/eld-q0-reviewer/WP-0005/003_2026-11-15_review_eld-q0-reviewer.md` remain HELD until the coordinator supplies frozen /002 candidate, evidence and report pins. No harness source was inspected.

## Identity, scope and disclosure

| Item | Value |
| --- | --- |
| Reviewer | eld-q0-reviewer; reserved session `e6147c9e-0303-475f-99ff-93ee38a681e4` (assigned by coordinator; I can't confirm the session UUID myself) |
| Model | Runtime-reported `claude-opus-5-5`, high effort, as dispatched. Coordinator verified availability separately; this reviewer did not inspect credentials |
| Upstream participation | None. I did not write any part of the WP-0005 /001 preflight, the /002 harness, the WP-0004 Q0 protocol or the corpus |
| Repository / branch / worktree | `jackgumpe/eledgercare` (private) / `review/wp-0005-q0` / `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-reviewer` |
| Full base | `df9a2b50894f01987d779d7f9ae805794503ce6f` (clean worktree at start) |
| Authoritative inputs read | Main checkout `a791d6c579d0e90ca867f51de52d2fe50accf82c` (equals `origin/coordination/bootstrap` after fetch): AGENTS.md, INDEX.md (WP-0005 rows), CURRENT.md, `docs/kickoffs/WP-0005-eld-q0-reviewer.md` |
| Reviewed candidate | Astra `95ce0a8df728ae2c41aaf9e09d1b97c7d990fe36`; publication `2c32dde602b274251043bb216752f5d7fe9593be` (= `origin/research/wp-0005-runtime-preflight`) |
| Review merge | `3e1837a61c9a33cce538976ac83f75e325a78021`, a normal `--no-ff` merge with parents `df9a2b5…` and `2c32dde…`. `git diff 2c32dde… HEAD` is empty, so all author bytes are preserved |
| Allowed outputs used | This file, plus ignored `.scratch/wp0005-q0/**` (two partial-clone bare repos and two extracted upstream text files) |

Scope: the base→candidate diff adds exactly 10 files under `qualification/q0/preflight/`, and candidate→publication adds exactly 1 file (the /001 report). The preflight subtree is `54c7e44130f0ca6e56a7074503e78d6a72d031de` at the candidate, the publication and my merge.

Candidate file identities (`git ls-tree -l 95ce0a8…`, Git blob / bytes): README.md `2337463e…` 15,999; collect-metadata.py `754ac6a0…` 4,011; collect-source-audit.py `8d3b37ba…` 2,269; cuda-wheel-metadata.json `216f19df…` 49,848; host-receipt.json `592f19dc…` 5,644; model-files-proposal.json `64ad111f…` 3,728; package-proposal-metadata.json `adfe0a71…` 98,305; proposed-artifacts.json `b2952c2c…` 3,193; source-audit.json `3fd7c0d5…` 21,356; verify-preflight.py `87bd3825…` 2,497. Report `8fc816f8…` 12,453.

## Permission denials (exact; no bypass attempted)

The session has no approval surface, so the following were auto-denied. I did not retry any of them or work around them with an equivalent tool:

1. PowerShell commands that use `$var` or `$LASTEXITCODE` expansion: "Command contains expandable strings with embedded expressions". I re-ran these as plain git commands, which have no expansion.
2. `tar -x` extraction of `git archive` into `.scratch`. I replaced it with a tree-hash identity check: the working tree equals the candidate subtree.
3. **All Python execution**, including the author's offline `verify-preflight.py` with `python.exe -I -B`. **I did NOT reproduce the author's verifier.** Its assertions were re-derived by hand where possible (see below).
4. `gh api` (blob lookup), `WebFetch`, `WebSearch`: no official web page could be re-read. I independently checked upstream *Git objects* using `git ls-remote` and blob-less partial fetches, which were permitted.
5. `Get-CimInstance` (C: free space), `sha256sum`, and Glob on `C:\Users\jackg\eLedgerCare-Q0`. As a result, **I have not measured current free space, the absence of the storage root, or SHA-256 of any file.**

## Executed checks and results

| # | Command / method | Result |
| --- | --- | --- |
| C1 | `git status`, `rev-parse`, `worktree list`, `fetch origin`, `rev-parse origin/...` | Clean owned branch at base; publication on origin; main checkout = origin integration `a791d6c…` |
| C2 | `git diff --name-status` base→candidate, candidate→publication; `merge-base --is-ancestor` | 10 additions plus 1 report-only addition; base is an ancestor |
| C3 | `git merge --no-ff 2c32dde…` then `git diff 2c32dde… HEAD` | Merge `3e1837a…`, empty diff |
| C4 | `git rev-parse <rev>:qualification/q0/preflight` ×3; `git ls-files --eol` | Identical tree `54c7e441…`; all files i/lf w/lf |
| C5 | `git hash-object` of 9 retained `research/astra/sources/hf-*.txt` | All 9 equal the model-files-proposal OIDs: modeling_unlimitedocr `2a717b55`, modeling_deepseekv2 `6cf69a31`, dash_attention `891d2ff7`, deepencoder `6b10ea1b`, sparse_gather_triton `6621872e`, sparse_gather_e2e_triton `021575ce`, _sparse_base_impl `32916376`, config.json `a1ea89c4`, generation_config.json `6f7f9313` |
| C6 | Read `hf-tree.json` (Git blob `23b993ec…` identical at `1eb6f4af…` and HEAD; 4,604 bytes, matching source-manifest; origin is the pinned-revision recursive tree API) | All 18 proposed objects match the tree's OID and size. Excluded: .gitattributes, README.md, PDF, 4 assets, sglang wheel. Hand sum: 6,688,305,576 weight + 10,889,605 other = **6,699,195,181** ✓ |
| C7 | `git ls-remote` tags | transformers v4.52.1^{} = `945727948c11…` ✓; pytorch v2.13.0 = `cf30153c4c13…` ✓; vision v0.28.0 = `8fb87713a249…` (recorded for future source checks) |
| C8 | Blob-less depth-1 fetch of the transformers pin into `.scratch`; `ls-tree -l` | All 6 recorded `git_blob` and `size` values in source-audit.json match upstream exactly (dynamic_module_utils `eec01749` 33,911; attn_mask_utils `dfdd976f` 21,221; pytorch_utils `ca60a05a` 14,943; modeling_llama `a25f05ea` 40,484; cache_utils `d24edd39` 119,524; import_utils `0b3f7e69` 96,241) |
| C9 | Same for the pytorch pin; `cat-file` RELEASE.md | Blob `feef468c` 34,135 ✓. Line 77: CUDA 13.0.2 Linux-x86/Windows builds include Blackwell (10.0, 12.0+PTX) with "+PTX available on linux builds only"; line 104: 2.13 released 8 Jul 2026 (consistent with the wheel `data-upload-time` 2026-07-08); line 480: Windows 10+ |
| C10 | Read upstream `dynamic_module_utils.py` (blob `eec01749`) lines 143–230, 355–444 | Loader reasoning confirmed; see "Loader" below |
| C11 | Static Grep of import graph in Git-blob-verified model sources plus config.json | See findings Q0R-03/04 |
| C12 | Hand arithmetic | Primary wheels 38,394,007 (13 PyPI) + 1,915,519,202 + 9,091,113 = **1,963,004,322** ✓. Budget 7+7+3+10+8+1+2 = 38 GiB ✓. 69,064,572,928 B = 64.32 GiB; minus 38 = 26.32 ✓. 2550×3301×3×4 = 101,010,600 ✓ |
| C13 | Cross-check renderer pins against admitted `evaluation/manifests/tooling-provenance.json` | pypdfium2 5.15.2 (4,187,589 B, `74d1bace…`) and Pillow 13.0.0 (7,272,166 B, `ff3fe9eb…`) are identical to the proposal ✓ |
| C14 | Reviewed requires_dist and markers in package/CUDA metadata | Required-dependency gap list in README §Runtime matches the recorded metadata for the 15 primaries (except as noted in Q0R-02/03) |

**Not run:** the author's verifier; any Python; network re-retrieval of indexes, PEP 658 bodies, HEAD headers or PyPI JSON; SHA-256 recomputation of `metadata_text`; host free-space, RAM or GPU observation; installs; downloads of wheels or model payloads; imports; CUDA. Because the metadata documents were not re-fetched, the torch/torchvision metadata-digest matches and the absence of a torchvision wheel digest are **author-recorded only, not independently reproduced**.

Disclosure: one repository-wide Grep for renderer version strings returned the single metadata lines `rasterizer` and `pillow_version` from three `evaluation/synthetic/expected/*.json` files. I did not open those files and saw no expected-answer content. No other corpus or expected-value file was read.

## Loader: local vs remote optional-Triton reasoning (confirmed from upstream source)

- `get_imports` (L159–186) skips `ast.Try` bodies and `if is_*_available()` blocks. It collects top-level and function-level absolute imports. `check_imports` (L209–230) **actually imports** each module. It collects only "No module named" failures, re-raises any other ImportError (L219–222), and returns `get_relative_imports`. That function is regex-based (L103/105), so it includes relative imports inside `try` blocks.
- Local directory (L360–362, L399–414): `submodule = basename(path)`. `check_imports` runs **only on the entrypoint**, and its direct relative files are copied without further checks.
- Remote ID (L415–444): for each relative module it recurses into `get_cached_module_file`, which runs `check_imports` on that file. `sparse_gather_triton.py` L23–24 and `sparse_gather_e2e_triton.py` L28–29 import `triton` at top level and outside any `try`, so the remote path raises the L225 ImportError. Astra's prediction is correct for the pinned code. It is still predicted, not observed.
- The entrypoint `modeling_unlimitedocr.py` names all 9 sibling modules directly (L1, 5, 6, 13, 19, 27, 31, 35, 53, 56), each in the regex-detectable `from .x import` form. That makes the local copy set complete. ✓

## Findings (interim; returned to authors, not repaired)

| ID | Severity | Verdict | Location | Finding / requested disposition |
| --- | --- | --- | --- | --- |
| Q0R-01 | Medium (provenance) | CONFIRMED | `package-proposal-metadata.json`; `collect-metadata.py` L34–48; report Verification row 2 | The committed JSON was **not produced by the committed helper**. The helper's `pins` order puts pillow 5th and writes `datetime.now(timezone.utc).isoformat()` (`+00:00`). The JSON puts pillow 13th, records 12 `retrieved_utc` values with a `-05:00` offset (e.g. L407, L596, L843) and records pillow as `2026-11-15T05:13:21.2364463Z` (7-digit, non-Python format, L906). Within the same run, the same `now()` wrote `cuda-wheel-metadata.json` as `05:10:33/34+00:00`, only about 1 s before the first PyPI record's `00:10:35-05:00`, and the committed script cannot emit both formats. So the stated producer is inaccurate, and the pillow record has an undocumented separate retrieval. Content risk is low because the pillow and pypdfium2 digests equal the admitted WP-0004 provenance (C13). Requested: the author documents the actual producer, or the dependency stage regenerates with a committed helper. `verify-preflight.py` cannot detect this |
| Q0R-02 | Medium (closure) | PLAUSIBLE | `package-proposal-metadata.json` L417; `host-receipt.json` python_probe `AMD64` | hf-xet marker: `platform_machine == "x86_64" or == "amd64" or "arm64" or "aarch64"`. The host interpreter reports `AMD64`, and PEP 508 non-version comparisons are case-sensitive strings, so hf-xet is likely **not** selected. In that case model shards (which carry xetHash) download over plain HTTP. Requested: the dependency stage evaluates the marker under the selected venv interpreter and records the result. Model verification must not depend on transport: SHA-256 of both shards vs the LFS oid, and the Git-blob SHA-1 (`git hash-object`) of all 16 non-LFS files vs the tree OIDs |
| Q0R-03 | Medium (source closure) | CONFIRMED gap | `model-files-proposal.json`; `research/astra/sources/` | Of the 10 Python sources, `configuration_deepseek_v2.py` (10,720 B), `conversation.py` (9,253 B) and `packing_patch.py` (8,110 B) are not retained. The same holds for `tokenizer_config.json` and `special_tokens_map.json`. Their third-party imports and the tokenizer class (which may need sentencepiece, protobuf, tiktoken or a remote tokenizer `auto_map`) are unverified, so the dependency gap list cannot yet be called complete. Requested: before freezing the lock, fetch only these small files at the pinned revision, verify their Git-blob OIDs, statically list imports and `tokenizer_class`/`auto_map`, then close the lock. No weights are needed for this |
| Q0R-04 | Medium (runtime path / telemetry) | CONFIRMED (source); runtime effect unmeasured | config.json L117–196; `_sparse_base_impl` L177–187, L1747–1811, L3322–3343; `dash_attention` L914, L1207–1211, L1342–1346 | Without Triton, the "native fallback" is specific. `use_sparse_attention: true` and `dash_use_triton: true` mean every CUDA sparse layer tries a Triton import and falls back. The base path prints `[SparseAttn] triton gather path failed …` once (layer 2), then uses an **eager matmul + block-mask fallback that materialises [B,H,Sq,Sk]** (the source comment L1741 warns OOM at long context). The DASH Triton fallback is **silent** (returns None). Flex attention is disabled (`use_flex_attention: false`), although `torch.compile(flex_attention)` is created inside a `try` at import. Requested for harness review: capture stdout/stderr verbatim; assert and record `importlib.util.find_spec("triton") is None`; label results as "unmodified model on non-Triton fallback path"; never infer the DASH path from log absence; measure prefill VRAM for F07 rather than infer it |
| Q0R-05 | Low (storage containment) | PLAUSIBLE | README §Fresh host | The budget has no line for C: consumption outside the task root: pagefile growth during CPU-side load of about 6.7 GB bf16 weights (plus any fp32 transient); the NVIDIA ComputeCache under %APPDATA% (pin `CUDA_CACHE_PATH` under the root); `PIP_CACHE_DIR`/`UV_CACHE_DIR`; and `TORCHINDUCTOR_CACHE_DIR` (covered only if TEMP is redirected first). `huggingface_hub` `local_dir` downloads also write `.cache/huggingface/` metadata into the model directory, which the 18-object verification must explicitly whitelist. Requested: add these env pins and measure C: free before and after each stage |
| Q0R-06 | Low (loader hygiene) | CONFIRMED (source) | upstream dynamic_module_utils L360–364, L399 | The local branch depends on `os.path.isdir(path)` and `basename(path)`. A trailing separator yields an empty submodule, and a missing directory is silently treated as a repo ID. Requested: pass a normalised absolute path without a trailing separator; assert `isdir` and the exact 18-file set first; set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` before any HF import, so a misconfiguration fails closed rather than reaching the remote branch. Classify DLL/ABI ImportErrors re-raised by `check_imports` (L221–222) as platform failures |
| Q0R-07 | Low (host preconditions) | PLAUSIBLE | `host-receipt.json` | The MSVC runtime (msvcp140/vcruntime140_1) required by Windows torch DLLs and the `LongPathsEnabled` setting are not recorded. Visual Studio 18 appears in the GPU-process list, which suggests the runtime is present but doesn't verify it. Requested: record both read-only before install |
| Q0R-08 | Info (index confusion) | CONFIRMED (metadata) | cuda-wheel-metadata torchvision `Requires-Dist: torch (==2.13.0)` | PEP 440 `==2.13.0` matches `2.13.0+cu130`, but it also matches the PyPI CPU `torch 2.13.0`. Install only with `--no-index --find-links <wheelhouse> --require-hashes` and the exact `torch==2.13.0+cu130`. This reinforces Astra stage 2 |
| Q0R-09 | Info (notices) | CONFIRMED | model-files-proposal.json | The 18-object set leaves out `README.md` (14,107 B, OID `c79e1e33…`), which is the model card carrying the repository license declaration. Requested: also retain it, OID-verified, as a notice artefact. It is not needed for loading |

Confirmed-correct claims: the candidate scope; all 18 model identities and sizes; the 7 source-audit blob/size identities; the tag→commit pins; the RELEASE.md Windows 13.0.2 / Blackwell 12.0 row (a release-process statement, not binary proof; `torch.cuda.get_arch_list()` is still required); Python tags/bounds (torch ≥3.10 with a cp312 classifier; torchvision ≥3.10,!=3.14.1; Pillow ≥3.11; numpy ≥3.10); renderer pins; storage arithmetic; the loader local/remote distinction; and that no Triton, flash-attn or xformers is needed for import (all are guarded).

**Not independently verified:** the PyTorch previous-versions pairing page, the NVIDIA capability table, and the 580.88 Windows driver minimum from the PyTorch 2.12 blog (web access denied). Driver 621.01 was not re-observed.

## Torchvision wheel provenance assessment (no publisher wheel digest)

Recorded facts: the index entry has no `#sha256=` fragment; HEAD gave Content-Length 9,091,113 and ETag `"1b523c73…-2"`. The `-N` suffix denotes a multipart-upload ETag, which is not a whole-file content digest and not SHA-256. The PEP 658 digest `f8e91ee9…` authenticates **only the METADATA document**. Neither may be recorded as a wheel hash. The torch fragment hash is served by the same origin over TLS and is not a signed attestation. Its value is that it is declared before download.

Recommended acceptable procedure, for coordinator decision at the dependency stage:

1. Get the URL only from the official `download.pytorch.org/whl/cu130/torchvision/` index entry, and download over HTTPS from `download-r2.pytorch.org` into an empty task-owned wheelhouse.
2. Record the URL, final URL, TLS host, retrieval UTC, Content-Length (must equal 9,091,113), ETag, Last-Modified, and the **locally computed SHA-256 and size**.
3. Without importing anything, read `torchvision-0.28.0+cu130.dist-info/METADATA` from the zip. Its SHA-256 must equal `f8e91ee9…` and its `Requires-Dist torch==2.13.0` must be present. This is a consistency check only.
4. Label the record `local-sha256-TOFU; publisher wheel digest unavailable`. Never call it publisher-verified.
5. Optionally, have a second independent retrieval at a later time agree byte-for-byte. This reduces transient-corruption risk but not origin risk.
6. Freeze that local hash into `--require-hashes` for all later installs.

Also check whether a combined official index (e.g. `/whl/torchvision/`) or the PEP 691 JSON publishes a digest for the identical filename. If one does, prefer it, and require that the local hash equals it.

## Interim disposition and next required inputs

Interim view (not acceptance): the frozen preflight is a sound basis for CPU harness preparation. Q0R-01 and Q0R-03 must be resolved before a dependency lock is released, Q0R-02 before the model download, and Q0R-04 through Q0R-06 belong in the harness/protocol review. None needs model or GPU execution.

Next inputs required from the coordinator to resume this same conversation:

1. Frozen /002 harness candidate SHA, evidence SHA and report publication SHA, plus the exact report path.
2. Any author response or corrected /001 sequence for Q0R-01..03 (corrections need a new reserved sequence).
3. If Python or reading the external root remain blocked in my session, an explicit permission grant, or the coordinator's instruction to record the author verifier as unreproduced.
4. A fresh host observation (C: free, root absence) if a released stage depends on it.
