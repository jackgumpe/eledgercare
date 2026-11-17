# WP-0012 / 002 — Independent Audit of Author `/001` & Reviewer `v3` Guard Reconciliation

- **Reviewer / Agent ID:** `eld-f4-reviewer`
- **Session / Model / Effort:** Antigravity CLI conversation `61105d43-7706-45f2-9176-69d3256248e0` — `Gemini 4 Carbon (High)`, `high` effort (backend checkpoint identifier not separately exposed)
- **Owned Worktree / Branch:** `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f4-reviewer` on `review/wp-0012-product-rehearsal`
- **Dispatch Authority (Read-Only Main Checkout):** `7af4cd0e2e8ffbcb9176fc78508b6cd601c16fc0` (`docs/kickoffs/WP-0012-eld-f4-reviewer-preparation-review.md`, incorporating coordinator helper inspection at `dec2d6476b770b9b5ee1774100d3df391c8c53d5`)
- **Merged Branch Base:** `cb4189aced6f38b269d8a90fa362b92058852bd0` (clean merge of reviewer initial CPU preparation `7f3f8626489e898a50d275e93ee904660e97fd59` and bound author `/001` publication `165b2421b297bf49181c91af8d05a449ad69e9b5`; Root's combined R&D branch was not merged)
- **Reviewed Author `/001` Revisions (`eld-f4-implementer`):**
  - Frozen deliverable: `ad5202a029a7a86bea5fa3e3d97760d0a9cc673a` (`9` added paths under `docs/implementation/WP-0012/eld-f4-implementer/`)
  - Post-freeze CPU evidence & inventory: `32465da577237827c3ac9d8ed5ee608c8e5668cf` (`14` added paths)
  - Canonical report `/001`: `165b2421b297bf49181c91af8d05a449ad69e9b5` ([001_2026-11-17_implementation_eld-f4-implementer.md](../../../../agent-reports/eld-f4-implementer/WP-0012/001_2026-11-17_implementation_eld-f4-implementer.md))
- **Disposition on Author `/001`:** **`changes-requested`** (zero defects in unchanged accepted production/worker code; three bounded rehearsal-helper defects `F12-B1`..`F12-B3` and one minor Phase B assertion gap `F12-D4` require author correction before `eld-coordinator` issues the author `/003` GPU lease)
- **Live GPU / Model Execution Status:** **Not executed (`CPU-only`).** Neither author `/003` nor reviewer `/004` has been run; CPU preparation and guard tests do not establish live OCR or end-to-end model runtime success.

---

## 1. Independent Source, Runbook, & Evidence Review of `eld-f4-implementer` `WP-0012 / 001`

### 1.1 Verified Criteria (`Pass` on CPU Scope)

1. **Unchanged Accepted Production & Worker Code (`WP12-RC-01`):**
   - `git diff 47fbc7612e4a08cf1960ad7ac01bd2843ae645e5..165b2421b297bf49181c91af8d05a449ad69e9b5` adds `24` paths exclusively under `docs/implementation/WP-0012/eld-f4-implementer/**` (`23` files) and `docs/agent-reports/eld-f4-implementer/WP-0012/**` (`1` report-only commit), leaving all `3,615` authority-base paths (`src/`, `web/`, `tests/`, `deploy/`, `ELedgerCare.slnx`, `workers/local_ocr/`, `research/`, `evaluation/`, `qualification/`, `INDEX.md`, `CURRENT.md`, `AGENTS.md`) bit-for-bit identical to `47fbc7612e4a08cf1960ad7ac01bd2843ae645e5` / `73c8d3c4f0a00312e3444328331b6cbd6406e882`.
   - Python AST inspection across all author `.py` helpers confirms `0` imports of `torch`, `transformers`, `safetensors`, `accelerate`, `pypdfium2`, `PIL`, `torchvision`, or `research`/`evaluation`/`qualification` packages. `node --check` passes cleanly on [drive_rehearsal_edge.mjs](../../../../implementation/WP-0012/eld-f4-implementer/helpers/drive_rehearsal_edge.mjs).

2. **Browser Workflow, Source-Grounded Corrections, Unknowns, Draft Isolation, Search, & Pinned History (`WP12-RC-05` — Static Design Inspection of Unrun Live Steps):**
   - Inspected [drive_rehearsal_edge.mjs](../../../../implementation/WP-0012/eld-f4-implementer/helpers/drive_rehearsal_edge.mjs) (`695` lines) against accepted PDF fixtures (`SYN-WO-01-v1-raster300.pdf` SHA-256 `47b2df6a...`, `1` page; `SYN-MP-01-v0-clean.pdf` SHA-256 `15e39351...`, `3` pages) and Angular routes (`IntakePage`, `DocumentPage`, `DocumentReviewPage`, `ArchivePage`):
     - Enforces `liveExtractionPosts <= 2` (`0` warmups, `0` retries) and throws immediately if either extraction response is non-`200` or `status !== 'succeeded'`.
     - Verifies persisted original byte length, SHA-256, `206 Partial Content` PDF preview, raw worker payload SHA-256, `modelRevision === '0480966938291445591f69f08a13b041c073a96a'`, `dependencyLockSha256`, `workerSourceSha256`, and page-specific `workerConfigSha256` (`579aad63...` for `1p`, `ac90459c...` for `3p`).
     - **`SYN-WO-01` human review:** Edits `parts_replaced` to `"Dual run capacitor 45/5 MFD 440V (CAP-45-5MFD-440V)"` with verbatim quote `"Replaced dual run capacitor 45/5 MFD 440V (part CAP-45-5MFD-440V)"` (page `1`) as `Reviewed #1`, then saves `Draft #2` (`technician_name = "M. Callahan — Lead HVAC Tech (QA Draft Hold)"`), verifying `Reviewed #1` remains active in `reviewed` archive search while `Draft #2` stays isolated from `reviewed` search and survives reopening pinned `/review/revisions/1`.
     - **`SYN-MP-01` human review:** Marks `vendor_or_assignee` (`missing_on_document`) and `completion_date` (`illegible`) as explicit `unknown` without fabricated text, edits `customer_or_site` to `"Maple Ridge Commons Asset Operations"` (`page 1`) and `parts_replaced` to `"Evaporator fan assembly — Walk-in Refrigerator Evaporator (see Page 2)"` (`page 2`) as `Reviewed #1`, and verifies `#page=2` PDF preview fragment navigation and source-mode search differentiation (`machine` vs `reviewed` vs `all`).

3. **Preserved Databases, Privilege Denials, & Author CPU Dry Run (`WP12-RC-06`):**
   - Independently verified all `23` SHA-256 digests in author `inventory.json`, re-executed all `18` `Wp0012PreparationGuardTests` in memory against pinned `ad5202a029a7a86bea5fa3e3d97760d0a9cc673a` (`18/18` passed), verified `13/13` SQLSTATE `42501` runtime-role DDL/sequence denials, verified author retained F4 database snapshots (`76e7970b...`, `ad4f44bc...`, `78f0f273...`) and empty `eledgercare_demo_wp0012_author` (`0` rows across `10` tables), and confirmed `0` local credentials in author logs/reports. Author ports (`5590/4610/55438`), database, and demo root were never started or modified by reviewer checks.

---

### 1.2 Blocking Rehearsal-Helper Defects Requiring Author Correction (`Status: changes-requested`)

#### `F12-B1` (Blocking — `WP12-RC-04` / `WP12-RC-07`): Partial-Startup Failure in `start_api_and_ui` Leaks an Alive Orphaned `dotnet` API Process and Open Log File Handle
- **Location:** [run_wp0012_rehearsal.py](../../../../implementation/WP-0012/eld-f4-implementer/helpers/run_wp0012_rehearsal.py) lines `846–906` (`start_api_and_ui`), called from `run_cpu_dry_run` (`L974, L1022`) and `execute_live_rehearsal` (`L1167, L1254`).
- **Mechanism:**
  1. `start_api_and_ui` opens `api_fh` (`L846`) and spawns `api_proc = subprocess.Popen(["dotnet", str(api_dll)], ...)` (`L847`, configured with `LocalOcr__Enabled=true` and `LocalOcr__LeasedGpuUuid=GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d` during Live Phase A).
  2. If `api_proc` does not bind `5590` within `45s` (`L867–869`), `api_fh.close()` runs and `RuntimeError("Owned API did not bind 5590 within 45s")` is raised **without terminating `api_proc`**.
  3. Worse, once `api_proc` binds `5590`, `start_api_and_ui` spawns `ui_proc` (`node ... ng.js serve --port 4610`, `L873`). If `Popen` raises, `ui_proc` exits early (`L887–889`), or `ui_proc` times out waiting for `200` on `4610` (`L897–899` — where `ui_proc` itself is also not killed!), `start_api_and_ui` raises `RuntimeError` **before returning `(api_proc, ..., ui_proc, ...)`** and without closing `api_fh`.
  4. In both callers (`run_cpu_dry_run` `L947–950` / `L1052–1053` and `execute_live_rehearsal` `L1139–1142` / `L1343–1344`), `api_proc` and `ui_proc` are still `None` when `start_api_and_ui` raises, so `finally: stop_proc(ui_proc, ui_fh); stop_proc(api_proc, api_fh)` is a complete no-op (`if proc is None: return`).
- **Deterministic CPU Reproduction (`verify_author_001_and_reviewer_v3_cpu.py`):**
  - Reproduced both failure modes purely on CPU using benign short-lived Python child processes (without binding `5590`/`4610`):
    - **Case A (`ui_proc` early exit `1`):** `start_api_and_ui` raised `RuntimeError("Owned UI exited early (1)...")`, leaving `api_proc` **alive in Win32 process table** (`api_proc_leaked_alive_after_exception: true`) and `api_fh` **open** (`api_fh_leaked_open_after_exception: true`). (Our test harness immediately reaped the test child in its own `finally`.)
    - **Case B (`api_proc` `45s` bind timeout):** `start_api_and_ui` raised `RuntimeError("Owned API did not bind 5590 within 45s")`, leaving `api_proc` **alive** (`api_proc_leaked_alive_after_exception: true`).
- **Required Author Fix:** Wrap `start_api_and_ui` in an internal `try/except Exception:` that calls `stop_proc(ui_proc, ui_fh)` and `stop_proc(api_proc, api_fh)` (verifying exact PID/creation identity) before re-raising.

#### `F12-B2` (Blocking — `WP12-RC-04` / `WP12-RC-07`): Stop-on-Failure Path in `execute_live_rehearsal` Skips Worker/Launcher Exit Verification, Port-Unbound Audit, Log Credential Scrubbing, and `owner-lease-return.json`
- **Location:** [run_wp0012_rehearsal.py](../../../../implementation/WP-0012/eld-f4-implementer/helpers/run_wp0012_rehearsal.py) lines `1129` and `1211–1350`.
- **Mechanism:**
  1. Under `WP-0012` authority, if Attempt #1 fails (`cp_a.returncode != 0` at `L1211`) or Phase B fails (`cp_b.returncode != 0` at `L1292`), the helper must stop immediately (`0` retries) **and** still verify clean process/GPU/port return and emit an honest lease-return record.
  2. Currently, raising `RuntimeError` at `L1212` or `L1293` jumps straight to `finally:` (`L1340–1350`), which stops `sampler`, `ui_proc`, `api_proc`, and PostgreSQL `55438`, **bypassing**:
     - querying `persisted_attempts` before PG stops (`L1215`) and verifying `launcher_pid` / `worker_pid` termination (`L1225–1231`),
     - checking `count_ocr_worker_processes() == 0` (`L1233`; also add a pre-launch `count_ocr_worker_processes() == 0` check before Phase A),
     - verifying `assert_ports_unbound((5590, 4610, 55438))` (`L1317`) and post-run Q0 model immutability (`L1319`),
     - scrubbing `pg-local.json` credentials from `logs_dir/*.log` in case a startup exception echoed `ConnectionStrings__Runtime`, and
     - writing `owner-lease-return.json` (`L1322–1338`) recording `status: "failed_stopped"`, `attempts_executed`, and verified resource return.
  3. Additionally, `ev_out_dir.mkdir(parents=True, exist_ok=True)` (`L1129`) does not refuse a non-empty `ev_out_dir`, risking overwrite of retained failure logs if accidentally re-invoked with the same `lease_id`.
- **Deterministic CPU Reproduction (`verify_author_001_and_reviewer_v3_cpu.py`):**
  - Simulated `cp_a.returncode == 1` in an isolated temporary directory: `execute_live_rehearsal` raised `RuntimeError("Live Phase A stopped/failed (exit=1)...")` with `owner_lease_return_json_written_on_failure: false` and `post_failure_worker_process_checks_executed: 0`.

#### `F12-B3` (Blocking — `WP12-RC-02`): Release-Contract Key Mismatch Between Canonical `/001` Handoff (`L64, L114`) and `_extract_independent_review_002_sha`
- **Location:** [001_2026-11-17_implementation_eld-f4-implementer.md](../../../../agent-reports/eld-f4-implementer/WP-0012/001_2026-11-17_implementation_eld-f4-implementer.md) lines `64` & `114` vs. [run_wp0012_rehearsal.py](../../../../implementation/WP-0012/eld-f4-implementer/helpers/run_wp0012_rehearsal.py) lines `406–413`.
- **Mechanism:**
  - Canonical `/001` (`L64` and `L114` Handoff) explicitly instructs `eld-coordinator` to bind `"independent_preparation_review_002_sha"` in the coordinator release JSON, whereas `_extract_independent_review_002_sha` only checks `("accepted_preparation_review", "accepted_review_002", "independent_review_002", "accepted_002", "accepted_review", "preparation_review")` and raises `RehearsalGuardError("Release JSON is missing required independent /002 review binding...")` when `"independent_preparation_review_002_sha"` is supplied.
- **Required Author Fix:** Add `"independent_preparation_review_002_sha"` to `_extract_independent_review_002_sha` (`L407`) so both the `RUNBOOK.md` key (`"accepted_review_002"`) and the `/001` Handoff key (`"independent_preparation_review_002_sha"`) work seamlessly.

---

### 1.3 Non-Blocking Prose Discrepancies & Minor Assertion Gap Recorded Against Immutable `/001` (`F12-D1`..`F12-D4`)

Published `/001` (`165b2421b297bf49181c91af8d05a449ad69e9b5`) is immutable; the following discrepancies between `/001` prose and executable source (`ad5202a0`) are recorded here for the canonical packet ledger:
- **`F12-D1` (CLI Flag Shorthand in `/001` Prose):** `/001` (`L42, L64`) writes `run_wp0012_rehearsal.py --execute-live --release <json|path>` (which exits `2: unrecognized arguments: --release`), whereas [run_wp0012_rehearsal.py](../../../../implementation/WP-0012/eld-f4-implementer/helpers/run_wp0012_rehearsal.py) (`L1361–1375`) and [RUNBOOK.md](../../../../implementation/WP-0012/eld-f4-implementer/RUNBOOK.md) (`L32, L49`) require `--execute-live --release-commit <40-hex> --release-path <git-rel-json>`.
- **`F12-D2` (Edge Mode Shorthand in `/001` Prose):** `/001` (`L41`) writes `live-phase1` / `live-phase2`, whereas [drive_rehearsal_edge.mjs](../../../../implementation/WP-0012/eld-f4-implementer/helpers/drive_rehearsal_edge.mjs) (`L470, L658`) and `RUNBOOK.md` (`L51`) implement `live-phase-a` and `live-phase-b-reopen`.
- **`F12-D3` (Overstated Validation Descriptions in `/001` Prose):**
  1. `/001` (`L64`) states the `/002` review SHA is verified via `git merge-base --is-ancestor`; `validate_release_contract` (`L518–520`) actually checks `commit_exists_fn(rev_sha)` (`git cat-file -e <sha>^{commit}`), which is the right check since an unmerged reviewer commit on `review/wp-0012-product-rehearsal` need not be an ancestor of the author branch before coordinator merge, whereas `git_is_ancestor` (`L512`) checks `47fbc761..actual_head`.
  2. `/001` (`L79`, Step `04`) describes the `18` unit tests in [validate_wp0012_preparation_cpu.py](../../../../implementation/WP-0012/eld-f4-implementer/helpers/validate_wp0012_preparation_cpu.py) as testing dirty worktrees, `>4 GiB` runtime usage, `<20 GiB` free disk, and symlinked paths, whereas `_validate()` sets `require_clean_worktree=False`, `test_14` mutates JSON contract integers (`storage_cap_bytes` / `free_floor_bytes`) rather than live disk usage, and symlinked-path rejection is implemented in `inspect_readonly_q0_and_demo_roots_cpu` (`L290–308`) rather than unit-tested in `Wp0012PreparationGuardTests`.
  3. `/001` (`L54`) refers to `archive_document_projections`; actual schema tables verified in `validation-summary.json` are `archive_result_projections` and `archive_projection_units`.
- **`F12-D4` (Minor Assertion Tightening for Author Correction Pass):** In [drive_rehearsal_edge.mjs](../../../../implementation/WP-0012/eld-f4-implementer/helpers/drive_rehearsal_edge.mjs) (`L675`), `live-phase-b-reopen` records literal `ocrEnabledDuringReopen: false` without asserting `extWo.body?.workerEnabled === false && extMp.body?.workerEnabled === false` from the already-fetched `/api/documents/{id}/extraction` payloads (`L646–647`). Adding that assertion alongside `F12-B1`..`F12-B3` will directly confirm `LocalOcr__Enabled=false` via the API contract during Phase B reopen.

---

## 2. Reconciliation of Coordinator Findings on Future-`/004` Reviewer Helper (`v3`)

All `30` initial preparation artifacts under [preparation/](../preparation/README.md) (`7f3f8626489e898a50d275e93ee904660e97fd59` / helper `c09cf1aa8282e440e364c6020152dd257355643b`) remain 100% untouched. In [run_wp0012_reviewer_rehearsal_v3.py](helpers/run_wp0012_reviewer_rehearsal_v3.py), all three coordinator findings (`docs/kickoffs/WP-0012-eld-f4-reviewer-preparation-review.md` `L15–23`) are reconciled for future `/004` execution:

1. **`RG-01` — Exact Git Release, Clean Executing `HEAD`/Helper Binding, Upstream `/002` + `/003` + Returned-Lease Bindings, Exact GPU UUID, Expiry Window, & Hashed Pre-Lease Observations:**
   - Live mode (`--mode live-leased-rehearsal`) and CPU contract check (`--mode validate-release-cpu`) load the release envelope strictly from an immutable Git blob (`git cat-file -p <release-commit>:<release-path>` under `docs/coordination/WP-0012/*.json`).
   - Rejects preparation/authority/historical commits (`47fbc761`, `7af4cd0e`, `dec2d647`, `73c8d3c4`, `c1fed680`, `ad5202a0`, `165b2421`, `c09cf1aa`, `7f3f8626`, `cb4189ac`), any envelope with `synthetic_test_only: true` in live mode, dirty worktrees, branch `!= review/wp-0012-product-rehearsal`, `executing_head != git rev-parse HEAD`, uncommitted byte drift on `run_wp0012_reviewer_rehearsal_v3.py` or [drive_wp0012_edge_workflow.mjs](../preparation/helpers/drive_wp0012_edge_workflow.mjs), drifted `product_tree_objects` or `pinned_digests`, non-exact `gpu_uuid != GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d`, invalid/future/expired/`>21,600s`/`<300s` remaining lease windows, `max_model_attempts != 2`, missing/unverified Git commit bindings for `accepted_review_002`, `accepted_author_003`, or `author_lease_return`, or SHA-256 mismatches on coordinator pre-lease observation blobs (`ownership-before.json` + `model-before.json`, or `host-before.json` + `processes-before.json` + `model-before.json`).
   - Positive CPU unit tests in [verify_author_001_and_reviewer_v3_cpu.py](helpers/verify_author_001_and_reviewer_v3_cpu.py) explicitly set `"synthetic_test_only": true` (`allow_synthetic_test_only=True` in unit-test harness only) and prove that `allow_synthetic_test_only=False` rejects synthetic envelopes immediately.

2. **`RG-02` — Windows Desktop/WDDM GPU Sharing vs. Unaccounted Competing Model Ownership:**
   - `evaluate_gpu_and_model_ownership` aligns directly with `docs/coordination/WP-0012-0013/observe_ownership.ps1` (`6360ed4`):
     - Never requires `nvidia-smi --query-compute-apps` to be empty, never claims hardware exclusivity (`"hardware_exclusivity_claimed": false`), and never infers ownership from low VRAM usage.
     - Classifies benign Windows desktop/WDDM processes (`dwm.exe`, `explorer.exe`, `msedge.exe`, `SearchHost.exe`, etc.) and non-model PIDs accounted for in the coordinator's pre-lease observation blob under `wddm_desktop_sharing_entries`.
     - Fails closed (`CompetingModelOwnershipError`) on any unaccounted competing model/OCR/inference workload in GPU compute rows, host process table, or `ollama ps` (`python*` worker/harness/qualification `mapping_v1`/`mapping_v2`/`coverage_v1`/`baseline`/`q0`, `ollama`, `llama-server`, `llama-cli`, `vllm`, `lmstudio`, `koboldcpp`, or any unaccounted unknown CUDA binary).

3. **`RG-03` — Brand-New Refusing-Overwrite Output Destinations & Atomic Partial-Startup Cleanup:**
   - `run_wp0012_reviewer_rehearsal_v3.py` has **no** default paths pointing into `preparation/` or `author-001-review/`. `guard_new_non_overwriting_output_targets` explicitly rejects `docs/reviews/WP-0012/eld-f4-reviewer/preparation/**`, `docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/**`, historical `WP-0006`/`0008`/`0010` review directories, author/R&D directories, symlinks/reparse points, any existing output JSON (`summary`, `edge-live-phase1.json`, `edge-live-phase2-post-restart.json`, `q0-check`, `resource-return`), or any non-empty `logs`/`screenshots` directory (`FileExistsError`).
   - `start_owned_services_atomic` (`L981–1071`) wraps owned API (`5690`) and UI (`4710`) startup in an internal `try/except` that terminates any already-spawned child (`PID` + `startUtc` verified) on partial startup failure (`test_20`, `test_21`), and `live-leased-rehearsal` writes a sanitized `resource-return.json` on both completion and first-failure stop paths.
