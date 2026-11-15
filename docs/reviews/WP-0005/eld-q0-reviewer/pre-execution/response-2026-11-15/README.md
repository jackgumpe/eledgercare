# WP-0005 /003: second interim checkpoint — /007 response review and torchvision provenance receipt

**INTERIM CHECKPOINT. This is not the canonical /003 report, not a harness review, and not a combined acceptance.** The prior phase A checkpoint `b75011da408fed5d2cc4f9025416ead6c5632ceb:docs/reviews/WP-0005/eld-q0-reviewer/pre-execution/README.md` and its findings Q0R-01..09 stay unchanged. This file adds new observations only.

## Identity, authority and disclosure

| Item | Value |
| --- | --- |
| Reviewer | eld-q0-reviewer, the same conversation as phase A. Coordinator CLI-init receipts record the session as `e6147c9e-0303-475f-99ff-93ee38a681e4` and the model as actual `claude-opus-5-5` with explicit high effort. I attribute identity to those receipts, not to self-observation |
| Authority | `docs/kickoffs/WP-0005-resume-2026-11-15.md` (reviewer section) at main `1f00ab03dec2c65d6f8402d1e1f10dfc38d3f5aa`, plus INDEX/CURRENT "Resumed /002 and /003 scoped checks, 2026-11-15T15:41Z" |
| Continuation base | `b75011da408fed5d2cc4f9025416ead6c5632ceb` (clean; equal to origin before work) |
| Reviewed /007 | candidate `d666c4163b8b6bdf5f6c69b455c30f3c377cbdc5`; evidence `6cb6a258b9652b7becd3fca9c7cf2f04866c3ec3` (adds only `response/verification.json`); report publication `951d408aabf7bdad3602c0e7698869e2e2457aed` (adds only the /007 report). Base→candidate: 22 paths (1 README link modification + 21 additions), as the author states |
| Review merge | `eb6ecccc0d181f9aa13240d2a9a18bfdc21c27c0`, a normal merge with parents `b75011da…` and `951d408a…`. `git diff 951d408a… eb6eccc` = only my prior phase A README. `qualification/` tree `1b673a0266c228647010ee4fe1363584eb9904be` is identical at the publication and my merge. Author bytes are preserved |
| Interpreter | `C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe`, `3.12.10 (tags/v3.12.10:0cc8128, Apr 8 2025) [MSC v.1943 64 bit (AMD64)]`, AMD64 64bit (confirmed by direct execution) |
| Participation disclosure | I acquired a third-party artifact (the torchvision wheel) as an independent observer. I did not author or edit any harness, preflight or response source, and I did not inspect in-flight /002 harness source |

## Executed checks (reviewer-run, this session)

| # | Command | Result |
| --- | --- | --- |
| R1 | `python.exe -I -B qualification/q0/preflight/verify-preflight.py` (on my merge, /001 subtree unchanged) | Exit 0, PASS. **This closes phase A denial #3 for the /001 verifier**. Its root-absent assertion held on the current host |
| R2 | `python.exe -I -B qualification/q0/preflight/response/verify-response.py` | Exit 0, PASS (author verifier, reproduced by the reviewer) |
| R3 | `python.exe -I -B docs/reviews/WP-0005/eld-q0-reviewer/pre-execution/response-2026-11-15/review_checks.py . <out>` (reviewer-authored; script SHA-256 `25c9bd74…b2f2fc`) | Exit 0, **PASS 25/25**; full output in [review-checks-result.json](review-checks-result.json) |
| R4 | Blob-less partial clone of the Transformers pin (scratch, phase A) `ls-tree -l` vs `git hash-object` of the 6 retained `sources/transformers-*.py` | **All 6 equal upstream tree blobs**: tokenization_auto `3c640de4`, tokenization_utils_fast `708275f3`, tokenization_llama_fast `c348322f`, convert_slow_tokenizer `a9e7c9bf`, tokenization_utils_base `c0e6e8d7`, integrations/ggml `51bdc886`. This closes the author's stated limitation ("not an independently fetched Git-tree comparison") |
| R5 | `git hash-object` of the 6 retained model texts; `ls-files --eol` | All equal hf-tree OIDs (`1c28cf39`, `65c295e8`, `f01b4bd3`, `e97c1bb9`, `ae2383ca`, `c79e1e33`); i/lf w/lf, so no eol filter masked bytes |
| R6 | `python.exe -I -B …/acquire_torchvision.py .scratch/torchvision-provenance <receipt> qualification/q0/preflight/response/cuda-metadata.json` | Exit 0, PASS; see receipt below |
| R7 | Second hash, by separate Python one-liner and PowerShell `Get-FileHash -Algorithm SHA256` | Both 9,091,113 B / `5ae0ff50…d385c`; the scratch dir holds only that file; `git check-ignore` → `.gitignore:25:.scratch/` |

What R3 establishes, recomputed from the raw `requires_dist` in pypi/cuda metadata rather than from the author's lock edges:
- **Q0R-01:** the helper matches its receipt SHA-256/blob and is byte-identical in frozen `13544cd2…` (an ancestor of the candidate). All 17 receipt outputs match committed bytes. The only unreceipted files are README, the two scripts, the receipt and verification.json. All 50 retrieval stamps are `+00:00` and fall inside the collection interval 05:46:57.354–05:47:06.724 UTC.
- **Q0R-02:** the lock environment equals an environment I built independently from `platform`/`sys` on this host. `platform_machine` is `AMD64`. All three hf-xet requirements are inactive.
- **Closure:** 35 active / 815 inactive / 850 edges. No active requirement is unsatisfied. All 32 artifacts are reachable from the 15 top-level pins with none extra, and they equal the raw metadata selections (1,974,477,651 B). Every tag is compatible with this interpreter's `sys_tags`. Hosts are only `files.pythonhosted.org` and `download-r2.pytorch.org`. No hf-xet, triton, sentencepiece, protobuf, tiktoken, gguf, accelerate, flash-attn or xformers is selected. The 13 original pins are unchanged.
- **Q0R-03:** the six model texts match the pinned tree. The new Python sources import only `transformers` (configuration), stdlib (conversation) and `torch` (packing_patch). The tokenizer is built-in `LlamaTokenizerFast`, with no `auto_map` in either the config or the special-tokens map, `add_prefix_space=null`, and `from_slow` absent.
- **torchvision:** /001 and /007 records agree on URL, size, ETag and METADATA text. The METADATA hash is `f8e91ee9…`. Neither index exposes a wheel digest. The torch publisher digest is unchanged.
- **Host** (observed 2026-11-15T15:54:32.99Z, `shutil.disk_usage`/`Path.exists`): C: free 69,312,876,544 B (64.55 GiB), total 491,350,462,464 B. The selected root and its parent are both absent. That clears the proposed ≥58 GiB start gate at this instant only. It is not a reservation, and it says nothing about the pagefile, DLLs, LongPaths or GPU.

## Finding closure assessment (interim)

| Finding | Interim status | Basis / what remains |
| --- | --- | --- |
| Q0R-01 | **CLOSED (provenance corrected)** | The original /001 producer claim is explicitly retracted, not repaired. Regeneration by a frozen helper is byte-bound and verified (R2, R3). The /001 JSON remains historically unattributed, which is acceptable because it is superseded |
| Q0R-02 | **CLOSED for metadata**; runtime part pending | Marker false on AMD64 (R3). Still pending: re-evaluation in the released venv; transport-independent model payload verification at acquisition |
| Q0R-03 | **CLOSED for static source/dependency closure** | Identities independently tree-matched (R4, R5). I spot-checked the static tokenizer reasoning in the tree-verified sources: in tokenization_llama_fast, L25–28 guard SentencePiece, L31 binds `tokenizer.json` and L151 gives the add_prefix_space slow trigger; in tokenization_utils_fast, L113–117 load `TokenizerFast.from_file` when no slow override is set. Actual tokenizer/class import is still unexecuted |
| Q0R-04..09 | Accepted as proposal refinements; **to be verified in the frozen harness** | Raw logs/Triton-absent labeling, local path/offline flags, cache env map, MSVC/LongPaths/pagefile precheck, hash-only offline install, notice retention. None of these can be accepted before /002 pins |

New observations, low severity, for the author/harness (no repair performed):
- **N-01 (Low):** `metadata-lock.json` cannot be installed yet. Its torchvision `sha256` is null by design. The lock must now be completed with the receipt below, with `hash_kind` set to `local-sha256-TOFU; publisher wheel digest unavailable`, never "publisher-declared". The lock should also bind this checkpoint's publication SHA as the source of the hash.
- **N-02 (Info):** verification at acquisition must still compare each installed wheel's own dist-info METADATA against the frozen graph, as /007 states. Only torchvision's METADATA has been read so far, and torch's wheel body has not been acquired.
- **N-03 (Info, reviewer self-correction):** my receipt field `etag_matches_recorded_head: false` is a **defect in my reporting script**, not a mismatch. The server returned the lowercase header key `etag` and my script looked up `ETag`. The values are byte-identical: `"1b523c735e0ad5a7e684b039d58e3868-2"` (receipt L24 vs /001 and /007 HEAD). Last-Modified matches. The ETag isn't a content digest in any case, and pass/fail didn't depend on it. I'm preserving the receipt unchanged.
- **N-04 (Info):** the payload was served by Cloudflare (`cf-cache-status: HIT`, `Server: cloudflare`), unlike the S3/CloudFront index. The final URL is the exact official `download-r2.pytorch.org` URL with no redirects. A cached edge copy is part of the TOFU limitation. The receipt records an anonymous `__cf_bm` bot-management cookie that the CDN set; it holds no user data.

## Torchvision acquisition receipt (for the dependency lock)

```text
label:           local-sha256-TOFU; publisher wheel digest unavailable
filename:        torchvision-0.28.0+cu130-cp312-cp312-win_amd64.whl
url / final_url: https://download-r2.pytorch.org/whl/cu130/torchvision-0.28.0%2Bcu130-cp312-cp312-win_amd64.whl  (HTTP 200, no redirects)
retrieved_utc:   2026-11-15T15:55:12.355593Z .. 15:55:15.799959Z (server Date: Sun, 15 Nov 2026 15:55:13 GMT)
size:            9,091,113 bytes (Content-Length and bytes read; 10 MiB bound)
local SHA-256:   5ae0ff50fcb43a189250a5fdb36a7dc780ea5caff469653cab1e3f32ed5d385c   (3 independent computations agree)
ETag:            "1b523c735e0ad5a7e684b039d58e3868-2" (multipart; not a digest); Last-Modified: Wed, 08 Jul 2026 12:31:59 GMT
ZIP:             215 members; exactly one dist-info METADATA: torchvision-0.28.0+cu130.dist-info/METADATA (5,744 B, deflate, CRC 3650667772)
METADATA:        SHA-256 f8e91ee987603053e2166e2e4063ddcfb533f266c88bae82b7f79119aadceb59 == published PEP 658 digest; bytes == recorded /007 PEP 658 body
                 Name torchvision; Version 0.28.0+cu130; Requires-Python >=3.10,!=3.14.1; Requires-Dist torch (==2.13.0), numpy, pillow (!=8.3.*,>=5.3.0) [+ inactive extras gdown/scipy]
local copy:      .scratch/torchvision-provenance/ in the reviewer worktree (git-ignored; not committed; not installed/extracted/imported/executed)
```

Full machine record: [torchvision-acquisition-receipt.json](torchvision-acquisition-receipt.json). Producer: [acquire_torchvision.py](acquire_torchvision.py), SHA-256 `0592b8ba9190f8186afade4eef854de6a96aff07658943cece11579d9277b7f7`. It uses stdlib HTTPS with a redirect guard limited to official PyTorch hosts and the exact filename, and it reads only the single METADATA member in memory.

**Explicit limits.** TOFU means this hash proves only that later copies equal the bytes this reviewer received over TLS from the official origin at this time. It does not prove publisher intent, and it does not prove the wheel is free of tampering upstream of the CDN. The PEP 658 match authenticates only METADATA, not the other 214 members. Coordinator and final acceptance must weigh these limits against the alternative (holding until PyTorch exposes a wheel digest). Optionally, a later independent second retrieval can confirm byte stability.

## Not done / still pending

- **Not done:** no install, extraction, import or execution of any wheel; no torch wheel or model shard download; no model/tokenizer import; no CUDA/GPU; no external root creation; no MSVC/LongPaths/pagefile/registry probe; no in-flight /002 inspection; no general web fetch. No new permission denial occurred in this session.
- **Pending for canonical /003:** exact frozen /002 candidate, evidence and report pins. Then: full harness review (Q0R-04..09 implementation, lock completion with this receipt and no circular /003-SHA dependency, observer/telemetry validation, fail-closed gates) and reviewer execution of applicable CPU checks on that candidate.
