# WP-0006 F2 Implementation and Resource Plan (Initial Checkpoint)

- **Owner / role**: `eld-f2-implementer` (product author)
- **Observed session initialization**: **Gemini 4 Carbon (High)** (`High` effort), new Antigravity CLI conversation `2b6861af-031b-4e8b-9ce9-2a6d476f9da0` (raw backend checkpoint not exposed)
- **Branch / owned worktree**: `feature/wp-0006-local-extraction` / `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f2-implementer`
- **Dispatch base SHA**: `c08d50e204395e60a88ce25f70e25bd29b97b8c6` (packet base `8e80a42c29c0fc27a4af6348cfb1ec22cab3764d`; proposed `/001` design candidate `efa9cb986711f82a886f917e68142a7a59319bba`)
- **Contract inspected**: [`docs/design/F2-local-extraction.md`](../../design/F2-local-extraction.md) and [`docs/kickoffs/WP-0006-eld-f2-implementer.md`](../../kickoffs/WP-0006-eld-f2-implementer.md)
- **Phase status**: **INITIAL PLANNING CHECKPOINT ONLY** (not canonical `WP-0006 /003`). Product source implementation is held until `eld-coordinator` binds accepted `WP-0006 /002`; GPU/model execution is held until a separate coordinator runtime release and sole GPU lease. No product code, dependencies, clusters, services, holdout corpus files (`F03`, `F05`, `F06`, `F08`), or secret values were touched.

---

## 1. Architecture and Product/Research Boundary

Keep the single `ELedgerCare.slnx` dependency direction (`Domain` <- `Application` <- `Infrastructure` <- `Api`), the Angular `22.2.6` frontend (`web/`), and add one self-contained production Python worker under `workers/local_ocr/`.

| Area | Planned additions / updates | Boundary rule |
| --- | --- | --- |
| `src/ELedgerCare.Domain` | Expand `ProcessingStatus` (`awaiting_extraction`, `queued`, `running`, `completed`, `failed`, `interrupted`); add `ExtractionLimits` (`1..3` pages), `ExecutionAttempt`, `ExtractionResult`, `ExtractionProvenance`, and state/fencing invariants on `ProcessingJob`. | Zero outward project/package dependencies. |
| `src/ELedgerCare.Application` | `RequestExtraction` (queue/reconcile/explicit retry), `GetDocumentStatus`, `GetDocumentExtraction`, `ExtractionEnvelopeValidator`, `IExtractionStore`, `ILocalOcrWorkerRunner`. | No EF/HTTP/process primitives; no test mocks in production assemblies. |
| `src/ELedgerCare.Infrastructure` | `ExtractionStore` (short `ReadCommitted` transactions with `SET LOCAL synchronous_commit = on`), forward migration `AddLocalExtraction`, `WindowsJobProcessSupervisor` + `LocalPythonOcrWorkerRunner`. | Real PostgreSQL 18.7 only; never references `qualification/`, `research/`, or `evaluation/`. |
| `src/ELedgerCare.Api` | `POST /api/documents/{documentId}/extraction`, `GET /api/documents/{documentId}/extraction`, extended `GET /api/documents/{documentId}`, `LocalOcrOptions` (`Enabled = false` default), concurrency-1 `ExtractionSupervisorService` (`BackgroundService`). | Loopback-only (`127.0.0.1`), `nosniff`, safe `ProblemDetails` without SQL/stack/worker log dumps. |
| `workers/local_ocr/` | `run_worker.py`, `local_ocr/` modules (`env_guard.py`, `verify_runtime.py`, `pdf_render.py`, `native_runner.py`, `envelope.py`), self-contained `manifests/model-files.json`, `manifests/dependency-lock.json`, `manifests/PROVENANCE.md`, and stdlib CPU tests under `workers/local_ocr/tests/`. | Zero imports, `git cat-file` reads, or subprocess calls into `qualification/`, `research/`, or `evaluation/`; no scorer logic. |
| `web/` | Extend `DocumentPage` (`/documents/:documentId`) with extraction request/retry controls, honest state/phase polling, unavailable/unsupported notices, unreviewed banner, provenance summary, and escaped 1..N page display; parameterize dev/e2e ports via env vars. | Zero `[innerHTML]`, `bypassSecurityTrustHtml`, or `eval`; all model strings rendered via Angular text interpolation `{{ ... }}`. |

**Zero new third-party dependencies**: `.NET 10.0` Win32 P/Invoke (`kernel32.dll`), existing locked NuGet/npm graphs, and read-only reuse of the verified Q0 Python `3.12.10` venv (`32` locked wheels) cover every requirement without lockfile expansion or global installs.

---

## 2. Minimal Safe Process-Lifetime Coupling and Recovery (`F2-04`)

1. **Windows Job Object lifetime coupling**:
   - On Windows, invoking `<Q0Root>\venv\Scripts\python.exe` spawns a `venv` launcher stub process that spawns a child `Python312\python.exe` CUDA worker.
   - For each claimed attempt, the `.NET` supervisor creates a dedicated per-attempt Win32 Job Object (`CreateJobObjectW` + `SetInformationJobObject` with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000`, and **without** `JOB_OBJECT_LIMIT_BREAKAWAY_OK`) and assigns the started child process to it.
   - Both the `venv` launcher and actual `Python312\python.exe` CUDA worker inherit the Job Object. Explicit supervisor stop (timeout, 300s forward-progress stall, 64 MiB log cap, 20 GiB disk floor, or fenced-out heartbeat) invokes `TerminateJobObject` and closes the handle. If the `.NET` API process itself dies abruptly (`TerminateProcess`), the Windows kernel closes the last Job Object handle and immediately terminates both launcher and CUDA worker with no orphan process.
2. **Durable OS process identity (never bare PID)**:
   - Every process is recorded as `(pid, create_filetime)` using Win32 `GetProcessTimes` (`CreationTime` 64-bit UTC FILETIME).
   - `execution_attempts` persists `(supervisor_pid, supervisor_create_filetime)` on claim, `(launcher_pid, launcher_create_filetime)` immediately after `Process.Start()`, and `(worker_pid, worker_create_filetime)` from the child's atomic `<runDir>\output\heartbeat.json` (cross-checked via `QueryInformationJobObject` / `GetProcessTimes`).
3. **Startup and pre-claim reconciliation without cross-supervisor theft**:
   - No database transaction spans child execution.
   - Before claiming queued work, the supervisor inspects `execution_attempts WHERE status = 'running'`:
     1. If `(supervisor_pid, supervisor_create_filetime)` still identifies a live OS process, **do not touch or reclaim** the attempt (another live supervisor owns it).
     2. Once the owning supervisor is confirmed gone, verify both `(launcher_pid, launcher_create_filetime)` and `(worker_pid, worker_create_filetime)` (checking both DB columns and `<runDir>\output\heartbeat.json` if written before crash) are absent or have non-matching `CreationTime`.
     3. Only after supervisor, launcher, and CUDA worker are all confirmed gone does recovery atomically transition the `running` attempt and its `processing_jobs` row (guarded by `fencing_token`) to `interrupted` (`failure_code = 'supervisor_interrupted'`). Abandoned runs are never silently re-executed; they become retryable only by explicit retry request.
   - Jobs committed in `queued` survive API and PostgreSQL restarts and are claimed in `queued_at ASC, job_id ASC` order when `LocalOcr:Enabled = true`.

---

## 3. Durable Attempts, Monotonic Fencing, Migration, and Grants (`F2-02`, `F2-03`, `F2-05`, `F2-07`)

### Schema and forward migration (`AddLocalExtraction` in schema `eledgercare`)
All tables are logged (`relpersistence = 'p'`) and all foreign keys use `ON DELETE RESTRICT`:

- **`documents` and `original_artifacts`**: unchanged from F1. Existing F1 rows, constraints, digests, and bytea payloads remain untouched.
- **Sequence `eledgercare.extraction_fencing_seq`**: `bigint` (`START WITH 1 INCREMENT BY 1 NO CYCLE`) providing globally monotonic ownership/fencing tokens.
- **`processing_jobs`** (forward-migrated in place):
  - Widens `ck_processing_jobs_status` to `status IN ('awaiting_extraction', 'queued', 'running', 'completed', 'failed', 'interrupted')`.
  - Adds `queued_at timestamptz NULL`, `updated_at timestamptz NOT NULL` (backfilled to `requested_at` for existing F1 rows), `attempt_count integer NOT NULL DEFAULT 0`, `latest_fencing_token bigint NOT NULL DEFAULT 0`, and `retried_from_attempt_id uuid NULL` (`FK -> execution_attempts(attempt_id) ON DELETE RESTRICT`).
  - Adds state-consistency check constraints (`awaiting_extraction` requires `queued_at IS NULL AND attempt_count = 0`; `queued` requires `queued_at IS NOT NULL`; `running`/`completed`/`failed`/`interrupted` require `attempt_count >= 1 AND latest_fencing_token >= 1`).
- **`execution_attempts`**:
  - `attempt_id uuid PK`, `job_id uuid NOT NULL FK`, `document_id uuid NOT NULL FK`, `attempt_number integer NOT NULL` (`UNIQUE (job_id, attempt_number)`), `fencing_token bigint NOT NULL` (`UNIQUE (fencing_token)`), `retried_from_attempt_id uuid NULL FK`.
  - Partial unique index **`ux_execution_attempts_one_running_per_job ON (job_id) WHERE status = 'running'`** preventing concurrent live attempts per job at the database boundary.
  - `status` (`running` | `completed` | `failed` | `interrupted`), `phase`, `run_directory_name`, `(supervisor_instance_id, supervisor_pid, supervisor_create_filetime)`, `(launcher_pid, launcher_create_filetime)`, `(worker_pid, worker_create_filetime)`, `started_at`, `last_heartbeat_at`, `ended_at`, `exit_code`, safe `failure_code`, safe `failure_detail`, optional bounded `diagnostic_raw_output_utf8` (for failed/truncated diagnostics only, never marked `completed`), and `diagnostic_metadata_json jsonb`.
- **`extraction_results`** (accepted results only):
  - `result_id uuid PK`, with unique accepted-result constraints **`UNIQUE (document_id)`**, **`UNIQUE (job_id)`**, **`UNIQUE (attempt_id)`**, and **`UNIQUE (fencing_token)`**.
  - `schema_version = 'eledgercare.local-extraction/1'`, `input_sha256 bytea` (32 B), `input_byte_length int`, `page_count int` (`1..3`).
  - Exact UTF-8 bytes stored losslessly in `raw_output_bytes bytea NOT NULL` (`octet_length <= 16777216`, validated strict UTF-8 before commit), `raw_output_byte_length int NOT NULL` (`= octet_length(raw_output_bytes)`), `raw_output_sha256 bytea NOT NULL` (32 B).
  - Full provenance: `model_repo_id`, `model_revision`, `model_manifest_sha256`, `dependency_lock_sha256`, `worker_source_digest`, `worker_config_digest`, `renderer_identity`, `generation_settings_json jsonb`, `finish_reason` (`= 'stop'`), `output_page_count` (`= page_count`), `started_at`, `completed_at`, `load_duration_ms`, `render_duration_ms`, `infer_duration_ms`, `total_duration_ms`, and `diagnostic_metadata_json jsonb`.

### Atomic fencing and HTTP replay/retry contract
- **Claim**: short `ReadCommitted` transaction (`SET LOCAL synchronous_commit = on`) locks oldest `queued` job via `FOR UPDATE SKIP LOCKED`, allocates `nextval('eledgercare.extraction_fencing_seq')`, updates `processing_jobs` (`status = 'running'`, `attempt_count + 1`, `latest_fencing_token`), and inserts `execution_attempts`.
- **Fenced publication / failure**: `UPDATE processing_jobs ... WHERE job_id = @jobId AND status = 'running' AND latest_fencing_token = @fencingToken` and `UPDATE execution_attempts ... WHERE attempt_id = @attemptId AND status = 'running' AND fencing_token = @fencingToken` execute inside the same transaction as `INSERT INTO extraction_results` (or failure update). If either `UPDATE` affects `0` rows, the attempt was fenced out and rolls back without mutating newer state.
- **HTTP semantics**:
  - `POST /api/documents` and `GET /api/submissions/{idempotencyKey}` keep the exact 7-property F1 `SubmissionReceiptResponse` (with live `status`).
  - `GET /api/documents/{documentId}` retains all 7 F1 fields and adds `admittedPageCount`, `extractionUrl`, `currentAttemptId`, and `acceptedResultId` (never loading `original_artifacts.bytes` or `extraction_results.raw_output_bytes`).
  - `POST /api/documents/{documentId}/extraction` (optional bounded JSON `{ "retryAttemptId"?: "<D-UUID>" }`):
    - Without `retryAttemptId`: `completed` -> `200 OK` (idempotent result identity, even when worker is disabled); `queued`/`running` -> `202 Accepted` (same active work); `failed`/`interrupted` -> `409 Conflict` (`retry_explicit_required`); `awaiting_extraction` -> validates `1..3` pages (`422 extraction_profile_unsupported` if `>3` pages, creating no attempt) and `LocalOcr:Enabled` (`503 extraction_disabled` if disabled), commits `queued`, returns `202 Accepted`.
    - With `retryAttemptId`: when `status IN ('failed', 'interrupted')` and latest attempt matches `retryAttemptId` (and profile/worker enabled), commits `queued` with `retried_from_attempt_id = retryAttemptId` while preserving all prior attempt rows -> `202 Accepted`; concurrent duplicate retry with matching `retried_from_attempt_id` while `queued`/`running` reconciles to `202 Accepted`; otherwise `409 Conflict`.
  - `GET /api/documents/{documentId}/extraction`: returns durable job, availability, attempt history summaries, and (when `completed`) unreviewed result + page-ordered safe view + provenance.

### Least-privilege runtime role (`deploy/dev/database/grant-runtime.sql`)
- `eledgercare_app` receives:
  - `SELECT, INSERT` only on `documents`, `original_artifacts`, and `extraction_results` (both original PDFs and accepted extraction results are immutable to the runtime role).
  - `SELECT, INSERT` plus column-restricted `UPDATE` on `processing_jobs` (`status`, `queued_at`, `updated_at`, `attempt_count`, `latest_fencing_token`, `retried_from_attempt_id`) and `execution_attempts` (progress/PID/heartbeat/outcome columns only).
  - `USAGE, SELECT` on `eledgercare.extraction_fencing_seq`.
  - Zero `DELETE`, `TRUNCATE`, `CREATE`, `REFERENCES`, `TRIGGER`, or `__ef_migrations_history` privileges; `eledgercare_migrator` remains separate.

---

## 4. Worker Execution, Guards, and Provenance Validation (`F2-01`, `F2-02`, `F2-06`)

- **Invocation**: `ProcessStartInfo` with `UseShellExecute = false`, `FileName = "<ReadOnlyQ0Root>\\venv\\Scripts\\python.exe"`, `ArgumentList = ["-I", "-B", "-X", "utf8", "-u", "<RepoRoot>\\workers\\local_ocr\\run_worker.py", "--request", "<runDir>\\request.json"]`.
- **Isolated offline environment**: explicit allowlist only (zero DB connection strings or credentials); `CUDA_DEVICE_ORDER=PCI_BUS_ID`, `CUDA_VISIBLE_DEVICES=<leased_gpu_uuid>`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_XET=1`, `PIP_NO_INDEX=1`; all writable caches (`TEMP`/`TMP`, `USERPROFILE`, `HF_HOME`, `HF_HUB_CACHE`, `TRANSFORMERS_CACHE`, `HF_MODULES_CACHE`, `TORCH_HOME`, `TRITON_CACHE_DIR`, `TORCHINDUCTOR_CACHE_DIR`, `CUDA_CACHE_PATH`) routed inside `<WritableRuntimeRoot>\runs\attempt-<attemptId>\cache\` so `C:\Users\jackg\eLedgerCare-Q0\WP-0005` remains strictly read-only.
- **Worker fail-closed checks**:
  1. CPython `3.12.10` (`Windows`/`AMD64`), exact 32-package lock match (`torch==2.13.0+cu130`, `torchvision==0.28.0+cu130` with `torchvision-local-sha256-TOFU`, `transformers==4.52.1`, `pypdfium2==5.15.2` / PDFium `159.0.8149.0`), `find_spec` for `triton`/`flash_attn`/`xformers` all `None`, single visible CUDA device matching leased UUID (`sm_120`).
  2. Pre-load verification of all 18 model objects (`Unlimited_OCR_2_04809669`) and separate `README.md` notice against `workers/local_ocr/manifests/model-files.json`, plus static AST proof that `eval` exists only inside `extract_coordinates_and_label` behind `if save_results and output_path:`.
  3. Post-load `HF_MODULES_CACHE` SHA-256 verification of all copied `.py` custom-code modules + PEP 669 `sys.monitoring` `SafetyTripwire` (`PY_START` raising `BaseException`) on `_uocr_save_results`, `process_image_with_refs`, `draw_bounding_boxes`, and `extract_coordinates_and_label`, plus forward-return progress counter and dense-fallback confirmation.
  4. Single-read hash-verified PDF rendering via `pypdfium2.PdfDocument(pdf_bytes)[i].render(scale=300.0 / 72.0).to_pil().convert("RGB")`, verifying page count `1..3` and safe per-page raster dimensions (`<= 6000 px` per axis before GPU submission).
  5. Frozen native `infer_multi` call (`prompt="Multi page parsing."`, `crop_mode=False`, `save_results=False`, `output_path=""`, `temperature=0.0`, `max_length=131072`, `max_new_tokens=8000*pages`, `max_page_tokens=20000`, `page_count_guard=True`, `no_repeat_ngram_size=35`, `ngram_window=1024 if pages > 1 else 128`, `ngram_whitelist_token_ids=None`, `base_size=1024`, `image_size=640`, `max_crops=16`, `dash_topm=16`, `tps_interval=0`, `test_compress=False`, `eval_mode=False`), verifying `prompt_len + 8000*pages <= 131072`, `finish_reason == "stop"`, and `num_pages_out == expected_pages == pages`.
- **Guards**: load `1800s`, 1-page call `1800s`, 2–3 page call `3600s`, forward-progress stall `300s` (5s heartbeat), raw output cap `16 MiB`, combined child stdout/stderr cap `64 MiB`, `C:\` free space `>= 20 GiB`, and owned `WritableRuntimeRoot` size `<= 4 GiB`.
- **`.NET` independent validation before publication**: verifies envelope schema `"eledgercare.local-extraction/1"`, exact `document_id`/`job_id`/`attempt_id`/`fencing_token`, `input_sha256`/`input_byte_length`/`page_count` against `original_artifacts`, `raw_output.utf8.bin` byte length (`<= 16 MiB`), strict UTF-8 decoding, recomputed SHA-256 == envelope `raw_output_sha256`, `finish_reason == "stop"`, `output_page_count == page_count`, `<PAGE>` marker count == `page_count`, and pinned model/manifest/lock/worker/config digests. Any mismatch records a bounded `failed` attempt and never publishes an accepted result.

---

## 5. Angular Result Screen and Safe Display Parsing (`web/`)

- **Port configurability for zero-edit independent review**: `web/proxy.conf.mjs`, `web/playwright.config.ts`, `web/e2e/owned-api.ts`, and `src/ELedgerCare.Api/appsettings.json` default to author ports (`API 5190`, `UI 4210`, `PostgreSQL 55434`) while honoring `ELEDGERCARE_API_PORT` / `ELEDGERCARE_UI_PORT` so `eld-next-reviewer` runs the exact frozen candidate on `5290 / 4310 / 55435` without editing source.
- **Honest states and controls on `/documents/:documentId`**:
  - Preserves all F1 receipt/document `data-testid`s and exact original download link.
  - Displays honest unavailable notice when `workerEnabled === false` and unsupported-profile notice when `admittedPageCount > 3`, without fabricated `%` progress or raw logs/tracebacks.
  - Polls `GET /api/documents/{id}/extraction` every `2s` only while `queued` or `running`, displaying attempt number, timestamps, and live phase.
  - Shows **Unreviewed raw extraction output** banner, model/revision/attempt/completed-UTC/duration/SHA-256 provenance summary, and 1..N page cards (`<PAGE>` split preserving page order, plain-text `<BLOCK>...<FORK>` + non-HTML state-machine `<table>/<tr>/<td>` cell text extraction + toggleable raw UTF-8 `<pre>{{ page.rawText }}</pre>`), bound strictly through Angular text nodes so `<script>` / event-handler strings in model output are inert text.

---

## 6. Owned Resources and Staged Verification Plan

### Observed baseline (read-only check at planning checkpoint)
- Host tools: `.NET SDK 10.0.403`, `Node.js v24.18.0`, `npm 11.16.0`; `C:` free space `56,796,155,904` bytes (`52.90 GiB`, above `20 GiB` floor).
- Author loopback ports `5190`, `4210`, `55434`: all unbound at inspection time (will be re-observed before every bind).
- Read-only cache/tool sources verified present (no secret files read): `eld-implementer\.local` (`tools\pgsql-18.7-1`, `nuget`, `npm-cache`) and `C:\Users\jackg\eLedgerCare-Q0\WP-0005` (`venv\Scripts\python.exe`, `models\Unlimited_OCR_2_04809669`, `notices\Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a\README.md`). `C:\Users\jackg\eLedgerCare-F2\WP-0006` is absent and will not be created before runtime release.

### Decisive verification matrix

| Stage / gate | Criteria covered | Real checks planned |
| --- | --- | --- |
| **Stage 1: CPU / PostgreSQL / Edge browser** (after `/002` acceptance + coordinator implementation release; `LocalOcr:Enabled = false` default, no GPU) | `F2-03`, `F2-04` (queue/fencing/boundary), `F2-06`, `F2-07`, F1 `DI-01..07` | 1. Initialize owned `.local` PostgreSQL 18.7 cluster on `127.0.0.1:55434` (copying verified `pgsql-18.7-1` subset `47c3deb9…` read-only, fresh `.local/secrets/pg-local.json`).<br>2. Full `dotnet test` + Python worker stdlib CPU unit tests (manifest/lock/AST/environment/envelope checks, product-research import isolation check).<br>3. Forward migration test: migrate fresh DB to F1 `20261114182147_InitialDurableIntake`, insert F1 rows, migrate forward to `AddLocalExtraction` + `grant-runtime.sql`, verify F1 data preservation and runtime role denials (`UPDATE`/`DELETE` on `original_artifacts`, `documents`, `extraction_results` -> `42501`).<br>4. Boundary & concurrency tests on real PostgreSQL: concurrent duplicate `POST .../extraction` race -> single queued/running attempt; `LOCK TABLE execution_attempts IN SHARE MODE` + abrupt API kill -> `queued` job survives restart; live-supervisor protection (second supervisor refuses to steal live PID+FILETIME); stale `fencing_token` publication/failure rejected after retry; `>3`-page PDF (`4` pages) -> `422` with `0` attempts; disabled worker -> `503` on new work while saved result reads/replays return `200`; service-boundary failure envelopes (malformed JSON, mismatched IDs/hashes/locks, `finish_reason='length'` truncation retained only as diagnostic, `>16 MiB` output cap, timeout/stall, `<script><img onerror>` payload).<br>5. Playwright Edge checks (`5190`/`4210`): all F1 intake specs + disabled-worker honest UI notice + unsupported-profile UI notice + XSS inertness check (`window.__xss` stays undefined when rendering hostile tags/tables). |
| **Stage 2: Exclusive GPU runtime verification** (after Stage 1 freeze + coordinator sole GPU lease and `C:\Users\jackg\eLedgerCare-F2\WP-0006\author` release) | `F2-01`, `F2-02`, `F2-03`, `F2-04` (real worker kill & retry), `F2-05` | 1. Pre-lease host/disk/process/GPU snapshot (`nvidia-smi` two-query check on `GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d`).<br>2. **Happy path 1-page raster (`F2-01`, `F2-02`)**: submit admitted dev `SYN-WO-01-v1-raster300.pdf` via browser/HTTP, request extraction, run real unmodified model to `completed`, verify original PDF SHA-256 unchanged, verify persisted `raw_output_bytes`/SHA-256/provenance match child `raw_output.utf8.bin`/`envelope.json` byte-for-byte, verify Edge result screen.<br>3. **Multi-page ordering (`F2-01`, `F2-02`)**: submit admitted dev `SYN-MP-01-v0-clean.pdf` (`3` pages), run real extraction to `completed`, verify `3` `<PAGE>` sections in exact `1..3` order (`MP01-P1`, `MP01-P2`, `MP01-P3`) in DB, API, and Edge.<br>4. **Real supervisor/worker forced termination & explicit retry (`F2-03`, `F2-04`)**: start real extraction, wait for live `(launcher_pid, worker_pid)` in DB, abruptly `TerminateProcess` the owned API process, verify Windows Job Object terminates both `launcher_pid` and `worker_pid` (zero orphan CUDA/Python process), restart API and verify transition to `interrupted` only after child absence check, then explicitly retry (`retryAttemptId`) to `completed` (`attempt_number = 2`) with `attempt_number = 1` preserved.<br>5. **Full restart & disabled-worker reopen (`F2-05`)**: restart API process and owned PostgreSQL (`pg_ctl stop -m fast` / `start`), start API with `LocalOcr:Enabled = false`, reopen completed documents in Edge and HTTP, verify exact raw bytes/identities/download and zero new Python/GPU execution.<br>6. Post-run worker absence check, Q0 18-object + notice integrity re-verification, explicit GPU lease return, evidence commit, and canonical `WP-0006 /003` publication. |

---

## 7. Blocking Contract Questions

**None.** No ambiguity in `docs/design/F2-local-extraction.md` blocks implementation once independent `/002` design review is accepted and bound by `eld-coordinator`.

For coordinator visibility at `/002` -> implementation release, this plan adopts four concrete contract-consistent resolutions within author discretion:
1. **3-page profile enabled**: `MaxExtractionPages` defaults to `3` (`1..3` pages), admitting both `SYN-WO-01-v1-raster300.pdf` (1-page raster) and `SYN-MP-01-v0-clean.pdf` (3-page ordering) while rejecting `4..50`-page F1 documents at `POST /api/documents/{documentId}/extraction` with `422 extraction_profile_unsupported`.
2. **F1 receipt compatibility**: `POST /api/documents` and `GET /api/submissions/{idempotencyKey}` keep the exact 7-key `SubmissionReceiptResponse`, while `GET /api/documents/{documentId}` retains those 7 keys and adds `admittedPageCount`, `extractionUrl`, `currentAttemptId`, and `acceptedResultId`.
3. **Idempotent request vs explicit retry on `POST /api/documents/{documentId}/extraction`**: empty/`{}` body requests initial work (`202`) or reconciles `queued`/`running` (`202`) and `completed` (`200`), returning `409` on `failed`/`interrupted`; `{ "retryAttemptId": "<uuid>" }` explicitly retries that `failed`/`interrupted` attempt (`202`) and reconciles duplicate retry calls naming the same `retryAttemptId`.
4. **Disabled-worker behavior**: with `LocalOcr:Enabled = false` (default), saved `completed` results remain readable (`GET`) and replayable (`POST -> 200`), while new/retry extraction `POST` requests return `503 extraction_disabled` without queuing unserviceable work, and the UI surfaces honest unavailable state.
