# WP-0006 F2 Stage 1 Implementation & CPU/PostgreSQL/Browser Checkpoint (`eld-f2-implementer`)

> **Stage 1 Status**: Source-complete F2 implementation frozen and verified across CPU, real PostgreSQL 18.7, and headless Microsoft Edge Playwright checks. **Canonical `WP-0006 /003` is intentionally NOT published yet, and F2 runtime/GPU acceptance is NOT claimed** pending the coordinator's bounded Stage 2 real-GPU acceptance release.

## 1. Identity & Lineage Pins

- **Author Role / Model / Session**: `eld-f2-implementer` · **Gemini 4 Carbon (High)** (`High` effort) · Antigravity CLI conversation `2b6861af-031b-4e8b-9ce9-2a6d476f9da0`
- **Repository / Owned Branch / Worktree**: `https://github.com/jackgumpe/eledgercare` · `feature/wp-0006-local-extraction` · `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f2-implementer`
- **Packet Base**: `8e80a42c29c0fc27a4af6348cfb1ec22cab3764d`
- **Initial Dispatch Base**: `c08d50e204395e60a88ce25f70e25bd29b97b8c6` (reviewed `/001` design `efa9cb986711f82a886f917e68142a7a59319bba`)
- **Author Planning Checkpoint**: `56498bf28326a55054d4b83ab5bb9e73234deffb`
- **Accepted Independent Design Review (`WP-0006 /002`)**: `e2452e1ab3d8937868c07ffb30ce430715b5be78` (dossier `7eae6de27d21bd41558611f95116e13cbd0f6b92`, evidence `dc296f3a3bc8041bc2eb62377c440a3879d1bcc8`)
- **Coordinator Stage 1 Implementation Release**: `d106db76de6dc8d9b52770d405ca95300b6dacd6` (deliverable `be3de3c1f17d5177cba87f589752c646b37d356c`)
- **Frozen Stage 1 Deliverable Candidate SHA**: **`0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978`** (`69` files changed, clean `git status --porcelain` before and after decisive execution)

## 2. Contract & Review Requirement Disposition (`F2-KR-01`, `F2-BIC-01..04`, `F2-04`)

| Requirement | Stage 1 Implementation & Verification |
|---|---|
| **`F2-KR-01`** (Grants, smoke scripts, `workers/ocr` placeholder) | Updated `deploy/dev/database/grant-runtime.sql` (`SELECT, INSERT` only on `documents`, `original_artifacts`, `extraction_results`; column-scoped `UPDATE` on `processing_jobs` and `execution_attempts`; `USAGE, SELECT` on `extraction_fencing_seq`); added port-parameterized `deploy/dev/smoke/run-browser-checks.ps1` and `deploy/dev/smoke/run-demo-smoke.ps1` (`5190`/`4210` defaults, reviewer `5290`/`4310` overrides); updated `workers/ocr/README.md` to point to `workers/local_ocr/`. |
| **`F2-BIC-01`** (Self-contained manifests; zero qualification/research/evaluation/git coupling) | Resolved self-contained `workers/local_ocr/manifests/model-files.json` (`18` model objects + `README.md` notice) and `dependency-lock.json` (`32` distributions + `torchvision-local-sha256-TOFU` provenance); verified by `SyntheticFixtureTests` and `test_worker_cpu.py` that runtime code/scripts never reference `qualification/`, `research/`, `evaluation/`, or `git.exe`. |
| **`F2-BIC-02`** (Non-modifying native `infer` observation; frozen Q0 kwargs/timeouts) | `workers/local_ocr/local_ocr/observer.py` uses Python 3.12 PEP 669 `sys.monitoring` (`TOOL_ID=4`) `PY_RETURN` on `UnlimitedOCRForCausalLM.infer` to capture the native dict (`finish_reason`, `num_pages_out`, `token_ids`) while `infer_multi` returns its unmodified 2-tuple, and `PY_START` `SafetyTripwire` on `_uocr_save_results` / `process_image_with_refs` / `draw_bounding_boxes` / `extract_coordinates_and_label` plus static AST reachability verification; 1p/2p/3p timeouts pinned to `1800s` / `2700s` / `3600s`. |
| **`F2-BIC-03`** (Caller replay vs explicit prior-attempt retry; F1 7-key receipt preserved) | `POST /api/documents` and `GET /api/submissions/{key}` preserve F1's exact 7 JSON keys; `GET /api/documents/{id}` extends summary with `admittedPageCount`, `currentAttemptId`, `acceptedResultId`. Empty-body `POST /api/documents/{id}/extraction` reconciles `queued`/`running` (`202`) or `completed` (`200`), and returns `409 retry_explicit_required` on `failed`/`interrupted` jobs unless `{ "retryAttemptId": "<latestAttemptId>" }` is explicitly supplied. |
| **`F2-BIC-04`** (Inert plain-text & structured table rendering; hostile markup safety) | `SafeNativeDisplayParser` splits `<PAGE>` sections in exact `1..N` order and parses native `<table>` rows into plain-text cell strings while preserving non-table tags (`<script>`, `<img onerror>`) literally; `document-page.ts` binds exclusively via Angular text interpolation (`{{ ... }}`), verified in headless Edge (`window.__f2_xss === undefined` and zero `<script>`/`<img>` DOM elements). |
| **`F2-04`** (Race-free child lifetime containment, OS PID+FILETIME, fencing) | `WindowsJobProcess.CreateSuspendedAssigned` creates a non-inheritable Job Object (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`), spawns the child via `CreateProcessW(CREATE_SUSPENDED)` with `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` (`[NUL, stdout, stderr]` only), assigns the suspended child to the Job Object, and persists `(launcher_pid, launcher_create_filetime)` in PostgreSQL **before** `ResumeThread`. Tested via `Abrupt_TerminateProcess_of_external_supervisor_kills_launcher_and_grandchild_via_Job_Object` in both `suspended` and `running` grandchild modes (`entireProcessTree: false`), plus monotonic `extraction_fencing_seq` fencing and live-supervisor/live-worker non-theft checks. |

## 3. Decisive Post-Freeze Stage 1 Verification Summary (`0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978`)

All 11 decisive commands ran sequentially against clean `HEAD = 0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978` on owned loopback ports (`5190` API, `4210` UI, `55434` PostgreSQL 18.7). Full machine-readable timings and check records are in [`decisive-summary.json`](decisive-summary.json).

| Step | Command | Result | Duration |
|---|---|---|---|
| `01` | `dotnet tool restore` | `EXIT 0` (`dotnet-ef 10.0.15`) | `246 ms` |
| `02` | `dotnet restore ELedgerCare.slnx --locked-mode` | `EXIT 0` (zero lock changes) | `17,668 ms` |
| `03` | `dotnet build ELedgerCare.slnx -c Release --no-restore` | `EXIT 0` (`0` warnings, `0` errors) | `4,984 ms` |
| `04` | `dotnet publish src/ELedgerCare.Api/ELedgerCare.Api.csproj -c Release --no-restore` | `EXIT 0` (`0` warnings, `0` errors) | `1,650 ms` |
| `05` | `python -B -m unittest discover -s workers/local_ocr/tests -p "test_*.py" -v` | `EXIT 0` (**`7/7` passed**) | `490 ms` |
| `06` | `npm ci --prefer-offline --no-audit` (`web/`) | `EXIT 0` (`241` locked packages) | `15,109 ms` |
| `07` | `npx ng build` (`web/`) | `EXIT 0` (`71.73 kB` initial bundle, `0` warnings) | `4,654 ms` |
| `08` | `pwsh -NoProfile -File deploy/dev/database/prepare-database.ps1 -Database eledgercare_stage1_0ad2fcd` | `EXIT 0` (F1+F2 migrations + least-privilege grants verified) | `6,978 ms` |
| `09` | `dotnet test --solution ELedgerCare.slnx -c Release --no-build` | `EXIT 0` (**`69/69` passed**: `11` Domain, `39` Infra, `19` PG Acceptance; `0` failed/skipped) | `80,731 ms` |
| `10` | `pwsh -NoProfile -File deploy/dev/smoke/run-browser-checks.ps1` | `EXIT 0` (**`10/10` passed** in headless MS Edge: `4` F2 + `6` F1) | `36,766 ms` |
| `11` | `pwsh -NoProfile -File deploy/dev/smoke/run-demo-smoke.ps1` | `EXIT 0` (`allMatch: true` across API termination + PostgreSQL `pg_ctl` fast restart) | `8,184 ms` |

- **Total Automated Test Count Executed on Frozen Candidate**: **`86 / 86` passed (`0` failed, `0` skipped)**.

## 4. Pinned Artifact & Config Digests on `0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978`

- `workers/local_ocr/manifests/model-files.json` SHA-256: `0df07bc60abf6937c917040bced32afabd7e4d11bafc0bd99902abca610a81be`
- `workers/local_ocr/manifests/dependency-lock.json` SHA-256: `582071bf20eaca1836c3d1cef21d31cbdaa1e1407184033a918a40612c128111`
- `workers/local_ocr` source digest (`ComputeWorkerSourceSha256`): `01ad2fa1d6dcf8643ecb5801a934b37bae4630faca2f70959b4a85cc4480eb01`
- Worker config digests (`ComputeWorkerConfigSha256`):
  - `1` page (`max_new_tokens=8000`, `ngram_window=128`): `579aad63a9893a58466baf005ea63f87e92540d4c1f71f6b3c399e8b1e6b35ff`
  - `2` pages (`max_new_tokens=16000`, `ngram_window=1024`): `e4df504ddb51dcc8fb137e97f5af97c735252374738b1a1754a88b16a05de5df`
  - `3` pages (`max_new_tokens=24000`, `ngram_window=1024`): `ac90459ca4011b5859cfdd0b224d5ea247489b7c01775118736df7c1c9819e86`
- Committed test fixtures:
  - `tests/fixtures/F1-SWO-001.pdf` (`887` B, `1` page): `875a2d8c83c1c1002b38840f8136b60bd5ebcfe8d2df47187bf36454c59497cb`
  - `tests/fixtures/SYN-WO-01-v1-raster300.pdf` (`372,258` B, `1` page): `47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd`
  - `tests/fixtures/SYN-MP-01-v0-clean.pdf` (`8,422` B, `3` pages): `15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3`

## 5. Checks Intentionally Not Run in Stage 1 & Stage 2 Coordinator Release Inputs

- **Not Run in Stage 1 (per Stage 1 Hold)**:
  - No GPU lease acquired; no `torch`, `transformers`, or `Unlimited-OCR-2` model load/inference executed; `C:\Users\jackg\eLedgerCare-Q0\WP-0005` was not invoked and `C:\Users\jackg\eLedgerCare-F2\WP-0006` was not created (`external_f2_runtime_root_exists: false`).
  - No holdout corpus families (`F03`, `F05`, `F06`, `F08`) accessed.
- **Concrete Stage 2 Runtime Release Inputs Needed from `eld-coordinator`**:
  1. Bind frozen Stage 1 source candidate **`0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978`** for Stage 2 real-GPU execution.
  2. Issue sole serialized GPU lease (`LocalOcr__LeasedGpuUuid=GPU-...` with `CUDA_DEVICE_ORDER=PCI_BUS_ID` after confirming `WP-0007` GPU work is idle).
  3. Authorize read-only reuse of `LocalOcr__ReadOnlyQ0Root=C:\Users\jackg\eLedgerCare-Q0\WP-0005` and creation of isolated writable runtime root `LocalOcr__WritableRuntimeRoot=C:\Users\jackg\eLedgerCare-F2\WP-0006` (`<= 4 GiB` cap, `>= 20 GiB` free disk floor) with `LocalOcr__Enabled=true` during the bounded Stage 2 run (`LocalOcr:Enabled` remains `false` in committed `appsettings.json`).
  4. Bind the finite Stage 2 acceptance run matrix:
     - `SYN-WO-01-v1-raster300.pdf` (`1` page real GPU extraction + persisted result screen verification)
     - `SYN-MP-01-v0-clean.pdf` (`3` pages real GPU extraction + page order `1..3` verification)
     - Forced owned supervisor/worker interruption during active model run (verifying `KILL_ON_JOB_CLOSE` leaves zero orphan CUDA worker/VRAM, startup reconciliation to `interrupted`, and explicit retry completion)
     - Full API + PostgreSQL fast restart and reopen of saved results with `LocalOcr__Enabled=false`.
