# WP-0005 / 002: Q0 unmodified-model qualification harness, frozen protocol and CPU verification

- Report path: `docs/agent-reports/eld-q0-harness/WP-0005/002_2026-11-15_implementation_eld-q0-harness.md`
- Sequence reservation: main `INDEX.md`, WP-0005 /002 row; kickoffs `docs/kickoffs/WP-0005-eld-q0-harness.md` and `docs/kickoffs/WP-0005-resume-2026-11-15.md` (coordinator main checkout)
- Category: implementation
- Author / agent ID: eld-q0-harness
- Actual model / effort: claude-opus-5-5, high. The model ID is reported by the runtime. The coordinator's CLI-init receipt confirms that the session UUID `04e0efba-5292-4cae-b922-1517dee7bbed` matched the reservation. I attribute that to the receipt, not to self-observation.
- Execution environment: Claude Code CLI on Windows 11 10.0.26200. PowerShell/Git Bash tools. CPU checks used `C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe` 3.12.10 (stdlib only), confirmed before running.
- Published by: author (normal owned-branch push)
- Timestamp: 2026-11-15T16:19:59Z
- Repository / branch: `jackgumpe/eledgercare` (private) / `qualification/wp-0005-harness`; worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness`
- Base revision: `df9a2b50894f01987d779d7f9ae805794503ce6f` (original task/report base); final continuation base `912f4f4f991977cca83bb40928cff45ac525efaa`
- Deliverable revision: frozen candidate **`84cef5ef30685ffee46281fefc5fd1356dbc1876`**; author evidence **`0331efd71ef17e5485adac5a53d864c6d96e8f4a`**
- Previous report: none by this author (first canonical /002 report)
- Related inputs (exact Git objects):
  - Astra /001 `95ce0a8df728ae2c41aaf9e09d1b97c7d990fe36` / `2c32dde602b274251043bb216752f5d7fe9593be`
  - Astra /007 candidate `d666c4163b8b6bdf5f6c69b455c30f3c377cbdc5`, evidence `6cb6a258b9652b7becd3fca9c7cf2f04866c3ec3`, report `951d408aabf7bdad3602c0e7698869e2e2457aed`
  - reviewer phase A `b75011da408fed5d2cc4f9025416ead6c5632ceb:docs/reviews/WP-0005/eld-q0-reviewer/pre-execution/README.md` (Q0R-01..09)
  - reviewer receipt checkpoint `ef72849519c83a71e59e80c311b48719252d0cd6:docs/reviews/WP-0005/eld-q0-reviewer/pre-execution/response-2026-11-15/` (README `63aa845b…`, receipt `877d8220…`; N-01..04)
- Status: ready-for-review (author verification only; this is not independent acceptance)
- Next owner: separate, uninvolved eld-q0-reviewer for /003

## Summary

This report delivers a separate **research** qualification harness for the unmodified `baidu/Unlimited-OCR-2@0480966938291445591f69f08a13b041c073a96a` checkpoint. It is not production OCR integration. The deliverable has four parts:

- a frozen protocol;
- a bound, non-circular dependency lock;
- a staged acquisition/installation plan;
- meaningful stdlib CPU checks.

**What is established is CPU harness readiness only.** The model has not been qualified. No wheel or model was downloaded, nothing was installed, no model or tokenizer was imported, and no CUDA allocation or GPU run happened. Every Q0 runtime question remains open for the released `/004` stage: native loading, the Triton/fallback path, memory, timing, determinism and finish behaviour.

The work went through three revisions. Each has its own evidence, and each set of passing checks applies only to its own revision:

| Revision | Code | Evidence | CPU result on that exact revision |
| --- | --- | --- | --- |
| Checkpoint 1 (initial candidate) | `50157e6cbaf0a2fcc29d229781237a05aa95fa92` | `fde7fdc16d4e32ca347661e96afc0d2f7c099fb4` + newline note `1b88bfd7cc22e06bc8fd78193ad4821d1a383cb0` | Attempt 1 invalid (evidence-runner path bug; no candidate code ran); attempt 2: 53 tests OK |
| Checkpoint 2 (prepared; torchvision digest still a gap) | `e228f9d19b64116d3d5894af97d21553d1fe4d10` | `912f4f4f991977cca83bb40928cff45ac525efaa` | 68 tests OK, 1 skipped |
| **Final candidate** | **`84cef5ef30685ffee46281fefc5fd1356dbc1876`** | **`0331efd71ef17e5485adac5a53d864c6d96e8f4a`** | **75 tests OK, 1 skipped**; all CLI checks as expected |

Frozen identities at the candidate (SHA-256 over the committed blob bytes):

- `qualification/q0/harness/protocol.json`: **`dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309`**
- `qualification/q0/harness/locks/dependency-lock.json`: **`d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e`**
- `qualification/q0/harness/manifests/model-files.json`: `085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8`
- Harness tree at the candidate: `b7afcd512d508e43b874cf7b9857b7493359a879`

## Objective and acceptance criteria

Implement the kickoff's research runner. Its requirements, with where each is met:

| Requirement | Where it is met |
| --- | --- |
| Native `infer_multi(..., crop_mode=False, save_results=False)` with `temperature=0.0` | §2 |
| Dev-only F01/F07 v0-clean inputs rendered by `pypdfium2==5.15.2` / PDFium 159.0.8149.0 at `scale=300/72` | §1 |
| Frozen prompt, budgets, guards, stop/timeout policy, fixture and raster hashes | §1–§3, §6 |
| Native return/finish information preserved; raw output written by a bounded stdlib writer; the eval save path never invoked | §3–§5 |
| Telemetry of Triton attempted/executed/fallback, DynamicCache growth and decode path, without changing semantics | §4 |
| Cold/warmup/two warm repeats with synchronized timing, CUDA/RSS memory, tokens, pages, finish reason and repeatability | §3 |
| Measurements labelled as direct, native, derived, source-inferred or unsupported | §3–§4 |
| Fail-closed classes; no manufactured accuracy | §6 |
| Exact acquisition/verification plan | `ACQUISITION.md` |
| Consume Astra /001 and /007 and the reviewer receipt by pin; remove the circular /003 requirement; address Q0R-04..09 and N-01..03; reconcile the observer plan | below |

Observable completion: the frozen candidate and its evidence are pushed and remote-verified, the decisive CPU checks pass, and the report is published. Section references (§) point to `qualification/q0/harness/PROTOCOL.md`.

## Change inventory

The base-to-evidence diff `df9a2b5…0331efd` contains **88 paths. All are additions under `qualification/q0/harness/`.** Nothing outside that subtree changed. No preflight, reviewer, corpus, model source, product or coordinator file was touched. This report is the only later addition.

| Action | Path(s) | What / why | Introduced → last changed |
| --- | --- | --- | --- |
| Added | `README.md`, `PROTOCOL.md`, `ACQUISITION.md` | Overview; frozen protocol; staged hash-verified plan | 50157e6c → 84cef5ef |
| Added | `protocol.json` | Machine-readable frozen protocol and lineage | 50157e6c → 84cef5ef |
| Added | `locks/dependency-lock.json` | `eldq0-lock/2`: bound to the Astra /007 graph and the CUDA METADATA source; torchvision local-digest record | 50157e6c (pending lock) → e228f9d1 (bound) → 84cef5ef (receipt) |
| Added | `manifests/model-files.json` | 18 runtime objects plus the separate model-card notice, derived from the pinned HF tree | 50157e6c (19 files) → e228f9d1 |
| Added | `q0.py` | CLI: CPU checks, host precheck, install-stage gates, `execute`/`child` | 50157e6c → 84cef5ef |
| Added | `q0harness/__init__.py`, `hashing.py`, `outcome.py`, `protocol.py`, `fixtures.py`, `sourcecheck.py`, `environment.py`, `writer.py`, `procmem.py`, `telemetry.py`, `render.py`, `session.py`, `supervisor.py`, `backend_torch.py`, `preflight.py` | Core harness | 50157e6c → e228f9d1 |
| Added | `q0harness/locks.py` | Bound lock, receipt verification, every-wheel METADATA check, installed-set check | 50157e6c → 84cef5ef |
| Added | `q0harness/modelfiles.py`, `release.py`, `hostcheck.py`, `logscan.py` | 18-object/notice/path hygiene; release records; read-only host precheck; raw-log markers | e228f9d1 (modelfiles from 50157e6c) |
| Added | `tests/support.py`, `tests/test_*.py` (8), `tests/fakemodel/*.py` (5) | Stdlib unittest CPU checks. The fake model package mirrors the native call graph and return contract; it is a test double, not model code | 50157e6c → 84cef5ef |
| Added | `evidence/002-cpu/**` (18) | Checkpoint 1 evidence, including the preserved invalid attempt 1 | fde7fdc1, 1b88bfd7 |
| Added | `evidence/002-checkpoint-2/**` (14) | Checkpoint 2 evidence (`-text`, byte-exact) | 912f4f4f |
| Added | `evidence/002-final/**` (15) | Final evidence (`-text`, byte-exact) | 0331efd7 |

Candidate-relative scope:

- base → candidate `84cef5ef`: 73 paths. These are 41 code/doc/test/config paths plus the 32 earlier evidence files.
- `912f4f4f` → `84cef5ef`: 11 modified paths: `ACQUISITION.md`, `PROTOCOL.md`, `README.md`, `locks/dependency-lock.json`, `protocol.json`, `q0.py`, `q0harness/locks.py`, `tests/support.py`, `tests/test_locks_preflight.py`, `tests/test_session.py`, `tests/test_supervisor_cli.py`.
- `84cef5ef` → `0331efd7`: 14 evidence-only additions.

Report metadata committed afterward: this one file. External effects:

- normal pushes of the owned branch only;
- `git fetch origin review/wp-0005-q0`, a read-only fetch used to obtain the receipt objects;
- read-only host observations (§Verification).

No directory under `C:\Users\jackg\eLedgerCare-Q0` was created. No settings, credentials, packages or other processes were changed, apart from the harness's own test child processes.

## Decisions and rationale

1. **Strict native call, no new processors.** The frozen kwargs are explicit native defaults plus three values from the upstream evaluation setup: `no_repeat_ngram_size=35`, `ngram_window` of 1024 for multi-page and 128 for single-page, and 8000 tokens/page. Both `save_results=False` and `output_path=""` are passed, because the save call requires both to be truthy. `infer_multi` returns only `(text, n)`, so the full native return dict is captured externally with `sys.monitoring` at `infer` return. There is no monkeypatch.
2. **Telemetry is external.** PEP 669 local events are set on the native code objects. The resulting observations cover:
   - Triton attempted, executed or import-fallback;
   - dense SDPA fallback;
   - DASH prefill/decode and fp32 decode attend;
   - base sparse-path calls;
   - DynamicCache `seq_len` and K/V bytes per forward;
   - the prefill-boundary allocator peak.

   The only intervention is a tripwire on the statically unreachable eval save chain. It raises before the chain's first instruction and is recorded even if the native bare `except` swallows it.
3. **Raster contract.** The predicted RGB digests are inflated from the committed dev v1-raster300 children, which the corpus generator built from exactly these v0 bytes with the same render call. The released stage must render and match them.
4. **Bound lock, never transcribed (Q0R-01..03, N-01).** The 32 artifacts, the 31 publisher hashes and the 850-edge Requires-Dist graph are read at check time from Astra's exact blob `ec8c650e…`. Its SHA-1, size, status, AMD64 marker environment and counts are all checked. The published METADATA digests for torch and torchvision come from the bound `cuda-metadata.json` blob `bca91aaa…`, whose recorded bodies are re-hashed.
5. **Torchvision local digest.** The local digest is bound to the independent receipt `ef728495…` (blob `877d8220…`, 3,103 B): `5ae0ff50fcb43a189250a5fdb36a7dc780ea5caff469653cab1e3f32ed5d385c`, 9,091,113 B, METADATA `f8e91ee9…`. Its label is `local-sha256-TOFU; publisher wheel digest unavailable`. The harness re-reads the receipt blob and requires:
   - the label, `pass` and every check true;
   - the exact URL, with no redirects and HTTP 200;
   - size, SHA-256 and METADATA digest equal to the record;
   - name/version and `torch (==2.13.0)`.

   The disclosed `etag_matches_recorded_head:false` reporting defect (N-03) is ignored explicitly and preserved, not treated as a payload mismatch. No cookies or unneeded headers are copied into the lock.
6. **Non-circular acceptance.** The lock contains no /003 identity; tests reject `accepted_review`/`review_003` inside it. A coordinator `eldq0-release/2` record per stage binds:
   - the accepted review;
   - the exact clean harness commit;
   - the protocol and lock SHA-256;
   - `accepted_provenance_exceptions` (must include `torchvision-local-sha256-TOFU`);
   - the storage root;
   - for execution, the GPU UUID and lease.
7. **Every wheel's METADATA before install (N-02).** `verify-wheelhouse` checks size and effective SHA-256 for each of the 32 wheels. It then reads each wheel's own top-level `dist-info/METADATA` from the ZIP and requires:
   - exact Name/Version;
   - a Requires-Dist multiset equal to the frozen graph, with formatting normalized only (name canonicalization, sorted extras and specifiers, marker whitespace and quotes);
   - for torch and torchvision, the published PEP 658 digest.

   The graph edges reproduce every artifact's published Requires-Dist list exactly (32/32 checked on this host before implementation). The comparison is validated on the real recorded torch and torchvision METADATA bodies.
8. **Q0R-04.** The lock and policy have no Triton, flash-attn or xformers, and `find_spec` must be None for each. Check 4 passes only on `triton_import_failed_dense_fallback` for every call, with +1 cache growth per step and no ring marker. The result is then labelled "unmodified model on non-Triton fallback path". Triton actually executing is NOT_QUALIFIED.

   Raw child stdout/stderr are preserved and scanned for the model's own diagnostic lines. The absence of a line is never treated as evidence of a path.
9. **Q0R-05.** Run-local caches and temp: `TEMP`/`TMP`/`TMPDIR`, `HF_MODULES_CACHE`, `TORCH_HOME`, `TORCHINDUCTOR_CACHE_DIR`, `TRITON_CACHE_DIR`, `CUDA_CACHE_PATH`, `PIP`/`UV` caches and `XDG`. `HF_HOME`, `HF_HUB_CACHE` and `TRANSFORMERS_CACHE` live under the root.

   Free-space floors are ≥ 58 GiB before the first download and ≥ 20 GiB at session preflight and every supervisor poll. The supervisor kills only its own child. Pagefile and driver growth outside the root are stated to be unbounded.
10. **Q0R-06.** The model directory is a normalized absolute path with no trailing separator. It must not be a reparse point and its basename must be an identifier: `models\Unlimited_OCR_2_04809669`, which the coordinator accepted. Offline flags are asserted before any HF import, and the harness never falls back to a repo ID.
11. **Q0R-07.** The read-only host precheck covers: MSVC runtime DLLs (presence, size, SHA-256, version), `LongPathsEnabled` plus known path lengths, paging-file configuration, commit/memory, free space and both observer queries. Venv path lengths are re-checked after installation.
12. **Q0R-08.** Installation is offline and hash-only: `--no-index --no-deps --only-binary=:all: --require-hashes --find-links <wheelhouse>`, then `pip check`. The installed set must equal the 32 locked distributions, so the CPU `torch 2.13.0` counts as a mismatch.
13. **Q0R-09.** The model files are 18 runtime objects: 16 checked by Git blob plus size, and 2 shards by LFS SHA-256 plus size, transport-independent. The model card `README.md` is a separately verified notice outside the runtime directory.
14. **Observer reconciliation.** The unvalidated combined `--query-gpu`/`--query-compute-apps` command is replaced by two separate `--id=<UUID>` queries. These are the forms Astra's /001 host receipt had already exercised, and the harness host precheck validated them on this host. Per-process VRAM is `[N/A]` under WDDM and is recorded as unsupported telemetry.

Rejected alternatives:

- **Transcribing the 32 hashes into the lock.** Error-prone, and duplicates Astra's bytes.
- **Checking METADATA for torchvision only.** This would leave N-02 unmet.
- **Lower-casing `AMD64`, or similar relaxations.** Rejected.
- **A per-run fresh `HF_MODULES_CACHE`.** Kept: each run is isolated, and module-cache identity is checked after load.

## Verification

Decisive checks ran on the frozen candidate `84cef5ef…`, from 2026-11-15T16:18:12.404294Z to 16:18:45.590321Z. Evidence is at `qualification/q0/harness/evidence/002-final/84cef5ef/` (commit `0331efd7…`). The raw output bytes equal `summary.json` digests (11/11, verified against the committed blobs).

| Check / exact command (from worktree root) | Revision | Actual result | Evidence |
| --- | --- | --- | --- |
| `python -I -B -c "import sys; print(sys.executable, sys.version)"` | n/a | `C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe` 3.12.10 (MSC v.1943 64 bit AMD64) | session log |
| `python -I -B qualification/q0/harness/evidence/002-final/run_checks.py 84cef5ef`, which runs: | 84cef5ef | HEAD unchanged, tracked diff empty, storage parent absent before and after, no scratch left, never-written file absent | `summary.json` |
| ↳ `-m unittest discover -s qualification/q0/harness/tests -t qualification/q0/harness/tests -v` | 84cef5ef | exit 0: **75 tests OK, 1 skipped** (`test_links_rejected`: WinError 1314, symlink privilege not held) | `01-unittest.txt` |
| ↳ `q0.py verify-snapshots` | 84cef5ef | exit 0: snapshots equal the pinned HF blobs. Static facts: single `eval` at L120, unique guard at L1103, exact save-chain callers, crop default False, native return keys present | `02` |
| ↳ `q0.py derive-rasters --check` | 84cef5ef | exit 0: F01 p1 and F07 p1–p3 digests identical | `03` |
| ↳ `q0.py build-model-manifest --check` | 84cef5ef | exit 0: identical (18 runtime objects plus notice) | `04` |
| ↳ `q0.py check-protocol` | 84cef5ef | exit 0: protocol SHA-256 `dd8a7dc3…`; fixtures verified | `05` |
| ↳ `q0.py lock-check` | 84cef5ef | exit 0: 32 artifacts, counts 31/1/0, `installable: true`, `required_exceptions: ["torchvision-local-sha256-TOFU"]`, receipt checks all true, METADATA digests for torch and torchvision, lock SHA-256 `d8eeaf0f…` | `06` |
| ↳ `q0.py status` | 84cef5ef | exit 0: code identity `84cef5ef…`, clean | `07` |
| ↳ `q0.py host-precheck --stage initial` | 84cef5ef | exit 0, pass. Read-only: C: free 68,879,597,568 B; MSVC 14.51.36247.0 ×3; LongPathsEnabled=0 with known paths ≤ 162; both `nvidia-smi` queries rc 0 (UUID match, RTX 5070 Ti, compute_cap 12.0); root absent | `08` |
| ↳ `q0.py execute --owner author` | 84cef5ef | exit 2: BLOCKED `EXECUTION_NOT_RELEASED`; nothing created | `09` |
| ↳ `q0.py write-requirements .scratch/never-written.txt` | 84cef5ef | exit 2: same; file not written | `10` |
| ↳ `q0.py verify-wheelhouse .scratch` | 84cef5ef | exit 2: same, before reading | `11` |
| `git cat-file blob` SHA-256 of protocol, lock and manifest at 84cef5ef | 84cef5ef | `dd8a7dc3…`, `d8eeaf0f…`, `085ac7ba…` | this report |

Earlier revisions (historical; they do not validate the final candidate):

- `50157e6c`, attempt 2: 53 OK.
- `50157e6c`, attempt 1: invalid because of the runner bug; preserved.
- `e228f9d1`: 68 OK, 1 skipped. Its host precheck passed, and refusals were `ACQUISITION_PROVENANCE_PENDING` while the receipt gap existed.

Development runs during authoring are not counted as evidence.

**Not run:**

- any wheel, torch or model-shard download;
- the real 32-wheel METADATA check (wheels not acquired; synthetic ZIPs used);
- venv creation, installation, `pip check` and venv path lengths;
- real `pypdfium2` rendering (a fake renderer replays committed bytes);
- torch, transformers or tokenizer import and model load, `torch.version.cuda`, `get_arch_list`, CUDA and GPU;
- `backend_torch.py` (never imported by the tests);
- real symlink rejection (privilege).

**Permission denials** (no bypass was attempted; each was recorded and an approved simple form used instead):

| Session | Denied operations |
| --- | --- |
| 1 | WebFetch of upstream `dynamic_module_utils.py` |
| 1 | PowerShell `$`-expansion, `Out-File`/`Select-String`/`Move-Item` pipelines |
| 1 | a compound Bash command |
| This continuation | one compound multi-command `git diff … ; … | Measure-Object …` PowerShell line; re-run as separate simple git commands |

The coordinator's resume kickoff approved Python execution after session 1.

## Review map

- Diffs:
  - candidate: `df9a2b5…84cef5ef`;
  - final change: `912f4f4f…84cef5ef`;
  - evidence only: `84cef5ef…0331efd7`.
- Start with:
  - `qualification/q0/harness/PROTOCOL.md` and `protocol.json`;
  - `locks/dependency-lock.json` with `q0harness/locks.py` (`bound_artifacts`, `_attach_published_metadata`, `check_local_record`, `verify_wheel_metadata`, `verify_wheelhouse`, `require_installable`);
  - `q0harness/release.py`, `session.py` (gate order), `telemetry.py` (targets, tripwire, `classify_kernel_path`, prefill probe), `supervisor.py`, `hostcheck.py`, `modelfiles.py`, `environment.py`, `sourcecheck.py`;
  - `ACQUISITION.md`.
- Evidence: `evidence/002-final/README.md` and the raw outputs.
- Suggested independent reproduction: run `python -I -B qualification/q0/harness/evidence/002-final/run_checks.py <new-subdir>` in a reviewer worktree. This needs the Astra and receipt Git objects to be present, for example via fetch.

## Risks, disagreements, and unfinished work

- **CPU readiness is not model qualification.** All Q0 runtime outcomes are unknown until `/004`. A native import or load failure, a Triton/fallback path different from the frozen baseline, OOM, a stall, truncation or non-determinism are fail-closed blockers. None of them is a 0 % score.
- **TOFU limit.** The torchvision digest proves only that later copies equal the bytes the reviewer received over TLS from the official origin, via a Cloudflare edge cache hit. The METADATA match authenticates only that member. The coordinator accepted this narrowly for bounded local Q0. The independent `/003` must still weigh it.
- **Every-wheel METADATA check** is implemented and tested on synthetic wheels and on the real recorded CUDA METADATA bodies. It has not run on real acquired wheels. A raw wheel METADATA form the normalizer does not anticipate would fail closed (a false stop), not open.
- **Other sources of truth that come later:**
  - `torch.version.cuda == "13.0"` is a source inference and must be observed at runtime;
  - the `PDFIUM_INFO` string form is checked only by `preflight-cpu`;
  - local-directory dynamic loading is source-reasoned (reviewer phase A) but not executed.
- `LongPathsEnabled=0`. The venv's deepest installed path is unknown until installation, and a path of 240 characters or more stops the stage. No registry change is authorized.
- No disagreements are open. Reviewer N-01..N-04 are addressed (N-01/N-02 implemented, N-03 ignored-and-preserved, N-04 recorded as a TOFU limit). Q0R-04..09 are implemented for the independent review.

## Handoff

Next: the independent, uninvolved eld-q0-reviewer `/003` reviews:

- the exact candidate `84cef5ef30685ffee46281fefc5fd1356dbc1876`;
- the evidence `0331efd71ef17e5485adac5a53d864c6d96e8f4a`;
- this report.

Reproduce applicable CPU checks independently. No install, model or GPU stage is released by this report. `/004` needs a separately amended kickoff, plus coordinator `eldq0-release/2` install and execute records binding the accepted review, the clean harness commit, protocol SHA-256 `dd8a7dc3…`, lock SHA-256 `d8eeaf0f…`, `torchvision-local-sha256-TOFU`, the storage root and an observed GPU lease.

Branch: `qualification/wp-0005-harness`. The report publication SHA follows in the handoff message. Remote confirmation of the candidate and evidence happens after the push, and this report is not rewritten to add its own SHA.
