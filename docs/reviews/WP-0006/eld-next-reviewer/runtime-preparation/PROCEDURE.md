# WP-0006 Independent F2 Runtime Verification & Safe Evidence Capture Procedure (`eld-next-reviewer`)

> [!IMPORTANT]
> This document prepares **only** the bounded independent runtime verification procedure and CPU-validated driver for `eld-next-reviewer` (`101b19cf-3133-4ead-91cb-9ca6068e3e72`, `gemini-4-carbon-high/high`) under coordinator authority `0e16cfd473b1dab3b6109c6fba8e7425e91c4ae5` ([WP-0006-eld-next-reviewer-runtime-preparation.md](../../../../../docs/kickoffs/WP-0006-eld-next-reviewer-runtime-preparation.md)).
> Neither this preparation checkpoint, nor accepted source reconciliation `82e8f732afbf038bfb5b6c560f1b1219aaa4e40f`, nor any author driver/lease (`882438d037fdb754df487c1d20a8bc958f81aeb2`, `WP-0006-author-runtime-*`, or active B0 lease `WP-0007-author-heldout-20261116T145544Z`) authorizes reviewer GPU/model execution. Canonical `WP-0006 /004` (`docs/agent-reports/eld-next-reviewer/WP-0006/004_2026-11-16_review_eld-next-reviewer.md`) remains **held** until separately released real independent execution and full disposition on actual author `/003`.

## 1. Provenance, Attribution, and Immutable Prior Artifacts

- **Reviewed & Accepted Stage 1 Product Source**: `8a73b7a5dab51e3ccf803aceedded4929529dd35` (`src` `73d0146b...`, `workers/local_ocr` `1ed60936...`, `workers/ocr` `493935fa...`, `web` `f0877a00...`, `tests` `5ad9bd15...`, `deploy` `dade6a38...`, `ELedgerCare.slnx` `c00c2bc5...`).
- **Accepted Design Review (`/002`, Immutable)**: `e2452e1ab3d8937868c07ffb30ce430715b5be78` ([002_2026-11-16_review_eld-next-reviewer.md](../../../../../docs/agent-reports/eld-next-reviewer/WP-0006/002_2026-11-16_review_eld-next-reviewer.md)).
- **Accepted Source/CPU/Child/PostgreSQL Reconciliation (Immutable)**: `82e8f732afbf038bfb5b6c560f1b1219aaa4e40f` ([source-reconciliation/README.md](../source-reconciliation/README.md); prior Stage 1 findings `10193e2c904f99cfc23c97367f1e5d881b0630f2` and resource preparation `2035412a7353511f5ef46f930ffb457f19fe8f5b` also preserved intact).
- **Attributed Structural Reference**: Inspected `eld-f2-implementer`'s audited `v2` preparation (`882438d037fdb754df487c1d20a8bc958f81aeb2`, helper freeze `5b33924b0a95db02731dcfa344131592e31fce30`, [runtime-corrected-preparation/README.md](../../../../../docs/implementation/WP-0006/runtime-corrected-preparation/README.md)). All reviewer release-binding rules, reviewer port/root/DB isolation, SQL/DOM/process assertions, Q0/author determinism cross-checks, and evidence packaging in `docs/reviews/WP-0006/eld-next-reviewer/runtime-preparation/**` are independently authored and owned by `eld-next-reviewer`.

## 2. Owned Reviewer Resources, Guard Limits, and Paths

| Resource / Parameter | Bound Reviewer Value |
| --- | --- |
| Reviewer driver | [helpers/run_f2_reviewer_runtime.py](helpers/run_f2_reviewer_runtime.py) |
| Reviewer Microsoft Edge UI verifier | [helpers/verify_ui_reviewer_real_results.mjs](helpers/verify_ui_reviewer_real_results.mjs) |
| CPU-only preparation validator | [helpers/validate_reviewer_runtime_prep_cpu.py](helpers/validate_reviewer_runtime_prep_cpu.py) |
| Loopback ports (reviewer-owned ONLY) | API `127.0.0.1:5290` · Angular UI `127.0.0.1:4310` · PostgreSQL `18.7` `127.0.0.1:55435` |
| Owned PostgreSQL cluster & database | `.local\postgres-data` (`.local\secrets\pg-local.json`, zero secrets printed/committed) · fresh DB `eledgercare_f2_runtime_reviewer` |
| Future writable reviewer runtime root | `C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer` (**never created or touched during preparation**) |
| Read-only Q0 model & Python venv root | `C:\Users\jackg\eLedgerCare-Q0\WP-0005` (`baidu/Unlimited-OCR-2` @ `0480966938291445591f69f08a13b041c073a96a`, `18` runtime objects + notice) |
| Storage & output ceilings | `<= 4 GiB` (`4,294,967,296` B) reviewer runtime root · `>= 20 GiB` (`21,474,836,480` B) free disk floor · `<= 16 MiB` raw output · `<= 64 MiB` child logs |
| Execution timeout ceilings | `1,800 s` model load · `1,800 s` 1-page inference · `3,600 s` multi-page (`2..3p`) inference · `300 s` forward-progress stall · `6 h` (`21,600 s`) total session cap |
| Future live scratch & Git evidence paths | `.scratch/stage2-reviewer-runtime/**` -> packaged to `docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/**`, followed by canonical `docs/agent-reports/eld-next-reviewer/WP-0006/004_2026-11-16_review_eld-next-reviewer.md` |

## 3. Fail-Closed Future Coordinator Release Validation (`validate_reviewer_release_contract`)

Before starting PostgreSQL, `ELedgerCare.Api`, Microsoft Edge, or any model process, `run_f2_reviewer_runtime.py` reads `<release_commit>:<release_path>` from immutable Git objects and enforces:

1. **Fresh Reviewer Authority & Active Sole Lease**:
   - Rejects all historical/returned/preparation commits (`d106db76...`, `9ae311e3...`, `97e65bed...`, `717a7689...`, `2c549274...`, `2ce3366d...`, `35e2f44d...`, `0e16cfd4...`).
   - Requires `owner == "eld-next-reviewer"`, `conversation_id == "101b19cf-3133-4ead-91cb-9ca6068e3e72"`, `model == "gemini-4-carbon-high"`, `effort == "high"`.
   - Requires `lease_id` starting with `"WP-0006-"` and containing `"reviewer"` (rejecting any author lease or `WP-0007` lease), `gpu_uuid == "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"`, `released_utc <= now < expires_utc` with `>= 300 s` remaining and `<= 21,600 s` (`6 h`) total lease window, plus verified pre-lease `host-before.json`, `processes-before.json`, and `model-before.json` Git blobs.
2. **Clean Executing HEAD + Ancestry + Exact Product/Protected Tree OIDs (No `HEAD~1` Assumption)**:
   - Verifies `git status --porcelain == ""`, `git rev-parse HEAD == release["executing_head"]`, and rejects all pre-runtime-preparation reviewer commits and all author commits.
   - Verifies `source_commit` (`8a73b7a5dab51e3ccf803aceedded4929529dd35`), `accepted_design_review` (`e2452e1ab3d8937868c07ffb30ce430715b5be78`), and `accepted_source_review` (`82e8f732afbf038bfb5b6c560f1b1219aaa4e40f`) are all Git ancestors of `executing_head`.
   - Verifies zero forbidden path changes since `8a73b7a5...`, exact product tree OIDs (`src`, `workers/local_ocr`, `workers/ocr`, `web`, `tests`, `deploy`, `ELedgerCare.slnx`) at both `source_commit` and `executing_head`, unchanged `qualification/q0`, `research`, `evaluation`, and immutable prior reviewer trees (`design`, `preparation`, `implementation`, `source-reconciliation`, `/002`), and absence of canonical `/004` prior to completion.
3. **Actual Completed Author Runtime Evidence & Author `/003` Bindings**:
   - Requires a valid 40-hex `author_runtime_evidence` commit SHA present in Git (rejecting pre-model failure `7280463a...`, Stage 1 `6faec9bf...`, source-response `386d5c30...`, and driver-prep `5b33924b...` / `882438d0...`).
   - Requires a valid 40-hex `author_003` commit SHA present in Git containing `docs/agent-reports/eld-f2-implementer/WP-0006/003_2026-11-16_implementation_eld-f2-implementer.md` (unless the coordinator explicitly sets `allow_bounded_sequencing_without_003_prose: true` for runtime start, in which case final `/004` publication remains held until actual `/003` is merged and inspected).
4. **Pinned Digests, Reviewer Isolation, & Finite 4-Attempt Matrix**:
   - Verifies both release JSON and live worktree computations match `worker_source_sha256 == c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54`, `model_manifest_sha256 == 0df07bc6...`, `dependency_lock_sha256 == 582071bf...`, 1p/2p/3p `worker_config` digests, and admitted DEV fixture digests (`F1-SWO-001`, `SYN-WO-01-v1-raster300`, `SYN-MP-01-v0-clean`).
   - Enforces `ports == {"api": 5290, "ui": 4310, "postgres": 55435}`, `runtime_root == C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer`, `max_model_attempts == 4` (`[1, 1, 2, 0]`, zero warmups, zero automatic retries, zero holdouts), and byte-identical committed helpers.

## 4. Bounded 4-Attempt Independent Runtime Matrix (`F2-01..07`)

No mock worker and no manually inserted database row can satisfy acceptance; every completed result must originate from the real `ELedgerCare.Api` -> `WindowsJobProcess` -> isolated Q0 `venv\Scripts\python.exe -I` -> `workers/local_ocr/run_worker.py` -> unmodified `baidu/Unlimited-OCR-2` pipeline:

1. **Scenario 1 (Attempt #1 of 4 — `SYN-WO-01-v1-raster300.pdf`, 1 page)**:
   - Submit via `POST /api/documents` (`201`), trigger `POST /api/documents/{id}/extraction` (`202`), observe live `heartbeat.json` + GPU compute occupancy, and verify completion (`status == "completed"`, `finish_reason == "stop"`, `page_count == 1`, positive load/render/infer/total durations, real `(launcher_pid, worker_pid)` creation filetimes).
   - Verify SHA-256 parity across disk `raw_output.utf8.bin`, `envelope.json`, PostgreSQL `sha256(raw_output_bytes)` (`bytea`), `GET /extraction` JSON, and headless Microsoft Edge (`4310` -> `5290`) unreviewed result view + original PDF download.
2. **Scenario 2 (Attempt #2 of 4 — `SYN-MP-01-v0-clean.pdf`, 3 pages)**:
   - Submit and execute 3-page extraction; verify exact `1..3` page ordering (`[1, 2, 3]`), 3-page config digest (`ac90459c...`), raw `bytea` parity, and descriptive byte/SHA-256 comparison against qualified Q0 `F07.warm1.raw.txt` (`893bf578...`) and author `/003` outputs.
3. **Scenario 3 (Attempt #3 Interrupted + Attempt #4 Explicit Retry — fresh `SYN-WO-01-v1-raster300.pdf`)**:
   - Trigger extraction on a fresh document, wait until `heartbeat.json` reports `phase == "inferring"` and `forward_progress >= 1` with `supervisor`, `launcher`, and `worker` verified alive by `(PID, CreateFileTime)`.
   - Terminate **only** the single `ELedgerCare.Api` supervisor process via Win32 `TerminateProcess` (non-recursive); verify kernel Job Object (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) kills both `launcher` and `worker` and releases CUDA compute memory, with `0` `extraction_results` rows published.
   - Start `ELedgerCare.Api` #2 (`5290`), verify reconciliation of Attempt #1 to `interrupted` (`supervisor_interrupted`), confirm `0` automatic retries occur and empty `POST /extraction` returns `409 retry_explicit_required`, then submit explicit `{"retryAttemptId": attempt1_id}` -> Attempt #4 completes with strictly higher `fencing_token` while Attempt #1 remains preserved as `interrupted` (and compare Attempt #4 raw SHA-256 against Scenario 1 Attempt #1 for within-session determinism).
4. **Scenario 4 (`0` Model Attempts — API + PostgreSQL `18.7` Fast Restart & `LocalOcr:Enabled=false` Saved-Result Reopen)**:
   - Stop `ELedgerCare.Api` #2, confirm `<= 4` attempt run directories exist, execute clean `pg_ctl` fast stop + start of owned PostgreSQL `18.7` (`55435`), and start `ELedgerCare.Api` #3 with `LocalOcr__Enabled=false`.
   - Verify all 3 completed documents reopen over HTTP (`workerEnabled == false`, idempotent `POST /extraction` returns `200` with `0` new attempts and `0` Python/model processes) and in headless Microsoft Edge (`verify_ui_reviewer_real_results.mjs`: unreviewed banner, pinned provenance, inert plain-text/table DOM with `0` executable elements/attributes, exact page order, preserved `[Interrupted, Completed]` attempt history on Doc 3, and byte-exact PDF downloads).
   - Stop all reviewer services in `finally`, verify all observed `(launcher_pid, worker_pid)` identities exited, re-verify all `18` Q0 model objects + notice + AST safety, confirm ports `5290/4310/55435` unbound, and write `trial-summary-reviewer.json` + `lease-return-reviewer.json`.

## 5. Future Live Commands (Only After Fresh Coordinator Reviewer Release)

```powershell
Set-Location "C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-next-reviewer"
git fetch origin --no-tags

# 1. Pure CPU/Git dry-run validation of the future coordinator reviewer release:
& "C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe" -B `
  docs/reviews/WP-0006/eld-next-reviewer/runtime-preparation/helpers/run_f2_reviewer_runtime.py `
  --dry-run-validate `
  --release-commit <FUTURE_COORDINATOR_RELEASE_SHA> `
  --release-path <FUTURE_REVIEWER_RELEASE_JSON_PATH> `
  --validation-output .scratch/stage2-reviewer-runtime/dry-run-validation.json

# 2. Bounded <=4-attempt independent GPU runtime verification under active sole reviewer lease:
& "C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe" -B `
  docs/reviews/WP-0006/eld-next-reviewer/runtime-preparation/helpers/run_f2_reviewer_runtime.py `
  --execute-live `
  --release-commit <FUTURE_COORDINATOR_RELEASE_SHA> `
  --release-path <FUTURE_REVIEWER_RELEASE_JSON_PATH>

# 3. Safe secret-checked & holdout-checked evidence packaging before canonical /004 report:
& "C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe" -B `
  docs/reviews/WP-0006/eld-next-reviewer/runtime-preparation/helpers/run_f2_reviewer_runtime.py `
  --package-evidence `
  --release-commit <FUTURE_COORDINATOR_RELEASE_SHA> `
  --release-path <FUTURE_REVIEWER_RELEASE_JSON_PATH> `
  --dest-dir docs/reviews/WP-0006/eld-next-reviewer/runtime-execution
```
